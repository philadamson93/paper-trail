# 2026-04-22 — Lit-review 2: competitor landscape and novelty recalibration

Second major journal entry for 2026-04-22. Follows the topology-freedom + optimizer-affordances decisions (D32–D38) earlier in the day and the clarifications-list walk-through that triggered a wide-net lit review. The earlier wide-net pass produced ten subagent reports across six paper-lines; this entry synthesizes those plus four follow-up targeted passes (Karpathy autoresearch code-level dive, orchestrator-of-agentic-workflows novelty check, slash-command-as-eval-harness check, VeRO close-read) into a calibrated novelty map. Multiple contribution claims from the pre-lit-review framing are partially scooped; the integrated-claim corner is clean; the two-paper split is resolved back to one paper.

**Authoritative plan docs updated in this session:** `docs/plans/agentic-pipeline-optimization-framework.md` (related-work section added, `recursive` overclaim dropped, autoresearch direct-lift items absorbed into §3), `docs/plans/paper-writeup-items.md` (two-paper split resolved → one paper; Core Contributions reordered with case study primary; borrow catalog revised with autoresearch / Meta-Harness / VeRO / AlphaEvolve / ADAS / AFlow entries), `docs/plans/NEXT.md` (Task 5 new deliverables from autoresearch borrow-list; `--bare` + Agent-tool canary added as Q9c-adjacent pre-Task-5 gate).

## Context

Human raised 2026-04-22: *"I've been surprised that this space was as untouched as we initially thought, given how popular Andrej Karpathy's posts have been on Twitter… we need to understand what exactly is claimed and at what level versus what we've already talked about here being novel… this very concretely defines what experiments are worth doing and paper positioning before we even begin."*

Agent proposed and Human approved a follow-up targeted pass after the wide-net pass, focused on three questions: (a) deep code-level dive on Karpathy's autoresearch repo to extract adoptable patterns, (b) targeted novelty check on the orchestrator-of-agentic-workflows framing Human articulated, (c) slash-command-as-eval-harness methodology check. A fourth targeted pass was added mid-session on VeRO after the slash-command subagent surfaced it as a potential bigger scoop than Meta-Harness.

Ten subagent-reports total synthesized here (six wide-net from earlier in the day, four targeted). Honest accounting of where we stand vs prior art follows.

## Competitor landscape (as of 2026-04-22)

| System | Date | Substrate | Optimizer type | Target system | Leakage discipline | Closest to us on |
|---|---|---|---|---|---|---|
| **Karpathy autoresearch** | Mar 2026 | Python + LM coding agent | LLM coding agent (Claude/Codex/etc.) | Single `train.py` (LM training) | Instruction-only, no held-out test | Agent-driven loop + instructional immutability pattern |
| **Meta-Harness** (Stanford IRIS, arxiv 2603.28052) | Feb-Mar 2026 | Python + Claude Code (with `--disable-slash-commands`) | Claude Code Opus-4.6 | Single-file Python harness | Manual regex audits | Optimizer identity + Claude-Code-as-optimizer framing |
| **VeRO** (Scale, arxiv 2602.22480) | Feb 2026 | uv Python package | Claude Sonnet/Opus 4.5 + GPT-5.2-Codex | Monolithic Python agent, fixed GPT-4.1-mini target | 3-tier with API-mediated DatasetViewer access control | Reproducibility-infrastructure framing; three-tier splits; budget-controlled eval |
| **AlphaEvolve** (DeepMind, arxiv 2506.13131) | Jun 2025 | Python | Scripted GA + LLM mutation | Algorithm/code block | Domain-specific conventions | Agent-framing + verifiable-reward + cascaded evaluation |
| **ADAS** (Hu/Lu/Clune, ICLR 2025, arxiv 2408.08435) | 2024 | Python | LLM meta-agent | Single `forward(taskInfo)` function | 20/60 val/test convention | Code-as-search-space + agent-as-meta-optimizer |
| **AFlow** (Zhang et al., ICLR 2025, arxiv 2410.10762) | Oct 2024 | Code graph | LLM + MCTS | Flat-graph homogeneous-node workflows | 20/80 val/test convention | Train+val plot (closest figure-type precedent); topology-as-optimization-variable |
| **AI Co-Scientist** (DeepMind, arxiv 2502.18864) | Feb 2025 | Multi-agent | Supervisor agent | Fixed multi-agent roster | LLM-judge tournament (Elo) | Multi-agent target but no optimizer over it |
| **Live-SWE-agent / DGM / HGM** | 2025 | Monolithic bash+edit | Self-modification | Single agent | None | Self-modifying agent against verifiable reward |
| **Sakana AI Scientist v1/v2** | 2024-2025 | Python + Aider | Agentic tree search | Fixed research pipeline | Semantic Scholar novelty check (input-side) | Multi-subagent + autonomous research framing |

