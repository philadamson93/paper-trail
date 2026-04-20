# Example run — Adamson et al. 2025

A complete `/paper-trail` reader-mode audit of one real paper: Adamson PM, Desai AD, Dominic J, et al. *"Using deep feature distances for evaluating the perceptual quality of MR image reconstructions."* **Magnetic Resonance in Medicine**, 2025. DOI [10.1002/mrm.30437](https://doi.org/10.1002/mrm.30437).

This is the canonical worked example — if you're wondering what `/paper-trail` produces on a real paper, this is it.

## Try it now

Open **`demo.html`** in any browser — ~39 MB (the PDF is inlined so it works from `file://` in Chrome/Safari/Firefox without setup). A PDF.js-based viewer renders `input-paper.pdf` on the left with the full claim ledger on the right. Click a claim row to jump to that spot in the PDF; click the ⓘ button for the full verdict detail popup (reference card, claim text, sub-claim breakdown, evidence excerpts, remediation). Click a citation marker *in* the PDF to highlight the matching claims in the sidebar. The sidebar supports text filtering and verdict-legend toggles.

## What's in this bundle

```
demo.html              Reference HTML viewer. Open in a browser.
input-paper.pdf        The audited paper itself.
paper.txt              Plaintext extraction used by demo.html
                       to render the manuscript with inline citation markers.
refs.bib               Bibliography parsed verbatim from input-paper.pdf.
refs.verified.bib      Same bibliography, enriched with DOIs / metadata
                       resolved via CrossRef during the audit.
verdict_schema.md      JSON schema every claim file conforms to.
data/
  claims/<id>.json         88 verdict files — one per claim. SOURCE OF TRUTH.
  evidence/<id>.json       49 extractor outputs (Pass 1; pre-verdict).
  verifications/<id>.json  5 verifier spot-check results.
```

Reference PDFs of the 31 fetched sources are not included — easily retrievable from their DOIs / arXiv IDs, and subject to publisher copyright. The verdicts capture every excerpt needed to reproduce a finding.

## Run at a glance

| | Count |
|---|---|
| References parsed from the PDF | 56 (matches CrossRef exactly) |
| Open-access source PDFs fetched | 31 |
| Paywalled under personal access | 25 → claim entries stubbed `PENDING / NEEDS_PDF` |
| In-text `(sentence, citekey)` claims | 87 (one extraction-artifact claim was dropped by the Tier 1 validator) |
| Grounded with real verdicts | 48 |
| `CONFIRMED` / `CONFIRMED_WITH_MINOR` | 34 / 5 |
| `CONTRADICTED` (critical) | 2 (see below) |
| `MISATTRIBUTED` | 1 (see below) |
| `INDIRECT_SOURCE` | 1 (see below) |
| `CITED_OUT_OF_CONTEXT` | 1 |
| `PARTIALLY_SUPPORTED` / `OVERGENERAL` | 2 / 1 |
| `UNSUPPORTED` | 1 |
| `AMBIGUOUS` | 0 |
| `PENDING / NEEDS_PDF` | 39 |
| Phase 1 bib-audit `CRITICAL` | 0 |
| Phase 1 bib-audit `MODERATE` / `MINOR` | 4 / 6 |

> **This bundle has been re-grounded once** after the Tier 1 claim-extraction validator (`.claude/scripts/validate_claims.py`) flagged 10 claims whose stored `claim_text` was a paraphrase or fabrication rather than a sentence from the manuscript. Nine were re-extracted and re-adjudicated against their source PDFs; one (`C071`, mason2020) was dropped as an extraction artifact since its text matched a sentence that doesn't cite any reference. The validator now reports 87/87 PASS.

## Headline findings

The most consequential verdicts, ordered by severity. Each is reproducible from the claim JSON + the cited source PDF.

| Claim | Citekey | Verdict | Summary |
|---|---|---|---|
| **C072** | `mason2020` | `CONTRADICTED` | Manuscript describes Mason 2020 as a study of "natural images"; the paper is actually about **MR images**. |
| **C069** | `vandersluijs2023` | `CONTRADICTED` | Manuscript says the paper's loss is "L2 + perceptual + adversarial"; the paper uses **KL** (not L2). |
| **C055** | `miao2008` | `MISATTRIBUTED` | HFEN / LoG(15×15, σ=1.5) cited to a perceptual-difference-model paper; actual primary is Ravishankar & Bresler 2011 (already cited as ref 20). One-character fix: `13` → `20`. |
| **C045** | `knoll2020` | `INDIRECT_SOURCE` | UNet architecture attributed to the fastMRI **data-resource** paper, which itself defers to Zbontar et al. 2018 for the baseline. |
| **C056** | `chen2022` | `UNSUPPORTED` | Listed metrics (MSSIM / IWSSIM / FSIM / HFEN) are absent from the cited paper. |

### Phase 1 bib-audit MODERATE findings

Not fabrications — metadata drift between the printed bib and authoritative sources:

- **`mantiuk2011`** (HDR-VDP-2) — CrossRef title truncated to the acronym; full title in the authoritative source.
- **`desai2022`** (SKM-TEA) — bib entry styled as an arXiv preprint (year 2022); actual peer-reviewed venue is **NeurIPS 2021 Datasets & Benchmarks Track** (Dec 2021).
- **`ding2020`** (DISTS) — `year = 2020` (IEEE early-access deposit) inconsistent with `volume = 44, number = 5, pages = 2567–2581` (May 2022 final pagination). Pick one.
- **`keshari2022`** — arXiv lists four authors; bib lists two (two mononym middle authors missing).

## What is "a claim"?

A *claim* is one cited assertion in the manuscript — a sentence that cites at least one reference. Each `(sentence, citekey)` pair gets one verdict file. Composite claims like *"ResNet50 pretrained on 1.4M medical images including 670k MRI"* split into multiple **sub-claims** so the verdict can report per-fact drift (e.g., "1.4M" vs the paper's actual "1.35M").

Each file under `data/claims/` has this shape:

```json
{
  "claim_id": "C006",
  "citekey": "mason2020",
  "claim_text": "In a reader study of 1000 MR images...",
  "manuscript_section": "Introduction (paragraph 1)",
  "claim_type": {"type": "DIRECT", "confidence": "medium"},
  "sub_claims": [
    {
      "sub_claim_id": "C006.a",
      "text": "The reader study used a library of 1000 MR images.",
      "verdict": "OVERSTATED",
      "paper_value": "414 images / 1017 scores",
      "claim_value": "1000 MR images",
      "evidence": [{"section": "...", "line": 12, "snippet": "..."}],
      "nuance": "..."
    }
  ],
  "overall_verdict": "CONFIRMED_WITH_MINOR",
  "overall_flag": "MINOR",
  "remediation": {"category": "REWORD", "suggested_edit": "..."},
  "attestation": {...},
  "co_cite_context": {...}
}
```

Cross-reference `claim_id` → `citekey` → entry in `refs.bib` for full reference metadata. Full schema: `verdict_schema.md` in this directory.

## Verdict categories

The twelve verdicts in the enum, ordered roughly worst → best:

- `CONTRADICTED` — paper actively says the opposite (critical)
- `UNSUPPORTED` — no evidence found despite thorough search
- `MISATTRIBUTED` — claim is true but this isn't the source
- `INDIRECT_SOURCE` — paper has the fact but credits another primary
- `CITED_OUT_OF_CONTEXT` — passage exists but used in a materially different context
- `PARTIALLY_SUPPORTED` — some sub-claims hold, others don't
- `OVERGENERAL` — paper proves it in narrow scope; manuscript generalizes beyond
- `OVERSTATED` / `OVERSTATED_MILD` — strength drift (manuscript stronger than source)
- `CONFIRMED_WITH_MINOR` — supported with small caveats (overall-only rollup)
- `CONFIRMED` — clean match
- `AMBIGUOUS` — adjudicator couldn't confidently pick; awaits human triage
- `PENDING` — source PDF unavailable (paywalled); not yet adjudicated

39 of the 88 entries in this bundle are `PENDING` — the audit couldn't fetch their source PDFs under personal access. The other 49 have real verdicts.

## Caveats specific to this run

- **39 `PENDING` entries** — paywalled refs. Drop PDFs into `pdfs/<citekey>.pdf` (via institutional access, etc.) and re-invoke `/paper-trail <pdf> --recheck` to ground them.
- **Verifier only ran on 5 of 49 grounded claims.** The verdicts without a verifier pass still carry full attestation logs (≥3 phrasings, section checklists, closest-adjacent quotes); spot-check them before acting on any one.
- **Every flagged entry should be manually verified** against the cited source before you act on it. The ledger is a triage queue, not a verdict.

## For UI builders

`demo.html` is the bundled viewer — a PDF.js-based reader that puts each claim's verdict alongside the cited sentence in the source paper. If you're building a different UI on top of the run, treat `data/claims/<id>.json` as the source of truth (schema in `verdict_schema.md`) and `demo.html` as one possible rendering. Directions the current viewer leaves on the table:

- **Side-by-side source reading** — show the cited paper's PDF in a second panel when a claim is focused (the bundle doesn't ship reference PDFs; would need a fetch step).
- **Drift visualization** — highlight `paper_value` vs `claim_value` mismatches inline (numbers that drifted).
- **Remediation queue** — present each non-CONFIRMED claim's `remediation.suggested_edit` as accept/reject/modify cards.
- **History diffs** — when re-running the audit, show diffs between runs (supported in the schema's `history[]` field).
- **Verifier-pass provenance** — the bundle's `data/verifications/` files carry PASS/PARTIAL/FAIL spot-checks; surface those as a confidence signal per claim.
