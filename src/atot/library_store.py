from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import path_context
from .safe_paths import confined_path, validate_identifier
from .podcasts import (
    CHINA_TZ,
    PodcastEpisode,
    audio_filename,
    episode_metadata,
    episode_topic_markdown,
)
from .utils import ensure_dir, read_json, read_text, write_json_atomic, write_text_atomic

LIBRARY_DIR_NAME = "Audio2TextLibrary"
LIBRARY_SCHEMA_VERSION = 1
EPISODE_ID_HEX_LENGTH = 24
PRODUCT_STATUS_AVAILABLE = "available"
PRODUCT_STATUS_METADATA_ONLY = "metadata_only"
DEFAULT_GROUP_NAME = "Default"

LIBRARY_KIND_MANIFEST = "audio2text.library.manifest"
LIBRARY_KIND_EPISODE = "audio2text.library.episode"
LIBRARY_KIND_SUBSCRIPTION = "audio2text.library.subscription"
LIBRARY_KIND_GROUP = "audio2text.library.group"
LIBRARY_KIND_TOMBSTONE = "audio2text.library.episode_tombstone"

DEFAULT_ICLOUD_LIBRARY_ROOT = Path(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary"
)

EPISODE_PUBLIC_KEYS = {
    "episode_id",
    "source",
    "source_url",
    "canonical_url",
    "title",
    "original_title",
    "title_updated_at",
    "processed_at",
    "summary_updated_at",
    "summary_generator",
    "series_name",
    "series_url",
    "published_at",
    "local_published_at",
    "date_folder",
    "duration",
    "description",
    "image_url",
    "audio_url",
    "media_filename",
    "guid",
    "subscription_id",
    "app_group",
    "app_status",
    "app_status_updated_at",
    "app_queue_status",
    "app_read",
    "app_star",
    "product_status",
    "documents",
}

SUBSCRIPTION_PUBLIC_KEYS = {
    "id",
    "title",
    "source",
    "url",
    "feed_url",
    "group_name",
    "created_at",
    "last_checked_at",
}


@dataclass(frozen=True)
class LibraryLocation:
    storage: str
    root: Path


def stable_episode_id(fields: dict[str, Any]) -> str:
    source = _clean(fields.get("source"))
    subscription_id = _clean(fields.get("subscription_id"))
    identity_key = ""
    identity_value = ""
    for key in ("guid", "audio_url", "canonical_url"):
        value = _clean(fields.get(key))
        if value:
            identity_key = key
            identity_value = value
            break
    if not identity_value:
        identity_key = "source_url"
        identity_value = _clean(fields.get("source_url")) or _clean(fields.get("title"))
    material = "\n".join((source, subscription_id, identity_key, identity_value))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:EPISODE_ID_HEX_LENGTH]


def default_icloud_library_root() -> Path:
    return DEFAULT_ICLOUD_LIBRARY_ROOT.expanduser()


def default_local_library_root(data_root: Path | None = None) -> Path:
    return path_context(data_root).data_root / LIBRARY_DIR_NAME


def normalize_library_root(root: Path | str) -> Path:
    path = Path(root).expanduser()
    return path if path.name == LIBRARY_DIR_NAME else path / LIBRARY_DIR_NAME


def resolve_library_location(
    *,
    storage: str,
    icloud_root: str = "",
    local_root: str = "",
    data_root: Path | None = None,
) -> LibraryLocation:
    normalized_storage = (storage or "icloud").strip().lower()
    if normalized_storage not in {"icloud", "local"}:
        raise ValueError("library.storage must be 'icloud' or 'local'.")
    if normalized_storage == "icloud":
        root = (
            normalize_library_root(icloud_root)
            if _clean(icloud_root)
            else default_icloud_library_root()
        )
        if not root.parent.is_dir():
            raise RuntimeError(
                "Default iCloud Drive library folder is unavailable. "
                "Enable iCloud Drive or set library.storage='local'."
            )
        return LibraryLocation(storage="icloud", root=root)
    root = (
        normalize_library_root(local_root)
        if _clean(local_root)
        else default_local_library_root(data_root)
    )
    return LibraryLocation(storage="local", root=root)


