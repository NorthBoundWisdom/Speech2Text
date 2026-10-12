#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
APP_DIR = REPO_ROOT / "app"
PRODUCT_NAME = "Audio2TextApp"
CLI_NAME = "Audio2TextCli"
IOS_SCHEME_NAME = "Audio2Text-iOS"
BUILD_DIR = REPO_ROOT / "build"
SWIFTPM_BUILD_DIR = BUILD_DIR / "swiftpm"
APP_BUNDLE = BUILD_DIR / "app" / "Audio2Text.app"
PACKAGE_DIR = BUILD_DIR / "package"
WHEEL_DIR = BUILD_DIR / "wheelhouse"
DEFAULT_DATA_ROOT = Path("~/Documents/SpeechToTextData")
APP_ENTITLEMENTS = APP_DIR / "Audio2TextApp.entitlements"
APP_PRIVACY_MANIFEST = APP_DIR / "PrivacyInfo.xcprivacy"
MODEL_INVENTORY = REPO_ROOT / "src" / "atot" / "data" / "model_inventory.json"
SOURCE_ROOTS_ACTIVE_LOCK = REPO_ROOT / "source_roots.lock.jsonc"
IDENTITY_LINE_PATTERN = re.compile(r'^\s*\d+\)\s+([0-9A-Fa-f]{40})\s+"([^"]+)"')
NOTARY_PROFILE_ENV = "ATOT_NOTARY_KEYCHAIN_PROFILE"


def data_root() -> Path:
    return DEFAULT_DATA_ROOT.expanduser()


def _env_python() -> Path:
    if os.environ.get("ATOT_BUILD_PYTHON"):
        return Path(os.environ["ATOT_BUILD_PYTHON"])
    return data_root() / "env" / "bin" / "python"


def _ensure_local_app_config() -> None:
    _run(["python3", "configs/setup_local_app.py"])


def _run(cmd: list[str], *, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None) -> None:
    print(">>", " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(cmd)}")


def _swift_env() -> dict[str, str]:
    module_cache = SWIFTPM_BUILD_DIR / "module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    return {"CLANG_MODULE_CACHE_PATH": str(module_cache)}


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


def _load_jsonc(path: Path) -> object:
    text = _strip_jsonc_trailing_commas(_strip_jsonc_comments(path.read_text(encoding="utf-8")))
    return json.loads(text)


def _require_app_config_string(payload: dict[str, object], key: str, *, path: Path) -> str:
    app_configs = payload.get("AppConfigs")
    if not isinstance(app_configs, dict):
        raise RuntimeError(f"{path.name} is missing AppConfigs")
    value = app_configs.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{path.name} is missing AppConfigs.{key}")
    normalized = value.strip()
    if "\r" in normalized or "\n" in normalized:
        raise RuntimeError(f"{path.name} AppConfigs.{key} cannot contain newlines")
    return normalized


def _app_build_settings() -> dict[str, str]:
    release_version = os.environ.get("ATOT_RELEASE_VERSION", "")
    if release_version:
        if not re.fullmatch(r"\d+\.\d+\.\d+", release_version):
            raise RuntimeError("ATOT_RELEASE_VERSION must be a numeric major.minor.patch version.")
        return {"MARKETING_VERSION": release_version, "ARCHIVE_ID": "1"}
    path = SOURCE_ROOTS_ACTIVE_LOCK
    if not path.is_file():
        raise RuntimeError(
            "Missing active source_roots.lock.jsonc. Run `python3 configs/source_root_workflow.py --init` first."
        )
    try:
        payload = _load_jsonc(path)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON/JSONC in {path.name}: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name} must be an object")
    marketing_version = _require_app_config_string(payload, "MARKETING_VERSION", path=path)
    archive_id = _require_app_config_string(payload, "ARCHIVE_ID", path=path)
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}(?:[A-Za-z0-9.+-]*)?", marketing_version):
        raise RuntimeError(f"Unsupported MARKETING_VERSION in {path.name}: {marketing_version}")
    if not archive_id.isdigit() or int(archive_id) <= 0:
        raise RuntimeError(f"Unsupported ARCHIVE_ID in {path.name}: {archive_id}")
    return {
        "MARKETING_VERSION": marketing_version,
        "ARCHIVE_ID": archive_id,
    }


