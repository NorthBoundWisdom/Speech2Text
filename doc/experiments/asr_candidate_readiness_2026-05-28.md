# ASR Candidate Readiness Snapshot

Checked at: `2026-05-28 04:48:21 +0800`.

Scope: candidate presets that still depend on Hugging Face model weights before they can enter the three-audio gate.

Commands:

```bash
.venv/bin/python src/scripts/asr_candidate_readiness.py \
  --preset mlx-qwen3-asr-0.6b \
  --probe-missing \
  --probe-bytes 65536 \
  --probe-timeout 10 \
  --min-mb-s 0.5

.venv/bin/python src/scripts/asr_candidate_readiness.py \
  --preset whisperlivekit-mlx \
  --probe-missing \
  --probe-bytes 65536 \
  --probe-timeout 10 \
  --min-mb-s 0.5
```

Result:

| Preset | Executable | Doctor/check | Missing cache files | Probe result | Gate-ready |
|---|---|---|---|---|---|
| `mlx-qwen3-asr-0.6b` | ok | ok | `Qwen/Qwen3-ASR-0.6B/model.safetensors`; `Qwen/Qwen3-ForcedAligner-0.6B/model.safetensors` | too slow: `0.06 MB/s` and `0.05 MB/s`, below `0.50 MB/s` | no |
| `whisperlivekit-mlx` | ok | ok | `mlx-community/whisper-large-v3-turbo/weights.safetensors` | too slow: `0.05 MB/s`, below `0.50 MB/s` | no |

Decision: do not start multi-GB downloads or three-audio gates for these presets until the required weights are already warm in the local cache or the range probe exceeds the configured threshold. Continue using local archive presets as network-free comparators.
