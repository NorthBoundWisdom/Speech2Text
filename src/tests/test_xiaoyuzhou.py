import json
from datetime import datetime, timezone

from atot import cli
from atot import workflow_service
from atot.xiaoyuzhou import (
    XiaoyuzhouEpisode,
    _audio_filename,
    _strip_episode_prefix,
    episode_topic_markdown,
    import_xiaoyuzhou_episode,
    parse_episode_html,
    parse_podcast_html,
)


HTML = """
<html>
<head>
<link rel="canonical" href="https://www.xiaoyuzhoufm.com/episode/abc"/>
<meta property="og:image" content="https://image.example/cover.png"/>
<script name="schema:podcast-show" type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "PodcastEpisode",
  "url": "https://www.xiaoyuzhoufm.com/episode/abc",
  "name": "001. 对话「日行迹」创始人孙天祥｜当AI自动写出顶会论文",
  "datePublished": "2026-05-20T16:02:32.229Z",
  "timeRequired": "PT95M",
  "description": "本期导读\\n主播：张伟楠\\n嘉宾：孙天祥",
  "associatedMedia": {
    "@type": "MediaObject",
    "contentUrl": "https://media.xyzcdn.net/show/episode.m4a"
  },
  "partOfSeries": {
    "@type": "PodcastSeries",
    "name": "AI青年志",
    "url": "https://www.xiaoyuzhoufm.com/podcast/show"
  }
}
</script>
</head>
</html>
"""


def test_parse_episode_html_extracts_json_ld_metadata():
    episode = parse_episode_html(
        HTML, source_url="https://www.xiaoyuzhoufm.com/episode/abc?s=share"
    )

    assert episode.title.startswith("001. 对话")
    assert episode.series_name == "AI青年志"
    assert episode.audio_url == "https://media.xyzcdn.net/show/episode.m4a"
    assert episode.date_folder == "0521"
    assert episode.local_published_at.hour == 0
    assert episode.image_url == "https://image.example/cover.png"


def test_parse_episode_html_handles_reordered_meta_and_multiple_json_ld():
    html = """
    <html><head>
      <meta content="https://image.example/reordered.png" property="og:image">
      <link href="https://www.xiaoyuzhoufm.com/episode/reordered" rel="canonical">
      <script type="application/ld+json">{"@type": "BreadcrumbList"}</script>
      <script data-x="1" type="application/ld+json">
      [{
        "@type": "PodcastEpisode",
        "name": "Vol.12 | 属性顺序测试",
        "datePublished": "2026-05-20T16:02:32.229Z",
        "description": "测试",
        "associatedMedia": {"contentUrl": "https://media.example/audio"},
        "partOfSeries": {"name": "测试节目"}
      }]
      </script>
    </head></html>
    """

    episode = parse_episode_html(
        html, source_url="https://www.xiaoyuzhoufm.com/episode/reordered?s=share"
    )

    assert episode.title == "Vol.12 | 属性顺序测试"
    assert episode.canonical_url == "https://www.xiaoyuzhoufm.com/episode/reordered"
    assert episode.image_url == "https://image.example/reordered.png"
    assert episode.audio_url == "https://media.example/audio"


def test_parse_podcast_html_extracts_recent_episodes_from_next_data():
    html = """
    <html><head>
      <link rel="canonical" href="https://www.xiaoyuzhoufm.com/podcast/show">
      <script id="__NEXT_DATA__" type="application/json">
      {
        "props": {
          "pageProps": {
            "podcast": {
              "pid": "show",
              "title": "测试栏目",
              "author": "主播",
              "description": "栏目介绍",
              "image": {"picUrl": "https://image.example/show.png"},
              "episodes": [{
                "eid": "episode1",
                "pid": "show",
                "title": "001. 栏目第一集",
                "description": "第一集 shownotes",
                "duration": 600,
                "pubDate": "2026-05-28T00:00:00.000Z",
                "enclosure": {"url": "https://media.example/episode1.m4a"}
              }]
            }
          }
        }
      }
      </script>
    </head></html>
    """

    podcast = parse_podcast_html(html, source_url="https://www.xiaoyuzhoufm.com/podcast/show")

    assert podcast.title == "测试栏目"
    assert len(podcast.episodes) == 1
    assert podcast.episodes[0].title == "001. 栏目第一集"
    assert podcast.episodes[0].canonical_url == "https://www.xiaoyuzhoufm.com/episode/episode1"
    assert podcast.episodes[0].audio_url == "https://media.example/episode1.m4a"


