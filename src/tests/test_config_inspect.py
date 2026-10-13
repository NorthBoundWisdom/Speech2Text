from __future__ import annotations

from atot.config_v2 import inspect_config
from atot import platform_defaults


def entry_by_key(payload: dict, key: str) -> dict:
    return next(entry for entry in payload["entries"] if entry["key"] == key)


def test_config_inspect_reports_defaults_when_missing(tmp_path):
    payload = inspect_config(tmp_path / "config.toml")

    assert payload["path"] == str(tmp_path / "config.toml")
    assert payload["layers"]["built_in_defaults"]["enabled"] is True
    assert payload["layers"]["user_config"]["enabled"] is False
    assert sorted(payload["effective"]) == [
        "cloud",
        "library",
        "local",
        "summary",
        "translation",
        "ui",
        "workflow",
    ]
    assert entry_by_key(payload, "local.asr_model")["source"] == "built_in_defaults"
    assert entry_by_key(payload, "local.asr_model")["is_default"] is True
    assert entry_by_key(payload, "library.storage")["source"] == "built_in_defaults"
    assert payload["effective"]["library"]["storage"] == platform_defaults.default_library_storage()
    assert payload["effective"]["cloud"]["api_key"] == ""


def test_config_inspect_uses_modern_cloud_keys_only(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
model = "unused-model"

[model_providers.OpenAI]
base_url = "https://unused.example/v1"
api_key = "unused-key"

[cloud]
api_base = "https://cloud.example/v1"
api_key = "cloud-key"
model = "cloud-model"
""",
        encoding="utf-8",
    )

    payload = inspect_config(config_path)

    assert payload["effective"]["cloud"]["api_base"] == "https://cloud.example/v1"
    assert payload["effective"]["cloud"]["model"] == "cloud-model"
    assert "provider_compat" not in payload["layers"]
    assert entry_by_key(payload, "cloud.model")["source"] == "user_config"
    assert entry_by_key(payload, "cloud.model")["raw_key"] == "cloud.model"


def test_config_inspect_redacts_api_key(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('[cloud]\napi_key = "secret-key"\n', encoding="utf-8")

    payload = inspect_config(config_path)
    api_key = entry_by_key(payload, "cloud.api_key")

    assert payload["effective"]["cloud"]["api_key"] == "***"
    assert api_key["value"] == "***"
    assert api_key["redacted"] is True


def test_config_inspect_ignores_provider_table_keys(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[model_providers.OpenAI]
base_url = "https://unused.example/v1"
""",
        encoding="utf-8",
    )

    payload = inspect_config(config_path)
    api_base = entry_by_key(payload, "cloud.api_base")

    assert payload["effective"]["cloud"]["api_base"] == ""
    assert api_base["source"] == "built_in_defaults"
    assert api_base["raw_key"] == "cloud.api_base"
    assert api_base["editable"] is True
    assert api_base["key"] == "cloud.api_base"
