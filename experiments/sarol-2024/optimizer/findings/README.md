# Per-iteration findings

One file per optimization iteration: `iter-<n>.md`, where `<n>` is the iteration number from the
optimizer's turn prompt.

This directory is the *within-iteration* half of the optimizer's memory.
`experiments/sarol-2024/optimizer/meta-learnings.md` is the *across-iteration* half and is the one
every future iteration reads;
this directory is written once and consulted on purpose. The split is defined in that file's
"What belongs here" section — the short form is that per-example blame belongs here and lessons about
optimizing the task belong there.

## What an `iter-<n>.md` holds

Written by the optimizer during Phase 4, from what its Phase 1 subagents returned. The procedure is
`experiments/sarol-2024/optimizer/context/failure-mode-discovery.md`; this is the shape of its output.

```markdown
# Iteration <n> findings

**Batch:** TRAIN n=<N>, profile <p>, k=<k> · <n_correct> correct / <n_mistakes> mistakes
**primary_metric:** <value> over <n_objective_classes_present> classes

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

## Predictions
Per edit: which verdict classes should move, in which direction. This is what next iteration checks
against `per_class_f1` / `per_class_f1_9way`.
```

## Not part of the program

Files here are the optimizer's working notes, not manifest entries, so they are never frozen into a
`program-v<n>` tag. That is deliberate — see
`experiments/sarol-2024/optimizer/context/edit-surface.md`. They persist in the loop
clone as continuity, and nothing about a version's reproducibility depends on them.
