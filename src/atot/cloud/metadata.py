from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ..utils import compact_ws, read_json, read_text

GENERIC_EPISODE_TITLES = {
    "cache",
    "cloud",
    "input",
    "materials",
    "output",
    "outputs",
    "work",
}


def _clean_title(value: Any) -> str:
    text = compact_ws(str(value or ""))
    text = re.sub(r"^#+\s*", "", text)
    return text.strip(" #\"'“”‘’`")


def _meaningful_title(value: Any) -> str:
    title = _clean_title(value)
    if not title:
        return ""
    if title.casefold() in GENERIC_EPISODE_TITLES:
        return ""
    return title


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _metadata_title(path: Path) -> str:
    payload = _read_json_object(path)
    return _meaningful_title(payload.get("episode_title") or payload.get("title"))


def _topic_title(path: Path) -> str:
    text = read_text(path)
    if not text:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = _meaningful_title(stripped)
            if title:
                return title
        for prefix in ("标题：", "标题:", "节目：", "节目:"):
            if stripped.startswith(prefix):
                title = _meaningful_title(stripped[len(prefix) :])
                if title:
                    return title
    return ""


def _unique_dirs(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if expanded in seen:
            continue
        seen.add(expanded)
        unique.append(expanded)
    return unique


def _metadata_dirs(output_dir: Path, run: dict[str, Any]) -> list[Path]:
    dirs = [output_dir, output_dir.parent]
    input_path = str(run.get("input_path") or "").strip()
    if input_path:
        dirs.insert(0, Path(input_path).expanduser().parent)
    for parent in output_dir.parents:
        if parent.name == "work":
            try:
                relative = output_dir.relative_to(parent)
            except ValueError:
                continue
            dirs.insert(1, parent.parent / "materials" / relative)
            break
    return _unique_dirs(dirs)


def episode_title_for_output(
    output_dir: Path,
    *,
    run: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Return the best available user-facing episode title for an output bundle."""

    base = output_dir.expanduser().resolve()
    run_payload = run if run is not None else _read_json_object(base / "run.json")
    manifest_payload = (
        manifest
        if manifest is not None
        else _read_json_object(base / "cloud" / "input" / "manifest.json")
    )
    for payload in (manifest_payload, run_payload):
        title = _meaningful_title(payload.get("episode_title") or payload.get("title"))
        if title:
            return title

    for metadata_dir in _metadata_dirs(base, run_payload):
        title = _metadata_title(metadata_dir / "episode.json")
        if title:
            return title

    for metadata_dir in _metadata_dirs(base, run_payload):
        title = _topic_title(metadata_dir / "主题.md")
        if title:
            return title

    input_path = str(run_payload.get("input_path") or "").strip()
    if input_path:
        title = _meaningful_title(Path(input_path).stem)
        if title:
            return title
    for fallback in (base.name, base.parent.name):
        title = _meaningful_title(fallback)
        if title:
            return title
    return base.name
