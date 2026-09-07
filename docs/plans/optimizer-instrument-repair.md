Reference: docs/claude_ops.md

# Optimizer prompt consistency — switch the objective to accuracy, and make the instruction set say one thing

**Status: Implemented** (2026-09-07). Both slices landed on the branch; 433/433 offline gates green,
every new guard negative-controlled. `Reviewed: No` — not yet read by Phil, and not yet `/land`ed.
**Branch.** `sarol-optimizer-impl` (worktree `.claude/worktrees/optimizer-impl`).

**Two decisions taken during implementation, both recorded because they are not what the plan's
text literally said:**

1. **S23 resolves to 9-way accuracy** (`pred_label == gold_label`), not the 3-way `correct / scored`
   the Verification section named. The plan was internally inconsistent: S25 says within-bucket
   confusions are "plainly errors ... under an accuracy objective", which is only true at 9-way
   resolution. Under 3-way the optimizer would have been shown mistakes it could not be rewarded
   for fixing. Confirmed with Phil before implementing. The 0.595 floor is identical either way.
2. **S13's trace gap resolves by putting `trace_ref` on the mistake rows**, the first of the two
   options the item offered, rather than deleting step 5 of the brief. Deleting it would have
   removed a capability the discovery fan-out depends on; the path was already being written to the
   run manifest, so surfacing it cost four lines.

**The canary is now pinned** (2026-09-07, after the Codex audit): claim `1969-64` under
`claude-haiku-4-5`, **3/3 observations agreed** on `ACCURATE`, recorded against
`program_combined_hash 0a02710cbd88` — which independently confirms the re-freeze reached a live
dispatch. That was the first end-to-end exercise of staging → BM25 evidence → headless judge →
parse → validate; every other check in this plan is offline. `run_optimization` no longer refuses
for canary reasons (it now refuses on budget, the next guard in line).

⚠ **The pin file is deliberately UNCOMMITTED.** `canary-<profile>.json` is meant to be committed
(the `.gitignore` says so), but the payload embeds an absolute `staging_dir` under the author's home
directory and **this repo is public**. The path carries no information — it is always
`canary/staging/<profile>/<claim_id>` — so the fix is to record it repo-relative in `canary.py`
(`:235`, `:295`) and resolve it against `repo_root` on load (`adapter.py:547`). Do that, re-pin or
hand-edit the field, then commit. Until then the pin works on this machine and nowhere else.

## Goal

**Improve the optimizer, not the program it optimizes.**

There are two layers here and they have been getting blurred:

- **The labeling PROGRAM** — the adjudicator prompt and the rubric it follows. This is *what gets
  optimized*. Its starting quality does not matter much: a null-state program is a fine starting point,
  because improving it is the optimizer's entire job.
- **The OPTIMIZER machinery** — the optimizer's own instructions, its subagent brief, the context docs
  it reads, and the loop that runs it. This is *what does the optimizing*, and **it has to be right
  before we start**. A good optimizer will lift a bad program. A bad optimizer guarantees nothing, and
  we will not be able to tell which of the two failed.

So the deliverable is a **correct optimizer machinery and a clean, documented separation between the
two layers.** Hand-tuning the program is explicitly out of scope — see *What we deliberately do not
touch* below.

### The seam, and how it is defined

The separation already exists in code, which gives a crisp test rather than a judgment call:
**the manifest defines the program; everything else is machinery.** `commit_new_version` stages only
manifest entries (`agentic-label-opt/engine/versioning.py:92-95`), so an edit outside the manifest is
not part of any `program-v<n>`.

| | Files | Who edits it |
|---|---|---|
| **Program, editable** | `prompts/adjudicator-dispatch-sarol.md`, `specs/verdict_schema_sarol.md`, plus the 3 extractor/verifier prompts (inert under `retrieval`) | **The optimizer.** Not us. |
| **Program, frozen** | `specs/verdict_enum_sarol.md`, `src/specs/verdict_schema.md`, `src/specs/verifier_results.md` | Nobody, during a run. Humans between runs. |
| **Machinery** | `optimizer/prompt/`, `optimizer/context/` (6 docs), `optimizer/findings/`, `meta-learnings.md`, and the Python | **Us.** This plan. |