Additional orthogonal references (cite-but-don't-position-against): GEPA (DSPy's ICLR 2026 Oral, best in class for prompt-only optimization), SkillsBench (arxiv 2602.12670, skills-as-first-class-eval-artifacts), Skilldex (arxiv 2604.16911, skill package management), `gh skill` (GitHub CLI v2.90.0, tag-pinned skills with `--pin`), Darwin/Huxley Gödel Machine (arxiv 2505.22954 / 2510.21614, self-modifying agents with reported reward hacking), plus Ellenberg et al. (arxiv 2503.11061, mathematician-led empirical study of FunSearch with explicit contamination warning).

## Decisions made today

### D39 — Two-paper split resolved: **one paper, consolidated**

**Raised by:** Human.
**Exact quote (voice-to-text, interpreted):** *"I still think we have a lane here for no other reason than no one else is working on the paper-trail problem… we very likely want this to be one paper, not two."*

**Context:** The 2026-04-21 reframe put framework contribution primary and paper-trail case-study secondary, and logged a two-paper-split as an open decision (paper-writeup-items.md §"Open paper-level decisions"). The lit-review-2 compressed the framework novelty — Karpathy / Meta-Harness / VeRO each scoop fragments of what looked like clean framework contributions. Splitting into two papers now means each paper has less standalone punch.

**Agent analysis:** consolidation lets the case study (paper-trail-on-Sarol) carry the empirical weight — INDIRECT-detection failure mode, 9-way Sarol baseline, cost-per-claim numbers are findings the framework papers cannot make because they don't touch biomedical citation-integrity. Methodology contributions ride on top as clean *subclaims* rather than standing alone as their own paper. The related-work section positions the integrated claim against all nine competitors in one place.

**Decision:** one paper, case study carries primary empirical weight, methodology contributions as layered subclaims. Update `paper-writeup-items.md` §"Open paper-level decisions" — the two-paper entry is resolved to "consolidated into one paper 2026-04-22 (D39)."

### D40 — Drop "recursive subagent spawning" framing; replace with heterogeneous-controllability-surface + topology-as-search-space

**Raised by:** orchestrator-of-agentic-workflows subagent report.
**Finding:** Claude Code subagents cannot spawn their own subagents. Docs quote: *"Subagents cannot spawn their own subagents. Don't include `Agent` in a subagent's `tools` array… This prevents infinite nesting (subagents cannot spawn other subagents)."* Depth is structurally capped at 2 (main orchestrator + one subagent layer). The VS Code Copilot feature allowing nesting-depth-5 is a different product.

**Agent response:** Our earlier framing that paper-trail's "subagents themselves spawn further subagents" overclaims Claude Code's substrate. Paper-trail at current topology is a 2-level system: main + one subagent layer. Subagents call tools; they do not call subagents.

**Replacement novelty framing** (what the subagent identified as genuinely unclaimed):
> *"Optimizer-of-multi-subagent-pipelines-with-heterogeneous-per-subagent-controllability-surface, with topology as part of the search space, and invariant declaration/validation across what the deployed system spawns during a single eval."*

