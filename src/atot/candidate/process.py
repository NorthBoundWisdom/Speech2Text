from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time


TIMEOUT_RETURN_CODE = 124
COMMAND_NOT_FOUND_RETURN_CODE = 127
MEMORY_POLL_INTERVAL_SECONDS = 0.1
IS_WINDOWS = os.name == "nt"


def child_pids(pid: int) -> list[int]:
    try:
        completed = subprocess.run(
            ["pgrep", "-P", str(pid)], text=True, capture_output=True, check=False
        )
    except OSError:
        return []
    if completed.returncode not in (0, 1):
        return []
    children: list[int] = []
    for line in completed.stdout.splitlines():
        try:
            children.append(int(line.strip()))
        except ValueError:
            continue
    return children


def process_tree_pids(pid: int) -> list[int]:
    seen: set[int] = set()
    stack = [pid]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(child_pids(current))
    return sorted(seen)


def rss_kb(pid: int) -> int:
    try:
        completed = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)], text=True, capture_output=True, check=False
        )
    except OSError:
        return 0
    if completed.returncode != 0:
        return 0
    try:
        return int(completed.stdout.strip() or "0")
    except ValueError:
        return 0


def process_tree_rss_mb(pid: int) -> float | None:
    total_rss_kb = sum(rss_kb(tree_pid) for tree_pid in process_tree_pids(pid))
    return round(total_rss_kb / 1024, 2) if total_rss_kb > 0 else None


def run_candidate_command(
    command: list[str], timeout: float | None
) -> tuple[int, float, float | None, bool, str, str]:
    started = time.perf_counter()
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_file,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr_file,
    ):
        try:
            if IS_WINDOWS:
                process: subprocess.Popen[str] = subprocess.Popen(
                    command,
                    text=True,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
            else:
                process = subprocess.Popen(
                    command,
                    text=True,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True,
                )
        except OSError as exc:
            return (
                COMMAND_NOT_FOUND_RETURN_CODE,
                time.perf_counter() - started,
                None,
                False,
                "",
                f"{exc}\n",
            )
        peak_rss_mb = process_tree_rss_mb(process.pid)
        timed_out = False
        while process.poll() is None:
            sample = process_tree_rss_mb(process.pid)
            if sample is not None:
                peak_rss_mb = sample if peak_rss_mb is None else max(peak_rss_mb, sample)
            if timeout is not None and time.perf_counter() - started >= timeout:
                timed_out = True
                _terminate_process_tree(process)
                break
            time.sleep(MEMORY_POLL_INTERVAL_SECONDS)
        process.wait()
        runtime_seconds = time.perf_counter() - started
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()
        if timed_out:
            timeout_note = f"Candidate command timed out after {timeout:.2f} seconds."
            stderr = f"{stderr.rstrip()}\n{timeout_note}\n" if stderr else f"{timeout_note}\n"
            return TIMEOUT_RETURN_CODE, runtime_seconds, peak_rss_mb, True, stdout, stderr
        return process.returncode, runtime_seconds, peak_rss_mb, False, stdout, stderr


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if process.poll() is None:
            process.kill()
        return
    try:
        getattr(os, "killpg")(process.pid, getattr(signal, "SIGKILL"))
    except OSError:
        process.kill()
