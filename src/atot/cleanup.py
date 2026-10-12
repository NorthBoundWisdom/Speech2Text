from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runinfo import now_iso
from .utils import write_json_atomic


@dataclass(frozen=True)
class CleanupOptions:
    output_dir: Path
    profile: str = "compact"
    dry_run: bool = False


PROFILE_TARGETS = {
    "full_debug": [],
    "normal": ["chunks/*.wav"],
    "compact": ["prepared.wav", "chunks/*.wav"],
    "archive": ["prepared.wav", "chunks/*.wav", "chunks/*.json"],
}


def cleanup_output(options: CleanupOptions) -> dict[str, Any]:
    base = options.output_dir.expanduser().resolve()
    if options.profile not in PROFILE_TARGETS:
        raise ValueError(f"Unknown cleanup profile: {options.profile}")
    candidates: list[Path] = []
    for pattern in PROFILE_TARGETS[options.profile]:
        candidates.extend(path for path in base.glob(pattern) if path.is_file())
    files: list[dict[str, Any]] = []
    total_bytes = 0
    for path in sorted(set(candidates)):
        size = path.stat().st_size
        total_bytes += size
        files.append({"path": path.relative_to(base).as_posix(), "bytes": size})
        if not options.dry_run:
            path.unlink()
    result = {
        "success": True,
        "created_at": now_iso(),
        "profile": options.profile,
        "dry_run": options.dry_run,
        "deleted_count": 0 if options.dry_run else len(files),
        "candidate_count": len(files),
        "freed_bytes": 0 if options.dry_run else total_bytes,
        "candidate_bytes": total_bytes,
        "files": files,
    }
    if not options.dry_run:
        write_json_atomic(base / "cleanup.last.json", result)
    return result
