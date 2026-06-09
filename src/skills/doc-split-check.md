---
name: doc-split-check
description: Check whether a plan doc is growing too long or drifting across conceptually distinct topics. Invoke BEFORE adding substantial content (>50 lines) to an existing plan doc, WHEN editing a doc already >400 lines, WHEN the proposed addition covers a topic distinct from the doc's stated scope (e.g. adding eval-arm invocation mechanics to a doc titled "optimization-loop hygiene"), or AT end-of-session before commit-review as a final quality check. Flags docs that exceed the project convention and proposes split / compress / archive. Pauses for user sign-off before reorganizing.
---

# doc-split-check

Plan docs in this project follow "one topic per file." Project `CLAUDE.md` says: *"if a doc gets past ~400 lines of prose, split it."* This skill prompts the agent to pause and check whether an edit-in-progress is the right move vs a split-first move, so monolithic docs don't accrete silently.

## When to run

- **Before adding >50 lines of substantive content** to an existing plan doc — catches drift before it lands.
- **When an existing doc is already >400 lines** and you're about to edit it further — pre-emptively considers whether to split first.
- **When your proposed addition is on a topic distinct from the doc's title** (e.g. adding "eval-arm invocation mechanics" to a doc called "optimization-loop hygiene") — topic boundary, not line count, is the trigger.
- **At end-of-session before commit-review** — final quality check; flags any newly-ballooned docs for attention in the next session.

## Check procedure

1. **Scan line counts.** Run:
   ```bash
   wc -l docs/plans/*.md docs/journal/*.md 2>/dev/null | sort -n | tail -20
   ```
   Flag anything over 400 lines.

2. **Topical-cohesion check.** For each flagged doc:
   ```bash
   grep -n "^## \|^### " <flagged-doc>
   ```
   List the top-level sections. Are they conceptually one topic, or multiple? Signal of drift: section titles that would make sense as their own file (e.g. "Rule 3 — eval-time IN/OUT isolation" inside a "Operational hygiene" doc).

3. **For the doc currently being edited:** compare the proposed addition's topic to the doc's stated scope (title + opening paragraph). If distinct, propose split rather than append.

4. **Propose action per flagged doc.** Choose one:
   - **Keep as-is** — long but cohesive (e.g. `agentic-pipeline-optimization-framework.md` is deliberately the top-level reference; splitting hurts navigation).
   - **Split** — two or more topic-named files; move the distinct content; leave a short pointer-section in the original so readers coming in via old links aren't stranded.
   - **Compress / archive** — historical or resolved content moves to a milestone doc (pattern: `experiment-april-20-findings.md`, `tier-0-resolution-YYYY-MM-DD.md`, read-only); replace in the active doc with a short pointer.

5. **Pause for user sign-off.** Surface the proposal clearly. Don't split silently — file-layout changes need approval. User picks keep / split / compress / different-boundary.

## Typical actions — concrete recipes

### Split a doc on a topic boundary

1. Identify the section(s) that have grown beyond the doc's original scope.
2. Create a new topic-named file (`experiment-sarol-eval-arm-isolation.md`, not `hygiene-part-2.md` — name by topic not position).
3. Move the content block verbatim; add a short header to the new file identifying its relationship to the original ("companion to X", "split from Y on DATE").
4. In the original doc, leave a short pointer-section (2-4 lines) where the moved content used to live, referencing the new file.
5. Update the project's `CLAUDE.md` "Reading path for a fresh agent" section if the new file belongs on that path.

### Compress a resolved status block into a milestone doc

1. Identify a resolved / frozen narrative block (typically in `NEXT.md` or similar status-y docs).
2. Create a milestone doc with a dated filename (`tier-0-resolution-YYYY-MM-DD.md`, `experiment-april-20-findings.md` is the pattern).
3. Mark it read-only at the top: "Read-only milestone doc. Captures ... frozen at DATE."
4. Move the full narrative verbatim (preserve historical context; future readers may need it).
5. In the active doc, replace with a 3-5 line pointer to the milestone plus the "what's current" summary.

### Reference-integrity pass (MANDATORY after any split or compression)

After any file-layout change, grep for references that may now be broken:

```bash
grep -rn "<old-doc-name>\|§<old-section-name>" docs/ .claude/
```

Update each reference to point at the new location. Common places that accumulate cross-references:
- `NEXT.md` meta-task and reading-path sections
- `CLAUDE.md` "Reading path for a fresh agent"
- Other plan docs citing the split doc
- Journal entries citing the split doc (may or may not need updating; historical journal entries can stay pointing at the old doc name as long as it still exists as a pointer-stub)

## Project conventions to honor

- **Plan docs** in `docs/plans/` are stable reference plans, edit in place — but split when too big or when adding a distinct topic.
- **Journal entries** in `docs/journal/` are append-only per-day-per-topic — don't split these; if one is too long, the right move is typically that it was trying to cover too much, so create a sibling entry on the same date with a distinct topic slug (`YYYY-MM-DD-<topic-a>.md` + `YYYY-MM-DD-<topic-b>.md`).
- **Milestone docs** (`experiment-april-20-findings.md`, `tier-0-resolution-YYYY-MM-DD.md`, etc.) are read-only historical records; don't edit them except to add a "Superseded by" pointer at the top.
- The repo's `CLAUDE.md` has a "Reading path for a fresh agent" section. If a split affects a doc on that path, update the reading-path list too.

## Non-goals

- Don't apply this to very-long files that are deliberately monolithic (e.g. reference specifications, full benchmark runbooks). The trigger is *topic drift*, not length alone. 400 lines is the prompt to *check*, not to *split*.
- Don't split journal entries retroactively — they're history.
- Don't create "doc-split-YYYY-MM-DD.md" meta-docs about the split; the split itself is the artifact.

## When to skip

- The doc is intentionally the top-level reference for its subtree (plan docs like `agentic-pipeline-optimization-framework.md`).
- The long content is a single cohesive specification (e.g. `canary-runbook-vertex.md` is long because a runbook needs to be self-contained).
- You're mid-session and the split would de-rail the current task — note the issue in the commit message and address next session.
