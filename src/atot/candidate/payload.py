from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CandidateSegmentParser:
    key: str
    text_fields: tuple[str, ...]


KNOWN_SEGMENT_PARSERS: tuple[CandidateSegmentParser, ...] = (
    CandidateSegmentParser(key="segments", text_fields=("text",)),
    CandidateSegmentParser(key="sentences", text_fields=("text", "sentence")),
    CandidateSegmentParser(key="chunks", text_fields=("text", "transcript")),
)


def load_candidate_payload(stdout: str, output_path: Path) -> Any:
    if output_path.exists():
        text = output_path.read_text(encoding="utf-8").strip()
    else:
        text = stdout.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def payload_text(payload: Any) -> str:
    if isinstance(payload, dict):
        text = payload.get("text")
        if text:
            return str(text)
        segments = payload_segments(payload)
        return "".join(str(segment.get("text", "")) for segment in segments)
    if isinstance(payload, list):
        segments = payload_segments(payload)
        return "".join(str(segment.get("text", "")) for segment in segments)
    return str(payload).strip()


def _coerce_time(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text_from_item(item: dict[str, Any], parser: CandidateSegmentParser | None) -> str:
    fields = parser.text_fields if parser else ("text", "sentence", "transcript")
    for field in fields:
        text = str(item.get(field) or "").strip()
        if text:
            return text
    return ""


def segment_from_item(
    item: Any,
    index: int,
    *,
    parser: CandidateSegmentParser | None = None,
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    text = _text_from_item(item, parser)
    if not text:
        return None
    timestamp = item.get("timestamp") or item.get("timestamps")
    has_explicit_timing = any(
        key in item for key in ("start", "start_time", "begin", "end", "end_time", "finish")
    )
    has_explicit_timing = has_explicit_timing or isinstance(timestamp, (list, tuple))
    start_default = float(index)
    end_default = start_default + 0.01
    if isinstance(timestamp, (list, tuple)) and timestamp:
        start_default = _coerce_time(timestamp[0], start_default)
        if len(timestamp) > 1:
            end_default = _coerce_time(timestamp[1], max(start_default + 0.01, end_default))
    start = _coerce_time(
        item.get("start", item.get("start_time", item.get("begin"))), start_default
    )
    end = _coerce_time(item.get("end", item.get("end_time", item.get("finish"))), end_default)
    if end <= start:
        end = start + 0.01
    return {
        "start": start,
        "end": end,
        "text": text,
        "_timing_source": "explicit" if has_explicit_timing else "synthetic",
    }


def _candidate_items(
    payload: dict[str, Any],
) -> tuple[list[Any] | None, CandidateSegmentParser | None]:
    for parser in KNOWN_SEGMENT_PARSERS:
        value = payload.get(parser.key)
        if isinstance(value, list):
            return value, parser
    return None, None


def payload_segments(payload: Any) -> list[dict[str, Any]]:
    candidates: Any = payload
    parser: CandidateSegmentParser | None = None
    if isinstance(payload, dict):
        candidates, parser = _candidate_items(payload)
        if candidates is None:
            text = str(payload.get("text") or "").strip()
            return (
                [{"start": 0.0, "end": 0.01, "text": text, "_timing_source": "text_fallback"}]
                if text
                else []
            )
    if not isinstance(candidates, list):
        text = str(candidates).strip()
        return (
            [{"start": 0.0, "end": 0.01, "text": text, "_timing_source": "text_fallback"}]
            if text
            else []
        )
    segments = []
    for index, item in enumerate(candidates):
        segment = segment_from_item(item, index, parser=parser)
        if segment:
            segments.append(segment)
    if segments:
        return segments
    text = str(payload.get("text") or "").strip() if isinstance(payload, dict) else ""
    return (
        [{"start": 0.0, "end": 0.01, "text": text, "_timing_source": "text_fallback"}]
        if text
        else []
    )


def extract_candidate_segments(stdout: str, output_path: Path) -> list[dict[str, Any]]:
    payload = load_candidate_payload(stdout, output_path)
    segments = payload_segments(payload)
    if segments:
        return segments
    text = payload_text(payload)
    return (
        [{"start": 0.0, "end": 0.01, "text": text, "_timing_source": "text_fallback"}]
        if text
        else []
    )


def extract_candidate_text(stdout: str, output_path: Path) -> str:
    payload = load_candidate_payload(stdout, output_path)
    return payload_text(payload)
