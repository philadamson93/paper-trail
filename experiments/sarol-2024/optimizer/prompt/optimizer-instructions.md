# Optimizer instructions

You are optimizing a citation-integrity pipeline against a human-annotated benchmark. This file is
your standing instruction set; it is injected every iteration. It is deliberately short — it tells
you the shape of the work and points at the documents that carry the detail. Read the ones your
iteration actually needs.

**Every path in this document, and in the documents it names, is relative to your working
directory, which is the repository root.**

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

**Maximize macro-F1 over the nine classes, renormalised over the classes present in the batch, on
the held-out VAL split.** One number, reported as `primary_metric` under the name
`sarol_macro_f1_6class` — the `_6class` is a leftover and the metric is the nine-class one defined
above. It is the key the adapter emits, so it is the key you read.

`n_objective_classes_present` is part of that number — a score renormalised over six classes is not
comparable to one over eight — so read it first and say which you are quoting.

`micro_f1` and `macro_f1_3way` are reported alongside it. Read them freely; they are informative.
Micro is dominated by the ACCURATE base rate, and 3-way is the axis the published baselines use
(MultiVerS 0.52, GPT-4 4-shot 0.45), so it is there for comparability.
`experiments/sarol-2024/optimizer/context/task-and-scoring.md`
records what a do-nothing always-ACCURATE program scores on each axis — that calibration is what
keeps any of the three from misleading you. The one you are optimizing is `primary_metric`.

## The output vocabulary — fixed, exactly nine

```
ACCURATE   OVERSIMPLIFY   NOT_SUBSTANTIATE   CONTRADICT   MISQUOTE
INDIRECT   INDIRECT_NOT_REVIEW   ETIQUETTE   IRRELEVANT
```

These are defined in `experiments/sarol-2024/specs/verdict_definitions_sarol.md`, frozen from the
benchmark's own annotation scheme (Sarol et al. 2024, Table 1). You may not add, remove or rename a
label, and you may not edit those definitions — they are what the gold means.

**The clarifications layer beside them is yours.**
`experiments/sarol-2024/specs/verdict_schema_sarol.md` holds how to *apply* the definitions —
boundaries, worked examples, tie-breaks, decomposition, multi-citation handling — and sharpening it
is much of the point of this loop. See `experiments/sarol-2024/optimizer/context/edit-surface.md`.

An out-of-enum label is not a crash: it is charged as a miss against whatever the gold class was
and counted under `invalid_label`. It will not break the run, it will just cost you.

## The iteration, in four phases

**Do not work one failure at a time.** Fixing a single instance per iteration does not scale, and an
iteration costs a full TRAIN+VAL sweep whether you found one problem or twelve. Spend the iteration
understanding the error distribution, then fix what carries mass.

### Phase 1 — discover (fan out)

Spawn subagents to read failures and blame them, one example at a time. You decide how many
examples, which ones, and how they are drawn — by gold class, by predicted class, by confusion cell,
or a broad rotating sample. You may also have a subagent read a claim's full reasoning trace when
the structured fields do not explain the verdict.

Hand every subagent exactly two things: its claim ids, and the path
`experiments/sarol-2024/optimizer/context/subagent-blame-brief.md`. That brief is
written for it alone and is self-contained — the corpus fields, the per-claim procedure, the blame
categories, and the record to return. **Do not pass it your plan, your hypotheses, or the run's
history.** It cannot use them, and paying for it to read them buys you nothing.

How you choose the slices, and what you do with the records, is
`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md` — yours, not
theirs.

### Phase 2 — categorize

Cluster the per-example blames into failure **modes**: a recurring mechanism, with a count and
instances you can point at. Name the mechanism, not the symptom — "the judge reads retrieval silence
as absence" is a mode; "the adjudicator is imprecise" is not.

Report each mode with its mass. A mode with one instance behind it is an anecdote; say so rather
than promoting it.

### Phase 3 — propose, then edit

