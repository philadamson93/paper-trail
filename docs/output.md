# Outputs & verdicts

Every `/paper-trail` run produces a bundle of machine- and human-readable artifacts.

## Files

- **`ledger/claims/<id>.json`** — one verdict file per claim. This is the source of truth: claim text, sub-claim breakdown, verdicts, evidence quotes, attestation log, remediation. Schema: [`.claude/specs/verdict_schema.md`](../.claude/specs/verdict_schema.md).
- **`ledger.md`** — human-readable view rendered from the JSONs. Hand-edits are overwritten on re-render; annotate the JSON's `nuance` or `history[]` fields instead.
- **`demo.html`** — PDF.js viewer with the paper on the left and a filterable claim ledger on the right. Click a claim to jump to its spot in the PDF; click a citation marker in the PDF to highlight matching claims. The PDF is inlined by default so the file opens from `file://` with no setup; pass `--external-pdf` to the renderer for a lightweight HTML that fetches the PDF alongside.
- **`pdfs/<citekey>.pdf`** + **`pdfs/<citekey>/`** — fetched source PDFs and their GROBID ingest handles (per-section text, figures, meta).
- **`refs.bib`** / **`refs.verified.bib`** — PDF-parsed bibliography and its CrossRef-enriched counterpart.
- **`parse_report.md`** — parser diagnostics (reader mode only).
- **`trace/*.jsonl`** — per-subagent dispatch log, grep-able for observability.

## Verdicts

Every sub-claim gets exactly one verdict. A claim's overall verdict rolls up from its sub-claims. Full rubric: [`.claude/specs/verdict_schema.md`](../.claude/specs/verdict_schema.md).

| Verdict | Meaning |
|---|---|
| `CONFIRMED` | Evidence directly supports the sub-claim |
| `CONFIRMED_WITH_MINOR` | Supported with small caveats (overall-only) |
| `OVERSTATED_MILD` / `OVERSTATED` | True, but the manuscript's wording is stronger than the source's — *strength* drift |
| `OVERGENERAL` | True in the paper's narrow scope; manuscript generalizes beyond — *scope* drift |
| `PARTIALLY_SUPPORTED` | Some sub-claims hold; others don't |
| `CITED_OUT_OF_CONTEXT` | Passage exists but is used in a materially different context |
| `UNSUPPORTED` | No evidence found on careful read (≥3 phrasings, full section checklist) |
| `CONTRADICTED` | Evidence actively contradicts the claim — critical |
| `MISATTRIBUTED` | Claim is true but this isn't the source for it |
| `INDIRECT_SOURCE` | Paper has the fact but itself credits another primary — reference-hygiene issue |
| `AMBIGUOUS` | Agent read fully but couldn't confidently pick between candidate verdicts; awaits user triage |
| `PENDING` | Not yet checked (paywall / ingest error) — carries a `NEEDS_PDF` / `NEEDS_OCR` flag |

## Remediation

When a verdict isn't `CONFIRMED`, every entry carries a suggested fix: `REWORD` (soften strength), `RESCOPE` (narrow the claim), `RECITE` (wrong source; suggest a different one), `CITE_PRIMARY` (replace with the primary source the cited paper itself credits), `SPLIT`, `ADD_EVIDENCE`, `REMOVE`, or `ACCEPT_AS_FRAMING`.