def _package_dmg_path(marketing_version: str, archive_id: str) -> Path:
    return PACKAGE_DIR / f"Audio2Text_v{marketing_version}_{archive_id}.dmg"


def _swift_build(configuration: str) -> Path:
    _run(
        [
            "swift",
            "build",
            "-c",
            configuration,
            "--scratch-path",
            str(SWIFTPM_BUILD_DIR),
            "--product",
            PRODUCT_NAME,
        ],
        cwd=APP_DIR,
        env=_swift_env(),
    )
    executable = SWIFTPM_BUILD_DIR / "debug" / PRODUCT_NAME
    if configuration == "release":
        executable = SWIFTPM_BUILD_DIR / "release" / PRODUCT_NAME
    if not executable.is_file():
        raise RuntimeError(f"Built executable not found: {executable}")
    return executable


def _xcode_configuration(configuration: str) -> str:
    return "Debug" if configuration == "debug" else "Release"


def _build_ios_simulator(configuration: str, *, scheme: str = IOS_SCHEME_NAME) -> None:
    _run(
        [
            "xcodebuild",
            "-project",
            "Audio2Text.xcodeproj",
            "-scheme",
            scheme,
            "-configuration",
            _xcode_configuration(configuration),
            "-sdk",
            "iphonesimulator",
            "-destination",
            "generic/platform=iOS Simulator",
            "build",
        ]
    )


def _selected_scheme(platform: str, requested: str) -> str:
    if platform == "ios" and requested == PRODUCT_NAME:
        return IOS_SCHEME_NAME
    return requested


def _package_app(configuration: str, *, distribution: str = "local") -> Path:
    wheel = _build_runtime_wheel()
    executable = _swift_build(configuration)
    build_settings = _app_build_settings()
    marketing_version = build_settings["MARKETING_VERSION"]
    archive_id = build_settings["ARCHIVE_ID"]
    contents = APP_BUNDLE / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    if APP_BUNDLE.exists():
        shutil.rmtree(APP_BUNDLE)
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, macos / PRODUCT_NAME)
    (macos / PRODUCT_NAME).chmod(0o755)
    shutil.copy2(executable, macos / CLI_NAME)
    (macos / CLI_NAME).chmod(0o755)
    from configs.release_licenses import copy_project_licenses
    copy_project_licenses(resources / "licenses")
    shutil.copy2(wheel, resources / wheel.name)
    shutil.copy2(MODEL_INVENTORY, resources / MODEL_INVENTORY.name)
    shutil.copy2(APP_PRIVACY_MANIFEST, resources / APP_PRIVACY_MANIFEST.name)
    icon = _build_app_icon()
    shutil.copy2(icon, resources / icon.name)
    plist = {
        "ATOTDistribution": distribution,
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": PRODUCT_NAME,
        "CFBundleIconFile": icon.name,
        "CFBundleIdentifier": "com.audio2text.local",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "Audio2Text",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": marketing_version,
        "CFBundleVersion": archive_id,
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
    }
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump(plist, handle)
    (contents / "PkgInfo").write_text("APPL????", encoding="ascii")
    if distribution == "ad-hoc":
        _run(["codesign", "--force", "--deep", "--sign", "-", str(APP_BUNDLE)])
        _run(["codesign", "--verify", "--deep", "--strict", str(APP_BUNDLE)])
    elif distribution == "development":
        _codesign_for_development(APP_BUNDLE)
    elif distribution == "developer-id":
        _codesign_for_developer_id(APP_BUNDLE)
    elif distribution == "app-store":
        _codesign_for_app_store_development(APP_BUNDLE)
        _validate_app_store_bundle(APP_BUNDLE)
    print(f"App version: {marketing_version}_{archive_id}")
    print(f"App bundle: {APP_BUNDLE}")
    return APP_BUNDLE


