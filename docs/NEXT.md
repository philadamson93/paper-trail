# NEXT — implementation queue for plan docs

Pointer-style index of plan docs in `docs/plans/` that are scoped but not yet implemented. Each item is 1-3 lines + a link to the plan doc for substance.

**Last updated:** 2026-06-28

---

## Recommended sequence

Plans coordinated by sequence rather than scope (the earlier ones reshuffle paths or surfaces that the later ones reference).

1. **[Repo organization](plans/repo-organization.md)** ([visual companion](plans/repo-organization.html)) — top-level `src/` mirrored to `.claude/` via subdirectory symlinks (intentional `.claude/` reference — publication target); new `src/specs/control_flow.md` callgraph spec; light brevity audit. Path-shuffles all the other plan docs' references, so goes first. **Fully review-revised 2026-05-20/21**: three reviewer passes (Codex 5-18, fresh-Claude 5-20, Codex second-pass 5-20) + a user-driven architectural pivot — **RD-9 supersedes RD-1: author mode now takes a manuscript path argument, no cross-repo vendoring**. All open questions resolved (OQ-A ship paperclip; OQ-B `src/skills/*` ignore with carveouts; OQ-C/C' → RD-9; OQ-D `{{spec_root}}` slot). Review artifacts in [plans/reviews/](plans/reviews/). **Implemented 2026-06-09 + merged to `main` 2026-06-24** (`8593683`); behavioral smokes (discovery + execution-path) PASS — see the plan's "Implementation results" section.
2. **[Run-isolation framework](plans/run-isolation-framework.md)** — `dev/isolation/` Docker + GROBID sidecar + `report.py`; regression-investigation report (not pass/fail test). Uses post-repo-org `src/` paths cleanly.
3. **[Paperclip-first architecture](plans/feature-paperclip-first-architecture.md)** — paperclip-mode read-path with PDF fallback; schema 1.0 → 1.1 adds `source_mode`/`paperclip_handle`/`locator`. **Phases 0-2 + Phase-3 (schema 1.1 `8d2019b` + dispatch `0f25bd2`) + Phase-5 render (source-mode badge + `claims_ledger.md` column) all SHIPPED and Codex `/review-implementation`-reviewed 2026-06-27. SKILL handling resolved 2026-06-27 (v0.5.11 stub adopted + dispatch repointed to `paperclip skill`). **Paperclip-mode path validated locally 2026-06-28 (Step-3 single-cite smoke PASSED: no-fetch + schema-1.1 + verifier replay + Phase-5 badge all confirmed).** **Merged to `main` 2026-06-28** — smoke gate accepted as satisfied for the paperclip-first path (the feature's core; PDF-mode is the legacy fallback, a near-rename of the existing M1 PDF workflow). **Deferred follow-up:** the PDF-mode/full-fixture smoke (Step-3 PDF-regression/OCR, Step-4 87-claim diff, Step-5 author-mode) — gated on the external-PDF toolchain (GROBID/Docker + a fetch path for the 29 external refs), not installed on this Mac; the run-isolation framework (#2) is its proper home.
4. **[Multi-cite joint verdict (Feature 1)](plans/feature-multi-cite-joint-verdict.md)** + **[Neighbor-claim attribution (Feature 2)](plans/feature-neighbor-claim-attribution.md)** — share `feature/multi-cite-and-neighbor-claims` branch (both touch the orchestrator and adjudicator). Plan-only; if they land they take schema 1.2 (paperclip-first took 1.0 → 1.1).
5. **[Issue command](plans/feature-issue-command.md)** — `/issue` slash command for bug reports + verdict disputes. Standalone; lands on its own feature branch when picked up.

## Repo-org close-out items (before or at merge)

- **Behavioral smokes — discovery + execution-path resolution DONE 2026-06-24** (headless `claude -p` sessions in the worktree): all 6 commands + both skill shapes discovered through the symlinks; reader + author-mode runs executed with **zero path-resolution errors**; RD-9 two-cwd contract holds (`--add-dir` registers the slash command; repo root resolves to the canonical path regardless of cwd). **Grounding is environment-blocked** (no fetch path / no `pdftotext`·GROBID·`lxml`) — orthogonal to the reorg, does **not** gate merge. Full results in [repo-organization.md § Behavioral smoke results](plans/repo-organization.md). Still open (non-blocking): a clean reader run through the Phase-5 render + a default-output author run. (Main-checkout note: before checking out this branch in the main checkout, move aside the untracked `.claude/skills/paperclip/`, now tracked at `src/skills/paperclip/`.)
- **Merge `repo-organization` → `main` — DONE 2026-06-24** (`8593683`). RD-8 rebase of `feature/paperclip-primary-workflow` is moot: that branch was superseded by `feat/paperclip-first-smoke-gate` (built on repo-org'd `main`, merged 2026-06-28) and the stale branch was deleted. Remaining gates are user-side (SHIP_SURFACE headline, default-output OQ).
- **Regenerate `plans/repo-organization.html`** via `/explain-plan` — **DONE 2026-06-24** (picked up Implementation-results + post-review + behavioral-smoke-results sections).
- **Workshop the `docs/SHIP_SURFACE.md` headline** with the user per RD-7 / memory `feedback_short_headline_copy.md`.
- **Open question (still open):** does the documented author-mode default-output set include `claims_ledger.md`? The 2026-06-24 author smoke used `--output-dir` overrides, so the default path wasn't exercised — needs a default-output run. See the adjudication log in [reviews/repo-organization-implementation-feedback.md](plans/reviews/repo-organization-implementation-feedback.md).

## Status conventions

- **In flight** — plan committed to a feature branch, implementation in progress.
- **Queued** — plan committed (typically to `main` or a feature branch), no implementation work started.
- **Implemented** — promoted to a release tag; remove from this doc and note in commit message.

| Plan | Status | Reviewed | Branch |
|---|---|---|---|
| repo-organization | **Merged to `main` 2026-06-24** (`8593683`); behavioral smokes (discovery + execution-path) PASS; grounding env-blocked (non-blocking); HTML regenerated. Open (non-blocking, user-side): SHIP_SURFACE headline + default-output OQ | Stale (visual companion read 2026-06-09 pre-implementation; Implementation-results + post-review + smoke-results sections added after) | merged to `main` |
| run-isolation-framework | Queued | No | none yet |
| feature-paperclip-first-architecture | **Merged to `main` 2026-06-28** (Phases 0-3 + Phase-5 render + SKILL stub, Codex-reviewed; paperclip-mode path smoke-PASSED locally 2026-06-28). **Deferred follow-up:** PDF-mode/full-fixture smoke (gated on GROBID/Docker + external-PDF fetch path) | No | merged to `main` |
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
