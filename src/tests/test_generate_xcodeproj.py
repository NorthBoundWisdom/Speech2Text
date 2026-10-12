import plistlib
from pathlib import Path

from configs import generate_xcodeproj


def _prepare_minimal_project(tmp_path, monkeypatch, *, app_configs: str) -> tuple[Path, Path]:
    project_path = tmp_path / "Audio2Text.xcodeproj"
    source_dir = tmp_path / "app" / "Sources" / "Audio2TextApp"
    core_dir = tmp_path / "app" / "Sources" / "Audio2TextCore"
    ios_dir = tmp_path / "app" / "Sources" / "Audio2TextiOS"
    test_dir = tmp_path / "app" / "Tests" / "Audio2TextAppTests"
    active_lock = tmp_path / "source_roots.lock.jsonc"
    source_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    ios_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    active_lock.write_text(
        f"""{{
  "schemaVersion": 5,
  "AppConfigs": {app_configs},
  "depsMode": "pinned",
  "depsManualPath": {{}},
  "dependencies": {{}}
}}
""",
        encoding="utf-8",
    )
    (core_dir / "Core.swift").write_text("import Foundation\n", encoding="utf-8")
    (source_dir / "Audio2TextApp.swift").write_text("import SwiftUI\n", encoding="utf-8")
    (source_dir / "ReadingStyleSettings.swift").write_text(
        "// Audio2Text-iOS shared source\n\nimport SwiftUI\n",
        encoding="utf-8",
    )
    (source_dir / "SimpleMarkdownView.swift").write_text(
        "// Audio2Text-iOS shared source\n\nimport SwiftUI\n",
        encoding="utf-8",
    )
    (source_dir / "MacOnlyView.swift").write_text("import SwiftUI\n", encoding="utf-8")
    (ios_dir / "Audio2TextiOSApp.swift").write_text("import SwiftUI\n", encoding="utf-8")
    (test_dir / "Audio2TextAppTests.swift").write_text("import Testing\n", encoding="utf-8")
    monkeypatch.setattr(generate_xcodeproj, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generate_xcodeproj, "PROJECT_PATH", project_path)
    monkeypatch.setattr(generate_xcodeproj, "PROJECT_FILE", project_path / "project.pbxproj")
    monkeypatch.setattr(generate_xcodeproj, "CORE_SOURCE_DIR", core_dir)
    monkeypatch.setattr(generate_xcodeproj, "APP_SOURCE_DIR", source_dir)
    monkeypatch.setattr(generate_xcodeproj, "IOS_SOURCE_DIR", ios_dir)
    monkeypatch.setattr(generate_xcodeproj, "APP_TEST_DIR", test_dir)
    monkeypatch.setattr(generate_xcodeproj, "SOURCE_ROOTS_ACTIVE_LOCK", active_lock)
    monkeypatch.setattr(
        generate_xcodeproj,
        "SCHEME_FILE",
        project_path / "xcshareddata" / "xcschemes" / "Audio2TextApp.xcscheme",
    )

    return project_path, generate_xcodeproj.generate_xcodeproj()


