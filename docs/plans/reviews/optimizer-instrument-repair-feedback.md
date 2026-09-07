Reference: docs/claude_ops.md

# Feedback: Optimizer instrument repair (Codex review)

## Verdict
Revise. The plan is pointed at real blockers and its main factual claims check out, but it is not handoff-ready because it misses one current metric-name contract drift, underspecifies the cross-repo release schema change, and overstates what the proposed two-run noise floor can establish.

## Critical Gaps
- Severity: Critical | Gap: Phase D does not explicitly fix the live metric-name contract: `PRIMARY_METRIC_NAME` remains `sarol_macro_f1_6class` while the scorer's objective is all nine classes renormalised over classes present | Why it matters: the next baseline would emit a misleading primary metric name into release payloads and gates, so downstream interpretation can still be wrong after B1/B2 | Evidence: experiments/sarol-2024/optimizer/adapter.py:314; experiments/sarol-2024/scripts/score_sarol3.py:62; experiments/sarol-2024/scripts/score_sarol3.py:175; experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:35 | Required fix: add an explicit phase item to rename the primary metric, update release examples/gates/docs, and decide whether old `_6class` payloads are rejected or treated as legacy.
- Severity: Critical | Gap: C1 says to put paired A/B effect into the next TRAIN release but does not name the engine schema/API change required | Why it matters: `ReleasePayloadTrain` has only `corpus`, and `ReleasePayloadVal` has only `metrics`; the engine currently passes `frontier`/`budget` kwargs but not pre/post deltas. A consumer-only doc edit cannot make that field appear reliably | Evidence: <sibling>/agentic-label-opt/engine/schemas.py:207; <sibling>/agentic-label-opt/engine/schemas.py:222; <sibling>/agentic-label-opt/engine/loop.py:366; <sibling>/agentic-label-opt/engine/loop.py:455 | Required fix: specify the exact engine surface, field name, payload location, backward compatibility, and pin/merge order before the consumer branch depends on it.
- Severity: Critical | Gap: The B3 decision gate treats two VAL runs on one frozen program as a sufficient noise floor | Why it matters: that measures one slice of judge stochasticity only; it does not capture sampling variance across stratified draws, canary variation, model alias drift, or the paired pre/post comparison used by step-back/frontier logic. Halting at `>0.03` may be under- or over-conservative without a confidence interval | Evidence: <sibling>/agentic-label-opt/engine/loop.py:410; <sibling>/agentic-label-opt/engine/loop.py:457; docs/journal/2026-09-03-first-optimization-attempt-postmortem.md:19; docs/journal/2026-09-03-first-optimization-attempt-postmortem.md:91 | Required fix: define the statistic before running: same VAL batch repeated at least enough times to estimate spread, report absolute metric delta and per-claim flip rate, and set a tolerance such as `τ_cal` with a confidence rule rather than a single two-run difference.
- Severity: Gap | Gap: A3 says to add `CLAUDE.md` and `.claude/settings.json` as manifest entries, but `.claude/settings.json` is absent and no `hash_only_resolver` or source/archive policy is specified | Why it matters: `hash_only` entries require `content_hash` and `archive_ref`; committed entries are staged by git. Without an exact policy, the manifest refreeze can either fail materialization or accidentally commit local/runtime config | Evidence: experiments/sarol-2024/optimizer/adapter.py:608; experiments/sarol-2024/program-v0/manifest.json:17; <sibling>/agentic-label-opt/engine/schemas.py:95; <sibling>/agentic-label-opt/engine/versioning.py:92 | Required fix: list each new manifest entry with `committed` vs `hash_only`, expected presence/optional status, resolver behavior, and whether absence of `.claude/settings.json` is acceptable.
- Severity: Gap | Gap: The verification expectation for B2 is too loose and partly underspecified for the actual objective | Why it matters: `OBJECTIVE_CLASSES` is all nine, TRAIN N=50 can include all nine under current water-filling, but VAL dev has no `INDIRECT_NOT_REVIEW`; the plan says “≥1 of every class with gold available” without naming expected counts or checking `objective_classes_present` stability | Evidence: experiments/sarol-2024/scripts/score_sarol3.py:89; experiments/sarol-2024/optimizer/sampling.py:286; experiments/sarol-2024/optimizer/context/task-and-scoring.md:37; experiments/sarol-2024/optimizer/context/task-and-scoring.md:49 | Required fix: pin expected stratified distributions for TRAIN N=50 and VAL N=80 and gate on `support_9way`, `objective_classes_present`, and stable denominator for each compared curve.

