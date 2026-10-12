# Audio2Text 文档索引

欢迎查阅 Audio2Text 项目文档。

---

## 📚 核心文档

### 用户文档

- **[README.md](../README.md)** - 项目概览、快速入门、安装指南
- **[PRIVACY.md](PRIVACY.md)** - 隐私政策和数据边界说明
- **[QUALITY_LOOP.md](QUALITY_LOOP.md)** - QA 检查、修复流程和质量保证策略
- **[QUALITY_TOOLS.md](QUALITY_TOOLS.md)** - 覆盖率、类型检查、安全审计和热点基准
- **[LIBRARY_LAYOUT.md](LIBRARY_LAYOUT.md)** - Library 当前布局和校验规则

### 开发文档

- **[ARCHITECTURE.md](ARCHITECTURE.md)** ⭐ - 系统架构、模块设计、数据流
- **[TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)** ⭐ - 开发指南、API 参考、调试技巧
- **[AGENTS.md](../AGENTS.md)** - 贡献指南和代码规范

### 状态文档

- **[ROADMAP_STATUS.md](ROADMAP_STATUS.md)** - 功能实现状态和验证映射

### 专题文档

- **[BACKEND_RESEARCH.md](BACKEND_RESEARCH.md)** - ASR 后端研究和候选评估
- **[QUALITY_TOOLS.md](QUALITY_TOOLS.md)** - 质量工具基线和架构边界检查
- **[RELEASE_LICENSES.md](RELEASE_LICENSES.md)** - 发布包许可、源码材料和清单检查
- **[OPEN_SOURCE_AUDIT.md](OPEN_SOURCE_AUDIT.md)** - 当前源码开源审计修复和验证边界

---

## 📂 目录结构

```
doc/
├── README.md                    # 本文档索引
├── ARCHITECTURE.md              # 架构文档 ⭐
├── TECHNICAL_GUIDE.md           # 技术指南 ⭐
├── BACKEND_RESEARCH.md          # 后端研究
├── ROADMAP_STATUS.md            # 功能状态
├── PRIVACY.md                   # 隐私政策
├── QUALITY_LOOP.md              # 质量循环
├── QUALITY_TOOLS.md             # 质量工具基线
├── LIBRARY_LAYOUT.md            # Library 当前布局
├── examples/                    # 示例文件
│   ├── prompt.zh.txt           # 中文提示词
│   ├── glossary.zh.json        # 词汇表
│   └── qa.balanced.json        # QA 配置
├── cloud_prompts/               # 云端提示模板
│   ├── summarize.zh.md
│   ├── chapterize.zh.md
│   ├── glossary_review.zh.md
│   └── polish_transcript.zh.md
└── experiments/                 # 实验记录
    ├── README.md
    ├── asr_candidate_gate_*.md
    ├── asr_candidate_sweep_*.md
    └── process_three_audio.md
```

---

## 🎯 快速导航

### 我想了解...

| 需求 | 推荐文档 |
|------|----------|
| **快速开始使用** | [README.md](../README.md) → 快速开始 |
| **系统如何工作** | [ARCHITECTURE.md](ARCHITECTURE.md) → 系统概览 |
| **如何开发扩展** | [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) → 扩展开发 |
| **添加新后端** | [BACKEND_RESEARCH.md](BACKEND_RESEARCH.md) + [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) |
| **数据隐私保护** | [PRIVACY.md](PRIVACY.md) |
| **质量保证流程** | [QUALITY_LOOP.md](QUALITY_LOOP.md) |
| **功能实现状态** | [ROADMAP_STATUS.md](ROADMAP_STATUS.md) |
| **代码质量** | [QUALITY_TOOLS.md](QUALITY_TOOLS.md) |
| **如何贡献** | [AGENTS.md](../AGENTS.md) |

### 我想做...

| 任务 | 操作步骤 |
|------|----------|
| **转录本地音频** | [README.md](../README.md) → 转录本地音频 |
| **导入小宇宙** | [README.md](../README.md) → 导入小宇宙 |
| **配置云端摘要** | [README.md](../README.md) → 云端文本阶段 |
| **自定义词汇表** | [examples/glossary.zh.json](examples/glossary.zh.json) |
| **调整 QA 策略** | [examples/qa.balanced.json](examples/qa.balanced.json) |
| **修复转录问题** | [QUALITY_LOOP.md](QUALITY_LOOP.md) → 修复流程 |
| **开发新功能** | [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) → 扩展开发 |
| **运行测试** | [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) → 测试指南 |
| **调试问题** | [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md) → 调试技巧 |
| **打包发布** | [README.md](../README.md) → 打包 DMG |

---

## 📖 文档说明

### 核心原则

1. **用户优先** - README 面向最终用户，专注快速上手
2. **开发者友好** - 技术文档详尽，包含代码示例
3. **持续更新** - 文档与代码同步演进
4. **相对路径** - 使用相对路径，避免绝对路径和隐私信息

### 文档职责

| 文档 | 读者 | 重点 |
|------|------|------|
| README.md | 用户 | 安装、使用、配置 |
| ARCHITECTURE.md | 开发者/架构师 | 设计决策、模块职责 |
| TECHNICAL_GUIDE.md | 开发者 | API、测试、调试 |
| BACKEND_RESEARCH.md | 研究者 | 实验结果、候选评估 |
| PRIVACY.md | 用户/合规 | 数据处理、隐私边界 |
| QUALITY_LOOP.md | 用户/运维 | QA、修复、维护 |
| AGENTS.md | 贡献者 | 编码规范、贡献流程 |

