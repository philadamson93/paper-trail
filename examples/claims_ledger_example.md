---
pdf_dir: background/
pdf_naming: "{citekey}.pdf"
bib_files:
  - references.bib
institutional_access: "university library proxy"
last_bootstrap: 2026-04-15
---

# Claims Ledger — example

This is a **sample ledger** showing what `/ground-claim` produces in practice. It exercises several different claim types, support levels, and remediation categories so you can see the format before running the command on your own manuscript.

The papers cited in the examples (Merlin, Duan et al. foundation-models-in-oncology, Prosperi, van Amsterdam, Pillar-0) are all real public works — source excerpts and page numbers are intended to illustrate the ledger format. Verify against the actual papers before relying on anything here for your own writing.

## Summary

| ID | Section | Cite | Type | Support | Source page | Flag | Last verified |
|----|---------|------|------|---------|-------------|------|---------------|
| C001 | 2.2.3 | blankemeier2024merlin | DIRECT | CONFIRMED | 13 | — | 2026-04-15 |
| C002 | 2.2.3 | blankemeier2024merlin | DIRECT | OVERSTATED | 9 | REVIEW | 2026-04-15 |
| C003 | 2.1 | blankemeier2024merlin | DIRECT | CONTRADICTED | 1, 4 | CRITICAL | 2026-04-15 |
| C004 | 2.1 | duan2025fmoncology | FRAMING | CONFIRMED | 1 | — | 2026-04-15 |
| C005 | 5.1 | prosperi2020causal | DIRECT | CONFIRMED | 1 | — | 2026-04-15 |
| C006 | 5.1 | vanamsterdam2025causaloncology | DIRECT | CONFIRMED | 1 | — | 2026-04-15 |
| C007 | 2.2.3 | agrawal2025pillar0 | DIRECT | PARTIALLY_SUPPORTED | 1, 5 | REVIEW | 2026-04-15 |

## Details

### C001 — CONFIRMED direct claim

- **Section:** 2.2.3
- **Citekey:** `blankemeier2024merlin`
- **Claim text (manuscript):** "Merlin is a 3D vision-language foundation model trained on 25,528 abdominal CT volumes from 18,321 patients."
- **Claim key:** `merlin is a 3d vision-language foundation model trained on 25,528 abdominal ct volumes from 18,321 patients.`
- **Claim type:** DIRECT
- **Source excerpt (p. 13):** "…trained on 25,528 abdominal CT volumes from 18,321 unique patients…"
- **Support level:** CONFIRMED
- **Remediation:** —
- **Last verified:** 2026-04-15

---

### C002 — OVERSTATED; propose REWORD

- **Section:** 2.2.3
- **Citekey:** `blankemeier2024merlin`
- **Claim text (manuscript):** "Merlin substantially outperforms OpenCLIP and BiomedCLIP on zero-shot findings classification."
- **Claim key:** `merlin substantially outperforms openclip and biomedclip on zero-shot findings classification.`
- **Claim type:** DIRECT
- **Source excerpt (p. 9):** "Merlin outperforms OpenCLIP and BiomedCLIP…" — no intensifier in the paper's wording.
- **Support level:** OVERSTATED
- **Remediation:** REWORD. Suggested edit: delete "substantially" — the source reports outperformance without the adjective.
- **Last verified:** 2026-04-15

---

### C003 — CONTRADICTED (typo); propose REWORD

Example of catching a real regression: the manuscript number disagrees with the source, and with an earlier sentence in the same chapter.

- **Section:** 2.1
- **Citekey:** `blankemeier2024merlin`
- **Claim text (manuscript):** "a phenotype classification head predicting 1,692 clinical phenotypes via PheWAS mapping"
- **Claim key:** `a phenotype classification head predicting 1,692 clinical phenotypes via phewas mapping`
- **Claim type:** DIRECT
- **Source excerpt (abstract p. 1; §2.2 p. 4):** "phenotype classification (**692** phenotypes)" / "Merlin in predicting **692** phenotypes defined in PheWAS"
- **Support level:** CONTRADICTED
- **Remediation:** REWORD. Suggested edit: change `1,692` → `692`. Likely a stray "1," prefix — the paper consistently reports 692.
- **Last verified:** 2026-04-15

