# Audio2Text

Audio2Text 是一个本地中文播客转录工具。当前稳定生产路径是 macOS / Apple Silicon +
MLX Whisper；Windows 是 CLI-only 路径，目标后端是 `faster-whisper` / CUDA。
v2 CLI 默认进入交互式 TUI；脚本化入口统一放在 `atot exec ...`，App bundle 内的
`Audio2TextCli` 使用同一套入口。默认模型别名为 `large-v3-turbo`。

- Mac 本地 ASR 基于 MLX Whisper。
- Windows CLI ASR 基于 faster-whisper，优先尝试本机 CUDA 13；若上游 wheel 需要 CUDA 12
  运行时，会明确报错，不自动切 CPU。
- 小宇宙导入会下载音频、保存节目元信息，并可直接转录。
- 输出包含可读稿、字幕、原始 JSON、QA 报告和可审计的修正规则记录。
- 云端摘要是可选的文本阶段；音频、视频、模型权重不会被打包发送。
- MCP 总结流程无需在 Audio2Text 配置 API Key：Codex 读取本地转录，用当前模型总结并回写资料库。
- macOS SwiftUI App 通过同一套 Python workflow service 执行导入、转录、QA、云端摘要和字幕流程。

## 运行数据

本地运行数据默认放在：

```text
~/Documents/SpeechToTextData/
  env/     Python 虚拟环境
  model/   本地模型文件
  cache/   日志、临时索引和工具缓存
  Audio2TextLibrary/  关闭 iCloud 时的本地权威资料库
  materials/  本机音视频素材和私有导入信息
  work/       转录、QA、repair、cloud 等处理过程文件
```

数据根目录由 App/CLI 固定定位，不再用环境变量覆盖。仓库里的 `materials/`、`work/`、
`Audio2TextLibrary/`、`model/`、模型权重、下载音频和生成稿件都不是源码，不应提交。

## For Mac

Mac 是当前稳定生产路径。

### Mac 环境

- macOS + Apple Silicon
- Python 3.10+
- Xcode，用于构建 macOS App
- Homebrew `ffmpeg`，推荐安装；没有时部分音频流程会退回系统工具

```bash
brew install ffmpeg
```

### Mac 快速开始

```bash
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli doctor
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli models
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli
```

`~/Documents/SpeechToTextData/env/` 是 App/CLI 使用的 Python 运行环境，不是公开 CLI
入口。DMG/App 内的公开命令是 `Audio2Text.app/Contents/MacOS/Audio2TextCli`。
本地开发时也可以用 `~/Documents/SpeechToTextData/env/bin/atot`；无子命令时会打开 TUI，
非交互流程使用 `exec`。

### Mac 模型

默认 MLX 模型需要放在：

```text
~/Documents/SpeechToTextData/model/whisper-large-v3-turbo/
  config.json
  weights.safetensors
```

模型别名、必需文件和手动下载 URL 统一维护在
`src/atot/data/model_inventory.json`。修改模型清单后运行：

```bash
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_model_inventory.py
```

Mac 手动下载清单：

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

## For Windows

Windows 是 CLI-only 路径。新拿到仓库时，用户只需要下载模型文件、用 vcpkg 安装本机
依赖；模型归档、PATH、虚拟环境和验证可以交给 agent 处理。

### Windows 快速开始

```powershell
python configs/setup_local_app.py
~\Documents\SpeechToTextData\env\Scripts\atot.exe doctor
~\Documents\SpeechToTextData\env\Scripts\atot.exe exec library status --json
~\Documents\SpeechToTextData\env\Scripts\atot.exe exec transcribe path\to\episode.m4a --language zh
```

Windows 默认后端是 `faster-whisper`，默认模型别名仍是 `large-v3-turbo`，实际解析到：

```text
~/Documents/SpeechToTextData/model/faster-whisper-large-v3-turbo/
```

