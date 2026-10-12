from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

from .http import open_url
from .paths import PROCESS_DIR
from .utils import ensure_dir, slugify, write_json_atomic, write_text_atomic

CHINA_TZ = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class PodcastEpisode:
    source_url: str
    canonical_url: str
    title: str
    series_name: str
    series_url: str
    published_at: datetime
    duration: str
    description: str
    audio_url: str
    image_url: str | None = None
    source: str = "podcast_rss"
    guid: str = ""
    subscription_id: str = ""

    @property
    def local_published_at(self) -> datetime:
        return self.published_at.astimezone(CHINA_TZ)

    @property
    def date_folder(self) -> str:
        return self.local_published_at.strftime("%m%d")


@dataclass(frozen=True)
class PodcastImportResult:
    episode: PodcastEpisode
    episode_dir: Path
    audio_path: Path
    topic_path: Path
    metadata_path: Path
    downloaded: bool
    reused_existing: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "episode_dir": str(self.episode_dir),
            "audio_path": str(self.audio_path),
            "topic_path": str(self.topic_path),
            "metadata_path": str(self.metadata_path),
            "downloaded": self.downloaded,
            "reused_existing": self.reused_existing,
            "title": self.episode.title,
            "series_name": self.episode.series_name,
            "published_at": self.episode.published_at.isoformat(),
            "local_published_at": self.episode.local_published_at.isoformat(),
            "audio_url": self.episode.audio_url,
            "source_url": self.episode.source_url,
        }


class PodcastImportError(RuntimeError):
    pass


def import_podcast_episode(
    episode: PodcastEpisode,
    *,
    process_dir: Path = PROCESS_DIR,
    physical_group_name: str | None = None,
    app_group_name: str | None = None,
    folder_name: str | None = None,
    audio_name: str | None = None,
    download: bool = True,
    force: bool = False,
    reuse_metadata_only: bool = False,
    download_fn: Any | None = None,
) -> PodcastImportResult:
    group_folder = slugify(physical_group_name) if physical_group_name else ""
    episode_parent = (
        process_dir / group_folder if group_folder else process_dir / episode.date_folder
    )
    existing_root = process_dir / group_folder if group_folder else process_dir
    if not force and folder_name is None and audio_name is None:
        existing = find_existing_import(
            existing_root, episode, require_audio=download and not reuse_metadata_only
        )
        if existing is not None:
            return existing

    episode_dir = ensure_dir(episode_parent / episode_folder_name(episode, folder_name))
    audio_path = episode_dir / audio_filename(episode, audio_name)
    topic_path = episode_dir / "主题.md"
    metadata_path = episode_dir / "episode.json"

    downloaded = False
    if download:
        downloader = download_fn or download_audio
        downloaded = downloader(episode.audio_url, audio_path, force=force)
    write_text_atomic(topic_path, episode_topic_markdown(episode))
    write_json_atomic(
        metadata_path,
        episode_metadata(
            episode, audio_path=audio_path, topic_path=topic_path, app_group_name=app_group_name
        ),
    )
    return PodcastImportResult(
        episode=episode,
        episode_dir=episode_dir,
        audio_path=audio_path,
        topic_path=topic_path,
        metadata_path=metadata_path,
        downloaded=downloaded,
    )


def find_existing_import(
    search_root: Path, episode: PodcastEpisode, *, require_audio: bool
) -> PodcastImportResult | None:
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
        if not isinstance(payload, dict) or not _metadata_matches_episode(payload, episode):
            continue
        episode_dir = metadata_path.parent
        audio_path = existing_audio_path(payload, episode_dir)
        if audio_path is None:
            audio_path = planned_audio_path(payload, episode_dir)
        if audio_path is None or (require_audio and not _is_existing_non_empty_file(audio_path)):
            continue
        return PodcastImportResult(
            episode=episode,
            episode_dir=episode_dir,
            audio_path=audio_path,
            topic_path=episode_dir / "主题.md",
            metadata_path=metadata_path,
            downloaded=False,
            reused_existing=True,
        )
    return None


def _metadata_matches_episode(payload: dict[str, Any], episode: PodcastEpisode) -> bool:
    for key, value in (("audio_url", episode.audio_url), ("guid", episode.guid)):
        if value and str(payload.get(key) or "") == value:
            return True

    # Some RSS feeds reuse the same episode page URL for every item, so link
    # matching is only safe when neither side has a stronger per-episode ID.
    if any((episode.audio_url, episode.guid, payload.get("audio_url"), payload.get("guid"))):
        return False
    for key, value in (
        ("canonical_url", episode.canonical_url),
        ("source_url", episode.source_url),
    ):
        if value and str(payload.get(key) or "") == value:
            return True
    return False


