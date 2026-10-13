# SonaFolio 文档入口

## 默认中文使用文档

### [中文官网](https://northboundwisdom.github.io/sonafolio/) · [完整使用手册](https://northboundwisdom.github.io/sonafolio/handbook/)

文档围绕已验证的 Apple Silicon / MLX Whisper 中文播客流程。界面按钮名、命令、配置键和兼容目录保持实际名称；多语言选项不等同于逐语言验证。

| 任务 | 中文教程 |
| --- | --- |
| 下载与运行 | [安装](../website/docs/install.md) · [模型](../website/docs/models.md) · [首次中文转写](../website/docs/quick-start.md) |
| 熟悉 App | [工作区](../website/docs/guides/workspace.md) · [设置](../website/docs/guides/settings.md) |
| 导入与批次 | [来源导入](../website/docs/guides/import.md) · [资料库和订阅](../website/docs/guides/library.md) |
| 转写与语言 | [转写](../website/docs/guides/transcription.md) · [语言设置](../website/docs/guides/languages.md) |
| 总结与回写 | [Codex/MCP](../website/docs/guides/agent-summary.md) · [云 API](../website/docs/guides/cloud-summary.md) |
| 字幕 | [SRT 与翻译](../website/docs/guides/subtitles.md) |
| 核对与排错 | [QA/修复](../website/docs/guides/quality.md) · [故障排查](../website/docs/guides/troubleshooting.md) |
| 阅读与资料保留 | [iOS](../website/docs/guides/ios.md) · [存储/备份](../website/docs/guides/storage.md) · [隐私](../website/docs/guides/privacy.md) |
| 脚本 | [CLI](../website/docs/guides/cli.md) · [README](../README.md) |

网站跟随当前源码，安装包以对应 release 为准。v0.9.0 早于新增列宽/折叠和语言控件。截图来自当前 macOS 源码版本。

## 开发与技术参考

下列工程资料保留英文技术原文；默认用户操作以中文手册为入口。

| 文档 | 内容 |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | CLI、Swift、Qt、MCP 与 ASR 边界 |
| [Technical guide](TECHNICAL_GUIDE.md) | 构建、接口与扩展 |
| [Agent guide](../AGENTS.md) | 开发政策与公共源码限制 |
| [Swift](../app/README.md) · [Qt](../qt/Audio2TextQt/README.md) | 客户端构建参考 |
| [CI releases](CI_RELEASES.md) | 四类安装包、签名与 tag 发布 |
| [官网维护](WEBSITE.md) | 中文页面、截图、预览、校验和 Pages |
| [Release licenses](RELEASE_LICENSES.md) | 第三方许可与产物核对 |
| [Open-source audit](OPEN_SOURCE_AUDIT.md) | 当前源码审计证据 |
| [Quality tools](QUALITY_TOOLS.md) | Ruff、mypy、依赖检查与测试 |
| [Privacy](PRIVACY.md) · [Library layout](LIBRARY_LAYOUT.md) · [Quality loop](QUALITY_LOOP.md) | 内部数据和质量契约 |
| [Branding](BRANDING.md) | 保留的兼容身份 |

## 研究与历史证据

[Roadmap](ROADMAP_STATUS.md)、[后端研究](BACKEND_RESEARCH.md)和[实验记录](experiments/README.md)保留原始测量，不为中文默认文档改写历史结论。历史数据不能证明当前版本、所有平台或语言都已验证。

[中文术语示例](examples/glossary.zh.json)、[QA 示例](examples/qa.balanced.json)、[ASR prompt](../src/atot/data/prompt.zh.txt)为语言资产。用户模型、音频、转写、输入包与 Key 不提交到 Git。
