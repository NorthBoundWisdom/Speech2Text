from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import tomlkit

from .config import (
    DEFAULT_CLOUD_MODEL_OPTIONS,
    DEFAULT_PROFILE,
    DEFAULT_TRANSLATION_LOCAL_MODEL,
    config_path,
)
from .credentials import STORE, resolve_api_key, store_api_key, write_private_config
from .toml_compat import tomllib
from .models import DEFAULT_MODEL_ALIAS
from .languages import normalize_languages, resolve_languages, summary_language
from .platform_defaults import default_asr_backend, default_library_storage
from .runtime_defaults import DEFAULT_CLOUD_MAX_TOKENS, DEFAULT_CLOUD_TIMEOUT_SECONDS


@dataclass(frozen=True)
class AtotLocalConfig:
    asr_model: str = DEFAULT_MODEL_ALIAS
    asr_profile: str = DEFAULT_PROFILE
    backend: str = field(default_factory=default_asr_backend)
    language: str = "auto"
    languages: list[str] | None = None

    @property
    def requested_languages(self) -> list[str]:
        return normalize_languages(
            self.languages if self.languages is not None else [self.language]
        )


@dataclass(frozen=True)
class AtotSummaryConfig:
    language: str = "zh"


@dataclass(frozen=True)
class AtotCloudConfig:
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
class AtotTranslationConfig:
    enabled: bool = False
    backend: str = "cloud"
    target_language: str = "zh"
    local_model_alias: str = DEFAULT_TRANSLATION_LOCAL_MODEL


@dataclass(frozen=True)
class AtotWorkflowConfig:
    default_cloud_summary: bool = False
    local_only: bool = False
    chunking: str = "auto"
    chunk_length: float = 20 * 60
    overlap: float = 10.0


@dataclass(frozen=True)
class AtotLibraryConfig:
    storage: str = field(default_factory=default_library_storage)
    icloud_root: str = ""
    local_root: str = ""


@dataclass(frozen=True)
class AtotUiConfig:
    language: str = "zh"
    theme: str = "system"
    no_alt_screen: bool = False


@dataclass(frozen=True)
class AtotConfig:
    path: Path
    local: AtotLocalConfig = field(default_factory=AtotLocalConfig)
    cloud: AtotCloudConfig = field(default_factory=AtotCloudConfig)
    summary: AtotSummaryConfig = field(default_factory=AtotSummaryConfig)
    translation: AtotTranslationConfig = field(default_factory=AtotTranslationConfig)
    workflow: AtotWorkflowConfig = field(default_factory=AtotWorkflowConfig)
    library: AtotLibraryConfig = field(default_factory=AtotLibraryConfig)
    ui: AtotUiConfig = field(default_factory=AtotUiConfig)
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


CONFIG_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*$")
CONFIG_TOP_LEVEL_KEYS = {
    "local",
    "cloud",
    "summary",
    "translation",
    "workflow",
    "library",
    "ui",
    "profiles",
}


