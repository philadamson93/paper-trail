Reference: docs/claude_ops.md

<!-- Codex CLI 0.132.0, read-only sandbox, post-hoc audit of 2b8ef7f..HEAD. Report reproduced verbatim; Codex could not write this file itself (read-only), so Claude saved its stdout. -->

# Implementation Feedback: Optimizer throughput — concurrent dispatch

## Verdict
A follow-up commit is warranted. The main concurrency implementation preserves ordering, totals, and flag plumbing, but unexpected worker exceptions now allow already-queued claims to keep running before `run()` re-raises, which is a paid-run semantic drift from the old fail-fast loop.

## Plan Coverage

Section | Status | Evidence: path:line | Notes
--- | --- | --- | ---
Lever 1: `SarolRunner(max_workers=N)`, default 1 | Done | `experiments/sarol-2024/optimizer/adapter.py:630`, `experiments/sarol-2024/optimizer/adapter.py:665` | Constructor defaults to 1 and clamps to at least 1.
Lever 1: bounded thread pool | Done | `experiments/sarol-2024/optimizer/adapter.py:1038` | Uses `ThreadPoolExecutor(max_workers=self.max_workers)`.
Lever 1: delete shared counter and derive totals | Done | `experiments/sarol-2024/optimizer/adapter.py:584`, `experiments/sarol-2024/optimizer/adapter.py:600` | `batch_totals()` sums stage records; old counter removed from dispatch.
Lever 1: canary included in totals | Done | `experiments/sarol-2024/optimizer/adapter.py:901`, `experiments/sarol-2024/optimizer/adapter.py:925`, `experiments/sarol-2024/optimizer/adapter.py:1052` | Canary early-return, manifest writes, and final `RunArtifacts` all include `[canary_record]`.
Lever 1: manifest write inside worker | Done | `experiments/sarol-2024/optimizer/adapter.py:1032`, `experiments/sarol-2024/optimizer/adapter.py:1035` | Restores `dispatch, write, dispatch, write` when `max_workers=1`.
Lever 1: collect by submission index | Done | `experiments/sarol-2024/optimizer/adapter.py:1013`, `experiments/sarol-2024/optimizer/adapter.py:1034`, `experiments/sarol-2024/optimizer/adapter.py:1047` | Uses integer submission index, not `claim_id` or arrival order.
Lever 1: `--max-workers` wiring | Done | `experiments/sarol-2024/optimizer/dispatcher.py:519`, `experiments/sarol-2024/optimizer/dispatcher.py:564`, `experiments/sarol-2024/optimizer/dispatcher.py:1926`, `experiments/sarol-2024/optimizer/dispatcher.py:2057` | CLI default and component default are both 1; flag reaches `SarolRunner`.
Lever 2: analysis only | Done | `docs/plans/optimizer-throughput-concurrent-dispatch.md:93` | No batching/inlined judge implementation appears in touched runtime files.

## Critical Drift
- Severity: Major | plan says unexpected exceptions should preserve old propagation semantics; code propagates, but only after the executor drains already-submitted work | Evidence: `experiments/sarol-2024/optimizer/adapter.py:1038`, `experiments/sarol-2024/optimizer/adapter.py:1044` | Required fix: use `wait(..., return_when=FIRST_EXCEPTION)` or equivalent, cancel pending futures, and exit the executor with `shutdown(cancel_futures=True)` on first unexpected exception. In-flight subprocesses cannot be unsent cheaply, but queued claims should not start after a worker has already failed.

## Concurrency Correctness
- `ledger_lock` covers the shared `indexed` dict and every partial manifest rewrite, and is not held during evidence production, `_stage_command`, `self.invoke`, trace copy, or validation. Evidence: `experiments/sarol-2024/optimizer/adapter.py:1013`, `experiments/sarol-2024/optimizer/adapter.py:1016`, `experiments/sarol-2024/optimizer/adapter.py:1032`, `experiments/sarol-2024/optimizer/adapter.py:1033`.

- The actual dispatch work remains outside the lock: evidence producer at `experiments/sarol-2024/optimizer/adapter.py:818`, command construction at `experiments/sarol-2024/optimizer/adapter.py:833`, nested invocation at `experiments/sarol-2024/optimizer/adapter.py:834`, trace lookup/copy at `experiments/sarol-2024/optimizer/adapter.py:842`, and validation at `experiments/sarol-2024/optimizer/adapter.py:874`. The pool is not silently serialized.

- `write_manifest` itself is safe under the new call discipline: the shared temp path is only used while `ledger_lock` is held for partial writes, and the final write happens after all futures have completed. Evidence: `experiments/sarol-2024/optimizer/adapter.py:987`, `experiments/sarol-2024/optimizer/adapter.py:1033`, `experiments/sarol-2024/optimizer/adapter.py:1048`.

- `out_dir.mkdir` runs before any worker is submitted, so directory creation is not a race. Evidence: `experiments/sarol-2024/optimizer/adapter.py:799`, `experiments/sarol-2024/optimizer/adapter.py:1038`.

- `validate_sarol` use is thread-safe in this path: `rollup_order` is computed once before dispatch, and `validate_file`/`validate_obj` use local `violations` and `counts`. Evidence: `experiments/sarol-2024/optimizer/adapter.py:804`, `experiments/sarol-2024/optimizer/adapter.py:874`, `experiments/sarol-2024/optimizer/validate_sarol.py:246`.

