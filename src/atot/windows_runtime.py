from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CUDA_TOOLKIT_ROOT = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA")
CUDA13_COMPATIBILITY_NOTE = (
    "CUDA 13 is preferred when the installed CTranslate2 wheel can use it. "
    "If the error mentions CUDA 12 DLLs such as cublas64_12.dll, install a "
    "CUDA 12.x-compatible runtime for this wheel or rebuild CTranslate2 for CUDA 13."
)
CPU_OPT_IN_NOTE = "CPU execution is explicit only: set ATOT_FASTER_WHISPER_DEVICE=cpu."


@dataclass(frozen=True)
class RuntimeErrorHint:
    category: str
    action_required: str
    cuda13_note: str = CUDA13_COMPATIBILITY_NOTE
    cpu_opt_in: str = CPU_OPT_IN_NOTE

    def to_json(self) -> dict[str, str]:
        return {
            "category": self.category,
            "action_required": self.action_required,
            "cuda13_note": self.cuda13_note,
            "cpu_opt_in": self.cpu_opt_in,
        }


def is_windows() -> bool:
    return platform.system() == "Windows"


def installed_distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def classify_cuda_runtime_error(error: BaseException | str) -> RuntimeErrorHint | None:
    text = str(error)
    lowered = text.lower()
    if "cublas64_12.dll" in lowered or "cublaslt64_12.dll" in lowered:
        return RuntimeErrorHint(
            category="missing_cuda12_cublas_runtime",
            action_required=(
                "CTranslate2 could not load CUDA 12 cuBLAS DLLs. The installed wheel may "
                "still require CUDA 12.x even when CUDA 13 is installed. Install the "
                "compatible CUDA 12 runtime DLLs or rebuild CTranslate2 against CUDA 13."
            ),
        )
    if re.search(r"cublas(?:lt)?64_\d+\.dll", lowered) or "cublas" in lowered:
        return RuntimeErrorHint(
            category="missing_cublas_runtime",
            action_required=(
                "CTranslate2 could not load cuBLAS. Ensure the CUDA runtime DLLs required "
                "by the installed CTranslate2 wheel are installed and visible on PATH."
            ),
        )
    if "cudnn" in lowered:
        return RuntimeErrorHint(
            category="missing_cudnn_runtime",
            action_required=(
                "CTranslate2 could not load cuDNN. Install cuDNN for the CUDA runtime used "
                "by the installed CTranslate2 wheel and ensure its bin directory is on PATH."
            ),
        )
    if "cuda" in lowered and ("no gpu" in lowered or "no cuda" in lowered or "device" in lowered):
        return RuntimeErrorHint(
            category="cuda_device_unavailable",
            action_required=(
                "No usable CUDA device was reported to CTranslate2. Check the NVIDIA driver, "
                "GPU visibility, and CUDA runtime installation."
            ),
        )
    if "cuda" in lowered or "dll" in lowered:
        return RuntimeErrorHint(
            category="cuda_runtime_error",
            action_required=(
                "The CUDA runtime failed while loading faster-whisper/CTranslate2. Check the "
                "installed CUDA/cuDNN DLLs and the CTranslate2 wheel compatibility."
            ),
        )
    return None


def enhance_cuda_error(message: str, error: BaseException | str) -> str:
    hint = classify_cuda_runtime_error(error)
    if hint is None:
        return message
    return (
        f"{message}\n"
        f"Runtime category: {hint.category}.\n"
        f"Action required: {hint.action_required}\n"
        f"{hint.cuda13_note}\n"
        f"{hint.cpu_opt_in}"
    )


def windows_runtime_payload(*, load_model_probe: Any | None = None) -> dict[str, Any]:
    """Return Windows-focused runtime diagnostics.

    The optional load_model_probe hook is intentionally tiny so tests can cover
    model-load failures without importing faster-whisper or requiring a GPU.
    """

    cpu_explicit = os.environ.get("ATOT_FASTER_WHISPER_DEVICE", "").lower() == "cpu"
    payload: dict[str, Any] = {
        "is_windows": is_windows(),
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "cuda_detected_versions": [],
        "preferred_cuda_version": None,
        "cuda_toolkits": [],
        "cuda_path": os.environ.get("CUDA_PATH"),
        "cuda_path_entries": _path_entries_with_cuda(),
        "dlls": {},
        "packages": {
            "faster-whisper": installed_distribution_version("faster-whisper"),
            "ctranslate2": installed_distribution_version("ctranslate2"),
        },
        "ctranslate2_cuda_probe": _ctranslate2_cuda_probe(),
        "faster_whisper_model_probe": None,
        "action_required": [],
        "notes": [],
    }
    toolkits = _cuda_toolkits()
    payload["cuda_toolkits"] = [str(path) for path in toolkits]
    payload["cuda_detected_versions"] = [_cuda_version_from_path(path) for path in toolkits]
    payload["cuda_detected_versions"] = [item for item in payload["cuda_detected_versions"] if item]
    payload["preferred_cuda_version"] = _preferred_cuda_version(payload["cuda_detected_versions"])
    payload["dlls"] = _dll_payload(toolkits)

    probe = payload["ctranslate2_cuda_probe"]
    if isinstance(probe, dict) and not cpu_explicit:
        if probe.get("success") is False:
            payload["action_required"].append(
                str(probe.get("action_required") or "CTranslate2 CUDA probe failed.")
            )
        elif probe.get("cuda_device_count") == 0:
            payload["action_required"].append("CTranslate2 reports zero CUDA devices.")

    if load_model_probe is not None:
        payload["faster_whisper_model_probe"] = _run_load_model_probe(load_model_probe)
        model_probe = payload["faster_whisper_model_probe"]
        if isinstance(model_probe, dict) and model_probe.get("success") is False:
            payload["action_required"].append(
                str(model_probe.get("action_required") or "faster-whisper model load failed.")
            )

    if payload["preferred_cuda_version"] and str(payload["preferred_cuda_version"]).startswith(
        "13"
    ):
        payload["notes"].append(CUDA13_COMPATIBILITY_NOTE)
    if cpu_explicit:
        payload["notes"].append(
            "ATOT_FASTER_WHISPER_DEVICE=cpu is set; CUDA is not required for this run."
        )
    else:
        payload["notes"].append(CPU_OPT_IN_NOTE)
    return payload