## Failure Modes
- Scenario | Why the plan misses it | What to add
- A run emits `sarol_macro_f1_6class` while actually optimizing nine-class renormalised macro-F1 | The plan flags stale examples but not the code constant that feeds the release and prompt gate | Add a metric-name migration item and a negative control that old/stale names fail docs or release checks.
- Paired-delta field is added only in paper-trail docs | C1 assumes the engine “already computes” the value, but release payload dataclasses have no field for it | Add an engine PR item that extends the release/frontier API or explicitly places the delta inside adapter-owned `corpus.metrics.breakdown`.
- Noise gate passes by luck after two similar VAL runs | Two runs do not estimate variance robustly and do not test sample sensitivity | Require repeated same-batch judge replicates plus at least one stratified-draw sensitivity check before deciding re-baseline readiness.
- Subagent cannot open the trace it is told to use | The brief points to run-manifest `trace_ref`, but the optimizer prompt says to hand only claim ids and brief path; the mistake row has no `trace_ref` or manifest path | Either add `trace_ref` to the mistake corpus rows or change the brief to route through `corpus.ref` plus an explicit manifest reference.
- Refreeze includes live command/settings files but they are not materialized for the nested command | Manifest policy is not defined for `.claude/commands/sarol-eval-item.md`, `CLAUDE.md`, and optional settings | Add materialization smoke criteria proving a frozen tree contains exactly the command/settings surface the runner actually uses.

## Contract Checks
The split between consumer and engine is mostly correct. Consumer-side: stratified TRAIN, corpus filtering, full manifest hash verification, `--current-tag`, and prompt/docs belong in `paper-trail` because they are adapter policy and Sarol-specific data handling. Engine-side: `_select_best` handling of unscored placeholders, probe failure semantics, and paired-delta release plumbing belong in `agentic-label-opt` because the relevant surfaces are `_select_best`, `run_loop`, `ReleasePayloadTrain`/`Val`, and `IterResult`.

The plan must tighten version pinning and merge order. `run_loop` still defaults `current_tag="program-v0"` and accepts optional `audit_ledger`/`policy_config`, but `dispatcher.run_optimization` does not pass those fields. If the engine schema changes for C1, the consumer branch needs a pinned sibling SHA and a refusal when the installed engine lacks the new field.

Confirmed load-bearing facts: TRAIN is not stratified (`train_inputs_factory` calls `resolve_batch` with no `pool`), VAL is stratified by default, the mistake corpus currently filters on `pred_3way == gold_3way`, `verify_contract_files` only checks `contract_file`, and `parse_rollup_order` takes the first fenced block containing all nine labels without requiring `>`.

## Modularity vs. YAGNI
The plan is too large to land as one unit. Split it into: first, Phase A+B minimal instrument repair and metric-name cleanup; second, engine release/frontier changes C1/B4/B5 with a pinned sibling engine SHA; third, optimizer-facing doc reconciliation; fourth, optional credibility work such as TEST and no-op controls. That gives a usable paid-run gate after the first two slices and keeps doc-only churn from blocking the core harness fix.

Reuse is generally right: use existing `stratified_draw`, `resolve_batch`, `LocalLoopOps`, `ReleaseBuilder`, and engine hooks. Avoid adding new manifest abstractions unless A3 truly needs `hash_only`; if the file can be committed and materialized normally, use the existing `committed` path.

## Verification Gaps
B1 should include a fixture where `gold_label != pred_label` but `gold_3way == pred_3way`, and assert the mistake row is present and `n_correct` is unchanged. B2 should assert exact support counts for representative rungs, not just non-empty class support.

A1 needs two separate negative controls: current tree content differs from manifest sha and named tag differs from `--current-tag`. Right now the plan blends tag identity and content identity.

B3 needs a stronger statistical success criterion: number of replicate runs, metric delta threshold, flip-rate threshold, and what happens when only one or two claims flip. The `~0.03` effect size is grounded in the postmortem's one-claim movement at n=37, but not defensible as a universal stop threshold without VAL size and denominator attached.

D-phase gates should include the stale objective-name/docs contradictions. Current docs still say `_6class` and in places say 3-way is the frontier, while `task-and-scoring.md` says the objective is nine-class renormalised.

## Handoff Readiness
The plan has useful file lists and phase labels, but several items lack exact sister files: `score_sarol3.py` is under `experiments/sarol-2024/scripts/`, not repo-root `scripts/`; C1 must name `engine/schemas.py`; A3 must name `.claude/commands/sarol-eval-item.md` explicitly because that is the command the nested session resolves.

The seven open questions are mostly real, but OQ2 is decidable from current code: the judge does not load `verdict_definitions_sarol.md`; it loads only enum and rubric, and `.claude/commands/sarol-eval-item.md` checks for only those two spec files. OQ4 is also partly decidable: the audit ledger is currently unwired in the consumer; the remaining decision is whether to wire it or delete the claim.

