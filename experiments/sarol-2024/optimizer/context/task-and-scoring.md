# The task, and what counts as better

## The task

Given a citing sentence from a manuscript and one paper it cites, decide how honestly the sentence
represents that paper. The program is a three-stage pipeline: an **extractor** pulls evidence
passages from the cited paper, an **adjudicator** assigns a verdict from those passages, and a
**verifier** spot-checks the extractor's evidence.

The benchmark is Sarol, Schneider & Kilicoglu 2024, *Assessing Citation Integrity in Biomedical
Publications* (Bioinformatics btae420): 3,063 human-annotated citation instances with reported
inter-annotator agreement, split TRAIN 2,141 / VAL 316 / TEST 606.

⚠ **Those are the headline figures, not the pool you are scored against.** A claim whose cited
bucket carries no evidence annotation has no gold label and is refused at staging, so the
*drawable* population is **1,699 TRAIN / 255 dev** — roughly 20-24% smaller. The gold table below
(1,463 + 376 + 34 = 1,873 annotations) is derived from the smaller population, so read the two
together and do not mix a rate from one with a count from the other.

## The output vocabulary

Nine labels, defined in the frozen `experiments/sarol-2024/specs/verdict_enum_sarol.md`. You cannot change this set.

`ACCURATE` · `OVERSIMPLIFY` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `MISQUOTE` · `INDIRECT` ·
`INDIRECT_NOT_REVIEW` · `ETIQUETTE` · `IRRELEVANT`

## The frontier scalar: macro-F1 over the six measurable classes

**The number being optimized is macro-F1 at 9-way resolution, over the six classes the held-out
split can actually measure, renormalised over those present in the batch:**

`ACCURATE` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `OVERSIMPLIFY` · `MISQUOTE` · `INDIRECT`

That set is not a preference, it is what the data supports. The 9-way gold distribution of the
drawable dev pool (255 claims) is:

| Class | dev gold | in objective |
|---|---:|:--:|
| ACCURATE | 185 | ✅ |
| NOT_SUBSTANTIATE | 25 | ✅ |
| CONTRADICT | 22 | ✅ |
| OVERSIMPLIFY | 8 | ✅ |
| MISQUOTE | 6 | ✅ |
| INDIRECT | 6 | ✅ |
| ETIQUETTE | 3 | ❌ support 3 — one claim moves a macro by ~0.06 |
| INDIRECT_NOT_REVIEW | **0** | ❌ no gold in dev at all |
| IRRELEVANT | **0** | ❌ no gold in dev at all |

Two classes have **no gold instance anywhere in dev**, so raw macro-9 caps a *perfect* program at
7/9 = 0.778 — a property of the sample, not of the program. Renormalising over present classes is
what removes that artifact, and it is why `n_objective_classes_present` is reported beside every
number. **Read it before comparing two scores**: a number renormalised over 5 classes is not
comparable to one over 6.

### Why not 3-way, which this used to be

3-way collapses `OVERSIMPLIFY` / `NOT_SUBSTANTIATE` / `CONTRADICT` / `MISQUOTE` / `INDIRECT` into
one NOT_ACCURATE bucket. In dev that is **67 of 255 claims (26%)** whose entire error structure
becomes invisible: confusing CONTRADICT for NOT_SUBSTANTIATE costs exactly nothing. That is a
quarter of the data with no gradient on it.

Worse, 3-way's IRRELEVANT bucket has support **3** in the entire dev pool (the ETIQUETTE claims;
its other two members have no dev gold). A third of the old objective rested on three claims —
which is precisely why the 2026-09-02 run never predicted IRRELEVANT and ~⅓ of the metric sat
pinned at zero before the program did anything.

3-way is still computed and reported as `macro_f1_3way`, because the published baselines are on
that axis (MultiVerS 0.52, GPT-4 4-shot 0.45). It is a comparability number, not the objective.

### Micro-F1 is reported. It is not the objective, and it is a trap

For single-label multiclass, micro-F1 equals accuracy. The gold distribution is heavily skewed:

