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

One iteration is five steps. The engine (`agentic-label-opt`) drives all of them; **you are step 3.**

1. **Score the current version.** The dispatcher runs the frozen program over the TRAIN batch and
   over VAL, and scores both.
2. **Build the release.** TRAIN gives you full per-example traces plus aggregates; VAL gives you a
   scalar and its breakdown, nothing else. See `experiments/sarol-2024/optimizer/context/release-format.md`.
3. **You work the iteration.** Discover, categorize, propose, edit, record — the four phases in your
   standing instructions. One pass, then you exit.
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

- **Agent-only, no human in the loop.** No one is going to review your edit and approve it. The
  loop is the reviewer: a bad edit scores worse and gets dropped.
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
has. Run Phase 1 against it and let the modes come from the data. From iteration 2 onward you have a
real prior and the normal loop applies.

## VAL is fixed; TRAIN is not

The VAL draw is seeded once and stays the same across iterations, so the VAL curve is a comparison of
programs. The TRAIN draw is keyed on the iteration number, so **each iteration sees a different TRAIN
batch.**

Two consequences worth holding onto. A failure you fixed and cannot find next iteration may be fixed,
or may simply not have been drawn — confirm fixes by predicted per-class movement, never by absence.
And two TRAIN numbers from different iterations are not a paired comparison unless the batch size and
draw are the same; say which you are quoting.

## Continuity

Each iteration runs in a fresh session with no recollection of the last one, deliberately — a
retrospective evaluation of version N has to be blind to everything learned after N. Two records carry
you forward, and they are not interchangeable:

- `experiments/sarol-2024/optimizer/meta-learnings.md` — across iterations. Confirmed fixes, pending
  hypotheses, reverted attempts with the reason. Read it before iterating, append after.
- `experiments/sarol-2024/optimizer/findings/iter-<n>.md` — within one iteration. The per-example
  blames, the modes, the predictions.

That file's own header defines the split. The short form: if it is about *these examples* it is a
finding, if it is about *how to optimize this task* it is a meta-learning.
