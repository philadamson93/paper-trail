---
name: plan-doc-readiness-check
description: Before committing a plan doc (new or substantially edited), check whether a fresh-agent in a future session has enough information to implement from it without conversation context. Surfaces missing codebase pointers, undefined integration points, schema-change details left as "TBD," and absent smoke-test criteria. Pauses for user sign-off before allowing commit. Invoke BEFORE commit-review on any plan-doc-bearing commit, or whenever finishing a planning conversation that produced a plan doc.
---

# plan-doc-readiness-check

Plan docs in `docs/plans/` are designed to outlive the conversation that produced them. A fresh-agent in a future session reads the plan doc and starts implementing; that agent has no memory of the brainstorm, no context for "what we decided versus what we considered." This skill is the check that the plan doc carries enough self-contained information to make that handoff work — and pauses to fix it before the doc lands if it does not.

## When to run

- **Before commit-review on any commit that creates or substantially modifies a plan doc** in `docs/plans/`. Typical timing: after the plan doc is drafted, before invoking commit-review.
- **At end of a planning conversation** that produced a plan doc, even if no commit is imminent — flag gaps so the user can decide whether to enrich now or later.
- **When updating an existing plan doc** with new sections — verify the new sections meet the same standard as the rest of the doc.

## Skip conditions

- The plan doc is itself meta-doc (e.g., a "decisions log" or "open questions" file that intentionally does not pin implementation details).
- The user has explicitly said to skip ("just commit the rough draft, we'll fix it later").
- The doc edit is a typo fix or pure prose-cleanup with no new content.

## Check procedure

For each plan doc being committed, read it fully and answer the following questions on behalf of a fresh agent. Any "no" or "unclear" is a gap to surface.

### 1. Codebase pointers

- Does the doc name the **specific files** the change touches? (e.g., `.claude/commands/paper-trail.md` line 315, not just "the orchestrator")
- Does the doc name the **convention or directory** for any new file it introduces? (e.g., "new slash command lives at `.claude/commands/issue.md` — see existing six commands for template")
- Does the doc point at **existing related code** the implementer should mirror or coordinate with? (e.g., "the existing `co_cite_context.sibling_citekeys` mechanism in `ground-claim.md` already provides sibling-extractor awareness")

### 2. Schema and interface changes

- If the doc proposes a schema change, does it name the **schema file** (`.claude/specs/verdict_schema.md`) and the **specific fields** being added or changed?
- If the doc proposes a new prompt or command, does it name the **file path** and any **template file** to model from?
- If the doc proposes an enum extension, does it list the **specific enum values**?
- Does the doc address **versioning impact** if the schema change is non-backward-compatible? (e.g., bump `schema_version` from "1.0" to "1.1"?)

### 3. Integration with existing patterns

- Does the doc explain how the change **interacts with the existing pipeline architecture** (orchestrator, dispatch prompts, subagents)?
- For features that touch multiple pipeline stages, does the doc name **all the stages** that need updating?
- Does the doc address **author-mode versus reader-mode** if the change affects both (or clarify it only affects one)?
- Does the doc address **interaction with other in-flight features** if any are coordinated? (e.g., "Feature 1 and Feature 2 both touch the orchestrator; coordinate during implementation")

### 4. Smoke-test and success criteria

- Does the doc say **how the implementer would know the feature works**? (canonical run, expected output, regression check)
- Does the doc point at a **canonical example or test fixture** the implementer should run against? (e.g., `examples/paper-trail-adamson-2025/` per memory `project_m1_complete.md`)
- Does the doc list **what should NOT change** as a regression check?

### 5. Open questions vs. decided design

- Does the doc clearly distinguish **decisions already made** from **questions left open for the implementer**?
- For open questions, does the doc give the implementer enough context to make a defensible call (or know to ask the user)?
- For decisions, does the doc include the **rationale** — at minimum a one-line "why" so the implementer can reason about edge cases that fall outside the decided scope?

### 6. Out-of-scope statement

- Does the doc have an explicit "Out of scope" section listing what is intentionally NOT in v1?
- This protects against scope creep and gives the implementer permission to defer items that look adjacent.

## Surface gaps and pause

If any check returns "no" or "unclear," list each gap with:

