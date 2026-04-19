---
input_paper:
  path: input-paper.pdf
  title: Deuterium Metabolic Imaging (DMI) for 3D Mapping of Glucose Metabolism in Humans with Central Nervous System Lesions at 3T
  authors: Philip M. Adamson, Keshav Datta, Ron Watkins, Lawrence Recht, Ralph Hurd, Daniel Spielman
  doi_submitted: xxx/xxxx
  doi_published: 10.1002/mrm.29830
  venue: Magnetic Resonance in Medicine, 2024
workflow: reader
scope: full
pdf_dir: pdfs/
pdf_naming: "{citekey}.pdf"
bib_files:
  - refs.bib
  - refs.verified.bib
institutional_access: Personal only
last_bootstrap: 2026-04-19
---

# Paper-trail audit — Adamson et al. 2024 (DMI of CNS lesions at 3T)

**DOI:** [10.1002/mrm.29830](https://doi.org/10.1002/mrm.29830) · **Venue:** *Magnetic Resonance in Medicine* · **Run:** `run_20260419T1236Z`

## Critical findings

### Phase 1 — Bibliography audit (CRITICAL)

- **`koppenol2009` (ref 1)** — chimeric citation: printed authors Koppenol & Bounds + printed journal/volume/issue/pages (Science 324(5930):1029–1033, 2009) exactly match Vander Heiden, Cantley, Thompson, *"Understanding the Warburg Effect"* (DOI `10.1126/science.1160809`). The intended Koppenol & Bounds review is likely *"Otto Warburg's contributions to current concepts of cancer metabolism"*, Nat Rev Cancer 11(5):325–337 (DOI `10.1038/nrc3038`). Either the wrong paper is cited or the bibliography entry is mis-assembled. **Action required:** the author must decide which source was intended; Phase 2 held this entry as NEEDS_PDF.

### Phase 3 — Claim grounding (CONTRADICTED)

- **[C061] defeyter2018 (ref 37)** — REWORD
  > Clinical subjects were scanned on a GE Signa 3T PET/MR scanner using a modified gradient filter (described in Section 2.1) and 2 H volume RF coil (coil A in Section 2.2) approximately 45 minutes following the oral ingestion of 60 g of deuterated gluc
  - **Finding:** Defeyter2018 consistently reports scans beginning 60-75 minutes (and acquisitions spanning up to 90 minutes) after oral glucose intake in both healthy and GBM subjects. The manuscript's '~45 minutes' post-ingestion timing is materially earlier than anything reported in defeyter2018 and does not match 'as in 37'. This is either an independent timing choice (the manuscript's own protocol) that should not be cited as 'as in 37', or an erroneous transcription of the source timing.
    - manuscript: `approximately 45 minutes following the oral ingestion` / source: `60 to 75 min (GBM patients); 60 min for first spectra (Fig. 1E); 65-90 min for human-brain DMI steady-state acquisition (Fig. 3A); 2H-labeled plasma lactate sampled at 60-75 min`
  - **Suggested edit:** Rephrase to 'approximately 45 minutes following the oral ingestion of 60 g of deuterated glucose ([6,6'-2H2]Glc), adapting the oral-dosing protocol described in De Feyter et al. 2018 (0.75 g/kg capped at 60 g).' Remove the 'as in 37' framing for the timing, since defeyter2018 scans at 60-75 min post-ingestion rather than ~45 min; or justify the earlier window with an explicit rationale (e.g., PET/MR scheduling constraints) and drop the timing-level attribution.

### Phase 3 — Claim grounding (UNSUPPORTED)

- **[C032] nelson2013 (ref 29)**
  > GLY), decarboxylated to acetyl-CoA (generating bicarbonate (Bic) in the process) as the first step towards OXPHOS, or transaminated to alanine29 .
  - **Finding:** Nelson 2013 makes zero mention of acetyl-CoA, bicarbonate, pyruvate dehydrogenase (PDH), OXPHOS, oxidative phosphorylation, or decarboxylation anywhere in the ingested content (Abstract, Introduction, Results, Discussion, Methods). The study's HP13C spectra are explicitly characterized as containing two peaks only: [1-13C]pyruvate (173 ppm) and [1-13C]lactate (185 ppm).
  - **Finding:** Nelson 2013 makes zero mention of alanine or transamination anywhere in the ingested content. The paper's representative spectra (Fig. 2B and throughout) are described as containing only [1-13C]pyruvate and [1-13C]lactate peaks — no alanine peak (∼177 ppm) is reported or discussed.
  - **Suggested edit:** Re-cite this three-fates sentence to a reference that actually describes all three pyruvate fates (Lac via LDH, acetyl-CoA/Bic via PDH, Ala via transamination) imaged with HP13C — e.g., a Kurhanewicz/Brindle review, Golman/Ardenkjær-Larsen 2006 (PNAS), or Schroeder/Tyler cardiac-PDH studies that explicitly show Pyr/Lac/Ala/Bic peaks. Nelson 2013 is a prostate-specific study whose spectra contain only pyruvate and lactate peaks, so it cannot anchor the alanine or bicarbonate claims. If the intent was to cite Nelson 2013 only for the Lac fate, split the citation.

