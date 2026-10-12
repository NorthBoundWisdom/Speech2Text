from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import short_model_name
from .runinfo import now_iso
from .utils import read_json, relative_posix_path, write_json_atomic, write_text_atomic


@dataclass(frozen=True)
class OutputAuditOptions:
    output_root: Path
    output_path: Path | None = None
    limit: int | None = None


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _relative_job_dir(job_dir: Path, output_root: Path) -> str:
    try:
        return relative_posix_path(job_dir, output_root)
    except ValueError:
        return str(job_dir)


def _qa_issue_counts(qa_report: dict[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    issues = qa_report.get("issues", []) if isinstance(qa_report.get("issues"), list) else []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_type = str(issue.get("type") or "").strip()
        if issue_type:
            counter[issue_type] += 1
    return counter


def _review_issue_types(review_report: dict[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    issues = (
        review_report.get("issues", []) if isinstance(review_report.get("issues"), list) else []
    )
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_type = str(issue.get("type") or "").strip()
        if issue_type:
            counter[issue_type] += 1
    return counter


def _top_codes(counter: Counter[str], *, limit: int = 3) -> list[str]:
    return [name for name, _count in counter.most_common(limit)]


def _run_rows(output_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_path in sorted(output_root.glob("*/*/run.json")):
        run = _read_json_dict(run_path)
        if not run:
            continue
        job_dir = Path(str(run.get("job_dir") or run_path.parent))
        qa_report = _read_json_dict(run_path.parent / "qa.json")
        review_report = _read_json_dict(run_path.parent / "review.json")
        quality = (
            run.get("quality_metrics", {}) if isinstance(run.get("quality_metrics"), dict) else {}
        )
        review_summary = run.get("review", {}) if isinstance(run.get("review"), dict) else {}
        qa_summary = run.get("qa", {}) if isinstance(run.get("qa"), dict) else {}
        qa_issue_counts = _qa_issue_counts(qa_report)
        review_issue_counts = _review_issue_types(review_report)
        rows.append(
            {
                "job_dir": str(job_dir),
                "relative_job_dir": _relative_job_dir(job_dir, output_root),
                "batch": job_dir.parent.name,
                "episode": job_dir.name,
                "created_at": run.get("created_at", ""),
                "success": bool(run.get("success")),
                "model": str(run.get("model_alias_or_input") or run.get("model") or ""),
                "backend": str(run.get("backend") or ""),
                "runtime_seconds": float(run.get("runtime_seconds", 0.0) or 0.0),
                "audio_duration": float(run.get("audio_duration", 0.0) or 0.0),
                "speed_factor": float(run.get("speed_factor", 0.0) or 0.0),
                "peak_rss_mb": float(run.get("peak_rss_mb", 0.0) or 0.0),
                "qa_status": str(qa_summary.get("status") or ""),
                "qa_issue_count": int(qa_summary.get("issue_count", 0) or 0),
                "qa_blocking_issue_count": int(qa_summary.get("blocking_issue_count", 0) or 0),
                "qa_warning_count": int(qa_summary.get("warning_count", 0) or 0),
                "review_issue_count": int(review_summary.get("issue_count", 0) or 0),
                "review_segment_issue_count": int(
                    review_summary.get("segment_issue_count", 0) or 0
                ),
                "corrected_char_count": int(quality.get("corrected_char_count", 0) or 0),
                "correction_count": int(quality.get("correction_count", 0) or 0),
                "empty_corrected_segment_count": int(
                    quality.get("empty_corrected_segment_count", 0) or 0
                ),
                "max_repeated_token_run": int(quality.get("max_repeated_token_run", 0) or 0),
                "top_token_ratio": float(quality.get("top_token_ratio", 0.0) or 0.0),
                "qa_issue_types": dict(qa_issue_counts),
                "review_issue_types": dict(review_issue_counts),
                "top_qa_issue_types": _top_codes(qa_issue_counts),
                "top_review_issue_types": _top_codes(review_issue_counts),
            }
        )
    rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return rows


def _summary(rows: list[dict[str, Any]], output_root: Path) -> dict[str, Any]:
    qa_fail_rows = [row for row in rows if row.get("qa_status") != "pass"]
    empty_rows = [row for row in rows if int(row.get("empty_corrected_segment_count", 0) or 0) > 0]
    review_rows = [row for row in rows if int(row.get("review_issue_count", 0) or 0) > 0]
    qa_issue_counts: Counter[str] = Counter()
    review_issue_counts: Counter[str] = Counter()
    for row in rows:
        qa_issue_counts.update(
            {key: int(value) for key, value in dict(row.get("qa_issue_types", {})).items()}
        )
        review_issue_counts.update(
            {key: int(value) for key, value in dict(row.get("review_issue_types", {})).items()}
        )
    worst_blockers = sorted(
        rows,
        key=lambda item: (
            -int(item.get("qa_blocking_issue_count", 0) or 0),
            -int(item.get("empty_corrected_segment_count", 0) or 0),
            -int(item.get("correction_count", 0) or 0),
            str(item.get("relative_job_dir", "")),
        ),
    )
    return {
        "created_at": now_iso(),
        "output_root": str(output_root),
        "run_count": len(rows),
        "qa_pass_count": sum(1 for row in rows if row.get("qa_status") == "pass"),
        "qa_fail_count": len(qa_fail_rows),
        "empty_segment_run_count": len(empty_rows),
        "review_issue_run_count": len(review_rows),
        "top_qa_issue_types": [
            {"type": name, "count": count} for name, count in qa_issue_counts.most_common(8)
        ],
        "top_review_issue_types": [
            {"type": name, "count": count} for name, count in review_issue_counts.most_common(8)
        ],
        "worst_runs": [
            {
                "relative_job_dir": row["relative_job_dir"],
                "qa_blocking_issue_count": row["qa_blocking_issue_count"],
                "empty_corrected_segment_count": row["empty_corrected_segment_count"],
                "correction_count": row["correction_count"],
                "top_qa_issue_types": row["top_qa_issue_types"],
            }
            for row in worst_blockers[:10]
        ],
    }


def _format_float(value: float) -> str:
    return f"{value:.2f}"


def audit_markdown(
    rows: list[dict[str, Any]], summary: dict[str, Any], *, limit: int | None = None
) -> str:
    shown = rows[:limit] if limit is not None else rows
    lines = [
        "# Output Library Audit",
        "",
        f"- Output root: `{summary.get('output_root', '')}`",
        f"- Run count: {summary.get('run_count', 0)}",
        f"- QA pass: {summary.get('qa_pass_count', 0)}",
        f"- QA fail: {summary.get('qa_fail_count', 0)}",
        f"- Runs with empty corrected segments: {summary.get('empty_segment_run_count', 0)}",
        f"- Runs with review issues: {summary.get('review_issue_run_count', 0)}",
        "",
    ]
    qa_types = summary.get("top_qa_issue_types", [])
    if qa_types:
        lines.append("## Top QA Issues")
        lines.append("")
        for item in qa_types:
            lines.append(f"- `{item['type']}`: {item['count']}")
        lines.append("")
    review_types = summary.get("top_review_issue_types", [])
    if review_types:
        lines.append("## Top Review Issues")
        lines.append("")
        for item in review_types:
            lines.append(f"- `{item['type']}`: {item['count']}")
        lines.append("")
    lines.extend(
        [
            "## Runs",
            "",
            "| Output | Model | QA | Blocking | Warnings | Empty segs | Review issues | Corrections | Repeat max | Top token | Runtime s | Speed x |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in shown:
        model = str(row.get("model") or "")
        model_label = short_model_name(model) if model else "n/a"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['relative_job_dir']}`",
                    model_label,
                    str(row.get("qa_status") or "n/a"),
                    str(row.get("qa_blocking_issue_count", 0)),
                    str(row.get("qa_warning_count", 0)),
                    str(row.get("empty_corrected_segment_count", 0)),
                    str(row.get("review_issue_count", 0)),
                    str(row.get("correction_count", 0)),
                    str(row.get("max_repeated_token_run", 0)),
                    _format_float(float(row.get("top_token_ratio", 0.0) or 0.0)),
                    _format_float(float(row.get("runtime_seconds", 0.0) or 0.0)),
                    _format_float(float(row.get("speed_factor", 0.0) or 0.0)),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def audit_outputs(options: OutputAuditOptions) -> dict[str, Any]:
    output_root = options.output_root.expanduser().resolve()
    rows = _run_rows(output_root)
    summary = _summary(rows, output_root)
    audit = {
        "created_at": summary["created_at"],
        "output_root": summary["output_root"],
        "summary": summary,
        "rows": rows,
    }
    if options.output_path is not None:
        output_path = options.output_path.expanduser().resolve()
        if output_path.suffix == ".json":
            write_json_atomic(output_path, audit)
        else:
            write_text_atomic(output_path, audit_markdown(rows, summary, limit=options.limit))
    return audit
