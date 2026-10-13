# 第一次中文转写

先用一段较短、声音清楚的中文本地录音验证流程。确认能生成转写与 QA，再处理长节目或整个订阅队列。尚未准备环境时，先阅读[安装](install.md)和[模型与工具](models.md)。

## 1. 检查环境

```bash
atot doctor
atot models
```

先解决 CLI、后端、模型、FFmpeg/ffprobe 的必需项错误。使用本地转写或 MCP 总结时，可选 Cloud Summary 未配置是正常状态，不必为此填写 Key。

原生 App 打开 **Settings → Overview**；Qt 可使用 Settings 的 Doctor，并确认外部 CLI 路径。[排查指南](guides/troubleshooting.md)说明 App 与终端结果不一致时如何定位。

## 2. 导入一份来源

原生 App 选择 **New Item**（`Command-N`），导入本地媒体或支持的单集链接，并选择分组。导入建立来源记录；处理才生成转写。订阅里看到单集元数据不代表已有音频或转写。

CLI 本地文件：

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
```

小宇宙单集：

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --language zh --local-only --json
```

替换示例路径和单集 ID。链接导入需要联网获取元数据与音频；随后 ASR 在本机处理。Apple Podcasts 节目和 RSS 地址使用订阅入口，CLI `exec import` 接收小宇宙单集链接。

## 3. 选择中文提示

当前源码的 **Settings → Local ASR → Transcription Languages** 可以勾选 **Chinese / Mandarin**，复现本手册的中文主路径。

不勾选时自动识别；勾选多个时自动识别并提供混合语言提示，保留各语言原文。当前新配置默认自动识别，但这不是宣称各种语言均已验证。旧的明确语言配置继续保留。

v0.9.0 的界面没有新增复选框和总结语言选择器，仍可使用单个 `--language zh`。详见[语言设置与版本区别](guides/languages.md)。

## 4. 运行本地转写

原生 App 选中条目，选择 **Transcribe locally only**，或使用 `Command-Return`。观察处理卡片与日志中的阶段。下载结束、ASR 正在处理某个块、整个任务结束是不同状态；不要因为长节目耗时就重复启动同一任务。

上面的 CLI 例子会执行本地转写与 QA，`--local-only` 明确跳过可选云总结，不需要模型 API Key。

## 5. 阅读并核对

打开 **Transcript** 阅读转写，**Overview** 查看来源、节目、发布时间和时长；**Summary** 只有总结生成后才有对应内容。

CLI 会报告实际工作目录。复制那一目录用于以下命令，不要猜测单集 ID：

```bash
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
atot exec library status --json
```

| 产物 | 用途 |
| --- | --- |
| `transcript.readable.md` | 阅读文本 |
| `transcript.timestamped.md` | 按时间找到原音频片段 |
| `transcript.srt` / `transcript.vtt` | 字幕 |
| `qa.json` | 自动质量检查 |
| `corrections.json` | 确定性修改记录 |
| 资料库 `documents/transcript.md` | 发布到资料库的阅读文档 |

复听关键人名、数字、观点与引用。QA 通过说明程序检查通过，并不保证逐字准确。需要修复时先看计划，再决定是否重跑相应窗口。

## 6. 需要时再生成总结

选择 [Codex/MCP 回写](guides/agent-summary.md)，使用当前 agent 会话模型，无需 SonaFolio Key；或选择[云 API 总结](guides/cloud-summary.md)，配置自己使用的服务。

要求总结基于完整转写、保留有用时间戳、说明不确定性。总结与完整转写分开保存。

一次短音频成功后，再尝试[订阅队列](guides/library.md)、[字幕导出](guides/subtitles.md)或[iOS 阅读](guides/ios.md)。
