# 2026-04-21 — Lit-review pass on prompt-optimization prior art

Second journal entry for 2026-04-21. Follows the archive-framework decisions entry (morning) and executes the lit-review that NEXT.md flagged as Task 1 — the gating question for whether the "train+val curve over human-driven prompt revisions" figure is a novel published figure type. Decision agreed with Human 2026-04-21 that the lit review must precede expensive experiments ("once we start the experiment, we can't stop it").

**Referenced doc:** `docs/plans/paper-writeup-items.md` §"Specific papers checked so far" and §"Net lit-review verdict (2026-04-21)" now hold the authoritative per-paper pass/fail. This entry is the decision log.

## Method

Five papers / paper-lines, one subagent per line, full-text reads via arxiv HTML / PDF. Each subagent got the same three-claim template to produce a pass/fail judgment on:

- **Claim A** — train+val curve over human-driven prompt revisions as a published figure type.
- **Claim B** — multi-subagent pipeline iteration formalized as an optimization paradigm.
- **Claim C** — train/test hygiene for prompt workflows (physical sealing + policy-gated planning-session blindness).

Per repo memory `feedback_rigor_over_compute.md`, the subagents were instructed to prefer thorough reads over faster paths; per memory `feedback_use_real_orchestrator.md`, dispatched via standard Agent tool rather than ad-hoc scripts.

## Per-claim verdicts and rationale

### Claim A — narrowed, not dropped

**Agent initial lean (pre-review):** plausibly novel as a *published figure type*. Hyperagents 2026 and Du et al. 2025 didn't have it; DSPy / TextGrad / OPRO / PromptBreeder / Reflexion still to check.

**Lit-review finding:** OPRO §5.4 + Figure 11 explicitly plots train AND val accuracy against optimization steps as a post-hoc overfitting analysis. MIPROv2 Appendix G Figures 8–13 plots best-score-so-far vs evaluation calls. The figure *shape* is prior art.

**Revised Agent position:** Claim A narrows. What remains novel and defensible:
1. x-axis is *human-driven revisions*, not algorithmic proposals.
2. Divergence point is used as the *explicit stopping rule*. OPRO §5.4: "For simplicity, we do not set aside a validation set in our default setting… [early stopping] suggested as future work." That is the gap we fill.
3. Applied to a *multi-subagent pipeline* (extractor/adjudicator/verifier), not a single instruction string.

**Decision:** retain as headline figure with narrowed framing. Cite OPRO Figure 11 as the closest precedent; cite MIPROv2 Appendix G as the algorithmic-multi-stage precedent.

### Claim B — dropped as standalone

**Agent initial lean (pre-review):** formalization of multi-subagent pipeline iteration is the weaker candidate; Du et al. 2025 survey §7.5 flagged multi-agent optimization as open, so possibly novel.

**Lit-review finding:** DSPy (Khattab et al. 2023) formalizes multi-stage LM programs with specialized modules (`GenerateSearchQuery`, `GenerateAnswer`, `Retrieve`, etc.) and teleprompters that "optimize all modules in the pipeline to maximize a metric" (§3). MIPROv2 (Opsahl-Ong et al. 2024) Algorithm 1 jointly optimizes `[ι₁…ιₘ]` and demonstrations across modules. Our extractor / adjudicator / verifier trio is exactly the DSPy shape.

**Revised Agent position:** Claim B is scooped. The Du et al. 2025 survey's §7.5 was about *parameter-driven* multi-agent optimization (fine-tuning pipelines), not parameter-free prompt iteration — I had misread which part was open. Parameter-free multi-stage pipeline optimization is DSPy's domain and has been since 2023.

**Decision:** drop B as a standalone claim. Cite DSPy/MIPROv2 as prior art. Reposition our pipeline as the *human-driven + citation-integrity + hygiene-disciplined* variant of the DSPy paradigm — not as a new paradigm.

### Claim C — clean, promoted to lead

**Agent initial lean (pre-review):** equally ranked with A and B; framed as one of three. Possibly novel but not singled out.

**Lit-review finding:** None of the five papers argues physical sealing of the test split during iteration, none argues policy-gated blindness of the researcher / planning session, and none frames the prompt-design discussion itself as the optimizer whose test exposure silently biases subsequent edits. DSPy §6 has a single hygiene sentence ("use dev to avoid overfitting on test") — genuine prior art for "use dev, not test," not for the stronger claim. MIPROv2 Appendix H acknowledges a proposer-overfits-to-few-shots failure mode and explicitly "leave[s] better understanding this phenomenon as an exploration for future work."

**Revised Agent position:** Claim C is the strongest of the three. The "planning session IS the optimizer" framing — which makes Rule 2 (main-session blindness) more than hygiene theater — is genuinely unclaimed.

**Decision:** promote C to the #1 contribution. This was not obvious before the lit review; the pass made it clear.

