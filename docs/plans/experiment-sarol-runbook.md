# Runbook: Sarol 2024 benchmark — Variant A smoketest (N=5)

Exact step-by-step for a fresh agent to run the first Sarol benchmark smoketest. Assumes the agent is running inside Claude Code at the paper-trail repo root, on the `experiment-plan` branch (or a successor branch). Assumes `/paper-trail-init` has already been run for this machine and the paper-trail stack is functional.

Companion docs: `docs/plans/experiment-sarol-benchmark.md` (experiment strategy), `docs/plans/paper-tool-validation.md` (umbrella plan).

## What this runbook does

Run paper-trail's real extractor → Sarol-variant adjudicator → verifier pipeline against 5 stratified training claims from Sarol 2024. Emit predictions in the Sarol 9-class rubric and compare to gold labels. Sanity-check end-to-end plumbing before scaling up.

## Preconditions

- Running inside Claude Code (the agent IS the orchestrator; `/ground-claim`-style dispatch happens inline).
- Current directory: `/Users/pmayankees/Documents/Misc/Projects/paper-trail` (or wherever the repo is cloned; commands below use relative paths).
- Benchmark data present. If not:

  ```bash
  bash data/benchmarks/sarol-2024/download.sh
  ```

- Python 3 available (stdlib only — no third-party deps needed for staging or parsing).

## The 5 claims

Pre-selected, stratified, all single-cit to simplify the smoketest (multi-cit handling is a separate sweep axis):

| Gold label | claim_id | paper_bucket | Citing claim (truncated) |
| --- | --- | --- | --- |
| ACCURATE | 417 | 81 | "The ubiquitinylated mitofusin proteins would next be targeted to proteosomal degradation [CIT]" |
| OVERSIMPLIFY | 42 | 52 | "The direct target for metformin is not clearly defined, however it is believed to act via inhibition of Complex I of the..." |
| NOT_SUBSTANTIATE | 975 | 93 | "Inflammation plays important roles in the progression of obesity and diabetes..." |
| CONTRADICT | 1395 | 43 | "prolactin can enhance SVZ neurogenesis in pregnant mice (Shingo et al., OTHER), while increased levels of glucoc..." |
| INDIRECT | 850 | 45 | "Diabetes in older adults is also linked to reduced functional status, increased risk of institutionalization..." |

Claim IDs are row IDs in `data/benchmarks/sarol-2024/claims-train.jsonl`. Paper buckets are `doc_id // 1000` for the cited paper.

## Steps (per claim — repeat 5 times)

### 1. Stage the inputs

For each claim, run:

```bash
python3 experiments/sarol-2024/scripts/stage_claim.py \
  --split train \
  --claim-id <CLAIM_ID> \
  --cited-paper-id <PAPER_BUCKET> \
  --source corpus \
  --out experiments/sarol-2024/staging/smoketest/claim_<CLAIM_ID>
```

This creates a working directory with `claims_ledger.md`, `refs.bib`, and a pre-ingested handle at `pdfs/sarol_train_<PAPER_BUCKET>/` containing `content.txt`, `meta.json`, `ingest_report.json`. Also writes `sarol_manifest.json` summarizing what was staged and the gold evidence labels.

### 2. Dispatch the **evidence extractor** subagent

Use the real extractor dispatch prompt at `.claude/prompts/extractor-dispatch.md`. Substitute slots as follows:

| Slot | Value |
| --- | --- |
| `{{claim_id}}` | `C001` (use C001 for the first smoketest claim; increment across runs) |
| `{{run_id}}` | `run_sarol_smoketest_<TIMESTAMP>` |
| `{{citekey}}` | `sarol_train_<PAPER_BUCKET>` (zero-padded 3 digits) |
| `{{claim_text}}` | `manifest.claim_text_normalized` (from `sarol_manifest.json`) |
| `{{manuscript_section}}` | `Sarol benchmark — synthetic section` |
| `{{claim_type_hint.type}}` | `PARAPHRASED` |
| `{{claim_type_hint.confidence}}` | `medium` |
| `{{handle}}` | `<staging_dir>/pdfs/<citekey>/` |
| `{{ingest_mode}}` | `pdftotext_fallback` |
| `{{co_citekeys}}` | `[]` (for single-cit smoketest) |
| `{{run_output_dir}}` | `<staging_dir>` |

Dispatch the filled prompt as a subagent (same mechanism `/ground-claim` uses). The extractor writes `<staging_dir>/ledger/evidence/C001.json`.

### 3. Dispatch the **Sarol-variant adjudicator** subagent

**Critical difference from the default `/ground-claim`.** Use the variant dispatch prompt at `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` — **not** the default `.claude/prompts/adjudicator-dispatch.md`. The variant enforces the Sarol 9-class rubric.

