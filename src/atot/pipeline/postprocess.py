from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..corrections import apply_corrections_to_segments, segments_to_plain_text
from ..entity_consistency import build_entity_consistency_report
from ..quality import build_quality_metrics
from ..review import build_review


@dataclass(frozen=True)
class LocalPostprocessResult:
    corrected_segments: list[dict[str, Any]]
    correction_report: list[dict[str, Any]]
    corrected_text: str
    review: dict[str, Any]
    quality_metrics: dict[str, Any]


def run_local_postprocess(
    raw_segments: list[dict[str, Any]],
    glossary: dict[str, Any],
    *,
    audio_duration: float,
    rule_packs: tuple[str, ...] | list[str] | None = None,
) -> LocalPostprocessResult:
    corrected_segments, correction_report = apply_corrections_to_segments(
        raw_segments,
        glossary,
        audio_duration=audio_duration,
    )
    corrected_text = segments_to_plain_text(corrected_segments)
    review = build_review(corrected_segments, glossary, rule_packs=rule_packs)
    review["entity_consistency"] = build_entity_consistency_report(corrected_segments, glossary)
    quality_metrics = build_quality_metrics(
        raw_segments=raw_segments,
        corrected_segments=corrected_segments,
        corrections=correction_report,
        review=review,
    )
    return LocalPostprocessResult(
        corrected_segments=corrected_segments,
        correction_report=correction_report,
        corrected_text=corrected_text,
        review=review,
        quality_metrics=quality_metrics,
    )
