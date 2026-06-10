Reference: docs/claude_ops.md

# Implementation Feedback: repo-organization

## Verdict

Revise before commit. The repo reorganization itself is in place, including `src/`, tracked symlinks, moved templates, tracked `paperclip/SKILL.md`, and the RD-9 author-mode redesign. The remaining issues are contract drift in `src/specs/control_flow.md` and exactness gaps in README/path-policy documentation.

## Plan Coverage

| Slice / section | Status | Evidence: path:line | Notes |
|---|---|---|---|
| New `src/` ship-surface layout | Done | `docs/SHIP_SURFACE.md:7` | `src/commands`, `src/prompts`, `src/specs`, `src/skills`, `src/scripts`, and `src/templates` are documented and present. |
| `.claude/<dir>` subdirectory symlinks | Done | `.claude/commands:1`, `.claude/prompts:1`, `.claude/specs:1`, `.claude/skills:1`, `.claude/scripts:1` | `git ls-files -s .claude/` shows all five entries as mode `120000`, targeting `../src/<dir>`. |
| `docs/SHIP_SURFACE.md` | Done | `docs/SHIP_SURFACE.md:1` | Short orientation doc, points at `src/`, explains `.claude/` as publication target. |
| Move commands/prompts/specs/scripts/skills/templates | Done | `CLAUDE.md:20`, `CLAUDE.md:25` | Canonical docs now point at `src/...`; top-level `templates/` is absent and `src/templates/claims_ledger.md` is tracked. |
| OQ-A paperclip tracking | Done | `CLAUDE.md:24` | `src/skills/paperclip/SKILL.md` is tracked and documented as directory-shaped. |
| OQ-B `.gitignore` shape | Done | `.gitignore:31` | Has `src/skills/*` plus the three carveouts at `.gitignore:32`, `.gitignore:33`, `.gitignore:34`. |
| RD-9 author-mode contract in command | Done | `src/commands/paper-trail.md:32` | Required absolute manuscript path, exact relative-path rejection message, `--output-dir`, validation-before-dispatch, and repo-root resolution all landed. |
| RD-9 README replacement of vendoring workflow | Partial | `README.md:65` | The vendoring copy commands are deleted and all three invocation patterns are present, but the required section name / exact error wording drifted; see Contract Violations. |
| OQ-D `{{spec_root}}` prompt contract | Partial | `src/commands/paper-trail.md:412`, `src/prompts/extractor-dispatch.md:58`, `src/prompts/adjudicator-dispatch.md:20` | `spec_root` is in the orchestrator payload and spec-reading dispatch prompts use `{{spec_root}}/src/specs/...`; `control_flow.md` slot map omits related dotted slots. |
| RD-2 path policy | Partial | `docs/claude_ops.md:44` | Shipped `src/` references are clean, but at least one non-exempt docs hit remains unannotated. |
| `src/specs/control_flow.md` pathway tables | Partial | `src/specs/control_flow.md:9`, `src/specs/control_flow.md:29`, `src/specs/control_flow.md:61` | Tables are present and use heading anchors, but validation cells are not Markdown links and the slot map misses actual placeholders. |
| Brevity audit implementation | Done | `src/commands/paper-trail.md:609`, `src/specs/trace_log.md:1`, `src/commands/paper-trail.md:672` | `wc -l` matches the plan results table; trace-log schema moved to `trace_log.md`; why-two-passes rationale moved to Provenance. |
| Smoke-test result recording | Done | `docs/plans/repo-organization.md:372`, `docs/plans/repo-organization.md:420` | Structural results are recorded; behavioral smokes are explicitly deferred to user-run Claude Code sessions. |

## Critical Drift

- None.

## Missing Pieces

- Plan item: dispatch slot map must match actual `{{slot}}` placeholders. Where it should land: `src/specs/control_flow.md:35`. Why it matters: the plan made `control_flow.md` the fresh-agent source of truth for orchestrator dispatch payloads. Suggested code change: add rows for `{{claim_type_hint.type}}` and `{{claim_type_hint.confidence}}`, sourced from payload `claim_type_hint.type` / `claim_type_hint.confidence`; both are used by extractor and adjudicator at `src/prompts/extractor-dispatch.md:20` and `src/prompts/adjudicator-dispatch.md:18`.
- Plan item: slot re-enumeration command must catch all placeholder shapes. Where it should land: `src/specs/control_flow.md:31`. Why it matters: the current command, `grep -o '{{[a-z_]*}}'`, misses dotted placeholders such as `{{claim_type_hint.type}}`. Suggested code change: replace it with a command equivalent to `grep -ho '{{[^}]*}}' src/prompts/*.md | sort -u` and explicitly document which generic tokens (`{{slot}}`, `{{...}}`) are examples, not fillable slots.

## Contract Violations

- Path-policy: the plan allows residual `.claude/` hits only when annotated as intentional/non-ship-surface. `docs/claude_ops.md:44` still says `~/.claude/plans/` with no annotation explaining that this is Claude Code's plan-mode storage path, not a shipped `.claude/` artifact. Required fix: annotate that literal in-place or rephrase to avoid matching the repo `.claude/` policy.
- Traceability/no-drift: `control_flow.md` says validation cells link to `src/specs/verdict_schema.md` Validation rules at `src/specs/control_flow.md:5`, but the table cells at `src/specs/control_flow.md:20` and `src/specs/control_flow.md:21` use plain prose (`per src/specs/verdict_schema.md § Validation rules`) instead of Markdown links to `src/specs/verdict_schema.md:179`. Required fix: make those cells actual links to `verdict_schema.md#validation-rules-orchestrator-enforced`.
- Traceability/no-drift: verifier validation reproduces enum details at `src/specs/control_flow.md:23` (`PASS`/`PARTIAL`/`FAIL`) instead of linking out. The plan explicitly says exit-validation cells must link rather than reproduce rules. Required fix: link to the verifier prompt output contract / handling section or to a dedicated spec if verifier result semantics become spec-owned.
- README RD-9 exactness: the plan asked for a README section named "Use paper-trail on an external manuscript"; the implementation uses `Author mode: audit your own in-progress manuscript` at `README.md:65`. Required fix: rename the section or confirm this heading deviation is intentional.
- README RD-9 exactness: the command contains the exact rejection message at `src/commands/paper-trail.md:42`, but README paraphrases it at `README.md:85`. Required fix: quote the same rejection string in README if the README is meant to carry the same contract verbatim.