默认 CUDA 设备是 `cuda`，计算类型是 `int8_float16`。如果只想显式使用 CPU：

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
~\Documents\SpeechToTextData\env\Scripts\atot.exe doctor
```

CPU 是显式 opt-in；默认 CUDA 失败时不会静默回退。

### Windows 下载清单

推荐下载 `faster-whisper-large-v3-turbo`，保存到任意临时下载目录。agent 应移动到数据根：
`~/Documents/SpeechToTextData/model/faster-whisper-large-v3-turbo/`。

| Model | Local path | URL |
|---|---|---|
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/config.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/model.bin` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/preprocessor_config.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/tokenizer.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true` |
| `faster-whisper-large-v3-turbo` | `model/faster-whisper-large-v3-turbo/vocabulary.json` | `https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true` |

备选模型 `faster-whisper-large-v3`：

| Model | Local path | URL |
|---|---|---|
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/config.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/config.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/model.bin` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/preprocessor_config.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/preprocessor_config.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/tokenizer.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/tokenizer.json?download=true` |
| `faster-whisper-large-v3` | `model/faster-whisper-large-v3/vocabulary.json` | `https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/vocabulary.json?download=true` |

CUDA / cuDNN 参考：

- `https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html`
- `https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html`

本机优先检测 CUDA 13。如果 `doctor` 或转录报 `cublas64_12.dll` / `cublasLt64_12.dll`
缺失，说明当前安装的 CTranslate2 Python wheel 仍需要 CUDA 12.x 运行时，或需要重新编译
CTranslate2 以适配 CUDA 13。此时请按 `doctor` 的 `action_required` 处理。

### Windows vcpkg 依赖

使用本机 vcpkg 安装音视频工具：

```powershell
vcpkg install "ffmpeg[ffmpeg,ffprobe]:x64-windows"
```

agent 应从 `%VCPKG_ROOT%` 或用户提供的 vcpkg 根目录发现 `ffmpeg.exe` / `ffprobe.exe`，
并在当前会话或本机配置中让 CLI 能找到它们。不要把本机 vcpkg 绝对路径写入源码或公共文档。

### Windows agent 维护任务

- 将下载目录中的 faster-whisper 模型文件移动到数据根 `model/` 下对应目录。
- 确认 `doctor` 报告 `faster-whisper`、CTranslate2、CUDA、cuDNN、`ffmpeg` 和 `ffprobe` 状态。
- 使用小 WAV fixture 做 smoke test，确认 `atot exec transcribe ... --backend faster-whisper`
  能产生输出，或因 CUDA/CTranslate2 运行时兼容性给出明确错误。
- Windows 不依赖 Swift、Xcode 或 macOS App 构建。

## CLI 约定

```bash
atot [PROMPT]                         # 打开交互式 TUI，可带自然语言初始提示
atot -c local.language='"zh"'          # 用 TOML 值临时覆盖配置并打开 TUI
atot exec transcribe path/to/audio.m4a --json --watch
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only
atot resume <task-id>
atot status --task-id <task-id>
atot config list
atot config get cloud.model
atot config set workflow.default_cloud_summary false
atot serve --stdio
```

旧的顶层 `transcribe`、`import-xiaoyuzhou`、`srt`、`qa`、`repair`、`cloud` 命令已移除；
自动化脚本应迁移到 `atot exec ...`。

## 转录本地音频

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec transcribe path/to/episode.m4a \
  --model large-v3-turbo \
  --language zh
```

默认 `--chunking auto`：短音频走固定切块，长音频自动启用智能切块，让切点尽量贴近
静音区。智能切块的静音阈值默认会从音频响度分布估算；需要复现实验时可以显式指定
`--silence-threshold -30`，或用 `--chunking fixed` 强制固定切块。

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec transcribe path/to/episode.m4a \
  --chunking smart \
  --chunk-length 900 \
  --max-chunk-length 1200 \
  --overlap 10
```

只想给本地音频或视频生成字幕、不导入资料库时，使用 `srt`：

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec srt path/to/video.mp4
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec srt path/to/video.mp4 --language zh --language en
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec srt path/to/video.mp4 --language auto
```

默认会在源文件同目录写入 `video.srt`，并把可复用中间产物保存在数据根的
`cache/srt/`。已有字幕不会被覆盖；需要替换时显式加 `--overwrite`。
重复 `--language` 表示源音频可能混合多种语言，会启用 ASR 自动语言识别。
字幕翻译由 App 设置或 `~/Documents/SpeechToTextData/config.toml` 中的
`[translation] enabled/backend/target_language` 控制；启用中文翻译后默认输出
`video.zh.srt`。本地翻译模型默认放在：

```bash
hf download facebook/nllb-200-distilled-600M \
  --local-dir "~/Documents/SpeechToTextData/model/nllb-200-distilled-600M"
```

常用后处理命令：

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec qa ~/Documents/SpeechToTextData/work/<batch>/<episode>
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec repair ~/Documents/SpeechToTextData/work/<batch>/<episode> --plan-only
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli status --task-id <task-id>
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_output_bundle.py ~/Documents/SpeechToTextData/work/<batch>/<episode>
```

`repair` 是可选的本地增强流程。QA 会给出状态和建议，但不会要求必须 repair 才能查看
转录、后处理或继续下游操作；真正替换文本只会在显式运行 repair 后发生。

资料库硬切为一份权威 `Audio2TextLibrary/` 加本机处理缓存。Mac/CLI 启用 iCloud 时，权威库
默认位于 `~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/`；
关闭 iCloud 时，同一套 schema 写到 `~/Documents/SpeechToTextData/Audio2TextLibrary/`。iOS/iPad
通过 Files 选择 iCloud Drive 里的 `Audio2Text` 或 `Audio2TextLibrary` 文件夹，并持久记录这
同一份 Library。

```text
Audio2TextLibrary/
  manifest.json
  subscriptions/<subscription_id>.json
  groups/<group_id>.json
  episodes/<episode_id>/episode.json
  episodes/<episode_id>/documents/summary.md
  episodes/<episode_id>/documents/transcript.md
  tombstones/episodes/<episode_id>.json

