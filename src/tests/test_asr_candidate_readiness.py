from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_presets():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    script = scripts_dir / "asr_candidate_presets.py"
    spec = importlib.util.spec_from_file_location("asr_candidate_presets", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_readiness():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "asr_candidate_readiness.py"
    spec = importlib.util.spec_from_file_location("asr_candidate_readiness", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_qwen_readiness_declares_required_local_files() -> None:
    module = _load_presets()
    preset = module.presets()["mlx-qwen3-asr-0.6b"]

    requirements = {item.path for item in preset.required_paths}

    for filename in (
        "config.json",
        "merges.txt",
        "model.safetensors",
        "tokenizer_config.json",
        "vocab.json",
    ):
        assert str(module.MODEL_DIR / "Qwen3-ASR-0.6B" / filename) in requirements
        assert str(module.MODEL_DIR / "Qwen3-ForcedAligner-0.6B" / filename) in requirements


def test_whisperlivekit_readiness_declares_local_mlx_weights() -> None:
    module = _load_presets()
    preset = module.presets()["whisperlivekit-mlx"]

    requirements = {item.path for item in preset.required_paths}

    assert str(module.MODEL_DIR / "whisper-large-v3-turbo" / "config.json") in requirements
    assert str(module.MODEL_DIR / "whisper-large-v3-turbo" / "weights.safetensors") in requirements


def test_readiness_reports_executable_missing(tmp_path) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()
    preset = presets_mod.CandidatePreset(
        name="missing",
        command="missing {audio}",
        note="",
        executable=str(tmp_path / "missing"),
    )

    result = readiness.readiness_results(preset, doctor=False)

    assert result[0].name == "executable"
    assert result[0].ok is False


def test_readiness_reports_executable_ok(tmp_path) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()
    executable = tmp_path / "tool"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o755)
    preset = presets_mod.CandidatePreset(
        name="ok",
        command=f"{executable} {{audio}}",
        note="",
        executable=str(executable),
    )

    result = readiness.readiness_results(preset, doctor=False)

    assert result[0].ok is True


def test_readiness_reports_local_path_requirements(tmp_path) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()
    present = tmp_path / "weights.bin"
    present.write_bytes(b"weights")
    missing = tmp_path / "missing.bin"
    preset = presets_mod.CandidatePreset(
        name="local",
        command="local {audio}",
        note="",
        executable="/bin/sh",
        required_paths=(
            presets_mod.LocalPathRequirement(path=str(present), note="present"),
            presets_mod.LocalPathRequirement(path=str(missing), note="missing"),
        ),
    )

    results = readiness.readiness_results(preset, doctor=False)

    assert [result.name for result in results] == [
        "executable",
        f"local-path:{present}",
        f"local-path:{missing}",
    ]
    assert results[1].ok is True
    assert results[2].ok is False
    assert "missing" in results[2].detail


def test_readiness_main_returns_nonzero_for_missing_local_model(tmp_path, monkeypatch) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()
    preset = presets_mod.CandidatePreset(
        name="missing-local",
        command="missing-local {audio}",
        note="",
        executable="/bin/sh",
        required_paths=(
            presets_mod.LocalPathRequirement(
                path=str(tmp_path / "missing.safetensors"), note="missing model"
            ),
        ),
    )

    monkeypatch.setattr(readiness, "presets", lambda: {"missing-local": preset})

    code = readiness.main(["--preset", "missing-local", "--skip-doctor"])

    assert code == 1


def test_readiness_adds_probe_for_missing_cache(monkeypatch) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()
    preset = presets_mod.CandidatePreset(
        name="probe",
        command="probe {audio}",
        note="",
        executable="/bin/sh",
        required_hf_files=(
            presets_mod.HfFileRequirement(model="org/model", filename="weights.bin", note="test"),
        ),
    )

    monkeypatch.setattr(readiness, "_cache_path", lambda requirement, cache_dir: None)
    monkeypatch.setattr(
        readiness,
        "_probe_hf_file",
        lambda requirement, **kwargs: readiness.CheckResult(
            name=f"hf-probe:{requirement.model}/{requirement.filename}",
            ok=False,
            detail="too slow",
        ),
    )

    results = readiness.readiness_results(preset, doctor=False, probe_missing=True)

    assert [result.name for result in results] == [
        "executable",
        "hf-cache:org/model/weights.bin",
        "hf-probe:org/model/weights.bin",
    ]
    assert results[-1].detail == "too slow"


def test_probe_hf_file_reports_subprocess_result(monkeypatch) -> None:
    presets_mod = _load_presets()
    readiness = _load_readiness()

    class Completed:
        returncode = 3
        stdout = "Download probe: too slow (min=0.50 MB/s, actual=0.10 MB/s)\n"
        stderr = ""

    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(readiness.subprocess, "run", fake_run)
    result = readiness._probe_hf_file(
        presets_mod.HfFileRequirement(model="org/model", filename="weights.bin"),
        probe_bytes=123,
        timeout=4,
        min_mb_s=0.5,
        disable_xet=True,
    )

    command = calls["command"]
    assert "--model" in command
    assert "org/model" in command
    assert "--filename" in command
    assert "weights.bin" in command
    assert "--probe-bytes" in command
    assert "123" in command
    assert "--disable-xet" in command
    assert result.ok is False
    assert "too slow" in result.detail
