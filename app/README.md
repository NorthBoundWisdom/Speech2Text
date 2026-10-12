# Audio2Text Swift App

SwiftUI macOS app for the local Audio2Text workflow.

## Run

Recommended local app workflow from the repository root:

```bash
git submodule update --init --recursive FreeCM
python3 configs/source_root_workflow.py --init
python3 configs/source_root_workflow.py --update
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
python3 configs/ios_workflow.py package --platform mac --scheme Audio2TextApp --configuration release --distribution development
```

FreeCM reads `configs/freecm.commands.jsonc` and exposes the same `config`, `build`, `run`, `test`,
and `package` actions. The config action regenerates the ignored root `Audio2Text.xcodeproj`. The
package action uses development signing for local verification and writes
`build/package/Audio2Text_v<MARKETING_VERSION>_<ARCHIVE_ID>.dmg`, using values from the repository
root `source_roots.lock.jsonc`. Website release builds require a `Developer ID Application`
certificate plus a `notarytool` Keychain profile, and should pass `--distribution developer-id`
with `--notary-profile "Audio2Text Release"`. The FreeCM Developer ID action has no profile input,
so its release host must set `ATOT_NOTARY_KEYCHAIN_PROFILE` to the saved profile name.

For fast development checks, SwiftPM still works:

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift run --scratch-path ../build/swiftpm Audio2TextApp
```

Local builds package the public CLI inside the app bundle. The CLI defaults to the interactive TUI;
the Swift app invokes the same Python workflow service through `serve --stdio`:

```text
build/app/Audio2Text.app/Contents/MacOS/Audio2TextCli
```

`~/Documents/SpeechToTextData/env/` remains the app-managed Python runtime environment, not the
public command location.

## Workflow

- The left sidebar shows the process library as custom groups. `Default` is always available.
- Use the folder-plus button to create a group.
- Use the plus button to open the import panel.
- Link mode checks a Xiaoyuzhou episode URL without downloading first. After the link is valid,
  choose a group and confirm. The app writes metadata to the unified Library first so the item
  appears immediately, then downloads audio into local `materials/<episode_id>/`.
- File mode lets the user choose a local audio or video file, choose a group, and confirm to copy it
  into local `materials/<episode_id>/`.
- Groups are stored as app metadata tags, not as filesystem folders.
- Imported items are not processed automatically. Use the item context menu to process, reprocess,
  star, move to another group, or delete an item.
- The detail pane shows `简介`, `Transcript`, and `Summary`. If a summary exists, the app selects it
  by default; otherwise it selects the intro page. Unprocessed items show only `简介`, where queue
  labels can be set to `unread`, `to process`, `process later`, or `delete`.

The app uses one authoritative `Audio2TextLibrary/` plus local-only processing roots:

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
~/Documents/SpeechToTextData/Audio2TextLibrary/
~/Documents/SpeechToTextData/materials/<episode_id>/
~/Documents/SpeechToTextData/work/<episode_id>/
```

Logs are persisted to `~/Documents/SpeechToTextData/cache/logs/job-*.log` before an output directory
is known, then mirrored to `work/<episode_id>/app.log` once the job work directory exists.

## Unified Library

macOS and iOS read and write the same `Audio2TextLibrary/` schema. When Library storage is iCloud,
the Mac app and CLI write the Library in visible iCloud Drive under `Audio2Text/Audio2TextLibrary`;
when storage is local, it lives under the app data root. On iOS/iPad, choose the shared
`Audio2Text` or `Audio2TextLibrary` folder from Settings so the app can keep a Files bookmark to
that same iCloud Drive Library. Use `Process > Refresh Library` on Mac to rescan the
shared Library manually.

The iOS app can add/remove subscriptions, refresh episode metadata, read `summary.md` and
`transcript.md`, and manage read/star/archive/group/delete state. Shared empty groups are stored as
`Audio2TextLibrary/groups/<group_id>.json` so Mac and iOS show the same folder list. Legacy macOS
local group preferences are migrated into that directory on refresh, then the shared Library becomes
the authority. It does not download audio or run transcription. The macOS app is the only client
that downloads audio, writes local work files, and invokes local models.

Both macOS and iOS show a Library sync status badge. For iCloud Drive Libraries, the badge checks
public Library JSON/Markdown files and reports one of three user-facing states: `正在同步`,
`网络断开`, or `同步成功`.

## Cloud Summary

Processing and reprocessing run local transcription, QA, then:

```bash
Audio2TextCli exec cloud summarize <work-dir> --call-api --from-readable
```

The app summary path reads `work/<episode_id>/transcript.readable.md`, writes cloud artifacts
under that work directory, and publishes `summary.md` to
`Audio2TextLibrary/episodes/<episode_id>/documents/summary.md`.
Cloud summary generation is opt-in. If the API key or transcript-upload setting is missing,
processing finishes after local transcription and QA, and users can generate a summary later from the
item action after enabling cloud summaries in Settings.

By default the app config selects `gpt-5.4-mini` and leaves the API base/key for the user-owned
`config.toml`:

```text
[cloud]
model = "gpt-5.4-mini"
api_base = ""
api_key = ""
```

Set the API key in the app Settings page. The Settings page tests the key only when `Check` is
clicked; saving does not perform another cloud request. For local development
only, you can also set `ATOT_CLOUD_API_KEY` before launching the app or create an ignored local file:

```json
{
  "api_base": "https://api.example.com/v1",
  "model": "gpt-5.4-mini",
  "timeout": "360",
  "temperature": "1",
  "max_tokens": "8192",
  "api_key": "sk-..."
}
```

Save that file as `app/cloud.local.json`. It is ignored by git.

## Required Local Model

The app checks the default ASR model files before processing:

```text
~/Documents/SpeechToTextData/model/whisper-large-v3-turbo/config.json
~/Documents/SpeechToTextData/model/whisper-large-v3-turbo/weights.safetensors
```

If either file is missing, Settings shows the exact missing path. Download URLs are listed in the
repository README model table.
