# Experimental plan of record

**Scope.** Single-artifact consolidated view of the experiment, phase by phase, from current state through paper submission. Created 2026-04-23 as the Tier-0 meta-task precursor to Task 5 (eval-arm scaffolding). Form is outline-with-pointers — each section names the authoritative deep-spec doc rather than duplicating its content. Intent is a navigable artifact a fresh agent or a human collaborator can read end-to-end in ~20 minutes and know (a) what we are claiming, (b) how we plan to earn it, (c) what we have explicitly deferred, and (d) which doc to open for depth on any given topic.

**Status.** First-pass outline. Will be pressure-tested by a soundness-review agent (patterned after the 2026-04-22 Rule-3 critic audit). Findings from that review fold back here before Task 5 scaffolding begins.

**Provenance.** Human 2026-04-23 raised that planning has accreted non-linearly across ~20 sessions into ~15 specialized docs with no single holistic view, which makes it hard for an agent to reason over the whole plan and hard for Human to explain the work to a colleague. This doc is the single-place answer to "what is the plan?" — everything below is consolidation; the deep specs remain authoritative.

**How to read this.** If you're fresh: read this top-to-bottom. If you're picking up active work: NEXT.md is the always-current status doc; this file is the big-picture map.

---

## 1. Thesis

**One-sentence claim.** A framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline (Train fully open / Val scalar-only / Test sealed) with structural enforcement (filesystem permissions + fixed-schema dispatcher CLIs) — instantiated on paper-trail (a citation-integrity pipeline) evaluated on the Sarol-2024 benchmark.

**Elaboration.** Standard held-out-set discipline is a training-time practice that has never, to our 9-paper lit-review knowledge, been applied structurally to LLM-agent prompt iteration where the optimizer is itself an agent with tool access. We argue it should be, and show one way to enforce it without trust-based appeals to optimizer discipline. Paper-trail + Sarol demonstrates the framework works on a non-trivial real task; the framework is the primary contribution, the case study is the proof point.

**Authoritative source for thesis phrasing:** `agentic-pipeline-optimization-framework.md` §1 (lines 32-37). Lit-review context: `paper-writeup-items.md` §"Net lit-review verdict (2026-04-21)."

---

## 2. Contributions

**Primary (framework layer):**

1. **Framework for agent-only optimization under tiered leakage discipline.** Tier 1 (Train) fully open to optimizer; Tier 2 (Val) scalar-only; Tier 3 (Test) physically sealed. Enforcement structural (filesystem + locked output schemas), not trust-based. No prior art in the 9-paper lit review argues per-example val inaccessibility for the optimizer.
2. **Agent-only optimizer architecture with structural defenses.** Optimizer agent (outer, long-lived, respawnable) + deterministic Python dispatcher + uniform-invocation eval subagents (fresh context per claim). Filesystem scoping + locked output schemas + dispatcher-not-agent are the mechanisms. Attack-surface analysis in framework §4.

**Secondary (case study layer):**

3. **Paper-trail citation-integrity pipeline on Sarol-2024.** Multi-subagent pipeline (extractor / adjudicator / verifier) evaluated on a labeled biomedical benchmark. Proof point for the framework.
4. **Train+val curve over agent-driven revisions as headline figure** — narrowed post-lit-review. OPRO Fig 11 + MIPROv2 App G publish the figure shape with algorithmic revisions; our novelty is (i) divergence as explicit stopping rule, (ii) multi-subagent pipeline application, (iii) under Tier 2 scalar-only-val discipline.
5. First 9-way Sarol baseline.
6. INDIRECT-detection failure mode, named and remedied.
7. Severity-under-commitment pattern (s4, tentative; pending N=50+ data).
8. Cost-per-claim practitioner numbers.

**Dropped / moved:**
- "Multi-subagent pipeline iteration formalized" as standalone — DSPy + MIPROv2 + BetterTogether + MAPRO + MASS scoop this. Cite as prior art.
- "Human-in-the-loop framing + human-value retrospective" — moved to a future separate paper (D30). Dataset continues to accrue in journals.

**Authoritative source:** `paper-writeup-items.md` §"Core contributions" + `NEXT.md` §"Paper contributions pursued" (lines 351-366). Both kept in sync.

---

## 3. Phase-by-phase plan

Phases are gates, not calendar weeks. Each phase has deliverables, a success gate, and descope triggers.

### Phase 0 — Current state (Tier 0 resolved)

