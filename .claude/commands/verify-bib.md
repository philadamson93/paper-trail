Audit BibTeX entries against authoritative sources (CrossRef, arXiv, PapersFlow if available). Categorize errors by severity. Optionally write corrections to the `.bib` file only.

## Core principle: raise, don't fix

By default this command reports issues and proposes fixes — it does not apply them. The user reviews and decides. Only with an explicit `--fix` flag will the command write corrections, and even then **only to the `.bib` file** (with a timestamped backup). The manuscript (`.tex`) is never touched by this command under any circumstances.

## Invocation forms

- `/verify-bib <citekey>` — single entry
- `/verify-bib path/to/references.bib` — whole file
- `/verify-bib path/to/file.bib --fix` — write corrections in-place (creates timestamped backup first)

## Data sources (first hit wins per field)

1. **PapersFlow MCP** if available — purpose-built citation verification endpoint; covers 474M+ papers via OpenAlex + Semantic Scholar.
2. **CrossRef API** via WebFetch: `https://api.crossref.org/works/<DOI>` (when a DOI is present) or the search endpoint for title-based lookup.
3. **arXiv API** via WebFetch for arXiv entries: `https://export.arxiv.org/api/query?id_list=<id>`.
4. **Semantic Scholar** (via PapersFlow or direct) as fallback for entries missing DOIs.

## Per-entry checks

For each BibTeX entry:

### Existence
- Does the DOI resolve? Does the arXiv ID exist? Does the title match a paper at the claimed venue + year?
- If none: likely fabricated. Mark **CRITICAL**.

### Author names
- Compare every author surname and initial against the authoritative source.
- Most or all authors wrong → **CRITICAL** (likely chimera: cite key + metadata describe different papers).
- Subset misspelled → **MODERATE**.

### Bibliographic fields
- **Title**: match allowing case and minor punctuation differences. Major mismatch → chimera → **CRITICAL**.
- **Journal** / **booktitle**, **volume**, **issue**, **pages**, **year**: all match authoritative source?
- **Required fields** by entry type:
  - `@article`: author, title, journal, year, volume, pages (issue if available)
  - `@inproceedings`: author, title, booktitle, year
  - `@book`: author/editor, title, publisher, year
  - `@misc`: author, title, year, howpublished/url
  - Missing → **MODERATE**.

### Preprint status
- If entry points to an arXiv preprint, check CrossRef for a peer-reviewed version.
- Published version found → **MINOR** — suggest arXiv→published upgrade.
- When upgrading: update journal/volume/pages/DOI/year. **Retain** the arXiv eprint field so the preprint version remains traceable.

### Duplicates
- Group entries by DOI (if present) and by normalized title.
- Distinct cite keys with the same DOI or title → **MINOR** — flag for the user to consolidate.

## Severity summary

| Severity | Examples |
|----------|----------|
| CRITICAL | Non-resolving DOI, fabricated/chimera entry, wrong DOI, majority-wrong author list |
| MODERATE | Misspelled author names, wrong pages/volume/year, missing required fields |
| MINOR | arXiv→published upgrade available, missing issue/DOI when one exists, duplicate keys |

## Report format

Output a markdown report:

```markdown
## BibTeX Audit — <path> (<N> entries)

### CRITICAL (X)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Fix: <specific correction>

### MODERATE (Y)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Fix: <specific correction>

### MINOR (Z)
- `<citekey>`: <what's wrong>
  Source: <authoritative URL>
  Suggestion: <specific correction>

### Verified clean (K)
`<citekey1>`, `<citekey2>`, ...

### Unverifiable (U)
`<citekey>`: <reason API could not be queried>
```

## --fix mode

When invoked with `--fix`:

1. Back up the .bib file to `<file>.bib.bak.<YYYYMMDD-HHMMSS>` before any edits.
2. Apply **CRITICAL** and **MODERATE** corrections in-place, preserving per-entry formatting and whitespace where possible.
3. **Leave MINOR issues for the user** — these often need human judgment (which arXiv→published version to prefer, which of two duplicate keys to keep). List them in the report.
4. Print a diff summary: "Fixed N entries across <file>.bib. M MINOR issues left for manual review. Backup: <path>."

Never apply `--fix` without the explicit flag, and never apply it silently.

## Do not

- **Never edit the manuscript (`.tex`) file.** This command touches `.bib` files only, and only in `--fix` mode.
- Never silently accept an unverified result. If an API is unreachable or returns ambiguous data, mark the entry `UNVERIFIED` rather than "clean".
- Never mass-replace author lists without showing a diff for user review, even in `--fix` mode.
- Never strip the arXiv eprint field when upgrading to a published version — keep both for traceability.
- Never introduce a DOI you didn't verify against CrossRef or arXiv.
