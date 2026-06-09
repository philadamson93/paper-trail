Download a paper's PDF to the project's configured PDF directory, or surface a structured retrieval prompt if the paper is paywalled. Never attempt to bypass access controls.

## Invocation forms

- `/fetch-paper <citekey>` — resolve via configured .bib files
- `/fetch-paper <DOI>` — direct DOI
- `/fetch-paper <arXiv-id>` — direct arXiv
- `/fetch-paper "<paper title>"` — fuzzy title lookup
- `/fetch-paper path/to/document.tex` — bulk: scan all `\cite{...}` calls, queue missing PDFs

## Read config

Read `pdf_dir`, `pdf_naming`, `bib_files`, and `institutional_access` from `claims_ledger.md` YAML frontmatter at the project root. If the ledger is missing, prompt the user to run `/init-writing-tools` first and stop.

## Resolution

- **citekey input**: look up in the configured .bib files. Extract DOI, arXiv ID, title, authors, year.
- **DOI input**: query CrossRef (`https://api.crossref.org/works/<DOI>`) to populate metadata.
- **arXiv-id input**: query arXiv API (`https://export.arxiv.org/api/query?id_list=<id>`).
- **title input**: search to resolve to a DOI and, if possible, an existing citekey.

## Download order (first hit wins)

Try these in order, stopping as soon as a PDF is retrieved:

1. `paper-search` MCP: `download_arxiv`, `download_biorxiv`, `download_medrxiv`, `download_pubmed` — whichever matches the source.
2. `papersflow` MCP: paper lookup to check for an open-access URL.
3. CrossRef via WebFetch: check the `is-open-access` flag and try the `URL` or `link` fields.
4. Direct arXiv PDF: `https://arxiv.org/pdf/<id>.pdf` if an arXiv ID was resolved.

Save the downloaded PDF to `<pdf_dir>/<formatted filename>` using the configured naming pattern. Create the directory if missing.

## Paywall fallback

If no open-access source is found, do not fail silently. Emit this structured prompt:

```
⚠ Paywalled or not found in open-access sources.

  Title:        <resolved title>
  Authors:      <resolved authors>
  Year:         <year>
  DOI:          <DOI>
  Journal URL:  https://doi.org/<DOI>
  arXiv URL:    <if a preprint exists>

  Target save path: <pdf_dir>/<formatted filename>

To proceed:
  1. Download via your institutional access (<institutional_access from config>).
  2. Either save directly to the target path, or tell me where you saved it and
     I'll copy + rename it.
```

## Bulk mode (`.tex` input)

- Parse all `\cite{...}`, `\citep{...}`, `\citet{...}`, `\parencite{...}` arguments (comma-separated keys handled).
- De-dupe by citekey.
- For each key whose target PDF path doesn't already exist, run single-paper logic above.
- At the end, report:
  - **Downloaded**: N keys (list)
  - **Already present**: M keys (list)
  - **Pending manual retrieval**: K keys (list with DOIs and target save paths)

## Do not

- Never suggest Sci-Hub, LibGen, or similar paywall-bypass workarounds.
- Never misrepresent a preprint as the published version (or vice versa). If both exist and the published version is open access, download that and note the arXiv ID in the retrieval report.
- Never substitute a different paper's PDF when the target is unavailable — fail explicitly with the paywall prompt.
- Never silently overwrite an existing PDF at the target path. If one exists, report "already present" and move on.
