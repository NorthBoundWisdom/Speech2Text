from __future__ import annotations

from pathlib import Path
from typing import Any

from .json_io import read_json_if_exists
from .numeric import as_float


def segments_from_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get("segments")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def first_segment_list(*payloads: Any) -> list[dict[str, Any]]:
    for payload in payloads:
        segments = segments_from_payload(payload)
        if segments:
            return segments
    return []


def validate_segment_payload_file(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], [f"missing required file: {path}"]
    payload = read_json_if_exists(path)
    if not isinstance(payload, dict):
        return [], [f"{path}: must be a JSON object"]
    segments = segments_from_payload(payload)
    errors: list[str] = []
    if not segments:
        errors.append(f"{path}: `segments` must be a non-empty list")
    for index, segment in enumerate(segments):
        if not isinstance(segment.get("text"), str):
            errors.append(f"{path}: segments[{index}].text must be a string")
        start = as_float(segment.get("start"))
        end = as_float(segment.get("end"))
        if start is None:
            errors.append(f"{path}: segments[{index}].start must be numeric")
        if end is None:
            errors.append(f"{path}: segments[{index}].end must be numeric")
        if start is not None and end is not None and end < start:
            errors.append(f"{path}: segments[{index}].end must be greater than or equal to start")
    return segments, errors
