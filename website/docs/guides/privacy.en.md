# Privacy and data boundaries

Local ASR, source imports, iCloud, agents, and cloud APIs are separate flows. Know which one is enabled before deciding what leaves the computer.

## Local processing

ASR reads media/weights and writes text, captions, QA, and logs without uploading audio. URL imports, RSS, and manual weight downloads contact their services. See [storage](storage.md).

| Optional flow | Data leaving the machine |
| --- | --- |
| iCloud | Library records/documents/state through OS sync |
| MCP/Codex | Agent-read source, QA, and notes enter conversation |
| Cloud summaries/translation | Text/context goes to your endpoint |

MCP itself calls no model. Client-local inference depends on its configuration; local stdio does not guarantee that all data remains local.

## Credentials and sharing

CLI/native clients use system credential mechanisms. Prefer CLI-managed keys for Qt. Do not put keys in public files, arguments, transcripts, screenshots, logs, or issues.

Redaction recognizes common patterns, not every private fact. Review real content before sharing and inspect prepared cloud input.

## Backup and website

Sync also propagates deletion; arrange independent backup. Model/media/work/library cleanup has different effects described in [storage](storage.md).

The website configures no analytics or remote fonts. Static search/resources are published with it. GitHub Pages handles requests; external destinations follow their own policies. Screenshots are reviewed user-provided images; the settings screenshot containing private paths is not published.

[Source privacy reference](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/PRIVACY.md) · [Summary paths](../handbook.md#choose-a-summary-path)
