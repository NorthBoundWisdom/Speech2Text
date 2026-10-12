from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def read_json_file(path: Path) -> Any:
    """Read a UTF-8 JSON file and return the decoded payload."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_relative_safe(value: str, base_dir: Path | None = None) -> bool:
    """Return whether a path stays relative and inside an optional base directory."""
    if "\x00" in value or "\\" in value:
        return False
    path = Path(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        return False
    if base_dir is None:
        return True
    try:
        base = base_dir.resolve()
        (base / path).resolve(strict=False).relative_to(base)
    except (OSError, ValueError):
        return False
    return True


def safe_relative_path(base_dir: Path, value: str) -> Path | None:
    """Resolve a safe relative path under ``base_dir``."""
    if not is_relative_safe(value, base_dir=base_dir):
        return None
    return base_dir.resolve() / value


def missing_keys(payload: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(required - set(payload))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def expect_dict(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    errors.append(f"`{key}` must be an object")
    return {}


def expect_nonnegative_number(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < 0:
        errors.append(f"`{key}` must be a non-negative number")


def expect_hash(payload: dict[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not HEX_64.match(value):
        errors.append(f"`{key}` must be a lowercase 64-character sha256 hex string")
