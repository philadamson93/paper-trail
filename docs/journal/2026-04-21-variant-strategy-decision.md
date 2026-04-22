# 2026-04-21 — Variant-strategy decision: lean into Variant C as the paper's headline

Fourth and smallest journal entry for 2026-04-21. Captures the variant-selection decision made late in the session, after the agent-only + tiered-leakage framework had been documented. Human was wrapping up for the night; the decision was light-on-argument and heavy-on-endorsement, which is its own interesting pattern.

**Authoritative spec:** `docs/plans/experiment-sarol-benchmark.md` §"Variant strategy (decision 2026-04-21)." This entry is the decision log.

## The prompting question (Human 2026-04-21)

Human raised, unprompted by Agent, a sharp framing concern after the framework doc was committed:

*"I think the other thing I want to clarify is how much of our process currently is agentic versus being solved in a single prompt. Or, in other words, the dataset that we've been given, how much could that dataset task be done in a single prompt? It plausibly could be done in a single prompt. … I worry about building this whole agentic thing, but then someone rebuts and says you could have solved this task with one LLM prompt. I'm competing again against all forms of prompt optimization, ChatGPT and so forth."*

**Why this question matters:** the agent-only framework's value proposition rests on the premise that the task being optimized genuinely benefits from a multi-subagent pipeline. If a single well-crafted prompt matches the pipeline's performance, the framework is optimizing over-engineered architecture on a task that doesn't need it — a legitimate reviewer-trap.

## Agent analysis (summary)

Agent pulled dataset specifics from `experiment-sarol-faithfulness.md` and `experiment-sarol-benchmark.md` and characterized each variant:

- **Variant A** — citing sentence + pre-selected cited-paper chunks → 9-class label. Classification task with structured input. A long-context LLM with rubric inline can plausibly hit respectable macro-F1. Extractor/adjudicator/verifier decomposition's marginal *accuracy* value on Variant A is probably small; its value is in auditability / per-stage optimization / cost attribution. Reviewer asking "why not one prompt?" has a fair question here.
- **Variant C** — citing paper PDF → verdicts on every citation. Requires PDF fetching (tool use), bib resolution, cross-doc retrieval, GROBID ingest, iteration over N citations. No single prompt can do this. Agentic by construction.

Agent presented three options: (A) lead with Variant A + zero-shot baseline, (B) pivot to Variant C, (C) both arms. Agent's recommendation: run zero-shot baseline cheaply first to inform which option is best.

## Decision — Variant C leads

**Raised by:** Human.
**Exact quote:** *"alright sounds good write this to a plan doc. I think we lean in to experiment C, to your point."*
**Decision:** Variant C is the paper's headline task. Variant A stays as the iteration workbench (cheap, fast, gradient substrate for the optimizer) and as the apples-to-apples comparison arm (Sarol's published baselines were essentially verdict-core, not end-to-end).

**Rationale beyond what Human stated:** Variant C justifies the agentic framing by construction rather than by defensive argument. The agentic-optimization-for-scientific-measurement angle is more defensible under Variant C than Variant A (where the single-prompt rebuttal has more bite). Also matches what the faithfulness doc already said — *"This is the paper's headline end-to-end story even if raw numbers are lower than Sarol's narrow benchmark."* The benchmark-strategy doc was already pointing toward Variant C; the decision formalizes what was latent.

## Backburnered — "Variant D" (raw source papers + independent claim extraction)

**Raised by:** Human, extending the thought.
**Exact quote:** *"you know ideally we test end to end too from ORIGINAL source papers but to your point that requires matching claim-level to the original dataset to measure which is not guaranteed. But extending their dataset to *raw* original 100 paper and seeing how close our claim extraction even matches their source data is a task in and of itself and we can consider using their dataset as a proxy to measuring the full system. Put it on the backburner."*

What this would be: start from the 100 citing papers' raw text (not from Sarol's pre-staged claim instances), run paper-trail claim-extraction independently on every `\cite{}`, match to Sarol's annotated claims via fuzzy / embedding-based alignment, evaluate coverage + conditional F1. Uses the Sarol dataset as a *proxy measurement* of full-system behavior on raw inputs rather than a claim-pre-staged benchmark.

Why backburnered: it's a task of its own. Matching paper-trail's independent claim extraction to Sarol's annotation schema requires a new alignment rubric and is meaningfully harder than Variant C. Ambition-expanding but scope-expanding. **Pin:** consider after Variant C primary results land.

## Zero-shot single-prompt baseline — backlog, not priority

**Raised by:** Human.
**Exact quote:** *"I still think we want the zeroshot comparison but imo it's a baseline, not a 'need to do now' priority."*
**Decision:** zero-shot single-prompt baseline on Variant A is a mandatory paper table row (TextGrad Table 3 precedent). Cost is trivial (~$5-30 at N=50-600). **Pin:** before paper submission, not before Task 5 framework build-out.

Agent had proposed running the zero-shot baseline early as a strategic-pivot check. Human's call: not needed for strategic pivot, because the strategic pivot (lean into Variant C) is already decided. The zero-shot baseline becomes what it would have been anyway — a standard comparison row.

## Attribution pattern for the future paper

**Pattern 6 (new) — Human raises reviewer-trap concerns that Agent missed.**

Agent had been deep in the 9-paper lit review + framework design for ~a day and was treating the Sarol benchmark as the fixed test substrate. Human stepped back and asked the harder strategic question: *is the benchmark even the right test?* Variant A vs Variant C was in the plan, but the *decision* about which is headline had been implicit. Human forced the decision into explicit terms, flagged the single-prompt rebuttal risk, and resolved it by leaning into Variant C.

This is adjacent to Pattern 2 (Human-surfaces-structural-argument) but distinguishable: Pattern 2 is Human catching an Agent framing that's suboptimal within the current plan; Pattern 6 is Human surfacing a reviewer-response risk that Agent wasn't thinking about at all. The distinction matters for the future retrospective paper — "what value does the human add?" includes "noticing threats the agent didn't know to watch for."

## End-of-session state

Human 2026-04-21, closing: *"So let's document and then update our to-do list and docs, im done for hte night and will revisit tomorrow… i think with those design decisions still you raised from the paper."*

Plan for the next session:
- Clarifications list (Agent owes Human — see architecture-synthesis-pending-decisions.md §"Sidebarred")
- Any remaining design decisions Human wants to revisit on the agent-only framework
- Possibly begin Task 5 scoping once clarifications and framework-open-problems resolve
