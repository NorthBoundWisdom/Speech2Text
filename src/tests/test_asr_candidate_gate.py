from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "asr_candidate_gate.py"
    spec = importlib.util.spec_from_file_location("asr_candidate_gate", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_discover_process_audios_excludes_generated_outputs(tmp_path) -> None:
    gate = _load_script()
    source = tmp_path / "process" / "0527" / "episode" / "episode.m4a"
    library_source = tmp_path / "process" / "episode-id" / "library-episode.m4a"
    prepared = tmp_path / "process" / "0527" / "episode" / "output" / "prepared.wav"
    sample = tmp_path / "process" / "0527" / "episode" / "sample_04m_2min.wav"
    library_sample = tmp_path / "process" / "episode-id" / "sample_04m_2min.wav"
    monitor = tmp_path / "process" / "0527" / "episode" / "monitor-large-v3" / "prepared.wav"
    compare_chunk = (
        tmp_path
        / "process"
        / "0527"
        / "episode"
        / "compare-baseline-candidate"
        / "chunks"
        / "chunk_0000.wav"
    )
    for path in (source, library_source, prepared, sample, library_sample, monitor, compare_chunk):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")

    assert gate.discover_process_audios(tmp_path / "process") == [source, library_source]


def test_gate_markdown_links_per_audio_comparisons() -> None:
    gate = _load_script()

    markdown = gate._gate_markdown(
        "candidate",
        [
            {
                "audio": "process/a.m4a",
                "success": True,
                "returncode": 0,
                "runtime_seconds": 1.25,
                "baseline_peak_rss_mb": 1000.0,
                "candidate_peak_rss_mb": 100.0,
                "corrected_char_count": 100,
                "empty_corrected_segment_count": 0,
                "review_issue_count": 0,
                "review_segment_issue_count": 0,
                "correction_count": 1,
                "max_repeated_token_run": 2,
                "baseline_review_issue_count": 0,
                "baseline_correction_count": 1,
                "baseline_max_repeated_token_run": 2,
                "candidate_review_issue_count": 0,
                "candidate_correction_count": 1,
                "candidate_max_repeated_token_run": 2,
                "baseline_top_token_ratio": 0.1,
                "candidate_top_token_ratio": 0.1,
                "baseline_srt_vtt_compatible": True,
                "candidate_srt_vtt_compatible": True,
                "corrected_char_ratio": 0.95,
                "metric_guardrail_pass": True,
                "metric_guardrail_failures": [],
                "comparison": "output/a/comparison.md",
            }
        ],
    )

    assert "# ASR Candidate Gate" in markdown
    assert "[a.m4a](output/a/comparison.md)" in markdown
    assert "| pass |" in markdown
    assert "| pass | none |" in markdown
    assert "| a" not in markdown
    assert "Promotion guardrail" in markdown


def test_gate_summary_row_reads_guardrail_failures(tmp_path) -> None:
    gate = _load_script()
    comparison_path = tmp_path / "comparison.md"
    comparison_path.with_suffix(".json").write_text(
        '{"metric_guardrail_pass": false, "metric_guardrail_failures": ["correction_count_regression"]}',
        encoding="utf-8",
    )

    row = gate._summary_row(Path("process/a.m4a"), {"success": True}, comparison_path)

    assert row["metric_guardrail_failures"] == ["correction_count_regression"]


def test_gate_parser_accepts_candidate_timeout() -> None:
    gate = _load_script()

    args = gate.build_parser().parse_args(
        [
            "--candidate-name",
            "candidate",
            "--candidate-command",
            "cmd",
            "--candidate-timeout",
            "3.5",
        ]
    )

    assert args.candidate_timeout == 3.5


def test_gate_parser_accepts_preset_without_candidate_command() -> None:
    gate = _load_script()

    args = gate.build_parser().parse_args(["--preset", "whisperlivekit-mlx"])

    assert args.preset == "whisperlivekit-mlx"
    assert args.candidate_command is None


def test_strict_counts_metric_guardrail_failures() -> None:
    gate = _load_script()

    failed_count, guardrail_failed_count = gate._strict_failure_counts(
        [
            {"success": True, "metric_guardrail_pass": True},
            {"success": True, "metric_guardrail_pass": False},
            {"success": False, "metric_guardrail_pass": "missing"},
        ]
    )

    assert failed_count == 1
    assert guardrail_failed_count == 2


def test_gate_summary_payload_requires_success_and_metric_guardrails() -> None:
    gate = _load_script()

    payload = gate._gate_summary_payload(
        "candidate",
        [
            {"success": True, "metric_guardrail_pass": True},
            {"success": False, "metric_guardrail_pass": False},
        ],
    )

    assert payload["candidate"] == "candidate"
    assert payload["audio_count"] == 2
    assert payload["success"] is False
    assert payload["failed_count"] == 1
    assert payload["guardrail_failed_count"] == 1
