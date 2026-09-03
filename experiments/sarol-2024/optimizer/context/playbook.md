# Playbook — how one optimization iteration runs

Reference doc for the optimizer agent. This is the procedure; `experiments/sarol-2024/optimizer/context/task-and-scoring.md` is what
counts as better, and `experiments/sarol-2024/optimizer/context/release-format.md` is what you get handed each iteration — both beside this
file in `experiments/sarol-2024/optimizer/context/`. **Every path in this document is relative to
your working directory, which is the repository root.**

Where this file and `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md` cover the same ground, the standing
instructions are authoritative and this file points rather than restates.

Most of what follows is not new. The Sarol experiment settled these questions in April 2026 and
this file ports those decisions forward to the engine's concrete shape rather than re-deciding
them. Where a decision has an identifier (D22, D26, …) it refers to
`docs/plans/experimental-plan-of-record.md`'s decision log.

## The shape of an iteration

One iteration is five steps. The engine (`agentic-label-opt`) drives all of them; you are step 3.

1. **Score the current version.** The dispatcher runs the frozen program over the TRAIN batch and
   over VAL, and scores both.
2. **Build the release.** TRAIN gives you full per-example traces plus aggregates; VAL gives you a
   scalar and its breakdown, nothing else. See
   `experiments/sarol-2024/optimizer/context/release-format.md`.
3. **You edit the program.** One pass. You may edit only the files in the EDIT scope (below).
4. **The harness commits and tags** the result as a new version. You never commit.
5. **The harness re-runs the frozen version against VAL** to confirm it still works, then the next
   iteration begins.

## What you may and may not touch

**EDIT — and the list depends on which profile this run is on.**

A run's *profile* fixes which stages actually execute, and you may only edit a stage that runs.
The profile is named in your release payload (`corpus.profile`) and in the run manifest; if you are
unsure which one you are on, read it there rather than assuming.

**Under `retrieval` (Phase 1) — two files:**

- `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` — verdict assignment
- `experiments/sarol-2024/specs/verdict_schema_sarol.md` — the rubric *guidance*: class
  definitions, boundaries, worked examples, tie-breaks, the worst-wins rollup order,
  multi-citation handling. Improving this is much of the point.

**Under `agentic` / `paperclip` (Phase 2) — those two, plus three more:**

- `src/prompts/extractor-dispatch-paperclip.md`
- `src/prompts/extractor-dispatch-pdf.md`
- `src/prompts/verifier-dispatch.md`

**Why the narrowing, and why it is not arbitrary.** Under `retrieval` there is no extractor
session at all: the evidence envelope is written mechanically by BM25 top-20 over the cited
paper's chunks, before your judge ever runs. Editing an extractor prompt would therefore change
nothing measurable — the file is never read — while still producing a new version, a new tag and a
wasted iteration. The experiment on this rung is "how good can the judge get at a *fixed* evidence
budget", so the judge and its rubric are the whole surface.

**One mechanical constraint on the rubric.** The exit validator enforces that every
`overall_verdict` is the worst-wins rollup of its sub-claims, reading the ladder *from your rubric*
rather than hard-coding it. Do not break the fenced block it lives in: the validator needs one
fenced code block containing all nine labels separated by `>`, strongest first, or every claim in
the run fails `ROLLUP_ORDER_UNPARSEABLE` — it fails closed, because an unenforceable rule is not
the same as an inapplicable one.

