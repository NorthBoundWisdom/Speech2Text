import pytest

from atot.batch import (
    create_queue,
    open_output_dir,
    output_dirs,
    queue_status,
    run_queue,
    set_paused,
)
from atot.utils import read_json, write_json_atomic


def test_batch_queue_lifecycle(tmp_path):
    queue = tmp_path / "queue.json"
    audio = tmp_path / "episode" / "episode.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"")

    create_queue(queue, [audio], model="tiny", local_only=True)
    assert queue_status(queue)["counts"] == {"pending": 1}
    assert output_dirs(queue) == [str(audio.parent / "output")]
    assert read_json(queue)["local_only"] is True
    assert read_json(queue)["jobs"][0]["local_only"] is True
    assert read_json(queue)["jobs"][0]["output"] == str(audio.parent / "output")

    set_paused(queue, True)
    assert run_queue(queue)["paused"] is True
    set_paused(queue, False)
    result = run_queue(queue, dry_run=True)

    assert result["started"] == 1
    job = read_json(queue)["jobs"][0]
    assert job["status"] == "dry_run"
    assert job["command"][3:7] == ["exec", "transcribe", str(audio), "--job-dir"]
    assert job["command"][7] == str(audio.parent / "output")
    assert job["command"][-1] == "--local-only"


def test_batch_open_output_dir_uses_selected_job(tmp_path):
    queue = tmp_path / "queue.json"
    first = tmp_path / "one" / "episode.wav"
    second = tmp_path / "two" / "episode.wav"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"")
    second.write_bytes(b"")
    create_queue(queue, [first, second], model="tiny")
    (second.parent / "output").mkdir()
    opened = []

    result = open_output_dir(queue, index=2, opener=lambda path: opened.append(path) or True)

    assert result == {"success": True, "output": str(second.parent / "output"), "opened": True}
    assert opened == [second.parent / "output"]


def test_batch_open_output_dir_can_print_or_create(tmp_path):
    queue = tmp_path / "queue.json"
    audio = tmp_path / "episode" / "episode.wav"
    audio.parent.mkdir()
    audio.write_bytes(b"")
    create_queue(queue, [audio], model="tiny")

    result = open_output_dir(queue, create=True, print_only=True)

    assert result == {"success": True, "output": str(audio.parent / "output"), "opened": False}
    assert (audio.parent / "output").is_dir()


def test_batch_open_output_dir_requires_selection_for_multiple_jobs(tmp_path):
    queue = tmp_path / "queue.json"
    first = tmp_path / "one" / "episode.wav"
    second = tmp_path / "two" / "episode.wav"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"")
    second.write_bytes(b"")
    create_queue(queue, [first, second], model="tiny")

    with pytest.raises(ValueError, match="Select a batch job"):
        open_output_dir(queue)


def test_batch_run_resume_skips_done_and_retry_failed(tmp_path):
    queue = tmp_path / "queue.json"
    first = tmp_path / "one" / "episode.wav"
    second = tmp_path / "two" / "episode.wav"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"")
    second.write_bytes(b"")
    create_queue(queue, [first, second], model="tiny")
    payload = read_json(queue)
    payload["jobs"][0]["status"] = "done"
    payload["jobs"][1]["status"] = "failed"
    payload["jobs"][1]["stderr"] = "old failure"
    write_json_atomic(queue, payload)

    result = run_queue(queue, dry_run=True, resume=True, retry_failed=True)

    assert result["started"] == 1
    updated = read_json(queue)
    assert updated["jobs"][0]["status"] == "done"
    assert updated["jobs"][1]["status"] == "dry_run"
    assert updated["jobs"][1]["previous_failure"]["stderr"] == "old failure"
