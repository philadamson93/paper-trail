Reference: docs/claude_ops.md

# Implementation Feedback: papertrail-optimizer post-mortem fixes

## Verdict
Revise before commit. The main release-file wiring is real, and the VAL scalar now crosses the loop seam, but two money/guard seams still have the prior failure shape: the per-call budget guard does not include canary cost, and fixed TRAIN input can still price one `--train-n` while executing a different batch.

## Plan Coverage
| Item | Status | Evidence: path:line | Notes |
|---|---|---|---|
| Release payload reaches optimizer | Done | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:735`; `/Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:378` | Plan/post-mortem: "VAL scalar is written and visible" (`docs/journal/...:255`). Code passes `loop_ops=LocalLoopOps(...)`, and engine writes `iter/<n>/release_{train,val}.json` only when `loop_ops` is non-null. |
| Missing canary fails closed at real CLI entrypoint | Partial | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:639`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:1418` | Default `--run` refuses a missing pin, but `--no-canary` is an explicit bypass and `run_optimization(components=...)` skips the refusal branch entirely. |
| Canary actually fires before scored claims when wired | Done | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:680`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:683` | Wired `CanarySpec` is processed before `results` starts, and mismatch returns `infra_error`. |
| CostModel canary pricing coupled to wiring | Partial | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:501`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:1495` | Build/preflight derive `canary_enabled` from a loaded/wired canary. Enforcement drift remains in `BudgetGuard`; see Critical Drift. |
| Ramp off-by-one | Done | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/sampling.py:73`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/sampling.py:398`; `/Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:319` | Engine first iter is 1; code rebases `iter_n` to a zero-based rung before lookup. |
| Runner output namespacing | Done | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:600`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:603` | Uses `materialized_path.name`, so current/probe calls stop clobbering the same manifest. Deviation from exact `val/iter<N>/{current,probe}` shape is defensible. |
| Staged batch size equals requested n | Partial | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/sampling.py:303`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/sampling.py:364`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/sampling.py:411` | The new staged VAL and TRAIN factory paths read back through `load_batch`. Static `--train-inputs` still has no equivalent check against `--train-n`. |
| Incremental manifest | Partial | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:699`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:723`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:752` | Timing is fixed: it writes after each claim. Durability is not: direct `write_text` can leave torn JSON, and full reserialization per claim is O(n^2). |
| VAL leakage boundary | Done | `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/dispatcher.py:454`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:1013`; `/Users/philadamson/Documents/Misc/Projects/paper-trail/.claude/worktrees/optimizer-impl/experiments/sarol-2024/optimizer/adapter.py:1027` | Explicit VAL root is refused inside the repo; VAL release reduction strips per-class structure and mistake refs. |
| Metric reachability before next paid run | Missing | `docs/journal/2026-09-03-first-optimization-attempt-postmortem.md:261` | The post-mortem requires stratified TRAIN or a reachable-class metric decision. This diff does not address it. |
| Noise floor / step-back threshold | Missing | `docs/journal/2026-09-03-first-optimization-attempt-postmortem.md:264`; `/Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py:445` | Engine still appends/scans scalar values directly; no consumer-side `tau` or replicate aggregation is added here. |

## Critical Drift
- Budget enforcement still undercounts canaries. Plan/code prose says canary cost is a real term (`docs/plans/papertrail-optimizer-requirements.md:269`) and the post-mortem says estimate and enforcement must describe the same work (`docs/journal/2026-09-03-first-optimization-attempt-postmortem.md:151`). `CostModel.sessions_per_iteration()` includes `canary_sessions()` (`dispatcher.py:149`), but `BudgetGuard.worst_case_to_finish_iteration()` computes only TRAIN plus VAL batch costs (`dispatcher.py:238`) and never adds canary sessions (`dispatcher.py:240`). A run can pass the Runner-side refusal with enough money for scored claims but not the canary it will run first.
- Fixed TRAIN batches retain the priced-vs-executed split. The post-mortem owed a gate that asserts on "the artifact that gets executed" (`docs/journal/...:163`). The staged factory does that, but the static path still passes `RunInputs(input_ref=train_input_ref, batch_id=..., split="train")` directly (`dispatcher.py:701`) while preflight and `BudgetGuard` price `train_n` (`dispatcher.py:669`; `dispatcher.py:517`). A mismatched fixed batch would reproduce the same class of under-quote as `--val-n`.

