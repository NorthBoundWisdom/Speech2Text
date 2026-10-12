#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT_PATH = REPO_ROOT / "Audio2Text.xcodeproj"
PROJECT_FILE = PROJECT_PATH / "project.pbxproj"
SCHEME_FILE = PROJECT_PATH / "xcshareddata" / "xcschemes" / "Audio2TextApp.xcscheme"
SOURCE_ROOTS_ACTIVE_LOCK = REPO_ROOT / "source_roots.lock.jsonc"
CORE_SOURCE_DIR = REPO_ROOT / "app" / "Sources" / "Audio2TextCore"
APP_SOURCE_DIR = REPO_ROOT / "app" / "Sources" / "Audio2TextApp"
IOS_SOURCE_DIR = REPO_ROOT / "app" / "Sources" / "Audio2TextiOS"
APP_TEST_DIR = REPO_ROOT / "app" / "Tests" / "Audio2TextAppTests"
APP_ENTITLEMENTS = "app/Audio2TextApp.entitlements"
IOS_ENTITLEMENTS = "app/Audio2TextiOS.entitlements"
IOS_INFO_PLIST = "app/Audio2TextiOS-Info.plist"
APP_PRIVACY_MANIFEST = "app/PrivacyInfo.xcprivacy"
IOS_ASSET_CATALOG = "app/Resources/Audio2Text.xcassets"
MODEL_INVENTORY = "src/atot/data/model_inventory.json"
PRODUCT_NAME = "SonaFolio"
CLI_NAME = "Audio2TextCli"
TARGET_NAME = "Audio2TextApp"
IOS_PRODUCT_NAME = "SonaFolio"
IOS_TARGET_NAME = "Audio2Text-iOS"
TEST_TARGET_NAME = "Audio2TextAppTests"
BUNDLE_IDENTIFIER = "com.audio2text.local"
IOS_BUNDLE_IDENTIFIER = "com.audio2text.local.ios"
TEST_BUNDLE_IDENTIFIER = "com.audio2text.local.tests"
IOS_SHARED_SOURCE_MARKER = "Audio2Text-iOS shared source"
APP_TARGET_ID = "A2T0000000000000000A001"
TEST_TARGET_ID = "A2T0000000000000000A002"
IOS_TARGET_ID = "A2T0000000000000000A003"
XCODE_CREATED_ON_TOOLS_VERSION = "26.5"
XCODE_LAST_UPGRADE_CHECK = "2650"
DEVELOPMENT_TEAM_KEY = "XCODE_DEVELOPMENT_TEAM"


def generate_xcodeproj() -> Path:
    if PROJECT_PATH.exists() and not PROJECT_PATH.is_dir():
        PROJECT_PATH.unlink()
    PROJECT_PATH.mkdir(parents=True, exist_ok=True)
    _write_text_if_changed(PROJECT_FILE, _project_pbxproj())
    _write_text_if_changed(
        PROJECT_PATH / "project.xcworkspace" / "contents.xcworkspacedata",
        _workspace_data(),
    )
    SCHEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    _write_text_if_changed(
        SCHEME_FILE,
        _scheme(APP_TARGET_ID, TARGET_NAME, PRODUCT_NAME, include_tests=True),
    )
    _write_text_if_changed(
        SCHEME_FILE.parent / f"{IOS_TARGET_NAME}.xcscheme",
        _scheme(IOS_TARGET_ID, IOS_TARGET_NAME, IOS_PRODUCT_NAME, include_tests=False),
    )
    return PROJECT_PATH


