Reference: docs/claude_ops.md

# Implementation Feedback: paperclip-first architecture — Phase 2

## Verdict
Revise before commit. The Phase 2 coverage branching and producer/consumer field contract are mostly aligned, but the coverage-aware post-fetch summary is internally inconsistent for already-present external PDFs.

## Plan Coverage
Phase 2 slice/item | Status (Done / Partial / Missing / Drifted) | Evidence: path:line | Notes
--- | --- | --- | ---
Read Phase 1 `coverage` from `refs.verified.bib` before `refs.bib` | Done | src/commands/paper-trail.md:240 | Matches the Phase 1 artifact contract in src/commands/verify-bib.md:132 and the plan's verified-bib field pin in docs/plans/feature-paperclip-first-architecture.md:57.
`coverage: paperclip` skips download and carries `paperclip_handle` | Done | src/commands/paper-trail.md:242; src/commands/fetch-paper.md:26 | Matches docs/plans/feature-paperclip-first-architecture.md:111 and the producer contract in src/commands/verify-bib.md:27.
`coverage: external` uses the existing fetch path | Done | src/commands/paper-trail.md:243; src/commands/fetch-paper.md:27 | Matches docs/plans/feature-paperclip-first-architecture.md:112.
`coverage: unresolved` skips fetch and goes to triage / `NEEDS_PDF` | Done | src/commands/paper-trail.md:247; src/commands/fetch-paper.md:28 | Matches docs/plans/feature-paperclip-first-architecture.md:113.
`--paperclip=only` gate lands in Phase 2 | Done, with a defensible broadening | src/commands/paper-trail.md:251 | The plan pin says `only` aborts on `external` (docs/plans/feature-paperclip-first-architecture.md:59). The implementation aborts on `external` or `unresolved`, which is consistent with pure-corpus intent but broader than the shorthand pin.
Coverage-aware post-fetch summary | Partial | src/commands/paper-trail.md:287 | Coverage counts sum to N and paperclip refs are not failures, but already-present external PDFs are omitted from the external accounting.
`/fetch-paper` coverage pre-check with no-coverage fallback | Done | src/commands/fetch-paper.md:22; src/commands/fetch-paper.md:30 | Same enum values and skip semantics as the orchestrator; no `coverage` field falls through to the old standalone behavior.
Phase 2.5 ingest only over fetched PDFs / external slice | Done | src/commands/paper-trail.md:249; src/commands/paper-trail.md:322 | Matches docs/plans/feature-paperclip-first-architecture.md:32 and docs/plans/feature-paperclip-first-architecture.md:119.

## Critical Drift
- Medium | plan/code internal accounting drift | Evidence: src/commands/paper-trail.md:244 and src/commands/paper-trail.md:290 | Required fix: account for already-present external PDFs in the post-fetch summary. The external path explicitly marks existing PDFs as "already present", but the summary says `Fetched: M / <E>` and `Could not retrieve (<E> - M)`, which incorrectly counts already-present external PDFs as failures unless `M` silently includes them. Make the denominator formula explicit, e.g. `Available: <D + A> / <E> external refs`, `Downloaded: D`, `Already present: A`, `Could not retrieve: <E - D - A>`.

## Missing Pieces
- Phase 2 summary already-present bucket | src/commands/paper-trail.md:287 | Without this, resumed runs and author-mode runs with staged PDFs can report false retrieval failures. | Add an `Already present: A external refs` line and update the failure arithmetic.
- `--paperclip` invocation discoverability | src/commands/paper-trail.md:16 | The prompt enforces `--paperclip=only` in Phase 2 but the invocation forms list does not show `--paperclip=<prefer|only|never|off>`. | Add the flag to the reader-mode forms and note that author mode inherits it alongside the other shared flags.

## Contract Violations
- None found for field names or enum values. Producer emits `coverage = {paperclip | external | unresolved}` and `paperclip_handle = {<doc_id>}` for paperclip refs (src/commands/verify-bib.md:132); consumers read `coverage` and `paperclip_handle` with the same names and values (src/commands/paper-trail.md:240; src/commands/fetch-paper.md:24).

