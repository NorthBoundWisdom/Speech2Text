---
name: audio2text-transcribe
description: Import and locally transcribe podcast or audio sources with this repository's SonaFolio CLI, then report QA and optionally create an agent-authored summary.md. Use when a user provides a Xiaoyuzhou episode URL, Apple Podcasts episode URL, direct audio URL, or local audio/video file and wants an imported episode, transcript, subtitles, or concise transcription summary.
---

# SonaFolio Transcribe

Use this skill inside the SonaFolio repository. Prefer the installed CLI from the configured data
root; fall back to `python -m atot.cli` only when the installed script is unavailable. Use only CLI
v2 commands under `atot exec`; do not use removed top-level aliases.

## Check The Runtime

1. Run `atot doctor --json`, preserving any known local tool environment such as `VCPKG_ROOT` on
   Windows.
2. Use the backend selected by the configured platform defaults. Omit `--backend` unless the user
   explicitly requests an override: macOS uses MLX Whisper and Windows uses faster-whisper.
3. If required model files are missing, do not download them. Read
   `src/atot/data/model_inventory.json`, report the exact `required_files` URLs and their target paths
   under the reported data-root `model/` directory, then stop for the user to place them.
4. If Windows CUDA fails, do not silently switch to CPU. CPU is an explicit opt-in:

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

5. Keep model weights, downloaded audio, work outputs, caches, and local absolute paths out of git.

The default installed CLI locations relative to the data root are:

```text
env/bin/atot
env/Scripts/atot.exe
```

In path examples below, use `$ATOT_DATA_ROOT` when it is set; otherwise substitute the `data_root`
reported by `atot doctor --json`.

## Import A Xiaoyuzhou Episode

Run the built-in import and stable local transcription path:

```bash
atot exec import "<xiaoyuzhou-episode-url>" --local-only --json
```

Use `--data-only` only when the user asks to download and prepare metadata without transcription.
Do not continue to transcript or summary steps after a data-only import.

For an import result, read the work directory from `transcription.run.work_dir`. For a direct
transcribe result, use `run.work_dir`. Treat a missing transcription object, a false
`transcription.run.success`, or a false `run.success` as a failure rather than guessing an output
path.

The primary files in the work directory are:

```text
transcript.readable.md
transcript.timestamped.md
transcript.corrected.txt
transcript.srt
transcript.vtt
run.json
qa.json
qa.md
```

## Create The Agent Summary

For a completed Xiaoyuzhou transcription, create `<work-dir>/summary.md` with the agent model when
the user asks for a summary or expects the standard import result. Read the complete
`transcript.readable.md`; process it in sections when it is too long for one context. Write concise
Markdown containing the episode topic, main points, and important conclusions, and distinguish
uncertain claims when QA reports blockers or warnings.

Do not invoke the local ASR pipeline or `atot exec cloud summarize` to generate this file. Do not
invent missing content, silently substitute a heuristic summary, or overwrite an existing
`summary.md` unless the user asks to regenerate it. If the transcript cannot be read or summarized,
surface the failure and leave `summary.md` absent.

## Transcribe An Apple Podcasts Episode

`atot exec import` accepts Xiaoyuzhou episode URLs only. For an Apple Podcasts episode URL:

1. Resolve the episode audio URL. The iTunes lookup API usually works:

```text
https://itunes.apple.com/lookup?id=<podcast-id>&entity=podcastEpisode&limit=200&country=CN
```

Find the result whose `trackId` matches the `i=` query parameter, then use its `episodeUrl`. Adjust
the `country` query for non-China links or inspect the page HTML only when needed.

2. Download the audio to `$ATOT_DATA_ROOT/materials/apple-<trackId>/episode.<ext>`.

3. Let SonaFolio select the configured platform backend:

```bash
atot exec transcribe "$ATOT_DATA_ROOT/materials/apple-<trackId>/episode.<ext>" \
  --job-dir "$ATOT_DATA_ROOT/work/apple-<trackId>" \
  --language zh --local-only --json
```

Do not commit the downloaded audio or generated outputs.

## Transcribe Direct Media

For a direct `.mp3`, `.m4a`, `.wav`, `.mp4`, or other ffmpeg-readable URL, download it to
`$ATOT_DATA_ROOT/materials/<stable-id>/`. For that media or a local file, run:

```bash
atot exec transcribe "<media-file>" --language zh --local-only --json
```

For subtitles only, run:

```bash
atot exec srt "<media-file>" --language zh --overwrite --json
```

## Report The Result

Include:

- Whether import and transcription succeeded.
- The work directory and main transcript, subtitle, and agent-summary paths that actually exist.
- `runtime_seconds` and `speed_factor` from `run.json` when available.
- QA status, blocker count, warning count, and `repair_window_count` from `qa.json`.
- Any required next step, such as local repair, manual model placement, or explicit Windows CPU use.

If the user asks for transcript content, provide a concise excerpt or summary instead of dumping a
very long transcript. Do not claim QA passed when `qa.status` is `fail`; successful ASR and failing
QA can both be true.
