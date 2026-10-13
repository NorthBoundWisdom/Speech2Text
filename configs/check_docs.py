"""Check current documentation links and product-name headings without touching history."""
from __future__ import annotations

from pathlib import Path
from html.parser import HTMLParser
import argparse
import json
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def current_documents() -> list[Path]:
    return sorted([
        ROOT / "README.md", ROOT / "README.en.md", ROOT / "AGENTS.md", ROOT / "app/README.md",
        ROOT / "qt/Audio2TextQt/README.md", ROOT / "website/README.md",
        *ROOT.glob("doc/*.md"), ROOT / "doc/experiments/README.md",
        *ROOT.glob("website/docs/**/*.md"),
    ])


def validate() -> list[str]:
    errors: list[str] = []
    screenshots = json.loads((ROOT / "website/screenshots.json").read_text(encoding="utf-8"))
    virtual_assets = { (ROOT / "website/docs" / target).resolve(): ROOT / source for target, source in screenshots.items() }
    for path in current_documents():
        if not path.is_file():
            errors.append(f"Missing document: {path.relative_to(ROOT)}")
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"^# .*\b(?:Audio2Text|AtoT|Speech2Text)\b", source, re.MULTILINE):
            errors.append(f"Old product title: {path.relative_to(ROOT)}")
        text = re.sub(r"```.*?```", "", source, flags=re.DOTALL)
        text = re.sub(r"`[^`\n]*`", "", text)
        for value in re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", text):
            target = urlsplit(value.strip().strip("<>"))
            if target.scheme or target.netloc or not target.path:
                continue
            destination = path.parent / unquote(target.path)
            if not destination.exists() and not virtual_assets.get(destination.resolve(), destination).exists():
                errors.append(f"Broken local link: {path.relative_to(ROOT)} -> {target.path}")
        if "github.com/NorthBoundWisdom/Speech2Text" in source:
            errors.append(f"Old repository URL: {path.relative_to(ROOT)}")
    return errors


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def validate_site(site: Path) -> list[str]:
    errors = []
    pages = list(site.rglob("*.html"))
    if not pages:
        return ["Built website contains no HTML pages."]
    for page in pages:
        parser = PageLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        for value in parser.links:
            target = urlsplit(value)
            if target.scheme or target.netloc or not target.path:
                continue
            destination = (
                site / unquote(target.path).removeprefix("/sonafolio/").lstrip("/")
                if target.path.startswith("/") else page.parent / unquote(target.path)
            )
            if destination.is_dir():
                destination /= "index.html"
            if not destination.exists():
                errors.append(f"Broken website resource: {page.relative_to(site)} -> {value}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate SonaFolio documentation and site links.")
    parser.add_argument("--site", type=Path)
    args = parser.parse_args()
    failures = validate()
    if args.site:
        failures.extend(validate_site(args.site))
    if failures:
        raise SystemExit("\n".join(failures))
    print("Current documentation links and product headings passed.")
