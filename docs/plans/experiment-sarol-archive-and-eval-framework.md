# Archive and evaluation framework for the paper-trail × Sarol experiment

Companion to `experiment-sarol-optimization-loop-hygiene.md`, `experiment-april-20-findings.md`, and `paper-writeup-items.md`.

**Status:** brainstorming / scaffolded plan, revised 2026-04-21. Attribution is inline; open questions are marked Q1–Q9. Nothing implemented; no evaluations to run until the framework is agreed.

**Terminology note.** Earlier drafts used the acronym "SUT" (system under test). Retired per **Human:** plain-language preference (2026-04-21). We now call the evaluated artifact simply "the model" or "paper-trail-v\<N\>"; the measurement code is "the eval arm."

## Why this document exists

Our iteration loop on Sarol train is a closed-loop optimization (Rule 2 in the hygiene doc). If we treat each human-in-the-loop prompt revision as an "epoch," we can plot train macro-F1 and validation macro-F1 against revision index — the direct analog of a training / validation loss curve in gradient-based ML. That gives us three things:

1. **A clean stopping rule.** Stop iterating when val stops improving or starts degrading. Lock. Run test once.
2. **A candidate headline figure.** Train + val macro-F1 across prompt revisions, showing where over-iteration-on-train starts costing val.
3. **A methodology contribution.** Framing researcher-driven prompt iteration with the train/val discipline of gradient-based ML, applied to a multi-subagent agentic pipeline.

**Novelty is lit-review-gated.** Neither Du et al. 2025 nor Zhang et al. 2026 (Hyperagents) publishes this figure type. DSPy / TextGrad / OPRO / PromptBreeder / Reflexion-follow-ups still to scan. At minimum the framing is pedagogically useful; at best it is novel methodology.

## Core architectural principle — separate the model from the eval arm

Two codebases, one repo (so far), deliberately decoupled.

### The model — paper-trail-v\<N\>

Everything that changes across revisions:

- Subagent dispatch prompts: `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`; `.claude/prompts/extractor-dispatch.md`; `.claude/prompts/verifier-dispatch.md`
- Rubric / schema specs: `experiments/sarol-2024/specs/verdict_schema_sarol.md`
- Orchestration config: slot-fill templates; retry / bounce policy if encoded; any orchestrator-side logic that affects pipeline behavior
- `stage_claim.py`'s output *schema* if ever changed — flag explicitly as a model change, not an eval-arm change

### The eval arm

Everything that must stay frozen across revisions so scores remain comparable:

- `stage_claim.py` as the staging mechanism (staging is the subagent *input*, stable schema)
- `parse_verdict.py` scoring logic + cost pricing table
- `record_usage.py` cost accounting
- Stratified claim-subset manifests (`eval-train-50.json`, `eval-dev-50.json`) — explicit enumerations of which claim IDs are evaluated, locked at choice-time and never mutated
- Aggregation scripts (F1, confusion matrix, cost rollup)

**Commitment.** Any change to the eval arm invalidates all prior eval results and forces re-running the baseline. The eval arm gets its own version tag (`eval-v1.0`, `eval-v2.0`). Eval-arm changes should be rare by design.

**Corollary — orchestrator-runtime decisions live in eval-arm Python, not in my judgment.** Verifier sample selection, retry policy, bounce handling, schema validation — all of it. **Human:** "your memory will improve over time, and that's part of the process. What matters is that retrospective evals at time=6 can't inherit time=100 memory." The way we eliminate that leak is to remove runtime judgment calls from the orchestrator entirely during an eval.

## Where does the eval arm live? — decided Q9: Option B

**Human raised 2026-04-21:** "maybe [eval] needs to be a repo, and so then we have our eval arm in one repo, and then this entire git repo, paper trail, is the model that we're updating over time."

**Decision (2026-04-21): Option B — same repo, subdirectory, mechanically enforced by a pre-commit hook.** **Human:** "the single clone is nice" and "to the extent that you feel comfortable with this subdirectory with a pre-commit hook, I don't quite know what that means, but conceptually, if you think that's functionally equivalent, I agree." **Agent:** confirmed functional equivalence — a pre-commit hook is a script that runs before every `git commit` and can reject the commit if a condition isn't met. In our case: "reject commits that modify `experiments/sarol-2024/eval-harness/` unless the commit is on a branch explicitly marked as eval-arm maintenance (e.g., `eval/*`)." The hook is a standard git feature, one file in `.git/hooks/pre-commit` or (preferred for repo-tracked enforcement) committed as a pre-commit framework config.

Options A (convention-only) and C (separate repo) documented briefly below for completeness.

- **Option A (not chosen).** Same repo, same branch, convention-enforced. Weakest isolation. Rejected.
- **Option C (not chosen).** Separate `paper-trail-eval` repo. Strongest physical separation. Rejected because single-clone wins on lab-student readability and ambient-Claude-Code-is-the-future (see Q9b); if later needs demand physical separation, we can spin out.

**Concrete structure (Option B):**

