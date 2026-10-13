# Import media and podcast sources

Use file import for media you already have, episode import for a Xiaoyuzhou conversation, and subscriptions for a series. Metadata, downloaded audio, and completed transcripts are different states.

| Source | Entry | First step |
| --- | --- | --- |
| Local audio/video | New Item or exec transcribe | Establish source/process local media |
| Xiaoyuzhou episode | App import or exec import | Fetch metadata, optionally audio |
| Xiaoyuzhou podcast | Add Subscription / subscriptions add | Resolve feed and episodes |
| Apple Podcasts show | Add Subscription | Resolve the show's feed |
| RSS | Add Subscription / subscriptions add | Read feed entries |

Exec import takes a Xiaoyuzhou episode URL, not an Apple Podcasts show or RSS URL. A file extension does not prove there is a decodable audio track; working FFmpeg is required.

## Local file

Choose New Item, file, and group, then local processing. CLI:

```bash
atot exec transcribe path/to/recording.m4a --language zh --local-only --json
atot exec transcribe path/to/recording.mp4 --job-dir path/to/work-dir \
  --language zh --local-only --json
```

Use different work directories for different sources. Default managed workflows associate media/work with episode IDs.

## Xiaoyuzhou episode

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --group-name Research --language zh --local-only --json
```

CLI import downloads/transcribes by default; local-only skips cloud summaries. Metadata/audio without ASR:

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only --json
```

Metadata without audio download:

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --data-only --no-download --json
```

Missing audio prevents ASR. Group-name is logical grouping; folder-name/audio-name change generated names. Force redownloads/replaces imported media deliberately.

## Subscribe to a series

Use a feed, Xiaoyuzhou podcast, or Apple Podcasts show in the subscription panel:

```bash
atot exec subscriptions add "https://example.org/podcast/rss.xml" \
  --group-name Research --limit 10 --json
atot exec subscriptions list --json
```

Replace the URL. Initial CLI import defaults to 10 metadata entries, not processing an entire series. See [queues](library.md).

## Verify the import

Open Overview for title, show, source URL, duration, and group; check audio readiness. Use returned paths and library status rather than guessing directories.

Separate source resolution/download failures from ASR. Providers can remove content or change access. Keep the URL/error, and avoid forcing a full reimport for every failure.

[Transcription →](transcription.md) · [Import troubleshooting →](troubleshooting.md#import-or-feed-refresh-fails)
