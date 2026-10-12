Four native client installers are provided: Windows Qt (x64), Linux Qt AppImage (x86_64),
macOS Qt (Apple Silicon) and macOS Swift (Apple Silicon). SHA256SUMS and per-asset build records
identify the exact tag commit and package bytes. All four builds must succeed before publication.

macOS apps use ad-hoc signatures and are not Developer ID signed or notarized. Windows setup is
unsigned. Linux requires Ubuntu 24.04 or a compatible glibc/desktop base; the AppImage may require
FUSE, or can run with --appimage-extract-and-run. Qt libraries, licenses, corresponding sources,
third-party notices and an SBOM are included. Windows setup installs the official Microsoft
Visual C++ Redistributable when installing the client.

These are client packages. Python CLI, FFmpeg, CUDA and model weights are not bundled into Qt
installers. Install/configure the CLI and FFmpeg separately for transcription. macOS Swift includes
the CLI wheel and uses its existing runtime setup flow. Models must be placed manually under the
data-root model/ directory. Linux client availability does not promote a Linux ASR backend.

No cloud API key is required for local browsing or agent summaries over MCP. No transcripts,
credentials, downloaded media or model weights are included in these release packages.
