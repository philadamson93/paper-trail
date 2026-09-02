# Meta-learnings — what iterations have established

Continuity across optimization sessions. Each iteration runs in a fresh session with no memory of
the previous one (deliberately — a retrospective evaluation of version N has to be blind to
everything learned after N), so this file is the only thing that carries forward.

**Read before iterating. Append after.** Move entries between sections as evidence accumulates;
do not delete them. A reverted attempt is as useful as a confirmed one, and more likely to be
retried by accident.

## Status

**No iterations have run.** `program-v0` is frozen and tagged but has never been scored. There is
no measured baseline for paper-trail on this benchmark — the first iteration produces the first
number that has ever existed.

Comparison points, for orientation only (other systems, not earlier versions of this one):

| System | 3-way macro-F1 |
|---|---:|
| MultiVerS | 0.52 |
| GPT-4, 4-shot | 0.45 |
| always-ACCURATE do-nothing | 0.292 (micro 0.781) |

The last row is the floor that matters. A program scoring near 0.292 with a high micro is not a
weak program, it is a program that has collapsed to the majority class.

## Confirmed

*(Fixes that improved the frontier scalar and held up on a later iteration. Nothing here yet.)*

| Iter | Change | Effect on macro-F1 | Held up at iter |
|---|---|---|---|

## Pending

Hypotheses with evidence but no iteration behind them yet. Both come from a stratified N=5 smoke
run in April 2026 (`docs/plans/experiment-april-20-findings.md`) — real observations, tiny sample.

### P1 — INDIRECT-detection blind spot

Indirectly-attributed claims are called `ACCURATE`. Two of five smoke claims failed this way,
including the most clear-cut INDIRECT instance available (a cited review in which every relevant
passage was itself an attribution elsewhere).

Proposed handle: supporting evidence snippets that end in citation markers — `(12)`, `(12,15)`,
`(Ota et al., 2009)` — signal onward attribution. The extractor's
`attestation.indirect_attribution_check` slot already exists and is currently free-form prose the
adjudicator can ignore without consequence.

Why this is the first thing to try: the signal is lexically detectable, the rubric already
distinguishes the classes, and the review/not-review split straddles two different 3-way buckets
(`INDIRECT` → NOT_ACCURATE, `INDIRECT_NOT_REVIEW` → IRRELEVANT), so getting it right pays on the
frontier scalar rather than only on the 9-way breakdown.

**Status:** untested — and **unreachable under the `retrieval` profile.**

⚠ **Read this before spending an iteration on P1.** The handle above is *extractor-side*: it
depends on `attestation.indirect_attribution_check` carrying something an adjudicator can act on.
Under `retrieval` there is no extractor, and the mechanical producer sets that field to `null` on
every claim — so the fix as written cannot be applied and cannot be measured on this rung.

What remains testable under `retrieval` is the narrower question: **can the judge detect onward
attribution from the passages it is handed?** The citation-marker signal is in the retrieved
snippets themselves, so a rubric change that tells the adjudicator to treat a trailing `(12)` /
`(Ota et al., 2009)` inside an otherwise-supporting passage as an INDIRECT signal is both legal and
in scope here. It is a weaker version of the same idea, and the delta between it and the
extractor-side fix is part of what Phase 2 is for.

### P2 — severity under-commitment

Two of five smoke claims landed one step down a severity ladder from gold (gold
`NOT_SUBSTANTIATE` → predicted `OVERSIMPLIFY`; gold `CONTRADICT` → predicted `NOT_SUBSTANTIATE`).
The second is informative: the extractor had already recorded the verbatim opposing passage that
`CONTRADICT` requires, and the adjudicator still dropped a level.

**Do not spend an iteration on this yet, for two independent reasons.** N=5 is within noise — 
whether the under-commitment is *systematic* needs N≥50. And both misses are 3-way **hits**: all
three labels collapse into NOT_ACCURATE, so the pattern costs nothing on the frontier scalar. It is
visible only in the 9-way breakdown, which is descriptive and has no published baseline.

Record instances when you see them. Revisit only if the 9-way axis ever becomes the objective,
which would be a deliberate decision by a human, not something to infer from a diagnostic.

**Status:** untested, and deliberately deprioritized.

## Reverted

*(Changes tried and backed out, with the reason. Nothing here yet.)*

| Iter | Change | Why reverted |
|---|---|---|

## Notes on the instrument itself

Things learned about the harness rather than the program. Worth recording separately — an
instrument problem misread as a program result is the expensive kind of mistake.

- **VAL is scalar-only by construction.** If you want VAL's per-class breakdown, that want is the
  leakage mechanism working as designed. Use TRAIN's.
- **`scored: false` is not a regression.** It means the number is a placeholder and `reason` says
  why. Reacting to it with a prompt edit is chasing an infrastructure signal.
- **A canary failure invalidates the whole run**, and every comparison across the break. Stop;
  never edit around it.
- **Contract files are enforced by re-hash, not by request.** Modifying one fails the iteration
  before scoring or freeze, and that iteration's work is lost.
