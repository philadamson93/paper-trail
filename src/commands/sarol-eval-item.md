The record of how **one** frozen-program stage is run against **one** staged Sarol 2024 citation
instance. **Nothing executes this file.**

This is an **experiment instrument**, not a user-facing command, and no session runs it (OQ1). The
dispatcher, `experiments/sarol-2024/optimizer/dispatch_prompt.py` (runner code, not program), does the
work deterministically: it checks the staged inputs, fills the slots of the frozen adjudicator prompt
(`experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`, the text between its `## Begin
dispatch prompt` and `## End dispatch prompt` markers) and hands the result to the adjudicator. The adjudicator runs as a sealed
session (PT-A), one per claim, in the shared engine's
program runner: the materialized program mounted read-only at `/workspace/program`, only the claim's
own folder writable at `/workspace/call`, deny-by-default permissions, `Read` and `Write` only.

It stays a frozen manifest entry: it is part of the program a version freezes, and it states the rules
the measurement keeps. Editing it changes no dispatch.

## The rules the measurement keeps

The pipeline enforces these. Any prompt text that would tell a session to break one corrupts the
measurement rather than merely failing it.

- **Never ask a question.** No session in this pipeline has a user attached.
- **Never read the source paper outside the evidence the stage is given.** Under `retrieval` the
  evidence is the BM25 envelope written before the adjudicator runs; that subset is the experimental
  condition being measured.
- **Never read, and never look for, gold labels.** Gold lives outside the repository
  (`$PAPER_TRAIL_GOLD_DIR`) and is not mounted in any sealed session. `parse_verdict.py` is the only
  code allowed to touch it, at scoring time, in a different process.
- **Never write the stage's output file yourself.** Only the adjudicator writes its verdict, to
  `/workspace/call/ledger/claims/<claim_id>.json`, stamped with the pass id it was given.
- **Never repair, reformat, re-score, or "improve" the adjudicator's output.** If it is wrong, it is
  wrong; `validate_sarol.py` owns the content rule, and an invalid verdict is scored as a miss.
- **Do not validate its content** anywhere but `validate_sarol.py`, the validator of record: a second
  opinion can only disagree with it.
- **Never retry a stage.** One session per claim per pass. A crashed or timed-out call is scored as a
  miss and counted as failed, never re-run inside the pass.
- **Never edit the frozen program during a measurement.** It is mounted read-only.

## What the dispatcher does, step by step

| Step | Where |
|---|---|
| Resolve and check inputs: staging info, evidence envelope, prompt and specs present | `dispatch_prompt.slot_values` raises `EVIDENCE_MISSING`, `CLAIM_ID_MISMATCH`, `CLAIM_TEXT_MISMATCH`, `CLAIM_TYPE_MISSING`; the program runner stops the pass with `stage_failed` |
| Collect the slot values | `dispatch_prompt.slot_values` |
| Fill the frozen prompt and dispatch it | `dispatch_prompt.render` (one regex pass; an unfilled slot raises `SLOT_UNRESOLVED`); the prompt goes to the adjudicator's sealed session |
| Verify the verdict file exists | the program runner's receipt; `validate_sarol.py` on every verdict |

## Stages not implemented: `extractor`, `verifier`

Recognised, deliberately not built (`STAGE_NOT_IMPLEMENTED`). Phase 1 (`retrieval` profile) runs the
adjudicator alone; the evidence envelope is produced mechanically, so no extractor session runs. The
`extractor` and `verifier` stages belong to the Phase 2 `agentic` profile (plan Part C6.1) and are not
built. `profiles.unrunnable_reason` refuses such a profile before any spend, and the grader program
(`sarol_program.SarolProgram`) refuses any profile whose stages are not the adjudicator alone. When
those stages are built, widen `profiles.IMPLEMENTED_STAGES` in the same change.
