# Experiment: paper-trail on the Sarol 2024 citation-integrity benchmark

Focused execution plan for the headline validation experiment from the umbrella plan (`paper-tool-validation.md`, Experiments 1A / 1A-9way / 1A').

> **2026-04-22 reframe — E1/E2/E3/E4 supersedes the Variant-A/B/C/D naming below.** Decision log: `docs/journal/2026-04-22-experiment-design-e1-e4.md` D50–D53. **Headline experiment is E3 (the fetch-through-verdict experiment, phases 2-5)** with input shape (citing sentence + claim, reference token, citing paper PDF). The prior Variant-A/B/C/D framing is preserved below for historical context but is no longer canonical. Read the §"Experiment design (E1-E4)" subsection immediately below first; everything farther down is provenance.

## Experiment design (E1-E4, canonical 2026-04-22)

The 5 phases of paper-trail (note: phase 4 renamed from "GROBID ingest" to the tool-agnostic "PDF parsing"):

1. **Claim extraction** — citing paper (PDF / LaTeX / text) → list of (citing_sentence, cited_ref_id, claim_text). PDF input requires PDF parsing as a sub-step.
2. **Bibliography resolution** — cited_ref_id + citing paper's reference list → canonical identifier (DOI / PMC ID).
3. **PDF fetching** — canonical identifier → cited paper PDF.
4. **PDF parsing** — cited paper PDF → structured text. (GROBID is current tool; phase is tool-agnostic.)
5. **Verdict production** — structured cited paper + citing_sentence + claim_text → 9-class Sarol verdict. Currently 3-subagent (extractor/adjudicator/verifier) under topology-freedom (D32 from earlier 2026-04-22 — the decision that lets the optimizer restructure paper-trail's internal subagent layout).

The 4 experimental setups:

| Name | Phases tested | Input | Status |
|---|---|---|---|
| **E1** (verdict-only) | Phase 5 only | Sarol pre-staged: structured cited paper chunks + citing sentence + claim | **Subaim / seeding only.** Not on the headline plot. May be dispatched by the optimizer for sample-efficient sub-experiment hypothesis-checking (per D52); not part of the canonical reported curve. Useful as initial isolated-component sanity check. |
| **E2** (claim-extraction-only) | Phase 1 only | Citing paper (PDF or text) | **Backlogged.** Decision deferred until after the main experiment lands. Requires LLM-as-judge alignment because Sarol annotations are a subset of any paper's claims by design — not strictly verifiable reward. May appear as supplementary proof-of-concept with explicit limitations note, OR skipped entirely. Resolve based on how the paper feels post-main-results. |
| **E3** (fetch-through-verdict) | Phases 2-5 | (citing sentence + claim text, reference token, citing paper PDF) | **Headline experiment we design for.** Paper-trail parses the citing PDF to find the bib entry corresponding to the reference token, resolves to canonical ID, fetches cited paper PDF, parses, produces verdict. Closest defensible end-to-end given the dataset; ties cleanly to Sarol's existing annotations. The plot. |
| **E4** (full end-to-end) | Phases 1-5 | Citing paper PDF (no pre-registration of which claims to evaluate) | **Not designed for in this paper.** Phase 2-5 numbers become a function of phase 1 quality, requires stratification, alignment problem with Sarol annotations is the well-known unresolved problem. Not on the roadmap. Future work. |

### E3 dataset-extension work (D51, new Task 5 deliverable)

E3's input shape is `(citing sentence + claim, reference token, citing paper PDF)` per claim. Sarol's existing annotations don't directly provide this — they give us per-claim records keyed by (citing sentence, pre-staged cited chunks, gold verdict), with citing paper identity implicit. We need a small dataset-extension step:

- For each Sarol claim, identify which citing paper it came from (Sarol annotations have this implicitly).
- For each claim, identify the reference token within the citing paper that points to the cited paper (the `\cite{}` key or `[N]` reference number).
- Package as: per-claim record = (citing sentence, claim text, reference token, path to citing paper PDF).
- Citing paper PDFs need to be fetched / collected (Sarol's 100 citing papers).

Estimated effort: ~1 day of dataset-engineering scripts + manual spot-check on a few papers. Lands as part of the eval-arm build. Acknowledge in paper methods section: "the experimental setup wasn't free; we extended Sarol's per-claim framing to test more pipeline phases."

### E3 scoring

- Input per claim: `(citing sentence + claim, reference token, citing paper PDF)`.
- Paper-trail output: 9-class Sarol verdict.
- Scoring: macro-F1 against Sarol's gold verdict for that claim. Same metric as the original Variant A.
- Coverage instrumentation: also report fetch-success-rate per landmark (did paper-trail successfully fetch the cited paper for this claim? what fraction of the dataset is reachable?), and ingest-success-rate (did PDF parsing produce usable structured text?). These are infrastructure-quality metrics, reported as a supplementary table per landmark, not as primary metrics the optimizer chases.

### Optimizer-canonical-vs-sample-efficiency split (D52)

- **Canonical run (always E3):** the dispatcher always invokes E3 for the train+val curve. Reported metric is E3 macro-F1.
- **Optional sample-efficient sub-dispatch (E1):** the optimizer's initial system prompt mentions that for cheap hypothesis-checking, it may dispatch isolated phase-5-only sub-experiments (E1-shaped, with pre-staged Sarol chunks as input). Useful for cheap "did this prompt edit improve adjudication?" pre-checks before committing to a full E3 run.
- **What's reported:** only E3 numbers go on the train+val curve. E1 sub-dispatches are logged for transparency but don't enter the canonical metric.

This gives the optimizer the sample-efficiency lever Karpathy-style autoresearch would expect, without confusing the canonical metric. Cleanliness preserved.

---

## Historical Variant-A/B/C/D framing (preserved for provenance, superseded 2026-04-22)

Original objective: run the actual paper-trail orchestrator (extractor → adjudicator → verifier) on Sarol et al.'s human-annotated citation-integrity corpus and compare per-claim verdicts to Sarol's 9-class gold labels.

Originally framed as two variants (A and C), with B and D added later. Mapping to current E-naming:

- **Variant A** ≈ **E1** (verdict-only, Sarol pre-staged inputs, phase 5 only). Was the "iteration workbench" in the prior framing; now demoted to subaim/sample-efficiency-only per D52.
- **Variant B** ≈ **E2** (claim-extraction-only, phase 1 only). Was the 2026-04-22-morning addition; now backlogged per D50.
- **Variant C** ≈ **E4** (full end-to-end, phases 1-5). Was originally the headline pre-2026-04-22-afternoon; now not designed for due to the unresolved alignment problem.
- **(no prior letter)** ≈ **E3** (the fetch-through-verdict experiment, phases 2-5). New 2026-04-22 — emerged from the experiment-design conversation as the defensible end-to-end given the dataset.
- **Variant D** = future-paper raw-source-extraction work; unaffected by E-naming reframe.

Original Variant-A/C table:

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

## Variant strategy (decision 2026-04-21) — Variant C is the headline

**Context.** After the agent-only reframe (see `agentic-pipeline-optimization-framework.md`), the paper's primary contribution is the framework for agent-only optimization of multi-subagent pipelines. The case study must exercise enough of the pipeline to plausibly require the pipeline — otherwise a reviewer can rebut "this task could have been solved with a single LLM prompt; your framework over-engineers the solution."

**Variant A is exposed to the single-prompt rebuttal.** Variant A's input is short (citing sentence + pre-selected chunks, ~5K tokens) and its output is a 9-class label. A long-context LLM with the rubric inline can plausibly solve this task directly. The extractor/adjudicator/verifier decomposition's marginal *accuracy* value on Variant A is probably small; its value is in auditability / per-stage cost attribution / optimizability. A reviewer asking "why not just one prompt?" has a fair question for Variant A specifically.

**Variant C is not exposed to the single-prompt rebuttal.** Variant C's input is a full citing PDF. Phases 1-7 must run: claim extraction from the manuscript, bib resolution, PDF fetch (tool-use against PMC / arXiv APIs), GROBID ingest, then extractor/adjudicator/verifier per claim. No single prompt can do PDF-fetch tool-use loops, cross-document retrieval, or iterate over N citations with per-citation structured output. Variant C is agentic by construction.

### Decision

**Variant C is the paper's headline task.** Paper's headline results table reports Variant C numbers. Variant A stays as the iteration workbench + apples-to-apples comparison arm (Sarol's published baselines were essentially verdict-core, not end-to-end).

**Rationale (Human 2026-04-21):** *"we lean in to experiment C, to your point."* Variant C justifies the agentic framing by construction rather than by defensive argument; the agentic-optimization-for-scientific-measurement angle is more defensible under C than under A (where the single-prompt rebuttal has more bite). Also matches the faithfulness-doc framing already in place: *"This is the paper's headline end-to-end story even if raw numbers are lower than Sarol's narrow benchmark."*

### Operational split

- **Variant A — iteration workbench.** Cheaper per run (no PDF fetch, no ingest). Used as the benchmark the optimizer agent iterates against during revision cycles. Fast feedback, short turnaround. Fits the graduated-N ramp (N=10/25/50/100/200) naturally.
- **Variant C — landmark validation.** More expensive per run (full-pipeline tool use). Run at a smaller set of landmarks — at minimum, `paper-trail-v1` and `paper-trail-v_final`; possibly one mid-curve landmark. Where the paper's headline numbers come from.

The optimizer iterates against Variant A gradients; Variant C landmarks are the reportable headline. Same underlying Sarol train/val/test splits and gold labels — no additional leakage risk introduced by running both variants against the same benchmark.

### Zero-shot single-prompt baseline — backlog, not priority (2026-04-21)

A zero-shot single-prompt baseline on Variant A is a mandatory paper table row (cf. TextGrad Table 3 "CoT (0-shot)"). **Human 2026-04-21:** *"I still think we want the zeroshot comparison but imo it's a baseline, not a 'need to do now' priority."*

- Scope: one prompt call per claim, N=50-600 on Variant A test (Sarol's native split). Cost ≈ $5-30 at Opus 4.7.
- Purpose: apples-to-apples comparison row in the paper, not a strategic pivot trigger. The strategic pivot (lean into Variant C) is already decided.
- Pin: before paper submission, not before Task 5 framework build-out.

### Variant B — phase 1 (claim extraction) evaluation (added 2026-04-22)

**Origin:** raised by Human 2026-04-22 while reviewing the lit-review-2 competitor landscape. Observation: Sarol's annotations include the citing sentence and cited reference for each claim; given a raw paper as input, paper-trail's phase 1 extractor should produce the same tuples. That's a verifiable-reward signal at phase 1 — independently measurable, before downstream adjudication runs.

**Input:** raw citing paper text (PMC XML or PDF). Sarol provides the annotated ground-truth `(citing_sentence, cited_reference, claim_text)` tuples for the paper.

**Task (paper-trail side):** run phase 1 only — extract every `\cite{}` citation, identify the citing sentence(s), produce the specific claim being made. Output: list of `(citing_sentence, cited_reference, claim_text)` tuples.

**Scoring:** LLM-as-judge matching of paper-trail's extracted tuples against Sarol's annotations for the same paper.
- Match rubric: given two tuples, "same claim" or "different claim." Consider reference equivalence (Smith 2020 ≈ \cite{smith2020} ≈ [3] if all resolve to the same paper), citing-sentence overlap (same sentence or substantially-overlapping sentences), claim-text semantic equivalence.
- Metrics: precision = `matched / extracted`; recall = `matched / Sarol-annotated`; F1.
- Judge-model choice: **probably not Opus** (risk of self-agreement artifact since Opus is also the extractor). Lean: Sonnet 4.6 or a cheaper frontier model. 3-seed judge agreement required for high-confidence matches.

**Why this variant exists:**
- Isolates phase 1 as a measurable, separately optimizable unit. Currently Variant A bypasses phase 1 (claims pre-staged); Variant C rolls phase 1 into the end-to-end number.
- Gives the optimizer a phase-1-specific gradient. Per D47 (train-tier per-claim adjudicator reasoning), the optimizer already sees downstream failure modes; Variant B adds upstream extraction failure modes to the visible gradient.
- De-risks Variant C scoring. The same LLM-as-judge matcher is what Variant C needs; Variant B validates the matcher as a sub-experiment.

**Cost estimate (rough):** ~$2-5 per paper for extraction + matching at Opus 4.7 + Sonnet 4.6 judge. For 100 Sarol-train papers, ~$200-500 per revision. Cheaper than Variant C full-pipeline. Probably runs at landmark tags alongside Variant A rather than on every revision.

**Empirical gate before commit (~1-2 hrs):** spot-check extraction on 5 Sarol-train papers; compute rough alignment rate with Sarol annotations using the LLM-judge matcher. Accept if alignment-rate ≥ ~70%; reconsider design if < ~50%.

**Open questions (to resolve during/after spot-check):**
- Reference disambiguation: what counts as "same reference" in the match rubric? Need a resolution step (probably via cited-paper title+author) as sub-primitive.
- Partial-match semantics: if paper-trail's claim is a superset of Sarol's annotation (includes extra clause), is that a match? Rubric-call for the LLM-judge.
- Inference cost for the matching step: if LLM-judge on every extracted × annotated cross product is prohibitive, use embedding-similarity as a cheap filter, LLM-judge only on ambiguous pairs.
- Does Variant B bypass bibliography resolution (phase 2)? Probably yes — we assume paper-trail extracts `\cite{key}` verbatim; resolution lives in phase 2 and belongs to Variant C.

**Relationship to Variant D (below):** Variant B is a narrower, tractable sub-experiment that de-risks Variant D's alignment problem before committing to it. Variant D is Variant B + downstream phases on the extracted claims. Variant B can land first; Variant D folds in after.

### Variant C end-to-end scoring — unresolved design question (deferred 2026-04-22)

Variant C as currently described (full PDF → all 7 phases → verdicts per Sarol annotation) has an unresolved scoring-alignment problem. Brainstormed options from Human + Agent 2026-04-22 (full thought-process logged in `paper-writeup-items.md` §"Other paper-level threads" — the "Variant C end-to-end scoring brainstorm" bullet). Tentative lean: **Option B (seed with pre-registered Sarol reference IDs; paper-trail extracts claims for those references, then runs downstream)** because it cleanly removes the "which claims count" ambiguity without opening composite-metric fiddly-ness. Defer resolution until Variant B alignment-rate spot-check gives empirical data on LLM-judge matching behavior. The end-to-end story for the paper may ultimately be: Variant A (iteration workbench) + Variant B (phase 1 validated separately) + Option B (phase 1 + A on pre-registered references) as the defensible end-to-end. Variant C full-PDF-start-to-finish then appears as a qualitative demonstration, not primary evaluation.

### Variant D (proposed, backburnered) — raw source papers + independent claim extraction

**Human 2026-04-21:** *"ideally we test end to end too from ORIGINAL source papers but to your point that requires matching claim-level to the original dataset to measure which is not guaranteed. But extending their dataset to *raw* original 100 paper and seeing how close our claim extraction even matches their source data is a task in and of itself and we can consider using their dataset as a proxy to measuring the full system. Put it on the backburner."*

What this would be:
- Start from the 100 citing papers' raw text (PMC XML or PDF), not from Sarol's pre-staged claim instances.
- Run paper-trail's full claim-extraction phase independently — every `\cite{}` in every paper.
- Match extracted claims to Sarol's annotated claims (the alignment problem — faithfulness doc §"Variant C claim-alignment problem" already flags fuzzy-match as the approach).
- Evaluate: does paper-trail's claim-extractor recall all Sarol-annotated claims? What fraction? Once matched, how well does the verdict core do on the matched subset?
- The Sarol dataset then becomes a *proxy measurement* of the full-system behavior on raw source inputs, not a claim-pre-staged benchmark.

**Why backburnered:** it's a task of its own — matching paper-trail's independently-extracted claims to Sarol's annotation schema is non-trivial, probably requires a new alignment rubric, and is meaningfully harder than Variant C's already-partially-aligned flow. Ambition-justifying but scope-expanding. Pin: consider after Variant C primary results are in; could be a follow-up experiment or a second-paper.

### Open operational question (deferred)

Whether Variant A or Variant C is the substrate against which the optimizer's train/val split is materially defined has an important implication: the optimizer optimizes against Variant A gradients (because it's cheap), but the paper reports Variant C (because it's the headline). If phases 1-4 (claim extraction, bib resolution, PDF fetch, ingest) are not meaningfully edited across revisions — because the optimizer never gets Variant A gradient on them — then Variant C improvements across versions are attributed to phases 5-7 only. That's fine if we disclose it honestly. If we want Variant C phases 1-4 to also improve, the optimizer needs some Variant-C-based signal. Probably addressable with a small-scale Variant C iteration budget alongside the Variant A main loop. Deferred until Task 5 build-out forces the question.

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

## Compute and cost tracking

All experiment runs use **Claude Opus 4.7** by default (upper-bound; most capable). Cheaper-model ablations (Sonnet 4.6, Haiku 4.5) are a named sweep axis — not the default.

Per-stage usage is captured after each subagent call via `experiments/sarol-2024/scripts/record_usage.py` and written to `ledger/usage/<claim_id>.jsonl`. `parse_verdict.py` aggregates into each prediction record under a `usage` field with `cost_usd_total` + per-stage breakdown. Pricing table is in `parse_verdict.py` top-of-file; update when Anthropic pricing changes.

**Observed pilot cost (Opus 4.7, 1 claim, no caching):** $0.66. Scaling estimate for the full run (~2,141 train + 606 test on-demand, no caching, no batch): ~$1,800 raw; with Batch API 50% + prompt-cache reuse of the rubric/prompt (~30% input reduction) probably ~$700.

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
