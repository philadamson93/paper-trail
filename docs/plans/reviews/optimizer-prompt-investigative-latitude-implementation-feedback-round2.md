Reference: docs/claude_ops.md

# Implementation Feedback (Round 2, committed-branch audit): Plan A — optimizer prompt investigative latitude

## Verdict

**Revise before commit.** The reset bytes, five standalone gates, 10-entry source-ref manifest, and 447-check suite can all be made green, but the two most important semantic contracts are checked only before the run—not after the optimizer edits the files—and the canonical tag/canary recut and Gate E are still unfinished.

## Measured Gate + Suite Results

All commands used `~/.local/bin/python3.13` with `AGENTIC_LABEL_OPT=/home/philadamson/engine-82f547d`.

| Check | Measured result |
|---|---:|
| Gate A, `check_paper_fidelity.py` | **40/40**; 8 definitions in both judge-path files plus reference, 6 retired strings absent |
| Gate D, `check_empty_window_regression.py` | **PASS**; empty array accepted, omitted field rejected as `MISSING_FIELD:sub_claims[0].evidence` |
| Gate F, `check_orchestrator_consistency.py` | **16/16** |
| Gate F selftest | **4/4** |
| Gate G, `check_prompt_hygiene.py` | **12 files reported clean** |
| Gate G selftest | **6/6** |
| Gate H, `check_run_scope.py` | **PASS**, sheet byte-identical to stub and no `findings/iter-*.md` |
| Gate H selftest | **4/4** |
| `freeze_program_v0.py --verify` | **10/10**, `combined_hash 7431a5bc98a9` reproduces |
| adapter | **152/152** |
| dispatcher | **114/114** |
| validate_sarol | **33/33** |
| sampling | **50/50** after setting `PAPER_TRAIL_GOLD_DIR=/tmp/codex-round2-gold` |
| evidence_producers | **26/26** |
| canary | **24/24** |
| profiles | **48/48** |
| Aggregate | **447/447** with the writable temporary gold root |

With only the environment stated in the request, `sampling.py --selftest` returned **48/50**, so the aggregate was **445/447**: both real-staging assertions failed because `stage_claim.stage()` attempted to write under the sandbox-read-only default gold root (`stage_claim.py:48-53`; `sampling.py:671-685,908-916`). Redirecting that output to `/tmp` made the same two checks pass. This is an undeclared selftest write precondition, not an implementation-logic failure, but the selftest should isolate its own writes.

The stronger composed-tree check is red: `freeze_program_v0.py --verify --tree program-v0` reports **3 mismatches across 10 entries** (`adjudicator-dispatch-sarol.md`, `verdict_schema_sarol.md`, `verdict_definitions_sarol.md`). Tags `program-v0` through `program-v5` remain live at their old commits; none is archived. The canary still records `program_combined_hash 0a02710cbd88`, not `7431a5bc98a9` (`optimizer/canary/canary-retrieval.json:12`).

## Plan Coverage

