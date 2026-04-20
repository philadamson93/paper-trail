# Implementation: leakage hardening for the Sarol experiment

Status-doc for the defenses landed in response to a concrete leakage incident during the first smoketest attempt (an orchestrator agent read the runbook's "Gold label" column and populated its task tracker with per-claim gold labels before adjudication).

Companion: `docs/plans/experiment-sarol-leakage-hardening.md` (the original analysis and trigger conditions).

## What happened

During an initial smoketest run, the fresh agent's visible task list contained entries like `Run pipeline for claim 417 (C001, ACCURATE)`. The runbook's claim table had a `Gold label` column and the agent dutifully carried the label forward. No subagent prompt was contaminated (the agent hadn't yet dispatched), but the orchestrator itself now had gold it shouldn't have, and its subsequent orchestration choices would not be blind.

Root cause: prose instructions ("do not look at gold") are insufficient when the runbook itself *shows* the gold, and when the benchmark raw data containing gold is sitting in the repo tree next to the scripts. Structural defenses were needed.

## What landed

### 1. Opaque citekeys (`ref_<6hex>`)

`stage_claim.py` now generates deterministic opaque citekeys via `sha256("<split>|<claim_id>|<paper_bucket>")[:6]`, prefixed `ref_`. The old scheme `sarol_train_081` directly encoded split and paper bucket; the new scheme reveals nothing.

- Staging handles: `pdfs/ref_02d728/…`
- `staging_info.json`: `{"citekey": "ref_02d728", "source_mode": …, "multi_cit_context": …}` — no provenance.
- Dispatch prompts reference only the opaque ref.

**Effect:** A subagent receiving a dispatch cannot infer which split or which paper bucket it's working on. Even if it wandered to benchmark data, it has no key to match against claims-*.jsonl row-ids without seeing the claim text.

### 2. Benchmark raw data moved outside the repo

`download.sh` now fetches into `$PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/` (default `$HOME/.paper-trail/benchmarks/sarol-2024/`). The repo's `data/benchmarks/sarol-2024/` contains only `README.md` + `download.sh` — zero benchmark content.

**Effect:** An orchestrator whose working directory is the repo cannot stumble onto claims-*.jsonl via `ls` or path-completion exploration. Access is only via `stage_claim.py`, which reads the env-var-rooted path.

### 3. Gold files moved outside the repo

`stage_claim.py` writes gold to `$PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/<citekey>.json` (default `$HOME/.paper-trail/gold/sarol-2024/…`). Previously at `experiments/sarol-2024/gold/<split>/…` which was gitignored but still in cwd.

**Effect:** Same as (2) — outside cwd exploration by default.

### 4. `parse_verdict.py` auto-resolves gold by opaque citekey

`parse_verdict.py` reads the opaque citekey from `<staging>/staging_info.json`, then globs `$PAPER_TRAIL_GOLD_DIR/sarol-2024/*/<citekey>.json` to find the matching gold file. The orchestrator never has to construct a gold path, and therefore never has gold-path fragments in its session state.

Removed: the `--gold` CLI flag. Adding `--gold` as an explicit argument would mean the orchestrator had to know the path, which meant assembling `<split>` and `<citekey>` into a string — a leakage-adjacent action. Auto-resolution removes that.

### 5. Adjudicate/score phase separation

Runbook now structured as **Phase A (adjudicate) → Phase B (score)**, with an explicit prohibition on invoking `parse_verdict.py` during Phase A. Gold reveals only at the Phase B moment.

### 6. Runbook claim table de-blinded

Previous table had a `Gold label` column. Gone. Table now shows only `internal ref`, `--split`, `--claim-id`, `--cited-paper-id` — the CLI arguments needed for `stage_claim.py`, nothing more.

Also de-blinded: language like "at least one of the four non-ACCURATE-class claims" (which implied exactly one ACCURATE) is gone. Runbook now says only "stratified across major Sarol label classes."

### 7. Stronger orchestrator restriction in prose

Runbook's "Leakage hygiene" section now explicitly prohibits:

- Leaving the repo working directory (`cd` out, absolute `$HOME` paths).
- Reading any file under `~/.paper-trail/`.
- Recording `claim_id`, `paper_bucket`, or `split` in any progress/task tracker in a way that associates them with a claim's eventual label.
- Invoking `parse_verdict.py` during Phase A.

Subagent filesystem-restriction paragraph also updated to mention `~/.paper-trail/` explicitly.

## Before / after leakage surface

| Vector | Before | After |
| --- | --- | --- |
| Runbook lists gold labels | ✗ (had "Gold label" column) | ✓ removed |
| Benchmark in repo tree | ✗ `data/benchmarks/sarol-2024/claims-*.jsonl` present | ✓ only README + script; data at `$HOME/.paper-trail/benchmarks/` |
| Gold in repo tree | ✗ `experiments/sarol-2024/gold/…` present (gitignored but present) | ✓ moved to `$HOME/.paper-trail/gold/` |
| Citekey reveals split + bucket | ✗ `sarol_train_081` | ✓ `ref_02d728` (opaque) |
| Orchestrator constructs gold path | ✗ `--gold <path>` CLI flag used | ✓ auto-resolved by citekey |
| Scoring interleaved with adjudication | ✗ possible per runbook structure | ✓ forbidden; Phase B is after all Phase A |
| Prose restriction scope | ✗ "don't read gold" | ✓ "don't leave repo dir; don't read `$HOME`" |

## What is still on the honor system

Structural defenses reduce leakage risk; they do not eliminate it because the agent has full filesystem access.

- Agent could `find / -name "claims-*.jsonl"` and reach benchmark data at `$HOME/.paper-trail/benchmarks/`.
- Agent could `cat $PAPER_TRAIL_GOLD_DIR/sarol-2024/*/ref_02d728.json` directly.
- Agent could read `stage_claim.py` source, observe the opaque-citekey hash function, and brute-force compute which `ref_XXXXXX` maps to which `(split, claim_id, bucket)` by trying all 2,141 train claims × 100 buckets = 214k hashes (minutes of compute).

These require deliberate effort; the defenses make casual or accidental leakage structurally impossible. Pure sandbox (OS-level, containers) would close these remaining vectors but is out of scope for the smoketest.

## What is deferred

From the original hardening plan (`experiment-sarol-leakage-hardening.md`):

- **#1 (dot-prefix gold dir)** — subsumed by #2 and #3 above. Skipped.
- **#3 (delete gold files, read benchmark directly)** — explored but not adopted; keeping gold as files (outside repo) makes post-hoc audit easier, and the benchmark-outside-repo defense is stronger than the marginal gain of deleting gold.
- **#5 (full slot-based opacity — orchestrator knows only `s1..s5`, not `claim_id`/`bucket`/`split`)** — not implemented. The runbook still shows `--split train --claim-id 417 --cited-paper-id 81` in the claim table because the orchestrator needs to pass those as CLI args. Hiding them fully would require an internal lookup table inside `stage_claim.py`, which the agent could still `cat` to reverse. Diminishing returns for the smoketest.
- **#6 (filesystem sandbox / containers)** — out of scope.

## Trigger revisions

Original plan set trigger conditions for full hardening before the full test-set eval. With the smoketest incident, we implemented most of it immediately. The remaining deferred items should be revisited before:

- Public release of test-set predictions.
- Third-party dataset contributions to this pipeline.
- Any scenario where an adversarial agent model is in the loop.

## Validation

End-to-end test on claim 417 after all changes:

- `stage_claim.py --split train --claim-id 417 --cited-paper-id 81 --source corpus --out …/s1` produces opaque citekey `ref_02d728`.
- Staging dir contents scanned for any Sarol label string → empty (confirmed clean).
- Mock adjudicator output written; `parse_verdict.py --staging …/s1 --out pred.jsonl` auto-resolves gold via `$HOME/.paper-trail/gold/sarol-2024/train/ref_02d728.json`, produces `pred_label=ACCURATE, gold_label=ACCURATE, cost_usd_total=$0.66`.

## Files changed

- `experiments/sarol-2024/scripts/stage_claim.py` — opaque citekeys, env-var-rooted paths.
- `experiments/sarol-2024/scripts/parse_verdict.py` — gold auto-resolution; dropped `--gold` flag.
- `data/benchmarks/sarol-2024/download.sh` — fetches to `$PAPER_TRAIL_BENCHMARKS_DIR` default.
- `data/benchmarks/sarol-2024/README.md` — explains external-data design.
- `.gitignore` — adjusted (old `experiments/*/gold/` entry preserved for safety; main defense is path-location now).
- `docs/plans/experiment-sarol-runbook.md` — Phase A/B split, new path references, stronger orchestrator restrictions, de-blinded claim table.
- `docs/plans/experiment-sarol-smoketest-handoff.md` — updated handoff prompt reflects Phase A/B and no-repo-exit restriction.
- `docs/plans/experiment-sarol-hardening-implementation.md` — this doc.
