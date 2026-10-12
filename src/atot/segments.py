from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from .utils import compact_ws, seconds_to_hms


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def segment_text(segment: dict[str, Any]) -> str:
    return compact_ws(str(segment.get("text", "")))


def segment_start(segment: dict[str, Any], *, default: float = 0.0) -> float:
    value = as_float(segment.get("start"), default)
    return float(default if value is None else value)


def segment_end(segment: dict[str, Any], *, default_start: float | None = None) -> float:
    start = segment_start(segment) if default_start is None else float(default_start)
    value = as_float(segment.get("end"), start + 0.01)
    return float(start + 0.01 if value is None else value)


def segment_midpoint(segment: dict[str, Any]) -> float:
    start = segment_start(segment)
    end = segment_end(segment, default_start=start)
    return (start + end) / 2.0


def segment_duration(segment: dict[str, Any]) -> float:
    start = segment_start(segment)
    end = segment_end(segment, default_start=start)
    return max(0.0, end - start)


def normalize_segment(
    segment: dict[str, Any], *, index: int | None = None, min_duration: float = 0.01
) -> dict[str, Any] | None:
    text = segment_text(segment)
    if not text:
        return None
    start = max(0.0, segment_start(segment))
    end = max(start + max(min_duration, 0.001), segment_end(segment, default_start=start))
    item = deepcopy(segment)
    if index is not None:
        item["id"] = index
    item["start"] = start
    item["end"] = end
    item["text"] = text
    return item


def canonicalize_segments(
    segments: list[dict[str, Any]],
    *,
    sort: bool = True,
    enforce_monotonic: bool = True,
    drop_empty: bool = True,
    max_end: float | None = None,
) -> list[dict[str, Any]]:
    """Return transcript segments in a stable, writer-friendly shape.

    The function is deliberately content-agnostic: it only normalizes whitespace,
    IDs, numeric timestamps, ordering, and optional timeline bounds. It does not
    apply vocabulary or episode-specific corrections.
    """
    candidates = (
        sorted(segments, key=lambda s: (segment_start(s), segment_end(s)))
        if sort
        else list(segments)
    )
    normalized: list[dict[str, Any]] = []
    previous_end = 0.0
    for raw in candidates:
        item = normalize_segment(raw)
        if item is None:
            if drop_empty:
                continue
            item = deepcopy(raw)
            item["text"] = ""
            item["start"] = max(0.0, segment_start(raw))
            item["end"] = max(item["start"] + 0.01, segment_end(raw, default_start=item["start"]))
        if max_end is not None:
            if float(item["start"]) > max_end:
                continue
            item["end"] = min(float(item["end"]), max(float(item["start"]) + 0.01, max_end))
        if enforce_monotonic:
            item["start"] = max(previous_end, float(item["start"]))
            item["end"] = max(float(item["start"]) + 0.01, float(item["end"]))
            previous_end = float(item["end"])
        normalized.append(item)
    for index, item in enumerate(normalized):
        item["id"] = index
    return normalized


def segment_plain_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(text for text in (segment_text(segment) for segment in segments) if text)


def segment_digest(segments: list[dict[str, Any]]) -> str:
    canonical = [
        {
            "start": round(segment_start(segment), 3),
            "end": round(segment_end(segment), 3),
            "text": segment_text(segment),
        }
        for segment in segments
    ]
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def timeline_gaps(
    segments: list[dict[str, Any]],
    *,
    audio_duration: float | None = None,
    min_gap: float = 0.0,
) -> list[dict[str, Any]]:
    timed: list[tuple[float, float]] = []
    for segment in segments:
        start = segment_start(segment)
        end = segment_end(segment, default_start=start)
        if end > start >= 0:
            timed.append((start, end))
    if not timed:
        return []
    timed.sort()
    gaps: list[dict[str, Any]] = []
    previous_end = 0.0
    for start, end in timed:
        if start - previous_end > min_gap:
            gaps.append(
                {
                    "start": round(previous_end, 3),
                    "end": round(start, 3),
                    "duration": round(start - previous_end, 3),
                    "time": seconds_to_hms(previous_end),
                }
            )
        previous_end = max(previous_end, end)
    if (
        audio_duration is not None
        and audio_duration > previous_end
        and audio_duration - previous_end > min_gap
    ):
        gaps.append(
            {
                "start": round(previous_end, 3),
                "end": round(audio_duration, 3),
                "duration": round(audio_duration - previous_end, 3),
                "time": seconds_to_hms(previous_end),
            }
        )
    return gaps


def coverage_metrics(
    segments: list[dict[str, Any]], *, audio_duration: float | None = None
) -> dict[str, Any]:
    if audio_duration is None or audio_duration <= 0:
        ends = [segment_end(segment) for segment in segments if segment_duration(segment) > 0]
        audio_duration = max(ends) if ends else 0.0
    if audio_duration <= 0:
        return {
            "audio_duration": 0.0,
            "covered_seconds": 0.0,
            "uncovered_seconds": 0.0,
            "coverage_ratio": 0.0,
        }

    intervals: list[tuple[float, float]] = []
    for segment in segments:
        start = max(0.0, min(audio_duration, segment_start(segment)))
        end = max(start, min(audio_duration, segment_end(segment, default_start=start)))
        if end > start:
            intervals.append((start, end))
    if not intervals:
        return {
            "audio_duration": round(audio_duration, 3),
            "covered_seconds": 0.0,
            "uncovered_seconds": round(audio_duration, 3),
            "coverage_ratio": 0.0,
        }
    intervals.sort()
    merged: list[list[float]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    covered = sum(end - start for start, end in merged)
    uncovered = max(0.0, audio_duration - covered)
    return {
        "audio_duration": round(audio_duration, 3),
        "covered_seconds": round(covered, 3),
        "uncovered_seconds": round(uncovered, 3),
        "coverage_ratio": round(covered / audio_duration, 4),
    }
