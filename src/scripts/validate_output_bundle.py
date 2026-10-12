#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from atot.validators import REQUIRED_OUTPUT_FILES
from atot.validators import validate_output_bundle as _validate_output_bundle

REQUIRED_FILES = REQUIRED_OUTPUT_FILES

__all__ = ["REQUIRED_FILES", "REQUIRED_OUTPUT_FILES", "validate_output_bundle"]


def validate_output_bundle(output_dir: Path) -> list[str]:
    return _validate_output_bundle(output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate an SonaFolio local transcription output bundle."
    )
    parser.add_argument("output_dir", type=Path, help="Transcription output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_output_bundle(args.output_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{args.output_dir}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
