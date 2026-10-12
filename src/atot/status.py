from __future__ import annotations

from pathlib import Path
from typing import Any

from .progress import cloud_progress, local_progress
from .qa import build_qa_report, qa_to_markdown
from .utils import read_json, write_text_atomic


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _details_dir(output_dir: Path) -> Path:
    return output_dir


def _exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def _tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def disk_usage_report(output_dir: Path) -> dict[str, Any]:
    details = _details_dir(output_dir)
    chunks = details / "chunks"
    raw_audio = 0
    run = _read_json_object(details / "run.json")
    input_value = str(run.get("input_path") or "")
    if input_value:
        input_path = Path(input_value)
        if input_path.exists() and input_path.is_file():
            raw_audio = input_path.stat().st_size
    categories = {
        "raw_audio": raw_audio,
        "prepared_wav": _tree_size(details / "prepared.wav"),
        "chunks_wav": sum(path.stat().st_size for path in chunks.glob("*.wav") if path.is_file()),
        "chunks_json": sum(path.stat().st_size for path in chunks.glob("*.json") if path.is_file()),
        "text": sum(
            path.stat().st_size
            for path in output_dir.rglob("*")
            if path.is_file() and path.suffix in {".txt", ".md", ".srt", ".vtt"}
        ),
        "json": sum(path.stat().st_size for path in output_dir.rglob("*.json") if path.is_file()),
        "cloud": _tree_size(output_dir / "cloud"),
        "repair": _tree_size(output_dir / "repair"),
    }
    categories["total"] = _tree_size(output_dir)
    return categories


def _quality_state(
    *,
    state: dict[str, Any],
    run: dict[str, Any],
    review_summary: dict[str, Any],
) -> dict[str, Any]:
    qa_summary_payload = state.get("qa_summary")
    cloud_payload = run.get("cloud")
    qa_summary: dict[str, Any] = qa_summary_payload if isinstance(qa_summary_payload, dict) else {}
    run_cloud: dict[str, Any] = cloud_payload if isinstance(cloud_payload, dict) else {}
    blocking = int(qa_summary.get("blocking_issue_count", 0) or 0)
    warning = int(qa_summary.get("warning_count", 0) or 0)
    review_segments = int(review_summary.get("segment_issue_count", 0) or 0)
    suppressed = int(review_summary.get("suppressed_segment_count", 0) or 0)
    unresolved_terms = int(review_summary.get("issue_count", 0) or 0) + review_segments
    readable_health = (
        "pass"
        if state.get("has_readable_md") and state.get("qa_status") == "pass"
        else ("attention" if state.get("has_readable_md") else "missing")
    )
    return {
        "asr_health": state.get("qa_status", "unknown"),
        "readable_health": readable_health,
        "cloud_summary_ready": _exists(
            Path(str(state.get("output_dir", ""))) / "cloud" / "summary.md"
        ),
        "cloud_summary_mode": str(run_cloud.get("summary_mode") or ""),
        "unresolved_term_count": unresolved_terms,
        "suppressed_segment_count": suppressed,
        "qa_blocking_issue_count": blocking,
        "qa_warning_count": warning,
        "repair_optional": True,
    }


