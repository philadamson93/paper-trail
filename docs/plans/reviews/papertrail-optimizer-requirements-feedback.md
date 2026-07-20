Reference: docs/claude_ops.md

# Feedback: papertrail-optimizer-requirements (Codex review)

## Verdict
Revise. The plan has the right problem framing, but it is not yet a fresh-agent-ready handoff: the required header is missing, core implementation choices remain unresolved, and several cross-repo/shared-engine contracts are named but not pinned precisely enough to implement.

## Critical Gaps
- Severity: Critical | Gap | The plan omits the required `Reference: docs/claude_ops.md` header and starts directly with the title. | Why it matters | This violates the repo's own plan contract and weakens traceability for a cross-repo handoff. | Evidence: docs/plans/papertrail-optimizer-requirements.md:1, docs/claude_ops.md:34 | Required fix | Add `Reference: docs/claude_ops.md` as line 1 and keep the title below it.
- Severity: Critical | Gap | The plan leaves the adjudicator/program-v0 choice open while downstream sections assume the mainline-plus-new-collapse path. | Why it matters | Phase 2c cannot freeze `program-v0`, define `agent_instructions`, or build the scorer until this is resolved; the plan itself says B1/C1 must be re-derived if the Sarol variant is chosen. | Evidence: docs/plans/papertrail-optimizer-requirements.md:48, docs/plans/papertrail-optimizer-requirements.md:71, docs/plans/papertrail-optimizer-requirements.md:119 | Required fix | Move the A2 decision to a resolved Decisions section, or split the plan into two explicit branches with separate filesets, release schemas, scorer mappings, and verification gates for each.
- Severity: Gap | Gap | The shared-engine contract is not pinned to concrete schema/version files or migration steps in the paper-trail repo. | Why it matters | The engine plan requires `papertrail/optimizer/adapter.py`, `experiments/sarol-2024/program-v0/`, structural tests, `ProgramManifest`, `RunInputs`, `RunArtifacts`, `ScoreResult`, `MistakeCorpus`, `ReleasePayload`, and `PolicyConfig`; this plan mostly describes concepts and does not state exact typed fields, version pins, or lockstep updates. | Evidence: docs/plans/papertrail-optimizer-requirements.md:94, /Users/philadamson/Documents/Stanford/VISTA/code/crc-extraction-agent/docs/plans/2026-07-10-shared-optimization-engine-package.md:251, /Users/philadamson/Documents/Stanford/VISTA/code/crc-extraction-agent/docs/plans/2026-07-10-shared-optimization-engine-package.md:267 | Required fix | Add a contract table naming owner repo, schema-of-record path, exact fields/enums/types, version pin, migration behavior, and tests for each engine surface.
- Severity: Gap | Gap | The plan relies on `src/*` paths while the checked-out `sarol` branch still exposes production files under `.claude/*`; it does not state whether implementation begins by merging/rebasing `main` or by reading files via `git show main:...`. | Why it matters | A fresh agent on `sarol` cannot open several files named in the plan from the worktree, and a freeze/tag can accidentally capture stale pre-repo-org files. | Evidence: docs/plans/papertrail-optimizer-requirements.md:26, docs/plans/papertrail-optimizer-requirements.md:40, CLAUDE.md:16 | Required fix | State the branch-reconciliation command sequence and source-of-truth paths before any `program-v0` freeze; include the old `.claude/*` to new `src/*` migration map.

## Failure Modes
- Scenario | `program-v0` is tagged from stale `sarol` branch prompt paths. | Why the plan misses it | Verification says to diff `main sarol -- src/prompts/`, but the current branch does not have those worktree paths and the plan does not state the merge/rebase operation. | What to add | A stop-before-tag gate that asserts the reconciled tree contains `src/prompts/extractor-dispatch-paperclip.md`, `src/prompts/extractor-dispatch-pdf.md`, `src/prompts/adjudicator-dispatch.md`, `src/prompts/verifier-dispatch.md`, and `src/specs/verdict_schema.md`.
- Scenario | The new scorer reports macro-F1 on a cherry-picked denominator by excluding `AMBIGUOUS`. | Why the plan misses it | It notes the caveat, but does not define `ScoreResult.primary_metric` versus reported breakdown fields for abstention-adjusted and misses-included metrics. | What to add | Pin one metric as `primary_metric` and require the other in `breakdown`, with names and denominator rules.
- Scenario | Nested Claude Code subagents can read gold/VAL/TEST paths even though the outer dispatcher is trusted. | Why the plan misses it | The engine plan has a Phase-3 nested-session negative control, but this plan's verification stops at adapter smoke and budget checks. | What to add | Add a paper-trail Phase-3 negative control: a nested extractor/adjudicator/verifier probe for sibling VAL/TEST/gold paths must fail.
- Scenario | The Sarol 9-class parser is reused for mainline `overall_verdict` output without a real migration. | Why the plan misses it | `parse_verdict.py` is hard-wired to `rubric_variant=sarol_2024_9class` and the Sarol 9-label enum, while the recommended plan path uses native 12-value `overall_verdict`. | What to add | A new scorer module or explicit migration patch list with fixtures covering all native `overall_verdict` values.

