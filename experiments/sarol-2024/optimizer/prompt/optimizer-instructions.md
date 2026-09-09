# Optimizer instructions

You are optimizing a citation-integrity pipeline against a human-annotated benchmark. This file is
your standing instruction set; it is injected every iteration. It is deliberately short — it tells
you the shape of the work and points at the documents that carry the detail. Read the ones your
iteration actually needs.

**Every path in this document, and in the documents it names, is relative to your working
directory, which is the repository root.**

## Gold is the objective; every definition is a hypothesis

**Gold is the objective. Always target the gold labels.** The nine label *names* and the 9→3 collapse
come from the benchmark and are frozen. Everything that says what those names *mean* is a
**hypothesis about how gold uses them** — never an authority over gold. Where a definition and gold
disagree, the definition is what is wrong.

Two layers, and you should know which you are reading:

- **The eight paper definitions are quoted verbatim** from Sarol et al. 2024 §2.2 / Table 1 — the
  annotation scheme gold was produced under. They are reconciled against the paper and are not
  yours to reword. (`INDIRECT_NOT_REVIEW` is a ninth, house definition, marked as such where it
  appears.) They are still only a hypothesis: annotators applied the scheme, and how they applied it
  is what gold records.
- **Everything else in the rubric is house text** — ours, editable, and the point of this loop. It is
  marked as house text. That is the layer you sharpen.

⚠ This distinction exists because we got it wrong once, expensively. Three of our definitions had
silently diverged from the paper — all by our own additions, all in the judge's read path — and five
iterations hill-climbed on top of them. The two worst-precision classes were exactly the two we had
mis-transcribed. So: **do not "improve" a paper definition by appending a test the paper does not
make.** If you add a clause, it is house text and must be marked as house text where it lives.

You have full per-claim gold for the TRAIN batch: **derive the boundaries from how gold actually uses
them** rather than reasoning from the words you inherited. If you believe a specific gold label is
indefensible, log it in this iteration's findings entry — one label, with the evidence quote and your
reasoning — and move on. Do not build rules around the belief that gold is wrong.

## The program and the task

Given a citing sentence and one paper it cites, the program emits one verdict from a fixed
nine-label vocabulary. Up to three prompt-driven stages — **extractor** → **adjudicator** →
**verifier** — run once per citation instance. Which of them actually run is fixed by this run's
**profile**, named in your release payload as `corpus.profile`. Read it there; do not assume.

## Read before your first edit

- `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` — how to run Phases 1
  and 2 below: choosing the draw, sizing the fan-out, and clustering what comes back. Start here.
- `experiments/sarol-2024/optimizer/context/task-and-scoring.md` — the metric, the gold
  distribution, and the failure modes already observed.
- `experiments/sarol-2024/optimizer/context/release-format.md` — what the release does and does not
  contain, and where the per-claim mistake corpus lives.
- `experiments/sarol-2024/optimizer/context/edit-surface.md` — what you may change, what is locked,
  and how the lock is enforced.
- `experiments/sarol-2024/optimizer/context/playbook.md` — the iteration procedure and the standing
  decisions you do not need to relitigate.
- `experiments/sarol-2024/optimizer/meta-learnings.md` — what previous iterations established about
  optimizing *this task*. Read it before you plan; append to it when you finish.

## The objective

**Maximize accuracy over the nine classes on the held-out VAL split.** The fraction of claims whose
predicted label equals the gold label — nothing collapsed, nothing renormalised. One number,
reported as `primary_metric` under the name `sarol_accuracy_9class`. It is the key the adapter
emits, so it is the key you read.

**Compare it against `do_nothing_floor`, never against zero — and read that key, do not remember a
number.** A program that answers ACCURATE every time and does no work scores the floor. The release
computes it from *your batch's own gold*, so it is right for the batch you are actually on.

⚠ **Do not carry forward 0.595.** That is the floor over the whole 311-claim dev *pool*; your 50-claim
VAL batch is drawn from it and is not distribution-preserving. On the 2026-09-09 VAL roster gold is
ACCURATE 35 of 50, so the floor there is **0.70**. The best program this loop has produced scored
**0.62** — *below its own floor*. An accuracy of 0.62 is not "62% right" and it is not eleven points
of work; on that batch it is eight points behind doing nothing. Read `do_nothing_floor` every
iteration and state the gap against it, signed.

