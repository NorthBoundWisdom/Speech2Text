from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable

from ..utils import compact_ws


IssueFactory = Callable[..., dict[str, Any]]

ENGLISH_PUNCT_IN_CJK_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff]\s*[,?!]\s*[\u3400-\u4dbf\u4e00-\u9fff]"
)
ENGLISH_CJK_SPACING_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff][A-Za-z0-9]|[A-Za-z0-9][\u3400-\u4dbf\u4e00-\u9fff]"
)
READABLE_TIMESTAMP_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\s*")


def readable_paragraphs(markdown: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append(compact_ws(" ".join(current)))
                current = []
            continue
        if line.startswith("#"):
            continue
        current.append(READABLE_TIMESTAMP_RE.sub("", line))
    if current:
        paragraphs.append(compact_ws(" ".join(current)))
    return [paragraph for paragraph in paragraphs if paragraph]


def max_run_without_sentence_punctuation(text: str) -> int:
    longest = 0
    current = 0
    for char in text:
        if char in "。！？!?；;":
            longest = max(longest, current)
            current = 0
            continue
        if char.isspace():
            continue
        current += 1
    return max(longest, current)


def unmatched_bracket_count(text: str) -> int:
    pairs = {"(": ")", "（": "）", "[": "]", "【": "】", "《": "》"}
    closers = {value: key for key, value in pairs.items()}
    stack: list[str] = []
    unmatched = 0
    for char in text:
        if char in pairs:
            stack.append(char)
        elif char in closers:
            if stack and stack[-1] == closers[char]:
                stack.pop()
            else:
                unmatched += 1
    return unmatched + len(stack)


def review_only_correction_count(corrections_payload: Any) -> int:
    if not isinstance(corrections_payload, dict):
        return 0
    corrections = corrections_payload.get("corrections")
    if not isinstance(corrections, list):
        return 0
    total = 0
    for item in corrections:
        if isinstance(item, dict) and item.get("kind") == "review_only":
            try:
                total += int(item.get("count") or 0)
            except (TypeError, ValueError):
                pass
    return total


def readable_metrics_and_issues(
    base: Path,
    *,
    corrections_payload: Any,
    settings: dict[str, Any],
    issue_factory: IssueFactory,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = base / "transcript.readable.md"
    if not path.exists():
        return {"available": False}, []
    markdown = path.read_text(encoding="utf-8")
    paragraphs = readable_paragraphs(markdown)
    paragraph_lengths = [len(paragraph.replace(" ", "")) for paragraph in paragraphs]
    readable_text = "\n".join(paragraphs)
    visible_chars = len(readable_text.replace(" ", "").replace("\n", ""))
    punctuation_count = len(re.findall(r"[，。！？；：、,.!?;:]", readable_text))
    sentence_punctuation_count = len(re.findall(r"[。！？!?；;]", readable_text))
    punctuation_per_1000 = (
        round(punctuation_count * 1000 / visible_chars, 2) if visible_chars else 0.0
    )
    max_run_on_chars = max_run_without_sentence_punctuation(readable_text)
    duplicate_count = len(paragraphs) - len(set(paragraphs))
    ascii_punctuation_in_cjk_count = len(ENGLISH_PUNCT_IN_CJK_RE.findall(readable_text))
    english_cjk_spacing_issue_count = len(ENGLISH_CJK_SPACING_RE.findall(readable_text))
    unmatched_count = unmatched_bracket_count(readable_text)
    review_only_count = review_only_correction_count(corrections_payload)
    metrics = {
        "available": True,
        "paragraph_count": len(paragraphs),
        "visible_char_count": visible_chars,
        "max_paragraph_chars": max(paragraph_lengths) if paragraph_lengths else 0,
        "average_paragraph_chars": round(sum(paragraph_lengths) / len(paragraph_lengths), 2)
        if paragraph_lengths
        else 0.0,
        "punctuation_count": punctuation_count,
        "sentence_punctuation_count": sentence_punctuation_count,
        "punctuation_per_1000_chars": punctuation_per_1000,
        "max_run_on_chars": max_run_on_chars,
        "repeated_paragraph_count": duplicate_count,
        "ascii_punctuation_in_cjk_count": ascii_punctuation_in_cjk_count,
        "english_cjk_spacing_issue_count": english_cjk_spacing_issue_count,
        "unmatched_bracket_count": unmatched_count,
        "review_only_correction_count": review_only_count,
    }
    issues: list[dict[str, Any]] = []
    warning_chars = int(settings.get("max_readable_paragraph_chars_warning", 360))
    blocker_chars = int(settings.get("max_readable_paragraph_chars_blocker", 600))
    for index, length in enumerate(paragraph_lengths):
        if length > blocker_chars:
            severity = "blocker"
        elif length > warning_chars:
            severity = "warning"
        else:
            continue
        issues.append(
            issue_factory(
                severity,
                "readable_long_paragraph",
                "Readable transcript paragraph is too long",
                source="transcript.readable.md",
                paragraph_index=index,
                paragraph_chars=length,
            )
        )
    density_min_chars = int(settings.get("min_readable_chars_for_density", 200))
    min_density = float(settings.get("min_readable_punctuation_per_1000_chars", 8.0))
    if visible_chars >= density_min_chars and punctuation_per_1000 < min_density:
        issues.append(
            issue_factory(
                "warning",
                "readable_low_punctuation_density",
                "Readable transcript punctuation density is low",
                source="transcript.readable.md",
                punctuation_per_1000_chars=punctuation_per_1000,
                min_punctuation_per_1000_chars=min_density,
            )
        )
    max_run = int(settings.get("max_readable_run_on_chars", 240))
    if max_run_on_chars > max_run:
        issues.append(
            issue_factory(
                "warning",
                "readable_run_on_text",
                "Readable transcript has a long run without sentence punctuation",
                source="transcript.readable.md",
                run_on_chars=max_run_on_chars,
            )
        )
    if duplicate_count:
        issues.append(
            issue_factory(
                "warning",
                "readable_repeated_paragraph",
                "Readable transcript contains repeated paragraphs",
                source="transcript.readable.md",
                count=duplicate_count,
            )
        )
    if english_cjk_spacing_issue_count:
        issues.append(
            issue_factory(
                "warning",
                "readable_english_cjk_spacing",
                "Readable transcript has English/CJK spacing issues",
                source="transcript.readable.md",
                count=english_cjk_spacing_issue_count,
            )
        )
    if ascii_punctuation_in_cjk_count:
        issues.append(
            issue_factory(
                "warning",
                "readable_ascii_punctuation_in_cjk",
                "Readable transcript has ASCII punctuation between CJK characters",
                source="transcript.readable.md",
                count=ascii_punctuation_in_cjk_count,
            )
        )
    if unmatched_count:
        issues.append(
            issue_factory(
                "warning",
                "readable_unmatched_brackets",
                "Readable transcript has unmatched brackets",
                source="transcript.readable.md",
                count=unmatched_count,
            )
        )
    if review_only_count:
        issues.append(
            issue_factory(
                "review",
                "readable_review_only_terms",
                "Readable transcript still contains review-only correction candidates",
                source="corrections.json",
                count=review_only_count,
            )
        )
    return metrics, issues
