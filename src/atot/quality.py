from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .numeric import as_float
from .segments import coverage_metrics, timeline_gaps
from .utils import compact_ws


def _correction_kind_counts(corrections: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in corrections:
        kind = str(item.get("kind") or "glossary")
        counts[kind] += int(item.get("count") or 0)
    return dict(sorted(counts.items()))


def _text_tokens(text: str) -> list[str]:
    return re.findall(r"[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]+", text)


def _max_token_run(tokens: list[str]) -> int:
    longest = 0
    current = 0
    previous = None
    for token in tokens:
        if token == previous:
            current += 1
        else:
            current = 1
            previous = token
        longest = max(longest, current)
    return longest


def _high_frequency_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    most_common = Counter(tokens).most_common(1)[0][1]
    return round(most_common / len(tokens), 4)


def _timeline_metrics(segments: list[dict[str, Any]]) -> dict[str, Any]:
    timed: list[tuple[float, float]] = []
    for segment in segments:
        start = as_float(segment.get("start"))
        end = as_float(segment.get("end"))
        if start is None or end is None:
            continue
        if end > start >= 0:
            timed.append((start, end))
    if not timed:
        return {
            "duration_seconds": 0.0,
            "average_segment_duration": 0.0,
            "max_segment_duration": 0.0,
            "gap_count_over_30s": 0,
            "max_gap_seconds": 0.0,
        }
    timed.sort()
    durations = [end - start for start, end in timed]
    gaps: list[float] = []
    previous_end = timed[0][1]
    for start, end in timed[1:]:
        if start > previous_end:
            gaps.append(start - previous_end)
        previous_end = max(previous_end, end)
    return {
        "duration_seconds": round(
            max(end for _, end in timed) - min(start for start, _ in timed), 3
        ),
        "average_segment_duration": round(sum(durations) / len(durations), 3),
        "max_segment_duration": round(max(durations), 3),
        "gap_count_over_30s": sum(1 for gap in gaps if gap > 30.0),
        "max_gap_seconds": round(max(gaps) if gaps else 0.0, 3),
    }


def _segment_timing_metrics(segments: list[dict[str, Any]]) -> dict[str, Any]:
    segment_count = len(segments)
    explicit_count = 0
    invalid_count = 0
    non_monotonic_count = 0
    overlap_count = 0
    max_overlap_seconds = 0.0
    previous_start: float | None = None
    previous_end: float | None = None

    for segment in segments:
        timing_source = str(segment.get("_timing_source") or "explicit")
        has_timing = timing_source == "explicit"
        start = as_float(segment.get("start"))
        end = as_float(segment.get("end"))
        if start is None or end is None:
            start = 0.0
            end = 0.0
            has_timing = False

        if has_timing:
            explicit_count += 1
        if not has_timing or start < 0 or end <= start:
            invalid_count += 1
        if previous_start is not None and start < previous_start:
            non_monotonic_count += 1
        if previous_end is not None and start < previous_end:
            overlap_count += 1
            max_overlap_seconds = max(max_overlap_seconds, previous_end - start)
        previous_start = start
        previous_end = end

    missing_count = segment_count - explicit_count
    return {
        "timed_segment_count": explicit_count,
        "missing_timing_segment_count": missing_count,
        "invalid_timing_segment_count": invalid_count,
        "non_monotonic_timing_segment_count": non_monotonic_count,
        "overlapping_timing_segment_count": overlap_count,
        "max_timing_overlap_seconds": round(max_overlap_seconds, 3),
        "srt_vtt_compatible": bool(segment_count)
        and missing_count == 0
        and invalid_count == 0
        and non_monotonic_count == 0
        and overlap_count == 0,
    }


def build_quality_metrics(
    *,
    raw_segments: list[dict[str, Any]],
    corrected_segments: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    review: dict[str, Any],
) -> dict[str, Any]:
    corrected_texts = [compact_ws(str(seg.get("text", ""))) for seg in corrected_segments]
    raw_texts = [compact_ws(str(seg.get("text", ""))) for seg in raw_segments]
    corrected_nonempty = [text for text in corrected_texts if text]
    tokens = _text_tokens("\n".join(corrected_nonempty))
    correction_kind_counts = _correction_kind_counts(corrections)
    review_summary = review.get("summary", {}) if isinstance(review, dict) else {}

    timeline = _timeline_metrics(corrected_segments)
    corrected_char_count = sum(len(text) for text in corrected_nonempty)
    duration_minutes = max(timeline.get("duration_seconds", 0.0) / 60.0, 1e-6)
    coverage = coverage_metrics(corrected_segments)
    gaps = timeline_gaps(corrected_segments, min_gap=30.0)

    return {
        "raw_segment_count": len(raw_segments),
        "corrected_segment_count": len(corrected_segments),
        "empty_corrected_segment_count": len(corrected_texts) - len(corrected_nonempty),
        "raw_char_count": sum(len(text) for text in raw_texts),
        "corrected_char_count": corrected_char_count,
        "chars_per_minute": round(corrected_char_count / duration_minutes, 2)
        if timeline.get("duration_seconds")
        else 0.0,
        "correction_count": sum(int(item.get("count") or 0) for item in corrections),
        "correction_kind_counts": correction_kind_counts,
        "review_issue_count": int(review_summary.get("issue_count") or 0),
        "review_segment_issue_count": int(review_summary.get("segment_issue_count") or 0),
        "token_count": len(tokens),
        "max_repeated_token_run": _max_token_run(tokens),
        "top_token_ratio": _high_frequency_token_ratio(tokens),
        "timing": _segment_timing_metrics(corrected_segments),
        "timeline": {**timeline, "coverage": coverage, "large_gaps": gaps[:20]},
    }
