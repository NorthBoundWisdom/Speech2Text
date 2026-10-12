from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import path_context
from .utils import ensure_dir, slugify, write_json_atomic


@dataclass(frozen=True)
class LocalImportResult:
    episode_dir: Path
    audio_path: Path
    original_path: Path
    mode: str
    title: str

    def to_json(self) -> dict[str, Any]:
        return {
            "episode_dir": str(self.episode_dir),
            "audio_path": str(self.audio_path),
            "original_path": str(self.original_path),
            "mode": self.mode,
            "title": self.title,
        }


def _file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {"size_bytes": stat.st_size, "mtime": stat.st_mtime, "sha256": digest.hexdigest()}


def _unique_directory(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = Path(f"{base}-{index}")
        if not candidate.exists():
            return candidate
    return Path(f"{base}-{datetime.now(timezone.utc).strftime('%H%M%S')}")


def import_local_media(
    source: str | Path,
    *,
    mode: str = "copy",
    process_dir: str | Path | None = None,
    group_name: str = "Default",
) -> LocalImportResult:
    if mode not in {"copy", "reference"}:
        raise ValueError("mode must be copy or reference")
    source_path = Path(source).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"Local media does not exist: {source_path}")
    ctx = path_context()
    root = Path(process_dir).expanduser() if process_dir is not None else ctx.process_dir
    now = datetime.now(timezone.utc)
    date_folder = now.strftime("%m%d")
    title = source_path.stem
    episode_dir = _unique_directory(root / date_folder / slugify(title))
    ensure_dir(episode_dir)
    target = episode_dir / source_path.name
    if mode == "copy":
        shutil.copy2(source_path, target)
    else:
        target.symlink_to(source_path)
    imported_at = now.isoformat()
    topic = f"""# {title}

- Source: local media
- Import mode: {mode}
- Imported at: {imported_at}
- Original file: {source_path}
- Media: {target.name}

## Shownotes

Local media import.
"""
    (episode_dir / "主题.md").write_text(topic, encoding="utf-8")
    write_json_atomic(
        episode_dir / "episode.json",
        {
            "source": "local",
            "title": title,
            "app_group": group_name,
            "app_status": "import",
            "app_read": False,
            "app_star": False,
            "app_queue_status": "unread",
            "imported_at": imported_at,
            "import_mode": mode,
            "audio_path": str(target),
            "original_path": str(source_path),
            "original_fingerprint": _file_fingerprint(source_path),
            "topic_path": str(episode_dir / "主题.md"),
        },
    )
    return LocalImportResult(
        episode_dir=episode_dir,
        audio_path=target,
        original_path=source_path,
        mode=mode,
        title=title,
    )
