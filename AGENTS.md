# SonaFolio Agent Guide

## Owner-Managed FreeCM Latest Policy

- This owner-managed repository follows the latest `FreeCM/master` on its
  existing primary branch without pull requests. This policy overrides generic
  FreeCM refresh and publication guidance elsewhere in the repository.
- Refresh from the host root with
  `git submodule update --remote --checkout FreeCM`; never run
  `git -C FreeCM pull` in the normally detached submodule.
- If `git diff --submodule -- FreeCM` is empty, stay silent: do not warn,
  commit, create a branch, or open a pull request.
- If the gitlink changes, run the relevant host validation, commit the FreeCM
  update and required compatibility edits on the existing primary branch, and
  push that branch directly without a pull request.
- Routine automatic refresh requires clean host and FreeCM worktrees. If either
  contains unrelated changes, stop and report them rather than mixing changes.
- The shared policy is documented in
  `FreeCM/.codex/freecm-wiring/assets/owner-managed-latest.md`.

This repository is public. Keep documentation, defaults, tests, and skills free of private absolute
paths, local usernames, machine-specific assumptions, and episode-specific tuning.

## Project Contract

- SonaFolio is a local Chinese podcast transcription CLI. The stable production path is
  macOS/Apple Silicon with MLX Whisper; Windows ASR uses the CLI with faster-whisper/CUDA. Qt client installers are available on macOS,
  Windows and Linux; iOS is a library reader. Linux ASR is not a stable supported backend.
- The stable production path is `atot exec transcribe` / `atot exec import` with the
  `large-v3-turbo` model alias. Old top-level command aliases such as `atot transcribe` and
  `atot import-xiaoyuzhou` are removed in CLI v2.
- Local runtime data lives under `~/Documents/SpeechToTextData/` by default and must stay out of git.
- `~/Documents/SpeechToTextData/model/` is the only local model storage location. `Downloads/` is
  temporary reference source and can be deleted without changing model resolution.
- Generated transcripts, model weights, downloaded audio, caches, and local reference checkouts are
  not source files.

## Development Commands

```bash
python3 configs/setup_local_app.py
~/Documents/SpeechToTextData/env/bin/atot doctor
~/Documents/SpeechToTextData/env/bin/python -m pytest
```

Useful focused checks:

```bash
~/Documents/SpeechToTextData/env/bin/python -m ruff check .
~/Documents/SpeechToTextData/env/bin/python src/scripts/check_public_paths.py
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_model_inventory.py
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_library.py Audio2TextLibrary
~/Documents/SpeechToTextData/env/bin/python -m pytest src/tests/test_xiaoyuzhou.py
~/Documents/SpeechToTextData/env/bin/python -m pytest src/tests/test_asr_candidate_presets.py src/tests/test_asr_candidate_readiness.py
~/Documents/SpeechToTextData/env/bin/python src/scripts/validate_run_json.py src/tests/fixtures/run.sample.json
```

Windows pytest discovery:

```powershell
where python
py -0p
python -m pip show pytest
python -c "import sys, pytest; print(sys.executable); print(pytest.__file__)"
python -m pytest
```

On Windows, prefer `python -m pytest` over invoking `pytest.exe` directly. A user-level
`pip install --user pytest` may place `pytest.exe` in a Scripts directory that is not on PATH, while
the module form still uses the pytest installed for the selected Python interpreter.

## Code Rules

- Do not develop on branches other than `main` unless the developer explicitly confirms
  branch-based work for the task. Without that confirmation, keep all development, commits, and
  pushes on `main`.
- Keep CLI behavior backward-compatible unless the user explicitly asks for a breaking change.
- Current product policy: do not add failure-compatibility or silent fallback behavior for summary,
  title, cloud, or local post-processing flows unless the user explicitly asks for it.
- When a required step fails, prefer surfacing the failure clearly over producing partial or heuristic
  replacement outputs.
- Remove obsolete compatibility code when the product policy has moved on and the user has asked to
  stop carrying it.
- Prefer shared rules in `src/atot/data/topic_rules.json` and `src/atot/data/review_rules.json`
  over hard-coded episode fixes.
