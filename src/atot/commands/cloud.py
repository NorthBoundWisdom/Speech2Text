from __future__ import annotations

import argparse
import json
from typing import Any

from ..cloud.output_state import CloudOutputOptions
from ..cloud.prepare import CloudPrepareOptions, prepare_cloud_input
from ..cloud.review import (
    apply_cloud_patches,
    write_cloud_glossary_review,
    write_cloud_polish_suggestions,
)
from ..cloud.summary_outputs import write_cloud_short_title, write_cloud_summary


def cmd_cloud_prepare(args: argparse.Namespace) -> int:
    if args.local_only:
        raise ValueError("--local-only refuses cloud input generation.")
    result = prepare_cloud_input(
        CloudPrepareOptions(
            output_dir=args.output, redact=args.redact, chunk_minutes=args.chunk_minutes
        )
    )
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        manifest = result.get("manifest", {})
        print(f"Cloud input directory: {result['input_dir']}")
        print(f"Contains audio: {manifest.get('contains_audio')}")
        print(f"Contains video: {manifest.get('contains_video')}")
        print(f"QA status: {manifest.get('qa_status')}")
        privacy_findings = manifest.get("privacy_findings", [])
        if privacy_findings:
            print(f"Privacy review: {manifest.get('privacy_review_file')}")
            print("Confirm or redact privacy findings before sharing cloud input.")
    return 0


def cmd_cloud_summarize(args: argparse.Namespace) -> int:
    _reject_cloud_local_only(args)
    _print_cloud_result(
        write_cloud_summary(_cloud_output_options(args)), json_output=args.json_output
    )
    return 0


def cmd_cloud_glossary_review(args: argparse.Namespace) -> int:
    _reject_cloud_local_only(args)
    _print_cloud_result(
        write_cloud_glossary_review(_cloud_output_options(args)), json_output=args.json_output
    )
    return 0


def cmd_cloud_polish(args: argparse.Namespace) -> int:
    _reject_cloud_local_only(args)
    _print_cloud_result(
        write_cloud_polish_suggestions(_cloud_output_options(args)), json_output=args.json_output
    )
    return 0


def cmd_cloud_title(args: argparse.Namespace) -> int:
    _reject_cloud_local_only(args)
    _print_cloud_result(
        write_cloud_short_title(_cloud_output_options(args), force=getattr(args, "force", False)),
        json_output=args.json_output,
    )
    return 0


def cmd_cloud_apply_patches(args: argparse.Namespace) -> int:
    _reject_cloud_local_only(args)
    _print_cloud_result(
        apply_cloud_patches(args.output, args.patches, mode=args.mode), json_output=args.json_output
    )
    return 0


def _print_cloud_result(result: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    outputs = result.get("outputs")
    if outputs:
        print("Outputs:")
        for item in outputs:
            print(f"  - {item}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _reject_cloud_local_only(args: argparse.Namespace) -> None:
    if getattr(args, "local_only", False):
        raise ValueError("--local-only refuses cloud-stage file generation or patch application.")


def _cloud_output_options(args: argparse.Namespace) -> CloudOutputOptions:
    mode = getattr(args, "mode", "auto")
    if getattr(args, "from_readable", False):
        mode = "direct"
    if getattr(args, "stream_summary", False) and mode != "direct":
        raise ValueError("--stream-summary requires --from-readable or --mode direct.")
    return CloudOutputOptions(
        output_dir=args.output,
        call_api=getattr(args, "call_api", False),
        prompt_file=getattr(args, "prompt_file", None),
        summary_mode=mode,
        direct_readable=mode == "direct",
        direct_readable_char_limit=getattr(args, "direct_readable_char_limit", 20_000),
        allow_long_direct=getattr(args, "allow_long_direct", False),
        stream_summary=getattr(args, "stream_summary", False),
        retry_count=getattr(args, "retry_count", 2),
        retry_backoff_seconds=getattr(args, "retry_backoff_seconds", 0.25),
    )
