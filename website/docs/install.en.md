# Download and install

Choose a client, then prepare the separate transcription runtime if you want to process audio. Browsing an existing library does not require model weights or a model API key.

## Release and current source {#release-and-current-source}

The [v0.9.0 release](https://github.com/NorthBoundWisdom/sonafolio/releases/tag/v0.9.0) provides four desktop installers. [GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) is the source of truth for versions, checksums, and package notes.

The handbook also describes later source features: resizable/collapsible columns, the compact macOS toolbar, spoken-language checkboxes, and summary output-language selection. Build current source for them. A website update does not upgrade an installed app.

| Platform | v0.9.0 download | Contents |
| --- | --- | --- |
| macOS / Apple Silicon | [Swift DMG](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioSwift-v0.9.0-macOS-arm64.dmg) | Native app and CLI wheel; Python, tools, and weights remain separate |
| macOS / Apple Silicon | [Qt DMG](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-macOS-arm64.dmg) | Qt client/libraries; external CLI for processing |
| Windows / x64 | [Qt installer](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-Windows-x64-Setup.exe) | Qt client and VC++ runtime installation; configure CLI separately |
| Linux / x86_64 | [Qt AppImage](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SonaFolioQt-v0.9.0-Linux-x86_64.AppImage) | Client; no promoted stable Linux ASR backend |
| iOS / iPadOS 17+ | Source build | Reader/subscriptions; no automatic IPA, App Store, or TestFlight distribution |

Weights are never bundled. Actions trial artifacts are different from releases and can require GitHub login.

## Verify the package

Download [SHA256SUMS](https://github.com/NorthBoundWisdom/sonafolio/releases/download/v0.9.0/SHA256SUMS) from the same release. Per-asset .build.json records identify the tag and build. From the download directory:

```bash
shasum -a 256 SonaFolioSwift-v0.9.0-macOS-arm64.dmg
```

```powershell
Get-FileHash .\SonaFolioQt-v0.9.0-Windows-x64-Setup.exe -Algorithm SHA256
```

```bash
sha256sum SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
```

Compare the exact platform/file entry. A matching hash verifies the release bytes, not a substitute for reviewing the source and notes.

## macOS / Apple Silicon {#macos-apple-silicon}

The native app requires macOS 13+. Stable Chinese ASR and automatic macOS packages target Apple Silicon. Choose Swift for the native workspace or Qt for the cross-platform client.

1. Open the DMG and copy the app to Applications.
2. Launch it. Packages use ad-hoc signatures without Apple notarization. For a trusted download blocked by macOS, use its normal **Privacy & Security → Open Anyway** flow.
3. Prepare the CLI below and [models/FFmpeg](models.md), then run doctor.
4. Check **Settings → Overview** in Swift. Optional cloud readiness is not needed for local-only work.
5. In Qt, select the external executable, normally `~/Documents/SpeechToTextData/env/bin/atot`.

The compatibility entrypoint Audio2TextCli remains intentional. The included wheel is not Python, FFmpeg, or model weights.

## Windows / x64 {#windows-x64}

1. Run the unsigned Qt installer and follow its dialogs, including Microsoft Visual C++ Redistributable installation.
2. Prepare Python and CLI; Windows does not need Swift/Xcode.
3. Supply ffmpeg.exe/ffprobe.exe through PATH or vcpkg.
4. Prepare the [faster-whisper model](models.md#windows-faster-whisper).
5. Run the managed atot.exe doctor and select the same executable in Qt.
6. Supply matching CUDA/cuDNN or explicitly choose CPU.

Defaults are faster-whisper, cuda, and int8_float16. Missing CUDA fails explicitly. Intentional CPU:

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

These variables affect processes launched from that environment. A separate desktop shortcut does not inherit another PowerShell session's values. See [CUDA troubleshooting](guides/troubleshooting.md#windows-cuda-or-cudnn-is-missing).

## Linux / x86_64 {#linux-x86_64}

Use Ubuntu 24.04 or a compatible glibc/desktop base:

```bash
chmod +x SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
./SonaFolioQt-v0.9.0-Linux-x86_64.AppImage
```

Without FUSE:

```bash
./SonaFolioQt-v0.9.0-Linux-x86_64.AppImage --appimage-extract-and-run
```

This is client availability, not Linux ASR promotion. Use existing libraries within the stated [support boundaries](handbook.md).

## Prepare the source CLI {#set-up-the-cli-from-source}

Python 3.10+ is required; CI uses 3.13. Clone recursively:

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

Windows uses python instead of python3. Setup creates the default managed runtime/config without downloading weights.

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

Activate Scripts/Activate.ps1 if shell policy permits, or keep using the full Windows path. A global Python/atot can be a different environment.

## Build the current native app

With Xcode installed, from the repository:

```bash
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp \
  --configuration debug --distribution ad-hoc
```

Open build/app/SonaFolio.app. This is a local source build, not a new release. Rebuild/restart after updating source. See [development](development.md) for Qt/iOS.

## Readiness checks

| Check | Expected result |
| --- | --- |
| Client | Opens the chosen library |
| doctor | Required backend, tools, weights ready |
| models | Correct files under model/ |
| Short Chinese task | Transcript and QA without a cloud key |

[Models →](models.md) · [First transcript →](quick-start.md)
