from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_object(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing JSON file: {path}")
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        errors.append(f"{path}: must be a JSON object")
        return {}
    return payload


def _validate_gate_summary(
    path: Path, *, min_audio_count: int, errors: list[str]
) -> dict[str, Any]:
    payload = _read_object(path, errors)
    candidate = payload.get("candidate")
    if not isinstance(candidate, str) or not candidate:
        errors.append(f"{path}: `candidate` must be a non-empty string")
    if payload.get("success") is not True:
        errors.append(f"{path}: gate summary success must be true")
    audio_count = payload.get("audio_count")
    if not isinstance(audio_count, int) or audio_count < min_audio_count:
        errors.append(f"{path}: audio_count must be at least {min_audio_count}")
    if payload.get("failed_count") not in (0, None):
        errors.append(f"{path}: failed_count must be 0")
    if payload.get("guardrail_failed_count") not in (0, None):
        errors.append(f"{path}: guardrail_failed_count must be 0")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{path}: `rows` must be a non-empty list")
        return payload
    if isinstance(audio_count, int) and audio_count != len(rows):
        errors.append(f"{path}: audio_count must match rows length")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{path}: rows[{index}] must be an object")
            continue
        if row.get("success") is not True:
            errors.append(f"{path}: rows[{index}].success must be true")
        if row.get("metric_guardrail_pass") is not True:
            errors.append(f"{path}: rows[{index}].metric_guardrail_pass must be true")
        if row.get("metric_guardrail_failures") not in ([], None):
            errors.append(f"{path}: rows[{index}].metric_guardrail_failures must be empty")
        if row.get("candidate_srt_vtt_compatible") is not True:
            errors.append(f"{path}: rows[{index}].candidate_srt_vtt_compatible must be true")
    return payload


def _validate_semantic_review(
    path: Path,
    *,
    gate: dict[str, Any],
    min_audio_count: int,
    min_content_type_count: int,
    min_gold_fixture_count: int,
    errors: list[str],
) -> None:
    review = _read_object(path, errors)
    if review.get("candidate") != gate.get("candidate"):
        errors.append(f"{path}: semantic review candidate must match gate summary")
    if review.get("decision") != "promote":
        errors.append(f"{path}: decision must be `promote`")
    if not str(review.get("reviewer", "")).strip():
        errors.append(f"{path}: reviewer must be recorded")
    reviewed_audios = review.get("reviewed_audios")
    if not isinstance(reviewed_audios, list) or len(reviewed_audios) < min_audio_count:
        errors.append(f"{path}: reviewed_audios must include at least {min_audio_count} items")
    gold_fixture_count = review.get("gold_fixture_count")
    if not isinstance(gold_fixture_count, int) or gold_fixture_count < min_gold_fixture_count:
        errors.append(f"{path}: gold_fixture_count must be at least {min_gold_fixture_count}")
    full_length_audio_count = review.get("full_length_audio_count")
    if not isinstance(full_length_audio_count, int) or full_length_audio_count < min_audio_count:
        errors.append(f"{path}: full_length_audio_count must be at least {min_audio_count}")
    content_types = review.get("content_types")
    if (
        not isinstance(content_types, list)
        or len({str(item).strip() for item in content_types if str(item).strip()})
        < min_content_type_count
    ):
        errors.append(
            f"{path}: content_types must include at least {min_content_type_count} distinct items"
        )
    for key in ("summary", "quality_notes", "risk_notes"):
        if not str(review.get(key, "")).strip():
            errors.append(f"{path}: `{key}` must be a non-empty string")
    if review.get("semantic_errors") not in (0, None):
        errors.append(f"{path}: semantic_errors must be 0 for promotion")
    if review.get("hallucination_risk") not in ("low", "none"):
        errors.append(f"{path}: hallucination_risk must be `low` or `none`")
    for key in (
        "qa_blocker_regressions",
        "review_issue_regressions",
    ):
        if review.get(key) not in (0, None):
            errors.append(f"{path}: {key} must be 0 for promotion")
    for key in (
        "character_density_stable",
        "runtime_acceptable",
        "memory_acceptable",
    ):
        if review.get(key) is not True:
            errors.append(f"{path}: {key} must be true for promotion")


def validate_backend_promotion(
    gate_summary: Path,
    semantic_review: Path,
    *,
    min_audio_count: int = 3,
    min_content_type_count: int = 3,
    min_gold_fixture_count: int = 1,
) -> list[str]:
    errors: list[str] = []
    gate = _validate_gate_summary(gate_summary, min_audio_count=min_audio_count, errors=errors)
    _validate_semantic_review(
        semantic_review,
        gate=gate,
        min_audio_count=min_audio_count,
        min_content_type_count=min_content_type_count,
        min_gold_fixture_count=min_gold_fixture_count,
        errors=errors,
    )
    return errors
