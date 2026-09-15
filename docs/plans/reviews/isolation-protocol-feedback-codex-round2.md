Reference: docs/claude_ops.md

# Feedback: The isolation protocol (Codex review, round 2)

## Verdict
Blocked. The core container-first design mostly survives spot-checking, but the current plan is not safe as an implementation handoff until it removes stale driver/Task verification text, corrects the shared-wrapper permission claim, and narrows the rad-eval `release_train.json`/gold-label claim to what the code actually exposes.

## Critical Gaps
- Severity: Critical | Gap | Verification still contains old driver/Task topology requirements after OQ1 removes the driver session | Why it matters | A fresh implementer could build or gate the wrong topology: the plan says no Task subagent in the concrete build list, but the green-by-absence table still says V0c should run the "real driver->Task topology" and V2a-live requires "Task available" | Evidence: docs/plans/isolation-protocol.md:237; docs/plans/isolation-protocol.md:239; docs/plans/isolation-protocol.md:1841; docs/plans/isolation-protocol.md:1844; docs/plans/isolation-protocol.md:1874 | Required fix | Sweep verification and gate summaries so every gate consistently asserts direct `dispatch_prompt.py` -> `claude --print`, no driver session, no Task, and "Task absent" rather than "Task available".
- Severity: Critical | Gap | The plan says the bypass flag is not passed by the consumer, but paper-trail's current judge command passes it directly | Why it matters | The upstream `engine/claude_wrapper.py` change is necessary for the optimizer path, but it is not sufficient for the program/judge path. An implementer who only changes the shared wrapper leaves `SarolRunner._stage_command()` still running with bypass permissions | Evidence: /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/claude_wrapper.py:128; /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/claude_wrapper.py:130; experiments/sarol-2024/optimizer/adapter.py:712; experiments/sarol-2024/optimizer/adapter.py:714 | Required fix | Split the requirement by path: engine wrapper must make bypass caller-selectable for optimizer/DockerAgent users, and paper-trail must replace the direct `_stage_command()` bypass flag in the judge invocation.
- Severity: Critical | Gap | The newest rad-eval allowlist claim overstates paper-trail's direct gold exposure through `release_train.json` | Why it matters | The boundary still needs to deny `iter/`, but the current rationale says `release_train.json` itself carries per-claim gold labels. Current paper-trail code puts per-claim `gold_label` in the TRAIN mistake corpus, while `release_train.json` carries `corpus.ref`, counts, and metrics/breakdown. If the sentinel is planted only in `release_train.json`, the test may prove the wrong thing | Evidence: /Users/philadamson/Documents/Misc/Projects/rad-eval/hooks/policy.py:183; /Users/philadamson/Documents/Misc/Projects/rad-eval/hooks/policy.py:187; experiments/sarol-2024/optimizer/adapter.py:1178; experiments/sarol-2024/optimizer/adapter.py:1187; experiments/sarol-2024/optimizer/adapter.py:1219; experiments/sarol-2024/optimizer/adapter.py:1224; experiments/sarol-2024/optimizer/adapter.py:1533; experiments/sarol-2024/optimizer/adapter.py:1544 | Required fix | Reword to: rad-eval grants release files by glob, including `release_train.json`; paper-trail's TRAIN release can point to the gold-bearing mistake corpus and include TRAIN metrics, but the per-claim gold labels are in `mistakes/<batch>.json`. Plant/probe sentinels in both `iter/*/release_train.json` and the referenced mistake corpus path, or explain why denying `iter/` is sufficient.
- Severity: Critical | Gap | Per-stage mount-set scope remains an open decision inside a plan that otherwise tells implementers what to build | Why it matters | The plan correctly says the prefix must key on `(stage, claim, version)`, but it only derives the adjudicator mount set and leaves extractor/verifier as an "Open decision." That is acceptable as a product decision, not as a handoff for Phase 1c if agentic profiles are reachable soon | Evidence: docs/plans/isolation-protocol.md:181; docs/plans/isolation-protocol.md:183; docs/plans/isolation-protocol.md:212; docs/plans/isolation-protocol.md:237; experiments/sarol-2024/optimizer/adapter.py:866; experiments/sarol-2024/optimizer/profiles.py:268 | Required fix | Either explicitly scope this implementation to `retrieval`/adjudicator-only and add a hard preflight refusing multi-stage profiles until extractor/verifier mount sets are specified, or derive all three stage mount sets now.

