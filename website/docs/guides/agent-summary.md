# Codex 总结与回写

`atot mcp` 是标准 MCP stdio 服务。它不调用云模型 API，总结由连接的 Agent 使用自己的模型完成。SonaFolio 不需要为这个流程配置 API Key。

## 连接

先准备本地 CLI。macOS 上，在 Codex 的终端中注册：

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

Windows：

```powershell
codex mcp add sonafolio -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
```

`sonafolio` 是客户端注册名称，可以自行选择。已注册为 `audio2text` 的连接继续有效，无需为了改名重复注册。重新打开 Codex 会话后确认工具可用。

## 请求总结

可向 Codex 提出：

> 使用 sonafolio MCP，查找已转录但没有总结的节目。读完整转录与 QA，生成中文 Markdown 总结并回写资料库，保留有用的时间标记。

MCP 提供四个工具：

| 工具 | 用途 |
| --- | --- |
| `list_episodes` | 按标题查询节目，可筛选待总结项并分页读取 |
| `get_episode` | 获取元信息、QA 状态及当前文档哈希 |
| `read_document` | 分页读取转录、摘要或 QA，读取到 `next_offset` 为空 |
| `write_summary` | 发布 Agent 创作的摘要，同时校验转录与摘要的当前哈希 |

写入文档前应读取完整转录和 QA。如果转录或旧摘要在阅读后变化，写入会失败，应重新读取。替换已有非空摘要需要你明确要求重新生成；Agent 不应自行覆盖。

## 数据边界

Agent 读取的转录会进入其会话并受客户端账户的数据政策约束。stdio 在本机运行不等于 Agent 模型在本机推理。MCP 不提供 API Key、模型权重、音频下载、任意路径读取或删除工具。

可选云 API 总结是另一条流程，需要配置 API 地址、模型与安全存储的 Key；它不属于上面的 MCP 路径。

[隐私与数据](privacy.md)