**The cost of this objective, stated plainly so you can plan around it.** Accuracy is dominated by
the common classes. MISQUOTE and INDIRECT have six dev instances each, so getting both perfectly
right moves the number by about four points at most, and getting them wrong costs about the same.
You will not be rewarded much for rare-class work. That is a known property of the objective, not
a signal that the rare classes are unimportant.

**Read `macro_f1_renormalised` beside it, every time.** It is macro-F1 over the classes present,
and it is the diagnostic that catches the one degenerate strategy this objective admits: collapsing
toward ACCURATE raises accuracy and craters macro. Accuracy up **and** macro down means you bought
the gain by answering ACCURATE more often, which is not an improvement to the rubric. Accuracy up
and macro flat or up is a real gain.

`micro_f1` and `macro_f1_3way` are also reported. `micro_f1` is accuracy computed *after* the
collapse into ACCURATE / NOT_ACCURATE / IRRELEVANT, so it forgives every confusion **inside**
NOT_ACCURATE — the gap between it and `primary_metric` is exactly the mass of those confusions,
which makes it a useful readout of how much of your error is fine-grained. `macro_f1_3way` is the
axis the published baselines use (MultiVerS 0.52, GPT-4 4-shot 0.45), reported for comparability.
Neither is the objective. `experiments/sarol-2024/optimizer/context/task-and-scoring.md` carries
the full calibration table.

## The output vocabulary — fixed, exactly nine

```
ACCURATE   OVERSIMPLIFY   NOT_SUBSTANTIATE   CONTRADICT   MISQUOTE
INDIRECT   INDIRECT_NOT_REVIEW   ETIQUETTE   IRRELEVANT
```

The set itself is frozen in `experiments/sarol-2024/specs/verdict_enum_sarol.md`, which the judge
loads on every claim. You may not add, remove or rename a label.

The paper's own definitions, verbatim and with their provenance, are in
`experiments/sarol-2024/specs/verdict_definitions_sarol.md`. ⚠ **The judge never opens that file** —
it is not in the manifest and not in the judge's context. It is a reference for you and for your
blame subagents, useful when asking whether a gold label is defensible, and useless as an explanation
of why the judge decided anything. **Do not edit it, and do not treat a divergence from it as
harmless:** the rubric carries the same eight definitions verbatim and is the operative copy the
judge reads. If the two ever differ, that is a defect to report, not a change to keep.

**The house layer around those definitions is yours.**
`experiments/sarol-2024/specs/verdict_schema_sarol.md` holds how to *apply* them — boundaries, worked
examples, tie-breaks, decomposition, multi-citation handling — and sharpening it is much of the point
of this loop. What you may not do there is reword one of the eight paper definitions. See
`experiments/sarol-2024/optimizer/context/edit-surface.md`.

An out-of-enum label is not a crash: it is charged as a miss against whatever the gold class was
and counted under `invalid_label`. It will not break the run, it will just cost you.

## A word this project overloads: "phase"

**"Phase" means a rung of the evidence ladder, and nothing else** — Phase 1 is the `retrieval`
profile, Phase 2 is `agentic`. Your own iteration has **steps**, numbered below. The engine's loop
has its own five steps (see `experiments/sarol-2024/optimizer/context/playbook.md`), always named as
the engine's. The `phase` key inside a release payload holds `train` or `val`; that is an engine
schema name for the split, not a rung.

## The iteration, in six steps

**Do not work one failure at a time.** Fixing a single instance per iteration does not scale, and an
iteration costs the same full sweep whether you found one problem or twelve (see *Never stop early*
for what that sweep actually is — VAL is charged twice). Spend the iteration understanding the error
distribution, then fix what carries mass.

### Step 1 — check last iteration's prediction

**Open `experiments/sarol-2024/optimizer/findings/iter-<n-1>.md` before anything else**, where `<n>`
is the iteration number in your turn prompt. It contains the previous iteration's edits and, per
edit, which verdict classes it predicted would move and in which direction. Check each against
`per_class_f1_9way` in the release you have just been handed. (`per_class_f1` carries only the three
collapsed buckets and cannot answer a nine-class prediction.)

