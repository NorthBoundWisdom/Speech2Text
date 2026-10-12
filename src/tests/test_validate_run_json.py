from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

from atot.utils import read_json


def _load_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "validate_run_json.py"
    spec = importlib.util.spec_from_file_location("validate_run_json", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fixture() -> dict:
    return read_json(Path(__file__).resolve().parent / "fixtures" / "run.sample.json")


def test_sample_run_json_fixture_matches_schema() -> None:
    validator = _load_script()

    assert validator.validate_run_json_payload(_fixture()) == []


def test_run_json_schema_requires_quality_and_output_keys() -> None:
    validator = _load_script()
    payload = _fixture()
    del payload["quality_metrics"]["timing"]["srt_vtt_compatible"]
    del payload["output_files"]["run.log"]
    del payload["output_files"]["transcript.readable.md"]
    del payload["output_files"]["qa.json"]

    errors = validator.validate_run_json_payload(payload)

    assert "missing timing metric `srt_vtt_compatible`" in errors
    assert "missing output file key `run.log`" in errors
    assert "missing output file key `transcript.readable.md`" in errors
    assert "missing output file key `qa.json`" in errors


def test_run_json_schema_rejects_hash_mismatches() -> None:
    validator = _load_script()
    payload = copy.deepcopy(_fixture())
    payload["chunk_layout"]["overlap"] = 5.0

    errors = validator.validate_run_json_payload(payload)

    assert "`chunk_layout_sha256` does not match `chunk_layout`" in errors


def test_run_json_schema_rejects_cache_identity_mismatches() -> None:
    validator = _load_script()
    payload = copy.deepcopy(_fixture())
    payload["transcription_fingerprint"]["chunk_layout_sha256"] = "0" * 64

    errors = validator.validate_run_json_payload(payload)

    assert "`transcription_fingerprint_sha256` does not match `transcription_fingerprint`" in errors
    assert (
        "`transcription_fingerprint.chunk_layout_sha256 vs chunk_layout_sha256` mismatch" in errors
    )


def test_run_json_schema_requires_backend_qa_repair_and_cloud_contracts() -> None:
    validator = _load_script()
    payload = copy.deepcopy(_fixture())
    del payload["backend_capabilities"]["supports_diarization"]
    del payload["qa"]["blocking_issue_count"]
    payload["repair"]["repair_run_ids"] = [1]
    payload["cloud"]["audio_uploaded"] = True

    errors = validator.validate_run_json_payload(payload)

    assert "missing backend capability `supports_diarization`" in errors
    assert "missing qa summary key `blocking_issue_count`" in errors
    assert "`repair.repair_run_ids` must be a list of strings" in errors
    assert "`cloud.audio_uploaded` must be false" in errors


def test_run_json_validator_cli_reports_success(capsys) -> None:
    validator = _load_script()
    fixture = Path(__file__).resolve().parent / "fixtures" / "run.sample.json"

    assert validator.main([str(fixture)]) == 0
    assert "run.sample.json: ok" in capsys.readouterr().out
