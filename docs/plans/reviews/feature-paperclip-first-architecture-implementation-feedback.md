Reference: docs/claude_ops.md

# Implementation Feedback: paperclip-first architecture — Phase 1

## Verdict
Revise before commit. The core Phase 1 coverage-classification slice is present and follows the smoke-test correction, but two prompt ambiguities should be tightened before commit: `--paperclip=off/never` wording in `verify-bib.md` accidentally says to skip the metadata fallback step, and `paper-trail.md` omits the top-N scan requirement from its Phase 1 summary.

## Plan Coverage
| Phase 1 slice/item | Status | Evidence: path:line | Notes |
|---|---|---|---|
| Emit `coverage` enum `paperclip` / `external` / `unresolved` | Done | `src/commands/verify-bib.md:25`, `src/commands/verify-bib.md:132`, `src/commands/paper-trail.md:216`, `src/commands/paper-trail.md:232` | Matches plan naming pin at `docs/plans/feature-paperclip-first-architecture.md:57`. |
| Emit and wire `paperclip_handle` for in-corpus refs | Done | `src/commands/verify-bib.md:27`, `src/commands/verify-bib.md:132`, `src/commands/paper-trail.md:220`, `src/commands/paper-trail.md:232` | Matches plan naming pin at `docs/plans/feature-paperclip-first-architecture.md:58`; handle is the `/papers/<doc_id>/` directory name. |
| Use `paperclip search -s <source>`, not server-broken `lookup` | Done | `src/commands/verify-bib.md:15`, `src/commands/verify-bib.md:31`, `src/commands/verify-bib.md:35`, `docs/plans/feature-paperclip-first-architecture.md:207` | Implementation encodes both smoke findings: `lookup` broken and `search` requires explicit `-s`. |
| Search arXiv by title for every reference | Done | `src/commands/verify-bib.md:35`, `src/commands/paper-trail.md:220`, `docs/plans/feature-paperclip-first-architecture.md:215` | This matches the documented 19 -> 27 undercount fix. |
| Apply normalized-title-overlap >= 0.6 and year +/-2 gate | Done | `src/commands/verify-bib.md:31`, `src/commands/verify-bib.md:35`, `src/commands/paper-trail.md:220` | Matches the plan's Phase 1 filter rule at `docs/plans/feature-paperclip-first-architecture.md:101` and smoke note at `docs/plans/feature-paperclip-first-architecture.md:215`. |
| Scan top-N, not result #1 only | Partial | `src/commands/verify-bib.md:31`, `src/commands/verify-bib.md:35`, `src/commands/paper-trail.md:220` | `verify-bib.md` requires scanning full top-N with `-n 4`; `paper-trail.md` delegates to `/verify-bib` but its one-line summary omits the top-N rule. |
| `abstracts` source default-on and identity-resolution-only | Done | `src/commands/verify-bib.md:36`, `src/commands/paper-trail.md:220`, `docs/plans/feature-paperclip-first-architecture.md:65`, `docs/plans/feature-paperclip-first-architecture.md:179` | A hit marks `coverage: external`; no grounding claim is made. |
| Auth probe is non-fatal and maps unauthenticated runs to `--paperclip=off` | Done | `src/commands/paper-trail.md:118`, `src/commands/paper-trail.md:134`, `docs/plans/feature-paperclip-first-architecture.md:66`, `docs/plans/feature-paperclip-first-architecture.md:178` | One-line warning + no interactive login matches OQ4 default. |
| Phase-1 summary line and counts sum to N | Done | `src/commands/paper-trail.md:235`, `docs/plans/feature-paperclip-first-architecture.md:105`, `docs/plans/feature-paperclip-first-architecture.md:215` | Implementation specifies `verified: <N>/<N> (paperclip:<a>, external:<b>, unresolved:<c>)` and says counts sum to N. |
| Step-1 smoke result recorded | Done | `docs/plans/feature-paperclip-first-architecture.md:215` | Records `verified: 56/56 (paperclip:27, external:29, unresolved:0)` and the fixed arXiv-search bug. |

## Critical Drift
- None found.

## Missing Pieces
- Phase 1 plan item: top-N candidate scan in the orchestrator summary | Where it should land: `src/commands/paper-trail.md:220` | Why it matters: the smoke result says true matches often sit at result #2-#3, and the user explicitly asked that `paper-trail.md` and `verify-bib.md` describe the same rule | Suggested change: add "scan the full top-N (`-n 4`), not just result #1" to the Phase 1 coverage bullet.

