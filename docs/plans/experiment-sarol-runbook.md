# Runbook: Sarol 2024 benchmark — Variant A smoketest (N=5)

Exact step-by-step for a fresh agent to run the first Sarol benchmark smoketest. Assumes the agent is running inside Claude Code at the paper-trail repo root, on the `experiment-plan` branch (or a successor branch). Assumes `/paper-trail-init` has already been run for this machine and the paper-trail stack is functional.

Companion docs: `docs/plans/experiment-sarol-benchmark.md` (experiment strategy), `docs/plans/paper-tool-validation.md` (umbrella plan).

## What this runbook does

Run paper-trail's real extractor → Sarol-variant adjudicator → verifier pipeline against 5 stratified training claims from Sarol 2024. Emit predictions in the Sarol 9-class rubric and compare to gold labels. Log per-stage token usage and cost into the ledger. Sanity-check end-to-end plumbing before scaling up.

## Model selection

All subagent calls use **Claude Opus 4.7** (upper-bound cost; most capable). In each Agent tool invocation below, pass `model: "opus"` explicitly. Cheaper ablations (Sonnet 4.6, Haiku 4.5) are a separate sweep axis — not part of the smoketest.

Observed cost from the pilot claim (claim 417, Opus 4.7, no caching): ~$0.66 per claim end-to-end (extractor $0.31 + adjudicator $0.21 + verifier $0.14). Budget accordingly.

## Leakage hygiene — READ BEFORE RUNNING

Every adjudication must happen **without any subagent — or the orchestrator — seeing the gold label first**. Structural defenses are now in place; you are responsible for not circumventing them.

**Structural defenses (in place after commit 869003c + this hardening):**

1. **Benchmark raw data lives OUTSIDE the repo** at `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/` (default `$HOME/.paper-trail/benchmarks/sarol-2024/`). The repo's `data/benchmarks/sarol-2024/` contains only `README.md` and `download.sh` — zero benchmark content. A subagent whose working directory is the repo cannot reach the benchmark by cwd-based exploration.
2. **Gold files live OUTSIDE the repo** at `$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/` (default `$HOME/.paper-trail/gold/sarol-2024/<split>/`). Same reasoning.
3. **Citekeys are opaque.** `stage_claim.py` generates `ref_<6hex>` by hashing (split, claim_id, paper_bucket). Staging files reference only the opaque ref. Split and paper bucket are not derivable from the citekey by inspection.
4. **`staging_info.json` contains only `citekey`, `source_mode`, `multi_cit_context`, `source_description`.** No claim_row_id, no split, no raw claim text, no provenance pointer.
5. **Scoring is physically separated from the run.** `parse_verdict.py` looks up gold via `$PAPER_TRAIL_GOLD_DIR` (outside repo) and is only invoked AFTER all claims have been adjudicated. Do not call `parse_verdict.py` inside the per-claim loop.

