from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunJsonContract:
    required_top_level: frozenset[str]
    required_status_keys: frozenset[str]
    required_output_files: frozenset[str]
    required_quality_keys: frozenset[str]
    required_timing_keys: frozenset[str]


@dataclass(frozen=True)
class CloudBundleContract:
    media_suffixes: frozenset[str]
    text_suffixes: frozenset[str]
    local_only_names: frozenset[str]
    required_input_files: frozenset[str]


RUN_JSON_CONTRACT = RunJsonContract(
    required_top_level=frozenset(
        {
            "success",
            "created_at",
            "input_path",
            "input_file",
            "prepared_audio",
            "job_dir",
            "backend",
            "backend_capabilities",
            "transcription_fingerprint",
            "transcription_fingerprint_sha256",
            "postprocess_fingerprint",
            "postprocess_fingerprint_sha256",
            "chunk_layout",
            "chunk_layout_sha256",
            "model",
            "model_source",
            "model_alias_or_input",
            "language",
            "audio_duration",
            "chunk_length",
            "overlap",
            "runtime_seconds",
            "chunk_runtime_seconds",
            "speed_factor",
            "chunk_status_counts",
            "peak_rss_mb",
            "machine_info",
            "chunks",
            "review",
            "qa",
            "repair",
            "cloud",
            "quality_metrics",
            "output_files",
        }
    ),
    required_status_keys=frozenset(
        {"transcribed", "transcribed_after_cache_mismatch", "skipped_existing"}
    ),
    required_output_files=frozenset(
        {
            "transcript.readable.md",
            "raw.json",
            "corrected.json",
            "transcript.raw.txt",
            "transcript.corrected.txt",
            "transcript.md",
            "transcript.timestamped.md",
            "transcript.srt",
            "transcript.vtt",
            "corrections.json",
            "chunks_manifest.json",
            "prepared.wav",
            "prepared.meta.json",
            "qa.json",
            "qa.md",
            "review.json",
            "review.md",
            "run.json",
            "run.log",
            "glossary.effective.json",
        }
    ),
    required_quality_keys=frozenset(
        {
            "raw_segment_count",
            "corrected_segment_count",
            "empty_corrected_segment_count",
            "raw_char_count",
            "corrected_char_count",
            "correction_count",
            "correction_kind_counts",
            "review_issue_count",
            "review_segment_issue_count",
            "token_count",
            "max_repeated_token_run",
            "top_token_ratio",
            "timing",
        }
    ),
    required_timing_keys=frozenset(
        {
            "timed_segment_count",
            "missing_timing_segment_count",
            "invalid_timing_segment_count",
            "non_monotonic_timing_segment_count",
            "overlapping_timing_segment_count",
            "max_timing_overlap_seconds",
            "srt_vtt_compatible",
        }
    ),
)

CLOUD_BUNDLE_CONTRACT = CloudBundleContract(
    media_suffixes=frozenset(
        {
            ".aac",
            ".aiff",
            ".avi",
            ".flac",
            ".m4a",
            ".m4v",
            ".mkv",
            ".mov",
            ".mp3",
            ".mp4",
            ".mpeg",
            ".mpg",
            ".ogg",
            ".opus",
            ".wav",
            ".webm",
        }
    ),
    text_suffixes=frozenset({".json", ".md", ".txt"}),
    local_only_names=frozenset({"redaction_map.local.json"}),
    required_input_files=frozenset(
        {
            "manifest.json",
            "transcript.for_cloud.md",
            "segments.for_cloud.json",
            "qa.for_cloud.json",
            "qa.for_cloud.md",
            "glossary.for_cloud.json",
            "run_summary.json",
        }
    ),
)
