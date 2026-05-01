# 2026-05-01 — repo-organization and run-isolation framework planning

## Trigger

Same-day continuation of the morning's paperclip-coverage-revisit session (see `2026-05-01-paperclip-coverage-revisit.md`). After committing the paperclip-first architecture plan, the user surfaced two follow-on engineering-organization concerns that didn't fit the architectural-pivot conversation:

1. The repo is agent-instruction-forward but doesn't look like one to a casual GitHub browser. Want a top-level ship-surface directory analogous to `src/` in conventional codebases.
2. We need a way to run `/paper-trail` in isolation — clean Docker environment, no host-state poisoning — to validate the shipped product works for a fresh user.

Both got their own plan docs: `docs/plans/repo-organization.md` and `docs/plans/run-isolation-framework.md`. Both are plan-only, no code yet.

## Principles the user surfaced and the plans honor

**Human:** "code that 'ships' with paper-trail I want in a similar src folder... code being both Python but also MD instruction files."

**Agent:** Read this as agent-instruction-forward repo organization — Markdown is the dominant ship-surface artifact; Python is the secondary fallback. The repo-org plan codifies this with a "decision policy" section: default to agent instructions, write Python only when Markdown is genuinely wrong (validators, renderers, file parsing).

**Human:** "We want clear traceability of what pathways call what modular sub components, keeping with the repo guidance of modaularity, agents having limited context and therefore information should be delivered 'on a need to know basis.'"

**Agent:** This is the largest concrete deliverable in the repo-org plan — a new `src/specs/control_flow.md` spec that maps the orchestrator → dispatch → subagent → validator graph as a series of pathway-tables. Today there is no map; a fresh agent picking up a feature plan has to re-read every prompt to infer the graph. Spec is human-maintained in v1 (the user picked the maintained-spec option over a parser-tool generator).

**Human:** "make sure re: limited context that those instructions contain what is needed, not extremely long documentation stuff... though this type of thing can and will be validated and optimized based on testing real workflows."

**Agent:** Light brevity audit now — catch obvious "this section is human-orientation-only, move it to a spec" cases on the 698-line `paper-trail.md` and similar. Defer deeper optimization to post-shipping testing. The plan explicitly bounds the audit so it does not become a dead weight in front of the paperclip-first implementation.

**Human:** "we do need a plan to make an isolated 'run paper-trail in isolation' framework with Git isolation, Docker for claude isolation. A subset of the experimental hygiene (to make sure we're testing paper-trail slash command in isolation without dependencies on our local state, though we dont have a train-test experimental hygiene thing in this setting)."

**Agent:** Scoped as the isolation plan. Explicitly distinguished from the agentic-pipeline-optimization track on `sarol` — where train/test/dev hygiene applies — versus paper-trail-the-tool engineering hygiene on `main` where train/test does not apply.

## Decisions and the discussion that produced them

### `dev/` over `tools/` for the test-tooling top-level directory

**Agent recommendation:** `tools/isolation/` for the isolated-run framework, framed as "things we use to do work, not the product."

**Human pushback:** "tools is ok unless people think 'paper-trail' is the tool itself... in which case i think dev is maybe better?"

**Agent retrospective:** Sharp catch. Paper-trail IS the tool the project ships, so `tools/` reads ambiguously — a casual reader might assume `tools/` contains the tool. `dev/` reads correctly as "engineer ergonomics, not the product." Plan switched to `dev/isolation/` and the repo-org plan's "recognized non-shipped top-level directories" list includes `dev/` with the rationale baked in.

### Paperclip auth via host credential mount, not pure isolation

**Agent recommendation:** Mount `~/.paperclip/credentials.json` from host into the container read-only. Trade some "pure isolation" for zero developer friction.

**Human:** "agreed on A seems like no downside."

**Agent:** Plan defaults to credential-mount for v1 (developer-machine isolation runs). Documents `PAPERCLIP_API_KEY` env-var path as the CI option for when CI gets added. Drops the interactive-login-per-run option entirely.

### Diff tool reports drift, doesn't fail on drift, doesn't treat M1 as ground truth

**Agent initial framing:** Per-claim verdict drift bar — strict for non-AMBIGUOUS, lenient for AMBIGUOUS. Treated as a regression-test where the M1 baseline is ground truth.

**Human reframe:** "we dont need perfect matches i dont think the tool is there yet... REPORT drift but dont assume our prior PDF workflow is the ground truth either."

