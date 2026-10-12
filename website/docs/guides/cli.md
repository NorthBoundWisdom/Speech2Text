# CLI and automation

The product is SonaFolio; the CLI remains `atot`. No arguments open the TUI. Scripts use `atot exec ...`.

```bash
atot --help
atot exec --help
atot doctor
atot models
atot exec transcribe path/to/audio.m4a --language zh --local-only
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --local-only
atot exec srt path/to/video.mp4 --language zh
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
atot exec library status --json
atot status --task-id <task-id>
atot mcp
```

Use `--json` where the command provides it; consult individual help pages. Old top-level
`atot transcribe` and `atot import-xiaoyuzhou` aliases were removed in CLI v2.

## Configure

Settings live in the data-root `config.toml`:

```bash
atot config list
atot config get local.asr_model
```

The default local model is `large-v3-turbo`. Experimental backends need quality gates before promotion.

## Schedule or connect an agent

External schedulers can invoke `exec`. MCP supports restricted library reading and summary writes.
`atot serve --stdio` is the GUI's internal JSON service, not MCP.

The optional HTTP service requires loopback and an independent token and exposes broader workflows.
Use MCP for ordinary agent summaries; HTTP need not be enabled.

[Complete CLI reference](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.md)
