from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable

from ..audio import (
    AudioError,
    ChunkSpec,
    compute_chunks,
    materialize_chunk_specs,
    materialize_chunks,
)
from .identity import _sha256_json
from ..runinfo import now_iso
from ..utils import read_json, write_json_atomic
from ..vad import build_smart_chunks, detect_silences_for_chunking


AUTO_CHUNKING = "auto"
AUTO_SMART_MIN_DURATION = 30 * 60
AUTO_SMART_TARGET_CHUNK_LENGTH = 15 * 60
AUTO_SMART_MAX_CHUNK_LENGTH = 20 * 60


@dataclass(frozen=True)
class ChunkMaterializationResult:
    chunking_plan: dict[str, Any]
    silence_detection: dict[str, Any] | None
    planned_chunk_specs: list[ChunkSpec]
    chunk_specs: list[ChunkSpec]
    chunk_layout: dict[str, Any]
    effective_chunk_length: float
    effective_max_chunk_length: float
    rewrite_chunks: bool


def _round_time(value: Any) -> float:
    return round(float(value), 6)


def _normalized_chunk_spec(payload: dict[str, Any]) -> dict[str, Any]:
    source_start = _round_time(payload.get("source_start", 0.0))
    source_end = _round_time(payload.get("source_end", source_start))
    return {
        "index": int(payload.get("index", 0)),
        "source_start": source_start,
        "source_end": source_end,
        "core_start": _round_time(payload.get("core_start", source_start)),
        "core_end": _round_time(payload.get("core_end", source_end)),
        "duration": _round_time(payload.get("duration", source_end - source_start)),
    }


def _payload_matches_chunk(payload: dict[str, Any], expected: ChunkSpec) -> bool:
    chunk = payload.get("chunk")
    if not isinstance(chunk, dict):
        return False
    try:
        return _normalized_chunk_spec(chunk) == _normalized_chunk_spec(expected.to_json())
    except (TypeError, ValueError):
        return False


