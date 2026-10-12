from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..formats import segments_to_srt, segments_to_vtt
from ..segments import segment_digest, segment_plain_text
from ..utils import read_text


def _issue(
    severity: str,
    issue_type: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    return {"severity": severity, "type": issue_type, "message": message, **extra}


def _resolve_recorded_path(path_text: Any, *, details_dir: Path) -> Path:
    path = Path(str(path_text or ""))
    if path.is_absolute() or path.exists():
        return path
    candidate = details_dir / path
    if candidate.exists():
        return candidate
    return details_dir.parent / path


def _normalize_file_text(text: str | None) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def text_payload_consistency_issues(
    *,
    base: Path,
    details: Path,
    raw: dict[str, Any] | None,
    corrected: dict[str, Any] | None,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find stale or mismatched transcript text artifacts."""
    issues: list[dict[str, Any]] = []

    if isinstance(raw, dict) and isinstance(raw.get("segments"), list) and "text" in raw:
        expected_raw = segment_plain_text(raw["segments"])
        if _normalize_file_text(str(raw.get("text") or "")) != _normalize_file_text(expected_raw):
            issues.append(
                _issue(
                    "blocker",
                    "raw_json_text_mismatch",
                    "raw.json text does not match its segment texts",
                    expected_sha256=hashlib.sha256(expected_raw.encode("utf-8")).hexdigest(),
                )
            )

    if isinstance(corrected, dict) and isinstance(corrected.get("segments"), list):
        expected_corrected = segment_plain_text(corrected["segments"])
        if "text" in corrected and _normalize_file_text(
            str(corrected.get("text") or "")
        ) != _normalize_file_text(expected_corrected):
            issues.append(
                _issue(
                    "blocker",
                    "corrected_json_text_mismatch",
                    "corrected.json text does not match its segment texts",
                    expected_sha256=hashlib.sha256(expected_corrected.encode("utf-8")).hexdigest(),
                )
            )
        txt_path = details / "transcript.corrected.txt"
        if not txt_path.exists():
            txt_path = base / "transcript.corrected.txt"
        if txt_path.exists() and _normalize_file_text(read_text(txt_path)) != _normalize_file_text(
            expected_corrected
        ):
            issues.append(
                _issue(
                    "blocker",
                    "corrected_txt_mismatch",
                    "transcript.corrected.txt is stale or does not match corrected.json",
                    path=str(txt_path),
                )
            )

    srt_path = details / "transcript.srt"
    if not srt_path.exists():
        srt_path = base / "transcript.srt"
    if srt_path.exists() and segments:
        expected_srt = segments_to_srt(segments)
        if _normalize_file_text(srt_path.read_text(encoding="utf-8")) != _normalize_file_text(
            expected_srt
        ):
            issues.append(
                _issue(
                    "blocker",
                    "srt_content_mismatch",
                    "transcript.srt is stale or does not match current corrected segments",
                    path=str(srt_path),
                    segment_digest=segment_digest(segments),
                )
            )

    vtt_path = details / "transcript.vtt"
    if vtt_path.exists() and segments:
        expected_vtt = segments_to_vtt(segments)
        if _normalize_file_text(vtt_path.read_text(encoding="utf-8")) != _normalize_file_text(
            expected_vtt
        ):
            issues.append(
                _issue(
                    "blocker",
                    "vtt_content_mismatch",
                    "transcript.vtt is stale or does not match current corrected segments",
                    path=str(vtt_path),
                    segment_digest=segment_digest(segments),
                )
            )
    return issues


def run_file_state_issues(details: Path, run: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Find missing or changed files recorded in run.json."""
    issues: list[dict[str, Any]] = []
    if not isinstance(run, dict) or not run:
        return issues
    prepared = run.get("prepared_audio")
    if isinstance(prepared, dict) and prepared.get("path"):
        prepared_path = _resolve_recorded_path(prepared.get("path"), details_dir=details)
        if not prepared_path.exists():
            issues.append(
                _issue(
                    "blocker",
                    "prepared_audio_missing",
                    "Prepared WAV recorded in run.json is missing",
                    path=str(prepared_path),
                )
            )
        else:
            recorded_size = prepared.get("size_bytes")
            if isinstance(recorded_size, int) and prepared_path.stat().st_size != recorded_size:
                issues.append(
                    _issue(
                        "blocker",
                        "prepared_audio_size_mismatch",
                        "Prepared WAV size does not match run.json",
                        path=str(prepared_path),
                        expected_size_bytes=recorded_size,
                        actual_size_bytes=prepared_path.stat().st_size,
                    )
                )
    input_file = run.get("input_file")
    if isinstance(input_file, dict) and input_file.get("path"):
        input_path = Path(str(input_file.get("path")))
        if not input_path.exists():
            issues.append(
                _issue(
                    "warning",
                    "input_file_missing",
                    "Original input file recorded in run.json is missing; resume and audit may be less reliable",
                    path=str(input_path),
                )
            )
        else:
            recorded_size = input_file.get("size_bytes")
            if isinstance(recorded_size, int) and input_path.stat().st_size != recorded_size:
                issues.append(
                    _issue(
                        "warning",
                        "input_file_size_mismatch",
                        "Original input file size differs from run.json",
                        path=str(input_path),
                        expected_size_bytes=recorded_size,
                        actual_size_bytes=input_path.stat().st_size,
                    )
                )
    return issues
