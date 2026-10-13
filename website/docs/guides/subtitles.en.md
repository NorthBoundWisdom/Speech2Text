# Subtitles and translation

Use dedicated SRT export for a player/editor. It does not require prior library import; reusable work stays under data-root cache/srt/.

## Original-language export

```bash
atot exec srt path/to/video.mp4 --language zh --json
atot exec srt path/to/first.mp4 path/to/second.m4a --language zh --json
```

Default output is video.srt beside the media. Inspect every batch result, its status, and actual output path.

Swift's Generate SRT (Command-Shift-S) selects media, displays progress/path, and offers Reveal. Current source follows Local ASR source-language settings.

## Destination and hints

```bash
atot exec srt path/to/video.mp4 --language zh --language en
atot exec srt path/to/video.mp4 --language auto
atot exec srt path/to/video.mp4 --output path/to/captions.srt
atot exec srt path/to/first.mp4 path/to/second.mp4 --output-dir path/to/subtitles
atot exec srt path/to/video.mp4 --language zh --overwrite
```

Mixed hints do not translate. Output is for one exact file; output-dir handles multiple inputs. Existing destinations require explicit overwrite.

## Optional translation

Translation is off by default. To translate to Chinese:

```bash
atot config set translation.enabled true
atot config set translation.backend cloud
atot config set translation.target_language zh
```

Chinese uses a separate video.zh.srt destination. Swift Settings → Translation exposes that workflow. Disable with:

```bash
atot config set translation.enabled false
```

| Backend | Prerequisites | Boundary |
| --- | --- | --- |
| cloud | Endpoint, model, system-stored key | Subtitle text goes to API |
| local | Translation environment and weights | Local backend |

Local translation is an explicit choice, not a silent replacement for failed cloud. The default nllb-200-distilled-600m files/URLs are in the [inventory](https://github.com/NorthBoundWisdom/sonafolio/blob/main/src/atot/data/model_inventory.json); prepare them only for that workflow. Required translation failure must not be presented as untranslated success.

## Review

Check beginning, middle, and end in the intended player. Valid structure and monotonic timing do not establish recognition/translation accuracy. Normal library work also retains SRT/VTT; this export entrypoint supplies deliberate destination/overwrite behavior.

[Languages →](languages.md) · [Export troubleshooting →](troubleshooting.md#subtitle-export-fails-or-refuses-a-file)
