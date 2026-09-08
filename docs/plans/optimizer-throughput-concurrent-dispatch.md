Reference: docs/claude_ops.md

# Optimizer throughput: concurrent dispatch, and whether the judge needs an agent

**Status: Lever 1 IMPLEMENTED + gated (2026-09-07). Lever 2 question ANSWERED, not implemented.**

Branch: `feat/optimizer-concurrent-dispatch`, cut from `sarol-optimizer-impl` @ `2b8ef7f`.

Written while the `hillclimb-2026-09-07` run was live in the `optimizer-impl` worktree. That tree
was never touched: this work was done in a separate worktree, and every check below is offline
(fake invokers, `sh` subprocesses) so nothing contended with the run for API capacity.

Context: `docs/plans/NEXT.md` § "Session 2026-09-07d", which measured ~2 min/claim and ranked three
speed-up levers by **how much they perturb the instrument**. This doc executes lever 1 and answers
the cheap question gating lever 2.

---

## Lever 1 — concurrency over independent claims (DONE)

### What changed

`SarolRunner.run`'s `for claim in claims: results.append(process(claim))` is now a bounded
`ThreadPoolExecutor`. Threads, not processes: `process` spends ~all its time blocked in
`communicate()` waiting on a `claude` subprocess, so the GIL is released throughout.

- **`SarolRunner(max_workers=N)`**, default **1** — byte-identical to the old serial dispatch.
- **`--max-workers N`** on `dispatcher.py`, wired through `build_components`.
- **The shared `counter` dict is deleted, not locked.** New module-level `batch_totals(records)`
  sums `sub_invocation_count` and `cost_usd` from the per-stage records, which already carry both.
  Fixing the default rather than guarding the call site.
- **The manifest write moved into the worker**, under a lock that also guards the results dict.

### Three things that were not obvious going in

1. **The canary must stay in the totals.** The deleted `counter` was incremented by the canary's
   own dispatch before the batch. A naive "sum over `results`" silently under-reports every run by
   one claim's cost and one sub-invocation. Both call sites now sum `[canary_record] + results`.
   Gated.

2. **Where the manifest is written is load-bearing, and the existing gates caught it.** The first
   draft collected finished futures on the main thread. That lets a worker pick up its next claim
   the instant the previous one returns — *before* the manifest naming the finished one is written.
   At `max_workers=1` that quietly weakens the incremental-manifest guarantee the salvage path
   depends on, and two pre-existing gates (`a manifest exists BEFORE the batch finishes`,
   `...covering the claims finished so far, and growing`) went red on it. Writing inside the worker
   restores exact serial ordering at N=1 and still lands each claim as it finishes at N>1.

3. **Results are collected by submission index, not by `claim_id`.** Keying on `claim_id` would let
   a duplicated id in one batch collapse two records into one — which would then pass the Scorer's
   coverage check at half the batch. Gated with a deliberately duplicated batch.

### Why the default is 1

Raising `max_workers` cannot move the instrument — every session, prompt, subagent and materialized
tree is byte-identical, which is why serially-measured baselines stay comparable. But the useful
**ceiling is empirical**: each claim is a nested session that itself spawns a subagent, so N workers
is ~2N concurrent API consumers plus N node processes. That ceiling could not be measured here
without contending with the live run for the very capacity being measured. So the flag ships at 1,
and the ramp belongs to the first session that can watch it.

Expected at N=4-8: ~20h → ~3-5h for a 5-iteration TRAIN=50/VAL=50 run.

**Accepted regression:** on a budget refusal the overshoot becomes the N claims in flight, not 1.

### Codex review (post-hoc) found one real bug — fixed

`/review-implementation` was run **after** the first commit was already pushed, which is out of
order per `docs/claude_ops.md` (implementation → review → commit). Codex's verdict was *"a follow-up
commit is warranted"*, and it was right:

**The first implementation drained the batch on failure instead of failing fast.** All claims are
submitted to the pool up front, so an unexpected exception in one worker propagated only *after*
`ThreadPoolExecutor.__exit__`'s `shutdown(wait=True)` had run every remaining submitted claim. The
serial `for claim in claims:` loop stopped at the failing claim. On a 300-claim paid batch that is
297 claims of spend after the failure — and the code comment asserting the old behaviour was
preserved made it look deliberate. Propagation was preserved; **fail-fast was not**, and fail-fast
was the part that cost money.

