# Meta-learnings — what iterations have established

Continuity across optimization sessions. Each iteration runs in a fresh session with no memory of
the previous one (deliberately — a retrospective evaluation of version N has to be blind to
everything learned after N), so this file is the only thing that carries forward.

**Read before iterating. Append after.** Move entries between sections as evidence accumulates;
do not delete them. A reverted attempt is as useful as a confirmed one, and more likely to be
retried by accident.

## Status

**Iterations 1, 2 and 3 have run.** `program-v0`, `v1` and `v2` all have TRAIN numbers; **none has
a VAL number — the release files have never been written and no VAL scalar has ever been visible to
this optimizer.** TRAIN 3-way macro-F1: v0 **0.424** (n=25), v1 **0.385** (n=50), v2 **0.356**
(n=50, same batch as v1). v1→v2 is a clean paired comparison; v0→v1 is confounded by a batch-size
change, so read the paired row in the iteration-2 log, not the headline.

**The one-line summary of three iterations: the judge's ACCURATE side has improved and its
NOT_ACCURATE side has decayed, and macro tracks the weaker of the two.** Both of the last two edits
were one-directional toward lenience. The next edit that helps will have to move claims in *both*
directions on the same batch.

### The v0 baseline (iteration 1 release, TRAIN n=25, profile `retrieval`, k=20)

18 correct / 7 mistakes. No release JSON was written for this iteration, so the metric below was
reconstructed from `train/mistakes/phase1-train-i1.json` plus `train/run_manifest.json`
(`validation.overall_verdict` gives the prediction for all 25; the 18 non-mistakes have
pred == gold). **Verify against the engine's own number when a release file appears** — if they
disagree, the engine's is the one that scored the run.

| | value |
|---|---:|
| **3-way macro-F1** | **0.424** |
| micro-F1 | 0.720 |
| ACCURATE F1 | 0.811 |
| NOT_ACCURATE F1 | 0.462 (P 0.43 / R 0.50) |
| IRRELEVANT F1 | 0.000 |

3-way confusion, gold rows × pred cols (ACCURATE / NOT_ACCURATE / IRRELEVANT):

```
ACCURATE      15   4   0
NOT_ACCURATE   3   3   0
IRRELEVANT     0   0   0
```

Four facts worth carrying forward:

- **v0 is above the always-ACCURATE floor (0.292) and below GPT-4 4-shot (0.45).** It has not
  collapsed to the majority class — it predicts NOT_ACCURATE 7 times in 25.
- **The errors are two-directional and roughly balanced**: 4 over-calls (gold ACCURATE →
  NOT_ACCURATE) against 3 under-calls. A pure "be stricter" or "be more lenient" edit trades
  precision against recall and probably nets zero. What is needed is a *sharper* boundary, not a
  shifted one. Prefer edits that fix both directions.
- **Zero IRRELEVANT gold and zero IRRELEVANT predictions in this batch**, so IRRELEVANT F1 is 0 and
  macro is capped at 0.667 on a batch like this. The scorer always divides by 3 (confirmed against
  the published always-ACCURATE calibration: 0.877/3 = 0.292). Do not read the 0.0 as a failure to
  detect IRRELEVANT; there was nothing to detect. Equally, do not chase IRRELEVANT blindly — at a
  1.8% base rate a wrong IRRELEVANT prediction costs on ACCURATE and gains nothing.
- **All 7 mistakes were 9-way errors that were also 3-way errors.** P2's severity-under-commitment
  pattern (errors that are 3-way hits) did **not** reappear here. No evidence for it at n=25.

### Instrument observations from iteration 1

- `iter/1/release_train.json` / `release_val.json` were **not written**. What existed was
  `train/mistakes/phase1-train-i1.json`, `train/run_manifest.json` and `val/run_manifest.json`.
  Neither manifest carries a computed metric, so no VAL scalar was visible to iteration 1 at all.
  If this recurs, reconstruct TRAIN as above and say plainly that VAL is unavailable.
- `canary` is `null` in both manifests — the canary did not run. **This is not a canary failure**
  (nothing was compared and found different), so it is not a stop. But it does mean iteration 1's
  number has no round-trip guarantee behind it. Flag it if it persists.
- VAL ran at **n=50**, not the full 316. TRAIN ran at **n=25**. Both are small: a single claim moves
  3-way macro by roughly 0.02–0.04 on TRAIN. Treat sub-0.05 movements as noise.
- `validator_error_class_counts` empty on both splits; no invalid labels.
- Cost: TRAIN $21.13 for 25 claims, VAL $42.04 for 50 — about **$0.84 per claim**, one adjudicator
  session each. A full 316-claim VAL would be roughly $265.

Comparison points, for orientation only (other systems, not earlier versions of this one):

