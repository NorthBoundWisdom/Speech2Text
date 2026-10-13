from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import errno
import os
from pathlib import Path
from typing import Any, Iterator

from ..runinfo import now_iso
from ..utils import ensure_dir, read_json, write_json_atomic

try:
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - Windows has no fcntl module.
    fcntl = None  # type: ignore[assignment]


def configured_output_language() -> str:
    from ..config_v2 import load_atot_config

    return load_atot_config(include_api_key=False).summary.language


@dataclass(frozen=True)
class CloudOutputOptions:
    output_dir: Path
    call_api: bool = False
    prompt_file: Path | None = None
    summary_mode: str = "chunked"
    direct_readable: bool = False
    direct_readable_char_limit: int = 20_000
    allow_long_direct: bool = False
    stream_summary: bool = False
    retry_count: int = 2
    retry_backoff_seconds: float = 0.25
    output_language: str = field(default_factory=configured_output_language)


SUMMARY_OUTPUT_FILES = (
    "summary.md",
    "chapters.json",
    "chapters.md",
    "shownotes.md",
    "social_copy.md",
    "title_candidates.json",
    "title_candidates.md",
    "short_title.txt",
    "terms.json",
    "terms.md",
    "uncertainty_report.md",
    "fact_or_term_uncertainties.md",
    "manifest.json",
)


def _cloud_dir(output_dir: Path) -> Path:
    return ensure_dir(output_dir / "cloud")


def _input_dir(output_dir: Path) -> Path:
    return output_dir / "cloud" / "input"


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


@contextmanager
def _cloud_summary_lock(output_dir: Path) -> Iterator[None]:
    cloud = _cloud_dir(output_dir)
    lock_path = cloud / "summary.lock"
    if fcntl is None:
        with _cloud_summary_file_lock(output_dir, lock_path):
            yield
        return
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            getattr(fcntl, "flock")(
                lock_file.fileno(), getattr(fcntl, "LOCK_EX") | getattr(fcntl, "LOCK_NB")
            )
        except BlockingIOError as exc:
            raise RuntimeError(f"Cloud summary is already running for: {output_dir}") from exc
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"pid={os.getpid()}\nstarted_at={now_iso()}\n")
        lock_file.flush()
        try:
            yield
        finally:
            getattr(fcntl, "flock")(lock_file.fileno(), getattr(fcntl, "LOCK_UN"))


@contextmanager
def _cloud_summary_file_lock(output_dir: Path, lock_path: Path) -> Iterator[None]:
    fd: int | None = None
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise RuntimeError(f"Cloud summary is already running for: {output_dir}") from exc
        raise
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            fd = None
            lock_file.write(f"pid={os.getpid()}\nstarted_at={now_iso()}\n")
            lock_file.flush()
        yield
    finally:
        if fd is not None:
            os.close(fd)
        _remove_file_if_exists(lock_path)


def _summary_strategy(source: str, outputs: list[str], mode: str | None = None) -> str:
    if mode:
        return mode
    if any(path.startswith("chunk_summaries/") for path in outputs):
        return "map_reduce"
    return source


def _record_cloud_outputs(
    output_dir: Path, outputs: list[str], *, source: str, mode: str | None = None
) -> None:
    run_path = output_dir / "run.json"
    manifest_path = "cloud/manifest.json"
    output_paths = [f"cloud/{item}" for item in outputs]
    strategy = _summary_strategy(source, outputs, mode)
    if not run_path.exists():
        _write_cloud_output_manifest(
            output_dir, [manifest_path, *output_paths], source=source, mode=strategy
        )
        return
    run = _read_json_object(run_path)
    existing = run.get("cloud", {}) if isinstance(run.get("cloud"), dict) else {}
    existing_outputs = (
        existing.get("outputs", []) if isinstance(existing.get("outputs"), list) else []
    )
    merged = list(dict.fromkeys([*map(str, existing_outputs), manifest_path, *output_paths]))
    run["schema_version"] = run.get("schema_version", 2)
    run["cloud"] = {
        "prepared": bool(existing.get("prepared", False)),
        "audio_uploaded": False,
        "source": source,
        "summary_mode": strategy,
        "summary_state": "partial" if source == "partial_cloud" else "complete",
        "summary_updated_at": now_iso(),
        "outputs": merged,
    }
    write_json_atomic(run_path, run)
    _write_cloud_output_manifest(output_dir, merged, source=source, mode=strategy)


def _write_cloud_output_manifest(
    output_dir: Path, output_paths: list[str], *, source: str, mode: str | None = None
) -> None:
    cloud_outputs = [
        path.removeprefix("cloud/")
        for path in output_paths
        if path.startswith("cloud/") and not path.startswith("cloud/input/")
    ]
    output_files = sorted(dict.fromkeys(["manifest.json", *cloud_outputs]))
    strategy = _summary_strategy(source, output_files, mode)
    write_json_atomic(
        _cloud_dir(output_dir) / "manifest.json",
        {
            "created_at": now_iso(),
            "source": source,
            "contains_audio": False,
            "contains_video": False,
            "summary_strategy": strategy,
            "output_files": output_files,
        },
    )


def _remove_file_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def _clear_cloud_summary_outputs(output_dir: Path) -> None:
    cloud = _cloud_dir(output_dir)
    for relative in SUMMARY_OUTPUT_FILES:
        _remove_file_if_exists(cloud / relative)
    _clear_cloud_summary_output_state(output_dir)


def _clear_cloud_summary_output_state(output_dir: Path) -> None:
    run_path = output_dir / "run.json"
    if not run_path.exists():
        return
    run = _read_json_object(run_path)
    cloud = run.get("cloud", {}) if isinstance(run.get("cloud"), dict) else {}
    outputs = cloud.get("outputs", []) if isinstance(cloud.get("outputs"), list) else []
    summary_paths = {f"cloud/{name}" for name in SUMMARY_OUTPUT_FILES}
    summary_paths.add("cloud/manifest.json")
    filtered = [
        str(path)
        for path in outputs
        if str(path) not in summary_paths and not str(path).startswith("cloud/chunk_summaries/")
    ]
    cloud["outputs"] = filtered
    cloud.pop("source", None)
    cloud.pop("summary_mode", None)
    cloud.pop("summary_outputs", None)
    run["cloud"] = cloud
    write_json_atomic(run_path, run)
