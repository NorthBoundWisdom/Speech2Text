from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from atot.candidate.matrix import build_matrix_markdown
from atot.numeric import as_int
from atot.candidate.paths import candidate_output_dir
from atot.paths import DEFAULT_OUTPUT_DIR
from atot.runinfo import now_iso
from atot.utils import ensure_dir, write_json_atomic, write_text_atomic


@dataclass(frozen=True)
class SweepTask:
    preset: str
    audio: Path


@dataclass(frozen=True)
class SweepOptions:
    presets: tuple[str, ...]
    audios: tuple[Path, ...]
    output_dir: Path
    model: str = "large-v3-turbo"
    candidate_timeout: float = 1800.0
    jobs: int = 1
    min_audio_count: int = 1


def default_sweep_output_dir(root: Path | None = None) -> Path:
    stamp = now_iso().replace(":", "").replace("-", "").split("+", 1)[0]
    base = (root or DEFAULT_OUTPUT_DIR / "benchmark" / "asr_candidate_sweep").expanduser()
    return base / stamp


def build_tasks(*, presets: tuple[str, ...], audios: tuple[Path, ...]) -> list[SweepTask]:
    return [
        SweepTask(preset=preset, audio=audio.expanduser().resolve())
        for preset in presets
        for audio in audios
    ]


def _comparison_json_path(output_dir: Path, task: SweepTask) -> Path:
    return candidate_output_dir(output_dir / "runs", task.audio, task.preset) / "comparison.json"


def run_compare_task(task: SweepTask, options: SweepOptions) -> dict[str, Any]:
    compare_script = Path(__file__).resolve().parents[2] / "scripts" / "compare_asr_candidate.py"
    command = [
        sys.executable,
        str(compare_script),
        str(task.audio),
        "--preset",
        task.preset,
        "--output-dir",
        str(options.output_dir / "runs"),
        "--model",
        options.model,
        "--candidate-timeout",
        str(options.candidate_timeout),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "preset": task.preset,
        "audio": str(task.audio),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "comparison_json": str(_comparison_json_path(options.output_dir, task)),
    }


def run_sweep(
    options: SweepOptions,
    *,
    runner: Callable[[SweepTask, SweepOptions], dict[str, Any]] = run_compare_task,
) -> dict[str, Any]:
    output_dir = ensure_dir(options.output_dir)
    ensure_dir(output_dir / "runs")
    tasks = build_tasks(presets=options.presets, audios=options.audios)
    results: list[dict[str, Any]] = []
    max_workers = max(1, min(int(options.jobs), len(tasks) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(runner, task, options): task for task in tasks}
        for future in as_completed(future_map):
            task = future_map[future]
            result = future.result()
            result.setdefault("preset", task.preset)
            result.setdefault("audio", str(task.audio))
            results.append(result)
    results.sort(key=lambda item: (str(item.get("preset", "")), str(item.get("audio", ""))))
    matrix = build_matrix_markdown(
        runs_dir=output_dir / "runs",
        candidates=set(options.presets),
        min_audio_count=max(1, int(options.min_audio_count)),
    )
    matrix_path = write_text_atomic(output_dir / "matrix.md", matrix)
    summary = {
        "created_at": now_iso(),
        "output_dir": str(output_dir),
        "runs_dir": str(output_dir / "runs"),
        "presets": list(options.presets),
        "audios": [str(audio) for audio in options.audios],
        "jobs": max_workers,
        "candidate_timeout": options.candidate_timeout,
        "baseline_model": options.model,
        "task_count": len(tasks),
        "failed_task_count": sum(
            1
            for item in results
            if (as_int(item.get("returncode")) if item.get("returncode") is not None else 1) != 0
        ),
        "results": results,
        "matrix_path": str(matrix_path),
    }
    write_json_atomic(output_dir / "summary.json", summary)
    return summary
