from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
from typing import Any

from .metadata import episode_title_for_output
from ..privacy import detect_privacy_findings, redact_pii
from ..utils import (
    compact_ws,
    ensure_dir,
    read_json,
    read_text,
    relative_posix_path,
    seconds_to_hms,
    write_json_atomic,
    write_text_atomic,
)

PROMPT_TEMPLATE_MAP = {
    "summarize.prompt.md": Path("doc/cloud_prompts/summarize.zh.md"),
    "polish.prompt.md": Path("doc/cloud_prompts/polish_transcript.zh.md"),
    "glossary_review.prompt.md": Path("doc/cloud_prompts/glossary_review.zh.md"),
    "chapterize.prompt.md": Path("doc/cloud_prompts/chapterize.zh.md"),
}


@dataclass(frozen=True)
class CloudPrepareOptions:
    """Options for creating the text-only cloud handoff bundle."""

    output_dir: Path
    redact: str | None = None
    chunk_minutes: float = 20.0


def _details_dir(output_dir: Path) -> Path:
    return output_dir


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _segments_from_output(output_dir: Path) -> list[dict[str, Any]]:
    details = _details_dir(output_dir)
    corrected = _read_json_object(details / "corrected.json")
    raw = _read_json_object(details / "raw.json")
    segments = corrected.get("segments") or raw.get("segments") or []
    return segments if isinstance(segments, list) else []


def _topic_path(output_dir: Path) -> Path | None:
    candidate = output_dir.parent / "主题.md"
    return candidate if candidate.exists() else None


def _transcript_markdown(segments: list[dict[str, Any]]) -> str:
    lines = ["# Transcript For Cloud", ""]
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = seconds_to_hms(float(segment.get("start", 0.0)))
        end = seconds_to_hms(float(segment.get("end", 0.0)))
        lines.append(f"[{start} -> {end}] {text}")
    return "\n".join(lines).strip() + "\n"


def _chunk_segments(
    segments: list[dict[str, Any]],
    *,
    chunk_seconds: float,
) -> list[tuple[float, float, list[dict[str, Any]]]]:
    if not segments:
        return []
    chunks: list[tuple[float, float, list[dict[str, Any]]]] = []
    current_start = float(segments[0].get("start", 0.0))
    current_end = current_start + chunk_seconds
    current: list[dict[str, Any]] = []
    for segment in segments:
        start = float(segment.get("start", 0.0))
        if current and start >= current_end:
            chunks.append((current_start, float(current[-1].get("end", current_end)), current))
            current_start = start
            current_end = current_start + chunk_seconds
            current = []
        current.append(segment)
    if current:
        chunks.append((current_start, float(current[-1].get("end", current_end)), current))
    return chunks


