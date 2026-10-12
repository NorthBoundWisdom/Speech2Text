from __future__ import annotations

import argparse
import json
from typing import Any

from ..cleanup import CleanupOptions, cleanup_output
from ..diarization import DiarizeOptions, run_diarization
from ..pipeline import print_run_summary
from ..postprocess import PostprocessOptions, run_postprocess
from ..qa import qa_to_markdown, run_qa
from ..repair import RepairOptions, run_repair
from ..status import inspect_output, status_to_markdown
from ..validators import validate_cloud_package, validate_output_bundle, validate_repair_artifacts


def cmd_qa(args: argparse.Namespace) -> int:
    report = run_qa(
        args.output,
        profile=getattr(args, "profile", "balanced"),
        qa_config=getattr(args, "qa_config", None),
        max_gap=args.max_gap,
        max_segment_duration=args.max_segment_duration,
        max_subtitle_chars=args.max_subtitle_chars,
        max_subtitle_line_chars=getattr(args, "max_subtitle_line_chars", None),
        fail_on_srt_error=args.fail_on_srt_error,
        write_report=not args.no_write_report,
    )
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(qa_to_markdown(report).strip())
    return 0 if report.get("success") else 1


def cmd_status(args: argparse.Namespace) -> int:
    report = inspect_output(args.output, write_report=args.write_report)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(status_to_markdown(report).strip())
    return 0 if report.get("success") else 1


def cmd_validate(args: argparse.Namespace) -> int:
    report = run_qa(args.output, write_report=False)
    checks: list[dict[str, Any]] = [
        {
            "name": "qa",
            "success": bool(report.get("success")),
            "errors": [],
            "summary": report.get("summary", {}),
        }
    ]
    if getattr(args, "bundle", False):
        errors = validate_output_bundle(args.output)
        checks.append({"name": "bundle", "success": not errors, "errors": errors})
    if getattr(args, "cloud", None):
        errors = validate_cloud_package(args.output, mode=args.cloud)
        checks.append({"name": "cloud", "success": not errors, "errors": errors})
    if getattr(args, "repair", False):
        errors = validate_repair_artifacts(args.output)
        checks.append({"name": "repair", "success": not errors, "errors": errors})
    success = all(check["success"] for check in checks)
    payload = {"success": success, "checks": checks, "qa": report}
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(qa_to_markdown(report).strip())
        for check in checks[1:]:
            print("")
            print(f"## {str(check['name']).title()} Validation")
            if check["success"]:
                print("Status: PASS")
            else:
                print("Status: FAIL")
                for error in check["errors"]:
                    print(f"- {error}")
    return 0 if success else 1


def cmd_cleanup(args: argparse.Namespace) -> int:
    result = cleanup_output(
        CleanupOptions(output_dir=args.output, profile=args.profile, dry_run=args.dry_run)
    )
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Profile: {result['profile']}")
        print(f"Deleted files: {result['deleted_count']}")
        print(f"Freed bytes: {result['freed_bytes']}")
    return 0


def cmd_postprocess(args: argparse.Namespace) -> int:
    run = run_postprocess(
        PostprocessOptions(
            output_dir=args.output,
            glossary_file=args.glossary_file,
            local_only=args.local_only,
            rule_packs=tuple(getattr(args, "rule_pack", None) or ()) or None,
        )
    )
    if args.json_output:
        print(json.dumps(run, ensure_ascii=False, indent=2))
    else:
        print(print_run_summary(run))
    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    result = run_repair(
        RepairOptions(
            output_dir=args.output,
            strategy=args.strategy,
            model=args.model,
            fallback_model=args.fallback_model,
            window_padding=args.window_padding,
            max_window_seconds=getattr(args, "max_window_seconds", 300.0),
            include_warning_windows=getattr(args, "include_warning_windows", True),
            candidate_profiles=getattr(args, "candidate_profiles", None),
            plan_only=args.plan_only,
            local_only=args.local_only,
            window_id=getattr(args, "window_id", None),
        )
    )
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Repair directory: {result['repair_dir']}")
        print(f"Windows: {len(result.get('plan', {}).get('windows', []))}")
        if result.get("plan_only"):
            print("Plan only: true")
        elif result.get("repair_run"):
            print(
                f"Replacement segments: {result['repair_run'].get('replacement_segment_count', 0)}"
            )
    return 0


def cmd_diarize(args: argparse.Namespace) -> int:
    result = run_diarization(DiarizeOptions(output_dir=args.output, mode=args.mode))
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Diarization mode: {result['mode']}")
        print(f"Segments: {result['segment_count']}")
    return 0
