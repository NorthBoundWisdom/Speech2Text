from __future__ import annotations

from pathlib import Path
from typing import Any

from .segment_validation import validate_segment_payload_file
from .subtitles import validate_srt_text, validate_vtt_text
from .validation_contracts import RUN_JSON_CONTRACT
from .validators_cloud import (
    validate_cloud_input as validate_cloud_input,
    validate_cloud_outputs as validate_cloud_outputs,
    validate_cloud_package as validate_cloud_package,
)
from .validators_common import (
    is_relative_safe as is_relative_safe,
    read_json_file,
    safe_relative_path as _safe_relative_path,
)
from .validators_repair import validate_repair_artifacts as validate_repair_artifacts
from .validators_run_json import validate_run_json_payload


REQUIRED_OUTPUT_FILES = set(RUN_JSON_CONTRACT.required_output_files)


def _validate_segment_payload(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    segments, segment_errors = validate_segment_payload_file(path)
    errors.extend(segment_errors)
    return segments


def _validate_text_file(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing required file: {path}")
        return
    if not path.read_text(encoding="utf-8").strip():
        errors.append(f"{path}: must not be empty")


def validate_output_bundle(output_dir: Path) -> list[str]:
    errors: list[str] = []
    output_dir = output_dir.expanduser().resolve()
    details = output_dir

    for item in sorted(REQUIRED_OUTPUT_FILES):
        path = output_dir / item
        if item.endswith((".txt", ".md", ".srt", ".vtt", ".log")):
            _validate_text_file(path, errors)
        elif not path.exists():
            errors.append(f"missing required file: {path}")

    raw_segments = _validate_segment_payload(details / "raw.json", errors)
    corrected_segments = _validate_segment_payload(details / "corrected.json", errors)
    corrected_text_path = details / "transcript.corrected.txt"
    corrected_text = (
        corrected_text_path.read_text(encoding="utf-8") if corrected_text_path.exists() else ""
    )
    if corrected_segments and not any(
        str(segment.get("text", "")).strip() in corrected_text for segment in corrected_segments
    ):
        errors.append(f"{corrected_text_path}: does not contain corrected segment text")
    if raw_segments and corrected_segments and len(corrected_segments) > len(raw_segments) * 3:
        errors.append(f"{details / 'corrected.json'}: corrected segment count is unexpectedly high")

    run_path = details / "run.json"
    if run_path.exists():
        run = read_json_file(run_path)
        if not isinstance(run, dict):
            errors.append(f"{run_path}: must be a JSON object")
            run = {}
        else:
            errors.extend(f"{run_path}: {error}" for error in validate_run_json_payload(run))
        output_files = run.get("output_files")
        if not isinstance(output_files, dict):
            errors.append(f"{run_path}: `output_files` must be an object")
        else:
            missing = REQUIRED_OUTPUT_FILES - set(output_files)
            for item in sorted(missing):
                errors.append(f"{run_path}: missing output_files key `{item}`")
            for key, value in sorted(output_files.items()):
                expected = _safe_relative_path(output_dir, key) if isinstance(key, str) else None
                if expected is None:
                    errors.append(f"{run_path}: unsafe output_files key `{key}`")
                    continue
                if not isinstance(value, str) or not value:
                    errors.append(f"{run_path}: output_files.{key} must be a path string")
                    continue
                actual = Path(value)
                if actual != expected:
                    errors.append(f"{run_path}: output_files.{key} must equal `{expected}`")
                if key in REQUIRED_OUTPUT_FILES and not expected.exists():
                    errors.append(f"{run_path}: listed output file `{key}` does not exist")
    return errors


def validate_subtitle_files(output_dir: Path) -> list[str]:
    output_dir = output_dir.expanduser().resolve()
    errors: list[str] = []
    srt = output_dir / "transcript.srt"
    if srt.exists():
        errors.extend(
            f"{srt}: {item.get('message', item.get('type'))}"
            for item in validate_srt_text(srt.read_text(encoding="utf-8"))
        )
    vtt = output_dir / "transcript.vtt"
    if vtt.exists():
        errors.extend(
            f"{vtt}: {item.get('message', item.get('type'))}"
            for item in validate_vtt_text(vtt.read_text(encoding="utf-8"))
        )
    return errors
