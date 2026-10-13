# SonaFolio 中文官网源码

[官网](https://northboundwisdom.github.io/sonafolio/)与[中文手册](https://northboundwisdom.github.io/sonafolio/handbook/)由 MkDocs Material 构建，通过 GitHub Pages 托管。完整中英内容围绕已经验证的中文播客流程，中文默认、英文位于 /en/；界面按钮与命令使用实际名称。

- `docs/`：中文默认页与同名 .en.md 英文版本，共 23 对。
- `mkdocs.yml`：双语构建、导航翻译、搜索和主题。
- `overrides/partials/alternate.html`：最上方直接可见的中英页级切换。
- `screenshots.json`：确切公开截图映射，原图来自 doc/assets。
- `locales/`：构建信息的中英标签。
- `hooks/`：构建来源信息及截图资产接入。
- `tests/`：metadata 与资产发布约束。

生成文件写入仓库外层的忽略目录 build/website，不进 Git。截图是真实当前源码界面，下载包以对应 release 为准。未审核的私人路径截图不进入网站。

[预览、验证、发布和维护](../doc/WEBSITE.md) · [中文文档地图](../doc/README.md)
