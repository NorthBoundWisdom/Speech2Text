# ASR 后端研究笔记

记录 SonaFolio 后端系统的演进和候选后端评估。

---

## 背景

SonaFolio 最初仅支持 MLX Whisper。为了支持更多后端（如 Qwen ASR、WhisperLiveKit 等），我们建立了后端抽象层并定义了候选晋级流程。

本文档记录已完成的后端集成工作和当前候选结论。

---

## 已完成工作

### ✓ 后端抽象层

**位置:** `src/atot/backends/`

**接口定义:**
```python
class ASRBackend(Protocol):
    def name(self) -> str
    def supports_word_timestamps(self) -> bool
    def transcribe(audio_path, options) -> ASRResult
```

**当前后端:**
- `mlx-whisper` - MLX Whisper (默认生产后端)
- `recording` - 录音回放 (用于测试)
- `fake` - 模拟后端 (用于测试)

### ✓ 候选评估工具

**工具链:**
```bash
# 1. 后端就绪检查
python src/scripts/asr_candidate_readiness.py --preset <name>

# 2. 单音频比较
python src/scripts/compare_asr_candidate.py audio.wav --preset <name>

# 3. 多音频门控
python src/scripts/asr_candidate_gate.py --preset <name> --strict

# 4. 交叉矩阵
python src/scripts/asr_candidate_matrix.py

# 5. 晋级验证
python src/scripts/validate_backend_promotion.py
```

**评估维度:**
- 命令成功率
- 转录质量 (字符比率、校正数、重复度)
- 时间轴兼容性 (SRT/VTT)
- 运行时间和内存
- 空段落检测
- 高频词占比

### ✓ 指标护栏

候选后端必须通过以下护栏：

1. **成功执行** - 命令正常退出
2. **非空输出** - 生成有意义的文本
3. **字符比率** - 70%-150% 基准长度
4. **质量不倒退** - 校正数/审阅数/重复度不增加
5. **时间轴兼容** - 单调、非重叠、SRT/VTT 兼容
6. **高频词控制** - 顶部词频不异常

失败码示例:
- `char_ratio_low` - 输出过短
- `correction_count_regression` - 校正数增加
- `repetition_regression` - 重复问题加剧
- `timestamp_incompatible` - 时间轴问题

### ✓ 运行时指标

**记录在 `run.json`:**
```json
{
  "backend": "mlx-whisper",
  "model": "large-v3-turbo",
  "runtime_metrics": {
    "total_seconds": 523.5,
    "audio_seconds": 5725.3,
    "speed_factor": 10.9,
    "chunks_transcribed": 5,
    "chunks_cached": 0,
    "peak_memory_mb": 2048
  }
}
```

---

## 候选后端状态

### 1. MLX Whisper 变体

#### large-v3-turbo (生产)
- **状态:** ✓ 默认后端
- **模型:** `mlx-community/whisper-large-v3-turbo`
- **性能:** ~10-11x 实时速度，~2.2 GB 内存
- **质量:** 三音频门控全部通过

#### large-v3-4bit
- **状态:** ⚠️ 实验性
- **模型:** `mlx-community/whisper-large-v3-mlx-4bit`
- **性能:** 显著慢于 `large-v3-turbo`
- **质量:** 三音频门控 1/3 通过
- **问题:** `char_ratio_low`, `top_token_ratio_regression`

#### large-v3
- **状态:** ❌ 不推荐
- **模型:** `mlx-community/whisper-large-v3-mlx`
- **性能:** ~219s/音频，~4.0 GB 内存
- **质量:** 三音频门控 0/3 通过
- **问题:** 严重 `repetition_regression`

### 2. 解码配置文件

测试了多种解码参数组合:

#### no-prev (最佳候选)
```python
condition_on_previous_text = False
```
- **优势:** 显著减少重复短语、空窗口
- **劣势:** 某些音频可能出现 `review_issue_regression`
- **状态:** 已完成 11 条长音频检查和语义审阅，8 条通过指标护栏，3 条出现审阅回归
- **结论:** 保持为可选候选配置，不晋级为默认配置

#### conservative
```python
temperature = (0.0, 0.2, 0.4)
compression_ratio_threshold = 1.8
logprob_threshold = -1.2
```
- **优势:** 更保守的生成策略
- **劣势:** 速度慢，保留文本略少
- **建议:** 作为后备配置

#### anti-repeat
```python
repetition_penalty = 1.1
```
- **状态:** 未晋级；现有证据没有显示相对 `no-prev` 的明确优势，当前不继续投入

**实验记录:** `doc/experiments/asr_candidate_sweep_2026-05-31.md`

