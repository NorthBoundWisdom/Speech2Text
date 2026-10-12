from atot.status import inspect_output, status_to_markdown
from atot.utils import write_json_atomic, write_text_atomic


def test_status_suggests_transcribe_when_raw_missing(tmp_path):
    output = tmp_path / "output"
    report = inspect_output(output)

    assert report["success"] is False
    assert report["state"]["has_raw_json"] is False
    assert report["next_actions"][0]["action"] == "run_transcribe"


def test_status_reports_cloud_prepare_after_qa_pass(tmp_path):
    output = tmp_path / "output"
    details = output
    write_json_atomic(details / "raw.json", {"segments": [{"start": 0, "end": 1, "text": "hello"}]})
    write_json_atomic(
        details / "corrected.json", {"segments": [{"start": 0, "end": 1, "text": "hello"}]}
    )
    write_text_atomic(details / "transcript.corrected.txt", "hello")
    write_text_atomic(output / "transcript.readable.md", "hello")
    write_text_atomic(details / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\nhello\n")
    write_json_atomic(details / "qa.json", {"success": True, "summary": {"issue_count": 0}})
    write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 0}})

    report = inspect_output(output, write_report=True)

    assert report["success"] is True
    assert report["state"]["qa_status"] == "pass"
    assert report["state"]["quality_state"]["asr_health"] == "pass"
    assert report["state"]["quality_state"]["readable_health"] == "pass"
    assert report["state"]["disk_usage"]["total"] > 0
    assert report["state"]["disk_usage"]["text"] > 0
    assert any(item["action"] == "cloud_prepare" for item in report["next_actions"])
    assert (details / "status.md").exists()
    assert "SonaFolio Output Status" in status_to_markdown(report)
    assert "Quality State" in status_to_markdown(report)


def test_status_detects_existing_cloud_input_and_missing_summary(tmp_path):
    output = tmp_path / "output"
    details = output
    write_json_atomic(details / "raw.json", {"segments": [{"start": 0, "end": 1, "text": "hello"}]})
    write_json_atomic(
        details / "corrected.json", {"segments": [{"start": 0, "end": 1, "text": "hello"}]}
    )
    write_json_atomic(details / "qa.json", {"success": True, "summary": {"issue_count": 0}})
    write_json_atomic(output / "cloud" / "input" / "manifest.json", {"contains_audio": False})

    report = inspect_output(output)

    assert report["state"]["cloud_input_prepared"] is True
    assert report["state"]["quality_state"]["cloud_summary_ready"] is False
    assert any(item["action"] == "cloud_summarize" for item in report["next_actions"])


def test_status_reports_local_and_cloud_progress(tmp_path):
    output = tmp_path / "output"
    details = output
    write_json_atomic(
        details / "run.json",
        {
            "success": False,
            "chunks": [{"index": 0}, {"index": 1}],
            "cloud": {"summary_state": "running", "audio_uploaded": False},
        },
    )
    write_text_atomic(
        details / "events.jsonl",
        "\n".join(
            [
                '{"event":"stage","stage":"prepare_audio"}',
                '{"event":"chunk","chunk":0,"total_chunks":2,"status":"started"}',
                '{"event":"chunk","chunk":0,"total_chunks":2,"status":"transcribed"}',
                '{"event":"chunk","chunk":1,"total_chunks":2,"status":"started"}',
            ]
        )
        + "\n",
    )
    write_json_atomic(details / "qa.json", {"success": True, "summary": {"issue_count": 0}})
    write_json_atomic(
        output / "cloud" / "input" / "manifest.json", {"text_chunks": ["chunks/text_chunk_0001.md"]}
    )
    write_json_atomic(
        output / "cloud" / "chunk_summaries" / "chunk_0001.summary.json",
        {"success": True, "summary": "ok"},
    )

    report = inspect_output(output)

    assert report["state"]["local_progress"]["completed"] == 1
    assert report["state"]["local_progress"]["total"] == 2
    assert report["state"]["local_progress"]["active_chunk"] == 1
    assert report["state"]["cloud_progress"]["status"] == "running"
    assert report["state"]["cloud_progress"]["completed"] == 1


def test_status_reports_optional_repair_for_qa_failures(tmp_path):
    output = tmp_path / "output"
    details = output
    write_json_atomic(details / "raw.json", {"segments": [{"start": 0, "end": 1, "text": "hello"}]})
    write_json_atomic(
        details / "qa.json", {"success": False, "summary": {"blocking_issue_count": 1}}
    )
    write_json_atomic(
        details / "review.json",
        {"summary": {"issue_count": 2, "segment_issue_count": 1, "suppressed_segment_count": 1}},
    )

    report = inspect_output(output)

    assert report["success"] is False
    assert report["state"]["quality_state"]["repair_optional"] is True
    assert report["state"]["quality_state"]["suppressed_segment_count"] == 1
    assert any(item["action"] == "inspect_qa_or_optional_repair" for item in report["next_actions"])
