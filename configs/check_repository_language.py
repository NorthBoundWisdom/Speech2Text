"""Enforce English source prose with reviewed documentation and language-data exceptions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "language-assets.json"
CHINESE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]")


def line_hash(line: str) -> str:
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def check_text(path: str, text: str, policy: dict) -> list[str]:
    resources = policy["resources"]
    if path in resources:
        return []
    approved = set(policy["embedded"].get(path, {}).get("line_hashes", []))
    return [
        f"{path}:{number}: Chinese outside reviewed documentation, translation, or ASR language assets"
        for number, line in enumerate(text.splitlines(), 1)
        if CHINESE.search(line) and line_hash(line) not in approved
    ]


def tracked_and_new_files() -> list[str]:
    result = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    )
    return sorted(set(path.decode("utf-8") for path in result.split(b"\0") if path))


def validate() -> list[str]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    errors = []
    for name in tracked_and_new_files():
        path = ROOT / name
        # FreeCM is a separately maintained third-party submodule, not host-owned source.
        if name == "FreeCM" or not path.is_file():
            continue
        if CHINESE.search(name):
            errors.append(f"{name}: non-English tracked filename")
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        errors.extend(check_text(name, source, policy))
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        raise SystemExit("\n".join(failures))
    print("Repository language policy passed; reviewed documentation and language assets are preserved.")
