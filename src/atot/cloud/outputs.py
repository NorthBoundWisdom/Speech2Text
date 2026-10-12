from __future__ import annotations

from pathlib import Path
from typing import Any

from . import review as _review_outputs
from . import summary_outputs as _summary_outputs
from .client import call_openai_compatible_chat, call_openai_compatible_chat_stream
from .output_state import CloudOutputOptions


_direct_readable_allowed = _summary_outputs._direct_readable_allowed
_audio_duration_seconds = _summary_outputs._audio_duration_seconds
_auto_direct_readable_allowed = _summary_outputs._auto_direct_readable_allowed
_hms_to_seconds = _summary_outputs._hms_to_seconds
_transcript_lines = _summary_outputs._transcript_lines
_chapterize = _summary_outputs._chapterize
_chapter_from_lines = _summary_outputs._chapter_from_lines
_source_chunks_for_range = _summary_outputs._source_chunks_for_range
_range_boundary_seconds = _summary_outputs._range_boundary_seconds
_input_bundle = _summary_outputs._input_bundle
_json_section = _summary_outputs._json_section
_short_text = _summary_outputs._short_text
_limited_text_section = _summary_outputs._limited_text_section
_compact_manifest_context = _summary_outputs._compact_manifest_context
_compact_qa_context = _summary_outputs._compact_qa_context
_compact_review_context = _summary_outputs._compact_review_context
_compact_chunk_summary = _summary_outputs._compact_chunk_summary
_readable_transcript_text = _summary_outputs._readable_transcript_text
_chunk_user_content_for_cloud = _summary_outputs._chunk_user_content_for_cloud
_write_chunk_summaries = _summary_outputs._write_chunk_summaries
_episode_input_from_chunk_summaries = _summary_outputs._episode_input_from_chunk_summaries
_fallback_summary_from_chunk_summaries = _summary_outputs._fallback_summary_from_chunk_summaries
_collect_uncertainties = _summary_outputs._collect_uncertainties
_write_uncertainty_report = _summary_outputs._write_uncertainty_report
_term_text = _summary_outputs._term_text
_write_terms_outputs = _summary_outputs._write_terms_outputs
_strip_outer_markdown_fence = _summary_outputs._strip_outer_markdown_fence

ASCII_TERM_RE = _review_outputs.ASCII_TERM_RE
_maybe_call_cloud = _review_outputs._maybe_call_cloud
_write_glossary_review_queue = _review_outputs._write_glossary_review_queue
_write_glossary_editor_items = _review_outputs._write_glossary_editor_items
_term_hit_count = _review_outputs._term_hit_count
_normalize_polish_patch_payload = _review_outputs._normalize_polish_patch_payload
_matching_patch_line = _review_outputs._matching_patch_line
read_json_from_text = _review_outputs.read_json_from_text
read_json_string = _review_outputs.read_json_string


def write_cloud_short_title(options: CloudOutputOptions, *, force: bool = False) -> dict[str, Any]:
    return _summary_outputs.write_cloud_short_title(
        options,
        force=force,
        call_chat=call_openai_compatible_chat,
    )


def write_cloud_summary(options: CloudOutputOptions) -> dict[str, Any]:
    return _summary_outputs.write_cloud_summary(
        options,
        call_chat=call_openai_compatible_chat,
        stream_chat=call_openai_compatible_chat_stream,
    )


def write_cloud_glossary_review(options: CloudOutputOptions) -> dict[str, Any]:
    return _review_outputs.write_cloud_glossary_review(
        options,
        call_chat=call_openai_compatible_chat,
    )


def write_cloud_polish_suggestions(options: CloudOutputOptions) -> dict[str, Any]:
    return _review_outputs.write_cloud_polish_suggestions(
        options,
        call_chat=call_openai_compatible_chat,
    )


def apply_cloud_patches(
    output_dir: str | Path, patches_path: str | Path, *, mode: str = "reviewed"
) -> dict[str, Any]:
    return _review_outputs.apply_cloud_patches(output_dir, patches_path, mode=mode)
