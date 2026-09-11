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

**Do not assume the TRAIN batch was re-drawn.** The draw is keyed on the iteration number, so a
different roster is possible in principle — but measured over the last run's
`train/draw_history.json`, all five iterations drew the **same 50 claims** (pairwise Jaccard 1.000).
**Read `train/draw_history.json` for this run and check** before treating a missing failure as
either fixed or undrawn. If the roster really did change, absence is not evidence. Confirm a fix by watching
`per_class_f1_9way` move in the direction you predicted, never by failing to re-find the instance.
(`per_class_f1` has only the three collapsed buckets in it and cannot answer a nine-class question.)

## Choosing the draw

The corpus is complete, so "sampling" here is about spending attention, not about reaching the data.

**Read `n_correct` and `n_mistakes` first.** Three mistakes out of ten is a disaster and three out of
three hundred is near ceiling, and the same three look identical in the list.

Then pick a draw. Use one, or several in parallel:

- **Broad rotation.** A spread across the whole mistake list, to see the error distribution before
  you have a theory. The right opener when you do not yet know where the mass is. Vary which claims
  you take between iterations so you are not re-reading the same ones.
- **By gold class.** Everything whose gold is `INDIRECT`, say. This is how you find out why a class
  is scoring zero. ⚠ **Weigh it by mass now.** Under the old macro objective a class with six gold
  instances moved the number as much as one with two hundred; under accuracy it moves it thirty-three
  times less. Reading a rare class is still worth doing — it is often where a mechanism is clearest —
  but expect to spend the iteration's *score* on the classes that carry claims.
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

`rubric` · `execution` · `retrieval` · `decomposition` · `attribution` · `gold` · `unclear`

Four of those — `rubric`, `execution`, `decomposition`, `attribution` — are defects in guidance you
can edit, and the first two want **opposite** edits: `rubric` means the guidance is wrong or silent
(write a rule), `execution` means the rule is already there and was skipped (make it harder to skip —
move it earlier, state it as a check, give it a worked example). A cluster of `execution` blames that
you treat as `rubric` produces an iteration spent re-writing a rule the judge already had.

⚠ **Do not accept an `execution` blame that has no trace quote behind it.** The brief requires a
subagent to open `trace_ref` and quote the point where the procedure was abandoned before recording
`execution`; a record without that quote is `unclear`, not `execution`. The reason is measured, not
theoretical: five iterations attributed failures to execution skips without opening a single trace,
and the traces showed **92% ordered-gate compliance** — the forced-nuance artifact at 31/31. Four
iterations went into hardening rules that were already being followed, for 1,716 added words and a
VAL move inside the scatter. **Restating an obeyed rule cannot help.** Sample the traces of correct
answers too: if the gates are being walked on the claims you get right, "skipped" is not your
explanation for the ones you get wrong. Correct-answer traces come from the per-iteration
`run_manifest.json`, not the mistake corpus, which lists only errors.

**A fourth remedy, and the one this loop has never reached for: delete the competing guidance.** A
rule that looks "skipped" is often a rule *contradicted* by an earlier layer aimed at the same
boundary — the judge followed the other one. Before adding prose, read every other passage in both
files touching that label boundary and ask whether they can all be true at once. **Removing two of
them is a valid edit, and a testable one.** Prose that accretes without deletion is how a program
develops internal contradictions that no amount of further prose resolves.

`retrieval` is reachable in one specific way and not another — see the reach test below. `gold` and
`unclear` are neither, and a slice that comes back mostly `unclear` is telling you the corpus fields
were not enough, not that the program is fine.

## Turning blames into modes

Collect the records into `experiments/sarol-2024/optimizer/findings/iter-<n>.md`, then cluster.

A **failure mode** is a recurring mechanism with a count and instances behind it. State it as the
step the program takes, not as the symptom:

> *"The judge treats an element it cannot find in the retrieved window as absent from the paper, and
> downgrades to NOT_SUBSTANTIATE."* — 7 claims, blame `retrieval`, all with locators clustered in one
> section.

not

> *"NOT_SUBSTANTIATE is over-predicted."* — which is a count, not a mechanism.

Report each mode with the count that supports it and which blame categories it drew from, and say
what you are treating it as. The usable rule, since "one instance is an anecdote" only tells you the
bottom of the scale:

| Instances in the mode | Treat it as | What to do |
|---|---|---|
| 1 | anecdote | Record it. Do not edit for it |
| 2-3 | candidate | Edit for it only if the mechanism is *clear enough to state in one sentence* and the fix is cheap. Otherwise record it and look for more instances next iteration |
| 4+ | established | Edit for it. This is what an iteration is for |
| ≥ 20% of the mistake list | dominant | Edit for it FIRST, whatever else you found |

The 2-3 band is the one that needs judgement, and the tie-breaker is the mechanism rather than the
count: three claims failing the same clearly-named step is worth more than three claims that merely
share a gold class. When two modes tie, take the one whose claims are more common in the batch —
under accuracy that is where the points are.

Watch for two things the counts will not tell you:

- **A mode that is really two.** If the instances split cleanly by gold class, or by whether the
  claim was multi-citation, they are probably two mechanisms sharing a symptom. Split them; a fix
  aimed at the merged version will address neither.
- **A mode outside your reach — and the reach test is narrower than it looks.** For a
  `retrieval`-blamed mode, ask which of two questions it is:

  **"The right passage was not retrieved."** Out of reach under `retrieval`, where BM25 does the
  selecting and no prompt of yours runs before the judge. Say so and move on. (Under `agentic` /
  `paperclip` the extractor prompt *is* yours, so the same mode is reachable there.)

  **"The judge mishandled a thin window."** *In* reach on every profile, and it is a live target
  rather than a consolation prize — the judge is never told its evidence is a subset, so it reports
  a fact as absent from the paper when the fact was merely not retrieved. Teaching the rubric to
  separate *the paper does not say it* from *what I was given does not say it* is a clarifications-
  layer edit, it costs nothing, and it is documented as failure mode 2 in
  `experiments/sarol-2024/optimizer/context/task-and-scoring.md`.

  The distinction matters because these are the same blame label on the same claims. Earlier
  iterations read "retrieval-blamed modes are out of reach under a mechanical profile" as covering
  both, and dropped a mode that was fully editable. **Only the first question is out of reach.**

Then go to Phase 3 in your standing instructions.
