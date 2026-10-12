# Your first transcript

Follow the [installation guide](install.md) to prepare the CLI, FFmpeg, and model files. Examples use
an activated macOS environment; Windows can activate its environment or use the complete executable
path shown in that guide.

## 1. Check the runtime

```bash
atot doctor
atot models
```

Resolve missing models, backends, media tools, or CUDA dependencies first. Local transcription and
library browsing do not need a model API key.

## 2. Choose an input

Local media:

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only
```

A Xiaoyuzhou episode:

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --local-only
```

Replace the episode ID with a real source ID. Link imports download audio and need network access;
local ASR does not upload it. The macOS app also imports links or files into a chosen group. Default
processing and primary shortcuts execute local transcription and QA; cloud summaries are opt-in.

## 3. Read and inspect

The command reports its work directory. Use it for QA and repair planning:

```bash
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
atot exec library status --json
```

Outputs include `transcript.readable.md`, `transcript.timestamped.md`, subtitles, `qa.json`, and
`corrections.json`. QA identifies possible issues; it does not guarantee a word-perfect transcript.
Check important content against the original audio.

Published library documents are `documents/transcript.md` and `documents/summary.md`.

## 4. Summarize

The ASR pipeline does not automatically create an agent summary. Connect Codex, read the complete
transcript and QA, and publish a model-authored summary with current document hashes.

[Set up agent summaries →](guides/agent-summary.md)
