# SonaFolio 官网与 GitHub Pages

官网：<https://northboundwisdom.github.io/sonafolio/>。
源码：`website/`，构建结果：`build/website/`，部署工作流：`.github/workflows/website-pages.yml`。

参考兄弟项目 Ravo 的 MkDocs Material 用户手册结构，首页介绍产品、工作流和平台边界，
手册提供安装、转录、资料库、MCP、CLI、QA、隐私与常见问题。页面支持中文搜索、
明暗模式、复制代码和移动端导航。没有网站访问统计或远程字体。

## 本地预览

从仓库根目录创建独立环境，避免将站点依赖混入 ASR 环境：

```bash
python3 -m venv build/website-env
build/website-env/bin/python -m pip install -r website/requirements.txt
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs serve -f website/mkdocs.yml
```

Windows 使用 `build\website-env\Scripts\python.exe`，并在 PowerShell 设置
`$env:NO_MKDOCS_2_WARNING = "true"`。变量只关闭 Material 的 MkDocs 2 迁移提示，不关闭严格构建警告。

## 验证

```bash
python3 configs/check_docs.py
build/website-env/bin/python -m pytest website/tests/test_build_metadata.py
NO_MKDOCS_2_WARNING=true build/website-env/bin/python -m mkdocs build -f website/mkdocs.yml --strict
python3 configs/check_docs.py --site build/website
```

首页构建信息来自当前 Git commit 和实际 UTC 构建时间，文本经过 HTML 转义。
可设置带时区的 `SONAFOLIO_SITE_BUILT_AT` 以复现时间；提交消息不能包含私人信息。

## 部署

仓库 Pages 设置使用 GitHub Actions。每次 push 到 `main` 自动执行链接检查、元信息测试与
严格构建，然后上传单独 Pages artifact，并由 `github-pages` environment 部署。
PR 只构建检查、不部署；无需提交 `gh-pages` 分支或生成 HTML。
部署 job 才有 `pages: write` 和 `id-token: write`，构建 job 只有源码读权限。

官网发布不创建应用 tag 或安装包；原生发行由 `release.yml` 单独处理。
网页的下载入口始终指向 Releases 列表，不能将 Actions 试跑描述成正式发布版本。

## 维护

产品名、链接和兼容标识按[品牌说明](BRANDING.md)维护。平台、签名、模型下载和云摘要行为
必须与当前源码一致；历史实验不能作为用户安装步骤。用户手册页面面向实际操作，
源码架构和研究报告保留在 `doc/`，避免把内部实现堆到产品首页。
