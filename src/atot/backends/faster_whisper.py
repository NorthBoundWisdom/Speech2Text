from __future__ import annotations

import os
import platform
import time
from pathlib import Path
from typing import Any, cast

from ..models import (
    DEFAULT_MODEL_ALIAS,
    local_model_dir,
    missing_required_local_paths,
    model_entry,
    resolve_model,
)
from ..utils import json_safe
from ..windows_runtime import add_windows_gpu_dll_directories, enhance_cuda_error, is_windows
from .base import ASRError, ASRTranscribeOptions, normalize_asr_result


DEFAULT_FAST_WHISPER_MODEL = "faster-whisper-large-v3-turbo"


class FasterWhisperBackend:
    name = "faster-whisper"
    supports_prompt = True
    supports_word_timestamps = True
    supports_diarization = False

    def __init__(
        self,
        *,
        verbose: bool | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self.verbose = verbose
        self.device = device or os.environ.get("ATOT_FASTER_WHISPER_DEVICE") or _default_device()
        self.compute_type = (
            compute_type
            or os.environ.get("ATOT_FASTER_WHISPER_COMPUTE_TYPE")
            or ("int8_float16" if self.device == "cuda" else "int8")
        )
        if is_windows() and self.device == "cuda":
            add_windows_gpu_dll_directories()
        self._model: Any | None = None
        self._model_path: str | None = None

    def transcribe(self, audio_path: str | Path, options: ASRTranscribeOptions) -> dict[str, Any]:
        model_path = resolve_faster_whisper_model(options.model)
        model = self._load_model(model_path)
        kwargs: dict[str, Any] = {
            "language": options.language,
            "initial_prompt": options.prompt,
            "word_timestamps": options.word_timestamps,
            "condition_on_previous_text": options.condition_on_previous_text,
            "temperature": options.temperature if options.temperature is not None else 0.0,
            "no_speech_threshold": options.no_speech_threshold,
            "log_prob_threshold": options.logprob_threshold,
            "compression_ratio_threshold": options.compression_ratio_threshold,
        }
        if options.extra_decode_options:
            kwargs.update(options.extra_decode_options)
        kwargs = {key: value for key, value in kwargs.items() if value is not None}

        start = time.perf_counter()
        try:
            segments_iter, info = model.transcribe(str(audio_path), **kwargs)
            segments = [
                _segment_to_dict(segment, index) for index, segment in enumerate(segments_iter)
            ]
        except Exception as exc:  # pragma: no cover - depends on local CUDA/runtime install.
            message = enhance_cuda_error(f"faster_whisper transcribe failed: {exc}", exc)
            raise ASRError(message) from exc
        runtime = time.perf_counter() - start

        payload = normalize_asr_result(
            {
                "text": "".join(segment["text"] for segment in segments),
                "segments": segments,
                "language": getattr(info, "language", None),
                "language_probability": getattr(info, "language_probability", None),
            }
        )
        payload["runtime_seconds"] = runtime
        payload["device"] = self.device
        payload["compute_type"] = self.compute_type
        return cast(dict[str, Any], json_safe(payload))

    def _load_model(self, model_path: str) -> Any:
        if self._model is not None and self._model_path == model_path:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - depends on optional install.
            raise ASRError(
                "Could not import faster_whisper. Install the Windows ASR dependencies."
            ) from exc
        try:
            self._model = WhisperModel(
                model_path, device=self.device, compute_type=self.compute_type
            )
        except Exception as exc:  # pragma: no cover - depends on local CUDA/runtime install.
            message = (
                f"Could not load faster-whisper model `{model_path}` on device `{self.device}` "
                f"with compute_type `{self.compute_type}`: {exc}"
            )
            raise ASRError(enhance_cuda_error(message, exc)) from exc
        self._model_path = model_path
        return self._model


def _default_device() -> str:
    return "cuda" if platform.system() == "Windows" else "auto"


def faster_whisper_model_name(model: str | None) -> str:
    if not model or model in {DEFAULT_MODEL_ALIAS, "mlx-community/whisper-large-v3-turbo"}:
        return DEFAULT_FAST_WHISPER_MODEL
    return model


def resolve_faster_whisper_model(model: str | None) -> str:
    model_name = faster_whisper_model_name(model)
    missing = missing_required_local_paths(model_name)
    if missing:
        raise ASRError(missing_faster_whisper_model_message(model_name, missing))
    return resolve_model(model_name)


def missing_faster_whisper_model_message(
    model_name: str, missing: tuple[Path, ...] | list[Path]
) -> str:
    target_dir = local_model_dir(model_name)
    lines = [
        f"Required faster-whisper model files are missing for `{model_name}`.",
        f"Place the files under `{target_dir}`.",
        "Missing files:",
        *(f"- {path}" for path in missing),
    ]
    entry = model_entry(model_name)
    if entry is not None and entry.required_files:
        lines.append("Manual download URLs:")
        lines.extend(f"- {item.url} -> {item.path}" for item in entry.required_files)
    return "\n".join(lines)


def _segment_to_dict(segment: Any, index: int) -> dict[str, Any]:
    words = []
    for word in getattr(segment, "words", None) or []:
        words.append(
            {
                "word": getattr(word, "word", ""),
                "start": getattr(word, "start", None),
                "end": getattr(word, "end", None),
                "probability": getattr(word, "probability", None),
            }
        )
    return {
        "id": index,
        "start": getattr(segment, "start", 0.0),
        "end": getattr(segment, "end", getattr(segment, "start", 0.0)),
        "text": str(getattr(segment, "text", "")).strip(),
        "words": words,
        "avg_logprob": getattr(segment, "avg_logprob", None),
        "compression_ratio": getattr(segment, "compression_ratio", None),
        "no_speech_prob": getattr(segment, "no_speech_prob", None),
        "raw": json_safe(segment),
    }
