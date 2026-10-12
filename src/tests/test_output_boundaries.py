from atot.formats import dedupe_segments
from atot.utils import read_json
from atot.writer import write_run_info, write_transcript_outputs


def test_write_run_info_includes_run_json_in_output_files(tmp_path):
    run = write_run_info(tmp_path, {"success": True})

    assert run["output_files"]["run.json"] == str(tmp_path / "run.json")
    assert run["output_files"]["run.log"] == str(tmp_path / "run.log")
    assert (tmp_path / "run.json").exists()
    assert (tmp_path / "run.log").exists()
    manifest = read_json(tmp_path / "manifest.json")
    assert manifest["schema_version"] == 1
    assert {item["path"] for item in manifest["artifacts"]} == {"run.json", "run.log"}


def test_transcript_outputs_keep_only_primary_files_at_top_level(tmp_path):
    job_dir = tmp_path / "output"
    input_path = tmp_path / "input" / "episode.m4a"
    input_path.parent.mkdir()
    input_path.write_bytes(b"audio")
    (input_path.parent / "episode.json").write_text(
        '{"title": "Episode", "audio_path": "/tmp/private.wav"}', encoding="utf-8"
    )
    segment = {"start": 0.0, "end": 1.0, "text": "你好。"}

    write_transcript_outputs(
        job_dir,
        input_path=input_path,
        model="large-v3-turbo",
        language="zh",
        audio_duration=1.0,
        chunk_payloads=[],
        raw_segments=[segment],
        corrected_segments=[segment],
        corrected_text="你好。",
        review={"summary": {}, "issues": []},
    )

    top_level = {path.name for path in job_dir.iterdir()}

    assert "details" not in top_level
    assert (job_dir / "raw.json").exists()
    assert (job_dir / "corrected.json").exists()
    assert (job_dir / "transcript.corrected.txt").exists()
    assert (job_dir / "transcript.md").exists()
    assert (job_dir / "transcript.timestamped.md").exists()
    assert (job_dir / "readable_transformations.json").exists()
    assert (job_dir / "transcript.srt").exists()
    assert (job_dir / "transcript.vtt").exists()
    assert not (tmp_path / "products").exists()


def test_dedupe_segments_removes_short_segment_inside_long_boundary_segment():
    segments = [
        {"start": 3590.0, "end": 3620.0, "text": "我就每次不太会把它收起来，然后明天继续做。"},
        {"start": 3590.4, "end": 3596.0, "text": "我就每次不太会把它收起来"},
        {"start": 3620.0, "end": 3630.0, "text": "新的内容继续。"},
    ]

    deduped = dedupe_segments(segments)

    assert [segment["text"] for segment in deduped] == [
        "我就每次不太会把它收起来，然后明天继续做。",
        "新的内容继续。",
    ]
