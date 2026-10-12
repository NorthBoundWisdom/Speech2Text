from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .http import fetch_bytes
from .podcasts import (
    PodcastEpisode,
    PodcastImportError,
    PodcastImportResult,
    audio_filename,
    audio_suffix,
    download_audio,
    episode_folder_name,
    episode_metadata as podcast_episode_metadata,
    episode_topic_markdown as podcast_episode_topic_markdown,
    existing_audio_path,
    import_podcast_episode,
    strip_episode_prefix,
)
from .paths import PROCESS_DIR


class _EpisodeHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.jsonld_scripts: list[str] = []
        self._script_type: str | None = None
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "meta":
            self.meta.append(attr_map)
        elif tag == "link":
            self.links.append(attr_map)
        elif tag == "script":
            script_type = attr_map.get("type", "").lower()
            if script_type == "application/ld+json":
                self._script_type = script_type
                self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._script_type == "application/ld+json":
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_type == "application/ld+json":
            self.jsonld_scripts.append("".join(self._script_parts))
            self._script_type = None
            self._script_parts = []


def _parse_episode_html(html_text: str) -> _EpisodeHtmlParser:
    parser = _EpisodeHtmlParser()
    parser.feed(html_text)
    parser.close()
    return parser


XiaoyuzhouEpisode = PodcastEpisode


XiaoyuzhouImportResult = PodcastImportResult


class XiaoyuzhouImportError(PodcastImportError):
    pass


@dataclass(frozen=True)
class XiaoyuzhouPodcast:
    """Podcast metadata parsed from a Xiaoyuzhou podcast page."""

    source_url: str
    canonical_url: str
    title: str
    author: str
    description: str
    image_url: str | None
    episodes: list[XiaoyuzhouEpisode]


def fetch_episode(url: str, *, timeout: float = 30.0) -> XiaoyuzhouEpisode:
    html_text = _fetch_text(url, timeout=timeout)
    return parse_episode_html(html_text, source_url=url)


def fetch_podcast(url: str, *, timeout: float = 30.0) -> XiaoyuzhouPodcast:
    html_text = _fetch_text(url, timeout=timeout)
    return parse_podcast_html(html_text, source_url=url)


