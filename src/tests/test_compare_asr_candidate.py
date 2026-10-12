from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_compare_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "compare_asr_candidate.py"
    spec = importlib.util.spec_from_file_location("compare_asr_candidate", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_failed_candidate_comparison_is_not_reported_as_quality_pass() -> None:
    compare = _load_compare_script()
    markdown = compare._comparison_markdown(
        audio=Path("sample.wav"),
        baseline_run={
            "runtime_seconds": 1.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 120,
                "empty_corrected_segment_count": 0,
                "correction_count": 1,
                "max_repeated_token_run": 2,
            },
        },
        candidate_run={
            "success": False,
            "candidate": "broken-backend",
            "returncode": 1,
            "runtime_seconds": 0.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 0,
                "empty_corrected_segment_count": 1,
                "correction_count": 0,
                "max_repeated_token_run": 0,
            },
        },
    )

    assert "| Candidate | failed | 1 |" in markdown
    assert "quality metrics for that row are diagnostic only" in markdown
    assert "do not interpret zero review issues as a quality pass" in markdown


def test_timed_out_candidate_comparison_is_diagnostic() -> None:
    compare = _load_compare_script()
    markdown = compare._comparison_markdown(
        audio=Path("sample.wav"),
        baseline_run={
            "runtime_seconds": 1.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {"corrected_char_count": 120},
        },
        candidate_run={
            "success": False,
            "timed_out": True,
            "candidate": "slow-backend",
            "returncode": compare.TIMEOUT_RETURN_CODE,
            "runtime_seconds": 0.1,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {"corrected_char_count": 0, "empty_corrected_segment_count": 1},
        },
    )

    assert "Candidate command timed out" in markdown
    assert f"| Candidate | failed | {compare.TIMEOUT_RETURN_CODE} |" in markdown


def test_comparison_payload_flags_metric_guardrail() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={
            "runtime_seconds": 1.2,
            "review": {"issue_count": 1, "segment_issue_count": 1},
            "quality_metrics": {
                "corrected_char_count": 120,
                "correction_count": 2,
                "max_repeated_token_run": 3,
                "top_token_ratio": 0.1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "runtime_seconds": 0.5,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "empty_corrected_segment_count": 0,
                "correction_count": 1,
                "max_repeated_token_run": 2,
                "top_token_ratio": 0.1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert payload["metric_guardrail_pass"] is True
    assert payload["metric_guardrail_failures"] == []
    assert payload["baseline"]["review_issue_count"] == 1
    assert payload["candidate_metrics"]["correction_count"] == 1
    assert payload["corrected_char_ratio"] == 100 / 120


def test_comparison_payload_rejects_empty_candidate_text() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={"review": {}, "quality_metrics": {"corrected_char_count": 120}},
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {},
            "quality_metrics": {"corrected_char_count": 0},
        },
    )

    assert payload["metric_guardrail_pass"] is False
    assert payload["metric_guardrail_failures"] == ["empty_candidate", "timestamp_incompatible"]


def test_comparison_payload_does_not_apply_ratio_when_baseline_is_empty() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={"review": {}, "quality_metrics": {"corrected_char_count": 0}},
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {},
            "quality_metrics": {
                "corrected_char_count": 100,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert payload["corrected_char_ratio"] == 0.0
    assert payload["metric_guardrail_pass"] is False
    assert payload["metric_guardrail_failures"] == ["empty_baseline"]


def test_comparison_payload_rejects_implausibly_short_candidate_text() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 1000,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert payload["corrected_char_ratio"] == 0.1
    assert payload["metric_guardrail_pass"] is False
    assert "char_ratio_low" in payload["metric_guardrail_failures"]


def test_comparison_markdown_reports_length_ratio_note() -> None:
    compare = _load_compare_script()
    markdown = compare._comparison_markdown(
        audio=Path("sample.wav"),
        baseline_run={
            "runtime_seconds": 1.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 1000,
                "empty_corrected_segment_count": 0,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "short-backend",
            "returncode": 0,
            "runtime_seconds": 0.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "empty_corrected_segment_count": 0,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert "Baseline ratio" in markdown
    assert "| Candidate | ok | 0 | 0.20 | n/a | 100 | 0.10 |" in markdown
    assert "outside the same-audio baseline ratio bounds" in markdown


def test_comparison_payload_rejects_missing_candidate_timestamps() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "timing": {"srt_vtt_compatible": False, "missing_timing_segment_count": 1},
            },
        },
    )

    assert payload["candidate_metrics"]["srt_vtt_compatible"] is False
    assert payload["metric_guardrail_pass"] is False
    assert "timestamp_incompatible" in payload["metric_guardrail_failures"]


