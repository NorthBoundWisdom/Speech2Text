import json
import tarfile
from io import BytesIO

import pytest

from configs import ci_release


@pytest.mark.parametrize(
    "tag,result", [("v1.2.3", ("1.2.3", "1.2.3")), ("0.9.0-rc.1", ("0.9.0-rc.1", "0.9.0"))]
)
def test_release_version(tag, result):
    assert ci_release.release_version(tag) == result


@pytest.mark.parametrize(
    "tag", ["v1", "v01.2.3", "v1.2.3/escape", "v1.2.3\n", "v65536.0.0", "v1.2.3;whoami"]
)
def test_release_tag_rejects_unsafe_or_invalid_values(tag):
    with pytest.raises(ValueError):
        ci_release.release_version(tag)


def test_license_extractor_does_not_extract_code_or_follow_links(tmp_path):
    archive = tmp_path / "vendor.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for name in ("vendor/LICENSES/MIT.txt", "vendor/code.sh"):
            item = tarfile.TarInfo(name)
            data = b"synthetic vendor data"
            item.size = len(data)
            target.addfile(item, BytesIO(data))
        link = tarfile.TarInfo("vendor/LICENSES/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/tmp/private"
        target.addfile(link)
    output = tmp_path / "license-texts"
    paths = ci_release.extract_license_texts(archive, output)
    assert [p.relative_to(output).as_posix() for p in paths] == ["LICENSES/MIT.txt"]
    assert not (output / "code.sh").exists()


def test_release_verification_requires_all_platforms_and_same_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(ci_release.subprocess, "check_output", lambda *args, **kwargs: "a" * 40)
    names = [
        "Audio2TextQt-v1.2.3-Windows-x64-Setup.exe",
        "Audio2TextQt-v1.2.3-Linux-x86_64.AppImage",
        "Audio2TextQt-v1.2.3-macOS-arm64.dmg",
        "Audio2TextSwift-v1.2.3-macOS-arm64.dmg",
    ]
    for name in names:
        file = tmp_path / name
        file.write_bytes(b"synthetic asset")
        file.with_suffix(file.suffix + ".build.json").write_text(
            json.dumps(
                {
                    "asset": name,
                    "version": "1.2.3",
                    "commit": "a" * 40,
                    "sha256": ci_release._sha(file),
                }
            )
        )
    ci_release.validate_assets(tmp_path, "v1.2.3")
    assert len((tmp_path / "SHA256SUMS").read_text().splitlines()) == 4
    (tmp_path / names[0]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        ci_release.validate_assets(tmp_path, "v1.2.3")


def test_release_verification_does_not_accept_partial_builds(tmp_path):
    with pytest.raises(FileNotFoundError):
        ci_release.validate_assets(tmp_path, "1.2.3")


def test_smoke_environment_does_not_use_developer_qt_paths(monkeypatch):
    monkeypatch.setenv("QT_PLUGIN_PATH", "/tmp/developer-qt")
    monkeypatch.setenv("QML_IMPORT_PATH", "/tmp/developer-qml")
    monkeypatch.setenv("DYLD_FRAMEWORK_PATH", "/tmp/developer-frameworks")
    environment = ci_release.clean_qt_environment()
    assert "QT_PLUGIN_PATH" not in environment
    assert "QML_IMPORT_PATH" not in environment
    assert "DYLD_FRAMEWORK_PATH" not in environment
    assert environment["QT_QPA_PLATFORM"] == "offscreen"