⚠ Before spending an edit on the ladder, read the ladder note in
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`: the rollup is currently the
identity function, because the judge emits exactly one sub-claim per claim.

**READ-ONLY — three contract files, frozen:**

- `experiments/sarol-2024/specs/verdict_enum_sarol.md` — the 9 emittable labels and the 3-way
  collapse. The benchmark defines these and the scorer consumes them.
- `src/specs/verdict_schema.md` — the output *structure*.
- `src/specs/verifier_results.md` — the verifier's contract of record.

This is enforced, not merely requested. The adapter re-hashes all three against the frozen
manifest after your edit pass; a modified contract file fails the iteration before anything is
scored or committed. The engine's own `contract_file` flag checks presence only, so this
consumer-side check is the entire guarantee.

**SEALED — you cannot reach these at all:**

VAL and TEST claim records and their gold labels live outside the repository tree
(`$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR`). There is no in-repo directory to be
denied access to, which is a stronger guarantee than a filesystem permission. Do not attempt to
locate them; attempts are logged to the audit ledger and a denied-call threshold pauses the run.

## Standing decisions you do not need to relitigate

- **Agent-only, no human in the loop (D22).** No one is going to review your edit and approve it.
  The loop is the reviewer: a bad edit scores worse and gets dropped.
- **The dispatcher is a Python script, not an agent (D26).** All orchestrator-runtime decisions —
  verifier sampling, retry, bounce, schema validation — are static code, not runtime judgement.
  This is what makes a retrospective re-run of version N reproducible.
- **Invocation is uniform across TRAIN and VAL (D27/D28).** The same subagent, the same headless
  invocation; only the dispatcher's routing of the output differs. TRAIN's output comes back to
  you in full, VAL's is reduced to a scalar before you see it. Do not infer anything from a
  difference in how a split was run, because there isn't one.
- **The topology is fixed for v0.** Extractor → adjudicator → verifier. You edit prompt content,
  not pipeline shape. Revisit once a v0 curve exists. (Recorded because the sibling
  crc-extraction-agent effort resolved the same fork the other way; the divergence is
  deliberate, not an oversight.)
- **The output vocabulary is fixed; the guidance is not.** You may not add, remove, or rename a
  label. An out-of-enum label is not a crash — it is charged as a miss and counted in
  `error_class_counts`, so an edit that wanders outside the vocabulary simply scores worse.

## Warm start: iteration 1 establishes the baseline, it does not characterize it

This matters and is easy to get wrong. **`program-v0` has no measured score.** Nothing has been
run against it. There is no published number for paper-trail on this benchmark, and the two
comparison points that do exist — MultiVerS at 0.52 macro-F1, GPT-4 4-shot at 0.45 — are other
systems, not earlier versions of this one.

So iteration 1's job is to *produce* the first real number, not to react to one. Do not open by
proposing fixes to a failure mode you have not seen; the first release is the first evidence
anyone has. Read it before you edit. From iteration 2 onward you have a real prior and the normal
loop applies.

## Per-claim budget

Cost per claim follows the profile: **one** nested Claude Code session under `retrieval` (the
adjudicator alone), **three** under `agentic` / `paperclip`. The profile fixes this and no edit of
yours can change it, so on the `retrieval` rung there is no compute to buy. See the per-claim
budget section of `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md` for the
Phase 2 ceiling and why it does not apply here.

## The round-trip canary

Every run begins by processing one pinned canonical claim whose expected verdict is known, before
any scored claim runs. If the canary's verdict changes, the run stops: something about the
pipeline or the scorer moved, and the numbers from that run are not comparable to earlier ones.

This exists because a silently-broken metric is the most expensive failure mode in this kind of
work — it is invisible, and it invalidates every iteration after the break, not just the current
one. Treat a canary failure as a stop, never as noise to retry through.

⚠ The release carries no canary field, so you can never observe a canary *pass* — only the stop.
Do not read silence as confirmation.

## What to do each iteration

1. Read the release. TRAIN traces first, then the aggregate, then the frontier line.
2. Form one hypothesis about *why* a class of claims is being misjudged. Name the class.
3. Make the smallest edit that tests it. A large edit that improves the score teaches you nothing
   about which part worked.
4. Write what you changed and what you expected into `experiments/sarol-2024/optimizer/meta-learnings.md`, naming the verdict
   classes you were targeting. Nothing reports that movement back to you automatically — you read
   `per_class_f1` in next iteration's TRAIN release against what you wrote. Naming the classes in
   advance is what makes that check meaningful.
5. If the score regressed and you believe the direction is still right, say so explicitly in
   `experiments/sarol-2024/optimizer/meta-learnings.md`, with the reasoning. Note that this consumer does not forward a step-back
   declaration to the engine, so it neither protects the edit nor triggers a revert — write it for
   the next iteration's reader, which is you.

## Continuity

`experiments/sarol-2024/optimizer/meta-learnings.md` beside this file carries what previous iterations established: confirmed
fixes, pending hypotheses, and reverted attempts with the reason. Read it before iterating and
append to it after. It is the only memory that survives between sessions — each iteration runs in
a fresh session with no recollection of the last one, deliberately (a retrospective evaluation of
version N has to be blind to everything learned after N).
