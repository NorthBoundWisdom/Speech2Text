import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "website_metadata", Path(__file__).resolve().parents[2] / "website/hooks/build_metadata.py"
)
assert spec is not None and spec.loader is not None
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


def test_public_build_metadata_escapes_commit_text(monkeypatch):
    monkeypatch.setattr(
        metadata.subprocess, "check_output",
        lambda args, **kwargs: "a" * 40 if args[1] == "rev-parse" else '<script>alert("x")</script>',
    )
    monkeypatch.setenv("SONAFOLIO_SITE_BUILT_AT", "2026-10-13T08:00:00+08:00")
    result = metadata.metadata_html()
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "2026-10-13 00:00 UTC" in result
    assert "https://github.com/NorthBoundWisdom/sonafolio/commit/" + "a" * 40 in result


def test_build_metadata_rejects_untrusted_sha(monkeypatch):
    monkeypatch.setattr(metadata.subprocess, "check_output", lambda *args, **kwargs: '"><script>')
    with pytest.raises(ValueError, match="SHA"):
        metadata.metadata_html()


def test_build_time_requires_timezone(monkeypatch):
    monkeypatch.setattr(metadata.subprocess, "check_output", lambda *args, **kwargs: "a" * 40)
    monkeypatch.setenv("SONAFOLIO_SITE_BUILT_AT", "2026-10-13T08:00:00")
    with pytest.raises(ValueError, match="timezone"):
        metadata.metadata_html()


def test_homepage_requires_one_metadata_marker():
    page = SimpleNamespace(file=SimpleNamespace(src_uri="index.md"))
    with pytest.raises(ValueError, match="exactly one"):
        metadata.on_page_markdown("no marker", page, None, None)
    with pytest.raises(ValueError, match="exactly one"):
        metadata.on_page_markdown(metadata.MARKER * 2, page, None, None)
