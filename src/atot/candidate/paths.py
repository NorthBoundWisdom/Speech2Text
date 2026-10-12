from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from atot.job import resolve_job_dir
from atot.paths import path_context
from atot.utils import ensure_dir, slugify


AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".flac", ".aac"}


def candidate_output_dir(root: Path, audio: Path, candidate_name: str) -> Path:
    return ensure_dir(root / slugify(audio.stem, max_len=60) / slugify(candidate_name, max_len=40))


def _resolved_process_dir(process_dir: Path | None = None) -> Path:
    return (process_dir or path_context().process_dir).expanduser().resolve()


def _resolved_output_dir(output_dir: Path | None = None) -> Path:
    return (output_dir or path_context().output_dir).expanduser().resolve()


def is_top_level_process_source_audio(audio: Path, process_dir: Path | None = None) -> bool:
    roots = [_resolved_process_dir(process_dir)] if process_dir is not None else []
    if process_dir is None:
        roots.extend(
            root
            for root in (
                _resolved_process_dir(None),
                Path("materials").expanduser().resolve(),
                Path("process").expanduser().resolve(),
            )
            if root not in roots
        )
    relative = None
    for root in roots:
        try:
            relative = audio.resolve().relative_to(root)
            break
        except ValueError:
            continue
    if relative is None:
        return False
    if len(relative.parts) not in (2, 3):
        return False
    if audio.suffix.lower() not in AUDIO_SUFFIXES:
        return False
    name = audio.name
    return not (
        name.startswith("sample_")
        or name.startswith("monitor-")
        or name.startswith("compare-baseline-")
        or name == "prepared.wav"
    )


def discover_process_audios(process_dir: Path | None = None) -> list[Path]:
    root = _resolved_process_dir(process_dir)
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and is_top_level_process_source_audio(path, root)
    )


def baseline_job_name(audio: Path, candidate_name: str) -> str | None:
    if is_top_level_process_source_audio(audio):
        return None
    return (
        f"compare-baseline-{slugify(audio.stem, max_len=40)}-{slugify(candidate_name, max_len=40)}"
    )


def official_process_run_json(
    audio: Path,
    process_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path | None:
    if not is_top_level_process_source_audio(audio, process_dir=process_dir):
        return None
    resolved_audio = audio.expanduser().resolve()
    process_root = _resolved_process_dir(process_dir)
    output_root = _resolved_output_dir(output_dir)
    job_dir = resolve_job_dir(resolved_audio, output_dir=output_root, process_dir=process_root)
    primary = job_dir / "run.json"
    if primary.exists():
        return primary
    return None


def glossary_terms(glossary: dict[str, Any]) -> str:
    terms: list[str] = []
    for key in ("people", "organizations", "technical_terms", "titles"):
        for value in glossary.get(key, []) or []:
            item = str(value).strip()
            if item and item not in terms:
                terms.append(item)
    return " ".join(terms)


def format_template(
    command: str,
    *,
    audio: Path,
    output: Path,
    output_dir: Path,
    context: str,
    glossary_terms: str,
) -> list[str]:
    rendered = command
    replacements = {
        "{audio}": shlex.quote(str(audio)),
        "{output}": shlex.quote(str(output)),
        "{output_dir}": shlex.quote(str(output_dir)),
        "{context}": shlex.quote(context),
        "{glossary_terms}": shlex.quote(glossary_terms),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return shlex.split(rendered)
