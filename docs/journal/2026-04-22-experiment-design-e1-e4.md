# 2026-04-22 — Experiment design landed: E1-E4 framing, E3 as the headline

Fourth journal entry for 2026-04-22. Follows three earlier entries (topology-freedom + optimizer affordances; lit-review-2 competitor landscape; substrate Claude Code vs Pydantic AI). Captures the experiment-design decision that closes out the day's planning thread: replaces the prior Variant-A/B/C/D + DECOMPOSED-LAYERED proposal with a cleaner E1-E4 framing rooted in pipeline phases, settles on E3 (phases 2-5 from a citing-paper PDF + reference-number + claim) as the headline experiment.

## What the experiment-design conversation arrived at

Human reframed the variant question from "which Variant A/B/C/D do we run?" to a clean experiment-numbering tied to which paper-trail pipeline phases each tests. The reframe is sharper than the prior naming and survives propagation across docs.

**The 5 phases of paper-trail (recap, with phase 4 renamed from "GROBID ingest" to the tool-agnostic "PDF parsing"):**

1. **Claim extraction** — citing paper (PDF / LaTeX / text) → list of (citing_sentence, cited_ref_id, claim_text). If input is a PDF, this phase parses the PDF first.
2. **Bibliography resolution** — cited_ref_id (e.g., `\cite{smith2020}`, `[3]`) + citing paper's reference list → canonical identifier (DOI / PMC ID).
3. **PDF fetching** — canonical identifier → PDF file (or fetch-error).
4. **PDF parsing** — PDF (cited paper) → structured text. Currently uses GROBID; the phase is tool-agnostic.
5. **Verdict production** — structured cited paper + citing_sentence + claim_text → 9-class Sarol verdict. Currently 3-subagent (extractor/adjudicator/verifier) under topology-freedom (D32 from earlier today, the decision that made paper-trail's internal topology a free variable for the optimizer).

**The 4 experiments mapped to phases:**

| Name | Phases tested | Input | Status decided 2026-04-22 |
|---|---|---|---|
| **E1** (verdict-only) | Phase 5 only | Sarol pre-staged: structured cited paper chunks + citing sentence + claim | **Subaim / seeding only.** Not on the headline plot. May appear in methods section as initial isolated-component sanity check. The optimizer may decompose to E1 for sample efficiency if guided to (see D52 below) but canonical reported metric is E3. |
| **E2** (claim-extraction-only) | Phase 1 only | Citing paper (PDF or text) | **Backlogged. Decision deferred until after main experiment.** Requires LLM-as-judge alignment against Sarol annotations because Sarol's annotations are a subset of any paper's claims by design — not strictly verifiable reward. May appear as supplementary proof-of-concept with explicit limitations note, OR skipped entirely. Resolve based on how the paper feels post-main-results. |
| **E3** (fetch-through-verdict) | Phases 2-5 | (citing sentence + claim, reference token, citing paper PDF) | **Headline experiment we design for.** Paper-trail parses the citing PDF to find the bibliography entry corresponding to the reference token, resolves to canonical ID, fetches cited paper PDF, parses it, produces verdict. Closest defensible end-to-end given the dataset; ties cleanly to Sarol's existing annotations. The plot. |
| **E4** (full end-to-end) | Phases 1-5 | Citing paper PDF (no pre-registration of which claims to evaluate) | **Not designed for in this paper.** Phase 2-5 numbers become a function of phase 1 quality, requires stratification, alignment problem with Sarol annotations is the well-known unresolved Variant-C problem from prior plan docs. Not on the roadmap. |

## Decisions made today (D50–D53)

### D50 — Design for E3 (phases 2-5) as the primary experiment

**Raised by:** Human.
**Exact quote:** *"My suggestion is as follows: Design for E3, Phase2-5. This is the dataset as intended. Table Phase1. Can be an independent experiment if we choose, but requires LLM as a judge adjudication and so that's a whole other game that's not strictly a verifiable reward and perhaps out of scope entirely."*

**Decision:** the paper's headline train+val curve is on E3 (the fetch-through-verdict experiment). The optimizer iterates against E3. E3 ties paper-trail's actual deployed agentic capability (parsing a citing paper, finding a reference, fetching the cited paper, producing a verdict) to Sarol's gold labels with no LLM-judge-required scoring at the verdict step (verdict is gold-labeled).

**Why E3 and not E4 (full pipeline including phase 1 / claim extraction):** E4 requires LLM-as-judge to align paper-trail's extracted claims against Sarol's annotated subset — Sarol annotates only some claims per paper by design, so there's no way to verify "did paper-trail extract the right claims" without LLM judgment. E3 sidesteps this by pre-registering which (claim, reference) pair to evaluate.

**Why E3 and not E1 (verdict-only):** E1 bypasses the whole pipeline-realism story (PDF parsing, bib resolution, fetching). It's a sanity check on phase 5, not a meaningful demonstration of paper-trail-the-system.

### D51 — E3 input shape requires small dataset extension

**Raised by:** Human.
**Exact quote:** *"one drawback is this requires a small bit of dataset CREATION to extend the dataset we have to our PDF + ref number + claim framing."*

**The work:** Sarol's existing annotations give us per-claim records with citing sentence, cited paper text (pre-staged chunks), and gold verdict. They do NOT directly give us per-claim records keyed by (citing-paper-PDF + reference-number-within-that-PDF). We need to derive an extended dataset:
- For each Sarol claim, identify which citing paper it came from (Sarol's annotations have this implicitly).
- For each claim, identify the reference token within the citing paper that points to the cited paper (the `\cite{}` key or `[N]` reference number).
- Package as: per-claim record = (citing sentence, claim text, reference token, path to citing paper PDF).
- Citing paper PDFs need to be fetched / collected (Sarol's 100 citing papers).

Estimated effort: small — maybe a day of dataset-engineering scripts + manual spot-check on a few papers. Lands as part of Task 5 (the eval-arm build phase that's currently the next-big-thing once the canary-test gates clear).

**Decision:** add as a Task 5 deliverable. Acknowledge as honest engineering work in the paper's methods section — the experimental setup wasn't free; we extended Sarol's framing to test more pipeline phases.

### D52 — Optimizer always runs E3 canonical, may decompose to E1 for sample efficiency if instructed

**Raised by:** Human.
**Exact quote:** *"i lean always run E3... if the agent CHOOSES to break down the problem it may... we always bias the action of the agent with our instructions prompt, arguably we can guide the model to make this decision and let it know 'hey experiments may be cheaper to run if doing it via X' but drawback is then we lose some of the deterministic train/val/test python scripts type stuff."*

**Decision:** the canonical reported metric is E3. The optimizer's deterministic dispatcher always runs E3 for the train+val curve. Separately, the optimizer's initial system prompt mentions that for sample-efficient hypothesis-checking, the optimizer may dispatch isolated phase-5 (E1-shaped) sub-experiments using the same dispatcher infrastructure but with pre-staged inputs from Sarol's chunked corpus. This gives the optimizer a sample-efficient debugging tool without confusing the canonical metric.

**Engineering implication:** the dispatcher needs to support both invocation modes:
- Default: E3 (full phases 2-5 with citing PDF input). Used for canonical train+val runs.
- Optional: E1 (phase 5 with pre-staged inputs). Used by the optimizer for cheap sub-experiment hypothesis-checking when it judges useful.

**What's reported in the paper:** only E3 numbers. E1 dispatches by the optimizer are logged but don't enter the train+val curve. This preserves the cleanliness of the deterministic-dispatcher methodology while giving the optimizer the freedom Karpathy-style autoresearch would expect.

### D53 — Adopt E1/E2/E3/E4 naming as canonical; retire prior Variant A/B/C/D

**Raised by:** Human.
**Exact quote:** *"Yes propagate but always use short descriptions with them in parentheses, this is the kind of thing humans (me) are bad at keeping track of."*

**Decision:** E1/E2/E3/E4 supersedes the prior Variant-A/B/C/D naming across all docs. Always paired with a short plain-English description in parentheses when written for human readers, e.g. "E3 (the fetch-through-verdict experiment with citing PDF input)." Raw E-numbers without descriptions are reserved for Agent's bookkeeping and doc cross-references only.

**Adjacent feedback memory saved:** `feedback_plain_english_with_structured_names.md` — applies broadly to all structured identifiers (D-numbers, Tier-numbers, Task-numbers, Q-numbers, etc.), not just E-numbers.

## What this scope does NOT include

- E2 phase-1 evaluation (claim extraction): backlog. Resolve post-main-experiment.
- E4 full-end-to-end: not in this paper. Future work.
- LLM-as-judge metrics generally: scoped out of headline. E3 uses gold-labeled verdict comparison only, no LLM judge in the reward path.
- Variant D (raw source papers, no Sarol pre-staging): backlog from prior plan doc, unaffected by this reframe.

## What it preserves from earlier today's reframes

- Topology-freedom (D32, the decision that lets the optimizer restructure paper-trail's internal subagent layout): unchanged. E3 still allows paper-trail to be implemented as 1, 3, 5, or any number of subagents.
- Tiered leakage discipline (Train fully open / Val scalar-only / Test sealed): unchanged. Applies to E3.
- Optimizer affordance catalog (D34, the seeded list of actions the optimizer is told it can take): gains one entry — D52 sample-efficiency-via-E1 hint.
- Substrate (Claude Code, D48 from the substrate journal): unchanged.
- Methodology contributions (Tier 2 scalar-only val + OS-level structural enforcement + declarative per-subagent heterogeneous controllability): unchanged. All substrate- and experiment-shape-independent.

## Doc updates triggered

Landing in same session as this journal:

1. `docs/plans/experiment-sarol-benchmark.md` — replace prior Variant-A/B/C/D framing with E1-E4. E3 gets its own subsection with input shape, scoring, and pipeline-phase coverage. Variant-naming retired. The earlier Variant-B (claim extraction) entry from earlier today gets relabeled as E2 with the backlogged-decision note.
2. `docs/plans/NEXT.md` — Task 5 (the eval-arm build) gains the E3-dataset-extension work as a deliverable. The Tier 1 deliverable list (currently centered on dispatcher scripts for train/val/test) gets the E3 input-shape note.
3. `docs/plans/agentic-pipeline-optimization-framework.md` §3 (Optimizer agent initial configuration) — adds D52 sample-efficiency-via-E1 hint to the affordance catalog.
4. `docs/plans/paper-writeup-items.md` — Core Contributions list updated to reference E3 as the headline experiment instead of generic "Variant A iteration workbench" language. The case-study claims are recast with E3-specific framing.

## What's next

The day's planning thread is now closed for this session. Open items going forward (in tier order, with plain-English context):

1. **The two pre-Task-5 canary tests:** Q9c (the memory-blind canary that confirms `claude --bare --print` doesn't load the user's accumulated CLAUDE.md memory) and D44 (the canary that confirms `claude --bare --print` preserves Agent-tool availability so paper-trail subagents can still spawn). ~30 min combined; both need to pass before the eval-arm build (Task 5) can begin in earnest.
2. **Task 5 (the eval-arm build):** the bigger engineering deliverable that builds the deterministic Python dispatcher scripts, the locked output schemas, the `/sarol-eval-item` slash command, the validate_run invariant checker, the per-revision archive scaffolding, the round-trip sanity canary, the per-claim budget enforcement, AND the new D51 dataset-extension work that converts Sarol's per-claim records into the (citing PDF + reference token + claim) format E3 needs.
3. **Task 3 + Task 4 (commit-pick + manifest-lock):** identify which commit on `experiment-plan` is paper-trail-v1 (the zero-point of the curve, before any smoketest-findings-informed prompt edits); generate seeded random subset manifests at N=10/25/50/100/200.
4. **First curve runs:** smoketest E3 at v1 with N=10 (~$7); first landmark; INDIRECT-detection fix → v2 → curve continues.
