# paper-trail validation paper — experiment plan

Living plan for a paper validating `paper-trail` as a citation-hygiene tool. Update as corpora and pilots evolve.

## Framing

**Contribution:** a methods/tool paper characterizing what automated citation audit catches in real manuscripts, validated on controlled and real corpora.

**Register:** citation hygiene (spell-checker for references), not fraud detection. "Errors are typically minor but pervasive, and authors miss them" *is* the paper, not a disappointment.

**Scope (what paper-trail does):** given a manuscript and its bibliography, verify that each cited claim is faithful to its named cited source. Ground truth is unambiguous — the cited paper either supports the claim or it doesn't. No adjudication of "is the claim true in the world," no open-corpus retrieval.

**What we are *not* doing:**

- **General claim verification** ("is X true, search the literature"). Datasets like SciFact, PubHealth, HealthVer, COVID-Fact, MSVEC, and tools like Valsci solve that — it's a different task with a much larger blast radius (requires adjudicating real-world truth, invites political and anti-science misuse).
- **Open-domain retrieval** ("find a paper that supports this claim"). Also out of scope — our inputs are always author-provided bibliographies.
- **Fraud detection.** Scope is miscitation, not misconduct.

Citation integrity is a clean scientific task because the unit of trust — the citation — is already the backbone of academic standing (Google Scholar, h-index, tenure cases all run on citations). A citation either faithfully represents its source or it doesn't; that's the whole ground truth.

**Strategic constraints:**

- **Priority defense.** Preprint + code release simultaneous so the *methodology + error-class taxonomy* are the claimable contribution. Anyone later running mass recall on journals is follow-on work.
- **Culture-war defense.** Avoid journal / country / institution comparisons and preprint→publication drift studies. Both invite misuse by exploitative publishers ("see, we add value!") and by anti-science commentary ("80% of papers are wrong!"). Revisit in a follow-up once framing authority is established.
- **Ethics.** No named findings on non-consenting authors' published work. Aggregate-only for retrospective corpora; named cases only from opt-in volunteers.

## Related work

### In-scope: citation integrity (claim tied to specific cited source)

Two tracks of prior work.

**Academic track — ScienceNLP Lab (Sarol, Schneider, Kilicoglu).** Biomedical-only, study-not-tool.