**Agent retrospective:** This reframe is the central principle of the isolation plan. The post-paperclip-first product will produce different verdicts than M1 for some references — paperclip-mode reading a different version of the same paper than M1's PDF-mode read may be more or less accurate. The framework needs to surface drift for human or review-agent inspection, not silently fail or silently pass. Plan switched from "regression test with pass/fail criteria" to "regression-investigation report with three classification buckets" (`agree-same-reasoning`, `agree-different-reasoning`, `disagree`). The M1 baseline is a comparison anchor, not the authority.

### Top-level `src/` mirrors `.claude/` via subdirectory symlinks (with fallbacks if symlinks break)

**Agent recommendation:** Keep `.claude/` as the canonical home (the conservative option) — Claude Code requires `.claude/commands/` and `.claude/skills/` for discovery, so the simplest path is to keep things there and rename mental model only.

**Human override:** Picked the more ambitious "Top-level src/ that mirrors .claude/" option without explicit pushback prose — the choice itself was the signal.

**Agent retrospective:** The user is willing to spend implementation cost for the cleaner ship-surface presentation on GitHub. The plan defaults to subdirectory-level symlinks (`.claude/commands/` → `src/commands/`) as the sync mechanism, and explicitly flags two fallback options as open question #1 in case symlinks break Claude Code's discovery: gitignore `.claude/<dir>/` and a `make sync` step, or back off entirely to the original conservative approach. Empirical-discovery-during-implementation is the right place to commit, not pre-commitment in the plan.

## Open questions deferred to implementation

These are listed in each plan but worth surfacing here so they don't disappear:

**repo-organization.md:**
- Sync mechanism (symlinks default; alternatives if symlinks break)
- Brevity audit threshold (content-driven for 698-line `paper-trail.md`; threshold-driven skip for prompts under 100 lines)
- Whether to keep `templates/` as a directory after collapsing to one file
- Length of `docs/SHIP_SURFACE.md` (default short; workshop the headline copy)
- Coordination with the in-flight `feature/paperclip-primary-workflow` and `feature/multi-cite-and-neighbor-claims` branches (default: land repo-org first, rebase others' plan-doc path references)

**run-isolation-framework.md:**
- GROBID version pinning depth (default: shared `.grobid-version` file at repo root)
- Claude Code CLI version pinning in the Dockerfile (default: yes)
- Smaller-and-faster fixture for iteration (default: defer until v1 lands and friction is measured)
- Network egress restriction (default: unrestricted in v1)
- Model version capture in the report (default: yes, top-of-report metadata)
- Reporting output scope — Markdown summary alongside HTML (default: yes)
- Symlink-aware bind-mounts in docker-compose post-repo-org (verify in implementation)

## Coordination implications across the now-three feature branches

After today's commits, the active branches are:

- `main` — clean baseline plus the two new plan docs once committed
- `feature/multi-cite-and-neighbor-claims` — Features 1+2 plan-only (joint multi-cite verdicts and neighbor-claim attribution)
- `feature/paperclip-primary-workflow` — paperclip-first architecture plan-only (this morning's pivot)

The repo-org plan, if landed first, requires path-reference updates in all three branches' plan docs. Coordination cost: rebase each feature branch onto the post-repo-org `main`, run `git grep -l '\.claude/'` to find affected references, update in a single rebase commit per branch.

The run-isolation plan, if landed after repo-org, references `src/<dir>/<file>` paths cleanly. If landed before repo-org, it would need the same `.claude/<dir>/<file>` references the existing plan docs use — and then need updating again when repo-org lands. Sequence: repo-org first, isolation second.

## Recommended implementation sequence

Pinning here so the user does not have to re-derive it next session:

1. **Land repo-org implementation first** (this is the layout reshuffle plus `src/specs/control_flow.md` plus the brevity audit). Plan-doc-only branches rebase against post-move `main`.
2. **Land run-isolation implementation second** (Dockerfile, docker-compose, run-test.sh, report.py). Uses the new `src/` paths cleanly.
3. **Resume paperclip-first implementation third** on the rebased `feature/paperclip-primary-workflow` branch.
4. **Land Features 1+2 fourth** on the rebased `feature/multi-cite-and-neighbor-claims` branch (or in parallel with paperclip-first if the schema-bump coordination plays out as the paperclip-first plan describes — sequence Features 1+2 first onto schema 1.1, then rebase paperclip-first to bump 1.2).

This is a recommendation, not a commitment. The user can resequence if priorities shift.