Concretely, the controllability surface Claude Code exposes per subagent — `model`, `tools`, `disallowedTools`, `mcpServers`, `permissionMode`, `memory`, `skills`, `isolation: worktree`, `hooks`, `maxTurns`, `effort`, `background` — is rich and none of the surveyed optimizer papers treat it as part of the search space or as invariants to validate. AFlow has per-node config in a flat graph but with homogeneous nodes; VeRO fixes target model to GPT-4.1-mini; Meta-Harness is monolithic.

**Decision:** replace "recursive subagent spawning" language wherever it appears in plan docs with heterogeneous-controllability-surface + topology-as-search-space. Update `agentic-pipeline-optimization-framework.md` accordingly. The depth-2 substrate constraint is noted explicitly as a design boundary the optimizer operates under (not a limitation of our contribution).

**Important architectural corollary:** the dispatcher is a Python script using `subprocess.run(["claude", "--bare", "--print", "/sarol-eval-item", ...])`, which launches a *fresh Claude Code process*. That fresh process is a new depth-0 main session with its own Agent tool, which can spawn paper-trail's internal subagents normally. The depth-2 cap never bites across the process boundary. This was already spec'd in the framework doc's dispatcher architecture but the structural reason (resets depth counter) was not explicit. Added to the framework doc in this commit.

### D41 — Required citations and positioning structure for the paper

**Raised by:** lit-review-2 synthesis.

**Required citations (must-cite, with role in paper):**

- **Karpathy autoresearch** — cite as **extension target**. Our paper explicitly positions structural filesystem enforcement as an extension of autoresearch's instruction-only pattern. One-paragraph quote: *"Modify `prepare.py`. It is read-only. It contains the fixed evaluation, data loading, tokenizer, and training constants."* — autoresearch's own scoping. Our contribution is to harden this with OS-level filesystem permissions + pre-commit hook + out-of-tree gold/benchmark for multi-subagent settings where instructional-only is too weak.
- **Meta-Harness (Stanford IRIS)** — cite as **adjacent substrate choice**. Same optimizer identity (Claude Code Opus as optimizer-agent); they run with `--disable-slash-commands` to constrain the optimizer's surface, targeting single-file Python harnesses. We keep slash-commands enabled and package the SUT as a Claude Code slash command with per-subagent YAML config so that **heterogeneous subagent configuration is a first-class declarative primitive** (model / tools / MCPs / memory / permissionMode per subagent). Framing: different packaging choices for the SUT, not "substrate inversion."
- **VeRO (Scale Labs)** — cite as **closest infrastructure competitor**. We adopt their committed-snapshot-is-SUT principle (uv-package + Git). At the invocation boundary, VeRO's uv Python package and our Claude Code slash-command are structurally equivalent — both are subprocess-launched reproducible units pinned at a git commit. The differentiation is *inside the unit*: **declarative per-subagent heterogeneous config (our slash-command + `.claude/agents/*.md` YAML) vs imperative per-call Python config (their uv package)**. Combined with our multi-subagent target (their targets are monolithic Python agents with a fixed target model) and their own empirical negative finding — *"current optimizers default to prompt modifications, exhibiting limited diversity and impact in the changes they can produce"* — this is a **motivation gift**: declarative-subagent-config-as-optimization-surface directly answers the "limited architectural change" gap VeRO identified. Narrower, more defensible framing than "Claude Code is fundamentally different."
- **AlphaEvolve** — cite as **paradigm example**: verifiable-reward-driven agent-framed optimization at scale. Use their explicit future-work framing from §6: *"we envision that the value of setting up more environments (problems) with robust evaluation functions will become more widely recognized."*
- **ADAS** — cite as **code-as-search-space precedent**. Quote §2: *"FMs are proficient in coding, utilizing a code search space allows us to leverage existing expertise from FMs during the search process."* Their contribution is code-as-search-space; ours extends to *agentic-coding-substrate* (Claude Code slash commands + subagent config) with structural defenses they lack.
- **AFlow** — cite as **closest figure-type precedent**. Their Figure 5 (train/val over optimization rounds on GSM8K) is the closest train+val-curve-over-agent-driven-revisions figure in the literature. We plot the same-shape figure over agent-driven `paper-trail-v<N>` revisions. (Stopping rule — whether we use plateau / gap-monitoring / budget — is standard ML hygiene, not a contribution; we do NOT position stopping-rule-choice as a named novelty claim.)
- **Ellenberg et al.** — cite for **contamination warning** in the intro motivation section: *"any model trained after the release of the original funsearch article may have incorporated the record-breaking program into its training data. This presents a potential issue that is likely to become a general concern in the future."* Mathematician-led empirical study of FunSearch; supports our structural sealing argument.
- **Anthropic Claude Code subagents docs** — cite for the substrate property our controllability argument rests on (markdown + YAML per-subagent config with `tools`, `model`, `mcpServers`, etc.).

