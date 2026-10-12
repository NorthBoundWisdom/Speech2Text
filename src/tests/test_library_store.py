from __future__ import annotations

import json

from atot import library_store
from atot.library_store import (
    LibraryStore,
    default_local_library_root,
    normalize_library_root,
    publish_work_documents_to_library,
    stable_episode_id,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_thin_manifest_rebuild_does_not_read_transcript_contents(tmp_path, monkeypatch):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    store.upsert_episode({"episode_id": "manifest-only", "title": "Manifest"})

    def refuse_document_reads(_path):
        raise AssertionError("A thin manifest only needs episode identities.")

    monkeypatch.setattr(library_store, "_document_records", refuse_document_reads)
    assert store.rebuild_manifest()["episode_count"] == 1


def test_library_store_writes_thin_manifest_and_public_records(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    subscription = store.upsert_subscription(
        {
            "id": "podcast_rss-test",
            "title": "测试订阅",
            "source": "podcast_rss",
            "url": "https://example.com/show",
            "feed_url": "https://example.com/feed.xml",
            "group_name": "Research",
            "private": "/tmp/private",
        }
    )
    episode_id = stable_episode_id(
        {
            "source": "podcast_rss",
            "subscription_id": subscription["id"],
            "guid": "episode-guid",
        }
    )

    episode, created = store.upsert_episode(
        {
            "episode_id": episode_id,
            "title": "001. 测试",
            "source": "podcast_rss",
            "source_url": "https://example.com/e",
            "canonical_url": "https://example.com/e",
            "audio_url": "https://media.example/e.m4a",
            "media_filename": "episode.m4a",
            "guid": "episode-guid",
            "subscription_id": subscription["id"],
            "audio_path": "/tmp/private/e.m4a",
            "topic_path": "/tmp/private/主题.md",
        }
    )
    documents = store.write_episode_documents(
        episode_id, summary="# Summary\n", transcript="正文\n"
    )
    manifest = read_json(store.root / "manifest.json")
    episode_record = read_json(store.episodes_root / episode_id / "episode.json")
    group_record = read_json(store.groups_root / "Research.json")

    assert created is True
    assert episode["product_status"] == "metadata_only"
    assert manifest["kind"] == "audio2text.library.manifest"
    assert manifest["episode_count"] == 1
    assert manifest["subscription_count"] == 1
    assert manifest["episodes"] == [
        {"episode_id": episode_id, "path": f"episodes/{episode_id}/episode.json"}
    ]
    assert manifest["subscriptions"] == [
        {"id": "podcast_rss-test", "path": "subscriptions/podcast_rss-test.json"}
    ]
    assert group_record["kind"] == "audio2text.library.group"
    assert group_record["title"] == "Research"
    assert {document["name"] for document in documents} == {"summary.md", "transcript.md"}
    assert episode_record["product_status"] == "available"
    assert episode_record["processed_at"]
    assert episode_record["media_filename"] == "episode.m4a"
    assert "audio_path" not in episode_record
    assert "topic_path" not in episode_record
    assert "/tmp/private" not in json.dumps(episode_record, ensure_ascii=False)


def test_delete_episode_writes_tombstone_and_cleans_local_files(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    episode, _ = store.upsert_episode(
        {
            "title": "待删除",
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "delete-me",
            "audio_url": "https://media.example/delete.m4a",
        }
    )
    episode_id = episode["episode_id"]
    store.local_material_dir(episode_id).mkdir(parents=True)
    store.local_work_dir(episode_id).mkdir(parents=True)
    (store.local_material_dir(episode_id) / "audio.m4a").write_text("audio", encoding="utf-8")
    (store.local_work_dir(episode_id) / "run.json").write_text("{}", encoding="utf-8")

    result = store.delete_episode(episode_id)

    tombstone = read_json(store.episode_tombstones_root / f"{episode_id}.json")
    manifest = read_json(store.root / "manifest.json")
    assert result["deleted"] == episode_id
    assert tombstone["kind"] == "audio2text.library.episode_tombstone"
    assert tombstone["guid"] == "delete-me"
    assert not (store.episodes_root / episode_id).exists()
    assert not store.local_material_dir(episode_id).exists()
    assert not store.local_work_dir(episode_id).exists()
    assert manifest["episode_count"] == 0
    assert manifest["tombstone_count"] == 1


def test_upsert_episode_preserves_published_ai_title(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    episode, _ = store.upsert_episode(
        {
            "title": "原始节目标题",
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "episode-guid",
            "audio_url": "https://media.example/episode.m4a",
        }
    )
    record_path = store.episodes_root / episode["episode_id"] / "episode.json"
    record = read_json(record_path)
    record["title"] = "AI 总结标题"
    record["title_updated_at"] = "2026-06-20T09:00:00Z"
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    updated, created = store.upsert_episode(
        {
            "episode_id": episode["episode_id"],
            "title": "刷新后的原始标题",
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "episode-guid",
            "audio_url": "https://media.example/episode.m4a",
            "description": "updated shownotes",
        }
    )

    persisted = read_json(record_path)
    assert created is False
    assert updated["title"] == "AI 总结标题"
    assert persisted["title"] == "AI 总结标题"
    assert persisted["title_updated_at"] == "2026-06-20T09:00:00Z"
    assert "processed_at" not in persisted
    assert persisted["description"] == "updated shownotes"


def test_upsert_episode_preserves_processed_at(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    episode, _ = store.upsert_episode(
        {
            "title": "已处理节目",
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "processed-guid",
            "audio_url": "https://media.example/processed.m4a",
        }
    )
    store.write_episode_documents(episode["episode_id"], summary="summary", transcript="transcript")
    record_path = store.episodes_root / episode["episode_id"] / "episode.json"
    processed_at = read_json(record_path)["processed_at"]

    store.upsert_episode(
        {
            "episode_id": episode["episode_id"],
            "title": "刷新后的节目标题",
            "source": "podcast_rss",
            "subscription_id": "podcast_rss-test",
            "guid": "processed-guid",
            "audio_url": "https://media.example/processed.m4a",
            "description": "updated shownotes",
        }
    )

    persisted = read_json(record_path)
    assert persisted["processed_at"] == processed_at
    assert persisted["description"] == "updated shownotes"


def test_publish_work_documents_to_library_uses_work_outputs(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    episode, _ = store.upsert_episode(
        {
            "title": "已处理",
            "source": "local",
            "source_url": "clip.m4a",
            "canonical_url": "clip.m4a",
        }
    )
    work_dir = store.local_work_dir(episode["episode_id"])
    (work_dir / "cloud").mkdir(parents=True)
    (work_dir / "transcript.readable.md").write_text("可读正文", encoding="utf-8")
    (work_dir / "cloud" / "summary.md").write_text("云摘要", encoding="utf-8")
    (work_dir / "raw.json").write_text('{"raw": true}', encoding="utf-8")

    result = publish_work_documents_to_library(
        store=store, episode_id=episode["episode_id"], work_dir=work_dir
    )

    documents_dir = store.episodes_root / episode["episode_id"] / "documents"
    assert result["documents_dir"] == str(documents_dir)
    assert (documents_dir / "summary.md").read_text(encoding="utf-8").strip() == "云摘要"
    assert (documents_dir / "transcript.md").read_text(encoding="utf-8").strip() == "可读正文"
    assert not (documents_dir / "raw.json").exists()
    assert read_json(store.episodes_root / episode["episode_id"] / "episode.json")["processed_at"]


def test_library_root_normalization_and_default_local_root(tmp_path):
    assert (
        normalize_library_root(tmp_path / "CloudDocs" / "Audio2Text")
        == tmp_path / "CloudDocs" / "Audio2Text" / "Audio2TextLibrary"
    )
    assert normalize_library_root(tmp_path / "Audio2TextLibrary") == tmp_path / "Audio2TextLibrary"
    assert default_local_library_root(tmp_path / "data") == tmp_path / "data" / "Audio2TextLibrary"
