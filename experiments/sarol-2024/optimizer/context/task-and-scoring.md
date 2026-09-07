# The task, and what counts as better

## The task

Given a citing sentence from a manuscript and one paper it cites, decide how honestly the sentence
represents that paper. The program is a three-stage pipeline: an **extractor** pulls evidence
passages from the cited paper, an **adjudicator** assigns a verdict from those passages, and a
**verifier** spot-checks the extractor's evidence.

The benchmark is Sarol, Schneider & Kilicoglu 2024, *Assessing Citation Integrity in Biomedical
Publications* (Bioinformatics btae420): 3,063 human-annotated citation instances with reported
inter-annotator agreement, split TRAIN 2,141 / VAL 316 / TEST 606.

⚠ **Those are the headline figures, not the pool you are scored against.** A claim is drawable only
if its gold label can be resolved, so the *drawable* population is **2,076 TRAIN / 311 dev** — a few
percent smaller, almost entirely rows the text join could not match. Every per-class count in this
document is over that repaired pool. (It was much smaller until 2026-09-07, for the reason in
"The pool used to delete two classes" below; any figure you meet elsewhere quoting 1,699 / 255 is
recording that bug, not the benchmark.)

## The output vocabulary

Nine labels. The emittable set is frozen in
`experiments/sarol-2024/specs/verdict_enum_sarol.md`, which the judge loads on every claim. What each
label *means* to the benchmark's annotators is transcribed in
`experiments/sarol-2024/specs/verdict_definitions_sarol.md` — a reference for you, **not** part of
the program and never read by the judge. You cannot change either. How to *apply* the labels is the
editable clarifications layer, and it is the only thing the judge reads besides the enum — see
`experiments/sarol-2024/optimizer/context/edit-surface.md`.

`ACCURATE` · `OVERSIMPLIFY` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `MISQUOTE` · `INDIRECT` ·
`INDIRECT_NOT_REVIEW` · `ETIQUETTE` · `IRRELEVANT`

## The objective: accuracy over the nine classes

**The number being optimized is accuracy** — the fraction of claims whose predicted label equals the
gold label, over the nine emittable labels. Nothing is collapsed and nothing is renormalised.
Reported as `primary_metric`, under the name `sarol_accuracy_9class`.

**Compare it against 0.595, never against zero.** See *The one table* below: that is what a program
scores by answering `ACCURATE` every time and doing no work at all. The release computes the floor
from each batch's own gold and reports it as `do_nothing_floor`, so it is always beside the number
it calibrates.

**The cost of this choice, on the record.** Accuracy is weighted by how common each class is, so it
is dominated by `ACCURATE`. `MISQUOTE` and `INDIRECT` have six dev instances each: getting both
perfectly right is worth about four points, and getting both wrong costs about the same. Rubric work
on the rare classes is real work that the number will barely reward. That is a known property of the
objective, not a signal the rare classes do not matter.

**Which is why you read `macro_f1_renormalised` beside it, every time.** It is macro-F1 at 9-way
resolution, renormalised over the classes present, and it is kept for one job: catching the single
degenerate strategy accuracy admits. Collapsing toward `ACCURATE` raises accuracy and craters macro.
So — accuracy up *and* macro down means the gain was bought by answering `ACCURATE` more often, and
is not an improvement. Accuracy up with macro flat or rising is a real gain. `objective_class_set`
and `n_objective_classes_present` belong to this diagnostic, not to the objective; two macro numbers
with different denominators are not comparable, and accuracy has no such caveat.

*(This was macro-F1 until 2026-09-07, and before that 3-way macro. The renormalising denominator
moved with the batch's class mix, which manufactured a −0.15 TRAIN "decline" across three iterations
for a program that never changed. Accuracy has no denominator to wobble, and that is most of why it
won.)*

Drawable gold, after the pool repair described below:

| Class | TRAIN | dev |
|---|---:|---:|
| ACCURATE | 1308 | 185 |
| ETIQUETTE | 264 | 38 |
| NOT_SUBSTANTIATE | 189 | 25 |
| CONTRADICT | 58 | 22 |
| IRRELEVANT | 118 | 21 |
| OVERSIMPLIFY | 56 | 8 |
| INDIRECT | 35 | 6 |
| MISQUOTE | 23 | 6 |
| INDIRECT_NOT_REVIEW | 25 | **0** |