| Step / section | Status | Evidence: path:line | Notes |
|---|---|---|---|
| P0 definitions reset | Done | `specs/verdict_schema_sarol.md:15-38`; `prompts/adjudicator-dispatch-sarol.md:29-48` | All eight definitions match the paper's §2.2 text; `INDIRECT_NOT_REVIEW` is marked house text. |
| P0 retired judge guidance | Done | `scripts/check_paper_fidelity.py:81-90,124-132` | The six named retired clauses are absent from both judge-path files. |
| P0 evidence-array carry-forward | Done | `prompts/adjudicator-dispatch-sarol.md:88-96`; `scripts/check_empty_window_regression.py:47-81` | Positive and negative paths are real. |
| P0 10-entry source-ref manifest | Done | `scripts/freeze_program_v0.py:38-64`; `program-v0/manifest.json:15-16,67-97` | Source-ref verification is 10/10 at `7431a5bc98a9`; driver is entry 10, editable. |
| P0 canonical ledger recut | Missing | `optimizer-prompt-investigative-latitude.md:104-109,571-574` | Old `program-v0..v5` tags remain; `program-v0` fails composed-tree verification; canary is stale. The plan header correctly says this remains (`:13`). |
| Step 0, gold is objective | Done | `optimizer/prompt/optimizer-instructions.md:11-37` | Correctly distinguishes verbatim definitions from editable house guidance. |
| Step 1, trace-grounded blame | Done | `optimizer/prompt/optimizer-instructions.md:208-222`; `optimizer/context/subagent-blame-brief.md:99-107,123-138` | Execution blame requires a trace quote and correct-answer traces point to `run_manifest.json`. |
| Step 2, three record surfaces | Partial | `optimizer/prompt/optimizer-instructions.md:288-315,437-449` | Main routing is correct, but the terminal no-edit instruction is contradicted at the end of the same prompt; see Contract Violations. |
| Step 3, honest evidence latitude | Done | `optimizer/context/edit-surface.md:225-246` | Retrieval remains a fixed BM25 top-20 condition and true acquisition changes are routed to Phase 2. |
| Step 4, trends and predictions | Done | `optimizer/prompt/optimizer-instructions.md:141-157,280-286,347-365` | Uses measured 0.06 scatter, three-or-more-iteration trend, and named observables. |
| Step 5, separable bundles | Done | `optimizer/prompt/optimizer-instructions.md:236-246` | Matches the plan. |
| Step 6, inherited facts | Partial | `optimizer/context/playbook.md:94-116`; `optimizer/context/failure-mode-discovery.md:27-31` | The playbook is corrected, but another mandatory agent-read document still states the opposite TRAIN-roster rule. |
| Step 7, driver manifest classification | Done, exposed | `program-v0/manifest.json:90-97`; `optimizer/profiles.py:45-58`; `optimizer/context/edit-surface.md:37-46` | The accepted classification shipped exactly; the promised mechanical boundary did not, and the new Gate F is not a post-edit guard. |
| Gate A2 / F | Partial | `scripts/check_orchestrator_consistency.py:123-183`; `scripts/vm/run_hillclimb_vm.sh:87-116` | Standalone current-tree gate works; within-run enforcement and negative-control coverage are incomplete. |
| Gate A3 / G | Partial | `scripts/check_prompt_hygiene.py:38-97` | Can fail on its regexes, but its deferred register is unused and actual forbidden history passes. |
| Gate A4 / H | Partial | `scripts/check_run_scope.py:46-78,128-168` | Current state and negative controls pass; comparing two jointly editable files is not a stable anchor. |
| Step B factual audit | Partial | `optimizer/context/playbook.md:99-103`; `optimizer/prompt/optimizer-instructions.md:347-355` | Run artifacts reproduce fixed TRAIN rosters (5×50, pairwise Jaccard 1.0), 94/94 non-null mistake `trace_ref`s, byte-identical 8-file historical snapshots, VAL 0.48/0.42 with 16 label changes, floor 0.70, and v5 0.62. The ten historical release files required by Step B are no longer present in any located loop checkout, so their present-on-disk claim cannot be reverified now. |
| Step C | Missing | `scripts/vm/run_hillclimb_vm.sh:164-167`; `optimizer/canary/canary-retrieval.json:12` | The runner would refuse the current tag and the canary hash is stale. |
| Step D | Done | `scripts/check_empty_window_regression.py:39-95` | Gate passes. |
| Step E | Missing | `optimizer-prompt-investigative-latitude.md:592-599` | No live behavioral probe is recorded; the plan and tracking docs say it remains. |
| Landing / cleanup | Missing | `optimizer-prompt-investigative-latitude.md:606-625` | Integration ordering, tag archive, journal promotion, status completion, and landing were not performed. |

## Critical Drift

