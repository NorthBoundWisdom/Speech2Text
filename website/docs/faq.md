# 常见问题

## 没有 API Key 可以用吗？

可以。本地转录、资料库浏览和 MCP 服务不需要模型 API Key。Codex 总结使用 Codex 自己的账户与模型；可选云 API 总结才需要在软件内配置地址与 Key。

## 为什么找不到安装包？

正式包出现在 [GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases)。若还未发布 tag，可以先从源码构建。CI 试跑成功不等于创建了正式版本。

## macOS 或 Windows 提示未知开发者？

当前 macOS 使用 ad-hoc 签名、未公证，Windows 安装器未签名。核对下载来源与 `SHA256SUMS`，再使用系统提供的允许打开流程。详细要求见[安装指南](install.md)。

## 安装 Qt 客户端后为什么不能转录？

Qt 包含界面和 Qt 运行时。CLI、FFmpeg、模型及后端依赖需另外配置。在 Settings 中指定 `atot`，运行 `atot doctor` 检查缺失项。

## 支持 Intel Mac、iPhone 本机转录或 Linux ASR 吗？

当前稳定 macOS ASR 以 Apple Silicon 为基础。iOS 是阅读与订阅管理客户端。Linux 有 Qt 客户端，但没有晋升为稳定支持的 ASR 后端。当前自动发布的 macOS 包仅为 arm64。

## Windows 缺少 CUDA 12 DLL，但已安装 CUDA 13？

CTranslate2 wheel 的实际 ABI 要求决定所需 DLL；版本名称更高不保证兼容。请按明确的缺失依赖提示准备兼容环境。CPU 转录只能显式启用：

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

## 为什么目录里还叫 Audio2Text？

这些名字是资料库、应用设置和内部模块的兼容标识，继续使用已有数据。产品显示名称和安装包已改为 SonaFolio；[兼容名称清单](naming.md)说明保留原因。

## 支持跨节目语义问答、说话人分离或定时抓取吗？

当前内置资料库主要提供标题查询、分组与阅读管理，没有完整的跨节目语义问答。稳定 ASR 后端不提供说话人分离；订阅采用手动刷新。需要调度时由外部工具调用 CLI。

## 哪里反馈问题？

在 [GitHub Issues](https://github.com/NorthBoundWisdom/sonafolio/issues) 提供平台、版本、复现步骤与脱敏日志。请不要提交模型、音频、私人资料库或密钥。
