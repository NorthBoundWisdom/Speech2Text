from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from .client import CloudClientOptions
from .output_state import CloudOutputOptions, _cloud_dir, _input_dir, _read_json_object
from ..numeric import as_float
from ..progress import update_cloud_summary_state
from ..utils import (
    compact_ws,
    ensure_dir,
    read_text,
    relative_posix_path,
    seconds_to_hms,
    write_json_atomic,
)


TIMESTAMP_LINE_RE = re.compile(
    r"^\[(?P<start>\d{2}:\d{2}:\d{2})(?:\s*->\s*(?P<end>\d{2}:\d{2}:\d{2}))?\]\s*(?P<text>.*)$"
)
CHUNK_RANGE_RE = re.compile(
    r"^Range:\s*(?P<start>\d{2}:\d{2}:\d{2})\s*->\s*(?P<end>\d{2}:\d{2}:\d{2})$"
)
FULLWIDTH_LATIN_NOISE_RE = re.compile(r"[\uFF21-\uFF3A]")
NOISE_NORMALIZE_RE = re.compile(r"[\s，。！？、；：,.!?;:\"'“”‘’`()\[\]{}<>《》…·-]+")
REPEATED_NOISE_RE = re.compile(r"(.{1,8})\1{4,}")

ChatCaller = Callable[..., str]


def _hms_to_seconds(value: str) -> float:
    hours, minutes, seconds = [int(part) for part in value.split(":")]
    return float(hours * 3600 + minutes * 60 + seconds)


def _input_chunk_paths(output_dir: Path) -> list[Path]:
    input_dir = _input_dir(output_dir)
    manifest = _read_json_object(input_dir / "manifest.json")
    text_chunks = manifest.get("text_chunks")
    chunk_paths = text_chunks if isinstance(text_chunks, list) else []
    paths = [input_dir / str(path) for path in chunk_paths]
    if not paths:
        paths = sorted((input_dir / "chunks").glob("text_chunk_*.md"))
    return [path for path in paths if path.exists()]


def _range_from_chunk_text(text: str) -> tuple[str, str] | None:
    for line in text.splitlines():
        match = CHUNK_RANGE_RE.match(line.strip())
        if match:
            return match.group("start"), match.group("end")
    return None


def _range_from_manifest(
    output_dir: Path, relative_input: str, fallback_index: int
) -> tuple[str, str] | None:
    manifest = _read_json_object(_input_dir(output_dir) / "manifest.json")
    text_chunk_ranges = manifest.get("text_chunk_ranges")
    ranges = text_chunk_ranges if isinstance(text_chunk_ranges, list) else []
    for item in ranges:
        if not isinstance(item, dict) or str(item.get("path", "")) != relative_input:
            continue
        start = item.get("start")
        end = item.get("end")
        if isinstance(start, str) and isinstance(end, str) and start and end:
            return start, end

    chunk_manifest = _read_json_object(output_dir / "chunks_manifest.json")
    layout_payload = chunk_manifest.get("chunk_layout")
    layout: dict[str, Any] = layout_payload if isinstance(layout_payload, dict) else {}
    layout_chunks = layout.get("chunks")
    chunks = layout_chunks if isinstance(layout_chunks, list) else chunk_manifest.get("chunks")
    if isinstance(chunks, list) and 0 <= fallback_index - 1 < len(chunks):
        chunk = chunks[fallback_index - 1]
        if isinstance(chunk, dict):
            start_seconds = as_float(chunk.get("core_start", chunk.get("source_start", 0.0)))
            if start_seconds is None:
                return None
            end_seconds = as_float(chunk.get("core_end", chunk.get("source_end", start_seconds)))
            if end_seconds is None:
                return None
            return seconds_to_hms(start_seconds), seconds_to_hms(end_seconds)
    return None


def _chunk_range(
    output_dir: Path, *, text: str, relative_input: str, fallback_index: int
) -> tuple[str, str]:
    return (
        _range_from_chunk_text(text)
        or _range_from_manifest(output_dir, relative_input, fallback_index)
        or (
            seconds_to_hms(float(max(0, fallback_index - 1) * 20 * 60)),
            seconds_to_hms(float(fallback_index * 20 * 60)),
        )
    )