- **Sarol et al. 2024, *Bioinformatics* (btae420).** Annotated corpus (3,063 citation instances across 100 PMC-OA papers) + fine-tuned NLP pipeline (BM25 + MonoT5 retriever → MultiVerS claim verifier / GPT-4 few-shot classifier). Labels collapsed from 8 to 3 (ACCURATE / NOT_ACCURATE / IRRELEVANT) because models couldn't learn fine-grained distinctions. Best F1: 0.59 micro / 0.52 macro. Authors' own framing: "not yet high for practical use." **Human-annotated (5 students, Cohen's κ reported).** GitHub: [ScienceNLP-Lab/Citation-Integrity](https://github.com/ScienceNLP-Lab/Citation-Integrity). Supervised; no inference API for new papers.
- **Sarol et al. 2025, ASIS&T.** LLM replication of Greenberg's 2009 Alzheimer's β-amyloid distortion study. Case study, not a tool.
- **Sarol et al. 2025, Peer Review Congress.** Gemini 1.5 Pro / GPT-4o / LLaMA-3.1 on a 2,000-paper citation corpus. Headline: **34% of citations erroneous, 37% of citing papers affected, 98% of cited papers cited incorrectly at least once.** Study, not tool.

**Concurrent tool track — SemanticCite (Sebastian Haan, Nov 2025).** arXiv 2511.16198; [sebhaan/semanticcite](https://github.com/sebhaan/semanticcite); Streamlit app + HuggingFace Space.

- Cross-domain (8 disciplines: CS, Medicine, Chemistry, Biology, Materials Science, Physics, Geology, Psychology).
- Four-stage pipeline: PyMuPDF text extraction → recursive 512-char chunking → ChromaDB hybrid retrieval → LLM classification.
- 4-class taxonomy: Supported / Partially Supported / Unsupported / Uncertain.
- Fine-tuned Qwen3 1.7B / 4B / 8B models released.
- Dataset: 1,111 citations across 8 disciplines, **labeled by GPT-4.1 (no human annotators, no inter-annotator agreement reported).** Performance numbers are against GPT-4.1's own labels, so they mostly reflect teacher-student distillation quality. Label distribution and dataset license not disclosed.
- Status as benchmark for us: **not usable as a primary benchmark** — labels aren't gold-standard. Usable as a concurrent-tool qualitative comparator.

**paper-trail's remaining white space:**

1. **Claude Code-native workflow** — author mode on in-progress LaTeX, bibliography resolution, paywalled-reference handling with institutional access. SemanticCite is a file-upload Streamlit; Sarol is a research pipeline.
2. **Three-agent attestation/verifier architecture** — extractor + adjudicator + verifier with fabricated-quote detection. No analog in either competitor.
3. **Fine-grained verdict rubric** (CONFIRMED, OVERSTATED, UNSUPPORTED, MISATTRIBUTED, CONTRADICTED, CITED_OUT_OF_CONTEXT, INDIRECT_SOURCE, AMBIGUOUS, UNVERIFIED_ATTESTATION) — actionable remediation classes vs SemanticCite's 4 coarse classes and Sarol's collapsed 3.
4. **GROBID-structured ingest** — sections, figures, tables preserved. SemanticCite uses PyMuPDF + recursive text splitting, loses structure. Sarol pre-chunks similarly.
5. **Validates on human-annotated benchmark** — Sarol 2024 is gold-standard. SemanticCite never validates against a human-annotated external corpus.

### Adjacent but out of scope: general claim verification / literature search

Called out for framing clarity — these are *not* competitors to paper-trail and we do not benchmark against them:

- **SciFact / SciFact-Open (Wadden et al.)**, **HealthVer**, **COVID-Fact**, **PubHealth**, **MSVEC**, **SciClaimHunt** — general scientific / public-health claim verification. Claims are synthesized atomic assertions or fact-checked public claims, not real in-paper citations. Task is "is this claim true given some corpus," which is a different ground-truth problem.
- **Valsci (Brice 2025, BMC Bioinformatics)** — open-source tool for "validate scientific claims en masse" via Semantic Scholar literature search. Input: standalone claims. Output: evidence synthesis across the literature. Different task (search-and-adjudicate) from paper-trail's task (audit an author's specific citation).
- **SourceCheckup** — evaluates groundedness of LLM responses against cited sources; adjacent but focused on LLM-generated content, not author-written manuscripts.

**Differentiation axes for paper-trail:**

1. **Fine-grained verdict rubric** (CONFIRMED, OVERSTATED, UNSUPPORTED, MISATTRIBUTED, CONTRADICTED, CITED_OUT_OF_CONTEXT, INDIRECT_SOURCE, AMBIGUOUS, UNVERIFIED_ATTESTATION). Agentic read-the-paper workflow can sustain granularity that retrieval-classifier pipelines collapsed.
2. **Full-paper ingest via GROBID** — bypasses their retrieval bottleneck (Recall@20 = 0.54) and their abstract-only evaluation constraint.
3. **Three-agent attestation/verifier** — no analog in prior work.
4. **Tables and figures** — they explicitly excluded; we handle.
5. **Cross-domain** — their corpus is biomedical only.
6. **Practitioner tool** — Claude Code-native author/reviewer workflow vs. academic corpus study.

## Corpora

### Primary

**1. Sarol-corpus benchmark — head-to-head vs. prior work.**
Directly benchmark paper-trail against MultiVerS and GPT-4 few-shot on the public Sarol et al. 2024 corpus. Two variants:

- **A (abstract-only, apples-to-apples):** feed paper-trail only the citing sentence + cited paper's title/abstract. Match their evaluation setup. Target: meet or exceed MultiVerS 0.59 micro / 0.52 macro F1 and GPT-4 4-shot 0.65 / 0.45.
- **A' (full-paper wedge):** resolve each cited `doc_id` → PMC article → full text, ingest via GROBID, let paper-trail use the whole paper. Metric: ΔF1 over A, broken down by error class. Demonstrates the full-paper advantage that motivates the tool.

Label mapping (draft): CONFIRMED → ACCURATE; OVERSTATED / UNSUPPORTED / CONTRADICTED / MISATTRIBUTED → NOT_ACCURATE; CITED_OUT_OF_CONTEXT → IRRELEVANT; AMBIGUOUS → exclude or report separately.

Data: 922 held-out claims (dev 316 + test 606); 8,515 reference abstracts. Located in `Data/multivers-format/` of their repo, SciFact-compatible JSONL.

Adapter work required: paper-trail runs on full manuscripts; we need a thin driver that feeds one (citing_sentence, source) pair at a time. Closest existing mode: `--scope=single`. Estimated ~1 day.

**2. Synthetic error injection — controlled precision/recall on paper-trail's native rubric.**
Take a small clean set (user's own + lab cohort volunteers). Inject controlled errors across the full verdict rubric. Run paper-trail blind. Metric: precision/recall per verdict class. Complements Experiment 1 by testing the fine-grained labels that Sarol et al. had to collapse.

**3. Opt-in lab cohort — real-world case studies.**
Recruit N volunteers from the lab (initial target: 5–10 papers). Run reader-mode on their published papers. Review findings with each author; capture TP, FP, and "minor-but-valid" classifications. Deliverable: error-class taxonomy with real, author-validated examples. Shows the tool works on arbitrary real papers, not just a curated corpus.

### Secondary

**4. Published errata/corrigenda — recall against author-acknowledged errors.**
Via PubMed `CommentsCorrections` linkage (22k+ errata in 2024 alone). For citation-level corrections, re-run paper-trail on the pre-correction paper and measure recall. Non-accusatory, public-record ground truth. Pilot to quantify what fraction of corrections are actually citation-level.

**5. (Dropped) Citation-distortion chain reproduction.**
Greenberg 2009 / Hagen 2022 / Brown 2024 chains — considered for reproduction but **Sarol et al. 2025 (ASIS&T) already ran the LLM replication of Greenberg**. Dropped to avoid direct overlap.

## Experiments

| # | Corpus | Experiment | Metric | Baselines |
| - | --- | --- | --- | --- |
| 1A-3way | Sarol-2024 | Chunk-grounded claim verification, paper-trail verdict collapsed to 3 classes | Micro/macro F1 (3-way) | MultiVerS 0.59/0.52; GPT-4 4-shot 0.65/0.45 |
| 1A-9way | Sarol-2024 | **Same data, fine-grained 9-way evaluation — no existing baselines** | Per-class F1, macro F1 (9-way) | None (Sarol et al. abandoned this granularity) |
| 1A' | Sarol-2024 + PMC full text | Full-paper ingest instead of pre-chunked corpus | ΔF1 vs 1A, broken down by label | Experiment 1A |
| 2 | Synthetic injection | Blind detection across full paper-trail verdict rubric | Precision/recall per verdict class | — |
| 3 | Opt-in lab cohort | Human-validated findings on 5–10 real papers | Error-class taxonomy, TP/FP rate | — |
| 4 | PubMed errata | Recall on citation-level author-acknowledged corrections | Recall on pre-correction manuscripts | — |
| 5 | Shared subset of (1A' / 3) | Qualitative head-to-head vs SemanticCite on same papers | Case-level comparison of findings | SemanticCite 4-class output |

**Why 1A-9way is the headline experiment.** Sarol et al. collapsed 8 annotated classes into 3 because their retrieval+classifier pipeline couldn't learn fine-grained distinctions. The fine-grained labels are still in the public test/dev data but nobody has ever reported numbers on them. Agentic full-paper reading is precisely the regime where fine-grained verdicts become tractable, so 1A-9way is where paper-trail's architecture most visibly differentiates. There are literally no baselines to beat because no one has tried.

## Ethics & consent

- **Synthetic:** no ethical issue — injected errors on own / consenting papers.
- **Opt-in:** consent per author; findings discussed and validated; any public naming is opt-in.
- **Errata:** authors have publicly acknowledged the error; aggregate recall stats only, no naming. Open question: courtesy email to authors included in the analysis?
- **Distortion:** Greenberg-style chains are already published analyses; we reproduce, not accuse. Open question: courtesy contact with the original chain authors.

## Scraping recipes

### Errata via Crossref

- API: `https://api.crossref.org/works?query.title=corrigendum&filter=from-pub-date:2024&rows=100`
- Alt queries: `erratum`, `correction to`.
- Parse each hit: corrected-paper DOI (via `relation.is-correction-of` or text match), correction text, publication date.
- Classify correction type with a light LLM pass.

### Errata via PubMed Central

- E-utilities: `esearch.fcgi?db=pubmed&term=published+erratum[ptyp]`
- Biomedical-focused; pairs well with Paperclip cache for source fetching later.

### Citation-distortion literature via Semantic Scholar

- API: `https://api.semanticscholar.org/graph/v1/paper/search?query=citation+distortion`
- Parallel queries: `citation accuracy`, `quotation accuracy`, `reference accuracy`, `citation drift`.
- Seed: Greenberg SA 2009 BMJ DOI; pull forward citations.

## Open questions

- **Author courtesy outreach.** Policy for errata and distortion corpora — aggregate-only, or individual notice with right of reply?
- **Scope.** Single-discipline (biomedical, matches Paperclip) vs cross-discipline?
- **Venue.** arXiv preprint + methods journal (e.g., PLoS ONE, F1000) vs discipline-specific?
- **Release timing.** Tool release vs preprint timing — simultaneous to establish priority, or stagger?

## Appendix: dataset inventory

### Sarol 2024 corpus (primary external benchmark)

Downloaded locally 2026-04-20 from [ScienceNLP-Lab/Citation-Integrity](https://github.com/ScienceNLP-Lab/Citation-Integrity) `Data/multivers-format/`. License: **MIT** (repo-wide LICENSE file). Total ~6.0 MB JSONL.

**Files:**

| File | Rows | Size |
| --- | --- | --- |
| `claims-train.jsonl` | 2,141 | 2.1 MB |
| `claims-dev.jsonl` | 316 | 274 kB |
| `claims-test.jsonl` | 606 | 488 kB |
| `corpus.jsonl` | 8,515 | 5.1 MB |

**Claim record schema** (`claims-*.jsonl`):

```json
{
  "id": 0,
  "claim": "It has been proposed that COVID-19 leads to deterioration of hepatic function... [<|multi_cit|>].",
  "evidence": {
    "31094": [{"sentences": [3], "label": "ACCURATE"}],
    "31004": [{"sentences": [4], "label": "ACCURATE"}, {"sentences": [5], "label": "ACCURATE"}]
  },
  "cited_doc_ids": [31000, 31001, ..., 31088]
}
```

- `claim`: the citing sentence with `<|multi_cit|>` or `<|cit|>` or `<|other_cit|>` marker at the citation position.
- `cited_doc_ids`: **all chunks of the single cited paper** (mean 72, median 73, max 123). Not a list of candidate papers — a list of chunks of one paper.
- `evidence`: the specific chunks that are relevant, each with per-sentence indices and a label.

**Corpus record schema** (`corpus.jsonl`):

```json
{"doc_id": 31004, "title": "", "abstract": ["sentence 1...", "sentence 2...", ...]}
```

- **100 cited papers** total (`doc_id // 1000` buckets; range 1–100).
- 8,515 chunks total, **mean 85 chunks/paper** (median 77, max 323).
- `title` is blank for all 8,515 entries. The "abstract" field is misnamed — it's actually paragraph-level body-text chunks of the cited paper (methods, results, figure legends, etc.), not the paper's abstract.
- Only 8.3% of chunks contain inline citations; the rest make direct scientific claims — which is the agentic-reading sweet spot.

**Key statistics (test + dev, 922 claims):**

- Claims with multi-citation marker (`<|multi_cit|>`): **471/922 (51%)** — must handle.
- Distinct cited-docs-with-evidence per claim: mean 1.23, median 1, max 6.
- Evidence annotations per claim: mean 2.0, median 2, max 18.
- Claim text length: mean 198 chars, median 175, max 3,218.
- 0 claims have mixed labels across docs — per-claim labeling is consistent.

**Label distribution (test + dev, 1,873 evidence annotations):**

| Sarol label | Count | % | Proposed paper-trail verdict |
| --- | ---: | ---: | --- |
| ACCURATE | 1,463 | 78.1% | CONFIRMED |
| OVERSIMPLIFY | 123 | 6.6% | OVERSTATED |
| NOT_SUBSTANTIATE | 112 | 6.0% | UNSUPPORTED |
| CONTRADICT | 65 | 3.5% | CONTRADICTED |
| MISQUOTE | 40 | 2.1% | MISATTRIBUTED (numerical) |
| INDIRECT | 36 | 1.9% | INDIRECT_SOURCE |
| INDIRECT_NOT_REVIEW | 17 | 0.9% | INDIRECT_SOURCE (variant) |
| ETIQUETTE | 16 | 0.9% | AMBIGUOUS / CITED_OUT_OF_CONTEXT |
| IRRELEVANT | 1 | 0.1% | exclude (too rare) |

Sarol et al.'s published 3-way collapse (per their paper): ACCURATE → ACCURATE; OVERSIMPLIFY / NOT_SUBSTANTIATE / CONTRADICT / MISQUOTE / INDIRECT → NOT_ACCURATE; ETIQUETTE / INDIRECT_NOT_REVIEW / IRRELEVANT → IRRELEVANT.

**Worked example per class (first test-split hit for each):**

- **ACCURATE.** Claim: "Dietary L-carnitine and choline… are metabolized into TMAO by gut commensals; in mice TMAO enhances atherosclerosis…" Cited chunk: "Chronic dietary L-carnitine supplementation in mice significantly altered cecal microbial composition, markedly enhanced synthesis of TMA/TMAO, and increased atherosclerosis…" → Direct match.
- **OVERSIMPLIFY.** Claim: "In apoE-deficient mice fed L-carnitine, atherosclerosis was also mediated by a microbiota-dependent mechanism." Same cited chunk as above. The cited paper established the mechanism in general mice; the citing paper overgeneralizes to apoE-deficient specifically.
- **NOT_SUBSTANTIATE.** Claim ties β-cell function to T2D risk; cited chunk describes a meta-analysis methodology, not a risk-lowering finding.
- **CONTRADICT.** Claim: "Increased TMPRSS2 in asthmatic patients may predispose them to COVID-19." Cited chunk: "expression levels of both genes were similar in asthma and health." Direct contradiction.
- **MISQUOTE.** Claim states DIAGRAMv3 identified additional common variants; cited chunk is a liability-variance derivation — wrong paper / wrong content.
- **INDIRECT.** Citing claim attributes a finding to ACE2 being the SARS receptor; cited chunk itself credits "Li et al. 2003" — classic indirect citation (citing a review that cites the primary source).
- **ETIQUETTE.** Citing sentence lumps multiple ideas with `<|multi_cit|>`; cited chunk is only tangentially related — ambiguous what the citation marker was actually supporting.

**Class imbalance implications:**

- 78% ACCURATE means a trivial always-ACCURATE baseline gets 0.78 accuracy, but F1-macro is bounded by the minority classes where all the signal is.
- IRRELEVANT (1 instance) should be excluded from per-class reporting.
- Minority error classes (OVERSIMPLIFY, NOT_SUBSTANTIATE, CONTRADICT, MISQUOTE, INDIRECT) each have 36–123 instances — enough for meaningful per-class F1.

### SemanticCite dataset (concurrent-tool comparator, not primary benchmark)

From [sebsigma/SemanticCite-Dataset](https://huggingface.co/datasets/sebsigma/SemanticCite-Dataset). Single JSON file, 6.29 MB, 1,111 rows, one split (`train`), no dev/test partition.

**License:** CC-BY-NC-4.0.

**Record schema** (abbreviated):

```json
{
  "claim": "preprocessed citation text with reference markers removed",
  "ref_snippets": [{"text": "...", "relevance_score": 0.x, "chunk_id": "..."}],
  "ref_metadata": {"title": "...", "authors": [...], "year": 2019, "abstract": "..."},
  "classification": "PARTIALLY_SUPPORTED",
  "reasoning": "...",
  "confidence": 0.7,
  "citation_text": "raw citation text as in original paper",
  "citation_type": "RESULT_COMPARISON",
  "citation_numerical": true,
  "citation_field": ["Medicine", "Materials Science"],
  "citation_url": "https://www.semanticscholar.org/paper/..."
}
```

**Labels:** 4-way — SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / UNCERTAIN. **LLM-generated by GPT-4.1**; no human annotation, no inter-annotator agreement, no disclosed label distribution.

**Disciplines (8):** Computer Science, Medicine, Chemistry, Biology, Materials Science, Physics, Geology, Psychology. ~500 papers per field with equal distribution across citation-impact tiers.

**Why not a primary benchmark:** F1 against GPT-4.1-labeled data mostly measures alignment with GPT-4.1, not citation-integrity skill.

**Why still useful:**

1. **Qualitative head-to-head.** Run both tools on the same papers, compare findings case-by-case (Experiment 5).
2. **Cross-domain stress test.** If we need to demonstrate paper-trail on non-biomed (CS, Physics, etc.), this is the closest thing to a cross-domain corpus.
3. **Citation-type tagging** (`RESULT_COMPARISON`, `METHOD_REFERENCE`, `BACKGROUND`) is a dimension Sarol lacks; could inform a secondary analysis.

## Pilot results

### Crossref corrigenda (2024-04-20)

- `query.title=corrigendum` + `from-pub-date:2024-01-01` + `type:journal-article`: **23,857 hits**. Plenty of volume.
- Issue: `relation.is-correction-of` was empty in 0/20 sampled. Linking a corrigendum back to the original paper's DOI requires either (a) parsing the corrigendum's body text or (b) cross-walking through PubMed's `CommentsCorrections` or (c) resolving `container-title` + issue/volume back to the original.
- Implication: Crossref gives volume but not ground-truth linkage out of the box. PubMed is probably the better spine.

### PubMed errata (2024-04-20)

- `"published erratum"[Publication Type] AND 2024[pdat]`: **22,629 hits** in 2024 alone.
- PubMed's `CommentsCorrections` field usually links erratum → original paper cleanly. TODO: confirm on a 50-paper sample that linkage + original-paper full text availability (OA or via institutional access).

### Semantic Scholar citation-distortion literature (2024-04-20)

Surfaced the full Sarol / Schneider / Kilicoglu body of work (now in the Related Work section). The Greenberg chain reproduction angle was eaten by Sarol et al. 2025 (ASIS&T).

### Sarol et al. 2024 corpus inspection (2024-04-20)

Pulled `Data/multivers-format/` from [ScienceNLP-Lab/Citation-Integrity](https://github.com/ScienceNLP-Lab/Citation-Integrity):

- `claims-{train,dev,test}.jsonl`: 2,141 / 316 / 606 claim instances. Schema: `{id, claim, evidence: {doc_id: [{sentences, label}]}, cited_doc_ids}`. Claims include a `<|multi_cit|>` marker at the citation position. Labels: ACCURATE / NOT_ACCURATE / IRRELEVANT.
- `corpus.jsonl`: 8,515 entries. Schema: `{doc_id, title, abstract}` where `abstract` is a sentence-list. **Titles are blank; "abstract" is actually paragraph-level chunks from the cited paper's body** (~85 chunks per paper × 100 papers). Only 8.3% of chunks contain inline citations — the rest make direct scientific claims. Good for agentic full-text reading.
- Held-out eval set: **922 claims** (dev + test).

### Dataset scope triage (2024-04-20)

Surveyed other claim-verification datasets and filtered by our citation-integrity scope (claim tied to a specific cited source, ground truth is "does the named source support this claim"):

- **In scope:** Sarol 2024 corpus — the only external benchmark that fits.
- **Out of scope:** SciFact / SciFact-Open / HealthVer / COVID-Fact / PubHealth / MSVEC / SciClaimHunt / Valsci / SourceCheckup. All are either general claim verification, open-corpus retrieval, or fact-checking of public claims — different task classes, larger blast radius, and would drag our story into ground we've explicitly excluded.

### Implications for plan

1. **Sarol 2024 is the single external benchmark.** All other external validation has to come from our own synthetic + opt-in + PubMed-errata work.
2. **Hygiene framing + citation-integrity scope is the spine.** Explicitly distinguish from general claim verification and from literature-search tools like Valsci in related work.
3. **PubMed over Crossref** as the errata spine: cleaner linkage, better OA availability for biomed.

