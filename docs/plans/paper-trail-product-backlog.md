# paper-trail product backlog

The Sarol experiment + paper-writing work occupies a *subspace* of the full paper-trail product — only the testable elements (extractor / adjudicator / verifier prompts and pipeline logic the eval-arm exercises) are part of that subspace. We still want to ship a respectable paper-trail v1 alongside the paper / blog-post launch, which means the items below need to land too.

## When this doc gets read

During paper-trail product work — typically post-submission, when attention turns from the experiment + writeup back to the shipped tool. **Not on the critical path during the experiment + writeup phase.** Fresh agents in experiment-or-writeup mode can skip this doc.

## Status convention

Backlog by default. None of these block the paper or the experiment. When picking one up, move it to a tracking issue or in-progress section as appropriate.

## Provenance

Created 2026-04-23 by migrating "incremental re-validation after corrections" out of `paper-writeup-items.md` (where it was parked because of motivational ties to the paper-presentation companion artifact, but where it would have been invisible to product-mode-Claude / product-mode-Human). The user added the additional items below at the same time, naming them as a non-exhaustive starting list — *"Probably a few other things but don't need to dwell on all of them now, but worth writing down alongside the above."*

---

## Backlog

### Features

- **Incremental re-validation after corrections** (raised 2026-04-23, originally captured in `paper-writeup-items.md` as the product dependency for the before/after companion-artifact paper-presentation flow; migrated here 2026-04-23). The before/after presentation in the paper / GitHub-companion artifact requires paper-trail to support a workflow where the author (or an agent collaborator assisting the author) corrects claims flagged by an initial paper-trail pass, paper-trail persists the prior verdict state, and a re-run re-validates only the corrected claims — claims that were already verified stay marked completed and are not re-run. Motivation is both (i) the companion-artifact presentation path for the paper (see `paper-writeup-items.md` §"Other paper-level threads worth developing", paper-presentation-artifact item) and (ii) general usability — re-running end-to-end after every small edit is expensive and noisy. **Open design questions for whoever picks this up:** what defines a "correction" — does paper-trail diff the manuscript automatically, or does the author explicitly mark which flagged claim they addressed? Does the prior-verdict-state cache invalidate when the cited paper itself changes (new version of the citing paper)? How does the cache key relate to the claim's text vs the surrounding paragraph?

- **UI improvements** (raised 2026-04-23 as a placeholder bucket). The shipped paper-trail UX surface — slash-command output formatting, in-product help text, the LaTeX/PDF artifact paper-trail produces, the demo at `philadamson93.github.io/paper-trail/demo.html` — has not had a v1-product-readiness pass. Specific items to enumerate as identified during the UX pass.

### Documentation

- **paper-trail product docs pass** (raised 2026-04-23). The shipped tool's README, demo page, how-to-use, and any in-product help text need a v1-product-readiness review alongside the paper / blog-post launch. Specific deliverables to enumerate as identified during the docs pass.

### Distribution

- **MCP server registry submissions** (raised 2026-04-23). paper-trail-as-MCP-server should be submitted to whatever community / Anthropic MCP registries exist for v1-product launch, so users discover and install paper-trail through the standard MCP discovery flow rather than having to find the GitHub repo first. Audit what registries exist + their submission requirements before picking up.

- **Skill repository submissions** (raised 2026-04-23). Same idea for skill registries — community skill repositories should list paper-trail as an available skill so users discover it via the same channels they discover other Claude Code skills.

### To enumerate

This list is intentionally non-exhaustive. The user named the items above 2026-04-23 with: *"Probably a few other things but don't need to dwell on all of them now, but worth writing down alongside the above."* Add items as identified during paper-trail product work.

---

## Out of scope for this doc

- **Sarol experiment work** — see `NEXT.md` tier-0 through tier-3.
- **Paper-writing concerns** (claims, framing, contributions, related-work positioning) — see `paper-writeup-items.md`.
- **Framework methodology decisions** (tiered leakage discipline, optimizer/dispatcher/subagent architecture, structural defenses) — see `agentic-pipeline-optimization-framework.md`.
- **Eval-arm-specific implementation** (archive schema, dispatcher invariants, sealed-test mechanism) — see `experiment-sarol-archive-and-eval-framework.md`.