### 3. Qwen ASR

#### mlx-qwen3-asr-0.6b
- **安装:** `$ATOT_DATA_ROOT/cache/tools/mlx-qwen3-asr-venv` (隔离环境)
- **模型:** `Qwen/Qwen3-ASR-0.6B` + `Qwen/Qwen3-ForcedAligner-0.6B`
- **特性:** 
  - 支持 `--context` (上下文)
  - 支持 `--timestamps` (强制对齐)
  - JSON 输出
- **状态:** ❌ 三音频窗口门控 0/3 通过；全部缺少兼容时间戳，其中 1 条出现重复回归
- **结论:** 保持实验性，不晋级；重新评估前必须先修复 forced alignment 时间轴归一化

### 4. WhisperLiveKit

#### whisperlivekit-mlx
- **安装:** `$ATOT_DATA_ROOT/cache/tools/whisperlivekit-venv` (隔离环境)
- **特性:**
  - 多后端支持 (MLX, faster-whisper)
  - 流式转录
  - 丰富的度量收集
- **状态:** ❌ 三条完整音频均在启动阶段失败；请求的 MLX 后端不可用或与所提供的本地模型不兼容
- **结论:** 保持诊断候选，不对产品暴露；只有上游兼容组合可用时才重新门控

**实验记录:** `doc/experiments/asr_candidate_readiness_2026-05-28.md`、
`doc/experiments/asr_candidate_gate_qwen_whisperlivekit_2026-06-24.md`

---

## 晋级标准

候选后端要成为生产默认，必须满足：

### 必需条件

1. **黄金测试集** - 至少 1 个黄金样本
2. **多音频验证** - 至少 3 个完整播客
3. **内容多样性** - 覆盖不同话题/说话人
4. **QA 不倒退** - 审阅数/校正数/重复度不增加
5. **字符密度稳定** - 字符数在合理范围
6. **运行时可接受** - 速度和内存合理
7. **语义审阅** - 人工确认质量

### 推荐条件

8. **词汇表支持** - 接受上下文/词汇表
9. **时间戳输出** - 段落级时间戳
10. **低幻觉风险** - 重复/无意义输出少

**验证工具:**
```bash
python src/scripts/validate_backend_promotion.py \
  --gate-summary output/benchmark/asr_candidate_gate/summary.json \
  --semantic-review output/benchmark/asr_candidate_gate/semantic_review.json
```

---

## 隔离安装策略

候选后端使用数据根目录下的独立虚拟环境，避免污染主环境：

```
$ATOT_DATA_ROOT/cache/tools/
├── bin/
│   └── ffmpeg              # imageio-ffmpeg shim
├── mlx-qwen3-asr-venv/     # Qwen ASR
│   └── bin/mlx-qwen3-asr
└── whisperlivekit-venv/    # WhisperLiveKit
    └── bin/wlk
```

**原则:**
- 主环境 (`~/Documents/SpeechToTextData/env/`) 仅包含生产依赖
- 候选环境在 `.tools/` 下隔离
- 通过预设 (`--preset`) 调用候选命令
- 晋级后才合并到主环境

---

## 借鉴的设计模式

从 WhisperLiveKit 和其他项目借鉴的模式：

### ✓ 已采用

1. **后端抽象** - 清晰的接口，支持多实现
2. **结构化度量** - `run.json` 记录完整运行元数据
3. **归一化输出** - 统一 `segments` 格式
4. **日志分离** - `run.log` 独立于标准输出
5. **可比较实验** - 固定输入、可复现结果

### 未采用 (保持简洁)

- 实时流式转录 - SonaFolio 专注批处理
- WebSocket 服务器 - CLI 优先
- 浏览器 UI - 原生 macOS App 更合适
- LocalAgreement 流式策略 - 当前固定切块已满足需求

---

## 实验记录

完整实验结果在 `doc/experiments/`:

- `process_three_audio.md` - 基准三音频结果
- `asr_candidate_gate_*.md` - 各候选门控结果
- `asr_candidate_sweep_2026-05-31.md` - 配置扫描
- `asr_candidate_gate_matrix.md` - 交叉对比矩阵

---

## 参考资源

- **后端接口:** `src/atot/backends/base.py`
- **候选预设:** `src/scripts/asr_candidate_presets.py`
- **比较工具:** `src/scripts/compare_asr_candidate.py`
- **门控工具:** `src/scripts/asr_candidate_gate.py`
- **晋级验证:** `src/scripts/validate_backend_promotion.py`

---

**更新时间:** 2026-07-10
**文档版本:** 2.1
