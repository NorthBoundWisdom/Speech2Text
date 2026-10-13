# Storage, backup, and migration

The authoritative library and local runtime data serve different purposes. Work alone is not a library backup; the library alone does not preserve recordings or weights.

## Local root

Default ~/Documents/SpeechToTextData/:

```text
SpeechToTextData/
  config.toml
  env/                 Python runtime
  model/               Manual weights
  materials/           Media and private import metadata
  work/                ASR, QA, repair and summary evidence
  cache/               Logs, tools, temporary data
  Audio2TextLibrary/    Local authoritative library
```

CLI accepts ATOT_DATA_ROOT; Qt passes its data-root to the service. Set the environment before launch; it does not move files. Setup prepares the default environment, not a complete migration by changing a variable.

## Authoritative library

```text
Audio2TextLibrary/
  manifest.json
  subscriptions/<subscription_id>.json
  groups/<group_id>.json
  episodes/<episode_id>/episode.json
  episodes/<episode_id>/documents/transcript.md
  episodes/<episode_id>/documents/summary.md
  tombstones/episodes/<episode_id>.json
```

Records contain document sizes/hashes for reading and publication. Do not change documents while ignoring their index; MCP tools publish with version checks.

Default iCloud:

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
```

Models/media/work remain local. Compatible Audio2Text names should not be renamed just for branding.

## What to back up

| Goal | Preserve |
| --- | --- |
| Reading, groups, feeds, deletion state | Full library, including tombstones |
| Audio and evidence | materials/work |
| Preferences | config.toml; credentials separately |
| Avoid re-preparing weights | model |

Environments can be recreated; do not copy one OS's env to another. iCloud propagates changes/deletions and is not an independent backup.

## Move safely

1. Stop processing/agent writes.
2. Confirm the actual root and make an independent complete backup.
3. Ensure iCloud files are available, then copy the whole library.
4. Point app/CLI/MCP at the same target.
5. Check counts, sample text/notes, groups, and state.
6. Run library status; developer setup can also validate the library.
7. Only retire the old location after read/write/recovery checks.

Storage switching does not promise automatic merging; removing tombstones is not a migration procedure.

## Cleanup and restore

Temporary cache cleanup differs from deleting media (source loss), work (QA/evidence loss), model (future ASR blocked), or library (reading data deleted). Restore a complete backup and verify documents. Copying config.toml does not transfer the system key store.

[iOS →](ios.md) · [Privacy →](privacy.md)
