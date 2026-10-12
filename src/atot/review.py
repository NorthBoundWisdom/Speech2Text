from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .corrections import glossary_terms
from .rules import load_rule_file, load_rule_file_for_text, selected_rule_packs
from .utils import compact_ws, seconds_to_hms


def _rules(
    context_text: str = "", *, rule_packs: tuple[str, ...] | list[str] | None = None
) -> dict[str, Any]:
    if context_text:
        return load_rule_file_for_text("review_rules.json", context_text, packs=rule_packs)
    return load_rule_file("review_rules.json", packs=selected_rule_packs("", rule_packs))


def _confusions(rules: dict[str, Any]) -> dict[str, list[str]]:
    raw = rules.get("confusions", {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(target): [str(item) for item in variants if str(item).strip()]
        for target, variants in raw.items()
        if isinstance(variants, list)
    }


def _term_set(glossary: dict[str, Any] | None) -> set[str]:
    if not glossary:
        return set()
    return {term.strip() for term in glossary_terms(glossary) if term.strip()}


def _near_miss_term_set(glossary: dict[str, Any] | None, rules: dict[str, Any]) -> set[str]:
    if not glossary:
        return set()
    terms: set[str] = set()
    for key in ("people", "organizations", "titles"):
        values = glossary.get(key, [])
        if isinstance(values, list):
            terms.update(
                str(term).strip()
                for term in values
                if str(term).strip() and not re.search(r"[A-Za-z]", str(term))
            )
    excluded = {str(item) for item in rules.get("near_miss_excluded_terms", [])}
    values = glossary.get("technical_terms", [])
    if isinstance(values, list):
        for term in values:
            clean = str(term).strip()
            if (
                clean
                and clean not in excluded
                and len(_cjk_key(clean)) >= 5
                and not re.search(r"[A-Za-z]", clean)
            ):
                terms.add(clean)
    return terms


def _title_term_set(glossary: dict[str, Any] | None) -> set[str]:
    if not glossary:
        return set()
    values = glossary.get("titles", [])
    if not isinstance(values, list):
        return set()
    return {str(term).strip() for term in values if str(term).strip()}


def _has_token(text: str, token: str, rules: dict[str, Any]) -> bool:
    if token.isascii() and re.search(r"[A-Za-z0-9]", token):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text) is not None
    boundaries = rules.get("cjk_variant_boundaries", {})
    if isinstance(boundaries, dict) and token in boundaries:
        return re.search(str(boundaries[token]), text) is not None
    return token in text


def _count_token(text: str, token: str, rules: dict[str, Any]) -> int:
    if token.isascii() and re.search(r"[A-Za-z0-9]", token):
        return len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text))
    boundaries = rules.get("cjk_variant_boundaries", {})
    if isinstance(boundaries, dict) and token in boundaries:
        return len(re.findall(str(boundaries[token]), text))
    return text.count(token)


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


def _unknown_ascii_tokens(
    text: str, terms: set[str], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    expected = {term.lower() for term in terms if re.search(r"[A-Za-z]", term)}
    allowed = {str(item) for item in rules.get("allowed_ascii_tokens", [])}
    markers = [str(item) for item in rules.get("suspicious_ascii_markers", [])]
    counts = Counter(
        re.findall(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9._/-]{2,})(?![A-Za-z0-9])", text)
    )
    items: list[dict[str, Any]] = []
    for token, count in counts.most_common():
        low = token.lower()
        looks_suspicious = any(marker in token for marker in markers)
        if count < 2 or low in expected or low in allowed or not looks_suspicious:
            continue
        if any(low in term or term in low for term in expected):
            continue
        items.append({"token": token, "count": count})
        if len(items) >= 30:
            break
    return items


