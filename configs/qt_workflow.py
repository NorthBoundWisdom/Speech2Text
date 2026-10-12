#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
FREECM_ROOT = REPO_ROOT / "FreeCM"
if FREECM_ROOT.exists() and str(FREECM_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECM_ROOT))

from configs.release_licenses import stage_release_licenses  # noqa: E402

QT_PROJECT_DIR = REPO_ROOT / "qt" / "Audio2TextQt"
DEFAULT_BUILD_DIR = REPO_ROOT / "build" / "Audio2TextQt"
DEFAULT_PACKAGE_DIR = REPO_ROOT / "build" / "package"
DEFAULT_PACKAGE_STAGING_DIR = REPO_ROOT / "build" / "package-staging"
DEFAULT_PYTHON_RUNTIME_SOURCE = Path(sys.base_prefix)
TARGET_NAME = "Audio2TextQt"
PRODUCT_NAME = "SonaFolioQt"
PACKAGE_PLATFORM = "Windows"
SOURCE_ROOTS_LOCK_NAMES = ("source_roots.lock.jsonc", "source_roots.lock.jsonc.in")
PACKAGE_IGNORE_PATTERNS = (
    "*.exp",
    "*.ilk",
    "*.lastbuildstate",
    "*.lib",
    "*.obj",
    "*.pdb",
    "*.tlog",
)
PYTHON_RUNTIME_IGNORE_PATTERNS = (
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "Doc",
    "include",
    "Lib/site-packages",
    "Lib/test",
    "Lib/tkinter",
    "libs",
    "Scripts",
    "tcl",
)
FFMPEG_TOOL_NAMES = ("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe")
MSVC_RUNTIME_DLL_NAMES = (
    "concrt140.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "vcomp140.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
)