| System | 3-way macro-F1 |
|---|---:|
| MultiVerS | 0.52 |
| GPT-4, 4-shot | 0.45 |
| always-ACCURATE do-nothing | 0.292 (micro 0.781) |

The last row is the floor that matters. A program scoring near 0.292 with a high micro is not a
weak program, it is a program that has collapsed to the majority class.

## Confirmed

*(Fixes that improved the frontier scalar and held up on a later iteration. Nothing here yet.)*

| Iter | Change | Effect on macro-F1 | Held up at iter |
|---|---|---|---|

## Pending

Hypotheses with evidence but no iteration behind them yet. Both come from a stratified N=5 smoke
run in April 2026 (`docs/plans/experiment-april-20-findings.md`) — real observations, tiny sample.

### P0 — the multi-citation attribution rule (iteration 1's edit; **scored at iteration 2 — inconclusive on the frontier, harmful in mechanism; see the iteration-2 log**)

See "Iteration 1" below for the change itself. Stated as a hypothesis so iteration 2 can judge it:
the grouped-citation rule was an *unconstrained free parameter*, and the judge tuned it per claim
until it reached a comfortable verdict — narrowing the attributable portion to produce an
over-call, widening the sibling-citation excuse to produce an under-call. Naming a procedure for
the partition, and stating that grouping changes *what* is judged and never *how strictly*, should
remove the parameter.

### P1 — INDIRECT-detection blind spot

Indirectly-attributed claims are called `ACCURATE`. Two of five smoke claims failed this way,
including the most clear-cut INDIRECT instance available (a cited review in which every relevant
passage was itself an attribution elsewhere).

Proposed handle: supporting evidence snippets that end in citation markers — `(12)`, `(12,15)`,
`(Ota et al., 2009)` — signal onward attribution. The extractor's
`attestation.indirect_attribution_check` slot already exists and is currently free-form prose the
adjudicator can ignore without consequence.

Why this is the first thing to try: the signal is lexically detectable, the rubric already
distinguishes the classes, and the review/not-review split straddles two different 3-way buckets
(`INDIRECT` → NOT_ACCURATE, `INDIRECT_NOT_REVIEW` → IRRELEVANT), so getting it right pays on the
frontier scalar rather than only on the 9-way breakdown.

**Status:** untested — and **unreachable under the `retrieval` profile.** Iteration 1 adds one
data point against its *urgency*: across 25 TRAIN claims the judge predicted `INDIRECT` /
`INDIRECT_NOT_REVIEW` zero times, and no mistake had either as gold. The blind spot may well be
real, but at this base rate it is not where the 0.424 is being lost. n=25 cannot rule it out.

⚠ **Read this before spending an iteration on P1.** The handle above is *extractor-side*: it
depends on `attestation.indirect_attribution_check` carrying something an adjudicator can act on.
Under `retrieval` there is no extractor, and the mechanical producer sets that field to `null` on
every claim — so the fix as written cannot be applied and cannot be measured on this rung.

What remains testable under `retrieval` is the narrower question: **can the judge detect onward
attribution from the passages it is handed?** The citation-marker signal is in the retrieved
snippets themselves, so a rubric change that tells the adjudicator to treat a trailing `(12)` /
`(Ota et al., 2009)` inside an otherwise-supporting passage as an INDIRECT signal is both legal and
in scope here. It is a weaker version of the same idea, and the delta between it and the
extractor-side fix is part of what Phase 2 is for.

### P2 — severity under-commitment

Two of five smoke claims landed one step down a severity ladder from gold (gold
`NOT_SUBSTANTIATE` → predicted `OVERSIMPLIFY`; gold `CONTRADICT` → predicted `NOT_SUBSTANTIATE`).
The second is informative: the extractor had already recorded the verbatim opposing passage that
`CONTRADICT` requires, and the adjudicator still dropped a level.

**Do not spend an iteration on this yet, for two independent reasons.** N=5 is within noise — 
whether the under-commitment is *systematic* needs N≥50. And both misses are 3-way **hits**: all
three labels collapse into NOT_ACCURATE, so the pattern costs nothing on the frontier scalar. It is
visible only in the 9-way breakdown, which is descriptive and has no published baseline.

Record instances when you see them. Revisit only if the 9-way axis ever becomes the objective,
which would be a deliberate decision by a human, not something to infer from a diagnostic.

**Status:** untested, and deliberately deprioritized. Iteration 1 saw **no** instances: all 7
mistakes crossed a 3-way boundary, none was a 9-way-only severity slip. Weak evidence against the
pattern being systematic.

### P4 — absence of evidence read as evidence of absence (`retrieval`-specific; **queued for
iteration 2**)

Not tested in iteration 1 — deliberately held back so it would not confound P0's measurement.

