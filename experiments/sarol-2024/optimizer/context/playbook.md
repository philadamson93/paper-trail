# Playbook — how one optimization iteration runs

Reference doc for the optimizer agent. This file carries the **engine's** view of an iteration and
the standing decisions behind it. The other context docs carry the rest:

- `/workspace/ro/in/context/failure-mode-discovery.md` — how you find failure modes,
  and what you point subagents at.
- `/workspace/ro/in/context/task-and-scoring.md` — what counts as better.
- `/workspace/ro/in/context/release-format.md` — what you are handed each iteration.
- `/workspace/ro/in/context/edit-surface.md` — what you may change, and what holds it.

**Every path in this document is relative to your working directory, which is the repository root.**

Where this file and your standing instructions (the start of your prompt) cover the
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
   scalar and its breakdown, nothing else. See `/workspace/ro/in/context/release-format.md`.
3. **You work the iteration.** Check the last prediction, establish the numbers, draw and fan out,
   cluster, edit, predict — the six steps in your standing instructions. One pass, then you exit.
4. **The harness commits and tags** the result as a new version. You never commit.
5. **The harness re-runs the frozen version against VAL** to confirm it still works, then the next
   iteration begins.

Note what step 4 means for step 3: the harness freezes only what the manifest lists. See
`/workspace/ro/in/context/edit-surface.md` before you create or edit a file outside it.

## What you may and may not touch

Moved to `/workspace/ro/in/context/edit-surface.md`, which is now the single place
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
  `/workspace/rw/out/meta-learnings.md` that you intend to.
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

## TRAIN and VAL change on a schedule

Both are drawn by the engine each iteration, on a schedule fixed before the run starts (the
instructions' *How TRAIN and VAL change during a run* has the rules).

- **VAL grows, and only grows.** Each VAL holds the previous one plus new claims, so the VAL curve is a
  comparison of programs *within* one VAL size. A score on a bigger VAL is a new measurement, not a
  step on the old curve. When VAL grows the engine re-grades the best version on it before your session,
  so the best-so-far is always measured on the current VAL; `run_summary.json` records each score with
  its VAL batch id (`<run>-val-n<k>`).
- **TRAIN is not the same claims each iteration.** Claims answered right twice running retire and new
  ones are drawn, so TRAIN leans towards what the program still gets wrong. Two TRAIN numbers from
  different iterations are therefore **not** a paired comparison, and a TRAIN accuracy that holds flat
  while claims retire means the program is now getting harder claims right.
- **Absence is not proof of a fix.** A failure can disappear from TRAIN because its claims retired (you
  fixed them) or because none was drawn. `/workspace/ro/feedback/iter/<n>/train_schedule.json` says which:
  it lists what was drawn, spot-checked and retired. Confirm a fix by predicted per-class movement.
- **Overfitting is less likely than with a fixed batch, not impossible.** Retired claims are only
  re-checked if the run asks for a spot-check, so a fix can quietly regress on claims that left the
  batch. VAL is the check on that.

## Continuity

Each iteration runs in a fresh session with no recollection of the last one, deliberately — a
retrospective evaluation of version N has to be blind to everything learned after N. Two records
carry you forward, and they are not interchangeable.

**Which record takes what is defined in one place: the *"The three record surfaces, and what goes in which"*
section of your standing instructions (the start of your prompt).** That is the file
injected into every iteration, so it is the copy you are guaranteed to have read. Do not look for a
second answer here, and do not add one: parallel copies of a rule drift apart, and then the judge
is reading two of them.
