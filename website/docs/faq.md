# 常见问题

## 不配 API Key 能用吗？

可以。本地转写、资料库阅读、MCP 回写都不需要 SonaFolio 模型 Key。Codex 使用自己的账户与会话模型；只有可选云 API 流程需要对应 endpoint、model 与 Key。

## 为什么默认官网和手册是中文？

中文播客是已经验证过的主要流程，尤其是 Apple Silicon + MLX Whisper + large-v3-turbo。文档优先讲清这条路径。可设置其他语言，不代表已有同等逐语言验证；软件按钮和配置键保留实际英文名称。

## 安装器包含全部环境吗？

不包含。Qt 包提供客户端与 Qt 库，Python CLI、FFmpeg、CUDA、模型另外准备。Swift 包包含 CLI wheel，仍需 Python、媒体工具与模型。见[安装](install.md)。

## 安装包和截图为何不一样？

v0.9.0 早于最新列宽/折叠、紧凑工具栏和语言设置。截图展示当前源码构建，使用这些功能需要重新构建并重启 App。官网发布不会更新已有安装包。

## 为什么操作系统提示未知开发者？

macOS 采用 ad-hoc 签名，尚未 Developer ID 签名/公证；Windows 安装器未签名。核对来源与 SHA256SUMS 后再决定使用系统正常放行流程。

## Intel Mac、iPhone ASR、Linux ASR 呢？

稳定 macOS ASR 与自动包面向 Apple Silicon。iOS 是阅读/订阅端；Linux 有 Qt 客户端但无稳定晋升 ASR 后端。平台可用不等于转写后端已验证。

## 能只勾选中文吗？

当前源码可以在 Local ASR 勾选 Chinese / Mandarin，也可传 `--language zh`。不选为自动，多选为自动识别加上下文，不是严格语言白名单。

## 改总结语言会重新生成旧总结吗？

不会。设置影响后续任务，默认中文。替换已有总结要明确请求重新生成；MCP 同时校验文档版本。

## 为什么 CUDA 13 仍报 CUDA 12 缺失？

实际 CTranslate2 wheel 决定 DLL 要求，不能仅看 CUDA 安装版本。按错误准备兼容 runtime，或[显式选择 CPU](install.md#windows-x64)，没有静默降级。

## 订阅刷新会自动转写全部节目吗？

不会。刷新更新 feed 元数据；下载与处理是后续动作。CLI 普通刷新有默认数量限制，全历史需 --full-history，且只限 feed 提供的内容。

## 有没有语义问答、说话人分离与定时刷新？

目前资料库提供标题查询、分组与状态管理，没有内置跨单集语义问答。稳定 ASR 不提供 diarization。RSS 手动刷新，自动调度交给外部工具。

## QA 通过代表完全准确吗？

不代表。它是程序检查结果，关键人名、数字、观点与引用仍需核对音频。先看修复计划再重跑疑似窗口。

## 目录里为什么还有 Audio2Text？

库目录、凭据身份与内部模块保留兼容名称，产品显示名是 SonaFolio。不要为品牌变更直接重命名现有数据。见[命名说明](naming.md)。

## 如何备份和反馈？

按[存储说明](guides/storage.md)备份完整权威库，原媒体/work 另行保留；iCloud 不是独立备份。问题反馈包含平台、版本、复现和脱敏日志，不上传 Key 或私人资料库。更多见[故障排查](guides/troubleshooting.md)。
