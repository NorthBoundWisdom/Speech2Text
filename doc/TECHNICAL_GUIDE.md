# SonaFolio 开发指南

本指南对应当前源码接口。用户安装、模型下载清单和稳定命令见[README](../README.md)，
模块关系见[架构](ARCHITECTURE.md)，仓库约定见[AGENTS](../AGENTS.md)。

## 初始化

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

Python 最低版本是 3.10。macOS 稳定 ASR 需要 Apple Silicon；Swift App 最低 macOS 13，
iOS 目标最低 iOS 17。Swift 构建使用 Xcode；Qt 客户端需要 Qt 6.8+，当前 CI 验证 Qt 6.12.0。
Windows CLI 不依赖 Xcode 或 Swift。

本机环境位于 `~/Documents/SpeechToTextData/env/`。macOS 激活后安装开发工具：

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
python -m pip install --constraint constraints/runtime.txt -e ".[dev]"
atot doctor
```

Windows 使用数据根目录 `env\Scripts\python.exe`，测试使用 `python -m pytest`。
`ATOT_DATA_ROOT` 可由 CLI/客户端显式指定数据根；默认位置仍是 `~/Documents/SpeechToTextData/`。
模型只能放在数据根的 `model/`，不要下载到源码树或提交模型与生成转录。

## 目录与源码接口

| 目录 | 维护范围 |
| --- | --- |
| `src/atot/` | Python CLI、工作流、ASR、资料库与 MCP |
| `src/scripts/` | 验证与候选实验薄入口 |
| `src/tests/` | Python 行为、平台与协议测试 |
| `app/Sources/`、`app/Tests/` | Swift 客户端、共享资料库协议及测试 |
| `qt/Audio2TextQt/` | Qt C++ / QML 客户端 |
| `configs/` | 本机设置、项目生成、构建、安装器与发行工具 |
| `website/` | 官网与用户手册源码 |
| `doc/experiments/` | 历史测量记录；不改写旧结果 |
| `FreeCM/` | 固定 gitlink 的第三方构建基础设施 |

`WorkflowService` 当前提供 `run_transcribe()`、`run_import_xiaoyuzhou()`、`run_qa()`、
`run_repair()`、`run_cloud_prepare()`、`run_cloud_summarize()`、`run_srt()`、
`run_subscriptions()` 与 `run_library_*()`。它负责流程和任务事件，GUI 不应另写一套 ASR 规则。

`ASRBackend` 是 `src/atot/backends/base.py` 中的 Protocol。实现接收
`transcribe(audio_path, options: ASRTranscribeOptions)`，返回规范化的 `text` 和 `segments`。
新增后端先放入候选逻辑并通过质量门禁，不能仅因能编译就晋升。

MCP 服务由 `create_mcp_server()` 创建，只公开 `list_episodes`、`get_episode`、
`read_document`、`write_summary`。完整文档与 QA 读取、哈希检查和显式覆盖要求是回写契约的一部分。

## 本地构建

SwiftPM 逻辑验证：

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift build -c release --scratch-path ../build/swiftpm --product Audio2TextApp
```

从仓库根目录构建与启动原生 App：

```bash
python3 configs/source_root_workflow.py --init
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
```

iOS 模拟器编译使用 `--platform ios --scheme Audio2Text-iOS`。生成的
`Audio2Text.xcodeproj` 不入 Git；不要手动维护生成项目作为源码。

Qt 构建与 QML 启动验证：

```bash
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
ctest --test-dir build/Audio2TextQt -C Release --output-on-failure
```

Linux/Windows 的 Qt 构建在 CI 中使用 Ninja；Windows 需要 MSVC，Linux SDK 的 ICU ABI 依赖由
发行工具准备。Qt runtime 部署与手动包、自动安装器的内容不同，详见[Qt README](../qt/Audio2TextQt/README.md)。

## 验证

```bash
python -m ruff check .
python -m mypy
python -m pytest
python src/scripts/check_public_paths.py
python src/scripts/validate_model_inventory.py
python src/scripts/validate_run_json.py src/tests/fixtures/run.sample.json
```

公共源码扫描覆盖路径与常见凭据；提交前也会检查 staged 内容。macOS hooks 默认要求 macOS
和 iOS 模拟器 Debug 构建通过。云调用和真实 ASR 验收需要对应用户配置、模型和数据，
不能用模拟测试通过来宣称准确率或真实 CUDA 验证完成。

依赖约束与审计流程见[质量工具](QUALITY_TOOLS.md)。针对改动选择有意义的协议、平台和行为测试；
不要把每次完整依赖下载或真实音频处理变成基础文档构建的前提。

官网检查与预览：

```bash
python -m pip install -r website/requirements.txt
NO_MKDOCS_2_WARNING=true python -m mkdocs build -f website/mkdocs.yml --strict
python configs/check_docs.py
```

## 扩展与诊断

- 修改模型先更新 `model_inventory.json`，再验证下载表与必需文件。
- 共享术语和审阅规则放在 `src/atot/data/`，禁止写入节目专属补丁。
- 缺失后端、模型、CUDA 或必需步骤应清楚报错；不添加未经请求的静默替代流程。
- 处理状态用 `atot status --task-id <task-id>`，文档健康用 `atot exec qa <work-dir>`。
- 日志位于数据根 `cache/logs/` 和对应 work 目录。反馈前移除私人转录、链接与凭据。
- Swift/Qt 内部模块名、`atot` 与存储身份保留兼容，见[品牌说明](BRANDING.md)。

## 发布

GitHub Actions 已覆盖 Python、Swift 和三平台 Qt。推送 `vMAJOR.MINOR.PATCH` tag 后构建 Windows
Qt EXE、Linux Qt AppImage、macOS Qt/Swift DMG。当前无证书发布，macOS 使用 ad-hoc 签名；
自有证书与公证流程仍可手动选择。

官网由 Pages 工作流从 `main` 构建并发布，PR 只做构建校验。

[发行流程](CI_RELEASES.md) · [许可材料](RELEASE_LICENSES.md) · [官网维护](WEBSITE.md)
