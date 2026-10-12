from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any
import webbrowser

from .runinfo import now_iso
from .utils import read_json, write_json_atomic


@dataclass(frozen=True)
class BatchOptions:
    queue: Path


def create_queue(
    queue: str | Path, inputs: list[Path], *, model: str, local_only: bool = False
) -> dict[str, Any]:
    jobs = [
        {
            "id": f"job_{index:04d}",
            "input": str(path),
            "model": model,
            "local_only": local_only,
            "status": "pending",
            "output": str(Path(path).parent / "output"),
            "created_at": now_iso(),
        }
        for index, path in enumerate(inputs, start=1)
    ]
    payload = {
        "schema_version": 1,
        "created_at": now_iso(),
        "paused": False,
        "local_only": local_only,
        "jobs": jobs,
    }
    write_json_atomic(queue, payload)
    return payload


def load_queue(queue: str | Path) -> dict[str, Any]:
    payload = read_json(queue)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError(f"Invalid batch queue: {queue}")
    return payload


def save_queue(queue: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    write_json_atomic(queue, payload)
    return payload


def set_paused(queue: str | Path, paused: bool) -> dict[str, Any]:
    payload = load_queue(queue)
    payload["paused"] = paused
    payload["updated_at"] = now_iso()
    return save_queue(queue, payload)


def queue_status(queue: str | Path) -> dict[str, Any]:
    payload = load_queue(queue)
    counts: dict[str, int] = {}
    for job in payload.get("jobs", []):
        if isinstance(job, dict):
            status = str(job.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
    return {
        "queue": str(queue),
        "paused": bool(payload.get("paused")),
        "counts": counts,
        "jobs": payload["jobs"],
    }


def run_queue(
    queue: str | Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    local_only: bool | None = None,
    resume: bool = False,
    retry_failed: bool = False,
) -> dict[str, Any]:
    queue_path = Path(queue)
    payload = load_queue(queue_path)
    queue_local_only = bool(payload.get("local_only")) if local_only is None else local_only
    if payload.get("paused"):
        return {"success": True, "paused": True, "started": 0}
    started = 0
    for job in payload["jobs"]:
        if not isinstance(job, dict):
            continue
        status = str(job.get("status") or "pending")
        if status == "done" and resume:
            continue
        if status == "failed" and retry_failed:
            job["previous_failure"] = {
                "returncode": job.get("returncode"),
                "stderr": job.get("stderr"),
                "failed_at": job.get("finished_at") or job.get("updated_at"),
            }
        elif status != "pending":
            continue
        if limit is not None and started >= limit:
            break
        command = [
            sys.executable,
            "-m",
            "atot.cli",
            "exec",
            "transcribe",
            str(job["input"]),
            "--job-dir",
            str(job.get("output") or Path(str(job["input"])).parent / "output"),
            "--model",
            str(job.get("model") or "large-v3-turbo"),
        ]
        if queue_local_only or bool(job.get("local_only")):
            command.append("--local-only")
            job["local_only"] = True
        job["command"] = command
        job["started_at"] = now_iso()
        if dry_run:
            job["status"] = "dry_run"
        else:
            result = subprocess.run(command, check=False, text=True, capture_output=True)
            job["returncode"] = result.returncode
            job["stdout"] = result.stdout[-4000:]
            job["stderr"] = result.stderr[-4000:]
            job["status"] = "done" if result.returncode == 0 else "failed"
            job["finished_at"] = now_iso()
        started += 1
        save_queue(queue_path, payload)
    payload["updated_at"] = now_iso()
    save_queue(queue_path, payload)
    return {"success": True, "paused": False, "started": started, "queue": str(queue_path)}


def output_dirs(queue: str | Path) -> list[str]:
    payload = load_queue(queue)
    dirs: list[str] = []
    for job in payload["jobs"]:
        if not isinstance(job, dict):
            continue
        output = str(job.get("output") or "")
        if output:
            dirs.append(output)
            continue
        input_path = Path(str(job.get("input", "")))
        if input_path.parent.name:
            dirs.append(str(input_path.parent / "output"))
    return dirs


def _select_job(
    payload: dict[str, Any], *, job_id: str | None = None, index: int | None = None
) -> dict[str, Any]:
    jobs = [job for job in payload["jobs"] if isinstance(job, dict)]
    if job_id:
        for job in jobs:
            if job.get("id") == job_id:
                return job
        raise ValueError(f"Unknown batch job id: {job_id}")
    if index is not None:
        if index < 1 or index > len(jobs):
            raise ValueError(f"Batch job index out of range: {index}")
        return jobs[index - 1]
    if len(jobs) != 1:
        raise ValueError(
            "Select a batch job with --job-id or --index when the queue has multiple jobs."
        )
    return jobs[0]


def output_dir_for_job(
    queue: str | Path, *, job_id: str | None = None, index: int | None = None
) -> str:
    payload = load_queue(queue)
    job = _select_job(payload, job_id=job_id, index=index)
    output = str(job.get("output") or "")
    if output:
        return output
    input_path = Path(str(job.get("input", "")))
    return str(input_path.parent / "output")


def open_output_dir(
    queue: str | Path,
    *,
    job_id: str | None = None,
    index: int | None = None,
    create: bool = False,
    print_only: bool = False,
    opener: Any | None = None,
) -> dict[str, Any]:
    output = Path(output_dir_for_job(queue, job_id=job_id, index=index))
    if create:
        output.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output}")
    if print_only:
        return {"success": True, "output": str(output), "opened": False}
    open_fn = opener or (lambda path: webbrowser.open(path.resolve().as_uri()))
    opened = bool(open_fn(output))
    return {"success": opened, "output": str(output), "opened": opened}