⚠ **That caveat applies to the macro diagnostic, not to the objective.** Renormalising means the
denominator depends on which classes the batch drew, so a `macro_f1_renormalised` over 6 classes is
not comparable to one over 8 — read `n_objective_classes_present` before comparing two of them.
Accuracy is free of this: its denominator is the batch size, whatever the batch contains.

### The pool used to delete two classes, and it shaped everything

Until 2026-09-07 a claim was drawable only if its cited bucket carried an **evidence annotation**.
But `IRRELEVANT` means *"no information in the cited paper is relevant"* and `ETIQUETTE` means
*"unclear what is being cited to this paper"* — both are **defined by the absence of evidence**, so
neither has evidence segments to point at.

The filter therefore deleted exactly those two classes and nothing else: **442 of 2141 TRAIN rows
(300 ETIQUETTE + 142 IRRELEVANT) and 61 of 316 dev rows (37 + 24)** — an exact match, while every
other class was 100% evidence-covered. It was a property of our filter, not of the benchmark.

⚠ **What that does and does not explain.** It explains why no run was ever *scored correct* on an
`IRRELEVANT` claim: there were none in the pool to be scored on. It does **not** explain why the
program never *emitted* `IRRELEVANT` — the program never sees gold labels at all, so the pool's
composition cannot reach its output. Those are two different facts with two different causes, and
the repaired pool fixes only the first. Do not expect a program to start predicting `IRRELEVANT`
merely because the pool now contains some; if it does not emit them, that is a rubric question and
it is yours.

Their labels are recovered from the benchmark's per-citation annotation files by matching claim
text (`sampling.recovered_gold`). The join is controlled against rows whose gold is already known:
**235 agree, 0 disagree** — its only failure is *no match* (~8%), never a wrong label, and
unmatched rows stay excluded. Pools are now **2076 TRAIN / 311 dev**.

### The one table: what a do-nothing program scores, on every axis

One fixture, one pool, every number in one place — the **repaired drawable dev pool, n=311**. The
program is "emit `ACCURATE` for every claim and do no work". All measured, not estimated, and pinned
by `score_sarol3.py --selftest`.

| Axis | Do-nothing scores | What it is |
|---|---:|---|
| **`primary_metric`** (accuracy, 9-class) | **0.595** | **The objective. This is the floor to beat.** |
| `micro_f1` (accuracy, after the 3-way collapse) | 0.595 | Diagnostic. Equal to the objective *only* for this program |
| `macro_f1_renormalised` (9-way, classes present) | 0.093 | Diagnostic. The collapse detector |
| `macro_f1_3way` | 0.249 | Comparability with the published baselines |
| `macro_f1_9way` (fixed /9 denominator) | 0.097 | Descriptive breakdown |

The 3-way gold distribution underlying it — `ACCURATE` **185 (59.5%)**, `NOT_ACCURATE` **67
(21.5%)**, `IRRELEVANT` **59 (19.0%)**. The `IRRELEVANT` row used to read 1.8%; that was the
deleted-classes bug, not the benchmark, since `ETIQUETTE` and `IRRELEVANT` both collapse into it and
both were being filtered out.

**Why `micro_f1` reads the same as the objective here, and will not once you do any work.** Both are
accuracy; they differ only in whether the labels are compared before or after the 3-way collapse. A
program that only ever says `ACCURATE` is right on exactly the gold-`ACCURATE` claims either way, so
the two coincide at the floor. The moment the program starts emitting the other eight labels they
separate, and **the gap between them is precisely the mass of your within-bucket confusions** — a
`CONTRADICT` answered for an `OVERSIMPLIFY` is wrong on `primary_metric` and right on `micro_f1`.
Read the gap as a readout: wide means much of your error is fine-grained discrimination inside
NOT_ACCURATE; narrow means your errors cross bucket boundaries.

### Why not 3-way, which the objective used to be

3-way collapses `OVERSIMPLIFY` / `NOT_SUBSTANTIATE` / `CONTRADICT` / `MISQUOTE` / `INDIRECT` into
one NOT_ACCURATE bucket, so every confusion among them costs nothing — a quarter of dev with no
gradient on it. Its IRRELEVANT bucket also rested almost entirely on the claims the filter was
deleting. It is still reported as `macro_f1_3way` for the published baselines (MultiVerS 0.52,
GPT-4 4-shot 0.45): a comparability number, not the objective.

