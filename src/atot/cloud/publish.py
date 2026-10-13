from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..languages import output_language_instruction
from .client import CloudClientOptions, call_openai_compatible_chat, read_prompt_template
from .metadata import episode_title_for_output
from .output_state import (
    CloudOutputOptions,
    _cloud_dir,
    _input_dir,
    _read_json_object,
    _record_cloud_outputs,
)
from ..corrections import glossary_terms
from ..utils import compact_ws, read_text, relative_posix_path, write_json_atomic, write_text_atomic


ChatCaller = Callable[..., str]


def _collect_uncertainties(output_dir: Path) -> list[dict[str, Any]]:
    input_dir = _input_dir(output_dir)
    uncertainties: list[dict[str, Any]] = []
    qa = _read_json_object(input_dir / "qa.for_cloud.json")
    if qa and qa.get("success") is not True:
        uncertainties.append(
            {
                "type": "qa_failed",
                "severity": "high",
                "time": None,
                "evidence": "qa.for_cloud.json did not pass",
                "suggested_action": "Review the flagged transcript ranges before publishing cloud summaries.",
            }
        )
    for issue in qa.get("issues", []) if isinstance(qa.get("issues"), list) else []:
        if not isinstance(issue, dict):
            continue
        uncertainties.append(
            {
                "type": str(issue.get("type") or "qa_issue"),
                "severity": str(issue.get("severity") or "medium"),
                "time": issue.get("time") or issue.get("start"),
                "evidence": str(issue.get("message") or issue.get("evidence") or issue),
                "suggested_action": "Inspect this range against the local transcript and audio.",
            }
        )
    review = _read_json_object(input_dir / "review.for_cloud.json")
    review_items = review.get("needs_human_confirmation", []) or review.get("uncertainties", [])
    if isinstance(review_items, list):
        for item in review_items:
            if not isinstance(item, dict):
                continue
            uncertainties.append(
                {
                    "type": str(item.get("type") or "review_uncertainty"),
                    "severity": str(item.get("severity") or "medium"),
                    "time": item.get("time") or item.get("start"),
                    "evidence": str(item.get("reason") or item.get("evidence") or item),
                    "suggested_action": "Confirm before converting the finding into a glossary or correction rule.",
                }
            )
    cloud = _cloud_dir(output_dir)
    for path in sorted((cloud / "chunk_summaries").glob("chunk_*.summary.json")):
        payload = _read_json_object(path)
        if payload.get("success") is False:
            uncertainties.append(
                {
                    "type": "chunk_summary_failed",
                    "severity": "high",
                    "time": f"{payload.get('start')} -> {payload.get('end')}",
                    "evidence": str(
                        payload.get("retry", {}).get("error") or "Chunk summary did not complete."
                    ),
                    "suggested_action": "Re-run cloud summarize to resume failed chunks.",
                }
            )
        chunk_items = payload.get("uncertainties", [])
        if not isinstance(chunk_items, list):
            continue
        chunk_range = (
            f"{payload.get('start')} -> {payload.get('end')}"
            if payload.get("start") and payload.get("end")
            else None
        )
        for item in chunk_items:
            if isinstance(item, str):
                evidence = compact_ws(item)
                term = ""
                severity = "medium"
                kind = "chunk_uncertainty"
            elif isinstance(item, dict):
                term = compact_ws(str(item.get("term") or item.get("canonical") or ""))
                evidence = compact_ws(
                    str(
                        item.get("reason")
                        or item.get("evidence")
                        or item.get("question")
                        or item.get("text")
                        or item
                    )
                )
                severity = str(item.get("severity") or "medium")
                kind = str(item.get("type") or "chunk_uncertainty")
            else:
                continue
            if term:
                evidence = f"{term}: {evidence}"
            uncertainties.append(
                {
                    "type": kind,
                    "severity": severity,
                    "time": chunk_range,
                    "evidence": evidence,
                    "suggested_action": "Confirm this chunk-level cloud finding before adding a correction or glossary rule.",
                }
            )
    return uncertainties


def _write_uncertainty_report(output_dir: Path) -> list[str]:
    uncertainties = _collect_uncertainties(output_dir)
    lines = ["# Uncertainty Report", ""]
    if uncertainties:
        for item in uncertainties:
            time = f" [{item['time']}]" if item.get("time") else ""
            lines.append(f"- {item['severity']} {item['type']}{time}: {item['evidence']}")
            lines.append(f"  Suggested action: {item['suggested_action']}")
    else:
        lines.append("No automatic uncertainties detected.")
    content = "\n".join(lines).strip() + "\n"
    outputs = ["uncertainty_report.md", "fact_or_term_uncertainties.md"]
    for output in outputs:
        write_text_atomic(_cloud_dir(output_dir) / output, content)
    return outputs


