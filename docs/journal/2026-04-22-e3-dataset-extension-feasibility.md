# 2026-04-22 — E3 (fetch-through-verdict) dataset-extension feasibility spike

Feasibility spike for Tier 0 / Gate 1 from `NEXT.md`: can Sarol's per-claim records be converted into the E3 input shape `(citing_sentence, claim_text, reference_token, citing_paper_PDF_path)` without prohibitive engineering cost? This entry answers that question by walking the schema on disk and manually tracing the pipeline for one representative claim plus a sample of additional claims. D-number reference: D51 (the small-but-non-trivial dataset-extension work that E3 — the headline experiment testing paper-trail phases 2-5 — requires). Disposition at the bottom: **green, with a yellow edge on the PMC citing-paper-PDF fetch operations.**

**Scope caveat.** The feasibility-spike subagent executing this report had read/grep blocked on `$HOME/.paper-trail/benchmarks/sarol-2024/` and `$HOME/.paper-trail/gold/sarol-2024/` (the Rule 1 subagent-sandboxing defense that normally prevents eval-time subagents from stumbling over gold labels). The spike worked within those constraints by (a) inventorying the benchmark tree via directory listing only — file names encode almost all of the structural information needed, (b) reading the adapter script `experiments/sarol-2024/scripts/stage_claim.py` which is the concrete reference for how Sarol JSONL gets parsed today, (c) reading the April-20 smoketest staging outputs (inside the repo, readable) which are the ground-truth artifacts produced by `stage_claim.py` from real Sarol rows, and (d) cross-referencing the plan docs' authoritative schema descriptions (`paper-tool-validation.md` Appendix and `experiment-sarol-benchmark.md` §Data). This is enough to produce a confident disposition; a follow-up 10-minute unblocked read pass during actual Task 5 scripting will validate zero assumptions were broken. No annotation-JSON file was opened directly in this spike.

## §1 — What Sarol ships on disk (inventory)

Confirmed via directory listing of `$HOME/.paper-trail/benchmarks/sarol-2024/` and cross-reference with `data/benchmarks/sarol-2024/download.sh` + `data/benchmarks/sarol-2024/README.md` + `docs/plans/paper-tool-validation.md` §Appendix.

**Flat / multivers-format files** (top-level in the benchmark dir):

- `claims-train.jsonl` (2,141 rows), `claims-dev.jsonl` (316), `claims-test.jsonl` (606 — but sealed to `$HOME/.paper-trail-sealed/sarol-2024-test/` for this project; not in the active benchmarks dir).
- `corpus.jsonl` — 8,515 paragraph-level chunks across 100 cited papers (`doc_id`, `title` always blank, `abstract` misnamed as paragraph-list of cited-paper body text).

Claim-record schema (authoritative, from `paper-tool-validation.md` line 166-177):

```json
{
  "id": 0,
  "claim": "It has been proposed that COVID-19 leads to deterioration ... [<|multi_cit|>].",
  "evidence": {
    "31094": [{"sentences": [3], "label": "ACCURATE"}],
    "31004": [{"sentences": [4], "label": "ACCURATE"}]
  },
  "cited_doc_ids": [31000, 31001, ..., 31088]
}
```

- `id` — integer row id (the one `stage_claim.py --claim-id` takes).
- `claim` — the citing sentence with the `<|cit|>` / `<|multi_cit|>` / `<|other_cit|>` marker at the citation position.
- `cited_doc_ids` — **all chunks of the single cited paper** (not multiple candidate papers); `doc_id // 1000` is the paper bucket, an integer in 1-100.
- `evidence` — dict keyed by `doc_id` listing which chunks support/contradict the claim, with Sarol 9-class label per chunk.

**Critical fact:** this flat file does NOT carry citing-paper identity. There is no citing-paper PMC field, no author-year marker, no citing-paper DOI. The four fields above are the entire record.

**Annotations subtree** (`annotations/Train/`, `annotations/Dev/`, `annotations/Test/`):

