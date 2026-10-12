from __future__ import annotations

from pathlib import Path
from typing import Any

from ..formats import collect_output_files
from ..models import model_source
from .identity import _sha256_json
from ..runinfo import machine_info, now_iso, peak_rss_mb, runtime_info


def _chunk_status_counts(chunk_status: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "transcribed": sum(1 for item in chunk_status if item["status"] == "transcribed"),
        "transcribed_after_cache_mismatch": sum(
            1 for item in chunk_status if item["status"] == "transcribed_after_cache_mismatch"
        ),
        "skipped_existing": sum(1 for item in chunk_status if item["status"] == "skipped_existing"),
    }


def _chunk_runtime_seconds(chunk_payloads: list[dict[str, Any]]) -> float:
    return sum(
        float(payload.get("runtime_seconds", 0.0))
        for payload in chunk_payloads
        if isinstance(payload.get("runtime_seconds"), (int, float))
    )


def build_initial_run_info(
    *,
    input_path: Path,
    input_file: dict[str, Any],
    media_probe: dict[str, Any],
    prepared_audio: dict[str, Any],
    job_dir: Path,
    backend_name: str,
    backend_capabilities: dict[str, Any],
    options: Any,
    context: Any,
    context_files: Any,
    review: dict[str, Any],
    quality_metrics: dict[str, Any],
    transcription_fingerprint: dict[str, Any],
    transcription_fingerprint_sha256: str,
    postprocess_fingerprint: dict[str, Any],
    postprocess_fingerprint_sha256: str,
    chunk_layout: dict[str, Any],
    model_repo: str,
    audio_duration: float,
    chunking_plan: dict[str, Any],
    effective_chunk_length: float,
    effective_max_chunk_length: float,
    silence_detection: dict[str, Any] | None,
    runtime_seconds: float,
    chunk_payloads: list[dict[str, Any]],
    chunk_status: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "success": True,
        "created_at": now_iso(),
        "input_path": str(input_path),
        "input_file": input_file,
        "media_probe": media_probe,
        "prepared_audio": prepared_audio,
        "job_dir": str(job_dir),
        "backend": backend_name,
        "profile": options.profile,
        "backend_capabilities": backend_capabilities,
        "transcription_fingerprint": transcription_fingerprint,
        "transcription_fingerprint_sha256": transcription_fingerprint_sha256,
        "postprocess_fingerprint": postprocess_fingerprint,
        "postprocess_fingerprint_sha256": postprocess_fingerprint_sha256,
        "chunk_layout": chunk_layout,
        "chunk_layout_sha256": _sha256_json(chunk_layout),
        "model": model_repo,
        "model_source": model_source(model_repo),
        "model_alias_or_input": options.model,
        "language": options.language,
        "prompt_file": str(options.prompt_file or ""),
        "prompt_sources": context.prompt_sources,
        "topic_prompt_summary_file": str(context_files.topic_prompt_summary_file or ""),
        "rule_pack_request": list(context.rule_pack_request),
        "topic_rule_packs": list(context.topic_rule_packs),
        "review_rule_packs": review.get("summary", {}).get("rule_packs", []),
        "rule_packs_file": str(context_files.rule_packs_file),
        "prompt": context.effective_prompt,
        "glossary_file": context_files.copied_glossary or str(options.glossary_file or ""),
        "episode_glossary_file": str(context_files.episode_glossary_file or ""),
        "effective_glossary_file": str(context_files.effective_glossary_file),
        "audio_duration": audio_duration,
        "chunk_length": effective_chunk_length,
        "chunking": chunking_plan["chunking"],
        "requested_chunking": options.chunking,
        "max_chunk_length": effective_max_chunk_length,
        "silence_threshold": chunk_layout.get("silence_threshold"),
        "silence_detection": silence_detection or {},
        "min_silence": options.min_silence,
        "overlap": options.overlap,
        "local_only": options.local_only,
        "runtime_seconds": runtime_seconds,
        "chunk_runtime_seconds": _chunk_runtime_seconds(chunk_payloads),
        "speed_factor": audio_duration / runtime_seconds if runtime_seconds > 0 else None,
        "chunk_status_counts": _chunk_status_counts(chunk_status),
        "peak_rss_mb": peak_rss_mb(),
        "machine_info": machine_info(),
        "runtime": runtime_info(),
        "chunks": chunk_status,
        "review": review.get("summary", {}),
        "qa": {
            "status": "fail",
            "issue_count": 0,
            "blocking_issue_count": 0,
            "warning_count": 0,
        },
        "repair": {"applied": False, "repair_run_ids": []},
        "cloud": {"prepared": False, "audio_uploaded": False, "outputs": []},
        "quality_metrics": quality_metrics,
        "output_files": collect_output_files(job_dir),
    }
