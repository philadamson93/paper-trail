# Per-iteration findings

One file per optimization iteration: `iter-<n>.md`, where `<n>` is the iteration number from the
optimizer's turn prompt.

This directory is the *within-iteration* surface of the optimizer's record-keeping. There are
**three**, with mutually exclusive scopes, and **which record takes what is defined in one place** —
the *"The three record surfaces, and what goes in which"* section of
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`. Restated here only as a routing
table:

| surface | scope | who writes | committed |
|---|---|---|---|
| this directory, `iter-<n>.md` | run-local per-iteration detail: metrics, blames, modes, edits, predictions | the optimizer, every iteration | no |
| `experiments/sarol-2024/optimizer/meta-learnings.md` | **verified reusable** optimization heuristics only, each dated | the optimizer, when a lesson generalizes | yes |
| `docs/journal/` | curated cross-run decisions and postmortems | a human, or the landing process promoting a finding | yes |

⚠ **The optimizer does not write `docs/journal/`.** Promotion out of this directory into the journal
happens at landing, under human curation — writing a journal entry per suspected defect would
duplicate what is already here and bypass that curation.

**A defect the optimizer cannot fix belongs here**, in the iteration's own file: a suspected-wrong
gold label, a harness bug, an evidence window it could not work around. Filing it here is what makes
a no-edit iteration a reportable outcome rather than a silent one.

**One file here IS read every iteration: the previous one.** Step 6 of the standing instructions
writes a prediction about which verdict classes the iteration's edits should move, and the first
thing the *next* iteration does is open `iter-<n-1>.md` and check that prediction against the new
release. That check is what makes an iteration a test rather than a guess, so this directory is not
write-only — `iter-<n-1>.md` has exactly one reader and it is guaranteed to arrive.

## What an `iter-<n>.md` holds

Written by the optimizer at step 6, from what its step 3 subagents returned. The procedure is
`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md`; this is the shape of its output.

```markdown
# Iteration <n> findings

**Batch:** TRAIN n=<N>, profile <p>, k=<k> · <n_correct> correct / <n_mistakes> mistakes
**primary_metric (accuracy):** <value>, against a do-nothing floor of <do_nothing_floor>
**macro_f1_renormalised:** <value> over <n_objective_classes_present> classes — the collapse check

## Last iteration's prediction, checked
What `iter-<n-1>.md` predicted would move, what actually moved, and whether the hypothesis held.
Omit only on iteration 1, which has no predecessor.

## Draw
Which claims were read, how they were chosen, and how many subagents read them.

## Per-example blames
The records the subagents returned — claim_id, gold/pred, blame, mechanism, evidence cue,
confidence. One row per claim, each claim blamed once.

## Failure modes
Each mode as a mechanism, with its count and the claim_ids behind it. Note which modes are out of
reach of the current edit surface and why.

## Edits made
What changed, in which file, aimed at which mode.

## Defects not fixable by a prompt edit
Anything found that editing the program cannot address — a suspected-wrong gold label (one label, the
evidence quote, the reasoning), a harness defect, an evidence window that is the binding constraint.
If this section carries the iteration's highest-mass mode, say plainly that no program edit is
warranted and why; that is a terminal stop for human triage, not a failure.

## Predictions
Per edit: the class or boundary you expect to move, the direction, and **the observable you will read
next time** — a named `per_class_f1_9way` entry, the VAL trend, or a specific `claim_id`'s label.
Next iteration resolves each as **held / did not hold / could not tell**.
```

## Not part of the program

Files here are the optimizer's working notes, not manifest entries, so they are never frozen into a
`program-v<n>` tag. That is deliberate — see
`experiments/sarol-2024/optimizer/context/edit-surface.md`. They persist in the loop
clone as continuity, and nothing about a version's reproducibility depends on them.
