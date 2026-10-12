# SonaFolio historical experiment index

This directory preserves dated snapshots and benchmark evidence. Audio2Text/AtoT are earlier names
of SonaFolio. Original numbers, failure codes, commands, and input identifiers remain unchanged;
non-English input names are language-test data. These records are not current installation or
platform-support instructions.

Current decisions are in [backend research](../BACKEND_RESEARCH.md), [roadmap status](../ROADMAP_STATUS.md),
and [branding](../BRANDING.md).

## Recorded experiments

| Record | Purpose and dated conclusion |
| --- | --- |
| [Three-audio baseline](process_three_audio.md) | Coffee podcast and two complete podcasts; baseline QA evidence |
| [Diagnostic gate smoke](asr_candidate_gate_smoke.md) | Echo-command plumbing; diagnostic only |
| [Local turbo gate](asr_candidate_gate_local_mlx_whisper.md) | Three successful commands, 1/3 guard passes; correction/review regressions |
| [Local 4-bit gate](asr_candidate_gate_local_mlx_whisper_4bit.md) | Three successful commands, 1/3 passes; about 1.5 GB versus 2.2 GB, length/token-ratio failures |
| [Full large-v3 gate](asr_candidate_gate_local_mlx_whisper_large_v3.md) | Three successful commands, 0/3 passes; about 4.0 GB, repetition regression |
| [Qwen/WhisperLiveKit decision](asr_candidate_gate_qwen_whisperlivekit_2026-06-24.md) | Qwen 0/3 timestamp guard passes; WhisperLiveKit 0/3 successful commands; neither promoted |
| [Decode sweep](asr_candidate_sweep_2026-05-31.md) | `no-prev`, conservative, anti-repeat, repair-strict; reduced repetition without default promotion |
| [Candidate matrix](asr_candidate_gate_matrix.md) | Runtime, memory, pass rate, and failure-code comparison |
| [Readiness snapshot](asr_candidate_readiness_2026-05-28.md) | Environment observations at that date, not a current readiness promise |

## Recording policy

Keep snapshots after an experiment completes. New experiments get a new date/name; update summaries
or this index instead of rewriting measured results. Translation of explanatory prose must preserve
numbers, statuses, input IDs, and commands. Input media, private datasets, models, and generated work
files are not committed.

Use names such as `<category>_<date>_<description>.md` and relative paths. Include the environment,
model/backend, inputs, exact commands, QA/runtime results, semantic observations, decision, and any
raw-output references. Preserve differences between gold, full-audio gates, diagnostic smoke, decode
sweeps, and readiness checks.

Current candidate commands are documented in [backend research](../BACKEND_RESEARCH.md). Historical
`.tools/` and `process/` references describe the experiment, not current setup. Current models resolve
under the data-root `model/` directory and require manual placement.
