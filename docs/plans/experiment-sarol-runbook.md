# Runbook: Sarol 2024 benchmark — Variant A smoketest (N=5)

Exact step-by-step for a fresh agent to run the first Sarol benchmark smoketest. Assumes the agent is running inside Claude Code at the paper-trail repo root, on the `experiment-plan` branch (or a successor branch). Assumes `/paper-trail-init` has already been run for this machine and the paper-trail stack is functional.

Companion docs: `docs/plans/experiment-sarol-benchmark.md` (experiment strategy), `docs/plans/paper-tool-validation.md` (umbrella plan).

## What this runbook does

Run paper-trail's real extractor → Sarol-variant adjudicator → verifier pipeline against 5 stratified training claims from Sarol 2024. Emit predictions in the Sarol 9-class rubric and compare to gold labels. Log per-stage token usage and cost into the ledger. Sanity-check end-to-end plumbing before scaling up.

## Model selection

All subagent calls use **Claude Opus 4.7** (upper-bound cost; most capable). In each Agent tool invocation below, pass `model: "opus"` explicitly. Cheaper ablations (Sonnet 4.6, Haiku 4.5) are a separate sweep axis — not part of the smoketest.

Observed cost from the pilot claim (claim 417, Opus 4.7, no caching): ~$0.66 per claim end-to-end (extractor $0.31 + adjudicator $0.21 + verifier $0.14). Budget accordingly.

## Leakage hygiene — READ BEFORE RUNNING

Every adjudication must happen **without any subagent seeing the gold label first**. Two layers:

1. **Gold files live outside the staging tree.** `stage_claim.py` writes `staging_info.json` (agent-safe: citekey, source_mode, multi_cit_context only) into the staging dir, and writes gold labels to `experiments/sarol-2024/gold/<split>/claim_<row_id>_<bucket>.json`. Subagents are given only the staging path; they must not reach into `experiments/sarol-2024/gold/` or into `data/benchmarks/sarol-2024/` (the raw benchmark, which also contains gold).

2. **Every subagent dispatch must include a sandbox restriction.** When filling the extractor / adjudicator / verifier dispatch prompts, append this paragraph to each prompt before sending (the orchestrator is responsible — subagents will follow it):

    > **Filesystem restriction.** You may read only files at the paths explicitly listed in the *Inputs* section above, plus files under the `source handle` / `evidence file` directories as needed. You must NOT invoke `ls`, `cat`, `rg`, or any other command against the benchmark directory `data/benchmarks/sarol-2024/`, against any `experiments/sarol-2024/gold/` directory, against `experiments/sarol-2024/staging/*/staging_info.json` or sibling manifests, or against any parent-directory / sibling paths of the paths given to you. If you need a file not listed in *Inputs*, stop and report back to the orchestrator instead of reading it.

If a subagent violates this (even curiously), flag the verdict and discard. Note the violation in the error-analysis writeup; do not silently correct.

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

This creates a paper-trail-compatible working directory with `claims_ledger.md`, `refs.bib`, a pre-ingested handle at `pdfs/sarol_train_<PAPER_BUCKET>/`, and a leakage-safe `staging_info.json` (citekey, source_mode, multi_cit_context only — **no gold, no claim_row_id, no raw benchmark pointer**).

Gold labels for this claim are written to `experiments/sarol-2024/gold/train/claim_<CLAIM_ID>_<BUCKET_3DIGIT>.json` (outside the staging tree). Remember this path for step 5.

### 2. Dispatch the **evidence extractor** subagent

Use the real extractor dispatch prompt at `.claude/prompts/extractor-dispatch.md`. Invoke via the `Agent` tool with `model: "opus"` and `subagent_type: "general-purpose"`. Substitute slots as follows:

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

Dispatch the filled prompt as a subagent (same mechanism `/ground-claim` uses). **Append the filesystem-restriction paragraph from the "Leakage hygiene" section to every dispatch.** The extractor writes `<staging_dir>/ledger/evidence/C001.json`.

**Capture usage.** The Agent tool returns a `<usage>` block with `total_tokens`, `tool_uses`, `duration_ms`. Immediately after the call, record:

```bash
python3 experiments/sarol-2024/scripts/record_usage.py \
  --staging <staging_dir> --claim-id C001 --stage extractor \
  --model claude-opus-4-7 \
  --total-tokens <TOKENS> --tool-uses <N> --duration-ms <MS>
```

Appends one line to `<staging_dir>/ledger/usage/C001.jsonl`.

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

The adjudicator reads `<staging_dir>/ledger/evidence/C001.json` + `experiments/sarol-2024/specs/verdict_schema_sarol.md` and writes `<staging_dir>/ledger/claims/C001.json`. Dispatch via `Agent` tool with `model: "opus"`, and **append the filesystem-restriction paragraph** to the dispatch prompt.

