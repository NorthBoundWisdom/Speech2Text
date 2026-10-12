#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.candidate.matrix import build_matrix_markdown
from atot.paths import DEFAULT_OUTPUT_DIR
from atot.utils import slugify, write_text_atomic

__all__ = ["build_matrix_markdown", "build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a cross-candidate matrix from ASR gate comparison.json files."
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "benchmark" / "asr_candidate_gate" / "runs",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("doc/experiments/asr_candidate_gate_matrix.md")
    )
    parser.add_argument(
        "--candidate",
        action="append",
        help="Candidate name to include. Defaults to all candidates.",
    )
    parser.add_argument("--min-audio-count", type=int, default=3)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidates = {slugify(item, max_len=80) for item in args.candidate} if args.candidate else None
    report = build_matrix_markdown(
        runs_dir=args.runs_dir,
        candidates=candidates,
        min_audio_count=args.min_audio_count,
    )
    write_text_atomic(args.output, report)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