## Missing Pieces
- No canary pin exists in the diff. `canary.py` is present, but `experiments/sarol-2024/optimizer/canary/canary-retrieval.json` is absent from `find` output; default runs will stop until someone performs the paid pinning step. That is fail-closed, but not yet "canary fire" for the next paid run (`docs/journal/...:258`).
- The canary loader ignores the pin file's own `profile`. It loads by path and returns only `claim` plus `expected_verdict` (`canary.py:104`; `canary.py:108`), so a misfiled `canary-retrieval.json` containing `"profile": "agentic"` would still wire and price as retrieval.
- `canary.py --split dev` is allowed by argparse (`canary.py:302`) despite the module saying a held-out canary would put VAL data in the optimizer's blast radius (`canary.py:86`). Help text is not a guard.
- VAL release omits `retrieval_k`. The plan says a Phase 1 number must carry its evidence condition and "`k`" (`docs/plans/papertrail-optimizer-requirements.md:423`). `run_manifest` and TRAIN release carry it (`adapter.py:734`; `adapter.py:1059`), but `_VAL_BREAKDOWN_ALLOWED` excludes `retrieval_k` (`adapter.py:1013`), so `release_val.json` carries `profile` but not the retrieval budget.

## Contract Violations
- No per-claim VAL outputs are placed inside the optimizer-readable tree by the new runner path: `build_components()` rejects a VAL root inside `store.repo_root` (`dispatcher.py:514`), and the runner appends the call namespace under that explicit root (`adapter.py:601`). This satisfies C6.9's filesystem boundary.
- The VAL release payload keeps the held-out scalar and completeness metadata, not per-class structure: `_reduce_for_val()` filters by `_VAL_BREAKDOWN_ALLOWED` (`adapter.py:1027`), and that allowlist does not include `per_class_f1`, `confusion_matrix`, `error_class_counts`, `support_9way`, or `mistakes_ref` (`adapter.py:1013`). I did not find a new leakage violation there.

## Gate Quality (would each new gate fail if its fix were reverted?)
- Release-file gate: good. `_integration_checks()` drives real `run_loop(..., loop_ops=LocalLoopOps(repo2))` and asserts actual `iter/1/release_val.json` presence (`dispatcher.py:938`; `dispatcher.py:954`; `dispatcher.py:965`). Removing `loop_ops` would fail this.
- Ramp gate: good at the cross-repo seam. It records the real `iter_n` passed by engine (`dispatcher.py:930`) and compares it to `sampling.ENGINE_FIRST_ITER_N` (`dispatcher.py:976`). If the engine base changes, this fails.
- Staged-size gate: good for `val_inputs_for()` and the TRAIN factory because it reads back through `adapter.load_batch()` (`sampling.py:316`). Incomplete for static `--train-inputs`, where the bug class remains reachable.
- Canary absence gate: good for the normal run path. `_integration_checks()` calls `run_optimization()` without a pin and sees `ValueError` (`dispatcher.py:1026`; `dispatcher.py:1039`). It would not catch a caller using prebuilt `components`, because that branch bypasses the refusal (`dispatcher.py:605`).
- Canary pricing gate: decorative with respect to enforcement. The tests assert `CostModel.for_profile(..., canary_enabled=False).canary_sessions() == 0` (`dispatcher.py:1037`; `dispatcher.py:1047`) and `CostModel.for_profile("retrieval").canary_sessions() == 3` (`dispatcher.py:1049`), but no gate checks `BudgetGuard.worst_case_to_finish_iteration()` includes that same canary term. It stays green under the current enforcement bug.
- Canary pin selftest: mostly loader-only. It writes a handcrafted pin and calls `load()` (`canary.py:261`; `canary.py:266`); it would still pass if `pin()` stopped dispatching through `SarolRunner`.
- Manifest incrementality gate: good for timing, incomplete for durability/cost. The spy sees a readable partial manifest mid-batch (`adapter.py:1672`; `adapter.py:1698`), but no gate would fail on non-atomic truncation/rewrite or O(n^2) serialization.
- VAL namespacing gate: good for clobbering. It runs the same VAL batch through two materialized directories and asserts different manifest paths (`adapter.py:1641`; `adapter.py:1646`).
- VAL Tier 2 gate: decent payload-level guard. It serializes the actual release payload and searches for leak keys (`dispatcher.py:1000`), so a top-level-only mistake would be caught.

