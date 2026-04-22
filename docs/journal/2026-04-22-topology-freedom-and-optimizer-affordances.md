# 2026-04-22 — Topology-freedom as positioning; optimizer affordance catalog

First journal entry for 2026-04-22. Session opened with the clarifications list Agent owed Human from 2026-04-21-end-of-night (seven explainers). Item #1 — "fixed-topology-by-design" — surfaced a disagreement that reoriented the paper's positioning and surfaced an initial spec for the optimizer agent's affordances.

**Authoritative spec:** `docs/plans/agentic-pipeline-optimization-framework.md` — updated in the same session with a new subsection in §3 (Architecture) capturing the optimizer-affordance content and an explicit note on topology-freedom.

## D32 — Topology is a free variable for the optimizer agent

**Raised by:** Human.
**Exact quote (condensed):** *"the concept that we have three agents is somewhat arbitrary in my opinion. I think that tasks exist at varying levels of hierarchy… we're testing the entire gigantic system, and it should be able to choose to do whatever it wants in this playground… Claude Code makes it very easy for it to add agents that do whatever it wants. It's not expensive. We're fixing the number of epochs, right? The extent to which it chooses to do more within an epoch, I'm not super worried about it."*

**Agent acknowledgement:** Agent had imported "fixed-topology-by-design" from the 9-paper prior-art cluster (PromptBreeder §6, MASS contrast) as a top-priority adopt in `paper-writeup-items.md` §"Top-priority adopts" item #2. That framing was internally inconsistent with the Q1 monolithic-tagging rationale Human had articulated 2026-04-21: *"it is not clear that our final solution will have three prompts, and it is not clear that those three prompts will be adjudicator, extractor, and verifier."* Q1 already committed to topology-freedom; the lit-review borrow contradicted it. Miss on Agent's part — the borrow catalog did not carry Q1's reasoning through.

**Decision:** the extractor/adjudicator/verifier trio is **seed knowledge from where paper-trail-v1 starts**, not a design commitment. The optimizer may restructure freely across revisions: split a prompt, combine prompts, create new prompts, add subagents, drop subagents (including the verifier if it discovers the verifier adds no information), add tool calls, change hand-off edges, etc. Per-revision budget is the fixed unit; within-revision cost of whatever structure the optimizer chooses is the optimizer's prerogative to spend.

**Framework-doc consistency:** the framework's dispatcher/subagent architecture (§3) is already topology-agnostic — the dispatcher spawns one `/sarol-eval-item` per Sarol example, and paper-trail-v<N> internally may fan out to any number of subagents and tool calls. D32 surfaces the implicit property and names it explicitly.

## D33 — Positioning: Claude Code substrate + verifiable reward

**Raised by:** Human.
**Exact quote:** *"it's much easier to do so than it was in 2024 or whenever that paper was… [the prior-art papers] are doing topology search explicitly. Here, the point is just to give Claude Code a verifiable reward and let it do whatever it wants. That may be topology search; it may not be. It's not this hand-crafted optimization. It is pure agent-driven decision making towards a verifiable reward, and that's it."*

**Agent synthesis:** the paper's related-work structure reorganizes into three buckets:

| Regime | Example | Topology handling |
| --- | --- | --- |
| Hand-crafted fixed topology | PromptBreeder, DSPy/MIPROv2, BetterTogether | Topology committed by the researcher; prompts optimized |
| Hand-crafted topology search | MASS | Topology also optimized, but the search *procedure* is itself hand-crafted |
| **Ours** | paper-trail-v<N> on Sarol | Topology is a free variable for the optimizer agent; framework does not prescribe a search procedure or a topology commitment |

**Framing language (for paper methods / related work):** *"Claude Code enables arbitrary multi-agent restructuring at negligible engineering cost. The 2023–2024 prompt-optimization literature worked in substrates where adding or removing a pipeline node incurred framework friction; fixed topology was partly a response to that friction, not a theoretical commitment. In our substrate, that friction is gone. We therefore step out of the way: the optimizer receives a verifiable reward and full freedom over the pipeline's structure."*