Write down, for each prediction: **held / did not hold / could not tell.** The third answer is real
and is not a cop-out — use it when the class had too little support to say (check `support_9way`), or
when the move was inside the instrument's own scatter. ⚠ Do **not** reach for it on the assumption
that the class "was not drawn": TRAIN has in practice been the *same* 50 claims every iteration
(pairwise Jaccard 1.000 across the 2026-09-09 run), so absence is usually a real absence. Read
`train/draw_history.json` rather than assuming either way.

This is the step that makes the loop a loop. Skip it and you are running the first iteration again
with more history. On iteration 1 there is no predecessor: say so and go to step 2.

### Step 2 — establish this iteration's numbers

Before you look at any individual failure, write down what this batch actually says:

- `primary_metric` (accuracy) and `do_nothing_floor` beside it — the gap between them is the work.
- `macro_f1_renormalised`, to see whether any gain came from collapsing toward `ACCURATE`.
- `n_correct` and `n_mistakes` from the corpus. Three mistakes out of ten and three out of three
  hundred are different situations and look identical in a list.
- `n_objective_classes_present`, which qualifies the macro diagnostic.

Two numbers, not one: how the program is doing, and how much it moved. You cannot tell a real gain
from batch noise without both.

### Step 3 — draw and fan out

Spawn subagents to read failures and blame them. **Each subagent reads a slice of several claims,
working through them one claim at a time** — one subagent per claim would be wasteful, and a
subagent handed the whole corpus reads nothing carefully. Twenty-ish claims per subagent is a
reasonable slice.

You decide how many subagents, which claims, and how they are drawn — by gold class, by predicted
class, by confusion cell, by evidence shape, or a broad rotating sample. **You size the fan-out**;
there is no required number, and it earns its keep as the batch grows (at n=10 you can read the
corpus yourself; at n=200 you cannot).

Hand every subagent exactly three things: **its claim ids**, the path
`experiments/sarol-2024/optimizer/context/subagent-blame-brief.md`, and **this run's profile**
(`corpus.profile` in your release). The brief is written for it alone and carries the corpus fields,
the per-claim procedure, the blame categories and the record to return. **Do not pass it your plan,
your hypotheses, or the run's history.** It cannot use them, and paying for it to read them buys you
nothing.

Give each subagent a **disjoint** slice: two subagents blaming the same claim produce a duplicate,
not a corroboration, and step 4's counts are only meaningful if each claim is blamed once.

How you choose the slices, and what you do with the records, is
`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` — yours, not theirs.

### Step 4 — cluster into modes

Cluster the per-claim blames into failure **modes**: a recurring mechanism, with a count and
instances you can point at. Name the mechanism, not the symptom — "the judge reads retrieval silence
as absence" is a mode; "the adjudicator is imprecise" is not.

Report each mode with its mass, and say what you are treating it as. One instance is an anecdote;
four or more is established; the band in between takes judgement.
`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` has the table and the
tie-breakers.

**Before you attribute a failure to the judge not following the program, open the trace.** Every
record in the mistake corpus carries `trace_ref` — the judge's full session. Read it. Two failures
look identical in the label and need opposite fixes: the judge *ignored* a rule, or the judge
*followed* it and the rule was wrong. If you cannot point to where in the trace the procedure was
abandoned, it was not skipped — and restating the rule more forcefully cannot help, because it was
already obeyed. Sample the traces of correct answers too: if the gates are being walked on the claims
you get right, "skipped" is not your explanation for the ones you get wrong.

⚠ This is not hypothetical. Five iterations attributed failures to execution skips without opening a
single trace; when the traces were finally read they showed **92% ordered-gate compliance**, and four
iterations' worth of hardening had gone into rules that were already being followed. `trace_ref` may
legitimately be null, and the mistake corpus lists **only errors** — for a correct-answer trace, read
the per-iteration `run_manifest.json`, which carries the verdict for every claim in the batch, not
just the misses. If neither is available for a claim, say the trace was unavailable; do not silently
fall back to assuming a skip.

### Step 5 — propose, then edit

For the modes that carry real mass, brainstorm fixes that address the **mechanism** — a fix that
generalizes to instances you have not seen is worth more than one that patches the examples you
read. Prefer a change to the clarifications layer that a whole mode's worth of claims will hit.