## Test Gaps
- Add a budget-guard assertion that a canary-enabled model requires more remaining budget than a canary-disabled model for the same split. Today the `CostModel` tests pass while `BudgetGuard` silently omits the canary term (`dispatcher.py:231`).
- Add a static `--train-inputs` negative control: create a 3-claim batch, pass `--train-n 1`, and require refusal before `run_loop`. This should target `dispatcher.py:701`, not the sampler.
- Add a canary pinning test with an injected runner that returns a manifest and prove `pin()` reads its observed verdict (`canary.py:177`; `canary.py:183`). The current canary selftest never exercises the pin path beyond `repeat=0`.
- Add a pin-profile validation test: a pin file whose JSON profile disagrees with the filename should be refused by `load()` or by `run_optimization()` before wiring.
- Add a canary split guard: `--split dev` should be rejected, or the code should explicitly document and gate any non-TRAIN use.
- Add an atomic-write/salvage test for the manifest writer once it writes via temp file plus rename. The current test only checks that JSON is readable when the process is alive between claims.

## Defensible Deviations
- Namespacing by `materialized_path.name` (`adapter.py:600`) instead of exactly `val/iter<N>/{current,probe}/` (`docs/journal/...:200`) is acceptable: the engine already materializes `iter<n>-current` and `iter<n>-<tag>` (`engine/loop.py:328`; `engine/loop.py:404`), so the two VAL manifests are disjoint and attributable.
- `--no-canary` is defensible as an explicit research waiver because it also reprices the run (`dispatcher.py:1499`). It should remain visibly marked as waiving the post-mortem's item 2, not described as an absolute fail-closed guarantee.

## Suggested Code Edits
- Include canary sessions in `BudgetGuard.worst_case_to_finish_iteration()` or delegate the remaining-call arithmetic to `CostModel` so preflight and per-call refusal cannot drift.
- Before constructing static `RunInputs` for TRAIN, read `train_input_ref` with `adapter.load_batch()` and assert `len(...) == train_n`; do the same for static VAL if a future CLI path accepts both `--val-inputs` and a priced VAL size.
- Make manifest writes atomic: serialize once to a temp file in the same directory, `fsync` if desired for paid-run durability, then `replace()` over `run_manifest.json`. Consider writing a compact sidecar index or only recomputing aggregate counts incrementally to avoid O(n^2) full-manifest serialization at high TRAIN rungs.
- Validate canary pin metadata on load: profile in payload must match the requested profile; split must be `train`; optionally assert `program_combined_hash` matches `SarolProgramStore.combined_hash`.
- Add `retrieval_k` to the VAL release's allowed completeness/identity metadata, or explicitly record why `profile` alone is sufficient despite C6.3's "macro-F1 without k is not a result" rule.

## Questions For The Author
- Is `--no-canary` intended to be allowed on paid optimization runs, or only for smoke/infrastructure runs? The code allows it universally (`dispatcher.py:1418`).
- Should `run_optimization(components=...)` be a test-only escape hatch? If yes, name it or assert that production callers cannot use it to bypass canary/root/profile gates (`dispatcher.py:605`).
- Is the committed pin expected in this same change? `.gitignore` says `canary-<profile>.json` is committed (`.gitignore:64`), but no pin file is currently present.

