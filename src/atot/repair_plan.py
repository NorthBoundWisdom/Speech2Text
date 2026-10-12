from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .runinfo import now_iso


JsonReader = Callable[[Path], dict[str, Any]]
QaBuilder = Callable[[Path], dict[str, Any]]
SegmentReader = Callable[[Path], list[dict[str, Any]]]
DurationReader = Callable[[Path], float | None]


REPAIRABLE_ISSUE_TYPES = {
    "large_timing_gap",
    "long_segment",
    "segment_overlap",
    "repeated_phrase",
    "adjacent_duplicate_segment",
    "low_avg_logprob_segment",
    "high_compression_ratio_segment",
    "high_no_speech_prob_segment",
}


def window_from_issue(
    issue: dict[str, Any],
    padding: float,
    *,
    segments: list[dict[str, Any]],
    include_warning_windows: bool,
) -> dict[str, Any] | None:
    severity = str(issue.get("severity") or "warning")
    if severity != "blocker" and not include_warning_windows:
        return None
    if not bool(issue.get("repairable")) and issue.get("type") not in REPAIRABLE_ISSUE_TYPES:
        return None
    start = issue.get("start")
    end = issue.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        index = issue.get("index")
        if isinstance(index, int) and 0 <= index < len(segments):
            segment = segments[index]
            try:
                start = float(segment.get("start", 0.0))
                end = float(segment.get("end", start + 0.01))
            except (TypeError, ValueError):
                return None
        else:
            return None
    return {
        "type": "rerun_window",
        "start": max(0.0, float(start) - padding),
        "end": max(float(start), float(end) + padding),
        "reason": issue.get("type"),
        "severity": severity,
        "source_issue": {k: v for k, v in issue.items() if k not in {"text"}},
    }


def split_window(window: dict[str, Any], *, max_window_seconds: float) -> list[dict[str, Any]]:
    if max_window_seconds <= 0:
        return [window]
    start = float(window["start"])
    end = float(window["end"])
    if end - start <= max_window_seconds:
        return [window]
    pieces: list[dict[str, Any]] = []
    cursor = start
    while cursor < end:
        piece_end = min(end, cursor + max_window_seconds)
        pieces.append({**window, "start": cursor, "end": piece_end})
        cursor = piece_end
    return pieces


def merge_windows(
    windows: list[dict[str, Any]], *, merge_gap_seconds: float = 2.0
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for window in sorted(windows, key=lambda item: (float(item["start"]), float(item["end"]))):
        source_issue_ids = [
            str(item)
            for item in window.get("source_issue_ids", [])
            if isinstance(window.get("source_issue_ids"), list) and item
        ]
        if not merged or float(window["start"]) > float(merged[-1]["end"]) + merge_gap_seconds:
            merged.append(
                {
                    **window,
                    "reasons": [str(window.get("reason"))],
                    "source_issues": [window.get("source_issue", {})],
                    "source_issue_ids": source_issue_ids,
                }
            )
            continue
        merged[-1]["end"] = max(float(merged[-1]["end"]), float(window["end"]))
        reason = str(window.get("reason"))
        if reason not in merged[-1]["reasons"]:
            merged[-1]["reasons"].append(reason)
        merged[-1].setdefault("source_issues", []).append(window.get("source_issue", {}))
        ids = merged[-1].setdefault("source_issue_ids", [])
        for issue_id in source_issue_ids:
            if issue_id not in ids:
                ids.append(issue_id)
        if str(window.get("severity")) == "blocker":
            merged[-1]["severity"] = "blocker"
    for index, window in enumerate(merged, start=1):
        window["id"] = f"repair-window-{index:04d}"
        window["duration"] = round(float(window["end"]) - float(window["start"]), 3)
        ids = list(window.get("source_issue_ids") or [])
        for source_issue in window.get("source_issues", []):
            if (
                isinstance(source_issue, dict)
                and source_issue.get("id")
                and str(source_issue["id"]) not in ids
            ):
                ids.append(str(source_issue["id"]))
        window["source_issue_ids"] = ids
    return merged


def clip_windows_to_audio_duration(
    windows: list[dict[str, Any]], audio_duration: float | None
) -> list[dict[str, Any]]:
    if audio_duration is None or audio_duration <= 0:
        return windows
    clipped: list[dict[str, Any]] = []
    for window in windows:
        start = min(max(0.0, float(window["start"])), audio_duration)
        end = min(max(start, float(window["end"])), audio_duration)
        if end <= start:
            continue
        clipped.append({**window, "start": start, "end": end})
    for index, window in enumerate(clipped, start=1):
        window["id"] = f"repair-window-{index:04d}"
        window["duration"] = round(float(window["end"]) - float(window["start"]), 3)
    return clipped


def build_repair_plan(
    output_dir: str | Path,
    *,
    details_dir: Callable[[Path], Path],
    read_json_object: JsonReader,
    build_qa_report: QaBuilder,
    segments_from_output: SegmentReader,
    audio_duration_from_output: DurationReader,
    window_padding: float = 15.0,
    max_window_seconds: float = 300.0,
    include_warning_windows: bool = True,
) -> dict[str, Any]:
    base = Path(output_dir).expanduser().resolve()
    qa_path = details_dir(base) / "qa.json"
    qa = read_json_object(qa_path) or build_qa_report(base)
    current_segments = segments_from_output(base)
    suggested = qa.get("suggested_repairs") if isinstance(qa.get("suggested_repairs"), list) else []
    windows: list[dict[str, Any]] = []
    if suggested:
        for item in suggested:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "blocker")
            if severity != "blocker" and not include_warning_windows:
                continue
            if not isinstance(item.get("start"), (int, float)) or not isinstance(
                item.get("end"), (int, float)
            ):
                continue
            windows.extend(
                split_window(
                    {**item, "type": "rerun_window"}, max_window_seconds=max_window_seconds
                )
            )
    else:
        for issue in qa.get("issues", []):
            if not isinstance(issue, dict):
                continue
            window = window_from_issue(
                issue,
                window_padding,
                segments=current_segments,
                include_warning_windows=include_warning_windows,
            )
            if window is not None:
                windows.extend(split_window(window, max_window_seconds=max_window_seconds))
    non_repairable = [
        {k: v for k, v in issue.items() if k not in {"text"}}
        for issue in qa.get("issues", [])
        if isinstance(issue, dict)
        and issue.get("severity") == "blocker"
        and not issue.get("repairable")
    ]
    merged_windows = merge_windows(windows)
    return {
        "created_at": now_iso(),
        "strategy": "bad-segments",
        "qa_success": qa.get("success"),
        "qa_summary": qa.get("summary", {}),
        "windows": clip_windows_to_audio_duration(merged_windows, audio_duration_from_output(base)),
        "non_repairable_blockers": non_repairable,
    }