def load_atot_config(
    path: Path | None = None,
    *,
    overrides: list[str] | tuple[str, ...] | None = None,
    include_api_key: bool = True,
) -> AtotConfig:
    resolved_path = (path or config_path()).expanduser()
    payload: dict[str, Any] = {}
    if resolved_path.exists():
        payload = _dict(tomllib.loads(resolved_path.read_text(encoding="utf-8")))
    parsed_overrides = parse_config_overrides(overrides or [])
    cloud_payload = _dict(payload.get("cloud"))
    key_override = next((value for key, value in parsed_overrides if key == "cloud.api_key"), None)
    if key_override is not None and not isinstance(key_override, str):
        raise ValueError("cloud.api_key override must be a string.")
    api_key = (
        (
            key_override
            if isinstance(key_override, str)
            else resolve_api_key(resolved_path, cloud_payload)
        )
        if include_api_key
        else ""
    )
    for key, value in parsed_overrides:
        if key == "local.language":
            key, value = "local.languages", normalize_languages([value])
        _set_nested(payload, key.split("."), value)
    local = _dict(payload.get("local"))
    cloud = _dict(payload.get("cloud"))
    summary = _dict(payload.get("summary"))
    translation = _dict(payload.get("translation"))
    workflow = _dict(payload.get("workflow"))
    library = _dict(payload.get("library"))
    ui = _dict(payload.get("ui"))
    profiles = _dict(payload.get("profiles"))
    return AtotConfig(
        path=resolved_path,
        local=AtotLocalConfig(
            asr_model=_str(local.get("asr_model"), DEFAULT_MODEL_ALIAS),
            asr_profile=_str(local.get("asr_profile"), DEFAULT_PROFILE),
            backend=_str(local.get("backend"), default_asr_backend()),
            language=resolve_languages(local["languages"])[0] or "auto"
            if "languages" in local
            else _str(local.get("language"), "auto"),
            languages=normalize_languages(local["languages"]) if "languages" in local else None,
        ),
        summary=AtotSummaryConfig(language=summary_language(summary.get("language", "zh"))),
        cloud=AtotCloudConfig(
            api_base=_str(cloud.get("api_base"), ""),
            api_key=api_key,
            model=_str(cloud.get("model"), DEFAULT_CLOUD_MODEL_OPTIONS[0]),
            timeout=_float(cloud.get("timeout"), DEFAULT_CLOUD_TIMEOUT_SECONDS),
            temperature=_noneable_float(cloud.get("temperature"), 1.0),
            max_tokens=_noneable_int(cloud.get("max_tokens"), DEFAULT_CLOUD_MAX_TOKENS),
            summary_prompt=_str(cloud.get("summary_prompt"), ""),
            title_prompt=_str(cloud.get("title_prompt"), ""),
            model_options=_str_list(cloud.get("model_options"), DEFAULT_CLOUD_MODEL_OPTIONS),
        ),
        translation=AtotTranslationConfig(
            enabled=_bool(translation.get("enabled"), False),
            backend=_choice(_str(translation.get("backend"), "cloud"), {"cloud", "local"}, "cloud"),
            target_language=_str(translation.get("target_language"), "zh"),
            local_model_alias=_str(
                translation.get("local_model_alias"), DEFAULT_TRANSLATION_LOCAL_MODEL
            ),
        ),
        workflow=AtotWorkflowConfig(
            default_cloud_summary=_bool(workflow.get("default_cloud_summary"), False),
            local_only=_bool(workflow.get("local_only"), False),
            chunking=_choice(
                _str(workflow.get("chunking"), "auto"), {"auto", "fixed", "smart"}, "auto"
            ),
            chunk_length=_float(workflow.get("chunk_length"), 20 * 60),
            overlap=_float(workflow.get("overlap"), 10.0),
        ),
        library=AtotLibraryConfig(
            storage=_choice(
                _str(library.get("storage"), default_library_storage()),
                {"icloud", "local"},
                default_library_storage(),
            ),
            icloud_root=_str(library.get("icloud_root"), ""),
            local_root=_str(library.get("local_root"), ""),
        ),
        ui=AtotUiConfig(
            language=_str(ui.get("language"), "zh"),
            theme=_str(ui.get("theme"), "system"),
            no_alt_screen=_bool(ui.get("no_alt_screen"), False),
        ),
        profiles={str(key): _dict(value) for key, value in profiles.items()},
        raw=payload,
    )


def parse_config_overrides(overrides: list[str] | tuple[str, ...]) -> list[tuple[str, Any]]:
    parsed: list[tuple[str, Any]] = []
    for raw in overrides:
        key, separator, value_text = raw.partition("=")
        if not separator:
            raise ValueError("Invalid config override, expected key=value.")
        key = validate_config_key(key, label="config override", require_nested=True)
        if not value_text.strip():
            raise ValueError("Invalid config override with empty value.")
        parsed.append((key, parse_toml_value(value_text.strip())))
    return parsed


def parse_toml_value(value_text: str) -> Any:
    if not value_text.strip():
        raise ValueError("Config value must not be empty.")
    try:
        return tomllib.loads(f"value = {value_text}")["value"]
    except tomllib.TOMLDecodeError as exc:
        bare_value = value_text.strip()
        if _is_quoted_string(bare_value):
            return bare_value[1:-1]
        if re.fullmatch(r"[A-Za-z0-9_.:/@+-]+", bare_value):
            return bare_value
        raise ValueError("Invalid TOML config value.") from exc


def validate_config_key(
    key_path: str, *, label: str = "config key", require_nested: bool = False
) -> str:
    key = key_path.strip()
    if not key:
        raise ValueError(f"Invalid {label} with empty key.")
    if not CONFIG_KEY_RE.fullmatch(key):
        raise ValueError(f"Invalid {label} `{key}`. Use dotted identifiers like `local.language`.")
    if require_nested and "." not in key:
        raise ValueError(f"Invalid {label} `{key}`. Use dotted identifiers like `local.language`.")
    top_level = key.split(".", 1)[0]
    if top_level not in CONFIG_TOP_LEVEL_KEYS:
        allowed = ", ".join(sorted(CONFIG_TOP_LEVEL_KEYS))
        raise ValueError(f"Invalid {label} `{key}`. Top-level key must be one of: {allowed}.")
    return key


