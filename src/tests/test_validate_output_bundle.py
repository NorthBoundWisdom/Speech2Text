from copy import deepcopy
from pathlib import Path
import wave

from atot.utils import read_json, write_json_atomic, write_text_atomic
from scripts.validate_output_bundle import REQUIRED_FILES, validate_output_bundle


def _write_valid_output_bundle(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    details = output
    fixture = read_json(Path("src/tests/fixtures/run.sample.json"))
    run = deepcopy(fixture)
    run["job_dir"] = str(output)
    run["input_path"] = "process/0000/sample/episode.m4a"
    run["output_files"] = {name: str(output / name) for name in sorted(REQUIRED_FILES)}

    segments = [{"start": 0.0, "end": 1.0, "text": "你好世界"}]
    write_json_atomic(details / "raw.json", {"segments": segments, "text": "你好世界"})
    write_json_atomic(details / "corrected.json", {"segments": segments, "text": "你好世界"})
    write_text_atomic(details / "transcript.raw.txt", "你好世界\n")
    write_text_atomic(details / "transcript.corrected.txt", "你好世界\n")
    write_text_atomic(output / "transcript.readable.md", "# Transcript\n\n你好世界\n")
    write_text_atomic(details / "transcript.md", "# Transcript\n\n你好世界\n")
    write_text_atomic(details / "transcript.timestamped.md", "[00:00:00] 你好世界\n")
    write_text_atomic(details / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n你好世界\n")
    write_text_atomic(
        details / "transcript.vtt", "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n你好世界\n"
    )
    write_json_atomic(details / "corrections.json", {"corrections": []})
    write_json_atomic(details / "chunks_manifest.json", {"chunks": []})
    write_json_atomic(details / "prepared.meta.json", {"schema_version": 1})
    with wave.open(str(details / "prepared.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)
    write_json_atomic(details / "qa.json", {"success": True})
    write_text_atomic(details / "qa.md", "# QA\n\nPASS\n")
    write_json_atomic(details / "review.json", {"summary": {}})
    write_text_atomic(details / "review.md", "# Review\n")
    write_json_atomic(details / "glossary.effective.json", {})
    write_text_atomic(details / "run.log", "success=true\n")
    write_json_atomic(details / "run.json", run)
    return output


def test_validate_output_bundle_accepts_complete_bundle(tmp_path):
    output = _write_valid_output_bundle(tmp_path)

    assert validate_output_bundle(output) == []


def test_validate_output_bundle_rejects_missing_required_file(tmp_path):
    output = _write_valid_output_bundle(tmp_path)
    (output / "transcript.readable.md").unlink()

    errors = validate_output_bundle(output)

    assert any("transcript.readable.md" in error and "missing" in error for error in errors)


def test_validate_output_bundle_rejects_stale_run_output_path(tmp_path):
    output = _write_valid_output_bundle(tmp_path)
    run = read_json(output / "run.json")
    run["output_files"]["transcript.srt"] = "output/transcript.srt"
    write_json_atomic(output / "run.json", run)

    errors = validate_output_bundle(output)

    assert any("output_files.transcript.srt must equal" in error for error in errors)


def test_validate_output_bundle_rejects_corrected_text_mismatch(tmp_path):
    output = _write_valid_output_bundle(tmp_path)
    write_text_atomic(output / "transcript.corrected.txt", "别的文本\n")

    errors = validate_output_bundle(output)

    assert any("does not contain corrected segment text" in error for error in errors)
