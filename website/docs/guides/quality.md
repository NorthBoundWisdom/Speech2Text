# QA and repair

ASR can miss sentences, repeat words, or misidentify terminology and timestamps. SonaFolio keeps QA,
correction records, and review evidence so you can decide where to revisit the audio.

```bash
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
```

Inspect `qa.json`, `review.json`, `entity_consistency.json`, and the repair plan. Apply local replacement
only when needed:

```bash
atot exec repair path/to/work-dir
```

Repair requires the matching local backend and model; it is not text-only polishing. Automatic
corrections are recorded in `corrections.json`. Uncertain terminology remains review-only rather than
becoming global replacements automatically.

Passing QA means the program's checks passed, not that every word is accurate. Verify important
citations and judgments against the original audio. Candidate ASR backends require the same gate and
semantic review before promotion; historical experiments describe dated evidence, not current support.

[Quality rules and research](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/QUALITY_LOOP.md)
