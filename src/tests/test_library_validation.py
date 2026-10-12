from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from atot.library_store import LibraryStore, stable_episode_id
from atot.library_validation import validate_library
from atot.utils import read_json, write_json_atomic


def _load_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "validate_library.py"
    spec = importlib.util.spec_from_file_location("validate_library_script", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sample_store(tmp_path: Path) -> tuple[LibraryStore, str]:
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    store.upsert_subscription(
        {
            "id": "podcast_rss-test",
            "title": "测试订阅",
            "source": "podcast_rss",
            "url": "https://example.com/show",
            "feed_url": "https://example.com/feed.xml",
            "group_name": "Research",
        }
    )
    episode_id = stable_episode_id(
        {
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "episode-guid",
        }
    )
    store.upsert_episode(
        {
            "episode_id": episode_id,
            "title": "001. 测试",
            "source": "podcast_rss",
            "source_url": "https://example.com/e",
            "canonical_url": "https://example.com/e",
            "audio_url": "https://media.example/e.m4a",
            "guid": "episode-guid",
            "subscription_id": "podcast_rss-test",
        }
    )
    store.write_episode_documents(episode_id, summary="# Summary\n", transcript="正文\n")
    return store, episode_id


def test_validate_library_accepts_store_output(tmp_path):
    store, _episode_id = _sample_store(tmp_path)

    assert validate_library(store.root) == []
    assert read_json(store.root / "groups" / "Research.json")["kind"] == "audio2text.library.group"


def test_validate_library_accepts_shared_groups(tmp_path):
    store, _episode_id = _sample_store(tmp_path)
    groups_root = store.root / "groups"
    groups_root.mkdir(exist_ok=True)
    write_json_atomic(
        groups_root / "生活.json",
        {
            "schema_version": 1,
            "kind": "audio2text.library.group",
            "id": "生活",
            "title": "生活",
            "created_at": "2026-01-01T00:00:00+08:00",
        },
    )

    assert validate_library(store.root) == []


def test_validate_library_rejects_invalid_shared_group(tmp_path):
    store, _episode_id = _sample_store(tmp_path)
    groups_root = store.root / "groups"
    groups_root.mkdir(exist_ok=True)
    write_json_atomic(
        groups_root / "Research.json",
        {
            "schema_version": 1,
            "kind": "audio2text.library.group",
            "id": "Research",
            "title": "Research",
            "debug_path": "/tmp/private",
        },
    )

    errors = validate_library(store.root)

    assert any("groups/Research.json: unexpected keys ['debug_path']" in error for error in errors)


def test_shared_library_fixture_matches_schema():
    fixture = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "Tests"
        / "Audio2TextCoreTests"
        / "Fixtures"
        / "Audio2TextLibrary"
    )

    assert validate_library(fixture) == []


def test_validate_library_rejects_fat_manifest_entries(tmp_path):
    store, _episode_id = _sample_store(tmp_path)
    manifest_path = store.root / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["episodes"][0]["title"] = "should live in episode.json"
    write_json_atomic(manifest_path, manifest)

    errors = validate_library(store.root)

    assert any("manifest.json: episodes[0]: unexpected keys ['title']" in error for error in errors)


def test_validate_library_rejects_unpublished_documents(tmp_path):
    store, episode_id = _sample_store(tmp_path)
    (store.episodes_root / episode_id / "documents" / "raw.json").write_text("{}", encoding="utf-8")

    errors = validate_library(store.root)

    assert any("unexpected Library document" in error for error in errors)


def test_validate_library_rejects_tombstoned_episode_records(tmp_path):
    store, episode_id = _sample_store(tmp_path)
    write_json_atomic(
        store.episode_tombstones_root / f"{episode_id}.json",
        {
            "schema_version": 1,
            "kind": "audio2text.library.episode_tombstone",
            "episode_id": episode_id,
            "deleted_at": "2026-01-01T00:00:00+08:00",
        },
    )
    store.rebuild_manifest()

    errors = validate_library(store.root)

    assert any(
        "tombstoned episode must not have a public episode record" in error for error in errors
    )
    assert any(
        "tombstone suppresses an episode directory that still exists" in error for error in errors
    )


def test_validate_library_rejects_local_absolute_paths(tmp_path):
    store, episode_id = _sample_store(tmp_path)
    episode_path = store.episodes_root / episode_id / "episode.json"
    episode = read_json(episode_path)
    episode["source_url"] = "/tmp/private/audio.m4a"
    write_json_atomic(episode_path, episode)

    errors = validate_library(store.root)

    assert any("source_url: contains a local absolute path" in error for error in errors)


def test_validate_library_script_returns_nonzero_for_invalid_library(tmp_path, capsys):
    script = _load_script()
    store, episode_id = _sample_store(tmp_path)
    (store.episodes_root / episode_id / "documents" / "debug.json").write_text(
        "{}", encoding="utf-8"
    )

    assert script.main([str(store.root)]) == 1
    assert "unexpected Library document" in capsys.readouterr().err
