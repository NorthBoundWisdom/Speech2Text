# Download and install

Check [GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) for published versions,
notes, and `SHA256SUMS`. If none exists, build from source. Actions trial artifacts require a GitHub
login and are not published releases.

## Choose a client

| Platform | Package | Runtime boundary |
| --- | --- | --- |
| macOS / Apple Silicon | `SonaFolioSwift-v<version>-macOS-arm64.dmg` | SwiftUI app with CLI wheel; Python and models still require setup |
| macOS / Apple Silicon | `SonaFolioQt-v<version>-macOS-arm64.dmg` | Qt client; install CLI and FFmpeg separately |
| Windows / x64 | `SonaFolioQt-v<version>-Windows-x64-Setup.exe` | Installs Qt client and Microsoft VC++ runtime; configure Python, CLI, FFmpeg, and ASR separately |
| Linux / x86_64 | `SonaFolioQt-v<version>-Linux-x86_64.AppImage` | Ubuntu 24.04 or compatible base; no stable Linux ASR backend |
| iOS / iPadOS 17+ | Source build | Reader and subscription manager; no App Store, TestFlight, or automatic IPA release |

macOS packages use **ad-hoc signatures** without Developer ID signing or Apple notarization. Windows
installers are unsigned. Your OS may warn about an unidentified developer; verify the repository
source and checksums before deciding to allow the app to open.

Qt packages include Qt libraries, so browsing does not require an SDK. No package contains models.

## Set up the CLI from source

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
```

On macOS:

```bash
source ~/Documents/SpeechToTextData/env/bin/activate
atot doctor
atot models
```

On Windows, use Python 3.10+, replace `python3` with `python`, and run:

```powershell
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" doctor
& "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" models
```

Stable macOS ASR requires Apple Silicon. Windows defaults to faster-whisper/CUDA. Follow actual
CTranslate2 DLL errors when configuring compatible CUDA/cuDNN. CPU is explicit opt-in.

## Models and media tools

Place models under `~/Documents/SpeechToTextData/model/`. The default alias is `large-v3-turbo`:

- macOS: `model/whisper-large-v3-turbo/`, including `config.json` and `weights.safetensors`.
- Windows: `model/faster-whisper-large-v3-turbo/`; required files and manual URLs are in the
  [model inventory](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json).

Download weights manually. On macOS, `brew install ffmpeg` provides media tools. Windows can use
vcpkg or PATH for `ffmpeg.exe` and `ffprobe.exe`. Configure the `atot` executable in Qt Settings.

[Make your first transcript →](quick-start.md)
