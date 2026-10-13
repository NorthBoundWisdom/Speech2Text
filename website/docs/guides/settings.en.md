# Settings and configuration

Swift uses Command-, and Save. Qt configures external CLI/tools, with some settings persisting immediately. Changes apply to future tasks, not automatic regeneration.

## Native sections

| Section | Purpose | Common choice |
| --- | --- | --- |
| Overview | Required model/CLI/tools, optional cloud | Resolve required issues, Recheck |
| Local ASR | Model/profile, current language selectors | large-v3-turbo + Chinese / Mandarin |
| Cloud Model | Endpoint/key/model/limits/prompts | Configure only for cloud API |
| Translation | SRT backend and Chinese target | Off by default; independent language |
| Workflow | Default cloud queue, local preference, chunks | Start locally |
| Library | Local/iCloud and authoritative location | Same library for all clients |
| Reading | Font/size/spacing/width | Display only |
| Runtime | Local runtime status/actions | Identify the real CLI |
| Config Sources | Effective values, layers, editable keys | Explain configuration |

Qt is not an exact copy of Swift's panes. Use its actual fields for external tools, model, languages, library, and optional cloud.

## Shared TOML

Default config.toml is under the data root:

```bash
atot config path
atot config list --json
atot config inspect --json
atot config get local.asr_model --json
```

| Key | Purpose |
| --- | --- |
| local.asr_model / local.asr_profile | Model/decode profile |
| local.languages | Current source hints array, empty = auto |
| summary.language | Current notes output, default zh |
| workflow.default_cloud_summary | Optional default cloud queue |
| workflow.local_only | Local preference |
| workflow.chunking / chunk_length / overlap | Strategy/seconds |
| translation.enabled / backend / target_language | SRT translation |
| library.storage / local_root / icloud_root | Library location |
| cloud.api_base / model | Endpoint/model |

```bash
atot config set local.asr_model large-v3-turbo
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config set workflow.default_cloud_summary false
```

Values are TOML; keep array quoting. Keys belong in the system credential workflow with hidden input, not public examples. See [cloud setup](cloud-summary.md).

## One-run overrides

```bash
atot -c 'local.languages=["zh"]' exec transcribe path/to/audio.m4a --local-only
```

C overrides this process; config set persists. Command language explicitly selects this task, omission uses effective settings. Legacy local.language migrates to the array on current saves.

ASR, notes, and captions are separate stages; reading style is only presentation. Language availability is not Chinese-validation parity.

## Verify a change

Save, query the key, run a short task, and inspect its actual work/run.json. If app and terminal disagree, compare executable, root, and storage before repeatedly changing models.

[Languages →](languages.md) · [Troubleshooting →](troubleshooting.md)
