from __future__ import annotations

from typing import Any

from .policy import REPAIRABLE_BLOCKER_TYPES, REPAIRABLE_WARNING_TYPES


def is_repairable_issue_type(issue_type: str, severity: str) -> bool:
    """Return whether an issue type should produce a repair window."""
    if severity == "blocker":
        return issue_type in REPAIRABLE_BLOCKER_TYPES
    if severity == "warning":
        return issue_type in REPAIRABLE_WARNING_TYPES
    return False


def _source_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in issue.items() if key != "text"}


def repair_windows(
    issues: list[dict[str, Any]],
    *,
    padding: float = 15.0,
    max_window_seconds: float = 300.0,
    merge_gap_seconds: float = 2.0,
) -> list[dict[str, Any]]:
    """Build merged repair windows from repairable QA issues."""
    windows: list[dict[str, Any]] = []
    for item in issues:
        severity = str(item.get("severity") or "warning")
        issue_type = str(item.get("type") or "")
        if not bool(item.get("repairable")) and not is_repairable_issue_type(issue_type, severity):
            continue
        start = item.get("start")
        end = item.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        padded_start = max(0.0, float(start) - padding)
        padded_end = max(float(start), float(end) + padding)
        if max_window_seconds > 0 and padded_end - padded_start > max_window_seconds:
            cursor = padded_start
            while cursor < padded_end:
                window_end = min(padded_end, cursor + max_window_seconds)
                windows.append(
                    {
                        "type": "rerun_window",
                        "start": cursor,
                        "end": window_end,
                        "reason": issue_type,
                        "severity": severity,
                        "source_issue": _source_issue(item),
                    }
                )
                cursor = window_end
            continue
        windows.append(
            {
                "type": "rerun_window",
                "start": padded_start,
                "end": padded_end,
                "reason": issue_type,
                "severity": severity,
                "source_issue": _source_issue(item),
            }
        )
    if not windows:
        return []
    merged: list[dict[str, Any]] = []
    for window in sorted(windows, key=lambda item: (float(item["start"]), float(item["end"]))):
        if not merged or float(window["start"]) > float(merged[-1]["end"]) + merge_gap_seconds:
            merged.append(
                {
                    **window,
                    "reasons": [str(window.get("reason"))],
                    "source_issues": [window.get("source_issue", {})],
                }
            )
            continue
        merged[-1]["end"] = max(float(merged[-1]["end"]), float(window["end"]))
        reason = str(window.get("reason"))
        if reason not in merged[-1]["reasons"]:
            merged[-1]["reasons"].append(reason)
        merged[-1].setdefault("source_issues", []).append(window.get("source_issue", {}))
        if str(window.get("severity")) == "blocker":
            merged[-1]["severity"] = "blocker"
    for index, window in enumerate(merged, start=1):
        window["id"] = f"repair-window-{index:04d}"
        window["duration"] = round(float(window["end"]) - float(window["start"]), 3)
        window["source_issue_ids"] = [
            str(item.get("id"))
            for item in window.get("source_issues", [])
            if isinstance(item, dict) and item.get("id")
        ]
    return merged
