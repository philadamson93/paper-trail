# Internals

## Component commands

`/paper-trail` is the orchestrator. Four component commands are individually invocable:

| Command | Purpose |
|---|---|
| [`/paper-trail-init`](../src/commands/paper-trail-init.md) | Probe + optionally install system dependencies (pdftotext, Docker, GROBID, `papersflow` MCP). Auto-invoked by `/paper-trail`'s preflight when blocking deps are missing. |
| [`/init-writing-tools`](../src/commands/init-writing-tools.md) | One-time author-mode bootstrap: detect `.bib` + PDF layout, write `claims_ledger.md` config. |
| [`/verify-bib`](../src/commands/verify-bib.md) | BibTeX metadata audit against CrossRef / arXiv / PapersFlow; `--fix` writes corrections. |
| [`/fetch-paper`](../src/commands/fetch-paper.md) | Download open-access PDFs or surface retrieval prompts for paywalled ones. |
| [`/ground-claim`](../src/commands/ground-claim.md) | Two-pass grounding of a single claim or a whole `.tex` file. Also provides `--triage`. |

None of these edits the manuscript. Every issue is surfaced as a proposal for the user to accept.

## Where the spec lives

The slash-command files and schemas *are* the spec, not a wrapper around hidden code:

- **Orchestrator phases (0 → 4) + invocation flags** — [`src/commands/paper-trail.md`](../src/commands/paper-trail.md).
- **Verdict JSON schema + rollup rules + validation** — [`src/specs/verdict_schema.md`](../src/specs/verdict_schema.md).
- **Ingest handle layout + GROBID pipeline** — [`src/specs/ingest.md`](../src/specs/ingest.md) and [`src/scripts/ingest_pdf.py`](../src/scripts/ingest_pdf.py).
- **Pre-dispatch claim validator** (`TEXT_ANCHOR_MISSING`, `FRONT_MATTER_ANCHOR`, `CITEKEY_MARKER_MISMATCH`) — [`src/scripts/validate_claims.py`](../src/scripts/validate_claims.py).
- **Dispatch prompts** (extractor / adjudicator / verifier) — [`src/prompts/`](../src/prompts/).
- **HTML demo renderer** — [`src/scripts/render_html_demo.py`](../src/scripts/render_html_demo.py).