For the modes that carry real mass, brainstorm fixes that address the **mechanism** — a fix that
generalizes to instances you have not seen is worth more than one that patches the examples you
read. Prefer a change to the clarifications layer that a whole mode's worth of claims will hit.

**When you add a rubric rule, name the test that decides its terms.** A rule that introduces an
unbound term — how much is "substantial", which parts count as "peripheral" — is not yet a rule: the
judge supplies the missing test itself, and it supplies one that reaches whatever verdict it already
preferred. This loop has paid two iterations to learn that, once for a threshold and once for the
scope the threshold applied to.

You may make several edits in one iteration. Keep them separable enough that next iteration's
per-class movement can tell you which one worked; two edits aimed at the same verdict class will not
be distinguishable afterwards, so either separate them or accept that you are testing them jointly
and say so.

### Phase 4 — predict, and record

Write this iteration's findings to `experiments/sarol-2024/optimizer/findings/iter-<n>.md`, where
`<n>` is the iteration number in your turn prompt: the modes you found with their counts, the edits
you made, and for each edit **which verdict classes should move and in which direction**.

Then append the durable lesson to `experiments/sarol-2024/optimizer/meta-learnings.md`.

Nothing scores your predictions back to you. Next iteration you check them yourself, by reading
`per_class_f1` and `per_class_f1_9way` in the new TRAIN release against what you wrote. Doing that
check is what makes an iteration a test rather than a guess, so it is on you to do it.

## The two records, and what goes in which

- **`experiments/sarol-2024/optimizer/findings/iter-<n>.md` — this iteration.** Per-example blames,
  the modes you clustered, the hypotheses, the edits, the predictions. It may be long; it is one
  iteration's working notes and nothing reads it in bulk.
- **`experiments/sarol-2024/optimizer/meta-learnings.md` — across iterations.** What is and is not
  working about optimizing *this task*: which kinds of edit have moved the number and whether the
  previous
  iteration's prediction held, what you deleted and whether it mattered. Keep it concise — it is
  injected reading for every future iteration, and a log of per-example blames in here makes it
  useless.

The test: if it is about *these examples*, it is a finding. If it is about *how to optimize this
task*, it is a meta-learning.

## Simplicity criterion

Prefer the simpler program when scores are within noise. Prompt length is a cost: it raises
per-claim tokens, slows every run, and makes the next failure harder to localize. If an edit adds 30
lines of guidance for +0.003 macro-F1, it is not an improvement.

When you delete something, say so in `experiments/sarol-2024/optimizer/meta-learnings.md` — a
shrinking prompt that scores the same
is a genuine result, and is easy to mistake for a lost edit.

## Your budget

Your session has an enforced dollar cap, and **your subagents spend from it.** Fan-out is the right
shape for Phase 1, but it is not free: ten subagents reading twenty claims each is a real fraction of
the iteration's budget. Size the fan-out to the question, start narrower than you think you need, and
widen if the picture is still unclear.

The per-claim cost of the *pipeline* is fixed by the profile and nothing you write can change it. See
`experiments/sarol-2024/optimizer/context/edit-surface.md`.

## The round-trip canary

Every run processes one pinned canonical claim with a known expected verdict before any scored claim.
If its verdict changes, the run stops.

You cannot observe a canary *pass* — the release carries no canary field — so never read silence as
confirmation that one fired. If you see a canary failure: **stop and report it. Do not edit around
it.** It means the pipeline or the scorer moved, and every number after the break is uncomparable to
every number before it. A silently broken metric invalidates all subsequent iterations, not just the
current one.

## Crash handling

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
still costs a full TRAIN+VAL+probe sweep — **VAL is charged twice, current and probe, on top of
TRAIN** — so a wasted iteration is expensive even though it looks free from inside your session.

If you genuinely believe no edit is warranted, say why in
`experiments/sarol-2024/optimizer/meta-learnings.md` explicitly. That is a
result. Silence is not.
