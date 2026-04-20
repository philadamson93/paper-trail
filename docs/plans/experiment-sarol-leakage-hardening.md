# Plan: leakage hardening for the Sarol experiment

Deferred hardening work for the gold-label leakage surface. The current state (after commit `a9a7852`) is adequate for the N=5 smoketest and early pilots; this plan lays out the tighter design to adopt before the full train + test eval, where publication credibility (reviewers asking "how did you prevent test-set contamination?") depends on a defensible story.

Scope: the Sarol 2024 benchmark experiment only. Generalizes naturally to other supervised-label benchmarks we add later.

## Current state (a9a7852)

Two defenses in place:

- `stage_claim.py` splits its output: `staging/<claim>/staging_info.json` contains only agent-safe metadata (citekey, source_mode, multi_cit_context, source_description); gold labels + provenance land in `experiments/sarol-2024/gold/<split>/claim_<N>_<B>.json`, outside the staging tree, gitignored.
- The runbook's "Leakage hygiene" section instructs the orchestrator to append a filesystem-restriction paragraph to every subagent dispatch ("do not read files outside your handle").

Scoring is a pure Python script (`parse_verdict.py --gold <path>`) — no LLM in the loop at scoring time.

## Residual leakage vectors (ranked by risk)

1. **Benchmark raw data at `data/benchmarks/sarol-2024/claims-<split>.jsonl`.** Contains every gold label. A subagent with the claim text (which the extractor legitimately holds) could `rg "<exact claim text>" data/benchmarks/…` and recover the label directly. **Highest residual risk.** Does not require `claim_row_id`; the text itself is the lookup key.
2. **Citekey encodes `split` + `paper_bucket`.** `sarol_train_081` tells a curious subagent where to look in the benchmark; makes #1 faster but does not enable it (the exact-text grep already works).
3. **`experiments/sarol-2024/gold/<split>/*.json`** — exists on disk in the repo tree. Less discoverable than #1 since it's a dedicated directory the dispatch prompts never reference, but still in cwd's neighborhood.

All three depend on a subagent actively ignoring its prompt restriction. None is an adversarial-threat scenario; the concern is accidental exploration.

## Options

| # | Option | Effort | Impact on residual risk |
| - | --- | --- | --- |
| 1 | Dot-prefix gold dir → `experiments/sarol-2024/.gold/` | 1 line | Hides from default `ls`/`cat *` — small |
| 2 | Move gold outside the repo (`$HOME/.paper-trail/gold/<benchmark>/…` via env var) | ~20 lines | Strong — agent's cwd-based exploration misses it |
| 3 | Delete gold files entirely; `parse_verdict.py` reads benchmark raw data with explicit CLI args | ~30 lines | Removes one vector but benchmark still on disk |
| 4 | Move benchmark raw data outside the repo too; dispatch prompts reference only staging | ~40 lines | Addresses #1 — the real residual risk |
| 5 | Opaque citekey (`ref_<6-hex>` instead of `sarol_train_081`) | ~15 lines | Addresses #2 |
| 6 | Filesystem sandbox / chroot / container per subagent | High | Strongest; likely overkill for this threat model |

## Recommended path for full eval

**Before the full train + test run, implement #4 + #5.** Together they:

- Remove the benchmark raw data from the repo tree by default. `data/benchmarks/sarol-2024/download.sh` fetches into `$PAPER_TRAIL_BENCHMARKS_DIR` (default `$HOME/.paper-trail/benchmarks/sarol-2024/`). A `PAPER_TRAIL_BENCHMARKS_DIR` env var lets users override for dev. Repo-tree `data/benchmarks/sarol-2024/` becomes a symlink or a README-only stub.
- Replace `sarol_<split>_<bucket>` citekeys with opaque `ref_<6-hex>` identifiers. stage_claim.py keeps a mapping `experiments/sarol-2024/.ref_map/<run>/<ref_id>.json` (outside staging, outside the agent's visibility) that translates back for scoring.
- Keep the dispatch-prompt filesystem restriction as the third layer.

**Keep the "scoring is pure Python" property.** `parse_verdict.py` continues to be the only piece that touches gold, and it runs locally after the orchestrator has finished. Call this out in the paper's methods section as a named contamination defense, not just an incidental implementation detail.

## What to defer

- **#1 (dot-prefix)** — cosmetic; subsumed by #2 when we move outside the repo. Skip.
- **#3 (delete gold files, read benchmark directly)** — sounds cleaner but the benchmark is still on disk, so residual risk is identical to keeping gold files. Skip.
- **#6 (sandbox)** — only worth it if we discover a concrete scenario where the prompt restriction is insufficient. Revisit if we see any evidence of subagent-initiated exploration outside the handle.

## Why this is adequate for the smoketest

- Scoring is pure Python; no agent sees gold during the run.
- Dispatch-prompt restriction + gold-outside-staging gives two layers.
- Smoketest results don't carry publication weight; their purpose is pipeline validation.

Hardening after smoketest preserves the credibility of the primary test-set evaluation, which is what matters for the paper.

## Trigger conditions

Implement #4 + #5 before any of the following:

- Running the full test set (Variant A or C) for a reported number.
- Releasing predictions publicly alongside the paper.
- Accepting a dataset contribution from a third party that uses the same directory structure.

Smoketest + N=50 pilot + methodological sweeps on train can all run under the current hardening.

## Sources

- Current gold-split fix: commit `a9a7852` on branch `experiment-plan`.
- Runbook "Leakage hygiene" section: `docs/plans/experiment-sarol-runbook.md`.
- Experiment plan: `docs/plans/experiment-sarol-benchmark.md`.
