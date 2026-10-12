# SonaFolio Architecture

SonaFolio 是一个模块化的本地音频转录系统，专为 Apple Silicon 和中文播客优化。

---

## 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                     macOS SwiftUI App                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  导入界面    │  │  处理队列    │  │  设置管理    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                  │
│                  ┌────────▼────────┐                         │
│                  │ JobController   │                         │
│                  └────────┬────────┘                         │
└───────────────────────────┼──────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  atot CLI (Python) │
                  └─────────┬─────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼──────┐
│ WorkflowService│  │  命令执行器    │  │  配置系统   │
└───────┬────────┘  └───────┬────────┘  └──────┬──────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼──────┐
│  音频处理      │  │  ASR 后端      │  │  后处理     │
│  (FFmpeg)      │  │  (MLX Whisper) │  │  (QA/校正)  │
└────────────────┘  └────────────────┘  └─────────────┘
```

---

## 核心模块

### 1. CLI 层 (`src/atot/cli.py`)

**职责:**
- 命令行接口入口
- 参数解析和验证
- 子命令路由 (exec, config, subscriptions)

**关键命令:**
```bash
atot                          # TUI 交互模式
atot exec transcribe <audio>  # 转录
atot exec import <url>        # 导入小宇宙
atot exec qa <output>         # 质量检查
atot exec repair <output>     # 修复窗口
atot exec cloud <command>     # 云端文本处理
atot config list/get/set      # 配置管理
```

### 2. 工作流服务 (`src/atot/workflow_service.py`)

**职责:**
- 统一服务入口，供 CLI 和 App 调用
- 任务编排和状态管理
- 事件通知机制

**核心方法:**
- `transcribe()` - 转录工作流
- `import_xiaoyuzhou()` - 小宇宙导入
- `run_qa()` - 质量检查
- `run_repair()` - 执行修复
- `cloud_prepare()`/`cloud_summarize()` - 云端处理

### 3. 转录管线 (`src/atot/pipeline/`)

核心转录流程由多个管线模块协作完成：

#### `pipeline/__init__.py` - 主管线入口
```python
def run_transcription(options: TranscribeOptions) -> dict:
    # 1. 准备音频 (转换为 16kHz mono WAV)
    # 2. 计算切块布局
    # 3. 物化切块 WAV 文件
    # 4. ASR 转录 (带缓存复用)
    # 5. 后处理 (校正、标点、合并)
    # 6. QA 质量检查
    # 7. 写入输出文件
    # 8. 返回 run.json 元数据
```

**关键子模块:**
- `pipeline/audio_cache.py` - 音频准备和缓存决策
- `pipeline/chunks.py` - 切块计划和物化
- `pipeline/asr.py` - ASR 执行和缓存
- `pipeline/postprocess.py` - 后处理流程
- `pipeline/identity.py` - 指纹计算 (SHA256)
- `pipeline/runinfo.py` - 运行信息构建

#### 缓存策略

**音频缓存:**
```python
PreparedAudioCacheDecision:
    - USE_EXISTING: 指纹匹配，复用
    - REGENERATE: 指纹不匹配或强制重新准备
```

**ASR 缓存:**
```python
ASRChunkCacheDecision:
    - USE_EXISTING: 转录指纹匹配 (模型+提示+chunk布局)
    - REGENERATE: 强制重新转录
    - STALE: 元数据不匹配
```

### 4. ASR 后端抽象 (`src/atot/backends/`)

**设计模式:** 策略模式，支持多后端切换

```python
class ASRBackend(Protocol):
    def name(self) -> str: ...
    def supports_word_timestamps(self) -> bool: ...
    def transcribe(
        self, 
        audio_path: Path, 
        options: ASRTranscribeOptions
    ) -> ASRResult: ...
