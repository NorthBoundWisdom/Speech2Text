# SonaFolio Roadmap Status

This file records completed roadmap implementation evidence. It separates repo-verifiable work from
acceptance items that require local audio, model weights, or cloud credentials.

## Repo-Verified Coverage

| Roadmap area | Current status | Evidence |
|---|---|---|
| P0 QA gate | Implemented and tested | `atot exec qa`, `qa.json`, `qa.md`, timeline/text/subtitle/chunk-integrity, chunk core coverage, and merge-retention checks |
| P0 SRT/VTT validation | Implemented and tested | `src/atot/subtitles.py`, `validate_output_bundle.py` |
| P0 Chinese punctuation | Implemented and tested | `src/atot/punctuation.py` |
| P0 readable outputs | Implemented and tested | `transcript.readable.md`, `transcript.timestamped.md`, enforced by `validate_run_json.py` and `validate_output_bundle.py` |
| P0 cloud/local separation | Implemented and tested | `output/cloud/`, `atot exec cloud prepare` |
| Agent-authored summaries through MCP | Implemented and protocol-tested | `atot mcp`, versioned/paged library reads, explicit summary write-back, `src/tests/test_agent_summary.py`, `src/tests/test_mcp_server.py`; default App processing requires no cloud key |
| Resizable/collapsible desktop columns | Implemented and interaction-tested | Native macOS split items, persistent widths/visibility, toolbar/View controls; Qt divider hit regions and real QML drag/collapse tests |
| SonaFolio brand and public website | Implemented | `doc/BRANDING.md`, MkDocs Material `website/`, Pages workflow and documentation/link checks |
| P0 project naming | Implemented | README title uses `SonaFolio`; distribution remains `audio2text-local`, Python module and CLI remain `atot`; existing data paths and bundle identifiers are preserved |
| P1 smart chunking | Implemented and unit-tested | `--chunking smart`, `src/atot/vad.py` |
| P1 repair | Implemented and unit-tested | `atot exec repair`, `output/repair/`, per-window raw/corrected JSON, `validate_repair_artifacts.py`, `src/atot/repair.py` |
| P1 fingerprints | Implemented and tested | `input_file`, `prepared_audio`, ASR fingerprint fields in `run.json` |
| P1 audio preparation trace | Implemented and tested | `prepared_audio.prepare_tool`, `prepare_command`, WAV metadata in `run.json` |
| P1 chunk-cache safety | Implemented and tested | ASR fingerprint includes `chunk_layout_sha256`; `validate_run_json.py` checks cache-identity hash consistency |
| P1 postprocess-only rerun | Implemented and tested | `src/atot/postprocess.py` |
| Prompt construction guardrail | Implemented and tested | full topic metadata is not injected; capped summary and terms stay under 800 chars |
| P2 cloud input package | Implemented and tested | `output/cloud/input/manifest.json`, time-range text chunks with previous-chunk context, QA/review/topic files, prompt templates, `validate_cloud_package.py` |
| P2 cloud prompt templates | Implemented and packaged | `doc/cloud_prompts/*.zh.md`, copied to `cloud/input/prompts/*.prompt.md` |
| P2 cloud output schemas | Implemented and tested | output manifest plus schema validation for chunk-level summaries, summary, chapters, shownotes, title candidates, social copy, terms, chunk uncertainty rollup, `fact_or_term_uncertainties.md`, glossary suggestions, polish patches |
| P2 cloud patch application | Implemented and tested | timestamped polish patch schema with `reason`/`risk`; patch application remains a lower-level validator flow |
| P2 cloud API hook | Implemented, mocked, and locally validated | OpenAI-compatible `--call-api` text requests, per-chunk and episode audit files, complete glossary/polish outputs; ignored real-provider evidence passes `validate_cloud_package.py --mode both` and `validate_runtime_evidence.py --require-cloud-api` |
| Privacy boundary | Implemented and tested | PII scan/redaction for phones, emails, IDs, address-like text, context-labeled private names, privacy hints, CLI confirmation prompt, `--redact pii`, local redaction map exclusion and manifest validation |
| Glossary rule layers | Implemented and tested | `safe_global`, `contextual_regex`, `review_only`, auditable matches |
| Gold fixtures | Implemented and validated | text-only fixtures under `tests/gold/` |
| Gold benchmark runner | Implemented and unit-tested | `src/atot/gold.py`; reports CER, term hits, QA/SRT status, unknown ASCII, repeats, gaps, runtime, peak memory, optional acceptance gate failures |
| Whisper parameter matrix runner | Implemented and unit-tested | candidate/gold runner modules with optional promotion thresholds |
| Backend interface metadata | Implemented and tested | backend capabilities plus normalized `text/segments/start/end/text/words/confidence/raw` result contract |
| Backend promotion evidence | Implemented and unit-tested | `asr_candidate_gate.py` JSON summaries plus `validate_backend_promotion.py` semantic-review gate |
| Candidate backend decisions | Evaluated and not promoted | Qwen completed 3/3 commands but failed timestamp compatibility on all rows; WhisperLiveKit failed 3/3 full-audio commands because its requested MLX backend was unavailable or incompatible with the supplied local model |
| Optional diarization | Implemented as inferred metadata | text-inferred metadata helpers; no promoted stable CLI command |
| UI wrapper | Implemented and tested | Python UI module starts `atot exec ...` subprocesses, status/model endpoints, QA/repair plan/latest repair run/cloud/chunk progress payload, output folder opening |
| Batch queue | Implemented and tested | Python batch queue module starts `atot exec transcribe`, records output directories, and preserves local-only passthrough |
| Local-only guardrail | Implemented and tested | all commands accept `--local-only`; cloud commands refuse generation/application |
| Manual Library refresh | Implemented and tested | returns an explicit task handle; isolated focused test and the complete Swift suite pass without polling timeouts |
| Developer ID release | Implemented and unit-tested | hardened runtime, secure timestamp, `notarytool --wait`, stapling, stapler validation, and Gatekeeper assessment; release credentials stay in a Keychain profile. A credentialed Apple submission remains release-host acceptance and is not claimed by repository tests |
| Dependency security floors | Implemented and tested | `constraints/runtime.txt` is consumed for fresh and existing editable environments; approved audit policy ignores only the unfixed `torch` CVE by ID |

