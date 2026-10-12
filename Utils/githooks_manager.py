#!/usr/bin/env python3
"""Manage repository Git hooks and hook behavior.

Usage examples:
  python3 Utils/githooks_manager.py install
  python3 Utils/githooks_manager.py status
  python3 Utils/githooks_manager.py config --build-gate on
  python3 Utils/githooks_manager.py reset
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Iterable

HOOKS_DIR = "configs/githooks"
HOOK_FILES = ("pre-commit",)
PREFIX = "audio2text.hooks"

BOOL_KEYS = {
    "build_gate": f"{PREFIX}.enableBuildGate",
    "logic_tests": f"{PREFIX}.runLogicTests",
}

STRING_KEYS = {
    "mac_scheme": f"{PREFIX}.macScheme",
    "ios_scheme": f"{PREFIX}.iosScheme",
    "build_configuration": f"{PREFIX}.buildConfiguration",
}

DEFAULTS = {
    BOOL_KEYS["build_gate"]: "true",
    BOOL_KEYS["logic_tests"]: "false",
    STRING_KEYS["mac_scheme"]: "Audio2TextApp",
    STRING_KEYS["ios_scheme"]: "Audio2Text-iOS",
    STRING_KEYS["build_configuration"]: "Debug",
}

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
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


def warn(message: str) -> None:
    print(f"{colorize('[warn]', YELLOW)} {message}")


def fail(message: str) -> None:
    print(f"{colorize('[error]', RED)} {message}", file=sys.stderr)


def run_git(
    repo_root: Path, args: Iterable[str], capture: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=capture,
        check=False,
    )


def get_repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or "not inside a git repository"
        raise RuntimeError(detail)
    return Path(proc.stdout.strip())


def ensure_hook_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def git_get(repo_root: Path, key: str) -> str | None:
    proc = run_git(repo_root, ["config", "--local", "--get", key])
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def git_set(repo_root: Path, key: str, value: str) -> None:
    proc = run_git(repo_root, ["config", "--local", key, value], capture=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to set git config: {key}={value}")


def git_unset(repo_root: Path, key: str) -> None:
    proc = run_git(repo_root, ["config", "--local", "--unset", key], capture=False)
    if proc.returncode not in (0, 5):
        raise RuntimeError(f"failed to unset git config: {key}")


def cmd_install(repo_root: Path) -> int:
    hooks_dir = repo_root / HOOKS_DIR
    if not hooks_dir.is_dir():
        fail(f"hooks directory not found: {hooks_dir}")
        return 1

    missing = [name for name in HOOK_FILES if not (hooks_dir / name).is_file()]
    if missing:
        fail(f"missing hook files: {', '.join(missing)}")
        return 1

    for hook_name in HOOK_FILES:
        hook_path = hooks_dir / hook_name
        ensure_hook_executable(hook_path)
        ok(f"prepared executable hook: {hook_path}")

    git_set(repo_root, "core.hooksPath", HOOKS_DIR)
    ok(f"configured core.hooksPath={HOOKS_DIR}")
    info("Run `python3 Utils/githooks_manager.py status` to check effective behavior.")
    return 0


def parse_on_off(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"on", "off"}:
        raise ValueError(f"invalid value: {value}, expected on/off")
    return "true" if normalized == "on" else "false"


def set_behavior_values(repo_root: Path, args: argparse.Namespace) -> int:
    changes: list[tuple[str, str]] = []

    if args.build_gate is not None:
        changes.append((BOOL_KEYS["build_gate"], parse_on_off(args.build_gate)))
    if args.logic_tests is not None:
        changes.append((BOOL_KEYS["logic_tests"], parse_on_off(args.logic_tests)))
    if args.mac_scheme is not None:
        changes.append((STRING_KEYS["mac_scheme"], args.mac_scheme))
    if args.ios_scheme is not None:
        changes.append((STRING_KEYS["ios_scheme"], args.ios_scheme))
    if args.build_configuration is not None:
        changes.append((STRING_KEYS["build_configuration"], args.build_configuration))

    if args.clear_build_overrides:
        changes.extend(
            [
                (STRING_KEYS["mac_scheme"], DEFAULTS[STRING_KEYS["mac_scheme"]]),
                (STRING_KEYS["ios_scheme"], DEFAULTS[STRING_KEYS["ios_scheme"]]),
                (
                    STRING_KEYS["build_configuration"],
                    DEFAULTS[STRING_KEYS["build_configuration"]],
                ),
            ]
        )

    if not changes:
        warn("no config changes provided")
        return 0

    for key, value in changes:
        git_set(repo_root, key, value)
        ok(f"set {key}={value}")
    return 0


def print_status(repo_root: Path) -> None:
    print(colorize("Git Hook Status", CYAN))
    info(f"repo: {repo_root}")

    hooks_path = git_get(repo_root, "core.hooksPath")
    hooks_path = hooks_path or ".git/hooks (default)"
    info(f"core.hooksPath: {hooks_path}")

    hooks_dir = repo_root / HOOKS_DIR
    for hook_name in HOOK_FILES:
        hook = hooks_dir / hook_name
        if not hook.exists():
            fail(f"missing hook file: {hook}")
            continue
        executable = os.access(hook, os.X_OK)
        marker = "x" if executable else "-"
        info(f"hook {hook_name}: present ({marker})")

    info("")
    print(colorize("Effective Hook Behavior", CYAN))
    for key in (
        BOOL_KEYS["build_gate"],
        BOOL_KEYS["logic_tests"],
        STRING_KEYS["mac_scheme"],
        STRING_KEYS["ios_scheme"],
        STRING_KEYS["build_configuration"],
    ):
        local_value = git_get(repo_root, key)
        value = local_value if local_value is not None else DEFAULTS[key]
        source = "local" if local_value is not None else "default"
        info(f"{key}: {value} ({source})")


def cmd_reset(repo_root: Path) -> int:
    for key in (*BOOL_KEYS.values(), *STRING_KEYS.values()):
        git_unset(repo_root, key)
    git_unset(repo_root, "core.hooksPath")
    ok("removed Audio2Text hook config and reset core.hooksPath")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Install tracked repository hooks.")
    subparsers.add_parser("status", help="Print local hook status and defaults.")
    subparsers.add_parser("reset", help="Unset hook config and restore default Git hooks.")

    config = subparsers.add_parser("config", help="Change local hook behavior.")
    config.add_argument("--build-gate", choices=("on", "off"))
    config.add_argument("--logic-tests", choices=("on", "off"))
    config.add_argument("--mac-scheme")
    config.add_argument("--ios-scheme")
    config.add_argument("--build-configuration")
    config.add_argument(
        "--clear-build-overrides",
        action="store_true",
        help="Reset schemes and configuration to repository defaults.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        repo_root = get_repo_root()
        if args.command == "install":
            return cmd_install(repo_root)
        if args.command == "status":
            print_status(repo_root)
            return 0
        if args.command == "config":
            return set_behavior_values(repo_root, args)
        if args.command == "reset":
            return cmd_reset(repo_root)
    except (RuntimeError, ValueError) as error:
        fail(str(error))
        return 1
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
