# Experiment: paper-trail on the Sarol 2024 citation-integrity benchmark

Focused execution plan for the headline validation experiment from the umbrella plan (`paper-tool-validation.md`, Experiments 1A / 1A-9way / 1A').

## Objective

Run the actual paper-trail orchestrator (extractor → adjudicator → verifier) on Sarol et al.'s human-annotated citation-integrity corpus and compare per-claim verdicts to Sarol's 9-class gold labels.

Two variants, A and C. A is the narrow apples-to-apples test; C is the full-pipeline test on the raw citing PDF.

| Variant | Input to paper-trail | Phases exercised | Apples-to-apples with Sarol? |
| --- | --- | --- | --- |
| **A** | citing sentence + pre-resolved chunks of cited paper | evidence extractor, adjudicator, verifier | Yes — same narrow slice Sarol's model sees |
| **C** | full citing paper PDF from PMC (via ID in `citations/` filenames) | **entire 7-phase pipeline** — claim extraction, bib resolution, PDF fetch, ingest, extractor, adjudicator, verifier | Much harder — paper-trail does everything end-to-end |

**Rubric decision (for this experiment only):** paper-trail's adapter emits **Sarol's 9-class labels directly** (ACCURATE / OVERSIMPLIFY / NOT_SUBSTANTIATE / CONTRADICT / MISQUOTE / INDIRECT / INDIRECT_NOT_REVIEW / ETIQUETTE / IRRELEVANT) rather than paper-trail's native rubric. Rationale: Sarol's taxonomy is well-defined, human-annotated, and published prior art; adopting it avoids label-mapping ambiguity. Whether to swap the main tool's rubric is a separate decision, deferred for now.

**Orchestrator discipline:** the adapter **does not reimplement or bypass paper-trail's agents.** It only bridges (i) Sarol input format → paper-trail inputs, and (ii) paper-trail verdicts → Sarol 9-class output. The actual reading, verdict, and verification go through the real orchestrator.

Success criteria:

- **A-3way — meet-or-beat.** paper-trail macro-F1 ≥ MultiVerS 0.52 and GPT-4 4-shot 0.45 on the same 922-claim test+dev holdout, with verdicts collapsed to Sarol's 3-way scheme.
- **A-9way — set the first baseline.** Report per-class F1 across all 9 Sarol labels; no prior baselines at this granularity.
- **C — end-to-end credibility.** Demonstrates paper-trail on full, real citing manuscripts (the thing it's actually designed for). Expected to be noisier than A but the only test that covers what real users do. This is the paper's headline end-to-end story even if raw numbers are lower than Sarol's narrow benchmark.

## Data

Cached at `data/benchmarks/sarol-2024/` (gitignored bulk; `download.sh` + `README.md` committed). License: MIT (upstream).

**Multivers-format (flat JSONL):**

| File | Rows | Use |
| --- | --- | --- |
| `claims-test.jsonl` | 606 | Primary eval — Variant A |
| `claims-dev.jsonl` | 316 | Iteration / prompt engineering |
| `claims-train.jsonl` | 2,141 | Smoketest pool (we do not train) |
| `corpus.jsonl` | 8,515 chunks across 100 papers | Source text for Variant A |

**annotations.zip (structured, used for Variants B and C):**

```
annotations/{Train,Dev,Test}/
  references/            — 70 / 10 / 20 cited-paper full texts, filename: NNN_PMC<ID>.txt
  references_paragraph.json  — paragraph-level structure of cited papers (JSONL despite .json ext)
  references_sentence/   — sentence-level structure
  citations/<cited_paper_dir>/<citing_paper_PMC>_N.json
      citing_paragraph    — full paragraph from citing paper, markers intact
      citation_context    — specific sentence containing the citation + char offsets
      marker_span.text    — original author-year marker ("Narendra et al., 2010")
      evidence_segments   — text in cited paper that supports/contradicts
      label               — Sarol 9-way gold label
```

Key facts from inspection:

- **Citing paper PMC IDs** are in the `citations/` filenames — enough to fetch full citing PDFs from PMC for Variant C.
- **Original citation marker text** is preserved in `marker_span.text` — fair input for paper-trail's bib resolver in Variant B.
- **Test split**: 20 cited papers × ~30 citing-paper instances each ≈ 606 claims (matches multivers-format).
- Across the test split there are likely several hundred unique citing papers — each a real PMC article. Variant C requires fetching all of them.

## Inputs to paper-trail per variant

All three variants invoke the real paper-trail orchestrator. The adapter only assembles inputs in paper-trail's expected shape and post-processes verdicts.

### Variant A — narrow (verdict core only)

| Input | Source |
| --- | --- |
| Claim text | multivers `claims-*.jsonl` → `claim` field, markers normalized |
| Source document | concatenated `corpus.jsonl` chunks listed in `cited_doc_ids`, ordered by `doc_id` |

Skipped phases: claim extraction, bib resolution, PDF fetch, GROBID ingest.

### Variant C — end-to-end

| Input | Source |
| --- | --- |
| Citing paper PDF | fetched from PMC via ID in `citations/.../<citing_PMC>_N.json` filename |

That's the entire input. paper-trail does everything from there: claim extraction, bib resolution, PDF fetching for each cited reference, GROBID ingest, extractor/adjudicator/verifier per claim.

Post-processing: for each Sarol-annotated citation instance (keyed by `(citing_PMC, marker_span.text)`), locate the matching verdict in paper-trail's ledger and record.

Paper-trail will also emit verdicts on **every other citation** in the citing paper — not just the Sarol-annotated ones. That's bonus data for qualitative analysis; no gold labels exist for those.

## Output format

Adapter emits Sarol's 9 labels directly. The extractor/adjudicator prompts receive a Sarol-specific rubric (not paper-trail's native one) for this experiment. The rubric is sourced verbatim from the Sarol paper's annotation guide. Classes:

- **ACCURATE** — cited paper supports the claim.
- **OVERSIMPLIFY** — cited paper's findings are oversimplified or overgeneralized in the claim.
- **NOT_SUBSTANTIATE** — cited paper does not substantiate all parts of the claim.
- **CONTRADICT** — citation context contradicts a statement in the cited paper.
- **MISQUOTE** — numbers or percentages misquoted.
- **INDIRECT** — evidence in cited paper itself cites other articles for the claim.
- **INDIRECT_NOT_REVIEW** — same as INDIRECT but cited paper is not a review article.
- **ETIQUETTE** — citation style is ambiguous; unclear what is being cited.
- **IRRELEVANT** — no information in the cited paper relevant to the claim.

Adapter writes `predictions.jsonl` per variant:

```json
{
  "instance_id": "...",
  "citing_pmc": "PMC2995166",
  "cited_pmc": "PMC2811155",
  "marker_text": "Narendra et al., 2010",
  "claim_text": "...",
  "pred_label": "OVERSIMPLIFY",
  "pred_sarol_3way": "NOT_ACCURATE",
  "gold_label": "OVERSIMPLIFY",
  "reasoning": "...",
  "evidence_quotes": [...],
  "cost_tokens": { "in": 1234, "out": 567 }
}
```

## Adapter

`scripts/run_sarol_benchmark.py`. Responsibilities:

1. Parse Sarol inputs per the chosen variant.
2. Stage a minimal paper-trail working directory with:
   - Variant A: single-claim file + pre-ingested cited source
   - Variant C: `pdf_dir` for paper-trail to fetch cited references into; citing PDF fetched from PMC
3. Invoke the real paper-trail entry point — `/ground-claim <citekey> "<claim sentence>"` for A, or `/paper-trail <citing_pdf>` for C.
4. Pass paper-trail a custom rubric config pointing at the Sarol 9-class label set (this experiment's prompt variant).
5. Collect ledger output, extract verdicts for the Sarol-annotated citations, write `predictions.jsonl`.

**Rule:** adapter does not touch paper-trail internals. Rubric override is via config, not code fork.

## Baselines

From Sarol et al. 2024 Table (not re-running, cited from paper):

| Model | 3-way micro-F1 | 3-way macro-F1 | Notes |
| --- | --- | --- | --- |
| MultiVerS (fine-tuned) | 0.59 | 0.52 | Best on ACCURATE (0.69), weak on NOT_ACCURATE (0.43) |
| GPT-4 4-shot | 0.65 | 0.45 | Strong on ACCURATE (0.80), very weak on NOT_ACCURATE (0.09) |

**No 9-way baselines exist.** We set the first.

## Metrics

Primary:

- **3-way micro & macro F1** on test (+ dev for confidence).
- **9-way macro F1** on test (+ dev).
- **Per-class F1** at both granularities (full confusion matrix).

Secondary:

- **Recall on the error classes** (non-ACCURATE). This is the practically meaningful number — can paper-trail find the errors?
- **Precision on error calls.** False-positive rate matters for a practitioner tool; authors won't trust a tool that cries wolf.
- **Cost per claim** (tokens in/out, wall-clock). For write-up + reproducibility.

Ablations (only if results warrant deeper analysis):

- A vs A' (chunks-only vs full-paper).
- With vs without verifier agent.
- Multi-citation (`<|multi_cit|>`) vs single-citation claims (split performance).
- Few-shot in-context examples drawn from `claims-train.jsonl` vs zero-shot.

## Train as methodological development data

Sarol's train split (2,141 human-annotated claims) is gold-standard labeled data. Even though paper-trail has no trainable weights, we *do* have many tunable design choices — prompt wording, sub-claim decomposition strategy, multi-cit handling, verifier inclusion, few-shot example selection, rubric phrasing. Train is where we evaluate those choices.

**Framing:** Sarol's train is our development set for paper-trail methodological iteration. Anything we learn on train (e.g., "per-source multi-cit prompting lifts macro-F1 by X") is legitimate methodology to report, and is a candidate to roll back into the main paper-trail tool, not just live in the experiment branch. Test is the held-out reporting set, evaluated once per locked configuration.

Axes we explicitly plan to explore on train:

- **Multi-cit per-source prompting.** Compare several wordings instructing the extractor to verify only the portion attributable to *this* source. Expect the largest F1 delta on the 51% multi-cit subset.
- **Sub-claim decomposition.** How aggressively the extractor decomposes the citing sentence into atomic sub-claims before evidence search. Too coarse → misses partial-support cases; too fine → decomposition noise.
- **Few-shot examples.** Draw from train for in-context exemplars; compare zero-shot vs 4-shot vs class-stratified 9-shot.
- **Verifier inclusion.** Run with and without the attestation-verifier pass; measure ΔF1 and ΔFP-rate.
- **Rubric phrasing.** The Sarol-rubric override text (class definitions) — word-for-word vs paper-trail-tone. Check whether Sarol's wording has any label-ambiguity that we should rephrase.

Each axis gets a controlled sweep on train; the winner is carried forward. **Test is only evaluated against the locked final configuration.** Any change discovered on dev or test that wasn't first found on train goes into a "post-hoc findings" section, not the headline numbers.

## Protocol

1. **N=5 smoketest (Variant A, train).** Five stratified claims from `claims-train.jsonl`, one per major label (ACCURATE / OVERSIMPLIFY / NOT_SUBSTANTIATE / CONTRADICT / INDIRECT). Adapter v0. Purpose: prove the orchestrator call actually runs, that verdicts come out in the Sarol label set, and that output is usable. Budget: a few hours.
2. **N=50 stratified pilot (Variant A, train).** All 9 labels represented (oversample minority). First pass on the Sarol-rubric prompt override. Establish per-claim cost baseline.
3. **Methodological sweeps (Variant A, train).** For each axis above (multi-cit prompting, sub-claim decomposition, few-shot, verifier, rubric phrasing), run a controlled sweep on a train subset (say 200–400 claims balanced across labels). Pick the best configuration. Treat dev split as an optional validation-of-winner checkpoint.
4. **Full train eval (Variant A, locked config).** 2,141 claims, winning config from step 3. Primary train numbers — these can be iterated on openly.
5. **Test eval (Variant A, locked config).** 606 test claims, prompts + orchestration locked. **Reported primary number. Evaluated once.**
6. **Variant C on test.** Fetch all unique citing PDFs from PMC, run paper-trail end-to-end, post-process to extract Sarol-annotated citation verdicts. Report F1 + coverage (fraction of Sarol-annotated citations paper-trail actually produced a verdict for).
7. **Head-to-head vs SemanticCite (optional).** Same test subset, qualitative side-by-side.

Decision gates:

- After smoketest: if the orchestrator fails to produce usable Sarol-labeled verdicts, fix the adapter before scaling.
- After pilot (N=50): if macro-F1 is catastrophically low, reassess rubric override before running sweeps.
- After sweeps: document what won and why. Any winning config chosen should have a defensible mechanistic rationale, not just a point-estimate F1 bump.
- After full-train: if results are strong, proceed to test. If weak, re-examine sweeps for missed axes.
- After test (Variant A): always run C — it's the end-to-end story the paper hinges on, even if Variant A numbers are already strong.

## Results artifacts

Per variant (A and A'):

- `predictions.jsonl` — per-claim predictions with raw + mapped verdicts.
- `confusion_matrix.csv` — 9x9 and 3x3.
- `per_class_report.md` — precision / recall / F1 / support per class, summary stats.
- `cost_report.md` — tokens and wall-clock.
- `error_analysis.md` — hand-selected misclassifications with notes (10–20 cases) for the paper.

All under `experiments/sarol-2024/{variant}/` in the repo (gitignored for the raw prediction JSONL if large; committed for the summary tables).

## Claim specificity (Sarol test+dev, N=922)

Breakdown of how the evaluated citation sits in the citing sentence:

| Type | N | % | Notes |
| --- | ---: | ---: | --- |
| Single-cit (specific attribution) | 450 | 48.8% | Lone `<\|cit\|>` or clearly separated from `<\|other_cit\|>` siblings. |
| Multi-cit (grouped cluster) | 471 | 51.1% | `<\|multi_cit\|>` — evaluated citation is one of a `[1,2,3]`-style cluster. |
| Edge / none | 1 | 0.1% | Dropped. |

Label distributions are nearly identical (76–80% ACCURATE both), but with class-level skews worth noting:

- **ETIQUETTE:** 1.9% multi-cit, 0% single-cit (citation-style ambiguity is by construction a multi-cite problem).
- **NOT_SUBSTANTIATE:** 7.2% single-cit vs 4.6% multi-cit (a lone cite bears full burden of support).
- **INDIRECT:** 2.8% multi-cit vs 1.2% single-cit (grouped cites pull in review papers).

**Design implication — multi-cit handling is a first-class adapter concern.** The extractor agent must be prompted per-source: "verify only the portion attributable to *this* source; do not penalize the paper for parts of the citing claim that a sibling citation may cover." Get this wrong and 51% of the data systematically miscalls.

## Risks and open questions
2. **Variant C coverage.** paper-trail may fail to extract a claim or resolve a bib entry that Sarol annotated — so the denominator for F1 on Variant C is "Sarol-annotated citations paper-trail produced any verdict for." Report coverage alongside F1.
3. **Rubric prompt override.** paper-trail's agents currently ship with its native rubric baked into prompts. The Sarol-rubric override must be a config-level swap, not a prompt fork. Pre-work: confirm the rubric is referenced via `.claude/specs/verdict_schema.md` and can be swapped for a Sarol variant without touching agent code.
4. **Class imbalance.** 78% ACCURATE. A trivial always-ACCURATE scorer gets 0.78 accuracy but ~0.09 macro-F1 (9-way). Report per-class F1 alongside macro to avoid misleading headlines.
5. **Pretraining contamination (test only).** Sarol's dataset is public on GitHub; if the LLM powering paper-trail saw it during pretraining, it may have memorized individual labels, inflating test F1 vs a genuine held-out benchmark. Note train is *allowed* to inform our methodology — contamination concerns only apply to the held-out test split. This is a general LLM-benchmark limitation. Mitigations: (a) flag in the paper; (b) Variant C's end-to-end setup adds bib-resolution + ingest stress that's unlikely to be memorized; (c) the synthetic-injection and opt-in-cohort experiments are not subject to this issue and serve as the independent defense.
6. **Cost for Variant C.** Hundreds of unique citing PDFs × full paper-trail audits = material spend. Estimate on a 5-paper subset before committing to the full test split.
7. **License for redistribution.** MIT on Sarol's data means we can publish predictions; confirm the annotations.zip redistribution terms on the linked paper before releasing.

## Deliverable checklist

- [ ] Confirm `.claude/specs/verdict_schema.md` can be swapped for a Sarol-rubric variant without forking agents.
- [ ] Draft the multi-cit per-source prompt fragment; sanity-check on a few hand-picked multi-cit claims.
- [ ] Write `scripts/run_sarol_benchmark.py` adapter for Variant A.
- [ ] N=5 smoketest on train (Variant A).
- [ ] N=50 stratified pilot on train (Variant A).
- [ ] Methodological sweeps on train: multi-cit handling, sub-claim decomposition, few-shot, verifier, rubric phrasing. Record winners with rationale.
- [ ] Roll any winning design improvements back into main paper-trail codebase (separate PR).
- [ ] Full train eval with locked config (Variant A).
- [ ] Extend adapter to Variant C (end-to-end from citing PDF).
- [ ] Full test eval on A (single-shot) and C (single-shot).
- [ ] Error analysis writeup (10–20 hand-selected cases across variants).
- [ ] Results tables + confusion matrices committed to `experiments/sarol-2024/`.
