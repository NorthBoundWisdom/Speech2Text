from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio import write_wav_chunk
from .backends import ASRBackend, ASRTranscribeOptions, build_backend
from .corrections import apply_corrections_to_segments, segments_to_plain_text
from .entity_consistency import build_entity_consistency_report
from .formats import (
    enforce_monotonic_timeline,
    normalize_segments,
    segments_to_markdown,
    segments_to_srt,
    segments_to_timestamped_markdown,
    segments_to_vtt,
)
from .json_io import read_json_object
from .models import DEFAULT_MODEL_ALIAS
from .numeric import as_float, positive_float
from .profiles import DECODE_PROFILES
from .qa import build_qa_report, run_qa
from .repair_candidates import (
    evaluate_repair_candidates,
    normalize_repair_candidate_profiles,
)
from .repair_plan import build_repair_plan as _build_repair_plan
from .quality import build_quality_metrics
from .readable import compose_readable_transcript
from .review import build_review, review_to_markdown
from .runinfo import now_iso
from .runtime_defaults import (
    DEFAULT_COMPRESSION_RATIO_THRESHOLD,
    DEFAULT_LOGPROB_THRESHOLD,
    DEFAULT_NO_SPEECH_THRESHOLD,
)
from .platform_defaults import default_asr_backend
from .segment_validation import first_segment_list
from .segments import segment_digest, segment_plain_text
from .utils import ensure_dir, seconds_to_hms, write_json_atomic, write_text_atomic
from .writer import write_artifact_manifest


@dataclass(frozen=True)
class RepairOptions:
    """Options for planning and applying local transcript repair windows."""

    output_dir: Path
    strategy: str = "bad-segments"
    model: str = DEFAULT_MODEL_ALIAS
    fallback_model: str | None = None
    window_padding: float = 15.0
    max_window_seconds: float = 300.0
    include_warning_windows: bool = True
    plan_only: bool = False
    language: str | None = None
    word_timestamps: bool = False
    condition_on_previous_text: bool = True
    candidate_profiles: tuple[str, ...] | list[str] | None = None
    local_only: bool = False
    window_id: str | None = None


def _details_dir(output_dir: Path) -> Path:
    return output_dir


def _read_json_object(path: Path) -> dict[str, Any]:
    return read_json_object(path)


def _segments_from_output(output_dir: Path) -> list[dict[str, Any]]:
    details = _details_dir(output_dir)
    corrected = _read_json_object(details / "corrected.json")
    raw = _read_json_object(details / "raw.json")
    return first_segment_list(corrected, raw)


def _audio_duration_from_output(output_dir: Path) -> float | None:
    details = _details_dir(output_dir)
    corrected = _read_json_object(details / "corrected.json")
    raw = _read_json_object(details / "raw.json")
    run = _read_json_object(details / "run.json")
    for payload in (corrected, raw, run):
        duration = positive_float(payload.get("audio_duration"))
        if duration is not None:
            return duration
    return None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _optional_positive_float(value: Any, *, field: str) -> float | None:
    if value is None or value == "":
        return None
    number = as_float(value)
    if number is None:
        raise ValueError(f"`{field}` must be numeric when present.")
    if number <= 0:
        raise ValueError(f"`{field}` must be positive when present.")
    return number


def build_repair_plan(
    output_dir: str | Path,
    *,
    window_padding: float = 15.0,
    max_window_seconds: float = 300.0,
    include_warning_windows: bool = True,
) -> dict[str, Any]:
    """Build a repair plan from QA issues without changing transcript files.

    Args:
        output_dir: Transcription output bundle directory.
        window_padding: Seconds to extend each repair window around issues.
        max_window_seconds: Maximum duration for a merged repair window.
        include_warning_windows: Whether warning-level QA issues may produce
            repair windows.

    Returns:
        A repair plan dictionary with QA summary and candidate windows.
    """

    return _build_repair_plan(
        output_dir,
        details_dir=_details_dir,
        read_json_object=_read_json_object,
        build_qa_report=build_qa_report,
        segments_from_output=_segments_from_output,
        audio_duration_from_output=_audio_duration_from_output,
        window_padding=window_padding,
        max_window_seconds=max_window_seconds,
        include_warning_windows=include_warning_windows,
    )


