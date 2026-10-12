from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, cast

from .backends.base import ASRBackend, ASRTranscribeOptions
from .utils import compact_ws, json_safe


DECODE_GUARD_VERSION = 1
RETRY_TEMPERATURES = (0.0, 0.2, 0.4)
MAX_RETRY_ATTEMPTS = 2

HIGH_COMPRESSION_BLOCKER = 3.0
HIGH_COMPRESSION_WARNING = 2.4
MIN_RISK_TEXT_CHARS = 8
MIN_RISK_DURATION_SECONDS = 1.0
MIN_REPEAT_SPAN_CHARS = 80
MIN_SHORT_REPEAT_COUNT = 8
MIN_LONG_REPEAT_COUNT = 4
MIN_ADJACENT_DUPLICATE_COUNT = 2
MIN_MARKER_NOISE_CHARS = 20
MIN_MARKER_NOISE_DENSITY = 0.02
MIN_MARKER_NOISE_SEGMENT_CHARS = 3
MIN_MARKER_NOISE_SEGMENT_DENSITY = 0.08

MARKER_NOISE_RE = re.compile(r"[\uff10-\uff19\uff21-\uff3a\uff41-\uff5a※◆◇■□▲△●○★☆]")


DECODE_GUARD_FINGERPRINT: dict[str, Any] = {
    "version": DECODE_GUARD_VERSION,
    "max_retry_attempts": MAX_RETRY_ATTEMPTS,
    "retry_temperature_fallback": list(RETRY_TEMPERATURES),
    "retry_triggers": [
        "high_compression_segment",
        "repeated_phrase",
        "adjacent_duplicate_segment",
        "marker_noise",
    ],
}


@dataclass(frozen=True)
class ASRHealth:
    score: int
    should_retry: bool
    segment_count: int
    visible_char_count: int
    high_compression_segments: int
    repeated_segments: int
    adjacent_duplicate_segments: int
    marker_noise_segments: int
    marker_noise_chars: int
    max_compression_ratio: float | None
    reasons: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecodeGuardResult:
    result: dict[str, Any]
    audit: dict[str, Any] | None


def transcribe_with_decode_guard(
    backend: ASRBackend,
    audio_path: str | Path,
    options: ASRTranscribeOptions,
) -> DecodeGuardResult:
    attempts: list[dict[str, Any]] = []
    primary = _run_attempt(backend, audio_path, options, name="primary", prompt_mode="full")
    attempts.append(primary)
    best = primary

    if primary["health"].should_retry:
        for retry_options, name, prompt_mode in _retry_attempts(options):
            attempt = _run_attempt(
                backend, audio_path, retry_options, name=name, prompt_mode=prompt_mode
            )
            attempts.append(attempt)
            if _better_attempt(attempt, best):
                best = attempt

    if len(attempts) == 1:
        return DecodeGuardResult(result=primary["result"], audit=None)

    return DecodeGuardResult(
        result=best["result"],
        audit={
            "version": DECODE_GUARD_VERSION,
            "triggered": True,
            "selected_attempt": best["name"],
            "attempts": [_attempt_audit_payload(attempt) for attempt in attempts],
        },
    )


