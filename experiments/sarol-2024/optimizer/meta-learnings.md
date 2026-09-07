# Meta-learnings — what iterations have established

Continuity across optimization sessions. Each iteration runs in a fresh session with no memory of
the previous one (deliberately — a retrospective evaluation of version N has to be blind to
everything learned after N), so this file is the only thing that carries forward.

**Read before iterating. Append after.** Move entries between sections as evidence accumulates;
do not delete them. A reverted attempt is as useful as a confirmed one, and more likely to be
retried by accident.

**What belongs here rather than in `findings/iter-<n>.md`** is defined in one place: the
*"The two records, and what goes in which"* section of
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`. The short form is that this
file is about *how to optimize this task* and that one is about *these examples* — but do not
carry a second copy of the rule in your head from here.

---

## Status

**No iteration has run against the current objective.** This file was reset on 2026-09-07 and is
deliberately empty of history. That is not a bug and nothing is missing: **the next iteration to
run is iteration 1**, and it establishes the first baseline rather than reacting to one.

### Why it was reset, so nobody goes looking for the old entries

Three iterations ran on 2026-09-02 and everything they established was denominated in things that
have since changed underneath it:

- **The objective was macro-F1**, renormalised over the classes present in the batch. It is now
  plain **accuracy** over the nine labels, quoted against a 0.595 do-nothing floor. Every score,
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

*(Nothing yet. An entry here has moved the number in a predicted direction and been seen again.)*

## Pending

*(Nothing yet. An entry here is an edit that has been made and not yet scored, or a hypothesis with
some evidence and no test.)*

## Reverted

*(Nothing yet. Record what was undone and why — ⚠ the loop is forward-only, so "reverted" means
you edited it back yourself, not that the harness rolled it back.)*

## Notes on the instrument itself

*(Anything you learn about the harness, the release, the scorer or the corpus that a future
iteration would otherwise rediscover. Instrument problems are not program problems: record them
here and do not edit prompts in response to them.)*

## Iteration log

*(One entry per iteration: what you predicted, what happened, and what you concluded. Append;
never rewrite an earlier entry.)*
