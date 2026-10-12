# Privacy

SonaFolio is designed for local podcast transcription. Audio and video files are processed on the user's
Mac by default, and local runtime data stays under the configured SonaFolio data root.

## Local Data

SonaFolio stores imported media, prepared audio, transcripts, QA reports, logs, model files, and job
metadata locally. These files are not uploaded by the local ASR pipeline.

## Cloud Summaries

Cloud summaries are optional. When enabled in the app Settings, SonaFolio sends transcript text and
supporting text metadata to the user-configured OpenAI-compatible API endpoint to generate a
summary. Audio files, video files, model files, raw chunk WAV files, and local redaction maps are
not sent by the cloud-summary path.

The macOS app and CLI share cloud API keys in Keychain, scoped to the resolved config file path.
The Windows CLI uses Windows Credential Manager; iOS uses device-only Keychain storage, accessible
when unlocked. No plaintext credential-store fallback is used. `config.toml` and mobile UserDefaults
store non-sensitive settings and a system-storage marker. Existing plaintext keys are migrated only
after a successful secure-store write; a failure preserves the old value and reports an error.
CLI local transcription and MCP do not require access to cloud credentials. CLI `config set
cloud.api_key --stdin` avoids putting the key in shell history. Logs and service responses redact
sensitive fields and common API-key/bearer-token patterns; custom secrets in arbitrary text cannot
be inferred reliably. Do not include credentials in transcript text or diagnostics.

The legacy HTTP service requires a separate random `ATOT_HTTP_TOKEN`, accepts only loopback binds,
checks Host, refuses browser Origin headers and requires JSON POST bodies. It exposes broader
workflow/configuration/deletion operations than MCP, so only trusted clients should have its token.

## Agent Summaries Through MCP

`atot mcp` runs as a local stdio server started by the MCP client. It exposes title-based episode
listing, versioned reading of library transcript/summary text and local QA, and agent-authored
summary publication. It does not expose cloud credentials, audio, model weights, arbitrary file
paths, deletion, or configuration changes. The server does not call a model API.

Text that Codex reads through MCP becomes part of the Codex conversation and is processed under
that client's account and data policies. This is separate from local ASR processing; a local MCP
transport does not imply that the client's model runs locally.

Writes require the current transcript and summary hashes. Replacing a nonempty summary also
requires an explicit overwrite request. The library summary and document index are updated; the
transcript and user read/star flags are preserved. A work copy and `agent-summary.json` provenance
record remain under the local data root. Writes to an iCloud Library follow its normal sync policy.

## User Control

App processing and its primary keyboard shortcuts default to local transcription and QA. Startup
cloud checks run only when automatic cloud summaries are explicitly enabled. Users can keep the
workflow local by leaving transcript upload disabled or by using CLI commands
with `--local-only`, and can use MCP when they choose to send transcript text to an agent.
Users can delete imported media, transcripts, logs, and generated outputs from
the local data root at any time.
