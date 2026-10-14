# SonaFolio Qt

SonaFolio Qt is the cross-platform Qt/QML client for SonaFolio. It mirrors the
Swift client boundary: the UI reads `Audio2TextLibrary` directly for browsing,
and runs workflow commands through `atot serve --stdio --request-json ... --unwrap-result`.

Qt clients are built for macOS, Windows and Linux. The Linux client does not promote a stable
Linux ASR backend. Qt 6.8+ is required; current CI validates Qt 6.12.0. Internal CMake/QML names
remain compatible; see [brand identifiers](../../doc/BRANDING.md).

## Build

```powershell
python configs/source_roots.py init-seeds --quiet
python configs/source_roots.py materialize --quiet
python configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python configs/qt_workflow.py build --configuration Release
```

On macOS, the CMake target builds `SonaFolioQt.app`; `configs/qt_workflow.py`
launches the bundle executable from `Contents/MacOS`. On Windows, the build runs
`windeployqt` after linking and copies the offscreen and minimal platform plugins
so the smoke test can run in CI-like shells.

## FreeCM

FreeCM exposes Qt client variants on macOS and Windows. With `Local App Config`
selected on macOS, use the arrow beside `Run` and choose `Mac Qt Client`. The same
configuration also exposes Qt build, smoke-test and ZIP-package variants. The Swift
app remains the default; selecting `Config: Mac Qt Client` makes the Qt variants
the defaults for all four actions. On Windows, choose `Windows Qt Client`. Both run
variants call `configs/qt_workflow.py`, which configures/builds `qt/Audio2TextQt` and then
launches the build output. Set `AUDIO2TEXTQT_QT_PREFIX` or `CMAKE_PREFIX_PATH` to
the Qt 6 prefix if Qt is not already discoverable from PATH or the existing CMake
cache.

`source_roots.lock.jsonc.in` pins GeoControls by its HTTPS remote and full commit.
FreeCM prepares its source root under ignored `build/`; CMake consumes that root
without downloading or vendoring controls. Existing machine-local locks must add the
GeoControls entries from the template before initialization. Manual sibling checkout
paths belong only in the ignored local lock's `depsManualPath.GeoControls`.

The client uses `GeoControls` for all interactive controls and `GeoControls.AppShell`
for its application window. Qt Quick Controls is imported under `QQC` only for enums
and attached layout/overlay contracts. The Basic style provides input behavior; buttons,
text fields, editing menus, tabs, popups, scroll bars and split handles use GeoControls
presentation. File/folder choosers use its public native-dialog entry points.
Theme initialization and static module registration are shared by the app and its
Quick Test runner; resource URLs remain available in installed packages.

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

By default, Qt and the Swift macOS client share `~/Documents/SpeechToTextData/`,
its `config.toml`, the local `model/` directory, and the same `Audio2TextLibrary`.
Qt reads `[library].storage`, `icloud_root`, and `local_root` from that shared
configuration. The default storage is iCloud on macOS and local on Windows,
matching the CLI. Switching frontends does not copy episodes or model weights.
Returning to Qt refreshes the shared configuration and library.

`--data-root` selects another data root and its configuration; it also accepts the
library root itself for browsing probes. Runtime command execution receives this
value via `ATOT_DATA_ROOT`. `--library-root` takes precedence for browsing.
Command-line path overrides apply only to the current run and do not change saved
preferences.

## Runtime Options

```text
--data-root <path>      SonaFolio data root for this run.
--library-root <path>   Optional explicit Audio2TextLibrary location.
--atot <path>           Optional atot, atot.exe, or Audio2TextCli path.
--vcpkg-root <path>     Optional vcpkg root used to discover ffmpeg/ffprobe.
--smoke-quit            Load QML and quit.
--library-probe         Scan the configured library and quit.
```

## Automatic installer releases

Tag builds produce Windows EXE, Linux AppImage and macOS DMG clients. These installers include
Qt libraries but do not bundle the Python CLI, FFmpeg, CUDA or model weights. This differs from
the manual FreeCM ZIP package above, which explicitly copies FFmpeg and may optionally bundle
a clean Windows Python runtime. Both paths require third-party license/source materials.

See [release workflow](../../doc/CI_RELEASES.md) and the [online installation guide](https://northboundwisdom.github.io/sonafolio/install/).

## Resizable and collapsible columns

Settings > Overview > Appearance offers Follow System (default), Light and Dark.
Changes apply immediately to the workspace, document reader, menus and settings,
and the Qt client remembers the choice across launches. Document tabs use a rounded
segmented strip and wrap onto another row when the reading pane is narrow.

Drag the thin vertical separators to resize Sources and Episode List. The toolbar keeps both
visibility buttons available when columns are hidden. `Ctrl+Shift+S` and `Ctrl+Shift+L` toggle the
columns. Expanded widths and visibility are saved between sessions; content remains loaded while
hidden. A wider invisible hit region makes each separator easier to grab.

CTest includes real QML divider-drag, collapse/restore, and narrow-window layout checks. Test QML is
kept in `tests/qt_workspace/`, outside the deployed module's import scan.
