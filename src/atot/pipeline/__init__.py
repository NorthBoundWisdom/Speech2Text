from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..asr_guard import transcribe_with_decode_guard
from ..backends import ASRBackend, ASRTranscribeOptions, build_backend, resolve_backend_model
from ..audio import (
    AudioError,
    compute_chunks,
    ffprobe_duration,
    materialize_chunk_specs,
    materialize_chunks,
    prepare_audio,
    prepare_audio_command,
    probe_media,
)
from ..context import build_prompt_context, write_context_files
from ..formats import (
    collect_output_files,
    merge_chunk_payloads_with_decisions,
)
from ..job import JobLayout, build_job_layout, chunk_json_path, resolve_job_dir
from ..models import model_source, short_model_name
from ..paths import path_context
from ..platform_defaults import default_asr_backend
from .asr import (
    ASRChunkCacheDecision as ASRChunkCacheDecision,
    _chunk_cache_decision as _chunk_cache_decision,
)
from .audio_cache import (
    PreparedAudioCacheDecision as PreparedAudioCacheDecision,
    _file_fingerprint as _file_fingerprint,
    _prepared_audio_cache_decision as _prepared_audio_cache_decision,
    _prepared_audio_fingerprint as _prepared_audio_fingerprint,
    _prepared_meta_matches as _prepared_meta_matches,
    _prepared_meta_payload as _prepared_meta_payload,
    _sha256_file as _sha256_file,
)
from .chunks import (
    AUTO_CHUNKING as AUTO_CHUNKING,
    AUTO_SMART_MAX_CHUNK_LENGTH as AUTO_SMART_MAX_CHUNK_LENGTH,
    AUTO_SMART_MIN_DURATION as AUTO_SMART_MIN_DURATION,
    AUTO_SMART_TARGET_CHUNK_LENGTH as AUTO_SMART_TARGET_CHUNK_LENGTH,
    ChunkMaterializationResult as ChunkMaterializationResult,
    _chunk_layout_fingerprint as _chunk_layout_fingerprint,
    _chunk_layout_matches as _chunk_layout_matches,
    _normalized_chunk_spec as _normalized_chunk_spec,
    _payload_matches_chunk as _payload_matches_chunk,
    _resolve_chunking_plan as _resolve_chunking_plan,
    _round_time as _round_time,
    _write_chunk_layout_manifest as _write_chunk_layout_manifest,
    plan_and_materialize_chunks,
)
from .identity import (
    _payload_matches_fingerprint as _payload_matches_fingerprint,
    _postprocess_fingerprint as _postprocess_fingerprint,
    _sha256_json as _sha256_json,
    _sha256_text as _sha256_text,
    _transcription_fingerprint as _transcription_fingerprint,
)
from .postprocess import LocalPostprocessResult as LocalPostprocessResult, run_local_postprocess
from .runinfo import (
    _chunk_runtime_seconds as _chunk_runtime_seconds,
    _chunk_status_counts as _chunk_status_counts,
    build_initial_run_info,
)
from ..profiles import apply_decode_profile
from ..qa import run_qa
from ..runinfo import now_iso
from ..runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
    DEFAULT_SAMPLE_RATE,
)
from ..utils import json_safe, read_json, write_json_atomic
from ..vad import build_smart_chunks, detect_silences_for_chunking
from ..writer import write_corrections_report, write_run_info, write_transcript_outputs