def _display_command(cmd: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(cmd)
    return " ".join(cmd)


def _qt_deploy_tool_name() -> str:
    if os.name == "nt":
        return "windeployqt.exe"
    if sys.platform == "darwin":
        return "macdeployqt"
    return "linuxdeployqt"


def _qt_qmake_names() -> tuple[str, ...]:
    return ("qmake.exe",) if os.name == "nt" else ("qmake6", "qmake")


def _source_roots_platform_key() -> str:
    if os.name == "nt":
        return "win"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def _run(
    cmd: list[str | Path], *, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None
) -> None:
    argv = [str(part) for part in cmd]
    print(f"$ {_display_command(argv)}", flush=True)
    completed = subprocess.run(argv, cwd=cwd, env=env, text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def _repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _cache_value(build_dir: Path, key: str) -> str | None:
    cache = build_dir / "CMakeCache.txt"
    if not cache.exists():
        return None
    prefix = f"{key}:"
    plain = f"{key}="
    for line in cache.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(("//", "#")):
            continue
        if line.startswith(prefix) or line.startswith(plain):
            return line.split("=", 1)[1].strip()
    return None


def _split_prefix_path(value: str | None) -> list[str]:
    if not value:
        return []
    separators = [os.pathsep]
    if ";" not in separators:
        separators.append(";")
    pattern = "|".join(re.escape(separator) for separator in separators)
    return [part.strip() for part in re.split(pattern, value) if part.strip()]


def _load_source_roots_lock(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        from freecm.jsonc import loads_jsonc  # type: ignore[import-not-found]

        payload = loads_jsonc(path.read_text(encoding="utf-8"), path_label=str(path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"SonaFolio Qt: invalid JSON in {path}: {exc}") from exc
    except ModuleNotFoundError:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"SonaFolio Qt: invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        return {}
    return payload


def _source_roots_lock_values(section: str, key: str) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    platform = _source_roots_platform_key()
    for name in SOURCE_ROOTS_LOCK_NAMES:
        path = REPO_ROOT / name
        data = _load_source_roots_lock(path)
        if not data:
            continue
        section_value = data.get(section)
        if not isinstance(section_value, dict):
            continue
        common_value = section_value.get(key)
        if isinstance(common_value, str):
            values.append((f"{name} {section}.{key}", common_value))
        platform_value = section_value.get(platform)
        if isinstance(platform_value, dict):
            nested_value = platform_value.get(key)
            if isinstance(nested_value, str):
                values.append((f"{name} {section}.{platform}.{key}", nested_value))
    return values


def _source_roots_terminal_path_entries() -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    platform = _source_roots_platform_key()
    for name in SOURCE_ROOTS_LOCK_NAMES:
        path = REPO_ROOT / name
        data = _load_source_roots_lock(path)
        if not data:
            continue
        terminal_path = data.get("terminalPath")
        if not isinstance(terminal_path, dict):
            continue
        for key in ("common", platform):
            entries = terminal_path.get(key)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, str) and entry.strip():
                    values.append((f"{name} terminalPath.{key}", entry))
    return values


def _tool_prefix(tool_name: str) -> Path | None:
    found = shutil.which(tool_name)
    if not found:
        return None
    tool = Path(found).resolve()
    if tool.parent.name.lower() == "bin":
        return tool.parent.parent
    return None


def _normalize_qt_prefix(path: Path) -> Path:
    if path.is_file() and path.name.lower() == "qt6config.cmake":
        path = path.parent
    if (
        path.name.lower() == "qt6"
        and path.parent.name.lower() == "cmake"
        and path.parent.parent.name.lower() == "lib"
    ):
        return path.parent.parent.parent
    if path.name.lower() == "bin":
        return path.parent
    return path


def _looks_like_qt_prefix(path: Path) -> bool:
    config = path / "lib" / "cmake" / "Qt6" / "Qt6Config.cmake"
    deploy_tool = path / "bin" / _qt_deploy_tool_name()
    qmake_tools = [path / "bin" / name for name in _qt_qmake_names()]
    return config.exists() and (deploy_tool.exists() or any(tool.exists() for tool in qmake_tools))


def _candidate_qt_prefixes(explicit: str | None, build_dir: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []

    def add(source: str, value: str | Path | None) -> None:
        if value is None:
            return
        text = str(value).strip().strip('"')
        if not text:
            return
        candidates.append(
            (source, _normalize_qt_prefix(Path(os.path.expandvars(os.path.expanduser(text)))))
        )

    add("--qt-prefix", explicit)
    add("AUDIO2TEXTQT_QT_PREFIX", os.environ.get("AUDIO2TEXTQT_QT_PREFIX"))
    add("Qt6_DIR", os.environ.get("Qt6_DIR"))
    for entry in _split_prefix_path(os.environ.get("CMAKE_PREFIX_PATH")):
        add("CMAKE_PREFIX_PATH", entry)
    add("QT_DIR", os.environ.get("QT_DIR"))
    add("QTDIR", os.environ.get("QTDIR"))
    add("Qt6_ROOT", os.environ.get("Qt6_ROOT"))
    for source, value in _source_roots_lock_values("cmakeEnvironment", "CMAKE_PREFIX_PATH"):
        for entry in _split_prefix_path(value):
            add(source, entry)
    for source, value in _source_roots_lock_values("cmakeCacheVariables", "CMAKE_PREFIX_PATH"):
        for entry in _split_prefix_path(value):
            add(source, entry)
    for source, value in _source_roots_terminal_path_entries():
        add(source, value)
    add("CMakeCache Qt6_DIR", _cache_value(build_dir, "Qt6_DIR"))
    for entry in _split_prefix_path(_cache_value(build_dir, "CMAKE_PREFIX_PATH")):
        add("CMakeCache CMAKE_PREFIX_PATH", entry)
    deploy_tool = _qt_deploy_tool_name()
    add(f"PATH {deploy_tool}", _tool_prefix(deploy_tool))
    for qmake_name in _qt_qmake_names():
        add(f"PATH {qmake_name}", _tool_prefix(qmake_name))
    return candidates


def _find_qt_prefix(explicit: str | None, build_dir: Path) -> Path | None:
    seen: set[str] = set()
    for source, prefix in _candidate_qt_prefixes(explicit, build_dir):
        key = str(prefix).lower()
        if key in seen:
            continue
        seen.add(key)
        if _looks_like_qt_prefix(prefix):
            print(f"SonaFolio Qt: using Qt prefix from {source}: {prefix}", flush=True)
            return prefix
        if explicit and source == "--qt-prefix":
            raise SystemExit(
                f"SonaFolio Qt: --qt-prefix does not look like a Qt 6 prefix: {prefix}"
            )
    return None


def _find_qt_deploy_tool(explicit: str | None, build_dir: Path) -> Path:
    tool_name = _qt_deploy_tool_name()
    searched: list[Path] = []
    seen: set[str] = set()
    for source, prefix in _candidate_qt_prefixes(explicit, build_dir):
        candidate = prefix / "bin" / tool_name
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        searched.append(candidate)
        if candidate.is_file():
            print(f"SonaFolio Qt: using {tool_name} from {source}: {candidate}", flush=True)
            return candidate
    found = shutil.which(tool_name)
    if found:
        return Path(found).resolve()
    locations = "\n  ".join(str(path) for path in searched) or "<none>"
    raise SystemExit(
        f"SonaFolio Qt: {tool_name} was not found for packaging. "
        "Set --qt-prefix, AUDIO2TEXTQT_QT_PREFIX, CMAKE_PREFIX_PATH, or source_roots terminalPath.\n"
        f"Searched:\n  {locations}"
    )


def _configure(args: argparse.Namespace, build_dir: Path) -> None:
    # --config only selects a configuration for multi-config generators. Ninja
    # and Makefiles need the build type at configure time to enable optimization.
    command: list[str | Path] = [
        "cmake",
        "-S",
        QT_PROJECT_DIR,
        "-B",
        build_dir,
        f"-DCMAKE_BUILD_TYPE={args.configuration}",
    ]
    if args.generator:
        command.extend(["-G", args.generator])
    qt_prefix = _find_qt_prefix(args.qt_prefix, build_dir)
    if qt_prefix is not None:
        # Cached module directories take precedence over a new prefix. Refresh
        # Qt package discovery so an existing build can switch SDK versions.
        command.extend(
            [
                "-UQt6*_DIR",
                "-UQT_FEATURE_*",
                f"-DCMAKE_PREFIX_PATH={qt_prefix}",
            ]
        )
    else:
        print(
            "SonaFolio Qt: Qt prefix was not auto-detected; relying on CMake search paths. "
            "Set AUDIO2TEXTQT_QT_PREFIX or CMAKE_PREFIX_PATH if configure fails.",
            file=sys.stderr,
            flush=True,
        )
    _run(command)


def _build(args: argparse.Namespace, build_dir: Path, *, configure_if_missing: bool) -> None:
    if configure_if_missing or not (build_dir / "CMakeCache.txt").exists():
        _configure(args, build_dir)
    _run(["cmake", "--build", build_dir, "--config", args.configuration, "--target", TARGET_NAME])


def _executable_candidates(build_dir: Path, configuration: str) -> list[Path]:
    suffix = ".exe" if os.name == "nt" else ""
    executable = f"{PRODUCT_NAME}{suffix}"
    candidates: list[Path] = []
    if sys.platform == "darwin":
        bundle_executable = Path(f"{PRODUCT_NAME}.app") / "Contents" / "MacOS" / PRODUCT_NAME
        candidates.extend(
            [
                build_dir / configuration / bundle_executable,
                build_dir / bundle_executable,
            ]
        )
    candidates.extend(
        [
            build_dir / configuration / executable,
            build_dir / executable,
        ]
    )
    return candidates


def _find_executable(build_dir: Path, configuration: str) -> Path:
    for candidate in _executable_candidates(build_dir, configuration):
        if candidate.exists():
            return candidate
    expected = "\n  ".join(str(path) for path in _executable_candidates(build_dir, configuration))
    raise SystemExit(f"SonaFolio Qt: executable was not found. Expected one of:\n  {expected}")


def _candidate_ffmpeg_dirs(explicit: str | None) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []

    def add(source: str, value: str | Path | None) -> None:
        if value is None:
            return
        text = str(value).strip().strip('"')
        if not text:
            return
        candidates.append((source, Path(os.path.expandvars(os.path.expanduser(text)))))

    add("--ffmpeg-dir", explicit)
    add("AUDIO2TEXTQT_FFMPEG_DIR", os.environ.get("AUDIO2TEXTQT_FFMPEG_DIR"))
    add("FFMPEG_DIR", os.environ.get("FFMPEG_DIR"))
    vcpkg_root = os.environ.get("VCPKG_ROOT")
    if vcpkg_root:
        installed = Path(os.path.expandvars(os.path.expanduser(vcpkg_root))) / "installed"
        if installed.exists():
            for triplet in sorted(path for path in installed.iterdir() if path.is_dir()):
                add("VCPKG_ROOT", triplet / "tools" / "ffmpeg")

    for source, value in (
        *_source_roots_lock_values("cmakeEnvironment", "CMAKE_PREFIX_PATH"),
        *_source_roots_lock_values("cmakeCacheVariables", "CMAKE_PREFIX_PATH"),
    ):
        for entry in _split_prefix_path(value):
            prefix = Path(os.path.expandvars(os.path.expanduser(entry)))
            add(source, prefix / "tools" / "ffmpeg")
            add(source, prefix / "bin")
    for source, value in _source_roots_terminal_path_entries():
        add(source, value)

    for tool_name in FFMPEG_TOOL_NAMES:
        found = shutil.which(tool_name)
        if found:
            add(f"PATH {tool_name}", Path(found).parent)
    return candidates


def _find_ffmpeg_tool(tool_name: str, explicit_dir: str | None) -> Path:
    searched: list[Path] = []
    for source, directory in _candidate_ffmpeg_dirs(explicit_dir):
        candidate = directory / tool_name
        searched.append(candidate)
        if candidate.is_file():
            print(f"SonaFolio Qt: using {tool_name} from {source}: {candidate}", flush=True)
            return candidate
    locations = "\n  ".join(str(path) for path in searched) or "<none>"
    raise SystemExit(
        f"SonaFolio Qt: {tool_name} was not found for packaging. "
        "Set --ffmpeg-dir or AUDIO2TEXTQT_FFMPEG_DIR to a directory containing "
        f"{' and '.join(FFMPEG_TOOL_NAMES)}.\nSearched:\n  {locations}"
    )


def _copy_ffmpeg_tools(staging_dir: Path, explicit_dir: str | None) -> None:
    tool_dirs: set[Path] = set()
    for tool_name in FFMPEG_TOOL_NAMES:
        source = _find_ffmpeg_tool(tool_name, explicit_dir)
        tool_dirs.add(source.parent)
        build_info = subprocess.run([str(source), "-version"], check=True, capture_output=True, text=True).stdout
        license_info = subprocess.run([str(source), "-L"], check=True, capture_output=True, text=True).stdout
        if "--enable-nonfree" in build_info:
            raise ValueError("FFmpeg --enable-nonfree builds cannot be redistributed.")
        # Keep version/license output for reviewers; no machine-specific configure paths.
        public_config = " ".join(flag for flag in build_info.split() if flag.startswith("--enable-") or flag.startswith("--disable-"))
        (staging_dir / f"{tool_name}.build.txt").write_text(build_info.splitlines()[0] + "\n" + public_config + "\n" + license_info, encoding="utf-8")
        shutil.copy2(source, staging_dir / tool_name)
    for tool_dir in sorted(tool_dirs):
        for dll in sorted(tool_dir.glob("*.dll")):
            shutil.copy2(dll, staging_dir / dll.name)


def _version_key(path: Path) -> tuple[int, ...]:
    for part in reversed(path.parts):
        if re.fullmatch(r"\d+(?:\.\d+)+", part):
            return tuple(int(value) for value in part.split("."))
    return ()


def _candidate_msvc_runtime_dirs(explicit: str | None) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []

    def add(source: str, value: str | Path | None) -> None:
        if value is None:
            return
        text = str(value).strip().strip('"')
        if not text:
            return
        candidates.append((source, Path(os.path.expandvars(os.path.expanduser(text)))))

    add("--msvc-runtime-dir", explicit)
    if candidates:
        return _expand_msvc_runtime_dirs(candidates)
    add("AUDIO2TEXTQT_MSVC_RUNTIME_DIR", os.environ.get("AUDIO2TEXTQT_MSVC_RUNTIME_DIR"))

    redist_root = os.environ.get("VCToolsRedistDir")
    if redist_root:
        add("VCToolsRedistDir", Path(redist_root) / "x64" / "Microsoft.VC143.CRT")
        add("VCToolsRedistDir", Path(redist_root) / "x64" / "Microsoft.VC145.CRT")

    vc_install = os.environ.get("VCINSTALLDIR")
    if vc_install:
        add("VCINSTALLDIR", Path(vc_install) / "Redist" / "MSVC")

    program_files = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
    for root in program_files:
        if not root:
            continue
        vs_root = Path(root) / "Microsoft Visual Studio"
        if not vs_root.is_dir():
            continue
        for redist in sorted(vs_root.glob("*/*/VC/Redist/MSVC"), key=_version_key, reverse=True):
            add("Visual Studio Redist", redist)

    return _expand_msvc_runtime_dirs(candidates)


def _expand_msvc_runtime_dirs(candidates: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    expanded: list[tuple[str, Path]] = []
    for source, directory in candidates:
        expanded.append((source, directory))
        if not directory.is_dir():
            continue
        for candidate in sorted(
            directory.glob("*/x64/Microsoft.VC*.CRT"),
            key=_version_key,
            reverse=True,
        ):
            expanded.append((source, candidate))
        for candidate in sorted(
            directory.glob("x64/Microsoft.VC*.CRT"),
            key=_version_key,
            reverse=True,
        ):
            expanded.append((source, candidate))
    return expanded


def _copy_msvc_runtime(staging_dir: Path, explicit_dir: str | None) -> None:
    copied: list[Path] = []
    searched: list[Path] = []
    for source, directory in _candidate_msvc_runtime_dirs(explicit_dir):
        if not directory.is_dir():
            searched.append(directory)
            continue
        available = {path.name.lower(): path for path in directory.glob("*.dll")}
        if not {"msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"}.issubset(available):
            searched.append(directory)
            continue
        for dll_name in MSVC_RUNTIME_DLL_NAMES:
            dll = available.get(dll_name)
            if dll is not None:
                target = staging_dir / dll.name
                shutil.copy2(dll, target)
                copied.append(target)
        names = ", ".join(sorted(path.name for path in copied))
        print(f"SonaFolio Qt: copied MSVC runtime from {source}: {directory} ({names})", flush=True)
        return
    locations = "\n  ".join(str(path) for path in searched) or "<none>"
    raise SystemExit(
        "SonaFolio Qt: MSVC runtime DLLs were not found for packaging. "
        "Set --msvc-runtime-dir or AUDIO2TEXTQT_MSVC_RUNTIME_DIR to a Microsoft.VC*.CRT directory.\n"
        f"Searched:\n  {locations}"
    )


def _qt_project_version() -> str:
    cmake_lists = QT_PROJECT_DIR / "CMakeLists.txt"
    content = cmake_lists.read_text(encoding="utf-8")
    match = re.search(
        rf"project\s*\(\s*{re.escape(TARGET_NAME)}\b[^)]*?\bVERSION\s+([^\s)]+)",
        content, flags=re.DOTALL,
    )
    if match is not None and match[1] == "${AUDIO2TEXTQT_RELEASE_VERSION}":
        match = re.search(r'set\(AUDIO2TEXTQT_RELEASE_VERSION "([0-9.]+)"', content)
    if match is None or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", match[1]):
        raise SystemExit(f"SonaFolio Qt: project version was not found in {cmake_lists}")
    return match[1]


def _package_archive_path(
    package_dir: Path,
    version: str,
    *,
    include_python_runtime: bool = False,
    platform: str = PACKAGE_PLATFORM,
) -> Path:
    suffix = "_Runtime" if include_python_runtime else ""
    return package_dir / f"{PRODUCT_NAME}_v{version}_{platform}{suffix}.zip"


def _reset_child_directory(path: Path, parent: Path) -> None:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved == resolved_parent or resolved.parent != resolved_parent:
        raise SystemExit(f"SonaFolio Qt: refusing to reset unsafe staging directory: {path}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _stage_runtime(runtime_dir: Path, staging_dir: Path) -> None:
    if not runtime_dir.is_dir():
        raise SystemExit(f"SonaFolio Qt: runtime directory was not found: {runtime_dir}")
    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    _reset_child_directory(staging_dir, staging_dir.parent)
    shutil.copytree(
        runtime_dir,
        staging_dir,
        ignore=shutil.ignore_patterns(*PACKAGE_IGNORE_PATTERNS),
    )


def _python_runtime_ignore(directory: str, names: list[str]) -> set[str]:
    rel = Path(directory).resolve()
    ignored: set[str] = set()
    for name in names:
        child = rel / name
        normalized = child.as_posix().lower()
        for pattern in PYTHON_RUNTIME_IGNORE_PATTERNS:
            if "/" in pattern:
                if normalized.endswith(pattern.lower()):
                    ignored.add(name)
            elif child.match(pattern):
                ignored.add(name)
    return ignored


def _stage_python_runtime(staging_dir: Path, source_dir: str | None) -> None:
    source = Path(source_dir or DEFAULT_PYTHON_RUNTIME_SOURCE).resolve()
    python = source / "python.exe"
    if not python.is_file():
        raise SystemExit(
            f"SonaFolio Qt: Python runtime source does not contain python.exe: {source}"
        )
    unexpected = [child.name for child in source.iterdir()
                  if child.name.lower() not in {"lib", "dlls", "libs", "include", "scripts", "doc", "tcl", "tools", "__pycache__"}
                  and child.name.lower() not in {"python.exe", "pythonw.exe", "license.txt"}
                  and not re.fullmatch(r"python(?:3|\d{2,3})(?:_d)?\.(?:dll|zip|_pth)", child.name.lower())
                  and not re.fullmatch(r"(?:vcruntime|msvcp)\d+(?:_\d+)?\.dll", child.name.lower())]
    if unexpected:
        raise SystemExit("Use a clean Python distribution; unexpected runtime root files: " + ", ".join(unexpected))
    if any(path.is_symlink() for path in source.rglob("*")):
        raise SystemExit("Python runtime source must not contain symlinks.")
    runtime_dir = staging_dir / "python"
    _reset_child_directory(runtime_dir, staging_dir)
    shutil.copytree(source, runtime_dir, ignore=_python_runtime_ignore)
    site_packages = runtime_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    _run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--no-compile",
            "--target",
            site_packages,
            ".",
        ],
        cwd=REPO_ROOT,
    )
    _run([runtime_dir / "python.exe", "-m", "atot.cli", "--help"], cwd=REPO_ROOT)


def _write_package_readme(
    staging_dir: Path, *, platform: str, include_python_runtime: bool
) -> None:
    if platform == "Windows":
        runtime_lines = (
            [
                "This package also contains a portable Python runtime with SonaFolio CLI dependencies.",
                "The Qt client will run python\\python.exe -m atot.cli automatically.",
            ]
            if include_python_runtime
            else [
                "Configure atot.exe in Settings, or place it under the default data root:",
                "%USERPROFILE%\\Documents\\SpeechToTextData\\env\\Scripts\\atot.exe",
            ]
        )
        title = "SonaFolio Qt Windows client"
    else:
        runtime_lines = [
            "Configure atot in Settings, or place it under the default data root:",
            "~/Documents/SpeechToTextData/env/bin/atot",
        ]
        title = f"SonaFolio Qt {platform} client"
    (staging_dir / "README.txt").write_text(
        "\n".join(
            [
                title,
                "",
                "This package contains the Qt client and ffmpeg/ffprobe.",
                *runtime_lines,
                "",
                "Model files, transcripts, downloaded audio, and runtime data stay outside "
                "this package.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _macos_app_bundle_from_executable(executable: Path) -> Path:
    for parent in executable.parents:
        if parent.name.endswith(".app"):
            return parent
    raise SystemExit(f"SonaFolio Qt: macOS app bundle was not found for executable: {executable}")


def _stage_macos_bundle(app_bundle: Path, staging_dir: Path) -> Path:
    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    _reset_child_directory(staging_dir, staging_dir.parent)
    staging_dir.mkdir(parents=True)
    target_app = staging_dir / app_bundle.name
    shutil.copytree(
        app_bundle,
        target_app,
        symlinks=True,
        ignore=shutil.ignore_patterns(*PACKAGE_IGNORE_PATTERNS),
    )
    return target_app


def _create_package_archive(staging_dir: Path, archive_path: Path) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    archive_base = archive_path.with_suffix("")
    created = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=staging_dir.parent,
        base_dir=staging_dir.name,
    )
    return Path(created)


def _package_windows(args: argparse.Namespace, build_dir: Path) -> Path:
    _build(args, build_dir, configure_if_missing=True)
    executable = _find_executable(build_dir, args.configuration)
    package_dir = _resolve_repo_path(args.package_dir)
    staging_root = _resolve_repo_path(args.package_staging_dir)
    staging_dir = staging_root / PRODUCT_NAME
    _stage_runtime(executable.parent, staging_dir)
    _copy_ffmpeg_tools(staging_dir, args.ffmpeg_dir)
    _copy_msvc_runtime(staging_dir, args.msvc_runtime_dir)
    if args.include_python_runtime:
        _stage_python_runtime(staging_dir, args.python_runtime_source)
    _write_package_readme(
        staging_dir, platform="Windows", include_python_runtime=args.include_python_runtime
    )
    archive_path = _package_archive_path(
        package_dir,
        _qt_project_version(),
        include_python_runtime=args.include_python_runtime,
        platform="Windows",
    )
    stage_release_licenses(staging_dir, Path(args.third_party_materials) if args.third_party_materials else None)
    created = _create_package_archive(staging_dir, archive_path)
    print(f"Package: {created}", flush=True)
    return created


def _verify_macos_dependency_paths(app: Path) -> None:
    """Do not release a bundle tied to a developer's Homebrew or other absolute library roots."""
    for path in app.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic not in {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                         b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
                         b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"}:
            continue
        result = subprocess.run(["otool", "-L", str(path)], check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "(compatibility version" not in line:
                continue
            dependency = line.strip().split(" (", 1)[0]
            if dependency.startswith("/") and not dependency.startswith(("/System/Library/", "/usr/lib/")):
                raise ValueError(
                    "Nonportable macOS dependency in " + path.name + ": " + Path(dependency).name
                    + ". Deploy and rewire matching libraries before release; include them in the license manifest."
                )


def _package_macos(args: argparse.Namespace, build_dir: Path) -> Path:
    if args.include_python_runtime:
        raise SystemExit(
            "SonaFolio Qt: --include-python-runtime is only supported for Windows packages."
        )
    _build(args, build_dir, configure_if_missing=True)
    executable = _find_executable(build_dir, args.configuration)
    app_bundle = _macos_app_bundle_from_executable(executable)
    package_dir = _resolve_repo_path(args.package_dir)
    staging_root = _resolve_repo_path(args.package_staging_dir)
    staging_dir = staging_root / PRODUCT_NAME
    target_app = _stage_macos_bundle(app_bundle, staging_dir)
    deploy_tool = _find_qt_deploy_tool(args.qt_prefix, build_dir)
    _run(
        [
            deploy_tool,
            target_app,
            f"-qmldir={QT_PROJECT_DIR / 'qml'}",
            "-appstore-compliant",
            "-always-overwrite",
        ]
    )
    _copy_ffmpeg_tools(target_app / "Contents" / "MacOS", args.ffmpeg_dir)
    _verify_macos_dependency_paths(target_app)
    _write_package_readme(staging_dir, platform="macOS", include_python_runtime=False)
    archive_path = _package_archive_path(
        package_dir,
        _qt_project_version(),
        platform="macOS",
    )
    stage_release_licenses(staging_dir, Path(args.third_party_materials) if args.third_party_materials else None)
    created = _create_package_archive(staging_dir, archive_path)
    print(f"Package: {created}", flush=True)
    return created


def _package(args: argparse.Namespace, build_dir: Path) -> Path:
    if os.name == "nt":
        return _package_windows(args, build_dir)
    if sys.platform == "darwin":
        return _package_macos(args, build_dir)
    raise SystemExit("SonaFolio Qt: client packaging is only supported on Windows and macOS.")


def _app_args(values: list[str]) -> list[str]:
    if values and values[0] == "--":
        return values[1:]
    return values


def _launch(
    args: argparse.Namespace, build_dir: Path, app_args: list[str], *, smoke: bool = False
) -> None:
    env = os.environ.copy()
    if smoke:
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        windows_fonts = Path(env.get("SystemRoot", r"C:\Windows")) / "Fonts"
        if windows_fonts.exists():
            env.setdefault("QT_QPA_FONTDIR", str(windows_fonts))
        app_args = ["--smoke-quit", *app_args]
    _run([_find_executable(build_dir, args.configuration), *app_args], env=env)


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-dir", default=_repo_relative(DEFAULT_BUILD_DIR))
    parser.add_argument("--configuration", default="Release")
    parser.add_argument("--qt-prefix")
    parser.add_argument("--generator")


def _add_package_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--third-party-materials", help="Reviewed redistribution manifest, including license texts and matching sources.")
    parser.add_argument("--package-dir", default=_repo_relative(DEFAULT_PACKAGE_DIR))
    parser.add_argument(
        "--package-staging-dir",
        default=_repo_relative(DEFAULT_PACKAGE_STAGING_DIR),
    )
    parser.add_argument(
        "--ffmpeg-dir",
        help="Directory containing ffmpeg/ffprobe tools and their runtime libraries.",
    )
    parser.add_argument(
        "--msvc-runtime-dir",
        help="Directory containing MSVC runtime DLLs such as msvcp140.dll.",
    )
    parser.add_argument(
        "--include-python-runtime",
        action="store_true",
        help="Bundle a portable Python runtime and SonaFolio CLI dependencies.",
    )
    parser.add_argument(
        "--python-runtime-source",
        help=f"Python installation to copy when --include-python-runtime is set. Defaults to {DEFAULT_PYTHON_RUNTIME_SOURCE}.",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SonaFolio Qt workflow helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("config", "build", "launch", "run", "smoke", "package"):
        subparser = subparsers.add_parser(name)
        _add_common_arguments(subparser)
        if name in {"launch", "run", "smoke"}:
            subparser.add_argument("app_args", nargs=argparse.REMAINDER)
        if name == "package":
            _add_package_arguments(subparser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    build_dir = _resolve_repo_path(args.build_dir)

    if args.command == "config":
        _configure(args, build_dir)
    elif args.command == "build":
        _build(args, build_dir, configure_if_missing=True)
    elif args.command == "launch":
        _launch(args, build_dir, _app_args(args.app_args))
    elif args.command == "run":
        _build(args, build_dir, configure_if_missing=True)
        _launch(args, build_dir, _app_args(args.app_args))
    elif args.command == "smoke":
        _build(args, build_dir, configure_if_missing=True)
        _launch(args, build_dir, _app_args(args.app_args), smoke=True)
    elif args.command == "package":
        _package(args, build_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
