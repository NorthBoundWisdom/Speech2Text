from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from importlib import resources
from typing import Any


AUTO_RULE_PACK = "auto"
RULE_PACK_FILES = ("topic_rules.json", "review_rules.json")


def _sha256_payload(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge_rules(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = {**current, **value}
        elif isinstance(current, list) and isinstance(value, list):
            merged[key] = [*current, *[item for item in value if item not in current]]
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=None)
def _load_base_rule_file(name: str) -> dict[str, Any]:
    with resources.files("atot.data").joinpath(name).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Rule file must be a JSON object: {name}")
    return data


@lru_cache(maxsize=None)
def _load_rule_pack_file(pack: str, name: str) -> dict[str, Any]:
    path = resources.files("atot.data").joinpath("rule_packs").joinpath(pack).joinpath(name)
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Rule pack file must be a JSON object: {pack}/{name}")
    return data


def available_rule_packs() -> tuple[str, ...]:
    root = resources.files("atot.data").joinpath("rule_packs")
    packs: list[str] = []
    for item in root.iterdir():
        if item.is_dir() and item.joinpath("pack.json").is_file():
            packs.append(item.name)
    return tuple(sorted(packs))


def normalize_rule_pack_request(packs: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if packs is None:
        return (AUTO_RULE_PACK,)
    available = set(available_rule_packs())
    normalized: list[str] = []
    for raw in packs:
        pack = str(raw).strip()
        if not pack:
            continue
        if pack != AUTO_RULE_PACK and pack not in available:
            raise ValueError(f"Unknown rule pack: {pack}")
        if pack not in normalized:
            normalized.append(pack)
    return tuple(normalized)


def load_rule_file(
    name: str, *, packs: tuple[str, ...] | list[str] | None = None
) -> dict[str, Any]:
    data = dict(_load_base_rule_file(name))
    for pack in tuple(packs or ()):
        data = _merge_rules(data, _load_rule_pack_file(str(pack), name))
    return data


def matching_rule_packs(text: str) -> tuple[str, ...]:
    matches: list[str] = []
    for pack in available_rule_packs():
        index = _load_rule_pack_file(pack, "pack.json")
        triggers = index.get("triggers", []) if isinstance(index, dict) else []
        if isinstance(triggers, list) and any(str(item) and str(item) in text for item in triggers):
            matches.append(pack)
    return tuple(matches)


def selected_rule_packs(
    text: str, packs: tuple[str, ...] | list[str] | None = None
) -> tuple[str, ...]:
    requested = normalize_rule_pack_request(packs)
    selected: list[str] = []
    for pack in requested:
        if pack == AUTO_RULE_PACK:
            for match in matching_rule_packs(text):
                if match not in selected:
                    selected.append(match)
        elif pack not in selected:
            selected.append(pack)
    return tuple(selected)


def load_rule_file_for_text(
    name: str,
    text: str,
    *,
    packs: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    return load_rule_file(name, packs=selected_rule_packs(text, packs))


def rule_set_fingerprint(
    packs: tuple[str, ...] | list[str] | None = None,
    *,
    files: tuple[str, ...] = RULE_PACK_FILES,
) -> dict[str, Any]:
    requested = normalize_rule_pack_request(packs)
    scoped_packs = (
        available_rule_packs()
        if AUTO_RULE_PACK in requested
        else tuple(pack for pack in requested if pack != AUTO_RULE_PACK)
    )
    merged_file_sha256 = {
        name: _sha256_payload(load_rule_file(name, packs=scoped_packs)) for name in files
    }
    return {
        "version": 1,
        "request": list(requested),
        "pack_scope": list(scoped_packs),
        "merged_file_sha256": merged_file_sha256,
    }
