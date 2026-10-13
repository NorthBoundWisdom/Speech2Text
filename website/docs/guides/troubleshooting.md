# 按症状排查

先定位失败层，不要每种错误都重新下载模型或重跑全部 ASR。记录平台、App/CLI 版本、实际命令、阶段和错误消息，必要时附脱敏日志。

## 推荐检查顺序

1. 确认客户端与 CLI 是预期版本。
2. 执行 `atot doctor`、`atot models`。
3. 确认 App、CLI、MCP 的数据根目录与资料库一致。
4. 用短中文文件与 `--local-only` 分离 ASR 和云总结问题。
5. 根据下面对应症状排查。

## Qt 能打开但不能转写

Qt 安装器含界面和 Qt 库，不含 Python CLI、FFmpeg、CUDA 或模型。按[安装说明](../install.md)准备运行时，在 Settings 选实际 `atot`，并检查同一个可执行文件的 doctor。终端里的另一个全局 atot 不能代替它。

## 模型缺失 {#model-files-are-missing}

看 `atot models` 的确切目录和文件名，按[模型清单](../models.md)手动补齐。MLX 与 faster-whisper 不能混用格式。模型只放数据根目录 model，不用 Downloads，不靠重命名文件“转换”格式。

## FFmpeg 或 ffprobe 找不到

分别检查两个工具的版本输出。App 启动环境可能不同于终端；Qt 配置 tool/vcpkg root，或从已配置的环境启动。只装 Qt SDK 不会安装媒体工具。

## Windows CUDA/cuDNN 缺失 {#windows-cuda-or-cudnn-is-missing}

按 CTranslate2 实际缺失 DLL 处理。安装 CUDA 13 不满足明确要求 CUDA 12 DLL 的 wheel；还需匹配 cuDNN 和 PATH。不要把缺库误认为音频损坏。

需要 CPU 时显式设置：

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

从同一环境运行命令或启动 App；独立桌面快捷方式不自动继承该会话变量。程序不会静默从 CUDA 降到 CPU。

## 导入或刷新失败 {#import-or-feed-refresh-fails}

区分小宇宙单集、节目/Apple Podcasts show 与 RSS 地址。前者用 exec import，后者用订阅。检查网络和来源是否还公开内容。完整历史只包含 feed 当前提供的条目；元数据成功不保证旧音频仍可下载。

## 转写重复、漏句或语言异常

中文先明确 `--language zh` 并确认默认模型。检查音频质量、QA 与时间窗口；先生成修复计划再决定重跑。其他语言或混合选项不代表已验证效果；多选不是语言白名单，也不是翻译开关。

## 资料库为空或两端不同 {#the-library-is-empty-or-different-on-another-device}

比较库的实际路径和 storage 模式，再检查分组/状态筛选、iCloud 文件是否下载、Files 权限。新建一个同名目录不是迁移资料库。参见[存储](storage.md)与[iOS](ios.md)。

## Codex 看不到工具或条目 {#codex-cannot-see-the-mcp-tools-or-episodes}

检查 `codex mcp get sonafolio` 和注册的可执行文件；修改后重开会话。确认服务进程看到正确数据根目录。检查条目是否有完整转写；仅有元数据不能总结。MCP 不需 SonaFolio 云 Key，不必靠填写云配置修复连接。

## 总结写入版本冲突

文档在阅读后改变。让 agent 重新 get_episode、读取变化文档，并使用新哈希。不要关闭版本检查，也不要使用其他单集的哈希。已有非空总结要明确请求重新生成才能覆盖。

## 云总结失败 {#cloud-summary-fails}

先核对 endpoint 的 Responses API 兼容性、实际模型名、访问权限、Key、超时与限额。403 是服务访问/鉴权问题，不能通过重跑 ASR 解决。分块失败或格式不符应明确失败，不能把残留流式文字当成完成总结。MCP 是独立替代工作流，不是静默降级。

## 字幕拒绝覆盖或导出失败 {#subtitle-export-fails-or-refuses-a-file}

目标存在时需明确 `--overwrite`。多个输入用 output-dir，而非一个共用 output 文件。检查返回的各条结果、媒体可解码性、ASR 环境和翻译是否启用。翻译失败应排查其后端，不把原语言字幕冒充翻译成功。

## 看不到新增列宽或语言设置

v0.9.0 早于这些功能。确认正在运行[当前源码构建](../install.md#release-and-current-source)，重新构建后退出旧 App 并重开；网站更新不会升级已安装二进制。

## 提交问题

到 [GitHub Issues](https://github.com/NorthBoundWisdom/sonafolio/issues) 提供可复现步骤、平台、版本、实际报错和脱敏日志。避免上传 Key、模型、私人媒体或完整资料库；只有公开来源必要片段才作为示例。

[常见问题 →](../faq.md) · [设置 →](settings.md)