### 实验文档政策

`experiments/` 目录保存历史实验快照：

- **不修改** - 实验完成后，文档成为历史记录
- **新增优先** - 重新实验时创建新文件（带日期）
- **可摘要** - 可更新 README 或矩阵汇总
- **相对路径** - 使用 `process/<MMDD>/<episode>/`
- **无隐私** - 不包含私人路径、用户名、音频文件

---

## 🔧 验证脚本

验证输出质量和完整性：

```bash
# 公共路径检查
python src/scripts/check_public_paths.py

# 模型清单验证
python src/scripts/validate_model_inventory.py

# 输出包验证
python src/scripts/validate_output_bundle.py work/<batch>/<episode>

# 运行元数据验证
python src/scripts/validate_run_json.py work/<batch>/<episode>/run.json

# Library 验证
python src/scripts/validate_library.py Audio2TextLibrary

# 云端包验证
python src/scripts/validate_cloud_package.py work/<batch>/<episode>

# 修复审计验证
python src/scripts/validate_repair_artifacts.py work/<batch>/<episode>

# 黄金测试集验证
python src/scripts/validate_gold_set.py

# 后端晋级验证
python src/scripts/validate_backend_promotion.py
```

---

## 📝 示例文件

### 提示词 (`examples/prompt.zh.txt`)

中文播客转录的默认提示词，包含常见术语和上下文。

### 词汇表 (`examples/glossary.zh.json`)

```json
{
  "safe_global": [
    {"pattern": "GPT3", "replacement": "GPT-3"},
    {"pattern": "ChatGPT", "replacement": "ChatGPT"}
  ],
  "contextual_regex": [
    {
      "pattern": "论文",
      "replacement": "论文",
      "trigger": "学术"
    }
  ]
}
```

### QA 配置 (`examples/qa.balanced.json`)

```json
{
  "policy": "balanced",
  "thresholds": {
    "max_gap_seconds": 3.0,
    "max_segment_duration": 45.0,
    "min_confidence": 0.75
  }
}
```

---

## 🧪 实验目录

`experiments/` 保存历史实验记录：

### 当前实验

- **process_three_audio.md** - 三音频基准测试
- **asr_candidate_sweep_2026-05-31.md** - 解码配置扫描
- **asr_candidate_gate_matrix.md** - 候选后端对比矩阵

### 后端评估

- **asr_candidate_gate_smoke.md** - 冒烟测试
- **asr_candidate_gate_local_mlx_whisper.md** - MLX Whisper 本地评估
- **asr_candidate_gate_local_mlx_whisper_4bit.md** - 4bit 量化评估
- **asr_candidate_gate_local_mlx_whisper_large_v3.md** - large-v3 评估
- **asr_candidate_readiness_2026-05-28.md** - 后端就绪检查

参见 [experiments/README.md](experiments/README.md) 了解实验文档策略。

---

## 🌐 云端提示模板

`cloud_prompts/` 包含云端处理的提示模板：

- **summarize.zh.md** - 摘要生成提示
- **chapterize.zh.md** - 章节划分提示
- **glossary_review.zh.md** - 术语审阅提示
- **polish_transcript.zh.md** - 转录润色提示

这些模板在 `atot exec cloud prepare` 时复制到输出包的 `cloud/input/prompts/` 目录。

---

## 🔄 文档更新流程

### 何时更新文档

- ✅ 添加新功能
- ✅ 修改 API 接口
- ✅ 重构架构
- ✅ 发现重要问题
- ✅ 完成实验

### 如何更新文档

1. **识别受影响文档** - 功能变更影响哪些文档？
2. **更新相关章节** - 修改对应内容
3. **检查交叉引用** - 确保链接有效
4. **更新版本和日期** - 文档底部标注
5. **提交时说明** - Git commit 描述文档变更

### 文档审查清单

- 信息准确且最新
- 代码示例可运行
- 相对路径正确
- 无隐私信息泄露
- 链接有效
- 格式规范统一

---

## ❓ FAQ

**Q: 找不到某个功能的文档？**  
A: 先查看 README，然后是 ARCHITECTURE 或 TECHNICAL_GUIDE。如果仍未找到，欢迎提出文档改进建议。

**Q: 实验文档过时了？**  
A: 实验文档是历史快照，不代表当前状态。查看 [ROADMAP_STATUS.md](ROADMAP_STATUS.md)
了解当前实现和验证结论。

**Q: 如何贡献文档？**  
A: 参见 AGENTS.md 贡献指南，文档改进同样欢迎！

**Q: 文档和代码不一致？**  
A: 请报告问题，我们会尽快修复。代码为准，但文档应及时同步。

---

## 📬 反馈

文档问题或改进建议：

1. 检查 [AGENTS.md](../AGENTS.md) 贡献流程
2. 提交 issue 或 pull request
3. 附上具体的文档位置和改进建议

---

**文档索引版本:** 2.0  
**最后更新:** 2026-06-10  
**维护者:** Audio2Text Team
