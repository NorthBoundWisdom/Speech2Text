import wave
from pathlib import Path

from atot.repair import RepairOptions, run_repair
from atot.utils import read_json, write_json_atomic, write_text_atomic
from scripts.validate_repair_artifacts import validate_repair_artifacts


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


class FakeBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(self, audio_path, options):
        duration = _wav_duration(Path(audio_path))
        return {
            "text": "修复后的文本",
            "segments": [{"start": 0.0, "end": duration, "text": "修复后的文本"}],
        }


def _write_wav(path: Path, *, seconds: int = 60, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * seconds * rate)


def _write_repairable_output(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    details = output
    segments = [
        {"start": 0.0, "end": 40.0, "text": "坏坏坏"},
        {"start": 45.0, "end": 46.0, "text": "后文"},
    ]
    write_json_atomic(
        details / "raw.json",
        {"input_path": "episode.m4a", "segments": segments, "audio_duration": 60.0},
    )
    write_json_atomic(details / "corrected.json", {"segments": segments, "text": "坏坏坏\n后文"})
    write_json_atomic(details / "glossary.effective.json", {})
    write_json_atomic(
        details / "run.json",
        {"success": True, "job_dir": str(output), "language": "zh", "prompt": "提示"},
    )
    write_text_atomic(output / "transcript.srt", "1\n00:00:00,000 --> 00:00:40,000\n坏坏坏\n")
    _write_wav(details / "prepared.wav")
    return output


def test_validate_repair_artifacts_accepts_plan_only(tmp_path):
    output = _write_repairable_output(tmp_path)
    run_repair(RepairOptions(output_dir=output, plan_only=True), backend=FakeBackend())

    assert validate_repair_artifacts(output) == []


def test_validate_repair_artifacts_accepts_completed_repair(tmp_path):
    output = _write_repairable_output(tmp_path)
    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())

    assert validate_repair_artifacts(output) == []
    assert read_json(output / "run.json")["repair"]["repair_run_ids"] == ["repair_run_001.json"]


def test_validate_repair_artifacts_accepts_versioned_replacement_segments(tmp_path):
    output = _write_repairable_output(tmp_path)
    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())
    repair = output / "repair"
    run = read_json(repair / "repair_run_001.json")
    run["repair_id"] = 2
    run["replacement_segment_count"] = 2
    write_json_atomic(repair / "repair_run_002.json", run)
    write_json_atomic(repair / "repair_plan_002.json", read_json(repair / "repair_plan_001.json"))
    segment = {"start": 10.0, "end": 11.0, "text": "第二段"}
    write_json_atomic(
        repair / "replacement_segments_002.json",
        {"segments": [segment, {**segment, "start": 12.0, "end": 13.0}]},
    )
    write_text_atomic(repair / "diff_002.md", (repair / "diff_001.md").read_text(encoding="utf-8"))
    write_json_atomic(
        repair / "repair_decision_002.json", read_json(repair / "repair_decision_001.json")
    )
    write_json_atomic(
        repair / "pre_repair_snapshot_002.json", read_json(repair / "pre_repair_snapshot_001.json")
    )
    write_json_atomic(
        repair / "post_repair_snapshot_002.json",
        read_json(repair / "post_repair_snapshot_001.json"),
    )
    run_json = read_json(output / "run.json")
    run_json["repair"]["repair_run_ids"].append("repair_run_002.json")
    write_json_atomic(output / "run.json", run_json)

    assert validate_repair_artifacts(output) == []


def test_validate_repair_artifacts_rejects_missing_window_corrected_json(tmp_path):
    output = _write_repairable_output(tmp_path)
    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())
    (output / "repair" / "windows" / "repair_0001.corrected.json").unlink()

    errors = validate_repair_artifacts(output)

    assert any("repair_0001.corrected.json" in error for error in errors)


def test_validate_repair_artifacts_rejects_stale_run_json_ids(tmp_path):
    output = _write_repairable_output(tmp_path)
    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())
    run_json = read_json(output / "run.json")
    run_json["repair"]["repair_run_ids"] = []
    write_json_atomic(output / "run.json", run_json)

    errors = validate_repair_artifacts(output)

    assert any("missing repair run id `repair_run_001.json`" in error for error in errors)
