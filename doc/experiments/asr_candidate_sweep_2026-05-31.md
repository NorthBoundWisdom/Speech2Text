# ASR Candidate Sweep 2026-05-31

## Goal

Use the current local MLX archive to improve long-form Chinese podcast stability, with emphasis on:

- repeated-phrase suppression
- empty or near-empty windows
- runaway high-compression spans
- keeping enough text coverage to avoid obvious deletions

Stable candidate set available locally at the time of this run:

- `mlx-whisper-local-large-v3-turbo`
- `mlx-whisper-local-large-v3-turbo-no-prev`
- `mlx-whisper-local-large-v3-turbo-conservative`
- `mlx-whisper-local-large-v3`
- `mlx-whisper-local-large-v3-no-prev`
- `mlx-whisper-local-large-v3-4bit`
- `mlx-whisper-local-large-v3-4bit-no-prev`

## Library Audit Snapshot

The local output audit over the current library (`output/`) found:

- 23 recorded runs
- 22 QA failures
- 17 runs with empty corrected segments
- 13 runs with review issues

Most common QA issue groups were:

- `high_compression_ratio_segment`
- `adjacent_duplicate_segment`
- `repeated_phrase`
- `empty_segment_text`

This was enough to justify a targeted candidate sweep before any more glossary-only tuning.

## Sample-Window Sweep

### Windows

Four 120-second benchmark windows were cut from real episodes with `src/scripts/create_sample_from_episode.sh`:

- `0517_repeat_window`: repeated-phrase blocker around `00:02:07`
- `0527_empty_window`: long high-compression / empty-window region around `00:45:40`
- `0521_runaway_window`: late runaway repetition region around `01:20:05`
- `0417_early_empty_window`: early empty-window region near the start of the episode

### Commands

Representative commands:

```bash
src/scripts/output_library_audit.py --output-root output --json

src/scripts/asr_candidate_sweep.py \
  process/bench_samples/0517_repeat_window.wav \
  process/bench_samples/0527_empty_window.wav \
  process/bench_samples/0521_runaway_window.wav \
  process/bench_samples/0417_early_empty_window.wav \
  --preset mlx-whisper-local-large-v3-turbo \
  --preset mlx-whisper-local-large-v3-turbo-no-prev \
  --preset mlx-whisper-local-large-v3-turbo-conservative \
  --output-dir output/benchmark/asr_candidate_sweep/20260531_samples_turbo_only_v2 \
  --jobs 2 \
  --min-audio-count 4
```

### Result Summary

Sample-window outputs are summarized in `output/benchmark/asr_candidate_sweep/20260531_samples_turbo_only_v2/`.

Per-candidate averages from the 4-window sweep:

| Candidate | Metric pass | Avg corrected-char ratio | Avg runtime s | Avg peak RSS MB | Practical read |
|---|---:|---:|---:|---:|---|
| `mlx-whisper-local-large-v3-turbo` | 4/4 | 1.0000 | 3.57 | 1805.26 | Keeps baseline behavior, including problematic local patterns |
| `mlx-whisper-local-large-v3-turbo-no-prev` | 4/4 | 0.8817 | 3.22 | 1810.68 | Best tradeoff: lower repetition risk, smaller top-token spikes, faster than conservative |
| `mlx-whisper-local-large-v3-turbo-conservative` | 4/4 | 0.8670 | 4.54 | 1963.61 | Similar quality direction to `no-prev`, but slower and slightly more text loss |

Window-level trends:

| Window | `turbo` | `no-prev` | `conservative` |
|---|---|---|---|
| `0417_early_empty_window` | ratio `1.000`, repeat `2`, top-token `0.1406` | ratio `0.823`, repeat `1`, top-token `0.0635` | ratio `0.820`, repeat `1`, top-token `0.0339` |
| `0517_repeat_window` | ratio `1.000`, repeat `1`, top-token `0.0250` | ratio `0.915`, repeat `1`, top-token `0.0120` | ratio `0.873`, repeat `1`, top-token `0.0120` |
| `0521_runaway_window` | ratio `1.000`, repeat `1`, top-token `0.0312` | ratio `0.946`, repeat `1`, top-token `0.0159` | ratio `0.946`, repeat `1`, top-token `0.0156` |
| `0527_empty_window` | ratio `1.000`, repeat `5`, top-token `0.1889` | ratio `0.842`, repeat `1`, top-token `0.0781` | ratio `0.829`, repeat `1`, top-token `0.0758` |

### Interpretation

- `mlx-whisper-local-large-v3-turbo` behaves like a faithful replay of the baseline and does not address the high-risk windows aggressively enough.
- `mlx-whisper-local-large-v3-turbo-no-prev` and `mlx-whisper-local-large-v3-turbo-conservative` both reduce local repetition and high-frequency-token concentration.
- `mlx-whisper-local-large-v3-turbo-no-prev` keeps slightly more text than `conservative`, while also finishing faster and using less memory.

Working conclusion from sample windows:

- Promote `mlx-whisper-local-large-v3-turbo-no-prev` to full-episode validation first.
- Keep `mlx-whisper-local-large-v3-turbo-conservative` as a fallback profile for more aggressive anti-hallucination experiments.
- Do not spend more iteration budget on `large-v3` or `large-v3-4bit` before `turbo-no-prev` is exhausted; both were much slower and already showed short-output or instability regressions on real audio.

## Partial Full-Episode Validation

Full-episode validation was started with:

```bash
src/scripts/asr_candidate_sweep.py \
  process/<MMDD>/<episode>/<audio>.m4a ... \
  --preset mlx-whisper-local-large-v3-turbo-no-prev \
  --preset mlx-whisper-local-large-v3-turbo-conservative \
  --output-dir output/benchmark/asr_candidate_sweep/20260531_full_parallel_focus \
  --jobs 6 \
  --min-audio-count 6
```

The run was intentionally stopped after the first useful partial results so the conclusions could be documented before more compute time was spent.

Recorded full-episode `turbo-no-prev` observations:

| Episode | Guardrail | Key movement |
|---|---|---|
| `0517 着急-是一种很强的负能量` | fail | `corrected_char_ratio=0.9417`; `correction_count` dropped from `520` to `36`; `top_token_ratio` dropped from `0.0160` to `0.0094`; but `review_issue_count` regressed `0 -> 1` and `review_segment_issue_count` regressed `0 -> 2` |
| `0527 咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生` | pass | `empty_corrected_segment_count` improved `28 -> 0`; `correction_count` dropped `3604 -> 7`; `max_repeated_token_run` improved `4 -> 2`; `top_token_ratio` improved `0.0804 -> 0.0348`; `corrected_char_ratio=1.1410` |
| `0521 对话-日行迹-创始人孙天祥-当AI自动写出顶会论文-人类科研的尽头在哪` | fail | `corrected_char_ratio=0.7509`; `correction_count` dropped `442 -> 61`; `max_repeated_token_run` improved `31 -> 2`; `top_token_ratio` improved `0.0252 -> 0.0115`; but `review_issue_count` regressed `4 -> 6` and `review_segment_issue_count` regressed `6 -> 13` |

### Interpretation

- `turbo-no-prev` clearly suppresses pathological repetition and heavy correction load on some long episodes.
- The tradeoff is not free. On at least two long episodes it introduced new review / segment-review regressions even while improving repetition metrics.
- This makes `turbo-no-prev` a strong candidate for targeted use, but not yet a safe global default.

## Memory and Concurrency Estimate

### Observed Memory

Sample-window sweep:

- `turbo`: about `1805 MB` peak RSS per worker
- `turbo-no-prev`: about `1811 MB` peak RSS per worker
- `turbo-conservative`: about `1964 MB` peak RSS per worker

Full-episode sweep observations:

- `turbo-no-prev`: about `2.16 GB` to `2.87 GB` RSS per worker, depending on episode
- `turbo-conservative`: about `2.72 GB` to `2.85 GB` RSS per worker in the observed partial runs

### Practical Concurrency Notes

Machine under test:

- Apple Silicon (`Apple M5 Max`)
- `128 GB` RAM

Observed scheduler behavior:

- `jobs=2` is very safe and easy to reason about.
- `jobs=6` with full-episode `turbo-no-prev` used roughly 6 candidate workers in parallel and still left `memory_pressure -Q` with system-wide free percentage around `79%-82%` during the measured interval.
- Swap usage during the monitored `jobs=6` run stayed roughly around `5.20 GB` used out of `6.14 GB`, which indicates the workload was not driving a fresh swap explosion during the short validation window, but also means the machine already carried swap pressure from prior runs.

Conservative planning budget for later iterations:

- `turbo-no-prev` only:
  - start at `jobs=6`
  - consider `jobs=8` only after checking `memory_pressure -Q` and confirming swap usage is not climbing materially
- mixed `turbo-no-prev` + `turbo-conservative`:
  - start at `jobs=4`
  - move to `jobs=6` only after checking real worker RSS on the current episodes
- archive-model exploratory runs (`large-v3`, `large-v3-4bit`):
  - keep at `jobs=2` unless there is a strong reason to spend more memory and time on them

Important nuance:

- On this host, the first bottleneck for the tested turbo candidates looked more like throughput and long-run validation time than raw RAM exhaustion.
- Future parallelism tuning should therefore track both memory and time-to-first-result, not memory alone.

## Next Attempts

1. Finish a controlled full-episode sweep for `mlx-whisper-local-large-v3-turbo-no-prev` across the current six-episode focus set and summarize every `comparison.json` into one matrix.
2. Run `mlx-whisper-local-large-v3-turbo-conservative` only on the episodes where `no-prev` still causes review regressions, rather than on the whole library.
3. Inspect the concrete `review.json` regressions on `0517` and `0521` to see whether they are glossary/term issues, timeline segmentation issues, or long-context coherence issues.
4. If the regressions are narrow, add a new preset between `no-prev` and `conservative` rather than pushing the whole library to the stricter thresholds.
5. Keep using sample-window sweeps first for any new decode preset, then promote only the winners to full-episode validation.
