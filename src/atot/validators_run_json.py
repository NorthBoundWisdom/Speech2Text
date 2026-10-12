from __future__ import annotations

from typing import Any

from .pipeline import _sha256_json
from .validation_contracts import RUN_JSON_CONTRACT
from .validators_common import (
    HEX_64,
    expect_dict,
    expect_hash,
    expect_nonnegative_number,
    is_number,
    missing_keys,
)


REQUIRED_RUN_TOP_LEVEL = set(RUN_JSON_CONTRACT.required_top_level)
REQUIRED_STATUS_KEYS = set(RUN_JSON_CONTRACT.required_status_keys)
REQUIRED_OUTPUT_FILES = set(RUN_JSON_CONTRACT.required_output_files)
REQUIRED_QUALITY_KEYS = set(RUN_JSON_CONTRACT.required_quality_keys)
REQUIRED_TIMING_KEYS = set(RUN_JSON_CONTRACT.required_timing_keys)


def _expect_hash_matches(
    payload: dict[str, Any], object_key: str, hash_key: str, errors: list[str]
) -> None:
    value = payload.get(object_key)
    expected = payload.get(hash_key)
    if not isinstance(value, dict) or not isinstance(expected, str) or not HEX_64.match(expected):
        return
    actual = _sha256_json(value)
    if actual != expected:
        errors.append(f"`{hash_key}` does not match `{object_key}`")


def _expect_equal(left: Any, right: Any, label: str, errors: list[str]) -> None:
    if left != right:
        errors.append(f"`{label}` mismatch")


