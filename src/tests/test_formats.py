from atot.formats import (
    enforce_monotonic_timeline,
    merge_chunk_payloads,
    merge_chunk_payloads_with_decisions,
    segments_to_srt,
    segments_to_vtt,
)


def test_merge_chunk_payloads_discards_overlap_duplicates():
    payloads = [
        {
            "audio_duration": 30,
            "chunk": {
                "index": 0,
                "source_start": 0,
                "source_end": 15,
                "core_start": 0,
                "core_end": 10,
            },
            "result": {
                "segments": [
                    {"start": 8, "end": 9, "text": "保留"},
                    {"start": 11, "end": 12, "text": "丢弃"},
                ]
            },
        },
        {
            "audio_duration": 30,
            "chunk": {
                "index": 1,
                "source_start": 8,
                "source_end": 22,
                "core_start": 10,
                "core_end": 20,
            },
            "result": {
                "segments": [
                    {"start": 1, "end": 2, "text": "前重叠"},
                    {"start": 3, "end": 4, "text": "保留二"},
                ]
            },
        },
    ]
    merged = merge_chunk_payloads(payloads)
    assert [s["text"] for s in merged] == ["保留", "保留二"]
    assert merged[1]["start"] == 11


def test_merge_chunk_payloads_repairs_remaining_overlaps():
    payloads = [
        {
            "audio_duration": 30,
            "chunk": {
                "index": 0,
                "source_start": 0,
                "source_end": 15,
                "core_start": 0,
                "core_end": 15,
            },
            "result": {
                "segments": [
                    {"start": 0, "end": 5, "text": "第一句"},
                    {"start": 4, "end": 6, "text": "第二句"},
                ]
            },
        },
    ]

    merged = merge_chunk_payloads(payloads)

    assert merged[1]["start"] == 5
    assert merged[1]["end"] == 6


def test_merge_chunk_payloads_keeps_half_core_overlap_and_records_decision():
    payloads = [
        {
            "audio_duration": 20,
            "chunk": {
                "index": 0,
                "source_start": 0,
                "source_end": 12,
                "core_start": 0,
                "core_end": 10,
            },
            "result": {"segments": [{"start": 9, "end": 11, "text": "跨边界句子"}]},
        }
    ]

    merged, decisions = merge_chunk_payloads_with_decisions(payloads)

    assert [segment["text"] for segment in merged] == ["跨边界句子"]
    assert any(
        item["action"] == "keep_boundary_segment" and item["overlap_ratio"] == 0.5
        for item in decisions
    )


def test_merge_chunk_payloads_dedupes_similar_boundary_text_by_quality():
    payloads = [
        {
            "audio_duration": 30,
            "chunk": {
                "index": 0,
                "source_start": 0,
                "source_end": 12,
                "core_start": 0,
                "core_end": 10,
            },
            "result": {
                "segments": [
                    {"start": 8.8, "end": 10.2, "text": "这里是边界句子。", "avg_logprob": -0.5}
                ]
            },
        },
        {
            "audio_duration": 30,
            "chunk": {
                "index": 1,
                "source_start": 8,
                "source_end": 22,
                "core_start": 10,
                "core_end": 20,
            },
            "result": {
                "segments": [
                    {"start": 1.8, "end": 3.0, "text": "这里是边界句子", "avg_logprob": -0.1}
                ]
            },
        },
    ]

    merged, decisions = merge_chunk_payloads_with_decisions(payloads)

    assert [segment["text"] for segment in merged] == ["这里是边界句子"]
    assert merged[0]["chunk_index"] == 1
    assert any(item["action"] == "dedupe_similar_boundary" for item in decisions)


def test_subtitle_formats():
    segments = [{"start": 1.23, "end": 2.34, "text": "你好"}]
    srt = segments_to_srt(segments)
    vtt = segments_to_vtt(segments)
    assert "00:00:01,230 --> 00:00:02,340" in srt
    assert vtt.startswith("WEBVTT")
    assert "00:00:01.230 --> 00:00:02.340" in vtt


def test_enforce_monotonic_timeline_repairs_overlaps():
    segments = [
        {"start": 0.0, "end": 2.0, "text": "第一句"},
        {"start": 1.0, "end": 3.0, "text": "第二句"},
        {"start": 2.5, "end": 2.6, "text": "第三句"},
    ]

    repaired = enforce_monotonic_timeline(segments)

    assert repaired[0]["start"] == 0.0
    assert repaired[1]["start"] == 2.0
    assert repaired[2]["start"] == 3.0
    assert repaired[2]["end"] == 3.01
