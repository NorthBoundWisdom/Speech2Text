"""Exercise the published bilingual routes rather than template-only link mocks."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]


class HeaderLanguages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_header = False
        self.in_switch = False
        self.header_switch = False
        self.links = []
        self.labels = []
        self.language = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "header":
            self.in_header = True
        if tag == "nav" and attrs.get("class") == "sf-language-switch":
            self.in_switch = True
            self.header_switch = self.in_header
        if tag == "a" and self.in_switch:
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_switch = False
        if tag == "header":
            self.in_header = False

    def handle_data(self, data):
        if self.in_switch and data.strip():
            self.labels.append(data.strip())


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    destination = tmp_path_factory.mktemp("bilingual-site")
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "-f",
         str(ROOT / "website/mkdocs.yml"), "--site-dir", str(destination)],
        cwd=ROOT, env={**os.environ, "NO_MKDOCS_2_WARNING": "true"},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return destination


def destination_for_link(site, page, href):
    path = unquote(urlsplit(href).path)
    destination = (site / path.removeprefix("/sonafolio/").lstrip("/")) if path.startswith("/") else page.parent / path
    return (destination / "index.html").resolve()


def test_every_page_has_two_visible_header_destinations_and_keeps_the_chapter(site):
    source_pages = sorted(p for p in (ROOT / "website/docs").rglob("*.md") if not p.name.endswith(".en.md"))
    assert source_pages
    for source in source_pages:
        assert source.with_name(source.stem + ".en.md").is_file()
        relative = source.relative_to(ROOT / "website/docs")
        output = Path("index.html") if relative.name == "index.md" else relative.with_suffix("") / "index.html"
        for locale in ("zh", "en"):
            page = site / (output if locale == "zh" else Path("en") / output)
            parsed = HeaderLanguages()
            parsed.feed(page.read_text(encoding="utf-8"))
            assert parsed.language == locale
            assert parsed.header_switch, page
            assert parsed.labels == ["中文", "English"]
            assert {link["hreflang"] for link in parsed.links} == {"zh", "en"}
            assert [link["hreflang"] for link in parsed.links if link.get("aria-current") == "true"] == [locale]
            for link in parsed.links:
                expected = site / (output if link["hreflang"] == "zh" else Path("en") / output)
                assert destination_for_link(site, page, link["href"]) == expected.resolve()
                assert expected.is_file()


def test_english_is_translated_and_search_indexes_both_versions(site):
    english = (site / "en/index.html").read_text(encoding="utf-8")
    chinese = (site / "index.html").read_text(encoding="utf-8")
    assert "Read the highlights." in english
    assert "Website build information" in english
    assert "官网构建信息" in chinese
    assert "Open the handbook" in english
    assert "Handbook overview" in (site / "en/handbook/index.html").read_text(encoding="utf-8")
    docs = json.loads((site / "search/search_index.json").read_text(encoding="utf-8"))["docs"]
    assert any("Too many podcasts" in row["title"] and row["location"].startswith("en/") for row in docs)
    assert any("播客太多" in row["title"] and not row["location"].startswith("en/") for row in docs)
    assert not list(site.rglob("screenshot-2.png"))



def test_error_page_switches_to_home_instead_of_the_last_chapter(site):
    page = site / "404.html"
    text = page.read_text(encoding="utf-8")
    parsed = HeaderLanguages()
    parsed.feed(text)
    assert parsed.language == "zh"
    assert parsed.header_switch
    for link in parsed.links:
        expected = site / ("index.html" if link["hreflang"] == "zh" else "en/index.html")
        assert destination_for_link(site, page, link["href"]) == expected.resolve()
