#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.validate_cloud_package import validate_cloud_package
from scripts.validate_output_bundle import validate_output_bundle
from scripts.validate_repair_artifacts import validate_repair_artifacts


REQUIRED_CLOUD_OUTPUTS = {
    "summary.md",
    "chapters.json",
    "chapters.md",
    "shownotes.md",
    "title_candidates.json",
    "title_candidates.md",
    "social_copy.md",
    "terms.json",
    "terms.md",
    "uncertainty_report.md",
    "fact_or_term_uncertainties.md",
    "glossary_suggestions.json",
    "transcript.polish_suggestions.json",
}


@dataclass(frozen=True)
class RuntimeEvidenceOptions:
    long_output: Path | None = None
    gold_report: Path | None = None
    repair_output: Path | None = None
    cloud_output: Path | None = None
    min_long_duration: float = 95.0 * 60.0
    min_gold_samples: int = 3
    require_condition_matrix: bool = True
    require_cloud_api: bool = False


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_json_object(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing JSON file: {path}")
        return {}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        errors.append(f"{path}: must be a JSON object")
        return {}
    return payload


def _run_json(output_dir: Path, errors: list[str]) -> dict[str, Any]:
    return _load_json_object(output_dir / "run.json", errors)


def _validate_long_output(output_dir: Path, options: RuntimeEvidenceOptions) -> list[str]:
    errors = [f"{output_dir}: {error}" for error in validate_output_bundle(output_dir)]
    run = _run_json(output_dir, errors)
    if run.get("success") is not True:
        errors.append(f"{output_dir}: run.json success must be true")
    duration = run.get("audio_duration")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        errors.append(f"{output_dir}: run.json audio_duration must be numeric")
    elif float(duration) < options.min_long_duration:
        errors.append(
            f"{output_dir}: audio_duration {float(duration):.2f}s is below required {options.min_long_duration:.2f}s"
        )
    if run.get("qa", {}).get("status") != "pass":
        errors.append(f"{output_dir}: QA status must be pass for unattended long-run evidence")
    if run.get("cloud", {}).get("audio_uploaded") is not False:
        errors.append(f"{output_dir}: cloud.audio_uploaded must be false")
    status_counts = run.get("chunk_status_counts")
    if (
        not isinstance(status_counts, dict)
        or sum(int(status_counts.get(key, 0) or 0) for key in status_counts) <= 0
    ):
        errors.append(f"{output_dir}: chunk_status_counts must show processed or reused chunks")
    return errors


def _validate_gold_report(path: Path, options: RuntimeEvidenceOptions) -> list[str]:
    errors: list[str] = []
    report = _load_json_object(path, errors)
    if report.get("success") is not True:
        errors.append(f"{path}: benchmark report success must be true")
    if report.get("gate_failures"):
        errors.append(f"{path}: gate_failures must be empty")
    rows = report.get("results")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{path}: results must be a non-empty list")
        rows = []
    samples = {
        str(row.get("sample")) for row in rows if isinstance(row, dict) and row.get("sample")
    }
    if len(samples) < options.min_gold_samples:
        errors.append(f"{path}: expected at least {options.min_gold_samples} distinct gold samples")
    condition_values = report.get("condition_on_previous_text_values")
    if options.require_condition_matrix and set(condition_values or []) != {False, True}:
        errors.append(f"{path}: condition_on_previous_text_values must include both false and true")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{path}: results[{index}] must be an object")
            continue
        for key in ("cer", "term_hit_rate", "runtime_seconds", "peak_rss_mb"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path}: results[{index}].{key} must be numeric")
        if row.get("qa_success") is not True:
            errors.append(f"{path}: results[{index}].qa_success must be true")
        if row.get("srt_pass") is not True:
            errors.append(f"{path}: results[{index}].srt_pass must be true")
        job_dir = row.get("job_dir")
        if not isinstance(job_dir, str) or not job_dir:
            errors.append(f"{path}: results[{index}].job_dir must be recorded")
    return errors


def _cloud_dir(output_dir: Path) -> Path:
    return output_dir / "cloud"


def _validate_cloud_api_audits(output_dir: Path) -> list[str]:
    errors: list[str] = []
    audit_paths = sorted(_cloud_dir(output_dir).rglob("*.api_run.json"))
    if not audit_paths:
        return [f"{output_dir}: no cloud API audit files found"]
    for path in audit_paths:
        audit = _load_json_object(path, errors)
        request = audit.get("request")
        if not isinstance(request, dict):
            errors.append(f"{path}: request must be an object")
            continue
        if audit.get("api") not in (None, "responses"):
            errors.append(f"{path}: cloud API audit must use responses")
        if request.get("input") != "[redacted in audit]":
            errors.append(f"{path}: request input must be redacted in audit")
        if "messages" in request:
            errors.append(f"{path}: request must use Responses API input, not chat messages")
        if "api_key" in audit or "Authorization" in json.dumps(audit, ensure_ascii=False):
            errors.append(f"{path}: audit must not store API credentials")
        if "response" not in audit:
            errors.append(f"{path}: missing response payload")
    return errors


def _validate_cloud_output(output_dir: Path, options: RuntimeEvidenceOptions) -> list[str]:
    errors = [f"{output_dir}: {error}" for error in validate_cloud_package(output_dir, mode="both")]
    run = _run_json(output_dir, errors)
    cloud = run.get("cloud")
    if not isinstance(cloud, dict):
        errors.append(f"{output_dir}: run.json cloud state must be an object")
    else:
        if cloud.get("prepared") is not True:
            errors.append(f"{output_dir}: cloud.prepared must be true")
        if cloud.get("audio_uploaded") is not False:
            errors.append(f"{output_dir}: cloud.audio_uploaded must be false")
    manifest = _load_json_object(_cloud_dir(output_dir) / "manifest.json", errors)
    output_files = manifest.get("output_files")
    if not isinstance(output_files, list):
        errors.append(f"{output_dir}: cloud manifest output_files must be a list")
        output_files = []
    missing = REQUIRED_CLOUD_OUTPUTS - set(map(str, output_files))
    for item in sorted(missing):
        errors.append(f"{output_dir}: missing cloud output `{item}`")
    if options.require_cloud_api:
        errors.extend(_validate_cloud_api_audits(output_dir))
    return errors


def _validate_repair_output(output_dir: Path) -> list[str]:
    errors = [f"{output_dir}: {error}" for error in validate_repair_artifacts(output_dir)]
    run = _run_json(output_dir, errors)
    repair = run.get("repair")
    if not isinstance(repair, dict):
        errors.append(f"{output_dir}: run.json repair state must be an object")
        return errors
    if repair.get("applied") is not True:
        errors.append(f"{output_dir}: repair.applied must be true")
    ids = repair.get("repair_run_ids")
    if not isinstance(ids, list) or not ids:
        errors.append(f"{output_dir}: repair_run_ids must include at least one repair run")
    return errors


def validate_runtime_evidence(options: RuntimeEvidenceOptions) -> list[str]:
    errors: list[str] = []
    provided = [
        options.long_output,
        options.gold_report,
        options.repair_output,
        options.cloud_output,
    ]
    if not any(provided):
        return ["provide at least one runtime evidence path to validate"]
    if options.long_output is not None:
        errors.extend(_validate_long_output(options.long_output.expanduser().resolve(), options))
    if options.gold_report is not None:
        errors.extend(_validate_gold_report(options.gold_report.expanduser().resolve(), options))
    if options.repair_output is not None:
        errors.extend(_validate_repair_output(options.repair_output.expanduser().resolve()))
    if options.cloud_output is not None:
        errors.extend(_validate_cloud_output(options.cloud_output.expanduser().resolve(), options))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate real runtime evidence for the AtoT roadmap."
    )
    parser.add_argument(
        "--long-output",
        type=Path,
        default=None,
        help="Output directory for a long local transcription run.",
    )
    parser.add_argument(
        "--gold-report", type=Path, default=None, help="Gold benchmark report.json from a real run."
    )
    parser.add_argument(
        "--repair-output",
        type=Path,
        default=None,
        help="Output directory with a completed local repair run.",
    )
    parser.add_argument(
        "--cloud-output",
        type=Path,
        default=None,
        help="Output directory with prepared cloud text outputs.",
    )
    parser.add_argument("--min-long-duration", type=float, default=95.0 * 60.0)
    parser.add_argument("--min-gold-samples", type=int, default=3)
    parser.add_argument(
        "--no-condition-matrix",
        action="store_true",
        help="Do not require both previous-text conditions.",
    )
    parser.add_argument(
        "--require-cloud-api",
        action="store_true",
        help="Require cloud API audit files in addition to local cloud outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_runtime_evidence(
        RuntimeEvidenceOptions(
            long_output=args.long_output,
            gold_report=args.gold_report,
            repair_output=args.repair_output,
            cloud_output=args.cloud_output,
            min_long_duration=args.min_long_duration,
            min_gold_samples=args.min_gold_samples,
            require_condition_matrix=not args.no_condition_matrix,
            require_cloud_api=args.require_cloud_api,
        )
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("runtime evidence: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
