# Common questions

## Can I use it without an API key?

Yes. Local transcription, library browsing, and MCP do not require a model API key. Codex uses its
own account/model; only the optional cloud API flow needs an endpoint and securely stored key.

## Where are the installers?

[GitHub Releases](https://github.com/NorthBoundWisdom/sonafolio/releases) lists published packages.
If no tag has been released, build from source. A successful Actions trial does not create a release.

## Why does the OS warn about the developer?

macOS currently uses ad-hoc signatures without notarization; Windows installers are unsigned. Verify
the source and `SHA256SUMS`, then use your OS's normal allow-open workflow. See [installation](install.md).

## Why can't the Qt installer transcribe immediately?

It contains the interface and Qt runtime. Configure the CLI, FFmpeg, models, and ASR dependencies
separately, select `atot` in Settings, and run `atot doctor`.

## Are Intel Mac, iPhone ASR, or Linux ASR supported?

Stable macOS ASR targets Apple Silicon. iOS is a reader/subscription client. Linux has a Qt client,
but no promoted stable ASR backend. Automatic macOS packages are arm64 only.

## Why does CUDA 13 still report missing CUDA 12 DLLs?

The CTranslate2 wheel's ABI determines required DLLs. Follow the actual dependency error and provide
a compatible runtime. CPU is explicit opt-in:

```powershell
$env:ATOT_FASTER_WHISPER_DEVICE = "cpu"
$env:ATOT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
```

## Why do some folders still say Audio2Text?

These are compatible library, settings, and internal module identities. Display names and release
packages use SonaFolio; see the [compatibility list](naming.md).

## Is there semantic Q&A, diarization, or scheduled RSS polling?

The library offers title queries, groups, and reading state, without built-in cross-episode semantic
Q&A. Stable ASR backends do not provide diarization. RSS refresh is manual; external tools can schedule
CLI calls.

## How do I report a problem?

Use [GitHub Issues](https://github.com/NorthBoundWisdom/sonafolio/issues) with platform, version,
reproduction steps, and sanitized logs. Do not upload keys, models, media, or a private library.
