# Research: systematic use of Sarol's gold-standard labels for paper-trail

Background reading for the methodological-sweep phase of the Sarol benchmark experiment. Surveys techniques for using labeled train data to improve paper-trail's verdict pipeline without fine-tuning model weights.

Companion: `docs/plans/experiment-sarol-benchmark.md` §"Train as methodological development data."

## Scope constraints

- **No model weight updates.** paper-trail's design is agentic with off-the-shelf LLMs; fine-tuning / LoRA / RLHF / distillation all break the tool's shape and give up generalization across domains. See §"What we are explicitly not doing" below.
- **No bespoke retrieval infra.** Want to keep the tool portable; heavy retriever training or dense-index maintenance is a separate project.
- **Inference-time only.** Anything we adopt should work by modifying prompts, dispatch sequences, or sampling strategy — not by changing weights.

## Method menu (ranked by effort ↗)

### 1. Few-shot in-context learning with stratified demonstrations (low effort, high value)

Simplest win. For each test claim, include K labeled examples from train in the adjudicator prompt.

Design choices from the literature:

- **Selection:** "Revisiting Demonstration Selection Strategies in In-Context Learning" (ACL 2024) finds retrieval-based methods (TopK semantic similarity, BM25) beat random selection; best retrievers vary by task and inference model. "Learn to Select: Label Distribution Divergence" (2025) shows balancing label distribution in selected demos matters — a pure-similarity retriever can over-represent the majority ACCURATE class.
- **Number of demos:** Atlas / OpenScholar evidence — performance saturates at 10s of examples; no need for hundreds.
- **Labels visible:** Yes, pair each demo with its gold Sarol label. The adjudicator learns the decision boundary implicitly.

Specific proposal for paper-trail:
- Pre-compute embeddings for all 2,141 train claims (simple sentence-transformer). For each test claim, retrieve K=6 nearest neighbors with class stratification (at least 1 per major class if available). Inject into the Sarol-variant adjudicator prompt as `## Examples` before the test claim.
- Compare zero-shot vs K∈{4, 8, 12} on train-held-out.
- Ablate: pure TopK vs TopK + label-stratified.

Risk: paper-trail's adjudicator prompt is already long; adding 8+ demos inflates context cost. Worth pricing.

### 2. Retrieval-augmented per-claim prompting (moderate effort, moderate value)

Same as #1 but formal: a retrieval step that embeds the test claim and surfaces the top-K train exemplars with a defined similarity function.

Literature:
- "Retrieval-style In-context Learning for Few-shot Hierarchical Text Classification" (TACL 2025) — formal framework for retrieval-ICL in classification.
- "Mixture of Demonstrations for In-Context Learning" (NeurIPS 2024) — multiple "buckets" of demos with different properties (hard cases, easy cases, diverse error modes), sampled for each query.

For paper-trail: probably overbuilding for v1. Try #1 first; only go to formal retrieval if demo selection quality is the bottleneck.

### 3. Self-consistency sampling (moderate effort, moderate value)

Sample K adjudicator responses at temperature > 0; take majority vote (or confidence-weighted vote).

Literature:
- **Wang 2022 self-consistency** — the baseline; plurality vote over K samples.
- **CISC (Confidence Improved Self-Consistency, 2025)** — assigns each sample a self-reported confidence, takes weighted vote. Strictly better than raw SC at same K.
- **RASC (Reasoning-Aware Self-Consistency, NAACL 2025)** — uses reasoning-path quality to stop early; ~70% fewer samples at same accuracy.
- **BoN-MAV (Multi-Agent Verification)** — instead of K replicas of the same model, run K different "aspect verifiers"; stronger scaling than raw SC.

For paper-trail specifically:
- **paper-trail's verifier stage is already a restricted form of verification sampling** — one independent agent spot-checking one evidence entry. Expanding this is natural. Specifically: on AMBIGUOUS verdicts from the adjudicator, run K=3–5 adjudicator re-samples (different seeds) and take majority vote.
- **CISC would compose cleanly** with paper-trail's confidence-hint output (the adjudicator already has `claim_type_hint.confidence`).
- **BoN-MAV maps directly** to paper-trail's extractor+adjudicator+verifier separation. We could add one more independent "aspect verifier" (e.g., a MISQUOTE-specific check on numerical claims) and compose via vote.

Recommended order: plain K=3 self-consistency on AMBIGUOUS-only claims → evaluate on train → if promising, try CISC; skip RASC/BoN-MAV unless needed.

Risk: K× cost. Only run on the subset of claims where the adjudicator is uncertain.

### 4. Error-cluster-targeted prompt refinement (moderate human effort, high value)

