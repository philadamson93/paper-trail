# Sarol 2024 verdict enum — the output contract

**This file is a frozen contract (`contract_file=True`). It is NOT optimizer-editable.**

It holds the two things the benchmark defines and the Scorer consumes: the set of emittable
labels, and the 9→3 collapse used for the published metric. Everything about *how to choose*
between these labels — class definitions, boundaries, worked examples, tie-breaks, the
worst-wins rollup order, multi-citation handling — lives in the rubric beside it
(`verdict_schema_sarol.md`) and **is** optimizer-editable.

Split out of `verdict_schema_sarol.md` on 2026-09-01 by Open Questions §8 of
`docs/plans/papertrail-optimizer-requirements.md` ("a contract file should be immutable"),
so that the immutable half and the editable half are separate files rather than separate
paragraphs of one file.

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

The adapter computes both 9-way and 3-way scores from the same predictions. The frontier
scalar is 3-way **macro**-F1; micro-F1 is reported only (a do-nothing always-ACCURATE
program scores micro 0.781 against this gold distribution and macro 0.292).

## Binding to code

`experiments/sarol-2024/scripts/parse_verdict.py` is the executable copy of this contract and
must stay byte-equivalent to it in content:

| This file | `parse_verdict.py` |
|---|---|
| the 9 labels above | `SAROL_9` |
| → NOT_ACCURATE row | `NOT_ACCURATE_3WAY` |
| → IRRELEVANT row | `IRRELEVANT_3WAY` |
| the collapse itself | `to_3way()` |

`score_sarol3.py` imports those names rather than redefining them, so the collapse is
single-sourced in code. If this file and `parse_verdict.py` ever disagree, `parse_verdict.py`
is what actually scored the run — reconcile before trusting the number.

## Workflow states are not verdicts

`PENDING` / `NEEDS_PDF` / `STALE` / `SCHEMA_VIOLATION` are pipeline machinery, orthogonal to
this enum, and are not emittable as a verdict. The same is true of `AMBIGUOUS`, which the
shipped tool keeps as a workflow flag driving Phase 4 "Ambiguity triage" (Open Questions §7):
it is **not** part of this vocabulary, and the exit validator must reject it appearing in a
verdict field exactly like any other out-of-enum label.
