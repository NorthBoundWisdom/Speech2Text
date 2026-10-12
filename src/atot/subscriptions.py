from __future__ import annotations

import hashlib
import calendar
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .feed_discovery import discover_feed
from .http import fetch_bytes
from .library_store import LibraryStore, default_local_library_root, stable_episode_id
from .podcasts import CHINA_TZ, PodcastEpisode
from .runtime_defaults import DEFAULT_NETWORK_TIMEOUT_SECONDS, DEFAULT_SUBSCRIPTION_LIMIT
from .utils import compact_ws, read_json
from .xiaoyuzhou import fetch_podcast

DEFAULT_LIMIT = DEFAULT_SUBSCRIPTION_LIMIT
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup?id={id}&entity=podcast"


def _feedparser() -> Any:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError(
            "Podcast subscription RSS parsing requires feedparser. Install with `pip install -e .`."
        ) from exc
    return feedparser


@dataclass(frozen=True)
class PodcastSubscription:
    id: str
    title: str
    source: str
    url: str
    feed_url: str
    group_name: str
    created_at: str
    last_checked_at: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "feed_url": self.feed_url,
            "group_name": self.group_name,
            "created_at": self.created_at,
            "last_checked_at": self.last_checked_at,
        }


@dataclass(frozen=True)
class SubscriptionDiscovery:
    title: str
    source: str
    url: str
    feed_url: str
    episodes: list[PodcastEpisode]


def add_subscription(
    url: str,
    *,
    group_name: str = "Default",
    limit: int | None = DEFAULT_LIMIT,
    library_root: Path | None = None,
) -> dict[str, Any]:
    discovery = discover_subscription(url, limit=limit)
    store = LibraryStore(library_root or default_local_library_root())
    subscriptions = store.load_subscriptions()
    now = _now_iso()
    subscription_id = subscription_id_for(discovery)
    existing = next((item for item in subscriptions if item.get("id") == subscription_id), None)
    if existing is None:
        existing = {
            "id": subscription_id,
            "title": discovery.title,
            "source": discovery.source,
            "url": discovery.url,
            "feed_url": discovery.feed_url,
            "group_name": group_name,
            "created_at": now,
            "last_checked_at": "",
        }
    else:
        existing.update(
            {
                "title": discovery.title,
                "source": discovery.source,
                "url": discovery.url,
                "feed_url": discovery.feed_url,
                "group_name": group_name,
            }
        )
    store.upsert_subscription(existing)
    imported = import_subscription_episodes(
        _subscription_from_json(existing),
        discovery.episodes[:limit],
        library_root=store.root,
    )
    return {
        "subscription": existing,
        "imported": imported,
        **_import_counts(imported),
    }


def list_subscriptions(*, library_root: Path | None = None) -> dict[str, Any]:
    store = LibraryStore(library_root or default_local_library_root())
    return {"schema_version": 1, "subscriptions": store.load_subscriptions()}


def refresh_subscriptions(
    *,
    subscription_id: str | None = None,
    refresh_all: bool = False,
    limit: int | None = DEFAULT_LIMIT,
    library_root: Path | None = None,
) -> dict[str, Any]:
    store = LibraryStore(library_root or default_local_library_root())
    subscriptions = store.load_subscriptions()
    if subscription_id:
        selected = [item for item in subscriptions if item.get("id") == subscription_id]
        if not selected:
            raise ValueError(f"Unknown subscription id: {subscription_id}")
    elif refresh_all:
        selected = subscriptions
    else:
        raise ValueError("Use --all or --id to select subscriptions to refresh.")

    now = _now_iso()
    results: list[dict[str, Any]] = []
    for item in selected:
        subscription = _subscription_from_json(item)
        discovery = discover_subscription(subscription.feed_url or subscription.url, limit=limit)
        item["title"] = discovery.title
        item["source"] = discovery.source
        item["feed_url"] = discovery.feed_url
        item["last_checked_at"] = now
        store.upsert_subscription(item)
        imported = import_subscription_episodes(
            subscription,
            discovery.episodes[:limit],
            library_root=store.root,
        )
        results.append(
            {
                "subscription": item,
                "imported": imported,
                **_import_counts(imported),
            }
        )
    return {"results": results, "subscriptions": store.load_subscriptions()}


def remove_subscription(
    subscription_id: str,
    *,
    library_root: Path | None = None,
) -> dict[str, Any]:
    store = LibraryStore(library_root or default_local_library_root())
    return store.delete_subscription(subscription_id)


