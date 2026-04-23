# NEXT — current state and immediate next steps

**Always-current.** Edit this file when state changes. Fresh agents picking up work should read this *first*, then follow the reading path in `CLAUDE.md`.

**Last updated:** 2026-04-22

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
- **Dispatcher invocation shape (new 2026-04-22 from CLI-ref docs sweep; amended 2026-04-23 post-critic + benchmark-integrity lit-review):** every subprocess invocation is the committed wrapper script `scripts/run-eval.sh --tier {iteration|landmark} --version v<N> --claim <id>`. The script internally applies: `env -i` + pinned `LANG`/`TZ`/`PATH`, `CLAUDE_CODE_OAUTH_TOKEN` (iteration) or Vertex GCP creds (landmark), `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, fresh-per-invocation `CLAUDE_CONFIG_DIR=/tmp/pt-eval-cfg-$uuid/`, clean cwd at `/tmp/pt-eval-wd-$uuid/`, `--add-dir $REPO`, `--tools default`, `--agents '<json>'`, `--settings <tag-scoped>`, `--mcp-config <tag-scoped> --strict-mcp-config`, `--no-session-persistence`, `--exclude-dynamic-system-prompt-sections`, `/sarol-eval-item ...`. Each piece tied to a specific leakage vector (full table in `optimization-loop-hygiene.md` §Rule 3). Wrapper-script-as-canonical-interface addresses "why didn't he just use a script?" criticism pre-emptively and commits the invocation shape as a reviewable artifact.
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

#### TIER 0 — Immediate gates (block Task 5 eval-arm build; all three run in parallel)

**Status 2026-04-22:**
- **Gate 1 (E3 dataset-extension feasibility):** ✅ **RESOLVED GREEN** with yellow caveat on PMC PDF fetch. See `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md`. Key numbers verified from disk: 70 Train cited-paper buckets, 2,141 annotation files (1:1 with claims-train.jsonl rows), 1,628 unique citing PMC IDs in Train. Citing-paper identity lives in annotation filenames `citations/<bucket>_PMC<cited>/<citing_PMC>_<N>.json`; reference token pre-extracted in each JSON's `marker_span.text`. ~1,900 unique citing PDFs to fetch across Train+Dev (Test deferred to unseal-time). Estimated ~1.5 engineering days for the full extension pipeline. No reason to descope E3 to E3-lite or swap headline to E1.
- **Gate 2 (memory-blind invocation) + Gate 3 (Task-tool availability):** ✅ **ITERATION TIER RESOLVED LOCALLY 2026-04-22** under OAuth via empirical canaries; landmark tier still backlogged pending Vertex VM execution of `canary-runbook-vertex.md`. Full empirical record in `docs/journal/2026-04-22-memblind-oauth-findings.md`; architecture reframe in `experiment-sarol-archive-and-eval-framework.md` §Q9c. Key findings:
  - `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` under OAuth suppresses auto-memory and all CLAUDE.md scopes (user, project, local) — verified with canaries. These env vars are documented at `code.claude.com/docs/en/env-vars` but don't appear in `claude --help`.
  - Env vars propagate transitively through Agent-tool subagent spawns — a subagent under a memblind main session is also memblind without extra plumbing. Verified with `memory-probe` inline subagent canary.
  - `--tools default` + `--agents '<json>'` dispatcher mechanics work under OAuth — Agent tool present in default toolset, custom subagents load inline, functional spawn returns verbatim. No `--bare` required for tool/agent mechanics.
  - `CLAUDE_CODE_SIMPLE=1` env var is functionally equivalent to `--bare` (also refuses OAuth).
  - `CLAUDE_CONFIG_DIR=/tmp/fresh/` override breaks OAuth on macOS — keychain entries appear keyed to the default config dir.
  - `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) is **subscription-scoped, not API-billed**. Designed for CI/scripts. Not readable under `--bare` but works under non-bare env-var auth. Combination with `CLAUDE_CONFIG_DIR` is the most promising full-isolation OAuth-subscription path — flagged for empirical verification next.
- **Additional empirical tests in the same session (subscription token path):** Human generated a `CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token` and shared it back; four follow-up tests (1, 2a, 2b, 3, 4) verified the full iteration-tier stack. Key results in `docs/journal/2026-04-22-memblind-oauth-findings.md` §5.1:
  - Subscription-token auth works with fresh `CLAUDE_CONFIG_DIR` override (overcomes the Test 6 result where `CLAUDE_CONFIG_DIR` alone broke keychain OAuth).
  - `CLAUDE_CONFIG_DIR=/tmp/fresh/` alone does not blind user CLAUDE.md (`$HOME/.claude/CLAUDE.md` is hardcoded against `$HOME`, not scoped to the config dir) — you still need `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` for that.
  - Full stack (token + both disable env vars + fresh config dir) blinds memory, user CLAUDE.md, project CLAUDE.md, user hooks/skills/plugins (structurally), keeps Agent tool + custom subagents working, and propagates isolation transitively to spawned subagents. **Functionally equivalent to `--bare` for this project's IN/OUT boundary — but under subscription auth.**