The profile narrows the program further at run time: under `retrieval` only the adjudicator and the
rubric are live, so the three extractor/verifier prompts are editable-but-inert.

**One file is currently neither**, and that ambiguity is itself a finding:
`specs/verdict_definitions_sarol.md` is in **no** manifest entry, and the judge never loads it
(`adjudicator-dispatch-sarol.md:21-22` loads only the enum and the rubric — "Nothing else"), yet four
machinery docs describe it as the judge's operative definitions. Resolving which side of the seam it
sits on is S21.

## The metric: accuracy

**`primary_metric` becomes overall accuracy.** It is already computed —
`score_sarol3.py:192` is literally `correct / scored`, and the module's own comment says
*"micro == accuracy here"*. So this is a change of which number is the objective, not new maths.

Why this is the right call, briefly:

- **It removes the drift that made the first run unreadable.** Macro-F1 renormalises its denominator
  over whichever classes land in the batch, so a batch that draws more rare classes scores lower for
  free. That is what manufactured the −0.15 TRAIN decline across the first three iterations for a
  program that never changed. Accuracy has no denominator to wobble.
- **It makes batches comparable** regardless of composition, which is the property a hill climb needs.
- **It costs nothing.** No AUROC, no ranked output, no schema change.

**The one real cost, on the record.** Accuracy is dominated by the common classes. Gold is 59.5%
ACCURATE on the repaired dev pool, so a program that always answers ACCURATE and does no work scores
**0.595**. That is a floor to quote, not a trap — compare against 0.595, never against zero. But it
does mean rubric work on the rare classes (MISQUOTE and INDIRECT have 6 dev instances each) will barely
move the number, and the optimizer will not be rewarded for it.

**So:** accuracy is the objective; the 0.595 do-nothing floor is quoted beside it every time; macro
stays **reported as a diagnostic** — purely so a gain that came from collapsing toward ACCURATE is
visible rather than invisible.

### What this decision deletes

- **TRAIN stratification is now the wrong move**, and comes off the plan. Under accuracy you want TRAIN
  to look like the population the score is computed over. Stratifying would show the optimizer a class
  balance it is not scored on.
- **VAL stratification becomes wrong for the same reason** and has to be turned off — `val_inputs_for`
  currently defaults `stratify=True` (`sampling.py:558-559`). Accuracy on a stratified VAL is not the
  population accuracy. This is a one-line default flip, justified by the metric choice.
- **The renormalising-denominator arguments** throughout the docs stop applying and must come out.

### What it breaks that must be rewritten, not deleted

`score_sarol3.py`'s selftest encodes *"micro must not be the objective"* as an invariant, in at least
four gates: `:234` (do-nothing micro is degenerate), `:239-240`, `:241-242` (`primary_metric < micro_f1`),
`:276-278`. Those assert the old choice. Replace them with gates asserting the new one — that
`primary_metric` equals `correct / scored`, and that the do-nothing floor is reported alongside it —
rather than dropping them and leaving the choice unguarded.

## Decisions taken (Phil, 2026-09-07)

| Was | Decision |
|---|---|
| Baseline: pristine v0 or current v3 tree? | **Pristine `v0`.** |
| Rename `sarol_macro_f1_6class`? | **Yes** — and it now renames to an accuracy metric, not a macro one. |
| One edit per iteration, or joint? | **As many edits as the agent wants.** No separability constraint. |
| Wire the audit ledger, or delete the claim? | **Delete it.** VAL isolation *is* by construction — the records live outside the repo tree. |
| Reset `meta-learnings.md`? | **Reset.** |
| Keep the subagent fan-out? | **Keep it; the agent sizes it.** Matters at higher sample; no hard gate. |
| No-op control arm? | **No.** |
| TEST evaluation? | **No — deferred.** |
| Noise-floor replicates? | **Dropped.** |