## Final Acceptance Checklist

| Roadmap acceptance item | Status |
|---|---|
| 95-minute Chinese podcast can transcribe locally without manual supervision | Locally validated with ignored 5725s output; verify with `validate_runtime_evidence.py --long-output <output>` |
| Audio/video are not uploaded to cloud | Repo-verified by cloud manifest/tests and `validate_cloud_package.py`; real API use still depends on command choice |
| Outputs include raw, corrected, timestamped, readable, SRT, VTT | Repo-verified and enforced by `validate_run_json.py` plus direct output bundle validation |
| `run.json` traces input, model, prompt, glossary, chunk, fingerprint, QA, repair, cloud state | Repo-verified and enforced by shared package validation, `validate_run_json.py`, and output path consistency checks |
| Prepared WAV metadata records conversion command and audio properties | Repo-verified |
| ASR prompt stays short and term-focused instead of using full topic notes | Repo-verified |
| Resume can reuse chunks without reusing stale input cache | Repo-verified for fingerprint logic; long-run evidence still recommended |
| ASR cache identity includes input, prepared WAV, chunk layout, model, prompt, and decode parameters | Repo-verified |
| Glossary changes can refresh outputs without ASR rerun | Repo-verified |
| QA detects large gaps, repetition, SRT errors, long subtitles, unknown terms | Repo-verified |
| QA detects missing/failed/stale chunk JSON, chunk manifest mismatches, core coverage gaps, and merge-retention gaps | Repo-verified |
| Bad windows can be repaired locally and audited | Repo-verified and locally validated with ignored real-ASR evidence; `validate_repair_artifacts.py` and `validate_runtime_evidence.py --repair-output` passed |
| Cloud stage handles text package and writes manifest, summary, chapters, title candidates, social copy, terms, polish patches | Repo-verified and locally validated with ignored real-provider evidence; strict cloud runtime validation passes |
| Cloud stage does not overwrite base ASR outputs | Repo-verified; `validate_run_json.py` enforces `cloud.audio_uploaded=false` |
| Three gold samples quantify model/parameter comparisons | Repo-verified fixtures plus an ignored local three-sample matrix covering both `condition_on_previous_text` values; `validate_runtime_evidence.py --gold-report` passed |
| CLI remains the core and UI only wraps it | Repo-verified; UI starts CLI subprocesses, reads run/QA/repair/cloud/chunk state, and opens output folders; batch can pause, resume, and open output directories |

## Current Verification Commands

```bash
python -m pytest
python -m ruff check .
python src/scripts/check_public_paths.py
python src/scripts/validate_model_inventory.py
python src/scripts/validate_run_json.py src/tests/fixtures/run.sample.json
python src/scripts/validate_gold_set.py
python src/scripts/validate_output_bundle.py process/<batch>/<episode>/output
python src/scripts/validate_cloud_package.py process/<batch>/<episode>/output --mode both
python src/scripts/validate_repair_artifacts.py process/<batch>/<episode>/output
python src/scripts/validate_library.py Audio2TextLibrary
python src/scripts/validate_runtime_evidence.py \
  --long-output process/<batch>/<episode>/output \
  --gold-report output/benchmark/gold/<timestamp>/report.json \
  --repair-output process/<batch>/<episode>/output \
  --cloud-output process/<batch>/<episode>/output \
  --require-cloud-api
```

## Requires Local Runtime Evidence

The current roadmap evidence set is complete. Future backend proposals must collect fresh ignored
runtime evidence and be recorded as actionable unfinished work before any promotion decision.

## Deliberately Not Promoted

- No new ASR backend has been made the default.
- Qwen and WhisperLiveKit remain experimental after their recorded 2026-06-24 gate failures.
- Diarization remains optional and text-inferred unless a local diarization backend passes evaluation.
- The UI wraps CLI state and does not reimplement core transcription, QA, repair, or cloud logic.
- Gold audio files are not committed; only public reference text and metadata are source files.