materials/<episode_id>/
  <audio-or-video>.<ext>
  local.json
  主题.md

work/<episode_id>/
  transcript.readable.md
  raw.json
  corrected.json
  transcript.corrected.txt
  transcript.srt
  transcript.vtt
  corrections.json
  qa.md
  qa.json
  review.md
  run.json
  run.log
```

同一输入重复运行时，ASR 指纹和切块布局匹配的 chunk 会被复用。需要全量重跑时加
`--force-transcribe`。

## 导入小宇宙

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>"
```

导入会写入权威 Library 元信息，并把下载的音频留在本机素材目录：

```text
Audio2TextLibrary/episodes/<episode_id>/episode.json

materials/<episode_id>/
  <episode-title>.<ext>
  local.json
  主题.md

work/<episode_id>/
  ...
```

常用选项：

- `--data-only`：只保存元信息和音频，不转录。
- `--no-download`：跳过下载，适合音频已存在的恢复流程。
- `--group-name`：写入 App 使用的逻辑分组标签。
- `--folder-name` / `--audio-name`：覆盖生成的目录名或音频文件名。

订阅索引只导入近期节目元信息，不自动下载或转录：

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec subscriptions add "https://www.xiaoyuzhoufm.com/podcast/<podcast-id>" --group-name Default
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec subscriptions list
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec subscriptions refresh --all
```

## iCloud / 本地 Library

Mac 和 iOS 直接读写同一份 `Audio2TextLibrary/`。Mac 可以下载音频并调用本地模型处理；
iOS 首次使用时在 Settings 里选择 iCloud Drive 的 `Audio2Text` 或 `Audio2TextLibrary` 文件夹，
之后会通过 Files bookmark 重新打开同一份 Library。iOS 可以订阅、移除订阅、刷新节目
元信息、阅读已处理文档，并管理已读、星标、归档、分组和删除节目，但不会下载音频或转录。

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec library status --json
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec library episode delete <episode_id> --json
```

`episode.json` 是节目简介和状态的唯一元信息文件；最终可读内容只放在
`documents/summary.md` 和 `documents/transcript.md`。删除节目会删除节目记录和文档，并写入
`tombstones/episodes/<episode_id>.json`，后续订阅刷新不会重新抓回。

## macOS App

App 是稳定 CLI 的原生壳层：导入音频或小宇宙链接，点击处理后执行
`import/download -> transcribe -> QA -> optional cloud summary`。

推荐使用 FreeCM VS Code 插件执行 `config`、`build`、`run`、`test`、`package`。`config` 会在仓库根目录生成本地
`Audio2Text.xcodeproj/`，该项目文件被 git ignore，不进入版本跟踪。命令行等价流程：

```bash
git submodule update --init --recursive FreeCM
python3 configs/source_root_workflow.py --init
python3 configs/source_root_workflow.py --update
python3 configs/setup_local_app.py
python3 configs/installhooks.py
python3 configs/ios_workflow.py test --level precommit
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution developer-id --notary-profile "Audio2Text Release"
```

`configs/installhooks.py` 会把 Git 的 `core.hooksPath` 指向仓库内的 `configs/githooks/`。
默认 `pre-commit` 会先运行 `configs/setup_local_app.py`，然后要求 macOS target
`Audio2TextApp` 和 iOS/iPad simulator target `Audio2Text-iOS` 都能 Debug 编译通过。

输出位置：

```text
Audio2Text.xcodeproj/
build/app/Audio2Text.app
build/package/Audio2Text_v<MARKETING_VERSION>_<ARCHIVE_ID>.dmg
```

## 打包 DMG

官网分发包使用 Developer ID 签名，不走 App Store sandbox。发布机需要先安装
`Developer ID Application` 证书，并用 `notarytool` 把 Apple 凭据保存为 Keychain profile：

```bash
xcrun notarytool store-credentials "Audio2Text Release"
```

Developer ID 打包会启用 hardened runtime 和安全时间戳，随后依次执行 notarization、
staple、stapler validation 和 Gatekeeper assessment；任一步失败都会以非零状态退出。

命令行发布包：

```bash
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution developer-id --notary-profile "Audio2Text Release"
```

该命令先构建 `build/app/Audio2Text.app`，再用 `hdiutil` 生成：