After full-train eval, cluster errors by confusion-matrix cell (e.g., "we said ACCURATE, Sarol says OVERSIMPLIFY"). For each cluster:

- Read 5–10 misclassified examples.
- Identify the systematic failure mode (e.g., "model doesn't catch scope narrowing", "model confuses INDIRECT and INDIRECT_NOT_REVIEW because it can't tell review papers apart").
- Write a targeted rubric addendum or few-shot example addressing that failure mode.

Literature backdrop: standard prompt engineering with a feedback loop. Not novel methodology; valuable mostly for the specific errors that show up.

For paper-trail: this is the most likely source of "bake back into the main tool" improvements. Errors found on Sarol biomedical data are likely to generalize to any domain.

### 5. Chain-of-thought rationales from gold (moderate effort, marginal value)

Construct CoT-style explanations for a stratified train subset (human-written or synthesized from gold + evidence), use as few-shot demos.

Literature: standard CoT prompting plus few-shot, e.g., Wei 2022 et seq.

For paper-trail: the adjudicator already emits reasoning in `nuance` fields. CoT few-shots would steer the reasoning structure but it's unclear that the extra specificity moves F1. Skip unless Method 1 plateaus and we need another lever.

### 6. Automated rubric-phrasing A/B (low effort, small value)

Word-for-word comparison of Sarol's published annotation guide vs paper-trail-tone phrasing of the same classes. Pick the phrasing that lifts macro-F1 on train.

Risk: small effect size. Worth a single sweep, not an ongoing investment.

## What we are explicitly not doing

### Fine-tuning / LoRA on Sarol train

Would improve F1 on Sarol, but:
- Requires maintaining fine-tuned model weights as part of paper-trail distribution, which breaks the "Claude Code-native, works with whatever LLM you have" positioning.
- Overfits to biomedical vocabulary; cross-domain generalization suffers.
- 2,141 claims is small for supervised tuning of a verdict-classifier head atop a large LLM; gains are typically marginal vs well-crafted few-shot.
- Sarol et al. 2024 already did this with MultiVerS and got 0.52 macro-F1; their own numbers demonstrate the ceiling of supervised approaches on this corpus.

### RLHF / DPO preference optimization

Requires a preference dataset (A-better-than-B pairs); we don't have one. Could synthesize from gold-vs-paper-trail comparisons, but then we're implicitly training to agree with Sarol's exact labels, not true citation integrity.

### Distillation into a smaller classifier

Would give cheaper inference but trades away paper-trail's evidence-first agentic design. Out of scope.

### Heavy retriever training

Training a dense retriever on Sarol train pairs would marginally improve demo selection for Method 1, but the infra cost (index, maintenance, deployment) is high. Off-the-shelf sentence-transformer embeddings are good enough for v1.

## Recommended sweep order

Per the experiment plan's methodological-iteration phase:

1. **Baseline (zero-shot).** Run the full train eval with no demos, no sampling. Establish the baseline.
2. **Few-shot stratified K=6 (Method 1).** Straight TopK + label-stratified. Report Δvs baseline.
3. **Self-consistency K=3 on AMBIGUOUS (Method 3).** Only on uncertainty cases. Report Δ.
4. **Error-cluster-targeted prompt additions (Method 4).** Read train errors, write targeted addenda, re-run.
5. **Optional: K=12 few-shot + CISC (Methods 1+3 combined).** If earlier methods leave headroom.

Lock the best configuration; carry to test.

## Sources

- Wang et al. 2023, *Self-Consistency Improves Chain of Thought Reasoning*.
- Brown et al. 2020, *GPT-3 / Language Models are Few-Shot Learners*.
- **Revisiting Demonstration Selection Strategies in In-Context Learning** — ACL 2024, https://aclanthology.org/2024.acl-long.492.pdf
- **Learn to Select: Label Distribution Divergence for ICL** — 2025, https://arxiv.org/html/2511.10675
- **CISC: Confidence Improves Self-Consistency** — ACL findings 2025, https://aclanthology.org/2025.findings-acl.1030.pdf
- **Mirror-Consistency** — EMNLP findings 2024, https://aclanthology.org/2024.findings-emnlp.135.pdf
- **RASC: Reasoning-Aware Self-Consistency** — NAACL 2025, https://aclanthology.org/2025.naacl-long.184/
- **Retrieval-style ICL for Text Classification** — TACL 2025, https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00697/124630/
- **Mixture of Demonstrations for ICL** — NeurIPS 2024, https://proceedings.neurips.cc/paper_files/paper/2024/file/a0da098e0031f58269efdcba40eedf47-Paper-Conference.pdf
- **Atlas** — Izacard et al. 2023 (retrieval-augmented few-shot saturation).
