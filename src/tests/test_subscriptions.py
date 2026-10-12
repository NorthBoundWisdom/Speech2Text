import json
from datetime import datetime, timezone

from atot import subscriptions as subs
from atot.library_store import stable_episode_id
from atot.podcasts import PodcastEpisode, audio_download_urls
from atot.service_protocol import subscriptions_params
from atot.subscriptions import PodcastSubscription, import_subscription_episodes, parse_rss_feed
from atot.xiaoyuzhou import XiaoyuzhouPodcast


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>测试播客</title>
    <itunes:image href="https://image.example/show.png"/>
    <item>
      <title>001. RSS 测试</title>
      <link>https://example.com/episodes/1</link>
      <guid>episode-1</guid>
      <pubDate>Thu, 28 May 2026 00:00:00 GMT</pubDate>
      <description><![CDATA[<p>Shownotes<br>嘉宾：Alice</p>]]></description>
      <itunes:duration>01:02:03</itunes:duration>
      <enclosure url="https://media.example/episode-1.m4a" type="audio/mp4" length="123"/>
    </item>
    <item>
      <title>002. RSS 第二集</title>
      <guid>episode-2</guid>
      <pubDate>Wed, 27 May 2026 00:00:00 GMT</pubDate>
      <enclosure url="https://media.example/episode-2.m4a" type="audio/mp4" length="456"/>
    </item>
  </channel>
</rss>
"""

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom 播客</title>
  <entry>
    <title>001. Atom 测试</title>
    <id>tag:example.com,2026:atom-1</id>
    <link href="https://example.com/atom/1"/>
    <link rel="enclosure" href="https://media.example/atom-1.mp3" type="audio/mpeg"/>
    <published>2026-05-28T00:00:00Z</published>
    <summary>Atom shownotes</summary>
  </entry>
</feed>
"""


def episode(title: str, audio_url: str, guid: str) -> PodcastEpisode:
    return PodcastEpisode(
        source_url=f"https://example.com/{guid}",
        canonical_url=f"https://example.com/{guid}",
        title=title,
        series_name="测试播客",
        series_url="https://example.com/feed.xml",
        published_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
        duration="PT10M",
        description="shownotes",
        audio_url=audio_url,
        source="podcast_rss",
        guid=guid,
    )


def test_parse_rss_feed_extracts_episode_metadata():
    discovery = parse_rss_feed(
        RSS, feed_url="https://example.com/feed.xml", source_url="https://apple.example/show"
    )

    assert discovery.title == "测试播客"
    assert discovery.source == "podcast_rss"
    assert discovery.episodes[0].title == "001. RSS 测试"
    assert discovery.episodes[0].audio_url == "https://media.example/episode-1.m4a"
    assert discovery.episodes[0].guid == "episode-1"
    assert discovery.episodes[0].duration == "01:02:03"
    assert "嘉宾：Alice" in discovery.episodes[0].description


def test_parse_rss_feed_accepts_atom_feed():
    discovery = parse_rss_feed(
        ATOM, feed_url="https://example.com/atom.xml", source_url="https://example.com/show"
    )

    assert discovery.title == "Atom 播客"
    assert discovery.feed_url == "https://example.com/atom.xml"
    assert discovery.episodes[0].title == "001. Atom 测试"
    assert discovery.episodes[0].audio_url == "https://media.example/atom-1.mp3"
    assert discovery.episodes[0].guid == "tag:example.com,2026:atom-1"
    assert discovery.episodes[0].source_url == "https://example.com/atom/1"


def test_apple_podcast_url_resolves_feed(monkeypatch):
    def fake_fetch(url, **_kwargs):
        assert "itunes.apple.com/lookup" in url
        return b'{"resultCount":1,"results":[{"feedUrl":"https://example.com/feed.xml"}]}'

    monkeypatch.setattr(subs, "_fetch_bytes", fake_fetch)

    assert (
        subs.apple_feed_url("https://podcasts.apple.com/us/podcast/show/id12345")
        == "https://example.com/feed.xml"
    )


