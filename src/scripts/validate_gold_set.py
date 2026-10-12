#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_CATEGORIES = {"ai_podcast", "coffee_podcast", "casual_talk"}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_gold_dir(gold_dir: Path) -> list[str]:
    errors: list[str] = []
    if not gold_dir.exists():
        return [f"missing gold directory: {gold_dir}"]
    categories: set[str] = set()
    for ref in sorted(gold_dir.glob("*.ref.txt")):
        stem = ref.name.removesuffix(".ref.txt")
        text = ref.read_text(encoding="utf-8").strip()
        if len(text) < 80:
            errors.append(f"{ref}: reference text is too short")
        terms_path = gold_dir / f"{stem}.terms.json"
        meta_path = gold_dir / f"{stem}.meta.json"
        if not terms_path.exists():
            errors.append(f"{ref}: missing {terms_path.name}")
            continue
        if not meta_path.exists():
            errors.append(f"{ref}: missing {meta_path.name}")
            continue
        terms_payload = _read_json(terms_path)
        terms = terms_payload.get("terms") if isinstance(terms_payload, dict) else None
        if not isinstance(terms, list) or not terms:
            errors.append(f"{terms_path}: `terms` must be a non-empty list")
        meta = _read_json(meta_path)
        if not isinstance(meta, dict):
            errors.append(f"{meta_path}: metadata must be an object")
            continue
        category = str(meta.get("category", ""))
        if category:
            categories.add(category)
        for key in ("source", "audio_file", "time_range", "category", "known_difficulties"):
            if key not in meta:
                errors.append(f"{meta_path}: missing `{key}`")
        audio_file = str(meta.get("audio_file", ""))
        if Path(audio_file).is_absolute():
            errors.append(f"{meta_path}: audio_file must be relative")
        difficulties = meta.get("known_difficulties")
        if not isinstance(difficulties, list) or not difficulties:
            errors.append(f"{meta_path}: known_difficulties must be a non-empty list")
    if not list(gold_dir.glob("*.ref.txt")):
        errors.append(f"{gold_dir}: no .ref.txt files found")
    missing_categories = REQUIRED_CATEGORIES - categories
    if missing_categories:
        errors.append(f"missing gold categories: {', '.join(sorted(missing_categories))}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate public text-only gold transcript fixtures."
    )
    parser.add_argument("--gold-dir", type=Path, default=Path("tests/gold"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_gold_dir(args.gold_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{args.gold_dir}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
