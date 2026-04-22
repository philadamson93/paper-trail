# NEXT — current state and immediate next steps

**Always-current.** Edit this file when state changes. Fresh agents picking up work should read this *first*, then follow the reading path in `CLAUDE.md`.

**Last updated:** 2026-04-21

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
- Move orchestrator-runtime decisions (verifier sampling, retry, bounce, schema validation) into eval-harness Python
- **3-seed minimum at v1 landmark** — non-negotiable per lit-review convergent signal (MIPROv2, TextGrad, BetterTogether, OPRO, MASS).
- **Train dispatcher emits raw per-subagent traces + macro-F1 + per-class F1** (topology-agnostic; no pre-computed per-stage sub-scores — those are the optimizer's job via its own mutable trace-aware metric). Per `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D36: the DSPy-pattern sub-metric (extractor recall, adjudicator conditional-F1, verifier flip rate, etc.) is an optimizer-owned artifact seeded at v1, not frozen eval-arm infrastructure — the optimizer rewrites it when paper-trail-v<N>'s topology evolves.
- **`paper-trail-v<N>.json` archive artifact** — emitted per tagged revision alongside the git tag. Contains {prompt hashes, signature specs, rubric examples, eval-arm tag, dispatcher versions, model aliases, settings.json hash, MCP config hash, handoff-doc schema version}.
- Test on paper-trail-v1 + eval-train-10 (~$7 smoketest of the new plumbing; validates that invariant-check machinery fires correctly)

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

### 7. Backlog (non-blocking, explicit pins)

**2026-04-21 additions — not starting now, not forgotten:**

- **Zero-shot single-prompt baseline on Variant A** (mandatory paper baseline row; cf. TextGrad Table 3). Cost: $5-30. **Pin:** before paper submission, not before Task 5. Purpose: apples-to-apples comparison row, not a strategic pivot trigger.
- **Variant D (raw source papers + independent claim extraction).** Start from 100 citing papers' raw text, run paper-trail claim-extraction independently, match to Sarol annotations, report coverage + conditional F1. Uses Sarol as a *proxy measurement* of full-system behavior on raw inputs. **Pin:** consider after Variant C primary results land; possibly a follow-up experiment or second-paper.
- **Clarifications list** (Agent owes Human). Fixed-topology-by-design, DSPy trace-aware metric, MA-SAPO App H / MAPRO App D, ProTeGi gradient template, PromptBreeder mutation-operator menu, subagent revision order, bandit candidate selection. **Pin:** next working session.
- **Agent-only N=10 de-risk smoketest design.** Does the optimizer agent move macro-F1 in the right direction autonomously? **Pin:** after Task 5 eval-arm scaffold is in place.
- **Memory-blind canary sanity-check (Q9c).** Still ON HOLD. **Pin:** before Task 5 eval-arm build begins.
- **Open problems from the framework doc §7.** Optimizer self-respawn protocol (handoff-doc schema, respawn criterion, budget), stopping rule, per-revision rationale capture, dispatcher-bug mitigation testing, optimizer initial-configuration schema (partial spec landed 2026-04-22 — affordance catalog, performance-not-cost philosophy, fight-Python-default guidance all in framework §3 "Optimizer agent initial configuration"; machine-checkable schema for the `paper-trail-v<N>.json` archive still owed). **Pin:** resolved during Task 5 implementation; spec'd before implementation. See `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` for the partial-spec decision log.

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

## Reading path for a fresh agent

1. This file (NEXT.md).
2. `CLAUDE.md` — repo orientation and conventions.
3. `docs/plans/experiment-sarol-archive-and-eval-framework.md` — the framework we're implementing.
4. `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — the hygiene rules.
5. `docs/plans/experiment-april-20-findings.md` — the smoketest findings that triggered all this.
6. `docs/plans/paper-writeup-items.md` — paper framing.
7. Most recent entry in `docs/journal/` — what was discussed and decided in the last working session.
