# 第一次转录

先按[安装指南](install.md)准备 CLI、FFmpeg 与模型。以下示例在已激活的 macOS 运行环境中使用 `atot`；Windows 可激活对应虚拟环境，或使用安装指南中的完整可执行文件路径。

## 1. 检查本地环境

```bash
atot doctor
atot models
```

先解决缺失模型、后端、音频工具或 CUDA 错误。无需为本地转录或浏览资料库填写模型 API Key。

## 2. 选择一种输入

本地音视频：

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only
```

小宇宙节目：

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --local-only
```

链接导入会从节目服务下载音频，因此需要网络；本地 ASR 本身不上传音频。把 `<episode-id>` 换成实际节目 ID。

在 macOS App 中，也可以通过导入按钮选择链接或本地文件，指定分组后再执行处理。默认处理和主要快捷键执行本地转录与 QA；云摘要需要单独启用。

## 3. 阅读并检查结果

程序输出工作目录位置。保留这一路径，用于后续 QA 与修复：

```bash
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
```

主要文件包括 `transcript.readable.md`、`transcript.timestamped.md`、字幕、`qa.json` 和 `corrections.json`。QA 指标用于定位问题，并不保证识别文本完全正确；重要内容请结合原音频检查。

资料库中发布的可读文档放在 `documents/transcript.md` 与 `documents/summary.md`。CLI 可查询当前资料库状态：

```bash
atot exec library status --json
```

## 4. 生成总结

默认 ASR 流程不自动生成 Agent 总结。连接 Codex 后，读完整转录与 QA，用当前 Agent 模型生成中文摘要，再通过版本检查回写。

[配置 Codex 总结与回写 →](guides/agent-summary.md)