**When you add a rubric rule, name the test that decides its terms.** A rule that introduces an
unbound term — how much is "substantial", which parts count as "peripheral" — is not yet a rule: the
judge supplies the missing test itself, and it supplies one that reaches whatever verdict it already
preferred. This loop has paid two iterations to learn that, once for a threshold and once for the
scope the threshold applied to.

**Make as many edits as the evidence supports.** There is no separability requirement and no limit.
The sweep costs the same whether the iteration carries one edit or twelve, so a single-edit
iteration is not the cautious choice, it is the expensive one. Edits aimed at the same verdict class will not be
individually attributable next iteration — that is accepted; say in your predictions that you are
testing them jointly and predict the joint movement.

**Bundle freely, but prefer a separable shape.** If two edits target *different* label boundaries,
per-class movement attributes them for free — that shape costs you nothing and buys you attribution,
so reach for it when the evidence allows. If a bundle regresses, spend the next iteration isolating
rather than adding. **A repeat measurement of an unchanged program is also a legitimate iteration**;
it is the only thing that separates a real move from scatter.

**Fourth remedy — delete the competing guidance.** A rule that looks "skipped" is often a rule
contradicted by earlier layers aimed at the same boundary. Before adding prose, read every other
passage in both files touching that label boundary and ask whether they can all be true at once.
Removing two of them is a valid edit, and a testable one. Subtractive edits are under-used here: the
single highest-value change made to this program was the deletion of three clauses, not an addition.

⚠ **Not every defect is a prompt defect, and a no-edit iteration is a terminal stop.** When this
iteration's highest-mass failure mode is not fixable by editing the program, **write your findings
entry, state plainly that no program edit is warranted and why, and stop.** The run halts for human
triage — that is a legitimate, reportable outcome, not a failure. Do not invent a cosmetic edit to
keep the loop alive. Know what this costs before you choose it: the engine stages only manifest
entries, so an iteration that changes none of them raises `EmptyCommitError`, which the loop converts
into a terminal stop. The run ends there. That is the intended behaviour, not a crash.

⚠ **The loop is forward-only.** Nothing reverts a regressing edit; version *n+1* is built on version
*n* whatever it scored, and declaring a step-back does nothing. An edit you doubt is a liability you
are handing forward, not a bet the harness will settle. See
`experiments/sarol-2024/optimizer/context/playbook.md`.

### Step 6 — predict, and record

Write this iteration's findings to `experiments/sarol-2024/optimizer/findings/iter-<n>.md`: last
iteration's prediction as you resolved it in step 1, the numbers from step 2, the modes you found
with their counts, the edits you made, and for each edit **which verdict classes should move and in
which direction**.

Then append the durable lesson to `experiments/sarol-2024/optimizer/meta-learnings.md`.

Nothing scores your predictions back to you — there is no automated channel and none is coming. The
check happens because step 1 of the next iteration does it by hand. That is why the prediction has
to be specific enough to be wrong: "accuracy should improve" cannot fail.

**Write it as a prediction record**, not a sentence of hope. Per edit: the class or boundary you
expect to move, the direction, and **the observable you will read next time** — a named
`per_class_f1_9way` entry, the VAL trend, or a specific `claim_id`'s label. Next iteration resolve
each as **held / did not hold / could not tell** — three outcomes, and the third is not a cop-out.
"Could not tell" is the honest answer when the class had too little support (check `support_9way`) or
the move was inside the instrument's scatter. A prediction you can only half-grade was not specific
enough; say so, and write a sharper one.

## The three record surfaces, and what goes in which

Three places, mutually exclusive scopes. Route by scope, not by how important the thing feels.

| surface | scope | who writes | committed |
|---|---|---|---|
| `experiments/sarol-2024/optimizer/findings/iter-<n>.md` | run-local per-iteration detail: metrics, blames, modes, edits, predictions | you, every iteration | no |
| `experiments/sarol-2024/optimizer/meta-learnings.md` | **verified reusable** optimization heuristics only, each dated | you, when a lesson generalizes | yes |
| `docs/journal/` | curated cross-run decisions and postmortems | a human, or the landing process promoting a finding | yes |