## Spot-Check Results
- 1. CONFIRMED | 22 direct `SarolRunner(` construction sites: 19 in `_selftest()` under `adapter.py:1642`, plus `dispatcher.py:554`, `canary.py:257`, and `scripts/run_baseline.py:119`. `_RealInvokerRunner` is declared at `adapter.py:2739`, overrides `_stage_command()` at `adapter.py:2742`, and inherits `SarolRunner.__init__()` from `adapter.py:624`.
- 2. CONFIRMED | `run_optimization()` accepts `components=` at `dispatcher.py:590` and `dispatcher.py:604`, uses `parts = components or build_components(...)` at `dispatcher.py:748`, and the selftest exercises this path at `dispatcher.py:1222`.
- 3. PARTLY | The shared wrapper unconditionally passes `--dangerously-skip-permissions` at `agentic-label-opt/engine/claude_wrapper.py:130`, but paper-trail's current consumer runner also passes it directly at `adapter.py:714`.
- 4. CONFIRMED | At engine `c2dd0b3`, `train_inputs` is callable-capable at `engine/loop.py:193`, `val_inputs` is plain at `engine/loop.py:194`, the docstring says fixed at `engine/loop.py:257`, and VAL is consumed unchanged at `engine/loop.py:377` and `engine/loop.py:475`.
- 5. PARTLY | Commits `82f547d` and `ee26d80` exist. `LoopStop.reason` is real at `engine/loop.py:63`, probe scoring is guarded at `engine/loop.py:469`, and partial-run enrichment is at `engine/loop.py:607`-`621`, not the plan's `:544-558`. `manifest_for_version` is real at `engine/loop.py:217` and fails closed at `engine/loop.py:280`-`299`.
- 6. PARTLY | rad-eval grants release files by glob (`iter/*/release_*.json`) at `rad-eval/hooks/policy.py:183`-`187` and `meta-learnings.md` by name at `rad-eval/hooks/policy.py:194`. Paper-trail's per-claim gold labels are in the TRAIN mistake corpus (`adapter.py:1178`-`1248`), not directly in `release_train.json`; the release carries the corpus reference and metrics at `adapter.py:1533`-`1548`.
- 7. CONFIRMED | The dispatch loop is per-stage at `adapter.py:866`, and `_stage_command(stage, ...)` already takes the stage at `adapter.py:700`. Phase 1c says the factory must key on stage at `docs/plans/isolation-protocol.md:237` and `docs/plans/isolation-protocol.md:871`, but the extractor/verifier mount-set decision remains open at `docs/plans/isolation-protocol.md:212`.
- 8. CONFIRMED | This branch's manifest has 8 entries at `experiments/sarol-2024/program-v0/manifest.json:17`-`82`; Plan A tip `f02d761` has 10 entries and includes `.claude/commands/sarol-eval-item.md` at `manifest.json:90`-`97`. The forward reference is called out at `docs/plans/isolation-protocol.md:2248`, but it is only safe if the implementer rebases first.
- 9. CONFIRMED | The inlined §4g items 1-7 and 9 map to phases as claimed at `docs/plans/isolation-protocol.md:56`-`66` and `docs/plans/isolation-protocol.md:79`-`80`. Item 8 is not in that mapping sentence but is mapped elsewhere to Phase 1b/1g and engine generic seal work at `docs/plans/isolation-protocol.md:787` and `docs/plans/isolation-protocol.md:1035`.
- 10. CONFIRMED | In rad-eval Docker mode the agent deletes/does not use `audit_ledger` at `rad-eval/src/optimizer_loop/docker_agent.py:79`-`84`; the engine initializes `denied = 0` and only changes it when `audit_ledger is not None` at `agentic-label-opt/engine/loop.py:492`-`521`. So `denied=0` proves no hook rows existed, not that no denial-worthy action happened.

## Failure Modes
- Scenario | Why the plan misses it | What to add
- Implementer changes only `engine/claude_wrapper.py` and leaves paper-trail `_stage_command()` on bypass | The plan says the flag is not ours to pass, but the judge path passes it directly today | Add a paper-trail acceptance check that no shipping judge argv contains `--dangerously-skip-permissions`.
- Sentinel planted in `release_train.json` passes while the judge can still read `mistakes/<batch>.json` | The plan conflates the release file with the gold-bearing per-claim corpus | Probe both the release path and every corpus ref reachable from a TRAIN release.
- Multi-stage profile is enabled before extractor/verifier mount sets exist | The plan keys the prefix on stage but leaves stage-specific mounts undecided | Add a hard preflight refusing non-adjudicator stages until their mount sets are specified and tested.
- A stale verification gate reintroduces `Task` | The verification table still contains old topology text | Make V0c/V2h assert no subagent is spawned and no `Task` tool is available.
- A green selftest silently skips engine checks | The plan notes the `AGENTIC_LABEL_OPT` skip hazard but there is no repo-local checklist to force it | Add a repo-grounded implementation checklist with exact commands and expected pass counts.

