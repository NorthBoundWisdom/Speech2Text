from __future__ import annotations

from pathlib import Path
from typing import Any

from ..numeric import as_float
from .artifacts import run_file_state_issues, text_payload_consistency_issues
from .chunks import chunk_issues
from .confidence import segment_confidence_issues
from .issues import issue as _issue
from .issues import normalize_issue_contract as _normalize_issue_contract
from .payloads import load_qa_payloads
from .policy import resolve_qa_settings
from .readable import readable_metrics_and_issues
from .repair import repair_windows as _repair_windows
from .scoring import quality_score as _quality_score
from .text import text_quality_issues
from .timing import segment_timing_issues
from ..subtitles import validate_srt_text, validate_vtt_text
from ..utils import compact_ws


def resolve_output_dir(path: str | Path) -> Path:
    p = Path(path)
    return p


def details_dir(output_dir: Path) -> Path:
    return output_dir


def _as_float(value: Any) -> float | None:
    return as_float(value)


def _audio_duration_from_payloads(
    *,
    run: dict[str, Any] | None,
    raw: dict[str, Any] | None,
    corrected: dict[str, Any] | None,
    segments: list[dict[str, Any]],
) -> float | None:
    for payload in (run, corrected, raw):
        if not isinstance(payload, dict):
            continue
        value = _as_float(payload.get("audio_duration"))
        if value is not None and value > 0:
            return value
    ends = [_as_float(segment.get("end")) for segment in segments]
    valid = [value for value in ends if value is not None and value > 0]
    return max(valid) if valid else None


def _visible_transcript_chars(segments: list[dict[str, Any]]) -> int:
    return sum(len(compact_ws(str(segment.get("text", "")))) for segment in segments)


def _segment_timing_issues(
    segments: list[dict[str, Any]],
    *,
    max_gap: float,
    max_segment_duration: float,
) -> list[dict[str, Any]]:
    return segment_timing_issues(
        segments,
        max_gap=max_gap,
        max_segment_duration=max_segment_duration,
        issue_factory=_issue,
    )


