Reference: docs/claude_ops.md

# Plan — agent-instruction-forward repo organization

## Goal

Make paper-trail's ship surface visible at a glance on GitHub. Today the shipped product (Markdown prompts + skills + specs + Python helpers) all sits under `.claude/` because Claude Code requires it there — a casual reader can't see "this is what ships." Introduce a top-level `src/` that mirrors `.claude/`, add a single source of truth (`src/specs/control_flow.md`) mapping the orchestrator → dispatch → subagent → exit-validation graph, and run a light brevity audit on existing prompts.

## Approach

Subdirectory-level symlinks (`.claude/<dir>/` → `src/<dir>/`) keep Claude Code's discovery working unchanged while making `src/` the canonical home. Shipped prompts/specs migrate path references to `src/...` (see Resolved decision RD-2). **Author-mode is redesigned to take a manuscript path argument** (RD-9, supersedes RD-1) — paper-trail lives at one canonical path, the user invokes `/paper-trail --author /abs/path/to/main.tex` after pointing Claude Code at paper-trail's directory; no cross-repo vendoring, no symlink portability concerns. Nested directory-shaped skills like `paperclip/SKILL.md` are part of the mirrored ship surface (RD-3). The path policy and smoke tests have their own sections below.

## Verification

The plan succeeds if a fresh agent can (a) browse `src/` on GitHub and see the ship-surface layout in one view, (b) read `src/specs/control_flow.md` and trace a Phase-3 dispatch from orchestrator line → dispatch prompt → emitted schema fields → exit-validation rule, (c) follow the updated README to invoke `/paper-trail --author /abs/path/to/main.tex` against an external manuscript without vendoring paper-trail into the writing repo (RD-9), and (d) run `/paper-trail` end-to-end on `examples/paper-trail-adamson-2025/` with Claude Code resolving slash commands through the symlinks. Full check list in "Smoke test plan" below.

---

## Provenance and status

**Path-literal note.** This plan documents the `.claude/` → `src/` migration itself, so its `.claude/` and `templates/` literals intentionally describe the pre-move layout and the publication-target symlinks; they are exempt from the RD-2 path-policy sweep (annotated here once rather than per-line).

