# Reader-mode example — Adamson et al. 2025 (DFD paper)

A real `/paper-trail` smoke-test run against one of the repo author's own published papers. Used as the end-to-end validation for the v1 blindspot fixes; every finding below is a true catch on a peer-reviewed paper.

**Input paper:** Adamson PM, Desai AD, Dominic J, et al. "Using deep feature distances for evaluating the perceptual quality of MR image reconstructions." *Magnetic Resonance in Medicine*, 2025. DOI [10.1002/mrm.30437](https://doi.org/10.1002/mrm.30437). (PDF not included; open the DOI for the source.)

**What this directory contains:**

- [`refs.bib`](./refs.bib) — 56 references parsed from the DFD paper's bibliography (numbered Vancouver style).
- [`parse_report.md`](./parse_report.md) — parser diagnostics: counts, style detection, low-confidence entries.
- [`ledger.md`](./ledger.md) — full audit artifact: input-paper frontmatter, Critical findings, Summary table, per-claim Details, verifier results, end-of-run triage.

Source PDFs (the paper itself + fetched cited papers) are intentionally omitted; they are easily retrieved via their DOIs / arXiv IDs and are subject to publisher copyright.

## Scope

Smoke test: 5 of 56 references ran end-to-end through Phases 1–3; the other 51 were deferred. Refs sampled:

| Ref # | Citekey | Reason to sample |
|---|---|---|
| 27 | `zhang2018` | LPIPS — central to the DFD paper's motivation |
| 35 | `deng2009` | ImageNet — test the `CITED_OUT_OF_CONTEXT` path on a dataset-paper citation used in a transfer-learning claim |
| 42 | `florian2020` | Pre-flagged as suspected parser / source bib error (fastMRI) |
| 46 | `simonyan2014` | VGG — test preprint→published upgrade detection |
| 51 | `desai2021` | VORTEX — test preprint→MIDL upgrade + methods-claim grounding |

## Workflow executed

### Phase 0 — Bibliography extraction
- Text extraction via `pdftotext` (59k chars across 14 pages, well above the 200 chars/page image-PDF threshold → no OCR needed).
- Numbered-Vancouver style auto-detected from entry prefixes.
- 56 entries parsed; 6 had arXiv IDs; 0 had DOIs printed in the bibliography (typical for Wiley formatting).
- Ref 42 pre-flagged in `parse_report.md`: printed authors `Florian K, Jure Z, Anuroop S` appear to have first/last names swapped — expected Knoll F, Zbontar J, Sriram A for the fastMRI paper.

### Phase 0.5 — Confirmation gate
- Asked the user to confirm the count of 56 matches the paper's printed bibliography. User confirmed and chose scoped smoke test (5 refs) over full pipeline.

### Phase 1 — Verify bib (5 subagents, parallel)
Each subagent invoked `/verify-bib` per-entry logic via CrossRef / arXiv lookups. Results:

- **`florian2020` — CRITICAL.** Chimera author field confirmed: first/last names swapped *and* the 23-author list truncated to 3. Authoritative DOI `10.1148/ryai.2020190007`. Suggested fix includes the full 23-author list from CrossRef.
- **`simonyan2014` — MINOR.** Preprint→published upgrade to ICLR 2015 available (ICLR has no CrossRef DOI, but the peer-reviewed venue is well-established).
- **`desai2021` — MINOR.** Preprint→published upgrade to MIDL 2022, PMLR v172:325–352 (`https://proceedings.mlr.press/v172/desai22a.html`).
- **`zhang2018` — MINOR.** Missing `doi = {10.1109/CVPR.2018.00068}`.
- **`deng2009` — clean.** All fields match CrossRef.

### Phase 2 — Fetch PDFs (5 subagents, parallel)
All 5 PDFs retrieved:

- `zhang2018.pdf` — arXiv 1801.03924 (5.4 MB).
- `florian2020.pdf` — **see caveat below**: the Radiology:AI DOI returned HTTP 403; the fetch subagent substituted arXiv:1811.08839 (the sibling preprint). Saved, but flagged throughout downstream phases.
- `deng2009.pdf` — image-net.org open-access copy (3.3 MB).
- `simonyan2014.pdf` — arXiv 1409.1556 (195 KB).
- `desai2021.pdf` — PMLR (15.3 MB; largest, triggered Phase 3 chunked-read).

### Phase 3 — Ground claims (5 subagents, one per source paper)
- Claim extraction on the DFD body text identified 6 claim–citekey tuples across these 5 refs (some multi-claim, e.g., fastMRI is cited for both dataset use *and* UNet architecture).
- Each subagent read its source PDF in full (or in chunked-read mode for `desai2021` at 35 pages > the 25-page threshold) and produced a verdict with a complete attestation log.

Per-claim results:

| ID | Citekey | Type | Support | Flag |
|---|---|---|---|---|
| C001 | `zhang2018` | PARAPHRASED (high) | PARTIALLY_SUPPORTED | REVIEW |
| C002 | `deng2009` | BACKGROUND (high) | CITED_OUT_OF_CONTEXT | REVIEW |
| C003 | `simonyan2014` | BACKGROUND (high) | CONFIRMED | — |
| C004 | `florian2020` | DIRECT (high) | CONFIRMED | — |
| C005 | `florian2020` | DIRECT (medium) | CITED_OUT_OF_CONTEXT | REVIEW |
| C006 | `desai2021` | DIRECT (high) | CONFIRMED | — |

### Phase 3.5 — Attestation verifier (2 probes, parallel)
Scoped to the two non-CONFIRMED entries (C001, C002). Both spot-checks passed — no `UNVERIFIED_ATTESTATION` flags. In a full run every claim gets a verifier probe.

### Phase 4 — Ambiguity triage
Zero `AMBIGUOUS` entries produced; no triage prompt was needed.

## Notable real catches

### 1. Bibliography: author list swapped on a frequently-cited paper
The printed DFD bibliography has "Florian K, Jure Z, Anuroop S" for the fastMRI entry — a classic typesetter error where given names and family names were swapped, likely from the submission's author metadata being parsed incorrectly by the publisher. `/verify-bib` caught it via CrossRef and suggested the full 23-author list.

### 2. Citation hygiene: dataset paper cited for a claim it doesn't make
Ref 35 (Deng et al. 2009, the ImageNet paper) is cited in the DFD intro for: *"the transfer of weights from ImageNet pre-trained architectures often fails due to distributional shifts..."* The grounding subagent read the ImageNet paper in full (abstract, §2 properties, §3 construction, §4 applications, §5 discussion, all 12 figures, Table 1, references) and confirmed the paper contains **no** mention of transfer learning, pre-training, distributional shift, or medical imaging. The transfer-failure claim belongs to the co-cite (Raghu et al. 2019). Verdict: `CITED_OUT_OF_CONTEXT` / remediation `RESCOPE` — narrow the Deng 2009 citation to attach only to "ImageNet" the entity, and let the Raghu 2019 cite carry the transfer-failure clause.

### 3. Citation hygiene: "fastMRI challenge" vs "fastMRI baseline" conflation
Ref 42 is cited for: *"The UNet models followed the architecture in the fastMRI challenge."* The grounding subagent verified the UNet architecture content does match the fastMRI dataset-paper baseline, but noted the cited paper labels this architecture as the *fastMRI dataset baseline*, not the *fastMRI challenge* architecture. The 2019 fastMRI Challenge was a separate event; its winning architectures were varnet / i-RIM, not the U-Net. Verdict: `CITED_OUT_OF_CONTEXT` (soft) / remediation `REWORD` — change "fastMRI challenge" to "fastMRI baseline". One-word fix; substance unchanged.

### 4. Scope drift + factual slip on LPIPS
The LPIPS claim in the DFD intro says LPIPS *"correlates strongly with human perceived IQ"* and describes it as *"a lower-dimensional feature space encoded by a CNN."* The grounding subagent caught two issues:
- Zhang et al. explicitly frame their dataset as **perceptual similarity**, not image quality — the CVPR changelog literally clarifies "perceptual similarity dataset (as opposed to an IQA dataset)." Using "IQ" is a `OVERGENERAL` scope drift.
- The LPIPS feature space is computed over layer activations (channels × spatial) that are generally **higher-dimensional** than raw pixel patches, not lower. Factual slip.
- Verdict: `PARTIALLY_SUPPORTED` / remediations `REWORD` ("human perceived IQ" → "human perceptual similarity judgments"; "lower-dimensional feature space" → "deep feature space").

## Features exercised on this run

- **Thorough-reading enforcement** (Step 2 minimum-reading + attestation log) — each grounding subagent produced a full section checklist with quoted passages per section.
- **Chunked-read** for >25-page source PDFs — `desai2021.pdf` at 35 pages triggered chunked mode with per-section notes.
- **Citation-hygiene taxonomy** — `CITED_OUT_OF_CONTEXT` and `OVERGENERAL` both surfaced on real claims (C001, C002, C005).
- **Indirect-attribution check** — C001 confirmed `zhang2018` is the primary source for LPIPS (the broader "perceptual loss" lineage is cited but LPIPS itself is original), no `INDIRECT_SOURCE` flag needed.
- **Verifier probes** — two spot-checks confirmed attestation-log accuracy (no fabrications).
- **Confirmation gate** (Phase 0.5) — used to scope the run before committing compute to all 56 refs.
- **`--skip-paywalled` flag** — used for the scoped fetch; no pause at Phase 2.
- **Classification confidence** + strict-default — C005's `DIRECT (medium)` flagged that the subagent was between DIRECT and BACKGROUND, triggering the stricter search.

Features **not** exercised on this paper (would require a paper that tripped them):

- OCR fallback — DFD paper is text-extractable.
- Non-IMRaD structure handling — DFD has a standard IMRaD layout.
- `INDIRECT_SOURCE` verdict — no multi-step citation chain surfaced in the sampled claims.
- `AMBIGUOUS` + triage — every verdict was decidable.
- `--fix` — reader mode forbids it.

## Substitution example: Phase 2 on `florian2020`

The Radiology:AI DOI (`10.1148/ryai.2020190007`) returned HTTP 403 to the fetch subagent, but a closely-related fastMRI preprint (arXiv:1811.08839, same author group, substantively overlapping content) was available. On this run the subagent substituted the preprint; downstream grounding for C004 and C005 remained valid and the substitution was flagged in both claim attestation logs for traceability.

This genuinely raises a design question — substituting a related preprint is cheaper and often adequate, but may be an older / pre-revision version with different wording or results. The run motivated an explicit configuration knob (landed in the spec after this test):

- New `--fetch-substitute=<never|ask|always>` flag on `/paper-trail`. Default **`ask`**.
- When a fetch subagent finds a paywalled target with a related preprint/postprint candidate, it returns a structured substitution candidate (target URL, candidate URL, relationship, risk notes); the orchestrator applies the configured policy.
  - **`ask`** (default) → prompt the user via `AskUserQuestion` with the candidate and its risk notes.
  - **`never`** → mark `NEEDS_PDF`; user fetches manually or uses `--skip-paywalled`.
  - **`always`** → auto-accept; flag prominently everywhere downstream.
- Every substitution is always logged in `parse_report.md` and in every downstream claim's attestation log — provenance is never silent.

This run effectively operated in an implicit `always` mode (my dispatch prompt handed the subagent the fallback URL, which pre-decided the substitution). A rerun today would default to `ask` and pause for user confirmation before fetching the preprint.

## What a full run would have produced

Scaling this smoke test to the full 56 refs:

- ~56 `/verify-bib` subagents (Phase 1) — most clean; the author-swap CRITICAL on `florian2020` is the headline bib finding.
- ~56 `/fetch-paper` subagents (Phase 2) — many refs are closed-access; `--skip-paywalled` would mark those `NEEDS_PDF` and continue.
- ~15–25 grounding subagents (Phase 3) — one per unique successfully-fetched source paper, each handling all claims that cite it.
- ~50–100 verifier probes (Phase 3.5) — one per claim entry.
- End-of-run triage report surfacing all `CITED_OUT_OF_CONTEXT`, `PARTIALLY_SUPPORTED`, any `UNVERIFIED_ATTESTATION`, and any `AMBIGUOUS` for user triage.

Token cost is real but absorbable — see the repo's rigor-over-compute policy.
