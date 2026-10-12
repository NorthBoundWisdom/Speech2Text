from __future__ import annotations

import re
from typing import Any

CJK_RE = r"\u3400-\u4dbf\u4e00-\u9fff"


def _replace_with_report(
    text: str,
    pattern: str,
    replacement: str,
    *,
    name: str,
) -> tuple[str, dict[str, Any] | None]:
    corrected, count = re.subn(pattern, replacement, text)
    if not count:
        return corrected, None
    return corrected, {
        "from": name,
        "to": replacement,
        "count": count,
        "kind": "punctuation_normalization",
    }


def normalize_chinese_punctuation(text: str) -> str:
    return normalize_chinese_punctuation_with_report(text)[0]


def normalize_chinese_punctuation_with_report(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Normalize ASCII punctuation only when the local context is clearly Chinese.

    This intentionally leaves English-internal punctuation alone, including GPT-3,
    example.com, emails, and decimal numbers.
    """
    corrected = text or ""
    reports: list[dict[str, Any]] = []

    replacements = [
        (rf"(?<=[{CJK_RE}])\s*,\s*(?=[{CJK_RE}A-Za-z0-9])", "，", "chinese_comma"),
        (rf"(?<=[{CJK_RE}])\s*;\s*(?=[{CJK_RE}A-Za-z0-9])", "；", "chinese_semicolon"),
        (rf"(?<=[{CJK_RE}])\s*:\s*(?=[{CJK_RE}])", "：", "chinese_colon"),
        (rf"(?<=[{CJK_RE}])\s*\?\s*", "？", "chinese_question"),
        (rf"(?<=[{CJK_RE}])\s*!\s*", "！", "chinese_exclamation"),
        (rf"(?<=[{CJK_RE}])\s*\.\s*(?=$|[\s{CJK_RE}])", "。", "chinese_period"),
    ]
    for pattern, replacement, name in replacements:
        corrected, report = _replace_with_report(corrected, pattern, replacement, name=name)
        if report:
            reports.append(report)

    corrected = re.sub(r"\s+([，。！？；：])", r"\1", corrected)
    corrected = re.sub(r"([，。！？；：])\s+", r"\1", corrected)
    return corrected, reports
