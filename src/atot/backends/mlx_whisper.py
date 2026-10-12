from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import Any

from ..models import resolve_model
from ..utils import json_safe
from .base import ASRError, ASRTranscribeOptions, normalize_asr_result


def _load_wav_as_float32(path: Path) -> Any:
    import numpy as np

    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())

    if sample_rate != 16_000:
        raise ASRError(f"Expected 16 kHz WAV chunk, got {sample_rate} Hz: {path}")
    if sample_width == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    elif sample_width == 1:
        audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ASRError(f"Unsupported WAV sample width {sample_width} bytes: {path}")
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio


class MlxWhisperBackend:
    name = "mlx-whisper"
    supports_prompt = True
    supports_word_timestamps = True
    supports_diarization = False

    def __init__(self, *, verbose: bool | None = None) -> None:
        self.verbose = verbose

    def transcribe(self, audio_path: str | Path, options: ASRTranscribeOptions) -> dict[str, Any]:
        try:
            import mlx_whisper
        except Exception as exc:  # pragma: no cover - depends on local MLX install
            raise ASRError(
                "Could not import mlx_whisper. Install dependencies with `pip install -e .` "
                "or `pip install mlx-whisper`."
            ) from exc

        kwargs: dict[str, Any] = {
            "path_or_hf_repo": resolve_model(options.model),
            "language": options.language,
            "initial_prompt": options.prompt,
            "word_timestamps": options.word_timestamps,
            "condition_on_previous_text": options.condition_on_previous_text,
            "temperature": options.temperature if options.temperature is not None else 0.0,
            "no_speech_threshold": options.no_speech_threshold,
            "logprob_threshold": options.logprob_threshold,
            "compression_ratio_threshold": options.compression_ratio_threshold,
            "verbose": self.verbose,
        }
        if options.hallucination_silence_threshold is not None:
            kwargs["hallucination_silence_threshold"] = options.hallucination_silence_threshold
        if options.extra_decode_options:
            kwargs.update(options.extra_decode_options)

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        start = time.perf_counter()
        audio_input: str | Any = str(audio_path)
        path = Path(audio_path)
        if path.suffix.lower() == ".wav":
            audio_input = _load_wav_as_float32(path)

        try:
            result = mlx_whisper.transcribe(audio_input, **kwargs)
        except Exception as exc:
            raise ASRError(f"mlx_whisper.transcribe failed: {exc}") from exc
        runtime = time.perf_counter() - start

        payload = json_safe(result)
        payload = normalize_asr_result(payload)
        payload["runtime_seconds"] = runtime
        return payload
