Reference: docs/claude_ops.md

# Plan — agent-instruction-forward repo organization

## Goal

Make paper-trail's ship surface visible at a glance on GitHub. Today the shipped product (Markdown prompts + skills + specs + Python helpers) all sits under `.claude/` because Claude Code requires it there — a casual reader can't see "this is what ships." Introduce a top-level `src/` that mirrors `.claude/`, add a single source of truth (`src/specs/control_flow.md`) mapping the orchestrator → dispatch → subagent → exit-validation graph, and run a light brevity audit on existing prompts.

## Approach

Subdirectory-level symlinks (`.claude/<dir>/` → `src/<dir>/`) keep Claude Code's discovery working unchanged while making `src/` the canonical home. Shipped prompts/specs migrate path references to `src/...` (see Resolved decision RD-2). Author-mode vendoring stays supported: README updated so users vendor-copy `src/` alongside `.claude/` (RD-1). Nested directory-shaped skills like `paperclip/SKILL.md` are part of the mirrored ship surface (RD-3). The packaging contract, path policy, and smoke tests have their own sections below.

## Verification

The plan succeeds if a fresh agent can (a) browse `src/` on GitHub and see the ship-surface layout in one view, (b) read `src/specs/control_flow.md` and trace a Phase-3 dispatch from orchestrator line → dispatch prompt → emitted schema fields → exit-validation rule, (c) follow the updated README to vendor `paper-trail` into a temp project and successfully invoke `/paper-trail --author`, and (d) run `/paper-trail` end-to-end on `examples/paper-trail-adamson-2025/` with Claude Code resolving slash commands through the symlinks. Full check list in "Smoke test plan" below.

---

## Provenance and status

