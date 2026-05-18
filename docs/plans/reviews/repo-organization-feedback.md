Reference: docs/claude_ops.md

# Feedback: Plan — agent-instruction-forward repo organization

## Verdict
Revise. The core goal is reasonable, but the plan’s biggest deliverable currently models the dispatch/validation graph incorrectly, and the symlink layout breaks the documented author-mode vendoring workflow unless the packaging contract is redesigned explicitly.

## Critical Gaps
- Critical | The proposed `control_flow.md` source of truth is anchored to the wrong phases and to nonexistent validator APIs. The sample rows point at the dispatch payload JSON, ledger rendering, and HTML render phase instead of the actual extractor/adjudicator/verifier dispatch sites, and `validate_claims.py` is the pre-dispatch manuscript validator rather than an exit-schema validator. If implemented as written, the plan’s flagship deliverable will encode a false contract for future agents. | Evidence: docs/plans/repo-organization.md:95-125, .claude/commands/paper-trail.md:394-411, .claude/commands/paper-trail.md:430-445, .claude/commands/paper-trail.md:456-468, .claude/commands/paper-trail.md:507-515, .claude/scripts/validate_claims.py:3-23, .claude/specs/verdict_schema.md:179-193 | Required fix: rewrite the `control_flow.md` scope around the real stages: pre-dispatch `validate_claims.py`, actual extractor/adjudicator/verifier dispatch points, and the schema-validation rules that gate each emitted artifact.
- Critical | The symlink design breaks the documented author-mode distribution contract. The README currently tells users to copy only `.claude/` and `templates/` into a writing project; after `.claude/*` becomes symlinks into `src/`, that copy is no longer self-contained. I verified locally that `cp -R` preserves the symlink and leaves `.claude/commands` dangling unless `src/` is copied alongside. | Evidence: docs/plans/repo-organization.md:38-66, README.md:67-81 | Required fix: add an explicit packaging/export decision and validation step for author mode: either vendor-copy `src/` with `.claude/`, materialize `.claude/` during export, or keep `.claude/` canonical for vendoring.
- Critical | The move spec does not cover the existing nested `paperclip` skill, so the promised `src/skills` mirror is incomplete on day one. The plan only moves `.claude/skills/*.md`, but the repo also ships `.claude/skills/paperclip/SKILL.md`, and the companion paperclip-first plan depends on that skill. | Evidence: docs/plans/repo-organization.md:29-35, docs/plans/repo-organization.md:57-64, .claude/skills/paperclip/SKILL.md:1-10, docs/plans/feature-paperclip-first-architecture.md:43-45 | Required fix: change the inventory from `*.md` globs to the actual `.claude/skills/` tree, preserve both single-file and directory-based skills under `src/skills/`, and include both in discovery tests.
- Gap | The touched-file inventory is materially incomplete. It names `CLAUDE.md` and several plan docs, but omits user-facing docs that hardcode the old layout or the old vendoring workflow, including the README, internals doc, and output doc. Leaving those stale would ship contradictory instructions immediately after the reorg. | Evidence: docs/plans/repo-organization.md:68-76, docs/claude_ops.md:82-83, README.md:67-81, docs/internals.md:9-26, docs/output.md:7-17 | Required fix: replace the hand-picked update list with a repo-wide grep-driven manifest and explicitly include README.md, docs/internals.md, docs/output.md, and any other cross-references that resolve to moved paths or changed packaging instructions.
- Gap | The plan’s “codebase pointers” section sends the implementer to the wrong files. It predicts `.claude/` path literals in `validate_claims.py` and `render_html_demo.py`, but those scripts currently do not contain them; the real hardcoded paths live in prompt/spec/command Markdown files. That mismatch makes the implementation checklist unreliable. | Evidence: docs/plans/repo-organization.md:177-181, .claude/scripts/validate_claims.py:186-205, .claude/scripts/render_html_demo.py:144-163, .claude/specs/ingest.md:65-70, .claude/prompts/extractor-dispatch.md:58-65, .claude/prompts/adjudicator-dispatch.md:20-21, .claude/prompts/adjudicator-dispatch.md:75-80, .claude/commands/paper-trail.md:301-301, .claude/commands/paper-trail.md:352-360, .claude/commands/paper-trail.md:383-411, .claude/commands/paper-trail.md:512-512 | Required fix: replace the speculative script checklist with explicit grep results and decide whether shipped prompt/spec prose should keep runtime `.claude/...` paths or migrate to canonical `src/...` references.
- Gap | The plan doc itself does not follow the repo’s required plan header/shape, which weakens its role as a future-session handoff. `docs/claude_ops.md` requires the `Reference:` header and a standard Goal/Approach/Files/Open Questions/Verification scaffold. | Evidence: docs/plans/repo-organization.md:1-5, docs/claude_ops.md:34-39, docs/claude_ops.md:57-78 | Required fix: add the required `Reference: docs/claude_ops.md` header and normalize the top-level scaffold so the key implementation and verification sections are easy to scan.

