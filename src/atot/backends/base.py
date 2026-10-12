from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
)


class ASRError(RuntimeError):
    pass


@dataclass(frozen=True)
class ASRTranscribeOptions:
    model: str
    language: str | None = "zh"
    prompt: str | None = None
    word_timestamps: bool = False
    condition_on_previous_text: bool = True
    temperature: float | tuple[float, ...] | None = 0.0
    no_speech_threshold: float | None = DEFAULT_NO_SPEECH_THRESHOLD
    logprob_threshold: float | None = DEFAULT_LOGPROB_THRESHOLD
    compression_ratio_threshold: float | None = DEFAULT_COMPRESSION_RATIO_THRESHOLD
    hallucination_silence_threshold: float | None = None
    extra_decode_options: dict[str, Any] = field(default_factory=dict)


class ASRBackend(Protocol):
    name: str
    supports_prompt: bool
    supports_word_timestamps: bool
    supports_diarization: bool

    def transcribe(
        self, audio_path: str | Path, options: ASRTranscribeOptions
    ) -> dict[str, Any]: ...


ASR_RESULT_CONTRACT: dict[str, Any] = {
    "required_top_level": ["text", "segments"],
    "segment_fields": ["id", "start", "end", "text", "words", "confidence", "raw"],
    "timing": "seconds, monotonic repair happens after backend normalization",
    "promotion_gate": "candidate gate plus semantic review before production registration",
}


def normalize_asr_result(payload: Any) -> dict[str, Any]:
    """Normalize backend-specific ASR payloads into the pipeline result contract."""
    if not isinstance(payload, dict):
        return {"text": str(payload), "segments": []}
    normalized = dict(payload)
    source_segments = payload.get("segments", [])
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(source_segments if isinstance(source_segments, list) else []):
        if not isinstance(segment, dict):
            continue
        try:
            start = float(segment.get("start", 0.0))
            end = float(segment.get("end", start))
        except (TypeError, ValueError):
            start = 0.0
            end = 0.0
        text = str(segment.get("text", "")).strip()
        item = dict(segment)
        item["id"] = (
            int(segment.get("id", index)) if str(segment.get("id", index)).isdigit() else index
        )
        item["start"] = max(0.0, start)
        item["end"] = max(item["start"] + 0.01, end)
        item["text"] = text
        item["words"] = segment.get("words") if isinstance(segment.get("words"), list) else []
        item["confidence"] = segment.get("confidence")
        item["raw"] = segment.get("raw") if isinstance(segment.get("raw"), dict) else dict(segment)
        segments.append(item)
    normalized["segments"] = segments
    if not str(normalized.get("text", "")).strip():
        normalized["text"] = "".join(str(segment.get("text", "")) for segment in segments)
    return normalized
