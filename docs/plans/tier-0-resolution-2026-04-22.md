# Tier 0 resolution milestone (2026-04-22 / 2026-04-23)

**Read-only milestone doc.** Captures the full resolution narrative for NEXT.md Tier 0 (three gates blocking the Task 5 eval-arm build) produced across two working sessions on 2026-04-22 and 2026-04-23. Extracted from NEXT.md's Tier 0 status block 2026-04-23 per the doc-hygiene split so NEXT.md can focus on current + next-up work rather than carrying the resolution history.

**Linked artifacts** (authoritative current-state docs, not superseded by this milestone):
- `experiment-sarol-eval-arm-isolation.md` — current canonical iteration-tier and landmark-tier invocation shapes (wrapper script + Docker) with IN/OUT formalization and residual investigation items.
- `experiment-sarol-optimization-loop-hygiene.md` — Rules 1 (subagent sandboxing) and 2 (main-session test blindness), still authoritative.
- `canary-runbook-vertex.md` — landmark-tier Vertex canary execution runbook (pending execution).
- `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md` — Gate 1 empirical report.
- `docs/journal/2026-04-22-memblind-oauth-findings.md` — Gate 2+3 empirical record + critic audit addendum.
- `docs/journal/2026-04-23-benchmark-integrity-lit-review.md` — Berkeley Agent-Eval Checklist + Zhu et al. ABC integration and creative-defenses brainstorm.

---

## Status 2026-04-22 / 2026-04-23 (frozen)

