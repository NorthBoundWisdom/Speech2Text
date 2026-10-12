from __future__ import annotations

from .base import (
    ASRBackend,
    ASRError,
    ASRTranscribeOptions,
    ASR_RESULT_CONTRACT,
    normalize_asr_result,
)
from .fake import FakeBackend
from .faster_whisper import FasterWhisperBackend
from .mlx_whisper import MlxWhisperBackend
from .recording import RecordingBackend
from .registry import (
    BackendSpec,
    backend_names,
    build_backend,
    doctor_backend,
    get_backend_spec,
    resolve_backend_model,
)

__all__ = [
    "ASRBackend",
    "ASRError",
    "ASR_RESULT_CONTRACT",
    "ASRTranscribeOptions",
    "BackendSpec",
    "FakeBackend",
    "FasterWhisperBackend",
    "MlxWhisperBackend",
    "RecordingBackend",
    "backend_names",
    "build_backend",
    "doctor_backend",
    "get_backend_spec",
    "normalize_asr_result",
    "resolve_backend_model",
]
