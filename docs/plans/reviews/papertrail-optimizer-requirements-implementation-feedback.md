Reference: docs/claude_ops.md

# Implementation Feedback: papertrail-optimizer-requirements

## Verdict
Blocked. The implementation has several correct helper pieces, but it is not yet a runnable paper-trail consumer of `agentic-label-opt`: `dispatcher.py` does not call `run_loop`, the Runner invokes a slash command that is absent from the repo, and the C5 validator weakens or misses parts of the stated Sarol contract.

## Plan Coverage
Slice / section | Status (Done / Partial / Missing / Drifted) | Evidence: path:line | Notes
--- | --- | --- | ---
Part A1/A4 manifest strip + contract paths | Done | experiments/sarol-2024/program-v0/manifest.json:17, experiments/sarol-2024/program-v0/manifest.json:50, experiments/sarol-2024/program-v0/manifest.json:58, experiments/sarol-2024/program-v0/manifest.json:74, experiments/sarol-2024/optimizer/adapter.py:167 | Manifest has 8 entries and three `contract_file=True`; adapter strips engine-unknown extras before building `ProgramManifest`.
Part A/OQ8 contract-file re-hash | Partial | experiments/sarol-2024/optimizer/adapter.py:191, experiments/sarol-2024/optimizer/adapter.py:719, /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:393 | Re-hash exists and a nonzero agent exit would stop before `commit_version`, but no real dispatcher wiring wraps the optimizer agent in `ContractGuardedAgent`.
Part B1 context docs | Done | experiments/sarol-2024/optimizer/context/playbook.md:13, experiments/sarol-2024/optimizer/context/task-and-scoring.md:21, experiments/sarol-2024/optimizer/context/release-format.md:43 | Covers iteration procedure, macro-F1 objective, known failure modes, release shape, and Tier 2 VAL reduction.
Part B2 hot-path prompt | Done | experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:23, experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:31, experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:48, experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:98, experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:108 | States the objective, 9-class enum, EDIT/contract/SEALED scope, per-claim budget, and canary.
Part B3 continuity docs | Done | experiments/sarol-2024/optimizer/meta-learnings.md:11, experiments/sarol-2024/optimizer/meta-learnings.md:28, experiments/sarol-2024/optimizer/meta-learnings.md:35, experiments/sarol-2024/optimizer/meta-learnings.md:75 | Covers no-baseline status plus confirmed/pending/reverted sections.
Part C1 scoring scalar + finite metric | Done | experiments/sarol-2024/scripts/score_sarol3.py:91, experiments/sarol-2024/optimizer/adapter.py:611, experiments/sarol-2024/optimizer/adapter.py:615 | 3-way macro-F1 is the primary metric and non-finite values are converted to `scored=false`.
Part C1/C3 Tier discipline | Done | experiments/sarol-2024/optimizer/adapter.py:628, experiments/sarol-2024/optimizer/adapter.py:644, experiments/sarol-2024/optimizer/adapter.py:663, experiments/sarol-2024/optimizer/adapter.py:672 | TRAIN keeps full breakdown via corpus metrics; VAL keeps scalar plus completeness metadata only.
Part C4 #1 Runner called 3x/cost counted | Partial | /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:334, /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:335, /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:410, experiments/sarol-2024/optimizer/dispatcher.py:93 | Cost model counts TRAIN + current VAL + probe VAL, but nested `claude` calls lack the required hard `--max-budget-usd` cap.
Part C4 #2 timeout/status handling | Done | experiments/sarol-2024/optimizer/adapter.py:269, experiments/sarol-2024/optimizer/adapter.py:469, experiments/sarol-2024/optimizer/adapter.py:513, experiments/sarol-2024/optimizer/adapter.py:562 | Runner catches timeout and nonzero exits into statuses; Scorer refuses non-`ok` artifacts.
Part C4 #3 `_split` not injected | Done | /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:336, experiments/sarol-2024/optimizer/adapter.py:549, experiments/sarol-2024/optimizer/adapter.py:552 | Scorer stashes `_split` into task_config before release building.
Part C4 #4 pre-resolved repo root | Done | experiments/sarol-2024/optimizer/adapter.py:150, experiments/sarol-2024/optimizer/adapter.py:360 | ProgramStore and Runner resolve roots before use.
Part C4 #5 materialized tree not runnable | Done | experiments/sarol-2024/optimizer/adapter.py:357, experiments/sarol-2024/optimizer/adapter.py:390, experiments/sarol-2024/optimizer/adapter.py:460 | Runner keeps a real checkout as cwd and passes materialized tree as `--spec-root`.
Part C4 #6 positional/keyword asymmetry | Done | experiments/sarol-2024/optimizer/adapter.py:414, experiments/sarol-2024/optimizer/adapter.py:544, experiments/sarol-2024/optimizer/adapter.py:654, experiments/sarol-2024/optimizer/adapter.py:739 | Concrete methods match the engine call shapes.
Part C5 Sarol exit validator | Drifted | experiments/sarol-2024/optimizer/validate_sarol.py:165, experiments/sarol-2024/optimizer/validate_sarol.py:191, experiments/sarol-2024/optimizer/validate_sarol.py:213, experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:35 | Variant gate and fixtures exist, but rollup, invalid sub-claim counting, and `AMBIGUOUS` fixture behavior drift from the plan.
Verification: paperclip pin negative control | Done | experiments/sarol-2024/program-v0/manifest.json:98, experiments/sarol-2024/optimizer/adapter.py:369, experiments/sarol-2024/optimizer/adapter.py:429, experiments/sarol-2024/optimizer/adapter.py:974 | Mismatch returns `infra_error` before batch loading/dispatch.
Verification: coverage assertion | Partial | experiments/sarol-2024/optimizer/adapter.py:578, experiments/sarol-2024/optimizer/adapter.py:596, experiments/sarol-2024/optimizer/adapter.py:647 | `n_total == requested_count` is enforced, but VAL reduction drops `n_invalid` despite the plan asking for it to be surfaced.

