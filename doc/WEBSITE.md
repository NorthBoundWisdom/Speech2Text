# SonaFolio 官网维护

官网：<https://northboundwisdom.github.io/sonafolio/>。源码 `website/`，生成产物 `build/website/`，GitHub Pages 工作流 `.github/workflows/website-pages.yml`。

## 中英版本与内容边界

官网和用户手册提供完整中英版本，中文默认路径保持不变，英文在 /en/。主 README 默认中文，重点说明已经验证的中文播客流程。Material 提供中文界面、中文/英文搜索、深浅色、代码复制和移动导航。代码、配置键、界面按钮名保留实际英文名称；研究与工程原始资料可保留英文。

网页说明当前源码与发布版区别，不把新官网截图当成 v0.9.0 包含所有新功能的证据。网站部署不创建 App tag，也不会升级已下载的 App。

语言政策在 language-assets.json 按确切文件登记中文文档及 locale 资源，不把整个代码目录列为例外。

## 双语维护

使用 mkdocs-static-i18n 的 suffix 结构：index.md 是中文默认文档，index.en.md 是对应英文，所有手册页面保持一一对应。导航使用 locale 的 nav_translations，主题和构建标签按语言显示。

顶栏 partials/alternate.html 直接显示中文与 English，两种目标都始终可见；切换进入当前章节的对应页面，不统一退回首页，不需要 JavaScript。中文默认不根据浏览器语言自动跳转。

新增或修改页面时同步维护两种版本。configs/check_docs.py 检查缺失翻译，网站集成测试验证 46 个阅读页面的语言、页级切换、资源和双语搜索索引。插件关闭默认语言回退，避免英文入口静默显示未翻译内容。

技术依据：[i18n 配置](https://ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/)和 [Material 语言选择](https://squidfunk.github.io/mkdocs-material/setup/changing-the-language/)。

## 截图

原图唯一位置是 `doc/assets/`。`website/screenshots.json` 只登记公开审核的截图，`hooks/screenshots.py` 在构建时提供对应网站资源，避免重复维护二进制。

当前发布 screenshot-1（订阅）与 screenshot-3（来源详情），不发布包含本机私人路径的 screenshot-2。图片保留真实界面及来源内容，不用 AI 重绘，也不把示例条目数量当成容量或准确率指标。

新增截图先检查私人路径、Key 和私人材料，再登记映射及引用。不要让未审核图片自动进入公开构建。

## 本地构建

```bash
python3 -m venv build/website-env
build/website-env/bin/python -m pip install -r website/requirements.txt
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs serve -f website/mkdocs.yml
```

Windows 使用 build/website-env/Scripts/python.exe 和 PowerShell 环境变量。NO_MKDOCS_2_WARNING 只抑制 Material 的迁移公告，不掩盖普通严格构建警告。

## 校验

```bash
python3 configs/check_docs.py
python3 configs/check_repository_language.py
build/website-env/bin/python -m pytest website/tests
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs build --strict -f website/mkdocs.yml
python3 configs/check_docs.py --site build/website
python3 src/scripts/check_public_paths.py --scope worktree
```

首页显示 Git SHA、提交标题和 UTC 构建时间，提交文本进行 HTML 转义。可用带时区的 SONAFOLIO_SITE_BUILT_AT 固定测试时间。构建信息不能包含私人内容。

## 发布

main 推送触发 Pages：先检查链接、语言政策、截图/metadata、公共路径与严格构建，再上传静态产物，通过 github-pages 环境部署。PR 只验证，不部署。只有部署 job 使用 Pages/OIDC 写权限。

HTML 与 gh-pages 分支不是源码。保持 GitHub Pages 托管，跟随当前仓库的品牌和支持边界。浏览器预览不可用时，说明视觉验证限制，仍完成构建、资源与部署验证。
