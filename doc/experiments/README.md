# SonaFolio 历史实验索引

本目录保存历史实验快照和基准测试结果。记录中的 Audio2Text / AtoT 是 SonaFolio 的早期名称。
原始命令、数字与测量结果保留原样；这些文件不是当前安装或支持说明。
当前状态见 [后端研究](../BACKEND_RESEARCH.md)、[功能状态](../ROADMAP_STATUS.md)和[品牌说明](../BRANDING.md)。

---

## 文档策略

### 原则

1. **快照性质** - 实验完成后不修改，保留历史记录
2. **新增优先** - 重新实验时创建新文件（带时间戳）
3. **可摘要** - 可更新矩阵汇总或 README
4. **相对路径** - 使用 `process/<MMDD>/<episode>/`，不含私人信息
5. **可复现** - 记录完整命令和环境信息

### 命名规范

```
<category>_<date>_<brief_description>.md
<category>_<name>.md
```

**示例:**
- `asr_candidate_gate_local_mlx_whisper.md`
- `asr_candidate_sweep_2026-05-31.md`
- `process_three_audio.md`

---

## 已记录实验

### 基准测试

- **[process_three_audio.md](process_three_audio.md)** - 三音频基准（咖啡播客 + 两个完整播客）
  - 状态: ✓ 所有 QA 通过，review.md 零问题
  - 用途: 后端对比基准

### 后端评估

#### 门控测试

- **[asr_candidate_gate_smoke.md](asr_candidate_gate_smoke.md)** - 冒烟测试（echo 命令）
- **[asr_candidate_gate_local_mlx_whisper.md](asr_candidate_gate_local_mlx_whisper.md)** - MLX Whisper large-v3-turbo
  - 结果: 3 个命令成功，1/3 通过指标护栏
  - 问题: `correction_count_regression`, `review_issue_regression`
  
- **[asr_candidate_gate_local_mlx_whisper_4bit.md](asr_candidate_gate_local_mlx_whisper_4bit.md)** - 4bit 量化版本
  - 结果: 3 个命令成功，1/3 通过指标护栏
  - 内存: ~1.5 GB (vs 2.2 GB)
  - 问题: `char_ratio_low`, `top_token_ratio_regression`
  
- **[asr_candidate_gate_local_mlx_whisper_large_v3.md](asr_candidate_gate_local_mlx_whisper_large_v3.md)** - 完整 large-v3
  - 结果: 3 个命令成功，0/3 通过指标护栏
  - 内存: ~4.0 GB，速度慢
  - 问题: 严重 `repetition_regression`

- **[asr_candidate_gate_qwen_whisperlivekit_2026-06-24.md](asr_candidate_gate_qwen_whisperlivekit_2026-06-24.md)** - Qwen / WhisperLiveKit 决策
  - Qwen: 3/3 命令成功，0/3 通过时间戳护栏
  - WhisperLiveKit: 0/3 命令成功，MLX 后端不可用或与所提供的模型不兼容
  - 结论: 两者均保持实验性，不晋级

#### 配置扫描

- **[asr_candidate_sweep_2026-05-31.md](asr_candidate_sweep_2026-05-31.md)** - 解码参数扫描
  - 测试配置: `no-prev`, `conservative`, `anti-repeat`, `repair-strict`
  - 最佳候选: `no-prev` (关闭 condition_on_previous_text)
  - 发现: 显著减少重复短语和空窗口

#### 交叉矩阵

- **[asr_candidate_gate_matrix.md](asr_candidate_gate_matrix.md)** - 候选后端对比矩阵
  - 对比维度: 运行时间、内存、通过率、失败码
  - 更新策略: 每次新门控运行后更新

### 就绪检查

- **[asr_candidate_readiness_2026-05-28.md](asr_candidate_readiness_2026-05-28.md)** - 后端环境就绪检查
  - 这是 2026-05-28 的历史快照；当前 readiness 与质量结论见 `doc/BACKEND_RESEARCH.md` 和后端决策记录

---

## 实验类型

### 1. 基准测试 (Baseline)

**目的:** 建立当前生产系统的质量和性能基准

**命名:** `baseline_<date>.md` 或 `process_<description>.md`

**内容:**
- 测试音频列表
- 运行命令
- QA 结果
- 质量指标
- 运行时指标

### 2. 候选评估 (Candidate Gate)

**目的:** 评估新后端或配置是否满足晋级标准

