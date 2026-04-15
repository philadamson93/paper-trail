# paper-trail

LLM workflows for writing and reviewing scientific papers: evidence-grounded claim verification and reference hygiene.

Shipped as Claude Code slash-commands; the `.md` files are plain prompt text, also usable with Codex CLI, Cursor, or direct paste.

## The problem

Scientific papers routinely cite 50–100 references. Verifying that every claim in a manuscript actually matches what its cited source says is laborious — usually deferred until peer review, often incomplete, and the mistakes that slip through propagate into the downstream literature. LLM-assisted writing makes this worse: plausibly-phrased attributions are easier to produce and harder to spot-check.

paper-trail automates the mechanical part: locating the claim in the source, extracting the relevant passage with a page number, classifying how the claim is supported (or not), and recording it in an audit-trail markdown file alongside the manuscript so a reviewer can see the receipts.

## Commands

| Command | Purpose |
|---------|---------|
| `/init-writing-tools` | One-time bootstrap: detect PDF layout and `.bib` files, write config |
| `/fetch-paper` | Download open-access PDFs or surface retrieval prompts for paywalled ones |
| `/ground-claim` | Verify cited claims against source PDFs; maintain a claims ledger |
| `/verify-bib` | BibTeX metadata audit against CrossRef / arXiv / PapersFlow; `--fix` to write corrections |

Each command is a self-contained prompt in `.claude/commands/*.md` — open the file for full detail (invocation modes, taxonomies, constraints). None of them edit the manuscript: issues are surfaced as proposals in a report or ledger for the user to accept.

## Installation

### Option A — Clone + symlink (user-wide, auto-updates)

```bash
git clone https://github.com/philadamson93/paper-trail.git ~/src/paper-trail
mkdir -p ~/.claude/commands
ln -s ~/src/paper-trail/.claude/commands/*.md ~/.claude/commands/
```

### Option B — Vendor-copy (per-project, customizable)

```bash
git clone https://github.com/philadamson93/paper-trail.git /tmp/paper-trail
cp -r /tmp/paper-trail/.claude ./
cp -r /tmp/paper-trail/templates ./
```

### Using with other LLM tools

The `.md` files are plain structured prompts. On Codex CLI, copy the text into your Codex configuration; on Cursor, adapt into `.cursor/rules/`; elsewhere, paste into a chat and ask the model to follow it against your document.

### First run

In your writing project, invoke `/init-writing-tools` once. It detects your layout, asks a few questions, and writes a `claims_ledger.md` with config at the project root.

## MCP requirements

Commands declare capabilities and degrade gracefully — they adapt to whichever tools are available.

- **Essential:** `pdf-reader` (local PDFs with page attribution) and `paper-search` (arXiv / bioRxiv / medRxiv / PubMed download). Multiple community implementations exist — browse [awesome-mcp-servers](https://github.com/modelcontextprotocol/servers) or [mcpservers.org](https://mcpservers.org/) and install via `claude mcp add <name>`. Without these, commands fall back to asking the user to paste relevant sections and download papers manually.
- **Recommended (free):** [PapersFlow MCP](https://github.com/papersflow-ai/papersflow-mcp) — purpose-built citation verification over 474M+ papers. Direct upgrade to `/verify-bib`:

  ```bash
  claude mcp add papersflow --transport streamable-http https://doxa.papersflow.ai/mcp
  ```

- **No MCP:** `pdftotext` from poppler lets commands read PDFs via shell; CrossRef and arXiv REST APIs work via plain HTTP fetches.

## Configuration

Config lives in YAML frontmatter at the top of `claims_ledger.md`, written by `/init-writing-tools`:

```yaml
---
pdf_dir: background/
pdf_naming: "{citekey}.pdf"
bib_files:
  - references.bib
institutional_access: "Stanford library proxy"
last_bootstrap: 2026-04-15
---
```

Edit by hand if your layout changes; no re-init needed.

## License

MIT — see [LICENSE](LICENSE).
