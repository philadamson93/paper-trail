# Example run — Adamson et al. 2024 (DMI of CNS lesions at 3T)

A complete `/paper-trail` reader-mode audit of Adamson PM, Datta K, Watkins R, Recht L, Hurd RE, Spielman DM. *"Deuterium metabolic imaging for 3D mapping of glucose metabolism in humans with central nervous system lesions at 3T."* **Magnetic Resonance in Medicine**, 2024. DOI [10.1002/mrm.29830](https://doi.org/10.1002/mrm.29830).

This is the second worked example bundled with the repo. The [first](../paper-trail-adamson-2025/) audits the authors' MR-reconstruction-quality paper; this one audits their DMI clinical-feasibility paper.

## Try it now

Open **`demo.html`** in any browser — ~7.5 MB (PDF inlined so it works from `file://`). A PDF.js viewer renders `input-paper.pdf` on the left with the full claim ledger on the right. Click a claim row to jump to that spot in the PDF; click the ⓘ button for the full verdict detail popup (reference card, claim text, sub-claim breakdown, evidence excerpts, remediation). Click a citation marker *in* the PDF to highlight matching claims in the sidebar.

Hosted copy: [philadamson93.github.io/paper-trail/Adamson-MRM-DMI-2024.html](https://philadamson93.github.io/paper-trail/Adamson-MRM-DMI-2024.html).

## What's in this bundle

```
demo.html                      Reference HTML viewer. Open in a browser.
input-paper.pdf                The audited paper itself.
paper.txt                      Plaintext extraction used by demo.html.
refs.bib                       Bibliography parsed verbatim from input-paper.pdf.
refs.verified.bib              Same bibliography, enriched + corrected via CrossRef audit.
parse_report.md                Phase 0 parser diagnostics (count reconciliation, flagged entries).
claim_extraction_report.md     Tier 1 validator output over the extracted claim list.
ledger.md                      Rendered audit artifact (derived from ledger/claims/*.json).
verdict_schema.md              JSON schema every claim file conforms to.
ledger/
  claims/<id>.json             71 verdict files — one per claim. SOURCE OF TRUTH.
```

Source PDFs and their GROBID ingest handles (section text, figure crops) are not included — reproducible from each citekey's DOI via `fetch-paper` + `.claude/scripts/ingest_pdf.py`, and subject to publisher copyright.

## Run at a glance

| | Count |
|---|---|
| References parsed from the PDF | 54 (exact match to CrossRef count) |
| Open-access source PDFs fetched | 22 |
| Paywalled / unreachable under personal access | 29 → claim entries stubbed `PENDING` / `NEEDS_PDF` |
| In-text `(sentence, citekey)` claims | 71 (all passed Tier 1 extraction validator) |
| Grounded with real verdicts | 30 |
| `CONFIRMED` | 22 |
| `PARTIALLY_SUPPORTED` | 5 |
| `CITED_OUT_OF_CONTEXT` | 1 |
| `UNSUPPORTED` | 1 |
| `CONTRADICTED` | 1 |
| `AMBIGUOUS` | 0 |
| `PENDING / NEEDS_PDF` | 41 |
| Phase 1 bib-audit `CRITICAL` | 1 (`koppenol2009` — chimeric citation) |
| Phase 1 bib-audit `MODERATE` / `MINOR` | ~14 / ~30 |

## Headline findings

- **Phase 1 — `koppenol2009` is chimeric.** The printed authors Koppenol & Bounds and the printed venue/volume/issue/pages (Science 324(5930):1029–1033, 2009) match two *different* papers: the publication details are Vander Heiden, Cantley, Thompson's *"Understanding the Warburg Effect"* (DOI `10.1126/science.1160809`); the printed authors fit Koppenol, Bounds, Dang's *"Otto Warburg's contributions to current concepts of cancer metabolism"* (Nat Rev Cancer 11(5):325–337, 2011, DOI `10.1038/nrc3038`). The author must resolve which source was intended before the Phase 2 fetch can proceed.
- **Phase 3 — `C061` contradicts `defeyter2018`.** The manuscript's Methods state clinical subjects were scanned "approximately 45 minutes following the oral ingestion of 60 g of deuterated glucose … as in [defeyter2018]". defeyter2018 actually scans at 60–75 min post-ingestion. The 60 g dose attribution is correct (defeyter2018 caps at that amount); the ~45 min timing attribution is not.
- **Phase 3 — `C032` is unsupported by `nelson2013`.** The manuscript cites Nelson 2013 (HP13C prostate) for the sentence describing pyruvate's three metabolic fates (lactate via LDH, acetyl-CoA/bicarbonate via PDH, alanine via transamination). Nelson 2013 reports only pyruvate and lactate peaks — no alanine, no PDH, no transamination. Remediation: re-cite a Kurhanewicz/Brindle HP13C review.
- **Phase 3 — `C006` cites `cho2017` out of context.** `cho2017` is a review of HP13C *imaging* of cancer metabolism; the manuscript cites it under "developing novel therapies that alter metabolic fluxes."

Full detail in `ledger.md` and `ledger/claims/<id>.json`.
