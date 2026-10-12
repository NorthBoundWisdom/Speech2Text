from __future__ import annotations

from collections import Counter
import re
from typing import Any, Callable

from ..numeric import as_float
from .policy import IssueType
from ..utils import compact_ws, seconds_to_hms

IssueFactory = Callable[..., dict[str, Any]]

ASCII_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
REPEATED_PHRASE_RE = re.compile(
    r"(?P<unit>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]{2,16})(?P=unit){2,}"
)
ENGLISH_PUNCT_IN_CJK_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff]\s*[,?!]\s*[\u3400-\u4dbf\u4e00-\u9fff]"
)


def normalized_text_for_repeat(text: str) -> str:
    return re.sub(r"[^\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]+", "", text)


def _find_runaway_repeat(text: str) -> dict[str, Any] | None:
    normalized = normalized_text_for_repeat(text)
    if len(normalized) < 6:
        return None
    for unit_len in range(2, min(18, len(normalized) // 3) + 1):
        pattern = re.compile(rf"(?P<unit>.{{{unit_len}}})(?P=unit){{2,}}")
        match = pattern.search(normalized)
        if not match:
            continue
        unit = match.group("unit")
        repeat_count = len(match.group(0)) // max(1, len(unit))
        if len(unit) <= 3 and repeat_count < 4:
            continue
        return {"unit": unit, "repeat_count": repeat_count, "normalized_span": match.group(0)}
    return None


def _repeat_info_from_regex(match: re.Match[str] | None) -> dict[str, Any] | None:
    if match is None:
        return None
    unit = match.group("unit")
    span = match.group(0)
    return {
        "unit": unit,
        "repeat_count": span.count(unit),
        "normalized_span": normalized_text_for_repeat(span),
    }


def _repeat_issue_payload(
    *,
    start: float,
    end: float,
    repeated_info: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    unit = str(repeated_info.get("unit") or "")
    repeat_count = int(repeated_info.get("repeat_count") or 0)
    normalized_span = str(repeated_info.get("normalized_span") or "")
    duration = max(0.0, end - start)
    short_threshold = int(settings.get("min_short_repeat_blocker_count", 8))
    long_threshold = int(settings.get("min_long_repeat_blocker_count", 4))
    count_threshold = short_threshold if len(unit) <= 3 else long_threshold
    span_threshold = int(settings.get("min_repeated_phrase_blocker_chars", 80))
    duration_threshold = float(settings.get("min_repeated_phrase_blocker_duration", 12.0))
    severity = "warning"
    if repeat_count >= count_threshold or len(normalized_span) >= span_threshold:
        severity = "blocker"
    elif duration >= duration_threshold and repeat_count >= max(3, long_threshold):
        severity = "blocker"
    return {
        "severity": severity,
        "text": unit,
        "repeat_count": repeat_count,
        "repeat_span_chars": len(normalized_span),
        "duration": round(duration, 3),
        "thresholds": {
            "min_repeat_count": count_threshold,
            "min_span_chars": span_threshold,
            "min_duration": duration_threshold,
        },
    }


def text_quality_issues(
    segments: list[dict[str, Any]],
    *,
    glossary: dict[str, Any] | None,
    settings: dict[str, Any],
    issue_factory: IssueFactory,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    all_text = "\n".join(compact_ws(str(segment.get("text", ""))) for segment in segments)
    duplicate_window = float(settings.get("duplicate_segment_window_seconds", 8.0))
    previous_text = ""
    previous_start: float | None = None
    previous_end: float | None = None
    for index, segment in enumerate(segments):
        text = compact_ws(str(segment.get("text", "")))
        start = as_float(segment.get("start")) or 0.0
        end = as_float(segment.get("end")) or start
        if not text:
            if segment.get("suppressed") is True:
                continue
            issues.append(
                issue_factory(
                    "blocker",
                    IssueType.EMPTY_SEGMENT_TEXT,
                    "Segment text is empty",
                    index=index,
                    start=start,
                    end=end,
                )
            )
            continue
        repeated = REPEATED_PHRASE_RE.search(text)
        repeated_info = _find_runaway_repeat(text) or _repeat_info_from_regex(repeated)
        if repeated_info:
            repeat_payload = _repeat_issue_payload(
                start=start, end=end, repeated_info=repeated_info, settings=settings
            )
            issues.append(
                issue_factory(
                    str(repeat_payload["severity"]),
                    IssueType.REPEATED_PHRASE,
                    "Repeated phrase detected",
                    index=index,
                    start=start,
                    end=end,
                    time=seconds_to_hms(start),
                    repairable=True,
                    text=repeat_payload["text"],
                    repeat_count=repeat_payload["repeat_count"],
                    repeat_span_chars=repeat_payload["repeat_span_chars"],
                    duration=repeat_payload["duration"],
                    thresholds=repeat_payload["thresholds"],
                )
            )
        if (
            previous_text
            and text == previous_text
            and previous_end is not None
            and previous_start is not None
        ):
            if abs(start - previous_end) <= duplicate_window:
                duplicate_duration = max(0.0, end - previous_start)
                normalized_duplicate = normalized_text_for_repeat(text)
                min_chars = int(settings.get("min_duplicate_segment_blocker_chars", 12))
                min_duration = float(settings.get("min_duplicate_segment_blocker_duration", 1.5))
                severity = (
                    "blocker"
                    if len(normalized_duplicate) >= min_chars and duplicate_duration >= min_duration
                    else "warning"
                )
                issues.append(
                    issue_factory(
                        severity,
                        IssueType.ADJACENT_DUPLICATE_SEGMENT,
                        "Adjacent segments contain identical text",
                        index=index,
                        previous_index=index - 1,
                        start=previous_start,
                        end=end,
                        time=seconds_to_hms(previous_start),
                        text=text[:120],
                        duplicate_chars=len(normalized_duplicate),
                        duration=round(duplicate_duration, 3),
                        thresholds={"min_chars": min_chars, "min_duration": min_duration},
                        repairable=True,
                    )
                )
        previous_text = text
        previous_start = start
        previous_end = end
        if CONTROL_RE.search(text):
            issues.append(
                issue_factory(
                    "blocker",
                    "control_character",
                    "Control character detected",
                    index=index,
                    start=start,
                    end=end,
                )
            )
        if ENGLISH_PUNCT_IN_CJK_RE.search(text):
            issues.append(
                issue_factory(
                    "warning",
                    IssueType.ENGLISH_PUNCTUATION_IN_CHINESE,
                    "ASCII punctuation appears in Chinese context",
                    index=index,
                    start=start,
                    end=end,
                    time=seconds_to_hms(start),
                    postprocessable=True,
                )
            )

    ascii_tokens = ASCII_TOKEN_RE.findall(all_text)
    if ascii_tokens:
        token_counts = Counter(ascii_tokens)
        uncommon = [
            token
            for token, count in token_counts.most_common(20)
            if count >= 2 and token.upper() not in {"HTTP", "HTTPS", "URL", "API", "GPT", "AI"}
        ]
        if uncommon:
            issues.append(
                issue_factory(
                    "warning",
                    "unknown_ascii_tokens",
                    "Repeated ASCII-like tokens may need glossary review",
                    tokens=uncommon[:10],
                )
            )

    corrections = (glossary or {}).get("common_corrections", {})
    if isinstance(corrections, dict):
        hits = [wrong for wrong in corrections if wrong and wrong in all_text]
        if hits:
            issues.append(
                issue_factory(
                    "warning",
                    "known_confusion_terms_present",
                    "Known glossary confusion terms remain in transcript",
                    terms=hits[:20],
                )
            )
    return issues
