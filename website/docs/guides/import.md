# 导入音频与播客来源

已有媒体文件用单文件入口，一集小宇宙内容用单集导入，整个节目用订阅入口。区分这些动作，可以清楚知道拿到了元数据、下载了音频，还是已经完成转写。

## 入口与来源

| 来源 | 入口 | 首先发生什么 |
| --- | --- | --- |
| 本地音频/视频 | New Item 或 `exec transcribe` | 建立来源并处理本地媒体 |
| 小宇宙单集链接 | App 导入或 `exec import` | 获取元数据，可选下载音频 |
| 小宇宙播客链接 | Add Subscription / `exec subscriptions add` | 解析 feed 并导入单集元数据 |
| Apple Podcasts 节目链接 | Add Subscription | 解析该节目的 feed |
| RSS feed | Add Subscription / `exec subscriptions add` | 读取 feed 和单集条目 |

CLI `exec import` 接收小宇宙 **episode** 链接。Apple Podcasts 节目与 RSS 用订阅流程。文件扩展名不能保证媒体可解码：需要音轨和正常的 FFmpeg。

## 本地文件

原生 App 选择 **New Item**，选择文件与分组，再启动本地处理。

```bash
atot exec transcribe path/to/recording.m4a --language zh --local-only --json
```

测试时需要固定工作目录：

```bash
atot exec transcribe path/to/recording.mp4 --job-dir path/to/work-dir \
  --language zh --local-only --json
```

不同来源使用不同工作目录。默认托管流程按 episode ID 关联媒体与工作数据，不必自己命名单集目录。

## 小宇宙单集

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --group-name Research --language zh --local-only --json
```

CLI 默认下载并转写；`--local-only` 跳过云总结。只导入元数据和音频、暂不运行 ASR：

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" --data-only --json
```

连音频也暂不下载：

```bash
atot exec import "https://www.xiaoyuzhoufm.com/episode/<episode-id>" \
  --data-only --no-download --json
```

元数据条目不具备音频时不能执行本地 ASR。`--group-name` 是逻辑分组；`--folder-name`、`--audio-name` 调整生成名称。`--force` 会重新下载/替换导入音频，用于明确的恢复操作。

## 订阅一个节目

通过订阅面板加入 RSS、小宇宙播客或 Apple Podcasts 节目链接。CLI RSS 示例：

```bash
atot exec subscriptions add "https://example.org/podcast/rss.xml" \
  --group-name Research --limit 10 --json
atot exec subscriptions list --json
```

替换为实际 feed。CLI 初始默认导入 10 条元数据。刷新是另一个动作；添加订阅不代表转写整个节目。参见[订阅与队列](library.md)。

## 检查导入结果

打开 **Overview**，确认标题、节目、原始 URL、时长和分组，再检查音频是否就绪。CLI 使用返回的实际路径和 `atot exec library status --json`，不要猜目录。

导入失败时先区分来源解析、下载与 ASR。节目服务可能删除内容或改变访问方式。保留原始链接与实际错误，避免遇到任何失败都强制重导入。

[转写与审阅 →](transcription.md) · [导入排查 →](troubleshooting.md#import-or-feed-refresh-fails)
