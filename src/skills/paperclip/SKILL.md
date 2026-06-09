---
name: paperclip
description: Search and read full-text biomedical papers from PubMed Central, bioRxiv, medRxiv, and arXiv using the paperclip CLI.
---

# Paperclip

A virtual filesystem of full-text biomedical papers from PubMed Central, bioRxiv, medRxiv, and arXiv.

Treat it like a mounted drive. Papers live at `/papers/<id>/` â use standard bash patterns to navigate, read, search, and extract.

## Paper Layout

`/papers/<id>/`: `meta.json` (metadata), `content.lines` (full text, line-numbered), `sections/` (named files), `figures/`, `supplements/`.

IDs: `PMC` (PubMed Central), `bio_` (bioRxiv), `med_` (medRxiv), `arx_` (arXiv).
`/.gxl/` is writable scratch. `/papers/` is read-only.

## Workflow

Default to `map` for multi-paper questions â it reads each paper via a lightweight model. After map, synthesize directly; don't re-read papers individually.

1. **Find**: `search "topic"` â present results
2. **One paper**: `head`/`grep`/`scan` on `/papers/<id>/`
3. **Many papers**: `search -n 10` â `map --from ID "q"` â synthesize
4. **Stats**: `sql "SELECT ..."`

## Examples

```
search "CRISPR base editing delivery"
head -40 /papers/bio_dca47d15/content.lines
cat /papers/bio_dca47d15/meta.json | jq .title
grep -i "off-target" /papers/bio_dca47d15/content.lines
scan /papers/bio_dca47d15/content.lines "CRISPR" "off-target"
```

Use `head -N`, section files, or `grep`/`scan` over `cat` on full `content.lines`.
Pipes: `bash 'search "protein design" | grep -i "diffusion"'`.

## Sources

Default search covers PMC, bioRxiv, medRxiv, arXiv.
- `-s abstracts` for broader abstract-only corpus (no full text).

## Citations

Cite **[1]**, **[2]** inline. End with:

```
--------
REFERENCES
[1] Authors. "Title." *Journal* vol, pages (year). doi:XX
    https://citations.gxl.ai/papers/<doc_id>#L<n>
```

Never expose doc_id in prose. Cite every factual claim.

# Commands

Run `<cmd> --help` for full usage on any command.

## Search & Discovery

| Command | Description |
|---------|-------------|
| `paperclip search QUERY` | Semantic + keyword search. Key opts: `-n`, `-s SOURCE`, `-e`, `--since`, `--sort`, `--author`, `--journal`, `--year` |
| `paperclip grep PATTERN PATH` | Regex search across corpus or within a paper |
| `paperclip lookup FIELD VALUE` | Find by metadata: doi, author, title, pmc, pmid, journal |
| `paperclip sql "SELECT ..."` | SQL on `documents` table (200-row limit) |

## Reading & Analysis

| Command | Description |
|---------|-------------|
| `paperclip cat`, `head`, `tail`, `ls` | Read files, list directories |
| `paperclip scan FILE "p1" "p2"` | Multi-pattern search in a file |
| `paperclip ask-image PATH "q"` | Analyze figure with vision. `--fn describe` / `--fn extract-data` |
| `paperclip map --from ID "q"` | LLM reader across search results â answers per paper |
| `paperclip reduce --from ID "q"` | Synthesize map results. Strategies: summarize, table, themes |
| `paperclip results [ID]` | View saved search/map results. `--list` to see all |

## Text Processing

`sed`, `awk`, `sort`, `cut`, `tr`, `jq` â standard tools, pipes via `bash '...'`.
## Configuration

`config`, `login`/`logout`, `install`/`setup`, `update`/`uninstall` â settings, auth, IDE skills.

## Map Query Tips

- Be specific about what to extract. Bad: "Summarize this paper." Good: "What delivery vector was used, what cell type was targeted, and what transfection efficiency was reported?"
- When extracting data, enumerate every field you want in the query.
- Specify which section to focus on when relevant (e.g., "From the Methods section, extract...").
- Keep search results to **3â10 papers** for fast execution (`-n 5` or `-n 10`).
- After map, respond directly â don't follow up by reading individual papers with `cat`/`grep`.
## Sandbox Environment

Commands run in a sandboxed virtual shell (vsh).

