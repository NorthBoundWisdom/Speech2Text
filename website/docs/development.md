# 开发与贡献

源代码采用 MIT 许可，第三方组件遵循自己的许可和分发要求。

- [源码与快速开始](https://github.com/NorthBoundWisdom/sonafolio)
- [架构](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/ARCHITECTURE.md)
- [开发与验证](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/TECHNICAL_GUIDE.md)
- [Agent 开发约定](https://github.com/NorthBoundWisdom/sonafolio/blob/main/AGENTS.md)
- [多平台构建与 tag 发布](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/CI_RELEASES.md)
- [发布许可与源码材料](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/RELEASE_LICENSES.md)
- [同类产品对比](https://github.com/NorthBoundWisdom/sonafolio/blob/main/README.md)

本官网参考兄弟项目 [Ravo 用户手册](https://northboundwisdom.github.io/Ravo/) 的组织方式，使用 MkDocs Material，提供搜索、明暗模式、移动端导航和网站构建信息。页面描述当前源码行为，下载版本的能力以对应 release 说明为准。

官网源码位于 `website/`。修改后进行严格构建，再由 GitHub Actions 上传 Pages 产物与部署。生成网页留在 `build/website/`，不提交到 Git。
