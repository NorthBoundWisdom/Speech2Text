from __future__ import annotations

from typing import Any


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def positive_float(value: Any) -> float | None:
    number = as_float(value)
    if number is None or number <= 0:
        return None
    return number
