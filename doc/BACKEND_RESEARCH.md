# ASR backend research

This document records SonaFolio's backend architecture and dated candidate conclusions. It is not an
installation guide. Historical measurements describe their recorded environment, not current speed
or accuracy guarantees. See [experiment records](experiments/README.md).

## Backend abstraction and tools

The original stable backend was MLX Whisper. `src/atot/backends/` defines the normalized adapter
contract and test backends, enabling comparison with Qwen ASR, WhisperLiveKit, and other candidates.
Windows production support uses faster-whisper; its CUDA acceptance is a separate platform concern.

```bash
python src/scripts/asr_candidate_readiness.py --preset <name>
python src/scripts/compare_asr_candidate.py path/to/audio.wav --preset <name>
python src/scripts/asr_candidate_gate.py --preset <name> --strict
python src/scripts/asr_candidate_matrix.py
python src/scripts/validate_backend_promotion.py --help
```

The comparison tooling measures command success, output quality, character ratio, correction/review
counts, repetition, timestamp compatibility, runtime, memory, empty segments, and frequent-token ratios.
Recorded runs include audio/wall time, speed factor, peak RSS, chunk/cache behavior, errors, and
quality indicators. Logs stay separate from stdout results.

Candidate guards require successful execution, meaningful nonempty text, roughly 70%-150% of baseline
character length, no quality regression, monotonic nonoverlapping subtitle-compatible timestamps,
and reasonable frequent-token ratios. Failures include `char_ratio_low`,
`correction_count_regression`, `repetition_regression`, and `timestamp_incompatible`.

## Dated candidate results

### MLX Whisper variants

- `large-v3-turbo`: production default, `mlx-community/whisper-large-v3-turbo`. The initial baseline
  recorded approximately 10-11x real time and 2.2 GB memory with three baseline audios passing.
  Later candidate runs have their own detailed regression results; do not conflate those gates.
- `large-v3-4bit`: experimental, `mlx-community/whisper-large-v3-mlx-4bit`; substantially slower than
  turbo in the recorded gate, 1/3 passing, with `char_ratio_low` and `top_token_ratio_regression`.
- Full `large-v3`: not recommended as default, `mlx-community/whisper-large-v3-mlx`; approximately
  219 seconds per audio and 4.0 GB in the summarized experiment, 0/3 passing, severe repetition.
  Exact per-input numbers remain in the original gate tables.

### Decode presets

- `no-prev` disables `condition_on_previous_text`. It reduced repeated phrases and empty windows,
  but some inputs regressed in review indicators. Eleven long-audio checks and semantic review
  produced eight guard passes and three review regressions. It remains optional, not the default.
- `conservative` uses more cautious generation, with slower execution and slightly less retained
  text; it remains an alternative preset.
- Other anti-repeat/repair presets were not promoted. Evidence did not show a clear advantage over
  `no-prev`, and they are not currently being advanced.

See [the 2026-05-31 sweep](experiments/asr_candidate_sweep_2026-05-31.md) for exact settings and results.

### Qwen3 ASR

The isolated environment is `$ATOT_DATA_ROOT/cache/tools/mlx-qwen3-asr-venv`.
Models are `Qwen/Qwen3-ASR-0.6B` and `Qwen/Qwen3-ForcedAligner-0.6B`.
The command offers context, forced alignment, and JSON output.

The three-window gate passed 0/3: all lacked compatible timestamps, and one had repetition
regression. Qwen remains experimental. Forced-alignment timeline normalization must be fixed before
reevaluation.

### WhisperLiveKit

The isolated environment is `$ATOT_DATA_ROOT/cache/tools/whisperlivekit-venv`.
Upstream offers multiple backends, streaming, and structured metrics. All three full-audio runs failed
at startup because the requested MLX backend was unavailable or incompatible with the supplied local
model. It remains a diagnostic candidate and is not exposed as a production backend. Regate only
when a compatible upstream combination is available.

See [readiness](experiments/asr_candidate_readiness_2026-05-28.md) and
[the Qwen/WhisperLiveKit decision](experiments/asr_candidate_gate_qwen_whisperlivekit_2026-06-24.md).

## Promotion requirements

A default backend requires at least one gold sample, at least three complete podcasts, varied topics
and speakers, no QA/review/correction/repetition regression, stable character density, acceptable
runtime/memory, and semantic review. Context/vocabulary support, segment timestamps, and low
hallucination risk are additional desirable properties. A command that merely exits successfully
has not passed this gate.

Candidates use isolated environments under the data-root cache. The production environment contains
only production dependencies. Presets select candidate commands; dependencies enter the production
environment only after promotion. Older `.tools/` environments in dated reports describe historical
setup and are not current model storage locations.

## Adopted patterns and scope

Adopted patterns include explicit adapters, structured `run.json` metrics, normalized segments,
separate logs, fixed inputs, and reproducible comparisons. SonaFolio focuses on batch transcription;
real-time streaming, WebSocket servers, and LocalAgreement streaming policies were not adopted.
The product has native/Qt clients; that does not make upstream streaming candidates stable backends.

## References

- Backend interface: `src/atot/backends/base.py`.
- Candidate presets: `src/scripts/asr_candidate_presets.py`.
- Comparison: `src/scripts/compare_asr_candidate.py`.
- Gates: `src/scripts/asr_candidate_gate.py`.
- Promotion validation: `src/scripts/validate_backend_promotion.py`.
- [Three-audio baseline](experiments/process_three_audio.md).
- [Candidate matrix](experiments/asr_candidate_gate_matrix.md).

Historical candidate conclusions were updated on 2026-07-10 (document version 2.1). English prose was
maintained later without rerunning or rewriting those measurements.

## Preserved example measurements and preset values

The original illustrative `run.json` recorded total time 523.5 seconds, audio time 5725.3 seconds,
speed factor 10.9, five transcribed chunks, zero cached chunks, and peak memory 2048 MB.
The conservative preset used `temperature=(0.0, 0.2, 0.4)`,
`compression_ratio_threshold=1.8`, and `logprob_threshold=-1.2`. The unpromoted anti-repeat preset
used `repetition_penalty=1.1`. These are historical observations/settings, not new measurements.