**Decision:** adopt this framing across `paper-writeup-items.md` (drop the fixed-topology top-priority adopt, replace with the three-bucket positioning) and in the framework doc's §1 (motivation) as additional context.

## D34 — Optimizer initial affordance catalog

**Raised by:** Human.
**Context:** natural extension of D33 — if the optimizer is free to restructure, it needs to know what "free to restructure" means. Human enumerated concrete actions to seed into the optimizer's initial system prompt so the optimizer does not conservatively default to prompt-text-only edits on the extractor/adjudicator/verifier trio.

**Affordance catalog (Human-articulated, for optimizer init):**

- Split a prompt into multiple distinct components.
- Combine prompts.
- Create new prompts entirely.
- Add tool calls within subagent dispatches.
- Search the internet for specific MCPs that might be helpful.
- Run web searches for literature on a specific problem the optimizer has encountered (including meta-strategy lit — "what's a more efficient way to keep sub-agents on track").
- Run web searches for specific data when the optimizer suspects the train labels are wrong — with an explicit guard: *do not overfit on this information*; the test set is the ground truth and train labels are not to be corrected into alignment with the optimizer's priors.
- Use whatever tools are available in the Claude Code environment.

**Philosophy (Human-articulated):** *"optimize for performance of the optimizer, not cost of the optimizer. This optimization step is relatively inexpensive compared to the enormous number of experiments that we will run with subagents… If it thinks it can make a better system by thinking longer and then it's going to go spin out a hundred sub-agents to actually solve the problem, that's time well spent."*

**Anti-pattern to fight — Python-default reflex.**

**Human:** *"stop writing so much Python code, because they default to just writing bespoke scripts to solve very, very specific problems. Think of it more agentic: code can be written on the fly if needed. You can have a library of Python tools, but entry points should always be agentic. Submodules should be agentic; it's an agentic framework."*

Claude Code's training distribution tilts the model toward writing bespoke Python scripts when asked to solve an operational problem. The optimizer's initial system prompt must push back explicitly: Python is a library; agentic tool-use is the entry point. Scripts should be built only when agentic approaches have been considered and rejected, not as the default reflex.

**Decision:** D34 partially specifies the Tier 1 invariant flagged as `agentic-pipeline-optimization-framework.md` §7 open problem #10: *"What counts as 'the optimizer agent'? Its system prompt, its tools, its `--add-dir` scope, its initial context — all of these are Tier 1 invariants for reproducibility. Needs a schema (folds into the `paper-trail-v<N>.json` archive artifact)."* The affordance catalog, the performance-not-cost philosophy, and the fight-Python-default guidance all live in that schema. Full schema still owed; content is now partially specified.

## D35 — Orchestrator tool-space vs subagent tool-space asymmetry (paper observation)

**Raised by:** Human.
**Exact quote:** *"the set of tools that the orchestrator agent may or may not use to build the sub-agents far exceeds the tools the sub-agents of paper-trail itself will end up using. Sub-agents of paper-trail don't need to do literature reviews of best ways to keep sub-agents on track, for lack of a better term."*

**Agent synthesis:** the optimizer's toolset (web search, MCP discovery, lit review, spawning exploratory subagents to test-drive candidate changes, writing prompts and scripts, proposing new pipeline shapes) is materially richer than what paper-trail-v<N>'s deployed subagents need (evidence extraction on a single cited-paper chunk, 9-class verdict adjudication, spot-check verification). The *experimenter-agent* and the *experiment-agents* operate at different levels of agency. This asymmetry is a paper-worthy observation.

**Decision:** add as a thread in `paper-writeup-items.md` under a new "Meta-observations on the framework" subsection. Paper observation, not a primary contribution — it sharpens the methods/discussion but does not stand as its own contribution claim.

## D36 — Trace-aware metric is optimizer-owned, not frozen eval infrastructure

**Raised by:** Human, during clarification-list item #2 (DSPy trace-aware metric).

