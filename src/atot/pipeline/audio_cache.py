from __future__ import annotations

import hashlib
from json import JSONDecodeError
import shlex
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..runinfo import now_iso
from ..utils import read_json


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "sha256": sha256_file(path),
    }


def prepared_audio_fingerprint(
    path: Path, *, prepare_command: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = file_fingerprint(path)
    try:
        with wave.open(str(path), "rb") as wav:
            payload.update(
                {
                    "duration": wav.getnframes() / wav.getframerate()
                    if wav.getframerate()
                    else 0.0,
                    "sample_rate": wav.getframerate(),
                    "channels": wav.getnchannels(),
                }
            )
    except wave.Error:
        payload.update({"duration": None, "sample_rate": None, "channels": None})
    args = [str(item) for item in prepare_command.get("args", [])] if prepare_command else []
    command_text = shlex.join(args) if args else ""
    tool = str(prepare_command.get("tool", "")) if prepare_command else ""
    payload["prepare_tool"] = tool
    payload["prepare_command"] = command_text
    payload["ffmpeg_command"] = command_text if tool == "ffmpeg" else ""
    return payload


def prepared_meta_payload(
    *,
    input_file: dict[str, Any],
    prepared_audio: dict[str, Any],
    prepare_command: dict[str, Any],
    sample_rate: int,
) -> dict[str, Any]:
    args = [str(item) for item in prepare_command.get("args", [])]
    return {
        "schema_version": 1,
        "created_at": now_iso(),
        "input_file": input_file,
        "prepare": {
            "tool": str(prepare_command.get("tool", "")),
            "available": bool(prepare_command.get("available")),
            "sample_rate": sample_rate,
            "args": args,
            "command": shlex.join(args) if args else "",
        },
        "prepared_audio": prepared_audio,
    }


def prepared_meta_matches(
    meta_path: Path,
    *,
    input_file: dict[str, Any],
    sample_rate: int,
    prepare_command: dict[str, Any],
) -> bool:
    if not meta_path.exists():
        return False
    try:
        payload = read_json(meta_path)
    except (OSError, JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    input_payload = payload.get("input_file")
    prepare_payload = payload.get("prepare")
    recorded_input: dict[str, Any] = input_payload if isinstance(input_payload, dict) else {}
    recorded_prepare: dict[str, Any] = prepare_payload if isinstance(prepare_payload, dict) else {}
    args = [str(item) for item in prepare_command.get("args", [])]
    return (
        recorded_input.get("sha256") == input_file.get("sha256")
        and int(recorded_prepare.get("sample_rate") or 0) == int(sample_rate)
        and str(recorded_prepare.get("command") or "") == (shlex.join(args) if args else "")
    )


@dataclass(frozen=True)
class PreparedAudioCacheDecision:
    meta_matches: bool
    overwrite: bool
    reason: str


def prepared_audio_cache_decision(
    *,
    prepared_wav: Path,
    meta_path: Path,
    input_file: dict[str, Any],
    sample_rate: int,
    prepare_command: dict[str, Any],
    force_prepare: bool,
    input_changed: bool,
) -> PreparedAudioCacheDecision:
    meta_matches = prepared_meta_matches(
        meta_path,
        input_file=input_file,
        sample_rate=sample_rate,
        prepare_command=prepare_command,
    )
    if force_prepare:
        return PreparedAudioCacheDecision(
            meta_matches=meta_matches, overwrite=True, reason="force_prepare"
        )
    if input_changed:
        return PreparedAudioCacheDecision(
            meta_matches=meta_matches, overwrite=True, reason="input_changed"
        )
    if prepared_wav.exists() and not meta_matches:
        return PreparedAudioCacheDecision(
            meta_matches=meta_matches,
            overwrite=True,
            reason="prepared_meta_mismatch",
        )
    return PreparedAudioCacheDecision(
        meta_matches=meta_matches, overwrite=False, reason="cache_valid_or_missing"
    )


_sha256_file = sha256_file
_file_fingerprint = file_fingerprint
_prepared_audio_fingerprint = prepared_audio_fingerprint
_prepared_meta_payload = prepared_meta_payload
_prepared_meta_matches = prepared_meta_matches
_prepared_audio_cache_decision = prepared_audio_cache_decision
