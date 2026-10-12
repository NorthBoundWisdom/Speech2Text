# Process Three-Audio Experiment

Scope: all audio files under `process/*/*/`.

Reference reviewed: local WhisperLiveKit README/API/integration docs, `whisperlivekit/core.py`, `metrics.py`, `metrics_collector.py`, and benchmark runner.

Generalization guardrail: metrics below compare behavior categories (review issues, correction kinds, repetition risk, cache reuse, speed, timestamp compatibility) rather than tuning for a single transcript.

| Episode | Duration min | Runtime s | Speed factor | Peak RSS MB | Chunk status | Review issues | Segment issues | Corrections | Max repeated token run | Top token ratio | SRT/VTT timing | Run JSON |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---|---|
| 0517/着急-是一种很强的负能量 | 64.31 | 0.20 | 19507.79 | 42.84 | skipped_existing:4, transcribed:0, transcribed_after_cache_mismatch:0 | 0 | 0 | glossary:1, title_context:1 | 2 | 0.0154 | yes | process/0517/着急-是一种很强的负能量/output/details/run.json |
| 0527/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生 | 67.63 | 0.12 | 33423.36 | 39.73 | skipped_existing:4, transcribed:0, transcribed_after_cache_mismatch:0 | 0 | 0 | asr_runaway_repetition:107, glossary:1 | 15 | 0.0967 | yes | process/0527/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/output/details/run.json |
| 0527/对话日行迹创始人孙天祥 | 95.42 | 0.23 | 24386.69 | 42.50 | skipped_existing:5, transcribed:0, transcribed_after_cache_mismatch:0 | 0 | 0 | glossary:67 | 2 | 0.0247 | yes | process/0527/对话日行迹创始人孙天祥/output/details/run.json |

## Notes

- `speed_factor` is Audio2Text's inverse of WhisperLiveKit-style RTF: audio duration divided by wall time.
- `correction_kind_counts` separates glossary, ASR artifact, contextual title, and runaway repetition corrections.
- `Chunk status` is valid only when both the ASR fingerprint and chunk layout manifest match the current run.
- `run.json` records separate transcription and post-processing fingerprints, so correction-only glossary changes can refresh outputs while reusing ASR chunks.
- `SRT/VTT timing` reports whether corrected segments have explicit, monotonic, non-overlapping timestamps.
- `src/scripts/validate_run_json.py` currently validates all three run files plus `src/tests/fixtures/run.sample.json`.
- A candidate backend should improve or preserve review, correction, repetition, diversity, timing, runtime, and memory metrics across all three audios before promotion.