## Contract Checks
- Owner repo: `agentic-label-opt` package, repo not yet created/owner unresolved. Surface: engine Protocol/dataclass contract (`ProgramManifest`, `RunInputs`, `RunArtifacts`, `ScoreResult`, `MistakeCorpus`, `ReleasePayload`, `PolicyConfig`). The engine plan says Phase 0 creates these typed contracts; paper-trail does not pin the package SHA/API version it will consume or how its adapter will migrate if the package breaks the envelope.
- Owner repo: paper-trail. Surface: `ProgramManifest` fileset. The plan names prompt/rubric globs, but omits manifest path, manifest schema version, content hash format, and exact behavior if topology-free mode includes `src/commands/paper-trail.md` / `src/commands/ground-claim.md`.
- Owner repo: paper-trail. Surface: scorer schema. `src/specs/verdict_schema.md` 1.1 defines required `source_mode` and conditional `paperclip_handle`, plus native `overall_verdict`; current Sarol parser expects Sarol 9-class output. The plan needs a schema-of-record for native-to-3-way scoring and fixtures for schema 1.0-to-1.1 migration.
- Owner repo: paper-trail. Surface: release payload. C1 lists `metrics`, `error_class_counts`, `followups`, `frontier`, `budget`, `prior_change_note`, and mistake-corpus access, but does not define JSON/Pydantic fields, `extra="forbid"` owner, version field, or accept/reject tests.
- Owner repo: crc-extraction-agent. Surface: sibling CRC plan pointer. The paper-trail plan references `crc-optimizer-requirements.md`, but the reachable file is `/Users/philadamson/Documents/Stanford/VISTA/code/crc-extraction-agent/docs/plans/2026-07-16-crc-optimizer-requirements.md`; fix the exact path or document the alias.
- Owner repo: crc-extraction-agent / engine plan. Surface: Phase 3 paper-trail isolation. The engine plan expects `dev/isolation/` extension and an Anthropic-egress/public-API negative control; this repo does not have `docs/plans/run-isolation-framework.md`, so the paper-trail plan must either point to the actual local isolation design or state it is new work.

## Modularity vs. YAGNI
- Decision point | Native mainline scorer vs Sarol-variant scorer. | Plan's current choice | Recommends native mainline plus a scoring adapter, but keeps Sarol variant open. | Modular alternative + realistic use case it would serve | A scorer interface with two concrete mappings (`native_overall_v1_1_to_sarol3`, `sarol9_to_sarol3`) would serve the real near-term need to compare old Sarol scaffolding against the current shipped product. | Recommendation | Modularize this mapping layer; the plan already has two realistic consumers.
- Decision point | Topology-fixed vs topology-free manifest. | Plan's current choice | Recommends fixed topology but leaves Phil's D32 topology-free design open. | Modular alternative + realistic use case it would serve | A manifest profile enum (`leaf_prompts_only`, `orchestrator_plus_leaf_prompts`) would let v0 start small while preserving the existing Sarol research question about optimizer-editable topology. | Recommendation | Raise to user and record the chosen profile explicitly.
- Decision point | Release payload structure. | Plan's current choice | Prose list of payload sections. | Modular alternative + realistic use case it would serve | A versioned `PaperTrailReleasePayload` schema with opaque `breakdown`/`mistake_corpus_ref` fields serves the shared engine's multi-consumer envelope and paper-trail's need to evolve error classes. | Recommendation | Modularize as a schema, not prose.
- Decision point | Reuse-vs-rewrite: cost accounting. | Plan's current choice | Reuse `parse_verdict.py`'s `PRICING` and `estimate_cost_usd`. | Modular alternative + realistic use case it would serve | Move cost summarization behind the adapter's budget/cost interface so nested-agent invocation count can be tracked alongside token cost. | Recommendation | Reuse the existing function initially, but do not duplicate cost logic in the optimizer prompt or release builder.
- Decision point | Reuse-vs-rewrite: scoring/collapse. | Plan's current choice | Build a new native collapse, with prior Sarol logic as inspiration. | Modular alternative + realistic use case it would serve | Extract a shared collapse helper from existing Sarol `to_3way()` and add a native adapter; avoids duplicating label-collapse logic. | Recommendation | Reuse the existing Sarol 9-class collapse for the Sarol variant and add only the native mapping as new code.

