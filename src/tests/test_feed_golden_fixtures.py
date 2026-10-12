import json
from pathlib import Path

from atot import subscriptions as subs
from atot.library_store import LibraryStore, stable_episode_id
from atot.subscriptions import PodcastSubscription, import_subscription_episodes, parse_rss_feed
from atot.xiaoyuzhou import parse_podcast_html


FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "Tests"
    / "Audio2TextCoreTests"
    / "Fixtures"
    / "FeedGolden"
)


def test_shared_feed_golden_fixtures_match_discovery_and_id_contracts(monkeypatch):
    expected = _expected()

    rss = parse_rss_feed(
        _fixture_text("rss.xml"),
        feed_url=expected["rss"]["feed_url"],
        source_url=expected["rss"]["url"],
    )
    _assert_discovery(rss, expected["rss"])

    monkeypatch.setattr(
        subs, "_fetch_bytes", lambda *_args, **_kwargs: _fixture_bytes("apple_lookup.json")
    )
    apple_feed_url = subs.apple_feed_url(expected["apple"]["source_url"])
    assert apple_feed_url == expected["apple"]["lookup_feed_url"]
    apple_rss = parse_rss_feed(
        _fixture_text("rss.xml"),
        feed_url=apple_feed_url,
        source_url=expected["apple"]["source_url"],
    )
    assert subs.subscription_id_for(apple_rss) == expected["rss"]["subscription_id"]

    atom = parse_rss_feed(
        _fixture_text("atom.xml"),
        feed_url=expected["atom"]["feed_url"],
        source_url=expected["atom"]["url"],
    )
    _assert_discovery(atom, expected["atom"])

    podcast = parse_podcast_html(
        _fixture_text("xiaoyuzhou.html"), source_url=expected["xiaoyuzhou"]["url"]
    )
    xiaoyuzhou = subs.SubscriptionDiscovery(
        title=podcast.title,
        source="xiaoyuzhou",
        url=podcast.canonical_url,
        feed_url="",
        episodes=podcast.episodes,
    )
    _assert_discovery(xiaoyuzhou, expected["xiaoyuzhou"])


def test_shared_feed_golden_fixture_writes_deterministic_library_counts(tmp_path):
    expected = _expected()
    library_root = tmp_path / "Audio2TextLibrary"
    discovery = parse_rss_feed(
        _fixture_text("rss.xml"),
        feed_url=expected["rss"]["feed_url"],
        source_url=expected["rss"]["url"],
    )
    subscription = PodcastSubscription(
        id=expected["rss"]["subscription_id"],
        title=discovery.title,
        source=discovery.source,
        url=discovery.url,
        feed_url=discovery.feed_url,
        group_name=expected["library_write"]["group_name"],
        created_at="2026-05-31T00:00:00+08:00",
    )
    store = LibraryStore(library_root)
    store.upsert_subscription(subscription.to_json())
    store.upsert_episode(
        {
            "episode_id": expected["library_write"]["reused_episode_id"],
            "title": "Existing Metadata Title",
            "source": "podcast_rss",
            "source_url": "https://podcast.example/golden/rss/002",
            "canonical_url": "https://podcast.example/golden/rss/002",
            "series_name": "Golden RSS Show",
            "series_url": expected["rss"]["feed_url"],
            "published_at": "2026-05-29T00:00:00+00:00",
            "duration": "00:24:00",
            "audio_url": "https://media.example/golden/rss-002.m4a",
            "guid": "golden-rss-002",
            "subscription_id": subscription.id,
            "app_group": expected["library_write"]["group_name"],
            "title_updated_at": "2026-05-31T00:00:00+08:00",
        }
    )
    tombstone_root = library_root / "tombstones" / "episodes"
    tombstone_root.mkdir(parents=True, exist_ok=True)
    (tombstone_root / f"{expected['library_write']['tombstone_episode_id']}.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "audio2text.library.episode_tombstone",
                "episode_id": expected["library_write"]["tombstone_episode_id"],
                "subscription_id": subscription.id,
                "guid": "golden-rss-deleted",
                "deleted_at": "2026-05-31T00:00:00Z",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rows = import_subscription_episodes(subscription, discovery.episodes, library_root=library_root)
    episodes = store.load_episodes()
    manifest = json.loads((library_root / "manifest.json").read_text(encoding="utf-8"))

    assert _import_counts(rows) == {
        "imported_count": expected["library_write"]["imported_count"],
        "reused_count": expected["library_write"]["reused_count"],
        "skipped_count": expected["library_write"]["skipped_count"],
    }
    assert sorted(episode["episode_id"] for episode in episodes) == sorted(
        [
            expected["library_write"]["new_episode_id"],
            expected["library_write"]["reused_episode_id"],
        ]
    )
    assert manifest["subscription_count"] == 1
    assert manifest["episode_count"] == 2
    assert manifest["tombstone_count"] == 1
    assert (
        next(
            episode
            for episode in episodes
            if episode["episode_id"] == expected["library_write"]["reused_episode_id"]
        )["title"]
        == "Existing Metadata Title"
    )


def _assert_discovery(discovery, expected: dict) -> None:
    subscription_id = subs.subscription_id_for(discovery)
    assert discovery.title == expected["title"]
    assert discovery.source == expected["source"]
    assert discovery.url == expected["url"]
    assert discovery.feed_url == expected.get("feed_url", "")
    assert subscription_id == expected["subscription_id"]
    assert [_episode_id(episode, subscription_id) for episode in discovery.episodes] == expected[
        "episode_ids"
    ]


def _episode_id(episode, subscription_id: str) -> str:
    return stable_episode_id(
        {
            "source": episode.source,
            "subscription_id": subscription_id,
            "guid": episode.guid,
            "audio_url": episode.audio_url,
            "canonical_url": episode.canonical_url,
            "source_url": episode.source_url,
            "title": episode.title,
        }
    )


def _import_counts(rows: list[dict]) -> dict[str, int]:
    return {
        "imported_count": sum(
            1 for row in rows if not row.get("reused_existing") and not row.get("skipped")
        ),
        "reused_count": sum(
            1 for row in rows if row.get("reused_existing") and not row.get("skipped")
        ),
        "skipped_count": sum(1 for row in rows if row.get("skipped")),
    }


def _expected() -> dict:
    return json.loads(_fixture_text("expected.json"))


def _fixture_text(name: str) -> str:
    return (FIXTURE_ROOT / name).read_text(encoding="utf-8")


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURE_ROOT / name).read_bytes()