```

**当前后端:**
- `mlx_whisper.py` - MLX Whisper (默认)
- `recording.py` - 录音回放 (测试)
- `fake.py` - 模拟后端 (测试)

**后端注册表:** `registry.py`
- 动态后端发现
- 模型别名解析

### 5. 音频处理 (`src/atot/audio.py`)

**功能:**
- FFmpeg/afconvert 音频转换
- 时长探测 (ffprobe/afinfo)
- 智能切块 + VAD 静音检测
- 固定切块 + 重叠处理

**关键函数:**
```python
prepare_audio()           # 转换为 16kHz mono WAV
ffprobe_duration()        # 探测时长
compute_chunks()          # 计算切块
materialize_chunks()      # 物化切块 WAV
```

### 6. 后处理系统

#### 校正 (`src/atot/corrections.py`)
```python
# 校正类型
- glossary: 词汇表匹配
- title_context: 标题上下文
- asr_runaway_repetition: 重复清理
- topic_triggered: 主题触发
- entity_near_miss: 实体近似匹配
```

**校正记录:**
```json
{
  "kind": "glossary",
  "rule_id": "ChatGPT",
  "original": "ChiaGPT",
  "replacement": "ChatGPT",
  "segment_index": 42,
  "context": "我们讨论了 ChiaGPT 的应用"
}
```

#### QA 检查 (`src/atot/qa/`)

**检查维度:**
- 时间轴: 间隙、重叠、单调性
- 文本: 密度、可见字符、空段落
- 段落: 过长、低置信度、高压缩率
- 元数据: 块覆盖、清单一致性
- 字幕: SRT/VTT 兼容性

**评分系统:**
```python
score = base - blockers * 25 - warnings * 6 - reviews * 3
# base: 90 (有内容) / 65 (空)
```

**输出:**
- `qa.json` - 结构化问题
- `qa.md` - 可读报告
- `review.json` - 审阅建议

#### 修复 (`src/atot/repair.py`)

**修复计划:**
```python
1. 从 QA 收集问题窗口
2. 决策: 重新转录 vs 跳过
3. 执行修复
4. 快照: pre_repair_snapshot_*.json
5. 审计: repair_run_*.json
```

### 7. 云端处理 (`src/atot/cloud/`)

**架构:** 文本包模式，音频不上传

```
cloud/input/
  ├── manifest.json          # 元数据
  ├── README.md             # 说明
  ├── transcript.readable.md # 转录文本
  ├── chunks/               # 分块文本
  └── prompts/              # 提示模板

cloud/output/
  ├── manifest.json
  ├── summary.md
  ├── chapters.json
  └── glossary_suggestions.json
```

**模块:**
- `prepare.py` - 打包云端输入
- `summary.py` - 摘要生成
- `chunking.py` - 文本分块
- `review.py` - 术语审阅
- `publish.py` - 输出发布
- `client.py` - OpenAI 兼容客户端

### 8. 配置系统 (`src/atot/config_v2.py`)

**配置文件:** `~/Documents/SpeechToTextData/config.toml`

```toml
[local]
asr_model = "large-v3-turbo"
language = "zh"
backend = "mlx-whisper"

[workflow]
default_cloud_summary = false

[cloud]
api_base = "https://api.example.com/v1"
api_key = ""
api_key_store = "system"
model = "gpt-5.4-mini"

[translation]
enabled = false
backend = "local"
target_language = "zh"
```

**命令行覆盖:**
```bash
atot -c local.language='"en"' exec transcribe audio.mp3
```

### 9. 小宇宙导入 (`src/atot/xiaoyuzhou.py`)

**功能:**
- 单集导入
- 订阅管理
- 元数据提取 (`主题.md`, `episode.json`)
- 音频下载

**存储:**
```
materials/<episode_id>/
  ├── <audio>.<ext>
  ├── 主题.md
  └── episode.json

work/<episode_id>/
  ├── transcript.readable.md
  ├── run.json
  └── cloud/

Audio2TextLibrary/
  ├── manifest.json
  └── episodes/<episode_id>/
      ├── episode.json
      └── documents/
          ├── summary.md
          └── transcript.md
```

### 10. macOS App (`app/Sources/Audio2TextApp/`)

**架构:** SwiftUI + Combine

**核心组件:**
- `Audio2TextApp.swift` - App 入口
- `JobController.swift` - 共享状态与生命周期；Library、Batch、Cloud、Summary 等职责拆分在对应的 `JobController` 扩展中
- `ProcessLibrary.swift` - 处理库管理
- `AppStore.swift` - 状态管理
- `SettingsView.swift` - 设置界面

**通信机制:**
```swift
// App 通过 CLI 执行工作流
Audio2TextCli exec transcribe --json --watch

