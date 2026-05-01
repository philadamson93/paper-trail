# 2026-05-01 — paperclip coverage re-probe and paperclip-first architecture decision

## Trigger

The paperclip team (James Zou's lab at Stanford) announced today that paperclip now ships full-text arXiv coverage in addition to the existing full-text PMC + bioRxiv + medRxiv corpus, plus a separate `abstracts` source that surfaces PubMed abstract-only entries.

This invalidates the central premise of the 2026-04-18 architecture reversal documented in user memory `project_paperclip_primary.md` — namely, that arXiv was abstract-only (`total_blocks=0` for every arxiv row), which capped real greppable-full-text coverage at ~15% on a representative fixture and made a paperclip-primary architecture not worth the doubled implementation surface.

## What we did this session

1. Branched from `main` to `feature/paperclip-primary-workflow` (the in-flight `feature/multi-cite-and-neighbor-claims` branch had no commits beyond `main` at the time, so no merge was needed before switching).
2. Read the archived plan `~/.claude/plans/shiny-juggling-fountain--v1-paperclip-primary-ARCHIVED.md` and the current `~/.claude/plans/shiny-juggling-fountain.md` to recover the original paperclip-primary design and the M0 reversal rationale.
3. Verified paperclip 0.3.0 ships:
   - arXiv as a first-class search source (`paperclip search -s arxiv`)
   - Real arxiv full-text at `/papers/<doc_id>/content.lines` (the `total_blocks=0` SQL field is stale; the read-layer is populated)
   - A new `abstracts` corpus for identity resolution (explicitly described as "no full text")
   - A new repo concept (`paperclip init` / `paperclip checkout`) for sticky-scoped queries
4. Ran a coverage probe on the canonical `examples/paper-trail-adamson-2025/` fixture (56 references, mixed medical-imaging plus image-quality classics — a worst-case fixture for arxiv coverage). Saved to `experiments/paperclip-coverage-2026-05-01/`. Result: **27/56 (48%) greppable full-text** — 21 via arxiv (the new addition) plus 6 via PMC. April baseline was ~6/56 (~11%), so roughly 4× lift on the worst-case fixture.
5. Drafted `docs/plans/feature-paperclip-first-architecture.md` adapting the archived v1-paperclip-primary design to the post-2026-05-01 corpus shape, the existing paper-trail orchestrator structure, and the schema-source-of-truth conventions paper-trail has shipped since the original design.

## Decisions

### Paperclip-first is the shipped default

**Human:** "i think we aim paperclip first. even with PDF fallback it requires manual download of PDFs that are paywalled which is a limitation anyways. We dont need a perfect tool, we need a helpful one."

**Agent:** That settled the question of whether mixed-path is acceptable. The PDF-centric path already requires manual user intervention for paywalled references (the existing paywall-fallback flow in `/fetch-paper`). Paperclip-first does not introduce a new failure mode — it shrinks the slice of references that hit the existing one. The April reversal hinged on "15% coverage doesn't justify a mixed-path's doubled implementation surface"; at ~50% on a worst-case fixture, that math flips.

### Empirical re-probe before plan rewrite (not announcement-driven)

**Agent:** Recommended re-running the coverage probe on the same Adamson fixture before committing to a plan rewrite, per memory `feedback_discover_by_building.md` ("default to empirical local exploration") and `feedback_rigor_over_compute.md` ("prefer thorough reads over faster paths"). The announcement said "full arxiv" but the precise shape of the addition (full-text via what mechanism? indexed how? for which subset?) needed to be measured, not assumed.

**Human:** "Re-run coverage probe first" — agreed without pushback.

**Agent retrospective:** The re-probe was load-bearing. The first read of the SQL — `arxiv | abstract_only | 3008354` — would have been misleading on its own; only inspection of `/papers/<arxiv_id>/content.lines` confirmed the full-text was real and the SQL field was stale. Skipping the re-probe and trusting the announcement summary would have produced a plan with the wrong architecture and been embarrassing on review.

### Mixed-path is permanent, not a deprecation target

**Agent:** Original archived v1-paperclip-primary plan framed PDF-centric as "the fallback path until we figure out how to push more refs through paperclip." That framing is wrong post-2026-05-01: ~50% of the Adamson fixture is paywalled MRM / IEEE TMI references that will not deposit to arxiv. The PDF-centric path is the right way to handle these, permanently. The architecture commits to two subagent dispatch prompts (paperclip and PDF) sharing one exit schema.

### Schema bump 1.1 → 1.2 is hard, no back-compat

**Agent:** New top-level `source_mode` field on the verdict envelope is required. Old verdict files without `source_mode` will fail validation; users re-run paper-trail to regenerate. Per memory `feedback_rework_for_quality.md` ("refactors are welcome if they improve the product; no backwards-compat pressure"), no migration shim.

### Author and reader modes are symmetric

**Agent:** No author-mode-only or reader-mode-only behavior. The plan applies equally to both. Smoke test covers both fixtures (`examples/paper-trail-adamson-2025/` for reader mode, `examples/DFD_authormode/` for author mode).

## Open questions deferred to implementation time

These are listed in the plan doc but worth surfacing here so they don't disappear:

1. Repo concept (paperclip 0.3.0's `init` / `checkout`) — should one paper-trail run map to one paperclip repo, or stay `--no-repo`? Discover empirically in the smoke test.
2. Sibling co-citation — keep the per-citekey extractor loop (parity with PDF mode) or switch to `paperclip map` for multi-cite sentences? Default to the loop in v1; revisit after smoke test.
3. Verifier — deterministic re-grep or LLM-based judgment layer? Default to deterministic in v1; LLM layer is orthogonal.
4. Authentication startup — one-line warning + auto-fall-back, or interactive `paperclip login` prompt? Default to one-line warning per `feedback_author_mode_always_ask_path.md`.
5. `abstracts` source in Phase 1 — default-on for identity resolution, or opt-in? Default-on; cost is sub-second per reference.

## Side findings

- The in-repo `.claude/skills/paperclip/SKILL.md` is stale (still describes the corpus as PMC + bioRxiv + medRxiv only with no arxiv or PubMed-abstract surface, and references commands the 0.3.0 CLI no longer exposes the same way). Refresh via `paperclip install --dir .` is a prerequisite for any paperclip-mode dispatch prompt to work — subagents read this skill, not memory. Listed in the plan doc as the first step of the smoke test.
- The April spike artifacts (`paper-trail-adamson2025-dfd/spike-paperclip-v1/`) were not on disk under `find` from the project root. Either cleaned up post-M1 or moved out-of-tree. The May 1 re-probe in `experiments/paperclip-coverage-2026-05-01/` is the new evidence base.
- Paperclip's `--json` flag for `sql` is silently a no-op in 0.3.0 — the CLI accepts it without error but always emits tabular text. Probe scripts that need to parse output should parse the text-table format instead. (May be worth surfacing upstream as a small bug-or-doc-mismatch fix; deferred per memory `feedback_discover_by_building.md`.)
