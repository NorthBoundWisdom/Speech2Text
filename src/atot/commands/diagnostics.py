from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys

from ..audio import optional_command
from ..backends.registry import doctor_backend
from ..models import describe_models
from ..paths import path_context
from ..platform_defaults import default_asr_backend
from ..runinfo import machine_info
from ..ui import UiOptions, serve_ui
from ..windows_runtime import is_windows, windows_runtime_payload


def doctor_payload() -> dict[str, object]:
    ffmpeg = optional_command("ffmpeg")
    ffprobe = optional_command("ffprobe")
    afconvert = shutil.which("afconvert")
    afinfo = shutil.which("afinfo")
    backend = default_asr_backend()
    backend_payload = doctor_backend(backend)
    windows_runtime = windows_runtime_payload() if is_windows() else None
    return {
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "data_root": str(path_context().data_root),
        "env_dir": str(path_context().env_dir),
        "model_dir": str(path_context().model_dir),
        "asr_backend": backend,
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "afconvert": afconvert,
        "afinfo": afinfo,
        "audio_prepare_available": bool(ffmpeg or afconvert),
        "audio_duration_available": bool(ffprobe or afinfo),
        "mlx_whisper_importable": importlib.util.find_spec("mlx_whisper") is not None,
        "faster_whisper_importable": importlib.util.find_spec("faster_whisper") is not None,
        "ctranslate2_importable": importlib.util.find_spec("ctranslate2") is not None,
        "backend": backend_payload,
        "windows_runtime": windows_runtime,
        "action_required": _action_required(
            audio_prepare_available=bool(ffmpeg or afconvert),
            audio_duration_available=bool(ffprobe or afinfo),
            backend_payload=backend_payload,
            windows_runtime=windows_runtime,
        ),
        "machine_info": machine_info(),
    }


def doctor_success(payload: dict[str, object]) -> bool:
    cpu_explicit = os.environ.get("ATOT_FASTER_WHISPER_DEVICE", "").lower() == "cpu"
    windows_runtime = payload.get("windows_runtime")
    action_required = payload.get("action_required")
    if is_windows() and not cpu_explicit and isinstance(action_required, list) and action_required:
        return False
    if is_windows() and not cpu_explicit and isinstance(windows_runtime, dict):
        probe = windows_runtime.get("ctranslate2_cuda_probe")
        if isinstance(probe, dict) and probe.get("success") is False:
            return False
    return bool(
        payload["audio_prepare_available"]
        and payload["audio_duration_available"]
        and (
            payload["faster_whisper_importable"]
            if payload.get("asr_backend") == "faster-whisper"
            else payload["mlx_whisper_importable"]
        )
    )


def models_payload() -> list[dict[str, str]]:
    return describe_models()


def cmd_doctor(args: argparse.Namespace) -> int:
    payload = doctor_payload()
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key in (
            "python_executable",
            "data_root",
            "env_dir",
            "model_dir",
            "ffmpeg",
            "ffprobe",
            "afconvert",
            "afinfo",
            "asr_backend",
            "audio_prepare_available",
            "audio_duration_available",
            "mlx_whisper_importable",
            "faster_whisper_importable",
            "ctranslate2_importable",
        ):
            print(f"{key}: {payload[key]}")
        print("backend:")
        print(json.dumps(payload["backend"], ensure_ascii=False, indent=2))
        if payload.get("windows_runtime") is not None:
            print("windows_runtime:")
            print(json.dumps(payload["windows_runtime"], ensure_ascii=False, indent=2))
        action_required = payload.get("action_required")
        if isinstance(action_required, list) and action_required:
            print("action_required:")
            for item in action_required:
                print(f"- {item}")
        print("machine_info:")
        print(json.dumps(payload["machine_info"], ensure_ascii=False, indent=2))
    return 0 if doctor_success(payload) else 1


def _action_required(
    *,
    audio_prepare_available: bool,
    audio_duration_available: bool,
    backend_payload: dict[str, object],
    windows_runtime: dict[str, object] | None,
) -> list[str]:
    actions: list[str] = []
    if not audio_prepare_available:
        actions.append("Install ffmpeg or make afconvert available for audio preparation.")
    if not audio_duration_available:
        actions.append(
            "Install ffmpeg/ffprobe or make afinfo available for audio duration probing."
        )
    backend_doctor = backend_payload.get("doctor")
    if isinstance(backend_doctor, dict):
        diagnostics = backend_doctor.get("diagnostics")
        if isinstance(diagnostics, list):
            actions.extend(str(item) for item in diagnostics)
    if windows_runtime is not None:
        runtime_actions = windows_runtime.get("action_required")
        if isinstance(runtime_actions, list):
            actions.extend(str(item) for item in runtime_actions)
    return list(dict.fromkeys(actions))


def cmd_models(args: argparse.Namespace) -> int:
    rows = models_payload()
    if args.json_output:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(f"{row['alias']:<20} {row['repo']}  # {row['note']}")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    serve_ui(UiOptions(host=args.host, port=args.port))
    return 0
