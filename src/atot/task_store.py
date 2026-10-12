from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .paths import path_context
from .safe_paths import confined_path, validate_identifier
from .runinfo import now_iso
from .utils import ensure_dir, read_json, write_json_atomic


TASK_EVENT_TYPES = {
    "task.created",
    "task.stage",
    "task.progress",
    "task.output",
    "task.finished",
    "task.failed",
}


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    kind: str
    title: str
    task_dir: Path
    events_path: Path


class TaskStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = ensure_dir(root or (path_context().cache_dir / "tasks"))

    def _path(self, task_id: str, name: str = "") -> Path:
        return confined_path(self.root / validate_identifier(task_id) / name, self.root)

    def create_task(self, kind: str, title: str, **fields: Any) -> TaskRecord:
        task_id = f"{kind}-{uuid4().hex[:12]}"
        task_dir = ensure_dir(self._path(task_id))
        record = TaskRecord(
            task_id=task_id,
            kind=kind,
            title=title,
            task_dir=task_dir,
            events_path=task_dir / "events.jsonl",
        )
        manifest = {
            "task_id": task_id,
            "kind": kind,
            "title": title,
            "created_at": now_iso(),
            **fields,
        }
        write_json_atomic(task_dir / "task.json", manifest)
        self.append(record, "task.created", **manifest)
        return record

    def append(self, task: TaskRecord | str, event: str, **fields: Any) -> dict[str, Any]:
        if event not in TASK_EVENT_TYPES:
            raise ValueError(f"Unknown task event type: {event}")
        record = self.record(task) if isinstance(task, str) else task
        if record.task_dir != self._path(record.task_id) or record.events_path != self._path(record.task_id, "events.jsonl"):
            raise ValueError("Task record points outside managed storage.")
        payload = {
            "event": event,
            "task_id": record.task_id,
            "created_at": now_iso(),
            **fields,
        }
        record.events_path.parent.mkdir(parents=True, exist_ok=True)
        with record.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return payload

    def record(self, task_id: str) -> TaskRecord:
        manifest_path = self._path(task_id, "task.json")
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise FileNotFoundError(f"Task not found: {task_id}")
        if str(manifest.get("task_id") or task_id) != task_id:
            raise ValueError("Task identity does not match its storage directory.")
        return TaskRecord(
            task_id=task_id,
            kind=str(manifest.get("kind") or "task"),
            title=str(manifest.get("title") or task_id),
            task_dir=manifest_path.parent,
            events_path=manifest_path.parent / "events.jsonl",
        )

    def events(self, task_id: str) -> list[dict[str, Any]]:
        path = self._path(task_id, "events.jsonl")
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
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

    def latest(self, *, limit: int = 20) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        for path in sorted(
            self.root.glob("*/task.json"), key=lambda item: item.stat().st_mtime, reverse=True
        ):
            self._path(path.parent.name, path.name)
            payload = read_json(path)
            if isinstance(payload, dict):
                events = self.events(str(payload.get("task_id") or path.parent.name))
                payload["last_event"] = events[-1] if events else None
                manifests.append(payload)
            if len(manifests) >= limit:
                break
        return manifests

    def status(self, task_id: str | None = None) -> dict[str, Any]:
        if task_id:
            record = self.record(task_id)
            events = self.events(task_id)
            return {
                "task": {
                    "task_id": record.task_id,
                    "kind": record.kind,
                    "title": record.title,
                    "task_dir": str(record.task_dir),
                },
                "events": events,
                "last_event": events[-1] if events else None,
            }
        return {"tasks": self.latest()}
