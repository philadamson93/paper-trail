# Operational hygiene for the Sarol experiment optimization loop

Companion to `experiment-sarol-leakage-hardening.md` and `experiment-sarol-hardening-implementation.md`. Those documents cover the structural defenses for subagent dispatches. This document articulates the **orchestrator-session rule**: the main planning session (the researcher ↔ LLM discussion in which failure modes are diagnosed and prompt edits are proposed) must also be test-blind, and why.

## The two rules

### Rule 1 — Subagents are structurally sandboxed from gold

**Already in place** as of commit 869003c and follow-ups. The extractor, adjudicator, and verifier subagents dispatched by the orchestrator cannot reach gold labels, claim row-ids, split names, paper buckets, or raw benchmark data.

Defenses:

- Gold files live outside the repo tree (`$PAPER_TRAIL_GOLD_DIR`, default `$HOME/.paper-trail/gold/sarol-2024/<split>/`).
- Benchmark raw data lives outside the repo tree (`$PAPER_TRAIL_BENCHMARKS_DIR`, default `$HOME/.paper-trail/benchmarks/sarol-2024/`).
- `stage_claim.py` generates opaque `ref_<6hex>` citekeys by hashing (split, claim_id, paper_bucket). The subagent sees only the opaque ref.
- `staging_info.json` contains only `citekey`, `claim_text_normalized`, `source_mode`, `multi_cit_context`, `source_description` — no claim row-id, no split, no paper bucket.
- Every dispatch appends the filesystem-restriction paragraph (see runbook). Violations invalidate the verdict.

### Rule 2 — The main planning session is test-blind by policy

**In place as of 2026-04-21.** The orchestrator / researcher LLM planning session — this session, the one where failure modes get diagnosed and prompt edits get proposed — must not see the test split of any benchmark being used for reporting.

Enforcement: test files have been moved out of `$PAPER_TRAIL_BENCHMARKS_DIR` to `$HOME/.paper-trail-sealed/sarol-2024-test/`. `stage_claim.py --split test` now fails cleanly with `FileNotFoundError`. `ls` against the sealed directory reveals filenames (and therefore split membership) but no labels; even so, the main session should not read or glob that directory.

## Why both rules matter — the less-obvious part

**Rule 1** is the obvious rule. A subagent that reads gold before emitting a verdict trivially biases the verdict. Most "don't leak labels to the grader" intuition lives here, and every benchmark-evaluation codebase implements some version of it.

**Rule 2 is the subtle one.** The main planning session — the place where the researcher and the orchestrator LLM talk through failure modes, read predictions, propose prompt edits, approve schema changes — **is the optimizer in the closed-loop optimization**. Every prompt edit that lands on disk is an output of that conversation.

If the main session sees a test label — even once, even "just to sanity check" — that observation flows into every subsequent prompt-edit proposal via human-in-the-loop effects. A researcher who has mentally noted "test claim X was labeled CONTRADICT" will subtly bias their next adjudicator-prompt edit toward catching the pattern that made X a CONTRADICT. There is no formal mechanism to "unsee" the observation.

Mathematically this is no different from training on test. The optimizer is non-differentiable, but the feedback loop is the same shape as gradient descent against test loss.

## What is and isn't allowed

### Allowed (and expected)

- Main session reads train claims + train gold freely. Train is the iteration corpus.
- Main session reads dev claims + dev gold, but only as a validation-of-winner checkpoint — not per-cycle. Continuous dev-based iteration overfits dev.
- Main session discusses Sarol's published baselines (MultiVerS, GPT-4 4-shot) — those are public numbers from the upstream paper, not our test predictions.
- Subagents read only what `stage_claim.py` wrote into their staging tree, plus the Sarol rubric spec.

### Disallowed

- Main session reads any file under `$HOME/.paper-trail-sealed/`.
- Main session globs or `ls`-es the sealed directory to see filenames, even without reading contents. Filenames in this context leak split membership, which is enough to bias test-claim selection downstream.
- Main session reconstructs test-split gold via any indirect route — re-downloading `annotations.zip` to a non-sealed location, scraping public repros, asking an LLM to recall what Sarol labels were for specific claim IDs, running the real Sarol authors' open-source tools against our test claims.
- Subagents read any file under `$PAPER_TRAIL_GOLD_DIR`. (Structurally prevented; noted for completeness.)

## When test unseals

Once per locked configuration, for a single final evaluation. All of the following must hold before unsealing:

1. Extractor + adjudicator + verifier prompts are frozen and committed on a dedicated branch.
2. Full train evaluation (N = 2,141) produces a macro-F1 number.
3. Dev evaluation (N = 316) produces an independent sanity-check number consistent with the train trajectory.
4. Pre-registered hypothesis recorded: expected test macro-F1, expected per-class F1, rationale for each.
5. Test unsealed. `stage_claim.py --split test` runs once through the full test split.
6. Numbers reported as primary results.
7. Test re-sealed if further iteration is planned; otherwise the experiment is closed.

Any deviation voids the reporting value. If test is inadvertently exposed mid-iteration, the options are:

- Swap to a fresh held-out benchmark for the paper's primary number (Sarol-style benchmarks exist; could also use a subset of Sarol test held out during the exposure).
- Report Sarol test results explicitly as exploratory rather than primary, and rely on Variant C + synthetic-injection experiments for the headline numbers.

## Enforcement summary

| Vector | Defense |
| --- | --- |
| Subagent reads gold | Gold outside repo; opaque citekeys; filesystem-restriction paragraph; scrubbed `staging_info.json` |
| Subagent reads raw benchmark | Benchmark outside repo; same filesystem restriction |
| Main session reads test claims | Test physically moved to `$HOME/.paper-trail-sealed/`; `stage_claim.py --split test` fails |
| Main session reads test gold | Gold/test/ dir never populated (would only appear if a test claim were staged — impossible while sealed) |
| Main session reads `annotations.zip` (contains test) | `annotations.zip` moved into sealed directory along with `annotations/Test/` |
| Main session reconstructs test labels via LLM recall | Policy-level: documented here, enforced by researcher discipline, flagged if observed |
| Iteration against dev | Policy-level: dev is a validation-of-winner checkpoint only |

## Why this rule is load-bearing for the paper

The paper argues (per `paper-writeup-items.md`) that agentic-pipeline prompt iteration is a closed-loop optimization with the same overfitting risks as gradient-based training. That argument is only defensible if **we ourselves held the discipline**. If the main session touched test mid-iteration, the paper's methodology contribution collapses — and so, by extension, does confidence in whatever test numbers we report.

Seal is cheap. Unsealed test is expensive.
