from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import read_json, write_json_atomic, write_text_atomic


@dataclass(frozen=True)
class LocalSummaryOptions:
    output_dir: Path
    command: str | None = None
    timeout: int = 300


def _transcript_text(output_dir: Path) -> str:
    candidates = [
        output_dir / "transcript.readable.md",
        output_dir / "transcript.corrected.txt",
        output_dir / "transcript.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _title(output_dir: Path) -> str:
    manifest = output_dir / "manifest.json"
    if manifest.exists():
        payload = read_json(manifest)
        if isinstance(payload, dict) and payload.get("title"):
            return str(payload["title"])
    return output_dir.name


def _run_local_command(
    command: str, *, title: str, transcript: str, timeout: int
) -> tuple[str, dict[str, Any]]:
    prompt = (
        "请只基于输入的中文播客转写稿生成结构化 Markdown 总结，不要补充外部事实。\n"
        f"标题：{title}\n\n转写稿：\n{transcript}\n"
    )
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        shell=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    audit = {
        "command": command,
        "returncode": completed.returncode,
        "stderr": completed.stderr[-4000:],
    }
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError(f"local summary command failed with exit code {completed.returncode}")
    return completed.stdout.strip() + "\n", audit


def write_local_summary(options: LocalSummaryOptions) -> dict[str, Any]:
    output_dir = options.output_dir.expanduser().resolve()
    transcript = _transcript_text(output_dir)
    if not transcript.strip():
        raise FileNotFoundError(f"No transcript found in {output_dir}")
    title = _title(output_dir)
    summary_dir = output_dir / "local"
    summary_path = summary_dir / "summary.md"
    summary_json_path = summary_dir / "summary.json"
    if not options.command:
        if summary_path.exists():
            summary_path.unlink()
        payload = {
            "success": False,
            "source": "failed",
            "output": "",
            "audit": {"command": None, "error": "Local summary command is required."},
        }
        write_json_atomic(summary_json_path, payload)
        raise ValueError("Local summary command is required.")
    try:
        summary, audit = _run_local_command(
            options.command,
            title=title,
            transcript=transcript,
            timeout=options.timeout,
        )
    except Exception as exc:
        if summary_path.exists():
            summary_path.unlink()
        payload = {
            "success": False,
            "source": "failed",
            "output": "",
            "audit": {"command": options.command, "error": str(exc)},
        }
        write_json_atomic(summary_json_path, payload)
        raise
    write_text_atomic(summary_path, summary)
    payload = {
        "success": True,
        "source": "local_llm",
        "output": str(summary_path),
        "audit": audit,
    }
    write_json_atomic(summary_json_path, payload)
    return payload
