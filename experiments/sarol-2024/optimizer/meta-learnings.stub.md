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

**This run has established nothing yet.** You are the first iteration of a fresh run, and this
sheet belongs to this run alone — it is archived and reset at the start of every run, so there is
no prior-run history here and none is missing. Nothing below is empty because something broke.

Record what *this* run establishes. Sections are ordered by how settled a claim is; move entries
between them as evidence accumulates rather than rewriting them in place.

⚠ **One measurement fact you need before your first entry, because it decides what counts as a
result:** the instrument's own scatter is **0.06** — a byte-identical program re-scored 0.48 vs
0.42 on the same 50 claims. A single-iteration delta of 0.02–0.04 is *inside* that scatter. Write
those down as hypotheses seen once, never as settled results.

## Confirmed

*(Claims this run has tested more than once, in the same direction.)*

## Pending

*(Claims seen once. Most single-iteration deltas belong here, not above.)*

## Resolved baselines (kept for provenance)

*(Numbers this run has pinned, each with the batch and key it was measured against.)*

## Reverted

*(Attempts this run made and backed out. As useful as a confirmed one, and likelier to be retried
by accident — say what you tried and what the measurement did.)*

## Notes on the instrument itself

*(Things you learned about the harness rather than about the task. If you believe an inherited
harness fact is wrong, verify it and record the verification here.)*

## Iteration log

*(One line per iteration: what you changed, what the measurement did, what you concluded.)*
