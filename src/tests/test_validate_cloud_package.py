from pathlib import Path
import pytest

from atot.cloud.output_state import CloudOutputOptions
from atot.cloud.prepare import CloudPrepareOptions, prepare_cloud_input
from atot.cloud.summary_outputs import write_cloud_summary
from atot.utils import read_json, write_json_atomic, write_text_atomic
from atot.validators import is_relative_safe
from scripts.validate_cloud_package import (
    validate_cloud_input,
    validate_cloud_outputs,
    validate_cloud_package,
)


def _write_output(tmp_path: Path) -> Path:
    output = tmp_path / "episode" / "output"
    details = output
    write_json_atomic(
        details / "corrected.json",
        {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "第一段"},
                {"start": 1200.0, "end": 1202.0, "text": "第二段"},
            ]
        },
    )
    write_json_atomic(details / "qa.json", {"success": True, "issues": []})
    write_text_atomic(details / "qa.md", "# QA\n\nStatus: PASS\n")
    write_json_atomic(details / "review.json", {"needs_human_confirmation": []})
    write_json_atomic(details / "glossary.effective.json", {"safe_global": []})
    write_json_atomic(
        details / "run.json", {"audio_duration": 1202.0, "model_alias_or_input": "large-v3-turbo"}
    )
    return output


def test_validate_cloud_package_accepts_prepared_input_and_outputs(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output, chunk_minutes=10.0))
    write_cloud_summary(CloudOutputOptions(output_dir=output))

    assert validate_cloud_input(output) == []
    assert validate_cloud_outputs(output) == []
    assert validate_cloud_package(output, mode="both") == []


def test_validate_cloud_input_rejects_media_and_local_redaction_map_manifest_entries(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output, redact="pii"))
    input_dir = output / "cloud" / "input"
    write_text_atomic(input_dir / "leaked.wav", "not actually audio")
    manifest = read_json(input_dir / "manifest.json")
    manifest["input_files"].extend(["redaction_map.local.json", "leaked.wav"])
    write_json_atomic(input_dir / "manifest.json", manifest)

    errors = validate_cloud_input(input_dir)

    assert any(
        "local-only file `redaction_map.local.json` must not be listed" in error for error in errors
    )
    assert any("media file `leaked.wav` must not be listed" in error for error in errors)


def test_validate_cloud_outputs_rejects_input_package_entries(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    write_cloud_summary(CloudOutputOptions(output_dir=output))
    manifest = read_json(output / "cloud" / "manifest.json")
    manifest["output_files"].append("input/transcript.for_cloud.md")
    write_json_atomic(output / "cloud" / "manifest.json", manifest)

    errors = validate_cloud_outputs(output)

    assert any(
        "must not list input package file `input/transcript.for_cloud.md`" in error
        for error in errors
    )


def test_validate_cloud_outputs_rejects_standard_json_schema_errors(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    write_cloud_summary(CloudOutputOptions(output_dir=output))
    write_json_atomic(output / "cloud" / "terms.json", {"terms": [{}]})
    write_json_atomic(output / "cloud" / "title_candidates.json", {"candidates": [{}]})

    errors = validate_cloud_outputs(output)

    assert any("terms[0].term must be a non-empty string" in error for error in errors)
    assert any("candidates[0].title must be a non-empty string" in error for error in errors)


def test_validate_cloud_outputs_rejects_incomplete_polish_patches(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    write_cloud_summary(CloudOutputOptions(output_dir=output))
    cloud = output / "cloud"
    write_json_atomic(
        cloud / "transcript.polish_suggestions.json",
        {"patches": [{"original": "第一段", "suggested": "第一段。"}]},
    )
    manifest = read_json(cloud / "manifest.json")
    manifest["output_files"].append("transcript.polish_suggestions.json")
    write_json_atomic(cloud / "manifest.json", manifest)

    errors = validate_cloud_outputs(output)

    assert any("patches[0].start must be a non-empty string" in error for error in errors)
    assert any("patches[0].risk must be a non-empty string" in error for error in errors)


def test_validate_cloud_input_rejects_file_manifest_hash_mismatch(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    input_dir = output / "cloud" / "input"
    write_text_atomic(input_dir / "transcript.for_cloud.md", "tampered transcript\n")

    errors = validate_cloud_input(input_dir)

    assert any(
        "input_file_manifest `transcript.for_cloud.md` sha256 does not match file" in error
        for error in errors
    )


def test_validate_cloud_input_rejects_missing_file_manifest_entry(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    input_dir = output / "cloud" / "input"
    manifest = read_json(input_dir / "manifest.json")
    manifest["input_file_manifest"] = [
        row for row in manifest["input_file_manifest"] if row["path"] != "transcript.for_cloud.md"
    ]
    write_json_atomic(input_dir / "manifest.json", manifest)

    errors = validate_cloud_input(input_dir)

    assert any(
        "input_file_manifest missing file `transcript.for_cloud.md`" in error for error in errors
    )


def test_validate_cloud_input_rejects_source_manifest_hash_mismatch(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    input_dir = output / "cloud" / "input"
    write_json_atomic(
        output / "corrected.json", {"segments": [{"start": 0.0, "end": 1.0, "text": "tampered"}]}
    )

    errors = validate_cloud_input(input_dir)

    assert any(
        "source_file_manifest `corrected.json` sha256 does not match source file" in error
        for error in errors
    )


def test_validate_cloud_input_rejects_symlink_escape(tmp_path):
    output = _write_output(tmp_path)
    prepare_cloud_input(CloudPrepareOptions(output_dir=output))
    input_dir = output / "cloud" / "input"
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    link = input_dir / "outside.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this filesystem")
    manifest = read_json(input_dir / "manifest.json")
    manifest["input_files"].append("outside.json")
    write_json_atomic(input_dir / "manifest.json", manifest)

    errors = validate_cloud_input(input_dir)

    assert any("input_files` contains unsafe path `outside.json`" in error for error in errors)


def test_relative_path_safety_allows_unicode_but_rejects_backslash_and_empty():
    assert is_relative_safe("资料/转写.json") is True
    assert is_relative_safe("") is False
    assert is_relative_safe("..\\secret.json") is False


def test_relative_path_safety_rejects_symlink_escape(tmp_path):
    base = tmp_path / "base"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    link = base / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available on this filesystem")

    assert is_relative_safe("linked/file.json", base_dir=base) is False
    assert is_relative_safe("safe/file.json", base_dir=base) is True
