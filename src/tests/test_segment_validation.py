from pathlib import Path

from atot.segment_validation import first_segment_list, validate_segment_payload_file
from atot.utils import write_json_atomic


def test_validate_segment_payload_rejects_bool_timing(tmp_path: Path):
    payload = tmp_path / "segments.json"
    write_json_atomic(payload, {"segments": [{"start": True, "end": 1.0, "text": "hello"}]})

    segments, errors = validate_segment_payload_file(payload)

    assert segments
    assert any("start must be numeric" in error for error in errors)


def test_first_segment_list_prefers_first_non_empty_payload():
    assert first_segment_list(
        {"segments": []}, {"segments": [{"start": 0, "end": 1, "text": "ok"}]}
    ) == [{"start": 0, "end": 1, "text": "ok"}]
