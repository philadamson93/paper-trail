(Codex second-pass review)

Reference: docs/claude_ops.md

# Feedback: Agent-instruction-forward repo organization (Codex second-pass review)

## Verdict
Revise. Most prior findings are now correctly reflected in the plan, but the migration manifest is still wrong in a load-bearing way: the proposed POSIX ERE misses many `templates/` references while the plan says it should find them. A few verification steps also need tighter, executable pass/fail criteria before this is ready to hand to an implementer.

## Critical Gaps
- Severity: Critical | Gap: The “fixed” migration-manifest regex still does not work as described under POSIX ERE. `git grep -nE '\.claude/|(\b|/)templates/' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` returns only 12 `templates/` hits in this tree and misses real references in `README.md`, `CLAUDE.md`, `docs/claude_ops.md`, `.claude/commands/paper-trail.md`, and `.claude/commands/init-writing-tools.md`; a POSIX-safe boundary pattern like `(^|[^[:alnum:]_])templates/` returns 45. | Why it matters: the first implementation step is the canonical migration manifest; if it misses the template references, the repo-wide path migration can “pass” while leaving stale top-level `templates/` paths in shipped prompts and author-mode docs. | Evidence: docs/plans/repo-organization.md:88, docs/plans/repo-organization.md:258, docs/plans/repo-organization.md:281, README.md:67, CLAUDE.md:23, docs/claude_ops.md:92, .claude/commands/paper-trail.md:14, .claude/commands/init-writing-tools.md:49 | Required fix: replace `(\b|/)templates/` with a real POSIX ERE boundary, e.g. `(^|[^[:alnum:]_])templates/`, and update the expected count based on the command’s actual output after excluding frozen review/journal paths.

## Failure Modes
- Scenario: Implementer runs the plan’s manifest, sees nonzero `templates/` hits, and proceeds. | Why the plan misses it: the smoke gate only says “zero hits means broken,” but the current command returns nonzero while still missing the most important references. | What to add: assert both count and sentinel files: the manifest must include at least `README.md`, `CLAUDE.md`, `docs/claude_ops.md`, `.claude/commands/paper-trail.md`, and `.claude/commands/init-writing-tools.md`.
- Scenario: `control_flow.md` starts by copying the validation bullets from `verdict_schema.md`; later the schema changes and the cross-cut doc drifts. | Why the plan misses it: the No-drift constraint is correct, but the sample pathway table already restates the validation checklist instead of linking to it. | What to add: change the sample rows to “per `src/specs/verdict_schema.md` §Validation rules” and keep only role-specific deltas in `control_flow.md`.
- Scenario: The smoke suite says `/paper-trail` ran on `examples/paper-trail-adamson-2025/`, but the command was invoked interactively against an existing output directory or stale artifacts. | Why the plan misses it: the behavioral smoke names the fixture directory, not the concrete PDF input and expected fresh output location. | What to add: specify `/paper-trail examples/paper-trail-adamson-2025/input-paper.pdf --skip-preflight` or the exact approved invocation, plus a clean output directory and expected artifacts.

## Contract Checks
- In-repo path contract: verified the plan now covers `README.md`, `CLAUDE.md`, `.gitignore`, docs, shipped prompts/specs/scripts, and both `templates/` and `.claude/` sweeps. The remaining blocker is the regex itself.
- Skill contract: verified `paperclip/SKILL.md` is currently untracked and ignored by `.gitignore:25`; the plan correctly elevates this as OQ-A instead of silently shipping it.
- Validation contract: verified `validate_claims.py` is a pre-dispatch manuscript validator, not an exit-schema validator; the plan’s “Where validation actually lives” note is correct against .claude/scripts/validate_claims.py:3 and .claude/specs/verdict_schema.md:179.
- Cross-repo author-mode contract: local-copy-only is mostly specified by RD-1 plus the readlink smoke. Commit-and-distribute is not fully specified; OQ-C should require either “out of scope / user owns `core.symlinks` risk” or a concrete non-symlink distribution path.

## Modularity vs. YAGNI
- Decision point: RD-4 symlinks first with fallback. | Plan's current choice: appropriate; it preserves the repo’s no-build-step assumption unless a measured failure forces a sync step. | Modular alternative + realistic use case: go straight to `make sync` for portability across symlink-hostile environments. | Recommendation: keep RD-4, but make the fallback patch concrete enough to apply, including `docs/claude_ops.md` and the exact sync-state check.
- Decision point: RD-5 brevity audit. | Plan's current choice: content-driven audit for the 698-line orchestrator only. | Modular alternative + realistic use case: audit every prompt now. | Recommendation: keep current choice; smaller dispatch prompts are close to 100 lines but not the source of the current context problem.
- Decision point: `src/specs/control_flow.md`. | Plan's current choice: useful cross-cut graph. | Modular alternative + realistic use case: rely on `verdict_schema.md` and orchestrator headings only. | Recommendation: keep the new doc only as consolidation and cross-reference; remove validation-rule restatements from the sample rows.

## Verification Gaps
- The manifest sanity check must fail on incomplete nonzero output, not only zero output.
- “Per-command coverage” is too hand-wavy: `/ground-claim and any other slash command` should list all six commands and define whether each must only discover, run a harmless preflight, or complete a real fixture workflow.
- The author-mode vendoring smoke should name `examples/DFD_authormode/main.tex` or another concrete fixture, not just “a small `.tex` fixture.”
- The plan’s Markdown and visual companion are drifting: `docs/plans/repo-organization.html` still contains older RD-1/RD-2/manifest wording that conflicts with the Markdown plan. If the HTML companion remains part of the plan surface, regeneration or an explicit “do not trust generated companion” note is needed.

## Suggested Revisions
- Replace every occurrence of `(\b|/)templates/` in the manifest command with `(^|[^[:alnum:]_])templates/`, then recalibrate the expected hit count.
- Add sentinel-file assertions to the manifest gate.
- In the `control_flow.md` sample table, replace copied validation bullets with links to `src/specs/verdict_schema.md` §Validation rules.
- Make the smoke suite executable: concrete command invocation, fixture path, output directory, and expected artifact for each behavioral check.
- Add a branch-specific OQ-C acceptance criterion: local-copy-only is documented as the contract, or commit-and-distribute gets a concrete portability design.

## Questions For The Author
- For OQ-C, is commit-and-distribute explicitly out of scope for v1, or does the implementation need to support collaborators cloning vendored writing repos with symlinks intact?
- Should `docs/plans/repo-organization.html` be regenerated as part of this plan, or treated as non-authoritative historical/visual material?

## Audit Trail
- docs/claude_ops.md
- docs/plans/repo-organization.md
- docs/plans/repo-organization.html
- docs/plans/reviews/repo-organization-feedback.md
- docs/plans/reviews/repo-organization-feedback-claude.md
- README.md
- CLAUDE.md
- .gitignore
- docs/NEXT.md
- docs/internals.md
- docs/output.md
- docs/plans/run-isolation-framework.md
- .claude/commands/paper-trail.md
- .claude/commands/ground-claim.md
- .claude/commands/init-writing-tools.md
- .claude/prompts/extractor-dispatch.md
- .claude/prompts/adjudicator-dispatch.md
- .claude/prompts/verifier-dispatch.md
- .claude/specs/verdict_schema.md
- .claude/specs/ingest.md
- .claude/scripts/validate_claims.py
- .claude/skills/doc-split-check.md
- .claude/skills/plan-check.md
- .claude/skills/paperclip/SKILL.md
- examples/paper-trail-adamson-2025/
- examples/DFD_authormode/
