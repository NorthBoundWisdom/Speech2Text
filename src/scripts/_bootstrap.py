from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_on_path() -> None:
    src_root = Path(__file__).resolve().parents[1]
    text = str(src_root)
    if text not in sys.path:
        sys.path.insert(0, text)
