# Common questions

## Can I work without a key?

Yes: local ASR, library reading, and MCP need no SonaFolio key. Codex uses its own account/model. Optional cloud calls need endpoint/model/key.

## What has been validated?

The primary evidence is Chinese podcasts on Apple Silicon with MLX Whisper and large-v3-turbo. English documentation does not imply equally validated English ASR. Other language choices are configurable, not parity claims.

## Are runtimes included?

Qt has client/libraries, not Python CLI, tools, CUDA, or weights. Swift includes the CLI wheel but still needs runtime/tools/models. See [installation](install.md).

## Why do screenshots differ from my app?

v0.9.0 predates column/toolbar/language improvements. Screenshots show current source, requiring rebuild/restart. Website publication does not update packages.

## Why an unidentified-developer warning?

Mac packages use ad-hoc signatures without Developer ID/notarization; Windows is unsigned. Verify source/checksums and decide whether to use the normal OS allow-open flow.

## Intel Mac, phone ASR, Linux ASR?

Stable Mac ASR/packages target Apple Silicon. iOS reads/manages subscriptions; Linux offers Qt without promoted stable ASR. Client availability is not backend validation.

## Can I choose just Chinese?

Current Local ASR offers Chinese / Mandarin; CLI accepts language zh. None means auto, several means auto with context, not a whitelist.

## Does output-language change regenerate notes?

No: it affects future work, defaulting to Chinese. Existing notes need deliberate regeneration; MCP also checks versions.

## Why missing CUDA 12 with CUDA 13 installed?

The actual CTranslate2 wheel defines DLL requirements. Supply compatible runtime or [choose CPU](install.md#windows-x64); no silent fallback.

## Does feed refresh process every episode?

No: metadata first, media/processing separately. CLI ordinary refresh has a limit; full-history is explicit and sees only feed-provided entries.

## Semantic Q&A, diarization, scheduled refresh?

Currently title queries, grouping, and state, without cross-episode semantic Q&A or stable diarization. Refresh is manual; external tools can schedule CLI.

## Is passing QA perfect accuracy?

No. Check important source claims and plan repairs before rerunning windows.

## Why Audio2Text names?

Compatible library, credentials, and build identities remain. Do not rename user data for branding. See [naming](naming.md).

## Backup and reporting?

Preserve the whole [library](guides/storage.md), with media/work separately. Sync is not backup. Report platform/version/steps/sanitized errors, not private keys or libraries. See [troubleshooting](guides/troubleshooting.md).
