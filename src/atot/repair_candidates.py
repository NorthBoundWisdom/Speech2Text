from __future__ import annotations

from typing import Any

from .numeric import as_float, as_int


DEFAULT_REPAIR_CANDIDATES = ("default", "anti_repeat_zh_podcast")
REPAIR_CANDIDATE_CHOICES = ("default", "anti_repeat_zh_podcast", "repair_strict")
MIN_REPAIR_CHAR_RATIO = 0.25
MAX_REPAIR_CHAR_RATIO = 3.5
MIN_REPAIR_COVERAGE_RATIO = 0.85
MIN_REPAIR_SCORE_IMPROVEMENT = 1.0


def normalize_repair_candidate_profiles(
    profiles: tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in profiles or DEFAULT_REPAIR_CANDIDATES:
        profile = str(raw).strip()
        if profile not in REPAIR_CANDIDATE_CHOICES:
            raise ValueError(f"Unknown repair candidate profile: {profile}")
        if profile not in normalized:
            normalized.append(profile)
    return tuple(normalized or DEFAULT_REPAIR_CANDIDATES)


def segment_char_count(segments: list[dict[str, Any]]) -> int:
    return len("".join("".join(str(segment.get("text", "")).split()) for segment in segments))


def segment_time_coverage(segments: list[dict[str, Any]], *, start: float, end: float) -> float:
    intervals: list[tuple[float, float]] = []
    for segment in segments:
        try:
            seg_start = max(start, float(segment.get("start", 0.0)))
            seg_end = min(end, float(segment.get("end", seg_start)))
        except (TypeError, ValueError):
            continue
        if seg_end > seg_start:
            intervals.append((seg_start, seg_end))
    if not intervals:
        return 0.0
    intervals.sort()
    merged: list[tuple[float, float]] = []
    for seg_start, seg_end in intervals:
        if not merged or seg_start > merged[-1][1]:
            merged.append((seg_start, seg_end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], seg_end))
    return sum(seg_end - seg_start for seg_start, seg_end in merged)


def qa_score(qa: dict[str, Any]) -> float:
    weights = {
        "blocker": 100.0,
        "error": 50.0,
        "high": 25.0,
        "medium": 10.0,
        "warning": 10.0,
        "low": 1.0,
    }
    issues = qa.get("issues", []) if isinstance(qa.get("issues"), list) else []
    score = 0.0
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        score += weights.get(str(issue.get("severity") or "warning"), 5.0)
    if qa.get("success") is False and not issues:
        score += 100.0
    return score


def qa_blocker_count(qa: dict[str, Any]) -> int:
    issues = qa.get("issues", []) if isinstance(qa.get("issues"), list) else []
    return sum(
        1 for issue in issues if isinstance(issue, dict) and str(issue.get("severity")) == "blocker"
    )


def candidate_ratios(
    *,
    before_chars: int,
    before_coverage: float,
    replacements: list[dict[str, Any]],
    start: float,
    end: float,
) -> tuple[int, float, float, float]:
    replacement_chars = segment_char_count(replacements)
    replacement_coverage = segment_time_coverage(replacements, start=start, end=end)
    char_ratio = (
        replacement_chars / before_chars
        if before_chars > 0
        else (1.0 if replacement_chars == 0 else MAX_REPAIR_CHAR_RATIO)
    )
    coverage_ratio = (
        replacement_coverage / before_coverage
        if before_coverage > 0
        else (1.0 if replacement_coverage > 0 else 0.0)
    )
    return replacement_chars, replacement_coverage, char_ratio, coverage_ratio


def candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    segments = candidate.get("segments")
    reasons = candidate.get("reasons")
    return {
        "id": candidate["id"],
        "profile": candidate.get("profile"),
        "kind": candidate.get("kind"),
        "segment_count": len(segments) if isinstance(segments, list) else 0,
        "char_count": candidate.get("char_count", 0),
        "char_ratio": candidate.get("char_ratio"),
        "coverage_seconds": candidate.get("coverage_seconds", 0.0),
        "coverage_ratio": candidate.get("coverage_ratio"),
        "qa_score": candidate.get("qa_score", 0.0),
        "blocker_count": candidate.get("blocker_count", 0),
        "rank": candidate.get("rank"),
        "eligible": candidate.get("eligible", False),
        "reasons": reasons if isinstance(reasons, list) else [],
    }