Under `retrieval` the judge sees BM25 top-20 chunks, and **nothing in the prompt or the rubric tells
it so.** The prompt's "do not invent evidence or override the extractor's findings" reads as though
the envelope were a curated complete view of the paper. The judge then reasons from silence.
Clearest instance, claim `193-11` (gold ACCURATE, predicted NOT_SUBSTANTIATE): the citing sentence
lists five non-pharmacological interventions, the judge found two in the retrieved passages and
wrote that travel restrictions, curfews and lockdowns are things "this paper never discusses" — of
a COVID-NPI paper, on the strength of 20 chunks. It very likely does discuss them; BM25 simply did
not surface them.

Proposed handle, and the reason it is not obvious: the judge cannot distinguish "absent from the
paper" from "absent from the retrieval" — but it can use **topical centrality** as a prior.
Lockdowns in an NPI paper are core subject matter, so silence is a retrieval gap. Schizophrenia in
a stress-and-neurogenesis paper is off-topic, so silence across 20 chunks is real absence — and
that is exactly the split gold draws between `193-11` (ACCURATE) and `1408-43` (NOT_SUBSTANTIATE).

Expected direction: raises NOT_ACCURATE **precision**, lowers recall slightly. Note it is
one-directional, which is why P0 went first — P0 addresses both.

**Status:** **subsumed and tested at iteration 2.** The n=50 batch showed the defect is real but
larger than P4 described: retrieval-silence is one of two inputs to a single over-calling
mechanism, the other being an unstated sufficiency threshold. Iteration 2 attacks both together as
P5. Do not re-run P4 as a standalone hypothesis; it is not separable from P5.

### P5 — no stated sufficiency threshold for partially-substantiated compound claims (iteration 2's edit; **awaiting its first score**)

The judge has no rule for *how much* of a claim must be found in the evidence to warrant ACCURATE,
and no statement that the envelope is a partial retrieval. It defaults to element-wise
verification: any enumeration item or conjunct it cannot locate becomes a "key element missing"
and the claim becomes NOT_SUBSTANTIATE. Gold does not work that way — gold ACCURATE tolerates a
citation that supports a sentence's central proposition even when a peripheral listed item is not
in the retrieved passages.

**Status:** **scored at iteration 3 — half right, and its falsifier fired.** Over-calls fell 16 → 9
as predicted, but under-calls rose 3 → 7 and all 11 changed predictions moved toward ACCURATE. TRAIN
macro fell 0.385 → 0.356 on the identical batch while micro rose 0.620 → 0.680. **Not reverted** —
ACCURATE F1 rose 0.716 → 0.795 and seven of the eleven changes were correct. The threshold is
retained and bounded by P7. See the iteration-3 log.

### P7 — "peripheral" was an unbound term (iteration 3's edit; **awaiting its first score**)

P5 defined *how much* of a claim must be substantiated and never defined *which parts count*. Its
only test for "peripheral" was topical centrality **of the paper**, which says nothing about how the
citing sentence commits. The judge filled the gap in its own favour and excused four positively
asserted specifics — a mortality figure, two of four percentages, a stated consequence, a temporal
finding — as peripheral or as retrieval gaps.

The proposed discriminator is **how the citing sentence states the element**, not how central it is
to the paper: open-ended or hedged phrasing ("such as", "various", "and others", "potentially")
asserts nothing particular of this source and is genuinely peripheral; a number, magnitude,
direction, stated consequence or temporal finding is positively asserted and is never peripheral,
however topical the paper. Plus one line closing the related leak that absence of contradiction was
being read as support.

**Status:** edit made at iteration 3, not yet scored. It is aimed by name at `1314-60`, `638-48`,
`915-51`, `969-93`, and its falsifier is paired on the same 50 claims — see the iteration-3 log.

## Reverted

*(Changes tried and backed out, with the reason. Nothing here yet.)*

| Iter | Change | Why reverted |
|---|---|---|

## Notes on the instrument itself

Things learned about the harness rather than the program. Worth recording separately — an
instrument problem misread as a program result is the expensive kind of mistake.

- **VAL is scalar-only by construction.** If you want VAL's per-class breakdown, that want is the
  leakage mechanism working as designed. Use TRAIN's.
- **`scored: false` is not a regression.** It means the number is a placeholder and `reason` says
  why. Reacting to it with a prompt edit is chasing an infrastructure signal.
- **A canary failure invalidates the whole run**, and every comparison across the break. Stop;
  never edit around it.
- **Contract files are enforced by re-hash, not by request.** Modifying one fails the iteration
  before scoring or freeze, and that iteration's work is lost.

## Iteration log

### Iteration 1 — the multi-citation attribution rule

**Baseline produced:** TRAIN 3-way macro-F1 **0.424** (reconstructed; see Status). No VAL scalar was
available.