def _summary_text_from_chunk(text: str, *, limit: int = 180) -> str:
    transcript_lines: list[str] = []
    for line in text.splitlines():
        match = TIMESTAMP_LINE_RE.match(line.strip())
        if not match:
            continue
        cleaned = _clean_chunk_line_text(match.group("text"))
        if cleaned:
            transcript_lines.append(cleaned)
    summary = compact_ws("".join(transcript_lines))
    return summary[:limit] if summary else "No transcript text available for this chunk."


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk_api_prompt() -> str:
    return (
        "你将收到一个带时间范围的中文播客文本块。"
        "转写中可能包含重复短语、占位字符（如“Ｂ”“Ｖ”）、乱码、空白句、半截句和相邻重复段。"
        "请忽略明显噪声，只总结仍然可辨认的有效内容；如果某一段主要是噪声，不要编造。"
        "必须只输出一个 JSON object，字段固定为 summary、terms、uncertainties。"
        "summary 必须是中文字符串；terms 与 uncertainties 必须是数组。不要添加外部事实。"
        "不要输出 Markdown，不要输出代码块，不要输出额外解释。"
    )


def _noise_signature(text: str) -> str:
    cleaned = FULLWIDTH_LATIN_NOISE_RE.sub("", text or "")
    return NOISE_NORMALIZE_RE.sub("", cleaned)


