# paper-trail

LLM workflows for writing and reviewing scientific papers: evidence-grounded claim verification and reference hygiene.

Shipped as Claude Code slash-commands; the `.md` files are plain prompt text, also usable with Codex CLI, Cursor, or direct paste.

## The problem

Scientific papers routinely cite 50–100 references. Verifying that every claim in a manuscript actually matches what its cited source says is laborious work — usually deferred until peer review, often incomplete, and the mistakes that slip through propagate into the downstream literature. LLM-assisted writing makes this worse: plausibly-phrased attributions are easier to produce and harder to spot-check.

paper-trail automates the mechanical part of that work — locating the claim in the source, extracting the relevant passage with a page number, classifying how the claim is supported (or not), and recording it in an audit-trail markdown file alongside the manuscript so a reviewer can see the receipts.

## The two workflows

### 1. Evidence grounding (`/ground-claim`)

Maintains a **claims ledger** — a markdown file that sits alongside the manuscript and records, for every cited claim: the claim sentence, the cited paper, the claim *type*, exact supporting text from the source (with page number), a support *level*, and a proposed remediation if support is weaker than needed.

Two non-obvious design choices:

1. **Grouped by source paper, not by manuscript section.** When a paper supports multiple claims, you read it once and verify all of them together. This scales; per-section verification doesn't.
2. **Verbatim source text is stored, not inserted into the draft.** The ledger is an audit artifact — the receipt proving a paraphrase is faithful to the source. The draft paraphrases; the ledger preserves the original so any reviewer can check.

Claims track a hash (or normalized key) of their sentence, so when manuscript text changes, affected entries are flagged `STALE` on the next run automatically.

**Claim type taxonomy:**

| Type | Description | Verification bar |
|------|-------------|------------------|
| DIRECT | "X et al. showed Y" | Near-verbatim match |
| PARAPHRASED | Summarizes paper's argument in our words | Semantic match |
| SUPPORTING | Our claim, paper cited as evidence | Paper's evidence compatible with our framing |
| BACKGROUND | Definition, priority, general context | Paper contains the concept |
| CONTRASTING | "Unlike X, we..." | Paper takes the contrasted position |
| FRAMING | Citation gestures at a broad topic without a specific extractable claim | Paper addresses the topic |

**Support levels:**

| Status | Meaning | Typical remediation |
|--------|---------|---------------------|
| CONFIRMED | Evidence directly supports | — |
| PARTIALLY_SUPPORTED | Supports part, sub-element missing | SPLIT, RESCOPE |
| OVERSTATED | True but wording is stronger than paper's | REWORD |
| UNSUPPORTED | No evidence found on careful read | RECITE, REMOVE |
| CONTRADICTED | Evidence actively contradicts | REMOVE, RECITE — **critical** |
| MISATTRIBUTED | Claim is true, wrong source for it | RECITE |
| STALE | Claim text changed since verification | Re-run `/ground-claim` |
| PENDING | Not yet checked | Run `/ground-claim` |

**Remediation categories** Claude proposes when support is not CONFIRMED:

| Action | When |
|--------|------|
| REWORD | Evidence weaker than language — soften |
| RESCOPE | Narrow the claim so evidence covers it fully |
| RECITE | Wrong citation — propose a better source |
| SPLIT | Composite claim — separate cited from synthesized |
| ADD_EVIDENCE | Add a second citation to cover the gap |
| REMOVE | Not supportable and not essential |
| ACCEPT_AS_FRAMING | Our framing, not paper's — hedge with "informed by" / "following" |

### 2. Reference hygiene (`/verify-bib`)

Two-pass audit of every BibTeX entry against CrossRef, arXiv, and optionally PapersFlow (if installed). Targets error categories that LLM-generated BibTeX actually exhibits:

- **Critical**: fabricated authors, wrong DOIs, chimera entries (key points to one paper, metadata to another)
- **Moderate**: misspelled surnames, wrong pages/volume/year, missing required fields
- **Minor**: arXiv→published upgrades available, missing issue numbers, duplicate keys

Report by default; `--fix` writes corrections to the `.bib` file only (backs up first). Never touches the manuscript.

## Commands