def validate_run_json_payload(payload: Any) -> list[str]:
    """Validate work/run.json schema invariants."""
    if not isinstance(payload, dict):
        return ["run json root must be an object"]

    errors: list[str] = []
    for key in missing_keys(payload, REQUIRED_RUN_TOP_LEVEL):
        errors.append(f"missing top-level key `{key}`")
    if payload.get("success") is not True:
        errors.append("`success` must be true")

    for key in (
        "audio_duration",
        "chunk_length",
        "overlap",
        "runtime_seconds",
        "chunk_runtime_seconds",
    ):
        expect_nonnegative_number(payload, key, errors)
    for key in (
        "transcription_fingerprint_sha256",
        "postprocess_fingerprint_sha256",
        "chunk_layout_sha256",
    ):
        expect_hash(payload, key, errors)

    input_file = expect_dict(payload, "input_file", errors)
    for key in ("path", "size_bytes", "mtime", "sha256"):
        if key not in input_file:
            errors.append(f"missing input file key `{key}`")
    if "sha256" in input_file:
        expect_hash(input_file, "sha256", errors)

    prepared_audio = expect_dict(payload, "prepared_audio", errors)
    for key in ("path", "size_bytes", "mtime", "sha256", "duration", "sample_rate", "channels"):
        if key not in prepared_audio:
            errors.append(f"missing prepared audio key `{key}`")
    if "sha256" in prepared_audio:
        expect_hash(prepared_audio, "sha256", errors)
    for key in ("prepare_tool", "prepare_command", "ffmpeg_command"):
        if key in prepared_audio and not isinstance(prepared_audio[key], str):
            errors.append(f"`prepared_audio.{key}` must be a string")

    backend_capabilities = expect_dict(payload, "backend_capabilities", errors)
    for key in ("supports_prompt", "supports_word_timestamps", "supports_diarization"):
        if key not in backend_capabilities:
            errors.append(f"missing backend capability `{key}`")
        if key in backend_capabilities and not isinstance(backend_capabilities[key], bool):
            errors.append(f"`backend_capabilities.{key}` must be boolean")

    transcription_fingerprint = expect_dict(payload, "transcription_fingerprint", errors)
    for key in (
        "version",
        "backend",
        "model",
        "input_sha256",
        "prepared_audio_sha256",
        "chunk_layout_sha256",
        "prompt_sha256",
    ):
        if key not in transcription_fingerprint:
            errors.append(f"missing transcription fingerprint key `{key}`")
    postprocess_fingerprint = expect_dict(payload, "postprocess_fingerprint", errors)
    for key in ("version", "glossary_sha256", "correction_pipeline"):
        if key not in postprocess_fingerprint:
            errors.append(f"missing postprocess fingerprint key `{key}`")

    chunk_layout = expect_dict(payload, "chunk_layout", errors)
    for key in ("version", "sample_rate", "audio_duration", "chunk_length", "overlap", "chunks"):
        if key not in chunk_layout:
            errors.append(f"missing chunk layout key `{key}`")
    if not isinstance(chunk_layout.get("chunks"), list) or not chunk_layout.get("chunks"):
        errors.append("`chunk_layout.chunks` must be a non-empty list")

    _expect_hash_matches(
        payload, "transcription_fingerprint", "transcription_fingerprint_sha256", errors
    )
    _expect_hash_matches(
        payload, "postprocess_fingerprint", "postprocess_fingerprint_sha256", errors
    )
    _expect_hash_matches(payload, "chunk_layout", "chunk_layout_sha256", errors)
    if isinstance(transcription_fingerprint, dict):
        _expect_equal(
            transcription_fingerprint.get("input_sha256"),
            input_file.get("sha256"),
            "transcription_fingerprint.input_sha256 vs input_file.sha256",
            errors,
        )
        _expect_equal(
            transcription_fingerprint.get("prepared_audio_sha256"),
            prepared_audio.get("sha256"),
            "transcription_fingerprint.prepared_audio_sha256 vs prepared_audio.sha256",
            errors,
        )
        _expect_equal(
            transcription_fingerprint.get("chunk_layout_sha256"),
            payload.get("chunk_layout_sha256"),
            "transcription_fingerprint.chunk_layout_sha256 vs chunk_layout_sha256",
            errors,
        )

    status_counts = expect_dict(payload, "chunk_status_counts", errors)
    for key in missing_keys(status_counts, REQUIRED_STATUS_KEYS):
        errors.append(f"missing chunk status count `{key}`")
    for key, value in status_counts.items():
        if not isinstance(value, int) or value < 0:
            errors.append(f"`chunk_status_counts.{key}` must be a non-negative integer")

    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        errors.append("`chunks` must be a non-empty list")
    else:
        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                errors.append(f"`chunks[{index}]` must be an object")
                continue
            for key in ("index", "wav", "json", "status", "core_start", "core_end"):
                if key not in chunk:
                    errors.append(f"missing `chunks[{index}].{key}`")

    review = expect_dict(payload, "review", errors)
    for key in ("issue_count", "segment_issue_count"):
        if key not in review:
            errors.append(f"missing review summary key `{key}`")
        elif not isinstance(review[key], int) or review[key] < 0:
            errors.append(f"`review.{key}` must be a non-negative integer")

    qa = expect_dict(payload, "qa", errors)
    if qa.get("status") not in {"pass", "fail"}:
        errors.append("`qa.status` must be `pass` or `fail`")
    for key in ("issue_count", "blocking_issue_count", "warning_count"):
        if key not in qa:
            errors.append(f"missing qa summary key `{key}`")
        elif not isinstance(qa[key], int) or qa[key] < 0:
            errors.append(f"`qa.{key}` must be a non-negative integer")

    repair = expect_dict(payload, "repair", errors)
    if "applied" not in repair:
        errors.append("missing repair key `applied`")
    elif not isinstance(repair["applied"], bool):
        errors.append("`repair.applied` must be boolean")
    if "repair_run_ids" not in repair:
        errors.append("missing repair key `repair_run_ids`")
    elif not isinstance(repair["repair_run_ids"], list) or not all(
        isinstance(item, str) for item in repair["repair_run_ids"]
    ):
        errors.append("`repair.repair_run_ids` must be a list of strings")

    cloud = expect_dict(payload, "cloud", errors)
    for key in ("prepared", "audio_uploaded"):
        if key not in cloud:
            errors.append(f"missing cloud key `{key}`")
        elif not isinstance(cloud[key], bool):
            errors.append(f"`cloud.{key}` must be boolean")
    if "outputs" not in cloud:
        errors.append("missing cloud key `outputs`")
    elif not isinstance(cloud["outputs"], list) or not all(
        isinstance(item, str) for item in cloud["outputs"]
    ):
        errors.append("`cloud.outputs` must be a list of strings")
    if cloud.get("audio_uploaded") is not False:
        errors.append("`cloud.audio_uploaded` must be false")

    quality = expect_dict(payload, "quality_metrics", errors)
    for key in missing_keys(quality, REQUIRED_QUALITY_KEYS):
        errors.append(f"missing quality metric `{key}`")
    for key in REQUIRED_QUALITY_KEYS - {"correction_kind_counts", "timing", "top_token_ratio"}:
        if key in quality and (not isinstance(quality[key], int) or quality[key] < 0):
            errors.append(f"`quality_metrics.{key}` must be a non-negative integer")
    if "top_token_ratio" in quality and (
        not is_number(quality["top_token_ratio"]) or not 0 <= float(quality["top_token_ratio"]) <= 1
    ):
        errors.append("`quality_metrics.top_token_ratio` must be between 0 and 1")
    if "correction_kind_counts" in quality and not isinstance(
        quality["correction_kind_counts"], dict
    ):
        errors.append("`quality_metrics.correction_kind_counts` must be an object")
    timing_payload = quality.get("timing")
    timing = timing_payload if isinstance(timing_payload, dict) else {}
    if not isinstance(timing_payload, dict):
        errors.append("`quality_metrics.timing` must be an object")
    for key in missing_keys(timing, REQUIRED_TIMING_KEYS):
        errors.append(f"missing timing metric `{key}`")
    if "srt_vtt_compatible" in timing and not isinstance(timing["srt_vtt_compatible"], bool):
        errors.append("`quality_metrics.timing.srt_vtt_compatible` must be boolean")

    output_files = expect_dict(payload, "output_files", errors)
    for key in missing_keys(output_files, REQUIRED_OUTPUT_FILES):
        errors.append(f"missing output file key `{key}`")
    for key, value in output_files.items():
        if not isinstance(value, str) or not value:
            errors.append(f"`output_files.{key}` must be a non-empty string")

    return errors
