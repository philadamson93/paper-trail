# Agentic pipeline optimization framework

**Top-level plan doc. Framework is the contribution; paper-trail + Sarol is the case study.**

**Status:** authoritative as of 2026-04-21. Supersedes the human-in-the-loop framing of earlier Sarol-experiment planning. See §"Relationship to existing hygiene rules" below for how prior rules map into this framework.

**Scope:** any agentic optimization of a multi-subagent pipeline with a verifiable reward signal. Paper-trail's citation-integrity pipeline (extractor / adjudicator / verifier) evaluated on Sarol-2024 is the current instantiation; the framework is deliberately benchmark-agnostic and pipeline-agnostic.

---

## 1. Motivation and reframing

### What was

Earlier planning framed the Sarol experiment as **human-in-the-loop** prompt iteration: Human (the researcher) and Agent (LLM-in-discussion) co-author prompt revisions, with the Sarol benchmark serving as verifiable reward. Novelty was pitched as (a) the human-revision-indexed train+val curve and (b) the hygiene principle of physically sealing test during researcher-in-the-loop iteration.

### What is

**Decision 2026-04-21 (Human):** the experiment is **agent-only** from this point forward. The optimizer is an agent (not a human + agent). Human quote: *"No one cares about the extent to which a human can build a system by learning good prompts, so it needs to be agent only from this point forward."*

**What the reframe changes:**

- **The contribution stack reorders.** Primary: a framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline. Secondary (case study): paper-trail + Sarol as the instantiation that demonstrates the framework works.
- **Claim B stays dropped as a standalone** (DSPy/MIPROv2 scooped it). Claim A (curve figure) narrows further — the x-axis is now *agent-driven revisions*, which loses the human-driven differentiator against OPRO Fig 11 / MIPROv2 App G. But Claim A keeps "train-vs-held-out divergence as explicit stopping rule" (OPRO defers this to future work) and "applied to a multi-subagent pipeline with tiered leakage discipline" (genuinely unclaimed).
- **Claim C gets structurally stronger.** "Physical sealing + policy-gated planning-session blindness" was a human-discipline norm. Now it becomes a *system property*: the optimizer is structurally unable to see test (Tier 3) and has only scalar access to val (Tier 2). Discipline enforced by filesystem permissions and output-schema validation, not trust.

### Why the reframe is load-bearing

- Scientific hygiene: a human-in-the-loop experiment conflates the method with the operator's skill. Agent-only experiments are the method; reproducibility is cleaner.
- Claim C strengthening: structural enforcement > human discipline.

### What the paper's framework-first framing looks like

- Title / lead idea: a framework for agent-only optimization of multi-subagent pipelines with structurally-enforced leakage discipline across train / val / test tiers.
- Proof point: paper-trail (a citation-integrity multi-subagent pipeline) evaluated on the Sarol-2024 benchmark demonstrates the framework works on a non-trivial real task.
- Method contributions: the tiered leakage model, the optimizer / dispatcher / subagent architecture, the structural defenses against leakage, and empirical evidence that an agent-only optimizer can drive measurable pipeline improvements without contaminating val or test.
- Not the contribution: paper-trail itself (as a product). Paper-trail is the example pipeline; if the framework generalizes, any labeled-benchmark pipeline could be the case study.

### What's deferred (explicitly, per `feedback_defer_with_milestone_pin.md`)

- **Human-in-the-loop comparison arm.** Future paper on human-agent research collaboration. Retrospective material on how the present paper was *planned* (human + agent collaboration during planning even though the experiment arm is agent-only) continues to be collected in `docs/plans/paper-writeup-items.md` §"Human-value retrospective" and in journal entries. Pin: separate paper, not this one.
- **From-scratch bootstrap** (no seed knowledge, agent builds paper-trail from zero). Separate experiment after first curve lands. Pin: post-v_final, separate arm. Human signal: "I want to start from where we are now."
- **Backbone portability** (Opus ↔ Sonnet ↔ Haiku). Pin: Task 6+ if budget allows.
- **Multi-benchmark validation** (framework on other labeled pipelines). Pin: after paper lands.
- **Cost-performance tradeoff curve for the case-study pipeline.** The current paper optimizes for macro-F1 only; cost-per-run is logged as a Tier 2 condition but is not an input to optimizer decisions. A manager-or-advisor agent that adjudicates cost-vs-performance tradeoffs during revision is an interesting follow-up but is **explicitly deferred**. Pin: future separate paper on cost-performance tradeoffs in agent-only pipeline optimization. See journal `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` §"Deferred — cost-performance adjudicator."

