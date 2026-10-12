from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import path_context
from .utils import ensure_dir, slugify


@dataclass(frozen=True)
class JobLayout:
    input_path: Path
    job_dir: Path
    details_dir: Path
    chunks_dir: Path
    prepared_wav: Path


def chunk_json_path(chunk_wav: Path) -> Path:
    return chunk_wav.with_suffix(".json")


def resolve_job_dir(
    input_path: Path,
    output_dir: Path | None = None,
    explicit_name: str | None = None,
    process_dir: Path | None = None,
) -> Path:
    ctx = path_context()
    output_root = (output_dir or ctx.work_dir).expanduser()
    process_root = (process_dir or ctx.process_dir).expanduser()
    try:
        relative_parent = input_path.parent.resolve().relative_to(process_root.resolve())
    except ValueError:
        return output_root / slugify(explicit_name or input_path.stem)
    if explicit_name:
        parent = relative_parent.parent if relative_parent.parts else Path()
        relative_parent = parent / slugify(explicit_name)
    return output_root / relative_parent


def build_job_layout(
    input_path: Path,
    output_dir: Path | None = None,
    explicit_name: str | None = None,
    explicit_job_dir: Path | None = None,
    process_dir: Path | None = None,
) -> JobLayout:
    job_dir = ensure_dir(
        explicit_job_dir.expanduser()
        if explicit_job_dir
        else resolve_job_dir(input_path, output_dir, explicit_name, process_dir=process_dir)
    )
    details_dir = ensure_dir(job_dir)
    return JobLayout(
        input_path=input_path,
        job_dir=job_dir,
        details_dir=details_dir,
        chunks_dir=ensure_dir(job_dir / "chunks"),
        prepared_wav=job_dir / "prepared.wav",
    )
