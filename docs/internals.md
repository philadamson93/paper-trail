# Internals

## Component commands

`/paper-trail` is the orchestrator. Four component commands are individually invocable:

| Command | Purpose |
|---|---|
| [`/init-writing-tools`](../.claude/commands/init-writing-tools.md) | One-time author-mode bootstrap: detect `.bib` + PDF layout, write `claims_ledger.md` config. |
| [`/verify-bib`](../.claude/commands/verify-bib.md) | BibTeX metadata audit against CrossRef / arXiv / PapersFlow; `--fix` writes corrections. |
| [`/fetch-paper`](../.claude/commands/fetch-paper.md) | Download open-access PDFs or surface retrieval prompts for paywalled ones. |
| [`/ground-claim`](../.claude/commands/ground-claim.md) | Two-pass grounding of a single claim or a whole `.tex` file. Also provides `--triage`. |

None of these edits the manuscript. Every issue is surfaced as a proposal for the user to accept.

## Where the spec lives

The slash-command files and schemas *are* the spec, not a wrapper around hidden code:

- **Orchestrator phases (0 → 4) + invocation flags** — [`.claude/commands/paper-trail.md`](../.claude/commands/paper-trail.md).
- **Verdict JSON schema + rollup rules + validation** — [`.claude/specs/verdict_schema.md`](../.claude/specs/verdict_schema.md).
- **Ingest handle layout + GROBID pipeline** — [`.claude/specs/ingest.md`](../.claude/specs/ingest.md) and [`.claude/scripts/ingest_pdf.py`](../.claude/scripts/ingest_pdf.py).
- **Dispatch prompts** (extractor / adjudicator / verifier) — [`.claude/prompts/`](../.claude/prompts/).
- **HTML demo renderer** — [`.claude/scripts/render_html_demo.py`](../.claude/scripts/render_html_demo.py).