---

## 2. Tiered leakage discipline

The central design commitment. For any agent-only optimization with verifiable reward and a three-split dataset (train / val / test):

### Tier 1 — Train: fully open to the optimizer agent

Optimizer can read:
- Per-example train inputs (full text, not just opaque keys)
- Gold labels
- Per-example subagent traces (what extractor returned, what adjudicator decided, what verifier flipped)
- Failure-mode patterns extracted from traces
- Aggregate metrics (macro-F1, per-class F1, confusion matrix, cost)

This is where the optimizer learns. The discipline here is only Rule 1 (the *deployed subagents during eval* don't see gold labels — opaque citekeys + filesystem restrictions + scrubbed staging_info). But the optimizer itself, which reads eval outputs, has full train label access.

### Tier 2 — Validation: scalar-only to the optimizer agent

Optimizer can read ONLY:
- Aggregate val metrics: macro-F1, per-class F1 — scalars, returned via a fixed-schema CLI.

Optimizer CANNOT read:
- Per-example val inputs (no text, not even the opaque keys of val examples).
- Gold labels for val.
- Per-example subagent traces on val.
- Any failure-mode list or error analysis for val.
- Confusion matrices or any per-example aggregation of val.

**Why this tier is novel:**

- Prior work (DSPy §6: "report extensive comparisons on the development set to avoid overfitting on test"; MIPROv2 App H acknowledging "tendency to overfit instructions to the few-shot examples in the meta-prompt") uses val as a standard held-out signal. The optimizer still reads per-example val behavior — this is how they decide which candidate to keep.
- Agent-only optimization changes the risk profile. An agent optimizer that reads per-example val output can hard-code val-specific fixes (e.g., "if input starts with this phrase, return this verdict") that don't generalize and don't show up as cheating in any obvious way. The agent is *optimizing* — it will find these fixes if they're reachable.
- Structural prevention (not "use val sparingly") is the defense. The optimizer is never given per-example val; it can only use aggregate val signal as a generalization-health check, which is what val is *for*.
- Human articulation 2026-04-21: *"It should be optimizing for sure the train loss going down, but it should also be aware of the validation loss. It should trust generalizable fixes, not just feeding in answers like cheating on a test, because those answers would never help validation."*

### Tier 3 — Test: physically sealed

- Optimizer cannot invoke test eval at all during iteration.
- Test split lives at a filesystem path outside the optimizer's `--add-dir` scope.
- Single scalar return at locked-candidate; only run once at the end of the experiment.
- Same mechanism as Tier 2 but stricter: zero invocations during iteration, not just scalar-only.

### Formal statement

Let \(\mathcal{D} = \mathcal{D}_{\text{train}} \cup \mathcal{D}_{\text{val}} \cup \mathcal{D}_{\text{test}}\), with sealed test. Let the optimizer be an agent \(O\) with read access \(R(O, \cdot)\):

- \(R(O, \mathcal{D}_{\text{train}}) = \text{full}\) — inputs, labels, traces.
- \(R(O, \mathcal{D}_{\text{val}}) = \text{scalar}\) — only aggregate metrics, never per-example anything.
- \(R(O, \mathcal{D}_{\text{test}}) = \emptyset\) during iteration — invoked only at terminal evaluation; scalar return.

Enforcement is structural (filesystem permissions + output-schema validation), not behavioral (trust).

---

## 3. Architecture

Three-tier agent hierarchy, uniform subagent invocation mechanism, differentiated only by dispatcher output routing.

### Components

**Optimizer agent (outer loop).** Long-lived. Owns train-label access. Proposes pipeline changes — prompt edits, subagent restructuring, new tool calls, topology modifications, whatever the optimizer judges useful (see "Optimizer agent initial configuration" below for the full affordance catalog). Issues eval commands. Decides when to stop. Can respawn a successor at context limits (see §5).

**Eval dispatcher (deterministic Python script; NOT an agent).** Orchestrates subagent invocations for a given split. Enforces output routing per the tier hierarchy. No LLM in the dispatcher — no "helpful summarizing" of per-example outputs to the optimizer. One dispatcher per split: `run_train_eval.py`, `run_val_eval.py`, `run_test_eval.py`.

**Eval subagents (headless Claude Code, fresh context, uniform invocation).** Run paper-trail-v<N> (or whatever pipeline-v<N>) on a single example. Label-blind (opaque citekeys, scrubbed staging, filesystem restrictions per Rule 1). Identical mechanism for train and val; test same mechanism but gated by the seal. **The count and roles of subagents internal to paper-trail-v<N> are not a framework concern** — the dispatcher spawns one `/sarol-eval-item` per Sarol example, and paper-trail-v<N> internally may fan out to any number of sub-invocations with any topology. The framework is topology-agnostic; see journal entry `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` for the positioning decision.

### Data flow per split

**Train eval:**
```
optimizer agent
    │
    │ CLI: run_train_eval.py --version v<N> --subset eval-train-<N>
    ▼
run_train_eval.py (deterministic Python)
    │
    ├── reads: train split + gold (has filesystem access)
    ├── spawns: per-item `claude --bare --print /sarol-eval-item ...`
    ├── collects: per-example verdicts + traces
    ├── computes: macro-F1 + per-class F1 + confusion matrix
    └── returns to stdout: full log (per-example + aggregate)
    ▼
optimizer agent reads full log
```

**Val eval:**
```
optimizer agent
    │
    │ CLI: run_val_eval.py --version v<N>
    ▼
run_val_eval.py (deterministic Python)
    │
    ├── reads: val split + gold (has filesystem access; optimizer does not)
    ├── spawns: per-item `claude --bare --print /sarol-eval-item ...`  (SAME INVOCATION AS TRAIN)
    ├── collects: per-example verdicts + traces
    ├── computes: macro-F1 + per-class F1
    ├── writes: per-example verdicts + traces → /val_runs/v<N>/  (filesystem-restricted from optimizer)
    └── returns to stdout: {"macro_f1": <float>, "per_class_f1": {...}}  (schema-validated, scalar-only)
    ▼
optimizer agent reads scalar F1 only
```

**Test eval:** same shape as val but with stricter filesystem scoping and a tripwire on `run_test_eval.py` that refuses to execute unless explicitly unsealed (e.g., by a separate `--confirm-unseal` argument that requires out-of-band confirmation). Called once at locked candidate.

### Uniform subagent invocation

`claude --bare --print /sarol-eval-item --item <opaque_id> --staging <path>` is identical for train and val. The subagent does not know and does not need to know which split it's operating on. What differs: (a) which dispatcher invoked it, (b) where outputs get written, (c) what returns to the optimizer.

This is important for measurement integrity: if train-eval and val-eval invoked subagents differently, we'd risk mode-divergence artifacts (e.g., "paper-trail-v<N> performs better on val because of some quirk of the val dispatcher"). Uniform invocation eliminates that class of artifact.

### Why the dispatcher is a script, not an agent

- **Determinism.** Python scripts execute the same way every time. Agents have temperature, non-determinism, and judgment.
- **No helpful summarization.** An LLM dispatcher might — trying to be useful — slip per-example val content into a summary back to the optimizer. A Python script can't accidentally be helpful that way.
- **Schema enforceable.** The dispatcher's stdout can be validated against a locked JSON schema before being returned. Schema violations are refused.
- **Reviewable.** Source code review + unit tests + schema validation together give auditable structural guarantees.

### Optimizer agent initial configuration

The optimizer agent's initial state — system prompt, tool availability, `--add-dir` scope, seeded context — is a Tier 1 invariant for reproducibility (see §7 open problem #10). This subsection pins the content Human has articulated 2026-04-22; a full machine-checkable schema is still owed.

**Affordance catalog.** The optimizer's initial system prompt tells it explicitly which pipeline-change actions are legitimate. The catalog:

- Split a prompt into multiple distinct components.
- Combine prompts.
- Create new prompts entirely.
- Add tool calls within subagent dispatches.
- Search the internet for MCP servers that might be helpful and integrate useful ones.
- Run web searches for literature on a specific problem the optimizer has encountered — including meta-strategy literature ("what's a more efficient way to keep sub-agents on track in a multi-agent pipeline").
- Run web searches for specific data when the optimizer suspects the train labels are wrong, with an explicit guard: **do not overfit on this information.** Train labels are the optimization substrate; test labels are the ground truth. Web-sourced "corrections" are a known overfitting attack vector and must not propagate into prompts as label overrides.
- Use whatever tools are available in the Claude Code environment.

This list is non-exhaustive — the intent is to give the optimizer permission to think beyond prompt-text edits on the currently-deployed subagents, not to fence it in.

**Philosophy: optimize for optimizer performance, not optimizer cost.**

The optimizer agent is instructed to prioritize the quality of its own outputs over the compute cost of producing them. Rationale: one optimizer "step" (one proposed pipeline revision) is followed by an expensive downstream eval (N claims × paper-trail-v<N>'s fan-out × LLM inference). The optimizer's own thinking cost is small relative to the eval cost it triggers. If the optimizer spends 100,000 tokens reasoning about a change before proposing it and the change saves a wrong eval-run, the tradeoff is favorable.

Concretely: if the optimizer decides to spin out exploratory subagents to test-drive a candidate change before committing, or to think longer in-context, that is time well spent. Cost minimization for the optimizer is not an objective.

(Cost-vs-performance tradeoff for the *case-study pipeline itself* — i.e., should paper-trail-v<N+1> cost more than paper-trail-v<N> — is a separate question, deferred to a future paper; see §1 "What's deferred.")

**Seeded artifact — trace-aware sub-metric (DSPy-pattern, optimizer-owned).**

The optimizer is seeded at v1 with a DSPy-style trace-aware metric targeting the v1 topology: `metric(example, pred, trace) → {macro_f1, per_class_f1, extractor_recall, adjudicator_conditional_f1, verifier_flip_rate, verifier_flip_precision, failure_modes}`. The optimizer is told explicitly that this metric is *its own tool* — for logging, debugging, and deciding what to do next — not frozen eval infrastructure. When the optimizer restructures the pipeline (per D32 / the affordance catalog above), it is expected to rewrite the metric to match the new topology: drop sub-metrics for removed stages, add sub-metrics for new stages. See `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D36.

Eval arm (Tier 1, topology-agnostic) emits raw per-subagent traces + macro-F1 + per-class F1 only. Per-stage sub-score aggregation is the optimizer's job, lives in the optimizer's workspace, versions with paper-trail-v<N>. Val dispatcher remains scalar-only regardless of optimizer-side metric evolution.

**Seeded pattern — ProTeGi-style failure-mode enumeration (optional for the optimizer to use).**

The optimizer is also seeded with ProTeGi's `<START>...<END>` delimiter template (Pryzant et al. 2023 App A.1.1) as a known-good pattern for structured failure-mode analysis on train examples. Usage: given a minibatch of failing examples + the current subagent prompts, the optimizer (or a subagent it dispatches) fills in the template and enumerates N hypotheses, each wrapped in `<START>...<END>`. Each hypothesis seeds a candidate revision. Matches ProTeGi's native design — the template was intended for LLM consumption all along.

Like the trace-aware metric, this is purely agentic and transparency-only: seeded as a known-good pattern, not enforced. The optimizer may invent alternative failure-mode-analysis workflows if it judges better. Enumerated hypotheses and the revisions the optimizer committed from them are archived per revision on GitHub (feeds framework §7 open problem #5 — per-revision rationale capture).

**Not seeded — PromptBreeder mutation-operator catalog.** Considered and declined 2026-04-22 per D38. The catalog is a content-prior (vocabulary of specific edit moves) rather than a format-prior, which would anchor the optimizer's attention on a 2023-era prompt-text-edit vocabulary and contradict D32 topology-freedom by habit even with an explicit caveat. PromptBreeder is cited as prior art for (a) LLM-driven mutation being viable and (b) fixed-topology contrast (#2), but the 36-operator catalog itself is not surfaced to the optimizer. See journal D38.

**Anti-pattern to fight — Python-default reflex.**

Claude Code's training distribution tilts the model toward writing bespoke Python scripts when asked to solve an operational problem. The optimizer's initial system prompt must push back against this explicitly: Python is a library; agentic tool-use is the entry point. The optimizer should consider agentic approaches first (spawning a subagent, invoking an existing tool, composing skills) and fall back to writing Python only when the agentic approach has been considered and is clearly not the right fit.

Human articulation 2026-04-22: *"code can be written on the fly if needed. You can have a library of Python tools, but entry points should always be agentic. Submodules should be agentic; it's an agentic framework."*

**Decision status.** D34 in journal entry `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` commits the content above; §7 open problem #10 still tracks the full machine-checkable schema that folds into the `paper-trail-v<N>.json` archive artifact.

---

## 4. Structural defenses

Two mechanisms. Both verifiable. Both structural (not trust-based).

### Defense 1 — Filesystem permissions

The optimizer agent is invoked with `claude --bare --print --add-dir <train_paths> <optimizer_workspace>` — scoped to the paths it needs. Val split, val-run outputs, test split, test-run outputs are **not** in the optimizer's `--add-dir` list. At the OS level, the optimizer cannot read these paths.

Structure:
```
/experiments/sarol-2024/
    train/              ← optimizer reads
    val/                ← optimizer does NOT read (dispatcher only)
    val_runs/           ← optimizer does NOT read (dispatcher writes here)
    test/               ← sealed; optimizer does NOT read (pre-commit hook enforces)
    test_runs/          ← optimizer does NOT read (dispatcher writes here)
    eval-harness/       ← dispatcher scripts live here; optimizer reads the SCHEMA but doesn't invoke directly — goes through CLIs
```

The dispatcher scripts themselves have full filesystem access (needed to read gold, write outputs). The optimizer agent doesn't.

### Defense 2 — Fixed output schema

Each dispatcher CLI has a locked JSON output schema. Val dispatcher output schema:

```json
{
  "macro_f1": <float>,
  "per_class_f1": {<class_name>: <float>, ...},
  "n_examples": <int>,
  "version": "<tag>",
  "split": "val",
  "dispatcher_version": "<tag>"
}
```

Validation: the dispatcher runs its output through a JSON-schema validator before printing. Schema lives in the eval-harness directory, versioned. Any additional fields cause validation failure → dispatcher aborts with non-zero exit. No free-form prose ever reaches the optimizer from the val dispatcher.

Train dispatcher schema is richer (includes per-example arrays) but is also locked.

### Attack surface table

| Attack | How it would leak val | Structural defense |
| --- | --- | --- |
| Optimizer asks dispatcher for more info | CLI args include `--return-examples`-style flag | Dispatcher accepts fixed argument set only; unknown flags → reject |
| Optimizer reads val outputs directly | Filesystem walk into `/val_runs/` | `--add-dir` scope excludes; OS refuses |
| Optimizer deduces val from train behavior | Distribution-general pattern transfer | **Intentional — generalizable learning.** Prohibition is on per-example peeking, not on distribution transfer. |
| Optimizer injects "tell me val" into paper-trail subagent dispatch prompt | Subagent runs on val, returns val text in its output | Subagent output goes to dispatcher (not optimizer); dispatcher schema is scalar-only for val |
| Optimizer uses train-eval subagents to probe val | Train-eval subagent tries to read val files | Train-eval subagents have `--add-dir` scoped to train only; OS refuses |
| Optimizer writes a file that a later subagent reads | Indirect instruction-channel | Each subagent is invoked with a controlled `--add-dir` set; optimizer workspace not in subagent scope |
| Dispatcher bug leaks val into stdout | Prose error message containing example content | Schema validation before print; schema rejects non-conforming output; error path itself sanitized |
| Optimizer reads dispatcher source to understand val format | Source code is human-readable | Val format knowledge is not val content knowledge; OK to know the schema, not the per-example data |

### What remains un-closed (honest)

- **Dispatcher bug.** If `run_val_eval.py` itself has a bug that leaks val, structural defenses don't catch it. Mitigation: unit tests + code review + schema validation on output. Not a zero-risk posture; this is why the dispatcher is small and auditable.
- **Subagent-side effects.** If a paper-trail subagent on val writes to a global location (e.g., a system-wide log file, a shared cache) that the optimizer can read, leakage happens. Mitigation: subagents run in `--bare` mode with scoped `--add-dir`; audit subagent filesystem interactions.
- **LLM backend caching effects.** Anthropic's backend may cache across invocations in ways neither user nor Claude Code sees. Mitigation: none we can impose. Disclose as a limitation.
- **Intentional subversion by the optimizer.** Our threat model is honest optimization, not adversarial. An adversarial optimizer agent (if it were deliberately trying to exfiltrate val) could probably find a channel. Not our problem for this experiment; worth noting as a limitation.

---

## 5. Optimizer continuity across context limits

The optimizer agent runs a long loop over many revisions. A single Claude Code session has a bounded context window (~200K tokens on Opus 4.7 at time of writing, though 1M-context variants exist). The optimizer needs to handle context-limit boundaries without losing state.

### Proposed mechanism

**Self-initiated respawn.** When the optimizer's context approaches a threshold (e.g., 150K tokens, leaving 50K headroom), the optimizer voluntarily does the following:

1. Writes a **handoff document** to a designated location (inside the optimizer's workspace, outside val/test paths) summarizing:
   - Current pipeline version: `paper-trail-v<N>`
   - Latest train F1: <scalar>
   - Latest val F1: <scalar>
   - Outstanding failure-mode hypotheses (natural-language list)
   - Revision history summary: which edits helped, which didn't, which are queued
   - Stopping-rule state (e.g., patience window count, budget remaining)
   - Current best candidate's tag and metric
2. Exits cleanly.
3. The outer harness (a bash script or a Python supervisor) detects optimizer exit, starts a fresh `claude --bare --print` with the handoff doc as initial context + a standard "continue-the-loop" system prompt.
4. Fresh optimizer successor reads handoff, picks up loop.

### Open problems with this mechanism

- **Compression fidelity.** How lossy is the handoff? The optimizer accumulates implicit knowledge (failure-mode intuitions, hunches) that don't compress into a structured doc. Some signal is lost every respawn.
- **Respawn criterion.** Who decides when to respawn? Optimizer self-decides = agency for a load-bearing state change, error-prone. Outer harness decides (at token threshold) = mechanical but may interrupt mid-reasoning. Lean: outer harness monitors token count, signals optimizer "wrap up at next checkpoint," optimizer writes handoff and exits.
- **Respawn budget.** Is there a cap on respawns? Probably yes — if the optimizer respawns 100 times, it's likely spinning. Cap + stopping rule.
- **Who writes the initial handoff-doc format?** This doc will evolve across revisions. Needs a schema and versioning (the handoff schema itself should be a Tier 1 invariant per the archive framework).

### Alternative considered

Claude Code Opus 4.7 1M-context variants. Would reduce (but not eliminate) the respawn problem by extending the single-session horizon. Tradeoff: higher cost per token; cache warming matters more; some features may degrade. Not adopting by default; keep as a fallback if respawns become a pain.

---

## 6. Relationship to existing hygiene rules

### Rule 1 — Subagent sandboxing (from `experiment-sarol-optimization-loop-hygiene.md`)

**STAYS, unchanged.** The deployed paper-trail subagents (extractor, adjudicator, verifier) during any eval — train, val, or test — never see gold labels. Defense mechanisms (opaque citekeys, `$PAPER_TRAIL_GOLD_DIR`, scrubbed `staging_info.json`, filesystem-restriction paragraph on every dispatch) remain authoritative.

Rule 1 is independent of the agent-only reframe. It applies to the *deployed pipeline*, not to the *optimizer*.

### Rule 2 — Main-session test blindness (from `experiment-sarol-optimization-loop-hygiene.md`)

**SUPERSEDED for agent-only mode.** Rule 2 framed test-blindness as a discipline on the *human main planning session*. In agent-only mode, there is no human main session; the optimizer is the session. Rule 2's semantic intent is preserved as **Tier 3 sealing** in the tiered leakage model: the optimizer cannot invoke test at all during iteration, enforced structurally (filesystem + CLI gating), not behaviorally.

The hygiene doc will be updated with a cross-reference: Rule 2 applies in any human-in-the-loop mode (e.g., the future separate paper on human-agent collaboration) but is subsumed by Tier 3 in the agent-only framework.

### Additional discipline from this framework

- **Tier 2 (val scalar-only).** New. Not present in prior Rule 1 / Rule 2. Specific to agent-only optimization where the optimizer would otherwise have unrestricted read access to val.
- **Uniform subagent invocation.** New norm: same `claude --bare --print` for train, val, test; differentiation is at the dispatcher level.
- **Dispatcher-as-script, not agent.** New norm: the eval dispatcher is deterministic Python.

These become explicit rules, referenced by the rest of the experiment planning.

---

## 7. Open problems

Honest list of what's not yet solved.

1. **Optimizer self-respawn protocol.** See §5. Handoff-doc schema, respawn criterion, respawn budget — all undefined.
2. **Stopping rule for the optimizer.** Candidate criteria: (a) val F1 patience window (N revisions without improvement), (b) budget exhaustion (dollars or revisions), (c) optimizer self-declared "no further improvement hypotheses." Need to pick and test.
3. **Dispatcher-bug risk.** §4 open item. If the dispatcher itself leaks val, no structural defense catches it. Mitigation via testing; not zero-risk.
4. **Initial seed knowledge.** Where does the optimizer agent start? From the existing paper-trail-v<N> prompts + the journal-captured failure-mode history? Or from a minimal seed? This is the "from-scratch" question Human deferred — see `docs/journal/2026-04-21-architecture-synthesis-pending-decisions.md` and this doc §1 deferrals.
5. **How does the optimizer justify its edits?** The paper wants to report *what the optimizer did* at each revision, not just *that* it revised. Mechanism: optimizer writes a per-revision rationale doc (analogous to a commit message) that lands in the archive. Schema TBD.
6. **Empirical validation: does the framework work?** N=10 de-risk smoketest (currently sidebarred per 2026-04-21 discussion) will tell us whether agent-only can move macro-F1 in the right direction on Sarol before we commit to a full curve.
7. **Generalization beyond paper-trail.** The framework is pitched as pipeline-agnostic. We have one case study. A reviewer may push on "does this work on other pipelines?" — addressable only by running a second case study, which is deferred.
8. **Cost accounting.** The framework adds overhead (multiple dispatchers, uniform headless invocation, optimizer respawns). Need to quantify vs a naive iteration loop. Logging already planned in archive framework.
9. **Attribution on failure modes.** Per-stage sub-scores (DSPy trace-aware metric pattern, deferred clarification) let us attribute macro-F1 deltas to extractor vs adjudicator vs verifier. Specification pending.
10. **What counts as "the optimizer agent"?** Its system prompt, its tools, its `--add-dir` scope, its initial context — all of these are Tier 1 invariants for reproducibility. Needs a schema (folds into the `paper-trail-v<N>.json` archive artifact). **Partial spec committed 2026-04-22** — see §3 "Optimizer agent initial configuration" (affordance catalog, performance-not-cost philosophy, fight-Python-default guidance). Full machine-checkable schema still owed.

---

## 8. Non-goals and explicit deferrals

Per memory `feedback_defer_with_milestone_pin.md`. Each item has a milestone pin.

- **Human-in-the-loop comparison arm.** Pin: separate future paper on human-agent research collaboration. The current paper's framework is agent-only; the planning-phase human-agent collaboration material (in `paper-writeup-items.md` §"Human-value retrospective") feeds the future paper, not this one.
- **From-scratch bootstrap.** Pin: separate arm after first curve lands. We start from the existing paper-trail-v<N> prompts, not from zero.
- **Backbone portability** (Opus↔Sonnet↔Haiku). Pin: Task 6+ if compute budget allows. Not in primary curve.
- **Multi-benchmark validation** beyond Sarol. Pin: after paper lands.
- **Hand-crafted topology search procedure (MASS-style).** We are not implementing a MASS-style block / topology / workflow three-stage search procedure. **Topology change as an affordance of the optimizer agent is explicitly allowed** — see §3 "Optimizer agent initial configuration" and journal `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D32/D33. The framework does not prescribe a search procedure; the optimizer may or may not restructure the pipeline as it judges useful.
- **Full per-N-landmark three-way ablation** (baseline | instructions-only | demos-only | joint from MIPROv2). Pin: run only at v_final, not at every landmark. Cost-driven.
- **Human A/B blind preference study** (Self-Refine App C). Pin: blog-post-only if we want it; not paper-required.
- **LLM-as-loss secondary judge** (TextGrad §3.4). Pin: skipped entirely; macro-F1 + per-class F1 is sufficient signal.
- **Bandit candidate selection** (ProTeGi UCB). Pin: only relevant if we sweep multiple candidate-branches in parallel; not baseline.
- **Memory-blind invocation spike (Q9c) canary test.** Pin: sanity-check owed before Task 5 eval arm build. See archive-framework doc §Q9c. `--bare` is the verified mechanism and this framework doc depends on it working as documented.

---

## Implementation checklist (feeds NEXT.md Task 5)

**v1 gate (must land before any curve runs):**

1. `--bare` canary sanity-check (resolve Q9c).
2. Eval dispatcher scripts: `run_train_eval.py`, `run_val_eval.py` — deterministic Python, locked output schemas, filesystem-scoped.
3. `/sarol-eval-item` slash command (or CLI equivalent) with locked argument set — non-interactive.
4. Filesystem layout per §4 Defense 1 with permission-boundary tests.
5. Schema validator module shared across dispatchers.
6. Val-run-outputs directory outside optimizer's `--add-dir` scope; verified by permission-boundary test.
7. `paper-trail-v<N>.json` archive schema covering tier-specific invariants + dispatcher versions + handoff-doc schema.
8. 3-seed minimum at v1 landmark.
9. Per-stage sub-scores in train dispatcher output.
10. Optimizer agent initial prompt + `--add-dir` scope + system prompt template (Tier 1 invariant).

**v2+ can roll in without invalidating v1 curve:**

11. Optimizer self-respawn protocol and handoff schema.
12. Three-way ablation structure (only at v_final).
13. Figure-grammar commitments (visual convention for the headline figure).
14. Feature-matrix related-work table.

---

## References

Internal:
- `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — Rule 1 (stays), Rule 2 (superseded for agent-only).
- `docs/plans/experiment-sarol-archive-and-eval-framework.md` — archive, invariants, Q9c memory-blind mechanism.
- `docs/plans/experiment-sarol-benchmark.md` — Sarol-specific strategy.
- `docs/plans/experiment-sarol-runbook.md` — Sarol-specific execution.
- `docs/plans/paper-writeup-items.md` — paper-framing, contributions, 9-paper borrow catalog.
- `docs/plans/NEXT.md` — status.
- `docs/journal/2026-04-21-architecture-synthesis-pending-decisions.md` — decision log; PENDING → RESOLVED with this doc.
- `docs/journal/2026-04-21-tiered-leakage-framework-decisions.md` — decision log for this doc's core commitments (to be written).

External (cited in related work):
- Khattab et al. 2023 (DSPy; arxiv 2310.03714) — multi-stage LM program formalism; Signature pattern.
- Opsahl-Ong et al. 2024 (MIPROv2; arxiv 2406.11695) — algorithmic multi-module proposer; App H overfitting acknowledgment.
- Yang et al. 2023 (OPRO; arxiv 2309.03409) — §5.4 / Fig 11 train+val over optimization steps; explicit deferral of val-gated early stopping.
- Soylu et al. 2024 (BetterTogether; arxiv 2407.10930) — joint prompt + weight optimization; LM-program formalism reinforced.
- Zhang et al. 2025 (MAPRO; arxiv 2510.07475) — MAS-as-DAG; reversed-topology blames; patience-window stopping.
- Seo et al. 2025 (MA-SAPO; arxiv 2510.16635) — score-aware reasoning; cascading-error taxonomy.
- Zhou et al. 2025 (MASS / Multi-Agent Design; arxiv 2502.02533) — topology-search contrast; fixed-topology positioning.
- Shinn et al. 2023 (Reflexion; arxiv 2303.11366) — actor/evaluator/self-reflection structure; episodic memory buffer.
- Madaan et al. 2023 (Self-Refine; arxiv 2303.17651) — iterative feedback-refine.
- Yuksekgonul et al. 2024 (TextGrad; arxiv 2406.07496) — computation-graph / variable / backward abstraction.
- Fernando et al. 2023 (PromptBreeder; arxiv 2309.16797) — fixed-topology rationale.
- Pryzant et al. 2023 (ProTeGi; arxiv 2305.03495) — gradient-template schema; learning-curve overfitting evidence.
