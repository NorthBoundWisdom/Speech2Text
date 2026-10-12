from atot.subtitles import (
    SubtitleCue,
    cues_to_srt,
    segments_to_cues,
    segments_to_srt,
    validate_srt_text,
)


def test_segments_to_cues_splits_long_segment_by_text_and_duration():
    segments = [
        {
            "start": 0.0,
            "end": 18.0,
            "text": "第一句很长，需要拆开。第二句也很长，需要继续拆开。第三句仍然很长，需要保持字幕可读。",
        }
    ]

    cues = segments_to_cues(segments, max_duration=7.0, max_chars=20, max_line_chars=12)

    assert len(cues) >= 3
    assert cues[0].start == 0.0
    assert cues[-1].end == 18.0
    assert all(cue.end > cue.start for cue in cues)
    assert all(len(line) <= 12 for cue in cues for line in cue.text.splitlines())


def test_validate_srt_text_flags_index_jump_and_long_text():
    srt = "1\n00:00:00,000 --> 00:00:01,000\n你好\n\n3\n00:00:01,000 --> 00:00:02,000\n" + "长" * 90

    issues = validate_srt_text(srt, max_chars=80)

    assert {issue["type"] for issue in issues} >= {
        "srt_index_jump",
        "long_subtitle",
        "long_subtitle_line",
    }


def test_segments_to_srt_outputs_continuous_indices_after_skipping_empty_segments():
    srt = segments_to_srt(
        [
            {"start": 0.0, "end": 1.0, "text": "你好"},
            {"start": 1.0, "end": 2.0, "text": ""},
            {"start": 2.0, "end": 3.0, "text": "再见"},
        ]
    )

    assert "\n2\n00:00:02,000 --> 00:00:03,000\n" in srt
    assert validate_srt_text(srt) == []


def test_cues_to_srt_outputs_continuous_indices_after_skipping_empty_cues():
    srt = cues_to_srt(
        [
            SubtitleCue(index=1, start=0.0, end=1.0, text="你好"),
            SubtitleCue(index=2, start=1.0, end=2.0, text=""),
            SubtitleCue(index=3, start=2.0, end=3.0, text="再见"),
        ]
    )

    assert "\n2\n00:00:02,000 --> 00:00:03,000\n" in srt
    assert validate_srt_text(srt) == []


def test_segments_to_cues_can_preserve_unwrapped_text_for_translation():
    cues = segments_to_cues(
        [{"start": 0.0, "end": 1.0, "text": "transformative technology"}],
        max_line_chars=8,
        wrap_text=False,
    )

    assert cues[0].text == "transformative technology"


def test_segments_to_cues_does_not_split_numeric_commas():
    cues = segments_to_cues(
        [{"start": 0.0, "end": 4.0, "text": "I took sales from 750,000 to 34 million."}],
        max_chars=24,
        wrap_text=False,
    )

    assert all(not cue.text.endswith("750,") for cue in cues)
    assert any("750,000" in cue.text for cue in cues)


def test_segments_to_cues_splits_latin_text_on_word_boundaries():
    cues = segments_to_cues(
        [{"start": 0.0, "end": 4.0, "text": "transformative technology creates durable companies"}],
        max_chars=24,
        wrap_text=False,
    )

    assert [cue.text for cue in cues] == ["transformative technology", "creates durable companies"]
