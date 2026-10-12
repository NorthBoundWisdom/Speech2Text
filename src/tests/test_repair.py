import wave

import pytest

from atot.repair import RepairOptions, build_repair_plan, run_repair
from atot.utils import read_json, write_json_atomic, write_text_atomic


def _wav_duration(path):
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


class FakeBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(self, audio_path, options):
        duration = _wav_duration(audio_path)
        return {
            "text": "修复后的文本",
            "segments": [{"start": 0.0, "end": duration, "text": "修复后的文本"}],
        }


class CorrectionBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(self, audio_path, options):
        duration = _wav_duration(audio_path)
        return {"text": "本课", "segments": [{"start": 0.0, "end": duration, "text": "本课"}]}


class EmptyBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(self, audio_path, options):
        return {"text": "", "segments": []}


class ShortBackend:
    name = "fake"
    supports_prompt = True
    supports_word_timestamps = False
    supports_diarization = False

    def transcribe(self, audio_path, options):
        return {"text": "太短", "segments": [{"start": 0.0, "end": 1.0, "text": "太短"}]}


class RecordingBackend(FakeBackend):
    def __init__(self):
        self.options = []

    def transcribe(self, audio_path, options):
        self.options.append(options)
        return super().transcribe(audio_path, options)


def _write_wav(path, *, seconds=60, rate=16000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"\x00\x00" * seconds * rate)


def _write_repairable_output(tmp_path):
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


def test_build_repair_plan_uses_qa_blockers(tmp_path):
    output = _write_repairable_output(tmp_path)

    plan = build_repair_plan(output, window_padding=5)

    assert plan["windows"]
    assert plan["windows"][0]["start"] == 0.0
    assert "long_segment" in plan["windows"][0]["reasons"]
    assert plan["windows"][0]["source_issue_ids"]


def test_build_repair_plan_clips_windows_to_audio_duration(tmp_path):
    output = _write_repairable_output(tmp_path)
    write_json_atomic(
        output / "qa.json",
        {
            "success": False,
            "summary": {"repair_window_count": 1},
            "issues": [],
            "suggested_repairs": [
                {
                    "type": "rerun_window",
                    "start": 45.0,
                    "end": 80.0,
                    "reason": "low_avg_logprob_segment",
                    "severity": "blocker",
                    "source_issue_ids": ["qa_fixture_001"],
                }
            ],
        },
    )

    plan = build_repair_plan(output, window_padding=5)

    assert plan["windows"][0]["start"] == 45.0
    assert plan["windows"][0]["end"] == 60.0
    assert plan["windows"][0]["duration"] == 15.0
    assert plan["windows"][0]["source_issue_ids"] == ["qa_fixture_001"]


def test_run_repair_plan_only_does_not_require_audio(tmp_path):
    output = _write_repairable_output(tmp_path)
    (output / "prepared.wav").unlink()

    result = run_repair(RepairOptions(output_dir=output, plan_only=True), backend=FakeBackend())

    assert result["plan_only"] is True
    assert (output / "repair" / "repair_plan.json").exists()


def test_run_repair_default_backend_uses_platform_registry(monkeypatch, tmp_path):
    output = _write_repairable_output(tmp_path)
    calls = []

    def build_backend(name):
        calls.append(name)
        return FakeBackend()

    monkeypatch.setattr("atot.repair.default_asr_backend", lambda: "faster-whisper")
    monkeypatch.setattr("atot.repair.build_backend", build_backend)

    result = run_repair(RepairOptions(output_dir=output, window_padding=0))

    assert result["success"] is True
    assert calls == ["faster-whisper"]


def test_run_repair_replaces_bad_window_and_writes_audit_files(tmp_path):
    output = _write_repairable_output(tmp_path)

    result = run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())

    assert result["success"] is True
    assert "修复后的文本" in (output / "transcript.corrected.txt").read_text(encoding="utf-8")
    assert (output / "repair" / "replacement_segments.json").exists()
    assert (output / "repair" / "replacement_segments_001.json").exists()
    assert (output / "repair" / "repair_plan_001.json").exists()
    assert (output / "repair" / "windows" / "repair_0001.corrected.json").exists()
    audit = output / "repair" / "runs" / "repair_run_001" / "windows" / "repair-window-0001"
    assert (audit / "input.wav").exists()
    assert read_json(audit / "decision.json")["action"] == "apply"
    assert read_json(audit / "decision.json")["selected_candidate"] == "default"
    assert (audit / "candidates" / "default" / "corrected.json").exists()
    assert (audit / "candidates" / "anti_repeat_zh_podcast" / "corrected.json").exists()
    assert read_json(audit / "qa_before_window.json")["summary"]["source_issue_ids"]
    assert read_json(audit / "qa_after_window.json")["success"] is True
    assert "修复后的文本" in (audit / "replacement.diff.md").read_text(encoding="utf-8")
    assert (output / "repair" / "diff_001.md").exists()
    assert read_json(output / "repair" / "repair_decision.json")["status"] == "applied"
    assert (output / "repair" / "pre_repair_snapshot_001.json").exists()
    assert (output / "repair" / "post_repair_snapshot_001.json").exists()
    repair_run = read_json(output / "repair" / "repair_run_001.json")
    assert repair_run["pre_segment_digest"] != repair_run["post_segment_digest"]
    assert repair_run["applied_window_count"] == 1
    assert repair_run["rejected_window_count"] == 0
    assert read_json(output / "run.json")["repair"]["applied"] is True
    assert (output / "manifest.json").exists()


