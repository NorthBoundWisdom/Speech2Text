# SonaFolio Qt

SonaFolio Qt is the cross-platform Qt/QML client for SonaFolio. It mirrors the
Swift client boundary: the UI reads `Audio2TextLibrary` directly for browsing,
and runs workflow commands through `atot serve --stdio --request-json ... --unwrap-result`.

## Build

```powershell
cmake -S qt/Audio2TextQt -B build/Audio2TextQt -DCMAKE_PREFIX_PATH=<Qt-prefix>
cmake --build build/Audio2TextQt --config Release
```

On macOS, the CMake target builds `SonaFolioQt.app`; `configs/qt_workflow.py`
launches the bundle executable from `Contents/MacOS`. On Windows, the build runs
`windeployqt` after linking and copies the offscreen and minimal platform plugins
so the smoke test can run in CI-like shells.

## FreeCM

FreeCM exposes Qt client variants on macOS and Windows. The `Run` action includes
`Mac Qt Client` on macOS and `Windows Qt Client` on Windows; both call
`configs/qt_workflow.py`, which configures/builds `qt/Audio2TextQt` and then
launches the build output. Set `AUDIO2TEXTQT_QT_PREFIX` or `CMAKE_PREFIX_PATH` to
the Qt 6 prefix if Qt is not already discoverable from PATH or the existing CMake
cache.

The `Package` action includes `Mac Qt Client ZIP` on macOS and `Windows Qt Client
ZIP` on Windows. macOS packaging runs `macdeployqt`, copies `ffmpeg` and `ffprobe`
into the app bundle, and writes `build/package/SonaFolioQt_v<version>_macOS.zip`.

## Smoke Checks

```powershell
ctest --test-dir build/Audio2TextQt -C Release --output-on-failure
```

macOS library probe:

```bash
build/Audio2TextQt/SonaFolioQt.app/Contents/MacOS/SonaFolioQt --library-probe --data-root path/to/SpeechToTextData
```

Windows library probe:

```powershell
build/Audio2TextQt/Release/SonaFolioQt.exe --library-probe --data-root path/to/SpeechToTextData
```

`--data-root` accepts either a data root containing `Audio2TextLibrary/` or the
library root itself. Runtime command execution also receives the same value via
`ATOT_DATA_ROOT`.

## Runtime Options

```text
--data-root <path>      SonaFolio data root for this run.
--library-root <path>   Optional explicit Audio2TextLibrary location.
--atot <path>           Optional atot, atot.exe, or Audio2TextCli path.
--vcpkg-root <path>     Optional vcpkg root used to discover ffmpeg/ffprobe.
--smoke-quit            Load QML and quit.
--library-probe         Scan the configured library and quit.
```
