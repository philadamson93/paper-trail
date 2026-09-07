Reference: docs/claude_ops.md

# Implementation Feedback: Optimizer prompt consistency / instrument repair

## Verdict
A follow-up commit is warranted. The core optimizer/code changes are mostly implemented and the offline suite passes 433/433, but the `program-v0` re-freeze is not complete: the manifest self-verifies against source refs, while the actual `program-v0` tag still points at the old enum bytes and old combined hash.

## Plan Coverage

| Item | Status | Evidence | Notes |
|---|---|---|---|
| S0 | Done | `experiments/sarol-2024/optimizer/README.md:20` | Human-facing seam doc says the manifest defines the program and explains program vs machinery. |
| S0b | Done | `experiments/sarol-2024/optimizer/context/edit-surface.md:7` | Agent-facing edit surface uses the manifest as the rule, not as one signal among several. |
| S1 | Done | `experiments/sarol-2024/optimizer/context/task-and-scoring.md:34` | Objective text is inverted to accuracy, with macro as diagnostic. |
| S2 | Done | `experiments/sarol-2024/optimizer/adapter.py:350` | Shared metric name is now `sarol_accuracy_9class`; release docs also use it at `experiments/sarol-2024/optimizer/context/release-format.md:24`. |
| S3 | Done | `experiments/sarol-2024/specs/verdict_enum_sarol.md:39` | Enum contract no longer calls 3-way macro the frontier; release doc calls 9-way accuracy the objective at `experiments/sarol-2024/optimizer/context/release-format.md:58`. |
| S4 | Done | `experiments/sarol-2024/optimizer/context/release-format.md:31` | Payload examples list all nine objective classes. |
| S5 | Done | `experiments/sarol-2024/optimizer/context/task-and-scoring.md:107` | One labelled do-nothing calibration table for repaired drawable dev pool, n=311. |
| S6 | Done | `experiments/sarol-2024/optimizer/meta-learnings.md:31` | File is reset and explains the retired metric history is intentionally absent. |
| S7 | Done | `experiments/sarol-2024/optimizer/context/edit-surface.md:98` | Docs now state VAL/TEST isolation is structural, not audit-ledger enforced. |
| S8 | Done | `experiments/sarol-2024/optimizer/context/playbook.md:54` | Forward-only loop and no automatic step-back are stated plainly. |
| S9 | Done | `experiments/sarol-2024/optimizer/context/edit-surface.md:145` | Ladder hazard names the two copies and the first-fenced-block parser behavior. |
| S10 | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:256` | Canary states and handling are documented; real run refusal is implemented at `experiments/sarol-2024/optimizer/dispatcher.py:671`. |
| S11 | Done | `experiments/sarol-2024/optimizer/context/release-format.md:273` | Missing-release reconstruction recipe is present. |
| S12a | Done | `experiments/sarol-2024/optimizer/context/subagent-blame-brief.md:11` | Brief requires opening rubric and definitions, and no longer claims all context is self-contained in one file. |
| S12b | Done | `experiments/sarol-2024/optimizer/findings/README.md:11` | Previous `iter-<n-1>.md` is explicitly read by the next iteration. |
| S12c | Done | `experiments/sarol-2024/optimizer/context/edit-surface.md:50` | Judge context window is documented as enum, rubric, and evidence envelope. |
| S12d | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:274` | Crash handling covers the previous edit never being scored. |
| S12e | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:175` | Standing instructions include the “name the test that decides its terms” rule. |
| S12f | Done | `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md:98` | Anecdote/candidate/established/dominant mode table gives an actionable scale. |
| S12g | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:220` | Simplicity criterion now defines “same” via rough sampling error. |
| S12h | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:241` | Budget cap is described as hidden, with concrete default fan-out. |
| S12i | Done | `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md:58` | Fan-out sizing and disjoint slices are clarified. |
| S12 | Done | `experiments/sarol-2024/optimizer/context/subagent-blame-brief.md:3` | Handoff now names three inputs: claim ids, corpus path, and profile. |
| S13 | Done | `experiments/sarol-2024/optimizer/adapter.py:1021` | Mistake rows carry `trace_ref`; brief documents real fields and fallbacks at `experiments/sarol-2024/optimizer/context/subagent-blame-brief.md:51`. |
| S14 | Done | `experiments/sarol-2024/optimizer/context/subagent-blame-brief.md:86` | Adds `execution` category and removes “rare” framing from `gold`. |
| S14a | Done | `experiments/sarol-2024/optimizer/context/task-and-scoring.md:94` | IRRELEVANT pool-filter causal claim is corrected. |
| S14b | Done | `experiments/sarol-2024/optimizer/context/playbook.md:20` | “Phase” is reserved for profile ladder; engine/optimizer steps are distinguished. |
| S15 | Done | `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md:119` | Retrieval reach test splits “right passage not retrieved” from “judge mishandled thin window.” |
| S16 | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:181` | Separability language is relaxed; joint edits are accepted. |
| S17 | Done | `experiments/sarol-2024/optimizer/context/failure-mode-discovery.md:58` | Agent sizes fan-out against the question and budget. |
| S18 | Done | `experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md:110` | Standing prompt sequence is check prediction, establish numbers, fan out, cluster, edit, predict. |
| S19 | Done | `experiments/sarol-2024/optimizer/context/playbook.md:111` | Findings vs meta-learnings rule points to one authoritative section instead of restating. |
| S20 | Done | `experiments/sarol-2024/specs/verdict_enum_sarol.md:39` | Enum is trimmed to classifier-relevant contract and no longer carries engineering binding history. |
| S21 | Done | `experiments/sarol-2024/specs/verdict_definitions_sarol.md:3` | Definitions file is marked optimizer-facing reference, not judge/program input. |
| S22 | Done | `experiments/sarol-2024/optimizer/context/task-and-scoring.md:145` | Smaller fixes are covered: `per_class_f1_9way`, manifest reasoning clarification, cost/probe wording, full edit-surface table, repaired sampling figures. |
| S23 | Done | `experiments/sarol-2024/scripts/score_sarol3.py:190` | `primary_metric` is 9-way accuracy, `do_nothing_floor` is emitted, and selftests negative-control within-bucket confusion at `experiments/sarol-2024/scripts/score_sarol3.py:281`. |
| S24 | Done | `experiments/sarol-2024/optimizer/sampling.py:546` | `val_inputs_for(stratify=False)` is the default and the selftest checks the population share. |
| S25 | Done | `experiments/sarol-2024/optimizer/adapter.py:1003` | Mistake corpus correctness is now 9-way label equality; selftest negative-control is at `experiments/sarol-2024/optimizer/adapter.py:1795`. |
| S26 | Partial | `experiments/sarol-2024/optimizer/dispatcher.py:690` | Startup tree guard exists and discriminates, but the actual `program-v0` tag was not re-cut to the new freeze; see Critical Drift. |

