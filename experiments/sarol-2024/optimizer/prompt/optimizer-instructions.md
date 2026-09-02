# Optimizer instructions

You are optimizing a citation-integrity pipeline against a human-annotated benchmark. This file is
your standing instruction set; it is injected every iteration. Structure follows Karpathy's
`program.md` (autoresearch, 2026), adapted to this task.

## Setup

The program is up to three prompt-driven stages — **extractor** → **adjudicator** → **verifier** —
run
once per citation instance. Given a citing sentence and one paper it cites, it emits one verdict
from a fixed nine-label vocabulary.

Your job each iteration: read the release, form one hypothesis about a failure class, make the
smallest edit that tests it, and record what you predicted.

Read these before your first edit:

- `context/playbook.md` — the iteration procedure and standing decisions.
- `context/task-and-scoring.md` — the metric and the two known failure modes.
- `context/release-format.md` — what the release does and does not contain.
- `meta-learnings.md` — what previous iterations established. Append to it when you finish.

## The objective

**Maximize 3-way macro-F1 on the held-out VAL split.** One number.

Do not optimize micro-F1. For single-label multiclass it equals accuracy, and gold is 78.1%
ACCURATE — so a program that always answers ACCURATE scores micro 0.781 and macro 0.292. A rising
micro with a falling macro means you are making it worse.

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

1. **Read the release before touching anything.** On iteration 1 there is no prior number —
   `program-v0` has never been scored. The first release is the first evidence that exists.
   Establish the baseline before you react to it.
2. **Name one failure class.** Not "the adjudicator is imprecise" — a class, with instances you can
   point at in the TRAIN corpus.
3. **Form one hypothesis** about the mechanism.
4. **Make the smallest edit that tests it.** A large edit that improves the score teaches you
   nothing about which part of it worked, and you cannot afford to re-derive that later.
5. **Predict.** Write which verdict classes should move and in which direction. The next release
   reports exactly those, but only because you named them.
6. **Append to `meta-learnings.md`**: what you changed, what you predicted, and — for the previous
   iteration — whether the prediction held.

## Simplicity criterion

Prefer the simpler program when scores are within noise. Prompt length is a cost: it raises
per-claim tokens, slows every run, and makes the next failure harder to localize. If an edit adds
30 lines of rubric guidance for +0.003 macro-F1, it is not an improvement.

When you delete something, say so in the change note — a shrinking prompt that scores the same is
a genuine result and is easy to mistake for a lost edit.

## Per-claim budget

Each claim costs one nested session under `retrieval`, three under `agentic` / `paperclip` — the
profile decides. The per-claim budget is a fixed **model-call count**
(deterministic, so it is the primary bound), with wall-clock as secondary. Ceiling: **1.5×
`program-v0`'s per-claim call count.**

You cannot buy score with compute. An edit that pushes a claim past the ceiling is rejected the
same way a broken edit is. If you believe a stage genuinely needs another call, say so in the
change note and argue it — do not just take it.

## The round-trip canary

Every run processes one pinned canonical claim with a known expected verdict before any scored
claim. If its verdict changes, the run stops.

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
- **The score regressed and you still believe the direction is right** → say so explicitly in the
  change note. A declared step-back is tolerated and can be reverted. An **undeclared** regression
  is never reverted, so staying quiet costs you the ability to back out.

## Output discipline

Do not print the mistake corpus, prompt files, or release JSON back into your output. Quote the
minimum needed to make a point — a single evidence snippet, a single verdict line. Your session's
token usage is the one budget the engine does enforce, and flooding it with material already on
disk is how a run ends early with nothing to show.

## Never stop early

Work the full iteration. If your first hypothesis collapses on inspection, form a second rather
than ending the session with no edit. An iteration that makes no change still costs a full
TRAIN+VAL+probe sweep — roughly 1,900 nested sessions at VAL=316 — so a wasted iteration is
expensive even though it looks free from inside your session.

If you genuinely believe no edit is warranted, say why in the change note explicitly. That is a
result. Silence is not.
