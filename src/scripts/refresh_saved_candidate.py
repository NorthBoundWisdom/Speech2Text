#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _bootstrap import ensure_src_on_path  # noqa: E402

ensure_src_on_path()

from atot.candidate.metrics import comparison_payload  # noqa: E402
from atot.candidate.outputs import comparison_markdown, refresh_candidate_outputs  # noqa: E402
from atot.candidate.paths import official_process_run_json  # noqa: E402
from atot.context import build_prompt_context  # noqa: E402
from atot.paths import DEFAULT_GLOSSARY_FILE, DEFAULT_PROMPT_FILE  # noqa: E402
from atot.utils import read_json, write_json_atomic, write_text_atomic  # noqa: E402


def _read_json_dict(path: Path) -> dict[str, Any]:
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _baseline_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": bool(summary.get("success", True)),
        "returncode": summary.get("returncode", 0),
        "timed_out": bool(summary.get("timed_out", False)),
        "runtime_seconds": float(summary.get("runtime_seconds", 0.0) or 0.0),
        "peak_rss_mb": summary.get("peak_rss_mb"),
        "review": {
            "issue_count": int(summary.get("review_issue_count", 0) or 0),
            "segment_issue_count": int(summary.get("review_segment_issue_count", 0) or 0),
        },
        "quality_metrics": {
            "corrected_char_count": int(summary.get("corrected_char_count", 0) or 0),
            "empty_corrected_segment_count": int(
                summary.get("empty_corrected_segment_count", 0) or 0
            ),
            "correction_count": int(summary.get("correction_count", 0) or 0),
            "max_repeated_token_run": int(summary.get("max_repeated_token_run", 0) or 0),
            "top_token_ratio": float(summary.get("top_token_ratio", 0.0) or 0.0),
            "timing": {
                "srt_vtt_compatible": bool(summary.get("srt_vtt_compatible", False)),
                "timed_segment_count": int(summary.get("timed_segment_count", 0) or 0),
                "missing_timing_segment_count": int(
                    summary.get("missing_timing_segment_count", 0) or 0
                ),
                "invalid_timing_segment_count": int(
                    summary.get("invalid_timing_segment_count", 0) or 0
                ),
                "non_monotonic_timing_segment_count": int(
                    summary.get("non_monotonic_timing_segment_count", 0) or 0
                ),
                "overlapping_timing_segment_count": int(
                    summary.get("overlapping_timing_segment_count", 0) or 0
                ),
            },
        },
    }


def refresh_candidate_dir(candidate_dir: Path) -> dict[str, Any]:
    candidate_dir = candidate_dir.expanduser().resolve()
    run = _read_json_dict(candidate_dir / "candidate.run.json")
    if not run:
        raise FileNotFoundError(f"Missing candidate.run.json under {candidate_dir}")
    raw_segments = read_json(candidate_dir / "candidate.raw.segments.json")
    if not isinstance(raw_segments, list):
        raise ValueError(f"candidate.raw.segments.json must be a JSON list: {candidate_dir}")

    audio = Path(str(run.get("audio") or ""))
    context = build_prompt_context(
        audio, prompt_file=DEFAULT_PROMPT_FILE, glossary_file=DEFAULT_GLOSSARY_FILE
    )
    refreshed_run = refresh_candidate_outputs(
        output_dir=candidate_dir,
        existing_run=run,
        raw_segments=raw_segments,
        context=context,
    )

    comparison_path = candidate_dir / "comparison.json"
    existing_comparison = _read_json_dict(comparison_path) if comparison_path.exists() else {}
    baseline_run_path = official_process_run_json(audio)
    if baseline_run_path is not None and baseline_run_path.exists():
        baseline_run = _read_json_dict(baseline_run_path)
    else:
        baseline_summary = existing_comparison.get("baseline", {})
        baseline_run = _baseline_from_summary(
            baseline_summary if isinstance(baseline_summary, dict) else {}
        )

    payload = comparison_payload(
        audio=audio, baseline_run=baseline_run, candidate_run=refreshed_run
    )
    markdown = comparison_markdown(
        audio=audio, baseline_run=baseline_run, candidate_run=refreshed_run
    )
    write_json_atomic(comparison_path, payload)
    write_text_atomic(candidate_dir / "comparison.md", markdown)
    return {
        "candidate_dir": str(candidate_dir),
        "audio": str(audio),
        "candidate": refreshed_run.get("candidate"),
        "metric_guardrail_pass": payload.get("metric_guardrail_pass"),
        "metric_guardrail_failures": payload.get("metric_guardrail_failures", []),
        "review_issue_count": refreshed_run.get("review", {}).get("issue_count", 0),
        "review_segment_issue_count": refreshed_run.get("review", {}).get("segment_issue_count", 0),
        "correction_count": refreshed_run.get("quality_metrics", {}).get("correction_count", 0),
        "corrected_char_count": refreshed_run.get("quality_metrics", {}).get(
            "corrected_char_count", 0
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh an existing candidate directory after rule/glossary changes without rerunning ASR."
    )
    parser.add_argument("candidate_dir", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = [refresh_candidate_dir(path) for path in args.candidate_dir]
    failed = [item for item in results if item.get("metric_guardrail_pass") is not True]
    if args.json_output:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        for item in results:
            failures = item.get("metric_guardrail_failures", [])
            status = "pass" if item.get("metric_guardrail_pass") is True else "fail"
            print(f"{item['candidate_dir']}: {status}")
            if failures:
                print("  failures:", ", ".join(str(code) for code in failures))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
