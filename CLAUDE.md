# paper-trail — orientation for Claude Code sessions

Fresh-agent crib sheet. Read before making structural or doc changes.

## What paper-trail is

A citation-integrity agent that audits the references in a manuscript. Ships as the `/paper-trail` slash command (plus sister commands `/ground-claim`, `/fetch-paper`, `/verify-bib`). The shipped product is the agent + its prompts + its orchestration — **not** any given Claude Code session.

## Where things live

- `docs/plans/` — stable reference plans. Long-lived; edit in place when decisions change. One file per major topic.
- `docs/journal/YYYY-MM-DD-<topic>.md` — per-day-per-topic decision log with attribution. Append-only in practice; captures *who* raised *what* and *why*. Filename prefix is ISO date + short topic slug so files grep chronologically and by topic. No subfolders.
- `experiments/sarol-2024/` — the Sarol benchmark experiment subtree. Runbook, prompts, specs, scripts.
- `experiments/sarol-2024/eval-harness/` — (planned, not yet created) frozen eval arm, isolated from revision commits by a pre-commit hook. Open decision Q9 in `experiment-sarol-archive-and-eval-framework.md`.
- `experiments/sarol-2024/archive/paper-trail-v<N>/` — (planned) per-version eval output; the archived *model* itself is the git tag.
- `.claude/prompts/`, `.claude/specs/` — production paper-trail prompts and rubric. **Not experiment-variant.** Sarol variants live under `experiments/sarol-2024/prompts/` and `experiments/sarol-2024/specs/`. Don't cross-contaminate.

## Documentation conventions

**Plain language.** Avoid acronyms unless expanded on first use, and prefer descriptive words over jargon. Historical example: an earlier draft of the archive-framework doc used "SUT" (system under test) throughout; Human objected twice. Retired.

**Attribution in decision rationale.** When a plan doc or journal entry records a decision whose rationale is interesting to retrospect on, mark inline with **Human:** and **Agent:** prefixes. Even when one party was wrong and pushed back by the other, preserve that — we're writing for the paper's human-value-in-agentic-collaboration discussion.

**Modularity over monolith.** One topic per file. Long monolithic docs are hard to navigate later; small per-topic files are grep-friendly. If a doc gets past ~400 lines of prose, split it.

**When to write a journal entry.** At the end of any substantive discussion that produced decisions or open questions. Especially for experiment-planning / paper-framing discussions where the who-said-what is the actual artifact.

## Working pace

**One thing at a time, conceptually.** When a session surfaces multiple threads — a primary task plus optional secondaries, or a main question plus incidental findings — complete the primary cleanly before opening the secondary, even if they're independently safe and the secondary is tempting. "One thing" is a conceptual scope, not literally one tool call: running multiple parallel subagents to execute one lit-review pass counts as one thing; adding a spike + a save-state + a CLAUDE.md edit + a memory write-out for one user request is still one thing. What to avoid is pursuing an independent second thread "because we can" — that muddies the primary's checkpoint with state from both and makes the next Human review harder.

Human raised 2026-04-21. Applies to this project and generally.

## Hygiene rules (Sarol experiment, and general pattern for any labeled-benchmark experiment)

See `docs/plans/experiment-sarol-optimization-loop-hygiene.md` for the formal treatment. Short version:

- **Rule 1 — Subagent sandboxing.** Subagents (extractor, adjudicator, verifier) cannot physically reach gold labels or raw benchmark data. Structural defenses: gold + benchmark outside the repo tree (`$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR`); opaque `ref_<6hex>` citekeys; filesystem-restriction paragraph on every dispatch; scrubbed `staging_info.json`.
- **Rule 2 — Main-session test blindness.** The main planning session (this one) is policy-gated to never see test labels. The test split of any benchmark used for reporting is physically moved out of its expected directory during iteration and only unsealed for a single final evaluation. Current seal: `$HOME/.paper-trail-sealed/sarol-2024-test/` (Sarol 2026-04-21).
- **Time-evolution memory framing.** My memory improving over sessions is part of the optimization process. The constraint is that retrospective eval of `paper-trail-v<N>` at time=T must be memory-blind regardless of my memory at time=T — implemented by encoding all orchestrator-runtime decisions in static eval-arm Python (no runtime judgment during evals).

