#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import statistics
import time

from atot.corrections import apply_corrections_to_segments
from atot.qa import build_qa_report
from atot.utils import read_json


def _time_call(iterations: int, fn) -> list[float]:
    timings: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - started)
    return timings


def _summary(label: str, timings: list[float]) -> str:
    return (
        f"{label}: n={len(timings)} "
        f"min={min(timings):.4f}s "
        f"median={statistics.median(timings):.4f}s "
        f"max={max(timings):.4f}s"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark local QA/correction hotspots.")
    parser.add_argument("output_dir", type=Path, help="Existing transcription output directory.")
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args(argv)

    work_dir = args.output_dir
    corrected = read_json(work_dir / "corrected.json")
    glossary_path = work_dir / "glossary.effective.json"
    glossary = read_json(glossary_path) if glossary_path.exists() else {}
    segments = corrected.get("segments", []) if isinstance(corrected, dict) else []
    if not isinstance(segments, list):
        raise SystemExit("corrected.json must contain a segments list")

    correction_timings = _time_call(
        args.iterations,
        lambda: apply_corrections_to_segments(segments, glossary),
    )
    qa_timings = _time_call(args.iterations, lambda: build_qa_report(args.output_dir))
    print(_summary("corrections", correction_timings))
    print(_summary("qa_report", qa_timings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