### Reported alongside

- Per-class F1 for all three **buckets** (`per_class_f1`) and for all nine **labels**
  (`per_class_f1_9way`). ⚠ These answer different questions. `per_class_f1` has only three entries,
  so it cannot tell you anything about a nine-class prediction — if you are checking whether
  `MISQUOTE` moved, `per_class_f1_9way` is the only one that can say.
- The 3×3 confusion matrix.
- `macro_f1_9way`, a descriptive breakdown with a fixed /9 denominator. **Read `support_9way`
  first**: it divides by nine regardless, so a batch whose gold covers five classes caps at
  5/9 = 0.556 however good the predictions — a low 9-way macro on a small batch usually just means
  the batch was small. There are **no published baselines** at 9-way granularity; Sarol et al.
  abandoned that resolution because models could not learn it.
- `do_nothing_floor` — the always-`ACCURATE` score on *this* batch's gold. Quote it beside every
  accuracy you report.
- `error_class_counts`, including `invalid_label` (see below).

### Invalid labels

A label outside the nine is not a crash and is never silently re-bucketed. It is charged as a miss
against whatever the gold class was, and counted under `invalid_label` and
`invalid_label:<THE_LABEL>`. An edit that invents vocabulary therefore just scores worse.

## Known failure modes

A head start, not a complete taxonomy. **They are ordered by weight of evidence, best first**, and
numbered in that order — modes 1-3 come from the **n=50** run of 2026-09-02; modes 4 and 5 were
observed on a stratified **N=5** smoke run in April 2026
(`docs/plans/experiment-april-20-findings.md`). Where they disagree, prefer the larger sample. The
bracketed id after each heading is the number the mode carried in earlier documents, which numbered
them by discovery date rather than by evidence, so a reader working top-to-bottom met the weakest
evidence first and its correction afterwards.

### 1. The judge is too STRICT, not too lenient — n=50 *(was mode 3)*

The strongest signal in the 2026-09-02 run: iteration 2's mistake corpus was **16 of 19 rows with
gold `ACCURATE`**. The program was calling correct citations inaccurate far more often than the
reverse. Mode 4 below points you at making the judge *stricter* about indirect attribution; on n=50
the error mass sat squarely on the other side. Start here, and read **`per_class_f1_9way`** for
ACCURATE against the NOT_ACCURATE classes before you accept either framing — `per_class_f1` has only
the three buckets in it and cannot answer a nine-class question.

### 2. Retrieval silence read as absence — n=50, and invisible to the judge *(was mode 4)*

Under `retrieval` the judge is handed a BM25 top-*k* subset of the cited paper and **nothing in the
prompt or the rubric tells it that it is a subset.** Observed consequence: given 20 chunks of a
COVID-NPI paper, the judge located two of five named interventions and wrote that lockdowns are
things "this paper never discusses" — of a paper about lockdowns.

So an "unsupported" verdict on this rung conflates two very different things: the paper does not
say it, and the retrieved window did not contain it. The rubric is yours to edit and this
distinction is exactly the kind it can carry. `sub_claims[].evidence[].locator` in the mistake
corpus is how you tell them apart — scattered locators across the paper mean broad coverage, a
tight cluster means you are looking through a keyhole.

### 3. The judge does not decompose multi-proposition claims — n=50 *(was mode 5)*

Every one of the 50 TRAIN claims produced exactly **one** sub-claim. On at least 5 of them the
judge's own `nuance` prose named two propositions — *"both halves of the citing sentence"*, *"the
morbidity conjunct"* — and still emitted a single sub-claim covering both.

This matters twice over. A sentence whose first half is supported and second half is not has no way
to be scored as such, so it gets one verdict for two claims; and while this holds the worst-wins rollup is
the identity function, so reordering the strictness ladder cannot move anything. Decomposition is
governed by the editable clarifications layer, so it is in scope for you — and it is the change that
would make the ladder matter at all.

### 4. The INDIRECT-detection blind spot — N=5 only; read mode 1 first *(was mode 1)*