def _looks_like_repetition_noise(text: str) -> bool:
    signature = _noise_signature(text)
    if len(signature) < 18:
        return False
    if len(set(signature)) <= 2 and len(signature) >= 24:
        return True
    match = REPEATED_NOISE_RE.search(signature)
    if match and len(match.group(0)) >= max(18, len(signature) // 2):
        return True
    distinct_ratio = len(set(signature)) / max(1, len(signature))
    return len(signature) >= 48 and distinct_ratio < 0.12


def _clean_chunk_line_text(text: str) -> str:
    cleaned = FULLWIDTH_LATIN_NOISE_RE.sub(" ", text or "")
    cleaned = compact_ws(cleaned)
    if not cleaned:
        return ""
    if not _noise_signature(cleaned):
        return ""
    if _looks_like_repetition_noise(cleaned):
        return ""
    return cleaned


def _truncate_chunk_content(text: str, *, max_chars: int = 7_500, tail_chars: int = 2_000) -> str:
    if len(text) <= max_chars:
        return text
    tail_chars = max(500, min(tail_chars, max_chars // 2))
    head_chars = max_chars - tail_chars - 64
    if head_chars < 500:
        head_chars = max_chars // 2
        tail_chars = max_chars - head_chars - 64
    omitted = len(text) - head_chars - tail_chars
    marker = f"\n\n[omitted {omitted} chars of repetitive or low-signal transcript]\n\n"
    return text[:head_chars].rstrip() + marker + text[-tail_chars:].lstrip()


def _chunk_user_content_for_cloud(text: str, *, max_chars: int = 7_500) -> str:
    header_lines: list[str] = []
    context_lines: list[str] = []
    transcript_lines: list[str] = []
    in_context = False
    in_transcript = False
    previous_signature = ""

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("# Text Chunk") or stripped.startswith("Range:"):
            header_lines.append(stripped)
            continue
        if stripped == "Previous chunk context:":
            in_context = True
            in_transcript = False
            continue
        if stripped == "# Transcript For Cloud":
            in_context = False
            in_transcript = True
            continue
        if in_context:
            cleaned_context = _clean_chunk_line_text(stripped)
            if cleaned_context:
                context_lines.append(cleaned_context)
            continue
        if not in_transcript:
            continue
        match = TIMESTAMP_LINE_RE.match(stripped)
        if not match:
            continue
        cleaned_text = _clean_chunk_line_text(match.group("text"))
        if not cleaned_text:
            continue
        signature = _noise_signature(cleaned_text)
        if signature and signature == previous_signature:
            continue
        previous_signature = signature
        start = match.group("start")
        end = match.group("end") or start
        transcript_lines.append(f"[{start} -> {end}] {cleaned_text}")

    parts: list[str] = []
    if header_lines:
        parts.append("\n".join(header_lines))
    context_text = compact_ws(" ".join(context_lines))
    if context_text:
        parts.append(f"Previous chunk context:\n{context_text[:500]}")
    if transcript_lines:
        transcript_body = "# Transcript For Cloud\n\n" + "\n".join(transcript_lines)
        parts.append(_truncate_chunk_content(transcript_body, max_chars=max_chars))
    else:
        parts.append(
            "# Transcript For Cloud\n\n[00:00:00 -> 00:00:00] No usable transcript text remained after noise cleanup."
        )
    return "\n\n".join(parts).strip()


def _read_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in cloud response.")
    payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Cloud JSON response must be an object.")
    return payload


def _chunk_payload_from_cloud_text(text: str) -> dict[str, Any]:
    try:
        payload = _read_json_from_text(text)
    except ValueError:
        return {"summary": compact_ws(text), "terms": [], "uncertainties": [], "raw_response": text}
    return {
        "summary": str(payload.get("summary") or payload.get("摘要") or ""),
        "terms": payload.get("terms") if isinstance(payload.get("terms"), list) else [],
        "uncertainties": payload.get("uncertainties")
        if isinstance(payload.get("uncertainties"), list)
        else [],
        **({"raw_response": text} if not payload.get("summary") else {}),
    }


def _call_chunk_cloud_once(
    options: CloudOutputOptions,
    *,
    user_content: str,
    audit_name: str,
    call_chat: ChatCaller,
) -> str | None:
    if not options.call_api:
        return None
    return call_chat(
        system_prompt=_chunk_api_prompt(),
        user_content=user_content,
        options=CloudClientOptions(),
        audit_path=_cloud_dir(options.output_dir.expanduser().resolve()) / audit_name,
    )


def _call_chunk_cloud_with_retry(
    options: CloudOutputOptions,
    *,
    user_content: str,
    audit_name: str,
    call_chat: ChatCaller,
) -> tuple[str | None, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    max_attempts = max(1, int(options.retry_count) + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            text = _call_chunk_cloud_once(
                options,
                user_content=user_content,
                audit_name=audit_name,
                call_chat=call_chat,
            )
            attempts.append({"attempt": attempt, "success": text is not None})
            return text, {"attempts": attempts}
        except Exception as exc:  # pragma: no cover - exception type depends on HTTP client
            attempts.append({"attempt": attempt, "success": False, "error": str(exc)})
            if attempt >= max_attempts:
                return None, {"attempts": attempts, "error": str(exc)}
            time.sleep(max(0.0, float(options.retry_backoff_seconds)) * attempt)
    return None, {"attempts": attempts}


def write_chunk_summaries(
    output_dir: Path,
    *,
    options: CloudOutputOptions,
    source: str,
    call_chat: ChatCaller,
) -> tuple[list[str], list[str]]:
    cloud = _cloud_dir(output_dir)
    summary_dir = ensure_dir(cloud / "chunk_summaries")
    outputs: list[str] = []
    failed: list[str] = []
    input_paths = _input_chunk_paths(output_dir)
    if options.call_api:
        update_cloud_summary_state(
            output_dir,
            "running",
            summary_stage="chunk_summaries",
            cloud_chunk_total=len(input_paths),
        )
    for index, path in enumerate(input_paths, start=1):
        if options.call_api:
            update_cloud_summary_state(
                output_dir,
                "running",
                summary_stage="chunk_summaries",
                cloud_chunk_index=index,
                cloud_chunk_total=len(input_paths),
            )
        text = read_text(path) or ""
        output_name = f"chunk_{index:04d}.summary.json"
        relative_input = relative_posix_path(path, _input_dir(output_dir))
        input_sha256 = _text_sha256(text)
        start, end = _chunk_range(
            output_dir, text=text, relative_input=relative_input, fallback_index=index
        )
        existing = _read_json_object(summary_dir / output_name)
        if (
            options.call_api
            and existing.get("source") == "cloud_model"
            and existing.get("input") == relative_input
            and existing.get("input_sha256") == input_sha256
            and existing.get("success") is not False
        ):
            outputs.append(f"chunk_summaries/{output_name}")
            continue
        cloud_payload: dict[str, Any] | None = None
        retry_audit: dict[str, Any] = {}
        if options.call_api:
            cloud_text, retry_audit = _call_chunk_cloud_with_retry(
                options,
                user_content=_chunk_user_content_for_cloud(text),
                audit_name=f"chunk_summaries/chunk_{index:04d}.api_run.json",
                call_chat=call_chat,
            )
            if cloud_text is not None:
                cloud_payload = _chunk_payload_from_cloud_text(cloud_text)
            else:
                failed.append(output_name)
        payload = {
            "success": cloud_payload is not None or not options.call_api,
            "chunk": index,
            "input": relative_input,
            "input_sha256": input_sha256,
            "start": start,
            "end": end,
            "summary": str(
                cloud_payload.get("summary")
                if cloud_payload
                else _summary_text_from_chunk(text)
                if not options.call_api
                else ""
            ),
            "terms": cloud_payload.get("terms", []) if cloud_payload else [],
            "uncertainties": cloud_payload.get("uncertainties", []) if cloud_payload else [],
            "source": "cloud_model" if cloud_payload else "failed" if options.call_api else source,
        }
        if retry_audit:
            payload["retry"] = retry_audit
        if cloud_payload and cloud_payload.get("raw_response"):
            payload["raw_response"] = cloud_payload["raw_response"]
        write_json_atomic(summary_dir / output_name, payload)
        outputs.append(f"chunk_summaries/{output_name}")
        if options.call_api:
            update_cloud_summary_state(
                output_dir,
                "running",
                summary_stage="chunk_summaries",
                cloud_chunk_completed=len(outputs) - len(failed),
                cloud_chunk_failed=len(failed),
                cloud_chunk_total=len(input_paths),
            )
    return outputs, failed
