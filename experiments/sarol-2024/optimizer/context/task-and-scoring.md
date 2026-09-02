# The task, and what counts as better

## The task

Given a citing sentence from a manuscript and one paper it cites, decide how honestly the sentence
represents that paper. The program is a three-stage pipeline: an **extractor** pulls evidence
passages from the cited paper, an **adjudicator** assigns a verdict from those passages, and a
**verifier** spot-checks the extractor's evidence.

The benchmark is Sarol, Schneider & Kilicoglu 2024, *Assessing Citation Integrity in Biomedical
Publications* (Bioinformatics btae420): 3,063 human-annotated citation instances with reported
inter-annotator agreement, split TRAIN 2,141 / VAL 316 / TEST 606.

## The output vocabulary

Nine labels, defined in the frozen `verdict_enum_sarol.md`. You cannot change this set.

`ACCURATE` · `OVERSIMPLIFY` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `MISQUOTE` · `INDIRECT` ·
`INDIRECT_NOT_REVIEW` · `ETIQUETTE` · `IRRELEVANT`

## The frontier scalar: 3-way macro-F1

The nine labels collapse to three for the published metric:

| Bucket | From |
|---|---|
| ACCURATE | `ACCURATE` |
| NOT_ACCURATE | `OVERSIMPLIFY`, `NOT_SUBSTANTIATE`, `CONTRADICT`, `MISQUOTE`, `INDIRECT` |
| IRRELEVANT | `ETIQUETTE`, `INDIRECT_NOT_REVIEW`, `IRRELEVANT` |

**3-way macro-F1 is the number being optimized.** It is directly comparable to the published
baselines — MultiVerS 0.52, GPT-4 4-shot 0.45 — and every class is reachable, so there is no
ceiling artifact to explain away.

### Micro-F1 is reported. It is not the objective, and it is a trap

For single-label multiclass, micro-F1 equals accuracy. The gold distribution is heavily skewed:

| Bucket | Gold count | Share |
|---|---:|---:|
| ACCURATE | 1,463 | 78.1% |
| NOT_ACCURATE | 376 | 20.1% |
| IRRELEVANT | 34 | 1.8% |

So a program that emits `ACCURATE` unconditionally and does no work at all scores **micro 0.781** —
beating both published baselines — while scoring **macro 0.292**. If you find yourself with a
rising micro and a falling macro, you are making the program worse and the wrong number is telling
you otherwise. `score_sarol3.py --selftest` pins both figures so this cannot be adopted by
accident.

### Reported alongside

- Per-class F1 for all three buckets.
- The 3×3 confusion matrix.
- 9-way per-class F1 and `macro_f1_9way`, as a descriptive breakdown only.
  **Read `support_9way` first.** Macro-9 always divides by nine, so a batch whose gold covers five
  classes caps at 5/9 = 0.556 however good the predictions — a low 9-way macro on a small batch
  usually means the batch was small. For calibration, the do-nothing always-ACCURATE program scores
  0.097 at 9-way against 0.292 at 3-way: the 9-way axis punishes it harder, which is informative,
  but it is still not the objective. There are **no published baselines** at
  9-way granularity — Sarol et al. abandoned that resolution because models could not learn it —
  so it is a diagnostic, not a score to chase.
- `error_class_counts`, including `invalid_label` (see below).

### Invalid labels

A label outside the nine is not a crash and is never silently re-bucketed. It is charged as a miss
against whatever the gold class was, and counted under `invalid_label` and
`invalid_label:<THE_LABEL>`. An edit that invents vocabulary therefore just scores worse.

## Known failure modes

These are real, observed on a stratified N=5 smoke run in April 2026
(`docs/plans/experiment-april-20-findings.md`). They are a head start, not a complete taxonomy —
and the sample was five claims, so treat the first as established and the second as a hypothesis.

### 1. The INDIRECT-detection blind spot — established, and the highest-value target

The adjudicator calls indirectly-attributed claims `ACCURATE`. Two of five claims failed this way,
including the most clear-cut INDIRECT case available: a cited review in which *every* relevant
passage was itself an attribution to some other primary source, which the adjudicator nonetheless
called ACCURATE.

The shape: the cited paper contains the fact, but credits someone else for it. The citing author
should have cited the primary. `INDIRECT` when the cited paper is a review,
`INDIRECT_NOT_REVIEW` otherwise.

Why this one is worth attacking first:

- **The signal is lexically detectable.** Evidence snippets that support the claim end in citation
  markers — `(12)`, `(12,15)`, `(Ota et al., 2009)`. If every supporting quote carries one, the
  fact is being attributed onward.
- **The rubric already distinguishes the classes**, so no vocabulary change is needed.
- **There is an unused slot for it.** The extractor's `attestation.indirect_attribution_check`
  exists and is currently free-form prose the adjudicator can ignore without consequence.
- **The blast radius is larger than the headline rate.** Sarol reports INDIRECT at 1.2% of
  single-citation claims and 2.8% of multi-citation ones, but `OVERSIMPLIFY` and
  `NOT_SUBSTANTIATE` instances frequently carry an indirect-attribution component too.

Note the collapse: `INDIRECT` → NOT_ACCURATE but `INDIRECT_NOT_REVIEW` → IRRELEVANT. Getting the
review/not-review distinction wrong moves the answer across two different 3-way buckets, so it
costs you on the frontier scalar, not just on the 9-way breakdown.

### 2. Severity under-commitment — tentative, and mostly invisible to the frontier

Two of five claims landed one step down a severity ladder from gold: gold `NOT_SUBSTANTIATE`
predicted `OVERSIMPLIFY`, and gold `CONTRADICT` predicted `NOT_SUBSTANTIATE`. The second is the
informative one — the extractor had already recorded the verbatim opposing passage that
`CONTRADICT` requires, and the adjudicator still dropped a level.

Two honest caveats, both of which should temper how much effort you spend here:

- **N=5 is within noise.** Whether the adjudicator *systematically* under-commits needs N≥50 to
  say. Do not treat it as established.
- **Both misses are 3-way hits.** `OVERSIMPLIFY`, `NOT_SUBSTANTIATE` and `CONTRADICT` all collapse
  into NOT_ACCURATE, so this pattern costs **nothing** on the frontier scalar. It shows up only in
  the 9-way breakdown, which is descriptive.

So: worth recording when you see it, not worth optimizing against under the current metric. If it
ever becomes the frontier, that is a decision someone makes deliberately, not one you make by
chasing a diagnostic.

## Multi-citation claims are half the data

51% of Sarol instances are multi-citation: the sentence cites a cluster, `[1,2,3]`, and only one
member is under evaluation. Verify only the portion of the claim attributable to *this* source.
Content a sibling citation might cover does not count against the current one. If the grouping is
so ambiguous that no sub-claim can be attributed to a single source, that is what `ETIQUETTE` is
for.

This is the single largest structural feature of the dataset and the guidance for it lives in the
editable rubric, so it is fully in scope for you to improve.

## What a good iteration looks like

A named failure class, a smallest-edit test of one hypothesis about it, and a prediction of which
verdict classes should move. The release reports movement per class, which is only informative if
you said in advance which ones you were aiming at.
