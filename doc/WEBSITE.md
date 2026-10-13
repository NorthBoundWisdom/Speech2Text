# SonaFolio 官网维护

官网：<https://northboundwisdom.github.io/sonafolio/>。源码 `website/`，生成产物 `build/website/`，GitHub Pages 工作流 `.github/workflows/website-pages.yml`。

## 中文默认与内容边界

官网、用户手册与主 README 默认中文，重点说明已经验证的中文播客流程。Material 提供中文界面、中文/英文搜索、深浅色、代码复制和移动导航。代码、配置键、界面按钮名保留实际英文名称；研究与工程原始资料可保留英文。

网页说明当前源码与发布版区别，不把新官网截图当成 v0.9.0 包含所有新功能的证据。网站部署不创建 App tag，也不会升级已下载的 App。

语言政策在 language-assets.json 按确切文件登记中文文档及 locale 资源，不把整个代码目录列为例外。

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