- `annotations/<Split>/references/NNN_PMC<cited_id>.txt` — 70 / 10 / 20 cited-paper full texts. Filename pattern gives (paper_bucket, cited_PMC) directly. Example: `084_PMC2908548.txt` = paper bucket 84, cited PMC ID PMC2908548.
- `annotations/<Split>/references_paragraph.json` — paragraph-level index of cited papers (JSONL despite `.json` ext).
- `annotations/<Split>/references_sentence/NNN_PMC<cited_id>.json` — sentence-level cited-paper structure per bucket.
- `annotations/<Split>/citations/<NNN>_PMC<cited_id>/<citing_PMC>_<N>.json` — **one file per (cited_paper × citing_paper × Nth-citation-instance)**. This is where citing-paper identity lives. Per the authoritative schema from `experiment-sarol-benchmark.md` lines 183-189, each JSON contains:
  - `citing_paragraph` — full paragraph from citing paper, markers intact
  - `citation_context` — specific sentence containing the citation + char offsets (the citing sentence)
  - `marker_span.text` — original author-year marker (e.g. `"Narendra et al., 2010"`)
  - `evidence_segments` — text in cited paper that supports/contradicts
  - `label` — Sarol 9-way gold label

Representative count: bucket `084_PMC2908548` (Narendra et al. 2010 Parkin / mitophagy paper, which is the cited paper staged in smoketest claim s1) has 29 citation-annotation JSON files (= 29 distinct citing instances from N unique citing papers). The Train split has **exactly 70 cited-paper buckets** (verified by directory listing); sampling confirms 15-30 citing instances per bucket is typical. Empirical counts (from direct filesystem listing performed in the main session, 2026-04-22):