def _write_text_chunks(
    input_dir: Path,
    segments: list[dict[str, Any]],
    *,
    chunk_minutes: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    chunk_dir = ensure_dir(input_dir / "chunks")
    relative_paths: list[str] = []
    ranges: list[dict[str, Any]] = []
    previous_context = ""
    for index, (start, end, chunk_segments) in enumerate(
        _chunk_segments(segments, chunk_seconds=max(60.0, chunk_minutes * 60.0)),
        start=1,
    ):
        text = _transcript_markdown(chunk_segments)
        path = chunk_dir / f"text_chunk_{index:04d}.md"
        header_parts = [
            f"# Text Chunk {index:04d}",
            "",
            f"Range: {seconds_to_hms(start)} -> {seconds_to_hms(end)}",
        ]
        if previous_context:
            header_parts.extend(["", "Previous chunk context:", previous_context])
        header = "\n".join(header_parts).strip() + "\n\n"
        write_text_atomic(path, header + text)
        relative_path = relative_posix_path(path, input_dir)
        relative_paths.append(relative_path)
        ranges.append(
            {
                "path": relative_path,
                "index": index,
                "start": seconds_to_hms(start),
                "end": seconds_to_hms(end),
                "start_seconds": float(start),
                "end_seconds": float(end),
            }
        )
        previous_context = _chunk_context_summary(chunk_segments)
    return relative_paths, ranges


def _chunk_context_summary(segments: list[dict[str, Any]], *, max_chars: int = 220) -> str:
    parts = [
        compact_ws(str(segment.get("text", "")))
        for segment in segments
        if compact_ws(str(segment.get("text", "")))
    ]
    return compact_ws(" ".join(parts))[:max_chars]


def _copy_or_write(path: Path, text: str | None) -> bool:
    if text is None:
        return False
    write_text_atomic(path, text)
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file_manifest(
    base: Path, *, exclude_local: bool = True, exclude_manifest: bool = True
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if exclude_local and path.name.endswith(".local.json"):
            continue
        if exclude_manifest and path.name == "manifest.json":
            continue
        rel = relative_posix_path(path, base)
        rows.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    return rows


def _safe_relative_files(base: Path, *, exclude_local: bool = True) -> list[str]:
    files: list[str] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if exclude_local and path.name.endswith(".local.json"):
            continue
        files.append(relative_posix_path(path, base))
    return files


def _source_file_manifest(output_dir: Path, details: Path) -> list[dict[str, Any]]:
    manifest = _read_json_object(output_dir / "manifest.json")
    manifest_artifacts = (
        manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    )
    canonical_paths = [
        "transcript.corrected.txt",
        "transcript.readable.md",
        "transcript.srt",
        "corrected.json",
        "raw.json",
        "qa.json",
        "review.json",
        "corrections.json",
        "glossary.effective.json",
    ]
    rows: list[dict[str, Any]] = []
    for artifact in manifest_artifacts:
        if not isinstance(artifact, dict) or artifact.get("path") not in canonical_paths:
            continue
        rows.append(
            {
                "path": str(artifact.get("path")),
                "size_bytes": int(artifact.get("bytes") or 0),
                "sha256": str(artifact.get("sha256") or ""),
                "source": "manifest",
            }
        )
    if rows:
        return rows
    candidates = [
        details / "transcript.corrected.txt",
        output_dir / "transcript.readable.md",
        details / "transcript.srt",
        details / "corrected.json",
        details / "raw.json",
        details / "qa.json",
        details / "review.json",
        details / "corrections.json",
        # run.json is intentionally excluded because cloud preparation records
        # the newly-created cloud input paths in run.json after this manifest is
        # built. run_summary.json carries the stable subset used for cloud work.
        details / "glossary.effective.json",
    ]
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            rel = relative_posix_path(path, output_dir)
        except ValueError:
            rel = str(path)
        rows.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    return rows


def _write_cloud_readme(input_dir: Path, *, qa_status: str) -> str:
    text = f"""# SonaFolio Cloud Input Package

This directory is a text-only package produced from local ASR outputs.

- Contains original audio/video: no
- QA status at package time: {qa_status}
- Use `manifest.json` to verify file hashes before upload.
- Use `handoff_contract.md` as the boundary for downstream cloud-model work.
- Do not treat cloud summaries as transcript corrections unless patches are explicitly reviewed and applied.
"""
    path = input_dir / "README.md"
    write_text_atomic(path, text)
    return relative_posix_path(path, input_dir)


def _write_handoff_contract(input_dir: Path) -> str:
    text = """# Cloud Handoff Contract

This package is text-only. It must not contain original audio or video bytes.

Use the transcript, segment JSON, QA report, review report, glossary, and topic context to produce downstream text artifacts. Do not invent corrected transcript content for QA-blocked ranges; mark uncertainty and request local repair or human review for those ranges.

Recommended downstream outputs:

- summary.md: episode-level summary grounded in the transcript.
- chapters.json / chapters.md: timestamped chapters.
- glossary_suggestions.json: candidate glossary additions and review-only terms.
- transcript.polish_suggestions.json: patch suggestions keyed by segment id or timestamp range.
- uncertainty_report.md: unresolved factual, term, or transcript-quality uncertainties.

Patch suggestions should be narrow and auditable. They should not rewrite large transcript spans without source segment IDs or timestamp ranges.
"""
    path = input_dir / "handoff_contract.md"
    write_text_atomic(path, text)
    return relative_posix_path(path, input_dir)


def _write_expected_outputs_schema(input_dir: Path) -> str:
    payload = {
        "summary.md": {"type": "markdown", "required": False},
        "chapters.json": {
            "type": "object",
            "required": False,
            "properties": {"chapters": "list of {start, end, title, summary}"},
        },
        "glossary_suggestions.json": {
            "type": "object",
            "required": False,
            "properties": {
                "suggestions": "list of candidate terms/corrections",
                "needs_human_confirmation": "list of uncertain terms",
            },
        },
        "transcript.polish_suggestions.json": {
            "type": "object",
            "required": False,
            "properties": {"patches": "list of narrow transcript patches keyed by segment/time"},
        },
        "uncertainty_report.md": {"type": "markdown", "required": False},
    }
    path = input_dir / "expected_outputs.schema.json"
    write_json_atomic(path, payload)
    return relative_posix_path(path, input_dir)


def _apply_redaction_map(text: str, redaction_map: dict[str, str]) -> str:
    redacted = text
    for placeholder, original in redaction_map.items():
        redacted = redacted.replace(original, placeholder)
    return redacted


def _redact_segments(
    segments: list[dict[str, Any]], redaction_map: dict[str, str]
) -> list[dict[str, Any]]:
    redacted_segments: list[dict[str, Any]] = []
    for segment in segments:
        item = dict(segment)
        item["text"] = _apply_redaction_map(str(item.get("text", "")), redaction_map)
        redacted_segments.append(item)
    return redacted_segments


def _write_prompt_templates(input_dir: Path) -> list[str]:
    prompt_dir = ensure_dir(input_dir / "prompts")
    written: list[str] = []
    for output_name, source in PROMPT_TEMPLATE_MAP.items():
        text = read_text(source)
        if text is None:
            continue
        path = prompt_dir / output_name
        write_text_atomic(path, text)
        written.append(relative_posix_path(path, input_dir))
    return sorted(written)


def prepare_cloud_input(options: CloudPrepareOptions) -> dict[str, Any]:
    """Create a text-only cloud input bundle from a local transcription output.

    The bundle contains redacted transcript artifacts, QA/review context,
    prompt templates, manifests, and handoff instructions under
    ``cloud/input``.

    Args:
        options: Cloud preparation options.

    Returns:
        A manifest-style dictionary describing the generated input bundle.
    """

    output_dir = options.output_dir.expanduser().resolve()
    details = _details_dir(output_dir)
    input_dir = ensure_dir(output_dir / "cloud" / "input")
    segments = _segments_from_output(output_dir)
    run = _read_json_object(details / "run.json")
    qa = _read_json_object(details / "qa.json")
    review = _read_json_object(details / "review.json")
    glossary = _read_json_object(details / "glossary.effective.json")

    transcript_text = _transcript_markdown(segments)
    topic = _topic_path(output_dir)
    topic_text = read_text(topic) if topic else None
    privacy_findings = detect_privacy_findings(
        "\n".join(part for part in (transcript_text, topic_text or "") if part)
    )
    redaction_map: dict[str, str] = {}
    if options.redact == "pii":
        transcript_text, redaction_map = redact_pii(transcript_text)
    cloud_segments = _redact_segments(segments, redaction_map) if redaction_map else segments
    write_text_atomic(input_dir / "transcript.for_cloud.md", transcript_text)
    write_json_atomic(input_dir / "segments.for_cloud.json", {"segments": cloud_segments})
    write_json_atomic(input_dir / "qa.for_cloud.json", qa)
    write_text_atomic(
        input_dir / "qa.for_cloud.md",
        read_text(details / "qa.md") or "# QA Report\n\nStatus: UNKNOWN\n",
    )
    write_json_atomic(input_dir / "review.for_cloud.json", review)
    _copy_or_write(input_dir / "review.for_cloud.md", read_text(details / "review.md"))
    write_json_atomic(input_dir / "glossary.for_cloud.json", glossary)
    if topic:
        if redaction_map and topic_text is not None:
            write_text_atomic(
                input_dir / "topic.for_cloud.md", _apply_redaction_map(topic_text, redaction_map)
            )
        else:
            shutil.copyfile(topic, input_dir / "topic.for_cloud.md")
    write_json_atomic(
        input_dir / "run_summary.json",
        {
            "model": run.get("model") or run.get("model_alias_or_input"),
            "language": run.get("language"),
            "audio_duration": run.get("audio_duration"),
            "qa": run.get("qa"),
            "review": run.get("review"),
        },
    )
    chunk_paths, chunk_ranges = _write_text_chunks(
        input_dir, cloud_segments, chunk_minutes=options.chunk_minutes
    )
    prompt_paths = _write_prompt_templates(input_dir)
    handoff_contract_path = _write_handoff_contract(input_dir)
    expected_schema_path = _write_expected_outputs_schema(input_dir)
    privacy_summary = [
        {"type": str(finding.get("type")), "count": int(finding.get("count") or 0)}
        for finding in privacy_findings
        if isinstance(finding, dict)
    ]
    if privacy_findings:
        lines = ["# Privacy Review", ""]
        for finding in privacy_findings:
            lines.append(f"- {finding['type']}: {finding['count']}")
        write_text_atomic(input_dir / "privacy_review.md", "\n".join(lines) + "\n")
    if redaction_map:
        write_json_atomic(input_dir / "redaction_map.local.json", redaction_map)

    qa_status = "pass" if qa.get("success") is True else "fail" if qa else "unknown"
    readme_path = _write_cloud_readme(input_dir, qa_status=qa_status)
    source_manifest = _source_file_manifest(output_dir, details)

    manifest = {
        "schema_version": 2,
        "workflow": "local_asr_text_only_cloud_handoff",
        "episode_title": episode_title_for_output(output_dir, run=run),
        "audio_duration": run.get("audio_duration"),
        "model": run.get("model_alias_or_input") or run.get("model"),
        "qa_status": qa_status,
        "qa_summary": qa.get("summary", {}) if isinstance(qa, dict) else {},
        "contains_audio": False,
        "contains_video": False,
        "redacted": options.redact == "pii",
        "input_files": [],
        "input_file_manifest": [],
        "text_chunks": chunk_paths,
        "text_chunk_ranges": chunk_ranges,
        "prompt_templates": prompt_paths,
        "handoff_contract": handoff_contract_path,
        "expected_outputs_schema": expected_schema_path,
        "readme": readme_path,
        "source_file_manifest": source_manifest,
        "privacy_findings": privacy_summary,
        "privacy_review_file": "privacy_review.md" if privacy_findings else "",
        "source_run_sha256": run.get("transcription_fingerprint_sha256") or "",
        "postprocess_sha256": run.get("postprocess_fingerprint_sha256") or "",
    }
    write_json_atomic(input_dir / "manifest.json", manifest)
    manifest["input_file_manifest"] = _safe_file_manifest(input_dir)
    manifest["input_files"] = _safe_relative_files(input_dir)
    write_json_atomic(input_dir / "manifest.json", manifest)
    run_path = details / "run.json"
    if run_path.exists():
        run_payload = _read_json_object(run_path)
        run_payload["schema_version"] = run_payload.get("schema_version", 2)
        run_payload["cloud"] = {
            "prepared": True,
            "audio_uploaded": False,
            "outputs": [str(Path("cloud/input") / item) for item in manifest["input_files"]],
        }
        write_json_atomic(run_path, run_payload)
    return {"success": True, "input_dir": str(input_dir), "manifest": manifest}
