from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .formats import (
    collect_output_files,
    segments_to_markdown,
    segments_to_srt,
    segments_to_timestamped_markdown,
    segments_to_txt,
    segments_to_vtt,
)
from .readable import compose_readable_transcript
from .review import review_to_markdown
from .utils import ensure_dir, write_json_atomic, write_text_atomic


def write_transcript_outputs(
    job_dir: Path,
    *,
    input_path: Path,
    model: str,
    language: str | None,
    audio_duration: float,
    chunk_payloads: list[dict[str, Any]],
    raw_segments: list[dict[str, Any]],
    corrected_segments: list[dict[str, Any]],
    corrected_text: str,
    review: dict[str, Any],
) -> None:
    details_dir = ensure_dir(job_dir)
    raw_text = segments_to_txt(raw_segments)
    raw_json = {
        "input_path": str(input_path),
        "model": model,
        "language": language,
        "audio_duration": audio_duration,
        "chunks": [p.get("chunk", {}) for p in chunk_payloads],
        "segments": raw_segments,
        "text": raw_text,
    }
    write_json_atomic(details_dir / "raw.json", raw_json)
    write_json_atomic(
        details_dir / "corrected.json",
        {
            "input_path": str(input_path),
            "model": model,
            "language": language,
            "audio_duration": audio_duration,
            "segments": corrected_segments,
            "text": corrected_text,
        },
    )
    write_text_atomic(details_dir / "transcript.raw.txt", raw_text)
    write_text_atomic(details_dir / "transcript.corrected.txt", corrected_text)
    readable = compose_readable_transcript(corrected_segments, title=input_path.stem)
    write_text_atomic(job_dir / "transcript.readable.md", readable.markdown)
    write_json_atomic(details_dir / "readable_transformations.json", readable.log)
    write_text_atomic(
        details_dir / "transcript.md",
        segments_to_markdown(
            corrected_segments,
            title=input_path.stem,
            corrected=True,
            model=model,
            input_path=str(input_path),
        ),
    )
    write_text_atomic(
        details_dir / "transcript.timestamped.md",
        segments_to_timestamped_markdown(corrected_segments, title=input_path.stem),
    )
    write_text_atomic(details_dir / "transcript.srt", segments_to_srt(corrected_segments))
    write_text_atomic(details_dir / "transcript.vtt", segments_to_vtt(corrected_segments))
    write_json_atomic(details_dir / "review.json", review)
    entity_consistency = review.get("entity_consistency")
    if isinstance(entity_consistency, dict):
        write_json_atomic(details_dir / "entity_consistency.json", entity_consistency)
    write_text_atomic(details_dir / "review.md", review_to_markdown(review))


def write_corrections_report(
    job_dir: Path,
    *,
    glossary_file: str,
    episode_glossary_file: str,
    effective_glossary_file: str,
    corrections: list[dict[str, Any]],
) -> None:
    details_dir = ensure_dir(job_dir)
    write_json_atomic(
        details_dir / "corrections.json",
        {
            "glossary_file": glossary_file,
            "episode_glossary_file": episode_glossary_file,
            "effective_glossary_file": effective_glossary_file,
            "corrections": corrections,
        },
    )


def write_run_info(job_dir: Path, run: dict[str, Any]) -> dict[str, Any]:
    details_dir = ensure_dir(job_dir)
    output_files = collect_output_files(job_dir)
    output_files["run.log"] = str(details_dir / "run.log")
    output_files["run.json"] = str(details_dir / "run.json")
    run["output_files"] = output_files
    write_json_atomic(details_dir / "run.json", run)
    write_text_atomic(details_dir / "run.log", run_log_text(run))
    write_artifact_manifest(job_dir)
    return run


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_artifact_manifest(job_dir: Path) -> dict[str, Any]:
    base = job_dir.expanduser().resolve()
    artifacts: list[dict[str, Any]] = []
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        if path.name == "manifest.json":
            continue
        relative_path = path.relative_to(base).as_posix()
        artifacts.append(
            {
                "path": relative_path,
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    write_json_atomic(base / "manifest.json", manifest)
    return manifest


def run_log_text(run: dict[str, Any]) -> str:
    review = run.get("review", {}) if isinstance(run.get("review"), dict) else {}
    quality = run.get("quality_metrics", {}) if isinstance(run.get("quality_metrics"), dict) else {}
    status = (
        run.get("chunk_status_counts", {})
        if isinstance(run.get("chunk_status_counts"), dict)
        else {}
    )
    lines = [
        f"created_at={run.get('created_at', '')}",
        f"input_path={run.get('input_path', '')}",
        f"backend={run.get('backend', '')}",
        f"model={run.get('model_alias_or_input') or run.get('model', '')}",
        f"language={run.get('language', '')}",
        f"audio_duration={run.get('audio_duration', '')}",
        f"runtime_seconds={run.get('runtime_seconds', '')}",
        f"speed_factor={run.get('speed_factor', '')}",
        "chunk_status_counts=" + ",".join(f"{key}:{status.get(key, 0)}" for key in sorted(status)),
        f"review_issue_count={review.get('issue_count', 0)}",
        f"review_segment_issue_count={review.get('segment_issue_count', 0)}",
        f"correction_count={quality.get('correction_count', 0)}",
        f"correction_kind_counts={quality.get('correction_kind_counts', {})}",
        f"max_repeated_token_run={quality.get('max_repeated_token_run', 0)}",
        f"top_token_ratio={quality.get('top_token_ratio', 0)}",
    ]
    return "\n".join(lines) + "\n"
