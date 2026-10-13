# QA, review, and repair

ASR can omit, repeat, misidentify terms, or mistime speech. QA, corrections, and review evidence guide checking. Even the validated Chinese workflow is not word-perfect for every recording.

## Read evidence first

Use the returned work directory:

```bash
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
```

| Evidence | Inspect |
| --- | --- |
| qa.json | Status, findings, windows |
| corrections.json | Deterministic changes |
| review.json | Uncertain terms/candidates |
| entity_consistency.json | Entity inconsistency |
| Repair plan | Windows worth another pass |

Failure suggests review, not that every line is unusable. Passing is not proof of accuracy. Prioritize numbers, names, judgments, quotations, and unusual gaps/repetition.

## Plan, then execute

Plan-only selects windows without recognition. Inspect ranges/reasons/audio, then explicitly run:

```bash
atot exec repair path/to/work-dir --json
```

Repair needs matching local backend/weights; it is audio re-recognition, not text polish. Back up needed work versions and review the new output/QA.

## Terminology and rules

Custom glossary/prompt and shared packs supply real context. Deterministic changes are audited; uncertain terms should remain review items, not global substitutions derived from one error.

A good title/summary does not certify ASR or fix source errors. Candidates need gates and semantic review. Historical research does not establish current, cross-platform, or multilingual validation.

[Transcription →](transcription.md) · [Troubleshooting →](troubleshooting.md)