@dataclass
class TranscribeOptions:
    """Options for one local transcription run.

    Attributes:
        input_path: Source audio or video file to transcribe.
        output_dir: Parent directory for generated job folders.
        job_dir: Exact job directory to use instead of deriving one.
        name: Optional display and folder name for the job.
        backend: Registered ASR backend name.
        recording_json: Optional recorded backend payload for deterministic tests.
        model: Model alias or backend-specific model identifier.
        language: Source language hint passed to the ASR backend.
        prompt_file: Optional prompt/context file.
        glossary_file: Optional glossary file for local corrections.
        chunk_length: Target fixed chunk length in seconds.
        chunking: Chunking mode, such as auto, fixed, or smart.
        max_chunk_length: Smart chunking upper bound in seconds.
        silence_threshold: Smart chunking silence threshold.
        min_silence: Minimum silence duration for smart chunking.
        overlap: Chunk overlap in seconds.
        local_only: Whether downstream cloud stages should stay disabled.
        sample_rate: Prepared WAV sample rate.
        force_prepare: Rebuild prepared audio even when cache matches.
        force_chunks: Rebuild chunks even when cache matches.
        force_transcribe: Rerun ASR even when chunk cache matches.
        word_timestamps: Request word timestamps when supported.
        verbose: Backend verbosity flag.
        condition_on_previous_text: ASR decoding context option.
        temperature: ASR decoding temperature or fallback temperatures.
        no_speech_threshold: ASR no-speech threshold.
        logprob_threshold: ASR average log probability threshold.
        compression_ratio_threshold: ASR compression ratio threshold.
        hallucination_silence_threshold: Optional hallucination guard threshold.
        profile: Decode profile name to apply before execution.
        rule_packs: Reusable correction rule pack names.
        progress_callback: Optional sink for stage and chunk progress events.
    """

    input_path: Path
    output_dir: Path | None = None
    job_dir: Path | None = None
    name: str | None = None
    backend: str = field(default_factory=default_asr_backend)
    recording_json: Path | None = None
    model: str = "large-v3-turbo"
    language: str | None = "zh"
    prompt_file: Path | None = None
    glossary_file: Path | None = None
    chunk_length: float = 20 * 60
    chunking: str = AUTO_CHUNKING
    max_chunk_length: float | None = None
    silence_threshold: float | None = None
    min_silence: float = 0.5
    overlap: float = 10
    local_only: bool = False
    sample_rate: int = DEFAULT_SAMPLE_RATE
    force_prepare: bool = False
    force_chunks: bool = False
    force_transcribe: bool = False
    word_timestamps: bool = False
    verbose: bool | None = False
    condition_on_previous_text: bool = True
    temperature: float | tuple[float, ...] | None = 0.0
    no_speech_threshold: float | None = DEFAULT_NO_SPEECH_THRESHOLD
    logprob_threshold: float | None = DEFAULT_LOGPROB_THRESHOLD
    compression_ratio_threshold: float | None = DEFAULT_COMPRESSION_RATIO_THRESHOLD
    hallucination_silence_threshold: float | None = None
    profile: str | None = None
    rule_packs: tuple[str, ...] | list[str] | None = None
    progress_callback: Callable[[dict[str, Any]], None] | None = None


_job_dir = resolve_job_dir
_chunk_json_path = chunk_json_path


def _append_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"created_at": now_iso(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(json_safe(payload), ensure_ascii=False, sort_keys=True) + "\n")


def _emit_progress(options: TranscribeOptions, event: str, **fields: Any) -> None:
    if options.progress_callback is None:
        return
    options.progress_callback({"event": event, **fields})


def _build_backend(options: TranscribeOptions) -> ASRBackend:
    return build_backend(
        options.backend, recording_json=options.recording_json, verbose=options.verbose
    )


def _load_previous_run(job: JobLayout) -> dict[str, Any]:
    path = job.details_dir / "run.json"
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _prepare_audio_stage(
    *,
    options: TranscribeOptions,
    input_path: Path,
    job: JobLayout,
    events_path: Path,
    input_file: dict[str, Any],
    input_changed: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float, bool]:
    media_probe = probe_media(input_path)
    if (
        input_path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".avi"}
        and media_probe.get("available") is True
    ):
        if not media_probe.get("audio_streams"):
            raise AudioError(
                "Video input has no audio stream. Select a video/audio file with at least one audio track."
            )
    _append_event(events_path, "stage", stage="prepare_audio", media_probe=media_probe)
    _emit_progress(options, "stage", stage="prepare_audio")
    prepare_command = prepare_audio_command(
        input_path, job.prepared_wav, sample_rate=options.sample_rate
    )
    prepared_meta_path = job.details_dir / "prepared.meta.json"
    prepared_cache = _prepared_audio_cache_decision(
        prepared_wav=job.prepared_wav,
        meta_path=prepared_meta_path,
        input_file=input_file,
        sample_rate=options.sample_rate,
        prepare_command=prepare_command,
        force_prepare=options.force_prepare,
        input_changed=input_changed,
    )
    force_prepare = prepared_cache.overwrite
    prepare_audio(
        input_path,
        job.prepared_wav,
        sample_rate=options.sample_rate,
        overwrite=force_prepare,
    )
    prepared_audio = _prepared_audio_fingerprint(job.prepared_wav, prepare_command=prepare_command)
    write_json_atomic(
        prepared_meta_path,
        _prepared_meta_payload(
            input_file=input_file,
            prepared_audio=prepared_audio,
            prepare_command=prepare_command,
            sample_rate=options.sample_rate,
        ),
    )
    audio_duration = ffprobe_duration(job.prepared_wav)
    return media_probe, prepare_command, prepared_audio, audio_duration, force_prepare