Fixed by consuming futures via `as_completed` (so the first failure is noticed in *time*, not in
submission order) and cancelling every still-queued future before re-raising. Cancelling is a no-op
for a claim already running — a dispatched nested session cannot be unsent — so the in-flight
overshoot matches the budget-refusal case above. Gated, and negative-controlled by reverting to the
exact committed code that shipped the bug (`143/144`, the new gate red).

Codex also caught a **stale comment** claiming `as_completed` was used for manifest ordering, left
over from an earlier draft; salvageability actually comes from the in-worker manifest write. Fixed.

Two Codex findings were judged not to need changes: the wall-clock gate is timing-based but backed
by the non-timing `par_peak` gates that carry the real contract, and the `globals()` stub in the CLI
gate is restored in a `finally` and fails closed (`_cli_max_workers` stays `None`).

### Verification

`python3 adapter.py --selftest` → **141/141**. `python3 dispatcher.py --selftest` → **114/114**.
17 new gates. Each was negative-controlled — the mutation was applied, the red observed, the tree
restored:

| # | Mutation | Gate(s) that went red |
|---|---|---|
| NC1 | pool forced to 1 worker | concurrency gate; wall-clock gate |
| NC2 | pool unbounded (64) | `max_workers` bound; default-is-serial; **both** incremental-manifest gates |
| NC3 | collect keyed on `claim_id` | duplicate-id gate |
| NC4 | manifest in reverse order | exactly-once/input-order gate |
| NC5 | totals stop summing per-stage cost | cost total; `batch_totals` contract |
| NC6 | manifest ordered by arrival | exactly-once; input-order determinism |
| NC7 | drop `max_workers` before the Runner | `--max-workers` reaches the Runner |
| NC8 | drop `args.max_workers` at the CLI | `--max-workers` reaches the RUN |

NC1 also caught a **flaky gate of my own**: `par_elapsed < ser_elapsed` passed on a coin flip once
both paths were serial. It is now a margin (`< ser * 0.75`) — the batch is 1.80s serial vs ~0.55s
over four workers, so a real speed-up clears it and a forced-serial control does not.

NC7/NC8 exist because this is the **third** time this flag-plumbing hazard has come up: `--profile`
shipped parsed-priced-and-dropped, `--model` was gated against a repeat. A `--max-workers` that
silently stayed at 1 would look exactly like "the pool didn't help" and be debugged as a rate limit.

---

## Lever 2 — does the adjudicator subagent do anything a single model call could not?

**No.** Read `.claude/commands/sarol-eval-item.md` and the frozen
`prompts/adjudicator-dispatch-sarol.md` end to end. Under the `retrieval` profile the judge's
entire tool surface is:

- **3 reads at paths fully known before dispatch** — the evidence envelope
  (`{{run_output_dir}}/ledger/evidence/{{claim_id}}.json`), the enum contract, and the rubric. The
  prompt says *"Read the evidence file, the enum contract, and the Sarol rubric. **Nothing else.**"*
- **1 write to a path known before dispatch** — `{{run_output_dir}}/ledger/claims/{{claim_id}}.json`,
  with *"Do not write outside the verdict JSON path."*

Every agentic affordance is explicitly forbidden: *"You do not re-read the source paper. You do not
run new searches. You do not invoke vision."* There is no branching on content, no discovery, no
conditional reads. Two of the three inputs (enum, rubric) live in the frozen materialized tree and
are **identical for every claim in an iteration**. The third is per-claim and, under `retrieval`, is
produced mechanically by BM25 *before* dispatch.

So the model's job really is text-in → verdict-JSON-out, and the harness can inline all three inputs
and write the response itself. **Batch-eligible, and per-claim isolation is preserved** since each
claim stays its own request.

### Two caveats before anyone treats that as a green light

1. **It still changes the program.** The dispatch path changes, so `program-v0`'s identity claim
   changes even if verdicts are distributionally identical. Baselines were measured through the
   nested path. Agreement has to be *measured* over the same k claims, not assumed.

2. **A subagent's context is not a bare prompt.** A Claude Code general-purpose subagent carries a
   system prompt and tool definitions the API call would not. That is a real difference in model
   input and is exactly what the agreement test has to cover.

### One ambiguity in the frozen prompt, worth knowing about