Coordination with in-flight work is not complete. `docs/plans/NEXT.md` says do not land the Sarol taxonomy branch on `main` until optimizer work is done, while this plan requires an engine sibling branch to land first. The landing section should spell out the consumer branch base, engine SHA pin, and whether the manifest refreeze happens before or after rebasing onto the engine update.

## Suggested Revisions
- Add Phase B0 or A6: rename `PRIMARY_METRIC_NAME`, release-format examples, prompt text, and gates from `_6class` to the actual nine-class renormalised objective.
- Move C1 into the engine-sibling slice and specify the exact payload/API contract, including compatibility behavior when older engines are installed.
- Strengthen B3 from “two VAL runs” to a calibrated repeat protocol with a confidence rule, and tie the threshold to the selected VAL N and `n_objective_classes_present`.
- Add exact expected stratified support tables for TRAIN N=50 and VAL N=80.
- Split landing into four PRs/commits: A+B core harness, engine sibling, docs reconciliation, credibility extras.
- Add `sampling.py` docstring cleanup for the obsolete 1,699/255 drawable-pool explanation.
- Resolve the trace handoff either by adding trace refs to mistake rows or by removing trace instructions from the subagent brief.

## Questions For The Author
- Should the primary metric key be renamed now, or intentionally kept as `_6class` for backward compatibility with existing artifacts?
- For A3, should `.claude/commands/sarol-eval-item.md` and `CLAUDE.md` be committed manifest entries, and should absent `.claude/settings.json` be an optional committed entry or omitted until it exists?
- Is C1 meant to change `agentic-label-opt` schemas, or should paper-trail encode paired deltas inside its adapter-owned release `corpus` body?
- What minimum replicate count is acceptable for the noise-floor gate before spending on the haiku re-baseline?
- Is TEST evaluation a separate credibility branch after the re-baseline, or a required landing gate before any reported curve?

## Audit Trail

**Author disposition (2026-09-07).** 13 findings applied. All six load-bearing facts the review was
asked to re-verify were independently confirmed, which is the main reason the plan's phase ordering
survived unchanged.

Two findings retired an Open Question by answering it from code: the judge does not load
`verdict_definitions_sarol.md`, and C1 needs no engine schema change because
`ReleasePayloadTrain.corpus` is an adapter-defined body (`agentic-label-opt/engine/schemas.py:207-214`)
— the latter removed C1 from the cross-repo critical path entirely, which is the single most useful
thing this review produced.

**One finding not applied.** Under Handoff Readiness the review states that "`docs/plans/NEXT.md` says
do not land the Sarol taxonomy branch on `main` until optimizer work is done". No such text exists in
`NEXT.md` — grep for landing/branch-hold language returns nothing matching. The *underlying* gap was
real and was fixed: the Landing section now names the branch base (`sarol`, 5 commits behind, not
`main`), the engine SHA pin, and the re-freeze-after-rebase ordering. The specific citation is not
reproduced because it does not check out.

**Scope split accepted.** The plan now lands as four slices per the Modularity section, with the
paid-run gate after slices 1 and 2.

- Repo-local checklist: none.
- docs/claude_ops.md
- docs/plans/optimizer-instrument-repair.md
- docs/plans/NEXT.md
- docs/journal/2026-09-03-first-optimization-attempt-postmortem.md
- experiments/sarol-2024/optimizer/sampling.py
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/validate_sarol.py
- experiments/sarol-2024/optimizer/profiles.py
- experiments/sarol-2024/scripts/score_sarol3.py
- experiments/sarol-2024/program-v0/manifest.json
- experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md
- experiments/sarol-2024/specs/verdict_schema_sarol.md
- experiments/sarol-2024/specs/verdict_definitions_sarol.md
- experiments/sarol-2024/specs/verdict_enum_sarol.md
- experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md
- experiments/sarol-2024/optimizer/context/release-format.md
- experiments/sarol-2024/optimizer/context/task-and-scoring.md
- experiments/sarol-2024/optimizer/context/edit-surface.md
- experiments/sarol-2024/optimizer/context/playbook.md
- experiments/sarol-2024/optimizer/context/failure-mode-discovery.md
- experiments/sarol-2024/optimizer/context/subagent-blame-brief.md
- .claude/commands/sarol-eval-item.md
- CLAUDE.md
- <sibling>/agentic-label-opt/engine/loop.py
- <sibling>/agentic-label-opt/engine/schemas.py
- <sibling>/agentic-label-opt/engine/versioning.py
- <sibling>/agentic-label-opt/engine/materialize.py
