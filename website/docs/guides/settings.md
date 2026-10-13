# 设置与配置

原生 macOS 使用 `Command-,` 打开 Settings，修改后 Save；Qt 在 Settings 里配置外部 CLI，部分选项即时保存。设置影响后续任务，不会自动重写已有转写或总结。

## 原生 App 的设置分区

| 分区 | 用途 | 常见选择 |
| --- | --- | --- |
| Overview | 模型、CLI、工具和可选云状态 | 先解决必需项，再 Recheck |
| Local ASR | 模型/profile，当前源码的语言选项 | 中文流程选 large-v3-turbo 与 Chinese / Mandarin |
| Cloud Model | 地址、Key、模型、超时和 prompt | 只有需要云 API 时配置 |
| Translation | SRT 翻译后端与中文目标 | 默认关闭，与总结语言独立 |
| Workflow | 默认云队列、本地偏好和分块 | 首次使用本地处理 |
| Library | 本地/iCloud 与资料库根目录 | App、CLI、MCP 指向同一库 |
| Reading | 字号、行距、字体和阅读宽度 | 不改变原始文档 |
| Runtime | 本地运行环境状态与操作 | 定位实际运行的 CLI |
| Config Sources | 有效值、来源层与可编辑键 | 解释“为什么用了这个值” |

Qt 的设置页不是原生分区的完全复制；按其实际字段配置模型、语言、外部工具、资料库和可选云服务。

## 共享 TOML 配置

默认配置位于数据根目录 `config.toml`。查询：

```bash
atot config path
atot config list --json
atot config inspect --json
atot config get local.asr_model --json
```

| 键 | 用途 |
| --- | --- |
| `local.asr_model` / `local.asr_profile` | ASR 模型与解码 profile |
| `local.languages` | 当前源码的转写语言数组，空数组自动识别 |
| `summary.language` | 当前源码的总结输出语言，默认 `zh` |
| `workflow.default_cloud_summary` | 是否默认排队可选云总结 |
| `workflow.local_only` | 本地处理偏好 |
| `workflow.chunking` / `chunk_length` / `overlap` | 分块策略与秒数 |
| `translation.enabled` / `backend` / `target_language` | 字幕翻译 |
| `library.storage` / `local_root` / `icloud_root` | 权威资料库位置 |
| `cloud.api_base` / `model` | 云服务与模型 |

中文示例：

```bash
atot config set local.asr_model large-v3-turbo
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config set workflow.default_cloud_summary false
```

命令行值按 TOML 解析，数组需保留引号。Key 用系统凭据存储和隐藏输入，见[云配置](cloud-summary.md)，不要写入公开示例。

## 单次覆盖与优先级

```bash
atot -c 'local.languages=["zh"]' exec transcribe path/to/audio.m4a --local-only
```

`-c` 提供本次进程覆盖，不替代持久化的 config set。命令自己的 `--language` 可以明确指定本次输入；不传时使用有效配置。旧 `local.language` 保留读取兼容，当前保存会迁移为数组。

ASR 语言、总结输出和字幕目标分别控制不同阶段；阅读样式只是显示设置。语言选项可用不代表各语言已经完成中文流程同等验证。

## 修改后如何确认

保存，查询相关键，启动一个新短任务，检查返回的工作目录与 `run.json`。App 与终端行为不一致时，核对可执行文件、数据根目录及存储模式，不要先反复改模型。

[语言说明 →](languages.md) · [按症状排查 →](troubleshooting.md)
