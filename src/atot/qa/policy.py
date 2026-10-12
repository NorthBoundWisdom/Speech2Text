from __future__ import annotations

from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any

from ..utils import read_json

DEFAULT_QA_PROFILE = "balanced"


class IssueType(str, Enum):
    LARGE_TIMING_GAP = "large_timing_gap"
    LONG_SEGMENT = "long_segment"
    SEGMENT_OVERLAP = "segment_overlap"
    EMPTY_SEGMENT_TEXT = "empty_segment_text"
    REPEATED_PHRASE = "repeated_phrase"
    ADJACENT_DUPLICATE_SEGMENT = "adjacent_duplicate_segment"
    LOW_AVG_LOGPROB_SEGMENT = "low_avg_logprob_segment"
    HIGH_COMPRESSION_RATIO_SEGMENT = "high_compression_ratio_segment"
    HIGH_NO_SPEECH_PROB_SEGMENT = "high_no_speech_prob_segment"
    ENGLISH_PUNCTUATION_IN_CHINESE = "english_punctuation_in_chinese"

    def __str__(self) -> str:
        return self.value


# Profiles are intentionally generic. They describe transcript-shape risk rather than
# episode-specific vocabulary or sample-specific expected phrases.
QA_PROFILES: dict[str, dict[str, Any]] = {
    "lenient": {
        "max_gap": 120.0,
        "max_segment_duration": 45.0,
        "max_subtitle_chars": 100,
        "max_subtitle_line_chars": 50,
        "min_chars_per_minute": 5.0,
        "max_chars_per_minute": 1200.0,
        "max_gap_coverage_ratio": 0.30,
        "duplicate_segment_window_seconds": 12.0,
        "min_avg_logprob_warning": -1.25,
        "min_avg_logprob_blocker": -1.75,
        "max_compression_ratio_warning": 2.40,
        "max_compression_ratio_blocker": 3.20,
        "max_no_speech_prob_warning": 0.85,
        "max_no_speech_prob_blocker": 0.95,
        "min_short_repeat_blocker_count": 10,
        "min_long_repeat_blocker_count": 5,
        "min_repeated_phrase_blocker_chars": 120,
        "min_repeated_phrase_blocker_duration": 20.0,
        "min_duplicate_segment_blocker_chars": 18,
        "min_duplicate_segment_blocker_duration": 3.0,
        "min_low_confidence_blocker_duration": 1.5,
        "min_low_confidence_blocker_chars": 4,
        "max_readable_paragraph_chars_warning": 420,
        "max_readable_paragraph_chars_blocker": 700,
        "max_readable_run_on_chars": 300,
        "min_readable_chars_for_density": 200,
        "min_readable_punctuation_per_1000_chars": 6.0,
        "repair_padding": 15.0,
        "merge_repair_gap_seconds": 3.0,
        "max_repair_window_seconds": 420.0,
    },
    "balanced": {
        "max_gap": 60.0,
        "max_segment_duration": 30.0,
        "max_subtitle_chars": 80,
        "max_subtitle_line_chars": 42,
        "min_chars_per_minute": 10.0,
        "max_chars_per_minute": 900.0,
        "max_gap_coverage_ratio": 0.20,
        "duplicate_segment_window_seconds": 8.0,
        "min_avg_logprob_warning": -1.10,
        "min_avg_logprob_blocker": -1.50,
        "max_compression_ratio_warning": 2.40,
        "max_compression_ratio_blocker": 3.00,
        "max_no_speech_prob_warning": 0.80,
        "max_no_speech_prob_blocker": 0.92,
        "min_short_repeat_blocker_count": 8,
        "min_long_repeat_blocker_count": 4,
        "min_repeated_phrase_blocker_chars": 80,
        "min_repeated_phrase_blocker_duration": 12.0,
        "min_duplicate_segment_blocker_chars": 12,
        "min_duplicate_segment_blocker_duration": 1.5,
        "min_low_confidence_blocker_duration": 1.0,
        "min_low_confidence_blocker_chars": 4,
        "max_readable_paragraph_chars_warning": 360,
        "max_readable_paragraph_chars_blocker": 600,
        "max_readable_run_on_chars": 240,
        "min_readable_chars_for_density": 200,
        "min_readable_punctuation_per_1000_chars": 8.0,
        "repair_padding": 15.0,
        "merge_repair_gap_seconds": 2.0,
        "max_repair_window_seconds": 300.0,
    },
    "strict": {
        "max_gap": 30.0,
        "max_segment_duration": 20.0,
        "max_subtitle_chars": 64,
        "max_subtitle_line_chars": 36,
        "min_chars_per_minute": 15.0,
        "max_chars_per_minute": 720.0,
        "max_gap_coverage_ratio": 0.12,
        "duplicate_segment_window_seconds": 6.0,
        "min_avg_logprob_warning": -1.00,
        "min_avg_logprob_blocker": -1.35,
        "max_compression_ratio_warning": 2.20,
        "max_compression_ratio_blocker": 2.80,
        "max_no_speech_prob_warning": 0.75,
        "max_no_speech_prob_blocker": 0.90,
        "min_short_repeat_blocker_count": 6,
        "min_long_repeat_blocker_count": 4,
        "min_repeated_phrase_blocker_chars": 60,
        "min_repeated_phrase_blocker_duration": 8.0,
        "min_duplicate_segment_blocker_chars": 8,
        "min_duplicate_segment_blocker_duration": 1.0,
        "min_low_confidence_blocker_duration": 0.8,
        "min_low_confidence_blocker_chars": 3,
        "max_readable_paragraph_chars_warning": 300,
        "max_readable_paragraph_chars_blocker": 520,
        "max_readable_run_on_chars": 180,
        "min_readable_chars_for_density": 160,
        "min_readable_punctuation_per_1000_chars": 10.0,
        "repair_padding": 20.0,
        "merge_repair_gap_seconds": 2.0,
        "max_repair_window_seconds": 240.0,
    },
}

