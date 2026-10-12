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

from atot.backends import ASRTranscribeOptions, MlxWhisperBackend
from atot.utils import write_json_atomic


def _noneable_float(value: str) -> float | None:
    if value.lower() in {"none", "null", "off", "false"}:
        return None
    return float(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run mlx-whisper as an external ASR candidate.")
    parser.add_argument("audio", type=Path)
    parser.add_argument(
        "--model", required=True, help="HF model id or local mlx-whisper model directory."
    )
    parser.add_argument("--language", default="zh")
    parser.add_argument("--context", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stdout-only", action="store_true")
    parser.add_argument("--word-timestamps", action="store_true")
    parser.add_argument(
        "--condition-on-previous-text",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass previous decoded text as prompt within each chunk.",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--no-speech-threshold", type=_noneable_float, default=0.6)
    parser.add_argument("--logprob-threshold", type=_noneable_float, default=-1.0)
    parser.add_argument("--compression-ratio-threshold", type=_noneable_float, default=2.4)
    parser.add_argument("--hallucination-silence-threshold", type=_noneable_float, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backend = MlxWhisperBackend(verbose=False)
    result = backend.transcribe(
        args.audio,
        ASRTranscribeOptions(
            model=args.model,
            language=args.language,
            prompt=args.context or None,
            word_timestamps=args.word_timestamps,
            condition_on_previous_text=args.condition_on_previous_text,
            temperature=args.temperature,
            no_speech_threshold=args.no_speech_threshold,
            logprob_threshold=args.logprob_threshold,
            compression_ratio_threshold=args.compression_ratio_threshold,
            hallucination_silence_threshold=args.hallucination_silence_threshold,
        ),
    )
    payload = {
        "text": result.get("text", ""),
        "segments": result.get("segments", []),
        "runtime_seconds": result.get("runtime_seconds"),
        "model": args.model,
        "language": args.language,
        "decode_options": {
            "condition_on_previous_text": args.condition_on_previous_text,
            "temperature": args.temperature,
            "no_speech_threshold": args.no_speech_threshold,
            "logprob_threshold": args.logprob_threshold,
            "compression_ratio_threshold": args.compression_ratio_threshold,
            "hallucination_silence_threshold": args.hallucination_silence_threshold,
            "word_timestamps": args.word_timestamps,
        },
    }
    if args.output:
        write_json_atomic(args.output, payload)
    if args.stdout_only or not args.output:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