def _cjk_key(value: str) -> str:
    return "".join(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", value))


def _near_miss_distance(term: str) -> int:
    if len(term) <= 2:
        return 0
    if len(term) <= 4:
        return 1
    return 2


def _is_near_miss_candidate(target: str, candidate: str) -> bool:
    if "的" in candidate:
        return False
    for suffix in ("大学", "学院", "实验室", "系统"):
        if target.endswith(suffix) and not candidate.endswith(suffix):
            return False
    return True


def _glossary_near_misses(
    text: str, terms: set[str], *, title_terms: set[str]
) -> list[dict[str, Any]]:
    cjk_runs = list(re.finditer(r"[\u3400-\u4dbf\u4e00-\u9fff]{2,}", text))
    issues: list[dict[str, Any]] = []
    for term in sorted(terms, key=lambda item: (-len(item), item)):
        key = _cjk_key(term)
        max_distance = _near_miss_distance(key)
        if not max_distance:
            continue
        candidate_counts: Counter[str] = Counter()
        lengths = range(max(2, len(key) - 1), len(key) + 2)
        for run_match in cjk_runs:
            run = run_match.group(0)
            for size in lengths:
                if len(run) < size:
                    continue
                for start in range(0, len(run) - size + 1):
                    candidate = run[start : start + size]
                    if candidate == key or candidate in key or key in candidate:
                        continue
                    if not _is_near_miss_candidate(key, candidate):
                        continue
                    if candidate[0] != key[0] and candidate[-1] != key[-1]:
                        continue
                    candidate_end = run_match.start() + start + size
                    if (
                        term in title_terms
                        and candidate_end < len(text)
                        and text[candidate_end].isdigit()
                    ):
                        continue
                    if _edit_distance(candidate, key, max_distance=max_distance) <= max_distance:
                        candidate_counts[candidate] += 1
        candidates = [
            {"observed": observed, "count": count}
            for observed, count in sorted(
                candidate_counts.items(),
                key=lambda item: (
                    -item[1],
                    _edit_distance(item[0], key, max_distance=max_distance),
                    abs(len(item[0]) - len(key)),
                    item[0],
                ),
            )[:5]
            if count > 0
        ]
        if candidates:
            issues.append(
                {
                    "type": "possible_glossary_near_miss",
                    "severity": "medium" if key not in text else "low",
                    "target": term,
                    "items": candidates,
                }
            )
        if len(issues) >= 30:
            break
    return issues


def _looks_repetitive(text: str) -> bool:
    words = re.findall(r"[\u3400-\u4dbf\u4e00-\u9fffA-Za-z0-9]+", text)
    if len(words) < 24:
        return False
    joined = "".join(words)
    for size in range(6, 18):
        chunks = [joined[i : i + size] for i in range(0, max(0, len(joined) - size + 1), size)]
        if not chunks:
            continue
        most_common = Counter(chunks).most_common(1)[0]
        if most_common[1] >= 5:
            return True
    return False


def _suppressed_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suppressed: list[dict[str, Any]] = []
    for seg in segments:
        if seg.get("suppressed") is not True:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        suppressed.append(
            {
                "start": start,
                "end": end,
                "time": seconds_to_hms(start),
                "reason": str(seg.get("suppress_reason") or "suppressed"),
            }
        )
    return suppressed


def build_review(
    segments: list[dict[str, Any]],
    glossary: dict[str, Any] | None,
    *,
    rule_packs: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    terms = _term_set(glossary)
    full_text = "\n".join(compact_ws(str(seg.get("text", ""))) for seg in segments)
    suppressed_segments = _suppressed_segments(segments)
    rule_context = "\n".join([full_text, *sorted(terms)])
    effective_rule_packs = selected_rule_packs(rule_context, rule_packs)
    rules = _rules(rule_context, rule_packs=rule_packs)
    near_miss_terms = _near_miss_term_set(glossary, rules)
    title_terms = _title_term_set(glossary)
    issues: list[dict[str, Any]] = []

    confusions = _confusions(rules)
    for target, variants in confusions.items():
        if target not in terms and target not in full_text:
            continue
        for variant in variants:
            count = _count_token(full_text, variant, rules)
            if count:
                issues.append(
                    {
                        "type": "possible_term_confusion",
                        "severity": "medium",
                        "target": target,
                        "observed": variant,
                        "count": count,
                    }
                )

    unknown_ascii = _unknown_ascii_tokens(full_text, terms, rules)
    if unknown_ascii:
        issues.append(
            {
                "type": "unknown_ascii_tokens",
                "severity": "low",
                "items": unknown_ascii,
            }
        )
    near_miss_issues = _glossary_near_misses(full_text, near_miss_terms, title_terms=title_terms)
    issues.extend(near_miss_issues)
    near_miss_by_observed = {
        str(item.get("observed"))
        for issue in near_miss_issues
        for item in issue.get("items", [])
        if isinstance(item, dict)
    }

    segment_issues: list[dict[str, Any]] = []
    for seg in segments:
        text = compact_ws(str(seg.get("text", "")))
        if not text:
            continue
        flags: list[str] = []
        if _looks_repetitive(text):
            flags.append("possible_repetition")
        for target, variants in confusions.items():
            if target not in terms and target not in full_text:
                continue
            if any(_has_token(text, variant, rules) for variant in variants):
                flags.append("possible_term_confusion")
                break
        if any(observed and observed in text for observed in near_miss_by_observed):
            flags.append("possible_glossary_near_miss")
        if flags:
            segment_issues.append(
                {
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "time": seconds_to_hms(float(seg.get("start", 0.0))),
                    "flags": sorted(set(flags)),
                    "text": text,
                }
            )
    return {
        "summary": {
            "issue_count": len(issues),
            "segment_issue_count": len(segment_issues),
            "suppressed_segment_count": len(suppressed_segments),
            "terms_checked": sorted(terms),
            "rule_packs": list(effective_rule_packs),
        },
        "issues": issues,
        "segments": segment_issues,
        "suppressed_segments": suppressed_segments,
    }


def review_to_markdown(review: dict[str, Any]) -> str:
    summary = review.get("summary", {})
    lines = [
        "# Review",
        "",
        f"- Issue groups: {summary.get('issue_count', 0)}",
        f"- Segment issues: {summary.get('segment_issue_count', 0)}",
        f"- Suppressed segments: {summary.get('suppressed_segment_count', 0)}",
        "",
    ]
    suppressed = review.get("suppressed_segments", []) or []
    if suppressed:
        lines.extend(["## Suppressed Segments", ""])
        for item in suppressed[:80]:
            lines.append(
                f"- {item.get('time')} ({item.get('reason', 'suppressed')}) "
                f"{item.get('start', 0.0)}-{item.get('end', 0.0)}"
            )
        lines.append("")
    entity_consistency = review.get("entity_consistency")
    entities = (
        entity_consistency.get("entities", []) if isinstance(entity_consistency, dict) else []
    )
    if entities:
        lines.extend(["## Entity Consistency", ""])
        for entity in entities[:50]:
            variants = ", ".join(
                f"`{item.get('text')}`({item.get('count')})"
                for item in entity.get("variants", [])[:5]
                if isinstance(item, dict)
            )
            lines.append(
                f"- `{entity.get('canonical')}` [{entity.get('category')}] "
                f"{entity.get('recommendation', 'review_only')}: {variants}"
            )
        lines.append("")
    issues = review.get("issues", []) or []
    if issues:
        lines.extend(["## Issue Groups", ""])
        for issue in issues:
            if issue.get("type") == "possible_term_confusion":
                lines.append(
                    f"- Possible `{issue.get('observed')}` -> `{issue.get('target')}`: {issue.get('count')} hits"
                )
            elif issue.get("type") == "unknown_ascii_tokens":
                tokens = ", ".join(
                    f"`{item['token']}`({item['count']})" for item in issue.get("items", [])
                )
                lines.append(f"- Unknown ASCII tokens: {tokens}")
            elif issue.get("type") == "possible_glossary_near_miss":
                tokens = ", ".join(
                    f"`{item['observed']}`({item['count']})"
                    for item in issue.get("items", [])
                    if item
                )
                lines.append(f"- Possible near miss for `{issue.get('target')}`: {tokens}")
        lines.append("")
    segments = review.get("segments", []) or []
    if segments:
        lines.extend(["## Segments To Check", ""])
        for item in segments[:80]:
            flags = ", ".join(item.get("flags", []))
            lines.append(f"### {item.get('time')} ({flags})")
            lines.append("")
            lines.append(str(item.get("text", "")))
            lines.append("")
    return "\n".join(lines).strip() + "\n"
