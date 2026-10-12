from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_script():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    script = scripts_dir / "asr_candidate_matrix.py"
    spec = importlib.util.spec_from_file_location("asr_candidate_matrix", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_comparison(
    path: Path, *, candidate: str, audio: str, passed: bool, failures: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "candidate": candidate,
                "audio": audio,
                "metric_guardrail_pass": passed,
                "metric_guardrail_failures": failures,
                "corrected_char_ratio": 0.9,
                "candidate_metrics": {
                    "success": True,
                    "runtime_seconds": 10.0,
                    "peak_rss_mb": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )


def test_matrix_filters_by_min_audio_count_and_summarizes_failures(tmp_path) -> None:
    matrix = _load_script()
    runs = tmp_path / "runs"
    _write_comparison(
        runs / "audio-a" / "candidate-a" / "comparison.json",
        candidate="candidate-a",
        audio="a.m4a",
        passed=True,
        failures=[],
    )
    _write_comparison(
        runs / "audio-b" / "candidate-a" / "comparison.json",
        candidate="candidate-a",
        audio="b.m4a",
        passed=False,
        failures=["repetition_regression"],
    )
    _write_comparison(
        runs / "audio-a" / "smoke" / "comparison.json",
        candidate="smoke",
        audio="a.m4a",
        passed=True,
        failures=[],
    )

    markdown = matrix.build_matrix_markdown(runs_dir=runs, min_audio_count=2)

    assert "`candidate-a` | 2 | 2/2 | 1/2 | no" in markdown
    assert "`repetition_regression`:1" in markdown
    assert "`smoke`" not in markdown
    assert "## Per-Audio Rows" in markdown


def test_matrix_marks_candidate_promotable_only_when_every_row_passes(tmp_path) -> None:
    matrix = _load_script()
    runs = tmp_path / "runs"
    _write_comparison(
        runs / "audio-a" / "candidate-a" / "comparison.json",
        candidate="candidate-a",
        audio="a.m4a",
        passed=True,
        failures=[],
    )
    _write_comparison(
        runs / "audio-b" / "candidate-a" / "comparison.json",
        candidate="candidate-a",
        audio="b.m4a",
        passed=True,
        failures=[],
    )

    markdown = matrix.build_matrix_markdown(runs_dir=runs, min_audio_count=2)

    assert "`candidate-a` | 2 | 2/2 | 2/2 | yes" in markdown


def test_matrix_cli_writes_output(tmp_path) -> None:
    matrix = _load_script()
    runs = tmp_path / "runs"
    output = tmp_path / "matrix.md"
    _write_comparison(
        runs / "audio-a" / "candidate-a" / "comparison.json",
        candidate="candidate-a",
        audio="a.m4a",
        passed=True,
        failures=[],
    )

    assert (
        matrix.main(["--runs-dir", str(runs), "--output", str(output), "--min-audio-count", "1"])
        == 0
    )
    assert "# ASR Candidate Gate Matrix" in output.read_text(encoding="utf-8")