def test_apple_podcast_url_rejects_invalid_lookup_json(monkeypatch):
    monkeypatch.setattr(subs, "_fetch_bytes", lambda *args, **kwargs: b"{")

    try:
        subs.apple_feed_url("https://podcasts.apple.com/us/podcast/show/id12345")
    except ValueError as exc:
        assert "invalid JSON" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_discover_subscription_finds_feed_from_html_alternate(monkeypatch):
    html = b"""
    <html><head>
      <link rel="alternate" type="application/rss+xml" href="/podcast.xml" title="Podcast">
    </head><body></body></html>
    """

    def fake_fetch(url, **_kwargs):
        if url == "https://example.com/show":
            return html
        if url == "https://example.com/podcast.xml":
            return RSS.encode("utf-8")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(subs, "_fetch_bytes", fake_fetch)

    discovery = subs.discover_subscription("https://example.com/show")

    assert discovery.title == "测试播客"
    assert discovery.feed_url == "https://example.com/podcast.xml"
    assert discovery.episodes[0].audio_url == "https://media.example/episode-1.m4a"


def test_discover_subscription_tries_well_known_feed_paths(monkeypatch):
    html = b"<html><head><title>No feed link</title></head><body></body></html>"
    calls = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if url == "https://example.com/show":
            return html
        if url == "https://example.com/feed/":
            return b"not a feed"
        if url == "https://example.com/index.xml":
            return RSS.encode("utf-8")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(subs, "_fetch_bytes", fake_fetch)

    discovery = subs.discover_subscription("https://example.com/show")

    assert discovery.feed_url == "https://example.com/index.xml"
    assert "https://example.com/feed/" in calls
    assert discovery.episodes[0].title == "001. RSS 测试"


def test_audio_download_urls_unwraps_simplecast_tracking_url():
    url = (
        "https://clrtpod.com/m/pscrb.fm/rss/p/mgln.ai/e/1184/"
        "afp-969439-injected.calisto.simplecastaudio.com/show/episodes/abc/audio/128/default.mp3"
        "?aid=rss_feed"
    )

    assert audio_download_urls(url) == [
        url,
        "https://afp-969439-injected.calisto.simplecastaudio.com/show/episodes/abc/audio/128/default.mp3"
        "?aid=rss_feed",
    ]


def test_add_subscription_writes_store_and_metadata_without_channel_folder(monkeypatch, tmp_path):
    podcast = XiaoyuzhouPodcast(
        source_url="https://www.xiaoyuzhoufm.com/podcast/show",
        canonical_url="https://www.xiaoyuzhoufm.com/podcast/show",
        title="小宇宙栏目",
        author="主播",
        description="简介",
        image_url=None,
        episodes=[
            PodcastEpisode(
                source_url="https://www.xiaoyuzhoufm.com/episode/abc",
                canonical_url="https://www.xiaoyuzhoufm.com/episode/abc",
                title="001. 小宇宙单集",
                series_name="小宇宙栏目",
                series_url="https://www.xiaoyuzhoufm.com/podcast/show",
                published_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
                duration="600",
                description="Shownotes",
                audio_url="https://media.example/xyz.m4a",
                source="xiaoyuzhou",
                guid="abc",
            )
        ],
    )
    monkeypatch.setattr(subs, "fetch_podcast", lambda _url: podcast)

    result = subs.add_subscription(
        "https://www.xiaoyuzhoufm.com/podcast/show",
        group_name="Research",
        library_root=tmp_path / "Audio2TextLibrary",
    )
    episode_id = result["imported"][0]["episode_id"]
    metadata_path = tmp_path / "Audio2TextLibrary" / "episodes" / episode_id / "episode.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["subscription"]["title"] == "小宇宙栏目"
    assert result["imported_count"] == 1
    assert metadata["app_group"] == "Research"
    assert metadata["app_read"] is False
    assert metadata["source"] == "xiaoyuzhou"
    assert metadata["subscription_id"] == result["subscription"]["id"]
    assert not (tmp_path / "process" / "小宇宙栏目").exists()
    assert list((tmp_path / "process").glob("*/*/episode.json")) == []


