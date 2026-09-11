# Playbook — how one optimization iteration runs

Reference doc for the optimizer agent. This file carries the **engine's** view of an iteration and
the standing decisions behind it. The other context docs carry the rest:

- `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` — how you find failure modes,
  and what you point subagents at.
- `experiments/sarol-2024/optimizer/context/task-and-scoring.md` — what counts as better.
- `experiments/sarol-2024/optimizer/context/release-format.md` — what you are handed each iteration.
- `experiments/sarol-2024/optimizer/context/edit-surface.md` — what you may change, and what holds it.

**Every path in this document is relative to your working directory, which is the repository root.**

Where this file and `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md` cover the
same ground, the standing instructions are authoritative and this file points rather than restates.

The decisions below were settled in April 2026 and are not open. They are stated here so you do not
spend an iteration re-deriving them.

## The shape of an iteration, from the engine's side

One iteration is five steps **on the engine's side**. The engine (`agentic-label-opt`) drives all of
them; **you are its step 3**, and your own six steps all happen inside it. (Neither of these is a
"phase" — that word is reserved for a rung of the evidence ladder. See the standing instructions.)

1. **Score the current version.** The dispatcher runs the frozen program over the TRAIN batch and
   over VAL, and scores both.
2. **Build the release.** TRAIN gives you full per-example traces plus aggregates; VAL gives you a
   scalar and its breakdown, nothing else. See `experiments/sarol-2024/optimizer/context/release-format.md`.
3. **You work the iteration.** Check the last prediction, establish the numbers, draw and fan out,
   cluster, edit, predict — the six steps in your standing instructions. One pass, then you exit.
4. **The harness commits and tags** the result as a new version. You never commit.
5. **The harness re-runs the frozen version against VAL** to confirm it still works, then the next
   iteration begins.

Note what step 4 means for step 3: the harness freezes only what the manifest lists. See
`experiments/sarol-2024/optimizer/context/edit-surface.md` before you create or edit a file outside it.

## What you may and may not touch

Moved to `experiments/sarol-2024/optimizer/context/edit-surface.md`, which is now the single place
that answers it — the editable set,
the frozen contract files, the permanently-locked scorer and held-out gold, the profile that decides
which stages run, and the per-claim budget that follows from it.

Kept here only because it is a decision rather than a rule: the narrowing under `retrieval` is not
arbitrary. On that rung there is no extractor session at all, so editing an extractor prompt would
change nothing measurable while still producing a new version, a new tag and a wasted iteration. The
experiment on that rung is "how good can the judge get at a *fixed* evidence budget", so the judge and
its clarifications layer are the whole surface.

## Standing decisions you do not need to relitigate

- **Agent-only, no human in the loop.** No one is going to review your edit and approve it.
- **The loop is FORWARD-ONLY. A regressing edit is not reverted — it becomes the next baseline.**
  This is the one standing decision most likely to catch you out, because the natural assumption is
  the opposite. There is no step-back: this consumer hard-codes `attempting_step_back` to `False`,
  so nothing compares your new version against the old one and rolls back the loser. Version *n+1*
  is built on version *n* whatever version *n* scored.

  Two things follow. **Declaring a step-back does nothing** — saying "the score regressed but I
  believe the direction is right" is a note to your future self, not a signal to the engine; it
  neither protects the edit nor triggers a revert. And **an edit you doubt is a liability you are
  handing forward**, not a bet the harness will settle. If you think an edit was wrong, the way to
  undo it is to edit it back yourself, next iteration, having written down in
  `experiments/sarol-2024/optimizer/meta-learnings.md` that you intend to.
- **The dispatcher is a Python script, not an agent.** All orchestrator-runtime decisions —
  verifier sampling, retry, bounce, schema validation — are static code, not runtime judgement. This
  is what makes a retrospective re-run of version N reproducible, and it is the same property that
  makes an edit outside the manifest worthless.
- **Invocation is uniform across TRAIN and VAL.** The same subagent, the same headless
  invocation; only the dispatcher's routing of the output differs. TRAIN's output comes back to you in
  full, VAL's is reduced to a scalar before you see it. Do not infer anything from a difference in how
  a split was run, because there isn't one.
- **The topology is fixed for v0.** Extractor → adjudicator → verifier. You edit prompt content, not
  pipeline shape.
- **The output vocabulary is fixed; the guidance is not.** You may not add, remove or rename a label.
  An out-of-enum label is not a crash — it is charged as a miss and counted in `error_class_counts`,
  so an edit that wanders outside the vocabulary simply scores worse.

## Warm start: iteration 1 establishes the baseline, it does not characterize it

This matters and is easy to get wrong. **`program-v0` has no measured score under the current
configuration.** There is no published number for paper-trail on this benchmark, and the two
comparison points that do exist — MultiVerS at 0.52 macro-F1, GPT-4 4-shot at 0.45 — are other
systems on a different axis, not earlier versions of this one.

So iteration 1's job is to *produce* the first real number, not to react to one. Do not open by
proposing fixes to a failure mode you have not seen; the first release is the first evidence anyone
has. Run the discovery fan-out (step 3) against it and let the modes come from the data. Step 1 has
nothing to check on iteration 1; say so and move on. From iteration 2 onward you have a
real prior and the normal loop applies.

## VAL is fixed — and so, in practice, is TRAIN

The VAL draw is seeded once and stays the same across iterations, so the VAL curve is a comparison of
programs.

⚠ **TRAIN has been identical too — this file used to claim otherwise, and the claim was false.**
Measured over the 2026-09-09 run's `train/draw_history.json`: all five iterations drew the **same 50
claims**, pairwise Jaccard **1.000** on every pair. The draw is keyed on the iteration number, so a
*different* roster is possible in principle, but do not assume it happened — **read
`train/draw_history.json` for this run and check.**

The consequences flip with the fact, so hold the right ones:

- **The real hazard is overfitting a fixed 50, not incomparability.** When the roster does not
  change, every iteration is tuning against the same examples, and TRAIN gains stop generalizing long
  before they stop appearing. Weigh VAL accordingly.
- **On an identical roster, two TRAIN numbers ARE a paired comparison** — same claims, different
  program — which makes them more informative than the old text allowed, not less.
- **Absence is still not proof of a fix**, but for a different reason: on a fixed roster a failure
  that has disappeared has genuinely been fixed *on these examples*, which is weaker evidence than it
  looks. Confirm by predicted per-class movement.
- If `draw_history.json` shows the roster *did* change between the iterations you are comparing, the
  old caution applies again: say which draw you are quoting.

## Continuity

Each iteration runs in a fresh session with no recollection of the last one, deliberately — a
retrospective evaluation of version N has to be blind to everything learned after N. Two records
carry you forward, and they are not interchangeable.

**Which record takes what is defined in one place: the *"The three record surfaces, and what goes in which"*
section of `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`.** That is the file
injected into every iteration, so it is the copy you are guaranteed to have read. Do not look for a
second answer here, and do not add one: parallel copies of a rule drift apart, and then the judge
is reading two of them.
