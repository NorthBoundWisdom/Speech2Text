from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corrections import load_glossary, make_prompt, merge_glossaries
from .paths import DEFAULT_TOPIC_FILE
from .rules import normalize_rule_pack_request, selected_rule_packs
from .topic import extract_episode_glossary
from .utils import ensure_dir, read_text, write_json_atomic, write_text_atomic


TOPIC_SUMMARY_SKIP_LABELS = (
    "原链接",
    "链接",
    "音频",
    "视频",
    "封面",
    "时长",
    "发布时间",
    "发布于",
    "Original link",
    "Source",
    "Audio",
    "Video",
    "Cover",
    "Duration",
    "Published at",
    "Podcast link",
    "Shownotes",
    "Show Notes",
)


@dataclass(frozen=True)
class PromptContext:
    topic_path: Path
    topic_text: str | None
    prompt_text: str | None
    prompt_sources: list[dict[str, str]]
    base_glossary: dict[str, Any]
    episode_glossary: dict[str, Any]
    glossary: dict[str, Any]
    effective_prompt: str | None
    topic_prompt_summary: str | None = None
    rule_pack_request: tuple[str, ...] = ()
    topic_rule_packs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextFiles:
    copied_glossary: str | None
    episode_glossary_file: Path | None
    effective_glossary_file: Path
    topic_prompt_summary_file: Path | None
    rule_packs_file: Path


def _copy_if_exists(src: Path | None, dst: Path) -> str | None:
    if src is None:
        return None
    src = src.expanduser()
    if not src.exists():
        return None
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return str(dst)


def _prompt_parts(paths: list[tuple[str, Path | None]]) -> tuple[str | None, list[dict[str, str]]]:
    parts: list[str] = []
    sources: list[dict[str, str]] = []
    for label, path in paths:
        text = read_text(path)
        if text and path is not None:
            parts.append(text)
            sources.append({"label": label, "path": str(path)})
    prompt = "\n\n".join(parts).strip()
    return prompt or None, sources


def topic_prompt_summary(topic_text: str | None, *, max_chars: int = 280) -> str | None:
    if not topic_text:
        return None
    lines: list[str] = []
    for raw_line in topic_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("http://", "https://")):
            continue
        line = line.lstrip("#|>-*0123456789.、)） \t")
        if not line:
            continue
        label = line.split("：", 1)[0].split(":", 1)[0].strip()
        if label in TOPIC_SUMMARY_SKIP_LABELS:
            continue
        if "http://" in line or "https://" in line:
            continue
        lines.append(line)
        if len("；".join(lines)) >= max_chars:
            break
    summary = "；".join(lines)
    if not summary:
        return None
    return summary[:max_chars].rstrip("，,、。；;：: \t\r\n")


def build_prompt_context(
    input_path: Path,
    *,
    prompt_file: Path | None,
    glossary_file: Path | None,
    rule_packs: tuple[str, ...] | list[str] | None = None,
) -> PromptContext:
    topic_path = input_path.parent / DEFAULT_TOPIC_FILE
    topic_text = read_text(topic_path)
    rule_pack_request = normalize_rule_pack_request(rule_packs)
    topic_rule_packs = selected_rule_packs(topic_text or "", rule_pack_request)
    prompt_text, prompt_sources = _prompt_parts(
        [
            ("public_prompt", prompt_file),
        ]
    )
    base_glossary = load_glossary(glossary_file)
    episode_glossary = extract_episode_glossary(topic_text, rule_packs=rule_pack_request)
    glossary = merge_glossaries(base_glossary, episode_glossary)
    summary = topic_prompt_summary(topic_text)
    effective_prompt = make_prompt(prompt_text, glossary)
    return PromptContext(
        topic_path=topic_path,
        topic_text=topic_text,
        topic_prompt_summary=summary,
        prompt_text=prompt_text,
        prompt_sources=prompt_sources,
        base_glossary=base_glossary,
        episode_glossary=episode_glossary,
        glossary=glossary,
        effective_prompt=effective_prompt,
        rule_pack_request=rule_pack_request,
        topic_rule_packs=topic_rule_packs,
    )


def write_context_files(
    job_dir: Path,
    context: PromptContext,
    *,
    glossary_file: Path | None,
) -> ContextFiles:
    details_dir = ensure_dir(job_dir)
    copied_glossary = _copy_if_exists(glossary_file, details_dir / "glossary.json")
    episode_glossary_file = None
    if context.episode_glossary:
        episode_glossary_file = details_dir / "episode_glossary.json"
        write_json_atomic(episode_glossary_file, context.episode_glossary)
    topic_prompt_summary_file = None
    if context.topic_prompt_summary:
        topic_prompt_summary_file = details_dir / "topic.prompt_summary.txt"
        write_text_atomic(topic_prompt_summary_file, context.topic_prompt_summary)
    rule_packs_file = details_dir / "rule_packs.json"
    write_json_atomic(
        rule_packs_file,
        {
            "request": list(context.rule_pack_request),
            "topic_selected": list(context.topic_rule_packs),
        },
    )
    effective_glossary_file = details_dir / "glossary.effective.json"
    write_json_atomic(effective_glossary_file, context.glossary)
    return ContextFiles(
        copied_glossary=copied_glossary,
        episode_glossary_file=episode_glossary_file,
        effective_glossary_file=effective_glossary_file,
        topic_prompt_summary_file=topic_prompt_summary_file,
        rule_packs_file=rule_packs_file,
    )