// 解析 JSON 事件流
{"event": "stage", "stage": "prepare_audio"}
{"event": "chunk_progress", "completed": 5, "total": 20}
{"event": "complete", "output_dir": "..."}
```

---

## 数据流

### 转录流程

```
1. 用户输入
   └─> 音频文件 / 小宇宙 URL

2. 音频准备
   └─> FFmpeg 转换 → 16kHz mono WAV
   └─> 指纹: input_file_sha256, prepared_audio_sha256

3. 切块计划
   └─> 固定切块 (默认 20min, 10s overlap)
   └─> 智能切块 (VAD + 静音检测)
   └─> 指纹: chunk_layout_sha256

4. 物化切块
   └─> 生成 chunk_0000.wav, chunk_0001.wav, ...
   └─> 写入 chunks_manifest.json

5. ASR 转录
   └─> 后端: MLX Whisper
   └─> 模型: large-v3-turbo
   └─> 输出: chunk_*.json (segments, text, confidence)
   └─> 缓存复用检查: transcription_fingerprint_sha256

6. 后处理
   └─> 合并段落
   └─> 词汇表校正
   └─> 标点规范化
   └─> 时间轴修复
   └─> 指纹: postprocess_fingerprint_sha256

7. QA 检查
   └─> 时间轴验证
   └─> 文本质量检查
   └─> 生成 qa.json, qa.md

8. 输出生成
   └─> transcript.readable.md
   └─> transcript.srt
   └─> transcript.vtt
   └─> raw.json
   └─> corrected.json
   └─> corrections.json
   └─> run.json
   └─> run.log
```

### 修复流程

```
1. QA 检测问题 → 问题窗口列表

2. 修复计划
   └─> 评估窗口: 可修复 / 阻断器
   └─> 决策: 重新转录 vs 跳过

3. 快照
   └─> pre_repair_snapshot_<timestamp>.json

4. 执行修复
   └─> 重新转录问题窗口
   └─> 应用相同后处理

5. 合并
   └─> 更新 corrected.json
   └─> 重新生成输出文件

6. 审计
   └─> repair_run_<timestamp>.json
   └─> post_repair_snapshot_<timestamp>.json
```

### 云端流程

```
1. 准备
   └─> 打包文本 → cloud/input/
   └─> 隐私扫描 (可选 PII 脱敏)
   └─> 生成 manifest.json

2. 摘要
   └─> 分块文本 (8000 字/块)
   └─> 并行 API 调用 (块级摘要)
   └─> 合并 → 完整摘要

3. 审阅
   └─> 术语提取
   └─> 实体识别
   └─> 词汇表建议

4. 发布
   └─> 写入 cloud/output/
   └─> 验证输出模式
```

---

## 指纹系统

SonaFolio 使用 SHA256 指纹实现智能缓存复用。

### 指纹类型

**1. 输入指纹**
```python
input_file_sha256 = sha256(原始音频文件)
```

**2. 准备音频指纹**
```python
prepared_audio_sha256 = sha256(WAV 文件)
prepared_audio_fingerprint = {
    "path": "prepared.wav",
    "size": 12345678,
    "sample_rate": 16000,
    "channels": 1,
    "prepare_tool": "ffmpeg",
    "prepare_command": "ffmpeg -i input.m4a ..."
}
```

**3. 切块布局指纹**
```python
chunk_layout_sha256 = sha256(json({
    "chunks": [
        {"start": 0, "end": 1200, "duration": 1200},
        {"start": 1190, "end": 2390, "duration": 1200}
    ],
    "overlap": 10,
    "total_duration": 5725.3
}))
```

**4. 转录指纹**
```python
transcription_fingerprint_sha256 = sha256(json({
    "backend": "mlx-whisper",
    "model": "large-v3-turbo",
    "language": "zh",
    "prompt": "...",
    "glossary": {...},
    "chunk_layout_sha256": "abc123...",
    "decode_params": {
        "temperature": 0.0,
        "condition_on_previous_text": true,
        ...
    }
}))
```

**5. 后处理指纹**
```python
postprocess_fingerprint_sha256 = sha256(json({
    "glossary": {...},
    "rule_packs": ["chinese_punctuation"],
    "corrections_config": {...}
}))
```

### 缓存决策矩阵

| 场景 | 指纹变化 | 决策 | 复用 |
|------|---------|------|------|
| 完全相同的重跑 | 无变化 | 全部复用 | 音频+ASR+后处理 |
| 修改词汇表 | postprocess 变化 | 复用 ASR | 音频+ASR |
| 修改提示词 | transcription 变化 | 复用音频 | 仅音频 |
| 修改切块参数 | chunk_layout 变化 | 复用音频 | 仅音频 |
| 更换模型 | transcription 变化 | 复用音频 | 仅音频 |
| 更换音频文件 | input 变化 | 全部重新生成 | 无 |

---

## 文件结构

### 本地资料库结构

```
materials/<batch>/<episode>/
├── episode.json                 # 节目元信息
├── 主题.md / intro.md            # 简介原文
└── <audio>.<ext>                # 原始音视频