def evaluate_repair_candidates(
    *,
    before: list[dict[str, Any]],
    qa_before: dict[str, Any],
    candidates: list[dict[str, Any]],
    start: float,
    end: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    before_chars = segment_char_count(before)
    before_coverage = segment_time_coverage(before, start=start, end=end)
    baseline_score = qa_score(qa_before)
    baseline = {
        "id": "baseline",
        "profile": "baseline",
        "kind": "baseline",
        "segments": before,
        "corrections": [],
        "qa": qa_before,
        "qa_score": baseline_score,
        "blocker_count": qa_blocker_count(qa_before),
        "char_count": before_chars,
        "char_ratio": 1.0,
        "coverage_seconds": before_coverage,
        "coverage_ratio": 1.0 if before_coverage > 0 else 0.0,
        "eligible": False,
        "reasons": ["baseline_current_window"],
    }
    evaluated = [baseline]
    for candidate in candidates:
        replacement_chars, replacement_coverage, char_ratio, coverage_ratio = candidate_ratios(
            before_chars=before_chars,
            before_coverage=before_coverage,
            replacements=candidate["segments"],
            start=start,
            end=end,
        )
        score = qa_score(candidate["qa"])
        reasons: list[str] = []
        if not candidate["segments"]:
            reasons.append("no_replacement_segments")
        if candidate["qa"].get("success") is not True:
            reasons.append("window_qa_after_failed")
        if qa_blocker_count(candidate["qa"]):
            reasons.append("new_blocking_window_issue")
        if before_chars > 0 and replacement_chars == 0:
            reasons.append("replacement_text_empty")
        if before_chars > 0 and not (MIN_REPAIR_CHAR_RATIO <= char_ratio <= MAX_REPAIR_CHAR_RATIO):
            reasons.append("character_ratio_out_of_bounds")
        if before_coverage > 0 and coverage_ratio < MIN_REPAIR_COVERAGE_RATIO:
            reasons.append("time_coverage_loss")
        if baseline_score - score < MIN_REPAIR_SCORE_IMPROVEMENT:
            reasons.append("qa_score_not_clearly_better")
        candidate.update(
            {
                "qa_score": score,
                "blocker_count": qa_blocker_count(candidate["qa"]),
                "char_count": replacement_chars,
                "char_ratio": round(char_ratio, 4),
                "coverage_seconds": round(replacement_coverage, 3),
                "coverage_ratio": round(coverage_ratio, 4),
                "eligible": not reasons,
                "reasons": reasons,
            }
        )
        evaluated.append(candidate)
    eligible = [
        candidate
        for candidate in evaluated
        if candidate.get("kind") != "baseline" and candidate.get("eligible")
    ]
    if eligible:

        def candidate_rank(candidate: dict[str, Any]) -> int:
            rank = as_int(candidate.get("rank"))
            return rank if rank is not None else 999

        selected = sorted(
            eligible,
            key=lambda candidate: (
                as_float(candidate.get("qa_score")) or 0.0,
                abs((as_float(candidate.get("char_ratio")) or 1.0) - 1.0),
                -(as_float(candidate.get("coverage_ratio")) or 0.0),
                candidate_rank(candidate),
            ),
        )[0]
        selected_segments = selected.get("segments")
        decision = {
            "action": "apply",
            "reasons": [],
            "selected_candidate": selected["id"],
            "baseline_score": baseline_score,
            "selected_score": selected.get("qa_score", 0.0),
            "before_segment_count": len(before),
            "replacement_segment_count": len(selected_segments)
            if isinstance(selected_segments, list)
            else 0,
            "candidates": [candidate_summary(candidate) for candidate in evaluated],
        }
        return decision, selected
    attempted = [candidate for candidate in evaluated if candidate.get("kind") != "baseline"]
    selected = min(
        attempted,
        key=lambda candidate: as_float(candidate.get("qa_score")) or 9999.0,
        default=baseline,
    )
    selected_segments = selected.get("segments")
    decision = {
        "action": "reject",
        "reasons": ["no_candidate_passed_arbitration"],
        "selected_candidate": selected["id"],
        "baseline_score": baseline_score,
        "selected_score": selected.get("qa_score", baseline_score),
        "before_segment_count": len(before),
        "replacement_segment_count": (
            len(selected_segments)
            if selected.get("kind") != "baseline" and isinstance(selected_segments, list)
            else 0
        ),
        "candidates": [candidate_summary(candidate) for candidate in evaluated],
    }
    return decision, selected
