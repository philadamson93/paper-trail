# 2026-04-21 — Agent-only reframe + tiered leakage framework decisions

Third and largest journal entry for 2026-04-21. Captures the load-bearing architectural decision that reshaped the paper's framing: the experiment is **agent-only** from this point on, and the primary contribution becomes a **framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline**, with paper-trail + Sarol as the case study. Human-in-the-loop is deferred to a future separate paper.

Follows `2026-04-21-archive-framework-decisions.md` (morning — archive + eval framework) and `2026-04-21-lit-review-prompt-optimization.md` (afternoon — 9-paper novelty + borrow pass) and the synthesis / pending-decisions doc that preceded this one.

**Authoritative plan doc:** `docs/plans/agentic-pipeline-optimization-framework.md`. This journal entry is the decision log; the plan doc is the spec.

## Background context

Coming off the 9-paper lit-review synthesis, Agent proposed a keep-vs-not classification and three architecture questions for Human to decide. Human returned from meetings and made a bigger-than-expected call: the fundamental framing of the experiment itself is up for grabs. Human raised the question — **should this be agent-only (fully autonomous, verifiable-reward-driven) or human-in-the-loop (Human + Agent co-author revisions)?** — and leaned agent-only while flagging the divergence risk.

## Decisions made today

### D22 — Experiment is agent-only

**Raised by:** Human.
**Exact quote:** *"I think the human in the loop is messy. It's interesting from a human teaming perspective, but I think it's too messy; there's too much room for me, the user, to really interfere with what's going on. No one cares about the extent to which a human can build a system by learning good prompts, so it needs to be agent only from this point forward."*
**Agent response:** agreed, with reasoning that agent-only (a) strengthens Claim C because test-sealing becomes a structural system property rather than a human-discipline norm; (b) removes the reproducibility-hedge ("testing my engineering skill"). Noted two costs: substantially more engineering effort (optimizer-loop needs to be built out), and Claim A narrows further (x-axis is now agent-driven, competing more directly with OPRO/MIPROv2 than the human-driven framing did). Both accepted.
**Decision:** agent-only. The optimizer is an agent, not a Human + Agent pair. Planning-phase Human-Agent collaboration (this very session, for instance) continues but doesn't feed the current paper — it feeds a future separate paper on human-agent research collaboration.

### D23 — Framework is the primary contribution; paper-trail + Sarol is the case study

**Raised by:** Human.
**Exact quote:** *"This experimental infrastructure is critical to nail down before we begin and actually kind of is the project. Paper trail is just the example."*
**Agent response:** this is the right reframe. Paper's contribution stack reorders: primary = framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline; secondary = paper-trail + Sarol as instantiation. The specific prior findings (9-way Sarol baseline, INDIRECT-detection failure mode, severity-under-commitment, cost-per-claim numbers) become features of the case study, not standalone paper-level contributions.
**Decision:** reframe the paper around the framework. Update `paper-writeup-items.md` §"Core contributions" to order framework/architecture first, case study second. Landed in this turn.

### D24 — Three-tier leakage discipline (Train open / Val scalar-only / Test sealed)

**Raised by:** Human.
**Exact quote (condensed):** *"The optimizer agent has to be label-aware, but only in the sense that it's running deterministic Python files that read labels and compute F1 scores. At least in the sense of the validation set, the agent should not see actually really any of the examples in the validation set. It is simply a Python call. It doesn't have access to the data, does not read the data… It's not just train-test-val leakage; it's a little bit of val leakage, but even the optimizer shouldn't be able to access and look at the individual labels or examples in validation."*
**Agent response:** this is substantive and extends Claim C into novel territory. Prior hygiene discipline frames test-vs-everything-else; Human is articulating a finer-grained three-tier model where *even val* is structurally off-limits to the optimizer at the per-example level. The rationale (paraphrased): the optimizer is an optimizer; if it sees per-example val, it will find val-specific fixes that don't generalize, and that's a class of cheating that standard held-out evaluation doesn't catch. Agent formalized this as: `R(optimizer, train) = full`; `R(optimizer, val) = scalar`; `R(optimizer, test) = ∅ during iteration`. Structural enforcement via filesystem permissions + fixed-schema dispatcher CLIs.
**Decision:** adopt as the core of the framework. Tier 2 is the genuinely novel layer on top of standard held-out hygiene. Authoritative spec in `agentic-pipeline-optimization-framework.md` §2. Worth preserving Human's exact phrasing in the paper's methods section: *"trust generalizable fixes, not just feeding in answers like cheating on a test."*

