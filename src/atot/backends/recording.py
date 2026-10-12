from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import read_json
from .base import ASRError, ASRTranscribeOptions, normalize_asr_result


class RecordingBackend:
    name = "recording"
    supports_prompt = True
    supports_word_timestamps = True
    supports_diarization = False

    def __init__(self, recording_path: Path | None) -> None:
        if recording_path is None:
            raise ASRError("recording backend requires --recording-json.")
        self.recording_path = recording_path.expanduser()
        self._payloads = _load_recording_payloads(self.recording_path)
        self._index = 0

    def transcribe(self, audio_path: str | Path, options: ASRTranscribeOptions) -> dict[str, Any]:
        if self._index >= len(self._payloads):
            raise ASRError(
                f"Recording fixture has no payload for chunk {self._index}: {self.recording_path}"
            )
        payload = self._payloads[self._index]
        self._index += 1
        return normalize_asr_result(payload)


def _load_recording_payloads(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, list):
        return [_result_payload(item) for item in payload]
    if not isinstance(payload, dict):
        raise ASRError(f"Recording fixture root must be an object or list: {path}")
    chunks = payload.get("chunks")
    if isinstance(chunks, list):
        return [_result_payload(item) for item in chunks]
    return [_result_payload(payload)]


def _result_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ASRError("Recording fixture payloads must be JSON objects.")
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    return payload