def discover_subscription(url: str, *, limit: int | None = DEFAULT_LIMIT) -> SubscriptionDiscovery:
    normalized = url.strip()
    if "xiaoyuzhoufm.com/podcast/" in normalized:
        podcast = fetch_podcast(normalized)
        return SubscriptionDiscovery(
            title=podcast.title,
            source="xiaoyuzhou",
            url=podcast.canonical_url or normalized,
            feed_url="",
            episodes=podcast.episodes[:limit],
        )
    if "podcasts.apple.com" in normalized:
        feed_url = apple_feed_url(normalized)
        discovery = parse_rss_feed(
            _fetch_bytes(feed_url), feed_url=feed_url, source_url=normalized, limit=limit
        )
        return SubscriptionDiscovery(
            title=discovery.title,
            source="podcast_rss",
            url=normalized,
            feed_url=feed_url,
            episodes=discovery.episodes[:limit],
        )
    discovered = discover_feed(normalized, fetcher=_fetch_bytes)
    return parse_rss_feed(
        discovered.data, feed_url=discovered.url, source_url=normalized, limit=limit
    )


def import_subscription_episodes(
    subscription: PodcastSubscription,
    episodes: list[PodcastEpisode],
    *,
    library_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    store = LibraryStore(library_root or default_local_library_root())
    for episode in episodes:
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
            subscription_id=subscription.id,
        )
        record = _episode_record(tagged, subscription)
        episode_id = stable_episode_id(record)
        if store.is_episode_tombstoned(episode_id, record):
            rows.append(_skipped_episode_row(tagged, {"state": "deleted"}))
            continue
        persisted, was_new = store.upsert_episode(record)
        rows.append(
            {
                "episode_id": persisted["episode_id"],
                "downloaded": False,
                "reused_existing": not was_new,
                "skipped": False,
                "title": tagged.title,
                "series_name": tagged.series_name,
                "published_at": tagged.published_at.isoformat(),
                "local_published_at": tagged.local_published_at.isoformat(),
                "audio_url": tagged.audio_url,
                "source_url": tagged.source_url,
            }
        )
    return rows


def _import_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "imported_count": sum(
            1 for row in rows if not row.get("reused_existing") and not row.get("skipped")
        ),
        "reused_count": sum(
            1 for row in rows if row.get("reused_existing") and not row.get("skipped")
        ),
        "skipped_count": sum(1 for row in rows if row.get("skipped")),
    }


def _skipped_episode_row(episode: PodcastEpisode, state_record: dict[str, Any]) -> dict[str, Any]:
    state = str(state_record.get("state") or "").strip() or "hidden"
    return {
        "downloaded": False,
        "reused_existing": False,
        "skipped": True,
        "skip_reason": f"library_tombstone_{state}",
        "state": state,
        "title": episode.title,
        "series_name": episode.series_name,
        "published_at": episode.published_at.isoformat(),
        "local_published_at": episode.local_published_at.isoformat(),
        "audio_url": episode.audio_url,
        "source_url": episode.source_url,
    }


def _episode_record(episode: PodcastEpisode, subscription: PodcastSubscription) -> dict[str, Any]:
    return {
        "app_group": subscription.group_name,
        "app_queue_status": "unread",
        "app_read": False,
        "app_star": False,
        "app_status": "link",
        "source": episode.source,
        "source_url": episode.source_url,
        "canonical_url": episode.canonical_url,
        "title": episode.title,
        "series_name": episode.series_name,
        "series_url": episode.series_url,
        "published_at": episode.published_at.isoformat(),
        "local_published_at": episode.local_published_at.isoformat(),
        "date_folder": episode.date_folder,
        "duration": episode.duration,
        "description": episode.description,
        "audio_url": episode.audio_url,
        "image_url": episode.image_url,
        "guid": episode.guid,
        "subscription_id": subscription.id,
    }


