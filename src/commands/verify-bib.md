Audit BibTeX entries against authoritative sources (paperclip full-text corpus, CrossRef, arXiv, PapersFlow if available), and classify each reference's grounding **coverage** (can claims be grounded against the paperclip corpus, or is a PDF needed?). Categorize errors by severity. Optionally write corrections to the `.bib` file only.

## Core principle: raise, don't fix

By default this command reports issues and proposes fixes — it does not apply them. The user reviews and decides. Only with an explicit `--fix` flag will the command write corrections, and even then **only to the `.bib` file** (with a timestamped backup). The manuscript (`.tex`) is never touched by this command under any circumstances.

## Invocation forms

- `/verify-bib <citekey>` — single entry
- `/verify-bib path/to/references.bib` — whole file
- `/verify-bib path/to/file.bib --fix` — write corrections in-place (creates timestamped backup first)

## Data sources (first hit wins per field)

1. **paperclip full-text corpus** (the gxl.ai CLI, if installed + authenticated) — paper-trail's grounding corpus (PMC + bioRxiv + medRxiv + arXiv). Used both to classify each reference's grounding **coverage** (see the next section) and, when a reference is in-corpus, as an authoritative metadata source — record metadata diffs against the printed entry the same way CrossRef diffs are recorded. Resolve by `paperclip search -s <source> "<DOI or title>"` — **not** `paperclip lookup`, which currently errors server-side on every field (2026-06-24 smoke finding); `search` also requires an explicit `-s <source>` flag (e.g. `-s pmc`, `-s arxiv`).
2. **PapersFlow MCP** if available — purpose-built citation verification endpoint; covers 474M+ papers via OpenAlex + Semantic Scholar. Broader metadata coverage than the paperclip full-text corpus; use it (and the chain below) for entries paperclip does not hold.
3. **CrossRef API** via WebFetch: `https://api.crossref.org/works/<DOI>` (when a DOI is present) or the search endpoint for title-based lookup.
4. **arXiv API** via WebFetch for arXiv entries: `https://export.arxiv.org/api/query?id_list=<id>`.
5. **Semantic Scholar** (via PapersFlow or direct) as fallback for entries missing DOIs.

## Coverage classification (paperclip-aware)

Separate from the metadata audit below, every reference gets a **`coverage`** value recording whether paper-trail can ground claims against the reference's full text in the paperclip corpus, or must fetch a PDF. Downstream phases (fetch, ground) read this to decide whether a PDF is needed.

`coverage` is one of:

- **`paperclip`** (in the full-text corpus) — claims can be grounded server-side, no PDF download needed. Record the reference's **`paperclip_handle`** — the `/papers/<doc_id>/` directory name as paperclip surfaces it (e.g. `PMC10131505`, `2407.11321`, `bio_<uuid>`).
- **`external`** (not in the corpus, or paperclip unavailable) — claims will be grounded against a fetched PDF, exactly as today. Paywalled references stay `external`.
- **`unresolved`** (no source resolved it) — flagged for user triage; no grounding attempted.

**How `paperclip search` behaves** (2026-06-24 smoke test on the 56-ref Adamson fixture): `search` is a fuzzy/semantic query — it **always returns the number of results you ask for**, even when none actually match, so a non-empty result set carries *zero* signal on its own. Confirm every candidate against the reference: **normalized-title overlap ≥ 0.6 AND publication year within ±2**. The real match, when present, is usually result **#2 or #3, not #1** (the ranker favors newer same-topic papers), so scan the full top-N — `-n 4` is enough. `paperclip lookup` (the exact-identifier primitive) is broken server-side; use `search -s` only.

Classify each reference in this order, first hit wins:

1. **paperclip by title across the full-text sources** — for **every** reference (not only ones carrying an arXiv eprint), run both `paperclip search -s pmc "<title>" -n 4` and `paperclip search -s arxiv "<title>" -n 4`. `-s pmc` already spans the PMC + bioRxiv/medRxiv preprint mirror, so those two searches cover the whole full-text corpus. **Journal and conference papers frequently have an arXiv preprint even when the citation is to the paywalled version — do not skip the arXiv search for journal-DOI references**; that preprint is exactly what makes the reference groundable (in the fixture, paywalled IEEE/MRM/CVPR refs like `hammernik2018` → `arx_1704.00447`, `mardani2019` → `arx_1706.00051`, `dar2019` → `arx_1802.01221` all resolved this way). Accept the first candidate clearing the ≥0.6-title-overlap + ±2-year gate; mark `coverage: paperclip` and record `paperclip_handle` (the `arx_...` or `PMC...` id). When the reference has an explicit arXiv id, the arXiv search surfaces it directly — confirm the id matches.
2. **paperclip `abstracts` source (identity resolution only)** — on a full-text miss, `paperclip search -s abstracts "<title or DOI>"`. The abstracts corpus is title + abstract only (no full text), so it **cannot ground** — but it catches wrong-paper citations and refines metadata. A hit here marks `coverage: external` (still needs a PDF) and feeds the metadata audit. Default-on; one sub-second query per reference.
3. **fall back to the metadata chain** — CrossRef → arXiv API → Semantic Scholar (via PapersFlow when present). Mark `coverage: external` if the reference resolves anywhere, `coverage: unresolved` if nothing does.

**DOI-prefix heuristic (a prior, never a rule):** paywalled-publisher prefixes — `10.1109/` (IEEE), `10.1002/mrm` (MRM), `10.1117/` (SPIE), `10.1145/` (ACM), `10.1016/` (Elsevier), `10.1007/` (Springer) — make `coverage: external` *likely*, but only after step 1 finds no preprint. Always run the title searches first; never mark a reference `external` on its DOI prefix alone.

**When paperclip is unavailable** (CLI not installed, not authenticated, or invoked with `--paperclip=off` / `--paperclip=never`): skip the paperclip searches (steps 1–2) entirely and classify every reference `external` or `unresolved` via step 3 (the CrossRef → arXiv API → Semantic Scholar chain) alone, exactly as today. This is non-fatal — the audit still runs in full.

## Per-entry checks

For each BibTeX entry:

### Existence
- Does the DOI resolve? Does the arXiv ID exist? Does the title match a paper at the claimed venue + year?
- If none: likely fabricated. Mark **CRITICAL**.

### Author names
- Compare every author surname and initial against the authoritative source.
- Most or all authors wrong → **CRITICAL** (likely chimera: cite key + metadata describe different papers).
- Subset misspelled → **MODERATE**.

### Bibliographic fields
- **Title**: match allowing case and minor punctuation differences. Major mismatch → chimera → **CRITICAL**.
- **Journal** / **booktitle**, **volume**, **issue**, **pages**, **year**: all match authoritative source?
- **Required fields** by entry type:
  - `@article`: author, title, journal, year, volume, pages (issue if available)
  - `@inproceedings`: author, title, booktitle, year
  - `@book`: author/editor, title, publisher, year
  - `@misc`: author, title, year, howpublished/url
  - Missing → **MODERATE**.

### Preprint status
- If entry points to an arXiv preprint, check CrossRef for a peer-reviewed version.
- Published version found → **MINOR** — suggest arXiv→published upgrade.
- When upgrading: update journal/volume/pages/DOI/year. **Retain** the arXiv eprint field so the preprint version remains traceable.

### Duplicates
- Group entries by DOI (if present) and by normalized title.
- Distinct cite keys with the same DOI or title → **MINOR** — flag for the user to consolidate.

## Severity summary

| Severity | Examples |
|----------|----------|
| CRITICAL | Non-resolving DOI, fabricated/chimera entry, wrong DOI, majority-wrong author list |
| MODERATE | Misspelled author names, wrong pages/volume/year, missing required fields |
| MINOR | arXiv→published upgrade available, missing issue/DOI when one exists, duplicate keys |

## Report format

Output a markdown report:

