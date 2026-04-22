# Items to touch on in the paper / blog writeup

Running notes for the paper-trail paper submission (CS conference + blog post). Captures paper-framing arguments, open questions, and terminology discussions that surfaced during experiment work. Will evolve; not a locked outline.

---

## What do we call this methodology?

**The thing we're doing:** iterate the paper-trail agent pipeline against the Sarol 2024 labeled benchmark, diagnose failure modes, edit prompts, rerun. The labels serve as a verifiable reward signal; the prompts (across multiple subagents) are the policy; we (human + LLM in discussion) are the optimizer.

**The terminology problem:**

- "Reinforcement learning with verifiable reward" (RLVR, per Karpathy / Tulu / DeepSeek-R1 literature) is literal gradient-based RL. Calling our work RL will upset readers with ML / math backgrounds — and they'd be right that it isn't.
- "Prompt optimization" undersells it and matches DSPy's typical scope (single prompt / single program). What we're doing is multi-prompt modular agentic-system iteration: extractor, adjudicator, and verifier each have their own prompts, and iteration may touch any subset plus the orchestration between them.
- "Prompt engineering" is too generic and carries a pejorative "vibes-based" connotation that misses the point (we have a verifiable benchmark; our iteration is metric-driven, not vibes-driven).

**Candidate names to test in prose:**

- **Benchmark-grounded agent iteration**
- **Verifier-in-the-loop pipeline refinement**
- **Agent-system prompt engineering with verifiable reward** (clunky but precise)
- **Multi-prompt pipeline refinement** (under-sells the verifier-loop shape)
- **Eval-driven agent development** (defensible, boring)
- "Prompt-level RLVR" (concedes the RL analogy; ML readers will still push back; risky)

Pick one and defend it. The paper's choice of name is itself a small contribution if no prior name is standardized.

**Lit-review question, resolved (2026-04-21 after 5-paper pass):** has the multi-prompt / agentic-system version of automated prompt optimization been named and formalized in published work? After reading DSPy / MIPROv2, TextGrad, OPRO, PromptBreeder, and the Reflexion / Self-Refine line full-text:

- **Multi-prompt pipeline optimization as a paradigm is NOT undeveloped.** DSPy (Khattab et al. 2023) and MIPROv2 (Opsahl-Ong et al. 2024) formalize it cleanly: specialized modules (`GenerateSearchQuery`, `GenerateAnswer`, `Retrieve`, etc.) composed into multi-stage programs, and Algorithm 1 in MIPROv2 jointly optimizes per-module instructions and demonstrations against a downstream metric. Our extractor / adjudicator / verifier decomposition is exactly this shape. **Claim B ("multi-subagent pipeline iteration formalized") cannot stand as a standalone contribution — it is prior art as of 2023–2024.**
- **The train+val-curve-over-optimization-steps figure shape is not novel either.** OPRO §5.4 + Figure 11 explicitly plot train and validation accuracy against optimization steps and discuss a 5–20% train-test gap; MIPROv2 Appendix G Figures 8–13 plot "Best Score So Far / Rolling Mean" vs evaluation calls. Both use algorithmic revisions, not human edits. **Claim A ("train+val curve over revisions") narrows to: human-revision-indexed x-axis applied to a multi-subagent pipeline, with divergence-as-stopping-rule.** OPRO explicitly declines val-based early stopping ("For simplicity, we do not set aside a validation set in our default setting… [early stopping] suggested as future work") — that is the specific gap we fill.
- **Train/test hygiene for prompt workflows is the cleanly unclaimed territory.** None of the five papers argues physical sealing of the test split, none argues policy-gated blindness of the researcher / planning session, and none frames the prompt-design session itself as the optimizer whose test exposure silently biases subsequent edits. DSPy §6 has a single hygiene sentence ("report extensive comparisons on the development set to avoid overfitting on test") — genuine prior art for "use dev, not test, during iteration" but not for the stronger claim. MIPROv2 Appendix H acknowledges a proposer-overfits-to-few-shots failure mode and "leave[s] better understanding this phenomenon as an exploration for future work." **Claim C ("train/test hygiene for prompt workflows — physical sealing + planning-session test blindness") is the strongest of the three and now leads.**

Net reshaping of contributions (propagated into §"Core contributions to argue" and NEXT.md §"Paper contributions pursued"): drop B as standalone, narrow A, lead with C.

Specific papers checked so far (full-text reads, 2026-04-21):

### Du et al. 2025, "A Survey on the Optimization of LLM-based Agents" (arxiv 2503.12434)

Taxonomizes agent optimization into **parameter-driven** (fine-tuning, RL) vs **parameter-free** (prompt engineering, RAG, retrieval, multi-agent collaboration). Covers the exact spectrum we discussed last turn (RLVR → DSPy → manual iteration).

What the survey does *not* contain (directly confirmed by full-text read):

