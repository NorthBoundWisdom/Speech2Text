from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from atot.utils import read_json


def read_comparison(path: Path) -> dict[str, Any]:
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def candidate_from_path(path: Path, runs_dir: Path) -> str:
    try:
        relative = path.relative_to(runs_dir)
    except ValueError:
        return path.parent.name
    return relative.parts[1] if len(relative.parts) >= 3 else path.parent.name


def audio_label(comparison: dict[str, Any], fallback: str) -> str:
    audio = str(comparison.get("audio") or fallback)
    return Path(audio).name


def candidate_rows(runs_dir: Path, candidates: set[str] | None) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(runs_dir.glob("*/*/comparison.json")):
        comparison = read_comparison(path)
        if not comparison:
            continue
        candidate = str(comparison.get("candidate") or candidate_from_path(path, runs_dir))
        if candidates is not None and candidate not in candidates:
            continue
        comparison["_comparison_path"] = str(path)
        comparison["_audio_label"] = audio_label(comparison, path.parents[1].name)
        grouped.setdefault(candidate, []).append(comparison)
    return grouped


def number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def format_number(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def format_failures(failures: Counter[str]) -> str:
    if not failures:
        return "none"
    return ", ".join(f"`{code}`:{count}" for code, count in sorted(failures.items()))


def sort_number(value: Any) -> float:
    resolved = number(value)
    return resolved if resolved is not None else float("inf")


def candidate_summary(candidate: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    runtimes: list[float] = []
    rss_values: list[float] = []
    failures: Counter[str] = Counter()
    successful_commands = 0
    metric_passes = 0
    for row in rows:
        candidate_metrics = row.get("candidate_metrics", {})
        if not isinstance(candidate_metrics, dict):
            candidate_metrics = {}
        if candidate_metrics.get("success") is True:
            successful_commands += 1
        if row.get("metric_guardrail_pass") is True:
            metric_passes += 1
        runtime = number(candidate_metrics.get("runtime_seconds"))
        if runtime is not None:
            runtimes.append(runtime)
        rss = number(candidate_metrics.get("peak_rss_mb"))
        if rss is not None:
            rss_values.append(rss)
        for failure in row.get("metric_guardrail_failures", []) or []:
            failures[str(failure)] += 1
    return {
        "candidate": candidate,
        "audio_count": len(rows),
        "command_success_count": successful_commands,
        "metric_pass_count": metric_passes,
        "promotable": bool(rows)
        and successful_commands == len(rows)
        and metric_passes == len(rows),
        "avg_runtime_seconds": mean(runtimes) if runtimes else None,
        "max_runtime_seconds": max(runtimes) if runtimes else None,
        "avg_peak_rss_mb": mean(rss_values) if rss_values else None,
        "max_peak_rss_mb": max(rss_values) if rss_values else None,
        "failures": failures,
    }


def build_matrix_markdown(
    *,
    runs_dir: Path,
    candidates: set[str] | None = None,
    min_audio_count: int = 3,
) -> str:
    grouped = {
        candidate: rows
        for candidate, rows in candidate_rows(runs_dir, candidates).items()
        if len(rows) >= min_audio_count
    }
    summaries = sorted(
        (candidate_summary(candidate, rows) for candidate, rows in grouped.items()),
        key=lambda item: (
            not bool(item["promotable"]),
            -int(item["metric_pass_count"]),
            sort_number(item["avg_runtime_seconds"]),
            item["candidate"],
        ),
    )
    lines = [
        "# ASR Candidate Gate Matrix",
        "",
        f"- Runs dir: `{runs_dir}`",
        f"- Minimum audio count: {min_audio_count}",
        "",
        "| Candidate | Audio count | Command success | Metric pass | Promotable | Avg runtime s | Max runtime s | Avg RSS MB | Max RSS MB | Guardrail failures |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---|",
    ]
    for summary in summaries:
        audio_count = int(summary["audio_count"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{summary['candidate']}`",
                    str(audio_count),
                    f"{summary['command_success_count']}/{audio_count}",
                    f"{summary['metric_pass_count']}/{audio_count}",
                    "yes" if summary["promotable"] else "no",
                    format_number(summary["avg_runtime_seconds"]),
                    format_number(summary["max_runtime_seconds"]),
                    format_number(summary["avg_peak_rss_mb"]),
                    format_number(summary["max_peak_rss_mb"]),
                    format_failures(summary["failures"]),
                ]
            )
            + " |"
        )
    if not summaries:
        lines.append("| n/a | 0 | 0/0 | 0/0 | no | n/a | n/a | n/a | n/a | none |")
    lines.extend(
        [
            "",
            "## Per-Audio Rows",
            "",
            "| Candidate | Audio | Metric guardrail | Runtime s | RSS MB | Char ratio | Failures | Comparison |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for candidate in sorted(grouped):
        for row in sorted(grouped[candidate], key=lambda item: str(item.get("_audio_label", ""))):
            metrics = (
                row.get("candidate_metrics", {})
                if isinstance(row.get("candidate_metrics"), dict)
                else {}
            )
            failures = [str(item) for item in row.get("metric_guardrail_failures", []) or []]
            comparison_path = str(row.get("_comparison_path", ""))
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{candidate}`",
                        str(row.get("_audio_label", "n/a")),
                        "pass" if row.get("metric_guardrail_pass") is True else "fail",
                        format_number(number(metrics.get("runtime_seconds"))),
                        format_number(number(metrics.get("peak_rss_mb"))),
                        format_number(number(row.get("corrected_char_ratio"))),
                        "none" if not failures else ", ".join(f"`{item}`" for item in failures),
                        f"[comparison]({comparison_path})",
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "Promotion rule: a candidate must pass every current process-audio row and still requires semantic transcript review before replacing the baseline.",
        ]
    )
    return "\n".join(lines) + "\n"