## Audit Trail
- Read, in order: `docs/claude_ops.md`, `docs/journal/2026-09-03-first-optimization-attempt-postmortem.md`, `docs/plans/papertrail-optimizer-requirements.md`, `git diff`, `git diff --staged`, and `experiments/sarol-2024/optimizer/canary.py`.
- Cross-repo engine reads: `/Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/loop.py`, `engine/loop_ops.py`, and `engine/schemas.py`.
- `git diff --staged` was empty.
- Offline checks run: `python3 experiments/sarol-2024/optimizer/sampling.py --selftest` (28/28), `python3 experiments/sarol-2024/optimizer/canary.py --selftest` (7/7), `python3 experiments/sarol-2024/optimizer/dispatcher.py --selftest` (83/83).

---

## Disposition (Claude, same session, after the audit)

**Applied — agreed with Codex, code changed:**
- `BudgetGuard.worst_case_to_finish_iteration` now delegates to a new
  `CostModel.remaining_iteration_cost`, so the preflight and the per-call refusal share one
  arithmetic source and the canary term cannot be omitted by one of them again. *(Critical Drift 1)*
- Static `--train-inputs` is read back through `adapter.load_batch` and refused when its size
  disagrees with the priced `--train-n`, via `_static_train_inputs`. *(Critical Drift 2)*
- `canary.load()` refuses a pin whose payload `profile` disagrees with the profile being loaded,
  or whose `split` is not `train`. The filename is no longer the authority.
- `canary.pin()` refuses a non-train split at the source, and the CLI constrains `--split` to
  `choices=("train",)`. Help text is not a guard.
- `retrieval_k` added to `_VAL_BREAKDOWN_ALLOWED`, so the VAL scalar carries its evidence
  condition per C6.3 (`plan:247`, `plan:423`). It is a run-level scalar, not per-class structure,
  so the Tier 2 surface is unchanged — asserted by a gate that offers `per_class_f1` on the same
  breakdown and confirms it is stripped.
- The run manifest is now written atomically (temp file + `os.replace`), so a kill mid-write
  cannot leave torn JSON for the salvage path that motivated writing it early.

**Gates added for each, and the decorative one replaced.** Codex's sharpest finding was correct:
the canary-pricing gate asserted `CostModel` arithmetic while nothing asserted that `BudgetGuard`
included the same term, so it stayed green under the enforcement bug. It is replaced with
behavioural gates on the guard itself, and those were **negative-controlled**: with the pre-fix
arithmetic restored, 3/3 fail. Also added: static-TRAIN size refusal, a `pin()` run against an
injected fake runner (proving the verdict is read back from a dispatch rather than asserted), pin
metadata refusals, unstable-judge refusal, atomic-write/no-torn-JSON, and the C6.3 pair above.
Suite: **337 offline gates**, from 296 before the post-mortem work.

**Not applied — surfaced to the author instead:**
- `--no-canary` on paid runs. Codex classes it a defensible deviation and it does reprice the run;
  whether it should be reachable outside smoke runs is a research call, not a code fix.
- `run_optimization(components=...)` bypassing the canary refusal. This is the documented
  selftest seam (the same reason the output-root refusal lives at this entrypoint rather than in
  `build_components`). Left as-is pending a decision on whether to name or gate it.
- No pin file committed. Creating one costs real sessions; it is the author's step, and the run
  correctly refuses to start until it exists.
- O(n²) manifest reserialization. Fact accepted and now documented at the call site: at the real
  rungs (10–200 claims) it is microseconds against a claim costing ~$1 and ~100s, so
  salvageability wins. Revisit only if a rung approaches the full 2,141.
- Metric reachability and the noise floor remain open author decisions (post-mortem items 3 and 4)
  and were never in this diff's scope.
