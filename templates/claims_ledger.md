---
pdf_dir: background/
pdf_naming: "{citekey}.pdf"
bib_files:
  - references.bib
institutional_access: ""
last_bootstrap:  # populated by /init-writing-tools
---

# Claims Ledger

Internal audit artifact for every cited claim in the manuscript. Each entry records:

- The claim sentence (and a hash / normalized key, for stale detection)
- The cited paper
- The claim type (DIRECT / PARAPHRASED / SUPPORTING / BACKGROUND / CONTRASTING / FRAMING)
- Exact source text supporting (or failing to support) the claim, with page number
- A support level (CONFIRMED / PARTIALLY_SUPPORTED / OVERSTATED / OVERGENERAL / CITED_OUT_OF_CONTEXT / UNSUPPORTED / CONTRADICTED / MISATTRIBUTED / INDIRECT_SOURCE / STALE / PENDING)
- A remediation (REWORD / RESCOPE / RECITE / CITE_PRIMARY / SPLIT / ADD_EVIDENCE / REMOVE / ACCEPT_AS_FRAMING) with a concrete suggested edit when support is not CONFIRMED

**The ledger preserves verbatim source text for verification. The manuscript itself paraphrases — the verbatim excerpts here are receipts, not draft content.**

Populated and maintained by `/ground-claim`.

## Summary

| ID | Section | Cite | Type | Support | Source page | Flag | Last verified |
|----|---------|------|------|---------|-------------|------|---------------|

## Details

_Populated per claim by `/ground-claim`._