def read_config_value(key_path: str, *, path: Path | None = None) -> Any:
    key_path = validate_config_key(key_path)
    config = load_atot_config(path)
    if key_path == "cloud.api_key":
        return "***" if config.cloud.api_key else ""
    if key_path == "local.languages":
        return config.local.requested_languages
    if key_path == "local.language":
        return resolve_languages(config.local.requested_languages)[0] or "auto"
    if key_path == "summary.language":
        return config.summary.language
    current: Any = config.raw
    for part in key_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_config_value(key_path: str, value: Any, *, path: Path | None = None) -> Path:
    key_path = validate_config_key(key_path, require_nested=True)
    if key_path == "local.language":
        key_path, value = "local.languages", normalize_languages([value])
    elif key_path == "local.languages":
        value = normalize_languages(value)
    elif key_path == "summary.language":
        value = summary_language(value)
    resolved_path = (path or config_path()).expanduser()
    if resolved_path.exists():
        document = tomlkit.parse(resolved_path.read_text(encoding="utf-8"))
    else:
        document = tomlkit.document()
    current: Any = document
    parts = key_path.split(".")
    for part in parts[:-1]:
        if part not in current or not hasattr(current[part], "items"):
            current[part] = tomlkit.table()
        current = current[part]
    if key_path == "cloud.api_key":
        if not isinstance(value, str):
            raise ValueError("cloud.api_key must be a string.")
        store_api_key(resolved_path, value.strip())
        current["api_key_store"] = STORE if value.strip() else ""
        value = ""
    elif key_path == "cloud.api_key_store":
        raise ValueError("Use config set cloud.api_key to manage system credentials.")
    elif "cloud" in document:
        legacy_cloud = document.get("cloud")
        if legacy_cloud is not None and legacy_cloud.get("api_key"):
            resolve_api_key(resolved_path, dict(legacy_cloud))
            document = tomlkit.parse(resolved_path.read_text(encoding="utf-8"))
            current = document
            for part in parts[:-1]:
                if part not in current:
                    current[part] = tomlkit.table()
                current = current[part]
    if key_path == "local.languages":
        current.pop("language", None)
    current[parts[-1]] = value
    write_private_config(resolved_path, tomlkit.dumps(document))
    return resolved_path


def config_as_dict(config: AtotConfig) -> dict[str, Any]:
    return {
        "path": str(config.path),
        "local": {**vars(config.local), "languages": config.local.requested_languages},
        "cloud": {**vars(config.cloud), "api_key": "***" if config.cloud.api_key else ""},
        "summary": vars(config.summary),
        "translation": vars(config.translation),
        "workflow": vars(config.workflow),
        "library": vars(config.library),
        "ui": vars(config.ui),
        "profiles": config.profiles,
    }


