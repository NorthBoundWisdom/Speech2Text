from __future__ import annotations

import importlib.util
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import (
    DEFAULT_MODEL_ALIAS,
    describe_models,
    local_model_dir,
    missing_required_local_paths,
    resolve_model,
)
from ..runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
)
from ..windows_runtime import windows_runtime_payload
from .base import ASRBackend, ASRError, ASR_RESULT_CONTRACT
from .fake import FakeBackend
from .faster_whisper import (
    DEFAULT_FAST_WHISPER_MODEL,
    FasterWhisperBackend,
    missing_faster_whisper_model_message,
    resolve_faster_whisper_model,
)
from .mlx_whisper import MlxWhisperBackend
from .recording import RecordingBackend


@dataclass(frozen=True)
class BackendSpec:
    name: str
    status: str
    capabilities: dict[str, bool]
    default_decode_options: dict[str, Any]
    model_aliases: list[str] = field(default_factory=list)
    factory: Callable[..., ASRBackend] | None = None
    model_resolver: Callable[[str | None], str] = resolve_model
    doctor: Callable[[], dict[str, Any]] | None = None
    notes: str = ""
    promotion_requirements: tuple[str, ...] = (
        "candidate_gate_pass",
        "semantic_review_pass",
        "same_sample_baseline_comparison",
    )

    @property
    def transcribable(self) -> bool:
        return self.factory is not None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "transcribable": self.transcribable,
            "capabilities": self.capabilities,
            "default_decode_options": self.default_decode_options,
            "model_aliases": self.model_aliases,
            "notes": self.notes,
            "result_contract": ASR_RESULT_CONTRACT,
            "promotion_requirements": list(self.promotion_requirements),
        }


DEFAULT_DECODE_OPTIONS: dict[str, Any] = {
    "language": "zh",
    "word_timestamps": False,
    "condition_on_previous_text": True,
    "temperature": 0.0,
    "no_speech_threshold": DEFAULT_NO_SPEECH_THRESHOLD,
    "logprob_threshold": DEFAULT_LOGPROB_THRESHOLD,
    "compression_ratio_threshold": DEFAULT_COMPRESSION_RATIO_THRESHOLD,
}


def _model_aliases() -> list[str]:
    return [str(row["alias"]) for row in describe_models()]


def _mlx_doctor() -> dict[str, Any]:
    model_path = resolve_model(DEFAULT_MODEL_ALIAS)
    path = Path(model_path).expanduser()
    model_available = path.exists() if path.is_absolute() else True
    importable = importlib.util.find_spec("mlx_whisper") is not None
    return {
        "success": importable and model_available,
        "importable": importable,
        "default_model": DEFAULT_MODEL_ALIAS,
        "resolved_model": model_path,
        "model_available": model_available,
        "diagnostics": [
            *(["mlx_whisper is not importable"] if not importable else []),
            *(["default model path is missing"] if not model_available else []),
        ],
    }


def _fake_doctor() -> dict[str, Any]:
    return {"success": True, "diagnostics": []}


def _recording_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "diagnostics": ["recording backend requires --recording-json for transcription"],
    }


def _faster_whisper_doctor() -> dict[str, Any]:
    importable = importlib.util.find_spec("faster_whisper") is not None
    ctranslate2_importable = importlib.util.find_spec("ctranslate2") is not None
    missing_model_files = missing_required_local_paths(DEFAULT_FAST_WHISPER_MODEL)
    model_available = not missing_model_files
    model_path = (
        resolve_model(DEFAULT_FAST_WHISPER_MODEL)
        if model_available
        else str(local_model_dir(DEFAULT_FAST_WHISPER_MODEL))
    )
    diagnostics = [
        *(["faster_whisper is not importable"] if not importable else []),
        *(["ctranslate2 is not importable"] if not ctranslate2_importable else []),
        *(
            [missing_faster_whisper_model_message(DEFAULT_FAST_WHISPER_MODEL, missing_model_files)]
            if not model_available
            else []
        ),
    ]
    load_model_probe = _faster_whisper_model_load_probe if importable and model_available else None
    runtime = windows_runtime_payload(load_model_probe=load_model_probe)
    ctranslate2_probe = runtime.get("ctranslate2_cuda_probe", {})
    cuda_device_count = (
        ctranslate2_probe.get("cuda_device_count") if isinstance(ctranslate2_probe, dict) else None
    )
    action_required = runtime.get("action_required")
    if isinstance(action_required, list):
        diagnostics.extend(str(item) for item in action_required)
    return {
        "success": importable and ctranslate2_importable and model_available and not diagnostics,
        "importable": importable,
        "ctranslate2_importable": ctranslate2_importable,
        "default_model": DEFAULT_FAST_WHISPER_MODEL,
        "resolved_model": model_path,
        "model_available": model_available,
        "missing_model_files": [str(path) for path in missing_model_files],
        "cuda_device_count": cuda_device_count,
        "windows_runtime": runtime,
        "diagnostics": diagnostics,
    }


