# SonaFolio 中文使用手册

SonaFolio 将播客与本地音视频整理为可读转写、字幕和总结。播客积压时，你可以直接读转写，也可以让 Codex 先整理总结，再选择值得深入的原文或音频。本手册以已经验证过的中文播客流程为主。

## 两种阅读入口

- **直接读全文：** 导入并本地转写后，打开 Transcript，阅读关心的段落。
- **先看总结：** 转写后让 Codex 读取完整文本与 QA 并回写总结，你从 Summary 开始，再按时间戳追溯原文。

完整转写是总结的来源层，生成与阅读它可以交给软件和 agent；不要求用户先听完整集或通读逐字稿。关键结论仍应按需要核对来源。

## 使用前先确认

本地转写不需要模型 API Key。客户端能打开，与转写运行环境已经准备好，是两件事：CLI、FFmpeg、ASR 后端与模型文件都必须可用，任务才能开始。

当前稳定主路径是 **Apple Silicon Mac + MLX Whisper + `large-v3-turbo` + 中文播客**。Windows 的客户端和 CLI 另有运行时配置；多语言选项可以设置，但不等于每种语言都完成了与中文相同的效果验证。

手册同时说明当前源码功能。已发布的 **v0.9.0** 安装包早于可调宽度/折叠列、紧凑工具栏和新增语言设置；使用这些功能需要当前源码构建。截图来自真实 macOS 源码版本，节目标题与内容保留来源语言。参见[版本区别](install.md#release-and-current-source)。

## 按任务阅读

| 你现在要做什么 | 建议顺序 |
| --- | --- |
| 首次转写中文音频 | [安装](install.md) → [模型与工具](models.md) → [首次转写](quick-start.md) |
| 熟悉桌面 App | [工作区](guides/workspace.md) → [导入](guides/import.md) → [转写](guides/transcription.md) |
| 批量处理播客 | [资料库与订阅](guides/library.md) → [转写](guides/transcription.md) → [QA 与修复](guides/quality.md) |
| 不配 SonaFolio Key，让 Codex 总结 | [MCP 回写](guides/agent-summary.md) → [语言设置](guides/languages.md) |
| 使用自己的模型服务 | [云 API 总结](guides/cloud-summary.md) → [设置](guides/settings.md) |
| 导出字幕 | [字幕与翻译](guides/subtitles.md) → [转写语言](guides/languages.md) |
| 在手机或平板继续阅读 | [资料库](guides/library.md) → [iOS 阅读端](guides/ios.md) |
| 备份或迁移资料 | [存储与备份](guides/storage.md) → [隐私](guides/privacy.md) |
| 用脚本自动化 | [CLI](guides/cli.md) → [质量检查](guides/quality.md) |
| 排查失败 | [故障排查](guides/troubleshooting.md) → [常见问题](faq.md) |

## 理解三个层次

**来源与媒体。** 导入保存节目元数据和原始链接。音频下载、准备后的媒体存放在本地数据根目录。刷新订阅只说明拿到了元数据，不说明单集已经下载或转写。

**转写与审阅。** ASR 产出可读文本、时间戳、字幕、QA 和纠正记录。它是需要对照音频核验的原始资料层；总结不替代完整转写，QA 通过也不保证逐字正确。

**资料库与笔记。** 权威资料库包含单集记录、Markdown 文档、分组与阅读状态。可选 iCloud Drive 把资料库交给 iOS 阅读端；模型与工作缓存仍留在执行转写的电脑上。

## 选择总结路径 {#choose-a-summary-path}

| | Codex / MCP | 可选云 API |
| --- | --- | --- |
| 谁生成内容 | 当前 agent 会话的模型 | 你配置的服务端模型 |
| SonaFolio 的模型 API Key | 不需要 | 需要 endpoint、model 与 Key |
| 读取或发送什么 | 转写与 QA 进入 agent 会话 | 文本及支撑上下文发送到 API |
| 回写方式 | `write_summary` 检查当前文档哈希 | 显式云任务发布产物 |
| 已有总结 | 明确要求重新生成后才覆盖 | 明确选择重新生成 |
| 配置教程 | [MCP](guides/agent-summary.md) | [云总结](guides/cloud-summary.md) |

本地转写不会自动生成一份 Codex 撰写的总结。两条总结路径都应保留原文，并检查遗漏、外部补充与不确定性。

## 第一轮使用检查

1. 安装客户端与 CLI，执行 `atot doctor`。
2. 按对应后端把模型文件放入数据根目录 `model/`。
3. 选择中文提示，先对一段短音频运行本地转写。
4. 打开 Transcript，对照音频核对人名、数字和重要判断。
5. 选择 MCP 或云 API 总结；使用 MCP 时可保持云配置为空。
6. 决定资料库使用本地存储还是 iCloud，并安排独立备份。

网站最上方的“中文 / English”可切换当前页面的对应版本。网站搜索支持两套内容，也可以搜索命令、配置键或错误消息。实际 UI 按钮名、命令、目录和配置键保留英文，便于对照软件操作。

[从安装开始 →](install.md)