**Failure class named:** *unconstrained attribution-partitioning on grouped multi-citations.*
`multi_cit_context` was `grouped` for **4 of the 7 mistakes**, and the rubric's grouped rule is
implicated in 3 of those 4 — firing in **both** directions:

- `1408-43` (gold NOT_SUBSTANTIATE, pred ACCURATE) — the claim named depression, anxiety and
  schizophrenia; the judge conceded "the paper says nothing about schizophrenia" and then excused
  it: "under the multi-citation rule that element is left to sibling citations and is not charged
  against this source."
- `30-52` (gold NOT_SUBSTANTIATE, pred ACCURATE) — the source's models are pharmacologically
  complex-I-*inhibited*, the claim says complex-I-*deficient*; waved off as "a wording looseness
  that does not change the substance" while invoking "the portion of this grouped citation
  attributable to it."
- `787-44` (gold ACCURATE, pred CONTRADICT) — the judge narrowed the attributable portion to the
  single clause "a less effective Aβ internalization in vivo," judged that fragment in isolation,
  and found the source said the opposite.

**Mechanism hypothesised:** the rule was one-directional and gave no procedure. It told the judge to
verify "only the portion attributable to this specific source" without saying how to find that
portion, and stated only the ACCURATE consequence ("if the evidence supports the source-specific
portion, label ACCURATE even if the overall sentence says more"). The "portion" was therefore a
free parameter the judge could tune per claim until the verdict felt right — narrow it and a
fragment reads as CONTRADICT, widen the sibling excuse and a real gap reads as ACCURATE.

**Edit made** (both files; the rule is stated once and referenced once):

1. `specs/verdict_schema_sarol.md` — rewrote "Multi-citation handling". Added a two-case procedure
   for fixing the attributable portion, *from the citing sentence alone, before looking at the
   evidence*: (1) the sentence syntactically assigns a clause to this citation → that clause; (2) it
   does not assign, the cluster sits at the end → **the whole claim**, every enumeration item and
   every conjunct, with no carving out on the theory that a sibling might cover it. Then the key
   sentence: fixing the portion is the *only* thing grouping changes — it narrows *what* is judged,
   never *how strictly*, and is never in itself a reason to prefer ACCURATE. Also tightened the
   ETIQUETTE line, which previously read "grouped ambiguously such that no sub-claim can clearly be
   attributed to a single source" — under case 2 that description fits every end-of-sentence
   cluster, which would have pushed a large share of the data into ETIQUETTE and therefore into the
   IRRELEVANT bucket. It now says explicitly that an end-of-sentence cluster is case 2, not
   ambiguity.
2. `prompts/adjudicator-dispatch-sarol.md` — **deleted** the four-line restatement of the old rule
   at step 4 and replaced it with a one-line pointer to the rubric section. The prompt shrank by 3
   lines. This was duplication with drift risk (the rubric itself warns against second copies), and
   the prompt's copy carried the same one-directional ACCURATE bias.

Net: rubric +7 lines, prompt −3. Rollup ladder untouched and still the sole fenced block in the
rubric; no contract file touched; no change to per-claim call count (still one adjudicator session).

**Predicted movement** — targeting `NOT_SUBSTANTIATE`, `CONTRADICT`, `ACCURATE`:

- `NOT_SUBSTANTIATE` **recall up**: claims like `1408-43` and `30-52`, where an unsupported
  enumeration item or a substantive mismatch was excused as a sibling's responsibility, should now
  be charged. This is the main intended gain.
- `CONTRADICT` **down / more conservative**: over-narrow partitions like `787-44` should stop
  producing fragment-level contradictions. Predicted 1 → 0 on a batch of this size.
- `ACCURATE` **recall roughly flat, precision up**: fewer gold-ACCURATE claims lost to over-calls,
  but this edit does not address the two *single*-citation over-calls (`193-11`, `1759-21`), so
  ACCURATE will not be clean.
- **3-way macro-F1 up**, driven by NOT_ACCURATE F1 rising from 0.462 — both its precision and its
  recall should improve, which is the point of a boundary-sharpening rather than
  threshold-shifting edit. Rough target 0.50–0.55 on TRAIN.
- **Falsifier:** if NOT_ACCURATE recall rises while its precision falls by as much, the edit merely
  shifted the threshold toward strictness rather than sharpening the boundary, and it should be
  reverted rather than tuned.

**Not attempted, and why:** P4 (absence-of-evidence, above) is a real and clearly-evidenced defect
and was the runner-up. Held for iteration 2 so that P0's effect stays measurable — two rubric edits
in one pass would have been unattributable. P1 (INDIRECT) is unreachable on this rung as written and
had zero instances at n=25.

### Iteration 2 — the sufficiency threshold for partial support

**Instrument note first.** As at iteration 1, `iter/2/release_train.json` and `release_val.json`
were **not written**. What existed was `train/mistakes/phase1-train-i2.json`,
`train/run_manifest.json` and `val/run_manifest.json`. The VAL manifest carries no gold and no
computed metric, so **no VAL scalar has ever been visible to this optimizer** — two iterations, and
the frontier number the objective is defined over has not once been observable. TRAIN metrics below
are reconstructed the same way iteration 1's were. `canary` is `null` on both splits again — still
not a canary *failure* (nothing was compared and found different), but two runs now have no
round-trip guarantee. Both of these are infrastructure signals; no prompt edit was made in response
to either. **They are worth a human's attention: the release files and the canary are the two
things the loop's design leans on hardest, and neither has run yet.**

**The headline TRAIN number fell, and that is mostly the batch.** Read the paired row, not the
first one.

| | v0 (iter 1) | v1 (iter 2) |
|---|---:|---:|
| TRAIN batch | n=25 | n=50 (a strict superset — verified) |
| 3-way macro-F1, as-run | 0.424 | 0.385 |
| 3-way macro-F1, **paired on the shared 25** | 0.424 | **0.433** |
| 3-way macro-F1, v1 on the 25 *new* claims only | — | 0.340 |

Only **3 of 25** predictions changed between v0 and v1: `1408-43` fixed (ACCURATE →
NOT_SUBSTANTIATE, gold NOT_SUBSTANTIATE — the exact claim P0 was aimed at), `533-19` and `808-65`
broken (both gold ACCURATE). So **P0 was close to a behavioural no-op**, and the 0.424 → 0.385 drop
is batch composition, not regression. Do not revert it on the headline number.

**On P0's own falsifier.** Iteration 1 wrote: revert if NOT_ACCURATE recall rises while precision
falls by as much. Across batches that is exactly what happened (P 0.43 → 0.32, R 0.50 → 0.70). But
the paired evidence says P0 moved almost nothing, so the falsifier is firing on a batch effect and
should not be honoured as written. **Lesson about the falsifier itself: it was stated in unpaired
terms on a metric measured on a batch that was free to change size. Write future falsifiers against
claims the previous version also ran.** P0's *text* is nonetheless implicated in the mechanism
below and iteration 2 amends one of its sentences.

### v1 on TRAIN n=50 — the numbers the edit is aimed at

31 correct / 19 mistakes. 3-way confusion, gold rows × pred cols (ACCURATE / NOT_ACCURATE /
IRRELEVANT):

```
ACCURATE      24  15   1
NOT_ACCURATE   3   7   0
IRRELEVANT     0   0   0
```

macro 0.385 · micro 0.620 · ACCURATE F1 0.716 (P 0.89 / R 0.60) · NOT_ACCURATE F1 0.438
(P 0.32 / R 0.70) · IRRELEVANT F1 0.0 (gold support 0 again).

**The error is no longer two-directional.** At n=25 it was 4 over-calls against 3 under-calls and
the note said a pure lenience edit would net zero. At n=50 it is **16 over-calls against 3
under-calls**. 37.5% of gold-ACCURATE claims are being called something else. NOT_ACCURATE
precision 0.32 is now the binding constraint; its recall, 0.70, is not.

**Failure class named:** *partial-support penalization of compound and enumerated claims.* Ten of
the sixteen over-calls state the pattern in their own nuance text — the judge verifies one part of
a compound claim, cannot find the other in the retrieved passages, and charges the gap:

- `160-11` "substantiates one half" · `1693-72` "substantiates the therapeutic half strongly"
- `1855-59` "substantiates the morbidity half only" · `1992-42` "only the ROS / mitochondrial half"
- `193-11` "two of the five listed measures" · `717-56` "does not substantiate the functional
  element" · `808-65` "two elements … are not substantiated" · `119-80` "the first half is well
  supported" · plus `1819-75` and `706-56` on a narrowed clause.

All ten are gold **ACCURATE**.

**Mechanism hypothesised (P5), two inputs, one effect:**

1. **No sufficiency threshold is stated anywhere.** The rubric says NOT_SUBSTANTIATE is "partial
   support but key element missing" and never says what makes an element key. Element-wise
   verification is the judge's default reading, and every enumeration then fails.
2. **Nothing tells the judge the envelope is a partial retrieval.** Worse, the adjudicator prompt
   actively instructed the failure: *"If evidence is insufficient, pick the rubric class that best
   reflects that state (often ETIQUETTE or NOT_SUBSTANTIATE)."* Under `retrieval` the evidence is
   *always* a BM25 top-20 subset, so that sentence fires on every claim with a long enumeration.
   This is P4's absence-of-evidence defect, and it is not separable from (1) — the threshold is
   what decides whether an unretrieved element matters.

P0's own text contributed: four of the over-calls (`160-11`, `1693-72`, `1992-42`, `717-56`) quote
its case-2 rule back verbatim — "the cluster sits at the end and assigns nothing, so the whole
claim is attributable to this source" — and then charge every conjunct. P0 correctly widened *what*
is in scope and, having no threshold to hand off to, the judge read the wider scope as a longer
checklist.

**Edit made** (both files):

1. `specs/verdict_schema_sarol.md` — new section **"How much of the claim must be substantiated"**
   (+11 lines, placed between the class list and Rollup). States that the evidence is a
   keyword-retrieved subset, that a missing element counts as genuinely absent only when it is core
   subject matter of the paper (lockdowns in a COVID-interventions paper = retrieval gap;
   schizophrenia in a stress-and-neurogenesis paper = real absence), and gives the threshold:
   central proposition supported + one peripheral element neither found nor contradicted →
   ACCURATE; central proposition unsupported, or an element positively conflicting → 
   NOT_SUBSTANTIATE / CONTRADICT. Closes with what "key element missing" does not mean.
2. `specs/verdict_schema_sarol.md`, multi-citation section — **amended two of P0's sentences**, not
   reverted. Case 2 now adds that fixing the portion sets what is *in scope* and the threshold
   decides how much of it must be verified. And "the same bar for a missing or mismatched element"
   — which is the element-wise instruction in so many words — became "the same sufficiency
   threshold, no stricter and no softer." P0's directional guard (grouping is never itself a reason
   to prefer ACCURATE) is kept.
