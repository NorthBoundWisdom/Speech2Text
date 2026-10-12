from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import DEFAULT_MODEL_ALIAS
from .paths import DEFAULT_OUTPUT_DIR
from .pipeline import TranscribeOptions, run_transcription
from .qa import run_qa
from .runinfo import now_iso
from .utils import (
    compact_ws,
    ensure_dir,
    read_json,
    read_text,
    write_json_atomic,
    write_text_atomic,
)


Transcriber = Callable[[TranscribeOptions], dict[str, Any]]


@dataclass(frozen=True)
class GoldBenchmarkOptions:
    samples: tuple[Path, ...]
    output_dir: Path = DEFAULT_OUTPUT_DIR / "benchmark" / "gold"
    model: str = DEFAULT_MODEL_ALIAS
    models: tuple[str, ...] = ()
    language: str | None = "zh"
    prompt_file: Path | None = None
    glossary_file: Path | None = None
    terms_file: Path | None = None
    condition_on_previous_text_values: tuple[bool, ...] = (True,)
    max_cer: float | None = None
    min_term_hit_rate: float | None = None
    require_qa_pass: bool = False
    require_srt_pass: bool = False
    max_repeated_phrase_count: int | None = None
    max_large_gap_count: int | None = None


def _edit_distance(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


def _normalize_for_cer(text: str) -> str:
    return "".join(compact_ws(text).split())


def character_error_rate(hypothesis: str, reference: str) -> float | None:
    ref = _normalize_for_cer(reference)
    hyp = _normalize_for_cer(hypothesis)
    if not ref:
        return None
    return round(_edit_distance(hyp, ref) / len(ref), 4)


def _load_terms(sample: Path, terms_file: Path | None) -> list[str]:
    paths = [
        path
        for path in (terms_file, sample.with_suffix(".terms.json"))
        if path is not None and path.exists()
    ]
    if not paths:
        return []
    payload = read_json(paths[0])
    if isinstance(payload, list):
        return [str(item) for item in payload if str(item).strip()]
    if isinstance(payload, dict):
        terms = payload.get("terms") or payload.get("technical_terms") or []
        if isinstance(terms, list):
            return [str(item) for item in terms if str(item).strip()]
    return []


def _term_hit_rate(text: str, terms: list[str]) -> float | None:
    if not terms:
        return None
    hits = sum(1 for term in terms if term in text)
    return round(hits / len(terms), 4)


def _qa_issue_count(qa_report: dict[str, Any], issue_type: str) -> int:
    issues = qa_report.get("issues", []) if isinstance(qa_report.get("issues"), list) else []
    return sum(1 for issue in issues if isinstance(issue, dict) and issue.get("type") == issue_type)


def _qa_unknown_ascii_token_count(qa_report: dict[str, Any]) -> int:
    issues = qa_report.get("issues", []) if isinstance(qa_report.get("issues"), list) else []
    tokens: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("type") != "unknown_ascii_tokens":
            continue
        for token in issue.get("tokens", []) if isinstance(issue.get("tokens"), list) else []:
            tokens.add(str(token))
    return len(tokens)


def _qa_srt_pass(qa_report: dict[str, Any]) -> bool | None:
    if not qa_report:
        return None
    issues = qa_report.get("issues", []) if isinstance(qa_report.get("issues"), list) else []
    for issue in issues:
        if (
            isinstance(issue, dict)
            and issue.get("source") == "transcript.srt"
            and issue.get("severity") == "blocker"
        ):
            return False
    return True


def _ref_path(sample: Path) -> Path:
    return sample.with_suffix(".ref.txt")


def _transcript_text(run: dict[str, Any]) -> str:
    files = run.get("output_files", {}) if isinstance(run.get("output_files"), dict) else {}
    path = files.get("transcript.corrected.txt")
    if path and Path(path).exists():
        return read_text(path) or ""
    job_dir = run.get("job_dir")
    if job_dir and (Path(str(job_dir)) / "transcript.corrected.txt").exists():
        return read_text(Path(str(job_dir)) / "transcript.corrected.txt") or ""
    if job_dir and (Path(str(job_dir)) / "transcript.corrected.txt").exists():
        return read_text(Path(str(job_dir)) / "transcript.corrected.txt") or ""
    return str(run.get("text") or "")


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return name.strip(".-") or "item"


def _benchmark_models(options: GoldBenchmarkOptions) -> tuple[str, ...]:
    if options.models:
        return tuple(dict.fromkeys(options.models))
    return (options.model,)


def _condition_values(options: GoldBenchmarkOptions) -> tuple[bool, ...]:
    values = tuple(dict.fromkeys(bool(item) for item in options.condition_on_previous_text_values))
    return values or (True,)


def _gate_config(options: GoldBenchmarkOptions) -> dict[str, Any]:
    return {
        "max_cer": options.max_cer,
        "min_term_hit_rate": options.min_term_hit_rate,
        "require_qa_pass": options.require_qa_pass,
        "require_srt_pass": options.require_srt_pass,
        "max_repeated_phrase_count": options.max_repeated_phrase_count,
        "max_large_gap_count": options.max_large_gap_count,
    }


def _gate_is_enabled(gate: dict[str, Any]) -> bool:
    return any(value not in (None, False) for value in gate.values())


def _evaluate_gate(rows: list[dict[str, Any]], gate: dict[str, Any]) -> list[dict[str, Any]]:
    if not _gate_is_enabled(gate):
        return []
    failures: list[dict[str, Any]] = []
    for row in rows:
        checks: list[tuple[str, Any, Any, Callable[[float, float], bool]]] = [
            (
                "max_cer",
                row.get("cer"),
                gate.get("max_cer"),
                lambda value, threshold: value <= threshold,
            ),
            (
                "min_term_hit_rate",
                row.get("term_hit_rate"),
                gate.get("min_term_hit_rate"),
                lambda value, threshold: value >= threshold,
            ),
            (
                "max_repeated_phrase_count",
                row.get("repeated_phrase_count"),
                gate.get("max_repeated_phrase_count"),
                lambda value, threshold: value <= threshold,
            ),
            (
                "max_large_gap_count",
                row.get("large_gap_count"),
                gate.get("max_large_gap_count"),
                lambda value, threshold: value <= threshold,
            ),
        ]
        for name, value, threshold, predicate in checks:
            if threshold is None:
                continue
            if not isinstance(value, (int, float)) or not predicate(float(value), float(threshold)):
                failures.append(
                    {
                        "sample": row.get("sample"),
                        "model": row.get("model_input") or row.get("model"),
                        "condition_on_previous_text": row.get("condition_on_previous_text"),
                        "metric": name,
                        "value": value,
                        "threshold": threshold,
                    }
                )
        if gate.get("require_qa_pass") and row.get("qa_success") is not True:
            failures.append(
                {
                    "sample": row.get("sample"),
                    "model": row.get("model_input") or row.get("model"),
                    "condition_on_previous_text": row.get("condition_on_previous_text"),
                    "metric": "qa_success",
                    "value": row.get("qa_success"),
                    "threshold": True,
                }
            )
        if gate.get("require_srt_pass") and row.get("srt_pass") is not True:
            failures.append(
                {
                    "sample": row.get("sample"),
                    "model": row.get("model_input") or row.get("model"),
                    "condition_on_previous_text": row.get("condition_on_previous_text"),
                    "metric": "srt_pass",
                    "value": row.get("srt_pass"),
                    "threshold": True,
                }
            )
    return failures


def run_gold_benchmark(
    options: GoldBenchmarkOptions,
    *,
    transcriber: Transcriber = run_transcription,
) -> dict[str, Any]:
    timestamp = now_iso().replace(":", "").replace("-", "").split("+", 1)[0]
    run_dir = ensure_dir(options.output_dir / timestamp)
    rows: list[dict[str, Any]] = []
    models = _benchmark_models(options)
    condition_values = _condition_values(options)
    for model in models:
        for condition_on_previous_text in condition_values:
            condition_label = "prev-on" if condition_on_previous_text else "prev-off"
            for sample in options.samples:
                sample_path = sample.expanduser().resolve()
                job_name = "__".join(
                    (
                        _safe_name(sample_path.stem),
                        _safe_name(model),
                        condition_label,
                    )
                )
                run = transcriber(
                    TranscribeOptions(
                        input_path=sample_path,
                        output_dir=run_dir,
                        name=job_name,
                        model=model,
                        language=options.language,
                        prompt_file=options.prompt_file,
                        glossary_file=options.glossary_file,
                        condition_on_previous_text=condition_on_previous_text,
                    )
                )
                transcript = _transcript_text(run)
                reference = read_text(_ref_path(sample_path)) or ""
                terms = _load_terms(sample_path, options.terms_file)
                qa_report = {}
                job_dir = Path(str(run.get("job_dir"))) if run.get("job_dir") else None
                if job_dir and job_dir.exists():
                    qa_report = run_qa(job_dir)
                rows.append(
                    {
                        "sample": str(sample_path),
                        "reference": str(_ref_path(sample_path))
                        if _ref_path(sample_path).exists()
                        else "",
                        "job_dir": str(run.get("job_dir", "")),
                        "model": run.get("model_alias_or_input") or run.get("model") or model,
                        "model_input": model,
                        "condition_on_previous_text": condition_on_previous_text,
                        "cer": character_error_rate(transcript, reference),
                        "term_hit_rate": _term_hit_rate(transcript, terms),
                        "terms": terms,
                        "qa_success": qa_report.get("success") if qa_report else None,
                        "srt_pass": _qa_srt_pass(qa_report),
                        "unknown_ascii_token_count": _qa_unknown_ascii_token_count(qa_report),
                        "repeated_phrase_count": _qa_issue_count(qa_report, "repeated_phrase"),
                        "large_gap_count": _qa_issue_count(qa_report, "large_timing_gap"),
                        "runtime_seconds": run.get("runtime_seconds"),
                        "peak_rss_mb": run.get("peak_rss_mb"),
                    }
                )
    gate = _gate_config(options)
    gate_failures = _evaluate_gate(rows, gate)
    report = {
        "success": not gate_failures,
        "created_at": now_iso(),
        "models": list(models),
        "condition_on_previous_text_values": list(condition_values),
        "gate": gate,
        "gate_failures": gate_failures,
        "results": rows,
    }
    write_json_atomic(run_dir / "report.json", report)
    write_text_atomic(run_dir / "report.md", gold_report_to_markdown(report))
    return {**report, "output_dir": str(run_dir)}


def _format_metric(value: Any) -> str:
    return "n/a" if value is None else str(value)


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, bool], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(
            (
                str(row.get("model_input") or row.get("model") or ""),
                bool(row.get("condition_on_previous_text")),
            ),
            [],
        ).append(row)

    aggregated: list[dict[str, Any]] = []
    for (model, condition), items in sorted(groups.items()):
        cers = [item["cer"] for item in items if isinstance(item.get("cer"), (int, float))]
        term_rates = [
            item["term_hit_rate"]
            for item in items
            if isinstance(item.get("term_hit_rate"), (int, float))
        ]
        qa_values = [item.get("qa_success") for item in items if item.get("qa_success") is not None]
        srt_values = [item.get("srt_pass") for item in items if item.get("srt_pass") is not None]
        runtimes = [
            item["runtime_seconds"]
            for item in items
            if isinstance(item.get("runtime_seconds"), (int, float))
        ]
        peak_memory = [
            item["peak_rss_mb"]
            for item in items
            if isinstance(item.get("peak_rss_mb"), (int, float))
        ]
        aggregated.append(
            {
                "model": model,
                "condition_on_previous_text": condition,
                "sample_count": len(items),
                "average_cer": round(sum(cers) / len(cers), 4) if cers else None,
                "average_term_hit_rate": round(sum(term_rates) / len(term_rates), 4)
                if term_rates
                else None,
                "qa_pass_count": sum(1 for item in qa_values if item is True),
                "qa_checked_count": len(qa_values),
                "srt_pass_count": sum(1 for item in srt_values if item is True),
                "srt_checked_count": len(srt_values),
                "unknown_ascii_token_count": sum(
                    int(item.get("unknown_ascii_token_count") or 0) for item in items
                ),
                "repeated_phrase_count": sum(
                    int(item.get("repeated_phrase_count") or 0) for item in items
                ),
                "large_gap_count": sum(int(item.get("large_gap_count") or 0) for item in items),
                "peak_rss_mb": round(max(peak_memory), 2) if peak_memory else None,
                "total_runtime_seconds": round(sum(runtimes), 2) if runtimes else None,
            }
        )
    return aggregated


