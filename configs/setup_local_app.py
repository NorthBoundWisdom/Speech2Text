#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from configs.generate_xcodeproj import generate_xcodeproj  # noqa: E402

DEFAULT_DATA_ROOT = Path("~/Documents/SpeechToTextData")
SWIFTPM_BUILD_DIR = REPO_ROOT / "build" / "swiftpm"
RUNTIME_CONSTRAINTS = REPO_ROOT / "constraints" / "runtime.txt"


def data_root() -> Path:
    return DEFAULT_DATA_ROOT.expanduser()


def _python_launcher() -> str:
    if os.name == "nt":
        return sys.executable
    return shutil.which("python3.13") or shutil.which("python3") or sys.executable


def _venv_bin_dir(env_dir: Path) -> Path:
    return env_dir / ("Scripts" if os.name == "nt" else "bin")


def _venv_executable(env_dir: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return _venv_bin_dir(env_dir) / f"{name}{suffix}"


def _default_asr_backend() -> str:
    return "faster-whisper" if os.name == "nt" else "mlx-whisper"


def _default_model_dir(root: Path) -> Path:
    name = "faster-whisper-large-v3-turbo" if os.name == "nt" else "whisper-large-v3-turbo"
    return root / "model" / name


def _ensure_data_dirs(root: Path) -> None:
    for name in ("model", "env", "cache", "output"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for name in ("logs", "pytest", "ruff", "tools"):
        (root / "cache" / name).mkdir(parents=True, exist_ok=True)
    _repair_tool_links(root / "cache" / "tools")


def _repair_tool_links(tools: Path) -> None:
    bin_dir = tools / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = bin_dir / "ffmpeg"
    if ffmpeg.exists():
        return
    for candidate in sorted(
        tools.glob("*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg*")
    ):
        if candidate.is_file():
            try:
                ffmpeg.unlink(missing_ok=True)
                ffmpeg.symlink_to(candidate)
            except OSError:
                pass
            return


def _command_ok(cmd: list[str], *, cwd: Path = REPO_ROOT) -> bool:
    try:
        completed = subprocess.run(
            cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
    except OSError:
        return False
    return completed.returncode == 0


def _swift_env() -> dict[str, str]:
    module_cache = SWIFTPM_BUILD_DIR / "module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    return {**os.environ, "CLANG_MODULE_CACHE_PATH": str(module_cache)}


def _atot_imports_from_source(python: Path) -> bool:
    code = (
        "from pathlib import Path\n"
        "import atot\n"
        f"expected = Path({str(REPO_ROOT / 'src' / 'atot').__repr__()}).resolve()\n"
        "actual = Path(atot.__file__).resolve().parent\n"
        "raise SystemExit(0 if actual == expected else 1)\n"
    )
    return _command_ok([str(python), "-c", code])


def _environment_meets_runtime_constraints(python: Path) -> bool:
    return all(
        _command_ok([str(python), "-c", _pep440_minimum_check_code(distribution, minimum)])
        for distribution, minimum in (("msgpack", "1.2.1"), ("mcp", "2.3"), ("filelock", "3.13"), ("keyring", "25.0"))
    )


def _pep440_minimum_check_code(
    distribution: str, minimum: str, *, installed_version: str | None = None
) -> str:
    installed_expression = (
        repr(installed_version)
        if installed_version is not None
        else f"version({distribution!r})"
    )
    return (
        "from importlib.metadata import version\n"
        "from packaging.version import Version\n"
        f"raise SystemExit(0 if Version({installed_expression}) >= Version({minimum!r}) else 1)\n"
    )


def _ensure_env(root: Path) -> int:
    env_dir = root / "env"
    python = _venv_executable(env_dir, "python")
    atot = _venv_executable(env_dir, "atot")
    app_cli = _venv_executable(env_dir, "Audio2TextCli")
    created_env = False
    if not python.exists():
        subprocess.run([_python_launcher(), "-m", "venv", str(env_dir)], cwd=REPO_ROOT, check=True)
        created_env = True
    if created_env:
        subprocess.run(
            [str(python), "-m", "pip", "install", "-U", "pip"], cwd=REPO_ROOT, check=True
        )
    needs_install = (
        not _atot_imports_from_source(python)
        or not _command_ok([str(python), "-m", "atot.cli", "--help"])
        or not atot.exists()
        or not app_cli.exists()
        or not _environment_meets_runtime_constraints(python)
    )
    if needs_install:
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--constraint",
                str(RUNTIME_CONSTRAINTS),
                "-e",
                ".[dev]",
            ],
            cwd=REPO_ROOT,
            check=True,
        )
    return 0


def main() -> int:
    root = data_root()
    _ensure_data_dirs(root)
    try:
        _ensure_env(root)
    except subprocess.CalledProcessError as error:
        print(f"Could not prepare Python env: {error}", file=sys.stderr)
        return error.returncode or 1

    required = [
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "src" / "atot",
        REPO_ROOT / "src" / "atot" / "data" / "model_inventory.json",
    ]
    if os.name != "nt":
        required.append(REPO_ROOT / "app" / "Package.swift")
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    if missing:
        print("Missing required project inputs:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1

    try:
        inventory = json.loads(
            (REPO_ROOT / "src" / "atot" / "data" / "model_inventory.json").read_text()
        )
    except json.JSONDecodeError as error:
        print(f"Invalid model inventory: {error}", file=sys.stderr)
        return 1
    if not inventory.get("models"):
        print("Model inventory contains no models.", file=sys.stderr)
        return 1

    project = None
    if os.name != "nt":
        completed = subprocess.run(
            [
                "swift",
                "package",
                "--disable-sandbox",
                "dump-package",
                "--scratch-path",
                str(SWIFTPM_BUILD_DIR),
            ],
            cwd=REPO_ROOT / "app",
            env=_swift_env(),
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
        project = generate_xcodeproj()

    print("local CLI config is ready" if os.name == "nt" else "local app config is ready")
    print(f"Platform: {platform.system()}")
    print(f"Data root: {root}")
    print(f"Python env: {root / 'env'} (local atot lives in {_venv_bin_dir(root / 'env')})")
    print(f"Cache root: {root / 'cache'}")
    print(f"Local library root: {root / 'Audio2TextLibrary'}")
    print(f"Materials root: {root / 'materials'}")
    print(f"Work root: {root / 'work'}")
    if project is not None:
        print("Swift package: app/Package.swift")
        print(f"Xcode project: {project.relative_to(REPO_ROOT)}")
    print(f"Default ASR backend: {_default_asr_backend()}")
    print(f"Default ASR model: {_default_model_dir(root)}")
    if os.name == "nt":
        print(f"Run doctor: {_venv_executable(root / 'env', 'atot')} doctor")
        print(
            f"Run CLI: {_venv_executable(root / 'env', 'atot')} exec transcribe path\\to\\audio.m4a"
        )
    else:
        print(f"Run doctor: {_venv_executable(root / 'env', 'atot')} doctor")
        print(
            "Build app: python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