- **File and section** the gap is in
- **What's missing** (the specific question the doc fails to answer)
- **Suggested addition** (concrete prose or pointer the doc should have)

Then pause for user sign-off. The user picks: (a) add the suggested fixes now, (b) commit as-is and queue the fixes for next session, (c) the gap is intentional (e.g., a known open question being deferred).

## Common gap patterns and fix recipes

These are the patterns this skill is designed to catch — based on real misses observed in earlier plan-doc work.

### "We add a Pass-3 X" (no file pointer)

Plan says "add a Pass-3 joint adjudicator" without naming where the new dispatch prompt lives or which orchestrator file dispatches it. **Fix:** Name the new file path (e.g., `.claude/prompts/joint-adjudicator-dispatch.md`), list the orchestrator files that need to change to dispatch it (e.g., `.claude/commands/paper-trail.md`, `.claude/commands/ground-claim.md`).

### "New schema field Y" (no schema file)

Plan says "the schema needs a new `claim_source` field" without saying the schema lives at `.claude/specs/verdict_schema.md` or whether the change is additive (1.0 → 1.1) or breaking (1.0 → 2.0). **Fix:** Point at the schema file, specify field type and enum values, address backward-compatibility.

### "New slash command /Z" (no command convention)

Plan says "add `/issue` slash command" without saying slash commands live at `.claude/commands/<name>.md`, that there are six existing commands to model from (`paper-trail.md`, `ground-claim.md`, etc.), and which is the closest template. **Fix:** Name the file path and the closest sister command to model from.

### "Pre-step does X" (no pre-step exists)

Plan refers to "the claim-extractor pre-step" or "the orchestrator's parsing module" or other architectural-sounding components that do not actually exist as separate code units in this project. (Often the orchestrator IS the agent driven by a slash-command prompt; there is no separate Python pre-step.) **Fix:** Re-frame against the actual code structure — usually means naming the prompt file the orchestrator instructions live in.

### "When the feature is done" (no success criterion)

Plan describes the feature without saying how the implementer knows it works. **Fix:** Name a canonical run (e.g., a fixture under `examples/`), list the expected output, name what should not regress.

### "The orchestrator IS the agent" (Python plumbing missed)

Plan correctly notes that the orchestrator is driven by a slash-command prompt rather than a Python program, and concludes that prompt edits are the entire surface area. Wrong — the project also has Python validators, renderers, dispatch-payload schemas, and subagent-prompt slot lists that almost always need to change in lockstep with prompt edits. **Fix:** when a feature touches `.claude/commands/*.md`, also check whether it touches:
- **Validators** like `.claude/scripts/validate_claims.py` — invariants (e.g., `CITEKEY_MARKER_MISMATCH`, `TEXT_ANCHOR_MISSING`) may reject the new feature's outputs without an explicit relax-rule.
- **Renderers** like `.claude/scripts/render_html_demo.py` — UI-anchor logic (e.g., highlight-claim-sentence-in-PDF) may mis-render new claim shapes without explicit handling.
- **Dispatch payloads** declared as JSON inside `.claude/commands/paper-trail.md` (around line 396) — new fields the subagents need must be added here, not just to the schema.
- **Subagent prompt slot lists** in `.claude/prompts/<role>-dispatch.md` — `{{slot}}` placeholders must be added before the subagent can read the new field.

This is the most common gap pattern observed in real critic-agent reviews. Always check all four when reviewing a plan that touches the orchestrator.

## Project conventions to honor

- Plan docs in `docs/plans/` follow the project's "one topic per file" convention. The companion skill `doc-split-check` checks length and topical drift; this skill checks implementability. Both can run on the same commit.
- Cross-reference any related plan docs and journal entries so the implementer can trace the design history.
- If the plan doc already does the right thing — passes all six checks — say so explicitly and proceed to commit-review without modification. Don't add fluff for its own sake.

## Non-goals

- Don't rewrite the plan doc — propose specific additions and let the user approve them. The user wrote the plan; this skill is a checker, not an editor.
- Don't apply this to status / index docs (e.g., `NEXT.md`-style files) where the convention is brevity-with-pointers, not implementability.
- Don't apply this to milestone / read-only docs that capture frozen historical state.
