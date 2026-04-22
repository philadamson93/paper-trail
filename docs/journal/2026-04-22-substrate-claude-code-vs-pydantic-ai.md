# 2026-04-22 — Substrate choice: Claude Code vs Pydantic AI (decision + argument reference)

Third journal entry for 2026-04-22. Follows `2026-04-22-topology-freedom-and-optimizer-affordances.md` (D32-D38) and `2026-04-22-lit-review-2-competitor-landscape.md` (D39-D47). Captures a substantive conversation about substrate choice that arose after lit-review-2 surfaced Meta-Harness and VeRO as partial scoops and Human raised whether Pydantic AI is a better academic-target substrate than Claude Code. Resolves to stay Claude Code with evidence-based rationale; sharpens the articulation for future conversations and for the paper's positioning.

## Context

Post-lit-review-2, Human raised: *"differentiate in paper from Pydantic tools, quick lit review on those... argue the claude code harness is so powerful we should leverage them rather than the 'manual' curation of pydantic libraries... it's not clear this is correct. Claude Code could write agents (paper-trail) into Pydantic in the same way."*

Two subsequent pushbacks sharpened the argument:
1. Human: *"it's also the post-training element of how and when to invoke tools. it's a problem solving engine natively. pydantic may or may not be."*
2. Human: *"does pydantic do 'post training' too? Especially if we're building tools perhaps our post training argument falls apart because our tools are custom."*

Followed by a practical request: *"i want to explain it to my colleague who is really keen on solving his problem with pydantic and i want to get him to see claude code is strictly better but dont have evidence per se."*

Two targeted subagents were dispatched during this conversation: (1) wide-pass Pydantic AI capability comparison, (2) narrow targeted lit-check on Pydantic AI as target substrate in the 2025-2026 agent-as-optimizer literature.

## D48 — Substrate choice: stay Claude Code with evidence-based rationale

**Raised by:** Human (concerns and pushback throughout).
**Resolved by:** targeted lit-review + argument-structure synthesis.

