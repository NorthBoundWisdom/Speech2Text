# Privacy and data

## Local processing

Local ASR reads media and weights and writes transcripts, subtitles, QA, and logs without uploading
audio. Link imports, RSS refresh, and manual model downloads contact their source services.

The default root is `~/Documents/SpeechToTextData/`: `model/` stores weights, `materials/` stores
media, `work/` stores processing artifacts, and `cache/` stores logs and tools. The JSON/Markdown
library can use local storage or optional iCloud Drive.

## Optional network flows

| Feature | Data leaving the machine |
| --- | --- |
| iCloud Drive library | Episode JSON, transcripts, summaries, and state under OS sync policy |
| MCP / Codex summaries | Agent-read transcript, QA, and summary text enters the client conversation |
| Cloud API summaries | Text and supporting metadata go to your endpoint; original media/weights are not sent |

MCP itself does not call a model API. Whether the client's model runs locally is its own configuration.

## Credentials and logs

macOS uses Keychain, Windows CLI uses Credential Manager, and iOS uses device Keychain. Public
configuration does not return plaintext keys; no silent plaintext credential-store substitute exists.
Logs redact common secrets and bearer tokens but cannot detect every private detail in arbitrary text.
Review actual contents before sharing logs, screenshots, or transcripts.

The website configures no analytics or remote fonts. Search indexes and static resources are deployed
with the site. GitHub Pages still handles page requests, and external links follow their destination
service policies.

[Complete source privacy statement](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/PRIVACY.md)