- Remaining edge: duplicate `claim_id` records do not collapse in the manifest, but duplicate IDs still collide on claim-keyed side effects: evidence file, verdict file, and trace copy. Evidence: record collection by index at `experiments/sarol-2024/optimizer/adapter.py:1034`; evidence path at `experiments/sarol-2024/optimizer/evidence_producers.py:235`; verdict path at `experiments/sarol-2024/optimizer/adapter.py:873`; trace path at `experiments/sarol-2024/optimizer/adapter.py:844`. If duplicate IDs are possible outside a synthetic gate, this is a real concurrent write hazard.

## Contract Violations
- None found for totals. Timeout and non-zero exits still create exactly one stage entry per returned `invoke`, so `batch_totals()` counts them exactly once. Evidence: `experiments/sarol-2024/optimizer/adapter.py:834`, `experiments/sarol-2024/optimizer/adapter.py:851`, `experiments/sarol-2024/optimizer/adapter.py:864`, `experiments/sarol-2024/optimizer/adapter.py:867`.

- None found for the evidence-producer failure path. It returns before any stage entry exists, so `sub_invocation_count=0` for that claim matches “no invoke happened.” Evidence: `experiments/sarol-2024/optimizer/adapter.py:818`, `experiments/sarol-2024/optimizer/adapter.py:827`, `experiments/sarol-2024/optimizer/adapter.py:830`.

- Manifest ordering contract is preserved for successful records: each partial and final manifest serializes `indexed` sorted by submission index. Evidence: `experiments/sarol-2024/optimizer/adapter.py:1035`, `experiments/sarol-2024/optimizer/adapter.py:1047`.

## Test Gaps
- Missing gate for first-exception behavior. The implementation asserts normal concurrency, ordering, totals, and duplicate-record preservation, but no gate makes a worker raise unexpectedly and verifies that pending claims are not started after the first failure. Evidence: concurrency gates at `experiments/sarol-2024/optimizer/adapter.py:2533`; exception handling comment without behavioral gate at `experiments/sarol-2024/optimizer/adapter.py:1042`.

- Timing gate is stronger than the documented flaky `par < ser` version, but still wall-clock based and can fail on a heavily loaded machine. Evidence: `experiments/sarol-2024/optimizer/adapter.py:2540`, `experiments/sarol-2024/optimizer/adapter.py:2546`. It is acceptable as a smoke gate, but the non-timing `par_peak > 1` and `par_peak <= 4` gates carry the important correctness contract.

- Duplicate-ID gate proves two manifest records survive, but not that duplicate IDs avoid side-effect collisions. Evidence: gate only checks `len(dup_man["claims"]) == 2` and `requested_count == 2` at `experiments/sarol-2024/optimizer/adapter.py:2609`; side-effect paths remain claim-id keyed at `experiments/sarol-2024/optimizer/evidence_producers.py:235` and `experiments/sarol-2024/optimizer/adapter.py:844`.

- CLI `globals()` mutation is restored in a `finally`, so it is leak-resistant for ordinary exceptions. Evidence: mutation at `experiments/sarol-2024/optimizer/dispatcher.py:1233`, restore at `experiments/sarol-2024/optimizer/dispatcher.py:1249`. The gate would fail if `main()` stopped calling `run_optimization` or dropped `max_workers`, because `_cli_max_workers` would remain `None` at `experiments/sarol-2024/optimizer/dispatcher.py:1251` and is checked at `experiments/sarol-2024/optimizer/dispatcher.py:1391`.

## Defensible Deviations
- The code comment says “`as_completed` rather than `map`,” but the code does not call `as_completed`; it iterates futures in submission order. This is defensible because the manifest write moved into the worker, so completion-time manifest landing does not depend on main-thread collection order. Evidence: comment at `experiments/sarol-2024/optimizer/adapter.py:1009`; actual loop at `experiments/sarol-2024/optimizer/adapter.py:1044`.

- The final result list is constructed from `indexed` after the pool completes rather than from `future.result()` return values. That is intentional and preserves submission ordering. Evidence: `experiments/sarol-2024/optimizer/adapter.py:1047`.

## Suggested Code Edits
- `experiments/sarol-2024/optimizer/adapter.py:1038`: replace the plain context-manager drain with first-exception handling. On first future exception, cancel futures that have not started and re-raise after shutdown with `cancel_futures=True`. Keep completed workers’ in-worker manifest writes intact.

- `experiments/sarol-2024/optimizer/adapter.py:2476`: add a self-test where one worker raises an unexpected exception, one earlier worker completes, and several later claims are queued. Assert the exception propagates, already completed records remain in the manifest, and queued claims do not dispatch.

- `experiments/sarol-2024/optimizer/adapter.py:2583`: either state duplicate claim IDs are only a manifest-record regression test, or add a stronger invariant that batches must have unique `claim_id` before concurrent dispatch starts.

## Questions For The Author
- Are duplicate `claim_id` values valid input, or only a negative-control shape for the result collector? The answer decides whether the claim-keyed evidence/verdict/trace path collision needs a runtime guard.

- Should unexpected worker exceptions fail fast for queued claims to contain paid spend, or is “wait for all already submitted work, then re-raise” an accepted regression? The plan only names budget-refusal overshoot, not exception overshoot.

## Audit Trail
- Files inspected:
- docs/claude_ops.md
- docs/plans/optimizer-throughput-concurrent-dispatch.md
- experiments/sarol-2024/optimizer/adapter.py
- experiments/sarol-2024/optimizer/dispatcher.py
- experiments/sarol-2024/optimizer/evidence_producers.py
- experiments/sarol-2024/optimizer/validate_sarol.py
- Git range inspected: `2b8ef7f..HEAD`
- Commits inspected: `64a57ea`, `314164a`
