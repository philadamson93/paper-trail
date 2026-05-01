# Plan — agent-instruction-forward repo organization

**Status.** Plan-only. No code yet. Companion to `docs/plans/feature-paperclip-first-architecture.md` (which assumes the present `.claude/` layout) and `docs/plans/run-isolation-framework.md` (the next plan doc, which will lean on this one's ship-surface map).

**Provenance.** Scoped 2026-05-01 immediately after the paperclip-first commit. Decision-log entry is the same day's `docs/journal/2026-05-01-paperclip-coverage-revisit.md` end section (to be appended).

---

## Headline rationale

paper-trail is **agent-instruction-forward**: the shipped product is mostly Markdown prompts (slash commands plus dispatch templates plus skills plus specs), with Python only where Markdown is genuinely the wrong tool (validators, renderers, GROBID ingest). Today these artifacts all sit under `.claude/` because that is what Claude Code requires for slash-command and skill discovery. A casual reader of the GitHub repo cannot see at a glance "this is what ships."

The user goal: a top-level `src/` directory that mirrors `.claude/` so that anyone browsing the repo can see the ship surface. Plus a single source of truth that maps the dispatch graph (which orchestrator phase calls which dispatch prompt, which subagent emits which schema field, which validator runs on which exit shape) so a fresh agent picking up a feature plan can trace pathways without re-reading every prompt. Plus a light audit of existing prompts to catch obvious "this section is human-orientation-only, move it to a spec" cases that bloat subagent context.

The user-stated principles this plan honors:

- **Modularity** over monolith. One topic per file. Already a project convention (per `doc-split-check`); applies symmetrically to ship-surface artifacts.
- **Limited-context, need-to-know information delivery.** Subagents see the dispatch prompt plus its slot fills, not the orchestrator's full 698-line context. Brevity in prompts is a context-budget concern, not just an aesthetic one.
- **Default to agent instructions over code.** Write Python only when Markdown is genuinely the wrong tool. Validation rules, schema rendering, PDF parsing — Python. Phase orchestration, subagent dispatch, decision rubrics — Markdown.
- **Validate via real-workflow testing.** Don't pre-optimize prompt brevity or layout choices that haven't shown up as a problem in a real run. The plan calls out one round of obvious wins now and explicitly defers deeper optimization to post-shipping observation.

---

## Implementation surface

**New directory layout.** Top-level `src/` becomes the canonical home for ship-surface artifacts:

```
src/
├── commands/        ← slash command prompts (mirrors .claude/commands/)
├── prompts/         ← dispatch prompts subagents receive
├── specs/           ← interface specs (verdict_schema.md, ingest.md, control_flow.md)
├── skills/          ← project-owned skills
├── scripts/         ← Python helpers
└── templates/       ← templates (currently top-level templates/, moves under src/)
```

**`.claude/` remains** but its content-bearing subdirectories become symlinks into `src/`:

```
.claude/
├── commands/        → src/commands/        (symlink)
├── prompts/         → src/prompts/         (symlink)
├── specs/           → src/specs/           (symlink)
├── skills/          → src/skills/          (symlink)
├── scripts/         → src/scripts/         (symlink)
└── settings.local.json   ← stays canonical at .claude/ root (Claude-Code-required, not part of the ship surface)
```

Rationale: Claude Code's discovery rules require slash commands at `.claude/commands/<name>.md` and project-owned skills at `.claude/skills/<name>.md`. The directories cannot move. But the *files* the directories contain can live elsewhere on disk; `.claude/<dir>/` becomes a directory-level symlink to `src/<dir>/`. macOS and Linux both follow symlinks for these reads transparently. Windows support is out of scope for v1 (none of paper-trail's tooling requires Windows today).

**Files to create:**

- `src/specs/control_flow.md` — single source of truth for the orchestrator → dispatch → subagent → validator graph. See "Traceability" section below for content.
- `docs/SHIP_SURFACE.md` — short repo-browser-facing doc explaining "this is what ships" and pointing at `src/`. Lives in `docs/`, not `src/`, because it documents the surface for humans, not for agents.

**Files to move (preserve git history with `git mv`):**

- `.claude/commands/*.md` → `src/commands/*.md`
- `.claude/prompts/*.md` → `src/prompts/*.md`
- `.claude/specs/*.md` → `src/specs/*.md`
- `.claude/skills/*.md` → `src/skills/*.md`
- `.claude/scripts/*.py` → `src/scripts/*.py`
- `templates/*.md` → `src/templates/*.md`

After the move, run `ln -s` to create the `.claude/` symlinks. Test that Claude Code still finds slash commands and skills via the symlink path.

**Files to update (for the cross-reference to `src/` paths):**