- **Severity: Critical | plan says the eight definitions cannot be reworded and the driver's prohibitions are non-negotiable; code checks both only before the optimizer edit pass | Evidence:** the editable scope contains rubric, dispatch prompt, and driver (`optimizer/profiles.py:45-58`; `program-v0/manifest.json:35-40,67-72,90-97`), all five gates run once before `dispatcher.py --run` (`scripts/vm/run_hillclimb_vm.sh:87-116,213-232`), and the only post-agent guard re-hashes `contract_file=True` entries (`optimizer/adapter.py:1591-1626`). **Required fix:** before commit/tag, rerun semantic checks against the optimizer-edited checkout—at minimum Gate A and the driver invariants in Gate F—and return a nonzero guarded-agent outcome on failure. Gate G should run there too if prompt hygiene is intended to survive optimizer edits. A pre-run check cannot constrain a mutation made later in that same run.

## Gate Soundness

- **Gate F:** It can fail. Its current-tree regex catches the two named contradiction shapes (`check_orchestrator_consistency.py:43-70,110-120`), and a read-only monkeypatch adding `extractor` to `profiles.IMPLEMENTED_STAGES` made the main gate fail with all four extractor deferrals, confirming the stage-growth tripwire at `:162-171`. The negative controls are only calls to the regex helper (`:186-226`): despite the comment at `:82-84`, they do not test stage growth, stale deferral removal, driver-prohibition deletion, or discovery of the real dispatch-file set. `KNOWN_DEFERRED` is tripwired by stage and by presence of some same-file/same-prohibition match (`:136-171`), but it is class-level rather than occurrence-level: replacing the known sentence with a different forbidden sentence in the same file remains suppressed. Derive dispatch files from the manifest/profile, and pin each deferral to an exact normalized match or digest.
- **Gate G:** It can fail on the nine regex families (`check_prompt_hygiene.py:38-49`), but its negative controls test those regexes rather than the contract. The claimed register is theatre: `KNOWN_DEFERRED` is declared at `:65-69` but never consumed by `main()` at `:80-97`; `src/specs/verdict_schema.md` is neither swept nor checked "exactly as known." The gate also reports clean while swept files still contain change narration, including "this file used to claim otherwise" (`context/playbook.md:99-103`), "an earlier version ... promised" (`context/release-format.md:255-259`), a struck-through superseded instruction (`context/task-and-scoring.md:261-277`), and "four documents used to say" (`context/edit-surface.md:129-138`). Expand the semantic patterns, remove struck-through old instructions, and make deferred entries executable assertions.
- **Gate H:** It can fail, and its four controls exercise the real `inherited()` function over temporary files (`check_run_scope.py:128-168`), so they are genuine. The clean-sheet SHA comparison itself is not robust: `SHEET` is compared only with `STUB` (`:46-47,58-78`), and both are ordinary optimizer-side files. If a previous session changes both to the same inherited content, Gate H passes. Anchor the stub to committed bytes (`git show HEAD:<stub>` plus a clean-worktree assertion) or a pinned digest, then compare the sheet to that anchor. The environment override is loud and appropriate (`:106-123`).

## The Mirrored-Copy Question (item 3)

A mirrored-copy agreement gate is warranted for the ladder, and existing validator coverage is not sufficient. The repository already documents the concrete failure: the judge follows the dispatch copy while `validate_sarol.py` parses the rubric copy, so a rubric-only optimizer edit is behaviorally inert and can then make otherwise valid output fail validation (`optimizer/context/edit-surface.md:150-166`). The parser proves only that one rubric fence contains all labels (`optimizer/validate_sarol.py:152-170`); the validator then enforces that rubric order (`:302-323`). It never establishes what order the judge was told to use.

Parse both judge-path ladders and require identical nine-label order after every optimizer edit. Also require the single-sub-claim exception in both copies. The exception is less dangerous than the ladder because worst-wins over one valid label is mathematically identical to returning that label, and the current generic validator therefore enforces the same result even without a special branch (`validate_sarol.py:304-323`). Still, an agreement assertion is cheap, prevents contradictory instructions, and closes the dominant length-1 read path identified at `context/release-format.md:141-146`. This should be a semantic post-edit invariant, not added to Gate A's paper-text regex alone.

## Missing Pieces