```markdown
## BibTeX Audit — <path> (<N> entries)

### CRITICAL (X)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Fix: <specific correction>

### MODERATE (Y)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Fix: <specific correction>

### MINOR (Z)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Suggestion: <specific correction>

### Verified clean (K)
`<citekey1>`, `<citekey2>`, ...

### Unverifiable (U)
`<citekey>`: <reason API could not be queried>
```

## --fix mode

When invoked with `--fix`:

1. Back up the .bib file to `<file>.bib.bak.<YYYYMMDD-HHMMSS>` before any edits.
2. Apply **CRITICAL** and **MODERATE** corrections in-place, preserving per-entry formatting and whitespace where possible.
3. **Leave MINOR issues for the user** — these often need human judgment (which arXiv→published version to prefer, which of two duplicate keys to keep). List them in the report.
4. Print a diff summary: "Fixed N entries across <file>.bib. M MINOR issues left for manual review. Backup: <path>."

Never apply `--fix` without the explicit flag, and never apply it silently.

## Emitting a verified bib for downstream use (when invoked by `/paper-trail`)

When `/paper-trail` invokes this command over a Phase 0 PDF-parsed bib (reader mode), the workflow needs the authoritative metadata in Phases 2 (fetch) and 3 (ground) — but must not silently overwrite the input-paper's printed bibliography in `refs.bib`, because that would erase the audit surface. To serve both roles:

- **Do not** write the authoritative corrections back to the input `refs.bib`. Treat it as a frozen record of what the paper actually printed.
- **Do** emit `<same-dir>/<basename>.verified.bib` (e.g., `refs.verified.bib`) containing the authoritative metadata per entry. For each entry:
  - Start from the printed entry's fields.
  - Apply non-CRITICAL corrections (author-spelling fixes, filled DOIs, corrected years/venues, preprint→published upgrades).
  - Annotate changed fields with an `audit_corrected` BibTeX field: `audit_corrected = {<field1>=<printed-value> -> <authoritative-value>; <field2>=<...>}`.
  - Record the coverage classification on every entry: `coverage = {paperclip | external | unresolved}`, and for `coverage: paperclip` also `paperclip_handle = {<doc_id>}` (the `/papers/<doc_id>/` directory name). Phases 2–3 read these to decide whether to fetch a PDF (`external`) or ground directly against the corpus (`paperclip`).
  - For CRITICAL entries (chimeric authors, wrong DOI, fabricated): keep the printed entry *as-is* in `.verified.bib` with an `audit_flag = {CRITICAL}` marker and a `audit_note = {see ledger finding <citekey>}` pointing into the audit report. The user decides whether to accept the correction during triage — we cannot silently resolve chimera on their behalf.
- The `audit_corrected` / `audit_flag` / `audit_note` / `coverage` / `paperclip_handle` fields are custom; they don't interfere with BibTeX parsing for tools that ignore unknown fields. Phases 2 and 3 read the standard fields plus `coverage` / `paperclip_handle`, and ignore the audit annotations.
- If no corrections were needed (rare but possible for clean bibs), still emit `<basename>.verified.bib` as a copy of the input, to give downstream phases a stable filename to consume.

Phases 2 and 3 in `/paper-trail` **must prefer `refs.verified.bib` over `refs.bib` if it exists**. `refs.bib` stays in place as the printed-as-seen record; `refs.verified.bib` is the authoritative working bib. This keeps audit traceability and reliable downstream fetching from fighting each other.

## Do not

- **Never edit the manuscript (`.tex`) file.** This command touches `.bib` files only, and only in `--fix` mode.
- Never silently accept an unverified result. If an API is unreachable or returns ambiguous data, mark the entry `UNVERIFIED` rather than "clean".
- Never mass-replace author lists without showing a diff for user review, even in `--fix` mode.
- Never strip the arXiv eprint field when upgrading to a published version — keep both for traceability.
- Never introduce a DOI you didn't verify against CrossRef or arXiv.
