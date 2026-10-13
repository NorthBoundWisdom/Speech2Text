from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from .numeric import as_float
from .runtime_defaults import (
    TAIL_HIGH_COMPRESSION_MAX_CHARS,
    TAIL_HIGH_COMPRESSION_RATIO,
    TAIL_LOW_CONFIDENCE_AVG_LOGPROB,
    TAIL_LOW_CONFIDENCE_MAX_CHARS,
    TAIL_LOW_CONFIDENCE_MIN_DURATION_SECONDS,
    TAIL_LOW_CONFIDENCE_WINDOW_SECONDS,
)
from .punctuation import normalize_chinese_punctuation_with_report
from .utils import compact_ws, read_json

PUNCTUATION_PROMPT_SUFFIX = (
    "重要：这是一段中文播客访谈，请用简体中文逐字转写，"
    "在停顿处使用逗号、句号、问号和顿号等自然中文标点。"
)
DEFAULT_PROMPT_MAX_CHARS = 800

ASR_ARTIFACT_CORRECTIONS = {
    "＞?": "？",
    ">?": "？",
    "＞": "，",
    "�": "",
}

RUNAWAY_REPEAT_RE = re.compile(
    r"(?P<unit>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]{1,16})"
    r"(?:(?:\s*[,，、。！？?!]\s*)(?P=unit)){2,}"
    r"(?:\s*[,，、。！？?!]\s*)?"
)
RUNAWAY_CLAUSE_REPEAT_RE = re.compile(
    r"(?P<unit>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9A-Za-z，,、：:；;（）()《》“”\"' \-]{4,80}?[。！？?!\.])"
    r"(?P<tail>(?P=unit){2,})"
    r"(?P<fragment>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]{0,16})"
)
TRAILING_FRAGMENT_RE = re.compile(
    r"(?:[,，、\s]*(?:但是|因为|如果|然后|所以|就是|那|我说|他说|她说|我们说|他们说)){1,4}"
    r"[,，、\s]*$"
)
TITLE_CONTEXT_RE = re.compile(
    r"(?P<prefix>欢迎来到|欢迎收听|这里是|您正在收听|正在收听|收听|来到)"
    r"(?P<title>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9·]{2,16})"
)
TITLE_EPISODE_RE = re.compile(
    r"(?P<title>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9·]{2,16})(?P<suffix>的第\d+期)"
)
TITLE_DISCUSSION_RE = re.compile(
    r"(?P<prefix>讨论|聊到|聊|提到|讲到|说到|谈到|关于|看过|看了|看|读过|读了|读|演过|演了|演|表演|改编)"
    r"\s*(?P<title>[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9·]{2,16})(?=[，,。、；;：:！？?!\s]|$)"
)

GLOSSARY_LIST_KEYS = ("people", "organizations", "technical_terms", "titles")
NOISY_PROMPT_TERM_RE = re.compile(
    r"(?:https?://|www\.|/|\\|"
    r"\.(?:com|net|org|fm|cn|io|ai|jpg|jpeg|png|webp|gif|m4a|mp3|wav|json|md)(?:$|[/?#]))",
    re.IGNORECASE,
)
ISO_DURATION_RE = re.compile(r"PT(?:\d+[HMS])+", re.IGNORECASE)


@dataclass(frozen=True)
class CorrectionResult:
    text: str
    report: list[dict[str, Any]]


def default_glossary() -> dict[str, Any]:
    return {
        "people": [],
        "organizations": [],
        "titles": [],
        "technical_terms": ["AI", "AGI", "ChatGPT", "大模型", "智能体", "播客", "字幕", "转写"],
        "common_corrections": {},
        "safe_global": {},
        "contextual_regex": [],
        "review_only": {},
    }


