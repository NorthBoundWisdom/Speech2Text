#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
LOCAL_SECRET_FILES = frozenset({"app/cloud.local.json", "config.toml", ".codex/config.toml"})
API_KEY_LIKE_PATTERNS = (
    ("API-key-like secret", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
    ("credential assignment", re.compile(
        r'''(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)["']?\s*[=:]\s*["']([A-Za-z0-9_+/=-]{24,})["']'''
    )),
)


@dataclass(frozen=True)
class PrivatePathHit:
    path: Path
    line_number: int
    label: str
    text: str = "<redacted>"


def _private_patterns() -> tuple[re.Pattern[str], ...]:
    return (
        re.compile("/" + r"Users/([^/\s\"'<>]+)(?:/|(?=$|[\s\"']))"),
        re.compile("/" + r"home/([^/\s\"'<>]+)(?:/|(?=$|[\s\"']))"),
        re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+([^\\/\s\"'<>]+)(?:[\\/]+|(?=$|[\s\"']))"),
    )


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout


def _repository_cached_files(root: Path) -> list[Path]:
    return [root / value.decode("utf-8") for value in _git(root, "ls-files", "--cached", "-z").split(b"\0") if value]


def _repository_untracked_files(root: Path) -> list[Path]:
    return [root / value.decode("utf-8") for value in _git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if value]


def _local_secret_file_hit(path: Path, *, root: Path) -> PrivatePathHit | None:
    rel = path.relative_to(root).as_posix()
    local_env = (path.name == ".env" or path.name.startswith(".env.")) and path.name not in {".env.example", ".env.template"}
    if rel in LOCAL_SECRET_FILES or local_env:
        return PrivatePathHit(path, 1, "local secret config file")
    return None


def _read_worktree_text(path: Path) -> str | None:
    if path.is_symlink():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return None


def _read_staged_text(path: Path, *, root: Path, revision: str = "") -> str | None:
    try:
        return _git(root, "show", f"{revision}:{path.relative_to(root).as_posix()}").decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return None


def find_private_path_hits(
    files: Iterable[Path], *, root: Path = ROOT,
    text_loader: Callable[[Path], str | None] | None = None,
) -> list[PrivatePathHit]:
    hits: list[PrivatePathHit] = []
    for path in files:
        if text_loader is None and not path.is_file():
            continue
        if file_hit := _local_secret_file_hit(path, root=root):
            hits.append(file_hit)
        content = text_loader(path) if text_loader else _read_worktree_text(path)
        if content is None:
            continue
        rel = path.relative_to(root).as_posix().lower()
        test_source = any(part in {"tests", "test", "fixtures"} for part in Path(rel).parts)
        for number, line in enumerate(content.splitlines(), 1):
            for pattern in _private_patterns():
                for match in pattern.finditer(line):
                    # Only explicit synthetic fixture users are allowed in test source.
                    if test_source and match[1].lower() in {"dev", "me", "test", "testuser", "example", "user"}:
                        continue
                    if match[1] in {"USER", "$USER", "${USER}", "%USERNAME%"}:
                        continue
                    hits.append(PrivatePathHit(path, number, "private absolute path"))
            for label, pattern in API_KEY_LIKE_PATTERNS:
                if pattern.search(line):
                    if label == "credential assignment" and any(other.search(line) for _, other in API_KEY_LIKE_PATTERNS[:-1]):
                        continue
                    hits.append(PrivatePathHit(path, number, label))
    return hits


def find_repository_private_path_hits(*, root: Path = ROOT, scope: str = "both") -> list[PrivatePathHit]:
    if scope not in {"staged", "worktree", "both"}:
        raise ValueError("Unknown scan scope.")
    cached = _repository_cached_files(root)
    hits: list[PrivatePathHit] = []
    if scope in {"staged", "both"}:
        hits += find_private_path_hits(cached, root=root, text_loader=lambda path: _read_staged_text(path, root=root))
    if scope in {"worktree", "both"}:
        hits += find_private_path_hits([*cached, *_repository_untracked_files(root)], root=root)
    for entry in _git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, revision, _ = metadata.split()
        if mode != b"160000":
            continue
        module = root / name.decode("utf-8")
        if not (module / ".git").exists():
            raise RuntimeError(f"Initialize the submodule before the public-source check: {name.decode()}")
        if scope in {"staged", "both"}:
            sha = revision.decode()
            files = [module / path.decode() for path in _git(module, "ls-tree", "-r", "--name-only", "-z", sha).split(b"\0") if path]
            hits += find_private_path_hits(files, root=module, text_loader=lambda path: _read_staged_text(path, root=module, revision=sha))
        if scope in {"worktree", "both"}:
            hits += find_repository_private_path_hits(root=module, scope="worktree")
    return list({(hit.path, hit.line_number, hit.label): hit for hit in hits}.values())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check current public source and submodules for private paths and secrets.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scope", choices=["staged", "worktree", "both"], default="both")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    hits = find_repository_private_path_hits(root=root, scope=args.scope)
    for hit in hits:
        # Never copy credential values into terminal logs or CI artifacts.
        print(f"{hit.path.relative_to(root)}:{hit.line_number}: {hit.label}", file=sys.stderr)
    return int(bool(hits))


if __name__ == "__main__":
    raise SystemExit(main())