def inspect_output(output_dir: str | Path, *, write_report: bool = False) -> dict[str, Any]:
    """Summarize where a local transcription job stands and what to do next.

    This is intentionally workflow-level and generic. It does not score semantic
    correctness or apply episode-specific quality assumptions; it reads the
    auditable local artifacts and reports missing/stale/blocked stages.
    """
    base = Path(output_dir).expanduser().resolve()
    details = _details_dir(base)
    run = _read_json_object(details / "run.json")
    raw = _read_json_object(details / "raw.json")
    corrected = _read_json_object(details / "corrected.json")
    review = _read_json_object(details / "review.json")
    corrections = _read_json_object(details / "corrections.json")
    qa = _read_json_object(details / "qa.json") or build_qa_report(base)
    cloud_manifest = _read_json_object(base / "cloud" / "input" / "manifest.json")
    repair_plan = _read_json_object(base / "repair" / "repair_plan.json")

    qa_success = qa.get("success") if isinstance(qa, dict) else None
    review_summary = review.get("summary", {}) if isinstance(review.get("summary"), dict) else {}
    run_cloud = run.get("cloud", {}) if isinstance(run.get("cloud"), dict) else {}
    run_repair = run.get("repair", {}) if isinstance(run.get("repair"), dict) else {}

    state = {
        "output_dir": str(base),
        "has_run_json": bool(run),
        "has_raw_json": bool(raw),
        "has_corrected_json": bool(corrected),
        "has_corrected_txt": _exists(details / "transcript.corrected.txt")
        or _exists(base / "transcript.corrected.txt"),
        "has_readable_md": _exists(base / "transcript.readable.md"),
        "has_srt": _exists(details / "transcript.srt") or _exists(base / "transcript.srt"),
        "has_vtt": _exists(details / "transcript.vtt"),
        "qa_status": "pass" if qa_success is True else "fail" if qa_success is False else "unknown",
        "qa_summary": qa.get("summary", {}) if isinstance(qa, dict) else {},
        "review_summary": review_summary,
        "correction_rule_count": len(corrections.get("corrections", []))
        if isinstance(corrections.get("corrections"), list)
        else 0,
        "repair_applied": bool(run_repair.get("applied")),
        "repair_plan_exists": bool(repair_plan),
        "cloud_input_prepared": bool(cloud_manifest),
        "cloud_recorded_in_run": bool(run_cloud.get("prepared")),
        "cloud_outputs_dir_exists": (base / "cloud").exists(),
        "local_progress": local_progress(base),
        "cloud_progress": cloud_progress(base),
        "disk_usage": disk_usage_report(base),
    }
    state["quality_state"] = _quality_state(state=state, run=run, review_summary=review_summary)

    next_actions: list[dict[str, str]] = []
    if not state["has_raw_json"]:
        next_actions.append(
            {"priority": "high", "action": "run_transcribe", "reason": "Missing raw.json."}
        )
    if state["has_raw_json"] and not state["has_corrected_json"]:
        next_actions.append(
            {
                "priority": "high",
                "action": "run_postprocess",
                "reason": "Raw ASR exists but corrected JSON is missing.",
            }
        )
    if state["qa_status"] == "fail":
        next_actions.append(
            {
                "priority": "high",
                "action": "inspect_qa_or_optional_repair",
                "reason": "QA has blocking issues; repair is optional and explicit.",
            }
        )
    elif state["qa_status"] == "unknown":
        next_actions.append(
            {"priority": "medium", "action": "run_qa", "reason": "No QA report exists yet."}
        )
    if state["qa_status"] == "pass" and not state["cloud_input_prepared"]:
        next_actions.append(
            {
                "priority": "medium",
                "action": "cloud_prepare",
                "reason": "Local transcript passed QA and is ready for text-only handoff.",
            }
        )
    if state["cloud_input_prepared"] and not _exists(base / "cloud" / "summary.md"):
        next_actions.append(
            {
                "priority": "low",
                "action": "cloud_summarize",
                "reason": "Cloud input exists but summary.md is missing.",
            }
        )
    if review_summary and int(review_summary.get("segment_issue_count") or 0) > 0:
        next_actions.append(
            {
                "priority": "medium",
                "action": "review_terms",
                "reason": "Review report has segment-level issues.",
            }
        )
    if not next_actions:
        next_actions.append(
            {
                "priority": "low",
                "action": "no_immediate_action",
                "reason": "Core local artifacts are present and QA is not blocking.",
            }
        )

    report = {
        "success": state["qa_status"] != "fail" and state["has_raw_json"],
        "state": state,
        "next_actions": next_actions,
    }
    if write_report:
        write_text_atomic(details / "status.md", status_to_markdown(report))
    return report


def status_to_markdown(report: dict[str, Any]) -> str:
    state = report.get("state", {}) if isinstance(report.get("state"), dict) else {}
    lines = [
        "# SonaFolio Output Status",
        "",
        f"Status: {'OK' if report.get('success') else 'NEEDS ATTENTION'}",
        "",
    ]
    lines.extend(
        [
            f"- Output: `{state.get('output_dir', '')}`",
            f"- QA: {state.get('qa_status', 'unknown')}",
            f"- Raw JSON: {state.get('has_raw_json')}",
            f"- Corrected JSON: {state.get('has_corrected_json')}",
            f"- Corrected TXT: {state.get('has_corrected_txt')}",
            f"- SRT: {state.get('has_srt')}",
            f"- Cloud input prepared: {state.get('cloud_input_prepared')}",
            f"- Cloud summary mode: {state.get('quality_state', {}).get('cloud_summary_mode', '')}",
            f"- Local progress: {state.get('local_progress', {}).get('completed', 0)}/{state.get('local_progress', {}).get('total', 0)}",
            f"- Cloud progress: {state.get('cloud_progress', {}).get('completed', 0)}/{state.get('cloud_progress', {}).get('total', 0)}",
            f"- Repair applied: {state.get('repair_applied')}",
            f"- Disk usage: {state.get('disk_usage', {}).get('total', 0)} bytes",
            "",
            "## Next Actions",
            "",
        ]
    )
    for item in (
        report.get("next_actions", []) if isinstance(report.get("next_actions"), list) else []
    ):
        if isinstance(item, dict):
            lines.append(
                f"- {item.get('priority', 'medium')}: {item.get('action')} - {item.get('reason')}"
            )
    qa_summary = state.get("qa_summary") if isinstance(state.get("qa_summary"), dict) else {}
    if qa_summary:
        lines.extend(["", "## QA Summary", ""])
        for key in sorted(qa_summary):
            lines.append(f"- {key}: {qa_summary[key]}")
    quality_state = (
        state.get("quality_state") if isinstance(state.get("quality_state"), dict) else {}
    )
    if quality_state:
        lines.extend(["", "## Quality State", ""])
        for key in sorted(quality_state):
            lines.append(f"- {key}: {quality_state[key]}")
    return "\n".join(lines).strip() + "\n"


def qa_markdown_for_status(output_dir: str | Path) -> str:
    return qa_to_markdown(build_qa_report(output_dir))