- `CLAUDE.md` — the "Where things live" section currently pins `.claude/<dir>/<file>` paths. Update to `src/<dir>/<file>` with a one-line note that `.claude/<dir>/` is a symlink. Keeps the document pointing at the canonical home.
- `.gitignore` — currently has `.claude/skills/*` plus a `!.claude/skills/<name>.md` carveout per skill. After the move, the canonical home is `src/skills/`, which doesn't need that carveout. Remove the `.claude/skills/*` ignore line and its carveouts (the symlink target lives in `src/` which is fully tracked). Verify the existing gitignored items (`/experiments/`, `.env`, GCP credentials, `pdfs/`) remain.
- `docs/plans/feature-paperclip-first-architecture.md` — references `.claude/<dir>/<file>` paths throughout. Update each reference to `src/<dir>/<file>`. (Cross-plan coordination cost; one of the reasons to land repo-org before paperclip-first implementation begins.)
- `docs/plans/feature-multi-cite-joint-verdict.md`, `docs/plans/feature-neighbor-claim-attribution.md`, `docs/plans/feature-issue-command.md` — same path-reference update pattern.
- `docs/plans/add-paper-trail-orchestrator.md`, `docs/plans/author-mode-parity.md`, `docs/plans/blindspot-mitigations.md` — same.
- `docs/plans/paper-trail-product-backlog.md` — same.
- `templates/claims_ledger.md` references — search for any file that references `templates/<file>` and update to `src/templates/<file>`.

**Naming and shape pins:**

- `src/` is the canonical home. `.claude/` is a publication target. If the symlinks ever break, regenerate from `src/`; never edit through `.claude/`.
- `src/specs/control_flow.md` filename: keep underscored-snake to match `verdict_schema.md` and `ingest.md`. Resists the temptation to call it `control-flow.md` for hyphen consistency with other docs — schema-and-spec files in this project use snake.
- `docs/SHIP_SURFACE.md`: caps because it's a repo-root-level orientation doc analogous to `README.md` or `CONTRIBUTING.md`. (Per memory `feedback_short_headline_copy.md`, this doc's headline copy should be 1-2 sentences max and workshopped before commit.)

**Pinned design decisions:**

- **Symlinks at the subdirectory level**, not at file level. One symlink per content-bearing subdirectory (`.claude/commands/` → `src/commands/`). Avoids the brittleness of per-file symlinks and keeps the directory listing legible if a fresh agent looks under `.claude/` directly.
- **`src/` is fully gitignore-clean and tracked.** No build step, no generated files — what's checked in IS the ship surface. The symlinks are tracked too (git stores them as symlinks, recreates on clone).
- **No `templates/` at top level after the move.** Moves to `src/templates/`. Reduces top-level directory count and groups templates with the rest of the ship surface. CLAUDE.md update reflects this.
- **CLAUDE.md and docs/journal/ stay top-level.** They are dev-and-product-docs scaffolding, not ship surface. The `docs/` directory is correctly named for human-facing documentation.
- **No back-compat for old `.claude/`-direct path references.** Per memory `feedback_rework_for_quality.md`, refactor cleanly. Plan-doc references update in lockstep with the move.
- **Recognized non-shipped top-level directories** post-move: `docs/` (human-facing documentation), `examples/` (canonical fixture runs), `experiments/` (gitignored scratch — sarol-leftovers and probe artifacts), `dev/` (engineering tooling for validating the ship surface — see `docs/plans/run-isolation-framework.md`). The naming choice `dev/` rather than `tools/` reflects that "paper-trail" itself is the tool; calling something else "tools/" would be confusing for a repo-browser. `dev/` reads as "engineer ergonomics, not the product."

---

## Traceability — `src/specs/control_flow.md`

The single largest deliverable of this plan. Today there is no map of which orchestrator phase dispatches which subagent, which dispatch prompt reads which `{{slot}}` from which orchestrator dispatch payload, which subagent emits which `verdict_schema.md` field, which validator runs against which exit shape. A fresh agent reads `paper-trail.md` (698 lines) and infers the graph; a less-fresh agent forgets. Both shapes are bug-prone.

`control_flow.md` is structured as a series of named pathway-tables. Each row is a single hop in the agent graph:

**Pathway: orchestrator → dispatch prompt**

| Phase | Orchestrator file (line) | Dispatch prompt | Schema fields populated | Validator |
|---|---|---|---|---|
| Phase 3 — Pass 1 (extractor) | `src/commands/paper-trail.md:396` | `src/prompts/extractor-dispatch.md` | `evidence`, `co_cite_context.sibling_citekeys`, `attestation` | `validate_claims.py::EVIDENCE_SHAPE` |
| Phase 3 — Pass 2 (adjudicator) | `src/commands/paper-trail.md:430` | `src/prompts/adjudicator-dispatch.md` | `verdict`, `claim_type`, `remediation`, `flag` | `validate_claims.py::VERDICT_SHAPE` |
| Phase 3.5 — verifier | `src/commands/paper-trail.md:507` | `src/prompts/verifier-dispatch.md` | `verifier_pass`, `verifier_re_grep_match` | `validate_claims.py::VERIFIER_SHAPE` |