def test_topic_markdown_contains_transcription_context():
    episode = XiaoyuzhouEpisode(
        source_url="https://example/source",
        canonical_url="https://example/canonical",
        title="咖啡时间：揭秘咖啡店里，一杯创意咖啡的诞生",
        series_name="大小电波",
        series_url="https://example/show",
        published_at=datetime(2026, 5, 26, 16, 39, tzinfo=timezone.utc),
        duration="PT67M",
        description="本期嘉宾：Bryce\\n关键词：创意咖啡、策展式咖啡馆",
        audio_url="https://media.example/audio.m4a",
    )

    markdown = episode_topic_markdown(episode)

    assert "# 咖啡时间" in markdown
    assert "- Podcast: 大小电波" in markdown
    assert "- Published at: 2026-05-27 00:39:00 +0800" in markdown
    assert "关键词：创意咖啡" in markdown


def test_strip_episode_prefix():
    assert _strip_episode_prefix("001. 对话孙天祥") == "对话孙天祥"
    assert _strip_episode_prefix("Vol.303 | 咖啡时间") == "咖啡时间"
    assert _strip_episode_prefix("咖啡时间") == "咖啡时间"


def test_audio_filename_defaults_to_m4a_when_audio_url_has_no_suffix():
    episode = XiaoyuzhouEpisode(
        source_url="https://example/source",
        canonical_url="https://example/canonical",
        title="Vol.303 | 咖啡时间",
        series_name="大小电波",
        series_url="https://example/show",
        published_at=datetime(2026, 5, 26, 16, 39, tzinfo=timezone.utc),
        duration="PT67M",
        description="",
        audio_url="https://media.example/audio?id=123",
    )

    assert _audio_filename(episode, None) == "咖啡时间.m4a"


