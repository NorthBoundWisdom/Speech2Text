#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.candidate.presets import (
    DEFAULT_TIMEOUT_SECONDS,
    CandidatePreset,
    HfFileRequirement,
    LocalPathRequirement,
    MODEL_DIR,
    TOOLS_DIR,
    ENV_DIR,
    _compare_command,
    _gate_command,
    build_parser,
    main,
    presets,
)

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "CandidatePreset",
    "ENV_DIR",
    "HfFileRequirement",
    "LocalPathRequirement",
    "MODEL_DIR",
    "TOOLS_DIR",
    "_compare_command",
    "_gate_command",
    "build_parser",
    "main",
    "presets",
]


if __name__ == "__main__":
    raise SystemExit(main())
