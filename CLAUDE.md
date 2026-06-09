# paper-trail — orientation for Claude Code sessions

Fresh-agent crib sheet. Read before making structural changes.

## What paper-trail is

A citation-integrity agent that audits the references in a manuscript. Ships as the `/paper-trail` slash command (plus sister commands `/ground-claim`, `/fetch-paper`, `/verify-bib`, `/init-writing-tools`, `/paper-trail-init`). The shipped product is the agent + its prompts + its orchestration — not any given Claude Code session.

Two workflow modes:

- **Reader mode** — audit someone else's paper end-to-end from a single PDF. Self-contained: writes to a `paper-trail-<pdf-stem>/` output directory. Used for peer review, literature vetting.
- **Author mode** — audit your own in-progress manuscript (a `.tex` file + `.bib` + source PDFs). Writes to the project's `claims_ledger.md`.

Both modes share the per-claim two-pass workflow (extractor → adjudicator) plus a Phase-3.5 attestation verifier.

## Where things live

`src/` is the canonical ship surface; `.claude/<dir>/` entries are subdirectory symlinks into `src/<dir>/` kept only because Claude Code's discovery rules require those paths (intentional `.claude/` reference — publication target). Never edit through `.claude/`; if a symlink breaks, regenerate it from `src/`.

- `src/commands/<name>.md` — slash command prompts (the orchestrator IS the agent driven by these prompts; there is no separate Python orchestrator). Six existing: `paper-trail.md` (entry point), `ground-claim.md` (per-claim workflow), `fetch-paper.md`, `verify-bib.md`, `init-writing-tools.md`, `paper-trail-init.md`.
- `src/prompts/<role>-dispatch.md` — literal prompts the orchestrator passes to subagents. Three roles: `extractor-dispatch.md`, `adjudicator-dispatch.md`, `verifier-dispatch.md`.
- `src/specs/<topic>.md` — interface specifications. `verdict_schema.md` is the per-claim verdict JSON schema (source of truth — `ledger.md` is rendered from these). `ingest.md` is the source-handle layout produced by `src/scripts/ingest_pdf.py`. `control_flow.md` maps the orchestrator → dispatch → subagent → exit-validation graph.
- `src/scripts/<name>.py` — supporting Python: `validate_claims.py`, `render_html_demo.py`, `ingest_pdf.py`.
- `src/skills/<name>.md` or `src/skills/<name>/SKILL.md` — project-owned skills. Currently `doc-split-check.md`, `plan-check.md` (a thin extension of the user-level `~/.claude/commands/plan-check.md`, adding paper-trail-specific gap patterns), and the directory-shaped `paperclip/`. The `.gitignore` carveout pattern (`src/skills/*` + `!` re-includes) is what makes these committable while machine-local skills stay ignored.
- `src/templates/claims_ledger.md` — the canonical author-mode ledger schema. Reused verbatim by reader mode.
- `examples/` — canonical runs. `paper-trail-adamson-2025/` is the M1 reference run (per memory `project_m1_complete.md`); start review-agents at its README.md. `paper-trail-adamson-dmi-cns-lesions/` and `DFD_authormode/` are additional fixtures.
- `docs/plans/` — stable reference plans. Long-lived; edit in place when decisions change. One file per major topic.
- `docs/NEXT.md` — pointer-style implementation queue for plans in `docs/plans/`. Updated during `/wrapup`. Recommended sequence + status table; substance lives in the linked plan docs.
- `docs/journal/YYYY-MM-DD-<topic>.md` — per-day-per-topic decision log with attribution. Append-only in practice; captures *who* raised *what* and *why*. No subfolders.
- `docs/claude_ops.md` — operational standards referenced by existing plan docs.
- `docs/trust-model.md`, `docs/internals.md`, `docs/prerequisites.md` — architecture and setup references.
- `docs/SHIP_SURFACE.md` — repo-browser-facing "this is what ships" orientation pointing at `src/`.

## Codebase pointers for fresh agents implementing features

When picking up a feature plan doc and starting implementation, the relevant files to read first are usually:

- **Control-flow map:** `src/specs/control_flow.md` — which phase dispatches which prompt, which subagent emits which schema fields, which validation gates each artifact. Read this before tracing the orchestrator by hand.
- **Orchestrator (slash-command prompt):** `src/commands/paper-trail.md` — phases 0-5. Phase 3.1 is "Claim extraction"; Phase 3 is the per-claim two-pass workflow that dispatches subagents.
- **Per-claim workflow:** `src/commands/ground-claim.md` — explains the multi-cite handling ("LaTeX `\cite{a,b,c}` produces one ledger entry per citekey"), the `co_cite_context.sibling_citekeys` population, and the Pass 1 / Pass 2 / Pass 3 (verifier) handoffs.
- **Verdict schema:** `src/specs/verdict_schema.md` — the source-of-truth contract for what each subagent emits. Includes verdict enum, `co_cite_context` envelope, `attestation` envelope, rollup rules.
- **Subagent dispatch prompts:** `src/prompts/extractor-dispatch.md`, `adjudicator-dispatch.md`, `verifier-dispatch.md` — the literal prompts subagents receive, with `{{slot}}` placeholders.
- **Ledger template:** `src/templates/claims_ledger.md` — author-mode ledger frontmatter and body schema.
- **Canonical fixture (reader mode):** `examples/paper-trail-adamson-2025/data/claims/` — 87 baseline claim JSONs (83 with multi-cite siblings) for regression checks. Note the `data/claims/` path uses the legacy layout; the modern layout is `ledger/claims/`. Both are produced by paper-trail and `render_html_demo.py` auto-detects either path. New code that loads claim JSONs should follow the same auto-detect pattern.
- **Canonical fixture (author mode):** `examples/DFD_authormode/ledger/claims/` — modern-layout author-mode example with `claims_ledger.md` frontmatter, `pdfs/`, and `ledger/`. Use this when smoke-testing author-mode behavior.

