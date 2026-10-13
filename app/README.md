# SonaFolio Swift clients

The macOS app imports media, runs local transcription/QA, and manages the library. iOS/iPadOS reads
the shared library and manages subscriptions and reading state. Product interfaces use English;
module and scheme identities remain compatible, as documented in [branding](../doc/BRANDING.md).

## Build and run

From the repository root:

```bash
git submodule update --init --recursive FreeCM
python3 configs/source_root_workflow.py --init
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
```

SwiftPM logic checks:

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift run --scratch-path ../build/swiftpm Audio2TextApp
```

Targets require macOS 13+ / iOS 17+. Stable macOS ASR requires Apple Silicon. iOS Simulator builds use
`--platform ios --scheme Audio2Text-iOS`; there is no automatic IPA/App Store distribution.

The bundle is `build/app/SonaFolio.app`. Its compatibility CLI is
`Contents/MacOS/Audio2TextCli`, which invokes the internal JSON `serve --stdio` protocol. Standard MCP
is separate: `atot mcp`. The generated `Audio2Text.xcodeproj` stays out of Git.

## Processing and summaries

Import a link or local media, choose a group, then process it through the item menu. The detail pane
shows Overview, Transcript, and existing Summary. Default processing and primary shortcuts execute
local transcription and QA without a cloud API key.

For agent summaries, Codex reads complete transcript/QA documents through MCP and publishes with
current hashes. Replacing a nonempty summary requires an explicit regeneration request. MCP itself
does not call a model API; agent-read text enters the client's conversation.

Optional cloud summaries require explicit enablement, transcript-upload permission, endpoint, model,
and a securely stored key. Settings checks call the API only when requested, or when automatic cloud
summaries have explicitly enabled startup checks. This is not the default local processing flow.

## Data and models

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
~/Documents/SpeechToTextData/Audio2TextLibrary/
~/Documents/SpeechToTextData/materials/<episode_id>/
~/Documents/SpeechToTextData/work/<episode_id>/
```

The first two are alternate iCloud/local authoritative library locations. Media and work files remain
local. iOS selects the existing `Audio2Text` or `Audio2TextLibrary` folder through Files and stores a
bookmark. It reads documents and manages subscriptions/read/star/archive/group/delete state, without
running ASR or downloading audio for processing.

The default model is `large-v3-turbo`, under `model/whisper-large-v3-turbo/`, with `config.json` and
`weights.safetensors`. Download manually using the repository model inventory. Logs live in
`cache/logs/` and corresponding work directories.

## Package

```bash
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution ad-hoc
```

Actions packages use ad-hoc signatures without notarization. The Swift bundle includes the CLI wheel;
Python, FFmpeg, and models still need runtime setup. Optional Developer ID signing requires the
appropriate certificate and notarytool profile.

[Releases](../doc/CI_RELEASES.md) · [Privacy](../doc/PRIVACY.md) · [Handbook](https://northboundwisdom.github.io/sonafolio/)

## Desktop columns

The macOS workspace follows NetNewsWire's native sidebar/content-list/reader layout. Drag the two
vertical dividers to resize Sources and Episode List. Toolbar buttons and the View menu independently
hide/show both columns; `Control-Command-S` toggles Sources and `Control-Command-L` toggles Episode List.
The View menu's Show All Columns restores both. Expanded widths and visibility are remembered, and
hiding a column preserves its selection and view state. The reader retains a usable minimum width.
