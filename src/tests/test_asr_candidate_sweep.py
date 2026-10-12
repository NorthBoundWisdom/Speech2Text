from __future__ import annotations

import json
from pathlib import Path

from atot.candidate.paths import candidate_output_dir
from atot.candidate.sweep import SweepOptions, SweepTask, build_tasks, run_sweep


def test_build_tasks_creates_cross_product(tmp_path) -> None:
    audio_a = tmp_path / "a.wav"
    audio_b = tmp_path / "b.wav"
    audio_a.write_bytes(b"a")
    audio_b.write_bytes(b"b")

    tasks = build_tasks(presets=("preset-a", "preset-b"), audios=(audio_a, audio_b))

    assert [(task.preset, task.audio.name) for task in tasks] == [
        ("preset-a", "a.wav"),
        ("preset-a", "b.wav"),
        ("preset-b", "a.wav"),
        ("preset-b", "b.wav"),
    ]
    assert all(task.audio.is_absolute() for task in tasks)


def test_run_sweep_writes_summary_and_matrix(tmp_path) -> None:
    audio = tmp_path / "process" / "0527" / "episode" / "episode.m4a"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"audio")
    output_dir = tmp_path / "sweep"

    def fake_runner(task: SweepTask, options: SweepOptions) -> dict[str, object]:
        candidate_dir = candidate_output_dir(options.output_dir / "runs", task.audio, task.preset)
        comparison = {
            "candidate": task.preset,
            "audio": str(task.audio),
            "metric_guardrail_pass": task.preset.endswith("good"),
            "metric_guardrail_failures": []
            if task.preset.endswith("good")
            else ["repetition_regression"],
            "corrected_char_ratio": 0.95,
            "candidate_metrics": {
                "success": True,
                "runtime_seconds": 12.0,
                "peak_rss_mb": 345.0,
            },
        }
        (candidate_dir / "comparison.json").write_text(json.dumps(comparison), encoding="utf-8")
        return {
            "preset": task.preset,
            "audio": str(task.audio),
            "returncode": 0,
            "comparison_json": str(candidate_dir / "comparison.json"),
        }

    summary = run_sweep(
        SweepOptions(
            presets=("candidate-good", "candidate-bad"),
            audios=(audio,),
            output_dir=output_dir,
            jobs=2,
            min_audio_count=1,
        ),
        runner=fake_runner,
    )

    assert summary["task_count"] == 2
    assert summary["failed_task_count"] == 0
    assert Path(str(summary["matrix_path"])).exists()
    assert Path(str(output_dir / "summary.json")).exists()
    matrix = (output_dir / "matrix.md").read_text(encoding="utf-8")
    assert "`candidate-good`" in matrix
    assert "`candidate-bad`" in matrix
    assert "`repetition_regression`:1" in matrix
