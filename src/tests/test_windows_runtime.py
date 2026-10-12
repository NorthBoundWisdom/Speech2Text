from __future__ import annotations

from atot.commands import diagnostics
from atot import runinfo
from atot.windows_runtime import (
    classify_cuda_runtime_error,
    enhance_cuda_error,
    windows_runtime_payload,
)


def test_cuda12_cublas_error_mentions_cuda13_compatibility() -> None:
    hint = classify_cuda_runtime_error("Library cublas64_12.dll is not found or cannot be loaded")

    assert hint is not None
    assert hint.category == "missing_cuda12_cublas_runtime"
    assert "CUDA 12" in hint.action_required
    assert "CUDA 13" in hint.cuda13_note


def test_enhance_cuda_error_keeps_cpu_as_explicit_opt_in() -> None:
    message = enhance_cuda_error("load failed", RuntimeError("cudnn64_9.dll is missing"))

    assert "missing_cudnn_runtime" in message
    assert "ATOT_FASTER_WHISPER_DEVICE=cpu" in message
    assert "CUDA 13" in message


def test_windows_runtime_prefers_cuda13_when_detected(monkeypatch, tmp_path) -> None:
    cuda_root = tmp_path / "CUDA"
    (cuda_root / "v12.4" / "bin").mkdir(parents=True)
    (cuda_root / "v13.3" / "bin").mkdir(parents=True)
    monkeypatch.setattr("atot.windows_runtime.CUDA_TOOLKIT_ROOT", cuda_root)
    monkeypatch.setattr(
        "atot.windows_runtime._ctranslate2_cuda_probe",
        lambda: {"success": True, "cuda_device_count": 1},
    )
    monkeypatch.setattr(
        "atot.windows_runtime.installed_distribution_version", lambda name: "test-version"
    )
    for key in list(__import__("os").environ):
        if key == "CUDA_PATH" or key.startswith("CUDA_PATH_V"):
            monkeypatch.delenv(key, raising=False)

    payload = windows_runtime_payload()

    assert payload["preferred_cuda_version"] == "13.3"
    assert payload["cuda_detected_versions"] == ["13.3", "12.4"]
    assert payload["ctranslate2_cuda_probe"]["success"] is True
    assert any("CUDA 13" in note for note in payload["notes"])


def test_doctor_success_rejects_windows_cuda_failure_without_cpu_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics, "is_windows", lambda: True)
    monkeypatch.delenv("ATOT_FASTER_WHISPER_DEVICE", raising=False)
    payload = {
        "audio_prepare_available": True,
        "audio_duration_available": True,
        "faster_whisper_importable": True,
        "mlx_whisper_importable": False,
        "asr_backend": "faster-whisper",
        "windows_runtime": {"ctranslate2_cuda_probe": {"success": False}},
        "action_required": ["Install CUDA runtime."],
    }

    assert diagnostics.doctor_success(payload) is False


def test_doctor_success_allows_explicit_cpu_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(diagnostics, "is_windows", lambda: True)
    monkeypatch.setenv("ATOT_FASTER_WHISPER_DEVICE", "cpu")
    payload = {
        "audio_prepare_available": True,
        "audio_duration_available": True,
        "faster_whisper_importable": True,
        "mlx_whisper_importable": False,
        "asr_backend": "faster-whisper",
        "windows_runtime": {"ctranslate2_cuda_probe": {"success": False}},
        "action_required": ["CPU execution is explicit only."],
    }

    assert diagnostics.doctor_success(payload) is True


def test_windows_runtime_cpu_opt_in_does_not_require_cuda(monkeypatch) -> None:
    monkeypatch.setenv("ATOT_FASTER_WHISPER_DEVICE", "cpu")
    monkeypatch.setattr(
        "atot.windows_runtime._ctranslate2_cuda_probe",
        lambda: {
            "success": False,
            "importable": False,
            "cuda_device_count": None,
            "action_required": "Install ctranslate2 through the Windows Python environment.",
        },
    )

    payload = windows_runtime_payload()

    assert payload["action_required"] == []
    assert any("CUDA is not required" in note for note in payload["notes"])


def test_runtime_info_uses_audio_tool_discovery_for_ffmpeg(monkeypatch) -> None:
    class Completed:
        returncode = 0
        stdout = "ffmpeg version test-build\nextra"
        stderr = ""

    monkeypatch.setattr(runinfo, "optional_command", lambda command: "ffmpeg-from-vcpkg.exe")
    monkeypatch.setattr(runinfo.subprocess, "run", lambda *args, **kwargs: Completed())

    assert runinfo._command_version("ffmpeg") == "ffmpeg version test-build"


def test_faster_whisper_doctor_reports_model_probe_action(monkeypatch, tmp_path) -> None:
    from atot.backends import registry

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    monkeypatch.setattr(registry, "resolve_model", lambda _name: str(model_dir))
    monkeypatch.setattr(registry, "missing_required_local_paths", lambda _name: ())
    monkeypatch.setattr(registry.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        registry,
        "windows_runtime_payload",
        lambda load_model_probe=None: {
            "ctranslate2_cuda_probe": {"success": True, "cuda_device_count": 1},
            "action_required": ["Install CUDA 12 runtime DLLs or rebuild CTranslate2 for CUDA 13."],
            "faster_whisper_model_probe": {
                "success": False,
                "category": "missing_cuda12_cublas_runtime",
            },
        },
    )

    payload = registry._faster_whisper_doctor()

    assert payload["success"] is False
    assert any("CUDA 12" in item for item in payload["diagnostics"])
