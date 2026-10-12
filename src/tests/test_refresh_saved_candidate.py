from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from atot.utils import write_json_atomic, write_text_atomic


def _load_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "refresh_saved_candidate.py"
    spec = importlib.util.spec_from_file_location("refresh_saved_candidate", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_refresh_saved_candidate_rebuilds_outputs_from_raw_segments(tmp_path) -> None:
    refresh = _load_script()
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    (tmp_path / "主题.md").write_text(
        "日行迹（Analemma）创始人孙天祥\n节目：测试播客\n", encoding="utf-8"
    )
    candidate_dir = tmp_path / "candidate"
    write_json_atomic(
        candidate_dir / "candidate.run.json",
        {
            "success": True,
            "candidate": "candidate",
            "audio": str(audio),
            "command": ["candidate"],
            "returncode": 0,
            "timed_out": False,
            "runtime_seconds": 1.2,
            "peak_rss_mb": 123.0,
            "review": {"issue_count": 1, "segment_issue_count": 1},
            "quality_metrics": {
                "corrected_char_count": 2,
                "empty_corrected_segment_count": 0,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "top_token_ratio": 0.1,
                "timing": {"srt_vtt_compatible": True},
            },
            "output_files": {
                "raw": str(candidate_dir / "candidate.raw.txt"),
                "raw_segments": str(candidate_dir / "candidate.raw.segments.json"),
                "corrected": str(candidate_dir / "candidate.corrected.txt"),
                "corrected_segments": str(candidate_dir / "candidate.corrected.segments.json"),
                "review": str(candidate_dir / "candidate.review.md"),
                "run": str(candidate_dir / "candidate.run.json"),
                "stdout": str(candidate_dir / "candidate.stdout.txt"),
                "stderr": str(candidate_dir / "candidate.stderr.txt"),
            },
        },
    )
    write_json_atomic(
        candidate_dir / "candidate.raw.segments.json",
        [
            {"start": 0.0, "end": 1.0, "text": "日行季"},
            {"start": 1.0, "end": 2.0, "text": "结束"},
        ],
    )
    write_text_atomic(candidate_dir / "candidate.raw.txt", "日行季结束")
    write_text_atomic(candidate_dir / "candidate.stdout.txt", "{}")
    write_text_atomic(candidate_dir / "candidate.stderr.txt", "")
    write_json_atomic(
        candidate_dir / "comparison.json",
        {
            "audio": str(audio),
            "candidate": "candidate",
            "baseline": {
                "success": True,
                "returncode": 0,
                "timed_out": False,
                "runtime_seconds": 1.0,
                "peak_rss_mb": 100.0,
                "corrected_char_count": 4,
                "empty_corrected_segment_count": 0,
                "review_issue_count": 0,
                "review_segment_issue_count": 0,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "top_token_ratio": 0.1,
                "srt_vtt_compatible": True,
                "timed_segment_count": 2,
                "missing_timing_segment_count": 0,
                "invalid_timing_segment_count": 0,
                "non_monotonic_timing_segment_count": 0,
                "overlapping_timing_segment_count": 0,
            },
            "candidate_metrics": {
                "success": True,
                "returncode": 0,
                "timed_out": False,
                "runtime_seconds": 1.2,
                "peak_rss_mb": 123.0,
                "corrected_char_count": 2,
                "empty_corrected_segment_count": 0,
                "review_issue_count": 1,
                "review_segment_issue_count": 1,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "top_token_ratio": 0.1,
                "srt_vtt_compatible": True,
                "timed_segment_count": 2,
                "missing_timing_segment_count": 0,
                "invalid_timing_segment_count": 0,
                "non_monotonic_timing_segment_count": 0,
                "overlapping_timing_segment_count": 0,
            },
            "corrected_char_ratio": 0.5,
            "metric_guardrail_pass": False,
            "metric_guardrail_failures": ["review_issue_regression"],
        },
    )

    result = refresh.refresh_candidate_dir(candidate_dir)

    assert isinstance(result["metric_guardrail_pass"], bool)
    assert isinstance(result["metric_guardrail_failures"], list)
    refreshed_run = json.loads((candidate_dir / "candidate.run.json").read_text(encoding="utf-8"))
    assert refreshed_run["quality_metrics"]["correction_count"] == 1
    assert refreshed_run["review"]["issue_count"] == 0
    refreshed_comparison = json.loads(
        (candidate_dir / "comparison.json").read_text(encoding="utf-8")
    )
    assert refreshed_comparison["candidate_metrics"]["correction_count"] == 1
    assert refreshed_comparison["candidate_metrics"]["review_issue_count"] == 0
    assert (candidate_dir / "candidate.corrected.txt").read_text(
        encoding="utf-8"
    ).strip() == "日行迹\n结束"
