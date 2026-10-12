from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any

from .utils import compact_ws, seconds_to_hms


ENTITY_KEYS = ("people", "organizations", "titles", "technical_terms")
ASCII_ENTITY_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9._/-]*(?:\s+[A-Za-z][A-Za-z0-9._/-]*)*)(?![A-Za-z0-9])"
)
CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]{2,}")


def _cjk_key(value: str) -> str:
    return "".join(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", value))


def _ascii_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).lower()


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


def _near_miss_distance(term: str) -> int:
    if len(term) <= 2:
        return 0
    if len(term) <= 4:
        return 1
    return 2


def _segment_times(
    segments: list[dict[str, Any]], text: str, *, limit: int = 12
) -> list[dict[str, Any]]:
    times: list[dict[str, Any]] = []
    for segment in segments:
        segment_text = compact_ws(str(segment.get("text", "")))
        if text not in segment_text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        times.append(
            {"start": round(start, 3), "end": round(end, 3), "time": seconds_to_hms(start)}
        )
        if len(times) >= limit:
            break
    return times


def _review_only_variants(glossary: dict[str, Any] | None) -> dict[str, set[str]]:
    review_only = (glossary or {}).get("review_only", {})
    variants: dict[str, set[str]] = defaultdict(set)
    if not isinstance(review_only, dict):
        return variants
    for observed, suggestions in review_only.items():
        if not isinstance(suggestions, list):
            continue
        for suggestion in suggestions:
            canonical = str(suggestion).strip()
            observed_text = str(observed).strip()
            if canonical and observed_text and canonical != observed_text:
                variants[canonical].add(observed_text)
    return variants


def _ascii_variants(text: str, canonical: str) -> Counter[str]:
    canonical_key = _ascii_key(canonical)
    if not canonical_key:
        return Counter()
    counts: Counter[str] = Counter()
    for match in ASCII_ENTITY_RE.finditer(text):
        observed = compact_ws(match.group(1))
        if observed == canonical:
            continue
        if _ascii_key(observed) == canonical_key:
            counts[observed] += 1
    return counts


def _cjk_variants(text: str, canonical: str) -> Counter[str]:
    key = _cjk_key(canonical)
    max_distance = _near_miss_distance(key)
    if not max_distance:
        return Counter()
    counts: Counter[str] = Counter()
    lengths = range(max(2, len(key) - 1), len(key) + 2)
    for run_match in CJK_RUN_RE.finditer(text):
        run = run_match.group(0)
        for size in lengths:
            if len(run) < size:
                continue
            for start in range(0, len(run) - size + 1):
                observed = run[start : start + size]
                if observed == key or observed in key or key in observed:
                    continue
                if observed[0] != key[0] and observed[-1] != key[-1]:
                    continue
                if _edit_distance(observed, key, max_distance=max_distance) <= max_distance:
                    counts[observed] += 1
    return counts


def build_entity_consistency_report(
    segments: list[dict[str, Any]],
    glossary: dict[str, Any] | None,
) -> dict[str, Any]:
    full_text = "\n".join(compact_ws(str(segment.get("text", ""))) for segment in segments)
    review_only = _review_only_variants(glossary)
    entities: list[dict[str, Any]] = []
    for category in ENTITY_KEYS:
        values = (glossary or {}).get(category, [])
        if not isinstance(values, list):
            continue
        for raw in values:
            canonical = str(raw).strip()
            if not canonical:
                continue
            variant_counts: Counter[str] = Counter()
            variant_sources: dict[str, set[str]] = defaultdict(set)
            for observed in review_only.get(canonical, set()):
                count = full_text.count(observed)
                if count:
                    variant_counts[observed] += count
                    variant_sources[observed].add("review_only")
            for observed, count in _ascii_variants(full_text, canonical).items():
                variant_counts[observed] += count
                variant_sources[observed].add("ascii_normalized")
            for observed, count in _cjk_variants(full_text, canonical).items():
                variant_counts[observed] += count
                variant_sources[observed].add("cjk_near_miss")
            variants = [
                {
                    "text": observed,
                    "count": count,
                    "sources": sorted(variant_sources[observed]),
                    "timestamps": _segment_times(segments, observed),
                }
                for observed, count in variant_counts.most_common(8)
                if observed != canonical and count > 0
            ]
            if not variants:
                continue
            canonical_count = full_text.count(canonical)
            entities.append(
                {
                    "canonical": canonical,
                    "category": category,
                    "canonical_count": canonical_count,
                    "variants": variants,
                    "recommendation": "review_only",
                    "confidence": "medium" if canonical_count else "low",
                }
            )
    return {
        "schema_version": 1,
        "summary": {
            "entity_count": len(entities),
            "variant_count": sum(len(entity["variants"]) for entity in entities),
        },
        "entities": entities,
    }
