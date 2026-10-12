import json

from atot.pipeline import _sha256_json
from atot.formats import segments_to_srt
from atot.qa import build_qa_report, qa_to_markdown, run_qa
from atot.qa.policy import IssueType
from atot.utils import write_json_atomic, write_text_atomic


def _write_minimal_output(tmp_path, *, segments):
    output = tmp_path / "output"
    details = output
    write_json_atomic(
        details / "raw.json", {"segments": segments, "text": "\n".join(s["text"] for s in segments)}
    )
    write_json_atomic(
        details / "corrected.json",
        {"segments": segments, "text": "\n".join(s["text"] for s in segments)},
    )
    write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 0}})
    write_json_atomic(details / "chunks_manifest.json", {"chunk_layout_sha256": "abc"})
    write_text_atomic(output / "transcript.srt", segments_to_srt(segments))
    return output


def test_build_qa_report_flags_large_gap_and_repetition(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 1.0, "text": "你好你好你好"},
            {"start": 80.0, "end": 81.0, "text": "后面"},
        ],
    )

    report = build_qa_report(output, max_gap=30.0)

    assert report["success"] is False
    assert {issue["type"] for issue in report["issues"]} >= {"large_timing_gap", "repeated_phrase"}
    assert report["suggested_repairs"]
    assert all(issue["id"].startswith("qa_") for issue in report["issues"])
    assert report["quality_score"]["overall"] < 90
    assert report["quality_score"]["timeline"] < 100


def test_qa_flags_segment_overlap_as_repairable_blocker(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 5.0, "text": "第一段正常内容。"},
            {"start": 4.5, "end": 7.0, "text": "第二段和前一段重叠。"},
        ],
    )

    report = build_qa_report(output)

    issue = next(
        item for item in report["issues"] if item["type"] == IssueType.SEGMENT_OVERLAP.value
    )
    assert report["success"] is False
    assert issue["severity"] == "blocker"
    assert issue["repairable"] is True
    assert issue["segment_ids"] == [1]
    assert issue["suggested_action"] == "repair_window"
    assert issue["previous_end"] == 5.0
    assert any(
        IssueType.SEGMENT_OVERLAP.value in window["reasons"]
        for window in report["suggested_repairs"]
    )


def test_qa_flags_large_timing_gap_as_repairable_blocker(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 2.0, "text": "开头内容。"},
            {"start": 70.5, "end": 72.0, "text": "长间隔之后的内容。"},
        ],
    )

    report = build_qa_report(output, max_gap=30.0)

    issue = next(
        item for item in report["issues"] if item["type"] == IssueType.LARGE_TIMING_GAP.value
    )
    assert report["success"] is False
    assert issue["severity"] == "blocker"
    assert issue["repairable"] is True
    assert issue["segment_ids"] == [1]
    assert issue["start"] == 2.0
    assert issue["end"] == 70.5
    assert issue["duration"] == 68.5
    assert issue["suggested_action"] == "repair_window"


def test_qa_flags_long_segment_as_repairable_blocker(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {
                "start": 10.0,
                "end": 45.5,
                "text": "这是一段持续时间过长但文本本身正常的转写内容。",
            },
        ],
    )

    report = build_qa_report(output, max_segment_duration=30.0)

    issue = next(item for item in report["issues"] if item["type"] == IssueType.LONG_SEGMENT.value)
    assert report["success"] is False
    assert issue["severity"] == "blocker"
    assert issue["repairable"] is True
    assert issue["segment_ids"] == [0]
    assert issue["start"] == 10.0
    assert issue["end"] == 45.5
    assert issue["duration"] == 35.5
    assert issue["suggested_action"] == "repair_window"


def test_build_qa_report_applies_config_and_confidence_checks(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[{"start": 0.0, "end": 2.0, "text": "低置信度片段", "avg_logprob": -1.6}],
    )
    config = tmp_path / "qa.json"
    write_json_atomic(config, {"profile": "balanced", "checks": {"min_avg_logprob_blocker": -1.55}})

    report = build_qa_report(output, qa_config=config)

    assert report["success"] is False
    assert report["checks"]["profile"] == "balanced"
    issue = next(item for item in report["issues"] if item["type"] == "low_avg_logprob_segment")
    assert issue["severity"] == "blocker"
    assert issue["repairable"] is True
    assert issue["suggested_action"] == "repair_window"
    assert report["summary"]["repair_window_count"] == 1
    assert report["suggested_repairs"][0]["source_issue_ids"] == [issue["id"]]