## Critical Drift

- Severity: Critical | C5 says the Sarol validator must preserve rollup consistency; the Sarol rubric defines that as a worst-wins order (`CONTRADICT > NOT_SUBSTANTIATE > ... > ACCURATE`). `validate_sarol.py` deliberately replaces that with "overall is one of the sub-claim labels", so a two-sub-claim file with `CONTRADICT` plus `ACCURATE` can validate with `overall_verdict=ACCURATE`. | Evidence: docs/plans/papertrail-optimizer-requirements.md:173, docs/plans/papertrail-optimizer-requirements.md:175, experiments/sarol-2024/specs/verdict_schema_sarol.md:25, experiments/sarol-2024/specs/verdict_schema_sarol.md:27, experiments/sarol-2024/optimizer/validate_sarol.py:30, experiments/sarol-2024/optimizer/validate_sarol.py:213, experiments/sarol-2024/optimizer/validate_sarol.py:220, experiments/sarol-2024/optimizer/validate_sarol.py:309 | Required fix: enforce the current Sarol worst-wins order for `rubric_variant=sarol_2024_9class`, or explicitly move rollup-order mutability out of the validator contract and update the plan. As written, the implementation weakens a named structural rule.
- Severity: Critical | C5/A2 say out-of-enum labels are misses counted in `error_class_counts`; the current pipeline only guarantees that for `overall_verdict`. `validate_sarol.py` counts invalid sub-claim verdicts without failing, but `SarolScorer` ignores `record["validation"]["error_class_counts"]` and re-derives errors only from `parse_verdict.parse(...).pred_label`, which is the overall verdict. A file with `sub_claims[0].verdict="PROBABLY_FINE"` and `overall_verdict="ACCURATE"` can validate and score with no invalid-label count. | Evidence: docs/plans/papertrail-optimizer-requirements.md:93, docs/plans/papertrail-optimizer-requirements.md:175, experiments/sarol-2024/optimizer/validate_sarol.py:139, experiments/sarol-2024/optimizer/validate_sarol.py:149, experiments/sarol-2024/optimizer/validate_sarol.py:238, experiments/sarol-2024/optimizer/adapter.py:485, experiments/sarol-2024/optimizer/adapter.py:590, experiments/sarol-2024/scripts/parse_verdict.py:174, experiments/sarol-2024/scripts/score_sarol3.py:72 | Required fix: either make any out-of-enum sub-claim verdict force an invalid overall prediction for scoring, or merge validator invalid-label counts into the scorer/release and add a fixture where only a sub-claim verdict is invalid.
- Severity: Critical | `dispatcher.py` says it drives `agentic-label-opt`'s `run_loop`, but it never imports or calls `run_loop`, never creates the optimizer agent, never wraps that agent in `ContractGuardedAgent`, and never loads `prompt/optimizer-instructions.md` as `agent_instructions`. The implemented module is a preflight/helper library, not the dispatcher promised by Files to create. | Evidence: docs/plans/papertrail-optimizer-requirements.md:190, docs/plans/papertrail-optimizer-requirements.md:191, experiments/sarol-2024/optimizer/dispatcher.py:1, experiments/sarol-2024/optimizer/dispatcher.py:295, experiments/sarol-2024/optimizer/dispatcher.py:319, experiments/sarol-2024/optimizer/dispatcher.py:493 | Required fix: add the real `run_loop(...)` entrypoint wiring `program_store`, `CachingRunner(SarolRunner)`, `SarolScorer`, `SarolReleaseBuilder`, `build_mistake_corpus`, the optimizer agent loaded with the hot-path prompt/context, and `ContractGuardedAgent` around that agent.
- Severity: Critical | The cost/runtime gate requires `claude -p --max-budget-usd` plus timeout; `SarolRunner` has the timeout but does not pass `--max-budget-usd` to any nested Claude invocation. The dispatcher estimates/refuses before runs, but there is no hard per-call spend cap at the actual spender. | Evidence: docs/plans/papertrail-optimizer-requirements.md:257, experiments/sarol-2024/optimizer/adapter.py:259, experiments/sarol-2024/optimizer/adapter.py:269, experiments/sarol-2024/optimizer/adapter.py:397, experiments/sarol-2024/optimizer/adapter.py:412 | Required fix: add a per-call budget parameter to `SarolRunner` and include `--max-budget-usd <value>` in `_stage_command`, with a self-test that inspects the command vector.
- Severity: Critical | C5/OQ7 specifically says use `AMBIGUOUS` as the out-of-enum fixture label and that `AMBIGUOUS` in a verdict field must be rejected "exactly like any other out-of-enum label"; the implemented fixture uses `PROBABLY_FINE`, and `validate_sarol.py` classifies `AMBIGUOUS` as a native-label `RUBRIC_MISMATCH`. That may be intentional, but it is not the contract the plan names. | Evidence: docs/plans/papertrail-optimizer-requirements.md:175, docs/plans/papertrail-optimizer-requirements.md:230, experiments/sarol-2024/optimizer/validate_sarol.py:22, experiments/sarol-2024/optimizer/validate_sarol.py:73, experiments/sarol-2024/optimizer/validate_sarol.py:85, experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:35, experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:42 | Required fix: decide the intended precedence. If the plan is authoritative, change the fixture to `AMBIGUOUS` and count it as `invalid_label`; if native-label mismatch is desired, update the plan and add a separate `AMBIGUOUS` regression fixture.

