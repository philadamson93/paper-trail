# Meta-learnings — what iterations have established

Continuity across optimization sessions. Each iteration runs in a fresh session with no memory of
the previous one (deliberately — a retrospective evaluation of version N has to be blind to
everything learned after N), so this file is the only thing that carries forward.

**Read before iterating. Append after.** Move entries between sections as evidence accumulates;
do not delete them. A reverted attempt is as useful as a confirmed one, and more likely to be
retried by accident.

**What belongs here rather than in `findings/iter-<n>.md`** is defined in one place: the
*"The three record surfaces, and what goes in which"* section of
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`. The short form is that this
file is about *how to optimize this task* and that one is about *these examples* — but do not
carry a second copy of the rule in your head from here.

---

## Status

**Five iterations have now run against the current objective** (`hillclimb-vm-2026-09-09`), and
their lessons are below. This file was reset on 2026-09-07 — the note about it being "deliberately
empty of history" applied to that reset and stopped being true when the 2026-09-09 run landed.

⚠ **Read everything below against two facts, both measured 2026-09-09.** First, the program those
five iterations tuned **no longer exists**: P0 reset the eight class definitions to the paper's
verbatim text, deleting three clauses the whole run had hill-climbed on. Second, the instrument's
own scatter is **0.06** — a byte-identical program re-scored 0.48 vs 0.42 on the same 50 claims.
Most single-iteration deltas recorded below are 0.02–0.04, i.e. **inside that scatter**. Treat them
as hypotheses that were seen once, not as settled results.

### Why it was reset, so nobody goes looking for the old entries

Three iterations ran on 2026-09-02 and everything they established was denominated in things that
have since changed underneath it:

- **The objective was macro-F1**, renormalised over the classes present in the batch. It is now
  plain **accuracy** over the nine labels, quoted against the release's `do_nothing_floor`. (An
earlier version of this line said 0.595; that is the 311-claim *pool* figure. On the 50-claim VAL
batch the floor is **0.70**. Read the key, not a remembered number.) Every score,
  every comparison and every "this edit helped" in the old log was in the retired unit — and the
  renormalising denominator moved with the batch's class mix, which manufactured a −0.15 TRAIN
  decline across three iterations for a program that never changed. Those numbers cannot be
  rebased; they have to be re-measured.
- **The drawable pool was missing two whole classes.** `IRRELEVANT` and `ETIQUETTE` are defined by
  the *absence* of evidence, and the pool filter required an evidence annotation, so it deleted
  100% of both. Any conclusion about class coverage from that period was drawn on a pool that
  could not contain them.
- **The baseline is being re-cut from pristine `program-v0`.** The versions the old log describes
  (`v1`, `v2`) are not the tree the next run starts from.

The old file is in this branch's git history if it is ever wanted. Two things worth keeping were
lifted out of it before the reset rather than left to die here, and both now live where they are
read every iteration:

- *"When you add a rubric rule, name the test that decides its terms"* — learned twice, at the cost
  of two iterations. It is now step 5 of the standing instructions.
- The reach test for `retrieval`-blamed failures — which half of them the rubric can actually fix.
  It is now in `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md`.

## Confirmed

⚠ **(2026-09-09) These were measured pre-reset, on a program that no longer exists, at step sizes
inside the instrument's scatter.** This section's own bar is "moved the number in a predicted
direction **and been seen again**"; most entries below were seen once. They are preserved because
they are the only record of what five iterations learned about the *rubric* — but several of them
reason about clauses P0 has since deleted. Re-derive before relying on one; do not treat this
heading as a warrant.

- **Enriching the terse rubric with boundary tests cures over-strictness (iter1→iter2).** iter1 added
  ACCURATE-substance, OVERSIMPLIFY-materiality, NS-vs-IRRELEVANT and empty-window tests. On iter2's
  batch the predicted direction held on every common class: pred ACCURATE 20→31 (=gold), NS
  over-prediction 17→8, OVERSIMPLIFY 10→5, invalid_label 5→0, accuracy 0.46→0.60 (VAL program-v1
  0.56), macro ~0.10→0.21 with **no collapse toward ACCURATE** (pred ACCURATE count = gold count).
  A rubric that was one-line-per-label was the bottleneck; worked boundary tests move the number.
- **A written rubric rule does NOT guarantee the judge runs it — "rule exists" vs "rule fired" are
  different failures.** iter1 wrote a full ETIQUETTE/attribution procedure; iter2 emitted **zero**
  ETIQUETTE (3/3 gold missed), and iter2's blame pass found **13 of 20 mistakes were `execution`**
  (rule present, judge skipped it), not `rubric`. The lesson from failure-mode-discovery.md held
  literally: a cluster of execution blames treated as rubric = an iteration spent rewriting a rule the
  judge already had. **Fix execution failures by making the rule unskippable** (move it into the
  dispatch-prompt workflow as a mandatory ordered gate the judge must walk per sub-claim), not by
  re-wording the rubric. iter2 did this; whether it works is the iter3 test.

- **Gate-ification fixes execution failures on the judge's DEFAULT path, not against it (iter2→iter3).**
  iter2 turned skipped rubric rules into a mandatory ordered Gate 0–3. On iter3 the gates that *add a
  check to what the judge already wants to do* worked: accuracy 0.60→0.68 TRAIN, VAL 0.56→0.60 (+0.04,
  first time above the 0.62 floor), macro 0.206→0.32, no ACCURATE-collapse. But the gate that asks the
  judge to *suppress its default* — Gate 0 attribution (don't judge substance, emit ETIQUETTE) —
  **still did not fire**: ETIQUETTE stayed at F1=0 (3/3 real cases skipped, using the rubric's own
  verbatim `[CIT];` examples). Lesson: making a rule mandatory helps when the rule is a *filter on the
  natural verdict*; it does not help when the rule requires the judge to *not do the obvious thing*.
  ETIQUETTE has now resisted both a rule (iter1) and a mandatory gate (iter2). It is also rare/low-mass
  on accuracy — stop spending iterations on it until the common-class work is exhausted.
- **A strictness gate over-corrects: iter2's fix for over-strictness produced over-leniency (iter3).**
  iter1 was too strict (ACCURATE under-predicted). iter2's gate + "prefer ACCURATE on thin window"
  fixed recall but swung the other way: iter3's dominant error (5 of 16 mistakes, crossing the 3-way
  bucket) is non-ACCURATE gold *predicted* ACCURATE — the judge sees a topically-matching passage and
  emits ACCURATE without running the downgrade checks (tell: empty `nuance` + null `remediation` on
  every silent-ACCURATE miss). The pendulum is the recurring risk on this task; the discriminator that
  keeps it centred is **specificity/scope, not support-vs-no-support** — "topical overlap is not
  support" is the missing operative distinction, and "prefer ACCURATE" must be scoped to *genuinely
  empty/keyhole* windows, never to *present-but-adjacent* passages.
- **To make the judge run a check it skips, force a written artifact as a precondition (iter3, untested).**
  Prose "you must run these three checks" was skipped. iter3's attempt: ACCURATE now requires the judge
  to *write* the anchored specific-element + its passage in `nuance` before emitting ACCURATE. Whether a
  required-artifact precondition actually stops the skip (where mandatory-prose did not) is the iter4 test.

- **A specificity/scope *anchor* over-corrected into NS over-prediction (iter3→iter4). The pendulum
  swings on the strict side too, and NS is where it lands now.** iter3's bet was that anchoring on the
  claim's most-specific element would recover NS/IRRELEVANT/OVERSIMPLIFY. On iter4 the anchor instead
  made **NS the catch-all downgrade**: 10 pred / 8 fp, and 8 of 18 mistakes were correct labels routed
  wrongly to NS or CONTRADICT (3 true-ACCURATE→NS, 2 IRRELEVANT→NS, 2 ETIQUETTE→NS, 2 NS-gold→CONTRADICT).
  VAL 0.60→0.58. The discriminator "specificity, not support-vs-no-support" is *correct* but the
  routing "adjacent/broader → NOT_SUBSTANTIATE" is too eager — the judge treats any topical overlap as
  "partial support" and picks NS. **Two side-effects DID hold**: OVERSIMPLIFY came off F1=0 (0.286,
  now over-predicted), and the Gate-0 "excluding≠ETIQUETTE" edit drove ETIQUETTE fp to 0. **Lesson:
  the NS/IRRELEVANT and NS/CONTRADICT boundaries need a *decidable quotable test* (must quote the
  supported element / must quote the incompatible span), not a "downgrade signal" heuristic that the
  judge resolves toward NS by default.** Whether the decidable-quote form recentres it is the iter5 test.
- **CONTRADICT is mis-calibrated in BOTH directions on this task (iter4).** Same batch showed 2 false
  CONTRADICTs (silence / temporal-state-mismatch read as opposition) and 1 missed real CONTRADICT
  (mechanism-swap read as missing element). A single decidable test — "quote a source span logically
  incompatible with the claim" — is the natural fix for both, because it suppresses the un-quotable
  false positives and licenses the quotable true positive. Tightening a label's *definition* to a
  quotable artifact is symmetric; adding "elevated scrutiny" prose (already present) was not enough.

- **The decidable-quotable-test edits (iter4) HELD on VAL; the NS/IRRELEVANT one carried it, the
  CONTRADICT and aggregate ones were skipped (iter4→iter5).** VAL 0.58→**0.60** (+0.02, recovered
  iter3's regression); TRAIN 0.64→0.74 (floor 0.60), macro 0.301→**0.415**, no ACCURATE-collapse.
  The **NS-vs-IRRELEVANT "quote the supported element" test worked** (NS F1 0.235→0.600, IRRELEVANT
  off 0). The **CONTRADICT "quote the incompatible span" test did NOT fire** (F1 still 0, both
  directions still wrong; 140-50's own nuance quoted the rubric's exact worked span and still emitted
  NS), and the **aggregate-exclusion edit did NOT fire** (1660-16 still NS). Confirms the standing
  rule sharper: **a quotable-artifact test lands when it *refines the label the judge was already
  reaching for* (NS→IRRELEVANT split), and is skipped when it asks the judge to leave NS for a
  higher-scrutiny label it does not spontaneously consider (CONTRADICT), or to drop a proposition it
  is inclined to grade (aggregate).** More prose on the skipped ones is not the lever.
- **NS has been the over-predicted catch-all for THREE consecutive iterations (3,4,5), and the
  through-line is one step: the judge downgrades on any element it cannot find, without first asking
  whether the *anchor* (central proposition) is supported and whether the missing element is merely
  *not retrieved*.** iter5 found this drives BOTH the NS over-prediction (over-strict on a supported
  anchor: 1660-16, 1360-20) AND the over-lenient ACCURATE misses in reverse (anchor unsupported but
  ruled ACCURATE on plausibility: 737-47, 982-93). "Window-silence is not paper-absence" is failure
  mode 2 and is in-reach on retrieval; the prior rubric only fired it for *empty* windows, never for a
  *partial* window missing one element. iter5's fix: an **anchor-first Gate 2** — quote the anchor
  first; if supported, a secondary element absent from the window is *not retrieved, not refuted* (no
  NS); if unsupported, route opposition→CONTRADICT / different-subject→IRRELEVANT / partial→NS. This
  is the first edit aimed at recentring the pendulum from *both* sides at once. Whether it holds without
  collapsing toward ACCURATE is the iter6 test.

## Pending

- **Iter 4 edits (untested until iter 5):** attacked the over-strictness pendulum (NS/CONTRADICT
  over-prediction, 8+ of 18 mistakes routed wrongly to NS). Three edits, all making an *existing*
  boundary **decidable by a quotable-artifact test** rather than adding a rule (execution fixes):
  (1) **CONTRADICT requires quoting a source span logically incompatible with the claim** — silence /
  a different-or-later state ("in trials"≠"approved") / failure-to-establish → NOT_SUBSTANTIATE;
  symmetric, also licenses a real under-fired CONTRADICT (mechanism-swap). (2) **NS-vs-IRRELEVANT is
  one test: can you quote a passage supporting a *specific element* (not the topic/field)?** yes→NS
  (name+quote it), no→IRRELEVANT. (3) aggregate-exclusion extended to literature-scope synthesis
  ("overwhelming majority of studies"). Predicted CONTRADICT fp→0, IRRELEVANT off 0, NS fp↓, VAL
  0.58→~0.60–0.62. **Risk: over-correcting toward IRRELEVANT / unrecovered NS.** See findings/iter-4.md.

- **Iter 3 edits → tested iter 4: the central bet FAILED, two side-effects held.** (see the new
  Confirmed bullet). Predicted 0.68→0.70–0.74; got TRAIN 0.64, **VAL 0.60→0.58 (−0.02)**.

- **Iter 3 edits (untested until iter 4):** attacked the new dominant error (silent ACCURATE, 5/16).
  (1) **Operationalized the ACCURATE gate as a mandatory specificity/scope *anchor*** (dispatch Gate
  1/2 + mirrored in rubric ACCURATE test): name the claim's most-specific element, find the passage
  asserting *that element*, and treat topical-overlap-without-the-element as a downgrade signal
  (broader→NS, different-subject→IRRELEVANT, scoped-finding-generalized→OVERSIMPLIFY); ACCURATE now
  requires *writing* the anchored element+passage in `nuance` first. (2) Gate 0: "excluding a
  sibling/aggregate ≠ ETIQUETTE — judge the remainder" (fixes the 1729-21 ETIQUETTE fp). Predicted
  0.68→~0.70–0.74, ACCURATE precision ↑, OVERSIMPLIFY leaving 0, ETIQUETTE fp→0. **Primary risk: the
  pendulum back to iter1 over-strictness — check ACCURATE recall (now 30/31) + VAL together.** See
  findings/iter-3.md.

## Resolved baselines (kept for provenance)

- **Iter 1 baseline (program-v0): BELOW the do-nothing floor.** TRAIN accuracy 0.460 vs 0.62 floor —
  systematic **over-strictness** (NS 17 vs 7 gold, OVERSIMPLIFY 10 vs 3, ACCURATE 20 vs 31, never
  IRRELEVANT/CONTRADICT/INDIRECT_NOT_REVIEW; 14/27 mistakes were gold-ACCURATE downgrades). Confirmed
  known failure mode 1 (too strict), not mode 4 (INDIRECT blind spot).
- **Iter 1 edits → tested iter 2: HELD.** Enriched terse rubric with boundary tests; accuracy
  0.46→0.60 TRAIN, VAL(v1)=0.56, macro up, invalid_label→0.
- **Iter 2 edits → tested iter 3: mixed but net positive.** Mandatory Gate 0–3 + IRRELEVANT-last-resort
  + one-way tolerance. Accuracy 0.60→0.68 TRAIN, **VAL 0.56→0.60 (+0.04, above floor)**, macro
  0.206→0.32; IRRELEVANT precision + MISQUOTE held; **OVERSIMPLIFY and ETIQUETTE recovery predictions
  FAILED**, and the gate introduced over-leniency toward ACCURATE. See the two Confirmed bullets above.

## Reverted

*(Nothing yet. Record what was undone and why — ⚠ the loop is forward-only, so "reverted" means
you edited it back yourself, not that the harness rolled it back.)*

## Notes on the instrument itself

⚠ **Nothing checks this file.** It was written by your predecessors, and three of its instrument
claims turned out to be false and propagated across five iterations. **Date every entry you add**, and
before relying on any claim here about where a file is or what the harness wrote, verify it — one
`ls` is cheaper than an iteration. If an inherited claim is false, delete it and say you deleted it,
as the dated entries below do.

- **(2026-09-09) DELETED — "no release files are written, this is now the norm for this run" was
  FALSE, and it cost all five iterations.** The releases *were* written, every iteration. They live at
  `iter/<n>/release_{train,val}.json` relative to **the loop clone — your own working directory**. The
  five sessions looked in the persisted run tree under `~/.paper-trail/runs/<run-id>/`, which never
  holds them, found nothing, and each concluded the release was missing. Every one of them then
  reconstructed metrics by hand from the mistake corpus, and passed the false claim forward. Verified
  2026-09-09: `engine/loop.py` writes both files before the agent starts, the dispatcher passes the
  `loop_ops` handle that enables the write on every real run, and a negative-controlled regression
  test guards that seam. **Do not restore this note.** If you think the release is missing, run the
  verify-absence check at the top of `experiments/sarol-2024/optimizer/context/release-format.md` first.
- **(2026-09-09) The reconstruction recipe is still worth knowing, but it is a fallback, not the
  routine.** Pred for all 50 is at `manifest.claims[*].validation.overall_verdict`; correct claims
  have gold=pred; `do_nothing_floor` is the gold-ACCURATE fraction. The manifest's `canary` record
  (`.canary.status == "ok"`) is where the round-trip check lives.
- **Empty BM25 windows are real on retrieval** (~3/50 got zero passages) and they used to double as
  `invalid_output` misses: the judge emitted a sub-claim with no `evidence` field →
  `MISSING_FIELD:sub_claims[*].evidence` → whole file rejected → scored a miss regardless of verdict.
  The exit validator (frozen) requires the field present; `"evidence": []` satisfies it. The fix
  belongs in the adjudicator dispatch prompt, not the validator.
- **The judge reads TWO editable operative documents on retrieval**, and they can contradict:
  `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` (its literal prompt, including an inline one-line class list) *and*
  `experiments/sarol-2024/specs/verdict_schema_sarol.md` (the rubric it loads). A rubric edit can be silently overridden by a stale
  inline description in the dispatch. Keep them in step — iter 1 had to fix the OVERSIMPLIFY/NS
  wording in both. **(2026-09-09) This lesson held and was acted on:** the paper-verbatim reset
  rewrote the class definitions in *both* files together, because resetting only the rubric would have
  left the judge reading the corrected scheme and the old divergent gloss in the same session. The
  rubric is now the single operative source; if the two ever differ again, that is a defect to report,
  not a change to keep.

## Iteration log

*(One entry per iteration: what you predicted, what happened, and what you concluded. Append;
never rewrite an earlier entry.)*

- **Iter 5 (frozen program = program-v4).** TRAIN i5 = **0.74** (floor 0.60, gap +0.14); VAL(program-v4)
  = **0.60**, up from program-v3's 0.58 — iter4's edits held, recovering iter3's regression. macro
  0.301→0.415, no ACCURATE-collapse. 13 mistakes; blame execution 6 / rubric 2 / attribution 2 /
  retrieval 2 / unclear 1. Dominant mode (4, ~31%): window-silence on a *secondary* element read as
  paper-absence, driving NS over-prediction (and, in reverse, over-lenient ACCURATE). One joint edit:
  **anchor-first Gate 2** (quote the anchor first; supported anchor + secondary gap = not-retrieved, no
  NS; unsupported anchor → opposition/different-subject/partial split). Deferred ETIQUETTE (Mode 2, 3
  gold) and CONTRADICT (Mode 3, execution skip). Predicted NS fp↓, OVERSIMPLIFY↑, ACCURATE precision+
  recall both↑ (offset, no collapse), VAL 0.60→0.60–0.64. Risk: over-correction toward ACCURATE. To
  check iter6. Instrument: canary ok. *(2026-09-09: this entry's "no release files (norm)" clause was deleted — it was false; see the instrument note above.)*
- **Iter 4 (frozen program = program-v3).** TRAIN i4 = 0.64 (floor 0.62, gap +0.02); VAL(program-v3)
  = 0.58, down from program-v2's 0.60. iter3's specificity-anchor central bet failed (NS became the
  catch-all downgrade, 8 fp), two side-effects held (OVERSIMPLIFY off 0; ETIQUETTE fp→0). 18 mistakes,
  blame execution 12 / attribution 3 / gold 2 / retrieval 1 — dominant mode is over-strict downgrade
  into NS/CONTRADICT (the pendulum). Made 3 edits converting existing boundaries to decidable
  quotable-artifact tests: CONTRADICT (quote incompatible span), NS-vs-IRRELEVANT (quote supported
  element), aggregate-exclusion (literature-scope synthesis). Predicted TRAIN→~0.68–0.72,
  VAL→~0.60–0.62, CONTRADICT+IRRELEVANT off F1=0. Instrument: canary ok. *(2026-09-09: this entry's
  "no release files (norm for this run)" clause was deleted — it was false; see the instrument note
  above.)* To check iter5.