**Status.** Plan-only. No code yet. Companion to `docs/plans/feature-paperclip-first-architecture.md` (which assumes the present `.claude/` layout) and `docs/plans/run-isolation-framework.md` (the next plan doc, which will lean on this one's ship-surface map).

**Provenance.** Scoped 2026-05-01 immediately after the paperclip-first commit. Decision-log entry is the same day's `docs/journal/2026-05-01-paperclip-coverage-revisit.md` end section (to be appended). Codex review of this plan landed 2026-05-18 at `docs/plans/reviews/repo-organization-feedback.md` (Verdict: Revise); findings applied in the corresponding revision pass — see "Resolved decisions" below for the three design forks the review surfaced (RD-1, RD-2, RD-3). On 2026-05-20 the five then-open questions were resolved by the user (RD-4..RD-8), and a fresh-Claude-Code second-reviewer pass at `docs/plans/reviews/repo-organization-feedback-claude.md` (Verdict: Revise) surfaced load-bearing gaps in the migration-manifest regex, the gitignored→tracked transition for `paperclip/SKILL.md`, the vendoring symlink contract, and a few smoke-test holes; agreed findings applied inline, four user-decision items preserved as OQ-A..OQ-D. A Codex second-pass review the same day at `docs/plans/reviews/repo-organization-feedback-2026-05-20.md` (Verdict: Revise) caught that the post-fresh-Claude regex fix was *still wrong* — `git grep -E` is POSIX ERE and `\b` is treated as a literal `b`, not a word boundary; the manifest count was 12 instead of the correct 45 and missed every sentinel doc. The regex now uses `(^|[^[:alnum:]_])templates/`, and the manifest gate now requires sentinel-file coverage in addition to a hit-count threshold. Later the same day the user resolved OQ-A/OQ-B/OQ-D, and the resolution of OQ-C escalated into an architectural pivot (**RD-9 supersedes RD-1**): author mode is redesigned to take a manuscript path argument rather than require vendoring paper-trail into the writing repo. RD-1, the six-step vendoring smoke test, the `readlink` relative-target invariant, and the `core.symlinks` portability concern are all retired by RD-9; the "Author-mode invocation" section captures the new contract.

**HTML companion.** `docs/plans/repo-organization.html` is a generated visual view via `/explain-plan`; it regenerates on substantive plan edits and is not a manual deliverable. Treat the markdown as canonical; if the HTML's embedded `plan-sha256` differs from the markdown's current SHA, the HTML is stale by definition — regenerate via `/explain-plan` rather than hand-editing.

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
- `.claude/skills/<entry>` → `src/skills/<entry>` for each entry under `.claude/skills/`, where an entry is **either** a single `<name>.md` **or** a directory of the shape `<name>/SKILL.md` (and any sidecar files the skill ships). At plan-write time the inventory is: `doc-split-check.md`, `plan-check.md`, `paperclip/SKILL.md`. Re-enumerate via `ls .claude/skills/` at implementation time so a newly-added skill isn't missed. **Paperclip transition (resolved per OQ-A):** `paperclip/SKILL.md` is currently untracked (matched by `.claude/skills/*` ignore without a carveout) but ships after the move — it is a load-bearing dependency of `feature-paperclip-first-architecture.md` and was always implicitly in the ship surface via RD-3. The new `.gitignore` adds an explicit carveout for `src/skills/paperclip/` so it tracks consistently with the other shipped skills.
- `.claude/scripts/*.py` → `src/scripts/*.py`
- `templates/*.md` → `src/templates/*.md`

After the move, run `ln -s` to create the `.claude/` symlinks. Test that Claude Code still finds slash commands and **both single-file and directory-shaped skills** via the symlink path — the discovery test must explicitly load a directory-shaped skill (e.g., `paperclip`) in addition to a single-file one.

**Files to update (for the cross-reference to `src/` paths):**

This list is illustrative, not exhaustive. The canonical manifest is generated at implementation time by `git grep -nE '\.claude/|(^|[^[:alnum:]_])templates/' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` (journal entries and review files are historical and stay frozen). Every hit is either updated to the new path or annotated in-place with a "stays as `.claude/` — publication target" comment per RD-2. The regex deliberately includes `templates/claims_ledger.md` — that file IS being moved and its references must follow. **Sanity-check the manifest by both count and sentinel-file assertions** (the 2026-05-20 Codex second-pass review caught that a count-only check passes coincidentally when the regex misses the most important references). Today's tree returns ~45 `templates/` hits with the correct POSIX ERE boundary; a manifest below 30 is suspect. **Required sentinel files** (the manifest MUST include at least one hit in each): `README.md`, `CLAUDE.md`, `docs/claude_ops.md`, `.claude/commands/paper-trail.md`, `.claude/commands/init-writing-tools.md`. **Do not use** `\b` as a word boundary in this regex — `git grep -E` is POSIX ERE and `\b` is treated as a literal `b`, not a boundary (this trap claimed two prior plan drafts). Also do not use PCRE lookaheads.

Known surfaces (verify and extend from the grep output):

- `README.md` — currently documents the author-mode "copy `.claude/` and `templates/` into a writing repo" workflow. **Per RD-9**, that section is deleted and replaced with "Use paper-trail on an external manuscript" documenting the three invocation patterns (cd into paper-trail / `claude --add-dir` / user-global slash-command symlink) and the `--output-dir` knob. Any remaining `.claude/<dir>/<file>` example references migrate to `src/<dir>/<file>` per RD-2.
- `docs/internals.md` — embeds `.claude/<dir>/<file>` path references when explaining the orchestrator architecture; migrate per RD-2.
- `docs/output.md` — same.
- `CLAUDE.md` — the "Where things live" section currently pins `.claude/<dir>/<file>` paths. Update to `src/<dir>/<file>` with a one-line note that `.claude/<dir>/` is a symlink. Keeps the document pointing at the canonical home.
- `.gitignore` — currently has `.claude/skills/*` plus a `!.claude/skills/<name>.md` carveout per shipped skill (today: `doc-split-check.md`, `plan-check.md`). After the move, drop the old `.claude/skills/*` block (it's now a symlink target) and **re-establish a `src/skills/*` ignore with explicit per-shipped-skill carveouts** (resolved per OQ-B — preserves today's "auto-installed or local-experiment skills don't accidentally ship" guarantee). Concrete `.gitignore` shape after the move:

  ```
  # Skills (shipped surface) — explicit carveout list; everything else under src/skills/ stays local-only
  src/skills/*
  !src/skills/doc-split-check.md
  !src/skills/plan-check.md
  !src/skills/paperclip/
  ```

  Re-enumerate carveouts from `ls src/skills/` at implementation time so a future shipped skill addition adds its carveout in lockstep. Verify the other existing gitignored items (`/experiments/`, `.env`, GCP credentials, `pdfs/`) remain.
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

## Author-mode invocation (paths, not vendoring)

Per **RD-9** (resolved 2026-05-20), author mode no longer requires vendoring paper-trail into the writing repo. paper-trail lives at one canonical path (the user's clone, e.g., `~/Documents/.../paper-trail/`); the user runs Claude Code with paper-trail's directory on the path and invokes the slash command with an absolute manuscript path argument. No cross-repo file copying; no symlinks crossing repos; no `core.symlinks` portability concern; nothing to commit to the writing repo's git history.

**Invocation patterns** (any one works; document all in README):

- **From inside paper-trail's directory:** `cd ~/Documents/.../paper-trail && claude` → `/paper-trail --author /abs/path/to/writing-repo/main.tex`
- **From the writing repo, with `--add-dir`:** `cd /path/to/writing-repo && claude --add-dir ~/Documents/.../paper-trail` → `/paper-trail --author $(pwd)/main.tex`
- **Symlink the slash-command file** (optional convenience): `ln -s ~/.../paper-trail/.claude/commands/paper-trail.md ~/.claude/commands/paper-trail.md` to make it user-globally discoverable; the slash command's prompt resolves all its references relative to paper-trail's canonical path, not the symlink-host path.

**Slash-command contract** (the orchestrator prompt accepts and validates):

- Required positional arg: absolute path to a `.tex` file or a directory containing one.
- Optional `--output-dir <path>` (default: alongside the manuscript — e.g., `<manuscript-dir>/ledger/`, `<manuscript-dir>/demo.html`).
- Reject relative paths in the manuscript arg with a clear error: "manuscript path must be absolute so paper-trail can locate the manuscript regardless of which directory Claude Code was launched from."
- Validate the manuscript path exists and is readable before any dispatch fires.

**Smoke test (mandatory before the reorg is considered shipped):**

1. From a clean Claude Code session: `cd ~/Documents/.../paper-trail && claude`.
2. Invoke `/paper-trail --author /Users/.../paper-trail/examples/DFD_authormode/main.tex` (known-good multi-citation fixture).
3. Confirm the slash command discovers, validates the manuscript path, and runs end-to-end without "command not found" or path errors.
4. Confirm outputs land at `examples/DFD_authormode/ledger/` and `examples/DFD_authormode/demo.html` (or wherever `--output-dir` pointed).
5. Repeat from a different cwd via `--add-dir`: `cd /tmp && claude --add-dir ~/Documents/.../paper-trail` and re-run the same invocation; confirm identical behavior. This isolates "the slash command resolves its own references via paper-trail's canonical path, not via the user's cwd."

**README rewrite** (per RD-9 + RD-2):

- Delete the "Install into a writing repo" / vendoring section entirely.
- Replace with a "Use paper-trail on an external manuscript" section documenting the three invocation patterns above.
- Note that vendoring (copying paper-trail into a writing repo) is intentionally not supported in v1 — if a user wants their writing repo to carry a frozen snapshot of paper-trail, they can `cp -R` it manually, but that's not the supported workflow and updates won't flow.

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
| Phase 3.2 Pass 1 — Extractor | "Step 3.2 — Two-pass dispatch" header → dispatch-template path named, then per-claim slot-fill and send | `src/prompts/extractor-dispatch.md` | `ledger/evidence/<claim_id>.json` | per `src/specs/verdict_schema.md` §Validation rules (orchestrator-enforced inline on each return) |
| Phase 3.2 Pass 2 — Adjudicator | Same "Step 3.2" subsection, post-extractor slot-fill of `adjudicator-dispatch.md` | `src/prompts/adjudicator-dispatch.md` | `ledger/claims/<claim_id>.json` | per `src/specs/verdict_schema.md` §Validation rules + rollup-consistency invariant (`overall_verdict` consistent with `sub_claims[*].verdict`) |
| Phase 3.3 — Ledger render | "Step 3.3 — Ledger rendering" heading | Derived-view re-render from `ledger/claims/*.json` | `ledger.md` | (re-render is idempotent; not a validation gate) |
| Phase 3.5 — Verifier | "Phase 3.5 — Attestation verification" heading; dispatch template named, slot-fill and send | `src/prompts/verifier-dispatch.md` | `ledger/verifications/<claim_id>__<sub_claim_id>.json` | `result` enum check (`PASS` / `PARTIAL` / `FAIL`); two-bounce ceiling before flagging `AMBIGUOUS` with `SCHEMA_VIOLATION` |
| Phase 5 — HTML render | "Phase 5 — Render HTML viewer" heading | `src/scripts/render_html_demo.py --run-dir <output-dir>` | `<output-dir>/demo.html` | Non-fatal warning on failure; canonical ledger artifacts unaffected |

**Pathway-row drafting rule** (for the implementer): each row's "Orchestrator anchor" must be a stable section heading or named step, not a raw line number. Line numbers shift on every prompt edit and silently invalidate the spec. Where pinning is desired for precision, pair the heading anchor with a current line number and a re-pin procedure (e.g., `grep -n "Step 3.2 — Two-pass dispatch" src/commands/paper-trail.md` returns the canonical line). `plan-check` adds an enforcement step.

**Where validation actually lives.** Codex review of this plan correctly flagged that `validate_claims.py` is a **pre-dispatch manuscript validator** (it checks that extracted claim text actually appears in the manuscript and that nearby citation markers match the assigned citekey), **not** an exit-schema validator on subagent output. The exit-schema validation rules are in `src/specs/verdict_schema.md` "Validation rules" section (`JSON parses` / `required fields` / `claim_id matches` / `sub_claims non-empty` / `valid verdict enums` / `rollup consistent`); they are enforced inline by the orchestrator on each subagent return, not by a separate Python validator. `control_flow.md` must name these correctly — pre-dispatch vs exit, script-name vs orchestrator-enforced.

**No-drift constraint for `control_flow.md`.** Exit-validation cells in the pathway tables MUST link to `src/specs/verdict_schema.md` "Validation rules" by section anchor — never reproduce the bulleted rules. Any cell that needs more than a sentence to express the validation must point at the source spec rather than expand. Same rule for verdict-enum lists, sub_claim shapes, and verifier `result` enums: spec is the source of truth; `control_flow.md` is the cross-cut. Drift between the two is the failure mode this constraint exists to prevent.

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

**Subagent-context audit (mandatory side-check).** For each block moved out of `paper-trail.md` into a spec, name which subagents read that spec. Moving a 50-line block from `paper-trail.md` → `verdict_schema.md` is a net win for the orchestrator's context and a net-zero for the adjudicator subagent (which reads `verdict_schema.md` anyway), but a net-loss for the extractor subagent if the moved block is irrelevant to extraction (the subagent now pulls in spec content it doesn't need). The audit deliverable below records, per moved block: source location, destination spec, which subagents currently read the destination, and whether the move is net-positive across all readers. If a block is only relevant to the orchestrator, prefer a Provenance section at the bottom of `paper-trail.md` or a journal entry, not a spec file the subagents will also load.

Audit deliverable: a per-prompt before/after line count plus a one-paragraph summary in this plan's "Smoke test results" section after the audit runs, plus the per-moved-block subagent-reader table from the side-check above. No further commitments — the deeper "is this prompt actually optimal" question goes to post-shipping testing per the user's stated principle.

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

- **Build the canonical migration manifest first.** Run `git grep -nE '\.claude/|(^|[^[:alnum:]_])templates/' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` from the repo root. POSIX ERE — do **not** use `\b` here (`git grep -E` treats it as a literal `b`, not a word boundary; this gave a 12-hit false-positive count in a prior plan draft). Do not use PCRE lookaheads. Every hit is a candidate for path migration per RD-2. Classify each hit before editing: (a) shipped runtime artifact → migrate to `src/...`, (b) doc/plan prose → migrate to `src/...`, (c) `.gitignore` rule → update carveout pattern, (d) intentional reference to publication-target `.claude/` (rare; annotate inline). The manifest is the source of truth for what gets touched in implementation commits, not the bullet list below. **Sanity-check by count AND sentinel files**: today's tree returns ~45 `templates/` hits; a manifest below 30 is suspect, and the result MUST include hits in `README.md`, `CLAUDE.md`, `docs/claude_ops.md`, `.claude/commands/paper-trail.md`, and `.claude/commands/init-writing-tools.md`.
- **Where path literals actually live** (verified 2026-05-18 against the current tree, not predicted):
  - **Shipped Markdown** is the dominant surface — `.claude/commands/paper-trail.md` carries the most hits (invocation strings for `validate_claims.py`, dispatch-template paths named in Phase 3 / 3.5, the Phase 5 renderer invocation), followed by `.claude/prompts/extractor-dispatch.md`, `.claude/prompts/adjudicator-dispatch.md`, `.claude/specs/ingest.md`, and `.claude/commands/ground-claim.md` / `.claude/commands/init-writing-tools.md`.
  - **`.claude/scripts/*.py`** is **not** a hit-heavy surface — `validate_claims.py` and `render_html_demo.py` accept paths as CLI flags and do not hardcode `.claude/<dir>/<file>` literals. Verify post-move with `grep -nE '\.claude' src/scripts/*.py`; expect zero structural hits, just docstring examples if any.
  - **User-facing docs** (`README.md`, `docs/internals.md`, `docs/output.md`) embed `.claude/` references when explaining the architecture or the author-mode workflow; the README is the API-surface document and per RD-9 its vendoring section is deleted (not migrated) and replaced with the manuscript-path-arg invocation patterns.
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

- **Manifest sanity-check (gates everything below).** Before treating the path-migration manifest as canonical, run it and assert two things: (i) hit count — today's tree returns ~45 `templates/` hits and several dozen `.claude/` hits; under 30 `templates/` hits is suspect, and (ii) **sentinel-file coverage** — the manifest MUST include at least one hit in each of `README.md`, `CLAUDE.md`, `docs/claude_ops.md`, `.claude/commands/paper-trail.md`, and `.claude/commands/init-writing-tools.md`. Count-only is insufficient: a regex that returns nonzero but misses these files (e.g., a `\b`-based boundary that `git grep -E` reads as literal `b`) passes a count check and quietly leaves stale references in the most important docs.
- **Slash-command discovery (structural).** Run `/paper-trail` after the symlink rewire. If Claude Code can't find the slash command, the symlink approach is wrong and the RD-4 fallback applies.
- **Slash-command execution (behavioral).** Concrete invocation against the canonical fixture: `/paper-trail examples/paper-trail-adamson-2025/` from a clean working tree (no pre-existing `ledger/` or `demo.html` under the fixture dir). Expected artifacts after completion: `examples/paper-trail-adamson-2025/ledger/claims/*.json` (one per extracted claim), `examples/paper-trail-adamson-2025/ledger.md`, `examples/paper-trail-adamson-2025/demo.html`. Discovery passing while execution fails (e.g., a runtime path-resolution error through the symlink chain) triggers the RD-4 fallback — not just outright "command not found." Move pre-existing output aside (`mv ledger /tmp/ledger-pre-reorg-backup`) before running, and diff after for regressions.
- **Per-command coverage** (all six slash commands; today's inventory from `.claude/commands/*.md`):
  - `/paper-trail` — full behavioral run, per the previous bullet.
  - `/ground-claim` — discover + run on a single claim from the canonical fixture (e.g., the first claim in the fixture's `claims_ledger.md`); expect a refreshed `ledger/claims/<cid>.json`.
  - `/init-writing-tools` — discover + run against `examples/DFD_authormode/`; expect a clean exit and updated `.claude/` artifacts in that fixture (or fail if init-writing-tools is reader-only — verify against today's behavior).
  - `/paper-trail-init` — discover + run against a clean temp directory; expect a fresh `paper-trail-init`-shaped scaffold.
  - `/fetch-paper` — discover only (behavioral test would hit the network; out of scope for the local smoke).
  - `/verify-bib` — discover + run against `examples/paper-trail-adamson-2025/` (or whichever fixture currently exercises bib verification); expect a `verify-bib` report artifact.
- **Skill discovery — both shapes.** Run a single-file skill (`doc-split-check`, `plan-check`) **and** the directory-shaped `paperclip` skill — auto-load it via the trigger condition or invoke explicitly. Discovering only the `.md` shape silently breaks the `feature-paperclip-first-architecture.md` workflow, so this is a separate must-pass step from the single-file check (closes Codex C3).
- **Author-mode invocation smoke (RD-9).** Execute the five-step "Author-mode invocation" procedure against `examples/DFD_authormode/main.tex`: invoke `/paper-trail --author /abs/path/to/main.tex` once from inside paper-trail's dir and once via `claude --add-dir` from `/tmp`, confirming both produce identical outputs at `<manuscript-dir>/ledger/` and `<manuscript-dir>/demo.html`. Mandatory before reorg ships — author mode is a public API surface. Replaces the prior vendoring smoke; there is no vendored copy to verify.
- **Fresh-clone symlink resolution (internal use only after RD-9).** `git clone` the repo into a clean directory; assert `readlink .claude/commands` resolves correctly so a fresh clone's internal Claude-Code discovery still works. (Pre-RD-9 this also gated cross-repo vendoring portability; post-RD-9 it only gates the repo's own internal consistency.)
- **Repo-wide path-policy sweep.** After the path migrations land, run `git grep -nE '\.claude/' -- 'src/' 'README.md' 'CLAUDE.md' '.gitignore' 'docs/' ':!docs/journal/*' ':!docs/plans/reviews/*'` and confirm the output is empty or every hit has an inline annotation explaining why it stays as `.claude/` (e.g., the `.gitignore` carveout rules, the CLAUDE.md "publication target" note). Any unannotated hit is a stale reference violating RD-2. Run the equivalent sweep for `templates/` (without the `src/` prefix) to catch stale top-level template references.
- **Git history continuity.** `git log --follow src/commands/paper-trail.md` should show full history back through the `.claude/commands/paper-trail.md` era. (`git mv` preserves history.) Repeat for one representative *tracked* single-file skill: `git log --follow src/skills/plan-check.md` or `src/skills/doc-split-check.md`. **Do not use `paperclip/SKILL.md` for this check** — it is currently untracked, so `git log --follow` returns empty regardless of whether `git mv` worked; the check would pass coincidentally. The paperclip skill's git history starts at the repo-org commit.
- **`settings.local.json` stays put.** Assert `test -f .claude/settings.local.json && test ! -e src/settings.local.json` — the file is Claude-Code-required at `.claude/` root and must not be swept into the move.
- **Clean working tree.** `git status` shows no spurious diffs from the symlink wiring.
- **Sync-script fallback gate (only if symlinks fail).** If discovery OR behavioral execution fails for a symlink-related reason and we fall back to RD-4 option (a) (gitignored `.claude/<dir>/` + `make sync`), `docs/claude_ops.md`'s "no build step" assumption changes — that fallback requires its own follow-up commit updating claude_ops.md and gating CI on `make sync` having run. **Pre-drafted fallback patch:** the implementer should pre-write the `docs/claude_ops.md` diff *before* running the symlink smoke test, so the choice at smoke-test time is "ship symlinks" or "apply the prepared patch," not "design the fallback under pressure."

---

## Resolved decisions

Nine design forks resolved across three reviewer passes and the user's same-day resolutions. RD-1 was superseded by RD-9 after the user surfaced a better author-mode design mid-OQ-resolution. Each pin is load-bearing for sections above — the plan reads incorrectly if a reader misses one.

- **RD-1 (SUPERSEDED by RD-9, 2026-05-20):** ~~Author-mode vendoring stays supported via vendor-copy of `src/` alongside `.claude/`.~~ Original framing assumed the cross-repo vendoring contract was load-bearing. The user's OQ-C' response surfaced a better design (paper-trail at canonical path, manuscript-path-as-arg) that eliminates vendoring entirely. RD-9 replaces this decision; the "Author-mode invocation" section above is the new contract.
- **RD-2: Shipped runtime references migrate to `src/...`.** `.claude/` is publication-only; never edit through it, never reference it from a shipped prompt/spec. Symlinks keep execution working; the migration buys single source of truth. See "Path policy in shipped prompts and specs" for the enumeration.
- **RD-3: Directory-shaped skills (e.g., `paperclip/SKILL.md`) are part of the mirrored ship surface.** The move spec is directory-aware; the discovery smoke test must cover both single-file and directory shapes. Alternative considered (leave `paperclip/` at `.claude/skills/paperclip/` as an out-of-scope exception) rejected: ships an inconsistent ship-surface mirror on day one and would silently break the `feature-paperclip-first-architecture.md` workflow.
- **RD-4: Symlinks first; defined fallback only if symlinks measurably fail (discovery OR execution).** Try subdirectory-level symlinks as the v1 sync mechanism (the smoke test gates this). If Claude Code's slash-command/skill *discovery* fails, OR if a behavioral end-to-end smoke (`/paper-trail examples/paper-trail-adamson-2025/`) fails for a symlink-or-path-resolution-related reason, fall back to (a) gitignore `.claude/<dir>/` and add a `make sync` target that copies `src/<dir>/*` into `.claude/<dir>/` before sessions. **Pre-drafted fallback patch (must be ready before smoke tests run):** (i) `docs/claude_ops.md` line 22 edit replacing the "no build step" assertion with "one build step: `make sync` keeps `.claude/<dir>/` in sync with `src/<dir>/` between sessions"; (ii) a `Makefile` `sync` target that does `for d in commands prompts specs skills scripts; do rsync -a --delete src/$$d/ .claude/$$d/; done`; (iii) a `make check-sync` target that runs `diff -r src/<dir>/ .claude/<dir>/` for each content-bearing directory and exits non-zero if they diverge (gate this in CI and in a pre-commit hook so a session-start divergence is caught loudly). Alternative (b) considered (keep `.claude/` canonical, skip the `src/` mirror entirely) rejected: defeats the headline goal of a visible ship surface.
- **RD-5: Brevity audit is content-driven for `paper-trail.md`, skipped for prompts under 100 lines this round.** On the 698-line orchestrator, move reference material to specs regardless of line count. Dispatch prompts and smaller commands (< 100 lines) are skipped in this audit and revisited after one real-workflow run. Avoids pre-optimizing prompts that haven't shown up as a problem.
- **RD-6: Keep `src/templates/` as a directory even though only `claims_ledger.md` lives there today.** `feature-issue-command.md` implies an `issue-draft.json` template arrives soon; the single-file directory is cheaper than re-creating it later, and groups templates with the rest of the ship surface.
- **RD-7: `docs/SHIP_SURFACE.md` is a short orientation doc (~50 lines), not a long one.** Points at `src/specs/control_flow.md` for the actual dispatch map. Honors the user's "instructions contain what is needed, not extremely long documentation" preference. Headline copy workshopped per memory `feedback_short_headline_copy.md` before commit.
- **RD-8: Land repo-org before the in-flight `feature/paperclip-primary-workflow` and `feature/multi-cite-and-neighbor-claims` branches.** Both reference `.claude/<dir>/<file>` paths in their plan docs; repo-org is plan-doc-only and cheap to rebase against, so those branches absorb a one-shot path-reference update on rebase rather than landing first and creating drift to chase.
- **RD-9 (resolved 2026-05-20, supersedes RD-1): Author mode takes a manuscript path argument; no vendoring.** paper-trail lives at one canonical path (the user's clone). User runs Claude Code with paper-trail's directory available (`cd paper-trail && claude` OR `claude --add-dir paper-trail/` OR a user-global slash-command symlink) and invokes `/paper-trail --author /abs/path/to/main.tex`. Outputs land at `<manuscript-dir>/ledger/` and `<manuscript-dir>/demo.html` by default (overridable via `--output-dir`). **What this eliminates:** the entire cross-repo vendoring contract; the six-step `/tmp/vendor-smoke` procedure; the `readlink` relative-target invariant; the `core.symlinks` portability concern; the OQ-C "local-copy vs commit-and-distribute" fork (moot — there is nothing to commit). **What this adds:** explicit-path arg validation in the slash-command prompt; the `--output-dir` knob with a sensible default; the README "Use paper-trail on an external manuscript" section; the two-cwd smoke test (from inside paper-trail's dir AND from elsewhere via `--add-dir`) to isolate that the slash command resolves its references via paper-trail's canonical path, not the user's cwd. Alternative considered (keep vendoring, declare commit-and-distribute out of scope per the original OQ-C local-copy default) rejected: the user's "do we really need vendoring?" question correctly identified that the vendoring contract was incidental complexity, not load-bearing for any real use case.

---

## Open questions

All four user-decision items surfaced by the 2026-05-20 fresh-Claude review pass are resolved (the resolution of OQ-C escalated into the architectural pivot captured as RD-9, which supersedes RD-1).

- **OQ-A (resolved 2026-05-20): Ship `paperclip/SKILL.md`.** It's the 208-line generic paperclip CLI skill (a virtual filesystem of full-text biomedical papers across PMC / bioRxiv / medRxiv / arXiv), not personal research-skills content. RD-3 + `feature-paperclip-first-architecture.md` already treat it as a load-bearing dependency, so transitively it was always part of the ship surface; the gitignored state was incidental. After the move, `src/skills/paperclip/SKILL.md` is tracked.
- **OQ-B (resolved 2026-05-20): re-establish a `src/skills/*` ignore with explicit carveouts** — option (b). Mirrors today's `.claude/skills/*` + per-shipped-skill carveout pattern. Rationale: the user wants the "auto-installed or local-experiment skills don't accidentally ship" guarantee to hold after the symlink rewire (personal research-skills experiments shouldn't leak into shipped commits). After the move, the new `.gitignore` reads:

  ```
  src/skills/*
  !src/skills/doc-split-check.md
  !src/skills/plan-check.md
  !src/skills/paperclip/
  ```

  (Re-enumerate the carveouts from the post-move `ls src/skills/` so a future shipped skill addition adds its carveout in lockstep.)
- **OQ-C / OQ-C' (resolved 2026-05-20 as RD-9): no vendoring; manuscript-path argument instead.** The original OQ-C framing ("local-copy vs commit-and-distribute" for the vendoring contract) was superseded mid-resolution when the user surfaced the deeper question of whether vendoring is even needed. RD-9 captures the redesign: paper-trail lives at one canonical path, slash command takes an absolute manuscript path argument. See RD-9 (Resolved decisions) and "Author-mode invocation" section for the contract.
- **OQ-D (resolved 2026-05-20): orchestrator passes the spec path in the slot fill** — option (3). The orchestrator knows its own canonical path (paper-trail repo root via `git rev-parse --show-toplevel` at dispatch time) and passes a `{{spec_root}}` (or `{{repo_root}}`) slot to dispatch prompts that need to reference specs. Dispatch prompts construct paths as `{{spec_root}}/src/specs/<file>` and resolve correctly regardless of the subagent's cwd. Relative paths embedded as literals in dispatch prompts (options 1 and 2) don't work because the subagent's cwd varies. The path-policy sweep gets a carveout: `{{spec_root}}/src/...` occurrences in dispatch prompts are valid; bare `src/specs/<file>` literals (no slot prefix) are stale. **Cross-check against RD-9:** with RD-9 in place, the subagent's cwd is whatever Claude Code was launched from (the user's choice); the `{{spec_root}}` slot makes that irrelevant for spec resolution.

---

## Implementation results (2026-06-09)

Implemented on branch `repo-organization` (off `feature/paperclip-primary-workflow`). Mechanical move landed as its own commit so `git mv` rename detection stays clean of the content edits.

### Manifest sanity check (gate) — PASS

`git grep -nE '\.claude/|(^|[^[:alnum:]_])templates/' -- ':!docs/journal/*' ':!docs/plans/reviews/*'` on the pre-move tree returned **306 hits, 48 `templates/` hits** (threshold ≥ 30), with all five sentinel files covered (`README.md` 1, `CLAUDE.md` 16, `docs/claude_ops.md` 5, `.claude/commands/paper-trail.md` 13, `.claude/commands/init-writing-tools.md` 2).

### Brevity audit deliverable (RD-5)

Per-prompt line counts (before → after; "before" includes the +~20 lines the RD-9 arg contract and `{{spec_root}}` payload additions added to `paper-trail.md` during this same implementation):

| Prompt | Before | After | Change |
|---|---|---|---|
| `paper-trail.md` | 698 (+~20 RD-9/OQ-D) | 674 | trace-log reference block → `src/specs/trace_log.md`; "why two passes" → Provenance footer |
| `ground-claim.md` | 172 | 172 | unchanged this round (content-driven pass found no spec-duplicating blocks; revisit after a real-workflow run per RD-5) |
| `paper-trail-init.md` | 146 | 146 | unchanged |
| `verify-bib.md` | 121 | 121 | unchanged |
| `init-writing-tools.md` | 87 | 87 | < 100 lines — skipped per RD-5 |
| `fetch-paper.md` | 70 | 70 | < 100 lines — skipped |
| `extractor-dispatch.md` | 87 | 87 | < 100 lines — skipped |
| `adjudicator-dispatch.md` | 102 | 102 | dispatch prompt — slot lists out of scope per audit rules |
| `verifier-dispatch.md` | 90 | 90 | < 100 lines — skipped |

Subagent-reader side-check for each moved block:

| Moved block | Source | Destination | Who reads the destination | Net |
|---|---|---|---|---|
| Trace-log record schema + event list + jq recipes (~40 lines) | `paper-trail.md` § Trace log | `src/specs/trace_log.md` (new spec) | orchestrator only — no dispatch prompt references it, so no subagent context cost | net-positive (orchestrator loads on demand; pointer + event-name summary stays inline) |
| "Why two passes" rationale (5 lines) | `paper-trail.md` § Step 3.2 | `paper-trail.md` § Provenance (bottom) | human reviewers | net-positive (orientation content out of the dispatch-time read path) |

### Pre-drafted RD-4 fallback patch (NOT applied — symlinks passed structural checks)

Prepared before smoke tests per RD-4, kept here in case a future behavioral smoke fails for a symlink-related reason:

1. `docs/claude_ops.md` — replace the "There is no build step, no runtime, and no test suite." sentence in the Environment section with: "One build step: `make sync` keeps `.claude/<dir>/` in sync with `src/<dir>/` between sessions. No runtime, no test suite."
2. New `Makefile`:

   ```make
   DIRS = commands prompts specs skills scripts

   sync:
   	for d in $(DIRS); do rm -rf .claude/$$d && rsync -a --delete src/$$d/ .claude/$$d/; done

   check-sync:
   	@for d in $(DIRS); do diff -r src/$$d/ .claude/$$d/ || exit 1; done
   ```

3. Gate `make check-sync` in a pre-commit hook (and CI when it exists) so session-start divergence fails loudly.

### Structural smoke results

All run 2026-06-09 on the `repo-organization` branch:

- **Path-policy sweep (`.claude/`)** — PASS. Residual hits are all annotated/intentional: `.gitignore` comments, the out-of-repo user-global memory path in `CLAUDE.md`, `src/skills/plan-check.md`'s pre-vs-post-repo-org guidance, and symlink-explaining prose. `docs/plans/repo-organization.md` is exempt via its single top-of-file annotation (documents the migration itself); generated `docs/plans/*.html` companions are excluded (regenerate via `/explain-plan`, never hand-edit).
- **Path-policy sweep (`templates/`)** — PASS, zero hits.
- **Git history continuity** — PASS. `git log --follow src/commands/paper-trail.md` reaches the original "Add /paper-trail orchestrator command" commit; `--follow src/skills/plan-check.md` reaches its `plan-doc-readiness-check` origin. (Checked a tracked skill, not `paperclip/SKILL.md`, whose history legitimately starts at the move commit.)
- **`settings.local.json` stays put** — PASS in the implementation worktree (`src/settings.local.json` absent); the `test -f .claude/settings.local.json` half holds in the user's main checkout where the machine-local file lives.
- **Read-through-symlink** — PASS. `.claude/commands` → `../src/commands` (relative target); file reads resolve.
- **iCloud gotcha (new, worth knowing):** the repo lives under iCloud-synced `Documents/`; iCloud renamed the five freshly-created symlinks to `<name> 2` mid-creation (sync-conflict suffix) on the first attempt. Fixed by `mv`-ing back; if symlinks ever show ` 2` suffixes after a checkout, that's iCloud, not git.
- **Fresh-clone symlink resolution** — PASS. `git clone --branch repo-organization` into a clean directory: `readlink .claude/commands` → `../src/commands`, file reads resolve through the symlink, and `git ls-files src/skills/` shows all three shipped skills including `paperclip/SKILL.md`.

### Deferred to user (behavioral smokes)

Discovery + execution smokes need real interactive Claude Code sessions against the main checkout after this branch merges:

1. `/paper-trail examples/paper-trail-adamson-2025/<input>.pdf` end-to-end from a clean tree (move pre-existing output aside first; diff after).
2. Per-command discovery coverage: `/ground-claim`, `/init-writing-tools`, `/paper-trail-init`, `/fetch-paper` (discover only), `/verify-bib`.
3. Skill discovery both shapes: a single-file skill (`plan-check`) AND the directory-shaped `paperclip`.
4. Author-mode two-cwd smoke (RD-9): `/paper-trail --author <abs>/examples/DFD_authormode/main.tex` once from inside paper-trail's dir, once from `/tmp` via `claude --add-dir`; outputs must be identical.

## Out of scope

- **Restructuring the existing dispatch-prompt content beyond the brevity audit.** Each prompt's slot list and orchestration semantics stay as today. Content edits beyond "move reference material to a spec" wait for real-workflow-testing feedback.
- **Renaming any artifact.** `paper-trail.md` stays `paper-trail.md`; `verdict_schema.md` stays `verdict_schema.md`. Path moves only.
- **Adding a CI check for the sync state.** A future plan can add a pre-commit hook that verifies `.claude/<dir>/` symlinks resolve to `src/<dir>/`. v1 doesn't need it; manual `ls -la .claude/` shows the state.
- **Generating `control_flow.md` from a parser tool.** That was option 3 in the original AskUserQuestion; user picked the human-maintained spec. v1 is human-maintained. A generator can come later if the spec drifts from reality often enough to warrant the tooling.
- **Windows-friendly symlink handling.** None of paper-trail's tooling requires Windows today. Revisit if a Windows user adopts the project.
- **Deeper prompt-brevity optimization.** Per the user's "validate via real workflows" preference, deeper optimization waits for real-workflow signals.
