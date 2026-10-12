from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .library_store import (
    EPISODE_PUBLIC_KEYS,
    LIBRARY_KIND_EPISODE,
    LIBRARY_KIND_GROUP,
    LIBRARY_KIND_MANIFEST,
    LIBRARY_KIND_SUBSCRIPTION,
    LIBRARY_KIND_TOMBSTONE,
    LIBRARY_SCHEMA_VERSION,
    SUBSCRIPTION_PUBLIC_KEYS,
    normalize_library_root,
)
from .utils import read_json

ALLOWED_DOCUMENT_NAMES = {"summary.md", "transcript.md"}
DOCUMENT_KEYS = {"name", "path", "bytes", "sha256"}
COMMON_RECORD_KEYS = {"schema_version", "kind"}
EPISODE_RECORD_KEYS = COMMON_RECORD_KEYS | EPISODE_PUBLIC_KEYS
SUBSCRIPTION_RECORD_KEYS = COMMON_RECORD_KEYS | SUBSCRIPTION_PUBLIC_KEYS
GROUP_RECORD_KEYS = COMMON_RECORD_KEYS | {"id", "title", "created_at", "updated_at"}
TOMBSTONE_RECORD_KEYS = {
    "schema_version",
    "kind",
    "episode_id",
    "deleted_at",
    "source",
    "source_url",
    "canonical_url",
    "audio_url",
    "guid",
    "subscription_id",
    "title",
}
MANIFEST_KEYS = {
    "schema_version",
    "kind",
    "updated_at",
    "episode_count",
    "subscription_count",
    "tombstone_count",
    "episodes",
    "subscriptions",
    "tombstones",
}
MANIFEST_EPISODE_KEYS = {"episode_id", "path"}
MANIFEST_SUBSCRIPTION_KEYS = {"id", "path"}
MANIFEST_TOMBSTONE_KEYS = {"episode_id", "path"}
LOCAL_PATH_RE = re.compile(
    r"(^|\s)(~/|file://|[A-Za-z]:[\\/]|/(Users|Volumes|tmp|private|var|opt|home|Library/Mobile Documents|SpeechToTextData)(/|$))"
)


def validate_library(root: str | Path) -> list[str]:
    library_root = normalize_library_root(root)
    errors: list[str] = []
    if not library_root.is_dir():
        return [f"{library_root}: library root does not exist"]

    for required in (
        library_root / "episodes",
        library_root / "subscriptions",
        library_root / "tombstones" / "episodes",
    ):
        if not required.is_dir():
            errors.append(f"{_rel(library_root, required)}: required directory is missing")

    manifest = _read_object(library_root / "manifest.json", errors, library_root)
    if manifest is not None:
        _validate_manifest_shape(library_root, manifest, errors)

    tombstone_entries = _validate_tombstones(library_root, errors)
    episode_entries = _validate_episodes(library_root, set(tombstone_entries), errors)
    subscription_entries = _validate_subscriptions(library_root, errors)
    _validate_groups(library_root, errors)

    if manifest is not None:
        _validate_manifest_consistency(
            library_root,
            manifest,
            "episodes",
            "episode_count",
            episode_entries,
            errors,
        )
        _validate_manifest_consistency(
            library_root,
            manifest,
            "subscriptions",
            "subscription_count",
            subscription_entries,
            errors,
        )
        _validate_manifest_consistency(
            library_root,
            manifest,
            "tombstones",
            "tombstone_count",
            tombstone_entries,
            errors,
        )

    return errors


