# Sarol 2024 — Citation-Integrity Benchmark

Local cache of the public benchmark from Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications: Corpus Annotation and NLP Models"* (Bioinformatics btae420).

**Source:** https://github.com/ScienceNLP-Lab/Citation-Integrity
**License:** MIT (upstream)
**Purpose for us:** primary external benchmark for the paper-trail validation experiment. See `docs/plans/experiment-sarol-benchmark.md` for the experiment plan.

## Fetch

```bash
./download.sh
```

Idempotent. Files below are gitignored — only `download.sh` and this README are committed.

## Files (after running `download.sh`)

- `claims-{train,dev,test}.jsonl` — SciFact-format claim records (2,141 / 316 / 606)
- `corpus.jsonl` — 8,515 cited-paper paragraph chunks across 100 papers
- `annotations.zip` + unpacked `annotations/` — richer original annotation format:
  - `annotations/{Train,Dev,Test}/references/NNN_PMC<ID>.txt` — full text of each cited paper
  - `annotations/{Train,Dev,Test}/citations/<cited_paper>/<citing_PMC>_N.json` — per-citation annotations with original marker text, citing paragraph, gold 9-way label

## Record schemas

See `docs/plans/paper-tool-validation.md` (Appendix) for full schemas, label distribution, and worked examples.

## Do not

- Do not commit the bulk JSONL / zip files. `.gitignore` excludes them.
- Do not redistribute without checking upstream license terms.
