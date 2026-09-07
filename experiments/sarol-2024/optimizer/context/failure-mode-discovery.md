# Failure-mode discovery — planning the fan-out, and reading what comes back

**For you, the optimizer.** This is Phases 1 and 2: how to choose which failures get read, how much
to spend reading them, and how to turn the results into failure modes.

**Your subagents do not read this file.** They get
`experiments/sarol-2024/optimizer/context/subagent-blame-brief.md`, which is their whole brief — the
corpus fields, the per-claim procedure, the blame categories and the record they return. Hand each
one that path plus its claim ids, and nothing else. It does not need your plan, and paying for it to
read your plan buys you nothing.

**Every path here is relative to your working directory, which is the repository root.**

## Where the failures are

Your release payload (`iter/<n>/release_train.json`) carries `corpus.ref`, a path to
`mistakes/<batch_id>.json` — the per-claim corpus for this iteration's TRAIN batch. That path is
what you hand your subagents.
`experiments/sarol-2024/optimizer/context/release-format.md` has its full shape.

Two properties of it that change how you plan:

**It holds only the claims that were wrong.** Correct ones are summarised by `n_correct`, not listed.
So it is a complete census of *this batch's* errors, not a sample of them — which is what makes
"how much mass does this mode carry" a real number rather than an impression.

**The TRAIN batch is re-drawn every iteration.** The draw seed is keyed on the iteration number;
VAL is fixed, TRAIN is not. So a failure you fixed last iteration and cannot find this iteration may
be fixed, or may simply not have been drawn. **Absence is not evidence.** Confirm a fix by watching
`per_class_f1` move in the direction you predicted, never by failing to re-find the instance.

## Choosing the draw

The corpus is complete, so "sampling" here is about spending attention, not about reaching the data.

**Read `n_correct` and `n_mistakes` first.** Three mistakes out of ten is a disaster and three out of
three hundred is near ceiling, and the same three look identical in the list.

Then pick a draw. Use one, or several in parallel:

- **Broad rotation.** A spread across the whole mistake list, to see the error distribution before
  you have a theory. The right opener when you do not yet know where the mass is. Vary which claims
  you take between iterations so you are not re-reading the same ones.
- **By gold class.** Everything whose gold is `INDIRECT`, say. This is how you find out why a class
  is scoring zero — and with a macro objective, a class with six gold instances moves the number as
  much as one with two hundred.
- **By confusion cell.** Everything where gold is X and the prediction was Y. The most diagnostic
  draw once you suspect a specific boundary is being crossed, because every example in it failed the
  same way by construction.
- **By evidence shape.** Claims whose `sub_claims[].evidence[].locator` values cluster tightly in one
  region of the paper versus scattering across it. A tight cluster means the judge was looking
  through a keyhole, and "unsupported" from inside one means something different than from a broad
  read.

**Size the fan-out to the question.** Subagents spend from your enforced budget. A first pass of a
few subagents on twenty-ish claims each usually settles where the mass is; widen only if the picture
is genuinely unclear. Do not fan out over every mistake in the corpus because you can.

**Give each subagent a disjoint slice.** Two subagents blaming the same claim produce a duplicate,
not a corroboration — and the counts in Phase 2 are only meaningful if each example is blamed once.

## What comes back

One record per claim: `claim_id`, gold/pred (with whether the miss crossed a 3-way bucket), a
**blame** category, a one-sentence **mechanism**, an evidence cue, and a confidence. The categories,
defined in the brief, are:

`rubric` · `retrieval` · `decomposition` · `attribution` · `gold` · `unclear`

Three of those — `rubric`, `decomposition`, `attribution` — are defects in guidance you can edit.
`retrieval` usually is not: see the reach caveat below. `gold` and `unclear` are neither, and a slice
that comes back mostly `unclear` is telling you the corpus fields were not enough, not that the
program is fine.

## Turning blames into modes

Collect the records into `experiments/sarol-2024/optimizer/findings/iter-<n>.md`, then cluster.

A **failure mode** is a recurring mechanism with a count and instances behind it. State it as the
step the program takes, not as the symptom:

> *"The judge treats an element it cannot find in the retrieved window as absent from the paper, and
> downgrades to NOT_SUBSTANTIATE."* — 7 claims, blame `retrieval`, all with locators clustered in one
> section.

not

> *"NOT_SUBSTANTIATE is over-predicted."* — which is a count, not a mechanism.

Report each mode with the count that supports it and which blame categories it drew from. **A mode
with one instance behind it is an anecdote** — record it, but say so, and do not spend the
iteration's edit on it over a mode carrying seven.

Watch for two things the counts will not tell you:

- **A mode that is really two.** If the instances split cleanly by gold class, or by whether the
  claim was multi-citation, they are probably two mechanisms sharing a symptom. Split them; a fix
  aimed at the merged version will address neither.
- **A mode outside your reach.** `retrieval`-blamed modes may have no rubric-side fix at all when the
  evidence is selected mechanically — see
  `experiments/sarol-2024/optimizer/context/edit-surface.md`. Say so explicitly rather than proposing
  a rubric edit that cannot bite. A mode you have correctly diagnosed and correctly declined to fix
  is a real result, and the next iteration should not have to rediscover it.

Then go to Phase 3 in your standing instructions.