---

## What we deliberately do not touch

Program-side quality is the optimizer's job, and hand-fixing it would be worse than leaving it alone:
it spends our time on work the loop is supposed to do, and it **conflates our edits with the
optimizer's** on any curve we then produce. The null-state program is the control.

So these stay broken on purpose, for the optimizer to find:

- The ETIQUETTE self-contradiction inside `verdict_schema_sarol.md` (one line restricts it to
  undecidable attribution, a later one makes it the general fallback for any undecidable verdict).
- The CONTRADICT gloss drift between the rubric and the adjudicator prompt, including the
  "requires a verbatim opposing excerpt" clause that appears in only some copies.
- Every other rubric-quality question: sufficiency thresholds, boundaries, worked examples, tie-breaks.

**Three narrow exceptions**, none of which are quality edits:

1. **A broken seam** — the duplicate strictness ladder. `validate_sarol.parse_rollup_order` reads the
   ladder from the **rubric**, while the judge follows a second copy in
   `adjudicator-dispatch-sarol.md:48`. An optimizer that reorders the rubric's ladder is silently
   disobeyed by the judge and then fails validation for it. That is machinery breaking the program, not
   program quality (S9).
2. **A frozen program file — anything the optimizer cannot reach.** "Leave it for the optimizer" is
   only an option for files the optimizer can edit. A frozen contract that states something false
   (`verdict_enum_sarol.md:44-46` calls 3-way macro the frontier, S3) or that wastes the judge's context
   on engineering history (S20) will never be fixed by the loop, so it is ours. **These land before the
   baseline is cut, never mid-run** — they change the program.
3. **Restoring the tree to pristine `v0`** before the run, per the baseline decision. That is resetting
   the program to its null state, not improving it.

## Slice 1 — optimizer machinery (the ask)

Every item is a doc asserting something the code does not do, or two docs disagreeing. All verified
against code; evidence named so a fresh agent can re-check rather than trust.

### Document the seam (do this first)

- **S0. State the program/machinery separation as a durable artifact.** Written this session as
  `experiments/sarol-2024/optimizer/README.md` — the two layers, the manifest-is-the-seam rule, who
  edits what, why we do not hand-tune the program, and the one file that currently sits on neither
  side. Human-facing; deliberately **not** injected into any agent's context.
- **S0b. Make the agent-facing half match it.** `context/edit-surface.md` is the optimizer's version of
  the same boundary. It needs the "what the judge actually sees" block (S12c) and the manifest rule
  stated as the definition rather than as one input among several.

### The objective, restated everywhere

- **S1. Invert the micro-F1 guidance.** This is the largest single edit. `task-and-scoring.md` has a
  section headed *"Micro-F1 is reported. It is not the objective, and it is a trap"*; the prompt tells
  the agent a rising micro with a falling macro means it is making things worse. Under the new
  objective that reads exactly backwards. Replace with: accuracy is the objective, 0.595 is the
  do-nothing floor, macro is the diagnostic that shows whether a gain came from collapsing to ACCURATE.
- **S2. Rename the metric key** and update every doc that names `sarol_macro_f1_6class`.
- **S3. Fix the frontier statement.** `release-format.md:64` and `verdict_enum_sarol.md:44-46` say
  3-way macro is the frontier. The enum file is a frozen contract — human fix between runs.
- **S4. Fix the six-class payload examples.** `release-format.md:28-29` and `:173-174` show
  `objective_class_set` with six members. Under accuracy the whole field is less load-bearing, but the
  examples still misdescribe what the scorer emits.
