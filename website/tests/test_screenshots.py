import importlib.util
import json
from pathlib import Path

from mkdocs.structure.files import Files
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("site_screenshots", ROOT / "website/hooks/screenshots.py")
assert spec is not None and spec.loader is not None
screenshots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screenshots)


def test_only_reviewed_assets_are_published_without_duplicate_sources(tmp_path):
    files = screenshots.on_files(Files([]), {"site_dir": str(tmp_path), "use_directory_urls": True})
    assert set(file.src_uri for file in files) == {"assets/screenshot-1.png", "assets/screenshot-3.png"}
    for file in files:
        file.copy_file()
        assert Path(file.abs_dest_path).read_bytes() == Path(file.abs_src_path).read_bytes()
        assert Path(file.abs_src_path).parent == ROOT / "doc/assets"
    assert not (tmp_path / "assets/screenshot-2.png").exists()


def test_missing_reviewed_asset_fails_the_build(tmp_path, monkeypatch):
    (tmp_path / "website").mkdir()
    (tmp_path / "website/screenshots.json").write_text(json.dumps({"assets/missing.png": "doc/assets/missing.png"}))
    monkeypatch.setattr(screenshots, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Missing reviewed"):
        screenshots.on_files(Files([]), {"site_dir": str(tmp_path / "output"), "use_directory_urls": True})
