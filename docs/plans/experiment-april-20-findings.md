# Experiment April 20 findings: Sarol 2024 N=5 smoketest

**Run date:** 2026-04-20 (Phase A adjudication) / scored and written up 2026-04-21.
**Branch:** `experiment-plan`
**Pipeline:** paper-trail extractor → Sarol-variant adjudicator → verifier, Opus 4.7 throughout, no caching, no Batch API.
**Input variant:** A (Sarol corpus-chunks, not full PDF).

## Hygiene note

These are **train** claims. Per the Sarol experiment plan, train is fair game for methodological iteration; recording `claim_row_id` + `gold_label` in this document is allowed. This file is orchestrator-visible and is **not to be handed to extractor/adjudicator/verifier subagents** — every subagent dispatch must retain the filesystem-restriction paragraph that prevents reads outside the staged inputs.

The **test** split (`claims-test.jsonl`, `annotations/Test/`, and the combined `annotations.zip`) has been moved out of `$PAPER_TRAIL_BENCHMARKS_DIR` to `$HOME/.paper-trail-sealed/sarol-2024-test/` as of this writeup. `stage_claim.py --split test` now fails cleanly with `FileNotFoundError`. Test does not get unsealed until a locked adjudicator/extractor configuration is ready for its single, final evaluation. Dev split remains reachable and is treated as an optional validation-of-winner checkpoint.

## Setup

- 5 stratified train claims chosen to span the major Sarol label classes (one each: ACCURATE, OVERSIMPLIFY, NOT_SUBSTANTIATE, CONTRADICT, INDIRECT). All single-cit.
- Opaque citekeys (`ref_XXXXXX`) throughout; subagents received the opaque ref only.
- Gold revealed only at Phase B scoring via `parse_verdict.py`, which reads from the external gold store.
- Run-id: `run_sarol_smoketest_20260420T215601Z`.

## Structural checks (Phase A)

| Internal ref | citekey | sub_claims | overall_verdict | verifier | cost |
| --- | --- | --- | --- | --- | ---: |
| s1 | ref_02d728 | 1 (ACCURATE) | ACCURATE | PASS | $0.751 |
| s2 | ref_925484 | 2 (ACCURATE × 2) | ACCURATE | PASS | $0.683 |
| s3 | ref_f4c6ce | 3 (OVERSIMPLIFY, ACCURATE, OVERSIMPLIFY) | OVERSIMPLIFY | PASS | $0.757 |
| s4 | ref_7b48d1 | 1 (NOT_SUBSTANTIATE) | NOT_SUBSTANTIATE | PASS | $0.701 |
| s5 | ref_f4319d | 3 (ACCURATE × 3) | ACCURATE | PASS | $0.761 |

- `rubric_variant == "sarol_2024_9class"` on all 5.
- Every sub-claim verdict is within the Sarol 9-class enum. No native labels (`CONFIRMED`, `PARTIALLY_SUPPORTED`, etc.) leaked.
- No verifier bounces (zero `bounce_to_re_ground`).
- Per-claim cost $0.68–$0.76, all under the $1.50 flag threshold.
- **Total smoketest cost: $3.65.** Per-claim mean $0.73, consistent with the $0.66 pilot estimate.

## Accuracy (Phase B, gold revealed)

| Ref | train claim_id | gold_label | pred_label | 9-way | 3-way |
| --- | ---: | --- | --- | :---: | :---: |
| s1 | 417 | ACCURATE | ACCURATE | ✓ | ✓ |
| s2 | 42 | OVERSIMPLIFY | ACCURATE | ✗ | ✗ |
| s3 | 975 | NOT_SUBSTANTIATE | OVERSIMPLIFY | ✗ | ✓ |
| s4 | 1395 | CONTRADICT | NOT_SUBSTANTIATE | ✗ | ✓ |
| s5 | 850 | INDIRECT | ACCURATE | ✗ | ✗ |