Step 1 says read three files and *"Nothing else"*, but the Output contract directs conformance to a
**fourth** file, `{{spec_root}}/src/specs/verdict_schema.md` (14KB). It *is* in the frozen manifest
(a contract file), so this is not an unfrozen input — but whether it lands in the judge's context is
left to the session. Anyone inlining inputs for lever 2 has to decide that question explicitly, and
that decision is itself a program change.

---

## Instrument fidelity: what the live run's own traces show

The 77 adjudicator traces from `hillclimb-2026-09-07` were read directly (read-only). Trace
attribution is sound — the trace `sessionId` matched the manifest's recorded `session_id` in
**76/76** cases with both present, so `find_transcript` is reliable and these really are the judge
sessions.

**Both cardinal prohibitions held in all 77.** No orchestrator wrote the verdict path, and none read
a source paper. (An earlier loose regex flagged ~50 apparent violations; every one was a false
positive — the mandated existence-check Bash call contains both `ledger/claims` and `>` via
`2>/dev/null`, and the string `content.txt` appears inside the *dispatch prompt text* the
orchestrator writes to `/tmp`, because the prompt's own prohibition names it.)

The real deviations are narrower, and they are variance in the instrument:

- **3/77 (~4%) dispatched the subagent twice** (`1572-12`, `64-96`, `1-31`) — distinct `tool_use`
  ids, distinct descriptions. This violates *"Never retry a stage. One dispatch per invocation."*
  Both dispatches write the same output path, so the **recorded verdict is the second
  adjudication** and that claim cost roughly two judge runs.
- **7/77 (~9%) reached for tools this command has no business using** — `ScheduleWakeup` (one
  called with the slash-command string as its prompt), `SendMessage`, `Monitor`, `ListAgents`,
  `ToolSearch`, `Edit`, `TaskStop`/`TaskOutput`.
- Many sessions stage the filled prompt through `/tmp` via heredoc. Not prohibited, but invented
  machinery, and one more thing that varies claim to claim.

**This sharpens the lever 2 argument rather than weakening it.** A single API call structurally
*cannot* double-dispatch, wander into `ScheduleWakeup`, or route a prompt through `/tmp`. The
nested-session path buys agentic latitude the adjudicator has been explicitly forbidden from using,
and ~4% of claims are already using some of it. Lever 2 would *reduce* instrument variance, not
just cost — which is a stronger reason to test it than the batch discount.

---

## Open questions for Phil

1. **Ramp `--max-workers` on the next real run?** Suggested: start at 4, watch for rate-limit
   errors, then 8. This is the only untested part of lever 1.
2. **Are duplicate `claim_id`s ever valid input?** Codex's open question. Records no longer collapse
   (they are collected by submission index), but the evidence file, verdict file and trace path are
   all still `claim_id`-keyed, so two same-id claims would *race on the same paths* under
   concurrency where serial dispatch merely overwrote deterministically. If duplicates cannot occur
   by construction, the existing gate is a collector regression test and nothing more is owed; if
   they can, a uniqueness precondition before dispatch is the cheap guard.
3. **Is the ~4% double-dispatch worth a fix now?** It is a real per-claim cost and variance leak.
   Cheapest containment is a gate that refuses a second dispatch, but the command file cannot
   enforce its own rules — that would need the harness to detect two `Agent` calls in the trace.
4. **Run the lever 2 agreement test?** ~50 claims down both paths, compare verdict agreement. The
   ambiguity above (does the 14KB schema enter context?) has to be resolved first, because it
   changes what "the same prompt" means.

## Landing & cleanup

- **Branch** `feat/optimizer-concurrent-dispatch`, worktree `.claude/worktrees/concurrent-dispatch`.
- **Landing gate** — do not land while `hillclimb-2026-09-07` is running out of the
  `optimizer-impl` worktree; that tree holds the uncommitted canary-path and pool/stager fixes.
  This branch was cut from `2b8ef7f` and does **not** contain them.
- **Rebase owed.** Their uncommitted `adapter.py` hunk is at `ClaimRecord.from_dict` (~line 547);
  this branch's changes are in `SarolRunner.run` (~721+) plus `_selftest`. Verified
  non-overlapping, so the rebase should be clean — but it is owed, and `--selftest` must be
  re-run green after it.
- **Cleanup on land** — prune branch + worktree, fold this doc's open questions into `NEXT.md`.
