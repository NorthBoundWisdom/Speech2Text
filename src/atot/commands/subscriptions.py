from __future__ import annotations

import argparse
import json
from typing import Any

from ..subscriptions import (
    add_subscription,
    list_subscriptions,
    refresh_subscriptions,
    remove_subscription,
)


def cmd_subscriptions(args: argparse.Namespace) -> int:
    library_root = args.library_root if getattr(args, "library_root", None) else None
    common: dict[str, Any] = {}
    if library_root is not None:
        common["library_root"] = library_root
    if args.subscriptions_command == "add":
        payload = add_subscription(args.url, group_name=args.group_name, limit=args.limit, **common)
    elif args.subscriptions_command == "list":
        payload = list_subscriptions(**common)
    elif args.subscriptions_command == "refresh":
        payload = refresh_subscriptions(
            subscription_id=args.id,
            refresh_all=args.refresh_all,
            limit=None if getattr(args, "full_history", False) else args.limit,
            **common,
        )
    elif args.subscriptions_command == "remove":
        payload = remove_subscription(args.id, **common)
    else:
        raise ValueError(f"Unknown subscriptions command: {args.subscriptions_command}")
    _print_json_or_summary(payload, json_output=args.json_output)
    return 0


def _print_json_or_summary(payload: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