**Positioning structure for the paper's related-work section:**

Three-bucket frame adapted from D33 (topology-freedom positioning):
1. **Hand-crafted fixed-topology prompt optimization** — DSPy/MIPROv2, PromptBreeder, BetterTogether, GEPA.
2. **Hand-crafted topology search procedures** — MASS, ADAS, AFlow.
3. **Agent-as-optimizer over agentic systems** (the 2026 wave) — Karpathy autoresearch, Meta-Harness, VeRO, AlphaEvolve, DGM/HGM, Live-SWE-agent.
4. **Ours** — positioned within bucket 3 with the specific corner we occupy: multi-subagent + heterogeneous controllability + topology-as-search-space + tiered structural leakage + labeled domain benchmark.

Decision: adopt this four-bucket structure explicitly in the framework doc's new "Related work and positioning" section. The paper's related-work section will mirror this structure.

### D42 — Autoresearch direct-lift items adopted into `agentic-pipeline-optimization-framework.md` §3 "Optimizer agent initial configuration"

**Raised by:** autoresearch deep-dive subagent borrow-list.

**Direct lifts with attribution** (full provenance preserved — these are Karpathy's formulations, ported):

- **NEVER STOP discipline** — lift verbatim the principle: the optimizer does not pause to ask the human whether to continue. Autonomous loop runs until externally terminated. Cite Karpathy `program.md` 2026.
- **Simplicity criterion** — lift verbatim the full principle: all else being equal simpler is better; a small improvement that adds ugly complexity is not worth it; removing something and getting equal-or-better results is a great outcome. Cite.
- **CAN / CANNOT declarative block structure** — adopt the pattern (two declarative lists defining modification surface vs no-go zones) for our setting. Enumerate our mod surface (prompts in `experiments/sarol-2024/prompts/`, subagent config, dispatcher schema surface, topology) and no-go zones (eval-harness subdirectory, `$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR`, sealed test, eval-arm code).
- **Output-flood prevention rule** — eval runs redirect to log files; optimizer greps, does not inhale raw output into context.
- **Crash-handling discipline** — split: typo-vs-fundamentally-broken. `tail -n 50 run.log` explicit recipe on empty-grep-output (Karpathy's commit `bd75534` "Fix agent crash blindspot by forcing it to read traceback" is a real observed failure mode).
- **Anti-rabbit-hole rule** — "if you can't get things to work after more than a few attempts, give up" — adopted as general discipline.
- **Experiment-as-commit-unit + short-text description** — our `paper-trail-v<N>` git tags already align; adopt the 5-column results-table structure (`commit` / primary_metric / secondary_metric / status / description), commit ours (contrast autoresearch's `results.tsv` ungitted).
- **Setup phase with human checkpoint** — before the NEVER STOP autonomous loop kicks in, a deterministic setup step with human confirmation (data verified, results table initialized, branch/tag created).

**Stronger-where-we-differ statements** (explicit improvement over autoresearch):
- Immutability is **structural** (pre-commit hook + filesystem permissions + out-of-tree gold/benchmark), not instructional.
- Results and full revision history are **committed**, not gitignored. Failure modes are evidence.
- Multi-subagent target (not single-file).
- Three-tier leakage with Tier 2 scalar-only (not one-tier).

**Decision:** these lifts land as a new/revised subsection of §3 "Optimizer agent initial configuration" in the framework doc, structured as "autoresearch-inherited discipline (with citation)" vs "our extensions." Human attribution preserved inline where relevant for retrospective-paper provenance.

### D43 — Contribution ordering: case study primary, methodology as layered subclaims

**Raised by:** D39 one-paper consolidation.

**Revised Core Contributions in `paper-writeup-items.md`** (post-consolidation):

**Primary empirical contributions (case study, un-scoopable by framework papers):**
1. **paper-trail on Sarol-2024 as the first biomedical citation-integrity agent system** evaluated on a labeled 9-way benchmark. 9-way macro-F1 baseline at N=50, progressing to full train/dev/test.
2. **INDIRECT-detection failure mode** — named, diagnosed, remedied. LLM-adjudicator bias toward over-trusting on-topic evidence with trailing citation markers. From April-20 smoketest (2/5 false-ACCURATEs had this shape). Pattern is legible and transferable beyond paper-trail.
3. **Severity-under-commitment pattern** (tentative pending N=50+).
4. **Cost-per-claim practitioner numbers** (~$0.73/claim at Opus 4.7 uncached).
5. **Train+val macro-F1 curve across paper-trail-v<N>** as empirical demonstration of agent-only optimization on a multi-subagent citation-integrity pipeline.

**Methodology subclaims (layered on top of case study; each individually has prior art, each cleanly extensible):**
6. **Tier 2 scalar-only val as structural defense.** Cleanest standalone methodology claim. No surveyed system enforces per-example val inaccessibility to the optimizer.
7. **OS-level structural enforcement** of leakage discipline (filesystem permissions + out-of-tree gold/benchmark + locked dispatcher schemas). Harder than autoresearch's instruction-only or VeRO's API-mediated DatasetViewer. Positions as extension of both.
8. **Declarative per-subagent heterogeneous controllability as an optimization surface.** AFlow has per-node config in flat graph (homogeneous nodes); VeRO fixes target model to GPT-4.1-mini; Meta-Harness is monolithic and `--disable-slash-commands`; none treat the Claude-Code-subagent-config surface (`model`, `tools`, `mcpServers`, `permissionMode`, `memory`, `skills`, `isolation`) as an optimization surface. Narrower substrate argument than "Claude Code is special" — specifically "declarative YAML per-subagent config is easier to vary and commit than imperative per-call Python config, making subagent-heterogeneity first-class." Combined with topology-as-search-space (D32), this is the integrated contribution.

**Subclaims explicitly DROPPED from contribution-list after lit-review-2 sharpening:**
- ~~Divergence-stopping rule on train+val curve~~ — AFlow + VeRO use plateau/budget stopping; ours would be train-vs-val gap monitoring; this is textbook ML early-stopping applied in a new setting, not a methodology contribution. Standard hygiene, cite textbook references, do not position as novel.
- ~~Slash-command-as-SUT-packaging as a named subclaim~~ — at the invocation boundary, VeRO's uv-package and our slash-command are structurally equivalent subprocess-launched reproducible units. The real differentiation is declarative-vs-imperative subagent config (now folded into subclaim 8). Don't claim the packaging primitive as novelty.

**Paper structure implied by this ordering:**
- §1 Intro: citation-integrity problem + paper-trail product motivation + the lit gap.
- §2 Related work: four-bucket structure (fixed-topology / hand-crafted-search / agent-as-optimizer / ours).
- §3 System (case study primary): paper-trail architecture + Sarol benchmark + evaluation protocol.
- §4 Framework (methodology subclaims): tiered leakage discipline + agent-only optimizer loop + structural defenses + topology-freedom.
- §5 Experiments: train+val curve, per-class F1 stacking, INDIRECT-detection + severity-under-commitment, cost-per-claim.
- §6 Discussion: what-we-extend-from-whom citations matrix + substrate argument + future work.
- §7 Limitations.

### D44 — `--bare` + Agent-tool compatibility canary added as Q9c-adjacent pre-Task-5 gate

**Raised by:** architectural clarification triggered by Human's question on subagent depth limits.

**Context:** Our dispatcher architecture (deterministic Python `subprocess.run(["claude", "--bare", "--print", "/sarol-eval-item", ...])`) depends on the fresh Claude Code process having Agent-tool access so paper-trail can spawn its internal subagents. `claude --help` documents that `--bare` skips auto-memory, CLAUDE.md auto-discovery, hooks, LSP, plugin sync, keychain, attribution, background prefetches — but does NOT state that `--bare` disables the Agent tool. Skills still resolve. Inference: Agent tool should be available by default. Testable.

**Canary test design** (parallel structure to the Q9c memory-blind canary):
1. Register a trivial slash command `/canary-agent-test` that dispatches one subagent (e.g., via Agent tool to echo "agent-reached" from the subagent).
2. Invoke `claude --bare --print /canary-agent-test` (no other flags).
3. Verify the subagent echoed "agent-reached" in the output.
4. If yes → `--bare` preserves Agent tool, architecture validated, Task 5 eval-arm build unblocked on this axis.
5. If no → we need to compose with `--allowedTools Agent` or similar; framework-doc updated and re-test.

**Decision:** add to framework-doc §7 open problems as #11, and to NEXT.md Task 7 backlog alongside Q9c memory-blind canary. Both canaries gate Task 5 eval-arm build. Estimated 15 min each; can be run in the same session.

### D45 — Per-claim wall-clock or model-call budget as fairness device (Tier 1 invariant candidate)

**Raised by:** autoresearch deep-dive borrow #5.

**Karpathy's insight:** a fixed 5-min wall-clock budget per experiment makes architecture changes comparable across `train.py` revisions — the agent cannot "win" by training longer. Our analog: a fixed per-claim evaluation budget (wall-clock or model-call count) so the optimizer cannot "win" by spending more compute per item.

**Rationale:** topology-freedom (D32) allows the optimizer to grow pipeline complexity. Without a per-claim budget, pipeline-bloat is a free optimization surface that contaminates the train+val curve. With a per-claim budget, pipeline bloat becomes visible as cost-per-claim rising faster than F1 improves — which is the performance-cost tradeoff Human explicitly deferred to a future paper (D34), not something the current paper wants in the train+val signal.

**Tradeoff:** a wall-clock budget has infrastructure variance (Anthropic backend latency, MCP calls, network). A model-call count budget is deterministic but doesn't penalize slow calls. Probably model-call count is the right primary budget, wall-clock as secondary.

**Decision:** add as Tier 1 candidate invariant. Validate at every run via `validate_run.py`. Specific bound (number) set at Task 5 design time; default-lean is "whatever paper-trail-v1 uses ×1.5" to allow growth headroom without encouraging bloat. Update NEXT.md Task 5 to include this deliverable. Update `experiment-sarol-archive-and-eval-framework.md` Tier 1 invariants table.

### D46 — Round-trip sanity canary per run (from autoresearch issue #384 lesson)

**Raised by:** autoresearch deep-dive community signals.

**Autoresearch issue #384:** the BPB evaluation metric had a silent bug for weeks — UTF-8 replacement characters were inflating the metric. An agent optimizing against a buggy metric optimizes the bug.

**Lesson for our setting:** Tier 1 invariants must include a **round-trip sanity test** beyond the file-hash invariants we already have. Specifically: at every run, the eval arm processes a known-good canonical claim (stored in gold but with a pinned expected verdict) and confirms the pipeline returns the expected verdict. If the sanity check fails, the run is invalid and the result is discarded.

**Decision:** add round-trip sanity canary to `validate_run.py` responsibilities. Two options for the canary claim:
- Option A: a synthetic canonical claim (pinned, hand-authored, obvious correct verdict). Pros: fully controlled; no real-data contamination. Cons: doesn't exercise real paper-fetching etc.
- Option B: a specific Sarol train claim with a known-correct verdict that's robust across reasonable paper-trail revisions. Pros: exercises the real pipeline. Cons: if the pipeline genuinely degrades on this claim, sanity fails and we lose runs.

Lean Option A for Task 5 v1; can upgrade to Option B if A proves too artificial. Update NEXT.md Task 5 deliverable list.

### D47 — Per-claim adjudicator-reasoning exposure to the optimizer in train-tier (from autoresearch issue #353 lesson)

**Raised by:** autoresearch deep-dive community signals.

**Autoresearch issue #353 (ottogin's 60% better fork):** simply giving the agent more training-dynamics diagnostics (loss curves, intermediate state) consistently improves optimization outcomes on the same hardware budget. A fork with better observability beats the baseline by ~60%.

**Lesson for our setting:** exposing per-claim adjudicator *reasoning* (not just F1 or per-class counts) to the optimizer in the train tier likely improves optimization velocity. The optimizer can see *why* failures happened (e.g., "trailing citation marker not scrutinized") rather than just *that* they happened.

**Tier-safety check:** this is train-tier disclosure. Val remains scalar-only (D36) — no per-example reasoning flows back via val. Tier 1 fully-open permits per-example train data and reasoning traces. So this is within-discipline.

**Decision:** train dispatcher's rich-schema output includes per-claim adjudicator reasoning + verifier narrative + any failure-mode tags. Optimizer-side trace-aware metric (D36) can aggregate these into failure-mode counts and attribution (which subagent produced the miss). Update NEXT.md Task 5 train dispatcher spec; clarify that this is train-tier-only and does not leak into val dispatcher output.

## Synthesis — what survived, what got reduced, what's scooped

**Cleanest standalone subclaims (post-lit-review-2 sharpening):**
- Tier 2 scalar-only val as structural defense
- OS-level structural enforcement of leakage (extending Karpathy's instructional and VeRO's API-mediated)
- Declarative per-subagent heterogeneous controllability as an optimization surface + topology-as-search-space (integrated)

**Not contributions — standard hygiene or redundant framing (dropped during sharpening):**
- Train+val gap monitoring as stopping rule (textbook ML; cite and use, don't claim)
- Slash-command-as-SUT-packaging (equivalent to uv-package at invocation boundary; real differentiation is the declarative-vs-imperative config point above)

**Partial overlaps (cite and differentiate):**
- Agent-as-optimizer over agentic systems — Karpathy / Meta-Harness / VeRO / ADAS / AFlow / AlphaEvolve
- Reproducibility via committed snapshot — VeRO explicitly, autoresearch implicitly
- Three-tier train/val/test — VeRO (API-mediated), us (OS-level)
- Structural filesystem enforcement — autoresearch (instructional), VeRO (API), us (OS-level)
- Multi-subagent pipelines as research systems — AI Co-Scientist (fixed roster), Sakana AI Scientist v2 (fixed stages)
- Topology-as-optimization-variable — MASS, ADAS, AFlow (but flat-graph or homogeneous)
- Verifiable-reward-driven improvement — entire 2025-2026 wave
- Train-vs-val gap monitoring for stopping — textbook ML; AFlow plots both curves, stops on val plateau; we use gap monitoring as standard hygiene

**What paper-trail uniquely owns (un-scoopable):**
- Biomedical citation-integrity domain
- 9-way Sarol-adjudicated baseline
- INDIRECT-detection failure mode (named, diagnosed, remedied)
- Severity-under-commitment pattern
- Cost-per-claim practitioner numbers
- The integrated combination above

## Attribution patterns observed in this turn (for the human-value retrospective future paper)

**Pattern 2 (Human-surfaces-strategic-argument) — again.** Human raised, unprompted by Agent: *"do I fundamentally do this Claude Code specification of agents cannot spin up agents or whatever, which is totally valid?"* Agent had not clearly thought through the architectural implications of the depth-2 cap for our dispatcher architecture. Human's question forced the explicit articulation that the subprocess-launches-fresh-main mechanism sidesteps the cap at the process boundary. That articulation is now in the framework doc and is a cleaner statement than what was there before.

**Pattern 6 (Human raises reviewer-trap concerns Agent missed) — again.** Human: *"I've been surprised that this space was as untouched as we initially thought, given how popular Andrej Karpathy's posts have been on Twitter."* That skepticism triggered the targeted lit-review pass which found Meta-Harness + autoresearch + VeRO as material competitors. Without the skepticism, we would have proceeded with the pre-lit-review-2 novelty framing and been scooped in review.

**Pattern 7 (new) — Agent-under-supervision-produces-overclaims-that-Human-catches.** Agent's pre-lit-review-2 framing used "recursive subagent spawning" based on an aspirational reading of Claude Code capabilities. The orchestrator-subagent's deep read caught that Claude Code explicitly forbids subagent-spawning-subagents. This is a specific instance of a general pattern: Agent's synthesis under time pressure reaches for clean-sounding framings; Human's slower, skeptical reading catches where those framings overclaim the substrate. The corrective mechanism is targeted-lit-review-pass-after-agent-synthesis. Worth preserving as a distinct pattern (not Pattern 5 Human-catches-imprecision-in-the-moment, but Agent-supplies-clean-story-Human-triggers-verification).

## Doc updates triggered by this entry

Landing in this session (same commit):

1. `docs/plans/agentic-pipeline-optimization-framework.md` —
   - §3 "Optimizer agent initial configuration" — absorb autoresearch direct-lifts (D42): NEVER STOP, simplicity criterion, CAN/CANNOT structure, output-flood prevention, crash handling, anti-rabbit-hole, experiment-as-commit-unit, setup-with-human-checkpoint. Cite Karpathy `program.md` throughout.
   - §3 — explicit note on the subprocess-launches-fresh-main architecture that sidesteps the Claude Code depth-2 cap (D40 corollary).
   - Drop any "recursive" language that overclaims substrate.
   - Add new §8 "Related work and positioning" — four-bucket structure with specific competitor comparisons (D41).
   - §7 open problems — add #11 `--bare` + Agent-tool canary (D44).
   - Renumber sections 8–9 accordingly.

2. `docs/plans/paper-writeup-items.md` —
   - §"Open paper-level decisions" — resolve two-paper-split entry to "one paper, 2026-04-22 (D39)."
   - §"Core contributions" — reorder per D43 (case study primary, methodology subclaims secondary).
   - §"Ideas to borrow from prior art" — add entries for autoresearch (cite-as-extension-target + 12-item borrow-list), Meta-Harness (cite-as-substrate-inversion contrast), VeRO (cite-as-closest-infrastructure-competitor + 10-item borrow-list), AlphaEvolve (cite-as-paradigm-example), ADAS (cite-as-code-as-search-space-precedent), AFlow (cite-as-closest-figure-type-precedent), Ellenberg et al. (cite-as-contamination-warning).
   - §"Other paper-level threads" — add VeRO empirical negative finding as motivation for substrate choice.

3. `docs/plans/NEXT.md` —
   - Task 5 — add per-claim budget deliverable (D45), round-trip sanity canary (D46), train dispatcher per-claim adjudicator reasoning + verifier narrative (D47 — train-tier only).
   - Task 7 backlog — add `--bare` + Agent-tool canary (D44) as pre-Task-5 gate alongside Q9c memory-blind canary.
   - Update framework-first contribution ordering to reflect D43 consolidation.

4. Memory: `project_paper_positioning_topology_free.md` stays valid (topology-freedom is still the right call); no update needed. New memory not required — this journal entry is the durable decision log.

## What's next (session plan)

After doc updates land and are committed:
1. Run the `--bare` + Agent-tool canary + Q9c memory-blind canary in the same session (~30 min total).
2. Both resolved → Task 5 eval arm build unblocked.
3. Then start Task 5.

**Clarifications list from 2026-04-21 end-of-night is complete** — items #1–#5 walked through earlier today, #6 and #7 skipped under D38's decision rule. Next session picks up from Task 5 scoping or canary-gate execution, Human's call.
