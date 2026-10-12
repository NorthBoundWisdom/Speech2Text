# ASR Candidate Gate Smoke

Purpose: verify that `src/scripts/asr_candidate_gate.py` evaluates the current process source-audio set as a shared gate for future ASR candidates.

Command:

```bash
.venv/bin/python src/scripts/asr_candidate_gate.py \
  --candidate-name gate-echo-smoke \
  --candidate-command "/bin/echo {glossary_terms}"
```

Result: the gate discovered exactly the three top-level source audio files under `process/<date>/<episode>/` and ignored generated chunks, monitor outputs, samples, and compare-baseline artifacts.

| Audio | Candidate status | Runtime/RSS | Corrected chars | Empty segments | Review issues | Segment issues | Max repeated token run | Top token ratio | SRT/VTT timestamps | Metric guardrail |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `process/0517/着急-是一种很强的负能量/着急-是一种很强的负能量.mp3` | ok | recorded | 257 | 0 | 0 | 0 | 1 | recorded | no | diagnostic only |
| `process/0527/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生/咖啡时间-揭秘咖啡店里-一杯创意咖啡的诞生.m4a` | ok | recorded | 283 | 0 | 0 | 0 | 1 | recorded | no | diagnostic only |
| `process/0527/对话日行迹创始人孙天祥/001-对话日行迹创始人孙天祥-当AI自动写出顶会论文.m4a` | ok | recorded | 112 | 0 | 0 | 0 | 1 | recorded | no | diagnostic only |

This is a plumbing smoke test only. `/bin/echo {glossary_terms}` proves that every candidate can receive the same topic-derived context across the three current audios; it is not an ASR quality result. Current gate logic records runtime and candidate-process-tree peak RSS, plus a separate metric guardrail that checks command success, non-empty output, baseline/candidate length ratio, review/correction/repetition regressions, high-frequency-token spikes, and explicit non-overlapping monotonic timestamps compatible with SRT/VTT, so a real `--strict` benchmark should fail short non-transcript outputs like this.

Promotion rule: a real candidate backend must pass this same three-audio gate and improve or preserve review, correction, repetition, runtime, memory, and timestamp compatibility metrics before replacing the current `large-v3-turbo` baseline. Passing metrics is still only a necessary condition; semantic transcript review remains required.
