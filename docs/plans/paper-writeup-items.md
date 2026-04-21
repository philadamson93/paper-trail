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

**Lit-review question, partially resolved (2026-04-21):** has the multi-prompt / agentic-system version of automated prompt optimization been named and formalized in published work? The single-prompt case is well-developed (DSPy / MIPROv2, TextGrad, OPRO, PromptBreeder, ProTeGi). The inference-time self-improvement case is well-developed too (ReAct, Reflexion, Self-Refine). What seems less-developed: **offline, metric-driven iteration across a multi-subagent pipeline with held-out test hygiene.**

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

### Still to scan

AutoGen, CAMEL, multi-agent-debate papers, Shinn et al. (Reflexion / follow-ups), DSPy's MIPROv2 and BetterTogether papers, TextGrad paper (Yuksekgonul), OPRO (Yang et al.), recent Stanford/Berkeley agent-system compilation work (PromptAgent, ProTeGi, EvoPrompt). If none formalizes the **multi-prompt + verifiable-reward + physical train/test sealing** combination, that's the gap worth naming.

---

## Core contributions to argue

Ranked by how concrete and defensible each is:

1. **First 9-way Sarol baseline.** No prior published baseline exists at 9-way granularity on this benchmark (Sarol et al. reported 3-way F1 only). Even a modest first number is novel.
2. **INDIRECT-detection failure mode in naive LLM adjudicators — named, diagnosed, remedied.** From the April-20 smoketest: 2 of 5 false-ACCURATEs had the same shape — extractor surfaces on-topic quotes, every quote ends in a trailing citation marker (`(N)` / `(Author et al., YEAR)`), adjudicator doesn't scrutinize the markers. Lexically detectable signal, prompt-level fix. The pattern is legible and transferable beyond paper-trail.
3. **Hygiene principle for agentic-pipeline development.** Argue explicitly: iterating prompts against a labeled benchmark is a closed-loop optimization and requires train/test separation identical to gradient-based training. "Don't look at test" is insufficient; physical sealing is necessary. Extend to: even the main planning / researcher session must be test-blind, because that session is where prompt edits are proposed.
4. **Train-and-validation curve over manual prompt revisions — the "loss curve" figure.** Treat each researcher-driven prompt revision as an optimization step (analog of an epoch), plot train macro-F1 and val macro-F1 against revision index. Expected shape: train rises monotonically; val tracks train early, then diverges when over-iteration on train starts costing val. The divergence point is the honest stopping signal. Possibly novel as a *published figure type* for human-in-the-loop multi-subagent pipeline iteration — we have not found it in Du et al. 2025, Hyperagents 2026, or the DSPy / Reflexion lineage (the closest analogs are algorithmic-compilation curves, not human-in-the-loop curves). Mechanism to support it lives in `experiment-sarol-archive-and-eval-framework.md`.
5. **Severity-under-commitment pattern** (s4 in the smoketest): adjudicator picked NOT_SUBSTANTIATE despite the extractor having surfaced verbatim contradictory evidence (the source explicitly dissociated SVZ neurogenesis from corticosterone). Whether this is systematic or per-claim noise needs N=50+ to know. May survive as a contribution; may not.
6. **Cost-per-claim practitioner numbers.** $0.73 mean per claim at Opus 4.7 with no caching and no batch. Projections for full train and test with + without optimizations. Useful for a practitioner-relevant paper, especially a blog-post companion.

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

---

## Open paper-level decisions (logged, not decided)

- Venue: which CS conference? Needs a decision before deadline constraints shape the writeup. Possible: ACL / EMNLP / NAACL (NLP); NeurIPS / ICML (ML with agentic angle); CHI / IUI (HCI, if practitioner framing dominates); a medical-informatics venue (Bioinformatics, JAMIA) given biomedical use case.
- Companion blog post scope: a tighter narrative focused on the INDIRECT-detection finding + hygiene principle, or a full repro of the paper? Likely the former for reach.
- What to do about the `/paper-trail` branding sidebar (see that memory note) — does the paper use the slash in prose? Probably not (math readers already bristle at unconventional notation); the blog can.
