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

- `ledger.md` — audit artifact. Reuses `templates/claims_ledger.md` schema (YAML frontmatter + Summary table + Details blocks + severity taxonomies) with two additions (see "Ledger additions" below).
- `refs.bib` — synthetic BibTeX built from the parsed + looked-up references.
- `pdfs/` — fetched source PDFs, each named `<citekey>.pdf`.
- `parse_report.md` — bibliography parser diagnostics: refs found, DOI hit rate, bibliography-style auto-detected, low-confidence entries flagged by line number.

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

### Step 0.3 — Dual-source extraction + enrichment

The PDF parser in Step 0.2 is fallible — bibliography layouts vary and OCR introduces noise. Cross-check the parsed list against an authoritative source list to catch misses.

- **Dual-source extraction:**
  - (a) PDF-parsed list from Step 0.2 (existing).
  - (b) If the input paper has a resolvable DOI, fetch its reference list from CrossRef (`https://api.crossref.org/works/<DOI>` — the `reference` array) and / or from PapersFlow / OpenAlex. This is the authoritative "who did the authors actually cite" list, to the extent publishers report it.
- **Reconcile:**
  - If (a) count and (b) count differ, record the diff in `parse_report.md` (e.g., "PDF parser found 42 refs, CrossRef reports 45").
  - For per-entry reconciliation, attempt external lookup on each parsed entry (first hit wins): **PapersFlow MCP** (if available) → **CrossRef** (by DOI, else by title+author+year) → **arXiv** (for preprint-shaped entries). If any field disagrees, prefer the authoritative value; record the PDF-parsed value in `parse_report.md` as a "parser diff" so we can audit parser quality.
  - Any entry present in (b) but not (a) is added to `refs.bib` with a `parser_source: crossref` marker and flagged low-confidence (we have the authoritative metadata but didn't see it in the PDF — possibly the parser missed an entry).
- Parallelize per-entry enrichment in batches per the configured batch size.

### Step 0.4 — Emit artifacts
- Write `refs.bib` in standard BibTeX. Preserve both parsed and looked-up values where they disagree, preferring the authoritative value in the bib and noting the parsed value in `parse_report.md`.
- Write `parse_report.md` with:
  - Total entries parsed from PDF; total from authoritative source (CrossRef / PapersFlow); diff count.
  - Total enriched; total with DOI; total flagged low-confidence.
  - Auto-detected bibliography style.
  - Per-entry parser diffs (authoritative vs parsed) for entries where they differ.
  - Explicit list of unparseable / low-confidence lines by line number so a human can spot-check.
  - List of entries added from the authoritative source that the PDF parser missed.

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

Run `/verify-bib` logic against `<output-dir>/refs.bib`, parallelized.

- Spawn one subagent per reference, batched per the configured batch size.
- Each subagent follows the `/verify-bib` per-entry workflow (existence, author match, bibliographic fields, preprint upgrades, duplicates) and returns a severity-classified result.
- Collect results and populate the ledger's `## Critical findings` section with every `CRITICAL` entry.
- Do **not** auto-apply `--fix` corrections in reader mode. Raise, don't fix. (The user is not the author — they don't get to correct the input paper's bib.)

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

### Step 3.2 — Group and dispatch
- Group claim candidates by their cited source paper (citekey).
- For each source paper with at least one non-skipped citekey, spawn a subagent (batched per the configured batch size) that:
  - Opens that single source PDF once.
  - Runs `/ground-claim` Step 2 pre-read checks (text extractability / image-based PDF → OCR fallback; page count → chunked-read mode if > 25 pages). For image-based PDFs with no OCR available, all claims citing that source are marked `PENDING` with `NEEDS_OCR` — do not force verdicts on unreadable PDFs.
  - Verifies every claim citing it in one pass (matches the `/ground-claim` "process claims grouped by source paper" rule). For PDFs > 25 pages, this one pass becomes a chunked-section pass per `/ground-claim` Step 2 "Paper-length handling".
  - **Follows the `/ground-claim` per-claim workflow in full**: Step 1 classify → Step 2 locate evidence (*including* the minimum-reading requirement, negative-evidence protocol, indirect-attribution check, out-of-context check, and Step 2 self-check) → Step 3 assess support → Step 4 propose remediation → Step 5 append to ledger.
  - **Rigor beats compute.** Subagent prompts must explicitly forbid shortcutting — no skimming, no abstract-only reads, no declaring `UNSUPPORTED` / `CONTRADICTED` without a full attestation log. It is materially better to spend extra tokens per subagent than to propagate a false verdict into the ledger.
- Refs marked `NEEDS_PDF` from Phase 2 → their claims are written to the ledger with status `PENDING` and flag `NEEDS_PDF`. Do not spawn a grounding subagent for them.

### Step 3.3 — Inflight-file layout (prevents concurrent-write clobbering)

Subagents do **not** write directly to `ledger.md`. Concurrent `Edit` / `Write` calls from batched subagents will race and clobber each other (the runtime does not serialize file edits across agents). Use a per-claim inflight-file layout instead:

1. Each grounding subagent writes one file per claim to `<output-dir>/.inflight/<claim_id>.md`. The file contains the Details block for that single claim (frontmatter-style fields + quoted source excerpt + search log + attestation log + any AMBIGUOUS-specific fields).
2. After every Phase 3 batch returns, the main orchestrator merges sequentially:
   - Reads every file in `.inflight/`.
   - Appends each claim's Details block to `ledger.md`'s `## Details` section under a single `### <claim_id> — <citekey>` subheading per entry. Do **not** prepend a wrapper heading if the inflight file already starts with its own — strip or skip the inflight file's leading heading to avoid duplicated `### Cxxx` lines in the merged ledger.
   - Updates the Summary table with one row per entry.
   - Deletes the merged inflight files.
3. Claim IDs (`C001`, `C002`, …) are allocated by the **main orchestrator** before dispatch — each subagent is handed its assigned ID, so concurrent subagents cannot collide on ID allocation.

Partial progress survives a crashed subagent: any inflight files written before the crash remain on disk. At end-of-run `.inflight/` should be empty; a non-empty `.inflight/` on startup is a resumption signal that Phase 3 was interrupted mid-batch.

## Phase 3.5 — Attestation verification

Attestation logs (Step 2 of `/ground-claim`) are self-reported — a grounding subagent that skimmed the abstract and invented plausible-looking attestation fields would pass. To counter this, every claim verdict is spot-checked by an independent verifier subagent.

### Dispatch

For every claim entry produced in Phase 3 (regardless of support level — including `CONFIRMED`), spawn one lightweight verifier subagent. Verifiers run in parallel batches per the configured batch size.

### Verifier workflow

Each verifier subagent:

1. Reads one ledger entry (Summary row + Details block + attestation log).
2. Picks one line at random from the attestation log's `Specific checks:` list — e.g., `Table 2 (dataset sizes)`, `Fig. 4 caption (accuracy numbers)`, `Eq. 3 surrounding prose`.
3. Opens the cited source PDF at the claimed page / section and confirms:
   - The specific check exists (the claimed table / figure / equation is there on the claimed page).
   - The `Closest adjacent passage` quote is present verbatim at the claimed page.
4. Writes a verifier result to `<output-dir>/.inflight/<claim_id>.verify.md`:

```
Verifier result:
  Claim ID:       C<N>
  Check sampled:  <one random line from Specific checks>
  Passage found:  YES | NO | PARTIAL
  Notes:          <YES → "ok"; NO → what the verifier found instead;
                   PARTIAL → what matched and what didn't>
```

### Handling verifier results

After all verifier subagents return, the orchestrator merges `.verify.md` files into `ledger.md`:

- **Verifier confirmed (YES)** → no change to the entry.
- **Verifier could not confirm (NO or PARTIAL)** → add `UNVERIFIED_ATTESTATION` to the entry's Flag column; append a dated history note to Details: `_<YYYY-MM-DD>: verifier could not confirm attestation — sampled check "<...>" not found as attested; verifier notes: <...>_`. The support level is **not** automatically changed — the flag is the signal.
- `UNVERIFIED_ATTESTATION`-flagged entries are surfaced in the end-of-run triage report alongside `CONTRADICTED` and `UNSUPPORTED`, because they indicate the original subagent may have fabricated the attestation.

### Default: verify every claim, not sampled

For v1, verify every claim. Rigor beats compute. A `--verifier-sample=<pct>` flag may be added later once we have cost data from real runs; not a v1 default.

### Do not

- Do not auto-correct verdicts based on verifier output. The verifier flags; the user (or a re-grounding pass) resolves.
- Do not skip verification on `CONFIRMED` entries. A falsely-confirmed claim is as dangerous as a falsely-denied one.
- Do not let a verifier subagent also produce the original verdict. Each verifier targets exactly one claim entry, and that entry must have been produced by a different subagent.

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
- For each ref with a PDF already in `pdfs/` → skip its Phase 2 fetch; mark "already present".
- Ledger entries with a non-`PENDING` support level → skip re-grounding in Phase 3, unless `--recheck` was passed.
- `PENDING` + `NEEDS_PDF` entries → retry their fetch in Phase 2 and grounding in Phase 3.
- `--recheck` semantics match `/ground-claim --recheck`: recompute claim keys, set `STALE` flags, re-verify.

## Agent / batching topology

Default parallelism: 10 concurrent subagents per phase. Override with `--batch-size N` or `--sequential` (equivalent to `--batch-size 1`).

- Phase 0 enrichment: one subagent per parsed reference.
- Phase 1 verify: one subagent per reference.
- Phase 2 fetch: one subagent per reference.
- Phase 3 ground: one subagent per unique cited source paper (not per claim — one paper handles all its own claims in a single pass).

Each phase waits for all subagents to return before advancing to the next. This is not the most aggressive parallelization possible, but it keeps the ledger writes orderly and makes partial-progress states interpretable.

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
