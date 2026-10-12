from __future__ import annotations

import subprocess
import sys

from configs import generate_xcodeproj
from configs import setup_local_app


def test_atot_import_origin_check_requires_source_tree(monkeypatch, tmp_path) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(setup_local_app.subprocess, "run", fake_run)

    assert setup_local_app._atot_imports_from_source(tmp_path / "python") is True
    assert calls
    code = calls[0][0][-1]
    assert str(setup_local_app.REPO_ROOT / "src" / "atot").__repr__() in code


def test_pyproject_publishes_v2_cli_scripts() -> None:
    text = (setup_local_app.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.scripts]" in text
    assert 'atot = "atot.cli:main"' in text
    assert 'Audio2TextCli = "atot.cli:main"' in text


def test_xcode_generator_shares_marked_workspace_shell_with_ios_target(tmp_path) -> None:
    shared_source = generate_xcodeproj.APP_SOURCE_DIR / "LibraryWorkspaceShell.swift"
    mac_only_source = tmp_path / "MacOnlyView.swift"
    mac_only_source.write_text("import SwiftUI\n", encoding="utf-8")

    assert (
        generate_xcodeproj.IOS_SHARED_SOURCE_MARKER
        in shared_source.read_text(encoding="utf-8")[:512]
    )
    assert generate_xcodeproj._is_ios_shared_app_source(shared_source) is True
    assert generate_xcodeproj._is_ios_shared_app_source(mac_only_source) is False


def test_setup_local_app_uses_platform_venv_bin(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(setup_local_app.os, "name", "nt", raising=False)

    assert setup_local_app._venv_bin_dir(tmp_path) == tmp_path / "Scripts"
    assert (
        setup_local_app._venv_executable(tmp_path, "python") == tmp_path / "Scripts" / "python.exe"
    )

    monkeypatch.setattr(setup_local_app.os, "name", "posix", raising=False)
    assert setup_local_app._venv_bin_dir(tmp_path) == tmp_path / "bin"
    assert setup_local_app._venv_executable(tmp_path, "python") == tmp_path / "bin" / "python"


def test_runtime_constraint_uses_pep440_prerelease_ordering() -> None:
    prerelease = setup_local_app._pep440_minimum_check_code(
        "msgpack", "1.2.1", installed_version="1.2.1rc1"
    )
    final = setup_local_app._pep440_minimum_check_code(
        "msgpack", "1.2.1", installed_version="1.2.1"
    )

    assert subprocess.run([sys.executable, "-c", prerelease], check=False).returncode == 1
    assert subprocess.run([sys.executable, "-c", final], check=False).returncode == 0


def test_ensure_env_uses_editable_install_when_source_is_not_active(monkeypatch, tmp_path) -> None:
    root = tmp_path
    python = setup_local_app._venv_executable(root / "env", "python")
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    commands = []

    monkeypatch.setattr(setup_local_app, "_atot_imports_from_source", lambda _python: False)
    monkeypatch.setattr(setup_local_app, "_command_ok", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        setup_local_app, "_environment_meets_runtime_constraints", lambda _python: True
    )

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(setup_local_app.subprocess, "run", fake_run)

    setup_local_app._ensure_env(root)

    assert commands == [
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--constraint",
            str(setup_local_app.RUNTIME_CONSTRAINTS),
            "-e",
            ".[dev]",
        ]
    ]


def test_ensure_env_reinstalls_when_runtime_constraints_are_stale(
    monkeypatch, tmp_path
) -> None:
    root = tmp_path
    python = setup_local_app._venv_executable(root / "env", "python")
    atot = setup_local_app._venv_executable(root / "env", "atot")
    app_cli = setup_local_app._venv_executable(root / "env", "Audio2TextCli")
    python.parent.mkdir(parents=True)
    for executable in (python, atot, app_cli):
        executable.write_text("", encoding="utf-8")
    commands = []

    monkeypatch.setattr(setup_local_app, "_atot_imports_from_source", lambda _python: True)
    monkeypatch.setattr(setup_local_app, "_command_ok", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        setup_local_app, "_environment_meets_runtime_constraints", lambda _python: False
    )
    monkeypatch.setattr(
        setup_local_app.subprocess,
        "run",
        lambda cmd, **kwargs: commands.append(cmd) or subprocess.CompletedProcess(cmd, 0),
    )

    setup_local_app._ensure_env(root)

    assert commands[0][4:6] == ["--constraint", str(setup_local_app.RUNTIME_CONSTRAINTS)]