- The canonical recut is not done: old tags remain, `program-v0` fails the 10-entry composed-tree check, and v1–v5 are not archived (`optimizer-prompt-investigative-latitude.md:104-109,571-574`).
- The canary was not re-pinned: recorded hash `0a02710cbd88` differs from manifest `7431a5bc98a9` (`optimizer/canary/canary-retrieval.json:12`; `program-v0/manifest.json:15`).
- Gate E is unimplemented/unrun (`optimizer-prompt-investigative-latitude.md:592-599`).
- The landing journal promotion and plan completion remain (`optimizer-prompt-investigative-latitude.md:620-625`); no `docs/journal/2026-09-09-table-1-reconciliation.md` appears in the branch diff.

## Contract Violations

- The optimizer-facing edit-surface contract contradicts the manifest. It says the definitions file is "not part of the program" and "in no manifest entry" (`optimizer/context/edit-surface.md:129-138`), while it is a frozen entry (`program-v0/manifest.json:74-80`). The same file's frozen-files table says there are three and omits it (`edit-surface.md:48-55`). `task-and-scoring.md` repeats "not part of the program" (`:23-29`). Conversely, the manifest's retained prose says the optimizer may edit "definitions" (`program-v0/manifest.json:111`), although the adapter enforces the opposite. This is the exact false-instrument-fact class Step 6 was meant to eliminate.
- The TRAIN sampling story contradicts itself. `failure-mode-discovery.md` says the batch "is re-drawn every iteration" and absence may mean not drawn (`:27-30`); `playbook.md` correctly records the measured identical roster and tells the optimizer to inspect `draw_history.json` (`:94-116`). The artifact audit measured five 50-claim sets, all equal, minimum pairwise Jaccard 1.0.
- The no-edit terminal route contradicts itself in one injected prompt. The operative section requires a findings entry (`optimizer-instructions.md:254-260,288-315`); the final "Never stop early" section instead tells the optimizer to write the result to `meta-learnings.md` (`:437-449`), violating the mutually exclusive routing rule and the ban on promoting run-specific harness observations.

## Test Gaps

- No post-edit semantic guard covers Gate A, Gate F, Gate G, or mirrored ladder agreement (`optimizer/adapter.py:1591-1626`).
- Gate F selftests omit the allowlist stage-growth and stale-entry claims they advertise (`scripts/check_orchestrator_consistency.py:82-84,186-226`).
- Gate G's deferred entry is dead data and no negative control proves scope completeness (`scripts/check_prompt_hygiene.py:51-69,80-118`).
- Gate H has no control where both sheet and stub are changed together (`scripts/check_run_scope.py:128-168`).
- The VM suite loop omits `evidence_producers.py`, even though it is the runnable retrieval path and contributes 26 checks to the claimed 447 (`scripts/vm/run_hillclimb_vm.sh:155-162`).
- `sampling.py --selftest` writes through the production gold-root default instead of installing a temporary gold root itself (`sampling.py:671-685`; `stage_claim.py:48-53`).

## Defensible Deviations

- Step 0 does not literally say every definition is "ours" because P0 made that false; the shipped paper-layer/house-layer distinction preserves the intended gold-is-objective rule (`optimizer-instructions.md:11-37`).
- Keeping the driver wholly editable is the explicit accepted Step 7 decision, and placing it in `JUDGE_SCOPE` makes that decision effective for retrieval (`optimizer/profiles.py:52-58`). The deviation is not the classification; it is treating preflight visibility as a bound on later optimizer edits.
- Gate H is appropriately labeled a stopgap pending per-run clones (`check_run_scope.py:11-17`). Its architecture debt is documented rather than hidden.
- The 50/50 sampling result with a temporary gold root shows the two initial failures were caused by this audit sandbox's read-only home, not by pool/stager disagreement. The undeclared write dependency should still be removed.

## Suggested Code Edits

