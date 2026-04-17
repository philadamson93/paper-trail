<p align="center">
  <img src="assets/logo.jpg" alt="paper-trail" width="180">
</p>

# paper-trail

LLM workflows for writing and reviewing scientific papers: evidence-grounded claim verification and reference hygiene.

Shipped as Claude Code slash-commands; the `.md` files are plain prompt text, also usable with Codex CLI, Cursor, or direct paste. 

UI + API key version coming soon.

## Why `paper-trail`

Scientific papers routinely cite 50–100 references. Verifying that every claim in a manuscript actually matches what its cited source says is laborious, mistake-prone, and the mistakes that slip through propagate into the downstream literature. LLM-assisted writing makes this worse, where plausibly-phrased attributions are easier to produce and harder to spot-check.

`paper-trail` helps automate this: locating the claim in the source, extracting the relevant passage with a page number, classifying how the claim is supported (or not), and recording it in an audit-trail markdown file alongside the manuscript so an author or reviewer can see the receipts.

## Getting started — `/paper-trail`

`paper-trail` exposes a single entry point: the **`/paper-trail`** slash command. It operates in two workflow modes:

- **Reader mode** (default) — hand it a PDF of someone else's paper (peer review, literature vetting, skeptical reading). It extracts the references, verifies the bibliography, fetches open-access source PDFs, and grounds every in-text citation against its source. Writes a self-contained audit artifact to `./paper-trail-<stem>/`.
- **Author mode** (`--author`) — point it at your own in-progress manuscript (a `.tex` file + `.bib` + source PDFs in a directory). It audits the bibliography, fetches any missing sources, and grounds every cited claim. Writes to `claims_ledger.md` at the project root.

Both modes share the per-claim workflow, the same severity taxonomies, and the same attestation-verifier and ambiguity-triage passes.

### Invoke

```bash
# Reader mode
/paper-trail                                # fully interactive; prompts for everything
/paper-trail <path-to-pdf>                  # reader mode against that PDF
/paper-trail <path-to-pdf> --skip-paywalled # don't block on paywalled refs

# Author mode
/paper-trail --author                       # author mode against the current writing project
/paper-trail --author path/to/document.tex  # author mode against a specific manuscript

# Either mode
/paper-trail [...] --scope=single           # ground one claim the user describes
/paper-trail [...] --triage                 # interactive triage for AMBIGUOUS entries
```

See [`.claude/commands/paper-trail.md`](.claude/commands/paper-trail.md) for the full spec (all flags, phase structure, taxonomies, rigor requirements).

## What `/paper-trail` produces

Every cited claim is recorded in the ledger with three orthogonal values plus evidence. The taxonomies:

### Claim type — *what kind of attribution is being made*

| Type | Meaning | Evidence bar |
|------|---------|--------------|
| `DIRECT` | Attributes a specific finding to the paper ("X et al. showed Y") | Near-verbatim match |
| `PARAPHRASED` | Summarizes the paper's argument in our words | Semantic match |
| `SUPPORTING` | Our claim; paper cited as evidence for it | Paper's evidence compatible with our framing |
| `BACKGROUND` | Definition, priority of invention, general context | Paper contains the concept |
| `CONTRASTING` | "Unlike X, we…" | Paper takes the contrasted position |
| `FRAMING` | Broad-topic gesture; no specific sentence-level claim extracted | Paper addresses the topic |

### Support level — *how well the evidence backs the claim*

| Support level | Meaning |
|---------------|---------|
| `CONFIRMED` | Evidence directly supports the claim |
| `PARTIALLY_SUPPORTED` | Supports part; a sub-element is missing or weaker |
| `OVERSTATED` | True, but our wording is stronger than the paper's — about *strength* |
| `OVERGENERAL` | True within the paper's narrow scope, but our claim generalizes beyond it — about *scope* |
| `CITED_OUT_OF_CONTEXT` | Passage exists in the paper, but used in a materially different context than it originally appears |
| `UNSUPPORTED` | No evidence found on careful read |
| `CONTRADICTED` | Evidence actively contradicts the claim (critical) |
| `MISATTRIBUTED` | Claim is true, but this isn't the source for it |
| `INDIRECT_SOURCE` | Paper contains the fact but itself credits another source for it — reference-hygiene issue |
| `AMBIGUOUS` | Agent read fully but could not confidently pick between 2+ candidate verdicts; awaits user triage |
| `STALE` | Claim text changed since last verification |
| `PENDING` | Not yet checked (pre-flight, or blocked on a flag like `NEEDS_PDF` / `NEEDS_OCR` / `NEEDS_SUPPLEMENT`) |

### Remediation — *concrete suggested fix when support isn't `CONFIRMED`*