## Internal Consistency
- `paper-trail.md` and `fetch-paper.md` agree on all three `coverage` enum values and skip semantics: `paperclip` skips download, `external` fetches, `unresolved` becomes `NEEDS_PDF` (src/commands/paper-trail.md:242; src/commands/fetch-paper.md:26).
- `paper-trail.md` and `verify-bib.md` agree that Phases 2-3 prefer `refs.verified.bib` because it carries `coverage` / `paperclip_handle` (src/commands/paper-trail.md:234; src/commands/verify-bib.md:134).
- The only mismatch is summary accounting for already-present external PDFs: the branch exists in the external path, but the summary has no bucket for it (src/commands/paper-trail.md:244; src/commands/paper-trail.md:290).

## Defensible Deviations
- `--paperclip=only` aborts on both `external` and `unresolved` (src/commands/paper-trail.md:253), while the mode pin says `only` aborts on `external` (docs/plans/feature-paperclip-first-architecture.md:59). This looks defensible because `unresolved` is also not groundable in the paperclip corpus, but the author should confirm the broader abort semantics are intended.
- The plan update records Step 2 as implemented but smoke-test gated (docs/plans/feature-paperclip-first-architecture.md:217). That is acceptable as audit metadata, not implementation behavior, but it leaves behavioral verification pending.

## Suggested Edits
- src/commands/paper-trail.md:287 — Change the summary block to include `Downloaded`, `Already present`, and `Could not retrieve` with arithmetic that sums over the external slice.
- src/commands/paper-trail.md:16 — Add `/paper-trail <path-to-pdf> --paperclip=<prefer|only|never|off>` and include it in the author-mode shared-flags sentence.
- src/commands/paper-trail.md:253 — If the broader gate is intended, clarify the wording as "abort on any non-`paperclip` coverage (`external` or `unresolved`)" so it no longer reads as an implementation detail beyond the mode pin.

## Questions For The Author
- Should `--paperclip=only` formally abort on `unresolved` as well as `external`, or should unresolved references be handled by the normal end-of-run triage path?

## Audit Trail
- docs/claude_ops.md
- docs/plans/feature-paperclip-first-architecture.md
- src/commands/verify-bib.md
- src/commands/paper-trail.md
- src/commands/fetch-paper.md

## Resolution (2026-06-24)
- APPLIED (Critical Drift / Missing Pieces — summary accounting): rewrote the post-fetch summary's external-slice arithmetic from the ambiguous `Fetched: M / <E>` + `Could not retrieve (<E> − M)` to explicit buckets — `External PDFs: <D + A> / <E> available (downloaded <D>, already present <A>)` + `Could not retrieve (<E> − D − A)`, so already-present external PDFs are no longer miscounted as retrieval failures (`src/commands/paper-trail.md`, post-fetch summary block).
- APPLIED (Missing Pieces — flag discoverability): added `/paper-trail <path-to-pdf> --paperclip=<prefer|only|never|off>` to the reader-mode invocation forms and appended `--paperclip` to the author-mode shared-flags sentence (`src/commands/paper-trail.md` Invocation forms).
- RESOLVED — Option A (Defensible Deviation + Question — `only` gate scope): narrowed `--paperclip=only` to abort on `external` ONLY; `unresolved` references flow to the normal end-of-run `NEEDS_PDF` triage in every mode (matches the plan pin at `docs/plans/feature-paperclip-first-architecture.md:59` and the Phase-1 "flags every external" wording at line 220). Decision deferred by the author to Claude, who ran an independent read-only Codex design consult — Codex returned "A — abort on external only" (rationale: `unresolved` is a *resolvability* failure, not a corpus-coverage one; the tool can't claim an unidentified paper is out-of-corpus, and conflating the two makes the gate less diagnostic). Added a clarifying paragraph to the gate section explaining why `unresolved` does not trip it.
- NOTED (Defensible Deviation — Step-2 plan metadata): the plan records Phase 2 as implemented but behavioral-smoke-gated; this is audit metadata, behavioral verification (step 2 "~27 skip / ~29 fetch") remains pending a live Phase-1 re-run that writes `coverage` into the fixture's `refs.verified.bib` (the committed fixture is the 2026-04-19 pre-coverage artifact).
