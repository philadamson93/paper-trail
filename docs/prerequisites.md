# Prerequisites

Commands adapt to whichever tools are available, but quality is proportional to what's installed. The easiest path: ask Claude to install these for you.

```
claude "set up paper-trail prereqs on this machine"
```

Claude will install / start what's missing below and verify each is reachable.

## GROBID (recommended)

Turns cited PDFs into clean per-section text + figures for Phase 2.5 ingest.

```bash
docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2
```

Without GROBID, the pipeline falls back to `pdftotext` (flat text, no per-section structure; figures still extracted). Serviceable for most claim types; DIRECT claims against numerical tables are weaker.

## PDF fetching

`paper-trail` can only automatically fetch **open-access** PDFs (arXiv / bioRxiv / medRxiv / PubMed Central / CrossRef OA links). Paywalled references are stubbed and marked `PENDING` with a `NEEDS_PDF` flag — you can drop the PDF in by hand (institutional access, ILL, authors' websites) and re-run to ground the associated claims. Nothing bypasses paywalls.

If you routinely have institutional access, point an `pdf-reader` MCP or a local PDF directory at the ingest path and the orchestrator will pick them up.

## Claude Code MCPs (optional)

- **`pdf-reader`** — local PDFs with page attribution. Browse [awesome-mcp-servers](https://github.com/modelcontextprotocol/servers) or [mcpservers.org](https://mcpservers.org/).
- **`paper-search`** — arXiv / bioRxiv / medRxiv / PubMed downloads.
- **`papersflow`** — purpose-built citation verification over 474M+ papers. Direct upgrade to `/verify-bib`:

  ```bash
  claude mcp add papersflow --transport streamable-http https://doxa.papersflow.ai/mcp
  ```

## Fallbacks

`pdftotext` (from poppler) + plain HTTP fetches to CrossRef / arXiv cover the no-MCP path.
