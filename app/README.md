# SonaFolio Swift 客户端

macOS 原生 App 执行本地导入、转录、QA 与资料库管理；iOS/iPadOS 客户端读取共享资料库并管理订阅与阅读状态。
产品名统一为 SonaFolio；Swift 模块与 Xcode scheme 保留兼容身份，见[品牌说明](../doc/BRANDING.md)。

## 构建与运行

在仓库根目录执行：

```bash
git submodule update --init --recursive FreeCM
python3 configs/source_root_workflow.py --init
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
```

SwiftPM 用于快速逻辑检查：

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift run --scratch-path ../build/swiftpm Audio2TextApp
```

最低 macOS 13 / iOS 17。本地 ASR 的稳定 macOS 路径要求 Apple Silicon。
iOS 模拟器构建使用 `--platform ios --scheme Audio2Text-iOS`；当前无 App Store 或 IPA 自动发行。

构建生成 `build/app/SonaFolio.app`，App 内保留兼容 CLI：

```text
build/app/SonaFolio.app/Contents/MacOS/Audio2TextCli
```

App 调用内部 `serve --stdio` JSON 服务；标准 MCP 是独立的 `atot mcp` 协议。
`Audio2Text.xcodeproj` 由脚本生成，不提交到 Git。

## 处理与总结

导入时选择链接或本地音视频并指定分组。导入后通过菜单执行处理、再处理、收藏、分组或删除。
详情展示简介、转录与已有摘要。默认处理动作与主要快捷键只执行本地转录和 QA，不需要云 API Key。

摘要推荐通过 `atot mcp` 交给 Codex：先读取完整转录与 QA，再带当前文档哈希回写。
已有非空摘要必须在用户明确请求重新生成后替换。MCP 不调用模型 API，读出的文本进入 Agent 会话。

可选云 API 总结必须显式启用并设置文本上传许可、API 地址、模型与安全存储的 Key。
设置页只有在用户点击检查，或明确启用自动云摘要的启动检查时调用云接口。
不要把可选云流程写成所有处理动作的默认后续步骤。

## 数据与模型

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
~/Documents/SpeechToTextData/Audio2TextLibrary/
~/Documents/SpeechToTextData/materials/<episode_id>/
~/Documents/SpeechToTextData/work/<episode_id>/
```

前两行分别是 iCloud 和本地存储模式的权威库；音视频与处理过程留在本机。
iOS 通过 Files 选择 `Audio2Text` 或 `Audio2TextLibrary` 并持久记录书签，可以刷新订阅元信息、
读取转录与摘要、管理阅读/收藏/归档/分组/删除，不运行 ASR 或下载处理音频。

默认模型为 `large-v3-turbo`，放置在数据根 `model/whisper-large-v3-turbo/`，包含
`config.json` 和 `weights.safetensors`。必须手动准备模型；下载清单见仓库 README。
日志在 `cache/logs/`，任务建立后同时写入对应 work 目录。

## 打包

```bash
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution ad-hoc
```

当前 Actions 生成 ad-hoc 签名 DMG，不需要证书、未公证。Swift 包包含 CLI wheel，运行时仍需
Python、FFmpeg 与模型。自有证书发行可显式使用 `developer-id` 和 notarytool profile。
详见[多平台发行](../doc/CI_RELEASES.md)、[隐私](../doc/PRIVACY.md)和[官网手册](https://northboundwisdom.github.io/sonafolio/)。