| Remediation | Action |
|-------------|--------|
| `REWORD` | Soften language to match evidence strength |
| `RESCOPE` | Narrow the claim so evidence covers it fully |
| `RECITE` | Wrong citation entirely; suggest a different source |
| `CITE_PRIMARY` | Replace with the primary source the cited paper itself credits (dug out of that paper's own bibliography) |
| `SPLIT` | Separate a composite claim from synthesized framing |
| `ADD_EVIDENCE` | Add a second citation to cover what the first doesn't |
| `REMOVE` | Not supportable and not essential |
| `ACCEPT_AS_FRAMING` | Move the citation scope or hedge ("informed by", "following") |

## Why these verdicts are trustworthy

- **Full-paper attestation.** Before any `UNSUPPORTED` or `CONTRADICTED` verdict, agents must record a section-by-section read checklist, a minimum of 3 distinct phrasings searched, and the closest adjacent passage. No abstract-only shortcuts.
- **Independent attestation verifier.** Every grounding verdict is spot-checked by a separate subagent against the cited PDF to catch fabricated logs (`UNVERIFIED_ATTESTATION` flag).
- **Chunked-read for long PDFs.** Source papers over 25 pages are read section-by-section with per-section attestation — avoids silent context truncation.
- **Configurable fetch substitution.** When a target DOI is paywalled but a related preprint exists, `--fetch-substitute=<never|ask|always>` controls whether to accept the substitute; every substitution is logged.

Full behavior lives in the command prompt at [`.claude/commands/paper-trail.md`](.claude/commands/paper-trail.md) — descriptive of the workflow, not a wrapper around hidden code.

## Under the hood (component commands)

`/paper-trail` orchestrates four component commands. Most users should just use `/paper-trail` — but these are individually invocable for advanced / targeted use.

| Component | Purpose |
|-----------|---------|
| [`/init-writing-tools`](.claude/commands/init-writing-tools.md) | One-time bootstrap for author mode: detect `.bib` / PDF layout, write `claims_ledger.md` config. Run once per writing project. |
| [`/verify-bib`](.claude/commands/verify-bib.md) | BibTeX metadata audit against CrossRef / arXiv / PapersFlow; `--fix` to write corrections. |
| [`/fetch-paper`](.claude/commands/fetch-paper.md) | Download open-access PDFs or surface retrieval prompts for paywalled ones. |
| [`/ground-claim`](.claude/commands/ground-claim.md) | Verify a specific claim (or a whole `.tex` file's citations) against source PDFs; maintain the claims ledger. Also provides the `--triage` invocation for resolving `AMBIGUOUS` entries. |

None of these edit the manuscript — issues are surfaced as proposals for the user to accept.

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

- **Reader mode:** just `/paper-trail <path-to-pdf>`. No setup required.
- **Author mode:** in your writing project, run `/paper-trail --author` — if no `claims_ledger.md` exists it will prompt you to run `/init-writing-tools` first (a one-time bootstrap that detects your `.bib`/PDF layout and writes config).

## MCP requirements

Commands declare capabilities and degrade gracefully — they adapt to whichever tools are available.

- **Essential:** `pdf-reader` (local PDFs with page attribution) and `paper-search` (arXiv / bioRxiv / medRxiv / PubMed download). Multiple community implementations exist — browse [awesome-mcp-servers](https://github.com/modelcontextprotocol/servers) or [mcpservers.org](https://mcpservers.org/) and install via `claude mcp add <name>`. Without these, commands fall back to asking the user to paste relevant sections and download papers manually.
- **Recommended (free):** [PapersFlow MCP](https://github.com/papersflow-ai/papersflow-mcp) — purpose-built citation verification over 474M+ papers. Direct upgrade to `/verify-bib`:

  ```bash
  claude mcp add papersflow --transport streamable-http https://doxa.papersflow.ai/mcp
  ```

- **No MCP:** `pdftotext` from poppler lets commands read PDFs via shell; CrossRef and arXiv REST APIs work via plain HTTP fetches.

## Configuration

Relevant only to author mode. Reader mode is self-contained per run and needs no config.

Config lives in YAML frontmatter at the top of `claims_ledger.md`, written by `/init-writing-tools`:

```yaml
---
pdf_dir: background/
pdf_naming: "{citekey}.pdf"
bib_files:
  - references.bib
institutional_access: "university library proxy"
last_bootstrap: 2026-04-15
---
```

Edit by hand if your layout changes; no re-init needed.

## Examples

- [`examples/claims_ledger_example.md`](examples/claims_ledger_example.md) — sample **author-mode** claims ledger with seven entries spanning different claim types (DIRECT, FRAMING), support levels (CONFIRMED, OVERSTATED, CONTRADICTED, PARTIALLY_SUPPORTED), and remediation categories (REWORD, RESCOPE). Includes a multi-cite case and a real-world typo catch.
- [`examples/paper-trail-dfd-adamson-2025/`](examples/paper-trail-dfd-adamson-2025/) — real **reader-mode** `/paper-trail` audit on a published paper. Contains the parsed 56-entry `refs.bib`, parser diagnostics, a 6-claim ledger, and a walkthrough of the catches: a CRITICAL author-swap bib error, two `CITED_OUT_OF_CONTEXT` findings, and a scope-drift `OVERGENERAL`. Source PDFs are not included.

## License

MIT — see [LICENSE](LICENSE).