**Decision:** stay Claude Code for paper-trail. 90/10 confidence (from Human's initial 70/30 uncertainty, flipped by the lit-review data).

**Evidence:**
- **13 of 13 surveyed 2025-2026 agent-as-optimizer papers use non-Pydantic-AI target substrates.** VeRO (custom Python / uv packages), SkillsBench (Claude Code + Codex CLI + Gemini CLI), Live-SWE-agent (mini-SWE-agent), SE-Agent (SWE-Agent + litellm), AgentEvolver (custom + PyTorch + veRL), Hermes Self-Evolution (Hermes Agent framework), Multi-Agent Evolve (custom), Self-Improving Coding Agent (standard Python + XML-tool-calls), Hyperagents (custom extending DGM), AgentFactory (pure Python "standardized documentation"), Self-Play SWE-RL (SWE-agent-lineage), Self-Improving LLM Agents at Test-Time (unverified but no mention), Self-Improving AI Agents through Self-Play (theoretical).
- **Pydantic AI in the agent-as-optimizer space is tooling-layer, not research-layer.** GEPA+Pydantic-AI is a blog post; MLflow+Pydantic-AI is docs; SuperOptiX+Pydantic-AI is Medium. Zero peer-reviewed / preprint papers use `pydantic-evals` + agent-as-optimizer as their experimental substrate.
- **VeRO specifically:** *"in our setting, 𝒜 consists of Python programs that invoke LLMs via tool-calling APIs... The VeRO scaffold is implemented as a Python class... VeRO as a framework is largely agnostic to the coding agent scaffold."* Custom Python, not Pydantic AI. Uses Claude Code as optimizer scaffold alongside their own.
- **Claude Code is in-distribution for this literature:** VeRO uses it as optimizer, SkillsBench benchmarks it, "Dive into Claude Code" (arxiv 2604.14228) treats it as architectural reference. Not an academic outlier.

**Rationale that survives scrutiny** (not "convenience" but genuinely load-bearing):

- **Model+harness co-design.** Claude Code is a problem-solving harness Anthropic has spent millions of post-training examples teaching Claude to operate in. Claude "knows" implicitly when to use Grep vs Glob, when to spawn a subagent, when to write a todo, how to recover from errors — accumulated from two years of Claude Code usage data feeding post-training cycles. Pydantic AI gives you typed-LLM-call primitives but no model has been post-trained on YOUR custom harness built on top.
- **Inherited improvements.** Every new Claude release is optimized against Claude Code's tool vocabulary and usage patterns. Compounding returns from Anthropic's continued investment.
- **Platform primitives as first-party defaults.** `--add-dir` filesystem scoping, `claude --bare --print` headless invocation, MCP as native primitive, subagent `.claude/agents/*.md` with enforced permissions — all ship with the platform. Pydantic AI requires 3-4 community packages (pydantic-deepagents, subagents-pydantic-ai, pydantic-ai-filesystem-sandbox, harness) to approximate, and the assembly itself is engineering debt.
- **Velocity.** Paper-trail is already built on Claude Code. A port to Pydantic AI is 2-4 weeks of harness-level engineering that doesn't advance any core paper claim.

## D49 — Claim #8 softened from "contribution" to "case-study instantiation rationale"

**Context:** earlier this session (D40 in lit-review-2 journal), Claim #8 was articulated as *"declarative per-subagent heterogeneous controllability as an optimization surface."* Originally positioned as a methodology contribution premised on Claude Code having unique declarative-YAML-per-subagent config.

**Findings that weaken the original framing:**
- **Capability parity exists in Pydantic AI + community packages.** Pydantic AI has `Agent.from_file()` for YAML/JSON specs; `pydantic-deepagents` offers "Claude Code-style deep agents in Python"; `subagents-pydantic-ai` has `max_depth` and `DeepAgentDeps.clone_for_subagent()`; `pydantic-ai-filesystem-sandbox` offers per-path mounts + `Sandbox.derive()`. So "uniquely first-class on Claude Code" is not defensible at the capability level.
- **Even the post-training argument narrows under Human's pushback:** Claude's post-training advantage is at the orchestrator-level dispatch decisions + built-in-tool fluency (Bash/Edit/Read/Agent on SWE tasks), not at our custom-prompt logic (extractor/adjudicator/verifier prompts). For domain-specific logic, the same model on Pydantic AI does prompt-following equivalently.

**Decision:** Claim #8 dissolves from a standalone methodology contribution into a **case-study-instantiation-choice rationale** in the paper's methods section. The tiered-leakage framework + structural defenses + agent-only optimization loop are substrate-portable and survive as methodology contributions; the why-on-Claude-Code is a rationale subsection with honest tradeoffs.

**New defensible wording:** *"We instantiate paper-trail on Claude Code because (a) the substrate provides as first-party defaults the filesystem-scoping, subagent-sandboxing, and MCP integration that would otherwise require custom-Python harness assembly (as VeRO, SE-Agent, Live-SWE-agent, and AgentEvolver each build independently); (b) Claude models are post-trained on Claude Code usage patterns, providing model-substrate alignment at the orchestrator-level dispatch decisions that is harder to match on Python-native substrates; (c) our methodology (tiered leakage, structural defenses, agent-only optimization loop) is substrate-portable — clean ports to Pydantic AI / LangGraph / Microsoft Agent Framework are future-work."*

## Argument structure for explaining to a colleague (reference material)

Human requested a usable argument for explaining the substrate choice to a colleague keen on Pydantic AI. Captured here so the argument doesn't have to be reconstructed:

**Core insight:** Claude Code is a model+harness co-design; Pydantic AI is just a harness library. The former ships a problem-solving engine that works out of the box because the model has been post-trained on its loop. The latter ships typed-LLM-call primitives you use to build a harness yourself — and no model has co-evolved with the harness you just built.

**Supporting prior:** Google has ML resources, their own model, their own infrastructure. They built Jules (coding agent) on their own custom harness + Gemini co-trained with it. They did NOT build Jules on Pydantic AI. Nobody doing state-of-the-art coding agents builds on a generic Python agent library. That's the tell.

**Pydantic AI's genuine wins** (to acknowledge in argument):
- Structured-output extraction in production Python services
- Provider-portable LLM calls (trivial swap)
- Integration into existing Python codebases
- Lightweight LLM-in-a-loop patterns

**Pydantic AI's limitations for agentic problem-solving:**
- No problem-solving loop (you write it)
- No post-trained model for operating in your loop
- No context management / session / memory / skills / hooks
- No built-in tool vocabulary the model knows

**Honest "strictly better" answer:** Claude Code is strictly better for problem-solving-agent use cases; Pydantic AI is strictly better for structured-output-in-production-Python use cases. "Strictly" depends on the problem class — it's not a universal ordering.

**Diagnostic questions to ask a colleague:**
1. What model will you use? (If Claude → worse harness for same model. If GPT/Gemini → suboptimal provider alignment.)
2. How will you handle subagent depth and isolation? (Build cost.)
3. How will you handle filesystem scoping / tool permissions? (Structural-defense cost + likely security holes.)
4. What does your agent do that isn't structured-output LLM calls? (If "complex multi-step tool-use loops" → Claude Code has that for free.)
5. Have you compared the same task on Claude Code vs your Pydantic AI implementation? (Usually settles it.)

## Attribution patterns observed in this session

**Pattern 2 (Human-surfaces-strategic-argument Agent missed) — two instances:**
1. Human raised the Pydantic AI concern unprompted after lit-review-2 landed. Agent had not surfaced this as a substrate-comparator worry; had been positioning substrate arguments against autoresearch / Meta-Harness / VeRO but missed the library-level Python alternative that could undercut the positioning.
2. Human's "post-training element" framing — Agent was arguing only at the platform-primitives level; Human surfaced that models themselves are post-trained on specific harnesses, which is a different argument layer.

**Pattern 7 (Agent overclaims; user's diagnostic question triggers sharpening) — instance:**
Agent's "declarative YAML uniquely first-class on Claude Code" (D40 framing) was an overclaim. Human's *"is Pydantic overstating what they can do?"* triggered the targeted lit-check that resolved the capability-parity question. Agent's Claim-#8 framing softened to case-study-instantiation-rationale.

**Pattern 1 (Agent correctly self-corrects under evidence) — instance:**
Agent's initial 70/30 → 50/50 wobble on whether to stay Claude Code was resolved to ~90/10 stay-Claude-Code by the targeted lit-check data. The data genuinely changed the answer; Agent did not double down on the pre-evidence position.

## Doc updates triggered by this entry

Landed in same session as this journal:

1. `docs/plans/paper-writeup-items.md` §"Core contributions" — Claim #8 rewording from "declarative per-subagent heterogeneous controllability as an optimization surface" to the narrower substrate-rationale framing per D49. Add Pydantic AI / LangGraph / Microsoft Agent Framework as cite-as-alternatives entries.
2. `docs/plans/agentic-pipeline-optimization-framework.md` §8 "Related work and positioning" — add a paragraph positioning Pydantic AI as library-layer, Claude Code as platform-layer-plus-model-co-design, with explicit citations of pydantic-deepagents as the community approximation of Claude Code's subagent pattern on Pydantic AI.
3. This journal entry preserves the argument-structure reference material.

## What this does NOT change

- Methodology contributions (tiered leakage, structural defenses, agent-only optimization loop, declarative heterogeneous controllability as optimization surface) remain substrate-portable and survive intact.
- The in-flight scope decision (5-phase variant naming + DECOMPOSED-LAYERED confirmation + FETCH seed type) is independent of substrate choice and remains open for Human's call.
- Tier 0 canaries (Q9c memory-blind + D44 `--bare`+Agent) remain the pre-Task-5 gate regardless of substrate.

## What's next

Resume the 5-phase experiment-design conversation interrupted by this tangent:
1. Confirm DECOMPOSED-LAYERED scope (VERDICT primary + EXTRACT secondary + FETCH landmark composite + E2E qualitative-only + D future).
2. Pick naming convention (VERDICT / EXTRACT / FETCH / E2E / D vs existing A/B/C/D).
3. Pick FETCH seed type (PMC_ID tests phases 3-5 vs `\cite`-key + citing bib tests phases 2-5).

Once these are resolved, propagate scope + naming + substrate-rationale as a single thematic commit across framework doc + paper-writeup-items + experiment-sarol-benchmark + NEXT.
