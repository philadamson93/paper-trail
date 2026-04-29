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

---

## Decisions

### Repo structure: monorepo for now, split-option preserved (resolved 2026-04-23)

Where do paper-trail-the-tool and the experiment harness (eval-arm, dispatcher scripts, Sarol-specific prompts) live relative to each other? Two options were weighed:

1. **Monorepo** — status quo; both live in the same git repo under the `experiments/sarol-2024/` subtree.
2. **Split** — paper-trail in its own repo (clean for product-mode users, MCP / skill-registry submissions point at a repo without research apparatus); experiment harness in a separate repo that references paper-trail at specific `paper-trail-v<N>` tags via git submodule or vendored snapshot.

**Decision: monorepo for the lifetime of this paper.**

**Why.** `paper-trail-v<N>` git tags are the model artifacts in the paper's framing — they need to live on the same repo as the paper-trail prompt/spec files the tag references; otherwise the tag becomes meaningless and you are forced to design a two-axis versioning scheme (paper-trail-prompts vN × eval-harness vM) during active iteration, which adds friction without payoff. Cross-doc references across the plan-doc cluster (this doc → `paper-writeup-items.md` → `agentic-pipeline-optimization-framework.md` → `experiment-sarol-archive-and-eval-framework.md`) are heavily interconnected and would become cross-repo URLs or relative paths vulnerable to either repo being renamed or moved. Pre-commit hook wiring for eval-harness immutability is already set up against the monorepo and would need re-hosting on a split.

**How to apply when product-launch cleanliness becomes a real concern.** Options ordered from least-cost to most-cost:

- **Inside-monorepo cleanliness (easiest).** Focused README on paper-trail-the-tool; clearly-labeled `experiments/` top-level subtree; clean `release/v1` tag documenting product scope. No structural change.
- **Subtree-split mirror (intermediate).** `git subtree split` a product-only mirror to a separate `paper-trail-tool` repo used for MCP / skill-registry submissions, with the monorepo staying canonical. No dual-history maintenance.
- **Full split (most-cost).** Extract `experiments/sarol-2024/` to its own repo, rewrite cross-references as cross-repo pointers. Mechanical, low-risk, and not harder to do later than it is now — so deferred.

**Human 2026-04-23:** *"I prefer to just go with the monorepo and can split it out later if we want to for simplicity."*