**State as of 2026-04-23.** Infrastructure-design phase complete. Three Tier-0 gates resolved:
- E3 dataset-extension feasibility — GREEN (70 Train buckets, 2,141 annotations, ~1,900 PDFs to fetch, ~1.5 eng-days). Source: `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md`.
- Memory-blind invocation (iteration tier) — verified under OAuth. Source: `docs/journal/2026-04-22-memblind-oauth-findings.md`.
- D44 `--bare` + Agent-tool compatibility — docs-sweep resolved; empirical landmark-tier (Vertex) pending VM session per `canary-runbook-vertex.md`.

**Architectural commitments.** Two-tier eval-arm (iteration via wrapper script `scripts/run-eval.sh`; landmark via Dockerfile with pinned Claude Code binary). IN/OUT formalization committed. Ten structural defenses evaluated (env -i, clean cwd + --add-dir, git worktree, wrapper script, APFS snapshot, sandbox-exec, separate OS user, chmod, Docker, ephemeral VM).

**Authoritative:** `experiment-sarol-eval-arm-isolation.md` (canonical invocation shapes + IN/OUT formalization + alternatives-evaluated catalog), `tier-0-resolution-2026-04-22.md` (milestone summary), `docs/journal/2026-04-23-benchmark-integrity-lit-review.md` (Zhu et al. ABC + Wang et al. checklist integration).

**Exit gate:** (already passed). Plan-of-record doc (this file) + soundness review are the last Phase-0 outputs before Phase 1 begins.

### Phase 1 — Task 5: Eval-arm build

**Deliverables** (full list in NEXT.md §5, lines 82-137). Grouped by function:

- **Three dispatcher scripts.** `run_train_eval.py` (full traces + aggregates, D47), `run_val_eval.py` (scalar-only, D24), `run_test_eval.py` (with `--confirm-unseal` tripwire).
- **E3 dispatcher + E3 dataset extension** (D50/D51). Dataset extension ~1.5 eng-days; dispatcher orchestrates phases 2-5 of paper-trail.
- **E1 sub-dispatcher** (D52, optimizer affordance for cheap sample-efficiency checks).
- **`/sarol-eval-item` slash command.** Non-interactive, locked arg set. `/sarol-eval` I/O contract is a non-deferrable build-time spec (D20).
- **Invariant checker `validate_run.py`.** Tier 1 pre-run, per-dispatch, post-run. Includes round-trip sanity canary (D46) and per-claim budget enforcement (D45, model-call count primary, wall-clock secondary, 1.5× v1). `expected_invariants.json` schema is a non-deferrable build-time spec (D20).
- **Schema validator module** (shared across dispatchers; locked schemas in `eval-harness/schemas/`).
- **Filesystem-permission boundary tests.** Confirm optimizer `--add-dir` scope cannot read val/, val_runs/, test/, test_runs/.
- **Wrapper script `scripts/run-eval.sh`** (canonical operator interface, ~80 lines bash) + **landmark Dockerfile** (pinned `@anthropic-ai/claude-code@<version>`).
- **Custom-subagent JSON registry builder** (new 2026-04-22). Emits `subagent-registry-v<N>.json` per tag.
- **Adversarial-agent smoketest suite** (D54, from Berkeley Agent-Eval Checklist + Zhu et al. ABC): null_agent, random_agent, injection_agent, tamper_agent.
- **Scorer adversarial audit** (D54) + **LLM-judge sanitization audit** (D54).
- **E3 crashed-task semantics** (D54): fetch-failure → FAILED_FETCH class, counts against macro-F1 denominator.
- **Pre-commit hook** enforcing eval-harness immutability on non-eval branches (D10).
- **Per-experiment `.claude/settings.json` + MCP config** committed to the repo (captured by paper-trail-v<N> git tag).
- **`paper-trail-v<N>.json` archive artifact** schema. Includes proposed-but-rejected topology logging (D55).
- **`program.md`-equivalent optimizer instruction document** (D42, `experiments/sarol-2024/optimizer/program.md`, mirroring Karpathy autoresearch structure).
- **5-column `results.tsv`-equivalent per-revision table** (committed; we don't gitignore ours as Karpathy does).
- **Analysis notebook** for train+val curve regeneration (reference: autoresearch `analysis.ipynb`).
- **Move orchestrator-runtime decisions into eval-arm Python** (D5). Verifier sampling, retry, bounce, schema validation all static.
- **3-seed minimum at v1 landmark** (non-negotiable per lit-review convergent signal).
- **Train dispatcher emits raw per-subagent traces + macro-F1 + per-class F1** (D36, topology-agnostic; no pre-computed per-stage sub-scores — optimizer owns the trace-aware metric).

**Pre-Task-5 canary sweep** (9 items; 5 from 2026-04-22 critic audit + 4 adversarial-agent smoketests). Full specs in `experiment-sarol-eval-arm-isolation.md` §"Residual investigation items." Token rotation reminder before running: `CLAUDE_CODE_OAUTH_TOKEN` from 2026-04-22 session was exposed in transcript.

**Authoritative:** `agentic-pipeline-optimization-framework.md` §"Implementation checklist" + `NEXT.md` §5 + `experiment-sarol-archive-and-eval-framework.md` §"Measurement invariants and validation."

**Exit gate.** Smoketest on paper-trail-v1 + eval-train-10 (~$7) validates invariant-check machinery fires correctly, round-trip sanity canary returns expected verdict, all Tier 1 invariants pass, run-invariants block written to `summary.json`.

**Descope triggers.**
- If smoketest macro-F1 at v1 < 30%: descope to manual-iteration warm-up before full curve (Tier 3 gate, NEXT.md line 235).
- If validator complexity > 200 LOC for a single tier: split into per-tier sub-validators.
- If dispatcher schema inflation > 5 keys: move richness to optimizer workspace (D36 precedent).
- If E3 dataset-extension engineering > 3 days: swap to E3-lite (pre-resolved references) or demote E3 to landmark-only + make E1 primary.

### Phase 2 — v1 tag + smoketest

**Deliverables.**
- **Task 3:** Pick `paper-trail-v1` commit SHA on `experiment-plan` immediately before first smoketest-findings-informed prompt edit. Verify `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` at that commit has no INDIRECT-specific clauses. Tag.
- **Task 4:** Lock eval-train manifests at N ∈ {10, 25, 50, 100, 200} (nested: subset-50 ⊂ subset-100 ⊂ subset-200). Seeded random draws from `claims-train.jsonl`. Committed.

**Authoritative:** `NEXT.md` §3 + §4.

**Exit gate.** v1 tag exists; v1 archive artifact `paper-trail-v1.json` written per schema; eval-train-10 smoketest clean (same gate as Phase 1 exit — Phase 2 is the first real use of Phase 1 machinery).

**Descope triggers.**
- If no clean commit exists pre-smoketest-edits: reconstruct from git history or accept a small INDIRECT-clause leak and document honestly.

### Phase 3 — Iteration curve under optimizer

**Deliverables.**
- Graduated-N ramp: iterate at cheap-N during optimizer loop (10/25/50/100/200); landmark at 2,141 (full train) per user's "ramp dataset size slowly" proposal (NEXT.md §4 adopted 2026-04-21).
- Optimizer autonomously proposes revisions → Python dispatcher evaluates on chosen split → optimizer reads train-tier rich trace + val-tier scalar F1 → decides: propose another revision, respawn with handoff doc, or declare stopping.
- E3 (fetch-through-verdict, the canonical headline metric, D50/D53) at iteration cadence; E1 (verdict-only, D52) is optimizer-optional for cheap pre-checks — logged but NOT on canonical curve.
- 5-column `results.tsv`-equivalent committed per revision: `commit / macro_f1 / per_class_summary / status / description`.
- Per-revision archive artifact `paper-trail-v<N>.json` with proposed-but-rejected topology logging (D55).
- Open framework §7 problems resolved during this phase: #1 respawn protocol, #2 stopping rule, #3 dispatcher-bug mitigation testing, #5 per-revision rationale capture, #8 cost accounting, #9 attribution on failure modes.

**Authoritative:** `agentic-pipeline-optimization-framework.md` §3 (optimizer architecture) + §5 (respawn) + §7 (open problems) + `experiment-sarol-benchmark.md` §"Variant strategy" (2026-04-21 decision) + `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` (D32, D34, D36).

**Exit gate.** Optimizer declares stopping (patience window on val F1 OR budget exhausted OR optimizer self-declared plateau). Train-val divergence detected. v_final tagged.

**Descope triggers.**
- If optimizer stalls (no new revisions for 2 hours): heartbeat + watchdog per framework §5 alternative OR manual reset with fresh handoff doc.
- If N=50 shows < 2% macro-F1 improvement from v1 after 5 revisions: declare seed baseline near-optimal; stop at v5; lock for final eval.
- If E3 cost-per-run at v1 > budget: revert to E1 as primary; report E3 only at v_final.
- If topology stays fixed across all revisions: confirm via proposed-but-rejected log (D55) whether "explored-and-backtracked" (defensible) or "never-explored" (bad — optimizer seed prompt under-invitational); if latter, iterate seed prompt once before paper.

### Phase 4 — Landmark tags + v_final + test unseal

**Deliverables.**
- **v_final landmark eval.** Triple-seed at N = {2141 (full train), 316 (full dev/val)}, single unseal at N = 606 (full test).
- **`--confirm-unseal` tripwire** exercised exactly once.
- **Variant B 5-paper spot-check gate** (Tier 3, `experiment-sarol-benchmark.md` §"Variant B" added 2026-04-22) — empirical validation of LLM-judge alignment rate before committing to landmark evaluator.
- **Variant C end-to-end scoring resolution** (Tier 3, options A-D documented; tentative lean Option B per `experiment-sarol-benchmark.md` §"Variant C end-to-end scoring").
- **Zero-shot single-prompt baseline** on E1 (mandatory paper baseline row, cf. TextGrad Table 3, $5-30).
- **Full per-N-landmark three-way ablation** at v_final only (Tier 6 pin).
- Archive all runs to `experiments/sarol-2024/archive/paper-trail-v_final/`.

**Authoritative:** `NEXT.md` §7 Tier 3 + `experiment-sarol-archive-and-eval-framework.md` §"Archive directory" + §Q4 resolution (multi-seed calibration).

**Exit gate.** Test macro-F1 within calibration variance of val macro-F1 (e.g., ±3%). All Tier 1 invariants pass across all seeds. Landmark Dockerfile reproduces results within variance.

**Descope triggers.**
- If test F1 degrades > 10% from val F1: investigate for label leakage; document honestly in paper limitations. Do NOT reseal and re-tune — test is one-shot.
- If any landmark run violates a Tier 1 invariant: re-run, don't post-hoc patch archived data.
- If calendar window since 2026-04-21 > 3 weeks: re-baseline v1 under current `opus` alias to check for silent drift OR accept + disclose the limitation.

### Phase 5 — Paper writing

**Deliverables.**
- Manuscript, 25-35 pages double-spaced. Sections: abstract, introduction, framework (methods-first per D23/D43), case study (paper-trail + Sarol), related work (five-bucket structure per D33 + D41 with Bucket 5 for benchmark-integrity, D54), limitations (full "things to be honest about" list), open problems (framework §7), appendix (framework-reproducibility artifacts per D37: optimizer init prompt, dispatcher schemas, headless invocation spec, memory-blind canary design/result, "evaluated alternatives" table D54).
- Headline figure: train+val curve over `paper-trail-v<N>` revisions, regenerated from committed `results.tsv` via analysis notebook.
- Mandatory citations (D41, D54): DSPy + MIPROv2 + OPRO (prior), Hyperagents (corroborating val-overfitting), Zhu et al. + Wang et al. + Fan et al. + METR (benchmark-integrity prior art).
- Blog post optional (tighter narrative — INDIRECT + hygiene — per `paper-writeup-items.md` §"Open paper-level decisions").

**Authoritative:** `paper-writeup-items.md` (full prose drafting + section structure) + `agentic-pipeline-optimization-framework.md` §8 (related work five-bucket) + this doc §6 "Non-goals" (for limitations section).

**Exit gate.** Submission-ready manuscript + rebuttal prep covering all "why didn't you" attack surfaces (evaluated-alternatives table, honest non-goals list, Tier 2 limitations disclosed).

**Descope triggers.**
- If 9-paper lit review surfaces new scoop: re-evaluate contributions list before draft freeze.
- If MAPRO / MA-SAPO / MASS final read reveals overlap with Claim B remnants: further narrow headline framing.

---

## 4. Explicit non-goals

Each non-goal has a milestone pin per `feedback_defer_with_milestone_pin.md`.

| Non-goal | Pin |
|---|---|
| Variant D (raw source papers + independent claim extraction) | Consider after Variant C results; possibly follow-up / second paper |
| Backbone portability (Opus ↔ Sonnet ↔ Haiku) | Task 6+ if compute budget allows |
| Multi-benchmark validation beyond Sarol | After paper lands |
| Cost-performance tradeoff curve (manager/advisor agent adjudicating cost vs perf) | Future separate paper |
| From-scratch bootstrap (no seed knowledge) (D29) | Separate arm post-v_final |
| Human-in-the-loop comparison arm (D22) | Future separate paper on human-agent research collaboration |
| Human-agent collaboration retrospective (D30) | Future separate paper; dataset accrues in journals |
| Bandit candidate selection (ProTeGi UCB) | Only if we parallelize candidate sweeps; not baseline |
| LLM-as-loss secondary judge (TextGrad §3.4) | Skipped entirely; macro-F1 + per-class F1 sufficient |
| Hand-crafted topology search procedure (MASS-style) | Not implementing; topology-as-optimizer-affordance (D32) instead |
| Human A/B blind preference study (Self-Refine App C) | Blog-post-only if at all |
| Full per-N-landmark three-way ablation | Run only at v_final, not at every landmark |
| 2025 multi-agent prompt optimization papers (MAPRO, MA-SAPO, MASS) full deep-read | One-pass read before final draft only |

**"Things to be honest about"** (disclosed as paper limitations, not mitigated further):
- N=5 not-a-result (initial smoketest, not curve point)
- Sarol tests 3 of 7 paper-trail arms (phases 5-7 only; E3 extends to phases 2-5 of the pipeline but still not the full fetch-to-reference-resolution arc)
- E1 (verdict-only) used for iteration; E3 (fetch-through-verdict) only at landmark
- Pretraining contamination — Sarol may appear in Opus training; disclosed but not mitigated
- No weight-level RL (prompt-optimization only)
- One-shot test commitment — cannot re-evaluate test if we find a bug post-unseal; disclose
- Alias-not-hash model pinning — `opus` alias may silently resolve to new version; calendar-compression mitigates (D18)
- Inference seed not lockable — Opus non-deterministic; triple-seed calibration compensates (D17)
- Backend changes invisible (Anthropic may update weights / routing / caching; no mitigation)
- **Topology-may-not-change** (D55): if optimizer converges back to seed topology, distinguish "explored-and-backtracked" (FOR) from "never-explored" (AGAINST) via proposed-but-rejected archive log.

**Authoritative:** `NEXT.md` Tier 6 (lines 275-291) + `paper-writeup-items.md` §"Things to be honest about."

---

## 5. Decision log (D1-D55+)

Consolidated from journal entries. For full rationale + attribution, open the cited journal doc. Lookup index: "what did we decide about X?" → find D-number → open journal for depth.

| D# | Decision | Status | Source |
|---|---|---|---|
| D1 | Frame prompt iteration as a training curve (train+val F1 vs revision index) | settled | `docs/journal/2026-04-21-archive-framework-decisions.md` |
| D2 | Archive via immutable git tags `paper-trail-v<N>`, not branches | settled | ibid |
| D3 | Retire "SUT" jargon; use "the model" or `paper-trail-v<N>` | settled | ibid |
| D4 | eval-train-50 uses random sampling, not stratified | settled | ibid |
| D5 | Orchestrator-runtime decisions move into static eval-arm Python | settled | ibid |
| D6 | "Time evolution of memory" framing — future memory leaking backward is NOT okay; memory improving over time IS okay | settled | ibid |
| D7 | Doc organization: `docs/plans/`, `docs/journal/YYYY-MM-DD-*.md`, CLAUDE.md | settled | ibid |
| D8 | Attribution convention: **Human:** / **Agent:** inline markers | settled | ibid |
| D9 | Monolithic `paper-trail-v<N>` version tagging (not per-subagent) | settled | ibid |
| D10 | Eval arm as subdirectory + pre-commit hook (Option B) | settled | ibid |
| D11 | Headless Claude Code as eval invocation (not SDK) | settled | ibid |
| D12 | Document "Sarol tests 3 of 7 paper-trail arms" honestly in paper | settled | ibid |
| D13 | Graduated-N ramp N ∈ {10, 25, 50, 100, 200, 2141}; nested subsets | settled | ibid |
| D14 | Val distinct from train via operational discipline (same distribution, no per-claim inspection) | settled | ibid |
| D15 | Paper-writeup-items cross-references faithfulness doc rather than duplicates | settled | ibid |
| D16 | NEXT.md is living always-current status doc | settled | ibid |
| D17 | Two kinds of seed: sample seed (locked, committed) + inference seed (single during iteration + triple-seed on v1 + multi-seed at test) | settled | ibid |
| D18 | Model pinning alias-only + calendar-compressed (~2 weeks from 2026-04-21); record Claude Code version as drift proxy | settled | ibid |
| D19 | Three-tier measurement-invariant framework (Tier 1 declared-and-locked / Tier 2 logged-for-drift / Tier 3 free variables) | settled | ibid |
| D20 | Two build-time specs non-deferrable: `expected_invariants.json` schema + `/sarol-eval` I/O contract | settled | ibid |
| D22 | **Experiment is agent-only** (optimizer is an agent, no human-in-the-loop) | settled 2026-04-21 | `docs/journal/2026-04-21-tiered-leakage-framework-decisions.md` |
| D23 | Framework is primary contribution; paper-trail + Sarol is case study | settled 2026-04-21 | ibid |
| D24 | Three-tier leakage discipline: Train R=full / Val R=scalar / Test R=∅ during iteration | settled 2026-04-21 | ibid |
| D25 | Optimizer architecture: agent (outer) + dispatcher (Python) + subagents (fresh-context) | settled 2026-04-21 | ibid |
| D26 | Dispatcher-as-script, not agent | settled 2026-04-21 | ibid |
| D27 | Uniform headless invocation across train + val (same subagent; dispatcher routes differently) | settled 2026-04-21 | ibid |
| D28 | Correction: same subagent, different output routing (not different subagent behavior) | settled 2026-04-21 | ibid |
| D29 | From-scratch variant deferred | settled 2026-04-21 | ibid |
| D30 | Human-agent collaboration retrospective → future separate paper | settled 2026-04-21 | ibid |
| D31 | Docs updated in single coordinated pass (2026-04-21) | settled | ibid |
| D32 | **Topology is a free variable for the optimizer**; extractor/adjudicator/verifier is seed knowledge, not design commitment | settled 2026-04-22 | `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` |
| D33 | Three-bucket related-work positioning (fixed-topology / topology-search-procedure / ours) | settled 2026-04-22 | ibid |
| D34 | Optimizer initial affordance catalog — partial (performance-not-cost, fight-Python-default, lit-review-OK); full Tier-1-invariant schema still owed (framework §7 #10) ⚠ | partial | ibid |
| D35 | Orchestrator tool-space vs subagent tool-space asymmetry (paper observation) | settled 2026-04-22 | ibid |
| D36 | Trace-aware sub-score metric is optimizer-owned, not frozen eval infrastructure | settled 2026-04-22 | ibid |
| D37 | Paper appendix publishes framework artifacts (optimizer prompt, schemas, canary design); NOT per-revision case-study prompts ⚠ contingent on D39 paper-split | settled 2026-04-22 | ibid |
| D38 | Don't seed PromptBreeder mutation-operator catalog; cite-only (topology-freedom compatibility) | settled 2026-04-22 | ibid |
| D39 | One paper, consolidated (framework + case study in single submission) ⚠ venue may force split | settled (revisit at venue choice) | `docs/journal/2026-04-22-lit-review-2-competitor-landscape.md` |
| D40 | Drop "recursive subagent spawning" framing; replace with heterogeneous-controllability + topology-as-search-space (later softened per D49) | settled 2026-04-22 | ibid |
| D41 | Required citations + five-bucket structure for related work | settled 2026-04-22 (extended by D54) | ibid |
| D42 | Autoresearch direct-lifts adopted (NEVER STOP, simplicity, CAN/CANNOT, output-flood, crash-handling) with attribution | settled 2026-04-22 | ibid |
| D43 | Contribution ordering aligned with D23 (framework primary, case study secondary) | settled 2026-04-22 | ibid |
| D44 | `--bare` + Agent-tool compatibility canary — docs-resolved (`--tools default` + `--agents <json>`); empirical landmark pending | resolved iteration; landmark pending | ibid |
| D45 | Per-claim budget as Tier 1 invariant (model-call-count primary, 1.5× v1 default) | settled 2026-04-22 | ibid |
| D46 | Round-trip sanity canary per run (guards silent metric bugs — autoresearch #384 precedent) | settled 2026-04-22 | ibid |
| D47 | Per-claim adjudicator reasoning + verifier narrative in train-tier rich schema (val stays scalar) | settled 2026-04-22 | ibid |
| D48 | Substrate choice: Claude Code (evidence-based: 13/13 surveyed agent-as-optimizer papers use platform-native harnesses) | settled 2026-04-22 | `docs/journal/2026-04-22-substrate-claude-code-vs-pydantic-ai.md` |
| D49 | Claim #8 softened from "contribution" to "case-study instantiation rationale" (methodology portable) | settled 2026-04-22 | ibid |
| D50 | Design for E3 (fetch-through-verdict) as primary experiment | settled 2026-04-22 | `docs/journal/2026-04-22-experiment-design-e1-e4.md` |
| D51 | E3 input shape requires dataset extension — GREEN (~1.5 eng-days) | settled 2026-04-22 (feasibility GREEN) | ibid + `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md` |
| D52 | Optimizer affordance: E1 sub-dispatcher for sample-efficiency checks (not canonical curve) | settled 2026-04-22 | ibid |
| D53 | Adopt E1/E2/E3/E4 naming canonical; retire Variant A/B/C/D | settled 2026-04-22 | ibid |
| D54 | Benchmark-integrity lit-review integration: Zhu et al. ABC + Wang et al. Berkeley checklist → Bucket 5 + Task 5 adversarial-smoketest suite | settled 2026-04-23 | `docs/journal/2026-04-23-benchmark-integrity-lit-review.md` |
| D55 | Proposed-but-rejected topology logging in per-revision archive artifact + seed-prompt "Topology-restructure invitation" | settled 2026-04-23 | `paper-writeup-items.md` §Things-to-be-honest-about + `agentic-pipeline-optimization-framework.md` §3 |

**Legend.** Settled = locked, do not relitigate without strong new evidence. Partial = decided in principle, implementation detail owed. Resolved (iteration / landmark pending) = canonical shape settled; empirical confirmation at landmark tier pending canary execution.

---

## 6. Doc landscape + cross-reference map

**Authoritative deep-spec docs** (edit in place):

| Doc | Scope | Line count |
|---|---|---:|
| `docs/plans/agentic-pipeline-optimization-framework.md` | Framework plan (PRIMARY). Tiered leakage, architecture, optimizer affordances, open problems, implementation checklist, related-work five-bucket. | 539 |
| `docs/plans/NEXT.md` | Always-current status + Tier 0-8 + immediate next steps | 418 |
| `docs/plans/paper-writeup-items.md` | Paper prose + contribution list + limitations + lit-review synthesis | 604 |
| `docs/plans/experiment-sarol-archive-and-eval-framework.md` | Archive schema + invariants + eval cadence + memory-blind | 507 |
| `docs/plans/experiment-sarol-benchmark.md` | Sarol-specific dataset + E1/E3 strategy + scoring | 394 |
| `docs/plans/experiment-sarol-runbook.md` | Pipeline execution runbook | — |
| `docs/plans/experiment-sarol-faithfulness.md` | Phase-by-phase variant coverage | — |
| `docs/plans/experiment-sarol-optimization-loop-hygiene.md` | Rules 1+2 (Rule 2 superseded for agent-only) | — |
| `docs/plans/experiment-sarol-eval-arm-isolation.md` | Rule 3 — iteration-tier wrapper script + landmark-tier Docker + IN/OUT + alternatives evaluated (NEW 2026-04-23) | — |
| `docs/plans/experiment-sarol-optimization-escalation.md` | Escalation ladder if manual stalls (trigger-based) | — |
| `docs/plans/experiment-sarol-methods-research.md` | Method menu for future sweeps | — |
| `docs/plans/canary-runbook-vertex.md` | Landmark-tier empirical canary runbook (pending VM execution) | 329 |
| `docs/plans/paper-trail-product-backlog.md` | Product backlog (off-critical-path during experiment phase) | — |

**Milestone docs** (read-only):
- `docs/plans/tier-0-resolution-2026-04-22.md` (74 lines)
- `docs/plans/experiment-april-20-findings.md`
- `docs/plans/experiment-sarol-leakage-hardening.md` (superseded)
- `docs/plans/experiment-sarol-hardening-implementation.md`
- `docs/plans/experiment-sarol-smoketest-handoff.md`

**Cross-reference map — topic → authoritative doc:**

| Topic | Primary | Secondary |
|---|---|---|
| Tiered leakage discipline | framework §2 | archive-framework §"Measurement invariants"; hygiene Rules 1+2 |
| Optimizer architecture | framework §3-5 | eval-arm-isolation §"Two-tier architecture" |
| Eval-arm isolation (Rule 3) | eval-arm-isolation | framework §4; hygiene Rule 1 |
| Measurement invariants (Tier 1/2/3) | archive-framework §"Measurement invariants and validation" | framework §7 #10 |
| Rule 1 (subagent sandboxing) | hygiene §Rule 1 | framework §3; archive-framework §D12 |
| Rule 2 (main-session blindness) / Tier 3 sealing | framework §2, §6 | hygiene §Rule 2 (historical) |
| Optimizer affordances (D34) | framework §3 | NEXT.md §5 seed-prompt deliverable; paper-writeup-items.md |
| Topology-freedom (D32) | journal 2026-04-22-topology-freedom §D32 | framework §3 |
| Proposed-but-rejected topology logging (D55) | paper-writeup-items.md §Things-to-be-honest-about | framework §3 "Topology-restructure invitation"; framework §7 #10 |
| Archive artifact schema | archive-framework §"Archive directory" | framework impl checklist |
| Variant strategy (E1/E3) | benchmark doc | journal 2026-04-22-experiment-design-e1-e4 §D50-D53 |
| Dataset extension (E3) | journal 2026-04-22-experiment-design-e1-e4 §D51 | journal 2026-04-22-e3-dataset-extension-feasibility (GREEN result) |
| Per-claim budget (D45) | journal 2026-04-22-lit-review-2 §D45 | NEXT.md Task 5 |
| Round-trip sanity canary (D46) | journal 2026-04-22-lit-review-2 §D46 | NEXT.md Task 5 |
| Benchmark-integrity integration | journal 2026-04-23-benchmark-integrity-lit-review §D54 | framework §8 Bucket 5; NEXT.md Task 5 adversarial suite |
| Two-tier eval-arm architecture | tier-0-resolution-2026-04-22 | eval-arm-isolation |
| Model pinning | archive-framework §D18 | paper-writeup-items.md §Things-to-be-honest-about |
| Memory-blind mechanism | archive-framework §Q9c | journal 2026-04-22-memblind-oauth-findings (empirical result) |
| Dispatcher-as-Python (D26) | framework §3-4 | NEXT.md Task 5 |
| Substrate choice (D48) | journal 2026-04-22-substrate-claude-code-vs-pydantic-ai | framework §8 |
| Contributions | paper-writeup-items.md §Core contributions | NEXT.md §Paper contributions pursued |
| Non-goals / deferrals | NEXT.md Tier 6 | feedback_defer_with_milestone_pin.md |
| Related work five-bucket | framework §8 | journal 2026-04-22-lit-review-2 §D41; journal 2026-04-23-benchmark-integrity §D54 |

---

## 7. Known gaps + items flagged for soundness review

Items the Explore pass surfaced as worth pressure-testing:

1. **D34 partial spec.** Full Tier-1-invariant schema for `paper-trail-v<N>.json` archive artifact still owed (framework §7 #10). Partial seed-prompt affordance catalog lives in framework §3. Risk: optimizer at Phase 3 lacks structured seed when we spin it up. Mitigation: ship full schema as part of Task 5.
2. **D37 ↔ D39 contingency.** D37 decided the paper appendix publishes framework artifacts (optimizer init prompt, schemas, canary design) not per-revision case-study prompts. But D39 (one paper vs two) remains softly open pending venue choice. If we end up with two papers (framework + case study), appendix scope needs re-deciding.
3. **Phase 4 test-unsealing protocol underspecified.** Framework §4 mentions `--confirm-unseal` tripwire; NEXT.md doesn't detail (a) who unseals, (b) how the tripwire fails loud, (c) what happens if test F1 shows a problem — paper-limitation-disclosure is the current answer but the process deserves explicit treatment.
4. **Calendar-discipline risk.** Model-pinning limitation (D18) assumes target completion "within ~2 weeks of 2026-04-21." Today is 2026-04-23 — still inside window, but this constraint is not heavily surfaced in the phase plan. Phase 3+4 execution speed matters for the limitation to hold.
5. **Topology-may-not-change evidence design.** D55 added proposed-but-rejected logging; seed-prompt "Topology-restructure invitation" is in framework §3 as working draft. If optimizer rejects the invitation at Phase 3 despite the seed-prompt language, we need a Phase-3 descope trigger (re-iterate seed prompt once) — added above but deserves separate critic attention.
6. **E3 scoring not fully resolved (Phase 4).** Four options (A subset-score / B pre-registered references / C manual-E2E / D composite). Tentative lean B. Phase 4 assumes this is resolved; may need a Phase-3-boundary decision gate.
7. **Variant B alignment-rate spot-check** (Tier 3 pin): assumed between Phase 1 and Phase 4 but not pinned to a specific phase boundary. Should probably be Phase-3-entry gate.
8. **Descope-trigger thresholds are gut-feel.** "< 30% macro-F1 at v1 smoketest" and "< 2% improvement after 5 revisions" haven't been defended against lit-review baselines. Soundness review should flag if these are loose.
9. **Open problems from framework §7 that span phases.** §7 #1 (respawn), #2 (stopping rule), #3 (dispatcher-bug mitigation) all touch Phase 3 but are spec'd only at the framework-level. Need Phase-1 build-time pinning of concrete mechanisms.
10. **9-paper pending reads.** MAPRO / MA-SAPO / MASS final read is Tier 6 pinned to "before paper submission" — but if they invalidate Claim 4 narrowing, we'd want to know pre-Phase-3, not post-Phase-5.

---

## 8. Next step — soundness review

This doc is the outline-with-pointers precursor form. The follow-up is a soundness-review agent briefed to adjudicate:
- Is the plan sound?
- What pitfalls / missing criteria / inconsistencies between phases / unstated assumptions are present?
- Where could empirical results invalidate downstream plans?

Pattern: 2026-04-22 Rule-3 critic audit on the eval-arm-isolation claim (separately briefed, pressure-test, grade, return actionable findings).

**Expected outputs:** findings integrated back into this doc + any open decisions or rescopes that surface become new Tier 1+ items in NEXT.md. Task 5 scaffolding proceeds after findings land.
