# Audio2Text Quality Loop

The local transcript is the auditable source layer. It may be imperfect, but every automatic change
should be visible, reversible, and scoped.

## Default Flow

1. Run `atot exec transcribe` or `atot exec import`.
2. Inspect `qa.json`, `review.json`, and `entity_consistency.json` in the output job directory.
3. Use `atot status --task-id <task-id>` for task/session state.
4. Run `atot exec qa <output>` for output health.
5. Run `atot exec repair <output> --plan-only` to inspect candidate windows.
6. Run `atot exec repair <output>` only when you want explicit local replacement.

Repair is optional. QA failures should surface warnings and suggested windows, but normal transcript
viewing, deterministic postprocess, cloud preparation, and manual review remain available.

## Deterministic Outputs

- `transcript.corrected.txt` is the faithful corrected transcript.
- `transcript.readable.md` is deterministic formatting for reading.
- `corrections.json` records deterministic corrections.
- `review.json` and `entity_consistency.json` keep uncertain entity or glossary
  issues review-only unless confirmed by a glossary.

## Rule And Glossary Scope

Reusable rule packs stay under `src/atot/data/rule_packs/` and are selected with `--rule-pack`.
Cloud glossary review writes a queue under `cloud/glossary_review_queue.*`; items should be
confirmed for episode or podcast scope before becoming reusable rules.

## Candidate Promotion

Changing the default model/backend requires the candidate gate plus semantic review. The promotion
validator requires gold evidence, multiple full-length audios, several content types, no QA/review
regressions, stable character density, acceptable runtime/memory, and low hallucination risk.