- **Critic audit (2026-04-22 same-session) softened the "fully equivalent to `--bare`" claim.** A separately-briefed subagent pressure-tested the iteration-tier isolation claim and identified six gaps that survive the committed stack. Three are landmark-tier-blocking (dynamic-system-prompt leakage, Claude Code binary version drift, subagent-side persistent memory); two are Task-5-scaffolding-blocking (`.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR`, settings-merge fail-closed canary); others are nice-to-have. Critic verdict: "defensible but not in the strong form — fix before landmark tagging; iteration-tier Task-5 scaffolding can proceed today." Doc amendments landed 2026-04-22 in `experiment-sarol-optimization-loop-hygiene.md` §Rule 3 (OUT-of-system table expanded; "Binary version invariant" subsection added; canonical invocation shapes add `--exclude-dynamic-system-prompt-sections` + `--no-session-persistence`) and mirrored in `experiment-sarol-archive-and-eval-framework.md` §Q9c. Full audit report archived in `docs/journal/2026-04-22-memblind-oauth-findings.md` §8.
- **Two-tier eval-arm architecture (revised post-critic 2026-04-22):**
  - **Iteration tier** (local, subscription token): **canonical shape is** `CLAUDE_CODE_OAUTH_TOKEN=$TOKEN CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CONFIG_DIR=/tmp/paper-trail-eval-<uuid>/ claude --print --no-session-persistence --exclude-dynamic-system-prompt-sections --tools default --agents '<json>' --settings <tag-scoped> --mcp-config <tag-scoped> --strict-mcp-config /sarol-eval-item ...`. Token in gitignored `.env`. Functionally equivalent to `--bare` for the six documented auto-discovery sources; dynamic-system-prompt and session-persistence covered by the two additional flags. **Unblocks Task 5 scaffolding — begin iteration-tier build now.**
  - **Landmark tier** (Vertex or ANTHROPIC_API_KEY, `--bare`): same flags as iteration-tier PLUS `--bare`. Binary version pinned via `npm install -g @anthropic-ai/claude-code@<pin>` on the Vertex VM; `claude --version` captured in `paper-trail-v<N>.json` archive metadata. Runbook at `canary-runbook-vertex.md` still applies; add the two new flags to the runbook's invocation pattern (see revised §Q9c). Also records binary version in archive.
- **Meta-task for the next session:**
  1. Proceed with Task 5 eval-arm iteration-tier scaffolding using the canonical subscription-token shape above. Do NOT wait for the Vertex runbook to run.
  2. Create `experiments/sarol-2024/eval-harness/.env.example` template alongside the dispatcher scripts documenting the env vars (commit template; actual `.env` is gitignored).
  3. Run the five blocking-priority critic-flagged canaries early in Task 5 scaffolding: (a) dynamic-system-prompt probe confirming `--exclude-dynamic-system-prompt-sections` moves cwd/git/env/memory-path out of context; (b) subagent-side persistent memory canary; (c) `.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR`; (d) settings-merge fail-closed negative test; (e) Claude Code binary version capture + pin convention. Each is short; full specs in `optimization-loop-hygiene.md` §Rule 3 residual items and in the journal §8.
  4. Add Claude Code binary version to `paper-trail-v<N>.json` archive artifact schema (new invariant field).
  5. When convenient, execute the Vertex runbook to empirically validate landmark-tier before the first `paper-trail-v<N>` tag cut producing paper-reportable numbers.

**Legacy gate descriptions below (preserved for history; superseded by the status block above where applicable).**

**Dependency note:** Gate 1 (dataset-extension feasibility) blocks the E3 dispatcher spec; Gates 2 & 3 (the two substrate canaries) block the `claude --bare --print` invocation architecture. If any of the three fails, re-scope the downstream plan before continuing.

##### Gate 1 — E3 dataset-extension feasibility spike (the new top-priority task, 2026-04-22 D51)

**Why this matters:** E3 (the headline experiment; fetch-through-verdict with citing-PDF + reference-token + claim input) requires per-claim records of shape `(citing_sentence, claim_text, reference_token, citing_paper_PDF_path)`. Sarol's existing annotations give us (citing_sentence, pre-staged cited chunks, gold verdict) keyed implicitly by citing paper. We need to derive the extended records before the E3 dispatcher can be built or the curve runs can start. If the derivation turns out to be harder than estimated, E3 scope may need to shrink (e.g., drop phase 2 bib resolution and pre-resolve references to canonical IDs, making it an E3-lite of phases 3-5 instead of 2-5) or we swap primary experiment back to E1 (the verdict-only experiment) and treat E3 as landmark-only.

**Concrete steps (fresh-session-executable):**

