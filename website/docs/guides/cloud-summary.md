# 可选云 API 总结

此路径让 SonaFolio 把转写文本发送到你配置的模型服务，与本地 ASR、[Codex/MCP](agent-summary.md)分开。需要服务地址、模型、API Key，并确认允许把该集文本发送给该服务。

本地处理不要求云配置。MCP 使用 agent 的会话模型；云 API 操作则使用你的 endpoint，其访问限制、计费与数据策略属于该服务。

## 配置服务

原生 App **Settings → Cloud Model** 包含 API Base、API Key、Model、超时、温度、token 限制及 summary/title prompt。地址与模型名填写服务实际支持的值；下面是占位示例：

```bash
atot config set cloud.api_base '"https://api.example.com/v1"'
atot config set cloud.model '"your-supported-model"'
```

当前客户端使用配置地址下的 Responses API。仅支持其他协议形状的服务不一定可用；协议错误不应靠不停猜模型名解决。

Key 使用原生 App 的安全字段，或通过隐藏输入送入 CLI stdin，避免写进 shell 历史和参数：

```bash
python -c 'import getpass, subprocess; subprocess.run(["atot", "config", "set", "cloud.api_key", "--stdin"], input=getpass.getpass("API key: "), text=True, check=True)'
```

在托管环境执行；macOS 根据实际命令使用 `python3`。这是隐藏输入，不是普通可见的 stdin 粘贴。Qt 建议通过 CLI 管理系统凭据，保持其 Key 文本字段为空。不要把真 Key 放进 issue、截图或聊天。

## 先检查待发送内容

对本地转写返回的工作目录执行：

```bash
atot exec cloud prepare path/to/work-dir --json
```

这生成 `cloud/input/` 文本上下文包，不调用 API。发送前检查内容与隐私发现；自动脱敏不保证删除所有私人信息。

## 显式生成

```bash
atot exec cloud summarize path/to/work-dir --call-api --mode auto --json
```

`--call-api` 明确发起模型调用。不带它产生的本地 scaffold 不是模型/agent 总结，不能当成生成完成的笔记。

| 模式 | 行为 |
| --- | --- |
| `auto` | 在限制内直接用可读转写，否则采用分块 |
| `direct` / `--from-readable` | 直接总结可读转写，受大小保护 |
| `chunked` | 分块总结后汇总整集 |

流式直接总结：

```bash
atot exec cloud summarize path/to/work-dir --call-api --from-readable --stream-summary
```

流式文本是进行中的产物，最终任务成功前不能当成完成结果。必需块失败、无效/空响应或 API 错误会报告失败，不应视作成功替代。

## 语言与 prompt

当前源码的[总结语言](languages.md)统一影响直接/分块总结与短标题，并优先于自定义 prompt 中冲突的语言要求。其他结构与内容要求保留。

```bash
atot exec cloud summarize path/to/work-dir --call-api --prompt-file path/to/summary.prompt.md
```

要求基于来源、保留有用时间戳、说明不确定性，不把外部事实伪装成转写内容。短标题是独立模型步骤，成功生成标题不证明转写正确。

## 检查与重试

查看 Summary 和 `cloud/` 产物，确认发送内容、模式和各阶段结果。当前源码按输出语言检查分块缓存，不会把旧语言块静默用于新语言总结。

鉴权失败先查 endpoint、协议、模型访问、Key、超时与限额，不必因此重跑 ASR。已有总结需要替换时明确选择重新生成，并先保留要留下的个人笔记。

[云错误排查 →](troubleshooting.md#cloud-summary-fails) · [设置 →](settings.md) · [数据边界 →](privacy.md)
