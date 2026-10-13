---
title: SonaFolio · 把听到的内容留下来
description: 面向中文播客的本地转写与知识资料库。保存原始来源，生成可读转写、字幕和总结，并通过 Codex 与 MCP 将笔记回写到资料库。
hide:
  - navigation
  - toc
---

<div class="sf-home" markdown>
<div class="sf-hero" markdown>
<div class="sf-hero-copy" markdown>

<p class="sf-eyebrow">让听过的内容，成为可以回看的资料</p>

# 听过一次。<br>值得再读。

<p class="sf-lead">把中文播客、音频与视频整理成自己的资料库：保留原始来源，在电脑上完成转写，再用 Codex 或自选模型整理观点、证据与笔记。</p>

<div class="sf-actions" markdown>
[下载 SonaFolio](install.md){ .md-button .md-button--primary }
[打开中文使用手册](handbook.md){ .md-button }
</div>

<p class="sf-fine">开源 · 本地转写 · Markdown 文档<br>已验证的主路径：Apple Silicon Mac 上的中文播客转写</p>
</div>

<figure class="sf-product-shot" markdown>
[![SonaFolio macOS 订阅界面：左侧分类、中间播客列表、右侧待处理单集与订阅操作。](assets/screenshot-1.png)](assets/screenshot-1.png)
<figcaption>真实 macOS 界面：整理订阅、选择单集、查看处理进度。点击图片查看原尺寸。</figcaption>
</figure>
</div>

<div class="sf-principles" markdown>
<div markdown>

### 把声音变成可以核对的文字

本地 ASR 生成可读 Markdown、带时间戳的转写与字幕。QA 标出值得复听的位置，纠正记录保留程序修改过的内容。重要结论仍可回到原音频核对。

[了解转写与核对 →](guides/transcription.md)
</div>
<div markdown>

### 给播客收藏一个明确的归处

导入文件与单集，订阅 RSS，按分组、收藏和阅读状态整理。来源链接、音频、转写与总结保持关联，方便之后继续阅读与引用。

[管理资料库与订阅 →](guides/library.md)
</div>
<div markdown>

### 让 Codex 帮你写回总结

通过 MCP 让 Codex 读取完整转写与 QA，用当前会话模型整理笔记，再按文档版本回写。此路径不需要 SonaFolio 的模型 API Key。

[配置 Codex 总结回写 →](guides/agent-summary.md)
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">围绕一集内容展开的工作区</p>

## 找到来源，再进入阅读。

<figure class="sf-wide-shot" markdown>
[![SonaFolio 资料库界面：分组、单集列表与包含节目、日期、时长和原始链接的 Overview 详情。](assets/screenshot-3.png)](assets/screenshot-3.png)
<figcaption>Overview 保留单集来源；Summary 与 Transcript 分别用于阅读已有总结与转写。截图来自当前源码版本，<a href="install/#release-and-current-source">已发布安装包的界面可能较早</a>。</figcaption>
</figure>

<div class="sf-feature-pair" markdown>
<div markdown>

### 按阅读需要调整空间

左侧选择来源，中间选择单集，右侧阅读内容。当前源码版本允许拖动分隔线调整前两列宽度，也可以分别折叠两列，把空间留给正文；工具栏与 View 菜单可恢复显示。

[查看工作区操作 →](guides/workspace.md)
</div>
<div markdown>

### 中文流程优先，语言选项独立

手册以已验证的中文播客流程为主。当前源码版本还提供转写语言复选框，以及独立的总结输出语言设置。多语言配置属于可用选项，不代表各语言已经通过与中文相同的效果验证。

[区分三种语言设置 →](guides/languages.md)
</div>
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">从单集到自己的笔记</p>

## 三步完成，原始材料始终保留。

<div class="sf-steps" markdown>
<div markdown>

### 01 / 导入与选择

导入本地音视频或小宇宙单集；通过 RSS、小宇宙播客链接或 Apple Podcasts 节目链接管理订阅。刷新先获取元数据，再决定下载与处理哪些单集。

[导入来源 →](guides/import.md)
</div>
<div markdown>

### 02 / 本地转写与核对

准备好模型和媒体工具，选择中文语言提示，运行本地转写并查看 QA。复核人名、术语和数字；需要时先生成修复计划，再重跑有问题的音频窗口。

[准备模型 →](models.md) · [查看 QA 与修复 →](guides/quality.md)
</div>
<div markdown>

### 03 / 总结与继续阅读