def test_comparison_payload_rejects_high_top_token_ratio() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "top_token_ratio": 0.05,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 0,
                "max_repeated_token_run": 1,
                "top_token_ratio": 0.9,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert payload["top_token_ratio_bound"] == 0.25
    assert payload["metric_guardrail_pass"] is False
    assert "top_token_ratio_regression" in payload["metric_guardrail_failures"]


def test_comparison_payload_reports_metric_regression_failures() -> None:
    compare = _load_compare_script()
    payload = compare._comparison_payload(
        audio=Path("sample.wav"),
        baseline_run={
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 1,
                "max_repeated_token_run": 2,
                "top_token_ratio": 0.1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "review": {"issue_count": 1, "segment_issue_count": 1},
            "quality_metrics": {
                "corrected_char_count": 100,
                "correction_count": 2,
                "max_repeated_token_run": 3,
                "top_token_ratio": 0.1,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert payload["metric_guardrail_pass"] is False
    assert payload["metric_guardrail_failures"] == [
        "review_issue_regression",
        "review_segment_issue_regression",
        "correction_count_regression",
        "repetition_regression",
    ]


def test_comparison_markdown_reports_metric_guardrail_failures() -> None:
    compare = _load_compare_script()
    markdown = compare._comparison_markdown(
        audio=Path("sample.wav"),
        baseline_run={
            "runtime_seconds": 1.2,
            "review": {"issue_count": 0, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "empty_corrected_segment_count": 0,
                "correction_count": 1,
                "max_repeated_token_run": 2,
                "timing": {"srt_vtt_compatible": True},
            },
        },
        candidate_run={
            "success": True,
            "candidate": "candidate",
            "returncode": 0,
            "runtime_seconds": 0.2,
            "review": {"issue_count": 1, "segment_issue_count": 0},
            "quality_metrics": {
                "corrected_char_count": 100,
                "empty_corrected_segment_count": 0,
                "correction_count": 2,
                "max_repeated_token_run": 3,
                "timing": {"srt_vtt_compatible": True},
            },
        },
    )

    assert "Metric guardrail failures" in markdown
    assert "`review_issue_regression`" in markdown
    assert "`correction_count_regression`" in markdown


def test_candidate_command_template_accepts_topic_context_placeholders() -> None:
    compare = _load_compare_script()

    command = compare._format_template(
        "tool --audio {audio} --out {output} --context {glossary_terms}",
        audio=Path("sample audio.wav"),
        output=Path("candidate.txt"),
        output_dir=Path("out dir"),
        context="full prompt",
        glossary_terms="孙天祥 ChatGPT",
    )

    assert command == [
        "tool",
        "--audio",
        "sample audio.wav",
        "--out",
        "candidate.txt",
        "--context",
        "孙天祥 ChatGPT",
    ]


def test_compare_parser_accepts_preset_without_candidate_command() -> None:
    compare = _load_compare_script()

    args = compare.build_parser().parse_args(["sample.wav", "--preset", "mlx-qwen3-asr-0.6b"])

    assert args.preset == "mlx-qwen3-asr-0.6b"
    assert args.candidate_command is None


def test_baseline_job_name_uses_official_process_output_for_source_audio() -> None:
    compare = _load_compare_script()
    legacy_audio = Path.cwd() / "materials" / "0527" / "topic" / "episode.m4a"
    library_audio = Path.cwd() / "materials" / "episode-id" / "episode.m4a"

    assert compare._baseline_job_name(legacy_audio, "candidate") is None
    assert compare._baseline_job_name(library_audio, "candidate") is None


def test_baseline_job_name_includes_audio_stem_for_samples() -> None:
    compare = _load_compare_script()
    sample = Path.cwd() / "materials" / "0527" / "topic" / "sample_04m_2min.wav"
    full = Path.cwd() / "materials" / "0527" / "topic" / "episode.m4a"

    assert (
        compare._baseline_job_name(sample, "candidate")
        == "compare-baseline-sample_04m_2min-candidate"
    )
    assert compare._baseline_job_name(full, "candidate") is None


def test_official_process_run_json_only_for_top_level_sources(tmp_path) -> None:
    compare = _load_compare_script()
    process_dir = tmp_path / "materials"
    output_dir = tmp_path / "work"
    source = process_dir / "0527" / "topic" / "episode.m4a"
    library_source = process_dir / "episode-id" / "library-episode.m4a"
    sample = process_dir / "0527" / "topic" / "sample_04m_2min.wav"
    run_json = output_dir / "0527" / "topic" / "run.json"
    library_run_json = output_dir / "episode-id" / "run.json"
    run_json.parent.mkdir(parents=True)
    run_json.write_text('{"success": true}', encoding="utf-8")
    library_run_json.parent.mkdir(parents=True)
    library_run_json.write_text('{"success": true}', encoding="utf-8")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"audio")
    library_source.parent.mkdir(parents=True, exist_ok=True)
    library_source.write_bytes(b"audio")
    sample.write_bytes(b"audio")

    assert (
        compare._official_process_run_json(source, process_dir=process_dir, output_dir=output_dir)
        == run_json
    )
    assert (
        compare._official_process_run_json(
            library_source, process_dir=process_dir, output_dir=output_dir
        )
        == library_run_json
    )
    assert compare._official_process_run_json(sample, process_dir=process_dir) is None


def test_run_candidate_command_returns_timeout() -> None:
    compare = _load_compare_script()

    returncode, _runtime, peak_rss_mb, timed_out, stdout, stderr = compare._run_candidate_command(
        [sys.executable, "-c", "import time; print('start'); time.sleep(2)"],
        timeout=0.01,
    )

    assert returncode == compare.TIMEOUT_RETURN_CODE
    assert peak_rss_mb is None or peak_rss_mb >= 0
    assert timed_out is True
    assert stdout in {"", "start\n"}
    assert "timed out" in stderr


def test_run_candidate_command_records_peak_rss() -> None:
    compare = _load_compare_script()

    returncode, runtime, peak_rss_mb, timed_out, stdout, stderr = compare._run_candidate_command(
        [sys.executable, "-c", "print('ok')"],
        timeout=5,
    )

    assert returncode == 0
    assert runtime >= 0
    assert peak_rss_mb is None or peak_rss_mb > 0
    assert timed_out is False
    assert stdout == "ok\n"
    assert stderr == ""


def test_run_candidate_command_records_missing_command_failure() -> None:
    compare = _load_compare_script()

    returncode, _runtime, peak_rss_mb, timed_out, stdout, stderr = compare._run_candidate_command(
        ["definitely-missing-audio2text-command"],
        timeout=5,
    )

    assert returncode == compare.COMMAND_NOT_FOUND_RETURN_CODE
    assert peak_rss_mb is None
    assert timed_out is False
    assert stdout == ""
    assert stderr


def test_candidate_command_template_allows_literal_json_braces() -> None:
    compare = _load_compare_script()

    command = compare._format_template(
        '/bin/echo \'{"text":"ok"}\' {audio}',
        audio=Path("sample.wav"),
        output=Path("candidate.txt"),
        output_dir=Path("out"),
        context="",
        glossary_terms="",
    )

    assert command == ["/bin/echo", '{"text":"ok"}', "sample.wav"]


def test_glossary_terms_are_stable_and_unique() -> None:
    compare = _load_compare_script()

    terms = compare._glossary_terms(
        {
            "people": ["孙天祥", "孙天祥"],
            "organizations": ["上海交通大学"],
            "technical_terms": ["ChatGPT"],
            "titles": ["AI青年志"],
        }
    )

    assert terms == "孙天祥 上海交通大学 ChatGPT AI青年志"


def test_candidate_json_output_preserves_segments_even_with_txt_suffix(tmp_path) -> None:
    compare = _load_compare_script()
    output = tmp_path / "candidate.command-output.txt"
    output.write_text(
        """
        {
          "text": "第一段第二段",
          "segments": [
            {"start": 1.5, "end": 2.0, "text": "第一段"},
            {"start": 2.0, "end": 3.0, "text": "第二段"}
          ]
        }
        """,
        encoding="utf-8",
    )

    assert compare._extract_candidate_text("", output) == "第一段第二段"
    assert compare._extract_candidate_segments("", output) == [
        {"start": 1.5, "end": 2.0, "text": "第一段", "_timing_source": "explicit"},
        {"start": 2.0, "end": 3.0, "text": "第二段", "_timing_source": "explicit"},
    ]


def test_candidate_json_sentences_support_timestamp_arrays() -> None:
    compare = _load_compare_script()
    stdout = '{"sentences":[{"timestamp":[4,5.5],"text":"一句话"}]}'

    assert compare._extract_candidate_text(stdout, Path("missing.txt")) == "一句话"
    assert compare._extract_candidate_segments(stdout, Path("missing.txt")) == [
        {"start": 4.0, "end": 5.5, "text": "一句话", "_timing_source": "explicit"}
    ]


def test_candidate_plain_text_output_marks_timing_as_fallback() -> None:
    compare = _load_compare_script()

    assert compare._extract_candidate_segments("纯文本", Path("missing.txt")) == [
        {"start": 0.0, "end": 0.01, "text": "纯文本", "_timing_source": "text_fallback"}
    ]


def test_candidate_outputs_repair_explicit_timeline_overlaps(tmp_path) -> None:
    compare = _load_compare_script()
    context = compare.PromptContext(
        topic_path=tmp_path / "主题.md",
        topic_text=None,
        prompt_text=None,
        prompt_sources=[],
        base_glossary={},
        episode_glossary={},
        glossary={},
        effective_prompt=None,
    )

    run = compare._write_candidate_outputs(
        audio=Path("episode.wav"),
        candidate_name="candidate",
        candidate_text="第一句第二句",
        candidate_segments=[
            {"start": 0.0, "end": 2.0, "text": "第一句", "_timing_source": "explicit"},
            {"start": 1.5, "end": 3.0, "text": "第二句", "_timing_source": "explicit"},
        ],
        output_dir=tmp_path,
        command=["candidate"],
        runtime_seconds=1.0,
        peak_rss_mb=10.0,
        returncode=0,
        timed_out=False,
        stdout="",
        stderr="",
        context=context,
    )

    assert run["quality_metrics"]["timing"]["srt_vtt_compatible"] is True
    corrected = compare.read_json(tmp_path / "candidate.corrected.segments.json")
    assert corrected[1]["start"] == corrected[0]["end"]


def test_candidate_outputs_keep_plain_text_timing_incompatible(tmp_path) -> None:
    compare = _load_compare_script()
    context = compare.PromptContext(
        topic_path=tmp_path / "主题.md",
        topic_text=None,
        prompt_text=None,
        prompt_sources=[],
        base_glossary={},
        episode_glossary={},
        glossary={},
        effective_prompt=None,
    )

    run = compare._write_candidate_outputs(
        audio=Path("episode.wav"),
        candidate_name="candidate",
        candidate_text="纯文本",
        candidate_segments=[
            {"start": 0.0, "end": 0.01, "text": "纯文本", "_timing_source": "text_fallback"}
        ],
        output_dir=tmp_path,
        command=["candidate"],
        runtime_seconds=1.0,
        peak_rss_mb=10.0,
        returncode=0,
        timed_out=False,
        stdout="",
        stderr="",
        context=context,
    )

    assert run["quality_metrics"]["timing"]["srt_vtt_compatible"] is False
