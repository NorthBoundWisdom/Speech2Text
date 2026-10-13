# SonaFolio

面向中文播客的本地转写与知识资料库。播客太多、没时间听完时，把节目转成文字，直接读完整转写，或先看 Codex 总结了解重点，再决定哪些内容值得深入阅读或收听。来源与时间戳一并保留。

## 中文官网与使用手册

### [打开 SonaFolio 官网](https://northboundwisdom.github.io/sonafolio/) · [完整中文手册](https://northboundwisdom.github.io/sonafolio/handbook/)

[下载与安装](https://northboundwisdom.github.io/sonafolio/install/) · [第一次中文转写](https://northboundwisdom.github.io/sonafolio/quick-start/) · [Codex 总结回写](https://northboundwisdom.github.io/sonafolio/guides/agent-summary/) · [故障排查](https://northboundwisdom.github.io/sonafolio/guides/troubleshooting/) · [English README](README.en.md)

**已经验证的主路径：Apple Silicon Mac + MLX Whisper + `large-v3-turbo` + 中文播客。** 多语言设置可用，不表示各语言都经过同等效果验证。CLI 保留 `atot`；既有资料、包名和内部身份保持兼容。

![SonaFolio 订阅与处理队列](doc/assets/screenshot-1.png)

截图来自当前源码构建，数量与节目标题是示例资料库状态。发布的 v0.9.0 早于新增列宽/折叠与语言控件，使用这些功能需当前源码构建。下载能力以[对应 release](https://github.com/NorthBoundWisdom/sonafolio/releases)为准。

## 平台与边界

| 平台 | 当前能力 |
| --- | --- |
| macOS / Apple Silicon | 原生 SwiftUI、Qt、CLI/TUI；中文稳定主路径采用 MLX Whisper |
| Windows / x64 | Qt 与 CLI；faster-whisper 需独立 CUDA 配置或显式 CPU |
| iOS / iPadOS 17+ | 阅读与订阅管理；不运行本机 ASR |
| Linux / x86_64 | Qt AppImage 客户端；无稳定晋升 Linux ASR 后端 |

本地 ASR 不上传音频；来源导入会联网。Codex 可通过 MCP 使用会话模型生成总结，不要求 SonaFolio Key。可选云 API 是另外的文本处理路径。iCloud、agent、云服务有不同数据边界。

## 快速开始

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

Python 3.10+；Windows 用 python 替换 python3，通过托管环境的 exe 检查：

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

安装器不含模型。按[模型教程](https://northboundwisdom.github.io/sonafolio/models/)手动准备权重，macOS 通过 `brew install ffmpeg` 等方式提供 ffmpeg/ffprobe。Windows 可使用 PATH/vcpkg，CUDA/cuDNN 需与实际 CTranslate2 wheel 匹配，不会静默改为 CPU。

## 已验证中文流程的 CLI 入口

```bash
atot exec transcribe path/to/episode.m4a --model large-v3-turbo --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --language zh --local-only --json
atot exec srt path/to/video.mp4 --language zh --json
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
atot exec library status --json
```

替换路径与 ID，使用任务返回的实际工作目录。重要人名、数字、引用与结论需复听；QA 通过不保证逐字准确。

无参数 atot 打开 TUI，脚本使用 exec。旧顶层 transcribe/import-xiaoyuzhou 等别名已移除。重建转写使用 `--force`，不是 --force-transcribe。更多选项以各自 --help 为准。

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --force
atot status --task-id <task-id> --json
atot resume <task-id> --json
```

当前 resume 查询持久化任务状态，不自动重跑任务。--watch 可提供事件，脚本仍需判断最终结果与退出码。

## 语言设置

当前源码在 Swift/Qt 的 **Settings → Local ASR** 中提供转写复选框和总结输出语言。中文流程勾选 Chinese / Mandarin；不选自动识别，多选自动加混合语言提示，保留原文，不构成严格语言白名单。

```bash
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot exec transcribe path/to/audio.m4a --language zh --language en --local-only
```

新配置的转写默认自动、总结默认中文；已有明确语言保留。旧 local.language 兼容读取，当前保存迁移为数组。改变设置不自动重生成旧文档。总结设置统一影响正文、标题和 MCP 指引，字幕翻译独立配置。

## 订阅与资料库

```bash
atot exec subscriptions add "https://example.org/feed.xml" --group-name Research --limit 10 --json
atot exec subscriptions list --json
atot exec subscriptions refresh --all --json
atot exec subscriptions refresh --id <subscription-id> --full-history --json
```

刷新获取元数据，不自动下载和处理全系列。权威库包含 JSON、Markdown、分组/阅读状态与删除 tombstone；媒体与 work 留在本机。删除与归档不同，见[资料库教程](https://northboundwisdom.github.io/sonafolio/guides/library/)和[备份说明](https://northboundwisdom.github.io/sonafolio/guides/storage/)。

默认数据根目录 `~/Documents/SpeechToTextData/`，模型唯一正常存储位置是其 model/。本地权威库在 Audio2TextLibrary/，iCloud 模式在兼容的 Audio2Text/Audio2TextLibrary/。不要为品牌变更直接改名用户目录。

## Codex / MCP 总结回写

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

Windows 使用用户 Documents 下 env/Scripts/atot.exe 的实际路径。连接名称可以自定义，旧 audio2text 注册不失效。

要求 agent 读取完整转写和 QA，按 get_episode 返回的当前哈希和输出语言，通过 write_summary 发布。非空总结仅在明确重新生成请求后覆盖；版本冲突需要重新读取。MCP 不调用模型 API，不暴露 Key、媒体、任意路径或删除操作。

原生 App 可复制 **Copy Codex summary write-back instructions** 后粘贴给 agent。它不会自动给 Codex 发消息。`atot serve --stdio` 是 GUI 内部协议，不是 MCP。完整说明见[中文 MCP 教程](https://northboundwisdom.github.io/sonafolio/guides/agent-summary/)。

## 可选云 API

```bash
atot exec cloud prepare path/to/work-dir --json
atot exec cloud summarize path/to/work-dir --call-api --mode auto --json
```

prepare 不调用 API；模型总结需明确 --call-api，并已配置 endpoint、model、安全存储 Key 与文本发送权限。未调用模型的 scaffold 不等于模型总结。隐藏输入与 Responses 协议边界见[云总结教程](https://northboundwisdom.github.io/sonafolio/guides/cloud-summary/)。

## 构建与发布

```bash
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution ad-hoc
python3 configs/ios_workflow.py build --platform ios --scheme Audio2Text-iOS --configuration debug
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
```

macOS 本地包在 build/app/SonaFolio.app。tag 发布四个平台客户端包，模型不随包分发；macOS ad-hoc 无公证，Windows 未签名，iOS 没有自动 IPA 分发。

[文档索引](doc/README.md) · [Swift 参考](app/README.md) · [Qt 参考](qt/Audio2TextQt/README.md) · [CI 发布](doc/CI_RELEASES.md) · [网站维护](doc/WEBSITE.md)

## 手动模型下载清单

别名、文件与链接以 [model_inventory.json](src/atot/data/model_inventory.json) 为准。候选条目不等于生产默认。代理不自动下载模型，修改清单后执行 `python src/scripts/validate_model_inventory.py`。

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

## 同类项目对比

已有九个项目与功能维度的完整对比保留在 [English README 的 Related projects](README.en.md#related-projects)，包含来源和时间快照。历史 Stars 与推送时间不作为实时活跃度数据，产品能力应再核对对应项目。

| 项目 | Stars 快照 | 推送日期快照 (UTC+8) | Focus | Declared repository license |
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

| 项目 | 界面 / ASR | RSS / 发现 | 总结 | 导出 |
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

| 项目 | Automation | Knowledge management | Diarization | Quality and recovery |
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


## 开发检查与许可

```bash
python -m ruff check .
python -m mypy
python -m pytest
python src/scripts/check_public_paths.py
python src/scripts/validate_model_inventory.py
python configs/check_docs.py
python configs/check_repository_language.py
```

官网、用户手册与本 README 默认中文，代码和通用界面保持英文。语言政策对中文文档、翻译和 ASR 资产逐文件记录，历史实验保留原始测量，公共源码不包含本机路径、音频、模型、Key 或私人资料库。

原始代码采用 [MIT](LICENSE)。第三方组件、模型和媒体有各自条款，参见[第三方声明](THIRD_PARTY_NOTICES.md)和[发布许可](doc/RELEASE_LICENSES.md)。FreeCM 独立维护。