## Failure Modes
- A user follows the current README and vendor-copies only `.claude/` and `templates/` into a writing repo | The plan verifies slash-command discovery only inside this repo, not the cross-repo packaging workflow | Add a clean temp-project vendoring smoke test and rewrite README/install guidance around the chosen export model.
- Small prompt edits shift line numbers in `paper-trail.md` | The plan wants `control_flow.md` to pin exact line numbers aggressively, but gives no drift-management strategy | Add either a regeneration/check procedure or reduce the pinning to stable section anchors plus grep cues.
- Symlink discovery works in-repo, then later falls back to `make sync` | That creates two writable surfaces (`src/` and `.claude/`) while `docs/claude_ops.md` still says the repo has no build step | Add a documented single-writer policy and an explicit docs update if the sync fallback is ever chosen.

## Contract Checks
- Slash-command discovery contract: `.claude/commands/<name>.md` must still resolve for Claude Code after clone, after vendoring into another repo, and after branch checkout.
- Skill discovery contract: both single-file skills and directory-based skills like `.claude/skills/paperclip/SKILL.md` need explicit coverage.
- Output-layout compatibility contract: `validate_claims.py` and `render_html_demo.py` currently auto-detect both `ledger/claims/` and legacy `data/claims/`; the reorg should state that fixture compatibility remains unchanged.
- Path-policy contract: decide whether shipped prompt/spec prose keeps runtime `.claude/...` paths or migrates fully to canonical `src/...` paths. Mixed guidance will confuse both humans and subagents.
- Author-mode packaging contract: README vendoring instructions are effectively a cross-repo API surface and need first-class treatment.

## Verification Gaps
- Missing clean temp-project test of the README vendoring workflow with symlinked `.claude/`.
- Missing repo-wide grep/link check proving no stale `.claude/` or `templates/claims_ledger.md` references remain where canonical `src` paths are intended.
- Missing discovery test for the nested `paperclip` skill in addition to `doc-split-check` and `plan-check`.
- Missing explicit validation for the sync-script fallback path even though it changes the repo’s “no build step” assumption in `docs/claude_ops.md`.

## Suggested Revisions
- Replace the illustrative `control_flow.md` table with a corrected draft based on the current repo: real dispatch/send points, real artifact outputs, and real validation owners.
- Expand `Files to update` into a grep-backed manifest rather than a hand-curated list; include README.md, docs/internals.md, docs/output.md, and any shipped prompts/specs whose prose embeds moved paths.
- Add a dedicated `Author-mode packaging / vendoring` section that states exactly what gets copied into external writing repos after the reorg.
- Treat `skills/` as directories-or-files, not `*.md`, and include `paperclip` explicitly in both move rules and smoke tests.
- Add the required `Reference: docs/claude_ops.md` header and a short canonical Goal/Approach/Verification scaffold at the top of the plan.

## Questions For The Author
- Is repo-org intended to preserve the current “copy pieces of paper-trail into another writing repo” workflow, or is author mode becoming contributor-only from this repo?
- Should runtime prompts/specs continue to reference `.claude/...` paths for execution ergonomics, or should every shipped reference move to `src/...` even though `.claude` symlinks keep working?
- Is `paperclip` intentionally part of the mirrored ship surface under `src/skills/paperclip/`, or should it remain outside this reorg’s scope?

## Audit Trail
- docs/claude_ops.md
- docs/plans/repo-organization.md
- CLAUDE.md
- .gitignore
- README.md
- docs/internals.md
- docs/output.md
- docs/NEXT.md
- .claude/commands/paper-trail.md
- .claude/commands/ground-claim.md
- .claude/commands/init-writing-tools.md
- .claude/prompts/extractor-dispatch.md
- .claude/prompts/adjudicator-dispatch.md
- .claude/prompts/verifier-dispatch.md
- .claude/specs/verdict_schema.md
- .claude/specs/ingest.md
- .claude/scripts/validate_claims.py
- .claude/scripts/render_html_demo.py
- .claude/skills/plan-check.md
- .claude/skills/paperclip/SKILL.md
- docs/plans/feature-paperclip-first-architecture.md