---

### C004 — FRAMING, confirmed

Example of the FRAMING type — citation as a pointer to a conversation, not evidence for a specific sentence-level claim.

- **Section:** 2.1
- **Citekey:** `duan2025fmoncology`
- **Claim text (manuscript):** "AI systems for oncology face a persistent evaluation gap that generalist foundation models do not adequately address."
- **Claim key:** `ai systems for oncology face a persistent evaluation gap that generalist foundation models do not adequately address.`
- **Claim type:** FRAMING
- **Source excerpt (p. 1 onward):** The paper surveys the evaluation gap for foundation models in oncology and advocates for more domain-appropriate benchmarks. Used here as a pointer to that conversation; no sentence-level claim is being directly attributed.
- **Support level:** CONFIRMED (paper addresses the topic)
- **Remediation:** —
- **Last verified:** 2026-04-15

---

### C005 — multi-cite, entry 1 of 2

The manuscript sentence is:

> "Causal inference methods have been proposed for treatment-effect estimation in retrospective oncology cohorts~\cite{prosperi2020causal, vanamsterdam2025causaloncology}."

`\cite{...}` with multiple keys produces one entry per citekey. C005 and C006 share the same `Claim text` and `Claim key` but differ in citekey, source excerpt, page, and (potentially) support level.

- **Section:** 5.1
- **Citekey:** `prosperi2020causal`
- **Claim text (manuscript):** "Causal inference methods have been proposed for treatment-effect estimation in retrospective oncology cohorts."
- **Claim key:** `causal inference methods have been proposed for treatment-effect estimation in retrospective oncology cohorts.`
- **Claim type:** DIRECT
- **Source excerpt (p. 1):** Prosperi et al. review causal-inference methods applicable to retrospective cohort analyses and argue for their wider adoption in clinical research.
- **Support level:** CONFIRMED
- **Remediation:** —
- **Last verified:** 2026-04-15

---

### C006 — multi-cite, entry 2 of 2

- **Section:** 5.1
- **Citekey:** `vanamsterdam2025causaloncology`
- **Claim text (manuscript):** "Causal inference methods have been proposed for treatment-effect estimation in retrospective oncology cohorts."
- **Claim key:** `causal inference methods have been proposed for treatment-effect estimation in retrospective oncology cohorts.`
- **Claim type:** DIRECT
- **Source excerpt (p. 1):** van Amsterdam et al. survey causal inference approaches applied to treatment-effect estimation in oncology.
- **Support level:** CONFIRMED
- **Remediation:** —
- **Last verified:** 2026-04-15

> Shares `Claim key` with C005. Lookup is by `(claim_key, citekey)` tuple — if the manuscript sentence is rewritten, both entries flag STALE together.

---

### C007 — PARTIALLY_SUPPORTED; propose RESCOPE

Example of a composite claim where the architecture is supported but a numeric sub-claim is ambiguous.

- **Section:** 2.2.3
- **Citekey:** `agrawal2025pillar0`
- **Claim text (manuscript):** "Pillar-0 uses a hierarchical multi-scale attention architecture trained on approximately 155,000 scans spanning chest, abdomen-pelvis, and head CT as well as breast MRI."
- **Claim key:** `pillar-0 uses a hierarchical multi-scale attention architecture trained on approximately 155,000 scans spanning chest, abdomen-pelvis, and head ct as well as breast mri.`
- **Claim type:** DIRECT
- **Source excerpt (p. 1, p. 5):** Architecture confirmed — "Multi-Scale Attention" named in Figure 2 (p. 5). Scan counts: CT-only total is 143,749; combined CT + breast MRI is 155,292. The wording "155,000 scans" is ambiguous about which modalities are included.
- **Support level:** PARTIALLY_SUPPORTED
- **Remediation:** RESCOPE. Suggested edit: replace "approximately 155,000 scans spanning chest, abdomen-pelvis, and head CT as well as breast MRI" → "approximately 155,000 volumes (143,749 CT and 11,543 breast MRI)". Disambiguates the combined count.
- **Last verified:** 2026-04-15
