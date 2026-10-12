from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .client import CloudClientOptions, call_openai_compatible_chat, read_prompt_template
from .output_state import CloudOutputOptions, _cloud_dir, _input_dir, _record_cloud_outputs
from .summary_outputs import _input_bundle, _transcript_lines
from ..punctuation import normalize_chinese_punctuation
from ..runinfo import now_iso
from ..utils import (
    compact_ws,
    read_json,
    read_text,
    seconds_to_hms,
    write_json_atomic,
    write_text_atomic,
)


ASCII_TERM_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9._/-]{2,})(?![A-Za-z0-9])")


def _maybe_call_cloud(
    options: CloudOutputOptions,
    *,
    default_prompt: str,
    fallback_prompt: Path,
    user_content: str,
    audit_name: str,
    prefer_fallback_prompt: bool = True,
    allow_custom_prompt: bool = True,
    call_chat: Any | None = None,
) -> str | None:
    if not options.call_api:
        return None
    if allow_custom_prompt and options.prompt_file:
        prompt = read_prompt_template(options.prompt_file)
    elif prefer_fallback_prompt and fallback_prompt.exists():
        prompt = read_prompt_template(fallback_prompt)
    else:
        prompt = default_prompt
    return (call_chat or call_openai_compatible_chat)(
        system_prompt=prompt,
        user_content=user_content,
        options=CloudClientOptions(),
        audit_path=_cloud_dir(options.output_dir.expanduser().resolve()) / audit_name,
    )


def write_cloud_glossary_review(
    options: CloudOutputOptions,
    *,
    call_chat: Any | None = None,
) -> dict[str, Any]:
    output_dir = options.output_dir.expanduser().resolve()
    cloud = _cloud_dir(output_dir)
    cloud_text = _maybe_call_cloud(
        options,
        default_prompt="请输出 glossary_suggestions.json 兼容的 JSON，只包含 suggestions 和 needs_human_confirmation。",
        fallback_prompt=Path("doc/cloud_prompts/glossary_review.zh.md"),
        user_content=_input_bundle(output_dir),
        audit_name="glossary_review.api_run.json",
        call_chat=call_chat,
    )
    if cloud_text is not None:
        try:
            payload = read_json_from_text(cloud_text)
        except ValueError:
            payload = {
                "suggestions": [],
                "needs_human_confirmation": [],
                "raw_response": cloud_text,
            }
        editor_outputs = _write_glossary_editor_items(output_dir, payload, source="cloud_model")
        review_queue_outputs = _write_glossary_review_queue(
            output_dir, payload, source="cloud_model"
        )
        write_json_atomic(cloud / "glossary_suggestions.json", payload)
        outputs = ["glossary_suggestions.json", *review_queue_outputs, *editor_outputs]
        _record_cloud_outputs(output_dir, outputs, source="cloud_model")
        return {"success": True, "source": "cloud_model", "outputs": outputs}
    lines = _transcript_lines(output_dir)
    text = "\n".join(str(line["text"]) for line in lines)
    counts: dict[str, int] = {}
    for token in ASCII_TERM_RE.findall(text):
        counts[token] = counts.get(token, 0) + 1
    suggestions = [
        {
            "canonical": token,
            "variants_seen": [token],
            "confidence": "medium",
            "reason": "Repeated ASCII token in transcript; confirm spelling before adding a rule.",
            "suggested_rule_type": "review_only",
        }
        for token, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ]
    payload = {"suggestions": [], "needs_human_confirmation": suggestions}
    write_json_atomic(cloud / "glossary_suggestions.json", payload)
    review_queue_outputs = _write_glossary_review_queue(
        output_dir, payload, source="local_scaffold"
    )
    editor_outputs = _write_glossary_editor_items(output_dir, payload, source="local_scaffold")
    outputs = ["glossary_suggestions.json", *review_queue_outputs, *editor_outputs]
    _record_cloud_outputs(output_dir, outputs, source="local_scaffold")
    return {"success": True, "outputs": outputs, "suggestion_count": len(suggestions)}


def _write_glossary_review_queue(
    output_dir: Path, payload: dict[str, Any], *, source: str
) -> list[str]:
    cloud = _cloud_dir(output_dir)
    queue = {
        "source": source,
        "created_at": now_iso(),
        "episode_suggestions": payload.get("suggestions", [])
        if isinstance(payload.get("suggestions"), list)
        else [],
        "review_only_terms": (
            payload.get("needs_human_confirmation", [])
            if isinstance(payload.get("needs_human_confirmation"), list)
            else []
        ),
        "global_rule_candidates": [],
        "policy": "Confirm episode or podcast scope before promoting any item to reusable rules.",
    }
    write_json_atomic(cloud / "glossary_review_queue.json", queue)
    lines = [
        "# Glossary Review Queue",
        "",
        "Confirm episode or podcast scope before promoting any item to reusable rules.",
        "",
        "## Episode Suggestions",
        "",
    ]
    for item in queue["episode_suggestions"]:
        lines.append(
            f"- {compact_ws(str(item)) if isinstance(item, str) else compact_ws(str(item.get('canonical') or item))}"
        )
    if not queue["episode_suggestions"]:
        lines.append("- none")
    lines.extend(["", "## Review Only", ""])
    for item in queue["review_only_terms"]:
        lines.append(
            f"- {compact_ws(str(item)) if isinstance(item, str) else compact_ws(str(item.get('canonical') or item))}"
        )
    if not queue["review_only_terms"]:
        lines.append("- none")
    write_text_atomic(cloud / "glossary_review_queue.md", "\n".join(lines).strip() + "\n")
    return ["glossary_review_queue.json", "glossary_review_queue.md"]


