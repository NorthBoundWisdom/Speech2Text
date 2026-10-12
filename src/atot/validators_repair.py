from __future__ import annotations

from pathlib import Path
from typing import Any

from .validators_common import HEX_64, is_number as _is_number, read_json_file


def _expect_json_object(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing required file: {path}")
        return {}
    payload = read_json_file(path)
    if not isinstance(payload, dict):
        errors.append(f"{path}: must be a JSON object")
        return {}
    return payload


def _numeric_value(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _validate_window(window: Any, path: Path, index: int, errors: list[str]) -> None:
    if not isinstance(window, dict):
        errors.append(f"{path}: windows[{index}] must be an object")
        return
    start = window.get("start")
    end = window.get("end")
    start_value = _numeric_value(start)
    end_value = _numeric_value(end)
    if start_value is None:
        errors.append(f"{path}: windows[{index}].start must be numeric")
    if end_value is None:
        errors.append(f"{path}: windows[{index}].end must be numeric")
    if start_value is not None and end_value is not None and end_value <= start_value:
        errors.append(f"{path}: windows[{index}].end must be greater than start")
    if not isinstance(window.get("reasons"), list) and not isinstance(window.get("reason"), str):
        errors.append(f"{path}: windows[{index}] must include `reasons` or `reason`")


def _validate_segments_payload(path: Path, errors: list[str]) -> int:
    payload = _expect_json_object(path, errors)
    segments = payload.get("segments")
    if not isinstance(segments, list):
        errors.append(f"{path}: `segments` must be a list")
        return 0
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            errors.append(f"{path}: segments[{index}] must be an object")
            continue
        if not _is_number(segment.get("start")) or not _is_number(segment.get("end")):
            errors.append(f"{path}: segments[{index}] must include numeric start/end")
        if not isinstance(segment.get("text"), str):
            errors.append(f"{path}: segments[{index}].text must be a string")
    return len(segments)


def _repair_dir(path: Path) -> Path:
    return path if path.name == "repair" else path / "repair"


def validate_repair_artifacts(output_or_repair_dir: Path) -> list[str]:
    """Validate repair plans, replacement segments, snapshots, and audit artifacts."""
    errors: list[str] = []
    repair_dir = _repair_dir(output_or_repair_dir)
    plan_path = repair_dir / "repair_plan.json"
    plan = _expect_json_object(plan_path, errors)
    windows = plan.get("windows", [])
    if not isinstance(windows, list):
        errors.append(f"{plan_path}: `windows` must be a list")
        windows = []
    for index, window in enumerate(windows):
        _validate_window(window, plan_path, index, errors)

    run_files = sorted(repair_dir.glob("repair_run_*.json"))
    if not run_files:
        return errors

    windows_dir = repair_dir / "windows"
    if not windows_dir.is_dir():
        errors.append(f"missing repair windows directory: {windows_dir}")

    latest_run_path = run_files[-1]
    for run_path in run_files:
        run = _expect_json_object(run_path, errors)
        if run.get("success") is not True:
            errors.append(f"{run_path}: `success` must be true")
        repair_id = run.get("repair_id")
        if not isinstance(repair_id, int) or repair_id <= 0:
            errors.append(f"{run_path}: `repair_id` must be a positive integer")
        if run.get("strategy") != "bad-segments":
            errors.append(f"{run_path}: `strategy` must be `bad-segments`")
        run_plan = plan
        run_plan_path = (
            repair_dir / f"repair_plan_{repair_id:03d}.json" if isinstance(repair_id, int) else None
        )
        if run_plan_path is not None and run_plan_path.exists():
            run_plan = _expect_json_object(run_plan_path, errors)
        run_plan_windows = run_plan.get("windows", [])
        if not isinstance(run_plan_windows, list):
            errors.append(f"{run_plan_path or plan_path}: `windows` must be a list")
            run_plan_windows = []
        run_windows = run.get("windows")
        if not isinstance(run_windows, list):
            errors.append(f"{run_path}: `windows` must be a list")
            run_windows = []
        if len(run_windows) != len(run_plan_windows):
            errors.append(f"{run_path}: window count must match its repair plan")
        for index, window in enumerate(run_windows):
            _validate_window(window, run_path, index, errors)
        replacement_path: Path | None = None
        if isinstance(repair_id, int):
            run_replacement_path = repair_dir / f"replacement_segments_{repair_id:03d}.json"
            if run_replacement_path.exists():
                replacement_path = run_replacement_path
        if replacement_path is None and run_path == latest_run_path:
            replacement_path = repair_dir / "replacement_segments.json"
        expected_count = run.get("replacement_segment_count")
        if not isinstance(expected_count, int) or expected_count < 0:
            errors.append(f"{run_path}: `replacement_segment_count` must be a non-negative integer")
        elif replacement_path is not None and replacement_path.exists():
            replacement_count = _validate_segments_payload(replacement_path, errors)
            if expected_count != replacement_count:
                errors.append(
                    f"{run_path}: `replacement_segment_count` does not match {replacement_path.name}"
                )
        elif run_path == latest_run_path and replacement_path is not None:
            _validate_segments_payload(replacement_path, errors)
        if isinstance(repair_id, int):
            diff_path = repair_dir / f"diff_{repair_id:03d}.md"
            if not diff_path.exists():
                errors.append(f"missing repair diff: {diff_path}")
            elif "### Before" not in diff_path.read_text(encoding="utf-8"):
                errors.append(f"{diff_path}: diff must include before/after sections")
            decision_path = repair_dir / f"repair_decision_{repair_id:03d}.json"
            decision = _expect_json_object(decision_path, errors)
            if decision and decision.get("status") not in {
                "applied",
                "rejected",
                "requires_human_review",
            }:
                errors.append(
                    f"{decision_path}: status must be applied, rejected, or requires_human_review"
                )
            for label in ("pre", "post"):
                snapshot_path = repair_dir / f"{label}_repair_snapshot_{repair_id:03d}.json"
                snapshot = _expect_json_object(snapshot_path, errors)
                if snapshot:
                    digest = snapshot.get("segment_digest")
                    if not isinstance(digest, str) or not HEX_64.match(digest):
                        errors.append(
                            f"{snapshot_path}: `segment_digest` must be a sha256 hex string"
                        )
            for key in ("pre_segment_digest", "post_segment_digest"):
                digest = run.get(key)
                if not isinstance(digest, str) or not HEX_64.match(digest):
                    errors.append(f"{run_path}: `{key}` must be a sha256 hex string")
            audit_run_dir = repair_dir / "runs" / f"repair_run_{repair_id:03d}"
            if audit_run_dir.exists():
                audit_windows_dir = audit_run_dir / "windows"
                if not audit_windows_dir.is_dir():
                    errors.append(f"missing repair audit windows directory: {audit_windows_dir}")
                for index, window in enumerate(run_windows, start=1):
                    window_id = str(window.get("id") or f"repair-window-{index:04d}")
                    audit_window_dir = audit_windows_dir / window_id
                    for name in (
                        "input.wav",
                        "raw.json",
                        "segments.json",
                        "corrected.json",
                        "qa_before_window.json",
                        "qa_after_window.json",
                        "replacement.diff.md",
                        "decision.json",
                        "audit.json",
                    ):
                        path = audit_window_dir / name
                        if not path.exists():
                            errors.append(f"missing repair audit artifact: {path}")
                    decision = _expect_json_object(audit_window_dir / "decision.json", errors)
                    action = decision.get("action")
                    if action not in {"apply", "reject"}:
                        errors.append(
                            f"{audit_window_dir / 'decision.json'}: action must be apply or reject"
                        )

    for index, _window in enumerate(windows, start=1):
        prefix = windows_dir / f"repair_{index:04d}"
        for suffix in (".raw.json", ".segments.json", ".corrected.json"):
            path = prefix.with_suffix(suffix)
            if suffix == ".segments.json":
                _validate_segments_payload(path, errors)
                continue
            payload = _expect_json_object(path, errors)
            if suffix == ".corrected.json":
                if not isinstance(payload.get("segments"), list):
                    errors.append(f"{path}: `segments` must be a list")
                if "corrections" not in payload:
                    errors.append(f"{path}: missing `corrections`")
            if "window" not in payload:
                errors.append(f"{path}: missing `window`")
        wav_path = prefix.with_suffix(".wav")
        if not wav_path.exists():
            errors.append(f"missing repair window audio: {wav_path}")

    run_json_path = repair_dir.parent / "run.json"
    if run_json_path.exists():
        run_json = _expect_json_object(run_json_path, errors)
        repair_state = run_json.get("repair")
        if not isinstance(repair_state, dict):
            errors.append(f"{run_json_path}: missing repair state")
        else:
            ids = repair_state.get("repair_run_ids")
            if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
                errors.append(f"{run_json_path}: repair.repair_run_ids must be a list of strings")
            else:
                for run_file in run_files:
                    if run_file.name not in ids:
                        errors.append(f"{run_json_path}: missing repair run id `{run_file.name}`")
    return errors