def test_generate_xcodeproj_writes_root_project(tmp_path, monkeypatch):
    project_path, generated = _prepare_minimal_project(
        tmp_path,
        monkeypatch,
        app_configs="""{
    "DevMode": false,
    "XCODE_DEVELOPMENT_TEAM": "9TBG64SL5U",
    "MARKETING_VERSION": "2.3.4",
    "ARCHIVE_ID": "56"
  }""",
    )

    assert generated == project_path
    assert (project_path / "project.pbxproj").is_file()
    assert (project_path / "xcshareddata" / "xcschemes" / "Audio2TextApp.xcscheme").is_file()
    project_text = (project_path / "project.pbxproj").read_text(encoding="utf-8")
    assert "PBXNativeTarget" in project_text
    assert "PRODUCT_NAME = SonaFolio;" in project_text
    assert "INFOPLIST_KEY_CFBundleDisplayName = SonaFolio;" in project_text
    assert "$(BUILT_PRODUCTS_DIR)/SonaFolio.app/" in project_text
    assert "com.apple.product-type.application" in project_text
    assert "Audio2Text-iOS" in project_text
    assert "app/Audio2TextiOS.entitlements" in project_text
    assert "app/Audio2TextiOS-Info.plist" in project_text
    assert "app/Resources/Audio2Text.xcassets" in project_text
    assert "Audio2Text.xcassets in Resources" in project_text
    assert "Core.swift in Sources" in project_text
    assert project_text.count("Core.swift in Sources") == 4
    assert project_text.count("ReadingStyleSettings.swift in Sources") == 4
    assert project_text.count("SimpleMarkdownView.swift in Sources") == 4
    assert project_text.count("MacOnlyView.swift in Sources") == 2
    assert "/usr/bin/codesign --force --sign" in project_text
    assert "Audio2TextCli" in project_text
    assert "ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;" in project_text
    assert "DEVELOPMENT_TEAM = 9TBG64SL5U;" in project_text
    assert 'MARKETING_VERSION = "2.3.4";' in project_text
    assert "CURRENT_PROJECT_VERSION = 56;" in project_text
    assert "LastUpgradeCheck = 2650;" in project_text
    assert "CreatedOnToolsVersion = 26.5;" in project_text
    assert "ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;" in project_text
    assert "DEAD_CODE_STRIPPING = YES;" in project_text
    assert "ENABLE_TESTABILITY = YES;" in project_text
    assert "ONLY_ACTIVE_ARCH = YES;" in project_text
    assert "STRING_CATALOG_GENERATE_SYMBOLS = YES;" in project_text
    assert 'INFOPLIST_FILE = "app/Audio2TextiOS-Info.plist";' in project_text
    assert "GENERATE_INFOPLIST_FILE = NO;" in project_text
    assert (project_path / "project.xcworkspace" / "contents.xcworkspacedata").is_file()
    assert (project_path / "xcshareddata" / "xcschemes" / "Audio2Text-iOS.xcscheme").is_file()


def test_generate_xcodeproj_preserves_existing_workspace_user_state(tmp_path, monkeypatch):
    project_path, _ = _prepare_minimal_project(
        tmp_path,
        monkeypatch,
        app_configs="""{
    "DevMode": false,
    "MARKETING_VERSION": "2.3.4",
    "ARCHIVE_ID": "56"
  }""",
    )
    user_state = (
        project_path
        / "project.xcworkspace"
        / "xcuserdata"
        / "local.xcuserdatad"
        / "UserInterfaceState.xcuserstate"
    )
    user_state.parent.mkdir(parents=True)
    user_state.write_text("keep local Xcode state", encoding="utf-8")

    generated = generate_xcodeproj.generate_xcodeproj()

    assert generated == project_path
    assert user_state.read_text(encoding="utf-8") == "keep local Xcode state"
    assert (project_path / "project.pbxproj").is_file()
    assert (project_path / "project.xcworkspace" / "contents.xcworkspacedata").is_file()


def test_generate_xcodeproj_allows_missing_development_team(tmp_path, monkeypatch):
    project_path, generated = _prepare_minimal_project(
        tmp_path,
        monkeypatch,
        app_configs="""{
    "DevMode": false,
    "MARKETING_VERSION": "2.3.4",
    "ARCHIVE_ID": "56"
  }""",
    )

    assert generated == project_path
    project_text = (project_path / "project.pbxproj").read_text(encoding="utf-8")
    assert "DEVELOPMENT_TEAM" not in project_text
    assert "CODE_SIGN_STYLE = Automatic;" in project_text


def test_ios_info_plist_declares_background_audio():
    plist_path = generate_xcodeproj.REPO_ROOT / generate_xcodeproj.IOS_INFO_PLIST
    payload = plistlib.loads(plist_path.read_bytes())

    assert payload["CFBundleDisplayName"] == "SonaFolio"
    assert payload["UIBackgroundModes"] == ["audio"], (
        "The iOS reader declares background audio for playback continuity."
    )
