# Source, summary, and subtitle languages

Three choices govern different stages. A Chinese summary does not automatically translate the transcript, and subtitle translation is not an ASR hint.

| Setting | Effect | Source translation? |
| --- | --- | --- |
| Transcription Languages | Single hint or mixed context | No; preserves speech |
| Summary Output Language | Body, headings, titles, MCP guidance | Authors notes in that language, preserves transcript |
| Subtitle target | Optional SRT translation | Translates subtitle output |

Checkboxes and the output selector are source features after v0.9.0, under **Settings → Local ASR** in Swift/Qt. Existing explicit old language settings remain readable.

## Validated Chinese workflow

Select Chinese / Mandarin and keep output language zh for the [first-run procedure](../quick-start.md). New implicit configurations default to auto detection. Auto, mixed, and other language choices are available without claiming validation parity with Chinese.

## How checkboxes work

| Selection | Behavior |
| --- | --- |
| None | Auto, no fixed hint |
| One | Pass that language hint |
| Several | Auto plus selected-language context |

Mixed hints are not a strict whitelist or a guarantee at every language switch. Whisper accepts one hint or auto. Mixed mode preserves each spoken language rather than translating everything.

Save in Swift; Qt language choices persist immediately. Automatic Detection clears selections. Changes apply to future tasks, not existing text.

Catalog: zh, en, ja, ko, yue, de, fr, es, ru, pt, it, ar, hi, vi, th, id. Selection is not an accuracy certification.

## Summary output

Default zh governs the body, Markdown headings, short titles, get_episode guidance, and copied Codex instructions. It overrides conflicting language requirements in saved summary/title prompts, preserving other content/structure requests. Selecting English takes precedence over a Chinese prompt without dropping its request to explain unfamiliar terms.

Saving requires no key and does not regenerate existing summaries. An explicit conversation language request can override the agent's configured default.

## CLI settings and overrides

```bash
atot config set local.languages '["zh"]'
atot config set summary.language zh
atot config get local.languages --json
atot config get summary.language --json
atot exec transcribe path/to/audio.m4a --language zh --local-only
atot exec transcribe path/to/audio.m4a --language zh --language en --local-only
atot exec transcribe path/to/audio.m4a --language auto --local-only
```

Import/SRT accept the same language option. Empty local.languages means auto; omission uses stored values. Legacy local.language is migrated on current saves. If both exist, the array wins. Auto/detect clear hints, jp normalizes to ja. Explicit old preferences remain; new implicit defaults are auto.

## Independent subtitle translation

Settings → Translation controls SRT. The current native UI offers Simplified Chinese output; CLI target/backend support needs its own check. Cloud translation requires configuration; local requires separate weights. Summary language does not enable translation.

[Subtitles →](subtitles.md) · [MCP →](agent-summary.md)
