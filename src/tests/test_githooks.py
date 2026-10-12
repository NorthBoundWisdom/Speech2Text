from pathlib import Path

from Utils import githooks_manager


def test_hook_manager_defaults_cover_mac_and_ipad_build_gate() -> None:
    assert githooks_manager.HOOKS_DIR == "configs/githooks"
    assert githooks_manager.HOOK_FILES == ("pre-commit",)
    assert githooks_manager.DEFAULTS[githooks_manager.BOOL_KEYS["build_gate"]] == "true"
    assert githooks_manager.DEFAULTS[githooks_manager.STRING_KEYS["mac_scheme"]] == "Audio2TextApp"
    assert githooks_manager.DEFAULTS[githooks_manager.STRING_KEYS["ios_scheme"]] == "Audio2Text-iOS"
    assert githooks_manager.DEFAULTS[githooks_manager.STRING_KEYS["build_configuration"]] == "Debug"


def test_pre_commit_builds_mac_and_ios_simulator_targets() -> None:
    script = Path("configs/githooks/pre-commit").read_text()

    assert "src/scripts/check_public_paths.py" in script
    assert "configs/setup_local_app.py" in script
    assert "xcodebuild" in script
    assert '-scheme "$mac_scheme"' in script
    assert '-scheme "$ios_scheme"' in script
    assert "-sdk macosx" in script
    assert "-sdk iphonesimulator" in script
    assert "generic/platform=iOS Simulator" in script
    assert "audio2text.hooks.enableBuildGate true" in script


def test_hook_installer_points_git_at_tracked_hook_directory() -> None:
    script = Path("configs/installhooks.py").read_text()
    manager = Path("Utils/githooks_manager.py").read_text()

    assert "Utils" in script
    assert "githooks_manager.py" in script
    assert "core.hooksPath" in manager
    assert "configs/githooks" in manager


def test_xcode_cloud_post_clone_generates_ignored_project() -> None:
    script_path = Path("ci_scripts/ci_post_clone.sh")
    script = script_path.read_text()

    assert script_path.exists()
    assert "CI_PRIMARY_REPOSITORY_PATH" in script
    assert "source_roots.lock.jsonc.in" in script
    assert "cp source_roots.lock.jsonc.in source_roots.lock.jsonc" in script
    assert "python3 configs/generate_xcodeproj.py" in script
    assert "Audio2Text.xcodeproj/project.pbxproj" in script
    assert "Audio2TextApp.xcscheme" in script
    assert "Audio2Text-iOS.xcscheme" in script