## Verification Gaps
- Missing exact schema fixture coverage for every native `overall_verdict` value, including `CONFIRMED_WITH_MINOR`, `AMBIGUOUS`, and workflow states that should be excluded or rejected.
- Missing Phase 2c structural adapter tests required by the engine plan for `ProgramManifest`, materialization, scorer envelope validation, and release payload `extra="forbid"` behavior.
- Missing additive-only verification for schema 1.0 to 1.1, which the engine plan explicitly requires before accepting scorer parity drift.
- Missing nested-subagent filesystem/tool-scope negative control for the Phase-3 paper-trail isolation profile.
- Missing local cost/runtime preflight criteria before running 10/25/50/100/200/2,141 claim ramps; the plan names estimates as needed but does not make them a gate.
- VM-handoff canonical spec lens skipped: `docs/claude_ops.md` is not a symlink and no reachable `references/verification-and-handoff-design.md` was found from this repo. The engine plan independently states paper-trail Phase 2c/3/4 are local-machine, no `vm-status` docs.

## Handoff Readiness
- Gap | Files and line ranges are not stated directly. | Specific question | Which exact files does a fresh agent create or modify for Phase 2c? | Proposed fix | Add a `Files to Modify / Create` table with paths and nearest sister files: `papertrail/optimizer/adapter.py`, `experiments/sarol-2024/program-v0/manifest.json`, `experiments/sarol-2024/optimizer/context/*.md`, scorer module(s), tests, and docs.
- Gap | Contract changes do not name schema-of-record files. | Specific question | Where is the release payload schema defined and versioned? | Proposed fix | State the schema file path, field list, version field, and lockstep updates to adapter tests and optimizer context docs.
- Gap | Success criterion is split between "first real scoring run" and engine Phase 4 optimization. | Specific question | Does this plan finish at Phase 2c smoke, first baseline score, or one optimization iteration? | Proposed fix | State the terminal success criterion in one sentence and align Verification/Landing to it.
- Gap | Open Questions remain after purported decisions. | Specific question | Is this ready for implementation if A2, topology, collapse correctness, and frontier metric permanence are unresolved? | Proposed fix | Move unresolved items to pre-implementation gates or resolve them before marking the plan Completed.
- Gap | In-flight coordination is incomplete. | Specific question | How does `sarol` reconcile with `main`, `repo-organization`, `feature-paperclip-first-architecture`, and the engine package Phase 0 SHA? | Proposed fix | Add a merge sequence with exact branches/SHAs to verify and stop conditions before tag creation.
- Gap | Landing plan omits cross-repo exact status checks. | Specific question | What status string does the engine repo check, and in which exact file? | Proposed fix | Use the engine plan's requirement: `papertrail-optimizer-requirements.md` reaches `Reviewed: Yes`/`Completed`; fix this plan's current `Status: Draft` / `Reviewed: No` header when ready.

## Suggested Revisions
- Add the required `Reference: docs/claude_ops.md` header.
- Resolve A2 before implementation, or split the plan into explicit mainline-native and Sarol-variant paths.
- Add a cross-repo contract table for engine, CRC sibling, paper-trail adapter, scorer, manifest, release payload, and isolation profile.
- Replace prose-only C1 release description with a versioned schema sketch and test list.
- Add exact branch reconciliation steps from `sarol` to current `main`, including old `.claude/*` and new `src/*` path handling.
- Correct the CRC sibling path to `docs/plans/2026-07-16-crc-optimizer-requirements.md` or document the alias.
- Add the engine-required Phase-3 paper-trail negative controls, or explicitly mark them out of this plan with a follow-up owner/path.
- Add line-range pointers to the closest source files: `src/specs/verdict_schema.md`, `src/commands/paper-trail.md`, `src/commands/ground-claim.md`, `experiments/sarol-2024/scripts/parse_verdict.py`, and `experiments/sarol-2024/scripts/stage_claim.py`.

