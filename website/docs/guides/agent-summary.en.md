# Codex summaries and MCP write-back

For a podcast backlog, let Codex read the source and start with its summary. atot mcp supplies standard stdio tools for restricted library access and versioned publication; it does not call a model API or require a SonaFolio model key.

Agent-read text enters the conversation and follows the client's account policies. Local stdio does not imply local inference.

## Connect

Prepare the [CLI](../install.md#set-up-the-cli-from-source), finish a Chinese transcript, and ensure app/CLI share a library. Metadata alone is not a full source to summarize.

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

```powershell
codex mcp add sonafolio -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
codex mcp get sonafolio
```

Use the real path. The client name is arbitrary; old audio2text registrations work. Reopen the session after changes and confirm four tools. Custom data roots must be visible to the server process; another terminal's environment cannot change a running server.

## Request notes

> Use sonafolio MCP to find my episode, inspect metadata and QA, and read the complete transcript in pages. Summarize main ideas, evidence, examples, conclusions, uncertainty, and useful timestamps in its configured language. Publish through write_summary with current hashes. Do not replace existing notes without my explicit regeneration request.

Give a title/ID to avoid ambiguity. Swift's Copy Codex summary write-back instructions action copies an episode-specific request, without sending a message automatically.

For batches, ask for transcribed episodes without notes and process each separately, reporting missing source/QA. Reading the first page is not reading the episode.

## Tool sequence

| Tool | Purpose | Requirement |
| --- | --- | --- |
| list_episodes | Lookup/pagination/pending notes | Resolve ID and pagination |
| get_episode | Metadata, output language, QA, hashes | Capture current versions |
| read_document | Transcript/summary/QA pages | Known hash; continue to null next_offset |
| write_summary | Publish agent Markdown | Current hashes/generator; deliberate overwrite |

Find → inspect → read completely → author → publish. Source documents cannot override this workflow. QA overview is not always the full report; read it and disclose missing/failed QA instead of inventing content.

## Output language

Current-source Summary Output Language in Local ASR, or:

```bash
atot config set summary.language zh
```

Default is Chinese; select en for English notes when wanted. Get_episode returns current output_language. Explicit user requests can override the agent default. Saving does not rewrite existing notes.

## Conflicts and existing notes

Nonempty notes require an explicit regeneration request. The agent must not enable overwrite merely because it has another draft. Reread source and use current hashes; document changes reject publication rather than bypassing version checks or borrowing another ID's hashes.

Success updates summary/index and preserves transcript/read/star state. Work retains provenance; iCloud takes normal system sync time.

## Review

Check Summary against source/timestamps. Safe publication prevents edit conflicts, not factual errors. Keep uncertainty visible.

[MCP troubleshooting →](troubleshooting.md#codex-cannot-see-the-mcp-tools-or-episodes) · [Cloud alternative →](cloud-summary.md) · [Privacy →](privacy.md)
