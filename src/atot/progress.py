from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .numeric import as_int
from .runinfo import now_iso
from .utils import read_json, write_json_atomic


LOCAL_DONE_STATUSES = {"transcribed", "transcribed_after_cache_mismatch", "skipped_existing"}


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _details_dir(output_dir: Path) -> Path:
    return output_dir


def _event_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def local_progress(output_dir: str | Path) -> dict[str, Any]:
    base = Path(output_dir).expanduser()
    details = _details_dir(base)
    run = _read_json_object(details / "run.json")
    rows = _event_rows(details / "events.jsonl")
    chunks = run.get("chunks", []) if isinstance(run.get("chunks"), list) else []
    total = len(chunks)
    completed = 0
    active_chunk = None
    current_stage = "missing"
    stages_seen: list[str] = []

    if chunks:
        completed = sum(
            1
            for item in chunks
            if isinstance(item, dict) and item.get("status") in LOCAL_DONE_STATUSES
        )

    chunk_done: set[int] = set()
    for row in rows:
        if row.get("event") == "stage":
            current_stage = str(row.get("stage") or current_stage)
            if current_stage not in stages_seen:
                stages_seen.append(current_stage)
        if row.get("event") != "chunk":
            continue
        chunk_index = as_int(row.get("chunk"))
        if chunk_index is None:
            continue
        total = max(total, as_int(row.get("total_chunks")) or 0)
        status = str(row.get("status") or "")
        if status == "started":
            active_chunk = chunk_index
        elif status in LOCAL_DONE_STATUSES:
            chunk_done.add(chunk_index)
            if active_chunk == chunk_index:
                active_chunk = None

    if chunk_done:
        completed = max(completed, len(chunk_done))
    if run.get("success") is True and total:
        completed = total
        current_stage = "complete"

    return {
        "status": "done" if run.get("success") is True else "running" if rows else "missing",
        "stage": current_stage,
        "completed": completed,
        "total": total,
        "percent": round((completed / total) * 100, 1) if total else 0.0,
        "active_chunk": active_chunk,
        "stages_seen": stages_seen,
    }


def cloud_progress(output_dir: str | Path) -> dict[str, Any]:
    base = Path(output_dir).expanduser()
    input_manifest = _read_json_object(base / "cloud" / "input" / "manifest.json")
    output_manifest = _read_json_object(base / "cloud" / "manifest.json")
    run = _read_json_object(_details_dir(base) / "run.json")
    cloud_run = run.get("cloud", {}) if isinstance(run.get("cloud"), dict) else {}
    summary_state = str(cloud_run.get("summary_state") or "")
    chunk_inputs = (
        input_manifest.get("text_chunks", [])
        if isinstance(input_manifest.get("text_chunks"), list)
        else []
    )
    chunk_dir = base / "cloud" / "chunk_summaries"
    chunk_outputs = sorted(chunk_dir.glob("chunk_*.summary.json"))
    completed = 0
    failed = 0
    for path in chunk_outputs:
        payload = _read_json_object(path)
        if payload.get("success") is False:
            failed += 1
        elif payload:
            completed += 1
    total = len(chunk_inputs) or len(chunk_outputs)
    summary_exists = (base / "cloud" / "summary.md").exists()
    prepared = bool(input_manifest)
    lock_exists = (base / "cloud" / "summary.lock").exists()

    if summary_state:
        status = summary_state
    elif not prepared:
        status = "missing"
    elif lock_exists and not summary_exists:
        status = "running"
    elif summary_exists and (failed or output_manifest.get("source") == "partial_cloud"):
        status = "partial"
    elif summary_exists:
        status = "complete"
    else:
        status = "prepared"

    return {
        "status": status,
        "prepared": prepared,
        "summary_exists": summary_exists,
        "completed": completed,
        "total": total,
        "failed": failed,
        "percent": round((completed / total) * 100, 1)
        if total
        else (100.0 if summary_exists else 0.0),
        "outputs": output_manifest.get("output_files", [])
        if isinstance(output_manifest.get("output_files"), list)
        else [],
    }


def update_cloud_summary_state(output_dir: str | Path, state: str, **fields: Any) -> dict[str, Any]:
    base = Path(output_dir).expanduser().resolve()
    run_path = base / "run.json"
    run = _read_json_object(run_path)
    if not run:
        return {}
    cloud = run.get("cloud", {}) if isinstance(run.get("cloud"), dict) else {}
    cloud.update(
        {
            "summary_state": state,
            "summary_updated_at": now_iso(),
            "audio_uploaded": False,
            **fields,
        }
    )
    run["cloud"] = cloud
    write_json_atomic(run_path, run)
    return run