**9-way: 1/5. 3-way: 3/5.** Below the smoketest's "≥3 of 5 match gold" 9-way threshold.

## Per-claim error analysis

### s1 (417 → ACCURATE / ACCURATE) — hit

Single-sub-claim ACCURATE call; extractor surfaced 13 direct evidence hits from the cited paper's Abstract, Introduction, and Results sections. Verifier spot-checked L5 of Abstract — verbatim match.

### s2 (42 → OVERSIMPLIFY called ACCURATE) — double signal missed

**Claim:** "The direct target for metformin is not clearly defined, however it is believed to act via inhibition of Complex I of the mitochondrial respiratory chain [CIT]."

Two Sarol-relevant signals were present in the extractor's own evidence and the adjudicator ignored both:

1. **Dropped qualifier (OVERSIMPLIFY shape).** Evidence at L19: "Metformin has been shown to disrupt complex I of the electron transport chain …" — but L36 says "Metformin is known to inhibit mitochondrial complex I **in vitro** …" The citing claim omits the *in vitro* qualifier. That is the textbook OVERSIMPLIFY pattern (narrower-in-source than claimed).
2. **Indirect attribution.** L36's full text: "Metformin is known to inhibit mitochondrial complex I in vitro (Ota et al., 2009; El-Mir et al., 2000; Owen et al., 2000)". The cited paper explicitly credits three primaries. This is INDIRECT shape.

Adjudicator reasoned from the presence of on-topic sentences and called ACCURATE without scrutinizing qualifiers or trailing citation markers.

### s3 (975 → NOT_SUBSTANTIATE called OVERSIMPLIFY) — adjacent class, 3-way hit

**Claim:** "Inflammation plays important roles in the progression of obesity and diabetes, which are correlated with human aging ([CIT])."

Adjudicator issued OVERSIMPLIFY (sub-claims: OVERSIMPLIFY, ACCURATE, OVERSIMPLIFY); gold is NOT_SUBSTANTIATE. Both land in the 3-way NOT_ACCURATE bucket, so this is visible as a 9-way miss but a 3-way hit. At N=5 it's hard to tell whether this is an adjudicator-systematic under-call of NOT_SUBSTANTIATE or within-noise.

### s4 (1395 → CONTRADICT called NOT_SUBSTANTIATE) — extractor found it, adjudicator hedged

**Claim:** "prolactin can enhance SVZ neurogenesis in pregnant mice (Shingo et al., [OTHER_CIT]), while increased levels of glucocorticoids associated with stress have the opposite effect ([CIT])"

The extractor did its job precisely. It pulled:
- L56: "we exploited the spatial specificity of X-irradiation to reduce hippocampal neurogenesis **while sparing neurogenesis in the subventricular zone (SVZ)**"
- L58: "**there was no relationship between the extent of SVZ neurogenesis inhibition and the corticosterone response** in irradiated mice"
- L61: "Increased stress response is **not due to reduced neurogenesis in the subventricular zone**."

L58 is a verbatim contradiction of the citing claim. The Sarol rubric says CONTRADICT requires "a verbatim source excerpt saying the opposite" — L58 qualifies. Adjudicator picked NOT_SUBSTANTIATE instead (one level down on the severity ladder).

3-way hit (both CONTRADICT and NOT_SUBSTANTIATE map to NOT_ACCURATE), 9-way miss. The underlying failure is **insufficient confidence to commit to CONTRADICT even when the extractor has provided the verbatim evidence required by the rubric**.

### s5 (850 → INDIRECT called ACCURATE) — same failure mode as s2, more clearly

**Claim:** "Diabetes in older adults is also linked to reduced functional status, increased risk of institutionalization and higher mortality [CIT]."

Every quote the extractor pulled from the cited paper ends with or contains a trailing numeric citation marker:

- L4: "diabetes in older adults is linked to higher mortality, reduced functional status, and increased risk of institutionalization **(2)**"
- L185: "… more functional impairment than those without diabetes **(64,65)**"
- L343: "… overall diabetes prevalence of 25% … **(121)**"
- L344: "LTC residents with diabetes have more falls **(122)**, … more cognitive decline and dependency than residents without diabetes **(123)**"

