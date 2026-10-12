from __future__ import annotations

from typing import Any, Callable

from ..numeric import as_float
from .policy import IssueType
from ..utils import seconds_to_hms

IssueFactory = Callable[..., dict[str, Any]]


def segment_timing_issues(
    segments: list[dict[str, Any]],
    *,
    max_gap: float,
    max_segment_duration: float,
    issue_factory: IssueFactory,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    previous_end: float | None = None
    for index, segment in enumerate(segments):
        start = as_float(segment.get("start"))
        end = as_float(segment.get("end"))
        if start is None or end is None:
            issues.append(
                issue_factory(
                    "blocker",
                    "invalid_segment_timing",
                    "Segment timing must be numeric",
                    index=index,
                )
            )
            continue
        if start < 0:
            issues.append(
                issue_factory(
                    "blocker",
                    "negative_segment_start",
                    "Segment start is negative",
                    index=index,
                    start=start,
                )
            )
        if end <= start:
            issues.append(
                issue_factory(
                    "blocker",
                    "non_positive_segment_duration",
                    "Segment end must be greater than start",
                    index=index,
                    start=start,
                    end=end,
                )
            )
        duration = end - start
        if duration > max_segment_duration:
            issues.append(
                issue_factory(
                    "blocker",
                    IssueType.LONG_SEGMENT,
                    f"Segment duration exceeds {max_segment_duration:.1f}s",
                    index=index,
                    start=start,
                    end=end,
                    time=seconds_to_hms(start),
                    duration=round(duration, 3),
                    repairable=True,
                )
            )
        if previous_end is not None:
            if start < previous_end:
                issues.append(
                    issue_factory(
                        "blocker",
                        IssueType.SEGMENT_OVERLAP,
                        "Segment starts before previous segment ends",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        previous_end=previous_end,
                        repairable=True,
                    )
                )
            gap = start - previous_end
            if gap > max_gap:
                issues.append(
                    issue_factory(
                        "blocker",
                        IssueType.LARGE_TIMING_GAP,
                        f"Large gap before segment {index}",
                        index=index,
                        start=previous_end,
                        end=start,
                        time=seconds_to_hms(previous_end),
                        duration=round(gap, 3),
                        repairable=True,
                    )
                )
        previous_end = max(previous_end or 0.0, end)
    return issues
