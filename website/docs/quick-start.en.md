# Your first Chinese transcript

Test a short, clear Chinese recording before processing long episodes or a subscription backlog. Complete [installation](install.md) and [models/tools](models.md) first.

## 1. Check readiness

```bash
atot doctor
atot models
```

Resolve required CLI, backend, model, and FFmpeg/ffprobe failures. Optional Cloud Summary can remain unconfigured for local ASR and MCP.

Use **Settings → Overview** in the native app. Qt offers Doctor and an external CLI path. See [troubleshooting](guides/troubleshooting.md) if app and terminal disagree.

## 2. Import one source

Choose **New Item** (`Command-N`) in the native app and select local media or a supported episode URL and group. Import establishes the source; processing creates text. Subscription metadata alone does not mean audio or a transcript exists.

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --language zh --local-only --json
```

Replace paths and IDs. URL imports contact the source for metadata/media; ASR then runs locally. Apple Podcasts show and RSS URLs use subscriptions; `exec import` takes a Xiaoyuzhou episode URL.

## 3. Select the Chinese hint

In current source, select **Chinese / Mandarin** under **Settings → Local ASR → Transcription Languages** to reproduce the validated workflow.

No selection means auto; multiple selections use auto plus mixed-language hints and retain original speech. New configurations default to auto, without claiming equal validation for other languages. Explicit old choices remain.

v0.9.0 lacks the new checkboxes and output selector but accepts a single `--language zh`. See [languages](guides/languages.md).

## 4. Run locally

Select **Transcribe locally only**, or `Command-Return`. Follow the stage and log: download completion, one ASR chunk, and final success are different states. Do not repeatedly start the same long task.

The CLI examples perform transcription and QA with `--local-only`, skipping optional cloud summaries and requiring no model key.

## 5. Read and check

Open **Transcript**; **Overview** preserves metadata. **Summary** has content after a summary workflow runs. Use the actual returned work directory:

```bash
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
atot exec library status --json
```

| Output | Purpose |
| --- | --- |
| transcript.readable.md | Reading text |
| transcript.timestamped.md | Locate source passages |
| transcript.srt / transcript.vtt | Captions |
| qa.json | Automated findings |
| corrections.json | Change audit |
| Library documents/transcript.md | Published reading document |

Check important names, numbers, judgments, and quotations against audio. QA is not an accuracy guarantee. Inspect a repair plan before rerunning windows.

## 6. Read a summary when useful

Choose [Codex/MCP](guides/agent-summary.md), using the current conversation model without a SonaFolio key, or [cloud API summaries](guides/cloud-summary.md). Have the agent read the full source, retain timestamps, and disclose uncertainty. You can start your own reading with its summary.

After the first run, try [subscriptions](guides/library.md), [subtitles](guides/subtitles.md), or [iOS reading](guides/ios.md).
