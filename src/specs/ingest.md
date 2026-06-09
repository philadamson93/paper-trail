# Phase 2.5 — PDF Ingest

Contract between Phase 2 (`/fetch-paper`) and Phase 3 (`/ground-claim`). Converts a fetched PDF into a structured filesystem that Phase 3 subagents can navigate with `rg`, `cat`, and vision calls — no PDF-reading smarts required at the subagent layer.

## Why this exists

The current `/ground-claim` workflow expects each subagent to:

1. Open a full PDF in context.
2. Navigate its structure by itself.
3. Locate evidence by skimming plain-text extraction.
4. Check figures by imagining / inferring their content.

At ~50 parallel subagents, this is where drift happens: open-ended PDF navigation is a big surface for error. The fix is to do the structural work **once per paper at ingest time**, producing a stable layout subagents can grep against and point vision at.

## Input

- `pdf_path` — absolute path to a fetched PDF.
- `citekey` — the bibtex key (e.g., `hammernik2021`).
- `out_dir` — directory to write into (e.g., `<run_output>/pdfs/hammernik2021/`).

## Output

```
pdfs/<citekey>/
  meta.json               # { title, authors, doi, abstract, page_count, pub_date, source_pdf }
  content.txt             # full concatenated body text with `L<n> [p<page>]` line prefixes
  sections/
    Abstract.txt
    Introduction.txt
    Methods.txt
    Results.txt
    Discussion.txt
    ...                   # names taken verbatim from the PDF; may include "§2.1 Foo" style
  figures/
    fig1_p2.png           # one PNG per figure; filename encodes figure number + page
    fig2_p3.png
    index.json            # [{figure, page, caption, filename}, ...]
  ingest_report.json      # { tool, success, sections_extracted, figure_count, errors }
```

If any step fails (e.g., image-based PDF, unreadable TEI), the script falls back gracefully and records `ingest_mode` in `ingest_report.json`:

- `grobid` — happy path: TEI XML parse succeeded, sections populated
- `ocr_fallback` — GROBID failed; tesseract OCR produced `content.txt`; no sections
- `pdftotext_fallback` — both above failed; flat text only
- `error` — nothing worked; Phase 3 falls back to in-context PDF read

The report's `ingest_mode` is the discriminator Phase 3 dispatch reads to pick its workflow.

## Line-number prefix format

`content.txt` uses `L<n> [p<page>]: <line text>` on every line. This mirrors Paperclip's `content.lines` format so phrasing-pattern conventions transfer. Example:

```
L1 [p1]: Deep learning for MRI reconstruction has become an active research area.
L2 [p1]: Compressed sensing remains a foundational technique.
L3 [p2]: We trained a ResNet50 on 1.35 million medical images.
```

The `L<n>` prefix lets subagents cite the exact line in their attestation. The `[p<page>]` prefix lets attestation URLs point to the right PDF page.

## Running

Script: `.claude/scripts/ingest_pdf.py`

Usage:

```
python3 .claude/scripts/ingest_pdf.py \
    --pdf pdfs/hammernik2021.pdf \
    --citekey hammernik2021 \
    --out-dir pdfs/hammernik2021/
```

Requires:

- Python 3.10+
- `pymupdf` (for figures + OCR detection + text extraction fallback)
- `lxml` (for TEI XML parsing)
- `requests` (for GROBID HTTP client)
- Docker + a running GROBID container. Default endpoint: `http://localhost:8070`. Overridable via `--grobid-url`.

## Starting GROBID

```
docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2
```

If not running, the script prints this command and exits non-zero. The orchestrator's Phase 2.5 should check GROBID health at the start and either start the container or skip to fallback mode.

## Resumability

Ingest is idempotent: if `<out_dir>/ingest_report.json` exists and reports `success: true`, skip. Force re-ingest with `--force`.
