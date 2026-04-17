# Phase 0 parse report

Input paper: **Adamson et al., "Using deep feature distances for evaluating the perceptual quality of MR image reconstructions"**, *Magnetic Resonance in Medicine* (2025). DOI: `10.1002/mrm.30437`.

## PDF readability

- Extraction tool: `pdftotext` (Poppler 26.02.0), layout mode.
- Pages: 14. Avg extracted chars/page: ~5400 (min 2328, max 8338). Well above the 200-chars/page threshold for image-based PDF detection — no OCR needed.
- OCR fallback available: `tesseract` **not** installed. macOS Shortcuts fallback not attempted (unnecessary here).

## Bibliography extraction

- Style detected: **numbered** (in-text superscript numerals keyed to a numbered references list).
- Reference section located at line 606 of `paper.txt`, starting with `1. Lustig M, Donoho D, Pauly JM. Sparse MRI...` and ending with `56. Desai AD, Ozturkler BM, Sandino CM, et al. Noise2Recon...`.
- PDF-parsed reference count: **56**.
- CrossRef-reported reference count (from `https://api.crossref.org/works/10.1002/mrm.30437`): **56**.
- Diff count: **0** — counts match 1:1 by ordinal.

## Dual-source extraction + enrichment

All 56 entries were cross-referenced against CrossRef. Result:

| Bucket | Count | Notes |
|---|---:|---|
| DOI resolvable via CrossRef | 45 | Authoritative metadata pulled from CrossRef and used as primary. |
| No DOI in CrossRef, manually resolved | 11 | arXiv preprints, NeurIPS / ICML workshop papers, and two Radiology AI 2022 papers where CrossRef returned partial metadata. |
| Total enriched | 56 | |
| Entries with DOI in `refs.bib` | 46 | 45 from CrossRef + 1 (`ding2020`, ref 28) where CrossRef did not assert a DOI but TPAMI published version has `10.1109/TPAMI.2020.3045810`. |
| Entries flagged low-confidence | 0 | All manual entries cross-checked against their arXiv IDs printed in the PDF. |
| Entries added from CrossRef that PDF parser missed | 0 | |
| Entries in PDF that CrossRef missed | 0 | |

## Per-entry parser diffs

Cases where the CrossRef metadata disagreed with a sensible reading of the PDF, and which value was chosen for `refs.bib`:

| Ref | Field | PDF value | CrossRef value | Chosen | Reason |
|---|---|---|---|---|---|
| 11 (`wang2003`) | year | 2003 | 2004 (from CrossRef `created` registration date) | **2003** | Conference was held in 2003; DOI slug contains "2003"; container-title ends in ", 2003". CrossRef `created` reflects registration date, not publication year. |
| 28 (`ding2020`) | DOI | none printed | none asserted | **10.1109/TPAMI.2020.3045810** (manual) | DISTS was published in *IEEE Transactions on Pattern Analysis and Machine Intelligence* with this DOI; CrossRef did not expose it in the reference metadata returned for the input paper, so added manually. |
| 25 (`zhao2021`) | arXiv ID | `rXiv:2109.11524` (typo — missing "a") | — | **2109.11524** | Obvious OCR/typo in the printed reference. Checked arXiv; ID resolves to the correct paper. |

## Manual-override entries (bib `parser_source: manual`)

These 11 refs were not DOI-resolvable via the input paper's CrossRef reference list. Metadata was recovered from a combination of the printed reference, the printed arXiv IDs, and author/venue lookup.

| Ref | Citekey | Source | Notes |
|---|---|---|---|
| 24 | `desai2022` | arXiv:2203.06823 | SKM-TEA dataset paper; arXiv preprint. |
| 25 | `zhao2021` | arXiv:2109.11524 | Preprint; not published in venue yet per PDF. |
| 28 | `ding2020` | CrossRef (manual DOI) | DISTS (TPAMI 2020). |
| 33 | `keshari2022` | arXiv:2204.09779 | Preprint. |
| 36 | `raghu2019` | NeurIPS 2019 | Also on arXiv:1902.07208. |
| 37 | `mei2022` | Radiology: AI 2022 | DOI: 10.1148/ryai.210315 (CrossRef returned partial). |
| 38 | `cadrinchenevert2022` | Radiology: AI 2022 | DOI: 10.1148/ryai.220126 (CrossRef returned partial). |
| 46 | `simonyan2014` | arXiv:1409.1556 | VGG paper; also at ICLR 2015. |
| 47 | `adamson2021` | NeurIPS 2021 Workshop | DLI workshop, SSFD paper. |
| 50 | `vandersluijs2023` | ICML 2023 Workshop | Neural Compression workshop. |
| 51 | `desai2021` | arXiv:2111.02549 | VORTEX preprint. |

## Unparseable or low-confidence lines

None. The PDF's references section is well-formed and extracted without ambiguity. Line-level spot check matched all 56 entries to their ordinals in `paper.txt`.

## Citation style consistency

Every in-text citation seen in the body uses superscript numerals (e.g., `…MR acquisitions¹⁻⁴`, `…reconstruction methods,⁵`, `…noise.⁴¹`). No author-year markers were observed in the body text. Phase 3 will enforce numbered-style consistency and record any stray author-year matches in this file.

## Artifacts emitted

- `refs.bib` — 56 entries, sorted by reference number; each entry carries `refnum` and `parser_source` fields.
- `citekey_map.tsv` — `refnum` ↔ `citekey` ↔ `doi` ↔ `parser_source` ↔ truncated title.
- `paper.txt` — layout-mode PDF text dump (retained for Phase 3 claim extraction).
- `crossref_cache/` — raw CrossRef JSON for each of the 45 DOI-resolved entries (kept for audit; safe to delete after Phase 3 completes).