**Status.** Plan-only. No code yet. Companion to `docs/plans/feature-paperclip-first-architecture.md` (which assumes the present `.claude/` layout) and `docs/plans/run-isolation-framework.md` (the next plan doc, which will lean on this one's ship-surface map).

**Provenance.** Scoped 2026-05-01 immediately after the paperclip-first commit. Decision-log entry is the same day's `docs/journal/2026-05-01-paperclip-coverage-revisit.md` end section (to be appended). Codex review of this plan landed 2026-05-18 at `docs/plans/reviews/repo-organization-feedback.md` (Verdict: Revise); findings applied in the corresponding revision pass — see "Resolved decisions" below for the three design forks the review surfaced.

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
- `.claude/skills/<entry>` → `src/skills/<entry>` for each entry under `.claude/skills/`, where an entry is **either** a single `<name>.md` **or** a directory of the shape `<name>/SKILL.md` (and any sidecar files the skill ships). At plan-write time the inventory is: `doc-split-check.md`, `plan-check.md`, `paperclip/SKILL.md`. Re-enumerate via `ls .claude/skills/` at implementation time so a newly-added skill isn't missed.
- `.claude/scripts/*.py` → `src/scripts/*.py`
- `templates/*.md` → `src/templates/*.md`

After the move, run `ln -s` to create the `.claude/` symlinks. Test that Claude Code still finds slash commands and **both single-file and directory-shaped skills** via the symlink path — the discovery test must explicitly load a directory-shaped skill (e.g., `paperclip`) in addition to a single-file one.

**Files to update (for the cross-reference to `src/` paths):**

This list is illustrative, not exhaustive. The canonical manifest is generated at implementation time by `git grep -nE '\.claude/|templates/(?!claims_ledger\.md$)' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` (journal entries and review files are historical and stay frozen). Every hit is either updated to the new path or annotated in-place with a "stays as `.claude/` — publication target" comment per RD-2.

Known surfaces (verify and extend from the grep output):

- `README.md` — currently documents the author-mode "copy `.claude/` and `templates/` into a writing repo" workflow; updates per RD-1 (vendor-copy `src/` alongside) plus per RD-2 (any `.claude/<dir>/<file>` example references migrate to `src/<dir>/<file>`).
- `docs/internals.md` — embeds `.claude/<dir>/<file>` path references when explaining the orchestrator architecture; migrate per RD-2.
- `docs/output.md` — same.
- `CLAUDE.md` — the "Where things live" section currently pins `.claude/<dir>/<file>` paths. Update to `src/<dir>/<file>` with a one-line note that `.claude/<dir>/` is a symlink. Keeps the document pointing at the canonical home.
- `.gitignore` — currently has `.claude/skills/*` plus a `!.claude/skills/<name>.md` carveout per skill. After the move, the canonical home is `src/skills/`, which doesn't need that carveout. Remove the `.claude/skills/*` ignore line and its carveouts (the symlink target lives in `src/` which is fully tracked). Verify the existing gitignored items (`/experiments/`, `.env`, GCP credentials, `pdfs/`) remain.
- `docs/plans/feature-paperclip-first-architecture.md` — references `.claude/<dir>/<file>` paths throughout. Update each reference to `src/<dir>/<file>`. (Cross-plan coordination cost; one of the reasons to land repo-org before paperclip-first implementation begins.)
- `docs/plans/feature-multi-cite-joint-verdict.md`, `docs/plans/feature-neighbor-claim-attribution.md`, `docs/plans/feature-issue-command.md` — same path-reference update pattern.
- `docs/plans/add-paper-trail-orchestrator.md`, `docs/plans/author-mode-parity.md`, `docs/plans/blindspot-mitigations.md` — same.
- `docs/plans/paper-trail-product-backlog.md` — same.
- `docs/NEXT.md` — verify path references; update any `.claude/` literals.
- Shipped runtime artifacts under `src/commands/`, `src/prompts/`, `src/specs/` — see "Path policy" section for the per-file enumeration.
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

## Author-mode packaging / vendoring

`README.md` documents an author-mode workflow where a user copies parts of paper-trail into a writing repo to gain the `/paper-trail --author` slash command locally. This is a cross-repo API surface — moving `.claude/<dir>/` to subdirectory symlinks into `src/` would silently break it, because `cp -R .claude templates writing-repo/` preserves the symlinks and leaves them dangling at the target unless `src/` is copied alongside.

**Resolved decision (RD-1):** vendor-copy `src/` alongside `.claude/` and `templates/`. The README's "Install into a writing repo" section gets a one-line update — from "copy `.claude/` and `templates/`" to "copy `src/`, `.claude/`, and `templates/` (in that order — `.claude/` contains symlinks that must resolve against the vendored `src/`)." The implication: the author-mode contract now spans three top-level directories, not two. After `templates/` moves under `src/templates/` per Implementation surface, the vendoring instruction collapses back to two: `src/` and `.claude/`.

**Smoke test (mandatory before the reorg is considered shipped):**

1. `mkdir /tmp/vendor-smoke && cd /tmp/vendor-smoke`
2. Copy `src/` and `.claude/` from the paper-trail repo per the new README instruction.
3. Verify `.claude/commands/paper-trail.md` resolves through the symlink (`ls -L .claude/commands/`).
4. Open the directory in Claude Code (`claude --add-dir /tmp/vendor-smoke`) and confirm `/paper-trail` appears as a discoverable slash command.
5. Invoke `/paper-trail --author <path-to-test-manuscript>` against a small `.tex` fixture (one citation, one claim) and confirm it completes without "command not found" or path errors.

This is the canonical packaging contract for author mode. Any change to the symlink layout that breaks step 4 must update the README in the same commit.

---

## Path policy in shipped prompts and specs

Today's `.claude/commands/paper-trail.md`, `.claude/prompts/*.md`, `.claude/specs/*.md`, and `.claude/scripts/*.py` contain hard-coded `.claude/<dir>/<file>` and `.claude/scripts/<file>` references in their prose (invocation strings, cross-file pointers, dispatch-template paths). After the reorg, those same paths resolve identically via the symlinks, but two writable surfaces (`src/` and `.claude/`) would let drift in.

**Resolved decision (RD-2):** migrate every shipped runtime reference to `src/...`. `.claude/` is publication-only — never edit through it, never reference it from a shipped prompt/spec. Symlinks keep execution working; the migration is purely about single source of truth.

**Concrete enumeration** (verify with `git grep -nE '\.claude/' src/ templates/` after the move; treat as a manifest, not a hand-curated list):

- `src/commands/paper-trail.md` — multiple sites: invocation examples for `validate_claims.py` (current `:352`, `:360`), the dispatch-template paths named in Phase 3 / 3.5 (`:383`, `:411`, `:445`), and the renderer invocation in Phase 5 (`:512`).
- `src/prompts/extractor-dispatch.md` — references to `verdict_schema.md` and any spec paths.
- `src/prompts/adjudicator-dispatch.md` — same.
- `src/prompts/verifier-dispatch.md` — same.
- `src/specs/ingest.md` — any `.claude/scripts/` references in invocation examples.
- `src/scripts/validate_claims.py` and `src/scripts/render_html_demo.py` — if any internal path defaults reference `.claude/` (they currently do not, but verify post-move with `grep -nE '\.claude' src/scripts/*.py`).

Re-anchored line numbers will shift slightly after edits; the spec is "every `.claude/` literal in shipped artifacts becomes `src/`," not "edit these specific lines."

---

## Traceability — `src/specs/control_flow.md`

The single largest deliverable of this plan. Today there is no map of which orchestrator phase dispatches which subagent, which dispatch prompt reads which `{{slot}}` from which orchestrator dispatch payload, which subagent emits which `verdict_schema.md` field, and which exit-validation rule gates each emitted artifact. A fresh agent reads `paper-trail.md` (698 lines) and infers the graph; a less-fresh agent forgets. Both shapes are bug-prone.

`control_flow.md` is structured as a series of named pathway-tables. Each row is a single hop in the agent graph. The example tables below are illustrative — exact orchestrator line numbers will be re-pinned at implementation time off the post-move `src/commands/paper-trail.md` and verified against the current dispatch sites, not assumed.

**Pathway: orchestrator stages → dispatch / script / exit-validation**

| Phase | Orchestrator anchor in `src/commands/paper-trail.md` | Call shape | Artifact (schema) | Exit validation |
|---|---|---|---|---|
| Phase 3.1 — Claim extraction | "Step 3.1 — Claim extraction" heading + the disambiguation-heuristics subsection | In-orchestrator prompt instructions (no subagent dispatch) | candidate-claim list `{claim_text, citekey, manuscript_section}` | (none — orchestrator-internal) |
| Phase 3.1.5 — Pre-dispatch claim validator | "Step 3.1.5 — Validate extracted claims against the manuscript" heading | `src/scripts/validate_claims.py --run-dir <output-dir>` (reader) **or** `--run-dir <project-root> --manuscript-path <…>` (author) | `claim_extraction_report.md` | Script flags `TEXT_ANCHOR_MISSING` / `FRONT_MATTER_ANCHOR` / `CITEKEY_MARKER_MISMATCH`; non-zero exit gates Phase 3.2 |
| Phase 3.2 Pass 1 — Extractor | "Step 3.2 — Two-pass dispatch" header → dispatch-template path named, then per-claim slot-fill and send | `src/prompts/extractor-dispatch.md` | `ledger/evidence/<claim_id>.json` | Orchestrator-enforced exit-schema checks per `src/specs/verdict_schema.md` "Validation rules" — JSON parses, required fields present, `claim_id` matches dispatch, `sub_claims` non-empty, every `sub_claims[i].verdict` is a valid enum |
| Phase 3.2 Pass 2 — Adjudicator | Same "Step 3.2" subsection, post-extractor slot-fill of `adjudicator-dispatch.md` | `src/prompts/adjudicator-dispatch.md` | `ledger/claims/<claim_id>.json` | Same orchestrator-enforced exit-schema checks per `verdict_schema.md`, plus the rollup-consistency invariant (`overall_verdict` consistent with `sub_claims[*].verdict`) |
| Phase 3.3 — Ledger render | "Step 3.3 — Ledger rendering" heading | Derived-view re-render from `ledger/claims/*.json` | `ledger.md` | (re-render is idempotent; not a validation gate) |
| Phase 3.5 — Verifier | "Phase 3.5 — Attestation verification" heading; dispatch template named, slot-fill and send | `src/prompts/verifier-dispatch.md` | `ledger/verifications/<claim_id>__<sub_claim_id>.json` | `result` enum check (`PASS` / `PARTIAL` / `FAIL`); two-bounce ceiling before flagging `AMBIGUOUS` with `SCHEMA_VIOLATION` |
| Phase 5 — HTML render | "Phase 5 — Render HTML viewer" heading | `src/scripts/render_html_demo.py --run-dir <output-dir>` | `<output-dir>/demo.html` | Non-fatal warning on failure; canonical ledger artifacts unaffected |

**Pathway-row drafting rule** (for the implementer): each row's "Orchestrator anchor" must be a stable section heading or named step, not a raw line number. Line numbers shift on every prompt edit and silently invalidate the spec. Where pinning is desired for precision, pair the heading anchor with a current line number and a re-pin procedure (e.g., `grep -n "Step 3.2 — Two-pass dispatch" src/commands/paper-trail.md` returns the canonical line). `plan-check` adds an enforcement step.

**Where validation actually lives.** Codex review of this plan correctly flagged that `validate_claims.py` is a **pre-dispatch manuscript validator** (it checks that extracted claim text actually appears in the manuscript and that nearby citation markers match the assigned citekey), **not** an exit-schema validator on subagent output. The exit-schema validation rules are in `src/specs/verdict_schema.md` "Validation rules" section (`JSON parses` / `required fields` / `claim_id matches` / `sub_claims non-empty` / `valid verdict enums` / `rollup consistent`); they are enforced inline by the orchestrator on each subagent return, not by a separate Python validator. `control_flow.md` must name these correctly — pre-dispatch vs exit, script-name vs orchestrator-enforced.

**Pathway: dispatch slot map**

| Dispatch prompt | Slot | Source field on orchestrator dispatch JSON | Notes |
|---|---|---|---|
| `extractor-dispatch.md` | `{{claim_id}}` | per-claim record `claim_id` | |
| `extractor-dispatch.md` | `{{co_citekeys}}` | per-claim record `co_citekeys` (flat array) | extractor populates `evidence.co_cite_context.sibling_citekeys` |
| `extractor-dispatch.md` | `{{handle}}` | per-claim record `handle` | local PDF dir for PDF mode; will become `paperclip_handle` for paperclip mode after `feature-paperclip-first-architecture.md` lands |
| `extractor-dispatch.md` | `{{ingest_mode}}` | per-claim record `ingest_mode` | `grobid` / `pdftotext_fallback` / `ocr_fallback` — drives trust-adjusted confidence |
| ... | ... | ... | ... |

The implementer enumerates all `{{slot}}` placeholders by grepping `src/prompts/*.md` and pairs each with its source in the dispatch-payload JSON sketch in `src/commands/paper-trail.md`. Re-enumeration on each prompt edit is a `plan-check` requirement.

**Pathway: skill auto-load triggers**

| Skill (location) | Trigger condition | Used by |
|---|---|---|
| `src/skills/doc-split-check.md` | doc edit ≥ 400 lines | manual + commit-review |
| `src/skills/plan-check.md` | new or substantially-edited plan doc in `docs/plans/` | manual + commit-review |
| `src/skills/paperclip/SKILL.md` (directory-shaped) | author/orchestrator invokes paperclip read-path or pre-pulls preprint metadata | `feature-paperclip-first-architecture.md` workflow |

Updates to `control_flow.md` are part of any feature plan that touches the dispatch graph (this becomes a check item in `plan-check.md`).

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

- **Build the canonical migration manifest first.** Run `git grep -nE '\.claude/|^\s*templates/' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` from the repo root. Every hit is a candidate for path migration per RD-2. Classify each hit before editing: (a) shipped runtime artifact → migrate to `src/...`, (b) doc/plan prose → migrate to `src/...`, (c) `.gitignore` rule → update carveout pattern, (d) intentional reference to publication-target `.claude/` (rare; annotate inline). The manifest is the source of truth for what gets touched in implementation commits, not the bullet list below.
- **Where path literals actually live** (verified 2026-05-18 against the current tree, not predicted):
  - **Shipped Markdown** is the dominant surface — `.claude/commands/paper-trail.md` carries the most hits (invocation strings for `validate_claims.py`, dispatch-template paths named in Phase 3 / 3.5, the Phase 5 renderer invocation), followed by `.claude/prompts/extractor-dispatch.md`, `.claude/prompts/adjudicator-dispatch.md`, `.claude/specs/ingest.md`, and `.claude/commands/ground-claim.md` / `.claude/commands/init-writing-tools.md`.
  - **`.claude/scripts/*.py`** is **not** a hit-heavy surface — `validate_claims.py` and `render_html_demo.py` accept paths as CLI flags and do not hardcode `.claude/<dir>/<file>` literals. Verify post-move with `grep -nE '\.claude' src/scripts/*.py`; expect zero structural hits, just docstring examples if any.
  - **User-facing docs** (`README.md`, `docs/internals.md`, `docs/output.md`) embed `.claude/` references when explaining the architecture or the author-mode vendoring workflow; the README is the API-surface document per RD-1 and gets the most-careful update.
- **CLAUDE.md** — contains the current "Where things live" pointer list and reading-path. Single largest single-file update among docs at the repo root.
- **`.gitignore`** — currently has `.claude/skills/*` plus per-skill carveouts (added in commit `dffb0b1`). The carveout pattern goes away after the move; `src/skills/` is fully tracked.
- **All plan docs in `docs/plans/`** — each contains `.claude/<dir>/<file>` path references; updated in lockstep. Plan docs under `docs/plans/reviews/` are historical (frozen).
- **`templates/claims_ledger.md`** — moves to `src/templates/claims_ledger.md`. Check whether `paper-trail.md` references the template path and update.

---

## Smoke test plan

The plan succeeds if a fresh agent in a future session can:

1. Open the repo on GitHub, click on `src/`, and see the ship-surface layout in one view.
2. Read `src/specs/control_flow.md` and explain in their own words: "Phase 3 dispatches the extractor at line N of `src/commands/paper-trail.md` using `src/prompts/extractor-dispatch.md`; the extractor populates the `evidence` field; the adjudicator reads the evidence and emits a verdict; `src/scripts/validate_claims.py::VERDICT_SHAPE` checks the verdict."
3. Pick up `docs/plans/feature-paperclip-first-architecture.md` and identify all the files they need to edit using only `src/` paths.
4. Run `/paper-trail` end-to-end on `examples/paper-trail-adamson-2025/` and confirm Claude Code still finds the slash command via the `.claude/commands/` symlink.

Specific verification steps:

- **Slash-command discovery.** Run `/paper-trail` after the symlink rewire. If Claude Code can't find the slash command, the symlink approach is wrong and we need to escalate to one of the open-question alternatives (build script or gitignored `.claude/`).
- **Per-command coverage.** Run `/ground-claim` and any other slash command from the new location. Same check.
- **Skill discovery — both shapes.** Run a single-file skill (`doc-split-check`, `plan-check`) **and** the directory-shaped `paperclip` skill — auto-load it via the trigger condition or invoke explicitly. Discovering only the `.md` shape silently breaks the `feature-paperclip-first-architecture.md` workflow, so this is a separate must-pass step from the single-file check (closes Codex C3).
- **Author-mode vendoring smoke test.** Execute the five-step vendoring procedure in "Author-mode packaging / vendoring" against a clean temp directory and confirm step 5 (`/paper-trail --author` against a small `.tex` fixture) completes without "command not found" or path errors. Mandatory before reorg ships — author mode is a cross-repo API surface.
- **Repo-wide path-policy sweep.** After the path migrations land, run `git grep -nE '\.claude/' -- 'src/' 'README.md' 'docs/' ':!docs/journal/*' ':!docs/plans/reviews/*'` and confirm the output is empty or every hit has an inline annotation explaining why it stays as `.claude/`. Any unannotated hit is a stale reference violating RD-2.
- **Git history continuity.** `git log --follow src/commands/paper-trail.md` should show full history back through the `.claude/commands/paper-trail.md` era. (`git mv` preserves history.) Repeat for one representative directory-shaped skill (`git log --follow src/skills/paperclip/SKILL.md`).
- **Clean working tree.** `git status` shows no spurious diffs from the symlink wiring.
- **Sync-script fallback gate (only if symlinks fail).** If discovery fails and we fall back to OQ1 option (a) (gitignored `.claude/<dir>/` + `make sync`), `docs/claude_ops.md`'s "no build step" assumption changes — that fallback requires its own follow-up commit updating claude_ops.md and gating CI on `make sync` having run.

---

## Resolved decisions

Three design forks the 2026-05-18 Codex review surfaced; resolved by the user the same day. Each pin is load-bearing for sections above — the plan reads incorrectly if a reader misses one.

- **RD-1: Author-mode vendoring stays supported via vendor-copy of `src/` alongside `.claude/`.** The "Author-mode packaging / vendoring" section above is the canonical contract; the README update + temp-project smoke test are mandatory deliverables. Alternative considered (materialize `.claude/` on export, dropping `src/` mirror, or deprecating author mode entirely) rejected: the simplest fix that preserves today's cross-repo workflow.
- **RD-2: Shipped runtime references migrate to `src/...`.** `.claude/` is publication-only; never edit through it, never reference it from a shipped prompt/spec. Symlinks keep execution working; the migration buys single source of truth. See "Path policy in shipped prompts and specs" for the enumeration.
- **RD-3: Directory-shaped skills (e.g., `paperclip/SKILL.md`) are part of the mirrored ship surface.** The move spec is directory-aware; the discovery smoke test must cover both single-file and directory shapes. Alternative considered (leave `paperclip/` at `.claude/skills/paperclip/` as an out-of-scope exception) rejected: ships an inconsistent ship-surface mirror on day one and would silently break the `feature-paperclip-first-architecture.md` workflow.

---

## Open questions

1. **Sync mechanism fallback if symlinks break Claude Code discovery.** Default is subdirectory-level symlinks (the smoke test gates this). If discovery fails in practice, fall back to: (a) gitignore `.claude/<dir>/` and have a `make sync` step that copies `src/<dir>/*` into `.claude/<dir>/` before Claude Code sessions, or (b) keep `.claude/` as the canonical home and skip the `src/` mirror entirely. Fallback (a) requires a follow-up commit updating `docs/claude_ops.md`'s "no build step" assumption. Decision: try symlinks first; back off only if measurable breakage.
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
