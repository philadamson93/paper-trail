---
name: plan-check
description: paper-trail-specific extension of the user-level plan-check skill. Adds project-specific file paths, gap patterns observed in paper-trail's plan-doc history, and pointers to the project's actual code structure. Read after the global skill, not instead of it. TRIGGER right after a Write or Edit tool call that produces a plan doc in paper-trail's docs/plans/, BEFORE invoking commit-review.
---

# plan-check (paper-trail extension)

This is the paper-trail-specific extension of the user-level skill at `~/.claude/commands/plan-check.md`. The global skill carries the universal principle (a plan doc is a fresh-agent handoff; context must be POINTED-AT or STATED-DIRECTLY) and the universal six-category checklist. This file adds:

- paper-trail's actual file paths
- gap patterns observed in past plan-doc reviews on this project
- pointers to the project's actual code structure that mismatch fresh-agent assumptions

Read the global skill first. Apply the six universal checks. Then layer in the project-specific patterns below.

## paper-trail's actual ship surface

Fresh-agent gap patterns often stem from getting the project's structure wrong. The actual structure today (post-repo-org reshuffle, see `docs/plans/repo-organization.md`):

- **Slash commands** live at `src/commands/<name>.md` (mirrored to `.claude/commands/<name>.md` via subdirectory symlink). Six exist: `paper-trail.md`, `ground-claim.md`, `verify-bib.md`, `fetch-paper.md`, `init-writing-tools.md`, `paper-trail-init.md`.
- **Dispatch prompts** for subagents live at `src/prompts/<role>-dispatch.md`. Three roles: extractor, adjudicator, verifier.
- **Specs** live at `src/specs/`. `verdict_schema.md` is the verdict-envelope source of truth. `ingest.md` is the GROBID source-handle layout. `control_flow.md` (post-repo-org) is the orchestrator-to-dispatch-to-subagent-to-validator graph.
- **Python helpers** live at `src/scripts/`: `validate_claims.py`, `render_html_demo.py`, `ingest_pdf.py`.
- **Templates** live at `src/templates/`: `claims_ledger.md`.

If a feature plan refers to `.claude/commands/` instead of `src/commands/`, check whether the plan is post-repo-org (use `src/`) or pre-repo-org (use `.claude/`) and flag if mixed.

## paper-trail-specific gap patterns

These supplement the universal patterns in the global skill.

### "We add a Pass-N X" (no dispatch-prompt file pointer)

Plan says "add a Pass-3 joint adjudicator" without naming where the new dispatch prompt lives. paper-trail's convention: dispatch prompts at `src/prompts/<role>-dispatch.md`. **Fix:** Name the new dispatch prompt path (e.g., `src/prompts/joint-adjudicator-dispatch.md`); list the orchestrator files that need to change to dispatch it (e.g., `src/commands/paper-trail.md` Phase 3, `src/commands/ground-claim.md`).

### "Schema needs new field Y" (no schema file)

Plan says "the schema needs a new `claim_source` field" without saying the schema lives at `src/specs/verdict_schema.md` or addressing whether the change is additive (1.0 → 1.1) or breaking (1.0 → 2.0). **Fix:** POINT AT the schema file. STATE DIRECTLY the field type, any enum values, and the versioning bump.

### "New slash command /Z" (no command convention)

Plan says "add `/issue` slash command" without saying slash commands live at `src/commands/<name>.md` or naming the closest sister command to model from. **Fix:** Name the file path and the sister command — `paper-trail.md` for orchestrator-shaped commands, `verify-bib.md` for single-purpose Phase commands, `ground-claim.md` for per-item subworkflows.

### "Pre-step does X" (no Python pre-step)

Plan refers to "the claim-extractor pre-step" or "the orchestrator's parsing module" — components that don't exist as Python code. The orchestrator IS an agent driven by `src/commands/paper-trail.md`'s prompt. The claim-extractor work happens inline in Phase 3.1 of that prompt, not in a Python module. **Fix:** Re-frame against the actual structure — the change is in the orchestrator's prompt instructions, not in a separate Python module.

### "When the feature is done" (no fixture)

Plan describes the feature without naming the canonical fixture. paper-trail's convention: `examples/paper-trail-adamson-2025/` is the M1 reference run for reader mode (per memory `project_m1_complete.md`); `examples/DFD_authormode/` for author mode. **Fix:** Name the fixture, list the expected output (e.g., "87 claims with correct verdicts; diff against `examples/paper-trail-adamson-2025/data/claims/`"), name what should not regress.

### Cross-stage plumbing missed (paper-trail's four surfaces)

When a plan touches `src/commands/paper-trail.md` (the orchestrator), it almost always also touches:

- **Validators** at `src/scripts/validate_claims.py` — invariants like `CITEKEY_MARKER_MISMATCH` and `TEXT_ANCHOR_MISSING` may reject the new feature's outputs without an explicit relax-rule. Plan must say which validator rules need updating.
- **Renderers** at `src/scripts/render_html_demo.py` — UI-anchor logic (e.g., highlight-claim-sentence-in-PDF) may mis-render new claim shapes. Plan must say if a new render path is needed.
- **Dispatch payloads** in `src/commands/paper-trail.md` (around line 396, the per-claim dispatch JSON) — new fields the subagents need must be added here, not just to `verdict_schema.md`. Plan must list the dispatch-payload fields being added.
- **Subagent prompt slot lists** at `src/prompts/<role>-dispatch.md` — `{{slot}}` placeholders must be added before the subagent can read the new field. Plan must name which dispatch prompts get new slots.

This is the most common gap pattern observed in paper-trail's plan-doc reviews. Always check all four surfaces when reviewing a plan that touches the orchestrator.

### Reader-mode vs author-mode parity

paper-trail has two workflow modes (per CLAUDE.md and memory `project_author_vs_reader_user_shape.md`): reader mode audits someone else's PDF; author mode audits your own LaTeX manuscript. Many features apply to both; some apply to only one. Plan must say explicitly which modes are affected, or that the feature is mode-blind.

## Coordination with other paper-trail skills

- **`doc-split-check`** (project skill): checks plan-doc length and topical drift. Runs in parallel with this skill on the same commit. They are orthogonal — `doc-split-check` is about "is the doc the right shape," `plan-check` is about "is the doc implementable from."
- **`commit-review`** (user-level skill, project-shared): runs after this skill, before the actual commit. plan-check surfaces gaps; commit-review surfaces appropriateness concerns.

## What this extension does NOT replace

- The universal six-category check is in the global skill at `~/.claude/commands/plan-check.md`. This extension does not duplicate it.
- The principle (POINT AT vs STATE DIRECTLY) is in the global skill. This extension assumes it.
- Generic gap patterns (cross-stage plumbing as a concept) are in the global skill. This extension lists paper-trail's specific four surfaces.

If a fresh agent runs this extension without first reading the global skill, the result is incomplete. Always read both.