work/<batch>/<episode>/
├── transcript.readable.md       # 中间可读转录
├── raw.json                     # 原始 ASR 输出
├── corrected.json               # 校正后段落
├── transcript.srt               # SRT 字幕
├── transcript.vtt               # WebVTT 字幕
├── transcript.timestamped.md    # 带时间戳版本
├── corrections.json             # 校正记录
├── qa.json                      # QA 结构化结果
├── qa.md                        # QA 可读报告
├── review.json                  # 审阅建议
├── entity_consistency.json      # 实体一致性
├── run.json                     # 运行元数据 ★
├── run.log                      # 运行日志
├── events.jsonl                 # 事件流
├── chunks_manifest.json         # 切块清单
├── chunks/                      # 切块数据
├── repair/                      # 修复历史
└── cloud/                       # 云端输入/输出包

Audio2TextLibrary/episodes/<episode_id>/documents/
├── summary.md                   # 可同步摘要
└── transcript.md                # 可同步可读正文
```

### run.json 核心字段

```json
{
  "input_file": "/path/to/audio.m4a",
  "input_file_sha256": "abc123...",
  "prepared_audio": {
    "path": "prepared.wav",
    "sha256": "def456...",
    "sample_rate": 16000,
    "channels": 1,
    "prepare_tool": "ffmpeg"
  },
  "chunk_layout_sha256": "ghi789...",
  "transcription_fingerprint_sha256": "jkl012...",
  "postprocess_fingerprint_sha256": "mno345...",
  "backend": "mlx-whisper",
  "model": "large-v3-turbo",
  "language": "zh",
  "prompt": "...",
  "glossary": {...},
  "chunk_count": 5,
  "total_duration": 5725.3,
  "quality_metrics": {
    "qa_score": 87,
    "timing": {
      "srt_vtt_compatible": true,
      "overlaps": 0,
      "gaps_count": 2
    },
    "text": {
      "total_chars": 125430,
      "visible_chars": 123890,
      "segment_count": 1342
    },
    "corrections": {
      "glossary": 45,
      "title_context": 3,
      "asr_runaway_repetition": 2
    }
  },
  "runtime_metrics": {
    "total_seconds": 523.5,
    "audio_seconds": 5725.3,
    "speed_factor": 10.9,
    "chunks_transcribed": 5,
    "chunks_cached": 0
  }
}
```

---

## 扩展点

### 1. 添加新 ASR 后端

```python
# src/atot/backends/my_backend.py
from .base import ASRBackend, ASRResult, ASRTranscribeOptions

class MyBackend(ASRBackend):
    def name(self) -> str:
        return "my-backend"
    
    def transcribe(
        self, 
        audio_path: Path, 
        options: ASRTranscribeOptions
    ) -> ASRResult:
        # 实现转录逻辑
        return ASRResult(
            text="转录文本",
            segments=[...],
            language="zh"
        )

# src/atot/backends/registry.py
_BACKENDS["my-backend"] = MyBackend
```

### 2. 添加后处理规则

```python
# src/atot/data/rule_packs/my_rules.json
{
  "safe_global": [
    {"pattern": "错误词", "replacement": "正确词"}
  ],
  "contextual_regex": [
    {
      "pattern": "模糊词",
      "replacement": "精确词",
      "trigger": "上下文关键词"
    }
  ]
}
```

### 3. 自定义 QA 策略

```python
# doc/examples/qa.custom.json
{
  "policy": "custom",
  "thresholds": {
    "max_gap_seconds": 5.0,
    "max_segment_duration": 60.0,
    "min_confidence": 0.7
  },
  "weights": {
    "blocker": 25,
    "warning": 6,
    "review": 3
  }
}
```

### 4. 集成云端服务

```python
# 自定义云端客户端
from atot.cloud.client import CloudClient