def apple_feed_url(url: str) -> str:
    match = re.search(r"/id(\d+)", url)
    if not match:
        raise ValueError(f"Could not find Apple Podcast id in URL: {url}")
    lookup_url = ITUNES_LOOKUP_URL.format(id=match.group(1))
    try:
        payload = json.loads(_fetch_bytes(lookup_url).decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Apple Podcast lookup returned invalid JSON for: {url}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Apple Podcast lookup returned an invalid payload for: {url}")
    results = payload.get("results") or []
    if (
        not isinstance(results, list)
        or not results
        or not isinstance(results[0], dict)
        or not results[0].get("feedUrl")
    ):
        raise ValueError(f"Could not find RSS feed for Apple Podcast: {url}")
    return str(results[0]["feedUrl"]).strip()


def parse_rss_feed(
    raw: bytes | str,
    *,
    feed_url: str,
    source_url: str,
    limit: int | None = None,
) -> SubscriptionDiscovery:
    parsed = _feedparser().parse(raw)
    if not parsed.version or (not parsed.feed.get("title") and not parsed.entries):
        raise ValueError("Feed is missing podcast metadata.")
    title = compact_ws(str(parsed.feed.get("title") or ""))
    image_url = _feed_image_url(parsed.feed)
    episodes: list[PodcastEpisode] = []
    for entry in parsed.entries[:limit]:
        try:
            episodes.append(
                _episode_from_feed_entry(
                    entry, feed_url=feed_url, series_name=title, series_image_url=image_url
                )
            )
        except ValueError:
            continue
    if parsed.entries and not episodes:
        raise ValueError("Feed does not contain podcast audio enclosures.")
    return SubscriptionDiscovery(
        title=title or feed_url,
        source="podcast_rss",
        url=source_url,
        feed_url=feed_url,
        episodes=episodes,
    )


def subscription_id_for(discovery: SubscriptionDiscovery) -> str:
    stable = discovery.feed_url or discovery.url
    digest = hashlib.sha1(f"{discovery.source}:{stable}".encode("utf-8")).hexdigest()[:12]
    return f"{discovery.source}-{digest}"


def _episode_from_feed_entry(
    entry: Any,
    *,
    feed_url: str,
    series_name: str,
    series_image_url: str | None,
) -> PodcastEpisode:
    audio_url = _entry_audio_url(entry)
    title = compact_ws(str(entry.get("title") or ""))
    if not title or not audio_url:
        raise ValueError("Feed entry is missing title or enclosure URL.")
    guid = compact_ws(str(entry.get("id") or entry.get("guid") or ""))
    link = compact_ws(str(entry.get("link") or ""))
    published_at = _entry_datetime(entry)
    description = _clean_description(_entry_description(entry))
    image_url = _entry_image_url(entry) or series_image_url
    return PodcastEpisode(
        source_url=link or guid or feed_url,
        canonical_url=link or guid or feed_url,
        title=title,
        series_name=series_name,
        series_url=feed_url,
        published_at=published_at,
        duration=compact_ws(str(entry.get("itunes_duration") or entry.get("duration") or "")),
        description=description,
        audio_url=audio_url,
        image_url=image_url,
        source="podcast_rss",
        guid=guid,
    )


def _entry_audio_url(entry: Any) -> str:
    for enclosure in entry.get("enclosures", []) or []:
        href = str(enclosure.get("href") or enclosure.get("url") or "").strip()
        mime_type = str(enclosure.get("type") or "").lower()
        if href and (not mime_type or mime_type.startswith("audio/")):
            return href
    for link in entry.get("links", []) or []:
        href = str(link.get("href") or link.get("url") or "").strip()
        mime_type = str(link.get("type") or "").lower()
        rel = str(link.get("rel") or "").lower()
        if href and (rel == "enclosure" or mime_type.startswith("audio/")):
            return href
    return ""


def _entry_datetime(entry: Any) -> datetime:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed[:9]), tz=timezone.utc)
    return _parse_rss_datetime(str(entry.get("published") or entry.get("updated") or ""))


def _entry_description(entry: Any) -> str:
    content = entry.get("content") or []
    if content and isinstance(content, list):
        value = content[0].get("value") if isinstance(content[0], dict) else ""
        if value:
            return str(value)
    return str(entry.get("summary") or entry.get("description") or "")


def _feed_image_url(feed: Any) -> str | None:
    image = feed.get("image") or {}
    if isinstance(image, dict):
        href = str(image.get("href") or image.get("url") or "").strip()
        if href:
            return href
    return None


def _entry_image_url(entry: Any) -> str | None:
    image = entry.get("image") or {}
    if isinstance(image, dict):
        href = str(image.get("href") or image.get("url") or "").strip()
        if href:
            return href
    return None


def _parse_rss_datetime(value: str) -> datetime:
    text = value.strip()
    if not text:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not parse RSS publish date: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_description(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _load_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "subscriptions": []}
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("subscriptions"), list):
        raise ValueError(f"Invalid subscriptions file: {path}")
    payload.setdefault("schema_version", 1)
    return payload


def _subscription_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in payload.get("subscriptions", []) if isinstance(item, dict)]


def _subscription_from_json(payload: dict[str, Any]) -> PodcastSubscription:
    return PodcastSubscription(
        id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        source=str(payload.get("source") or ""),
        url=str(payload.get("url") or ""),
        feed_url=str(payload.get("feed_url") or ""),
        group_name=str(payload.get("group_name") or "Default"),
        created_at=str(payload.get("created_at") or ""),
        last_checked_at=str(payload.get("last_checked_at") or ""),
    )


def _fetch_bytes(url: str, *, timeout: float = DEFAULT_NETWORK_TIMEOUT_SECONDS) -> bytes:
    return fetch_bytes(url, timeout=timeout)


def _now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat()
