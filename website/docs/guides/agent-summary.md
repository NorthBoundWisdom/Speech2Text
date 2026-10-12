# Codex summaries and write-back

`atot mcp` is a standard MCP stdio service. The connected agent authors summaries using its own model;
the server does not call a cloud model API. This flow requires no SonaFolio API key.

## Connect

Prepare the CLI, then register it in Codex on macOS:

```bash
codex mcp add sonafolio -- "$HOME/Documents/SpeechToTextData/env/bin/atot" mcp
codex mcp get sonafolio
```

Windows:

```powershell
codex mcp add sonafolio -- "$env:USERPROFILE\Documents\SpeechToTextData\env\Scripts\atot.exe" mcp
```

`sonafolio` is a client-chosen alias. Existing `audio2text` registrations continue to work. Reopen the
Codex session and confirm tools are available.

## Request a summary

For example:

> Use the sonafolio MCP connection to find transcribed episodes without summaries. Read the complete
> transcript and QA, write a Markdown summary, preserve useful timestamps, and publish it to the library.

| Tool | Purpose |
| --- | --- |
| `list_episodes` | Title lookup, pagination, and pending-summary filtering |
| `get_episode` | Metadata, QA state, and current document hashes |
| `read_document` | Paged transcript, summary, or QA; read until `next_offset` is null |
| `write_summary` | Publish agent-authored text after checking current transcript and summary hashes |

If documents change during reading, writes fail and the agent must reread. Replacing an existing
nonempty summary requires your explicit regeneration request; the agent must not overwrite it on
its own.

## Data boundaries

Agent-read text enters its conversation and follows the client's account policies. Local stdio does
not imply local model inference. MCP does not expose keys, weights, media downloads, arbitrary path
access, or deletion tools. Optional cloud API summaries are a separate explicitly configured flow.

[Privacy and data](privacy.md)