## Commit style

Short, single-sentence commit messages. No AI attribution trailers. See memory `feedback_commit_style.md`.

## Where the user's global memory lives

`/Users/pmayankees/.claude/projects/-Users-pmayankees-Documents-Misc-Projects-paper-trail/memory/`. Indexed by `MEMORY.md`. Out-of-repo; will not be seen by subagents. Do not rely on memory content to make a prompt file "work" — prompts must be self-contained.

## Reading path for a fresh agent picking up this work

Always read in this order:

1. **`docs/plans/NEXT.md`** — the living "where we are, what's next" doc. Read this first. Everything below is background context that NEXT.md will point you to as needed.
2. This file (CLAUDE.md) — repo orientation and conventions.
3. **`docs/plans/agentic-pipeline-optimization-framework.md`** — **authoritative framework plan** (as of 2026-04-21). Tiered leakage discipline, optimizer/dispatcher/subagent architecture, structural defenses. The paper's primary contribution; paper-trail + Sarol is the case study, not the contribution.
4. `docs/plans/experiment-sarol-archive-and-eval-framework.md` — Sarol-specific archive + invariants + Q9c memory-blind mechanism. Companion to the framework doc.
5. `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — Rule 1 (subagent sandboxing, stays authoritative); Rule 2 (main-session test blindness, **superseded for agent-only mode** by the framework doc's Tier 3 sealing — see the cross-reference at the bottom of the hygiene doc).
6. `docs/plans/experiment-april-20-findings.md` — the N=5 Sarol smoketest findings; the INDIRECT-detection failure mode.
7. `docs/plans/paper-writeup-items.md` — paper-framing, named contributions, 9-paper lit review + borrow catalog.
8. Newest entries in `docs/journal/` — what was discussed and decided last working session, with inline **Human:** / **Agent:** attribution.
9. (If needed) `docs/plans/experiment-sarol-benchmark.md` — the original strategy doc; `docs/plans/experiment-sarol-runbook.md` — the pipeline execution runbook; `docs/plans/experiment-sarol-faithfulness.md` — phase-by-phase map of what Sarol variants do and don't test.

## Doc landscape (current, 2026-04-21)

**Stable authoritative references (edit in place):**
- `docs/plans/NEXT.md` — status + next steps
- **`docs/plans/agentic-pipeline-optimization-framework.md` — framework plan (authoritative post-2026-04-21 reframe): tiered leakage discipline + optimizer/dispatcher/subagent architecture**
- `docs/plans/experiment-sarol-benchmark.md` — strategy (Sarol-specific)
- `docs/plans/experiment-sarol-runbook.md` — execution (Sarol-specific)
- `docs/plans/experiment-sarol-faithfulness.md` — phase-by-phase variant coverage (source of truth for "what Sarol tests")
- `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — hygiene rules; Rule 1 authoritative; Rule 2 superseded for agent-only mode (see framework doc §6)
- `docs/plans/experiment-sarol-optimization-escalation.md` — escalation ladder if manual stalls
- `docs/plans/experiment-sarol-archive-and-eval-framework.md` — archive + eval framework (Sarol-specific companion to the framework doc)
- `docs/plans/experiment-sarol-methods-research.md` — method menu for future sweeps
- `docs/plans/paper-writeup-items.md` — paper-framing running notes + 9-paper borrow catalog

**Historical / milestone docs (read for provenance, don't edit):**
- `docs/plans/experiment-sarol-leakage-hardening.md` — original leakage analysis (superseded by optimization-loop-hygiene)
- `docs/plans/experiment-sarol-hardening-implementation.md` — status doc on hardening defenses that landed
- `docs/plans/experiment-sarol-smoketest-handoff.md` — the original N=5 smoketest handoff prompt
- `docs/plans/experiment-april-20-findings.md` — the N=5 findings themselves (milestone, not updated)

**Journal (append-only, daily-per-topic):**
- `docs/journal/YYYY-MM-DD-<topic>.md` — decision logs with inline **Human:** / **Agent:** attribution