def test_qa_treats_short_conversational_repetition_as_warning(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[{"start": 0.0, "end": 1.0, "text": "对对对对对对。"}],
    )

    report = build_qa_report(output)

    assert report["success"] is True
    issue = next(item for item in report["issues"] if item["type"] == "repeated_phrase")
    assert issue["severity"] == "warning"
    assert issue["repairable"] is True
    assert issue["segment_ids"] == [0]


def test_qa_blocks_long_dense_repetition(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[{"start": 0.0, "end": 30.0, "text": "欢迎收听本节目。" * 8}],
    )

    report = build_qa_report(output)

    assert report["success"] is False
    issue = next(item for item in report["issues"] if item["type"] == "repeated_phrase")
    assert issue["severity"] == "blocker"


def test_qa_treats_short_low_confidence_tail_as_warning(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[{"start": 0.0, "end": 0.3, "text": "是", "avg_logprob": -2.0}],
    )

    report = build_qa_report(output)

    assert report["success"] is True
    issue = next(item for item in report["issues"] if item["type"] == "low_avg_logprob_segment")
    assert issue["severity"] == "warning"


def test_qa_treats_short_high_compression_tail_as_warning(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[{"start": 0.0, "end": 0.3, "text": "Wow", "compression_ratio": 4.0}],
    )

    report = build_qa_report(output)

    assert report["success"] is True
    issue = next(
        item
        for item in report["issues"]
        if item["type"] == IssueType.HIGH_COMPRESSION_RATIO_SEGMENT.value
    )
    assert issue["severity"] == "warning"


def test_qa_treats_short_adjacent_duplicate_as_warning(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 1.0, "text": "行,"},
            {"start": 1.1, "end": 1.3, "text": "行,"},
        ],
    )

    report = build_qa_report(output)

    assert report["success"] is True
    issue = next(item for item in report["issues"] if item["type"] == "adjacent_duplicate_segment")
    assert issue["severity"] == "warning"


def test_qa_uses_canonical_issue_type_for_english_punctuation_in_chinese(tmp_path):
    output = _write_minimal_output(
        tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好,世界"}]
    )

    report = build_qa_report(output)

    issue = next(
        item
        for item in report["issues"]
        if item["type"] == IssueType.ENGLISH_PUNCTUATION_IN_CHINESE
    )
    assert issue["severity"] == "warning"
    assert report["quality_score"]["text_health"] < 100


def test_qa_ignores_empty_text_for_suppressed_segments(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 1.0, "text": "正常内容。"},
            {
                "start": 95.0,
                "end": 100.0,
                "text": "",
                "suppressed": True,
                "suppress_reason": "tail_hallucination",
            },
        ],
    )

    report = build_qa_report(output)

    assert "empty_segment_text" not in {issue["type"] for issue in report["issues"]}


def test_qa_reports_readable_transcript_metrics_and_issues(tmp_path):
    output = _write_minimal_output(
        tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "正常内容。"}]
    )
    details = output
    write_text_atomic(
        output / "transcript.readable.md",
        "# Transcript\n\n[00:00:00] "
        + ("这是一段没有句号的可读文本" * 30)
        + "ChatGPT很好(测试\n\n[00:01:00] 你好,世界。\n",
    )
    write_json_atomic(
        details / "corrections.json", {"corrections": [{"kind": "review_only", "count": 2}]}
    )

    report = build_qa_report(output)

    readable = report["metrics"]["readable"]
    issue_types = {issue["type"] for issue in report["issues"]}
    assert readable["available"] is True
    assert readable["paragraph_count"] == 2
    assert readable["max_run_on_chars"] > 240
    assert readable["review_only_correction_count"] == 2
    assert "readable_low_punctuation_density" in issue_types
    assert "readable_run_on_text" in issue_types
    assert "readable_english_cjk_spacing" in issue_types
    assert "readable_ascii_punctuation_in_cjk" in issue_types
    assert "readable_unmatched_brackets" in issue_types
    assert "readable_review_only_terms" in issue_types
    assert "Readable paragraphs" in qa_to_markdown(report)