def assess_asr_result(result: dict[str, Any]) -> ASRHealth:
    segments = result.get("segments")
    if not isinstance(segments, list):
        segments = []

    high_compression = 0
    repeated = 0
    adjacent_duplicates = 0
    marker_noise_segments = 0
    marker_noise_chars = 0
    max_compression: float | None = None
    visible_chars = 0
    previous_text = ""
    reasons: list[str] = []

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = compact_ws(str(segment.get("text", "")))
        visible_chars += len(text)
        duration = _segment_duration(segment)
        text_len = len(text)
        segment_marker_noise = _marker_noise_chars(text)
        marker_noise_chars += segment_marker_noise
        if _is_marker_noise_segment(segment_marker_noise, text_len):
            marker_noise_segments += 1

        compression = _segment_metric(segment, "compression_ratio")
        if compression is not None:
            max_compression = (
                compression if max_compression is None else max(max_compression, compression)
            )
            if (
                compression > HIGH_COMPRESSION_BLOCKER
                and text_len >= MIN_RISK_TEXT_CHARS
                and duration >= MIN_RISK_DURATION_SECONDS
            ):
                high_compression += 1

        repeat = _find_runaway_repeat(text)
        if repeat is not None and _repeat_is_blocking(repeat, duration=duration):
            repeated += 1

        if (
            previous_text
            and text == previous_text
            and len(_normalized_text_for_repeat(text)) >= MIN_REPEAT_SPAN_CHARS
        ):
            adjacent_duplicates += 1
        previous_text = text

    if high_compression:
        reasons.append("high_compression_segment")
    if repeated:
        reasons.append("repeated_phrase")
    if adjacent_duplicates >= MIN_ADJACENT_DUPLICATE_COUNT:
        reasons.append("adjacent_duplicate_segment")
    marker_noise_blocking = (
        _is_marker_noise_chunk(marker_noise_chars, visible_chars) or marker_noise_segments > 0
    )
    if marker_noise_blocking:
        reasons.append("marker_noise")

    should_retry = bool(
        high_compression
        or repeated
        or adjacent_duplicates >= MIN_ADJACENT_DUPLICATE_COUNT
        or marker_noise_blocking
    )
    warnings = 0
    if (
        max_compression is not None
        and max_compression > HIGH_COMPRESSION_WARNING
        and not high_compression
    ):
        warnings += 1

    score = 100
    score -= min(80, high_compression * 18)
    score -= min(80, repeated * 22)
    score -= min(50, adjacent_duplicates * 10)
    score -= min(60, marker_noise_segments * 10 + marker_noise_chars // 3)
    score -= warnings * 6
    if visible_chars == 0 and segments:
        score -= 30
    score = max(0, min(100, score))

    return ASRHealth(
        score=score,
        should_retry=should_retry,
        segment_count=len(segments),
        visible_char_count=visible_chars,
        high_compression_segments=high_compression,
        repeated_segments=repeated,
        adjacent_duplicate_segments=adjacent_duplicates,
        marker_noise_segments=marker_noise_segments,
        marker_noise_chars=marker_noise_chars,
        max_compression_ratio=round(max_compression, 4) if max_compression is not None else None,
        reasons=tuple(reasons),
    )


def _run_attempt(
    backend: ASRBackend,
    audio_path: str | Path,
    options: ASRTranscribeOptions,
    *,
    name: str,
    prompt_mode: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    result = backend.transcribe(audio_path, options)
    runtime = time.perf_counter() - started
    return {
        "name": name,
        "prompt_mode": prompt_mode,
        "options": options,
        "result": result,
        "runtime_seconds": runtime,
        "health": assess_asr_result(result),
    }


def _retry_attempts(options: ASRTranscribeOptions) -> list[tuple[ASRTranscribeOptions, str, str]]:
    retry_temperature = _retry_temperature(options.temperature)
    attempts: list[tuple[ASRTranscribeOptions, str, str]] = []
    if options.condition_on_previous_text or retry_temperature != options.temperature:
        attempts.append(
            (
                replace(
                    options,
                    condition_on_previous_text=False,
                    temperature=retry_temperature,
                ),
                "no_previous_text",
                "full",
            )
        )
    if options.prompt:
        attempts.append(
            (
                replace(
                    options,
                    prompt=None,
                    condition_on_previous_text=False,
                    temperature=retry_temperature,
                ),
                "no_prompt_no_previous_text",
                "none",
            )
        )
    return attempts[:MAX_RETRY_ATTEMPTS]


def _retry_temperature(
    temperature: float | tuple[float, ...] | None,
) -> float | tuple[float, ...] | None:
    if isinstance(temperature, tuple):
        return temperature
    if temperature is None:
        return RETRY_TEMPERATURES
    try:
        if float(temperature) == 0.0:
            return RETRY_TEMPERATURES
    except (TypeError, ValueError):
        return temperature
    return temperature


def _better_attempt(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_health: ASRHealth = candidate["health"]
    current_health: ASRHealth = current["health"]
    if candidate_health.score != current_health.score:
        return candidate_health.score > current_health.score
    candidate_risk = (
        candidate_health.high_compression_segments
        + candidate_health.repeated_segments
        + candidate_health.adjacent_duplicate_segments
    )
    current_risk = (
        current_health.high_compression_segments
        + current_health.repeated_segments
        + current_health.adjacent_duplicate_segments
    )
    if candidate_risk != current_risk:
        return candidate_risk < current_risk
    return candidate_health.visible_char_count > current_health.visible_char_count


def _attempt_audit_payload(attempt: dict[str, Any]) -> dict[str, Any]:
    options: ASRTranscribeOptions = attempt["options"]
    return cast(
        dict[str, Any],
        json_safe(
            {
                "name": attempt["name"],
                "prompt_mode": attempt["prompt_mode"],
                "runtime_seconds": round(float(attempt["runtime_seconds"]), 3),
                "decode_options": {
                    "condition_on_previous_text": options.condition_on_previous_text,
                    "temperature": options.temperature,
                    "prompt": "present" if options.prompt else "none",
                },
                "health": attempt["health"].to_json(),
            }
        ),
    )


def _segment_metric(segment: dict[str, Any], key: str) -> float | None:
    value = _as_float(segment.get(key))
    if value is not None:
        return value
    raw = segment.get("raw")
    if isinstance(raw, dict):
        return _as_float(raw.get(key))
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _segment_duration(segment: dict[str, Any]) -> float:
    start = _as_float(segment.get("start")) or 0.0
    end = _as_float(segment.get("end")) or start
    return max(0.0, end - start)


def _normalized_text_for_repeat(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"[^\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]+", "", normalized)


def _marker_noise_chars(text: str) -> int:
    return len(MARKER_NOISE_RE.findall(text))


def _is_marker_noise_segment(marker_chars: int, text_len: int) -> bool:
    if marker_chars < MIN_MARKER_NOISE_SEGMENT_CHARS or text_len <= 0:
        return False
    return marker_chars / text_len >= MIN_MARKER_NOISE_SEGMENT_DENSITY


def _is_marker_noise_chunk(marker_chars: int, visible_chars: int) -> bool:
    if marker_chars < MIN_MARKER_NOISE_CHARS or visible_chars <= 0:
        return False
    return marker_chars / visible_chars >= MIN_MARKER_NOISE_DENSITY


def _find_runaway_repeat(text: str) -> dict[str, Any] | None:
    normalized = _normalized_text_for_repeat(text)
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


def _repeat_is_blocking(repeat: dict[str, Any], *, duration: float) -> bool:
    unit = str(repeat.get("unit") or "")
    repeat_count = int(repeat.get("repeat_count") or 0)
    span_chars = len(str(repeat.get("normalized_span") or ""))
    count_threshold = MIN_SHORT_REPEAT_COUNT if len(unit) <= 3 else MIN_LONG_REPEAT_COUNT
    return (
        repeat_count >= count_threshold
        or span_chars >= MIN_REPEAT_SPAN_CHARS
        or (duration >= 12.0 and repeat_count >= max(3, MIN_LONG_REPEAT_COUNT))
    )
