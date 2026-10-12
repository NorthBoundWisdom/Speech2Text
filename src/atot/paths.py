from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]

DEFAULT_DATA_ROOT = Path("~/Documents/SpeechToTextData")
DATA_ROOT_ENV_VAR = "ATOT_DATA_ROOT"


@dataclass(frozen=True)
class PathContext:
    data_root: Path
    cache_dir: Path
    materials_dir: Path
    work_dir: Path
    process_dir: Path
    tools_dir: Path
    model_dir: Path
    env_dir: Path
    output_dir: Path


def data_root() -> Path:
    return path_context().data_root


def path_context(data_root: Path | str | None = None) -> PathContext:
    root_value = data_root if data_root is not None else os.environ.get(DATA_ROOT_ENV_VAR, "")
    root = Path(root_value if root_value else str(DEFAULT_DATA_ROOT))
    root = root.expanduser()
    cache = root / "cache"
    materials = root / "materials"
    work = root / "work"
    return PathContext(
        data_root=root,
        cache_dir=cache,
        materials_dir=materials,
        work_dir=work,
        # Compatibility field names for older internal call sites. New writes
        # use the unified Library plus local materials/work roots.
        process_dir=materials,
        tools_dir=cache / "tools",
        model_dir=root / "model",
        env_dir=root / "env",
        output_dir=work,
    )


_DEFAULT_CONTEXT = path_context()
DATA_ROOT = _DEFAULT_CONTEXT.data_root
CACHE_DIR = _DEFAULT_CONTEXT.cache_dir
MATERIALS_DIR = _DEFAULT_CONTEXT.materials_dir
WORK_DIR = _DEFAULT_CONTEXT.work_dir
PROCESS_DIR = _DEFAULT_CONTEXT.process_dir
TOOLS_DIR = _DEFAULT_CONTEXT.tools_dir
MODEL_DIR = _DEFAULT_CONTEXT.model_dir
ENV_DIR = _DEFAULT_CONTEXT.env_dir
DOC_DIR = PROJECT_ROOT / "doc"
PACKAGE_DATA_DIR = PACKAGE_ROOT / "data"

DEFAULT_OUTPUT_DIR = _DEFAULT_CONTEXT.output_dir
DEFAULT_TOPIC_FILE = "主题.md"
DEFAULT_PROMPT_FILE = PACKAGE_DATA_DIR / "prompt.zh.txt"
DEFAULT_GLOSSARY_FILE = PACKAGE_DATA_DIR / "glossary.zh.json"
