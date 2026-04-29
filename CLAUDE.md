# paper-trail — orientation for Claude Code sessions

Fresh-agent crib sheet. Read before making structural changes.

## What paper-trail is

A citation-integrity agent that audits the references in a manuscript. Ships as the `/paper-trail` slash command (plus sister commands `/ground-claim`, `/fetch-paper`, `/verify-bib`, `/init-writing-tools`, `/paper-trail-init`). The shipped product is the agent + its prompts + its orchestration — not any given Claude Code session.

Two workflow modes:

- **Reader mode** — audit someone else's paper end-to-end from a single PDF. Self-contained: writes to a `paper-trail-<pdf-stem>/` output directory. Used for peer review, literature vetting.
- **Author mode** — audit your own in-progress manuscript (a `.tex` file + `.bib` + source PDFs). Writes to the project's `claims_ledger.md`.

Both modes share the per-claim two-pass workflow (extractor → adjudicator) plus a Phase-3.5 attestation verifier.

## Where things live

- `.claude/commands/<name>.md` — slash command prompts (the orchestrator IS the agent driven by these prompts; there is no separate Python orchestrator). Six existing: `paper-trail.md` (entry point, 698 lines), `ground-claim.md` (per-claim workflow, 172 lines), `fetch-paper.md`, `verify-bib.md`, `init-writing-tools.md`, `paper-trail-init.md`.
- `.claude/prompts/<role>-dispatch.md` — literal prompts the orchestrator passes to subagents. Three roles: `extractor-dispatch.md`, `adjudicator-dispatch.md`, `verifier-dispatch.md`.
- `.claude/specs/<topic>.md` — interface specifications. `verdict_schema.md` is the per-claim verdict JSON schema (source of truth — `ledger.md` is rendered from these). `ingest.md` is the source-handle layout produced by `scripts/ingest_pdf.py`.
- `.claude/scripts/<name>.py` — supporting Python: `validate_claims.py`, `render_html_demo.py`, `ingest_pdf.py`.
- `.claude/skills/<name>.md` — project-owned skills. Currently `doc-split-check.md` and `plan-doc-readiness-check.md`. The `.gitignore` carveout pattern (`.claude/skills/*` + `!` re-includes) is what makes these committable while machine-local skills stay ignored.
- `templates/claims_ledger.md` — the canonical author-mode ledger schema. Reused verbatim by reader mode.
- `examples/` — canonical runs. `paper-trail-adamson-2025/` is the M1 reference run (per memory `project_m1_complete.md`); start review-agents at its README.md. `paper-trail-adamson-dmi-cns-lesions/` and `DFD_authormode/` are additional fixtures.
- `docs/plans/` — stable reference plans. Long-lived; edit in place when decisions change. One file per major topic.
- `docs/journal/YYYY-MM-DD-<topic>.md` — per-day-per-topic decision log with attribution. Append-only in practice; captures *who* raised *what* and *why*. No subfolders.
- `docs/claude_ops.md` — operational standards referenced by existing plan docs.
- `docs/trust-model.md`, `docs/internals.md`, `docs/prerequisites.md` — architecture and setup references.

## Codebase pointers for fresh agents implementing features

When picking up a feature plan doc and starting implementation, the relevant files to read first are usually:

- **Orchestrator (slash-command prompt):** `.claude/commands/paper-trail.md` — phases 0-5, 698 lines. Phase 3.1 is "Claim extraction" (line 315+); Phase 3 is the per-claim two-pass workflow that dispatches subagents.
- **Per-claim workflow:** `.claude/commands/ground-claim.md` — explains the multi-cite handling ("LaTeX `\cite{a,b,c}` produces one ledger entry per citekey"), the `co_cite_context.sibling_citekeys` population, and the Pass 1 / Pass 2 / Pass 3 (verifier) handoffs.
- **Verdict schema:** `.claude/specs/verdict_schema.md` — the source-of-truth contract for what each subagent emits. Includes verdict enum, `co_cite_context` envelope, `attestation` envelope, rollup rules.
- **Subagent dispatch prompts:** `.claude/prompts/extractor-dispatch.md`, `adjudicator-dispatch.md`, `verifier-dispatch.md` — the literal prompts subagents receive, with `{{slot}}` placeholders.
- **Ledger template:** `templates/claims_ledger.md` — author-mode ledger frontmatter and body schema.
- **Canonical fixture:** `examples/paper-trail-adamson-2025/` — reference output to compare against when validating that a feature change has not regressed.

## Documentation conventions

**Plain language.** Avoid acronyms unless expanded on first use, and prefer descriptive words over jargon. Per memory `feedback_plain_language.md`.

**Attribution in decision rationale.** When a plan doc or journal entry records a decision whose rationale is interesting to retrospect on, mark inline with **Human:** and **Agent:** prefixes. Even when one party was wrong and pushed back by the other, preserve that — we're writing for the paper's human-value-in-agentic-collaboration discussion. Per memory `feedback_decision_doc_attribution.md`.

**Modularity over monolith.** One topic per file. Long monolithic docs are hard to navigate later. The `doc-split-check` project-owned skill enforces this (~400-line trigger).

**Plan-doc readiness.** Before committing a new plan doc, the `plan-doc-readiness-check` project-owned skill verifies the doc carries enough self-contained information for a fresh-agent in a future session to implement from it without the conversation context — codebase pointers, schema-change details, smoke-test criteria, integration points.

**When to write a journal entry.** At the end of any substantive discussion that produced decisions or open questions. Especially for design / scope discussions where the who-said-what is the actual artifact.

## Working pace

**One thing at a time, conceptually.** When a session surfaces multiple threads — a primary task plus optional secondaries, or a main question plus incidental findings — complete the primary cleanly before opening the secondary, even if they're independently safe and the secondary is tempting. "One thing" is a conceptual scope, not literally one tool call. Per memory `feedback_one_thing_at_a_time.md`.

## Commit style

Short single-line thematic commit messages. No AI attribution trailers. Per memory `feedback_commit_style.md`.

## Where the user's global memory lives

`/Users/pmayankees/.claude/projects/-Users-pmayankees-Documents-Misc-Projects-paper-trail/memory/`. Indexed by `MEMORY.md`. Out-of-repo; will not be seen by subagents. Do not rely on memory content to make a prompt file "work" — prompts must be self-contained.

## Reading path for a fresh agent picking up this work

Always read in this order:

1. This file (CLAUDE.md) — repo orientation and conventions.
2. **`docs/plans/` for the feature you're picking up** — `feature-multi-cite-joint-verdict.md`, `feature-neighbor-claim-attribution.md`, or `feature-issue-command.md`. Each is self-contained with codebase pointers.
3. **`docs/plans/paper-trail-product-backlog.md`** — broader product backlog context if the feature touches shipping concerns.
4. **`.claude/commands/paper-trail.md` and `.claude/commands/ground-claim.md`** — the two orchestrator prompts. The feature you're implementing almost certainly modifies one or both.
5. **`.claude/specs/verdict_schema.md`** — schema source of truth. Most features touch the schema.
6. Newest entries in `docs/journal/` — what was discussed and decided last working session, with inline **Human:** / **Agent:** attribution.

## Doc landscape (current)

**Stable authoritative references (edit in place):**

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
- **`feature/<scope>`** — feature-implementation branches off main. Currently `feature/multi-cite-and-neighbor-claims` (Features 1+2 share a branch since both touch the orchestrator and adjudicator).
- **`sarol`** — paused agentic-pipeline-optimization research line (Sarol-2024 benchmark). Not part of paper-trail-the-tool development. Out of scope for fresh-agent main-branch work.