- **No train/test split hygiene discussion.** Data construction and filtering are covered (trajectory evaluation, model-based scoring, rule-based scoring) but never from a train/test-contamination angle. The closest adjacent topic is "catastrophic forgetting" (fine-tuning SFT-only weakens general reasoning), which is unrelated to leakage discipline.
- **No verifier-in-the-loop iteration for non-weight-updating methods.** Verification appears only as a *post-hoc data filtering* mechanism (e.g., AgentOhana's AgentRater 0–5 scoring), not as a real-time loop for prompt compilation.
- **Multi-agent frameworks (SMART, COEVOL, Self-Talk, ATM, CMAT, CORY) are presented as data-generation mechanisms, not as architectures requiring end-to-end pipeline-level optimization with sealed test sets.** The survey *mentions* multi-agent as a category but does not formalize it as an optimization paradigm.
- **Section 7.5 explicitly lists "Parameter-Driven LLM-based Multi-Agent Optimization" as an open challenge.** Even the weight-updating case for multi-agent pipelines is unaddressed in the field. The *parameter-free* case — which is where our work sits — is even less formalized.

What this means for our writeup:
1. **Use the survey's taxonomy as our related-work backbone.** Position our work as the parameter-free + multi-subagent + train/test-hygiene point.
2. **Claim the gap.** The survey itself flags Section 7.5 as open; we can cite it directly as validation that multi-agent pipeline optimization methodology is unresolved.

### Zhang et al. 2026, "Hyperagents" (arxiv 2603.19461)

Self-referential agents where both the task agent and the meta-agent (the thing that proposes modifications) are editable. Extends the Darwin Gödel Machine framework. Agents self-modify via a meta-agent that reads the repo + previous evaluations + remaining iteration budget, proposes edits, applies them, evaluates on staged benchmarks, adds to an archive.

**Directly-quotable validations for our paper's hygiene argument:**

- > "AI judges are more likely to overfit to the training data. When a validation subset is defined for a domain, the performance component used in parent selection is measured on the validation set."

  This is paper-level validation of our Rule 2 (policy-gated test blindness). The Hyperagents authors observed the same overfitting risk in a *fully autonomous* setting and mitigated it with an explicit train/validation/test split. We are doing the same with an additional physical seal. Cite this as corroborating evidence.

- > Improving the coding agent "also enhances the system's ability to carry out future self-improvements" only because both evaluation and self-modification were coding tasks. This assumption "is unlikely to hold outside coding domains, where task-solving skills may differ substantially from the skills needed to analyze failures."

  This directly supports our human-in-the-loop choice. In our setting, the adjudicator's task (citation-integrity verdict) and the meta-task (analyzing failure modes to propose prompt edits) require different skills. Hyperagents solves this by evolving the meta-agent too; we keep the meta-agent as a human. That's the defensible positioning.

**Borrowable methodology ideas:**

1. **Staged evaluation gate.** Hyperagents screens candidates on 10 tasks first, then only the survivors run on the full 50/100-task benchmark. Matches our experiment plan's N=5 → N=50 → N=200–400 → N=2,141 cadence. Reassuring that our staging is standard practice.
2. **Archive of versions + evaluations.** Every candidate is kept with its eval result. For us: formalize a `experiments/sarol-2024/archive/<prompt-hash>/` tree where each adjudicator-prompt version is kept with its per-claim scores. Supports ablation tables in the paper.
3. **Transfer across domains.** Hyperagents showed meta-level improvements transfer from paper-review + robotics to math-grading. Analog for us: if our INDIRECT-detection fix is prompted correctly, it should transfer to other citation-integrity benchmarks (e.g., SemanticCite). Worth testing.
4. **Parent-selection policy.** "Proportional to performance, inversely proportional to number of children that successfully compiled." Not directly applicable in manual mode, but useful framing when we have multiple adjudicator-prompt variants in play at sweep time.

**Authors' own acknowledged limitations** (useful for positioning):

- **Frozen outer loop.** Parent selection and evaluation protocols stay fixed even as the agent evolves. In our work, *we* control the outer loop; this is a tradeoff (we cap the ceiling of autonomy but keep failure modes legible).
- **Fixed task distribution.** Hyperagents doesn't co-evolve tasks. Sarol's task distribution is likewise fixed from the benchmark; that's fine.
- **Saturation.** "Increasing performance from 0.7 to 0.8 is typically more challenging than from 0.0 to 0.1." Relevant when we're reporting improvements from low bases.

**What Hyperagents is NOT:**

- Not a comparison point for DSPy / MIPROv2 / TextGrad / OPRO / RLVR / GRPO — the paper doesn't benchmark against any of these. The only baseline is the original DGM plus a domain-customized variant.
- Not multi-prompt / multi-subagent pipeline. Hyperagents is a single-agent system that can modify itself; multi-domain evaluation is performed by the *same* agent across tasks, not by a pipeline of specialized subagents.

**Our positioning relative to Hyperagents:**

- Hyperagents = fully autonomous, single-agent, meta-agent-editable, evolutionary search.
- paper-trail-with-Sarol = human-in-the-loop, multi-subagent pipeline, meta-agent = researcher, deliberate search.

We occupy a different point on the same spectrum. We cite Hyperagents as (a) the autonomous extreme, and (b) an independent confirmation that the AI-judge-overfitting risk is real.

### DSPy / MIPROv2 (Khattab et al. 2023; Opsahl-Ong et al. 2024)

arXiv: 2310.03714 (DSPy); 2406.11695 (MIPROv2)

**Claim A (train+val curve over human-driven revisions as published figure):** PARTIAL — MIPROv2 Appendix G Figures 8–13 publish the figure *shape* we want ("Best Score So Far" / "Rolling Mean" vs evaluation calls across trials on ScoNe, HotPotQA, HoVer, Iris, Heart Disease), and Appendix H Tables 5–10 show prompt progressions at Trial 10 / 50 / 330. But revisions are **algorithmically proposed by an LM proposer under Bayesian / surrogate search**, not human edits. DSPy itself publishes final-metric tables only (Tables 1–2), no curves. The figure shape is prior art; the human-revision-indexed x-axis and divergence-as-stopping-rule semantics are not something DSPy/MIPRO present.

**Claim B (multi-subagent pipeline iteration):** **FAIL — scooped.** DSPy is explicitly a multi-stage, multi-module pipeline optimizer. Modules are specialized by signature (e.g., `GenerateSearchQuery`, `GenerateAnswer`, `Retrieve`, `MultiChainComparison`, `ReAct`) and composed into programs like `BasicMultiHop` and `ThoughtReflection`. MIPROv2 §3–5 explicitly factorizes optimization per-module: Algorithm 1 optimizes `[ι₁…ιₘ]` and `[d₁..ₖ,₁…d₁..ₖ,ₘ]` *across modules* to maximize the downstream metric. Our extractor / adjudicator / verifier trio is exactly the multi-stage-specialized-module shape DSPy/MIPROv2 defined first. Must cite as prior art.

**Claim C (train/test hygiene for prompt workflows):** PARTIAL — DSPy §6 contains a single hygiene sentence: "We sample 200 and 300… for training and development… final evaluations use the 1.3k official test set examples. We report extensive comparisons on the development set to avoid overfitting on test." That is prior art for "use dev to avoid test overfitting" in prompt-pipeline optimization. MIPROv2 Appendix H acknowledges an overfitting failure mode: "one of the failure modes of our current proposers is the tendency to overfit instructions to the few-shot examples provided in the meta-prompt" and "we leave better understanding this phenomenon as an exploration for future work." Neither paper addresses researcher-in-the-loop as an optimizer, neither proposes physical sealing, neither discusses planning-session contamination. Our stronger claim survives.

**Quotable observations:**
- DSPy §6: "We report extensive comparisons on the development set to avoid overfitting on test" — cite as prior art for train/dev/test discipline in prompt-pipeline optimization.
- DSPy §3: teleprompters optimize "all modules in the pipeline to maximize a metric" — canonical statement of pipeline-as-optimization-target.
- MIPROv2 Abstract: "MIPRO outperforms baseline optimizers on five of seven diverse multi-stage LM programs (Llama-3-8B) by as high as 13%" — quantitative baseline for algorithmic pipeline optimization.
- MIPROv2 Appendix G, Figures 8–13: "Best Score So Far / Rolling Mean" vs evaluation calls — published figure whose shape we're repurposing on a human-revision axis.
- MIPROv2 Appendix H overfit note ("tendency to overfit instructions to the few-shot examples… leave better understanding this phenomenon as an exploration for future work") — open problem our human-hygiene contribution addresses.

**Limitations they acknowledge:**
- MIPROv2 Limitations §: fixed proposer / task LM; "restricted ability to infer the rules governing complex tasks without a hand-written seed prompt"; single budget regime tested.
- MIPROv2 Appendix H: overfit-instruction failure mode explicitly left to future work.
- Neither paper discusses the planning-session-as-optimizer threat model.

**Novelty implication:** Claim B is scooped — DSPy/MIPROv2 formalized multi-stage pipeline optimization with specialized modules in 2023–2024. Cite as prior art; narrow our contribution to human-in-the-loop + citation-integrity + hygiene. Claim A is weakly novel: figure shape exists, only x-axis semantics (human revision index) and divergence-as-stopping-rule differ. Claim C's strongest form survives — DSPy/MIPROv2 do not argue physical sealing or planning-session blindness.

### TextGrad (Yuksekgonul et al. 2024)

arXiv: 2406.07496

**Claim A (train+val curve over human-driven revisions as published figure):** PASS — TextGrad iterations are fully algorithmic (the `∇_LLM` operator proposes edits; Textual Gradient Descent regenerates the prompt). No human in the loop. On the figure question, TextGrad does not publish a train-vs-validation loss-curve figure at all: §3.3 uses validation-based early stopping ("After each iteration, we run a validation loop… if the performance is better than the previous iteration we update the Prompt") but Table 3 shows only final accuracies. The one iteration-axis plot (Figure 3, radiotherapy) tracks clinical dose metrics on a single cohort. Both the human-driven x-axis and the train+val divergence figure are clean for us against TextGrad specifically.

**Claim B (multi-subagent pipeline iteration):** PASS — TextGrad frames around "compound AI systems" and a computation-graph abstraction, but every published application is a homogeneous LLM-call graph, not a multi-specialized-subagent pipeline. Code optimization, solution optimization, and prompt optimization are single-LLM graphs with one learnable variable and a scalar/textual loss. Molecule design (§3.4) and radiotherapy (§3.5) are hybrid LLM + numerical-simulator loops — still no role specialization, no extractor/adjudicator/verifier-style decomposition. (Note: DSPy/MIPROv2 still scoops Claim B; TextGrad does not.)

**Claim C (train/test hygiene for prompt workflows):** PASS — Mixed hygiene with no researcher-blindness discussion. Prompt optimization (§3.3) uses train/val/test splits with val-based stopping — standard ML hygiene, cite as prior art for "val exists." But instance/solution optimization (§3.2) refines the same test instance across 3–5 iterations under self-supervision with no held-out check. Radiotherapy (§3.5) uses N=5 patients with in-context paired examples whose provenance vs the eval set is not stated. Paper never discusses whether the prompt author saw test splits while designing TextGrad's own scaffolding.

**Quotable observations:**
- TextGrad Abstract: "developing principled and automated optimization methods for compound AI systems is one of the most important new challenges" — same problem statement; we offer the human-in-the-loop + hygiene-disciplined analog.
- Cite as prior art for val-based stopping: §3.3 — "After each iteration, we run a validation loop with the validation set of the datasets, and if the performance is better than the previous iteration we update the Prompt."
- Undercut to disclose: GSM8k initial prompt "You will answer a mathematical reasoning question. Think step by step." evolves over 12 algorithmic iterations into guidance like "Restate the problem… Verify each step… re-check calculations" — essentially *automatic* manual-style prompt revision; our contribution must be "human-driven + pipeline + hygiene," not "iterative prompt editing is new."
- Undercut: §3.1 code + §3.2 solution optimization refine the *same* test instance across iterations with self-supervised loss and do not treat this as leakage — we can cite this to motivate physical sealing.
- Table 3 / §3.3 reports only final accuracy; no iteration-axis accuracy curves and no train-vs-val divergence figure — the curve-figure shape we're proposing is not in TextGrad.

**Limitations they acknowledge:** need for broader domain testing and LLM compatibility (framed generically, not as a hygiene concession); no discussion of researcher blindness, prompt-engineer bias, or test contamination via human scaffolding design; radiotherapy validated on only 5 patients.

**Novelty implication:** All three claims survive TextGrad *on its own*. TextGrad is the closest neighbor in spirit (same compound-system motivation, same iterative loop) but is algorithmic, homogeneous-call, and hygiene-light. Positioning: "human-in-the-loop analog of TextGrad for multi-subagent citation-integrity pipelines, with explicit physical test-sealing hygiene that TextGrad's automatic setting never addresses." Cite TextGrad as the automated counterpart.

### OPRO (Yang et al. 2023 / ICLR 2024)

arXiv: 2309.03409

**Claim A (train+val curve over human-driven revisions as published figure):** **PARTIAL — closest precedent.** OPRO publishes accuracy-vs-optimization-step curves (Figures 1, 4, 6, 12), and §5.4 + Figure 11 explicitly plot train AND val accuracy on the same axes as a post-hoc overfitting analysis (caption: "The exemplars are splitted to 1/3 training, 1/3 validation and 1/3 test. We compute the validation accuracy every 3 steps"). The figure *shape* is prior art — we cannot claim it as novel. However, OPRO iterations are LLM-proposed ("the LLM generates candidate solutions… based on the optimization problem description and previously evaluated solutions in the meta-prompt"), not human-driven; they explicitly decline val-based early stopping ("For simplicity, we do not set aside a validation set in our default setting… [early stopping] suggested as future work"); and they argue overfitting is "less harmful" rather than treating divergence as a stopping signal. The *human-revision-indexed, divergence-as-stopping-rule* framing is not OPRO's; the bare figure type is.

**Claim B (multi-subagent pipeline iteration):** PASS — OPRO is a meta-optimizer loop over a **single instruction string** applied to one scorer LLM. "Optimizer LLM + scorer LLM" is a two-role meta-setup, not a multi-specialized-subagent pipeline (no extractor/adjudicator/verifier decomposition; no orchestration graph). Related work in OPRO does not discuss pipeline-level optimization.

**Claim C (train/test hygiene for prompt workflows):** PASS — OPRO uses training set for optimization and held-out test for final numbers, but (a) the test set is not physically sealed; (b) they acknowledge train accuracies run 5–20% above test; (c) no discussion of researcher-in-the-loop contamination, meta-prompt designer test exposure, or planning-session blindness. Physical sealing + main-session policy-gating is not prefigured here.

**Quotable observations:**
- OPRO frames prompt search as LLM-driven optimization against a scorer, producing accuracy-vs-step curves — prior art for "optimization curve" visualization of prompt iteration (Figures 1, 4, 6).
- §5.4 + Figure 11 plot train vs val accuracy over optimization steps and acknowledge a 5–20% train-test gap — **closest precedent to our headline figure**; we must cite it and explicitly distinguish (human-driven axis, divergence-as-stop).
- OPRO declines to use val for early stopping (§5.4) — leaves the "divergence as honest stopping signal" gap explicit.
- Meta-prompt at each step contains "the best 20 instructions so far and 3 randomly picked exemplars from the training set" — basic split hygiene, no researcher-contamination discussion.

**Limitations they acknowledge:**
- Overfitting acknowledged but downplayed: "training accuracies are often 5%-20% higher than our test accuracies… our test and overall accuracies are still mostly higher than human-written counterparts" (§5.4).
- Early stopping / validation-driven stopping explicitly deferred to future work.
- No acknowledgment of human/researcher contamination risk when humans design meta-prompts with benchmark knowledge.

**Novelty implication:** Claim A must be narrowed — the train+val-over-optimization-step figure type is prior art (OPRO Figure 11). What remains: (i) human-revision-indexed x-axis, (ii) divergence as stopping criterion (OPRO explicitly declines this), (iii) the plot driving an actual stop decision. Rewrite Claim A to foreground those three distinctions. Claim B is clean against OPRO (their two-role meta-loop is not a multi-subagent pipeline). Claim C is clean against OPRO — they acknowledge the train-test gap without solving it; validating precedent for the problem, not for our solution.

### PromptBreeder (Fernando et al. 2023)

arXiv: 2309.16797

**Claim A (train+val curve over human-driven revisions as published figure):** PASS — Figure 3 + Appendix B shows a generation-by-generation fitness curve (blue dots = individual fitness, red line = population mean) but plots training-set fitness only, no train-vs-held-out separation, no overfitting-divergence analysis. Curve is driven by LLM-generated mutations under an evolutionary algorithm, not researcher-driven manual edits.

**Claim B (multi-subagent pipeline iteration):** PASS — PromptBreeder evolves a "unit of evolution" containing typically two task-prompts plus a mutation-prompt applied sequentially to the same single-turn problem. Conclusion explicitly: "the topology of prompting remains fixed… we only adapt the prompt content not the prompting algorithm itself." No specialized subagent roles, no heterogeneous pipeline, no pipeline-level optimization target.

**Claim C (train/test hygiene for prompt workflows):** PASS — Training set for fitness evaluation (100 Q&A per eval, §3); for four asterisked datasets in Table 1, a random 50/50 train/test split. No discussion of researcher-in-the-loop contamination, no physical sealing, no planning-session blindness.

**Quotable observations:**
- §3: fitness is measured on "a batch of 100 Q&A pairs from the entire training set" — no dev/val layer.
- Conclusion: "the topology of prompting remains fixed… we only adapt the prompt content not the prompting algorithm itself" — explicit scope admission we can cite to motivate pipeline-level optimization.
- Appendix B / Figure 3: generation-wise fitness curve is training-only — useful contrast for our train+val figure.
- Table 1: ad-hoc 50/50 splits on only four datasets; most evaluated without explicit held-out-test discipline.

**Limitations they acknowledge:** system "remains limited compared to the open-endedness of human thought processes"; topology is fixed; no explicit overfitting-across-generations limitation acknowledged (useful gap for us).

**Novelty implication:** All three claims survive PromptBreeder. Closest overlap is the generation-wise fitness plot, but single-curve, training-only, algorithmically-driven. Clean contrast paper: fixed topology, no operator-contamination discussion, no pipeline-level target.

**Adjacent (EvoPrompt / ProTeGi):** Both are single-prompt algorithmic optimizers (EvoPrompt: evolutionary operators over a prompt population; ProTeGi: natural-language "gradients" + beam search). Neither targets a multi-subagent pipeline, neither reports train-vs-val divergence curves, neither discusses researcher-in-the-loop hygiene. Same contrast story — reinforces novelty of all three claims.

### Reflexion + Self-Refine + follow-ups (Shinn 2023; Madaan 2023)

arXiv: 2303.11366 (Reflexion); 2303.17651 (Self-Refine)

**Framing note:** Reflexion and Self-Refine are primarily **inference-time self-improvement** — the model improves *within a single run* by reflecting on its own output. Our work is **offline iteration** — the researcher + LLM discuss failure modes and edit prompts between runs. Related regimes, distinct optimizers.

**Claim A (train+val curve over human-driven revisions as published figure):** PASS — Both papers plot metric-vs-iteration curves, but the iteration axis is *inference-time within-run trial index* (Reflexion: HumanEval/HotpotQA/AlfWorld trials against the same task instance with an accumulating episodic memory; Self-Refine: "Iteration 0 to Iteration 2" rate-of-refinement on a single output). Neither axis represents offline human-driven prompt revisions, neither reports train vs val macro-F1 separation, neither discusses overfitting of the prompt system as a stopping signal. Self-Refine caps at iteration 2 per output with no overfitting analysis.

**Claim B (multi-subagent pipeline iteration):** PARTIAL — Reflexion names three modules (Actor, Evaluator, Self-Reflection), which at first glance looks like a specialized-subagent pipeline. But (i) same LLM with different prompts, not separately-tuned specialized agents; (ii) optimization object is the Actor's memory buffer at inference time, not the pipeline prompts across revisions; (iii) no offline iteration of the three component prompts against a labeled benchmark. Self-Refine is explicitly single-model (generator = refiner = feedback-provider). Weak prior at best; DSPy/MIPROv2 is the stronger prior art for Claim B.

**Claim C (train/test hygiene for prompt workflows):** PASS — Neither paper discusses prompt-engineering-as-optimizer leakage, physical test sealing, or policy-gated blindness of the planning / prompting session. Reflexion uses standard benchmark test splits as frozen eval substrates, not as something the prompt-design session could contaminate. Fully unclaimed in this line.

**Quotable observations:**
- Reflexion's modules share one LLM and differ only in prompt; the "policy" updated across trials is an episodic memory buffer, not the Actor/Evaluator/Self-Reflection prompts themselves.
- Self-Refine "uses a single LLM as the generator, refiner, and feedback provider" — explicitly single-agent self-critique, not a pipeline.
- Both report metric-vs-iteration curves, but iteration index is inference-time trials on one task instance, not offline prompt revisions across a dataset.
- Self-Refine terminates by iteration 2; no overfitting signal or honest stopping criterion against held-out data.
- Neither paper's limitations section raises prompt-engineering leakage into the test set or into the prompt-design session.

**Notes on follow-ups:**
- *ACE / prompt-learning agents (2024–25)* — consolidate experience into reusable "playbooks" at inference time; still within-run / online; no offline train/val/test framing.
- **MA-SAPO, MAPRO, Multi-Agent Design (2025)** — multi-agent prompt optimization pipelines with evaluation-driven objectives. *Relevant to Claim B specifically* — these ARE pipeline-level optimization, and they're 2025 so they post-date DSPy/MIPROv2 but extend the paradigm. Algorithmic, not human-in-the-loop; train/test hygiene not their pitch. **Flagged for a separate follow-up lit-review pass** — they don't change the "Claim B is scooped" verdict (DSPy/MIPROv2 already did that in 2023–2024) but they're additional prior art we must cite and distinguish.
- *Language Agent Meets Offline RL Critic (EMNLP 2024)* — "offline" here means offline RL on Reflexion-style traces, not offline prompt iteration; not a collision.

**Novelty implication:** Claims A (human-driven revision axis with overfitting divergence as stop signal) and C (physical sealing + planning-session blindness) are clean against the Reflexion/Self-Refine line and direct descendants. Claim B is a weak PARTIAL hit here and already a stronger hit against DSPy/MIPROv2; will face additional pressure from MAPRO / MA-SAPO / Multi-Agent Design 2025.

### MAPRO (Zhang et al. 2025)

arXiv: 2510.07475. "Recasting Multi-Agent Prompt Optimization as Maximum a Posteriori Inference."

**Claim A:** CLEAN. Figure 3 plots joint validation pass-rate across 10 algorithmic iterations (MBPP+ only); no train-vs-val divergence, no human-in-the-loop. Stopping rule is a patience window on validation gains (§3.4, T=3, ε≈0) — plateau detection, not divergence detection. Add alongside OPRO Fig 11 and MIPROv2 App G in the algorithmic-loop precedent cluster; does not threaten our specific figure type.

**Claim B:** FURTHER SCOOPED. MAPRO formalizes MAS prompt optimization as MAP inference over a DAG, introduces topology-aware credit assignment via reversed-topology "blames" (§3.3 — natural-language, not scalar). More directly on-point than DSPy/MIPROv2 for "specialized subagents with per-agent prompt updates." Keep B dropped; MAPRO is now the strongest 2025 prior art for that formalization.

**Claim C:** CLEAN. No discussion of leakage, contamination, or test-set blindness. Train/test is a plain index slice (App B.1: "first 100 records for optimization, rest 64 for testing") with unfettered optimizer access to training split. Strong motivation citation for our hygiene contribution — MAPRO is an exemplar of the practice Claim C argues is insufficient.

### MA-SAPO (Seo et al. 2025/2026)

arXiv: 2510.16635 v2. "MA-SAPO: Multi-Agent Reasoning for Score-Aware Prompt Optimization."

**Claim A:** CLEAN. No iteration loop — single-pass test phase (§3.3). No convergence plot, no stopping rule, no human revision. Fig 2 is a KDE of score distributions, not a trajectory.

**Claim B:** Confirms B is scooped but for a different reason than DSPy/MIPROv2. Five-role sequential decomposition (Explainer → Diagnostician → Synthesizer; Analyzer → Refiner; §3.2–3.3). Another point in the multi-agent-optimization design space; cite as contemporary example, not prior-art-that-scoops-us specifically.

**Claim C:** CLEAN. Zero discussion of train/val/test hygiene. Retrieval corpus built from HelpSteer2 train, evaluated on HelpSteer1/2 validation (§4.1) with no leakage analysis. Their silence in our favor.

### MASS — "Multi-Agent Design" (Zhou et al. 2025, ICLR 2026)

arXiv: 2502.02533. "Optimizing Agents with Better Prompts and Topologies."

**Claim A:** CLEAN. Fully automated; reports only validation trajectories (Fig 6). No train-vs-val divergence plot, no overfitting-based stopping, no human-in-the-loop axis.

**Claim B:** ADDITIONAL PRESSURE BEYOND DSPy/MIPROv2. MASS jointly optimizes prompts + topology — three stages: block-level APO → topology search → workflow-level prompt opt. Contradicts PromptBreeder's fixed-topology stance. Formalizing "specialized subagent pipeline + human-revised prompts" as standalone is not viable; MASS lands the formalization harder than we could. **Framing pivot:** position our constraint as *"pipeline topology held fixed by design, prompts are the only tuned axis"* (see borrowing item 2.1 below) — makes Claim B's narrowing principled rather than defensive.

**Claim C:** CLEAN. MASS explicitly does not address test-set sealing or contamination (§4 / App B specify splits only). Rule 1 / Rule 2 hygiene untouched.

### BetterTogether (Soylu, Potts, Khattab 2024, EMNLP main)

arXiv: 2407.10930. "Fine-Tuning and Prompt Optimization: Two Great Steps that Work Better Together." Released as the `BetterTogether` optimizer in DSPy.

**Claim A:** CLEAN. Table 1 reports final numbers only; no learning curves, no stopping criteria (BFRS searches over 6 candidate few-shot prompts; fine-tuning fixed at 5 epochs). No human-in-the-loop.

**Claim B:** SCOOPED FURTHER. §2 and Appendix A formalize "LM programs" with per-module prompts π_i and weights θ_i; HotPotQA uses three modules (two hop-query + answer) and optimizes end-to-end via bootstrapped traces with "no gold labels for any intermediate stages" — exactly our extractor/adjudicator/verifier setting. Confirms dropping B as standalone; this is the formalism we inherit.

**Claim C:** CLEAN. Standard train/dev/test splits with no sealing / blinding / hygiene procedures discussed. Limitations section admits "we do not yet understand why both are important" but no leakage discussion.

### Net lit-review verdict (2026-04-21, updated after 9-paper pass)

| Claim | Verdict | Action |
| --- | --- | --- |
| A — train+val curve over human-driven revisions | **Narrowed** | Cite algorithmic precedent cluster: OPRO Fig 11 (closest — train+val on shared axes), MIPROv2 App G (best-score-so-far), MAPRO Fig 3 (patience-window stopping), MASS Fig 6 (validation trajectory). Novelty rests on: (i) human-revision-indexed x-axis, (ii) divergence-as-explicit-stopping-rule (OPRO defers, MAPRO uses plateau instead), (iii) applied to a multi-subagent pipeline with train-vs-held-out divergence visible (absent from all cited prior art). Retain as headline figure. |
| B — multi-subagent pipeline iteration formalized | **Drop as standalone** | Scooped by DSPy (Khattab 2023) + MIPROv2 (Opsahl-Ong 2024) + BetterTogether (Soylu 2024) + MAPRO (Zhang 2025) + MASS (Zhou 2025) + MA-SAPO (Seo 2025). Our pipeline shape is the DSPy-LM-program shape. **Framing pivot (new after MASS):** position "pipeline topology held fixed by design, prompts are the only tuned axis" as our owned constraint, explicitly contrasting MASS which searches topology. |
| C — train/test hygiene for prompt workflows | **Clean — leads** | No prior art in any of the 9 papers. DSPy §6 has standard "use dev not test"; MIPROv2 App H defers algorithmic-overfitting as future work; MAPRO, MA-SAPO, MASS, BetterTogether report splits without sealing/blinding discussion. Physical sealing + policy-gated main-session blindness + "planning session IS the optimizer" framing is unclaimed. MAPRO and MA-SAPO are strong motivation citations as exemplars of the practice Claim C argues is insufficient. |

### Open follow-up lit-review items (non-blocking)

- **AutoGen, CAMEL, multi-agent-debate papers.** Du et al. 2025 survey already reviewed these as data-generation mechanisms. Skim only if a reviewer flags.
- **Systematic Survey of Automatic Prompt Optimization (EMNLP 2025).** Surfaced by the first-pass Reflexion subagent. Potential one-stop related-work reference; worth a skim.
- **ACE / prompt-learning agents (2024–25).** Surfaced by Reflexion subagent; inference-time "playbooks." Likely not relevant to our offline regime. Defer unless a reviewer flags.
- **JSON prompting (Twitter-surfaced 2026-04-21).** Quick characterization pending; backlogged from Human's aside. See §"JSON prompting — quick note" below.

---

## Ideas to borrow from prior art (with provenance)

Consolidated from the secondary lit-review pass (2026-04-21) across all 9 papers. Purpose: adopt best practices with inline citation provenance, not just defensive-novelty accounting. Each item has an **adopt cost** (low / medium / high) and **citation class** (cite-as-prior-art / adapt-freely / re-implement-and-cite).

### Top-priority adopts (dedup'd across papers, ranked by value/cost)

These are items that surfaced in multiple reports or that unlock downstream work at low cost. Adopt first.

1. **Multi-seed evaluation at every landmark (3-5 seeds, report mean ± std).** Convergent signal from MIPROv2 (5 seeds, App G variance bands), TextGrad (Table 1 `0.36 ± 0.018`), BetterTogether (§4 "3 random seeds"), OPRO (Fig 11 3-rep shaded stds), MASS (§4 "3 times on validation"). Our LM backend is non-deterministic (Tier 2 invariant per our framework); without seed replication we can't distinguish version gains from sampling noise. **Cost:** medium (compute). **Class:** cite-as-prior-art. **Action:** before claiming any v<N+1> > v<N>, run ≥3 seeds per landmark and report `macro-F1 ± σ` with bold-wins. Add to `validate_run.py` invariants as a required output.
2. **Topology-freedom as framework-enabled positioning** (three-bucket related-work contrast). The extractor → adjudicator → verifier trio is v1 seed knowledge, not a design commitment. The optimizer agent may restructure the pipeline freely — split/combine/create prompts, add/drop subagents, add tool calls, search for MCPs. Three-bucket related-work structure: (i) hand-crafted fixed topology (PromptBreeder §6, DSPy/MIPROv2, BetterTogether), (ii) hand-crafted topology search (MASS), (iii) **ours** — topology is a free variable for the optimizer agent; framework does not prescribe a search procedure. Framing claim: Claude Code removes the substrate friction that made fixed topology a necessity in 2023–2024; in this substrate the principled move is to step out of the way and let the agent choose. **Cost:** low (framing paragraph). **Class:** cite-as-prior-art (three-bucket contrast). **Action:** one paragraph in related work distinguishing the three regimes; methods section notes topology-freedom as the optimizer's first-class affordance (see framework doc §3 "Optimizer agent initial configuration"); limitations section names the overfitting-via-complexity surface (caught structurally by Tier 2 val-scalar). Full decision log: `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D32/D33.
3. **Best-score-so-far + rolling-mean + variance-band plot on revision index.** MIPROv2 App G Figs 8-13 visual grammar; OPRO Fig 11 train+val with ±1σ shaded bands (3-rep averaging). Our headline figure: paper-trail-v<N> version index on x, macro-F1 on y, per-seed dots + best-so-far step + rolling mean + shaded variance + train vs held-out divergence annotated. Reviewers read this instantly. **Cost:** low (figure design). **Class:** cite-as-prior-art.
4. **Mini-batch during iteration, full-set on landmarks** (MIPROv2 §3.2: batch B per trial, full eval every S steps). Maps directly to our graduated N: N=10/25 are mini-batch noise-floor checks during iteration; N=50/100/200 are landmarks tied to `paper-trail-v<N>` tags; N=2141 is the one-shot final. Don't re-run 200 on every revision. **Cost:** low (framing-of-existing-plan). **Class:** cite-as-prior-art.
5. **DSPy trace-aware metric pattern as optimizer-owned diagnostic tool** (DSPy `metric(example, pred, trace=None)`; Reflexion-style failure-reason decomposition curve Fig 3b). Eval arm emits raw per-subagent traces + macro-F1 + per-class F1 (Tier 1, topology-agnostic). Optimizer agent owns a mutable trace-aware metric, seeded at v1 with {extractor recall, adjudicator conditional F1 given good extraction, verifier flip rate + flip precision, per-failure-mode counts}, that it rewrites as paper-trail-v<N>'s topology evolves. Directly addresses INDIRECT-detection diagnosis and supports the Reflexion Fig 3b failure-mode-stacked plot as a derived artifact. **Cost:** medium. **Class:** adapt-freely. **Decision log:** `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D36.
6. **Per-revision archive on GitHub; framework-reproducibility surface in the paper appendix.** We adapt the MA-SAPO App H / MAPRO App D / DSPy `optimized_program.save()` reproducibility norm but target the *framework* surface, not the case-study prompts. Their appendices publish *their systems'* prompts because their system IS the contribution; our contribution is the framework and paper-trail is the case study.
   - **On GitHub, per `paper-trail-v<N>`:** emit `paper-trail-v<N>.json` under `archive/` with {per-subagent prompt content, spec files, rubric examples, eval-arm git tag, model aliases, `.claude/settings.json` hash, MCP config hash, optimizer workspace snapshot including the trace-aware metric per D36}. Grep-friendly diffs across versions; slots into Task 5's `expected_invariants.json` schema.
   - **In the paper appendix (framework-reproducibility, stable across epochs):**
     - Optimizer initial system prompt — D34 affordance catalog + performance-not-cost philosophy + fight-Python-default guidance. Tier 1 invariant per framework §3.
     - Tiered-leakage operational spec — filesystem layout, `--add-dir` scopes per role, dispatcher locked JSON output schemas.
     - Headless Claude Code invocation pattern — exact `claude --bare --print …` command + flag rationale + memory-blind mechanism.
     - Memory-blind canary design + result (once Q9c resolves).
     - Eval dispatcher CLI contracts — args, exit codes, output schemas.
   - **Not in the appendix:** per-revision subagent prompts. Those are epoch-dependent case-study artifacts and live on GitHub only. **Human rationale 2026-04-22:** *"everything about paper-trail is going to change over the course of epochs… the actual three agents as it stands now instructions, I think, is not the focus of the paper."*
   - **Cost:** low. **Class:** adapt-freely. Decision log: `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D37.
7. **MIPROv2 three-way ablation column structure** (baseline | instructions-only | demos-only | joint). Our headline table: baseline prompt | human-revised instructions (fixed rubric examples) | fixed instructions (bootstrapped examples) | both revised. Isolates whether gains come from instruction-engineering vs example-selection — reviewers will ask. **Cost:** medium (requires single-lever runs, not just joint). **Class:** re-implement-and-cite.
8. **Reflexion Fig 1 tri-column trajectory figure** (rows: task / trajectory / evaluation / reflection / next-trajectory; red/green highlighted spans). Our analog: paper-trail-v1 vs v2 vs v3 on one Sarol INDIRECT-detection example with red-highlighted wrong adjudication spans and green-highlighted corrected ones. Strongest methods-section visual for the qualitative narrative. **Cost:** medium (requires clean example from run logs). **Class:** adapt-freely.
9. **Reflexion Fig 3b failure-reason decomposition curve.** Stack our Sarol failure-mode taxonomy (INDIRECT-miss, bib-only-ghost, year-mismatch, severity-under-commitment, etc.) across revision index to show which modes retire when. Directly tests "human revisions retire one failure mode at a time." **Cost:** medium (requires per-example failure-mode tags across revisions). **Class:** adapt-freely.
10. **ProTeGi natural-language "gradient" template as a seeded optimizer pattern for failure-mode enumeration.** The optimizer agent (not Human — reframed post-D32 agent-only) uses ProTeGi's `<START>...<END>` delimiter template for structured failure-mode analysis: given a minibatch of failing train examples + the current subagent prompts, the optimizer enumerates N hypotheses in delimiters, each becoming a candidate edit. Matches ProTeGi's native design (template was always intended for LLM consumption, not Human journaling — the pre-reframe borrow was slightly miscast). Seeded in the optimizer's initial prompt as a known-good pattern, not enforced — purely agentic per D36's "transparency-only norm." The enumerated hypotheses + committed edit archive per revision on GitHub (feeds framework §7 open problem #5 — per-revision rationale capture). **Cost:** low (template in the optimizer's seed prompt). **Class:** cite-as-prior-art (ProTeGi App A.1.1 + TextGrad Eq 6/9 as dual references). Appendix destination: the template appears in the paper appendix as part of the optimizer's seeded patterns (framework reproducibility per D37); per-revision hypotheses go on GitHub.

### Per-paper borrowing catalog

Full per-paper detail from the secondary pass subagent reports. Consolidated below; items that appeared in the top-10 above are referenced by number and not repeated.

#### DSPy / MIPROv2 borrows
- **Signature/LM-program formalism** for extractor / adjudicator / verifier I/O contracts (DSPy Signatures; BetterTogether §2). Define three Signature-style dataclasses in `experiments/sarol-2024/specs/` with `desc=` strings as authoritative spec; prompts generated from these. Eliminates spec↔prompt drift. **Cost:** medium. **Class:** re-implement-and-cite. See #5 for per-stage metric integration.
- **MIPROv2 instruction-proposer field schema** (`dataset_description`, `program_code`, `program_description`, `module`, `task_demos`, `previous_instructions`, `basic_instruction`, `tip`). Our revision journal entries record these seven fields so human-driven revisions and future automated optimizers share a schema. **Cost:** low. **Class:** re-implement-and-cite.
- **Bootstrap demonstrations** by filtering pipeline traces with metric μ (DSPy BootstrapFewShot; MIPROv2 §3.1). Log every (extractor input → adjudicator verdict → gold match) triple; auto-promote high-F1 traces into a candidate pool for rubric worked-examples. Human curates final picks; candidate generation is mechanical. **Cost:** low. **Class:** adapt-freely.
- **MIPROv2 App H algorithmic-overfitting limitation** cited as prior acknowledgment in our Limitations: "sealed-test hygiene defends against dataset overfitting but not against algorithmic overfitting to Sarol's 9-class taxonomy itself." **Cost:** low. **Class:** cite-as-prior-art.
- Items #3, #4, #5, #6, #7 above are primarily from this line.

#### TextGrad borrows
- **Variable / `role_description` / backward / step abstraction** (§2, Code Snippet 2, Fig 1c). Frame our three subagent prompts as Variables with role_description fields. Diagram (Fig 1c analog) becomes a clean methods figure showing which edges the human edits and which the eval arm holds fixed. **Cost:** low (diagram + notation). **Class:** cite-as-prior-art.
- **Textual-gradient template** (§2 Eq 6, Eq 9 update rule). Give Human a one-page failure-analysis template mirroring Eq 6 per failed Sarol item: (input, subagent output, criticism, targeted Variable). Revision commits reference filled template. **Cost:** low. **Class:** adapt-freely (see also #10).
- **Before/after prompt snapshot as worked example in §Methods** (GSM8k box, 72.9% → 81.1%). Reproduce for our adjudicator prompt between paper-trail-v1 and paper-trail-v<latest>, annotating which failure class each delta addresses. **Cost:** low. **Class:** adapt-freely.
- **LLM-as-loss for non-scalar signals** (§3.4 Eq 17, §3.5). For error classes Sarol's gold labels don't cover (quote-span quality, evidence sufficiency), define an LLM-judge loss node *inside the eval arm* pinned per paper-trail-v<N> tag. Keeps macro-F1 as headline; secondary gradient signal without hand-crafting per-iteration rubric. **Cost:** medium. **Class:** re-implement-and-cite.
- **Explicit instance-vs-prompt optimization distinction + hygiene gap we fix** (§2 framing + §3.2 same-instance refinement). Quote TextGrad's framing verbatim in §Related Work; pin our contribution as prompt-optimization *with* the train/test seal TextGrad omits. **Cost:** low. **Class:** re-implement-and-cite.

#### OPRO borrows
- **Figure 11 visual design: train+val with ±1σ shaded bands from 3 optimization repeats**; validation every 3 steps (not every step). Our adaptation of this is item #3 above.
- **Explicit "Overfitting Analysis in Prompt Optimization" subsection with figure** (§5.4 title + placement). Mirror: §"Overfitting in human-in-the-loop prompt iteration" containing our train-vs-sealed-test gap with the multi-tag curve as headline. Lead with honest gap rather than apologize. **Cost:** low. **Class:** cite-as-prior-art.
- **Ascending-order best-N** in the revision context (§5.2, §5.2 ablation). Show Human prior `paper-trail-v<N>` prompts + macro-F1 worst→best so strongest prior anchors the new proposal. Trivial convention; worth citing. **Cost:** low. **Class:** adapt-freely.
- **K-random-exemplar rotation biased toward current-version misclassifications** (§4.2, Fig 3). Before each manual revision, surface 3 rotating Sarol examples — biased toward confusion-matrix off-diagonal. Keeps Human grounded in concrete failure cases. **Cost:** medium (small script). **Class:** adapt-freely.
- **Contribution framing by capacity, not by SOTA.** "LLMs have the capacity of gradually improving based on past optimization trajectory." Our version: "human-agent iteration produces measurable, archivable per-revision gains on a labeled citation-integrity benchmark" — sidesteps the comparison-baseline gap we don't have clean coverage for. **Cost:** low. **Class:** cite-as-prior-art.
- **Explicit future-work pin on val-gated stopping** (§5.4). Per our `feedback_defer_with_milestone_pin` norm. **Cost:** low. **Class:** cite-as-prior-art.

#### PromptBreeder / EvoPrompt / ProTeGi borrows
- **PromptBreeder mutation-operator catalog — cite-as-prior-art, do not seed** (§3.2, Table 2, App C: 36+ operators). Reconsidered 2026-04-22 per D38 and declined as a seeded pattern. Reasoning: ProTeGi's template (#10) is a *structural pattern* (delimiter scheme for parseable output) that constrains format without biasing content; PromptBreeder's catalog is a *vocabulary catalog* (named edit moves) that biases the optimizer's attention toward a 2023-era prompt-text-edit vocabulary and contradicts D32 topology-freedom by habit. Also, PromptBreeder's own ablations don't isolate the catalog's value — they isolate the broader "LLMs can do mutation" finding, which EvoPrompt §5.3 Table 6 ("random prompts nearly match top-performing initialization") weakly undercuts. We cite PromptBreeder for (a) LLM-driven mutation being viable and (b) fixed-topology contrast (#2), but leave the optimizer's edit-move imagination unconstrained. **Class:** cite-as-prior-art, do not seed.
- **Lineage-based archive schema** (PromptBreeder §3.2.2). Store tagged prompt variants with full ancestry chain (parent tag, diff, macro-F1 delta). Enables "gradient-of-revisions" figure + retrospective "which revision-move helped most" analysis. **Cost:** low. **Class:** cite-as-prior-art.
- **Fixed-topology framing** (PromptBreeder §6). Now a **contrast** citation for our #2 topology-freedom positioning, not a direct adoption: PromptBreeder fixed topology because its substrate required it; we allow topology-freedom because ours doesn't.
- **ProTeGi learning-curve overfitting observation** (§3.4, Fig 4): "all datasets peaked at around 3 steps." Strong supporting citation for our hygiene-rules section — ProTeGi *empirically saw* overfitting in 3 steps on simple NLP classification; our loop runs many more cycles, so overfit risk is higher. Cite as empirical precedent for test-split sealing. **Cost:** low. **Class:** cite-as-prior-art. **High-value citation.**
- **ProTeGi minibatch-of-4-errors → gradient → m=4 edits → bandit-select protocol** (§3.2). Concrete numeric parameters for our revision cycle: sample ~4 failure-minibatch cases, generate ~4 candidate prompt edits, keep best 1-2 after dev-slice check. Mirrors our manual cadence with reportable parameters. **Cost:** low. **Class:** cite-as-prior-art.
- **ProTeGi UCB-over-Successive-Rejects finding** (§2.2.2, Table 2). Declined as a seeded pattern 2026-04-22 per D38's decision rule — we are not running parallel candidate variants; the optimizer can invent bandit-like selection if it decides to parallelize. Keeps as a future-work citation only. **Cost:** low (future). **Class:** cite-as-prior-art.
- **EvoPrompt "mutate-on-differences" operator** (§3.3, Table 5: +5.68 on Subj). When comparing prompt-vN against prompt-v(N-1), perturb only changed stanzas. Cleaner ablation story and more conservative regressions. **Cost:** low (workflow convention). **Class:** adapt-freely.
- **EvoPrompt initialization-quality finding** (§5.3, Table 6): "Random prompts nearly match top-performing initialization." Useful negative-result citation — supports framing our contribution as the hygiene + archive + harness, not the specific seed prompts. Disarms "you just got lucky with p_0" reviewer critique. **Cost:** low. **Class:** cite-as-prior-art.

#### Reflexion / Self-Refine borrows
- **Triptych architecture diagram** (Reflexion Fig 2a). Our Fig 1 = Extractor / Adjudicator / Verifier around shared "Staging info" artifact, with external arrow = Sarol gold signal crossing the train/test seal boundary (our addition: the seal). **Cost:** low. **Class:** cite-as-prior-art.
- **Algorithm pseudocode box** (Reflexion Alg 1; Self-Refine Alg 1). Write `paper-trail-optimization-loop` pseudocode with train/test seal as a guard clause — makes offline-vs-inference-time distinction visually obvious alongside theirs. **Cost:** low. **Class:** adapt-freely.
- **Related-work comparison table with feature checkmarks** (Reflexion p.3; Self-Refine Tables 3, 5). Rows: Reflexion, Self-Refine, APO/ProTeGi, DSPy/MIPROv2, OPRO, MAPRO, MASS, ours. Columns: offline prompt iteration | human-in-the-loop | train/test split enforced | multi-agent pipeline | labeled external reward signal. "Train/test split enforced" is our unique column — this is where our novelty lands. **Cost:** low. **Class:** adapt-freely.
- **Reflexion episodic-memory buffer as accumulated failure-mode notes across revision sessions.** Bounded sliding window (Ω=1-3) of past failure-mode observations fed into each new revision. Already informal in our journal entries; formalize as bounded window. **Cost:** low. **Class:** adapt-freely.
- **WebShop-style negative-result plot** (Reflexion Fig 6, §B.1). Dedicate a subsection "Where manual optimization plateaus" — a Sarol slice where v_N and v_{N-1} are tied, or where macro-F1 regressed. Pairs with our escalation-ladder doc. **Cost:** low. **Class:** adapt-freely.
- **Self-Refine human A/B blind preference table** (App C, Table 6). Where Sarol gold is ambiguous, run a small blinded A/B with domain readers on paper-trail-v1 vs v_final outputs. Complements macro-F1 with a preference signal Sarol labels can't capture. **Cost:** medium (recruit blinded readers). **Class:** adapt-freely.

#### MAPRO borrows
- **Patience-window stopping** (§3.4: `max ΔS_{t−i+1} ≤ ε` with T=3). Use for any automated comparator baseline so "both loops used identical stopping discipline." **Cost:** low. **Class:** cite-as-prior-art.
- **MAS-as-DAG formalism** (§2.1). Use the DAG vocabulary (nodes=agents, edges=hand-offs) for our pipeline description. Zero cost in prose. **Cost:** low. **Class:** adapt-freely.
- **Reversed-topology blames for failure attribution** (§3.3). During Human prompt-revision sessions, run a reversed-topology critique pass on failed Sarol examples (verifier blames adjudicator blames extractor). Better signal for which subagent's prompt to edit. **Cost:** medium (small tooling). **Class:** re-implement-and-cite. **Notable — directly addresses our manual revision workflow.**
- **MAPRO App B.1 split protocol** as exemplar of "current practice we argue is insufficient." Clean motivation citation for Claim C. **Cost:** zero. **Class:** cite-as-prior-art.

#### MA-SAPO borrows
- **Reasoning-assets corpus** (§3.2: `(trace, reasoning-card, diagnosis, edit-directive)` tuples as persistent retrieval corpus). Our `docs/journal/` is already close to this; publishing as queryable artifact turns it into first-class reproducibility material. **Cost:** low. **Class:** adapt-freely.
- **Efficiency-vs-performance second figure** (Fig 3: input-token cost + wall-clock latency vs aggregate score). Across paper-trail-v1…vN, plot macro-F1 vs cost-per-run. Aligns with our cost-reduction-paths subsection. **Cost:** medium (requires token/latency logging in eval arm). **Class:** adapt-freely.
- **Cascading-error limitation framing** (§5.2 end). Our INDIRECT-detection failure fits exactly this taxonomy; frame as empirical instance of MA-SAPO's hypothesized failure mode and cite bidirectionally. **Cost:** low. **Class:** cite-as-prior-art.
- **No-leakage-discipline gap citation** (§4.1). "Contemporary MAS-prompt-optimization work (e.g., MA-SAPO) evaluates on validation splits without structural defenses against test contamination." Clean intro hook for Claim C. **Cost:** low. **Class:** cite-as-prior-art.

#### MASS borrows
- **Design-principles-as-conclusions format** (Fig 7 caption: three crisp principles). End our paper with 2-3 human-collaboration principles distilled from the retrospective. **Cost:** low. **Class:** adapt-freely.
- **Per-stage incremental-gain table** (Table 6: Base → +APO → +block → +topology → +global). Our equivalent: macro-F1 per paper-trail-v<N> with per-revision delta column. Directly what our archive enables. **Cost:** low. **Class:** adapt-freely.
- **Backbone-portability ablation** (Table 4: "AFlow does not generalize beyond Claude 3.5 Sonnet"). For paper-trail-v<final>, run Opus 4.7 ↔ Sonnet 4.6 ↔ Haiku 4.5 ablation. Turns a limitations paragraph into a defensible figure. **Cost:** high (extra eval compute). **Class:** re-implement-and-cite.
- **Building-block taxonomy language** (Summarize / Reflect / Debate / Aggregate). Describe our pipeline in this mental map: extractor ≈ single predictor, adjudicator ≈ Reflect-style verifier, verifier ≈ Aggregate. Positions us in the reader's established vocabulary. **Cost:** low. **Class:** cite-as-prior-art.

#### BetterTogether borrows
- **Permutation ablation table** (Table 1: Π, Θ, Π→Π, Θ→Θ, Π→Θ, Θ→Π, Π→Θ→Π). Declined 2026-04-22 per D38's decision rule — the borrow was already a loose analogy (BetterTogether permutes prompt/weight interleaving, not subagent-prompt revision order). Post-D32 topology-freedom, the optimizer restructures on its own schedule; pre-registering revision order contradicts the reframe. Also carries compute cost for the ablation itself. **Class:** skip.
- **"Teach itself" framing as rhetorical foil.** Do NOT borrow directly — contrast. Our paper: "human teaches the program" vs theirs: "program teaches itself." Useful for the human-value-in-agentic-collaboration discussion. **Cost:** low. **Class:** cite-as-prior-art (as contrast).
- **Limitations-section template structure** (§6: coverage bounds + one narrow methodological caveat + frank mechanism-level ignorance). Strong one-paragraph template that doesn't over-hedge. **Cost:** low. **Class:** adapt-freely.

### Themes across papers (convergent recommendations)

- **Seed replication is standard.** 5 papers independently adopted 3-5 seed averaging. Non-optional.
- **Verbatim prompt appendix is standard.** 4 papers (MAPRO App D, MA-SAPO App H, Reflexion App C, TextGrad §3.3) publish exact prompts. Already aligned with our archive plan.
- **Explicit "Overfitting Analysis" subsection with figure is emerging convention.** OPRO §5.4, MIPROv2 App H, ProTeGi §3.4 Fig 4. Our version leads with the train-vs-sealed-test gap.
- **None of the 9 papers argue physical sealing or planning-session blindness.** Consistent with Claim C being clean; use MAPRO/MA-SAPO/MASS as motivation citations.

### JSON prompting — quick note (2026-04-21)

Human aside during session: "JSON prompting" seen on Twitter, characterized as "writing prompts structured like code." Quick-search characterization:

**What it is:** A practitioner / blog-world pattern (not a named academic paper or formal optimizer), circulating heavily on Twitter and in developer blogs through late 2025 / early 2026. Two overlapping practices:
1. **Structured output.** Tell the LLM to reply in a specific JSON schema (enums, field types, required keys). Reported adherence rises from ~60% to >95% once the schema is specified explicitly. This is the dominant framing.
2. **Structured input.** Format the prompt itself as JSON with fields like `{task, context, constraints, output_format}` rather than free prose. Claimed benefits: less ambiguity ("ambiguity tax"), cleaner integration, easier versioning and testing.

**Relationship to paper-trail:** We are already doing the structured-output version — our adjudicator returns a fixed verdict schema defined in `experiments/sarol-2024/specs/verdict_schema_sarol.md`, and Sarol's benchmark evaluates against that schema. The structured-input framing (prompts-as-JSON) we are *not* doing; our prompts are authored prose. DSPy's `Signature` pattern (item "Signature/LM-program formalism" in the borrowing catalog above) is the rigorous academic version of the same intuition and supersedes JSON prompting as a citation target.

**Implication for the paper:** Not a novelty threat. No canonical paper to cite (practitioner pattern, blog-form); if we want to nod to it in prose, "structured prompting with JSON schemas (often called 'JSON prompting')" with a citation to a representative blog is fine but low-priority. The DSPy Signature borrow already covers the citable-academic version. **No further lit-review action unless a reviewer flags.**

Sources searched:
- [Is JSON Prompting a Good Strategy?](https://blog.promptlayer.com/is-json-prompting-a-good-strategy/) — practitioner summary of the pattern
- [JSON prompting for LLMs (IBM Developer)](https://developer.ibm.com/articles/json-prompting-llms/) — structured-output framing
- [Mastering JSON Prompting for LLMs (ML Mastery)](https://machinelearningmastery.com/mastering-json-prompting-for-llms/) — implementation tutorial
- [Mastering Prompt Engineering: Using LLMs to Generate JSON-Based Prompts (Republic Labs, Jan 2026)](https://blog.republiclabs.ai/2026/01/mastering-prompt-engineering-using-llms.html) — structured-input framing

---

## Core contributions to argue

Revised 2026-04-21 after (a) 9-paper lit-review pass and (b) agent-only reframe. **Framework-first contribution ordering.** Paper-trail + Sarol is the case study; the framework is the primary contribution. Authoritative plan doc: `agentic-pipeline-optimization-framework.md`.

1. **Framework for agent-only optimization of multi-subagent pipelines under tiered leakage discipline.** Primary contribution. Three-tier access model: Train (fully open to optimizer) / Val (scalar-only to optimizer) / Test (sealed). Structural enforcement via filesystem permissions + fixed-schema dispatcher CLIs + dispatcher-as-deterministic-Python-script. No prior art in the 9-paper lit review argues per-example val inaccessibility for the optimizer agent — Tier 2 is the specifically novel layer. Claim C (physical sealing + planning-session blindness) is preserved as Tier 3 but is now a *system property*, not a human discipline norm.
2. **Agent-only optimizer architecture with structural defenses.** Optimizer agent + deterministic Python dispatcher + uniform-invocation eval subagents (headless Claude Code, `--bare`). Attack-surface analysis (framework doc §4) demonstrates the defenses close the relevant leakage channels. Optimizer self-respawn at context limits is an open problem with a proposed mechanism (framework doc §5).
3. **Paper-trail citation-integrity pipeline on Sarol-2024 as the case study.** Demonstrates the framework works on a real multi-subagent pipeline (extractor / adjudicator / verifier) with a non-trivial labeled biomedical benchmark. The case study carries the following specific findings:
   - First 9-way Sarol baseline (no prior published baseline exists at 9-way granularity).
   - INDIRECT-detection failure mode in naive LLM adjudicators — named, diagnosed, remedied. From the April-20 smoketest: 2 of 5 false-ACCURATEs had the same shape (extractor surfaces on-topic quotes, every quote ends in a trailing citation marker, adjudicator doesn't scrutinize the markers). Pattern is legible and transferable beyond paper-trail.
   - Severity-under-commitment pattern (s4; tentative pending N=50+).
   - Cost-per-claim practitioner numbers (~$0.73/claim at Opus 4.7 uncached).
4. **Train+val curve over agent-driven revisions as headline figure — further narrowed post-reframe.** Treat each agent-driven revision as an optimization step; plot train + val macro-F1 against revision index; divergence is the stopping rule. **Prior art on the figure shape:** OPRO §5.4 / Figure 11 (algorithmic train+val vs optimization-step), MIPROv2 Appendix G (algorithmic best-score-so-far), MAPRO Figure 3 (patience-window stopping). Our novelty: (i) divergence as explicit stopping rule — OPRO defers this to future work — (ii) applied to a multi-subagent pipeline, (iii) under Tier 2 scalar-only-val discipline (which no prior work enforces). Loses the "human-driven" differentiator present before the 2026-04-21 reframe; gains the "tiered-leakage-disciplined" differentiator.

**Dropped / moved:**
- **"Multi-subagent pipeline iteration formalized" as standalone.** Scooped by DSPy + MIPROv2 + BetterTogether + MAPRO + MASS + MA-SAPO. Cite as prior art.
- **Human-in-the-loop framing + "human-value-in-agentic-collaboration retrospective" as a current-paper arm.** Moved to a future separate paper on human-agent research collaboration. Planning-phase material (in §"Human-value retrospective" below) continues to be collected for that future paper. Human 2026-04-21: *"I'll save it for a new paper, but this planning phase, I still think, is interesting: how we're working together, what you're coming up with, what I'm coming up with. We do want to remember to keep documenting that."*

---

## Hygiene principles to formalize in the methods section

Two complementary rules (both operational; argued from first principles in `experiment-sarol-optimization-loop-hygiene.md`):

a) **Structural subagent sandboxing.** Subagents dispatched by the orchestrator cannot physically reach gold labels. Implemented via: gold stored outside the repo tree (`$PAPER_TRAIL_GOLD_DIR`); opaque `ref_XXXXXX` citekeys that do not encode split / claim-id / paper-bucket; filesystem-restriction paragraph appended to every dispatch; `staging_info.json` scrubbed of claim metadata beyond what the subagent needs.

b) **Policy-gated main-session test blindness.** The main planning session — the orchestrator / researcher discussion with an LLM about failure modes — must never see test labels. That session is the optimizer in the loop; test exposure there silently biases every subsequent prompt edit via human-in-the-loop effects. Mathematically identical to training on test. Implemented via physical seal of test at `$HOME/.paper-trail-sealed/sarol-2024-test/` with a `stage_claim.py --split test` tripwire.

**The less-obvious rule is (b).** In gradient-based training, test-leakage discipline is well-internalized. In prompt-engineering workflows it is routinely violated — practitioners "just eyeball test once to sanity-check," and every subsequent iteration is quietly contaminated. Worth arguing in the paper as a methodological standard.

---

## Things to be honest about

- **N=5 smoketest is not a result, it's a plumbing check.** The paper must not report smoketest numbers as evidence of anything. They appear in appendices (if at all) as "we verified the pipeline end-to-end before scaling."
- **Sarol tests 3 of paper-trail's 7 arms.** Variant A exercises phases 5–7 (extractor, adjudicator, verifier). Phases 1–4 (claim extraction, bibliography resolution, PDF fetching, GROBID ingest) are bypassed because the Sarol benchmark pre-provides staged inputs. Headline Sarol numbers must be framed as "phase-5-to-7 performance on Sarol's narrow task," not as whole-paper-trail performance. Variant C covers the other four phases end-to-end and is the paper's headline-product story even if noisier. **The full phase-by-phase map (and exactly what is idealized or impaired in each variant) is already formally written up in `docs/plans/experiment-sarol-faithfulness.md` — use that doc as the source of truth when writing this section of the paper, not this summary note.**
- **We are doing Variant A (corpus-chunks), not Variant C (end-to-end from citing PDF).** Variant C is the end-to-end story the product hinges on. Paper should lead with C even if Variant C's raw numbers are noisier.
- **Pretraining contamination on Sarol test.** Sarol 2024 is public on GitHub; frontier LLMs have plausibly seen the labels during pretraining. Flag this explicitly. Note mitigations: (i) Variant C's end-to-end ingestion stress is unlikely to be memorized as a latent lookup; (ii) the synthetic-injection and opt-in-cohort experiments (from `paper-tool-validation.md`) are contamination-free and serve as the independent defense.
- **We do not do weight-level RL.** Be precise. paper-trail's "optimization" is prompt-level only.
- **The one-shot test eval is a commitment.** If we make mistakes during iteration that force re-unsealing, we must either swap held-out benchmarks or report Sarol test results as exploratory. The paper has to be honest about which.
- **Model pinning is via alias, not version hash.** Claude Code's Agent tool accepts only `opus` / `sonnet` / `haiku` — not explicit model IDs. If Anthropic promotes a new Opus version behind the `opus` alias mid-experiment, that is a silent change. Mitigation: calendar compression (target full train + dev + test within ~2 weeks of 2026-04-21); each archived run records the Claude Code version at the time. Fully-reproducible alternative — direct Anthropic SDK calls with pinned `claude-opus-4-7` hash, or an open-source agentic framework — was considered and rejected in favor of deployment-parity (see `experiment-sarol-archive-and-eval-framework.md` §Model pinning). Disclose this explicitly.
- **Inference seed is not lockable through Claude Code.** Opus 4.7 is non-deterministic; seed parameter is not exposed to the Agent tool. Paper must cite this as a constraint and report multi-seed CIs at locked-candidate + test as the compensating rigor.
- **Backend changes to the same model ID are invisible to us.** Anthropic may update weights, routing, caching, or context-compression behavior without a version bump. No mitigation; disclose.

---

## Other paper-level threads worth developing

- **Qualitative comparison to SemanticCite.** Sarol 2024 didn't compare; we should. Head-to-head on a test subset, including where each tool catches / misses the same claim.
- **Error taxonomy across labels.** Which Sarol classes are easy for an LLM adjudicator, which are hard, and why. INDIRECT is already a candidate for "hard."
- **False-ACCURATE bias as a general LLM-adjudicator finding.** Our smoketest showed 2/2 false ACCURATEs came from over-trusting topically-relevant quotes. If this generalizes past N=5, it's a broader finding about LLM-as-verifier setups, not just paper-trail.
- **Cost / wall-clock tradeoff table.** Opus 4.7 vs Sonnet 4.6 vs Haiku 4.5 on the same train subset. Is there a sweet spot? Ablation axis from the experiment plan.
- **Variant C coverage metric.** For end-to-end runs, report `coverage = (fraction of Sarol-annotated citations for which paper-trail produced any verdict)` alongside F1. Coverage is a legitimate measure of end-to-end robustness that Variant A hides.
- **Orchestrator tool-space vs subagent tool-space asymmetry** (D35 2026-04-22). The optimizer agent's toolset (web search, MCP discovery, lit review, spawning exploratory subagents to test-drive candidate changes, writing prompts and scripts, proposing new pipeline shapes) is materially richer than what paper-trail-v<N>'s deployed subagents need (evidence extraction, 9-class verdict adjudication, spot-check verification). The *experimenter-agent* and the *experiment-agents* operate at different levels of agency. Paper observation for the discussion section, not a primary contribution. **Human quote 2026-04-22:** *"the set of tools that the orchestrator agent may or may not use to build the sub-agents far exceeds the tools the sub-agents of paper-trail itself will end up using. Sub-agents of paper-trail don't need to do literature reviews of best ways to keep sub-agents on track."* See journal `docs/journal/2026-04-22-topology-freedom-and-optimizer-affordances.md` D35.
- **Python-default reflex as a substrate-level anti-pattern.** Claude Code's training distribution tilts toward bespoke-Python-script solutions. Paper-trail's optimizer agent fights this explicitly in its initial system prompt (see framework doc §3 "Optimizer agent initial configuration"). Worth a sentence in methods naming the anti-pattern and a discussion-section thread on "what initial prompts does the optimizer agent need to behave agentically in a coding-biased substrate?" Relevant framing for why our optimizer-agent seeding matters as a reproducibility detail.

---

## Human-value retrospective — raw material for a *future separate paper*

**Moved out of this paper's scope 2026-04-21** per the agent-only reframe (see §"Core contributions" above and `agentic-pipeline-optimization-framework.md` §1). This section now feeds a **future, separate paper** on human-agent research collaboration. Human 2026-04-21: *"We lose the agent-human teaming interaction. I'll save it for a new paper, but this planning phase, I still think, is interesting: how we're working together, what you're coming up with, what I'm coming up with. We do want to remember to keep documenting that."*

**Continue collecting.** Every journal entry through the current paper's planning and writing should continue the inline `**Human:**` / `**Agent:**` attribution convention. The dataset grows even though the current paper doesn't publish it. When/if the future paper happens, this section is the bibliography of its retrospective examples.

Running catalog of collaboration-pattern moments captured in `docs/journal/2026-04-21-*.md` entries. Not every entry here will survive to publication; the point is to have a dataset.

### Observed patterns so far

**Pattern 1 — Agent surfaces operational distinctions that Human's intuition initially collapsed.**
Example (D14): Human leaned "train and val are functionally the same in this framework." Agent countered with the per-claim-discipline argument (on train we inspect per-claim failures; on val we look only at aggregate F1 and never at per-claim cases). Human explicitly credited the insight: "Note that that was your insight."

**Pattern 2 — Human surfaces structural / strategic arguments that Agent's initial lean underweighted.**
Examples:
- D9 (monolithic version tagging): Agent's argument was figure-simplicity. Human's argument was structural flexibility — "the final solution may not have three prompts, may not be adjudicator/extractor/verifier." Stronger; subsumed Agent's.
- D11 (headless Claude Code vs direct SDK): Agent argued external reproducibility. Human argued deployment parity and the ambient-Claude-Code future. Stronger; Agent conceded.
- D4 (random vs stratified sampling for eval-train-50): Agent leaned stratified with oversampling of tail classes. Human pushed random on defensibility grounds (oversampling is fairness optimization, not overall-performance optimization). Stronger.

**Pattern 3 — Defer risks sliding into oblivion unless pinned by milestone.**
Example (D20): Agent recommended deferring standalone feature docs. Human's response "just make sure you document [the caveat]" pinned what MUST NOT be deferred (expected_invariants schema, /sarol-eval contract) as non-deferrable Task 5 deliverables. Without the pin, "defer" collapses to "never happens."

**Pattern 4 — Agent enumerates specific instances of a Human-articulated principle.**
Example (D19): Human articulated the invariants-vs-free-variables dividing line philosophically. Agent populated the Tier 1 / Tier 2 / Tier 3 lists with specific items, including candidates Human hadn't named (tool permissions, MCP servers, schema versions, slot-fill determinism). Human then refined by moving tools + MCP off Tier 1 into the system-design-surface.

### Hypothesis to test as the experiment continues

**Claim to defend or falsify in the paper:** human+agent research collaboration on methodology-heavy problems shows a complementary pattern — the agent has depth on known instances of a concept (naming specific items in a category, checking consistency across a literature) and the human has strategic-context judgment (when a framing is philosophically load-bearing, when a deferral needs a milestone pin, when operational discipline beats elegant theory). Neither party's contribution is subset of the other's; removing either degrades the output measurably.

Each journal entry through the remaining experiment should continue to tag contributions by origin so we can test this hypothesis retrospectively. If the pattern does NOT hold — if either party's contributions dominate, or if we can't cleanly distinguish them — that is also a paper finding, worth reporting honestly.

## Cost-reduction paths to evaluate after initial results

- **Prompt caching for the rubric + dispatch-prompt prefix.** Anthropic's prompt caching could amortize the fixed-prefix tokens across repeated subagent calls. Estimated 30%+ input-token reduction on the adjudicator's rubric-prefix alone.
- **Batch API (50% cost at 24h latency).** For the full-train eval at N=2,141 this saves ~$780.
- **Paperclip (MCP-cached paper content).** User's Stanford collaboration. Reading the cited paper is structurally expensive because every subagent call re-ingests the content; an MCP-backed cache of pre-parsed biomedical papers would slash per-claim cost. Deferred per `project_paperclip_primary.md` memory — Paperclip is a deferred optional accelerator, not primary. Revisit after initial results justify additional compute spend.
- **Smaller model ablation (Sonnet 4.6, Haiku 4.5).** Named sweep axis in the experiment plan. Potentially large cost reduction if quality holds.

## Open paper-level decisions (logged, not decided)

- Venue: which CS conference? Needs a decision before deadline constraints shape the writeup. Possible: ACL / EMNLP / NAACL (NLP); NeurIPS / ICML (ML with agentic angle); CHI / IUI (HCI, if practitioner framing dominates); a medical-informatics venue (Bioinformatics, JAMIA) given biomedical use case.
- Companion blog post scope: a tighter narrative focused on the INDIRECT-detection finding + hygiene principle, or a full repro of the paper? Likely the former for reach.
- What to do about the `/paper-trail` branding sidebar (see that memory note) — does the paper use the slash in prose? Probably not (math readers already bristle at unconventional notation); the blog can.
- **One paper or two?** Raised by Human 2026-04-22 — consider splitting into (A) a framework paper (working title direction: "Scientific Principles for Agentic Ecosystems with Verifiable Rewards" or similar; tiered leakage discipline + optimizer/dispatcher/subagent architecture + topology-freedom under verifiable reward + Claude Code substrate argument; paper-trail + Sarol as empirical instantiation) and (B) a shorter tool paper on paper-trail as a citation-integrity agentic tool (INDIRECT-detection finding, 9-way Sarol baseline, cost-per-claim numbers, Variant C end-to-end story; cites Paper A for methodology). **Motivating argument (Human):** a single paper would have two orthogonal punch lines that don't reinforce each other; the framework reader and the tool reader are different audiences. **Tradeoff:** doubles write-cost; risk of one landing and the other not; citation coupling between the papers. **Pin:** workshop later, not now. Titles are placeholders — will workshop.