**Your (orchestrator's) responsibilities:**

- **Stay inside the repo tree.** Your working directory is the paper-trail repo. Do not `cd` out of it, do not use absolute paths under `$HOME` directly, do not `ls` or `cat` against `$PAPER_TRAIL_BENCHMARKS_DIR` or `$PAPER_TRAIL_GOLD_DIR`, do not read any file under `~/.paper-trail/`. The provided scripts (`stage_claim.py`, `parse_verdict.py`, `record_usage.py`) reach out there on your behalf; that is the only sanctioned access.
- **Do not record any `claim_id`, `paper_bucket`, or `split` value in your task tracker in a way that associates it with a Sarol label. The claim_id/bucket/split you pass to `stage_claim.py` are command arguments — keep them in arguments, not in trackers that might get pattern-matched against gold later.**
- **Do not cat the raw benchmark JSONL** even if you know its path.
- **Do not invoke `parse_verdict.py` until all 5 claims are adjudicated** (see Protocol below).

**Subagent sandbox restriction.** Append this paragraph to every extractor / adjudicator / verifier dispatch prompt before sending:

> **Filesystem restriction.** You may read only files at the paths explicitly listed in the *Inputs* section above, plus files under the `source handle` / `evidence file` directories as needed. You must NOT invoke `ls`, `cat`, `rg`, or any other command against `$HOME`, against any `~/.paper-trail/` path, against the repo's `data/benchmarks/` directory, against any `experiments/sarol-2024/staging/*/staging_info.json` or sibling manifests, or against any parent-directory / sibling paths of the paths given to you. If you need a file not listed in *Inputs*, stop and report back to the orchestrator instead of reading it.

If any subagent violates this (even curiously), flag the verdict and discard. Note the violation in the error-analysis writeup; do not silently correct.

## Preconditions

- Running inside Claude Code (the agent IS the orchestrator; `/ground-claim`-style dispatch happens inline).
- Current directory: the paper-trail repo (commands below use relative paths only).
- Benchmark data present at `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/` (default `$HOME/.paper-trail/benchmarks/sarol-2024/`). **You don't read this directly** — the scripts do. If absent, run the download script:

  ```bash
  bash data/benchmarks/sarol-2024/download.sh
  ```

  This fetches into the external location by design. You don't need to verify the resulting files personally; a successful exit is sufficient.

- Python 3 available (stdlib only — no third-party deps needed for staging or parsing).

## The 5 claims

Pre-selected, stratified across major Sarol label classes, all single-cit. **Gold labels are blinded** — you (the orchestrator) must not see them until `parse_verdict.py` surfaces them at the end-of-run scoring phase.

| Internal ref | --split | --claim-id | --cited-paper-id |
| --- | --- | ---: | ---: |
| s1 | train | 417 | 81 |
| s2 | train | 42 | 52 |
| s3 | train | 975 | 93 |
| s4 | train | 1395 | 43 |
| s5 | train | 850 | 45 |

These are exactly the arguments to pass to `stage_claim.py`. The benchmark JSONL that houses these row-ids lives **outside the repo** at `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/claims-train.jsonl`; you never read it directly (and you shouldn't — doing so is a leakage path, since the claim text is the lookup key for gold). After staging, each claim's citekey is an opaque 6-hex hash (`ref_XXXXXX`) — the citekey is all you use in subagent dispatches.

The five jointly stratify across Sarol label classes. Their individual labels are not disclosed anywhere in this runbook, in staging files, or in any agent-reachable location inside the repo. They surface only when `parse_verdict.py` runs against the external gold store at the end.

## Protocol

The run is two phases. **Phase A: adjudicate all 5 claims blind. Phase B: score once, all at once.** Do not interleave.

## Phase A — Adjudicate (per claim — repeat 5 times, once for each of s1–s5)

### 1. Stage the inputs

For each claim, run (example for s1):

```bash
python3 experiments/sarol-2024/scripts/stage_claim.py \
  --split train \
  --claim-id 417 \
  --cited-paper-id 81 \
  --source corpus \
  --out experiments/sarol-2024/staging/smoketest/s1
```

The script reads the benchmark from outside the repo, writes staging inside, and writes gold to the external gold store — all in one invocation. Output includes the opaque `citekey` (e.g., `ref_02d728`). **Record this citekey internally; you'll use it as the dispatch slot value. Do NOT record the `--claim-id`, `--cited-paper-id`, or `--split` values alongside per-claim outputs or progress markers.**

Staging contents (what you will see):

- `claims_ledger.md`, `refs.bib`
- `pdfs/<citekey>/content.txt`, `meta.json`, `ingest_report.json`
- `staging_info.json` — opaque citekey + source_mode + multi_cit_context + source_description. That's it.

### 2. Dispatch the **evidence extractor** subagent

Use the real extractor dispatch prompt at `.claude/prompts/extractor-dispatch.md`. Invoke via the `Agent` tool with `model: "opus"` and `subagent_type: "general-purpose"`. Substitute slots as follows:

| Slot | Value |
| --- | --- |
| `{{claim_id}}` | `C001` for s1, `C002` for s2, etc. |
| `{{run_id}}` | `run_sarol_smoketest_<TIMESTAMP>` |
| `{{citekey}}` | opaque ref from staging (e.g., `ref_02d728`) |
| `{{claim_text}}` | read from `<staging_dir>/pdfs/<citekey>/meta.json` or infer — actually, the claim text is NOT in staging_info.json for leakage reasons; read it from the claim argument your orchestrator was given. Specifically: the `--claim-id` value let `stage_claim.py` populate the handle, but you need the normalized claim text too. See "How to get the claim text" note below. |
| `{{manuscript_section}}` | `Sarol benchmark (synthetic)` |
| `{{claim_type_hint.type}}` | `PARAPHRASED` |
| `{{claim_type_hint.confidence}}` | `medium` |
| `{{handle}}` | `<staging_dir>/pdfs/<citekey>/` |
| `{{ingest_mode}}` | `pdftotext_fallback` |
| `{{co_citekeys}}` | `[]` (single-cit) |
| `{{run_output_dir}}` | `<staging_dir>` |

**How to get the claim text:** `stage_claim.py` prints a `staging_info` object to stdout on completion; that block does NOT include the claim text (by design). The claim text is available in the external gold file (`$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/<citekey>.json`) but **you should not read that file during Phase A** — it contains gold. Instead, have `stage_claim.py` optionally print the normalized claim text to a sidecar file when needed. TODO: add a `--emit-claim-text <path>` flag so the orchestrator can get just the text without seeing gold. In the interim, use `python3 -c "import json; print(json.loads(open('<staging_dir>/pdfs/<citekey>/meta.json').read())['title'])"` plus any text you saved at stage time — OR pass the claim text through an internal variable your orchestrator session constructed from the `row['claim']` it got when it invoked stage_claim.py. (Yes, this is awkward. The hardening plan acknowledges it as known friction.)

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

## Phase B — Score (after all 5 claims are adjudicated)

**Only after steps 1–4 have completed for all five claims s1–s5.** Do not run Phase B mid-loop. Phase B is the moment gold is revealed.

For each staging dir in sequence:

```bash
python3 experiments/sarol-2024/scripts/parse_verdict.py \
  --staging experiments/sarol-2024/staging/smoketest/s<N> \
  --out experiments/sarol-2024/predictions/smoketest.jsonl
```

`parse_verdict.py` auto-resolves gold from `$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/<citekey>.json` via the opaque citekey it reads from `staging_info.json`. No `--gold` path to construct; no benchmark access. Gold reveals only at this moment.

Appends one JSONL line per claim with `{pred_label, gold_label, pred_3way, gold_3way, usage: {…}, …}` to `predictions/smoketest.jsonl`. The `usage` block folds in per-stage token counts and estimated USD cost (input-token split is inferred at 85/15 when the runtime only gives total tokens).

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

Structural (check during Phase A, no gold exposure needed):

- All 5 claims produce a valid Sarol-9-class verdict JSON (`rubric_variant == "sarol_2024_9class"`, `overall_verdict` is one of the 9 classes).
- Verifier produces PASS (or a documented PARTIAL) on every spot-check; no unresolved bounces after one retry.
- Per-claim cost within budget (~$0.40–0.80; flag any claim >$1.50).
- No subagent exited with any indication it read files outside its handle (check each subagent's final message).

Accuracy (revealed only in Phase B):

- ≥3 of 5 match gold (basic capability signal).
- Error-class discrimination is visible (not all predictions collapse to one class).

If structural criteria pass and accuracy is reasonable: proceed to the 50-claim pilot (see the experiment plan, Protocol §2) with the same pipeline. If any structural criterion fails: debug before scaling. If structural passes but accuracy is <3/5: escalate rubric/prompt issue before running more claims.

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