def _build_runtime_wheel() -> Path:
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    for old in WHEEL_DIR.glob("audio2text_local-*.whl"):
        old.unlink()
    python = _env_python()
    _run(
        [
            str(python),
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(WHEEL_DIR),
            ".",
        ]
    )
    wheels = sorted(WHEEL_DIR.glob("audio2text_local-*.whl"))
    if not wheels:
        raise RuntimeError(f"Runtime wheel was not produced under {WHEEL_DIR}")
    return wheels[-1]


def _build_app_icon() -> Path:
    iconset = BUILD_DIR / "Audio2Text.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True, exist_ok=True)
    _run(["swift", "configs/render_app_icon.swift", str(iconset)], env=_swift_env())
    icon = BUILD_DIR / "Audio2Text.icns"
    if icon.exists():
        icon.unlink()
    _run(["iconutil", "-c", "icns", str(iconset), "-o", str(icon)])
    return icon


def _dmg_app_bundle(app: Path) -> Path:
    if not app.is_dir():
        raise RuntimeError(f"App bundle not found: {app}")
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    build_settings = _app_build_settings()
    marketing_version = build_settings["MARKETING_VERSION"]
    archive_id = build_settings["ARCHIVE_ID"]
    package_dmg = _package_dmg_path(marketing_version, archive_id)
    if package_dmg.exists():
        package_dmg.unlink()
    hdiutil = shutil.which("hdiutil")
    if not hdiutil:
        raise RuntimeError("hdiutil is required to create a macOS DMG package.")
    staging_root = BUILD_DIR / "package-staging"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(app, staging_root / app.name, symlinks=True)
        (staging_root / "Applications").symlink_to("/Applications")
        _run(
            [
                hdiutil,
                "create",
                "-volname",
                f"Audio2Text {marketing_version}_{archive_id}",
                "-srcfolder",
                str(staging_root),
                "-ov",
                "-format",
                "UDZO",
                str(package_dmg),
            ]
        )
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    print(f"Package: {package_dmg}")
    return package_dmg


def _list_codesigning_identities() -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["security", "find-identity", "-v", "-p", "codesigning"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Failed to list code signing identities.")
    identities: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        match = IDENTITY_LINE_PATTERN.match(line)
        if match:
            identities.append((match.group(1), match.group(2)))
    return identities


def _select_development_identity() -> str:
    identities = _list_codesigning_identities()
    for prefix in ("Apple Development:", "Apple Dev:"):
        for sha1, name in identities:
            if name.startswith(prefix):
                return sha1
    raise RuntimeError(
        "No Apple Development code signing identity is available for local packaging."
    )


def _select_developer_id_identity() -> str:
    identities = _list_codesigning_identities()
    for sha1, name in identities:
        if name.startswith("Developer ID Application:"):
            return sha1
    raise RuntimeError(
        "No Developer ID Application code signing identity is available for website packaging."
    )


def _codesign_for_development(app: Path) -> None:
    _codesign_for_website(app, _select_development_identity(), secure_timestamp=False)


def _codesign_for_developer_id(app: Path) -> None:
    _codesign_for_website(app, _select_developer_id_identity(), secure_timestamp=True)


def _codesign_for_website(app: Path, identity: str, *, secure_timestamp: bool = False) -> None:
    timestamp_option = "--timestamp" if secure_timestamp else "--timestamp=none"
    executable = app / "Contents" / "MacOS" / PRODUCT_NAME
    if executable.is_file():
        _run(
            [
                "codesign",
                "--force",
                "--sign",
                identity,
                timestamp_option,
                "--options",
                "runtime",
                str(executable),
            ]
        )
    _run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign",
            identity,
            timestamp_option,
            "--options",
            "runtime",
            str(app),
        ]
    )
    _run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])


