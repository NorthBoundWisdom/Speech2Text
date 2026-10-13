from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .client import (
    CloudClientOptions,
    call_openai_compatible_chat,
    call_openai_compatible_chat_stream,
    read_prompt_template,
)
from .metadata import episode_title_for_output
from .output_state import (
    CloudOutputOptions,
    _clear_cloud_summary_outputs,
    _cloud_dir,
    _cloud_summary_lock,
    _input_dir,
    _read_json_object,
    _record_cloud_outputs,
)
from .publish import _strip_outer_markdown_fence
from ..languages import output_language_instruction
from ..progress import update_cloud_summary_state
from ..utils import compact_ws, read_text, relative_posix_path, write_text_atomic


ChatCaller = Callable[..., str]
StreamCaller = Callable[..., str]
FINAL_CONTEXT_TEXT_LIMIT = 12_000
FINAL_CONTEXT_ITEM_LIMIT = 12
GENERIC_SUMMARY_HEADING_MARKERS = ("播客结构化总结", "结构化总结", "中文播客摘要")
SUMMARY_SECTION_MARKERS = ("主要内容", "核心观点", "关键要点", "重要名词", "结论", "金句")


def _summary_prompt_with_title_instruction(prompt: str) -> str:
    return (
        prompt.strip() + "\n\nThe first line must be '# <specific episode summary title>', "
        "followed by a blank line and the Markdown body. Do not use a generic title such as Summary."
    ).strip()


@dataclass(frozen=True)
class SummaryDependencies:
    """Callbacks used by cloud summary generation to read and write artifacts."""

    readable_transcript_text: Callable[[Path], str]
    direct_readable_allowed: Callable[[CloudOutputOptions, str], bool]
    auto_direct_readable_allowed: Callable[[CloudOutputOptions, Path, str], bool]
    write_chunk_summaries: Callable[[Path], tuple[list[str], list[str]]]
    write_uncertainty_report: Callable[[Path], list[str]]
    write_terms_outputs: Callable[[Path], list[str]]
    transcript_lines: Callable[[Path], list[dict[str, Any]]]
    chapterize: Callable[[Path, list[dict[str, Any]]], list[dict[str, Any]]]
    episode_input_from_chunk_summaries: Callable[[Path], str]
    input_bundle: Callable[[Path], str]
    fallback_summary_from_chunk_summaries: Callable[[Path, bool], str]
    write_chapter_outputs: Callable[[Path, list[dict[str, Any]], str], None]
    write_publish_outputs: Callable[[Path, str, list[dict[str, Any]]], list[str]]
    write_short_title: Callable[..., dict[str, Any]]


def _maybe_call_cloud(
    options: CloudOutputOptions,
    *,
    default_prompt: str,
    fallback_prompt: Path,
    user_content: str,
    audit_name: str,
    call_chat: ChatCaller | None = None,
    prefer_fallback_prompt: bool = True,
    allow_custom_prompt: bool = True,
    prompt_transform: Callable[[str], str] | None = None,
) -> str | None:
    if not options.call_api:
        return None
    if allow_custom_prompt and options.prompt_file:
        prompt = read_prompt_template(options.prompt_file)
    elif prefer_fallback_prompt and fallback_prompt.exists():
        prompt = read_prompt_template(fallback_prompt)
    else:
        prompt = default_prompt
    if prompt_transform:
        prompt = prompt_transform(prompt)
    return (call_chat or call_openai_compatible_chat)(
        system_prompt=prompt + "\n\n" + output_language_instruction(options.output_language),
        user_content=user_content,
        options=CloudClientOptions(),
        audit_path=_cloud_dir(options.output_dir.expanduser().resolve()) / audit_name,
    )


def _summary_prompt_for_direct_readable(options: CloudOutputOptions) -> str:
    prompt = (
        read_prompt_template(options.prompt_file)
        if options.prompt_file
        else (
            "Summarize only the supplied transcript as structured Markdown. Cover main ideas, evidence, "
            "key points, unfamiliar terms, conclusions, and memorable quotes. Do not add external facts "
            "or output a reasoning trace."
        )
    )
    return (
        _summary_prompt_with_title_instruction(prompt)
        + "\n\n"
        + output_language_instruction(options.output_language)
    )


