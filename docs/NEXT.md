# NEXT — implementation queue for plan docs

Pointer-style index of plan docs in `docs/plans/` that are scoped but not yet implemented. Each item is 1-3 lines + a link to the plan doc for substance.

**Last updated:** 2026-06-09

---

## Recommended sequence

Plans coordinated by sequence rather than scope (the earlier ones reshuffle paths or surfaces that the later ones reference).

1. **[Repo organization](plans/repo-organization.md)** ([visual companion](plans/repo-organization.html)) — top-level `src/` mirrored to `.claude/` via subdirectory symlinks (intentional `.claude/` reference — publication target); new `src/specs/control_flow.md` callgraph spec; light brevity audit. Path-shuffles all the other plan docs' references, so goes first. **Fully review-revised 2026-05-20/21**: three reviewer passes (Codex 5-18, fresh-Claude 5-20, Codex second-pass 5-20) + a user-driven architectural pivot — **RD-9 supersedes RD-1: author mode now takes a manuscript path argument, no cross-repo vendoring**. All open questions resolved (OQ-A ship paperclip; OQ-B `src/skills/*` ignore with carveouts; OQ-C/C' → RD-9; OQ-D `{{spec_root}}` slot). Review artifacts in [plans/reviews/](plans/reviews/). **Implemented 2026-06-09** on the `repo-organization` branch — structural smokes pass; behavioral smokes (slash-command discovery/execution, author-mode two-cwd) pending a user-run session; see the plan's "Implementation results" section.
2. **[Run-isolation framework](plans/run-isolation-framework.md)** — `dev/isolation/` Docker + GROBID sidecar + `report.py`; regression-investigation report (not pass/fail test). Uses post-repo-org `src/` paths cleanly.
3. **[Paperclip-first architecture](plans/feature-paperclip-first-architecture.md)** — paperclip-mode read-path with PDF fallback; schema 1.1 → 1.2 hard bump adds `source_mode` enum and `paperclip_handle`. In flight on `feature/paperclip-primary-workflow`; rebases against post-repo-org `main`.
4. **[Multi-cite joint verdict (Feature 1)](plans/feature-multi-cite-joint-verdict.md)** + **[Neighbor-claim attribution (Feature 2)](plans/feature-neighbor-claim-attribution.md)** — share `feature/multi-cite-and-neighbor-claims` branch (both touch the orchestrator and adjudicator). Land at schema 1.1; coordinate with paperclip-first's 1.2 bump.
5. **[Issue command](plans/feature-issue-command.md)** — `/issue` slash command for bug reports + verdict disputes. Standalone; lands on its own feature branch when picked up.

## Repo-org close-out items (before or at merge)

- **Behavioral smokes** — user-run interactive sessions; exact list in [repo-organization.md § Deferred to user](plans/repo-organization.md). Before checking out the branch in the main checkout, move aside the untracked `.claude/skills/paperclip/` (now tracked at `src/skills/paperclip/`).
- **Merge `repo-organization` → `main`**, then rebase `feature/paperclip-primary-workflow` per RD-8.
- **Regenerate `plans/repo-organization.html`** via `/explain-plan` (stale — plan gained Implementation-results + post-review sections).
- **Workshop the `docs/SHIP_SURFACE.md` headline** with the user per RD-7 / memory `feedback_short_headline_copy.md`.
- **Open question:** does the documented author-mode default-output set include `claims_ledger.md`? Settle at the author-mode behavioral smoke; see the adjudication log in [reviews/repo-organization-implementation-feedback.md](plans/reviews/repo-organization-implementation-feedback.md).

## Status conventions

- **In flight** — plan committed to a feature branch, implementation in progress.
- **Queued** — plan committed (typically to `main` or a feature branch), no implementation work started.
- **Implemented** — promoted to a release tag; remove from this doc and note in commit message.

| Plan | Status | Reviewed | Branch |
|---|---|---|---|
| repo-organization | Implemented on `repo-organization` branch 2026-06-09, 4 commits incl. Codex `/review-implementation` fixes (structural smokes pass; behavioral smokes + merge to main pending; HTML companion stale — regenerate via `/explain-plan`) | Stale (visual companion read 2026-06-09 pre-implementation; Implementation-results + post-review sections added after) | `repo-organization` (off `feature/paperclip-primary-workflow`) |
| run-isolation-framework | Queued | No | none yet |
| feature-paperclip-first-architecture | In flight (plan-only) | No | `feature/paperclip-primary-workflow` |
| feature-multi-cite-joint-verdict + feature-neighbor-claim-attribution | In flight (plan-only) | No | `feature/multi-cite-and-neighbor-claims` |
| feature-issue-command | Queued | No | none yet |

**Reviewed column.** `Yes` = user has read the current plan content end-to-end (typically via `/read-plan` completion). `Stale` = was `Yes` before a substantive edit. `No` = never reviewed, or never recorded as reviewed. Only `/read-plan` promotes a row to `Yes`.

## Backlog (deferred, not on the immediate sequence)

Plans in `docs/plans/` that exist but aren't part of the current implementation queue (architecture-level scoping that's already shipped, or items deferred until product-launch concerns become real):

- [add-paper-trail-orchestrator.md](plans/add-paper-trail-orchestrator.md) — original `/paper-trail` orchestrator scoping; M1 implementation complete per memory `project_m1_complete.md`.
- [author-mode-parity.md](plans/author-mode-parity.md) — author-mode parity with reader mode; verify implementation completeness against memory `project_author_vs_reader_user_shape.md`.
- [blindspot-mitigations.md](plans/blindspot-mitigations.md) — v1 rigor-gap mitigations; status unclear, audit before next-session implementation work.
- [paper-trail-product-backlog.md](plans/paper-trail-product-backlog.md) — v1-product-launch backlog (UI improvements, docs pass, MCP registry submissions, incremental re-validation). Read when entering product-launch mode.

## Conventions

- This doc is updated during `/wrapup` at session end. Pointer-style only — substance lives in the linked plan/journal/spec.
- When a plan ships, remove from the table above and note in the commit message.
- When a new plan is scoped, add to the table and slot into the recommended sequence (or the backlog).
- "Recommended sequence" is a recommendation, not a commitment. The user can resequence based on shifting priorities.
