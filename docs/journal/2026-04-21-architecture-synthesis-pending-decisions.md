# 2026-04-21 — Architecture synthesis from the lit review + pending decisions

**STATUS: RESOLVED 2026-04-21 — superseded by the agent-only reframe.** Human returned from meetings and decided the fundamental question that was raised at the top: the experiment is agent-only, not human-in-the-loop. This supersedes most of the "keep vs. not" recommendations below (which assumed human-in-the-loop) and the three pending decisions become either moot or answered by the new framework.

**Resolution:** see the authoritative plan doc `docs/plans/agentic-pipeline-optimization-framework.md` (tiered leakage discipline, optimizer/dispatcher/subagent architecture, structural defenses) and the decision-log journal entry `docs/journal/2026-04-21-tiered-leakage-framework-decisions.md`.

**Mapping of the three pending decisions → post-reframe resolution:**
- **Decision 1 (revision-workflow doc placement):** now moot. In agent-only mode the "revision workflow" is the optimizer agent's internal loop, not a Human-Agent session. Its specification lives in the framework plan doc, not in a hygiene-rule section.
- **Decision 2 (v1 gate list):** answered by `agentic-pipeline-optimization-framework.md` §"Implementation checklist (feeds NEXT.md Task 5)." Expanded from the five originally proposed to include filesystem-permission boundary tests, locked output schemas for train/val/test dispatchers, and uniform-invocation `/sarol-eval-item`.
- **Decision 3 (three-way ablation frequency):** resolved — Agent lean (only at v_final) adopted. Applied to the case study (paper-trail + Sarol); not a framework-level concern.

**Sidebarred (explicitly deferred during the reframe):**
- Clarifications list (fixed-topology-by-design, DSPy trace-aware metric, MA-SAPO App H, ProTeGi gradient template, mutation-operator menu, subagent revision order, bandit candidate selection). Owed to Human; not blocking.
- Agent-only N=10 de-risk smoketest design. Deferred per Human: "I still think we're a little ways away from that. This experimental infrastructure is critical to nail down before we begin."
- From-scratch variant (could the framework build paper-trail from zero?). Deferred per Human: "I want to start from where we are now."
- Human-agent collaboration retrospective → future separate paper.

