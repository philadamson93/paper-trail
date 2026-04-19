# paper-trail demo — UI team handoff

A complete audit run of one real paper (Adamson et al. 2025, *Magnetic Resonance in Medicine*) processed through the paper-trail pipeline. The included reference UI (`demo.html`) shows one way to surface the verdicts; you are encouraged to redesign it.

## What's in this bundle

```
demo.html              Reference UI. Open in a browser, no server needed.
input-paper.pdf        The audited paper itself. The audit is *about* this paper.
paper.txt              Plaintext extraction of input-paper.pdf, used by demo.html
                       to render the manuscript with inline citation markers.
refs.bib               Bibliography parsed verbatim from input-paper.pdf.
refs.verified.bib      Same bibliography, enriched with DOIs / metadata
                       resolved via CrossRef during the audit.
verdict_schema.md      Schema spec for the JSON files in data/. Read this first
                       if you're building anything off the data.
data/
  claims/<id>.json         88 verdict files — one per claim. SOURCE OF TRUTH.
  evidence/<id>.json       49 extractor outputs (Pass 1; pre-verdict).
  verifications/<id>.json  5 verifier spot-check results.
```

## What is "a claim"?

A *claim* is one cited assertion in the manuscript — a sentence that cites at least one reference. Each `(sentence, citekey)` pair gets one verdict file. Composite claims like *"ResNet50 pretrained on 1.4M medical images including 670k MRI"* break down into multiple **sub-claims** so the UI can highlight per-fact drift (e.g., "1.4M" vs paper's actual "1.35M").

## How to use the data

Each file under `data/claims/` looks like:

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
    },
    ...
  ],
  "overall_verdict": "CONFIRMED_WITH_MINOR",
  "overall_flag": "MINOR",
  "remediation": {"category": "REWORD", "suggested_edit": "..."},
  "attestation": {...},
  "co_cite_context": {...}
}
```

Cross-reference `claim_id` → `citekey` → entry in `refs.bib` for full reference metadata. The `refs.bib` `refnum` field maps to the reference number printed in the manuscript (e.g., the "6" in `mason2020,6`).

Full schema: `verdict_schema.md` in this directory.

## Verdict categories

Twelve verdicts in the enum, ordered roughly worst → best:

- `CONTRADICTED` — paper actively says the opposite (red)
- `UNSUPPORTED` — no evidence found despite thorough search
- `MISATTRIBUTED` — claim is true but this isn't the source
- `INDIRECT_SOURCE` — paper has the fact but credits another primary
- `CITED_OUT_OF_CONTEXT` — passage exists but used in a different context
- `PARTIALLY_SUPPORTED` — some sub-claims hold, others don't
- `OVERGENERAL` — paper proves it in narrow scope, manuscript generalizes beyond
- `OVERSTATED` / `OVERSTATED_MILD` — strength drift (manuscript stronger than source)
- `CONFIRMED_WITH_MINOR` — supported with small caveats
- `CONFIRMED` — clean match
- `AMBIGUOUS` — adjudicator couldn't confidently pick; awaits human triage
- `PENDING` — source PDF unavailable (paywalled); not yet adjudicated

39 of the 88 entries in this bundle are `PENDING` — the audit couldn't fetch their source PDFs under personal access. The other 49 have real verdicts.

## Suggested UI directions

The reference `demo.html` does the obvious thing: highlight citation markers in the paper text, popup on hover with verdict + claim + evidence. Other things you might explore:

- **Side-by-side reading view** — paper text on the left, currently-hovered claim's source excerpt on the right.
- **Filterable claim list** — surface CRITICAL flags first, let user filter by verdict, citekey, or section.
- **Drift visualization** — highlight `paper_value` vs `claim_value` mismatches inline (numbers that drifted).
- **Remediation queue** — present each non-CONFIRMED claim's `remediation.suggested_edit` as accept/reject/modify cards for the author.
- **Evidence inspector** — let user click an evidence excerpt to navigate to the source paper section. (Bundle doesn't include reference PDFs, so this would require either fetching them or letting the user provide them.)
- **Verdict comparison** — when re-running the audit, show diffs between successive runs (history is supported in the schema's `history[]` field).

## Headline catches in this run (as starting talking points)

These six claims are the most consequential findings — useful for showcasing what the audit catches:

| Claim ID | Citekey | Verdict | Why interesting |
|---|---|---|---|
| C055 | miao2008 | MISATTRIBUTED | HFEN/LoG params cited to wrong paper |
| C069 | vandersluijs2023 | CONTRADICTED | "L2 + perceptual + adversarial" — paper has KL not L2 |
| C072 | mason2020 | CONTRADICTED | Mason described as "natural images" — actually MR images |
| C040 | huang2023 | CITED_OUT_OF_CONTEXT | Paper concludes opposite to manuscript framing |
| C056 | chen2022 | UNSUPPORTED | Listed metrics not in cited paper |
| C070 | desai2021 | UNSUPPORTED | Cited for SSFD-loss; paper uses L1 |

## Reference UI walkthrough

`demo.html` is self-contained (~580KB; all 88 verdicts inlined as JSON). Open it in any browser — no build step, no server.

- Citation markers in the paper body are colored by verdict severity
- Hover or click a marker → popup with reference info, claim text, sub-claim breakdown, evidence excerpts, remediation
- Reference list at bottom; verdict legend at top

The visual design is intentionally minimal — meant as a clear data viewer, not a finished product.

## Notes / caveats

- The bundle does NOT include the reference PDFs (the 31 cited papers). The verdicts capture every excerpt the UI needs; reference PDFs are 200MB+ and unnecessary for the UI.
- 5 claims have verifier spot-check results (`data/verifications/`); the other 44 grounded claims do not. Verifier coverage will be expanded in a future run.
- `paper_value` / `claim_value` fields in `sub_claims` are populated when there's a numerical or quantitative drift between paper and manuscript. They're the most "obviously visualize-able" sub-fields.
- Source: this bundle was produced by `paper-trail v2` (orchestrator + dispatch templates in `.claude/` of the parent repo). Schema versioned at `1.0`. Schema changes will bump the version field.
