# Library and subscriptions

One authoritative library stores episodes, subscriptions, groups, reading state, and documents.
Media and processing caches stay on the local machine, outside the iCloud library.

## Import and subscribe

Import local media or a Xiaoyuzhou episode, select a group, and process after import.

```bash
atot exec subscriptions add "https://www.xiaoyuzhoufm.com/podcast/<podcast-id>" --group-name Default
atot exec subscriptions list
atot exec subscriptions refresh --all
```

RSS and Xiaoyuzhou feeds use manual refresh. There is no built-in scheduling promise; external tools
can invoke the CLI when automation is needed.

## Read and organize

Clients show Overview, Transcript, and existing Summary. Use groups, favorites, read/archive state,
and title queries to organize episodes:

```bash
atot exec library status --json
```

Deleting an episode removes its library record and documents and writes a tombstone, preventing
subscription refresh from silently reimporting it. Confirm you no longer need those documents.

## Share between Mac and iOS

The default iCloud folder is:

```text
~/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text/Audio2TextLibrary/
```

Local-storage mode uses:

```text
~/Documents/SpeechToTextData/Audio2TextLibrary/
```

In iOS/iPadOS Settings, select the existing `Audio2Text` or `Audio2TextLibrary` folder through Files.
Compatibility folder names are unchanged; the product is SonaFolio.

iOS reads documents, refreshes subscription metadata, and manages state. It does not run ASR or
download audio for processing. iCloud availability depends on OS sync, networking, and file state.

[Storage and privacy](privacy.md) · [Compatibility names](../naming.md)

## Adjust the desktop workspace

Drag the vertical dividers to resize Sources and Episode List. Their toolbar buttons independently
hide or restore each column, even when both are hidden. The desktop clients remember expanded
widths and visibility without clearing your selected episode.

On macOS, the View menu offers the same actions and Show All Columns. Use `Control-Command-S` for
Sources and `Control-Command-L` for Episode List. Qt uses `Ctrl+Shift+S` and `Ctrl+Shift+L`.
