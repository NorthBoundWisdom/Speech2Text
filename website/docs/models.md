# 模型与媒体工具

客户端、ASR 后端、模型文件和媒体工具是独立部分。先准备齐全，再开始长节目。本项目以 Apple Silicon Mac 上的中文播客流程为已验证主路径，默认模型是 `large-v3-turbo`。

## 选择对应后端

| 电脑 | 处理路径 | 模型目录 |
| --- | --- | --- |
| Apple Silicon Mac | MLX Whisper；中文稳定主路径 | `model/whisper-large-v3-turbo/` |
| Windows | faster-whisper / CTranslate2；运行时独立配置 | `model/faster-whisper-large-v3-turbo/` |

数据根目录默认为 `~/Documents/SpeechToTextData/`，Windows 对应用户 Documents 目录。模型只能存入其中的 `model/`；仓库 `Downloads/` 是临时参考位置，不参与正常模型解析。

模型不随安装器分发，也不由转写流程自动下载。请手动下载下表中的确切文件。

## macOS / MLX Whisper {#macos-mlx-whisper}

来源：[mlx-community/whisper-large-v3-turbo](https://huggingface.co/mlx-community/whisper-large-v3-turbo)。把下面文件放在同一模型目录：

| 数据根目录下的目标路径 | 手动下载 |
| --- | --- |
| `model/whisper-large-v3-turbo/config.json` | [config.json](https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/config.json?download=true) |
| `model/whisper-large-v3-turbo/weights.safetensors` | [weights.safetensors](https://huggingface.co/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors?download=true) |

不要混用另一后端的权重格式；不要把模型文件放进源码仓库。

## Windows / faster-whisper {#windows-faster-whisper}

来源：[h2oai/faster-whisper-large-v3-turbo](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo)。把下面文件放在同一模型目录：

| 数据根目录下的目标路径 | 手动下载 |
| --- | --- |
| `model/faster-whisper-large-v3-turbo/config.json` | [config.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/config.json?download=true) |
| `model/faster-whisper-large-v3-turbo/model.bin` | [model.bin](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/model.bin?download=true) |
| `model/faster-whisper-large-v3-turbo/preprocessor_config.json` | [preprocessor_config.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/preprocessor_config.json?download=true) |
| `model/faster-whisper-large-v3-turbo/tokenizer.json` | [tokenizer.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json?download=true) |
| `model/faster-whisper-large-v3-turbo/vocabulary.json` | [vocabulary.json](https://huggingface.co/h2oai/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json?download=true) |

不要混用另一后端的权重格式；不要把模型文件放进源码仓库。

## 配置 FFmpeg 与 ffprobe

两者都需要被执行任务的 CLI 找到。macOS 可使用 Homebrew：

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

Windows 可把已有工具安装目录加入 PATH，或通过 vcpkg 提供工具：

```powershell
vcpkg install "ffmpeg[ffmpeg,ffprobe]:x64-windows"
ffmpeg -version
ffprobe -version
```

Qt Settings 可以配置本机 vcpkg root。填写自己的路径，不要照抄别人的机器目录。Qt 库已随客户端分发，不代表媒体工具也已准备好。

## 转写前检查

```bash
atot models
atot doctor
```

`models` 展示别名与必需文件；`doctor` 同时检查运行时和工具。缺失文件按清单链接手动放置。不要通过改名把 `weights.npz` 当成 `weights.safetensors`，或把 `model.bin` 当成 MLX 权重：它们是不同格式。

通过 **Settings → Local ASR** 选择模型，或：

```bash
atot config set local.asr_model large-v3-turbo
```

改模型影响后续任务，不会自动重写已有转写。

## 资源与候选模型

先用默认模型完成中文短音频测试，再考虑对比模型。速度和内存占用取决于硬件、音频时长和后端，不承诺所有机器统一的实时倍速。

Windows 的 CUDA/cuDNN 必须满足实际 CTranslate2 wheel。装了 CUDA 13，不代表 wheel 要求的 CUDA 12 DLL 已存在；按 `doctor` 与缺失 DLL 消息处理。CPU 是[显式选项](install.md#windows-x64)。

模型清单还包含较小或实验模型。列入清单不等于通过生产晋升；不要把候选研究结果当成首次安装的推荐步骤。多语言选项同样不代表已完成逐语言效果验证。

## 更新与移动

权重留在 Git 外。移动数据根目录时一起移动 `model/`，然后用指向新根目录的 CLI 检查。清理缓存不应顺手删除模型。

[模型清单](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json) 是别名、目标路径和手动链接的依据。

[首次中文转写 →](quick-start.md) · [模型缺失排查 →](guides/troubleshooting.md#model-files-are-missing)
