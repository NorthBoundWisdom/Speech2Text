from __future__ import annotations

import importlib.util
import shlex
import sys
from pathlib import Path


def _load_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "asr_candidate_presets.py"
    spec = importlib.util.spec_from_file_location("asr_candidate_presets", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_qwen3_preset_requests_json_stdout_and_timestamps() -> None:
    presets = _load_script().presets()
    module = _load_script()
    command = shlex.split(presets["mlx-qwen3-asr-0.6b"].command)

    assert str(module.TOOLS_DIR / "mlx-qwen3-asr-venv" / "bin" / "mlx-qwen3-asr") in command
    assert command[command.index("--model") + 1] == str(module.MODEL_DIR / "Qwen3-ASR-0.6B")
    assert "--output-format" in command
    assert "json" in command
    assert "--stdout-only" in command
    assert "--timestamps" in command
    assert command[command.index("--forced-aligner") + 1] == str(
        module.MODEL_DIR / "Qwen3-ForcedAligner-0.6B"
    )
    assert "--context" in command
    assert "{glossary_terms}" in command
    assert "{audio}" in command
    requirement_paths = {
        Path(item.path).relative_to(module.MODEL_DIR)
        for item in presets["mlx-qwen3-asr-0.6b"].required_paths
    }
    expected_files = {
        "config.json",
        "merges.txt",
        "model.safetensors",
        "tokenizer_config.json",
        "vocab.json",
    }
    assert requirement_paths == {
        Path(model_dir) / filename
        for model_dir in ("Qwen3-ASR-0.6B", "Qwen3-ForcedAligner-0.6B")
        for filename in expected_files
    }


def test_whisperlivekit_preset_uses_json_output_file() -> None:
    presets = _load_script().presets()
    module = _load_script()
    command = shlex.split(presets["whisperlivekit-mlx"].command)

    assert str(module.TOOLS_DIR / "whisperlivekit-venv" / "bin" / "wlk") in command
    assert command[command.index("--model") + 1] == str(module.MODEL_DIR / "whisper-large-v3-turbo")
    assert "--format" in command
    assert "json" in command
    assert "--output" in command
    assert "{output}" in command
    assert "{audio}" in command
    assert {Path(item.path).name for item in presets["whisperlivekit-mlx"].required_paths} == {
        "config.json",
        "weights.safetensors",
    }


def test_local_mlx_whisper_preset_uses_repo_model_dir_by_default() -> None:
    preset = _load_script().presets()["mlx-whisper-local-large-v3-turbo"]
    module = _load_script()
    command = shlex.split(preset.command)

    assert command[:2] == ["env", "HF_HUB_DISABLE_XET=1"]
    assert str(module.ENV_DIR / "bin" / "python") in command
    assert "src/scripts/mlx_whisper_candidate.py" in command
    assert "--model" in command
    assert str(module.MODEL_DIR / "whisper-large-v3-turbo") in command
    assert "--context" in command
    assert "{context}" in command
    assert "--stdout-only" in command
    assert "{audio}" in command
    assert {Path(item.path).name for item in preset.required_paths} == {
        "config.json",
        "weights.safetensors",
        "ffmpeg",
    }


def test_all_local_mlx_whisper_archive_presets_use_same_wrapper() -> None:
    presets = _load_script().presets()
    module = _load_script()

    for name, expected_dir, expected_weight in [
        (
            "mlx-whisper-local-large-v3-turbo",
            str(module.MODEL_DIR / "whisper-large-v3-turbo"),
            "weights.safetensors",
        ),
        (
            "mlx-whisper-local-large-v3",
            str(module.MODEL_DIR / "whisper-large-v3-mlx"),
            "weights.npz",
        ),
        (
            "mlx-whisper-local-large-v3-4bit",
            str(module.MODEL_DIR / "whisper-large-v3-mlx-4bit"),
            "weights.npz",
        ),
    ]:
        preset = presets[name]
        command = shlex.split(preset.command)
        assert "src/scripts/mlx_whisper_candidate.py" in command
        assert command[command.index("--model") + 1] == expected_dir
        assert "--context" in command
        assert "--stdout-only" in command
        assert {Path(item.path).name for item in preset.required_paths} == {
            "config.json",
            expected_weight,
            "ffmpeg",
        }


def test_large_v3_turbo_profile_matrix_presets_are_available() -> None:
    presets = _load_script().presets()

    expected = {
        "mlx-whisper-local-large-v3-turbo",
        "mlx-whisper-local-large-v3-turbo-no-prev",
        "mlx-whisper-local-large-v3-turbo-anti-repeat",
        "mlx-whisper-local-large-v3-turbo-conservative",
        "mlx-whisper-local-large-v3-turbo-repair-strict",
    }

    assert expected.issubset(presets)

    anti_repeat = shlex.split(presets["mlx-whisper-local-large-v3-turbo-anti-repeat"].command)
    repair_strict = shlex.split(presets["mlx-whisper-local-large-v3-turbo-repair-strict"].command)
    assert "--no-condition-on-previous-text" in anti_repeat
    assert anti_repeat[anti_repeat.index("--no-speech-threshold") + 1] == "0.55"
    assert repair_strict[repair_strict.index("--hallucination-silence-threshold") + 1] == "1.0"
    assert "--word-timestamps" in repair_strict


def test_compare_command_uses_direct_preset_entrypoint() -> None:
    module = _load_script()
    preset = module.presets()["whisperlivekit-mlx"]
    command = module._compare_command(preset, Path("sample.wav"), timeout=456)
    parts = shlex.split(command)

    assert parts[:3] == [
        str(module.ENV_DIR / "bin" / "python"),
        "src/scripts/compare_asr_candidate.py",
        "sample.wav",
    ]
    assert parts[parts.index("--preset") + 1] == preset.name
    assert "--candidate-command" not in parts
    assert parts[parts.index("--candidate-timeout") + 1] == "456"


def test_gate_command_uses_direct_preset_entrypoint() -> None:
    module = _load_script()
    preset = module.presets()["mlx-qwen3-asr-0.6b"]
    command = module._gate_command(preset, timeout=123)
    parts = shlex.split(command)

    assert parts[:2] == [
        str(module.ENV_DIR / "bin" / "python"),
        "src/scripts/asr_candidate_gate.py",
    ]
    assert parts[parts.index("--preset") + 1] == preset.name
    assert "--candidate-command" not in parts
    assert parts[parts.index("--candidate-timeout") + 1] == "123"
    assert "--strict" in parts
