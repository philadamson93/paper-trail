# Bibliography Parser Diagnostics — DFD paper (Adamson et al. 2025)

**Input paper:** `Magnetic Resonance in Med - 2025 - Adamson - Using deep feature distances for evaluating the perceptual quality of MR image.pdf`
**Input paper DOI:** `10.1002/mrm.30437`
**Parse date:** 2026-04-17

## Text extraction

- Method: `pdftotext` (poppler).
- Total characters extracted: **59,189** across 14 pages.
- Avg chars/page: **~4228** (well above the 200 char/page image-PDF threshold).
- Paper is **not** image-based; no OCR fallback needed.

## Bibliography style

- Auto-detected: **Numbered Vancouver** (entries prefixed by `1.`, `2.`, …).
- In-text citation style: **superscript numerals** (e.g., `reconstructions.¹⁻⁴`, `SSIM (IWSSIM¹⁰)`).

## Parse counts

| Metric | Count |
|---|---|
| Entries parsed from PDF | **56** |
| Entries with DOI in printed bib | 0 |
| Entries with arXiv ID in printed bib | 6 (refs 24, 25, 33, 46, 51, and 46 → Simonyan & Zisserman arXiv:1409.1556) |
| Entries with journal + volume + pages | 43 |
| Entries that are conference/workshop proceedings | 13 |
| Low-confidence entries | 1 (see below) |

## Low-confidence / suspected parser or source errors

### Ref 42 — `florian2020` — SUSPECTED SOURCE BIB ERROR (not parser error)

Printed in the DFD paper's bibliography as:

> 42. Florian K, Jure Z, Anuroop S. fastMRI: a publicly available raw k-space and DICOM dataset of knee images for accelerated MR image reconstruction using machine learning. Radiol Artif Intell. 2020;2:e190007.

The author names appear to have **first names and last names swapped**. The actual fastMRI paper is authored by:

- **Knoll, F.** (not "Florian K")
- **Zbontar, J.** (not "Jure Z")
- **Sriram, A.** (not "Anuroop S")

This is expected to surface as a **CRITICAL**-or-**MODERATE** finding in `/verify-bib` (Phase 1) once CrossRef or arXiv metadata is compared. Recording here for traceability.

The parser preserved the printed-as values in `refs.bib`; the `note:` field on that entry flags the issue for downstream cross-check.

## Dual-source extraction status (Phase 0.3)

- PDF-parsed list: **56 entries** (this report).
- CrossRef `/works/10.1002/mrm.30437` reference list: **NOT YET FETCHED**.
  - Next step in Phase 0.3: fetch CrossRef reference count and per-entry metadata; reconcile against PDF-parsed list; record any diffs here.
  - For this smoke-test run, dual-source is deferred to focus on Phase 1–3 validation on a scoped subset.

## Citekey collisions

None within year. First-author-year scheme worked cleanly for this paper:

- `chaudhari2018` (ref 7) and `chaudhari2020` (ref 8) — different years, no collision.
- `hammernik2018` (ref 4) and `hammernik2021` (ref 3) — different years, no collision.
- `miao2008` (ref 13) and `miao2013` (ref 15) — different years, no collision.
- `wang2003` / `wang2004` / `wang2010` / `wang2024` — four Wang entries, all different years.
- `zhang2011` (ref 12) and `zhang2018` (ref 27, LPIPS) — different years.
- `desai2021` / `desai2022` / `desai2023` — three Desai entries, all different years.
- `zhao2021` (ref 25) and `zhao2022` (ref 26) — different years.

## Style-consistency check

All in-text citation markers observed through pages 1–10 are numerical superscripts; no author-year markers detected in the body text. Citation-marker false-positive risk (e.g., bare parenthetical years in prose being misread as cites) is **low** for this paper — consistent with the numbered-style paper class.

## Open parser-quality TODOs (for future runs)

- [ ] Fetch CrossRef reference list and compute PDF-vs-authoritative diff (Phase 0.3 dual-source).
- [ ] Spot-check 3 random parsed entries against CrossRef metadata to estimate per-field parser accuracy.
- [ ] Log any superscript markers that do **not** resolve to a numbered ref (none observed on first scan, but a thorough scan is pending Phase 3 claim extraction).