def load_glossary(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    data = read_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Glossary must be a JSON object: {p}")
    return data


def glossary_terms(glossary: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in GLOSSARY_LIST_KEYS:
        values = glossary.get(key, [])
        if isinstance(values, list):
            terms.extend(str(x) for x in values if str(x).strip())
    return terms


def merge_glossaries(*glossaries: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "people": [],
        "organizations": [],
        "technical_terms": [],
        "titles": [],
        "common_corrections": {},
    }
    seen: dict[str, set[str]] = {
        "people": set(),
        "organizations": set(),
        "technical_terms": set(),
        "titles": set(),
    }
    for glossary in glossaries:
        if not glossary:
            continue
        for key in GLOSSARY_LIST_KEYS:
            values = glossary.get(key, [])
            if not isinstance(values, list):
                continue
            for value in values:
                item = str(value).strip()
                if item and item not in seen[key]:
                    seen[key].add(item)
                    merged[key].append(item)
        corrections = glossary.get("common_corrections", {})
        if isinstance(corrections, dict):
            for wrong, right in corrections.items():
                wrong_s = str(wrong).strip()
                right_s = str(right).strip()
                if wrong_s and right_s:
                    merged["common_corrections"][wrong_s] = right_s
        safe_global = glossary.get("safe_global", {})
        if isinstance(safe_global, dict):
            merged.setdefault("safe_global", {})
            for wrong, right in safe_global.items():
                wrong_s = str(wrong).strip()
                right_s = str(right).strip()
                if wrong_s and right_s:
                    merged["safe_global"][wrong_s] = right_s
        contextual = glossary.get("contextual_regex", [])
        if isinstance(contextual, list):
            merged.setdefault("contextual_regex", [])
            merged["contextual_regex"].extend(item for item in contextual if isinstance(item, dict))
        review_only = glossary.get("review_only", {})
        if isinstance(review_only, dict):
            merged.setdefault("review_only", {})
            for observed, suggestions in review_only.items():
                if isinstance(suggestions, list):
                    merged["review_only"][str(observed)] = [str(item) for item in suggestions]
    return {key: value for key, value in merged.items() if value}


def _append_with_budget(parts: list[str], text: str, *, remaining: int) -> int:
    clean = compact_ws(text)
    if not clean or remaining <= 0:
        return remaining
    if len(clean) <= remaining:
        parts.append(clean)
        return remaining - len(clean)
    parts.append(clean[:remaining].rstrip("，,、。；;：: \t\r\n"))
    return 0


def _term_prompt(terms: list[str], *, max_chars: int, language: str | None = "zh") -> str | None:
    prefix = "重点人名、机构名和术语：" if language == "zh" else "Names and terms: "
    suffix = "。"
    budget = max_chars - len(prefix) - len(suffix)
    if budget <= 0:
        return None
    selected: list[str] = []
    used = 0
    for term in terms:
        clean = compact_ws(term)
        if not _promptworthy_term(clean):
            continue
        added = len(clean) + (1 if selected else 0)
        if used + added > budget:
            break
        selected.append(clean)
        used += added
    if not selected:
        return None
    return prefix + "、".join(selected) + suffix


def _promptworthy_term(term: str) -> bool:
    clean = term.strip()
    if not clean or len(clean) > 48:
        return False
    if clean.lower() in {"m4a", "mp3", "wav", "flac", "aac", "jpg", "jpeg", "png", "webp"}:
        return False
    if ISO_DURATION_RE.fullmatch(clean):
        return False
    if NOISY_PROMPT_TERM_RE.search(clean):
        return False
    if re.search(r"[A-Za-z]", clean) and clean.count(".") >= 2:
        return False
    return True


def make_prompt(
    base_prompt: str | None,
    glossary: dict[str, Any] | None,
    *,
    topic_summary: str | None = None,
    max_chars: int = DEFAULT_PROMPT_MAX_CHARS,
    language: str | None = "zh",
) -> str | None:
    max_chars = max(1, max_chars)
    suffix = (
        PUNCTUATION_PROMPT_SUFFIX
        if language == "zh"
        else "Use natural punctuation for each spoken language."
    )[:max_chars]
    remaining = max_chars - len(suffix)
    parts: list[str] = []
    if base_prompt:
        remaining = _append_with_budget(parts, base_prompt, remaining=remaining)
    if topic_summary:
        remaining = _append_with_budget(
            parts, f"节目背景摘要：{topic_summary}", remaining=remaining
        )
    if glossary and remaining > 0:
        terms = glossary_terms(glossary)
        term_prompt = _term_prompt(terms, max_chars=remaining, language=language)
        if term_prompt:
            remaining = _append_with_budget(parts, term_prompt, remaining=remaining)
    body = "\n".join(p for p in parts if p).strip()
    if body:
        body_budget = max_chars - len(suffix) - 1
        if body_budget <= 0:
            prompt = suffix
        else:
            body = body[:body_budget].rstrip("，,、。；;：: \t\r\n")
            prompt = f"{body}\n{suffix}"
    else:
        prompt = suffix
    return prompt or None


@lru_cache(maxsize=512)
def _ascii_boundary_pattern(wrong: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(wrong)}(?![A-Za-z0-9])")


def _replace_with_count(text: str, wrong: str, right: str) -> tuple[str, int]:
    if wrong.isascii() and re.search(r"[A-Za-z0-9]", wrong):
        return _ascii_boundary_pattern(wrong).subn(right, text)
    return text.replace(wrong, right), text.count(wrong)


def _apply_builtin_artifact_corrections(text: str) -> tuple[str, list[dict[str, Any]]]:
    corrected = text
    report: list[dict[str, Any]] = []
    for wrong, right in ASR_ARTIFACT_CORRECTIONS.items():
        corrected, count = _replace_with_count(corrected, wrong, right)
        if count:
            report.append({"from": wrong, "to": right, "count": count, "kind": "asr_artifact"})
    return corrected, report


def _required_runaway_repeat_count(unit: str) -> int:
    if len(unit) <= 3:
        return 6
    if len(unit) <= 8:
        return 4
    return 3


def _normalized_repeat_unit(text: str) -> str:
    return re.sub(r"[\s,，、。！？?!\.：:；;（）()《》“”\"'\-]", "", text)


def _required_clause_repeat_count(unit: str) -> int:
    normalized = _normalized_repeat_unit(unit)
    if len(normalized) <= 5:
        return 4
    return 3


def _cleanup_after_repetition_trim(text: str) -> str:
    corrected = re.sub(r"\s*([,，、。！？?!])\s*", r"\1", text)
    corrected = re.sub(r"^[,，、。！？?!\s]+", "", corrected)
    corrected = re.sub(r"[,，、\s]+$", "", corrected)
    return corrected


def _trim_runaway_clause_repetitions(text: str) -> tuple[str, list[dict[str, Any]]]:
    report: list[dict[str, Any]] = []

    def replacement(match: re.Match[str]) -> str:
        unit = match.group("unit")
        tail = match.group("tail")
        fragment = match.group("fragment") or ""
        count = 1 + (len(tail) // len(unit))
        if count < _required_clause_repeat_count(unit):
            return match.group(0)

        unit_key = _normalized_repeat_unit(unit)
        fragment_key = _normalized_repeat_unit(fragment)
        suffix = "" if fragment_key and unit_key.startswith(fragment_key) else fragment
        replacement_text = unit + suffix
        report.append(
            {
                "from": match.group(0),
                "to": replacement_text,
                "count": count,
                "kind": "asr_runaway_clause_repetition",
            }
        )
        return replacement_text

    corrected = RUNAWAY_CLAUSE_REPEAT_RE.sub(replacement, text)
    if report:
        corrected = _cleanup_after_repetition_trim(corrected)
    return corrected, report


def _remove_runaway_repetitions(text: str) -> tuple[str, list[dict[str, Any]]]:
    report: list[dict[str, Any]] = []

    def replacement(match: re.Match[str]) -> str:
        unit = match.group("unit")
        count = match.group(0).count(unit)
        if count < _required_runaway_repeat_count(unit):
            return match.group(0)
        report.append(
            {"from": match.group(0), "to": "", "count": count, "kind": "asr_runaway_repetition"}
        )
        return ""

    corrected = RUNAWAY_REPEAT_RE.sub(replacement, text)
    if report:
        corrected = TRAILING_FRAGMENT_RE.sub("", corrected)
        corrected = _cleanup_after_repetition_trim(corrected)
    return corrected, report


def _edit_distance(a: str, b: str, *, max_distance: int) -> int:
    if abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        row_min = i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
            row_min = min(row_min, current[-1])
        if row_min > max_distance:
            return max_distance + 1
        previous = current
    return previous[-1]


def _cjk_key(value: str) -> str:
    return "".join(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", value))


def _title_values(glossary: dict[str, Any] | None) -> list[str]:
    if not glossary:
        return []
    values = glossary.get("titles", [])
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _is_plausible_title_variant(candidate: str, title: str) -> bool:
    if candidate == title:
        return False
    if not (2 <= len(candidate) <= 12 and len(candidate) == len(title)):
        return False
    if not re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", candidate + title):
        return False
    same_positions = sum(1 for left, right in zip(candidate, title) if left == right)
    max_distance = 1 if len(title) <= 3 else 2
    if same_positions < max(1, len(title) - max_distance):
        return False
    return _edit_distance(candidate, title, max_distance=max_distance) <= max_distance


def _apply_contextual_title_corrections(
    text: str, glossary: dict[str, Any] | None
) -> tuple[str, list[dict[str, Any]]]:
    titles = _title_values(glossary)
    if not titles:
        return text, []
    report: list[dict[str, Any]] = []

    def replacement(match: re.Match[str]) -> str:
        candidate = match.group("title")
        for title in titles:
            if _is_plausible_title_variant(candidate, title):
                report.append({"from": candidate, "to": title, "count": 1, "kind": "title_context"})
                return match.group("prefix") + title
        return match.group(0)

    corrected = TITLE_CONTEXT_RE.sub(replacement, text)

    def episode_replacement(match: re.Match[str]) -> str:
        candidate = match.group("title")
        for title in titles:
            if _is_plausible_title_variant(candidate, title):
                report.append({"from": candidate, "to": title, "count": 1, "kind": "title_context"})
                return title + match.group("suffix")
        return match.group(0)

    corrected = TITLE_EPISODE_RE.sub(episode_replacement, corrected)

    def discussion_replacement(match: re.Match[str]) -> str:
        candidate = match.group("title")
        for title in titles:
            if _is_plausible_title_variant(candidate, title):
                report.append({"from": candidate, "to": title, "count": 1, "kind": "title_context"})
                return match.group("prefix") + title
        return match.group(0)

    corrected = TITLE_DISCUSSION_RE.sub(discussion_replacement, corrected)
    return corrected, report


def _entity_near_miss_terms(glossary: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not glossary:
        return []
    terms: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key in ("people", "organizations"):
        values = glossary.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            term = str(value).strip()
            cjk = _cjk_key(term)
            if term and cjk == term and 3 <= len(cjk) <= 12 and term not in seen:
                seen.add(term)
                terms.append((term, cjk))
    return sorted(terms, key=lambda item: (-len(item[1]), item[0]))


def _is_plausible_entity_variant(candidate: str, target: str) -> bool:
    if candidate == target or len(candidate) != len(target):
        return False
    if "的" in candidate:
        return False
    for suffix in ("大学", "学院", "实验室", "公司", "团队", "课题组"):
        if target.endswith(suffix) and not candidate.endswith(suffix):
            return False
    if candidate[0] != target[0] and candidate[-1] != target[-1]:
        return False
    same_positions = sum(1 for left, right in zip(candidate, target) if left == right)
    if same_positions < len(target) - 1:
        return False
    return _edit_distance(candidate, target, max_distance=1) <= 1


def _apply_entity_near_miss_corrections(
    text: str, glossary: dict[str, Any] | None
) -> tuple[str, list[dict[str, Any]]]:
    terms = _entity_near_miss_terms(glossary)
    if not terms:
        return text, []
    report: list[dict[str, Any]] = []

    def run_replacement(match: re.Match[str]) -> str:
        run = match.group(0)
        out: list[str] = []
        index = 0
        while index < len(run):
            for term, key in terms:
                size = len(key)
                candidate = run[index : index + size]
                if len(candidate) == size and _is_plausible_entity_variant(candidate, key):
                    out.append(term)
                    report.append(
                        {"from": candidate, "to": term, "count": 1, "kind": "glossary_near_miss"}
                    )
                    index += size
                    break
            else:
                out.append(run[index])
                index += 1
        return "".join(out)

    corrected = re.sub(r"[\u3400-\u4dbf\u4e00-\u9fff]{3,}", run_replacement, text)
    return corrected, report


def _glossary_correction_maps(glossary: dict[str, Any] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key in ("common_corrections", "safe_global"):
        corrections = (glossary or {}).get(key, {})
        if not isinstance(corrections, dict):
            continue
        for wrong, right in corrections.items():
            wrong_s = str(wrong)
            right_s = str(right)
            if wrong_s:
                merged[wrong_s] = right_s
    return merged


@lru_cache(maxsize=256)
def _compile_contextual_regex(pattern: str) -> re.Pattern[str] | None:
    try:
        return re.compile(pattern)
    except re.error:
        return None


def _apply_contextual_regex_corrections(
    text: str, glossary: dict[str, Any] | None
) -> tuple[str, list[dict[str, Any]]]:
    rules = (glossary or {}).get("contextual_regex", [])
    if not isinstance(rules, list):
        return text, []
    corrected = text
    report: list[dict[str, Any]] = []
    full_context = "\n".join(glossary_terms(glossary or {})) + "\n" + corrected
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        name = str(rule.get("name") or rule.get("pattern") or "contextual_regex")
        pattern = str(rule.get("pattern") or "")
        replacement = str(rule.get("replacement") or "")
        if not pattern:
            continue
        requires_terms = rule.get("requires_terms", [])
        if isinstance(requires_terms, list) and any(
            str(term) not in full_context for term in requires_terms
        ):
            continue
        compiled = _compile_contextual_regex(pattern)
        if compiled is None:
            continue
        corrected, count = compiled.subn(replacement, corrected)
        if count:
            report.append(
                {
                    "from": pattern,
                    "to": replacement,
                    "count": count,
                    "kind": "contextual_regex",
                    "rule_name": name,
                }
            )
    return corrected, report


def _review_only_report(text: str, glossary: dict[str, Any] | None) -> list[dict[str, Any]]:
    review_only = (glossary or {}).get("review_only", {})
    if not isinstance(review_only, dict):
        return []
    report: list[dict[str, Any]] = []
    for observed, suggestions in review_only.items():
        observed_s = str(observed)
        if not observed_s:
            continue
        count = text.count(observed_s)
        if count:
            report.append(
                {
                    "from": observed_s,
                    "to": "",
                    "count": count,
                    "kind": "review_only",
                    "suggestions": [str(item) for item in suggestions]
                    if isinstance(suggestions, list)
                    else [],
                }
            )
    return report


def _as_float(value: Any) -> float | None:
    return as_float(value)


def _segment_metric(segment: dict[str, Any], key: str) -> float | None:
    value = _as_float(segment.get(key))
    if value is not None:
        return value
    raw = segment.get("raw")
    if isinstance(raw, dict):
        return _as_float(raw.get(key))
    return None


def _suppress_tail_hallucination_segments(
    segments: list[dict[str, Any]], audio_duration: float | None
) -> list[dict[str, Any]]:
    if audio_duration is None or audio_duration <= 0:
        return []
    report: list[dict[str, Any]] = []
    tail_start = max(0.0, audio_duration - TAIL_LOW_CONFIDENCE_WINDOW_SECONDS)
    for index in range(len(segments) - 1, -1, -1):
        segment = segments[index]
        text = compact_ws(str(segment.get("text", "")))
        if not text:
            continue
        start = _as_float(segment.get("start")) or 0.0
        end = _as_float(segment.get("end")) or start
        if start < tail_start and end < audio_duration - 5.0:
            break
        duration = max(0.0, min(end, audio_duration) - start)
        avg_logprob = _segment_metric(segment, "avg_logprob")
        compression_ratio = _segment_metric(segment, "compression_ratio")
        low_confidence_tail = (
            avg_logprob is not None
            and avg_logprob <= TAIL_LOW_CONFIDENCE_AVG_LOGPROB
            and duration >= TAIL_LOW_CONFIDENCE_MIN_DURATION_SECONDS
            and len(text) <= TAIL_LOW_CONFIDENCE_MAX_CHARS
            and end >= audio_duration - 5.0
        )
        high_compression_tail = (
            compression_ratio is not None
            and compression_ratio >= TAIL_HIGH_COMPRESSION_RATIO
            and len(text) <= TAIL_HIGH_COMPRESSION_MAX_CHARS
            and (start >= audio_duration - 10.0 or end >= audio_duration - 1.0)
        )
        is_tail_hallucination = low_confidence_tail or high_compression_tail
        if not is_tail_hallucination:
            break
        segment["text"] = ""
        segment["suppressed"] = True
        segment["suppress_reason"] = "tail_hallucination"
        segment["end"] = min(end, audio_duration)
        report.append(
            {
                "from": text,
                "to": "",
                "count": 1,
                "kind": "asr_tail_hallucination",
                "matches": [
                    {
                        "segment_index": index,
                        "start": start,
                        "end": end,
                        "before": text,
                        "after": "",
                    }
                ],
            }
        )
    return list(reversed(report))


def apply_corrections(text: str, glossary: dict[str, Any] | None) -> CorrectionResult:
    corrected = text or ""
    corrected, report = _apply_builtin_artifact_corrections(corrected)
    corrected, clause_repetition_report = _trim_runaway_clause_repetitions(corrected)
    report.extend(clause_repetition_report)
    corrected, repetition_report = _remove_runaway_repetitions(corrected)
    report.extend(repetition_report)
    corrected, title_report = _apply_contextual_title_corrections(corrected, glossary)
    report.extend(title_report)
    corrected, contextual_report = _apply_contextual_regex_corrections(corrected, glossary)
    report.extend(contextual_report)
    corrected, entity_near_miss_report = _apply_entity_near_miss_corrections(corrected, glossary)
    report.extend(entity_near_miss_report)
    corrections = _glossary_correction_maps(glossary)
    for wrong, right in sorted(
        corrections.items(), key=lambda item: len(str(item[0])), reverse=True
    ):
        wrong_s = str(wrong)
        right_s = str(right)
        if not wrong_s:
            continue
        corrected, count = _replace_with_count(corrected, wrong_s, right_s)
        if count:
            kind = (
                "safe_global"
                if wrong_s in ((glossary or {}).get("safe_global", {}) or {})
                else "glossary"
            )
            report.append({"from": wrong_s, "to": right_s, "count": count, "kind": kind})
    report.extend(_review_only_report(corrected, glossary))
    corrected, punctuation_report = normalize_chinese_punctuation_with_report(corrected)
    report.extend(punctuation_report)
    return CorrectionResult(text=corrected, report=report)


def apply_corrections_to_segments(
    segments: list[dict[str, Any]],
    glossary: dict[str, Any] | None,
    *,
    audio_duration: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply deterministic text corrections to transcript segments.

    Args:
        segments: Transcript segment dictionaries. The input list is not
            mutated.
        glossary: Effective glossary and correction rules.
        audio_duration: Optional full audio duration used by tail hallucination
            suppression.

    Returns:
        A pair of corrected segments and an aggregate correction report.
    """

    corrected_segments = deepcopy(segments)
    aggregate: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    def record(
        item: dict[str, Any],
        *,
        segment_index: int | None = None,
        segment: dict[str, Any] | None = None,
        before: str = "",
        after: str = "",
    ) -> None:
        kind = str(item.get("kind") or "glossary")
        rule_name = str(item.get("rule_name") or item.get("from") or kind)
        key = (str(item.get("from", "")), str(item.get("to", "")), kind, rule_name)
        if key not in aggregate:
            aggregate[key] = {
                "from": key[0],
                "to": key[1],
                "count": 0,
                "kind": kind,
                "rule_name": rule_name,
                "matches": [],
            }
            if "suggestions" in item:
                aggregate[key]["suggestions"] = item["suggestions"]
        aggregate[key]["count"] += int(item["count"])
        if "matches" in item and isinstance(item["matches"], list):
            aggregate[key]["matches"].extend(item["matches"])
        elif segment_index is not None and segment is not None:
            aggregate[key]["matches"].append(
                {
                    "segment_index": segment_index,
                    "start": float(segment.get("start", 0.0)),
                    "end": float(segment.get("end", 0.0)),
                    "before": before,
                    "after": after,
                }
            )

    for segment_index, segment in enumerate(corrected_segments):
        before = str(segment.get("text", ""))
        result = apply_corrections(str(segment.get("text", "")), glossary)
        segment["text"] = result.text
        for item in result.report:
            record(
                item, segment_index=segment_index, segment=segment, before=before, after=result.text
            )
    for item in _suppress_tail_hallucination_segments(corrected_segments, audio_duration):
        record(item)
    report = [aggregate[key] for key in sorted(aggregate)]
    return corrected_segments, report


def segments_to_plain_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(
        compact_ws(str(s.get("text", ""))) for s in segments if compact_ws(str(s.get("text", "")))
    )