## Missing Pieces

- Plan item: `dispatcher.py` drives `run_loop` | Where it should land: `experiments/sarol-2024/optimizer/dispatcher.py` | Why it matters: without the real loop entrypoint, none of the protocol objects are proven together under the engine's actual iteration order, and the contract-file guard is only exercised in an isolated self-test. | Suggested code change: add a CLI path that constructs `RunInputs`, policy/config/run-store arguments, the optimizer agent, and calls `engine.loop.run_loop(...)`.
- Plan item: per-call hard budget via `claude -p --max-budget-usd` | Where it should land: `SarolRunner._stage_command` and `dispatcher.build_components` | Why it matters: the engine does not enforce Runner spend, and the current implementation only forecasts/refuses at wrapper boundaries. | Suggested code change: thread `per_call_max_budget_usd` into `SarolRunner` and append `--max-budget-usd` to every nested Claude command.
- Plan item: round-trip canary stops the run before scored claims | Where it should land: `SarolRunner.run` or the real dispatcher before constructing the scored batch | Why it matters: Part B requires the canary as the scorer-breakage guard; currently it is documented in prompt/context only, with no implementation hook in `adapter.py` or `dispatcher.py`. | Suggested code change: run the pinned canonical claim before batch dispatch and return `infra_error`/`program_error` before the first scored claim if the expected verdict changes.
- Plan item: runnable nested dispatch | Where it should land: `SarolRunner._stage_command` or a new `.claude/commands/sarol-eval-item.md` | Why it matters: the runner invokes `/sarol-eval-item`, but no such slash command exists under `.claude/commands`, `src/commands`, or `experiments/sarol-2024`; a real run will fail before producing a verdict. | Suggested code change: either add the slash command as a fixed runner dependency or change `_stage_command` to call an existing command/script that performs the extractor/adjudicator/verifier stage.
- Plan item: `n_invalid` surfaced in release | Where it should land: `SarolReleaseBuilder._reduce_for_val` / `release-format.md` | Why it matters: the scorer computes `n_invalid`, but the VAL release strips it even though the Verification table calls it out with coverage. | Suggested code change: include `n_invalid` in `_VAL_BREAKDOWN_ALLOWED`, or document why Tier 2 intentionally hides it and update the plan.