**命名:** `asr_candidate_gate_<backend_name>.md`

**内容:**
- 候选后端信息
- 就绪检查结果
- 三音频门控结果
- 指标护栏通过/失败
- 失败码分析
- 晋级建议

### 3. 参数扫描 (Sweep)

**目的:** 探索参数空间，找到最佳配置

**命名:** `asr_candidate_sweep_<date>.md`

**内容:**
- 参数矩阵
- 每个配置的结果
- 性能对比
- 最佳配置推荐

### 4. 就绪检查 (Readiness)

**目的:** 验证环境和依赖是否满足实验条件

**命名:** `asr_candidate_readiness_<date>.md`

**内容:**
- 环境信息
- 依赖检查
- 模型可用性
- 网络探测结果
- 阻塞问题

### 5. 交叉矩阵 (Matrix)

**目的:** 汇总多个候选的对比结果

**命名:** `asr_candidate_gate_matrix.md`

**内容:**
- 候选列表
- 关键指标对比表
- 晋级状态
- 更新历史

---

## 阅读指南

### 我想了解...

| 需求 | 推荐文档 |
|------|----------|
| 当前生产质量如何 | [process_three_audio.md](process_three_audio.md) |
| 哪个后端最好 | [asr_candidate_gate_matrix.md](asr_candidate_gate_matrix.md) |
| 某后端详细评估 | `asr_candidate_gate_<name>.md` |
| 最佳解码配置 | [asr_candidate_sweep_2026-05-31.md](asr_candidate_sweep_2026-05-31.md) |
| 环境准备状态 | [asr_candidate_readiness_2026-05-28.md](asr_candidate_readiness_2026-05-28.md) |

---

## 实验流程

### 标准后端评估流程

```bash
# 1. 就绪检查
python src/scripts/asr_candidate_readiness.py --preset <name>

# 2. 单音频快速验证
python src/scripts/compare_asr_candidate.py \
  tests/audio/sample.wav \
  --preset <name> \
  --candidate-timeout 300

# 3. 三音频门控
python src/scripts/asr_candidate_gate.py \
  --preset <name> \
  --candidate-timeout 1800 \
  --strict

# 4. 更新矩阵
python src/scripts/asr_candidate_matrix.py

# 5. 记录实验
# - 复制门控输出到 asr_candidate_gate_<name>.md
# - 添加分析和建议
# - 更新本 README
```

---

## 实验环境

实验在以下环境中进行：

- **操作系统:** macOS (Apple Silicon)
- **Python:** 3.10+
- **主环境:** `~/Documents/SpeechToTextData/env/`
- **隔离环境:** `.tools/*-venv/`
- **测试音频:** `process/<MMDD>/<episode>/`

**注意:** 实验结果与硬件、网络、模型版本相关，不同环境可能有差异。

---

## 贡献新实验

### 创建新实验文档

1. **选择合适的实验类型**
2. **按命名规范创建文件**
3. **包含完整信息:**
   - 日期和环境
   - 完整命令
   - 原始输出或摘要
   - 分析和结论
4. **使用相对路径，避免隐私信息**
5. **更新本 README**

### 实验文档模板

```markdown
# <实验标题>

**日期:** YYYY-MM-DD  
**类型:** 基准测试 / 候选评估 / 参数扫描 / 就绪检查  
**目标:** <简短描述实验目的>

---

## 环境

- Python: X.XX
- 后端: <name>
- 模型: <model>
- 测试集: <audio list>

---

## 命令

```bash
<完整可复现命令>
```

---

## 结果

### 汇总

- 成功率: X/Y
- 指标护栏: X/Y 通过
- 平均运行时间: X 秒
- 峰值内存: X MB

### 详细结果

| 音频 | 状态 | 字符数 | QA 分数 | 运行时间 | 内存 | 护栏 |
|------|------|---------|---------|----------|------|------|
| ... | ... | ... | ... | ... | ... | ... |

---

## 分析

<关键发现和问题分析>

---

## 建议

- 建议 1
- 建议 2

---

## 原始输出

<可选: 附加完整输出>
```

---

## 历史实验

较旧的实验记录可能不再反映当前系统状态，但保留用于历史追溯。

### 归档策略

- 保留所有实验记录
- 在 README 中标注 "历史" 或 "已过时"
- 必要时添加注释说明当前状态

---

**维护者:** SonaFolio 贡献者
**索引维护:** 2026-10-13（不修改实验测量日期）
