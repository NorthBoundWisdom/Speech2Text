from __future__ import annotations

import json

import pytest

from atot.agent_summary import AgentSummaryService
from atot.library_store import LibraryStore
from atot.library_validation import validate_library


@pytest.fixture
def summary_service(tmp_path):
    store = LibraryStore(tmp_path / "Audio2TextLibrary", data_root=tmp_path / "data")
    store.upsert_episode(
        {
            "episode_id": "test-episode",
            "title": "测试节目",
            "original_title": "节目原始标题",
            "source": "local",
            "app_read": True,
            "app_star": True,
            "app_group": "Research",
            "app_status_updated_at": "2026-01-01T00:00:00+08:00",
        }
    )
    store.write_episode_documents(
        "test-episode", summary="", transcript="# 转录\n\n[00:00:01] 中文内容🙂\n" * 200
    )
    return AgentSummaryService(store)


def versions(service):
    episode = service.get_episode("test-episode")
    return {key: episode[key] for key in ("transcript_sha256", "summary_sha256")}


def test_agent_reads_complete_unicode_transcript_in_versioned_pages(summary_service):
    expected = summary_service.read_document("test-episode", max_chars=12000)["text"]
    digest = versions(summary_service)["transcript_sha256"]
    pages = []
    offset = 0
    while True:
        page = summary_service.read_document(
            "test-episode", offset=offset, max_chars=31, expected_sha256=digest
        )
        assert len(page["text"]) <= 31
        pages.append(page["text"])
        if page["next_offset"] is None:
            break
        offset = page["next_offset"]
    assert "".join(pages) == expected
    assert summary_service.get_episode("test-episode")["qa_available"] is False


def test_agent_summary_publishes_without_key_and_preserves_transcript_and_flags(summary_service):
    store = summary_service.store
    transcript = store.episodes_root / "test-episode/documents/transcript.md"
    before = transcript.read_bytes()
    result = summary_service.write_summary(
        "test-episode", "# 总结\n\n主要观点。", generator="Codex", **versions(summary_service)
    )
    episode = store.load_episode("test-episode")
    assert result["success"] is True
    assert transcript.read_bytes() == before
    assert episode["app_read"] is True and episode["app_star"] is True
    assert episode["title"] == "测试节目" and episode["app_group"] == "Research"
    assert episode["original_title"] == "节目原始标题"
    assert episode["app_status_updated_at"] == "2026-01-01T00:00:00+08:00"
    assert episode["summary_generator"] == "Codex"
    assert validate_library(store.root) == []
    work = store.local_work_dir("test-episode")
    assert (work / "summary.md").read_text(encoding="utf-8") == "# 总结\n\n主要观点。\n"
    audit = json.loads((work / "agent-summary.json").read_text(encoding="utf-8"))
    assert audit["summary_sha256"] == result["summary_sha256"]
    assert (
        next(doc for doc in episode["documents"] if doc["name"] == "summary.md")["sha256"]
        == audit["summary_sha256"]
    )


def test_agent_refuses_stale_transcript_before_writing(summary_service):
    old = versions(summary_service)
    transcript = summary_service.store.episodes_root / "test-episode/documents/transcript.md"
    transcript.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Transcript changed"):
        summary_service.write_summary("test-episode", "# 总结", **old)
    assert not (summary_service.store.local_work_dir("test-episode") / "summary.md").exists()


def test_agent_refuses_stale_summary_even_when_overwrite_is_requested(summary_service):
    old = versions(summary_service)
    summary = summary_service.store.episodes_root / "test-episode/documents/summary.md"
    summary.write_text("user edit", encoding="utf-8")
    with pytest.raises(ValueError, match="Summary changed"):
        summary_service.write_summary("test-episode", "# 总结", overwrite=True, **old)
    assert summary.read_text(encoding="utf-8") == "user edit"


def test_overwrite_requires_explicit_request_and_current_version(summary_service):
    summary_service.write_summary("test-episode", "# 原总结", **versions(summary_service))
    current = versions(summary_service)
    with pytest.raises(FileExistsError):
        summary_service.write_summary("test-episode", "# 新总结", **current)
    summary_service.write_summary("test-episode", "# 新总结", overwrite=True, **current)
    with pytest.raises(ValueError, match="Summary changed"):
        summary_service.write_summary("test-episode", "# 再次总结", overwrite=True, **current)


@pytest.mark.parametrize("episode_id", ["../outside", "/outside", "..", "a/b", "C:\\outside"])
def test_agent_rejects_path_identifiers(summary_service, episode_id):
    with pytest.raises(ValueError, match="identifier"):
        summary_service.get_episode(episode_id)


def test_agent_rejects_document_symlink_outside_library(summary_service, tmp_path):
    transcript = summary_service.store.episodes_root / "test-episode/documents/transcript.md"
    outside = tmp_path / "private.txt"
    outside.write_text("private", encoding="utf-8")
    transcript.unlink()
    transcript.symlink_to(outside)
    with pytest.raises(ValueError, match="configured root"):
        summary_service.read_document("test-episode")


def test_agent_does_not_fabricate_qa_when_report_is_malformed(summary_service):
    work = summary_service.store.local_work_dir("test-episode")
    work.mkdir(parents=True)
    (work / "qa.json").write_text("not JSON", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        summary_service.get_episode("test-episode")


def test_agent_rejects_deleted_episode(summary_service):
    summary_service.store.delete_episode("test-episode")
    with pytest.raises(FileNotFoundError, match="deleted"):
        summary_service.get_episode("test-episode")


def test_agent_lists_only_transcribed_episodes_without_summary(summary_service):
    store = summary_service.store
    store.upsert_episode({"episode_id": "metadata-only", "title": "未转录"})
    result = summary_service.list_episodes(needs_summary=True)
    assert [episode["episode_id"] for episode in result["episodes"]] == ["test-episode"]
    summary_service.write_summary("test-episode", "# 已完成", **versions(summary_service))
    assert summary_service.list_episodes(needs_summary=True)["total"] == 0
    page = summary_service.list_episodes(limit=1)
    assert page["next_offset"] == 1
    assert len(summary_service.list_episodes(offset=1, limit=1)["episodes"]) == 1


def test_agent_read_rejects_stale_version_and_invalid_ranges(summary_service):
    with pytest.raises(ValueError, match="Document changed"):
        summary_service.read_document("test-episode", expected_sha256="stale")
    for params in ({"offset": -1}, {"max_chars": 0}, {"max_chars": 12001}, {"offset": 100000}):
        with pytest.raises(ValueError):
            summary_service.read_document("test-episode", **params)


def test_agent_summary_exposes_configured_language_without_changing_versions(summary_service):
    service = AgentSummaryService(summary_service.store, output_language="en")
    episode = service.get_episode("test-episode")
    assert episode["output_language"] == "en"
    assert "English (en)" in episode["instructions"]
    assert "write a Chinese" not in episode["instructions"]
    assert versions(service) == versions(summary_service)