def existing_audio_path(payload: dict[str, Any], episode_dir: Path) -> Path | None:
    candidates: list[Path] = []
    planned = planned_audio_path(payload, episode_dir)
    if planned is not None:
        candidates.append(planned)
    candidates.extend(
        sorted(
            path
            for path in episode_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".m4a", ".mp3", ".wav", ".flac", ".aac"}
        )
    )
    for path in candidates:
        if _is_existing_non_empty_file(path):
            return path
    return None


def planned_audio_path(payload: dict[str, Any], episode_dir: Path) -> Path | None:
    recorded = str(payload.get("audio_path") or "").strip()
    if not recorded:
        return None
    path = Path(recorded)
    return path if path.is_absolute() else episode_dir / path


def download_audio(
    url: str, output_path: Path, *, force: bool = False, timeout: float = 60.0
) -> bool:
    if _is_existing_non_empty_file(output_path) and not force:
        return False
    errors: list[Exception] = []
    for candidate in audio_download_urls(url):
        try:
            _download_audio_once(candidate, output_path, timeout=timeout)
            return True
        except Exception as exc:
            errors.append(exc)
    if errors:
        raise errors[-1]
    raise PodcastImportError(f"No audio download URL candidates for: {url}")


def _download_audio_once(url: str, output_path: Path, *, timeout: float) -> None:
    ensure_dir(output_path.parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=output_path.name, suffix=".tmp", dir=str(output_path.parent)
    )
    try:
        with open_url(url, timeout=timeout) as response, os.fdopen(fd, "wb") as tmp:
            fd = -1
            shutil.copyfileobj(response, tmp)
        tmp_path = Path(tmp_name)
        if tmp_path.stat().st_size <= 0:
            raise PodcastImportError(f"Downloaded audio is empty: {url}")
        Path(tmp_name).replace(output_path)
    finally:
        if fd >= 0:
            os.close(fd)
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()


def audio_download_urls(url: str) -> list[str]:
    candidates = [url]
    parsed = urlparse(url)
    embedded = _embedded_simplecast_audio_url(parsed)
    if embedded and embedded not in candidates:
        candidates.append(embedded)
    return candidates


def _embedded_simplecast_audio_url(parsed: Any) -> str | None:
    marker = "/afp-"
    parsed_path = str(parsed.path)
    parsed_netloc = str(parsed.netloc)
    marker_index = parsed_path.find(marker)
    if parsed_netloc != "clrtpod.com" or marker_index < 0:
        return None
    rest = parsed_path[marker_index + 1 :]
    if "/" not in rest:
        return None
    host, path = rest.split("/", 1)
    if not host.endswith(".simplecastaudio.com"):
        return None
    return urlunparse(("https", host, f"/{path}", "", str(parsed.query), ""))


def episode_topic_markdown(episode: PodcastEpisode) -> str:
    lines = [
        f"# {episode.title}",
        "",
        f"- Podcast: {episode.series_name or ''}",
        f"- Published at: {episode.local_published_at.strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"- Original link: {episode.canonical_url or episode.source_url}",
        f"- Audio: {episode.audio_url}",
    ]
    if episode.duration:
        lines.append(f"- Duration: {episode.duration}")
    if episode.image_url:
        lines.append(f"- Cover: {episode.image_url}")
    if episode.series_url:
        lines.append(f"- Podcast link: {episode.series_url}")
    lines.extend(["", "## Shownotes", "", episode.description.strip()])
    return "\n".join(lines).strip() + "\n"


def episode_metadata(
    episode: PodcastEpisode,
    *,
    audio_path: Path,
    topic_path: Path,
    app_group_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "app_read": False,
        "app_star": False,
        "app_status": "link",
        "app_status_updated_at": datetime.now(CHINA_TZ).isoformat(),
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
        "audio_path": str(audio_path),
        "topic_path": str(topic_path),
    }
    if episode.guid:
        payload["guid"] = episode.guid
    if episode.subscription_id:
        payload["subscription_id"] = episode.subscription_id
    if app_group_name:
        payload["app_group"] = app_group_name
    return payload


def episode_folder_name(episode: PodcastEpisode, explicit: str | None) -> str:
    if explicit:
        return slugify(explicit)
    return slugify(strip_episode_prefix(episode.title), max_len=80)


def audio_filename(episode: PodcastEpisode, explicit: str | None) -> str:
    if explicit:
        filename = slugify(Path(explicit).stem, max_len=120)
        suffix = Path(explicit).suffix or audio_suffix(episode.audio_url)
        return f"{filename}{suffix}"
    return f"{slugify(strip_episode_prefix(episode.title), max_len=120)}{audio_suffix(episode.audio_url)}"


def audio_suffix(audio_url: str) -> str:
    suffix = Path(urlparse(audio_url).path).suffix
    return suffix if suffix else ".m4a"


def strip_episode_prefix(title: str) -> str:
    return re.sub(r"^\s*(?:vol\.?\s*)?\d+[\s.、_|:：-]+", "", title, flags=re.I).strip() or title


def _is_existing_non_empty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False
