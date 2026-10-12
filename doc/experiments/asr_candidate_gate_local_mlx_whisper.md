# Local MLX Whisper Candidate Gate

Source: configured local model directory for `whisper-large-v3-turbo`.

Command:

```bash
.venv/bin/python src/scripts/asr_candidate_gate.py \
  --preset mlx-whisper-local-large-v3-turbo \
  --candidate-timeout 1800 \
  --strict
```

Result: candidate commands succeeded on all three audios. After applying the same monotonic timeline repair used by the main pipeline, all candidate rows are SRT/VTT-compatible and the coffee episode passes the metric guardrail. The candidate still should not be promoted because two rows fail the metric guardrail with structured, cross-audio reasons: `correction_count_regression` plus `repetition_regression` on one row, and `review_issue_regression` on another.

- Candidate: `mlx-whisper-local-large-v3-turbo`
- Audio count: 3

| Audio | Status | Return code | Runtime s | Candidate RSS MB | Corrected chars | Baseline ratio | Empty segments | Candidate issues | Baseline issues | Candidate corrections | Baseline corrections | Candidate repeat | Baseline repeat | Candidate top token | Candidate SRT/VTT | Metric guardrail | Guardrail failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| [着急-是一种很强的负能量.mp3](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3-turbo/comparison.md) | ok | 0 | 51.94 | 2048.00 | 20834 | 0.93 | 0 | 0 | 0 | 24 | 2 | 7 | 2 | 0.01 | yes | fail | `correction_count_regression`, `repetition_regression` |
| [咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3-turbo/comparison.md) | ok | 0 | 56.12 | 2096.66 | 23522 | 0.98 | 0 | 0 | 0 | 0 | 108 | 10 | 15 | 0.08 | yes | pass | none |
| [001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3-turbo/comparison.md) | ok | 0 | 76.10 | 2217.56 | 33760 | 1.01 | 0 | 1 | 0 | 58 | 67 | 2 | 2 | 0.02 | yes | fail | `review_issue_regression` |

Promotion guardrail: all gate rows should succeed and pass the metric guardrail before a candidate is promoted. Metric pass is necessary but not sufficient; semantic transcript quality still requires review.