1. **Read the canonical setup:** `docs/plans/experiment-sarol-benchmark.md` §"Experiment design (E1-E4, canonical 2026-04-22)" and its subsection "E3 dataset-extension work" for the target shape. Also read `docs/journal/2026-04-22-experiment-design-e1-e4.md` D50/D51 for the decision rationale.
2. **Inventory what Sarol provides on disk:** check `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/` and the `annotations/` subdirectory. Confirm: (a) flat JSONL claim records exist with citing sentence + cited chunks; (b) `annotations/{Train,Dev,Test}/references/` directories with cited-paper full texts (filename pattern `NNN_PMC<ID>.txt` indicating PMC IDs are derivable); (c) paragraph-level structure in `references_paragraph.json`. Check for the **citing-paper-identity link** — which citing paper each claim came from. This is the first critical unknown.
3. **Pick one representative claim from Sarol-train.** Walk the full extension pipeline manually for this one claim:
   - Identify its citing paper (where did this claim come from? Does Sarol have this link in the annotation schema, or do we have to reverse-engineer it from the pre-staged chunks?)
   - Find the reference token — the `\cite{key}` or `[N]` citation marker within the citing paper that points to the cited paper. This requires the citing paper's text or PDF.
   - Locate or fetch the citing paper's PDF. Sarol's 100 citing papers should be listed somewhere; if not, we may have to fetch them from PMC / DOI resolvers one at a time.
   - Package as `(citing_sentence, claim_text, reference_token, citing_paper_PDF_path)` — verify the shape holds.
4. **If step 3 works cleanly for one claim:** try ~5 more claims from different citing papers to check for edge cases (missing citing-paper link, ambiguous reference token, paywalled citing paper, reference-list format variants).
5. **Estimate total effort to extend for all ~3K Sarol claims** based on what you learned in steps 3-4. Expected outcomes:
   - **Green:** 1 day of scripting + some manual spot-checks. Proceed with E3 as planned; add dataset-extension to Task 5 deliverables.
   - **Yellow:** 2-3 days with edge cases. Proceed but flag the engineering cost in the paper methods section as non-trivial.
   - **Red:** > 1 week OR hard unresolved ambiguities (e.g., Sarol annotations don't reliably encode citing-paper-identity). Descope E3 to E3-lite (phases 3-5 with pre-resolved PMC IDs instead of reference tokens, skipping phase 2 bib resolution). If even E3-lite is blocked, swap headline back to E1 (phase 5 only) and treat fetch-through-verdict work as future-paper.
6. **Produce a short report** to land in a new journal entry `docs/journal/YYYY-MM-DD-e3-dataset-extension-feasibility.md`: which annotation fields link claims to citing papers, how references are keyed in the citing-paper text, list of edge cases, effort estimate, recommended disposition (green/yellow/red).

**Est: 1-2 hours hands-on + 30 min report.** Blocks the E3 dispatcher spec in Task 5 (the eval-arm build).

##### Gate 2 — Q9c memory-blind canary (the test that confirms `--bare` suppresses memory)

Plant a distinctive memory entry in the project's memory directory, invoke `claude --bare --print` on a probe question designed to elicit the canary memory, confirm memory doesn't leak. If `--bare` suppresses → mark Q9c (the memory-blind mechanism question) RESOLVED → unblock Task 5 (the eval-arm build). If it leaks → document failure mode, move to fallback options in `experiment-sarol-archive-and-eval-framework.md` §Q9c.

**Source:** `experiment-sarol-archive-and-eval-framework.md` §Q9c (test design is written end-to-end there); `docs/journal/2026-04-21-lit-review-prompt-optimization.md` for context. Est: 15 min. Status: **ON HOLD since 2026-04-21.**

##### Gate 3 — D44 `--bare` + Agent-tool compatibility canary (the test that confirms subprocess-launched Claude can spawn subagents)

Dispatch a trivial slash command that spawns one subagent; invoke via `claude --bare --print`; verify the subagent ran (i.e., Agent tool is preserved in `--bare` mode). If yes → dispatcher architecture (Python subprocess launching fresh Claude process with paper-trail subagents) is validated. If no → compose with `--allowedTools Agent` and re-test; if still blocked, re-examine the depth-2 cap implications.

**Source:** `agentic-pipeline-optimization-framework.md` §7 open problem #11; `docs/journal/2026-04-22-lit-review-2-competitor-landscape.md` D44. Est: 15 min. Status: pending; can run in same session as Q9c.

**Meta-task for next session — triage and execute Tier 0:** before starting any downstream work, open this NEXT.md, run through the three Tier 0 gates, report status of each, then reassess Tier 1+ priorities based on what Tier 0 findings say about E3 feasibility and dispatcher architecture.

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
- **§7 #10 Optimizer agent initial-configuration schema.** Partial spec landed 2026-04-22 (D34: affordance catalog, performance-not-cost philosophy, fight-Python-default, autoresearch direct-lifts, ProTeGi seeded pattern, declined-PromptBreeder). Machine-checkable schema for the `paper-trail-v<N>.json` archive artifact still owed.
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
- **"Evaluated alternatives" methods-section table (new 2026-04-23):** explicit table documenting 10 structural-defense mechanisms we evaluated (env -i, clean cwd + --add-dir, git worktree, wrapper script, APFS snapshot, sandbox-exec, separate OS user, chmod, Docker, ephemeral VM) with adoption-decision column. Pre-empts "why didn't he just..." reviewer criticism. Source table in `optimization-loop-hygiene.md` §Rule 3 "Structural defenses beyond native Claude Code flags (alternatives evaluated)" subsection.
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