def _validate_manifest_shape(root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    rel = "manifest.json"
    _validate_schema(
        manifest,
        rel,
        kind=LIBRARY_KIND_MANIFEST,
        required=("schema_version", "kind"),
        errors=errors,
    )
    _validate_allowed_keys(manifest, MANIFEST_KEYS, rel, errors)
    _validate_no_private_paths(manifest, rel, errors)
    for key in ("episode_count", "subscription_count", "tombstone_count"):
        if not isinstance(manifest.get(key), int):
            errors.append(f"{rel}: {key} must be an integer")
    _manifest_entries(root, manifest, "episodes", MANIFEST_EPISODE_KEYS, errors)
    _manifest_entries(root, manifest, "subscriptions", MANIFEST_SUBSCRIPTION_KEYS, errors)
    _manifest_entries(root, manifest, "tombstones", MANIFEST_TOMBSTONE_KEYS, errors)


def _validate_episodes(
    root: Path, tombstones: set[tuple[str, str]], errors: list[str]
) -> set[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    episodes_root = root / "episodes"
    if not episodes_root.is_dir():
        return entries
    tombstone_ids = {episode_id for episode_id, _path in tombstones}
    for episode_dir in sorted(path for path in episodes_root.iterdir() if path.is_dir()):
        episode_id = episode_dir.name
        episode_path = episode_dir / "episode.json"
        rel = _rel(root, episode_path)
        if not episode_path.is_file():
            errors.append(f"{_rel(root, episode_dir)}: episode.json is missing")
            continue
        if episode_id in tombstone_ids:
            errors.append(f"{rel}: tombstoned episode must not have a public episode record")
        record = _read_object(episode_path, errors, root)
        if record is None:
            continue
        _validate_schema(
            record,
            rel,
            kind=LIBRARY_KIND_EPISODE,
            required=("schema_version", "kind", "episode_id", "title", "documents"),
            errors=errors,
        )
        _validate_allowed_keys(record, EPISODE_RECORD_KEYS, rel, errors)
        _validate_no_private_paths(record, rel, errors)
        if record.get("episode_id") != episode_id:
            errors.append(f"{rel}: episode_id must match containing directory")
        _validate_documents(root, episode_id, record, errors)
        entries.add((episode_id, f"episodes/{episode_id}/episode.json"))
    return entries


def _validate_subscriptions(root: Path, errors: list[str]) -> set[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    subscriptions_root = root / "subscriptions"
    if not subscriptions_root.is_dir():
        return entries
    for path in sorted(subscriptions_root.glob("*.json")):
        subscription_id = path.stem
        rel = _rel(root, path)
        record = _read_object(path, errors, root)
        if record is None:
            continue
        _validate_schema(
            record,
            rel,
            kind=LIBRARY_KIND_SUBSCRIPTION,
            required=("schema_version", "kind", "id", "title"),
            errors=errors,
        )
        _validate_allowed_keys(record, SUBSCRIPTION_RECORD_KEYS, rel, errors)
        _validate_no_private_paths(record, rel, errors)
        if record.get("id") != subscription_id:
            errors.append(f"{rel}: id must match filename stem")
        entries.add((subscription_id, f"subscriptions/{subscription_id}.json"))
    return entries


def _validate_groups(root: Path, errors: list[str]) -> None:
    groups_root = root / "groups"
    if not groups_root.exists():
        return
    if not groups_root.is_dir():
        errors.append(f"{_rel(root, groups_root)}: groups path must be a directory")
        return
    seen: set[str] = set()
    for path in sorted(groups_root.glob("*.json")):
        rel = _rel(root, path)
        record = _read_object(path, errors, root)
        if record is None:
            continue
        _validate_schema(
            record,
            rel,
            kind=LIBRARY_KIND_GROUP,
            required=("schema_version", "kind", "id", "title"),
            errors=errors,
        )
        _validate_allowed_keys(record, GROUP_RECORD_KEYS, rel, errors)
        _validate_no_private_paths(record, rel, errors)
        group_id = record.get("id")
        if not isinstance(group_id, str) or not group_id.strip():
            errors.append(f"{rel}: id must be a non-empty string")
            continue
        if group_id in seen:
            errors.append(f"{rel}: duplicate group id {group_id!r}")
        seen.add(group_id)


def _validate_tombstones(root: Path, errors: list[str]) -> set[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    tombstones_root = root / "tombstones" / "episodes"
    if not tombstones_root.is_dir():
        return entries
    for path in sorted(tombstones_root.glob("*.json")):
        episode_id = path.stem
        rel = _rel(root, path)
        record = _read_object(path, errors, root)
        if record is None:
            continue
        _validate_schema(
            record,
            rel,
            kind=LIBRARY_KIND_TOMBSTONE,
            required=("schema_version", "kind", "episode_id", "deleted_at"),
            errors=errors,
        )
        _validate_allowed_keys(record, TOMBSTONE_RECORD_KEYS, rel, errors)
        _validate_no_private_paths(record, rel, errors)
        if record.get("episode_id") != episode_id:
            errors.append(f"{rel}: episode_id must match filename stem")
        if (root / "episodes" / episode_id).exists():
            errors.append(f"{rel}: tombstone suppresses an episode directory that still exists")
        entries.add((episode_id, f"tombstones/episodes/{episode_id}.json"))
    return entries


def _validate_documents(
    root: Path, episode_id: str, record: dict[str, Any], errors: list[str]
) -> None:
    rel = f"episodes/{episode_id}/episode.json"
    documents = record.get("documents")
    if not isinstance(documents, list):
        errors.append(f"{rel}: documents must be a list")
        return

    documents_dir = root / "episodes" / episode_id / "documents"
    actual_names: set[str] = set()
    if documents_dir.exists():
        if not documents_dir.is_dir():
            errors.append(f"{_rel(root, documents_dir)}: documents path must be a directory")
        else:
            for child in sorted(documents_dir.iterdir()):
                if not child.is_file() or child.name not in ALLOWED_DOCUMENT_NAMES:
                    errors.append(f"{_rel(root, child)}: unexpected Library document")
                    continue
                actual_names.add(child.name)

    recorded_names: set[str] = set()
    for index, document in enumerate(documents):
        context = f"{rel}: documents[{index}]"
        if not isinstance(document, dict):
            errors.append(f"{context} must be an object")
            continue
        _validate_allowed_keys(document, DOCUMENT_KEYS, context, errors)
        _validate_no_private_paths(document, context, errors)
        name = document.get("name")
        path = document.get("path")
        if name not in ALLOWED_DOCUMENT_NAMES:
            errors.append(f"{context}.name must be one of {sorted(ALLOWED_DOCUMENT_NAMES)}")
            continue
        if name in recorded_names:
            errors.append(f"{context}.name duplicates another document record")
        recorded_names.add(str(name))
        expected_path = f"documents/{name}"
        if path != expected_path:
            errors.append(f"{context}.path must be {expected_path}")
        document_path = documents_dir / str(name)
        if not document_path.is_file():
            errors.append(f"{context}: referenced document file is missing")
            continue
        data = document_path.read_bytes()
        if "bytes" in document and document.get("bytes") != len(data):
            errors.append(f"{context}.bytes does not match the file size")
        expected_sha = hashlib.sha256(data).hexdigest()
        if "sha256" in document and document.get("sha256") != expected_sha:
            errors.append(f"{context}.sha256 does not match the file content")

    for name in sorted(actual_names - recorded_names):
        errors.append(
            f"episodes/{episode_id}/documents/{name}: document is missing from episode.json"
        )


def _validate_manifest_consistency(
    root: Path,
    manifest: dict[str, Any],
    key: str,
    count_key: str,
    expected: set[tuple[str, str]],
    errors: list[str],
) -> None:
    entries = _manifest_entries(root, manifest, key, _manifest_entry_keys(key), errors)
    if entries != expected:
        missing = sorted(expected - entries)
        extra = sorted(entries - expected)
        if missing:
            errors.append(f"manifest.json: {key} is missing entries {missing}")
        if extra:
            errors.append(f"manifest.json: {key} has stale entries {extra}")
    if manifest.get(count_key) != len(expected):
        errors.append(f"manifest.json: {count_key} must be {len(expected)}")


def _manifest_entry_keys(key: str) -> set[str]:
    if key == "subscriptions":
        return MANIFEST_SUBSCRIPTION_KEYS
    if key == "tombstones":
        return MANIFEST_TOMBSTONE_KEYS
    return MANIFEST_EPISODE_KEYS


def _manifest_entries(
    root: Path,
    manifest: dict[str, Any],
    key: str,
    allowed_keys: set[str],
    errors: list[str],
) -> set[tuple[str, str]]:
    value = manifest.get(key)
    if not isinstance(value, list):
        errors.append(f"manifest.json: {key} must be a list")
        return set()
    entries: set[tuple[str, str]] = set()
    id_key = "id" if key == "subscriptions" else "episode_id"
    for index, item in enumerate(value):
        context = f"manifest.json: {key}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{context} must be an object")
            continue
        _validate_allowed_keys(item, allowed_keys, context, errors)
        _validate_no_private_paths(item, context, errors)
        identifier = item.get(id_key)
        path = item.get("path")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{context}.{id_key} is required")
            continue
        if not isinstance(path, str) or not path:
            errors.append(f"{context}.path is required")
            continue
        if not _is_safe_relative_path(path):
            errors.append(f"{context}.path must be a relative POSIX path")
            continue
        if not (root / path).is_file():
            errors.append(f"{context}.path does not reference an existing file")
        entries.add((identifier, path))
    return entries


def _validate_schema(
    record: dict[str, Any],
    rel: str,
    *,
    kind: str,
    required: tuple[str, ...],
    errors: list[str],
) -> None:
    for key in required:
        if key not in record:
            errors.append(f"{rel}: {key} is required")
    if record.get("schema_version") != LIBRARY_SCHEMA_VERSION:
        errors.append(f"{rel}: schema_version must be {LIBRARY_SCHEMA_VERSION}")
    if record.get("kind") != kind:
        errors.append(f"{rel}: kind must be {kind}")


def _validate_allowed_keys(
    record: dict[str, Any], allowed: set[str], context: str, errors: list[str]
) -> None:
    extra = sorted(set(record) - allowed)
    if extra:
        errors.append(f"{context}: unexpected keys {extra}")


def _validate_no_private_paths(value: Any, context: str, errors: list[str]) -> None:
    def visit(node: Any, path: str) -> None:
        if isinstance(node, str):
            if _looks_local_path(node):
                errors.append(f"{context}{path}: contains a local absolute path")
            return
        if isinstance(node, dict):
            for key, child in node.items():
                visit(child, f"{path}.{key}")
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]")

    visit(value, "")


def _looks_local_path(text: str) -> bool:
    if not text.strip():
        return False
    normalized = text.replace("\\", "/")
    return bool(LOCAL_PATH_RE.search(normalized))


def _is_safe_relative_path(path: str) -> bool:
    if "\\" in path:
        return False
    pure = PurePosixPath(path)
    return not pure.is_absolute() and "~" not in pure.parts and ".." not in pure.parts


def _read_object(path: Path, errors: list[str], root: Path) -> dict[str, Any] | None:
    rel = _rel(root, path)
    if not path.is_file():
        errors.append(f"{rel}: required file is missing")
        return None
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{rel}: invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{rel}: JSON root must be an object")
        return None
    return payload


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
