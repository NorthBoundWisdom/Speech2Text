from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .numeric import as_float
from .utils import compact_ws, seconds_to_srt_ts, seconds_to_vtt_ts


@dataclass(frozen=True)
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


SRT_TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})$"
)
VTT_TIMESTAMP_RE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})$"
)
SPLIT_AFTER_RE = re.compile(r"([。！？!?；;，,、])")
NUMBER_COMMA_PLACEHOLDER = "\ue000"


def _timestamp_to_seconds(value: str) -> float:
    time_part, ms_part = value.replace(",", ".").split(".", 1)
    hours, minutes, seconds = [int(part) for part in time_part.split(":")]
    return hours * 3600 + minutes * 60 + seconds + int(ms_part) / 1000.0


def _visible_len(text: str) -> int:
    return len(compact_ws(text).replace(" ", ""))


def _split_long_piece(piece: str, max_chars: int) -> list[str]:
    piece = compact_ws(piece)
    if _visible_len(piece) <= max_chars:
        return [piece] if piece else []
    if " " in piece:
        chunks: list[str] = []
        current = ""
        for word in piece.split(" "):
            candidate = compact_ws(f"{current} {word}")
            if current and _visible_len(candidate) > max_chars:
                chunks.append(current)
                current = word
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks
    output_chunks: list[str] = []
    current = ""
    for char in piece:
        candidate = current + char
        if current and _visible_len(candidate) > max_chars:
            output_chunks.append(current)
            current = char
        else:
            current = candidate
    if current:
        output_chunks.append(current)
    return output_chunks


def split_subtitle_text(text: str, *, max_chars: int = 80) -> list[str]:
    text = compact_ws(text)
    if not text:
        return []
    text = re.sub(r"(?<=\d),(?=\d)", NUMBER_COMMA_PLACEHOLDER, text)
    pieces: list[str] = []
    parts = SPLIT_AFTER_RE.split(text)
    current = ""
    for part in parts:
        if not part:
            continue
        current += part
        if SPLIT_AFTER_RE.fullmatch(part):
            pieces.append(current)
            current = ""
    if current:
        pieces.append(current)

    chunks: list[str] = []
    current = ""
    for piece in pieces or [text]:
        piece = compact_ws(piece.replace(NUMBER_COMMA_PLACEHOLDER, ","))
        if not piece:
            continue
        candidate = compact_ws(current + piece)
        if current and _visible_len(candidate) > max_chars:
            chunks.extend(_split_long_piece(current, max_chars))
            current = piece
        else:
            current = candidate
    if current:
        chunks.extend(_split_long_piece(current, max_chars))
    return chunks


def _wrap_cue_text(text: str, *, max_line_chars: int = 42) -> str:
    chunks = split_subtitle_text(text, max_chars=max_line_chars)
    if not chunks:
        return compact_ws(text)
    return "\n".join(chunks)