def _repair_plan_for_options(output_dir: Path, options: RepairOptions) -> dict[str, Any]:
    plan = build_repair_plan(
        output_dir,
        window_padding=options.window_padding,
        max_window_seconds=options.max_window_seconds,
        include_warning_windows=options.include_warning_windows,
    )
    if not options.window_id:
        return plan
    requested = options.window_id
    filtered_windows = []
    for index, window in enumerate(plan["windows"], start=1):
        numbered_id = f"repair_{index:04d}"
        if requested in {str(window.get("id")), numbered_id}:
            filtered_windows.append(window)
    return {**plan, "windows": filtered_windows, "requested_window_id": requested}


def _next_repair_id(repair_dir: Path) -> int:
    existing = sorted(repair_dir.glob("repair_run_*.json"))
    if not existing:
        return 1
    ids: list[int] = []
    for path in existing:
        try:
            ids.append(int(path.stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return (max(ids) + 1) if ids else 1


def _offset_segments(
    result: dict[str, Any], window_start: float, *, window_end: float | None = None
) -> list[dict[str, Any]]:
    segments = result.get("segments", [])
    if not isinstance(segments, list):
        segments = []
    if not segments and result.get("text"):
        segments = [
            {
                "start": 0.0,
                "end": max(0.01, float(result.get("duration", 0.01))),
                "text": result.get("text"),
            }
        ]
    shifted: list[dict[str, Any]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        item = dict(segment)
        item["start"] = window_start + float(item.get("start", 0.0))
        item["end"] = window_start + float(item.get("end", item["start"] + 0.01))
        if window_end is not None:
            if float(item["start"]) >= window_end:
                continue
            item["end"] = min(float(item["end"]), window_end)
        if float(item["end"]) <= float(item["start"]):
            continue
        shifted.append(item)
    return normalize_segments(shifted)


def _replace_window_segments(
    original: list[dict[str, Any]],
    replacements: list[dict[str, Any]],
    *,
    start: float,
    end: float,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for segment in original:
        seg_start = float(segment.get("start", 0.0))
        seg_end = float(segment.get("end", seg_start))
        midpoint = (seg_start + seg_end) / 2.0
        if start <= midpoint <= end:
            continue
        kept.append(dict(segment))
    return enforce_monotonic_timeline(normalize_segments([*kept, *replacements]))


def _write_repaired_outputs(
    output_dir: Path,
    *,
    segments: list[dict[str, Any]],
    glossary: dict[str, Any],
    model: str,
    language: str | None,
    local_only: bool = False,
) -> dict[str, Any]:
    details = _details_dir(output_dir)
    raw_payload = _read_json_object(details / "raw.json")
    run_payload = _read_json_object(details / "run.json")
    input_path = (
        _optional_string(raw_payload.get("input_path"))
        or _optional_string(run_payload.get("input_path"))
        or ""
    )
    title = Path(input_path).stem or "Transcript"
    audio_duration = _optional_positive_float(
        raw_payload.get("audio_duration") or run_payload.get("audio_duration"),
        field="audio_duration",
    )
    corrected_segments, correction_report = apply_corrections_to_segments(
        segments,
        glossary,
        audio_duration=audio_duration,
    )
    corrected_text = segments_to_plain_text(corrected_segments)
    review = build_review(corrected_segments, glossary)
    review["entity_consistency"] = build_entity_consistency_report(corrected_segments, glossary)
    quality = build_quality_metrics(
        raw_segments=segments,
        corrected_segments=corrected_segments,
        corrections=correction_report,
        review=review,
    )
    write_json_atomic(
        details / "corrected.json",
        {
            "input_path": input_path,
            "model": model,
            "language": language,
            "audio_duration": audio_duration,
            "segments": corrected_segments,
            "text": corrected_text,
            "segment_digest": segment_digest(corrected_segments),
        },
    )
    write_text_atomic(details / "transcript.corrected.txt", corrected_text)
    readable = compose_readable_transcript(corrected_segments, title=title)
    write_text_atomic(output_dir / "transcript.readable.md", readable.markdown)
    write_json_atomic(details / "readable_transformations.json", readable.log)
    write_text_atomic(
        details / "transcript.md",
        segments_to_markdown(
            corrected_segments, title=title, corrected=True, model=model, input_path=input_path
        ),
    )
    write_text_atomic(
        details / "transcript.timestamped.md",
        segments_to_timestamped_markdown(corrected_segments, title=title),
    )
    write_text_atomic(details / "transcript.srt", segments_to_srt(corrected_segments))
    write_text_atomic(details / "transcript.vtt", segments_to_vtt(corrected_segments))
    write_json_atomic(details / "review.json", review)
    write_json_atomic(details / "entity_consistency.json", review["entity_consistency"])
    write_text_atomic(details / "review.md", review_to_markdown(review))
    write_json_atomic(
        details / "corrections.json",
        {
            "glossary_file": "",
            "episode_glossary_file": "",
            "effective_glossary_file": str(details / "glossary.effective.json"),
            "corrections": correction_report,
        },
    )
    qa = run_qa(output_dir)
    run = _read_json_object(details / "run.json")
    run.update(
        {
            "schema_version": run.get("schema_version", 2),
            "repair": {
                "applied": True,
                "updated_at": now_iso(),
                "repair_run_ids": [
                    str(path.name)
                    for path in sorted((output_dir / "repair").glob("repair_run_*.json"))
                ],
            },
            "local_only": local_only,
            "review": review.get("summary", {}),
            "qa": {
                "status": "pass" if qa.get("success") else "fail",
                **(qa.get("summary", {}) if isinstance(qa.get("summary"), dict) else {}),
            },
            "cloud": run.get("cloud", {"prepared": False, "audio_uploaded": False, "outputs": []}),
            "quality_metrics": quality,
        }
    )
    write_json_atomic(details / "run.json", run)
    return {"review": review, "qa": qa, "quality_metrics": quality}


def _repair_diff(
    window: dict[str, Any], before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> str:
    lines = [
        f"## Window {seconds_to_hms(float(window['start']))}-{seconds_to_hms(float(window['end']))}",
        "",
        "### Before",
        "",
        "\n".join(
            str(segment.get("text", "")).strip()
            for segment in before
            if str(segment.get("text", "")).strip()
        )
        or "(empty)",
        "",
        "### After",
        "",
        "\n".join(
            str(segment.get("text", "")).strip()
            for segment in after
            if str(segment.get("text", "")).strip()
        )
        or "(empty)",
        "",
        "### Reason",
        "",
        ", ".join(window.get("reasons", []) or [str(window.get("reason", ""))]),
        "",
    ]
    return "\n".join(lines)


def _window_segments(
    segments: list[dict[str, Any]], *, start: float, end: float
) -> list[dict[str, Any]]:
    return [
        segment
        for segment in segments
        if start <= (float(segment.get("start", 0.0)) + float(segment.get("end", 0.0))) / 2.0 <= end
    ]


def _window_qa_before(window: dict[str, Any], before: list[dict[str, Any]]) -> dict[str, Any]:
    issues = [item for item in window.get("source_issues", []) if isinstance(item, dict)]
    return {
        "success": not any(str(item.get("severity")) == "blocker" for item in issues),
        "summary": {
            "issue_count": len(issues),
            "segment_count": len(before),
            "source_issue_ids": [str(item) for item in window.get("source_issue_ids", [])],
        },
        "issues": issues,
    }


def _window_qa_after(
    window: dict[str, Any],
    replacements: list[dict[str, Any]],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    start = float(window["start"])
    end = float(window["end"])
    if not replacements:
        issues.append(
            {
                "type": "empty_repair_replacement",
                "severity": "blocker",
                "message": "Repair backend produced no replacement segments for this window.",
            }
        )
    previous_end: float | None = None
    for index, segment in enumerate(replacements):
        seg_start = float(segment.get("start", 0.0))
        seg_end = float(segment.get("end", seg_start))
        text = str(segment.get("text", "")).strip()
        if not text:
            issues.append({"type": "empty_segment_text", "severity": "blocker", "index": index})
        if seg_start < start - 0.05 or seg_end > end + 0.05:
            issues.append(
                {
                    "type": "replacement_outside_window",
                    "severity": "blocker",
                    "index": index,
                    "start": seg_start,
                    "end": seg_end,
                }
            )
        if previous_end is not None and seg_start < previous_end - 0.05:
            issues.append(
                {
                    "type": "replacement_overlap",
                    "severity": "blocker",
                    "index": index,
                    "start": seg_start,
                    "previous_end": previous_end,
                }
            )
        previous_end = max(previous_end if previous_end is not None else seg_end, seg_end)
    return {
        "success": not any(str(item.get("severity")) == "blocker" for item in issues),
        "summary": {"issue_count": len(issues), "segment_count": len(replacements)},
        "issues": issues,
    }


def _candidate_profile_options(
    options: RepairOptions, profile: str, *, language: str | None, prompt: str | None
) -> ASRTranscribeOptions:
    if profile != "default" and profile not in DECODE_PROFILES:
        raise ValueError(f"Unknown repair candidate profile: {profile}")
    profile_options = DECODE_PROFILES[profile].options if profile in DECODE_PROFILES else {}
    return ASRTranscribeOptions(
        model=options.fallback_model or options.model,
        language=language,
        prompt=prompt,
        word_timestamps=bool(profile_options.get("word_timestamps", options.word_timestamps)),
        condition_on_previous_text=bool(
            profile_options.get("condition_on_previous_text", options.condition_on_previous_text)
        ),
        temperature=profile_options.get("temperature", 0.0),
        no_speech_threshold=profile_options.get("no_speech_threshold", DEFAULT_NO_SPEECH_THRESHOLD),
        logprob_threshold=profile_options.get("logprob_threshold", DEFAULT_LOGPROB_THRESHOLD),
        compression_ratio_threshold=profile_options.get(
            "compression_ratio_threshold",
            DEFAULT_COMPRESSION_RATIO_THRESHOLD,
        ),
        hallucination_silence_threshold=profile_options.get("hallucination_silence_threshold"),
    )


def _update_run_repair_state(output_dir: Path, repair_dir: Path, applied_window_count: int) -> None:
    run_path = _details_dir(output_dir) / "run.json"
    if not run_path.exists():
        return
    run_payload = _read_json_object(run_path)
    repair_payload = run_payload.get("repair")
    repair_state: dict[str, Any] = repair_payload if isinstance(repair_payload, dict) else {}
    repair_state["applied"] = bool(repair_state.get("applied")) or applied_window_count > 0
    repair_state["repair_run_ids"] = [
        str(path.name) for path in sorted(repair_dir.glob("repair_run_*.json"))
    ]
    run_payload["repair"] = repair_state
    write_json_atomic(run_path, run_payload)


def run_repair(options: RepairOptions, *, backend: ASRBackend | None = None) -> dict[str, Any]:
    """Run local window repair for bad transcript segments.

    Args:
        options: Repair settings, including output directory and window policy.
        backend: Optional ASR backend override for tests or custom execution.

    Returns:
        A dictionary describing the repair plan, repair directory, selected
        candidates, replacement segment count, and whether changes were applied.

    Raises:
        ValueError: If the strategy, candidate profile, or persisted payload
            types are invalid.
        FileNotFoundError: If repair execution needs prepared audio and it is
            missing.
    """

    if options.strategy != "bad-segments":
        raise ValueError("Only --strategy bad-segments is currently supported.")
    output_dir = options.output_dir.expanduser().resolve()
    repair_dir = ensure_dir(output_dir / "repair")
    plan = _repair_plan_for_options(output_dir, options)
    write_json_atomic(repair_dir / "repair_plan.json", plan)
    if options.plan_only or not plan["windows"]:
        return {"success": True, "plan_only": True, "repair_dir": str(repair_dir), "plan": plan}

    prepared_wav = _details_dir(output_dir) / "prepared.wav"
    if not prepared_wav.exists():
        raise FileNotFoundError(f"Repair requires prepared audio: {prepared_wav}")

    details = _details_dir(output_dir)
    run = _read_json_object(details / "run.json")
    glossary = _read_json_object(details / "glossary.effective.json")
    language = options.language if options.language is not None else run.get("language", "zh")
    prompt = run.get("prompt") if isinstance(run.get("prompt"), str) else None
    repair_id = _next_repair_id(repair_dir)
    write_json_atomic(repair_dir / f"repair_plan_{repair_id:03d}.json", plan)
    windows_dir = ensure_dir(repair_dir / "windows")
    run_audit_dir = ensure_dir(repair_dir / "runs" / f"repair_run_{repair_id:03d}")
    run_audit_windows_dir = ensure_dir(run_audit_dir / "windows")
    current_segments = _segments_from_output(output_dir)
    pre_segment_digest = segment_digest(current_segments)
    replacement_segments: list[dict[str, Any]] = []
    diffs: list[str] = []
    window_decisions: list[dict[str, Any]] = []
    backend = backend or build_backend(default_asr_backend())
    candidate_profiles = normalize_repair_candidate_profiles(options.candidate_profiles)
    write_json_atomic(
        repair_dir / f"pre_repair_snapshot_{repair_id:03d}.json",
        {
            "created_at": now_iso(),
            "repair_id": repair_id,
            "segment_count": len(current_segments),
            "segment_digest": pre_segment_digest,
            "text_preview": segment_plain_text(current_segments)[:2000],
            "qa_summary": plan.get("qa_summary", {}),
        },
    )

    for index, window in enumerate(plan["windows"], start=1):
        start = float(window["start"])
        end = float(window["end"])
        wav_path = windows_dir / f"repair_{index:04d}.wav"
        audit_window_dir = ensure_dir(
            run_audit_windows_dir / str(window.get("id") or f"repair-window-{index:04d}")
        )
        candidates_dir = ensure_dir(audit_window_dir / "candidates")
        write_wav_chunk(prepared_wav, wav_path, start, max(0.01, end - start))
        shutil.copyfile(wav_path, audit_window_dir / "input.wav")
        before = _window_segments(current_segments, start=start, end=end)
        qa_before = _window_qa_before(window, before)
        candidates: list[dict[str, Any]] = []
        for candidate_rank, profile in enumerate(candidate_profiles):
            candidate_id = profile
            candidate_dir = ensure_dir(candidates_dir / candidate_id)
            result = backend.transcribe(
                wav_path,
                _candidate_profile_options(
                    options,
                    profile,
                    language=str(language) if language is not None else None,
                    prompt=prompt,
                ),
            )
            raw_replacements = _offset_segments(result, start, window_end=end)
            corrected_replacements, correction_report = apply_corrections_to_segments(
                raw_replacements,
                glossary,
                audio_duration=_audio_duration_from_output(output_dir),
            )
            qa_after = _window_qa_after(window, corrected_replacements)
            candidate = {
                "id": candidate_id,
                "profile": profile,
                "rank": candidate_rank,
                "kind": "asr_rerun",
                "result": result,
                "raw_segments": raw_replacements,
                "segments": corrected_replacements,
                "corrections": correction_report,
                "qa": qa_after,
            }
            candidates.append(candidate)
            write_json_atomic(
                candidate_dir / "raw.json", {"window": window, "profile": profile, "result": result}
            )
            write_json_atomic(candidate_dir / "segments.json", {"segments": raw_replacements})
            write_json_atomic(
                candidate_dir / "corrected.json",
                {
                    "window": window,
                    "profile": profile,
                    "segments": corrected_replacements,
                    "corrections": correction_report,
                },
            )
            write_json_atomic(candidate_dir / "qa_after_window.json", qa_after)
        decision, selected_candidate = evaluate_repair_candidates(
            before=before,
            qa_before=qa_before,
            candidates=candidates,
            start=start,
            end=end,
        )
        selected_raw_segments = (
            selected_candidate.get("raw_segments", [])
            if selected_candidate.get("kind") != "baseline"
            else []
        )
        selected_replacements = (
            selected_candidate.get("segments", [])
            if selected_candidate.get("kind") != "baseline"
            else []
        )
        selected_corrections = (
            selected_candidate.get("corrections", [])
            if selected_candidate.get("kind") != "baseline"
            else []
        )
        selected_result = (
            selected_candidate.get("result", {})
            if selected_candidate.get("kind") != "baseline"
            else {}
        )
        selected_qa_after = selected_candidate.get("qa", _window_qa_after(window, []))
        diff_text = _repair_diff(window, before, selected_replacements)
        write_json_atomic(
            windows_dir / f"repair_{index:04d}.raw.json",
            {"window": window, "result": selected_result},
        )
        write_json_atomic(
            windows_dir / f"repair_{index:04d}.segments.json", {"segments": selected_raw_segments}
        )
        write_json_atomic(
            windows_dir / f"repair_{index:04d}.corrected.json",
            {
                "window": window,
                "segments": selected_replacements,
                "corrections": selected_corrections,
            },
        )
        window_decision = {
            "window_id": str(window.get("id") or f"repair-window-{index:04d}"),
            "index": index,
            "decision": decision,
            "source_issue_ids": [str(item) for item in window.get("source_issue_ids", [])],
        }
        window_decisions.append(window_decision)
        write_json_atomic(
            audit_window_dir / "raw.json", {"window": window, "result": selected_result}
        )
        write_json_atomic(audit_window_dir / "segments.json", {"segments": selected_raw_segments})
        write_json_atomic(
            audit_window_dir / "corrected.json",
            {
                "window": window,
                "segments": selected_replacements,
                "corrections": selected_corrections,
            },
        )
        write_json_atomic(audit_window_dir / "qa_before_window.json", qa_before)
        write_json_atomic(audit_window_dir / "qa_after_window.json", selected_qa_after)
        write_json_atomic(audit_window_dir / "decision.json", decision)
        write_text_atomic(audit_window_dir / "replacement.diff.md", diff_text)
        write_json_atomic(
            audit_window_dir / "audit.json",
            {
                "created_at": now_iso(),
                "repair_id": repair_id,
                "window": window,
                "qa_before_window": qa_before.get("summary", {}),
                "qa_after_window": selected_qa_after.get("summary", {}),
                "decision": decision,
            },
        )
        if decision["action"] == "apply":
            current_segments = _replace_window_segments(
                current_segments, selected_replacements, start=start, end=end
            )
            replacement_segments.extend(selected_replacements)
        diffs.append(diff_text)

    replacement_payload = {"segments": replacement_segments}
    write_json_atomic(
        repair_dir / f"replacement_segments_{repair_id:03d}.json", replacement_payload
    )
    write_json_atomic(repair_dir / "replacement_segments.json", replacement_payload)
    write_text_atomic(repair_dir / f"diff_{repair_id:03d}.md", "\n".join(diffs))
    applied_window_count = sum(
        1 for item in window_decisions if item["decision"]["action"] == "apply"
    )
    if applied_window_count:
        output_summary = _write_repaired_outputs(
            output_dir,
            segments=current_segments,
            glossary=glossary,
            model=options.fallback_model or options.model,
            language=str(language) if language is not None else None,
            local_only=options.local_only,
        )
    else:
        output_summary = {"qa": build_qa_report(output_dir), "review": {}, "quality_metrics": {}}
    post_segment_digest = segment_digest(current_segments)
    repair_run = {
        "success": True,
        "created_at": now_iso(),
        "repair_id": repair_id,
        "strategy": options.strategy,
        "model": options.model,
        "fallback_model": options.fallback_model,
        "windows": plan["windows"],
        "pre_segment_digest": pre_segment_digest,
        "post_segment_digest": post_segment_digest,
        "replacement_segment_count": len(replacement_segments),
        "applied_window_count": applied_window_count,
        "rejected_window_count": len(window_decisions) - applied_window_count,
        "window_decisions": window_decisions,
        "qa_success_after": output_summary["qa"].get("success"),
        "qa": output_summary["qa"].get("summary", {}),
    }
    repair_decision = {
        "success": True,
        "created_at": now_iso(),
        "repair_id": repair_id,
        "status": "applied" if applied_window_count else "rejected",
        "applied_window_count": applied_window_count,
        "rejected_window_count": len(window_decisions) - applied_window_count,
        "window_decisions": window_decisions,
    }
    write_json_atomic(repair_dir / f"repair_decision_{repair_id:03d}.json", repair_decision)
    write_json_atomic(repair_dir / "repair_decision.json", repair_decision)
    write_json_atomic(repair_dir / f"repair_run_{repair_id:03d}.json", repair_run)
    write_json_atomic(
        repair_dir / f"post_repair_snapshot_{repair_id:03d}.json",
        {
            "created_at": now_iso(),
            "repair_id": repair_id,
            "segment_count": len(current_segments),
            "segment_digest": post_segment_digest,
            "qa_summary": output_summary["qa"].get("summary", {}),
        },
    )
    _update_run_repair_state(output_dir, repair_dir, applied_window_count)
    write_artifact_manifest(output_dir)
    return {"success": True, "repair_dir": str(repair_dir), "plan": plan, "repair_run": repair_run}