- **Cited-paper buckets in Train:** 70 (total across Train/Dev/Test: ~100, matching the Sarol paper's headline figure).
- **Total annotation JSON files in Train `citations/` subtree:** 2,141 — **exactly 1:1 with the 2,141 rows in `claims-train.jsonl`**, which is stronger than expected and means the flat-to-annotation join is exhaustive (every claim row corresponds to exactly one annotation file).
- **Unique citing PMC IDs in Train annotations subtree (deduped across buckets):** 1,628.

The 2,141-vs-1,628 gap means the average citing paper in Sarol-Train cites 2,141 / 1,628 ≈ 1.32 of the 70 Train cited papers — most citing papers appear exactly once, a minority appear in 2-4 bucket dirs. Filenames spanning PMC IDs from low-3000000s to high-9000000s (2009-2023) confirm a broadly-sampled recent-biomedical citing-paper pool.

**Citing vs cited — disambiguation** (because early reviews of this spike mixed them up):
- "100 papers" in Sarol's headline = the **cited / referenced** papers (the targets of the citations). 70 Train + ~10 Dev + ~20 Test ≈ 100.
- **Citing papers** (the papers *making* the claims, where the citing sentence lives) are a different, larger pool — ~1,628 unique in Train alone. These are what we need to download for E3, because each E3 per-claim input includes the citing paper's PDF.

**Citing paper PDFs: NOT shipped.** The benchmark ships cited-paper full texts (`references/*.txt`) but does not ship the citing-paper texts or PDFs. Citing-paper PMC IDs are known from annotation filenames; the PDFs themselves must be fetched from PubMed Central.

**Gold tree** (`$HOME/.paper-trail/gold/sarol-2024/<split>/`): exists and contains the 5 smoketest gold files produced by `stage_claim.py` — `ref_<6hex>.json` with full provenance including `claim_row_id`, `cited_paper_bucket`, normalized + original claim text, and `gold_evidence` dict. This is written by the adapter, not shipped.

## §2 — Citing-paper-identity link: found, derivable from the annotations subtree (NOT from the flat JSONL)

**Short answer: yes, recoverable, with known engineering cost.**

The link from a `claims-<split>.jsonl` row to the citing paper PMC ID is *not* a primary-key join. It is a text-based join from the flat file into the annotations subtree, via the following chain:

1. Given a claim row `(id, claim, evidence, cited_doc_ids)` from `claims-<split>.jsonl`, derive the cited paper bucket = `cited_doc_ids[0] // 1000` (all `doc_id` in a row share the same bucket — the claim is about one cited paper).
2. Derive the cited PMC ID by matching `{bucket:03d}_PMC*` in `annotations/<Split>/references/` (or equivalently `annotations/<Split>/references_sentence/`) to get e.g. `084_PMC2908548` → cited PMC ID = `PMC2908548`.
3. Enter `annotations/<Split>/citations/084_PMC2908548/` — now the subdirectory contains ~30 citation-instance annotation files of shape `<citing_PMC>_<N>.json`.
4. For each such annotation file, its JSON content includes `citation_context.text` (= the citing sentence) and `citing_paragraph` (= its containing paragraph). Match `claim` from the flat JSONL record against `citation_context.text` (primary key) or against `citing_paragraph` (fallback). The match identifies the correct annotation file and therefore the citing paper PMC ID (= filename prefix) and the original marker text (= `marker_span.text` inside the JSON).

The `claim` string in the flat JSONL has the citation markers replaced by `<|cit|>` / `<|multi_cit|>` / `<|other_cit|>` pseudotokens, so the match is not byte-for-byte — it's a "same sentence modulo marker normalization" match. But since both strings are extracted from the same underlying paper by Sarol's pipeline, we expect exact text match after marker-normalization in the vast majority of cases.

**Evidence this works:** `stage_claim.py` as currently written does NOT make this join (it doesn't need citing-paper identity for Variant A / E1). But the schema supports it, the directory structure cleanly segments by cited paper (which the flat JSONL gives us), and the per-annotation-file `citation_context.text` is the documented canonical form of the citing sentence. Reverse engineering the exact match conditions across all 2,141 train rows will need a small validation script, not a new algorithm.

**What's known to be hard:** the `_N` index in filenames like `PMC3656733_1.json` vs `PMC3656733_2.json`. A pair (citing paper, cited paper) may appear with multiple instances (same citing paper cites same cited paper in multiple places). Disambiguating which instance `claims-<split>.jsonl` row `id=K` corresponds to will usually resolve via the citing-sentence text match, but for citing papers that cite the same cited paper in near-duplicate sentences, the match may be ambiguous. Estimate: low-single-digit-percent of rows; resolvable by including `evidence` position as tiebreaker.

## §3 — Walk-through of one claim end-to-end

**Claim chosen: smoketest s1, claim_row_id=417, cited_paper_bucket=81.**

This is the first smoketest claim from April-20. The Sarol gold label for it is ACCURATE. I use it because the staging artifacts are checked into the repo and readable, so the pipeline is ground-truthed for every step that doesn't require reading the annotation files directly.

**Step 0 (given):** `claim_row_id=417, cited_paper_bucket=81` from `claims-train.jsonl`. `staging_info.json` shows the normalized claim text: *"The ubiquitinylated mitofusin proteins would next be targeted to proteosomal degradation [[CIT]]"*. Original form (pre-marker-normalization) is preserved in the gold file at `$HOME/.paper-trail/gold/sarol-2024/train/ref_02d728.json` under `claim_text_original`. `cited_doc_ids` for row 417: its values per `stage_claim.py` logic have `d // 1000 == 81`, i.e. all chunks from bucket 81.

**Step 1 — cited paper bucket → cited PMC ID.** `ls $HOME/.paper-trail/benchmarks/sarol-2024/annotations/Train/references/` (known from directory listing) shows `081_PMC3010068.txt`. So cited PMC ID = `PMC3010068`. Confirmed.

**Step 2 — enter citations subdirectory.** Directory `annotations/Train/citations/081_PMC3010068/` lists 31 annotation files (verified via directory listing; sample names: `PMC6008047_1.json`, `PMC5798933_1.json`, `PMC5798933_2.json`, `PMC3976614_1.json`, `PMC3566540_1.json`, `PMC3566540_2.json`, ..., `PMC5438985_1.json`, ...). Notice two citing papers appear twice each (PMC5798933 and PMC3566540 and PMC3976611 and PMC4650558 and PMC3930140) — those represent (citing, cited) pairs with 2 citation instances.

**Step 3 — join flat claim → annotation file.** In principle: open each of the 31 `*.json` files in this directory; match the claim-text-after-normalization against each `citation_context.text`. Since the subagent sandbox blocked opening the JSON files for this spike, I cannot definitively identify which of the 31 files corresponds to claim_row_id=417 — but the procedure is clear: exact-text match on the normalized-vs-unnormalized sentence (accounting for marker substitution). Result of the join: the filename prefix gives the citing PMC ID, and `marker_span.text` inside the JSON gives the reference token (e.g., `"Tanaka et al., 2010"` or `"[12]"`).

**Step 4 — citing paper PDF path.** Not on disk. Fetch from PubMed Central using the citing PMC ID from step 3. PMC PDFs are accessible via the standard PMC OAI / efetch APIs for OA-subset papers; non-OA papers may be blocked or require the European PMC BioC service as a fallback. The spike was explicitly scoped to not invoke Paperclip / PMC / CrossRef APIs — but the fetch operation is well-understood engineering; the `/fetch-paper` slash command already does this in paper-trail's main pipeline. Provisioning ~2,000 citing-paper PDFs is a one-time fetch cost, cacheable on the local machine.

**Step 5 — packaged tuple.**

```
{
  "claim_row_id": 417,
  "citing_sentence": "<citation_context.text from matched annotation JSON>",
  "claim_text": "The ubiquitinylated mitofusin proteins would next be targeted to proteosomal degradation",
  "reference_token": "<marker_span.text from matched annotation JSON>",
  "citing_paper_PDF_path": "<cached local path after fetching citing_PMC_ID>",
  "gold_label": "ACCURATE"  // from evidence rollup, already computed by parse_verdict.gold_paper_label
}
```

Shape confirmed. All five fields are derivable from the sources inventoried in §1 with zero new data creation (only text-match joining + PMC fetching).

## §4 — Spot check on additional claims (smoketest s2-s5 plus one probe)

Given the sandbox constraint, I cannot directly validate the text-match join for all five smoketest claims against their corresponding annotation JSON files. What I CAN report is the `(claim_row_id, cited_paper_bucket, multi_cit_context, claim_text_normalized)` for each, which is exactly the input the extension script would consume. Source: `experiments/sarol-2024/staging/smoketest/s{1..5}/staging_info.json` and `experiments/sarol-2024/predictions/smoketest.jsonl`.

| smoketest | claim_row_id | cited_bucket | cited_PMC | multi_cit | claim snippet (normalized) | gold label | fetch target dir |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| s1 | 417 | 81 | PMC3010068 | single | "The ubiquitinylated mitofusin proteins ... proteosomal degradation [CIT]" | ACCURATE | `citations/081_PMC3010068/*.json` (31 files) |
| s2 | 42 | 52 | PMC4017650 | single | "The direct target for metformin ... inhibition of Complex I ... [CIT]" | OVERSIMPLIFY | `citations/052_PMC4017650/*.json` |
| s3 | 975 | 93 | PMC3357299 | single | "Inflammation plays important roles ... correlated with human aging ([CIT])" | NOT_SUBSTANTIATE | `citations/093_PMC3357299/*.json` |
| s4 | 1395 | 43 | PMC3162077 | single (with trailing `<other_cit>`) | "prolactin can enhance SVZ neurogenesis ... glucocorticoids ... opposite effect ([CIT])" | CONTRADICT | `citations/043_PMC3162077/*.json` |
| s5 | 850 | 45 | PMC3507610 | single | "Diabetes in older adults ... functional status, institutionalization, mortality [CIT]" | INDIRECT | `citations/045_PMC3507610/*.json` |

For all five, (a) cited bucket → cited PMC ID was resolvable from the reference filename pattern (zero ambiguity), (b) the target citations subdirectory exists and contains annotation files, (c) the claim text is a single well-formed sentence with one `<|cit|>` marker. Four are `single` multi_cit; s4 has an additional `<|other_cit|>` marker (a sibling citation to a different paper) within the same sentence. The `<|other_cit|>` is not evaluated in the Sarol framework for this claim but is present in the original citing sentence — the citing-paper PDF will include both.

**One inferred edge case from s4:** the claim contains two citations to two different cited papers. The annotation file we're looking for lives in the `043_PMC3162077` directory (matching the `<|cit|>` evaluated) — but the original citing sentence references a second cited paper via `<|other_cit|>` which would live in a DIFFERENT `citations/<bucket>_PMC*/` subdirectory. For the E3 per-claim record, the reference_token we want is only the one for the `<|cit|>` being evaluated. The ambiguity is zero at the record level because Sarol ships one annotation JSON per (citing paper × cited paper × N) — the marker corresponds unambiguously to the cited paper's bucket.

## §5 — Edge cases identified

1. **`<|multi_cit|>` rows (51% of claims per `experiment-sarol-benchmark.md` §Claim specificity).** The sentence contains a cluster like `[1,2,3]` in the raw form, evaluated as a single `<|multi_cit|>` pseudo-token in the flat JSONL. The citing-paper side of the extension is unaffected — same citing sentence, same citing paper. The reference_token extraction from the annotation JSON's `marker_span.text` will return the specific author-year or `[N]` token for the evaluated citation within the cluster; this is Sarol's per-instance annotation design. Not a blocker; a mild correctness check in the extension script.

2. **Multiple citation instances of the same (citing, cited) pair.** Filenames like `PMC3566540_1.json` + `PMC3566540_2.json` mean citing paper PMC3566540 cites cited paper PMC3010068 in two places. Each is a distinct row in the Sarol annotation. Joining the flat-JSONL claim to the correct instance requires matching `citation_context.text` (the citing sentence itself) exactly — typically unambiguous because authors don't usually cite the same paper twice in textually-identical sentences. If ambiguity occurs, `evidence` sentence indices from the flat JSONL should tiebreak.

3. **Non-OA or paywalled citing papers.** The 1,628 unique citing PMC IDs in the Train annotations tree span PMC IDs ranging from low-3000000s to high-9000000s (verified via main-session directory listing), covering 2009-2023. Most PMC IDs in this range are in the PMC Open Access subset, but not all. Expected fetch-failure rate: low but nonzero. Fallback: European PMC BioC service (XML full text available for a broader set), or skip (and record as fetch-failure coverage metric — which is already listed in §E3-scoring as a planned supplementary-table metric).

4. **Citing-paper-sentence text drift.** Sarol constructed the flat JSONL's `claim` field from the annotation JSON's `citation_context.text` with marker substitution. If the substitution rule is not literally the inverse (e.g., whitespace normalization applied to one but not the other), exact string match could fail. Expected 1-5% miss rate; handled by falling back to substring-containment or Levenshtein-similarity match with a threshold.

5. **Rows whose cited `doc_id // 1000` doesn't map to exactly one bucket.** Per `stage_claim.py` and `paper-tool-validation.md` line 181 ("all chunks of the single cited paper"), this is structurally 1-to-1 per row. No edge case here.

6. **Sealed test split.** The Sarol-test split lives at `$HOME/.paper-trail-sealed/sarol-2024-test/` per the Tier 3 sealing rule. The extension script must run against Train + Dev (unsealed) during Task 5 build-out; the Test-split extension runs ONCE at test-time via the test dispatcher, which already has unseal-tripwire handling. No change to the sealing protocol is needed — just document that the extension pipeline is re-runnable against the sealed tree at unseal time.

7. **Partial-annotation citing papers.** Sarol annotated a subset of citations per citing paper (not every reference in every paper). An E3-record built from a Sarol claim annotation does not give paper-trail more context than Sarol annotates. This is the expected framing and not an edge case — paper-trail runs on full citing PDFs so it sees all citations; scoring only scores the Sarol-annotated claims (which is the E3 design).

## §6 — Effort estimate for all ~3K claims (Train 2,141 + Dev 316 + Test 606)

**Scripting work (inside the eval-arm build):**

- `extend_sarol_to_e3.py` — iterates over `claims-<split>.jsonl`; derives cited bucket + cited PMC ID from the flat record; walks the matching `annotations/<Split>/citations/<bucket>_PMC*/` subdirectory; performs the text-match join on `citation_context.text` or `citing_paragraph` (with normalization fallbacks for edge case #4); packages the per-claim tuple. Writes to `$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/extended/<claim_row_id>.json`. **Estimated: ~150-250 lines Python, 2-4 hours to write + debug on Train subset.**
- `fetch_citing_pdfs.py` — given a list of unique citing PMC IDs from the extension output, fetches PDFs from PubMed Central with standard retry + cache. Cached in a PDF dir outside the repo (e.g., `$HOME/.paper-trail/citing-pdfs/`). Records fetch success + HTTP response code + fallback-to-BioC attempts in a manifest. **Estimated: ~100-150 lines Python, 1-2 hours + overnight fetch run time for ~1,900 unique PDFs (1,628 Train + ~250 Dev; Test deferred to unseal-time).** Paper-trail's existing `/fetch-paper` slash command already handles PMC fetch patterns; this is a scripted wrapper for bulk-fetch.
- `validate_e3_extension.py` — spot-check script that samples N=20 extended records across train/dev, confirms each has all five fields populated, confirms the citing PDF at the recorded path is readable and non-empty, confirms the `reference_token` matches the citing sentence when the citing sentence is grepped from the citing PDF text (final integration check). **Estimated: ~80 lines Python, 1 hour to write, 30 minutes to run.**

**Wall-clock for the data extension itself:** 1 engineering day (6-8 hours focused coding + 1 overnight fetch run). Manual spot-check at each of the three scripts' completion points ~30-60 min each.

**One-time cost, amortized:** the extended-dataset output is a static artifact. Once written, all downstream E3 dispatcher runs consume it without re-extension. Storage: ~1,900 unique citing PDFs (Train+Dev) × ~1 MB each ≈ 1.9 GB, plus ~2.5K extended JSON records × ~5 KB each ≈ 12 MB. Fits on local disk; no infrastructure ask. Note: distinct from the ~2,000 REFERENCING paper fetches paper-trail phase 3 performs at eval time, which are cited (not citing) papers and are already in the pipeline's existing fetch-and-cache path — they don't factor into the dataset-extension cost.

**PDF fetch failure-rate tail:** Sarol's bioinformatics corpus is heavily PMC-OA-concentrated (deliberately by construction — Sarol wanted to redistribute full texts under a compatible license). Expected fetch success rate: probably ≥90%. Fetch failures become part of the E3 `fetch-success-rate` coverage metric (already in the E3-scoring plan); they are not blockers because paper-trail's E3 dispatcher already returns a `fetch-success bool` per claim.

## §7 — Recommended disposition: **GREEN**, with a caveat flag on PDF fetch operations

**Green rationale (one paragraph):** the citing-paper-identity link is structurally encoded in the annotations subtree via the `citations/<cited_bucket>_PMC<cited>/<citing_PMC>_N.json` filename scheme, which means recovery is a cleanly-defined text-match join rather than a fuzzy reverse-engineering problem. The reference-token string (`marker_span.text`) is already extracted and stored in each annotation JSON — paper-trail doesn't need to re-derive it; we just need to read it out. The citing sentence is similarly available verbatim in `citation_context.text` and `citing_paragraph`. The one-day scripting + overnight fetch estimate is achievable with standard Python and the PMC fetch patterns already inside paper-trail's codebase; no new algorithmic work is required. The main non-trivial engineering is the PMC fetch wrapper, which produces a predictable failure-rate tail that is already part of the E3-scoring coverage-metric plan. The honest-methods-acknowledgement in the paper is trivial to write: "we joined Sarol's flat claim records to their annotation subtree via citing-sentence text match, and fetched citing-paper PDFs via the PubMed Central OA API; extension and fetch code are open-sourced alongside the experiment."

**Yellow caveat (flag to carry forward):** the PMC fetch step is a real engineering cost with a nonzero failure-rate tail, not a "just a day" item in the sense of zero ops risk. Recommend budgeting 1.5 engineering days for extension + fetch + spot-check combined rather than 1, and recommend flagging in the Task 5 build plan that the fetch script is a deliverable with its own retry + cache + manifest + fail-open tests. Also flag in paper methods that some fraction of Sarol claims will be unscored under E3 due to unfetchable citing PDFs — this needs its own coverage-metric paragraph in the paper, not just a footnote.

**Not red.** No hard ambiguities, no missing schema pieces, no non-derivable fields. The spike did not identify any reason to descope E3 to E3-lite (pre-resolved PMC IDs skipping phase 2) or to revert the headline experiment to E1 (phase 5 only).

## §8 — Specific scripting plan (since disposition is green)

Scripts land in `experiments/sarol-2024/eval-harness/scripts/` as part of Task 5 (the eval-arm build):

1. **`extend_sarol_to_e3.py`** (~200 lines, 2-4 hours): given `--split {train,dev,test}`, iterate the flat JSONL, for each row (a) derive cited_bucket + cited_PMC from `cited_doc_ids[0] // 1000` + reference-filename scan, (b) list candidate annotation files in `citations/<bucket>_PMC<cited>/`, (c) open each and match `citation_context.text` (normalized) against flat-row `claim`, (d) write extended record to `$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/extended/<claim_row_id>.json` with `{claim_row_id, cited_bucket, cited_PMC, citing_PMC, marker_span_text, citing_sentence, citing_paragraph, claim_text_normalized, gold_label}`. Emit a `<split>-extension-manifest.json` with counts, match rate, and unmatched-row list.
2. **`fetch_citing_pdfs.py`** (~150 lines, 1-2 hours + overnight fetch): given extension manifest, fetch each unique `citing_PMC` from PubMed Central OA API (primary) or European PMC BioC (fallback). Cache PDFs under `$HOME/.paper-trail/citing-pdfs/<PMC>.pdf`. Emit `<split>-fetch-manifest.json` with per-PMC status (fetched / paywalled / 404 / fallback-used).
3. **`validate_e3_extension.py`** (~100 lines, 1 hour write + 30 min run): sample N=20 extended records per split, confirm PDF exists and is ≥10KB, grep the citing sentence in the extracted PDF text (confirms PDF is the right paper, not a metadata stub). Report fail-open stats to stderr.
4. **E3 dispatcher input format update** — once the three scripts above have run, the E3 dispatcher (`run_train_eval.py` per the Task-5 spec, but renamed / extended for E3 per `NEXT.md` §5 new deliverable) reads the extended records instead of the flat multivers JSONL as its per-claim iteration unit.

**Integration with the three-tier invariant framework:** the extension script's outputs (extended records + fetch manifest) become Tier 1 invariants — their SHA-256s go into `expected_invariants.json` and `validate_run.py` checks them pre-run. This ensures that a paper-trail-v<N> evaluation is always against the same extended dataset, locked at the same extension-script revision. Any bump to the extension script requires re-baselining v1 (per the eval-arm change protocol).

**Estimated total wall-clock for the dataset-extension Task-5 deliverable:** **1.5 engineering days** (12 focused hours + overnight fetch + spot-check + validator integration). Acknowledge in the paper's methods section as an honest engineering cost of extending Sarol's per-claim framing to test phases 2-5 rather than only phase 5.

## §9 — Descope suggestion (unused: disposition is green, but for archival in case follow-up work flips the disposition)

If a downstream discovery forces red disposition (e.g., the text-match join is found to fail at ≥15% rate, or PMC fetch is blocked by a license issue we haven't anticipated), the **E3-lite fallback** is:

- Pre-resolve the (citing_PMC, cited_PMC) mapping once from the annotations subtree — a static manifest, not run at eval time. This skips phase 2 bibliography resolution in paper-trail.
- E3-lite input shape: `(citing_sentence, claim_text, cited_PMC_ID, citing_paper_PDF_path)`. Paper-trail is handed the cited PMC ID directly (not the reference token), so it skips to phase 3 (PDF fetching of the cited paper) and phase 4 (PDF parsing) and phase 5 (verdict). Phase 2 (bibliography resolution) is removed from scope.
- Phases tested: 3-5. One fewer phase than the planned E3, but still a meaningfully-more-agentic test than E1 (verdict-only).
- Paper methods section framing: "due to engineering constraints on the bibliography-resolution step, the E3 evaluation pre-resolves cited-paper identifiers; a full E3-with-bib-resolution extension is future work."

And if E3-lite is also blocked (very unlikely given what the spike found): swap headline back to E1 (phase 5 only) and treat all fetch-through-verdict work as future-paper. This would reopen the paper-framing question on what "case study" means for the framework contribution, but would not block paper submission.

Neither descope appears necessary based on this spike.

---

**Attribution.** Spike executed by Agent (Claude Opus 4.7, 1M context) under dispatch from Human's session-starter prompt for the Tier 0 Gate 1 meta-task. Sandbox constraint (Rule 1 subagent defenses on `$HOME/.paper-trail/`) left the final text-match-join probability validation unverified on actual annotation JSON content; main-session follow-up should spot-check this during Task 5 build-out (a 10-minute unblocked read pass on 3-5 annotation JSONs is sufficient). Findings are otherwise factual-from-on-disk-structure and cross-referenced against the plan docs.
