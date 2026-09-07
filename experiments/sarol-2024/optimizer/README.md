# The optimizer — and what it is allowed to optimize

Orientation for a human or a fresh session. **Not injected into any agent's context**; the
agent-facing version of this boundary is `context/edit-surface.md`.

## Two layers, and why the difference matters

- **The labeling PROGRAM** — the adjudicator prompt and the rubric it follows. This is *what gets
  optimized*. Its starting quality is not important: a null-state program is a fine starting point,
  because improving it is the optimizer's whole job.
- **The OPTIMIZER machinery** — the optimizer's own instructions, its subagent brief, the context docs
  it reads, and the Python loop that runs it. This is *what does the optimizing*, and it has to be
  right before a run starts.

A good optimizer will lift a bad program. A bad optimizer guarantees nothing — and worse, when the
curve is flat you cannot tell which of the two layers failed.

**So: we fix machinery. The optimizer fixes the program.**

## The seam is defined by the manifest, not by judgement

`experiments/sarol-2024/program-v0/manifest.json` lists the program. Everything else is machinery.
This is enforced, not merely conventional: `commit_new_version` stages **only** manifest entries
(`agentic-label-opt/engine/versioning.py:92-95`), so an edit outside the manifest is never part of any
`program-v<n>` — it is not staged, not tagged, and not reproducible.

| | Files | Who edits it |
|---|---|---|
| **Program, editable** | `prompts/adjudicator-dispatch-sarol.md`, `specs/verdict_schema_sarol.md`, and the 3 extractor/verifier prompts under `src/prompts/` | **The optimizer**, during a run |
| **Program, frozen** | `specs/verdict_enum_sarol.md`, `src/specs/verdict_schema.md`, `src/specs/verifier_results.md` | Nobody during a run; humans between runs |
| **Machinery** | `prompt/`, `context/` (6 docs), `findings/`, `meta-learnings.md`, and the `.py` files beside this README | **Us** |

A run's **profile** narrows the program further. Under `retrieval` — the only profile any run has used
— just the adjudicator and the rubric are live; the three extractor/verifier prompts are
editable-but-inert, because no extractor or verifier session runs at all.

## Why we do not hand-tune the program

Two reasons, and the second is the one that bites:

1. It is the optimizer's job. Time spent there is time spent doing the loop's work by hand.
2. **It contaminates the result.** If we hand-improve the rubric and then run the optimizer, any curve
   we produce mixes our edits with the optimizer's, and the experiment stops being able to answer
   whether the optimizer works. The null-state program is the control.

So known rubric defects are left in place deliberately, for the optimizer to find. If you notice one,
write it down — do not fix it.

**Narrow exceptions**, none of which are quality edits:

- **A broken seam.** Machinery and program disagreeing in a way that makes the optimizer's edits behave
  unpredictably. The live example: `validate_sarol.parse_rollup_order` reads the strictness ladder from
  the *rubric*, while the judge follows a second copy inside `prompts/adjudicator-dispatch-sarol.md`. An
  optimizer that reorders the rubric's ladder is silently disobeyed and then fails validation for it.
- **A frozen program file — anything the optimizer cannot reach.** "Leave it for the optimizer" is
  only an option for files the optimizer can edit. A frozen contract that states something false, or
  that wastes the judge's context on engineering history, will never be fixed by the loop. Those are
  ours — and they land **before a baseline is cut, never mid-run**, because they change the program.
- **Resetting the program to its null state** before a run — that is restoring the control, not
  improving it.

## One file currently sits on neither side

`specs/verdict_definitions_sarol.md` is in **no** manifest entry, and the judge never loads it:
`prompts/adjudicator-dispatch-sarol.md:21-22` reads only the enum contract and the rubric, and says
"Nothing else." Yet several machinery docs describe it as the judge's operative definitions.

Until that is resolved it is neither program nor machinery, and anything reasoning about it is
reasoning about a document nothing reads. See the open plan for the resolution.

## Where to look next

- `context/edit-surface.md` — the agent-facing statement of this boundary.
- `prompt/optimizer-instructions.md` — the optimizer's standing instructions.
- `context/subagent-blame-brief.md` — the self-contained brief handed to blame subagents.
- `docs/plans/optimizer-instrument-repair.md` — the open plan for the machinery.