**Context:** Agent walked through the DSPy `metric(example, pred, trace=None)` pattern and proposed adopting it for per-stage sub-scores (extractor recall / adjudicator conditional F1 / verifier flip rate) in `validate_run.py`. Agent flagged a complication: if we hard-code these three sub-metrics by name, we re-fix the topology through the back door of the metric schema — which contradicts D32 (topology-freedom). Agent proposed a "per-declared-stage manifest" adapter to resolve it.

**Human correction:** the metric shouldn't be part of the frozen eval arm at all. It is the **optimizer agent's own tool**, used for logging, debugging, and deciding what to do next. Seeded at v1 with the DSPy trio; mutable as paper-trail-v<N>'s topology evolves.

**Exact quote (voice-to-text, interpreted):** *"We should suggest to the agent to use this DSPy metric thing and to structure it in this way. We can indeed seed it in that way. The agent should know that, if it changes the topology and it is free to do so, it needs to change this DSPy signature. That's fine. The DSPy thing is purely for the agent orchestrator's own use, for logging the experiment itself and debugging and deciding what to do next. It is not a static tool, per our decision previously."*

**Decision — the split between eval arm and optimizer:**

- **Eval arm (Tier 1 frozen, topology-agnostic):** emits raw per-subagent traces — full inputs/outputs for every subagent invocation on every claim — plus macro-F1, per-class F1, confusion matrix, cost/latency. Schema is stable across all paper-trail-v<N>. No pre-computed per-stage sub-scores.
- **Optimizer agent (mutable, version-aligned with paper-trail-v<N>):** owns sub-metric definitions. Seeded at v1 with the DSPy pattern targeting the extractor/adjudicator/verifier trio (extractor recall, adjudicator conditional F1 given good extraction, verifier flip rate + flip precision). When the optimizer restructures, it rewrites the metric to match — dropping sub-metrics for stages it removed, adding sub-metrics for new stages.

**Properties this gives us:**

1. **No schema-adapter infrastructure** for cross-version comparison — the optimizer writes version-aware analyses when it wants them. Example: *"v5 collapsed extractor+adjudicator into a combined_judge; compare v5's combined_judge F1 against v4's adjudicator F1."*
2. **Retrospective reproducibility intact** — eval arm emits raw traces as the invariant; a future reproducer at time=100 applies whatever metric they want to paper-trail-v2's traces. Historical optimizer metric choices live in git.
3. **Clean tier separation** — val dispatcher remains scalar-only regardless of what metric-evolution the optimizer has done. Per-stage sub-scores never flow back via val.

**Repo location (proposed, pending Task 5 scoping):** the optimizer's metric code lives under something like `experiments/sarol-2024/optimizer/metric-v<N>.py`, versioned alongside paper-trail-v<N>. Not in `experiments/sarol-2024/eval-harness/` (that's Tier 1 frozen). The pre-commit hook that enforces eval-harness immutability does NOT cover the optimizer workspace — the optimizer is expected to mutate its own metric over revisions.

**Implication for Task 5:** `run_train_eval.py`'s rich-schema output is *raw traces + aggregate F1s*, not pre-computed per-stage sub-scores. Adjust the Task 5 deliverable list in NEXT.md accordingly.

**Implication for optimizer initial prompt (D34 catalog extension):** the affordance catalog gains a seeded-artifact — the v1 trace-aware metric template — that the optimizer is told it owns and can modify. Framework doc §3 "Optimizer agent initial configuration" updated with a reference.

**Degree of enforcement — purely agentic, transparency-only norm.** Raised 2026-04-22 during the D36 discussion. The optimizer's metric sits squarely in the agent's circle: no rigid schema, no minimum-sub-score requirement, no validator that refuses runs on metric non-conformance. Reasoning: the metric is the optimizer's *interpretive lens* on runs, not the measurement itself (macro-F1 is the measurement, produced by `parse_verdict.py` in the eval arm). Raw-trace emission at Tier 1 is the safety net — any sub-score we care about at paper-writing time can be recomputed from the archived traces post-hoc, regardless of what metric the optimizer was running at the time. Parallel to the 2026-04-21 call (archive-framework doc §"What Tier 1 deliberately does NOT include") that moved tool permissions and MCP servers off Tier 1 for the same reason: system-design surface captured by the git tag, not a measurement invariant. Only norm: the optimizer's metric code is archived per revision with paper-trail-v<N> for transparency — not enforced.