## Contract Checks
- paper-trail | `SarolRunner` construction/refusal contract | Constructor refusal is the right locus because it covers direct sites and `components=` bypass. The plan must require a reachability census that counts subclasses, not only text matches.
- paper-trail | Release/mistake-corpus output contract | `ReleasePayloadTrain.corpus` is adapter-owned and points at a gold-bearing mistake corpus. The plan must distinguish the release envelope from the file behind `corpus.ref`.
- paper-trail | Manifest/version contract | Current branch has 8 entries; Plan A has 10. The plan addresses this, but handoff must say "do not implement before rebasing to Plan A tip" as a hard gate, not just a warning.
- paper-trail | Engine dependency contract | There is no `pyproject.toml`, `requirements.txt`, or lockfile in this checkout; runtime imports use `DEFAULT_ENGINE`/`AGENTIC_LABEL_OPT` at `adapter.py:102` and `adapter.py:117`-`118`, duplicated in `experiments/sarol-2024/scripts/materialize_smoke.py:39`. Creating `pyproject.toml` with a git revision pin is adequate only if the runtime import path is changed to use the installed package outside selftests.
- agentic-label-opt | `isolation/docker_prefix.py` | Surface: env rendering. Plan addresses by-name env, but must state default/backward-compatible behavior for rad-eval and crc.
- agentic-label-opt | `isolation/negative_control.py` and `tests/test_isolation_negative_control.py` | Surface: generic seal proof. Plan addresses exact mount-set/probe requirements; keep paper-trail-specific sentinels out of the engine.
- agentic-label-opt | `engine/claude_wrapper.py` | Surface: permission mode and bypass flag. Plan must require an API preserving existing consumers unless they opt into deny-by-default, then pin paper-trail to that revision.
- agentic-label-opt | `isolation/Dockerfile` and `isolation/README.md` | Surface: CLI version/image provenance. Plan addresses re-pin and digest recording; migration story should say consumers that rely on older image behavior must rebuild and record digest.
- agentic-label-opt | `engine/loop.py` | Surface: `val_inputs` signature and probe consumption. Backward-compatible for plain `RunInputs`, but tests must cover rad-eval's and crc's existing plain-value calls. I could not inspect crc because no crc checkout path was in scope.

## Re-use vs. building something you don't need yet
- Decision point | Plan's current choice | Reusable alternative + the realistic use case it would serve | Recommendation, OR "raise to user" when realistic use is unclear.
- Program/optimizer container path building | New `optimizer/isolation.py` wraps mount-set builders and path maps | Reuse engine `build_docker_cmd_prefix()` and rad-eval's `DockerAgent` staging/copy-back pattern; crc is a realistic later user of a gold-holding program container | Recommendation: keep `optimizer/isolation.py` as a thin consumer adapter over engine primitives, with mount contents as data, not a second Docker renderer.
- Seal negative control | Split generic seal logic upstream and paper-trail sentinels locally | Reuse engine `run_probe()`/fixture helpers and add exact mount-set assertions upstream | Recommendation: correct modular split.
- Deterministic dispatch | New `optimizer/dispatch_prompt.py` | Reuse slot-source logic from `evidence_producers.py:201`-`216` and validation vocabulary from `validate_sarol.py:266`; do not reimplement staging-info parsing differently | Recommendation: build the module, but explicitly mark it harness-owned and non-editable.
- Per-run reset | Plan replaces clone with archive/reset | rad-eval's per-run clone is useful for concurrent namespaces, which paper-trail says it will not need | Recommendation: reset is fine for paper-trail; raise to user only for the remaining `program-v*` tag namespace decision.
- Per-stage mount sets | Plan derives adjudicator only | A generic per-stage mount-set table would serve future crc/program-stage containers | Recommendation: raise to user now: adjudicator-only with hard refusal, or derive all stages.

## Verification Gaps
- No repo-local checklist exists; per the prompt, this should be flagged. A checklist with exact branch, engine SHA, Plan A rebase state, Docker availability, `AGENTIC_LABEL_OPT`, Python version, and expected selftest counts would sharpen the handoff.
- V0c/V2a-live/V2h need topology cleanup: assert direct judge invocation, no `Task`, and no old driver session.
- V2f must check both wrapper and consumer command surfaces for bypass and token leakage.
- V2a-seal should enumerate and probe corpus refs in addition to `iter/*/release_train.json`.
- Cross-repo engine tests should include "existing plain `val_inputs` consumers still work" and one callable `val_inputs` test that reaches both current VAL and probe VAL.
- Real-data/GPU/high-throughput validation is mostly specified, but the plan should add a non-paid dry run that validates generated argv/prefixes for all stage/profile combinations before the paid one-claim V0c.

