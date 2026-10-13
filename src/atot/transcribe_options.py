from __future__ import annotations

from pathlib import Path
import sys
from collections.abc import Callable
from typing import Any

from .config import load_app_config
from .languages import normalize_language_hint
from .numeric import as_int
from .paths import path_context
from .pipeline import TranscribeOptions
from .platform_defaults import default_asr_backend
from .runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
    DEFAULT_SAMPLE_RATE,
)


def transcribe_options_from_values(
    values: Any,
    *,
    input_path: Path,
    output_dir: Path | None = None,
    name: str | None = None,
    force_all: bool = False,
) -> TranscribeOptions:
    force = bool(getattr(values, "force", False)) if force_all else False
    ctx = path_context()
    config = load_app_config(include_api_key=False)
    return TranscribeOptions(
        input_path=input_path,
        output_dir=output_dir or ctx.output_dir,
        job_dir=getattr(values, "job_dir", None),
        name=name,
        backend=getattr(values, "backend", default_asr_backend()),
        recording_json=getattr(values, "recording_json", None),
        model=config.local.asr_model,
        language=normalize_language_hint(getattr(values, "language", "auto")),
        prompt_file=values.prompt_file if getattr(values, "prompt_file", None) else None,
        glossary_file=values.glossary_file if getattr(values, "glossary_file", None) else None,
        rule_packs=tuple(getattr(values, "rule_pack", None) or ()) or None,
        chunk_length=values.chunk_length,
        chunking=getattr(values, "chunking", "auto"),
        max_chunk_length=getattr(values, "max_chunk_length", None),
        silence_threshold=getattr(values, "silence_threshold", None),
        min_silence=getattr(values, "min_silence", 0.5),
        overlap=values.overlap,
        local_only=getattr(values, "local_only", False),
        sample_rate=getattr(values, "sample_rate", DEFAULT_SAMPLE_RATE),
        force_prepare=getattr(values, "force_prepare", False) or force,
        force_chunks=getattr(values, "force_chunks", False) or force,
        force_transcribe=getattr(values, "force_transcribe", False) or force,
        word_timestamps=values.word_timestamps,
        verbose=True if values.verbose else False,
        condition_on_previous_text=getattr(values, "condition_on_previous_text", True),
        temperature=getattr(values, "temperature", 0.0),
        no_speech_threshold=getattr(values, "no_speech_threshold", DEFAULT_NO_SPEECH_THRESHOLD),
        logprob_threshold=getattr(values, "logprob_threshold", DEFAULT_LOGPROB_THRESHOLD),
        compression_ratio_threshold=getattr(
            values, "compression_ratio_threshold", DEFAULT_COMPRESSION_RATIO_THRESHOLD
        ),
        hallucination_silence_threshold=getattr(values, "hallucination_silence_threshold", None),
        profile=config.local.asr_profile,
        progress_callback=_cli_progress_callback(enabled=not getattr(values, "json_output", False)),
    )


def _cli_progress_callback(*, enabled: bool) -> Callable[[dict[str, Any]], None] | None:
    if not enabled:
        return None

    def emit(event: dict[str, Any]) -> None:
        if event.get("event") == "stage":
            stage = event.get("stage")
            if stage in {"start", "prepare_audio", "chunking", "postprocess", "qa", "complete"}:
                # User-facing CLI progress goes to stderr so stdout remains machine-readable.
                print(f"Local: {stage}", file=sys.stderr)
            return
        if event.get("event") == "chunk":
            status = str(event.get("status") or "")
            if status == "started":
                return
            total = as_int(event.get("total_chunks")) or 0
            chunk = (as_int(event.get("chunk")) or 0) + 1
            # User-facing CLI progress goes to stderr so stdout remains machine-readable.
            print(f"Local chunks: {chunk}/{total} {status}", file=sys.stderr)

    return emit