## D37 — Paper appendix publishes framework-reproducibility artifacts, not case-study prompts

**Raised by:** Human, during clarification-list item #3 (MA-SAPO App H / MAPRO App D).

**Context:** Agent walked through the MA-SAPO / MAPRO convention of publishing verbatim per-agent prompts in the paper appendix and proposed we do the analog — publish `paper-trail-v1` and `paper-trail-v_final` subagent prompts (extractor/adjudicator/verifier at v1, whatever topology at v_final) in the appendix for reproducibility.

**Human correction:** per-revision subagent prompts are epoch-dependent case-study artifacts. They change constantly as the optimizer iterates. Putting them in a paper appendix baselines the paper against a snapshot that won't be current even by submission time, let alone after. Better: point readers to GitHub for the current state. What belongs in the appendix is the **framework's** reproducibility surface — the optimizer's initial instructions, the train/val/test hygiene spec, the headless-mode invocation spec — because those are the actual contribution and they change much more slowly than the case-study prompts.

**Exact quote (voice-to-text, interpreted):** *"I think this all goes on GitHub. I mean, sure, you can throw in supplementary material, but I'd rather just point people out to GitHub, because everything about paper-trail is going to change over the course of epochs. I suppose what we can include is maybe the instructions that we started with for the orchestrator itself, or some more information about the real contribution here, like more detailed implementation specs on train, val, and test hygiene, or running a specific thing in headless mode. That's the focus. The actual three agents as it stands now instructions, I think, is not the focus of the paper."*

**Decision — paper appendix contents:**

- **Include (framework-reproducibility, stable across epochs):**
    - Optimizer initial system prompt — D34 affordance catalog + performance-not-cost philosophy + fight-Python-default guidance. Tier 1 invariant per framework §3 "Optimizer agent initial configuration."
    - Tiered-leakage operational spec — filesystem layout, `--add-dir` scopes per role, dispatcher locked JSON output schemas.
    - Headless Claude Code invocation pattern — exact `claude --bare --print …` command + flag rationale + memory-blind mechanism.
    - Memory-blind canary design + result (once Q9c resolves).
    - Eval dispatcher CLI contracts — args, exit codes, output schemas (matches `/sarol-eval` I/O contract, non-deferrable per NEXT.md Task 5).
- **Do NOT include:** per-revision subagent prompts for paper-trail-v1 or any other v<N>. Those live on GitHub under `archive/paper-trail-v<N>/` and in the `paper-trail-v<N>.json` artifact. A reader who wants to reproduce a specific revision clones the repo and checks out that tag.

**Why this maps to MA-SAPO / MAPRO correctly:** their appendices publish their system's prompts because their system IS the contribution. Our framework is the contribution; our case-study system (paper-trail) is the proof-point. Publishing the framework's reproducibility surface in our appendix is the analog — same convention, different artifact because we have a different contribution claim.

**Consistency with the two-paper-split open decision:** if Paper A (framework) and Paper B (tool) split happens (logged 2026-04-22 in `paper-writeup-items.md` §"Open paper-level decisions"), D37 applies to *both* papers. Paper A's appendix publishes framework artifacts; Paper B (tool) would likely also point to GitHub for prompts since the tool itself is continuously evolving. Neither paper's appendix holds snapshot prompts for a frozen version.

**Implication for Task 5:** the `/sarol-eval` I/O contract (non-deferrable Task 5 deliverable per NEXT.md line 110) becomes the appendix's "eval dispatcher CLI contracts" section. The `expected_invariants.json` schema (the other non-deferrable spec) becomes appendix "Tier 1 invariant declaration format." Both are already scoped correctly; D37 just pins their paper-appendix destination.

