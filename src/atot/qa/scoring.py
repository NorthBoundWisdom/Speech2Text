from __future__ import annotations

from typing import Any

from .policy import IssueType
from ..runtime_defaults import (
    QA_BLOCKER_PENALTY,
    QA_CLOUD_BLOCKER_PENALTY,
    QA_REVIEW_PENALTY,
    QA_SCORE_MAX,
    QA_WARNING_PENALTY,
)


def score_from_penalty(
    *, base: int = 100, blockers: int = 0, warnings: int = 0, reviews: int = 0
) -> int:
    """Calculate a bounded QA score after severity penalties."""
    score = (
        base
        - blockers * QA_BLOCKER_PENALTY
        - warnings * QA_WARNING_PENALTY
        - reviews * QA_REVIEW_PENALTY
    )
    return max(0, min(QA_SCORE_MAX, score))


def quality_score(issues: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, int]:
    """Build the public QA score breakdown from normalized issues and metrics."""

    def count(types: set[str], severity: str | None = None) -> int:
        return sum(
            1
            for item in issues
            if str(item.get("type")) in types
            and (severity is None or str(item.get("severity")) == severity)
        )

    timeline_types = {
        "invalid_segment_timing",
        "negative_segment_start",
        "non_positive_segment_duration",
        "non_monotonic_segment_start",
        "overlapping_segment",
        str(IssueType.LARGE_TIMING_GAP),
        str(IssueType.LONG_SEGMENT),
        "chunk_core_coverage_gap",
        "chunk_core_merge_missing",
    }
    text_types = {
        str(IssueType.EMPTY_SEGMENT_TEXT),
        str(IssueType.REPEATED_PHRASE),
        str(IssueType.ADJACENT_DUPLICATE_SEGMENT),
        "control_character",
        str(IssueType.ENGLISH_PUNCTUATION_IN_CHINESE),
        "ascii_token_burst",
        "low_visible_char_density",
        "high_visible_char_density",
    }
    subtitle_types = {
        "missing_srt",
        "srt_time_order",
        "srt_time_overlap",
        "srt_text_too_long",
        "vtt_time_order",
        "vtt_time_overlap",
        "vtt_text_too_long",
    }
    confidence_types = {
        str(IssueType.LOW_AVG_LOGPROB_SEGMENT),
        str(IssueType.HIGH_COMPRESSION_RATIO_SEGMENT),
        str(IssueType.HIGH_NO_SPEECH_PROB_SEGMENT),
    }

    blocker_count = sum(1 for item in issues if item.get("severity") == "blocker")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    review_count = sum(1 for item in issues if item.get("severity") == "review")
    segment_count = int(metrics.get("segment_count") or 0)
    visible_char_count = int(metrics.get("visible_char_count") or 0)
    base = 90 if segment_count and visible_char_count else 65

    timeline_blockers = count(timeline_types, "blocker")
    timeline_warnings = count(timeline_types, "warning")
    text_blockers = count(text_types, "blocker")
    text_warnings = count(text_types, "warning")
    subtitle_blockers = count(subtitle_types, "blocker")
    subtitle_warnings = count(subtitle_types, "warning")
    confidence_blockers = count(confidence_types, "blocker")
    confidence_warnings = count(confidence_types, "warning")

    overall = score_from_penalty(
        base=base, blockers=blocker_count, warnings=warning_count, reviews=review_count
    )
    return {
        "overall": overall,
        "timeline": score_from_penalty(blockers=timeline_blockers, warnings=timeline_warnings),
        "text_health": score_from_penalty(blockers=text_blockers, warnings=text_warnings),
        "subtitle": score_from_penalty(blockers=subtitle_blockers, warnings=subtitle_warnings),
        "confidence": score_from_penalty(
            blockers=confidence_blockers, warnings=confidence_warnings
        ),
        "cloud_readiness": max(
            0, min(QA_SCORE_MAX, overall - blocker_count * QA_CLOUD_BLOCKER_PENALTY)
        ),
    }