- **S5. One calibration table, labelled with its pool.** `task-and-scoring.md` gives two do-nothing
  baselines fifteen lines apart from different fixtures, neither labelled (0.093/0.595/0.249 vs
  0.097/0.292). Under the new objective the number that matters is **0.595**, and it should be stated
  once, prominently, with its pool named.
- **S6. Reset `meta-learnings.md`** (Phil). 620 lines injected every iteration, denominated entirely in
  the retired axis, and carrying an iteration-4 target that is wrong on inspection.

### The agent is told things that are false

- **S7. Delete the audit-ledger claim.** `edit-surface.md` and `subagent-blame-brief.md` both promise
  that reaching for held-out gold is "logged to the audit ledger, and a denied-call threshold pauses the
  run". `audit_ledger` and `policy_config` appear **zero** times in `dispatcher.py`. Per Phil: isolation
  is by construction — the records live outside the repo tree — so say that.
- **S8. Fix the step-back contradiction.** `attempting_step_back` is hard-coded `False`
  (`dispatcher.py:445`, `adapter.py:1313/1349`), so the loop is forward-only and every edit, including a
  regressing one, becomes the next base. `playbook.md:53` says "a bad edit scores worse and gets
  dropped", filed under decisions not to relitigate.
- **S9. Fix the ladder hazard — documented backwards.** `edit-surface.md` warns an unparseable fenced
  block fails closed. `validate_sarol.parse_rollup_order:162-170` walks **every** fenced block and
  returns the **first** covering all nine labels, never requiring `>`. The real hazard is a silently
  wrongly-parsed earlier block — and the docs invite worked examples. **There is also a second ladder**
  at `adjudicator-dispatch-sarol.md:48`, which is what the judge follows while the validator reads only
  the rubric's.
- **S10. Fix the canary claim.** "You cannot observe a canary pass" is false — `dispatcher.py:865`
  writes a `canary` record into the run manifest. The only state that has ever occurred (`null`) has no
  prescribed handling.
- **S11. Add a missing-release recipe.** All three iterations landed in the one case no doc covers, and
  each reinvented the same reconstruction.

### The loop has functional holes (from the two role-play agents)

These are places the instruction set did not *work*, found by running it rather than reading it.

- **S12a. The brief is not self-contained, and says it is.** It opens *"This document is your whole
  brief… you do not need any context beyond this file"*, then contradicts that 25 lines later. The real
  gap: the `rubric` blame category asks whether the guidance pointed the judge wrong, and the brief
  names only `verdict_definitions_sarol.md` — never `verdict_schema_sarol.md`, which *is* the rubric.
  The role-playing subagent opened it anyway and reported that four of its five mechanism sentences
  would otherwise have been the worthless outcome-restatements the brief warns against. **Add the
  rubric path, make the read unconditional, and drop the false self-containment claim.** This adds a
  *pointer* to the rubric from a machinery doc — it does not edit the rubric, which stays the
  optimizer's.
- **S12b. Predictions are written to a file nothing reopens.** Phase 4 writes them to
  `findings/iter-<n>.md`; no doc tells iteration *n+1* to open `iter-<n-1>.md`. `findings/README.md`
  says the directory is "consulted on purpose" and `meta-learnings.md` says "that one is not" read every
  iteration. The prediction check the prompt calls the point of the whole loop is open at both ends.
  **Phase 4 should open with "read `findings/iter-<n-1>.md`".**
- **S12c. No doc says what is in the judge's context window.** The optimizer's whole job is editing the
  judge's guidance, and nothing states that the adjudicator loads exactly the enum, the rubric and the
  evidence JSON — and nothing else. The cold review called this the cheapest high-value addition
  available. **Add a three-line "what the judge sees" block to `edit-surface.md`.**
- **S12d. Nothing covers "the previous edit was never scored."** All three iterations landed there.
- **S12e. Promote the best rule in the corpus.** *"When adding a rubric rule, name the test that decides
  its terms, or the judge will supply one that reaches whatever verdict it already prefers."* It was
  learned twice at the cost of two iterations and sits at line ~618 of a 620-line file that is about to
  be reset. Move it into the standing instructions before the reset deletes it.