## Documentation conventions

**Plain language.** Avoid acronyms unless expanded on first use, and prefer descriptive words over jargon. Per memory `feedback_plain_language.md`.

**Attribution in decision rationale.** When a plan doc or journal entry records a decision whose rationale is interesting to retrospect on, mark inline with **Human:** and **Agent:** prefixes. Even when one party was wrong and pushed back by the other, preserve that — we're writing for the paper's human-value-in-agentic-collaboration discussion. Per memory `feedback_decision_doc_attribution.md`.

**Modularity over monolith.** One topic per file. Long monolithic docs are hard to navigate later. The `doc-split-check` project-owned skill enforces this (~400-line trigger).

**Plan-doc readiness.** After writing a plan doc, the `plan-check` skill (user-level at `~/.claude/commands/plan-check.md`, with a thin paper-trail-specific extension at `src/skills/plan-check.md`) verifies the doc carries enough self-contained information for a fresh-agent in a future session to implement from it without the conversation context. The principle: every piece of context the current session accumulated must either be **pointed at** (name the docs / files / memories the fresh agent should read first) or **stated directly** (when the context is load-bearing and brittle to indirection).

**When to write a journal entry.** At the end of any substantive discussion that produced decisions or open questions. Especially for design / scope discussions where the who-said-what is the actual artifact.

## Working pace

**One thing at a time, conceptually.** When a session surfaces multiple threads — a primary task plus optional secondaries, or a main question plus incidental findings — complete the primary cleanly before opening the secondary, even if they're independently safe and the secondary is tempting. "One thing" is a conceptual scope, not literally one tool call. Per memory `feedback_one_thing_at_a_time.md`.

## Commit style

Short single-line thematic commit messages. No AI attribution trailers. Per memory `feedback_commit_style.md`.

## Where the user's global memory lives

`/Users/philadamson/.claude/projects/-Users-philadamson-Documents-Misc-Projects-paper-trail/memory/`. Indexed by `MEMORY.md`. Out-of-repo; will not be seen by subagents. Do not rely on memory content to make a prompt file "work" — prompts must be self-contained.

## Reading path for a fresh agent picking up this work

Always read in this order:

1. This file (CLAUDE.md) — repo orientation and conventions.
2. **`docs/plans/` for the feature you're picking up** — `feature-multi-cite-joint-verdict.md`, `feature-neighbor-claim-attribution.md`, or `feature-issue-command.md`. Each is self-contained with codebase pointers.
3. **`docs/plans/paper-trail-product-backlog.md`** — broader product backlog context if the feature touches shipping concerns.
4. **`src/commands/paper-trail.md` and `src/commands/ground-claim.md`** — the two orchestrator prompts. The feature you're implementing almost certainly modifies one or both.
5. **`src/specs/verdict_schema.md`** — schema source of truth. Most features touch the schema.
6. Newest entries in `docs/journal/` — what was discussed and decided last working session, with inline **Human:** / **Agent:** attribution.

## Doc landscape (current)

**Stable authoritative references (edit in place):**

- `docs/plans/feature-paperclip-first-architecture.md` — paperclip-first read-path with PDF fallback (post-2026-05-01 arxiv-fulltext re-probe; supersedes the April PDF-centric default)
- `docs/plans/repo-organization.md` — agent-instruction-forward repo with top-level `src/` mirroring `.claude/` via subdirectory symlinks, callgraph spec at `src/specs/control_flow.md`, light brevity audit
- `docs/plans/run-isolation-framework.md` — isolated `/paper-trail` run framework under `dev/isolation/` (Docker + GROBID sidecar, host paperclip-credential mount, regression-investigation report rather than pass/fail test)
- `docs/plans/feature-multi-cite-joint-verdict.md` — joint-verdict pass for multi-citation sentences (per-ref + joint, both reported)
- `docs/plans/feature-neighbor-claim-attribution.md` — ±1-sentence bidirectional neighbor inference, skip-when-neighbor-cited
- `docs/plans/feature-issue-command.md` — `/issue` slash command for bug reports + verdict disputes
- `docs/plans/paper-trail-product-backlog.md` — product backlog; v1-launch features, distribution items, repo-structure decision
- `docs/plans/add-paper-trail-orchestrator.md` — original `/paper-trail` orchestrator scoping
- `docs/plans/author-mode-parity.md` — author-mode parity with reader mode
- `docs/plans/blindspot-mitigations.md` — v1 rigor-gap mitigations

**Journal (append-only, daily-per-topic):**

- `docs/journal/YYYY-MM-DD-<topic>.md` — decision logs with inline **Human:** / **Agent:** attribution

## Branch model

- **`main`** — paper-trail-the-tool. Plan docs land here as forward-looking to-do items; code changes go on feature branches off main.
- **`feature/<scope>`** — feature-implementation branches off main. Currently `feature/multi-cite-and-neighbor-claims` (Features 1+2 share a branch since both touch the orchestrator and adjudicator), and `feature/paperclip-primary-workflow` (paperclip-first architecture; the architectural-shift branch supersedes the April PDF-centric default).
- **`sarol`** — paused agentic-pipeline-optimization research line (Sarol-2024 benchmark). Not part of paper-trail-the-tool development. Out of scope for fresh-agent main-branch work.
