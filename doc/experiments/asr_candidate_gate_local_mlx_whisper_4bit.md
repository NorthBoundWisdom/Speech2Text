# Local MLX Whisper 4bit Candidate Gate

Source: configured local model directory for `whisper-large-v3-mlx-4bit`.

Command:

```bash
.venv/bin/python src/scripts/asr_candidate_gate.py \
  --preset mlx-whisper-local-large-v3-4bit \
  --candidate-timeout 1800 \
  --strict
```

Result: candidate commands succeeded on all three audios. The model used less peak memory than the local turbo candidate, but it should not be promoted: two rows fail the metric guardrail, with one severe short-output/high-frequency-token failure and one repeated-token/review regression. This keeps the current `large-v3-turbo` baseline as the safer default.

- Candidate: `mlx-whisper-local-large-v3-4bit`
- Audio count: 3

| Audio | Status | Return code | Runtime s | Candidate RSS MB | Corrected chars | Baseline ratio | Empty segments | Candidate issues | Baseline issues | Candidate corrections | Baseline corrections | Candidate repeat | Baseline repeat | Candidate top token | Candidate SRT/VTT | Metric guardrail | Guardrail failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| [着急-是一种很强的负能量.mp3](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3-4bit/comparison.md) | ok | 0 | 45.41 | 1461.48 | 2677 | 0.12 | 0 | 0 | 0 | 0 | 2 | 1 | 2 | 0.32 | yes | fail | `char_ratio_low`, `top_token_ratio_regression` |
| [咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3-4bit/comparison.md) | ok | 0 | 216.49 | 1513.80 | 24622 | 1.02 | 0 | 0 | 0 | 0 | 108 | 2 | 15 | 0.10 | yes | pass | none |
| [001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3-4bit/comparison.md) | ok | 0 | 296.32 | 1642.86 | 32697 | 0.98 | 0 | 2 | 0 | 43 | 67 | 263 | 2 | 0.09 | yes | fail | `review_issue_regression`, `review_segment_issue_regression`, `repetition_regression` |

Promotion guardrail: all gate rows should succeed and pass the metric guardrail before a candidate is promoted. Metric pass is necessary but not sufficient; semantic transcript quality still requires review.
