from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..audio import ChunkSpec
from .chunks import _payload_matches_chunk
from .identity import _payload_matches_fingerprint
from ..utils import read_json, valid_json_file


@dataclass(frozen=True)
class ASRChunkCacheDecision:
    payload: dict[str, Any]
    status: str
    should_transcribe: bool


def _chunk_cache_decision(
    json_path: Path,
    spec: ChunkSpec,
    transcription_fingerprint: dict[str, Any],
    *,
    force_transcribe: bool = False,
) -> ASRChunkCacheDecision:
    if valid_json_file(json_path) and not force_transcribe:
        payload = read_json(json_path)
        if _payload_matches_fingerprint(
            payload, transcription_fingerprint
        ) and _payload_matches_chunk(payload, spec):
            return ASRChunkCacheDecision(
                payload=payload, status="skipped_existing", should_transcribe=False
            )
        return ASRChunkCacheDecision(payload={}, status="cache_mismatch", should_transcribe=True)
    return ASRChunkCacheDecision(payload={}, status="missing_or_forced", should_transcribe=True)