**Pathway: dispatch slot map**

| Dispatch prompt | Slot | Source field on orchestrator dispatch JSON | Notes |
|---|---|---|---|
| `extractor-dispatch.md` | `{{claim_id}}` | per-claim record `claim_id` | |
| `extractor-dispatch.md` | `{{co_citekeys}}` | per-claim record `co_citekeys` (flat array) | extractor populates `sibling_citekeys` |
| `extractor-dispatch.md` | `{{handle}}` | per-claim record `handle` | local PDF dir for PDF mode; will become `paperclip_handle` for paperclip mode after `feature-paperclip-first-architecture.md` lands |
| ... | ... | ... | ... |

**Pathway: skill auto-load triggers**

| Skill file | Trigger condition | Used by |
|---|---|---|
| `src/skills/doc-split-check.md` | doc edit ≥ 400 lines | manual + commit-review |
| `src/skills/plan-doc-readiness-check.md` | new or substantially-edited plan doc in `docs/plans/` | manual + commit-review |

The exact line numbers are pinned in `control_flow.md` and updated when the orchestrator changes. The validator names are pinned to specific functions in `src/scripts/validate_claims.py`. Updates to `control_flow.md` are part of any feature plan that touches the dispatch graph (this becomes a check item in `plan-doc-readiness-check.md`).

---

## Brevity audit — light pass

Existing prompt lengths:

- `paper-trail.md`: 698 lines (the orchestrator)
- `ground-claim.md`: 172 lines (per-claim workflow doc, called from `paper-trail.md`)
- `verify-bib.md`: 121 lines
- `paper-trail-init.md`: 146 lines
- `init-writing-tools.md`: 87 lines
- `fetch-paper.md`: 70 lines
- `extractor-dispatch.md`: 87 lines
- `adjudicator-dispatch.md`: 102 lines
- `verifier-dispatch.md`: 90 lines

The light audit looks for two specific patterns:

1. **Reference material that duplicates a spec.** If `paper-trail.md` includes a 50-line block explaining the verdict schema, that block can collapse to a 1-line pointer to `src/specs/verdict_schema.md`. The orchestrator agent reads the spec on-demand via the pointer; the schema isn't loaded into context every turn.
2. **Human-orientation-only content.** "This phase exists because of the April reversal..." kind of context. Useful for a code reviewer; not load-bearing for the agent at dispatch time. Move to a Provenance section at the bottom or to a journal entry.

Out of scope for this audit:

- Deciding whether a `{{slot}}` is underspecified. That's a real-workflow-testing concern.
- Rewriting prompt prose for terseness. The audit removes content; it does not rewrite content.
- Touching the dispatch-prompt slot lists. Those changes come with their feature plans, not here.

Audit deliverable: a per-prompt before/after line count plus a one-paragraph summary in this plan's "Smoke test results" section after the audit runs. No further commitments — the deeper "is this prompt actually optimal" question goes to post-shipping testing per the user's stated principle.

---

## Decision policy: instructions vs code

A heuristic for future feature plans, captured here so the principle is visible:

1. **First consider:** can this be a slash command, a dispatch prompt slot, a skill, or a spec field?
2. **Fallback:** Python helper in `src/scripts/`. Only when:
   - The work is genuinely non-Markdown — file parsing (GROBID), HTML rendering, JSON validation
   - Or the work is a determinism guarantee — same input must produce identical output (validators, schema checks)
   - Or the work is performance-bound — searching across many local files, batch operations
3. **Never:** write Python plumbing that wraps a Markdown task. If a feature can be specified as a prompt edit, it should be.

Future feature plans should explicitly state which choice they made and why. Plan-doc-readiness-check should add a check for this rationale on plans that introduce code.

---

## Codebase pointers for fresh agents

When picking up this plan and starting implementation:

- **CLAUDE.md** — contains the current "Where things live" pointer list and reading-path. The single largest single-file update.
- **`.gitignore`** — currently has `.claude/skills/*` plus per-skill carveouts (added in commit `dffb0b1`). The carveout pattern goes away after the move.
- **All plan docs in `docs/plans/`** — each contains hardcoded `.claude/<dir>/<file>` path references that need updating in lockstep. Use `git grep -l "\.claude/"` to find them all before the move.
- **All scripts in `src/scripts/`** (post-move) — check whether any Python file hardcodes a `.claude/<dir>/<file>` path. `validate_claims.py` and `render_html_demo.py` likely both do. Use `grep -rn '\.claude/' src/scripts/` after the move.
- **`templates/claims_ledger.md`** — moves to `src/templates/claims_ledger.md`. Check whether `paper-trail.md` references the template path and update.

