from __future__ import annotations

from pathlib import Path
import re


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def validate_identifier(value: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid identifier: use 1–128 ASCII letters, digits, underscores or hyphens.")
    if value.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise ValueError("Identifier is a reserved Windows device name.")
    return value


def confined_path(path: Path, root: Path) -> Path:
    """Reject traversal and symlink descendants, including links to other files inside root."""
    anchor = root.absolute()
    candidate = path.absolute()
    try:
        relative = candidate.relative_to(anchor)
    except ValueError as exc:
        raise ValueError("Path is outside its storage root.") from exc
    if ".." in relative.parts or not candidate.resolve().is_relative_to(anchor.resolve()):
        raise ValueError("Path is outside its storage root.")
    current = anchor
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlinks are not allowed inside managed storage.")
    return path