## Questions For The Author
- Which adjudicator path is the actual implementation target: current mainline native rubric or the Sarol 9-class variant?
- Should topology freedom be preserved in v0, or is leaf-prompt-only optimization the explicit first release?
- What is the package version/SHA of `agentic-label-opt` that paper-trail should pin once Phase 0 exists?
- Is the 3-way Sarol collapse the promotion metric, or only a near-term compatibility metric while native fine-grained F1 remains the headline?

## Audit Trail
- docs/claude_ops.md
- docs/plans/papertrail-optimizer-requirements.md
- CLAUDE.md
- docs/plans/experimental-plan-of-record.md
- docs/plans/paper-tool-validation.md
- docs/plans/NEXT.md
- data/benchmarks/sarol-2024/download.sh
- experiments/sarol-2024/scripts/parse_verdict.py
- experiments/sarol-2024/scripts/stage_claim.py
- experiments/sarol-2024/scripts/record_usage.py
- experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md
- experiments/sarol-2024/specs/verdict_schema_sarol.md
- src/specs/verdict_schema.md
- src/commands/paper-trail.md
- src/commands/ground-claim.md
- /Users/philadamson/Documents/Stanford/VISTA/code/crc-extraction-agent/docs/plans/2026-07-10-shared-optimization-engine-package.md
- /Users/philadamson/Documents/Stanford/VISTA/code/crc-extraction-agent/docs/plans/2026-07-16-crc-optimizer-requirements.md

## Post-review classification (Claude, applying this feedback)

**Applied (7):** Reference header; sibling CRC plan path precision; A3 branch-reconciliation rewrite (git-verified `sarol` lacks `src/` — reads from `main` only); Verification table A3 row + new cost/runtime-preflight row; A2 `primary_metric`/`breakdown` naming + new-collapse-script pointer; C1 payload tightening + cost-accounting single-source-of-truth note; new "Files to create" section.

**Raised to user (1), decision: keep as-is:** Modularity finding (wrap native + existing Sarol collapse behind one scorer interface now) — Phil chose not to build the wrapper ahead of A2 resolving.

**Dismissed, Claude-sided (evidence: plan already addresses these, reviewer missed the text):**
- Critical Gap #2 (force-resolve A2 now / split into two branches) — already an Open Question (§1) with a recommendation + explicit downstream contingency (Part A2, "If Phil picks the Sarol-rubric variant instead...").
- Nested-subagent negative control (Failure Mode + Contract Check) — Docker isolation substrate is explicitly Out of scope (engine-plan Phase 2c/3 work); no `run-isolation-framework.md` path is referenced anywhere in this plan.
- "Sarol 9-class parser reused for mainline without migration" (Failure Mode) — misreads Part A2: the recommended path builds a *new* native collapse, doesn't reuse/migrate the Sarol parser's 9-class logic.
- Schema 1.0→1.1 migration fixtures (Verification Gap) — not applicable; the new collapse only ever reads live current-schema (1.1) data, no 1.0 migration involved.
- Structural adapter tests for `ProgramManifest`/`ReleasePayload` envelope (Verification Gap) — engine Phase 0/2c's own testing responsibility, not duplicated per-consumer; the existing "Adapter smoke" row is right-sized for this plan.
- "Open Questions remaining = not ready" (Handoff Readiness) — Open Questions with explicit recommendations are the designed Phil-sign-off mechanism (`claude_ops.md` workflow), not a defect.
- Topology-fixed-vs-free profile enum (Modularity) — already an explicit Open Question (§3) with a recommendation; building infra for an undecided fork is premature.
- Success-criterion clarity (Handoff Readiness) — already stated in Out of scope ("Verification only requires establishing a first real scoring run, not a complete curve").
- Landing-plan status-string vagueness (Handoff Readiness) — already precisely named at Landing & cleanup ("this plan's `**Status.**` header reads `Completed`").
- Engine-package version/SHA pin required now (Contract Check) — chronologically impossible; engine Phase 0 (which creates the package) hasn't landed as code yet per that plan's own status header.
