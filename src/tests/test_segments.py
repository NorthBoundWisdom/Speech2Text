from atot.segments import canonicalize_segments, coverage_metrics, segment_digest, timeline_gaps


def test_canonicalize_segments_is_content_agnostic_and_monotonic():
    segments = [
        {"start": 5.0, "end": 5.5, "text": " 后面 "},
        {"start": 1.0, "end": 0.5, "text": "前面"},
        {"start": 2.0, "end": 3.0, "text": "   "},
    ]

    normalized = canonicalize_segments(segments)

    assert [item["text"] for item in normalized] == ["前面", "后面"]
    assert normalized[0]["start"] == 1.0
    assert normalized[0]["end"] > normalized[0]["start"]
    assert normalized[1]["id"] == 1


def test_timeline_gaps_and_coverage_metrics_are_generic():
    segments = [
        {"start": 0.0, "end": 10.0, "text": "a"},
        {"start": 50.0, "end": 60.0, "text": "b"},
    ]

    gaps = timeline_gaps(segments, audio_duration=90.0, min_gap=20.0)
    coverage = coverage_metrics(segments, audio_duration=90.0)

    assert [gap["duration"] for gap in gaps] == [40.0, 30.0]
    assert coverage["covered_seconds"] == 20.0
    assert coverage["uncovered_seconds"] == 70.0
    assert segment_digest(segments) == segment_digest(list(segments))
