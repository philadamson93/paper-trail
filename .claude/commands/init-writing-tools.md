One-time project bootstrap for the paper-trail workflow. Do all of the following:

## 1. Discover existing conventions

Scan the current project:

- Look for `*.bib` files at any depth. Note their paths. **Exclude** `.bib` files inside `background/`, `drafts/`, `scratch/`, `vendor/`, or other nested reference-material subtrees by default — these typically belong to vendored third-party projects, not the manuscript. List only top-level or chapter-level bib files.
- Look for directories commonly used for reference PDFs: `background/`, `papers/`, `refs/`, `pdfs/`, `literature/`. Note which exist and how many PDFs each contains.
- If PDFs are present, cross-reference filenames against cite keys in the detected .bib files to infer the naming convention. Candidates: `{citekey}.pdf`, `{author}{year}.pdf`, `{first-word-of-title}.pdf`, or free-form.
- Check for an existing `claims_ledger.md` at the project root. If present, surface that init has already been run and ask whether to update in place or re-init from scratch.

Report what you found in a brief summary: bib files (paths), PDF directory (path + PDF count), inferred naming convention, whether a ledger already exists.

## 2. Ask focused setup questions

Ask each question, offering the inferred value as the default. Accept a short answer or a one-line override:

1. **PDF directory** — which folder holds reference PDFs? (default: inferred or `background/`)
2. **Naming convention** — how are PDFs named? (default: inferred or `{citekey}.pdf`)
3. **Bib file(s)** — confirm the auto-detected list or provide overrides. For multi-chapter projects with multiple `.bib` files, include all by default (the auditor may need to verify citations from any chapter); list the actively-edited chapter's bib file first if known.
4. **Institutional access** — free-text note on what access the user has for paywalled papers (e.g., "Stanford library proxy", "NIH library", "personal only"). Used by `/fetch-paper` to tailor retrieval prompts.

## 3. Check available tool capabilities

Identify which of the following are reachable in this session. Do not call them yet — just check for availability:

- **PDF reading**: `pdf-reader` MCP, `paper-search` `read_*` tools, or `pdftotext` on PATH.
- **Paper download**: `paper-search` MCP (`download_arxiv`, `download_biorxiv`, `download_medrxiv`, `download_pubmed`), `papersflow` MCP.
- **Reference validation**: `papersflow` MCP (preferred), else fall back to CrossRef / arXiv REST via WebFetch.

Report what's available and what's missing. Point to the relevant README section for missing essentials.

## 4. Write config and scaffold files

Write `claims_ledger.md` at the project root with this YAML frontmatter header:

```yaml
---
pdf_dir: <chosen path>
pdf_naming: "<chosen pattern>"
bib_files:
  - <path1>
  - <path2>
institutional_access: "<user input>"
last_bootstrap: <today's ISO date>
---
```

Below the frontmatter, add a short explanatory header and empty Summary / Details sections. If `templates/claims_ledger.md` is available in the package, use it as the base and fill in the frontmatter values.

Create the configured PDF directory if it doesn't exist (`mkdir -p`).

When copying from `templates/claims_ledger.md`, replace any placeholder values (e.g., `last_bootstrap` empty) with real values before writing — the ledger should never contain literal placeholders after init completes.

## 5. PDF coverage check

After config is written, parse the first-listed `.bib` file and count cite keys. Compare against PDFs in `pdf_dir` (applying the configured naming pattern). Report coverage:

```
PDF coverage: 17/18 cite keys have matching PDFs in background/.
  Missing: xu20253dino
  → Run /fetch-paper xu20253dino to retrieve.
```

Surfacing missing PDFs at bootstrap lets the user resolve them before `/ground-claim` runs — cheaper than discovering mid-audit.

## 6. Confirm

Print a one-line summary of what was set up and what comes next:

```
Bootstrap complete.
  Ledger:   <path>
  PDF dir:  <path> (N existing PDFs, K missing)
  Bib:      <path>
Next: /fetch-paper <citekey> to grab a missing PDF, or /ground-claim path/to/chapter.tex to verify citations.
```

## What not to do

- Don't do any grounding, downloading, or auditing yet — that's what the other commands are for.
- Don't overwrite an existing `claims_ledger.md` without confirming first.
- Don't leave literal template placeholders (e.g., `YYYY-MM-DD`) in the written ledger — fill them with real values or empty strings.
- Don't hard-code paths; everything the other commands need must come from the ledger frontmatter so users can move files without breaking the workflow.
