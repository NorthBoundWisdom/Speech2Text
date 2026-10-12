from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .toml_compat import tomllib
from .credentials import resolve_api_key
from .models import DEFAULT_MODEL_ALIAS
from .paths import data_root
from .runtime_defaults import DEFAULT_CLOUD_MAX_TOKENS, DEFAULT_CLOUD_TIMEOUT_SECONDS

DEFAULT_PROFILE = "balanced_zh_podcast"


DEFAULT_CLOUD_MODEL_OPTIONS = [
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-5.5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
]
DEFAULT_TRANSLATION_LOCAL_MODEL = "nllb-200-distilled-600m"


@dataclass(frozen=True)
class LocalConfig:
    asr_model: str = DEFAULT_MODEL_ALIAS
    asr_profile: str = DEFAULT_PROFILE


@dataclass(frozen=True)
class CloudConfig:
    api_base: str = ""
    api_key: str = ""
    model: str = DEFAULT_CLOUD_MODEL_OPTIONS[0]
    timeout: float = DEFAULT_CLOUD_TIMEOUT_SECONDS
    temperature: float | None = 1.0
    max_tokens: int | None = DEFAULT_CLOUD_MAX_TOKENS
    summary_prompt: str = ""
    title_prompt: str = ""
    model_options: list[str] = field(default_factory=lambda: list(DEFAULT_CLOUD_MODEL_OPTIONS))


@dataclass(frozen=True)
class TranslationConfig:
    enabled: bool = False
    backend: str = "cloud"
    target_language: str = "zh"
    local_model_alias: str = DEFAULT_TRANSLATION_LOCAL_MODEL


@dataclass(frozen=True)
class AppConfig:
    local: LocalConfig = field(default_factory=LocalConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)


def config_path() -> Path:
    return data_root() / "config.toml"


def load_app_config(path: Path | None = None, *, include_api_key: bool = True) -> AppConfig:
    path = path or config_path()
    if not path.exists():
        return AppConfig()
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    local = _dict(payload.get("local"))
    cloud = _dict(payload.get("cloud"))
    translation = _dict(payload.get("translation"))
    return AppConfig(
        local=LocalConfig(
            asr_model=_str(local.get("asr_model"), DEFAULT_MODEL_ALIAS),
            asr_profile=_str(local.get("asr_profile"), DEFAULT_PROFILE),
        ),
        cloud=CloudConfig(
            api_base=_str(cloud.get("api_base"), ""),
            api_key=resolve_api_key(path, cloud) if include_api_key else "",
            model=_str(cloud.get("model"), DEFAULT_CLOUD_MODEL_OPTIONS[0]),
            timeout=_float(cloud.get("timeout"), DEFAULT_CLOUD_TIMEOUT_SECONDS),
            temperature=_noneable_float(cloud.get("temperature"), 1.0),
            max_tokens=_noneable_int(cloud.get("max_tokens"), DEFAULT_CLOUD_MAX_TOKENS),
            summary_prompt=_str(cloud.get("summary_prompt"), ""),
            title_prompt=_str(cloud.get("title_prompt"), ""),
            model_options=_str_list(cloud.get("model_options"), DEFAULT_CLOUD_MODEL_OPTIONS),
        ),
        translation=TranslationConfig(
            enabled=_bool(translation.get("enabled"), False),
            backend=_choice(_str(translation.get("backend"), "cloud"), {"cloud", "local"}, "cloud"),
            target_language=_str(translation.get("target_language"), "zh"),
            local_model_alias=_str(
                translation.get("local_model_alias"), DEFAULT_TRANSLATION_LOCAL_MODEL
            ),
        ),
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _choice(value: str, choices: set[str], default: str) -> str:
    return value if value in choices else default


def _bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _float(value: Any, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return default


def _noneable_float(value: Any, default: float | None) -> float | None:
    if isinstance(value, str) and value.lower() in {"none", "null", "off", "false"}:
        return None
    return _float(value, default or 0.0) if value is not None else default


def _noneable_int(value: Any, default: int | None) -> int | None:
    if isinstance(value, str) and value.lower() in {"none", "null", "off", "false"}:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    return default


def _str_list(value: Any, default: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if items:
            return items
    return list(default)