def test_import_xiaoyuzhou_default_runs_transcription(monkeypatch, tmp_path, capsys):
    from atot.config_v2 import set_config_value
    set_config_value("library.storage", "local")
    audio_path = tmp_path / "process" / "0527" / "episode" / "episode.m4a"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"audio")
    calls = {}

    class FakeResult:
        def __init__(self, audio_path):
            self.audio_path = audio_path

        def to_json(self):
            return {
                "episode_dir": str(audio_path.parent),
                "audio_path": str(audio_path),
                "topic_path": str(audio_path.parent / "主题.md"),
                "metadata_path": str(audio_path.parent / "episode.json"),
                "downloaded": False,
            }

    def fake_import(url, **kwargs):
        calls["import"] = {"url": url, **kwargs}
        return FakeResult(audio_path)

    def fake_run(options):
        calls["transcribe"] = options
        return {
            "job_dir": str(audio_path.parent / "output"),
            "runtime_seconds": 1.0,
            "output_files": {"run.json": str(audio_path.parent / "output" / "run.json")},
            "review": {},
            "model": options.model,
        }

    monkeypatch.setattr(workflow_service, "import_xiaoyuzhou_episode", fake_import)
    monkeypatch.setattr(workflow_service, "run_transcription", fake_run)

    rc = cli.main(
        [
            "exec",
            "import",
            "https://www.xiaoyuzhoufm.com/episode/abc",
            "--no-download",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert calls["import"]["download"] is False
    assert calls["transcribe"].input_path == audio_path
    assert calls["transcribe"].model == "large-v3-turbo"
    assert '"transcription"' in output


def test_import_xiaoyuzhou_data_only_does_not_transcribe(monkeypatch, tmp_path):
    audio_path = tmp_path / "episode.m4a"
    calls = {"transcribe": 0}

    class FakeResult:
        def __init__(self, audio_path):
            self.audio_path = audio_path

        def to_json(self):
            return {
                "episode_dir": str(tmp_path),
                "audio_path": str(audio_path),
                "topic_path": str(tmp_path / "主题.md"),
                "metadata_path": str(tmp_path / "episode.json"),
                "downloaded": True,
            }

    monkeypatch.setattr(
        workflow_service,
        "import_xiaoyuzhou_episode",
        lambda *args, **kwargs: FakeResult(audio_path),
    )
    monkeypatch.setattr(
        workflow_service, "run_transcription", lambda options: calls.update(transcribe=1)
    )

    rc = cli.main(["exec", "import", "https://www.xiaoyuzhoufm.com/episode/abc", "--data-only"])

    assert rc == 0
    assert calls["transcribe"] == 0


def test_import_xiaoyuzhou_reuses_existing_audio_by_audio_url(monkeypatch, tmp_path):
    process_dir = tmp_path / "process"
    episode_dir = process_dir / "0521" / "existing"
    episode_dir.mkdir(parents=True)
    audio_path = episode_dir / "existing.m4a"
    audio_path.write_bytes(b"audio")
    metadata_path = episode_dir / "episode.json"
    metadata_path.write_text(
        '{"audio_url":"https://media.example/same.m4a","audio_path":"existing.m4a"}',
        encoding="utf-8",
    )
    calls = {"download": 0}
    episode = XiaoyuzhouEpisode(
        source_url="https://www.xiaoyuzhoufm.com/episode/new",
        canonical_url="https://www.xiaoyuzhoufm.com/episode/new",
        title="新链接同音频",
        series_name="测试节目",
        series_url="https://www.xiaoyuzhoufm.com/podcast/show",
        published_at=datetime(2026, 5, 20, 16, 2, tzinfo=timezone.utc),
        duration="PT10M",
        description="",
        audio_url="https://media.example/same.m4a",
    )

    monkeypatch.setattr("atot.xiaoyuzhou.fetch_episode", lambda _url: episode)
    monkeypatch.setattr(
        "atot.xiaoyuzhou.download_audio", lambda *args, **kwargs: calls.update(download=1)
    )

    result = import_xiaoyuzhou_episode(
        "https://www.xiaoyuzhoufm.com/episode/new", process_dir=process_dir
    )

    assert result.audio_path == audio_path
    assert result.episode_dir == episode_dir
    assert result.downloaded is False
    assert result.reused_existing is True
    assert result.to_json()["reused_existing"] is True
    assert calls["download"] == 0


def test_import_xiaoyuzhou_can_use_custom_process_group(monkeypatch, tmp_path):
    process_dir = tmp_path / "process"
    episode = XiaoyuzhouEpisode(
        source_url="https://www.xiaoyuzhoufm.com/episode/new",
        canonical_url="https://www.xiaoyuzhoufm.com/episode/new",
        title="自定义分组测试",
        series_name="测试节目",
        series_url="https://www.xiaoyuzhoufm.com/podcast/show",
        published_at=datetime(2026, 5, 20, 16, 2, tzinfo=timezone.utc),
        duration="PT10M",
        description="",
        audio_url="https://media.example/custom.m4a",
    )

    monkeypatch.setattr("atot.xiaoyuzhou.fetch_episode", lambda _url: episode)
    monkeypatch.setattr(
        "atot.xiaoyuzhou.download_audio",
        lambda _url, output_path, **_kwargs: output_path.write_bytes(b"audio") or True,
    )

    result = import_xiaoyuzhou_episode(
        "https://www.xiaoyuzhoufm.com/episode/new",
        process_dir=process_dir,
        group_name="Research Notes",
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))

    assert result.episode_dir == process_dir / "Research-Notes" / "自定义分组测试"
    assert result.audio_path.exists()
    assert metadata["app_status"] == "link"
    assert metadata["app_read"] is False
    assert metadata["app_star"] is False
    assert metadata["app_status_updated_at"]
