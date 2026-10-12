# CLI 与自动化

产品名称是 SonaFolio，命令行入口保留 `atot`。没有参数时进入 TUI；脚本使用 `atot exec ...`。

```bash
atot --help
atot exec --help
atot doctor
atot models
atot exec transcribe path/to/audio.m4a --language zh --local-only
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --local-only
atot exec srt path/to/video.mp4 --language zh
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
atot exec library status --json
atot status --task-id <task-id>
atot mcp
```

`--json` 适用于提供此选项的命令，具体参数以对应命令的 `--help` 为准。顶层旧式 `atot transcribe`、`atot import-xiaoyuzhou` 已在 CLI v2 中移除；不要使用过时示例。

## 配置

配置默认在数据根目录的 `config.toml`。查询公开配置：

```bash
atot config list
atot config get local.asr_model
```

本地默认模型是 `large-v3-turbo`。不要通过配置更改为尚未通过质量门禁的实验后端。

## 后台与 Agent

外部调度器可以执行 `exec` 命令。MCP 面向 Agent 的资料库读取与摘要回写；`atot serve --stdio` 是 GUI 使用的内部 JSON 服务，两者协议不同。

内部 HTTP 服务只接受 loopback，要求独立 token，并提供比 MCP 更广的工作流能力。一般 Agent 总结任务应使用 MCP，无需开启 HTTP 服务。

更完整的参数和输出示例见[仓库 CLI 参考](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.md)。