3. `prompts/adjudicator-dispatch-sarol.md` — **deleted** the "often ETIQUETTE or NOT_SUBSTANTIATE"
   default and replaced it in place with a pointer to the sufficiency threshold. Net zero lines.

Net: rubric +11 lines, prompt ±0. Ladder untouched and still the sole fenced block; no contract
file touched; per-claim call count unchanged at one adjudicator session.

**Predicted movement** — targeting `NOT_SUBSTANTIATE`, `OVERSIMPLIFY`, `ACCURATE`:

- `NOT_SUBSTANTIATE` **predictions down sharply** — it is 15 of 22 NOT_ACCURATE predictions and
  most are the partial-support pattern. Expect roughly 15 → 6–8 on a batch of this size.
- `ACCURATE` **recall up, precision roughly flat or slightly down** — recall 0.60 is the damaged
  number; target 0.80+. Precision 0.89 has room to give.
- `NOT_ACCURATE` **precision up, recall down** — this edit is deliberately one-directional, which
  is defensible only because the class is currently at P 0.32 / R 0.70. Target P ≥ 0.5.
- `OVERSIMPLIFY` **down modestly** (4 preds, 3 of them over-calls on partially-supported compounds).
- **3-way macro-F1 up.** Arithmetic on the n=50 batch: cutting over-calls 15 → 5 while losing 2
  true positives gives ACCURATE F1 ≈ 0.875, NOT_ACCURATE ≈ 0.50, macro ≈ **0.46**. Target 0.45–0.50
  on a comparable batch.
