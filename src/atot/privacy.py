from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)")
ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
ADDRESS_RE = re.compile(
    r"(?:[\u3400-\u4dbf\u4e00-\u9fff]{2,}(?:省|自治区|特别行政区))?"
    r"[\u3400-\u4dbf\u4e00-\u9fff]{2,}(?:市|区|县)"
    r"[\u3400-\u4dbf\u4e00-\u9fff0-9A-Za-z]{2,}(?:路|街|巷|弄|道)"
    r"[\u3400-\u4dbf\u4e00-\u9fff0-9A-Za-z-]{0,16}(?:号|室|楼|单元)?"
)
PERSON_CONTEXT_RE = re.compile(
    r"(?P<prefix>(?:姓名|联系人|真实姓名|收件人|嘉宾本名|我的名字是|我叫)[:：\s]*)"
    r"(?P<name>[\u3400-\u4dbf\u4e00-\u9fff]{2,4})"
)
PRIVATE_HINTS = ("不要公开", "私下说", "别外传", "保密", "身份证", "护照")


def detect_privacy_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    patterns = [
        ("email", EMAIL_RE),
        ("phone", PHONE_RE),
        ("national_id", ID_RE),
        ("address", ADDRESS_RE),
    ]
    for kind, pattern in patterns:
        matches = pattern.findall(text or "")
        if matches:
            findings.append({"type": kind, "count": len(matches), "examples": matches[:3]})
    person_matches = [match.group("name") for match in PERSON_CONTEXT_RE.finditer(text or "")]
    if person_matches:
        findings.append(
            {
                "type": "person_unconfirmed",
                "count": len(person_matches),
                "examples": person_matches[:3],
            }
        )
    hint_hits = [hint for hint in PRIVATE_HINTS if hint in (text or "")]
    if hint_hits:
        findings.append({"type": "privacy_hint", "count": len(hint_hits), "examples": hint_hits})
    return findings


def redact_pii(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    counters = {"EMAIL": 0, "PHONE": 0, "ID": 0, "ADDRESS": 0, "PERSON_UNCONFIRMED": 0}

    def replace(pattern: re.Pattern[str], label: str, value: str) -> str:
        def repl(match: re.Match[str]) -> str:
            original = match.group(0)
            if original not in mapping:
                counters[label] += 1
                mapping[original] = f"[{label}_{counters[label]}]"
            return mapping[original]

        return pattern.sub(repl, value)

    redacted = replace(EMAIL_RE, "EMAIL", text or "")
    redacted = replace(PHONE_RE, "PHONE", redacted)
    redacted = replace(ID_RE, "ID", redacted)
    redacted = replace(ADDRESS_RE, "ADDRESS", redacted)

    def person_repl(match: re.Match[str]) -> str:
        original = match.group("name")
        if original not in mapping:
            counters["PERSON_UNCONFIRMED"] += 1
            mapping[original] = f"[PERSON_UNCONFIRMED_{counters['PERSON_UNCONFIRMED']}]"
        return match.group("prefix") + mapping[original]

    redacted = PERSON_CONTEXT_RE.sub(person_repl, redacted)
    return redacted, {placeholder: original for original, placeholder in mapping.items()}
