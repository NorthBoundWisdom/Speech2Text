# 资料库与订阅

SonaFolio 使用一份权威资料库保存节目、订阅、分组、阅读状态与文档。音频素材和处理缓存留在本机，不是 iCloud 资料库的一部分。

## 导入与订阅

导入按钮接受本地音视频或小宇宙节目链接。导入时选择分组；添加节目后再执行本地处理。

订阅可从 CLI 管理：

```bash
atot exec subscriptions add "https://www.xiaoyuzhoufm.com/podcast/<podcast-id>" --group-name Default
atot exec subscriptions list
atot exec subscriptions refresh --all
```

RSS 和小宇宙订阅使用手动刷新。当前不承诺内置定时抓取；如需调度，可让系统或外部工具调用 CLI。

## 阅读和整理

客户端可浏览简介、转录和已有摘要，并管理分组、收藏、阅读及归档状态。查询资料库状态：

```bash
atot exec library status --json
```

删除节目会删除资料库记录和文档，并写入删除标记；后续订阅刷新不会自动把它重新导入。执行删除前确认不再需要这些文档。

## Mac 与 iOS 共享资料库

启用 iCloud Drive 时，默认资料库目录为：

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
```

关闭 iCloud 时，本机资料库默认位于：

```text
~/Documents/SpeechToTextData/Audio2TextLibrary/
```

在 iOS/iPadOS 的 Settings 中，通过 Files 选择已有 `Audio2Text` 或 `Audio2TextLibrary` 文件夹。目录名作为兼容标识保留，软件名称已经是 SonaFolio。

iOS 客户端可以阅读文档、更新订阅元信息、管理节目状态；不在设备上下载处理音频或运行 ASR。iCloud 的同步状态受系统、网络与文件可用性影响。

[了解存储与隐私](privacy.md) · [名称兼容说明](../naming.md)
