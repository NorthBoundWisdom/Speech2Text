from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .utils import compact_ws, seconds_to_hms


CJK_RE = r"\u3400-\u4dbf\u4e00-\u9fff"
ASCII_WORD_RE = r"[A-Za-z0-9][A-Za-z0-9+._/\-*#]*"
END_PUNCTUATION = "。！？!?；;.!?"
PUNCTUATION = "，。！？；：、,.!?;:"
OPENING_PUNCTUATION = "（([【《"
CLOSING_PUNCTUATION = "，。！？；：、,.!?;:）)]】》"


@dataclass(frozen=True)
class ReadableComposerResult:
    markdown: str
    log: dict[str, Any]


def _visible_len(text: str) -> int:
    return len(compact_ws(text).replace(" ", ""))


def _normalize_readable_spacing(text: str) -> tuple[str, bool]:
    before = compact_ws(text)
    after = before
    after = re.sub(rf"([{CJK_RE}])({ASCII_WORD_RE})", r"\1 \2", after)
    after = re.sub(rf"({ASCII_WORD_RE})([{CJK_RE}])", r"\1 \2", after)
    after = re.sub(rf"\s+([{CLOSING_PUNCTUATION}])", r"\1", after)
    after = re.sub(rf"([{OPENING_PUNCTUATION}])\s+", r"\1", after)
    after = re.sub(r"\s{2,}", " ", after).strip()
    return after, after != before


def _is_cjk(char: str) -> bool:
    return bool(re.match(rf"[{CJK_RE}]", char))


def _is_ascii_word(char: str) -> bool:
    return bool(re.match(r"[A-Za-z0-9]", char))


def _joiner(left: str, right: str) -> str:
    if not left or not right:
        return ""
    left_char = left[-1]
    right_char = right[0]
    if left_char in END_PUNCTUATION or right_char in CLOSING_PUNCTUATION:
        return ""
    if left_char in OPENING_PUNCTUATION:
        return ""
    if (_is_cjk(left_char) and _is_ascii_word(right_char)) or (
        _is_ascii_word(left_char) and _is_cjk(right_char)
    ):
        return " "
    if _is_ascii_word(left_char) and _is_ascii_word(right_char):
        return " "
    if _is_cjk(left_char) and _is_cjk(right_char):
        return "，"
    return ""


def _sentence_chunks(text: str, *, max_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in END_PUNCTUATION and _visible_len(current) >= max_chars:
            pieces.append(current)
            current = ""
    if current:
        pieces.append(current)
    if not pieces:
        return []

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = current + piece
        if current and _visible_len(candidate) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)

    hard_split: list[str] = []
    for chunk in chunks:
        if _visible_len(chunk) <= max_chars * 1.25:
            hard_split.append(chunk)
            continue
        cursor = ""
        for char in chunk:
            cursor += char
            if _visible_len(cursor) >= max_chars:
                hard_split.append(cursor)
                cursor = ""
        if cursor:
            hard_split.append(cursor)
    return [compact_ws(item) for item in hard_split if compact_ws(item)]


def compose_readable_transcript(
    segments: list[dict[str, Any]],
    *,
    title: str = "Transcript",
    bucket_seconds: float = 180.0,
    max_paragraph_chars: int = 320,
) -> ReadableComposerResult:
    lines = [f"# {title}", ""]
    transformations: list[dict[str, Any]] = []
    paragraphs: list[dict[str, Any]] = []
    paragraph_text = ""
    paragraph_start: float | None = None
    rendered_segment_count = 0

    def flush(reason: str) -> None:
        nonlocal paragraph_text, paragraph_start
        text = compact_ws(paragraph_text)
        if not text:
            paragraph_text = ""
            paragraph_start = None
            return
        start = float(paragraph_start or 0.0)
        chunks = _sentence_chunks(text, max_chars=max_paragraph_chars)
        if len(chunks) > 1:
            transformations.append(
                {
                    "type": "split_long_paragraph",
                    "start": round(start, 3),
                    "paragraph_chars": _visible_len(text),
                    "chunk_count": len(chunks),
                }
            )
        for chunk in chunks:
            paragraphs.append({"start": start, "text": chunk})
        transformations.append(
            {
                "type": "flush_paragraph",
                "reason": reason,
                "start": round(start, 3),
                "paragraph_chars": _visible_len(text),
            }
        )
        paragraph_text = ""
        paragraph_start = None

    for segment_index, segment in enumerate(segments):
        raw_text = compact_ws(str(segment.get("text", "")))
        if not raw_text:
            continue
        try:
            start = float(segment.get("start", 0.0))
        except (TypeError, ValueError):
            start = 0.0
        text, changed = _normalize_readable_spacing(raw_text)
        if changed:
            transformations.append(
                {
                    "type": "normalize_spacing",
                    "segment_index": segment_index,
                    "start": round(start, 3),
                    "before": raw_text,
                    "after": text,
                }
            )
        if paragraph_start is not None and start - paragraph_start >= bucket_seconds:
            flush("time_bucket")
        if (
            paragraph_text
            and _visible_len(paragraph_text) + _visible_len(text) > max_paragraph_chars
        ):
            flush("max_paragraph_chars")
        if paragraph_start is None:
            paragraph_start = start
        joiner = _joiner(paragraph_text, text)
        if joiner:
            transformations.append(
                {
                    "type": "insert_joiner",
                    "segment_index": segment_index,
                    "start": round(start, 3),
                    "joiner": joiner,
                }
            )
        paragraph_text += joiner + text
        rendered_segment_count += 1
    flush("end")

    for paragraph in paragraphs:
        lines.append(f"[{seconds_to_hms(float(paragraph['start']))}] {paragraph['text']}")
        lines.append("")

    log = {
        "schema_version": 1,
        "title": title,
        "input_segment_count": len(segments),
        "rendered_segment_count": rendered_segment_count,
        "paragraph_count": len(paragraphs),
        "bucket_seconds": bucket_seconds,
        "max_paragraph_chars": max_paragraph_chars,
        "transformation_count": len(transformations),
        "transformations": transformations,
    }
    return ReadableComposerResult(markdown="\n".join(lines).strip() + "\n", log=log)