def _notary_profile(explicit_profile: str | None) -> str:
    profile = (explicit_profile or os.environ.get(NOTARY_PROFILE_ENV, "")).strip()
    if not profile:
        raise RuntimeError(
            "Developer ID packaging requires a notarytool Keychain profile. "
            f"Pass --notary-profile or set {NOTARY_PROFILE_ENV}."
        )
    if "\n" in profile or "\r" in profile:
        raise RuntimeError("The notarytool Keychain profile name cannot contain newlines.")
    return profile


def _notarize_dmg(package_dmg: Path, *, keychain_profile: str | None = None) -> None:
    if not package_dmg.is_file():
        raise RuntimeError(f"DMG package not found for notarization: {package_dmg}")
    profile = _notary_profile(keychain_profile)
    xcrun = shutil.which("xcrun")
    spctl = shutil.which("spctl")
    if not xcrun:
        raise RuntimeError("xcrun is required for Developer ID notarization.")
    if not spctl:
        raise RuntimeError("spctl is required for Developer ID package verification.")
    _run(
        [
            xcrun,
            "notarytool",
            "submit",
            str(package_dmg),
            "--keychain-profile",
            profile,
            "--wait",
        ]
    )
    _run([xcrun, "stapler", "staple", str(package_dmg)])
    _run([xcrun, "stapler", "validate", str(package_dmg)])
    _run(
        [
            spctl,
            "--assess",
            "--type",
            "open",
            "--context",
            "context:primary-signature",
            "--verbose=2",
            str(package_dmg),
        ]
    )


def _codesign_for_app_store_development(app: Path) -> None:
    _run(
        [
            "codesign",
            "--force",
            "--sign",
            "-",
            "--entitlements",
            str(APP_ENTITLEMENTS),
            "--options",
            "runtime",
            str(app),
        ]
    )


