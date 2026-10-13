# 中文本地转写

本地任务依次准备音频、分块、运行 ASR、合并结果、应用可追踪纠正，并生成阅读文档和 QA。`--local-only` 不需要模型 API Key，也不把音频上传给总结服务。

已验证主路径使用 Apple Silicon、MLX Whisper 与 `large-v3-turbo` 处理中文播客。本页例子明确指定 `zh`，便于复现这一流程；其他语言设置不代表具有同等验证证据。

## 开始前

1. 确认音频存在；订阅元数据可能仍显示 Audio pending。
2. 执行 `atot doctor`，确认后端、模型和媒体工具。
3. 选择模型、profile 和[中文语言提示](languages.md)。
4. 首次运行选择短音频与本地处理。

## App 操作

导入后选中条目，选择 **Transcribe locally only**；原生 macOS 主快捷键是 `Command-Return`。已经处理的内容可以明确选择重新处理（`Command-Shift-Return`）。

观察阶段与日志。下载完成、一个 ASR chunk 完成，与整个任务成功是不同状态。实际任务结束后再判断是否产生新文档。

## CLI 操作

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
```

可以用 `--language auto` 覆盖已保存的语言提示。当前源码也支持重复语言参数；不传参数使用已保存选择。转写保留原始口语语言，不通过总结语言或字幕目标设置翻译原文。

## 工作目录里有什么

| 文件 | 用途 |
| --- | --- |
| `transcript.corrected.txt` | 忠实的纠正后文本 |
| `transcript.readable.md` | 确定性阅读排版 |
| `transcript.timestamped.md` | 按时间找片段 |
| `transcript.srt` / `transcript.vtt` | 定时字幕 |
| `qa.json` | 自动检查结果 |
| `corrections.json` | 确定性修改记录 |
| `review.json` / `entity_consistency.json` | 术语与实体审阅 |
| `run.json` | 来源、模型/后端、语言请求、缓存身份和运行证据 |

资料库接收 `documents/transcript.md`。详细处理证据留在工作目录；QA/repair 应使用命令报告的实际目录。

## 长音频与分块

默认 `auto` 对较短音频使用固定窗口，对较长音频使用静音感知边界。先保留默认值；确有问题或需要可复现实验时再调整。时长选项单位是秒：

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only \
  --chunking smart --chunk-length 900 --max-chunk-length 1200 --overlap 10
```

| 参数 | 意义 |
| --- | --- |
| `--chunking auto/fixed/smart` | 边界策略 |
| `--chunk-length` | 目标块时长 |
| `--max-chunk-length` | smart 最大块时长 |
| `--silence-threshold` | 静音阈值 |
| `--min-silence` | 最小静音长度 |
| `--overlap` | 块之间的上下文重叠 |

重叠用于提供识别上下文，合并步骤决定保留哪些片段。不要直接拼接有重叠的 chunk 文本。

## 缓存与重新处理

来源、模型、解码参数、语言提示和实际 prompt 等参与缓存判断。设置改变不自动改写已经发布的文档。明确重建：

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --force
```

当前参数是 `--force`，不是旧文档中的 `--force-transcribe`。重新处理可能替换工作数据和资料库转写，需要保留旧结果时先备份。旧总结也可能不再对应新转写，应核对后明确请求重新生成。

## 上下文与纠正

`--prompt-file` 和 `--glossary-file` 指定自定义上下文；可重复 `--rule-pack` 选择共享规则。纠正应窄而可审计，不把一次噪声结果变成全局替换。

当前源码不会向自动、混合或非中文任务默认注入中文专用 ASR prompt；显式自定义上下文仍保留。QA 与审阅帮助定位不确定片段，但重要名字、数字、引用仍需复听。

[QA 与修复 →](quality.md) · [字幕导出 →](subtitles.md)
