# Qwen And WhisperLiveKit Candidate Gates 2026-06-24

## Scope

This record closes the initial quality-gate evaluation for `mlx-qwen3-asr-0.6b` and
`whisperlivekit-mlx`. Generated candidate outputs remain under the ignored data root; this document
keeps only public-safe aggregate results and product decisions.

## Qwen ASR

The Qwen preset ran successfully on three distinct 120-second Chinese podcast windows.

| Result | Count |
|---|---:|
| Candidate commands completed | 3/3 |
| Metric guardrail passed | 0/3 |
| Timestamp compatible | 0/3 |
| Repetition regression | 1/3 |

Corrected-character ratios ranged from `1.0646` to `1.1855`, and runtime ranged from `5.71` to
`8.88` seconds per two-minute window. All rows lacked usable segment timing, so none could produce
compatible SRT/VTT output.

A manual spot check found that all three transcripts remained coherent at the paragraph level, but
they also contained local repetition and English/proper-name recognition errors. These semantic
issues do not overturn the structural rejection; the review decision is `hold`.

Decision: do not promote `mlx-qwen3-asr-0.6b`. Keep the preset experimental until its forced
alignment output is normalized into the shared timestamp contract and a new gate is explicitly
proposed.

## WhisperLiveKit

The WhisperLiveKit preset was run against three complete Chinese podcast episodes. All three
commands exited before transcription because the requested MLX Whisper backend reported that it was
unavailable or incompatible with the supplied local model.

| Result | Count |
|---|---:|
| Candidate commands completed | 0/3 |
| Metric guardrail passed | 0/3 |
| Empty candidate output | 3/3 |
| Timestamp incompatible | 3/3 |

Readiness checks confirm that the executable, doctor command, and local model files exist; that is
not sufficient runtime compatibility evidence.

Decision: do not expose or promote `whisperlivekit-mlx`. Keep the preset as a diagnostic candidate
until an upstream-compatible MLX model/backend combination is available and a new gate is explicitly
proposed.

## Promotion Status

Neither candidate reached semantic promotion review because both failed mandatory structural gates.
Qwen received the non-promotion `hold` spot check above. WhisperLiveKit produced no candidate text,
so semantic transcript review was not applicable.
`validate_backend_promotion.py` intentionally accepts only `decision=promote` evidence, so it must
not be used to manufacture a passing result for these rejected candidates.
