from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .context import build_prompt_context, write_context_files
from .corrections import apply_corrections_to_segments, segments_to_plain_text
from .entity_consistency import build_entity_consistency_report
from .pipeline import _postprocess_fingerprint, _sha256_json
from .qa import run_qa
from .quality import build_quality_metrics
from .review import build_review
from .runinfo import now_iso
from .utils import read_json
from .writer import write_corrections_report, write_run_info, write_transcript_outputs


@dataclass(frozen=True)
class PostprocessOptions:
    output_dir: Path
    glossary_file: Path | None = None
    local_only: bool = False
    rule_packs: tuple[str, ...] | list[str] | None = None


def _chunk_payloads_from_raw(raw: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = raw.get("chunks", [])
    if not isinstance(chunks, list):
        return []
    return [{"chunk": chunk} for chunk in chunks if isinstance(chunk, dict)]


def run_postprocess(options: PostprocessOptions) -> dict[str, Any]:
    job_dir = options.output_dir.expanduser().resolve()
    details_dir = job_dir
    raw_path = details_dir / "raw.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw transcript JSON: {raw_path}")
    raw = read_json(raw_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Raw transcript JSON must be an object: {raw_path}")
    raw_segments = raw.get("segments", [])
    if not isinstance(raw_segments, list):
        raise ValueError(f"Raw transcript JSON must contain a segments list: {raw_path}")

    run_path = details_dir / "run.json"
    previous_run = read_json(run_path) if run_path.exists() else {}
    if not isinstance(previous_run, dict):
        previous_run = {}

    input_path = Path(str(raw.get("input_path") or previous_run.get("input_path") or "input"))
    context = build_prompt_context(
        input_path,
        prompt_file=None,
        glossary_file=options.glossary_file,
        rule_packs=options.rule_packs,
    )
    context_files = write_context_files(job_dir, context, glossary_file=options.glossary_file)
    audio_duration = float(raw.get("audio_duration") or previous_run.get("audio_duration") or 0.0)
    corrected_segments, correction_report = apply_corrections_to_segments(
        raw_segments,
        context.glossary,
        audio_duration=audio_duration,
    )
    corrected_text = segments_to_plain_text(corrected_segments)
    review = build_review(
        corrected_segments, context.glossary, rule_packs=context.rule_pack_request
    )
    review["entity_consistency"] = build_entity_consistency_report(
        corrected_segments, context.glossary
    )
    quality_metrics = build_quality_metrics(
        raw_segments=raw_segments,
        corrected_segments=corrected_segments,
        corrections=correction_report,
        review=review,
    )

    model = str(
        raw.get("model")
        or previous_run.get("model")
        or previous_run.get("model_alias_or_input")
        or ""
    )
    language = (
        raw.get("language") if raw.get("language") is not None else previous_run.get("language")
    )
    write_transcript_outputs(
        job_dir,
        input_path=input_path,
        model=model,
        language=str(language) if language is not None else None,
        audio_duration=audio_duration,
        chunk_payloads=_chunk_payloads_from_raw(raw),
        raw_segments=raw_segments,
        corrected_segments=corrected_segments,
        corrected_text=corrected_text,
        review=review,
    )
    write_corrections_report(
        job_dir,
        glossary_file=context_files.copied_glossary or str(options.glossary_file or ""),
        episode_glossary_file=str(context_files.episode_glossary_file or ""),
        effective_glossary_file=str(context_files.effective_glossary_file),
        corrections=correction_report,
    )
    qa_report = run_qa(job_dir)
    postprocess_fingerprint = _postprocess_fingerprint(
        context.glossary, rule_packs=context.rule_pack_request
    )

    run = {
        **previous_run,
        "schema_version": previous_run.get("schema_version", 2),
        "success": previous_run.get("success", True),
        "postprocessed_at": now_iso(),
        "postprocess_fingerprint": postprocess_fingerprint,
        "postprocess_fingerprint_sha256": _sha256_json(postprocess_fingerprint),
        "glossary_file": context_files.copied_glossary or str(options.glossary_file or ""),
        "episode_glossary_file": str(context_files.episode_glossary_file or ""),
        "effective_glossary_file": str(context_files.effective_glossary_file),
        "topic_prompt_summary_file": str(context_files.topic_prompt_summary_file or ""),
        "rule_pack_request": list(context.rule_pack_request),
        "topic_rule_packs": list(context.topic_rule_packs),
        "review_rule_packs": review.get("summary", {}).get("rule_packs", []),
        "rule_packs_file": str(context_files.rule_packs_file),
        "local_only": options.local_only,
        "review": review.get("summary", {}),
        "qa": {
            "status": "pass" if qa_report.get("success") else "fail",
            **(qa_report.get("summary", {}) if isinstance(qa_report.get("summary"), dict) else {}),
        },
        "repair": previous_run.get("repair", {"applied": False, "repair_run_ids": []}),
        "cloud": previous_run.get(
            "cloud", {"prepared": False, "audio_uploaded": False, "outputs": []}
        ),
        "quality_metrics": quality_metrics,
    }
    if "created_at" not in run:
        run["created_at"] = now_iso()
    if "input_path" not in run:
        run["input_path"] = str(input_path)
    if "job_dir" not in run:
        run["job_dir"] = str(job_dir)
    if "model" not in run:
        run["model"] = model
    if "language" not in run:
        run["language"] = language
    if "audio_duration" not in run:
        run["audio_duration"] = audio_duration
    return write_run_info(job_dir, run)