## Contract Violations

- Sarol rollup contract: `experiments/sarol-2024/specs/verdict_schema_sarol.md:25` defines worst-wins rollup, but `validate_sarol.py:220` accepts any `overall_verdict` present among sub-claims.
- C5 fixture contract: `docs/plans/papertrail-optimizer-requirements.md:175` requires an out-of-enum `AMBIGUOUS` fixture; `experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:35` uses `PROBABLY_FINE`.
- Dispatcher contract: `docs/plans/papertrail-optimizer-requirements.md:191` says `dispatcher.py` drives `run_loop`; `experiments/sarol-2024/optimizer/dispatcher.py:493` exposes only `--selftest` and `--preflight`.
- Runner command contract: `SarolRunner._stage_command` invokes `/sarol-eval-item`, but the repo has no such command file. Evidence: experiments/sarol-2024/optimizer/adapter.py:393, `.claude/commands/ground-claim.md` exists while `.claude/commands/sarol-eval-item.md` does not.
- Coverage/release contract: `score_sarol3.py` computes `n_invalid`, but `_VAL_BREAKDOWN_ALLOWED` omits it, so `release_val.json` cannot surface it. Evidence: experiments/sarol-2024/scripts/score_sarol3.py:102, experiments/sarol-2024/optimizer/adapter.py:635.

## Test Gaps

- `validate_sarol.py --selftest` asserts the weakened rollup behavior rather than the plan's rule: it expects `overall_verdict="ACCURATE"` to validate for a fixture whose sub-claims include `OVERSIMPLIFY`. This test would still pass if worst-wins consistency were entirely absent. Evidence: experiments/sarol-2024/optimizer/validate_sarol.py:309.
- No test covers an invalid sub-claim verdict with a valid overall verdict. The existing invalid fixture sets both fields to `PROBABLY_FINE`, so it does not prove `sub_claims[*].verdict` invalid labels are surfaced in scoring/release. Evidence: experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:35, experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json:42.
- `adapter.py --selftest` proves `ContractGuardedAgent` catches a mutation only when manually constructed around `_StubAgent`; no dispatcher or loop test proves the real optimizer agent is wrapped before `commit_version`. Evidence: experiments/sarol-2024/optimizer/adapter.py:812, experiments/sarol-2024/optimizer/dispatcher.py:319.
- No test inspects the nested Claude command for `--max-budget-usd`; `_stage_command` is untested for the plan's hard per-call budget requirement. Evidence: experiments/sarol-2024/optimizer/adapter.py:397.
- No test covers the round-trip canary path. The canary is described in docs, but `grep` finds no implementation in `adapter.py` or `dispatcher.py`. Evidence: experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:108.

## Defensible Deviations

- `validate_sarol.py` also carries schema 1.1 `source_mode` / `paperclip_handle` checks, although C5's named structural list is shorter. This is defensible because the native schema lists those as label-independent exit rules, and the fixtures cover both modes. Evidence: src/specs/verdict_schema.md:196, experiments/sarol-2024/optimizer/validate_sarol.py:181.
- The VAL release strips per-class F1, confusion matrix, and `error_class_counts` more aggressively than "aggregates-only" might imply. This is defensible under the framework's Tier 2 scalar-only rule, but it conflicts with the separate `n_invalid surfaced` verification item and should be confirmed. Evidence: experiments/sarol-2024/optimizer/adapter.py:628, experiments/sarol-2024/optimizer/adapter.py:635.
- Paperclip version normalization accepts banners like `paperclip, version 0.5.11` and `0.5.11` as equal. That preserves the runtime pin's semantic check without making banner text a false blocker. Evidence: experiments/sarol-2024/optimizer/adapter.py:306.
- Cost accounting uses metered CLI `total_cost_usd` rather than `parse_verdict.estimate_cost_usd`, matching the plan's C1 correction. Evidence: docs/plans/papertrail-optimizer-requirements.md:152, experiments/sarol-2024/optimizer/adapter.py:235.