### Principles stated without an actionable rule

- **S12f. "A mode with one instance is an anecdote"** gives the bottom of the scale and nothing else.
  The role-play agent had three modes at n=2 and had to guess. Give a usable rule or drop the framing.
- **S12g. "Prefer the simpler program when scores are within noise"** — noise is undefined, and since
  measuring it is now dropped, this needs a rule of thumb or deletion rather than a forward reference.
- **S12h. The dollar cap is never stated** while the agent is told to size its fan-out against it.
  Either surface the cap in the turn prompt, or replace the instruction with a concrete default.
- **S12i. "Spawn subagents to read failures one example at a time"** is ambiguous — one example per
  subagent, or one at a time within a slice? The prompt and `failure-mode-discovery.md` read differently.

### The subagent brief does not survive contact with its own input

- **S12. Fix the hand-off contradiction.** The prompt says hand the subagent "exactly two things"; the
  brief opens saying it was handed claim ids *and a corpus path*. Also pass the profile — the brief
  hard-codes one profile's behaviour as "this pipeline".
- **S13. Repair the brief against real data.** `adjudicator_reasoning.nuance` is a JSON **array**, not
  prose; `remediation.suggested_edit` is present, undocumented, and was the most useful field the
  role-playing subagent had; step 5 points at a `trace_ref` the subagent cannot reach, which induces the
  tree-searching the same doc forbids. Add a per-field fallback and one worked record from a real claim
  instead of the invented `C042`. The trace gap is a binary: put the reference on the mistake rows, or
  delete step 5.
- **S14. Add a seventh blame category — judge execution error.** `rubric` conflates "the guidance is
  wrong" with "the guidance is right and the judge ignored it", which imply opposite edits. Also drop
  "rare" from the `gold` category — it demonstrably broke a tie the evidence did not.
