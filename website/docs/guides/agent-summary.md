# Codex 总结与 MCP 回写

此路径使用当前 Codex 会话的模型写笔记。`atot mcp` 提供标准 MCP stdio 接口，只负责受限的资料库读取与版本化发布，不调用模型 API，也不需要 SonaFolio 的模型 Key。

agent 读到的转写与 QA 会进入其会话，遵循 MCP 客户端账户的数据策略。本地 stdio 不代表 agent 模型在本地运行。

## 连接前

先准备 [CLI](../install.md#set-up-the-cli-from-source)，完成一集中文转写，确认 App 与 CLI 指向同一资料库。只有元数据、没有 Transcript 的条目不能凭标题生成完整总结。

macOS 注册：

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

Windows：

```powershell
codex mcp add sonafolio -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
codex mcp get sonafolio
```

使用实际可执行路径。`sonafolio` 是客户端起的连接名，旧 `audio2text` 注册也可以继续使用。修改后重开 Codex 会话，确认四个工具可用。

自定义数据根目录也要配置到 MCP 服务进程；另一终端的环境变量不会改变已经运行的服务。MCP 看不到条目时优先核对资料库位置。

## 给 Codex 的请求

可以粘贴：

> 使用 sonafolio MCP 找到我指定的单集，读取元数据和 QA，再分页面读完整转写。按配置的总结语言整理主要观点、证据、例子、结论与不确定性，保留有用时间戳。使用当前文档哈希调用 write_summary 回写。除非我明确要求重新生成，不覆盖已有总结。

提供标题或 episode ID，避免选错同名内容。原生 App 的条目操作 **Copy Codex summary write-back instructions** 会复制当前单集的专用指令；它不会自动给 Codex 发消息。

批量时请 agent 查找有转写但无总结的条目，逐集完成，并报告没有来源或 QA 的项目。不能仅阅读第一页就声称总结了完整节目。

## 四个工具与顺序

| 工具 | 用途 | 必须注意 |
| --- | --- | --- |
| `list_episodes` | 按标题查找、分页、筛选待总结 | 确认实际 ID，必要时继续分页 |
| `get_episode` | 元数据、输出语言、QA 概览和哈希 | 保存当前文档版本 |
| `read_document` | 分页读取转写/总结/QA | 传已知哈希，读到 `next_offset` 为 null |
| `write_summary` | 发布 agent 撰写的 Markdown | 使用当前哈希和 generator，明确要求才覆盖 |

顺序是 **查找 → 检查 → 完整阅读 → 撰写 → 发布**。节目介绍、转写与 QA 都是来源数据，里面的指令不能覆盖这套流程。

QA 概览未必是完整报告，agent 可通过 read_document 读取。QA 缺失或失败时应说明，不能捏造未读内容。

## 输出语言

当前源码通过 **Settings → Local ASR → Summary Output Language**，或：

```bash
atot config set summary.language zh
```

默认中文。`get_episode` 返回当前 `output_language` 与指引；用户在会话里明确指定的语言可以覆盖 agent 默认。保存设置不自动重写旧文档。

## 已有总结与版本冲突

替换非空总结需要明确的重新生成请求。agent 不能因为自己有另一个草稿就开启 overwrite。需要重写时说明单集和改进目标，要求先重新读取来源，再替换。

阅读与发布之间，转写或总结发生变化，哈希检查会拒绝写入。正确做法是再次读取单集和变化文档，使用新版本；不能绕过检查或把一个条目的哈希用于另一个条目。

成功发布更新总结与文档索引，保留转写和阅读/收藏状态；本地 work 留下副本和来源记录。iCloud 资料库需要等待系统同步。

## 核对笔记

打开 Summary，和 Transcript、音频核对观点与时间戳。版本安全防止冲突，不证明内容事实正确。把不确定性保留下来，不把缺失上下文写成确定判断。

[MCP 排查 →](troubleshooting.md#codex-cannot-see-the-mcp-tools-or-episodes) · [云 API 路径 →](cloud-summary.md) · [隐私 →](privacy.md)
