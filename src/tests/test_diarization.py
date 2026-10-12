from atot.diarization import DiarizeOptions, infer_speakers, run_diarization
from atot.utils import read_json, write_json_atomic


def test_infer_speakers_marks_segments_as_text_inferred():
    segments = [
        {"start": 0.0, "end": 1.0, "text": "主持人开场"},
        {"start": 4.0, "end": 5.0, "text": "嘉宾回应"},
    ]

    inferred = infer_speakers(segments)

    assert inferred[0]["speaker"] == "host_inferred"
    assert inferred[1]["speaker"] == "guest_inferred"
    assert inferred[0]["speaker_source"] == "text_inferred"


def test_run_diarization_writes_independent_outputs(tmp_path):
    output = tmp_path / "output"
    details = output
    write_json_atomic(
        details / "corrected.json",
        {"segments": [{"start": 0.0, "end": 1.0, "text": "主持人开场"}], "text": "主持人开场"},
    )
    write_json_atomic(details / "run.json", {"success": True})

    result = run_diarization(DiarizeOptions(output_dir=output))

    assert result["success"] is True
    assert (details / "speakers.inferred.json").exists()
    assert (details / "transcript.speaker.md").exists()
    assert read_json(details / "run.json")["diarization"]["mode"] == "inferred"
