#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from atot.validators import validate_cloud_input, validate_cloud_outputs, validate_cloud_package

__all__ = ["validate_cloud_input", "validate_cloud_outputs", "validate_cloud_package"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SonaFolio cloud text-only package manifests.")
    parser.add_argument(
        "path", type=Path, help="Output directory, cloud directory, or cloud input directory."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "input", "outputs", "both"),
        default="auto",
        help="Which cloud package manifest to validate.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_cloud_package(args.path, mode=args.mode)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{args.path}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
