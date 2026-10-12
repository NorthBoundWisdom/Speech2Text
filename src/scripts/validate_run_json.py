#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from atot.validators import read_json_file, validate_run_json_payload

__all__ = ["validate_run_json_file", "validate_run_json_payload"]


def validate_run_json_file(path: Path) -> list[str]:
    try:
        payload = read_json_file(path)
    except Exception as exc:
        return [f"failed to read JSON: {exc}"]
    return validate_run_json_payload(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate SonaFolio work/run.json schema invariants."
    )
    parser.add_argument("run_json", nargs="+", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    failed = False
    for path in args.run_json:
        errors = validate_run_json_file(path)
        if errors:
            failed = True
            print(f"{path}: failed", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{path}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
