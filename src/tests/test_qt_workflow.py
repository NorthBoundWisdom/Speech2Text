from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from configs import qt_workflow


@pytest.mark.skipif(
    not shutil.which("cmake") or not shutil.which("ctest"), reason="CMake tools unavailable"
)
def test_qt_build_includes_new_test_targets(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    build = tmp_path / "build"
    targets = [
        "Audio2TextQt", "Audio2TextQtLanguageSettingsTests",
        "Audio2TextQtWorkspaceTests", "Audio2TextQtSharedRuntimeTests",
    ]
    lines = [
        "cmake_minimum_required(VERSION 3.24)", "project(BuildCoverage NONE)", "enable_testing()"
    ]
    for target in targets:
        lines.append(
            f'add_custom_target({target} ALL COMMAND "${{CMAKE_COMMAND}}" -E touch '
            f'"${{CMAKE_BINARY_DIR}}/{target}.built")'
        )
    lines.append(
        'add_test(NAME SharedRuntime COMMAND "${CMAKE_COMMAND}" -E compare_files '
        '"${CMAKE_BINARY_DIR}/Audio2TextQtSharedRuntimeTests.built" '
        '"${CMAKE_BINARY_DIR}/Audio2TextQt.built")'
    )
    (source / "CMakeLists.txt").write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["cmake", "-S", str(source), "-B", str(build)], check=True, capture_output=True)
    args = qt_workflow.parse_args(["build"])
    qt_workflow._build(args, build, configure_if_missing=False)
    subprocess.run(
        ["ctest", "--test-dir", str(build), "-C", "Release", "--output-on-failure"],
        check=True, capture_output=True,
    )


@pytest.mark.parametrize("configuration", ["Release", "Debug", "RelWithDebInfo"])
def test_qt_configure_sets_build_type_and_refreshes_qt_discovery(
    monkeypatch, tmp_path, configuration
) -> None:
    args = qt_workflow.parse_args(
        [
            "config",
            "--generator",
            "Ninja",
            "--configuration",
            configuration,
        ]
    )
    commands = []
    class Roots:
        def root_for_dependency(self, name):
            assert name == "GeoControls"
            return tmp_path / "GeoControls"

    monkeypatch.setattr(qt_workflow.WORKFLOW, "resolve_source_roots", lambda **_: Roots())
    monkeypatch.setattr(qt_workflow, "_find_qt_prefix", lambda *_: tmp_path / "Qt")
    monkeypatch.setattr(qt_workflow, "_run", commands.append)

    qt_workflow._configure(args, tmp_path / "build")

    assert f"-DCMAKE_BUILD_TYPE={configuration}" in commands[0]
    assert "-UQt6*_DIR" in commands[0]
    assert "-UQT_FEATURE_*" in commands[0]
    assert f"-DGEOCONTROLS_SOURCE_ROOT={tmp_path / 'GeoControls'}" in commands[0]


def test_qt_workflow_package_command_defaults_to_release_zip() -> None:
    args = qt_workflow.parse_args(["package"])

    assert args.command == "package"
    assert args.configuration == "Release"
    assert args.build_dir == "build/Audio2TextQt"
    assert args.package_dir == "build/package"
    assert args.package_staging_dir == "build/package-staging"
    assert args.ffmpeg_dir is None
    assert args.msvc_runtime_dir is None
    assert args.include_python_runtime is False
    assert args.python_runtime_source is None


def test_qt_package_archive_path_includes_version(tmp_path) -> None:
    archive = qt_workflow._package_archive_path(tmp_path, "1.2.3")

    assert archive.name == "SonaFolioQt_v1.2.3_Windows.zip"


def test_qt_runtime_package_archive_path_has_distinct_name(tmp_path) -> None:
    archive = qt_workflow._package_archive_path(tmp_path, "1.2.3", include_python_runtime=True)

    assert archive.name == "SonaFolioQt_v1.2.3_Windows_Runtime.zip"


