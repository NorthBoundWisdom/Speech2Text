#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.models import model_download_rows


ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
ROW_RE = re.compile(
    r"^\| `(?P<model>[^`]+)` \| `(?P<path>model/[^`]+)` \| `(?P<url>https://huggingface\.co/[^`]+)` \|$"
)


def readme_model_rows(readme_path: Path = README) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        match = ROW_RE.match(line.strip())
        if match:
            rows.append(match.groupdict())
    return rows


def validate_readme_model_rows(readme_path: Path = README) -> list[str]:
    expected = {(row["path"], row["url"]) for row in model_download_rows()}
    actual = {(row["path"], row["url"]) for row in readme_model_rows(readme_path)}
    errors = []
    for path, url in sorted(expected - actual):
        errors.append(f"README is missing model download row: {path} -> {url}")
    for path, url in sorted(actual - expected):
        errors.append(f"README has model download row not present in inventory: {path} -> {url}")
    return errors


def validate_huggingface_urls() -> list[str]:
    errors = []
    for row in model_download_rows():
        url = row["url"]
        request = Request(url, method="HEAD")
        try:
            with urlopen(request, timeout=15):
                pass
        except HTTPError as exc:
            errors.append(f"{row['path']}: {url} returned HTTP {exc.code}")
        except URLError as exc:
            errors.append(f"{row['path']}: {url} failed: {exc.reason}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate README model download rows.")
    parser.add_argument("--readme", type=Path, default=README)
    parser.add_argument(
        "--check-remote",
        action="store_true",
        help="Also issue HEAD requests for Hugging Face URLs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_readme_model_rows(args.readme)
    if args.check_remote:
        errors.extend(validate_huggingface_urls())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
