# 下载与安装

先选择适合电脑的客户端；需要处理音频时，再准备独立的转写运行环境。只浏览已有资料库，不必先准备模型或模型 API Key。

## 发布版与当前源码 {#release-and-current-source}

[已发布的 v0.9.0](https://github.com/NorthBoundWisdom/sonafolio/releases/tag/v0.9.0) 提供四种桌面安装包。[GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) 是版本、校验和及发布说明的依据。

本手册也介绍 v0.9.0 之后的当前源码功能：前两列调宽与折叠、紧凑 macOS 工具栏、转写语言复选框、总结输出语言选择器。使用这些功能需构建当前源码；官网更新不会替换你已经下载的 App。

| 平台 | v0.9.0 安装包 | 包内能力 |
| --- | --- | --- |
| macOS / Apple Silicon | [Swift DMG](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioSwift-v0.9.0-macOS-arm64.dmg) | 原生 App 和 CLI wheel；Python、媒体工具及模型仍需准备 |
| macOS / Apple Silicon | [Qt DMG](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-macOS-arm64.dmg) | Qt 客户端和 Qt 库；处理依赖外部 CLI |
| Windows / x64 | [Qt 安装器](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-Windows-x64-Setup.exe) | Qt 客户端，并安装 Microsoft VC++ 运行库；CLI 独立配置 |
| Linux / x86_64 | [Qt AppImage](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-Linux-x86_64.AppImage) | Qt 客户端；尚无稳定 Linux ASR 后端 |
| iOS / iPadOS 17+ | 源码构建 | 资料库阅读与订阅管理；没有自动 IPA、App Store 或 TestFlight 分发 |

所有安装包都不包含模型权重。Actions 测试产物与正式发布包不同，下载测试产物可能需要 GitHub 登录。

## 校验安装包

从同一 release 下载 [SHA256SUMS](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SHA256SUMS)，比较所选文件的校验和。每个包对应的 `.build.json` 记录源码标签和构建信息。

macOS 在下载目录执行：

```bash
shasum -a 256 SonaFolioSwift-v0.9.0-macOS-arm64.dmg
```

Windows：

```powershell
Get-FileHash .\SonaFolioQt-v0.9.0-Windows-x64-Setup.exe -Algorithm SHA256
```

Linux：

```bash
sha256sum SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
```

比较的是该平台、该文件的条目。校验和确认文件与发布字节一致；运行前仍应阅读来源与发布说明。

## macOS / Apple Silicon {#macos-apple-silicon}

原生 App 要求 macOS 13+；已验证的本地中文 ASR 主路径与自动 macOS 安装包面向 Apple Silicon。偏好原生工作区可选 Swift，需要跨平台客户端可选 Qt。

1. 打开 DMG，将 App 拷入 Applications。
2. 启动 SonaFolio。发布包使用 ad-hoc 签名，没有 Apple 公证。确认来源可信后，如系统阻止启动，可用系统 **Privacy & Security → Open Anyway** 流程放行。
3. 需要本地处理时，准备下文的 CLI、[模型和 FFmpeg](models.md)，执行 `atot doctor`。
4. 原生 App 打开 **Settings → Overview**，检查模型、CLI 与音频工具。可选 Cloud Summary 未配置不妨碍本地转写。
5. Qt Settings 中选择外部 `atot`，默认安装位置为 `~/Documents/SpeechToTextData/env/bin/atot`。

原生 App 的兼容入口仍叫 `Audio2TextCli`；这是保留的内部名称。随 App 的 wheel 不包含 Python、FFmpeg 或模型文件。

## Windows / x64 {#windows-x64}

1. 运行 Qt EXE，按安装器提示安装客户端和 Microsoft Visual C++ Redistributable。安装器未签名，系统可能显示发行者提醒。
2. 准备 Python 与 CLI；Windows 安装不依赖 Swift 或 Xcode。
3. 通过 PATH 或 vcpkg 提供 `ffmpeg.exe`、`ffprobe.exe`。
4. 手动准备 [faster-whisper 模型](models.md#windows-faster-whisper)。
5. 运行托管环境的 `atot.exe doctor`，并在 Qt Settings 选择同一可执行文件。
6. 准备与 CTranslate2 匹配的 CUDA/cuDNN，或明确选择 CPU。

默认 Windows 后端是 faster-whisper，设备 `cuda`，计算类型 `int8_float16`。缺少 CUDA 不会静默改用 CPU。需要 CPU 时显式设置：

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

变量影响从该环境启动的命令与 App。独立桌面快捷方式不会自动继承另一 PowerShell 会话的设置。参见 [CUDA 排查](guides/troubleshooting.md#windows-cuda-or-cudnn-is-missing)。

## Linux / x86_64 {#linux-x86_64}

AppImage 面向 Ubuntu 24.04 或兼容的 glibc/桌面基础。在下载目录执行：

```bash
chmod +x SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
./SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
```

没有 FUSE 时，可使用发布包支持的解包运行方式：

```bash
./SonaFolioQt-v0.9.0-Linux-x86_64.AppImage --appimage-extract-and-run
```

这是客户端支持，不代表 Linux 转写后端已经通过稳定晋升。可以浏览已有资料库；ASR 能力以[平台说明](handbook.md)为准。

## 从源码配置 CLI {#set-up-the-cli-from-source}

要求 Python 3.10+，CI 使用 Python 3.13。递归克隆仓库，保留构建基础设施：

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

Windows 用 `python` 替换 `python3`。初始化创建本地托管环境和配置，不自动下载模型权重。

macOS：

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

Windows：

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

Windows 可按本机 shell 策略激活 `Scripts\Activate.ps1`，或始终使用完整可执行文件路径。不要把另一个全局 Python/atot 的结果误认为托管环境的结果。

## 构建当前 macOS 原生 App

安装 Xcode 后，在仓库根目录执行：

```bash
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp \
  --configuration debug --distribution ad-hoc
```

打开 `build/app/SonaFolio.app`。这生成当前源码的本地 ad-hoc 签名版本，不创建新的 GitHub release。Qt 与 iOS 构建入口见[开发说明](development.md)。源码更新后重新构建并重启 App，再检查新增界面功能。

## 检查是否准备好

| 检查 | 应看到什么 |
| --- | --- |
| 客户端 | 可以打开并读取所选资料库 |
| `atot doctor` | 必需后端、工具和模型可用 |
| `atot models` | 当前模型文件完整地位于 `model/` |
| 一次中文短音频转写 | 无云 Key 也能生成转写与 QA |

[准备模型与工具 →](models.md) · [首次中文转写 →](quick-start.md)
