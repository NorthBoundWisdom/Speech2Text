from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_hf_model.py"
    spec = importlib.util.spec_from_file_location("check_hf_model", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_format_size() -> None:
    check = _load_script()

    assert check._format_size(None) == "unknown"
    assert check._format_size(512) == "512 B"
    assert check._format_size(1024 * 1024) == "1.0 MB"


def test_file_entries_extract_names_and_sizes() -> None:
    check = _load_script()
    info = SimpleNamespace(
        siblings=[
            SimpleNamespace(rfilename="weights.npz", size=123),
            SimpleNamespace(rfilename="config.json", size=None),
            SimpleNamespace(rfilename=None, size=10),
        ]
    )

    entries = check._file_entries(info)

    assert [entry.name for entry in entries] == ["config.json", "weights.npz"]
    assert check._find_file(entries, "weights.npz").size == 123
    assert check._find_file(entries, "missing.bin") is None


def test_parser_defaults_to_metadata_only_check() -> None:
    check = _load_script()
    args = check.build_parser().parse_args([])

    assert args.model == check.DEFAULT_MODEL
    assert args.filename is None
    assert args.probe_bytes == check.DEFAULT_PROBE_BYTES
    assert args.min_mb_s == 0.0
    assert args.local_cache_only is False


def test_mb_per_second() -> None:
    check = _load_script()

    assert check._mb_per_second(1024 * 1024, 2.0) == 0.5
    assert check._mb_per_second(1024, 0.0) == 0.0


def test_local_cache_path_handles_cache_miss(monkeypatch) -> None:
    check = _load_script()

    monkeypatch.setattr(check, "try_to_load_from_cache", lambda *args, **kwargs: None)

    assert (
        check._local_cache_path(
            repo_id="model",
            filename="weights.npz",
            revision="main",
            cache_dir=None,
        )
        is None
    )


def test_local_cache_path_returns_existing_path(monkeypatch, tmp_path) -> None:
    check = _load_script()
    cached = tmp_path / "weights.npz"
    cached.write_bytes(b"weights")
    monkeypatch.setattr(check, "try_to_load_from_cache", lambda *args, **kwargs: str(cached))

    assert (
        check._local_cache_path(
            repo_id="model",
            filename="weights.npz",
            revision="main",
            cache_dir=None,
        )
        == cached
    )