## Suggested Code Edits

- `experiments/sarol-2024/optimizer/validate_sarol.py:213`: replace the "overall in sub-label set" rollup check with the Sarol worst-wins order from `experiments/sarol-2024/specs/verdict_schema_sarol.md:27`, and add positive/negative multi-sub-claim fixtures.
- `experiments/sarol-2024/optimizer/validate_sarol.py:73`: resolve `AMBIGUOUS` precedence. If the plan stands, remove it from `NATIVE_VERDICTS` for Sarol validation or special-case it as `invalid_label`, then change `fixtures/out_of_enum_label.json:35` and `:42` to `AMBIGUOUS`.
- `experiments/sarol-2024/optimizer/adapter.py:580`: carry validator invalid-label counts into scoring, especially for sub-claim labels, or make invalid sub-claim labels fail the claim before `parse_verdict` can produce a valid-looking overall score.
- `experiments/sarol-2024/optimizer/adapter.py:390`: add a preflight assertion that the invoked slash command exists, or replace `/sarol-eval-item` with an implemented command/script.
- `experiments/sarol-2024/optimizer/adapter.py:397`: include `--max-budget-usd` in the nested Claude command and self-test the exact command vector.
- `experiments/sarol-2024/optimizer/dispatcher.py:493`: add the real run subcommand that calls `engine.loop.run_loop(...)` and wires `ContractGuardedAgent` around the optimizer agent.
- `experiments/sarol-2024/optimizer/adapter.py:635`: include `n_invalid` in VAL completeness metadata or update the plan to state that Tier 2 hides it.
- `experiments/sarol-2024/optimizer/adapter.py:450`: implement the round-trip canary before iterating over scored claims, so a canary failure returns before any claim dispatch beyond the canary.

## Questions For The Author

- Should Sarol rollup order be optimizer-editable during this phase? The implementation assumes yes and weakens validation accordingly; the plan says the structural rollup-consistency rule survives unchanged.
- Should `AMBIGUOUS` in a Sarol verdict field be treated as a native-rubric mismatch or as the named out-of-enum miss? The plan says the latter in C5/OQ7, while the implementation chooses the former.
- Is `/sarol-eval-item` an intended external slash command not included in this branch, or should this implementation add it?
- Does Tier 2 allow `n_invalid` as non-structural completeness metadata, or should it be hidden with `error_class_counts`?

## Audit Trail

- docs/claude_ops.md
- CLAUDE.md
- docs/plans/papertrail-optimizer-requirements.md
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/validate_sarol.py
- experiments/sarol-2024/optimizer/fixtures/mixed_native_sarol.json
- experiments/sarol-2024/optimizer/fixtures/out_of_enum_label.json
- experiments/sarol-2024/optimizer/fixtures/valid_all_sarol.json
- experiments/sarol-2024/optimizer/context/playbook.md
- experiments/sarol-2024/optimizer/context/task-and-scoring.md
- experiments/sarol-2024/optimizer/context/release-format.md
- experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md
- experiments/sarol-2024/optimizer/meta-learnings.md
- experiments/sarol-2024/program-v0/manifest.json
- experiments/sarol-2024/scripts/score_sarol3.py
- experiments/sarol-2024/scripts/parse_verdict.py
- src/specs/verdict_schema.md
- experiments/sarol-2024/specs/verdict_schema_sarol.md
- experiments/sarol-2024/specs/verdict_enum_sarol.md
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/adapter.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/schemas.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/materialize.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/versioning.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/policy.py

Self-tests run with `PYTHONDONTWRITEBYTECODE=1`:

- `python3 experiments/sarol-2024/optimizer/validate_sarol.py --selftest` -> 15/15 passed
- `python3 experiments/sarol-2024/optimizer/adapter.py --selftest` -> 44/44 passed
- `python3 experiments/sarol-2024/optimizer/dispatcher.py --selftest` -> 24/24 passed