def parse_episode_html(html_text: str, *, source_url: str) -> XiaoyuzhouEpisode:
    payload = _extract_podcast_episode_json(html_text)
    title = str(payload.get("name", "")).strip()
    audio_url = str((payload.get("associatedMedia") or {}).get("contentUrl", "")).strip()
    if not title:
        title = _extract_meta_content(html_text, "og:title")
    if not audio_url:
        audio_url = _extract_meta_content(html_text, "og:audio")
    if not title or not audio_url:
        raise XiaoyuzhouImportError("Could not find episode title or audio URL in Xiaoyuzhou page.")

    published_raw = str(payload.get("datePublished", "")).strip()
    try:
        published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise XiaoyuzhouImportError(
            f"Could not parse episode publish date: {published_raw}"
        ) from exc

    series = payload.get("partOfSeries") or {}
    canonical_url = str(
        payload.get("url") or _extract_canonical_url(html_text) or source_url
    ).strip()
    return XiaoyuzhouEpisode(
        source_url=source_url,
        canonical_url=canonical_url,
        title=title,
        series_name=str(series.get("name", "")).strip(),
        series_url=str(series.get("url", "")).strip(),
        published_at=published_at,
        duration=str(payload.get("timeRequired", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        audio_url=audio_url,
        image_url=_extract_meta_content(html_text, "og:image") or None,
        source="xiaoyuzhou",
    )


def parse_podcast_html(html_text: str, *, source_url: str) -> XiaoyuzhouPodcast:
    payload = _extract_next_podcast_json(html_text)
    title = str(payload.get("title") or "").strip()
    if not title:
        raise XiaoyuzhouImportError("Could not find Xiaoyuzhou podcast title.")
    canonical_url = _extract_canonical_url(html_text) or source_url
    image = payload.get("image") or {}
    episodes = [
        _episode_from_next_payload(item, podcast=payload, source_url=source_url)
        for item in payload.get("episodes", [])
        if isinstance(item, dict)
    ]
    return XiaoyuzhouPodcast(
        source_url=source_url,
        canonical_url=canonical_url,
        title=title,
        author=str(payload.get("author") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        image_url=str(image.get("picUrl") or "").strip()
        or _extract_meta_content(html_text, "og:image")
        or None,
        episodes=episodes,
    )


def import_xiaoyuzhou_episode(
    url: str,
    *,
    process_dir: Path = PROCESS_DIR,
    group_name: str | None = None,
    folder_name: str | None = None,
    audio_name: str | None = None,
    download: bool = True,
    force: bool = False,
) -> XiaoyuzhouImportResult:
    """Import a Xiaoyuzhou episode into the local process library.

    Args:
        url: Xiaoyuzhou episode URL.
        process_dir: Process library root.
        group_name: Optional physical group name under the process library.
        folder_name: Optional destination episode folder override.
        audio_name: Optional downloaded audio filename override.
        download: Whether to download the episode audio.
        force: Whether to overwrite an existing import.

    Returns:
        Metadata for the imported or reused podcast episode.
    """

    episode = fetch_episode(url)
    return import_podcast_episode(
        episode,
        process_dir=process_dir,
        physical_group_name=group_name,
        folder_name=folder_name,
        audio_name=audio_name,
        download=download,
        force=force,
        download_fn=download_audio,
    )


def _find_existing_import_by_audio_url(
    search_root: Path, episode: XiaoyuzhouEpisode
) -> XiaoyuzhouImportResult | None:
    if not search_root.exists():
        return None
    metadata_paths = sorted(
        {*search_root.glob("*/episode.json"), *search_root.glob("*/*/episode.json")}
    )
    for metadata_path in metadata_paths:
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            not isinstance(payload, dict)
            or str(payload.get("audio_url") or "") != episode.audio_url
        ):
            continue
        episode_dir = metadata_path.parent
        audio_path = existing_audio_path(payload, episode_dir)
        if audio_path is None:
            continue
        topic_path = episode_dir / "主题.md"
        return XiaoyuzhouImportResult(
            episode=episode,
            episode_dir=episode_dir,
            audio_path=audio_path,
            topic_path=topic_path,
            metadata_path=metadata_path,
            downloaded=False,
            reused_existing=True,
        )
    return None


def episode_topic_markdown(episode: XiaoyuzhouEpisode) -> str:
    return podcast_episode_topic_markdown(episode)


def episode_metadata(
    episode: XiaoyuzhouEpisode, *, audio_path: Path, topic_path: Path
) -> dict[str, Any]:
    return podcast_episode_metadata(episode, audio_path=audio_path, topic_path=topic_path)


def _fetch_text(url: str, *, timeout: float) -> str:
    try:
        raw = fetch_bytes(url, timeout=timeout)
    except Exception as exc:
        raise XiaoyuzhouImportError(f"Could not fetch Xiaoyuzhou page: {url}") from exc
    return raw.decode("utf-8", errors="replace")


def _extract_podcast_episode_json(html_text: str) -> dict[str, Any]:
    for script in _parse_episode_html(html_text).jsonld_scripts:
        text = html.unescape(script).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        for item in _jsonld_items(payload):
            if item.get("@type") == "PodcastEpisode":
                return item
    raise XiaoyuzhouImportError("Could not find PodcastEpisode JSON-LD in Xiaoyuzhou page.")


def _extract_next_podcast_json(html_text: str) -> dict[str, Any]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, re.S
    )
    if not match:
        raise XiaoyuzhouImportError("Could not find Xiaoyuzhou podcast page data.")
    try:
        payload = json.loads(html.unescape(match.group(1)))
    except json.JSONDecodeError as exc:
        raise XiaoyuzhouImportError("Could not parse Xiaoyuzhou podcast page data.") from exc
    podcast = ((payload.get("props") or {}).get("pageProps") or {}).get("podcast")
    if not isinstance(podcast, dict):
        raise XiaoyuzhouImportError("Could not find Xiaoyuzhou podcast metadata.")
    return podcast


def _episode_from_next_payload(
    payload: dict[str, Any],
    *,
    podcast: dict[str, Any],
    source_url: str,
) -> XiaoyuzhouEpisode:
    title = str(payload.get("title") or "").strip()
    audio_url = str((payload.get("enclosure") or {}).get("url") or "").strip()
    if not audio_url:
        audio_url = str(
            (((payload.get("media") or {}).get("source") or {}).get("url")) or ""
        ).strip()
    published_raw = str(payload.get("pubDate") or "").strip()
    if not title or not audio_url or not published_raw:
        raise XiaoyuzhouImportError("Could not parse Xiaoyuzhou podcast episode metadata.")
    try:
        published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise XiaoyuzhouImportError(
            f"Could not parse episode publish date: {published_raw}"
        ) from exc
    eid = str(payload.get("eid") or "").strip()
    pid = str(podcast.get("pid") or payload.get("pid") or "").strip()
    canonical_url = f"https://www.xiaoyuzhoufm.com/episode/{eid}" if eid else source_url
    image = payload.get("image") or podcast.get("image") or {}
    duration = payload.get("duration")
    return XiaoyuzhouEpisode(
        source_url=canonical_url,
        canonical_url=canonical_url,
        title=title,
        series_name=str(podcast.get("title") or "").strip(),
        series_url=f"https://www.xiaoyuzhoufm.com/podcast/{pid}" if pid else source_url,
        published_at=published_at,
        duration=str(duration or "").strip(),
        description=str(payload.get("shownotes") or payload.get("description") or "").strip(),
        audio_url=audio_url,
        image_url=str(image.get("picUrl") or "").strip() or None,
        source="xiaoyuzhou",
        guid=eid,
    )


def _jsonld_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _extract_meta_content(html_text: str, property_name: str) -> str:
    expected = property_name.lower()
    for attrs in _parse_episode_html(html_text).meta:
        meta_name = (attrs.get("property") or attrs.get("name") or "").lower()
        if meta_name == expected:
            return html.unescape(attrs.get("content", "")).strip()
    return ""


def _extract_canonical_url(html_text: str) -> str:
    for attrs in _parse_episode_html(html_text).links:
        rel_values = {value.strip().lower() for value in attrs.get("rel", "").split()}
        if "canonical" in rel_values:
            return html.unescape(attrs.get("href", "")).strip()
    return ""


def _episode_folder_name(episode: XiaoyuzhouEpisode, explicit: str | None) -> str:
    return episode_folder_name(episode, explicit)


def _audio_filename(episode: XiaoyuzhouEpisode, explicit: str | None) -> str:
    return audio_filename(episode, explicit)


def _audio_suffix(audio_url: str) -> str:
    return audio_suffix(audio_url)


def _strip_episode_prefix(title: str) -> str:
    return strip_episode_prefix(title)
