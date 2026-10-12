from __future__ import annotations

from pathlib import Path
from typing import Any


MIN_CANDIDATE_CHAR_RATIO = 0.7
MAX_CANDIDATE_CHAR_RATIO = 1.5
MAX_ABSOLUTE_TOP_TOKEN_RATIO = 0.25
MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER = 3.0


def coerce_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_float(value: Any) -> str:
    number = coerce_optional_float(value)
    return "n/a" if number is None else f"{number:.2f}"


def summary_metrics(run: dict[str, Any], *, default_success: bool) -> dict[str, Any]:
    review = run.get("review", {}) if isinstance(run.get("review"), dict) else {}
    quality = run.get("quality_metrics", {}) if isinstance(run.get("quality_metrics"), dict) else {}
    timing = quality.get("timing", {}) if isinstance(quality.get("timing"), dict) else {}
    return {
        "success": bool(run.get("success", default_success)),
        "returncode": run.get("returncode", 0),
        "timed_out": bool(run.get("timed_out", False)),
        "runtime_seconds": float(run.get("runtime_seconds", 0.0) or 0.0),
        "peak_rss_mb": coerce_optional_float(run.get("peak_rss_mb")),
        "corrected_char_count": int(quality.get("corrected_char_count", 0) or 0),
        "empty_corrected_segment_count": int(quality.get("empty_corrected_segment_count", 0) or 0),
        "review_issue_count": int(
            review.get("issue_count", quality.get("review_issue_count", 0)) or 0
        ),
        "review_segment_issue_count": int(
            review.get("segment_issue_count", quality.get("review_segment_issue_count", 0)) or 0
        ),
        "correction_count": int(quality.get("correction_count", 0) or 0),
        "max_repeated_token_run": int(quality.get("max_repeated_token_run", 0) or 0),
        "top_token_ratio": float(quality.get("top_token_ratio", 0.0) or 0.0),
        "srt_vtt_compatible": bool(timing.get("srt_vtt_compatible", False)),
        "timed_segment_count": int(timing.get("timed_segment_count", 0) or 0),
        "missing_timing_segment_count": int(timing.get("missing_timing_segment_count", 0) or 0),
        "invalid_timing_segment_count": int(timing.get("invalid_timing_segment_count", 0) or 0),
        "non_monotonic_timing_segment_count": int(
            timing.get("non_monotonic_timing_segment_count", 0) or 0
        ),
        "overlapping_timing_segment_count": int(
            timing.get("overlapping_timing_segment_count", 0) or 0
        ),
    }


def guardrail_failures(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    corrected_char_ratio: float,
    top_token_ratio_bound: float,
) -> list[str]:
    failures: list[str] = []
    if not bool(candidate["success"]):
        failures.append("candidate_command_failed")
    if bool(candidate["timed_out"]):
        failures.append("candidate_timed_out")
    baseline_chars = int(baseline["corrected_char_count"])
    candidate_chars = int(candidate["corrected_char_count"])
    if baseline_chars <= 0:
        failures.append("empty_baseline")
    if candidate_chars <= 0:
        failures.append("empty_candidate")
    elif baseline_chars > 0 and corrected_char_ratio < MIN_CANDIDATE_CHAR_RATIO:
        failures.append("char_ratio_low")
    elif baseline_chars > 0 and corrected_char_ratio > MAX_CANDIDATE_CHAR_RATIO:
        failures.append("char_ratio_high")
    if int(candidate["review_issue_count"]) > int(baseline["review_issue_count"]):
        failures.append("review_issue_regression")
    if int(candidate["review_segment_issue_count"]) > int(baseline["review_segment_issue_count"]):
        failures.append("review_segment_issue_regression")
    if int(candidate["correction_count"]) > int(baseline["correction_count"]):
        failures.append("correction_count_regression")
    if int(candidate["max_repeated_token_run"]) > int(baseline["max_repeated_token_run"]):
        failures.append("repetition_regression")
    if float(candidate["top_token_ratio"]) > top_token_ratio_bound:
        failures.append("top_token_ratio_regression")
    if not bool(candidate["srt_vtt_compatible"]):
        failures.append("timestamp_incompatible")
    return failures


def comparison_payload(
    *,
    audio: Path,
    baseline_run: dict[str, Any],
    candidate_run: dict[str, Any],
) -> dict[str, Any]:
    baseline = summary_metrics(baseline_run, default_success=True)
    candidate = summary_metrics(candidate_run, default_success=False)
    baseline_chars = int(baseline["corrected_char_count"])
    candidate_chars = int(candidate["corrected_char_count"])
    corrected_char_ratio = candidate_chars / baseline_chars if baseline_chars > 0 else 0.0
    top_token_ratio_bound = max(
        MAX_ABSOLUTE_TOP_TOKEN_RATIO,
        float(baseline["top_token_ratio"]) * MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER,
    )
    failures = guardrail_failures(
        baseline=baseline,
        candidate=candidate,
        corrected_char_ratio=corrected_char_ratio,
        top_token_ratio_bound=top_token_ratio_bound,
    )
    return {
        "audio": str(audio),
        "candidate": candidate_run.get("candidate"),
        "baseline": baseline,
        "candidate_metrics": candidate,
        "corrected_char_ratio": corrected_char_ratio,
        "corrected_char_ratio_bounds": {
            "min": MIN_CANDIDATE_CHAR_RATIO,
            "max": MAX_CANDIDATE_CHAR_RATIO,
        },
        "top_token_ratio_bound": top_token_ratio_bound,
        "metric_guardrail_pass": not failures,
        "metric_guardrail_failures": failures,
        "promotion_note": (
            "Metric guardrail is necessary but not sufficient; semantic transcript quality still requires review."
        ),
    }


def format_failures(value: Any) -> str:
    if not isinstance(value, list):
        return str(value)
    if not value:
        return "none"
    return ", ".join(f"`{item}`" for item in value)
