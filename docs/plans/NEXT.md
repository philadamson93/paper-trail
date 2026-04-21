# NEXT — current state and immediate next steps

**Always-current.** Edit this file when state changes. Fresh agents picking up work should read this *first*, then follow the reading path in `CLAUDE.md`.

**Last updated:** 2026-04-21

---

## Current phase

**Designing the meta-experiment infrastructure.** We are in the framework-design stage that follows the N=5 Sarol smoketest (2026-04-20) and precedes applying any prompt-level fixes. The three locked decisions from 2026-04-21:

- Q1 — monolithic version tagging (`paper-trail-v<N>`, whole-system snapshots)
- Q9 — eval arm lives in `experiments/sarol-2024/eval-harness/` with a pre-commit hook enforcing immutability during revision commits
- Q9b — eval invocation is headless Claude Code (`claude --print /sarol-eval ...`), not direct Anthropic SDK

See `docs/plans/experiment-sarol-archive-and-eval-framework.md` for the full framework + open-questions.

## What is paused, deliberately

- **INDIRECT-detection adjudicator fix.** Smoketest identified the failure mode; we drafted three prompt clauses but have not applied them. Paused so that the archive/eval framework is in place first, so v1-vs-v2 can be measured properly rather than re-running ad hoc.
- **Ramping past N=5 to larger evals.** Paused until the eval arm is built and orchestrator-runtime decisions have been moved into it.

## Immediate next steps, ordered

### 1. Lit-review pass (45 min)

**Why it must come first:** the train-and-val-over-human-revisions figure is our candidate headline contribution. Currently lit-review-gated on whether it's novel in published form. User agreed 2026-04-21 to do the lit review before starting expensive experiments ("once we start the experiment, we can't stop it").

**Scope:** full-text reads of
- DSPy / MIPROv2 (Khattab et al.)
- TextGrad (Yuksekgonul et al.)
- OPRO (Yang et al.)
- PromptBreeder (Fernando et al.)
- Reflexion + Self-Refine + any follow-ups from Shinn / Madaan lines

**Deliverables:** update `paper-writeup-items.md` §"What do we call this methodology" with specific pass/fail on each paper: does it publish the train+val-over-human-revisions figure? does it formalize multi-subagent pipeline iteration? does it argue train/test hygiene for prompt workflows? Lock-or-unlock the novelty claim.

### 2. Memory-blind invocation spike (Q9c)

**Why it's critical:** the retrospective-replay property — "eval of paper-trail-v<N> at time=T is memory-blind regardless of my memory at time=T" — is the centerpiece of the methodology contribution. If memory leaks from the planning session into headless Claude Code eval runs, the contribution is broken.

**Task:** determine how to run `claude --print /sarol-eval` with zero memory loading. Investigate in this order:
1. **Fresh working directory + minimal `.claude/` config.** Run eval from a dir that's not the paper-trail repo; put a minimal `.claude/settings.json` there; let Claude Code pick up local config and (hopefully) not inherit the planning session's memory. Candidate: `~/paper-trail-eval-workdir/` or similar; user flagged concern about filesystem bloat — size it minimally.
2. **Explicit flag.** Check Claude Code's CLI for `--no-memory` / `--clean` / `--profile <name>` options. Use `/claude-code-guide` agent or read docs.
3. **Temporary profile swap.** Rename `~/.claude/projects/<slug>/memory/` during eval, restore after.
4. **Container / fresh user.** Overkill unless (1)-(3) all leak.

**Deliverable:** documented mechanism (one-page in the archive-framework doc) + a sanity-check script that invokes paper-trail on a known claim in the memory-blind mode and confirms the response does not reflect planning-session memory content (proxy test: ask the eval-mode agent a question whose answer would be obviously memory-informed, confirm the answer is "I don't know").

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

Once tasks 1–4 are closed:
- `experiments/sarol-2024/eval-harness/` scaffolding
- Move `stage_claim.py`, `parse_verdict.py`, `record_usage.py` into it
- Author `/sarol-eval` slash command definition
- Pre-commit hook enforcing eval-harness immutability on non-eval branches
- Move orchestrator-runtime decisions (verifier sampling, retry, bounce, schema validation) into eval-harness Python
- Test on paper-trail-v1 + eval-train-10 (~$7 smoketest of the new plumbing)

### 6. First curve points

Run /sarol-eval on paper-trail-v1 at N=10 (and N=50 if N=10 looks clean). Apply INDIRECT-detection fix → tag paper-trail-v2 → rerun. Two points on the curve.

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

- **Test split sealed** at `$HOME/.paper-trail-sealed/sarol-2024-test/`. Never unseal during iteration.
- **Subagents never see gold labels or raw benchmark data.** Structural defenses in place (gold outside repo, opaque citekeys, filesystem-restriction paragraph on every dispatch). Documented in `experiment-sarol-optimization-loop-hygiene.md`.
- **Main-session (planning) test blindness.** Same doc.
- **Memory-blind retrospective eval.** Once Task 2 (the memory-blind mechanism) is built, every archived eval run must use it. No exceptions.
- **Eval arm changes force re-baselining.** Once `experiments/sarol-2024/eval-harness/` is created and first used, any commit modifying it without rerunning v1 invalidates the curve.
- **Model pinning.** Every subagent dispatch uses `model: "opus"`. Orchestrator invoked with `claude --model opus --print ...`. Each archived `summary.json` records the Claude Code version at run time as proxy for alias-drift detection. Mixed-model runs (opus/sonnet/haiku mix) are reserved for a named ablation branch, never the main curve.
- **Calendar discipline for model-drift mitigation.** Target completion of all train + dev + test runs within ~2 weeks of 2026-04-21. Beyond that window, the risk of a silent `opus` alias drift grows; we either compress the schedule, re-baseline if we cross a version boundary, or accept the limitation explicitly.
- **Measurement invariants are validated at every run.** Three-tier classification (invariants / logged / free) is defined in `experiment-sarol-archive-and-eval-framework.md` §"Measurement invariants and validation." Invariant violations invalidate the run. Tier 1 includes: prompt file hashes, eval-arm hashes, model aliases, subset manifest hash, benchmark + gold data hashes, tool permissions, MCP servers connected, env vars, memory-blind status, rubric variant. Validator (`validate_run.py`) is built as part of Task 5 (eval arm build).

## Paper contributions pursued (short list — full discussion in paper-writeup-items.md)

1. First 9-way Sarol baseline.
2. INDIRECT-detection failure mode, named and remedied.
3. Hygiene principle for agentic-pipeline development (Rule 1 subagent sandboxing + Rule 2 main-session test blindness + time-evolution memory framing).
4. Train+val curve over human revisions as headline figure *(lit-review-gated; Task 1 above)*.
5. Severity-under-commitment pattern (s4, tentative).
6. Cost-per-claim practitioner numbers.

## Reading path for a fresh agent

1. This file (NEXT.md).
2. `CLAUDE.md` — repo orientation and conventions.
3. `docs/plans/experiment-sarol-archive-and-eval-framework.md` — the framework we're implementing.
4. `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — the hygiene rules.
5. `docs/plans/experiment-april-20-findings.md` — the smoketest findings that triggered all this.
6. `docs/plans/paper-writeup-items.md` — paper framing.
7. Most recent entry in `docs/journal/` — what was discussed and decided in the last working session.
