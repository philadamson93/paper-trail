# Handoff: run the Sarol 2024 smoketest (N=5)

Paste the block below into a fresh Claude Code session at the paper-trail repo root. Assumes the user has already pulled the `experiment-plan` branch.

Companion docs (the fresh agent reads these as part of step 3–4 below):

- `docs/plans/experiment-sarol-runbook.md` — step-by-step runbook, the canonical source of truth
- `docs/plans/experiment-sarol-benchmark.md` — experiment strategy and success criteria
- `experiments/sarol-2024/specs/verdict_schema_sarol.md` — Sarol 9-class rubric
- `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` — variant dispatch prompt
- `docs/plans/experiment-sarol-leakage-hardening.md` — why the gold and benchmark layouts are what they are

---

## Handoff prompt

I need you to run the Sarol 2024 citation-integrity benchmark smoketest — N=5 stratified training claims end-to-end through paper-trail's extractor → Sarol-variant adjudicator → verifier pipeline. The full runbook is at `docs/plans/experiment-sarol-runbook.md` on branch `experiment-plan`. Read it start-to-finish before doing anything.

**Before you start:**

1. Confirm you're on branch `experiment-plan` and pulled to latest (`git pull --ff-only`).
2. Confirm benchmark data is present: `ls data/benchmarks/sarol-2024/claims-train.jsonl`. If missing, run `bash data/benchmarks/sarol-2024/download.sh`.
3. Read `docs/plans/experiment-sarol-runbook.md` in full — especially the "Leakage hygiene" section. **Every subagent dispatch must have the filesystem-restriction paragraph appended.** Violations invalidate the verdict.
4. Read the context docs so you understand what we're doing and why:
   - `docs/plans/experiment-sarol-benchmark.md` (experiment strategy)
   - `experiments/sarol-2024/specs/verdict_schema_sarol.md` (9-class rubric)
   - `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` (variant dispatch)
   - `docs/plans/experiment-sarol-leakage-hardening.md` (why we're doing what we're doing — do not touch gold files or `data/benchmarks/sarol-2024/` except via the provided scripts)

**Run the smoketest:**

For each of the 5 pre-selected claims in the runbook's table (rows 417, 42, 975, 1395, 850):

1. Stage via `stage_claim.py` (creates staging dir + gold file outside staging).
2. Dispatch extractor via `Agent` tool with `subagent_type: "general-purpose"`, `model: "opus"`, and the extractor-dispatch prompt (slot-filled per the runbook) with the filesystem-restriction paragraph appended.
3. Record usage with `record_usage.py --stage extractor`.
4. Dispatch Sarol-variant adjudicator (use `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`, NOT the default), `model: "opus"`, restriction appended. Validate exit: `rubric_variant == "sarol_2024_9class"` and `overall_verdict` is one of the Sarol 9 classes. If it's a paper-trail native label (CONFIRMED, PARTIALLY_SUPPORTED, etc.), stop and debug.
5. Record usage.
6. Sample one evidence entry, dispatch verifier, `model: "opus"`, restriction appended.
7. Record usage.
8. Parse: `parse_verdict.py --staging <dir> --gold experiments/sarol-2024/gold/train/claim_<ID>_<BUCKET_3DIGIT>.json --out experiments/sarol-2024/predictions/smoketest.jsonl`.

**At the end, report:**

- Per-claim: `pred_label` vs `gold_label`, per-stage token/cost.
- Aggregate: accuracy (hits/5), total cost USD, any verifier bounces, any validation failures.
- Any surprises or anomalies worth flagging before we scale to N=50.

**Budget expectation:** ~$0.40–0.80 per claim (pilot claim 417 came in at $0.66). Total smoketest ~$2–4. If any single claim runs dramatically over $1, flag and pause before continuing.

**Do NOT:**

- Read `data/benchmarks/sarol-2024/claims-*.jsonl` contents or `experiments/sarol-2024/gold/` during orchestration. Only `parse_verdict.py` touches gold, only after adjudication.
- Use `/ground-claim` for these claims (it uses the default adjudicator = wrong rubric).
- Edit anything under `.claude/prompts/` or `.claude/specs/` — the Sarol variants live under `experiments/sarol-2024/`.
- Iterate prompts based on results. This is a validation run; prompt iteration happens in a later phase.

Claim 417 was already validated in the prior session (ACCURATE ↔ gold ACCURATE, $0.66, verifier PASS) — you'll re-run it cleanly. The interesting signal is on the 4 not-ACCURATE claims; if 2+ of them land wrong, flag before scaling.

---

## What "success" looks like for this handoff

- `experiments/sarol-2024/predictions/smoketest.jsonl` has 5 records, each with `pred_label`, `gold_label`, per-stage `usage`, and `cost_usd_total`.
- Aggregate summary printed at end showing hits/5 and total cost.
- All 5 verdicts had `rubric_variant == "sarol_2024_9class"` and only Sarol-9 labels — no paper-trail-native labels leaked through.
- No subagent read gold or benchmark files outside what the provided scripts do.

## What "needs attention before scaling" looks like

- Any claim's prediction validation failed (wrong rubric, non-Sarol label).
- Any verifier `FAIL` that bounced twice (systematic extractor issue).
- Any single claim cost >$1.50 (extractor searching too broadly — prompt issue).
- 2+ of the 4 non-ACCURATE claims wrong (rubric-mapping or prompt problem, not just noise).

In any of those cases, stop and debug before running N=50.
