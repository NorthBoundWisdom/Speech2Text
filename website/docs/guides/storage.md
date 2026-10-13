# 存储、备份与迁移

先分清权威资料库与本地运行数据。只备份一个 work 目录，不能替代完整资料库备份；只备份资料库，也不包括原音频和模型。

## 本地数据根目录

默认 `~/Documents/SpeechToTextData/`：

```text
SpeechToTextData/
  config.toml
  env/                 Python 运行环境
  model/               手动准备的模型
  materials/           媒体与私人导入信息
  work/                转写、QA、修复与总结证据
  cache/               日志、工具和临时数据
  Audio2TextLibrary/    本地模式的权威资料库
```

CLI 接受 `ATOT_DATA_ROOT`；Qt 的 data-root 也传入其工作流服务。修改环境变量必须在启动进程前完成，且不会自动移动已有文件。默认 setup 脚本准备默认托管环境，不应假定换一个变量就完成整个迁移。

## 权威资料库

```text
Audio2TextLibrary/
  manifest.json
  subscriptions/<subscription_id>.json
  groups/<group_id>.json
  episodes/<episode_id>/episode.json
  episodes/<episode_id>/documents/transcript.md
  episodes/<episode_id>/documents/summary.md
  tombstones/episodes/<episode_id>.json
```

记录包含文档大小和哈希，软件据此读取与回写。不要只修改文档而忽略记录的一致性；MCP 采用版本化工具处理发布。

iCloud 模式默认资料库位置是：

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
```

模型、媒体与工作数据仍在本机。兼容路径中的 Audio2Text 不需要为了品牌更名而手动改名。

## 备份什么

| 目的 | 要保留的内容 |
| --- | --- |
| 还原阅读、分组、订阅及删除状态 | 整个权威 Audio2TextLibrary，包含 tombstones |
| 保留原音频与处理证据 | materials 与 work |
| 保存设置 | config.toml；Key 另外由系统凭据管理 |
| 避免重新准备权重 | model |

运行环境通常可按依赖重新创建，不应把一个操作系统的 env 直接复制到另一个系统。iCloud 同步会传播变化和删除，不是独立备份。

## 迁移步骤

1. 停止本机处理与 agent 写入，避免复制时文档继续变化。
2. 确认当前权威库路径，制作独立完整备份。
3. 等待 iCloud 文件在本机可用，再复制整个库。
4. 配置目标客户端/CLI/MCP 使用同一新位置。
5. 检查单集数量、几份转写与总结、分组及状态。
6. 执行 `atot exec library status --json`；开发环境还可使用库验证器。
7. 在确认可读、可写和备份可恢复后再处理旧位置。

切换本地/iCloud 设置不保证两个位置自动合并，也不要用删除 tombstone 的方式绕过历史删除状态。

## 清理与恢复

确认用途后可清理临时缓存。删除 materials 会失去本地媒体，修复可能需要重新下载；删除 work 会失去 QA 等证据；删除 model 会阻止后续 ASR。删除权威库会删除阅读内容。

恢复时还原完整备份，在客户端指向恢复位置后检查文档。系统凭据在配置文件外，不能因为拷贝了 config.toml 就假定 Key 也存在。

[iOS 阅读 →](ios.md) · [隐私 →](privacy.md)