---

## Smoke test plan

The plan succeeds if a fresh agent in a future session can:

1. Open the repo on GitHub, click on `src/`, and see the ship-surface layout in one view.
2. Read `src/specs/control_flow.md` and explain in their own words: "Phase 3 dispatches the extractor at line N of `src/commands/paper-trail.md` using `src/prompts/extractor-dispatch.md`; the extractor populates the `evidence` field; the adjudicator reads the evidence and emits a verdict; `src/scripts/validate_claims.py::VERDICT_SHAPE` checks the verdict."
3. Pick up `docs/plans/feature-paperclip-first-architecture.md` and identify all the files they need to edit using only `src/` paths.
4. Run `/paper-trail` end-to-end on `examples/paper-trail-adamson-2025/` and confirm Claude Code still finds the slash command via the `.claude/commands/` symlink.

Specific verification steps:

- Run `/paper-trail` after the symlink rewire. If Claude Code can't find the slash command, the symlink approach is wrong and we need to escalate to one of the open-question alternatives (build script or gitignored `.claude/`).
- Run `/ground-claim` and any other slash command from the new location. Same check.
- Run a project-owned skill (`doc-split-check`, `plan-doc-readiness-check`). Same check.
- `git log --follow src/commands/paper-trail.md` should show full history back through the `.claude/commands/paper-trail.md` era. (`git mv` preserves history.)
- `git status` shows no spurious diffs from the symlink wiring.

---

## Open questions

1. **Sync mechanism: symlinks vs gitignored-and-built `.claude/` vs sync script.** Default in this plan is subdirectory-level symlinks, but the alternatives are real. Test the default during implementation; if any of the `.claude/<dir>/` symlinks break Claude Code's discovery, fall back to: (a) gitignore `.claude/<dir>/` and have a `make sync` step that copies `src/<dir>/*` into `.claude/<dir>/` before Claude Code sessions, or (b) keep `.claude/` as the canonical home and skip the `src/` mirror entirely (the original "Recommended" option I had presented). Decision: try symlinks first; back off only if measurable breakage.
2. **Per-prompt brevity audit threshold.** Should the audit be content-driven (move all reference material to specs regardless of line count) or threshold-driven (only audit prompts > 200 lines)? Default to content-driven on the 698-line `paper-trail.md` and threshold-driven (skip) on prompts < 100 lines. Revisit after one round.
3. **`templates/` move depth.** Currently the top-level `templates/` directory has only `claims_ledger.md`. After moving to `src/templates/`, is the directory worth keeping for one file? Default: yes, in case more templates emerge (the `feature-issue-command.md` plan implies an `issue-draft.json` template might want to live here).
4. **Should `docs/SHIP_SURFACE.md` be a README pointer or a full doc?** The user said "instructions contain what is needed, not extremely long documentation." Default to a short doc (one screenful, ~50 lines) that points at `src/specs/control_flow.md` for the actual map. Workshop the headline copy per memory `feedback_short_headline_copy.md`.
5. **Coordinate with the in-flight `feature/paperclip-primary-workflow` and `feature/multi-cite-and-neighbor-claims` branches.** Both reference `.claude/<dir>/<file>` paths in their plan docs. Either land repo-org first and rebase those branches' plan-doc path references onto `src/`, or land those branches first and update their path references in their implementation commits. Default: land repo-org first, since it's plan-doc-only and cheap to rebase against.

---

## Out of scope

- **Restructuring the existing dispatch-prompt content beyond the brevity audit.** Each prompt's slot list and orchestration semantics stay as today. Content edits beyond "move reference material to a spec" wait for real-workflow-testing feedback.
- **Renaming any artifact.** `paper-trail.md` stays `paper-trail.md`; `verdict_schema.md` stays `verdict_schema.md`. Path moves only.
- **Adding a CI check for the sync state.** A future plan can add a pre-commit hook that verifies `.claude/<dir>/` symlinks resolve to `src/<dir>/`. v1 doesn't need it; manual `ls -la .claude/` shows the state.
- **Generating `control_flow.md` from a parser tool.** That was option 3 in the original AskUserQuestion; user picked the human-maintained spec. v1 is human-maintained. A generator can come later if the spec drifts from reality often enough to warrant the tooling.
- **Windows-friendly symlink handling.** None of paper-trail's tooling requires Windows today. Revisit if a Windows user adopts the project.
- **Deeper prompt-brevity optimization.** Per the user's "validate via real workflows" preference, deeper optimization waits for real-workflow signals.
