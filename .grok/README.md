# Audio2Text Grok project config

Grok does not scan Codex `.codex/skills`. `.grok/skills` is a relative symlink
to `../.codex/skills`, so both harnesses share one skill tree.

Edit SOP, scripts, and assets only under `.codex/skills/`. Command examples in
those files keep the `.codex/skills/...` paths.

## Invoke

- Slash: `/<skill-name>`
- Menu: `/skills`
- Inspect: `grok inspect`

## Catalog

| Skill | Use |
| --- | --- |
| `audio2text-transcribe` | Import and locally transcribe podcast or audio sources with this repository's Audio2Text CLI, then report QA and opti... |
