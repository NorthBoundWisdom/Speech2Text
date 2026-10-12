from __future__ import annotations

from pathlib import Path

from atot.asr_guard import RETRY_TEMPERATURES, assess_asr_result, transcribe_with_decode_guard
from atot.backends import ASRTranscribeOptions


def _segment(text: str, *, compression_ratio: float = 1.2) -> dict[str, object]:
    return {
        "start": 0.0,
        "end": 20.0,
        "text": text,
        "compression_ratio": compression_ratio,
    }


def test_assess_asr_result_flags_runaway_repetition_and_compression() -> None:
    bad_text = "萌" * 120

    health = assess_asr_result(
        {"text": bad_text, "segments": [_segment(bad_text, compression_ratio=15.7)]}
    )

    assert health.should_retry is True
    assert health.high_compression_segments == 1
    assert health.repeated_segments == 1
    assert health.max_compression_ratio == 15.7
    assert set(health.reasons) == {"high_compression_segment", "repeated_phrase"}


def test_assess_asr_result_flags_fullwidth_marker_noise() -> None:
    noisy_text = "这是一段清晰语音Ｚ但是解码插入了标记Ｚ我们继续说产品Ｚ" * 8

    health = assess_asr_result({"text": noisy_text, "segments": [_segment(noisy_text)]})

    assert health.should_retry is True
    assert health.marker_noise_chars >= 20
    assert "marker_noise" in health.reasons


def test_assess_asr_result_flags_symbol_marker_noise() -> None:
    noisy_text = "这是一段清晰语音※但是解码插入了符号※我们继续说产品※" * 8

    health = assess_asr_result({"text": noisy_text, "segments": [_segment(noisy_text)]})

    assert health.should_retry is True
    assert health.marker_noise_chars >= 20
    assert "marker_noise" in health.reasons


def test_transcribe_with_decode_guard_selects_healthiest_retry() -> None:
    calls: list[ASRTranscribeOptions] = []

    class FakeBackend:
        name = "fake-asr"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def transcribe(self, audio_path: str | Path, options: ASRTranscribeOptions):
            calls.append(options)
            if options.prompt:
                bad_text = "７" * 120
                return {"text": bad_text, "segments": [_segment(bad_text, compression_ratio=18.0)]}
            text = "这是一段正常清晰的中文转写。"
            return {"text": text, "segments": [_segment(text)]}

    guarded = transcribe_with_decode_guard(
        FakeBackend(),
        Path("chunk.wav"),
        ASRTranscribeOptions(
            model="large-v3-turbo",
            prompt="本期术语：阳萌",
            condition_on_previous_text=True,
            temperature=0.0,
        ),
    )

    assert guarded.result["text"] == "这是一段正常清晰的中文转写。"
    assert guarded.audit is not None
    assert guarded.audit["selected_attempt"] == "no_prompt_no_previous_text"
    assert [attempt["name"] for attempt in guarded.audit["attempts"]] == [
        "primary",
        "no_previous_text",
        "no_prompt_no_previous_text",
    ]
    assert [call.condition_on_previous_text for call in calls] == [True, False, False]
    assert [call.prompt for call in calls] == ["本期术语：阳萌", "本期术语：阳萌", None]
    assert calls[1].temperature == RETRY_TEMPERATURES
    assert calls[2].temperature == RETRY_TEMPERATURES


def test_transcribe_with_decode_guard_does_not_retry_healthy_output() -> None:
    calls: list[ASRTranscribeOptions] = []

    class FakeBackend:
        name = "fake-asr"
        supports_prompt = True
        supports_word_timestamps = True
        supports_diarization = False

        def transcribe(self, audio_path: str | Path, options: ASRTranscribeOptions):
            calls.append(options)
            text = "稳定的正常转写。"
            return {"text": text, "segments": [_segment(text)]}

    guarded = transcribe_with_decode_guard(
        FakeBackend(),
        Path("chunk.wav"),
        ASRTranscribeOptions(
            model="large-v3-turbo", prompt="术语", condition_on_previous_text=True
        ),
    )

    assert guarded.result["text"] == "稳定的正常转写。"
    assert guarded.audit is None
    assert len(calls) == 1
