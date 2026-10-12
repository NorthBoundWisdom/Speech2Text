from __future__ import annotations

from pathlib import Path
import wave

import pytest

from atot import audio as audio_module
from atot import pipeline as pipeline_module
from atot.backends import ASRTranscribeOptions
from atot.models import resolve_model
from atot.pipeline import TranscribeOptions, run_transcription
from atot.utils import read_json, write_json_atomic
from atot.validators import validate_output_bundle


def _write_tiny_wav(path: Path, *, sample_rate: int = 16_000, seconds: float = 0.25) -> None:
    frame_count = int(sample_rate * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def test_pipeline_runs_generated_wav_through_real_audio_preparation(tmp_path, monkeypatch) -> None:
    if audio_module.optional_command("ffmpeg") is None:
        pytest.skip("ffmpeg is required for the tiny-WAV integration path")

    calls: list[Path] = []

    class FakeBackend:
        name = "fake-asr"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def __init__(self, *, verbose: bool | None = None) -> None:
            self.verbose = verbose

        def transcribe(self, audio_path: Path, options: ASRTranscribeOptions):
            calls.append(Path(audio_path))
            assert options.model == resolve_model("large-v3-turbo")
            return {"text": "你好", "segments": [{"start": 0.0, "end": 0.2, "text": "你好"}]}

    monkeypatch.setattr(
        pipeline_module,
        "build_backend",
        lambda name, *, recording_json=None, verbose=None: FakeBackend(verbose=verbose),
    )
    audio = tmp_path / "episode.wav"
    _write_tiny_wav(audio)

    run = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="mlx-whisper",
            model="large-v3-turbo",
            language="zh",
            chunk_length=1.0,
            overlap=0.0,
        )
    )

    assert calls == [tmp_path / "out" / "episode" / "chunks" / "chunk_0000.wav"]
    assert run["success"] is True
    assert run["model_alias_or_input"] == "large-v3-turbo"
    assert run["chunk_status_counts"]["transcribed"] == 1
    assert run["quality_metrics"]["corrected_char_count"] == 2
    assert run["quality_metrics"]["timing"]["srt_vtt_compatible"] is True
    assert (tmp_path / "out" / "episode" / "prepared.wav").exists()
    assert (tmp_path / "out" / "episode" / "chunks" / "chunk_0000.wav").exists()
    assert (tmp_path / "out" / "episode" / "run.json").exists()


def test_pipeline_retries_decode_loop_chunk_and_records_audit(tmp_path, monkeypatch) -> None:
    if audio_module.optional_command("ffmpeg") is None:
        pytest.skip("ffmpeg is required for the tiny-WAV integration path")

    calls: list[ASRTranscribeOptions] = []

    class FakeBackend:
        name = "fake-asr"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def transcribe(self, audio_path: Path, options: ASRTranscribeOptions):
            calls.append(options)
            if options.prompt:
                bad_text = "萌" * 120
                return {
                    "text": bad_text,
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 20.0,
                            "text": bad_text,
                            "compression_ratio": 17.5,
                        }
                    ],
                }
            text = "这是一段恢复正常的转写。"
            return {"text": text, "segments": [{"start": 0.0, "end": 0.2, "text": text}]}

    monkeypatch.setattr(
        pipeline_module,
        "build_backend",
        lambda name, *, recording_json=None, verbose=None: FakeBackend(),
    )
    audio = tmp_path / "episode.wav"
    prompt = tmp_path / "prompt.txt"
    _write_tiny_wav(audio)
    prompt.write_text("本期术语：阳萌", encoding="utf-8")

    run = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="mlx-whisper",
            prompt_file=prompt,
            model="large-v3-turbo",
            language="zh",
            chunk_length=1.0,
            overlap=0.0,
        )
    )

    output = tmp_path / "out" / "episode"
    chunk_payload = read_json(output / "chunks" / "chunk_0000.json")
    corrected_text = (output / "transcript.corrected.txt").read_text(encoding="utf-8")

    assert [call.condition_on_previous_text for call in calls] == [True, False, False]
    assert [call.prompt is None for call in calls] == [False, False, True]
    assert "这是一段恢复正常的转写。" in corrected_text
    assert "萌萌萌" not in corrected_text
    assert chunk_payload["asr_decode_guard"]["selected_attempt"] == "no_prompt_no_previous_text"
    assert run["chunks"][0]["decode_guard"] == {
        "triggered": True,
        "selected_attempt": "no_prompt_no_previous_text",
    }
    assert run["chunk_status_counts"]["transcribed"] == 1
    assert validate_output_bundle(output) == []


def test_transcribe_can_run_end_to_end_with_fake_backend(tmp_path) -> None:
    if audio_module.optional_command("ffmpeg") is None:
        pytest.skip("ffmpeg is required for the tiny-WAV integration path")

    audio = tmp_path / "episode.wav"
    _write_tiny_wav(audio)

    run = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="fake",
            chunk_length=1.0,
            overlap=0.0,
        )
    )

    output = tmp_path / "out" / "episode"
    assert run["backend"] == "fake"
    assert run["chunk_status_counts"]["transcribed"] == 1
    assert run["media_probe"]["audio_streams"]
    assert "fake backend" in (output / "transcript.corrected.txt").read_text(encoding="utf-8")
    events = (output / "events.jsonl").read_text(encoding="utf-8")
    assert '"stage": "prepare_audio"' in events
    assert '"event": "chunk"' in events
    assert validate_output_bundle(output) == []


def test_transcribe_can_replay_recording_backend_fixture(tmp_path) -> None:
    if audio_module.optional_command("ffmpeg") is None:
        pytest.skip("ffmpeg is required for the tiny-WAV integration path")

    audio = tmp_path / "episode.wav"
    recording = tmp_path / "recording.json"
    _write_tiny_wav(audio)
    write_json_atomic(
        recording,
        {
            "chunks": [
                {
                    "result": {
                        "text": "录制 fixture",
                        "segments": [{"start": 0.0, "end": 0.2, "text": "录制 fixture"}],
                    }
                }
            ]
        },
    )

    run = run_transcription(
        TranscribeOptions(
            input_path=audio,
            output_dir=tmp_path / "out",
            backend="recording",
            recording_json=recording,
            chunk_length=1.0,
            overlap=0.0,
        )
    )

    assert run["backend"] == "recording"
    assert "录制 fixture" in (tmp_path / "out" / "episode" / "transcript.corrected.txt").read_text(
        encoding="utf-8"
    )
