# SonaFolio documentation

The [website and handbook](https://northboundwisdom.github.io/sonafolio/) cover installation,
transcription, library management, and agent summaries. The [repository README](../README.md) is the
quick start, manual model inventory, and stable CLI reference.

## Users and data

| Document | Contents |
| --- | --- |
| [README](../README.md) | Platform support, runtime setup, models, and CLI commands |
| [Privacy](PRIVACY.md) | Local, iCloud, MCP, and optional cloud API data boundaries |
| [Library layout](LIBRARY_LAYOUT.md) | Authoritative JSON/Markdown library, processing cache, tombstones |
| [QA and repair](QUALITY_LOOP.md) | Review, correction records, and targeted repair |
| [Branding](BRANDING.md) | Product name and retained compatibility identifiers |

## Development and distribution

| Document | Contents |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | CLI, Swift, Qt, MCP, and ASR boundaries |
| [Development guide](TECHNICAL_GUIDE.md) | Builds, source interfaces, validation, and extension |
| [Agent guide](../AGENTS.md) | Repository policies and public-source requirements |
| [Swift client](../app/README.md) | macOS/iOS builds and runtime |
| [Qt client](../qt/Audio2TextQt/README.md) | CMake, SDK, and client packaging |
| [CI and releases](CI_RELEASES.md) | Four-platform packaging, signing, and tag publication |
| [Website](WEBSITE.md) | Local preview, strict builds, and GitHub Pages deployment |
| [Release licensing](RELEASE_LICENSES.md) | Third-party sources, notices, and artifact verification |
| [Open-source audit](OPEN_SOURCE_AUDIT.md) | Source audit results and acceptance limits |
| [Quality tools](QUALITY_TOOLS.md) | Ruff, mypy, dependency auditing, and tests |

## Research and historical evidence

- [Roadmap status](ROADMAP_STATUS.md) records completed implementation and validation evidence.
- [Backend research](BACKEND_RESEARCH.md) records candidate gates, not installation instructions.
- [Experiment index](experiments/README.md) explains dated results and historical names.
- [Glossary example](examples/glossary.zh.json), [QA example](examples/qa.balanced.json), and
  [ASR prompt](../src/atot/data/prompt.zh.txt) are reference language assets.
- Text-processing prompt templates live in `cloud_prompts/`. User cloud packages and local work data
  must not be committed.

Current documentation follows source behavior; individual release notes describe downloaded packages.
Historical measurements do not establish support for current platforms, models, or versions.
