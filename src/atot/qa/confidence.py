from __future__ import annotations

from typing import Any, Callable

from ..numeric import as_float
from .policy import IssueType
from ..utils import compact_ws, seconds_to_hms

IssueFactory = Callable[..., dict[str, Any]]


def segment_metric(segment: dict[str, Any], key: str) -> float | None:
    value = as_float(segment.get(key))
    if value is not None:
        return value
    raw = segment.get("raw")
    if isinstance(raw, dict):
        return as_float(raw.get(key))
    return None


def segment_confidence_issues(
    segments: list[dict[str, Any]],
    *,
    settings: dict[str, Any],
    issue_factory: IssueFactory,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        start = as_float(segment.get("start")) or 0.0
        end = as_float(segment.get("end")) or start
        duration = max(0.0, end - start)
        text_len = len(compact_ws(str(segment.get("text", ""))))
        min_blocker_duration = float(settings.get("min_low_confidence_blocker_duration", 1.0))
        min_blocker_chars = int(settings.get("min_low_confidence_blocker_chars", 4))
        can_block_confidence = duration >= min_blocker_duration and text_len >= min_blocker_chars
        avg_logprob = segment_metric(segment, "avg_logprob")
        if avg_logprob is not None:
            blocker = float(settings.get("min_avg_logprob_blocker", -1.5))
            warning = float(settings.get("min_avg_logprob_warning", -1.1))
            if avg_logprob < blocker:
                severity = "blocker" if can_block_confidence else "warning"
                issues.append(
                    issue_factory(
                        severity,
                        IssueType.LOW_AVG_LOGPROB_SEGMENT,
                        "ASR average log probability is very low"
                        if severity == "blocker"
                        else "ASR average log probability is very low on a short segment",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        avg_logprob=round(avg_logprob, 4),
                        threshold=blocker,
                        duration=round(duration, 3),
                        text_length=text_len,
                        thresholds={
                            "min_blocker_duration": min_blocker_duration,
                            "min_blocker_chars": min_blocker_chars,
                        },
                        repairable=True,
                    )
                )
            elif avg_logprob < warning:
                issues.append(
                    issue_factory(
                        "warning",
                        IssueType.LOW_AVG_LOGPROB_SEGMENT,
                        "ASR average log probability is low",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        avg_logprob=round(avg_logprob, 4),
                        threshold=warning,
                        repairable=True,
                    )
                )
        compression_ratio = segment_metric(segment, "compression_ratio")
        if compression_ratio is not None:
            blocker = float(settings.get("max_compression_ratio_blocker", 3.0))
            warning = float(settings.get("max_compression_ratio_warning", 2.4))
            if compression_ratio > blocker:
                severity = "blocker" if can_block_confidence else "warning"
                issues.append(
                    issue_factory(
                        severity,
                        IssueType.HIGH_COMPRESSION_RATIO_SEGMENT,
                        "ASR compression ratio is very high; possible hallucination or repetition"
                        if severity == "blocker"
                        else "ASR compression ratio is high on a short segment",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        compression_ratio=round(compression_ratio, 4),
                        threshold=blocker,
                        repairable=True,
                    )
                )
            elif compression_ratio > warning:
                issues.append(
                    issue_factory(
                        "warning",
                        IssueType.HIGH_COMPRESSION_RATIO_SEGMENT,
                        "ASR compression ratio is high",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        compression_ratio=round(compression_ratio, 4),
                        threshold=warning,
                        repairable=True,
                    )
                )
        no_speech_prob = segment_metric(segment, "no_speech_prob")
        if no_speech_prob is not None and text_len >= 8:
            blocker = float(settings.get("max_no_speech_prob_blocker", 0.92))
            warning = float(settings.get("max_no_speech_prob_warning", 0.80))
            if no_speech_prob > blocker:
                issues.append(
                    issue_factory(
                        "blocker",
                        IssueType.HIGH_NO_SPEECH_PROB_SEGMENT,
                        "ASR marked this text segment as likely no-speech",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        no_speech_prob=round(no_speech_prob, 4),
                        threshold=blocker,
                        repairable=True,
                    )
                )
            elif no_speech_prob > warning:
                issues.append(
                    issue_factory(
                        "warning",
                        IssueType.HIGH_NO_SPEECH_PROB_SEGMENT,
                        "ASR no-speech probability is high for a non-empty text segment",
                        index=index,
                        start=start,
                        end=end,
                        time=seconds_to_hms(start),
                        no_speech_prob=round(no_speech_prob, 4),
                        threshold=warning,
                        repairable=True,
                    )
                )
    return issues