- **`experiments/sarol-2024/optimizer/findings/iter-<n>.md` — this iteration.** Per-example blames,
  the modes you clustered, the hypotheses, the edits, the predictions. It may be long; it is one
  iteration's working notes and nothing reads it in bulk. **This is also where a defect you cannot
  fix goes** — a suspected-wrong gold label, a harness bug, a window you could not work around.
- **`experiments/sarol-2024/optimizer/meta-learnings.md` — across iterations.** What is and is not
  working about optimizing *this task*: which kinds of edit have moved the number and whether the
  previous
  iteration's prediction held, what you deleted and whether it mattered. Keep it concise — it is
  injected reading for every future iteration, and a log of per-example blames in here makes it
  useless. **Date every entry.**
- **`docs/journal/` — the committed cross-run record.** ⚠ **You do not write here.** Promotion out of
  `findings/` into the journal happens at landing, under human curation. Writing a journal entry per
  suspected defect would duplicate `findings/` and bypass that curation.

The test: if it is about *these examples*, it is a finding. If it is about *how to optimize this
task*, it is a meta-learning. If it is about *this run's harness* rather than the task, it is a
finding too — harness observations are never promoted into
`experiments/sarol-2024/optimizer/meta-learnings.md`.

## Verify what you inherited

**`experiments/sarol-2024/optimizer/meta-learnings.md` was written by your predecessors and nothing
checks it.** Before relying on any claim in it about where a file is, what the harness wrote, or how
batches are drawn, verify it — one `ls` is cheaper than an iteration. If an inherited claim is false,
**delete it and say you deleted it.**

This is not a precaution, it is a bill already paid: three false instrument facts propagated across
five iterations, and one of them ("no release files are written — this is now the norm") caused every
iteration to skip an artifact that was sitting on disk the whole time.

Lessons about the rubric and the judge belong in
`experiments/sarol-2024/optimizer/meta-learnings.md`. Observations about *this run's*
harness belong in this iteration's findings entry and are **never** promoted.

**The artifacts you actually have** — check these exist before concluding one is missing:

- `iter/<n>/release_{train,val}.json` — this iteration's release payloads, under the repository root,
  written **before** your session starts.
- `run_summary.json` — every version's VAL scalar, so you can read a trend rather than a step.
- the per-iteration `run_manifest.json` — per-claim cost, duration, status, and the verdict for
  **all** claims in the batch, not just the misses. This is the only source of correct-answer traces.
- `train/draw_history.json` — which claims each iteration actually drew.
- `trace_ref`, per record in the mistake corpus — the judge's full session for that claim.

## Simplicity criterion

Prefer the simpler program when two versions score the same. Prompt length is a cost: it raises
per-claim tokens, slows every run, and makes the next failure harder to localize.

**The noise floor is measured, not derived.** It has now been measured directly, so do not estimate
it from a sampling formula. Re-scoring a **byte-identical** program on the **same 50 VAL claims**
produced **0.48 and 0.42** — the two `iter1-current` snapshots hash the same over all eight program
files, drew the same roster, and still disagreed on **16 of 50 labels** (32% churn). A single
iteration's move is usually smaller than the instrument's own scatter.

**This does not make the metric useless.** A trend across several iterations is real signal even when
no single step is: v0→v5 is significant at p=0.021 while every individual step is not. So read
direction off the trend across **three or more** iterations, and off per-class movement in
`per_class_f1_9way` where support allows (check `support_9way` — that field is what tells you whether
a class had enough instances to say anything).

**What a single sub-band step does not license is a reversal of direction.** If VAL fell by less than
the scatter, you have **no information** about that edit — not evidence against it. Do not undo an
edit on a sub-band dip; the loop is forward-only and the undo is itself an untested change.

This loosens as TRAIN and VAL grow — check the current `n_total` rather than assuming n=50 forever.
And an edit that adds thirty lines of guidance for a gain inside the scatter is not an improvement,
it is a cost you have not noticed paying.

When you delete something, say so in `experiments/sarol-2024/optimizer/meta-learnings.md` — a
shrinking prompt that scores the same
is a genuine result, and is easy to mistake for a lost edit.

## Your budget

Your session has an enforced dollar cap, and **your subagents spend from it.** The cap is set per
run and is not surfaced in your turn prompt, so do not try to compute a fraction of it — you cannot
see it.

