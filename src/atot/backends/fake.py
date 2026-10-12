from __future__ import annotations

import wave
from pathlib import Path

from .base import ASRTranscribeOptions


class FakeBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(
        self, audio_path: str | Path, options: ASRTranscribeOptions
    ) -> dict[str, object]:
        duration = _wav_duration(Path(audio_path))
        end = max(0.01, duration)
        text = "这是 fake backend 转写。"
        return {
            "text": text,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": end,
                    "text": text,
                    "confidence": 1.0,
                }
            ],
            "language": options.language,
        }


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            return wav.getnframes() / rate if rate else 0.0
    except (wave.Error, FileNotFoundError):
        return 0.0
