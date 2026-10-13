# CI and tag releases

GitHub Actions runs `.github/workflows/ci.yml` for main pushes, pull requests and manual dispatch.
Python checks cover Linux (3.10 and 3.13), Windows and macOS; Qt builds/QML smoke checks cover all
three desktop platforms; Swift tests and Release compilation run on Apple Silicon macOS.
Tests use synthetic credentials and fake ASR inputs; they do not download model weights or call a
cloud model API. Actions are pinned to reviewed commit SHAs, checkout credentials are not retained,
and normal build jobs have read-only repository permissions.

## Build a release

Push a semantic version tag after CI passes:

```bash
git tag v0.9.1
git push origin v0.9.1
```

Native release builds four installers from that exact tag commit:

| Client | Runner / architecture | Asset |
|---|---|---|
| Qt Windows | windows-2022 / x64 | `SonaFolioQt-v<version>-Windows-x64-Setup.exe` |
| Qt Linux | ubuntu-24.04 / x86_64 | `SonaFolioQt-v<version>-Linux-x86_64.AppImage` |
| Qt macOS | macos-26 / arm64 | `SonaFolioQt-v<version>-macOS-arm64.dmg` |
| Swift macOS | macos-26 / arm64 | `SonaFolioSwift-v<version>-macOS-arm64.dmg` |

Windows setup is built with Inno Setup, installs Qt/QML files and the official Microsoft Visual C++
Redistributable, and creates a Start-menu shortcut. It does not copy arbitrary developer CRT DLLs.
Linux is an AppImage containing shared Qt and QML imports; it needs Ubuntu 24.04 or an equivalent
base system with compatible glibc and desktop libraries. macOS DMGs provide drag-to-Applications
installation. Both macOS clients use **ad-hoc signatures**; no certificate secrets are required,
and these packages are not Developer ID signed or notarized. Windows setup is unsigned.

Version tags accept `vMAJOR.MINOR.PATCH` and a prerelease suffix such as `-rc.1`. GUI versions and
installer filenames come from the tag; prereleases are marked as prereleases on GitHub.
A separate verification step requires all four assets, matching SHA-256 values and the same tag
commit before creating the GitHub Release. Failed builds do not publish a partial Release.
Release assets include `SHA256SUMS` and `.build.json` provenance records. Rerunning publication
for an already published tag does not overwrite existing release assets.

For a build-only trial, run **Native release** with `workflow_dispatch` on main and enter a version.
Manual runs upload a verified artifact set but do not create a tag or publish a GitHub Release.
This lets contributors exercise Windows and Linux packaging before publishing a version.

## Final package startup gate

Following Ravo's separate-runner package checks, `package-smoke` downloads the final EXE,
AppImage and both DMGs on fresh runners without Qt SDKs, source roots or compiler caches.
Windows silently installs the final EXE; macOS mounts the DMG read-only and copies its app
outside the checkout; Linux launches the final AppImage payload under Xvfb and a D-Bus session.
The AppImage extraction mode avoids depending on privileged FUSE mounts in CI.

Each client must load its native platform plugin and display a window frame through
`--startup-smoke`. An offscreen launch or a zero exit code without a matching first-frame
marker cannot pass. The verifier clears developer library/QML search paths and uses an
isolated data root; it does not transcribe, download models or test a cloud API.
Swift startup smoke skips cloud preflight. All checks must pass before release publication.

Checks retain loader/installer logs and per-package evidence JSON, including the package hash,
source commit, success and first-frame status. They verify startup on the selected CI operating
systems, not every target machine, GPU driver or optional ASR runtime.

## Runtime boundary

Qt CI and tag builds materialize the exact GeoControls revision from
`source_roots.lock.jsonc.in` through FreeCM before CMake configuration. Its reusable controls,
window shell and icons are linked into the client, and the deployed launch check verifies that
no developer QML search path is needed. Packages include its MIT license and revision inventory.

Qt packages contain the client and shared Qt runtime. Python CLI, FFmpeg, CUDA and model weights
remain external. Install/configure the CLI and FFmpeg before requesting transcription; configure
`atot` in the Qt Settings. Library reading does not require ASR. Linux Qt availability does not
promote a Linux ASR backend: the supported production ASR paths remain macOS MLX and Windows
faster-whisper/CUDA. macOS Swift includes the CLI wheel and uses the existing runtime setup flow.

No API key is needed for local browsing or agent summaries through `atot mcp`. Model files must be
placed manually under the data-root `model/` directory. Never put keys in Actions variables or
committed configuration merely to make a test pass.

## Redistribution materials

`configs/ci-vendors.json` pins Qt 6.12.0 source archives/checksums, AppImage tooling/runtime and the
Microsoft runtime license document. The Windows SDK uses the official architecture-specific repository and SHA-256 archive checks
(the current aqt release does not support that new Windows repository layout). Other Qt SDK
downloads are verified by aqtinstall; source
archives are verified against the committed SHA-256 values. The release script confirms that SDK
and source versions match. Linux builds the ICU 73.2 ABI required by the vendor Qt SDK from its
verified source, deploys its shared libraries, and includes its Unicode license/source materials. SDK SPDX build records, copyright/license notices, corresponding
sources and rebuild/relink instructions are included in each Qt package. The existing
[release license gate](RELEASE_LICENSES.md) validates the actual deployed file/material hashes
before generating an installer. Windows uses the vendor-signed official redist installer;
its Authenticode publisher/status is checked before bundling. Linux pins the embedded AppImage
runtime and includes its license and source/build provenance.

`configs/ci_release.py` stages with Qt's CMake deployment API and verifies a deployed QML launch
with developer Qt search variables removed. It refuses external macOS library dependencies.
The Windows runner additionally silently installs its generated setup and launches the installed
client; Linux launches the resulting AppImage using extraction mode, so CI does not depend on
FUSE. macOS apps are signed again after license resources have been added.

When updating Qt, update the version/archives in both workflows and the vendor lock, review the
module licenses and upstream SPDX data, and run a build-only release. License and source material
collection supports the selected QtBase/QtDeclarative/QtSvg runtime; adding a new deployed module
requires adding its corresponding sources and notices. Hashes do not independently establish
redistribution rights or verify source completeness; the maintainer still reviews the materials.

References: [GitHub runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[Qt CMake deployment](https://doc.qt.io/qt-6/cmake-deployment.html),
[Qt Windows runtime deployment](https://doc.qt.io/qt-6/windows-deployment.html),
[AppImage tooling](https://github.com/AppImage/appimagetool).
