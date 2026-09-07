# Release format — what you are handed each iteration

Two files land per iteration, written by the engine before your session starts:
`iter/<n>/release_train.json` and `iter/<n>/release_val.json`, where `<n>` is the iteration number
your turn prompt gives you. **Every path in this document is relative to your working directory,
which is the repository root.** They are deliberately not the same
shape, and the difference is the whole leakage design.

## TRAIN release — Tier 1, fully open

```json
{
  "schema_version": "0.2.0",
  "phase": "train",
  "iter": 3,
  "produced_at_utc": "2026-09-01T18:04:11+00:00",
  "optimizer_isolation_hash": "sarol-2024",
  "corpus": {
    "ref": "<path to mistakes/<batch_id>.json -- the per-claim corpus itself>",
    "counts": { "invalid_label": 0 },
    "profile": "retrieval",
    "retrieval_k": 20,
    "metrics": {
      "primary_metric_name": "sarol_accuracy_9class",
      "primary_metric": 0.63,
      "breakdown": {
        "do_nothing_floor": 0.595,
        "n_correct_9way": 32,
        "macro_f1_renormalised": 0.28,
        "macro_f1_3way": 0.41,
        "objective_class_set": ["ACCURATE","OVERSIMPLIFY","NOT_SUBSTANTIATE","CONTRADICT",
                               "MISQUOTE","INDIRECT","INDIRECT_NOT_REVIEW","ETIQUETTE",
                               "IRRELEVANT"],
        "objective_classes_present": ["ACCURATE","NOT_SUBSTANTIATE","CONTRADICT","INDIRECT"],
        "n_objective_classes_present": 4,
        "micro_f1": 0.76,
        "per_class_f1": { "ACCURATE": 0.86, "NOT_ACCURATE": 0.37, "IRRELEVANT": 0.0 },
        "confusion_matrix": { "ACCURATE": {...}, "NOT_ACCURATE": {...}, "IRRELEVANT": {...} },
        "macro_f1_9way": 0.21,
        "per_class_f1_9way": { "ACCURATE": 0.86, "OVERSIMPLIFY": 0.31, "...": "..." },
        "support_9way": { "ACCURATE": 39, "OVERSIMPLIFY": 7, "MISQUOTE": 1, "...": "..." },
        "n_classes_present_9way": 5,
        "error_class_counts": { "invalid_label": 0 },
        "n_total": 50, "n_scored": 50, "n_invalid": 0,
        "requested_count": 50, "n_unresolved": 0,
        "scored": true, "split": "train",
        "profile": "retrieval", "retrieval_k": 20,
        "mistakes_ref": "<same path as corpus.ref>"
      }
    },
    "frontier": { "best_tag": "...", "best_metric_value": 0.44,
                  "current_tag": "...", "current_metric_value": 0.41 },
    "budget":   { "spent_usd": 212.40, "spent_input": ..., "spent_output": ..., ... }
  }
}
```

**Reading the objective.** `primary_metric` is **accuracy over the nine labels** — the fraction of
claims whose predicted label equals the gold label. Nothing collapsed, nothing renormalised, so it
needs no companion field to be comparable between batches.

**Read it against `do_nothing_floor`, which sits beside it.** That is what a program scores by
answering `ACCURATE` every time, computed from this batch's own gold (≈0.595 on full dev). An
accuracy of 0.63 is 3.5 points of work, not 63% of a job done.

`macro_f1_renormalised` is the **diagnostic**, not the objective: macro-F1 over
`objective_class_set` renormalised over the members present. Read it to check *how* an accuracy gain
was bought — collapsing toward `ACCURATE` raises accuracy and craters macro, and that is the one
degenerate strategy accuracy admits. `n_objective_classes_present` is part of **that** number, not
of the objective: a macro over 4 classes is not comparable to one over 6. On TRAIN you also get
`objective_classes_present`, so you can see *which* class a small batch is missing; on VAL you get
only the count, because the presence vector is VAL gold structure.

