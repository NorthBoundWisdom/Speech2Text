from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from . import chunking as _chunk_outputs
from . import publish as _publish_outputs
from . import summary as _summary_outputs
from .client import call_openai_compatible_chat, call_openai_compatible_chat_stream
from .output_state import CloudOutputOptions, _input_dir, _read_json_object
from ..utils import compact_ws, read_text, seconds_to_hms


TIMESTAMP_LINE_RE = re.compile(
    r"^\[(?P<start>\d{2}:\d{2}:\d{2})(?:\s*->\s*(?P<end>\d{2}:\d{2}:\d{2}))?\]\s*(?P<text>.*)$"
)
LONG_DIRECT_AUDIO_SECONDS = 95 * 60


def _direct_readable_allowed(options: CloudOutputOptions, transcript: str) -> bool:
    if options.allow_long_direct:
        return True
    return len(transcript) <= max(0, int(options.direct_readable_char_limit))


def _audio_duration_seconds(output_dir: Path) -> float | None:
    for path in (output_dir / "cloud" / "input" / "manifest.json", output_dir / "run.json"):
        payload = _read_json_object(path)
        try:
            duration = float(payload.get("audio_duration", 0.0))
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return None


def _auto_direct_readable_allowed(
    options: CloudOutputOptions, output_dir: Path, transcript: str
) -> bool:
    duration = _audio_duration_seconds(output_dir)
    if (
        duration is not None
        and duration >= LONG_DIRECT_AUDIO_SECONDS
        and not options.allow_long_direct
    ):
        return False
    return _direct_readable_allowed(options, transcript)


def _hms_to_seconds(value: str) -> float:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return float(hours * 3600 + minutes * 60 + seconds)


def _transcript_lines(output_dir: Path) -> list[dict[str, Any]]:
    transcript = read_text(_input_dir(output_dir) / "transcript.for_cloud.md") or ""
    lines: list[dict[str, Any]] = []
    for index, line in enumerate(transcript.splitlines(), start=1):
        match = TIMESTAMP_LINE_RE.match(line.strip())
        if not match:
            continue
        text = compact_ws(match.group("text"))
        if not text:
            continue
        lines.append(
            {
                "start": _hms_to_seconds(match.group("start")),
                "end": _hms_to_seconds(match.group("end") or match.group("start")),
                "time": match.group("start"),
                "segment_id": f"segment_{index:06d}",
                "text": text,
            }
        )
    return lines


