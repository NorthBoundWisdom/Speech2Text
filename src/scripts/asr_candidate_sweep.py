#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.candidate.paths import discover_process_audios
from atot.candidate.presets import local_preset_names
from atot.candidate.sweep import SweepOptions, default_sweep_output_dir, run_sweep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a parallel same-audio sweep across vetted local ASR candidates."
    )
    parser.add_argument(
        "audio",
        nargs="*",
        type=Path,
        help="Audio files. Defaults to discovered process source audio.",
    )
    parser.add_argument(
        "--preset",
        action="append",
        dest="presets",
        help="Candidate preset to include. Defaults to all local mlx-whisper presets.",
    )
    parser.add_argument(
        "--process-dir",
        type=Path,
        default=None,
        help="Process tree used when audio files are omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Sweep output directory. Defaults to output/benchmark/asr_candidate_sweep/<timestamp>/",
    )
    parser.add_argument(
        "--model",
        default="large-v3-turbo",
        help="Baseline model used if a fresh baseline run is needed.",
    )
    parser.add_argument("--candidate-timeout", type=float, default=1800.0)
    parser.add_argument(
        "--jobs", type=int, default=3, help="Maximum parallel candidate comparisons."
    )
    parser.add_argument("--min-audio-count", type=int, default=1)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audios = [path.expanduser().resolve() for path in args.audio]
    if not audios:
        audios = discover_process_audios(args.process_dir)
    if not audios:
        raise SystemExit("No process source audio files found.")
    presets = tuple(args.presets or local_preset_names())
    if not presets:
        raise SystemExit("No candidate presets selected.")
    output_dir = (
        args.output_dir.expanduser().resolve() if args.output_dir else default_sweep_output_dir()
    )
    summary = run_sweep(
        SweepOptions(
            presets=presets,
            audios=tuple(audios),
            output_dir=output_dir,
            model=args.model,
            candidate_timeout=args.candidate_timeout,
            jobs=max(1, args.jobs),
            min_audio_count=max(1, args.min_audio_count),
        )
    )
    if args.json_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Sweep output: {summary['output_dir']}")
        print(f"Matrix: {summary['matrix_path']}")
        print(f"Failed tasks: {summary['failed_task_count']}/{summary['task_count']}")
    return 0 if summary.get("failed_task_count", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