**Reading the 9-way fields.** `macro_f1_9way` always divides by nine, so a batch whose gold covers only five
classes caps at 5/9 = 0.556 however perfect the predictions. **Always read `support_9way` and
`n_classes_present_9way` before reading the F1s** — a low 9-way macro on a small batch usually means
the batch was small, not that the program got worse. That fixed denominator is why `macro_f1_9way`
is a descriptive breakdown and not a frontier; the frontier is **accuracy**, and `macro_f1_3way`
exists for comparability with the published baselines. The full calibration table — every axis, one
pool, one do-nothing program — is in
`experiments/sarol-2024/optimizer/context/task-and-scoring.md`; do not carry a second copy of those
numbers in your head from here.

`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` is how that corpus gets read —
the draw discipline, the blame record, and what to hand a subagent. This section is the shape; that
document is the procedure.

**`corpus.ref` points at the per-claim mistake corpus itself** — `mistakes/<batch_id>.json` under
the run's TRAIN output root. Not at the run manifest: the manifest carries dispatch bookkeeping
(exit codes, costs, timings, the canary record) and **no gold and no structured reasoning**, so
following it told you nothing about *why* you were wrong. Read the corpus; it is the point.

*(The manifest does hold one thing worth knowing about: a `trace_ref` per claim and stage, pointing
at the judge's raw transcript. That is a pointer to unstructured text, not reasoning the manifest
itself carries — and since 2026-09-07 the same path is copied onto every mistake-corpus row, so you
never need to open the manifest to reach it.)*

Its shape is an object wrapping the per-claim list:

```json
{
  "batch_id": "run_x-train", "split": "train",
  "n_scored": 50, "n_correct": 47, "n_mistakes": 3,
  "claims": [
    { "claim_id": "C042", "citekey": "ref_a1b2c3",
      "claim_text": "<the citing sentence>",
      "evidence_snippets": ["<each passage the judge was given>"],
      "pred_label": "ACCURATE",  "gold_label": "CONTRADICT",
      "pred_3way": "ACCURATE",   "gold_3way": "NOT_ACCURATE",
      "adjudicator_reasoning": {
        "sub_claim_verdicts": ["ACCURATE"], "nuance": ["..."],
        "overall_flag": null, "remediation": { "category": "...", "suggested_edit": "..." } },

      "claim_type": { "type": "PARAPHRASED", "confidence": "medium" },
      "rubric_variant": "sarol_2024_9class",
      "sub_claims": [
        { "sub_claim_id": "C042.a", "text": "<the proposition actually judged>",
          "verdict": "ACCURATE", "nuance": "...",
          "evidence": [ { "snippet": "...", "locator": "pdfs/ref_a1b2c3/content.txt#L22",
                          "section": "content", "line": 22 } ] }
      ] }
  ]
}
```

### `sub_claims` — which evidence drove which sub-verdict

`evidence_snippets` above is the **union** of every sub-claim's evidence, and
`adjudicator_reasoning.sub_claim_verdicts` is a bare list of labels with no text attached. Between
them they can tell you a claim was wrong and which passages were in play, but not *which passage
drove the sub-verdict that went wrong* — which is the question you have to answer to fix a rubric.

`sub_claims` closes that: each entry carries the proposition the judge actually evaluated, the
verdict it gave that proposition, and the evidence **mapped to it**, with a `locator`
(`pdfs/<citekey>/content.txt#L22`) so you can see whether the retrieved passages cluster in one
part of the paper or are scattered across it. Under `retrieval` that distinction matters more than
it sounds: the judge sees a BM25 top-*k* subset and is **not told that it is a subset**, so a
sub-claim marked unsupported may simply have had its evidence retrieved away. Only the per-sub-claim
mapping separates a rubric defect from a retrieval one.

⚠ **`sub_claims` is currently almost always length 1.** In the 2026-09-02 run every one of 50
claims produced exactly one sub-claim — even the five where the judge's own `nuance` named two
propositions ("both halves of the citing sentence", "the morbidity conjunct"). The claims
decompose; the judge is not decomposing them. Two consequences: the worst-wins rollup is currently
the identity function, so reordering the strictness ladder cannot move anything; and **making the
judge decompose is an available target with direct evidence behind it.**