- **Falsifier, stated in paired terms this time:** on the claims v1 also ran, if over-calls
  (gold ACCURATE → NOT_ACCURATE) do not fall by at least a third, the threshold was not the binding
  constraint and P5 is wrong. If over-calls fall but under-calls (gold NOT_ACCURATE → ACCURATE)
  rise by as many, the edit shifted the threshold toward lenience instead of locating it, and
  should be reverted rather than tuned.

**Not attempted, and why:**

- **The 3 under-calls** (`1062-13`, `30-52`, `873-82`) are all cases where the judge found real
  support and gold disagrees — annotation-boundary calls, no shared mechanism, and 3 instances.
  Nothing actionable.
- **INDIRECT over-firing — new, and worth a name (P6).** `533-19` (a methods "essentially as
  previously described" cite) and `2000-42` both drew INDIRECT / INDIRECT_NOT_REVIEW against gold
  ACCURATE. Two false positives, zero true positives, across 75 claim-runs. Note this **inverts
  P1**, which predicted the judge would *under*-detect indirect attribution: under `retrieval` it
  over-detects. Left alone this iteration to keep P5's measurement clean, and because 2 instances
  is a thin basis. If INDIRECT false positives persist at n=50, they are worth an iteration —
  `INDIRECT_NOT_REVIEW` lands in the IRRELEVANT bucket, so each one costs on two classes at once.

### Iteration 3 — bounding the peripheral-element allowance

**Instrument note first, and it is now a pattern.** `iter/3/release_train.json` / `release_val.json`
were **not written** — third iteration in a row. What existed was
`train/mistakes/phase1-train-i3.json` and `train/run_manifest.json`. The VAL manifest on disk is
still iteration 2's (mtime 04:21; TRAIN i3 finished 05:45), carries no gold and no computed metric.
**No VAL scalar has ever been visible to this optimizer across three iterations** — the number the
objective is defined over has never once been observed. `canary` is `null` again on both splits:
still not a canary *failure*, but three runs now with no round-trip guarantee. Both are
infrastructure signals; no prompt edit was made in response. **This needs a human.** The release
writer and the canary are the two things the loop leans on hardest and neither has ever run.

TRAIN metrics below reconstructed as before (`validation.overall_verdict` for all 50, gold = pred
for the 34 non-mistakes). Cost $40.62 / 50 claims = $0.81 per claim, 50 sub-invocations, one
adjudicator session each — unchanged.

### v2 on TRAIN n=50 — micro up, macro down. Read both.

**Same 50 claims as iteration 2 — verified identical batch, so this is a clean paired comparison.**

| | v1 (iter 2) | v2 (iter 3) |
|---|---:|---:|
| correct / 50 | 31 | **34** |
| micro-F1 | 0.620 | **0.680** |
| **3-way macro-F1** | **0.385** | **0.356** |
| ACCURATE F1 | 0.716 (P 0.89 / R 0.60) | 0.795 (P 0.82 / R 0.775) |
| NOT_ACCURATE F1 | 0.438 (P 0.32 / R 0.70) | **0.273 (P 0.25 / R 0.30)** |
| IRRELEVANT F1 | 0.0 (gold support 0) | 0.0 (gold support 0) |

3-way confusion, gold rows × pred cols (ACCURATE / NOT_ACCURATE / IRRELEVANT):

```
ACCURATE      31   9   0
NOT_ACCURATE   7   3   0
IRRELEVANT     0   0   0
```

**This is the micro-up / macro-down trap the task doc warns about, and it is worth stating plainly
so no future iteration mistakes three extra correct answers for progress.** Gold on this batch is
40 ACCURATE / 10 NOT_ACCURATE; the always-ACCURATE floor scores micro 0.80, macro 0.296. v2 sits at
micro 0.68 / macro 0.356 — closer to the collapse floor than v1 was.

**P5's verdict: partially right, and its falsifier fires.** Iteration 2 predicted over-calls would
fall by at least a third — they did, 16 → 9. But it also said: *if over-calls fall and under-calls
rise by as many, the edit shifted the threshold toward lenience instead of locating it.* Under-calls
went 3 → 7. And the decisive evidence is the direction of every change:

**11 predictions changed between v1 and v2 and all 11 moved toward ACCURATE. Not one moved the
other way.** Seven were right, four were wrong. That is a pure threshold shift, not a sharper
boundary — exactly what iteration 1's note said would net roughly zero, and here it nets negative
because the class it drains (NOT_ACCURATE, support 10) carries a third of the macro.

- **Fixed (all gold ACCURATE):** `119-80` `160-11` `1693-72` `1759-21` `193-11` `533-19` `808-65`
- **Broken (all gold NOT_ACCURATE):** `1314-60` `638-48` `915-51` `969-93` — all → ACCURATE

**Do not revert P5.** ACCURATE F1 rose 0.716 → 0.795 and those seven fixes are real. The defect is
that P5's two escapes are unbounded, not that they are wrong.

**Failure class named:** *the peripheral-element escape applied to positively-asserted specifics.*
P5 gave the judge two outs — "core subject matter of the paper → silence is a retrieval gap" and
"one peripheral element neither found nor contradicted → ACCURATE" — and defined "peripheral" only
against *topical centrality of the paper*. It never said anything about **how the citing sentence
states the element**. All four broken claims quote an escape back verbatim while excusing something
the sentence positively asserts:

- `1314-60` "around 60,000 deaths per year" — number not retrieved; excused because "tetanus
  mortality is core subject matter of this source." A specific figure *is* the claim.
- `915-51` "4, 6, 12, and 16%" — two of four percentages found; the other two "neither contradicted
  nor central."
- `969-93` "ultimately improving mitochondrial function" — a stated consequence, dismissed as "the
  secondary conjunct … neither contradicted nor the sentence's central proposition."
- `638-48` "cross-sectional group differences emerged only later in the first year" — a temporal
  empirical finding, accepted as "consistent with … and is nowhere contradicted."

Now put those beside the seven it correctly fixed. What the judge had been wrongly charging there is
uniformly **open-ended or hedged** phrasing: "various strategies", "NPIs *such as* travel
restrictions, curfews …", "viruses and *other* pathogens", "*potentially* interesting … *such as*
microbicides", "*many* diseases". The discriminator is not central-vs-peripheral and not
topical-vs-off-topic. It is **how the citing sentence commits**: open-ended list or hedge (nothing
particular is asserted of this source) versus a positively-asserted specific (a number, a magnitude,
a direction, a consequence, a temporal finding).

Note also the second-order failure in `638-48` and `969-93`: *absence of contradiction* was read as
support. That is a separate leak in the same section and cheap to close in one sentence.

**Edit made** — one file, `specs/verdict_schema_sarol.md`, section "How much of the claim must be
substantiated". The prompt was deliberately not touched, so the change is single-file attributable.

1. Bounded the peripheral bullet: an element is peripheral **only when the citing sentence states it
   open-endedly** — "such as", "various", "and others", or a hedge. Open-ended phrasing does not
   assert that any particular item is in this source.
2. Added the complementary bullet: **a specific assertion is never peripheral, however topical the
   paper is** — number/percentage/rate, magnitude/direction/comparison, stated consequence or
   mechanism, temporal or conditional finding. Not found in the evidence → `NOT_SUBSTANTIATE`, and
   explicitly *not* excusable as a retrieval gap. This is the sentence that overrides P5's
   core-subject-matter escape in the one place it was being abused, without deleting it.
3. Added one line: evidence that fails to contradict an element is not evidence that supports it.

Net: rubric +4 lines, prompt ±0. Ladder untouched and still the sole fenced block in the file; no
contract file touched; per-claim call count unchanged at one adjudicator session.

**Predicted movement** — targeting `NOT_SUBSTANTIATE`, `ACCURATE`, `MISQUOTE`:

- `NOT_SUBSTANTIATE` **predictions up modestly**, 7 → 10–12, and concentrated on the four broken
  claims. Those four are the direct test: the edit is aimed at them by name.
- **NOT_ACCURATE recall up, 0.30 → 0.60+**, precision **up or flat** (0.25 → 0.40+). This is the
  edit's whole point: recover recall without re-buying the nine surviving over-calls, none of which
  turn on an unretrieved specific.
- `ACCURATE` **recall down slightly** (0.775 → ~0.70), **precision up** (0.82 → ~0.90). Some of the
  seven fixes may cost back; `193-11` and `160-11` are the ones to watch, since "such as" and
  "various" are exactly the phrasing bullet 1 protects.
- `MISQUOTE` **may appear for the first time** (0 predictions so far). Bullet 2 puts numbers on the
  judge's radar; a *wrong* number is MISQUOTE, an *unfound* one is NOT_SUBSTANTIATE. Both collapse
  to NOT_ACCURATE, so this is 9-way noise only — recorded so it is not mistaken for a new defect.
- **3-way macro-F1 up.** Arithmetic on this batch: recovering 3 of the 4 broken claims while losing
  1 of the 7 fixes gives ACCURATE F1 ≈ 0.84, NOT_ACCURATE ≈ 0.52, macro ≈ **0.45**. Target
  0.42–0.47 paired on these 50.
- **Falsifier, paired on the same 50 claims:** if `1314-60`, `638-48`, `915-51`, `969-93` do not
  return to NOT_ACCURATE, the open-ended/specific distinction is not the operative one and P7 is
  wrong. If they return but three or more of the seven v2 fixes revert with them, the edit is
  another threshold shift wearing a discriminator's clothes and should be reverted rather than
  tuned — the test is whether *both* directions improve, since 11-for-11 one-directional movement is
  what made v2 fail.

**Not attempted, and why:**

- **The nine surviving over-calls** (`1819-75` `1855-59` `1992-42` `2000-42` `237-91` `706-56`
  `714-56` `717-56` `787-44`) are stable across three rubric versions and split into distinct
  sub-mechanisms — two persistent CONTRADICTs on gold ACCURATE, two OVERSIMPLIFYs, one INDIRECT,
  four NOT_SUBSTANTIATEs. No single edit reaches them and each sub-bucket is 1–4 instances. The
  CONTRADICT pair (`237-91`, `787-44`) is the best-defined and is the natural iteration-4 target if
  P7 lands: `CONTRADICT` requires a verbatim opposing excerpt and is being reached without one.
- **P6 (INDIRECT over-firing)** improved on its own: `533-19` corrected, leaving `2000-42` as the
  only INDIRECT false positive and `915-51` as a *missed* true INDIRECT. One in each direction at
  n=50 — no longer a one-sided pattern, and not worth an iteration. Keep counting it.
- **IRRELEVANT** has had gold support 0 in all three batches. Macro is capped at 0.667 on batches
  like this and nothing can be learned about the third class. Worth a human's attention when
  choosing the next TRAIN sample.

**Amendment to P5 (do not read it as reverted):** P5's threshold is retained in full. Iteration 3
adds the missing half of its definition — P5 said *how much* of a claim must be substantiated and
never said *which parts count*, and an undefined "peripheral" is the same species of free parameter
that P0 left behind for the attributable portion. Two iterations running, the defect has been an
unbound term in a rule rather than a wrong rule. That generalizes: **when adding a rubric rule, name
the test that decides its terms, or the judge will supply one that reaches whatever verdict it
already prefers.**