def _heading_text(line: str) -> str:
    return compact_ws(line.lstrip("#").strip(" #\"'“”‘’`"))


def _summary_heading_is_generic(line: str) -> bool:
    heading = _heading_text(line)
    if not heading:
        return True
    if any(marker in heading for marker in GENERIC_SUMMARY_HEADING_MARKERS):
        return True
    lower = heading.casefold()
    return lower == "work" or bool(re.search(r"(^|[《「:：\s])work([》」\s]|$)", lower))


def _summary_title_from_content(summary_text: str) -> str:
    for raw_line in summary_text.splitlines():
        line = compact_ws(raw_line.strip(" -*\t"))
        if not line or line.startswith("#") or line.startswith("```") or line.startswith("|"):
            continue
        if any(marker in line[:16] for marker in SUMMARY_SECTION_MARKERS):
            continue
        candidate = re.split(r"[。！？!?；;]\s*", line, maxsplit=1)[0]
        candidate = re.sub(
            r"^本期(?:节目|播客|访谈|内容)?(?:主要)?(?:围绕|讨论|聚焦|是|为)?", "", candidate
        )
        candidate = compact_ws(candidate).strip("，,：: ")
        if len(candidate) >= 6:
            return candidate[:36].strip()
    return ""


def _summary_heading_title(output_dir: Path, summary_text: str) -> str:
    episode_title = episode_title_for_output(output_dir)
    content_title = _summary_title_from_content(summary_text)
    if episode_title and episode_title != output_dir.name:
        return episode_title
    return content_title or episode_title


def _normalize_summary_heading(
    output_dir: Path, summary_text: str, *, output_language: str = "zh"
) -> str:
    text = summary_text.strip()
    if not text:
        return ""
    lines = text.splitlines()
    if output_language != "zh":
        first = lines[0].strip()
        if (
            not first.startswith("# ")
            or _summary_heading_is_generic(first)
            or _heading_text(first).casefold() == "summary"
        ):
            raise ValueError(
                "Summary must begin with a specific Markdown title in the output language."
            )
        return text
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        title = _summary_heading_title(output_dir, text)
        if line.lstrip().startswith("#"):
            if title and _summary_heading_is_generic(line):
                lines[index] = f"# {title}"
            return "\n".join(lines).strip()
        if title:
            return f"# {title}\n\n{text}"
        return text
    return text


def _short_title_options(options: CloudOutputOptions) -> CloudOutputOptions:
    return CloudOutputOptions(
        output_dir=options.output_dir,
        call_api=options.call_api,
        output_language=options.output_language,
    )