**Allowed**: `cd`, `ls`, `cat`, `head`, `tail`, `grep`, `sed`, `awk`, `sort`, `cut`, `tr`, `jq`, `search`, `scan`, and more.
**Blocked**: `rm`, `curl`, `wget`, `ssh`, `sudo`, etc.
**Not supported**: Shell loops (`for`/`while`) and `xargs` â use pipes or multiple tool calls.

### Writable scratch: `/.gxl/`

Redirect output with `> /.gxl/file.txt` or `>> /.gxl/file.txt`. This maps to a `.gxl/` folder in the user's current working directory â files persist and are directly accessible on their machine.

```
grep -i "IC50" /papers/<id>/content.lines > /.gxl/ic50_hits.txt
awk -F, "NR==1 || \$3>100" /papers/<id>/supplements/data.csv > /.gxl/filtered.csv
ls /.gxl/
```

## Saving Files Locally

Any paper file can be saved to the local machine by redirecting `cat` with `>`. Binary assets (figures, images) stream as raw bytes; text files as text.

```
cat /papers/PMC10791696/meta.json > meta.json
cat /papers/PMC11576387/figures/fx1.jpg > fx1.jpg
cat /papers/PMC10791696/supplements/source_data.csv > data.csv
```

## Supplements (CSV / Excel)

Supplementary materials live under `supplements/` for many PMC papers. Process with `sed`/`awk`, write to `/.gxl/`, or save raw files locally with `cat > file`.

```
ls /papers/<id>/supplements/
head -5 /papers/<id>/supplements/source_data.csv
cat /papers/<id>/supplements/source_data.csv > source_data.csv
```

## Citation URL Format

Each reference must include a `citations.gxl.ai` link:

```
https://citations.gxl.ai/papers/<doc_id>#L<n1>,L<n2>
```

- `<doc_id>` = directory name under `/papers/` (e.g. `PMC10791696`, `bio_214f7ec77685`).
- Line numbers from `L<n>` prefixes in `content.lines`.
- Single: `#L45` â range: `#L45-L52` â multiple: `#L45,L120,L210`.
- Nature style for journals. "bioRxiv/medRxiv (year)" for preprints.
- Get author names, title, DOI from `meta.json`.
- Number references in the order they first appear.

## Search Examples

```
search "CRISPR delivery nanoparticle"
search "protein design" -n 50
search -s pmc "mRNA vaccine"
search -s biorxiv "single cell"
search -s arxiv "transformer protein"
search -s abstracts "drug discovery"
search -e "genome-wide association study"
search "AlphaFold" --since 30d
search "cancer" --journal "Cell" --year 2024
search --all "protein folding"
```

Key options: `-n/--limit`, `-s/--source`, `-e/--exact`, `--since`, `--sort [relevance|date]`,
`--author`, `--journal`, `--year`, `--category`, `-m/--mode [any|all]`, `--ranking [hybrid|bm25|vector]`.

## Lookup Examples

```
lookup doi 10.1101/2024.01.15.575613
lookup pmc PMC7194329
lookup pmid 32943797
lookup arxiv 2403.03507
lookup author "James Zou" -n 10
lookup title "CRISPR base editing"
lookup journal "Nature Medicine"
```

Fields: doi, author, title, abstract, source, date, pmc, pmid, arxiv, journal,
publisher, type, keywords, category, license, year, volume, issue, issn.
## Map & Reduce Examples

```
search "protein design" -n 10
map --from s_14bebc10 "What methods were used for protein design?"
reduce --from m_ec2c9cc9 --strategy summarize "What are the main findings?"
reduce --from m_ec2c9cc9 --strategy table "Compare methods and results"
reduce --from m_ec2c9cc9 --strategy themes "What themes emerge?"
```

Reduce strategies: `summarize`, `table`, `themes`, `consensus`, `bullet_points`, `extract`.
## Ask-Image Examples

```
ls /papers/<id>/figures/
ask-image /papers/<id>/figures/<filename> "What does this figure show?"
ask-image /papers/<id>/figures/<filename> --fn describe
ask-image /papers/<id>/figures/<filename> --fn extract-data
```

## Tips

- Prefer `head -N`, section files, or `grep`/`scan` â avoid `cat` on full `content.lines`.
- Use `> file.txt` after any command to save output locally.
- Use `bash '...'` for pipes or redirection to `/.gxl/`.
- `map` runs an LLM reader per paper â limit inputs with `-n 5` on search.
- Run `paperclip <command> --help` for full usage on any command.