def test_qt_macos_package_archive_path_has_platform_name(tmp_path) -> None:
    archive = qt_workflow._package_archive_path(tmp_path, "1.2.3", platform="macOS")

    assert archive.name == "SonaFolioQt_v1.2.3_macOS.zip"


def test_qt_workflow_macos_executable_candidates_include_app_bundle(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(qt_workflow, "_source_roots_platform_key", lambda: "mac")
    monkeypatch.setattr(qt_workflow, "_qt_deploy_tool_name", lambda: "macdeployqt")
    monkeypatch.setattr(qt_workflow, "_qt_qmake_names", lambda: ("qmake6", "qmake"))
    monkeypatch.setattr(qt_workflow.sys, "platform", "darwin")

    candidates = qt_workflow._executable_candidates(tmp_path, "Release")

    assert (
        tmp_path / "Release" / "SonaFolioQt.app" / "Contents" / "MacOS" / "SonaFolioQt"
        in candidates
    )
    assert tmp_path / "SonaFolioQt.app" / "Contents" / "MacOS" / "SonaFolioQt" in candidates
    suffix = ".exe" if qt_workflow.os.name == "nt" else ""
    assert tmp_path / "Release" / ("SonaFolioQt" + suffix) in candidates
    assert tmp_path / ("SonaFolioQt" + suffix) in candidates


def test_qt_workflow_macos_qt_prefix_accepts_macdeployqt(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(qt_workflow, "_source_roots_platform_key", lambda: "mac")
    monkeypatch.setattr(qt_workflow, "_qt_deploy_tool_name", lambda: "macdeployqt")
    monkeypatch.setattr(qt_workflow, "_qt_qmake_names", lambda: ("qmake6", "qmake"))
    monkeypatch.setattr(qt_workflow.sys, "platform", "darwin")
    qt_prefix = tmp_path / "Qt"
    (qt_prefix / "lib" / "cmake" / "Qt6").mkdir(parents=True)
    (qt_prefix / "lib" / "cmake" / "Qt6" / "Qt6Config.cmake").write_text("", encoding="utf-8")
    (qt_prefix / "bin").mkdir()
    (qt_prefix / "bin" / "macdeployqt").write_text("", encoding="utf-8")

    assert qt_workflow._looks_like_qt_prefix(qt_prefix)


def test_qt_workflow_qt_prefix_accepts_qmake6(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(qt_workflow, "_source_roots_platform_key", lambda: "mac")
    monkeypatch.setattr(qt_workflow, "_qt_deploy_tool_name", lambda: "macdeployqt")
    monkeypatch.setattr(qt_workflow, "_qt_qmake_names", lambda: ("qmake6", "qmake"))
    monkeypatch.setattr(qt_workflow.sys, "platform", "darwin")
    qt_prefix = tmp_path / "Qt"
    (qt_prefix / "lib" / "cmake" / "Qt6").mkdir(parents=True)
    (qt_prefix / "lib" / "cmake" / "Qt6" / "Qt6Config.cmake").write_text("", encoding="utf-8")
    (qt_prefix / "bin").mkdir()
    (qt_prefix / "bin" / "qmake6").write_text("", encoding="utf-8")

    assert qt_workflow._looks_like_qt_prefix(qt_prefix)


def test_qt_workflow_reads_qt_prefix_from_source_roots(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(qt_workflow, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qt_workflow, "_source_roots_platform_key", lambda: "mac")
    monkeypatch.setattr(qt_workflow, "_qt_deploy_tool_name", lambda: "macdeployqt")
    monkeypatch.setattr(qt_workflow, "_qt_qmake_names", lambda: ("qmake6", "qmake"))
    monkeypatch.setattr(qt_workflow.sys, "platform", "darwin")
    qt_prefix = tmp_path / "Qt" / "6.11.1" / "macos"
    (qt_prefix / "lib" / "cmake" / "Qt6").mkdir(parents=True)
    (qt_prefix / "lib" / "cmake" / "Qt6" / "Qt6Config.cmake").write_text("", encoding="utf-8")
    (qt_prefix / "bin").mkdir()
    (qt_prefix / "bin" / "macdeployqt").write_text("", encoding="utf-8")
    (tmp_path / "source_roots.lock.jsonc").write_text(
        json.dumps(
            {
                "schemaVersion": 5,
                "cmakeCacheVariables": {"mac": {"CMAKE_PREFIX_PATH": str(qt_prefix)}},
            }
        ),
        encoding="utf-8",
    )

    assert qt_workflow._find_qt_prefix(None, tmp_path / "build") == qt_prefix


def test_qt_workflow_source_roots_ffmpeg_dirs_include_prefix_tools(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(qt_workflow, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(qt_workflow, "_source_roots_platform_key", lambda: "mac")
    monkeypatch.setattr(qt_workflow, "_qt_deploy_tool_name", lambda: "macdeployqt")
    monkeypatch.setattr(qt_workflow, "_qt_qmake_names", lambda: ("qmake6", "qmake"))
    monkeypatch.setattr(qt_workflow.sys, "platform", "darwin")
    vcpkg_prefix = tmp_path / "vcpkg" / "installed" / "arm64-osx"
    (tmp_path / "source_roots.lock.jsonc").write_text(
        json.dumps(
            {
                "schemaVersion": 5,
                "cmakeCacheVariables": {"mac": {"CMAKE_PREFIX_PATH": str(vcpkg_prefix)}},
            }
        ),
        encoding="utf-8",
    )

    dirs = qt_workflow._candidate_ffmpeg_dirs(None)

    assert (
        "source_roots.lock.jsonc cmakeCacheVariables.mac.CMAKE_PREFIX_PATH",
        vcpkg_prefix / "tools" / "ffmpeg",
    ) in dirs
    assert (
        "source_roots.lock.jsonc cmakeCacheVariables.mac.CMAKE_PREFIX_PATH",
        vcpkg_prefix / "bin",
    ) in dirs


def test_qt_workflow_finds_macos_app_bundle_from_executable(tmp_path) -> None:
    executable = tmp_path / "SonaFolioQt.app" / "Contents" / "MacOS" / "SonaFolioQt"

    assert (
        qt_workflow._macos_app_bundle_from_executable(executable) == tmp_path / "SonaFolioQt.app"
    )


def test_qt_project_version_matches_cmake_project() -> None:
    assert qt_workflow._qt_project_version() == "0.9.2"


def test_qt_stage_runtime_excludes_debug_sidecars(tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "SonaFolioQt.exe").write_text("", encoding="utf-8")
    (runtime_dir / "Qt6Core.dll").write_text("", encoding="utf-8")
    (runtime_dir / "Audio2TextQt.pdb").write_text("", encoding="utf-8")
    (runtime_dir / "Audio2TextQt.ilk").write_text("", encoding="utf-8")

    staging_dir = tmp_path / "staging" / "Audio2TextQt"
    qt_workflow._stage_runtime(runtime_dir, staging_dir)

    assert (staging_dir / "SonaFolioQt.exe").exists()
    assert (staging_dir / "Qt6Core.dll").exists()
    assert not (staging_dir / "Audio2TextQt.pdb").exists()
    assert not (staging_dir / "Audio2TextQt.ilk").exists()


def test_qt_package_copies_ffmpeg_tools_next_to_executable(tmp_path, monkeypatch) -> None:
    import subprocess
    monkeypatch.setattr(qt_workflow.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout="ffmpeg version test\nconfiguration: --enable-gpl\n"))
    ffmpeg_dir = tmp_path / "ffmpeg"
    ffmpeg_dir.mkdir()
    for tool_name in qt_workflow.FFMPEG_TOOL_NAMES:
        (ffmpeg_dir / tool_name).write_text(tool_name, encoding="utf-8")
    (ffmpeg_dir / "avcodec-62.dll").write_text("dll", encoding="utf-8")

    staging_dir = tmp_path / "staging" / "Audio2TextQt"
    staging_dir.mkdir(parents=True)
    qt_workflow._copy_ffmpeg_tools(staging_dir, str(ffmpeg_dir))

    for tool_name in qt_workflow.FFMPEG_TOOL_NAMES:
        assert (staging_dir / tool_name).read_text(encoding="utf-8") == tool_name
    assert (staging_dir / "avcodec-62.dll").read_text(encoding="utf-8") == "dll"


def test_qt_package_copies_msvc_runtime_next_to_executable(tmp_path) -> None:
    runtime_dir = tmp_path / "Microsoft.VC143.CRT"
    runtime_dir.mkdir()
    for dll_name in (
        "msvcp140.dll",
        "msvcp140_1.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
    ):
        (runtime_dir / dll_name).write_text(dll_name, encoding="utf-8")

    staging_dir = tmp_path / "staging" / "Audio2TextQt"
    staging_dir.mkdir(parents=True)
    qt_workflow._copy_msvc_runtime(staging_dir, str(runtime_dir))

    for dll_name in (
        "msvcp140.dll",
        "msvcp140_1.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
    ):
        assert (staging_dir / dll_name).read_text(encoding="utf-8") == dll_name


def test_qt_package_requires_msvc_runtime_for_windows_zip(tmp_path) -> None:
    runtime_dir = tmp_path / "empty"
    runtime_dir.mkdir()
    staging_dir = tmp_path / "staging" / "Audio2TextQt"
    staging_dir.mkdir(parents=True)

    with pytest.raises(SystemExit, match="MSVC runtime DLLs were not found"):
        qt_workflow._copy_msvc_runtime(staging_dir, str(runtime_dir))


def test_qt_python_runtime_ignore_skips_global_site_packages(tmp_path) -> None:
    source = tmp_path / "Python312"
    site = source / "Lib" / "site-packages"
    site.mkdir(parents=True)

    ignored = qt_workflow._python_runtime_ignore(str(source / "Lib"), ["site-packages", "os.py"])

    assert "site-packages" in ignored
    assert "os.py" not in ignored


def test_qt_package_rejects_nonfree_ffmpeg(tmp_path, monkeypatch):
    import subprocess
    ffmpeg_dir = tmp_path / 'ffmpeg'
    ffmpeg_dir.mkdir()
    for tool in qt_workflow.FFMPEG_TOOL_NAMES:
        (ffmpeg_dir / tool).write_text('synthetic tool')
    monkeypatch.setattr(qt_workflow.subprocess, 'run', lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout='ffmpeg version test\n--enable-nonfree\n'))
    with pytest.raises(ValueError, match='cannot be redistributed'):
        qt_workflow._copy_ffmpeg_tools(tmp_path, str(ffmpeg_dir))


def test_python_runtime_rejects_private_custom_files(tmp_path):
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    (runtime / 'python.exe').write_text('synthetic runtime')
    (runtime / 'config.toml').write_text('private configuration')
    with pytest.raises(SystemExit, match='clean Python distribution'):
        qt_workflow._stage_python_runtime(tmp_path / 'stage', str(runtime))


def test_macos_release_rejects_external_non_system_linked_libraries(tmp_path, monkeypatch):
    import subprocess
    executable = tmp_path / 'ffmpeg'
    executable.write_bytes(b'\xcf\xfa\xed\xfe' + b'synthetic Mach-O')
    monkeypatch.setattr(qt_workflow.subprocess, 'run', lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout='ffmpeg:\n /opt/local/lib/libcodec.dylib (compatibility version 1.0.0, current version 1.0.0)\n'))
    with pytest.raises(ValueError, match='Nonportable macOS dependency'):
        qt_workflow._verify_macos_dependency_paths(tmp_path)