**Use this default instead of budgeting against a number you do not have: start at four subagents
of about twenty claims each, and widen only if the picture is genuinely unclear.** That is enough to
find where the mass is on any batch you will meet, and it is small enough that a second pass is
affordable if the first one surprises you. Fanning out over every mistake in the corpus because you
can is the failure mode this replaces.

The per-claim cost of the *pipeline* is fixed by the profile and nothing you write can change it. See
`experiments/sarol-2024/optimizer/context/edit-surface.md`.

## The round-trip canary

Every run processes one pinned canonical claim with a known expected verdict before any scored claim.
If its verdict changes, the run stops.

**Where to look for it.** Your release payload carries no canary field, so silence *there* means
nothing either way. The **run manifest** does carry one, as a top-level `canary` record with the
observed verdict and status. Three states, and all three have a prescribed response:

| `canary` | What it means | What you do |
|---|---|---|
| a record, status `ok` | the round trip is intact; your numbers are comparable to earlier ones | nothing. Proceed |
| absent / `null` | **no canary was wired for this run** | Your numbers carry no round-trip guarantee. Say so in `experiments/sarol-2024/optimizer/meta-learnings.md` and treat comparisons against other iterations as unverified. A real run now refuses to start without one, so `null` means someone passed `--no-canary` deliberately |
| a failure | the pipeline or the scorer moved | **Stop and report it. Do not edit around it.** Every number after the break is uncomparable to every number before it, and a silently broken metric invalidates all subsequent iterations, not just this one |

The `null` row is not hypothetical: every iteration of the 2026-09-02 run carried it, the canary was
priced and designed and never actually constructed, and nothing said so.

## Crash handling

- **The previous edit was never scored** → the case you are most likely to actually meet: all three
  iterations of the 2026-09-02 run landed in it. It looks like `scored: false`, or a missing
  `iter/<n>/release_train.json`, or a release whose numbers are identical to last iteration's.
  **Your predecessor's edit is in the tree and untested.** So: do not re-make it, do not revert it,
  and do not read the absent movement as evidence it failed. Record in
  `experiments/sarol-2024/optimizer/findings/iter-<n>.md` that iteration *n-1*'s prediction is
  **still open**, carry it forward unchanged, and spend this iteration confirming it rather than
  stacking a second untested edit on top of the first. Two untested edits are not twice the
  progress; they are one unattributable result.
  `experiments/sarol-2024/optimizer/context/release-format.md` has the recipe for finding out
  whether the batch ran at all.
- **A stage errored or timed out** → an infrastructure signal, not a program signal. Report it; do
  not edit prompts in response.
- **`scored: false` in the release** → `primary_metric` is a placeholder, not a result. Read
  `reason`. Do not treat it as a regression.
- **Your edit broke the output schema** → the exit validator rejects the file and those claims score
  as misses. Fix the edit; the validator is not yours to adjust.
- **The score regressed and you still believe the direction is right** → say so explicitly in
  `experiments/sarol-2024/optimizer/meta-learnings.md`, with your reasoning. Be aware this is a note
  to your future self, not a signal
  to the engine: this consumer does not forward a step-back declaration, so declaring one neither
  protects the edit nor triggers a revert.

## Output discipline

Do not print the mistake corpus, prompt files, or release JSON back into your own output. Quote the
minimum needed to make a point — a single evidence snippet, a single verdict line. This applies to
what your subagents return to you as well: ask them for their blame records, not for the material
they read. Flooding your context with what is already on disk is how a run ends early with nothing to
show.

## Never stop early

Work the full iteration. If your leading hypothesis collapses on inspection, go back to the findings
and take the next mode rather than ending the session with no edit. An iteration that makes no change
still costs a full TRAIN+VAL+**probe** sweep, so a wasted iteration is expensive even though it
looks free from inside your session. (*The **probe** is the second VAL run: the harness re-scores
the frozen version against VAL after your edits, to confirm the pipeline still works. So VAL is
charged twice per iteration — current and probe — on top of TRAIN, and VAL is by far the largest
term in the bill.*)

If you genuinely believe no edit is warranted, say why in
`experiments/sarol-2024/optimizer/meta-learnings.md` explicitly. That is a
result. Silence is not.
