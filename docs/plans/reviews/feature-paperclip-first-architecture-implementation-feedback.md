Reference: docs/claude_ops.md

# Implementation Feedback: Paperclip-First Architecture — Phase-5 Render Increment

## Verdict
Revise before commit. The render/ledger increment is correctly scoped and the `source_mode` data path is display-only, but the Phase-5 color contract drifts for `pdf`: the plan pins PDF as blue, while the renderer uses a slate/gray badge.

## Plan Coverage
| Slice / section | Status (Done / Partial / Missing / Drifted) | Evidence: path:line | Notes |
| --- | --- | --- | --- |
| `render_html_demo.py` source-mode sidebar badge | Drifted | docs/plans/feature-paperclip-first-architecture.md:145; src/scripts/render_html_demo.py:986; src/scripts/render_html_demo.py:990; src/scripts/render_html_demo.py:991; src/scripts/render_html_demo.py:992; src/scripts/render_html_demo.py:1075; src/scripts/render_html_demo.py:1084 | Badge exists and uses the schema enum keys, but `pdf` is colored `#64748b` instead of the plan's blue. |
| `render_html_demo.py` summary data path | Done | src/scripts/render_html_demo.py:260; src/scripts/render_html_demo.py:271; src/scripts/render_html_demo.py:320; src/scripts/render_html_demo.py:354; src/scripts/render_html_demo.py:359 | `build_claim_summary()` reads the verdict envelope's top-level `claim.get("source_mode")` and carries it into `DATA.summaries`. |
| `render_html_demo.py` popup data path | Done | src/scripts/render_html_demo.py:354; src/scripts/render_html_demo.py:358; src/scripts/render_html_demo.py:1130; src/scripts/render_html_demo.py:1136; src/scripts/render_html_demo.py:1212 | `claimsById` stores full claim objects and the popup badge reads `claim.source_mode` from that object. |
| Legacy verdict behavior | Done | src/scripts/render_html_demo.py:271; src/scripts/render_html_demo.py:994; src/scripts/render_html_demo.py:995; src/scripts/render_html_demo.py:996 | Missing `source_mode` becomes `""`; unknown/empty modes return no badge and do not crash. |
| Inert provenance contract | Done | src/specs/verdict_schema.md:116; src/scripts/render_html_demo.py:986; src/scripts/render_html_demo.py:987; src/scripts/render_html_demo.py:988; src/scripts/render_html_demo.py:1075; src/scripts/render_html_demo.py:1212 | New field is used only by `sourceModeBadge()`. Sorting/filtering remain verdict/severity/text based (`src/scripts/render_html_demo.py:320`, `src/scripts/render_html_demo.py:321`, `src/scripts/render_html_demo.py:1112`, `src/scripts/render_html_demo.py:1113`). |
| HTML escaping | Done | src/scripts/render_html_demo.py:997; src/scripts/render_html_demo.py:1084; src/scripts/render_html_demo.py:1212 | Badge label/title are passed through `escapeHtml`; mode is only used as a key into the fixed `SOURCE_MODE` map. |
| Python `.format()` brace safety | Done | src/scripts/render_html_demo.py:375; src/scripts/render_html_demo.py:389; src/scripts/render_html_demo.py:630; src/scripts/render_html_demo.py:989; src/scripts/render_html_demo.py:997 | Added CSS/JS braces are doubled inside the Python format template. I also ran a non-mutating template `.format()` smoke check successfully. |
| `claims_ledger.md` source_mode column | Done | docs/plans/feature-paperclip-first-architecture.md:47; src/templates/claims_ledger.md:28; src/templates/claims_ledger.md:29 | Summary table includes `Source mode` with matching separator width. |
| `claims_ledger.md` enum documentation near top | Done | docs/plans/feature-paperclip-first-architecture.md:47; src/templates/claims_ledger.md:12; src/templates/claims_ledger.md:18 | Top bullet documents all three enum values and states provenance is inert. |

## Critical Drift
- None.

## Missing Pieces
- None within this Phase-5 render/ledger slice.

## Contract Violations
- Severity: Minor | Color-key contract drift | The plan says `paperclip = green, pdf = blue, pdf_ocr_fallback = yellow` (`docs/plans/feature-paperclip-first-architecture.md:145`), but the renderer maps `pdf` to slate/gray `#64748b` (`src/scripts/render_html_demo.py:991`). Required fix: change the `pdf` badge color to a blue value.

## Test Gaps
- Phase-5 smoke not shown in the diff | The smoke plan calls for a DOM/state render check: "assert the `source_mode` badge from parsed JSON / DOM state, not a substring in the rendered HTML" (`docs/plans/feature-paperclip-first-architecture.md:214`). This repo has no unit-test suite (`docs/claude_ops.md:22`, `docs/claude_ops.md:23`), and the diff contains no recorded browser/DOM verification. Suggested follow-up: run the renderer on a small fixture containing `paperclip`, `pdf`, `pdf_ocr_fallback`, and legacy missing `source_mode`, then inspect `window.__DATA__` / DOM badges.

## Defensible Deviations
- Popup badge addition | The plan explicitly asks for a badge per claim row (`docs/plans/feature-paperclip-first-architecture.md:145`); adding the same badge to the detail popup (`src/scripts/render_html_demo.py:1212`) is extra but defensible because it is display-only and uses the same source-of-truth claim object.
- Legacy 1.0 graceful display | The schema bump is hard for validation (`src/specs/verdict_schema.md:196`), but the renderer intentionally renders no badge for unknown/empty modes (`src/scripts/render_html_demo.py:994`, `src/scripts/render_html_demo.py:996`). This is a defensible viewer resilience improvement and does not weaken schema validation.

## Suggested Code Edits
- `src/scripts/render_html_demo.py:991` — change the `pdf` entry's color from `#64748b` to a blue swatch, for example `#2563eb`, to match `pdf = blue` in the Phase-5 spec.

## Questions For The Author
- None.

## Audit Trail
- docs/claude_ops.md
- docs/plans/feature-paperclip-first-architecture.md
- src/specs/verdict_schema.md
- src/scripts/render_html_demo.py
- src/templates/claims_ledger.md
- Unstaged diff from `git diff -- src/scripts/render_html_demo.py src/templates/claims_ledger.md`
- Staged diff from `git diff --staged -- src/scripts/render_html_demo.py src/templates/claims_ledger.md`