Slot fills:

| Slot | Value |
| --- | --- |
| `{{claim_id}}` | same as step 2 |
| `{{run_id}}` | same as step 2 |
| `{{claim_text}}` | same as step 2 |
| `{{claim_type_hint.type}}` / `{{claim_type_hint.confidence}}` | same as step 2 |
| `{{multi_cit_context}}` | `manifest.multi_cit_context` (`"single"` for all smoketest claims) |
| `{{run_output_dir}}` | same as step 2 |

The adjudicator reads `<staging_dir>/ledger/evidence/C001.json` + `experiments/sarol-2024/specs/verdict_schema_sarol.md` and writes `<staging_dir>/ledger/claims/C001.json`.

**Validate on exit:**

- `rubric_variant == "sarol_2024_9class"` at top level.
- `overall_verdict` is one of the Sarol 9 classes.
- Every `sub_claims[*].verdict` is one of the Sarol 9 classes.

If validation fails: **stop and debug the adjudicator prompt or the Sarol rubric spec**. Do not fall back to the native rubric.

### 4. Dispatch the **verifier** subagent

Unchanged from paper-trail native. Use `.claude/prompts/verifier-dispatch.md`. The verifier just spot-checks the extractor's evidence against `content.txt`; it does not care about the rubric variant.

Sample one evidence entry from the adjudicated claim, fill slots, dispatch. The verifier writes `<staging_dir>/ledger/verifications/C001__C001.a.json`.

On `verdict_impact == "bounce_to_re_ground"`: re-run steps 2–3 for that claim (one bounce max in the smoketest; if it bounces again, flag and move on).

### 5. Parse the verdict into a prediction record

```bash
python3 experiments/sarol-2024/scripts/parse_verdict.py \
  --staging experiments/sarol-2024/staging/smoketest/claim_<CLAIM_ID> \
  --out experiments/sarol-2024/predictions/smoketest.jsonl
```

Appends one JSONL line with `{pred_label, gold_label, pred_3way, gold_3way, …}` to `predictions/smoketest.jsonl`.

## After all 5 claims run

Quick sanity-check script (inline):

```bash
python3 -c "
import json
for line in open('experiments/sarol-2024/predictions/smoketest.jsonl'):
    r = json.loads(line)
    hit = '✓' if r['pred_label'] == r['gold_label'] else '✗'
    print(f\"{hit} claim_id={r['claim_row_id']:>5} gold={r['gold_label']:<18} pred={r['pred_label']:<18}\")
"
```

## Success criteria for the smoketest

- All 5 claims produce a valid Sarol-9-class verdict JSON (structural success).
- ≥3 of 5 match the gold label (basic capability signal; 100% would be surprising given class imbalance favors ACCURATE).
- Verifier produces PASS on the extractor's evidence for ≥4 of 5 (attestation isn't broken).

If all three pass: proceed to the 50-claim pilot (see the experiment plan, Protocol §2) with the same pipeline. If any fail: debug before scaling.

## What *not* to do

- Do not edit `.claude/specs/verdict_schema.md` or `.claude/prompts/adjudicator-dispatch.md`. The Sarol-variant rubric and dispatch are siblings under `experiments/sarol-2024/`.
- Do not run `/ground-claim` for these claims. It uses the default adjudicator (native rubric) and will produce paper-trail-native labels that our parser won't accept.
- Do not pre-view the gold label before the adjudicator emits a verdict. The adjudicator must never see the gold.
- Do not iterate prompts based on test outcomes. Only train is fair game for iteration.
- Do not commit `staging/` or `predictions/` bulk artifacts — they're gitignored.

## If something goes sideways

- **Staging fails** ("claim id not found"): verify `claims-train.jsonl` is the file you think it is and the claim_id matches a row.
- **Staging fails** ("no evidence annotations on paper bucket"): you may have picked a bucket that isn't in this claim's evidence. Check `row['evidence'].keys()` — buckets are `int(doc_id) // 1000`.
- **Extractor hallucinates evidence**: expected occasionally. The verifier (step 4) should catch. Bounce once.
- **Adjudicator emits paper-trail-native verdicts (CONFIRMED, PARTIALLY_SUPPORTED, etc.)**: you used the wrong dispatch prompt. Use the variant at `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`.
- **Adjudicator refuses all verdicts as ETIQUETTE**: likely the Sarol rubric's multi-cit rule is over-firing. Only one of the 5 smoketest claims is expected to land ETIQUETTE (and all 5 are single-cit, so zero should). Check the adjudicator's nuance field.

## Next step after smoketest succeeds

Stratified pilot on N=50 train claims covering all 9 labels (oversample minorities). See the experiment plan's Protocol §2 and the "Methodological iteration on train" section for the sweep axes.
