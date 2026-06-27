Reference: docs/claude_ops.md

# Implementation Feedback: Paperclip-first architecture — schema 1.1 slice

## Verdict
Revise before commit. The schema slice covers most of the planned 1.1 contract, but two contract drifts should be fixed before landing: `source_mode` is documented as both inert and adjudicator-weighting, and the still-PDF-specific required `handle` field leaves paperclip-mode verdicts without a coherent envelope.

## Plan Coverage
| Item | Status (Done / Partial / Missing / Drifted) | Evidence: path:line | Notes |
| --- | --- | --- | --- |
| Plan status line destaled | Done | docs/plans/feature-paperclip-first-architecture.md:3 | Line 3 now says Phase 3 is in progress and the schema 1.1 increment is implemented. |
| OQ6 resolved to Option A | Done | docs/plans/feature-paperclip-first-architecture.md:174 | Evidence item is resolved additively to `{section, line, snippet, source_mode?, locator?}`. |
| OQ7 resolved to Option A | Done | docs/plans/feature-paperclip-first-architecture.md:175 | Plan says `source_mode` rides in adjudicator-visible evidence as inert provenance. |
| Schema version bump | Done | src/specs/verdict_schema.md:32, src/specs/verdict_schema.md:111, src/specs/verdict_schema.md:203 | JSON example, field reference, and version history all say `1.1`. |
| Required `source_mode` enum | Partial | src/specs/verdict_schema.md:116, src/specs/verdict_schema.md:196 | Field and validation rule are present, but the field doc contradicts OQ7 by saying `pdf_ocr_fallback` has lower confidence weighting in the adjudicator. |
| Conditional `paperclip_handle` | Done | src/specs/verdict_schema.md:117, src/specs/verdict_schema.md:197 | Spec allows absent/null outside paperclip mode and validates both directions of mismatch. |
| Evidence item additive shape | Done | src/specs/verdict_schema.md:131 | Keeps `{section, line, snippet}` and adds optional `source_mode` / `locator`. |
| `figures_checked.figure_path?` | Done | src/specs/verdict_schema.md:132 | Optional `figure_path` is documented for paperclip and PDF-derived figures. |
| Validation rules in schema, not `validate_claims.py` | Done | docs/plans/feature-paperclip-first-architecture.md:160, src/specs/verdict_schema.md:196 | `git diff --name-only` shows only the three scoped files; `src/scripts/validate_claims.py` is untouched. |
| Companion HTML consistency | Drifted | docs/plans/feature-paperclip-first-architecture.html:111, docs/plans/feature-paperclip-first-architecture.html:143 | The decision card says OQ7 Option A, but the TL;DR still says the adjudicator stays mode-blind. |

## Critical Drift
- `src/specs/verdict_schema.md:116` conflicts with OQ7. The plan says `source_mode` is inert provenance and "must not influence the verdict" (`docs/plans/feature-paperclip-first-architecture.md:175`), but the schema says `pdf_ocr_fallback` gets "lower confidence weighting in the adjudicator" before saying the adjudicator must not let `source_mode` bias the verdict. That makes the authoritative spec internally contradictory.
- `src/specs/verdict_schema.md:114` still defines required `handle` as `pdfs/<citekey>/`, while paperclip-covered refs skip download and never hit disk (`docs/plans/feature-paperclip-first-architecture.md:112`) and use `paperclip_handle` as the locator base (`src/specs/verdict_schema.md:117`). A paperclip-mode verdict therefore has no valid value for the required `handle` field unless producers invent a fake PDF handle.

## Missing Pieces
- None within the declared schema-slice scope. The extractor split, orchestrator dispatch branch, dispatch payload wiring, and `control_flow.md` slot-map changes are explicitly later increments and are not counted missing here.

