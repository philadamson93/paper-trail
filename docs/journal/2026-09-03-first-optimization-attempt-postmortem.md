# First optimization attempt — post-mortem (2026-09-02/03)

Reference: `docs/plans/papertrail-optimizer-requirements.md` · branch `sarol-optimizer-impl`

paper-trail's first real optimization run. Three `retrieval`-profile iterations against the Sarol
2024 benchmark, preceded by a v0 baseline. **The loop worked end-to-end. It produced no measurable
improvement, and the reason is measurement power, not the optimizer.**

Run artifacts: `~/.paper-trail/runs/phase1-2026-09-02/` (outside the repo, per C6.9).

---

## What was measured

Paired on the **identical 37 VAL claims** — the raw 0.4949 (n=37) vs 0.4182 (n=50) comparison
confounds the program change with the sample change, so it should not be quoted.

| | 3-way macro-F1 | micro-F1 | ACCURATE | NOT_ACCURATE | IRRELEVANT |
|---|---:|---:|---:|---:|---:|
| `program-v0` | 0.4949 | 0.784 | 0.885 | 0.600 | **0.000** |
| after 3 iterations | 0.4647 | 0.757 | 0.868 | 0.526 | **0.000** |

TRAIN accuracy across iterations: 0.720 → 0.620 → 0.680 (on batches of 25 → 50 → 50, so not
comparable rung-to-rung).

**The entire VAL delta is one claim.** Of 37 paired claims only **3** changed prediction: 2
`NOT_ACCURATE→ACCURATE`, 1 `ACCURATE→NOT_ACCURATE`; 1 fixed, 2 broken, **net −1**. A single claim
moves 3-way macro-F1 by ~0.03, which is the whole observed "regression". There is no signal here in
either direction.

---

## Finding 1 — the metric is one third unreachable, and the optimizer could not have known

Neither `program-v0` nor any optimized version **ever predicts `IRRELEVANT`**:

- gold in the paired VAL set: `ACCURATE` 26, `NOT_ACCURATE` 9, `IRRELEVANT` 2
- v0 predictions: `ACCURATE` 26, `NOT_ACCURATE` 11
- optimized predictions: `ACCURATE` 27, `NOT_ACCURATE` 10

So `IRRELEVANT` F1 is structurally 0.000 and macro-3 divides by three regardless — **~0.17 of the
frontier metric is pinned at zero before the program does anything.** That is the largest
recoverable gap on the board.

**And the optimizer never saw the class.** The gold labels appearing anywhere in the three TRAIN
mistake corpora are exactly: `ACCURATE`, `INDIRECT`, `NOT_SUBSTANTIATE`, `OVERSIMPLIFY`. No
`IRRELEVANT`, no `ETIQUETTE` — the two 9-way classes that collapse into 3-way `IRRELEVANT`. With
those classes at ~1.8% of gold and TRAIN batches of 25–50, a mistake corpus containing zero
instances is the expected outcome, not bad luck.

**You cannot optimize a class you never observe.** This is structural, and no number of iterations
at this batch size fixes it. Options, in rough order of directness:

1. **Stratify the TRAIN draw** so rare classes are represented (changes the estimator — deliberate,
   not silent).
2. **Raise TRAIN** until rare classes appear naturally (~1.8% ⇒ hundreds of claims; expensive).
3. **Report macro over reachable classes only**, as OQ2 pass 1 already forced once for a different
   reason — with the reachability caveat stated.

## Finding 2 — the optimizer's edits were rational and correctly targeted

Worth recording, because "no improvement" invites the wrong conclusion. Edit scope held exactly:
only `prompts/adjudicator-dispatch-sarol.md` and `specs/verdict_schema_sarol.md`, which is the
`retrieval` editable set. The three contract files were untouched.

What it diagnosed: iteration 2's mistake corpus is **16 of 19 rows with gold `ACCURATE`** — the
program was *too strict*, emitting non-`ACCURATE` labels on claims that were fine.