### D25 — Optimizer agent architecture (three-tier agent hierarchy)

**Raised by:** Human, working through the mechanics out loud.
**Exact quote (condensed):** *"Agent only is still an optimization agent that separately spins off agents that run the tool and report back to the main optimization agent. The main optimization agent may very well run out of context, in which case it may choose, at perhaps some 200,000 token limit, to start a new agent. A new version of itself with enough memory to continue the experiment. The individual experiment arms that actually run paper trail are their own agents that always are starting with fresh context."*
**Agent clarification:** captured as: (1) optimizer agent (outer loop, long-lived, can self-respawn at context limits); (2) eval dispatcher (deterministic Python script, NOT an agent — dispatchers-as-scripts prevent an LLM from "helpfully summarizing" per-example val outputs back to the optimizer); (3) eval subagents (headless Claude Code, fresh context, `--bare`, uniform invocation for train / val / test). Output routing is what differs between splits, not subagent behavior.
**Decision:** adopted. Spec'd out in framework doc §3, §4, §5. Open problems (respawn protocol, handoff-doc schema, stopping rule) flagged in framework doc §7.

### D26 — Dispatcher-as-script, not agent

**Raised by:** Human, asking whether the eval dispatch layer needs to be its own agent or a script.
**Exact quote:** *"Unless we can make that scriptable in some way. Where, yes, it's a script that deploys sub-agents, but it only ever reports back the F1 scores and does not allow the main optimizer agent to look at what those sub-agents did to learn from what they did in every way."*
**Agent response:** script is strongly preferred. Reasons: determinism (no temperature, no judgment); no accidental helpful-summarization; schema-enforceable output; auditable source code. Agent dispatchers add leakage surface area for no benefit.
**Decision:** dispatcher is deterministic Python. `run_train_eval.py`, `run_val_eval.py`, `run_test_eval.py`. Locked JSON output schemas. Source-code-reviewable.

### D27 — Uniform headless-Claude-Code invocation across train and val

**Raised by:** Human.
**Exact quote (condensed):** *"I think the other question is, if we're running headless mode, we should probably run headless mode across all three sessions, even in train. We don't want divergent behavior between how train and val are implemented, just that the optimizer can see the logs from the headless state."*
**Agent response:** correct. Uniform subagent invocation (`claude --bare --print /sarol-eval-item ...`) for both train and val; what differs is output routing at the dispatcher layer, not subagent mechanism. Eliminates mode-divergence artifacts in measurement.
**Decision:** uniform subagent invocation. Framework doc §3.

### D28 — Correction on attack-surface-4: same subagent, different output routing

**Raised by:** Human, catching Agent's imprecise framing.
**Exact quote:** *"The paper trail slash command is run by both Val as well as train, obviously, but it's written by the optimizer. Are you saying that even if the optimizer asked to report Val, the sub agent it spawns is unable to do so when it's looking at train due to permissions? And it's able to do so when it's running on Val, but that's okay because it reports back a fixed schema in headless mode."*
**Agent acknowledgment:** I was imprecise in the initial architecture sketch. The subagent doesn't behave differently on train vs val. The dispatchers behave differently: train dispatcher returns full per-example traces to the optimizer; val dispatcher returns scalar F1 only. Same subagent, same dispatch prompt (edited by the optimizer), same `--bare` invocation. Only the dispatcher's output-routing differs. Cleaner, less surface area for mode-divergence.
**Decision:** adopted correctly in framework doc §3.

### D29 — From-scratch variant deferred

**Raised by:** Human.
**Exact quote:** *"I want to start from where we are now. To the extent that we want to start from scratch, we could try, but I think we need the knowledge that we've already accumulated in the structure that we formulated. I still think that's kind of interesting, but I don't know."*
**Decision:** defer. Framework doc §1 and §8 mark this as a separate experiment to run post-v_final if interesting; not in the main curve. Pin preserved per `feedback_defer_with_milestone_pin.md`.

### D30 — Human-agent collaboration retrospective → future separate paper