class LibraryStore:
    def __init__(self, root: Path | str, *, data_root: Path | None = None) -> None:
        self.root = normalize_library_root(root)
        self.data_root = path_context(data_root).data_root

    def _path(self, *parts: str) -> Path:
        return confined_path(self.root.joinpath(*parts), self.root)

    def episode_dir(self, episode_id: str) -> Path:
        return self._path("episodes", validate_identifier(episode_id))

    def _subscription_path(self, subscription_id: str) -> Path:
        return self._path("subscriptions", f"{validate_identifier(subscription_id)}.json")

    @property
    def episodes_root(self) -> Path:
        return self._path("episodes")

    @property
    def subscriptions_root(self) -> Path:
        return self._path("subscriptions")

    @property
    def episode_tombstones_root(self) -> Path:
        return self._path("tombstones", "episodes")

    @property
    def groups_root(self) -> Path:
        return self._path("groups")

    def ensure(self) -> None:
        ensure_dir(self.episodes_root)
        ensure_dir(self.subscriptions_root)
        ensure_dir(self.groups_root)
        ensure_dir(self.episode_tombstones_root)

    def status(self) -> dict[str, Any]:
        episodes = self.load_episodes()
        subscriptions = self.load_subscriptions()
        tombstones = self.load_episode_tombstones()
        return {
            "success": True,
            "library_root": str(self.root),
            "exists": self.root.is_dir(),
            "manifest_exists": (self._path("manifest.json")).is_file(),
            "episode_count": len(episodes),
            "subscription_count": len(subscriptions),
            "tombstone_count": len(tombstones),
            "group_count": len(self.load_groups()),
        }

    def load_subscriptions(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self.subscriptions_root.glob("*.json")):
            self._path(*path.relative_to(self.root).parts)
            record = _read_json_object(path)
            if not _is_subscription_record(record):
                continue
            subscription = _public_subscription_record(record)
            validate_identifier(_clean(subscription.get("id")))
            if path.stem != subscription["id"]:
                raise ValueError("Subscription identity does not match its storage file.")
            if _clean(subscription.get("id")):
                records.append(subscription)
        return sorted(records, key=lambda item: str(item.get("title") or item.get("id") or ""))

    def load_episodes(
        self, *, include_deleted: bool = False, read_documents: bool = True
    ) -> list[dict[str, Any]]:
        tombstoned = set(self.load_episode_tombstones()) if not include_deleted else set()
        records = []
        for path in sorted(self.episodes_root.glob("*/episode.json")):
            self._path(*path.relative_to(self.root).parts)
            record = _read_json_object(path)
            if not _is_episode_record(record):
                continue
            public = _public_episode_record(record)
            episode_id = _clean(record.get("episode_id")) or stable_episode_id(public)
            validate_identifier(episode_id)
            if path.parent.name != episode_id:
                raise ValueError("Episode identity does not match its storage directory.")
            if not episode_id or episode_id in tombstoned:
                continue
            public["episode_id"] = episode_id
            public["documents"] = (
                _document_records(self.episode_dir(episode_id) / "documents")
                if read_documents
                else record.get("documents", [])
            )
            public["product_status"] = (
                PRODUCT_STATUS_AVAILABLE
                if public["documents"]
                else _clean(public.get("product_status")) or PRODUCT_STATUS_METADATA_ONLY
            )
            records.append(public)
        return sorted(records, key=_episode_sort_key)

    def load_episode(self, episode_id: str) -> dict[str, Any] | None:
        record = _read_json_object(self.episode_dir(episode_id) / "episode.json")
        if not _is_episode_record(record):
            return None
        public = _public_episode_record(record)
        public["episode_id"] = episode_id
        public["documents"] = _document_records(self.episode_dir(episode_id) / "documents")
        public["product_status"] = (
            PRODUCT_STATUS_AVAILABLE
            if public["documents"]
            else _clean(public.get("product_status")) or PRODUCT_STATUS_METADATA_ONLY
        )
        return public

    def load_episode_tombstones(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for path in sorted(self.episode_tombstones_root.glob("*.json")):
            self._path(*path.relative_to(self.root).parts)
            record = _read_json_object(path)
            episode_id = _clean(record.get("episode_id")) or path.stem
            validate_identifier(episode_id)
            if path.stem != episode_id:
                raise ValueError("Tombstone identity does not match its storage file.")
            if episode_id:
                records[episode_id] = record
        return records

    def load_groups(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self.groups_root.glob("*.json")):
            self._path(*path.relative_to(self.root).parts)
            record = _read_json_object(path)
            if _clean(record.get("kind")) not in {"", LIBRARY_KIND_GROUP}:
                continue
            group_id = _clean(record.get("id"))
            title = _clean(record.get("title")) or group_id
            if group_id:
                records.append({"id": group_id, "title": title})
        return sorted(records, key=lambda item: str(item.get("title") or item.get("id") or ""))

    def upsert_group(self, group_name: str) -> dict[str, Any]:
        self.ensure()
        title = _normalized_group_name(group_name)
        if title == DEFAULT_GROUP_NAME:
            return {"id": DEFAULT_GROUP_NAME, "title": DEFAULT_GROUP_NAME}
        path = self._existing_group_path(title) or self._path("groups", _group_record_filename(title))
        existing = _read_json_object(path)
        record = {
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_GROUP,
            "id": title,
            "title": title,
            "created_at": _clean(existing.get("created_at")) or _now_iso(),
            "updated_at": _now_iso(),
        }
        write_json_atomic(path, record)
        return record

    def _existing_group_path(self, group_name: str) -> Path | None:
        normalized = _normalized_group_name(group_name)
        for path in sorted(self.groups_root.glob("*.json")):
            self._path(*path.relative_to(self.root).parts)
            record = _read_json_object(path)
            if (
                _clean(record.get("id")) == normalized
                or _normalized_group_name(record.get("title")) == normalized
            ):
                return path
        return None

    def upsert_subscription(self, record: dict[str, Any]) -> dict[str, Any]:
        self.ensure()
        public = _public_subscription_record(record)
        subscription_id = _clean(public.get("id"))
        if not subscription_id:
            raise ValueError("Subscription record is missing id.")
        existing = _read_json_object(self._subscription_path(subscription_id))
        merged = {
            **_public_subscription_record(existing),
            **public,
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_SUBSCRIPTION,
        }
        write_json_atomic(self._subscription_path(subscription_id), merged)
        self.upsert_group(_clean(merged.get("group_name")))
        self.rebuild_manifest()
        return merged

    def upsert_episode(self, record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        self.ensure()
        public = _public_episode_record(record)
        episode_id = _clean(public.get("episode_id")) or stable_episode_id(public)
        if not episode_id:
            raise ValueError("Episode record is missing a stable identity.")
        if self.is_episode_tombstoned(episode_id, public):
            skipped = dict(public)
            skipped["episode_id"] = episode_id
            skipped["skipped"] = True
            skipped["skip_reason"] = "library_tombstone_deleted"
            return skipped, False
        episode_dir = ensure_dir(self.episode_dir(episode_id))
        path = episode_dir / "episode.json"
        existing = _read_json_object(path)
        was_new = not path.exists()
        documents = _document_records(episode_dir / "documents")
        merged = {
            **_public_episode_record(existing),
            **public,
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_EPISODE,
            "episode_id": episode_id,
            "documents": documents,
            "product_status": PRODUCT_STATUS_AVAILABLE
            if documents
            else PRODUCT_STATUS_METADATA_ONLY,
        }
        if _clean(existing.get("title_updated_at")) and not _clean(public.get("title_updated_at")):
            merged["title"] = existing.get("title")
            merged["title_updated_at"] = existing.get("title_updated_at")
        write_json_atomic(path, merged)
        self.upsert_group(_clean(merged.get("app_group")))
        self.rebuild_manifest()
        return merged, was_new

    def upsert_episode_from_podcast(
        self,
        episode: PodcastEpisode,
        *,
        subscription_id: str = "",
        app_group_name: str = "Default",
    ) -> tuple[dict[str, Any], bool]:
        tagged = PodcastEpisode(
            source_url=episode.source_url,
            canonical_url=episode.canonical_url,
            title=episode.title,
            series_name=episode.series_name,
            series_url=episode.series_url,
            published_at=episode.published_at,
            duration=episode.duration,
            description=episode.description,
            audio_url=episode.audio_url,
            image_url=episode.image_url,
            source=episode.source,
            guid=episode.guid,
            subscription_id=subscription_id or episode.subscription_id,
        )
        record = episode_metadata(
            tagged,
            audio_path=Path(audio_filename(tagged, None)),
            topic_path=Path("主题.md"),
            app_group_name=app_group_name,
        )
        record.pop("audio_path", None)
        record.pop("topic_path", None)
        return self.upsert_episode(record)

    def write_episode_documents(
        self, episode_id: str, *, summary: str, transcript: str
    ) -> list[dict[str, Any]]:
        self.ensure()
        episode_dir = ensure_dir(self.episode_dir(episode_id))
        documents_dir = ensure_dir(confined_path(episode_dir / "documents", self.root))
        for name in ("summary.md", "transcript.md"):
            confined_path(documents_dir / name, self.root)
        for child in documents_dir.iterdir():
            confined_path(child, self.root)
        _prune_documents(documents_dir)
        write_text_atomic(confined_path(documents_dir / "summary.md", self.root), summary)
        write_text_atomic(documents_dir / "transcript.md", transcript)
        documents = _document_records(documents_dir)
        record = _read_json_object(episode_dir / "episode.json")
        if _is_episode_record(record):
            processed_at = _now_iso()
            record = {
                **_public_episode_record(record),
                "schema_version": LIBRARY_SCHEMA_VERSION,
                "kind": LIBRARY_KIND_EPISODE,
                "episode_id": episode_id,
                "processed_at": processed_at,
                "documents": documents,
                "product_status": PRODUCT_STATUS_AVAILABLE,
            }
            write_json_atomic(episode_dir / "episode.json", record)
        self.rebuild_manifest()
        return documents

    def write_episode_summary(
        self, episode_id: str, *, summary: str, generator: str
    ) -> list[dict[str, Any]]:
        """Update only the summary and index, preserving transcript bytes and user flags."""
        episode_dir = self.episode_dir(episode_id)
        record = read_json(confined_path(episode_dir / "episode.json", self.root))
        if not isinstance(record, dict) or not _is_episode_record(record):
            raise ValueError(f"Invalid episode record: {episode_id}")
        documents_dir = confined_path(episode_dir / "documents", self.root)
        write_text_atomic(confined_path(documents_dir / "summary.md", self.root), summary)
        documents = _document_records(documents_dir)
        record = {
            **_public_episode_record(record),
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_EPISODE,
            "episode_id": episode_id,
            "summary_updated_at": _now_iso(),
            "summary_generator": generator,
            "documents": documents,
            "product_status": PRODUCT_STATUS_AVAILABLE,
        }
        write_json_atomic(episode_dir / "episode.json", record)
        self.rebuild_manifest()
        return documents

    def delete_episode(self, episode_id: str, *, clean_local: bool = True) -> dict[str, Any]:
        self.ensure()
        validate_identifier(episode_id)
        tombstone_path = self._path("tombstones", "episodes", f"{episode_id}.json")
        if clean_local:
            self.local_material_dir(episode_id)
            self.local_work_dir(episode_id)
        record = self.load_episode(episode_id) or {}
        episode_dir = self.episode_dir(episode_id)
        if episode_dir.exists():
            shutil.rmtree(episode_dir)
        tombstone = {
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_TOMBSTONE,
            "episode_id": episode_id,
            "deleted_at": _now_iso(),
        }
        for key in (
            "source",
            "source_url",
            "canonical_url",
            "audio_url",
            "guid",
            "subscription_id",
            "title",
        ):
            if _clean(record.get(key)):
                tombstone[key] = record[key]
        write_json_atomic(tombstone_path, tombstone)
        if clean_local:
            self.delete_local_episode_files(episode_id)
        self.rebuild_manifest()
        return {"deleted": episode_id, "tombstone": tombstone}

    def delete_subscription(self, subscription_id: str) -> dict[str, Any]:
        path = self._subscription_path(subscription_id)
        if not path.is_file():
            raise ValueError(f"Unknown subscription id: {subscription_id}")
        episodes = self.load_episodes(include_deleted=True)
        for episode in episodes:
            self.episode_dir(_clean(episode.get("episode_id")))
        path.unlink()
        removed_metadata_only = 0
        preserved_available = 0
        for episode in episodes:
            if _clean(episode.get("subscription_id")) != subscription_id:
                continue
            episode_id = _clean(episode.get("episode_id"))
            if not episode_id:
                continue
            if episode.get("documents"):
                preserved_available += 1
                continue
            episode_dir = self.episode_dir(episode_id)
            if episode_dir.exists():
                shutil.rmtree(episode_dir)
                removed_metadata_only += 1
        self.rebuild_manifest()
        return {
            "removed": subscription_id,
            "removed_metadata_only_episode_count": removed_metadata_only,
            "preserved_available_episode_count": preserved_available,
            "subscriptions": self.load_subscriptions(),
        }

    def is_episode_tombstoned(self, episode_id: str, record: dict[str, Any] | None = None) -> bool:
        validate_identifier(episode_id)
        tombstones = self.load_episode_tombstones()
        if episode_id in tombstones:
            return True
        if record is None:
            return False
        for tombstone in tombstones.values():
            if _records_match_identity(tombstone, record):
                return True
        return False

    def local_material_dir(self, episode_id: str) -> Path:
        return confined_path(path_context(self.data_root).materials_dir / validate_identifier(episode_id), self.data_root)

    def local_work_dir(self, episode_id: str) -> Path:
        return confined_path(path_context(self.data_root).work_dir / validate_identifier(episode_id), self.data_root)

    def local_audio_path(self, episode: dict[str, Any]) -> Path:
        episode_id = _clean(episode.get("episode_id"))
        title = _clean(episode.get("title")) or episode_id
        suffix = Path(_clean(episode.get("audio_url"))).suffix or ".m4a"
        return confined_path(self.local_material_dir(episode_id) / f"{_safe_filename(title)}{suffix}", self.data_root)

    def materialize_local_metadata(self, episode_id: str) -> dict[str, Any]:
        episode = self.load_episode(episode_id)
        if episode is None:
            raise ValueError(f"Unknown episode id: {episode_id}")
        material_dir = ensure_dir(self.local_material_dir(episode_id))
        audio_path = self.local_audio_path(episode)
        topic_path = confined_path(material_dir / "主题.md", self.data_root)
        metadata_path = confined_path(material_dir / "episode.json", self.data_root)
        write_text_atomic(topic_path, episode_topic_markdown(_podcast_episode_from_record(episode)))
        metadata = dict(episode)
        metadata["audio_path"] = str(audio_path)
        metadata["topic_path"] = str(topic_path)
        write_json_atomic(metadata_path, metadata)
        return {
            "material_dir": str(material_dir),
            "audio_path": str(audio_path),
            "metadata_path": str(material_dir / "episode.json"),
        }

    def delete_local_episode_files(self, episode_id: str) -> None:
        for path in (self.local_material_dir(episode_id), self.local_work_dir(episode_id)):
            if path.exists():
                shutil.rmtree(path)

    def rebuild_manifest(self) -> dict[str, Any]:
        self.ensure()
        episodes = [
            {
                "episode_id": episode["episode_id"],
                "path": f"episodes/{episode['episode_id']}/episode.json",
            }
            for episode in self.load_episodes(include_deleted=True, read_documents=False)
            if _clean(episode.get("episode_id"))
        ]
        subscriptions = [
            {"id": subscription["id"], "path": f"subscriptions/{subscription['id']}.json"}
            for subscription in self.load_subscriptions()
            if _clean(subscription.get("id"))
        ]
        tombstones = [
            {"episode_id": episode_id, "path": f"tombstones/episodes/{episode_id}.json"}
            for episode_id in sorted(self.load_episode_tombstones())
        ]
        manifest = {
            "schema_version": LIBRARY_SCHEMA_VERSION,
            "kind": LIBRARY_KIND_MANIFEST,
            "updated_at": _now_iso(),
            "episode_count": len(episodes),
            "subscription_count": len(subscriptions),
            "tombstone_count": len(tombstones),
            "episodes": episodes,
            "subscriptions": subscriptions,
            "tombstones": tombstones,
        }
        write_json_atomic(self._path("manifest.json"), manifest)
        return manifest


def library_episode_record_from_local_file(
    path: Path, *, title: str | None = None
) -> dict[str, Any]:
    name = title or path.stem
    record: dict[str, Any] = {
        "source": "local",
        "source_url": path.name,
        "canonical_url": path.name,
        "title": name,
        "series_name": "Local Files",
        "series_url": "",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "local_published_at": datetime.now(CHINA_TZ).isoformat(),
        "duration": "",
        "description": "",
        "audio_url": "",
        "app_group": "Default",
        "app_status": "import",
        "app_queue_status": "unread",
        "app_read": False,
        "app_star": False,
    }
    record["episode_id"] = stable_episode_id(record)
    return record


def publish_work_documents_to_library(
    *,
    store: LibraryStore,
    episode_id: str,
    work_dir: Path,
) -> dict[str, Any]:
    transcript = _first_text(
        [
            work_dir / "transcript.readable.md",
            work_dir / "transcript.timestamped.md",
            work_dir / "transcript.corrected.txt",
            work_dir / "transcript.md",
        ]
    )
    summary = _first_text(
        [
            work_dir / "summary.md",
            work_dir / "cloud" / "summary.md",
            work_dir / "cloud" / "outputs" / "summary.md",
        ]
    )
    documents = store.write_episode_documents(episode_id, summary=summary, transcript=transcript)
    return {
        "library_root": str(store.root),
        "episode_id": episode_id,
        "documents_dir": str(store.episodes_root / episode_id / "documents"),
        "documents": documents,
    }


def _is_episode_record(record: dict[str, Any]) -> bool:
    kind = _clean(record.get("kind"))
    return bool(record.get("title")) and kind in {
        "",
        LIBRARY_KIND_EPISODE,
        "audio2text.mobile_sync.episode",
        "audio2text.product.intro",
    }


def _is_subscription_record(record: dict[str, Any]) -> bool:
    kind = _clean(record.get("kind"))
    return bool(record.get("id")) and kind in {
        "",
        LIBRARY_KIND_SUBSCRIPTION,
        "audio2text.mobile_sync.subscription",
    }


def _public_episode_record(metadata: dict[str, Any]) -> dict[str, Any]:
    record = {
        key: metadata[key]
        for key in sorted(EPISODE_PUBLIC_KEYS)
        if key in metadata and _json_public_value(metadata[key])
    }
    record.setdefault("source", "podcast_rss")
    if not _clean(record.get("episode_id")):
        record["episode_id"] = stable_episode_id(record)
    return record


def _public_subscription_record(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: metadata[key]
        for key in sorted(SUBSCRIPTION_PUBLIC_KEYS)
        if key in metadata and _json_scalar(metadata[key])
    }


def _document_records(documents_dir: Path) -> list[dict[str, Any]]:
    confined_path(documents_dir, documents_dir.parent)
    rows: list[dict[str, Any]] = []
    for name in ("summary.md", "transcript.md"):
        path = confined_path(documents_dir / name, documents_dir)
        if not path.is_file():
            continue
        data = path.read_bytes()
        rows.append(
            {
                "name": name,
                "path": f"documents/{name}",
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return rows


def _prune_documents(documents_dir: Path) -> None:
    keep = {"summary.md", "transcript.md"}
    for path in documents_dir.iterdir():
        if path.name in keep and path.is_file():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def _records_match_identity(lhs: dict[str, Any], rhs: dict[str, Any]) -> bool:
    for key in ("episode_id", "audio_url", "guid", "canonical_url", "source_url"):
        left = _clean(lhs.get(key))
        right = _clean(rhs.get(key))
        if left and right and left == right:
            return True
    return False


def _podcast_episode_from_record(record: dict[str, Any]) -> PodcastEpisode:
    published_at = _parse_datetime(
        _clean(record.get("published_at")) or _clean(record.get("local_published_at"))
    )
    return PodcastEpisode(
        source_url=_clean(record.get("source_url")) or _clean(record.get("canonical_url")),
        canonical_url=_clean(record.get("canonical_url")) or _clean(record.get("source_url")),
        title=_clean(record.get("title")),
        series_name=_clean(record.get("series_name")),
        series_url=_clean(record.get("series_url")),
        published_at=published_at,
        duration=_clean(record.get("duration")),
        description=_clean(record.get("description")),
        audio_url=_clean(record.get("audio_url")),
        image_url=_clean(record.get("image_url")) or None,
        source=_clean(record.get("source")) or "podcast_rss",
        guid=_clean(record.get("guid")),
        subscription_id=_clean(record.get("subscription_id")),
    )


def _parse_datetime(text: str) -> datetime:
    if not text:
        return datetime.now(CHINA_TZ)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(CHINA_TZ)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _episode_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    published = _clean(item.get("published_at")) or _clean(item.get("local_published_at"))
    return (published, _clean(item.get("title")))


def _read_json_object(path: Path) -> dict[str, Any]:
    confined_path(path, path.parent)
    if not path.is_file():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_filename(value: str) -> str:
    from .utils import slugify

    return slugify(value, max_len=120) or "audio"


def _normalized_group_name(value: Any) -> str:
    text = _clean(value)
    return text or DEFAULT_GROUP_NAME


def _group_record_filename(group_name: str) -> str:
    return f"{_group_record_stem(group_name)}.json"


def _group_record_stem(group_name: str) -> str:
    normalized = _normalized_group_name(group_name)
    stem = "".join(
        char if char.isalnum() or _is_cjk(char) or char in {"-", "_"} else "-"
        for char in normalized
    )
    collapsed = re.sub("-+", "-", stem).strip("-. ")
    if collapsed and len(collapsed) <= 80:
        return collapsed
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    if collapsed:
        return f"{collapsed[:67]}-{digest}"
    return f"group-{digest}"


def _is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return 0x3400 <= codepoint <= 0x4DBF or 0x4E00 <= codepoint <= 0x9FFF


def _json_scalar(value: Any) -> bool:
    return isinstance(value, str | int | float | bool) or value is None


def _json_public_value(value: Any) -> bool:
    if _json_scalar(value):
        return not _looks_private_path(value)
    if isinstance(value, list):
        return True
    return False


def _looks_private_path(value: Any) -> bool:
    text = str(value or "")
    slash = "/"
    private_markers = (
        f"{slash}Users{slash}",
        f"{slash}SpeechToTextData{slash}",
        f"{slash}Library{slash}",
    )
    return any(marker in text for marker in private_markers)


def _first_text(paths: list[Path]) -> str:
    for path in paths:
        text = read_text(path)
        if text:
            return text
    return ""


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat()
