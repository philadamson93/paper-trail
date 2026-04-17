# Claude Code Operating Standards

This document defines how Claude Code should operate in the `paper-trail` repo. Reference this file at the start of every planning document.

Adapted from the VISTA `claude_ops.md` with paper-trail-specific differences noted inline.

---

## Core Principles

1. **Plan before you code.** Enter Plan mode (Shift+Tab twice) before writing any code for a non-trivial change. Iterate on the plan until solid, then execute.
2. **Re-enter plan mode when direction changes.** If you discover a new constraint, architectural concern, or a change in direction while implementing, pause and re-enter plan mode.
3. **A wrong fast answer is slower than a right slow answer.** Prioritize correctness over speed.
4. **You don't trust; you instrument.** Provide verification mechanisms for every change. For this repo that usually means: run the modified command against an example PDF / `.bib` / manuscript and check the artifact.
5. **YAGNI.** Don't build for hypothetical futures. Implement what's needed now, nothing more.

---

## Environment

- **Local code execution is allowed on this machine.** Unlike the VISTA VM setup, this repo can be developed and tested locally.
- **The repo is a collection of slash-command prompts.** Most "code" in `paper-trail` is natural-language prompt text in `.claude/commands/*.md`, read by Claude at invocation time. There is no build step, no runtime, and no test suite.
- **"Testing" means running the command.** Commands are validated by invoking them against a real PDF / `.bib` / manuscript and inspecting the resulting artifact (ledger, report, refs.bib). There is no unit-test suite to gate on.

---

## Planning Workflow

### Starting a Task

1. Enter Plan mode before any implementation.
2. **Read the existing command files and templates first.** The four existing commands (`init-writing-tools`, `fetch-paper`, `ground-claim`, `verify-bib`) define conventions — invocation forms, "raise, don't fix" principle, ledger schema, taxonomies. Extend these rather than diverging.
3. Draft the plan in plan mode's internal file.
4. Begin the plan document with:
   ```
   Reference: docs/claude_ops.md
   ```
5. Articulate both *what* you're building and *why*.
6. Ask: "Are there any points of ambiguity about this plan?" to surface underspecified requirements.
7. Iterate until solid, then exit plan mode.

### Saving the Plan (after exiting plan mode)

Plan mode can only write to its internal plan file (`~/.claude/plans/`). It cannot write to `docs/plans/` in this repo. So:

1. **Exit plan mode** — this approves plan *content*, not implementation.
2. **Immediately copy the plan to `docs/plans/<descriptive-name>.md`** (not `plan_01.md`). Traceability across sessions depends on this.
3. **Stop and confirm** — ask the user before starting implementation.

### When to Re-enter Plan Mode

- The current approach won't work.
- A new requirement or constraint surfaced.
- Scope turned out larger than expected.
- An architectural concern affects the design.

### Plan Document Structure

```markdown
Reference: docs/claude_ops.md

# [Descriptive Task Title]

## Goal
What are we building and why?

## Approach
How will we implement this?

## Files to Modify / Create
- path/to/file.md — description of changes

## Open Questions
- Ambiguities still to resolve?

## Verification
How will we know this works? (For paper-trail: which example PDF / `.bib` will we run the command against, and what should the artifact contain?)
```

### After Completing a Plan

- **Update all affected docs.** `README.md` command table, example ledgers in `examples/`, any cross-references.
- **Mark the plan doc completed** by adding `**Status: Completed** (date)` at the top.

---

## Code Quality Standards

### Re-use Over Duplication

- Existing commands have conventions worth reusing (ledger schema, severity taxonomies, "raise-don't-fix" principle, YAML frontmatter config, per-invocation-form sections). Extend them; don't create parallel ones.
- Templates in `templates/` are the canonical schemas — modify there rather than re-specifying inline.

### Simplicity

- Write the simplest prompt / workflow that solves the problem.
- Avoid unnecessary abstractions in command files.
- Don't add features that aren't explicitly requested.

---

## Git Practices

### Before Committing

- **Always check and report the current branch.** Confirm with the user if the branch seems unexpected.

### Branching

- Major changes can use a feature branch; doc-only and minor fixes can go directly on `main`.

### Commit Messages

- **AI attribution is used in this repo.** Keep `Co-Authored-By: Claude ...` trailers on commits (consistent with existing history). This differs from the VISTA convention.
- **One theme per commit** where reasonable — split config, core-logic, and doc changes into separate commits.
- **One sentence per message**, concise and descriptive.

### Commit Frequency

- Commit frequently to maintain clean revert points.

---

## Communication Standards

### Ask Clarifying Questions For

- Functional requirements (what the command should do, what taxonomies to use).
- Ambiguous specifications.
- Decisions that significantly affect command semantics — invocation forms, defaults, artifact layout, severity cutoffs.
- **Fallback vs exception behavior.** Don't default to silent fallbacks — they can mask upstream errors. Ask explicitly.

### Use Your Judgement For

- Prompt wording and formatting style.
- Internal structure of a command file's sections.
- Standard refactors within a single command's prompt.

---

## Pre-Commit Review Agents

Spawn an implementation-review subagent before committing **non-minor** changes. Skip for:
- Single-file fixes (typo, small wording change, logo swap).
- Doc-only tweaks (README polish).
- Config/metadata changes.

### Implementation Review Agent

After finishing implementation, spawn a subagent to review all changes against the plan doc.

Prompt template:
```
IMPORTANT: Follow docs/claude_ops.md. Your job is read-only review.

Review all changes in this session against the plan doc at docs/plans/<plan>.md. Check:
1. Do changes match the plan spec?
2. Were claude_ops procedures followed (plan doc saved, thematic commits, docs updated)?
3. Any code quality issues (YAGNI violations, unnecessary complexity)?
4. Are README / examples / templates updated where affected?
Report issues with specific file:line references.
```

Note: no separate test-review agent for this repo — there is no test suite. Verification is "did you run the new/changed command against an example input and inspect the artifact?" The implementation review agent should check that the plan's Verification section was addressed.

---

## Slash Commands

This repo *is* slash commands. When adding a new one:

- Follow the existing `.claude/commands/*.md` style (directive "Do X" sentences, numbered steps, explicit "Do not" section, invocation-forms section up top).
- If the new command orchestrates existing ones, reuse their semantics (ledger schema, config frontmatter, fallback prompts) rather than re-specifying.
- If the new command introduces a config field, update `templates/claims_ledger.md` and `init-writing-tools.md`.

---

## Context Management

- **Fresh sessions for fresh tasks.** Start new sessions when switching to unrelated work.
- **Match rigor to stakes.** A new orchestrator command warrants a full plan; a logo swap doesn't.
