"""Render escaped Git provenance on the public product home page."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
MARKER = "<!-- SONAFOLIO_BUILD -->"


def metadata_html(locale: str = "zh") -> str:
    if locale not in {"zh", "en"}:
        raise ValueError("Unsupported website locale.")
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
    labels = json.loads((ROOT / f"website/locales/{locale}.json").read_text(encoding="utf-8"))
    return (
        f'<aside class="build-provenance" aria-label="{escape(labels["build_aria"])}">'
        f'<span>{escape(labels["build_label"])} · {escape(label)}</span> '
        f'<a href="{url}">{escape(labels["source_label"])} {sha[:7]}</a>'
        f'<span class="build-title">{escape(title)}</span></aside>'
    )


def on_page_markdown(markdown: str, page, config, files) -> str:
    if page.file.src_uri not in {"index.md", "index.en.md", "en/index.md"}:
        return markdown
    if markdown.count(MARKER) != 1:
        raise ValueError("Home page must contain exactly one build metadata marker.")
    locale = config.theme.get("language", "zh") if config is not None else "zh"
    return markdown.replace(MARKER, metadata_html(locale))



def on_template_context(context, template_name, config):
    """Give the shared error page home links, independent of the last rendered chapter."""
    if template_name != "404.html":
        return context
    labels = json.loads((ROOT / "website/locales/zh.json").read_text(encoding="utf-8"))
    base_path = urlsplit(config.site_url).path.rstrip("/")
    alternates = []
    for locale, suffix in (("zh", "/"), ("en", "/en/")):
        language_labels = json.loads((ROOT / f"website/locales/{locale}.json").read_text(encoding="utf-8"))
        alternates.append({"lang": locale, "name": language_labels["language_name"], "link": base_path + suffix})
    localized = dict(config)
    localized["theme"] = {**dict(config.theme), "language": "zh"}
    localized["extra"] = {**config.extra, "alternate": alternates,
                          "error_title": labels["error_title"], "error_hint": labels["error_hint"]}
    context["config"] = localized
    return context
