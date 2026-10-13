# SonaFolio handbook

Turn podcast episodes and local media into readable transcripts, subtitles, and summaries. When your backlog grows, read the transcript directly or let Codex summarize first, then choose the passages worth reading or hearing in depth.

## Two reading entrypoints

- **Read the full text:** import and transcribe locally, then open Transcript at the passages you care about.
- **Start with a summary:** let Codex read the complete transcript and QA and publish its notes; start in Summary and follow timestamps when you need context.

The complete transcript remains the source layer. Software and the agent can do that reading for you; you do not need to hear the entire episode or read every line before requesting a summary. Check important conclusions against their sources when needed.

## Before you begin

Local transcription needs no model API key. A working interface and a ready ASR runtime are separate: CLI, FFmpeg, backend, and model files must be available.

The validated primary workflow is **Apple Silicon Mac + MLX Whisper + large-v3-turbo + Chinese podcasts**. Windows has its own runtime setup. Other language options are configurable, but do not have a claim of validation parity with Chinese.

The handbook describes current source. Published **v0.9.0** installers predate adjustable/collapsible columns, the compact toolbar, and new language selectors. Build current source for those features. Screenshots show a real macOS source build with original-language podcast content. See [release differences](install.md#release-and-current-source).

## Find your task

| Goal | Suggested route |
| --- | --- |
| First Chinese transcript | [Install](install.md) → [Models](models.md) → [First transcript](quick-start.md) |
| Learn the app | [Workspace](guides/workspace.md) → [Import](guides/import.md) → [Transcription](guides/transcription.md) |
| Process a backlog | [Library](guides/library.md) → [Transcription](guides/transcription.md) → [QA](guides/quality.md) |
| Use Codex without a SonaFolio key | [MCP summaries](guides/agent-summary.md) → [Languages](guides/languages.md) |
| Use your own endpoint | [Cloud summaries](guides/cloud-summary.md) → [Settings](guides/settings.md) |
| Make subtitles | [Subtitles](guides/subtitles.md) → [Languages](guides/languages.md) |
| Read on a phone or tablet | [Library](guides/library.md) → [iOS](guides/ios.md) |
| Back up or move data | [Storage](guides/storage.md) → [Privacy](guides/privacy.md) |
| Automate | [CLI](guides/cli.md) → [QA](guides/quality.md) |
| Diagnose a failure | [Troubleshooting](guides/troubleshooting.md) → [FAQ](faq.md) |

## Understand the layers

**Source and media.** Imports preserve metadata and source URLs. Audio and prepared media stay in the local data root. Feed refresh does not mean an episode has been downloaded or transcribed.

**Transcription and review.** ASR creates text, timing, subtitles, QA, and corrections. It is evidence to check against audio. A summary does not replace the full transcript, and passing QA does not mean word-perfect recognition.

**Library and notes.** The authoritative library stores records, Markdown, groups, and state. Optional iCloud shares it with the iOS reader; weights and work caches stay on the processing computer.

## Choose a summary path {#choose-a-summary-path}

| | Codex / MCP | Optional cloud API |
| --- | --- | --- |
| Author | The current conversation model | Your endpoint's model |
| SonaFolio API key | Not needed | Endpoint, model, and key needed |
| Data read/sent | Transcript and QA enter the agent conversation | Text/context is sent to the API |
| Publication | Versioned write_summary | Explicit cloud workflow |
| Existing summary | Explicit regeneration required | Deliberate regeneration action |
| Setup | [MCP](guides/agent-summary.md) | [Cloud](guides/cloud-summary.md) |

Local ASR does not automatically create Codex notes. Check both summary paths for missing context, unsupported additions, and uncertainty.

## First-run checklist

1. Install the client and CLI; run `atot doctor`.
2. Prepare the correct model files under the data-root `model/`.
3. Select Chinese and test a short file locally.
4. Inspect names, numbers, quotations, and key judgments.
5. Choose MCP or cloud; cloud configuration can stay empty for MCP.
6. Decide between local/iCloud library storage and arrange an independent backup.

Use the top language controls to switch between the corresponding Chinese and English page. Search accepts text, commands, configuration keys, and error messages. UI labels and identifiers retain their real names.

[Begin with installation →](install.md)
