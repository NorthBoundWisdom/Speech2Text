# SonaFolio 文档索引

[官网与用户手册](https://northboundwisdom.github.io/sonafolio/)面向安装、转录、资料库和 Agent 总结。
[仓库 README](../README.md)是快速开始、模型下载清单和稳定 CLI 参考。

## 用户与数据

| 文档 | 内容 |
| --- | --- |
| [README](../README.md) | 平台支持、环境、模型与 CLI 用法 |
| [隐私与数据](PRIVACY.md) | 本地、iCloud、MCP 与可选云 API 的数据边界 |
| [资料库布局](LIBRARY_LAYOUT.md) | JSON / Markdown 权威库、处理缓存和删除标记 |
| [QA 与修复](QUALITY_LOOP.md) | 审阅、修正规则与定向修复 |
| [品牌与兼容标识](BRANDING.md) | SonaFolio 与保留旧标识的关系 |

## 开发与发布

| 文档 | 内容 |
| --- | --- |
| [架构](ARCHITECTURE.md) | CLI、Swift、Qt、MCP 与 ASR 模块边界 |
| [开发指南](TECHNICAL_GUIDE.md) | 构建、源码接口、验证与扩展 |
| [Agent 约定](../AGENTS.md) | 仓库维护政策与公开路径要求 |
| [Swift 客户端](../app/README.md) | macOS / iOS 客户端构建与运行 |
| [Qt 客户端](../qt/Audio2TextQt/README.md) | CMake、SDK 与客户端打包 |
| [CI 与安装包](CI_RELEASES.md) | 四平台构建、签名与 tag 发布 |
| [官网与 Pages](WEBSITE.md) | 本地预览、严格构建与自动部署 |
| [发布许可](RELEASE_LICENSES.md) | 第三方源码、许可和产物验证 |
| [开源审计](OPEN_SOURCE_AUDIT.md) | 当前源码审计结果与验证边界 |
| [质量工具](QUALITY_TOOLS.md) | Ruff、mypy、依赖审计与测试 |

## 研究与历史

- [功能状态](ROADMAP_STATUS.md)记录完成项与验证证据。
- [后端研究](BACKEND_RESEARCH.md)记录候选门禁，不作为安装指南。
- [实验索引](experiments/README.md)说明记录日期和历史名称，保留实测结果。
- [术语示例](examples/glossary.zh.json)、[QA 示例](examples/qa.balanced.json)与
  [ASR 提示词](../src/atot/data/prompt.zh.txt)是当前可访问的参考文件。
- 云文本模板位于 `cloud_prompts/`；处理后的云包与本机工作数据不能提交。

文档优先描述当前源码行为；具体下载包以相应 release 说明为准。历史测量不代表当前平台、
模型或软件版本的支持承诺。新增功能应同步更新相应用户指南和验证入口。
