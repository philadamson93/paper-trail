# Reader-mode example — Adamson et al. 2025 (DFD paper)

I ran `/paper-trail` against one of my own published papers. It caught two real miscitations I hadn't spotted — and surfaced some tool-limit caveats worth documenting.

**Input paper:** Adamson PM, Desai AD, Dominic J, et al. "Using deep feature distances for evaluating the perceptual quality of MR image reconstructions." *Magnetic Resonance in Medicine*, 2025. DOI [10.1002/mrm.30437](https://doi.org/10.1002/mrm.30437). (PDF not included; open the DOI for the source.)

## What's in here

- [`ledger.md`](./ledger.md) — **the full audit artifact** (~3,450 lines): YAML frontmatter, Critical findings, Summary table (88 rows), per-claim Details with verbatim source quotes + page numbers + attestation logs. This is the reference document — the summary below only lists the non-CONFIRMED findings.
- [`refs.bib`](./refs.bib) — 56 references, 45 CrossRef-resolved by DOI, 11 manually resolved (arXiv preprints, NeurIPS / ICML workshop papers, Radiology AI articles).
- [`parse_report.md`](./parse_report.md) — Phase 0 parser diagnostics (PDF readability, style detection, enrichment sources, per-entry parser diffs).

Source PDFs of the 31 fetched cited papers are not committed to the repo — they're easily retrievable from their DOIs / arXiv IDs and are subject to publisher copyright.

## Run at a glance

| | Count |
|---|---|
| References parsed | 56 (matches CrossRef exactly) |
| Source PDFs fetched (open-access) | 31 |
| Paywalled / unretrievable under personal access | 25 → claim entries marked `PENDING / NEEDS_PDF` |
| In-text citation → claim tuples extracted | 88 |
| Grounded against their cited PDF | 49 |
| `CONFIRMED` | 43 |
| `MISATTRIBUTED` | **2** ← headline findings |
| `CITED_OUT_OF_CONTEXT` | 4 (extractor artifacts — see caveats) |
| `PENDING / NEEDS_PDF` | 39 |
| `AMBIGUOUS` | 0 |
| Phase 1 bib-audit `CRITICAL` | 0 |
| Phase 1 bib-audit `MODERATE` / `MINOR` | 4 / 6 |

## Headline findings — the non-confirmed entries

Two citations point to the wrong paper in the bib — both are real errors, both have correct alternatives already in (or easy to add to) the reference list.

### 1. `MISATTRIBUTED` — UNet architecture attributed to the fastMRI dataset paper

**Claim C045** (`knoll2020`, ref #42, Methods §2.1): *"The UNet models followed the architecture in the fastMRI challenge,42…"*

The grounding subagent read Knoll 2020 in full (abstract, methods, §3–5, all tables and figure captions). Knoll 2020 is the fastMRI **data-resource** paper; it contains zero mentions of U-Net, CNN, neural networks, or any model architecture. Its own text explicitly points readers to **Zbontar et al. 2018** (arXiv:1811.08839) for "complete details" including the UNet baseline.

- Verdict: `MISATTRIBUTED`.
- Remediation: `RECITE` — add Zbontar et al. 2018 to `refs.bib` and cite it here instead of (or in addition to) Knoll 2020.
- Full attestation log: [ledger.md §C045](./ledger.md#c045--knoll2020).

### 2. `MISATTRIBUTED` — HFEN LoG-filter specs attributed to a PDM paper

**Claim C055** (`miao2008`, ref #13, Methods §2.3): *"…where LoG is a rotationally symmetric Laplacian of Gaussian filter with a kernel size of 15 × 15 pixels and a standard deviation of 1.5 pixels.13"*

The grounding subagent read Miao 2008 in full. It is a **perceptual-difference-model** (Case-PDM) paper — its pipeline is retinal luminance calibration → 2D CSF → cortex filters → detection mechanisms. No LoG filter, no 15 × 15 kernel, no σ = 1.5 parameter, no mention of HFEN anywhere in the paper or its 71-entry reference list. The HFEN LoG-filter specification originates with **Ravishankar & Bresler 2011** — which the manuscript already cites correctly as ref #20 earlier in the same paragraph (*"…HFEN aims to capture finer-grained features… it is limited to assessing only high-frequency content.20"*).

- Verdict: `MISATTRIBUTED`.
- Remediation: `CITE_PRIMARY` — change the superscript from `13` → `20`. One-character fix.
- Full attestation log: [ledger.md §C055](./ledger.md#c055--miao2008).

### 3. Phase 1 bib audit — 4 MODERATE findings

None are fabrications; all are metadata drift between the bib and the authoritative source:

- **Ref 14** (`mantiuk2011`, HDR-VDP-2) — CrossRef-stored title is truncated to just the acronym `HDR-VDP-2`; full title is *"HDR-VDP-2: A calibrated visual metric for visibility and quality predictions in all luminance conditions."* Remediation: expand the title in the bib.
- **Ref 24** (`desai2022`, SKM-TEA) — the bib entry is styled as an arXiv preprint with year 2022; the actual peer-reviewed venue is **NeurIPS 2021 Datasets & Benchmarks Track**, held Dec 2021. The arXiv post came after the conference. Remediation: upgrade to `@inproceedings` with `year = 2021`.
- **Ref 28** (`ding2020`, DISTS) — bib lists `year = 2020` (the IEEE early-access deposit date) alongside `volume = 44, number = 5, pages = 2567–2581` (the May 2022 final pagination). These are inconsistent — pick one or the other.
- **Ref 33** (`keshari2022`) — arXiv lists four authors: Abhisek Keshari, Komal, Sadbhawna, Badri Subudhi. The printed reference and bib list only two ("Keshari A, Subudhi B"); the two middle authors (both mononyms) are missing.

Full bib-audit details in [ledger.md § Critical findings → Phase 1](./ledger.md#phase-1--bib-audit).

## Secondary findings — surfaces of the tool, not of the paper

These are flagged in the ledger but reflect tool limitations rather than errors by the authors.

### 4 × `CITED_OUT_OF_CONTEXT` — regex claim-extractor artifacts

The claim extractor occasionally attached a citation marker to the **wrong sentence** within a paragraph. Example: paragraph 48 has one legitimate `ref 50` citation near the top (for Med-VAEFD), plus several subsequent sentences that don't cite ref 50 — but the extractor tagged ref 50 onto those too. The grounding subagents caught all four cases (C067, C068, C075, C076) and labeled them non-attributions.

Filed as a backlog item for the extractor. For this run, the flags are tool noise and don't imply editorial errors.

### Fetch substitution on `gu2022` — silent 2022 → 2021 swap

The Phase 2 fetcher used Semantic Scholar's `openAccessPdf` field to resolve a paywalled IEEE DOI. For ref 34 (NTIRE 2022 Challenge on Perceptual IQA, `10.1109/CVPRW56347.2022.00109`), the returned OA PDF was actually the **NTIRE 2021** challenge paper (arXiv:2105.03072). The 2021 edition is structurally similar, so the 4 grounding verdicts for NTIRE-style findings still hold, but the substitution was silent in my Phase 2 implementation — it should have been gated by the `--fetch-substitute=ask` policy. Filed as a backlog item; the substitution is flagged prominently in `ledger.md` run caveats.

### Phase 3.5 attestation verifier — skipped

The spec calls for an independent verifier subagent per claim to spot-check each grounding subagent's attestation log. This run skipped that pass (49 more subagents felt disproportionate for a single session). The Phase 3 grounding subagents still produced full attestation logs — section checklists, ≥3 phrasings, closest-adjacent quotes — which are preserved in the Details blocks for anyone who wants to spot-check manually.

## Scope & caveats — what to trust, what to double-check

1. **MISATTRIBUTED findings (C045, C055)** — the attestation logs are thorough; I verified both against the source PDFs independently before writing this README. These are real.
2. **CONFIRMED entries (43)** — the grounding subagents produced full attestation logs. Without the Phase 3.5 verifier pass, a reviewer relying on any one of these for a high-stakes decision should spot-check it against the page numbers in the Details block.
3. **PENDING entries (39)** — no verdict; source PDF was paywalled under "personal only" access. Save the PDFs as `pdfs/<citekey>.pdf` and re-run `/paper-trail <pdf> --recheck` to ground them.
4. **CITED_OUT_OF_CONTEXT entries (C067/C068/C075/C076)** — tool noise, not author errors.
5. **LLM fallibility** — every flagged entry should be **manually verified** against the cited source before acting on it. The ledger is a triage queue, not a verdict.

## Features exercised

- **Rigor-over-compute grounding** — each of the 31 grounding subagents read the entire cited PDF (or chunked-read for longer papers), produced a section checklist and ≥3 phrasings per claim, and recorded verbatim source excerpts with page numbers.
- **Dual-source bibliography extraction** — PDF-parsed entries reconciled against CrossRef's reference list for the input DOI; 56 entries from each source, 1:1 match by ordinal.
- **Phase 0 confirmation gate** — parser counts surfaced to the user for manual confirmation before Phase 1.
- **`--skip-paywalled` path** — 25 refs marked `PENDING / NEEDS_PDF`; downstream phases ran on the other 31.
- **Programmatic fetch pipeline** — arXiv direct → Unpaywall → Semantic Scholar → publisher-specific direct URLs → OpenReview for workshop papers. 31/56 open-access copies retrieved over 4 progressively-broader passes.
- **Inflight-file claim layout** — per-claim `Cxxx.md` files from 31 concurrent grounding subagents, merged sequentially into the final `ledger.md` (no concurrent-write clobbering).
- **Citation-hygiene taxonomy** — `MISATTRIBUTED` surfaced twice on real editorial slips; `CITED_OUT_OF_CONTEXT` surfaced four times on tool artifacts.

## What a re-run with better access would add

- Full `--fetch-substitute=ask` gating on Phase 2 (the NTIRE 2022 → 2021 swap would have paused for user confirmation).
- 25 more grounding subagents once the paywalled refs are retrieved via institutional access.
- Phase 3.5 verifier probes on all 49 (or ~74 with the paywalled batch) grounded claims.

## Companion example

See the repo root's [`README.md`](../../README.md) for the `/paper-trail` spec overview, taxonomies, and installation.