def _external_command_doctor(command: str, *, note: str) -> dict[str, Any]:
    executable = shutil.which(command)
    return {
        "success": executable is not None,
        "executable": executable,
        "diagnostics": [] if executable else [f"{command} is not on PATH"],
        "note": note,
    }


def _faster_whisper_model_load_probe() -> dict[str, Any]:
    model_path = resolve_model(DEFAULT_FAST_WHISPER_MODEL)
    backend = FasterWhisperBackend(verbose=False)
    backend._load_model(model_path)
    return {"success": True, "device": backend.device, "compute_type": backend.compute_type}


BACKEND_REGISTRY: dict[str, BackendSpec] = {
    "mlx-whisper": BackendSpec(
        name="mlx-whisper",
        status="production",
        capabilities={"prompt": True, "word_timestamps": True, "diarization": False},
        default_decode_options=DEFAULT_DECODE_OPTIONS,
        model_aliases=_model_aliases(),
        factory=lambda *, verbose=None, recording_json=None: MlxWhisperBackend(verbose=verbose),
        doctor=_mlx_doctor,
        notes="Stable production backend for Apple Silicon.",
    ),
    "fake": BackendSpec(
        name="fake",
        status="test",
        capabilities={"prompt": True, "word_timestamps": False, "diarization": False},
        default_decode_options=DEFAULT_DECODE_OPTIONS,
        model_aliases=[],
        factory=lambda *, verbose=None, recording_json=None: FakeBackend(),
        doctor=_fake_doctor,
        notes="Deterministic test backend.",
    ),
    "recording": BackendSpec(
        name="recording",
        status="test",
        capabilities={"prompt": True, "word_timestamps": True, "diarization": False},
        default_decode_options=DEFAULT_DECODE_OPTIONS,
        model_aliases=[],
        factory=lambda *, verbose=None, recording_json=None: RecordingBackend(recording_json),
        doctor=_recording_doctor,
        notes="Fixture replay backend.",
    ),
    "faster-whisper": BackendSpec(
        name="faster-whisper",
        status="candidate",
        capabilities={"prompt": True, "word_timestamps": True, "diarization": False},
        default_decode_options=DEFAULT_DECODE_OPTIONS,
        model_aliases=[DEFAULT_MODEL_ALIAS, DEFAULT_FAST_WHISPER_MODEL, "faster-whisper-large-v3"],
        factory=lambda *, verbose=None, recording_json=None: FasterWhisperBackend(verbose=verbose),
        model_resolver=resolve_faster_whisper_model,
        doctor=_faster_whisper_doctor,
        notes="Windows CLI target backend using CTranslate2/faster-whisper.",
    ),
    "funasr": BackendSpec(
        name="funasr",
        status="candidate",
        capabilities={"prompt": False, "word_timestamps": False, "diarization": True},
        default_decode_options={},
        model_aliases=[],
        doctor=lambda: _external_command_doctor(
            "funasr",
            note="External comparator only; must pass candidate gate before promotion.",
        ),
        notes="Chinese ASR candidate; not wired into production transcription.",
    ),
    "sensevoice": BackendSpec(
        name="sensevoice",
        status="candidate",
        capabilities={"prompt": False, "word_timestamps": True, "diarization": False},
        default_decode_options={},
        model_aliases=[],
        doctor=lambda: _external_command_doctor(
            "funasr",
            note="SenseVoice is evaluated through the isolated FunASR toolchain.",
        ),
        notes="Candidate backend target; use candidate scripts for benchmarking.",
    ),
    "whisper.cpp": BackendSpec(
        name="whisper.cpp",
        status="candidate",
        capabilities={"prompt": True, "word_timestamps": True, "diarization": False},
        default_decode_options={},
        model_aliases=[],
        doctor=lambda: _external_command_doctor(
            "whisper-cli",
            note="External comparator only; not a production backend.",
        ),
        notes="Candidate backend target; keep model files under data-root model/ when evaluated.",
    ),
}


def backend_names(*, transcribable_only: bool = False) -> list[str]:
    names = sorted(BACKEND_REGISTRY)
    if transcribable_only:
        return [name for name in names if BACKEND_REGISTRY[name].transcribable]
    return names


def get_backend_spec(name: str) -> BackendSpec:
    try:
        return BACKEND_REGISTRY[name]
    except KeyError as exc:
        raise ASRError(f"Unknown ASR backend: {name}") from exc


def build_backend(
    name: str, *, recording_json: Path | None = None, verbose: bool | None = None
) -> ASRBackend:
    spec = get_backend_spec(name)
    if spec.factory is None:
        raise ASRError(
            f"Backend `{name}` is registered as {spec.status} but is not wired into production transcription. "
            "Run candidate gate scripts and validate promotion evidence before enabling it."
        )
    return spec.factory(recording_json=recording_json, verbose=verbose)


def resolve_backend_model(name: str, model: str | None) -> str:
    return get_backend_spec(name).model_resolver(model)


def doctor_backend(name: str) -> dict[str, Any]:
    spec = get_backend_spec(name)
    payload = spec.to_json()
    payload["doctor"] = spec.doctor() if spec.doctor else {"success": True, "diagnostics": []}
    return payload
