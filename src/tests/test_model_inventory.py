from pathlib import Path

from atot.models import (
    DEFAULT_MODEL_ALIAS,
    describe_models,
    local_model_dir,
    model_download_rows,
    resolve_model,
)
from scripts.validate_model_inventory import readme_model_rows, validate_readme_model_rows


ROOT = Path(__file__).resolve().parents[2]


def test_model_inventory_drives_public_model_aliases():
    aliases = [row["alias"] for row in describe_models()]

    assert DEFAULT_MODEL_ALIAS == "large-v3-turbo"
    assert aliases == ["large-v3-turbo", "small-4bit"]


def test_model_inventory_local_paths_are_under_model_directory():
    for row in model_download_rows():
        assert row["path"].startswith("model/")
        assert "/" + "Users/" not in row["path"]
        assert row["url"].startswith("https://huggingface.co/")
        assert "/resolve/main/" in row["url"]


def test_readme_model_download_table_matches_inventory():
    assert validate_readme_model_rows(ROOT / "README.md") == []

    readme_pairs = {(row["path"], row["url"]) for row in readme_model_rows(ROOT / "README.md")}
    inventory_pairs = {(row["path"], row["url"]) for row in model_download_rows()}
    assert readme_pairs == inventory_pairs


def test_resolver_uses_inventory_local_dir_for_default(monkeypatch, tmp_path):
    local_dir = tmp_path / "model" / "whisper-large-v3-turbo"
    local_dir.mkdir(parents=True)
    (local_dir / "config.json").write_text("{}", encoding="utf-8")
    (local_dir / "weights.safetensors").write_bytes(b"weights")

    monkeypatch.setattr("atot.models.MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr("atot.models.LOCAL_MODELS_DIR", tmp_path / "model")

    assert local_model_dir("large-v3-turbo") == tmp_path / "model" / "whisper-large-v3-turbo"
    assert resolve_model("large-v3-turbo") == str(local_dir)


def test_resolver_accepts_ctranslate2_model_bin(monkeypatch, tmp_path):
    local_dir = tmp_path / "model" / "faster-whisper-large-v3-turbo"
    local_dir.mkdir(parents=True)
    (local_dir / "config.json").write_text("{}", encoding="utf-8")
    (local_dir / "model.bin").write_bytes(b"weights")

    monkeypatch.setattr("atot.models.MODEL_DIR", tmp_path / "model")
    monkeypatch.setattr("atot.models.LOCAL_MODELS_DIR", tmp_path / "model")

    assert local_model_dir("faster-whisper-large-v3-turbo") == local_dir
    assert resolve_model("faster-whisper-large-v3-turbo") == str(local_dir)