def _write_glossary_editor_items(
    output_dir: Path, payload: dict[str, Any], *, source: str
) -> list[str]:
    cloud = _cloud_dir(output_dir)
    items: list[dict[str, Any]] = []
    for group, default_action in (
        ("suggestions", "confirm_episode_glossary"),
        ("needs_human_confirmation", "review_only"),
    ):
        values = payload.get(group, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str):
                term = compact_ws(value)
                category = "technical_terms"
            elif isinstance(value, dict):
                term = compact_ws(
                    str(value.get("canonical") or value.get("term") or value.get("text") or "")
                )
                category = str(
                    value.get("category") or value.get("suggested_category") or "technical_terms"
                )
            else:
                continue
            if not term:
                continue
            items.append(
                {
                    "term": term,
                    "category": category,
                    "scope": "episode",
                    "action": str(value.get("suggested_rule_type") or default_action)
                    if isinstance(value, dict)
                    else default_action,
                    "source": source,
                    "last_used": now_iso(),
                    "hit_count": _term_hit_count(output_dir, term),
                    "enabled": True,
                }
            )
    write_json_atomic(cloud / "glossary_editor_items.json", {"items": items})
    lines = [
        "# Glossary Editor Items",
        "",
        "| Term | Category | Scope | Action | Source | Last used | Hit count |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| {item['term']} | {item['category']} | {item['scope']} | {item['action']} | "
            f"{item['source']} | {item['last_used']} | {item['hit_count']} |"
        )
    if not items:
        lines.append("|  |  |  |  |  |  |  |")
    write_text_atomic(cloud / "glossary_editor_items.md", "\n".join(lines).strip() + "\n")
    return ["glossary_editor_items.json", "glossary_editor_items.md"]


def _term_hit_count(output_dir: Path, term: str) -> int:
    text = read_text(_input_dir(output_dir) / "transcript.for_cloud.md") or ""
    return text.count(term)


def write_cloud_polish_suggestions(
    options: CloudOutputOptions,
    *,
    call_chat: Any | None = None,
) -> dict[str, Any]:
    output_dir = options.output_dir.expanduser().resolve()
    cloud = _cloud_dir(output_dir)
    cloud_text = _maybe_call_cloud(
        options,
        default_prompt="请输出 transcript.polish_suggestions.json 兼容的 JSON patches，不要直接改写全文。",
        fallback_prompt=Path("doc/cloud_prompts/polish_transcript.zh.md"),
        user_content=_input_bundle(output_dir),
        audit_name="polish.api_run.json",
        call_chat=call_chat,
    )
    if cloud_text is not None:
        try:
            payload = read_json_from_text(cloud_text)
        except ValueError:
            payload = {"patches": [], "raw_response": cloud_text}
        payload = _normalize_polish_patch_payload(payload, raw_response=cloud_text)
        write_json_atomic(cloud / "transcript.polish_suggestions.json", payload)
        outputs = ["transcript.polish_suggestions.json"]
        _record_cloud_outputs(output_dir, outputs, source="cloud_model")
        return {
            "success": True,
            "source": "cloud_model",
            "outputs": outputs,
            "patch_count": len(payload.get("patches", [])),
        }
    lines = _transcript_lines(output_dir)
    patches: list[dict[str, Any]] = []
    for line in lines:
        original = str(line["text"])
        suggested = normalize_chinese_punctuation(original)
        if suggested == original:
            continue
        patches.append(
            {
                "patch_id": f"patch_{len(patches) + 1:04d}",
                "segment_id": str(line["segment_id"]),
                "start": line["time"],
                "end": seconds_to_hms(float(line["end"])),
                "old_text": original,
                "new_text": suggested,
                "reason": "Chinese punctuation normalization",
                "risk": "low",
                "requires_audio_check": False,
            }
        )
    payload = {"patches": patches}
    write_json_atomic(cloud / "transcript.polish_suggestions.json", payload)
    outputs = ["transcript.polish_suggestions.json"]
    _record_cloud_outputs(output_dir, outputs, source="local_scaffold")
    return {"success": True, "outputs": outputs, "patch_count": len(patches)}


