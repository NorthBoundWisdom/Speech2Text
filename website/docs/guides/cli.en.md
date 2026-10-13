# CLI and automation

SonaFolio keeps the atot command. No arguments opens TUI; scripts use exec. Replace example paths/IDs.

## Checks/help

```bash
atot --help
atot exec --help
atot doctor
atot models
atot config path
atot config inspect --json
```

Individual help is authoritative. Old top-level transcribe/import-xiaoyuzhou aliases were removed.

## Validated Chinese entrypoints

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only --json
atot exec transcribe path/to/episode.m4a --language zh --local-only --force
```

Force rebuilds; see [transcription](transcription.md) for replacement/backup. Current source permits repeatable languages without multilingual validation parity.

## Captions and review

```bash
atot exec srt path/to/video.mp4 --language zh --json
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
```

Inspect plans before explicit repair. Captions need overwrite when a destination exists.

## Feeds/status

```bash
atot exec subscriptions add "https://example.org/feed.xml" --group-name Research --json
atot exec subscriptions list --json
atot exec subscriptions refresh --all --json
atot exec library status --json
atot status --task-id <task-id> --json
atot resume <task-id> --json
```

Resume currently queries persisted task/session state, not automatic ASR re-execution. Start the workflow deliberately with cache/force policy when retrying.

## Persistent and one-run choices

```bash
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config set workflow.default_cloud_summary false
atot -c 'local.languages=["zh"]' exec transcribe path/to/audio.m4a --local-only
```

Empty arrays mean auto; legacy local.language remains readable. Task overrides are not persisted config set. See [settings](settings.md).

## JSON and events

Json-capable commands return structured results; watch streams events. Check exit code/final success and every batch item, not one progress event:

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json --watch
```

With events mixed into stdout, parse lines/protocol rather than one whole JSON object. External tools schedule jobs; metadata refresh does not run an audio queue automatically.

## Service boundaries

MCP is restricted library access. Serve stdio is the GUI JSON protocol, not MCP. Optional loopback HTTP requires an independent token and exposes broader operations; ordinary agent notes need only MCP.

[README reference](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.en.md) · [MCP](agent-summary.md)
