# 开发与参与

原始源码使用 MIT，第三方组件、模型与媒体遵循各自许可。用户文档默认中文，代码、配置键和界面身份保持实际名称；历史测量保留原始证据。

## 本地客户端

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution ad-hoc
python3 configs/ios_workflow.py build --platform ios --scheme Audio2Text-iOS --configuration debug
```

macOS 原生包在 `build/app/SonaFolio.app`；iOS 命令验证模拟器构建。Qt 使用本机 Qt SDK 与 CMake：

```bash
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
```

替换实际 SDK 路径，不提交机器绝对路径。生产 ASR 后端的变更需要质量门与语义审阅，不因“能编译”就晋升。

## 测试与文档

```bash
python -m ruff check .
python -m mypy
python -m pytest
python configs/check_docs.py
python configs/check_repository_language.py
```

运行在托管 Python 环境。Swift/Qt 的专门验证见各客户端 README。

网站使用 MkDocs Material，源码 `website/`，输出 `build/website/`。严格构建、资源/链接、语言政策与公共路径检查完成后，由 GitHub Pages 发布；生成 HTML 不进 Git。模型、音频、用户库与凭据也不进 Git。

## 技术资料入口

- [仓库与中文 README](https://github.com/NorthBoundWisdom/sonafolio)
- [架构参考](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/ARCHITECTURE.md)
- [构建与扩展参考](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/TECHNICAL_GUIDE.md)
- [Agent 开发政策](https://github.com/NorthBoundWisdom/sonafolio/blob/main/AGENTS.md)
- [CI 与 tag 发布](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/CI_RELEASES.md)
- [第三方许可](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/RELEASE_LICENSES.md)
- [官网维护说明](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/WEBSITE.md)

技术与研究参考中可能保留英文原文；默认用户流程以[中文手册](handbook.md)为准，下载包能力以对应 release 为准。
