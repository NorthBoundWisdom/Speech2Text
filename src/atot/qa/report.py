from __future__ import annotations

from typing import Any

from ..utils import seconds_to_hms


def qa_to_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    checks = report.get("checks", {}) if isinstance(report.get("checks"), dict) else {}
    metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {}
    readable = metrics.get("readable", {}) if isinstance(metrics.get("readable"), dict) else {}
    lines = [
        "# QA Report",
        "",
        f"Status: {'PASS' if report.get('success') else 'FAIL'}",
        "",
        f"- Profile: {checks.get('profile', 'balanced')}",
        f"- Issues: {summary.get('issue_count', 0)}",
        f"- Blocking: {summary.get('blocking_issue_count', 0)}",
        f"- Warnings: {summary.get('warning_count', 0)}",
        f"- Suggested repair windows: {summary.get('repair_window_count', 0)}",
        f"- Segments: {metrics.get('segment_count', 0)}",
        f"- Visible chars: {metrics.get('visible_char_count', 0)}",
        f"- Readable paragraphs: {readable.get('paragraph_count', 0)}",
        f"- Readable punctuation / 1000 chars: {readable.get('punctuation_per_1000_chars', 0)}",
        "",
    ]
    issues = report.get("issues", []) if isinstance(report.get("issues"), list) else []
    for title, severity in (
        ("Blocking Issues", "blocker"),
        ("Warnings", "warning"),
        ("Review Items", "review"),
        ("Diagnostics", "diagnostic"),
    ):
        selected = [item for item in issues if item.get("severity") == severity]
        lines.extend([f"## {title}", ""])
        if not selected:
            lines.extend(["- None", ""])
            continue
        for item in selected:
            start = item.get("start")
            end = item.get("end")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                prefix = f"{seconds_to_hms(start)} -> {seconds_to_hms(end)}: "
            else:
                prefix = ""
            lines.append(f"- {prefix}{item.get('type')}: {item.get('message')}")
        lines.append("")
    repairs = (
        report.get("suggested_repairs", [])
        if isinstance(report.get("suggested_repairs"), list)
        else []
    )
    if repairs:
        lines.extend(["## Suggested Repairs", ""])
        for item in repairs:
            reasons = ", ".join(map(str, item.get("reasons") or [item.get("reason")]))
            window_id = item.get("id", "")
            prefix = f"{window_id}: " if window_id else ""
            lines.append(
                f"- {prefix}{seconds_to_hms(float(item['start']))} -> {seconds_to_hms(float(item['end']))}: {reasons}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"
