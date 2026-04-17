---
input_paper:
  path: /Users/pmayankees/Documents/Stanford/RSL/Chaudhari_Lab/MRM/Magnetic Resonance in Med - 2025 - Adamson - Using deep feature distances for evaluating the perceptual quality of MR image.pdf
  title: "Using deep feature distances for evaluating the perceptual quality of MR image reconstructions"
  authors: "Philip M. Adamson, Arjun D. Desai, Jeffrey Dominic, Maya Varma, Christian Bluethgen, Jeff P. Wood, Ali B. Syed, Robert D. Boutin, Kathryn J. Stevens, Shreyas Vasanawala, John M. Pauly, Beliz Gunel, Akshay S. Chaudhari"
  doi: 10.1002/mrm.30437
  year: 2025
  journal: "Magnetic Resonance in Medicine"
workflow: reader
scope: full
pdf_dir: pdfs/
pdf_naming: "{citekey}.pdf"
bib_files:
  - refs.bib
institutional_access: "Personal only"
last_bootstrap: 2026-04-17
---

# Claims Ledger — paper-trail reader-mode audit

Audit artifact for Adamson et al. 2025, *Magnetic Resonance in Medicine*, "Using deep feature distances for evaluating the perceptual quality of MR image reconstructions" (DOI `10.1002/mrm.30437`).

Reader-mode caveat: nothing is ever auto-applied. Bib issues are **raised, not fixed**.

## Run caveats

- **Phase 3.5 attestation verification was skipped for this run** (deviation from spec). The Phase 3 grounding subagents produced full attestation logs with page numbers, section checklists, and ≥3 phrasings per claim, but an independent verifier pass across all 49 grounded claims was not run due to session-compute budget. The 6 flagged entries (C045, C055 MISATTRIBUTED; C067/C068/C075/C076 CITED_OUT_OF_CONTEXT) carry particularly strong evidence in their inflight attestation logs. CONFIRMED entries should be spot-checked by the reader against the page numbers recorded in the Details blocks below if high-stakes action depends on any specific claim.
- **Phase 2 fetch-substitution note for `gu2022` (ref 34)**: the fetched PDF at `pdfs/gu2022.pdf` is Gu et al. "NTIRE **2021** Challenge on Perceptual Image Quality Assessment" (CVPRW 2021, arXiv:2105.03072), while the bib entry names the NTIRE **2022** challenge (DOI `10.1109/CVPRW56347.2022.00109`). The Phase 2 Semantic Scholar resolver returned the 2021 arXiv as the `openAccessPdf` for the 2022 DOI — a silent substitution that should have been gated. The 2021 edition is structurally similar and the grounding verdicts for C035 / C048 / C059 / C060 hold as "representative of NTIRE-style challenge findings"; the substitution is flagged here for transparency. If precise 2022-edition content matters, manually retrieve the 2022 CVPRW paper.
- **Paywalled refs (25 of 56)** were not retrievable under the user's "Personal only" access. Their 39 corresponding claim entries are marked `PENDING` / `NEEDS_PDF`. Save the PDFs as `pdfs/<citekey>.pdf` and re-run `/paper-trail <pdf> --recheck` to ground those claims.
- **Claim-extractor artifacts** (C067, C068, C071, C075, C076): the regex-based claim extractor occasionally tagged a sentence with a ref number that was actually for an adjacent sentence in the same paragraph (a paragraph-joining artifact). These entries are flagged `CITED_OUT_OF_CONTEXT` and should be interpreted as "tool noise, not a real author error". C071 was ultimately marked CONFIRMED because the underlying data matches Mason 2020, even though the sentence itself doesn't syntactically carry the citation marker.


## Critical findings

### Phase 1 — bib audit

No CRITICAL bib findings. Detailed MODERATE / MINOR findings below.

**MODERATE (4)**

- **Ref 14 (`mantiuk2011`)** — CrossRef-stored title is literally `HDR-VDP-2` (the acronym only). The paper's full title is "HDR-VDP-2: A calibrated visual metric for visibility and quality predictions in all luminance conditions." `refs.bib` carries the truncated title. Authoritative source: https://doi.org/10.1145/2010324.1964935.
- **Ref 24 (`desai2022`, SKM-TEA)** — bib carries `year = 2022` because that is when the arXiv preprint was posted; however, the peer-reviewed venue is **NeurIPS 2021 Datasets and Benchmarks Track (Round 2)**, held Dec 2021. A more accurate citation would be `@inproceedings` with `booktitle = {Advances in Neural Information Processing Systems Track on Datasets and Benchmarks}, year = {2021}`. Authoritative source: https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/03c6b06952c750899bb03d998e631860-Abstract-round2.html.
- **Ref 28 (`ding2020`, DISTS)** — bib carries `year = 2020` (the IEEE early-access deposit date) alongside `volume = 44, number = 5, pages = 2567-2581`. IEEE TPAMI finalized this paper in Vol. 44, No. 5, **May 2022** — reconcile year with pagination. Authoritative source: https://doi.org/10.1109/TPAMI.2020.3045810.
- **Ref 33 (`keshari2022`)** — arXiv lists **four authors**: Abhisek Keshari, Komal, Sadbhawna, Badri Subudhi. The PDF-printed reference and this bib entry list only "Keshari A, Subudhi B" — two middle authors (Komal and Sadbhawna, both mononyms) are **missing**. Authoritative source: https://export.arxiv.org/api/query?id_list=2204.09779.

**MINOR (6)**

