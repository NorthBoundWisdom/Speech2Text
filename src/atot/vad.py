from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sys
from typing import Any
import wave

from .audio import AudioError, ChunkSpec, optional_command, run_command
from .numeric import as_float


@dataclass(frozen=True)
class Silence:
    start: float
    end: float

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0


SILENCE_START_RE = re.compile(r"silence_start:\s*(?P<value>[0-9.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*(?P<value>[0-9.]+)")
DEFAULT_SILENCE_THRESHOLD = -30.0
MIN_DYNAMIC_SILENCE_THRESHOLD = -45.0
MAX_DYNAMIC_SILENCE_THRESHOLD = -25.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile from no values.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def sample_wav_rms_dbfs(
    audio_path: str | Path,
    *,
    sample_seconds: float = 0.5,
    max_windows: int = 120,
) -> list[float]:
    try:
        with wave.open(str(audio_path), "rb") as wav:
            sample_width = wav.getsampwidth()
            if sample_width != 2:
                return []
            frame_rate = wav.getframerate()
            total_frames = wav.getnframes()
            window_frames = max(1, int(frame_rate * sample_seconds))
            if frame_rate <= 0 or total_frames <= 0 or window_frames <= 0:
                return []
            window_count = max(1, min(max_windows, total_frames // window_frames or 1))
            stride = max(window_frames, (total_frames - window_frames) // max(1, window_count - 1))
            values: list[float] = []
            for index in range(window_count):
                frame = min(index * stride, max(0, total_frames - window_frames))
                wav.setpos(frame)
                frames = wav.readframes(min(window_frames, total_frames - frame))
                samples = array("h")
                samples.frombytes(frames)
                if sys.byteorder == "big":
                    samples.byteswap()
                if not samples:
                    continue
                rms = (
                    math.sqrt(sum(float(item) * float(item) for item in samples) / len(samples))
                    / 32768.0
                )
                values.append(20.0 * math.log10(max(rms, 1e-9)))
            return values
    except (wave.Error, OSError):
        return []


def choose_dynamic_silence_threshold(
    audio_path: str | Path,
    *,
    fallback_threshold: float = DEFAULT_SILENCE_THRESHOLD,
) -> dict[str, Any]:
    samples = sample_wav_rms_dbfs(audio_path)
    if len(samples) < 3:
        return {
            "threshold": fallback_threshold,
            "source": "fallback_default",
            "reason": "insufficient_loudness_samples",
            "sample_count": len(samples),
        }
    noise_floor = _percentile(samples, 0.2)
    speech_level = _percentile(samples, 0.75)
    dynamic_range = speech_level - noise_floor
    if dynamic_range < 6.0:
        return {
            "threshold": fallback_threshold,
            "source": "fallback_default",
            "reason": "low_dynamic_range",
            "sample_count": len(samples),
            "noise_floor_dbfs": round(noise_floor, 2),
            "speech_level_dbfs": round(speech_level, 2),
            "dynamic_range_db": round(dynamic_range, 2),
        }
    threshold = noise_floor + max(4.0, dynamic_range * 0.35)
    threshold = min(threshold, speech_level - 8.0)
    threshold = max(MIN_DYNAMIC_SILENCE_THRESHOLD, min(MAX_DYNAMIC_SILENCE_THRESHOLD, threshold))
    return {
        "threshold": round(threshold, 2),
        "source": "dynamic_rms",
        "sample_count": len(samples),
        "noise_floor_dbfs": round(noise_floor, 2),
        "speech_level_dbfs": round(speech_level, 2),
        "dynamic_range_db": round(dynamic_range, 2),
    }


def detect_silences_ffmpeg(
    audio_path: str | Path,
    *,
    silence_threshold: float = -30.0,
    min_silence: float = 0.5,
) -> list[Silence]:
    ffmpeg = optional_command("ffmpeg")
    if ffmpeg is None:
        raise AudioError("Smart chunking requires ffmpeg silencedetect.")
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(audio_path),
            "-af",
            f"silencedetect=noise={silence_threshold}dB:d={min_silence}",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    if result.returncode != 0:
        raise AudioError(f"ffmpeg silencedetect failed:\n{result.stderr}")
    silences: list[Silence] = []
    current_start: float | None = None
    for line in result.stderr.splitlines():
        start_match = SILENCE_START_RE.search(line)
        if start_match:
            current_start = float(start_match.group("value"))
            continue
        end_match = SILENCE_END_RE.search(line)
        if end_match and current_start is not None:
            end = float(end_match.group("value"))
            if end > current_start:
                silences.append(Silence(start=current_start, end=end))
            current_start = None
    return silences


def assess_silence_points(silences: list[Silence], *, duration: float) -> dict[str, Any]:
    if duration <= 0:
        return {"status": "unknown", "silence_count": len(silences), "silence_ratio": 0.0}
    total_silence = sum(
        max(0.0, min(duration, item.end) - max(0.0, item.start)) for item in silences
    )
    silence_ratio = total_silence / duration
    points_per_hour = len(silences) * 3600.0 / duration
    status = "ok"
    if not silences or points_per_hour < 1.0 or silence_ratio < 0.001:
        status = "too_sparse"
    elif silence_ratio > 0.75 or points_per_hour > 900.0:
        status = "too_dense"
    return {
        "status": status,
        "silence_count": len(silences),
        "silence_seconds": round(total_silence, 3),
        "silence_ratio": round(silence_ratio, 4),
        "points_per_hour": round(points_per_hour, 3),
    }


def _silence_status_rank(status: str) -> int:
    return {"ok": 0, "unknown": 1, "too_sparse": 2, "too_dense": 2}.get(status, 3)


def detect_silences_for_chunking(
    audio_path: str | Path,
    *,
    duration: float,
    silence_threshold: float | None = None,
    min_silence: float = 0.5,
) -> tuple[list[Silence], dict[str, Any]]:
    threshold_plan = (
        choose_dynamic_silence_threshold(audio_path)
        if silence_threshold is None
        else {"threshold": silence_threshold, "source": "explicit"}
    )
    threshold = as_float(threshold_plan.get("threshold"))
    if threshold is None:
        raise AudioError("Silence threshold could not be resolved.")
    silences = detect_silences_ffmpeg(
        audio_path, silence_threshold=threshold, min_silence=min_silence
    )
    assessment = assess_silence_points(silences, duration=duration)
    metadata = {
        **threshold_plan,
        "threshold": threshold,
        "min_silence": min_silence,
        "assessment": assessment,
    }
    if (
        silence_threshold is not None
        or assessment["status"] == "ok"
        or threshold == DEFAULT_SILENCE_THRESHOLD
    ):
        return silences, metadata
    fallback_silences = detect_silences_ffmpeg(
        audio_path,
        silence_threshold=DEFAULT_SILENCE_THRESHOLD,
        min_silence=min_silence,
    )
    fallback_assessment = assess_silence_points(fallback_silences, duration=duration)
    if _silence_status_rank(str(fallback_assessment["status"])) <= _silence_status_rank(
        str(assessment["status"])
    ):
        return fallback_silences, {
            **metadata,
            "threshold": DEFAULT_SILENCE_THRESHOLD,
            "source": "fallback_default",
            "fallback_reason": assessment,
            "assessment": fallback_assessment,
        }
    return silences, metadata


def choose_chunk_boundaries(
    duration: float,
    *,
    target_chunk_length: float,
    max_chunk_length: float,
    silences: list[Silence],
) -> list[float]:
    if duration <= 0:
        raise AudioError("Audio duration must be positive.")
    if target_chunk_length <= 0:
        return [0.0, duration]
    max_chunk_length = max(target_chunk_length, max_chunk_length)
    boundaries = [0.0]
    current = 0.0
    while current + max_chunk_length < duration:
        target = current + target_chunk_length
        lower = current + max(30.0, target_chunk_length * 0.5)
        upper = min(current + max_chunk_length, duration)
        candidates = [
            silence.midpoint for silence in silences if lower <= silence.midpoint <= upper
        ]
        boundary = min(candidates, key=lambda value: abs(value - target)) if candidates else upper
        if boundary <= current:
            boundary = upper
        boundaries.append(round(boundary, 3))
        current = boundary
    if boundaries[-1] < duration:
        boundaries.append(round(duration, 3))
    return boundaries


def build_smart_chunks(
    duration: float,
    *,
    chunks_dir: str | Path,
    target_chunk_length: float,
    max_chunk_length: float,
    overlap: float,
    silences: list[Silence],
) -> list[ChunkSpec]:
    if overlap < 0:
        raise AudioError("Overlap must be non-negative.")
    boundaries = choose_chunk_boundaries(
        duration,
        target_chunk_length=target_chunk_length,
        max_chunk_length=max_chunk_length,
        silences=silences,
    )
    out_dir = Path(chunks_dir)
    specs: list[ChunkSpec] = []
    for index, (core_start, core_end) in enumerate(zip(boundaries, boundaries[1:])):
        source_start = max(0.0, core_start - (overlap if core_start > 0 else 0.0))
        source_end = min(duration, core_end + (overlap if core_end < duration else 0.0))
        specs.append(
            ChunkSpec(
                index=index,
                path=out_dir / f"chunk_{index:04d}.wav",
                source_start=source_start,
                source_end=source_end,
                core_start=core_start,
                core_end=core_end,
            )
        )
    return specs
