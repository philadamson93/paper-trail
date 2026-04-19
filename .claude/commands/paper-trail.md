The single entry point for the `paper-trail` workflow. Given a paper to audit, extract its reference list, verify bib metadata, fetch open-access source PDFs, and ground every in-text citation against its source. Produces a self-contained audit artifact.

Two workflow modes:

- **Reader mode** (default) — audit someone else's paper end-to-end from a single PDF. Used for peer review, literature vetting, skeptical reading. Self-contained: no project config, no manuscript editing.
- **Author mode** — audit your own in-progress manuscript (a `.tex` file + `.bib` + source PDFs in a directory). Orchestrates `/init-writing-tools` (first run only), `/verify-bib`, `/fetch-paper`, and `/ground-claim` against your writing project; writes to `claims_ledger.md` at the project root per the existing author-mode conventions.

Both modes share the per-claim workflow (Step 1 classify → Step 2 locate evidence with full attestation → Step 3 support level → Step 4 remediation → Step 5 ledger write), the same taxonomies, and the same Phase 3.5 attestation verifier. The difference is **who owns the paper** and therefore what gets written where.

## Core principle: one orchestrator, two workflows

- **Reader mode** writes everything inside a single `<output-dir>/`. Never touches project-level config. If a project `claims_ledger.md` exists in cwd, ignore it — reader mode is for *external* papers.
- **Author mode** writes to the project's existing `claims_ledger.md` (or bootstraps one via `/init-writing-tools` on first run). Never edits the manuscript; all remediations are surfaced as proposals for the user to accept.
- Both modes reuse the ledger schema at `templates/claims_ledger.md` verbatim.

## Invocation forms

Reader mode (default when a PDF path is given):

- `/paper-trail` — fully interactive; prompts for every setting (including which workflow).
- `/paper-trail <path-to-pdf>` — reader mode against that PDF; prompts for remaining settings.
- `/paper-trail <path-to-pdf> --scope=single` — single-claim grounding scope (see below).
- `/paper-trail <path-to-pdf> --skip-paywalled` — don't block on paywalled refs; mark them `NEEDS_PDF` and continue.
- `/paper-trail <path-to-pdf> --skip=key1,key2` — exclude specific citekeys from fetch + grounding.
- `/paper-trail <path-to-pdf> --sequential` — process one item at a time (rate-limited MCPs, small context budgets).
- `/paper-trail <path-to-pdf> --batch-size N` — override parallel batch size (default 10).
- `/paper-trail <path-to-pdf> --recheck` — re-verify all existing ledger entries in the target output-dir.
- `/paper-trail <path-to-pdf> --triage` — run interactive triage on `AMBIGUOUS` entries in an existing output-dir (no re-grounding).
- `/paper-trail <path-to-pdf> --fetch-substitute=<never|ask|always>` — policy for Phase 2 when a target paper's primary URL is paywalled but a related-but-not-identical paper (e.g., an arXiv preprint of the same work, an earlier arXiv version, a workshop paper vs. a later journal version) is available. Default: `ask`.

Author mode:

- `/paper-trail --author` — author mode against the current writing project (expects a `.tex` file + `.bib` + source PDFs in cwd, or config in `claims_ledger.md`).
- `/paper-trail --author path/to/document.tex` — author mode against a specific manuscript file.
- `/paper-trail --author --scope=single` — ground one specific claim (prompts for claim description).
- All the `--skip-paywalled` / `--sequential` / `--batch-size` / `--recheck` / `--triage` / `--fetch-substitute` flags apply in author mode too.

## Initial questions

Use `AskUserQuestion` for any value not provided via args or reliably inferrable from the working directory. Skip a question when the answer is unambiguous from context.

1. **Workflow** — `reader` (default) or `author`. Skip this question if the invocation already specifies: presence of `--author` or a `.tex` path implies author mode; a PDF path argument implies reader mode.
2. **Input** — what paper are we auditing?
   - **Reader mode:** the input PDF. Offer two ways to provide it:
     - **Paste a path** (absolute or relative).
     - **Search by name** — ask for the paper's filename or title fragment (e.g., "deuterium metabolic imaging" or "DMI Adamson 2023"). Run a filesystem search (`Glob` + lightweight `find`) against likely locations (`~/Documents`, `~/Downloads`, `~/Desktop`, and cwd). If multiple candidates match, let the user pick via `AskUserQuestion`; if zero match, iterate on the search fragment. Never silently pick a PDF — always confirm.
   - **Author mode:** path to the manuscript `.tex` file (or confirm auto-detected one in cwd). If no `claims_ledger.md` exists at the project root, offer to run `/init-writing-tools` first.
3. **Output location**
   - **Reader mode:** output directory, default `./paper-trail-<pdf-stem>/`, confirmable or overridable.
   - **Author mode:** uses the existing project `claims_ledger.md`; no separate output dir.
4. **Scope** — grounding scope for this run: `full` (default — ground every claim) or `single` (ground one claim the user describes).
5. **Institutional access** — short free-text note (e.g., "university library proxy", "personal only"). Used by Phase 2 paywall prompts. If a project `claims_ledger.md` exists with this field, offer its value as the default.
6. **(single scope only)** — "Describe the claim you want to ground" — free text. Interpret semantically against the input PDF (reader mode) or the manuscript (author mode); do not require a verbatim quote.

Keep the question count at or below these six (not counting the internal search-candidates pick for Q2 when search-by-name is chosen). Anything else is inferred or set to a sensible default.

## Artifact layout

`<output-dir>/`:

