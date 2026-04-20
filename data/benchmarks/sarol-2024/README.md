# Sarol 2024 — Citation-Integrity Benchmark

Download script + README for the public benchmark from Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications: Corpus Annotation and NLP Models"* (Bioinformatics btae420).

**Source:** https://github.com/ScienceNLP-Lab/Citation-Integrity
**License:** MIT (upstream)
**Purpose for us:** primary external benchmark for the paper-trail validation experiment.

## Where the data actually lives

**Outside the repo.** `download.sh` fetches into `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/` (default: `$HOME/.paper-trail/benchmarks/sarol-2024/`). The repo only contains this README and the download script — **no bulk benchmark data is ever committed or placed inside the repo tree.**

This is deliberate. The experiment orchestrator runs inside the repo; keeping the benchmark (which contains every gold label) outside the repo means the orchestrator's cwd-based filesystem exploration cannot stumble onto it.

## Fetch

```bash
bash data/benchmarks/sarol-2024/download.sh
```

Idempotent. To override the destination (e.g., a shared drive for a multi-user setup):

```bash
export PAPER_TRAIL_BENCHMARKS_DIR=/path/to/benchmarks
bash data/benchmarks/sarol-2024/download.sh
```

`stage_claim.py` and `parse_verdict.py` respect the same env var.

## Files (after running `download.sh`)

All under `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/`:

- `claims-{train,dev,test}.jsonl` — SciFact-format claim records (2,141 / 316 / 606).
- `corpus.jsonl` — 8,515 cited-paper paragraph chunks across 100 papers.
- `annotations.zip` + unpacked `annotations/` — richer original format with `references/NNN_PMC<ID>.txt` (cited-paper full text) and `citations/<cited>/<citing_PMC>_N.json` (per-citation annotations with marker text, citing paragraph, gold label).

## Record schemas

See `docs/plans/paper-tool-validation.md` (Appendix) for full schemas, label distribution, and worked examples.

## Leakage policy

See `docs/plans/experiment-sarol-leakage-hardening.md`. Short version: do not copy, symlink, or grep this benchmark data from inside the repo during experiment orchestration. `parse_verdict.py` is the only code that should ever touch it at scoring time, and even that reads only via the env-var-rooted path.