让 Codex 完整阅读转写、保留有用时间戳，并将总结写回同一资料库。桌面端阅读；可选通过 iCloud Drive 把 JSON/Markdown 资料库交给 iPhone、iPad 阅读端。

[MCP 总结回写 →](guides/agent-summary.md) · [iOS 阅读 →](guides/ios.md)
</div>
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">产物清晰，文件可带走</p>

## 留下的不只是一个模型回答。

| 你的需要 | SonaFolio 的产物 | 操作说明 |
| --- | --- | --- |
| 回看一段访谈 | 可读 Markdown 与带时间戳的转写 | [本地转写](guides/transcription.md) |
| 给播放器或剪辑工具提供字幕 | SRT 导出；转写工作目录也保留 VTT | [字幕与翻译](guides/subtitles.md) |
| 整理观点与证据 | Codex/agent 总结或显式调用的云 API 总结 | [选择总结路径](handbook.md#choose-a-summary-path) |
| 找到值得复听的位置 | QA、纠正记录、术语审阅与修复计划 | [质量检查](guides/quality.md) |
| 备份自己的资料 | JSON 单集记录与 Markdown 阅读文档 | [存储与备份](guides/storage.md) |

完整转写与总结分开保存。当前资料库提供分类、收藏与阅读管理；没有内置跨单集语义问答，也没有生产路径的说话人分离承诺。
</div>

<div class="sf-section sf-platforms" markdown>
<p class="sf-eyebrow">先选适合自己的运行路径</p>

## 一份资料库，几个入口。

| 平台 | 当前能力与边界 | 开始使用 |
| --- | --- | --- |
| **macOS / Apple Silicon** | 原生 SwiftUI App、Qt 客户端和 CLI；中文播客的稳定主路径使用 MLX Whisper | [macOS 安装](install.md#macos-apple-silicon) |
| **Windows / x64** | Qt 客户端与 CLI；faster-whisper 需要单独准备运行时，使用 CUDA 或显式选择 CPU | [Windows 安装](install.md#windows-x64) |
| **iPhone / iPad** | 源码构建的资料库阅读与订阅管理端；不运行本机 ASR | [iOS 阅读说明](guides/ios.md) |
| **Linux / x86_64** | Qt AppImage 客户端；尚无晋升为稳定支持的 Linux ASR 后端 | [Linux 客户端](install.md#linux-x86_64) |

<p class="sf-fine">安装包包含客户端，模型权重需手动准备。Qt 客户端处理音频还需单独配置 CLI 和 FFmpeg。签名、运行时与版本能力以对应发布说明为准。</p>

[下载并检查运行环境](install.md){ .md-button }
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">从你现在要做的事情开始</p>

## 中文手册覆盖整条工作流。

<div class="sf-guide-grid" markdown>
<div markdown>

### 第一次转写

先准备客户端、媒体工具与模型，再用一段短音频验证中文流程，确认可以阅读转写与 QA 后再处理长节目。

[首次转写步骤 →](quick-start.md)
</div>
<div markdown>

### 处理订阅积压

分清刷新、下载与处理；筛选待处理单集，明确选择批次，再整理处理结果和阅读状态。

[订阅与队列 →](guides/library.md)
</div>
<div markdown>

### 请 Codex 写笔记

连接 MCP，完整读取原文，使用当前版本信息安全回写。已有总结只有在明确要求重新生成时才替换。

[连接与回写 →](guides/agent-summary.md)
</div>
<div markdown>

### 环境或任务出错

按客户端、CLI、媒体工具、模型、GPU 运行时与可选云配置分层排查，避免把总结失败误认为转写失败。

[按症状排查 →](guides/troubleshooting.md)
</div>
</div>
</div>

<div class="sf-closing" markdown>
<div markdown>

## 清楚地知道，数据去了哪里。

本地 ASR 不上传音频。来源导入会连接节目服务。可选的 iCloud 同步、agent 总结与云 API 各有独立的数据边界，由你选择启用哪条路径。

[隐私与数据流 →](guides/privacy.md)
</div>
<div class="sf-closing-links" markdown>

[中文使用手册](handbook.md)

[CLI 与自动化](guides/cli.md)

[GitHub 源码](https://github.com/NorthBoundWisdom/sonafolio)

[反馈问题](https://github.com/NorthBoundWisdom/sonafolio/issues)
</div>
</div>

<!-- SONAFOLIO_BUILD -->
</div>