def test_refresh_subscription_is_idempotent(monkeypatch, tmp_path):
    calls = {"count": 0}

    def fake_discover(_url, *, limit):
        calls["count"] += 1
        return subs.SubscriptionDiscovery(
            title="测试播客",
            source="podcast_rss",
            url="https://example.com/feed.xml",
            feed_url="https://example.com/feed.xml",
            episodes=[episode("001. 测试", "https://media.example/one.m4a", "one")],
        )

    monkeypatch.setattr(subs, "discover_subscription", fake_discover)
    library_root = tmp_path / "Audio2TextLibrary"
    added = subs.add_subscription("https://example.com/feed.xml", library_root=library_root)
    refreshed = subs.refresh_subscriptions(
        subscription_id=added["subscription"]["id"],
        limit=10,
        library_root=library_root,
    )

    assert calls["count"] == 2
    assert refreshed["results"][0]["imported_count"] == 0
    assert refreshed["results"][0]["reused_count"] == 1
    assert refreshed["results"][0]["skipped_count"] == 0
    assert len(list((tmp_path / "Audio2TextLibrary" / "episodes").glob("*/episode.json"))) == 1


def test_refresh_full_history_passes_unlimited_limit(monkeypatch, tmp_path):
    limits = []

    def fake_discover(_url, *, limit):
        limits.append(limit)
        return subs.SubscriptionDiscovery(
            title="测试播客",
            source="podcast_rss",
            url="https://example.com/feed.xml",
            feed_url="https://example.com/feed.xml",
            episodes=[
                episode("001. 测试", "https://media.example/one.m4a", "one"),
                episode("002. 测试", "https://media.example/two.m4a", "two"),
                episode("003. 测试", "https://media.example/three.m4a", "three"),
            ],
        )

    monkeypatch.setattr(subs, "discover_subscription", fake_discover)
    library_root = tmp_path / "Audio2TextLibrary"
    subscription = {
        "id": "podcast_rss-test",
        "title": "测试播客",
        "source": "podcast_rss",
        "url": "https://example.com/feed.xml",
        "feed_url": "https://example.com/feed.xml",
        "group_name": "Default",
        "created_at": "2026-05-29T00:00:00+08:00",
        "last_checked_at": "",
    }
    subs.LibraryStore(library_root).upsert_subscription(subscription)

    refreshed = subs.refresh_subscriptions(
        subscription_id=subscription["id"],
        limit=None,
        library_root=library_root,
    )

    assert limits == [None]
    assert refreshed["results"][0]["imported_count"] == 3
    assert len(list((library_root / "episodes").glob("*/episode.json"))) == 3


def test_service_protocol_parses_full_history_subscription_refresh():
    params = subscriptions_params(
        ["refresh", "--id", "podcast_rss-test", "--full-history", "--json"]
    )

    assert params["command"] == "refresh"
    assert params["subscription_id"] == "podcast_rss-test"
    assert params["limit"] is None


def test_refresh_skips_deleted_episode_state(monkeypatch, tmp_path):
    def fake_discover(_url, *, limit):
        return subs.SubscriptionDiscovery(
            title="测试播客",
            source="podcast_rss",
            url="https://example.com/feed.xml",
            feed_url="https://example.com/feed.xml",
            episodes=[episode("001. 测试", "https://media.example/one.m4a", "one")],
        )

    monkeypatch.setattr(subs, "discover_subscription", fake_discover)
    library_root = tmp_path / "Audio2TextLibrary"
    process_dir = tmp_path / "process"
    added = subs.add_subscription("https://example.com/feed.xml", library_root=library_root)
    episode_record = {
        "source": "podcast_rss",
        "subscription_id": added["subscription"]["id"],
        "guid": "one",
        "audio_url": "https://media.example/one.m4a",
        "canonical_url": "https://example.com/one",
    }
    episode_id = stable_episode_id(episode_record)
    tombstone_dir = tmp_path / "Audio2TextLibrary" / "tombstones" / "episodes"
    tombstone_dir.mkdir(parents=True, exist_ok=True)
    (tombstone_dir / f"{episode_id}.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "audio2text.library.episode_tombstone",
                "episode_id": episode_id,
                "subscription_id": added["subscription"]["id"],
                "audio_url": "https://media.example/one.m4a",
                "guid": "one",
            }
        ),
        encoding="utf-8",
    )

    refreshed = subs.refresh_subscriptions(
        subscription_id=added["subscription"]["id"],
        limit=10,
        library_root=library_root,
    )

    row = refreshed["results"][0]["imported"][0]
    assert refreshed["results"][0]["imported_count"] == 0
    assert refreshed["results"][0]["reused_count"] == 0
    assert refreshed["results"][0]["skipped_count"] == 1
    assert row["skipped"] is True
    assert row["skip_reason"] == "library_tombstone_deleted"
    assert list(process_dir.glob("*/*/episode.json")) == []