## Attribution and human-value retrospective notes

This pass was predominantly Agent-executed — 5 parallel subagents, Agent-synthesized verdicts, Agent-proposed contribution reshuffling. Relevant patterns from the ongoing catalog in `paper-writeup-items.md` §"Human-value retrospective":

**Pattern 1 adjacent (Agent self-correction under evidence).** Agent's pre-review ranking had C below A and B; lit review evidence flipped it. Without the evidence pass, the paper would have led with a scooped claim and underplayed the clean one. This is a different shape from Pattern 1 — not "Human corrects Agent," but "evidence corrects Agent" — worth noting as a sub-pattern. Useful for the paper's reflective section: the value of a rigor-over-speed norm (memory `feedback_rigor_over_compute.md`) is concretely illustrated here; a faster pass would have missed OPRO Figure 11 and left Claim A mis-framed.

**Pattern 3 applied (defer with milestone pin).** 2025 multi-agent prompt-optimization papers (MAPRO, MA-SAPO, Multi-Agent Design) flagged by the Reflexion subagent as additional prior art for Claim B. Per memory `feedback_defer_with_milestone_pin.md`: deferred to "before final paper draft," not generically deferred. Documented in `paper-writeup-items.md` §"Open follow-up lit-review items." The B-claim is already dropped so these don't change the verdict, only the citation list.

## What this unblocks

NEXT.md Task 1 is complete. Expensive experiments (Task 2: memory-blind spike; Task 3–6: eval arm build and first curve points) are no longer gated on novelty uncertainty. The headline figure survives with narrower framing; the hygiene contribution is now the lead; the pipeline-iteration claim is reframed as domain application of DSPy/MIPROv2.

**Task 2 (memory-blind invocation spike)** — partial progress this session.

Research leg (Option 2 in the NEXT.md list: "check Claude Code's CLI for `--no-memory` / `--clean` / `--profile <name>`") delegated to `/claude-code-guide` subagent. Subagent returned specific candidate flags and env vars. Per memory `feedback_rigor_over_compute.md` and the general memory-verification norm, I ground-truthed against `claude --help` before committing to plan docs.

**Verified:** `--bare` flag exists, and its `--help` description explicitly names "auto-memory" and "CLAUDE.md auto-discovery" in the skip list. Reinforcing flags (`--no-session-persistence`, `--strict-mcp-config`, `--setting-sources`, `--add-dir`, `--append-system-prompt-file`, `--settings`, `--agents`, `--mcp-config`) are all real and compose with `--bare` to opt back in to only the context the `paper-trail-v<N>` tag specifies.

**Not verified:** subagent-claimed env vars `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `CLAUDE_CODE_DISABLE_CLAUDE_MDS` and a settings key `autoMemoryEnabled`. None appear in `claude --help`. Not adopted.

**Still owed:** the canary sanity-check — plant a distinctive memory file, invoke with and without `--bare`, confirm the flag prevents citation. Test design written into archive-framework doc §Q9c. Estimated 15 min; not run this session to keep the commitment-step boundary clean.

**Q9c status:** "candidate identified, not yet verified empirically." Documented in `experiment-sarol-archive-and-eval-framework.md` §Q9c with the full invocation pattern, the verified flag set, explicit rejection of the unverified env vars, and the canary-test design. NEXT.md Task 2 updated to "PARTIAL" with the sanity-check as the completion bar.

**Attribution note for the human-value retrospective:** this is a Pattern-1-adjacent moment where *Agent's own rigor norm corrected an Agent-subordinate's output*. The `/claude-code-guide` subagent returned plausible-sounding but unverified specifics; the outer Agent applied the "verify before recommending" norm and caught the hallucination. Human did not participate in this correction at all. Worth preserving as an instance of how the hygiene norms in CLAUDE.md and memory files operate even in pure-Agent workflows — relevant context for the paper's discussion of agent-research-collaboration quality.

## What Human should decide next

1. **Confirm the contribution reshuffle.** Is "hygiene principle" leading the paper the right call, or is the headline figure still the draw? This is a paper-framing decision, not a technical one.
2. **Task 2 canary test.** `--bare` is the candidate mechanism. Approve running the canary-test (plant a temporary memory file, invoke with and without `--bare`, confirm) to close out Q9c. ~15 min. Safe — temporary file under user's own memory dir, deleted after test. Or defer if Human wants to run it personally to inspect.
3. **2025 multi-agent paper follow-up.** Target for read: before final paper draft. Is that the right pin, or sooner?
4. **Proceed to Task 3+?** The session prompt was clear: "Do NOT proceed past Task 2 without Human sign-off — Task 3+ are commitment steps." Not proceeding. Awaiting Human sign-off on the above before touching Task 3 (`paper-trail-v1` commit pick), Task 4 (subset manifests), Task 5 (eval arm build).
