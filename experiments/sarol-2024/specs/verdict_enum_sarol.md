# Sarol 2024 verdict enum — the output contract

**This file is a frozen contract (`contract_file=True`). It is NOT optimizer-editable.**

It holds the two things the benchmark defines and the Scorer consumes: the set of emittable
labels, and the 9→3 collapse used for the published metric. Everything about *how to choose*
between these labels — class definitions, boundaries, worked examples, tie-breaks, the
worst-wins rollup order, multi-citation handling — lives in the rubric beside it
(`verdict_schema_sarol.md`) and **is** optimizer-editable.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical
Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

## Verdict enum (9 classes)

The adjudicator picks exactly one of these per sub-claim, and one for `overall_verdict`.
This list is closed: a label outside it is an ordinary invalid output — charged as a miss
against its gold class and counted in `error_class_counts`, never a crash and never
silently re-bucketed.

```
ACCURATE
OVERSIMPLIFY
NOT_SUBSTANTIATE
CONTRADICT
MISQUOTE
INDIRECT
INDIRECT_NOT_REVIEW
ETIQUETTE
IRRELEVANT
```

## 3-way collapse (for Sarol's published metric)

- **ACCURATE** → ACCURATE
- **OVERSIMPLIFY / NOT_SUBSTANTIATE / CONTRADICT / MISQUOTE / INDIRECT** → NOT_ACCURATE
- **ETIQUETTE / INDIRECT_NOT_REVIEW / IRRELEVANT** → IRRELEVANT

This collapse exists for comparability with the published 3-way baselines. **It is not the
objective**, which is accuracy over the nine labels above — so a verdict that lands in the right
3-way bucket but the wrong 9-way label is simply wrong. Scoring is defined in
`experiments/sarol-2024/scripts/score_sarol3.py` and nowhere else.

## Workflow states are not verdicts

`PENDING` / `NEEDS_PDF` / `STALE` / `SCHEMA_VIOLATION` are pipeline machinery, orthogonal to
this enum, and are not emittable as a verdict. The same is true of `AMBIGUOUS`, which is a
workflow flag elsewhere in the tool and is **not** part of this vocabulary: emitting it in a
verdict field is an out-of-enum label like any other, and is rejected.