def _validate_app_store_bundle(app: Path) -> None:
    required = [
        app / "Contents" / "Info.plist",
        app / "Contents" / "MacOS" / CLI_NAME,
        app / "Contents" / "Resources" / "PrivacyInfo.xcprivacy",
        app / "Contents" / "Resources" / "model_inventory.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"App Store bundle is missing required files: {', '.join(missing)}")
    completed = subprocess.run(
        ["codesign", "-d", "--entitlements", ":-", str(app)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    entitlements = completed.stdout + completed.stderr
    for key in (
        "com.apple.security.app-sandbox",
        "com.apple.security.network.client",
        "com.apple.security.files.user-selected.read-only",
    ):
        if key not in entitlements:
            raise RuntimeError(f"App Store bundle is missing entitlement: {key}")


def _app_bundle_info(app: Path) -> dict[str, object]:
    info = app / "Contents" / "Info.plist"
    if not info.is_file():
        return {}
    with info.open("rb") as handle:
        payload = plistlib.load(handle)
    return payload if isinstance(payload, dict) else {}


def _app_bundle_identifier(app: Path) -> str | None:
    bundle_identifier = _app_bundle_info(app).get("CFBundleIdentifier")
    return bundle_identifier if isinstance(bundle_identifier, str) and bundle_identifier else None


def _app_bundle_executable_path(app: Path) -> Path:
    executable = _app_bundle_info(app).get("CFBundleExecutable")
    executable_name = executable if isinstance(executable, str) and executable else PRODUCT_NAME
    return app / "Contents" / "MacOS" / executable_name


def _running_pids_for_executable_name(executable_name: str) -> list[str]:
    completed = subprocess.run(
        ["pgrep", "-x", executable_name],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _test(level: str) -> None:
    _test_for_platform(level, platform="mac")


def _test_for_platform(level: str, *, platform: str) -> None:
    _ensure_local_app_config()
    python = _env_python()
    if level in {"logic", "precommit"}:
        _run(
            [
                str(python),
                "-m",
                "ruff",
                "check",
                "src",
                "configs",
            ]
        )
        _run([str(python), "src/scripts/check_public_paths.py"])
        _run([str(python), "-m", "pytest", "-q", "src/tests"], env={"PYTHONPATH": "src"})
        _run(["swift", "test", "--scratch-path", str(SWIFTPM_BUILD_DIR)], cwd=APP_DIR)
    if level in {"precommit", "xcode-builds"}:
        if platform == "ios":
            _build_ios_simulator("debug")
        else:
            _package_app("debug")


def _quit_running_app(bundle_identifier: str | None, executable_path: Path) -> None:
    if bundle_identifier:
        script = 'tell application id "{bundle_id}" to if it is running then quit'.format(
            bundle_id=bundle_identifier.replace('"', '\\"')
        )
        subprocess.run(["osascript", "-e", script], cwd=REPO_ROOT, text=True, check=False)
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if not _running_pids_for_executable_name(executable_path.name):
            return
        time.sleep(0.2)
    subprocess.run(["pkill", "-x", executable_path.name], cwd=REPO_ROOT, text=True, check=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audio2Text local app workflow")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--platform", default="mac", choices=["mac", "ios"])
    build.add_argument("--scheme", default=PRODUCT_NAME)
    build.add_argument("--configuration", default="debug", choices=["debug", "release"])
    build.add_argument(
        "--distribution",
        default="local",
        choices=["local", "ad-hoc", "development", "developer-id", "app-store"],
    )
    run = sub.add_parser("run")
    run.add_argument("--platform", default="mac", choices=["mac", "ios"])
    run.add_argument("--scheme", default=PRODUCT_NAME)
    run.add_argument("--configuration", default="debug", choices=["debug", "release"])
    run.add_argument(
        "--distribution",
        default="local",
        choices=["local", "ad-hoc", "development", "developer-id", "app-store"],
    )
    test = sub.add_parser("test")
    test.add_argument(
        "--level", default="precommit", choices=["logic", "precommit", "xcode-builds"]
    )
    test.add_argument("--platform", default="mac", choices=["mac", "ios"])
    package = sub.add_parser("package")
    package.add_argument("--platform", default="mac", choices=["mac", "ios"])
    package.add_argument("--scheme", default=PRODUCT_NAME)
    package.add_argument("--configuration", default="release", choices=["debug", "release"])
    package.add_argument(
        "--distribution",
        default="development",
        choices=["local", "ad-hoc", "development", "developer-id", "app-store"],
    )
    package.add_argument(
        "--notary-profile",
        default=None,
        help=f"notarytool Keychain profile for developer-id packages (or {NOTARY_PROFILE_ENV}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            _ensure_local_app_config()
            if args.platform == "ios":
                _build_ios_simulator(
                    args.configuration, scheme=_selected_scheme(args.platform, args.scheme)
                )
            else:
                _package_app(args.configuration, distribution=args.distribution)
        elif args.command == "run":
            _ensure_local_app_config()
            if args.platform == "ios":
                _build_ios_simulator(
                    args.configuration, scheme=_selected_scheme(args.platform, args.scheme)
                )
                return 0
            app = _package_app(args.configuration, distribution=args.distribution)
            _quit_running_app(_app_bundle_identifier(app), _app_bundle_executable_path(app))
            _run(["open", str(app)])
        elif args.command == "test":
            _test_for_platform(args.level, platform=args.platform)
        elif args.command == "package":
            if args.platform != "mac":
                raise RuntimeError(
                    "iOS packaging is not supported yet; use `build --platform ios` for simulator validation."
                )
            notary_profile = (
                _notary_profile(args.notary_profile)
                if args.distribution == "developer-id"
                else None
            )
            _ensure_local_app_config()
            app = _package_app(args.configuration, distribution=args.distribution)
            package_dmg = _dmg_app_bundle(app)
            if args.distribution == "developer-id":
                _notarize_dmg(package_dmg, keychain_profile=notary_profile)
        return 0
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
