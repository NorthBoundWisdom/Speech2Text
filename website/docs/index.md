---
title: SonaFolio · 让好内容留下来
description: 本地优先的播客转录与知识资料库。把声音变成可读稿、摘要和可携带的 Markdown。
hide:
  - navigation
  - toc
---

<div class="sf-home" markdown>

<div class="sf-hero" markdown>
<div class="sf-hero-copy" markdown>

<p class="sf-eyebrow">声音里的好想法，值得留存</p>

# 把听过的内容，<br>留成自己的资料库。

<p class="sf-lead">SonaFolio 将播客与音视频整理为可读的转录、字幕和摘要。<br>在电脑上转录，在资料库里积累，在 iPhone 和 iPad 上继续阅读。</p>

<div class="sf-actions" markdown>
[开始使用](install.md){ .md-button .md-button--primary }
[查看源代码](https://github.com/NorthBoundWisdom/sonafolio){ .md-button }
</div>

<p class="sf-fine">开源 · 本地优先 · macOS / Windows · iOS 阅读 · Qt Linux 客户端</p>
</div>

<div class="sf-preview" role="img" aria-label="产品布局示意：节目列表、带时间戳的转录和摘要。不是实际节目内容。">
<div class="sf-preview-bar"><span class="sf-dots">● ● ●</span><span>SonaFolio</span><span class="sf-preview-label">布局示意</span></div>
<div class="sf-preview-body">
<div class="sf-preview-library"><span class="sf-caption">我的资料库</span><strong>让灵感有处可寻</strong><span class="sf-selected">声音如何变成知识</span><span>一次值得记住的对话</span><span>把好想法留下来</span><span class="sf-library-bottom">3 篇示例 · Markdown</span></div>
<div class="sf-preview-document"><div class="sf-preview-tabs"><span>简介</span><b>摘要</b><span>转录</span></div><span class="sf-caption">播客笔记 / 示例内容</span><strong>声音如何变成知识</strong><p>听见一个好想法只是开始。<br>留下原文，再整理自己的理解。</p><div class="sf-quote"><span>00:12:08</span><p>让每一次回顾，都能找到原来的上下文。</p></div><span class="sf-caption">要点</span><p class="sf-preview-bullets">保留时间戳，方便回看<br>以文本保存，方便复用<br>由你决定如何总结</p></div>
</div>
</div>
</div>

<div class="sf-principles" markdown>
<div markdown>

### 在本机转录

Apple Silicon 使用 MLX Whisper，Windows 使用 faster-whisper。音频由本地 ASR 处理，模型文件由你管理。
</div>
<div markdown>

### 在资料库积累

节目、可读稿、摘要、收藏和分组集中保存。可选 iCloud Drive 同步，让 Mac 与 iOS 阅读同一份资料库。
</div>
<div markdown>

### 把总结交给 Agent

通过 MCP 让 Codex 读完转录与 QA，再用当前模型总结并回写。SonaFolio 无需为这条路径配置模型 API Key。
</div>
</div>

<div class="sf-section" markdown>
<p class="sf-eyebrow">从一段声音，到一份可回看的笔记</p>

## 听过之后，还有下一步。

<div class="sf-steps" markdown>
<div markdown>

### 01 / 导入

选择本地音视频，或导入小宇宙节目。通过 RSS 订阅与手动刷新，把节目整理进资料库。
</div>
<div markdown>

### 02 / 转录与审校

生成可读稿、字幕和 QA 报告。查看时间戳、修正规则与问题窗口，需要时执行定向修复。
</div>
<div markdown>

### 03 / 总结与收藏

由 Agent 生成摘要，通过版本检查回写。保留完整原文，再用收藏、分组与阅读状态组织内容。
</div>
</div>

[完成第一次转录 →](quick-start.md)
</div>

<div class="sf-section sf-platforms" markdown>
<p class="sf-eyebrow">选择适合你的入口</p>

## 一份资料库，几种使用方式。

| 平台 | 当前可用能力 |
| --- | --- |
| **macOS / Apple Silicon** | SwiftUI 原生 App、Qt 客户端与 `atot` CLI；稳定的 MLX Whisper 本地转录 |
| **Windows / x64** | Qt 客户端与 `atot` CLI；faster-whisper 转录需要另行配置运行环境 |
| **iPhone / iPad** | 从源码构建的阅读客户端；资料库、订阅、摘要与转录阅读，不在设备上执行 ASR |
| **Linux / x86_64** | Qt AppImage 客户端；尚未提供稳定的 Linux ASR 后端 |

<p class="sf-fine">Qt 安装包包含客户端与 Qt 运行时；CLI、FFmpeg 和模型需另行配置。macOS 当前使用 ad-hoc 签名，未公证。发布版本以 GitHub Releases 为准，详细要求见安装指南。</p>

[下载与安装](install.md){ .md-button }
</div>

<div class="sf-closing" markdown>
<div markdown>

## 内容由你掌握。

资料库使用 JSON 与 Markdown 保存，字幕可导出为 SRT/VTT。本地转录不上传音频；可选 iCloud、Agent 总结和云 API 各有自己的数据边界。

[了解隐私与数据 →](guides/privacy.md)
</div>
<div class="sf-closing-links" markdown>

[用户手册](quick-start.md)

[CLI 与自动化](guides/cli.md)

[常见问题](faq.md)

[参与开发](development.md)
</div>
</div>

<!-- SONAFOLIO_BUILD -->
</div>
