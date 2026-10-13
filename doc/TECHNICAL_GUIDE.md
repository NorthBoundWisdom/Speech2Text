# SonaFolio development guide

This guide follows current source interfaces. See the [README](../README.md) for stable CLI usage,
[architecture](ARCHITECTURE.md) for boundaries, and [AGENTS](../AGENTS.md) for repository policy.

## Initialize

```bash
git clone --recurse-submodules https://github.com/NorthBoundWisdom/sonafolio.git
cd sonafolio
python3 configs/setup_local_app.py
source ~/Documents/SpeechToTextData/env/bin/activate
python -m pip install --constraint constraints/runtime.txt -e ".[dev]"
atot doctor
```

Python 3.10+ is required. Stable macOS ASR requires Apple Silicon. Swift clients target macOS 13+ and
iOS 17+ and require Xcode to build. Qt requires 6.8+; CI validates 6.12.0. Windows CLI setup does not
require Swift or Xcode.

Windows uses the data-root `env\Scripts\python.exe`; run tests with `python -m pytest`.
`ATOT_DATA_ROOT` can override the default `~/Documents/SpeechToTextData/`. Models belong under its
`model/` directory, not the source tree. Do not download weights automatically or commit outputs.

## Source interfaces

| Directory | Scope |
| --- | --- |
| `src/atot/` | CLI, workflows, ASR, library, MCP |
| `src/scripts/` | Thin validation and candidate experiment entrypoints |
| `src/tests/` | Python behavior, platform, and protocol tests |
| `app/Sources/`, `app/Tests/` | Swift clients, shared schema, tests |
| `qt/Audio2TextQt/` | C++/QML client |
| `configs/` | Setup, project generation, builds, installers |
| `website/` | English product site and handbook |
| `doc/experiments/` | Dated measurements; preserve original results |
| `FreeCM/` | Third-party build infrastructure at a pinned gitlink |

`WorkflowService` provides `run_transcribe()`, `run_import_xiaoyuzhou()`, `run_qa()`, `run_repair()`,
`run_cloud_prepare()`, `run_cloud_summarize()`, `run_srt()`, `run_subscriptions()`, and `run_library_*()`.
GUI clients use these workflows instead of duplicating ASR rules.

`ASRBackend` is the Protocol in `src/atot/backends/base.py`. Implement
`transcribe(audio_path, options: ASRTranscribeOptions)` and return normalized `text` and `segments`.
Candidates need the same quality gate and semantic review before promotion.

`create_mcp_server()` exposes only `list_episodes`, `get_episode`, `read_document`, and `write_summary`.
Complete transcript/QA reading, current hashes, and explicit overwrite authorization are required.

## Build locally

SwiftPM:

```bash
cd app
swift test --scratch-path ../build/swiftpm
swift build -c release --scratch-path ../build/swiftpm --product Audio2TextApp
```

From the repository root:

```bash
python3 configs/source_root_workflow.py --init
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform mac --scheme Audio2TextApp --configuration debug --distribution local
python3 configs/ios_workflow.py run --platform mac --scheme Audio2TextApp
```

iOS Simulator uses `--platform ios --scheme Audio2Text-iOS`. The generated `Audio2Text.xcodeproj`
is ignored; do not maintain it as source.

Qt:

```bash
python3 configs/source_roots.py init-seeds --quiet
python3 configs/source_roots.py materialize --quiet
python3 configs/qt_workflow.py config --configuration Release --qt-prefix <Qt-prefix>
python3 configs/qt_workflow.py smoke --configuration Release
ctest --test-dir build/Audio2TextQt -C Release --output-on-failure
```

Windows requires MSVC; CI uses Ninja for Windows/Linux and prepares the Linux SDK's ICU ABI
requirements. Manual ZIP and automatic installer contents differ; see the [Qt guide](../qt/Audio2TextQt/README.md).

## Validate

```bash
python -m ruff check .
python -m mypy
python -m pytest
python src/scripts/check_public_paths.py
python configs/check_repository_language.py
python src/scripts/validate_model_inventory.py
python src/scripts/validate_run_json.py src/tests/fixtures/run.sample.json
```

Public-source checks cover private paths and common credentials, including staged files. Default
macOS hooks require macOS/iOS Simulator Debug builds. Mock tests do not establish real ASR accuracy,
CUDA acceptance, or cloud API acceptance; those need the user's runtime, models, and data.

Website validation is independent:

```bash
python -m pip install -r website/requirements.txt
NO_MKDOCS_2_WARNING=true python -m mkdocs build -f website/mkdocs.yml --strict
python configs/check_docs.py --site build/website
```

See [quality tools](QUALITY_TOOLS.md) for dependency auditing and platform checks.

## Extend and diagnose

- Update `model_inventory.json` before model tables or required-file checks.
- Keep shared terminology and review rules in `src/atot/data/`, never episode-specific patches.
- Fail clearly for missing models, backends, CUDA, or required steps; do not add silent substitutes.
- Use `atot status --task-id <task-id>` for tasks and `atot exec qa <work-dir>` for document health.
- Logs live in `cache/logs/` and the relevant work directory. Remove private content before sharing.
- Keep English source prose and interfaces; document localized language assets explicitly.
- Preserve `atot`, internal module names, and storage identities listed in [branding](BRANDING.md).

## Publish

Tag pushes build Windows Qt EXE, Linux Qt AppImage, and macOS Qt/Swift DMG installers. macOS uses
ad-hoc signatures without certificates; optional manual Developer ID/notarization flows remain.
Pages deploys the website from `main`; PRs run build checks only.

[Releases](CI_RELEASES.md) · [Licensing](RELEASE_LICENSES.md) · [Website](WEBSITE.md)