def segments_to_cues(
    segments: list[dict[str, Any]],
    *,
    max_duration: float = 7.0,
    max_chars: int = 80,
    max_line_chars: int = 42,
    wrap_text: bool = True,
) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    for segment in segments:
        text = compact_ws(str(segment.get("text", "")))
        if not text:
            continue
        start_value = as_float(segment.get("start"))
        end_value = as_float(segment.get("end"))
        if start_value is None or end_value is None:
            continue
        start = max(0.0, start_value)
        end = max(start + 0.01, end_value)
        duration = end - start
        desired_parts = max(
            1, int(duration // max_duration) + (1 if duration % max_duration else 0)
        )
        text_parts = split_subtitle_text(text, max_chars=max_chars)
        if len(text_parts) < desired_parts:
            text_parts = split_subtitle_text(
                text, max_chars=max(1, int(_visible_len(text) / desired_parts))
            )
        text_parts = text_parts or [text]
        weights = [max(1, _visible_len(part)) for part in text_parts]
        total_weight = sum(weights)
        cursor = start
        for i, part in enumerate(text_parts):
            if i == len(text_parts) - 1:
                cue_end = end
            else:
                cue_duration = duration * (weights[i] / total_weight)
                cue_end = min(end, max(cursor + 0.01, cursor + cue_duration))
            cues.append(
                SubtitleCue(
                    index=len(cues) + 1,
                    start=cursor,
                    end=max(cursor + 0.01, cue_end),
                    text=_wrap_cue_text(part, max_line_chars=max_line_chars)
                    if wrap_text
                    else compact_ws(part),
                )
            )
            cursor = cue_end
    return cues


def cues_to_srt(cues: list[SubtitleCue]) -> str:
    blocks: list[str] = []
    for cue in cues:
        if not compact_ws(cue.text):
            continue
        blocks.append(
            f"{len(blocks) + 1}\n{seconds_to_srt_ts(cue.start)} --> {seconds_to_srt_ts(cue.end)}\n{cue.text}"
        )
    return "\n\n".join(blocks).strip() + "\n"


def cues_to_vtt(cues: list[SubtitleCue]) -> str:
    blocks = ["WEBVTT", ""]
    for cue in cues:
        if not compact_ws(cue.text):
            continue
        blocks.append(
            f"{seconds_to_vtt_ts(cue.start)} --> {seconds_to_vtt_ts(cue.end)}\n{cue.text}\n"
        )
    return "\n".join(blocks).strip() + "\n"


def segments_to_srt(
    segments: list[dict[str, Any]],
    *,
    max_duration: float = 7.0,
    max_chars: int = 80,
    max_line_chars: int = 42,
) -> str:
    return cues_to_srt(
        segments_to_cues(
            segments,
            max_duration=max_duration,
            max_chars=max_chars,
            max_line_chars=max_line_chars,
        )
    )


def segments_to_vtt(
    segments: list[dict[str, Any]],
    *,
    max_duration: float = 7.0,
    max_chars: int = 80,
    max_line_chars: int = 42,
) -> str:
    return cues_to_vtt(
        segments_to_cues(
            segments,
            max_duration=max_duration,
            max_chars=max_chars,
            max_line_chars=max_line_chars,
        )
    )


def validate_srt_text(
    text: str, *, max_chars: int = 80, max_line_chars: int = 42
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    stripped = text.strip()
    if not stripped:
        return [{"severity": "blocker", "type": "empty_srt", "message": "SRT file is empty"}]
    previous_end: float | None = None
    expected_index = 1
    for block_number, block in enumerate(re.split(r"\n\s*\n", stripped), start=1):
        lines = [line.rstrip("\n") for line in block.splitlines()]
        if len(lines) < 3:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "malformed_srt_block",
                    "message": f"SRT block {block_number} has fewer than three lines",
                }
            )
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "invalid_srt_index",
                    "message": f"SRT block {block_number} index is not an integer",
                }
            )
            index = expected_index
        if index != expected_index:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "srt_index_jump",
                    "expected": expected_index,
                    "actual": index,
                    "message": f"SRT index jump: expected {expected_index}, got {index}",
                }
            )
            expected_index = index
        expected_index += 1

        timestamp = SRT_TIMESTAMP_RE.match(lines[1].strip())
        if timestamp is None:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "invalid_srt_timestamp",
                    "index": index,
                    "message": f"SRT block {index} has invalid timestamp format",
                }
            )
            continue
        start = _timestamp_to_seconds(timestamp.group("start"))
        end = _timestamp_to_seconds(timestamp.group("end"))
        if end <= start:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "non_positive_srt_duration",
                    "index": index,
                    "start": start,
                    "end": end,
                    "message": f"SRT block {index} end must be greater than start",
                }
            )
        if previous_end is not None and start < previous_end:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "srt_overlap",
                    "index": index,
                    "start": start,
                    "previous_end": previous_end,
                    "message": f"SRT block {index} starts before previous block ends",
                }
            )
        previous_end = end

        cue_lines = lines[2:]
        cue_text = compact_ws(" ".join(cue_lines))
        if not cue_text:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "empty_subtitle",
                    "index": index,
                    "message": f"SRT block {index} has empty subtitle text",
                }
            )
        if _visible_len(cue_text) > max_chars:
            issues.append(
                {
                    "severity": "warning",
                    "type": "long_subtitle",
                    "index": index,
                    "chars": _visible_len(cue_text),
                    "message": f"SRT block {index} has {_visible_len(cue_text)} visible chars",
                }
            )
        for line in cue_lines:
            if _visible_len(line) > max_line_chars:
                issues.append(
                    {
                        "severity": "warning",
                        "type": "long_subtitle_line",
                        "index": index,
                        "chars": _visible_len(line),
                        "message": f"SRT block {index} has a line over {max_line_chars} chars",
                    }
                )
    return issues


def validate_vtt_text(text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    stripped = text.strip()
    if not stripped:
        return [{"severity": "blocker", "type": "empty_vtt", "message": "VTT file is empty"}]
    if not stripped.startswith("WEBVTT"):
        issues.append(
            {
                "severity": "blocker",
                "type": "missing_vtt_header",
                "message": "VTT missing WEBVTT header",
            }
        )
    previous_end: float | None = None
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        if "-->" not in line:
            continue
        timestamp = VTT_TIMESTAMP_RE.match(line.strip())
        if timestamp is None:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "invalid_vtt_timestamp",
                    "line": line_number,
                    "message": f"VTT line {line_number} has invalid timestamp format",
                }
            )
            continue
        start = _timestamp_to_seconds(timestamp.group("start"))
        end = _timestamp_to_seconds(timestamp.group("end"))
        if end <= start:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "non_positive_vtt_duration",
                    "line": line_number,
                    "message": f"VTT line {line_number} end must be greater than start",
                }
            )
        if previous_end is not None and start < previous_end:
            issues.append(
                {
                    "severity": "blocker",
                    "type": "vtt_overlap",
                    "line": line_number,
                    "message": f"VTT line {line_number} starts before previous cue ends",
                }
            )
        previous_end = end
    return issues
