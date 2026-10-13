from __future__ import annotations

import hashlib
import json
from typing import Any

from ..asr_guard import DECODE_GUARD_FINGERPRINT
from ..rules import rule_set_fingerprint
from ..utils import json_safe


def _sha256_json(payload: Any) -> str:
    text = json.dumps(json_safe(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_text(text: str | None) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _transcription_fingerprint(
    *,
    backend_name: str,
    model: str,
    options: Any,
    prompt: str | None,
    input_sha256: str | None = None,
    prepared_audio_sha256: str | None = None,
    chunk_layout_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "version": 2,
        "backend": backend_name,
        "model": model,
        "input_sha256": input_sha256,
        "prepared_audio_sha256": prepared_audio_sha256,
        "chunk_layout_sha256": chunk_layout_sha256,
        "language": options.language,
        "requested_languages": list(options.requested_languages),
        "prompt_sha256": _sha256_text(prompt),
        "word_timestamps": options.word_timestamps,
        "condition_on_previous_text": options.condition_on_previous_text,
        "temperature": options.temperature,
        "no_speech_threshold": options.no_speech_threshold,
        "logprob_threshold": options.logprob_threshold,
        "compression_ratio_threshold": options.compression_ratio_threshold,
        "hallucination_silence_threshold": options.hallucination_silence_threshold,
        "profile": options.profile,
        "decode_guard": DECODE_GUARD_FINGERPRINT,
    }


def _postprocess_fingerprint(
    glossary: dict[str, Any] | None,
    *,
    rule_packs: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    rule_set = rule_set_fingerprint(rule_packs)
    return {
        "version": 4,
        "glossary_sha256": _sha256_json(glossary or {}),
        "rule_set": rule_set,
        "rule_set_sha256": _sha256_json(rule_set),
        "correction_pipeline": "builtin-corrections-and-review-v3",
    }


def _payload_matches_fingerprint(payload: dict[str, Any], expected: dict[str, Any]) -> bool:
    expected_hash = _sha256_json(expected)
    return payload.get("transcription_fingerprint_sha256") == expected_hash