## Critical Drift

- Severity: Critical | Plan says the program-v0 re-freeze should restore the tree to pristine v0, rewrite the manifest, and leave the manifest self-verifying against the composed tag. Code/data does: `experiments/sarol-2024/program-v0/manifest.json:15` records combined hash `0a02710cbd88...`, but `python3 experiments/sarol-2024/scripts/freeze_program_v0.py --verify --tree program-v0` fails with `MISMATCH (composed tree program-v0) experiments/sarol-2024/specs/verdict_enum_sarol.md`. The script explicitly treats tag verification as the composed tree gate at `experiments/sarol-2024/scripts/freeze_program_v0.py:159`. Required fix: re-cut or move the `program-v0` tag to the composed tree whose enum hash is `11179f3...`, push/update that tag as intended, then rerun `--verify --tree program-v0`.

## Missing Pieces

- The old combined hash is still cited as current in existing docs. The prompt asked to verify that nothing still cites `391f54fae7c5`; `docs/plans/papertrail-optimizer-requirements.md:63`, `docs/plans/papertrail-optimizer-requirements.md:203`, `docs/plans/papertrail-optimizer-requirements.md:323`, and `docs/plans/papertrail-optimizer-requirements.md:403` still present it as the active `program-v0` identity. Required fix: update those current-contract statements or clearly mark them superseded by the 2026-09-07 re-freeze.
- `docs/plans/NEXT.md:125` still says “Now `sarol_macro_f1_6class`” and describes the retired macro-six objective. Later lines correct the objective, so this is archival drift rather than the active optimizer instructions, but this file was touched in the reviewed range and is a handoff document.

## Contract Violations

- `program-v0` tag mismatch: local tag resolves to `67fb280...` while `HEAD` is `fa470fc...`; the tag message still says `combined_hash: 391f54fae7c5...`, and `git show program-v0:experiments/sarol-2024/specs/verdict_enum_sarol.md | shasum -a 256` yields the old `46e31e4...` hash rather than manifest hash `11179f3...`. The engine materializer reads committed entries from the supplied version SHA via `git show` at `/Users/philadamson/Documents/Misc/Projects/agentic-label-opt/engine/materialize.py:63`, so a stale tag remains a real materialization contract problem even though `run_loop` starts from `HEAD` in fresh local runs.

## Test Gaps

- No selftest invokes `freeze_program_v0.py --verify --tree program-v0`; the offline suite passed 433/433 while that command fails. Add this to an offline gate or a documented required pre-run command.
- The dispatcher startup guard verifies the working tree against the manifest (`experiments/sarol-2024/optimizer/dispatcher.py:701`), not that `current_tag` resolves to the same manifest bytes. That is why S26 passes while the re-freeze/tag contract is broken.
- One adapter selftest label is stale: it prints “the frontier scalar is 3-way macro-F1” at `experiments/sarol-2024/optimizer/adapter.py:1596` while checking only `score.primary_metric.name == PRIMARY_METRIC_NAME`. The assertion has teeth, but the test name now lies.

## Defensible Deviations

