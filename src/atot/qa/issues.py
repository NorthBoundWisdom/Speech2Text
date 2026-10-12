from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any

from .repair import is_repairable_issue_type

QA_SEVERITIES = {"blocker", "warning", "review", "diagnostic"}


def issue(
    severity: str,
    issue_type: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a QA issue payload with the shared base fields."""
    return {"severity": severity, "type": issue_type, "message": message, **extra}


def _sha256_json(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(data).hexdigest()


def _stable_issue_id(item: dict[str, Any]) -> str:
    signature = {
        key: item.get(key)
        for key in (
            "type",
            "severity",
            "source",
            "index",
            "segment_id",
            "start",
            "end",
            "message",
            "text",
            "chunk_index",
        )
        if key in item
    }
    digest = _sha256_json(signature)[:12]
    return f"qa_{digest}"


def _segment_ids_for_issue(item: dict[str, Any]) -> list[Any]:
    raw = item.get("segment_ids")
    if isinstance(raw, list):
        return raw
    if "segment_id" in item:
        return [item["segment_id"]]
    if "index" in item:
        return [item["index"]]
    return []


def _suggested_action(item: dict[str, Any]) -> str:
    if bool(item.get("repairable")):
        return "repair_window"
    severity = str(item.get("severity") or "warning")
    if severity == "blocker":
        return "manual_review"
    if severity == "warning":
        return "review_before_publish"
    return "diagnostic"


def _normalized_severity(item: dict[str, Any]) -> str:
    severity = str(item.get("severity") or "warning")
    if severity in QA_SEVERITIES:
        return severity
    return "warning"


def normalize_issue_contract(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize issue severity, IDs, repairability, segment IDs, and actions."""
    normalized: list[dict[str, Any]] = []
    seen: Counter[str] = Counter()
    for item in issues:
        item = dict(item)
        severity = _normalized_severity(item)
        issue_type = str(item.get("type") or "")
        item["severity"] = severity
        if "repairable" not in item and is_repairable_issue_type(issue_type, severity):
            item["repairable"] = True
        item.setdefault("repairable", False)
        item.setdefault("segment_ids", _segment_ids_for_issue(item))
        base_id = str(item.get("id") or _stable_issue_id(item))
        seen[base_id] += 1
        item["id"] = base_id if seen[base_id] == 1 else f"{base_id}_{seen[base_id]:02d}"
        item.setdefault("suggested_action", _suggested_action(item))
        normalized.append(item)
    return normalized
