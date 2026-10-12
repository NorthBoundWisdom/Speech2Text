"""Render escaped Git provenance on the public product home page."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MARKER = "<!-- SONAFOLIO_BUILD -->"


def metadata_html() -> str:
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Website build requires a valid Git commit SHA.")
    title = subprocess.check_output(
        ["git", "show", "-s", "--format=%s", sha], cwd=ROOT, text=True
    ).strip()
    timestamp = os.environ.get("SONAFOLIO_SITE_BUILT_AT")
    built_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.now(timezone.utc)
    if built_at.tzinfo is None:
        raise ValueError("Website build time must include a timezone.")
    label = built_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    url = f"https://github.com/NorthBoundWisdom/sonafolio/commit/{sha}"
    return (
        '<aside class="build-provenance" aria-label="网站构建信息">'
        f'<span>网站构建 · {escape(label)}</span> '
        f'<a href="{url}">源码 {sha[:7]}</a>'
        f'<span class="build-title">{escape(title)}</span></aside>'
    )


def on_page_markdown(markdown: str, page, config, files) -> str:
    if page.file.src_uri != "index.md":
        return markdown
    if markdown.count(MARKER) != 1:
        raise ValueError("Home page must contain exactly one build metadata marker.")
    return markdown.replace(MARKER, metadata_html())
