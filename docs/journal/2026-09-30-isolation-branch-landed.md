# 2026-09-30 — The isolation branch lands on main

The Sep 1–21 isolation work (branch `sarol-optimizer-concurrent`, 254 commits) is now on `main`. It is
what the Sarol hill-climb ran on through `program-v10`: the graders in a sealed container, the seal
check, the setup pin, the per-pass answer reset and the concurrent dispatcher.

## What was not built

- **The optimizer's container (isolation step 1e).** The optimizer still runs on the host. It moved
  into the shared engine as its optimizer plan (landed on the engine's `main` at `22e4833`), and
  paper-trail adopts it next.
- **Step 0a's absent-check.** Replaced by the Sep 21 per-pass answer reset, which is now the engine's
  program runner (`edc8446`).

## What the transcripts showed

No optimizer or grader session read test data. Two optimizer sessions listed the validation answer-key
filenames; none opened one. The graders were sealed throughout, so the scores are clean. The rubric
carries one number counted from the test set, removed in the next program version.

## How it landed

`main` was merged into the branch, not rebased, and `main` fast-forwarded to that merge. The branch's
plan docs and journal entries were copied to the shared planning folder first and left out of git,
following the 2026-09-19 rule that only code lands. Plans and the master list of what moves into the
engine live in the shared planning folder: `paper-trail/isolation-protocol.md` and
`agentic-label-opt/2026-09-22-engine-consolidation-umbrella.md`.

## What's next

paper-trail moves its optimizer and graders onto the engine's sealed sessions
(`paper-trail/2026-09-30-adopt-engine-sessions.md`). No paper-trail hill-climb runs until the engine's
run bookkeeping and shared driver have also landed.
