# 转写、总结与字幕语言

语言设置分为三件事。总结用中文，不代表把转写自动翻译成中文；字幕翻译也不是 ASR 语言提示。

| 设置 | 控制什么 | 是否翻译原文 |
| --- | --- | --- |
| Transcription Languages | ASR 单语言提示或混合语言上下文 | 不翻译，保留口语原文 |
| Summary Output Language | 总结正文、标题及 MCP 指令 | 用所选语言写总结，不替换转写 |
| 字幕目标语言 | 可选 SRT 翻译 | 翻译字幕产物 |

复选框和总结语言选择器是 **v0.9.0 之后的当前源码功能**，位于 Swift/Qt 的 **Settings → Local ASR**。旧配置中的明确语言值继续可读。

## 中文推荐操作

勾选 **Chinese / Mandarin**，总结输出保留中文 `zh`，先完成[首次中文转写](../quick-start.md)。这是本手册围绕的已验证流程。

当前新配置不勾选语言时默认自动识别。自动识别、多语言及其他语言的配置选项可以使用，但目前不声称具有与中文流程相同的逐语言验证覆盖。

## 复选框如何生效

| 选择 | 行为 |
| --- | --- |
| 都不勾选 | 自动识别，不传固定语言提示 |
| 只勾选一个 | 向 ASR 传该语言提示 |
| 勾选多个 | 自动识别，并提供所选语言的混合上下文 |

多选不是严格识别白名单，也不能保证每次语言切换都准确。现有 Whisper 接口接受一个语言提示或自动模式；混合模式保留各语言原文，不强制译为一种语言。

在原生 App 修改后保存；Qt 的语言选择即时写入配置。**Automatic Detection** 清空选项。改变设置只影响后续任务，不自动覆盖已有文档。

支持选择的代码：`zh`、`en`、`ja`、`ko`、`yue`、`de`、`fr`、`es`、`ru`、`pt`、`it`、`ar`、`hi`、`vi`、`th`、`id`。能选择不等于识别效果保证。

## 总结输出语言

**Summary Output Language** 默认中文，影响正文、生成的 Markdown 标题、短标题、MCP `get_episode` 返回的指引和复制给 Codex 的回写请求。

该设置优先于自定义 summary/title prompt 里冲突的语言要求；其他内容和结构要求保留。例如选英文时，旧 prompt 要求中文不再决定输出语言，但“解释生僻术语”的要求仍保留。

设置无需 API Key，也不自动生成或翻译已有总结。对 agent 会话发出的明确语言要求可以覆盖其配置默认值。

## CLI 设置与单次覆盖

```bash
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config get local.languages --json
atot config get summary.language --json
```

单次覆盖示例：

```bash
atot exec transcribe path/to/audio.m4a --language zh --local-only
atot exec transcribe path/to/audio.m4a --language zh --language en --local-only
atot exec transcribe path/to/audio.m4a --language auto --local-only
```

`exec import`、`exec srt` 同样接受语言选项。配置中 `local.languages = []` 表示自动识别；不传 `--language` 使用已保存的选择。

兼容旧 `local.language`。当前界面保存时迁移为数组；手动编辑同时留下两个键时，数组优先。`auto/detect` 清除提示，`jp` 等别名规范化为 `ja`。已有明确语言配置保留，新隐式配置采用自动识别。

## 字幕翻译单独配置

**Settings → Translation** 配置 SRT 翻译。当前原生界面以简体中文目标为入口；CLI 的 target 配置与后端支持需单独确认。云翻译需要服务配置，本地翻译需要独立模型，不能把总结语言当成字幕翻译开关。

[字幕说明 →](subtitles.md) · [MCP 回写 →](agent-summary.md)
