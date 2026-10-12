from __future__ import annotations

import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str | Path | None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8").strip()
    return text or None


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: str | Path, data: Any, *, indent: int = 2) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name, suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(json_safe(data), f, ensure_ascii=False, indent=indent)
            f.write("\n")
        Path(tmp_name).replace(target)
    finally:
        tmp = Path(tmp_name)
        if tmp.exists():
            tmp.unlink()
    return target


def write_text_atomic(path: str | Path, text: str) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name, suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            if text and not text.endswith("\n"):
                f.write("\n")
        Path(tmp_name).replace(target)
    finally:
        tmp = Path(tmp_name)
        if tmp.exists():
            tmp.unlink()
    return target


def slugify(value: str, *, max_len: int = 80) -> str:
    """Keep CJK characters, ASCII letters/numbers, and a few path-safe delimiters."""
    value = value.strip().replace("/", "-").replace(":", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^0-9A-Za-z_\-.\u4e00-\u9fff\u3400-\u4dbf]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return (value or "audio")[:max_len]


def seconds_to_hms(seconds: float) -> str:
    if seconds is None or math.isnan(float(seconds)):
        seconds = 0
    seconds = max(0.0, float(seconds))
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def seconds_to_srt_ts(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def seconds_to_vtt_ts(seconds: float) -> str:
    return seconds_to_srt_ts(seconds).replace(",", ".")


def compact_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def relative_posix_path(path: str | Path, base: str | Path) -> str:
    return Path(path).relative_to(Path(base)).as_posix()


def json_safe(obj: Any) -> Any:
    """Convert common numpy/MLX scalar objects into JSON-serializable values."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [json_safe(x) for x in obj]
    if hasattr(obj, "tolist"):
        try:
            return obj.tolist()
        except Exception:
            pass
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    return str(obj)


def valid_json_file(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        payload = read_json(p)
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("success") is True
