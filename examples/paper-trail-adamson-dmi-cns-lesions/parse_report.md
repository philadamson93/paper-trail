# Phase 0 parse report

**Input PDF:** `input-paper.pdf` (14 pages, 5.3 MB)
**Published version resolved:** [doi.org/10.1002/mrm.29830](https://doi.org/10.1002/mrm.29830) (Magn Reson Med, 2024) — the working copy in the repo is a pre-publication manuscript (blank submission dates; `DOI: xxx/xxxx` placeholder on page 1). References cross-checked against the published CrossRef record.

## Step 0.0 — PDF readability

Text extraction via `pdftotext`. All 14 pages produced substantial text (1,193–6,452 chars/page; no page below the 200-char OCR threshold). PDF is born-digital and fully machine-readable — no OCR fallback needed.

| Page | Chars |
|-----:|------:|
| 1 | 3,594 |
| 2 | 6,114 |
| 3 | 5,451 |
| 4 | 1,705 |
| 5 | 1,193 |
| 6 | 4,588 |
| 7 | 3,718 |
| 8 | 1,390 |
| 9 | 1,318 |
| 10 | 1,370 |
| 11 | 1,365 |
| 12 | 4,327 |
| 13 | 6,452 |
| 14 | 5,797 |

## Step 0.1 — Input-paper metadata

| Field | Value |
|---|---|
| Title | Deuterium Metabolic Imaging (DMI) for 3D Mapping of Glucose Metabolism in Humans with Central Nervous System Lesions at 3T |
| Authors | Philip M. Adamson, Keshav Datta, Ron Watkins, Lawrence Recht, Ralph Hurd, Daniel Spielman |
| DOI (submitted ms) | (blank — `xxx/xxxx` placeholder) |
| DOI (published) | 10.1002/mrm.29830 |
| Venue (published) | Magnetic Resonance in Medicine, 2024 |
| Year | 2024 (published) / in-submission draft |

## Step 0.2 — Bibliography parser

- Located the `REFERENCES` section on page 13, immediately after the `ORCID` block.
- Auto-detected style: **numbered** (entries prefixed `1.`, `2.`, ...).
- Parsed **54** entries from the PDF bibliography.
- Citekeys derived as `<firstauthor><year>` with suffix handling for single-author-year collisions (e.g. Corbin Z. 2017 → `corbin2017`, Corbin Z.A. 2019 → `corbin2019`).

## Step 0.3 — Count reconciliation vs. CrossRef

Published version DOI `10.1002/mrm.29830` resolves the authoritative reference list.

| Source | Count |
|---|---|
| PDF parser (this step) | 54 |
| CrossRef `reference[]` | 54 |
| Diff | **0 — exact match** |

No `crossref_count_fill` entries needed. No missed references detected by count-check.

## Step 0.4 — Parser diagnostics (entries to watch)

Per spec, metadata *enrichment* is deferred to Phase 1. These are parser-level observations flagged so downstream phases know which entries to audit carefully:

- **Ref 10 (`mukherjee2004`)** — layout-column artifact: CCR year `2004;10(16):5622–5629.` printed on page 14 line 01; attached to ref 10 by paragraph continuation. Bib entry preserves `Clinical Cancer Research, 2004, 10(16), 5622–5629` verbatim.
- **Ref 26 (`ardenkjaerlarsen2003`)** — similar left-column wrap: year line `2003;100(18):10158–10163.` landed on page 14 line 01. Parser re-attached correctly.
- **Ref 35 (`datta2019`)** — printed as `Datta Keshav, Lauritzen Mette H., Merchant , et al.` with an empty given name after "Merchant". Parser preserved the empty-given-name entry verbatim (`Merchant, {}`) so Phase 1 can raise it against CrossRef.
- **Ref 38 (`low2023`)** — no volume / issue / pages printed (bib ends with `Progress in Nuclear Magnetic Resonance Spectroscopy. 2023;.`). Parser preserved verbatim; flag for Phase 1.
- **Ref 48 (`adamson2022`)** — looks like an ISMRM 2022 abstract; printed as `In: :1352; 2022.` with booktitle omitted. Parser captured `pages=1352` and flagged `venue missing`.
- **Ref 49 (`graaf2021`)** — `DMIWizard v1.3` — software, not a paper. Typed as `@misc` with `howpublished = {Yale University, MRRC}`.
- **Ref 51 (`pohmann2018`)** — `In: ; 2018.` — conference abstract with booktitle missing. Likely ISMRM/ESMRMB 2018; Phase 1 can try to resolve.
- **Ref 53 (`vos2021`)** — printed `Frontiers in Physics. 2021;:413.` — volume field is empty; `413` is article ID. Parser stored `pages=413`.

No lines were unparseable; there are no `unresolved` entries.

## Step 0.5 — Confirmation gate

**Status:** ready for user confirmation. PDF-parsed count (54) matches CrossRef-reported count (54) exactly, so no count-fill entries were introduced.