- S23 implementing 9-way accuracy is defensible. The scorer compares `pred_label == gold_label` at `experiments/sarol-2024/scripts/score_sarol3.py:194`, reports `do_nothing_floor` at `experiments/sarol-2024/scripts/score_sarol3.py:214`, and keeps 3-way/macro diagnostics. That aligns with S25’s within-bucket-confusion requirement and is internally consistent.
- S13 choosing to put `trace_ref` on mistake rows is defensible. The row-level copy at `experiments/sarol-2024/optimizer/adapter.py:1021` makes the brief’s optional trace read followable without handing subagents the run manifest.

## Suggested Code Edits

- Add a pre-run/tag verification gate that compares `current_tag` against every manifest entry when `current_tag == store.program_version`, or at minimum wire `freeze_program_v0.py --verify --tree program-v0` into the offline/pre-run checklist.
- Rename the stale adapter selftest description at `experiments/sarol-2024/optimizer/adapter.py:1596` so future failures do not send readers back to the retired objective.

## Questions For The Author

- Was the `program-v0` tag intentionally left unmoved because tags are managed outside the pushed branch, or was it expected to be updated as part of the re-freeze?
- Should older plan docs remain immutable history, or should current-contract lines in `papertrail-optimizer-requirements.md` be amended now that they contradict the live manifest?

## Audit Trail

- Read `docs/claude_ops.md`.
- Read `docs/plans/optimizer-instrument-repair.md` in full.
- Inspected `git log --oneline 9cc932f..HEAD` and `git diff 9cc932f..HEAD`.
- Ran requested selftests: `sampling.py`, `adapter.py`, `dispatcher.py`, `canary.py`, `validate_sarol.py`, `profiles.py`, `evidence_producers.py`, and `scripts/score_sarol3.py --selftest`; result: 433/433 passed.
- Verified manifest source refs: `python3 experiments/sarol-2024/scripts/freeze_program_v0.py --verify`; result: OK, 8/8 and combined hash `0a02710cbd88` reproduces.
- Verified composed tag: `python3 experiments/sarol-2024/scripts/freeze_program_v0.py --verify --tree program-v0`; result: FAIL, enum mismatch.
- Recomputed HEAD file hashes against manifest entries; all 8 HEAD files matched and the combined hash reproduced.
- Searched for old/new combined hashes; found stale current-contract uses of `391f54fae7c5` outside the updated manifest.

---

## Disposition (applied 2026-09-07, after the audit)

Every finding was agreed with; none was disputed. Applied in commits `988456a`..`HEAD`:

- **Critical Drift — `program-v0` tag not re-cut.** Correct, and it was an explicit plan instruction
  I had missed: *Landing & cleanup* says "restore the tree to pristine `v0` **and re-tag**". I did
  the restore, not the re-tag. Tag re-cut onto `988456a` with a message recording the new
  `combined_hash 0a02710cbd88` and naming the superseded `67fb280`.
  `freeze_program_v0.py --verify --tree program-v0` now reports **OK 8/8**, and
  `materialize_smoke.py` confirms the engine writes all 8 files byte-faithfully from that SHA.
  The requirements plan already recorded this exact Stop-condition at its line 403 ("a `program-v0`
  tag cut over the superseded fileset → delete the tag and re-cut it after the re-freeze").
- **Test Gap 2 — the guard checked the tree, not the tag.** The sharpest finding in the audit. The
  S26 guard was built to stop a mislabelled baseline and had a blind spot in exactly that dimension,
  because `engine.materialize` reads from the tag via `git show` and never off disk. Added
  `SarolProgramStore.verify_tag_tree()` and a second refusal in `run_optimization`. Gated with the
  Codex scenario reproduced literally — clean tree, stale tag — plus a negative control asserting
  the *tree* check calls that same repo clean, and a check that an unresolvable tag is a violation
  rather than a silent pass. Negative-controlled: disabling the tag check turns both wiring gates
  red. Gates 433 → 439.
- **Test Gap 1 — nothing ran `--verify --tree`.** Covered by the above; the mechanism is now gated
  in `dispatcher._selftest` against a purpose-built repo rather than depending on a local tag.
- **Test Gap 3 — stale selftest label.** `adapter.py` no longer describes the assertion as "the
  frontier scalar is 3-way macro-F1".
- **Missing Piece 2 — `NEXT.md` archival drift.** Superseded marker added; the 2026-09-03 narrative
  is left intact as history.
- **Missing Piece 1 / Question 2 — stale `combined_hash` in `papertrail-optimizer-requirements.md`.**
  Put to the author, who chose superseded markers over rewriting. Three added at the
  current-contract sites (lines ~63, ~203, ~323); narrative untouched.
- **Question 1 — was the tag intentionally left unmoved?** No: it was an oversight, now fixed. The
  author additionally chose to **push** the re-cut tag (`origin/program-v0`, new — v0 had never been
  pushed, though v1–v3 were), so the baseline identity is reproducible from a fresh clone.

Both *Defensible Deviations* were confirmed by the author as intended: S23's 9-way accuracy and
S13's row-level `trace_ref`.
