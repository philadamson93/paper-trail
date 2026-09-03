# NEXT — current state and immediate next steps

**Always-current.** Edit this file when state changes. Fresh agents picking up work should read this *first*, then follow the reading path in `CLAUDE.md`.

**Last updated:** 2026-09-02

> **Paused 2026-04-29** (see `docs/journal/2026-04-29-pause-sarol-pivot-to-features.md`) — prioritized paper-trail-the-tool feature work over this experiment. **Narrowly resumed 2026-07-20**, not as a return to the paper-writing track: a new plan, `docs/plans/papertrail-optimizer-requirements.md`, makes paper-trail the 3rd consumer of an external, cross-repo shared agentic-optimization engine (`agentic-label-opt` — see that plan's header for the sibling-repo pointer). The sibling engine plan itself (in crc-extraction-agent) is Reviewed (`/review-plan`, findings applied) and iterated via `/explain-plan` feedback. Its own Open Questions §4 confirms scope: the value already delivered is the generalization insight this framework's design gave that external effort; actually building/running paper-trail's optimizer to a real curve stays real, unstarted work, secondary to that — Phases 3-5 below (paper writing) stay paused. **Update 2026-07-20 (this session):** `papertrail-optimizer-requirements.md` itself went through one `/review-plan` (Codex) round — the confirmed finding was that the `sarol` worktree lacks the `src/` tree the plan assumed, now fixed in Part A3 — plus a fresh `/explain-plan` HTML companion, opened for Phil's read. Plan is still `Draft` / `Reviewed: No`; both the plan and the HTML are UNCOMMITTED. **Update 2026-09-01:** cross-repo status refresh applied to the plan + HTML (UNCOMMITTED) — the July sequencing answer's "engine not yet battle-tested against a real consumer" claim is stale. `agentic-label-opt` is `main` @ `6d621ac` (2026-08-24, 50 commits past this plan's `5973dbc407e9` pin, all schema drift additive); rad-eval ran one armed end-to-end Vertex iteration 2026-08-05 and MedVAL (consumer #4) took its adapter VM readback GREEN, so the §459 "interface guessed from ~1.5 consumers" risk is materially retired, and two engine landings (the `"open"` network policy, plural `EditAgentMounts.editable_files`) moved toward this consumer specifically. Part C's re-pin target is now `6d621ac`. **Update 2026-09-01 (round 2):** an independent compatibility audit of the plan against `agentic-label-opt` @ `6d621ac` landed, plus a reconciliation against crc's now-approved dispatcher plan. **OQ1 RESOLVED** (freeze mainline + new scorer-side collapse) and **OQ3 RESOLVED** (fixed topology for v0, recorded against crc's contrary Topology Z precedent). New: **Part A4** — Part A is NOT zero-risk; the manifest isn't closed over the prompts' own `{{spec_root}}` references, and the paperclip command reference lives behind an unpinned external CLI, so two frozen versions could behave differently with no manifest diff. New: **Part C4** — six engine-contract blockers for the adapter (Runner called 3×/iteration not 2×, no timeout or status checks, `_split` never injected, `repo_root` must be pre-resolved, materialized tree isn't a runnable Claude Code project, positional-vs-keyword call asymmetry), plus the audit-ledger actor gap. **No engine change is being requested** — crc settled Runner-cost bounding consumer-side (Phil, 2026-08-27), and paper-trail adopts that pattern. C1's cost source-of-truth corrected from `parse_verdict.py` to real metered spend. ⚠ The `.html` is deliberately left STALE (SHA un-bumped) so the change-layer diffs correctly — regenerate with `/explain-plan` before a visual review. **Part A DONE 2026-09-01 (`24e8740`).** Reference closure computed mechanically over all five A1 prompts: four referenced paths sat outside the fileset. `src/specs/verifier_results.md` **added** (contract of record, `contract_file=True`); `control_flow.md` / `paper-trail.md` / `paperclip/SKILL.md` excluded with reasons recorded in the manifest. The paperclip reproducibility hole is closed by a **version pin** (`paperclip 0.5.11` in `runtime_pins`) rather than by freezing the 10-line stub. `experiments/sarol-2024/program-v0/manifest.json` is written and **self-verifying** — 6 entries frozen from `main` @ `4997e067c3a7`, `combined_hash` `006c36dc46db`, recomputable from the JSON alone with no tooling (verified 6/6 on write). **Two items deliberately left open:** (1) `verifier-dispatch.md:93` still references `src/specs/verifier_results.md` as a BARE relative path — it must become `{{spec_root}}/...` or it won't resolve in a materialized tree, but that is a one-line fix to a shipped prompt on `main`, i.e. tool-feature work on a different branch, not `sarol` research; (2) **no `program-v0` git tag was created** — the program files live on `main` while this work is on `sarol`, and the engine harness mints its own `program-v<i>` tags during the loop, so a hand-made tag risks colliding with that scheme; the manifest is a content-addressed freeze that stands without one. **OQ1 REVERSED 2026-09-01 to the Sarol-rubric variant (`66fb299`).** OQ2 pass 1 ran and failed: a native→Sarol collapse is not injective — `INDIRECT_SOURCE` spans both `INDIRECT` (→NOT_ACCURATE) and `INDIRECT_NOT_REVIEW` (→IRRELEVANT), leaving 17 of IRRELEVANT's 34 gold instances **structurally unreachable**. Rather than accept a capped metric, the program itself changed: `program-v0`'s adjudicator is now `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`, emitting Sarol's own 9 classes, so every gold label is reachable and **3-way macro-F1 is the frontier scalar**, directly comparable to MultiVerS 0.52 / GPT-4 0.45. ⚠ **Micro-F1 is a trap here** — it equals accuracy for single-label, so an always-ACCURATE do-nothing program scores 0.781 and beats both baselines; macro scores it 0.292. `score_sarol3.py --selftest` pins both (9/9). **Output vocabulary is a fixed contract, rubric guidance is not:** the optimizer may edit definitions, boundaries, examples and orderings, but not the set of emittable labels; an out-of-enum label is scored as a miss and counted in `error_class_counts`, never a crash. `program-v0` re-frozen: 7 entries, **two source refs** (5 from `main` @ `4997e067c3a7`, 2 from `sarol` @ `ba7a5308832b`), `combined_hash` `be2eb8070ae1`, verified 7/7. The Sarol variant's stale `.claude/` paths were repaired first (`ba7a530`); only one of the four was operational. **Native taxonomy RETIRED 2026-09-01 (`2004d87`), landing DEFERRED.** Phil: the native rubric was arbitrary, so adopt Sarol's as the tool's own. Git-traced rather than assumed: all 11 native verdicts plus `CONFIRMED_WITH_MINOR` landed **fully formed in one commit** (`18b3832`, 2026-04-19, the commit that created the schema), with no incremental history and no design doc — and the repo's literature review is dated three days later and never mentions the taxonomy. Sarol's 9 are human-annotated over 3,063 instances with reported κ. So severity (`OVERSTATED_MILD`/`OVERGENERAL`/`CONFIRMED_WITH_MINOR`) and abstention (`AMBIGUOUS`), plus `PARTIALLY_SUPPORTED`/`MISATTRIBUTED`/`CITED_OUT_OF_CONTEXT`, are **removed, not carried as an orthogonal field** — they had no grounding. Workflow states (`PENDING`/`NEEDS_PDF`/`STALE`/`SCHEMA_VIOLATION`) stay: pipeline machinery, not taxonomy. **This retires the "gains don't transfer to the shipped tool" objection** — the tool converges on the same rubric. ⚠ **Do NOT land on `main` until the optimizer work is done** (Phil). It is its own scoped change — rubric, adjudicator, extractor, `ground-claim.md`, `paper-trail.md`, `render_html_demo.py`, README, and regenerating the committed example runs, whose ledgers and demo HTMLs carry the retired vocabulary. `sarol`'s variant is already byte-identical in label space to that destination, so waiting creates no rework.

**All nine OQs resolved.** ⚠ The `.html` is deliberately STALE (SHA un-bumped) and now shows a reversed decision — regenerate with `/explain-plan` before any visual review.

**Parts B and C IMPLEMENTED 2026-09-02, branch `sarol-optimizer-impl`** (5 commits off `sarol` @ `d8f52f8`, pushed; not merged). `sarol` itself was fast-forwarded onto `sarol-oq6-9-feedback` first, so the `program-v0` tag's commit now sits on `sarol` and is safe to push.

- **Part C.** `experiments/sarol-2024/optimizer/`: `validate_sarol.py` (the C5 rubric-variant exit validator + 5 fixtures), `adapter.py` (the four `TaskAdapter` protocols, the contract-file re-hash, the paperclip-pin negative control, the round-trip canary, per-call timeout **and** `--max-budget-usd`), `dispatcher.py` (cost model, budget guard, content-addressed probe cache, and the real `run_loop` entrypoint).
- **Part B.** `optimizer/context/{playbook,task-and-scoring,release-format}.md`, `optimizer/prompt/optimizer-instructions.md`, `optimizer/meta-learnings.md`.
- **Independent audit applied.** `/review-implementation` (Codex, `docs/plans/reviews/papertrail-optimizer-requirements-implementation-feedback.md`) returned **Blocked** with 5 Critical findings; all were agreed and fixed. The two that mattered most: the first-pass validator had *weakened* the rollup rule to "overall appears among the sub-claims", so `CONTRADICT`+`ACCURATE` could roll up to `ACCURATE` — now worst-wins is enforced against a ladder **parsed from the editable rubric**, so the optimizer may reorder it but cannot contradict it, and an unparseable ladder fails closed. And an invalid label on a *sub-claim* under a valid overall verdict scored clean, because the scorer only ever sees the overall label — the validator's counts are now merged in.
- **Offline gates all green:** 131 self-test checks (validator 28, adapter 58, dispatcher 36, scorer 9), freeze 8/8 against the `program-v0` tag, materialization smoke 8/8, contract files clean. The dispatcher's checks include an **integration test that drives the engine's real `run_loop`** against a seeded throwaway checkout and proves a mutated contract file stops the iteration with **no version committed or tagged** — while an edit inside the EDIT scope still commits and tags.

**⚠ Cost finding, decision-relevant.** The old "cheap iteration N=10 ≈ \$7" figure in the graduated-N table below is **TRAIN-only and wrong by ~13×**. An iteration costs *three* Runner calls (TRAIN + VAL + the post-commit probe), so at VAL=316 × 3 nested sessions the floor is a fixed **~\$95/iteration regardless of TRAIN size** — at N=10 that is ~\$96, of which 98% is VAL. `dispatcher.py --preflight` prints the corrected table for every landmark. Caching the redundant probe removes roughly half.

**REPLANNED 2026-09-02 — phase the experiment (Phil), then REVISED the same day after a Codex round-3 review returned Blocked.** **Part C6** in the plan. The full pipeline is kept as a **profile**, not deleted.

The first draft of C6 was wrong in two ways the review caught, both worth knowing:

- It proposed letting the adjudicator read `content.txt` itself. **The frozen adjudicator prompt forbids exactly that** — its stated design invariant is "the adjudicator never reads the source paper. Reads only the evidence JSON and the rubric." So something must always select evidence; "adjudicator-only" can never mean "adjudicator reads the paper".
- It claimed Phase 1 would be directly comparable to MultiVerS 0.52 / GPT-4 0.45 while feeding all ~72 chunks of the cited paper. **It would not be.** Sarol's MultiVerS result used BM25 + MonoT5 **top-20** sentences and their GPT baselines top-5 — and this repo's own `paper-tool-validation.md:79` already defined the apples-to-apples condition as title + abstract.

The corrected design is a **ladder of evidence producers with the judge held constant** — which is a better experiment than the original, and closer to the paper's actual thesis:

| Profile | Evidence producer | LLM sessions/claim | Phase |
|---|---|---:|---|
| `abstract-only` | mechanical: title + abstract | 1 | 1a — matches the published setup |
| `retrieval` | mechanical: BM25 top-*k* | 1 | 1b — matches MultiVerS's top-20 budget |
| `agentic` | the extractor subagent + verifier | 3 | 2 — the pipeline as landed |
| `paperclip` | extractor querying the paper conversationally (Phil, 2026-09-02) | 3 | backlog, C6.10 |

The claim sharpens to **"does agentic evidence acquisition beat retrieval?"**, measured as a delta over Phase 1's *optimized* adjudicator. ⚠ With a confound the plan now records: Phase 1 also does no sub-claim decomposition and gets a null `indirect_attribution_check`, so a Phase 2 win is not attributable to agency alone.

- **Cost**: ~$96 → **~$32/iteration** for a mechanical profile (~$16 with the probe cache).
- **Blocking detail found while revising:** the envelope wants `source_mode: "sarol_corpus"`, but that field is constrained to `{paperclip, pdf, pdf_ocr_fallback}` by `verdict_schema.md` — a **frozen contract file**. Must be settled (Open Questions §13) before the envelope is built, or the exit validator rejects every claim.
- **Two real gaps this surfaced in the landed code**, both now specified in C6.7/C6.8 and owed: (1) the mistake corpus is **counts-only**, so the optimizer sees its score but not which claims failed or what gold said — near-blind on a Tier-1-open split; (2) VAL per-example outputs share a root with TRAIN, so scalar-only is a *convention*, not a boundary. Note the three actors: the **program** never sees gold on any split, the **optimizer** sees TRAIN gold fully (that is the mechanism, not a leak), TEST stays sealed.
- **Owed doc fix**: `meta-learnings.md` P1 and `context/playbook.md` currently point the optimizer at an **extractor-side** INDIRECT fix that Phase 1 cannot make. They must be narrowed when the profile lands, not before, or docs and code will contradict each other.

**PLAN APPROVED 2026-09-02 (Phil), via the `/explain-plan` visual path.** `Reviewed: No → Yes`, against the SHA-in-sync HTML companion; that SHA is stamped in the plan header as the last-reviewed baseline. Two changes landed from Phil's feedback round:

- **The `abstract-only` rung is dropped.** It was never constructible from what Sarol ships — `corpus.jsonl` is 8,515 chunks over 100 papers (~85 each) and `cited_doc_ids` is *all* chunks of one paper (mean 72), i.e. the whole paper chunked. The per-chunk field is only *named* `abstract` because Sarol inherited SciFact's schema. ⚠ **The repo contradicts itself here:** `paper-tool-validation.md:79` calls Variant A "title/abstract, match their evaluation setup" while its own line 181 says `cited_doc_ids` is every chunk — and `stage_claim.py` implements the latter. Recorded in C6.1 so nobody rebuilds it. Phil's sharper objection: an abstract-only condition exercises nothing paper-trail is *for*. Ladder is now **`retrieval` → `agentic` → `paperclip`**.
- **9-way scoring added as a breakdown, not a frontier.** `score_sarol3.py` emits `macro_f1_9way`, `per_class_f1_9way`, `support_9way`, `n_classes_present_9way` from the same predictions — deterministic, no re-run (17/17 selftests). Two tests pin why it stays a breakdown: macro-9 always divides by nine, so a batch covering 3 gold classes **caps at 0.333** however perfect the predictions, and the do-nothing program scores **0.097** at 9-way vs 0.292 at 3-way. At VAL=316 several classes land in single-digit support. Revisit as a frontier only at the upper N rungs, against real support counts (not computable — the benchmark is not on this machine).

**ALL THREE remaining Open Questions RESOLVED 2026-09-02 (Phil), each applied in code.** **OQ11** — keep the adjudicator prompt **frozen** and report the confound; this scopes the *v0 starting point* only, and the optimizer may still edit that prompt during a Phase 1 run. **OQ12** — the canary fires **once per Runner call** (three per iteration) and is now a **priced** term: `CostModel.canary_sessions()` feeds both `sessions_per_iteration()` and `iteration_cost()`, and `--preflight` prints it. **OQ13** — **variant-gate** `source_mode`: `validate_sarol.py` carries `SAROL_VARIANT_SOURCE_MODES = {"sarol_corpus"}` under the same `rubric_variant` gate as the verdict enum, leaving the frozen `verdict_schema.md` and `main`'s validator untouched. **The envelope is unblocked end-to-end** — C6.2's skeleton, parsed out of the plan text with its real `sarol_corpus` value, validates with zero violations. A separate gap found the same day and fixed: C6.2's skeleton was missing the required `schema_version`, which would have failed **every claim** in the first Phase 1 run. ⚠ These edits put the plan past its approved baseline `18aac02ae8b2`, so it is now **`Reviewed: Stale`** — regenerate the `.html` with `/explain-plan` before any visual review. OQ2's owed hand-sample stays open: a rater task, not a design decision — and note that scoring both granularities *reports* more, it does not *validate* anything.

**PART C6 RETROFIT LANDED 2026-09-02**, so the "one build remaining" note below is closed: profiles, the BM25 evidence producer, profile-aware `editable_paths()`/`stages_per_claim`, the per-claim mistake corpus and the explicit VAL root all shipped, and a Codex C6 audit ran with every finding agreed and fixed (`1122306`). Offline gates: **271 checks** (profiles 37, evidence_producers 26, validator 33, adapter 92, dispatcher 66, scorer 17), freeze 8/8, materialize 8/8.

**TWO OF THE THREE PAID GATES PASSED 2026-09-02, against real Vertex/Anthropic spend and the real benchmark.**

- **Budget invariant — PASSED, both halves.** The dispatcher preflight refuses an unaffordable run (`REFUSE  10 iteration(s) at TRAIN=2141: ~$1,245.35 worst case … against a $100.00 budget`) and clears an affordable one, and the live half fires at the actual spender: `claude -p --max-budget-usd 0.001` returns `Error: Exceeded USD budget (0.001)`. This is the gate the plan makes a precondition for every other paid run.
- **Adapter smoke — PASSED.** `program-v0` materialized 8/8 from the tag, then the Runner drove one real headless Claude Code session end-to-end on dev claim 0 under `retrieval`/k=20: **exactly 1 nested invocation** (the C6.1 stage-subsetting gate), exit 0, zero validator violations, predicted `ACCURATE` against gold `ACCURATE`, and a valid `0.2.0` VAL release payload carrying `profile: retrieval` and reduced to scalar-plus-completeness. The whole chain — producer → envelope → judge → exit validation → scorer → release — now has a real run behind it, not a simulated judge.
- **Benchmark prerequisite fixed.** The Sarol data was not on this machine at all. `data/benchmarks/sarol-2024/download.sh` fetched it to `~/.paper-trail/benchmarks/sarol-2024/`; counts verified against the README (2,141 / 316 / 606 claims, 8,515 corpus chunks). Staging confirms the plan's C6.1 claim directly: `cited_doc_ids` for dev claim 0 is **123 chunks of one paper**, ~49KB of `content.txt` — the whole paper chunked, not an abstract.

⚠ **COST CALIBRATION — the headline number was wrong by ~20x, and this is the live decision.** `DEFAULT_PER_SESSION_USD` was a `0.05` placeholder whose own comment said "the real number replaces it after the first metered claim." That claim has now run: **$1.0026 metered, 98.7s**, for one `retrieval` adjudicator session on a 123-chunk paper under `opus`. The constant is calibrated to `1.00` and the three cost tests now name the `$0.05` they were derived at, so they still pin the arithmetic. What this does to the plan's figures:

| | at the assumed $0.05 | at the measured $1.00 |
|---|---:|---:|
| `retrieval` iteration @ TRAIN=10 | $32.25 | **~$647** |
| …probe cached | $16.40 | ~$329 |
| VAL-only v0 baseline (316 claims) | ~$16 | **~$317**, ~8.7h sequential |
| `agentic` iteration @ TRAIN=10 | $96.75 | ~$1,939 |

Runtime matters as much as money: 98.7s/session × 645 sessions ≈ **17.7 hours sequential** for one Phase 1 iteration (the Runner processes claims in a list comprehension, not in parallel). One sample, so treat it as order-of-magnitude and re-measure if the profile, model or claim mix changes.

**ALL THREE PAID GATES ARE NOW RUN (2026-09-02/03), and the first optimization attempt is complete.** Full analysis: **`docs/journal/2026-09-03-first-optimization-attempt-postmortem.md`** — read that before planning the next run; the summary below is a pointer, not a substitute.

- **v0 baseline established: 3-way macro-F1 `0.4949`** (micro 0.784, n=37 dev, `retrieval` k=20, 0 invalid). Above GPT-4 4-shot's 0.45, just under MultiVerS's 0.52, and verified *not* to be the always-ACCURATE collapse the plan warns about.
- **3 optimizer iterations ran and tagged `program-v1/v2/v3`.** Paired on the identical 37 claims: `0.4949 → 0.4647`. **The entire delta is one claim** (3 predictions changed: 1 fixed, 2 broken). No signal either way. TRAIN accuracy 0.720 → 0.620 → 0.680.
- **The optimizer's own 602-line hypothesis log is at `optimizer/meta-learnings.md`** (P0–P7, confirmed/pending/reverted, plus a per-iteration log). Its edits were rational and correctly targeted — it diagnosed over-strictness from a corpus that was 16/19 gold-ACCURATE and added a sufficiency threshold. The optimizer is not what failed.

⚠ **THIS RUN DID NOT TEST THE RESEARCH QUESTION, and the `0.4949 → 0.4647` delta must not be recorded as evidence about agentic optimization.** Three compounding *instrument* failures, all silent, none the optimizer's doing:

- **The optimizer never saw a VAL scalar.** The per-iteration release payloads (`release_train.json` / `release_val.json`) were **never written** — confirmed: no `*release*` file exists under the run root, and the agent says so itself in `meta-learnings.md`. It optimized with **zero feedback about the quantity being optimized**, for all three iterations. The Tier 2 boundary was over-enforced: C6.9 correctly put VAL outputs beyond reach, but the artifact meant to carry the scalar *back* never got produced.
- **The canary never fired** (`"canary": null` in both manifests). The guard OQ12 priced as load-bearing — "a run whose instrument moved is not a run at all" — was configured, paid for, and did not execute. No number from this run carries a round-trip guarantee.
- **A third of the metric was unreachable.** No version ever predicts `IRRELEVANT`, and no TRAIN corpus ever contained an `IRRELEVANT`/`ETIQUETTE` mistake (~1.8% × TRAIN 25–50 ⇒ zero expected). ~0.17 of macro-3 is pinned at zero.

**Blocking the next paid run — in this order. Items 1–2 are wiring; nothing is learnable until they're fixed.**
1. **Make the release payload reach the optimizer.** Cheap wiring fix, and by far the highest-value one: until the VAL scalar is visible, more iterations buy nothing.
2. **Make the canary fire, and fail closed if it doesn't.** A silently absent guard is worse than none.
3. **Fix metric reachability** — stratify the TRAIN draw, or report macro over reachable classes only. **Phil's call: it changes the estimator.**
4. **Establish the noise floor** before reading any curve (effects are ~1 claim ≈ 0.03 macro-F1 at n=37, so step-back is currently driven by noise; adopt crc's `τ_cal`).
5. **Three owed gates**: batch-size-equals-requested; ramp indexing against the engine's real `iter_n` base; per-iteration VAL output paths.

**Cross-cutting lesson:** all three instrument failures were silent while 296 offline gates stayed green, because each gate asserted on a local object rather than on the artifact the next stage consumes. **A guard that can be absent without announcing itself is not a guard.**
2. ~~**`/sarol-eval-item` does not exist.**~~ **WRITTEN 2026-09-02** (`a1fb578`), at `.claude/commands/sarol-eval-item.md`. Single-stage, as the replan scoped it: the `adjudicator` stage is implemented; `extractor`/`verifier` abort with `STAGE_NOT_IMPLEMENTED` pointing at the C6.1 profile retrofit, deliberately, so a missing profile is visible rather than quietly running Phase 2. ⚠ **Location is load-bearing** — `command_path()` accepts three directories but Claude Code only resolves `.claude/commands/` from the session cwd; the other two pass the preflight and then fail at dispatch. An adapter selftest pins the location. ~~The remaining blocker on a first curve point is now the Part C6 retrofit.~~ **That retrofit LANDED 2026-09-02** — the BM25 producer writes the envelope `/sarol-eval-item` reads, and `STAGES` is profile-derived rather than a global 3-tuple. The command was exercised for real in the adapter smoke above.
3. **OQ2 pass 2** — the owed hand-sample of the adjudicator's 9-class judgement on real dev-split claims. A rater task, not an agent task.
4. Still open: pushing the `program-v0` tag (now safe), and the bare-relative `{{spec_root}}` fix in `verifier-dispatch.md:93` on `main`.

Everything below this line predates the pause and is historical design context, not live status.

> **Major reframe 2026-04-21: experiment is agent-only; infrastructure is the contribution.** Human decision: the optimizer is an agent (not human-in-the-loop). Paper-trail + Sarol is the case study; the framework is the primary contribution. See `docs/plans/agentic-pipeline-optimization-framework.md` for the authoritative plan (tiered leakage discipline, optimizer/dispatcher/subagent architecture, structural defenses). Everything downstream — contributions list, Task 5 eval-arm deliverables, hygiene rules — has been updated below.

---

## Current phase

**Designing the meta-experiment infrastructure — agent-only reframe landed 2026-04-21.** Framework plan doc is authoritative: `docs/plans/agentic-pipeline-optimization-framework.md`. We are in the pre-v1 design stage; no curve runs yet. Locked decisions through 2026-04-21:

- Q1 — monolithic version tagging (`paper-trail-v<N>`, whole-system snapshots)
- Q9 — eval arm lives in `experiments/sarol-2024/eval-harness/` with a pre-commit hook enforcing immutability during revision commits
- Q9b — eval invocation is headless Claude Code (`claude --bare --print`), not direct Anthropic SDK
- **NEW 2026-04-21: experiment is agent-only.** Optimizer is an agent; no human-in-the-loop revision. Paper-trail + Sarol = case study; framework = primary contribution.
- **NEW 2026-04-21: tiered leakage discipline** (Train fully open / Val scalar-only / Test sealed) with structural enforcement (filesystem permissions + fixed output schema).

Reading order going forward:
1. `agentic-pipeline-optimization-framework.md` — authoritative plan doc.
2. `experiment-sarol-archive-and-eval-framework.md` — Sarol-specific archive + invariants + Q9c memory-blind mechanism.
3. `experiment-sarol-optimization-loop-hygiene.md` — Rule 1 (stays); Rule 2 (superseded for agent-only, preserved as Tier 3 sealing).
4. `paper-writeup-items.md` — contribution framing (see below for reshuffle after reframe).

## What is paused, deliberately

- **INDIRECT-detection adjudicator fix.** Smoketest identified the failure mode; we drafted three prompt clauses but have not applied them. Paused so that the archive/eval framework is in place first, so v1-vs-v2 can be measured properly rather than re-running ad hoc.
- **Ramping past N=5 to larger evals.** Paused until the eval arm is built and orchestrator-runtime decisions have been moved into it.

## Immediate next steps, ordered

### 1. Lit-review pass (45 min) — **COMPLETED 2026-04-21**

**Outcome:** three-claim verdict in `paper-writeup-items.md` §"Net lit-review verdict (2026-04-21)" and §"Specific papers checked so far":
- **Claim A (train+val curve over human revisions):** NARROWED. OPRO Figure 11 and MIPROv2 Appendix G publish the figure shape with algorithmic revisions. Retain as headline figure; novelty narrowed to human-driven x-axis + divergence-as-stopping-rule + multi-subagent pipeline application.
- **Claim B (multi-subagent pipeline iteration):** DROPPED as standalone. DSPy + MIPROv2 scooped it. Cite as prior art.
- **Claim C (physical sealing + planning-session blindness):** CLEAN, now leads. No prior art in the 5-paper pass.

Contribution list above updated. Downstream implication: **first expensive experiments are not blocked on this lit review** — the headline figure remains viable, just with narrowed framing.

**Open follow-up (non-blocking):** 2025 multi-agent prompt optimization papers (MAPRO, MA-SAPO, Multi-Agent Design) flagged for a one-pass read before final paper draft. Don't change Claim B's verdict; mandatory citations.

### 2. Memory-blind invocation spike (Q9c) — **ON HOLD 2026-04-21**

Human decision 2026-04-21: put on hold in service of working one thing at a time. Full state saved in `experiment-sarol-archive-and-eval-framework.md` §Q9c.

**State summary** (for a fresh agent picking this up later):
- **Candidate mechanism identified and verified:** `claude --bare --print` skips auto-memory and CLAUDE.md auto-discovery per its `--help` description. Ground-truthed against `claude --help` 2026-04-21. Full invocation pattern + flag list documented in archive-framework doc §Q9c.
- **Rejected as unverified:** subagent-proposed env vars `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `CLAUDE_CODE_DISABLE_CLAUDE_MDS` — absent from `claude --help`. Do not adopt without further verification.
- **What's left to do:** run the canary sanity-check (plant a temporary memory file, invoke with and without `--bare`, confirm suppression). Test design written in archive-framework doc §Q9c. Estimated 15 min.

**Restart instructions:** read archive-framework doc §Q9c end-to-end, run the canary test, update §Q9c with results + resolve Q9c if passing, or document the failure mode + move to fallback option (1) or (2) and re-test.

Resume before Task 5 (eval arm build) — the eval arm assumes the memory-blind mechanism works.

### 3. Pick the `paper-trail-v1` commit (Q8)

**User decision 2026-04-21:** v1 = the current state of the `experiment-plan` branch that has the Sarol adapter wired up but has NOT yet incorporated any prompt changes informed by the April-20 smoketest findings. User noted that older versions of paper-trail predate the Sarol rubric and so don't conform to the eval harness at all — the "starting point" for *this* experiment is where we are now, not an earlier paper-trail release.

**Action:** find the commit SHA on `experiment-plan` immediately before the first smoketest-findings-informed edit. Verify `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` at that commit contains no INDIRECT-specific clauses. Tag as `paper-trail-v1`.

### 4. Lock eval-train manifests (graduated N)

**User proposal 2026-04-21, adopted:** ramp dataset size slowly for compute efficiency. Suggested ramp:

| Gate | N | Approx cost/revision (single seed, Opus 4.7) |
| --- | ---: | ---: |
| Cheap iteration | 10 | ~$7 |
| Medium iteration | 25 | ~$18 |
| Primary curve point | 50 | ~$37 |
| Post-structural-change | 100 | ~$75 |
| Sweep comparison | 200 | ~$150 |
| Locked candidate | 2,141 (full train) | ~$1,560 |

**Action:** write `experiments/sarol-2024/eval-harness/scripts/sample_subset.py` — seeded random draw from `claims-train.jsonl`, outputs `eval-harness/subsets/eval-train-<N>.json` (list of claim row IDs). Generate subsets for N ∈ {10, 25, 50, 100, 200}. Lock once generated (never redraw; seed committed).

**Subset relationship:** nested (subset-50 ⊂ subset-100 ⊂ subset-200). Enables direct comparison of the same version across N levels.

### 5. Build the eval arm

**Scope expanded 2026-04-21 to include the tiered-leakage framework deliverables.** Authoritative spec: `agentic-pipeline-optimization-framework.md` §"Implementation checklist (feeds NEXT.md Task 5)".

Once tasks 1–4 are closed:

- `experiments/sarol-2024/eval-harness/` scaffolding
- Move `stage_claim.py`, `parse_verdict.py`, `record_usage.py` into it
- `sample_subset.py` — seeded random draw from `claims-train.jsonl` or `claims-dev.jsonl`; outputs `eval-harness/subsets/eval-{split}-{N}.json` with committed claim-ID list and seed
- `validate_run.py` — implements the three-tier invariant framework from `experiment-sarol-archive-and-eval-framework.md` §"Measurement invariants and validation." Checks Tier 1 pre-run, per-dispatch, and post-run; writes full run-invariants block into `summary.json`
- **Three dispatcher scripts (NEW per tiered-leakage framework):**
  - `run_train_eval.py` — returns full per-example traces + aggregates to the optimizer. Train is Tier 1 fully open.
  - `run_val_eval.py` — returns scalar F1 only to the optimizer (locked output schema, schema-validated). Writes per-example outputs to `val_runs/v<N>/` (filesystem-restricted from optimizer's `--add-dir` scope). Tier 2.
  - `run_test_eval.py` — same shape as val dispatcher but with `--confirm-unseal` tripwire. Tier 3. Called once at locked-candidate.
- **Filesystem-permission boundary test** — confirms the optimizer's `--add-dir` scope cannot read val/, val_runs/, test/, test_runs/. Run as part of the v1 gate.
- **Schema validator module** — shared by all dispatchers. Locked output schemas live in `eval-harness/schemas/`.
- `/sarol-eval-item` slash command — non-interactive, takes all inputs via CLI args. Uniform invocation for train / val / test subagents (`claude --bare --print /sarol-eval-item ...`). No interactive questions.
- Pre-commit hook enforcing eval-harness immutability on non-eval branches
- Commit any per-experiment `.claude/settings.json` / MCP config to the repo (captured by the paper-trail version tag — do NOT let these live in user-global settings)
- **Dispatcher invocation shape (new 2026-04-22 from CLI-ref docs sweep; amended 2026-04-23 post-critic + benchmark-integrity lit-review):** every subprocess invocation is the committed wrapper script `scripts/run-eval.sh --tier {iteration|landmark} --version v<N> --claim <id>`. The script internally applies: `env -i` + pinned `LANG`/`TZ`/`PATH`, `CLAUDE_CODE_OAUTH_TOKEN` (iteration) or Vertex GCP creds (landmark), `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, fresh-per-invocation `CLAUDE_CONFIG_DIR=/tmp/pt-eval-cfg-$uuid/`, clean cwd at `/tmp/pt-eval-wd-$uuid/`, `--add-dir $REPO`, `--tools default`, `--agents '<json>'`, `--settings <tag-scoped>`, `--mcp-config <tag-scoped> --strict-mcp-config`, `--no-session-persistence`, `--exclude-dynamic-system-prompt-sections`, `/sarol-eval-item ...`. Each piece tied to a specific leakage vector (full table in `experiment-sarol-eval-arm-isolation.md`). Wrapper-script-as-canonical-interface addresses "why didn't he just use a script?" criticism pre-emptively and commits the invocation shape as a reviewable artifact.
- **Custom-subagent JSON registry builder (new 2026-04-22):** a small utility that reads `.claude/agents/*.md` YAML frontmatter + body at a given paper-trail-v<N> git tag, serializes to the `--agents` JSON format, and emits `experiments/sarol-2024/eval-harness/subagent-registry-v<N>.json`. Committed alongside each tag. ~50 lines Python.
- **Wrapper script `scripts/run-eval.sh` (new 2026-04-23):** canonical operator interface; encapsulates the env-var + flag chain above. ~80 lines bash. Documents invocation modality in `.env.example` sibling template.
- **Landmark-tier Dockerfile `experiments/sarol-2024/eval-harness/Dockerfile` (new 2026-04-23):** pinned Claude Code binary via `npm install -g @anthropic-ai/claude-code@<specific-version>`. Closes the binary-drift reproducibility gap the critic flagged 2026-04-22. Published per-tag as part of the `paper-trail-v<N>` git-tag archive artifact set.
- **Adversarial-agent smoketest suite (new 2026-04-23, from Berkeley Agent-Eval Checklist + Zhu et al. ABC):** four small agents in `experiments/sarol-2024/eval-harness/adversarial/`: `null_agent.py` (empty verdict, expected ~0 macro-F1 floor), `random_agent.py` (~11% baseline), `injection_agent.py` (prompt-injection attempt, expected verifier catches), `tamper_agent.py` (filesystem-write attempt, expected Rule-1 blocks). Run at `paper-trail-v1` smoketest; results land in `paper-trail-v1.json`.
- **Scorer adversarial audit before v1 tag (new 2026-04-23):** run `parse_verdict.py` + macro-F1 computation against malformed inputs (empty, whitespace, wrong-schema JSON, extra-keys JSON, all-9-verdicts JSON, non-UTF-8). All must fail with typed errors, not silently score.
- **LLM-judge sanitization audit before v1 tag (new 2026-04-23):** review adjudicator + verifier prompts for delimiter discipline around agent content, system-prompt-marker escape, structured-output enforcement.
- **E3 dispatcher crashed-task semantics spec (new 2026-04-23):** fetch-failure → claim scored as FAILED_FETCH → counts as missed in macro-F1 denominator; never dropped, never retried without a counter. Matches Berkeley/Zhu et al. crashed-task discipline (TAU-bench "empty = success" lesson).
- Move orchestrator-runtime decisions (verifier sampling, retry, bounce, schema validation) into eval-harness Python
- **3-seed minimum at v1 landmark** — non-negotiable per lit-review convergent signal (MIPROv2, TextGrad, BetterTogether, OPRO, MASS).
- **Train dispatcher emits raw per-subagent traces + macro-F1 + per-class F1** (topology-agnostic; no pre-computed per-stage sub-scores — those are the optimizer's job via its own mutable trace-aware metric). Per `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D36: the DSPy-pattern sub-metric (extractor recall, adjudicator conditional-F1, verifier flip rate, etc.) is an optimizer-owned artifact seeded at v1, not frozen eval-arm infrastructure — the optimizer rewrites it when paper-trail-v<N>'s topology evolves.
- **`paper-trail-v<N>.json` archive artifact** — emitted per tagged revision alongside the git tag. Contains {prompt hashes, signature specs, rubric examples, eval-arm tag, dispatcher versions, model aliases, settings.json hash, MCP config hash, handoff-doc schema version}.
- Test on paper-trail-v1 + eval-train-10 (~$7 smoketest of the new plumbing; validates that invariant-check machinery fires correctly)

**New deliverable from 2026-04-22 experiment-design decision (D50/D51 — design for E3, the fetch-through-verdict experiment):**

- **E3 dataset-extension** (D51, the small-but-non-trivial work to convert Sarol's per-claim records into the (citing PDF + reference token + claim) shape E3 needs): for each Sarol claim, identify the citing paper it came from, identify the reference token within that paper that points to the cited paper, package as `(citing_sentence, claim_text, reference_token, citing_paper_PDF_path)`, fetch/collect Sarol's 100 citing paper PDFs. Estimated ~1 day of dataset-engineering scripts + manual spot-check on a few papers. Acknowledge in paper methods section as honest engineering work — we extended Sarol's framing to test more of the pipeline.
- **E3 dispatcher** (replaces / extends the prior `run_train_eval.py` spec): takes per-claim records of the form above; orchestrates phases 2-5 of paper-trail; emits per-claim verdict + fetch-success bool + ingest-success bool + macro-F1 aggregate. Locked schema. The canonical reported metric.
- **E1 sub-dispatcher** (the sample-efficiency sub-experiment per D52, for the optimizer's optional cheap hypothesis-checking on phase-5-only): same dispatcher infrastructure but with pre-staged Sarol chunked inputs (Sarol's flat JSONL claims). Optimizer may invoke for cheap pre-checks; logged but not part of the canonical curve.
- See `docs/journal/2026-04-22-experiment-design-e1-e4.md` for the full decision log.

**New deliverables from 2026-04-22 lit-review-2 (autoresearch + VeRO borrow-lists):**

- **Per-claim budget as Tier 1 invariant** (D45): fixed per-claim wall-clock OR fixed per-claim model-call count so the optimizer cannot "win" by growing per-claim compute. Probably model-call-count as primary (deterministic), wall-clock as secondary. Default `1.5 × paper-trail-v1's per-claim call count` for headroom without encouraging bloat. Specific bound set at Task-5 build time. `validate_run.py` enforces.
- **Round-trip sanity canary per run** (D46): eval-arm processes a known-good canonical claim at the start of each run, confirms the pipeline returns the expected verdict. Defends against silent metric bugs in the Karpathy autoresearch issue #384 shape (BPB metric inflated by UTF-8 replacement chars for weeks). Option A (pinned synthetic canary claim) for v1; Option B (pinned Sarol-train claim with robust expected verdict) considered if A feels too artificial.
- **Train dispatcher per-claim adjudicator reasoning + verifier narrative in rich-schema output** (D47, train-tier-only): expose failure-mode detail to the optimizer in the train tier, not just macro-F1 / per-class F1. Val dispatcher stays scalar-only regardless. Motivation: Karpathy autoresearch issue #353 (ottogin's fork showed ~60% improvement by exposing richer diagnostics to the optimizer).
- **`program.md`-equivalent optimizer instruction document** (from autoresearch borrow-list): author `experiments/sarol-2024/optimizer/program.md` at Task 5 build time. Structure mirrors Karpathy's: Setup / Experiment loop / NEVER STOP / Simplicity criterion / CAN-CANNOT block / Output-flood prevention / Crash handling. Attribute Karpathy `program.md` 2026 throughout. Full framework doc §3 "Optimizer agent initial configuration" is the spec for what this file must contain.
- **5-column `results.tsv`-equivalent per-revision table** (from autoresearch): commit a structured table per `paper-trail-v<N>` revision with columns `commit / macro_f1 / per_class_summary / status / description`. **Commit ours** (autoresearch gitignores theirs; we need full provenance for paper reproducibility).
- **Analysis-notebook-equivalent for progress.png / train-val curve generation** (from autoresearch `analysis.ipynb`): `experiments/sarol-2024/eval-harness/progress.ipynb` or `.py` that regenerates the train+val curve figure from committed archive data. Reference implementation to study: autoresearch's `analysis.ipynb`.

Short specs per script live alongside the script as `<name>.md` siblings, written at build time. No separate feature-requirements docs authored in advance — the archive-framework doc is the specification; individual scripts get short implementation notes only.

**Two specs that MUST be written at build time (not deferred indefinitely — external reproducers need them):**

1. **`expected_invariants.json` schema.** JSON schema spec. Defines what a valid expected-invariants manifest looks like (field names, types, which fields are required, which are optional). Matters because future reproducers — someone re-running `paper-trail-v6` two years from now — need to know the manifest format. ~50 lines. Author when `validate_run.py` lands; location: `experiments/sarol-2024/eval-harness/expected_invariants.schema.md` or alongside `validate_run.py` as a docstring-referenced file.
2. **`/sarol-eval` I/O contract.** What command-line arguments it accepts, what exit codes it returns, what files it writes and where, what it does on invariant-violation (abort + error format). ~30 lines. Required for anyone running headless evals externally. Author when the slash command lands; location: as a docstring in the slash command definition or as `experiments/sarol-2024/eval-harness/sarol-eval.contract.md`.

Both are implementation-close specs, not speculative feature docs. They exist to make the eval arm externally reproducible — someone cloning the repo a year later should be able to read these and run `paper-trail-v<N>` without having to reverse-engineer our conventions. Do NOT defer past Task 5 completion.

### 6. First curve points — Variant strategy decided 2026-04-21

**Variant C is the paper's headline task; Variant A is the iteration workbench.** Full strategic reasoning in `experiment-sarol-benchmark.md` §"Variant strategy (decision 2026-04-21) — Variant C is the headline." Short form: Variant A is exposed to a "could-have-been-one-prompt" reviewer rebuttal; Variant C requires a pipeline by construction (PDF fetching, bib resolution, cross-doc retrieval, tool use). Human 2026-04-21: *"we lean in to experiment C."*

**Operational split:**
- **Variant A** is cheap; used as the iteration benchmark across the graduated N ramp (N=10/25/50/100/200/2141) during the optimizer's revision loop.
- **Variant C** is expensive; run at landmark tags only — minimum `paper-trail-v1` and `paper-trail-v_final`; possibly one mid-curve landmark. Where the paper's headline numbers come from.

**First concrete runs:**
- Run Variant A at paper-trail-v1 with N=10 (~$7 smoketest of the new plumbing).
- Once Variant A at v1 looks clean, run Variant C at v1 as the first landmark.
- Apply INDIRECT-detection fix → tag paper-trail-v2 → rerun Variant A (cheap). Variant C at v2 optional depending on delta size.

### 7. Complete outstanding-items status (doc sweep 2026-04-22)

**Comprehensive prioritized status across all plan docs and journal entries.** Produced via targeted sweep after lit-review-2. Each item cites its source doc. Tier 0 is blockers; Tier 5 is future-paper / not-this-paper; Tier 6 is non-Sarol threads flagged for awareness but off the critical path.

#### TIER 0 — RESOLVED (see milestone doc)

**All three gates resolved 2026-04-22 / 2026-04-23.** Iteration tier (local OAuth subscription) is unblocked — Task 5 scaffolding can proceed now. Landmark tier (Vertex + Docker) is architecturally specified; empirical Vertex canary execution still pending on the GCP VM.

Full resolution narrative, all six 2026-04-22 canaries, the 2026-04-22 critic audit findings, the 2026-04-23 benchmark-integrity lit-review (Berkeley + Zhu et al.), and the 2026-04-23 creative-defenses brainstorm + wrapper-script + Docker architecture revision: see `docs/plans/tier-0-resolution-2026-04-22.md` (read-only milestone doc).

**Authoritative current-state docs the next session needs:**
- `experiment-sarol-eval-arm-isolation.md` — canonical iteration-tier and landmark-tier invocation shapes (wrapper script + Docker); IN/OUT formalization; alternatives-evaluated catalog; residual investigation items.
- `experiment-sarol-optimization-loop-hygiene.md` — Rules 1 (subagent sandboxing) + 2 (main-session blindness); still authoritative.
- `canary-runbook-vertex.md` — landmark-tier empirical canary runbook (pending VM execution).

**Next-session meta-task** (ordered — do 0 first since it may reshape 1):

0. **Write a consolidated experimental-plan-of-record doc** (new 2026-04-23 per Human observation that planning has accreted across many sessions into many specialized docs with no single holistic view). **Problem:** an agent or collaborator reasoning over the whole plan currently has to cross-reference ~10 plan docs + journal entries to reconstruct thesis → phases → criteria → non-goals; the non-linear accretion may be hiding soundness pitfalls that a holistic view would surface. **Deliverable:** `docs/plans/experimental-plan-of-record.md` — outline with:
   - Thesis (1-2 sentences: the paper's core claim)
   - Primary + secondary contributions (consolidated from `paper-writeup-items.md` §Core contributions)
   - Phase-by-phase plan start-to-finish (Phase 0 current state → Phase 1 Task 5 eval-arm build → Phase 2 v1 tag + smoketest → Phase 3 iteration curve under optimizer → Phase 4 landmark tags + v_final + test unseal → Phase 5 paper writing)
   - Per-phase success criteria + descope triggers
   - Explicit non-goals (what's pinned to future papers — Variant D, from-scratch, backbone portability, multi-benchmark, human-in-loop, etc.)
   - Pointers per section to the authoritative deep-spec docs (framework doc §1-§8, eval-arm-isolation, hygiene Rules 1+2, benchmark doc, archive-and-eval, paper-writeup-items, milestone docs)
   - Consolidated view of the D-number decisions (D1…D53+) and what each settled — a decision-log table so readers can find "what did we decide about X" without grepping journals
   
   **First-pass scope:** outline-with-pointers is fine — the precursor form is already valuable because it forces the plan into one navigable artifact. Full prose can follow once the structure is agreed.

   **Follow-up: spawn a soundness-review agent** on the plan-of-record doc. Brief: adjudicate whether the plan is sound; identify pitfalls, missing criteria, inconsistencies between phases, unstated assumptions, paths where empirical results could invalidate downstream plans. Pattern mirrors the 2026-04-22 critic audit on the Rule-3 isolation claim (separately briefed, pressure-test, grade, return actionable findings). Expected outputs: findings integrated into the plan-of-record + any open decisions or rescopes that surface become new Tier 1+ items.

1. **Begin Task 5 eval-arm scaffolding** (Tier 1 below) — after the plan-of-record + soundness review lands, because the audit may rescope some deliverables.

2. **Run the nine blocking-priority canaries early in Task 5** (five from the 2026-04-22 critic + four adversarial-agent smoketests from Berkeley / Zhu et al. — full specs in `experiment-sarol-eval-arm-isolation.md` §Residual-investigation-items).

3. **Token rotation reminder:** the `CLAUDE_CODE_OAUTH_TOKEN` used in 2026-04-22 canaries was shared in session transcript; rotate at claude.ai settings before running new canaries. (Session-local cleanup of the cached approval-pattern in `.claude/settings.local.json` already done 2026-04-23.)

#### TIER 1 — Task 5 eval-arm build (the core deliverable)

Full list lives in §5 above. Summary of deliverables (all required before any curve runs):

- Eval-harness scaffolding + move `stage_claim.py` / `parse_verdict.py` / `record_usage.py` into it
- `sample_subset.py` (seeded random draws, committed manifests, nested subsets at N=10/25/50/100/200)
- `validate_run.py` with Tier 1 invariant framework + round-trip sanity canary (D46)
- Three dispatcher scripts: `run_train_eval.py` (full traces + aggregates), `run_val_eval.py` (scalar-only), `run_test_eval.py` (with `--confirm-unseal` tripwire)
- Filesystem-permission boundary tests
- Schema validator module
- `/sarol-eval-item` slash command (non-interactive, locked arg set)
- Pre-commit hook enforcing eval-harness immutability on non-eval branches
- Per-experiment `.claude/settings.json` / MCP config committed to the repo
- Move orchestrator-runtime decisions into eval-arm Python
- 3-seed minimum at v1 landmark (non-negotiable per lit-review)
- Train dispatcher emits raw per-subagent traces + macro-F1 + per-class F1 (topology-agnostic; no pre-computed sub-scores — those are the optimizer's job)
- Per-claim adjudicator reasoning + verifier narrative in train-tier rich-schema output (D47, train-tier-only — val stays scalar)
- Per-claim budget as Tier 1 invariant (D45, model-call count as primary, wall-clock as secondary)
- Round-trip sanity canary per run (D46; guards against silent metric bugs in autoresearch issue #384 shape)
- `paper-trail-v<N>.json` archive artifact schema
- `program.md`-equivalent optimizer instruction document (mirroring Karpathy structure, with framework §3 content)
- **Proposed-but-rejected topology logging in the optimizer-output schema** (added 2026-04-23 from paper-writeup-items.md §Things-to-be-honest-about topology-may-not-change item): per-revision archive artifact must include a structured record of restructure proposals the optimizer made-evaluated-and-rejected, alongside accepted changes. Required to distinguish "explored-and-backtracked" (evidence FOR the framework claim) from "never-explored" (neutral-to-negative evidence) when topology converges back to the seed decomposition. Without this logging the paper cannot honestly defend the explored-and-backtracked outcome. See paper-writeup-items.md §Things-to-be-honest-about for the framing argument and framework doc §3 "Topology-restructure invitation" + §7 open-problem-#10 for the spec hooks.
- 5-column `results.tsv`-equivalent per-revision table (committed)
- Analysis-notebook-equivalent for train+val curve regeneration from committed archive (reference: autoresearch `analysis.ipynb`)
- **Two non-deferrable specs** (already committed to ship with eval arm, not later): `expected_invariants.json` schema + `/sarol-eval` I/O contract.
- Smoketest on paper-trail-v1 + eval-train-10 (~$7; validates invariant-check machinery)

#### TIER 2 — Framework-spec items (resolve during Task 5 implementation)

From framework doc §7 open problems, all spec'd before their implementation touches:

- **§7 #1 Optimizer self-respawn protocol** — handoff-doc schema, respawn criterion, respawn budget. 1M-context default (2026-04-22 update to §5) reduces frequency but doesn't eliminate.
- **§7 #2 Stopping rule for the optimizer** — val F1 patience window vs budget exhaustion vs optimizer self-declared plateau. Textbook train-vs-val gap monitoring as default; pick a specific criterion.
- **§7 #3 Dispatcher-bug risk mitigation testing.**
- **§7 #4 Initial seed knowledge** — paper-trail-v1 prompts + journal-captured failure-mode history (committed 2026-04-21 D29: start from where we are).
- **§7 #5 Per-revision rationale capture** — schema for "what the optimizer did at each revision." Feeds the archive artifact.
- **§7 #6 Empirical validation (agent-only N=10 de-risk smoketest).** Does the optimizer agent move macro-F1 in the right direction autonomously? **Pin:** after Task 5 eval-arm scaffold is in place.
- **§7 #7 Generalization beyond paper-trail** — one-case-study caveat; address by second case study in future paper.
- **§7 #8 Cost accounting.** Cost-per-revision instrumentation already planned in archive framework.
- **§7 #9 Attribution on failure modes.** Per-stage sub-scores via trace-aware metric (D36); schema lives in optimizer workspace.
- **§7 #10 Optimizer agent initial-configuration schema.** Partial spec landed 2026-04-22 (D34: affordance catalog, performance-not-cost philosophy, fight-Python-default, autoresearch direct-lifts, ProTeGi seeded pattern, declined-PromptBreeder). Machine-checkable schema for the `paper-trail-v<N>.json` archive artifact still owed. **Added 2026-04-23 from paper-writeup-items.md topology-may-not-change refinement pass:** the seed prompt currently has *permissive* topology-restructure framing in the framework-doc-§3 affordance catalog ("may restructure"); refine to *invitational* framing — explicitly call out topology restructure as a recommended-to-attempt proposal class worth trying at least once or twice before settling on prompt-text edits. The goal is to raise the chance the realized end-of-experiment outcome is "explored-and-backtracked" (evidence FOR the framework claim) rather than "never-explored" (neutral-to-negative evidence), which makes the topology-may-not-change limitation defensible in the paper. Working draft language landed in framework doc §3 "Topology-restructure invitation" subsection.
- **§7 #11 `--bare` + Agent-tool canary** (listed Tier 0).
- **§7 #12 Round-trip sanity canary** (listed Tier 1 — part of `validate_run.py`).
- **Agent-stall structural defenses** (from framework §5 post-2026-04-22 update): heartbeat + watchdog OR log-line-rate monitor OR stall-as-Tier-1-invariant. Pick mechanism and implement as part of outer harness.

#### TIER 3 — Pre-paper-submission experimental items

- **Task 3: pick `paper-trail-v1` commit SHA.** Find commit on `experiment-plan` immediately before first smoketest-findings-informed prompt edit; verify adjudicator-dispatch-sarol.md has no INDIRECT clauses at that commit; tag. Source: NEXT §3. Blocks the graduated N curve.
- **Task 4: lock eval-train manifests.** Seeded draws at N∈{10,25,50,100,200}, nested. Source: NEXT §4. Blocks first curve points.
- **First curve runs** (Task 6): Variant A at v1 N=10 smoketest → Variant A+C at v1 landmark → apply INDIRECT fix → v2 → rerun.
- **Zero-shot single-prompt baseline on Variant A.** Mandatory paper baseline row (cf. TextGrad Table 3). Cost $5-30. **Pin:** before paper submission, not before Task 5.
- **Variant B 5-paper spot-check gate.** Empirical validation of LLM-judge alignment rate before committing to Variant B as a landmark evaluator. **Pin:** after Task 5 eval-arm lands, before any landmark run. Source: `experiment-sarol-benchmark.md` §"Variant B" (added 2026-04-22).
- **Variant C end-to-end scoring resolution.** Four options documented (subset-score / pre-registered-references / manual-E2E / composite-metric); tentative lean Option B. **Pin:** resolve after Variant B alignment-rate spot-check yields empirical data. Source: `experiment-sarol-benchmark.md` §"Variant C end-to-end scoring" + `paper-writeup-items.md` §"Other paper-level threads."
- **Multi-seed calibration at v1 landmark.** Triple-seed once on v1 to measure noise amplitude (Q4 decision). Source: archive-framework §Q4.
- **Model-drift calendar compression.** Target full train + dev + test inside ~2 weeks of 2026-04-21 to minimize `opus` alias drift. Absolute deadline implicit in the alias pinning limitation.
- **INDIRECT-detection fix → v2 tag.** Draft clauses exist, not applied. Paused until archive framework lands.

#### TIER 4 — Paper-writing content threads (not experiments)

From `paper-writeup-items.md` §"Core contributions" + §"Other paper-level threads" + §"Things to be honest about" + §"Hygiene principles to formalize":

- Related-work section five-bucket structure + specific-competitor comparisons (framework doc §8). Bucket 5 added 2026-04-23 for benchmark-integrity prior art.
- **Mandatory citations in related-work section (new 2026-04-23 post-benchmark-integrity lit-review):** Zhu et al. 2025 (arxiv 2507.02825, Agentic Benchmark Checklist — canonical academic reference), Wang et al. 2026 (Berkeley RDI "How We Broke Top AI Agent Benchmarks" blog, 7-pattern taxonomy + BenchJack + Agent-Eval Checklist), Fan et al. 2025 (arxiv 2512.12806, fault-tolerant transactional-FS sandboxing — future-work reference), METR 2025-06-05 (frontier-model reward-hacking blog, prior motivation for round-trip sanity canary). Framing: "building on Zhu et al.'s ABC and Wang et al.'s Agent-Eval Checklist, we extend benchmark-integrity discipline to the agentic-execution substrate."
- **"Evaluated alternatives" methods-section table (new 2026-04-23):** explicit table documenting 10 structural-defense mechanisms we evaluated (env -i, clean cwd + --add-dir, git worktree, wrapper script, APFS snapshot, sandbox-exec, separate OS user, chmod, Docker, ephemeral VM) with adoption-decision column. Pre-empts "why didn't he just..." reviewer criticism. Source table in `experiment-sarol-eval-arm-isolation.md` "Structural defenses beyond native Claude Code flags (alternatives evaluated)" subsection.
- INDIRECT-detection failure mode narrative + figure
- Severity-under-commitment pattern writeup (pending N=50+ data from Tier 3 curve)
- Cost-per-claim practitioner numbers finalization
- Qualitative comparison to SemanticCite
- Error taxonomy across labels (which classes are easy/hard for LLM adjudicator)
- False-ACCURATE bias as a general LLM-adjudicator finding (if pattern generalizes)
- Cost / wall-clock tradeoff table (Opus/Sonnet/Haiku)
- Variant C coverage metric (`coverage = annotated-citations-with-verdict / annotated-citations`)
- Orchestrator tool-space vs subagent tool-space asymmetry (D35 paper observation)
- Python-default reflex as substrate anti-pattern (D42 paper observation)
- Agent-stall as operational failure mode (new 2026-04-22 paper thread)
- Variant B thread (new 2026-04-22 paper thread)
- Variant C end-to-end brainstorm options (new 2026-04-22 paper thread, may resolve to Option B)
- Hygiene principles to formalize in methods section (subagent sandboxing + Tier 3 sealing)
- Things to be honest about (N=5 not-a-result, Sarol-tests-3-of-7-arms, Variant-A-not-C, pretraining contamination, no weight-level RL, one-shot test commitment, alias-not-hash model pinning, inference-seed not lockable, backend changes invisible)

#### TIER 5 — Open paper-level decisions (logged, not decided)

- **Venue.** ACL/EMNLP/NAACL (NLP); NeurIPS/ICML (ML agentic); CHI/IUI (HCI practitioner); Bioinformatics/JAMIA (biomedical). Source: `paper-writeup-items.md` §"Open paper-level decisions." Deadline-driven once chosen.
- **Companion blog post scope.** Tighter narrative (INDIRECT finding + hygiene) vs full paper repro. Likely former.
- **/paper-trail branding in paper prose.** Probably not; blog can.
- **Paper title.** Workshopped later; current draft directions include something around "Scientific Principles for Agentic Ecosystems with Verifiable Rewards" for framework framing, `paper-trail: Agentic citation auditing for scholarly manuscripts` for case study framing — but now consolidated to one paper (D39), so title needs to reflect both case study and framework. Workshop at draft time.

#### TIER 6 — Deferred with milestone pins (not-this-paper)

Per `feedback_defer_with_milestone_pin.md`. Each has explicit pin.

- **Variant D (raw source papers + independent claim extraction).** **Pin:** consider after Variant C primary results land; possibly follow-up or second paper.
- **Backbone portability (Opus↔Sonnet↔Haiku).** **Pin:** Task 6+ if compute budget allows.
- **Multi-benchmark validation** beyond Sarol. **Pin:** after paper lands.
- **Cost-performance tradeoff curve.** **Pin:** future separate paper.
- **From-scratch bootstrap** (no seed knowledge). **Pin:** separate arm post-v_final.
- **Human-in-the-loop comparison arm.** **Pin:** future separate paper on human-agent research collaboration.
- **Human-agent collaboration retrospective.** **Pin:** future separate paper; data continues to accrue in journal entries.
- **Bandit candidate selection (ProTeGi UCB).** **Pin:** only if we parallelize candidate sweeps; not baseline.
- **LLM-as-loss secondary judge (TextGrad §3.4).** **Pin:** skipped entirely; macro-F1 + per-class F1 sufficient.
- **Hand-crafted topology search procedure (MASS-style).** **Pin:** not implementing; topology-as-optimizer-affordance is allowed.
- **Human A/B blind preference study (Self-Refine App C).** **Pin:** blog-post-only if at all.
- **Full per-N-landmark three-way ablation.** **Pin:** run only at v_final.
- **2025 multi-agent prompt optimization papers (MAPRO, MA-SAPO, MASS)** — one-pass read before final draft. **Pin:** before paper submission.

#### TIER 7 — Non-Sarol plan docs (other threads, off critical path)

Flagged for visibility; not on the current Sarol-experiment critical path. May be relevant for paper-trail-the-product but not the paper.

- **`author-mode-parity.md`** — author-mode LaTeX / orchestrator wiring plan. Parallel product thread.
- **`add-paper-trail-orchestrator.md`** — orchestrator architecture refinement. Parallel product thread.
- **`blindspot-mitigations.md`** — extractor/verifier blindspot mitigation plans. May inform paper-trail-v2+ revisions indirectly but optimizer-driven.
- **`paper-tool-validation.md`** — paper-trail validation plan (synthetic injection, opt-in cohort). Relevant to "pretraining contamination mitigation" paragraph; otherwise parallel.
- **`experiment-sarol-methods-research.md`** — method menu (multi-cit prompting, decomposition, few-shot, rubric phrasing) for future sweeps. **Pin:** post-baseline-iteration.
- **`experiment-sarol-optimization-escalation.md`** — escalation ladder if manual iteration stalls. Trigger-based, not proactively scheduled.
- **`paper-trail-product-backlog.md`** — product backlog for shipping paper-trail-the-tool alongside the paper / blog post (incremental re-validation feature, UI improvements, product docs pass, MCP / skill registry submissions). Created 2026-04-23 by migrating items out of `paper-writeup-items.md` that belonged to product mode rather than paper-writing mode. Off critical path during the current experiment + writeup phase; pick up post-submission.

#### TIER 8 — Historical / milestone docs (read-only, don't edit)

- `experiment-sarol-leakage-hardening.md` — original analysis (superseded by optimization-loop-hygiene)
- `experiment-sarol-hardening-implementation.md` — status of landed defenses
- `experiment-sarol-smoketest-handoff.md` — original N=5 handoff prompt
- `experiment-april-20-findings.md` — N=5 findings (milestone, not updated)

## Recommended next-session sequence

Shortest path to unblocking Task 5:

1. **Run Tier 0 canaries in one ~30-min session.** Q9c memory-blind + D44 `--bare`+Agent-tool. If both pass → Task 5 unblocked; update archive-framework §Q9c + framework §7 #11 to RESOLVED. If either fails → document failure, fallback, retest.
2. **Scope Task 5 build.** Split the big deliverable list (Tier 1) into a sequenced build order with per-deliverable acceptance criteria. Cross-reference the "Implementation-time reference reads" section of NEXT for concrete external artifacts to consult per deliverable.
3. **Execute Task 5 build.** Ship to the smoketest-on-v1 gate (Tier 1 last item).
4. **Run Task 3 (pick v1 commit SHA) + Task 4 (lock manifests at graduated N)** in parallel with or immediately before the v1 smoketest.
5. **First curve points** (Task 6): Variant A at v1 N=10 → v1 landmark → INDIRECT fix → v2.
6. **Variant B spot-check** (Tier 3) in parallel once eval arm can run phase 1 in isolation.

## Open decisions (framework-level)

See `experiment-sarol-archive-and-eval-framework.md` §"Open questions." Currently open:

- **Q4 seeds — resolved.** Two kinds: sample seed (which claims) = fixed + seeded + committed manifests, never redrawn. Inference seed (LLM stochasticity) = single during iteration + one-time triple-seed calibration on v1; multi-seed at locked-candidate + test.
- **Q5 val — resolved.** Val is Sarol's actual dev split (316); dev-50 sampled check at pre-registered gates; per-claim dev failures never inspected. Distinction from train is operational discipline, not data-distribution (Agent insight, credited by Human).
- **Q6 eval-arm change protocol — default applied.** Eval-arm bump invalidates prior results; re-anchor v1 and latest v<N>.
- **Q9c memory-blind mechanism — open, Task 2 above.**

## Things we said we'd test but paused / deprioritized

- **Component-level ablations** (per-subagent attribution of curve movement). Rolled into monolithic tagging + git-diff-at-paper-time. No separate task.
- **Variant C (end-to-end from citing PDF).** Full-pipeline test covering all 7 paper-trail phases. Separate experiment; starts after Variant A's test number is locked. Referenced in `experiment-sarol-benchmark.md` Protocol §6.
- **Methodological sweeps** (multi-cit prompting, decomposition, few-shot, rubric phrasing). See `experiment-sarol-methods-research.md` for the method menu. These happen after the baseline iterations produce a stable-enough config.

## Invariants — do not violate

- **Tiered leakage discipline (agent-only, NEW 2026-04-21).** Train fully open to optimizer; Val scalar-only to optimizer; Test sealed. Structural enforcement via filesystem permissions + fixed-schema dispatcher CLIs. Authoritative: `agentic-pipeline-optimization-framework.md` §2.
- **Test split sealed** at `$HOME/.paper-trail-sealed/sarol-2024-test/`. Never unseal during iteration. This is the Tier 3 sealing.
- **Subagents never see gold labels or raw benchmark data.** Rule 1 from `experiment-sarol-optimization-loop-hygiene.md`. Structural defenses: gold outside repo, opaque citekeys, filesystem-restriction paragraph on every dispatch, scrubbed `staging_info.json`.
- **Val dispatcher returns scalar F1 only.** Per-example val outputs written to `val_runs/v<N>/` — filesystem-restricted from optimizer's `--add-dir` scope. No prose, no per-example data, no failure-mode lists flow back to the optimizer. Schema-validated before return.
- **Rule 2 (main-session blindness) applies in any future human-in-the-loop mode** but is **superseded for agent-only mode** by Tier 3 sealing + the tiered leakage model. See `experiment-sarol-optimization-loop-hygiene.md` for the cross-reference.
- **Memory-blind retrospective eval.** Once Task 2 (the memory-blind mechanism) is resolved, every archived eval run must use `--bare`. No exceptions. Currently ON HOLD pending canary sanity-check.
- **Eval arm changes force re-baselining.** Once `experiments/sarol-2024/eval-harness/` is created and first used, any commit modifying it without rerunning v1 invalidates the curve.
- **Model pinning.** Every subagent dispatch uses `model: "opus"`. Orchestrator invoked with `claude --model opus --print ...`. Each archived `summary.json` records the Claude Code version at run time as proxy for alias-drift detection. Mixed-model runs (opus/sonnet/haiku mix) are reserved for a named ablation branch, never the main curve.
- **Calendar discipline for model-drift mitigation.** Target completion of all train + dev + test runs within ~2 weeks of 2026-04-21. Beyond that window, the risk of a silent `opus` alias drift grows; we either compress the schedule, re-baseline if we cross a version boundary, or accept the limitation explicitly.
- **Measurement invariants are validated at every run.** Three-tier classification (invariants / logged / free) is defined in `experiment-sarol-archive-and-eval-framework.md` §"Measurement invariants and validation." Invariant violations invalidate the run. Tier 1 includes: prompt file hashes, eval-arm hashes, model aliases, subset manifest hash, benchmark + gold data hashes, env vars, memory-blind status, rubric variant, orchestrator slot-fill determinism. Tool permissions + MCP servers are NOT Tier 1 — they are part of the agentic system's design captured by the `paper-trail-v<N>` git tag; commit their config to the repo rather than leaving in user-global settings. Validator (`validate_run.py`) is built as part of Task 5 (eval arm build).

## Paper contributions pursued (short list — full discussion in paper-writeup-items.md)

Revised 2026-04-21 after lit-review pass **and** the agent-only reframe. Framework-first contribution ordering; paper-trail is the case study.

1. **Framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline.** Primary contribution. Tiered access model (Train fully open to optimizer / Val scalar-only / Test sealed) with structural enforcement (filesystem permissions + fixed-schema dispatcher CLIs, not trust-based). Authoritative in `agentic-pipeline-optimization-framework.md`. No prior art in the 9-paper lit review argues per-example val inaccessibility for the optimizer — that's the novel layer on top of standard held-out hygiene.
2. **Agent-only optimizer architecture with structural defenses.** Optimizer agent + deterministic Python dispatcher + uniform-invocation eval subagents. Filesystem scoping + locked output schemas + dispatcher-not-agent are the mechanisms. Attack-surface analysis included.
3. **Paper-trail citation-integrity pipeline on Sarol-2024 as the case study / proof point.** The framework applied to a real multi-subagent pipeline (extractor / adjudicator / verifier) on a labeled biomedical benchmark.
4. Train+val curve over agent-driven revisions as headline figure — **further narrowed post-reframe**. OPRO §5.4 / Figure 11 and MIPROv2 Appendix G publish the figure shape with algorithmic revisions. Our novelty is: (i) divergence as explicit stopping rule (OPRO defers this to future work), (ii) multi-subagent pipeline application, (iii) under Tier 2 scalar-only-val discipline (which no prior work enforces). Loses the "human-driven" differentiator; gains the "tiered-leakage-disciplined" differentiator.
5. First 9-way Sarol baseline.
6. INDIRECT-detection failure mode, named and remedied.
7. Severity-under-commitment pattern (s4, tentative).
8. Cost-per-claim practitioner numbers.

**Dropped / moved after reframe:**
- **"Multi-subagent pipeline iteration formalized" as standalone.** DSPy + MIPROv2 + BetterTogether + MAPRO + MASS scooped this. Cite as prior art.
- **Human-in-the-loop framing + "human-value-in-agentic-collaboration retrospective" as a current-paper arm.** Moved to a future separate paper. Planning-phase material still collected in `paper-writeup-items.md` §"Human-value retrospective" for that future paper.

## Implementation-time reference reads (do not read now — read at Task 5 build time)

Concrete external artifacts to pull up when implementing specific Task 5 deliverables. Not decisions-to-make-now; references-to-consult-when-coding. Flagged here so a fresh agent starting Task 5 knows what to read before writing code.

**For the optimizer instruction document (`experiments/sarol-2024/optimizer/program.md`):**
- Karpathy's `program.md`: https://github.com/karpathy/autoresearch/blob/master/program.md — read in full. Structure to mirror: Setup / Experimentation / Output format / Logging results / The experiment loop. Lift NEVER STOP rule, simplicity criterion, CAN/CANNOT block, output-flood prevention, crash-handling discipline verbatim with attribution.
- Karpathy's `README.md` at the same repo — context on design-choices framing.

**For the immutable-harness mechanism (pre-commit hook + filesystem enforcement):**
- Karpathy's `prepare.py`: https://github.com/karpathy/autoresearch/blob/master/prepare.py — reference for the *pattern* (constants + evaluation function in a canonically-read-only file). Note autoresearch's enforcement is instruction-only; ours is structural (pre-commit hook + OS filesystem permissions + out-of-tree gold/benchmark). Extend, don't copy.
- Autoresearch issue #384 (BPB silent bug): https://github.com/karpathy/autoresearch/issues/384 — motivation for our round-trip sanity canary (D46).

**For the per-revision results table / archive format:**
- Karpathy's `results.tsv` specification (described in `program.md` §"Output format"). 5 columns: `commit / val_bpb / memory_gb / status / description`. Our analog: `commit / macro_f1 / per_class_summary / status / description`. **Commit ours** (Karpathy gitignores his; we need archival).

**For the train+val curve figure generation:**
- Karpathy's `analysis.ipynb`: https://github.com/karpathy/autoresearch/blob/master/analysis.ipynb — reference implementation for generating `progress.png` from a committed results table. Adapt for our train+val curve over `paper-trail-v<N>`.

**For the dispatcher architecture and split access control:**
- VeRO paper (arxiv 2602.22480) §3.3 "Fair Comparison Across Optimizers" and Algorithm 1 — study the `DatasetViewer` / `ExperimentViewer` / `FileTools` / `ExperimentRunner` / `GitControl` abstraction. Consider aligning our dispatcher naming for reviewer legibility. If VeRO has a public GitHub repo at Task 5 time, pull their `DatasetViewer` and `Filesystem` access-control code as a reference implementation for our glob-pattern defenses on the non-sealed tiers. Our OS-level sealing is strictly harder, so adopt complementarily, not as a replacement.
- VeRO §3.3 on uv-package reproducibility — cite the framing; map our analog (committed `.claude/commands/*.md` + `.claude/agents/*.md` + `.claude/settings.json` + MCP config at the `paper-trail-v<N>` git tag).

**For the optimizer's affordance catalog and initial prompt:**
- Framework doc `agentic-pipeline-optimization-framework.md` §3 "Optimizer agent initial configuration" — authoritative spec for content (seeded patterns, philosophy, anti-pattern-to-fight, direct-lifts from autoresearch).
- Anthropic Claude Code subagents documentation: https://docs.anthropic.com/en/docs/claude-code/sub-agents — reference for the full controllability surface (`model`, `tools`, `disallowedTools`, `mcpServers`, `permissionMode`, `memory`, `skills`, `isolation`) that is our optimization space per claim 8.

**For the `--bare` + Agent-tool compatibility check (D44 canary):**
- Claude Code headless mode docs: https://code.claude.com/docs/en/headless — verify `--bare` / `--print` / `--allowedTools` flag semantics. If canary fails, compose with `--allowedTools Agent` per docs.

**For the related-work section of the paper:**
- Meta-Harness (arxiv 2603.28052) — read to confirm exact `--disable-slash-commands` language and the `claude_wrapper.py` architecture. Cite for the substrate-choice contrast.
- AlphaEvolve (arxiv 2506.13131) — §6 discussion for the future-work quote; §2.4 for the evaluation cascade pattern.
- Ellenberg et al. (arxiv 2503.11061) §3.1 — exact contamination-warning quote.
- ADAS (arxiv 2408.08435) §2 — "code search space" argument quote.
- AFlow (arxiv 2410.10762) Figure 5 — closest figure-type precedent.
- Anthropic Claude Code Agent Skills announcement (Oct 2025) — for the "agents editing their own skills" future-work framing we're effectively instantiating.

**Flag for paper-submission-time re-check** (not Task 5, but before submission):
- VeRO's GitHub repo (if released) — pull latest impl for citation-tightness.
- 2026-04-22-and-later arxiv listings on "agent-as-optimizer" / "agentic experimentation" / "self-evolving agent" — this field is moving fast; re-sweep ~2 weeks before submission.
- Anthropic engineering blog and research page — new posts in this space are likely between now and submission.

## Reading path for a fresh agent

1. This file (NEXT.md).
2. `CLAUDE.md` — repo orientation and conventions.
3. `docs/plans/experiment-sarol-archive-and-eval-framework.md` — the framework we're implementing.
4. `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — the hygiene rules.
5. `docs/plans/experiment-april-20-findings.md` — the smoketest findings that triggered all this.
6. `docs/plans/paper-writeup-items.md` — paper framing.
7. Most recent entry in `docs/journal/` — what was discussed and decided in the last working session.
