# Local Chinese transcription

A local task prepares audio, chunks it, runs ASR, merges results, applies auditable corrections, and writes reading documents and QA. Local-only requires no model API key and does not upload audio to a summary service.

The validated primary path uses Apple Silicon, MLX Whisper, and large-v3-turbo for Chinese podcasts. These examples explicitly select zh to reproduce it. Other language choices do not imply the same validation evidence.

## Before starting

1. Confirm audio exists; subscription metadata can still show Audio pending.
2. Run doctor for backend, weights, and tools.
3. Select model/profile and [spoken language](languages.md).
4. Test a short recording locally first.

## App and CLI

Choose **Transcribe locally only**, or Command-Return in Swift. An explicit local reprocess uses Command-Shift-Return. Follow task stages; a download or chunk completing is not final task success.

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
```

Use language auto to override stored hints. Current source supports repeated language flags; omission uses saved settings. ASR preserves speech rather than applying summary/subtitle translation language.

## Work artifacts

| File | Purpose |
| --- | --- |
| transcript.corrected.txt | Faithful corrected text |
| transcript.readable.md | Deterministic reading layout |
| transcript.timestamped.md | Locate passages |
| transcript.srt / transcript.vtt | Timed captions |
| qa.json | Automated findings |
| corrections.json | Change audit |
| review.json / entity_consistency.json | Terminology/entity review |
| run.json | Source, model/backend, language requests, cache identity, evidence |

The library receives documents/transcript.md. Detailed evidence stays in the returned work directory used for QA/repair.

## Long audio and chunks

Auto uses fixed windows for short audio and silence-aware boundaries for longer recordings. Start with defaults. For controlled experiments, durations are seconds:

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only \
  --chunking smart --chunk-length 900 --max-chunk-length 1200 --overlap 10
```

| Option | Meaning |
| --- | --- |
| chunking auto/fixed/smart | Boundary strategy |
| chunk-length | Target duration |
| max-chunk-length | Smart maximum |
| silence-threshold | Silence threshold |
| min-silence | Minimum boundary silence |
| overlap | Context between chunks |

Overlap provides context; merging chooses retained segments. Do not concatenate overlapped transcripts as independent passages.

## Caching and reprocessing

Source, model, decode parameters, selected hints, and effective prompt participate in cache identity. Saving settings does not rewrite existing documents. Explicit rebuild:

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --force
```

Force is the current option, not force-transcribe. Reprocessing can replace work and the published transcript; back up versions you need. An older summary may no longer describe the new transcript, so check it and request regeneration deliberately.

## Context and corrections

Use prompt-file/glossary-file for explicit context and repeatable rule-pack for shared rules. Corrections should be narrow and auditable, not a global replacement derived from a noisy result.

Current source avoids default Chinese-only prompts in auto/mixed/non-Chinese runs while preserving explicit custom context. QA guides review; verify important names, numbers, and quotes against audio.

[QA and repair →](quality.md) · [Subtitles →](subtitles.md)