def add_windows_gpu_dll_directories() -> list[str]:
    """Register likely CUDA/cuDNN DLL directories for this Python process."""

    if not hasattr(os, "add_dll_directory"):
        return []
    directories: list[Path] = []
    for toolkit in _cuda_toolkits():
        directories.extend([toolkit / "bin" / "x64", toolkit / "bin"])
    directories.extend(_cudnn_bin_dirs())
    added: list[str] = []
    seen: set[str] = set()
    for directory in directories:
        normalized = str(directory).lower()
        if normalized in seen or not directory.is_dir():
            continue
        seen.add(normalized)
        os.add_dll_directory(str(directory))
        added.append(str(directory))
    return added


def _run_load_model_probe(load_model_probe: Any) -> dict[str, Any]:
    try:
        result = load_model_probe()
    except Exception as exc:  # pragma: no cover - depends on local runtime.
        hint = classify_cuda_runtime_error(exc)
        return {
            "success": False,
            "error": str(exc),
            "category": hint.category if hint else "model_load_error",
            "action_required": hint.action_required
            if hint
            else "faster-whisper could not load the default model.",
        }
    if isinstance(result, dict):
        return result
    return {"success": bool(result)}


def _ctranslate2_cuda_probe() -> dict[str, Any]:
    if importlib.util.find_spec("ctranslate2") is None:
        return {
            "success": False,
            "importable": False,
            "cuda_device_count": None,
            "action_required": "Install ctranslate2 through the Windows Python environment.",
        }
    try:
        import ctranslate2

        getter = getattr(ctranslate2, "get_cuda_device_count", None)
        count = int(getter()) if callable(getter) else None
        return {"success": True, "importable": True, "cuda_device_count": count}
    except Exception as exc:  # pragma: no cover - depends on local runtime.
        hint = classify_cuda_runtime_error(exc)
        return {
            "success": False,
            "importable": True,
            "cuda_device_count": None,
            "error": str(exc),
            "category": hint.category if hint else "ctranslate2_cuda_probe_error",
            "action_required": hint.action_required if hint else "CTranslate2 CUDA probe failed.",
        }


def _cuda_toolkits() -> list[Path]:
    roots: list[Path] = []
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        roots.append(Path(cuda_path))
    for key, value in os.environ.items():
        if key.startswith("CUDA_PATH_V") and value:
            roots.append(Path(value))
    if CUDA_TOOLKIT_ROOT.exists():
        roots.extend(
            path
            for path in CUDA_TOOLKIT_ROOT.iterdir()
            if path.is_dir() and path.name.lower().startswith("v")
        )
    seen: set[str] = set()
    unique: list[Path] = []
    for path in roots:
        normalized = str(path).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(path)
    return sorted(
        unique, key=lambda path: _version_tuple(_cuda_version_from_path(path)), reverse=True
    )


def _path_entries_with_cuda() -> list[str]:
    entries = []
    for item in os.environ.get("PATH", "").split(os.pathsep):
        if item and ("cuda" in item.lower() or "nvidia" in item.lower()):
            entries.append(item)
    return entries


def _cuda_version_from_path(path: Path) -> str | None:
    match = re.search(r"v?(\d+(?:\.\d+)*)$", path.name)
    return match.group(1) if match else None


def _preferred_cuda_version(versions: list[str]) -> str | None:
    if not versions:
        return None
    cuda13 = [version for version in versions if version.startswith("13")]
    candidates = cuda13 or versions
    return sorted(candidates, key=_version_tuple, reverse=True)[0]


def _version_tuple(version: str | None) -> tuple[int, ...]:
    if not version:
        return ()
    return tuple(int(part) for part in re.findall(r"\d+", version))


def _dll_payload(toolkits: list[Path]) -> dict[str, Any]:
    search_dirs = []
    for path in toolkits:
        search_dirs.extend([path / "bin" / "x64", path / "bin"])
    search_dirs.extend(_cudnn_bin_dirs())
    for item in os.environ.get("PATH", "").split(os.pathsep):
        if item:
            search_dirs.append(Path(item))
    required = [
        "cudart64_13.dll",
        "cublas64_13.dll",
        "cublasLt64_13.dll",
        "cublas64_12.dll",
        "cublasLt64_12.dll",
        "cudnn64_9.dll",
    ]
    result: dict[str, Any] = {}
    for name in required:
        matches = []
        seen: set[str] = set()
        for directory in search_dirs:
            candidate = directory / name
            normalized = str(candidate).lower()
            if candidate.exists() and normalized not in seen:
                seen.add(normalized)
                matches.append(str(candidate))
        result[name] = {"found": bool(matches), "paths": matches}
    return result


def _cudnn_bin_dirs() -> list[Path]:
    roots = [
        Path("C:/Program Files/NVIDIA/CUDNN"),
        Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA"),
    ]
    directories: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("cudnn64_9.dll"):
            directories.append(candidate.parent)
    return directories