**Validate on exit:**

- `rubric_variant == "sarol_2024_9class"` at top level.
- `overall_verdict` is one of the Sarol 9 classes.
- Every `sub_claims[*].verdict` is one of the Sarol 9 classes.

If validation fails: **stop and debug the adjudicator prompt or the Sarol rubric spec**. Do not fall back to the native rubric.

**Capture usage** the same way as step 2, with `--stage adjudicator`.

### 4. Dispatch the **verifier** subagent

Unchanged from paper-trail native. Use `.claude/prompts/verifier-dispatch.md`. Dispatch via `Agent` tool with `model: "opus"`. The verifier just spot-checks the extractor's evidence against `content.txt`; it does not care about the rubric variant.

Sample one evidence entry from the adjudicated claim, fill slots, dispatch with `model: "opus"` and the filesystem-restriction paragraph appended. The verifier writes `<staging_dir>/ledger/verifications/C001__C001.a.json`.

On `verdict_impact == "bounce_to_re_ground"`: re-run steps 2–3 for that claim (one bounce max in the smoketest; if it bounces again, flag and move on).

**Capture usage** the same way as step 2, with `--stage verifier`.

### 5. Parse the verdict into a prediction record

```bash
python3 experiments/sarol-2024/scripts/parse_verdict.py \
  --staging experiments/sarol-2024/staging/smoketest/claim_<CLAIM_ID> \
  --gold experiments/sarol-2024/gold/train/claim_<CLAIM_ID>_<BUCKET_3DIGIT>.json \
  --out experiments/sarol-2024/predictions/smoketest.jsonl
```

The `--gold` path is required and deliberately lives outside staging so the pre-adjudication subagents never had access. If the gold file is missing, re-run `stage_claim.py` to regenerate it.

Appends one JSONL line with `{pred_label, gold_label, pred_3way, gold_3way, usage: {…}, …}` to `predictions/smoketest.jsonl`. The `usage` block folds in per-stage token counts and estimated USD cost (input-token split is inferred at 85/15 when the runtime only gives total tokens).

## After all 5 claims run

Quick sanity-check script (inline) — accuracy + cost:

```bash
python3 -c "
import json
total = 0; hits = 0; cost = 0.0
for line in open('experiments/sarol-2024/predictions/smoketest.jsonl'):
    r = json.loads(line); total += 1
    ok = r['pred_label'] == r['gold_label']
    hits += ok
    c = (r.get('usage') or {}).get('cost_usd_total') or 0.0
    cost += c
    mark = '✓' if ok else '✗'
    print(f\"{mark} claim_id={r['claim_row_id']:>5} gold={r['gold_label']:<18} pred={r['pred_label']:<18} cost=\${c:.3f}\")
print(f'---\\n{hits}/{total} correct; total cost \${cost:.2f}')
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
- **Do not pre-view the gold label before the adjudicator emits a verdict.** Do not `cat` any file under `experiments/sarol-2024/gold/`, `data/benchmarks/sarol-2024/`, or the benchmark raw data as part of orchestration — only `parse_verdict.py` touches gold, and only after adjudication has completed.
- Do not add any slot fill that contains gold label text to a dispatch prompt. If you see `ACCURATE`, `OVERSIMPLIFY`, etc. ending up in a subagent's input, stop and audit.
- Do not iterate prompts based on test outcomes. Only train is fair game for iteration.
- Do not commit `staging/`, `predictions/`, or `gold/` bulk artifacts — they're gitignored.

## If something goes sideways

- **Staging fails** ("claim id not found"): verify `claims-train.jsonl` is the file you think it is and the claim_id matches a row.
- **Staging fails** ("no evidence annotations on paper bucket"): you may have picked a bucket that isn't in this claim's evidence. Check `row['evidence'].keys()` — buckets are `int(doc_id) // 1000`.
- **Extractor hallucinates evidence**: expected occasionally. The verifier (step 4) should catch. Bounce once.
- **Adjudicator emits paper-trail-native verdicts (CONFIRMED, PARTIALLY_SUPPORTED, etc.)**: you used the wrong dispatch prompt. Use the variant at `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`.
- **Adjudicator refuses all verdicts as ETIQUETTE**: likely the Sarol rubric's multi-cit rule is over-firing. Only one of the 5 smoketest claims is expected to land ETIQUETTE (and all 5 are single-cit, so zero should). Check the adjudicator's nuance field.

## Next step after smoketest succeeds

Stratified pilot on N=50 train claims covering all 9 labels (oversample minorities). See the experiment plan's Protocol §2 and the "Methodological iteration on train" section for the sweep axes.
