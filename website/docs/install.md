# 下载与安装

从 [GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) 查看已发布版本、更新说明和 `SHA256SUMS`。没有版本时可从源码开始；Actions 的打包试跑产物需要登录 GitHub 下载，不能作为已发布版本的承诺。

## 选择客户端

| 平台 | 发布包 | 运行边界 |
| --- | --- | --- |
| macOS / Apple Silicon | `SonaFolioSwift-v<version>-macOS-arm64.dmg` | 原生 SwiftUI App，包含 CLI wheel；首次运行需要配置 Python 环境与模型 |
| macOS / Apple Silicon | `SonaFolioQt-v<version>-macOS-arm64.dmg` | Qt 客户端，CLI 与 FFmpeg 另行安装 |
| Windows / x64 | `SonaFolioQt-v<version>-Windows-x64-Setup.exe` | Qt 安装器，安装 Microsoft VC++ 运行时；Python、CLI、FFmpeg 与 ASR 依赖另行准备 |
| Linux / x86_64 | `SonaFolioQt-v<version>-Linux-x86_64.AppImage` | Ubuntu 24.04 或兼容系统的 Qt 客户端；Linux ASR 尚未晋升为稳定后端 |
| iOS / iPadOS 17+ | 从源码构建 | 阅读和订阅管理客户端；当前没有 App Store、TestFlight 或 IPA 自动发布 |

macOS 安装包使用 **ad-hoc 签名**，未经过 Developer ID 签名和 Apple 公证。Windows 安装器未签名。系统可能提示未识别的开发者；请从本仓库下载，核对校验和，并按系统提示选择是否允许打开。

Qt 安装包已经包含 Qt 运行时，不需要另外安装 Qt SDK 才能浏览资料库。模型不随任何安装包分发。

## 从源码准备 CLI

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

macOS 上激活运行环境，再检查依赖：

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

Windows 使用 Python 3.10+，将上面的 `python3` 改为 `python`，然后运行：

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

macOS 稳定转录需要 Apple Silicon。Windows 默认 faster-whisper / CUDA；若 CTranslate2 wheel 要求 CUDA 12 DLL，请按实际错误准备兼容运行时。CPU 是显式选择，不会在 CUDA 出错时自动切换。

## 放置模型和音频工具

模型统一放在 `~/Documents/SpeechToTextData/model/`。默认别名为 `large-v3-turbo`：

- macOS：`model/whisper-large-v3-turbo/`，至少包含 `config.json` 和 `weights.safetensors`。
- Windows：`model/faster-whisper-large-v3-turbo/`，所需文件与下载地址见源码中的[完整模型清单](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json)。

模型必须手动下载；运行检查不会替你下载模型。macOS 可使用 `brew install ffmpeg`；Windows 可通过 vcpkg 或 PATH 提供 `ffmpeg.exe` / `ffprobe.exe`。Qt 客户端在 Settings 中配置 `atot` 的可执行文件位置。

[完成第一次转录 →](quick-start.md)