def _transcribe_chunk_payloads(
    *,
    options: TranscribeOptions,
    backend: ASRBackend,
    chunk_specs: list[Any],
    events_path: Path,
    model_repo: str,
    prompt: str | None,
    audio_duration: float,
    transcription_fingerprint: dict[str, Any],
    transcription_fingerprint_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chunk_payloads: list[dict[str, Any]] = []
    chunk_status: list[dict[str, Any]] = []
    for spec in chunk_specs:
        _append_event(
            events_path,
            "chunk",
            stage="transcribe",
            chunk=spec.index,
            total_chunks=len(chunk_specs),
            status="started",
            core_start=spec.core_start,
            core_end=spec.core_end,
        )
        _emit_progress(
            options,
            "chunk",
            stage="transcribe",
            chunk=spec.index,
            total_chunks=len(chunk_specs),
            status="started",
        )
        json_path = chunk_json_path(spec.path)
        cache_decision = _chunk_cache_decision(
            json_path,
            spec,
            transcription_fingerprint,
            force_transcribe=options.force_transcribe,
        )
        payload = cache_decision.payload
        status = cache_decision.status
        decode_guard_audit: dict[str, Any] | None = None
        if cache_decision.should_transcribe:
            chunk_started = time.perf_counter()
            guarded = transcribe_with_decode_guard(
                backend,
                spec.path,
                ASRTranscribeOptions(
                    model=model_repo,
                    language=options.language,
                    prompt=prompt,
                    word_timestamps=options.word_timestamps,
                    condition_on_previous_text=options.condition_on_previous_text,
                    temperature=options.temperature,
                    no_speech_threshold=options.no_speech_threshold,
                    logprob_threshold=options.logprob_threshold,
                    compression_ratio_threshold=options.compression_ratio_threshold,
                    hallucination_silence_threshold=options.hallucination_silence_threshold,
                ),
            )
            result = guarded.result
            decode_guard_audit = guarded.audit
            payload = {
                "success": True,
                "created_at": now_iso(),
                "backend": backend.name,
                "backend_capabilities": {
                    "supports_prompt": backend.supports_prompt,
                    "supports_word_timestamps": backend.supports_word_timestamps,
                    "supports_diarization": backend.supports_diarization,
                },
                "transcription_fingerprint": transcription_fingerprint,
                "transcription_fingerprint_sha256": transcription_fingerprint_sha256,
                "model": model_repo,
                "model_source": model_source(model_repo),
                "language": options.language,
                "audio_duration": audio_duration,
                "chunk": spec.to_json(),
                "runtime_seconds": time.perf_counter() - chunk_started,
                "result": result,
            }
            if decode_guard_audit is not None:
                payload["asr_decode_guard"] = decode_guard_audit
            write_json_atomic(json_path, payload)
            status = (
                "transcribed"
                if status == "missing_or_forced"
                else "transcribed_after_cache_mismatch"
            )
            if decode_guard_audit is not None:
                _append_event(
                    events_path,
                    "chunk",
                    stage="transcribe",
                    chunk=spec.index,
                    total_chunks=len(chunk_specs),
                    status="decode_guard_retry",
                    selected_attempt=decode_guard_audit.get("selected_attempt"),
                )
        elif isinstance(payload, dict) and isinstance(payload.get("asr_decode_guard"), dict):
            decode_guard_audit = payload["asr_decode_guard"]
        _append_event(
            events_path,
            "chunk",
            stage="transcribe",
            chunk=spec.index,
            total_chunks=len(chunk_specs),
            status=status,
        )
        _emit_progress(
            options,
            "chunk",
            stage="transcribe",
            chunk=spec.index,
            total_chunks=len(chunk_specs),
            status=status,
        )
        chunk_payloads.append(payload)
        chunk_status.append(
            {
                "index": spec.index,
                "wav": str(spec.path),
                "json": str(json_path),
                "status": status,
                "core_start": spec.core_start,
                "core_end": spec.core_end,
                **(
                    {
                        "decode_guard": {
                            "triggered": True,
                            "selected_attempt": decode_guard_audit.get("selected_attempt"),
                        }
                    }
                    if decode_guard_audit is not None
                    else {}
                ),
            }
        )
    return chunk_payloads, chunk_status


def run_transcription(options: TranscribeOptions) -> dict[str, Any]:
    """Run the stable local transcription pipeline.

    Args:
        options: Fully resolved transcription options.

    Returns:
        A run summary dictionary containing output paths, cache decisions,
        backend metadata, QA state, and artifact manifest information.

    Raises:
        AudioError: If media probing, preparation, duration detection, or
            chunking cannot complete.
        ValueError: If options reference unsupported models, backends, or
            decode profiles.
        OSError: If required files cannot be read or written.
    """

    options = apply_decode_profile(options)
    started = time.perf_counter()
    input_path = options.input_path.expanduser().resolve()
    model_repo = resolve_backend_model(options.backend, options.model)
    ctx = path_context()
    job = build_job_layout(
        input_path, options.output_dir, options.name, explicit_job_dir=options.job_dir
    )
    events_path = job.details_dir / "events.jsonl"
    if events_path.exists():
        events_path.unlink()
    _append_event(events_path, "stage", stage="start", input_path=str(input_path))
    _emit_progress(options, "stage", stage="start", input_path=str(input_path))
    previous_run = _load_previous_run(job)
    input_file = _file_fingerprint(input_path)
    previous_input = (
        previous_run.get("input_file", {})
        if isinstance(previous_run.get("input_file"), dict)
        else {}
    )
    input_changed = bool(
        previous_input.get("sha256") and previous_input.get("sha256") != input_file["sha256"]
    )

    context = build_prompt_context(
        input_path,
        prompt_file=options.prompt_file,
        glossary_file=options.glossary_file,
        rule_packs=options.rule_packs,
    )
    context_files = write_context_files(job.job_dir, context, glossary_file=options.glossary_file)

    media_probe, prepare_command, prepared_audio, audio_duration, force_prepare = (
        _prepare_audio_stage(
            options=options,
            input_path=input_path,
            job=job,
            events_path=events_path,
            input_file=input_file,
            input_changed=input_changed,
        )
    )
    _append_event(events_path, "stage", stage="chunking", audio_duration=audio_duration)
    _emit_progress(options, "stage", stage="chunking", audio_duration=audio_duration)
    chunk_plan = plan_and_materialize_chunks(
        options=options,
        prepared_wav=job.prepared_wav,
        chunks_dir=job.chunks_dir,
        chunk_manifest_path=job.details_dir / "chunks_manifest.json",
        audio_duration=audio_duration,
        force_prepare=force_prepare,
        detect_silences=detect_silences_for_chunking,
        build_smart=build_smart_chunks,
        compute_fixed=compute_chunks,
        materialize_smart=materialize_chunk_specs,
        materialize_fixed=materialize_chunks,
    )
    chunking_plan = chunk_plan.chunking_plan
    silence_detection = chunk_plan.silence_detection
    chunk_specs = chunk_plan.chunk_specs
    chunk_layout = chunk_plan.chunk_layout
    effective_chunk_length = chunk_plan.effective_chunk_length
    effective_max_chunk_length = chunk_plan.effective_max_chunk_length

    backend = _build_backend(options)
    transcription_fingerprint = _transcription_fingerprint(
        backend_name=backend.name,
        model=model_repo,
        options=options,
        prompt=context.effective_prompt,
        input_sha256=str(input_file.get("sha256")),
        prepared_audio_sha256=str(prepared_audio.get("sha256")),
        chunk_layout_sha256=_sha256_json(chunk_layout),
    )
    transcription_fingerprint_sha256 = _sha256_json(transcription_fingerprint)
    chunk_payloads, chunk_status = _transcribe_chunk_payloads(
        options=options,
        backend=backend,
        chunk_specs=chunk_specs,
        events_path=events_path,
        model_repo=model_repo,
        prompt=context.effective_prompt,
        audio_duration=audio_duration,
        transcription_fingerprint=transcription_fingerprint,
        transcription_fingerprint_sha256=transcription_fingerprint_sha256,
    )

    raw_segments, merge_decisions = merge_chunk_payloads_with_decisions(chunk_payloads)
    write_json_atomic(job.details_dir / "merge_decisions.json", {"decisions": merge_decisions})
    _append_event(events_path, "stage", stage="postprocess", total_chunks=len(chunk_specs))
    _emit_progress(options, "stage", stage="postprocess", total_chunks=len(chunk_specs))
    postprocess_fingerprint = _postprocess_fingerprint(
        context.glossary, rule_packs=context.rule_pack_request
    )
    postprocess_fingerprint_sha256 = _sha256_json(postprocess_fingerprint)
    postprocess = run_local_postprocess(
        raw_segments,
        context.glossary,
        audio_duration=audio_duration,
        rule_packs=context.rule_pack_request,
    )

    write_transcript_outputs(
        job.job_dir,
        input_path=input_path,
        model=model_repo,
        language=options.language,
        audio_duration=audio_duration,
        chunk_payloads=chunk_payloads,
        raw_segments=raw_segments,
        corrected_segments=postprocess.corrected_segments,
        corrected_text=postprocess.corrected_text,
        review=postprocess.review,
    )
    write_corrections_report(
        job.job_dir,
        glossary_file=context_files.copied_glossary or str(options.glossary_file or ""),
        episode_glossary_file=str(context_files.episode_glossary_file or ""),
        effective_glossary_file=str(context_files.effective_glossary_file),
        corrections=postprocess.correction_report,
    )
    runtime = time.perf_counter() - started
    backend_capabilities = {
        "supports_prompt": backend.supports_prompt,
        "supports_word_timestamps": backend.supports_word_timestamps,
        "supports_diarization": backend.supports_diarization,
    }
    run = build_initial_run_info(
        input_path=input_path,
        input_file=input_file,
        media_probe=media_probe,
        prepared_audio=prepared_audio,
        job_dir=job.job_dir,
        backend_name=backend.name,
        backend_capabilities=backend_capabilities,
        options=options,
        context=context,
        context_files=context_files,
        review=postprocess.review,
        quality_metrics=postprocess.quality_metrics,
        transcription_fingerprint=transcription_fingerprint,
        transcription_fingerprint_sha256=transcription_fingerprint_sha256,
        postprocess_fingerprint=postprocess_fingerprint,
        postprocess_fingerprint_sha256=postprocess_fingerprint_sha256,
        chunk_layout=chunk_layout,
        model_repo=model_repo,
        audio_duration=audio_duration,
        chunking_plan=chunking_plan,
        effective_chunk_length=effective_chunk_length,
        effective_max_chunk_length=effective_max_chunk_length,
        silence_detection=silence_detection,
        runtime_seconds=runtime,
        chunk_payloads=chunk_payloads,
        chunk_status=chunk_status,
    )
    run["work_dir"] = str(job.job_dir)
    run["materials_dir"] = (
        str(input_path.parent) if _is_under(input_path.parent, ctx.materials_dir) else ""
    )
    write_run_info(job.job_dir, run)
    _append_event(events_path, "stage", stage="qa")
    _emit_progress(options, "stage", stage="qa")
    qa_report = run_qa(job.job_dir)
    run["qa"] = {
        "status": "pass" if qa_report.get("success") else "fail",
        **(qa_report.get("summary", {}) if isinstance(qa_report.get("summary"), dict) else {}),
    }
    run["output_files"] = collect_output_files(job.job_dir)
    _append_event(
        events_path, "stage", stage="complete", runtime_seconds=time.perf_counter() - started
    )
    _emit_progress(
        options, "stage", stage="complete", runtime_seconds=time.perf_counter() - started
    )
    return write_run_info(job.job_dir, run)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(root.expanduser().resolve())
        return True
    except ValueError:
        return False


def print_run_summary(run: dict[str, Any]) -> str:
    files = run.get("output_files", {})
    lines = [
        f"Job directory: {run.get('job_dir')}",
        f"Model: {short_model_name(str(run.get('model', '')))}",
        f"Runtime seconds: {float(run.get('runtime_seconds', 0.0)):.2f}",
        "Outputs:",
    ]
    for key in sorted(files):
        lines.append(f"  - {key}: {files[key]}")
    return "\n".join(lines)
