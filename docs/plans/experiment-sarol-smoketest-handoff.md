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
2. Benchmark and gold live **outside the repo** at `$HOME/.paper-trail/` (by design — leakage hardening). The provided scripts know where to look; you never read those paths directly. If the benchmark is absent, run `bash data/benchmarks/sarol-2024/download.sh` which fetches into the external location.
3. Read `docs/plans/experiment-sarol-runbook.md` in full — especially the "Leakage hygiene" section. Every subagent dispatch must have the filesystem-restriction paragraph appended. Violations invalidate the verdict.
4. Read the context docs so you understand what we're doing and why:
   - `docs/plans/experiment-sarol-benchmark.md` (experiment strategy)
   - `experiments/sarol-2024/specs/verdict_schema_sarol.md` (9-class rubric)
   - `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` (variant dispatch)
   - `docs/plans/experiment-sarol-leakage-hardening.md` (why the gold and benchmark layouts are what they are)
   - `docs/plans/experiment-sarol-hardening-implementation.md` (what structural defenses are in place and what your responsibilities are)

**Run the smoketest — two phases:**

**Phase A (adjudicate):** For each of the 5 pre-selected claims in the runbook's table (internal refs s1–s5):

1. Stage via `stage_claim.py` (creates staging dir + gold file outside repo). Record the opaque `ref_XXXXXX` citekey.
2. Dispatch extractor via `Agent` tool with `subagent_type: "general-purpose"`, `model: "opus"`, and the extractor-dispatch prompt (slot-filled per the runbook) with the filesystem-restriction paragraph appended.
3. Record usage with `record_usage.py --stage extractor`.
4. Dispatch Sarol-variant adjudicator (use `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`, NOT the default), `model: "opus"`, restriction appended. Validate exit: `rubric_variant == "sarol_2024_9class"` and `overall_verdict` is one of the Sarol 9 classes. If it's a paper-trail native label (CONFIRMED, PARTIALLY_SUPPORTED, etc.), stop and debug.
5. Record usage.
6. Sample one evidence entry, dispatch verifier, `model: "opus"`, restriction appended.
7. Record usage.

**Phase B (score — only after all 5 adjudications are complete):**

8. For each staging dir s1..s5: `parse_verdict.py --staging experiments/sarol-2024/staging/smoketest/s<N> --out experiments/sarol-2024/predictions/smoketest.jsonl`. No `--gold` arg — auto-resolves via the opaque citekey.

**During the run** (before scoring), report only:

- Per-claim: `pred_label` (Sarol class), per-stage tokens and cost, verifier result.
- Structural checks: `rubric_variant` is `sarol_2024_9class` on all 5; every verdict is one of the 9 classes.

**After `parse_verdict.py` runs for all 5** (gold is revealed here, not before):

- Per-claim: `pred_label` vs `gold_label`.
- Aggregate: accuracy (hits/5), total cost USD, any verifier bounces, any validation failures.
- Any surprises or anomalies worth flagging before we scale to N=50.

**Budget expectation:** ~$0.40–0.80 per claim (prior pilot run landed at $0.66). Total smoketest ~$2–4. If any single claim runs dramatically over $1, flag and pause before continuing.

**Do NOT:**

- Leave the repo working directory during Phase A. No `cd` out, no absolute paths under `$HOME`, no reads of `~/.paper-trail/`.
- Cat any raw benchmark JSONL (not even "just to see the schema").
- Invoke `parse_verdict.py` during Phase A — it reveals gold. Only invoke it in Phase B after all 5 adjudications complete.
- Record `claim_id`, `paper_bucket`, or `split` in any progress tracker or per-claim task entry. Those are CLI arguments only; keep them in arguments, not trackers.
- Use `/ground-claim` for these claims (it uses the default adjudicator = wrong rubric).
- Edit anything under `.claude/prompts/` or `.claude/specs/` — the Sarol variants live under `experiments/sarol-2024/`.
- Iterate prompts based on results. This is a validation run; prompt iteration happens in a later phase.

One of the five claims was validated in a prior session (pipeline mechanics work end-to-end, cost $0.66, verifier PASS). Treat all five as blinded — do not look up which one was the prior pilot.

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