def _text_quality_issues(
    segments: list[dict[str, Any]],
    *,
    glossary: dict[str, Any] | None,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    return text_quality_issues(
        segments,
        glossary=glossary,
        settings=settings,
        issue_factory=_issue,
    )


def _segment_confidence_issues(
    segments: list[dict[str, Any]],
    *,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    return segment_confidence_issues(segments, settings=settings, issue_factory=_issue)


def _transcript_health_issues(
    segments: list[dict[str, Any]],
    *,
    audio_duration: float | None,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not segments or audio_duration is None or audio_duration <= 0:
        return issues
    char_count = _visible_transcript_chars(segments)
    minutes = max(audio_duration / 60.0, 1e-6)
    chars_per_minute = char_count / minutes
    min_cpm = float(settings.get("min_chars_per_minute", 10.0))
    max_cpm = float(settings.get("max_chars_per_minute", 900.0))
    if chars_per_minute < min_cpm:
        issues.append(
            _issue(
                "warning",
                "low_transcript_density",
                "Transcript has very few characters for the audio duration",
                chars_per_minute=round(chars_per_minute, 2),
                threshold=min_cpm,
                char_count=char_count,
                audio_duration=round(audio_duration, 3),
            )
        )
    if chars_per_minute > max_cpm:
        issues.append(
            _issue(
                "warning",
                "high_transcript_density",
                "Transcript has unusually many characters for the audio duration",
                chars_per_minute=round(chars_per_minute, 2),
                threshold=max_cpm,
                char_count=char_count,
                audio_duration=round(audio_duration, 3),
            )
        )
    sorted_segments = sorted(
        segments,
        key=lambda item: (_as_float(item.get("start")) or 0.0, _as_float(item.get("end")) or 0.0),
    )
    gap_total = 0.0
    previous_end = 0.0
    for segment in sorted_segments:
        start = _as_float(segment.get("start"))
        end = _as_float(segment.get("end"))
        if start is None or end is None:
            continue
        if start > previous_end:
            gap_total += start - previous_end
        previous_end = max(previous_end, end)
    if previous_end < audio_duration:
        gap_total += audio_duration - previous_end
    ratio = gap_total / audio_duration
    max_ratio = float(settings.get("max_gap_coverage_ratio", 0.20))
    if ratio > max_ratio:
        issues.append(
            _issue(
                "warning",
                "high_uncovered_audio_ratio",
                "Large portions of the audio timeline have no transcript segments",
                uncovered_ratio=round(ratio, 4),
                threshold=max_ratio,
                uncovered_seconds=round(gap_total, 3),
                audio_duration=round(audio_duration, 3),
            )
        )
    return issues


def build_qa_report(
    output_dir: str | Path,
    *,
    profile: str | None = "balanced",
    qa_config: str | Path | None = None,
    max_gap: float | None = None,
    max_segment_duration: float | None = None,
    max_subtitle_chars: int | None = None,
    max_subtitle_line_chars: int | None = None,
    fail_on_srt_error: bool = True,
) -> dict[str, Any]:
    """Build an in-memory QA report for a transcription output bundle.

    Args:
        output_dir: Output bundle directory, or a path that resolves to one.
        profile: QA profile name. Use ``None`` to rely on defaults only.
        qa_config: Optional QA settings file.
        max_gap: Override for maximum allowed timeline gap in seconds.
        max_segment_duration: Override for maximum segment duration.
        max_subtitle_chars: Override for subtitle cue character limit.
        max_subtitle_line_chars: Override for subtitle line character limit.
        fail_on_srt_error: Whether SRT blocker issues fail the report.

    Returns:
        A dictionary with ``success``, ``summary``, ``checks``, ``metrics``,
        ``quality_score``, ``issues``, and ``suggested_repairs`` keys.
    """

    settings = resolve_qa_settings(
        profile=profile,
        config_file=qa_config,
        overrides={
            "max_gap": max_gap,
            "max_segment_duration": max_segment_duration,
            "max_subtitle_chars": max_subtitle_chars,
            "max_subtitle_line_chars": max_subtitle_line_chars,
        },
    )
    max_gap_value = float(settings["max_gap"])
    max_segment_duration_value = float(settings["max_segment_duration"])
    max_subtitle_chars_value = int(settings["max_subtitle_chars"])
    max_subtitle_line_chars_value = int(settings["max_subtitle_line_chars"])

    base = resolve_output_dir(output_dir)
    details = details_dir(base)
    payloads = load_qa_payloads(details)
    raw = payloads.raw
    corrected = payloads.corrected
    run = payloads.run
    review = payloads.review
    manifest = payloads.manifest
    glossary = payloads.glossary
    corrections_payload = payloads.corrections
    raw_segments = payloads.raw_segments
    segments = payloads.segments
    audio_duration = _audio_duration_from_payloads(
        run=run if isinstance(run, dict) else None,
        raw=raw if isinstance(raw, dict) else None,
        corrected=corrected if isinstance(corrected, dict) else None,
        segments=segments,
    )

    issues: list[dict[str, Any]] = []
    if not isinstance(raw, dict):
        issues.append(_issue("blocker", "missing_raw_json", "raw.json is missing or invalid"))
    elif not raw_segments:
        issues.append(_issue("blocker", "missing_segments", "raw.json has no segments"))
    else:
        issues.extend(
            _segment_timing_issues(
                segments,
                max_gap=max_gap_value,
                max_segment_duration=max_segment_duration_value,
            )
        )
        issues.extend(
            _text_quality_issues(
                segments,
                glossary=glossary if isinstance(glossary, dict) else None,
                settings=settings,
            )
        )
        issues.extend(_segment_confidence_issues(segments, settings=settings))
        issues.extend(
            _transcript_health_issues(segments, audio_duration=audio_duration, settings=settings)
        )

    issues.extend(
        text_payload_consistency_issues(
            base=base,
            details=details,
            raw=raw if isinstance(raw, dict) else None,
            corrected=corrected if isinstance(corrected, dict) else None,
            segments=segments,
        )
    )
    issues.extend(run_file_state_issues(details, run if isinstance(run, dict) else None))
    readable_metrics, readable_issues = readable_metrics_and_issues(
        base,
        corrections_payload=corrections_payload,
        settings=settings,
        issue_factory=_issue,
    )
    issues.extend(readable_issues)

    srt_path = details / "transcript.srt"
    if not srt_path.exists():
        srt_path = base / "transcript.srt"
    if srt_path.exists():
        srt_issues = validate_srt_text(
            srt_path.read_text(encoding="utf-8"),
            max_chars=max_subtitle_chars_value,
            max_line_chars=max_subtitle_line_chars_value,
        )
        for item in srt_issues:
            severity = item.get("severity", "warning")
            if not fail_on_srt_error and severity == "blocker":
                severity = "warning"
            issues.append({**item, "severity": severity, "source": "transcript.srt"})
    else:
        issues.append(_issue("blocker", "missing_srt", "transcript.srt is missing"))

    vtt_path = details / "transcript.vtt"
    if vtt_path.exists():
        issues.extend(
            {**item, "source": "transcript.vtt"}
            for item in validate_vtt_text(vtt_path.read_text(encoding="utf-8"))
        )

    if isinstance(review, dict):
        summary = review.get("summary", {})
        if isinstance(summary, dict) and int(summary.get("segment_issue_count") or 0) > 0:
            issues.append(
                _issue(
                    "review",
                    "review_segment_issues",
                    "Review report contains segment-level issues",
                    count=int(summary.get("segment_issue_count") or 0),
                )
            )

    issues.extend(
        chunk_issues(
            details,
            run if isinstance(run, dict) else None,
            manifest if isinstance(manifest, dict) else None,
            segments,
        )
    )

    issues = _normalize_issue_contract(issues)

    blocking_count = sum(1 for item in issues if item.get("severity") == "blocker")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    review_count = sum(1 for item in issues if item.get("severity") == "review")
    diagnostic_count = sum(1 for item in issues if item.get("severity") == "diagnostic")
    suggested_repairs = _repair_windows(
        issues,
        padding=float(settings.get("repair_padding", 15.0)),
        max_window_seconds=float(settings.get("max_repair_window_seconds", 300.0)),
        merge_gap_seconds=float(settings.get("merge_repair_gap_seconds", 2.0)),
    )
    metrics = {
        "audio_duration": audio_duration,
        "visible_char_count": _visible_transcript_chars(segments),
        "segment_count": len(segments),
        "readable": readable_metrics,
    }
    return {
        "success": blocking_count == 0,
        "summary": {
            "issue_count": len(issues),
            "blocking_issue_count": blocking_count,
            "warning_count": warning_count,
            "review_count": review_count,
            "diagnostic_count": diagnostic_count,
            "repair_window_count": len(suggested_repairs),
        },
        "checks": {
            "profile": settings.get("profile"),
            "max_gap": max_gap_value,
            "max_segment_duration": max_segment_duration_value,
            "max_subtitle_chars": max_subtitle_chars_value,
            "max_subtitle_line_chars": max_subtitle_line_chars_value,
            "fail_on_srt_error": fail_on_srt_error,
            "min_chars_per_minute": settings.get("min_chars_per_minute"),
            "max_chars_per_minute": settings.get("max_chars_per_minute"),
            "max_gap_coverage_ratio": settings.get("max_gap_coverage_ratio"),
            "max_readable_paragraph_chars_warning": settings.get(
                "max_readable_paragraph_chars_warning"
            ),
            "max_readable_paragraph_chars_blocker": settings.get(
                "max_readable_paragraph_chars_blocker"
            ),
            "max_readable_run_on_chars": settings.get("max_readable_run_on_chars"),
            "min_readable_punctuation_per_1000_chars": settings.get(
                "min_readable_punctuation_per_1000_chars"
            ),
        },
        "metrics": metrics,
        "quality_score": _quality_score(issues, metrics),
        "issues": issues,
        "suggested_repairs": suggested_repairs,
    }