def gold_report_to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Gold Benchmark", ""]
    rows = report.get("results", []) if isinstance(report.get("results"), list) else []
    gate_failures = (
        report.get("gate_failures", []) if isinstance(report.get("gate_failures"), list) else []
    )
    if report.get("gate") and any(
        value not in (None, False) for value in dict(report.get("gate", {})).values()
    ):
        lines.append("## Acceptance Gate")
        lines.append("")
        lines.append(f"Status: {'PASS' if report.get('success') else 'FAIL'}")
        lines.append("")
        if gate_failures:
            for failure in gate_failures:
                sample = Path(str(failure.get("sample", ""))).name
                condition = "on" if failure.get("condition_on_previous_text") else "off"
                lines.append(
                    "- {sample} {model} previous-text={condition} {metric}: {value} (required {threshold})".format(
                        sample=sample,
                        model=failure.get("model", ""),
                        condition=condition,
                        metric=failure.get("metric", ""),
                        value=_format_metric(failure.get("value")),
                        threshold=_format_metric(failure.get("threshold")),
                    )
                )
        else:
            lines.append("- All configured gate checks passed.")
        lines.append("")
    aggregate = _aggregate_rows(rows)
    if aggregate:
        lines.append("## Matrix Summary")
        lines.append("")
        lines.append(
            "| Model | Previous Text | Samples | Avg CER | Avg Term Hit Rate | QA Pass | SRT Pass | Unknown ASCII | Repeats | Gaps | Peak MB | Total Runtime |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in aggregate:
            runtime = row.get("total_runtime_seconds")
            peak_mb = row.get("peak_rss_mb")
            lines.append(
                "| {model} | {condition} | {samples} | {cer} | {term_hit} | {qa} | {srt} | {ascii_count} | {repeats} | {gaps} | {peak_mb} | {runtime} |".format(
                    model=row.get("model", ""),
                    condition="on" if row.get("condition_on_previous_text") else "off",
                    samples=row.get("sample_count", 0),
                    cer=_format_metric(row.get("average_cer")),
                    term_hit=_format_metric(row.get("average_term_hit_rate")),
                    qa=f"{row.get('qa_pass_count', 0)}/{row.get('qa_checked_count', 0)}",
                    srt=f"{row.get('srt_pass_count', 0)}/{row.get('srt_checked_count', 0)}",
                    ascii_count=row.get("unknown_ascii_token_count", 0),
                    repeats=row.get("repeated_phrase_count", 0),
                    gaps=row.get("large_gap_count", 0),
                    peak_mb="n/a" if peak_mb is None else f"{peak_mb:.2f}",
                    runtime="n/a" if runtime is None else f"{runtime:.2f}s",
                )
            )
        lines.append("")
    lines.append("## Per-Sample Results")
    lines.append("")
    lines.append(
        "| Sample | Model | Previous Text | CER | Term Hit Rate | QA | SRT | Unknown ASCII | Repeats | Gaps | Runtime | Peak MB |"
    )
    lines.append("|---|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        sample = Path(str(row.get("sample", ""))).name
        qa = (
            "n/a"
            if row.get("qa_success") is None
            else ("pass" if row.get("qa_success") else "fail")
        )
        srt = "n/a" if row.get("srt_pass") is None else ("pass" if row.get("srt_pass") else "fail")
        runtime = row.get("runtime_seconds")
        peak_mb = row.get("peak_rss_mb")
        lines.append(
            "| {sample} | {model} | {condition} | {cer} | {term_hit} | {qa} | {srt} | {ascii_count} | {repeats} | {gaps} | {runtime} | {peak_mb} |".format(
                sample=sample,
                model=row.get("model_input") or row.get("model", ""),
                condition="on" if row.get("condition_on_previous_text") else "off",
                cer=_format_metric(row.get("cer")),
                term_hit=_format_metric(row.get("term_hit_rate")),
                qa=qa,
                srt=srt,
                ascii_count=row.get("unknown_ascii_token_count", 0),
                repeats=row.get("repeated_phrase_count", 0),
                gaps=row.get("large_gap_count", 0),
                runtime="n/a" if runtime is None else f"{float(runtime):.2f}s",
                peak_mb="n/a" if peak_mb is None else f"{float(peak_mb):.2f}",
            )
        )
    return "\n".join(lines).strip() + "\n"
