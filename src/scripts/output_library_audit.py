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

from atot.output_audit import OutputAuditOptions, audit_markdown, audit_outputs
from atot.paths import DEFAULT_OUTPUT_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize historical Audio2Text output quality across the local library."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--report", type=Path, default=None, help="Write markdown or JSON report to this path."
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum rows to render in markdown output."
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audit = audit_outputs(
        OutputAuditOptions(
            output_root=args.output_root,
            output_path=args.report,
            limit=max(1, args.limit) if args.limit else None,
        )
    )
    if args.json_output:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(
            audit_markdown(
                audit["rows"], audit["summary"], limit=max(1, args.limit) if args.limit else None
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