```text
build/package/Audio2Text_v<MARKETING_VERSION>_<ARCHIVE_ID>.dmg
```

`MARKETING_VERSION` 和 `ARCHIVE_ID` 来自仓库根目录的 active `source_roots.lock.jsonc`。
这两个值也会写入 App bundle 的 `CFBundleShortVersionString` 和 `CFBundleVersion`。

签名行为：

- `--distribution developer-id` 是官网发布路径，选择 `Developer ID Application` 证书并开启 hardened runtime，不附加 App Sandbox entitlement。
- FreeCM 默认 `package` 仍使用 `--distribution development`，用于没有 Developer ID 证书的开发机本机验包。
- FreeCM 另提供 `Mac App DMG (Developer ID)`，用于发布机生成官网分发包。
- `development` 使用本机 `Apple Development` 证书签名，不附加 App Sandbox entitlement，只用于本机验包。
- `--distribution local` 不执行 `codesign`，等价于未签名/skip。
- `--distribution app-store` 仅保留给沙盒 entitlement 检查；当前项目不走 App Store 上架路径。

需要明确指定时：

```bash
# 官网分发包；需要本机安装证书并配置 notarytool Keychain profile
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution developer-id --notary-profile "Audio2Text Release"

# 本机验包；开发机没有 Developer ID 证书时使用
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution development

# 未签名包；等价 skip
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution local

# 沙盒 entitlement 检查包；当前非发布路径
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution app-store
```

## Qt Client 开发运行

Qt/QML 客户端可在 macOS 和 Windows 上通过 FreeCM 运行。FreeCM 的 `Run` 动作在 macOS
提供 `Mac Qt Client`，在 Windows 提供 `Windows Qt Client`；两者都会调用
`configs/qt_workflow.py` 完成 CMake 配置、构建并启动客户端。

直接运行命令：

```bash
python3 configs/qt_workflow.py run --configuration Release
```

Windows 上使用：

```powershell
python configs/qt_workflow.py run --configuration Release
```

如果 Qt 6 不能被 CMake 自动发现，设置 `AUDIO2TEXTQT_QT_PREFIX` 或 `CMAKE_PREFIX_PATH`
到 Qt 6 安装前缀。macOS 构建输出为 `build/Audio2TextQt/Audio2TextQt.app`，客户端默认从
`~/Documents/SpeechToTextData/env/bin/atot` 发现 CLI；Windows 默认从
`%USERPROFILE%\Documents\SpeechToTextData\env\Scripts\atot.exe` 发现 CLI。

FreeCM 的 `Package` 动作在 macOS 还提供 `Mac Qt Client ZIP`：

```bash
python3 configs/qt_workflow.py package --configuration Release
```

输出位置：

```text
build/package/Audio2TextQt_v<version>_macOS.zip
```

这个包包含 `Audio2TextQt.app`、部署后的 Qt 运行时，以及 bundle 内的 `ffmpeg` / `ffprobe`。

## Windows Qt Client 打包

Qt 发布前必须准备实际运行库的许可证、对应源码和构建材料清单；缺失或哈希不符时不会生成发布归档。
详见 [发布许可检查](doc/RELEASE_LICENSES.md)。Windows 上使用：

```powershell
python configs/qt_workflow.py package --configuration Release --third-party-materials build/release-materials/manifest.json
```

输出位置：

```text
build/package/Audio2TextQt_v<version>_Windows.zip
```

这个包包含 `Audio2TextQt` 客户端、Qt 运行时，以及和 `Audio2TextQt.exe` 同目录的
`ffmpeg.exe` / `ffprobe.exe`。打包脚本会从 `--ffmpeg-dir`、`AUDIO2TEXTQT_FFMPEG_DIR`、
`FFMPEG_DIR`、`VCPKG_ROOT` 或 PATH 中寻找这两个工具；找不到时会明确失败。

`atot.exe`、模型、转录结果和下载音频仍按本地运行时策略放在
`~/Documents/SpeechToTextData/` 下，或在客户端 Settings 中显式配置。客户端运行时会优先从程序所在目录发现
`ffmpeg` / `ffprobe`，再回退到本地环境和 vcpkg 工具路径。

需要给用户提供只需自行放置模型的包时，使用包含 Python 运行时的变体：

```powershell
python configs/qt_workflow.py package --configuration Release --include-python-runtime --third-party-materials build/release-materials/manifest.json
```

输出位置：

```text
build/package/Audio2TextQt_v<version>_Windows_Runtime.zip
```

这个变体要求干净的 Python 发行安装目录，并复制其中的运行时并安装 Audio2Text CLI 运行依赖到包内 `python/`，
客户端会自动通过 `python\python.exe -m atot.cli` 启动 CLI。模型、转录结果、下载音频和
运行时数据仍保留在 `~/Documents/SpeechToTextData/`。