## Test Gaps

- No missing structural smoke stands out beyond the documentation issues above. The plan's behavior smokes are recorded as deferred to user-run interactive Claude Code sessions at `docs/plans/repo-organization.md:429`; that deferral matches the plan's Implementation results and should not be re-flagged as missing.

## Defensible Deviations

- Author-mode default outputs include `<manuscript-dir>/claims_ledger.md` in README and the command at `README.md:85` and `src/commands/paper-trail.md:36`, while the plan's RD-9 shorthand emphasized `<manuscript-dir>/ledger/` and `<manuscript-dir>/demo.html`. This appears intentional and consistent with existing author-mode semantics (`src/commands/paper-trail.md:570`), but the author should confirm the public contract is "claims_ledger.md plus ledger/demo", not only ledger/demo.

## Suggested Code Edits

- `src/specs/control_flow.md:20` and `src/specs/control_flow.md:21` — replace plain schema references with Markdown links to `src/specs/verdict_schema.md#validation-rules-orchestrator-enforced`.
- `src/specs/control_flow.md:23` — replace inline verifier enum/rule prose with links to `src/prompts/verifier-dispatch.md` output/handling sections, or move verifier result semantics into a spec and link there.
- `src/specs/control_flow.md:31` — change the placeholder grep to `grep -ho '{{[^}]*}}' src/prompts/*.md | sort -u`, then list generic examples separately.
- `src/specs/control_flow.md:35` — add slot-map rows for `{{claim_type_hint.type}}` and `{{claim_type_hint.confidence}}` for extractor and adjudicator.
- `docs/claude_ops.md:44` — annotate `~/.claude/plans/` as Claude Code's user-local plan storage, not a repo ship-surface path.
- `README.md:65` — either rename the section to "Use paper-trail on an external manuscript" or note the deviation from the plan's exact wording.
- `README.md:85` — quote the command's exact relative-path rejection message if README is intended to carry the same contract.

## Questions For The Author

- Should author-mode's documented default output contract explicitly include `claims_ledger.md` alongside `ledger/` and `demo.html`, or should the plan/RD-9 wording be kept narrower?
- Should verifier result semantics move into a spec so `control_flow.md` can link to a stable section instead of linking to a dispatch prompt?

## Adjudication (2026-06-09, post-review)

- **Applied (agreed):** slot-map rows for `{{claim_type_hint.type}}` / `{{claim_type_hint.confidence}}`; re-enumeration grep fixed to `{{[^}]*}}`; validation cells converted to Markdown links; verifier enum reproduction removed from `control_flow.md`; `~/.claude/plans/` annotated in `docs/claude_ops.md`.
- **Applied (user sided with Codex):** verifier result semantics extracted to a new `src/specs/verifier_results.md` (contract of record); `verifier-dispatch.md` orchestrator notes, `paper-trail.md` § Handling results, and `control_flow.md` now point at it.
- **Dismissed (user sided with Claude):** README section keeps "Author mode: audit your own in-progress manuscript" (parallel Reader/Author structure beats the plan's literal heading); README keeps the paraphrased absolute-path explanation (verbatim rejection string stays single-sourced in the command to avoid drift).
- **Left open:** whether the documented author-mode default-output contract is `claims_ledger.md + ledger/ + demo.html` or RD-9's narrower `ledger/ + demo.html` — user undecided; implementation documents all three (matches actual behavior); to be settled empirically at the author-mode behavioral smoke.

## Audit Trail

- docs/claude_ops.md
- docs/plans/repo-organization.md
- .gitignore
- README.md
- CLAUDE.md
- docs/NEXT.md
- docs/SHIP_SURFACE.md
- docs/internals.md
- docs/output.md
- docs/plans/add-paper-trail-orchestrator.md
- docs/plans/author-mode-parity.md
- docs/plans/blindspot-mitigations.md
- docs/plans/feature-issue-command.md
- docs/plans/feature-multi-cite-joint-verdict.md
- docs/plans/feature-neighbor-claim-attribution.md
- docs/plans/feature-paperclip-first-architecture.md
- docs/plans/run-isolation-framework.md
- .claude/commands
- .claude/prompts
- .claude/scripts
- .claude/skills
- .claude/specs
- src/commands/fetch-paper.md
- src/commands/ground-claim.md
- src/commands/init-writing-tools.md
- src/commands/paper-trail-init.md
- src/commands/paper-trail.md
- src/commands/verify-bib.md
- src/prompts/adjudicator-dispatch.md
- src/prompts/extractor-dispatch.md
- src/prompts/verifier-dispatch.md
- src/scripts/ingest_pdf.py
- src/scripts/render_html_demo.py
- src/scripts/validate_claims.py
- src/skills/doc-split-check.md
- src/skills/paperclip/SKILL.md
- src/skills/plan-check.md
- src/specs/control_flow.md
- src/specs/ingest.md
- src/specs/trace_log.md
- src/specs/verdict_schema.md
- src/templates/claims_ledger.md