| Bucket | Gold count | Share |
|---|---:|---:|
| ACCURATE | 1,463 | 78.1% |
| NOT_ACCURATE | 376 | 20.1% |
| IRRELEVANT | 34 | 1.8% |

So a program that emits `ACCURATE` unconditionally and does no work at all scores **micro 0.725**
on the real dev pool — while scoring **0.140** on the objective and 0.280 on 3-way. Measured, not
estimated. The 2026-09-02 program scored micro 0.784, so *everything the pipeline does* is worth
about six points of micro sitting on top of a 72.5-point floor you get for free by returning a
constant. And inside that band the cheapest way up is to answer `ACCURATE` more often, because
ACCURATE is 72.5% of dev — the gradient points at the do-nothing program. If you find yourself with a
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

A head start, not a complete taxonomy. **Read the ordering caveat first:** modes 1 and 2 were
observed on a stratified **N=5** smoke run in April 2026
(`docs/plans/experiment-april-20-findings.md`); modes 3, 4 and 5 come from the **n=50** run of
2026-09-02 and are correspondingly better evidenced. Where they disagree, prefer the larger sample.

### 3. The judge is too STRICT, not too lenient — n=50, and it inverts mode 1's advice

The strongest signal in the 2026-09-02 run: iteration 2's mistake corpus was **16 of 19 rows with
gold `ACCURATE`**. The program was calling correct citations inaccurate far more often than the
reverse. Mode 1 below points you at making the judge *stricter* about indirect attribution; on n=50
the error mass sat squarely on the other side. Start here, and read `per_class_f1` for ACCURATE
against the NOT_ACCURATE classes before you accept either framing.

### 4. Retrieval silence read as absence — n=50, and invisible to the judge

Under `retrieval` the judge is handed a BM25 top-*k* subset of the cited paper and **nothing in the
prompt or the rubric tells it that it is a subset.** Observed consequence: given 20 chunks of a
COVID-NPI paper, the judge located two of five named interventions and wrote that lockdowns are
things "this paper never discusses" — of a paper about lockdowns.

So an "unsupported" verdict on this rung conflates two very different things: the paper does not
say it, and the retrieved window did not contain it. The rubric is yours to edit and this
distinction is exactly the kind it can carry. `sub_claims[].evidence[].locator` in the mistake
corpus is how you tell them apart — scattered locators across the paper mean broad coverage, a
tight cluster means you are looking through a keyhole.

### 5. The judge does not decompose multi-proposition claims — n=50

Every one of the 50 TRAIN claims produced exactly **one** sub-claim. On at least 5 of them the
judge's own `nuance` prose named two propositions — *"both halves of the citing sentence"*, *"the
morbidity conjunct"* — and still emitted a single sub-claim covering both.

This matters twice over. A sentence whose first half is supported and second half is not has no way
to be scored as such, so it gets one verdict for two claims; and the worst-wins rollup is the
identity function while this holds, which makes the strictness ladder inert (see
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`). The rubric governs decomposition, so this is in scope for you.

### 1. The INDIRECT-detection blind spot — N=5 only; see mode 3 before prioritising it

The adjudicator calls indirectly-attributed claims `ACCURATE`. Two of five claims failed this way,
including the most clear-cut INDIRECT case available: a cited review in which *every* relevant
passage was itself an attribution to some other primary source, which the adjudicator nonetheless
called ACCURATE.

The shape: the cited paper contains the fact, but credits someone else for it. The citing author
should have cited the primary. `INDIRECT` when the cited paper is a review,
`INDIRECT_NOT_REVIEW` otherwise.

Why it looked worth attacking first — and why the n=50 evidence complicates that (mode 3 found the
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

Note the collapse: `INDIRECT` → NOT_ACCURATE but `INDIRECT_NOT_REVIEW` → IRRELEVANT. Getting the
review/not-review distinction wrong moves the answer across two different 3-way buckets, so it
costs you on the frontier scalar, not just on the 9-way breakdown.

### 2. Severity under-commitment — N=5, tentative, and mostly invisible to the frontier

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
