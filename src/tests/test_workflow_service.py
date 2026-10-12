from __future__ import annotations

import pytest

from atot.config_v2 import AtotConfig, AtotLibraryConfig
from atot.task_store import TaskStore
from atot.utils import read_json, write_text_atomic
from atot.workflow_service import WorkflowService


def test_transcribe_and_cloud_summary_publish_documents_to_library(monkeypatch, tmp_path):
    library_root = tmp_path / "Audio2TextLibrary"
    work_dir = tmp_path / "work" / "episode"
    audio_path = tmp_path / "episode.m4a"
    audio_path.write_bytes(b"audio")
    config = AtotConfig(
        path=tmp_path / "config.toml",
        library=AtotLibraryConfig(storage="local", local_root=str(library_root)),
    )
    service = WorkflowService(config=config, task_store=TaskStore(tmp_path / "tasks"))

    def fake_run_transcription(options):
        assert options.input_path == audio_path
        assert options.job_dir == work_dir
        options.job_dir.mkdir(parents=True, exist_ok=True)
        write_text_atomic(
            options.job_dir / "transcript.readable.md", "# Transcript\n\n本地转写正文\n"
        )
        return {
            "success": True,
            "job_dir": str(options.job_dir),
            "output_files": {
                "transcript.readable.md": str(options.job_dir / "transcript.readable.md")
            },
            "review": {},
        }

    def fake_write_cloud_summary(options):
        cloud_dir = options.output_dir / "cloud"
        cloud_dir.mkdir(parents=True, exist_ok=True)
        write_text_atomic(cloud_dir / "summary.md", "# Summary\n\n云摘要\n")
        return {"success": True, "outputs": ["cloud/summary.md"]}

    monkeypatch.setattr("atot.workflow_service.run_transcription", fake_run_transcription)
    monkeypatch.setattr("atot.workflow_service.write_cloud_summary", fake_write_cloud_summary)

    result = service.run_transcribe(audio_path, job_dir=work_dir, local_only=True)
    episode_id = result["run"]["episode_id"]
    documents_dir = library_root / "episodes" / episode_id / "documents"

    assert (documents_dir / "transcript.md").read_text(
        encoding="utf-8"
    ) == "# Transcript\n\n本地转写正文\n"

    service.run_cloud_summarize(work_dir, call_api=True, from_readable=True)

    assert (documents_dir / "summary.md").read_text(encoding="utf-8") == "# Summary\n\n云摘要\n"
    run = read_json(work_dir / "run.json")
    assert run["episode_id"] == episode_id
    assert run["library"]["documents_dir"] == str(documents_dir)


def _local_library_config(tmp_path):
    return AtotConfig(
        path=tmp_path / "config.toml",
        library=AtotLibraryConfig(storage="local", local_root=str(tmp_path / "Audio2TextLibrary")),
    )


def _latest_task_events(store: TaskStore) -> list[dict]:
    latest = store.latest(limit=1)
    assert latest
    return store.events(str(latest[0]["task_id"]))


def _assert_failed_without_finished(events: list[dict], *, stage: str, message: str) -> None:
    assert [event["event"] for event in events][-1] == "task.failed"
    assert events[-1]["stage"] == stage
    assert events[-1]["detail"] == f"{stage} failed"
    assert events[-1]["error_type"] == "RuntimeError"
    assert message in events[-1]["error"]
    assert "task.finished" not in {event["event"] for event in events}


def test_import_failure_records_stage_and_does_not_finish(monkeypatch, tmp_path):
    store = TaskStore(tmp_path / "tasks")
    service = WorkflowService(config=_local_library_config(tmp_path), task_store=store)

    def fail_import(*_args, **_kwargs):
        raise RuntimeError("metadata fetch failed")

    monkeypatch.setattr("atot.workflow_service.import_xiaoyuzhou_episode", fail_import)

    with pytest.raises(RuntimeError, match="metadata fetch failed"):
        service.run_import_xiaoyuzhou(
            "https://www.xiaoyuzhoufm.com/episode/example", transcribe=False
        )

    _assert_failed_without_finished(
        _latest_task_events(store),
        stage="import",
        message="metadata fetch failed",
    )


def test_subscription_refresh_failure_records_stage_and_does_not_finish(monkeypatch, tmp_path):
    store = TaskStore(tmp_path / "tasks")
    service = WorkflowService(config=_local_library_config(tmp_path), task_store=store)

    def fail_refresh(*_args, **_kwargs):
        raise RuntimeError("feed refresh failed")

    monkeypatch.setattr("atot.workflow_service.refresh_subscriptions", fail_refresh)

    with pytest.raises(RuntimeError, match="feed refresh failed"):
        service.run_subscriptions("refresh", refresh_all=True)

    events = _latest_task_events(store)
    assert events[1]["event"] == "task.stage"
    assert events[1]["stage"] == "subscriptions.refresh"
    _assert_failed_without_finished(
        events,
        stage="subscriptions.refresh",
        message="feed refresh failed",
    )


@pytest.mark.parametrize(
    ("method_name", "patch_target", "stage", "message"),
    [
        (
            "run_cloud_prepare",
            "atot.workflow_service.prepare_cloud_input",
            "cloud.prepare",
            "cloud prepare failed",
        ),
        (
            "run_cloud_summarize",
            "atot.workflow_service.write_cloud_summary",
            "cloud.summarize",
            "cloud summarize failed",
        ),
        (
            "run_cloud_title",
            "atot.workflow_service.write_cloud_short_title",
            "cloud.title",
            "cloud title failed",
        ),
        (
            "run_cloud_glossary_review",
            "atot.workflow_service.write_cloud_glossary_review",
            "cloud.glossary_review",
            "cloud glossary review failed",
        ),
        (
            "run_cloud_polish",
            "atot.workflow_service.write_cloud_polish_suggestions",
            "cloud.polish",
            "cloud polish failed",
        ),
    ],
)
def test_cloud_failures_record_stage_and_do_not_finish(
    monkeypatch,
    tmp_path,
    method_name,
    patch_target,
    stage,
    message,
):
    store = TaskStore(tmp_path / "tasks")
    service = WorkflowService(config=_local_library_config(tmp_path), task_store=store)
    output = tmp_path / "work" / "episode"
    output.mkdir(parents=True)

    def fail_cloud(*_args, **_kwargs):
        raise RuntimeError(message)

    monkeypatch.setattr(patch_target, fail_cloud)

    with pytest.raises(RuntimeError, match=message):
        getattr(service, method_name)(output)

    _assert_failed_without_finished(
        _latest_task_events(store),
        stage=stage,
        message=message,
    )