- `ledger.md` — audit artifact (**human-readable view, rendered from `ledger/claims/*.json`**). Reuses `templates/claims_ledger.md` schema with the additions below.
- `ledger/claims/<claim_id>.json` — **source-of-truth verdict** per claim. Schema: `.claude/specs/verdict_schema.md`. The orchestrator renders `ledger.md` from these files after every merge; edits to `ledger.md` are overwritten on the next render.
- `ledger/evidence/<claim_id>.json` — extractor output (Pass 1). Verdict fields are `PENDING`; used by the adjudicator in Pass 2 and retained for verifier bounces.
- `ledger/verifications/<claim_id>__<sub_claim_id>.json` — verifier spot-check output (Phase 3.5).
- `refs.bib` — PDF-parsed BibTeX (Phase 0).
- `refs.verified.bib` — bib-audit-corrected copy emitted by Phase 1 (Phases 2–3 prefer this if present).
- `pdfs/<citekey>.pdf` — fetched source PDFs.
- `pdfs/<citekey>/` — per-PDF **ingest handle** (Phase 2.5 output): `meta.json`, `content.txt`, `sections/*.txt`, `figures/*.png`, `figures/index.json`, `ingest_report.json`. Schema: `.claude/specs/ingest.md`.
- `parse_report.md` — bibliography parser diagnostics + ingest-mode summary (how many refs ingested via GROBID vs fallbacks).
- `demo.html` — standalone HTML viewer rendered from the verdict JSONs (PDF.js viewer + claims sidebar). Produced by Phase 5.
- `trace/<subagent_id>.jsonl` — per-subagent trace log for observability (see "Trace log").

### Ledger additions for reader mode

Beyond the standard `claims_ledger.md` frontmatter, include:

```yaml
---
input_paper:
  path: <absolute path to input PDF>
  title: <resolved title>
  authors: <resolved author list>
  doi: <DOI if known>
  year: <year>
workflow: reader | author
scope: full | single
pdf_dir: pdfs/
pdf_naming: "{citekey}.pdf"
bib_files:
  - refs.bib
institutional_access: <from Q4>
last_bootstrap: <today's ISO date>
---
```

Above the `## Summary` table, render a `## Critical findings` section that surfaces:

- `CRITICAL` bib-audit entries (fabricated / chimeric / non-resolving DOIs) from Phase 1.
- `CONTRADICTED` and `UNSUPPORTED` claim entries from Phase 3.

Each finding links to its detail block lower in the file. This is the "do I need to panic" view for the reader.

## Phase 0 — Bibliography extraction

Goal: produce `refs.bib` and `parse_report.md`.

### Step 0.0 — Verify PDF is readable

Before anything else, extract text from the input PDF and confirm it is readable:

- Use `pdftotext`, the `Read` tool, or equivalent.
- Count extracted characters per page. If the average is below ~200 chars/page (or extraction returns empty), the PDF is image-based (scanned).
- **Image-based PDF handling:** attempt OCR fallback — `tesseract` on PATH, or macOS `shortcuts run "Extract Text From PDF"`. If OCR succeeds, proceed with OCR text and record the OCR method (and any confidence signal) in `parse_report.md`. If no OCR is available → emit a structured error telling the user to OCR externally and re-invoke; do **not** proceed into Phase 1/2/3 on an unreadable PDF.
- Record text-extraction method and per-page character counts in `parse_report.md`.

### Step 0.1 — Input-paper metadata
- Extract the input paper's title, authors, DOI (if printed on page 1 or resolvable from the filename).
- Record in the ledger frontmatter.

### Step 0.2 — Parse bibliography from the PDF
- Locate the "References" / "Bibliography" / "Literature Cited" section in the input PDF. Scan from the end backwards; stop at the first recognizable section header.
- Auto-detect the style:
  - **Numbered** — entries prefixed by `[N]`, `N.`, or superscript numbering that aligns with in-text markers.
  - **Author-year** — entries begin with author surname(s) + year.
  - **Other** — flag as low-confidence in `parse_report.md` but still attempt extraction.
- For each entry, extract whichever fields are recoverable: authors, title, venue, year, volume/issue/pages, DOI, arXiv ID.
- Derive a citekey per entry:
  - Author-year style → `<firstauthor><year>` (e.g., `smith2023`), with a suffix letter for collisions.
  - Numbered style → `ref<N>` initially; promote to `<firstauthor><year>` once authors/year are extracted.

### Step 0.3 — Cross-check count against an authoritative source

The PDF parser in Step 0.2 is fallible — bibliography layouts vary and OCR introduces noise. Do a **count-only** reconciliation against an authoritative list to catch missed entries, but do **not** enrich individual entries' metadata here.

- If the input paper has a resolvable DOI, fetch its reference list from CrossRef (`https://api.crossref.org/works/<DOI>` — the `reference` array) and / or from PapersFlow / OpenAlex. This is the authoritative "who did the authors actually cite" list, to the extent publishers report it.
- Compare counts. If the PDF-parsed count and CrossRef-reported count differ, record the diff in `parse_report.md` (e.g., "PDF parser found 42 refs, CrossRef reports 45").
- For any entry that CrossRef/OpenAlex reports but the PDF parser missed, add the missing entry to `refs.bib` using CrossRef metadata and mark it `parser_source: crossref_count_fill`. Flag low-confidence in `parse_report.md` — the authoritative source asserts it, but we didn't see it in the PDF's reference list.

**Do not enrich the metadata of PDF-parsed entries here.** Per-entry metadata enrichment (resolving incomplete authors, correcting swapped surnames, filling missing DOIs, etc.) is the job of Phase 1's `/verify-bib`, which compares the printed metadata against CrossRef/arXiv/PapersFlow and raises each disagreement as a **bib-audit finding**. If Phase 0 silently corrects a chimeric author list against CrossRef, Phase 1 has nothing to flag and a real authoring error goes unreported. Chimeric entries, author-swap typos, and title truncations in the printed bibliography are exactly the kind of thing this tool exists to surface — it must see them before it corrects them.

