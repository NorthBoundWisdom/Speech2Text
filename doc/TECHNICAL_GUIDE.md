# SonaFolio 技术指南

开发者和高级用户的深入技术参考。

---

## 目录

1. [开发环境设置](#开发环境设置)
2. [代码库结构](#代码库结构)
3. [核心概念](#核心概念)
4. [API 参考](#api-参考)
5. [测试指南](#测试指南)
6. [调试技巧](#调试技巧)
7. [性能优化](#性能优化)
8. [扩展开发](#扩展开发)

---

## 开发环境设置

### 前置要求

- macOS 12+ (Apple Silicon 推荐)
- Python 3.10+
- Xcode 14+ (用于 macOS App)
- Homebrew

### 克隆和初始化

```bash
git clone <repository-url>
cd SonaFolio

# 初始化子模块 (FreeCM)
git submodule update --init --recursive

# 设置本地环境
python3 configs/setup_local_app.py

# 安装依赖
~/Documents/SpeechToTextData/env/bin/python -m pip install -e .
~/Documents/SpeechToTextData/env/bin/python -m pip install -e ".[dev]"
```

### 验证安装

```bash
~/Documents/SpeechToTextData/env/bin/atot doctor
~/Documents/SpeechToTextData/env/bin/python -m pytest
~/Documents/SpeechToTextData/env/bin/python -m ruff check .
```

### IDE 配置

**VS Code 推荐设置** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "~/Documents/SpeechToTextData/env/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["-q", "src/tests"],
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black"
}
```

---

## 代码库结构

```
Audio2Text/
├── src/atot/                    # Python 核心包
│   ├── __init__.py
│   ├── cli.py                   # CLI 入口
│   ├── workflow_service.py      # 服务层
│   ├── pipeline/                # 转录管线包
│   ├── audio.py                 # 音频处理
│   ├── corrections.py           # 校正逻辑
│   ├── qa/                      # 质量检查包
│   ├── repair.py                # 修复流程
│   ├── backends/                # ASR 后端
│   │   ├── __init__.py
│   │   ├── base.py              # 后端接口
│   │   ├── mlx_whisper.py       # MLX Whisper
│   │   └── registry.py          # 后端注册
│   ├── cloud/                   # 云端处理
│   │   ├── prepare.py           # 打包
│   │   ├── summary.py           # 摘要
│   │   └── client.py            # API 客户端
│   ├── commands/                # CLI 命令
│   ├── data/                    # 数据文件
│   │   ├── model_inventory.json # 模型清单
│   │   └── rule_packs/          # 规则包
│   └── ...
├── src/tests/                   # 测试
│   ├── test_*.py
│   ├── fixtures/                # 测试 fixture
│   └── gold/                    # 黄金标准
├── src/scripts/                 # 实用脚本
│   ├── validate_*.py            # 验证脚本
│   ├── compare_asr_candidate.py # 后端比较
│   └── ...
├── app/                         # macOS App
│   ├── Package.swift
│   └── Sources/Audio2TextApp/   # Swift 源码
│       ├── Audio2TextApp.swift
│       ├── JobController.swift
│       ├── AppStore.swift
│       └── ...
├── configs/                     # 构建配置
│   ├── setup_local_app.py       # 环境设置
│   ├── ios_workflow.py          # 构建脚本
│   └── ...
├── doc/                         # 文档
│   ├── ARCHITECTURE.md          # 架构文档
│   ├── TECHNICAL_GUIDE.md       # 本文档
│   ├── PRIVACY.md               # 隐私说明
│   ├── examples/                # 示例
│   └── experiments/             # 实验记录
├── tests/                       # 集成测试资源
│   └── gold/                    # 黄金测试集
├── pyproject.toml               # Python 项目配置
├── README.md                    # 用户文档
└── AGENTS.md                    # 贡献指南
```

---

## 核心概念

### 1. 作业 (Job)

作业代表一次转录任务的完整生命周期。

```python
from atot.job import build_job_layout

job = build_job_layout(
    input_path=Path("audio.m4a"),
    output_dir=Path("~/Documents/SpeechToTextData/output"),
    name="my-episode"
)

# job.output_dir: output/0610/my-episode/
# job.details_dir: output/0610/my-episode/
# job.chunks_dir: output/0610/my-episode/chunks/
```

### 2. 后端 (Backend)

后端是 ASR 引擎的抽象接口。

```python
from atot.backends import build_backend, ASRTranscribeOptions

backend = build_backend("mlx-whisper")

result = backend.transcribe(
    audio_path=Path("chunk_0000.wav"),
    options=ASRTranscribeOptions(
        model="large-v3-turbo",
        language="zh",
        prompt="播客转录..."
    )
)

# result.text: 完整文本
# result.segments: 分段列表
# result.language: 检测到的语言
```

### 3. 段落 (Segment)

段落是转录的基本单位。

```python
segment = {
    "id": 0,
    "start": 0.0,
    "end": 5.2,
    "text": "欢迎收听本期播客",
    "words": [
        {"word": "欢迎", "start": 0.0, "end": 0.8},
        {"word": "收听", "start": 0.9, "end": 1.5},
        ...
    ],
    "confidence": 0.95,
    "no_speech_prob": 0.02,
    "compression_ratio": 1.8
}
```

### 4. 指纹 (Fingerprint)

指纹用于确定缓存是否有效。

```python
from atot.pipeline.identity import (
    _transcription_fingerprint,
    _postprocess_fingerprint
)

# ASR 指纹 (模型+提示+参数)
asr_fp = _transcription_fingerprint(
    backend="mlx-whisper",
    model="large-v3-turbo",
    language="zh",
    prompt="...",
    glossary={...},
    chunk_layout_sha256="abc123",
    decode_params={...}
)

# 后处理指纹 (词汇表+规则)
post_fp = _postprocess_fingerprint(
    glossary={...},
    rule_packs=["chinese_punctuation"]
)
```

### 5. 事件流 (Event Stream)

管线通过事件流报告进度。

```python
def progress_callback(event: dict):
    if event["event"] == "stage":
        print(f"Stage: {event['stage']}")
    elif event["event"] == "chunk_progress":
        print(f"Progress: {event['completed']}/{event['total']}")

options = TranscribeOptions(
    input_path=Path("audio.m4a"),
    progress_callback=progress_callback
)

run_transcription(options)
```

---

## API 参考

### WorkflowService

主服务类，统一所有工作流操作。

```python
from atot.workflow_service import WorkflowService
from atot.config_v2 import load_atot_config

def event_sink(event: dict):
    print(json.dumps(event))

service = WorkflowService(
    config=load_atot_config(),
    event_sink=event_sink
)

# 转录
result = service.transcribe(
    input_path="audio.m4a",
    model="large-v3-turbo",
    language="zh"
)

# 导入小宇宙
result = service.import_xiaoyuzhou(
    url="https://www.xiaoyuzhoufm.com/episode/...",
    data_only=False
)

# QA 检查
qa_result = service.run_qa(output_dir="output/0610/episode")

# 修复
repair_result = service.run_repair(
    output_dir="output/0610/episode",
    plan_only=False
)

# 云端准备
cloud_result = service.cloud_prepare(
    output_dir="output/0610/episode"
)

# 云端摘要
summary_result = service.cloud_summarize(
    output_dir="output/0610/episode",
    call_api=True
)
```

### 转录管线

```python
from atot.pipeline import run_transcription, TranscribeOptions

options = TranscribeOptions(
    input_path=Path("audio.m4a"),
    output_dir=Path("output"),
    name="my-episode",
    backend="mlx-whisper",
    model="large-v3-turbo",
    language="zh",
    prompt_file=Path("prompt.txt"),
    glossary_file=Path("glossary.json"),
    chunk_length=1200,  # 20 分钟
    overlap=10,
    chunking="smart",  # 或 "fixed"
    force_transcribe=False,
    word_timestamps=False,
    condition_on_previous_text=True,
    temperature=0.0,
    profile=None,  # 或 "no-prev", "conservative"
    rule_packs=["chinese_punctuation"]
)

result = run_transcription(options)

# result["output_dir"]: 输出目录
# result["qa_score"]: QA 分数
# result["total_duration"]: 音频时长
# result["runtime_metrics"]: 性能指标
```

### 音频处理

```python
from atot.audio import (
    prepare_audio,
    ffprobe_duration,
    compute_chunks,
    materialize_chunks
)

# 准备音频
prepared_path = prepare_audio(
    input_path=Path("audio.m4a"),
    output_path=Path("prepared.wav"),
    sample_rate=16000,
    overwrite=False
)

# 探测时长
duration = ffprobe_duration(Path("audio.m4a"))

# 计算切块
chunks = compute_chunks(
    duration=5725.3,
    chunk_length=1200,
    overlap=10
)

# 物化切块
materialize_chunks(
    source_wav=Path("prepared.wav"),
    chunks=chunks,
    output_dir=Path("chunks")
)
```

### QA 检查

```python
from atot.qa import run_qa, QAOptions

result = run_qa(
    output_dir=Path("output/0610/episode"),
    options=QAOptions(
        policy="balanced",  # lenient / balanced / strict
        write_report=True,
        write_json=True
    )
)

# result["score"]: 0-100 分数
# result["blockers"]: 阻断器列表
# result["warnings"]: 警告列表
# result["reviews"]: 审阅建议
```

### 修复

```python
from atot.repair import run_repair, RepairOptions

result = run_repair(
    output_dir=Path("output/0610/episode"),
    options=RepairOptions(
        plan_only=True,  # 仅计划，不执行
        include_warnings=False,
        max_window_duration=300
    )
)

# result["plan"]: 修复计划
# result["repairable_count"]: 可修复窗口数
# result["blocker_count"]: 阻断器数
```

### 云端处理

```python
from atot.cloud.prepare import prepare_cloud_input
from atot.cloud.summary import generate_summary
from atot.cloud.client import CloudClient

# 准备云端输入
prepare_cloud_input(
    output_dir=Path("output/0610/episode"),
    redact_pii=True
)

# 配置客户端
client = CloudClient(
    api_base="https://api.example.com/v1",
    api_key="sk-...",
    model="gpt-5.4-mini"
)

# 生成摘要
summary = generate_summary(
    output_dir=Path("output/0610/episode"),
    client=client
)
```

---

## 测试指南

### 运行所有测试

```bash
~/Documents/SpeechToTextData/env/bin/python -m pytest
```

### 运行特定测试

```bash
# 单个文件
pytest src/tests/test_segments.py

# 单个测试
pytest src/tests/test_qa.py::test_qa_score_calculation

# 匹配模式
pytest -k "correction"
```

### 详细输出

```bash
pytest -v                    # 详细模式
pytest -s                    # 显示 print
pytest --tb=short            # 短回溯
pytest -x                    # 首次失败停止
pytest --lf                  # 仅重跑上次失败
```

### 覆盖率报告

```bash
pip install pytest-cov
pytest --cov=atot --cov-report=html
open htmlcov/index.html
```

### 编写测试

```python
# src/tests/test_my_feature.py
import pytest
from atot.my_module import my_function

def test_my_function_basic():
    result = my_function(input="test")
    assert result == "expected"

def test_my_function_edge_case():
    with pytest.raises(ValueError):
        my_function(input=None)

@pytest.fixture
def sample_audio(tmp_path):
    """创建测试音频文件"""
    audio_path = tmp_path / "test.wav"
    # 生成测试音频
    return audio_path

def test_with_fixture(sample_audio):
    result = process_audio(sample_audio)
    assert result is not None
```

---

## 调试技巧

### 1. 启用详细日志

```python
from atot.pipeline import TranscribeOptions

options = TranscribeOptions(
    input_path=Path("audio.m4a"),
    verbose=True  # 启用详细输出
)
```

### 2. 检查运行日志

```bash
cat output/<batch>/<episode>/run.log
tail -f output/<batch>/<episode>/run.log
```

### 3. 检查事件流

```bash
cat output/<batch>/<episode>/events.jsonl | jq .
```

### 4. 验证输出包

```bash
python src/scripts/validate_output_bundle.py output/<batch>/<episode>
python src/scripts/validate_run_json.py output/<batch>/<episode>/run.json
```

### 5. 使用 Python 调试器

```python
import pdb; pdb.set_trace()  # 在代码中插入断点

# 或使用 ipdb (更友好)
pip install ipdb
import ipdb; ipdb.set_trace()
```

### 6. 分析性能

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 运行代码
run_transcription(options)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(20)
```

### 7. 内存分析

```python
import tracemalloc

tracemalloc.start()

# 运行代码
run_transcription(options)

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

---

## 性能优化

### 1. 缓存复用

确保指纹一致以复用缓存：

```python
# ✓ 好: 仅修改词汇表 (复用 ASR)
options.glossary_file = Path("new_glossary.json")

# ✗ 差: 每次改模型 (重新转录)
options.model = "large-v3"  # 昂贵操作
```

### 2. 切块优化

```python
# 固定切块 (快)
options.chunking = "fixed"
options.chunk_length = 1200  # 20 分钟

# 智能切块 (质量更好但慢 10-15%)
options.chunking = "smart"
options.max_chunk_length = 1200
options.silence_threshold = -30
```

### 3. 并行处理

```python
# 云端 API 并行调用
from concurrent.futures import ThreadPoolExecutor

def process_chunk(chunk):
    return client.summarize(chunk)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_chunk, chunks))
```

### 4. 减少文件 I/O

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def read_config(path: Path) -> dict:
    return read_json(path)
```

### 5. 量化模型

使用 4bit 量化模型降低内存：

```bash
atot exec transcribe audio.m4a --model large-v3-turbo-q4
```

---

## 扩展开发

### 创建自定义 ASR 后端

```python
# src/atot/backends/my_backend.py
from pathlib import Path
from typing import Any
from .base import ASRBackend, ASRResult, ASRTranscribeOptions

class MyCustomBackend(ASRBackend):
    def __init__(self, verbose: bool = False):
        self._verbose = verbose
    
    def name(self) -> str:
        return "my-custom-backend"
    
    def supports_word_timestamps(self) -> bool:
        return True
    
    def transcribe(
        self,
        audio_path: Path,
        options: ASRTranscribeOptions
    ) -> ASRResult:
        # 1. 加载模型
        model = self._load_model(options.model)
        
        # 2. 执行转录
        output = model.transcribe(
            str(audio_path),
            language=options.language,
            prompt=options.prompt
        )
        
        # 3. 规范化输出
        segments = []
        for seg in output["segments"]:
            segments.append({
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "words": seg.get("words", []),
                "confidence": seg.get("confidence", 1.0)
            })
        
        return ASRResult(
            text=output["text"],
            segments=segments,
            language=output.get("language", options.language),
            model_source=f"custom/{options.model}"
        )
    
    def _load_model(self, model_name: str):
        # 实现模型加载逻辑
        pass

# 注册后端
from .registry import register_backend
register_backend("my-custom-backend", MyCustomBackend)
```

### 创建自定义校正规则

```python
# src/atot/data/rule_packs/podcast_terms.json
{
  "name": "podcast_terms",
  "description": "播客常用术语校正",
  "safe_global": [
    {"pattern": "麦克风", "replacement": "麦克风"},
    {"pattern": "播客", "replacement": "播客"}
  ],
  "contextual_regex": [
    {
      "pattern": "Apple 播客",
      "replacement": "Apple Podcasts",
      "trigger": "Apple"
    }
  ],
  "review_only": [
    {"pattern": "不确定词", "message": "需要人工审阅"}
  ]
}
```

使用：
```bash
atot exec transcribe audio.m4a --rule-pack podcast_terms
```

### 创建自定义验证器

```python
# src/scripts/my_validator.py
from pathlib import Path
from atot.utils import read_json

def validate_custom_requirement(output_dir: Path) -> bool:
    run_json = read_json(output_dir / "details" / "run.json")
    
    # 自定义验证逻辑
    if run_json["quality_metrics"]["qa_score"] < 80:
        print("❌ QA 分数低于 80")
        return False
    
    if run_json["runtime_metrics"]["speed_factor"] < 5:
        print("❌ 速度因子低于 5x")
        return False
    
    print("✓ 所有检查通过")
    return True

if __name__ == "__main__":
    import sys
    output_dir = Path(sys.argv[1])
    success = validate_custom_requirement(output_dir)
    sys.exit(0 if success else 1)
```

### 集成到 CI/CD

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install -e .
          python -m pip install -e ".[dev]"
      
      - name: Run linter
        run: python -m ruff check .
      
      - name: Run tests
        run: python -m pytest
      
      - name: Validate scripts
        run: |
          python src/scripts/check_public_paths.py
          python src/scripts/validate_model_inventory.py
```

---

## 故障排查速查表

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| `ModuleNotFoundError` | 环境未激活 | 使用完整路径或激活环境 |
| `FFmpeg not found` | FFmpeg 未安装 | `brew install ffmpeg` |
| `Model not found` | 模型未下载 | 查看 `atot models` |
| 转录质量差 | 模型/提示不当 | 尝试 `large-v3` 或调整提示 |
| 内存不足 | 模型过大 | 使用 4bit 量化模型 |
| 速度慢 | 切块配置 | 使用 `chunking=fixed` |
| QA 分数低 | 音频质量差 | 检查 `qa.md` 详情 |
| 缓存未复用 | 指纹变化 | 检查 `run.json` 指纹字段 |
| 云端失败 | API 配置错误 | 检查 `config.toml` |
| App 崩溃 | Python 环境问题 | 重新运行 `setup_local_app.py` |

---

## 常见开发任务

### 添加新命令

```python
# src/atot/cli.py
@exec_app.command("my-command")
def exec_my_command(
    ctx: typer.Context,
    input: Path = typer.Argument(...),
    option: str = typer.Option("default")
):
    """命令描述"""
    service = _service(ctx)
    result = service.my_operation(input, option)
    _print(result, json_output=False)
```

### 添加新配置项

```toml
# config.toml
[my_feature]
enabled = true
threshold = 0.8
```

```python
# src/atot/config_v2.py
@dataclass
class MyFeatureConfig:
    enabled: bool = True
    threshold: float = 0.8

@dataclass
class AtotConfig:
    # ... 现有配置
    my_feature: MyFeatureConfig = field(default_factory=MyFeatureConfig)
```

### 添加新验证脚本

```python
# src/scripts/validate_my_feature.py
#!/usr/bin/env python3
"""验证我的功能"""

import sys
from pathlib import Path
from atot.utils import read_json

def validate(output_dir: Path) -> tuple[bool, list[str]]:
    errors = []
    
    # 执行验证
    if not (output_dir / "my_file.json").exists():
        errors.append("缺少 my_file.json")
    
    return len(errors) == 0, errors

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: validate_my_feature.py <output_dir>")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    success, errors = validate(output_dir)
    
    if success:
        print("✓ 验证通过")
        sys.exit(0)
    else:
        print("✗ 验证失败:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
```

---

## 参考资源

- **架构文档:** `doc/ARCHITECTURE.md`
- **用户指南:** `README.md`
- **隐私说明:** `doc/PRIVACY.md`
- **质量循环:** `doc/QUALITY_LOOP.md`
- **实现与验收状态:** `doc/ROADMAP_STATUS.md`
- **示例:** `doc/examples/`
- **实验记录:** `doc/experiments/`

---

**更新时间:** 2026-06-10  
**文档版本:** 1.0
