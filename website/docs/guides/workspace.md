# 桌面工作区

桌面资料库分为三列：来源、单集和所选单集的详情。Swift 原生 App 与 Qt 客户端采用类似结构，具体控件随平台不同。界面按钮目前使用英文，下面保留实际名称，方便对照。

![真实 macOS 工作区：来源分类、单集列表和单集 Overview。](../assets/screenshot-3.png){ loading=lazy }

*截图来自当前源码版本，节目内容保留来源语言。[查看原图](../assets/screenshot-3.png)。*

## 三列分别做什么

| 列 | 用途 | 常见动作 |
| --- | --- | --- |
| Sources | 选择订阅、分组或状态筛选 | 打开 Unprocessed、Starred 或某个分组 |
| Episode List | 从当前来源选择单集 | 选中要阅读或处理的内容 |
| Detail | 查看来源和阅读文档 | 切换 Overview、Summary、Transcript |

**Overview** 是来源元数据；**Transcript** 是处理后的转写；**Summary** 显示已经存在的总结。切换 Summary 不会自动调用模型，导入后尚未处理的单集也可能没有 Transcript。

## 调宽与折叠

这是 v0.9.0 之后的当前源码功能：

1. 指针移到 Sources 与 Episode List 之间的竖向分隔线，水平拖动。
2. 同样拖动第二条分隔线，调整单集列表宽度。
3. 用标题栏左侧两个按钮分别隐藏或恢复相应列。
4. 可以同时隐藏两列，只留阅读空间；两个恢复按钮仍可使用。

软件记住展开宽度和显示状态，恢复列不会清除所选单集。各列有最小可用宽度，窄窗口不会允许无限缩小。macOS 的 **View → Show All Columns** 可恢复两列。

| 动作 | 原生 macOS | Qt |
| --- | --- | --- |
| 显示/隐藏 Sources | `Control-Command-S` | `Control-Shift-S` |
| 显示/隐藏 Episode List | `Control-Command-L` | `Control-Shift-L` |

如果下载的 App 仍是旧布局，先看[发布版与源码区别](../install.md#release-and-current-source)。

## 阅读与组织

选中单集，通过条目操作或右键菜单收藏、修改分组或标记阅读状态。已读、已处理、归档不是同一概念：阅读状态用于组织；处理状态反映是否执行过任务。

原始链接可回到节目上下文。缩短的列表标题不替代保留的来源信息。原生 App 的 **Settings → Reading** 可以调整字号、行距、字体和阅读宽度。

## 从工作区处理

先通过 **New Item** 导入，再对单集选择 **Transcribe locally only**。云总结是独立操作，需要配置和上传文本许可。处理卡片与日志报告阶段及失败原因。

订阅页面的行选择并不等于启动处理；刷新只更新元数据。媒体仍可能是 Audio pending。参见[订阅与队列](library.md)。

## 原生 macOS 常用入口

| 动作 | 入口 |
| --- | --- |
| Settings | `Command-,` |
| New Item | `Command-N` |
| New Group | `Command-Shift-N` |
| 本地转写 | `Command-Return` |
| 重新本地转写 | `Command-Shift-Return` |
| Generate SRT | `Command-Shift-S` |
| Refresh | `Command-R` |
| Refresh Library | `Command-Shift-I` |
| 复制 Codex 回写指令 | 条目菜单 **Copy Codex summary write-back instructions** |
| 查看日志 | **Reveal Logs** |

操作是否可用取决于当前选择、媒体和运行环境。处理按钮禁用时，先确认这些前提。

[导入来源 →](import.md) · [设置说明 →](settings.md)