`claim_type` is the judge's own read of the claim (`PARAPHRASED`, `DIRECT`, …) and `rubric_variant`
names the rubric version that produced the verdict — both are plausible upstream causes of a wrong
label, and both were previously invisible to you.

### `trace_ref` — the judge's full session, if you want it

**Every mistake-corpus row carries `trace_ref`**: a path to a copy of the judge's own session
transcript for that claim (`<run>/traces/<claim_id>-<stage>.jsonl`). It is `null` when the
transcript could not be captured. The run manifest carries the same path per claim and per stage,
alongside the `model` that produced it and the `session_id` — but you do not need the manifest for
this, and a blame subagent, which is handed the corpus and nothing else, could not reach it there.

**This is an optional read and nothing pushes it into your context.** Open one when the structured
fields above leave you genuinely unsure *why* the judge concluded what it did — it is the full
reasoning, not a summary. It is also large: opening many of them will exhaust your session budget
long before it teaches you anything, and `## Output discipline` in your standing instructions still
applies. One or two, on the claims you actually care about, is the intended use.

**Read `n_correct` before `n_mistakes`.** Three mistakes out of ten is a disaster; three out of
three hundred is close to ceiling, and the same list of three looks identical either way. The
counts are in the file precisely so you never have to reason about the numerator alone.

`claims` holds **only the claims that were wrong** — correct ones are summarised by `n_correct`, not
listed. That is a deliberate boundary: your job is to fix mistakes without breaking what already
works, and `n_correct` is how you notice if you did.

⚠ **What is NOT here, and why.** There is no verifier bounce history: under the `retrieval` profile
no verifier runs at all (see `experiments/sarol-2024/optimizer/context/playbook.md`). `evidence_snippets` under that profile are the BM25
top-*k* passages, not an extractor's chosen quotes. And TRAIN is Tier 1 — gold labels are open to
you here, deliberately, because that is the mechanism by which you learn. Raw benchmark provenance
(row ids, paper buckets, which split a claim came from) is withheld even so; you have no use for it.

## VAL release — Tier 2, scalar only

```json
{
  "schema_version": "0.2.0",
  "phase": "val",
  "iter": 3,
  "produced_at_utc": "2026-09-01T18:19:52+00:00",
  "optimizer_isolation_hash": "sarol-2024",
  "metrics": {
    "primary_metric": { "name": "sarol_accuracy_9class", "value": 0.61,
                        "higher_is_better": true },
    "breakdown": { "scored": true, "n_total": 50, "n_invalid": 0,
                   "requested_count": 50, "split": "val",
                   "profile": "retrieval", "retrieval_k": 20,
                   "model": "claude-haiku-4-5",
                   "do_nothing_floor": 0.60,
                   "n_objective_classes_present": 6,
                   "objective_class_set": ["ACCURATE","OVERSIMPLIFY","NOT_SUBSTANTIATE",
                                           "CONTRADICT","MISQUOTE","INDIRECT",
                                           "INDIRECT_NOT_REVIEW","ETIQUETTE","IRRELEVANT"] }
  }
}
```

That is the entire VAL surface. **No per-class F1, no confusion matrix, no error-class counts, no
per-example anything.** The scalar plus enough metadata to distinguish a real score from a partial
batch.

`profile`, `retrieval_k` and `model` are **run identity**, not signal: they say which pipeline, how
much evidence, and which judge produced the number. An accuracy quoted without them is not a
result, and none of the three tells you anything about which claims went which way. The judge model
is configurable (`--model`) and defaults to a cheap one, since it runs once per claim and is where
essentially all of a run's cost is — so two numbers from different runs are only comparable when
this field matches.

`n_invalid` is the one borderline field, and it is included deliberately: it is a bare count of
malformed predictions, never a distribution over classes, so it tells you *that* output was
unparseable and nothing about *which* claims or which gold classes. Without it a VAL run could be
half-garbage and still report `scored: true`.

This is not an oversight to be worked around. Per-class structure on the held-out split is exactly
the signal an optimizer overfits to, and the divergence between the TRAIN curve and the VAL curve
is the experiment's stopping rule — a rule that stops meaning anything if VAL's error structure is
visible while you are editing. The reduction is enforced in `adapter.SarolReleaseBuilder`, and
`adapter.py --selftest` runs the same scored batch through both tiers to prove the difference is
the boundary rather than a difference in the underlying numbers.