The cited paper is a review summarizing primaries. Every relevant passage is itself an attribution to elsewhere. This is the most unambiguous INDIRECT call in the benchmark — yet the adjudicator called it ACCURATE.

## Root cause: INDIRECT-detection blind spot

**The single highest-impact finding from this smoketest.** 2 of 5 claims (s2, s5) fail with the same shape:

1. Extractor surfaces topically-correct supporting sentences.
2. Adjudicator sees on-point quotes and calls ACCURATE.
3. Adjudicator does **not** examine whether the quoted passage is itself an attribution to another primary — i.e., ends with `(N)`, `(Author et al., YEAR)`, or a similar marker.
4. Gold is INDIRECT / INDIRECT_NOT_REVIEW / OVERSIMPLIFY-with-indirect-signal.

Why this matters:
- **It is common.** Any citing sentence whose cited paper is a review, or a primary that happens to cite secondaries for this specific fact, triggers it. Sarol reports 1.2% INDIRECT in single-cit claims and 2.8% in multi-cit — but OVERSIMPLIFY and NOT_SUBSTANTIATE frequently have an indirect-attribution component as well, so the real blast radius is larger than the headline INDIRECT rate.
- **It is lexically detectable.** Trailing `(N)` / `(N,M)` / `(Author, YEAR)` in the quoted passage is a cheap signal.
- **The rubric already distinguishes.** INDIRECT vs ACCURATE is explicit in Sarol's 9 classes, and the extractor prompt has an `attestation.indirect_attribution_check` slot that is currently underused.

## Adjacency-miss pattern (s3, s4)

2 of 5 claims land in a neighboring severity class: s3 (gold NOT_SUBSTANTIATE, pred OVERSIMPLIFY) and s4 (gold CONTRADICT, pred NOT_SUBSTANTIATE). Both are 3-way hits. At N=5 this is within noise; at N=50 we'd quantify whether the adjudicator systematically under-commits on severity. The s4 case is especially informative because the extractor provided the verbatim evidence the CONTRADICT verdict requires, and the adjudicator still dropped a level.

## Cost

Per-stage cost shares are stable across the 5 claims:

| Stage | Mean cost | Range | Mean tool uses |
| --- | ---: | ---: | ---: |
| Extractor | $0.356 | $0.318 – $0.390 | 13 |
| Adjudicator | $0.221 | $0.207 – $0.231 | 3 |
| Verifier | $0.154 | $0.143 – $0.172 | 3 |
| **Total/claim** | **$0.730** | **$0.683 – $0.761** | — |

Extractor dominates cost and tool-use count. Adjudicator is cheap because it never touches the source PDF. Verifier is cheap because its scope is a single evidence entry.

Projected costs at this rate (Opus 4.7, no caching, no batch):
- N=50 pilot: ~$37
- Full train (2,141 claims): ~$1,560
- Full test (606 claims): ~$442
  - With Batch API 50% + prompt-cache on rubric/prompts: plausibly ~$180

## Runbook-gate verdict

Against the smoketest's "needs attention before scaling" criteria:

| Gate | Result |
| --- | --- |
| Valid Sarol-9 verdict on all 5 | ✓ pass |
| Verifier PASS (no unresolved bounces) | ✓ pass |
| Per-claim cost < $1.50 | ✓ pass |
| ≤ 2 of 4 non-ACCURATE claims wrong at 9-way | ✗ **fail** (4/4 wrong) |

**→ Stop and debug before scaling to N=50.**

## Pending next steps — NOT YET IMPLEMENTED

These are the candidate adjudicator/prompt changes to evaluate on train before scaling. Each should be tested against a stratified train subset (say N=50), the change with the clearest per-class-F1 lift carried forward, and dev used as a sanity check before any test run.

