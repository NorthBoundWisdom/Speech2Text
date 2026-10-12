from atot.quality import build_quality_metrics


def test_build_quality_metrics_summarizes_review_and_corrections():
    metrics = build_quality_metrics(
        raw_segments=[
            {"text": "你好你好"},
            {"text": "我说,我说,我说,我说,我说,我说"},
        ],
        corrected_segments=[
            {"text": "你好你好"},
            {"text": ""},
        ],
        corrections=[
            {
                "from": "我说,我说,我说,我说,我说,我说",
                "to": "",
                "count": 6,
                "kind": "asr_runaway_repetition",
            },
            {"from": "博客", "to": "播客", "count": 1, "kind": "glossary"},
        ],
        review={"summary": {"issue_count": 1, "segment_issue_count": 2}},
    )

    assert metrics["raw_segment_count"] == 2
    assert metrics["corrected_segment_count"] == 2
    assert metrics["empty_corrected_segment_count"] == 1
    assert metrics["correction_count"] == 7
    assert metrics["correction_kind_counts"] == {"asr_runaway_repetition": 6, "glossary": 1}
    assert metrics["review_issue_count"] == 1
    assert metrics["review_segment_issue_count"] == 2
    assert metrics["timing"]["missing_timing_segment_count"] == 2
    assert metrics["timing"]["srt_vtt_compatible"] is False


def test_build_quality_metrics_reports_timestamp_compatibility():
    metrics = build_quality_metrics(
        raw_segments=[
            {"start": 0.0, "end": 1.0, "text": "第一句"},
            {"start": 1.0, "end": 2.0, "text": "第二句"},
        ],
        corrected_segments=[
            {"start": 0.0, "end": 1.0, "text": "第一句"},
            {"start": 1.0, "end": 2.0, "text": "第二句"},
        ],
        corrections=[],
        review={"summary": {"issue_count": 0, "segment_issue_count": 0}},
    )

    assert metrics["timing"]["timed_segment_count"] == 2
    assert metrics["timing"]["invalid_timing_segment_count"] == 0
    assert metrics["timing"]["srt_vtt_compatible"] is True
    assert metrics["timeline"]["duration_seconds"] == 2.0
    assert metrics["timeline"]["max_gap_seconds"] == 0.0
    assert metrics["chars_per_minute"] == 180.0


def test_build_quality_metrics_rejects_synthetic_or_overlapping_timestamps():
    metrics = build_quality_metrics(
        raw_segments=[],
        corrected_segments=[
            {"start": 0.0, "end": 1.0, "text": "第一句", "_timing_source": "synthetic"},
            {"start": 0.5, "end": 2.0, "text": "第二句"},
        ],
        corrections=[],
        review={"summary": {"issue_count": 0, "segment_issue_count": 0}},
    )

    assert metrics["timing"]["missing_timing_segment_count"] == 1
    assert metrics["timing"]["overlapping_timing_segment_count"] == 1
    assert metrics["timing"]["srt_vtt_compatible"] is False