### Step 0.4 — Emit artifacts

**Emit a PDF-parsed `refs.bib`**, not an enriched one:

- Each entry's fields reflect what the PDF actually printed: whatever the parser could recover for authors, title, venue, year, volume/issue/pages, DOI (if printed), arXiv ID (if printed). For fields the parser couldn't recover, omit the field rather than inventing a value from CrossRef.
- Each entry carries a `parser_source` field: `pdf_parsed` (parsed from the PDF bibliography), `crossref_count_fill` (added in Step 0.3 because CrossRef reported it but the parser missed it), or `unresolved` (the parser could not recover a usable entry; see `parse_report.md` for the raw line).
- Citekeys per Step 0.2's rules — author-year `<firstauthor><year>` or numbered `ref<N>` until authors/year extracted.

Phase 1 will read this bib, enrich and audit each entry, and (if any corrections were accepted during audit) emit a `refs.verified.bib` for Phases 2–3 to consume. Phases 2–3 **must prefer `refs.verified.bib` over `refs.bib` if the former exists**, because it carries the authoritative metadata needed for reliable PDF fetching and claim matching.

Write `parse_report.md` with:
  - Total entries parsed from PDF; total from authoritative source (CrossRef / PapersFlow); diff count.
  - Total with DOI printed in the PDF; total flagged low-confidence.
  - Auto-detected bibliography style.
  - Explicit list of unparseable / low-confidence lines by line number so a human can spot-check.
  - List of entries added from the authoritative source that the PDF parser missed (`crossref_count_fill`).

Do **not** include per-entry parser diffs (authoritative vs parsed) in `parse_report.md` — those now live in Phase 1's bib-audit findings (as MODERATE / MINOR entries against each disagreement). Mixing them into `parse_report.md` duplicates surfacing and obscures which issues the user still has to action.

### Step 0.5 — Confirmation gate

Before proceeding to Phase 1, surface the parse results to the user via `AskUserQuestion`:

- **Question**: "Phase 0 parsed **N** references from the PDF; CrossRef reports **M** for this DOI. Does **N** match the reference count printed in the paper's bibliography?"
- **Options**:
  - `Confirm — proceed to Phase 1` (counts match or user has eyeballed `parse_report.md`).
  - `Pause for review` (user wants to inspect `parse_report.md` before continuing — exit cleanly; resume with same output-dir later).
  - `Override count — proceed with N (known-partial)` (user accepts partial and wants to continue).

If CrossRef data is unavailable (no DOI, API down), ask only for PDF-parsed N and let the user eyeball.

This confirmation gate is the single place where parser quality bubbles up to the user before it silently contaminates downstream phases.