### Phase 3 — Claim grounding (CITED_OUT_OF_CONTEXT)

- **[C006] cho2017 (ref 6)**
  > From a therapeutic perspective, multiple studies indicate that this Warburg phenotype is critical to the cancer process, thus providing the basis for developing novel therapies in which altering the fluxes through these metabolic pathways is the goal
  - **Finding:** cho2017 is a review of hyperpolarized 13C MRI for noninvasively interrogating cancer metabolism; its own contribution is imaging/measurement of metabolic flux, not the development of metabolism-altering therapies. The paper mentions in passing that metabolism-targeting drugs are entering FDA pipelines, but does not itself describe or advance such therapies. Better positioned as an imaging/measurement citation than a therapeutic citation.
  - **Suggested edit:** Move cho2017 to a citation about noninvasive measurement of cancer metabolism / hyperpolarized 13C imaging (a separate sentence), rather than the 'developing novel therapies that alter metabolic fluxes' sentence. A therapy-oriented citation (e.g., seth2011 or le2010, already cited) is a better fit here.

## Summary

| | Count |
|---|---|
| References parsed from PDF | 54 (matches CrossRef exactly) |
| Open-access source PDFs fetched | 22 |
| Paywalled / unreachable under personal access | 29 → claim entries `PENDING` / `NEEDS_PDF` |
| In-text (sentence, citekey) claims | 71 (all passed Tier 1 extraction validator) |
| Grounded with real verdicts | 30 |
| `CONFIRMED` | 22 |
| `PARTIALLY_SUPPORTED` | 5 |
| `CITED_OUT_OF_CONTEXT` | 1 |
| `UNSUPPORTED` | 1 |
| `CONTRADICTED` | 1 |
| `PENDING` / `NEEDS_PDF` | 41 |
| Phase 1 bib-audit `CRITICAL` | 1 (`koppenol2009`) |
| Phase 1 bib-audit `MODERATE` | ~14 (see `refs.verified.bib` `audit_corrected` fields) |
| Phase 1 bib-audit `MINOR` | ~30 (missing DOIs, journal casing, author truncation) |

## Ledger — detail index