## Contract Violations
- Companion HTML contradiction: `docs/plans/feature-paperclip-first-architecture.html:111` says the adjudicator stays "mode-blind", but OQ7 Option A says the adjudicator sees `source_mode` as inert metadata (`docs/plans/feature-paperclip-first-architecture.html:143`). This does not change the implementation artifact, but it contradicts the plan contract the companion is supposed to mirror.
- Paperclip locator format is correct in the authoritative spec (`src/specs/verdict_schema.md:131` uses `/papers/<handle>/sections/<name>.lines#L<n>`), but the companion's decision table drops the leading slash (`docs/plans/feature-paperclip-first-architecture.html:124`). Low severity because source precedence gives `verdict_schema.md` priority.

## Test Gaps
- No runnable test suite exists for this repo per `docs/claude_ops.md`; no behavioral smoke is expected for this schema-only slice. The review verified the unstaged diff and full schema text only.

## Defensible Deviations
- `paperclip_handle` outside paperclip mode is documented as `null / absent` (`src/specs/verdict_schema.md:117`) even though the plan says "present iff" (`docs/plans/feature-paperclip-first-architecture.md:156`). This is defensible because the mismatch rule treats non-null outside paperclip mode as the violation (`src/specs/verdict_schema.md:197`), preserving clean JSON examples for PDF mode.
- The schema adds optional evidence fields rather than an attestation/hits model (`src/specs/verdict_schema.md:131`), matching OQ6 and preserving existing consumers of `{section, line, snippet}`.

## Suggested Code Edits
- In `src/specs/verdict_schema.md`, remove "lower confidence weighting in the adjudicator" from the `source_mode` field doc, or move OCR confidence handling to `ingest_mode` / verifier behavior so OQ7 remains true.
- Clarify `handle` for paperclip mode: either make it nullable/absent when `source_mode == "paperclip"`, or redefine it as a generic source artifact prefix that may be `/papers/<paperclip_handle>/` for paperclip mode and `pdfs/<citekey>/` for PDF mode.
- In the companion HTML, replace "the adjudicator stays mode-blind" with "the adjudicator applies the same rubric and treats provenance as inert metadata"; restore the leading `/` in the paperclip locator example.

## Questions For The Author
- Should paperclip-mode verdicts retain a generic `handle` pointing at `/papers/<paperclip_handle>/`, or should `handle` become PDF-only nullable metadata now that `paperclip_handle` is the paperclip locator base?

## Audit Trail
- Read `docs/claude_ops.md`.
- Read `docs/plans/feature-paperclip-first-architecture.md`, focused on Schema changes and OQ6/OQ7.
- Ran `git diff -- docs/plans/feature-paperclip-first-architecture.md docs/plans/feature-paperclip-first-architecture.html src/specs/verdict_schema.md`.
- Read `src/specs/verdict_schema.md` in full with line numbers.
- Confirmed unstaged diff names are exactly the three scoped files and `src/scripts/validate_claims.py` is untouched.

## Resolution (Claude, 2026-06-27)

All findings agreed with and resolved:
- **Critical #1 (source_mode vs OQ7):** fixed — removed "lower confidence weighting in the adjudicator" from the `source_mode` doc; OCR confidence now attributed to the verifier threshold / `ingest_mode`, never the adjudicator (`verdict_schema.md` `source_mode` field).
- **Critical #2 / Author Question (PDF-only required `handle`):** user chose **Option A** — `handle` relaxed to required-unless-`paperclip` (null/absent for paperclip, where `paperclip_handle` is the artifact base); `ingest_mode` likewise null for paperclip. Recorded in `verdict_schema.md` (`handle` field + version history) and the plan's Schema-changes section.
- **Contract violation (companion TL;DR "mode-blind"):** fixed — TL;DR now says the adjudicator applies the same rubric and treats `source_mode` as inert metadata.
- **Contract violation (companion locator missing leading slash):** fixed — restored `/papers/...` in both companion occurrences (decision card + knobs card).
- **Defensible deviations:** both confirmed keep (`paperclip_handle` null/absent framing; additive evidence shape per OQ6).
- **Test gaps:** none — schema-only slice, no runnable suite per `claude_ops.md`.