The adjudicator calls indirectly-attributed claims `ACCURATE`. Two of five claims failed this way,
including the most clear-cut INDIRECT case available: a cited review in which *every* relevant
passage was itself an attribution to some other primary source, which the adjudicator nonetheless
called ACCURATE.

The shape: the cited paper contains the fact, but credits someone else for it. The citing author
should have cited the primary. `INDIRECT` when the cited paper is a review,
`INDIRECT_NOT_REVIEW` otherwise.

Why it looked worth attacking first — and why the n=50 evidence complicates that (mode 1 found the
error mass on the leniency side, and no mistake in the three 2026-09-02 corpora carried gold
`INDIRECT` at all beyond a single instance):

- **The signal is lexically detectable.** Evidence snippets that support the claim end in citation
  markers — `(12)`, `(12,15)`, `(Ota et al., 2009)`. If every supporting quote carries one, the
  fact is being attributed onward.
- **The rubric already distinguishes the classes**, so no vocabulary change is needed.
- **There is an unused slot for it.** The extractor's `attestation.indirect_attribution_check`
  exists and is currently free-form prose the adjudicator can ignore without consequence.
- **The blast radius is larger than the headline rate.** Sarol reports INDIRECT at 1.2% of
  single-citation claims and 2.8% of multi-citation ones, but `OVERSIMPLIFY` and
  `NOT_SUBSTANTIATE` instances frequently carry an indirect-attribution component too.

Note the collapse: `INDIRECT` → NOT_ACCURATE but `INDIRECT_NOT_REVIEW` → IRRELEVANT. That used to
be the reason this confusion was worth attention — it crossed two 3-way buckets while its neighbours
did not. **Under accuracy that argument is retired**: every wrong label costs exactly one claim,
whatever bucket it collapses into. The distinction is worth getting right on its own merits now, not
because of where it lands.

### 5. Severity under-commitment — N=5, tentative, and NO LONGER invisible *(was mode 2)*

Two of five claims landed one step down a severity ladder from gold: gold `NOT_SUBSTANTIATE`
predicted `OVERSIMPLIFY`, and gold `CONTRADICT` predicted `NOT_SUBSTANTIATE`. The second is the
informative one — the extractor had already recorded the verbatim opposing passage that
`CONTRADICT` requires, and the adjudicator still dropped a level.

Two honest caveats, both of which should temper how much effort you spend here:

- **N=5 is within noise.** Whether the adjudicator *systematically* under-commits needs N≥50 to
  say. Do not treat it as established. This caveat stands.
- ~~**Both misses are 3-way hits**, so this pattern costs nothing on the frontier.~~ **No longer
  true, and the reversal matters.** That was written when the objective was 3-way; `OVERSIMPLIFY`,
  `NOT_SUBSTANTIATE` and `CONTRADICT` all collapse into NOT_ACCURATE, so a slip among them was free.
  **Under accuracy every one of them is a full miss.** These three plus `MISQUOTE` and `INDIRECT`
  hold 67 of dev's 311 claims, and confusions *inside* that group are now scored — they are exactly
  the mass that `micro_f1` still forgives and `primary_metric` does not.

So: this went from "worth recording, not worth optimizing" to a live target, on the same evidence.
The N=5 caveat is the only thing still holding it back, so confirm the pattern at n≥50 before
spending an iteration on it — but do look.

## Multi-citation claims are half the data

51% of Sarol instances are multi-citation: the sentence cites a cluster, `[1,2,3]`, and only one
member is under evaluation. Verify only the portion of the claim attributable to *this* source.
Content a sibling citation might cover does not count against the current one. If the grouping is
so ambiguous that no sub-claim can be attributed to a single source, that is what `ETIQUETTE` is
for.

This is the single largest structural feature of the dataset and the guidance for it lives in the
editable rubric, so it is fully in scope for you to improve.

## What a good iteration looks like

The error distribution mapped rather than sampled: failure **modes** with counts behind them, edits
aimed at the mechanisms that carry mass, and a written prediction of which verdict classes should
move and in which direction. Make as many edits as the evidence supports — there is no separability
requirement, and the sweep costs the same whether an iteration carries one edit or twelve.
The release reports movement per class, which is only informative if you said in advance which
classes you were aiming at, so the prediction is the part that turns an iteration into a test.