1. **INDIRECT detection from extractor evidence.** Adjudicator prompt should explicitly instruct: scan each `evidence[*].snippet` for trailing citation markers (`(N)`, `(N,M)`, `(Author et al., YEAR)`). If every supporting quote ends in such a marker, prefer INDIRECT (if the cited paper is a review) or INDIRECT_NOT_REVIEW (otherwise). Fold this into the existing `attestation.indirect_attribution_check` signal.
2. **Dropped-qualifier detection (OVERSIMPLIFY).** Adjudicator should explicitly compare the citing-claim text to the strongest supporting quote; if the source quote includes scope qualifiers (`in vitro`, `in mice`, `ex vivo`, `at high dose`, `in a subset`, `in cell culture`, …) that the citing claim omits, prefer OVERSIMPLIFY over ACCURATE.
3. **CONTRADICT commitment.** Clarify that CONTRADICT is justified when the extractor has recorded a verbatim source excerpt in direct opposition, and does *not* require the adjudicator to re-confirm via its own reading. s4 is the test case.
4. **Extractor-side attestation signals.** Consider extending the extractor's `attestation.indirect_attribution_check` from a free-form note to a structured field that the adjudicator must consume — e.g., `{fact_cited_to_other: bool, other_citations: [...]}`. This removes the adjudicator's ability to silently ignore the signal.

Each change is a prompt/spec edit on the `experiment-plan` branch, tested on train only. Test remains sealed.

## Meta: this is the optimization loop

The pattern — run a labeled benchmark, inspect per-claim failures, iterate prompts or architecture — is the same loop shape as RLVR-style training, with a human/LLM in the optimizer role rather than gradient descent. The labels are the verifiable reward; the prompts are the policy; each iteration tightens the policy against the reward signal.

Two implications:
1. **Train/test hygiene is load-bearing.** Any closed-loop optimization overfits to what it sees. Test must be physically unreachable from the orchestrator during iteration; "we'll just not look" is insufficient. Sealed at `$HOME/.paper-trail-sealed/sarol-2024-test/` as of this writeup.
2. **This is a legitimate methodology to name and defend in the paper.** The paper-trail agent architecture, prompt-engineered against a held-out verifiable-reward signal (Sarol's 9-class gold labels), can set a first 9-way baseline on the Sarol benchmark and a meet-or-beat 3-way baseline against MultiVerS / GPT-4 4-shot. That is the headline claim.

## Paper-framing hooks

Candidate threads for the paper writeup, ranked by concreteness of the contribution:

1. **INDIRECT-detection failure mode with a named remedy.** Concrete, measurable deficiency in naive LLM adjudicators; lexically detectable signal; prompt-level fix evaluable on train. Good for a "concrete improvement, not vibes" narrative.
2. **First 9-way Sarol baseline.** No prior published baseline at 9-way granularity. Even if the first number is modest, the granularity is novel.
3. **Verifiable-reward hygiene for agentic pipelines.** Pitch the train/test discipline as a contribution in its own right — what gradient-based ML takes for granted is not yet standard practice for agentic-pipeline prompt engineering.
4. **Error taxonomy of adjudicator failures.** Using train as a labeled source of systematic error modes — the INDIRECT blind spot, the severity-under-commitment pattern (s4), etc. — is the same thing gradient-training does automatically via loss gradients, but made legible at the failure-class level.

## Reproducibility pointers

- Predictions: `experiments/sarol-2024/predictions/smoketest.jsonl`
- Staging trees (per-claim ledger, evidence, claims, verifications, usage): `experiments/sarol-2024/staging/smoketest/s1..s5/`
- Gold (outside repo, agent-invisible): `$HOME/.paper-trail/gold/sarol-2024/train/<citekey>.json`
- Adjudicator prompt variant: `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`
- Rubric spec: `experiments/sarol-2024/specs/verdict_schema_sarol.md`
- Sealed test split: `$HOME/.paper-trail-sealed/sarol-2024-test/` (do not read; unseal only for locked-config final eval)