| Claim | Citekey | Ref | Verdict | Flag |
|---|---|---|---|---|
| C001 | `koppenol2009` | 1 | `PENDING` | CRITICAL |
| C002 | `agnihotri2013` | 2 | `PENDING` | NEEDS_PDF |
| C003 | `chesnelong2014` | 3 | `CONFIRMED` |  |
| C004 | `mathupala2009` | 4 | `PENDING` | NEEDS_PDF |
| C005 | `corbin2017` | 5 | `PENDING` | NEEDS_PDF |
| C006 | `cho2017` | 6 | `CITED_OUT_OF_CONTEXT` | REVIEW |
| C007 | `smeitink2006` | 7 | `PENDING` | NEEDS_PDF |
| C008 | `le2010` | 8 | `CONFIRMED` |  |
| C009 | `seth2011` | 9 | `CONFIRMED` |  |
| C010 | `mukherjee2004` | 10 | `PENDING` | NEEDS_PDF |
| C011 | `clark2016` | 11 | `PENDING` | NEEDS_PDF |
| C012 | `papandreou2011` | 12 | `PENDING` | NEEDS_PDF |
| C013 | `corbin2017` | 5 | `PENDING` | NEEDS_PDF |
| C014 | `corbin2019` | 13 | `PENDING` | NEEDS_PDF |
| C015 | `spence2004` | 14 | `CONFIRMED` |  |
| C016 | `koppenol2009` | 1 | `PENDING` | CRITICAL |
| C017 | `kreis2020` | 15 | `PENDING` | NEEDS_PDF |
| C018 | `kreis2020` | 15 | `PENDING` | NEEDS_PDF |
| C019 | `vaishnavi2010` | 16 | `CONFIRMED` |  |
| C020 | `vlassenko2015` | 17 | `PARTIALLY_SUPPORTED` | REVIEW |
| C021 | `baron2012` | 18 | `PENDING` | NEEDS_PDF |
| C022 | `mintun1984` | 19 | `CONFIRMED` |  |
| C023 | `witney2015` | 20 | `PENDING` | NEEDS_PDF |
| C024 | `beinat2018` | 21 | `PENDING` | NEEDS_PDF |
| C025 | `beinat2021` | 22 | `PENDING` | NEEDS_PDF |
| C026 | `fan2020` | 23 | `PARTIALLY_SUPPORTED` | REVIEW |
| C027 | `goldenberg2019` | 24 | `PENDING` | NEEDS_PDF |
| C028 | `henning2018` | 25 | `PENDING` | NEEDS_PDF |
| C029 | `ardenkjaerlarsen2003` | 26 | `CONFIRMED` |  |
| C030 | `hurd2012` | 27 | `PENDING` | NEEDS_PDF |
| C031 | `kurhanewicz2011` | 28 | `CONFIRMED` |  |
| C032 | `nelson2013` | 29 | `UNSUPPORTED` | REVIEW |
| C033 | `hurd2012` | 27 | `PENDING` | NEEDS_PDF |
| C034 | `kurhanewicz2011` | 28 | `PARTIALLY_SUPPORTED` | MINOR |
| C035 | `nelson2013` | 29 | `CONFIRMED` |  |
| C036 | `cunningham2016` | 30 | `CONFIRMED` |  |
| C037 | `malloy2011` | 31 | `PENDING` | NEEDS_PDF |
| C038 | `park2018` | 32 | `CONFIRMED` |  |
| C039 | `morze2019` | 33 | `PENDING` | NEEDS_PDF |
| C040 | `hurd2012` | 27 | `PENDING` | NEEDS_PDF |
| C041 | `kurhanewicz2011` | 28 | `CONFIRMED` |  |
| C042 | `nelson2013` | 29 | `CONFIRMED` |  |
| C043 | `miloushev2018` | 34 | `CONFIRMED` | NEEDS_PDF |
| C044 | `corbin2017` | 5 | `PENDING` | NEEDS_PDF |
| C045 | `datta2019` | 35 | `CONFIRMED` |  |
| C046 | `park2016` | 36 | `PENDING` | NEEDS_PDF |
| C047 | `defeyter2018` | 37 | `CONFIRMED` |  |
| C048 | `low2023` | 38 | `CONFIRMED` |  |
| C049 | `defeyter2021` | 39 | `PENDING` | NEEDS_PDF |
| C050 | `graaf2020` | 40 | `PENDING` | NEEDS_PDF |
| C051 | `macallan2009` | 41 | `PENDING` | NEEDS_PDF |
| C052 | `bier1977` | 42 | `PENDING` | NEEDS_PDF |
| C053 | `kreis2020` | 15 | `PENDING` | NEEDS_PDF |
| C054 | `taglang2022` | 46 | `CONFIRMED` |  |
| C055 | `batsios2022` | 47 | `PENDING` | NEEDS_PDF |
| C056 | `adamson2022` | 48 | `PENDING` | NEEDS_PDF |
| C057 | `graaf2021` | 49 | `PENDING` | NEEDS_PDF |
| C058 | `beare2018` | 50 | `CONFIRMED` |  |
| C059 | `defeyter2018` | 37 | `PARTIALLY_SUPPORTED` | NEEDS_SUPPLEMENT |
| C060 | `pohmann2018` | 51 | `PENDING` | NEEDS_PDF |
| C061 | `defeyter2018` | 37 | `CONTRADICTED` | REVIEW |
| C062 | `hamilton2017` | 52 | `PENDING` | NEEDS_PDF |
| C063 | `defeyter2018` | 37 | `CONFIRMED` |  |
| C064 | `seresroig2023` | 44 | `PENDING` | NEEDS_PDF |
| C065 | `ruhm2021` | 45 | `PENDING` | NEEDS_PDF |
| C066 | `hamilton2017` | 52 | `PENDING` | NEEDS_PDF |
| C067 | `vos2021` | 53 | `CONFIRMED` |  |
| C068 | `marques2019` | 54 | `CONFIRMED` |  |
| C069 | `defeyter2018` | 37 | `PARTIALLY_SUPPORTED` | NEEDS_SUPPLEMENT |
| C070 | `corbin2017` | 5 | `PENDING` | NEEDS_PDF |
| C071 | `graaf2020` | 40 | `PENDING` | NEEDS_PDF |

## Notes

- Phase 3.5 (attestation verifier) was **skipped** in this run — with 30 adjudicated claims and extractors explicitly prompted with verdict-schema rubric + manuscript context, drift risk was judged low. Re-running with `--recheck` would trigger verification.
- Phase 4 (ambiguity triage) found **0 AMBIGUOUS** entries — no human triage needed.
- The `demo.html` viewer (rendered by `.claude/scripts/render_html_demo.py`) gives a click-through claim-by-claim view of the same data.
- Source of truth: `ledger/claims/<CXXX>.json`. This markdown is a rendered view; edits here are overwritten on the next render.
