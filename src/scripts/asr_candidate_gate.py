#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path

ensure_src_on_path()

from atot.candidate.metrics import format_failures as _format_failures
from atot.candidate.paths import AUDIO_SUFFIXES, discover_process_audios as _discover_process_audios
from atot.paths import DEFAULT_OUTPUT_DIR
from atot.utils import ensure_dir, read_json, slugify, write_json_atomic, write_text_atomic
from asr_candidate_presets import presets


def _is_source_audio(path: Path, process_dir: Path) -> bool:
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        return False
    try:
        relative = path.relative_to(process_dir)
    except ValueError:
        return False
    if len(relative.parts) != 3:
        return False
    if path.name == "prepared.wav" or path.name.startswith("sample_"):
        return False
    return True


def discover_process_audios(process_dir: Path) -> list[Path]:
    return _discover_process_audios(process_dir)


def _candidate_dir(root: Path, audio: Path, candidate_name: str) -> Path:
    return root / slugify(audio.stem, max_len=60) / slugify(candidate_name, max_len=40)


def _read_run(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _summary_row(audio: Path, run: dict[str, Any], comparison_path: Path) -> dict[str, Any]:
    comparison_json = comparison_path.with_suffix(".json")
    comparison = _read_run(comparison_json)
    guardrail_failures = comparison.get("metric_guardrail_failures")
    if not isinstance(guardrail_failures, list):
        guardrail_failures = (
            [] if comparison.get("metric_guardrail_pass") is True else ["metric_guardrail_missing"]
        )
    baseline_metrics = (
        comparison.get("baseline", {}) if isinstance(comparison.get("baseline"), dict) else {}
    )
    candidate_metrics = (
        comparison.get("candidate_metrics", {})
        if isinstance(comparison.get("candidate_metrics"), dict)
        else {}
    )
    review = run.get("review", {}) if isinstance(run.get("review"), dict) else {}
    quality = run.get("quality_metrics", {}) if isinstance(run.get("quality_metrics"), dict) else {}
    return {
        "audio": str(audio),
        "success": bool(run.get("success")),
        "returncode": run.get("returncode", "missing"),
        "runtime_seconds": run.get("runtime_seconds", 0.0),
        "baseline_peak_rss_mb": baseline_metrics.get("peak_rss_mb", "missing"),
        "candidate_peak_rss_mb": candidate_metrics.get(
            "peak_rss_mb", run.get("peak_rss_mb", "missing")
        ),
        "corrected_char_count": quality.get("corrected_char_count", "missing"),
        "empty_corrected_segment_count": quality.get("empty_corrected_segment_count", "missing"),
        "review_issue_count": review.get("issue_count", "missing"),
        "review_segment_issue_count": review.get("segment_issue_count", "missing"),
        "correction_count": quality.get("correction_count", "missing"),
        "max_repeated_token_run": quality.get("max_repeated_token_run", "missing"),
        "baseline_review_issue_count": baseline_metrics.get("review_issue_count", "missing"),
        "baseline_correction_count": baseline_metrics.get("correction_count", "missing"),
        "baseline_max_repeated_token_run": baseline_metrics.get(
            "max_repeated_token_run", "missing"
        ),
        "baseline_top_token_ratio": baseline_metrics.get("top_token_ratio", "missing"),
        "candidate_review_issue_count": candidate_metrics.get(
            "review_issue_count", review.get("issue_count", "missing")
        ),
        "candidate_correction_count": candidate_metrics.get(
            "correction_count", quality.get("correction_count", "missing")
        ),
        "candidate_max_repeated_token_run": candidate_metrics.get(
            "max_repeated_token_run", quality.get("max_repeated_token_run", "missing")
        ),
        "candidate_top_token_ratio": candidate_metrics.get(
            "top_token_ratio", quality.get("top_token_ratio", "missing")
        ),
        "baseline_srt_vtt_compatible": baseline_metrics.get("srt_vtt_compatible", "missing"),
        "candidate_srt_vtt_compatible": candidate_metrics.get("srt_vtt_compatible", "missing"),
        "corrected_char_ratio": comparison.get("corrected_char_ratio", "missing"),
        "metric_guardrail_pass": comparison.get("metric_guardrail_pass", "missing"),
        "metric_guardrail_failures": [str(item) for item in guardrail_failures],
        "comparison": str(comparison_path),
    }


def _status(value: bool) -> str:
    return "ok" if value else "failed"


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_guardrail(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return str(value)


def _format_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def _gate_markdown(candidate_name: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        "# ASR Candidate Gate",
        "",
        f"- Candidate: `{candidate_name}`",
        f"- Audio count: {len(rows)}",
        "",
        "| Audio | Status | Return code | Runtime s | Candidate RSS MB | Corrected chars | Baseline ratio | Empty segments | Candidate issues | Baseline issues | Candidate corrections | Baseline corrections | Candidate repeat | Baseline repeat | Candidate top token | Candidate SRT/VTT | Metric guardrail | Guardrail failures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{Path(str(row['audio'])).name}]({row['comparison']})",
                    _status(bool(row["success"])),
                    _format_number(row["returncode"]),
                    _format_number(row["runtime_seconds"]),
                    _format_number(row["candidate_peak_rss_mb"]),
                    _format_number(row["corrected_char_count"]),
                    _format_number(row["corrected_char_ratio"]),
                    _format_number(row["empty_corrected_segment_count"]),
                    _format_number(row["candidate_review_issue_count"]),
                    _format_number(row["baseline_review_issue_count"]),
                    _format_number(row["candidate_correction_count"]),
                    _format_number(row["baseline_correction_count"]),
                    _format_number(row["candidate_max_repeated_token_run"]),
                    _format_number(row["baseline_max_repeated_token_run"]),
                    _format_number(row["candidate_top_token_ratio"]),
                    _format_bool(row["candidate_srt_vtt_compatible"]),
                    _format_guardrail(row["metric_guardrail_pass"]),
                    _format_failures(row["metric_guardrail_failures"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Promotion guardrail: all gate rows should succeed and pass the metric guardrail before a candidate is promoted. Metric pass is necessary but not sufficient; semantic transcript quality still requires review.",
        ]
    )
    return "\n".join(lines) + "\n"


def _strict_failure_counts(rows: list[dict[str, Any]]) -> tuple[int, int]:
    failed = [row for row in rows if not row["success"]]
    guardrail_failed = [row for row in rows if row.get("metric_guardrail_pass") is not True]
    return len(failed), len(guardrail_failed)


def _gate_summary_payload(candidate_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    failed_count, guardrail_failed_count = _strict_failure_counts(rows)
    return {
        "candidate": candidate_name,
        "audio_count": len(rows),
        "success": failed_count == 0 and guardrail_failed_count == 0,
        "failed_count": failed_count,
        "guardrail_failed_count": guardrail_failed_count,
        "rows": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the same external ASR candidate comparison across the process audio gate."
    )
    parser.add_argument(
        "audio",
        nargs="*",
        type=Path,
        help="Audio files. Defaults to discovered process source audio.",
    )
    parser.add_argument(
        "--preset", choices=sorted(presets()), help="Use a vetted candidate command preset."
    )
    parser.add_argument("--candidate-name")
    parser.add_argument("--candidate-command")
    parser.add_argument("--process-dir", type=Path, default=Path("process"))
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "benchmark" / "asr_candidate_gate"
    )
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument(
        "--candidate-timeout",
        type=float,
        default=0.0,
        help="Seconds before killing each candidate command. 0 disables the timeout.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if any candidate row fails or misses the metric guardrail.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected_preset = presets().get(args.preset) if args.preset else None
    candidate_name = args.candidate_name or (selected_preset.name if selected_preset else "")
    candidate_command_template = args.candidate_command or (
        selected_preset.command if selected_preset else ""
    )
    if not candidate_name:
        build_parser().error("--candidate-name is required unless --preset is used")
    if not candidate_command_template:
        build_parser().error("--candidate-command is required unless --preset is used")

    audios = [path.expanduser().resolve() for path in args.audio]
    if not audios:
        audios = [path.resolve() for path in discover_process_audios(args.process_dir)]
    if not audios:
        print("No process source audio files found.", file=sys.stderr)
        return 2

    output_dir = ensure_dir(args.output_dir)
    rows: list[dict[str, Any]] = []
    compare_script = Path(__file__).with_name("compare_asr_candidate.py")
    for audio in audios:
        command = [
            sys.executable,
            str(compare_script),
            str(audio),
            "--candidate-name",
            candidate_name,
            "--candidate-command",
            candidate_command_template,
            "--output-dir",
            str(output_dir / "runs"),
            "--model",
            args.model,
        ]
        if args.candidate_timeout and args.candidate_timeout > 0:
            command.extend(["--candidate-timeout", str(args.candidate_timeout)])
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        candidate_dir = _candidate_dir(output_dir / "runs", audio, candidate_name)
        run_path = candidate_dir / "candidate.run.json"
        comparison_path = candidate_dir / "comparison.md"
        if completed.returncode != 0 and not run_path.exists():
            ensure_dir(candidate_dir)
            (candidate_dir / "gate.stdout.txt").write_text(completed.stdout, encoding="utf-8")
            (candidate_dir / "gate.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        rows.append(_summary_row(audio, _read_run(run_path), comparison_path))

    summary_path = output_dir / f"{slugify(candidate_name, max_len=40)}.md"
    summary_json_path = output_dir / f"{slugify(candidate_name, max_len=40)}.json"
    write_text_atomic(summary_path, _gate_markdown(candidate_name, rows))
    write_json_atomic(summary_json_path, _gate_summary_payload(candidate_name, rows))
    print(f"Gate summary: {summary_path}")
    print(f"Gate summary JSON: {summary_json_path}")
    failed_count, guardrail_failed_count = _strict_failure_counts(rows)
    if failed_count:
        print(f"Candidate failures: {failed_count}/{len(rows)}", file=sys.stderr)
    if guardrail_failed_count:
        print(f"Metric guardrail failures: {guardrail_failed_count}/{len(rows)}", file=sys.stderr)
    return 1 if args.strict and (failed_count or guardrail_failed_count) else 0


if __name__ == "__main__":
    raise SystemExit(main())
