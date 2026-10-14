from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_PATH = REPO_ROOT / "configs" / "freecm.commands.jsonc"


def _manifest() -> dict[str, object]:
    return json.loads(COMMANDS_PATH.read_text(encoding="utf-8"))


def _configuration(manifest: dict[str, object], config_id: str) -> dict[str, object]:
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    configurations = commands["config"]
    assert isinstance(configurations, list)
    return next(
        config
        for config in configurations
        if isinstance(config, dict) and config.get("id") == config_id
    )


def _default_variant(
    manifest: dict[str, object], action: str, config_id: str = "local-app"
) -> dict[str, object]:
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    config = _configuration(manifest, config_id)
    if action == "config":
        return config
    defaults = config["defaults"]
    assert isinstance(defaults, dict)
    variants = commands[action]
    assert isinstance(variants, list)
    return next(
        variant
        for variant in variants
        if isinstance(variant, dict) and variant.get("id") == defaults[action]
    )


def test_freecm_manifest_passes_current_config_context_validation() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "FreeCM" / "tools" / "validate_repo_commands.py"),
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_freecm_config_build_package_are_wired_to_local_app_workflow() -> None:
    manifest = _manifest()

    config = _default_variant(manifest, "config")
    build = _default_variant(manifest, "build")
    package = _default_variant(manifest, "package")

    assert config["command"] == "python3"
    assert config["args"] == ["configs/setup_local_app.py"]

    assert build["command"] == "python3"
    assert build["args"] == [
        "configs/ios_workflow.py",
        "build",
        "--platform",
        "mac",
        "--scheme",
        "Audio2TextApp",
        "--configuration",
        "debug",
        "--distribution",
        "local",
    ]

    assert package["command"] == "python3"
    assert package["args"] == [
        "configs/ios_workflow.py",
        "package",
        "--platform",
        "mac",
        "--scheme",
        "Audio2TextApp",
        "--configuration",
        "release",
        "--distribution",
        "development",
    ]


def test_freecm_developer_id_package_variant_is_release_dmg() -> None:
    manifest = _manifest()
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    package_variants = commands["package"]
    assert isinstance(package_variants, list)

    developer_id = next(
        variant
        for variant in package_variants
        if isinstance(variant, dict) and variant.get("id") == "mac-app-dmg-developer-id"
    )

    assert developer_id["args"] == [
        "configs/ios_workflow.py",
        "package",
        "--platform",
        "mac",
        "--scheme",
        "Audio2TextApp",
        "--configuration",
        "release",
        "--distribution",
        "developer-id",
    ]


def test_freecm_macos_qt_run_variant_uses_qt_workflow() -> None:
    manifest = _manifest()
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    run_variants = commands["run"]
    assert isinstance(run_variants, list)

    mac_qt = next(
        variant
        for variant in run_variants
        if isinstance(variant, dict) and variant.get("id") == "mac-qt-client"
    )

    assert mac_qt["command"] == "python3"
    assert mac_qt["args"] == [
        "configs/qt_workflow.py",
        "run",
        "--configuration",
        "Release",
    ]
    assert mac_qt["configurations"] == ["local-app", "mac-qt-client"]
    assert _configuration(manifest, "mac-qt-client")["platforms"] == ["darwin"]
    assert "default" not in mac_qt


def test_freecm_macos_qt_package_variant_uses_qt_workflow() -> None:
    manifest = _manifest()
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    package_variants = commands["package"]
    assert isinstance(package_variants, list)

    mac_qt = next(
        variant
        for variant in package_variants
        if isinstance(variant, dict) and variant.get("id") == "mac-qt-client-zip"
    )

    assert mac_qt["command"] == "python3"
    assert mac_qt["args"] == [
        "configs/qt_workflow.py",
        "package",
        "--configuration",
        "Release",
    ]
    assert mac_qt["configurations"] == ["local-app", "mac-qt-client"]
    assert _configuration(manifest, "mac-qt-client")["platforms"] == ["darwin"]
    assert "default" not in mac_qt


def test_freecm_windows_package_variant_is_qt_client_zip() -> None:
    manifest = _manifest()
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    package_variants = commands["package"]
    assert isinstance(package_variants, list)

    windows_package = next(
        variant
        for variant in package_variants
        if isinstance(variant, dict) and variant.get("id") == "win-qt-client-zip"
    )

    assert windows_package["command"] == "python"
    assert windows_package["args"] == [
        "configs/qt_workflow.py",
        "package",
        "--configuration",
        "Release",
    ]
    assert windows_package["configurations"] == ["win-qt-client"]
    assert _configuration(manifest, "win-qt-client")["platforms"] == ["win32"]
    assert _default_variant(manifest, "package", "win-qt-client") == windows_package


def test_freecm_windows_runtime_package_variant_bundles_python() -> None:
    manifest = _manifest()
    commands = manifest["commands"]
    assert isinstance(commands, dict)
    package_variants = commands["package"]
    assert isinstance(package_variants, list)

    windows_package = next(
        variant
        for variant in package_variants
        if isinstance(variant, dict) and variant.get("id") == "win-qt-client-runtime-zip"
    )

    assert windows_package["command"] == "python"
    assert windows_package["args"] == [
        "configs/qt_workflow.py",
        "package",
        "--configuration",
        "Release",
        "--include-python-runtime",
    ]
    assert windows_package["configurations"] == ["win-qt-client"]
    assert _configuration(manifest, "win-qt-client")["platforms"] == ["win32"]
    assert "default" not in windows_package