REPAIRABLE_BLOCKER_TYPES = {
    IssueType.LARGE_TIMING_GAP.value,
    IssueType.LONG_SEGMENT.value,
    IssueType.SEGMENT_OVERLAP.value,
    IssueType.REPEATED_PHRASE.value,
    IssueType.ADJACENT_DUPLICATE_SEGMENT.value,
    IssueType.LOW_AVG_LOGPROB_SEGMENT.value,
    IssueType.HIGH_COMPRESSION_RATIO_SEGMENT.value,
    IssueType.HIGH_NO_SPEECH_PROB_SEGMENT.value,
}
REPAIRABLE_WARNING_TYPES = {
    IssueType.REPEATED_PHRASE.value,
    IssueType.LOW_AVG_LOGPROB_SEGMENT.value,
    IssueType.HIGH_COMPRESSION_RATIO_SEGMENT.value,
    IssueType.HIGH_NO_SPEECH_PROB_SEGMENT.value,
    IssueType.ADJACENT_DUPLICATE_SEGMENT.value,
}


def load_qa_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"QA config does not exist: {p}")
    payload = read_json(p)
    if not isinstance(payload, dict):
        raise ValueError(f"QA config must be a JSON object: {p}")
    return payload


def _profile_from_config(config: dict[str, Any], requested: str | None) -> str:
    value = requested or config.get("profile") or DEFAULT_QA_PROFILE
    profile = str(value)
    if profile not in QA_PROFILES:
        raise ValueError(
            f"Unknown QA profile `{profile}`. Choose one of: {', '.join(sorted(QA_PROFILES))}"
        )
    return profile


def _config_settings(config: dict[str, Any], profile: str) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    profiles = config.get("profiles")
    if isinstance(profiles, dict):
        profile_settings = profiles.get(profile)
        if isinstance(profile_settings, dict):
            settings.update(profile_settings)
    checks = config.get("checks")
    if isinstance(checks, dict):
        settings.update(checks)
    # Allow small one-off JSON files to contain settings directly.
    for key, value in config.items():
        if key in {"profile", "profiles", "checks"}:
            continue
        if key in QA_PROFILES[profile]:
            settings[key] = value
    return settings


def resolve_qa_settings(
    *,
    profile: str | None = None,
    config_file: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_qa_config(config_file)
    resolved_profile = _profile_from_config(config, profile)
    settings = deepcopy(QA_PROFILES[resolved_profile])
    settings.update(_config_settings(config, resolved_profile))
    for key, value in (overrides or {}).items():
        if value is not None:
            settings[key] = value
    settings["profile"] = resolved_profile
    settings["repairable_blocker_types"] = sorted(REPAIRABLE_BLOCKER_TYPES)
    settings["repairable_warning_types"] = sorted(REPAIRABLE_WARNING_TYPES)
    return settings