SwiftPM 快速检查：

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift run --scratch-path ../build/swiftpm Audio2TextApp
```

更多 App 行为见 `app/README.md`。

## 使用 Codex 总结与回写（无需 API Key）

App 默认处理动作和 `Command-Return` 只运行本地转录与 QA。完成后，可以把总结交给 Codex。
Audio2Text 提供标准 MCP stdio 服务，旧的 `atot serve --stdio` 是内部 JSON 服务，两者协议不同。

先准备运行环境，再注册 MCP：

```bash
python3 configs/setup_local_app.py
codex mcp add audio2text -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get audio2text
```

Windows CLI 环境使用：

```powershell
python configs/setup_local_app.py
codex mcp add audio2text -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
```

重新加载 Codex 的 MCP 连接后，在对话中说：

连接配置和重新加载方式见 [Codex MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

> 使用 audio2text MCP，查找已转录但没有总结的节目，读完转录和 QA，生成中文总结并回写资料库。

指定节目时也可以通过 App 的 **Process → 复制 Codex 总结回写指令** 获取该节目的指令。
已有总结只有明确要求重新生成时才允许覆盖。

| MCP tool | 用途 |
|---|---|
| `list_episodes` | 按标题查询、分页列出节目；`needs_summary=true` 查找待总结转录 |
| `get_episode` | 获取节目元信息、QA 状态和转录/总结版本 |
| `read_document` | 分页读取完整转录、已有总结或 QA；检查跨页版本一致性 |
| `write_summary` | 保存 Codex 撰写的 Markdown；检查版本、更新资料库索引与工作副本 |

MCP 只访问所配置资料库的节目文本及对应本地 QA；不提供 API Key、音频、模型权重或任意文件读写。
回写更新 `episodes/<episode_id>/documents/summary.md`，保留转录、标题、收藏和阅读状态；本地
`work/<episode_id>/summary.md` 同步更新，`agent-summary.json` 记录作者和版本指纹。
App 可通过 **Refresh Library** 查看更新后的总结，iCloud Library 按原有规则同步。
MCP 服务不会自行调用模型；总结由 Codex 当前模型完成，所读取文本进入该 Codex 对话的处理范围。

本地转录仍使用 `atot exec transcribe ... --local-only` / `atot exec import ... --local-only`。
长音频通过 CLI 完成本地转录后，再调用 MCP 读取和总结。

## 云端文本阶段

云端阶段只处理文本包，默认不调用 API：

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec cloud prepare ~/Documents/SpeechToTextData/work/<batch>/<episode>
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec cloud summarize ~/Documents/SpeechToTextData/work/<batch>/<episode>
```

调用 OpenAI-compatible 接口前，在 App 设置中配置 Cloud Model，或用 CLI 设置。
macOS App/CLI 共用 Keychain；Windows CLI 使用 Credential Manager。`config.toml` 只保存
存储标记和非敏感配置；旧明文 key 会在安全存储成功后迁移并移除，失败则保留原文件并报错：

```toml
[cloud]
api_base = "https://api.example.com/v1"
api_key = ""
api_key_store = "system"
model = "gpt-5.4-mini"
model_options = ["gpt-5.4-mini", "gpt-5.4", "gpt-5.5", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]
```

```bash
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli config set cloud.api_base '"https://api.example.com/v1"'
# 通过隐藏输入交给 stdin，避免 key 进入 shell 历史
read -s "ATOT_KEY?Cloud API key: "
printf '%s' "$ATOT_KEY" | atot config set cloud.api_key --stdin
unset ATOT_KEY
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli exec cloud summarize ~/Documents/SpeechToTextData/work/<batch>/<episode> --call-api
```

App 默认不检查云端 API；`workflow.default_cloud_summary=true` 且 `workflow.local_only=false`
时才执行启动云端检查。只有明确选择云 API 总结动作并配置 Key，或显式启用 CLI 的云端阶段后，
才发送转录文本。MCP 总结流程使用 Codex 对话，不使用或转交该 Key。隐私边界见 `doc/PRIVACY.md`。

### 本地 HTTP 服务

优先使用 `atot mcp` 或 `atot serve --stdio`。需要旧 JSON HTTP 接口时，生成随机 token 后启动：

```bash
export ATOT_HTTP_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
atot serve --http --host 127.0.0.1 --port 8765
```

所有请求需要 `Authorization: Bearer <ATOT_HTTP_TOKEN>`；POST 还需要 `Content-Type: application/json`。
只允许 loopback 监听和对应的 Host，拒绝带 Origin 的浏览器请求，不提供 CORS。
HTTP token 独立于云端 API key；HTTP 接口包含删除和配置操作，请仅交给可信本地客户端。

