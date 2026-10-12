from __future__ import annotations

from pathlib import Path
from typing import Any

from .builder import build_qa_report as build_qa_report
from .builder import details_dir as _details_dir
from .builder import resolve_output_dir
from .report import qa_to_markdown
from ..utils import write_json_atomic, write_text_atomic

__all__ = ["build_qa_report", "qa_to_markdown", "resolve_output_dir", "run_qa", "write_qa_report"]


def write_qa_report(output_dir: str | Path, report: dict[str, Any]) -> None:
    details = _details_dir(resolve_output_dir(output_dir))
    write_json_atomic(details / "qa.json", report)
    write_text_atomic(details / "qa.md", qa_to_markdown(report))


def run_qa(
    output_dir: str | Path,
    *,
    profile: str | None = "balanced",
    qa_config: str | Path | None = None,
    max_gap: float | None = None,
    max_segment_duration: float | None = None,
    max_subtitle_chars: int | None = None,
    max_subtitle_line_chars: int | None = None,
    fail_on_srt_error: bool = True,
    write_report: bool = True,
) -> dict[str, Any]:
    """Run QA and optionally write ``qa.json`` and ``qa.md``.

    Args:
        output_dir: Output bundle directory to inspect.
        profile: QA profile name.
        qa_config: Optional QA settings file.
        max_gap: Override for maximum allowed timeline gap in seconds.
        max_segment_duration: Override for maximum segment duration.
        max_subtitle_chars: Override for subtitle cue character limit.
        max_subtitle_line_chars: Override for subtitle line character limit.
        fail_on_srt_error: Whether SRT blocker issues fail the report.
        write_report: Whether to persist the JSON and Markdown QA reports.

    Returns:
        The QA report dictionary produced by ``build_qa_report``.
    """

    report = build_qa_report(
        output_dir,
        profile=profile,
        qa_config=qa_config,
        max_gap=max_gap,
        max_segment_duration=max_segment_duration,
        max_subtitle_chars=max_subtitle_chars,
        max_subtitle_line_chars=max_subtitle_line_chars,
        fail_on_srt_error=fail_on_srt_error,
    )
    if write_report:
        write_qa_report(output_dir, report)
    return report
