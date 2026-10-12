---
title: SonaFolio · Keep what you hear
description: Local-first podcast transcription and a portable knowledge library. Turn audio into readable transcripts, summaries, and Markdown.
hide:
  - navigation
  - toc
---

<div class="sf-home" markdown>
<div class="sf-hero" markdown>
<div class="sf-hero-copy" markdown>

<p class="sf-eyebrow">Good ideas deserve a place to stay</p>

# Turn what you hear<br>into a library of your own.

<p class="sf-lead">SonaFolio organizes podcasts and media into readable transcripts, subtitles, and summaries.<br>Transcribe on your computer. Build your library. Keep reading on iPhone and iPad.</p>

<div class="sf-actions" markdown>
[Get started](install.md){ .md-button .md-button--primary }
[View source](https://github.com/NorthBoundWisdom/sonafolio){ .md-button }
</div>

<p class="sf-fine">Open source · Local first · macOS / Windows · iOS reader · Linux Qt client</p>
</div>

<div class="sf-preview" role="img" aria-label="Illustrated product layout with an episode list, timestamped transcript, and summary. Not actual episode content.">
<div class="sf-preview-bar"><span class="sf-dots">● ● ●</span><span>SonaFolio</span><span class="sf-preview-label">Illustration</span></div>
<div class="sf-preview-body">
<div class="sf-preview-library"><span class="sf-caption">MY LIBRARY</span><strong>A home for ideas</strong><span class="sf-selected">From sound to knowledge</span><span>A conversation to remember</span><span>Keeping a good idea</span><span class="sf-library-bottom">3 examples · Markdown</span></div>
<div class="sf-preview-document"><div class="sf-preview-tabs"><span>Overview</span><b>Summary</b><span>Transcript</span></div><span class="sf-caption">PODCAST NOTES / EXAMPLE</span><strong>From sound to knowledge</strong><p>Hearing a good idea is a beginning.<br>Keep the source. Make sense of it.</p><div class="sf-quote"><span>00:12:08</span><p>Return to the original context whenever you need it.</p></div><span class="sf-caption">KEY POINTS</span><p class="sf-preview-bullets">Keep timestamps for reference<br>Save text you can reuse<br>Choose how to summarize</p></div>
</div>
</div>
</div>

<div class="sf-principles" markdown>
<div markdown>

### Transcribe locally

MLX Whisper on Apple Silicon, faster-whisper on Windows. Local ASR processes your audio; you manage the model files.
</div>
<div markdown>

### Build your library

Keep episodes, transcripts, summaries, favorites, and groups together. Optional iCloud Drive sync lets Mac and iOS read the same library.
</div>
<div markdown>

### Summarize with an agent

Let Codex read transcripts and QA through MCP, then summarize with its current model and write back. No SonaFolio model API key is required.
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">From audio to notes you can revisit</p>

## Listening is just the beginning.

<div class="sf-steps" markdown>
<div markdown>

### 01 / Import

Choose local media or import a Xiaoyuzhou episode. Organize feeds with RSS subscriptions and manual refresh.
</div>
<div markdown>

### 02 / Transcribe and review

Generate readable text, subtitles, and QA reports. Inspect timestamps, corrections, and problem windows; apply targeted repair when needed.
</div>
<div markdown>

### 03 / Summarize and keep

Publish agent-authored summaries with version checks. Preserve the full source and organize it with favorites, groups, and reading state.
</div>
</div>

[Make your first transcript →](quick-start.md)
</div>

<div class="sf-section sf-platforms" markdown>
<p class="sf-eyebrow">Choose your way in</p>

## One library. Several ways to use it.

| Platform | Current capabilities |
| --- | --- |
| **macOS / Apple Silicon** | Native SwiftUI app, Qt client, and `atot` CLI; stable MLX Whisper transcription |
| **Windows / x64** | Qt client and `atot` CLI; faster-whisper requires separate runtime setup |
| **iPhone / iPad** | Source-built library reader and subscription manager; no on-device ASR |
| **Linux / x86_64** | Qt AppImage client; no stable Linux ASR backend |

<p class="sf-fine">Qt installers include the client and Qt runtime. Configure the CLI, FFmpeg, and models separately. macOS packages currently use ad-hoc signatures without notarization. Published versions are listed in GitHub Releases.</p>

[Download and install](install.md){ .md-button }
</div>

<div class="sf-closing" markdown>
<div markdown>

## Your content stays yours.

The library uses JSON and Markdown; subtitles export to SRT/VTT. Local ASR does not upload audio. Optional iCloud, agent summaries, and cloud APIs have their own data boundaries.

[Understand privacy and data →](guides/privacy.md)
</div>
<div class="sf-closing-links" markdown>

[User handbook](quick-start.md)

[CLI and automation](guides/cli.md)

[Common questions](faq.md)

[Contribute](development.md)
</div>
</div>

<!-- SONAFOLIO_BUILD -->
</div>
