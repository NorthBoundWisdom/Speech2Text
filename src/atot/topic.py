from __future__ import annotations

import re
from typing import Any

from .rules import load_rule_file_for_text


_CJK = r"\u3400-\u4dbf\u4e00-\u9fff"
_NOISY_ASCII_RE = re.compile(
    r"(?:https?://|www\.|/|\\|"
    r"\.(?:com|net|org|fm|cn|io|ai|jpg|jpeg|png|webp|gif|m4a|mp3|wav|json|md)(?:$|[/?#]))",
    re.IGNORECASE,
)
_ISO_DURATION_RE = re.compile(r"PT(?:\d+[HMS])+", re.IGNORECASE)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip(" \t\r\n，。、；：:,.()（）[]【】「」《》\"'")
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _not_org_like(value: str) -> bool:
    return not any(token in value for token in ("大学", "学院", "公司", "实验室", "团队", "课题组"))


def _clean_org(value: str) -> str:
    item = value.strip()
    for prefix in (
        "以及",
        "作为",
        "如今作为",
        "现为",
        "目前是",
        "他是",
        "她是",
        "我是",
        "和",
        "与",
        "在",
        "到",
    ):
        if item.startswith(prefix):
            item = item[len(prefix) :]
    return item


def _clean_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>\-]+", " ", text)
    return text


def _extract_people(text: str) -> list[str]:
    people: list[str] = []
    patterns = [
        rf"([{_CJK}]{{2,4}})(?:博士|老师|教授|导师|先生|女士)",
        rf"(?:教授|导师|主播|一作)\s*([{_CJK}]{{2,4}})",
        rf"([{_CJK}]{{2,4}})（@[A-Za-z0-9_{_CJK}]+）",
    ]
    for pattern in patterns:
        people.extend(re.findall(pattern, text))
    return [person for person in _unique(people) if _not_org_like(person)]


def _extract_organizations(text: str) -> list[str]:
    organizations: list[str] = []
    organizations.extend(re.findall(r"「([^」]{2,24})」", text))
    organizations.extend(re.findall(r"《([^》]{2,24})》", text))
    organizations.extend(
        re.findall(
            rf"(?<![{_CJK}])([{_CJK}]{{2,12}}(?:大学|学院|实验室))(?=(?:导师|教授|老师)|[^{_CJK}]|$)",
            text,
        )
    )
    for zh, latin in re.findall(
        rf"([{_CJK}]{{2,12}})（([A-Za-z][A-Za-z0-9 ._-]{{1,32}})）创始人", text
    ):
        organizations.extend([zh, latin])
    return _unique([_clean_org(org) for org in organizations])


def _extract_titles(text: str) -> list[str]:
    titles: list[str] = []
    titles.extend(re.findall(
        r"(?:^|\n)\s*(?:-\s*)?(?:Podcast|Show|Series):\s*([^\n]{2,96})",
        text,
        flags=re.IGNORECASE,
    ))
    titles.extend(re.findall(r"(?:节目|播客|栏目)[：:]\s*([^\n，。,；;]{2,24})", text))
    titles.extend(re.findall(r"《([^》]{2,24})》", text))
    return _unique(titles)


def _extract_terms(
    text: str, *, rule_packs: tuple[str, ...] | list[str] | None = None
) -> list[str]:
    rules = load_rule_file_for_text("topic_rules.json", text, packs=rule_packs)
    terms: list[str] = []
    ascii_terms = re.findall(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9+._/-]{1,})(?![A-Za-z0-9])", text)
    keep_mixed = set(rules.get("ascii_keep_terms", []))
    terms.extend(term for term in ascii_terms if _is_topic_term(term, keep_mixed))
    known_phrases = [str(item) for item in rules.get("known_phrases", []) if str(item).strip()]
    terms.extend(phrase for phrase in known_phrases if phrase in text)
    return _unique(terms)


def _is_topic_term(term: str, keep_mixed: set[str]) -> bool:
    clean = term.strip()
    if not clean:
        return False
    if clean in keep_mixed:
        return True
    if clean.lower() in {"m4a", "mp3", "wav", "flac", "aac", "jpg", "jpeg", "png", "webp"}:
        return False
    if len(clean) > 48:
        return False
    if _ISO_DURATION_RE.fullmatch(clean):
        return False
    if _NOISY_ASCII_RE.search(clean):
        return False
    if clean.count(".") >= 2:
        return False
    return clean.isupper() or any(ch.isdigit() for ch in clean)


def _term_set(glossary: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("people", "organizations", "technical_terms", "titles"):
        for item in glossary.get(key, []) or []:
            if str(item).strip():
                values.add(str(item).strip())
    return values


def _known_corrections(
    terms: set[str], *, rule_packs: tuple[str, ...] | list[str] | None = None
) -> dict[str, str]:
    rules = load_rule_file_for_text("topic_rules.json", "\n".join(sorted(terms)), packs=rule_packs)
    corrections: dict[str, str] = {}

    def add(wrong: str, right: str) -> None:
        if wrong != right and right in terms:
            corrections[wrong] = right

    known = rules.get("known_corrections", {})
    if isinstance(known, dict):
        for wrong, right in known.items():
            add(str(wrong), str(right))
    for rule in rules.get("conditional_corrections", []) or []:
        if not isinstance(rule, dict):
            continue
        when_any = {str(item) for item in rule.get("when_any", [])}
        if when_any.intersection(terms):
            wrong = str(rule.get("from", "")).strip()
            right = str(rule.get("to", "")).strip()
            if wrong and right and wrong != right:
                corrections[wrong] = right
    return corrections


def extract_episode_glossary(
    topic_text: str | None,
    *,
    rule_packs: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    if not topic_text:
        return {}
    text = _clean_markdown(topic_text)
    glossary: dict[str, Any] = {
        "people": _extract_people(text),
        "organizations": _extract_organizations(text),
        "titles": _extract_titles(text),
        "technical_terms": _extract_terms(text, rule_packs=rule_packs),
    }
    corrections = _known_corrections(_term_set(glossary), rule_packs=rule_packs)
    if corrections:
        glossary["common_corrections"] = corrections
    return {key: value for key, value in glossary.items() if value}
