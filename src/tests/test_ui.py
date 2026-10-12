import pytest

from atot.ui import (
    cloud_prepare_command,
    open_output_folder,
    qa_command,
    status_payload,
    transcribe_command,
)
from atot.utils import write_json_atomic


def test_status_payload_reads_run_qa_repair_and_cloud(tmp_path):
    output = tmp_path / "output"
    write_json_atomic(
        output / "run.json",
        {
            "success": True,
            "chunks": [{"index": 0}, {"index": 1}],
            "chunk_status_counts": {"transcribed": 1, "skipped_existing": 1},
        },
    )
    write_json_atomic(output / "qa.json", {"success": False})
    write_json_atomic(output / "repair" / "repair_plan.json", {"windows": [{"start": 0, "end": 1}]})
    write_json_atomic(output / "repair" / "repair_run_001.json", {"success": True, "repair_id": 1})
    write_json_atomic(
        output / "cloud" / "input" / "manifest.json", {"input_files": ["transcript.for_cloud.md"]}
    )

    payload = status_payload(output)

    assert payload["run_status"] == "done"
    assert payload["qa_status"] == "fail"
    assert payload["repair_status"] == "applied"
    assert payload["repair_run"]["repair_id"] == 1
    assert payload["cloud_status"] == "prepared"
    assert payload["chunk_progress"]["completed"] == 2
    assert payload["chunk_progress"]["total"] == 2
    assert payload["local_progress"]["status"] == "done"
    assert payload["local_progress"]["percent"] == 100.0
    assert payload["cloud_progress"]["status"] == "prepared"


def test_open_output_folder_uses_injected_opener(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    opened = []

    result = open_output_folder(output, opener=lambda path: opened.append(path) or True)

    assert result == {"success": True, "output": str(output), "opened": True}
    assert opened == [output]


def test_open_output_folder_requires_existing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        open_output_folder(tmp_path / "missing", opener=lambda _path: True)


def test_ui_commands_use_exec_cli_v2():
    payload = {
        "input": "episode.wav",
        "output": "work/output",
        "model": "large-v3-turbo",
        "smart": True,
        "local_only": True,
    }

    assert transcribe_command(payload)[3:] == [
        "exec",
        "transcribe",
        "episode.wav",
        "--job-dir",
        "work/output",
        "--model",
        "large-v3-turbo",
        "--chunking",
        "smart",
        "--local-only",
    ]
    assert qa_command(payload)[3:] == ["exec", "qa", "work/output"]
    assert cloud_prepare_command(payload)[3:] == ["exec", "cloud", "prepare", "work/output"]