client = CloudClient(
    api_base="https://api.example.com/v1",
    api_key="sk-...",
    model="custom-model"
)

# 调用摘要
summary = client.summarize(text="...")
```

---

## 性能特征

### 典型性能 (Apple Silicon M1/M2)

| 场景 | 音频时长 | 处理时间 | 速度因子 | 内存 |
|------|---------|---------|---------|------|
| 小文件 (2min) | 120s | 15s | 8x | ~1.5 GB |
| 中等文件 (30min) | 1800s | 180s | 10x | ~2.0 GB |
| 长文件 (95min) | 5725s | 523s | 11x | ~2.2 GB |

**注意:** 
- 首次运行包含模型加载时间 (~10-20s)
- 缓存复用可将重复运行时间降至 <5s
- 智能切块比固定切块慢 10-15%

### 并发处理

- ASR 后端: 串行处理切块 (单模型实例)
- 云端 API: 并行调用 (可配置并发数)
- 文件 I/O: 异步写入

---

## 安全考虑

### 1. 本地隐私

- **默认:** 所有处理本地完成
- **音频:** 永不上传到云端
- **模型:** 本地存储在 `~/Documents/SpeechToTextData/model/`

### 2. 云端隐私

- **传输:** 仅文本包 (无音频/视频)
- **PII 脱敏:** 可选，扫描电话/邮箱/地址
- **审计:** 完整请求/响应记录在 `cloud/audit/`

### 3. API 密钥

- **存储:** 非敏感设置放在 `~/Documents/SpeechToTextData/config.toml`；key 使用 macOS Keychain / Windows Credential Manager，App 与 CLI 按配置路径共用条目。
- **权限:** 仅当前用户可读
- **日志:** 自动脱敏 (不记录明文密钥)

### 4. 路径安全

- **验证:** 所有路径通过 `is_relative_safe()` 检查
- **沙盒:** 限制在数据根目录内
- **符号链接:** 解析后验证

---

## 测试策略

### 自动化测试

```bash
python -m pytest
swift test --package-path app
```

**覆盖模块:**
- 段落处理
- 校正逻辑
- QA 检查
- 修复计划
- 云端打包
- 配置管理

### 集成测试

```bash
pytest src/tests/test_pipeline_integration.py
```

**覆盖流程:**
- 完整转录流程
- 缓存复用
- 错误恢复

### 验证脚本

```bash
# 运行元数据验证
python src/scripts/validate_run_json.py work/0000/sample/run.json

# Library 验证
python src/scripts/validate_library.py Audio2TextLibrary

# 云端包验证
python src/scripts/validate_cloud_package.py work/0000/sample

# 修复审计验证
python src/scripts/validate_repair_artifacts.py work/0000/sample

# 后端晋级验证
python src/scripts/validate_backend_promotion.py
```

---

## 故障排查

### 常见问题

**1. FFmpeg 未找到**
```bash
brew install ffmpeg
# 或使用内置 afconvert (仅 macOS)
```

**2. 模型未找到**
```bash
atot models
# 手动下载到 ~/Documents/SpeechToTextData/model/
```

**3. 转录失败**
```bash
atot doctor  # 诊断环境
cat output/<batch>/<episode>/run.log  # 查看日志
```

**4. 内存不足**
```bash
# 使用 4bit 量化模型
atot exec transcribe audio.m4a --model large-v3-turbo-q4
```

**5. QA 分数低**
```bash
# 查看详细报告
cat output/<batch>/<episode>/qa.md

# 计划修复
atot exec repair output/<batch>/<episode> --plan-only
```

---

## 贡献指南

参见根目录 `AGENTS.md` 了解代码规范和贡献流程。

**关键原则:**
- 保持模块化和可测试性
- 添加单元测试
- 更新相关文档
- 通过 `ruff check .`
- 验证输出包格式

---

**更新时间:** 2026-06-10  
**文档版本:** 1.0