1. Extend `ContractGuardedAgent.run()` to execute semantic post-edit checks over the live checkout before returning success: paper definitions/retired clauses, mirrored ladder + exception, driver hard prohibitions, and prompt hygiene (`optimizer/adapter.py:1611-1626`).
2. Make Gate F derive its dispatch paths from the manifest/profile and represent each deferral as an exact normalized offending match plus arming stage; add selftests for stage growth, stale entries, prohibition deletion, and path-set growth (`scripts/check_orchestrator_consistency.py:73-98,136-171,186-226`).
3. Implement Gate G's `KNOWN_DEFERRED` logic, assert a fixed/derived file set instead of silently dropping missing paths, and remove the four current pieces of changelog prose cited above (`scripts/check_prompt_hygiene.py:51-97`).
4. Anchor Gate H's stub to committed bytes, then compare the sheet against it (`scripts/check_run_scope.py:46-78`).
5. Reconcile all manifest/edit-surface statements: definitions are frozen program, judge-inert; rubric boundaries are editable; driver is editable (`program-v0/manifest.json:111`; `optimizer/context/edit-surface.md:48-55,129-138`; `optimizer/context/task-and-scoring.md:23-29`).
6. Replace the stale TRAIN-redraw paragraph and the stale no-edit/meta-learnings instruction with the already-canonical rules (`failure-mode-discovery.md:27-31`; `optimizer-instructions.md:447-449`).
7. Complete Step C in its specified order: recut/verify `program-v0`, archive v1–v5, re-pin the canary three times at `7431a5bc98a9`, then run materialization and all gates. Update stale tracking counts/hashes (`docs/plans/README.md:40`; `docs/plans/NEXT.md:12-14`; `scripts/materialize_smoke.py:17`).
8. Make the sampling selftest install its own temporary `PAPER_TRAIL_GOLD_DIR`, and add `evidence_producers` to the VM suite loop (`sampling.py:664-685`; `scripts/vm/run_hillclimb_vm.sh:158`).

## Questions For The Author

1. Was Gate F intentionally designed only as a pre-run audit even though the driver becomes editable after that check? If so, what mechanism is expected to enforce "non-negotiable" during an iteration?
2. Is `program-v0/manifest.json:111` intended to remain agent-facing contract text? It directly preserves the pre-P0 rule that definitions are editable.
3. Should Gate G enforce its stated rule semantically, or only a narrow lexical house style? Its current pass includes struck-through superseded instructions and explicit change narration.
4. Were the historical release payloads deliberately removed? If yes, where is Step B's durable evidence that both release files existed for all five iterations meant to live after checkout cleanup?

## Audit Trail

- Read in required order: `docs/claude_ops.md`; all 626 lines of the plan including Verification A/A2/A3/A4/B/C/D/E and Landing; `git diff sarol-optimizer-concurrent..HEAD`; then the 30 touched files. Also read the live driver and validator paths needed to adjudicate Steps 7 and the mirrored-copy question.
- Branch: `feat/optimizer-prompt-latitude`, HEAD `94a376f`; range contains 25 commits and 30 files, +2240/-371. Working tree was clean before the audit.
- Read `git log --oneline sarol-optimizer-concurrent..HEAD` for commit intent.
- Independently checked the eight strings against Sarol et al. 2024 §2.2 at `https://pmc.ncbi.nlm.nih.gov/articles/PMC11231046/`; all eight current strings are exact. The paper also states categories are priority-ordered, but the repository's separate house ladder is intentionally optimizer-editable.
- Reproduced from preserved run manifests: identical historical program snapshots (`0a02710cbd88`, 8 files); VAL `24/50=0.48` versus `21/50=0.42`; 16/50 predictions changed; the 2026-09-09 VAL gold distribution is ACCURATE 35, ETIQUETTE 6, CONTRADICT 4, NOT_SUBSTANTIATE 3, INDIRECT 1, IRRELEVANT 1 (floor 0.70); program-v5 is 31/50=0.62; TRAIN draw history is five identical 50-claim sets; 94/94 mistake rows carry non-null `trace_ref`.
- Verified Gate F's growth tripwire without editing files by monkeypatching `profiles.IMPLEMENTED_STAGES` in memory to include `extractor`; the gate returned 1 with four armed extractor contradictions.
- No source, plan, or existing documentation was edited. Only this requested feedback file was created; no commit was made.