**Raised by:** Human.
**Exact quote:** *"I'll save it for a new paper, but this planning phase, I still think, is interesting: how we're working together, what you're coming up with, what I'm coming up with. We do want to remember to keep documenting that."*
**Agent response:** acknowledged. The "human-value-in-agentic-collaboration retrospective" as a current-paper contribution is dropped; the dataset continues to accrue in `paper-writeup-items.md` §"Human-value retrospective" and in journal-entry attribution. When/if the future paper happens, the material is there.
**Decision:** move to future separate paper. Continue the `**Human:**` / `**Agent:**` attribution convention in all future journal entries. Updated `paper-writeup-items.md` §"Human-value retrospective" to reflect the future-paper framing.

### D31 — Docs updated in a single pass after decisions resolved

**Raised by:** Human.
**Exact quote:** *"Yes, agree on everything. Sounds good. Let's get documenting and planning. Go."*
**Decision:** Agent wrote the framework plan doc + propagated the reframe across NEXT.md, the hygiene doc, paper-writeup-items.md, the pending-decisions journal entry (marked RESOLVED), CLAUDE.md (reading-path update), and wrote this journal entry. Single conceptual unit of work per the "one thing at a time" norm.

## Open problems explicitly named (framework doc §7)

Not decisions-made-today but decisions-owed-later, surfaced during this conversation:

1. **Optimizer self-respawn protocol.** Handoff-doc schema, respawn criterion, respawn budget. Agent's proposed mechanism (§5) is a first draft; needs pressure-testing once we start implementing.
2. **Stopping rule for the optimizer.** Patience window on val F1 vs. budget exhaustion vs. optimizer self-declared plateau. Not yet chosen.
3. **Dispatcher-bug risk.** The tiered-leakage discipline is structural modulo the dispatcher being bug-free. Mitigation via testing + code review + schema validation; not zero-risk.
4. **Initial seed knowledge for the optimizer.** Starts from existing paper-trail-v<N> prompts + journal-captured failure modes vs. starts from minimal seed? Deferred per D29 but not fully specified.
5. **Per-revision rationale capture.** The paper wants to report *what* the optimizer did at each revision, not just *that* it revised. Needs a schema for the optimizer's commit-message-equivalent.
6. **Framework validation empirically.** The N=10 agent-only de-risk smoketest (sidebarred) answers whether the framework actually works on Sarol before we commit to a full curve.

## What's sidebarred (explicit — not forgotten, not starting now)

Per Human's "one thing at a time" rule + explicit instruction to sidebar certain items during this reframe:

1. **Clarifications list** — Agent owes Human explanations of: fixed-topology-by-design, DSPy trace-aware metric pattern, MA-SAPO App H / MAPRO App D, ProTeGi gradient template, PromptBreeder mutation-operator menu, subagent revision order, bandit candidate selection. Pending; not blocking.
2. **N=10 de-risk smoketest design.** Deferred per Human: "I still think we're a little ways away from that."
3. **From-scratch variant (D29).**
4. **Human-agent collaboration retrospective → future paper (D30).**
5. **Memory-blind canary sanity-check (Q9c).** Still ON HOLD from earlier 2026-04-21 decision. Resume before Task 5 (eval arm build); framework doc depends on `--bare` working as documented.

## Attribution patterns observed in this turn (for the human-value retrospective future paper)

**Pattern 2 (Human-surfaces-strategic-argument) — strongest instance of the session.** Human surfaced the agent-only-vs-human-in-the-loop question, which Agent had not raised. Agent's entire prior planning (9-paper borrow catalog, keep-vs-not synthesis, three decision questions) assumed human-in-the-loop. Human reshaped the framing; Agent adapted. Without Human's framing question, the paper would have been pitched around human-driven revisions, which is the weaker framing given the scientific-hygiene argument.

**Pattern 4 (Agent-enumerates-Human-articulates) — inverted this time.** Normally Human articulates the principle and Agent enumerates instances. Here, Human articulated the val-leakage principle ("even the optimizer shouldn't be able to access and look at the individual labels or examples in validation") and Agent enumerated the attack-surface table + structural defenses. The direction of articulation can flow either way depending on whose expertise dominates the concern.

**Pattern 5 (new) — Human-catches-Agent-imprecision.** D28 (the attack-surface-4 correction). Agent's initial framing of "the subagent behaves differently" was sloppy; Human pinned it down to "same subagent, different output routing." Worth adding to the catalog: Human's implementation-level clarity exceeds Agent's when Agent is working at architecture-level abstraction. The human role here is keeping the architecture honest about its mechanism.

These patterns continue to accumulate as dataset for the future paper.
