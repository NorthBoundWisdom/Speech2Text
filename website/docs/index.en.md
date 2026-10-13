---
title: SonaFolio · Too many podcasts. Read the highlights.
description: Turn your podcast backlog into readable transcripts and summaries. Read the full text or ask Codex to summarize first, then choose the passages worth exploring.
hide:
  - navigation
  - toc
---

<div class="sf-home" markdown>
<div class="sf-hero" markdown>
<div class="sf-hero-copy" markdown>

<p class="sf-eyebrow">Turn your podcast backlog into something you can read</p>

# Too many podcasts.<br>Read the highlights.

<p class="sf-lead">Turn podcasts into text. Read the full transcript, or let Codex summarize the ideas first and choose what deserves a closer read or listen. Keep the source and timestamps alongside your notes.</p>

<div class="sf-actions" markdown>
[Download SonaFolio](install.md){ .md-button .md-button--primary }
[Open the handbook](handbook.md){ .md-button }
</div>

<p class="sf-fine">Open source · Local transcription · Markdown documents<br>Validated primary workflow: Chinese podcasts on an Apple Silicon Mac</p>
</div>

<figure class="sf-product-shot" markdown>
[![SonaFolio's macOS subscription workspace with source filters, podcast subscriptions, and episodes waiting to be processed.](assets/screenshot-1.png)](assets/screenshot-1.png)
<figcaption>Real macOS workspace: organize subscriptions, select episodes, and follow processing. Click to view full size.</figcaption>
</figure>
</div>

<div class="sf-principles" markdown>
<div markdown>

### Read a long conversation as text

Local ASR produces a complete transcript, readable Markdown, and timed subtitles. Read the passages that matter to you; QA and correction records provide review clues, and timestamps take you back to the recording.

[Transcription and review →](guides/transcription.md)
</div>
<div markdown>

### Give your podcast backlog a home

Subscribe to RSS feeds and import episodes you have not had time to hear. Sources, transcripts, and summaries stay connected. Use groups, favorites, and reading state to work through your collection.

[Library and subscriptions →](guides/library.md)
</div>
<div markdown>

### Let Codex read and summarize for you

Through MCP, Codex reads the complete transcript and QA, then writes back ideas, evidence, and conclusions. Start with the summary and decide where to explore further. No SonaFolio model API key is required.

[Set up Codex write-back →](guides/agent-summary.md)
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">A workspace centered on the episode</p>

## Keep the source. Get to the reading.

<figure class="sf-wide-shot" markdown>
[![SonaFolio's macOS library showing groups, an episode list, and an Overview with podcast, date, duration, and source links.](assets/screenshot-3.png)](assets/screenshot-3.png)
<figcaption>Overview preserves the source; Summary and Transcript show existing reading documents. These are current-source screenshots; <a href="install/#release-and-current-source">released installers can have an earlier interface</a>.</figcaption>
</figure>

<div class="sf-feature-pair" markdown>
<div markdown>

### Make room for what you are reading

Choose a source on the left, an episode in the middle, and read on the right. Current source lets you drag the two dividers or hide either column independently. Restore them through the toolbar or View menu.

[Tour the workspace →](guides/workspace.md)
</div>
<div markdown>

### Language choices with clear boundaries

The validated workflow focuses on Chinese podcasts. Current source also offers spoken-language checkboxes and a separate summary output language. Available language options do not establish validation parity with Chinese.

[Understand language settings →](guides/languages.md)
</div>
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">From a backlog to useful notes</p>

## Three steps, with the source intact.

<div class="sf-steps" markdown>
<div markdown>

### 01 / Import and choose

Import local media or a Xiaoyuzhou episode. Manage RSS, Xiaoyuzhou podcast, or Apple Podcasts show subscriptions. Refresh metadata first, then choose the recordings to download and process.

[Import sources →](guides/import.md)
</div>
<div markdown>

### 02 / Create the full text locally

Prepare the model and media tools, select the Chinese language hint, and let ASR produce the transcript and QA. Read it directly or give it to Codex, retaining review evidence for names, terminology, and numbers.

[Prepare models →](models.md) · [Review QA →](guides/quality.md)
</div>
<div markdown>

### 03 / Summarize first, explore selectively

Codex reads the transcript and publishes a summary with source timestamps. See the highlights, then open related text or audio. Optional iCloud Drive sharing brings your reading library to iPhone and iPad.

[Agent write-back →](guides/agent-summary.md) · [Read on iOS →](guides/ios.md)
</div>
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">Clear outputs you can take with you</p>

## Keep more than a model response.

| Your goal | What you keep | Learn more |
| --- | --- | --- |
| Read a conversation directly | Readable Markdown and timestamped text | [Transcription](guides/transcription.md) |
| Provide captions to a player or editor | SRT export; work artifacts also retain VTT | [Subtitles](guides/subtitles.md) |
| Collect ideas and evidence | Agent-authored or explicitly requested cloud summaries | [Summary paths](handbook.md#choose-a-summary-path) |
| Find passages worth checking | QA, corrections, entity review, and repair plans | [Quality](guides/quality.md) |
| Back up your collection | JSON episode records and Markdown documents | [Storage](guides/storage.md) |

The full transcript is stored separately from the summary. The library offers organization and reading state; it does not currently include cross-episode semantic Q&A or production speaker diarization.
</div>

<div class="sf-section sf-platforms" markdown>
<p class="sf-eyebrow">Choose your setup</p>

## One library. Several ways in.

| Platform | Capabilities and boundaries | Start here |
| --- | --- | --- |
| **macOS / Apple Silicon** | SwiftUI app, Qt client, and CLI; the validated Chinese workflow uses MLX Whisper | [macOS installation](install.md#macos-apple-silicon) |
| **Windows / x64** | Qt client and CLI; faster-whisper needs separate CUDA setup or explicit CPU mode | [Windows installation](install.md#windows-x64) |
| **iPhone / iPad** | Source-built reader and subscription manager; no on-device ASR | [iOS guide](guides/ios.md) |
| **Linux / x86_64** | Qt AppImage client; no promoted stable Linux ASR backend | [Linux client](install.md#linux-x86_64) |

<p class="sf-fine">Installers contain the client; model weights are prepared manually. Qt processing needs a separately configured CLI and FFmpeg. Signing, runtime boundaries, and capabilities follow the corresponding release notes.</p>

[Download and check your setup](install.md){ .md-button }
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">Start with the task in front of you</p>

## A handbook for the complete workflow.

<div class="sf-guide-grid" markdown>
<div markdown>

### Make your first transcript

Prepare the client, tools, and model. Test a short Chinese recording before starting long episodes.

[First transcript walkthrough →](quick-start.md)
</div>
<div markdown>

### Catch up without hearing every episode

Choose a batch, transcribe it, and read the text or request summaries. Save listening time for the passages that interest you.

[Subscriptions and queues →](guides/library.md)
</div>
<div markdown>

### Start with the summary

Connect MCP and let Codex read the complete source. Begin with its notes, then follow timestamps. Existing summaries are replaced only on an explicit regeneration request.

[Connect and write back →](guides/agent-summary.md)
</div>
<div markdown>

### Diagnose a setup or task failure

Separate the client, CLI, media tools, model, GPU runtime, and optional cloud configuration.

[Troubleshoot by symptom →](guides/troubleshooting.md)
</div>
</div>
</div>

<div class="sf-closing" markdown>
<div markdown>

## Know where your data goes.

Local ASR does not upload audio. Imports contact source services. Optional iCloud sync, agent summaries, and cloud APIs have distinct boundaries that you choose to enable.

[Privacy and data flow →](guides/privacy.md)
</div>
<div class="sf-closing-links" markdown>

[User handbook](handbook.md)

[CLI and automation](guides/cli.md)

[Source on GitHub](https://github.com/NorthBoundWisdom/sonafolio)

[Report a problem](https://github.com/NorthBoundWisdom/sonafolio/issues)
</div>
</div>

<!-- SONAFOLIO_BUILD -->
</div>
