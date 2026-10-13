# CLI 与自动化

产品名是 SonaFolio，命令保留 `atot`。无参数打开 TUI，脚本流程使用 `atot exec ...`。以下路径和 ID 都需替换为实际值。

## 检查与帮助

```bash
atot --help
atot exec --help
atot doctor
atot models
atot config path
atot config inspect --json
```

每个命令以自身 `--help` 为准。旧顶层 `atot transcribe`、`atot import-xiaoyuzhou` 已移除，使用 exec 子命令。

## 中文转写与导入

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --language zh --local-only --json
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only --json
atot exec transcribe path/to/episode.m4a --language zh --local-only --force
```

`--force` 重建已有转写；数据保留与覆盖说明见[转写章节](transcription.md)。当前源码新增多次 --language，但本手册围绕已验证中文路径。

## 字幕、QA 与修复

```bash
atot exec srt path/to/video.mp4 --language zh --json
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
```

先看修复计划，再明确执行不带 plan-only 的修复。字幕目标存在时需 --overwrite。

## 订阅与状态

```bash
atot exec subscriptions add "https://example.org/feed.xml" --group-name Research --json
atot exec subscriptions list --json
atot exec subscriptions refresh --all --json
atot exec library status --json
atot status --task-id <task-id> --json
atot resume <task-id> --json
```

当前 `resume` 查询持久化任务/会话状态，不自动重新执行失败 ASR。需要重跑时重新发起对应任务，并按缓存或 --force 策略处理。

## 保存设置与单次覆盖

```bash
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config set workflow.default_cloud_summary false
atot -c 'local.languages=["zh"]' exec transcribe path/to/audio.m4a --local-only
```

当前语言数组为空表示自动；旧 local.language 兼容读取。命令语言覆盖只针对本次，config set 才持久化。详情见[设置](settings.md)。

## JSON、事件与脚本

有 --json 的命令提供结构化结果，--watch 提供任务事件。脚本应检查退出码和最终 success/错误，不把一条进度事件当成完成。批次检查每个结果。

```bash
atot exec transcribe path/to/episode.m4a --language zh --local-only --json --watch
```

事件流与最终结果混合时按行/协议识别，不把整个 stdout 当成单个 JSON 对象。调度由外部工具承担，feed 刷新不自动运行整个音频队列。

## 接口边界

`atot mcp` 是受限资料库读写工具；`atot serve --stdio` 是 GUI 内部 JSON 协议，不是 MCP。可选 HTTP 接口需要 loopback 和独立 token，操作范围更大；普通 agent 总结使用 MCP 即可，不必开启 HTTP。

[完整入口：README](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.md) · [MCP](agent-summary.md)
