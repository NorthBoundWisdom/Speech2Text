# SonaFolio branding and compatibility

The product name is **SonaFolio**. The repository is
[NorthBoundWisdom/sonafolio](https://github.com/NorthBoundWisdom/sonafolio), and the website is
[GitHub Pages](https://northboundwisdom.github.io/sonafolio/).

The GitHub description and Python project description are:

> Local-first podcast transcription and knowledge library for macOS, iOS, and Windows.

Use SonaFolio in interfaces, help, documentation, and release packages. Keep `atot` as the CLI name.
The following identifiers preserve existing data and integrations; do not apply a blind global rename.

| Retained identifier | Compatibility purpose |
| --- | --- |
| `atot`, `ATOT_*`, `src/atot/` | CLI, Python module, and runtime interfaces |
| `audio2text-local`, `audio2text_local-*.whl` | Distribution name and bundled wheel discovery |
| `Audio2TextCli` | Existing scripts and the app bundle's compatibility CLI entrypoint |
| `SpeechToTextData/`, `Audio2TextLibrary/`, iCloud `Audio2Text/` | Existing models, media, and library paths |
| `audio2text.library.*` and related JSON kinds | Shared Swift/Qt/Python library schema |
| `com.audio2text.local*`, `local.audio2text.Audio2TextQt` | Bundle, signing, settings, and system authorization identity |
| Qt `Audio2Text` / `Audio2TextQt` QSettings and `audio2text.*` keys | Existing preferences, credentials, service markers, and Git hooks |
| `Audio2TextApp`, `Audio2TextCore`, `Audio2TextiOS`, `Audio2Text-iOS`, `Audio2TextQt` | Source modules, Xcode schemes, and CMake targets |
| `Audio2Text.xcodeproj`, `Audio2Text.xcassets`, `/Audio2TextQt/` QML URI | Generated project and resource addresses |
| `audio2text-transcribe` skill ID | Existing skill invocation; its display name uses SonaFolio |
| Existing `audio2text` MCP registrations | Client-chosen alias; new connections may use `sonafolio` |
| Old fixtures, diagnostic filenames, historical records | Compatibility coverage and original measured evidence |

Release assets use `SonaFolioQt-v<version>-...` and `SonaFolioSwift-v<version>-...`.
The Swift app is `SonaFolio.app`; Qt executables and bundles use `SonaFolioQt`.

## Maintenance rules

- Documentation, website pages, code comments, and default interfaces are English.
- Retain non-English text only as localization or ASR language data reviewed in `language-assets.json`.
  `python configs/check_repository_language.py` enforces exact resources and embedded lines.
- Keep compatibility identifiers in code style and explain their purpose.
- Do not rename FreeCM's third-party brand, license, or source identity.
- Preserve historical numbers, commands, and failure codes when translating experiment prose.
- Retain contributor attribution and third-party copyright notices.
- Platform, signing, download, and cloud-processing claims must match current source and workflows.
