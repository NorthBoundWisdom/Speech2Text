# Local MLX Whisper Large v3 Candidate Gate

Source: configured local model directory for `whisper-large-v3-mlx`.

Command:

```bash
.venv/bin/python src/scripts/asr_candidate_gate.py \
  --preset mlx-whisper-local-large-v3 \
  --candidate-timeout 1800 \
  --strict
```

Result: candidate commands succeeded on all three audios, but none passed the metric guardrail. This model is slower and much more memory-heavy than the local turbo candidate, with severe repeated-token and high-frequency-token regressions on two rows. It should not replace the current `large-v3-turbo` baseline.

- Candidate: `mlx-whisper-local-large-v3`
- Audio count: 3

| Audio | Status | Return code | Runtime s | Candidate RSS MB | Corrected chars | Baseline ratio | Empty segments | Candidate issues | Baseline issues | Candidate corrections | Baseline corrections | Candidate repeat | Baseline repeat | Candidate top token | Candidate SRT/VTT | Metric guardrail | Guardrail failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| [着急-是一种很强的负能量.mp3](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3/comparison.md) | ok | 0 | 49.19 | 3668.48 | 2898 | 0.13 | 0 | 0 | 0 | 0 | 2 | 1 | 2 | 0.25 | yes | fail | `char_ratio_low` |
| [咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3/comparison.md) | ok | 0 | 237.31 | 3715.17 | 19661 | 0.82 | 0 | 0 | 0 | 0 | 108 | 996 | 15 | 0.49 | yes | fail | `repetition_regression`, `top_token_ratio_regression` |
| [001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3/comparison.md) | ok | 0 | 372.03 | 3969.77 | 25937 | 0.77 | 0 | 1 | 0 | 29 | 67 | 1512 | 2 | 0.58 | yes | fail | `review_issue_regression`, `repetition_regression`, `top_token_ratio_regression` |

Promotion guardrail: all gate rows should succeed and pass the metric guardrail before a candidate is promoted. Metric pass is necessary but not sufficient; semantic transcript quality still requires review.
