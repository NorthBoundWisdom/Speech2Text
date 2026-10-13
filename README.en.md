# SonaFolio

Local-first podcast transcription and knowledge library for macOS, iOS, and Windows.

[English website and handbook](https://northboundwisdom.github.io/sonafolio/en/) · [中文官网](https://northboundwisdom.github.io/sonafolio/) · [Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) · [Documentation](doc/README.md)

SonaFolio turns podcasts and audio/video files into readable transcripts, subtitles, and a local
knowledge library. Work through a podcast backlog by reading transcripts directly or asking Codex
to summarize first, then choose the passages worth reading or listening to in depth. The CLI remains `atot`. Existing data, package names, and application identities
are preserved; see [branding and compatibility](doc/BRANDING.md).

| Platform | Current support |
| --- | --- |
| macOS / Apple Silicon | SwiftUI app, Qt client, CLI/TUI; stable MLX Whisper ASR |
| Windows / x64 | Qt client and CLI; faster-whisper ASR with separately configured CUDA or explicit CPU mode |
| iOS / iPadOS 17+ | Library reader and subscription management; no on-device ASR |
| Linux / x86_64 | Qt AppImage client; no stable Linux ASR backend |

The default model alias is `large-v3-turbo`. Local ASR does not upload audio. Cloud summaries are an
optional text-only stage. Codex can summarize through MCP using its own model, without a SonaFolio
API key; text read by the agent becomes part of its conversation.

## Quick start

Clone the repository and initialize its build infrastructure:

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

Python 3.10+ is required. On macOS, activate the managed environment and check dependencies:

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

macOS ASR requires Apple Silicon. Install FFmpeg, for example with `brew install ffmpeg`, and place
model files manually under the data-root `model/` directory. The default macOS model is:

```text
~/Documents/SpeechToTextData/model/whisper-large-v3-turbo/
  config.json
  weights.safetensors
```

On Windows, use `python` instead of `python3` and run:

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

The default Windows model is `model/faster-whisper-large-v3-turbo/`, with device `cuda` and compute
type `int8_float16`. CUDA is never silently replaced with CPU. Explicit CPU mode:

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

Use PATH or vcpkg to provide `ffmpeg.exe` and `ffprobe.exe`:

```powershell
vcpkg install "ffmpeg[ffmpeg,ffprobe]:x64-windows"
```

A CTranslate2 wheel may require CUDA 12 DLLs even when CUDA 13 is installed. Follow the explicit
`doctor` errors for compatible CUDA/cuDNN dependencies. Windows setup does not require Swift or Xcode.

## CLI reference

With the environment activated, `atot` opens the TUI. Scripted workflows use `atot exec ...`:

```bash
atot --help
atot exec transcribe path/to/episode.m4a --model large-v3-turbo --language zh --local-only
atot exec transcribe path/to/episode.m4a --json --watch
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --local-only
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
atot status --task-id <task-id>
atot resume <task-id>
atot config list
atot config get cloud.model
atot config set workflow.default_cloud_summary false
```

The old top-level `transcribe`, `import-xiaoyuzhou`, `srt`, `qa`, `repair`, and `cloud` aliases were
removed in CLI v2. Use the corresponding `exec` commands. Individual `--help` pages describe options.

Automatic chunking uses fixed windows for short audio and silence-aware boundaries for longer
inputs. Explicit settings are available for reproducible experiments:

```bash
atot exec transcribe path/to/episode.m4a \
  --chunking smart --chunk-length 900 --max-chunk-length 1200 --overlap 10
```

Use `--chunking fixed` for fixed windows, `--silence-threshold -30` for an explicit silence threshold,
and `--force` to rerun ASR instead of reusing matching cached chunks.

### Transcription and summary languages

In either desktop app, open **Settings > Local ASR**. Check one spoken language to set a language
hint, or several for mixed-language transcription. Leave all unchecked for automatic detection.
Multiple selections enable automatic detection with context hints; they do not restrict detection to
a language whitelist. Transcription preserves each spoken language rather than translating it.

**Summary Output Language** defaults to Chinese and controls summary text, headings, short titles,
and MCP/Codex instructions. It takes priority over conflicting language requests in saved custom
prompts. Saving language settings requires no API key and does not regenerate existing documents.
Subtitle translation remains a separate setting.

The shared configuration and CLI also support these settings:

```bash
atot config set local.languages '["zh", "en"]'
atot config set summary.language en
atot exec transcribe path/to/episode.m4a --language zh --language en --local-only
atot exec transcribe path/to/episode.m4a --language auto --local-only
```

`local.languages = []` means auto; an omitted `--language` uses the saved selection. Existing explicit
`local.language` values remain supported and are migrated when settings are saved. New configurations
use auto detection. `summary.language` is a single language code, defaulting to `zh`. Both source and
summary selectors offer Chinese/Mandarin, English, Japanese, Korean, Cantonese, German, French,
Spanish, Russian, Portuguese, Italian, Arabic, Hindi, Vietnamese, Thai, and Indonesian.

### Subtitles and translation

```bash
atot exec srt path/to/video.mp4
atot exec srt path/to/video.mp4 --language zh --language en
atot exec srt path/to/video.mp4 --language auto
```

The command writes `video.srt` beside the source and reusable intermediate files under `cache/srt/`.
Existing subtitles require `--overwrite`. Repeated source languages enable automatic ASR language
detection. Optional subtitle translation is configured through `[translation]` settings; a Chinese
target writes `video.zh.srt`. Local translation models must also be placed manually under `model/`.

### Imports and subscriptions

Xiaoyuzhou imports preserve metadata, download media into local materials, and optionally transcribe:

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only
atot exec subscriptions add "https://www.xiaoyuzhoufm.com/podcast/<podcast-id>" --group-name Default
atot exec subscriptions list
atot exec subscriptions refresh --all
atot exec library status --json
```

`--data-only` skips transcription. `--no-download` skips media download for recovery workflows.
`--group-name` sets a logical library group; `--folder-name` and `--audio-name` customize generated
names. Subscription refresh imports recent metadata without automatically downloading or processing.
Scheduling is delegated to external tools.

## Data and privacy

The default runtime root is `~/Documents/SpeechToTextData/`. The CLI accepts `ATOT_DATA_ROOT`; Qt's
`--data-root` is passed to its workflow service.

```text
SpeechToTextData/
  env/                 Python runtime
  model/               Manually installed models
  materials/           Local media and private import metadata
  work/                Transcription, QA, repair and cloud artifacts
  cache/               Logs, tools and temporary indexes
  Audio2TextLibrary/   Authoritative library in local-storage mode
```

In iCloud mode, the authoritative library defaults to
`~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/`. iOS accesses the same
folder through a Files bookmark. Compatibility folder names remain unchanged.

`episode.json` contains metadata and reading state; `documents/transcript.md` and
`documents/summary.md` contain readable documents. Deleted episodes receive tombstones so subscription
refresh does not reimport them. Models, audio, user libraries, credentials, caches, and generated
transcripts are not source files and must stay out of Git.

MCP, iCloud, and optional cloud API calls have separate data boundaries. See [privacy](doc/PRIVACY.md),
[library layout](doc/LIBRARY_LAYOUT.md), and [QA and repair](doc/QUALITY_LOOP.md).

## Agent summaries through MCP

Register the local stdio service with Codex:

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

On Windows:

```powershell
codex mcp add sonafolio -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
```

The client registration name is arbitrary; existing `audio2text` connections continue to work.
Request a summary for episodes with transcripts but no summary, ask the agent to read the complete
transcript and QA, and publish through `write_summary` with current document hashes.

The four MCP tools are `list_episodes`, `get_episode`, `read_document`, and `write_summary`. They do
not expose credentials, media, arbitrary file paths, configuration changes, or deletion. A nonempty
summary may be replaced only after an explicit regeneration request. Version conflicts require
rereading the documents. The server does not call a model API.

`atot serve --stdio` is the GUI's internal JSON protocol, not MCP. The legacy HTTP service is
loopback-only and requires its own `ATOT_HTTP_TOKEN`; use MCP for ordinary agent summaries.

## Optional cloud text processing

Cloud preparation does not call an API by default:

```bash
atot exec cloud prepare path/to/work-dir
atot exec cloud summarize path/to/work-dir
```

Enable API execution explicitly after configuring an endpoint, model, securely stored key, and
transcript-upload permission:

```bash
atot config set cloud.api_base '"https://api.example.com/v1"'
atot config set cloud.api_key --stdin
atot exec cloud summarize path/to/work-dir --call-api
```

Use hidden input for keys; never place them in shell arguments or public files. Default app processing
and its primary shortcuts execute local transcription and QA, without requiring cloud credentials.

## Clients and builds

Build the Swift macOS app from the repository root:

```bash
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
```

The app bundle is `build/app/SonaFolio.app`, with the compatibility entrypoint
`Contents/MacOS/Audio2TextCli`. Internal Swift targets and the generated `Audio2Text.xcodeproj` retain
stable names. iOS builds use `--platform ios --scheme Audio2Text-iOS`.

Qt requires Qt 6.8+; CI validates Qt 6.12.0. Configure an external `atot` executable in Settings:

```bash
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
```

See the [Swift guide](app/README.md), [Qt guide](qt/Audio2TextQt/README.md), and
[development guide](doc/TECHNICAL_GUIDE.md) for complete build and packaging instructions.

## CI and releases

GitHub Actions checks Python, Swift, and Qt on macOS, Windows, and Linux. Push a version tag to build
Windows Qt EXE, Linux Qt AppImage, macOS Qt DMG, and macOS Swift DMG installers. All four packages
must pass provenance, licensing, and hash checks before GitHub Release publication:

```bash
git tag v0.9.1
git push origin v0.9.1
```

Manual Native release runs build artifacts without publishing. macOS currently uses ad-hoc signatures
without notarization; Windows installers are unsigned. Qt packages include Qt libraries but not the
CLI, FFmpeg, CUDA, or model weights. Swift packages include the CLI wheel and use the existing runtime
setup flow. Linux client availability does not imply stable Linux ASR support.

[Release workflow](doc/CI_RELEASES.md) · [License materials](doc/RELEASE_LICENSES.md) · [Website maintenance](doc/WEBSITE.md)

## Manual model download inventory

All model aliases, required files, and manual URLs are maintained in
[src/atot/data/model_inventory.json](src/atot/data/model_inventory.json). Experimental aliases are not
promoted defaults. Agents must not download weights automatically. After changing the inventory, run
`python src/scripts/validate_model_inventory.py` to verify this table.

| Model | Local path | URL |
|---|---|---|
| `small-4bit` | `model/whisper-small-mlx-4bit/config.json` | `https://huggingface.co/mlx-community/whisper-small-mlx-4bit/resolve/main/config.json?download=true` |
| `small-4bit` | `model/whisper-small-mlx-4bit/weights.npz` | `https://huggingface.co/mlx-community/whisper-small-mlx-4bit/resolve/main/weights.npz?download=true` |
| `large-v3-turbo` | `model/whisper-large-v3-turbo/config.json` | `https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/config.json?download=true` |
| `large-v3-turbo` | `model/whisper-large-v3-turbo/weights.safetensors` | `https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors?download=true` |
| `large-v3-turbo-q4` | `model/whisper-large-v3-turbo-q4/config.json` | `https://huggingface.co/mlx-community/whisper-large-v3-turbo-q4/resolve/main/config.json?download=true` |
| `large-v3-turbo-q4` | `model/whisper-large-v3-turbo-q4/weights.npz` | `https://huggingface.co/mlx-community/whisper-large-v3-turbo-q4/resolve/main/weights.npz?download=true` |
| `large-v3-4bit` | `model/whisper-large-v3-mlx-4bit/config.json` | `https://huggingface.co/mlx-community/whisper-large-v3-mlx-4bit/resolve/main/config.json?download=true` |
| `large-v3-4bit` | `model/whisper-large-v3-mlx-4bit/weights.npz` | `https://huggingface.co/mlx-community/whisper-large-v3-mlx-4bit/resolve/main/weights.npz?download=true` |
| `large-v3` | `model/whisper-large-v3-mlx/config.json` | `https://huggingface.co/mlx-community/whisper-large-v3-mlx/resolve/main/config.json?download=true` |
| `large-v3` | `model/whisper-large-v3-mlx/weights.npz` | `https://huggingface.co/mlx-community/whisper-large-v3-mlx/resolve/main/weights.npz?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ASR-0.6B/config.json` | `https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/main/config.json?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ASR-0.6B/merges.txt` | `https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/main/merges.txt?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ASR-0.6B/model.safetensors` | `https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/main/model.safetensors?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ASR-0.6B/tokenizer_config.json` | `https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/main/tokenizer_config.json?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ASR-0.6B/vocab.json` | `https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/main/vocab.json?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ForcedAligner-0.6B/config.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/config.json?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ForcedAligner-0.6B/merges.txt` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/merges.txt?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ForcedAligner-0.6B/model.safetensors` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/model.safetensors?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ForcedAligner-0.6B/tokenizer_config.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/tokenizer_config.json?download=true` |
| `mlx-qwen3-asr-0.6b` | `model/Qwen3-ForcedAligner-0.6B/vocab.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/vocab.json?download=true` |
| `qwen3-forced-aligner-0.6b` | `model/Qwen3-ForcedAligner-0.6B/config.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/config.json?download=true` |
| `qwen3-forced-aligner-0.6b` | `model/Qwen3-ForcedAligner-0.6B/merges.txt` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/merges.txt?download=true` |
| `qwen3-forced-aligner-0.6b` | `model/Qwen3-ForcedAligner-0.6B/model.safetensors` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/model.safetensors?download=true` |
| `qwen3-forced-aligner-0.6b` | `model/Qwen3-ForcedAligner-0.6B/tokenizer_config.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/tokenizer_config.json?download=true` |
| `qwen3-forced-aligner-0.6b` | `model/Qwen3-ForcedAligner-0.6B/vocab.json` | `https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B/resolve/main/vocab.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/config.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/model.bin` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/preprocessor_config.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/tokenizer.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/vocabulary.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/config.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/config.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/model.bin` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/preprocessor_config.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/preprocessor_config.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/tokenizer.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/tokenizer.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/vocabulary.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/vocabulary.json?download=true` |
## Related projects and feature comparison

This is the **2026-10-12** source/documentation snapshot, translated without refreshing its historical
measurements. Stars and push dates are static GitHub API observations; dates use UTC+8. They do not
measure quality or release freshness. We have not run a shared accuracy, speed, or summary-quality
benchmark across these projects. "Not documented" means the reviewed documentation did not promise
that capability, not that it is unsupported. Model licenses are separate from repository licenses.

| Project | Stars | Last push (UTC+8) | Focus | Declared repository license |
| --- | ---: | --- | --- | --- |
| [Buzz](https://github.com/chidiwilliams/buzz) | 21,948 | 2026-10-11 | Desktop transcription, live audio and subtitles | MIT |
| [Vibe](https://github.com/thewh1teagle/vibe) | 7,759 | 2026-10-06 | Local transcription, multiple models and AI analysis | MIT |
| [Speakr](https://github.com/murtaza-nasir/speakr) | 4,082 | 2026-10-12 | Self-hosted recordings, knowledge Q&A and teams | AGPLv3 / commercial dual license |
| [MinusPod](https://github.com/ttlequals0/MinusPod) | 472 | 2026-10-12 | Ad detection, audio editing and RSS republication | MIT |
| [podcast-bridge](https://github.com/Hatari130/podcast-bridge) | 91 | 2026-07-05 | Agent skills, Xiaoyuzhou/RSS and local text libraries | MIT |
| [podHarvest](https://github.com/Community-Access/podharvest) | 1 | 2026-09-06 | Podcast archiving, chapters and accessible reading | MIT |
| [ai-podcast-ripper](https://github.com/mbjornson/ai-podcast-ripper) | 0 | 2026-09-29 | Automated podcasts with local Mac models | Not identified by GitHub |
| [MediaBrief](https://github.com/EvilIrving/mediabrief) | 1 | 2026-09-09 | macOS media links, subtitles and summaries | MIT |
| [Lumina](https://github.com/brentonmallen1/lumina) | 0 | 2026-07-02 | Self-hosted extraction, summaries and Q&A | README states MIT |

| Project | Interface / ASR | RSS and discovery | Summaries | Exports |
| --- | --- | --- | --- | --- |
| **SonaFolio** | SwiftUI, Qt, iOS reader, CLI; MLX Whisper / faster-whisper | Xiaoyuzhou, RSS, manual refresh | Codex MCP; optional text API | Markdown, JSON, SRT/VTT |
| [Buzz][compare-buzz] | Desktop; multiple Whisper backends and live microphone | Directory watching; RSS not documented | AI summary plugin | TXT, SRT, VTT |
| [Vibe][compare-vibe] | Desktop; Whisper, Nemotron, Parakeet, system/microphone audio | Media links; RSS not documented | Local Ollama; Claude API | SRT/VTT, TXT, DOCX/PDF |
| [Speakr][compare-speakr] | Self-hosted Web/PWA; WhisperX or cloud ASR | Directory import; RSS not documented | Ollama or API; customizable prompts | Template-based exports |
| [MinusPod][compare-minuspod] | Self-hosted Web; faster-whisper/Parakeet or remote ASR | Polling, optional Podping, rebuilt feeds | LLM ad detection and review | Ad-free audio/RSS, transcripts, chapters |
| [podcast-bridge][compare-bridge] | CLI/Agent skill; default Bijian cloud ASR, Jianying integration | Xiaoyuzhou, RSS, explicit sync | Agent reads the full transcript | Timestamped Markdown / Obsidian |
| [podHarvest][compare-harvest] | wxPython/CLI; local ASR, source transcripts or cloud | RSS/OPML; manual saved-feed checks | Optional llama.cpp or cloud enhancements | SRT/VTT, Markdown/HTML/TXT/JSON |
| [ai-podcast-ripper][compare-ripper] | macOS CLI/dashboard; oMLX Whisper / faster-whisper | Incremental RSS, backfill, optional LaunchAgent | Local oMLX / Ollama | Markdown summaries, separate TXT |
| [MediaBrief][compare-mediabrief] | Apple Silicon app; source subtitles first, then mlx-whisper | RSS / YouTube channels and queues | Configurable LLM API | Markdown, TXT, DOCX/PDF, subtitles |
| [Lumina][compare-lumina] | Self-hosted Web; faster-whisper/Whisper/Canary/Qwen Audio | Automatic RSS monitoring | Ollama, multiple summary modes | TXT, SRT, VTT |

| Project | Automation | Knowledge management | Diarization | Quality and recovery |
| --- | --- | --- | --- | --- |
| **SonaFolio** | CLI, internal JSON, paged MCP, versioned writes; external scheduling | Title search, groups, read/star state, iCloud; no built-in cross-episode semantic Q&A | Not in stable backends | QA, correction audit, targeted repair, hash checks |
| [Buzz][compare-buzz] | CLI, plugins, queue, directory watching; MCP not documented | Transcript search and playback | Supported | Speech separation, transcript viewer |
| [Vibe][compare-vibe] | CLI, HTTP API, agent skills, multi-file batches; MCP not documented | Transcript analysis | Supported | VAD timestamp mode |
| [Speakr][compare-speakr] | REST, webhooks, research agent, import queues | Cross-library semantic Q&A, tags, SSO, teams | Backend dependent | Vocabulary, speaker tools, editing, retention |
| [MinusPod][compare-minuspod] | REST/OpenAPI, webhooks, scheduled RSS | Episode/ad search, history and cost statistics | Not documented | Confidence, review, verification, backup, retries |
| [podcast-bridge][compare-bridge] | CLI and agent skills, concurrent chunks | SQLite full-text/metadata search, Obsidian | Explicitly not separated | Preflight, feed validation, full-transcript summaries |
| [podHarvest][compare-harvest] | CLI, source/directory batches; no background feed polling | Full-text search, audio navigation, saved feeds, archives | Optional backends | Download validation, benchmarks, transcript/chapter editing |
| [ai-podcast-ripper][compare-ripper] | Incremental batches, backfill, LaunchAgent | Keyword/semantic summary search, daily digests | Not documented | Chunked summaries, retry state, failure isolation |
| [MediaBrief][compare-mediabrief] | Backend HTTP, Telegram/Slack bots, queues | SQLite history and source filters | Not documented | Original text, retries without retranscription, LLM cleanup |
| [Lumina][compare-lumina] | HTTP/OpenAPI, queues, automatic RSS | SQLite FTS5, single-content Q&A | Optional pyannote with HF token | Audio enhancement; common QA gate not documented |

Scenario fit is an inference from these capabilities, not a benchmark ranking: Buzz/Vibe cover broad
multi-platform audio inputs; Speakr/Lumina focus on self-hosted knowledge services; MinusPod focuses
on ad-free podcast republication; podcast-bridge/podHarvest emphasize agent-driven feeds or local
archives; ai-podcast-ripper/MediaBrief emphasize Mac automation or subtitle-first media reading.
SonaFolio emphasizes local ASR, auditable repair, a portable library, and agent summary write-back.

podcast-bridge's default key-free ASR still uploads audio; its summary style flag does not itself
create the agent-authored summary. See its [entrypoint](https://github.com/Hatari130/podcast-bridge/blob/main/transcribe.py)
and [skill](https://github.com/Hatari130/podcast-bridge/blob/main/SKILL.md). podHarvest saved feeds use
manual checks; see its [model guide](https://github.com/Community-Access/podharvest/blob/main/docs/MODELS.md)
and [reference](https://github.com/Community-Access/podharvest/blob/main/docs/REFERENCE.md).

[compare-buzz]: https://github.com/chidiwilliams/buzz/blob/main/README.md
[compare-vibe]: https://github.com/thewh1teagle/vibe/blob/main/README.md
[compare-speakr]: https://github.com/murtaza-nasir/speakr/blob/master/README.md
[compare-minuspod]: https://github.com/ttlequals0/MinusPod/blob/main/README.md
[compare-bridge]: https://github.com/Hatari130/podcast-bridge/blob/main/README.md
[compare-harvest]: https://github.com/Community-Access/podharvest/blob/main/README.md
[compare-ripper]: https://github.com/mbjornson/ai-podcast-ripper/blob/main/README.md
[compare-mediabrief]: https://github.com/EvilIrving/mediabrief/blob/main/README.md
[compare-lumina]: https://github.com/brentonmallen1/lumina/blob/main/README.md

## Development and repository maintenance

```bash
python -m ruff check .
python -m mypy
python -m pytest
python src/scripts/check_public_paths.py
python src/scripts/validate_model_inventory.py
python configs/check_docs.py
python configs/check_repository_language.py
```

Source lives in `src/atot/`, platform adapters in `backends/`, candidate comparisons in `candidate/`,
shared language rules and model inventory in `data/`, and thin validators in `src/scripts/`.
Swift and Qt clients live in `app/` and `qt/`; `website/` contains the Chinese-first handbook and Pages site.
Historical experiment measurements stay in `doc/experiments/`; completed evidence belongs in
`doc/ROADMAP_STATUS.md`. Keep `TODO.md` only while concrete unfinished work exists.

## License

Original source uses [MIT](LICENSE). Dependencies, models, and media retain their own terms; see
[third-party notices](THIRD_PARTY_NOTICES.md) and [release licensing](doc/RELEASE_LICENSES.md).

The website, user handbook, and main README default to Chinese. Source prose and interfaces remain English. Reviewed translations, Chinese ASR
prompts/rules, multilingual fixtures, and original benchmark input names remain as language data.
`language-assets.json` records their scope; CI rejects new Chinese prose or UI outside those entries.
FreeCM is an independently maintained third-party submodule.
