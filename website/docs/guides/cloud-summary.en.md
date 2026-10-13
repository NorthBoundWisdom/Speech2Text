# Optional cloud API summaries

This sends transcript text to your configured model service, separately from local ASR and [Codex/MCP](agent-summary.md). It requires endpoint, model, key, and permission to send the episode text.

MCP uses the current conversation model without a SonaFolio key. Cloud availability, pricing, limits, and data policy belong to the provider.

## Configure

Swift Settings → Cloud Model exposes API Base, Key, Model, timeout, temperature, token limit, and prompts. Use actual provider values; these are placeholders:

```bash
atot config set cloud.api_base '"https://api.example.com/v1"'
atot config set cloud.model '"your-supported-model"'
```

The client uses the Responses API under that base. An endpoint supporting only another protocol may not work. Protocol errors should not be handled by guessing models repeatedly.

Use the native secure key field or hidden stdin, not shell arguments/history:

```bash
python -c 'import getpass, subprocess; subprocess.run(["atot", "config", "set", "cloud.api_key", "--stdin"], input=getpass.getpass("API key: "), text=True, check=True)'
```

Run in the managed environment, using python3 where appropriate. This is hidden input, not visible stdin pasting. Prefer CLI-managed system credentials for Qt and leave its key text field empty. Do not put keys in issues, screenshots, or chat.

## Inspect what will be sent

```bash
atot exec cloud prepare path/to/work-dir --json
```

Use the returned work directory. Preparation creates cloud/input/ without calling the API. Review it and privacy findings; automatic redaction does not guarantee removal of every private detail.

## Generate explicitly

```bash
atot exec cloud summarize path/to/work-dir --call-api --mode auto --json
```

Call-api is explicit model execution. Without it, a local scaffold is not a model/agent-authored summary.

| Mode | Behavior |
| --- | --- |
| auto | Direct readable text within safeguards, otherwise chunks |
| direct / from-readable | Direct readable source, with size limits |
| chunked | Chunk summaries then episode assembly |

```bash
atot exec cloud summarize path/to/work-dir --call-api --from-readable --stream-summary
```

Streaming is in-progress output, not final success. Required chunk failures, invalid/empty responses, and API errors must not be treated as completed substitute notes.

## Language and prompts

Current-source [output language](languages.md) governs direct/chunked summaries and short titles, taking precedence over conflicting saved language instructions. Other structure/content requests remain.

```bash
atot exec cloud summarize path/to/work-dir --call-api --prompt-file path/to/summary.prompt.md
```

Require grounding, timestamps, and uncertainty; do not disguise outside facts as source content. Title generation is a separate step and does not certify ASR.

## Check and retry

Inspect Summary and cloud/ artifacts for input, mode, and completion. Current chunk reuse accounts for output language. Authentication failures call for endpoint/protocol/model/key/timeout/limit checks, not rerunning ASR. Regenerate existing notes deliberately and preserve personal edits.

[Cloud errors →](troubleshooting.md#cloud-summary-fails) · [Settings →](settings.md) · [Privacy →](privacy.md)
