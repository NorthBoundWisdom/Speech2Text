from __future__ import annotations

import os
import platform
import subprocess
import sys
from importlib import metadata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audio import optional_command

try:
    import resource
except ModuleNotFoundError:  # pragma: no cover - Windows has no resource module.
    resource = None  # type: ignore[assignment]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sysctl_value(key: str) -> str | None:
    try:
        result = subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def machine_info() -> dict[str, Any]:
    memsize = _sysctl_value("hw.memsize")
    memory_gb = round(int(memsize) / (1024**3), 2) if memsize and memsize.isdigit() else None
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version.replace("\n", " "),
        "cpu_brand": _sysctl_value("machdep.cpu.brand_string"),
        "memory_gb": memory_gb,
        "cwd": str(Path.cwd()),
        "pid": os.getpid(),
    }


def _package_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def _command_version(command: str) -> str | None:
    executable = optional_command(command)
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "-version"], capture_output=True, text=True, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    first_line = (result.stdout or result.stderr).splitlines()
    return first_line[0].strip() if first_line else None


def runtime_info() -> dict[str, Any]:
    packages = {
        name: _package_version(name)
        for name in (
            "mlx-whisper",
            "mlx",
            "faster-whisper",
            "ctranslate2",
            "numpy",
            "huggingface_hub",
            "feedparser",
            "httpx",
        )
    }
    return {
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "package_versions": packages,
        "ffmpeg_version": _command_version("ffmpeg"),
        "git_commit": _git_commit(),
    }


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def peak_rss_mb() -> float | None:
    if resource is None:
        return None
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (OSError, ValueError):
        return None
    # Darwin returns bytes; Linux returns KiB. Use a simple platform split.
    if platform.system() == "Darwin":
        return round(rss / (1024**2), 2)
    return round(rss / 1024, 2)
