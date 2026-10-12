#!/usr/bin/env python3
"""One-shot hook installer for the repository."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"


def supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


COLOR_ENABLED = supports_color()


def colorize(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{color}{text}{RESET}"


def info(message: str) -> None:
    print(message)


def ok(message: str) -> None:
    print(f"{colorize('[ok]', GREEN)} {message}")


def fail(message: str) -> None:
    print(f"{colorize('[error]', RED)} {message}", file=sys.stderr)


def run(cmd: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_git_repo(repo_root: Path) -> None:
    try:
        run(["git", "rev-parse", "--git-dir"], cwd=repo_root)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "current directory is not a git repository"
        raise RuntimeError(detail) from error


def find_python() -> list[str]:
    for candidate in ("python3", "python"):
        completed = subprocess.run(
            [candidate, "--version"], text=True, capture_output=True, check=False
        )
        if completed.returncode == 0:
            return [candidate]
    raise RuntimeError("python3/python is required.")


def main() -> int:
    if len(sys.argv) > 1:
        fail("configs/installhooks.py does not accept command-line arguments.")
        info("Use: python3 configs/installhooks.py")
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    python_cmd = find_python()

    print(colorize("Installing Audio2Text hooks...", CYAN))
    try:
        ensure_git_repo(repo_root)
        manager_script = repo_root / "Utils" / "githooks_manager.py"
        if not manager_script.is_file():
            raise RuntimeError(f"missing hook manager: {manager_script}")

        completed = run([*python_cmd, str(manager_script), "install"], cwd=repo_root)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)

        info(
            "[installhooks] The pre-commit hook now builds both macOS and "
            "iOS/iPad simulator targets before commit."
        )
        ok("Hooks are installed.")
        return 0
    except RuntimeError as error:
        fail(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