def _term_text(value: Any) -> str:
    if isinstance(value, str):
        return compact_ws(value)
    if not isinstance(value, dict):
        return ""
    for key in ("term", "canonical", "text", "name"):
        candidate = value.get(key)
        if isinstance(candidate, str) and compact_ws(candidate):
            return compact_ws(candidate)
    return ""


def _write_terms_outputs(output_dir: Path) -> list[str]:
    cloud = _cloud_dir(output_dir)
    terms: dict[str, dict[str, Any]] = {}

    def add_term(value: Any, *, source: str) -> None:
        text = _term_text(value)
        if not text:
            return
        item = terms.setdefault(text, {"term": text, "sources": [], "count": 0})
        item["count"] = int(item["count"]) + 1
        if source not in item["sources"]:
            item["sources"].append(source)

    glossary = _read_json_object(_input_dir(output_dir) / "glossary.for_cloud.json")
    for term in glossary_terms(glossary):
        add_term(term, source="input_glossary")

    for path in sorted((cloud / "chunk_summaries").glob("chunk_*.summary.json")):
        payload = _read_json_object(path)
        chunk_terms = payload.get("terms", [])
        if not isinstance(chunk_terms, list):
            continue
        for term in chunk_terms:
            add_term(term, source=relative_posix_path(path, cloud))

    payload = {"terms": sorted(terms.values(), key=lambda item: str(item["term"]).lower())}
    write_json_atomic(cloud / "terms.json", payload)

    lines = ["# Terms", ""]
    if payload["terms"]:
        for item in payload["terms"]:
            sources = ", ".join(map(str, item["sources"]))
            lines.append(f"- {item['term']} ({sources})")
    else:
        lines.append("No terms detected.")
    write_text_atomic(cloud / "terms.md", "\n".join(lines).strip() + "\n")
    return ["terms.json", "terms.md"]


def _episode_title(output_dir: Path) -> str:
    manifest = _read_json_object(_input_dir(output_dir) / "manifest.json")
    return episode_title_for_output(output_dir, manifest=manifest)


def _write_publish_outputs(
    output_dir: Path, *, summary: str, chapters: list[dict[str, Any]]
) -> list[str]:
    cloud = _cloud_dir(output_dir)
    episode_title = _episode_title(output_dir)
    first_chapter = str(chapters[0].get("title") or "").strip() if chapters else ""
    compact_summary = compact_ws(summary)
    title_candidates = [
        {"title": episode_title, "source": "episode_title"},
        {"title": first_chapter[:36], "source": "first_chapter"} if first_chapter else {},
        {"title": compact_summary[:36], "source": "summary"} if compact_summary else {},
    ]
    deduped_titles: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for item in title_candidates:
        title = compact_ws(str(item.get("title", ""))) if item else ""
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        deduped_titles.append(
            {"title": title, "source": str(item.get("source") or "local_scaffold")}
        )
    write_json_atomic(cloud / "title_candidates.json", {"candidates": deduped_titles})

    title_lines = ["# Title Candidates", ""]
    if deduped_titles:
        for item in deduped_titles:
            title_lines.append(f"- {item['title']} ({item['source']})")
    else:
        title_lines.append("- No title candidates available.")
    write_text_atomic(cloud / "title_candidates.md", "\n".join(title_lines).strip() + "\n")

    social_lines = ["# Social Copy", ""]
    if compact_summary:
        social_lines.extend([f"{episode_title}：{compact_summary[:120]}", ""])
    else:
        social_lines.extend([episode_title, ""])
    if chapters:
        social_lines.append("## Chapters")
        for chapter in chapters[:5]:
            social_lines.append(f"- {chapter['start']} {chapter['title']}")
    write_text_atomic(cloud / "social_copy.md", "\n".join(social_lines).strip() + "\n")
    return ["title_candidates.json", "title_candidates.md", "social_copy.md"]


def _clean_short_title(text: str, *, limit: int = 36, language: str = "zh") -> str:
    raw = _strip_outer_markdown_fence(text).strip()
    if not raw:
        return ""
    title = next((compact_ws(line) for line in raw.splitlines() if line.strip()), "")
    title = title.strip(" #\"'“”‘’`")
    if language == "zh":
        title = title.replace(":", "：")
    prefixes = ("短标题：", "标题：", "短标题:", "标题:")
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
    return title[:limit].strip()


