# SonaFolio 中文官网源码

[官网](https://northboundwisdom.github.io/sonafolio/)与[中文手册](https://northboundwisdom.github.io/sonafolio/handbook/)由 MkDocs Material 构建，通过 GitHub Pages 托管。默认中文内容围绕已经验证的中文播客流程；界面按钮与命令使用实际名称。

- `docs/`：中文产品页与按任务组织的手册。
- `mkdocs.yml`：中文导航、搜索和主题。
- `screenshots.json`：确切公开截图映射，原图来自 doc/assets。
- `locales/zh.json`：构建信息的中文标签。
- `hooks/`：构建来源信息及截图资产接入。
- `tests/`：metadata 与资产发布约束。

生成文件写入仓库外层的忽略目录 build/website，不进 Git。截图是真实当前源码界面，下载包以对应 release 为准。未审核的私人路径截图不进入网站。

[预览、验证、发布和维护](../doc/WEBSITE.md) · [中文文档地图](../doc/README.md)
