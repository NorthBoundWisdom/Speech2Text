# Troubleshoot by symptom

Locate the failing layer before downloading weights again or rerunning every ASR stage. Keep platform/version, exact command/stage/error, and sanitized logs.

## Check in order

1. Confirm app/CLI version.
2. Run doctor and models.
3. Compare app/CLI/MCP root and library.
4. Test a short Chinese local-only file to separate ASR from cloud.
5. Follow the relevant symptom below.

## Qt opens but cannot transcribe

The installer has client/Qt libraries, not CLI, FFmpeg, CUDA, or weights. Follow [installation](../install.md), select the real atot in Settings, and run that executable's doctor. Another global terminal installation is not a substitute.

## Missing weights {#model-files-are-missing}

Read exact models paths/files and prepare the [inventory](../models.md) manually. Do not mix MLX/CTranslate2 formats, use Downloads, or rename files as conversion.

## Missing media tools

Check both ffmpeg and ffprobe versions. App environment can differ from terminal; configure Qt tool/vcpkg roots or launch from the prepared environment. Qt SDK is not FFmpeg.

## Windows CUDA/cuDNN {#windows-cuda-or-cudnn-is-missing}

Follow actual CTranslate2 DLL requirements, compatible cuDNN, and PATH. CUDA 13 does not provide explicitly requested CUDA 12 DLLs. Missing libraries are not corrupt media.

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

CPU is explicit. Launch in the same environment; independent shortcuts do not inherit another session's variables. No silent CUDA-to-CPU switch occurs.

## Import/refresh failures {#import-or-feed-refresh-fails}

Separate Xiaoyuzhou episode import from show/RSS subscriptions. Check network and source availability. Full-history refresh only sees current feed entries; metadata does not guarantee old audio access.

## Repetition, omissions, unexpected language

For Chinese, explicitly use zh and the default model. Inspect audio/QA/windows and plan repair before rerunning. Mixed/other options do not have equal validation claims; hints are not a whitelist or translation switch.

## Empty/different libraries {#the-library-is-empty-or-different-on-another-device}

Compare actual paths/storage, filters, iCloud downloads, and Files permission. An empty identically named folder is not migration. See [storage](storage.md)/[iOS](ios.md).

## Missing Codex tools/episodes {#codex-cannot-see-the-mcp-tools-or-episodes}

Check mcp get sonafolio and executable; reopen after registration changes. Confirm server root and complete source. MCP needs no SonaFolio cloud key; adding one does not repair a connection.

## Summary version conflicts

Documents changed after reading. Fetch current episode/changed pages and hashes; do not disable checks or use another episode's versions. Nonempty notes require deliberate regeneration.

## Cloud failures {#cloud-summary-fails}

Verify Responses compatibility, actual model, access, key, timeout, and limits. A 403 is access/authentication, not an ASR problem. Failed chunks/formats or residual streamed text are not completed notes. MCP is a separate chosen workflow, not silent failure fallback.

## SRT refusal/failure {#subtitle-export-fails-or-refuses-a-file}

Existing output requires overwrite. Multiple inputs use output-dir, not one shared file. Check each result, decodability, ASR readiness, and translation settings. Diagnose the translation backend rather than claiming untranslated success.

## Missing width/language controls

v0.9.0 predates them. Build [current source](../install.md#release-and-current-source), restart the app, and check the real executable. Website updates do not update binaries.

## Report a problem

Use [Issues](https://github.com/NorthBoundWisdom/sonafolio/issues) with steps, platform/version, actual error, and sanitized evidence. Do not upload keys, weights, private media, or your complete library.

[FAQ →](../faq.md) · [Settings →](settings.md)