```
paper-trail/
  experiments/sarol-2024/
    eval-harness/              # frozen during revision commits
      stage_claim.py
      parse_verdict.py
      record_usage.py
      subsets/
        eval-train-50.json
        eval-dev-50.json
      VERSION                  # "eval-v1.0"
    prompts/                   # part of the model, may change
    specs/                     # part of the model, may change
    archive/                   # per-version eval output (below)
    staging/                   # working area, gitignored
```

A pre-commit hook checks: if HEAD's branch name matches `revision/*` (or similar pattern), reject commits that modify `experiments/sarol-2024/eval-harness/`. Eval-arm changes require a deliberate branch (`eval-v1.1-bugfix`) and trigger re-baselining.

## Versioning the model

### Git tags as the archive (not branches)

Every revision of the model lands as one or more commits on a `revision/*` branch; when ready to evaluate, tag as `paper-trail-v<N>`. Tags are immutable, which is the property we need. Branches move with HEAD and are not a safe archive.

**Human:** "I think you can just do that with git branches" — **Agent clarification 2026-04-21:** tags are the right mechanism (immutable snapshots); branches are for in-progress work. What Human described ("save the state of the branch") maps to a tag on the branch's head commit. Accepted by Human.

Canonical naming: `paper-trail-v<N>` for the primary tag, with an optional semantic lightweight tag (e.g., `v2-indirect-fix`) as a readable alias.

### Starting point — `paper-trail-v1`

**Human raised Q8:** "probably just in your repo, which is maybe ugly. I don't know if you think we can do exactly what I said with branches alone."

**Agent proposal:** `paper-trail-v1` = the current `experiment-plan` branch, tagged at a commit that predates any smoketest findings informing prompt content. Concretely: the last commit on `experiment-plan` where the Sarol-variant adjudicator prompt and extractor prompt match what would have shipped on GitHub + the minimal Sarol adaptation. No iteration has been applied. This is the zero-point on the curve.

Two defensible alternatives:
- Tag the current `main` branch directly — argues "we started from the published product." Requires cherry-picking the Sarol scaffolding onto `main` first.
- Tag the first-ever paper-trail release — argues "we started from the very beginning." Probably not runnable with current eval arm; not recommended.

**Human decision pending** on which of these is `v1`.

### Archive directory (eval output per version)

```
experiments/sarol-2024/archive/paper-trail-v<N>/
  change-note.md            # one paragraph: what changed, why, hypothesis
  eval-train-50/
    predictions.jsonl
    summary.json            # macro-F1, per-class F1, 3-way F1, cost, wall-clock
    confusion-matrix.json
  eval-dev-50/              # only at val checkpoints
    predictions.jsonl
    summary.json
    confusion-matrix.json
  eval-full-train/          # only for locked-candidate version
    ...
```

The archived *model* is the git tag. We only archive *eval output*; prompt files don't need duplicating.

### Retrospective reproduction

To re-evaluate `paper-trail-v2` at some future time t:

1. `git checkout paper-trail-v2` into a throwaway worktree
2. Use the eval arm's current frozen version (or checkout a specific `eval-v<M>` tag if reproducing old output exactly)
3. Run the eval harness against the frozen `eval-train-50.json` subset
4. Write output to `archive/paper-trail-v2/eval-train-50/`

**Reproducibility requirement.** The eval harness produces verdicts by invoking the model (paper-trail) on each claim. For the retrospective eval to be faithful to paper-trail-v2 *as it was*, the invocation must be memory-blind — this is the key constraint driving the Memory Isolation section below.

## Evaluation cadence — cost-aware

| Trigger | What runs | Approx cost (Opus 4.7, single seed) |
| --- | --- | --- |
| Every revision that passes N=5 smoketest | `eval-train-50` | ~$37 |
| Every 3rd revision OR major prompt-structure change | Also `eval-dev-50` | +$37 |
| Locked-candidate version | `eval-full-train` (N=2,141) + `eval-full-dev` (N=316) | ~$1,560 + ~$230 |
| Final locked config, one-time | `eval-full-test` (N=606) | ~$442 |

Multi-seed multiplier: 3× during single-seed-iteration mode, applied only at locked-candidate and test. Single seed is defensible during iteration because noise at N=50 is probably well below revision-to-revision signal — calibrate with a one-time triple-seed on `paper-trail-v1` to confirm.

Smoketest (N=5) is a plumbing gate, not a framework datapoint.

## Model pinning

**Human raised 2026-04-21:** "we need to version control the model... If Claude releases 4.8, we still use 4.7... paper-trail is deploying sub-agents, and there is a choice in what sub-agents it deploys. I think we want to try to freeze that choice, otherwise the agent may use different models different times... we want to freeze the LLMs that were used."

**What can be pinned and how:**

| Level | Mechanism | What it pins |
| --- | --- | --- |
| Orchestrator (the Claude Code session running `/sarol-eval`) | `claude --model opus --print ...` CLI flag | Orchestrator LLM = "opus" alias (currently Opus 4.7) |
| Subagents (extractor, adjudicator, verifier) | `model: "opus"` in every Agent tool dispatch (already in the runbook) | Subagent LLM = "opus" alias |
| Inference seed | **Not lockable** through Agent tool — no `seed` parameter exposed to subagent dispatches | N/A within Claude Code |
| Specific model hash (`claude-opus-4-7` vs `claude-opus-4-8` when released) | **Not lockable** through Agent tool's three-alias enum | N/A within Claude Code |