def test_run_qa_writes_reports(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])

    report = run_qa(output)

    assert report["success"] is True
    assert json.loads((output / "qa.json").read_text(encoding="utf-8"))["success"] is True
    assert "quality_score" in json.loads((output / "qa.json").read_text(encoding="utf-8"))
    assert "Status: PASS" in (output / "qa.md").read_text(encoding="utf-8")


def test_qa_uses_review_and_diagnostic_severities(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    details = output
    write_json_atomic(details / "review.json", {"summary": {"segment_issue_count": 1}})
    write_json_atomic(
        details / "chunks_manifest.json",
        {
            "chunk_layout": {
                "audio_duration": 1.0,
                "chunks": [
                    {
                        "index": 0,
                        "source_start": 0.0,
                        "source_end": 1.0,
                        "core_start": 0.0,
                        "core_end": 1.0,
                    }
                ],
            }
        },
    )

    report = build_qa_report(output)

    review_issue = next(
        item for item in report["issues"] if item["type"] == "review_segment_issues"
    )
    diagnostic_issue = next(
        item for item in report["issues"] if item["type"] == "missing_chunk_layout_hash"
    )
    assert report["success"] is True
    assert review_issue["severity"] == "review"
    assert diagnostic_issue["severity"] == "diagnostic"
    assert report["summary"]["review_count"] == 1
    assert report["summary"]["diagnostic_count"] == 1
    markdown = (output / "qa.md").read_text(encoding="utf-8") if (output / "qa.md").exists() else ""
    if markdown:
        assert "Review Items" in markdown


def test_qa_issue_ids_are_stable_across_runs(tmp_path):
    output = _write_minimal_output(
        tmp_path,
        segments=[
            {"start": 0.0, "end": 1.0, "text": "你好你好你好"},
            {"start": 80.0, "end": 81.0, "text": "后面"},
        ],
    )

    first = build_qa_report(output, max_gap=30.0)
    second = build_qa_report(output, max_gap=30.0)

    assert [issue["id"] for issue in first["issues"]] == [issue["id"] for issue in second["issues"]]


def test_qa_flags_chunk_fingerprint_and_manifest_mismatch(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    details = output
    layout = {
        "version": 1,
        "sample_rate": 16000,
        "audio_duration": 1.0,
        "chunk_length": 1200.0,
        "overlap": 0.0,
        "chunks": [
            {"index": 0, "source_start": 0.0, "source_end": 1.0, "core_start": 0.0, "core_end": 1.0}
        ],
    }
    run_fingerprint = {
        "version": 1,
        "backend": "fake",
        "model": "m",
        "chunk_layout_sha256": _sha256_json(layout),
    }
    chunk_json = details / "chunks" / "chunk_0000.json"
    write_json_atomic(
        chunk_json,
        {
            "success": True,
            "transcription_fingerprint_sha256": "0" * 64,
            "chunk": {"index": 0, "core_start": 0.0, "core_end": 1.0},
        },
    )
    write_json_atomic(
        details / "run.json",
        {
            "chunk_layout_sha256": _sha256_json(layout),
            "transcription_fingerprint": run_fingerprint,
            "transcription_fingerprint_sha256": _sha256_json(run_fingerprint),
            "chunks": [
                {
                    "index": 0,
                    "json": str(chunk_json),
                    "core_start": 0.0,
                    "core_end": 1.0,
                }
            ],
        },
    )
    write_json_atomic(
        details / "chunks_manifest.json",
        {"chunk_layout": {**layout, "overlap": 10.0}, "chunk_layout_sha256": "1" * 64},
    )

    report = build_qa_report(output)

    assert report["success"] is False
    issue_types = {issue["type"] for issue in report["issues"]}
    assert "chunk_layout_hash_mismatch" in issue_types
    assert "chunk_layout_manifest_hash_invalid" in issue_types
    assert "chunk_fingerprint_hash_mismatch" in issue_types


def test_qa_flags_chunk_layout_core_coverage_gap(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    details = output
    write_json_atomic(
        details / "chunks_manifest.json",
        {
            "chunk_layout": {
                "audio_duration": 3.0,
                "chunks": [
                    {
                        "index": 0,
                        "source_start": 0.0,
                        "source_end": 1.0,
                        "core_start": 0.0,
                        "core_end": 1.0,
                    },
                    {
                        "index": 1,
                        "source_start": 2.0,
                        "source_end": 3.0,
                        "core_start": 2.0,
                        "core_end": 3.0,
                    },
                ],
            },
            "chunk_layout_sha256": "abc",
        },
    )

    report = build_qa_report(output)

    assert report["success"] is False
    assert "chunk_core_coverage_gap" in {issue["type"] for issue in report["issues"]}


def test_qa_allows_small_chunk_layout_rounding_drift(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    details = output
    write_json_atomic(
        details / "chunks_manifest.json",
        {
            "chunk_layout": {
                "audio_duration": 3.0,
                "chunks": [
                    {
                        "index": 0,
                        "source_start": 0.0,
                        "source_end": 3.0,
                        "core_start": 0.0,
                        "core_end": 3.001,
                    },
                ],
            },
            "chunk_layout_sha256": "abc",
        },
    )

    report = build_qa_report(output)

    assert "invalid_chunk_layout_bounds" not in {issue["type"] for issue in report["issues"]}


def test_qa_flags_core_chunk_text_missing_from_merged_output(tmp_path):
    output = _write_minimal_output(
        tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "第一段", "chunk_index": 0}]
    )
    details = output
    layout = {
        "audio_duration": 2.0,
        "chunks": [
            {
                "index": 0,
                "source_start": 0.0,
                "source_end": 1.0,
                "core_start": 0.0,
                "core_end": 1.0,
            },
            {
                "index": 1,
                "source_start": 1.0,
                "source_end": 2.0,
                "core_start": 1.0,
                "core_end": 2.0,
            },
        ],
    }
    missing_json = details / "chunks" / "chunk_0001.json"
    write_json_atomic(
        missing_json,
        {
            "success": True,
            "chunk": layout["chunks"][1],
            "result": {"segments": [{"start": 0.1, "end": 0.9, "text": "第二段"}]},
        },
    )
    write_json_atomic(
        details / "run.json",
        {
            "chunk_layout": layout,
            "chunks": [{"index": 1, "json": str(missing_json), "core_start": 1.0, "core_end": 2.0}],
        },
    )
    write_json_atomic(
        details / "chunks_manifest.json", {"chunk_layout": layout, "chunk_layout_sha256": "abc"}
    )

    report = build_qa_report(output)

    assert report["success"] is False
    assert "chunk_core_merge_missing" in {issue["type"] for issue in report["issues"]}


def test_qa_flags_stale_corrected_text_and_srt(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    write_text_atomic(output / "transcript.corrected.txt", "旧文本")
    write_text_atomic(output / "transcript.srt", "1\n00:00:00,000 --> 00:00:01,000\n旧文本\n")

    report = build_qa_report(output)

    assert report["success"] is False
    issue_types = {issue["type"] for issue in report["issues"]}
    assert "corrected_txt_mismatch" in issue_types
    assert "srt_content_mismatch" in issue_types


def test_qa_flags_prepared_audio_size_mismatch(tmp_path):
    output = _write_minimal_output(tmp_path, segments=[{"start": 0.0, "end": 1.0, "text": "你好"}])
    details = output
    prepared = details / "prepared.wav"
    prepared.write_bytes(b"abc")
    write_json_atomic(
        details / "run.json",
        {
            "prepared_audio": {"path": str(prepared), "size_bytes": 10},
            "input_file": {},
        },
    )

    report = build_qa_report(output)

    assert report["success"] is False
    assert "prepared_audio_size_mismatch" in {issue["type"] for issue in report["issues"]}