- **Gate 1 (E3 dataset-extension feasibility):** ✅ **RESOLVED GREEN** with yellow caveat on PMC PDF fetch. See `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md`. Key numbers verified from disk: 70 Train cited-paper buckets, 2,141 annotation files (1:1 with claims-train.jsonl rows), 1,628 unique citing PMC IDs in Train. Citing-paper identity lives in annotation filenames `citations/<bucket>_PMC<cited>/<citing_PMC>_<N>.json`; reference token pre-extracted in each JSON's `marker_span.text`. ~1,900 unique citing PDFs to fetch across Train+Dev (Test deferred to unseal-time). Estimated ~1.5 engineering days for the full extension pipeline. No reason to descope E3 to E3-lite or swap headline to E1.
- **Gate 2 (memory-blind invocation) + Gate 3 (Task-tool availability):** ✅ **ITERATION TIER RESOLVED LOCALLY 2026-04-22** under OAuth via empirical canaries; landmark tier still backlogged pending Vertex VM execution of `canary-runbook-vertex.md`. Full empirical record in `docs/journal/2026-04-22-memblind-oauth-findings.md`; architecture now lives in `experiment-sarol-eval-arm-isolation.md` (split from `optimization-loop-hygiene.md` §Rule 3 on 2026-04-23). Key findings:
  - `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` under OAuth suppresses auto-memory and all CLAUDE.md scopes (user, project, local) — verified with canaries. These env vars are documented at `code.claude.com/docs/en/env-vars` but don't appear in `claude --help`.
  - Env vars propagate transitively through Agent-tool subagent spawns — a subagent under a memblind main session is also memblind without extra plumbing. Verified with `memory-probe` inline subagent canary.
  - `--tools default` + `--agents '<json>'` dispatcher mechanics work under OAuth — Agent tool present in default toolset, custom subagents load inline, functional spawn returns verbatim. No `--bare` required for tool/agent mechanics.
  - `CLAUDE_CODE_SIMPLE=1` env var is functionally equivalent to `--bare` (also refuses OAuth).
  - `CLAUDE_CONFIG_DIR=/tmp/fresh/` override breaks OAuth on macOS — keychain entries appear keyed to the default config dir.
  - `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) is **subscription-scoped, not API-billed**. Designed for CI/scripts. Not readable under `--bare` but works under non-bare env-var auth. Combination with `CLAUDE_CONFIG_DIR` is the full-isolation OAuth-subscription path, empirically verified 2026-04-22.
- **Additional empirical tests 2026-04-22 (subscription token path):** Human generated a `CLAUDE_CODE_OAUTH_TOKEN` via `claude setup-token` and shared it back; four follow-up tests (1, 2a, 2b, 3, 4) verified the full iteration-tier stack. Key results in `docs/journal/2026-04-22-memblind-oauth-findings.md` §5.1:
  - Subscription-token auth works with fresh `CLAUDE_CONFIG_DIR` override.
  - `CLAUDE_CONFIG_DIR=/tmp/fresh/` alone does not blind user CLAUDE.md (`$HOME/.claude/CLAUDE.md` is hardcoded against `$HOME`, not scoped to the config dir) — you still need `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` for that.
  - Full stack (token + both disable env vars + fresh config dir) blinds memory, user CLAUDE.md, project CLAUDE.md, user hooks/skills/plugins (structurally), keeps Agent tool + custom subagents working, and propagates isolation transitively to spawned subagents. **Functionally equivalent to `--bare` for this project's IN/OUT boundary under subscription auth** (softened after the critic audit — see next bullet).
- **Critic audit 2026-04-22 softened the "fully equivalent to `--bare`" claim.** A separately-briefed subagent pressure-tested the iteration-tier isolation claim and identified six gaps that survive the committed stack. Three landmark-tier-blocking (dynamic-system-prompt leakage, Claude Code binary version drift, subagent-side persistent memory); two Task-5-scaffolding-blocking (`.claude/commands/` resolution under fresh `CLAUDE_CONFIG_DIR`, settings-merge fail-closed canary); others nice-to-have. Verdict: "defensible but not in the strong form — fix before landmark tagging; iteration-tier Task-5 scaffolding can proceed today." Doc amendments landed 2026-04-22 in `experiment-sarol-optimization-loop-hygiene.md` §Rule 3 (later split to `experiment-sarol-eval-arm-isolation.md` on 2026-04-23) and mirrored in `experiment-sarol-archive-and-eval-framework.md` §Q9c. Full audit report archived in `docs/journal/2026-04-22-memblind-oauth-findings.md` §8.
- **2026-04-23 benchmark-integrity lit-review.** Human pointed to Berkeley RDI's "How We Broke Top AI Agent Benchmarks" (Wang et al. 2026); follow-up arxiv search surfaced Zhu et al. 2025 (arxiv 2507.02825, "Establishing Best Practices for Building Rigorous Agentic Benchmarks" — the canonical academic reference, introduces the Agentic Benchmark Checklist / ABC) and Fan et al. 2025 (arxiv 2512.12806, fault-tolerant transactional-FS sandboxing). Full synthesis in `docs/journal/2026-04-23-benchmark-integrity-lit-review.md`. Their evaluator-side integrity recommendations added to the Task-5 queue: adversarial-agent smoketest suite (null / random / injection / tamper), scorer adversarial audit, LLM-judge input-sanitization audit, E3-dispatcher crashed-task-semantics spec. Our substrate-level isolation contribution positioned as extension of their framework; citations added to framework doc §8 as a new Bucket 5.
- **2026-04-23 creative-defenses brainstorm + architecture revision.** Human: "I want to avoid any 'why didn't he just...' criticism." Ten-mechanism evaluation catalog landed in `experiment-sarol-eval-arm-isolation.md` §Structural-defenses; wrapper script (`scripts/run-eval.sh`) adopted as canonical operator interface (addresses the "why didn't he just use a script?" case pre-emptively); Docker with pinned Claude Code binary adopted for landmark tier (closes the binary-drift gap); `env -i` + clean cwd + `--add-dir` added to canonical iteration-tier shape (verified 2026-04-23 that clean cwd kills git-state leakage at source).

## Two-tier eval-arm architecture (final form post-critic + post-lit-review)

- **Iteration tier** (local, subscription token): canonical invocation is `scripts/run-eval.sh --tier iteration --version v<N> --claim <id>`. The wrapper internally applies `env -i` + pinned `HOME`/`PATH`/`LANG`/`TZ` + `CLAUDE_CODE_OAUTH_TOKEN` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` + `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` + fresh per-uuid `CLAUDE_CONFIG_DIR` + clean cwd + `--add-dir <repo>` + the standard `--tools default --agents '<json>' --settings <tag-scoped> --mcp-config <tag-scoped> --strict-mcp-config --no-session-persistence --exclude-dynamic-system-prompt-sections /sarol-eval-item ...` combination. Full spec in `experiment-sarol-eval-arm-isolation.md` §Mechanisms.
- **Landmark tier** (Vertex VM with Docker, paper-reportable): canonical invocation is `docker run --rm ... paper-trail-eval:v<N> /repo/scripts/run-eval.sh --tier landmark --version v<N> --claim <id>`. The Docker image `paper-trail-eval:v<N>` is built from a committed `Dockerfile` at the tag, pinning Claude Code binary via `npm install -g @anthropic-ai/claude-code@<specific-version>`. Full spec in `experiment-sarol-eval-arm-isolation.md` §Mechanisms.

