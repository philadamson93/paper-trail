Reference: docs/claude_ops.md

# Plan B — Phase 2: make evidence acquisition programmable (and comparable)

**Status: Draft — scoping only, design work deferred** (2026-09-09) · **Reviewed: No**
**Split from** `docs/plans/optimizer-prompt-investigative-latitude.md` (Plan A) on Codex's
recommendation — feedback at `docs/plans/reviews/optimizer-prompt-investigative-latitude-feedback.md`.
**Depends on:** Plan A (paper-verbatim baseline recut) and the isolation plan (it rewrites the same
driver). Both land first.

## Goal

Make the optimizer able to change **how evidence reaches the judge**, not just how the judge reasons
about it — which is Phil's ruling ("BM25 failing to retrieve the needed passage is still the
optimizer's problem… it doesn't NEED to use BM25 at all"), and which the architecture already
anticipates but cannot currently execute.

## Why this is smaller than it looks

The capability is already designed and already manifest-owned. What is missing is one thing: the
driver cannot dispatch the stages that use it.

| profile | evidence producer | edit scope | runnable today? |
|---|---|---|---|
| `retrieval` (`profiles.py:107`) | `bm25`, `bm25-top20`, `k=20`, one query | `JUDGE_SCOPE` | yes — Phase 1 |
| `agentic` (`profiles.py:121`) | `extractor` agent reading the staged paper, `source_mode="pdf"` | `JUDGE_SCOPE + ACQUISITION_SCOPE` | **no** |
| `paperclip` (`profiles.py:136`) | `paperclip` conversational query | `JUDGE_SCOPE + ACQUISITION_SCOPE` | **no** |

`ACQUISITION_SCOPE` (`profiles.py:55`) is `(EXTRACTOR_PDF, EXTRACTOR_PAPERCLIP, VERIFIER)` — three
prompts that are **already manifest entries and already optimizer-editable**. So "an agent reads the
whole paper and decides what evidence matters" is a prompt the optimizer can write today.

The blocker is `profiles.py:59-61`: the driver "implements the Phase 1 adjudicator path and aborts
`extractor` / `verifier` with `STAGE_NOT_IMPLEMENTED`, so a profile requiring them cannot complete a
run however well-formed it is."

**What this plan therefore is NOT:** a versioned retrieval-config schema (`query_strategy`, `k`,
`ranker`, `bm25_k1`, `bm25_b`). Codex proposed that; Plan A declines it. It would engineer tunability
into a profile whose fixity is deliberate — the `retrieval` profile pins BM25 precisely so Phase 1
measures the adjudicator alone — and it would duplicate, in config, a capability Phase 2 already
grants in prose. If `retrieval_k` tuning is ever wanted for the cheap profile, that is a one-field
addition, not an architecture.

## Approach (to be designed — this is the scope, not the solution)

1. **Implement `extractor` and `verifier` dispatch in the driver.** This is the load-bearing change.
   Coordinate with Plan A's Step 7 driver split and with the isolation plan's harness-side prompt
   rendering — all three touch `.claude/commands/sarol-eval-item.md`.
2. **Make the acquisition condition part of program identity.** Today `run_manifest.json`, the scorer
   breakdown, the VAL allowlist, releases, resume hard fields and baseline summaries carry only
   `profile`, `retrieval_k` and model (`adapter.py:983`, `:1415`, `:1482`, `dispatcher.py:818`,
   `scripts/run_baseline.py:166`). A Phase-2 run needs the acquisition condition recorded with enough
   fidelity to replay. Specify exact new keys/types, the release schema-version impact, and migration
   behaviour for existing `0.2.0` releases.
3. **Resolve the comparability problem.** Changing acquisition changes the evidence, so
   version-to-version deltas confound acquisition with judgment. Plan A's earlier draft asserted a
   comparability *rule* that the loop cannot execute: the engine scores the base program before the
   edit and the new program after, with no slot for re-scoring the previous program under the new
   condition (`engine/loop.py:338`, `:394`, `:437`). This plan must decide the model and who pays:
   - **OQ-B1 — RESOLVED, dropped** (Phil, 2026-09-09: "nope don't care about this at all"). No
     counterfactual run, no 2×2, no factorial program×condition model, and therefore **no engine or
     adapter API change** for comparability. The confound is accepted: when acquisition changes, a
     version-to-version VAL move no longer isolates a judgment improvement, so read such a step as
     "the system got better" rather than "the rubric got better." Record the acquisition condition in
     the run manifest (item 2 above) so the confound is at least *visible* after the fact — that is
     bookkeeping, not a comparison mechanism. This removes what Codex called Plan B's blocking design
     question.
4. **Cost.** Phase 2 is three sessions per claim against Phase 1's one. At the measured ~$0.18/claim
   for the adjudicator alone, a 50-claim Phase-2 iteration is materially more expensive than $25 —
   size it before committing.
5. **Reporting discipline** (pre-existing, `profiles.py:118-120`): Phase 2 is "reported as a delta over
   Phase 1's *optimized* adjudicator, never head-to-head against the published baselines (C6.3)."
   Whatever this plan builds must preserve that.

## Files to Modify (indicative — firm up at design time)
- `.claude/commands/sarol-eval-item.md` — extractor/verifier dispatch (coordinate: Plan A Step 7 +
  isolation plan).
- `experiments/sarol-2024/optimizer/profiles.py` — the dispatchable-stages constraint at :59-61.
- `experiments/sarol-2024/optimizer/adapter.py` — acquisition condition in run manifest / release /
  attestation (:983, :1415, :1482).
- `experiments/sarol-2024/optimizer/dispatcher.py` (:818), `scripts/run_baseline.py` (:166).
- `experiments/sarol-2024/optimizer/context/edit-surface.md` — Phase-2 scope, once executable.
- Release schema version + `engine/resume.py` hard fields, if acquisition identity grows.

## Open Questions
- ~~**OQ-B1** — comparability model and who pays.~~ **Resolved: dropped** (see Approach item 3).
- **OQ-B2** — does Phase 2 use `source_mode="pdf"` (staged flat file) or `paperclip` (needs the cited
  papers ingested into a paperclip corpus first, at which point the `paperclip_cli` runtime pin
  becomes load-bearing at run time rather than merely recorded)?
- **OQ-B3** — is optimizer-authored *ranking code* ever in scope, or is the acquisition prompt the
  whole lever? Plan A assumes the latter. The former needs a sandbox and validation story.

## Verification (to be designed)
At minimum, before any paid Phase-2 run:
- A deterministic fixture proving two acquisition prompts yield **different selected evidence**, a
  changed program identity, and complete provenance in run manifest / release / baseline summary.
- (Dropped with OQ-B1: no counterfactual-run fixture. The acquisition condition must still appear in
  the run manifest / release / baseline summary so a later reader can see which condition produced a
  number.)
- The Phase-1 → Phase-2 delta reporting rule (C6.3) still holds.

## Landing & cleanup
- **Branch:** `feat/phase2-acquisition`, cut after Plan A lands on `sarol-optimizer-concurrent`.
- **Order:** isolation plan → Plan A → Plan B. All three touch the driver; this one lands last.
- **Landing gate:** the two verification fixtures green; cost sized and approved. (OQ-B1 dropped.)
- **Cleanup:** prune branch/worktree; `Status: Completed`; `docs/plans/README.md` row and
  `docs/plans/NEXT.md` pointer.
