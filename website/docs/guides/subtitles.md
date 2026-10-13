# 字幕导出与翻译

需要给播放器或剪辑工具提供字幕时，使用独立 SRT 导出。此流程不要求先把文件导入资料库，工作数据位于数据根目录 `cache/srt/`。

## 导出原语言字幕

```bash
atot exec srt path/to/video.mp4 --language zh --json
```

默认生成源文件旁的 `video.srt`。也可一次提供多个文件：

```bash
atot exec srt path/to/first.mp4 path/to/second.m4a --language zh --json
```

检查整个 results 数组：每个文件有独立状态与实际 SRT 路径，首个成功不代表整批都成功。

原生 App 使用 **Generate SRT…**（`Command-Shift-S`），选择文件并导出。面板显示日志、产物路径和成功后的 Reveal 操作。当前源码使用 Local ASR 中保存的转写语言选择。

## 语言与目标路径

```bash
atot exec srt path/to/video.mp4 --language zh --language en
atot exec srt path/to/video.mp4 --language auto
atot exec srt path/to/video.mp4 --output path/to/captions.srt
atot exec srt path/to/first.mp4 path/to/second.mp4 --output-dir path/to/subtitles
```

混合语言选项只是上下文提示，不启用翻译。单文件可以指定 `--output`；多个文件使用 `--output-dir`。默认不覆盖已存在目标，明确替换时：

```bash
atot exec srt path/to/video.mp4 --language zh --overwrite
```

## 可选翻译

默认不翻译。需要把原语言字幕翻译成中文时明确启用：

```bash
atot config set translation.enabled true
atot config set translation.backend cloud
atot config set translation.target_language zh
```

中文目标使用独立的 `video.zh.srt`。原生 **Settings → Translation** 提供对应操作。关闭翻译：

```bash
atot config set translation.enabled false
```

| 后端 | 前提 | 数据边界 |
| --- | --- | --- |
| `cloud` | 服务地址、模型、系统存储的 Key | 字幕文本发送到配置的 API |
| `local` | 本地翻译环境和模型文件 | 使用本地翻译后端 |

本地翻译是明确选择，不会静默替代失败的云调用。默认本地别名 `nllb-200-distilled-600m` 的文件与手动链接在[模型清单](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json)中。只有选择该流程才需要准备此模型。

必需翻译失败应报告失败，不能把未翻译字幕当作成功替代产物。

## 检查结果

在目标播放器或编辑器打开 SRT，检查开头、中间和结尾的文本与时间。结构合法、时间单调不等于识别准确或翻译准确。

正常资料库转写也在工作目录保留 SRT/VTT。需要明确源文件旁的目标及覆盖策略时，使用本页的独立导出入口。

[语言设置 →](languages.md) · [字幕排查 →](troubleshooting.md#subtitle-export-fails-or-refuses-a-file)
