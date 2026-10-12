from __future__ import annotations

import platform

from .models import DEFAULT_MODEL_ALIAS


def default_asr_backend() -> str:
    return "faster-whisper" if platform.system() == "Windows" else "mlx-whisper"


def default_asr_model() -> str:
    return DEFAULT_MODEL_ALIAS


def default_library_storage() -> str:
    return "local" if platform.system() == "Windows" else "icloud"