If you find yourself wanting VAL's per-class breakdown: that want is the mechanism working. Use
TRAIN's.

## Reading `scored`

`scored: false` means **the number in `primary_metric` is not a result.** It is 0.0 as a
placeholder, with `reason` saying why — a coverage shortfall, an unresolvable claim, a non-finite
metric, or a run that timed out or errored. Do not treat it as a regression and do not react to it
with a prompt edit; it is an infrastructure signal, not a program signal.

The distinction matters more than it would if the loop could recover. A failed batch scored as a
real 0.0 would poison the frontier — and **the loop is forward-only, so nothing would undo it.**
There is no step-back and no automatic revert; version *n+1* is built on version *n* whatever
version *n* scored (see the standing decisions in
`experiments/sarol-2024/optimizer/context/playbook.md`). A placeholder 0.0 mistaken for a result is
therefore not a bad iteration you recover from next time, it is a wrong baseline you keep building
on.

## `frontier` and `budget`

- **`frontier`** carries best-so-far versus current, so you can tell "worse than my last edit" from
  "worse than the best we have ever had". Only the scalar, on both sides.
- **`budget`** is the engine's own accounting of the *optimizer session's* token spend. It does not
  include the Runner's cost, which is where nearly all real spend lives — that is bounded
  separately and consumer-side by `dispatcher.py`. If a run stops for budget reasons it will say so
  explicitly; you will not see it coming in this field.

## Checking your own predictions

There is **no `followups` key and nothing scores your predictions back to you.** An earlier version
of this document promised one; no code ever emitted it, so the promise is removed rather than left
standing.

What you do instead, and where: **write the prediction into
`experiments/sarol-2024/optimizer/findings/iter-<n>.md`** when you make the edit — which verdict
classes should move, in which direction, per edit. **Then, as the FIRST thing you do next
iteration, open `iter-<n-1>.md` and check it** against `per_class_f1_9way` in the new TRAIN release.
(`per_class_f1` has only the three collapsed buckets and cannot answer a nine-class prediction.)

Both halves are on you, and the second one is the half that gets skipped. Writing a prediction
nobody reads back is bookkeeping; reading it back is what turns an iteration into a test rather than
a guess. The automation is what is missing, not the discipline.

## When the release is not there at all

**All three iterations of the 2026-09-02 run landed here**, and each reconstructed the same recipe
from scratch, so it is written down now. If `iter/<n>/release_train.json` does not exist:

1. **Do not treat it as a zero, a regression, or a signal about the program.** A release that was
   never written says nothing about how the program scored. It is the same class of event as
   `scored: false`.
2. **Look for the run manifest instead.** The dispatcher writes one per Runner call under the run's
   TRAIN output root; it carries `claims[]` with per-claim `status`, `staging_dir`, `stages` and the
   canary record. That tells you whether the batch ran at all, and where it stopped if not.
3. **Look for the mistake corpus directly**, at `mistakes/<batch_id>.json` under the same root. It
   is written by the scorer, independently of the release, so it frequently exists when the release
   does not — and it is the file you actually wanted.
4. **If neither exists, the batch did not run.** Report that and stop. Do not edit prompts in
   response to an infrastructure failure; you would be optimizing against noise, and the loop is
   forward-only, so the edit stays.
5. **Say so in `experiments/sarol-2024/optimizer/meta-learnings.md`.** An iteration that produced no
   number is a fact the next iteration needs, and it is invisible in the frontier.

The underlying cause of the 2026-09-02 instances has since been fixed — `run_optimization` was
calling `run_loop` without `loop_ops`, so the release files were never written. It is recorded here
because a missing release will happen again for some other reason, and the recipe is the same.

## Schema stability

`schema_version` is `0.2.0` — bumped from `0.1.0` when the `profile` key entered both payloads,
because a release that cannot say which rung produced its number is not comparable to one that can.
The engine validates that a train-phase call returns a train payload and a val-phase call returns a
val payload, and stops the run if they are crossed — so a change to these shapes is a real change,
not a cosmetic one.
