import ast
from pathlib import Path

import pytest

from atot.asr_guard import RETRY_TEMPERATURES
from atot.backends import ASR_RESULT_CONTRACT, ASRError, normalize_asr_result
from atot.backends.faster_whisper import FasterWhisperBackend
from atot.backends.registry import (
    backend_names,
    doctor_backend,
    get_backend_spec,
    resolve_backend_model,
)
from atot.pipeline import TranscribeOptions
from atot.profiles import apply_decode_profile


def test_backend_registry_exposes_production_and_candidate_backends():
    names = backend_names()
    mlx = get_backend_spec("mlx-whisper")
    faster = get_backend_spec("faster-whisper")
    funasr = get_backend_spec("funasr")

    assert "mlx-whisper" in names
    assert "faster-whisper" in names
    assert "funasr" in names
    assert mlx.transcribable is True
    assert mlx.capabilities["prompt"] is True
    assert "large-v3-turbo" in mlx.model_aliases
    assert faster.transcribable is True
    assert faster.capabilities["word_timestamps"] is True
    assert "faster-whisper-large-v3-turbo" in faster.model_aliases
    assert funasr.status == "candidate"
    assert funasr.transcribable is False
    assert funasr.to_json()["result_contract"] == ASR_RESULT_CONTRACT
    assert "candidate_gate_pass" in funasr.to_json()["promotion_requirements"]
    assert doctor_backend("fake")["doctor"]["success"] is True


def test_faster_whisper_backend_exposes_capabilities():
    backend = FasterWhisperBackend(verbose=False, device="cpu", compute_type="int8")

    assert backend.name == "faster-whisper"
    assert backend.supports_prompt is True
    assert backend.supports_word_timestamps is True
    assert backend.supports_diarization is False


def test_faster_whisper_resolver_maps_default_alias_to_ctranslate2_model(monkeypatch, tmp_path):
    model_dir = tmp_path / "model" / "faster-whisper-large-v3-turbo"
    model_dir.mkdir(parents=True)
    for name in (
        "config.json",
        "model.bin",
        "preprocessor_config.json",
        "tokenizer.json",
        "vocabulary.json",
    ):
        (model_dir / name).write_bytes(b"model")
    monkeypatch.setattr("atot.models.MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr("atot.models.LOCAL_MODELS_DIR", tmp_path / "model")

    assert resolve_backend_model("faster-whisper", "large-v3-turbo") == str(model_dir)


def test_faster_whisper_resolver_requires_local_inventory_files(monkeypatch, tmp_path):
    monkeypatch.setattr("atot.models.MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr("atot.models.LOCAL_MODELS_DIR", tmp_path / "model")

    with pytest.raises(ASRError) as exc_info:
        resolve_backend_model("faster-whisper", "large-v3-turbo")

    message = str(exc_info.value)
    assert "Required faster-whisper model files are missing" in message
    assert "faster-whisper-large-v3-turbo" in message
    assert "model.bin" in message


def test_decode_profile_applies_named_options_without_changing_default_path():
    base = TranscribeOptions(input_path=Path("episode.m4a"))
    balanced = apply_decode_profile(
        TranscribeOptions(input_path=Path("episode.m4a"), profile="balanced_zh_podcast")
    )
    quality = apply_decode_profile(
        TranscribeOptions(input_path=Path("episode.m4a"), profile="quality_zh_podcast")
    )
    profiled = apply_decode_profile(
        TranscribeOptions(input_path=Path("episode.m4a"), profile="repair_strict")
    )
    anti_repeat = apply_decode_profile(
        TranscribeOptions(input_path=Path("episode.m4a"), profile="anti_repeat_zh_podcast")
    )

    assert apply_decode_profile(base) == base
    assert balanced.profile == "balanced_zh_podcast"
    assert balanced.condition_on_previous_text is False
    assert balanced.word_timestamps is False
    assert balanced.chunk_length == 20 * 60
    assert balanced.temperature == RETRY_TEMPERATURES
    assert quality.profile == "quality_zh_podcast"
    assert quality.condition_on_previous_text is False
    assert quality.word_timestamps is True
    assert quality.temperature == RETRY_TEMPERATURES
    assert profiled.profile == "repair_strict"
    assert profiled.word_timestamps is True
    assert profiled.condition_on_previous_text is False
    assert profiled.hallucination_silence_threshold == 1.0
    assert anti_repeat.profile == "anti_repeat_zh_podcast"
    assert anti_repeat.chunk_length == 15 * 60
    assert anti_repeat.overlap == 12
    assert anti_repeat.word_timestamps is False
    assert anti_repeat.condition_on_previous_text is False
    assert anti_repeat.temperature == RETRY_TEMPERATURES
    assert anti_repeat.no_speech_threshold == 0.55
    assert anti_repeat.logprob_threshold == -0.9
    assert anti_repeat.compression_ratio_threshold == 2.2


def test_backend_result_normalizer_enforces_segment_contract():
    result = normalize_asr_result(
        {
            "segments": [
                {"start": "0", "end": "1.5", "text": " 你好 ", "avg_logprob": -0.1},
                {
                    "start": 1.5,
                    "end": 1.4,
                    "text": "后文",
                    "words": [{"word": "后文"}],
                    "confidence": 0.8,
                },
            ]
        }
    )

    assert result["text"] == "你好后文"
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["end"] == 1.5
    assert result["segments"][0]["text"] == "你好"
    assert result["segments"][0]["words"] == []
    assert result["segments"][0]["confidence"] is None
    assert result["segments"][0]["raw"]["avg_logprob"] == -0.1
    assert result["segments"][1]["end"] > result["segments"][1]["start"]
    assert result["segments"][1]["words"] == [{"word": "后文"}]
    assert result["segments"][1]["confidence"] == 0.8


def test_backend_implementation_imports_stay_inside_backend_boundary():
    atot_root = Path(__file__).resolve().parents[1] / "atot"
    backend_root = atot_root / "backends"
    implementation_modules = {
        "atot.backends.fake",
        "atot.backends.faster_whisper",
        "atot.backends.mlx_whisper",
        "atot.backends.recording",
    }
    violations: list[str] = []

    for path in sorted(atot_root.rglob("*.py")):
        if path.is_relative_to(backend_root):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_backend_implementation_module(alias.name, implementation_modules):
                        violations.append(
                            f"{path.relative_to(atot_root.parent)}:{node.lineno}: import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = _resolved_import_module(path, atot_root, node)
                if _is_backend_implementation_module(module, implementation_modules):
                    violations.append(
                        f"{path.relative_to(atot_root.parent)}:{node.lineno}: from {module}"
                    )
                elif module == "atot.backends":
                    for alias in node.names:
                        imported_module = f"{module}.{alias.name}"
                        if _is_backend_implementation_module(
                            imported_module, implementation_modules
                        ):
                            violations.append(
                                f"{path.relative_to(atot_root.parent)}:{node.lineno}: "
                                f"from {module} import {alias.name}"
                            )

    assert violations == []


def _resolved_import_module(path: Path, atot_root: Path, node: ast.ImportFrom) -> str:
    module = node.module or ""
    if node.level == 0:
        return module
    package_parts = ["atot", *path.relative_to(atot_root).with_suffix("").parts[: -node.level]]
    if module:
        package_parts.extend(module.split("."))
    return ".".join(package_parts)


def _is_backend_implementation_module(module: str, implementation_modules: set[str]) -> bool:
    return module in implementation_modules or any(
        module.startswith(f"{name}.") for name in implementation_modules
    )