## Contract Violations
- `--paperclip=off` / `--paperclip=never` wording is internally contradictory in `verify-bib.md`. Plan says `never` forces existing PDF path and `off` is equivalent with a startup warning (`docs/plans/feature-paperclip-first-architecture.md:59`); code says "skip steps 1-3 entirely" (`src/commands/verify-bib.md:41`) even though step 3 is the fallback metadata chain at `src/commands/verify-bib.md:37`, then also says "classify ... via the metadata chain alone." Required fix: change to "skip paperclip steps 1-2" or "skip paperclip full-text and abstracts searches, then run the metadata chain."

## Internal Consistency
- `verify-bib.md` says to scan the full top-N and uses `-n 4` (`src/commands/verify-bib.md:31`, `src/commands/verify-bib.md:35`); `paper-trail.md` summarizes the same coverage rule but only mentions the match gate and fuzzy results (`src/commands/paper-trail.md:220`). This is not a behavioral contradiction because it delegates to `/verify-bib`, but it is an instruction-fidelity mismatch for the orchestrator prompt.
- `paper-trail.md` says `never` / `off` skip paperclip and classify via the metadata chain (`src/commands/paper-trail.md:220`), while `verify-bib.md` says "skip steps 1-3 entirely" (`src/commands/verify-bib.md:41`). Tighten `verify-bib.md` so both files say the same thing.

## Defensible Deviations
- The plan's older Phase 1 prose starts with "exact-DOI lookup" (`docs/plans/feature-paperclip-first-architecture.md:100`), but the implementation resolves full-text coverage by title search across `-s pmc` and `-s arxiv` for every reference (`src/commands/verify-bib.md:35`). This is a defensible improvement because the plan's own smoke notes say `lookup` is server-broken and the corrected title-search rule recovered 19 -> 27 hits (`docs/plans/feature-paperclip-first-architecture.md:207`, `docs/plans/feature-paperclip-first-architecture.md:215`).
- `paper-trail.md` says explicit `--paperclip=off` / `--paperclip=never` suppresses the preflight probe and warning (`src/commands/paper-trail.md:134`). The plan says auth failure should warn and auto-fall back to `off` (`docs/plans/feature-paperclip-first-architecture.md:66`, `docs/plans/feature-paperclip-first-architecture.md:178`), but suppressing an auth probe when the user explicitly opted out is reasonable; author should confirm this intended UX.
- `paper-trail.md` says `--paperclip=only` flags `external` references in Phase 1 and gates in Phase 2 (`src/commands/paper-trail.md:220`), while the naming pin says `only` "abort on external" (`docs/plans/feature-paperclip-first-architecture.md:59`). For a Phase 1-only slice, surfacing/flagging now and aborting later is plausible, but the eventual Phase 2 implementation should preserve the abort behavior.

## Suggested Edits
- `src/commands/verify-bib.md:41`: replace "skip steps 1-3 entirely" with "skip paperclip steps 1-2 entirely" or equivalent wording that keeps the CrossRef -> arXiv API -> Semantic Scholar fallback active.
- `src/commands/paper-trail.md:220`: add the top-N rule from `verify-bib.md`: scan the full top-N (`-n 4`), not just result #1, before accepting a candidate that clears the title/year gate.
- `src/commands/paper-trail.md:220`: optionally clarify `--paperclip=only` as "record/flag externals in Phase 1; Phase 2 aborts before fetching them" to reconcile with the plan's mode pin.

## Questions For The Author
- Should explicit `--paperclip=off` / `--paperclip=never` intentionally skip the `paperclip config` probe and warning, or should the run still record that paperclip was not probed because the user opted out?
- In `--paperclip=only`, should Phase 1 abort immediately on any `external`, or is Phase 1 allowed to complete classification and leave the abort gate to Phase 2?

## Audit Trail
- docs/claude_ops.md
- docs/plans/feature-paperclip-first-architecture.md
- src/commands/paper-trail.md
- src/commands/verify-bib.md
- git diff

## Resolution (2026-06-24)
- APPLIED: Contract Violation — `verify-bib.md` "skip steps 1–3 entirely" → "skip the paperclip searches (steps 1–2) … via step 3 (the CrossRef → arXiv API → Semantic Scholar chain)" (keeps the metadata fallback active when paperclip is off).
- APPLIED: Internal Consistency / Missing Piece — added the top-N scan rule (`-n 4`, match usually at result #2–#3) to `paper-trail.md`'s Phase 1 coverage summary so it matches `verify-bib.md`.
- CONFIRMED-KEEP (author): explicit `--paperclip=off`/`never` suppresses the preflight probe + warning (Defensible Deviation; user opted-out → probing/warning is noise).
- DEFERRED to Phase 2 (carry-forward note): `--paperclip=only` flags `external` in Phase 1, with the actual abort gate to be implemented in Phase 2's fetch step (preserves the plan's "abort on external" pin at the right layer).