def _chapterize(
    output_dir: Path, lines: list[dict[str, Any]], *, bucket_seconds: float = 600.0
) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_bucket: int | None = None
    for line in lines:
        bucket = int(float(line["start"]) // bucket_seconds)
        if current and bucket != current_bucket:
            chapters.append(_chapter_from_lines(output_dir, current))
            current = []
        current_bucket = bucket
        current.append(line)
    if current:
        chapters.append(_chapter_from_lines(output_dir, current))
    return chapters


def _chapter_from_lines(output_dir: Path, lines: list[dict[str, Any]]) -> dict[str, Any]:
    start = float(lines[0]["start"])
    end = float(lines[-1]["end"])
    text = "".join(str(item["text"]) for item in lines)
    title = compact_ws(text[:28]) or "Segment"
    return {
        "start": seconds_to_hms(start),
        "end": seconds_to_hms(end),
        "title": title,
        "summary": compact_ws(text[:120]),
        "source_chunks": _source_chunks_for_range(output_dir, start=start, end=end),
        "source_segment_ids": [str(item["segment_id"]) for item in lines if item.get("segment_id")],
    }


def _source_chunks_for_range(output_dir: Path, *, start: float, end: float) -> list[str]:
    manifest = _read_json_object(_input_dir(output_dir) / "manifest.json")
    text_chunk_ranges = manifest.get("text_chunk_ranges")
    ranges = text_chunk_ranges if isinstance(text_chunk_ranges, list) else []
    matches: list[str] = []
    for item in ranges:
        if not isinstance(item, dict):
            continue
        try:
            chunk_start = _range_boundary_seconds(item, "start")
            chunk_end = _range_boundary_seconds(item, "end")
        except (TypeError, ValueError):
            continue
        if chunk_end >= start and chunk_start <= end:
            path = str(item.get("path") or "")
            if path:
                matches.append(path)
    return matches


def _range_boundary_seconds(item: dict[str, Any], key: str) -> float:
    seconds_key = f"{key}_seconds"
    if seconds_key in item:
        return float(item[seconds_key])
    return _hms_to_seconds(str(item[key]))


def _input_bundle(output_dir: Path, *, include_transcript: bool = True) -> str:
    input_dir = _input_dir(output_dir)
    parts: list[str] = []
    names = [
        "manifest.json",
        "qa.for_cloud.md",
        "review.for_cloud.md",
        "glossary.for_cloud.json",
        "topic.for_cloud.md",
    ]
    if include_transcript:
        names.append("transcript.for_cloud.md")
    for name in names:
        path = input_dir / name
        text = read_text(path)
        if text:
            parts.append(f"## {name}\n\n{text}")
    return "\n\n".join(parts).strip()


_json_section = _summary_outputs._json_section
_short_text = _summary_outputs._short_text
_limited_text_section = _summary_outputs._limited_text_section
_compact_manifest_context = _summary_outputs._compact_manifest_context
_compact_qa_context = _summary_outputs._compact_qa_context
_compact_review_context = _summary_outputs._compact_review_context
_compact_chunk_summary = _summary_outputs._compact_chunk_summary
_episode_input_from_chunk_summaries = _summary_outputs._episode_input_from_chunk_summaries
_fallback_summary_from_chunk_summaries = _summary_outputs._fallback_summary_from_chunk_summaries
_collect_uncertainties = _publish_outputs._collect_uncertainties
_write_uncertainty_report = _publish_outputs._write_uncertainty_report
_term_text = _publish_outputs._term_text
_write_terms_outputs = _publish_outputs._write_terms_outputs
_strip_outer_markdown_fence = _publish_outputs._strip_outer_markdown_fence


def _readable_transcript_text(output_dir: Path) -> str:
    candidates = [
        output_dir / "transcript.readable.md",
        output_dir / "cloud" / "transcript.readable.md",
        output_dir / "transcript.corrected.txt",
        output_dir / "transcript.corrected.txt",
    ]
    for path in candidates:
        text = read_text(path)
        if text:
            return text
    raise FileNotFoundError(f"Missing readable transcript under {output_dir}")


def _chunk_user_content_for_cloud(text: str, *, max_chars: int = 7_500) -> str:
    return _chunk_outputs._chunk_user_content_for_cloud(text, max_chars=max_chars)


def _write_chunk_summaries(
    output_dir: Path,
    *,
    options: CloudOutputOptions,
    source: str,
    call_chat: _summary_outputs.ChatCaller,
) -> tuple[list[str], list[str]]:
    return _chunk_outputs.write_chunk_summaries(
        output_dir,
        options=options,
        source=source,
        call_chat=call_chat,
    )


def write_cloud_short_title(
    options: CloudOutputOptions,
    *,
    force: bool = False,
    call_chat: _summary_outputs.ChatCaller | None = None,
) -> dict[str, Any]:
    return _publish_outputs.write_cloud_short_title(
        options,
        force=force,
        call_chat=call_chat or call_openai_compatible_chat,
    )


def write_cloud_summary(
    options: CloudOutputOptions,
    *,
    call_chat: _summary_outputs.ChatCaller | None = None,
    stream_chat: _summary_outputs.StreamCaller | None = None,
) -> dict[str, Any]:
    active_call_chat = call_chat or call_openai_compatible_chat
    active_stream_chat = stream_chat or call_openai_compatible_chat_stream
    dependencies = _summary_outputs.SummaryDependencies(
        readable_transcript_text=_readable_transcript_text,
        direct_readable_allowed=_direct_readable_allowed,
        auto_direct_readable_allowed=_auto_direct_readable_allowed,
        write_chunk_summaries=lambda output_dir: _write_chunk_summaries(
            output_dir,
            options=options,
            source="local_scaffold",
            call_chat=active_call_chat,
        ),
        write_uncertainty_report=_write_uncertainty_report,
        write_terms_outputs=_write_terms_outputs,
        transcript_lines=_transcript_lines,
        chapterize=lambda output_dir, lines: _chapterize(output_dir, lines),
        episode_input_from_chunk_summaries=_episode_input_from_chunk_summaries,
        input_bundle=_input_bundle,
        fallback_summary_from_chunk_summaries=lambda output_dir, partial: (
            _fallback_summary_from_chunk_summaries(
                output_dir,
                partial=partial,
            )
        ),
        write_chapter_outputs=_publish_outputs._write_chapter_outputs,
        write_publish_outputs=lambda output_dir, summary, chapters: (
            _publish_outputs._write_publish_outputs(
                output_dir,
                summary=summary,
                chapters=chapters,
            )
        ),
        write_short_title=lambda title_options, **kwargs: write_cloud_short_title(
            title_options,
            call_chat=active_call_chat,
            **kwargs,
        ),
    )
    return _summary_outputs.write_cloud_summary(
        options,
        dependencies,
        call_chat=active_call_chat,
        stream_chat=active_stream_chat,
    )
