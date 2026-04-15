# paper-trail

A small set of Claude Code slash-commands for rigorous scientific writing with LLMs: evidence-grounded claim verification, reference hygiene, and submission-guide compliance. Distilled from a real thesis project, packaged for lab sharing. Not plug-and-play — a starting point you fork to your own conventions.

The name is a double meaning: the commands build an **audit trail** for every cited claim in your **paper**.

## Core principle: raise, don't fix

**These commands never edit the manuscript.** They read the manuscript, read the source papers, run verification, and write to audit artifacts (claims ledger, compliance table). Every problem they find is surfaced in a triage report with:

- Exactly where in the manuscript the issue is (section, line)
- The **source-paper page number** for the relevant passage (for citation issues)
- A concrete suggested edit — as a proposal, not an application

The user reviews the report and decides what to accept. This keeps control of the prose where it belongs and avoids churn from well-intentioned but wrong auto-fixes. The one exception is `/verify-bib --fix`, which only ever writes to `.bib` files (not the manuscript), and only when the user explicitly passes the flag.

## What this addresses

LLMs produce fluent, well-structured, subtly wrong text. Fluency is load-bearing; errors hide in plausible prose. These workflows each target one specific failure mode that tends to appear only at submission time — when it's most expensive to fix.

| Failure mode | Symptom at submission | Workflow |
|--------------|----------------------|----------|
| Hallucinated or overstated attributions | A cited paper doesn't actually support the claim, or supports a weaker version | `/ground-claim` |
| Fabricated or stale BibTeX metadata | Wrong authors, wrong DOI, arXiv preprint now published, duplicate keys | `/verify-bib` |
| Submission-guideline gaps discovered late | Margins, missing sections, co-author attribution, file naming | `/check-style` |

## The three workflows

### 1. Evidence grounding (`/ground-claim`)

Maintains a **claims ledger** — a markdown file that sits alongside the manuscript and records, for every cited claim: the claim sentence, the cited paper, the claim *type*, exact supporting text from the source (with page number), a support *level*, and a proposed remediation if support is weaker than needed.

Two non-obvious design choices:

1. **Grouped by source paper, not by manuscript section.** When a paper supports multiple claims, you read it once and verify all of them together. This scales; per-section verification doesn't.
2. **Verbatim source text is stored, not inserted into the draft.** The ledger is an audit artifact — the receipt proving a paraphrase in the manuscript is faithful to the source. The draft paraphrases; the ledger preserves the original text so any reviewer can check.

The ledger uses sentence hashes: when manuscript text changes, affected entries are flagged `STALE` automatically on the next run.

**Claim type taxonomy** (assigned per claim):

| Type | Description | Verification bar |
|------|-------------|------------------|
| DIRECT | "X et al. showed Y" | Near-verbatim match |
| PARAPHRASED | Summarizes paper's argument in our words | Semantic match |
| SUPPORTING | Our claim, paper cited as evidence | Paper's evidence compatible with our framing |
| BACKGROUND | Definition, priority, general context | Paper contains the concept |
| CONTRASTING | "Unlike X, we..." | Paper actually takes the contrasted position |

**Support levels:**

| Status | Meaning | Typical remediation |
|--------|---------|---------------------|
| CONFIRMED | Evidence directly supports | — |
| PARTIALLY_SUPPORTED | Supports part, sub-element missing | SPLIT, RESCOPE |
| OVERSTATED | True but our wording is stronger than paper's | REWORD |
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

Report by default; `--fix` to write corrections (backs up first).

### 3. Compile-time compliance (`/check-style`)

Point the skill at your submission guide URL (thesis template, journal author info, conference style sheet). It builds a requirement-indexed compliance table keyed to source URLs, marks each `COMPLIANT` / `VERIFY` / `NOT-COMPLIANT`, and re-runs on demand. Compile + visual PDF scan for margins, widows, orphans.

## Skills

| Skill | Purpose |
|-------|---------|
| `/init-writing-tools` | One-time bootstrap: detect PDF layout and .bib files, write config |
| `/fetch-paper` | Download open-access PDFs or surface retrieval prompts for paywalled ones |
| `/ground-claim` | Evidence grounding against source papers (single claim or whole document) |
| `/verify-bib` | BibTeX metadata audit; `--fix` to write corrections |
| `/check-style` | Submission-guide compliance table + compile checks |

## Installation

Two options, pick based on how you want updates to work.

### Option A — Clone + symlink (user-wide, auto-updates)

```bash
git clone https://github.com/philadamson93/paper-trail.git ~/src/paper-trail
ln -s ~/src/paper-trail/.claude/commands/*.md ~/.claude/commands/
```

Every project can invoke these. `git pull` in the clone to update.

### Option B — Vendor-copy (per-project, customizable)

From your writing project root:

```bash
git clone https://github.com/philadamson93/paper-trail.git /tmp/paper-trail
cp -r /tmp/paper-trail/.claude ./
cp -r /tmp/paper-trail/templates ./
```

The `.claude/commands/` directory travels with your project. Edit the commands to taste — you own them now.

### After install, in your writing project

```
/init-writing-tools
```

This is the only command you always run first. It detects your conventions, writes config, and scaffolds the ledger.

## MCP requirements

Skills declare capabilities and degrade gracefully — they adapt to whichever tools are available.

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

- `pdftotext` from poppler (`brew install poppler` / `apt install poppler-utils`) lets the skills read PDFs via shell.
- CrossRef and arXiv REST APIs work via plain HTTP fetches — slower but zero setup.

## Configuration

Config lives in YAML frontmatter at the top of `claims_ledger.md` — the ledger is project state, and config travels with it. `/init-writing-tools` writes this on first run:

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

Edit this by hand if your layout changes; no re-init needed.

## A note on "verbatim"

The ledger stores exact source text for verification. **This text does not go in your draft.** The draft paraphrases; the ledger preserves the original as a receipt. Keep excerpts minimal — a sentence or phrase that pins the claim — but quote exactly, including minor extraction artifacts (hyphenation, whitespace), to preserve the audit trail.

## Adapt, don't adopt

These commands are a starting point. The project they came from needed grouping by paper, five claim types, and an eight-status support taxonomy. Yours may not. Trim, extend, rename, replace — the point is the workflow, not the specific labels.

## License

MIT — see [LICENSE](LICENSE).
