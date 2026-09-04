# Optimizer instructions

You are optimizing a citation-integrity pipeline against a human-annotated benchmark. This file is
your standing instruction set; it is injected every iteration. Structure follows Karpathy's
*program.md* (autoresearch, 2026), adapted to this task.

## Setup

The program is up to three prompt-driven stages — **extractor** → **adjudicator** → **verifier** —
run
once per citation instance. Given a citing sentence and one paper it cites, it emits one verdict
from a fixed nine-label vocabulary.

Your job each iteration: read the release, form one hypothesis about a failure class, make the
smallest edit that tests it, and record what you predicted.

**Every path in this document and in the documents it names is relative to your working
directory, which is the repository root.**

Read these before your first edit:

- `experiments/sarol-2024/optimizer/context/playbook.md` — the iteration procedure and standing
  decisions.
- `experiments/sarol-2024/optimizer/context/task-and-scoring.md` — the metric and the known
  failure modes.
- `experiments/sarol-2024/optimizer/context/release-format.md` — what the release does and does
  not contain.
- `experiments/sarol-2024/optimizer/meta-learnings.md` — what previous iterations established,
  and where you record this one. Append to it when you finish.

## The objective

**Maximize macro-F1 over the six measurable classes, on the held-out VAL split.** One number,
reported as `primary_metric` (`sarol_macro_f1_6class`).

The six are `ACCURATE`, `NOT_SUBSTANTIATE`, `CONTRADICT`, `OVERSIMPLIFY`, `MISQUOTE`, `INDIRECT` —
every class the dev split has enough gold to score. The other three are excluded because dev cannot
measure them (two have zero gold there; `ETIQUETTE` has three claims), not because they do not
matter. It is computed at 9-way resolution and renormalised over the objective classes present in
the batch, so **read `n_objective_classes_present` before comparing two numbers.**

Do not optimize micro-F1. For single-label multiclass it equals accuracy, and dev is 72.5%
ACCURATE — so a program that always answers ACCURATE and does no work scores micro **0.725** while
scoring **0.140** on the objective. A rising micro with a falling objective means you are making it
worse.

`macro_f1_3way` is also reported. It is the axis the published baselines use (MultiVerS 0.52,
GPT-4 4-shot 0.45) and is there for comparability, not to be optimized: it collapses five of your
six classes into one bucket, so it cannot see most of what you change.

## The output vocabulary — fixed, exactly nine

```
ACCURATE   OVERSIMPLIFY   NOT_SUBSTANTIATE   CONTRADICT   MISQUOTE
INDIRECT   INDIRECT_NOT_REVIEW   ETIQUETTE   IRRELEVANT
```

Collapse for the metric: `ACCURATE` → ACCURATE; `OVERSIMPLIFY` / `NOT_SUBSTANTIATE` /
`CONTRADICT` / `MISQUOTE` / `INDIRECT` → NOT_ACCURATE; `ETIQUETTE` / `INDIRECT_NOT_REVIEW` /
`IRRELEVANT` → IRRELEVANT.

You may not add, remove, or rename a label. `AMBIGUOUS` is **not** in this vocabulary — it is a
workflow flag elsewhere in the tool and is never a verdict. An out-of-enum label is charged as a
miss and counted under `invalid_label`; it will not crash, it will just cost you.

## CAN / CANNOT

**You CAN edit** — and the list depends on this run's **profile**, which is named in your release
payload as `corpus.profile`. Read it there; do not assume.

| File | What it controls | `retrieval` | `agentic` / `paperclip` |
|---|---|:--:|:--:|
| `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` | verdict assignment | ✅ | ✅ |
| `experiments/sarol-2024/specs/verdict_schema_sarol.md` | rubric guidance: class definitions, boundaries, examples, tie-breaks, rollup order, multi-citation handling | ✅ | ✅ |
| `src/prompts/extractor-dispatch-paperclip.md` | evidence retrieval, in-corpus read path | ❌ | ✅ |
| `src/prompts/extractor-dispatch-pdf.md` | evidence retrieval, fetched-PDF read path | ❌ | ✅ |
| `src/prompts/verifier-dispatch.md` | evidence spot-check | ❌ | ✅ |

