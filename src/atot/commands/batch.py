from __future__ import annotations

import argparse
import json
from typing import Any

from ..batch import create_queue, open_output_dir, output_dirs, queue_status, run_queue, set_paused


def cmd_batch(args: argparse.Namespace) -> int:
    if args.batch_command == "create":
        payload = create_queue(
            args.queue, args.inputs, model=args.model, local_only=args.local_only
        )
        _print_json_or_summary(payload, json_output=args.json_output)
        return 0
    if args.batch_command == "run":
        payload = run_queue(
            args.queue,
            limit=args.limit,
            dry_run=args.dry_run,
            local_only=args.local_only,
            resume=args.resume,
            retry_failed=args.retry_failed,
        )
        _print_json_or_summary(payload, json_output=args.json_output)
        return 0
    if args.batch_command == "status":
        payload = queue_status(args.queue)
        _print_json_or_summary(payload, json_output=args.json_output)
        return 0
    if args.batch_command == "pause":
        set_paused(args.queue, True)
        print("paused")
        return 0
    if args.batch_command == "resume":
        set_paused(args.queue, False)
        print("resumed")
        return 0
    if args.batch_command == "outputs":
        for item in output_dirs(args.queue):
            print(item)
        return 0
    if args.batch_command == "open-output":
        payload = open_output_dir(
            args.queue,
            job_id=args.job_id,
            index=args.index,
            create=args.create,
            print_only=args.print_only,
        )
        if args.json_output:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload["output"])
        return 0
    raise ValueError(f"Unknown batch command: {args.batch_command}")


def _print_json_or_summary(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
