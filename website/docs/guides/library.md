# 资料库、订阅与队列

权威资料库保存单集元数据、阅读文档、分组和状态。订阅提供单集条目，处理才产生阅读文档；媒体与工作缓存留在执行转写的本机。

![订阅工作区：播客统计、待处理筛选、单集选择与添加订阅入口。](../assets/screenshot-1.png){ loading=lazy }

*真实 macOS 源码版本。截图中的数量是示例资料库状态，不是容量或准确率承诺。[查看原图](../assets/screenshot-1.png)。*

## 添加与刷新

原生 App 打开 **Subscriptions**，在 **Add Subscription** 粘贴 RSS、小宇宙播客或 Apple Podcasts 节目链接，选择分组。选中节目查看单集。刷新更新元数据，不自动下载或转写全部内容。

```bash
atot exec subscriptions add "https://example.org/podcast/rss.xml" \
  --group-name Research --limit 10 --json
atot exec subscriptions list --json
atot exec subscriptions refresh --all --json
```

CLI 初始/普通刷新默认限制 10 条。需要 feed 当前提供的完整历史时：

```bash
atot exec subscriptions refresh --id <subscription-id> --full-history --json
```

ID 来自 list。完整历史也只限来源 feed 暴露的条目，不能恢复已从 feed 移除的节目。刷新目前是手动操作，外部调度器可调用 CLI，但 App 不承诺后台自动轮询。

## 先筛选，再选批次

原生订阅详情显示总量、未处理和已处理数量。使用 **Unprocessed only** 与时间筛选，再使用 **Select all / Deselect all**、当前源码的 **First N** 或逐行选择。

1. 选择订阅与筛选范围。
2. 选择一个有限批次，核对选择结果。
3. 无云 Key 时选择本地处理。
4. 等待本批结果，阅读 QA，再选择下一批。

选中行不等于开始任务，某些选择可能不符合具体操作条件。Audio pending 仍需下载/恢复媒体，旧来源音频也可能已经不可访问。

## 整理与阅读

用分组区分项目或主题，用 **Starred** 标记重点，用阅读/归档状态管理稍后回看。Today、Unprocessed 和分组视图不是文档的独立复制。

改分组不触发 ASR；标记已读不表示核验过转写。Overview、Transcript、Summary 保持分离。没有总结时选择 [MCP](agent-summary.md) 或[云 API](cloud-summary.md)，不能靠切换阅读页生成总结。

## 删除与取消订阅

移除订阅停止管理 feed；删除单集移除记录及阅读文档，并写 tombstone，避免刷新静默重新导入。两者是不同操作，删除前保留需要的备份。

```bash
atot exec subscriptions remove <subscription-id> --json
atot exec library episode delete <episode-id> --json
```

不要随意删内部 JSON 来强制刷新。tombstone 是删除与同步状态的一部分，备份应包括完整资料库。

## 共享同一资料库

原生 App 的 **Settings → Library** 选择本地或 iCloud。默认 iCloud 路径保留兼容名称：

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
```

本地模式：

```text
~/Documents/SpeechToTextData/Audio2TextLibrary/
```

这两者是不同的权威位置。模型、媒体和 work 留在本地运行根目录。切换位置不证明两个目录有同样内容，迁移前先检查目标并备份。

iOS 通过 Files 选择已有 `Audio2Text` 或 `Audio2TextLibrary` 文件夹。它读取文档、刷新订阅元数据与管理状态，不做 ASR 或下载音频处理。见 [iOS 阅读端](ios.md)。

## 确认实际数据

```bash
atot exec library status --json
```

App 与 CLI 显示不同内容时，先比较存储模式和解析到的资料库根目录，再检查过滤器和 iCloud 文件下载状态。

[工作区 →](workspace.md) · [备份 →](storage.md) · [同步排查 →](troubleshooting.md#the-library-is-empty-or-different-on-another-device)