| Command | Purpose |
|---------|---------|
| `/init-writing-tools` | One-time bootstrap: detect PDF layout and .bib files, write config |
| `/fetch-paper` | Download open-access PDFs or surface retrieval prompts for paywalled ones |
| `/ground-claim` | Evidence grounding against source papers (single claim or whole document) |
| `/verify-bib` | BibTeX metadata audit; `--fix` to write corrections |

## Installation and usage

Two install options — pick based on how you want updates to work.

### Option A — Clone + symlink (user-wide, auto-updates)

```bash
git clone https://github.com/philadamson93/paper-trail.git ~/src/paper-trail
ln -s ~/src/paper-trail/.claude/commands/*.md ~/.claude/commands/
```

Every Claude Code project can invoke these. `git pull` in the clone to update.

### Option B — Vendor-copy (per-project, customizable)

From your writing project root:

```bash
git clone https://github.com/philadamson93/paper-trail.git /tmp/paper-trail
cp -r /tmp/paper-trail/.claude ./
cp -r /tmp/paper-trail/templates ./
```

The `.claude/commands/` directory travels with your project. Edit the commands to taste.

### Using with other LLM tools

The `.md` files are plain structured prompts. If you're not on Claude Code:

- **Codex CLI** — copy command text into your Codex configuration.
- **Cursor** — adapt into project rules (`.cursor/rules/` or equivalent).
- **Direct paste** — copy the content of a `.md` file into a chat and ask the model to follow it against your document.

### First run

In your writing project, invoke `/init-writing-tools` once. It detects your layout (bib files, PDF folder, naming convention), asks a few clarifying questions, and writes a `claims_ledger.md` with config at the project root. After that, use `/fetch-paper`, `/ground-claim`, and `/verify-bib` as needed.

## MCP requirements

Commands declare capabilities and degrade gracefully — they adapt to whichever tools are available.

### Essential

- **`pdf-reader`** — reads local PDFs with page-number attribution. Used by `/ground-claim`.
- **`paper-search`** — searches and downloads from arXiv, bioRxiv, medRxiv, PubMed. Used by `/fetch-paper`.

Without these, commands fall back to asking the user to paste relevant PDF sections and download papers manually.

### Recommended (free)

- **PapersFlow MCP** — 474M+ papers via OpenAlex + Semantic Scholar, with a purpose-built citation verification endpoint. Direct upgrade to `/verify-bib`:

  ```bash
  claude mcp add papersflow --transport streamable-http https://doxa.papersflow.ai/mcp
  ```

  Public tools are free, no API key needed.

### Fallback (no MCP)

- `pdftotext` from poppler (`brew install poppler` / `apt install poppler-utils`) lets the commands read PDFs via shell.
- CrossRef and arXiv REST APIs work via plain HTTP fetches — slower but zero setup.

## Configuration

Config lives in YAML frontmatter at the top of `claims_ledger.md` — the ledger is project state, and config travels with it. `/init-writing-tools` writes this on first run:

```yaml
---
pdf_dir: background/
pdf_naming: "{citekey}.pdf"
bib_files:
  - merlinonc/references.bib
institutional_access: "Stanford library proxy"
last_bootstrap: 2026-04-15
---
```

Edit by hand if your layout changes; no re-init needed.

## Design principle: raise, don't fix

**These commands never edit the manuscript.** They read the manuscript, read the source papers, run verification, and write to an audit artifact — the claims ledger. Every problem they find is surfaced in a triage report with:

- Exactly where in the manuscript the issue is (section, line)
- The source-paper page number for the relevant passage
- A concrete suggested edit — as a proposal, not an application

The user reviews and decides what to accept. This keeps control of the prose where it belongs and avoids churn from well-intentioned but wrong auto-fixes. The one exception is `/verify-bib --fix`, which writes only to `.bib` files (never the manuscript), and only when the user explicitly passes the flag.

## A note on "verbatim"

The ledger stores exact source text for verification. **This text does not go in your draft.** The draft paraphrases; the ledger preserves the original as a receipt. Keep excerpts minimal — a sentence or phrase that pins the claim — but quote exactly, including minor extraction artifacts (hyphenation, whitespace), to preserve the audit trail.

## License

MIT — see [LICENSE](LICENSE).