## 同类项目与功能对比

以下对比覆盖通用转录软件、播客处理工具和自托管知识库，便于判断不同场景的适用性。
核对日期为 **2026-10-12**；功能依据各项目默认分支的 README、相关文档及少量入口代码，
AtoT 依据本仓库当前实现。未对这些项目运行同一套中文播客测试，因此不对识别准确率、
转录速度或摘要质量做数值排名。**“未说明”表示所查文档未明确承诺该能力，不等于确认不支持。**

### 项目与维护快照

Stars 和最近推送来自 GitHub API 的 `stargazers_count` / `pushed_at`，是本次查询的静态快照。
推送日期已转换为北京时间（UTC+8），并不等同于最近发布版本或核心功能更新时间；Stars
表示关注度，不能替代质量评测。许可列仅记录仓库声明，不涵盖下载模型的许可。

| 项目 | Stars | 最近推送（北京时间） | 主要定位 | 仓库声明许可 |
|---|---:|---|---|---|
| [Buzz](https://github.com/chidiwilliams/buzz) | 21,948 | 2026-10-11 | 跨平台桌面转录、实时音频与字幕 | MIT |
| [Vibe](https://github.com/thewh1teagle/vibe) | 7,759 | 2026-10-06 | 跨平台本地转录、多模型与 AI 分析 | MIT |
| [Speakr](https://github.com/murtaza-nasir/speakr) | 4,082 | 2026-10-12 | 自托管录音、知识问答与团队协作 | AGPLv3 / 商业双许可 |
| [MinusPod](https://github.com/ttlequals0/MinusPod) | 472 | 2026-10-12 | 广告识别、音频裁剪与 RSS 重发布 | MIT |
| [podcast-bridge](https://github.com/Hatari130/podcast-bridge) | 91 | 2026-07-05 | Agent Skill、小宇宙/RSS 与本地文本库 | MIT |
| [podHarvest](https://github.com/Community-Access/podharvest) | 1 | 2026-09-06 | 播客归档、转录、章节与无障碍阅读 | MIT |
| [ai-podcast-ripper](https://github.com/mbjornson/ai-podcast-ripper) | 0 | 2026-09-29 | Mac 本地模型驱动的播客自动处理 | GitHub 未识别 |
| [MediaBrief](https://github.com/EvilIrving/mediabrief) | 1 | 2026-09-09 | macOS 媒体链接、字幕优先与 AI 摘要 | MIT |
| [Lumina](https://github.com/brentonmallen1/lumina) | 0 | 2026-07-02 | 自托管多种内容提取、摘要与问答 | README 标注 MIT |

### 转录、播客与总结

项目名链接至对应功能文档。表中“本地”指相应处理阶段的位置；启用云 ASR、云 LLM 或
外部 Agent 后，音频或文本的数据路径随之改变。AtoT 的 Codex MCP 路径无需在 AtoT 填写
模型 API Key，但总结文本会进入 Codex 对话，不代表模型在本机推理。

| 项目 | 界面 / 部署 | ASR / 输入处理 | RSS 与新节目发现 | 总结执行方式 | 字幕与主要导出 |
|---|---|---|---|---|---|
| **AtoT** | macOS 原生 App + CLI/TUI；Windows CLI | 本地 MLX Whisper / faster-whisper | 小宇宙导入、RSS 订阅与手动刷新 | Codex MCP；可选云 API | SRT/VTT、Markdown、JSON |
| [Buzz][compare-buzz] | macOS / Windows / Linux 桌面 | 本地多种 Whisper 后端；麦克风实时转录 | RSS 未说明；支持目录监听 | AI 摘要插件 | TXT、SRT、VTT |
| [Vibe][compare-vibe] | macOS / Windows / Linux 桌面 | 本地 Whisper、Nemotron、Parakeet；系统音频/麦克风 | RSS 未说明；支持媒体网站链接 | Ollama 本地分析；Claude API | SRT/VTT、TXT、DOCX/PDF 等 |
| [Speakr][compare-speakr] | 自托管 Web/PWA；Docker | 自托管 WhisperX 或多种云 ASR | RSS 未说明；目录自动导入 | 本地 Ollama 或模型 API；可定制提示词 | 模板化文件导出 |
| [MinusPod][compare-minuspod] | 自托管 Web；Docker | 本地 faster-whisper / Parakeet 或远端 ASR | RSS 轮询、可选 Podping、重建订阅源 | LLM 主要用于广告检测与复核 | 去广告音频/RSS、转录与章节 |
| [podcast-bridge][compare-bridge] | Python CLI + Agent Skill | 默认必剪云 ASR；也支持剪映接口 | 小宇宙、RSS 管理与显式同步 | Agent 阅读全文后撰写 | 带时间戳 Markdown / Obsidian 笔记 |
| [podHarvest][compare-harvest] | wxPython 桌面 + CLI；重点验证 Windows | 本地 Whisper/Parakeet 等；可用源站转录或云模型 | RSS/OPML；收藏源手动检查更新 | 可选本地 llama.cpp 增强；可选云模型 | SRT/VTT、Markdown/HTML/TXT/JSON 等 |
| [ai-podcast-ripper][compare-ripper] | macOS Python CLI + 本地仪表盘 | 本地 oMLX Whisper / faster-whisper | RSS 增量处理、历史补录；可配 LaunchAgent | 本地 oMLX / Ollama | Markdown 摘要、独立 TXT 全文 |
| [MediaBrief][compare-mediabrief] | macOS Apple Silicon App | 优先取原字幕；无字幕时本地 mlx-whisper | RSS / YouTube 频道与任务队列 | LLM 接口；可自配 OpenAI 兼容服务 | Markdown、TXT、DOCX/PDF；媒体字幕下载 |
| [Lumina][compare-lumina] | 自托管 Web；Docker | 本地 faster-whisper / Whisper / Canary / Qwen Audio | RSS 自动监控与转录 | Ollama；多种摘要模式 | TXT、SRT、VTT |

### 自动化、检索与质量控制

| 项目 | CLI / API / Agent 接入 | 批处理与调度 | 检索、知识管理与协作 | 说话人分离 | 审校、质量或恢复机制 |
|---|---|---|---|---|---|
| **AtoT** | CLI、内部 JSON 服务；MCP 分页读取与版本化总结回写 | App 批处理；调度由外部工具执行 | 标题查询、分组、阅读/收藏、iCloud；无内置跨节目语义问答 | 稳定 ASR 后端不支持；实验模块未晋升 | QA 门禁、修正规则审计、定向 repair、回写版本检查 |
| [Buzz][compare-buzz] | CLI 与插件；MCP 未说明 | 任务队列、目录监听 | 稿件内搜索与播放；跨节目知识问答未说明 | 支持 | 语音分离、转录查看器；统一 QA 门禁未说明 |
| [Vibe][compare-vibe] | CLI、HTTP API、Agent skills；MCP 未说明 | 多文件批转录 | 稿件分析；跨节目语义库未说明 | 支持 | VAD 稳定时间戳模式；统一 QA 门禁未说明 |
| [Speakr][compare-speakr] | REST API、Webhooks；内部研究 Agent；MCP 未说明 | 自动导入、作业队列、批量操作 | 跨库语义搜索/问答、标签、SSO 与多人共享 | 支持；后端相关 | 词表/热词、说话人管理、编辑与保留策略 |
| [MinusPod][compare-minuspod] | REST/OpenAPI、Webhooks；MCP 未说明 | RSS 自动队列与定时处理 | 节目/广告模式搜索、历史与成本统计 | 未说明 | 广告置信度、人工复核、二次验证、备份与重试 |
| [podcast-bridge][compare-bridge] | CLI + Claude/Codex 等 Agent Skill；MCP 未说明 | 分片并发；订阅操作由 Agent/CLI 驱动 | SQLite 本地全文搜索、元数据搜索、Obsidian 输出 | 文档明确不区分 | 转录前自检、订阅源校验；摘要需 Agent 读完整稿 |
| [podHarvest][compare-harvest] | CLI；MCP/公共 HTTP API 未说明 | 按源或目录批处理；无后台订阅定时轮询 | 跨稿全文检索、音频定位、收藏与文件归档 | 可选多种后端 | 下载校验、模型 benchmark、转录/章节编辑 |
| [ai-podcast-ripper][compare-ripper] | CLI 与仪表盘；MCP 未说明 | 增量批处理、历史补录、LaunchAgent 调度 | 全文关键词搜索、摘要语义搜索、每日汇总 | 未说明 | 长稿分块总结、可重试状态、失败隔离 |
| [MediaBrief][compare-mediabrief] | 后端 HTTP 接口、Telegram/Slack bots；MCP 未说明 | 统一任务队列、RSS 批量入队 | SQLite 历史搜索、来源筛选；跨库语义问答未说明 | 未说明 | 保留原文、无需重新转录即可重试、LLM 输出清理 |
| [Lumina][compare-lumina] | HTTP/OpenAPI；MCP 未说明 | 多文件队列、RSS 自动监控 | SQLite FTS5 历史搜索、单份内容问答 | 可选 pyannote；需 HF Token | 降噪/人声分离等音频增强；统一 QA 门禁未说明 |

两处容易混淆的边界：podcast-bridge 默认的“免 Key”来自必剪云 ASR，音频仍会上传，
其 `--summary` 当前只表达摘要风格，实际摘要由 Agent 生成，见
[入口代码](https://github.com/Hatari130/podcast-bridge/blob/main/transcribe.py) 与
[Skill](https://github.com/Hatari130/podcast-bridge/blob/main/SKILL.md)。podHarvest 的收藏源是
手动检查的新节目书签；其本地 LLM 增强、字幕及说话人后端细节见
[模型目录](https://github.com/Community-Access/podharvest/blob/main/docs/MODELS.md) 与
[技术参考](https://github.com/Community-Access/podharvest/blob/main/docs/REFERENCE.md)。

### 场景评价

以下是基于上述能力的适配判断，不是统一基准测试的获胜排名。

| 使用场景 | 优先考察的项目 | 主要取舍 |
|---|---|---|
| 中文播客、本机 ASR、可审计修复、交给 Codex 总结回写 | AtoT | 需准备本地模型；稳定 GUI 以 Mac 为主，内置语义问答与多人协作仍是缺口 |
| 多平台日常音视频转录、实时音频与字幕制作 | Buzz、Vibe | 桌面输入与模型选择更广；RSS 播客资料库能力应另行核对 |
| 自托管知识问答或团队共享 | Speakr、Lumina | Speakr 偏跨库问答与协作，Lumina 偏多种内容分析；需部署服务及配置模型 |
| 自动去广告并继续在播客播放器收听 | MinusPod | 广告识别与重发布是核心；不适合作为纯摘要工具的等价替代 |
| Agent 管理小宇宙/RSS，或保留可搜索文件库 | podcast-bridge、podHarvest | 前者偏 Skill 驱动且默认云 ASR；后者偏本机归档、无障碍阅读与手动控制 |
| Mac 播客自动汇总，或视频链接快速阅读 | ai-podcast-ripper、MediaBrief | 前者偏本地模型与定时处理；后者偏字幕优先和多平台链接，摘要的数据路径依模型服务 |

[compare-buzz]: https://github.com/chidiwilliams/buzz/blob/main/README.md
[compare-vibe]: https://github.com/thewh1teagle/vibe/blob/main/README.md
[compare-speakr]: https://github.com/murtaza-nasir/speakr/blob/master/README.md
[compare-minuspod]: https://github.com/ttlequals0/MinusPod/blob/main/README.md
[compare-bridge]: https://github.com/Hatari130/podcast-bridge/blob/main/README.md
[compare-harvest]: https://github.com/Community-Access/podharvest/blob/main/README.md
[compare-ripper]: https://github.com/mbjornson/ai-podcast-ripper/blob/main/README.md
[compare-mediabrief]: https://github.com/EvilIrving/mediabrief/blob/main/README.md
[compare-lumina]: https://github.com/brentonmallen1/lumina/blob/main/README.md

## 开发检查

```bash
~/Documents/SpeechToTextData/env/bin/python -m ruff check .
~/Documents/SpeechToTextData/env/bin/python -m pytest
~/Documents/SpeechToTextData/env/bin/python src/scripts/check_public_paths.py
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_run_json.py src/tests/fixtures/run.sample.json
```

候选后端、gold benchmark、修复审计和云端包验证属于实验/验收流程，入口脚本保留在
`src/scripts/`，已完成能力和验收映射见 `doc/ROADMAP_STATUS.md`。

## 维护入口

只有存在明确、可执行的未完成工作时才创建或保留根目录 `TODO.md`；历史实验记录保留在
`doc/experiments/`；已实现能力和验证映射见 `doc/ROADMAP_STATUS.md`；文档地图见
`doc/README.md`。

## 项目结构

- `src/atot/`：CLI、转录管线、QA、修复、云端文本阶段。
- `src/atot/backends/`：ASR 后端适配层。
- `src/atot/candidate/`：候选后端比较和门禁复用逻辑。
- `src/atot/data/`：模型清单、默认提示词、主题和审阅规则。
- `src/scripts/`：验证、benchmark、候选后端实验入口。
- `app/`：SwiftUI macOS App。
- `configs/`：本地环境、FreeCM、App 构建和打包脚本。
- `doc/`：文档索引、隐私说明、技术说明、实验记录。

## 文档索引

- `AGENTS.md`：贡献者和 coding agent 规则。
- `doc/README.md`：文档地图。
- `doc/PRIVACY.md`：本地数据和云端摘要边界。
- `doc/BACKEND_RESEARCH.md`：ASR 后端研究和候选评估。
- `doc/ROADMAP_STATUS.md`：已实现能力和验证映射。

## License

本项目原创源码使用 [MIT](LICENSE)。依赖、模型和媒体适用各自的许可，详见
[第三方说明](THIRD_PARTY_NOTICES.md)及[发布许可检查](doc/RELEASE_LICENSES.md)。