**What stays valid from the synthesis below:** the per-item borrow classifications (must-adopt / revision-workflow / paper-visual / defer / skip) mostly survive, reinterpreted in agent-only context (e.g., ProTeGi gradient template now templates the OPTIMIZER AGENT's failure-mode analysis rather than a Human journal entry). The "must-adopt" items fold into the framework doc §"Implementation checklist." The "defer-with-milestone-pin" items fold into the framework doc §8. The "skip" items are unchanged.

---

## Original content (preserved for reference — not authoritative post-reframe)

**One fundamental question I have is: should the experiment be agent-only, fully autonomous, with no leakage from me from this point out, and you have a verifiable reward? Or is the angle of my paper that the human is in the loop always, and so we should test systems like that with the bias that we're kind of testing my own engineering skills a little bit? Perhaps that's not good science, even if it would lead to a better product — clearly, if I was just building a paper trail, I would do the human in the loop, the me in the loop. To the extent that I want to measure a system that agentically is able to build and improve upon a tool, perhaps the answer is agent only, obviously not human only. I haven't quite decided yet. I lean towards agent only; I just worry about how well it will work. Maybe if it doesn't work well, then it's an architecture flaw. I suppose I worry about divergence, whereby, imagine a system and not you, but where you know you have this verifiable reward. We get so off track that we can't begin to converge again, but some simple course correction from a human would push you down the right track. That's what I want to avoid, but I guess that's always an experiment that can be run later?**

## Context

Follows the 9-paper lit review (5 original + 4 secondary) from `2026-04-21-lit-review-prompt-optimization.md` and the "Ideas to borrow from prior art" catalog in `docs/plans/paper-writeup-items.md`. Human asked to synthesize those learnings into system architecture + experiment framework decisions. Agent proposed the keep-vs-not breakdown and where borrows should land in existing plan docs; Human needs to resolve three open questions before doc edits happen.

This doc preserves the full synthesis for Human's return — not just the questions, because the decisions are easier to make with the keep-vs-not context visible.

## Keep vs. not — Agent recommendations

### Must adopt — bake into v1 before first curve runs
(Low cost, high value, multi-paper convergence.)

- **3–5 seed replication at every landmark, report mean±σ** — 5 papers convergent (MIPROv2, TextGrad, BetterTogether, OPRO, MASS). Non-optional for claiming v<N+1> > v<N>.**Agree**
- **Fixed-topology-by-design** as an owned design commitment — MASS contrast (they search topology), PromptBreeder §6 (they also fix it). Makes Claim B's narrowing principled, not defensive. **not sure what this means, clarify**
- **Best-score-so-far + variance-band figure grammar** for the headline figure — OPRO Fig 11 + MIPROv2 App G visual convention. Per-seed dots + best-so-far step + rolling mean + shaded variance + train-vs-held-out divergence. **yes**
- **Per-stage sub-scores in `validate_run.py` output** — DSPy trace-aware metric pattern. Emit extractor recall of candidate quotes, adjudicator conditional-F1 given good extraction, verifier flip rate — plus macro-F1. Enables attribution when v<N+1> moves. **dont fully know how DSPy trace-aware metric pattern works but makes some sense...**
- **`paper-trail-v<N>.json` archive artifact alongside the git tag** — DSPy `save()`, MA-SAPO App H, MAPRO App D. Contains {prompt hashes, signature specs, rubric examples, eval-arm tag, model aliases, settings.json hash, MCP config hash}. Grep-friendly diffs across versions; slots into `expected_invariants.json` (Task 5).**yes though what is MA-SAPO App H, MAPRO App D. ?**
- **Train/test seal + planning-session blindness** — our lead contribution (Claim C). No prior art in any of the 9 papers argues this. **yup.... still need to think of best practice for this. There's also another ind of leakage which is even within train, cant have the *agent* have label leakage**

### Adopt into the per-revision workflow
Structure the Human-Agent per-session revision process itself.

- **ProTeGi gradient template for Human's failure-mode write-ups** — App A.1.1. Per failed Sarol case: (a) paste examples with opaque citekeys, (b) enumerate N reasons in `<START>…<END>` delimiters, (c) each reason = candidate prompt-edit hypothesis. **What is this? ProTeGi gradient**
- **PromptBreeder mutation-operator menu as edit-proposal checklist** — Table 2, App C (36+ operators). Short checklist of edit-moves: "paraphrase," "add self-verification," "decompose," "re-describe." **elaborate**
- **MAPRO reversed-topology "blames" pass on failed examples** — §3.3. During revision session, run verifier-blames-adjudicator-blames-extractor critique. Better signal for which subagent's prompt to edit. **ya i like this, nice**
- **MIPROv2 seven-field proposer schema for revision-journal entries** — §3. Record `dataset_description`, `program_code`, `program_description`, `module`, `task_demos`, `previous_instructions`, `basic_instruction`, `tip` per revision. Makes human-driven revisions commensurable with any later automated optimizer.
- **OPRO ascending-order best-N context presentation** — §5.2 ablation. When surfacing prior `paper-trail-v<N>` prompts + macro-F1 to Human for the next revision, list worst→best so strongest prior anchors the new proposal.

### Adopt as paper-visual commitments
Defer implementation until after first landmark runs produce data, but commit to the figure/table design now so data is collected with presentation in mind.

- **Reflexion Fig 1 tri-column before/after trajectory figure** — paper-trail-v1 vs v2 vs v3 on one Sarol INDIRECT-detection example with red-highlighted wrong spans and green-highlighted corrected spans. Strongest methods-section visual.
- **Reflexion Fig 3b failure-mode decomposition stacked by revision** — Sarol failure-mode taxonomy (INDIRECT-miss, bib-only-ghost, year-mismatch, severity-under-commitment) stacked across revision index. Tests "human revisions retire one failure mode at a time."
- **Feature-matrix related-work table** — rows: Reflexion, Self-Refine, ProTeGi, DSPy/MIPROv2, OPRO, MAPRO, MASS, MA-SAPO, BetterTogether, ours. Columns: offline prompt iteration | human-in-the-loop | train/test split enforced | multi-agent pipeline | labeled external reward. "Train/test split enforced" is our unique column.
- **MASS Table 6 per-revision incremental-gain column table** — macro-F1 per paper-trail-v<N> with per-revision delta column.
- **MIPROv2 three-way ablation structure** — baseline | instructions-only | demos-only | joint. Isolates instruction-engineering from example-selection contribution. *Cost implication flagged as Decision 3 below.*

### Defer with milestone pin
High cost or blocked on decisions not yet made. Per memory `feedback_defer_with_milestone_pin.md`, each has an explicit pin.

- **Backbone portability ablation (Opus↔Sonnet↔Haiku) at v_final** — MASS Table 4. **Pin:** Task 6+ if budget allows; not in primary curve. **Yeah, I don't think this ablation is super interesting.**
- **Permutation ablation of subagent-revision order** — BetterTogether Table 1 shape. **Pin:** post-v_final; only if reviewers ask. **What does sub-agent revision order mean?**
- **Human A/B blind preference** — Self-Refine App C. **Pin:** blog-post-only if we want it; not paper-required.
- **Efficiency-vs-performance second figure** (token cost + wall-clock vs macro-F1) — MA-SAPO Fig 3. **Pin:** cheap once token-logging is in eval arm; bundle into Task 5 deliverables. **Right. Yeah, we definitely need to be logging the cost of all of these experiments throughout the process. I don't know if we want to build a trade-off curve of minimizing the cost of an experiment, but we should at least quantify it.So I believe we've already built that in.**

### Skip (explicit, with reasons)

- **LLM-as-loss secondary judge** (TextGrad §3.4). Reason: macro-F1 + per-class F1 is sufficient signal; adds eval-arm complexity (second pinned model alias, extra Tier 1 invariant) without clear ROI.**We don't need that.**
- **Bandit candidate selection** (ProTeGi UCB). Reason: only relevant if we automate variant sweeps, which is Escalation-ladder territory, not baseline.**Not sure what this means, but I'll take your word for it.**
- **Mutate-on-differences operator** (EvoPrompt §3.3). Reason: spirit already captured by the broader "mutation-operator menu" borrow; separate operator adds workflow ceremony.
- **Reasoning-assets corpus formalization** (MA-SAPO §3.2). Reason: our journal entries already do this informally; formalization adds process overhead without paper-benefit over just citing the journal structure.

## Where this lands in existing docs (Agent proposal)

No new docs, to avoid proliferation. Four existing docs absorb the borrows:

- **`experiment-sarol-archive-and-eval-framework.md`** — all "must adopt" items + paper-visual commitments. This is the architecture reference and the natural home.
- **`experiment-sarol-optimization-loop-hygiene.md`** — revision-workflow items land here as a new **Rule 3** section (extending the existing Rule 1 / Rule 2 structure rather than creating a new file).
- **`experiment-sarol-methods-research.md`** — deferred items with their milestone pins.
- **`NEXT.md`** — Task 5 (eval arm build) deliverables expand to include the must-adopt list; Task 6 (first curves) gets the v1-gate checklist.

`paper-writeup-items.md` already has the full borrow catalog from the previous pass — it doesn't need more edits in this round.

## Three decisions pending Human sign-off

### Decision 1 — Revision-workflow doc placement

Where do the revision-workflow borrows (ProTeGi template, mutation-operator menu, reversed-topology blame, MIPROv2 seven-field schema, OPRO ascending-best-N) live?

- **Option A (Agent lean):** new **Rule 3** section in `experiment-sarol-optimization-loop-hygiene.md`. Extends the existing Rule 1 (subagent sandboxing) + Rule 2 (main-session blindness) structure. Keeps doc count flat.
- **Option B:** new file `experiment-sarol-revision-workflow.md`. Cleaner separation, but adds a doc.
- **Option C:** docstrings / templates committed alongside the subagent prompts in `experiments/sarol-2024/prompts/`. Most-distributed; least-discoverable for a fresh reader. **Let's make some decisions first per above and then start talking about where to document things. These are documentation ideas around how to run this experiment. I think, generally, my lean is one document that then can point to a hierarchical goal directory of other ND files that contain unit-ish pieces of information that are discoverable by the main document. This way we don't just have ever-expanding single files, but we also don't have the problem of undiscoverable files.It also depends on what the intention of this is for, and so some of this is going to be plan docs or building specs. Some are going to be references for people, so I haven't fully decided yet.**

**Agent lean: A.** Matches the existing Rule 1 / Rule 2 pattern; the workflow items are operationally hygiene-adjacent (they constrain *how* the Human revisor works, the same way Rule 2 constrains what the Human revisor can see).

### Decision 2 — v1 gate list

Which borrows MUST block `paper-trail-v1` before we can run any curve? Everything else can roll into v2+ without invalidating the curve.

**Agent lean — five items gate v1:**

1. Seed replication (3-seed minimum) at the v1 landmark run
2. `paper-trail-v<N>.json` archive schema defined and emitted for v1
3. Per-stage sub-scores emitted by `validate_run.py` for v1
4. Train/test seal in place and validated (already done, just confirm)
5. Planning-session blindness mechanism (Q9c — `--bare` candidate, sanity-check pending)

Items deferred past v1 (roll into v2+ without invalidating):
- Fixed-topology-by-design framing — paper-writeup concern only, doesn't affect evals
- Figure grammar / visual commitments — needed before paper submission, not before v1
- Three-way ablation — cost-heavy (Decision 3)
- All deferred-with-pin items above

**Agree with the five-item v1 gate, or adjust?** Important: Q9c still ON HOLD; if the memory-blind mechanism sanity-check fails, v1 blocks until resolved. Currently that's the critical-path item.

### Decision 3 — Three-way ablation frequency
**I don't fully appreciate what this decision means either, sorry.**
MIPROv2 Table 1 structure (baseline | instructions-only | demos-only | joint) isolates whether our gains come from instruction-engineering vs example-selection. Reviewers will ask. But running it at every N-landmark ≈ 3× the compute (four conditions per landmark instead of one).

- **Option A (Agent lean):** run three-way ablation ONLY at v_final. Our primary curve is the "joint" column across v1…v_final; the single-lever conditions run once at the end for the ablation table.
- **Option B:** run at every landmark. Complete attribution across the curve, expensive.
- **Option C:** run at v_final + one mid-curve landmark (e.g., v3 or wherever we see a big F1 jump). Compromise.

**Agent lean: A.** Compute cost matters; the question "does revision order of concerns matter (instruction vs demo)" is a one-time question at the locked candidate, not a per-revision question.

## Restart instructions for Human (post-meetings)

1. Re-read the "Keep vs. not" section above with fresh eyes. Flag any borrow Agent classified that you want reclassified (e.g., promote "skip" → "must adopt," demote "must adopt" → "defer").
2. Answer the three decisions — A/B/C for each. Agent's leans are documented; overriding is fine.
3. Once resolved, Agent will draft the doc edits in one pass across the four target docs.

## Pointer to full context

- 9-paper borrow catalog with adopt-cost + citation-class per item: `docs/plans/paper-writeup-items.md` §"Ideas to borrow from prior art (with provenance)."
- Secondary lit-review verdict table: `docs/plans/paper-writeup-items.md` §"Net lit-review verdict (2026-04-21, updated after 9-paper pass)."
- First-pass novelty pass journal: `docs/journal/2026-04-21-lit-review-prompt-optimization.md`.
- Archive-framework authoritative: `docs/plans/experiment-sarol-archive-and-eval-framework.md`.
- Hygiene rules authoritative: `docs/plans/experiment-sarol-optimization-loop-hygiene.md`.
