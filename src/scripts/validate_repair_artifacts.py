#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from atot.validators import validate_repair_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AtoT repair audit artifacts.")
    parser.add_argument("path", type=Path, help="Output directory or output/repair directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_repair_artifacts(args.path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{args.path}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
