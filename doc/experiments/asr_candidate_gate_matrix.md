# ASR Candidate Gate Matrix

- Runs dir: `output/benchmark/asr_candidate_gate/runs`
- Minimum audio count: 3

| Candidate | Audio count | Command success | Metric pass | Promotable | Avg runtime s | Max runtime s | Avg RSS MB | Max RSS MB | Guardrail failures |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| `mlx-whisper-local-large-v3-turbo` | 3 | 3/3 | 1/3 | no | 61.39 | 76.10 | 2120.74 | 2217.56 | `correction_count_regression`:1, `repetition_regression`:1, `review_issue_regression`:1 |
| `mlx-whisper-local-large-v3-4bit` | 3 | 3/3 | 1/3 | no | 186.08 | 296.32 | 1539.38 | 1642.86 | `char_ratio_low`:1, `repetition_regression`:1, `review_issue_regression`:1, `review_segment_issue_regression`:1, `top_token_ratio_regression`:1 |
| `mlx-whisper-local-large-v3` | 3 | 3/3 | 0/3 | no | 219.51 | 372.03 | 3784.47 | 3969.77 | `char_ratio_low`:1, `repetition_regression`:2, `review_issue_regression`:1, `top_token_ratio_regression`:2 |

## Per-Audio Rows

| Candidate | Audio | Metric guardrail | Runtime s | RSS MB | Char ratio | Failures | Comparison |
|---|---|---|---:|---:|---:|---|---|
| `mlx-whisper-local-large-v3` | 001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a | fail | 372.03 | 3969.77 | 0.77 | `review_issue_regression`, `repetition_regression`, `top_token_ratio_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3/comparison.json) |
| `mlx-whisper-local-large-v3` | 咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a | fail | 237.31 | 3715.17 | 0.82 | `repetition_regression`, `top_token_ratio_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3/comparison.json) |
| `mlx-whisper-local-large-v3` | 着急-是一种很强的负能量.mp3 | fail | 49.19 | 3668.48 | 0.13 | `char_ratio_low` | [comparison](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3/comparison.json) |
| `mlx-whisper-local-large-v3-4bit` | 001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a | fail | 296.32 | 1642.86 | 0.98 | `review_issue_regression`, `review_segment_issue_regression`, `repetition_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3-4bit/comparison.json) |
| `mlx-whisper-local-large-v3-4bit` | 咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a | pass | 216.49 | 1513.80 | 1.02 | none | [comparison](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3-4bit/comparison.json) |
| `mlx-whisper-local-large-v3-4bit` | 着急-是一种很强的负能量.mp3 | fail | 45.41 | 1461.48 | 0.12 | `char_ratio_low`, `top_token_ratio_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3-4bit/comparison.json) |
| `mlx-whisper-local-large-v3-turbo` | 001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a | fail | 76.10 | 2217.56 | 1.01 | `review_issue_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文/mlx-whisper-local-large-v3-turbo/comparison.json) |
| `mlx-whisper-local-large-v3-turbo` | 咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a | pass | 56.12 | 2096.66 | 0.98 | none | [comparison](output/benchmark/asr_candidate_gate/runs/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/mlx-whisper-local-large-v3-turbo/comparison.json) |
| `mlx-whisper-local-large-v3-turbo` | 着急-是一种很强的负能量.mp3 | fail | 51.94 | 2048.00 | 0.93 | `correction_count_regression`, `repetition_regression` | [comparison](output/benchmark/asr_candidate_gate/runs/着急-是一种很强的负能量/mlx-whisper-local-large-v3-turbo/comparison.json) |

Promotion rule: a candidate must pass every current process-audio row and still requires semantic transcript review before replacing the baseline.