## Meta-task for the next session (unchanged from 2026-04-23 commit)

1. Proceed with Task 5 eval-arm iteration-tier scaffolding using the canonical wrapper-script interface. Do NOT wait for the Vertex runbook to run.
2. Create `experiments/sarol-2024/eval-harness/.env.example` template documenting the env vars (commit template; actual `.env` is gitignored).
3. Run the nine blocking-priority canaries early in Task 5 scaffolding (five critic-flagged + four benchmark-integrity adversarial agents); full specs in `experiment-sarol-eval-arm-isolation.md` §Residual-investigation-items.
4. Add Claude Code binary version to `paper-trail-v<N>.json` archive artifact schema (new invariant field).
5. When convenient, execute the Vertex runbook (`canary-runbook-vertex.md`) to empirically validate landmark-tier before the first `paper-trail-v<N>` tag cut producing paper-reportable numbers.

---

## Original gate descriptions (preserved for history, superseded by the status block above)

**Dependency note at time of framing (2026-04-22):** Gate 1 (dataset-extension feasibility) blocks the E3 dispatcher spec; Gates 2 & 3 (the two substrate canaries) block the `claude --bare --print` invocation architecture. If any of the three fails, re-scope the downstream plan before continuing.

### Gate 1 — E3 dataset-extension feasibility spike (top-priority task, 2026-04-22 D51)

**Why this matters:** E3 (the headline experiment; fetch-through-verdict with citing-PDF + reference-token + claim input) requires per-claim records of shape `(citing_sentence, claim_text, reference_token, citing_paper_PDF_path)`. Sarol's existing annotations give us (citing_sentence, pre-staged cited chunks, gold verdict) keyed implicitly by citing paper. We need to derive the extended records before the E3 dispatcher can be built or the curve runs can start. If the derivation turns out to be harder than estimated, E3 scope may need to shrink (e.g., drop phase 2 bib resolution and pre-resolve references to canonical IDs, making it an E3-lite of phases 3-5 instead of 2-5) or we swap primary experiment back to E1 (the verdict-only experiment) and treat E3 as landmark-only.

**Resolution 2026-04-22:** GREEN. See `docs/journal/2026-04-22-e3-dataset-extension-feasibility.md`.

### Gate 2 — Q9c memory-blind canary (the test that confirms `--bare` suppresses memory)

Plant a distinctive memory entry in the project's memory directory, invoke `claude --bare --print` on a probe question designed to elicit the canary memory, confirm memory doesn't leak. If `--bare` suppresses → mark Q9c RESOLVED → unblock Task 5 (the eval-arm build). If it leaks → document failure mode, move to fallback options.

**Source:** `experiment-sarol-archive-and-eval-framework.md` §Q9c (test design). Est: 15 min. Original status: **ON HOLD since 2026-04-21.**

**Resolution 2026-04-22:** reframed to iteration-tier (local, OAuth subscription) via `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` env vars (no `--bare` required under OAuth); landmark tier retains `--bare` on Vertex / API key. Empirical verification in `docs/journal/2026-04-22-memblind-oauth-findings.md`.

### Gate 3 — D44 `--bare` + Agent-tool compatibility canary (the test that confirms subprocess-launched Claude can spawn subagents)

Dispatch a trivial slash command that spawns one subagent; invoke via `claude --bare --print`; verify the subagent ran (i.e., Agent tool is preserved in `--bare` mode). If yes → dispatcher architecture (Python subprocess launching fresh Claude process with paper-trail subagents) is validated. If no → compose with `--allowedTools Agent` and re-test; if still blocked, re-examine the depth-2 cap implications.

**Source:** `agentic-pipeline-optimization-framework.md` §7 open problem #11; `docs/journal/2026-04-22-lit-review-2-competitor-landscape.md` D44. Est: 15 min. Original status: pending.

**Resolution 2026-04-22:** resolved via docs sweep — `--tools default` enables Task under `--bare`; `--agents '<json>'` loads custom subagents under `--bare`. Empirically verified under non-bare OAuth (Agent tool present in default toolset; functional spawn works with inline `--agents` JSON). Empirical verification under `--bare` on Vertex backlogged until `canary-runbook-vertex.md` runs.

**Original meta-task for next session (2026-04-22 pre-resolution):** *before starting any downstream work, open this NEXT.md, run through the three Tier 0 gates, report status of each, then reassess Tier 1+ priorities based on what Tier 0 findings say about E3 feasibility and dispatcher architecture.* All three gates are now resolved (iteration-tier) or have a committed runbook (landmark-tier).