- **S14a. Fix the IRRELEVANT causal error in `task-and-scoring.md`.** *"That is why no run ever
  predicted IRRELEVANT: the program was never shown one"* — the program never sees gold labels, so the
  pool filter explains why IRRELEVANT was never *correct*, not why it was never *emitted*. As written it
  licenses the inference that a repaired pool will make the program start predicting IRRELEVANT, which
  does not follow. Machinery, so ours.
  *(The ETIQUETTE self-contradiction and the CONTRADICT gloss drift were previously listed here. Both
  are rubric quality — program-side — and now sit under* What we deliberately do not touch *instead.
  They are the optimizer's to find.)*
- **S14b. "Phase" means three different things** across the docs: the optimizer's four phases, the
  engine's five steps, the train/val split, and paper-trail's own product phases. Reserve the word.
- **S15. Fix the retrieval reach test.** `failure-mode-discovery.md` tells the optimizer to give up on
  retrieval-blamed modes under mechanical evidence — the only profile ever run — while two other docs
  call it the live target, and it is what iterations 2 and 3 spent themselves on.

### Structure and duplication

- **S16. Relax the separability language** (Phil: as many edits as it wants). Say plainly that edits are
  tested jointly and that is accepted.
- **S17. Let the agent size the fan-out** (Phil). Note it earns its keep as sample grows; no gate.
- **S18. Restructure the four phases.** Both role-play agents found the boundaries mis-cut: the Phase
  1/2 boundary decides nothing, checking last iteration's prediction has no home, and nothing owns
  "establish this iteration's numbers". Shape: **check last prediction → establish the batch → draw and
  fan out → cluster → edit → predict.**
- **S19. Deduplicate.** The findings-vs-meta-learnings rule appears in **six** files; one piece of advice
  in two, reworded; another in four. One owner per fact.
- **S20. Trim `verdict_enum_sarol.md`.** In the judge's context on every claim, and about half of it
  is repo engineering history — a "Binding to code" section telling an engineer to reconcile against
  `parse_verdict.py`, sitting in a classifier's window ~50 times per run.
  **Why this is ours despite being program-side:** "leave it for the optimizer" is only an option for
  files the optimizer can reach, and this one is frozen. Left alone it is a permanent handicap the loop
  can never lift, which is a different thing from a rubric defect the optimizer will find and fix.
  **Constraint:** it changes the program, so it lands *before* the baseline is cut, never mid-run.
- **S21. Resolve `verdict_definitions_sarol.md` — the file on neither side of the seam.** It is in no
  manifest entry, and the judge never loads it (`adjudicator-dispatch-sarol.md:21-22` reads only the
  enum and the rubric — "Nothing else"), yet four machinery docs call it the judge's operative
  definitions. Anything reasoning about it is reasoning about a document nothing reads.
  **The fix is machinery-side only:** correct those four docs, and either delete the file or mark it
  plainly as an optimizer-facing reference. **Do not touch the rubric's own copy of the definitions** —
  an earlier draft proposed de-duplicating them, but the rubric is the optimizer's file and its copy is
  the operative one. Once the unread file is resolved there is no duplication left to fix.
- **S22. Smaller, all verified**: `per_class_f1` is 3-bucket and cannot answer a 9-class prediction, yet
  two docs name it as the check; `release-format.md:72` says the manifest carries "no reasoning" while
  `:132` says it carries a transcript pointer; iteration cost is stated two ways and "probe" is never
  defined; `playbook.md:102` has the wrong antecedent; `edit-surface.md`'s table omits two frozen
  manifest entries; `task-and-scoring.md`'s failure modes are numbered 3,4,5,1,2 so a top-to-bottom
  reader absorbs superseded guidance before its correction; `sampling.py:22-23` still states the
  drawable pool as the pre-repair 1,699 / 255 figures.

### Keep these — they tested well

Not everything needs changing, and two things should be protected from the edits above.

- **The `mechanism` field instruction** ("name the step that produced the wrong answer, not the
  outcome", with a worked negative example) was called the best-written thing in the brief by the agent
  that had to use it. Do not dilute it while fixing the fields around it.
- **The `retrieval` vs `rubric` blame distinction** was defended as the one part of the discovery
  machinery that could not be replaced by reading the corpus directly — it separates a fixable defect
  from an unfixable one. Keep it, and fix S15 rather than collapsing the categories.

## Slice 2 — the code the metric change needs

Small, and all of it follows from the decision above.

- **S23. Make `primary_metric` accuracy** and report the do-nothing floor beside it. Rewrite the four
  selftest gates that encode the old choice (`score_sarol3.py:234, 239-240, 241-242, 276-278`).
- **S24. Turn off VAL stratification** — flip `val_inputs_for(stratify=...)` to default `False`
  (`sampling.py:558-559`), so accuracy estimates the population it claims to.
- **S25. Fix the corpus filter to 9-way** (`adapter.py:961`). It currently skips any claim whose 3-way
  buckets match, so within-bucket confusions are recorded as **correct**, hidden from the corpus the
  optimizer reads, and added to the `n_correct` the agent is told to read first. Under an accuracy
  objective those are plainly errors, and the optimizer cannot fix what it is never shown.
- **S26. A cheap tag guard.** `current_tag` is hard-coded `"program-v0"`
  (`dispatcher.py:598/940/1009/1135`) with no flag to set it, while the working tree differs from the
  manifest on both editable content files. Since the baseline decision is **pristine v0**, the tree gets
  restored before the run — so a start-up check that the tree matches the tag it names is worth the few
  lines.

## Deferred, with the reason

- **Noise floor / replicate runs** — dropped. Revisit only if a hill climb produces ambiguous moves.
- **No-op control arm**, **TEST evaluation** — no / deferred (Phil).
- **Per-edit attribution** and the paired A/B delta — follows from "as many edits as it wants".
- **TRAIN stratification** — actively wrong under accuracy. Reopens only if the objective changes back.
- **Engine-side fixes** — `_select_best` accepting placeholder 0.0s; a single failed probe claim killing
  a run via `LoopStop`. Both real, both cross-repo, neither blocking.
- **Bringing `/sarol-eval-item` and `CLAUDE.md` inside the freeze** — real, but not a prompt-consistency
  blocker.

## Files to Modify

**Docs (the deliverable)** — `optimizer/README.md` (**new**, the seam statement),
`prompt/optimizer-instructions.md`,
`context/{failure-mode-discovery,subagent-blame-brief,edit-surface,playbook,release-format,task-and-scoring}.md`,
`findings/README.md`, `meta-learnings.md`, `specs/{verdict_enum,verdict_definitions,verdict_schema}_sarol.md`

**Code (Slice 2)**
- `experiments/sarol-2024/scripts/score_sarol3.py` — accuracy as `primary_metric`; rewrite the four gates (S23)
- `experiments/sarol-2024/optimizer/sampling.py` — VAL stratify default (S24); stale module docstring (S22)
- `experiments/sarol-2024/optimizer/adapter.py` — 9-way corpus filter (S25); metric name (S2)
- `experiments/sarol-2024/optimizer/dispatcher.py` — tag guard (S26)
- `experiments/sarol-2024/optimizer/profiles.py` — extend the doc-gate corpus to every file Slice 1 touches

## Open Questions

None blocking. The metric is decided; the remaining judgment calls are inside items and named there.

## Verification

Everything runs on this machine (zero-PHI repo). Nothing in this plan costs money.

- **Offline gates, after each slice** — all seven optimizer modules plus `scripts/score_sarol3.py`.
  **Expected:** no FAIL. **Stop:** any regression that is not one of the four gates S23 deliberately
  rewrites — those must be *replaced*, and the replacement must fail if the objective is switched back.
- **S23** — `primary_metric` equals `correct / scored` on a fixture; the do-nothing always-ACCURATE
  program scores **0.595** on the repaired dev distribution and that number is reported beside it.
- **S24** — an unstratified VAL draw reproduces the population class balance within sampling error.
- **S25** — a fixture where labels differ but 3-way buckets match produces a mistake row **and** leaves
  `n_correct` unchanged. **Negative control:** the row is absent under the old comparison.
- **S26** — a tree differing from the tag it names refuses at start-up; a matching tree does not.
- **Slice 1** — extend the `profiles.py` doc-gate corpus to every file touched and
  **negative-control each new gate** (assert it fails when its fix is reverted). This session already
  shipped a gate that passed over three absent guards. Add a rendering check for broken list markup —
  no gate covers it, and this session's own re-wrap script introduced one.
- **The real test is a hill climb.** These fixes are justified by making the optimizer's inputs and its
  objective honest, not by a measured improvement. The next run is the evidence.

## Landing & cleanup

- **Branch** — `sarol-optimizer-impl`, unmerged, merges to `sarol` (not `main`). **72 commits ahead
  of `sarol` and 0 behind**, merge-base `d8f52f8` = `sarol`'s tip, so this lands as a fast-forward.
  (This line read "5 commits off `sarol`" while the plan was in draft; it was never right.)
  Four other worktrees are live here, so re-verify the branch immediately before each commit.
- **Order** — Slice 2 first this time (it is small and it decides what the docs must say), then Slice 1
  against the settled objective. Writing the docs first would mean rewriting the objective prose twice.
- **Before the next run** — restore the tree to pristine `v0` and re-tag.
- **Cleanup on land** — prune the branch and worktree, mark this plan `Status: Completed`, prune the
  `NEXT.md` entry, and delete `docs/session/optimizer-prompt-ANNOTATED-2026-09-07.md` once Slice 1 is
  verified against it.
