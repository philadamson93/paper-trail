Reference: docs/claude_ops.md

# v1 blindspot mitigations — rigor gaps in `/paper-trail` and `/ground-claim`

## Context

After shipping the `/paper-trail` orchestrator and the strengthened `/ground-claim` subagent instructions, a pre-test blindspot audit surfaced 10 gaps that could produce unreliable verdicts or corrupt artifacts. This plan covers 9 of them (all except #10, retraction checks — deferred as low-priority relative to implementation cost).

The gaps fall into three rough classes:

- **Data integrity**: concurrent ledger writes that clobber, load-bearing and untested PDF bibliography parser.
- **Agent honesty**: fakeable attestation logs, claim-type misclassification that cascades to lenient search strategies.
- **Coverage**: multi-cite sub-aspect attribution, citation-marker false positives, non-IMRaD paper structures, image-based scanned PDFs.

The user has explicitly prioritized rigor over compute efficiency (see memory `feedback_rigor_over_compute.md`) — mitigations should favor thoroughness over speed. UX polish is owned by a collaborator and is not in scope here (memory `collaborator_ux.md`).

All fixes land in the command prompt files and the template. No runtime changes — the prompts are the product.

## Goal

Address 9 of the 10 blindspots in two sequenced rounds.

- **Round 1** (do *before* the DFD smoke test): the cheap fixes that close the worst data-integrity and agent-honesty holes.
- **Round 2** (do *after* the DFD smoke test): moderate-cost fixes where first-run data will sharpen priorities.

Item #10 (retraction checks) is deferred to a separate future plan — low real-world impact for typical modern papers, and it requires a new API integration with its own design questions.

## Approach

### Round 1 — before the DFD smoke test

#### #3 — Concurrent ledger clobbering (data integrity, top priority)

Problem: Batched subagents write to `ledger.md` via `Edit` / `Write` concurrently; nothing serializes them; last write wins.

Fix: Each grounding subagent writes a single per-claim file to `<output-dir>/.inflight/<claim_id>.md`. After every batch returns, the main orchestrator merges `.inflight/*.md` into `ledger.md` sequentially, then deletes the merged inflight files. No concurrent writes to the same file, and partial progress survives a crashed subagent.

Files: `paper-trail.md` (Phase 3.3 — Concurrent ledger writes); `ground-claim.md` (Step 5 — add inflight-file spec).

#### #1 — Fakeable attestation (agent honesty)

Problem: The Step 2 attestation log is self-reported. An agent that skims the abstract and invents plausible-looking attestation fields passes.

Fix: Add a **verifier probe** phase. After a subagent produces a verdict, spawn a lightweight verifier subagent that:

1. Reads the entry's attestation log.
2. Picks one "Specific check" line at random (e.g., "Table 2 rows for dataset sizes").
3. Opens the cited PDF to the claimed page/table and confirms the quoted passage exists (or explicitly is absent as described for UNSUPPORTED).
4. If the passage is absent or materially different from what the attestation claimed, writes a new flag `UNVERIFIED_ATTESTATION` and queues the entry for re-grounding.

Default: run the verifier against every claim for v1 (rigor > compute). Add a `--verifier-sample=<pct>` flag to tune this once we have cost data; not a v1 default.

Files: `ground-claim.md` (new "Attestation verification" section; new `UNVERIFIED_ATTESTATION` flag in the Flag table); `paper-trail.md` (Phase 3.5 — Attestation verification, after claim-grounding and before Phase 4 triage); `templates/claims_ledger.md` (taxonomy).

#### #5 — Multi-cite sub-aspect resolution (coverage)

Problem: "Prior work has explored X [5, 12, 17]" produces three entries (one per citekey) but the prompt doesn't say how each citekey attaches to a sub-aspect of X.

Fix: Add a ledger field `Sub-claim attributed:` for multi-cite entries. The grounding subagent states which slice of the parent claim this citekey supports. When genuinely unclear, return `AMBIGUOUS` with "candidate sub-aspects" in the reasoning; the triage pass will resolve.

Files: `ground-claim.md` (Step 5 — entry spec; Multi-cite citations section — reinforcement).

#### #6 — Citation-marker false positives (coverage)

Problem: Phase 3.1 scans for citation markers; bare parenthetical years (e.g., "data from 2014") and some footnote markers masquerade as cites.

Fix: Explicit disambiguation heuristics in Phase 3.1:

- **Author-year**: require pattern `(Name[, et al.][,] YYYY[a-z]?)` or `Name[, et al.][,] (YYYY[a-z]?)` — bare `(YYYY)` without a name token is not a citation.
- **Numbered**: every `[N]` must resolve to a `refs.bib` entry; unresolved numbers are recorded in `parse_report.md` as "possibly not a citation" and are NOT queued for grounding.
- **Superscript**: auto-detect the paper's citation style from the first confirmed marker; enforce consistency thereafter.
- Low-confidence markers surface in `parse_report.md` with line/page references so a human can spot-check.

Files: `paper-trail.md` (Phase 3.1 — Claim extraction expansion).

#### #8 — Classification cascade (agent honesty)

Problem: Step 1 of `/ground-claim` classifies a claim into DIRECT / PARAPHRASED / FRAMING / etc. Step 2's search rigor branches on this. A misclassified DIRECT-as-FRAMING gets the lowest evidence bar — real errors escape.

Fix:

- Step 1 outputs a classification **confidence**: `high` / `medium` / `low`.
- Medium / low confidence → apply the **strictest** search strategy available (default to DIRECT's strategy regardless of the tentative type).
- After Step 2 finds (or fails to find) evidence, self-check: does the evidence fit the classified type? If not, re-classify and re-search. This loop runs at most twice to bound cost.

Files: `ground-claim.md` (Step 1 — confidence output; Step 2 — strict-default branch + re-classify self-check).

### Round 2 — after the DFD smoke test

#### #2 — Source PDF exceeds subagent context

Problem: Phase 3 subagent reads the whole cited PDF in one pass. Long papers (30+ pages, theses, review articles, papers with long supplements) may exceed the subagent's context — causing silent truncation. The "read the whole paper" requirement becomes a lie.

Fix: Pre-read branch in the grounding subagent:

1. First tool call: extract PDF page count.
2. If `pages ≤ 25`: read in one pass per existing spec.
3. If `pages > 25`: chunked-read mode:
   - Read the table of contents / bookmarks / detected section headers.
   - Process each section in sequence, writing per-section notes to `<output-dir>/.inflight/<claim_id>.notes.md`.
   - After all sections are read, synthesize the verdict from the accumulated notes.
   - Attestation log enumerates sections covered *with* per-section quote snippets — no section left unaccounted for.
4. Threshold `25` is tunable; placed in a "Paper-length handling" subsection so we can adjust without hunting through prose.

Files: `ground-claim.md` (Step 2 — extend Minimum reading requirement with chunked-read branch); `paper-trail.md` (Phase 3.2 — point to the chunked-read spec).

#### #4 — Parser load-bearing, untested

Problem: Phase 0's PDF bibliography parsing drives every downstream phase. If it misses 30% of refs, Phases 1–3 proceed on a partial list with no signal that something is missing.

Fix:

- **Dual-source extraction** in Phase 0:
  - (a) PDF parse (existing).
  - (b) CrossRef `/works/<DOI>` reference list for the input paper's DOI (when available).
- Cross-check counts and entry metadata; diffs are recorded in `parse_report.md` as "parser diff".
- **Confirmation gate** after Phase 0: print `"Parsed N refs from PDF; CrossRef reports M for DOI <...>. Does N match the count printed in the paper?"` via `AskUserQuestion`. Options: `confirm` / `pause for review` / `override count and continue`.

Files: `paper-trail.md` (Phase 0 — Step 0.2 dual-source; new Step 0.5 confirmation gate).

#### #7 — Paper structure assumption

Problem: "Read abstract / intro / methods / results / discussion / conclusions" assumes IMRaD structure. Review papers, math papers, theses, short letters, opinion pieces don't match. Agents confronted with a non-IMRaD paper either fail the checklist or fake-check it.

Fix: Replace the prescriptive section list with "read the paper's actual structure":

- Detect structure from PDF bookmarks / section headers / outline where present.
- Map each found section to a functional role (methods-ish, results-ish, framing) where the role is obvious; otherwise treat as "content section".
- Attestation checklist enumerates *actual* sections found in *this* paper, not a hypothetical IMRaD template.
- For unstructured papers (single-column letters, no headers), require page-by-page reading with per-page attestation.
- Keep the existing behavior for recognizable IMRaD structure — it remains the common case and the most prescriptive checklist is still the right default when applicable.

Files: `ground-claim.md` (Step 2 — Minimum reading requirement overhaul).

#### #9 — Image-based / scanned PDFs

Problem: `pdftotext` returns empty on scanned PDFs; prompts assume text is extractable. Silent failure mode — the agent might declare UNSUPPORTED on a paper it literally couldn't read.

Fix:

- Detect early: after first PDF text extraction, if text-length-per-page is below a threshold (e.g., `< 200 chars/page`), flag the PDF as image-based.
- OCR fallback chain:
  1. `tesseract` if available on PATH.
  2. macOS `shortcuts run "Extract Text From PDF"` if available.
  3. If neither is available → mark entries from this PDF as `NEEDS_OCR` and pause with guidance for the user to OCR externally and drop the extracted text back.
- Record OCR method (and its success) in `parse_report.md` so users know how to calibrate trust in the downstream verdicts.

Files: `paper-trail.md` (Phase 0 — PDF read early-check); `ground-claim.md` (Step 2 — PDF read early-check).

## Files to Modify / Create

- **`.claude/commands/paper-trail.md`** — Round 1: Phase 3.1 citation-marker disambiguation (#6), Phase 3.3 inflight-file layout (#3), new Phase 3.5 Attestation verification (#1). Round 2: Phase 0 dual-source + confirmation gate (#4), Phase 3.2 pointer to chunked-read (#2), Phase 0 image-based-PDF detection (#9).
- **`.claude/commands/ground-claim.md`** — Round 1: Step 1 confidence output + Step 2 strict-default branch (#8), Step 2 sub-aspect attribution guidance (#5), Step 5 inflight-file spec (#3), new Attestation verification section + new `UNVERIFIED_ATTESTATION` flag (#1). Round 2: Step 2 chunked-read branch (#2), Step 2 Minimum reading overhaul for non-IMRaD (#7), Step 2 image-based-PDF detection (#9).
- **`templates/claims_ledger.md`** — add `UNVERIFIED_ATTESTATION` to flag taxonomy (Round 1).
- **`README.md`** — brief note in Features section on verifier pattern and chunked reads once both rounds land. Docs-only, last step.

Do **not** touch:
- `verify-bib.md` — retraction checks (#10) are deferred; file is otherwise unaffected.
- `init-writing-tools.md` — `/paper-trail` does not depend on init; no cross-coupling.
- `examples/claims_ledger_example.md` — existing example remains valid; add a new example showcasing `UNVERIFIED_ATTESTATION` only after a real run produces one.

## Open Questions

- **Verifier sampling for v1**: default to full verification (every claim)? My recommendation is yes (rigor > compute), with `--verifier-sample=<pct>` available for future tuning. Worth confirming.
- **Chunked-read page threshold**: 25 pages is a guess. Tunable; placed in a dedicated subsection so it can be moved without hunting. First run on real papers will tell us if it needs adjustment.
- **Table-of-contents detection fallback**: most scientific PDFs have internal bookmarks; those that don't need header-detection from `pdftotext` output. No plan to use a library for this in v1 — we leaf on best-effort heuristics and flag uncertainty in the attestation log.
- **CrossRef reference-list reliability**: varies by publisher. Treated as a cross-check signal, not ground truth.
- **OCR availability**: `tesseract` isn't everywhere. We fall back gracefully; users without OCR see `NEEDS_OCR` and guidance.

## Verification

No unit-test suite (per `docs/claude_ops.md`). Verification is end-to-end against a public-ish test paper:

**Test PDF**: `/Users/pmayankees/Documents/Stanford/RSL/Chaudhari_Lab/MRM/Magnetic Resonance in Med - 2025 - Adamson - Using deep feature distances for evaluating the perceptual quality of MR image.pdf` — one of the user's own 2025 MRM papers, so ground-truth reference metadata and claim accuracy are knowable, and parser / verifier output can be checked against the real bibliography and known source papers.

### After Round 1

1. `/paper-trail <DFD-paper>`. Confirm:
   - No concurrent-write corruption: `ledger.md` contains one entry per `(claim, citekey)` tuple; no duplicates, no overwritten entries.
   - `.inflight/` is empty after the run completes (all per-claim files merged and cleaned up).
   - Every grounding verdict is accompanied by a verifier probe result; any `UNVERIFIED_ATTESTATION` flags surface in the Critical findings header.
   - Multi-cite sentences produce one entry per `(claim, citekey)` with a populated `Sub-claim attributed:` field.
   - Citation-marker extraction does not generate phantom claims from bare parenthetical years in the body text.
   - Low-confidence classifications ran the strictest search strategy (inspect a sample of ledger entries — they should show the DIRECT-style search log even if their final classification is BACKGROUND/FRAMING).
2. Manual spot-check of 3 grounding verdicts against the actual source PDFs. Did the verifier catch anything? Did it miss anything obvious?
3. If all above pass → proceed to Round 2.

### After Round 2

1. Re-run `/paper-trail` on the DFD paper (same output-dir, so resumability is also tested). Confirm:
   - `parse_report.md` shows the dual-source counts (PDF-parsed vs CrossRef).
   - Confirmation gate after Phase 0 fired and was handled by the user.
   - If any cited PDF is > 25 pages, that grounding subagent's attestation log shows chunked-read section notes.
   - If any cited PDF is image-based, the OCR fallback engaged (or `NEEDS_OCR` was raised with guidance).
   - Non-IMRaD structure (if present among cited papers) was handled without the attestation checklist breaking.
2. Manual review of 2 chunked-read verdicts: do the per-section notes track the real structure of the source paper?

Pre-commit implementation-review agent (per `docs/claude_ops.md`) runs after each round to check plan fidelity and docs updates.

---

**Status**: plan drafted. Round 1 implementation begins next.