## Handoff Readiness
- Missing handoff detail | Which permission surface owns bypass removal? | Proposed fix: list both `agentic-label-opt/engine/claude_wrapper.py` and `paper-trail/adapter.py::_stage_command()` with separate acceptance checks.
- Missing handoff detail | Where exactly do per-claim gold labels live after scoring? | Proposed fix: document `release_train.json -> corpus.ref -> mistakes/<batch>.json`, and update sentinel locations.
- Missing handoff detail | Are extractor/verifier mount sets in scope? | Proposed fix: make the open decision a hard pre-implementation decision, or add an explicit adjudicator-only preflight.
- Missing handoff detail | How does the new `pyproject.toml` change runtime import behavior? | Proposed fix: state whether `adapter.engine_path()` remains selftest-only, how scripts launch under uv, and whether `AGENTIC_LABEL_OPT` is still accepted.
- Missing handoff detail | What does "other consumers unchanged" mean for rad-eval and crc? | Proposed fix: name the specific engine tests or consumer smoke checks required for each engine file. I could inspect rad-eval, but crc was not in the provided repo set.
- Implementation-forward hygiene | The nine-item "Open Questions" section is all resolved but still occupies the spec | Proposed fix: fold resolutions into normative sections and move historical Q/A to an appendix; leave only the `program-v*` tag namespace as a true open decision.
- Implementation-forward hygiene | The plan admits ~120 stale "judge" uses | Proposed fix: do the naming sweep before implementation. This is not cosmetic because "judge" vs "program" changes the per-stage mount-set interpretation.

## Suggested Revisions
- Replace every verification reference to driver->Task, "Task available", or V2i inheritance with direct-dispatch/no-subagent assertions.
- Change the bypass prerequisite language to say "shared wrapper and paper-trail judge command both currently pass bypass."
- Reword the rad-eval READ_WHITELIST claim to "glob grants `iter/*/release_*.json`, including `release_train.json`" and reword paper-trail gold exposure to the actual `corpus.ref`/mistake-corpus path.
- Promote the Plan A rebase requirement from warning to landing precondition.
- Add a compact repo-grounded checklist at the top of Verification.
- Resolve or explicitly defer the extractor/verifier mount-set decision before coding starts.

## Questions For The Author
- Is this implementation adjudicator-only until a later stage-profile plan, or must it derive extractor and verifier mount sets now?
- Should paper-trail continue supporting `AGENTIC_LABEL_OPT` as an override after adding `pyproject.toml`, or should that path become selftest/development-only?
- For `program-v*` identity, are tags being namespaced per run or replaced by manifest `combined_hash` before Phase 4 lands?

## Audit Trail
- Files inspected (paths only).
- docs/claude_ops.md
- docs/plans/isolation-protocol.md
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/canary.py
- experiments/sarol-2024/optimizer/profiles.py
- experiments/sarol-2024/optimizer/sampling.py
- experiments/sarol-2024/optimizer/validate_sarol.py
- experiments/sarol-2024/optimizer/context/task-and-scoring.md
- experiments/sarol-2024/optimizer/context/edit-surface.md
- experiments/sarol-2024/program-v0/manifest.json
- experiments/sarol-2024/scripts/run_baseline.py
- experiments/sarol-2024/scripts/materialize_smoke.py
- experiments/sarol-2024/scripts/vm/run_hillclimb_vm.sh
- .claude/commands/sarol-eval-item.md
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/claude_wrapper.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/schemas.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/isolation/docker_prefix.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/isolation/open_profile.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/isolation/negative_control.py
- /Users/philadamson/Documents/Misc/Projects/agentic-label-opt/tests/test_isolation_negative_control.py
- /Users/philadamson/Documents/Misc/Projects/rad-eval/hooks/policy.py
- /Users/philadamson/Documents/Misc/Projects/rad-eval/src/optimizer_loop/docker_agent.py
- /Users/philadamson/Documents/Misc/Projects/rad-eval/src/optimizer_loop/allowed_tools.py
- /Users/philadamson/Documents/Misc/Projects/rad-eval/pyproject.toml
- /Users/philadamson/Documents/Misc/Projects/rad-eval/uv.lock
