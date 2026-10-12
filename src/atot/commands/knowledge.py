from __future__ import annotations

import argparse
import json

from ..local_summary import LocalSummaryOptions, write_local_summary
from ..search import build_search_index, search_index


def cmd_summary_local(args: argparse.Namespace) -> int:
    result = write_local_summary(
        LocalSummaryOptions(
            output_dir=args.output,
            command=args.command,
            timeout=args.timeout,
        )
    )
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"summary: {result['output']}")
        print(f"source: {result['source']}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    if args.search_command == "index":
        result = build_search_index(args.root, args.index)
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"indexed: {result['document_count']}")
            print(f"index: {args.index}")
        return 0
    if args.search_command == "query":
        hits = [hit.to_json() for hit in search_index(args.query, args.index, limit=args.limit)]
        if args.json_output:
            print(json.dumps({"hits": hits}, ensure_ascii=False, indent=2))
        else:
            for hit in hits:
                stamp = f" [{hit['timestamp']}]" if hit["timestamp"] else ""
                print(f"{hit['episode']}{stamp}: {hit['line']}")
        return 0
    raise ValueError(f"Unknown search command: {args.search_command}")
