from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

from .paths import MODEL_DIR


DEFAULT_MODEL_ALIAS = "large-v3-turbo"


@dataclass(frozen=True)
class ModelSpec:
    alias: str
    repo: str
    note: str = ""


@dataclass(frozen=True)
class ModelFile:
    path: str
    url: str


@dataclass(frozen=True)
class ModelInventoryEntry:
    name: str
    aliases: tuple[str, ...]
    repo: str
    local_dir: str
    note: str
    production: bool
    candidate: bool
    required_files: tuple[ModelFile, ...]


@lru_cache(maxsize=1)
def model_inventory() -> tuple[ModelInventoryEntry, ...]:
    inventory_path = resources.files("atot").joinpath("data/model_inventory.json")
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    entries = []
    for raw in payload["models"]:
        entries.append(
            ModelInventoryEntry(
                name=str(raw["name"]),
                aliases=tuple(str(alias) for alias in raw.get("aliases", [])),
                repo=str(raw["repo"]),
                local_dir=str(raw["local_dir"]),
                note=str(raw.get("note", "")),
                production=bool(raw.get("production", False)),
                candidate=bool(raw.get("candidate", False)),
                required_files=tuple(
                    ModelFile(path=str(item["path"]), url=str(item["url"]))
                    for item in raw.get("required_files", [])
                ),
            )
        )
    return tuple(entries)


def _production_specs() -> tuple[ModelSpec, ...]:
    return tuple(
        ModelSpec(alias=entry.name, repo=entry.repo, note=entry.note)
        for entry in sorted(
            (entry for entry in model_inventory() if entry.production),
            key=lambda item: (item.name != DEFAULT_MODEL_ALIAS, item.name),
        )
    )


def _alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for entry in model_inventory():
        for alias in {entry.name, *entry.aliases}:
            aliases[alias] = entry.repo
    return aliases


def model_entry(name: str) -> ModelInventoryEntry | None:
    for entry in model_inventory():
        if (
            name == entry.name
            or name in entry.aliases
            or name == entry.repo
            or name == entry.local_dir
        ):
            return entry
    return None


def local_model_dir(name: str) -> Path:
    entry = model_entry(name)
    if entry is not None:
        return MODEL_DIR / entry.local_dir
    return MODEL_DIR / short_model_name(name)


def required_local_paths(name: str) -> tuple[Path, ...]:
    entry = model_entry(name)
    if entry is None:
        return ()
    paths: list[Path] = []
    for item in entry.required_files:
        path = Path(item.path)
        if path.parts and path.parts[0] == "model":
            paths.append(MODEL_DIR.joinpath(*path.parts[1:]))
        else:
            paths.append(MODEL_DIR / path)
    return tuple(paths)


def missing_required_local_paths(name: str) -> tuple[Path, ...]:
    return tuple(path for path in required_local_paths(name) if not path.exists())


def required_local_files(name: str) -> tuple[str, ...]:
    entry = model_entry(name)
    if entry is None:
        return ()
    return tuple(item.path for item in entry.required_files)


def model_download_rows(*, include_candidates: bool = True) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in model_inventory():
        if not entry.production and not (include_candidates and entry.candidate):
            continue
        for item in entry.required_files:
            key = (item.path, item.url)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"model": entry.name, "path": item.path, "url": item.url})
    return rows


MODEL_SPECS: tuple[ModelSpec, ...] = _production_specs()

MODEL_ALIASES = {spec.alias: spec.repo for spec in MODEL_SPECS}
LOCAL_MODELS_DIR = MODEL_DIR
DEFAULT_BENCHMARK_MODELS = (
    "small-4bit",
    "large-v3-turbo-q4",
)


def resolve_model(model: str | None) -> str:
    if not model:
        model = DEFAULT_MODEL_ALIAS
    resolved = MODEL_ALIASES.get(model, model)
    entry = model_entry(model) or model_entry(resolved)
    local_candidates = [local_model_dir(model)]
    if entry is None:
        local_candidates.extend(
            [
                LOCAL_MODELS_DIR / resolved.rsplit("/", 1)[-1],
                LOCAL_MODELS_DIR / short_model_name(resolved),
            ]
        )
    for local in local_candidates:
        if (
            local.is_dir()
            and (local / "config.json").exists()
            and (
                (local / "weights.safetensors").exists()
                or (local / "weights.npz").exists()
                or (local / "model.bin").exists()
            )
        ):
            return str(local)
    return resolved


def short_model_name(model: str) -> str:
    repo = _alias_map().get(model, model)
    return repo.rsplit("/", 1)[-1].replace("whisper-", "")


def describe_models() -> list[dict[str, str]]:
    return [{"alias": s.alias, "repo": s.repo, "note": s.note} for s in MODEL_SPECS]


def model_source(model: str) -> str:
    path = Path(model)
    if path.exists():
        return "local"
    return "huggingface"