def _chunk_layout_fingerprint(
    *,
    options: Any,
    audio_duration: float,
    chunk_specs: list[ChunkSpec],
    chunking: str | None = None,
    chunk_length: float | None = None,
    max_chunk_length: float | None = None,
    silence_threshold: float | None = None,
    silence_detection: dict[str, Any] | None = None,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    effective_chunking = chunking or options.chunking
    effective_chunk_length = chunk_length or options.chunk_length
    effective_max_chunk_length = (
        max_chunk_length or options.max_chunk_length or effective_chunk_length
    )
    return {
        "version": 2,
        "sample_rate": options.sample_rate,
        "audio_duration": _round_time(audio_duration),
        "requested_chunking": options.chunking,
        "chunking": effective_chunking,
        "chunk_length": _round_time(effective_chunk_length),
        "max_chunk_length": _round_time(effective_max_chunk_length),
        "silence_threshold": silence_threshold
        if silence_threshold is not None
        else options.silence_threshold,
        "silence_detection": silence_detection or {},
        "fallback_reason": fallback_reason or "",
        "min_silence": options.min_silence,
        "overlap": _round_time(options.overlap),
        "chunks": [_normalized_chunk_spec(spec.to_json()) for spec in chunk_specs],
    }


def _chunk_layout_matches(manifest_path: Path, expected: dict[str, Any]) -> bool:
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        return False
    try:
        payload = read_json(manifest_path)
    except (OSError, JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    expected_hash = _sha256_json(expected)
    return payload.get("chunk_layout_sha256") == expected_hash


def _write_chunk_layout_manifest(manifest_path: Path, chunk_layout: dict[str, Any]) -> None:
    write_json_atomic(
        manifest_path,
        {
            "created_at": now_iso(),
            "chunk_layout": chunk_layout,
            "chunk_layout_sha256": _sha256_json(chunk_layout),
        },
    )


def _resolve_chunking_plan(options: Any, *, audio_duration: float) -> dict[str, Any]:
    requested = options.chunking or AUTO_CHUNKING
    if requested not in {AUTO_CHUNKING, "fixed", "smart"}:
        raise ValueError(f"Unknown chunking strategy: {requested}")
    if requested == AUTO_CHUNKING:
        if audio_duration >= max(AUTO_SMART_MIN_DURATION, options.chunk_length * 1.25):
            target = min(options.chunk_length, AUTO_SMART_TARGET_CHUNK_LENGTH)
            return {
                "requested_chunking": requested,
                "chunking": "smart",
                "chunk_length": target,
                "max_chunk_length": options.max_chunk_length
                or max(target, AUTO_SMART_MAX_CHUNK_LENGTH),
                "fallback_reason": "",
            }
        return {
            "requested_chunking": requested,
            "chunking": "fixed",
            "chunk_length": options.chunk_length,
            "max_chunk_length": options.max_chunk_length or options.chunk_length,
            "fallback_reason": "short_audio_auto_fixed",
        }
    return {
        "requested_chunking": requested,
        "chunking": requested,
        "chunk_length": options.chunk_length,
        "max_chunk_length": options.max_chunk_length or options.chunk_length,
        "fallback_reason": "",
    }


def plan_and_materialize_chunks(
    *,
    options: Any,
    prepared_wav: Path,
    chunks_dir: Path,
    chunk_manifest_path: Path,
    audio_duration: float,
    force_prepare: bool,
    detect_silences: Callable[
        ..., tuple[list[Any], dict[str, Any] | None]
    ] = detect_silences_for_chunking,
    build_smart: Callable[..., list[ChunkSpec]] = build_smart_chunks,
    compute_fixed: Callable[..., list[ChunkSpec]] = compute_chunks,
    materialize_smart: Callable[..., list[ChunkSpec]] = materialize_chunk_specs,
    materialize_fixed: Callable[..., list[ChunkSpec]] = materialize_chunks,
) -> ChunkMaterializationResult:
    chunking_plan = _resolve_chunking_plan(options, audio_duration=audio_duration)
    silence_detection: dict[str, Any] | None = None
    silences: list[Any] = []
    if chunking_plan["chunking"] == "smart":
        try:
            silences, silence_detection = detect_silences(
                prepared_wav,
                duration=audio_duration,
                silence_threshold=options.silence_threshold,
                min_silence=options.min_silence,
            )
        except AudioError:
            if options.chunking != AUTO_CHUNKING:
                raise
            chunking_plan = {
                **chunking_plan,
                "chunking": "fixed",
                "chunk_length": options.chunk_length,
                "max_chunk_length": options.max_chunk_length or options.chunk_length,
                "fallback_reason": "smart_silence_detection_failed",
            }
            silences = []
            silence_detection = {"error": "smart_silence_detection_failed"}

    effective_chunk_length = float(chunking_plan["chunk_length"])
    effective_max_chunk_length = float(chunking_plan["max_chunk_length"])
    if chunking_plan["chunking"] == "smart":
        planned_chunk_specs = build_smart(
            audio_duration,
            chunks_dir=chunks_dir,
            target_chunk_length=effective_chunk_length,
            max_chunk_length=effective_max_chunk_length,
            overlap=options.overlap,
            silences=silences,
        )
    else:
        planned_chunk_specs = compute_fixed(
            audio_duration,
            chunks_dir=chunks_dir,
            chunk_length=effective_chunk_length,
            overlap=options.overlap,
        )

    chunk_layout = _chunk_layout_fingerprint(
        options=options,
        audio_duration=audio_duration,
        chunk_specs=planned_chunk_specs,
        chunking=str(chunking_plan["chunking"]),
        chunk_length=effective_chunk_length,
        max_chunk_length=effective_max_chunk_length,
        silence_threshold=(
            float(silence_detection["threshold"])
            if isinstance(silence_detection, dict) and "threshold" in silence_detection
            else options.silence_threshold
        ),
        silence_detection=silence_detection,
        fallback_reason=str(chunking_plan.get("fallback_reason") or ""),
    )
    rewrite_chunks = (
        options.force_chunks
        or force_prepare
        or not _chunk_layout_matches(chunk_manifest_path, chunk_layout)
    )
    if chunking_plan["chunking"] == "smart":
        chunk_specs = materialize_smart(prepared_wav, planned_chunk_specs, overwrite=rewrite_chunks)
    else:
        chunk_specs = materialize_fixed(
            prepared_wav,
            chunks_dir,
            chunk_length=effective_chunk_length,
            overlap=options.overlap,
            overwrite=rewrite_chunks,
            duration=audio_duration,
        )
    _write_chunk_layout_manifest(chunk_manifest_path, chunk_layout)
    return ChunkMaterializationResult(
        chunking_plan=chunking_plan,
        silence_detection=silence_detection,
        planned_chunk_specs=planned_chunk_specs,
        chunk_specs=chunk_specs,
        chunk_layout=chunk_layout,
        effective_chunk_length=effective_chunk_length,
        effective_max_chunk_length=effective_max_chunk_length,
        rewrite_chunks=rewrite_chunks,
    )
