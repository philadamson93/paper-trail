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
| **Program, frozen** | `specs/verdict_enum_sarol.md`, `specs/verdict_definitions_sarol.md`, `src/specs/verdict_schema.md`, `src/specs/verifier_results.md` | Nobody during a run; humans between runs |
| **Machinery** | `prompt/`, `context/` (6 docs), `findings/`, `meta-learnings.md`, and the `.py` files beside this README | **Us** |

⚠ **"Program, editable" is not editable all the way down.** The rubric's **eight class definitions are
the paper's verbatim text** (Sarol et al. 2024 §2.2 / Table 1) and are not the optimizer's to reword;
what is editable is the house layer around them — boundaries, tie-breaks, decomposition,
multi-citation attribution, rollup — and that layer is marked as house text in the file. The same
eight definitions are inlined in the dispatch prompt, because the judge reads both documents in one
session and a divergence between them would silently defeat the scheme. `verdict_definitions_sarol.md`
holds the same text plus its provenance and is frozen; the rubric is the single *operative* copy.

This distinction is not decorative. Three of those definitions had silently diverged from the paper —
all by our own additions — and five optimizer iterations hill-climbed on top of them before the
divergence was found. `scripts/check_paper_fidelity.py` is the guard: it asserts the eight verbatim
definitions everywhere the judge can read them, and fails if a retired clause reappears.

### Three record surfaces, not two

`findings/iter-<n>.md` is run-local per-iteration detail and is not committed. `meta-learnings.md`
carries **verified reusable** heuristics only, dated, and is committed. `docs/journal/` is the curated
cross-run record — **the optimizer never writes it**; promotion out of `findings/` happens at landing,
under human curation. The routing rule lives in
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`; the other two files restate it
and must be kept in step.

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

## One file that sits on neither side — resolved 2026-09-07, re-resolved 2026-09-09

`specs/verdict_definitions_sarol.md` is **frozen program the judge never reads.** Those are two
separate facts and the file's history is a record of getting the pair wrong in both directions:

- **It IS in the manifest** (since 2026-09-09): entry 8 of 9, `contract_file: true`, hashed into
  `combined_hash`. Editing it changes the program's identity and forces a re-freeze. That is the
  point — the reconciled scheme must not be reworded without cutting a version.
- **The judge never loads it:** `prompts/adjudicator-dispatch-sarol.md` reads only the enum contract
  and the rubric, and says "Nothing else." So it is never itself the cause of a judge's mistake.

⚠ Until 2026-09-09 this section, the file's own header, and two other docs all said it was in **no**
manifest entry. That was true when written and was falsified by the freeze in the same change that
reconciled the text. It is called out here because a stale self-description inside a `contract_file`
is the exact defect class the optimizer's Step 6 duty exists to delete — and this one had been
hashed into the freeze.

It is the right thing to consult when asking whether a gold label is defensible, and the wrong thing
to consult when asking why the judge decided something.

✅ **The reconciliation it used to owe is DONE (2026-09-09).** The text is now the paper's verbatim
§2.2 / Table 1 wording with provenance recorded in the file. Three definitions had diverged — all by
our own additions, all in the judge's read path — and `scripts/check_paper_fidelity.py` now guards
against their return.

## The enum contract and the code must agree — a human's job, not the judge's

`specs/verdict_enum_sarol.md` and `scripts/parse_verdict.py` are two copies of one contract: the
nine labels are `SAROL_9`, the NOT_ACCURATE row is `NOT_ACCURATE_3WAY`, the IRRELEVANT row is
`IRRELEVANT_3WAY`, and the collapse itself is `to_3way()`. `score_sarol3.py` imports those names
rather than redefining them, so the collapse is single-sourced *in code*; what is not automatic is
the doc agreeing with the code. **If the two ever disagree, `parse_verdict.py` is what actually
scored the run — reconcile before trusting the number.**

This used to be stated inside the enum file itself, where it did no good and cost something real:
that file is loaded into the judge's context on every claim, roughly fifty times a run, and a
classifier has no use for an instruction to an engineer about reconciling two source files. It was
moved here in the 2026-09-07 trim, which took the file from 70 lines to 49.

## Where to look next

- `context/edit-surface.md` — the agent-facing statement of this boundary.
- `prompt/optimizer-instructions.md` — the optimizer's standing instructions.
- `context/subagent-blame-brief.md` — the self-contained brief handed to blame subagents.
- `docs/plans/optimizer-instrument-repair.md` — the open plan for the machinery.
