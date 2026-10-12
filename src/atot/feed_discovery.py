from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Callable
from urllib.parse import urljoin, urlparse, urlunparse

from .http import HttpFetchError, fetch_bytes

FeedFetcher = Callable[..., bytes]

FEED_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/feed+json",
    "application/json",
    "text/xml",
    "application/xml",
}


class FeedDiscoveryError(ValueError):
    pass


def _feedparser() -> Any:
    try:
        import feedparser
    except ImportError as exc:
        raise RuntimeError(
            "Podcast feed discovery requires feedparser. Install with `pip install -e .`."
        ) from exc
    return feedparser


@dataclass(frozen=True)
class DiscoveredFeed:
    url: str
    data: bytes


@dataclass(frozen=True)
class FeedCandidate:
    url: str
    title: str
    source: str
    order: int


class _FeedLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[FeedCandidate] = []
        self._order = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        attr_map = {key.lower(): value or "" for key, value in attrs}
        rel_values = {value.strip().lower() for value in attr_map.get("rel", "").split()}
        href = attr_map.get("href", "").strip()
        if "alternate" not in rel_values or not href:
            return
        mime_type = attr_map.get("type", "").strip().lower()
        if mime_type and mime_type not in FEED_TYPES:
            return
        self._order += 1
        self.links.append(
            FeedCandidate(
                url=urljoin(self.base_url, href),
                title=attr_map.get("title", "").strip(),
                source="html_head",
                order=self._order,
            )
        )


def discover_feed(
    url: str, *, fetcher: FeedFetcher = fetch_bytes, timeout: float = 30.0
) -> DiscoveredFeed:
    normalized = url.strip()
    initial_data = _fetch(normalized, fetcher=fetcher, timeout=timeout)
    if can_parse_feed(initial_data):
        return DiscoveredFeed(url=normalized, data=initial_data)

    if not is_probably_html(initial_data):
        raise FeedDiscoveryError(f"Could not discover podcast feed from URL: {url}")

    candidates = [
        *html_feed_candidates(initial_data, base_url=normalized),
        *fallback_feed_candidates(normalized),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen:
            continue
        seen.add(candidate.url)
        try:
            data = _fetch(candidate.url, fetcher=fetcher, timeout=timeout)
        except (HttpFetchError, OSError, UnicodeError):
            continue
        if can_parse_feed(data):
            return DiscoveredFeed(url=candidate.url, data=data)

    raise FeedDiscoveryError(f"Could not discover podcast feed from URL: {url}")


def html_feed_candidates(raw: bytes | str, *, base_url: str) -> list[FeedCandidate]:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    parser = _FeedLinkParser(base_url)
    parser.feed(text)
    parser.close()
    return parser.links


def fallback_feed_candidates(url: str) -> list[FeedCandidate]:
    parsed = urlparse(url)
    root = urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))
    return [
        FeedCandidate(url=urljoin(root, "feed/"), title="", source="well_known", order=1),
        FeedCandidate(url=urljoin(root, "index.xml"), title="", source="well_known", order=2),
    ]


def can_parse_feed(raw: bytes | str) -> bool:
    parsed = _feedparser().parse(raw)
    return bool(parsed.version) and (bool(parsed.feed.get("title")) or bool(parsed.entries))


def is_probably_html(raw: bytes | str) -> bool:
    sample = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    lowered = sample[:4096].lower()
    return any(
        marker in lowered for marker in ("<!doctype html", "<html", "<head", "<body", "<link")
    )


def _fetch(url: str, *, fetcher: FeedFetcher, timeout: float) -> bytes:
    return fetcher(url, timeout=timeout)
