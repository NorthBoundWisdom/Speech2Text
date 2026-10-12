#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.candidate.metrics import (
    MAX_ABSOLUTE_TOP_TOKEN_RATIO,
    MAX_CANDIDATE_CHAR_RATIO,
    MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER,
    MIN_CANDIDATE_CHAR_RATIO,
    coerce_optional_float as _coerce_optional_float,
    comparison_payload as _comparison_payload,
    format_float as _format_float,
    guardrail_failures as _guardrail_failures,
    summary_metrics as _summary_metrics,
)
from atot.candidate.outputs import (
    comparison_markdown as _comparison_markdown,
    write_candidate_outputs as _write_candidate_outputs,
)
from atot.candidate.paths import (
    AUDIO_SUFFIXES,
    baseline_job_name as _baseline_job_name,
    candidate_output_dir as _candidate_output_dir,
    format_template as _format_template,
    glossary_terms as _glossary_terms,
    is_top_level_process_source_audio as _is_top_level_process_source_audio,
    official_process_run_json as _official_process_run_json,
)
from atot.candidate.payload import (
    extract_candidate_segments as _extract_candidate_segments,
    extract_candidate_text as _extract_candidate_text,
    load_candidate_payload as _load_candidate_payload,
    payload_segments as _payload_segments,
    payload_text as _payload_text,
    segment_from_item as _segment_from_item,
)
from atot.candidate.process import (
    COMMAND_NOT_FOUND_RETURN_CODE,
    MEMORY_POLL_INTERVAL_SECONDS,
    TIMEOUT_RETURN_CODE,
    child_pids as _child_pids,
    process_tree_pids as _process_tree_pids,
    process_tree_rss_mb as _process_tree_rss_mb,
    rss_kb as _rss_kb,
    run_candidate_command as _run_candidate_command,
)
from atot.context import PromptContext, build_prompt_context
from atot.paths import DEFAULT_GLOSSARY_FILE, DEFAULT_OUTPUT_DIR, DEFAULT_PROMPT_FILE
from atot.pipeline import TranscribeOptions, run_transcription
from atot.utils import read_json, write_json_atomic, write_text_atomic
from asr_candidate_presets import presets


__all__ = [
    "AUDIO_SUFFIXES",
    "COMMAND_NOT_FOUND_RETURN_CODE",
    "MAX_ABSOLUTE_TOP_TOKEN_RATIO",
    "MAX_CANDIDATE_CHAR_RATIO",
    "MAX_RELATIVE_TOP_TOKEN_RATIO_MULTIPLIER",
    "MEMORY_POLL_INTERVAL_SECONDS",
    "MIN_CANDIDATE_CHAR_RATIO",
    "PromptContext",
    "TIMEOUT_RETURN_CODE",
    "_baseline_job_name",
    "_candidate_output_dir",
    "_child_pids",
    "_coerce_optional_float",
    "_comparison_markdown",
    "_comparison_payload",
    "_extract_candidate_segments",
    "_extract_candidate_text",
    "_format_float",
    "_format_template",
    "_glossary_terms",
    "_guardrail_failures",
    "_is_top_level_process_source_audio",
    "_load_candidate_payload",
    "_official_process_run_json",
    "_payload_segments",
    "_payload_text",
    "_process_tree_pids",
    "_process_tree_rss_mb",
    "_rss_kb",
    "_run_candidate_command",
    "_segment_from_item",
    "_summary_metrics",
    "_write_candidate_outputs",
    "read_json",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare Audio2Text baseline with an external ASR candidate command."
    )
    parser.add_argument("audio", type=Path)
    parser.add_argument(
        "--preset", choices=sorted(presets()), help="Use a vetted candidate command preset."
    )
    parser.add_argument("--candidate-name")
    parser.add_argument(
        "--candidate-command",
        help=(
            "Command template. Available placeholders: {audio}, {output}, {output_dir}, "
            "{context}, {glossary_terms}."
        ),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "benchmark" / "asr_candidates"
    )
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument(
        "--candidate-timeout",
        type=float,
        default=0.0,
        help="Seconds before killing the candidate command. 0 disables the timeout.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    selected_preset = presets().get(args.preset) if args.preset else None
    candidate_name = args.candidate_name or (selected_preset.name if selected_preset else "")
    candidate_command_template = args.candidate_command or (
        selected_preset.command if selected_preset else ""
    )
    if not candidate_name:
        parser.error("--candidate-name is required unless --preset is used")
    if not candidate_command_template:
        parser.error("--candidate-command is required unless --preset is used")

    audio = args.audio.expanduser().resolve()
    candidate_dir = _candidate_output_dir(args.output_dir, audio, candidate_name)
    candidate_command_output = candidate_dir / "candidate.command-output.txt"
    context = build_prompt_context(
        audio, prompt_file=DEFAULT_PROMPT_FILE, glossary_file=DEFAULT_GLOSSARY_FILE
    )

    baseline_run_path = _official_process_run_json(audio)
    if baseline_run_path is not None:
        baseline_run = read_json(baseline_run_path)
    else:
        baseline_run = run_transcription(
            TranscribeOptions(
                input_path=audio,
                model=args.model,
                name=_baseline_job_name(audio, candidate_name),
                prompt_file=DEFAULT_PROMPT_FILE,
                glossary_file=DEFAULT_GLOSSARY_FILE,
            )
        )
        baseline_run_path = Path(str(baseline_run.get("job_dir", ""))) / "run.json"

    command = _format_template(
        candidate_command_template,
        audio=audio,
        output=candidate_command_output,
        output_dir=candidate_dir,
        context=context.effective_prompt or "",
        glossary_terms=_glossary_terms(context.glossary),
    )
    timeout = (
        args.candidate_timeout if args.candidate_timeout and args.candidate_timeout > 0 else None
    )
    returncode, runtime_seconds, peak_rss_mb, timed_out, stdout, stderr = _run_candidate_command(
        command, timeout
    )
    candidate_text = _extract_candidate_text(stdout, candidate_command_output)
    candidate_segments = _extract_candidate_segments(stdout, candidate_command_output)
    candidate_run = _write_candidate_outputs(
        audio=audio,
        candidate_name=candidate_name,
        candidate_text=candidate_text,
        candidate_segments=candidate_segments,
        output_dir=candidate_dir,
        command=command,
        runtime_seconds=runtime_seconds,
        peak_rss_mb=peak_rss_mb,
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        context=context,
    )
    comparison_path = candidate_dir / "comparison.md"
    comparison_json_path = candidate_dir / "comparison.json"
    write_text_atomic(
        comparison_path,
        _comparison_markdown(audio=audio, baseline_run=baseline_run, candidate_run=candidate_run),
    )
    write_json_atomic(
        comparison_json_path,
        _comparison_payload(audio=audio, baseline_run=baseline_run, candidate_run=candidate_run),
    )
    print(f"Baseline run: {baseline_run_path}")
    print(f"Candidate run: {candidate_run['output_files']['run']}")
    print(f"Comparison: {comparison_path}")
    print(f"Comparison JSON: {comparison_json_path}")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