What it did about it: added a sufficiency-threshold section ("the evidence you are given is a
keyword-retrieved subset … an element you cannot find may simply not have been retrieved"),
distinguishing *peripheral* elements (open-ended "such as" lists, hedges) from *specific
assertions* (numbers, magnitudes, stated mechanisms) that are never excusable as retrieval gaps.
It also rewrote multi-citation handling into a two-case decision procedure and **removed** the old
"prefer ACCURATE" thumb on the scale.

That is a sensible, well-reasoned response to the evidence it was given, and it had the intended
directional effect on VAL (`ACCURATE` predictions 26 → 27). It simply moved ~1 claim on a 37-claim
sample. **The optimizer is not the thing that failed.**

## Finding 3 — the optimizer never saw a VAL scalar. It optimized blind, for all three iterations

**This is the deepest finding of the run, and it came from the optimizer's own log, not from
analysis of the outputs.** `optimizer/meta-learnings.md`, written by the agent itself:

> *"`program-v0`, `v1` and `v2` all have TRAIN numbers; **none has a VAL number — the release files
> have never been written and no VAL scalar has ever been visible to this optimizer.**"*
>
> *"`iter/1/release_train.json` / `release_val.json` were **not written**. … Neither manifest
> carries a computed metric, so no VAL scalar was visible to iteration 1 at all."*

Confirmed independently: no file matching `*release*` exists anywhere under the run root. The
per-iteration release payload — the Tier 2 artifact whose entire purpose is to hand the optimizer
the held-out scalar and nothing else — was never produced.

So the optimizer had **no feedback whatsoever about the quantity being optimized.** It saw TRAIN
mistakes, edited the rubric, and was told nothing about whether VAL moved. Three iterations of that
is not a converging loop; it is three independent guesses. **This alone is sufficient to explain the
absence of improvement**, and it is a wiring gap, not a research result.

Note the irony: the Tier 2 boundary was *over*-enforced. C6.9 correctly put VAL outputs beyond the
optimizer's reach, but the release payload that is supposed to carry the scalar *back* never got
written — so the optimizer got the isolation without the signal.

## Finding 4 — the canary never fired, so no number has a round-trip guarantee

Also from the optimizer's log, and confirmed in both run manifests (`"canary": null`):

> *"`canary` is `null` in both manifests — the canary did not run. **This is not a canary failure**
> (nothing was compared and found different), so it is not a stop. But it does mean iteration 1's
> number has no round-trip guarantee behind it."*

The canary is the guard OQ12 resolved and priced as a real cost term (three firings per iteration,
once per Runner call) precisely so that "a run whose instrument moved is not a run that scored
worse — it is not a run at all". It was configured, priced, and did not execute. Every number from
this run therefore lacks the instrument check the design says it must carry.

## Finding 5 — the optimizer's own TRAIN numbers show a monotonic decline, and it diagnosed why

It computed TRAIN 3-way macro-F1 itself: v0 **0.424** (n=25), v1 **0.385** (n=50), v2 **0.356**
(n=50, same batch as v1). It also flagged the right comparison unprompted — v1→v2 is paired
(identical batch), v0→v1 is confounded by the batch-size change. On the clean paired row, **TRAIN
macro fell 0.385 → 0.356.**

Its one-line self-diagnosis is sharper than anything the output analysis produced:

> *"the judge's ACCURATE side has improved and its NOT_ACCURATE side has decayed, and macro tracks
> the weaker of the two."*

That matches VAL exactly (`ACCURATE` 0.885→0.868 is roughly flat; `NOT_ACCURATE` 0.600→0.526 is the
real loss). The sufficiency-threshold edits made the judge more willing to accept partial support,
which helps the majority class and costs the minority one — and macro punishes precisely that
trade. The optimizer identified its own failure mode correctly while blind to VAL.

## Finding 6 — VAL=50 cannot detect the effect size this optimizer produces

Effects are ~1 claim per iteration; 1 claim ≈ 0.03 macro-F1 at n=37. The frontier is therefore
dominated by sampling noise, which also means **the engine's step-back logic is being driven by
noise** — it will step back on a program that happened to lose one claim. Any future run needs
either a materially larger VAL or an explicit noise floor (crc's Open Q D calls this `τ_cal`, a
stochasticity-calibration threshold, and reaches for replicate aggregation when spread exceeds it —
paper-trail should adopt the same discipline before reading any curve).

---

## Bug 1 — `--val-n` priced the run but did not sample it

**Symptom.** `--val-n` reached `CostModel(val_size=…)` so the preflight quoted a smaller VAL, while
`run_optimization` still handed `run_loop` the caller's static `val_input_ref`. The run would have
scored the full supplied batch at the small-batch price.

**Impact had it shipped.** The preflight quotes **$63** for a run that costs **$647** — a 10×
under-quote on the one decision that is explicitly money-gated. Worse, `BudgetGuard` reads the same
cost model, so the guard would have under-refused by the same factor: both the estimate and the
enforcement were wrong in the same direction.

**Why 296 gates missed it.** Every cost gate asserted on `CostModel`; none asserted that the batch
the Runner actually received had the requested size. The two representations of "VAL size" — a
pricing input and a real staged batch — had nothing tying them together.

**Fixed** (`9871e51`) by `sampling.val_inputs_for()`, which draws and stages the batch that is then
passed to `run_loop`.

**Gate still owed:** assert `len(load_batch(val_inputs.input_ref)) == val_n`. That single check is
what would have caught this, and it does not exist yet. Same check owed for the TRAIN factory.

**Generalisable lesson.** When a flag both *prices* work and *selects* work, a test that only reads
the price proves nothing. Assert on the artifact that gets executed.

## Bug 2 — the TRAIN ramp was off by one, so the cheapest rung never ran

**Symptom.** Requested `10,25,50`; actually ran **25 → 50 → 50** (confirmed from
`sampling/draw_history.json`).

**Cause.** `ramp_for()` indexes `schedule[min(iteration, len-1)]`, assuming 0-based iterations. The
engine calls `train_inputs(iter_n)` with `iter_n` starting at **1**, so it returned rung[1]=25,
rung[2]=50, then clamped to 50.

**Impact.** The 10-claim rung — the cheap, fast one whose whole purpose is to fail early — never
ran. Iteration 3 got no size increment over iteration 2, so the run bought two iterations at the
same scale and the "ramp" was not a ramp. No corruption: draws stayed cumulative supersets
(25 ⊂ 50 ⊂ 50), VAL stayed fixed, spend stayed bounded.

**Why the gates missed it.** `sampling.py`'s selftests call `resolve_batch(0, …)`, `(1, …)`, `(2, …)`
— they assert *my* indexing convention against itself. They passed while disagreeing with the
engine, which is the failure mode of testing an assumption instead of a contract.

**Fix owed.** Normalise to the engine's actual first `iter_n` rather than assuming either
convention, and pin it with a gate that reads that value from `loop.py` (or from a recorded run)
instead of hard-coding 0 or 1.

**Generalisable lesson.** A cross-repo seam's indexing base is a contract, not a detail. Verify it
against the caller; do not infer it.

## Bug 3 — one `val_output_root`, so the per-iteration VAL curve was overwritten

All VAL calls wrote `<val_output_root>/run_manifest.json`, the same path, once per call. Only the
**last** VAL manifest survives, so the three-point VAL curve this run was supposed to produce does
not exist on disk — the reason this post-mortem can only pair v0 against a final state.

**Fix owed:** namespace VAL outputs per iteration and per call (`val/iter<N>/{current,probe}/`).
Cheap, and it is the difference between a curve and a single point.

## Not a bug — the 101-minute "hang" was the laptop sleeping

A claim showed a 101-minute gap with no verdict while a 900s per-call timeout was configured. I
diagnosed a `subprocess.run` pipe-drain defect and wrote that mechanism into a code comment as
established fact. **It was machine sleep** (Phil). macOS's monotonic clock does not advance across
sleep, so the timeout correctly never fired; claims either side took 82s and 4min.

My attempted reproduction returned in 1.0s — i.e. it *disconfirmed* the theory — and I should have
treated that as decisive before asserting a root cause in the code. The comment has been corrected
to describe the process-group kill as **hardening, not a fix**, with a note telling the next reader
to check whether the machine was awake before reading a wall-clock gap as a hang.

**Operational lesson:** run long unattended batches under `caffeinate -i`. Also note detachment
matters — harness-tracked background tasks were killed four times during this session while the
`nohup`-detached chain survived every one.

## Recoverability note — the baseline was salvageable, by luck

The baseline was killed at 37/50. The Runner writes per-claim verdicts incrementally but its
`run_manifest.json` **only after the whole batch**, so 37 finished claims were left on disk with
nothing pointing at them. They were recovered by rebuilding a manifest over exactly the claims that
finished — which is how a v0 baseline exists at all.

**Fix owed:** either write the manifest incrementally, or ship the salvage path as a real script
rather than leaving it as this session's ad-hoc recovery.

---

## Cost

~$370–400 for the session (loop ~$320–345 + baseline ~$39 + smokes/probes ~$5). Exact accounting is
not possible because the per-call manifests overwrite each other — see Bug 3.

Measured per-session cost is **$0.59–$1.08** ($29.55/50 on a VAL call, $40.62/50 on a TRAIN call),
so the calibrated `DEFAULT_PER_SESSION_USD = 1.00` is conservative in the safe direction. The old
`0.05` placeholder was ~20× optimistic.

## Revised conclusion

This run did **not** test whether prose-editing can move the frontier. It could not have: the
optimizer never saw the frontier (Finding 3), the instrument check never ran (Finding 4), and a
third of the metric was unreachable from the data it was shown (Finding 1). Three compounding
instrument failures, none of them the optimizer's doing — which behaved rationally throughout and
diagnosed its own failure mode while blind (Findings 2, 5).

**Treat the 0.4949 v0 baseline as the real deliverable.** It is a genuine first curve point. Treat
`0.4949 → 0.4647` as uninformative and do not record it as evidence about agentic optimization.

## What to do before the next paid run

Ordered by what blocks the most. Items 1–2 are wiring; nothing is learnable until they are fixed.

1. **Make the release payload actually reach the optimizer** (Finding 3). Until the VAL scalar is
   written and visible, the loop has no feedback and more iterations buy nothing. Highest priority
   by a wide margin, and cheap — it is a wiring fix, not a design question.
2. **Make the canary fire, and fail closed if it does not** (Finding 4). A silently absent guard is
   worse than no guard: every number this run produced lacks the round-trip check the design
   requires, and nothing announced it. Absence should stop the run.
3. **Fix the metric's reachability** (Finding 1) — stratify TRAIN, or report macro over reachable
   classes only. Optimizing while a third of the frontier is unreachable wastes every iteration.
   *Phil's call: it changes the estimator.*
4. **Establish the noise floor** (Finding 6) before reading any curve, and gate step-back on it.
5. **Land the three owed gates**: batch-size-equals-requested (Bug 1), ramp indexing against the
   engine's real base (Bug 2), per-iteration VAL output paths (Bug 3).
6. Only then re-run, with a VAL large enough to resolve a ~1-claim effect.

**The cross-cutting lesson.** Every one of the three instrument failures was *silent*: the release
files simply were not there, the canary was `null`, and the ramp quietly ran the wrong rungs. The
offline gates were all green throughout — 296 of them — because each asserted on a local object
rather than on the artifact the next stage actually consumed. **A guard that can be absent without
announcing itself is not a guard.** The next round of gates should assert presence and shape of
what crosses each seam, not the correctness of what produces it.