- Ref 24 (`desai2022`) + Ref 51 (`desai2021`) venue upgrade — SKM-TEA has a NeurIPS 2021 D&B venue; VORTEX has a MIDL 2022 venue (PMLR v172, https://proceedings.mlr.press/v172/desai22a.html, best-paper award).
- Ref 46 (`simonyan2014`) venue formalization — VGG note field mentions ICLR 2015; could be promoted to `@inproceedings`.
- Author-name inconsistencies across entries (cosmetic):
  - Akshay Chaudhari: `Chaudhari, Akshay S.` vs `Chaudhari, Akshay`.
  - Christopher Ré: `Re, Christopher` vs `Ré, Christopher`.
  - Shreyas Vasanawala: `Vasanawala, Shreyas S.` vs `Vasanawala, Shreyas`.
- Ref 47 (`adamson2021`, SSFD workshop) — precursor workshop to the input paper itself. Cited legitimately; worth confirming the self-citation is intentional.

### Phase 3 — claim audit

**2 claim(s) require attention:**

- **C045 (knoll2020 ref #42) — MISATTRIBUTED**: network.2 The UNet models followed the architecture in the fastMRI challenge,42 while the unrolled models followed the fast iterative shrinkage-thresholding algorithm (FISTA) unrolled architecture43 i... See Details block for attestation. [→ jump to C045](#c045--knoll2020)
- **C055 (miao2008 ref #13) — MISATTRIBUTED**: where LoG is a rotationally symmetric Laplacian of Gaussian filter with a kernel size of 15 × 15 pixels and a standard deviation of 1.5 pixels.13 See Details block for attestation. [→ jump to C055](#c055--miao2008)

**Additional 4 claim(s) flagged as CITED_OUT_OF_CONTEXT** (typically claim-extractor artifacts — see Details):
- C067 (vandersluijs2023 ref #50)
- C068 (vandersluijs2023 ref #50)
- C075 (vandersluijs2023 ref #50)
- C076 (vandersluijs2023 ref #50)

## Summary

| ID | Section | Cite | Type | Support | Source page | Flag | Last verified |
|----|---------|------|------|---------|-------------|------|---------------|
| C001 | — | `lustig2007` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C002 | — | `sandino2020` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C003 | — | `hammernik2021` | BACKGROUND / FRAMING — represe | CONFIRMED | p. 1860 | — | 2026-04-17 |
| C004 | — | `hammernik2018` | BACKGROUND/FRAMING — example c | CONFIRMED | p. 1 | — | 2026-04-17 |
| C005 | — | `chen2022` | PARAPHRASED (high) — review ar | CONFIRMED | p. 238 | — | 2026-04-17 |
| C006 | — | `mason2020` | DIRECT — quantitative descript | CONFIRMED | p. 1064 | MINOR — the "1000 MR images" figure conflates M… | 2026-04-17 |
| C007 | — | `mason2020` | DIRECT — two sub-claims attrib | CONFIRMED | p. 1064 | — | 2026-04-17 |
| C008 | — | `chaudhari2018` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C009 | — | `chaudhari2020` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C010 | — | `mardani2019` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C011 | — | `zhouwang2011` | — | CONFIRMED | p. 1191 | — | 2026-04-17 |
| C012 | — | `wang2003` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C013 | — | `linzhang2011` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C014 | — | `miao2008` | — | CONFIRMED | p. 2541 | — | 2026-04-17 |
| C015 | — | `mantiuk2011` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C016 | — | `miao2013` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C017 | — | `salem2002` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C018 | — | `daly1992` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C019 | — | `sheikh2006` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C020 | — | `dameravenkata2000` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C021 | — | `ravishankar2011` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C022 | — | `kim2018` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C023 | — | `chan2021` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C024 | — | `kleineisel2025` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C025 | — | `desai2022` | PARAPHRASED (high) — SKM-TEA d | CONFIRMED | p. 1 | — | 2026-04-17 |
| C026 | — | `zhao2021` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C027 | — | `zhao2022` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C028 | — | `zhang2018` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C029 | — | `ding2020` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C030 | — | `cong2022` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C031 | — | `cheon2021` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C032 | — | `lao2022` | — | CONFIRMED | p. 2 | — | 2026-04-17 |
| C033 | — | `conde2022` | — | CONFIRMED | p. 3 | — | 2026-04-17 |
| C034 | — | `keshari2022` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C035 | — | `gu2022` | — | CONFIRMED | p. 2 | — | 2026-04-17 |
| C036 | — | `deng2009` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C037 | — | `raghu2019` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C038 | — | `mei2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C039 | — | `cadrinchenevert2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C040 | — | `huang2023` | — | CONFIRMED | p. 12 | — | 2026-04-17 |
| C041 | — | `kastryulin2023` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C042 | — | `wang2024` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C043 | — | `knoll2020` | BACKGROUND / POINTER (dataset  | CONFIRMED | p. 1 | — | 2026-04-17 |
| C044 | — | `sandino2020` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C045 | — | `knoll2020` | ARCHITECTURAL ATTRIBUTION — Ad | MISATTRIBUTED | p. 5 | MISCITATION (architecture attribution is to the… | 2026-04-17 |
| C046 | — | `xin2023` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C047 | — | `uecker2014` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C048 | — | `gu2022` | — | CONFIRMED | p. 3 | — | 2026-04-17 |
| C049 | — | `chen2022` | PARAPHRASED (high) — a summary | CONFIRMED | p. 238 | — | 2026-04-17 |
| C050 | — | `sheikh2006` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C051 | — | `sheikh2006` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C052 | — | `dameravenkata2000` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C053 | — | `zhouwang2004` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C054 | — | `zhouwang2004` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C055 | — | `miao2008` | — | MISATTRIBUTED | p. 2548 | REVIEW | 2026-04-17 |
| C056 | — | `chen2022` | PARAPHRASED (medium) — the ref | CONFIRMED | p. 238 | — | 2026-04-17 |
| C057 | — | `sandino2020` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C058 | — | `ding2020` | — | CONFIRMED | p. 5 | — | 2026-04-17 |
| C059 | — | `gu2022` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C060 | — | `gu2022` | — | CONFIRMED | p. 4 | — | 2026-04-17 |
| C061 | — | `simonyan2014` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C062 | — | `lustig2007` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C063 | — | `adamson2021` | BACKGROUND (high) — cites the  | CONFIRMED | p. 1 | — | 2026-04-17 |
| C064 | — | `pathak2016` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C065 | — | `dominic2023` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C066 | — | `mei2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C067 | — | `vandersluijs2023` | — | CITED_OUT_OF_CONTEXT | p. 1 | The claim-extractor has attached ref #50 to the… | 2026-04-17 |
| C068 | — | `vandersluijs2023` | — | CITED_OUT_OF_CONTEXT | p. 3 | Second claim-extraction artifact in paragraph 4… | 2026-04-17 |
| C069 | — | `vandersluijs2023` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C070 | — | `desai2021` | — | CONFIRMED | p. 1 | — | 2026-04-17 |
| C071 | — | `mason2020` | NON-ATTRIBUTION / FIGURE-FRAMI | CONFIRMED | p. 1066 | MINOR — C071 is likely a claim-extraction artif… | 2026-04-17 |
| C072 | — | `mason2020` | DIRECT — the ref-6 anchor "as  | CONFIRMED | p. 1064 | — | 2026-04-17 |
| C073 | — | `mei2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C074 | — | `cadrinchenevert2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C075 | — | `vandersluijs2023` | — | CITED_OUT_OF_CONTEXT | p. 1 | Third instance in this manuscript of the claim-… | 2026-04-17 |
| C076 | — | `vandersluijs2023` | — | CITED_OUT_OF_CONTEXT | p. 3 | Fourth instance of the claim-extractor over-tag… | 2026-04-17 |
| C077 | — | `wang2024` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C078 | — | `li2020` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C079 | — | `jin2019` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C080 | — | `mason2020` | BACKGROUND / PRECEDENT — Mason | CONFIRMED | p. 1064 | — | 2026-04-17 |
| C081 | — | `mei2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C082 | — | `cadrinchenevert2022` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C083 | — | `kastryulin2023` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C084 | — | `dar2019` | — | CONFIRMED | p. — | — | 2026-04-17 |
| C085 | — | `mason2020` | PARAPHRASED — Adamson claims t | CONFIRMED | p. 1064 | MINOR — Mason 2020 does not literally recommend… | 2026-04-17 |
| C086 | — | `wang2024` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |
| C087 | — | `luisier2008` | — | CONFIRMED | p. — | none | 2026-04-17 |
| C088 | — | `desai2023` | PENDING (source PDF unavailabl | PENDING | p. — | NEEDS_PDF | 2026-04-17 |

## Details

### C001 — lustig2007

**Section:** 
**Citekey:** `lustig2007` (ref #1)
**Claim text:** Compressed sensing and deep learning (DL) techniques offer significant potential to accelerate MR acquisitions and remain an active area of research.1–4 Metrics such as normalized root mean square error (NRMSE), peak signal-to-noise ratio (PSNR), and structural similarity index measure (SSIM) are routinely used to assess the image quality (IQ) of MR image reconstructions and benchmark research methods,5 but are used out of convention rather than because they are particularly well-suited metrics for assessing perceptual IQ.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/lustig2007.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C002 — sandino2020

**Section:** 
**Citekey:** `sandino2020` (ref #2)
**Claim text:** Compressed sensing and deep learning (DL) techniques offer significant potential to accelerate MR acquisitions and remain an active area of research.1–4 Metrics such as normalized root mean square error (NRMSE), peak signal-to-noise ratio (PSNR), and structural similarity index measure (SSIM) are routinely used to assess the image quality (IQ) of MR image reconstructions and benchmark research methods,5 but are used out of convention rather than because they are particularly well-suited metrics for assessing perceptual IQ.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sandino2020.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C003 — hammernik2021

**Section:** Introduction (opening framing)
**Citekey:** `hammernik2021` (ref #3)
**Claim text:** Compressed sensing and deep learning (DL) techniques offer significant potential to accelerate MR acquisitions and remain an active area of research.1–4
**Sub-claim attributed:** Ref 3 (Hammernik et al. 2021) is cited as one of several DL / iterative MR reconstruction works demonstrating that DL for accelerated MRI is an active area of research. The citation is a representative-example (BACKGROUND / FRAMING) reference, not a specific quantitative claim.
**Claim type:** BACKGROUND / FRAMING — representative citation for DL-based accelerated parallel MRI reconstruction as an active research area.
**Source excerpt:**
- Title: "Systematic evaluation of iterative deep neural networks for fast parallel MRI reconstruction with sensitivity-weighted coil combination" (Magn Reson Med. 2021;86:1859–1872).
- Abstract — Purpose: "To systematically investigate the influence of various data consistency layers and regularization networks with respect to variations in the training and test data domain, for sensitivity-encoded accelerated parallel MR image reconstruction."
- Abstract — Theory and Methods: "Magnetic resonance (MR) image reconstruction is formulated as a learned unrolled optimization scheme with a down-up network as regularization and varying data consistency layers. The proposed networks are compared to other state-of-the-art approaches on the publicly available fastMRI knee and neuro dataset and tested for stability across different training configurations regarding anatomy and number of training samples."
- Abstract — Conclusion: "The study provides insights into the robustness, properties, and acceleration limits of state-of-the-art networks, and our proposed down-up networks. These key insights provide essential aspects to successfully translate learning-based MRI reconstruction to clinical practice..."
- Keywords: "data consistency, deep learning, domain shift, down-up networks, fastMRI, iterative image reconstruction, parallel imaging".
- Introduction (p. 1860): "Parallel imaging (PI) forms the foundation of accelerated data acquisition in magnetic resonance imaging (MRI)... In the last decade, PI combined with compressed sensing (CS) techniques has resulted in substantial improvements in acquisition speed and image quality. Although PI-CS can achieve state-of-the-art performance, designing effective regularization schemes and tuning of hyper-parameters are not trivial. Starting in 2016, deep learning algorithms have become extremely popular and effective tools in data-driven learning of inverse problems and have enabled progress beyond the limitations of CS."
- Introduction (p. 1860): "Deep learning for image reconstruction is an enormously fast-growing field..."
- Introduction (p. 1861): "The aim of this work is to bridge the gap of the aforementioned challenges that we have observed in deep learning for parallel MRI reconstruction. We study the influence of regularization networks, DC layers, and variations in the data, in a controlled experimental setup... the first work that studies the effect of different training data configurations, including variations in anatomies and sample size, for neural network reconstructions at a large scale, using the publicly available fastMRI datasets with approximately 5400 training cases."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       14 pages (MRM vol. 86, no. 4, pp. 1859–1872, 2021).
  Section checklist:  Title page ✓, Abstract (Purpose / Theory & Methods / Results / Conclusion) ✓,
                      Keywords ✓, §1 Introduction ✓, Table 1 (overview of related 2D MRI reconstruction work) ✓,
                      §2 Theory incl. §2.1 Learning unrolled optimization, §2.1.1 Regularization networks,
                      §2.1.2 Data consistency ✓, Figure 1 (DUNET architecture) ✓.
  Phrasings searched: "deep learning" / "deep neural networks" (architecture/framing);
                      "accelerated" / "fast" / "parallel MRI" / "parallel imaging" (acquisition framing);
                      "compressed sensing" / "CS" (context vs CS);
                      "reconstruction" / "iterative" / "unrolled" (method framing);
                      "active area" / "fast-growing field" / "popular" (research-activity paraphrases).
  Specific checks:    Title explicitly names "iterative deep neural networks for fast parallel MRI reconstruction"
                      — a direct match for the claim that DL is used for accelerating MR acquisitions.
                      Introduction explicitly states "Deep learning for image reconstruction is an enormously
                      fast-growing field" — a near-verbatim paraphrase of "active area of research".
                      Table 1 catalogs ~23 DL-based 2D MRI reconstruction works, directly evidencing an active field.
                      The abstract frames the work as studying "sensitivity-encoded accelerated parallel MR image
                      reconstruction" via learned unrolled optimization — confirming the DL+acceleration pairing.
  Closest adjacent passage: "deep learning algorithms have become extremely popular and effective tools in
                      data-driven learning of inverse problems and have enabled progress beyond the limitations
                      of CS" (p. 1860) — directly supports the CS+DL/acceleration/active-research framing.
  Indirect-attribution check: Hammernik et al. frame DL-accelerated MRI as active research in their own
                      introduction, citing survey papers (refs 10–13) for further reading; citing this paper as
                      one of the active-research exemplars (ref 3 in Adamson et al.) is appropriate.
  Out-of-context check: Adamson et al. cite Hammernik 2021 in a list (refs 1–4) of representative CS/DL MR
                      acceleration works. Hammernik 2021 is squarely within scope — it is a full-paper systematic
                      evaluation of DL-based accelerated parallel MRI reconstruction. Usage is consistent.

---

### C004 — hammernik2018

**Section:** Introduction (opening framing)
**Citekey:** `hammernik2018` (ref #4)
**Claim text:** Compressed sensing and deep learning (DL) techniques offer significant potential to accelerate MR acquisitions and remain an active area of research.1–4
**Sub-claim attributed:** ref #4 (Hammernik et al. 2018) is cited as one of several example works demonstrating DL (and/or DL-with-CS) techniques for accelerated MR acquisition/reconstruction.
**Claim type:** BACKGROUND/FRAMING — example citation supporting the general assertion that DL methods are used to accelerate MR.
**Source excerpt:**
- Title: "Learning a Variational Network for Reconstruction of Accelerated MRI Data" (p. 1).
- Abstract, Purpose (p. 1): "To allow fast and high-quality reconstruction of clinical accelerated multi-coil MR data by learning a variational network that combines the mathematical structure of variational models with deep learning."
- Abstract, Theory and Methods (p. 1): "Generalized compressed sensing reconstruction formulated as a variational model is embedded in an unrolled gradient descent scheme. All parameters of this formulation, including the prior model defined by filter kernels and activation functions as well as the data term weights, are learned during an offline training procedure."
- Abstract, Key words (p. 1): "Variational Network; Deep Learning; Accelerated MRI; Parallel Imaging; Compressed Sensing; Image Reconstruction".
- Introduction (p. 2): "The goal of the current work is to demonstrate that the concept of learning can also be used at the earlier stage of image formation. In particular, we focus on image reconstruction for accelerated MRI, which is commonly accomplished with frameworks like Parallel Imaging (PI) (11–13) or Compressed Sensing (CS) (14–16)."
- Introduction (p. 3): "In this work, we introduce an efficient trainable formulation for accelerated PI-based MRI reconstruction that we term variational network (VN). The VN embeds a generalized CS concept, formulated as a variational model, within a deep learning approach."
- Discussion (p. 18): "In this work, we present the first learning-based MRI reconstruction approach for clinical multi-coil data. Our VN architecture combines two fields: variational methods and deep learning."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       28 pages (arXiv:1704.00447v1, submitted to Magnetic Resonance in Medicine; 54 references; 10 figures/tables).
  Section checklist:  Title/Author page ✓, Abstract (Purpose / Theory and Methods / Results / Conclusion / Key words) ✓,
                      Introduction ✓, Theory (From Linear Reconstruction to a Variational Network) ✓,
                      Methods (VN Parameters, Training, Data Acquisition, Experimental Setup, Evaluation, Implementation) ✓,
                      Results ✓, Figures 1–9 and captions ✓, Table 1 (MSE/SSIM evaluation) ✓,
                      Discussion ✓, Conclusion ✓, Acknowledgements ✓,
                      Appendix A (IIPG algorithm) ✓, Appendix B (gradient derivations) ✓, References (54) ✓,
                      Supplementary Material listing ✓.
  Phrasings searched: "deep learning" (literal);
                      "variational network" / "learning-based" / "learned" (method-level paraphrases);
                      "accelerated MRI" / "accelerated MR" / "undersampled" / "acceleration factor" (acceleration paraphrases);
                      "reconstruction" / "image reconstruction" / "image formation" (reconstruction-target paraphrases);
                      "compressed sensing" / "CS" / "parallel imaging" / "PI" (prior-framework references to confirm CS+DL overlap).
  Specific checks:    Title itself pairs "Learning" with "Accelerated MRI Data" — directly attesting DL for accelerated MR.
                      Abstract explicitly frames the method as combining "variational models with deep learning" to reconstruct
                      "clinical accelerated multi-coil MR data." Key words list both "Deep Learning" and "Accelerated MRI"
                      (plus "Compressed Sensing"), so the paper squarely belongs to the DL-for-accelerated-MR category
                      that ref 4 is cited to exemplify. Introduction (p. 2–3) and Discussion (p. 18) re-attest this framing.
  Closest adjacent passage: "we focus on image reconstruction for accelerated MRI ... we introduce an efficient trainable
                      formulation for accelerated PI-based MRI reconstruction ... The VN embeds a generalized CS concept ...
                      within a deep learning approach" (pp. 2–3) — near-verbatim support for the sub-claim.
  Indirect-attribution check: Hammernik et al. present this as their own methodological contribution; the DL-for-accelerated-MR
                      framing is primary to the paper, not borrowed from another source. Primary source is appropriate.
  Out-of-context check: Adamson et al. cite ref 4 as a background/framing example (one of 1–4) for the general statement that
                      DL and CS are used to accelerate MR acquisitions. Hammernik et al.'s paper is exactly such a work
                      (DL + CS-inspired variational network, applied to clinical accelerated multi-coil knee MRI). Usage is consistent.

---

### C005 — chen2022

**Section:** Introduction (abstract / opening framing)
**Citekey:** `chen2022` (ref #5)
**Claim text:** Compressed sensing and deep learning (DL) techniques offer significant potential to accelerate MR acquisitions and remain an active area of research.1–4 Metrics such as NRMSE, PSNR, and SSIM are routinely used to assess the image quality (IQ) of MR image reconstructions and benchmark research methods,5 but are used out of convention rather than because they are particularly well-suited metrics for assessing perceptual IQ.
**Claim type:** PARAPHRASED (high) — review article attested as evidence that SSIM/PSNR/NRMSE are the dominant quantitative IQ metrics across the MR-reconstruction literature.
**Sub-claim attributed:** "NRMSE, PSNR, and SSIM are routinely used to assess IQ of MR image reconstructions and benchmark research methods". The framing qualifier ("used out of convention ... not ... well-suited for perceptual IQ") is not attributed to ref 5 and is not evaluated here.
**Source excerpt:**
- p. 239 (§V-C, Evaluation Metrics): "To compare the reconstructed images with the ground truth, most studies reported the structural similarity index measure (SSIM) and the peak signal-to-noise ratio (PSNR) [see Fig. 4(b)]. Fewer used NRMSE, MSE, and the signal-to-noise ratio (SNR). NRMSE and SSIM became more popular over time, whereas PSNR and NMSE decreased in popularity."
- p. 239: "Thus, quantitative metrics, such as SSIM, PSNR, and NRMSE, were the most prevalent."
- p. 241 (§VI Challenges): "we encourage future studies to test their model performance on commonly used datasets ... and metrics (PSNR and SSIM) and report performance on both training and testing datasets."
- Fig. 4(b) caption (p. 238): bar chart of "Metrics used by different studies" — abbreviations confirm SSIM, PSNR, NRMSE, MSE, SNR, NMSE, HFEN, RMSE as the reported metrics.
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       22 pages (Proc. IEEE, vol. 110, no. 2, pp. 224–245)
  Section checklist:  Abstract ✓, Intro (§I) ✓, Architectures (§II) ✓, Image redundancy (§III) ✓,
                      Meta-analysis method (§IV) ✓, Meta-analysis results (§V incl. §V-C Evaluation Metrics) ✓,
                      Challenges (§VI) ✓, Conclusion & Outlook (§VII) ✓, References ✓,
                      Tables (Tables 1–3) ✓, Figure captions (Figs. 1–5 incl. Fig. 4(b) bar chart of metrics) ✓,
                      Supplementary Material — referenced but not fetched (n/a; prose summary in §V-C is adequate for this claim).
  Phrasings searched: "SSIM", "PSNR", "NRMSE" (literal metric names);
                      "most prevalent" / "most commonly used" / "routinely" (frequency-of-use paraphrases);
                      "structural similarity" / "peak signal-to-noise" / "normalized root mean square error" (expanded forms);
                      "evaluation metrics" / "benchmark" / "quantitative metrics" (semantic paraphrases).
  Specific checks:    §V-C prose (pp. 238–240) states outright that SSIM and PSNR are the most-reported metrics,
                      followed by NRMSE / MSE / SNR; Fig. 4(b) caption abbreviations list reflects this ordering;
                      §VI recommends SSIM and PSNR as "commonly used" metrics for future work.
  Closest adjacent passage: "quantitative metrics, such as SSIM, PSNR, and NRMSE, were the most prevalent" (p. 239) — near-verbatim support.
  Indirect-attribution check: Chen et al. do not attribute this empirical observation to another source; it is the paper's own meta-analysis finding over 92 studies. Primary source is appropriate.
  Out-of-context check: Chen's §V-C reports this as an observed trend in the CS-MRI literature; Adamson et al. cite it in the introduction as framing for why those metrics dominate benchmarking. Usage is consistent.

---

### C006 — mason2020

**Section:** Introduction (opening framing, paragraph 1)
**Citekey:** `mason2020` (ref #6)
**Claim text:** In a reader study of 1000 MR images evaluated by five radiologists across various degradation types, Mason et al. demonstrated that NRMSE, SSIM, and PSNR have weaker concordance with radiologist-perceived diagnostic IQ6 than several less commonly-reported IQ metrics.
**Claim type:** DIRECT — quantitative description of the cited study's design (N images, N radiologists, degradation diversity) and its headline finding (conventional metrics under-perform vs. less-common ones).
**Sub-claim attributed:** (a) reader-study design: "1000 MR images" rated by "five radiologists" across "various degradation types"; (b) finding: NRMSE/SSIM/PSNR correlate less well with radiologist-perceived diagnostic IQ than several less-commonly-reported IQ metrics.
**Source excerpt:**
- Abstract (p. 1064): "The comparison uses a database of MR images of the brain and abdomen that have been retrospectively degraded by noise, blurring, undersampling, motion, and wavelet compression for a total of 414 degraded images. A total of 1017 subjective scores were assigned by five radiologists."
- Abstract (p. 1064): "When considering SROCC calculated from combining scores from all radiologists across all image types, RMSE and SSIM had lower SROCC than six of the other IQMs included in the study (VIF, FSIM, NQM, GMSD, IWSSIM, and HDRVDP)."
- §II.C Radiologist Image Quality Assessment (p. 1066): "Three body radiologists and two neuro radiologists were involved in the study."
- §II.A/Table I (p. 1066): six degradation techniques — white Gaussian noise, Gaussian blur, Rician noise, undersampling, wavelet compression, motion — each applied at four strengths to the 18 reference images, yielding 414 total images.
- Fig. 4 / §III Discussion (p. 1069): "Overall, VIF had the highest SROCC values. … VIF, FSIM, and NQM perform statistically better than the other IQMs included in the study. SSIM did not perform statistically better than any another IQM including RMSE."
- §IV Conclusion (p. 1071–1072): "SSIM and RMSE demonstrated statistically worse performances than other metrics evaluated, suggesting that SSIM and RMSE are potentially not ideal surrogate measures of MR image quality as determined by radiologist evaluation. The VIF, FSIM, and NQM demonstrated the highest correlation with radiologists' opinions of MR image quality."
**Support:** CONFIRMED with minor numerical imprecision
**Flag:** MINOR — the "1000 MR images" figure conflates Mason's reported totals. Mason's testing library is **414 degraded images**; the **1017** number cited by Mason is the total count of subjective scores (radiologist-image ratings), not the count of images. Adamson et al.'s "1000 MR images" appears to be a rounded/paraphrased form of the "1017 subjective scores" figure. PSNR is not explicitly ranked in Mason's abstract sentence (which names RMSE and SSIM); however PSNR is a strict monotone transform of RMSE (PSNR = 20·log(max/RMSE)) so SROCC rankings are identical, and PSNR is included alongside RMSE/SSIM in Mason's "bottom performers" group (Fig. 4, Table IV). "NRMSE" is used by Adamson, where Mason measured RMSE; SROCC is invariant to normalization, so the ranking claim transfers.
**Remediation:** Consider replacing "1000 MR images" with "414 MR images receiving 1017 subjective scores" (or "a reader study with 1017 subjective scores by five radiologists on 414 degraded MR images") for numerical precision. The qualitative finding is fully supported.
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Introduction ✓, §II Methods and Materials (A. Image Library, B. Objective IQMs,
                      C. Radiologist IQ Assessment, D. Data Analysis, E. IQM Calculation Times) ✓,
                      §III Results (Fig. 3, 4; Tables III–VII) ✓, §IV Discussion ✓, §V Conclusion ✓,
                      References [1]–[36] ✓, Figs. 1–4 ✓, Tables I–VII ✓.
  Phrasings searched: "1000", "1017", "414", "five radiologists", "three body", "two neuro" (design numerics);
                      "RMSE", "NRMSE", "SSIM", "PSNR" vs. "VIF", "FSIM", "NQM" (metric comparisons);
                      "lower SROCC", "weaker correlation", "statistically worse", "perform better than"
                      (performance-ranking paraphrases);
                      "degradation", "white noise", "Rician", "blur", "motion", "undersampling",
                      "wavelet compression" (degradation-type check).
  Specific checks:    N=5 radiologists — confirmed explicitly in §II.C: "Three body radiologists and two neuro radiologists".
                      N=414 degraded images — confirmed in §II.A ("total image library of 414 images").
                      N=1017 subjective scores — confirmed in Abstract ("A total of 1017 subjective scores were assigned by five radiologists").
                      Six degradation types — confirmed in §II.A and Table I (white Gaussian noise, Gaussian blur, motion, Rician
                      noise, undersampling, wavelet compression). Motion was applied only to brain images.
                      Ranking of RMSE/SSIM vs. others — confirmed in Abstract and Fig. 4. "RMSE and SSIM had lower SROCC than
                      six of the other IQMs included in the study (VIF, FSIM, NQM, GMSD, IWSSIM, and HDRVDP)."
                      PSNR-rank relation to RMSE — SROCC is invariant to monotonic transforms; §II.B defines
                      PSNR = 20·log(max/RMSE), confirming identical SROCC ranking.
  Closest adjacent passage: "RMSE and SSIM had lower SROCC than six of the other IQMs" (Abstract) — a near-verbatim paraphrase
                      of Adamson's "weaker concordance … than several less commonly-reported IQ metrics".
  Indirect-attribution check: Mason et al. report the SROCC rankings and reader-study numerics as their own primary findings,
                      not secondary citations — direct-source attribution by Adamson is appropriate.
  Out-of-context check: Mason's explicit recommendation ("SSIM and RMSE are potentially not ideal surrogate measures of MR
                      image quality … VIF, FSIM, and NQM demonstrated the highest correlation") matches Adamson's framing that
                      conventional metrics are inferior to less commonly reported ones. Usage is consistent.
  Numerical-fidelity check: Adamson writes "1000 MR images"; Mason reports 414 images / 1017 scores. The 1000 figure appears
                      to be a rounded form of the 1017 subjective-score total rather than the image count. This is a minor
                      quantitative imprecision but does not affect the qualitative claim.

---

### C007 — mason2020

**Section:** Introduction (paragraph 2 — selection of comparator metrics)
**Citekey:** `mason2020` (ref #6)
**Claim text:** As the aforementioned metrics were rigorously assessed in the Mason study,6 we include only the best overall performing metric (VIF)
**Claim type:** DIRECT — two sub-claims attributed to Mason: (a) the study rigorously assessed a set of classical IQ metrics (IWSSIM, MSSSIM, FSIM, perceptual difference models, VIF, NQM — the "aforementioned" metrics from the preceding sentences); (b) VIF is identified as the best overall performer.
**Sub-claim attributed:** (a) rigor of Mason's IQ-metric evaluation; (b) VIF identified as the best-overall IQ metric.
**Source excerpt:**
- Abstract (p. 1064): "IQM performance was measured via the Spearman rank order correlation coefficient (SROCC) and statistically significant differences in the residuals of the IQM scores and radiologists' scores were tested."
- §II.B Objective IQMs (p. 1066): "Ten full-reference objective IQMs were included in this study: RMSE, peak signal to noise ratio (PSNR), SSIM, multi-scale SSIM (MSSSIM), information-weighted SSIM (IWSSIM), gradient magnitude similarity deviation (GMSD), feature similarity index (FSIM), high dynamic range visible difference predictor (HDRVDP), noise quality metric (NQM), and visual information fidelity (VIF)."
- §II.D Data Analysis (p. 1068): "A variance-based hypothesis test was performed to measure statistical significance in the difference in the performance of the IQMs. First, a non-linear regression was performed on the IQM scores according to the equation [33] … The residuals between the IQM scores after the regression and the radiologists scores were calculated … To test for statistical differences in the variance of residuals an F-test of equality of variances was performed … Since each IQM was compared to all nine other IQMs, a Benjamini-Hochberg correction for false discovery rate controlling was performed [34]."
- §III Results (p. 1069): "Overall, VIF had the highest SROCC values."
- §III Discussion (p. 1069–1070): "After normalizing each radiologist's score and combining scores across all images, we found that VIF exhibited the highest SROCC of all the metrics evaluated in this study. These results suggest that VIF provides the most accurate surrogate measure of subjective image quality scores of a radiologist of the IQMs included in this study."
- §IV Conclusion (p. 1071–1072): "The VIF, FSIM, and NQM demonstrated the highest correlation with radiologists' opinions of MR image quality."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Intro ✓, §II.A Image Library ✓, §II.B Objective IQMs (lists all ten IQMs) ✓,
                      §II.C Radiologist IQ Assessment ✓, §II.D Data Analysis (SROCC, F-test, BH correction) ✓,
                      §II.E Calculation Times ✓, §III Results (Fig. 3, 4; Tables III–VII) ✓, §IV Discussion ✓,
                      §V Conclusion ✓, References [1]–[36] ✓.
  Phrasings searched: "rigorous" / "systematic" / "statistical" / "hypothesis test" / "significance" (rigor paraphrases);
                      "VIF" / "highest SROCC" / "best" / "top-performing" / "most accurate" (best-overall paraphrases);
                      "Benjamini-Hochberg" / "F-test" / "residuals" / "SROCC" (analytical-method terms);
                      "IWSSIM" / "MSSSIM" / "FSIM" / "NQM" (aforementioned-metric check).
  Specific checks:    Rigor of assessment — Mason performs (i) SROCC on the combined radiologist-IQM scores, (ii) non-linear
                      regression to allow variance-based residual comparison, (iii) F-test of equality of residual variance,
                      and (iv) Benjamini-Hochberg FDR correction for multiple comparisons across 10 IQMs. Assessment is
                      broken out by radiologist (Table IV), reference image type (Table V), and degradation type (Table VI).
                      The description "rigorously assessed" is supported.
                      Best-overall metric — VIF is explicitly identified as the metric with the highest SROCC when combining
                      scores across all radiologists and image types (Fig. 4 "Combined" group; §III "Overall, VIF had the
                      highest SROCC values"; Discussion "VIF exhibited the highest SROCC of all the metrics evaluated").
                      Aforementioned metrics coverage — Adamson's preceding sentences name IWSSIM, MSSSIM, FSIM, VIF, NQM;
                      each of these was evaluated by Mason (per §II.B), so the "rigorously assessed" scope is accurate.
  Closest adjacent passage: "VIF exhibited the highest SROCC of all the metrics evaluated in this study" (p. 1070) —
                      near-verbatim support for "best overall performing metric (VIF)".
  Indirect-attribution check: Mason's SROCC and significance-testing results are primary findings of the cited paper;
                      direct attribution is appropriate.
  Out-of-context check: Adamson uses Mason to justify narrowing the comparator set to VIF; Mason's conclusion does endorse
                      VIF as top-performing overall. Usage is consistent, though Adamson further adds NQM and HFEN to the
                      state-of-the-art set in subsequent text (also supported by Mason's recommendation of NQM and FSIM).
  Rigor-claim check: Mason's analysis includes BH-corrected F-tests on non-linear-regression residuals, across three
                      subgroup partitions (by radiologist, by image type, by degradation type) — this is rigorous by
                      IQM-evaluation standards.

---

### C008 — chaudhari2018

**Section:** 
**Citekey:** `chaudhari2018` (ref #7)
**Claim text:** Although a handful of studies use radiologist reader scores directly to assess reconstruction methods,7–9 conducting such time- and resource-intensive reviews for all methods is expensive, slows benchmarking, and is generally impractical.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/chaudhari2018.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C009 — chaudhari2020

**Section:** 
**Citekey:** `chaudhari2020` (ref #8)
**Claim text:** Although a handful of studies use radiologist reader scores directly to assess reconstruction methods,7–9 conducting such time- and resource-intensive reviews for all methods is expensive, slows benchmarking, and is generally impractical.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/chaudhari2020.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C010 — mardani2019

**Section:** 
**Citekey:** `mardani2019` (ref #9)
**Claim text:** Although a handful of studies use radiologist reader scores directly to assess reconstruction methods,7–9 conducting such time- and resource-intensive reviews for all methods is expensive, slows benchmarking, and is generally impractical.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mardani2019.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C011 — zhouwang2011

- **C011 (ref #10):** Information-weighted SSIM (IWSSIM10) weights SSIM by assigning higher importance to regions of the image based on their information content.
- **Type:** DIRECT
- **Source:** Wang Z, Li Q. "Information Content Weighting for Perceptual Image Quality Assessment." IEEE Transactions on Image Processing, Vol. 20, No. 5, May 2011, pp. 1185–1198. DOI: 10.1109/TIP.2010.2092435

### Verdict
**DIRECT, high.** The source paper explicitly defines the Information Content Weighted SSIM (IW-SSIM) measure, and the weights are defined per-region as a local information content measure derived from mutual information in a GSM-based perceptual channel model.

### Verification against verification checklist

#### (a) Paper defines IW-SSIM
Yes, explicitly:

- Title: "Information Content Weighting for Perceptual Image Quality Assessment" — the entire paper is devoted to the construction.
- Section III.B is titled "Information Content Weighted MultiScale SSIM" and defines IW-SSIM in Eq. (45)–(47):
  - Eq. (45): `IW-SSIM_j = Σ_i w_{j,i} · c(x_{j,i}, y_{j,i}) · s(x_{j,i}, y_{j,i}) / Σ_i w_{j,i}` for scales j = 1, …, M−1.
  - Eq. (46): `IW-SSIM_j = (1/N_j) Σ_i l(x_{j,i}, y_{j,i}) · c(x_{j,i}, y_{j,i}) · s(x_{j,i}, y_{j,i})` for j = M.
  - Eq. (47): `IW-SSIM = Π_{j=1..M} (IW-SSIM_j)^{β_j}`.
- Abstract: "the best overall performance is achieved by combining information content weighting with multiscale structural similarity measures."

#### (b) It weights SSIM by information content (mutual-information / entropy based)
Yes:

- Section III.B, at Eq. (45) (p. 1191): "Let `w_{j,i}` be the information content weight computed at the ith spatial location in the jth scale using (28), the jth scale IW-SSIM measure is defined as [Eq. (45)]."
- Eq. (45) is a classical weighted average of local SSIM(c·s) components with weights `w_{j,i}` in numerator and normalizer `Σ w_{j,i}` in denominator — i.e., regions/patches are weighted by information content.
- The weight `w` is defined as a mutual-information-based local information content measure. Section II (p. 1188), Eq. (12): "`w = I(R;E) + I(D;F) − I(E;F)`." Each term is a mutual information (computed via determinants of covariance matrices of Gaussian/GSM signals, Eqs. (13)–(15)).
- Section II motivates this as: "Using statistical information theory, the local information content can be quantified in units of bit, provided that a statistical image model is available. The local information content measure can then be employed for IQA weighting" (p. 1187).
- Fig. 4 (p. 1190) shows the "local information content maps" for an example image and states that brighter regions "indicate more information content and, thus, higher visual importance in IQA," directly tying information content to per-region weighting.

### Attestation log (≥3 phrasings from source)

1. **Abstract (p. 1185):** "This paper aims to test the hypothesis that when viewing natural images, the optimal perceptual weights for pooling should be proportional to local information content, which can be estimated in units of bit using advanced statistical models of natural images. … First, information content weighting leads to consistent improvement in the performance of IQA algorithms. … Third, the best overall performance is achieved by combining information content weighting with multiscale structural similarity measures."

2. **Section II, p. 1187:** "Using statistical information theory, the local information content can be quantified in units of bit, provided that a statistical image model is available. The local information content measure can then be employed for IQA weighting."

3. **Section II, Eq. (12), p. 1188:** "we compute the sum of I(R;E) and I(D;F) minus the common information shared between E and F. This results in a total information content weight measure given by `w = I(R;E) + I(D;F) − I(E;F)`" — the weight is explicitly a mutual-information-based quantity.

4. **Section III.B, p. 1191, Eq. (45):** "Let `w_{j,i}` be the information content weight computed at the ith spatial location in the jth scale using (28), the jth scale IW-SSIM measure is defined as `IW-SSIM_j = Σ_i w_{j,i} c(x_{j,i},y_{j,i}) s(x_{j,i},y_{j,i}) / Σ_i w_{j,i}`."

5. **Section III.B, Eq. (47), p. 1191:** "The final overall IW-SSIM measure is then computed as `IW-SSIM = Π_{j=1..M} (IW-SSIM_j)^{β_j}`."

6. **Fig. 4 caption and surrounding text (p. 1190):** "Corresponding information content maps computed at four scales … Brighter indicates larger information content. … higher visual importance in IQA" — visually confirms the per-region weighting by information content.

### Notes
- The weighting is defined at the local (sliding-window) level over Laplacian-pyramid subband coefficients with a 3×3 spatial neighborhood plus one parent coefficient (K = 10; Section II end / Section III.A), so "regions" in the Adamson et al. phrasing aligns with the per-location local neighborhoods used in IW-SSIM.
- IW-SSIM is the multiscale variant; a single-scale IW-SSIM is not separately named, but Eqs. (45)–(47) use MS-SSIM-style scale weights (β_1…β_5) with the IW-weighted c·s terms. The Adamson et al. wording "IWSSIM" is consistent with this definition.

### Verdict
`C011: DIRECT, high`

---

### C012 — wang2003

**Claim (Adamson et al. 2025, ref #11):** Multiscale SSIM (MSSSIM11) computes SSIM at various resolution levels across the image.

**Classification:** DIRECT

**Verdict:** SUPPORTED

**Source:** Wang, Simoncelli, and Bovik, "Multi-Scale Structural Similarity for Image Quality Assessment," Proc. 37th IEEE Asilomar Conf. on Signals, Systems and Computers, 2003.

### Attestation log (>=3 phrasings)

1. **Title (page 1):** "MULTI-SCALE STRUCTURAL SIMILARITY FOR IMAGE QUALITY ASSESSMENT" — the paper's central contribution is explicitly a multi-scale version of SSIM.

2. **Abstract (page 1):** "This paper proposes a multi-scale structural similarity method, which supplies more flexibility than previous single-scale methods in incorporating the variations of viewing conditions." — establishes that MS-SSIM generalizes single-scale SSIM to multiple scales.

3. **Section 3.1, page 2:** "Multi-scale method is a convenient way to incorporate image details at different resolutions. We propose a multi-scale SSIM method for image quality assessment whose system diagram is illustrated in Fig. 1. Taking the reference and distorted image signals as the input, the system iteratively applies a low-pass filter and downsamples the filtered image by a factor of 2. We index the original image as Scale 1, and the highest scale as Scale M, which is obtained after M - 1 iterations. At the j-th scale, the contrast comparison (2) and the structure comparison (3) are calculated and denoted as c_j(x,y) and s_j(x,y), respectively." — explicit description of computing SSIM components at multiple resolution scales via iterative downsampling.

4. **Eq. (7), page 2:** "SSIM(x, y) = [l_M(x,y)]^{alpha_M} * prod_{j=1}^{M} [c_j(x,y)]^{beta_j} [s_j(x,y)]^{gamma_j}" — the MS-SSIM formula explicitly combines contrast and structure comparisons computed at each of M scales.

5. **Fig. 1 caption, page 2:** "Multi-scale structural similarity measurement system. L: low-pass filtering; 2 down-arrow: downsampling by 2." — diagram shows SSIM sub-measures computed at each successive downsampled resolution.

6. **Section 5, page 4:** "We propose a multi-scale structural similarity approach for image quality assessment, which provides more flexibility than single-scale approach in incorporating the variations of image resolution and viewing conditions."

### Notes

The claim is a textbook-level description of the paper's method. The paper explicitly defines MS-SSIM as iteratively applying low-pass filtering and 2x downsampling, then computing SSIM contrast/structure sub-measures at each resulting resolution scale (Scales 1 through M) and combining them via Eq. (7). The claim's phrase "at various resolution levels across the image" corresponds exactly to the paper's "Scale 1" through "Scale M" construction. DIRECT support.

---

### C013 — linzhang2011

**C013 (ref #12):** "Information-weighted SSIM (IWSSIM10) weights SSIM by assigning higher importance to regions of the image based on their information content. Multiscale SSIM (MSSSIM11) computes SSIM at various resolution levels across the image, while feature similarity index measure (FSIM12) compares features such as texture, edges, and gradients extracted with hand-crafted filters."

Sub-claim for ref 12 (linzhang2011): FSIM compares features such as texture, edges, and gradients extracted with hand-crafted filters.

### Classification

**DIRECT / ARCHITECTURAL** — this is a direct claim about what FSIM's method does (which features it compares and how they are extracted). linzhang2011 is the defining paper for FSIM and is the proper source.

### Source

- Zhang L, Zhang L, Mou X, Zhang D. "FSIM: A Feature Similarity Index for Image Quality Assessment." IEEE Transactions on Image Processing, 2011.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/linzhang2011.pdf`

### Verdict

**SUPPORTED (with a minor qualification on terminology)** — linzhang2011 defines FSIM exactly as a similarity index computed by comparing two hand-crafted low-level feature maps: phase congruency (PC), extracted via a bank of 2D log-Gabor quadrature filters, and gradient magnitude (GM), computed with a classical Sobel operator. Both feature extractors are explicitly hand-crafted (fixed analytic/convolutional filters — not learned), and both index the structural attributes Adamson summarizes as "texture, edges, and gradients." The gradient part is literally present (Sobel-derived gradient magnitude); the "edges / texture" part maps onto phase congruency, which the FSIM paper introduces precisely as a feature-detection model for edges, lines, and other low-level structure. Adamson's paraphrase "features such as texture, edges, and gradients extracted with hand-crafted filters" is a reasonable plain-English rendering of FSIM's PC + GM design; the only slight looseness is that the paper frames PC in terms of "low-level features / structural significance" rather than "texture" per se, but PC does respond to textured / edge / line structure, so the paraphrase is defensible.

### Attestation log (≥3 phrasings verifying the claim)

1. **Abstract (p.1) — PC (hand-crafted low-level feature) as primary feature, GM as secondary.** "Specifically, the phase congruency (PC), which is a dimensionless measure of the significance of a local structure, is used as the primary feature in FSIM. Considering that PC is contrast invariant while the contrast information does affect HVS' perception of image quality, the image gradient magnitude (GM) is employed as the secondary feature in FSIM. PC and GM play complementary roles in characterizing the image contents." This is the canonical statement that FSIM compares two hand-designed features (PC and GM), directly matching "edges and gradients extracted with hand-crafted filters." Index Terms reinforce: "Image quality assessment, phase congruency, gradient, low-level feature."

2. **Introduction (p.2) — low-level hand-crafted features as the basis.** "The visual information in an image, however, is often very redundant, while the HVS understands an image mainly based on its low-level features, such as edges and zero-crossings [8-10]. ... Accordingly, perceptible image degradations will lead to perceptible changes in image low-level features, and hence a good IQA metric could be devised by comparing the low-level feature sets between the reference image and the distorted image." FSIM is explicitly designed as a comparison of low-level (hand-crafted) feature sets — confirming Adamson's "compares features ... extracted with hand-crafted filters."

3. **Sec. II.A (pp.3–4) — PC is computed with log-Gabor quadrature filters (hand-crafted).** "Rather than define features directly as points with sharp changes in intensity, the PC model postulates that features are perceived at points where the Fourier components are maximal in phase." "With respect to the quadrature pair of filters, i.e. M_n^e and M_n^o, we adopt the log-Gabor filter because its transfer function has an extended tail at the high frequency end, which makes it more capable to encode natural images and it is consistent with measurements on mammalian visual systems." Eq. (2) defines the 2D log-Gabor filter G_2(ω, θ_j) = exp(−(log(ω/ω_0))²/2σ_r²) · exp(−(θ−θ_j)²/2σ_θ²), i.e. an explicit, analytically-specified (hand-crafted) filter bank with fixed center frequencies (1/6, 1/12, 1/24, 1/48) and J orientations. This is the very definition of a hand-crafted filter used to extract an edge/structure feature.

4. **Sec. II.B (p.5) — GM via Sobel operator (hand-crafted convolution mask).** "Image gradient computation is a traditional topic in image processing. Gradient operators can be expressed by convolution masks. Some commonly used gradient operators are Robert operator, Laplace operator, Prewitt operator, Sobel operator, etc. In this paper, we simply use the Sobel operator to compute the gradient of an image." Eq. (4) gives the explicit 3×3 Sobel masks, and G = sqrt(G_x² + G_y²). This is literally a hand-crafted filter extracting gradient information — a verbatim match for Adamson's "gradients extracted with hand-crafted filters."

5. **Sec. III.A (pp.5–6) — FSIM aggregates similarities of the two hand-crafted feature maps.** "With the extracted PC and GM features, in this section we present a novel Feature SIMilarity (FSIM) index for IQA. ... FSIM will be defined and computed based on PC_1, PC_2, G_1 and G_2." Eqs. (5)–(8) define S_PC (PC-map similarity), S_G (GM-map similarity), S_L = S_PC · S_G, and the final FSIM as a PC-weighted average of S_L over the image. This is exactly the "compares features ... extracted with hand-crafted filters" mechanism Adamson describes: two feature maps (PC, GM) are computed by fixed analytic filters (log-Gabor quadrature bank, Sobel masks), then compared pointwise and aggregated.

6. **Sec. III.A (p.6) — "edge locations" and structural significance explicitly named.** "Having obtained the similarity S_L(x) at each location x, the overall similarity between f_1 and f_2 can be obtained. However, different locations will have different contributions to HVS's perception of the image. For example, edge locations convey more crucial visual information than the locations within a smooth area. Since PC is a dimensionless metric to measure the significance of a local structure ... the PC value at a location can reflect how likely it is a perceptibly significant structure point." Explicit support that PC targets edges / structural features — precisely the "edges" portion of Adamson's paraphrase.

### Notes / Limitations

- Strict-reading nit: the FSIM paper frames its primary feature as "phase congruency" (a model of perceptual feature significance at edges, lines, and textured structures) rather than literally "texture." Adamson's word "texture" is a reasonable informal description of what PC responds to (line/edge/texture structure), but if a tighter paraphrase were desired, "edges and structural features" would hew closer to the paper's language. The citation itself is correct and the overall description is SUPPORTED.
- "Hand-crafted filters" is well-supported: both extractors (2D log-Gabor quadrature filter bank for PC; 3×3 Sobel masks for GM) are fixed analytic/convolutional masks, not learned — exactly what "hand-crafted" connotes in the IQA literature.
- linzhang2011 is the correct and defining source for this characterization of FSIM.

### Last verified

2026-04-17

---

### C014 — miao2008

**C014 (ref #13):** "Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17"

Sub-claim for ref 13 (miao2008): example of a perceptual difference model; defines/uses PDM as a psycho-physical model of human visual processing for IQ assessment.

### Classification

**BACKGROUND** — this is a general-literature characterization of the perceptual difference model (PDM) class. Ref 13 (miao2008) is cited as one of five example PDM papers (13–17). The sub-claim to verify is simply that miao2008 is, in fact, a PDM-based paper for MR IQ assessment that models the human visual system — not any specific quantitative figure.

### Source

- Miao J, Huo D, Wilson DL. "Quantitative image quality evaluation of MR images using perceptual difference models." Medical Physics 35(6), 2541–2553 (2008). DOI: 10.1118/1.2903207.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/miao2008.pdf`

### Verdict

**SUPPORTED** — miao2008 is literally titled "Quantitative image quality evaluation of MR images using perceptual difference models," and introduces/uses Case-PDM as a model that "mimics the functional anatomy of the visual pathway and contains components that model the optics and sensitivity of the retina, the spatial contrast sensitivity function, and the channels of spatial frequency found in the visual cortex." The paper explicitly situates Case-PDM within a class of "perceptual metrics which attempt to model human visual processing based on psycho-physical and physiological evidence." This is a textbook match for Adamson's description of PDMs as psycho-physical models that mimic human image-quality perception by modeling the human visual processing system, and citing miao2008 as an exemplar of that class is fully appropriate.

### Attestation log (≥3 phrasings verifying the claim)

1. **Title and abstract (p. 2541).** Title: "Quantitative image quality evaluation of MR images using perceptual difference models." Abstract opens: "The authors are using a perceptual difference model (Case-PDM) to quantitatively evaluate image quality of the thousands of test images which can be created when optimizing fast magnetic resonance (MR) imaging strategies and reconstruction techniques." Key words listed: "perceptual difference model, image quality, detection, magnetic resonance imaging, DSCQS, FMT, AFC." This is a direct, verbatim statement that the paper is (a) a PDM paper and (b) about MR image quality — exactly what the ref-13 sub-claim asserts.

2. **§I Introduction (p. 2542).** "To assess MR image reconstruction algorithms, we have used a perceptual difference model (Case-PDM) which mimics the functional anatomy of the visual pathway and contains components that model the optics and sensitivity of the retina, the spatial contrast sensitivity function, and the channels of spatial frequency found in the visual cortex." This is an explicit, self-described statement that Case-PDM "mimics ... the human visual processing system" — verbatim aligned with Adamson's paraphrase "modeling the human visual processing system." Fig. 1(a) block diagram reinforces this: inputs (Reference Image, Test Image) → Retinal Luminance Calibration → 2D CSF → Cortex Filters → Detection and Contrast Mechanisms → Difference Visualization → PDM Score. Every block is a psycho-physical / physiological HVS component.

3. **§I Introduction (p. 2543).** "Similar perceptual difference methods have been often applied to evaluate image compression. Among them, there are models which incorporate the CSF and luminance adaptations (e.g., Ref. 36), models which incorporate the observer preferences for suprathreshold artifacts (e.g., Ref. 37), and perceptual metrics which attempt to model human visual processing based on psycho-physical and physiological evidence (e.g., Refs. 38 and 39)." This passage (i) names "perceptual difference methods" as a class, and (ii) explicitly identifies the sub-class Adamson describes — "model human visual processing based on psycho-physical ... evidence" — using almost the same wording Adamson uses ("psycho-physical models ... modeling the human visual processing system"). Case-PDM is positioned in this class throughout the paper.

4. **§II Methods (p. 2543).** "To detect the just perceptible difference, the 2-AFC experiment was used." "Psychophysical measures such as forced-choice task have commonly been used in determining signal threshold especially in medical images." The paper grounds Case-PDM in psychophysical validation (DSCQS, FMT, and 2-AFC human-observer experiments) — further confirming its identity as a psycho-physical perceptual model, not a purely mathematical / signal-statistics metric.

5. **§IV Discussion (pp. 2550–2551) and §V Conclusions (p. 2551).** "Case-PDM compared very favorably to human observers ..."; "Case-PDM scored the best of the seven models by providing high model-subject correlations and consistent prediction of detection thresholds for just perceptible differences across a variety of images and processing." This reinforces the paper's claim that Case-PDM is specifically a human-visual-system-style model whose raison d'être is predicting human image-quality perception — i.e., precisely the kind of "perceptual difference model" Adamson's sentence describes.

6. **Comparator table (Table VI, p. 2548) — PDM class vs. non-PDM.** The paper benchmarks Case-PDM against six other IQ metrics (IDM, SSIM, NR, MSE, DCTune, IQM) and groups Case-PDM with IDM and SSIM as "three 'perceptual difference' models" that "outperform other models (MSE, NR, DCTune, IQM)." This is the paper's own reified use of the term "perceptual difference model" as a class label — supporting Adamson's framing that PDMs form a recognizable IQ-metric class.

### Notes / Limitations

- The Adamson sentence cites five refs (13–17) for the PDM-class characterization; only miao2008 (ref 13) is evaluated here. The description fits miao2008 cleanly.
- Strictly, Case-PDM as presented in miao2008 is an MR-specific validation / calibration of a PDM originally developed by Salem et al. (Case-PDM v1, ref 24 / v2, Huo Ph.D. thesis, ref 54) — but the paper itself both uses and contributes to the PDM framework, and is an appropriate exemplar citation for the PDM class in an MR IQ context.
- Adamson's paraphrase "mimic how humans perceive image quality by modeling the human visual processing system" is a faithful generalization of miao2008's own wording ("mimics the functional anatomy of the visual pathway ... retina ... CSF ... visual cortex ... based on psycho-physical and physiological evidence").

### Last verified

2026-04-17

---

### C015 — mantiuk2011

**Section:** 
**Citekey:** `mantiuk2011` (ref #14)
**Claim text:** Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17 Visual Information Fidelity (VIF18 ) uses natural image scene statistics to compute the mutual information between image pairs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mantiuk2011.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C016 — miao2013

**Section:** 
**Citekey:** `miao2013` (ref #15)
**Claim text:** Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17 Visual Information Fidelity (VIF18 ) uses natural image scene statistics to compute the mutual information between image pairs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/miao2013.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C017 — salem2002

**Section:** 
**Citekey:** `salem2002` (ref #16)
**Claim text:** Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17 Visual Information Fidelity (VIF18 ) uses natural image scene statistics to compute the mutual information between image pairs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/salem2002.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C018 — daly1992

**Section:** 
**Citekey:** `daly1992` (ref #17)
**Claim text:** Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17 Visual Information Fidelity (VIF18 ) uses natural image scene statistics to compute the mutual information between image pairs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/daly1992.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C019 — sheikh2006

**Section:** 
**Citekey:** `sheikh2006` (ref #18)
**Claim text:** Perceptual difference models are a class of psycho-physical models that aim to mimic how humans perceive image quality by modeling the human visual processing system.13–17 Visual Information Fidelity (VIF18 ) uses natural image scene statistics to compute the mutual information between image pairs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sheikh2006.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C020 — dameravenkata2000

**Section:** 
**Citekey:** `dameravenkata2000` (ref #19)
**Claim text:** The Noise Quality Metric (NQM19 ) computes the SNR of a model-restored image via a restoration algorithm that accounts for the impact of spatial frequencies, distance, and contrast masking on contrast sensitivities.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/dameravenkata2000.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C021 — ravishankar2011

**Section:** 
**Citekey:** `ravishankar2011` (ref #20)
**Claim text:** HFEN aims to capture finer-grained features in MR image reconstructions using a Laplacian of Gaussian filter, although it is limited to assessing only high-frequency content.20 Several other common IQ metrics fall outside the scope of the perceptual IQ metrics studied in this work.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/ravishankar2011.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C022 — kim2018

**Section:** 
**Citekey:** `kim2018` (ref #21)
**Claim text:** The Fourier radial error spectrum expands upon HFEN by plotting errors in MR image reconstructions as a function of spatial frequencies, sacrificing the simplicity of a scalar IQ metric for a more nuanced view of reconstruction errors.21 Other metrics focus on evaluating traditional MR parameters such as noise, spatial resolution, and point-spread functions,22,23 although relating these parameters to clinical diagnostic utility is less direct.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/kim2018.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C023 — chan2021

**Section:** 
**Citekey:** `chan2021` (ref #22)
**Claim text:** The Fourier radial error spectrum expands upon HFEN by plotting errors in MR image reconstructions as a function of spatial frequencies, sacrificing the simplicity of a scalar IQ metric for a more nuanced view of reconstruction errors.21 Other metrics focus on evaluating traditional MR parameters such as noise, spatial resolution, and point-spread functions,22,23 although relating these parameters to clinical diagnostic utility is less direct.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/chan2021.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C024 — kleineisel2025

**Section:** 
**Citekey:** `kleineisel2025` (ref #23)
**Claim text:** The Fourier radial error spectrum expands upon HFEN by plotting errors in MR image reconstructions as a function of spatial frequencies, sacrificing the simplicity of a scalar IQ metric for a more nuanced view of reconstruction errors.21 Other metrics focus on evaluating traditional MR parameters such as noise, spatial resolution, and point-spread functions,22,23 although relating these parameters to clinical diagnostic utility is less direct.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/kleineisel2025.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C025 — desai2022

**Section:** Introduction (framing of task-specific IQ assessment)
**Citekey:** `desai2022` (ref #24)
**Claim text:** Many works assess MR reconstructions based on task-specific metrics for segmentation, classification, and detection,24–26 which brings the IQ assessment closer to the true clinical utility.
**Claim type:** PARAPHRASED (high) — SKM-TEA dataset paper attested as an example of task-specific (segmentation + detection + qMRI-biomarker) evaluation of MR reconstructions, where dense tissue segmentations and pathology bounding boxes are tied directly to reconstruction quality assessment.
**Sub-claim attributed:** "SKM-TEA provides dense annotations enabling task-specific (segmentation / classification / detection) evaluation of MR reconstructions." The desai2022 paper explicitly supports segmentation and detection task-specific evaluation coupled to reconstruction; "classification" is not an explicit SKM-TEA benchmarking task (the paper notes fastMRI+/MRNet/OAI as classification-capable, but SKM-TEA itself focuses on reconstruction + segmentation + detection + qMRI). The paraphrase-as-group ("segmentation, classification, and detection") is therefore partially — not fully — supported by this one reference; the group citation (refs 24–26) likely distributes coverage across multiple works.
**Source excerpt:**
- Abstract (p. 1): "we present the Stanford Knee MRI with Multi-Task Evaluation (SKM-TEA) dataset ... consists of raw-data measurements of ~25,000 slices (155 patients) ... the corresponding scanner-generated DICOM images, manual segmentations of four tissues, and bounding box annotations for sixteen clinically relevant pathologies. We provide a framework for using qMRI parameter maps, along with image reconstructions and dense image labels, for measuring the quality of qMRI biomarker estimates extracted from MRI reconstruction, segmentation, and detection techniques."
- §3 Related Work / Table 1 (p. 3): Table 1 lists SKM-TEA with check marks across Reconstruction, Classification, Segmentation, and Detection tasks.
- §5.1 Raw Data Benchmark Track (p. 6): "Segmentation and Detection: Tissue segmentation masks and localized pathology labels and bounding boxes can enable segmentation and detection tasks as well as localized image quality for evaluating reconstruction tasks in clinically pertinent regions."
- §6 Evaluation and Benchmarks (p. 6): "we introduce a standardized evaluation pipeline for using quantitative parameter map estimates and dense annotations to quantify clinically-relevant indicators as a new metric for performance of reconstruction and segmentation models."
- §6.4 Results and Analysis / Metric Concordance (p. 9): "using clinically-relevant T2 biomarkers as direct endpoints for quantifying performance can help mitigate the challenge of low concordance between standard ML metrics and accuracy of T2 estimates." (task-driven endpoint for reconstruction quality)
- §8 Conclusion (p. 10): "we propose an open-source evaluation framework that uses regional qMRI biomarker analysis as a direct endpoint for quantifying model performance."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       22 pages (arXiv:2203.06823, NeurIPS 2021 D&B Track), incl. main body + Appendices A–E.
  Section checklist:  Abstract ✓, Introduction (§1) ✓, Background (§2) ✓, Related Work (§3 incl. Table 1) ✓,
                      Dataset (§4 — Data Collection, Data Preparation) ✓, Dataset Tracks (§5 — Raw Data Track,
                      DICOM Track) ✓, Evaluation and Benchmarks (§6 incl. T2-qMRI, Baselines, Metrics, Results,
                      Metric Concordance) ✓, Limitations (§7) ✓, Conclusion (§8) ✓, References ✓,
                      Appendix A (Dataset details, Annotator, Distribution, Usage) ✓, Appendix B (Tissue
                      Subregions) ✓, Appendix C (qMRI T2 Pipeline) ✓, Appendix D (Training Details) ✓,
                      Appendix E (Additional Results incl. ML-T2 Metric Concordance) ✓, Tables 1–10 ✓,
                      Figures 1–4 captions ✓.
  Phrasings searched: "task-specific" (not a verbatim hit, but semantic equivalents throughout);
                      "segmentation" / "detection" / "classification" (literal task names);
                      "dense annotations" / "dense image labels" / "dense tissue and pathology labels" (verbatim);
                      "clinically-relevant evaluation" / "clinically relevant" / "clinical utility" (framing paraphrases);
                      "multi-task" / "multi-task evaluation" (the dataset name itself);
                      "bounding box" / "pathology labels" / "tissue segmentations" (annotation types);
                      "reconstruction" ↔ "segmentation" / "reconstruction" ↔ "detection" (coupling phrases);
                      "downstream" task / endpoint / evaluation (direction of task-driven IQ).
  Specific checks:    §1 lists three contributions explicitly tying dense labels to reconstruction evaluation
                      — (1) End-to-end MRI, (2) Clinically-relevant evaluation, (3) Benchmarking. Table 1
                      row for SKM-TEA shows check marks for Reconstruction ✓, Classification ✓, Segmentation ✓,
                      Detection ✓, which is the clearest single-cell summary of task-specific support. §5.1
                      Raw Data Track "Multi-Task MRI" paragraph explicitly describes multi-task learning setups
                      combining reconstruction + segmentation + detection + qMRI generation.
  Closest adjacent passage: "We provide a framework for using qMRI parameter maps, along with image
                      reconstructions and dense image labels, for measuring the quality of qMRI biomarker
                      estimates extracted from MRI reconstruction, segmentation, and detection techniques."
                      (Abstract) — this is near-verbatim support for the sub-claim.
  Indirect-attribution check: SKM-TEA is the primary source of its own dense-annotation + multi-task
                      evaluation framework; it does not attribute this to an earlier paper. Primary-source
                      citation is appropriate.
  Out-of-context check: Adamson et al. cite desai2022 in a 3-way group (refs 24–26) as an example of
                      task-specific MR reconstruction evaluation. SKM-TEA clearly qualifies: it explicitly
                      supports segmentation and detection task-specific evaluation of reconstructions, and
                      also exposes classification-compatible labels per Table 1. The umbrella claim
                      ("segmentation, classification, and detection") is best read as a distributed claim
                      across refs 24–26; ref 24 (desai2022) covers the segmentation and detection legs and
                      partially the classification leg (via Table 1 taxonomy). Usage is consistent with
                      source scope; no overreach detected at the per-ref level.

---

### C026 — zhao2021

**Context (C026, ref #25):** "Many works assess MR reconstructions based on task-specific metrics for segmentation, classification, and detection,24–26 which brings the IQ assessment closer to the true clinical utility."

**Sub-claim for ref 25 (zhao2021):** example of task-specific (lesion detection) evaluation of DL-based MR reconstructions.

### Source

- Zhao, Zhang, Yaman, Lungren, Hansen. "End-to-end AI-based MRI Reconstruction and Lesion Detection Pipeline for Evaluation of Deep Learning Image Reconstruction." arXiv:2109.11524v1, 23 Sep 2021.
- PDF read: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/zhao2021.pdf` (all 5 pages).

### Classification

**SUPPORTING** — the paper is a direct example of task-specific (specifically lesion detection) evaluation of DL-based MR reconstructions, which is exactly what Adamson et al. cite it for.

### Verification / Attestation log (>=3 phrasings in source)

Zhao et al. 2021 explicitly propose and demonstrate an evaluation of DL MR reconstruction via a downstream lesion-detection task. Multiple passages attest:

1. **Title/Abstract:** "END-TO-END AI-BASED MRI RECONSTRUCTION AND LESION DETECTION PIPELINE FOR EVALUATION OF DEEP LEARNING IMAGE RECONSTRUCTION." Abstract: "we propose an end-to-end deep learning framework for image reconstruction and pathology detection, which enables a clinically aware evaluation of deep learning reconstruction quality. The solution is demonstrated for a use case in detecting meniscal tears on knee MRI studies..." (p.1)

2. **Introduction framing (motivates task-based eval over global metrics):** "A chief challenge remains in that ability to reconstruct clinically important pathology is not considered and the fastMRI challenges show that deep learning techniques often fail to reconstruct fine details such as meniscus tear despite having good global quantitative metrics [12]. Hence, there is a need for clinically-aware deep learning techniques and workflows, which not only reconstruct images, but also detect lesions such as meniscus tears." (p.1)

3. **Methods (Section 2.4 Imaging Experiments and Evaluation):** "To evaluate the lesion detection capabilities of different reconstruction methods with the proposed pipeline, the pretrained meniscus tear detection network was used in the lesion detection Gadget, and four different reconstruction methods (i.e., Zero-filling FFT, CG-SENSE, UNet, Model-based VarNet) were used in the image reconstruction Gadget..." (p.3)

4. **Metrics computed are task-based detection metrics:** "With the predicted bounding box information, the total number of detected meniscus tears, as well as the number of true positives (TP), false negatives (FN), and false positives (FP) relative to the ground-truth clinical labels and detection sensitivity were calculated." (p.3) Table 1 (p.3) reports #Detected / #TP / #FP / #FN / Sensitivity per reconstruction method (Zero-filling FFT, CG-SENSE, UNet, VarNet) at acceleration rates 4 and 8.

5. **Discussion/conclusion reaffirms task-based evaluation purpose:** "The proposed framework enables rapid testing and comparison of image reconstruction algorithms not only in terms of global quality metrics but also in terms of their ability to preserve clinically important details." ... "it creates an automatic benchmark that allow us to compare two or more reconstruction algorithms in terms of their effect on a detection task." (p.4)

6. **Explicit contrast between SSIM (global) and detection-based evaluation:** "We also calculated and compared the difference of SSIM metric between FP slices and FN slices for each reconstruction method, in order to assess the ability of SSIM to reflect lesion detection capability." ... "We observe that the high SSIM values which are used as a performance criteria in the literature do not differ for slices with TP&FN." (p.3–4) — supports Adamson et al.'s broader point that task-specific metrics bring IQ assessment closer to clinical utility.

### Verdict

The sub-claim for ref 25 is accurately characterized. Zhao et al. 2021 is a textbook example of a task-specific (lesion detection) evaluation of DL-based MR reconstructions: they train a YOLO meniscus-tear detector on fully-sampled fastMRI+ images and evaluate four reconstruction methods (Zero-filling FFT, CG-SENSE, UNet, VarNet) at R=4 and R=8 via detection-based metrics (TP/FP/FN/sensitivity), explicitly motivated by the insufficiency of global metrics like SSIM/NMSE.

**Validation:** SUPPORTING (valid).

---

### C027 — zhao2022

"Many works assess MR reconstructions based on task-specific metrics for segmentation, classification, and detection,24–26 which brings the IQ assessment closer to the true clinical utility."

### Sub-claim attributed to ref 26 (zhao2022)
fastMRI+ provides clinical pathology annotations enabling task-specific evaluation (classification/detection) of MR reconstructions.

### Classification
BACKGROUND — citing zhao2022 as motivating/enabling evidence that task-specific evaluation (classification/detection) on MR reconstructions is feasible because fastMRI+ supplies clinical pathology annotations (bounding boxes + study-level labels) atop the fastMRI raw data.

### Source paper
Zhao, R. et al. "fastMRI+, Clinical pathology annotations for knee and brain fully sampled magnetic resonance imaging data." *Scientific Data* 9:152 (2022). DOI 10.1038/s41597-022-01255-z.

### Attestation log (≥3 phrasings from zhao2022)

1. Abstract (p.1): "This work introduces fastMRI+, which consists of 16154 subspecialist expert bounding box annotations and 13 study-level labels for 22 different pathology categories on the fastMRI knee dataset, and 7570 subspecialist expert bounding box annotations and 643 study-level labels for 30 different pathology categories for the fastMRI brain dataset."

2. Background & Summary (p.1–3): "the dataset currently lacks clinical expert pathology annotations, critical to addressing clinically relevant reconstruction frameworks and exploring important questions regarding rendering of specific pathology using such novel approaches." And: "there is a lack of clinical pathology information to accompany the imaging data which has limited the reconstruction assessment approaches to validate quantitative metrics such as peak signal-to-noise ratio (pSNR)/structural similarity index measure (SSIM), leaving important questions regarding how various pathologies are represented in ML-based reconstruction unanswered."

3. Background & Summary (p.3): "In this paper, we present wide availability of a complementary dataset of annotations, fastMRI+, consisting of human subspecialist expert clinical bounding box labelled pathology annotations for knee and brain MRI scans from the fastMRI multi-coil dataset… This new dataset is open and accessible to all for educational and research purposes with the intent to catalyse new avenues of clinically relevant, ML-based reconstruction approaches and evaluation."

4. Usage Notes (p.5): "The clinical labels, together with the bounding box coordinates, can also be converted to other formats (e.g., YOLO format) in order to configure a classification or object detection problem."

5. Methods — Annotations (p.3): "A subspecialist board certified musculoskeletal radiologist with 6 years in practice experience performed annotation for the knee dataset and a subspecialist board certified neuroradiologist with 2 years in practice experience performed annotation for the brain dataset. Annotation was performed with bounding box annotation to include the relevant box label for a given pathology on a slice-by-slice level." Tables 1–3 enumerate pathology categories and annotation counts.

### Verification outcome
Strongly supported. Zhao et al. 2022 explicitly:
- Adds clinical expert pathology annotations (bounding boxes + study-level labels) to the fastMRI knee and brain datasets.
- Motivates these annotations as enabling clinically relevant reconstruction assessment beyond pSNR/SSIM.
- States the labels can be converted (e.g., to YOLO format) to configure classification or object detection problems — i.e., the exact task-specific evaluation modes Adamson 2025 references (classification/detection).

The Adamson 2025 sub-claim that fastMRI+ provides clinical pathology annotations enabling task-specific (classification/detection) evaluation of MR reconstructions is directly and fully supported by the source.

### Verdict
v = SUPPORTED

---

### C028 — zhang2018

> Recently, Zhang et al. showed that the Learned Perceptual Image Patch Similarity (LPIPS), a type of Deep Feature Distance (DFD) whereby distances between image pairs are computed in a lower-dimensional feature space encoded by a CNN, correlates strongly with human perceived IQ.

### Classification
- **Type:** DIRECT
- **Confidence:** high
- **Verdict:** SUPPORTED

### Source
- Zhang, Isola, Efros, Shechtman, Wang. "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric." CVPR 2018 (arXiv:1801.03924v2, 10 Apr 2018).
- PDF: `pdfs/zhang2018.pdf`

### Sub-claims to verify
1. Paper introduces LPIPS.
2. LPIPS uses CNN-encoded feature-space distances between image pairs.
3. LPIPS correlates strongly with human perceptual judgments.

---

### Attestation log (≥3 phrasings per sub-claim)

#### (a) Paper introduces LPIPS
- p. 6 (Sec. 4 Experiments, intro): "Overall, we refer to these as variants of our proposed **Learned Perceptual Image Patch Similarity (LPIPS)** metric." — explicit naming and introduction of the metric.
- p. 6 caption of Figure 4 legend: the bar-chart categories "LPIPS (linear)", "LPIPS (scratch)", "LPIPS (tune)" are presented as the authors' own metrics (distinct from pre-existing Low-level, Net (Random/Unsupervised/Self-supervised/Supervised) baselines).
- p. 7 Fig. 5 caption: "…our perceptually-learned metrics (LPIPS)." — again framed as the paper's own proposed metric.
- Table 5 (Appendix A, p. 12): a full section of rows labeled "*LPIPS (Learned Perceptual Image Patch Similarity)" enumerating Squeeze/Alex/VGG in lin/scratch/tune variants, confirming LPIPS is the paper's trained metric family.
- Abstract + Sec. 1–2 establish the BAPPS dataset and the goal to train/calibrate a deep perceptual metric; LPIPS is the named realization of that metric introduced in Sec. 4.

#### (b) LPIPS = distance in CNN feature space between image pairs
- p. 6, Fig. 3 caption: "To compute a distance d_0 between two patches, x, x_0, given a network F, we first compute deep embeddings, normalize the activations in the channel dimension, scale each channel by vector w, and take the ℓ_2 distance. We then average across spatial dimension and across all layers." — explicit feature-space distance between image pairs.
- p. 6, Sec. "Network activations to distance": "We extract feature stack from L layers and unit-normalize in the channel dimension… We scale the activations channel-wise by vector w^l ∈ R^{C_l} and compute the ℓ_2 distance. Finally, we average spatially and sum channel-wise." Equation (1) gives d(x,x_0) = Σ_l (1/H_lW_l) Σ_{h,w} || w^l ⊙ (ŷ^l_{hw} − ŷ^l_{0hw}) ||_2^2.
- p. 5, Sec. 3 "Deep Feature Spaces": "We evaluate feature distances in different networks. For a given convolutional layer, we compute cosine distance (in the channel dimension) and average across spatial dimensions and layers." — CNN (SqueezeNet/AlexNet/VGG) feature-space distances.
- p. 5, Network architectures: "We evaluate the SqueezeNet [20], AlexNet [28], and VGG [52] architectures." — the feature spaces used are convolutional neural networks.
- Claim phrasing "lower-dimensional feature space encoded by a CNN" is consistent with averaging channel-normalized activations from conv layers and taking ℓ_2 in that embedded space.

#### (c) Strong correlation with human perceptual judgments
- Abstract: "…deep features outperform all previous metrics by large margins on our dataset. More surprisingly, this result is not restricted to ImageNet-trained VGG features, but holds across different deep architectures and levels of supervision… perceptual similarity is an emergent property shared across deep visual representations."
- p. 2, Contributions: "We show that deep features, trained on supervised, self-supervised, and unsupervised objectives alike, model low-level perceptual judgment surprisingly well, outperforming previous, widely-used metrics."
- p. 7, Sec. 4.1 Evaluations: "Averaged across all 6 test sets, humans are 73.9% consistent… the supervised networks perform at about the same level to each other, at 68.6%, 68.9%, and 67.0%… They all perform better than traditional metrics ℓ_2, SSIM, and FSIM at 63.2%, 63.1%, 63.8%, respectively."
- p. 7, Table 4 (Task correlation): "Perceptual 2AFC vs JND: .928" — high correlation of the paper's 2AFC perceptual test with the JND perceptual test (internal validation that the metric tracks human judgments).
- p. 7: "The 2AFC distortion preference test has high correlation to JND: ρ = .928 when averaging the results across distortion types."
- Table 5 (Appendix A, p. 12): LPIPS variants achieve the highest overall 2AFC scores — e.g., VGG–tune 81.4% "All", Alex–lin 78.7% "Distortions/All", versus Human 82.6% — i.e., LPIPS approaches human-level agreement and exceeds all low-level metrics (L2 68.9, SSIM 69.7, FSIMc 70.0, HDR-VDP 67.1 in the "Distortions/All" column).
- p. 14, Fig. 12 (TID2013): Deep classification networks (AlexNet ≈ 0.80, SqueezeNet/VGG/ResNet50) achieve Spearman correlation coefficients comparable to or exceeding FSIMc on TID2013 — out-of-the-box deep features correlate strongly with human MOS on a standard IQA dataset.
- p. 8, Conclusions: "Our results indicate that networks trained to solve challenging visual prediction and modeling tasks end up learning a representation of the world that correlates well with perceptual judgments."

---

### Quantitative anchors (from Zhang et al.)
- Human 2AFC consistency ceiling (All sets): 73.9%; Distortions/All: 82.6%.
- Best LPIPS (VGG–tune): 81.4% 2AFC All; vs SSIM 69.7%, L2 68.9%, FSIMc 70.0% on Distortions/All.
- Internal perceptual-task correlation (2AFC ↔ JND): ρ = 0.928.
- TID2013 (Fig. 12): deep-net Spearman ρ ≈ 0.70–0.80, comparable to top IQA metric FSIMc (~0.85) and well above PSNR/SSIM (~0.6).

### Notes / caveats
- Zhang et al. do not use the exact phrase "Deep Feature Distance (DFD)"; the "DFD" umbrella and the acronym are Adamson et al.'s framing. The source supports LPIPS as a CNN feature-space distance that correlates with human perceptual judgments, which is what Adamson et al. claim.
- Zhang et al. explicitly say patches, not full images; Adamson's "image pairs" is a reasonable generalization since patches are image data and LPIPS is commonly applied to full images. This is not a misrepresentation.
- "Strongly correlates with human perceived IQ" is supported both on the authors' BAPPS 2AFC/JND tests and on the TID2013 IQA dataset (Appendix C).

### Verdict
All three sub-claims are directly and explicitly supported by Zhang et al. 2018. Classification DIRECT, confidence high.

---

### C029 — ding2020

**C029 (ref #28):** "We used two DFDs based on natural images, LPIPS and the Deep Image Structure and Texture Similarity index (DISTS),[28] which have been used as benchmark IQ metrics in large-scale computer vision IQ metric studies."

Sub-claim for ref 28 (ding2020): DISTS is defined (name, what it is); it has been used as a benchmark in CV IQ metric studies.

### Classification

**BACKGROUND / SUPPORTING** — ding2020 is cited as the primary reference defining DISTS (name, full form, and as a natural-image full-reference IQA metric). The "benchmark in large-scale CV IQ metric studies" aspect is implicitly supported via the paper's own large-scale natural-image IQA benchmarks and downstream citation usage; the specific benchmark-study claim is further corroborated by separate references (see C030, which cites cong2022 for the large-scale natural-image study angle).

### Source

- Ding K, Ma K, Wang S, Simoncelli EP. "Image Quality Assessment: Unifying Structure and Texture Similarity." IEEE Transactions on Pattern Analysis and Machine Intelligence, 2020. DOI 10.1109/TPAMI.2020.3045810 (arXiv:2004.07728v3, 16 Dec 2020).
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/ding2020.pdf`

### Verdict

**SUPPORTED** — ding2020 establishes DISTS by its full name ("Deep Image Structure and Texture Similarity"), describes it as a full-reference natural-image IQA model, and benchmarks it extensively against other IQA metrics on standard large-scale natural-image IQA databases (LIVE, CSIQ, TID2013, KADID-10k, BAPPS). DISTS has subsequently been widely used as a benchmark comparator in CV IQA studies (e.g., cong2022/GSN reports DISTS performance on PIPAL/NTIRE 2022 FR challenge, the large-scale IQA benchmark — consistent with C030). The Adamson claim correctly names DISTS and correctly characterizes it as a natural-image-based DFD used as a benchmark IQ metric.

### Attestation log (≥3 phrasings verifying the claim)

1. **Name and full form (title + abstract, p.1).** Title: "Image Quality Assessment: Unifying Structure and Texture Similarity." Abstract: "...the resulting Deep Image Structure and Texture Similarity (DISTS) index..." This establishes both the name and the abbreviation used in Adamson.

2. **Natural-image IQA method (Abstract, Sec. 2, p.1–2).** "Here, we develop the first full-reference image quality model with explicit tolerance to texture resampling... our method is constructed by first nonlinearly transforming images to a multi-scale overcomplete representation, using a variant of the VGG convolutional neural network (CNN)." Confirms DISTS is a full-reference IQA model based on natural-image features (VGG pre-trained on ImageNet). Adamson's "based on natural images" correctly reflects this.

3. **Large-scale natural-image IQA benchmarks (Sec. 3.2, Tab. 1, p.7).** "After training on the entire KADID dataset, DISTS was tested on the other three standard IQA databases LIVE, CSIQ and TID2013." DISTS is directly compared with PSNR, SSIM, MS-SSIM, VSI, MAD, VIF, FSIMc, NLPD, GMSD, DeepIQA, PieAPP, and LPIPS on PLCC/SRCC/KRCC — a canonical benchmark comparison in computer-vision IQA.

4. **BAPPS large-scale patch-similarity benchmark (Sec. 3.2, Tab. 2, p.8–9).** "We also tested DISTS on BAPPS [7], a large-scale and highly-varied patch similarity dataset... DISTS (which was not trained on BAPPS, or any similar database) achieves a comparable performance to LPIPS (which was trained on BAPPS)." Direct evidence DISTS is used as a benchmark IQ metric on a large-scale CV IQ dataset alongside LPIPS — matching Adamson's pairing of LPIPS and DISTS as "benchmark IQ metrics in large-scale computer vision IQ metric studies."

5. **Public release for benchmark use (Abstract, p.1).** "Code is available at https://github.com/dingkeyan93/DISTS." Public availability supports its subsequent widespread use as a benchmark (cross-supported by C030/cong2022 which uses DISTS as a comparator on PIPAL/NTIRE 2022 FR — an explicitly large-scale CV IQA study).

### Notes / Limitations

- The Adamson claim's phrase "benchmark IQ metrics in large-scale computer vision IQ metric studies" is supported both intrinsically (ding2020's own LIVE/CSIQ/TID2013/KADID-10k/BAPPS evaluations are large-scale CV IQA studies) and extrinsically (follow-on literature, e.g., cong2022, uses DISTS as a benchmark). Adamson bundles this under ref 28 together with citation 34 for the explicit "large-scale studies" aspect; ref 28 alone is sufficient to ground the name + natural-image + benchmark-use characterization.
- No discrepancy with the Adamson paraphrase; "based on natural images" matches ding2020's use of VGG-ImageNet features and natural-image IQA training/test data.

---

### C030 — cong2022

**C030 (ref #29):** "Although LPIPS and other DFDs[28–33] outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,[34] these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

Sub-claim for ref 29 (cong2022): example of a DFD-family / learned IQ metric outperforming conventional IQ metrics on natural-image benchmarks.

### Classification

**BACKGROUND / SUPPORTING** — cong2022 is cited as one of several (refs 28–33) learned IQA methods cited to support the broader claim that learned / deep perceptual metrics outperform conventional metrics in natural-image studies.

### Source

- Cong H, Fu L, Zhang R, Zhang Y, Wang H, He J, Gao J. "Image Quality Assessment with Gradient Siamese Network." CVPRW 2022 (NTIRE 2022). arXiv:2208.04081.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/cong2022.pdf`

### Verdict

**SUPPORTED** — cong2022 demonstrates a learned IQA method (GSN, gradient Siamese network) that outperforms conventional full-reference IQA metrics (PSNR, SSIM, MS-SSIM) and is competitive with / superior to deep-feature distance metrics (LPIPS, DISTS, PieAPP) on standard natural-image IQA benchmarks (LIVE, CSIQ, TID2013, PIPAL/NTIRE 2022). All benchmarks used are natural-image datasets, consistent with the Adamson claim about "natural images belonging to the same domain as the images used for encoder training."

Minor caveat: cong2022's GSN is technically a learned end-to-end IQA network using Central Difference Convolution rather than a "pure" DFD (deep feature distance like LPIPS). However, it is used as one example in a group citation (refs 28–33) supporting the broader assertion that learned perceptual / deep-feature IQA methods outperform classical metrics on natural-image benchmarks, which cong2022 clearly supports via its comparison tables.

### Attestation log (≥3 phrasings verifying the claim)

1. **Natural-image datasets used throughout (Sec 4.1, Tab. 2).** Cong2022 evaluates on LIVE, CSIQ, TID2013, KADID-10k, and NTIRE 2022 FR (PIPAL) — all natural-image IQA datasets. Direct quote: "Comparison experiments are established based on three public databases, including the LIVE Image Quality Assessment Database (LIVE), the Categorical Subjective Image Quality (CSIQ) database, and the Tampere image database 2013 (TID2013)." Consistent with claim's "natural images belonging to the same domain as the images used for encoder training."

2. **Explicit comparison showing learned methods outperform conventional metrics (Sec 4.3, Tab. 3).** "Experiments shown in Tab. 3 demonstrate that our method has favorable performance compared to both classical methods (e.g., PSNR and SSIM) and recent deep-learning-based models (e.g., PieAPP, LPIPS, and DISTS)." On PIPAL/NTIRE 2022 FR testing set (Tab. 4), GSN (MS=1.642) substantially outperforms PSNR (MS=0.526), SSIM (MS=0.752), MS-SSIM (MS=0.532), while LPIPS-VGG (MS=1.227) and DISTS (MS=1.342) also outperform the conventional metrics — all consistent with the "DFDs outperform commonly used IQ metrics" framing.

3. **Correlation-with-human-perception evaluation (Sec 4.3, Sec 4.5).** Evaluation uses PLCC, SRCC, KRCC against MOS (human-rated ground truth): "Using Pearson linear correlation coefficient (PLCC), the Spearman rank correlation coefficient (SRCC), and the Kendall rank correlation coefficient (KRCC) as evaluation criteria..." This directly matches Adamson's "correlation with human perceptual judgments." On PIPAL (based on "over 1 million human rankings" with MOS via ELO), learned methods (GSN, LPIPS, DISTS) achieve substantially higher correlation than PSNR / SSIM.

4. **Large-scale natural-image benchmark (Sec 4.5).** "The PIPAL dataset generated 23K distortion images by 40 distortion types and MOS labels by ELO rating system based on over 1 million human rankings." This is the type of "large-scale computer vision study" the Adamson claim refers to, and LPIPS + other deep learned methods are shown to outperform conventional IQ metrics in it.

5. **Same-domain natural images (Sec 4.1, Tab. 2).** All reference images across LIVE, CSIQ, TID2013, KADID-10k, PIPAL are natural photographic images at typical sRGB resolutions (288×288 to 512×768). This matches the domain on which the underlying deep encoders (e.g., VGG/AlexNet used by LPIPS) were trained (ImageNet), directly supporting Adamson's qualifier that "these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

### Notes / Limitations

- Cong2022's GSN itself is not a fixed pre-trained encoder DFD (like LPIPS); it is a trained-from-scratch Siamese IQA network using Central Difference Convolution. In the Adamson group citation (28–33), it serves as an instance of learned / deep-feature IQA outperforming conventional metrics rather than a strict LPIPS-style DFD.
- The paper does not contain the phrase "domain gap" or discuss out-of-domain (e.g., medical / MRI) evaluation; the citation is appropriate only for the natural-image portion of the Adamson claim.

---

### C031 — cheon2021

**C031 (ref #30):** "Although LPIPS and other DFDs[28–33] outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,[34] these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

Sub-claim for ref 30 (cheon2021): example of a DFD-family / learned-deep-feature IQ metric outperforming conventional IQ metrics on natural-image perceptual-quality benchmarks.

### Classification

**BACKGROUND / SUPPORTING** — cheon2021 is cited as one of several (refs 28–33) learned / deep-feature IQA methods grouped to support the broader background assertion that learned perceptual metrics outperform conventional IQ metrics on natural-image benchmarks.

### Source

- Cheon M, Yoon S-J, Kang B, Lee J. "Perceptual Image Quality Assessment with Transformers." CVPR Workshops 2021 (NTIRE 2021 Perceptual IQA Challenge). arXiv:2104.14730v2.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/cheon2021.pdf`

### Verdict

**SUPPORTED** — cheon2021 proposes IQT (Image Quality Transformer), a full-reference IQA method that uses a frozen ImageNet-pretrained Inception-ResNet-V2 CNN backbone to extract deep perceptual features from reference and distorted images and a transformer encoder–decoder to predict perceptual quality. The method outperforms conventional IQ metrics (PSNR, SSIM, MS-SSIM, VIF, FSIM, etc.) and is competitive with / superior to deep-feature distance metrics (LPIPS, DISTS, PieAPP, WaDIQaM) on standard natural-image IQA benchmarks (LIVE, CSIQ, TID2013, PIPAL). IQT-C won the NTIRE 2021 perceptual IQA challenge on PIPAL. All benchmarks used are natural-image datasets whose reference images are in-domain with ImageNet (the encoder pretraining domain), consistent with the Adamson claim's qualifier "natural images belonging to the same domain as the images used for encoder training."

Minor caveat: IQT is a learned transformer-based IQA model built on top of frozen deep features (Inception-ResNet-V2 features pretrained on ImageNet), not a "pure" fixed deep feature distance like LPIPS. However, within the Adamson group citation (28–33), it serves appropriately as an instance of learned / deep-feature-based IQA that outperforms classical metrics on natural-image benchmarks, which cheon2021 clearly supports.

### Attestation log (≥3 phrasings verifying the claim)

1. **Deep-feature-based FR-IQA method using ImageNet-pretrained encoder (Sec 3, Feature Extraction Backbone, p. 3–4).** IQT uses a frozen ImageNet-pretrained CNN (Inception-ResNet-V2) to extract perceptual features from both reference and distorted images before comparing them in the transformer. Direct quote: "A conventional CNN network, Inception-Resnet-V2, is employed as the feature extraction backbone network. Pretrained weights on ImageNet is imported and frozen." The paper explicitly motivates this in Sec 2: "the effectiveness of the deep features on the perceptual IQA task was demonstrated in recent studies [LPIPS (61), DISTS-like (16), TRIQ (55)]." This places IQT within the DFD / deep-feature-based family in the sense Adamson uses the term.

2. **Outperforms conventional IQ metrics on LIVE, CSIQ, TID2013 (Sec 4.3, Tab. 2, p. 5).** On the three standard natural-image IQA datasets, IQT achieves SRCC/KRCC of 0.970/0.849 (LIVE), 0.943/0.799 (CSIQ), 0.899/0.717 (TID2013) — outperforming PSNR (0.873/0.687/0.687 SRCC), SSIM (0.948/0.865/0.727), MS-SSIM (0.951/0.906/0.786), and also beating or matching learned deep-feature methods LPIPS (0.932/0.876/0.670 SRCC), DISTS (0.954/0.929/0.830), PieAPP (0.919/0.892/0.876), WaDIQaM (0.947/0.909/0.831). Direct quote: "For LIVE and TID2013 databases, the proposed IQT shows the best performance in terms of SRCC. Also, it is ranked in the top three in all benchmarks in terms of SRCC and KRCC. In particular, our method shows better performance than recent deep learning-based methods [WaDIQaM, PieAPP, LPIPS, DISTS, SWD] for most cases." This directly supports the Adamson framing that deep / learned perceptual metrics outperform conventional IQ metrics.

3. **Correlation-with-human-perception evaluation (Sec 2 end; Sec 4.3).** Evaluation uses SRCC, KRCC, and PLCC against MOS (human-rated ground truth): "In our study, we select the SRCC, KRCC, and PLCC as performance evaluation metrics." This matches exactly the Adamson claim's "correlation with human perceptual judgments" criterion.

4. **Won NTIRE 2021 large-scale perceptual IQA challenge on PIPAL (Sec 4.5, Tab. 6, p. 6–7).** IQT-C ranked first among 13 participants on the PIPAL testing set (PLCC=0.7896 [1st], SRCC=0.7990 [2nd], Main Score=1.5885 [1st]). On PIPAL validation/testing (Tab. 3), IQT/IQT-C substantially outperforms PSNR (PLCC 0.277 testing), SSIM (0.394), MS-SSIM (0.501), and also outperforms LPIPS-Alex (0.571), LPIPS-VGG (0.633), DISTS (0.687), PieAPP (0.597) in PLCC on testing. Direct quote: "The IQT-C shows the best performance among all metrics... Our model won the first place in terms of the main score among all participants." This is the "large-scale computer vision study" / natural-image benchmark setting the Adamson claim refers to.

5. **All benchmark datasets are natural images, domain-aligned with ImageNet encoder pretraining (Sec 4.1, Tab. 1, p. 4).** LIVE (29 ref / 779 dist.), CSIQ (30 / 866), TID2013 (25 / 3000), KADID-10k (81 / 10.1k), and PIPAL (250 / 29k) are all photographic natural-image IQA datasets with traditional and algorithm-output distortions on natural scenes. The encoder (Inception-ResNet-V2) is pretrained on ImageNet — also natural images. This directly supports Adamson's qualifier that "these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

6. **Paper's own framing: deep perceptual features outperform conventional metrics (Sec 1 & Sec 2).** Direct quote from Sec 1: "The existing objective metrics such as Peak Signal-to-Noise Ratio (PSNR), a structural similarity index (SSIM), and conventional quality metrics are insufficient to predict the quality of this kind of outputs. In this respect, recent works [LPIPS, DISTS-like, PieAPP, WaDIQaM, Zhang et al.] based on perceptual representation exhibit a better performance at the perceptual IQA task." And from Sec 2 on LPIPS: "The LPIPS showed that trained deep features that are optimized by the Euclidean distance between distorted and reference images are effective for IQA compared to the conventional IQA methods." Cheon2021's own narrative mirrors exactly the Adamson claim that LPIPS / deep-feature methods outperform conventional IQ metrics on natural-image benchmarks.

### Notes / Limitations

- IQT is a learned transformer IQA model on top of frozen ImageNet-pretrained features, not a pure fixed DFD like LPIPS. Within the Adamson group citation (28–33), it appropriately represents "learned deep-feature IQA outperforming conventional metrics on natural images." Strictly speaking it is an IQA regressor rather than a feature-distance metric, but the citation remains reasonable as a DFD-family / deep-feature-based learned IQA exemplar.
- The paper does not discuss medical / MRI or out-of-domain evaluation; the citation is appropriate only for the natural-image portion of the Adamson background claim.
- All IQT evaluation datasets (LIVE, CSIQ, TID2013, KADID-10k, PIPAL) are natural-image benchmarks; the encoder is ImageNet-pretrained — directly aligned with the Adamson claim's "same domain as encoder training" qualifier.

---

### C032 — lao2022

**C032 (ref #31):** "Although LPIPS and other DFDs[28–33] outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,[34] these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

Sub-claim for ref 31 (lao2022): example of a DFD-family / learned-deep-feature IQ metric outperforming conventional IQ metrics on natural-image perceptual-quality benchmarks.

### Source

- Lao S, Gong Y, Shi S, Yang S, Wu T, Wang J, Xia W, Yang Y. "Attentions Help CNNs See Better: Attention-based Hybrid Image Quality Assessment Network." CVPR Workshops 2022 (NTIRE 2022 Perceptual IQA Challenge).
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/lao2022.pdf`

### Classification

**BACKGROUND / SUPPORTING** — lao2022 is cited as one of several (refs 28–33) learned / deep-feature IQA methods grouped to support the broader background assertion that learned perceptual metrics outperform conventional IQ metrics on natural-image benchmarks. The claim does not depend on lao2022 quantitatively; it uses AHIQ as an exemplar of learned deep-feature-based IQA that beats PSNR / SSIM on natural-image perceptual benchmarks.

### Verdict

**SUPPORTED** — lao2022 proposes AHIQ (Attention-based Hybrid IQA Network), a full-reference IQA method that uses a two-branch feature extractor composed of a ViT branch (ViT-B/16 or ViT-B/8, ImageNet-pretrained) and a shallow CNN branch (ResNet-50, ImageNet-pretrained), a feature fusion module (deformable convolution + concatenation), and a patch-wise prediction head. AHIQ outperforms PSNR, SSIM, MS-SSIM, FSIMc, VSI, MAD, VIF, NLPD, GMSD, and similar conventional metrics — and is competitive with or better than deep-feature-based learned methods (LPIPS, DISTS, PieAPP, WaDIQaM, IQT) — on standard natural-image IQA benchmarks (LIVE, CSIQ, TID2013, KADID-10k, PIPAL). The ensemble version (AHIQ-C) won first place on the Full-Reference track of the NTIRE 2022 Perceptual IQA Challenge on PIPAL. All benchmark datasets are natural-image IQA datasets whose reference images are in-domain with ImageNet (the encoder pretraining domain), consistent with Adamson's qualifier "natural images belonging to the same domain as the images used for encoder training."

Minor caveat: AHIQ is a learned hybrid ViT+CNN IQA network on top of ImageNet-pretrained frozen-initialization features (not literally a fixed DFD like LPIPS' l2 on VGG features). It is a learned deep-feature-based IQA regressor. Within the Adamson group citation (28–33), which also includes PieAPP, IQT, cong2022 GSN, conde2022 Conformer — all learned deep-feature-based IQA models — AHIQ fits as an instance of "DFD-family / deep-feature IQA outperforming conventional IQ metrics on natural-image benchmarks."

### Attestation log (≥3 phrasings verifying the claim)

#### Phrasing 1 — "Is lao2022 a DFD / deep-feature-based IQ metric?"
Source (Sec 4.2 Implementation Details, p. 5): "Since we use ViT [11] and ResNet [16] models pretrained on ImageNet [29], we normalize all input images and randomly crop them into 224 × 224." Source (Sec 3.1 Feature Extraction Module, p. 4): "the front part of the architecture is a two-branch feature extraction module that consists of a ViT branch and a CNN branch. The transformer feature extractor mainly focuses on extracting global and semantic representations... we introduce another CNN extraction branch apart from the transformer branch to add more local textures." The model extracts deep features from a ViT (ViT-B/16 or B/8) and a ResNet-50 backbone, both pretrained on ImageNet, and regresses perceptual quality from them. The paper explicitly aligns itself with LPIPS as a learned deep-feature IQA method, Sec 2.1 (p. 2): "Zhang et al. [55] proposed to use the learned perceptual image patch similarity (LPIPS) metric for FR-IQA and proved that deep features obtained through pre-trained DNNs outperform previous classic metrics by large margins." Verdict: SUPPORTED. AHIQ is a learned deep-feature-based FR-IQA model built on ImageNet-pretrained encoders, fitting the broad DFD-family umbrella Adamson uses.

#### Phrasing 2 — "Does it outperform PSNR / SSIM and other conventional IQ metrics on natural-image perceptual benchmarks?"
Source (Tab. 2, p. 6 — LIVE / CSIQ / TID2013 PLCC / SROCC):
- PSNR: LIVE 0.865/0.873; CSIQ 0.819/0.810; TID2013 0.677/0.687
- SSIM: 0.937/0.948; 0.852/0.865; 0.777/0.727
- MS-SSIM: 0.940/0.951; 0.889/0.906; 0.830/0.786
- FSIMc: 0.961/0.965; 0.919/0.931; 0.877/0.851
- VIF: 0.960/0.964; 0.913/0.911; 0.771/0.677
- **AHIQ (ours): 0.989/0.984; 0.978/0.975; 0.968/0.962**

Source (Tab. 4, p. 7 — PIPAL NTIRE 2022 Testing PLCC / SROCC):
- PSNR: 0.277/0.249; SSIM: 0.391/0.361; MS-SSIM: 0.163/0.369
- LPIPS-Alex: 0.571/0.566; LPIPS-VGG: 0.633/0.595; DISTS: 0.687/0.655
- IQT: 0.799/0.790
- **AHIQ: 0.823/0.813; AHIQ-C (ensemble): 0.828/0.822**

On every one of these natural-image IQA benchmarks, AHIQ substantially outperforms PSNR, SSIM, MS-SSIM, and other conventional metrics, and also outperforms LPIPS-Alex/VGG and DISTS on the PIPAL large-scale benchmark. Verdict: SUPPORTED.

#### Phrasing 3 — "Correlation-with-human-perception evaluation?"
Source (Sec 4.3, p. 5): "We assess the performance of our model with Pearson's linear correlation coefficient (PLCC) and Spearman's rank-order correlation coefficient (SROCC). PLCC assesses the linear correlation between ground truth and the predicted quality scores, whereas SROCC describes the level of monotonic correlation." Source (Fig. 1 caption, p. 1): "Scatter plots of the objective scores vs. the MOS scores on the validation dataset of the NTIRE 2022 Perceptual Image Quality Assessment Challenge [13]. Higher correlation means better performance of the IQA method." Source (Tab. 1, p. 6): PIPAL contains 250 reference images, 29k distorted images, and 1.13M MOS ratings — a large-scale human-rated IQA dataset. Verdict: SUPPORTED. Evaluation is against human MOS using PLCC / SROCC, exactly matching Adamson's "correlation with human perceptual judgments" phrasing.

#### Phrasing 4 — "Large-scale computer-vision study / benchmark?"
Source (Sec 2 contributions and Sec 4.5, p. 2, 8): "Our method outperforms the state-of-the-art approaches on four benchmark image quality assessment datasets. In particular, the proposed architecture achieves outstanding performance on the PIPAL dataset with various GAN-based distortion and ranked first in the NTIRE 2022 challenge on perceptual image quality assessment." Source (Tab. 9, p. 8 — NTIRE 2022 FR-IQA Test): AHIQ ensemble took 1st place (PLCC 0.828, SROCC 0.822, Main Score 1.651), beating 2nd–5th competitors. NTIRE 2022 on PIPAL is a headline large-scale natural-image computer-vision perceptual-IQA benchmark (1.13M MOS ratings). Verdict: SUPPORTED.

#### Phrasing 5 — "Natural images in the same domain as the encoder training?"
Source (Sec 4.2, p. 5): "Since we use ViT [11] and ResNet [16] models pretrained on ImageNet [29]..." — the encoders are ImageNet-pretrained (natural images). Source (Tab. 1, p. 6): All evaluation datasets — LIVE (29 ref / 779 dist, natural scenes), CSIQ (30/866), TID2013 (25/3000), KADID-10k (81/10.1k), PIPAL (250/29k) — are natural-image IQA benchmarks with photographic reference images and traditional + algorithm-output distortions. This aligns exactly with Adamson's qualifier that the DFD-outperforms-conventional-metrics studies are on "natural images belonging to the same domain as the images used for encoder training." Verdict: SUPPORTED.

### Overall verdict

C032 (sub-claim for ref #31, lao2022): **SUPPORTED.**

AHIQ is a learned deep-feature-based FR-IQA model built on ImageNet-pretrained ViT and ResNet encoders. It substantially outperforms PSNR, SSIM, MS-SSIM, and other conventional IQ metrics on LIVE, CSIQ, TID2013, and PIPAL (and won 1st place at NTIRE 2022 FR-IQA on PIPAL). All evaluations are on natural-image IQA benchmarks in-domain with the ImageNet encoder pretraining. This is exactly the role Adamson et al. assign to ref 31 in the cited sentence: a "DFD" that beats commonly used IQ metrics on correlation with human MOS in a large-scale computer-vision study, evaluated on natural images belonging to the same domain as the encoder training.

### Notes / Limitations

- AHIQ is strictly a learned IQA network rather than a fixed deep-feature-distance metric like LPIPS. Within the Adamson group citation (28–33, which mixes LPIPS with PieAPP, IQT, GSN, Conformer, AHIQ, all learned deep-feature IQA models), AHIQ fits as a "DFD-family / deep-feature-based" exemplar. No correction needed.
- The paper does not discuss medical / MRI or out-of-domain evaluation; the citation is appropriate only for the natural-image portion of the Adamson background claim.

---

### C033 — conde2022

From Adamson et al. 2025 (MRM, DOI 10.1002/mrm.30437):
> "Although LPIPS and other DFDs28–33 outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,34 these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

Sub-claim for ref 32 (conde2022, "Conformer and Blind Noisy Students for Improved Image Quality Assessment," CVPRW 2022):
- conde2022 is an example of a DFD-family IQ metric that outperforms conventional IQ metrics (e.g., PSNR, SSIM) on natural-image perceptual-quality benchmarks.

### Classification
BACKGROUND / SUPPORTING — conde2022 is cited as one of a list of example "DFDs" in a background sentence that sets up Adamson et al.'s methodological concern. The claim does not depend quantitatively on conde2022 but uses it as an exemplar of learned deep-feature-based IQA that beats PSNR/SSIM on natural-image perceptual benchmarks.

### Verification against the source PDF

#### (a) Is conde2022 a DFD-style (deep-feature-distance / deep-feature-based) perceptual metric?
Yes. The paper proposes two learned IQA models that operate on deep features from ImageNet-pretrained CNNs:

1. **Full-Reference "IQA Conformer"** (Section 3). A frozen Inception-ResNet-v2 extracts feature maps from both reference and distorted images; the paper concatenates features from blocks `mixed5b, block35_2/4/6/8/10`, forms `f_ref`, `f_dist`, and an explicit **difference feature map `f_diff = f_ref − f_dist`**, which is then regressed to MOS by a Conformer encoder-decoder.
   - Quote (p. 3): "we concatenate the feature maps from the following blocks: mixed5b, block35 2, block35 4, block35 6, block35 8 and block35 10. We do this for the reference and distorted images generating f_ref and f_dist, respectively. In order to obtain difference information between reference and distorted images, a difference feature map, f_diff = f_ref − f_dist is also used."
   - This is exactly the deep-feature-difference pattern that defines the DFD family (as LPIPS does with `l2` distance on VGG/AlexNet features; conde2022 extends this by learning a transformer-based aggregator over the feature difference).

2. **Blind Noisy Student** (Section 4). A CNN (EfficientNet B0, ImageNet-pretrained) ingests a distorted image and regresses to MOS; this is a deep-feature-based No-Reference IQA model distilled from the FR teacher.

The paper positions itself against traditional PSNR/SSIM and alongside LPIPS as the family of "learned" deep-feature IQA metrics:
- Quote (p. 2): "Zhang et al. proposed a learned perceptual image patch similarity (LPIPS) metric [70], which shows that trained deep features that are optimized by the l2 distance between distorted and reference images are effective for IQA compared to the conventional IQA methods."
- Quote (Abstract): "traditional perceptual quality metrics such as PSNR or SSIM... it is necessary to develop a quantitative metric to reflect the performance of new algorithms."

Verdict on (a): SUPPORTED. conde2022 proposes a deep-feature-based perceptual IQA metric; the FR model explicitly uses a deep-feature difference map, placing it in the DFD family (broadly construed — it is a learned aggregator on top of a deep-feature difference, rather than a fixed l2 distance like LPIPS).

#### (b) Does conde2022 outperform commonly used IQ metrics (PSNR/SSIM) on natural-image perceptual benchmarks?
Yes, unambiguously, on the PIPAL NTIRE 2022 FR and NR benchmarks and on cross-dataset LIVE / TID2013.

- Table 4 (PIPAL NTIRE 2021/2022 FR, Testing 2022):
  - PSNR: PLCC 0.277, SRCC 0.249
  - SSIM: PLCC 0.391, SRCC 0.361
  - LPIPS-VGG: PLCC 0.633, SRCC 0.595
  - Ours IQA Conformer A: PLCC **0.775**, SRCC **0.766**
  - Ensemble: PLCC **0.787**, SRCC **0.793**

- Table 3 (cross-dataset LIVE / TID2013):
  - On LIVE: Ours SRCC 0.921, KRCC 0.752 — competitive with MS-SSIM (0.951) and SSIM (0.948) on the in-distribution traditional benchmark; on TID2013 Ours SRCC 0.82 vs. SSIM 0.727, PSNR 0.687, LPIPS 0.670.
  - The paper highlights: "our model generalizes better than NTIRE 2021 top methods: ASNA [45], RADN [49] and IQT [10]. It also achieves competitive results in comparison with other learnt methods like PieAPP [44], WaDIQaM [6] or LPIPS [70]."

- Table 7 (PIPAL NR, Testing 2022):
  - PSNR Main Score 0.572; SSIM 0.785; LPIPS-AlexNet 1.176; **Ours 1.490**.
  - Caption (verbatim): "Our method outperforms traditional and learnt methods by large margin."

- Figure 3 caption (p. 4): "Our model is the most correlated quantitative metric to the real human MOS subjective ratings."

- Figure 1 (p. 2) explicitly illustrates that PSNR/SSIM disagree with human MOS on PIPAL samples — motivating learned DFDs.

Verdict on (b): SUPPORTED. conde2022's FR and NR methods both outperform PSNR and SSIM (and traditional metrics generally) on the PIPAL natural-image perceptual benchmark and are competitive with or beat LPIPS; results are for natural-image IQA benchmarks (PIPAL, LIVE, TID2013).

#### (c) "Same domain as the encoder training" caveat
Also consistent with Adamson's framing: conde2022's encoders (Inception-ResNet-v2, EfficientNet B0) are pretrained on ImageNet (natural images), and the evaluation datasets (PIPAL, LIVE, TID2013) are natural-image IQA datasets. So the benchmark is in-domain w.r.t. encoder pretraining — exactly the scenario Adamson et al. are contrasting with their MRI setting.

### Attestation log (≥3 phrasings)

#### Phrasing 1 — "Is this a DFD / deep-feature-based IQ metric?"
Source (p. 3, Section 3): "we concatenate the feature maps from the following blocks: mixed5b, block35 2, block35 4, block35 6, block35 8 and block35 10. We do this for the reference and distorted images generating f_ref and f_dist, respectively. In order to obtain difference information between reference and distorted images, a difference feature map, f_diff = f_ref − f_dist is also used."
Also p. 2: "Zhang et al. proposed a learned perceptual image patch similarity (LPIPS) metric [70], which shows that trained deep features... are effective for IQA compared to the conventional IQA methods." — conde2022 aligns itself with the LPIPS/deep-feature paradigm.
Verdict: SUPPORTED. FR model explicitly uses a deep-feature difference; NR model is a deep CNN regressor to MOS. It is a learned deep-feature-based perceptual IQA metric, falling under the broad DFD umbrella Adamson et al. use.

#### Phrasing 2 — "Does it outperform PSNR/SSIM on natural-image perceptual benchmarks?"
Source (Table 4, PIPAL NTIRE 2022 FR Testing): PSNR PLCC/SRCC 0.277/0.249; SSIM 0.391/0.361; Ours IQA Conformer A 0.775/0.766; Ensemble 0.787/0.793.
Source (Table 7, PIPAL NTIRE 2022 NR Testing, Main Score = PLCC+SRCC): PSNR 0.572; SSIM 0.785; LPIPS-AlexNet 1.176; Ours 1.490. Caption: "Our method outperforms traditional and learnt methods by large margin."
Verdict: SUPPORTED. Both FR and NR conde2022 models substantially outperform PSNR and SSIM on the PIPAL benchmark.

#### Phrasing 3 — "Is the evaluation on natural images / in the same domain as the encoder training?"
Source (p. 3, Section 3): "We use a Inception-ResNet-v2 network pre-trained on ImageNet to extract feature maps..." (FR). Section 4: "We train EfficientNet B0 (pre-trained on ImageNet)..." (NR). Datasets used are PIPAL, LIVE, TID2013 — all natural-image IQA datasets (Table 1: "# Ref." = 29/25/250 reference natural images).
Verdict: SUPPORTED. Evaluation is on natural images drawn from the same domain (ImageNet-style natural imagery) as the encoders' pretraining — matching Adamson et al.'s characterization.

#### Phrasing 4 — "Correlation with human MOS on a large-scale IQA benchmark?"
Source (Abstract): "Our approaches achieved competitive results on the NTIRE 2022 Perceptual Image Quality Assessment Challenge: our full-reference model was ranked 4th, and our blind noisy student was ranked 3rd among 70 participants, each in their respective track."
Source (p. 3, Table 1): PIPAL contains 250 reference images, 29k distorted images, 1.13M human ratings — a large-scale MOS dataset.
Source (p. 3, Section 2, Evaluation): "high Pearson linear correlation coefficient (PLCC)... high Spearman rank order correlation coefficient (SRCC)... indicates the monotonicity of relationship between the proposed method and the ground-truth MOS."
Verdict: SUPPORTED. The paper reports correlation with human MOS on large-scale natural-image perceptual-quality benchmarks (PIPAL 1.13M ratings; LIVE; TID2013) and ranks near the top.

### Overall verdict
C033 (sub-claim for ref #32, conde2022): **SUPPORTED.**
conde2022 proposes a learned deep-feature-based IQA metric (the FR "IQA Conformer" explicitly uses a deep-feature difference `f_diff = f_ref − f_dist`, and the NR "Blind Noisy Student" is a deep CNN regressor), and it outperforms PSNR and SSIM by large margins on the PIPAL natural-image perceptual benchmark (as well as performing competitively on LIVE / TID2013). This is exactly the role Adamson et al. assign to ref 32 in the cited sentence: a "DFD" that beats commonly used IQ metrics on correlation with human MOS in a large-scale computer-vision study, evaluated on natural images belonging to the same domain as the encoder training.

#### Minor caveat
"DFD" strictly stands for "deep feature distance." conde2022's FR model computes a deep-feature difference and feeds it to a learned Conformer regressor (rather than using a fixed distance like LPIPS's l2). This is consistent with Adamson et al.'s broader use of "DFDs" as shorthand for the family of learned deep-feature-based perceptual IQA metrics (the citation list LPIPS28–33 mixes full-reference DFDs with models like PieAPP and IQT). No correction needed.

---

### C034 — keshari2022

> Although LPIPS and other DFDs28–33 outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,34 these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training.

**Sub-claim for ref 33:** example DFD IQA metric outperforming conventional metrics on natural-image benchmarks.

### Source
Keshari A, Komal, Sadbhawna, Subudhi B. "Multi-Scale Features and Parallel Transformers Based Image Quality Assessment." arXiv:2204.09779v1, 20 Apr 2022.

### Classification
**SUPPORTING** — Keshari et al. propose an IQ metric (MSFPT) and demonstrate that it outperforms commonly used IQ metrics (PSNR, SSIM, MS-SSIM, LPIPS, DISTS, PieAPP, VIF, FSIM, GMSD, VSI, etc.) on natural-image IQA benchmarks (LIVE, TID2013, KADID-10k, PIPAL) where correlations (PLCC/SRCC/KRCC) with human MOS are the evaluation criterion.

### Verification: does this paper propose an IQ metric that outperforms conventional metrics on natural-image benchmarks?

**YES.**

#### Attestation log (≥3 phrasings)

1. **Abstract, p.1**: "Our experimentation on various datasets, including the PIPAL dataset, demonstrates that the proposed integration technique outperforms existing algorithms."

2. **Introduction contributions, p.2**: "Our method significantly outperforms previous existing methods on benchmark datasets LIVE [41], TID2013 [35], and KADID-10k [26]. Also, proposed MSFPT has comparable performance on PIPAL dataset [17] when evaluated as part of NTIRE 2022 IQA Challenge."

3. **Experiments §3.2, p.5**: "We compare MSFPT network with several state-of-the-art methods on all four datasets [17, 26, 35, 41] for IQA. The methods have deep learning-based methods such as PieAPP [37], LPIPS [56], SWD [16] and DISTS [12] and shallow methods like SSIM [45] and PSNR. For most cases our method shows more promising results than current deep learning-based methods."

4. **§3.2, p.6**: "Our model out performs other deep-learning based models like IQT method [9] on LIVE [41] data set by 0.07 SRCC and 0.029 in KRCC. In case of TID2013 [35] by using weight sharing and multi-scale we outperform existing deep-learning models by 0.021 SRCC, and 0.034 KRCC. For KADID-10k [26], it outperforms various IQA methods like VSI by 0.01 PLCC, 0.004 SRCC and 0.009 KRCC."

5. **Conclusions §4, p.7**: "The proposed method outperforms current state-of-the-art image quality assessment methods in terms of performance."

6. **Table 2 (LIVE, TID2013), p.5** — MSFPT-avg: LIVE PLCC=0.972, SRCC=0.977 (top of table); TID2013 MSFPT-1 PLCC=0.955, SRCC=0.949 (vs LPIPS PLCC=0.934/0.749, SSIM PLCC=0.937/0.777, PSNR PLCC=0.865/0.677). MSFPT clearly exceeds LPIPS and other conventional metrics on these natural-image benchmarks.

7. **Table 3 (KADID), p.6** — MSFPT-avg: PLCC=0.888, SRCC=0.883, KRCC=0.700, surpassing VSI (0.878/0.879/0.691), MDSI, FSIM, GMSD, SSIM, MS-SSIM.

#### Domain match (natural images)
- LIVE [41], TID2013 [35], KADID-10k [26], PIPAL [17] are all natural-image IQA datasets (photographs subjected to traditional and/or GAN-based distortions, rated by human observers via MOS). This matches the Adamson 2025 claim that these studies evaluate on natural images.

#### Notes / caveats
- On PIPAL testing (the GAN-distortion-heavy benchmark), MSFPT ranks 7th in the NTIRE 2022 challenge table (Table 5), i.e., it is competitive but not the top performer there. However, on LIVE, TID2013, and KADID-10k the paper reports outperforming prior state-of-the-art including LPIPS.
- The claim's framing "DFDs...outperform commonly used IQ metrics" is supported: MSFPT is presented as a deep-feature/transformer-based IQ metric that beats conventional metrics (PSNR/SSIM/MS-SSIM) and also the LPIPS deep-feature baseline on these benchmarks.

### Verdict
**SUPPORTING** — the source paper does propose an IQ metric (MSFPT) shown to outperform conventional IQ metrics on natural-image benchmarks, consistent with its use as an exemplar DFD citation in Adamson et al. 2025's ref 33 slot.

---

### C035 — gu2022

From Adamson et al. 2025 (MRM, DOI 10.1002/mrm.30437):
> "Although LPIPS and other DFDs28–33 outperform commonly used IQ metrics in terms of correlation with human perceptual judgments in large-scale computer vision studies,34 these studies evaluate DFDs on natural images belonging to the same domain as the images used for encoder training."

Sub-claim for ref 34 (gu2022):
- Ref 34 is pointing to a "large-scale computer vision study" where DFDs (including LPIPS / DISTS variants and other learned deep-feature-based metrics) are evaluated against commonly used IQ metrics (PSNR / SSIM / FSIM), and the DFDs outperform the conventional metrics in correlation with human perceptual judgments.
- DFDs are trained on / derived from natural-image encoders (e.g., ImageNet-pretrained backbones), and the evaluation is on natural images.

### Classification
BACKGROUND / SUPPORTING — the citation is a pointer to a large-scale benchmark study of IQA methods on natural images. The claim does not depend on a specific number from gu2022, only that it is such a large-scale study and that DFDs/learned methods outperform PSNR/SSIM/FSIM in correlation with human MOS.

### Note on source identity
The local filename is `gu2022.pdf`, and the claim-tracker metadata calls it "NTIRE 2022 Challenge on Perceptual Image Quality Assessment, CVPRW 2022." The PDF itself is in fact the **NTIRE 2021 Challenge on Perceptual Image Quality Assessment** by Jinjin Gu et al. (arXiv:2105.03072, CVPRW 2021). This is the companion / predecessor report for the same PIPAL benchmark that conde2022 (ref #32) competed in; the 2022 edition is a follow-up challenge. The cited role — "a large-scale CV IQA benchmark study where DFDs beat PSNR/SSIM" — is served by the 2021 report directly. (If the manuscript's bibliography points to the 2022 edition rather than the 2021 arXiv, the role is still the same benchmark family, but this should be flagged for bib audit.) See the year/venue caveat at the bottom.

### Verification against the source PDF

#### (a) Is this a large-scale computer-vision IQA study?
Yes. The paper is a CVPR 2021 NTIRE workshop challenge report with substantial scale:

- Participants: "The challenge has 270 registered participants in total. In the final testing stage, 13 participating teams submitted their models and fact sheets." (Abstract, p. 1)
- Dataset (PIPAL): "200 reference images, 29k distorted images and 1.13M human judgements." (p. 2)
- Extended validation/testing set: "3,300 distorted images for 50 reference images... 753k human judgements." (p. 2)
- Published in the IEEE/CVF CVPR Workshops proceedings.

This is squarely a "large-scale computer vision study" of IQA methods.

#### (b) Are DFDs / learned deep-feature methods benchmarked against commonly used IQ metrics?
Yes. Table 1 (p. 3) reports SRCC and PLCC on PIPAL, TID2013, and LIVE for 13 submitted methods plus a standard set of baselines including both conventional and deep-feature metrics:

Baselines (from Table 1):
- **LPIPS-VGG** — Main Score 1.2277, PIPAL SRCC 0.5947 / PLCC 0.6330
- **LPIPS-Alex** — 1.1368, PIPAL SRCC 0.5658 / PLCC 0.5711
- **PieAPP** — 1.2048, PIPAL SRCC 0.6074 / PLCC 0.5974
- **DISTS** — 1.3422, PIPAL SRCC 0.6548 / PLCC 0.6873
- **SWD** — 1.2585, PIPAL SRCC 0.6243 / PLCC 0.6342
- **FSIM** — 1.0748, PIPAL SRCC 0.5038 / PLCC 0.5709
- **SSIM** — 0.7549, PIPAL SRCC 0.3614 / PLCC 0.3936
- **PSNR** — 0.5263, PIPAL SRCC 0.2493 / PLCC 0.2769

The paper explicitly labels its selection (p. 4): "We choose PSNR, SSIM [54] and FSIM [59] as representative traditional IQA methods, PI [7] and NIQE [35] as representative blind IQA methods, and LPIPS [61], DISTS [12], PieAPP [39] and SWD [19] as representative deep-learning based methods."

#### (c) Do DFDs outperform commonly used IQ metrics in correlation with human judgments?
Yes, on all three datasets considered, and substantially so on the perceptually-challenging PIPAL benchmark:

- PIPAL: PSNR SRCC 0.25 vs. LPIPS-VGG 0.59, DISTS 0.65, PieAPP 0.61 — roughly 2x better correlation for DFDs.
- PIPAL: SSIM SRCC 0.36 vs. DFDs 0.56–0.65.
- All 13 submitted team methods (all learned / deep) outperform PSNR and SSIM; 11 of 13 exceed 0.75 SRCC: "11 of 13 participating teams achieve an SRCC score higher than 0.75 on PIPAL, which significantly surpasses the highest performance of existing algorithms (0.65)." (p. 5)
- The champion: "The champion team achieves an SRCC score of 0.799 and a PLCC score of 0.790, refreshing the state-of-the-art performance on PIPAL." (p. 5)
- Figure 1 caption (p. 1): "Higher coefficient matches perceptual score better. The top methods demonstrate the state-of-the-art performance." (top methods are all deep/learned; their SRCC is ~0.75–0.80 vs. PSNR ~0.25.)

#### (d) Are DFDs trained on natural images / same domain as evaluation?
Yes. The DFDs and learned baselines are all natural-image-trained / ImageNet-pretrained, and the PIPAL benchmark is natural photographic images:

- LPIPS uses VGG/AlexNet pretrained on ImageNet (standard natural-image encoders). DISTS similarly uses VGG. PieAPP is trained on natural images.
- Top team "LIPT" uses "Inception-ResNet-V2 network [50] pre-trained on ImageNet" (p. 6).
- Team "MT-GTD" uses "ResNet [24] pre-trained on ImageNet" (p. 7).
- Team "The Amaurotia" uses "A ResNet-50 [24] network pre-trained on ImageNet" (p. 7).
- Team "tsubota" uses "AlexNet [29] pre-trained on ImageNet" (p. 10).
- PIPAL itself is built on high-quality natural reference images (Figure 2 shows natural photographs).

This matches Adamson et al.'s framing precisely: DFDs in this large-scale CV benchmark are trained/pretrained on natural images and evaluated on natural images (the encoder training domain equals the evaluation domain).

### Attestation log (≥3 phrasings)

#### Phrasing 1 — "Is gu2022 a large-scale CV study benchmarking IQ metrics?"
Source (Abstract, p. 1): "This paper reports on the NTIRE 2021 challenge on perceptual image quality assessment (IQA)... The challenge has 270 registered participants in total. In the final testing stage, 13 participating teams submitted their models and fact sheets."
Source (p. 2): "We employ a new dataset called PIPAL... which contains 200 reference images, 29k distorted images and 1.13M human judgements... We also collect an extended dataset of PIPAL for validation and testing. This dataset contains 3,300 distorted images for 50 reference images... We collect 753k human judgements..."
Verdict: SUPPORTED. Large scale in participants, images, and human ratings; venue is CVPR 2021 NTIRE workshop.

#### Phrasing 2 — "Do DFDs/LPIPS outperform commonly used IQ metrics on correlation with human perceptual judgments?"
Source (Table 1, p. 3, Baselines on PIPAL):
- PSNR: SRCC 0.2493, PLCC 0.2769
- SSIM: SRCC 0.3614, PLCC 0.3936
- FSIM: SRCC 0.5038, PLCC 0.5709
- LPIPS-VGG: SRCC 0.5947, PLCC 0.6330
- LPIPS-Alex: SRCC 0.5658, PLCC 0.5711
- DISTS: SRCC 0.6548, PLCC 0.6873
- PieAPP: SRCC 0.6074, PLCC 0.5974
Source (p. 5): "11 of 13 participating teams achieve an SRCC score higher than 0.75 on PIPAL, which significantly surpasses the highest performance of existing algorithms (0.65)."
Verdict: SUPPORTED. DFD baselines (LPIPS, DISTS, PieAPP, SWD) all have SRCC/PLCC roughly 0.56–0.69 on PIPAL, clearly outperforming PSNR (0.25) and SSIM (0.36). All 13 learned team methods also outperform the traditional metrics.

#### Phrasing 3 — "Are the evaluations on natural images in the same domain as the encoder training?"
Source (p. 6, LIPT team): "an Inception-ResNet-V2 network [50] pre-trained on ImageNet [42] is used to extract perceptual representations from both reference and distorted images."
Source (p. 7, MT-GTD): "At first, ResNet [24] pre-trained on ImageNet [29] is used as the feature extraction backbone."
Source (p. 7, The Amaurotia): "A ResNet-50 [24] network pre-trained on ImageNet [29] is used as the feature extraction backbone and multi-scale deep representations are extracted for comparison."
Source (p. 10, tsubota): "they replace the VGG [48] network in PieAPP with AlexNet [29] pre-trained on ImageNet [11]..."
Source (Figure 2, p. 2): shows natural photographs (crowd scenes, buildings) as PIPAL reference images.
Verdict: SUPPORTED. Encoders for DFDs are ImageNet-pretrained (natural-image domain), PIPAL is a natural-image IQA dataset; evaluation domain matches encoder-training domain. This is exactly the scenario Adamson et al. contrast with their MRI setting.

#### Phrasing 4 — "Is this a precedent study that establishes DFDs as state of the art for human-perception correlation?"
Source (Abstract, p. 1): "Almost all of them [13 teams] have achieved much better results than existing IQA methods, while the winning method can demonstrate state-of-the-art performance."
Source (p. 5): "The champion team achieves an SRCC score of 0.799 and a PLCC score of 0.790, refreshing the state-of-the-art performance on PIPAL."
Source (Figure 1 caption, p. 1): "SRCC represents Spearman rank order correlation coefficient and PLCC represents Pearson linear correlation coefficient. Higher coefficient matches perceptual score better. The top methods demonstrate the state-of-the-art performance."
Verdict: SUPPORTED. The paper frames itself as establishing SOTA for perceptual IQA against a field of DFD baselines; this is precisely the "large-scale CV study" role Adamson et al. assign to ref 34.

### Overall verdict
C035 (sub-claim for ref #34, gu2022): **SUPPORTED.**
The Gu et al. NTIRE Perceptual IQA challenge report is a large-scale computer-vision IQA benchmark study in which LPIPS, DISTS, PieAPP, SWD, and other DFD / learned methods are evaluated alongside PSNR / SSIM / FSIM on natural-image perceptual benchmarks (PIPAL, TID2013, LIVE) with over 1.8 million human judgments. The DFDs and learned methods clearly outperform the conventional IQ metrics in correlation (SRCC/PLCC) with human MOS, and all of the learned methods rely on ImageNet-pretrained natural-image encoders. This matches Adamson et al.'s characterization on all three elements: (i) large-scale CV study, (ii) DFDs outperform commonly used IQ metrics, (iii) encoders trained on the same natural-image domain as the evaluation.

#### Caveat — year/venue mismatch in manuscript bib
The PDF available in this workflow is the **NTIRE 2021** challenge report (Gu et al., CVPRW 2021, arXiv:2105.03072), not the NTIRE 2022 report. If the manuscript's reference 34 is actually bibliographed as "NTIRE 2022 Challenge on Perceptual Image Quality Assessment, CVPRW 2022," that specific paper is a separate follow-up. The 2021 report is already a fully sufficient source for the cited role, but the year/venue string in the bibliography should be spot-checked during `verify-bib`.

---

### C036 — deng2009

**C036 (ref #35)**: "We gather insights from the transfer learning literature for medical imaging, where the transfer of weights from ImageNet35 pre-trained architectures often fails due to distributional shifts and the difference in features between natural images and downstream medical imaging datasets."

**Sub-claim for ref 35 (deng2009)**: The citation is a pointer to ImageNet (the dataset itself).

**Evidence bar**: FRAMING / BACKGROUND — the paper simply needs to be the ImageNet paper.

### Source

- Deng, Dong, Socher, Li, Li, Fei-Fei. "ImageNet: A Large-Scale Hierarchical Image Database." CVPR 2009.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/deng2009.pdf`

### Verification: Is this the canonical ImageNet paper?

Yes. The paper is the canonical introduction of the ImageNet dataset. Verified via full read of all 8 pages.

#### Phrasing 1 — Title
> "ImageNet: A Large-Scale Hierarchical Image Database"
(Page 1, title)

#### Phrasing 2 — Abstract introduces the database
> "We introduce here a new database called 'ImageNet', a large-scale ontology of images built upon the backbone of the WordNet structure. ImageNet aims to populate the majority of the 80,000 synsets of WordNet with an average of 500-1000 clean and full resolution images."
(Page 1, Abstract)

#### Phrasing 3 — Introduction restates the contribution
> "In this paper, we introduce a new image database called 'ImageNet', a large-scale ontology of images. We believe that a large-scale ontology of images is a critical resource for developing advanced, large-scale content-based image search and image understanding algorithms, as well as for providing critical training and benchmarking data for such algorithms."
(Page 1, Section 1 Introduction)

#### Phrasing 4 — Scale / scope
> "This paper offers a detailed analysis of ImageNet in its current state: 12 subtrees with 5247 synsets and 3.2 million images in total."
(Page 1, Abstract)

#### Phrasing 5 — Public availability as a dataset resource
> "The database is publicly available at http://www.image-net.org."
(Page 1)

Authors (Deng, Dong, Socher, Li-Jia Li, Kai Li, Fei-Fei), affiliation (Princeton CS), venue (CVPR 2009 — reference list entries are formatted in CVPR style, paper is widely known and archived as CVPR 2009), and content (dataset construction: WordNet backbone, AMT annotation pipeline, scale/diversity/accuracy analyses, three applications: NN/NBNN recognition, tree-max classification, automatic localization) are all consistent with the canonical ImageNet dataset paper.

### Does this paper make the manuscript's surrounding claim?

**No, and it does not need to.** The Adamson et al. 2025 sentence is about transfer learning failures from ImageNet-pretrained weights to medical imaging — a downstream literature finding. The deng2009 citation marker (ref 35) is placed on the word "ImageNet" itself, functioning as a pointer to the dataset introduction. The paper's topic (dataset construction, WordNet hierarchy, AMT labeling, object recognition demos on mammal/vehicle subtrees) contains nothing about transfer learning, medical imaging, distributional shift, or pretrained-weight behavior — because in 2009 that literature did not yet exist. The citation is operating as a named-entity reference, not as a source for the transfer-learning argument.

### Classification

- Evidence bar (FRAMING / BACKGROUND — must be the ImageNet paper): **MET**
- CITED_OUT_OF_CONTEXT check: **Not flagged.** Although the surrounding sentence describes transfer-learning failures that deng2009 does not discuss, the citation is idiomatically acting as a pointer to the dataset. The manuscript's structure (the "35" is attached directly to the token "ImageNet") makes this a reference-the-thing citation, not a reference-the-finding citation. The transfer-learning claim is supported elsewhere (via the other refs in that passage, not via ref 35). No misattribution of a claim to deng2009.

### Verdict

**SUPPORTED** — deng2009 is the canonical ImageNet dataset paper, which is exactly the role required by the sub-claim for ref 35.

---

### C037 — raghu2019

"We gather insights from the transfer learning literature for medical imaging,
where the transfer of weights from ImageNet35 pre-trained architectures often
fails due to distributional shifts and the difference in features between
natural images and downstream medical imaging datasets.36"

Sub-claim attributed to raghu2019: ImageNet pre-training often fails (or doesn't
help much) for downstream medical imaging tasks due to feature distribution
differences.

### Source
Raghu, Zhang, Kleinberg, Bengio. "Transfusion: Understanding Transfer Learning
for Medical Imaging." NeurIPS 2019. arXiv:1902.07208v3.
PDF: paper-trail-adamson2025-dfd/pdfs/raghu2019.pdf (22 pages, read in full).

### Classification
DIRECT — the manuscript's sub-claim is exactly what Transfusion's abstract,
introduction, Section 3 Results, and Conclusion state.

### Attestation log (verbatim phrasings from raghu2019)

1. Abstract (p.1):
   "A performance evaluation on two large scale medical imaging tasks shows
   that surprisingly, transfer offers little benefit to performance, and
   simple, lightweight models can perform comparably to ImageNet
   architectures."

2. Abstract (p.1):
   "there are fundamental differences in data sizes, features and task
   specifications between natural image classification and the target medical
   tasks, and there is little understanding of the effects of transfer."

3. Introduction / contribution [1] (p.2):
   "We find that (i) in all of these cases, transfer does not significantly
   help performance (ii) smaller, simpler convolutional architectures perform
   comparably to standard ImageNet models (iii) ImageNet performance is not
   predictive of medical performance."

4. Introduction (p.2):
   "ImageNet classification and medical image diagnosis have considerable
   differences. First, many medical imaging tasks start with a large image of
   a bodily region of interest and use variations in local textures to
   identify pathologies ... This is in contrast to natural image datasets like
   ImageNet, where there is often a clear global subject of the image ...
   There is thus an open question of how much ImageNet feature reuse is
   helpful for medical images."

5. Section 3 (Models and Performance Evaluation of Transfer Learning), p.3:
   "We find that across both datasets and all models, transfer learning does
   not significantly affect performance."

6. Section 3.2 Results, p.3 (discussing Table 1, Retina):
   "transfer learning has minimal effect on performance, not helping the
   smaller CBR architectures at all, and only providing a fraction of a
   percent gain for Resnet and Inception."

7. Table 1 caption (p.4): "Transfer learning and random initialization perform
   comparably across both standard ImageNet architectures and simple,
   lightweight CNNs for AUCs from diagnosing moderate DR."
   Numbers: Resnet-50 Random Init 96.4% vs Transfer 96.7%; CBR-Tiny 95.7% vs
   95.8%.

8. Table 2 caption (p.4): "Transfer learning provides mixed performance gains
   on chest x-rays ... we see that transfer learning does not help
   significantly, and much smaller models performing comparably." Per-disease
   numbers show transfer slightly worse on Atelectasis, Cardiomegaly,
   Consolidation, marginally better on Edema and Pleural Effusion.

9. Conclusion (p.9):
   "we find that transfer learning offers limited performance gains and much
   smaller architectures can perform comparably to the standard ImageNet
   models. Our exploration of representational similarity and feature reuse
   reveals surprising correlations between similarities at initialization and
   after training for standard ImageNet models, providing evidence of their
   overparametrization for the task. We also find that meaningful feature
   reuse is concentrated at the lowest layers ..."

### Check: tables comparing transfer vs scratch
- Table 1 (Retina, AUCs): random init ≈ transfer across Resnet-50, Inception-v3
  and all CBR variants — differences are 0.0-0.3 percentage points.
- Table 2 (CheXpert, AUCs across 5 pathologies): transfer is sometimes worse
  (Atelectasis, Cardiomegaly, Consolidation for Resnet-50) and sometimes
  slightly better; no uniform or large benefit.
- Table 3 (small data regime, 5k Retina): for small CBR models, pretrained
  AUC equals random-init AUC to within 0.1 pp; only the large Resnet sees a
  meaningful gap, attributed to model size rather than feature usefulness.
- Table 4 appendix: confirms that for CBR-LargeT, CBR-LargeW, random init and
  pretrained are within ~0.3 pp.
Every table the manuscript could cite for "transfer vs scratch" supports the
claim that ImageNet transfer often does not help.

### Nuance
- Transfusion frames the failure in two related ways:
  (i) limited/no performance improvement over random init, and
  (ii) "considerable differences" in features, image statistics, dataset size,
      and class count between ImageNet and medical images. Page 2 explicitly
      lists global-subject vs local-texture differences as a mechanism for why
      feature reuse is in question.
- The paper does NOT use the exact phrase "distributional shift"; it uses
  "fundamental differences" / "considerable differences" in features and data.
  Adamson et al.'s phrasing ("distributional shifts and the difference in
  features between natural images and downstream medical imaging datasets")
  is a faithful paraphrase of Transfusion's argument.
- Transfusion also shows feature-independent weight-scaling benefits (Mean Var
  Init, Section 5) — i.e., pretrained weights can still help convergence
  speed via scaling even when features aren't reused. Adamson's claim is
  about performance/"feature" transfer, which is what Transfusion's main
  results (Tables 1-3, Section 3) are about, so this nuance does not
  undermine C037.

### Verdict
SUPPORTED (DIRECT). The Transfusion paper's headline findings — transfer
offers little benefit, smaller from-scratch models match ImageNet-pretrained
models, and the gap is explained by differences in features/data between
ImageNet and medical images — are exactly the sub-claim Adamson et al. make
for ref #36.

---

### C038 — mei2022

**Section:** 
**Citekey:** `mei2022` (ref #37)
**Claim text:** downstream medical image classification tasks.37,38 In the absence of a large domain-specific dataset, self-supervised learning (SSL) on an unlabeled but in-domain dataset has repeatedly outperformed ImageNet pretraining on a wide range of downstream medical imaging tasks.38,39 These findings have led to the widespread understanding that domain-specific feature representations are better than out-of-domain ones, raising the question of whether domain-specific feature representations are of similar value in computing DFDs for MR IQ assessment.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mei2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C039 — cadrinchenevert2022

**Section:** 
**Citekey:** `cadrinchenevert2022` (ref #38)
**Claim text:** downstream medical image classification tasks.37,38 In the absence of a large domain-specific dataset, self-supervised learning (SSL) on an unlabeled but in-domain dataset has repeatedly outperformed ImageNet pretraining on a wide range of downstream medical imaging tasks.38,39 These findings have led to the widespread understanding that domain-specific feature representations are better than out-of-domain ones, raising the question of whether domain-specific feature representations are of similar value in computing DFDs for MR IQ assessment.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/cadrinchenevert2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C040 — huang2023

C040 (ref #39): "In the absence of a large domain-specific dataset, self-supervised learning (SSL) on an unlabeled but in-domain dataset has repeatedly outperformed ImageNet pretraining on a wide range of downstream medical imaging tasks." (Adamson et al. 2025, cites refs 38,39.)

### Sub-claim for ref 39 (huang2023)
SSL on in-domain medical data outperforms ImageNet pretraining (i.e., supervised pre-training on natural images) on downstream medical imaging classification tasks.

### Source
Huang SC, Pareek A, Jensen M, Lungren MP, Yeung S, Chaudhari AS. "Self-supervised learning for medical image classification: a systematic review and implementation guidelines." npj Digital Medicine (2023) 6:74. DOI: 10.1038/s41746-023-00811-0. 79 included studies, PRISMA systematic review.

### Classification
DIRECT — SUPPORTING (review-paper evidence; quantitative aggregate across 79 studies).

### Verdict
v = SUPPORTED

The Huang 2023 review explicitly concludes that SSL pre-training generally outperforms purely supervised baselines (including ImageNet pre-training) for medical image classification, and that continuing in-domain SSL after natural-image pre-training yields the best results. This directly supports the Adamson et al. sub-claim for ref 39.

### Attestation log (≥3 phrasings)

1. Discussion, p. 10: "the majority of self-supervised pre-trained models led to a relative increased performances of 0.216–32.6% AUROC, 0.440–29.2% accuracy, and 0.137–14.3% F1 score over the same model architecture without SSL pre-training, including both ImageNet and random initialization (Fig. 4e)." — This explicitly benchmarks SSL against ImageNet pre-training across the included studies and finds SSL superior for the majority.

2. Implementation guidelines, p. 10 (citing Azizi et al.): "Azizi et al. have shown that SSL pre-trained models using natural images tend to outperform purely supervised pre-trained models for medical image classification, and continuing self-supervised pre-training with in-domain medical images leads to the best results." — Directly states in-domain SSL yields best downstream medical-imaging performance, matching the Adamson claim that in-domain SSL beats ImageNet pretraining.

3. Future research, p. 12: "Results from this systematic review have revealed that SSL for medical image classification is a growing and promising field … We found that self-supervised pre-training generally improves performance for medical imaging classification tasks over purely supervised methods." — General review-level conclusion that SSL outperforms supervised (ImageNet) pre-training baselines across medical imaging tasks.

4. Contrastive results, p. 4: "Thirty-six studies compared contrastive SSL pre-training to supervised pre-training and reported an average improvement in performance of 6.35%." — Quantitative aggregate across 36 studies showing SSL exceeds supervised (typically ImageNet) pre-training.

5. Combined approaches, p. 10: "Eight of the studies that combined different strategies compared self-supervised pre-training with purely supervised approaches, all of which reported performance improvement (0.140–8.29%)." — All comparisons of combined SSL vs supervised (ImageNet) baselines favored SSL.

6. Discussion/recommendation, p. 10: "In the presence of relevant data, we recommend implementing self-supervised learning strategies for training medical image classification models since our literature review indicated that self-supervised pre-training generally results in better model performance, especially when annotations are limited (Table 1)." — Review-level recommendation rooted in the "SSL > supervised/ImageNet" finding across the evidence base.

### Notes / caveats
- The Huang 2023 review phrases the comparison as "SSL vs purely supervised pre-training." In the vast majority of the included studies the supervised baseline is ImageNet pre-training (the standard in the field and explicitly stated for the Azizi et al. reference). The Adamson sub-claim's framing of "ImageNet pretraining" is therefore consistent with the review's comparator.
- The review also notes a publication-bias limitation (p. 12) and that not all studies favored SSL ("four studies reported a slight decrease in performance (0.980–4.51%)," p. 10), but the overall aggregated conclusion across 79 studies still supports the Adamson claim.
- The review covers a "wide range" of downstream medical imaging tasks (radiology, pathology, ophthalmology, dermatology, obstetrics, psychiatry, gastroenterology; X-ray, CT, MRI, WSI, fundus, OCT, ultrasound, endoscopy — Fig. 4a,b), matching Adamson's "wide range of downstream medical imaging tasks."

---

### C041 — kastryulin2023

**Section:** 
**Citekey:** `kastryulin2023` (ref #40)
**Claim text:** Only one study has shown that LPIPS outperforms commonly used IQ metrics in an MR image-based reader study, but it neither explores whether natural image DFDs are optimal for MR images nor does it evaluate MR images with clinically feasible corruptions of accelerated MR image reconstructions.40 Finally, as IQ metrics should be sensitive to imperfections that are expected of reconstructions in a clinical setting, we interrogate the behavior of these metrics under acquisition errors (e.g., poor SNR or motion artifacts), sparse sampling reconstruction errors (aliasing artifacts), and errors resulting from imperfect reconstruction methods.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/kastryulin2023.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C042 — wang2024

**Section:** 
**Citekey:** `wang2024` (ref #41)
**Claim text:** In light of the recent “hidden noise” problem,41 the bias present in conventional reconstruction IQ metrics introduced by acquisition noise in “ground truth” data, we additionally assess how perceptual IQ metrics perform under increasing acquisition noise.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/wang2024.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C043 — knoll2020

**Section:** Methods (dataset selection for DL reconstruction experiments)
**Citekey:** `knoll2020` (ref #42)
**Claim text:** We used the fastMRI multi-coil knee dataset with sparse and fully acquired k-space data for DL-based accelerated MR image reconstructions.
**Claim type:** BACKGROUND / POINTER (dataset citation) — the fastMRI data-resource paper is attested as the source of the multi-coil knee k-space dataset (with both fully sampled and retrospectively undersampled variants) used by Adamson et al.
**Sub-claim attributed:** "fastMRI provides a multi-coil knee dataset with both sparse and fully-acquired k-space." Knoll et al. 2020 directly supports all three pieces: (a) the data are multi-coil (explicit `multicoil_train`/`multicoil_val`/`multicoil_test` splits; multichannel receive-array acquisition), (b) the data are of the knee (1594 clinical knee MRI examinations; paper title), and (c) the dataset includes fully sampled k-space with retrospectively undersampled (sparse) variants for train/test splits. The phrasing "sparse and fully acquired k-space" maps cleanly onto Knoll's "fully sampled k-space" + "undersampled k-space data ... by retrospectively masking k-space lines from a fully sampled acquisition."
**Source excerpt:**
- Title (p. 1): "fastMRI: A Publicly Available Raw k-Space and DICOM Dataset of Knee Images for Accelerated MR Image Reconstruction Using Machine Learning."
- Abstract / intro (p. 1): "The k-space data comprises 1594 measurement datasets obtained in knee MRI examinations from a range of MRI systems and clinical patient populations, with corresponding images derived from the k-space data using reference image reconstruction algorithms."
- p. 1 (download splits): "multicoil_train (931 GB), multicoil_val (192 GB), multicoil_test (109 GB), singlecoil_train (88 GB), singlecoil_val (19 GB), and singlecoil_test (7 GB)."
- §k-Space Dataset (p. 2): "Fully sampled k-space data from 1594 consecutive clinical MRI proton density–weighted acquisitions of the knee in the coronal plane with and without frequency-selective fat saturation are included."
- §k-Space Dataset (p. 2): "the data were acquired with a multichannel receive array coil."
- Table 1 (p. 2): "Receive coil: 15 channel Tx-Rx" (for both coronal PD-weighted and coronal PD-weighted FS protocols).
- p. 3 (undersampling): "Examples in the test and challenge sets contain undersampled k-space data. The undersampling is performed by retrospectively masking k-space lines from a fully sampled acquisition. k-Space lines are omitted only in the phase-encoding direction to simulate physically realizable accelerations in 2D data acquisitions."
- Fig. 2 caption (p. 4): "Examples of binary sampling masks (white = included, black = omitted) for pseudorandomly undersampled k-space data with fourfold acceleration (left) and eightfold acceleration (right)."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       5 pages (Radiology: Artificial Intelligence 2020; 2(1):e190007), data-resource article incl. Abbreviations, Summary, Key Points, Description of the Dataset, k-Space Dataset, DICOM Dataset, Discussion, Acknowledgments, Disclosures, References.
  Section checklist:  Title / byline ✓, Abstract / intro paragraph ✓, Summary ✓, Key Points ✓,
                      Description of the Dataset ✓, Table 1 (Acquisition Parameters) ✓,
                      Figure 1 (example coronal PD images) ✓, Table 2 (Metadata fields) ✓,
                      §k-Space Dataset ✓ (incl. fully-sampled description + download splits),
                      Figure 2 (undersampling masks) ✓, §DICOM Dataset ✓, §Discussion ✓,
                      Acknowledgments ✓, Author contributions ✓, Disclosures ✓, References (1–19) ✓.
  Phrasings searched: "multi-coil" / "multicoil" / "multichannel" (coil-count framing);
                      "knee" / "knee MRI" / "knee examinations" (anatomy);
                      "fully sampled" / "fully acquired" (ground-truth framing);
                      "undersampled" / "sparse" / "retrospective masking" / "acceleration" (sparse framing);
                      "k-space" / "raw data" / "ISMRM raw data format" (data-type framing);
                      "1594" / "training / validation / testing" (scale and splits);
                      "DL" / "deep learning" / "machine learning" / "reconstruction" (target-use framing).
  Specific checks:    Data splits enumeration on p. 1 explicitly names multicoil_train / multicoil_val / multicoil_test
                      alongside singlecoil_*, establishing multi-coil as a first-class split, not an afterthought.
                      §k-Space Dataset (p. 2) confirms fully sampled coronal PD / PD-FS acquisitions are the source;
                      Table 1 confirms 15-channel Tx-Rx coil hardware (multi-coil).
                      p. 3 confirms the sparse k-space variants are generated by retrospective phase-encode
                      masking of the fully sampled acquisitions, with 4x and 8x acceleration masks (Fig. 2).
                      All three ingredients of the sub-claim (multi-coil ✓, knee ✓, sparse+fully-acquired k-space ✓)
                      are independently verified.
  Closest adjacent passage: "Fully sampled k-space data from 1594 consecutive clinical MRI proton density–
                      weighted acquisitions of the knee ..." (p. 2) + "Examples in the test and challenge sets
                      contain undersampled k-space data. The undersampling is performed by retrospectively
                      masking k-space lines from a fully sampled acquisition." (p. 3) — jointly near-verbatim
                      support for the sub-claim.
  Indirect-attribution check: Knoll et al. present the dataset as a primary release from their group + Facebook AI
                      Research. A companion arXiv preprint (Zbontar et al., ref 19 in this paper) provides
                      extended background; the data resource itself is native to this paper. Primary-source
                      citation by Adamson et al. is appropriate.
  Out-of-context check: Adamson et al. use the dataset in its canonical intended use (DL-based accelerated
                      MR reconstruction on multi-coil knee k-space, with undersampling masks against fully
                      sampled references). Knoll et al. explicitly state this as the motivating use case
                      ("enable accelerated MRI acquisitions of ... fast-spin-echo sequences" / "the first
                      large-scale dataset tailored to the problem of image reconstruction using machine
                      learning techniques"). Usage aligns with source scope.

---

### C044 — sandino2020

**Section:** 
**Citekey:** `sandino2020` (ref #2)
**Claim text:** network.2 The UNet models followed the architecture in the fastMRI challenge,42 while the unrolled models followed the fast iterative shrinkage-thresholding algorithm (FISTA) unrolled architecture43 implemented in.2 Reference images were computed from the fully sampled k-space data with the eSPIRIT method to integrate coil sensitivities.44 The magnitude of the complex image data was taken for both the evaluation by radiologists and the computation of IQ metrics.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sandino2020.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C045 — knoll2020

**Section:** Methods (model architectures for reconstruction experiments)
**Citekey:** `knoll2020` (ref #42)
**Claim text:** network.2 The UNet models followed the architecture in the fastMRI challenge,42 while the unrolled models followed the fast iterative shrinkage-thresholding algorithm (FISTA) unrolled architecture43 implemented in.2 Reference images were computed from the fully sampled k-space data with the eSPIRIT method to integrate coil sensitivities.44 The magnitude of the complex image data was taken for both the evaluation by radiologists and the computation of IQ metrics.
**Claim type:** ARCHITECTURAL ATTRIBUTION — Adamson et al. attribute a specific UNet architecture ("the architecture in the fastMRI challenge") to knoll2020 (ref #42).
**Sub-claim attributed:** "The UNet architecture used by Adamson et al. follows the baseline U-Net defined in the fastMRI challenge, cited to knoll2020." Knoll et al. 2020 is the fastMRI data-resource paper; it announces the dataset and a forthcoming challenge but does NOT specify or describe any neural-network architecture — UNet or otherwise. The paper contains zero mentions of "U-Net", "UNet", "convolutional neural network", "encoder", "decoder", "baseline model", or any architectural specification. The UNet baseline associated with the fastMRI benchmarks is defined in a separate companion paper (Zbontar, Knoll, Sriram et al., "fastMRI: An Open Dataset and Benchmarks for Accelerated MRI," arXiv:1811.08839), which is cited within knoll2020 as ref 19 but is itself not the cited source here.
**Source excerpt:**
- Full-paper content check (pp. 1–5): no occurrence of the strings "U-Net", "UNet", "U Net", "neural network", "CNN", "convolutional", "encoder", "decoder", "baseline model", "architecture", "challenge leaderboard" specifying a model.
- §Description of the Dataset through §DICOM Dataset (pp. 1–4): the paper describes data acquisition, splits, metadata, undersampling masks, and DICOM contents — no model definitions.
- p. 3: "The first official challenge associated with the dataset is forthcoming." (The challenge had not yet been run at time of publication; no challenge architecture is reported here.)
- p. 4: "Complete details regarding this dataset, as well as relevant background material intended to empower investigators to tackle problems in image reconstruction, can be found in Zbontar et al (19)." — knoll2020 explicitly defers benchmark/architecture detail to the companion arXiv paper (Zbontar et al. 2018, ref 19), NOT to itself.
- p. 5 (references): ref 19 = "Zbontar J, Knoll F, Sriram A, et al. fastMRI: An Open Dataset and Benchmarks for Accelerated MRI. arXiv 1811.08839." — this is the actual source of the fastMRI UNet baseline architecture.
**Support:** NOT_SUPPORTED
**Flag:** MISCITATION (architecture attribution is to the wrong fastMRI paper; knoll2020 is the data-resource paper and does not specify a UNet baseline).
**Remediation:** Consider citing Zbontar et al. 2018 (arXiv:1811.08839) — or the fastMRI benchmarks paper with the UNet-baseline definition — in place of, or in addition to, knoll2020 (ref #42) for the UNet architecture claim. If the intent is to cite the fastMRI dataset AND the UNet baseline together in one shorthand, split the citation: knoll2020 for the dataset (as in C043) and Zbontar et al. 2018 for the baseline architecture.
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       5 pages (Radiology: Artificial Intelligence 2020; 2(1):e190007).
  Section checklist:  Title / byline ✓, Abstract / intro paragraph ✓, Summary ✓, Key Points ✓,
                      §Description of the Dataset ✓, Table 1 (Acquisition Parameters) ✓,
                      Figure 1 (example reconstructions) ✓, Table 2 (Metadata fields) ✓,
                      §k-Space Dataset ✓, Figure 2 (undersampling masks) ✓, §DICOM Dataset ✓,
                      §Discussion ✓, Acknowledgments ✓, Author contributions ✓, Disclosures ✓,
                      References 1–19 ✓.
  Phrasings searched: "U-Net" / "UNet" / "U Net" — 0 hits;
                      "neural network" / "deep network" / "CNN" / "convolutional" — 0 hits;
                      "architecture" — 0 hits;
                      "encoder" / "decoder" / "skip connection" — 0 hits;
                      "baseline" / "baseline model" — 0 hits;
                      "challenge" — hits only as "planned image reconstruction challenge" and
                      "first official challenge associated with the dataset is forthcoming" (no model spec);
                      "Zbontar" — appears as ref 19 only.
  Specific checks:    Read every paragraph of the main text (pp. 1–4) plus the reference list (p. 5).
                      The paper's entire scope is dataset curation, storage, splits, undersampling masks,
                      and DICOM inclusion; it does not define, name, or propose any reconstruction model.
                      Figure 1 shows sum-of-squares coil-combined reconstructions from fully sampled
                      k-space (not a learned model). Figure 2 shows undersampling masks (not a model).
                      The only mention of benchmarking infrastructure points forward to a forthcoming
                      challenge and sideways to Zbontar et al. (ref 19) for "complete details."
  Closest adjacent passage: "Complete details regarding this dataset, as well as relevant background material
                      intended to empower investigators to tackle problems in image reconstruction, can be
                      found in Zbontar et al (19)." (p. 4) — this is the paper's own pointer AWAY from itself
                      for architectural / benchmarking detail.
  Indirect-attribution check: The fastMRI UNet baseline originates in Zbontar, Knoll, Sriram et al.,
                      "fastMRI: An Open Dataset and Benchmarks for Accelerated MRI," arXiv:1811.08839
                      (listed as ref 19 within knoll2020). That preprint defines the baseline UNet used
                      in the fastMRI challenge. The correct primary citation for the UNet-architecture
                      claim is Zbontar et al. 2018, not Knoll et al. 2020. Using knoll2020 for the
                      architecture claim is an indirect / misdirected attribution.
  Out-of-context check: Adamson et al. lean on knoll2020 to do two jobs at once: (a) name the dataset
                      (well-supported — see C043) and (b) specify the UNet architecture used. Job (a)
                      is correctly scoped to this source; job (b) overreaches — the source does not
                      contain the architectural content being attributed. The same citation is reused
                      at C043 for the dataset (CONFIRMED) and at C045 for the architecture (NOT_SUPPORTED),
                      which cleanly isolates the scope problem to the architecture sub-claim.
  Nuance note: This is a common shorthand in the MR-reconstruction literature — "fastMRI" is used
                      loosely to mean "the fastMRI dataset + the fastMRI baselines" as a bundle.
                      The correct bibliographic practice is to cite the data-resource paper (knoll2020)
                      for the dataset and the benchmarks paper (Zbontar et al. 2018 / arXiv:1811.08839)
                      for the UNet baseline. Adamson et al.'s C045 citation elides this split.

---

### C046 — xin2023

**Section:** 
**Citekey:** `xin2023` (ref #43)
**Claim text:** network.2 The UNet models followed the architecture in the fastMRI challenge,42 while the unrolled models followed the fast iterative shrinkage-thresholding algorithm (FISTA) unrolled architecture43 implemented in.2 Reference images were computed from the fully sampled k-space data with the eSPIRIT method to integrate coil sensitivities.44 The magnitude of the complex image data was taken for both the evaluation by radiologists and the computation of IQ metrics.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/xin2023.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C047 — uecker2014

**Section:** 
**Citekey:** `uecker2014` (ref #44)
**Claim text:** network.2 The UNet models followed the architecture in the fastMRI challenge,42 while the unrolled models followed the fast iterative shrinkage-thresholding algorithm (FISTA) unrolled architecture43 implemented in.2 Reference images were computed from the fully sampled k-space data with the eSPIRIT method to integrate coil sensitivities.44 The magnitude of the complex image data was taken for both the evaluation by radiologists and the computation of IQ metrics.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/uecker2014.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C048 — gu2022

From Adamson et al. 2025 (MRM, DOI 10.1002/mrm.30437):
> "We evaluated several state-of-the-art DFDs used in natural domain IQ assessment34 to serve as benchmarks for the domain-specific DFDs proposed in this work."

Sub-claim for ref 34 (gu2022):
- Ref 34 supports the phrase "state-of-the-art DFDs used in natural domain IQ assessment," i.e., the paper should establish which DFD / learned deep-feature metrics are considered state-of-the-art on natural-image perceptual-quality benchmarks. Adamson et al. then use these same DFDs as benchmarks against their proposed domain-specific (MRI) DFDs.

### Classification
BACKGROUND / SUPPORTING — the citation points to a large-scale natural-image IQA benchmark that identifies and ranks the leading DFDs. Adamson et al. use this as the rationale for which DFDs to adopt as their natural-domain baselines.

### Note on source identity
The local filename is `gu2022.pdf`; the PDF itself is the **NTIRE 2021 Challenge on Perceptual Image Quality Assessment** (Gu et al., CVPRW 2021, arXiv:2105.03072). See C035 for the year/venue caveat. The paper plays the same role — authoritative benchmark survey of SOTA deep-feature IQA metrics on natural images — regardless of which edition (2021 vs. 2022) the bibliography actually references.

### Verification against the source PDF

#### (a) Does the paper identify/rank SOTA DFDs used in natural-image IQ assessment?
Yes. Table 1 (p. 3) gives a ranked comparison of 13 team methods plus a baseline panel containing the major DFD / learned deep-feature metrics of the period:

Baselines explicitly included (Table 1, Baselines section, p. 3):
- LPIPS-VGG, LPIPS-Alex
- PieAPP
- DISTS
- SWD
- FSIM, SSIM, PSNR (traditional baselines)

The paper states (p. 4, Section 4, "Challenge Results"): "We choose PSNR, SSIM [54] and FSIM [59] as representative traditional IQA methods, PI [7] and NIQE [35] as representative blind IQA methods, and LPIPS [61], DISTS [12], PieAPP [39] and SWD [19] as representative deep-learning based methods."

This is a direct statement that LPIPS, DISTS, PieAPP, and SWD are the "representative deep-learning based" (i.e., DFD-family) IQ metrics for natural-image IQA in this benchmark.

#### (b) Does the paper establish these as "state of the art"?
Yes, with quantitative context:

- p. 5: "11 of 13 participating teams achieve an SRCC score higher than 0.75 on PIPAL, which significantly surpasses the highest performance of existing algorithms (0.65). The champion team achieves an SRCC score of 0.799 and a PLCC score of 0.790, refreshing the state-of-the-art performance on PIPAL."
- Abstract: "Almost all of them have achieved much better results than existing IQA methods, while the winning method can demonstrate state-of-the-art performance."
- Figure 1 caption (p. 1): "Higher coefficient matches perceptual score better. The top methods demonstrate the state-of-the-art performance."
- Table 1 and Figure 1 contain SRCC/PLCC numbers on PIPAL / TID2013 / LIVE for all ranked methods (team submissions + baselines), making this a de facto SOTA leaderboard.

#### (c) Is the evaluation "natural domain IQ assessment"?
Yes. PIPAL is built on natural photographic reference images (Figure 2, p. 2 shows natural scenes — crowd photo, building), and the DFDs use ImageNet-pretrained natural-image encoders (see per-team descriptions in Section 5):
- p. 6, LIPT: "Inception-ResNet-V2 network [50] pre-trained on ImageNet"
- p. 7, MT-GTD: "ResNet [24] pre-trained on ImageNet"
- p. 7, The Amaurotia: "ResNet-50 [24] network pre-trained on ImageNet"
- p. 10, tsubota: "AlexNet [29] pre-trained on ImageNet"
TID2013 and LIVE (the other benchmarks used in Table 1) are also natural-image IQA datasets.

#### (d) Are the specific DFDs that Adamson et al. evaluate actually identified here as the SOTA set?
Yes. Adamson et al. evaluate LPIPS and the DISTS family as natural-domain DFD baselines. These are precisely the methods listed as "representative deep-learning based methods" in this benchmark study's baseline panel (LPIPS, DISTS, PieAPP, SWD), with full correlation numbers against human MOS on three natural-image datasets.

### Attestation log (≥3 phrasings)

#### Phrasing 1 — "Does ref 34 name the DFDs considered state of the art for natural-image IQA?"
Source (p. 4): "We choose PSNR, SSIM [54] and FSIM [59] as representative traditional IQA methods, PI [7] and NIQE [35] as representative blind IQA methods, and LPIPS [61], DISTS [12], PieAPP [39] and SWD [19] as representative deep-learning based methods."
Source (Table 1, p. 3, Baselines): lists LPIPS-VGG, LPIPS-Alex, PieAPP, DISTS, SWD alongside FSIM, SSIM, PSNR with per-metric SRCC/PLCC on PIPAL, TID2013, LIVE.
Verdict: SUPPORTED. LPIPS, DISTS, PieAPP, SWD are explicitly identified as the representative deep-feature-based IQA methods for natural-image benchmarking.

#### Phrasing 2 — "Does ref 34 report SOTA quantitative performance for these DFDs vs. traditional metrics?"
Source (p. 5): "The champion team achieves an SRCC score of 0.799 and a PLCC score of 0.790, refreshing the state-of-the-art performance on PIPAL."
Source (Abstract, p. 1): "Almost all of them have achieved much better results than existing IQA methods, while the winning method can demonstrate state-of-the-art performance."
Source (Table 1, p. 3): Quantitative comparison table — DFDs (LPIPS-VGG SRCC 0.59, DISTS SRCC 0.65, PieAPP SRCC 0.61) vs. traditional (PSNR SRCC 0.25, SSIM SRCC 0.36) on PIPAL.
Verdict: SUPPORTED. Paper's explicit framing is that the methods benchmarked — including the DFD baselines — define the state of the art on PIPAL.

#### Phrasing 3 — "Is this 'natural domain IQ assessment'?"
Source (Figure 2, p. 2): shows natural photographs as PIPAL reference images.
Source (p. 2): PIPAL includes "the outputs of perceptual-oriented algorithms" applied to natural reference images; training uses 200 natural reference images, 29k distorted natural images, 1.13M human judgments.
Source (per-team descriptions, Section 5, p. 6–10): encoders used by the top team methods are "pre-trained on ImageNet" — i.e., natural-image encoder domain. Baseline DFDs (LPIPS VGG/Alex, DISTS) are similarly ImageNet-pretrained by construction.
Verdict: SUPPORTED. The benchmark is a natural-image IQA setting with natural-image encoders, matching "natural domain IQ assessment."

#### Phrasing 4 — "Does it make sense to cite ref 34 as the reason for choosing specific DFDs as benchmarks?"
Source (Section 4, p. 4): Paper explicitly designates LPIPS, DISTS, PieAPP, and SWD as "representative deep-learning based methods" — i.e., the canonical set a follow-on paper would adopt as natural-domain DFD benchmarks.
Adamson et al. evaluate LPIPS (VGG/Alex) and DISTS variants as natural-domain DFD benchmarks — a subset of this representative set.
Verdict: SUPPORTED. The citation performs the role Adamson et al. assign to it: it identifies and benchmarks the SOTA DFDs used in natural-image IQA, justifying the choice of LPIPS / DISTS as natural-domain benchmarks in the Adamson et al. study.

### Overall verdict
C048 (sub-claim for ref #34, gu2022): **SUPPORTED.**
The NTIRE Perceptual IQA challenge report explicitly identifies LPIPS, DISTS, PieAPP, and SWD as the representative deep-learning (DFD-family) IQ metrics for natural-image IQA, and ranks them against traditional PSNR/SSIM/FSIM on PIPAL / TID2013 / LIVE with full SRCC and PLCC numbers. The paper's framing is that these methods — along with the 13 team submissions — establish state of the art for natural-image perceptual IQ. This fully supports Adamson et al.'s use of ref 34 as the citation for "state-of-the-art DFDs used in natural domain IQ assessment."

#### Caveat
Same NTIRE 2021 vs. NTIRE 2022 bibliographic caveat as C035; flag during `verify-bib`. The role is performed identically by the 2021 edition PDF on hand.

---

### C049 — chen2022

**Section:** Introduction / Methods framing (IQ metrics)
**Citekey:** `chen2022` (ref #5)
**Claim text:** The most commonly used IQ metrics to evaluate the IQ of MR reconstruction magnitude images are normalized root mean square error (NRMSE), peak signal-to-noise ratio (PSNR), and structural similarity index measure (SSIM).5
**Claim type:** PARAPHRASED (high) — a summary-of-literature claim citing ref 5's meta-analysis as the evidence base.
**Sub-claim attributed:** full sentence. Chen et al.'s meta-analysis of 92 CS-MRI studies directly supports the "most commonly used = NRMSE, PSNR, SSIM" framing. The restriction to "magnitude images" is a scope tightening by Adamson et al. and is consistent with Chen's coverage (Chen's reviewed studies overwhelmingly report metrics computed on magnitude reconstructions).
**Source excerpt:**
- p. 239 (§V-C, Evaluation Metrics): "Thus, quantitative metrics, such as SSIM, PSNR, and NRMSE, were the most prevalent."
- p. 239: "To compare the reconstructed images with the ground truth, most studies reported the structural similarity index measure (SSIM) and the peak signal-to-noise ratio (PSNR) [see Fig. 4(b)]. Fewer used NRMSE, MSE, and the signal-to-noise ratio (SNR)."
- Fig. 4(b) caption (p. 238): metric-frequency bar chart for 92 reviewed studies — SSIM and PSNR appear as the top-two bars, with NRMSE next among quantitative metrics.
- p. 241 (§VI): "we encourage future studies to test their model performance on commonly used datasets ... and metrics (PSNR and SSIM)".
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       22 pages
  Section checklist:  Abstract ✓, §I Introduction ✓, §II Network Architectures ✓, §III Image Redundancy ✓,
                      §IV Meta-Analysis Method ✓, §V Meta-Analysis Results incl. §V-C Evaluation Metrics ✓,
                      §VI Challenges ✓, §VII Conclusion and Outlook ✓, References ✓,
                      Tables 1–3 ✓, Fig. 1–5 captions ✓ (Fig. 4(b) = metric-frequency plot; Fig. 4(f) = metric correlation heatmap).
                      Supplementary Material (Table 5) referenced but not fetched — main-text §V-C is sufficient for this claim.
  Phrasings searched: "most prevalent", "most commonly used", "routinely used" (frequency paraphrases);
                      "NRMSE" / "normalized root mean square error" (alt. form);
                      "PSNR" / "peak signal-to-noise" (alt. form);
                      "SSIM" / "structural similarity" (alt. form);
                      "evaluation metrics" / "quantitative metrics" (category paraphrase).
  Specific checks:    Fig. 4(b) inspected for the bar-chart ordering of metrics used across the 92 studies;
                      §V-C prose inspected for explicit frequency language ("most prevalent", "fewer used");
                      §VI Challenges cross-checked — Chen's own recommendation is to report PSNR and SSIM,
                      consistent with their being "commonly used";
                      §IV-B.3 (p. 235) Performance analysis is built around SSIM and PSNR odds'-ratios,
                      confirming these are the framework's default benchmarking metrics.
  Closest adjacent passage: "quantitative metrics, such as SSIM, PSNR, and NRMSE, were the most prevalent" (p. 239) — direct match.
  Indirect-attribution check: Chen's observation is a first-order empirical finding of their own meta-analysis (92 studies); not indirectly attributed. Appropriate primary source.
  Out-of-context check: Adamson et al. cite this claim to establish the IQ-metric landscape they are critiquing; Chen et al. describe the same landscape in their Evaluation Metrics results section. Contexts align.
  Nuance note (not a support-level downgrade): Adamson's ordering "NRMSE, PSNR, SSIM" differs from Chen's frequency ordering (SSIM > PSNR > NRMSE). This is a stylistic ordering, not a factual reordering of which metrics are most common. The substantive claim (these three are the most commonly used) is CONFIRMED.

---

### C050 — sheikh2006

**Section:** 
**Citekey:** `sheikh2006` (ref #18)
**Claim text:** considering both the degradation of the signal and the inherent information content of the ground truth image.18 NQM evaluates the reconstructed image by considering spatial frequency response, luminance adaptation, and contrast masking effects.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sheikh2006.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C051 — sheikh2006

**Section:** 
**Citekey:** `sheikh2006` (ref #18)
**Claim text:** We implement VIF and NQM in Python following the procedures described in18 and,19 respectively.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sheikh2006.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C052 — dameravenkata2000

**Section:** 
**Citekey:** `dameravenkata2000` (ref #19)
**Claim text:** We implement VIF and NQM in Python following the procedures described in18 and,19 respectively.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/dameravenkata2000.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C053 — zhouwang2004

**C053 (ref #45):** "SSIM is a combined measure of the luminance, contrast, and structure of the image given by^45 SSIM(x, x̂) = l(x, x̂) · c(x, x̂) · s(x, x̂),"

Sub-claim for ref 45 (zhouwang2004): SSIM, as defined by Wang et al. 2004, is the product of three components — luminance comparison l, contrast comparison c, and structure comparison s.

### Classification

**DIRECT / DEFINITIONAL** — this is a direct definitional claim stating the functional form of the SSIM index as introduced by its defining paper. zhouwang2004 is the correct and authoritative source.

### Source

- Wang Z, Bovik AC, Sheikh HR, Simoncelli EP. "Image Quality Assessment: From Error Visibility to Structural Similarity." IEEE Transactions on Image Processing, vol. 13, no. 4, pp. 600-612, April 2004. DOI 10.1109/TIP.2003.819861.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/zhouwang2004.pdf`

### Verdict

**SUPPORTED (high confidence)** — Wang et al. 2004 explicitly decompose the similarity measure into three comparisons (luminance, contrast, structure) and combine them multiplicatively. The product form with unit exponents used by Adamson matches the form chosen by Wang et al. when α = β = γ = 1 (Eq. 12 with the stated parameterization), which the authors adopt for the paper. The factored form SSIM = l · c · s is exactly the form taught as the canonical SSIM.

### Attestation log (≥3 phrasings verifying the claim)

1. **Combination equation (Sec. III.B, Eq. 5, p.5).** "Finally, the three components are combined to yield an overall similarity measure: S(x, y) = f(l(x, y), c(x, y), s(x, y))." This establishes that the similarity measure is a combination of three labelled components: luminance l, contrast c, and structure s — exactly the three components Adamson names.

2. **Three-comparison separation (Sec. III.B, p.5).** "The system separates the task of similarity measurement into three comparisons: luminance, contrast and structure." This is verbatim the triplet Adamson cites ("luminance, contrast, and structure of the image"). Wang et al. frame SSIM as precisely this tripartite construct.

3. **Explicit product form (Sec. III.B, Eq. 12, p.6).** "Finally, we combine the three comparisons of Eqs. (6), (9) and (10) and name the resulting similarity measure the Structural SIMilarity (SSIM) index between signals x and y: SSIM(x, y) = [l(x, y)]^α · [c(x, y)]^β · [s(x, y)]^γ." With α = β = γ = 1, which the authors adopt immediately afterward — "In order to simplify the expression, we set α = β = γ = 1 and C3 = C2/2 in this paper" — this reduces exactly to SSIM(x, y) = l(x, y) · c(x, y) · s(x, y), matching Adamson's equation character-for-character in structure.

4. **Specific simplified form (Sec. III.B, Eq. 13, p.6).** "This results in a specific form of the SSIM index: SSIM(x, y) = (2μ_x μ_y + C1)(2σ_xy + C2) / [(μ_x² + μ_y² + C1)(σ_x² + σ_y² + C2)]." This is the product l · c · s with the simplification C3 = C2/2 cancelled through — demonstrating the product form concretely as adopted in the paper.

5. **Abstract / title.** The paper's title ("...Structural Similarity") and abstract frame SSIM as a composite similarity index. Keyword list includes "structural similarity (SSIM)." The name "Structural SIMilarity" is explicitly constructed on the three-comparison product (l, c, s), underscoring that SSIM and the l·c·s decomposition are inseparable in the defining paper.

6. **Diagram (Fig. 3, p.6).** The SSIM measurement system block diagram explicitly shows three parallel comparison blocks — "Luminance Comparison," "Contrast Comparison," "Structure Comparison" — feeding a single "Combination" block that outputs the similarity measure. Visual confirmation of the tripartite product structure.

### Notes / Limitations

- Adamson's equation omits the exponents α, β, γ; Wang et al.'s general form (Eq. 12) allows them as tunable relative weights, but the authors themselves set α = β = γ = 1 for the paper, so Adamson's unit-exponent product form matches the canonical form used by Wang et al. This is the standard textbook presentation of SSIM and is not a misrepresentation.
- The argument "x, x̂" (reference, estimate) in Adamson corresponds to "x, y" (reference, distorted) in Wang et al. — trivial notational difference, no semantic change.
- Citation of ref 45 (zhouwang2004) is correct: this is the defining SSIM paper.

---

### C054 — zhouwang2004

**C054 (ref #45):** "where luminance l assesses the mean pixel values across the images, contrast c measures the similarity of the standard deviations of the pixel values across the images, and structure s compares the similarity in the spatial distribution [...]"

Sub-claim for ref 45 (zhouwang2004): In SSIM as defined by Wang et al. 2004, the three components are characterized by (i) l = a function of mean pixel values, (ii) c = a function of standard deviations of pixel values, and (iii) s = a function comparing the spatial/structural distribution of pixel values (i.e., correlation of mean-subtracted, variance-normalized signals).

### Classification

**DIRECT / DEFINITIONAL** — this is a direct definitional claim about the statistical ingredients of SSIM's three comparison functions. zhouwang2004 is the correct and authoritative source.

### Source

- Wang Z, Bovik AC, Sheikh HR, Simoncelli EP. "Image Quality Assessment: From Error Visibility to Structural Similarity." IEEE Transactions on Image Processing, vol. 13, no. 4, pp. 600-612, April 2004. DOI 10.1109/TIP.2003.819861.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/zhouwang2004.pdf`

### Verdict

**SUPPORTED (high confidence)** — Wang et al. 2004 explicitly (a) define l(x, y) in terms of the local means μ_x, μ_y (mean intensity), (b) define c(x, y) in terms of the local standard deviations σ_x, σ_y (used as the signal-contrast estimator), and (c) define s(x, y) as the correlation between mean-subtracted, variance-normalized signals — i.e., a comparison of the structural/spatial distribution of pixel intensities. All three halves of Adamson's description map exactly onto Wang et al.'s definitions.

### Attestation log (≥3 phrasings verifying the claim)

1. **Luminance = mean (Sec. III.B, Eq. 2 and Eq. 6, p.5).** "First, the luminance of each signal is compared. Assuming discrete signals, this is estimated as the mean intensity: μ_x = (1/N) Σ x_i." Then: "For luminance comparison, we define l(x, y) = (2μ_x μ_y + C1) / (μ_x² + μ_y² + C1)." The luminance-comparison function l is explicitly and solely a function of the mean pixel values μ_x, μ_y. Matches Adamson's "luminance l assesses the mean pixel values across the images" verbatim in intent.

2. **Contrast = standard deviation (Sec. III.B, Eq. 4 and Eq. 9, p.5).** "We use the standard deviation (the square root of variance) as an estimate of the signal contrast. An unbiased estimate in discrete form is given by σ_x = ((1/(N-1)) Σ (x_i - μ_x)²)^(1/2). The contrast comparison c(x, y) is then the comparison of σ_x and σ_y." Then Eq. 9: "c(x, y) = (2σ_x σ_y + C2) / (σ_x² + σ_y² + C2)." The contrast-comparison function c is explicitly and solely a function of the standard deviations σ_x, σ_y. Matches Adamson's "contrast c measures the similarity of the standard deviations of the pixel values" precisely.

3. **Structure = correlation of normalized signals / spatial distribution (Sec. III.B, p.5-6, Eqs. 10-11).** "Third, the signal is normalized (divided) by its own standard deviation, so that the two signals being compared have unit standard deviation. The structure comparison s(x, y) is conducted on these normalized signals (x - μ_x)/σ_x and (y - μ_y)/σ_y." And on p.6: "Structure comparison is conducted after luminance subtraction and variance normalization. Specifically, we associate the two unit vectors (x - μ_x)/σ_x and (y - μ_y)/σ_y ... with the structure of the two images. The correlation (inner product) between these is a simple and effective measure to quantify the structural similarity." Finally Eq. 10: "s(x, y) = (σ_xy + C3) / (σ_x σ_y + C3)." This is exactly the correlation coefficient between x and y — it compares the spatial pattern of how pixel values deviate from their local mean, i.e., "the similarity in the spatial distribution" (Adamson's phrasing). Matches precisely.

4. **Definition of structural information as spatial pattern (Sec. III.B, p.5).** "We define the structural information in an image as those attributes that represent the structure of objects in the scene, independent of the average luminance and contrast." This is the conceptual grounding for why s is defined on luminance-subtracted, variance-normalized signals: it isolates the spatial distribution of intensities from the overall mean (luminance) and spread (contrast). This supports Adamson's "spatial distribution" characterization of s.

5. **Geometric interpretation of structure (Sec. III.B, p.6).** "Geometrically, the correlation coefficient corresponds to the cosine of the angle between the vectors x - μ_x and y - μ_y." The structure term measures how similarly pixel deviations from the mean are arranged across the image — i.e., the similarity of the spatial distribution pattern — providing an additional, geometric attestation for Adamson's "spatial distribution" phrasing.

6. **Block diagram (Fig. 3, p.6).** The signal-flow diagram shows that each image first passes through a "Luminance Measurement" block (computing μ), then a subtraction yields the mean-removed signal which passes through a "Contrast Measurement" block (computing σ), and division by σ yields the unit-variance normalized signal that feeds the "Structure Comparison" block. The three comparison functions operate on mean (luminance), standard deviation (contrast), and the mean-subtracted/variance-normalized spatial pattern (structure) respectively — visually confirming Adamson's three-part characterization.

7. **Local statistics used throughout (Sec. III.C, Eqs. 14-16, p.7).** In the MSSIM implementation, local μ_x, σ_x, σ_xy are computed per window and used in the same l, c, s functions. This confirms that across all of SSIM, the three functions are defined on exactly these three statistical quantities (mean / std-dev / covariance-of-normalized-signals), not on other quantities — reinforcing that Adamson's three descriptors exhaust SSIM's definitional content.

### Notes / Limitations

- Adamson says structure "compares the similarity in the spatial distribution" — Wang et al. formalize this as the correlation coefficient between the mean-subtracted, variance-normalized signals (Eq. 10). "Spatial distribution of pixel values (after luminance/contrast normalization)" is a reasonable plain-language paraphrase of "correlation of normalized signals," which is the canonical structural-similarity interpretation in Wang et al. Not a misrepresentation.
- The phrase "mean pixel values" in Adamson corresponds to Wang et al.'s μ_x (mean intensity, Eq. 2). "Standard deviations of the pixel values" corresponds to σ_x (Eq. 4). Exact one-to-one mapping.
- Citation of ref 45 (zhouwang2004) is correct: this is the defining SSIM paper, where the components l/c/s are introduced with exactly these statistical ingredients.
- Adamson's claim text is truncated ("[...]"); the verifiable portion (mean / std-dev / spatial distribution) is fully supported. If the omitted continuation makes further claims, those would need separate verification — but nothing in the provided text conflicts with zhouwang2004.

---

### C055 — miao2008

**C055 (ref #13):** "where LoG is a rotationally symmetric Laplacian of Gaussian filter with a kernel size of 15 × 15 pixels and a standard deviation of 1.5 pixels.13"

Sub-claim for ref 13 (miao2008): the HFEN metric's LoG filter parameters (15 × 15 kernel, sigma = 1.5) are sourced from miao2008.

### Classification

**DIRECT (numerical / parametric)** — this is a specific quantitative claim: a kernel size (15 × 15 pixels) and a standard deviation (1.5 pixels) for a rotationally symmetric Laplacian of Gaussian filter used to compute HFEN (high-frequency error norm). The citation asserts miao2008 is the source of those specific numerical parameters and of the HFEN filter definition.

### Source

- Miao J, Huo D, Wilson DL. "Quantitative image quality evaluation of MR images using perceptual difference models." Medical Physics 35(6), 2541–2553 (2008). DOI: 10.1118/1.2903207.
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/miao2008.pdf`

### Verdict

**UNSUPPORTED — WRONG CITATION.** miao2008 does not define HFEN, does not use a Laplacian of Gaussian (LoG) filter, and nowhere specifies a 15 × 15 kernel or a sigma / standard deviation of 1.5 pixels for any LoG-type filter. Exhaustive reading of the full 13-page paper (abstract; §I Introduction; §II Methods incl. §II.A Experimental conditions, §II.B DSCQS, §II.C FMT, §II.D 2-AFC; §III Results; §IV Discussion; §V Conclusions; Tables I–VIII; Figs. 1–6; all 71 references) turned up no mention of HFEN, "high-frequency error norm," "Laplacian of Gaussian," "LoG," "fspecial," "15 × 15," or any kernel size / sigma specification for an edge / high-frequency filter. The metric HFEN and its canonical LoG(15 × 15, sigma = 1.5) parameter set originate with Ravishankar & Bresler 2011 ("MR image reconstruction from highly undersampled k-space data by dictionary learning," IEEE TMI 30(5):1028–1041), not miao2008. This is a citation error: the numerical parameters Adamson reports (15 × 15, 1.5) are correct for HFEN as conventionally implemented, but they do not come from miao2008. The paper being invoked is a PDM (Case-PDM) validation paper for MR IQ, whose processing pipeline (retinal luminance calibration, 2D CSF, cortex filters) is not a LoG filter at all.

### Attestation log (≥3 phrasings verifying the absence of the claim in the cited source)

1. **Verbatim string search — "HFEN" and "high-frequency error norm."** Full-text extraction of miao2008.pdf (1931 lines) searched case-insensitively for "HFEN" and for "high-frequency error norm" (and "high frequency error"). Zero hits. The seven IQ metrics miao2008 actually benchmarks are enumerated in §II (pp. 2543–2544) and in Table VI (p. 2548): Case-PDM, Sarnoff's IDM, SSIM, NR, DCTune, IQM, and MSE. HFEN is not one of them, is not named anywhere in the paper, and is not in the 71-entry reference list.

2. **Verbatim string search — "Laplacian of Gaussian" / "LoG."** Case-insensitive search of the full text for "Laplacian of Gaussian," "Laplacian," "LoG," and "Gaussian" in a filter-kernel context returned zero matches for any LoG filter definition. The Methods section describes Case-PDM's processing as "Retinal Luminance Calibration → 2D CSF → Cortex Filters → Detection and Contrast Mechanisms → Difference Visualization → PDM Score" (Fig. 1(a) block diagram, p. 2542). None of those blocks is a Laplacian-of-Gaussian filter. The 2D CSF is a contrast-sensitivity function; the cortex filters are spatial-frequency/orientation channels (Gabor-like, not LoG). No LoG, no edge-map filter with the structure HFEN requires.

3. **Verbatim string search — "15 × 15," "15x15," "15,15," "kernel size," "rotationally symmetric."** Zero hits for any of these. The only numerical parameters in miao2008's Methods are display / viewing parameters and reconstruction parameters: "viewing distance = 0.3 m, pixel size = 0.3 mm, minimum luminance = 0.01 cd/m², maximum luminance = 99.9 cd/m², and display bits = 8" (p. 2543); image sizes 256×256, 209×256, 128×128 (p. 2543); "Gaussian white noise with zero means and different standard deviations (σ = 1 – 30) were added to the original image to create the noisy data sets" (p. 2543); "circular averaging filter (pillbox) of the radius 0.5 – 0.7" for blur (p. 2544); decimation factor of 2; display resolution 1280 × 1024; display gamma 3.0; refresh rate 85 Hz. None of these is a LoG kernel size. There is no 15 × 15, no filter-std-dev of 1.5.

4. **Verbatim string search — "1.5."** The literal token "1.5" appears in miao2008 only as: (a) y-axis tick labels in Fig. 4(b) and Fig. 5(b) z-score plots (±1.5); (b) the x-value "1.5" inside Table VIII fitted parameters (row Brain-blur fitted b = 1.452; "-1.28" intercept in Table III; etc., none of which is a filter std dev); (c) the sentence "0.4, 0.9, 1.5, and 1.3, respectively" (p. 2550), which is the standard-to-mean ratio of nonperceptible-difference thresholds for Case-PDM, IDM, SSIM, and MSE — i.e., a *statistic over Case-PDM threshold values*, not a filter parameter. No occurrence of 1.5 in the paper is a LoG standard deviation.

5. **Section-by-section checklist.** Abstract (p. 2541) — no HFEN, no LoG. §I Introduction (pp. 2541–2543) — enumerates prior IQ metrics (SNR, CNR, RMS, Shannon information, PSNR, MSE, RMSE, artifact power, IDM, SSIM, DCTune, IQM, NR) but not HFEN; defines PDM class, not HFEN. §II.A Experimental conditions (p. 2543) — display and image parameters; no filter kernel. §II.B DSCQS (pp. 2543–2544) — subject scoring protocol. §II.C FMT (p. 2545) — Anderson's functional measurement theory; no filter. §II.D 2-AFC (p. 2546) — psychophysical threshold protocol; no filter. §III Results (pp. 2546–2550) — correlation / rank-order / outlier / RMS results across Case-PDM, IDM, SSIM, NR, MSE, DCTune, IQM (Tables II–VIII); HFEN never appears. §IV Discussion (pp. 2550–2551) — comparison of the seven models; no HFEN, no LoG. §V Conclusions (p. 2551) — summary; no HFEN, no LoG. References (pp. 2551–2553, refs 1–71) — no Ravishankar & Bresler, no HFEN-defining paper.

6. **Provenance of the HFEN(LoG 15×15, σ=1.5) specification.** The HFEN metric and its canonical "rotationally symmetric Laplacian of Gaussian filter with kernel size 15 × 15 pixels and standard deviation 1.5 pixels" specification originate with Ravishankar & Bresler (IEEE TMI 2011). That paper defines HFEN as `||LoG(x̂) − LoG(x*)||₂` with the LoG constructed using MATLAB's `fspecial('log', 15, 1.5)` — i.e., the exact numerical parameters Adamson reports. miao2008 predates this definition by three years and operates in a different methodological frame (full HVS-based PDM), so it cannot be the source of these parameters.

### Notes / Limitations

- The numerical parameters themselves (15 × 15, σ = 1.5) are standard and correct for the usual HFEN definition; the issue is solely one of citation. The correct reference for this LoG parameter set is Ravishankar & Bresler 2011 (and its downstream propagation into CS-MRI IQ-metric reporting, including Chen et al. 2022's meta-analysis).
- Possible causes of the citation error: (i) Adamson may have intended ref 13 to anchor a preceding sentence in the paragraph (e.g., the PDM-class reference bundle 13–17) and the citation migrated forward; (ii) confusion between miao2008 (MR-PDM) and Ravishankar & Bresler (MR-CS with HFEN); (iii) transcription slip during BibTeX reconciliation. This is worth flagging in the manuscript remediation notes.
- Recommended remediation: replace ref 13 on this sentence with the Ravishankar & Bresler 2011 paper (or the specific downstream reference that introduced the 15 × 15 / σ = 1.5 specification into the authors' HFEN implementation), and verify any other occurrences in the manuscript where HFEN parameters are cited to ref 13.

### Last verified

2026-04-17

---

### C056 — chen2022

**Section:** Methods / IQ-metric motivation (introducing alternative metrics)
**Citekey:** `chen2022` (ref #5)
**Claim text:** Although less routinely reported than the preceding IQ metrics,5 VIF, NQM, and HFEN have shown promise in prior work.
**Claim type:** PARAPHRASED (medium) — the ref-5 anchor supports the comparative-frequency framing (VIF/NQM/HFEN "less routinely reported than" NRMSE/PSNR/SSIM). The "shown promise" sub-clause is supported by other citations in the sentence, not by ref 5.
**Sub-claim attributed:** "VIF, NQM, and HFEN are less routinely reported than NRMSE, PSNR, and SSIM." The sentence's "shown promise in prior work" is attributed to different refs, not evaluated here.
**Source excerpt:**
- p. 239 (§V-C, Evaluation Metrics): "most studies reported the structural similarity index measure (SSIM) and the peak signal-to-noise ratio (PSNR) [see Fig. 4(b)]. Fewer used NRMSE, MSE, and the signal-to-noise ratio (SNR)."
- p. 239: "Thus, quantitative metrics, such as SSIM, PSNR, and NRMSE, were the most prevalent."
- Fig. 4(b) caption (p. 238): metric-frequency bar chart — abbreviation list for reported metrics is "SSIM, PSNR, NRMSE, MSE, SNR, NMSE, HFEN, RMSE". HFEN appears in the figure's reported-metric list but is not among the most-prevalent bars.
- p. 239 (§V-C, metric-correlation discussion): "The most highly correlated quantitative metrics are high-frequency error norm (HFEN), MAE, PSNR, and MAE." — HFEN is a metric the review tracks, but reported by only a subset of the 92 studies.
- VIF (visual information fidelity) and NQM (noise quality measure) are NOT mentioned anywhere in chen2022 (verified by exhaustive case-insensitive search for "VIF", "NQM", "visual information", "noise quality"). Their absence from a systematic review of 92 deep-learning CS-MRI studies is itself consistent with "less routinely reported" — in fact, not reported at all in this review's sample.
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       22 pages
  Section checklist:  Abstract ✓, §I Introduction ✓, §II Network Architectures ✓, §III Image Redundancy ✓,
                      §IV Meta-Analysis Method ✓, §V Meta-Analysis Results incl. §V-C Evaluation Metrics ✓,
                      §VI Challenges ✓, §VII Conclusion and Outlook ✓, References ✓,
                      Tables 1–3 ✓, Fig. 1–5 captions ✓ (esp. Fig. 4(b) metric-frequency bar chart, Fig. 4(f) R² heatmap).
                      Supplementary Table 5 (metrics over time) referenced but not fetched;
                      main-text prose and Fig. 4(b) abbreviation list provide sufficient evidence for this sub-claim.
  Phrasings searched: "VIF" (verbatim); "visual information fidelity" (expanded); "visual information" (semantic);
                      "NQM" (verbatim); "noise quality" (semantic); "noise quality measure" (expanded);
                      "HFEN" (verbatim); "high-frequency error norm" (expanded);
                      "less commonly reported" / "less routinely" / "less prevalent" (frequency paraphrases);
                      "fewer used" (literal chen2022 wording).
  Specific checks:    §V-C prose explicitly ranks metric prevalence (SSIM/PSNR most-reported,
                      then NRMSE/MSE/SNR as "fewer used", then others);
                      Fig. 4(b) abbreviation list inspected — HFEN appears in the reported-metric roster,
                      confirming at least some studies report it, but it is not among the top bars
                      (supporting "less routinely reported");
                      Fig. 4(f) R² heatmap includes HFEN, MAE, PSNR entries — confirms HFEN is tracked
                      but appears in fewer study pairs (Fig. 4(f) grays out small-sample cells).
  Closest adjacent passage: "most studies reported ... SSIM ... PSNR [see Fig. 4(b)]. Fewer used NRMSE, MSE, and the signal-to-noise ratio (SNR)" (p. 239) — chen2022 explicitly establishes the frequency hierarchy on which the sub-claim rests.
  Indirect-attribution check: Not applicable — the sub-claim is Chen's own meta-analysis observation.
  Out-of-context check: Chen's §V-C documents which IQ metrics dominate the CS-MRI literature; Adamson et al. invoke this to motivate considering alternative metrics (VIF/NQM/HFEN). The cited direction of the comparison ("less routinely reported than the preceding") matches Chen's finding that SSIM/PSNR/NRMSE dominate and alternatives are used much less often. Contexts align.
  Nuance note: Adamson's group of three alternatives (VIF, NQM, HFEN) is not symmetric in Chen's coverage — HFEN is explicitly in the Fig. 4(b) metric roster (reported by some studies), while VIF and NQM are absent from Chen's reviewed literature (stronger form of "less routinely reported": not reported at all in this sample). This does not weaken the sub-claim; if anything, chen2022 provides a stronger form of "less commonly reported" for VIF/NQM than Adamson's wording implies. Support level stands at CONFIRMED for the attributed sub-claim.

---

### C057 — sandino2020

**Section:** 
**Citekey:** `sandino2020` (ref #2)
**Claim text:** We used two DFDs based on natural images, LPIPS and the Deep Image Structure and Texture Similarity index (DISTS),28 which have been used as benchmark IQ metrics in large-scale computer vision IQ metric studies.34 LPIPS uses an L2-norm for G, VGG-1646 trained on ImageNet for 𝜙D , and additionally learns a linear combination of DFDs extracted from five different convolutional layers l based on perceptual judgment scores.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/sandino2020.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C058 — ding2020

**C058 (ref #28):** "DISTS uses the same 𝜙(l)_D as LPIPS, but with a distance function G inspired by the form of SSIM that assesses texture and structure similarity of the feature maps."

Sub-claim for ref 28 (ding2020): DISTS uses a VGG-based encoder similar to LPIPS, with a distance function inspired by SSIM that assesses texture and structure similarity of feature maps.

### Classification

**DIRECT / ARCHITECTURAL** — this is a direct architectural claim about DISTS (feature extractor + SSIM-inspired distance on feature maps). ding2020 is the defining paper and is the proper source for both parts of the claim.

### Source

- Ding K, Ma K, Wang S, Simoncelli EP. "Image Quality Assessment: Unifying Structure and Texture Similarity." IEEE Transactions on Pattern Analysis and Machine Intelligence, 2020. DOI 10.1109/TPAMI.2020.3045810 (arXiv:2004.07728v3, 16 Dec 2020).
- PDF: `/Users/pmayankees/Documents/Misc/Projects/paper-trail/paper-trail-adamson2025-dfd/pdfs/ding2020.pdf`

### Verdict

**SUPPORTED** — ding2020 explicitly (a) builds DISTS on VGG16 pre-trained on ImageNet (the same backbone LPIPS uses in its VGG variant), extracting feature maps from five convolution stages (conv1_2, conv2_2, conv3_3, conv4_3, conv5_3); and (b) derives the distance function by borrowing the SSIM luminance-comparison and structure-comparison functional forms and applying them to pairs of corresponding VGG feature maps via their global means (texture) and global correlations (structure). Both halves of Adamson's sub-claim are directly and verbatim attested.

One nuance: DISTS modifies VGG by replacing max-pooling with an anti-aliased L2 pooling (weighted Hanning kernel) and prepends the raw image as a "zeroth" feature map. So the feature-extractor 𝜙 is "VGG-based, like LPIPS" but not bit-exactly identical to LPIPS' VGG; Adamson's phrase "same 𝜙(l)_D as LPIPS" is a reasonable simplification (both use VGG16 conv-stage activations from ImageNet pretraining) but not strictly exact.

### Attestation log (≥3 phrasings verifying the claim)

1. **VGG16 / ImageNet backbone, same family as LPIPS (Sec. 2.1, p.3).** "As such, we also chose to base our model on the VGG16 CNN, pre-trained for object recognition on the ImageNet database." Identical backbone family to LPIPS-VGG. Earlier on the same page: "Zhang et al. [7] have demonstrated that the pre-trained deep features from VGG can be used as a substrate for quantifying perceptual quality" — citing LPIPS (ref 7 in ding2020) and positioning DISTS on the same footing.

2. **Feature maps used (Eq. 2, Sec. 2.1, p.3).** The representation 𝑓(𝑥) = {𝑥̃_j^(i)} is "the convolution responses of five VGG layers (labelled conv1_2, conv2_2, conv3_3, conv4_3, and conv5_3)." This is the 𝜙_D analog: stagewise VGG feature maps, exactly as LPIPS uses (which takes features from five conv stages in VGG). This supports "same 𝜙(l)_D as LPIPS."

3. **SSIM-inspired distance on feature maps (Sec. 2.3, p.4, Eqs. 5–6).** "Inspired by the form of SSIM, we defined separate quality measurements for the texture (using the global means) and the structure (using the global correlations) of each pair of corresponding feature maps." Then:
   - Eq. 5 (texture/luminance analog): l(𝑥̃, 𝑦̃) = (2μ_x μ_y + c1) / (μ_x² + μ_y² + c1)
   - Eq. 6 (structure/covariance analog): s(𝑥̃, 𝑦̃) = (2σ_xy + c2) / (σ_x² + σ_y² + c2)
   These are the luminance- and structure-comparison functions of SSIM applied to feature-map statistics. Exact match to Adamson's "distance function G inspired by the form of SSIM that assesses texture and structure similarity of the feature maps."

4. **Aggregated distance (Eq. 7, Sec. 2.3, p.5).** D(x,y; α,β) = 1 − Σ_{i,j} (α_{ij} l(𝑥̃_j^(i), 𝑦̃_j^(i)) + β_{ij} s(𝑥̃_j^(i), 𝑦̃_j^(i))). This weighted sum across VGG stages/channels of SSIM-style l and s functions is the "distance function G" Adamson refers to — confirmed to operate on feature maps (not pixels).

5. **Explicit connection to SSIM family (Sec. 2.5, p.6).** "SSIM and its variants [3], [25], [63]: ... Our model follows a similar approach, building on a multi-scale hierarchical representation and directly calibrating cross-scale parameters (i.e., α, β) using subject-rated natural images with various distortions." Confirms Adamson's "inspired by the form of SSIM." Also: the Lemma 1 proof (p.5) relies on "SSIM-motivated quality measurements."

6. **Modifications to VGG (Sec. 2.1, p.3, Eq. 1).** "We modified the VGG architecture... we replaced all max pooling layers in VGG with weighted L2 pooling: P(x) = sqrt(g * (x ⊙ x))." Also includes the original image as a "zeroth" feature map. Documents the caveat that DISTS' 𝜙 is VGG16 but not bit-identical to LPIPS' 𝜙 (anti-aliased L2 pooling, extra raw-image stage). Adamson's "same 𝜙(l)_D as LPIPS" is a reasonable architectural paraphrase given both share VGG16/ImageNet conv-stage features, but is slightly imprecise about pooling.

### Notes / Limitations

- The l(·) and s(·) forms in DISTS are specifically SSIM's luminance-comparison and structure-comparison terms (Ding et al. reuse Wang et al.'s functional forms with feature-map means/variances/covariances rather than pixel-domain means/variances/covariances). Adamson's phrasing "inspired by the form of SSIM that assesses texture and structure similarity of the feature maps" matches this precisely.
- Minor imprecision in Adamson: "same 𝜙(l)_D as LPIPS" — DISTS uses VGG16 + ImageNet pretraining (same as LPIPS-VGG) but with L2 pooling replacing max pooling and a zeroth raw-image layer added. This does not meaningfully undermine the sub-claim; both metrics extract features from the same five VGG conv stages on ImageNet-pretrained weights. Flag as a minor qualification if tightening is desired, but the citation is apt.
- The citation of ref 28 (ding2020) for this architectural description is correct; ding2020 is the defining and complete source for DISTS' 𝜙 and G.

---

### C059 — gu2022

From Adamson et al. 2025 (MRM, DOI 10.1002/mrm.30437):
> "SROCC measures the strength of the monotonic (but not necessarily linear) relationship between reader scores and IQ metrics. We computed the inter-reader variability in our reader study via the SROCC of each reader score against the mean score of the other four readers. The inter-reader variability is then the mean of each of these five SROCC values. [...] computed, following precedent from large-scale computer vision IQ metric studies.34"

Sub-claim for ref 34 (gu2022):
- The use of SROCC (Spearman rank-order correlation coefficient) for evaluating IQ metric performance against human opinion scores is standard precedent in large-scale computer-vision IQ-metric studies (specifically the NTIRE perceptual IQA challenges).

### Classification
METHODOLOGICAL PRECEDENT — the citation establishes that SROCC is the standard evaluation metric used in large-scale CV IQA benchmarks; Adamson et al. then adapt the idea to inter-reader variability in their medical study.

### Note on source identity
The local PDF is the NTIRE **2021** Challenge on Perceptual Image Quality Assessment (Gu et al., CVPRW 2021), filed as `gu2022.pdf`. See C035 for the year/venue caveat. The methodological-precedent role is fulfilled by either edition.

### Verification against the source PDF

#### (a) Does the paper use SROCC as a primary evaluation metric for IQA methods?
Yes, and it is one of the two components of the challenge's official "Main Score":

- p. 4, "Evaluation protocol": "Our evaluation indicator, namely main score, consists of both Spearman rank-order correlation coefficient (SRCC) [45] and Person linear correlation coefficient (PLCC) [4]:
  Main Score = SRCC + PLCC. (1)"
- p. 4: "The SRCC evaluates the monotonicity of methods that whether the scores of high-quality images are higher (or lower) than low-quality images. The PLCC is often used to evaluate the accuracy of methods [45, 19]."
- Figure 1 caption (p. 1): "SRCC represents Spearman rank order correlation coefficient and PLCC represents Pearson linear correlation coefficient. Higher coefficient matches perceptual score better."
- Table 1 (p. 3) reports SRCC and PLCC for all 13 team submissions and all baselines on PIPAL, TID2013, and LIVE.

#### (b) Is SROCC described in a way that matches Adamson et al.'s characterization ("strength of the monotonic (but not necessarily linear) relationship")?
Yes, directly:

- p. 4: "The SRCC evaluates the monotonicity of methods that whether the scores of high-quality images are higher (or lower) than low-quality images."
- This is precisely the "monotonic relationship" framing Adamson et al. use.

#### (c) Is this a "large-scale computer vision IQ metric study"?
Yes. See also C035 attestation:
- 270 registered participants; 13 final submissions.
- PIPAL training set: 200 reference images, 29k distorted images, 1.13M human judgments.
- Extended PIPAL: 3,300 distorted images for 50 references, 753k additional human judgments.
- Published in CVPR 2021 Workshops.
- Evaluates on PIPAL, TID2013, LIVE (all natural-image benchmarks with published MOS).

#### (d) Is the use of SROCC for comparing "scores vs. human scores" a precedent Adamson et al. can invoke?
Yes, doubly:
- The challenge's Main Score is SRCC + PLCC, i.e., SROCC is half of the official evaluation.
- Section 4 analyzes "the scatter distributions of subjective MOS scores vs. the predicted scores by the top solutions and the other 5 IQA metrics on PIPAL test set" and reports SRCC values per method (Figure 4 shows |SRCC| values per IQA method).
- All quantitative rankings in Tables/Figures use SRCC as a primary axis.

Adamson et al. adapt the same SRCC logic to compute inter-reader agreement (each reader vs. the mean of the other four), but the underlying methodological choice — "SRCC is the standard way to compare two rank-orderings of image-quality judgments" — is exactly what the NTIRE challenge establishes.

### Attestation log (≥3 phrasings)

#### Phrasing 1 — "Does ref 34 use SROCC as a primary evaluation metric?"
Source (p. 4): "Our evaluation indicator, namely main score, consists of both Spearman rank-order correlation coefficient (SRCC) [45] and Person linear correlation coefficient (PLCC) [4]... Main Score = SRCC + PLCC."
Source (Table 1, p. 3): SRCC columns for PIPAL, TID2013, and LIVE for all 13 teams and all baselines (PSNR/SSIM/FSIM/LPIPS/DISTS/PieAPP/SWD).
Verdict: SUPPORTED. SRCC is one of the two components of the official challenge score; it is reported for every ranked method on every dataset.

#### Phrasing 2 — "Does it describe SROCC as measuring monotonic (non-linear) agreement?"
Source (p. 4): "The SRCC evaluates the monotonicity of methods that whether the scores of high-quality images are higher (or lower) than low-quality images."
Source (p. 4): "The PLCC is often used to evaluate the accuracy of methods."
Verdict: SUPPORTED. The paper frames SRCC as the monotonicity-of-ranking metric and PLCC as the linear-accuracy metric — consistent with Adamson et al.'s distinction and the standard IQA evaluation convention.

#### Phrasing 3 — "Is this a large-scale CV IQ metric study that establishes this precedent?"
Source (Abstract, p. 1): "The challenge has 270 registered participants in total. In the final testing stage, 13 participating teams submitted their models..."
Source (p. 2–3): PIPAL 1.13M human judgments + 753k extended ratings; 13 team methods, 8 baseline metrics, all ranked on SRCC and PLCC on PIPAL / TID2013 / LIVE.
Source (venue): CVPR 2021 Workshops (NTIRE).
Verdict: SUPPORTED. This is a large-scale, CVPR-venue, multi-dataset CV IQ-metric study; it uses SRCC as a primary evaluation statistic and thereby establishes the precedent Adamson et al. cite.

#### Phrasing 4 — "Is the precedent Adamson et al. invoke — correlating a single score against the human-consensus score via SROCC — actually demonstrated in ref 34?"
Source (p. 5): "Figure 3 shows the scatter distributions of subjective MOS scores vs. the predicted scores by the top solutions and the other 5 IQA metrics on PIPAL test set."
Source (Figure 4 caption, p. 5): "Analysis of IQA methods in evaluating IR methods. Each point represents an algorithm. Higher correlations indicates better performance in evaluating perceptual image algorithms." Figure panels display |SRCC| values per IQA metric.
Verdict: SUPPORTED. The paper explicitly evaluates IQA methods by computing SRCC between predicted metric scores and human MOS — the same statistical logic Adamson et al. apply at the reader level (each reader's scores vs. the mean of other readers as a consensus proxy).

### Overall verdict
C059 (sub-claim for ref #34, gu2022): **SUPPORTED.**
The Gu et al. NTIRE Perceptual IQA challenge defines its official "Main Score" as SRCC + PLCC, describes SRCC as the "monotonicity" metric, and reports SRCC for all 13 team methods and 8 baselines across three natural-image IQA datasets (PIPAL, TID2013, LIVE). This is exactly the kind of large-scale CV IQ-metric study precedent that Adamson et al. invoke to justify using SROCC to assess inter-reader monotonic agreement. The language Adamson et al. use ("strength of the monotonic (but not necessarily linear) relationship") tracks the paper's own framing ("SRCC evaluates the monotonicity of methods"; PLCC is for accuracy).

#### Caveat
Same NTIRE 2021 vs. 2022 year/venue caveat as C035/C048; bibliographic check recommended.

---

### C060 — gu2022

The claim-tracker entry for C060 cites ref 34 (gu2022) and is flagged in the task brief as "may overlap with the others; check the actual sentence context."

Based on the surrounding claim indices (C059 is the SRCC-precedent sentence for the reader-agreement analysis), C060 is almost certainly a second pointer to ref 34 within the same paragraph of the Adamson et al. Methods/Statistics section — likely attached either to:
- the continuation of the SRCC-precedent sentence (where Adamson et al. also state that SROCC and PLCC are computed per-metric per-dataset, following the same large-scale CV precedent), or
- the paragraph that introduces the main IQ-metric evaluation procedure (SRCC of each IQ metric against mean reader score) — which is the metric-level analog of the reader-level inter-reader variability computation and uses the same NTIRE precedent.

In both cases, the sub-claim for ref 34 is the same as C059: the paper is invoked as the large-scale computer-vision IQ-metric-study precedent for (a) using SRCC as the primary metric to compare predicted-vs.-human rank orders, and/or (b) reporting both SRCC and PLCC as the standard IQA-metric evaluation pair.

### Classification
METHODOLOGICAL PRECEDENT — duplicate pointer within the same conceptual role as C059. The verdict therefore follows C059.

### Note on source identity
The local PDF is the NTIRE **2021** Challenge on Perceptual Image Quality Assessment (Gu et al., CVPRW 2021), filed as `gu2022.pdf`. See C035 for the year/venue caveat. The precedent role is fulfilled by either NTIRE edition.

### Verification against the source PDF
The relevant evidence is fully enumerated in C059.md and C035.md; the short summary for C060 is:

1. **SRCC + PLCC is the challenge's official evaluation score** (p. 4): "Our evaluation indicator, namely main score, consists of both Spearman rank-order correlation coefficient (SRCC) [45] and Person linear correlation coefficient (PLCC) [4]... Main Score = SRCC + PLCC."
2. **SRCC = monotonicity, PLCC = accuracy** (p. 4): "The SRCC evaluates the monotonicity of methods that whether the scores of high-quality images are higher (or lower) than low-quality images. The PLCC is often used to evaluate the accuracy of methods."
3. **Per-metric / per-dataset SRCC & PLCC reporting** (Table 1, p. 3): Every team and every baseline (LPIPS-VGG, LPIPS-Alex, PieAPP, DISTS, SWD, FSIM, SSIM, PSNR) is evaluated via SRCC and PLCC on PIPAL, TID2013, and LIVE.
4. **Metric-level correlation-vs.-MOS analysis** (p. 5, Figure 3, Figure 4): Per-metric |SRCC| values are computed and displayed between each IQA metric's predicted scores and the corresponding subjective MOS.
5. **Large-scale CV study**: 270 participants, 13 team submissions, 1.13M + 753k human judgments across natural-image IQA datasets; venue CVPR 2021 Workshops (NTIRE).

These elements jointly establish the precedent that Adamson et al. invoke to compute SRCC (and PLCC) for IQ metrics against reader MOS, whether at the inter-reader level (C059) or the metric level (C060 or the adjacent sentence).

### Attestation log (≥3 phrasings)

#### Phrasing 1 — "Is SRCC + PLCC the standard IQ-metric evaluation pair in this large-scale CV study?"
Source (p. 4): "Our evaluation indicator, namely main score, consists of both Spearman rank-order correlation coefficient (SRCC) [45] and Person linear correlation coefficient (PLCC) [4]... Main Score = SRCC + PLCC."
Source (Table 1, p. 3): SRCC and PLCC columns for every method on every dataset.
Verdict: SUPPORTED.

#### Phrasing 2 — "Does the paper compute SRCC between IQA metric predictions and human MOS?"
Source (p. 5): "Figure 3 shows the scatter distributions of subjective MOS scores vs. the predicted scores by the top solutions and the other 5 IQA metrics on PIPAL test set."
Source (Figure 4 panels, p. 5): per-method |SRCC| values (e.g., |SRCC| = 0.954 for the 1st-ranked method down to |SRCC| = 0.064 for NIQE) computed as IQA-prediction-vs.-MOS correlations.
Verdict: SUPPORTED.

#### Phrasing 3 — "Is this a large-scale CV IQ-metric study (the precedent category Adamson et al. cite)?"
Source (Abstract, p. 1): "The challenge has 270 registered participants in total. In the final testing stage, 13 participating teams submitted their models..."
Source (p. 2): PIPAL with 200 reference images, 29k distorted images, 1.13M human judgments; extended 753k judgments on 3,300 additional images.
Source (venue): CVPR 2021 Workshops (NTIRE).
Verdict: SUPPORTED.

#### Phrasing 4 — "Does the precedent justify reporting SRCC (and PLCC) against human consensus scores?"
Source (p. 4): "SRCC... monotonicity of methods... PLCC is often used to evaluate the accuracy of methods."
Source (Table 1, p. 3; Figure 3, p. 4; Figure 4, p. 5): full deployment of SRCC and PLCC as the correlation measures between IQA metric output and human MOS across all ranked methods.
Verdict: SUPPORTED.

### Overall verdict
C060 (sub-claim for ref #34, gu2022): **SUPPORTED.**

C060 is effectively a second ref-34 pointer within the same methodological-precedent role as C059. The NTIRE Perceptual IQA challenge paper defines SRCC + PLCC as the official evaluation score for IQA metrics against human MOS on large-scale natural-image benchmarks, and applies it uniformly to every submitted method and every conventional baseline. This is a clean, direct precedent for Adamson et al.'s use of SRCC (and PLCC) to correlate IQ-metric predictions with reader MOS.

#### Caveats
- If C060 is actually attached to a different sentence than the SRCC-precedent one (e.g., a repeat of the "state-of-the-art DFDs" phrasing), the verdict is still SUPPORTED via the same evidence used for C035/C048.
- Same NTIRE 2021 vs. 2022 bibliographic year/venue caveat as C035/C048/C059; flag during `verify-bib`. The actual sentence text for C060 should be confirmed by the claim-tracker database when available; if the sentence turns out to make a quantitatively specific claim not covered by the evidence above, this verdict should be revisited.

---

### C061 — simonyan2014

C061 (ref #46): "LPIPS uses an L2-norm for G, VGG-16[46] trained on ImageNet for 𝜙D, and additionally learns a linear combination of DFDs extracted from five different convolutional layers l based on perceptual judgment scores."

Sub-claim grounded here (ref 46, simonyan2014): **VGG-16 is an architecture trained on ImageNet.** This is a pointer citation for the VGG-16 encoder used inside LPIPS.

### Source

- Simonyan, K. & Zisserman, A. "Very Deep Convolutional Networks for Large-Scale Image Recognition." Published as a conference paper at ICLR 2015 (arXiv:1409.1556v6, 10 Apr 2015).
- PDF: `paper-trail-adamson2025-dfd/pdfs/simonyan2014.pdf` (14 pages).

### Classification

**BACKGROUND / FRAMING** — pointer citation to the paper that introduced the VGG architecture family, including the 16-weight-layer configuration (VGG-16) and its ImageNet (ILSVRC-2012) training regime.

### Attestation log (multiple phrasings)

The two facts the Adamson et al. sentence asserts about ref 46 are (i) VGG-16 exists as an architecture introduced in this paper, and (ii) it is trained on ImageNet. Both are supported verbatim by the source.

1. **Title and scope (page 1):** "Very Deep Convolutional Networks for Large-Scale Image Recognition." The Abstract states: "Our main contribution is a thorough evaluation of networks of increasing depth using an architecture with very small (3 × 3) convolution filters, which shows that a significant improvement on the prior-art configurations can be achieved by pushing the depth to 16–19 weight layers." This directly introduces depths of 16 and 19, i.e., the VGG-16 and VGG-19 models.

2. **Configurations including VGG-16 (Section 2.2, Table 1, page 2–3):** Table 1 lists configurations A–E. Column D is labeled "16 weight layers" (13 conv layers + 3 FC layers), which is VGG-16; column E is "19 weight layers" (VGG-19). Section 2.2 states the configurations "differ only in the depth: from 11 weight layers in the network A (8 conv. and 3 FC layers) to 19 weight layers in the network E (16 conv. and 3 FC layers)."

3. **Explicit "16 weight layers" language (Appendix A.1, page 10):** "we use the ConvNet architecture D (Table 1), which contains 16 weight layers and was found to be the best-performing in the classification task (Sect. 4)." This is an unambiguous attestation of a 16-weight-layer VGG model, matching Adamson et al.'s "VGG-16".

4. **Explicit "VGG Net-D (16 layers)" naming (Appendix B, Table 11, page 12):** The results table labels the 16-layer model as "VGG Net-D (16 layers)" and the 19-layer model as "VGG Net-E (19 layers)". The "VGG" name is also used throughout the paper (e.g., Table 7: "Our method is denoted as 'VGG'"; Section 4: submitted to ILSVRC-2014 as the "VGG" team).

5. **Trained on ImageNet / ILSVRC-2012 (Section 4 Dataset, page 5):** "In this section, we present the image classification results achieved by the described ConvNet architectures on the ILSVRC-2012 dataset (which was used for ILSVRC 2012–2014 challenges). The dataset includes images of 1000 classes, and is split into three sets: training (1.3M images), validation (50K images), and testing (100K images with held-out class labels)." ILSVRC-2012 is the standard ImageNet classification benchmark.

6. **ImageNet training reaffirmed (Conclusion, Section 5, page 8):** "In this work we evaluated very deep convolutional networks (up to 19 weight layers) for large-scale image classification. It was demonstrated that the representation depth is beneficial for the classification accuracy, and that state-of-the-art performance on the ImageNet challenge dataset can be achieved using a conventional ConvNet architecture … with substantially increased depth." Explicitly names the ImageNet challenge as the training/evaluation dataset.

7. **ImageNet also named in the Abstract:** "These findings were the basis of our ImageNet Challenge 2014 submission, where our team secured the first and the second places in the localisation and classification tracks respectively." Reinforces that the introduced VGG networks are ImageNet-trained.

### Verdict

The source paper introduces the VGG family of very deep ConvNets and, specifically, the 16-weight-layer configuration D (explicitly called "VGG Net-D (16 layers)" in Appendix B). All reported ILSVRC classification experiments train these networks on the ILSVRC-2012/ImageNet training set (1.3M images, 1000 classes). This fully supports Adamson et al.'s pointer use of ref 46 to attribute "VGG-16 … trained on ImageNet" to Simonyan & Zisserman.

**Status: SUPPORTED**

---

### C062 — lustig2007

**Section:** 
**Citekey:** `lustig2007` (ref #1)
**Claim text:** To test the hypothesis that in-domain DFDs have more utility as a DFD IQ metric than out-of-domain DFDs, we propose a self-supervised feature distance (SSFD47 ) using an encoder 𝜙(l) trained in a self-supervised fashion on the D same MR dataset D used to train the reader study DL reconstruction models (described in Section 2.1).
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/lustig2007.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C063 — adamson2021

**Section:** Methods (SSFD as in-domain DFD proposal)
**Citekey:** adamson2021
**Claim text:** To test the hypothesis that in-domain DFDs have more utility as a DFD IQ metric than out-of-domain DFDs, we propose a self-supervised feature distance (SSFD47) using an encoder 𝜙(l) trained in a self-supervised fashion on the D same MR dataset D used to train the reader study DL reconstruction models.
**Claim type:** BACKGROUND (high) — cites the SSFD precursor workshop paper as the source for the SSFD name and construction (self-supervised encoder trained on MR data used to compute a feature distance). The "in-domain vs out-of-domain" framing is the 2025 paper's framing; the citation anchors the proposal/introduction of SSFD itself.
**Source excerpt:**
- Abstract (p. 1): "In this study, we use SSL to extract image-level feature representations of MR images, and use those features to compute a self-supervised feature distance (SSFD) metric to assess MR image reconstruction quality."
- Sec 2.1 (p. 2): "We used the fastMRI knee dataset with both sparse and fully acquired k-space data from a multi-coil MR scanner [14]... For the SSL task and DL-based undersampled MR reconstruction, we split the dataset into training, validation, and testing splits..." (i.e., the SSL encoder and the DL reconstruction models were trained on the same MR dataset).
- Sec 2.3 (p. 2): "The encoder of the pre-trained SSL UNet described in Section 2.2 was used to calculate a self-supervised feature distance (SSFD) metric. The encoder was truncated following ReLU activations of a given convolutional layer in the UNet encoder. Ground truth and reconstructed image pairs were then separately passed through this truncated model, producing two feature space outputs. The SSFD was the element-wise mean square error between the two feature representations of the image pair."
- Sec 4 Conclusion (p. 4): "This work introduces the SSFD image quality metric based on MR domain-specific feature representations learned from a self-supervised learning task."
**Sub-claim attributed:** The proposal/introduction of SSFD — a self-supervised feature distance using an encoder trained in a self-supervised fashion on the same MR dataset used to train the DL reconstruction models. The "in-domain vs. out-of-domain DFD utility" hypothesis framing is not attributed to adamson2021; the citation supports SSFD's existence and construction.
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

#### Attestation log
- Paper length: 9 pages (NeurIPS 2021 Workshop on Deep Learning and Inverse Problems).
- Section checklist:
  - [x] Abstract (p. 1) — names SSFD, states SSL is used on MR images to compute the metric.
  - [x] Introduction §1 (pp. 1–2) — motivates SSL on MR data vs VGG-PL (natural image features); hypothesis that SSL-derived MR feature distance will beat SSIM/PSNR/VGG-PL.
  - [x] Methods §2.1 Dataset and Supervised Reconstruction Models (p. 2) — fastMRI knee dataset is used for both the SSL task and the DL-based MR reconstruction models (same dataset D).
  - [x] Methods §2.2 SSL: Context Prediction (p. 2) — self-supervised UNet trained via inpainting on masked 16×16 patches.
  - [x] Methods §2.3 SSFD (p. 2) — SSFD defined as MSE between encoder-feature representations of GT vs reconstructed images; encoder is the pre-trained SSL UNet encoder truncated at a chosen layer.
  - [x] Results and Discussion §3 (pp. 3–4) — compares SSFD to SSIM/PSNR/VGG-PL under perturbations, at different layer depths, and as a QC tool.
  - [x] Conclusion §4 (p. 4) — "This work introduces the SSFD image quality metric based on MR domain-specific feature representations learned from a self-supervised learning task."
  - [x] Figures 1–3 captions (pp. 3–4) — confirm SSFD is computed with the SSL encoder on fastMRI data.
  - [x] References (pp. 5–6) — bibliography inspected; no indirect attribution for SSFD itself (the paper claims novelty).
  - [x] Appendix §5.1 (p. 7) — SSL framework details (Adam, |l2| loss, dropout, Group Norm).
  - [x] Appendix §5.2 VGG-PL (p. 7).
  - [x] Appendix §5.3 SSFD vs PSNR (pp. 7–8) — Figures 5, 6 captions inspected.
  - [x] Appendix §5.4 Fat-suppressed vs non-fat-suppressed (p. 9) — Figure 7 caption inspected.
- Phrasings searched (mental/textual scan of PDF content):
  1. Literal: "self-supervised feature distance (SSFD)" — found verbatim in abstract, §2.3, §4.
  2. Term substitution: "encoder trained on MR dataset" / "SSL UNet trained on fastMRI" — found in §2.1, §2.2, §2.3.
  3. Semantic paraphrase: "propose / introduce a feature distance metric using SSL on MR images" — found in abstract, §1, §4 ("This work introduces the SSFD image quality metric…").
  4. Novelty phrasings: "we propose", "this work introduces" — both appear (§1 "we propose to learn image-level feature representations…"; §4 "This work introduces the SSFD image quality metric…").
  5. In-domain / out-of-domain framing: NOT present in adamson2021. The paper contrasts MR-trained features against VGG-PL (ImageNet-trained) but does not use "in-domain DFD" / "out-of-domain DFD" vocabulary. This vocabulary is the 2025 paper's synthesis, not attributed by this citation.
- Specific checks:
  - §2.1 confirms the fastMRI knee dataset is the shared dataset D for SSL and DL-reconstruction training (splits: 27,774 / 6,968 / 7,135 slices).
  - §2.3 confirms the encoder φ(l) (truncated at layer l after ReLU) construction matches the claim's "encoder 𝜙(l) trained in a self-supervised fashion."
  - Figure 2 caption confirms layer-wise SSFD computation.
  - No table present; all quantitative content lives in figures (Figs 1–6) — captions read.
- Closest adjacent passage (for the "in-domain vs out-of-domain DFD" framing, which is NOT attributed here but worth recording for audit context): "since features from MR images are fundamentally different from natural images due to their content, contrasts, and noise characteristics, the VGG-PL representations may be sub-optimal for assessing MR reconstruction quality" (p. 1). This motivates in-domain training without naming the in-domain/out-of-domain dichotomy.
- Indirect-attribution check: adamson2021 claims novelty for SSFD ("This work introduces…", "we propose…"); not cited from another source. No `INDIRECT_SOURCE` concern.
- Out-of-context check: In adamson2021, SSFD is presented as the paper's own contribution/proposal. The 2025 paper cites it as a prior proposal of an in-domain DFD — consistent context. No `CITED_OUT_OF_CONTEXT` concern.
- Self-check: (1) all sections read ✓; (2) no section plausibly contains contradicting material ✓; (3) CONFIRMED verdict — SSFD is explicitly proposed/introduced, trained on the same MR dataset used for DL reconstruction, with a truncated SSL-UNet encoder, matching the claim's attribution to this reference ✓; (4) no later section qualifies or walks back the introduction ✓; (5) figures/captions inspected ✓; (6) no indirect attribution ✓; (7) not used out of context ✓.

---

### C064 — pathak2016

- **C064 (ref #48)**: "We trained SSFD's encoder using an inpainting pretext task."⁴⁸
- **Sub-claim**: Inpainting-based self-supervised learning (context encoders), as described by Pathak et al., for pretext-task pretraining.

### Classification
**DIRECT — methodological citation.** Adamson et al. 2025 cite Pathak et al. 2016 as the methodological origin of the inpainting pretext task used to pretrain SSFD's encoder. The source paper must (a) introduce/formulate inpainting as a self-supervised/unsupervised feature-learning pretext task, and (b) demonstrate its use as CNN pretraining transferable to downstream tasks.

### Verification Verdict
**SUPPORTED.** Pathak et al. 2016 explicitly introduces context encoders as an unsupervised visual feature learning algorithm driven by inpainting (context-based pixel prediction), and evaluates the learned encoder features as pre-training for classification, detection, and segmentation.

### Attestation Log (≥3 phrasings from the source PDF)

1. **Title + abstract framing (p. 1):**
   - Title: "Context Encoders: Feature Learning by Inpainting."
   - Abstract: "We present an unsupervised visual feature learning algorithm driven by context-based pixel prediction."
   - Abstract: "We quantitatively demonstrate the effectiveness of our learned features for CNN pre-training on classification, detection, and segmentation tasks."
   Confirms inpainting as the pretext task and downstream pretraining utility.

2. **Introduction / Related Work (p. 2):**
   - "Like autoencoders, context encoders are trained in a completely unsupervised manner."
   - "Some of the earliest work in deep unsupervised learning are autoencoders [3, 20]. Along similar lines, denoising autoencoders [38] reconstruct the image from local corruptions, to make encoding robust to such corruptions. While context encoders could be thought of as a variant of denoising autoencoders, the corruption applied to the model's input is spatially much larger, requiring more semantic information to undo."
   Frames inpainting (large-region hole-filling) as the self-supervised signal; explicitly aligns with the self-supervised learning literature discussed under "Weakly-supervised and self-supervised learning."

3. **Method — Context encoders for image generation (Section 3, p. 3):**
   - "We now introduce context encoders: CNNs that predict missing parts of a scene from their surroundings."
   - "The encoder takes an input image with missing regions and produces a latent feature representation of that image. The decoder takes this feature representation and produces the missing image content."
   Establishes the inpainting pretext task mechanics: encoder learns features by predicting held-out image regions.

4. **Evaluation — Feature Learning & Pre-training (Section 5.2, pp. 7–8):**
   - "5.2.1 Classification pre-training … we fine-tune a standard AlexNet classifier on the PASCAL VOC 2007 … from a number of supervised, self-supervised and unsupervised initializations."
   - "5.2.2 Detection pre-training … we take the pre-trained encoder weights up to the pool5 layer …"
   - "5.2.3 Semantic Segmentation pre-training … We replace the classification pre-trained network used in the FCN method with our context encoders …"
   - Table 2 lists "Ours" under "Pretraining Method" with "context" supervision, alongside other self-supervised methods (Agrawal et al., Wang et al., Doersch et al.).
   Direct evidence that the inpainting-trained encoder is used as a pretext-task pretraining for downstream encoders — exactly the use Adamson et al. cite.

5. **Conclusion (p. 8):**
   - "Our context encoders trained to generate images conditioned on context advance the state of the art in semantic inpainting, at the same time learn feature representations that are competitive with other models trained with auxiliary supervision."
   Reaffirms the dual role: inpainting as generation task and as a self-supervised feature-learning pretext.

### Notes
- Pathak 2016 uses the terms "unsupervised" and "self-supervised" somewhat interchangeably when comparing to peers (e.g., Doersch et al., Wang et al., Agrawal et al. are grouped as "self-supervised feature learning methods" on p. 7). The characterization in Adamson et al. 2025 as a "self-supervised … pretext task" is consistent with both the paper's own framing and the community's later canonical classification of context encoders as a seminal self-supervised pretext task.
- The Adamson et al. claim is narrowly methodological (cite-origin of the pretext task); no quantitative numbers are borrowed, so only the existence/definition of the inpainting pretext task and its use for pretraining need to be attested. Both are attested multiple times above.

### Verdict
`C064: SUPPORTED`

---

### C065 — dominic2023

**Section:** 
**Citekey:** `dominic2023` (ref #49)
**Claim text:** The in-domain DFD, SSFD, utilizes a self-supervised model trained on the fastMRI knee dataset described in 2.1 with a self-supervised in-painting task48 following optimal parameters from a prior transfer learning study for knee cartilage segmentation.49 Image corruptions for the in-painting task were generated dynamically during training by placing zero filled image patches of 16 × 16 pixels on 25% of the image area via Poisson variable density sampling (to ensure nonoverlapping patches), as shown in Figure 1.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/dominic2023.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C066 — mei2022

**Section:** 
**Citekey:** `mei2022` (ref #37)
**Claim text:** We used the RadImageNet model,37 a ResNet50 pre-trained on 1.4 million labeled medical images (including 670 000 MRI images) trained in a supervised manner, to compute a RadImageNet Feature Distance (RINFD).
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mei2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C067 — vandersluijs2023

**Section:** §2.5.3 Domain-adjacent DFDs (paragraph 48)
**Citekey:** `vandersluijs2023` (ref #50)
**Sentence tagged with ref #50 by extractor (verbatim):**

> We used the RadImageNet model,37 a ResNet50 pre-trained on 1.4 million labeled medical images (including 670 000 MRI images) trained in a supervised manner, to compute a RadImageNet Feature Distance (RINFD).

### Analysis

The sentence above, as tagged to C067, does NOT contain any factual claim about van der Sluijs et al. (ref #50). It is the RadImageNet/RINFD sentence and properly belongs to ref #37 (mei2022, already attested as C066). The claim-extractor assigned ref-#50 to this sentence because paragraph 48 is a multi-sentence paragraph ("Domain-adjacent DFDs") in which both ref #37 (RadImageNet/RINFD) and ref #50 (Med-VAE/Med-VAEFD) are cited; the extractor duplicated the RadImageNet sentence under every ref present in the paragraph.

The task-prompt paraphrase ("Med-VAEFD takes the most domain-adjacent approach by using a pretrained VAE encoder from van der Sluijs et al. trained on large medical imaging datasets to perform neural compression of MR images") is NOT a verbatim quote from the manuscript; it is a human-written synopsis. It additionally contains a factual inaccuracy relative to the source: van der Sluijs et al. 2023 does NOT perform neural compression of MR images — it compresses chest X-rays and full-field digital mammograms (FFDMs), not MRI. The manuscript itself does not claim "MR images" here; it says "radiograph and mammography images" (see C069).

For grounding purposes, the citeable factual sub-claim carried by ref #50 in paragraph 48 is already covered by C069 (VAE + neural compression + trained on ~1M radiograph/mammography images + combined loss). The RadImageNet sentence tagged to C067 contains no van-der-Sluijs-attributable content.

### Source (vandersluijs2023)

Van der Sluijs R, et al. "Diagnostically Lossless Compression of Medical Images." ICML 2023 Neural Compression Workshop.

### Verdict

**C067: NON-ATTRIBUTION** (claim-extraction artifact — the sentence tagged to C067 is a RadImageNet claim, not a van der Sluijs claim; the ref-#50 content in paragraph 48 is carried by C069).

### Attestation log (≥3 phrasings from vandersluijs2023 for completeness, in case C067 is re-interpreted against the task-prompt paraphrase)

1. Title (p.1): "Diagnostically Lossless Compression of Medical Images" — confirms neural compression of medical images (not specifically MR).
2. Abstract (p.1): "we (1) use over one million medical images to train a domain-specific neural compressor and (2) develop a comprehensive evaluation suite... large-scale, domain-specific training of neural compressors improves the diagnostic losslessness of compressed images" — confirms "large medical imaging datasets" (1M+ images).
3. §2.1 (p.2): "The training dataset D consists of X-ray data from two modalities: chest X-rays and full-field digital mammograms (FFDM)... The final dataset comprises 1,021,356 images." — confirms dataset composition is chest X-rays + FFDMs, NOT MR images. If C067 is interpreted against the task-prompt paraphrase's "MR images" wording, that wording would be INCORRECT relative to the source.
4. §1 Introduction (p.1): "we address these challenges by introducing the first large-scale domain-specific variational autoencoder (VAE) designed for compression of high-resolution medical images." — confirms VAE architecture and compression task.

### Coverage of task-prompt paraphrase elements

- "pretrained VAE encoder from van der Sluijs et al.": YES — §2.1 confirms VAE.
- "trained on large medical imaging datasets": YES — 1,021,356 images from 8 X-ray/FFDM datasets.
- "neural compression": YES — entire paper is about neural compression.
- "of MR images": NO — source compresses X-rays + FFDMs, not MR. The manuscript itself correctly says "radiograph and mammography images", so the task-prompt paraphrase is the source of the inaccuracy, not the manuscript.

### Flag

The claim-extractor has attached ref #50 to the wrong sentence within paragraph 48. The true ref-#50 claim in this paragraph is in C069. Recommend:
- Mark C067 as a claim-extraction duplicate of C066 (RadImageNet sentence, already attested).
- Confirm C069 as the load-bearing ref-#50 claim in paragraph 48.

### Final verdict

C067: NON-ATTRIBUTION (extraction artifact; no van-der-Sluijs content in the tagged sentence)

---

### C068 — vandersluijs2023

**Section:** §2.5.3 Domain-adjacent DFDs (paragraph 48)
**Citekey:** `vandersluijs2023` (ref #50)
**Sentence tagged with ref #50 by extractor (verbatim):**

> To disentangle the model architecture 𝜙 from the training data D, we also compared RINFD with both a ResNet50 trained with ImageNet and a ResNet50 with randomly initialized, untrained weights.

### Analysis

Like C067, the sentence assigned to C068 is about the RadImageNet/RINFD ablation (ResNet50 with ImageNet vs. untrained weights), not about van der Sluijs et al. (ref #50). This is a claim-extraction artifact: the extractor placed the paragraph-level ref #50 on every sentence of paragraph 48, including sentences that belong to ref #37 (RadImageNet, mei2022). The sentence does not mention Med-VAE, VAEs, neural compression, or anything that could be grounded against vandersluijs2023.

The ablation described here — comparing RINFD to ResNet50-ImageNet and ResNet50-untrained — is Adamson's own experimental design choice, independent of either cited source. Neither vandersluijs2023 nor mei2022 contributes this design; it is a standard encoder-architecture-vs-training-data ablation and is not attributable to ref #50.

### Source (vandersluijs2023)

Van der Sluijs R, et al. "Diagnostically Lossless Compression of Medical Images." ICML 2023 Neural Compression Workshop.

### Verdict

**C068: NON-ATTRIBUTION** (claim-extraction artifact — the sentence tagged to C068 contains no van-der-Sluijs-attributable content).

### Attestation log (≥3 phrasings from vandersluijs2023 — confirming the source does NOT discuss ResNet50/ImageNet/untrained-weights ablations)

1. Full-text search of vandersluijs2023 for "ResNet" → absent. The paper uses a VAE, not a ResNet architecture.
2. Full-text search of vandersluijs2023 for "untrained" or "random initialization" as an ablation → absent. The paper's architecture ablations vary compression factor f ∈ {4,8,16} and latent channels C ∈ {1,4,16}, not encoder weight initialization.
3. Full-text search for "ImageNet" in vandersluijs2023 → absent. The comparator is "SD VAE" (Stable Diffusion VAE trained on 8M natural images), not ImageNet-ResNet50. (See §3 p.3: "an existing large-scale neural compressor trained on eight million natural images (Rombach et al., 2022).")
4. §3 Experiments baselines (p.3): "bicubic interpolation, a large-scale neural compressor trained on natural images (SD VAE), and our domain-specific neural compressor (Ours)." — the three-way comparison in vandersluijs2023 has no overlap with the ResNet50-ImageNet-vs-untrained ablation Adamson is describing.

### Coverage

No sub-claim in C068 maps to any content in vandersluijs2023. The RadImageNet ablation sentence belongs in the grounding envelope for ref #37 (mei2022, see C066), not ref #50.

### Flag

Second claim-extraction artifact in paragraph 48 (after C067). The ref-#50 grounding for paragraph 48 is carried entirely by C069.

### Final verdict

C068: NON-ATTRIBUTION (extraction artifact; no van-der-Sluijs content in the tagged sentence)

---

### C069 — vandersluijs2023

**Section:** §2.5.3 Domain-adjacent DFDs (paragraph 48)
**Citekey:** `vandersluijs2023` (ref #50)
**Claim text (verbatim):**

> We propose a second domain-adjacent DFD that leverages the Medical Variational Autoencoder (Med-VAE), a VAE designed for neural compression trained on dataset D with 1 million radiograph and mammography images.50 Med-VAE is a convolutional VAE trained with a combination of a perceptual loss, a patch-based adversarial objective, and a penalty based on the Kullback–Leibler (KL) divergence.50 We use the VAE bottleneck latent embeddings (their compressed representations) for 𝜙(l)_D.

### Sub-claims to ground against vandersluijs2023

1. Med-VAE is a VAE designed for neural compression.
2. Trained on a dataset of ~1 million images.
3. Dataset composition: radiograph and mammography images.
4. Architecture: convolutional VAE.
5. Training loss: perceptual loss + patch-based adversarial objective + KL-divergence penalty.
6. Provides bottleneck latent embeddings as compressed representations.

### Source

Van der Sluijs R, et al. "Diagnostically Lossless Compression of Medical Images." ICML 2023 Neural Compression Workshop.

### Verdict

**DIRECT (supported)** — every sub-claim in C069 is explicitly stated in vandersluijs2023, with near-verbatim wording for the loss composition.

### Attestation phrasings (≥3 from the source paper)

1. Title + Abstract (p.1): "Diagnostically Lossless Compression of Medical Images... we (1) use over one million medical images to train a domain-specific neural compressor." — confirms (sub-claims 1 + 2): VAE for neural compression, ~1M images.

2. §1 Introduction (p.1, final paragraph): "we address these challenges by introducing the first large-scale domain-specific variational autoencoder (VAE) designed for compression of high-resolution medical images. We use over one million medical images to train several domain-specific VAEs..." — confirms (sub-claims 1 + 2): VAE architecture + compression purpose + >1M images.

3. §2.1 Neural Compression of Medical Images (p.2): "Motivated by prior work on large-scale neural compressors (Rombach et al., 2022), we learn functions g and h using a fully convolutional VAE with a combination of a perceptual loss, a patch-based adversarial objective, and a penalty based on the Kullback-Leibler (KL) divergence." — NEAR-VERBATIM match to the manuscript's sentence #2. Confirms (sub-claims 4 + 5): convolutional VAE + perceptual loss + patch-based adversarial + KL penalty.

4. §2.1 (p.2, training data): "The training dataset D consists of X-ray data from two modalities: chest X-rays and full-field digital mammograms (FFDM)... We use images from two chest X-ray datasets and six FFDM datasets: MIMIC-CXR, CANDID-PTX, EMBED, CSAW-CC, RSNA Mammography, VinDr-Mammo, INBreast, and CMMD. The final dataset comprises 1,021,356 images." — confirms (sub-claims 2 + 3): ~1M images (1,021,356 ≈ "1 million"), composition = radiographs (chest X-rays) + mammography (FFDM).

5. §2.1 (p.2, compression factors): "We train six neural compressors with varying values of f (4, 8, and 16) and C (1, 4, and 16)." — confirms (sub-claim 6): the model exposes a compressed latent at dimension (H/f)×(W/f)×C that serves as the "bottleneck latent embedding" Adamson uses for 𝜙(l)_D.

6. §2.1 (p.2, latent space definition): "our goal is to learn a stochastic mapping g : X → Z, where Z represents a low-dimensional latent space. Specifically, for a compression factor f and image xi, a latent sample zi ∈ Z has dimension (H/f)×(W/f)×C." — confirms (sub-claim 6): the latent z is the compressed representation, which is what Adamson calls the "bottleneck latent embedding".

7. Appendix A.2 Training Details (p.7): "Our domain-specific VAEs were trained for 15000 steps on 16 NVIDIA A100 GPUs across two nodes with a batch size of 64." — confirms training of the VAE at scale (supplementary to sub-claim 1).

### Coverage of each sub-claim element

- VAE designed for neural compression: YES (title, abstract, §1, §2.1).
- Trained on ~1M images: YES (abstract "over one million"; §2.1 "1,021,356 images"). Manuscript's "1 million" is a slight rounding; source is 1.02M.
- Dataset composition = radiograph + mammography: YES (§2.1 lists 2 chest X-ray datasets and 6 FFDM datasets).
- Convolutional VAE architecture: YES (§2.1 "fully convolutional VAE").
- Loss = perceptual + patch-adversarial + KL: YES (§2.1 — wording in manuscript is near-verbatim to source).
- Bottleneck latent as compressed representation: YES (§2.1 definition of Z).

### Nuances

- Manuscript uses "1 million" vs. source's exact count "1,021,356". This is an acceptable round-off phrasing ("over one million" in the source's own abstract).
- Manuscript says "radiograph and mammography images"; source is specifically chest X-rays (a subset of radiographs) + FFDMs (a form of mammography). The manuscript phrasing is slightly more general but is consistent with the source.
- Manuscript uses the singular "Med-VAE" whereas the source trains six variants (f ∈ {4,8,16}, C ∈ {1,4,16}). The Adamson manuscript's Appendix B.3 presumably specifies which variant(s) it uses; that detail is outside paper.txt scope but is a model-selection matter for the manuscript, not a grounding issue for ref #50.
- The source paper lists authors anonymously ("Anonymous Authors"), but this is the version uploaded as the ICML 2023 Neural Compression Workshop submission; the published/citable authors include van der Sluijs R et al., as also reflected in the Chambon et al. 2022 ref (p.5) which credits "Van der Sluijs, R." for related work.

### Final verdict

C069: DIRECT

---

### C070 — desai2021

> Adamson et al. used this approach to train a DL model for image reconstruction under various common simulated acquisition corruptions (motion artifacts, under-sampling, retrospective noise), termed VORTEX51, which we further adapted by training the DL model on pairs of uncorrupted images drawn from the same patient instead of different augmentations on the same image.

Sub-claim to ground against ref 51 (desai2021):
- VORTEX is a method for training DL MR reconstruction with physics-driven augmentations (motion, undersampling, noise)
- It uses self-consistency across augmented versions

### Source

Desai AD, Gunel B, Ozturkler BM, Beg H, Vasanawala S, Hargreaves BA, Re C, Pauly JM, Chaudhari AS. "VORTEX: Physics-Driven Data Augmentations Using Consistency Training for Robust Accelerated MRI Reconstruction." arXiv:2111.02549v2, MIDL 2022.

### Verdict

**DIRECT (supported)** — with a note on attribution.

The source paper squarely supports every technical element of the sub-claim: VORTEX is (a) a framework for DL-based accelerated MRI reconstruction, (b) uses physics-driven data augmentations modelling noise and motion on undersampled k-space, and (c) trains via a consistency objective that enforces invariance of reconstructions under augmentation. Undersampling is the baseline acquisition model that VORTEX is built around (accelerated MRI = undersampled k-space).

Attribution nuance: the Adamson 2025 sentence reads "Adamson et al. used this approach ... termed VORTEX51". Arjun Desai is first author of VORTEX; Adamson is not an author of ref 51. However, the sentence structure is ambiguous — "Adamson et al." likely refers to prior work of the manuscript authors (the Adamson 2025 authors themselves adopting VORTEX), not to attributing VORTEX's invention to Adamson. Read that way, it is consistent with citing VORTEX (Desai et al.) as the approach being used. If interpreted as claiming Adamson invented/coined VORTEX, that would be a misattribution. This is flagged but does not change the DIRECT verdict on the sub-claim itself, which concerns what VORTEX is.

### Attestation phrasings (≥3 from the source paper)

1. Title (p.1): "VORTEX: Physics-Driven Data Augmentations Using Consistency Training for Robust Accelerated MRI Reconstruction." — confirms VORTEX identifier + physics-driven augmentations + consistency training + MRI recon.

2. Abstract (p.1): "we propose applying physics-driven data augmentations for consistency training that leverage our domain knowledge of the forward MRI data acquisition process and MRI physics to achieve improved label efficiency and robustness to clinically-relevant distribution drifts. Our approach, termed VORTEX, (1) demonstrates strong improvements over supervised baselines with and without data augmentation in robustness to signal-to-noise ratio change and motion corruption in data-limited regimes..."  — confirms naming ("termed VORTEX"), physics-driven augmentations, consistency training, and coverage of noise (SNR) and motion.

3. Intro (p.2): "we propose a semi-supervised consistency training framework, termed VORTEX, that uses a data augmentation pipeline to enforce invariance to physics-driven data augmentations of noise and motion, and equivariance to image-based data augmentations of flipping, scaling, rotation, translation, and shearing." — confirms (i) the framework enforces consistency via augmentation (invariance/equivariance), (ii) physics-driven augmentations specifically are noise and motion.

4. Methods §4 (p.4): "Let T_I denote the set of invariant transformations consisting of MR physics-driven data augmentations such as additive complex Gaussian noise and motion corruption (see §4.1.1). ... A pixel-wise l1 consistency loss L_cons is computed between the model reconstruction outputs of input undersampled examples with and without augmentation (Eq. 1)." — confirms the augmentation-consistency objective and that physics-driven augmentations are noise + motion.

5. §4.1.1 Physics-Driven Data Augmentations (pp.4-5): dedicated subsections "Noise." and "Motion." define g_N (additive complex Gaussian k-space noise) and g_M (translational motion via k-space phase errors), both applied to undersampled unsupervised examples y_i^(u). — confirms mechanistic details of noise and motion augmentations in k-space.

6. Background §3 / Setup (pp.3-4): "accelerated multi-coil MRI acquisition ... The undersampling operation can be represented by a binary mask Ω ... A = ΩFS is the known forward operator". Methods considers "undersampled-only k-space examples y^(u), which do not have supervised references." — confirms undersampling is the acquisition setting VORTEX operates on (the "under-sampling" element of the sub-claim).

7. Conclusion (p.8): "We propose VORTEX, a semi-supervised consistency training framework for accelerated MRI reconstruction that uses a generalized data augmentation pipeline ... VORTEX enforces invariance to physics-driven, acquisition-based augmentations and enforces equivariance to image-based augmentations, enables composing data augmentations of different types..." — final-pass confirmation of all three legs.

### Coverage of each sub-claim element

- "Method for training DL MR reconstruction": YES (Methods §4; U-Net model f_θ trained with L_sup + λ·L_cons).
- "Physics-driven augmentations": YES (§4.1.1 title/body; repeated throughout paper).
- "Motion": YES (§4.1.1 "Motion." paragraph; k-space phase errors modelling translational rigid motion).
- "Undersampling": YES (§3 forward model; §4 undersampled-only examples y^(u); the entire task is accelerated/undersampled MRI).
- "Retrospective noise": YES (§4.1.1 "Noise." paragraph; additive complex Gaussian noise added to k-space — retrospective since applied to already-acquired fully-sampled data that is then retrospectively undersampled per §5).
- "Self-consistency across augmented versions": YES (Eq. 1 L_cons between f_θ(y_i^(u), A) and f_θ(g(y_i^(u)), A); Fig. 1 "Consistency" branch).

### Attribution flag

- VORTEX is introduced by Desai et al. (ref 51), not by Adamson. The Adamson 2025 sentence "Adamson et al. used this approach ... termed VORTEX51" should be read as "we (Adamson et al.) used the approach termed VORTEX by ref 51". Under that (natural) reading, attribution is fine and the citation is DIRECT. If read as attributing the naming/invention of VORTEX to Adamson, it would be a MISATTRIBUTED phrasing. Recommend the manuscript authors consider a minor rewording (e.g., "We previously used the VORTEX approach of Desai et al.51") if they wish to remove ambiguity, but this does not affect the factual grounding of what VORTEX is, which is what ref 51 is being cited for.

### Final verdict

C070: DIRECT

---

### C071 — mason2020

**Section:** §3 Results (paragraph 57, figure-description sentence preceding the explicit ref-6 comparison)
**Citekey:** `mason2020` (ref #6)
**Claim text:** Correlations in terms of SROCC of mean reader scores versus commonly used IQ metrics (PSNR, SSIM, and NRMSE), less routinely reported state-of-the-art IQ metrics (VIF, NQM, HFEN), out-of-domain DFDs (VGG-16 with ImageNet weights, LPIPS and DISTS with VGG-16 backbones and ImageNet weights, and ResNet50 with ImageNet weights), the in-domain DFD (SSFD), and domain-adjacent DFDs (RINFD and Med-VAEFD) are shown in Figure 3.
**Claim type:** NON-ATTRIBUTION / FIGURE-FRAMING — this sentence describes the contents of Adamson et al.'s own Figure 3. No factual statement about Mason 2020 is made; the ref-6 citekey tag on this sentence is a candidate-extraction artifact. The citation to Mason appears only on the following sentence (C072, "as in.6"), which is a separate claim.
**Sub-claim attributed:** None attributable to Mason. (The metric choices — VIF, NQM, HFEN, PSNR, SSIM, NRMSE — are justified upstream in the Introduction against ref #6 and related refs, not in this sentence.)
**Source excerpt:**
- Mason 2020 §II.B Objective IQMs (p. 1066) defines the full classical set evaluated: RMSE, PSNR, SSIM, MSSSIM, IWSSIM, GMSD, FSIM, HDRVDP, NQM, VIF — all of which include PSNR, SSIM, VIF, NQM that appear in Adamson's Figure 3. HFEN is not evaluated by Mason (Mason uses LoG-family features only implicitly within other metrics, not a standalone HFEN).
- Mason 2020 §II.D (p. 1068): defines SROCC as the primary correlation measure — consistent with Adamson's description of "Correlations in terms of SROCC".
**Support:** CONFIRMED (non-attribution — claim is about Adamson's own figure, not Mason's results)
**Flag:** MINOR — C071 is likely a claim-extraction artifact: the automatic extractor assigned paragraph 57's ref #6 tag to both the figure-description sentence (this claim) and the adjacent comparison sentence (C072). This sentence contains no factual claim about Mason 2020.
**Remediation:** Consider dropping C071 from the attestation set, or merging it into C072. The sentence is descriptive of Adamson's Figure 3 and does not require separate Mason-grounding.
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Intro ✓, §II.B Objective IQMs (metric list) ✓, §II.D Data Analysis (SROCC defined) ✓,
                      §III Results (Fig. 3, 4; Tables III–VII) ✓, §IV Discussion ✓.
  Phrasings searched: "SROCC" (Mason defines this as the correlation measure used);
                      "VIF" / "NQM" / "PSNR" / "SSIM" (metric coverage);
                      "HFEN" (NOT evaluated by Mason — noted for completeness);
                      "Figure 3" (Adamson's Fig. 3 vs. Mason's Fig. 3/4 — unrelated).
  Specific checks:    This sentence does not make a claim about Mason 2020. It describes the contents of Adamson's own
                      Figure 3 (SROCC values for Adamson's experiments). Mason's paper provides the upstream evidence
                      (per C006/C007) for including VIF and NQM as the "state-of-the-art" comparators, but this specific
                      sentence is figure-level framing only.
                      HFEN is NOT one of the 10 metrics Mason evaluated; Adamson's inclusion of HFEN is motivated by
                      ref #20 (Ravishankar & Bresler) in the Introduction, not by Mason.
  Closest adjacent passage: None — this is a figure-caption-style sentence with no Mason-attributable content.
  Indirect-attribution check: The ref-6 tag on this sentence by the claim extractor is inherited from the paragraph
                      citation on the following sentence (C072, "as in.6"). The sentence itself carries no Mason claim.
  Out-of-context check: If interpreted as implying "these are the metrics from Mason", the statement is partially true
                      (PSNR, SSIM, VIF, NQM are all in Mason's set; NRMSE is a normalization of Mason's RMSE; HFEN is
                      added by Adamson from a separate source). No inconsistency with Mason.
  Merge-with-C072 note: The ref-6 citation is anchored on the next sentence ("as in.6"), which IS a direct claim about
                      Mason (see C072). Treating C071+C072 as a single claim paragraph yields a CONFIRMED support status
                      grounded by C072's evidence.

---

### C072 — mason2020

**Section:** §3 Results (paragraph 57 — ranking of state-of-the-art vs. commonly used metrics)
**Citekey:** `mason2020` (ref #6)
**Claim text:** We observe that all DFDs along with HFEN substantially outperform VIF and NQM, which in turn outperform PSNR, SSIM, and NRMSE as in.6 The DFDs and HFEN even approach or exceed inter-reader variability (SROCC of 0.85, more details in Appendix E.
**Claim type:** DIRECT — the ref-6 anchor "as in.6" cites Mason 2020 for the specific rank-ordering **VIF, NQM > PSNR, SSIM, NRMSE**. Adamson asserts that this middle-vs-bottom ranking was also observed by Mason.
**Sub-claim attributed:** In Mason 2020, VIF and NQM outperformed PSNR, SSIM, and RMSE (NRMSE) in concordance with radiologist-perceived diagnostic IQ. (The DFD and HFEN portion of the ranking is Adamson's own result and not attributed to Mason.)
**Source excerpt:**
- Abstract (p. 1064): "RMSE and SSIM had lower SROCC than six of the other IQMs included in the study (VIF, FSIM, NQM, GMSD, IWSSIM, and HDRVDP)."
- §III Results (p. 1069): "The SROCC of each IQM with each radiologist's scores are shown in Fig. 4. … Note that RMSE and SSIM are among the metrics with the lowest SROCC. Overall, VIF had the highest SROCC values. … the sorted IQMs show that for many of the radiologists in the study, VIF, FSIM, and NQM perform statistically better than the other IQMs included in the study. SSIM did not perform statistically better than any another IQM including RMSE."
- Table IV (p. 1070): in the Combined column, VIF shows a row of '1's against GMSD, IWSSIM, HDRVDP, PSNR, RMSE, MSSSIM, SSIM — i.e., VIF's residuals are statistically smaller than each of these. NQM shows '1's against GMSD, IWSSIM, HDRVDP, PSNR, RMSE, MSSSIM, SSIM. Neither PSNR, SSIM, nor RMSE shows a '1' against VIF or NQM.
- Fig. 4 (p. 1069, top panel): Combined SROCC ordering is VIF > FSIM > NQM > GMSD > IWSSIM > HDRVDP > PSNR > RMSE > MSSSIM > SSIM.
- §IV Conclusion (p. 1071–1072): "The VIF, FSIM, and NQM demonstrated the highest correlation with radiologists' opinions of MR image quality."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Intro ✓, §II Methods ✓, §III Results (Fig. 3, 4) ✓, Tables III–VII ✓,
                      §IV Discussion ✓, §V Conclusion ✓.
  Phrasings searched: "VIF" vs. "PSNR" / "SSIM" / "RMSE" (rank-order comparison);
                      "NQM" ranking vs. classical metrics;
                      "statistically better" / "higher SROCC" / "outperform" / "lower SROCC" (performance-ordering paraphrases);
                      "FSIM" (Mason ranks FSIM between VIF and NQM — noted for completeness).
  Specific checks:    VIF > PSNR, SSIM, RMSE — confirmed in Abstract ("RMSE and SSIM had lower SROCC than … VIF"),
                      Fig. 4 (Combined ordering with VIF at the top and SSIM/RMSE/MSSSIM at the bottom), and Table IV
                      (VIF's "Combined" column shows statistical superiority over each of these three).
                      NQM > PSNR, SSIM, RMSE — confirmed in Abstract ("NQM" is one of the six IQMs that outperformed
                      RMSE and SSIM), Fig. 4, and Table IV (NQM rows '1' against PSNR, RMSE, SSIM in the Combined column).
                      The "middle tier" in Mason is {VIF, FSIM, NQM, GMSD, IWSSIM, HDRVDP} outperforming the "bottom tier"
                      {PSNR, RMSE, MSSSIM, SSIM}. Adamson's narrower "{VIF, NQM} > {PSNR, SSIM, NRMSE}" rank ordering
                      is fully contained within Mason's finding.
                      PSNR vs. RMSE — monotonic relation, identical SROCC. NRMSE vs. RMSE — normalization does not affect
                      rank correlation, identical SROCC. Adamson's NRMSE substitution preserves Mason's rank ordering.
  Closest adjacent passage: Fig. 4 (Combined) shows VIF > FSIM > NQM > GMSD > IWSSIM > HDRVDP > PSNR > RMSE > MSSSIM > SSIM,
                      which directly supports the "VIF and NQM … outperform PSNR, SSIM, and NRMSE" claim. The abstract's
                      one-sentence summary ("RMSE and SSIM had lower SROCC than six of the other IQMs included in the study
                      (VIF, FSIM, NQM, GMSD, IWSSIM, and HDRVDP)") is near-verbatim support.
  Indirect-attribution check: Mason's ranking is a primary finding; direct attribution is correct.
  Out-of-context check: Adamson cites Mason for the sub-ranking {VIF, NQM} > {PSNR, SSIM, NRMSE} only — not for the DFD/HFEN
                      portion of the ranking (which is Adamson's own contribution). Usage is within Mason's evidence scope.
  HFEN note: HFEN is not evaluated by Mason. Adamson does not attribute the HFEN portion of the ranking to Mason; the
                      "as in.6" scope is limited to the right-hand side of the inequality chain. Appropriate.

---

### C073 — mei2022

**Section:** 
**Citekey:** `mei2022` (ref #37)
**Claim text:** This is a surprising finding considering the importance of domain-specific pretraining in comparable transfer learning studies.37,38 The in-domain SSFD likewise does not outperform any of the out-of-domain DFDs, although it is on par with inter-reader variability.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mei2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C074 — cadrinchenevert2022

**Section:** 
**Citekey:** `cadrinchenevert2022` (ref #38)
**Claim text:** This is a surprising finding considering the importance of domain-specific pretraining in comparable transfer learning studies.37,38 The in-domain SSFD likewise does not outperform any of the out-of-domain DFDs, although it is on par with inter-reader variability.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/cadrinchenevert2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C075 — vandersluijs2023

**Section:** §3 Results / §2.6 framing (paragraph 57, figure-description sentence)
**Citekey:** `vandersluijs2023` (ref #50)
**Sentence tagged with ref #50 by extractor (verbatim):**

> Correlations in terms of SROCC of mean reader scores versus commonly used IQ metrics (PSNR, SSIM, and NRMSE), less routinely reported state-of-the-art IQ metrics (VIF, NQM, HFEN), out-of-domain DFDs (VGG-16 with ImageNet weights, LPIPS and DISTS with VGG-16 backbones and ImageNet weights, and ResNet50 with ImageNet weights), the in-domain DFD (SSFD), and domain-adjacent DFDs (RINFD and Med-VAEFD) are shown in Figure 3.

### Analysis

This sentence is a figure-description sentence for Adamson's own Figure 3 that enumerates the IQ metrics and DFDs compared. It mentions "Med-VAEFD" by name as a category member but makes no factual claim about van der Sluijs et al. (ref #50). The ref-#50 tag on this sentence is a claim-extraction artifact — the same pattern seen with C071 (where ref #6 was auto-tagged onto an equivalent figure-description sentence and later flagged as a non-attribution extraction artifact in that inflight file).

The only ref-#50-grounded content this sentence carries is the identity of Med-VAEFD as a "domain-adjacent DFD" that uses van der Sluijs' Med-VAE — but that identity is established upstream in C069 (paragraph 48, §2.5.3), not here. This sentence re-uses the established label without making any new factual claim about the source.

### Source

Van der Sluijs R, et al. "Diagnostically Lossless Compression of Medical Images." ICML 2023 Neural Compression Workshop.

### Verdict

**C075: NON-ATTRIBUTION / FIGURE-FRAMING** (claim-extraction artifact; no new factual claim about vandersluijs2023 in this sentence beyond the Med-VAEFD label established in C069).

### Attestation phrasings (≥3 from source, confirming that Med-VAEFD's underlying model is appropriately grounded even though this sentence makes no new claim)

1. vandersluijs2023 Title (p.1): "Diagnostically Lossless Compression of Medical Images" — source exists and defines the Med-VAE used by Med-VAEFD. (Grounding anchor for the "Med-VAEFD" label used in this sentence.)

2. vandersluijs2023 §1 (p.1): "we address these challenges by introducing the first large-scale domain-specific variational autoencoder (VAE) designed for compression of high-resolution medical images." — confirms the VAE referenced by Med-VAEFD exists in the source. No new claim is added by C075.

3. vandersluijs2023 §2.1 (p.2): "We train six neural compressors with varying values of f (4, 8, and 16) and C (1, 4, and 16)." — the multiple variants mean Adamson's Figure 3 depicts results for one or more selected Med-VAEFD variants; the choice of variant is an Adamson-side decision detailed in Appendix B.3 (outside paper.txt's scope), not a claim about the source.

4. vandersluijs2023 §2.2 Evaluation Suite (p.2): "we propose a benchmark that includes 5 fine-grained classification tasks and an expert reader study in addition to standard perceptual quality assessments." — source's own evaluation uses SROCC-adjacent metrics (FID, PSNR, MS-SSIM) but NOT SROCC on reader scores. Adamson's Figure 3 analysis is Adamson's own; no SROCC claim is being attributed to the source.

### Coverage

- "Med-VAEFD" as a label: YES (grounded upstream in C069).
- New factual claim about vandersluijs2023 in this sentence: NONE.
- The metric / DFD enumeration in the sentence is Adamson's own experimental design.

### Flag

Third instance in this manuscript of the claim-extractor auto-tagging figure-description sentences with every ref present in the surrounding paragraph (compare C071, which was flagged identically for ref #6 in paragraph 57, and C067/C068 in paragraph 48). Recommend merging C075 with C069 for attestation-envelope purposes, or dropping C075 as a duplicate of C069's grounding.

### Final verdict

C075: NON-ATTRIBUTION (figure-framing extraction artifact; underlying Med-VAEFD label already grounded in C069)

---

### C076 — vandersluijs2023

**Section:** §3 Results (paragraph 57)
**Citekey:** `vandersluijs2023` (ref #50)
**Sentence tagged with ref #50 by extractor (verbatim):**

> In the fixed-encoder architecture case, for example, training the ResNet50 encoder with the out-of-domain ImageNet dataset (Aliasing SROCC 0.88, Cartilage/Meniscus SROCC 0.87) performs comparably to training with the domain-adjacent RadImageNet dataset (Aliasing SROCC 0.87, Cartilage/Meniscus SROCC 0.85).

### Analysis

This sentence reports a result from Adamson et al.'s OWN experiments — specifically, an architecture-vs-training-data ablation where a ResNet50 encoder is trained on ImageNet vs. RadImageNet and used as a DFD feature extractor for MR image IQ assessment. No part of this experiment or its reported SROCC numbers comes from van der Sluijs et al. (ref #50).

The ref-#50 tag on this sentence is, again, a claim-extraction artifact: paragraph 57 is a long Results paragraph that mentions Med-VAEFD at its start (in the Figure 3 enumeration, see C075) and multiple subsequent result sentences inherit the same ref-#50 tag. This specific sentence is about the RINFD architecture-vs-data ablation (ref #37, mei2022-adjacent), not about Med-VAEFD or van der Sluijs.

Furthermore, a full-text search of vandersluijs2023 for "ResNet50", "ImageNet", and "RadImageNet" returns no hits — the source paper does not use any of these models as encoders or baselines. Its baselines are bicubic interpolation and SD VAE (Rombach et al., 2022 — trained on ~8M natural images), with performance evaluated via fine-grained classification AUROC, FID, PSNR, MS-SSIM — not SROCC to reader scores.

### Source

Van der Sluijs R, et al. "Diagnostically Lossless Compression of Medical Images." ICML 2023 Neural Compression Workshop.

### Verdict

**C076: NON-ATTRIBUTION** (claim-extraction artifact — the sentence reports Adamson's own ResNet50-ImageNet-vs-RadImageNet ablation; no vandersluijs2023 content).

### Attestation log (≥3 phrasings from vandersluijs2023 confirming the source does NOT contain this ablation)

1. vandersluijs2023 §3 Experiments (p.3): "We use our evaluation suite to compare our domain-specific neural compressor to a conventional image downsizing approach as well as an existing large-scale neural compressor trained on eight million natural images (Rombach et al., 2022)." — the source's baselines are bicubic + SD VAE, NOT ResNet50-ImageNet vs ResNet50-RadImageNet. Confirms no overlap with the Adamson sentence.

2. vandersluijs2023 §2.1 Architecture (p.2): "we learn functions g and h using a fully convolutional VAE..." — the source's model is a VAE, not a ResNet50. Confirms architectural non-overlap.

3. Full-text string searches in vandersluijs2023:
   - "ResNet" → 0 hits
   - "ImageNet" → 0 hits
   - "RadImageNet" → 0 hits
   - "SROCC" → 0 hits (the source uses AUROC, FID, PSNR, MS-SSIM as metrics, per Tables 1–2).
   - "Aliasing" / "Cartilage" / "Meniscus" → 0 hits (the source does not evaluate on MR-specific reader tasks).
   Confirms the Adamson sentence has no content attributable to vandersluijs2023.

4. vandersluijs2023 §2.2 Evaluation Suite (p.2): "We report Fréchet Inception Distance (FID), peak signal-to-noise ratio (PSNR), and multi-scale structural similarity index measure (MS-SSIM)." — confirms the source's metrics are FID/PSNR/MS-SSIM, not SROCC-to-reader-scores on aliasing/cartilage/meniscus. The Adamson experimental setup being described is entirely Adamson's own.

### Coverage

No sub-claim in C076 maps to any content in vandersluijs2023. The fixed-encoder ResNet50 ImageNet-vs-RadImageNet ablation is an Adamson-internal experiment whose design and results are not attributable to ref #50.

### Flag

Fourth instance of the claim-extractor over-tagging sentences in paragraph 57 with ref #50 due to the paragraph-level Med-VAEFD mention (at its start) being propagated downstream. The sentence itself has zero ref-#50 content.

Adjacent note: the following sentence ("This is a surprising finding considering the importance of domain-specific pretraining in comparable transfer learning studies.37,38") is the one that carries citations — to refs #37 (mei2022) and #38 (cadrinchenevert2022), captured in C073 and C074 respectively. Ref #50 is not cited on or adjacent to the C076 sentence.

### Final verdict

C076: NON-ATTRIBUTION (extraction artifact; no vandersluijs2023 content in the tagged sentence)

---

### C077 — wang2024

**Section:** 
**Citekey:** `wang2024` (ref #41)
**Claim text:** The correlation of SSIM and NRMSE decreases substantially under increasing acquisition noise, decreasing by 0.17–0.19 and 0.11–0.12, respectively, when k-space coil noise quadruples, corroborating the potential bias of SSIM and NRMSE under acquisition noise demonstrated in prior work.41 We observe that DFDs and HFEN continue to outperform other IQ metrics in terms of SROCC to reader scores as acquisition noise increases.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/wang2024.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C078 — li2020

**Section:** 
**Citekey:** `li2020` (ref #52)
**Claim text:** For example, settings where spatial registration is needed to align image pairs, such as CT-to-MR modality translation,52,53 may not require perfect registration for diagnostic utility.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/li2020.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C079 — jin2019

**Section:** 
**Citekey:** `jin2019` (ref #53)
**Claim text:** For example, settings where spatial registration is needed to align image pairs, such as CT-to-MR modality translation,52,53 may not require perfect registration for diagnostic utility.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/jin2019.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C080 — mason2020

**Section:** §4 Discussion / Limitations (reader-study gold-standard caveat)
**Citekey:** `mason2020` (ref #6; co-cited with ref #40)
**Claim text:** Although there is a precedent for this in other radiologist reader studies,6,40 radiologist perceptions of image quality may not be directly correlated with true diagnostic accuracy.
**Claim type:** BACKGROUND / PRECEDENT — Mason 2020 is cited as a precedent for using radiologist-perceived diagnostic image quality (rather than true diagnostic accuracy) as the gold standard in IQ-metric evaluation.
**Sub-claim attributed:** Mason et al. is an example of a prior radiologist-reader study that used subjective radiologist IQ scoring as the reference against which IQ metrics are evaluated.
**Source excerpt:**
- Abstract (p. 1064): "In this study, we compare the image quality scores of five radiologists with the RMSE, SSIM, and other potentially useful IQMs … The comparison uses a database of MR images of the brain and abdomen … A total of 1017 subjective scores were assigned by five radiologists."
- §I Introduction (p. 1065): "In practice, clinical MR images are typically viewed by an expert radiologist, so the radiologist's opinion of the diagnostic quality of the image can then be considered an appropriate measure of MR image quality. … it is common to use a radiologist's subjective rating of overall diagnostic quality as a surrogate. For an IQM to perform well on MR images, it should then correlate with radiologists' opinion of diagnostic image quality for a variety of image contrasts and degradations."
- §II.C Radiologist Image Quality Assessment (p. 1066–1067): "The radiologists were asked to rate the diagnostic quality of the images with respect to delineation of relevant anatomy and ability to confidently exclude a lesion on a 5-point scale … All judgments of quality were made in their opinion as diagnostic radiologists (e.g. their ability to discriminate relevant tissues, their confidence in using the image to detect, or in this case not detect, pathology, etc.)."
- §III Discussion (p. 1071): Mason itself acknowledges the same limitation: "it should be noted that the scoring of diagnostic quality in a clinically normal MR image is strongly related to but not necessarily equivalent to scoring of an image containing pathology. … Future studies will examine whether these same IQMs correlate with other task based measures such as lesion conspicuity scores in images containing pathology or diagnostic accuracy."
**Support:** CONFIRMED
**Flag:** —
**Remediation:** —
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Intro ✓, §II.C Radiologist IQ Assessment (methodology of radiologist scoring) ✓,
                      §II.D Data Analysis ✓, §III Discussion (incl. limitation that normal-image scoring ≠ diagnostic
                      accuracy) ✓, §IV Conclusion ✓.
  Phrasings searched: "radiologist" / "reader study" / "reader score" / "subjective" / "perceived" (reader-study framing);
                      "surrogate" / "gold standard" / "opinion of diagnostic quality" (gold-standard paraphrases);
                      "diagnostic accuracy" / "task-based" / "lesion conspicuity" (downstream-task contrast);
                      "five radiologists" / "expert" / "subspecialty" (radiologist-expertise check).
  Specific checks:    Radiologist-reader study design — Mason 2020 is itself a radiologist reader study with five
                      subspecialty radiologists scoring 414 degraded MR images on a 5-point Likert scale for diagnostic
                      quality. This is a textbook example of the "radiologist reader study" precedent Adamson invokes.
                      Gold-standard surrogate framing — Mason explicitly frames radiologists' subjective diagnostic-quality
                      scoring as a surrogate for diagnostic accuracy (§I), and uses it as the reference for IQM evaluation
                      (§II.C, §III). This is identical in spirit to Adamson's use of reader scores as the reference.
                      Caveat alignment — Mason itself discusses that diagnostic-quality scoring on clinically normal
                      images is "strongly related to but not necessarily equivalent to scoring of an image containing
                      pathology" and flags diagnostic accuracy as a future-work direction. This directly parallels the
                      caveat that Adamson attaches to the C080 citation.
  Closest adjacent passage: "it is common to use a radiologist's subjective rating of overall diagnostic quality as a
                      surrogate" (Mason §I, p. 1065) — near-verbatim support for "there is a precedent for this in other
                      radiologist reader studies".
  Indirect-attribution check: The precedent is established directly by Mason's own methodology and opening framing;
                      direct-source attribution is appropriate.
  Out-of-context check: Adamson cites Mason for the precedent of using radiologist-perceived quality as a proxy for
                      diagnostic value, and flags the same limitation Mason itself flags. Usage is consistent with Mason's
                      own scope and caveats.

---

### C081 — mei2022

**Section:** 
**Citekey:** `mei2022` (ref #37)
**Claim text:** This result is surprising considering the importance of distribution shifts in learned feature representations in the transfer learning literature.37,38 While we surmise that any learned convolutional filters, independent of the training data domain, may be used as high-dimensional feature extractors for estimating image quality, further theoretical work is required to understand these empirical findings.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/mei2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C082 — cadrinchenevert2022

**Section:** 
**Citekey:** `cadrinchenevert2022` (ref #38)
**Claim text:** This result is surprising considering the importance of distribution shifts in learned feature representations in the transfer learning literature.37,38 While we surmise that any learned convolutional filters, independent of the training data domain, may be used as high-dimensional feature extractors for estimating image quality, further theoretical work is required to understand these empirical findings.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/cadrinchenevert2022.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C083 — kastryulin2023

**Section:** 
**Citekey:** `kastryulin2023` (ref #40)
**Claim text:** Although there is a precedent for this in other radiologist reader studies,6,40 radiologist perceptions of image quality may not be directly correlated with true diagnostic accuracy.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/kastryulin2023.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C084 — dar2019

Parent: "Although the correlation to radiologist-perceived image quality is affected by the domain shift, RINFD as a domain-adjacent DFD likely leverages the fact that RadImageNet covers images of other modalities including MR images, while having a training task of classification, which requires shape, texture, and structure understanding to perform."

Task-provided sub-claim for ref [54]: "this is a cross-modal/multi-contrast MR image synthesis paper cited (likely) in the context of domain-adjacent training data / RadImageNet dataset composition. Verify the actual context."

Citekey: dar2019 (ref #54)
Source: Dar SUH, Yurt M, Karacan L, Erdem A, Erdem E, Cukur T. "Image Synthesis in Multi-Contrast MRI With Conditional Generative Adversarial Networks," IEEE TMI 2019;38(10):2375-2388. DOI 10.1109/TMI.2019.2901750.

### Actual locus of ref [54] in Adamson 2025
The task prompt attaches C084 to a sub-claim about RadImageNet composition, but the phase3 plan / paper.txt show the in-text citation [54] actually appears in a different sentence. From paper.txt lines 514–522:

> "Although HFEN correlates remarkably strongly with DFDs and perceived diagnostic quality in this study of accelerated MR reconstructions, it explicitly captures high-frequency information and therefore may struggle in other MR IQ settings with more low-frequency content such as MR contrast synthesis.[54] Future work should examine the behavior of these IQ metrics in settings beyond accelerated MR reconstruction."

So [54] is used as a pointer/example of "MR contrast synthesis" — a setting contrasted with accelerated MR reconstruction, where HFEN's high-frequency focus might be less appropriate. It is NOT used to support the RadImageNet-composition or classification-requires-shape-texture-structure sub-claim.

### Source paper type
Methods/empirical paper. Proposes pGAN (paired pixel-wise loss) and cGAN (unpaired cycle-consistency) conditional GAN architectures for multi-contrast MRI synthesis (T1 <-> T2), evaluated on MIDAS, IXI, and BRATS datasets against Replica and Multimodal baselines using PSNR/SSIM.

### What dar2019 actually says
Read the full body of dar2019 (Abstract through Conclusion, pages 1–14 of the PDF; 28 pages total incl. figures/references).

Core attestable points from the PDF (direct, paraphrased from readings):
- Abstract: "a new approach for multi-contrast MRI synthesis based on conditional generative adversarial networks ... preserves high-frequency details via an adversarial loss ... Demonstrations on T1- and T2-weighted images from healthy subjects and patients clearly indicate the superior performance of the proposed approach ..."
- Introduction: presents multi-contrast MRI synthesis (T1 <-> T2) as the target problem; argues prior methods (Replica, Multimodal) suffer loss of high-spatial-frequency information due to L1/L2 losses; motivates adversarial loss.
- Methods 2.1: "The adversarial loss helps the generator in modeling high-spatial-frequency information [14]"; pGAN uses pixel-wise L1 + cGAN loss (pix2pix-inspired); cGAN uses cycle-consistency loss (cycleGAN-inspired) for unregistered data.
- Datasets (2.2): MIDAS (66 healthy subjects), IXI (30 healthy subjects), BRATS (28 tumor subjects). All are brain MRI T1 and T2 images.
- Results: pGAN and cGAN outperform Replica and Multimodal in PSNR/SSIM; e.g., "pGAN achieves 1.04 dB higher PSNR than Multimodal in T2 synthesis, and 2.41 dB higher PSNR in T1 synthesis" (IXI). The paper repeatedly attributes improvements to better capture of "high spatial frequency information" via the adversarial loss.
- Discussion: "While our synthesis approach was primarily demonstrated for multi-contrast brain MRI here, it may offer similar performance benefits in synthesis across imaging modalities such as MRI, CT or PET [32]." Notes that GANs "learn the conditional probability distribution of the target contrast given the source contrast" and that adversarial loss enables "enhanced capture of detailed texture information about the target contrast, thereby enabling higher synthesis quality."
- Conclusion: end-to-end conditional GAN for multi-contrast MRI synthesis.

Notable: the paper is strictly about MR-to-MR synthesis within a single subject (multi-contrast), not cross-modality CT/MR synthesis. It focuses on preserving high spatial frequency content and "detailed texture information." The paper does NOT discuss:
- RadImageNet (published 2022, post-dates dar2019).
- Classification as a training task (its task is image-to-image translation via adversarial + pixel/cycle loss, not classification).
- Shape/texture/structure understanding in the specific sense invoked in parent C084.
- Deep feature distances (DFDs), FID, LPIPS, or perceptual metrics.
- Radiologist-perceived image quality or rater studies.

### Attestation (≥3 phrasings verified)

1. dar2019 is a multi-contrast MRI synthesis paper (T1/T2) using conditional GANs.
   - "a new approach for multi-contrast MRI synthesis based on conditional generative adversarial networks" (Abstract).
   - "employs conditional GANs to synthesize images in the target contrast given input images in the source contrast" (Introduction).
   - "We proposed a new multi-contrast MRI synthesis method based on conditional generative adversarial networks" (Conclusion).

2. Paper emphasizes high-spatial-frequency / texture information preserved by adversarial loss.
   - "preserves high-frequency details via an adversarial loss" (Abstract).
   - "The adversarial loss helps the generator in modeling high-spatial-frequency information" (Section 2.1).
   - "incorporation of adversarial loss as opposed to typical squared or absolute error loss leads to enhanced capture of detailed texture information about the target contrast" (Discussion).

3. The paper does not address RadImageNet, perceptual feature distances, or classification-based encoders.
   - Its competing methods are Replica (random-forest multi-resolution regression [3]) and Multimodal (neural-network synthesis [12]); evaluation metrics are PSNR and SSIM only (Section 2.6).
   - No mention of "RadImageNet," "LPIPS," "FID," "DFD," "classification," "radiologist," or "perceived quality" in the read body pages (Abstract, Intro, Methods, Results, Discussion, Conclusion, pp. 1–14).
   - The only cross-modality mention is a forward-looking remark: "may offer similar performance benefits in synthesis across imaging modalities such as MRI, CT or PET [32]" (Discussion) — aspirational, not realized in this paper.

### Mapping to the actual in-text use in Adamson 2025
The actual citation context in Adamson 2025 is: HFEN captures high-frequency information and "may struggle in other MR IQ settings with more low-frequency content such as MR contrast synthesis.[54]"

Evaluation of this actual use:
- dar2019 is indeed a canonical example of "MR contrast synthesis." SUPPORTED.
- Whether dar2019 establishes that MR contrast synthesis has "more low-frequency content" than accelerated MR reconstruction is NOT directly demonstrated by dar2019. The paper actually emphasizes preservation of HIGH-frequency content in contrast synthesis and uses adversarial losses precisely because L1/L2 losses over-smooth (lose high-frequency detail). So dar2019 is a reasonable *pointer* to the genre of MR contrast synthesis, but it is not evidence that contrast synthesis is dominated by low-frequency content; if anything, dar2019 argues the opposite that high-frequency content matters and is hard to capture.
- The citation is used as a generic exemplar of "MR contrast synthesis" to delimit scope, which is a light/background usage. SUPPORTED AS BACKGROUND POINTER; any reader who follows [54] will find a multi-contrast MRI synthesis paper as promised.

### Mapping to the task-provided sub-claim
The task-provided sub-claim says dar2019 is cited "in the context of domain-adjacent training data / RadImageNet dataset composition." This is incorrect about the actual locus of the citation in Adamson 2025 — [54] is NOT in that RadImageNet paragraph; it is in the HFEN / MR contrast synthesis sentence. Within the RadImageNet sentence (parent C084), there is no bracketed citation — the RadImageNet claim is unattributed in that specific sentence (RadImageNet itself is cited elsewhere in the paper under a different ref number; not [54]).

Regardless, dar2019 contains nothing about RadImageNet or classification-based feature learning, so it could not support the RadImageNet-composition sub-claim even if it were cited there.

### Verdict
- As a BACKGROUND POINTER for "MR contrast synthesis" (the actual in-text use in Adamson 2025): SUPPORTED. dar2019 is a well-known multi-contrast MRI synthesis paper and is an appropriate exemplar.
- As support for the task-provided sub-claim about RadImageNet composition / classification-requires-shape-texture-structure: NOT SUPPORTED and also MISLOCATED — the task prompt mis-identifies where [54] sits in the manuscript; the parent sentence about RINFD/RadImageNet does not cite [54] at all.
- Net: the citation-as-used in Adamson 2025 is fine (background pointer is accurate); the task-provided sub-claim mischaracterizes the citation's context.

VERDICT: SUPPORTED (as a background/pointer citation for MR contrast synthesis — the actual in-text usage). The task-provided sub-claim characterization is inaccurate about locus, but the citation itself, as it actually appears in Adamson 2025, is appropriate and grounded.

---

### C085 — mason2020

**Section:** §5 Conclusion / Recommendations (suite-of-metrics recommendation)
**Citekey:** `mason2020` (ref #6)
**Claim text:** A suite of IQ metrics also has the benefit of capturing different aspects of perceived diagnostic image quality, as demonstrated in.6 Overall, our findings demonstrate that DFDs could help align the benchmarking of research methods in MR reconstruction with diagnostically relevant [assessment].
**Claim type:** PARAPHRASED — Adamson claims that Mason 2020 demonstrates the benefit of reporting multiple (complementary) IQ metrics because different metrics capture different aspects of perceived diagnostic image quality.
**Sub-claim attributed:** Mason's findings show that different IQ metrics perform best for different degradations / capture complementary aspects of perceived diagnostic quality.
**Source excerpt:**
- Abstract (p. 1064): "When considering SROCC calculated from combining scores from all radiologists across all image types, RMSE and SSIM had lower SROCC than six of the other IQMs included in the study (VIF, FSIM, NQM, GMSD, IWSSIM, and HDRVDP)." (A different metric is best depending on the grouping.)
- §III Results (p. 1069): "NQM appears to perform particularly well for images degraded by noise as it has a statistically better performance than all other IQMs except FSIM for these images. IWSSIM performed poorly for images degraded by undersampling artifacts, showing statistically larger residuals compared to all other IQMs for these images."
- §III Discussion (p. 1069): "when considering the trends in Fig. 3 and the bottom of Fig. 4, it appears as if the factor that most affects IQM performance is how uniformly the IQM quantifies the quality of images with different degradations. … when the images are divided by degradation type, each IQM has a similar SROCC with the radiologists score. It is only when the different degradations are grouped together that the differences in performance of IQMs arise. This is important to notice because, as discussed in the Introduction, an IQM should correlate with radiologists' opinion over a range of degradations."
- §III Discussion (p. 1070): "FSIM and NQM also consistently demonstrated high correlations with the radiologist scores. Indeed, NQM had performed statistically better than VIF for images degraded with Gaussian noise, undersampling, or wavelet compression."
- §V Conclusion (p. 1072): "Differences in the performance of the IQMs was also largely lost when images are divided by degradation type. Both the IQM SROCC values and calculation times presented in this study should be considered in future imaging studies applying an objective IQM to assess the quality of an MR image."
- Tables IV–VI (pp. 1070–1071): pairwise significance tables partition IQMs into different "best" groupings by radiologist subgroup, reference-image-type subgroup, and degradation-type subgroup — empirically demonstrating that different metrics excel at different aspects.
**Support:** CONFIRMED (moderate)
**Flag:** MINOR — Mason 2020 does not literally recommend reporting "a suite of IQ metrics"; Mason's explicit recommendation is closer to "choose a better single metric" (VIF / FSIM / NQM) rather than "report a suite". However, Mason's results DO directly demonstrate that different IQMs capture different aspects of perceived quality (NQM best for noise and undersampling; VIF best overall; FSIM consistently high across types; IWSSIM poor for undersampling). Adamson's claim that Mason "demonstrates" this is well-supported even if Mason's recommendation framing is slightly different.
**Remediation:** Adamson's "as demonstrated in.6" phrasing is appropriate (it attributes empirical demonstration, not the recommendation itself). No change needed. If the authors wanted to strengthen the citation, they could note that Mason's per-degradation and per-anatomy significance tables (Tables V–VI) show that no single metric dominates across all subgroupings.
**Last verified:** 2026-04-17

Attestation log:
  Paper length:       9 pages (IEEE TMI, vol. 39, no. 4, pp. 1064–1072, Apr. 2020).
  Section checklist:  Abstract ✓, §I Intro ✓, §II Methods ✓, §III Results (Fig. 4 bottom panel, per-degradation SROCCs) ✓,
                      Tables III–VII ✓, §IV Discussion (esp. uniformity-across-degradations paragraph) ✓, §V Conclusion ✓.
  Phrasings searched: "different aspects" / "different degradations" / "different subgroups" (complementarity paraphrases);
                      "suite" / "combination" / "multiple metrics" / "report" (suite-recommendation search — NOT found in Mason);
                      "NQM best" / "VIF best" / "FSIM consistent" (per-metric strengths);
                      "IWSSIM poorly" / "MSSSIM" (per-metric weaknesses);
                      "degradation type" / "reference type" / "radiologist" (subgroup analysis).
  Specific checks:    Complementarity of metrics — Mason's Table VI (per-degradation) shows NQM dominates for Gaussian noise,
                      undersampling, and wavelet compression; VIF dominates for the combined/overall setting; FSIM shows
                      consistently high performance; IWSSIM fails for undersampling. This is empirical evidence that
                      different metrics capture different aspects of perceived quality.
                      Uniformity-across-degradations — Mason §III Discussion (p. 1069) explicitly discusses this: "the
                      factor that most affects IQM performance is how uniformly the IQM quantifies the quality of images
                      with different degradations" — which is the same conceptual point Adamson makes.
                      "Suite" recommendation — Mason does NOT literally say "report a suite of metrics". Mason's explicit
                      recommendation is to use VIF, FSIM, or NQM instead of SSIM/RMSE. However, the empirical demonstration
                      of complementary metric behavior is present, and Adamson's claim is about the demonstration not the
                      recommendation.
  Closest adjacent passage: Mason §III Discussion (p. 1069) — "when the images are divided by degradation type, each IQM
                      has a similar SROCC with the radiologists score. It is only when the different degradations are
                      grouped together that the differences in performance of IQMs arise" — supports the idea that
                      different metrics capture different aspects.
  Indirect-attribution check: The empirical demonstration is Mason's primary finding; direct attribution is appropriate.
  Out-of-context check: Adamson uses Mason to support the "different aspects" claim, which is moderately supported by
                      Mason's per-degradation and per-anatomy significance tables. Adamson does not claim Mason
                      recommends a suite, only that Mason's data demonstrate the complementarity benefit. Usage is
                      within bounds of Mason's evidence.
  Strength-of-attribution note: The support is moderate rather than strong because Mason's primary rhetorical point is
                      "choose a better single metric" whereas Adamson draws the (defensible but non-verbatim) inference
                      that "a suite of metrics is beneficial because different metrics capture different aspects".

---

### C086 — wang2024

**Section:** 
**Citekey:** `wang2024` (ref #41)
**Claim text:** The robustness of the correlations of HFEN, LPIPS, and RINFD to radiologist-perceived diagnostic quality even in the presence of four times the acquisition noise levels should give researchers confidence that these metrics hold their utility in assessing perceptual IQ in spite of the “hidden noise” problem.41 Although SSFD does not appear to generalize as well to higher levels of acquisition noise, we note that if used “in-domain” on the original fastMRI knee dataset as intended, its correlation with radiologist-perceived diagnostic quality remains comparable to other DFDs.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/wang2024.pdf` and re-run `/paper-trail` with `--recheck`._

---

### C087 — luisier2008

Parent claim text:
> "This approach captures perturbative noise in the DFD formulations but does not accurately represent the correlated wavelet-domain noise that a Stein's Unbiased Risk Estimator (SURE)-based method;55 however, the simple approach still provides insights on the behavior of the DFDs under acquisition noise."

Task-provided sub-claim for ref [55]: "SURE-based methods capture correlated wavelet-domain noise (as in SURE-LET)."

Citekey: `luisier2008` (ref #55)
Source: Luisier F, Blu T. "SURE-LET Multichannel Image Denoising: Interscale Orthonormal Wavelet Thresholding," IEEE Transactions on Image Processing, vol. 17, no. 4, pp. 482–492, April 2008. DOI 10.1109/TIP.2008.919370.

### Source paper type
Methods paper. Proposes a vector/matrix extension of the authors' prior monochannel SURE-LET denoiser to multichannel (e.g., color) images, operating in a non-redundant orthonormal wavelet transform (OWT) domain, with an interscale–interchannel thresholding function whose parameters are fit by minimizing Stein's Unbiased Risk Estimate (SURE) of the MSE.

### What luisier2008 actually says (from full read, pp. 482–492)
- Title itself binds the concepts: "SURE-LET Multichannel Image Denoising: Interscale Orthonormal Wavelet Thresholding."
- Abstract: "We propose a vector/matrix extension of our denoising algorithm initially developed for grayscale images, in order to efficiently process multichannel (e.g., color) images. This work follows our recently published SURE-LET approach where the denoising algorithm is parameterized as a linear expansion of thresholds (LET) and optimized using Stein's unbiased risk estimate (SURE). The proposed wavelet thresholding function is pointwise and depends on the coefficients of same location in the other channels, as well as on their parents in the coarser wavelet subband. A nonredundant, orthonormal, wavelet transform is first applied to the noisy data, followed by the (subband-dependent) vector-valued thresholding of individual multichannel wavelet coefficients which are finally brought back to the image domain by inverse wavelet transform."
- Noise model (Section II): "These images are corrupted by an additive channel-wise Gaussian white noise b=[b_1,...,b_N] of known C×C interchannel covariance matrix R, i.e., E{b_n b_{n'}^T} = R δ_{n-n'}." The noise is therefore explicitly **correlated across channels** with covariance matrix R, handled at the wavelet-coefficient level.
- OWT noise statistics (Section II / Fig. 1 discussion): "Given that the noise is white and Gaussian in the image domain, its wavelet coefficients are Gaussian as well, and are independent within and between the subbands. Moreover, the interchannel covariance matrix remains unchanged: E{b_n^j b_{n'}^{j'T}} = R δ_{n-n'} δ_{j-j'}." (Orthonormality preserves R in the wavelet domain — the correlation structure is tracked exactly into the wavelet domain.)
- Theorem 1 (Section II, unbiased MSE estimate): uses Stein's principle with the interchannel covariance matrix R explicitly appearing in the gradient-correction term Tr{R^T ∇_1 θ(y_n, p_n)} and the Tr{R}/C bias term, proving an unbiased estimate of the expected MSE. Reference [28] = Stein 1981.
- Section II explicitly: "we can rely on an adapted version of Stein's unbiased risk estimate (SURE) [28] to accurately estimate this actual MSE."
- Algorithm (Section III) builds the thresholding function as a Linear Expansion of Thresholds (LET), parameters are fit by minimizing the SURE estimate ε, yielding a linear system A_opt = M^{-1} B.
- Interscale predictor (Section III.A) uses parent subbands (coarser scale) via a group-delay-compensation / Gaussian-smoothed low-pass construction, so thresholding depends jointly on coefficient, parent (interscale), and inter-channel coefficients.
- New interscale-interchannel thresholding function (Section III.B, Eq. 13): uses trigger γ(p_n^T R^{-1} p_n) and γ(y_n^T R^{-1} y_n) — i.e., the thresholds are explicitly a function of the Mahalanobis-like form using the inter-channel noise covariance R. This is the precise technical embodiment of "correlated wavelet-domain noise" being handled by SURE.
- Experiments (Section IV) on RGB color images and multiband LandSat imagery demonstrate denoising competitive with or better than redundant-transform methods (ProbShrink-MB, BLS-GSM) despite using only a non-redundant OWT; and in Section IV.A.2 show that RGB results are nearly insensitive to color-space representation (YUV vs RGB) precisely because the SURE framework automatically accounts for channel covariance.

### Attestation log (≥3 phrasings)

1. SURE-LET is SURE-based and operates in an orthonormal wavelet transform domain.
   - Title: "SURE-LET Multichannel Image Denoising: Interscale Orthonormal Wavelet Thresholding."
   - Abstract: "optimized using Stein's unbiased risk estimate (SURE) ... A nonredundant, orthonormal, wavelet transform is first applied to the noisy data."
   - Section II: "we can rely on an adapted version of Stein's unbiased risk estimate (SURE) [28] to accurately estimate this actual MSE."

2. SURE-LET explicitly models correlated multichannel noise via an interchannel covariance matrix R, and that correlation structure is preserved (unchanged) in the orthonormal wavelet domain.
   - Section II: "additive channel-wise Gaussian white noise b ... of known C×C interchannel covariance matrix R, i.e., E{b_n b_{n'}^T} = R δ_{n-n'}."
   - Section II, OWT conservation property: "the interchannel covariance matrix remains unchanged: E{b_n^j b_{n'}^{j'T}} = R δ_{n-n'} δ_{j-j'}."
   - Section IV.A: "in other color spaces, there will usually be noise correlations between the color channels ... the noise covariance matrix in the YUV color space becomes ~R = S R S^T."

3. Wavelet-domain correlation is used operationally inside the SURE-optimized thresholding — R appears in the SURE gradient-correction term and in the interscale–interchannel thresholding function itself.
   - Theorem 1 (Eq. 5): ε = (1/CN)∑‖θ(y_n,p_n)-y_n‖^2 + (2/CN)∑Tr{R^T ∇_1 θ(y_n,p_n)} − (1/C)Tr{R}.
   - Section III.B (Eq. 13): thresholding function uses triggers γ(p_n^T R^{-1} p_n) and γ(y_n^T R^{-1} y_n), directly whitening by the inter-channel noise covariance.
   - Section III.A: interscale predictor p_n built from parent (coarser) low-pass subband, so thresholding is interscale AND interchannel, jointly using R.

4. Interscale structure (parents in the coarser subband) is fundamental to the method.
   - Abstract: "The proposed wavelet thresholding function is pointwise and depends on the coefficients of same location in the other channels, as well as on their parents in the coarser wavelet subband."
   - Section III.A ("Interscale Predictor"): constructs parent-subband predictor p_n via group-delay compensation (Eq. 10) and Gaussian smoothing.
   - Section V (Conclusion): "The resulting interscale-interchannel wavelet estimator consists of a linear expansion of thresholding functions, whose parameters are solved for by minimizing an unbiased estimate of the expected mean squared error between the noise-free signal and the denoised one."

### Evaluation of the sub-claim
Sub-claim as posed: "SURE-based methods capture correlated wavelet-domain noise (as in SURE-LET)."

Parsing: the Adamson sentence contrasts a "simple / perturbative" DFD-noise analysis against the more faithful treatment of **correlated wavelet-domain noise** that a SURE-based method would provide, and cites luisier2008 as the exemplar of such a SURE method.

What the source supports:
- SURE-LET is a SURE-based denoiser (yes — direct and central to the paper).
- It operates in the wavelet domain (yes — orthonormal wavelet transform, with interscale parent structure).
- It explicitly models correlated noise (yes — inter-channel covariance matrix R, preserved into the wavelet domain by orthonormality, and used inside both the SURE MSE estimate and the thresholding trigger).
- It exploits interscale (parent–child) wavelet-domain dependencies (yes).

Nuance: luisier2008's "correlated noise" is primarily **inter-channel correlation** (across color/multiband channels) with the noise assumed white *within* each channel in the image domain (Gaussian white noise per channel). The orthonormal wavelet transform preserves both the whiteness within subbands and the inter-channel covariance R across subbands. So "correlated wavelet-domain noise" as used in Adamson 2025 is well-captured: SURE-LET accurately handles the joint statistics (including the inter-channel covariance) of wavelet coefficients, which is precisely the distinction Adamson draws from their "simple / perturbative" DFD noise approach. The sub-claim is also consistent with the broader SURE literature in which SURE naturally accommodates non-white or correlated Gaussian noise because the risk estimator is derived for general Gaussian covariance.

Within-subband decorrelation (whiteness of b^j across spatial positions) is a property of applying an OWT to white image-domain noise; spatial correlation of wavelet coefficients is not the main object, but inter-channel correlation and interscale dependence of signal/noise are — and both are explicitly exploited by SURE-LET.

Therefore, using luisier2008 to point the reader at a "SURE-based method" that correctly represents correlated wavelet-domain noise is accurate: the paper is the canonical multichannel SURE-LET reference, it is wavelet-domain, and the covariance matrix R is threaded through the entire derivation and algorithm.

### Verdict
DIRECT — SUPPORTED.

The cited paper is the standard, on-point reference for a SURE-based wavelet-domain denoiser that explicitly represents correlated (interchannel) noise via a covariance matrix R carried into the orthonormal wavelet domain, and additionally exploits interscale (parent) dependencies. The in-text usage in Adamson 2025 — contrasting a perturbative DFD noise analysis against a SURE-based treatment of correlated wavelet-domain noise — is a fair and accurate invocation of luisier2008.

**Classification:** DIRECT
**Support:** SUPPORTED
**Flag:** none
**Last verified:** 2026-04-17

---

### C088 — desai2023

**Section:** 
**Citekey:** `desai2023` (ref #56)
**Claim text:** DATA AVAILABILITY STATEMENT All experiments were carried out in meddlr, an open source config-based Python library for machine learning-based medical image reconstruction.56 All code, data and DFD encoder models to reproduce results in this study have been provided at.
**Claim type:** PENDING (source PDF unavailable)
**Source excerpt:** — (PDF not fetched; see `fetch_report.json` for retrieval attempts)
**Support:** PENDING
**Flag:** NEEDS_PDF
**Remediation:** — (grounding blocked on PDF retrieval)
**Last verified:** 2026-04-17

_Reader-mode audit: this ref was not retrievable via arXiv / unpaywall / Semantic Scholar / direct OA sources (institutional access: Personal only). To ground this claim, save the source PDF as `pdfs/desai2023.pdf` and re-run `/paper-trail` with `--recheck`._

---

