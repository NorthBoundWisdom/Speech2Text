# Audio2Text Library Layout

Audio2Text now treats `Audio2TextLibrary/` as the only authoritative user-facing data store.
App startup and normal CLI workflows read Library records from this layout only.

## Layout

```text
Audio2TextLibrary/
  manifest.json
  subscriptions/<subscription_id>.json
  groups/<group_id>.json
  episodes/<episode_id>/episode.json
  episodes/<episode_id>/documents/summary.md
  episodes/<episode_id>/documents/transcript.md
  tombstones/episodes/<episode_id>.json
```

Local runtime data stays outside the Library:

```text
materials/<episode_id>/
work/<episode_id>/
model/
```

## Episode Documents

Readable episode documents live under:

```text
Audio2TextLibrary/episodes/<episode_id>/documents/summary.md
Audio2TextLibrary/episodes/<episode_id>/documents/transcript.md
```

Each document entry in `episode.json` must include `name`, `path`, `bytes`, and `sha256`; zero-byte
or missing-byte documents are not treated as synced readable content.

## Validation

Validate the Library after direct edits:

```bash
python src/scripts/validate_library.py Audio2TextLibrary
```

If validation reports extra files, absolute local paths, stale manifest entries, or tombstone
conflicts, fix the Library record instead of adding compatibility reads.