def _looks_like_summary_title(raw_response: str, title: str) -> bool:
    raw = _strip_outer_markdown_fence(raw_response).strip()
    if not raw:
        return False
    if any(marker in title for marker in ("结构化总结", "播客总结", "主要内容")):
        return True
    lines = [line for line in raw.splitlines() if line.strip()]
    return len(lines) > 1 and any(line.lstrip().startswith("#") for line in lines)


def _write_short_title_outputs(
    output_dir: Path, *, title: str, source: str, raw_response: str = ""
) -> list[str]:
    cloud = _cloud_dir(output_dir)
    episode_title = _episode_title(output_dir)
    payload = {
        "candidates": [
            {
                "title": title,
                "source": source,
                "kind": "short_title",
            }
        ],
        "episode_title": episode_title,
    }
    if raw_response:
        payload["raw_response"] = raw_response
    write_json_atomic(cloud / "title_candidates.json", payload)
    write_text_atomic(
        cloud / "title_candidates.md", f"# Title Candidates\n\n- {title} ({source})\n"
    )
    write_text_atomic(cloud / "short_title.txt", title + "\n")
    return ["title_candidates.json", "title_candidates.md", "short_title.txt"]


def write_cloud_short_title(
    options: CloudOutputOptions,
    *,
    force: bool = False,
    call_chat: ChatCaller | None = None,
) -> dict[str, Any]:
    output_dir = options.output_dir.expanduser().resolve()
    cloud = _cloud_dir(output_dir)
    existing = _read_json_object(cloud / "title_candidates.json")
    candidates = (
        existing.get("candidates", []) if isinstance(existing.get("candidates"), list) else []
    )
    if not force and any(
        isinstance(item, dict) and item.get("kind") == "short_title" for item in candidates
    ):
        return {
            "success": True,
            "source": "existing",
            "skipped": True,
            "outputs": ["title_candidates.json", "title_candidates.md", "short_title.txt"],
        }
    summary = read_text(cloud / "summary.md")
    if not summary:
        raise FileNotFoundError(
            f"Missing cloud summary for title generation: {cloud / 'summary.md'}"
        )
    cloud_text = None
    if options.call_api:
        prompt = (
            read_prompt_template(options.prompt_file)
            if options.prompt_file
            else "Write one concise podcast list title based only on the supplied summary. Use Guest: complete viewpoint, or Topic: complete viewpoint when no main guest is known. Output only the title, no explanation."
        )
        cloud_text = (call_chat or call_openai_compatible_chat)(
            system_prompt=prompt + "\n\n" + output_language_instruction(options.output_language),
            user_content=summary,
            options=CloudClientOptions(),
            audit_path=cloud / "title.api_run.json",
        )
    source = "cloud_model" if cloud_text is not None else "local_scaffold"
    title = _clean_short_title(
        cloud_text or "",
        language=options.output_language,
        limit=36 if options.output_language == "zh" else 100,
    )
    if cloud_text is not None and _looks_like_summary_title(cloud_text, title):
        raise ValueError("Cloud title response looks like a summary, not a short title.")
    if not title:
        title = _clean_short_title(_episode_title(output_dir))
        source = "local_scaffold"
    outputs = _write_short_title_outputs(
        output_dir, title=title, source=source, raw_response=cloud_text or ""
    )
    _record_cloud_outputs(output_dir, outputs, source=source)
    return {"success": True, "source": source, "title": title, "outputs": outputs}


def _write_chapter_outputs(cloud: Path, chapters: list[dict[str, Any]], summary: str) -> None:
    write_json_atomic(cloud / "chapters.json", {"chapters": chapters})
    chapter_lines = ["# Chapters", ""]
    for chapter in chapters:
        chapter_lines.append(f"- {chapter['start']} - {chapter['end']} {chapter['title']}")
    if not chapters:
        chapter_lines.append("- No timestamped transcript lines available.")
    write_text_atomic(cloud / "chapters.md", "\n".join(chapter_lines).strip() + "\n")
    shownotes = ["# Shownotes", "", summary, "", "## Chapters", ""]
    if chapters:
        for chapter in chapters:
            shownotes.append(f"- [{chapter['start']} - {chapter['end']}] {chapter['title']}")
    else:
        shownotes.append("- No timestamped transcript lines available.")
    write_text_atomic(cloud / "shownotes.md", "\n".join(shownotes).strip() + "\n")


def _strip_outer_markdown_fence(text: str, *, allow_open: bool = False) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    lines = stripped.splitlines()
    if not lines:
        return ""
    opening = lines[0].strip().lower()
    if opening not in {"```", "```md", "```markdown"}:
        return stripped
    if len(lines) == 1:
        return "" if allow_open else stripped
    if lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    if allow_open:
        return "\n".join(lines[1:]).strip()
    return stripped