def test_refresh_reuses_existing_library_episode(monkeypatch, tmp_path):
    def fake_discover(_url, *, limit):
        return subs.SubscriptionDiscovery(
            title="测试播客",
            source="podcast_rss",
            url="https://example.com/feed.xml",
            feed_url="https://example.com/feed.xml",
            episodes=[episode("001. 测试", "https://media.example/one.m4a", "one")],
        )

    monkeypatch.setattr(subs, "discover_subscription", fake_discover)
    library_root = tmp_path / "Audio2TextLibrary"
    added = subs.add_subscription("https://example.com/feed.xml", library_root=library_root)

    refreshed = subs.refresh_subscriptions(
        subscription_id=added["subscription"]["id"],
        limit=10,
        library_root=library_root,
    )

    row = refreshed["results"][0]["imported"][0]
    assert refreshed["results"][0]["imported_count"] == 0
    assert refreshed["results"][0]["reused_count"] == 1
    assert refreshed["results"][0]["skipped_count"] == 0
    assert row["reused_existing"] is True


def test_refresh_keeps_items_with_shared_episode_page_separate(monkeypatch, tmp_path):
    def fake_discover(_url, *, limit):
        return subs.SubscriptionDiscovery(
            title="测试播客",
            source="podcast_rss",
            url="https://example.com/feed.xml",
            feed_url="https://example.com/feed.xml",
            episodes=[
                PodcastEpisode(
                    source_url="https://example.com/show",
                    canonical_url="https://example.com/show",
                    title="001. 第一集",
                    series_name="测试播客",
                    series_url="https://example.com/feed.xml",
                    published_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
                    duration="PT10M",
                    description="shownotes",
                    audio_url="https://media.example/one.m4a",
                    source="podcast_rss",
                    guid="one",
                ),
                PodcastEpisode(
                    source_url="https://example.com/show",
                    canonical_url="https://example.com/show",
                    title="002. 第二集",
                    series_name="测试播客",
                    series_url="https://example.com/feed.xml",
                    published_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
                    duration="PT10M",
                    description="shownotes",
                    audio_url="https://media.example/two.m4a",
                    source="podcast_rss",
                    guid="two",
                ),
            ][:limit],
        )

    monkeypatch.setattr(subs, "discover_subscription", fake_discover)
    library_root = tmp_path / "Audio2TextLibrary"

    added = subs.add_subscription("https://example.com/feed.xml", library_root=library_root)

    assert added["imported_count"] == 2
    metadata_paths = sorted((tmp_path / "Audio2TextLibrary" / "episodes").glob("*/episode.json"))
    assert len(metadata_paths) == 2
    audio_urls = {
        json.loads(path.read_text(encoding="utf-8"))["audio_url"] for path in metadata_paths
    }
    assert audio_urls == {"https://media.example/one.m4a", "https://media.example/two.m4a"}


def test_import_subscription_episodes_writes_to_library_root(tmp_path):
    subscription = PodcastSubscription(
        id="podcast_rss-test",
        title="测试播客",
        source="podcast_rss",
        url="https://example.com/feed.xml",
        feed_url="https://example.com/feed.xml",
        group_name="Default",
        created_at="2026-05-29T00:00:00+08:00",
    )

    rows = import_subscription_episodes(
        subscription,
        [episode("001. 默认目录", "https://media.example/default.m4a", "default")],
        library_root=tmp_path / "Audio2TextLibrary",
    )

    assert rows[0]["episode_id"]
    assert (
        tmp_path / "Audio2TextLibrary" / "episodes" / rows[0]["episode_id"] / "episode.json"
    ).is_file()
    assert not (tmp_path / "process" / "测试播客").exists()
