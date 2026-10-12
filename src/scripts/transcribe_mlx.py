#!/usr/bin/env python3
"""Compatibility baseline script for the initial SonaFolio MLX Whisper experiment.

The main repo CLI is `atot exec transcribe`, but this script preserves the command
shape from the earlier demo folder. Prefer `atot exec transcribe` for new work.

    python src/scripts/transcribe_mlx.py path/to/sample.wav \
      --model mlx-community/whisper-large-v3-turbo \
      --language zh \
      --output-dir out \
      --output-name sample_large_v3_turbo
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from atot.corrections import apply_corrections, load_glossary, make_prompt
from atot.models import resolve_model
from atot.utils import read_text, write_json_atomic, write_text_atomic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", default="mlx-community/whisper-small-mlx-4bit")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--output-dir", type=Path, default=Path("out"))
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--prompt-file", type=Path, default=None)
    parser.add_argument("--glossary-file", type=Path, default=None)
    parser.add_argument("--word-timestamps", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        import mlx_whisper  # type: ignore
    except Exception as exc:
        raise SystemExit("Could not import mlx_whisper. Run `pip install mlx-whisper`.") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or args.audio.stem
    prompt = make_prompt(read_text(args.prompt_file), load_glossary(args.glossary_file))

    started = time.perf_counter()
    result: dict[str, Any] = mlx_whisper.transcribe(
        str(args.audio),
        path_or_hf_repo=resolve_model(args.model),
        language=args.language or None,
        initial_prompt=prompt,
        word_timestamps=args.word_timestamps,
        verbose=True if args.verbose else False,
        temperature=0.0,
    )
    runtime = time.perf_counter() - started
    raw_text = str(result.get("text", ""))
    corrected = apply_corrections(raw_text, load_glossary(args.glossary_file))

    write_json_atomic(
        args.output_dir / f"{output_name}.json", {"runtime_seconds": runtime, "result": result}
    )
    write_text_atomic(args.output_dir / f"{output_name}.raw.txt", raw_text)
    write_text_atomic(args.output_dir / f"{output_name}.corrected.txt", corrected.text)
    write_json_atomic(args.output_dir / f"{output_name}.corrections.json", corrected.report)
    print(
        json.dumps(
            {
                "output": str(args.output_dir),
                "output_name": output_name,
                "runtime_seconds": runtime,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