## D38 — Don't seed the PromptBreeder mutation-operator catalog; cite-only

**Raised by:** Human, during clarification-list item #5 (PromptBreeder mutation-operator menu).

**Context:** Agent proposed — after reframing the pre-reframe "human checklist" borrow for the agent-only setting — to seed PromptBreeder's 36+ mutation-operator catalog (Table 2 + App C) in the optimizer's initial prompt alongside the ProTeGi template (D36-adjacent seeded pattern #2). Agent had even written the framework-doc §3 edit landing it as a third seeded pattern.

**Human pushback:** the catalog feels contrived and too manual; the pattern of seeding it may over-constrain the optimizer's thinking to prompt-text-only edits; is the empirical evidence that the specific 36-operator menu matters (vs just "an LLM does the mutation") actually strong enough to justify the attention-budget cost?

**Exact quote (voice-to-text, interpreted):** *"Do you think we need to revise the prompt a little bit, borrowing kind of the mutations it suggests, but perhaps I don't know, it maybe feels too manual. I'm not so sure how useful this is, to be honest with you. I think four made a lot of sense. I don't know, a lot of these feel a bit contrived. I mean, are these high-impact papers? It feels so manual… it's so prompt-specific. The failure mode thing I think was natural, but this, I don't know. What do you think? Push back?"*

**Agent concession — Human is correct.** The sharper distinction between #4 (ProTeGi, seeded) and #5 (PromptBreeder, not seeded):

- **ProTeGi template = structural pattern** (delimiter scheme for parseable output). Constrains *format* without biasing *content*. The optimizer reasons freely about what hypotheses to enumerate; the delimiters just make the output parseable.
- **PromptBreeder catalog = vocabulary catalog** (36+ named edit moves). Pre-structures the *content* of the optimizer's thinking. Even with an explicit "these are prompt-text-only; topology moves are also available" caveat, seeding the catalog spends the optimizer's attention budget on a 2023-era prompt-text-edit vocabulary that contradicts D32 topology-freedom by habit.

**Also:** PromptBreeder's own ablations don't isolate the catalog's value — they isolate the broader "LLMs can do mutation" finding. EvoPrompt §5.3 Table 6 ("random prompts nearly match top-performing initialization") is a weak empirical undercut to operator-diversity-as-a-value.

**Decision:** demote PromptBreeder from "seeded pattern" to "cite-as-prior-art, do not seed." Cite PromptBreeder for (a) the LLM-driven-mutation-is-viable finding, and (b) the fixed-topology contrast that already grounds borrow #2. Do not surface the 36-operator catalog to the optimizer. Leave the optimizer's edit-move imagination unconstrained.

**Framework-doc edit:** the third seeded pattern subsection added in an earlier edit of this same session is reverted; only the trace-aware metric (D36) and the ProTeGi template (D34/clarification-#4-landed) remain seeded.

**Paper-writeup-items edit:** PromptBreeder borrow reclassed to "cite-as-prior-art, do not seed" with the structural vs vocabulary distinction written into the rationale so future re-evaluation doesn't re-import the same reasoning flaw.

**Decision rule extracted (for remaining clarifications #6 and #7):** *does this borrow improve the optimizer's raw performance in a way that pays for its attention-budget cost, or does it just sound useful?* If the borrow is primarily a *content vocabulary* rather than a *structural pattern*, and its own paper's evidence base doesn't isolate the value of the specific content catalog, skip the seeding — cite only.

**Attribution pattern observed.** This is a crisp instance of **Pattern 2 — Human surfaces strategic argument Agent missed**. Agent imported the borrow from the 9-paper catalog with a plausible-looking post-reframe rationale; Human immediately saw that the borrow had a different *shape* (vocabulary not format) than #4 and that the rationale was sand. Without the pushback, a contrived seed would have landed in the optimizer's initial prompt and quietly narrowed its imagination. Worth preserving alongside yesterday's Pattern-2 instance (D32 topology-freedom).

## Deferred — cost-performance adjudicator

**Raised by:** Human.
**Exact quote (condensed):** *"if it was too expensive, the agent updates that, or maybe pulls in lessons to say, 'Hey, this was more expensive and it did better, but we could do it this way instead.'… maybe there needs to be a manager agent in that sense or an advisor agent, right? I don't know; I think we'll cross that bridge if we come to it for some reason."*

**Decision:** defer. The performance-vs-cost tradeoff is explicitly flagged as a future separate paper. Current framework optimizes for performance only; cost is recorded as a Tier 2 logged condition (framework §7 open problem #8 already covers cost accounting) but is not an input to optimizer decisions. Current paper discloses this choice honestly and names the future paper direction. Per memory `feedback_defer_with_milestone_pin.md`: **Pin:** separate paper on performance-cost tradeoff curves; not this one.

## Attribution patterns observed in this session (for the future human-value retrospective paper)

**Pattern 4 (Agent-enumerates-Human-articulates) — both directions in one exchange.**

Two opposite instances of Pattern 4 showed up in this single clarifications-list turn:

- **Agent→Human, raising the question.** Agent's 2026-04-21 lit-review synthesis distilled "fixed-topology-by-design" as a top-priority adopt. Human had not read the 9 papers, Agent had, and produced a defensible-looking framing. The framing was internally wrong — it inherited a 2023-era substrate constraint that doesn't fit Claude Code — but it was the concrete prompt Human needed to push back against. Without Agent's distillation, Human would not have had the target; without Human's substrate argument, Agent's distillation would have carried forward into the framework doc.
- **Human→Agent, articulating the principle.** Human enumerated the optimizer affordance catalog (D34) in one continuous verbal pass. Agent will now enumerate the attack-surface implications, operational specifics, and Tier 1 invariant schema.

**Human self-attested 2026-04-22:** *"a lot of the seventh bullet points of what problems to solve and raising these questions was from you. It's this: hey, you prompt me with an idea. Oh, I hadn't thought about specifying that, right, so there is this back and forth, very clearly, because I didn't read those seven papers, to be honest with you, you did."*

Worth preserving for the future retrospective paper: the decision mechanism here is not Human-corrects-Agent nor Agent-enumerates-Human alone — it is the *combination* in both directions that produces the resolved framing. Neither contributor alone would have arrived at D33/D34.

**Pattern 5 (Human-catches-Agent-imprecision) — continuing from 2026-04-21.** Agent's "fixed-topology-by-design" framing was an imprecision: it inherited prior-art wording without testing fit to Q1. Pattern 5 from yesterday predicted this class of failure; it surfaced here in a different content area.

## Doc updates made in this session after this journal entry

1. `agentic-pipeline-optimization-framework.md` — new subsection within §3 (Architecture) titled "Optimizer agent initial configuration" capturing D34 (affordance catalog, performance-not-cost philosophy, fight-Python-default guidance). Also: brief explicit note under §3 Components that the subagent count/roles internal to paper-trail-v<N> are free and can vary across revisions. §7 open problem #10 annotated with a pointer to the new §3 subsection.
2. `paper-writeup-items.md` — top-priority adopt #2 (Pipeline-topology-fixed-by-design) removed; replaced with a topology-freedom positioning item that names the three-bucket related-work structure from D33. New "Meta-observations on the framework" subsection added capturing D35 (orchestrator vs subagent tool-space asymmetry).
3. `NEXT.md` — Task 7 backlog item on framework §7 open problems annotated with a pointer to this journal entry for the optimizer-initialization partial spec.
4. Memory: new `project_paper_positioning_topology_free.md` capturing the D32/D33/D34 framing so future conversations start aligned.

## What's next (session plan for today)

Clarifications list continues from #2 (DSPy trace-aware metric) after these doc updates land. Remaining clarifications: #2 DSPy trace-aware metric, #3 MA-SAPO App H / MAPRO App D, #4 ProTeGi gradient template, #5 PromptBreeder mutation-operator menu, #6 subagent revision order, #7 bandit candidate selection. Then framework §7 open problems. Then Q9c memory-blind canary. Then Task 5 scoping.
