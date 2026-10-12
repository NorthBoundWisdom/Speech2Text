#!/usr/bin/env python3
"""Tag-driven native client packaging with verified vendor redistribution materials."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from xml.etree import ElementTree
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.release_licenses import _required_files, _sha, stage_release_licenses  # noqa: E402

VENDORS = ROOT / "configs" / "ci-vendors.json"
OUTPUT = ROOT / "build" / "release"
VERSION_RE = re.compile(
    r"(?:v)?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*))?\Z"
)


def release_version(value: str) -> tuple[str, str]:
    match = VERSION_RE.fullmatch(value)
    if not match:
        raise ValueError(
            "Release version must be vMAJOR.MINOR.PATCH with an optional prerelease suffix."
        )
    numeric = ".".join(match.group(i) for i in (1, 2, 3))
    if any(int(match.group(i)) > 65535 for i in (1, 2, 3)):
        raise ValueError("Release version exceeds native installer version limits.")
    return numeric + ("-" + match[4] if match[4] else ""), numeric


def run(
    *args: str | Path, env: dict[str, str] | None = None, cwd: Path = ROOT, timeout: int = 1200
) -> None:
    print("Release step:", subprocess.list2cmdline([str(arg) for arg in args]), flush=True)
    subprocess.run([str(arg) for arg in args], check=True, cwd=cwd, env=env, timeout=timeout)


def download(url: str, destination: Path, checksum: str | None = None) -> Path:
    if not url.startswith("https://"):
        raise ValueError("Vendor downloads require HTTPS.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and checksum and _sha(destination) == checksum:
        return destination
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SonaFolio-release/1"})
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            temporary.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
        if checksum and _sha(temporary) != checksum:
            raise ValueError("Vendor checksum mismatch: " + destination.name)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def record(path: Path, root: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": _sha(path)}


def extract_license_texts(archive: Path, destination: Path) -> list[Path]:
    """Read license files directly, without extracting executable files or following tar links."""
    result = []
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            parts = Path(member.name).parts
            if not member.isfile() or member.size > 2 * 1024 * 1024:
                continue
            if "LICENSES" not in parts and not Path(member.name).name.startswith(
                ("LICENSE", "COPYING")
            ):
                continue
            relative = Path(*parts[1:])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe vendor archive member.")
            file = destination / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            content = source.extractfile(member)
            if content is None:
                raise ValueError("Unreadable vendor license.")
            file.write_bytes(content.read())
            result.append(file)
    if not result:
        raise ValueError("Vendor archive has no license texts: " + archive.name)
    return result


def build_icu(materials: Path) -> None:
    if sys.platform != "linux":
        raise ValueError("ICU preparation is a Linux build step.")
    vendor = json.loads(VENDORS.read_text())["icu"]
    archive = download(vendor["url"], materials / "icu4c-73_2-src.tgz", vendor["sha256"])
    source = ROOT / "build/icu-source"
    source.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as package:
        package.extractall(source, filter="data")
    prefix = ROOT / "build/icu-install"
    configure = source / "icu/source/configure"
    run(
        configure,
        f"--prefix={prefix}",
        "--disable-tests",
        "--disable-samples",
        cwd=configure.parent,
    )
    run("make", "-j3", cwd=configure.parent)
    run("make", "install", cwd=configure.parent)
    if os.environ.get("GITHUB_ENV"):
        with Path(os.environ["GITHUB_ENV"]).open("a") as handle:
            handle.write(f"LD_LIBRARY_PATH={prefix / 'lib'}\n")


def install_windows_qt() -> None:
    if os.name != "nt":
        raise ValueError("The Windows SDK installer requires Windows.")
    version = json.loads(VENDORS.read_text())["qt_version"]
    compact = version.replace(".", "")
    base = f"https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_{compact}/qt6_{compact}_msvc2022_64/"
    cache = ROOT / "build/qt-downloads"
    metadata = download(base + "Updates.xml", cache / "Updates.xml")
    document = ElementTree.fromstring(metadata.read_bytes())
    selected = {"qtbase", "qtdeclarative", "qtsvg", "qtshadertools"}
    found = set()
    output = ROOT / "build/qt-sdk"
    extractor = shutil.which("7z") or str(Path(os.environ.get("ProgramFiles", "")) / "7-Zip/7z.exe")
    for package in document.findall("PackageUpdate"):
        name = package.findtext("Name") or ""
        release = package.findtext("Version") or ""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name + release):
            raise ValueError("Invalid vendor package metadata.")
        if ".debug_info." in name:
            continue
        for raw in (package.findtext("DownloadableArchives") or "").split(","):
            archive_name = raw.strip()
            module = archive_name.split("-", 1)[0]
            if module not in selected:
                continue
            if not re.fullmatch(r"[A-Za-z0-9_.-]+\.7z", archive_name):
                raise ValueError("Invalid vendor archive name.")
            url = base + name + "/" + release + archive_name
            checksum_file = download(url + ".sha256", cache / (archive_name + ".sha256"))
            expected = checksum_file.read_text().strip().split()[0]
            archive = download(url, cache / archive_name)
            with archive.open("rb") as handle:
                digest = hashlib.sha256()
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError("Official Qt SDK archive checksum mismatch.")
            run(extractor, "x", archive, f"-o{output}", "-y")
            found.add(module)
    if found != selected:
        raise ValueError("The official Windows SDK is missing required modules.")
    candidates = list(output.glob("**/bin/qmake.exe"))
    if len(candidates) != 1:
        raise ValueError(
            "Installed Windows SDK must contain exactly one qmake.exe; found "
            + str(len(candidates))
        )
    prefix = candidates[0].parent.parent
    with Path(os.environ["GITHUB_ENV"]).open("a") as handle:
        handle.write(f"QT_ROOT_DIR={prefix}\nCMAKE_PREFIX_PATH={prefix}\n")
    with Path(os.environ["GITHUB_PATH"]).open("a") as handle:
        handle.write(str(prefix / "bin") + "\n")


def prepare_materials(qt_prefix: Path, materials: Path) -> None:
    vendors = json.loads(VENDORS.read_text())
    version = vendors["qt_version"]
    qmake = qt_prefix / "bin" / ("qmake.exe" if os.name == "nt" else "qmake")
    installed = subprocess.check_output([str(qmake), "-query", "QT_VERSION"], text=True).strip()
    if installed != version:
        raise ValueError("Qt SDK and corresponding-source versions must match.")
    materials.mkdir(parents=True, exist_ok=True)
    sources, licenses, build_files = [], [], []
    for item in vendors["qt_sources"]:
        archive = download(item["url"], materials / Path(item["url"]).name, item["sha256"])
        sources.append(record(archive, materials))
        for path in extract_license_texts(archive, materials / item["name"]):
            unique = (
                materials
                / "license-texts"
                / (
                    item["name"]
                    + "--"
                    + path.relative_to(materials / item["name"]).as_posix().replace("/", "_")
                )
            )
            unique.parent.mkdir(exist_ok=True)
            shutil.copy2(path, unique)
            licenses.append(record(unique, materials))
    sboms = list((qt_prefix / "sbom").glob("*.spdx"))
    if not sboms:
        raise ValueError("Installed Qt SDK must provide SPDX build/license records.")
    for path in sboms:
        target = materials / "qt-sbom" / path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
        build_files.append(record(target, materials))
        # Preserve extracted third-party copyright/license text from the upstream SBOM.
        texts = re.findall(r"ExtractedText: <text>(.*?)</text>", path.read_text(), re.DOTALL)
        for index, text in enumerate(texts):
            target = materials / "qt-notices" / f"{path.stem}-{index}.txt"
            target.parent.mkdir(exist_ok=True)
            target.write_text(text + "\n")
            licenses.append(record(target, materials))
    instructions = materials / "qt-build-and-relink.txt"
    instructions.write_text(
        f"Qt {version} shared open-source SDK; LGPL-3.0-only option for QtBase/QtDeclarative/QtSvg.\n"
        "Original module licenses, third-party notices and exact vendor build commands are included.\n"
        "Corresponding module sources are the verified official source archives in this directory.\n"
        "Use the compiler/platform and configure options recorded in qt-sbom to rebuild shared Qt.\n"
        "Libraries remain dynamically linked and replaceable; do not enforce signature checks on replacements.\n"
        "To relink the client, build the matching SonaFolio tag with CMake and CMAKE_PREFIX_PATH\n"
        "pointing to your rebuilt Qt. Run cmake --install to deploy it. On macOS remove/reapply\n"
        "the ad-hoc signature after replacing a framework: codesign --force --deep --sign - <app>.\n"
        "Linux base-system libraries are provided by the OS, not copied into this client.\n"
    )
    build_files.append(record(instructions, materials))
    payload = {
        "qt": {
            "name": "qt",
            "version": version,
            "license": "LGPL-3.0-only",
            "license_files": licenses,
            "source_archives": sources,
            "build_files": build_files,
        }
    }
    if sys.platform == "linux":
        for key in ("appimagetool", "appimage_runtime"):
            item = vendors[key]
            download(item["url"], materials / key, item["sha256"]).chmod(0o755)
        item = vendors["appimage_runtime"]
        url = f"https://github.com/{item['repo']}/archive/{item['revision']}.tar.gz"
        archive = download(url, materials / "appimage-runtime-source.tar.gz")
        paths = extract_license_texts(archive, materials / "appimage-runtime-licenses")
        instructions = materials / "appimage-runtime-build.txt"
        instructions.write_text(
            f"Upstream {item['repo']} commit {item['revision']}.\n"
            "Build scripts and dependency definitions are in the included source archive.\n"
        )
        icu = vendors["icu"]
        icu_archive = materials / "icu4c-73_2-src.tgz"
        icu_licenses = extract_license_texts(icu_archive, materials / "icu-licenses")
        icu_instructions = materials / "icu-build.txt"
        icu_instructions.write_text(
            "ICU 73.2: configure --prefix=<install> --disable-tests --disable-samples; make -j3; make install.\nShared libraries, replaceable independently of Qt.\n"
        )
        payload["icu"] = {
            "name": "icu",
            "version": icu["version"],
            "license": icu["license"],
            "license_files": [record(p, materials) for p in icu_licenses],
            "source_archives": [record(icu_archive, materials)],
            "build_files": [record(icu_instructions, materials)],
        }
        payload["appimage_runtime"] = {
            "name": "appimage-runtime",
            "version": item["revision"],
            "license": "MIT",
            "license_files": [record(p, materials) for p in paths],
            "source_archives": [record(archive, materials)],
            "build_files": [record(instructions, materials)],
        }
    if os.name == "nt":
        item = vendors["vc_runtime_license"]
        license_doc = download(item["url"], materials / "vc-runtime-license.docx", item["sha256"])
        with zipfile.ZipFile(license_doc) as document:
            xml = ElementTree.fromstring(document.read("word/document.xml"))
            text = "\n".join(
                node.text for node in xml.iter() if node.tag.endswith("}t") and node.text
            )
        if "MICROSOFT" not in text.upper():
            raise ValueError("Microsoft runtime license text is missing.")
        license_text = materials / "vc-runtime-license.txt"
        license_text.write_text(text)
        # Official redistributable, not arbitrary development-machine CRT DLLs.
        redist = download(
            "https://aka.ms/vs/17/release/vc_redist.x64.exe", materials / "vc_redist.x64.exe"
        )
        command = "$s=Get-AuthenticodeSignature -LiteralPath $env:ATOT_REDIST; if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){exit 1}"
        run(
            "powershell",
            "-NoProfile",
            "-Command",
            command,
            env={**os.environ, "ATOT_REDIST": str(redist)},
        )
        payload["vc_runtime"] = {
            "name": "microsoft-vc-runtime",
            "version": "2015-2022",
            "license": "LicenseRef-Microsoft-Visual-C-Runtime",
            "license_files": [record(license_text, materials)],
        }
    (materials / "prepared.json").write_text(json.dumps(payload, indent=2) + "\n")


def write_material_manifest(stage: Path, materials: Path) -> Path:
    prepared = json.loads((materials / "prepared.json").read_text())
    qt_files, own_files, runtime_files, vc_files, icu_files = [], [], [], [], []
    for name in sorted(_required_files(stage)):
        row = record(stage / name, stage)
        if Path(name).name.startswith("libicu"):
            icu_files.append(row)
        elif name.endswith("vc_redist.x64.exe"):
            vc_files.append(row)
        elif name == "appimage-runtime":
            runtime_files.append(row)
        elif "/Audio2TextQt/" in name:
            own_files.append(row)
        else:
            qt_files.append(row)
    components = [{**prepared["qt"], "files": qt_files}]
    if own_files:
        license_file = materials / "Audio2Text-LICENSE"
        shutil.copy2(ROOT / "LICENSE", license_file)
        components.append(
            {
                "name": "audio2text-qml",
                "version": "source",
                "license": "MIT",
                "files": own_files,
                "license_files": [record(license_file, materials)],
            }
        )
    if runtime_files:
        components.append({**prepared["appimage_runtime"], "files": runtime_files})
    if icu_files:
        components.append({**prepared["icu"], "files": icu_files})
    if vc_files:
        components.append({**prepared["vc_runtime"], "files": vc_files})
    path = materials / "manifest.json"
    path.write_text(json.dumps({"schema_version": 1, "components": components}, indent=2) + "\n")
    return path


def clean_qt_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "QT_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
        "DYLD_LIBRARY_PATH",
        "DYLD_FRAMEWORK_PATH",
        "QT_ROOT_DIR",
        "QTDIR",
        "QT_DIR",
        "CMAKE_PREFIX_PATH",
    ):
        environment.pop(key, None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_QUICK_BACKEND"] = "software"
    return environment


def adhoc_sign(app: Path) -> None:
    run("codesign", "--force", "--deep", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", app)


def create_dmg(stage: Path, app: Path, output: Path) -> None:
    # Only this temporary DMG layout has an intentional link outside the staged application.
    layout = stage.parent / (stage.name + "-dmg")
    if layout.exists():
        shutil.rmtree(layout)
    layout.mkdir()
    shutil.copytree(app, layout / app.name, symlinks=True)
    (layout / "Applications").symlink_to("/Applications")
    run(
        "hdiutil",
        "create",
        "-volname",
        app.stem,
        "-srcfolder",
        layout,
        "-ov",
        "-format",
        "UDZO",
        output,
    )
    shutil.rmtree(layout)


def write_build_record(output: Path, kind: str, version: str) -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    payload = {
        "schema_version": 1,
        "kind": kind,
        "version": version,
        "commit": commit,
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "system": platform.system(),
        "architecture": platform.machine(),
        "signature": "ad-hoc" if sys.platform == "darwin" else "unsigned",
        "asset": output.name,
        "sha256": _sha(output),
    }
    output.with_suffix(output.suffix + ".build.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )


def package_qt(version: str, qt_prefix: Path, materials: Path) -> Path:
    version, numeric = release_version(version)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build = ROOT / "build" / "ci-qt"
    stage = ROOT / "build" / "ci-qt-stage"
    if stage.exists():
        shutil.rmtree(stage)
    run(
        "cmake",
        "-S",
        ROOT / "qt/Audio2TextQt",
        "-B",
        build,
        "-G",
        "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_PREFIX_PATH={qt_prefix}",
        f"-DAUDIO2TEXTQT_RELEASE_VERSION={numeric}",
    )
    run("cmake", "--build", build, "--parallel", "3")
    run("ctest", "--test-dir", build, "--output-on-failure")
    run("cmake", "--install", build, "--config", "Release", "--prefix", stage)
    if sys.platform == "darwin":
        from configs.qt_workflow import _verify_macos_dependency_paths

        app = stage / "SonaFolioQt.app"
        _verify_macos_dependency_paths(app)
        adhoc_sign(app)
        executable = app / "Contents/MacOS/SonaFolioQt"
        asset = OUTPUT / f"SonaFolioQt-v{version}-macOS-arm64.dmg"
        license_stage = app / "Contents/Resources"
        license_stage.mkdir(parents=True, exist_ok=True)
        # Manifest paths use the whole stage, with resources copied into the app after verification.
    else:
        executable = stage / "bin/SonaFolioQt"
        asset = OUTPUT / f"SonaFolioQt-v{version}-Linux-x86_64.AppImage"
        if os.name == "nt":
            executable = executable.with_suffix(".exe")
            shutil.copy2(materials / "vc_redist.x64.exe", stage / "vc_redist.x64.exe")
            asset = OUTPUT / f"SonaFolioQt-v{version}-Windows-x64-Setup.exe"
        else:
            shutil.copy2(materials / "appimage_runtime", stage / "appimage-runtime")
    run(
        executable,
        "--smoke-quit",
        "--data-root",
        ROOT / "build/ci-smoke-data",
        env=clean_qt_environment(),
        timeout=45,
    )
    manifest = write_material_manifest(stage, materials)
    stage_release_licenses(stage, manifest)
    if sys.platform == "darwin":
        for name in ("licenses", "third-party-components.json", "sbom.cdx.json"):
            shutil.move(str(stage / name), str(license_stage / name))
        index = license_stage / "third-party-components.json"
        document = json.loads(index.read_text())
        prefix = license_stage.relative_to(stage).as_posix()
        for component in document["components"]:
            for category in ("license_files", "source_materials"):
                for row in component[category]:
                    row["path"] = prefix + "/" + row["path"]
        index.write_text(json.dumps(document, indent=2) + "\n")
        # Resources were added after initial deployment/signing; renew the bundle signature.
        adhoc_sign(app)
        create_dmg(stage, app, asset)
    elif os.name == "nt":
        iscc = shutil.which("iscc") or str(
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6/ISCC.exe"
        )
        run(
            iscc,
            f"/DSourceDir={stage}",
            f"/DOutputDir={OUTPUT}",
            f"/DReleaseVersion={version}",
            f"/DNumericVersion={numeric}",
            ROOT / "configs/installers/windows.iss",
        )
        if not asset.is_file():
            raise ValueError("Windows installer compiler produced no expected setup executable.")
    else:
        (stage / "SonaFolioQt.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=SonaFolio\nExec=SonaFolioQt\nIcon=SonaFolioQt\nCategories=AudioVideo;Audio;\n"
        )
        shutil.copy2(ROOT / "qt/Audio2TextQt/resources/app-icon.png", stage / "SonaFolioQt.png")
        (stage / "AppRun").write_text(
            '#!/bin/sh\nset -eu\nATOT_APPDIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$ATOT_APPDIR/bin/SonaFolioQt" "$@"\n'
        )
        (stage / "AppRun").chmod(0o755)
        tool = materials / "appimagetool"
        run(
            tool,
            "--appimage-extract-and-run",
            "--no-appstream",
            "--runtime-file",
            materials / "appimage_runtime",
            stage,
            asset,
            env={**os.environ, "ARCH": "x86_64", "VERSION": version},
        )
        run(
            asset,
            "--appimage-extract-and-run",
            "--smoke-quit",
            "--data-root",
            ROOT / "build/ci-smoke-data",
            env=clean_qt_environment(),
        )
    write_build_record(asset, "qt", version)
    return asset


def package_swift(version: str) -> Path:
    version, numeric = release_version(version)
    os.environ["ATOT_RELEASE_VERSION"] = numeric
    os.environ["ATOT_BUILD_PYTHON"] = sys.executable
    from configs import ios_workflow

    app = ios_workflow._package_app("release", distribution="ad-hoc")
    dmg = ios_workflow._dmg_app_bundle(app)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"SonaFolioSwift-v{version}-macOS-arm64.dmg"
    shutil.move(dmg, target)
    write_build_record(target, "swift", version)
    return target


def validate_assets(directory: Path, version: str) -> None:
    version, _ = release_version(version)
    names = [
        f"SonaFolioQt-v{version}-Windows-x64-Setup.exe",
        f"SonaFolioQt-v{version}-Linux-x86_64.AppImage",
        f"SonaFolioQt-v{version}-macOS-arm64.dmg",
        f"SonaFolioSwift-v{version}-macOS-arm64.dmg",
    ]
    commits = set()
    rows = []
    for name in names:
        asset = directory / name
        proof = json.loads(asset.with_suffix(asset.suffix + ".build.json").read_text())
        if proof["asset"] != name or proof["version"] != version or proof["sha256"] != _sha(asset):
            raise ValueError("Release asset provenance/hash mismatch: " + name)
        commits.add(proof["commit"])
        rows.append(f"{proof['sha256']}  {name}")
    expected = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if commits != {expected}:
        raise ValueError("Release artifacts must match the checked-out tag commit.")
    (directory / "SHA256SUMS").write_text("\n".join(rows) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["metadata", "prepare", "qt", "swift", "verify", "icu", "windows-sdk"]
    )
    parser.add_argument("--version", default=os.environ.get("RELEASE_VERSION", ""))
    parser.add_argument("--qt-prefix", type=Path)
    parser.add_argument("--materials", type=Path, default=ROOT / "build/release-materials")
    parser.add_argument("--directory", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.command == "icu":
        build_icu(args.materials)
        return
    if args.command == "windows-sdk":
        install_windows_qt()
        return
    if args.command == "prepare":
        if args.qt_prefix is None:
            parser.error("--qt-prefix is required")
        prepare_materials(args.qt_prefix, args.materials)
        return
    version, numeric = release_version(args.version)
    if args.command == "metadata":
        if os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a") as handle:
                handle.write(f"version={version}\nnumeric={numeric}\n")
        print(version)
    elif args.command == "qt":
        if args.qt_prefix is None:
            parser.error("--qt-prefix is required")
        print(package_qt(version, args.qt_prefix, args.materials))
    elif args.command == "swift":
        print(package_swift(version))
    else:
        validate_assets(args.directory, version)


if __name__ == "__main__":
    main()
