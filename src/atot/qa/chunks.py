from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..json_io import read_json_if_exists
from ..numeric import as_float
from ..utils import compact_ws


def _issue(
    severity: str,
    issue_type: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    return {"severity": severity, "type": issue_type, "message": message, **extra}


def _sha256_json(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(data).hexdigest()


def _resolve_recorded_path(path_text: Any, *, details_dir: Path) -> Path:
    path = Path(str(path_text or ""))
    if path.is_absolute() or path.exists():
        return path
    for candidate in (details_dir.parent / path, details_dir / path):
        if candidate.exists():
            return candidate
    return path


def _rounded(value: Any) -> float:
    return round(float(value), 3)


def _as_float(value: Any) -> float | None:
    return as_float(value)


def _chunk_layout_coverage_issues(
    run: dict[str, Any] | None, manifest: dict[str, Any] | None
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    layout = manifest.get("chunk_layout") if isinstance(manifest, dict) else None
    if not isinstance(layout, dict) and isinstance(run, dict):
        layout = run.get("chunk_layout")
    if not isinstance(layout, dict):
        return issues
    chunks = layout.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        issues.append(
            _issue("blocker", "missing_chunk_layout_entries", "Chunk layout has no chunk entries")
        )
        return issues
    audio_duration = _as_float(layout.get("audio_duration"))
    previous_core_end: float | None = None
    previous_source_end: float | None = None
    tolerance = 0.05
    for position, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            issues.append(
                _issue(
                    "blocker",
                    "invalid_chunk_layout_entry",
                    "Chunk layout entry must be an object",
                    index=position,
                )
            )
            continue
        source_start_value = _as_float(chunk.get("source_start"))
        source_end_value = _as_float(chunk.get("source_end"))
        core_start_value = _as_float(chunk.get("core_start"))
        core_end_value = _as_float(chunk.get("core_end"))
        if (
            source_start_value is None
            or source_end_value is None
            or core_start_value is None
            or core_end_value is None
        ):
            issues.append(
                _issue(
                    "blocker",
                    "invalid_chunk_layout_timing",
                    "Chunk layout timing must be numeric",
                    index=chunk.get("index", position),
                )
            )
            continue
        source_start = float(source_start_value)
        source_end = float(source_end_value)
        core_start = float(core_start_value)
        core_end = float(core_end_value)
        bounds_are_consistent = (
            source_start <= core_start + tolerance
            and core_start <= core_end + tolerance
            and core_end <= source_end + tolerance
        )
        if not bounds_are_consistent or source_end <= source_start or core_end <= core_start:
            issues.append(
                _issue(
                    "blocker",
                    "invalid_chunk_layout_bounds",
                    "Chunk source/core bounds are inconsistent",
                    index=chunk.get("index", position),
                    source_start=source_start,
                    source_end=source_end,
                    core_start=core_start,
                    core_end=core_end,
                )
            )
        if position == 0 and abs(core_start) > tolerance:
            issues.append(
                _issue(
                    "blocker",
                    "chunk_core_coverage_start_gap",
                    "First chunk core does not start at the beginning of the audio",
                    start=0.0,
                    end=core_start,
                    duration=round(core_start, 3),
                )
            )
        if previous_core_end is not None:
            core_gap = core_start - previous_core_end
            if abs(core_gap) > tolerance:
                issue_type = (
                    "chunk_core_coverage_gap" if core_gap > 0 else "chunk_core_coverage_overlap"
                )
                issues.append(
                    _issue(
                        "blocker",
                        issue_type,
                        "Adjacent chunk core windows do not form continuous coverage",
                        index=chunk.get("index", position),
                        start=previous_core_end,
                        end=core_start,
                        duration=round(abs(core_gap), 3),
                    )
                )
        if previous_source_end is not None and source_start > previous_source_end + tolerance:
            issues.append(
                _issue(
                    "warning",
                    "chunk_source_coverage_gap",
                    "Adjacent chunk source windows have a gap",
                    index=chunk.get("index", position),
                    start=previous_source_end,
                    end=source_start,
                    duration=round(source_start - previous_source_end, 3),
                )
            )
        previous_core_end = core_end
        previous_source_end = (
            source_end if previous_source_end is None else max(previous_source_end, source_end)
        )
    if (
        audio_duration is not None
        and previous_core_end is not None
        and abs(previous_core_end - audio_duration) > tolerance
    ):
        issues.append(
            _issue(
                "blocker",
                "chunk_core_coverage_end_gap",
                "Last chunk core does not end at the audio duration",
                start=previous_core_end,
                end=audio_duration,
                duration=round(abs(audio_duration - previous_core_end), 3),
            )
        )
    return issues


def _payload_has_core_text(payload: dict[str, Any]) -> bool:
    chunk = payload.get("chunk")
    result = payload.get("result")
    if not isinstance(chunk, dict) or not isinstance(result, dict):
        return False
    source_start = _as_float(chunk.get("source_start")) or 0.0
    core_start = _as_float(chunk.get("core_start"))
    core_end = _as_float(chunk.get("core_end"))
    if core_start is None or core_end is None:
        return False
    for segment in result.get("segments", []) if isinstance(result.get("segments"), list) else []:
        if not isinstance(segment, dict) or not compact_ws(str(segment.get("text", ""))):
            continue
        local_start = _as_float(segment.get("start"))
        local_end = _as_float(segment.get("end"))
        if local_start is None or local_end is None:
            continue
        midpoint = source_start + ((local_start + local_end) / 2.0)
        if core_start <= midpoint < core_end:
            return True
    return False


def _merged_chunk_indexes(segments: list[dict[str, Any]]) -> set[int]:
    indexes: set[int] = set()
    for segment in segments:
        try:
            indexes.add(int(segment["chunk_index"]))
        except (KeyError, TypeError, ValueError):
            continue
    return indexes


def chunk_issues(
    details_dir: Path,
    run: dict[str, Any] | None,
    manifest: dict[str, Any] | None,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find chunk layout, fingerprint, and merge consistency issues."""
    issues: list[dict[str, Any]] = []
    issues.extend(_chunk_layout_coverage_issues(run, manifest))
    chunks = run.get("chunks", []) if isinstance(run, dict) else []
    if not chunks and not isinstance(manifest, dict):
        return issues
    if isinstance(manifest, dict) and not manifest.get("chunk_layout_sha256"):
        issues.append(
            _issue(
                "diagnostic",
                "missing_chunk_layout_hash",
                "Chunk manifest lacks chunk_layout_sha256",
            )
        )
    if isinstance(run, dict) and isinstance(manifest, dict):
        run_layout_hash = run.get("chunk_layout_sha256")
        manifest_layout_hash = manifest.get("chunk_layout_sha256")
        if run_layout_hash and manifest_layout_hash and run_layout_hash != manifest_layout_hash:
            issues.append(
                _issue(
                    "blocker",
                    "chunk_layout_hash_mismatch",
                    "Chunk manifest hash does not match current run.json",
                    run_chunk_layout_sha256=run_layout_hash,
                    manifest_chunk_layout_sha256=manifest_layout_hash,
                )
            )
        manifest_layout = manifest.get("chunk_layout")
        if (
            isinstance(manifest_layout, dict)
            and manifest_layout_hash
            and _sha256_json(manifest_layout) != manifest_layout_hash
        ):
            issues.append(
                _issue(
                    "blocker",
                    "chunk_layout_manifest_hash_invalid",
                    "Chunk manifest hash does not match its chunk_layout payload",
                    manifest_chunk_layout_sha256=manifest_layout_hash,
                )
            )
    merged_indexes = _merged_chunk_indexes(segments)
    for chunk in chunks if isinstance(chunks, list) else []:
        json_path = _resolve_recorded_path(chunk.get("json"), details_dir=details_dir)
        if not json_path.exists():
            issues.append(
                _issue(
                    "blocker",
                    "missing_chunk_json",
                    "Chunk JSON listed in run.json is missing",
                    index=chunk.get("index"),
                    path=str(json_path),
                )
            )
            continue
        payload = read_json_if_exists(json_path)
        chunk_index = chunk.get("index")
        if not isinstance(payload, dict) or payload.get("success") is not True:
            issues.append(
                _issue(
                    "blocker",
                    "failed_chunk_json",
                    "Chunk JSON is missing success=true",
                    index=chunk_index,
                    path=str(json_path),
                )
            )
            continue
        if isinstance(run, dict):
            expected_hash = run.get("transcription_fingerprint_sha256")
            payload_hash = payload.get("transcription_fingerprint_sha256")
            payload_fingerprint = payload.get("transcription_fingerprint")
            run_fingerprint = run.get("transcription_fingerprint")
            if expected_hash and payload_hash and expected_hash != payload_hash:
                issues.append(
                    _issue(
                        "blocker",
                        "chunk_fingerprint_hash_mismatch",
                        "Chunk transcription fingerprint hash does not match current run.json",
                        index=chunk_index,
                        path=str(json_path),
                    )
                )
            elif (
                expected_hash
                and isinstance(payload_fingerprint, dict)
                and _sha256_json(payload_fingerprint) != expected_hash
            ):
                issues.append(
                    _issue(
                        "blocker",
                        "chunk_fingerprint_payload_mismatch",
                        "Chunk transcription fingerprint payload does not match current run.json",
                        index=chunk_index,
                        path=str(json_path),
                    )
                )
            elif (
                isinstance(payload_fingerprint, dict)
                and isinstance(run_fingerprint, dict)
                and payload_fingerprint != run_fingerprint
            ):
                issues.append(
                    _issue(
                        "blocker",
                        "chunk_fingerprint_payload_mismatch",
                        "Chunk transcription fingerprint payload does not match current run.json",
                        index=chunk_index,
                        path=str(json_path),
                    )
                )
        if _payload_has_core_text(payload):
            try:
                expected_index = int(chunk_index)
            except (TypeError, ValueError):
                expected_index = None
            if expected_index is not None and expected_index not in merged_indexes:
                issues.append(
                    _issue(
                        "blocker",
                        "chunk_core_merge_missing",
                        "Chunk has transcribed text in its core window but merged transcript has no segment from that chunk",
                        index=expected_index,
                        path=str(json_path),
                    )
                )
        payload_chunk = payload.get("chunk")
        if isinstance(payload_chunk, dict):
            for key in ("index", "core_start", "core_end"):
                if key not in chunk:
                    continue
                try:
                    expected = int(chunk[key]) if key == "index" else _rounded(chunk[key])
                    actual = (
                        int(payload_chunk[key]) if key == "index" else _rounded(payload_chunk[key])
                    )
                except (KeyError, TypeError, ValueError):
                    issues.append(
                        _issue(
                            "blocker",
                            "chunk_timing_metadata_invalid",
                            "Chunk JSON timing metadata is invalid",
                            index=chunk_index,
                            path=str(json_path),
                            field=key,
                        )
                    )
                    continue
                if expected != actual:
                    issues.append(
                        _issue(
                            "blocker",
                            "chunk_timing_metadata_mismatch",
                            "Chunk JSON timing metadata does not match current run.json",
                            index=chunk_index,
                            path=str(json_path),
                            field=key,
                        )
                    )
        else:
            issues.append(
                _issue(
                    "blocker",
                    "missing_chunk_timing_metadata",
                    "Chunk JSON does not contain chunk timing metadata",
                    index=chunk_index,
                    path=str(json_path),
                )
            )
    return issues
