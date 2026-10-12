from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from .asr_guard import RETRY_TEMPERATURES

if TYPE_CHECKING:
    from .pipeline import TranscribeOptions


@dataclass(frozen=True)
class DecodeProfile:
    name: str
    description: str
    options: dict[str, Any]


DECODE_PROFILES: dict[str, DecodeProfile] = {
    "fast": DecodeProfile(
        name="fast",
        description="Shorter chunks and conservative decode settings for faster local runs.",
        options={
            "chunk_length": 12 * 60,
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "temperature": 0.0,
        },
    ),
    "balanced_zh_podcast": DecodeProfile(
        name="balanced_zh_podcast",
        description="Default Chinese podcast balance that avoids cross-window decode loops on the first pass.",
        options={
            "chunk_length": 20 * 60,
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "temperature": RETRY_TEMPERATURES,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0,
            "compression_ratio_threshold": 2.4,
        },
    ),
    "quality_zh_podcast": DecodeProfile(
        name="quality_zh_podcast",
        description="Higher-detail Chinese podcast profile with word timestamps enabled.",
        options={
            "chunk_length": 15 * 60,
            "condition_on_previous_text": False,
            "word_timestamps": True,
            "temperature": RETRY_TEMPERATURES,
            "no_speech_threshold": 0.5,
            "logprob_threshold": -1.0,
            "compression_ratio_threshold": 2.2,
        },
    ),
    "anti_repeat_zh_podcast": DecodeProfile(
        name="anti_repeat_zh_podcast",
        description="Chinese podcast rerun profile that disables previous-text conditioning for repeated or runaway windows.",
        options={
            "chunk_length": 15 * 60,
            "overlap": 12,
            "condition_on_previous_text": False,
            "word_timestamps": False,
            "temperature": RETRY_TEMPERATURES,
            "no_speech_threshold": 0.55,
            "logprob_threshold": -0.9,
            "compression_ratio_threshold": 2.2,
        },
    ),
    "repair_strict": DecodeProfile(
        name="repair_strict",
        description="Narrow low-temperature settings for repair windows and hallucination-sensitive reruns.",
        options={
            "chunk_length": 8 * 60,
            "condition_on_previous_text": False,
            "word_timestamps": True,
            "temperature": 0.0,
            "no_speech_threshold": 0.45,
            "logprob_threshold": -0.8,
            "compression_ratio_threshold": 2.0,
            "hallucination_silence_threshold": 1.0,
        },
    ),
}


def profile_names() -> list[str]:
    return list(DECODE_PROFILES)


def describe_profiles() -> list[dict[str, Any]]:
    return [
        {
            "name": profile.name,
            "description": profile.description,
            "options": profile.options,
        }
        for profile in DECODE_PROFILES.values()
    ]


def apply_decode_profile(options: TranscribeOptions) -> TranscribeOptions:
    if not options.profile:
        return options
    profile = DECODE_PROFILES.get(options.profile)
    if profile is None:
        raise ValueError(f"Unknown decode profile: {options.profile}")
    return replace(options, **profile.options)