def inspect_config(path: Path | None = None) -> dict[str, Any]:
    config = load_atot_config(path)
    defaults = AtotConfig(path=config.path)
    raw = config.raw
    entries = [
        _entry(
            "local.asr_model",
            config.local.asr_model,
            defaults.local.asr_model,
            raw,
            ["local.asr_model"],
        ),
        _entry(
            "local.asr_profile",
            config.local.asr_profile,
            defaults.local.asr_profile,
            raw,
            ["local.asr_profile"],
        ),
        _entry(
            "local.backend", config.local.backend, defaults.local.backend, raw, ["local.backend"]
        ),
        _entry(
            "local.languages",
            config.local.requested_languages,
            defaults.local.requested_languages,
            raw,
            ["local.languages", "local.language"],
        ),
        _entry(
            "cloud.api_base",
            config.cloud.api_base,
            defaults.cloud.api_base,
            raw,
            ["cloud.api_base"],
        ),
        _entry(
            "cloud.api_key",
            config.cloud.api_key,
            defaults.cloud.api_key,
            raw,
            ["cloud.api_key"],
            redacted=True,
        ),
        _entry(
            "cloud.model",
            config.cloud.model,
            defaults.cloud.model,
            raw,
            ["cloud.model"],
        ),
        _entry(
            "cloud.timeout",
            config.cloud.timeout,
            defaults.cloud.timeout,
            raw,
            ["cloud.timeout"],
        ),
        _entry(
            "cloud.temperature",
            config.cloud.temperature,
            defaults.cloud.temperature,
            raw,
            ["cloud.temperature"],
        ),
        _entry(
            "cloud.max_tokens",
            config.cloud.max_tokens,
            defaults.cloud.max_tokens,
            raw,
            ["cloud.max_tokens"],
        ),
        _entry(
            "cloud.summary_prompt",
            config.cloud.summary_prompt,
            defaults.cloud.summary_prompt,
            raw,
            ["cloud.summary_prompt"],
        ),
        _entry(
            "cloud.title_prompt",
            config.cloud.title_prompt,
            defaults.cloud.title_prompt,
            raw,
            ["cloud.title_prompt"],
        ),
        _entry(
            "cloud.model_options",
            config.cloud.model_options,
            defaults.cloud.model_options,
            raw,
            ["cloud.model_options"],
        ),
        _entry(
            "translation.enabled",
            config.translation.enabled,
            defaults.translation.enabled,
            raw,
            ["translation.enabled"],
        ),
        _entry(
            "translation.backend",
            config.translation.backend,
            defaults.translation.backend,
            raw,
            ["translation.backend"],
        ),
        _entry(
            "translation.target_language",
            config.translation.target_language,
            defaults.translation.target_language,
            raw,
            ["translation.target_language"],
        ),
        _entry(
            "translation.local_model_alias",
            config.translation.local_model_alias,
            defaults.translation.local_model_alias,
            raw,
            ["translation.local_model_alias"],
        ),
        _entry(
            "workflow.default_cloud_summary",
            config.workflow.default_cloud_summary,
            defaults.workflow.default_cloud_summary,
            raw,
            ["workflow.default_cloud_summary"],
        ),
        _entry(
            "workflow.local_only",
            config.workflow.local_only,
            defaults.workflow.local_only,
            raw,
            ["workflow.local_only"],
        ),
        _entry(
            "workflow.chunking",
            config.workflow.chunking,
            defaults.workflow.chunking,
            raw,
            ["workflow.chunking"],
        ),
        _entry(
            "workflow.chunk_length",
            config.workflow.chunk_length,
            defaults.workflow.chunk_length,
            raw,
            ["workflow.chunk_length"],
        ),
        _entry(
            "workflow.overlap",
            config.workflow.overlap,
            defaults.workflow.overlap,
            raw,
            ["workflow.overlap"],
        ),
        _entry(
            "library.storage",
            config.library.storage,
            defaults.library.storage,
            raw,
            ["library.storage"],
        ),
        _entry(
            "library.icloud_root",
            config.library.icloud_root,
            defaults.library.icloud_root,
            raw,
            ["library.icloud_root"],
        ),
        _entry(
            "library.local_root",
            config.library.local_root,
            defaults.library.local_root,
            raw,
            ["library.local_root"],
        ),
        _entry(
            "summary.language",
            config.summary.language,
            defaults.summary.language,
            raw,
            ["summary.language"],
        ),
        _entry("ui.language", config.ui.language, defaults.ui.language, raw, ["ui.language"]),
        _entry("ui.theme", config.ui.theme, defaults.ui.theme, raw, ["ui.theme"]),
        _entry(
            "ui.no_alt_screen",
            config.ui.no_alt_screen,
            defaults.ui.no_alt_screen,
            raw,
            ["ui.no_alt_screen"],
        ),
    ]
    return {
        "path": str(config.path),
        "effective": {
            "local": {**vars(config.local), "languages": config.local.requested_languages},
            "cloud": {**vars(config.cloud), "api_key": "***" if config.cloud.api_key else ""},
            "summary": vars(config.summary),
            "translation": vars(config.translation),
            "workflow": vars(config.workflow),
            "library": vars(config.library),
            "ui": vars(config.ui),
        },
        "layers": {
            "built_in_defaults": {
                "name": "Built-in defaults",
                "enabled": True,
                "description": "Values used when config.toml does not provide a setting.",
            },
            "user_config": {
                "name": "User config",
                "enabled": config.path.exists(),
                "path": str(config.path),
                "description": "The writable config.toml file.",
            },
        },
        "entries": entries,
    }


def _entry(
    key: str,
    value: Any,
    default: Any,
    raw: dict[str, Any],
    preferred_keys: list[str],
    *,
    redacted: bool = False,
) -> dict[str, Any]:
    raw_key = _first_existing(raw, preferred_keys)
    source = "user_config" if raw_key else "built_in_defaults"
    return {
        "key": key,
        "value": "***" if redacted and value else value,
        "redacted": bool(redacted and value),
        "source": source,
        "raw_key": raw_key or preferred_keys[0],
        "editable": True,
        "is_default": value == default,
    }


def _first_existing(raw: dict[str, Any], key_paths: list[str]) -> str | None:
    for key_path in key_paths:
        current: Any = raw
        found = True
        for part in key_path.split("."):
            if not isinstance(current, dict) or part not in current:
                found = False
                break
            current = current[part]
        if found:
            return key_path
    return None


def _set_nested(payload: dict[str, Any], parts: list[str], value: Any) -> None:
    current = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts == ["local", "languages"]:
        current.pop("language", None)
    current[parts[-1]] = value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _is_quoted_string(value: str) -> bool:
    return len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}


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