def test_run_repair_applies_glossary_to_window_replacements(tmp_path):
    output = _write_repairable_output(tmp_path)
    write_json_atomic(output / "glossary.effective.json", {"safe_global": {"本课": "本科"}})

    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=CorrectionBackend())

    corrected = read_json(output / "repair" / "windows" / "repair_0001.corrected.json")
    replacements = read_json(output / "repair" / "replacement_segments.json")
    assert corrected["segments"][0]["text"] == "本科"
    assert corrected["corrections"][0]["kind"] == "safe_global"
    assert replacements["segments"][0]["text"] == "本科"
    assert "本科" in (output / "repair" / "diff_001.md").read_text(encoding="utf-8")


def test_run_repair_rejects_empty_window_replacement(tmp_path):
    output = _write_repairable_output(tmp_path)

    result = run_repair(RepairOptions(output_dir=output, window_padding=0), backend=EmptyBackend())

    repair_run = result["repair_run"]
    assert repair_run["replacement_segment_count"] == 0
    assert repair_run["applied_window_count"] == 0
    assert repair_run["rejected_window_count"] == 1
    decision = read_json(
        output
        / "repair"
        / "runs"
        / "repair_run_001"
        / "windows"
        / "repair-window-0001"
        / "decision.json"
    )
    assert decision["action"] == "reject"
    assert read_json(output / "repair" / "repair_decision.json")["status"] == "rejected"
    assert read_json(output / "run.json")["repair"]["applied"] is False


def test_run_repair_arbitration_rejects_time_coverage_loss(tmp_path):
    output = _write_repairable_output(tmp_path)

    result = run_repair(RepairOptions(output_dir=output, window_padding=0), backend=ShortBackend())

    repair_run = result["repair_run"]
    assert repair_run["applied_window_count"] == 0
    decision = read_json(
        output
        / "repair"
        / "runs"
        / "repair_run_001"
        / "windows"
        / "repair-window-0001"
        / "decision.json"
    )
    assert decision["action"] == "reject"
    candidates = {item["id"]: item for item in decision["candidates"]}
    assert "time_coverage_loss" in candidates["default"]["reasons"]


def test_run_repair_accepts_explicit_candidate_profile_matrix(tmp_path):
    output = _write_repairable_output(tmp_path)

    result = run_repair(
        RepairOptions(
            output_dir=output, window_padding=0, candidate_profiles=("default", "repair_strict")
        ),
        backend=FakeBackend(),
    )

    decision = result["repair_run"]["window_decisions"][0]["decision"]
    assert {item["id"] for item in decision["candidates"]} == {
        "baseline",
        "default",
        "repair_strict",
    }


def test_run_repair_does_not_pass_audit_fields_as_decode_options(tmp_path):
    output = _write_repairable_output(tmp_path)
    backend = RecordingBackend()

    run_repair(RepairOptions(output_dir=output, window_padding=0), backend=backend)

    assert backend.options
    assert all(options.extra_decode_options == {} for options in backend.options)
    audit = output / "repair" / "runs" / "repair_run_001" / "windows" / "repair-window-0001"
    assert read_json(audit / "candidates" / "default" / "corrected.json")["profile"] == "default"


def test_run_repair_can_filter_to_one_window(tmp_path):
    output = _write_repairable_output(tmp_path)

    result = run_repair(
        RepairOptions(output_dir=output, window_padding=0, window_id="repair_0001"),
        backend=FakeBackend(),
    )

    assert result["plan"]["requested_window_id"] == "repair_0001"
    assert len(result["plan"]["windows"]) == 1


def test_run_repair_rejects_invalid_audio_duration_payload(tmp_path):
    output = _write_repairable_output(tmp_path)
    raw = read_json(output / "raw.json")
    raw["audio_duration"] = {"bad": "type"}
    write_json_atomic(output / "raw.json", raw)

    with pytest.raises(ValueError, match="audio_duration"):
        run_repair(RepairOptions(output_dir=output, window_padding=0), backend=FakeBackend())
