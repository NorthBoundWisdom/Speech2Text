"""Publish reviewed screenshots from their canonical documentation location."""
import json
from pathlib import Path

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[2]


def on_files(files, config):
    manifest = json.loads((ROOT / "website/screenshots.json").read_text(encoding="utf-8"))
    for destination, name in manifest.items():
        source = ROOT / name
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Missing reviewed website screenshot: {name}")
        resource = File(destination, src_dir=str(ROOT), dest_dir=config["site_dir"],
                        use_directory_urls=config["use_directory_urls"])
        resource.abs_src_path = str(source)
        files.append(resource)
    return files