### Large-paper guardrail
If more than 200 references are parsed, print the count and confirm before continuing to Phase 1 (in addition to Step 0.5's gate). Offer the user a chance to `--skip` or narrow scope.

## Phase 1 — Verify bib

Run `/verify-bib` logic against `<output-dir>/refs.bib` (the PDF-parsed bib from Phase 0). Phase 1 is where printed-vs-authoritative disagreements become **findings** the user can see.

- Spawn one subagent per reference, batched per the configured batch size.
- Each subagent follows the `/verify-bib` per-entry workflow (existence, author match, bibliographic fields, preprint upgrades, duplicates) and returns a severity-classified result.
- For every disagreement between the PDF-parsed entry and the authoritative source (CrossRef / arXiv / PapersFlow), raise an explicit finding:
  - **Author-list mismatch** — e.g., printed authors `Florian K, Jure Z, Anuroop S` but CrossRef returns `Knoll F, Zbontar J, Sriram A, …` with 23 authors total. Severity `CRITICAL` for chimeric entries (first/last names swapped, names invented, author count wrong by more than ±1).
  - **Title truncation / fabrication** — printed title differs from authoritative title by more than a subtitle or trailing punctuation. Severity `MODERATE`.
  - **Wrong year / venue** — printed year off by more than 1 from the authoritative issued date; wrong journal / conference. Severity `MODERATE`.
  - **Missing DOI** — authoritative source has a DOI; bib entry does not. Severity `MINOR`.
  - **Preprint→published upgrade** — bib entry cites arXiv; authoritative source has a peer-reviewed publication. Severity `MINOR`.
  - **Duplicates** — two bib entries resolve to the same authoritative paper. Severity `MODERATE`.
- Collect results and populate the ledger's `## Critical findings` section with every `CRITICAL` entry and a structured MODERATE / MINOR summary.
- **Emit a corrected bib for downstream phases.** After all subagents return, write `<output-dir>/refs.verified.bib`:
  - Start from `refs.bib` (the PDF-parsed version).
  - For each entry with a non-CRITICAL authoritative correction available, apply the correction to `refs.verified.bib` (not to `refs.bib`) and record the change in the entry's BibTeX as `audit_corrected: "<field>=<printed> -> <authoritative>"`.
  - For CRITICAL entries (chimeric author lists etc.), *do not* silently replace — keep the printed entry in `refs.verified.bib` with the original fields, and add an `audit_flag: CRITICAL` annotation plus a comment pointing to the ledger finding. The user must decide whether to accept the correction.
  - Phases 2 and 3 **must read `refs.verified.bib` if it exists**, falling back to `refs.bib`. This is how the authoritative metadata reaches fetch / grounding without silently overwriting the audit surface.
- Do **not** auto-apply `--fix` corrections to `refs.bib` in reader mode. Raise, don't fix. (The user is not the author — they don't get to correct the input paper's bib.) `refs.verified.bib` is an internal tool artifact for Phases 2–3, not a corrected copy of the input paper's bibliography — this distinction matters for audit traceability.

## Phase 2 — Fetch PDFs

For each unique citekey in `refs.bib`:

- If `<output-dir>/pdfs/<citekey>.pdf` already exists → mark "already present" and skip.
- Else spawn a subagent invoking `/fetch-paper <citekey>` logic (batched per the configured batch size).
- The subagent follows the existing download-order fallback: `paper-search` MCP → `papersflow` → CrossRef open-access → direct arXiv.
- Save to `<output-dir>/pdfs/<citekey>.pdf`.

### Fetch substitution policy

Fetch subagents must never silently substitute a different paper's PDF for the target. But "different paper" is a spectrum — sometimes a paywalled journal DOI has an open-access preprint at arXiv that is substantively the same work (same authors, overlapping content, possibly an earlier or later version). Whether to use such a substitute is a user-level design decision, not a tool-level policy.

When a Phase 2 subagent hits a paywall and identifies a candidate substitute (a related but not identical paper at a different URL), it does **not** auto-fetch. Instead it returns a structured substitution candidate to the orchestrator:

```
Substitution candidate for <citekey>:
  Target:      <primary URL — paywalled / unreachable>
  Target DOI:  <if applicable>
  Candidate:   <alternative URL>
  Relationship: <preprint of published | earlier arXiv version | workshop version
                 of later journal | other — describe>
  Risk notes:  <older version may predate published revisions; may have different
                wording, missing figures, or different results — whatever applies>
```

The orchestrator applies the configured `--fetch-substitute` policy:

- **`never`** — mark `<citekey>` as `NEEDS_PDF`; do not fetch the candidate. The user must retrieve the target manually or skip via `--skip-paywalled`.
- **`ask` (default)** — prompt the user via `AskUserQuestion`:
  - Question body: the structured substitution candidate above.
  - Options: `Use substitute` / `Mark NEEDS_PDF` / `Skip this ref`.
  - User's choice is recorded in `parse_report.md` and in every downstream claim entry's attestation log.
- **`always`** — accept the substitute automatically, but record prominently in `parse_report.md` and flag every downstream claim's attestation log with the substitution and its provenance risk.

**Regardless of policy**, any substitution that occurs is **always logged** in both `parse_report.md` and the attestation log of every claim grounded against that substituted PDF. Provenance is never hidden. Downstream grounding subagents must read the substitution note and include a per-claim caveat in their attestation logs.

### Post-fetch paywall handling

After all fetch subagents return, print a structured paywalled/failed list:

```
N refs could not be retrieved:
  <citekey>  (DOI: <doi>)  — paywalled
  <citekey>  — retrieval failed: <reason>
  ...

Total fetched: M / (M+N)
```

- If `--skip-paywalled` was passed → mark those refs' eventual claim entries as `PENDING` with `NEEDS_PDF`, and continue to Phase 3.
- Otherwise → stop and surface two options to the user:
  1. Drop PDFs into `<output-dir>/pdfs/<citekey>.pdf` via institutional access, then re-invoke `/paper-trail <pdf>` to resume.
  2. Re-invoke with `--skip-paywalled` to continue without them.

Never suggest Sci-Hub, LibGen, or similar. Inherit the `/fetch-paper` policy.

## Phase 2.5 — Ingest

After every successful fetch, run the ingest pipeline to turn the PDF into Phase 3's structured handle. Spec: `.claude/specs/ingest.md`.

### Pre-flight — GROBID availability check

Before the first ingest call:

1. Probe `http://localhost:8070/api/isalive` (or the `--grobid-url` override).
2. If it responds `true` → proceed with full-fidelity ingest.
3. If not → emit a one-time warning: *"GROBID not available — ingest will fall back to `pdftotext_fallback` mode (no per-section structure; figures still extracted). To enable full ingest, run `docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2`."* Continue; do **not** block on GROBID.

Per-run summary of ingest modes lands in `parse_report.md` so downstream consumers know which handles are `grobid` vs `pdftotext_fallback` vs `ocr_fallback`.

### Per-ref ingest

For each `<citekey>` with a fetched `<output-dir>/pdfs/<citekey>.pdf`:

1. If `<output-dir>/pdfs/<citekey>/ingest_report.json` exists with `success: true`, skip (resumability).
2. Else invoke `.claude/scripts/ingest_pdf.py --pdf <path>.pdf --citekey <citekey> --out-dir <output-dir>/pdfs/<citekey>/`.
3. Record the resulting `ingest_mode` per citekey.

### Failure handling

- `ingest_mode: grobid` → full-fidelity handle; all Phase 3 primitives available.
- `ingest_mode: ocr_fallback` → content.txt from OCR; no sections; figure extraction still attempted. Phase 3 dispatch marks claims against this handle with a trust-adjusted confidence.
- `ingest_mode: pdftotext_fallback` → flat text, no sections, figures still extracted. Serviceable for most claim types; DIRECT claims against numerical tables may need vision inspection.
- `ingest_mode: error` → mark every claim citing this source `PENDING` with `NEEDS_PDF`; surface in the run report.

Ingest is idempotent. Re-invocation reuses the cached handle unless `--force-ingest` is passed.

## Phase 3 — Ground claims

### Step 3.1 — Claim extraction
- Scan the input PDF body text. Exclude the references section, figure/table captions, and any clearly-marked supplementary / appendix sections.
- Detect inline citation markers matching the auto-detected style from Phase 0: author-year `(Author et al., YYYY)`, numbered `[N]`, or superscript numerals.

### Disambiguation heuristics (prevent phantom citations)

Citation-marker detection in running prose is noisy. Year-in-parens in body text (`"data from 2014"`, `"since 2008, …"`) and superscript footnote markers can masquerade as citations. Apply these heuristics to avoid generating phantom claims:

- **Author-year style**: a match requires an author-name token directly adjacent to the year — one of:
  - `(Surname[, et al.][,] YYYY[a-z]?)`
  - `Surname[, et al.][,] (YYYY[a-z]?)`
  - `Surname et al., YYYY[a-z]?` (narrative form)

  A bare `(YYYY)` or `(YYYY–YYYY)` *without* an adjacent surname token is **not** a citation. Flag it as "possibly not a citation" and do not queue a claim.
- **Numbered style**: every `[N]` or `^N` must resolve to a `refs.bib` entry for which `N` was assigned during Phase 0. Unresolved numbers (reference not found in the parsed bibliography) are recorded in `parse_report.md` with surrounding text and page number, but are **not** queued for grounding. This catches footnote markers and equation numbers misread as citations.
- **Style consistency**: once the paper's citation style is confirmed from the first few clean matches, enforce consistency thereafter. A paper that uses numbered citations throughout and produces a lone author-year match deep in the body is almost certainly a false positive.
- **Context filters**: skip matches that appear inside math environments (between `$...$` or similar delimiters), inside figure/table captions (already excluded above), and inside the references section itself (a reference's own internal citations are not part of *this* paper's claims).

Record low-confidence matches in `parse_report.md` so a human can spot-check; do not queue them for grounding.

### From markers to claims

- Every sentence containing one or more **confirmed** citation markers is a candidate claim.
- Map each marker to the corresponding `refs.bib` citekey.
- For multi-marker sentences (e.g., `[5, 12, 17]`), produce one claim entry per `(sentence, citekey)` pair — matching the existing `/ground-claim` multi-cite semantics. The grounding subagent handling each entry is responsible for determining which *sub-aspect* of the sentence its citekey supports (see `/ground-claim` Step 5 "Sub-claim attributed" field).

### Step 3.1.5 — Validate extracted claims against the manuscript

Before any Phase 3 dispatch, run the claim-extraction validator:

```bash
python3 .claude/scripts/validate_claims.py --run-dir <output-dir>
```

The validator enforces two invariants per extracted claim, with no LLM cost:

- **TEXT_ANCHOR_MISSING** — the claim's `claim_text` must fuzzy-match somewhere in `paper.txt`. If no 3-word content-token window (with up to 3 intervening words) appears in the manuscript, the stored claim_text is paraphrased or fabricated and should not be dispatched.
- **CITEKEY_MARKER_MISMATCH** — once a text anchor is found, the citation markers within ±280 chars of that position must include the `refnum` that the claim's `citekey` resolves to. Range markers like `28–33` are expanded. A mismatch means the claim is attached to the wrong reference.

The validator writes `claim_extraction_report.md` and exits non-zero if any claim flags. Default behavior is **strict** — the orchestrator must pause and surface the report via `AskUserQuestion` when flags exist. Options:

- `Drop flagged claims from this run` — exclude them from Phase 3 dispatch; record in `parse_report.md`.
- `Re-run extraction for flagged claims only` — requeue those claims for Phase 3.1 with a pointed "this claim's text was not found in the manuscript; re-extract the actual sentence" message.
- `Proceed anyway` — dispatch all claims including flagged ones; only use when the user has reviewed `claim_extraction_report.md` and accepted the risk.

Running retroactively against an existing run is safe and informative — the report is diagnostic-only unless piped into a re-extraction pass.

### Step 3.2 — Two-pass dispatch (extractor → adjudicator)

Each claim is processed by **two subagents in sequence**, then a **third verifier subagent** in Phase 3.5. The three dispatch prompts are materialized in `.claude/prompts/` — the orchestrator reads the template, fills `{{slots}}` with per-claim values, and sends the result verbatim. No improvisation at dispatch time. See `.claude/specs/verdict_schema.md` for the exit-JSON contract both passes share.

**Why two passes:** at 50 parallel subagents the single-pass "read PDF → decide verdict" workflow drifts (subagents write Python, invent taxonomies, default to CONFIRMED). Splitting the work keeps each subagent's context narrow:

- **Pass 1 — Extractor** reads the paper handle, gathers evidence. Emits `ledger/evidence/<claim_id>.json` with `verdict` fields left `PENDING`.
- **Pass 2 — Adjudicator** reads only the evidence JSON + the rubric (`verdict_schema.md`), no paper. Emits `ledger/claims/<claim_id>.json` with final verdicts.

Claim IDs (`C001`, `C002`, …) are allocated by the orchestrator before dispatch. Each subagent is handed its assigned ID; concurrent subagents cannot collide.

#### Dispatch inputs

For each claim, the orchestrator computes the dispatch payload:

```json
{
  "claim_id": "C042",
  "run_id": "run_20260418T1234Z",
  "citekey": "hammernik2021",
  "claim_text": "...",
  "manuscript_section": "2.2.3",
  "claim_type_hint": {"type": "PARAPHRASED", "confidence": "medium"},
  "handle": "pdfs/hammernik2021/",
  "ingest_mode": "grobid",
  "co_citekeys": ["chen2022", "sandino2020"],
  "run_output_dir": "<absolute path>"
}
```

— then substitutes each `{{slot}}` in `.claude/prompts/extractor-dispatch.md` with the matching value and sends the filled prompt to the extractor subagent. After validation of its `ledger/evidence/<claim_id>.json`, the orchestrator fills `.claude/prompts/adjudicator-dispatch.md` the same way and dispatches the adjudicator.

#### Grouping

Group claims by cited source paper (citekey). All claims citing the same paper share one ingested handle, so reading-cost amortizes. The extractor processes each claim in the group one at a time (not bulk); the adjudicator runs per-claim. Parallelism is across papers, not across claims within a paper, to keep adjudicator contexts tiny.

#### Refs without a handle

Refs marked `NEEDS_PDF` in Phase 2 or `ingest_mode: error` in Phase 2.5 → orchestrator writes a stub `ledger/claims/<claim_id>.json` with `overall_verdict: PENDING` and `overall_flag: NEEDS_PDF`. No subagent is dispatched for these.

#### Exit-JSON validation

On extractor return:

1. Validate `ledger/evidence/<claim_id>.json` against the schema. On failure, retry once with a pointed error message. On second failure, keep the malformed output at `<claim_id>.json.invalid` and flag the claim `SCHEMA_VIOLATION`.
2. On success, dispatch the adjudicator.

On adjudicator return: same validation → `ledger/claims/<claim_id>.json`. Validation failure blocks Phase 3.5 verification for that claim; proceed with others.

### Step 3.3 — Ledger rendering

After each batch of adjudications returns, the orchestrator re-renders `ledger.md` from all `ledger/claims/*.json` files. The markdown is a derived view:

- Frontmatter (unchanged across runs)
- `## Critical findings` section populated from `overall_flag` in `["CRITICAL", "AMBIGUOUS", "SCHEMA_VIOLATION"]`
- `## Summary` table — one row per `ledger/claims/<claim_id>.json`, columns `| ID | Section | Cite | Type | Support | Source page | Flag | Last verified |`
- `## Details` — one block per claim, rendered from the JSON (claim_text, sub_claims with verdicts + evidence, attestation summary, remediation, source_ref_urls click-through)

Hand-edits to `ledger.md` are **lost on the next render**. If a user wants to annotate an entry, they should do so in the JSON's free-form `nuance` or `history[]` fields.

## Phase 3.5 — Attestation verification (gating)

Every adjudicated claim (regardless of overall verdict, including `CONFIRMED`) is spot-checked by a narrow verifier subagent before its verdict is considered final. The verifier sees only `{claim, one sampled evidence entry, rubric}` — no paper, no other sub-claims — so it can't drift.

Dispatch template: `.claude/prompts/verifier-dispatch.md`.

### Sampling

For each `ledger/claims/<claim_id>.json`:

1. Flatten `sub_claims[*].evidence[*]` into a list.
2. Filter out figure-derived entries (marked `sample_type: "figure"` — out of scope for text verifier).
3. Randomly pick one. If every evidence entry is figure-derived, sample from `attestation.closest_adjacent`.
4. If no evidence at all (e.g., UNSUPPORTED with nothing to verify), skip verification — the adjudicator's closest-adjacent attestation stands.

### Dispatch payload

```json
{
  "claim_id": "C042",
  "run_id": "...",
  "sampled_evidence": { ... one evidence entry ... },
  "handle": "pdfs/hammernik2021/",
  "run_output_dir": "<absolute path>"
}
```

Orchestrator fills `.claude/prompts/verifier-dispatch.md` with these slots.

### Handling results

Verifier emits `ledger/verifications/<claim_id>__<sub_claim_id>.json` with `result ∈ {PASS, PARTIAL, FAIL}` and `verdict_impact`:

- `PASS` / `verdict_impact: none` → verdict stands.
- `PARTIAL` / `flag_unverified_attestation` → patch the verdict JSON's `overall_flag` to include `UNVERIFIED_ATTESTATION`. Verdict itself unchanged.
- `FAIL` / `bounce_to_re_ground` → re-dispatch the claim through extractor + adjudicator. Increment `attempts` on the claim's JSON; after 2 bounces, flag the claim `AMBIGUOUS` with `SCHEMA_VIOLATION` and stop (systematic extractor issue).

### Default

Verify every claim in v1. A `--verify-sample-rate=<pct>` flag may be added later based on cost data; not a v1 default. Rigor beats compute.

### Do not

- Do not auto-correct verdicts based on verifier output. The verifier flags (or bounces for re-grounding); it does not rewrite the verdict directly.
- Do not skip verification on `CONFIRMED` entries — a falsely-confirmed claim is as dangerous as a falsely-denied one.
- Do not let the same subagent produce both the adjudicated verdict and the verification. They must be separate dispatches.

## Phase 4 — Ambiguity triage

After Phase 3 completes, count `AMBIGUOUS` entries in the ledger. `AMBIGUOUS` means the subagent read the cited paper fully (attestation log present) but could not confidently pick between two or more candidate verdicts on the evidence it found — see `/ground-claim` "Ambiguity triage" for the required entry format and semantics.

### When `AMBIGUOUS` entries exist

Prompt the user via `AskUserQuestion`:

- **Question**: "N claim(s) were flagged AMBIGUOUS — the agent read the cited papers fully but couldn't confidently pick a verdict. Triage now or defer?"
- **Options**: `Triage now` (recommended) | `Defer to /paper-trail <pdf> --triage later`

If the user picks "triage now", run the `/ground-claim --triage` workflow inline: iterate through each `AMBIGUOUS` entry, present the claim ID, citekey, evidence quote, candidate verdicts, and reasoning; collect the user's chosen verdict via `AskUserQuestion`; update the ledger with a dated history note.

If the user defers, note the count in the triage report and exit. Re-run `/paper-trail <pdf> --triage` later to pick up where left off.

### `--triage` invocation (standalone)

When invoked with `--triage`, skip Phases 0–3 entirely. Read the existing ledger in the output directory and run only the triage workflow above on `AMBIGUOUS` entries. No new grounding is performed.

## Phase 5 — Render HTML viewer

After Phase 4 completes (or at the end of a `--triage`-only run), render the standalone HTML viewer:

```bash
python3 .claude/scripts/render_html_demo.py --run-dir <output-dir>
```

The script reads `ledger/claims/*.json`, `refs.bib` (or `refs.verified.bib` if present), `paper.txt`, and the input PDF, then emits `<output-dir>/demo.html` — a PDF.js-based viewer with a claims sidebar. Re-run after any `--recheck`, `--triage`, or partial resume to keep the viewer in sync with the JSONs.

If the script fails or is unavailable, emit a non-fatal warning — the run's canonical artifacts (`ledger/claims/*.json` + `ledger.md`) are unaffected.

### Do not

- **Do not auto-resolve `AMBIGUOUS` entries** based on your own best guess. The whole point of surfacing ambiguity is to get a human call on close verdicts.
- **Do not skip the triage prompt** at end of run if `AMBIGUOUS` entries exist. Surfacing them is the whole feature — silently leaving them in the ledger defeats the purpose.

## Single-claim scope (`--scope=single`)

Applies in both reader and author modes.

When `--scope=single` or the user selects `single` at prompt time:

1. Run Phase 0 normally — we still need the full `refs.bib` (reader mode) or the project's `.bib` files (author mode) to resolve the claim's citation.
2. Ask the user: "Describe the claim you want to ground" (free text).
3. Read the paper body text (input PDF in reader mode, manuscript `.tex` in author mode) and semantically match the description to one or more candidate sentences. Do **not** require verbatim quoting — the user may paraphrase, reference a section heading ("the part about transformer scaling laws"), or just describe a topic.
4. For each candidate sentence, resolve its citation markers to citekeys.
5. Present the matched sentence(s) + cited citekey(s) to the user via `AskUserQuestion` for confirmation. If multiple candidates match, let the user pick.
6. Scope Phases 1, 2, 3 to **only** the confirmed citekey(s) — typically 1–2 refs total.
7. Ledger artifact is still written in full (frontmatter + Critical findings + Summary + Details), but with only those 1–2 refs' worth of entries.

## Author mode (`--author`)

Author mode runs the same underlying workflow as reader mode (extract refs → verify bib → fetch sources → ground claims → attestation verify → triage), but against the user's own writing project rather than an external PDF. It orchestrates the existing component commands instead of re-implementing their logic.

### Input-paper discovery

Unlike reader mode where the input is a single PDF, author mode operates on a writing project:

- **Bib files** — read from `claims_ledger.md` frontmatter `bib_files:` if it exists; else auto-detect (top-level `*.bib`, excluding `background/`, `drafts/`, `vendor/`).
- **Manuscript** — `.tex` file(s) at the project root, or a specific path if provided.
- **PDF directory** — from `claims_ledger.md` `pdf_dir:`, else auto-detect (`background/`, `papers/`, `refs/`, `pdfs/`, `literature/`).
- If no `claims_ledger.md` exists → prompt to run `/init-writing-tools` first. Author mode does not bypass initialization.

### Phase mapping

| Phase | Reader mode | Author mode |
|-------|-------------|-------------|
| 0 — bibliography | Parse refs from input PDF | Skip — use existing `.bib` file(s) directly |
| 1 — verify bib | `/verify-bib refs.bib` | `/verify-bib <project-bib-file>` (same logic, raise-don't-fix — no `--fix` applied by orchestrator; user can invoke `/verify-bib --fix` manually afterwards) |
| 2 — fetch PDFs | Fetch open-access source PDFs | `/fetch-paper <citekey>` for each missing PDF per the configured `pdf_naming` pattern |
| 3 — ground claims | Extract claims from input PDF body text | `/ground-claim path/to/document.tex` — extracts `\cite{...}` markers from LaTeX (matches the existing command's bulk mode) |
| 3.5 — attestation verifier | Spot-check every claim | Same |
| 4 — ambiguity triage | Same | Same |

### Artifact layout

No separate output-dir. Everything writes into the project's existing structure:

- `claims_ledger.md` at the project root (author-mode canonical artifact; already maintained by `/ground-claim`).
- Source PDFs into the configured `pdf_dir/`.
- Bibliography fixes (if user runs `/verify-bib --fix` afterwards) into the configured `.bib` file with timestamped backup.

### Do not (author mode)

- **Never edit the manuscript `.tex`** (same as `/ground-claim`). Remediations are surfaced as proposals.
- **Never apply `/verify-bib --fix` automatically** — surface CRITICAL/MODERATE/MINOR findings and let the user decide whether to run `/verify-bib --fix` as a separate step.
- **Never write a separate `./paper-trail-*/` output-dir in author mode** — the project's `claims_ledger.md` is the canonical artifact.

## Resumability

Running `/paper-trail` against a pre-existing `<output-dir>`:

- If `refs.bib` exists → skip Phase 0 extraction. Ask the user before re-running Phase 0 (which would overwrite parser diagnostics).
- For each ref with a PDF already in `pdfs/<citekey>.pdf` → skip its Phase 2 fetch; mark "already present".
- For each ref with `pdfs/<citekey>/ingest_report.json` reporting `success: true` → skip Phase 2.5 ingest. `--force-ingest` forces re-ingest.
- Claims with a `ledger/claims/<claim_id>.json` whose `overall_verdict` is not `PENDING` → skip re-grounding in Phase 3, unless `--recheck` was passed.
- `PENDING` + `NEEDS_PDF` claims → retry fetch + ingest + ground.
- `SCHEMA_VIOLATION` claims → retry once with a fresh extractor dispatch. If it violates again, surface to user.
- `--recheck` semantics match `/ground-claim --recheck`: recompute claim keys, set `STALE` flags on drift, re-verify.

## Agent / batching topology

**Default `--batch-size 1` (serial) in v1.** Parallelism is deferred to a later milestone once the serial path is validated end-to-end. Subagent drift at higher concurrency is the known-failure-mode we're paying explicit attention to — rigor over speed, serial over parallel, until we prove the serial path is rock-solid.

Override with `--batch-size N` for parallel runs; understand that higher `N` empirically regresses verdict quality until we finish observability + retry hardening.

- Phase 0 enrichment: one subagent per parsed reference.
- Phase 1 verify: one subagent per reference.
- Phase 2 fetch: one subagent per reference.
- Phase 2.5 ingest: the ingest script is process-local (not a subagent); it runs once per ref, serially per batch.
- Phase 3 ground: the orchestrator groups claims by cited source paper and runs extractor → adjudicator sequentially per claim within the group. Parallelism, when enabled, is across papers, not within.
- Phase 3.5 verifier: one subagent per adjudicated claim.

Each phase waits for all subagents to return before advancing to the next.

## Trace log

Every subagent dispatch and final message is logged to `<output-dir>/trace/<subagent_id>.jsonl`. One file per subagent; newline-delimited JSON records. This is the local observability substrate — grep-able, diff-able, no vendor dependency.

### Record schema

Each line is one event:

```json
{
  "ts": "2026-04-18T15:22:03.412Z",
  "run_id": "run_20260418T1522Z",
  "subagent_id": "extractor-C042",
  "stage": "grounding",
  "role": "extractor",
  "claim_id": "C042",
  "event": "dispatch",
  "prompt_hash": "sha256:abcdef...",
  "payload": {"claim_text": "...", "handle": "pdfs/hammernik2021/"}
}
```

Events emitted:

- `dispatch` — orchestrator sends a prompt to a subagent. `payload` = the dispatch slot values.
- `final_message` — subagent returns. `payload` = the subagent's last message + exit path.
- `validation_pass` / `validation_fail` — orchestrator's schema check result. On fail, `payload.errors` is populated.
- `bounce` — verifier rejected; re-dispatching. `payload.reason` is the verifier's note.
- `escalation` — the orchestrator gave up on a claim (second bounce, second schema fail).

### Usage

- `cat trace/*.jsonl | jq 'select(.event == "validation_fail")'` — find every schema violation across the run.
- `grep '"claim_id":"C042"' trace/*.jsonl` — reconstruct the full history of one claim.
- `jq -r 'select(.event == "final_message") | [.role, .claim_id, .payload.exit_path] | @tsv' trace/*.jsonl` — quick tabular view of all subagent outcomes.

No Phoenix / Langfuse dependency in v1. If a vendor observability tool is needed later (M2+), it reads the same JSONL as its source.

### Skip handling
- `--skip=key1,key2` excludes those citekeys from Phases 2 and 3. Their ledger entries become `PENDING` / `NEEDS_PDF`.
- `--skip-paywalled` auto-adds to the skip list any citekey Phase 2 couldn't fetch.
- The user can also drop specific citekeys interactively via `AskUserQuestion` at the post-fetch pause (see Phase 2).

## End-of-run triage report

Print a structured summary mirroring `/ground-claim`'s end-of-run format, with a header for the input paper:

```
paper-trail audit: <input-paper-title>
  Output: <output-dir>/ledger.md
  Refs:   N parsed, M fetched, K skipped (NEEDS_PDF)
  Bib audit (Phase 1):
    CRITICAL:  X
    MODERATE:  Y
    MINOR:     Z
  Claim audit (Phase 3): N claims processed.
    CONFIRMED:            …
    PARTIALLY_SUPPORTED:  …
    OVERSTATED:           …
    OVERGENERAL:          …
    CITED_OUT_OF_CONTEXT: …
    UNSUPPORTED:          …  ← review
    CONTRADICTED:         …  ← critical
    MISATTRIBUTED:        …
    INDIRECT_SOURCE:      …
    AMBIGUOUS:            …  ← awaiting user triage
    STALE:                …
    PENDING (needs PDF):  …

Requiring attention:
- <CRITICAL bib issues, one per line>
- <CONTRADICTED / UNSUPPORTED claims with source-page pointers, one per line>
- <AMBIGUOUS count; "run /paper-trail <pdf> --triage to resolve" if > 0>
```

Every flagged entry includes the source paper page number (for claims) or authoritative source URL (for bib) so the user can verify directly.

## Do not (both modes)

- **Never bypass paywalls.** Inherit the `/fetch-paper` policy (no Sci-Hub, no LibGen, no misrepresenting preprint as published).
- **Never silently ground a claim against an un-fetched PDF.** Use `PENDING` + `NEEDS_PDF`.
- **Never drop parser diffs on the floor.** If a PDF-parsed value disagrees with the authoritative source, record both in `parse_report.md` — this is the signal we use to iterate on parser quality.
- **Never collapse multi-cite claims into one entry.** One ledger entry per `(claim_key, citekey)` tuple, per the existing `/ground-claim` rule.
- **Never mark the run "complete" if a phase partially failed.** Print the in-progress state so re-runs can resume from the right place.
- **Never edit the manuscript.** Both modes: remediations are surfaced as proposals in the triage report.

### Reader-mode-specific

- **Never modify a project-level `claims_ledger.md`.** Reader mode writes only within `<output-dir>/`.
- **Never run `/verify-bib --fix` in reader mode.** The input paper is not the user's to correct.

### Author-mode-specific

- **Never write a `./paper-trail-*/` output-dir in author mode.** The project's existing `claims_ledger.md` is the canonical artifact.
- **Never apply `/verify-bib --fix` automatically.** Surface findings and let the user decide whether to run the fix as a separate step.
- **Never proceed without a `claims_ledger.md` or its equivalent config.** Prompt to run `/init-writing-tools` first.