def _normalize_polish_patch_payload(
    payload: dict[str, Any], *, raw_response: str
) -> dict[str, Any]:
    raw_patches = payload.get("patches", [])
    if not isinstance(raw_patches, list):
        return {"patches": [], "raw_response": raw_response}
    patches: list[dict[str, Any]] = []
    for index, item in enumerate(raw_patches, start=1):
        if not isinstance(item, dict):
            continue
        patch_id = str(item.get("patch_id") or f"patch_{index:04d}").strip()
        segment_id = str(item.get("segment_id") or "").strip()
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        old_text = str(item.get("old_text") or item.get("original") or "").strip()
        new_text = str(item.get("new_text") or item.get("suggested") or "").strip()
        if not all((patch_id, start, end, old_text, new_text)):
            continue
        patches.append(
            {
                "patch_id": patch_id,
                "segment_id": segment_id,
                "start": start,
                "end": end,
                "old_text": old_text,
                "new_text": new_text,
                "reason": str(
                    item.get("reason") or "Cloud polish suggestion; confirm before applying."
                ).strip(),
                "risk": str(item.get("risk") or "review").strip(),
                "requires_audio_check": bool(item.get("requires_audio_check", True)),
            }
        )
    normalized: dict[str, Any] = {"patches": patches}
    if not patches and raw_response:
        normalized["raw_response"] = raw_response
    return normalized


def apply_cloud_patches(
    output_dir: str | Path, patches_path: str | Path, *, mode: str = "reviewed"
) -> dict[str, Any]:
    if mode != "reviewed":
        raise ValueError("Only --mode reviewed is supported.")
    base = Path(output_dir).expanduser().resolve()
    cloud = _cloud_dir(base)
    patches_payload = read_json(patches_path)
    if not isinstance(patches_payload, dict) or not isinstance(
        patches_payload.get("patches"), list
    ):
        raise ValueError("Patch file must contain a patches list.")
    transcript = read_text(_input_dir(base) / "transcript.for_cloud.md") or ""
    lines = _transcript_lines(base)
    applied = 0
    updated = transcript
    decisions: list[dict[str, Any]] = []
    for patch in patches_payload["patches"]:
        if not isinstance(patch, dict):
            continue
        normalized = _normalize_polish_patch_payload({"patches": [patch]}, raw_response="").get(
            "patches", []
        )
        if not normalized:
            decisions.append({"patch": patch, "applied": False, "reason": "invalid_patch_schema"})
            continue
        item = normalized[0]
        match = _matching_patch_line(lines, item)
        if match is None:
            decisions.append(
                {
                    "patch_id": item["patch_id"],
                    "applied": False,
                    "reason": "segment_or_time_mismatch",
                }
            )
            continue
        original = str(item["old_text"])
        suggested = str(item["new_text"])
        if original not in updated:
            decisions.append(
                {"patch_id": item["patch_id"], "applied": False, "reason": "old_text_not_found"}
            )
            continue
        updated = updated.replace(original, suggested, 1)
        applied += 1
        decisions.append(
            {
                "patch_id": item["patch_id"],
                "segment_id": item.get("segment_id"),
                "applied": True,
                "reason": "matched_old_text_and_timestamp",
                "old_text": original,
                "new_text": suggested,
            }
        )
    write_text_atomic(cloud / "transcript.readable.md", updated)
    result = {
        "success": True,
        "mode": mode,
        "applied_patch_count": applied,
        "review_state": "human_confirmed",
        "output": "transcript.readable.md",
        "decisions": decisions,
    }
    write_json_atomic(cloud / "patch_apply_run.json", result)
    write_json_atomic(cloud / "patch_apply.audit.json", result)
    _record_cloud_outputs(
        base,
        ["transcript.readable.md", "patch_apply_run.json", "patch_apply.audit.json"],
        source="reviewed_patch",
    )
    return result


def _matching_patch_line(
    lines: list[dict[str, Any]], patch: dict[str, Any]
) -> dict[str, Any] | None:
    old_text = compact_ws(str(patch.get("old_text") or ""))
    start = str(patch.get("start") or "")
    end = str(patch.get("end") or "")
    segment_id = str(patch.get("segment_id") or "")
    for line in lines:
        if segment_id and line.get("segment_id") != segment_id:
            continue
        line_start = seconds_to_hms(float(line.get("start", 0.0)))
        line_end = seconds_to_hms(float(line.get("end", 0.0)))
        if start and start != line_start:
            continue
        if end and end != line_end:
            continue
        if old_text and old_text not in compact_ws(str(line.get("text", ""))):
            continue
        return line
    return None


def read_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in cloud response.")
    payload = read_json_string(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Cloud JSON response must be an object.")
    return payload


def read_json_string(text: str) -> Any:
    import json

    return json.loads(text)