Under `retrieval` the extractor and verifier **never run** — the evidence envelope is produced
mechanically (BM25 top-20 over the cited paper's chunks) before your judge sees it. Editing a file
that is never read spends an iteration and moves no number.

You may reorder the worst-wins strictness ladder in that rubric — the validator reads the ladder
from your file and holds the program to whatever order you declared. Keep it in a fenced block
listing all nine labels separated by `>`, strongest first; if it cannot be parsed, every claim in
the run fails `ROLLUP_ORDER_UNPARSEABLE`.

⚠ **Check whether reordering it can move anything before you spend an edit on it.** The rollup
only differs from the sub-verdict when a claim decomposes into **more than one** sub-claim. In the
2026-09-02 run, all 50 TRAIN claims produced exactly **one** sub-claim each, so the rollup was the
identity function and any reordering would have moved nothing.

That is itself the interesting finding, and a live target: on at least 5 of those 50 the judge's
own prose named two propositions — *"both halves of the citing sentence"*, *"the morbidity
conjunct"* — while still emitting a single sub-claim. The claims decompose; the judge is not
decomposing them. Getting it to is a real edit with a real mechanism behind it. Reordering a
ladder it never consults is not.

**You CANNOT edit** — three frozen contract files:

`experiments/sarol-2024/specs/verdict_enum_sarol.md` · `src/specs/verdict_schema.md` ·
`src/specs/verifier_results.md`

These are re-hashed against the frozen manifest after your edit pass. Touching one fails the
iteration outright — before anything is scored or committed. Your work for that iteration is lost.
Do not test this.

**You CANNOT reach** VAL or TEST claim records or gold labels. They live outside the repository
tree entirely. There is nothing to find; attempts are logged and a denied-call threshold pauses
the run.

**You CANNOT** commit, tag, or run the pipeline yourself. The harness does that. You edit files and
exit.

## The experiment loop

1. **Read the release before touching anything.** It is at `iter/<n>/release_train.json` and
   `iter/<n>/release_val.json`, where `<n>` is the iteration number given in your turn prompt.
   On iteration 1 there is no prior number —
   `program-v0` has never been scored. The first release is the first evidence that exists.
   Establish the baseline before you react to it.
2. **Name one failure class.** Not "the adjudicator is imprecise" — a class, with instances you can
   point at in the TRAIN corpus.
3. **Form one hypothesis** about the mechanism.
4. **Make the smallest edit that tests it.** A large edit that improves the score teaches you
   nothing about which part of it worked, and you cannot afford to re-derive that later.
5. **Predict.** Write which verdict classes should move and in which direction, into
   `experiments/sarol-2024/optimizer/meta-learnings.md`. Nothing scores your prediction back to you automatically — you check it
   yourself next iteration by reading `per_class_f1` / `per_class_f1_9way` in the new TRAIN
   release against what you wrote. Doing that check is what makes an iteration a test rather than
   a guess, so it is on you to do it.
6. **Append to `experiments/sarol-2024/optimizer/meta-learnings.md`**: what you changed, what you predicted, whether the *previous*
   iteration's prediction held, and anything you deleted. That file is the only artifact that
   carries your reasoning forward — there is no separate change note.

## Simplicity criterion

Prefer the simpler program when scores are within noise. Prompt length is a cost: it raises
per-claim tokens, slows every run, and makes the next failure harder to localize. If an edit adds
30 lines of rubric guidance for +0.003 macro-F1, it is not an improvement.

When you delete something, say so in `experiments/sarol-2024/optimizer/meta-learnings.md` — a shrinking prompt that scores the same
is a genuine result and is easy to mistake for a lost edit.

## Per-claim budget

Each claim costs one nested session under `retrieval`, three under `agentic` / `paperclip` — the
**profile** decides, and nothing you write can change it. Under `retrieval` the Runner dispatches
exactly one session per claim regardless of what the rubric says, so there is no compute to buy
and no ceiling for you to hit: you cannot trade tokens for score on this rung even if you try.

(A 1.5× per-claim call-count ceiling is specified for Phase 2, where `agentic` / `paperclip` let
an edit change how many stages run. It is not enforced under `retrieval` because it cannot be
reached. Do not budget around it here.)

## The round-trip canary

Every run processes one pinned canonical claim with a known expected verdict before any scored
claim. If its verdict changes, the run stops. A run with no pinned canary refuses to start at all,
unless it was launched with an explicit `--no-canary` waiver.

⚠ **You cannot currently observe canary state from the release** — it carries no canary field. So
you will not see a canary *pass*; you will only ever see the run stop. Do not read the absence of
a canary message as evidence that one fired. (In the 2026-09-02 run no canary fired at all and
nothing said so; the refuse-to-start behaviour above is the repair.)

If you see a canary failure: **stop and report it. Do not edit around it.** It means the pipeline
or the scorer moved, and every number after the break is uncomparable to every number before it. A
silently broken metric invalidates all subsequent iterations, not just the current one. This is the
most expensive failure available to you and it is invisible unless you respect the stop.

## Crash handling

- **A stage errored or timed out** → an infrastructure signal, not a program signal. Report it;
  do not edit prompts in response.
- **`scored: false` in the release** → the `primary_metric` is a placeholder, not a result. Read
  `reason`. Do not treat it as a regression.
- **Your edit broke the output schema** → the exit validator rejects the file and the claims score
  as misses. Fix the edit; do not adjust the validator, which you cannot reach anyway.
- **The score regressed and you still believe the direction is right** → say so explicitly in
  `experiments/sarol-2024/optimizer/meta-learnings.md`, with your reasoning. Be aware that this is a note to your future self and
  to a human reader, not a signal to the engine: this consumer does not currently forward a
  step-back declaration, so declaring one neither protects the edit nor triggers a revert. Write
  it because the next iteration needs to know why the number moved, not because it buys anything.

## Output discipline

Do not print the mistake corpus, prompt files, or release JSON back into your output. Quote the
minimum needed to make a point — a single evidence snippet, a single verdict line. Your session's
token usage is the one budget the engine does enforce, and flooding it with material already on
disk is how a run ends early with nothing to show.

## Never stop early

Work the full iteration. If your first hypothesis collapses on inspection, form a second rather
than ending the session with no edit. An iteration that makes no change still costs a full
TRAIN+VAL+probe sweep — **VAL is charged twice, current and probe, on top of TRAIN** — so at
TRAIN=10 with VAL=50 that is ~113 nested sessions, and it scales with VAL. A wasted iteration is
expensive even though it looks free from inside your session.

If you genuinely believe no edit is warranted, say why in `experiments/sarol-2024/optimizer/meta-learnings.md` explicitly. That is
a result. Silence is not.
