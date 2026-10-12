from __future__ import annotations

import re
from typing import Any


SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


_TEXT_SECRETS = re.compile(
    r"(?i)\b(?:sk-[a-z0-9][a-z0-9_-]{20,}|gh[pousr]_[a-z0-9]{30,}|github_pat_[a-z0-9_]{30,}|"
    r"xox[baprs]-[a-z0-9-]{20,}|bearer\s+[a-z0-9._~+/-]+=*)"
)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and is_sensitive_key(key):
                redacted[key] = "***" if item else item
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, str):
        return _TEXT_SECRETS.sub("***", value)
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value
