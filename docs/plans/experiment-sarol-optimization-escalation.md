# If manual iteration stalls: optimization escalation plan

Companion to `experiment-april-20-findings.md`. Captures the choice (as of 2026-04-21) to pursue manual, human-in-the-loop prompt iteration against Sarol train labels as the primary method, plus the escalation ladder we'll climb only if manual stalls.

## Current path (chosen)

**Level 0 — manual prompt iteration against Sarol train labels.**

Diagnose failures by reading per-claim smoketest output, propose prompt / schema edits (adjudicator first, extractor when needed, verifier rarely), rerun on train, re-score with `parse_verdict.py`. Test stays sealed.

### Why manual first

1. **Diagnosability is a paper contribution.** Manually named failure modes (the INDIRECT-detection blind spot from the April-20 smoketest; the severity-under-commitment pattern) make clearer, more defensible paper arguments than compiled optimizer logs.
2. **The current failures are prompt-level.** The INDIRECT, OVERSIMPLIFY-on-qualifier-drop, and CONTRADICT-commitment issues are each addressable by a targeted prompt clause. No architecture change required.
3. **No new dependencies.** No framework integration, no custom optimizer code, no extra model API. Lowest-friction path.
4. **Opus 4.7 is already the model ceiling.** Any automated-optimizer path that preserves base-model quality (DSPy, TextGrad, OPRO) still runs Claude via the API — the underlying model doesn't get better. Upside from automation is prompt-search breadth, not model capability.

## Stall triggers

Escalate from Level 0 to Level 1 when **any** of the following is observed:

- Three or more manual prompt-edit cycles without measurable lift on the failure modes we're targeting.
- Per-class F1 trades become intractable: fixing class X systematically breaks class Y, and the prompt space has too many axes to cover by hand.
- The methodological-sweep phase (experiment plan Protocol §3: multi-cit prompting, sub-claim decomposition, few-shot, verifier inclusion, rubric phrasing) requires searching a prompt space too large for manual exploration at the required statistical resolution.

## Level 1 — automated prompt search, frozen base model

Automated optimization of prompts with Claude held fixed via API. No weight access required.

### Tools

- **DSPy / MIPROv2** (Khattab et al., Stanford). Most production-ready. Compiles a DSPy program against a labeled dev set via Bayesian-ish search over instruction variants plus bootstrapped few-shot example selection. First-class Anthropic LM adapter.
- **TextGrad** (Yuksekgonul et al., Stanford, 2024). A meta-LLM produces natural-language "gradients" (edit suggestions) from the loss signal, which are applied to the prompt text. Elegant formulation; less mature tooling.
- **OPRO** (Yang et al., DeepMind, 2023). Simpler loop: an LLM proposes prompt rewrites, each scored on the metric, best carried forward. Good for small prompt spaces.

### Known friction (unresolved)

**DSPy-and-friends are typically framed around a single prompt / single program.** paper-trail is a multi-prompt modular agentic pipeline (extractor + adjudicator + verifier, each a separate subagent dispatch). Options at Level 1:

- **Decoupled compile.** Optimize each subagent prompt independently, accepting that cross-stage interactions aren't captured. Cheapest; probably leaves value on the table.
- **Orchestrator-level DSPy module.** Wrap the full pipeline in a DSPy `Module` with all three subagents as sub-modules; let MIPROv2 optimize across the whole thing. Non-trivial integration but technically supported.
- **Custom harness.** Write a thin sweep harness that takes a prompt variant set (adjudicator × extractor × verifier combinations), runs N train claims, scores, ranks. Simpler than DSPy; fewer correctness guarantees.

Open question for the paper-items doc: has the multi-prompt / agentic-system version of automated prompt optimization been named and studied in published work? If not, the DSPy extension may itself be a contribution.

### Level-1 cost expectation

For a 200-claim train subset × (say) 5 candidate adjudicator prompts × 3 candidate extractor prompts = 3,000 pipeline runs at ~$0.73/claim ≈ $2,200. Expensive enough that Level 1 should only trigger when Level 0 has demonstrably stalled.

## Level 2 — custom search / meta-prompting loops

If DSPy / TextGrad can't express the orchestration we need, roll a bespoke meta-prompting loop: a supervisor LLM reads a full pipeline trace (extractor output + adjudicator output + verifier output + gold label) and proposes edits to any of the three subagent prompts. Essentially TextGrad extended to multi-stage. Specific to paper-trail; unlikely to transfer.

Would only reach here if Level 1 is exhausted and we still have prompt-level room to move.

## Level 3 — open-weight model + GRPO

Swap Claude for Llama 3.x / Qwen 2.5-3.x / DeepSeek R1-Distill and RL-train the base model against Sarol gold via TRL, Open Instruct, or veRL (GRPO / PPO).

Tradeoff: lose Opus 4.7-level reasoning. For paper-trail, where adjudicator judgment is a major quality lever, this is almost certainly a net loss. Listed for completeness only — wouldn't expect to reach this tier unless a research-grade reason to study RLVR on paper-trail emerges (e.g., a sponsor / co-author interested in the weight-training path).

## What we never do during iteration

- Touch test. Sealed at `$HOME/.paper-trail-sealed/sarol-2024-test/`; stays sealed until the locked-config single-shot final eval.
- Iterate against dev. Dev is an optional validation-of-winner checkpoint, not a per-cycle signal.
- Commit prompt edits that pass s1-s5 but haven't been re-validated on a broader stratified train subset. Smoketest reruns are sanity checks, not evidence of generalization.
- Unseal test to "debug one failed claim" mid-iteration. Doing so voids the reporting value of test numbers.

## What triggers the single test run

All of the following must hold before unsealing:

1. Extractor + adjudicator + verifier prompts are frozen and committed on a dedicated branch.
2. Full train evaluation (N = 2,141) produces a macro-F1 number.
3. Dev evaluation (N = 316) produces an independent sanity-check number consistent with train.
4. Pre-registered hypothesis: expected test macro-F1 and per-class F1, with rationale.
5. Test unsealed. One-shot test eval. Numbers reported as primary results.
6. Test re-sealed if further iteration is planned; otherwise the experiment is closed.

Any deviation from this sequence voids the test-number reporting. If test is inadvertently exposed mid-iteration, options are: (a) swap to a fresh held-out benchmark for the paper's primary number, or (b) report Sarol test results explicitly as exploratory rather than primary.