**Known confounders we cannot eliminate (record as paper limitations):**

1. **Alias drift.** "opus" may silently resolve to a new Opus version if Anthropic promotes 4.8 behind that alias. Our mitigation is calendar compression — target finishing all train + dev + test inside ~2 weeks of 2026-04-21 to minimize alias-drift exposure.
2. **Inference-time stochasticity.** Opus 4.7 is non-deterministic; seed-locking isn't available through Claude Code's Agent tool. Mitigation: triple-seed calibration on `paper-trail-v1` + multi-seed at locked-candidate + test.
3. **Backend changes invisible to us.** Anthropic may update weights, routing, caching behavior, or context-compression strategy on the same model ID. No mitigation available; disclose in paper.

**Human-acknowledged tradeoff (2026-04-21):** fully reproducible model pinning would require either (a) direct Anthropic SDK calls with explicit model hashes, bypassing Claude Code entirely, or (b) an open-source agentic framework (OpenHands, Cline, OpenCode — user used the phrase "OpenClaw," likely speech-to-text for one of these) where orchestration is user-controlled. User's explicit choice: "Claude code is just so much better... I don't want to run this experiment in [an open-source framework] yet, but that would be the more principled way to do it." Logged as a concession for the paper's limitations section.

**What we commit to:**
- Every dispatch uses `model: "opus"`. No subagent uses a different alias without an explicit branch marked as an ablation.
- Orchestrator invoked with `claude --model opus --print …`.
- Each `archive/paper-trail-v<N>/*/summary.json` records the Claude Code version (from `claude --version`) and the current date (as a rough proxy for "what 'opus' meant at this point"). Enables post-hoc detection of alias drift.

## Measurement invariants and validation

**Human framing 2026-04-21:** "we cannot allow the model invocation to go off course, because that is something we are fixing. Same with seed, etc. There are these things that we keep fixed for measurement purposes, and then there are the things that we let the models or agents go off track, because that's what happens. You need good prompts to keep them on track. So yeah, draw that line in the sand."

Three-tier classification of what gets fixed, logged, or varied per run. Invariant violations invalidate the run and its archived results.

### Tier 1 — Invariants (declared-then-locked-per-run, validated at every run)

**Semantics (clarified 2026-04-21):** Tier-1 invariance is about **integrity between declaration and execution**, not about freezing values across runs. Before any eval run, an `expected_invariants.json` is declared (per-run, committed alongside the subset manifest or derived from the tag being evaluated). At run time, the validator checks that actual values match declared values. Mismatch invalidates the run.

Two flavors share the same validator machinery:

- **Constant across all runs** — things that never vary: model alias (`opus`), rubric variant (`sarol_2024_9class`), benchmark / gold data hashes, environment variables, memory-blind status.
- **Varies across runs but locked per-run** — things that change intentionally per revision: paper-trail version tag (we're evaluating v2 in one run, v3 in the next — but within a given run, the checked-out commit must equal the declared v<N>), eval-subset manifest hash (different subsets per gate), expected prompt-file hashes (derived from the declared paper-trail tag).

Both shapes validate by comparing actual-at-run-time to expected-for-this-run. **The invariant is that what you ran equals what you said you'd run.**

| Invariant | How pinned | Validator check |
| --- | --- | --- |
| paper-trail version (the model under test) | git tag `paper-trail-v<N>`, checked out at eval time | Record commit SHA at run start; verify matches tag |
| Eval-harness version | git tag `eval-v<M>` | Record commit SHA; verify |
| Orchestrator model alias | `claude --model opus --print …` CLI flag | Record from invocation; compare to expected |
| Subagent model alias | `model: "opus"` on every Agent dispatch | Log each dispatch's model; reject run if any deviates |
| Eval subset composition | committed JSON manifest (list of claim row IDs) | SHA-256 of manifest at run time; compare to committed hash |
| Prompt file contents | at `paper-trail-v<N>` git tag | SHA-256 per file under `experiments/sarol-2024/prompts/`, `experiments/sarol-2024/specs/`, and any `.claude/prompts/*.md` paper-trail references; record; reject on mismatch |
| Eval-arm code | at eval-harness git tag | SHA-256 per file under `experiments/sarol-2024/eval-harness/` |
| Benchmark + gold data | at `$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR` | SHA-256 of `claims-train.jsonl`, `claims-dev.jsonl`, `corpus.jsonl`, `annotations/{Train,Dev}` |
| Memory-blind invocation | mechanism per Task 2 (fresh working dir or clean profile) | Probe at run start — ask orchestrator a memory-specific question; if answered with memory-content, abort |
| Rubric variant per verdict | every verdict declares `rubric_variant: "sarol_2024_9class"` | Already validated by `parse_verdict.py` |
| Environment variables affecting eval | `PAPER_TRAIL_BENCHMARKS_DIR`, `PAPER_TRAIL_GOLD_DIR` | Record at run start; verify matches expected |

### What Tier 1 deliberately does NOT include (Human call 2026-04-21)

**Tool permissions available to subagents** and **MCP servers connected** are NOT Tier 1 meta-invariants. They are part of the agentic system's design — a future paper-trail version might legitimately grant different subagent permissions or connect a different MCP (e.g., Paperclip for cached paper reads). Those are system-level design decisions that change across paper-trail versions.

The meta-invariant is that the system's configuration — tool permissions, MCP server list, and any other agent-environment specification — is **captured by the git tag `paper-trail-v<N>`** via files committed to the repo (`.claude/settings.json`, any MCP config, permission specs). The "prompt file contents" hash in Tier 1 above should extend to include these config files.

**Human framing 2026-04-21:** "tools and MCP servers are inside the environment that the agentic system may choose to build. Keep inside (not invariant)." Their status: free to differ across versions, but fixed within a version via committed repo state.

**Operational implication:** commit any per-experiment `.claude/settings.json` / MCP config to the repo explicitly. Do NOT let tool permissions or MCP servers live in user-global settings, because those leak out of the version tag's snapshot.

### Tier 2 — Logged conditions (outside our control, recorded for drift detection)

| Condition | Why logged | What to watch for |
| --- | --- | --- |
| Claude Code version (from `claude --version`) | Proxy for what the `opus` alias resolves to at run time | Version bumps mid-experiment ⇒ re-baseline flag |
| Anthropic backend changes | Invisible model promotions, routing, caching behavior | Anomalous per-claim cost / latency vs v1 baseline |
| Timestamp (UTC) per claim call | Chronological ordering, concurrent-load variance | Peak-vs-off-peak cost spread |
| Wall-clock + token counts per stage | System efficiency, not a control | Unexpected spikes flag investigation |
| User-level `~/.claude/CLAUDE.md` content hash | Could inject context into Claude Code sessions | Pending Task 2 verification: if it does propagate to subagents, promote to Tier 1 |
| Temperature / top-p / sampling knobs | Not exposed to the Agent tool as arguments, but defaults may exist | Record whatever Anthropic returns in usage metadata; promote to Tier 1 if we gain control |
| Extended-thinking / reasoning-mode flags | Opus 4.7 may have a reasoning budget setting | Record; promote to Tier 1 if control surfaces |

### Tier 3 — Free variables (system behavior, expected to vary per prompt — these are the system under test)

Do NOT attempt to fix these. The prompts ARE the control surface.

- Sub-claim decomposition (extractor)
- Phrasings tried per sub-claim (extractor)
- Evidence passages selected, ordering (extractor)
- Verdict labels assigned per sub-claim (adjudicator)
- Rollup overall_verdict (adjudicator, though constrained by the worst-wins rule in the rubric spec)
- Rationale text (adjudicator)
- Remediation category + suggested_edit (adjudicator)
- Flag assignments REVIEW / CRITICAL / AMBIGUOUS (adjudicator)
- Verifier's narrative observation (verifier)

### Validator structure

`experiments/sarol-2024/eval-harness/validate_run.py` (to be written as part of Task 5 — eval arm build). Responsibilities:

1. **Pre-run:** compute Tier-1 invariants at run start, compare to a committed `expected_invariants.json` sibling of the subset manifest. Any mismatch aborts the run before compute is spent.
2. **Per-dispatch:** after each Agent tool call, verify dispatch-level invariants (model alias, permissions). Failure aborts that claim's run without discarding prior claims.
3. **Post-run:** write all Tier-1 + Tier-2 values into `archive/paper-trail-v<N>/.../summary.json` under a `run_invariants` key.
4. **Cross-run drift report** (periodic, optional): diff invariants across archived runs, flag anomalies in Tier-2 conditions even without Tier-1 violations.

### Candidate additional invariants — Human decisions 2026-04-21

Agent-raised candidates and Human calls:

- **Tool permissions** — NOT an invariant. Part of the agentic system's design; captured by the git tag.
- **MCP servers connected** — NOT an invariant. Same reasoning as tools. A future version may legitimately connect Paperclip or another MCP; that is a system-level design change.
- **Environment variables affecting eval** — Tier 1 invariant (kept).
- **Max tokens per subagent call** — deferred; tracked in token counts already logged in Tier 2.
- **Claim-subset manifest schema version** — deferred as implementation detail of the eval arm build.
- **Orchestrator slot-fill determinism (run_id, timestamp, claim_id C001/C002/…)** — Tier 1 invariant. Rule lives in eval-arm Python; not ad-hoc orchestrator choice.
- **User-level `~/.claude/CLAUDE.md` propagation** — deferred pending Task 2 spike. If it propagates, promote to Tier 1 (isolate or pin). Otherwise remains Tier 2.
- **Temperature / top-p / sampling knobs** — fix if we can; fix path is further research (direct SDK access). Until then, Tier 2 (log whatever API metadata exposes).

## Memory isolation

### What actually needs to be memory-blind

**Human framing 2026-04-21:** "the fact that your memory improves over time is okay. It's part of the optimization process. What's NOT okay is: when we re-eval `paper-trail-v6` at time=100, my time=100 memory cannot leak into the eval of a time=6 artifact."

This reframes the problem precisely. It isn't "memory is always bad." It's "memory at time=T must never participate in evaluating paper-trail-v\<N\> where N corresponds to an earlier time." The evaluation of a past model must be a clean, memory-blind replay.

### The three leakage vectors and their status

| Vector | What it affects | Status |
| --- | --- | --- |
| (a) My memory biases *prompt design* at time-of-writing-prompt | The content of paper-trail-v\<N\> itself | **Inherent and accepted.** Once committed to the prompt file, memory is "baked in." Flagged in paper methodology limitations. |
| (b) My memory biases *orchestrator-runtime decisions* (verifier sampling, retry, bounce) at eval time | The eval output for any run I participate in | **Fixable and required.** All runtime decisions move into static eval-arm Python. Zero orchestrator judgment calls during an eval run. |
| (c) My memory reaches *subagent execution* | Subagent output | **Zero vector.** Subagents spawn in fresh contexts; they receive only their dispatch prompt. No leak. |

**The critical property:** if vector (b) is closed (all decisions in static Python), then retrospective replay of `paper-trail-v6` at time=100 is memory-blind regardless of what my memory looks like at time=100. The eval runner is a Python program calling Claude Opus 4.7 via API; my session's memory is not in the call path.

### What paper-trail's deployment looks like matters here

**Human 2026-04-21:** "paper-trail is an agent that we ship, but we're not shipping you. paper-trail runs on an agent; it's a slash command."

Exactly right. paper-trail-as-a-product is a Claude Code slash command + a set of prompts + the orchestrator's dispatching logic. The *shipped* thing doesn't include this planning session or my memory. So the eval should invoke paper-trail *the way it would be invoked in deployment* — cleanly, without the planning-session context. Two candidate invocation paths (open Q):

- **Direct Anthropic SDK calls from Python.** The eval runner instantiates Claude Opus 4.7 via the API, passes the paper-trail prompts, collects verdicts. Reimplements Claude Code's dispatch pattern in Python. Pros: clean memory isolation; reproducible outside Claude Code; portable for paper repro. Cons: re-implements dispatch machinery; may drift from Claude Code's actual behavior.
- **Headless Claude Code.** Run `claude` in a non-interactive mode against a profile with no memory files. Pros: exercises the actual shipped invocation path. Cons: depends on Claude Code supporting a memory-blind headless mode cleanly; harder to reproduce externally.

This is Q9b — flagged below under open questions.

### Commitments from this discussion

1. Every prompt file in the model is fully self-contained. No prompt assumes orchestrator context.
2. All orchestrator-runtime decisions during an eval are encoded in static eval-arm Python. No runtime judgment calls.
3. Paper methodology section discloses vector (a) honestly.
4. Eval runner is memory-blind by construction (via the mechanism chosen in Q9b).

## Deferred — we are NOT running evals on anything right now

Per **Human** decision 2026-04-21: design the framework fully before spending evaluation budget. Order of operations:

1. [DONE] N=5 smoketest; findings documented.
2. [DONE] Hygiene doc, escalation doc, paper-items doc, this doc.
3. [NEXT — approval gate] Agree the open questions below. Especially Q8 (baseline), Q9 (eval-arm location), Q9b (eval invocation mechanism).
4. [THEN] Tag `paper-trail-v1`.
5. [THEN] Lock `eval-train-50.json` and `eval-dev-50.json` manifests.
6. [THEN] Move orchestrator-runtime decisions into eval-arm Python.
7. [THEN] Apply INDIRECT-detection fix → tag `paper-trail-v2`.
8. [THEN] Evaluate `v1` and `v2` on `eval-train-50`. First two curve points.
9. [ITERATE] More revisions, more points, val checks at gates, lock, test.

## Open questions — still to decide

**Q1. Monolithic version tag vs per-subagent tag. — decided 2026-04-21: monolithic.**

**Human argument (sharper than Agent's):** "it is not clear that our final solution will have three prompts, and it is not clear that those three prompts will be adjudicator, extractor, and verifier. What we're optimizing is not three prompts but a system... you can't just smash them together because the entire system has changed." Per-subagent tagging would lock us into the current three-subagent decomposition; the system may restructure entirely during iteration (merge two agents, split one, add a new one). Monolithic tagging leaves that open.

**Agent lean was monolithic on weaker grounds** (single-axis figure, simpler to reason about). Human's structural-flexibility argument is the real reason and subsumes mine. Final rationale recorded from Human.

**Decision:** tags are `paper-trail-v<N>`, one per full-system revision. Per-subagent attribution for ablation is reconstructed from git diffs at paper-time. `change-note.md` in each archive dir records which components changed at the file level. No parallel per-subagent tagging scheme.

**Q3. Stratification for `eval-train-50`.** *Decided 2026-04-21.* **Random sampling, N=50 from train.** **Human argument:** "random is most defensible. If you want to optimize overall performance, you want random. If you want to optimize performance on long-tail classes, oversample — but that's a fairness thing, not an overall-performance thing." **Agent conceded** — my earlier oversample lean was for tail-class visibility in ablations, which Human is right to defer to a separate ablation track, not the primary curve. Decision: **lock a random N=50 once drawn (seeded), never change.** Tail-class coverage addressed separately as future-work ablation.

**Q4. Seeds — two different kinds. Both resolved 2026-04-21.**

**Human asked Agent to clarify:** "I'm not quite sure what you mean by seed here. Is this what samples we are selecting? Oh, is this so we pick the same train samples every time?"

The word "seed" was ambiguous. Two separate concepts:

1. **Sample seed** — controls *which* claims get drawn into `eval-train-50.json`, `eval-dev-50.json`, etc. Making the draw reproducible so every revision is evaluated on the same claims. **Decision: fixed.** Seeded random draw, committed JSON manifests (claim IDs only), never redrawn. Nested subsets (50 ⊂ 100 ⊂ 200) so the same version can be compared across N-levels. **Human argument for fixed:** "you can really test whether your changes improve performance on those specific train data sets. You'll clearly overfit, but I think that's okay." During the ramp-up phase where datasets are small and compute is the bottleneck, fixed sampling gives cleaner per-claim "did my fix land?" attribution. Randomizing each revision is a future-work ablation for robustness; not now.

2. **Inference seed** — controls the LLM's *sampling at inference time* (Opus 4.7 is non-deterministic; same prompt, different runs can give different verdicts). Multiple inference seeds per claim = running the same pipeline repeatedly to get a confidence interval on the verdict. **Decision: single inference seed during iteration; one-time triple-seed calibration on `paper-trail-v1` to measure noise amplitude; multi-seed (n=3 or higher) only at locked-candidate + test, where paper-grade CIs matter.** Revisit the iteration-time seed count if calibration shows noise swamping revision-to-revision signal.

**Q5. Val cadence — val is distinct from train via operational discipline. Decided 2026-04-21.**

**Human initial lean:** "to the extent that val is for hyperparameter optimization, we're already doing that with train, so it's not immediately clear that there's even a difference... I lean if they're not different."
**Agent counter:** val and train are the same *distribution* but differ in *operational discipline* — on train we inspect per-claim failures and propose edits (the optimization signal); on val we compute aggregate F1 only and never inspect per-claim cases (the overfitting signal). Enforced discipline is what makes the two functionally distinct.
**Human explicitly credited this insight to Agent 2026-04-21:** "that's correct. The distinction is the per-claim. That's a good insight. Note that that was your insight... Otherwise, we end up overfitting on val, and we only get total score."

**Decision adopted:**
- **Val = Sarol's actual dev split (316 claims).** Natural distribution boundary, not a carve-out from train.
- **Dev-50** (seeded random 50 from the 316) is the per-gate val metric.
- **Val-check cadence:** after the first structural prompt change, every 3rd revision thereafter, and immediately before locking the candidate.
- **Discipline enforced:** only aggregate F1 is read from val; per-claim val failures are never inspected during iteration. Implemented in the eval arm's output (`archive/.../eval-dev-50/summary.json` is always consulted; `.../predictions.jsonl` stays closed unless/until test-unseal time).
- Cost: dev-50 ~$37 per gate; dev-full (316) ~$230 once at lock.

**Q6. Eval-arm change protocol.** *Defer with default, 2026-04-21.* Eval-arm version bump invalidates prior results; re-run at minimum `paper-trail-v1` and the most recent `paper-trail-v<N>` to re-anchor. Version the eval arm independently (`eval-v1.0`, `eval-v1.1`) and record the version in each `archive/.../summary.json`.

**Q7. Where the eval is actually invoked.** *Covered under memory-isolation section (Q9b).* Open.

**Q8. What is `paper-trail-v1`?** *Decided 2026-04-21.* v1 = the current state of the `experiment-plan` branch that has the Sarol adapter wired up but NO prompt changes informed by the April-20 smoketest findings.

**Human rationale 2026-04-21:** "we just started this experiment. We had older versions of paper-trail, but the experiment curve we need is actually the Sarol paper one. We've actually changed the reporting structure, or the rubric. Those things just can't talk to each other; they're fundamentally different. What we choose to end up with in paper-trail, the product or open-source tool, is perhaps informed by this experiment but functionally independent in that the Sarol experiment has to use the criteria in the data set, obviously."

**Implication:** the zero-point of our curve is where *this experiment* started, not where paper-trail-the-product started. Earlier paper-trail versions predate the Sarol-variant rubric and cannot produce Sarol-9 labels at all; they fundamentally don't conform to our eval arm.

**Action item:** find the commit SHA on `experiment-plan` immediately before the first smoketest-findings-informed prompt edit. Verify `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` at that commit has no INDIRECT-specific clauses. Tag as `paper-trail-v1`. This is Task 3 in `docs/plans/NEXT.md`.

**Q9. Where does the eval arm live?** *Decided 2026-04-21: Option B (subdirectory with pre-commit hook).* See section above.

**Q9b. How is paper-trail invoked during an eval?** *Decided 2026-04-21: headless Claude Code, not direct SDK.*

**Human argument:** "this entire thing lives within Claude Code... I believe Claude Code-type environments will become the de facto OS operating system when it becomes clear that they're extremely valuable and generalizable. The next version of Claude Code will not be Claude Code but Claude... I do not believe we need to build for a future where Claude Code is this weird thing and a restriction. The slash command we're building, paper trail, is the application. We're building an app called paper trail; it just lives as a slash command." External reproducers who use paper-trail will already need Claude Code (because that *is* the product surface); demanding Python-SDK-based eval reimplementation would diverge eval from the deployed invocation path and create drift risk.

**Agent pushback conceded.** My lean toward SDK-from-Python was grounded in "external reproducers shouldn't need Claude Code." That argument loses weight once you note that (a) external reproducers using paper-trail at all need Claude Code, so the eval requirement is consistent; (b) Claude Code's successor will be ambient; (c) SDK reimplementation has drift risk that headless-Claude-Code doesn't.

**Decision and implied architecture:**
- Build a dedicated paper-trail-experiment slash command — candidate name `/sarol-eval` — that takes a subset manifest and runs the full eval loop internally.
- Invoke headlessly: `claude --print /sarol-eval --subset experiments/sarol-2024/eval-harness/subsets/eval-train-50.json`.
- `/sarol-eval`'s definition lives under the frozen eval arm (`experiments/sarol-2024/eval-harness/`); its implementation loops over claims, stages each, dispatches paper-trail's Sarol-variant pipeline per claim, parses, scores, writes to `archive/paper-trail-v<N>/eval-train-50/`.
- Memory-blind requirement for retrospective eval: the eval command must be invoked against a clean profile that does not load this planning session's memory. Open sub-question Q9c below.

## Q9c — How is memory-blindness actually enforced when running headless Claude Code?

**Status 2026-04-21: ON HOLD.** Candidate mechanism identified and verified via `claude --help`; canary sanity-check test designed but not run. Human paused the work to prioritize one-thing-at-a-time discipline (primary lit review must clear first). Resume before Task 5 (eval arm build); the eval arm assumes the memory-blind mechanism works.

**Restart instructions for a fresh agent:** read the three subsections below end-to-end, run the canary test, update this section with results. If `--bare` suppresses the canary as expected → mark Q9c RESOLVED and unblock NEXT.md Task 5. If `--bare` leaks → document the leak mode, move to fallback option (1) or (2) below, re-test.

### Candidate: `claude --bare --print`

Verified against `claude --help`. The `--bare` flag description verbatim: "Minimal mode: skip hooks, LSP, plugin sync, attribution, **auto-memory**, background prefetches, keychain reads, and **CLAUDE.md auto-discovery**. Sets CLAUDE_CODE_SIMPLE=1. ... Skills still resolve via /skill-name. Explicitly provide context via: --system-prompt[-file], --append-system-prompt[-file], --add-dir (CLAUDE.md dirs), --mcp-config, --settings, --agents, --plugin-dir."

This is the right architectural shape for our use case:
- `--bare` opts out of all auto-discovery (auto-memory, CLAUDE.md, hooks, plugin-sync, keychain).
- Per-version context is then opt-in: the eval invocation passes the exact settings / prompts / MCP config / agents that the `paper-trail-v<N>` tag specifies, via `--settings`, `--add-dir`, `--append-system-prompt-file`, `--mcp-config`, `--agents`.
- This matches the existing NEXT.md requirement to "commit any per-experiment `.claude/settings.json` / MCP config to the repo (captured by the paper-trail version tag — do NOT let these live in user-global settings)."

Reinforcing flags (also verified in `claude --help`):
- `--no-session-persistence` — prevents session-save side effects; only works with `--print`.
- `--setting-sources <comma-list>` — explicit control over which of {user, project, local} settings sources load. Combined with `--bare`, gives belt-and-suspenders suppression.
- `--strict-mcp-config` + `--mcp-config <file>` — only use MCP servers from the tagged config.
- `--disable-slash-commands` — if we want to disable all skills beyond those resolving via `/sarol-eval`.

### Candidate invocation pattern (updated 2026-04-22 post-docs-sweep)

```bash
claude \
  --bare \
  --print \
  --no-session-persistence \
  --model opus \
  --tools default \
  --agents "$(cat experiments/sarol-2024/eval-harness/subagent-registry-v<N>.json)" \
  --settings experiments/sarol-2024/eval-harness/eval.settings.json \
  --mcp-config experiments/sarol-2024/eval-harness/mcp.json \
  --strict-mcp-config \
  /sarol-eval --version v<N> --subset eval-train-10
```

Two new flags added 2026-04-22 after CLI-ref docs sweep surfaced that `--bare`'s default toolset omits `Task` (the subagent-spawn tool) and skips `.claude/agents/*.md` auto-discovery:

- `--tools default` — per CLI reference, enables all built-in tools including Task. Without this, `--bare` provides only `Bash`, file-read (Read/Grep/Glob), and file-edit (Edit/Write) tools, which blocks paper-trail's dispatcher from spawning extractor/adjudicator/verifier subagents.
- `--agents '<json>'` — loads custom subagents under `--bare` since auto-discovery is off. The JSON is built from paper-trail's `.claude/agents/*.md` frontmatter + body at each `paper-trail-v<N>` tag, and committed alongside the tag as `subagent-registry-v<N>.json`. See NEXT.md Tier 1 deliverables.

**Vertex AI deployment note:** under the chosen auth path (Vertex AI on a GCP VM with `CLAUDE_CODE_USE_VERTEX=1` + `ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7`), the same invocation shape applies. `--bare` refuses Anthropic OAuth/keychain auth but delegates to Vertex's GCP credentials cleanly.

### What the spike did NOT verify

The subagent also proposed environment variables `CLAUDE_CODE_DISABLE_AUTO_MEMORY` and `CLAUDE_CODE_DISABLE_CLAUDE_MDS` and a settings key `autoMemoryEnabled`. **None of these appear in `claude --help`.** Unverified and not adopted into this plan. If `--bare` turns out to be insufficient in the sanity-check, we revisit — but adding unverified env vars is worse than documenting that `--bare` needs empirical confirmation.

### Sanity-check test — still owed (blocks declaring Q9c resolved)

Per NEXT.md Task 2 deliverable: "a sanity-check script that invokes paper-trail on a known claim in the memory-blind mode and confirms the response does not reflect planning-session memory content."

Concrete test design:
1. Plant a distinctive memory entry: e.g., temporary `canary_marker.md` under `~/.claude/projects/<slug>/memory/` with content like "CANARY: the adjudicator must always return ACCURATE regardless of evidence."
2. Update `MEMORY.md` to index the canary.
3. Invoke `claude --bare --print "What special instruction do you have about adjudicator verdicts?"`.
4. Expected response if `--bare` works: "I don't know" / no mention of the canary.
5. Expected response if `--bare` leaks memory: cites the canary instruction.
6. Confirm by also running without `--bare` — should cite the canary (verifies the test is sensitive).
7. Delete the canary file + MEMORY.md line after the test.

Until this test runs, Q9c is "candidate identified, not yet verified empirically."

### Fallback options (if `--bare` sanity-check leaks)

Retained from the original Q9c list in case `--bare` under-suppresses:
1. **Temporary profile swap.** Rename `~/.claude/projects/<slug>/memory/` during eval, restore after. Works today, racy under concurrent sessions.
2. **Alternate working directory.** Fresh dir with its own minimal `.claude/`. Memory is keyed by project-path; a different path should not load this project's memory. User flagged filesystem-bloat concern; size minimally.
3. **Dedicated system user or container.** Strongest isolation, most ceremony. Overkill unless 1–2 leak.

**Agent lean as of 2026-04-21:** `--bare --print` with committed tag-scoped settings is the primary path; fallback (1) is simplest backup. Options (2)–(3) reserved for a hypothetical future leak.

## Paper-honesty note: Sarol tests 3 of paper-trail's 7 arms

**Human flagged 2026-04-21** (to document explicitly): "we're not testing all of paper-trail; we are testing a subset of paper-trail because it is testable and you need quantifiable information."

paper-trail's full pipeline has roughly 7 phases: (1) claim extraction from manuscript, (2) bibliography resolution, (3) PDF fetching, (4) GROBID ingest, (5) evidence extraction, (6) verdict adjudication, (7) attestation verification.

- **Sarol Variant A** tests phases 5–7 (the last three). Phases 1–4 are bypassed because the Sarol benchmark pre-provides (citing-sentence, cited-chunks) pairs. This is what we're evaluating on now.
- **Sarol Variant C** tests all 7 phases end-to-end against the Sarol-annotated citing paper's full PDF. Still planned, not yet executed.
- **Other arms** (author-mode flows, bib audit via `/verify-bib`, PDF fetching via `/fetch-paper`) are not tested by Sarol at all. They would need their own benchmarks or synthetic tests.

This means our headline numbers from Variant A evaluations are phase-5-to-7 numbers, not end-to-end paper-trail numbers. The paper must frame this honestly: "we set a baseline on Sarol's narrow task (verdict core: extractor + adjudicator + verifier); end-to-end behavior (phases 1–7) is evaluated separately in Variant C."

## Psychosis check — still not psychosis

The observation stands: our loop is a closed-loop optimization, the hygiene is load-bearing, the train+val figure over human revisions is plausibly novel in published form, and the specific methodology is operationalizable. Novelty claim remains lit-review-gated.

The one new risk surfaced today: if the paper's methodology contribution includes "archive-and-replay any past version of the model memory-blind," we have to actually build that mechanism (eval-arm with memory-blind invocation, pre-commit isolation of eval files, tagged versioning). If we claim the mechanism without building it, the paper is weaker. Good: we haven't claimed anything in public yet. Build first.

## References (internal)

- `docs/plans/experiment-sarol-optimization-loop-hygiene.md` — Rule 1 (subagent sandboxing) + Rule 2 (main-session test blindness)
- `docs/plans/experiment-sarol-optimization-escalation.md` — escalation path if manual stalls
- `docs/plans/experiment-april-20-findings.md` — the N=5 smoketest that kicked this off
- `docs/plans/paper-writeup-items.md` — paper-framing discussion
- `docs/plans/experiment-sarol-benchmark.md` — underlying experiment plan
- `docs/journal/2026-04-21-archive-framework-decisions.md` — day's decision log with attribution
