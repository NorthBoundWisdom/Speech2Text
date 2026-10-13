# iPhone and iPad reader

iOS/iPadOS reads and manages the library/subscriptions. It does not run ASR or download audio for processing. Transcribe on a supported computer, then share documents.

## Requirements and distribution

Requires iOS/iPadOS 17+. No App Store, TestFlight, or automatic IPA release is provided. Source builds validate the simulator; real devices need your development signing/provisioning.

```bash
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform ios --scheme Audio2Text-iOS --configuration debug
```

See [development](../development.md). A macOS ad-hoc DMG is not an iOS package.

## Select an existing library

1. Confirm the Mac's iCloud authoritative location.
2. Wait for library documents to sync.
3. In iOS Settings, use Files to select the existing Audio2Text/Audio2TextLibrary folder and grant access.
4. Refresh and inspect an episode with an existing transcript.
5. Wait for Files/iCloud availability when documents are not downloaded.

Creating an empty folder with the same name does not copy the collection. [Storage](storage.md) lists compatible names/paths.

## Read and organize

Read source, transcript, existing notes, and manage read/star/archive/group state and feed metadata. Changes follow library files/system sync; weights/media stay on the processing machine.

Metadata-only entries have no reading documents. Return to the computer to download/process them, then wait for sync rather than expecting phone ASR.

## When clients differ

Compare actual folders/files, not only display names. Check filters, downloads, and Files permission; reselect the folder when needed. Avoid moving/deleting the whole library during sync. There is no fixed sync-latency promise, and iCloud does not replace backups.

[Sync troubleshooting →](troubleshooting.md#the-library-is-empty-or-different-on-another-device) · [Backup →](storage.md)