def _write_text_if_changed(path: Path, text: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(text, encoding="utf-8")
    temporary_path.replace(path)


def _workspace_data() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Workspace
   version = "1.0">
   <FileRef
      location = "self:">
   </FileRef>
</Workspace>
"""


def _strip_jsonc_comments(text: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index < len(text) - 1:
                if text[index] == "*" and text[index + 1] == "/":
                    index += 2
                    break
                result.append(text[index] if text[index] in "\r\n" else " ")
                index += 1
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _strip_jsonc_trailing_commas(text: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue
        result.append(char)
        index += 1
    return "".join(result)


def _active_app_configs() -> dict[str, str]:
    if not SOURCE_ROOTS_ACTIVE_LOCK.is_file():
        return {"MARKETING_VERSION": "0.0.0", "ARCHIVE_ID": "1", DEVELOPMENT_TEAM_KEY: ""}
    payload = json.loads(
        _strip_jsonc_trailing_commas(
            _strip_jsonc_comments(SOURCE_ROOTS_ACTIVE_LOCK.read_text(encoding="utf-8"))
        )
    )
    app_configs = payload.get("AppConfigs", {}) if isinstance(payload, dict) else {}
    marketing_version = str(app_configs.get("MARKETING_VERSION", "0.0.0")).strip() or "0.0.0"
    archive_id = str(app_configs.get("ARCHIVE_ID", "1")).strip() or "1"
    development_team = str(app_configs.get(DEVELOPMENT_TEAM_KEY, "")).strip()
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}(?:[A-Za-z0-9.+-]*)?", marketing_version):
        marketing_version = "0.0.0"
    if not archive_id.isdigit() or int(archive_id) <= 0:
        archive_id = "1"
    if development_team and not re.fullmatch(r"[A-Za-z0-9]{10}", development_team):
        development_team = ""
    return {
        "MARKETING_VERSION": marketing_version,
        "ARCHIVE_ID": archive_id,
        DEVELOPMENT_TEAM_KEY: development_team,
    }


class _IdFactory:
    def __init__(self) -> None:
        self._value = 0

    def make(self) -> str:
        self._value += 1
        return f"A2T{self._value:021X}"


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _pbx_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _file_type(path: Path) -> str:
    if path.suffix == ".swift":
        return "sourcecode.swift"
    if path.suffix == ".json":
        return "text.json"
    if path.suffix == ".xcprivacy":
        return "text.xml"
    if path.suffix == ".entitlements":
        return "text.plist.entitlements"
    if path.name == "Package.swift":
        return "sourcecode.swift"
    return "text"


def _is_ios_shared_app_source(path: Path) -> bool:
    if path.suffix != ".swift":
        return False
    try:
        header = path.read_text(encoding="utf-8", errors="ignore")[:512]
    except OSError:
        return False
    return IOS_SHARED_SOURCE_MARKER in header


def _project_pbxproj() -> str:
    ids = _IdFactory()
    app_configs = _active_app_configs()
    core_source_files = sorted(CORE_SOURCE_DIR.glob("*.swift"))
    source_files = sorted(APP_SOURCE_DIR.glob("*.swift"))
    ios_source_files = sorted(IOS_SOURCE_DIR.glob("*.swift"))
    test_files = sorted(APP_TEST_DIR.glob("*.swift"))

    core_file_refs: list[tuple[str, Path]] = []
    app_core_build_files: list[tuple[str, str, Path]] = []
    ios_core_build_files: list[tuple[str, str, Path]] = []
    for path in core_source_files:
        file_id = ids.make()
        app_build_id = ids.make()
        ios_build_id = ids.make()
        core_file_refs.append((file_id, path))
        app_core_build_files.append((app_build_id, file_id, path))
        ios_core_build_files.append((ios_build_id, file_id, path))

    app_file_refs: list[tuple[str, Path]] = []
    app_build_files: list[tuple[str, str, Path]] = []
    ios_shared_app_build_files: list[tuple[str, str, Path]] = []
    for path in source_files:
        file_id = ids.make()
        build_id = ids.make()
        app_file_refs.append((file_id, path))
        app_build_files.append((build_id, file_id, path))
        if _is_ios_shared_app_source(path):
            ios_build_id = ids.make()
            ios_shared_app_build_files.append((ios_build_id, file_id, path))

    ios_file_refs: list[tuple[str, Path]] = []
    ios_build_files: list[tuple[str, str, Path]] = []
    for path in ios_source_files:
        file_id = ids.make()
        build_id = ids.make()
        ios_file_refs.append((file_id, path))
        ios_build_files.append((build_id, file_id, path))

    test_file_refs: list[tuple[str, Path]] = []
    test_build_files: list[tuple[str, str, Path]] = []
    for path in test_files:
        file_id = ids.make()
        build_id = ids.make()
        test_file_refs.append((file_id, path))
        test_build_files.append((build_id, file_id, path))

    package_ref = ids.make()
    entitlements_ref = ids.make()
    ios_entitlements_ref = ids.make()
    ios_info_plist_ref = ids.make()
    privacy_ref = ids.make()
    privacy_build = ids.make()
    ios_privacy_build = ids.make()
    ios_asset_catalog_ref = ids.make()
    ios_asset_catalog_build = ids.make()
    inventory_ref = ids.make()
    product_ref = ids.make()
    ios_product_ref = ids.make()
    test_product_ref = ids.make()
    app_group = ids.make()
    core_sources_group = ids.make()
    app_sources_group = ids.make()
    ios_sources_group = ids.make()
    app_tests_group = ids.make()
    products_group = ids.make()
    root_group = ids.make()
    app_sources_phase = ids.make()
    app_frameworks_phase = ids.make()
    app_resources_phase = ids.make()
    app_runtime_phase = ids.make()
    ios_sources_phase = ids.make()
    ios_frameworks_phase = ids.make()
    ios_resources_phase = ids.make()
    test_sources_phase = ids.make()
    test_frameworks_phase = ids.make()
    test_resources_phase = ids.make()
    target_dependency = ids.make()
    target_proxy = ids.make()
    app_target = APP_TARGET_ID
    ios_target = IOS_TARGET_ID
    test_target = TEST_TARGET_ID
    project_id = ids.make()
    project_debug = ids.make()
    project_release = ids.make()
    app_debug = ids.make()
    app_release = ids.make()
    ios_debug = ids.make()
    ios_release = ids.make()
    test_debug = ids.make()
    test_release = ids.make()
    project_config_list = ids.make()
    app_config_list = ids.make()
    ios_config_list = ids.make()
    test_config_list = ids.make()

    build_files = [
        f"\t\t{build_id} /* {path.name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_id} /* {path.name} */; }};"
        for build_id, file_id, path in [*app_core_build_files, *app_build_files]
    ]
    build_files.extend(
        f"\t\t{build_id} /* {path.name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_id} /* {path.name} */; }};"
        for build_id, file_id, path in [
            *ios_core_build_files,
            *ios_shared_app_build_files,
            *ios_build_files,
        ]
    )
    build_files.extend(
        f"\t\t{build_id} /* {path.name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_id} /* {path.name} */; }};"
        for build_id, file_id, path in test_build_files
    )
    build_files.append(
        f"\t\t{privacy_build} /* PrivacyInfo.xcprivacy in Resources */ = {{isa = PBXBuildFile; fileRef = {privacy_ref} /* PrivacyInfo.xcprivacy */; }};"
    )
    build_files.append(
        f"\t\t{ios_privacy_build} /* PrivacyInfo.xcprivacy in Resources */ = {{isa = PBXBuildFile; fileRef = {privacy_ref} /* PrivacyInfo.xcprivacy */; }};"
    )
    build_files.append(
        f"\t\t{ios_asset_catalog_build} /* Audio2Text.xcassets in Resources */ = {{isa = PBXBuildFile; fileRef = {ios_asset_catalog_ref} /* Audio2Text.xcassets */; }};"
    )

    file_refs = [
        f'\t\t{package_ref} /* Package.swift */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = Package.swift; sourceTree = "<group>"; }};',
        f"\t\t{entitlements_ref} /* Audio2TextApp.entitlements */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = {APP_ENTITLEMENTS}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{ios_entitlements_ref} /* Audio2TextiOS.entitlements */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.entitlements; path = {IOS_ENTITLEMENTS}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{ios_info_plist_ref} /* Audio2TextiOS-Info.plist */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = {IOS_INFO_PLIST}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{privacy_ref} /* PrivacyInfo.xcprivacy */ = {{isa = PBXFileReference; lastKnownFileType = text.xml; path = {APP_PRIVACY_MANIFEST}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{ios_asset_catalog_ref} /* Audio2Text.xcassets */ = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = {IOS_ASSET_CATALOG}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{inventory_ref} /* model_inventory.json */ = {{isa = PBXFileReference; lastKnownFileType = text.json; path = {MODEL_INVENTORY}; sourceTree = SOURCE_ROOT; }};",
        f"\t\t{product_ref} /* {PRODUCT_NAME}.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = {PRODUCT_NAME}.app; sourceTree = BUILT_PRODUCTS_DIR; }};",
        f"\t\t{ios_product_ref} /* {IOS_PRODUCT_NAME}.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = {IOS_PRODUCT_NAME}.app; sourceTree = BUILT_PRODUCTS_DIR; }};",
        f"\t\t{test_product_ref} /* {TEST_TARGET_NAME}.xctest */ = {{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = {TEST_TARGET_NAME}.xctest; sourceTree = BUILT_PRODUCTS_DIR; }};",
    ]
    file_refs.extend(
        f"\t\t{file_id} /* {path.name} */ = {{isa = PBXFileReference; lastKnownFileType = {_file_type(path)}; path = {_quote(_pbx_path(path))}; sourceTree = SOURCE_ROOT; }};"
        for file_id, path in [*core_file_refs, *app_file_refs, *ios_file_refs, *test_file_refs]
    )

    core_children = "\n".join(
        f"\t\t\t\t{file_id} /* {path.name} */," for file_id, path in core_file_refs
    )
    source_children = "\n".join(
        f"\t\t\t\t{file_id} /* {path.name} */," for file_id, path in app_file_refs
    )
    ios_children = "\n".join(
        f"\t\t\t\t{file_id} /* {path.name} */," for file_id, path in ios_file_refs
    )
    test_children = "\n".join(
        f"\t\t\t\t{file_id} /* {path.name} */," for file_id, path in test_file_refs
    )
    product_children = f"""
\t\t\t\t{product_ref} /* {PRODUCT_NAME}.app */,
\t\t\t\t{ios_product_ref} /* {IOS_PRODUCT_NAME}.app */,
\t\t\t\t{test_product_ref} /* {TEST_TARGET_NAME}.xctest */,"""
    app_source_build_children = "\n".join(
        f"\t\t\t\t{build_id} /* {path.name} in Sources */,"
        for build_id, _, path in [*app_core_build_files, *app_build_files]
    )
    ios_source_build_children = "\n".join(
        f"\t\t\t\t{build_id} /* {path.name} in Sources */,"
        for build_id, _, path in [
            *ios_core_build_files,
            *ios_shared_app_build_files,
            *ios_build_files,
        ]
    )
    test_source_build_children = "\n".join(
        f"\t\t\t\t{build_id} /* {path.name} in Sources */,"
        for build_id, _, path in test_build_files
    )

    runtime_script = r"""set -euo pipefail
cd "$SRCROOT"
resources="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
mkdir -p "$resources"
cp "src/atot/data/model_inventory.json" "$resources/model_inventory.json"
macos="$TARGET_BUILD_DIR/$EXECUTABLE_FOLDER_PATH"
if [ -x "$TARGET_BUILD_DIR/$EXECUTABLE_PATH" ]; then
  cli="$macos/Audio2TextCli"
  cp "$TARGET_BUILD_DIR/$EXECUTABLE_PATH" "$cli"
  chmod 755 "$cli"
  if [ "${CODE_SIGNING_ALLOWED:-NO}" = "YES" ]; then
    identity="${EXPANDED_CODE_SIGN_IDENTITY:--}"
    if [ -z "$identity" ]; then
      identity="-"
    fi
    /usr/bin/codesign --force --sign "$identity" --timestamp=none --options runtime "$cli"
  fi
fi
python_bin="$HOME/Documents/SpeechToTextData/env/bin/python"
if [ -x "$python_bin" ]; then
  "$python_bin" -m pip wheel --no-build-isolation --no-deps --wheel-dir "$SRCROOT/build/wheelhouse" "$SRCROOT"
  wheel="$(ls -t "$SRCROOT"/build/wheelhouse/audio2text_local-*.whl | head -n 1)"
  cp "$wheel" "$resources/"
else
  echo "warning: SonaFolio Python runtime env is missing; run python3 configs/setup_local_app.py" >&2
fi
"""

    return f"""// !$*UTF8*$!
{{
\tarchiveVersion = 1;
\tclasses = {{
\t}};
\tobjectVersion = 56;
\tobjects = {{

/* Begin PBXBuildFile section */
{chr(10).join(build_files)}
/* End PBXBuildFile section */

/* Begin PBXContainerItemProxy section */
\t\t{target_proxy} /* PBXContainerItemProxy */ = {{
\t\t\tisa = PBXContainerItemProxy;
\t\t\tcontainerPortal = {project_id} /* Project object */;
\t\t\tproxyType = 1;
\t\t\tremoteGlobalIDString = {app_target};
\t\t\tremoteInfo = {TARGET_NAME};
\t\t}};
/* End PBXContainerItemProxy section */

/* Begin PBXFileReference section */
{chr(10).join(file_refs)}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
\t\t{app_frameworks_phase} /* Frameworks */ = {{
\t\t\tisa = PBXFrameworksBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{test_frameworks_phase} /* Frameworks */ = {{
\t\t\tisa = PBXFrameworksBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{ios_frameworks_phase} /* Frameworks */ = {{
\t\t\tisa = PBXFrameworksBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
\t\t{root_group} = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t{app_group} /* app */,
\t\t\t\t{inventory_ref} /* model_inventory.json */,
\t\t\t\t{products_group} /* Products */,
\t\t\t);
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{app_group} /* app */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t{package_ref} /* Package.swift */,
\t\t\t\t{entitlements_ref} /* Audio2TextApp.entitlements */,
\t\t\t\t{ios_entitlements_ref} /* Audio2TextiOS.entitlements */,
\t\t\t\t{ios_info_plist_ref} /* Audio2TextiOS-Info.plist */,
\t\t\t\t{privacy_ref} /* PrivacyInfo.xcprivacy */,
\t\t\t\t{ios_asset_catalog_ref} /* Audio2Text.xcassets */,
\t\t\t\t{core_sources_group} /* Audio2TextCore */,
\t\t\t\t{app_sources_group} /* Sources */,
\t\t\t\t{ios_sources_group} /* iOS */,
\t\t\t\t{app_tests_group} /* Tests */,
\t\t\t);
\t\t\tpath = app;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{app_sources_group} /* Sources */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{source_children}
\t\t\t);
\t\t\tpath = Sources/Audio2TextApp;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{core_sources_group} /* Audio2TextCore */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{core_children}
\t\t\t);
\t\t\tpath = Sources/Audio2TextCore;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{ios_sources_group} /* iOS */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{ios_children}
\t\t\t);
\t\t\tpath = Sources/Audio2TextiOS;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{app_tests_group} /* Tests */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{test_children}
\t\t\t);
\t\t\tpath = Tests/Audio2TextAppTests;
\t\t\tsourceTree = "<group>";
\t\t}};
\t\t{products_group} /* Products */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{product_children}
\t\t\t);
\t\t\tname = Products;
\t\t\tsourceTree = "<group>";
\t\t}};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
\t\t{app_target} /* {TARGET_NAME} */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = {app_config_list} /* Build configuration list for PBXNativeTarget "{TARGET_NAME}" */;
\t\t\tbuildPhases = (
\t\t\t\t{app_sources_phase} /* Sources */,
\t\t\t\t{app_frameworks_phase} /* Frameworks */,
\t\t\t\t{app_resources_phase} /* Resources */,
\t\t\t\t{app_runtime_phase} /* Bundle Runtime */,
\t\t\t);
\t\t\tbuildRules = (
\t\t\t);
\t\t\tdependencies = (
\t\t\t);
\t\t\tname = {TARGET_NAME};
\t\t\tproductName = {PRODUCT_NAME};
\t\t\tproductReference = {product_ref} /* {PRODUCT_NAME}.app */;
\t\t\tproductType = "com.apple.product-type.application";
\t\t}};
\t\t{ios_target} /* {IOS_TARGET_NAME} */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = {ios_config_list} /* Build configuration list for PBXNativeTarget "{IOS_TARGET_NAME}" */;
\t\t\tbuildPhases = (
\t\t\t\t{ios_sources_phase} /* Sources */,
\t\t\t\t{ios_frameworks_phase} /* Frameworks */,
\t\t\t\t{ios_resources_phase} /* Resources */,
\t\t\t);
\t\t\tbuildRules = (
\t\t\t);
\t\t\tdependencies = (
\t\t\t);
\t\t\tname = "{IOS_TARGET_NAME}";
\t\t\tproductName = "{IOS_PRODUCT_NAME}";
\t\t\tproductReference = {ios_product_ref} /* {IOS_PRODUCT_NAME}.app */;
\t\t\tproductType = "com.apple.product-type.application";
\t\t}};
\t\t{test_target} /* {TEST_TARGET_NAME} */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = {test_config_list} /* Build configuration list for PBXNativeTarget "{TEST_TARGET_NAME}" */;
\t\t\tbuildPhases = (
\t\t\t\t{test_sources_phase} /* Sources */,
\t\t\t\t{test_frameworks_phase} /* Frameworks */,
\t\t\t\t{test_resources_phase} /* Resources */,
\t\t\t);
\t\t\tbuildRules = (
\t\t\t);
\t\t\tdependencies = (
\t\t\t\t{target_dependency} /* PBXTargetDependency */,
\t\t\t);
\t\t\tname = {TEST_TARGET_NAME};
\t\t\tproductName = {TEST_TARGET_NAME};
\t\t\tproductReference = {test_product_ref} /* {TEST_TARGET_NAME}.xctest */;
\t\t\tproductType = "com.apple.product-type.bundle.unit-test";
\t\t}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
\t\t{project_id} /* Project object */ = {{
\t\t\tisa = PBXProject;
\t\t\tattributes = {{
\t\t\t\tBuildIndependentTargetsInParallel = 1;
\t\t\t\tLastSwiftUpdateCheck = {XCODE_LAST_UPGRADE_CHECK};
\t\t\t\tLastUpgradeCheck = {XCODE_LAST_UPGRADE_CHECK};
\t\t\t\tTargetAttributes = {{
\t\t\t\t\t{app_target} = {{
\t\t\t\t\t\tCreatedOnToolsVersion = {XCODE_CREATED_ON_TOOLS_VERSION};
\t\t\t\t\t}};
\t\t\t\t\t{ios_target} = {{
\t\t\t\t\t\tCreatedOnToolsVersion = {XCODE_CREATED_ON_TOOLS_VERSION};
\t\t\t\t\t}};
\t\t\t\t\t{test_target} = {{
\t\t\t\t\t\tCreatedOnToolsVersion = {XCODE_CREATED_ON_TOOLS_VERSION};
\t\t\t\t\t\tTestTargetID = {app_target};
\t\t\t\t\t}};
\t\t\t\t}};
\t\t\t}};
\t\t\tbuildConfigurationList = {project_config_list} /* Build configuration list for PBXProject "Audio2Text" */;
\t\t\tcompatibilityVersion = "Xcode 14.0";
\t\t\tdevelopmentRegion = en;
\t\t\thasScannedForEncodings = 0;
\t\t\tknownRegions = (
\t\t\t\ten,
\t\t\t\tBase,
\t\t\t);
\t\t\tmainGroup = {root_group};
\t\t\tproductRefGroup = {products_group} /* Products */;
\t\t\tprojectDirPath = "";
\t\t\tprojectRoot = "";
\t\t\ttargets = (
\t\t\t\t{app_target} /* {TARGET_NAME} */,
\t\t\t\t{ios_target} /* {IOS_TARGET_NAME} */,
\t\t\t\t{test_target} /* {TEST_TARGET_NAME} */,
\t\t\t);
\t\t}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
\t\t{app_resources_phase} /* Resources */ = {{
\t\t\tisa = PBXResourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t\t{privacy_build} /* PrivacyInfo.xcprivacy in Resources */,
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{ios_resources_phase} /* Resources */ = {{
\t\t\tisa = PBXResourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t\t{ios_privacy_build} /* PrivacyInfo.xcprivacy in Resources */,
\t\t\t\t{ios_asset_catalog_build} /* Audio2Text.xcassets in Resources */,
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{test_resources_phase} /* Resources */ = {{
\t\t\tisa = PBXResourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXShellScriptBuildPhase section */
\t\t{app_runtime_phase} /* Bundle Runtime */ = {{
\t\t\tisa = PBXShellScriptBuildPhase;
\t\t\talwaysOutOfDate = 1;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
\t\t\t);
\t\t\tinputPaths = (
\t\t\t\t"$(SRCROOT)/pyproject.toml",
\t\t\t\t"$(SRCROOT)/src/atot/data/model_inventory.json",
\t\t\t);
\t\t\tname = "Bundle Runtime";
\t\t\toutputPaths = (
\t\t\t\t"$(TARGET_BUILD_DIR)/$(EXECUTABLE_FOLDER_PATH)/{CLI_NAME}",
\t\t\t\t"$(TARGET_BUILD_DIR)/$(UNLOCALIZED_RESOURCES_FOLDER_PATH)/model_inventory.json",
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t\tshellPath = /bin/sh;
\t\t\tshellScript = {_quote(runtime_script)};
\t\t}};
/* End PBXShellScriptBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
\t\t{app_sources_phase} /* Sources */ = {{
\t\t\tisa = PBXSourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{app_source_build_children}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{ios_sources_phase} /* Sources */ = {{
\t\t\tisa = PBXSourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{ios_source_build_children}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
\t\t{test_sources_phase} /* Sources */ = {{
\t\t\tisa = PBXSourcesBuildPhase;
\t\t\tbuildActionMask = 2147483647;
\t\t\tfiles = (
{test_source_build_children}
\t\t\t);
\t\t\trunOnlyForDeploymentPostprocessing = 0;
\t\t}};
/* End PBXSourcesBuildPhase section */

/* Begin PBXTargetDependency section */
\t\t{target_dependency} /* PBXTargetDependency */ = {{
\t\t\tisa = PBXTargetDependency;
\t\t\ttarget = {app_target} /* {TARGET_NAME} */;
\t\t\ttargetProxy = {target_proxy} /* PBXContainerItemProxy */;
\t\t}};
/* End PBXTargetDependency section */

/* Begin XCBuildConfiguration section */
{_build_configuration(project_debug, "Debug", _project_build_settings(app_configs, configuration="debug"))}
{_build_configuration(project_release, "Release", _project_build_settings(app_configs, configuration="release"))}
{_build_configuration(app_debug, "Debug", _app_build_settings(app_configs, configuration="debug"))}
{_build_configuration(app_release, "Release", _app_build_settings(app_configs, configuration="release"))}
{_build_configuration(ios_debug, "Debug", _ios_build_settings(app_configs, configuration="debug"))}
{_build_configuration(ios_release, "Release", _ios_build_settings(app_configs, configuration="release"))}
{_build_configuration(test_debug, "Debug", _test_build_settings(app_configs, configuration="debug"))}
{_build_configuration(test_release, "Release", _test_build_settings(app_configs, configuration="release"))}
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
\t\t{project_config_list} /* Build configuration list for PBXProject "Audio2Text" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{project_debug} /* Debug */,
\t\t\t\t{project_release} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
\t\t{app_config_list} /* Build configuration list for PBXNativeTarget "{TARGET_NAME}" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{app_debug} /* Debug */,
\t\t\t\t{app_release} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
\t\t{ios_config_list} /* Build configuration list for PBXNativeTarget "{IOS_TARGET_NAME}" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{ios_debug} /* Debug */,
\t\t\t\t{ios_release} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
\t\t{test_config_list} /* Build configuration list for PBXNativeTarget "{TEST_TARGET_NAME}" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t{test_debug} /* Debug */,
\t\t\t\t{test_release} /* Release */,
\t\t\t);
\t\t\tdefaultConfigurationIsVisible = 0;
\t\t\tdefaultConfigurationName = Release;
\t\t}};
/* End XCConfigurationList section */
\t}};
\trootObject = {project_id} /* Project object */;
}}
"""


def _project_build_settings(app_configs: dict[str, str], *, configuration: str) -> dict[str, str]:
    settings = {
        "ALWAYS_SEARCH_USER_PATHS": "NO",
        "ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS": "YES",
        "CLANG_ANALYZER_NONNULL": "YES",
        "CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION": "YES_AGGRESSIVE",
        "CLANG_CXX_LANGUAGE_STANDARD": "gnu++20",
        "CLANG_ENABLE_MODULES": "YES",
        "CLANG_ENABLE_OBJC_ARC": "YES",
        "CLANG_ENABLE_OBJC_WEAK": "YES",
        "CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING": "YES",
        "CLANG_WARN_BOOL_CONVERSION": "YES",
        "CLANG_WARN_COMMA": "YES",
        "CLANG_WARN_CONSTANT_CONVERSION": "YES",
        "CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS": "YES",
        "CLANG_WARN_DIRECT_OBJC_ISA_USAGE": "YES_ERROR",
        "CLANG_WARN_DOCUMENTATION_COMMENTS": "YES",
        "CLANG_WARN_EMPTY_BODY": "YES",
        "CLANG_WARN_ENUM_CONVERSION": "YES",
        "CLANG_WARN_INFINITE_RECURSION": "YES",
        "CLANG_WARN_INT_CONVERSION": "YES",
        "CLANG_WARN_NON_LITERAL_NULL_CONVERSION": "YES",
        "CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF": "YES",
        "CLANG_WARN_OBJC_LITERAL_CONVERSION": "YES",
        "CLANG_WARN_OBJC_ROOT_CLASS": "YES_ERROR",
        "CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER": "YES",
        "CLANG_WARN_RANGE_LOOP_ANALYSIS": "YES",
        "CLANG_WARN_STRICT_PROTOTYPES": "YES",
        "CLANG_WARN_SUSPICIOUS_MOVE": "YES",
        "CLANG_WARN_UNGUARDED_AVAILABILITY": "YES_AGGRESSIVE",
        "CLANG_WARN_UNREACHABLE_CODE": "YES",
        "CLANG_WARN__DUPLICATE_METHOD_MATCH": "YES",
        "COPY_PHASE_STRIP": "NO",
        "DEAD_CODE_STRIPPING": "YES",
        "ENABLE_STRICT_OBJC_MSGSEND": "YES",
        "ENABLE_USER_SCRIPT_SANDBOXING": "NO",
        "GCC_C_LANGUAGE_STANDARD": "gnu17",
        "GCC_NO_COMMON_BLOCKS": "YES",
        "GCC_WARN_64_TO_32_BIT_CONVERSION": "YES",
        "GCC_WARN_ABOUT_RETURN_TYPE": "YES_ERROR",
        "GCC_WARN_UNDECLARED_SELECTOR": "YES",
        "GCC_WARN_UNINITIALIZED_AUTOS": "YES_AGGRESSIVE",
        "GCC_WARN_UNUSED_FUNCTION": "YES",
        "GCC_WARN_UNUSED_VARIABLE": "YES",
        "MACOSX_DEPLOYMENT_TARGET": "13.0",
        "SDKROOT": "macosx",
        "STRING_CATALOG_GENERATE_SYMBOLS": "YES",
        "SWIFT_VERSION": "5.0",
    }
    _apply_development_team(settings, app_configs)
    if configuration == "debug":
        settings.update(
            {
                "ENABLE_TESTABILITY": "YES",
                "ONLY_ACTIVE_ARCH": "YES",
            }
        )
    return settings


def _apply_development_team(settings: dict[str, str], app_configs: dict[str, str]) -> None:
    development_team = app_configs.get(DEVELOPMENT_TEAM_KEY, "").strip()
    if development_team:
        settings["DEVELOPMENT_TEAM"] = development_team


def _app_build_settings(app_configs: dict[str, str], *, configuration: str) -> dict[str, str]:
    settings = {
        "ASSETCATALOG_COMPILER_APPICON_NAME": "",
        "CODE_SIGN_STYLE": "Automatic",
        "COMBINE_HIDPI_IMAGES": "YES",
        "CURRENT_PROJECT_VERSION": app_configs["ARCHIVE_ID"],
        "DEAD_CODE_STRIPPING": "YES",
        "ENABLE_HARDENED_RUNTIME": "YES",
        "ENABLE_PREVIEWS": "YES",
        "GENERATE_INFOPLIST_FILE": "YES",
        "INFOPLIST_KEY_CFBundleDisplayName": PRODUCT_NAME,
        "INFOPLIST_KEY_CFBundleIconFile": "",
        "INFOPLIST_KEY_LSApplicationCategoryType": "public.app-category.productivity",
        "INFOPLIST_KEY_NSHighResolutionCapable": "YES",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/../Frameworks",
        # This target defines no App Intents; skip the unused metadata build step.
        "LM_SKIP_METADATA_EXTRACTION": "YES",
        "MARKETING_VERSION": app_configs["MARKETING_VERSION"],
        "PRODUCT_BUNDLE_IDENTIFIER": BUNDLE_IDENTIFIER,
        "PRODUCT_NAME": PRODUCT_NAME,
        "SUPPORTED_PLATFORMS": "macosx",
        "SUPPORTS_MACCATALYST": "NO",
        "SWIFT_EMIT_LOC_STRINGS": "YES",
        "SWIFT_VERSION": "5.0",
    }
    _apply_development_team(settings, app_configs)
    if configuration == "debug":
        settings.update(
            {
                "COPY_PHASE_STRIP": "NO",
                "DEBUG_INFORMATION_FORMAT": "dwarf",
                "ENABLE_TESTABILITY": "YES",
                "GCC_DYNAMIC_NO_PIC": "NO",
                "GCC_OPTIMIZATION_LEVEL": "0",
                "MTL_ENABLE_DEBUG_INFO": "INCLUDE_SOURCE",
                "ONLY_ACTIVE_ARCH": "YES",
                "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
                "SWIFT_OPTIMIZATION_LEVEL": "-Onone",
            }
        )
    else:
        settings.update(
            {
                "COPY_PHASE_STRIP": "NO",
                "DEBUG_INFORMATION_FORMAT": "dwarf-with-dsym",
                "MTL_ENABLE_DEBUG_INFO": "NO",
                "SWIFT_COMPILATION_MODE": "wholemodule",
                "SWIFT_OPTIMIZATION_LEVEL": "-O",
            }
        )
    return settings


def _ios_build_settings(app_configs: dict[str, str], *, configuration: str) -> dict[str, str]:
    settings = {
        "ASSETCATALOG_COMPILER_APPICON_NAME": "AppIcon",
        "CODE_SIGN_ENTITLEMENTS": IOS_ENTITLEMENTS,
        "CODE_SIGN_STYLE": "Automatic",
        "CURRENT_PROJECT_VERSION": app_configs["ARCHIVE_ID"],
        "DEAD_CODE_STRIPPING": "YES",
        "ENABLE_PREVIEWS": "YES",
        "GENERATE_INFOPLIST_FILE": "NO",
        "INFOPLIST_FILE": IOS_INFO_PLIST,
        "IPHONEOS_DEPLOYMENT_TARGET": "17.0",
        "LD_RUNPATH_SEARCH_PATHS": "$(inherited) @executable_path/Frameworks",
        # This target defines no App Intents; skip the unused metadata build step.
        "LM_SKIP_METADATA_EXTRACTION": "YES",
        "MARKETING_VERSION": app_configs["MARKETING_VERSION"],
        "PRODUCT_BUNDLE_IDENTIFIER": IOS_BUNDLE_IDENTIFIER,
        "PRODUCT_NAME": IOS_PRODUCT_NAME,
        "SDKROOT": "iphoneos",
        "SUPPORTED_PLATFORMS": "iphoneos iphonesimulator",
        "SUPPORTS_MACCATALYST": "NO",
        "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD": "NO",
        "SWIFT_EMIT_LOC_STRINGS": "YES",
        "SWIFT_VERSION": "5.0",
        "TARGETED_DEVICE_FAMILY": "1,2",
    }
    _apply_development_team(settings, app_configs)
    if configuration == "debug":
        settings.update(
            {
                "COPY_PHASE_STRIP": "NO",
                "DEBUG_INFORMATION_FORMAT": "dwarf",
                "ENABLE_TESTABILITY": "YES",
                "GCC_DYNAMIC_NO_PIC": "NO",
                "GCC_OPTIMIZATION_LEVEL": "0",
                "MTL_ENABLE_DEBUG_INFO": "INCLUDE_SOURCE",
                "ONLY_ACTIVE_ARCH": "YES",
                "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
                "SWIFT_OPTIMIZATION_LEVEL": "-Onone",
            }
        )
    else:
        settings.update(
            {
                "COPY_PHASE_STRIP": "NO",
                "DEBUG_INFORMATION_FORMAT": "dwarf-with-dsym",
                "MTL_ENABLE_DEBUG_INFO": "NO",
                "SWIFT_COMPILATION_MODE": "wholemodule",
                "SWIFT_OPTIMIZATION_LEVEL": "-O",
            }
        )
    return settings


def _test_build_settings(app_configs: dict[str, str], *, configuration: str) -> dict[str, str]:
    settings = {
        "BUNDLE_LOADER": "$(TEST_HOST)",
        "CODE_SIGN_STYLE": "Automatic",
        "CURRENT_PROJECT_VERSION": app_configs["ARCHIVE_ID"],
        "DEAD_CODE_STRIPPING": "YES",
        "GENERATE_INFOPLIST_FILE": "YES",
        "MARKETING_VERSION": app_configs["MARKETING_VERSION"],
        "PRODUCT_BUNDLE_IDENTIFIER": TEST_BUNDLE_IDENTIFIER,
        "PRODUCT_NAME": "$(TARGET_NAME)",
        "SUPPORTED_PLATFORMS": "macosx",
        "SWIFT_VERSION": "5.0",
        "TEST_HOST": "$(BUILT_PRODUCTS_DIR)/SonaFolio.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/SonaFolio",
    }
    _apply_development_team(settings, app_configs)
    if configuration == "debug":
        settings.update(
            {
                "DEBUG_INFORMATION_FORMAT": "dwarf",
                "ENABLE_TESTABILITY": "YES",
                "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
                "SWIFT_OPTIMIZATION_LEVEL": "-Onone",
            }
        )
    else:
        settings.update(
            {
                "DEBUG_INFORMATION_FORMAT": "dwarf-with-dsym",
                "SWIFT_COMPILATION_MODE": "wholemodule",
                "SWIFT_OPTIMIZATION_LEVEL": "-O",
            }
        )
    return settings


def _build_configuration(config_id: str, name: str, settings: dict[str, str]) -> str:
    rendered_settings = "\n".join(
        f"\t\t\t\t{key} = {_quote(value) if _needs_quoting(value) else value};"
        for key, value in sorted(settings.items())
    )
    return f"""\t\t{config_id} /* {name} */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
{rendered_settings}
\t\t\t}};
\t\t\tname = {name};
\t\t}};"""


def _needs_quoting(value: str) -> bool:
    return value == "" or re.fullmatch(r"[A-Za-z0-9_]+", value) is None


def _scheme(target_id: str, target_name: str, product_name: str, *, include_tests: bool) -> str:
    test_action = (
        f"""
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">
      <Testables>
         <TestableReference
            skipped = "NO">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{TEST_TARGET_ID}"
               BuildableName = "{TEST_TARGET_NAME}.xctest"
               BlueprintName = "{TEST_TARGET_NAME}"
               ReferencedContainer = "container:Audio2Text.xcodeproj">
            </BuildableReference>
         </TestableReference>
      </Testables>
   </TestAction>"""
        if include_tests
        else """
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">
      <Testables>
      </Testables>
   </TestAction>"""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1500"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{target_id}"
               BuildableName = "{product_name}.app"
               BlueprintName = "{target_name}"
               ReferencedContainer = "container:Audio2Text.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
{test_action}
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "{target_id}"
            BuildableName = "{product_name}.app"
            BlueprintName = "{target_name}"
            ReferencedContainer = "container:Audio2Text.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "{target_id}"
            BuildableName = "{product_name}.app"
            BlueprintName = "{target_name}"
            ReferencedContainer = "container:Audio2Text.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""


def main() -> int:
    project = generate_xcodeproj()
    print(f"Generated local Xcode project: {project.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