- Keep backend-specific code behind `src/atot/backends/` or explicit candidate scripts.
- Keep reusable candidate comparison logic under `src/atot/candidate/`; `src/scripts/` should stay
  thin entrypoints.
- Do not promote a new ASR backend unless it passes the same candidate gate and semantic review.
- Use relative paths in examples. Use environment variables for user-specific directories.
- Keep deterministic corrections narrow, auditable, and recorded in `corrections.json`.

## Documentation Rules

- `README.md` is the public quick-start and stable CLI reference.
- `doc/README.md` is the documentation map.
- Create or keep root `TODO.md` only while concrete unfinished work exists; remove completed items
  instead of retaining an empty backlog. Completed roadmap evidence belongs in
  `doc/ROADMAP_STATUS.md`.
- `doc/BACKEND_RESEARCH.md` tracks backend research and should not become setup documentation.
- Experiment notes under `doc/experiments/` are historical records; update summaries instead of
  rewriting measured results.
- `.codex/skills/*/SKILL.md` must match the CLI behavior and public-path policy.

## Model Path Policy

The default model alias is `large-v3-turbo`, backed by
`mlx-community/whisper-large-v3-turbo`. Local model files should be placed under the data-root
`model/` directory, for example:

```text
~/Documents/SpeechToTextData/model/whisper-large-v3-turbo/
```

Candidate presets must also resolve model files under the data-root `model/`; do not add committed
absolute paths or `Downloads/` model references.

Agents must not download model files automatically. When a required model is missing, provide the
official download links and exact target files, then stop and ask the developer to download or place
the files under the data-root `model/` directory.

Model aliases, local paths, required files, and manual download URLs live in
`src/atot/data/model_inventory.json`. Update that inventory first, then update README if the
validated table changes.

## Windows CLI Notes

- Keep Windows ASR and setup independent of Swift, Xcode, or the macOS App build. The Qt client
  invokes the separately configured CLI; its installer does not bundle the ASR environment.
- Users may download faster-whisper model files into an arbitrary temporary download directory.
  Agents should move only clearly matching model files into the data-root `model/` directory and
  never commit those files.
- Use vcpkg-discovered tools such as `ffmpeg.exe` and `ffprobe.exe` through environment/PATH setup or
  runtime discovery. Do not commit local vcpkg roots or absolute machine paths.
- For this Windows workstation, the common vcpkg root is `C:\OpenSource\vcpkg`; wire it through
  `source_roots.lock.jsonc.in` / generated `source_roots.lock.jsonc` so FreeCM plugin
  `--init` and `--update` can expose it to commands.
- Keep Windows backend code behind `src/atot/backends/` and Windows runtime checks in small,
  testable modules.
- Prefer CUDA 13 when the installed CTranslate2 wheel can actually use it. If CTranslate2 reports
  missing CUDA 12 DLLs such as `cublas64_12.dll`, surface that compatibility issue clearly.
- Prefer explicit failures for missing CUDA, cuDNN, faster-whisper, ffmpeg, or model files. Do not
  add silent CPU or heuristic fallbacks unless the user asks for them. CPU is an explicit opt-in via
  `ATOT_FASTER_WHISPER_DEVICE=cpu`.

## Summary Files

`output/summary.md` is produced by the Codex Xiaoyuzhou import skill with the agent model. It is not
generated by the local ASR pipeline and should not be wired to a local model by default.

`atot mcp` also accepts summaries authored by the connected agent. Prefer its versioned library
read/write tools when available: read the complete transcript and QA, then publish through
`write_summary` with the current document hashes. Do not call a cloud API as part of this agent
summary path. Replacing a nonempty summary requires an explicit regeneration request.

## Public Website

- `website/` contains the SonaFolio product site and searchable user handbook, published through
  GitHub Pages. Keep platform, signing and download claims aligned with actual release workflows.
- Run a strict MkDocs build and `python configs/check_docs.py` when maintaining website/docs links.
- Use SonaFolio in product prose. Preserve only the compatibility identities in `doc/BRANDING.md`.