def _json_section(title: str, payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    return f"## {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"


def _short_text(value: Any, *, limit: int = 220) -> str:
    text = compact_ws(str(value or ""))
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


def _limited_text_section(title: str, path: Path, *, limit: int = FINAL_CONTEXT_TEXT_LIMIT) -> str:
    text = read_text(path)
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip() + "\n\n[truncated]"
    return f"## {title}\n\n{text}"


def _compact_manifest_context(output_dir: Path) -> dict[str, Any]:
    manifest = _read_json_object(_input_dir(output_dir) / "manifest.json")
    if not manifest:
        return {}
    keys = [
        "episode_title",
        "audio_duration",
        "qa_status",
        "contains_audio",
        "contains_video",
        "text_chunks",
        "text_chunk_ranges",
    ]
    return {key: manifest[key] for key in keys if key in manifest}


def _compact_qa_context(output_dir: Path) -> dict[str, Any]:
    qa = _read_json_object(_input_dir(output_dir) / "qa.for_cloud.json")
    if not qa:
        return {}
    issues = qa.get("issues", []) if isinstance(qa.get("issues"), list) else []
    issue_counts: dict[str, int] = {}
    for issue in issues:
        if isinstance(issue, dict):
            issue_type = str(issue.get("type") or "unknown")
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
    examples: list[dict[str, Any]] = []
    for issue in issues[:FINAL_CONTEXT_ITEM_LIMIT]:
        if not isinstance(issue, dict):
            continue
        examples.append(
            {
                "type": issue.get("type"),
                "severity": issue.get("severity"),
                "time": issue.get("time") or issue.get("start"),
                "message": _short_text(issue.get("message") or issue.get("evidence") or issue),
            }
        )
    payload: dict[str, Any] = {
        "success": qa.get("success"),
        "status": qa.get("status"),
        "issue_count": len(issues),
        "issue_counts": issue_counts,
        "examples": examples,
    }
    summary = qa.get("summary")
    if isinstance(summary, dict):
        payload["summary"] = summary
    return payload


def _compact_review_context(output_dir: Path) -> dict[str, Any]:
    review = _read_json_object(_input_dir(output_dir) / "review.for_cloud.json")
    if not review:
        return {}
    payload: dict[str, Any] = {
        key: review[key] for key in ("success", "status", "summary") if key in review
    }
    for key in ("needs_human_confirmation", "uncertainties", "items"):
        values = review.get(key)
        if isinstance(values, list):
            payload[key] = values[:FINAL_CONTEXT_ITEM_LIMIT]
    return payload


def _compact_chunk_summary(path: Path) -> dict[str, Any]:
    payload = _read_json_object(path)
    keys = [
        "success",
        "chunk",
        "input",
        "start",
        "end",
        "summary",
        "terms",
        "uncertainties",
        "source",
    ]
    compact = {key: payload[key] for key in keys if key in payload}
    if isinstance(compact.get("summary"), str):
        compact["summary"] = _short_text(compact["summary"], limit=1200)
    if isinstance(compact.get("terms"), list):
        compact["terms"] = compact["terms"][:FINAL_CONTEXT_ITEM_LIMIT]
    if isinstance(compact.get("uncertainties"), list):
        compact["uncertainties"] = compact["uncertainties"][:FINAL_CONTEXT_ITEM_LIMIT]
    return compact


def _episode_input_from_chunk_summaries(output_dir: Path) -> str:
    cloud = _cloud_dir(output_dir)
    input_dir = _input_dir(output_dir)
    parts = [
        _json_section("manifest.compact.json", _compact_manifest_context(output_dir)),
        _json_section("qa.compact.json", _compact_qa_context(output_dir)),
        _json_section("review.compact.json", _compact_review_context(output_dir)),
        _limited_text_section(
            "glossary.for_cloud.json", input_dir / "glossary.for_cloud.json", limit=6_000
        ),
        _limited_text_section("topic.for_cloud.md", input_dir / "topic.for_cloud.md", limit=6_000),
    ]
    for path in sorted((cloud / "chunk_summaries").glob("chunk_*.summary.json")):
        payload = _compact_chunk_summary(path)
        if payload:
            parts.append(_json_section(relative_posix_path(path, cloud), payload))
    return "\n\n".join(part for part in parts if part).strip()


def _fallback_summary_from_chunk_summaries(output_dir: Path, *, partial: bool) -> str:
    cloud = _cloud_dir(output_dir)
    entries: list[dict[str, str]] = []
    for path in sorted((cloud / "chunk_summaries").glob("chunk_*.summary.json")):
        payload = _read_json_object(path)
        summary = compact_ws(_strip_outer_markdown_fence(str(payload.get("summary") or "")))
        if not summary:
            continue
        entries.append(
            {
                "start": str(payload.get("start") or ""),
                "end": str(payload.get("end") or ""),
                "summary": _short_text(summary, limit=420),
                "source": str(payload.get("source") or ""),
            }
        )

    lines = [f"# {episode_title_for_output(output_dir) or 'Summary'}", ""]
    if partial:
        lines.append(
            "This summary combines available chunk results. Some cloud chunks are incomplete; review uncertainty_report.md."
        )
    else:
        lines.append("This summary combines the currently available chunk results.")
    lines.append("")

    if not entries:
        lines.append("No chunk summaries are available.")
        return "\n".join(lines).strip() + "\n"

    lines.extend(["## Chunk Highlights", ""])
    for item in entries:
        start = item["start"] or "unknown"
        end = item["end"] or start
        suffix = " (fallback)" if item["source"] != "cloud_model" else ""
        lines.append(f"### {start} -> {end}{suffix}")
        lines.append("")
        lines.append(item["summary"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _write_direct_readable_summary(
    options: CloudOutputOptions,
    dependencies: SummaryDependencies,
    *,
    call_chat: ChatCaller | None = None,
    stream_chat: StreamCaller | None = None,
) -> dict[str, Any]:
    output_dir = options.output_dir.expanduser().resolve()
    transcript = dependencies.readable_transcript_text(output_dir)
    if not dependencies.direct_readable_allowed(options, transcript):
        raise ValueError(
            "transcript.readable.md is too long for direct readable summary "
            f"({len(transcript)} chars > {options.direct_readable_char_limit}). "
            "Use --mode chunked or pass --allow-long-direct."
        )
    summary_path = _cloud_dir(output_dir) / "summary.md"
    update_cloud_summary_state(output_dir, "running", summary_stage="direct_summary")
    cloud_text: str | None
    if options.call_api and options.stream_summary:
        chunks: list[str] = []
        write_text_atomic(summary_path, "")

        def write_delta(delta: str) -> None:
            chunks.append(delta)
            write_text_atomic(
                summary_path, _strip_outer_markdown_fence("".join(chunks), allow_open=True)
            )

        cloud_text = (stream_chat or call_openai_compatible_chat_stream)(
            system_prompt=_summary_prompt_for_direct_readable(options),
            user_content=transcript,
            options=CloudClientOptions(),
            on_delta=write_delta,
            audit_path=summary_path.parent / "summary.readable.api_run.json",
        )
    else:
        cloud_text = _maybe_call_cloud(
            options,
            default_prompt=_summary_prompt_for_direct_readable(options),
            fallback_prompt=Path("doc/cloud_prompts/summarize.zh.md"),
            user_content=transcript,
            audit_name="summary.readable.api_run.json",
            call_chat=call_chat,
            prefer_fallback_prompt=False,
            prompt_transform=_summary_prompt_with_title_instruction,
        )
    summary_text = _normalize_summary_heading(
        output_dir,
        _strip_outer_markdown_fence(cloud_text or ""),
        output_language=options.output_language,
    )
    write_text_atomic(summary_path, summary_text + ("\n" if summary_text else ""))
    outputs = ["summary.md"]
    if options.call_api and summary_text:
        title_result = dependencies.write_short_title(_short_title_options(options), force=True)
        outputs.extend(str(item) for item in title_result.get("outputs", []))
    _record_cloud_outputs(
        output_dir,
        outputs,
        source="cloud_model" if options.call_api else "local_scaffold",
        mode="direct_readable",
    )
    return {
        "success": True,
        "source": "cloud_model" if options.call_api else "local_scaffold",
        "mode": "direct_readable",
        "outputs": outputs,
    }


def write_cloud_summary(
    options: CloudOutputOptions,
    dependencies: SummaryDependencies,
    *,
    call_chat: ChatCaller | None = None,
    stream_chat: StreamCaller | None = None,
) -> dict[str, Any]:
    """Generate cloud summary artifacts for a transcription output bundle.

    Args:
        options: Output directory, model, and cloud execution settings.
        dependencies: File-system and summarization callbacks.
        call_chat: Optional non-streaming chat caller override.
        stream_chat: Optional streaming chat caller override.

    Returns:
        A dictionary describing whether generation succeeded and which output
        artifacts were written.

    Raises:
        RuntimeError: If cloud execution is requested but required cloud output
            content is missing or chunk generation fails.
        ValueError: If an unsupported summary mode is requested.
    """

    output_dir = options.output_dir.expanduser().resolve()
    with _cloud_summary_lock(output_dir):
        update_cloud_summary_state(output_dir, "running", summary_stage="start")
        _clear_cloud_summary_outputs(output_dir)
        try:
            mode = "direct" if options.direct_readable else options.summary_mode
            if mode == "auto":
                try:
                    transcript = dependencies.readable_transcript_text(output_dir)
                except FileNotFoundError:
                    transcript = ""
                mode = (
                    "direct"
                    if transcript
                    and dependencies.auto_direct_readable_allowed(options, output_dir, transcript)
                    else "chunked"
                )
            if mode == "direct":
                return _write_direct_readable_summary(
                    options,
                    dependencies,
                    call_chat=call_chat,
                    stream_chat=stream_chat,
                )
            if mode != "chunked":
                raise ValueError(f"Unknown cloud summary mode: {mode}")
            cloud = _cloud_dir(output_dir)
            chunk_outputs, failed_chunks = dependencies.write_chunk_summaries(output_dir)
            uncertainty_outputs = dependencies.write_uncertainty_report(output_dir)
            term_outputs = dependencies.write_terms_outputs(output_dir)
            lines = dependencies.transcript_lines(output_dir)
            chapters = dependencies.chapterize(output_dir, lines)
            if options.call_api and failed_chunks:
                raise RuntimeError("Cloud chunk summaries failed: " + ", ".join(failed_chunks))
            cloud_text = None
            if options.call_api:
                update_cloud_summary_state(output_dir, "running", summary_stage="episode_summary")
                cloud_text = _maybe_call_cloud(
                    options,
                    default_prompt="Summarize the supplied podcast content as structured Markdown with a specific title, key points, evidence, conclusions and uncertainty. Do not add external facts.",
                    prefer_fallback_prompt=False,
                    fallback_prompt=Path("doc/cloud_prompts/summarize.zh.md"),
                    user_content=dependencies.episode_input_from_chunk_summaries(output_dir)
                    if options.call_api
                    else dependencies.input_bundle(output_dir),
                    audit_name="summarize.api_run.json",
                    call_chat=call_chat,
                    prompt_transform=_summary_prompt_with_title_instruction,
                )
                if cloud_text is None:
                    raise RuntimeError("Cloud episode summary produced no content.")
            if cloud_text is not None:
                cloud_text = _normalize_summary_heading(
                    output_dir,
                    _strip_outer_markdown_fence(cloud_text),
                    output_language=options.output_language,
                )
                write_text_atomic(cloud / "summary.md", cloud_text)
                dependencies.write_chapter_outputs(cloud, chapters, cloud_text)
                publish_outputs = dependencies.write_publish_outputs(
                    output_dir, cloud_text, chapters
                )
                title_outputs: list[str] = []
                if options.call_api and cloud_text:
                    title_result = dependencies.write_short_title(
                        _short_title_options(options), force=True
                    )
                    title_outputs = [str(item) for item in title_result.get("outputs", [])]
                outputs = [
                    "summary.md",
                    "chapters.json",
                    "chapters.md",
                    "shownotes.md",
                    *publish_outputs,
                    *title_outputs,
                    *term_outputs,
                    *uncertainty_outputs,
                    *chunk_outputs,
                ]
                result_source = "partial_cloud" if failed_chunks else "cloud_model"
                _record_cloud_outputs(output_dir, outputs, source=result_source, mode="map_reduce")
                return {
                    "success": True,
                    "source": result_source,
                    "mode": "chunked",
                    "partial": bool(failed_chunks),
                    "outputs": outputs,
                }
            summary = dependencies.fallback_summary_from_chunk_summaries(output_dir, False)
            outputs = [
                "summary.md",
                "chapters.json",
                "chapters.md",
                "shownotes.md",
                *term_outputs,
                *uncertainty_outputs,
                *chunk_outputs,
            ]
            write_text_atomic(cloud / "summary.md", summary)
            dependencies.write_chapter_outputs(cloud, chapters, summary)
            publish_outputs = dependencies.write_publish_outputs(output_dir, summary, chapters)
            outputs.extend(publish_outputs)
            _record_cloud_outputs(output_dir, outputs, source="local_scaffold", mode="map_reduce")
            return {
                "success": True,
                "source": "local_scaffold",
                "mode": "chunked",
                "partial": False,
                "outputs": outputs,
            }
        except Exception as exc:
            update_cloud_summary_state(output_dir, "failed", error=str(exc))
            raise
