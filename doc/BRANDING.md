# SonaFolio 品牌与兼容标识

产品名称是 **SonaFolio**；GitHub 仓库是
[NorthBoundWisdom/sonafolio](https://github.com/NorthBoundWisdom/sonafolio)，官网是
[GitHub Pages](https://northboundwisdom.github.io/sonafolio/)。

GitHub Description 和 Python 项目描述统一为：

> Local-first podcast transcription and knowledge library for macOS, iOS, and Windows.

界面、产品文案、帮助说明、文档标题与发布包采用 SonaFolio。CLI 继续使用 `atot`。
下面的名称作为兼容标识保留，不应进行全仓字符串替换。

| 保留标识 | 原因与边界 |
| --- | --- |
| `atot`、`ATOT_*`、`src/atot/` | 稳定 CLI、Python 模块和运行环境接口 |
| `audio2text-local`、`audio2text_local-*.whl` | Python 分发包及 App 查找随包 wheel 的约定 |
| `Audio2TextCli` | 已有脚本与 App bundle 内的兼容 CLI 入口；新文档优先用 `atot` |
| `SpeechToTextData/`、`Audio2TextLibrary/`、iCloud Drive 的 `Audio2Text/` | 已有模型、音频、资料库路径；改品牌无需移动数据 |
| `audio2text.library.*` 等 JSON kind | 已有资料库 schema 与 Swift/Qt/Python 共享协议 |
| `com.audio2text.local*`、`local.audio2text.Audio2TextQt` | Bundle、签名和系统设置身份，避免旧偏好与授权失效 |
| Qt `Audio2Text` / `Audio2TextQt` QSettings、`audio2text.*` 偏好或凭据键 | 已有设置、Keychain、服务标识与 Git hooks 配置 |
| `Audio2TextApp`、`Audio2TextCore`、`Audio2TextiOS`、`Audio2Text-iOS`、`Audio2TextQt` | 源码目录、Swift 模块、Xcode scheme 与 CMake target；对开发命令保留兼容 |
| `Audio2Text.xcodeproj`、`Audio2Text.xcassets`、`/Audio2TextQt/` QML URI | 生成项目、资源目录与 qrc 地址；资源不是产品显示名 |
| `audio2text-transcribe` Skill ID | 已有 Skill 调用名；其显示名称使用 SonaFolio |
| 用户已注册的 `audio2text` MCP 连接 | MCP 客户端自定义别名；新安装建议 `sonafolio`，旧连接继续有效 |
| 旧测试夹具、历史诊断文件名与历史实验记录 | 对旧数据的兼容覆盖及当时测量证据；历史名称指 SonaFolio 的早期版本 |

发布产物名为 `SonaFolioQt-v<version>-...` 与 `SonaFolioSwift-v<version>-...`。
Swift App bundle 为 `SonaFolio.app`，Qt 可执行文件和 bundle 为 `SonaFolioQt`。

## 文档维护规则

- 当前用户文档采用 SonaFolio；出现兼容名称时使用代码样式并指向本清单。
- 不修改 `FreeCM/` 的第三方品牌、许可和源码身份。
- `doc/experiments/` 的实测记录保留原始命令与数据；目录索引解释旧名称和结果日期。
- 许可文件保留原始贡献者归属，明确项目现名，不能通过改品牌移除第三方版权。
- 本轮更新了文档索引、架构、开发指南、签名要求、平台边界和 MCP 注册示例。
  当前支持以 README、官网和发布说明为准。
