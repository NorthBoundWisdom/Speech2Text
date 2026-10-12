#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".aac"}


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def discover_audio(process_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in process_dir.glob("*/*/*")
        if path.is_file()
        and path.suffix.lower() in AUDIO_EXTENSIONS
        and "output" not in path.parts
        and not path.name.startswith("sample_")
    )


def run_json_path(audio_path: Path) -> Path:
    return audio_path.parent / "run.json"


def correction_summary(run: dict[str, Any]) -> str:
    quality = run.get("quality_metrics", {})
    if not isinstance(quality, dict):
        return "n/a"
    kinds = quality.get("correction_kind_counts", {})
    if not isinstance(kinds, dict) or not kinds:
        return "0"
    return ", ".join(f"{key}:{value}" for key, value in sorted(kinds.items()))


def chunk_summary(run: dict[str, Any]) -> str:
    counts = run.get("chunk_status_counts", {})
    if not isinstance(counts, dict) or not counts:
        return "n/a"
    return ", ".join(f"{key}:{value}" for key, value in sorted(counts.items()))


def timing_summary(quality: dict[str, Any]) -> str:
    timing = quality.get("timing", {}) if isinstance(quality.get("timing"), dict) else {}
    compatible = timing.get("srt_vtt_compatible")
    if compatible is True:
        return "yes"
    if compatible is False:
        overlap = timing.get("overlapping_timing_segment_count", "n/a")
        missing = timing.get("missing_timing_segment_count", "n/a")
        return f"no (overlap:{overlap}, missing:{missing})"
    return "n/a"


def fmt_float(value: Any, digits: int = 2) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "n/a"


def build_report(process_dir: Path, *, reference_dir: Path) -> str:
    rows: list[str] = []
    missing: list[str] = []
    for audio in discover_audio(process_dir):
        run_path = run_json_path(audio)
        run = read_json(run_path)
        if not run:
            missing.append(str(audio))
            continue
        review = run.get("review", {}) if isinstance(run.get("review"), dict) else {}
        quality = (
            run.get("quality_metrics", {}) if isinstance(run.get("quality_metrics"), dict) else {}
        )
        duration_min = fmt_float(
            (run.get("audio_duration") or 0) / 60 if run.get("audio_duration") else None
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    str(audio.parent.relative_to(process_dir)),
                    duration_min,
                    fmt_float(run.get("runtime_seconds")),
                    fmt_float(run.get("speed_factor")),
                    fmt_float(run.get("peak_rss_mb")),
                    chunk_summary(run),
                    str(review.get("issue_count", "n/a")),
                    str(review.get("segment_issue_count", "n/a")),
                    correction_summary(run),
                    str(quality.get("max_repeated_token_run", "n/a")),
                    fmt_float(quality.get("top_token_ratio"), digits=4),
                    timing_summary(quality),
                    str(run_path),
                ]
            )
            + " |"
        )

    lines = [
        "# Process Three-Audio Experiment",
        "",
        "Scope: all audio files under `process/*/*/`.",
        "",
        "Reference reviewed: "
        f"`{reference_dir}/README.md`, `docs/API.md`, `docs/technical_integration.md`, "
        "`whisperlivekit/core.py`, `metrics.py`, `metrics_collector.py`, and benchmark runner.",
        "",
        "Generalization guardrail: metrics below compare behavior categories "
        "(review issues, correction kinds, repetition risk, cache reuse, speed, timestamp compatibility) "
        "rather than tuning for a single transcript.",
        "",
        "| Episode | Duration min | Runtime s | Speed factor | Peak RSS MB | Chunk status | Review issues | Segment issues | Corrections | Max repeated token run | Top token ratio | SRT/VTT timing | Run JSON |",
        "|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---|---|",
    ]
    lines.extend(
        rows or ["| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |"]
    )
    if missing:
        lines.extend(["", "## Missing Current Runs", ""])
        lines.extend(f"- `{item}`" for item in missing)
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `speed_factor` is SonaFolio's inverse of WhisperLiveKit-style RTF: audio duration divided by wall time.",
            "- `correction_kind_counts` separates glossary, ASR artifact, contextual title, and runaway repetition corrections.",
            "- `Chunk status` is valid only when both the ASR fingerprint and chunk layout manifest match the current run.",
            "- `run.json` records separate transcription and post-processing fingerprints, so correction-only glossary changes can refresh outputs while reusing ASR chunks.",
            "- `SRT/VTT timing` reports whether corrected segments have explicit, monotonic, non-overlapping timestamps.",
            "- `src/scripts/validate_run_json.py` currently validates all three run files plus `src/tests/fixtures/run.sample.json`.",
            "- A candidate backend should improve or preserve review, correction, repetition, diversity, timing, runtime, and memory metrics across all three audios before promotion.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize SonaFolio process/ experiment runs.")
    parser.add_argument("--process-dir", type=Path, default=Path("process"))
    parser.add_argument("--reference-dir", type=Path, default=Path("reference/whisperlivekit"))
    parser.add_argument(
        "--output", type=Path, default=Path("doc/experiments/process_three_audio.md")
    )
    args = parser.parse_args()

    report = build_report(args.process_dir, reference_dir=args.reference_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
