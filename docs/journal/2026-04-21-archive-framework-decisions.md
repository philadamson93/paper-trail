# 2026-04-21 — Archive framework discussion, decisions, open questions

Day's journal entry for the archive-and-eval framework brainstorm that followed the April-20 Sarol smoketest. Captures decisions with attribution (who raised what, who pushed back, final call) for later retrospective paper-writing. Intentionally granular about the back-and-forth — the point is to make the human/agent collaboration pattern legible.

**Referenced plan doc:** `docs/plans/experiment-sarol-archive-and-eval-framework.md`.

## Background context

Coming off the N=5 smoketest findings (`experiment-april-20-findings.md`): 1/5 at 9-way, 3/5 at 3-way, runbook gate "stop and debug before N=50" triggered. **Agent raised** the INDIRECT-detection failure mode as the headline finding (both false-ACCURATEs fit the pattern; the extractor surfaced quotes with trailing citation markers; the adjudicator didn't scrutinize). Recommended three prompt clauses as a remedy. **Human explicitly paused** the fix to first design the evaluation infrastructure that will let us measure whether the remedy actually works — and, more broadly, to set up a framework for plotting the iteration loop as a training curve.

## Decisions made today

### D1 — The iteration loop is an optimization loop; make the figure

**Raised by:** Human.
**Exact quote:** "our epochs are iterating on our prompt, me and you, right? We show a loss curve on train. When we're done, we're going to show it on val as well, and then we'll be able to see overfitting."
**Agent response:** plausibly novel framing; validated by Hyperagents 2026's acknowledgment that "AI judges are more likely to overfit to the training data." Lit-review-gated on novelty claim (DSPy / MIPROv2 / TextGrad / OPRO / PromptBreeder / Reflexion follow-ups still unread). Minimum contribution: pedagogical framing. Maximum: novel methodology.
**Decision:** adopt the framing. Plot train + val macro-F1 against prompt-revision index as a candidate headline figure. Commit to the mechanism to support it (archive + replay) before running any evals.

### D2 — Archive via git tags, not branches

**Raised by:** Human ("I kind of think you can just do that with git branches as maybe the cleanest way... I don't think that we need to save every file. We can just save the state of our git branch").
**Agent clarification:** tags are the right mechanism — branches move with HEAD and can lose snapshots; tags are immutable.
**Decision:** tag `paper-trail-v<N>` at each archived revision. Canonical integer tag with optional semantic alias (e.g., `v2-indirect-fix`). Confirmed by Human.

### D3 — Retire "SUT" jargon

**Raised by:** Human (twice, politely — "I don't know what you mean by SUT, sorry" and "again, I don't know what SUT is").
**Decision:** use "the model" or "paper-trail-v\<N\>" instead. Applied globally in `experiment-sarol-archive-and-eval-framework.md`. **Agent memory updated** (`feedback_plain_language.md`) to avoid unexpanded acronyms in future.

### D4 — `eval-train-50` uses random sampling, not stratified

**Agent initial lean:** stratified by 9-class label with oversampling of INDIRECT and ETIQUETTE (tail classes).
**Human pushback:** "random is most defensible. If you want to optimize overall performance, you want random. If you want to optimize performance on long-tailed classes, sure, you oversample those; that's a fairness thing, but that doesn't necessarily mean you do better overall."
**Agent response:** conceded. Stratification-with-oversampling is a legitimate ablation track for tail-class visibility; the primary curve should track overall-performance, and for that the honest sample is random.
**Decision:** random N=50 from train, seeded, locked once drawn. Stratified / tail-oversampled evaluation preserved for a separate ablation (future-work, not primary).

This is an interesting who-said-what data point: Agent overcorrected toward ML-folklore-stratification; Human's plainer overall-perf argument won. Worth remembering for the paper's discussion of human value in human+agent loops.

### D5 — Orchestrator-runtime decisions move into static eval-arm Python

**Raised by:** Human framing that "retrospective evals at time=100 can't inherit my time=100 memory; eval of time=6 must use time=6 context."
**Agent mechanism proposal:** encode *all* orchestrator-runtime decisions (verifier sample selection, retry, bounce, schema validation) in static Python in the eval arm. No runtime judgment calls by me during an eval. This closes vector (b) (memory → runtime → eval output) structurally.
**Decision:** adopted. Not built yet — required before first `eval-train-50` run. Sketched under "Memory isolation" in the plan doc.

### D6 — "Time evolution of memory" framing accepted into the plan doc

**Raised by:** Human, as the precise reformulation of the memory-isolation concern. "Your memory improving over time is okay; it's part of the process. What's NOT okay is time=100 memory leaking into an eval of time=6."
**Decision:** incorporated verbatim as the operative framing in the Memory Isolation section. This is the formulation the paper should use.

### D7 — Folder structure for documentation

**Raised by:** Human ("we can even do daily folders. We can build folder structures beyond plans ... Anytime you commit to a folder structure, what's critical is that it goes into Claude MD").
**Decision:**
- `docs/plans/` — stable reference plans (existing).
- `docs/journal/YYYY-MM-DD-<topic>.md` — per-topic daily entries, attribution-labeled. This file is the first.
- `CLAUDE.md` at repo root — fresh-agent orientation, folder conventions, plain-language preference, attribution convention. Created this turn.

Modularity preferred over monolithic docs per Human ("the more information in a doc, the harder it is to find later"). Daily-prefix-on-filename rather than date subfolders, so the repo is grep-friendly and chronological without deep nesting.

### D8 — Attribution convention for decision docs

**Raised by:** Human ("document what you said versus what I said; I think it's interesting anywhere you could say, 'Hey, I came up with this; the human input guided me this way,' even if the human input is wrong").
**Decision:** inline **Human:** and **Agent:** markers on decision rationale lines. Applied in this journal entry and in the revised plan doc. **Agent memory updated** (`feedback_decision_doc_attribution.md`) so future sessions continue the practice.

### D9 — Monolithic version tagging confirmed, with sharper Human rationale

**Agent initial reason:** single-axis figure, simpler to reason about.
**Human supplied the real reason:** "it is not clear that our final solution will have three prompts, and it is not clear that those three prompts will be adjudicator, extractor, and verifier. What we're optimizing is not three prompts but a system... you can't just smash [individual components from different versions] together because the entire system has changed." The structural-flexibility argument subsumes Agent's figure-simplicity argument. Per-subagent tagging would lock us into the current three-agent decomposition and prevent restructuring.
**Decision:** monolithic `paper-trail-v<N>` tags. Component-level ablation reconstructed from git diffs at paper-time, not from a parallel tagging scheme.

This is another who-said-what data point worth preserving: Agent had the right answer on weaker grounds; Human's reasoning was structurally deeper. For the paper's human-value retrospective.

### D10 — Eval arm as subdirectory with pre-commit hook (Option B) confirmed

**Human:** "the single clone is nice. To the extent that you feel comfortable with this subdirectory with a pre-commit hook, I don't quite know what that means, but conceptually, if you think that's functionally equivalent, I agree."
**Agent clarified:** a pre-commit hook is a script that runs before every `git commit` and can reject the commit if a condition isn't met (standard git feature). In our case: reject commits that modify `experiments/sarol-2024/eval-harness/` unless the commit is on a dedicated eval-arm maintenance branch. Functionally equivalent to physical separation for our purposes, at lower ceremony.
**Decision:** Option B. Subdirectory under `experiments/sarol-2024/eval-harness/` + pre-commit hook enforcement. Separate-repo option deferred unless later needs demand it.

### D11 — Headless Claude Code as the eval invocation path (Q9b), not direct SDK

**Agent initial lean:** direct Anthropic SDK from Python, on external-reproducibility grounds.
**Human pushback with strategic framing:** "this entire thing lives within Claude Code. They explicitly ship this as something that lives inside Claude Code... Claude Code-type environments will become the de facto OS operating system. The next version of Claude Code will not be Claude Code but Claude... I do not believe we need to build for a future where Claude Code is this weird thing and a restriction. The slash command we're building, paper trail, is the application. We're building an app called paper trail; it just lives as a slash command."
**Agent concession:** Human argument is stronger. External reproducers of paper-trail need Claude Code anyway; requiring it for eval is consistent with how the tool is actually used; SDK reimplementation has drift risk; future Claude Code successor will be ambient. Conceded.
**Decision:** headless Claude Code. Concrete architecture: build a dedicated experiment slash command (candidate name `/sarol-eval`) that takes a subset manifest and runs the full eval loop internally. Invoked non-interactively via `claude --print /sarol-eval --subset <manifest>.json`. The slash command's definition lives in the frozen eval arm; the paper-trail model under test is whatever the checked-out `paper-trail-v<N>` tag contains.

**Spawned Q9c (memory-blindness mechanism).** Open. Agent lean: alternate working directory with minimal `.claude/` config; verify empirically; fall back to temp profile-swap or container if it leaks. Needs a spike against Claude Code's memory-loading semantics.

### D12 — Document "Sarol tests only 3 of paper-trail's 7 arms"

**Human:** "We're not testing all of paper-trail; we are testing a subset of paper-trail because it is testable and you need quantifiable information. We can test the other arms later in experiment C, what we described yesterday."
**Decision:** paper honesty note in the archive-framework doc (added) and in paper-writeup-items.md (updated). Headline Sarol Variant A numbers cover phases 5–7 (extractor, adjudicator, verifier); phases 1–4 are bypassed because Sarol pre-provides staged inputs. End-to-end coverage comes via Variant C.

## Open questions carried forward

Numbered to match the plan doc.

- **Q1 — Monolithic vs per-subagent version tags.** Explained in more detail in the plan doc; Agent lean monolithic. Human's understanding check pending.
- **Q4 — Seeds per claim during iteration.** Agent lean single-seed + one-time triple-seed calibration on v1. Human not yet weighed in.
- **Q5 — When val is checked.** Agent lean: only at pre-registered gates. Human not yet weighed in.
- **Q6 — Eval-arm change protocol.** Agent lean: eval-arm bump invalidates, re-anchor at minimum v1 and the latest v\<N\>. Human not yet weighed in.
- **Q8 — What commit is `paper-trail-v1`?** Agent proposal: tag `experiment-plan` at the commit before smoketest findings shaped prompts. Human reacted openly ("probably just in your repo, which is maybe ugly"). Needs a specific SHA pick.
- **Q9 — Where does the eval arm live?** Human raised separate-repo (option C); Agent lean subdirectory-with-hook (option B). **Human decision pending and flagged.**
- **Q9b — How is paper-trail invoked during eval?** Direct Anthropic SDK from Python vs headless Claude Code memory-off. Open.

## Meta-observations for the paper retrospective

Two patterns worth noting from today that might generalize:

**Pattern 1.** Agent brought ML-community-standard priors (stratified sampling, acronym-heavy nomenclature, structured sandboxing frames). Human pushed back with plainer, more operationally defensible positions (random sampling is more defensible for overall-performance; plain language for readability; reframed memory isolation in terms of time-evolution rather than vector-by-vector). Both pushbacks improved the plan.

**Pattern 2.** Agent independently raised the existence of the INDIRECT-detection failure mode as the headline smoketest finding, and independently proposed the three-clause remedy. Human adopted but deferred the fix to first build infrastructure. The Agent's diagnostic + Human's infrastructure instinct complement each other: diagnosis generates the technical claim; infrastructure ensures the claim can be measured repeatably.

Hypothesis to test over subsequent revisions: Agent leans toward finding-and-remedying specific failures; Human leans toward building reusable measurement structure. Worth logging per-revision to see if this pattern holds.

## What to do next session

See `docs/plans/NEXT.md` for the living task list. As of end-of-day 2026-04-21, immediate ordering:

1. 45-min lit-review pass (DSPy/MIPROv2, TextGrad, OPRO, PromptBreeder, Reflexion follow-ups) — lock or unlock the train+val-curve novelty claim before committing engineering effort.
2. Memory-blind invocation spike (Q9c).
3. Pick `paper-trail-v1` commit (Q8 resolved in intent; just need the SHA).
4. Lock graduated-N eval-train manifests (N∈{10, 25, 50, 100, 200}).
5. Build the eval arm (`experiments/sarol-2024/eval-harness/` + `/sarol-eval` slash command + pre-commit hook + migrate orchestrator-runtime decisions into static Python).
6. First curve points: v1 and v2 on eval-train-10 (or -50).

### D13 — Graduated-N ramp-up adopted

**Human raised 2026-04-21:** "we ramp up our dataset size slowly for compute efficiency. And then only once we've reached the full train set size do we start building at a valence."
**Agent:** adopted the ramp; proposed ladder N ∈ {10, 25, 50, 100, 200, full=2,141}. Nested subsets (subset-50 ⊂ subset-100 ⊂ subset-200) so the same version can be compared across N levels.

### D14 — Q5 resolved: val is distinct from train via operational discipline (Agent insight, explicitly credited by Human)

**Human initial lean:** "to the extent that val is for hyperparameter optimization, we're already doing that with train, so it's not immediately clear that there's even a difference... I lean if they're not different."
**Agent counter:** val and train are the same distribution but differ in operational discipline — on train we look at per-claim failures (the optimization signal), on val we measure aggregate F1 only and never inspect per-claim failures (the overfitting signal). Without that discipline they are indeed equivalent; with it, val serves as the in-flight holdout check.
**Human response 2026-04-21:** "you're absolutely right. That's correct. The distinction is the per-claim. That's a good insight. **Note that that was your insight.** Otherwise, we end up overfitting on val, and we only get total score."
**Decision:** val = Sarol's actual dev split (316). Dev-50 sampled check at pre-registered gates (first structural change, every third revision, pre-lock). Per-claim dev failures are never inspected; only aggregate F1 consulted.

**This is the first case in our journal where Human explicitly asked Agent's contribution to be credited as a data point.** Worth preserving for the paper's retrospective on human-agent collaboration value. Emerging pattern to test: Agent sometimes surfaces operational distinctions that Human's intuition initially collapsed; Human's role is often to surface strategic arguments that Agent's initial lean underweighted (e.g., monolithic tagging's structural-flexibility reason, random sampling's defensibility reason, headless-Claude-Code's ambient-future reason). Complementary, not hierarchical.

### D19 — Three-tier measurement-invariant framework

**Human framing 2026-04-21:** "we cannot allow the model invocation to go off course, because that is something we are fixing. Same with seed, etc. There are these things that we keep fixed for measurement purposes, and then there are the things that we let the models or agents go off track... You need good prompts to keep them on track and good structure. So yeah, draw that line in the sand. And raise any other lines that we may need to draw along the same philosophy."
**Agent response:** formalized a three-tier classification — Tier 1 invariants (fixed + validated, violation invalidates the run), Tier 2 logged conditions (can't control, record for drift detection), Tier 3 free variables (prompt-driven, part of the system under test, must NOT be fixed). Enumerated specific Tier 1 invariants: paper-trail + eval-harness git tags, model aliases per role, eval subset manifest hash, prompt file hashes, eval-arm code hashes, benchmark + gold data hashes, memory-blind status, rubric variant declaration, environment variables, tool permissions, MCP servers connected.

**Agent also surfaced candidate invariants Human had not yet named:** tool permissions available to subagents, connected MCP servers, max tokens per subagent call, claim-subset manifest schema version, orchestrator-assigned slot-fill values (run_id / claim_id naming). Added to Tier 1 where mechanism is clear. Extended-thinking / temperature / top-p parameters and user-level global CLAUDE.md propagation flagged as Tier 2 pending Task 2 spike.

**Human refinement 2026-04-21 (later):** tools + MCP servers are NOT Tier 1 meta-invariants. They're inside the agentic system's design surface — a future paper-trail version might legitimately grant different subagent permissions or connect a new MCP. Part of the system, captured by the git tag, not a separate meta-invariant. **Agent updated** the framework: Tier 1 lists no longer include tool permissions or MCP servers; a new subsection "What Tier 1 deliberately does NOT include" explains the reasoning and notes the operational implication — commit any per-experiment `.claude/settings.json` / MCP config to the repo, don't let these live in user-global settings (else they leak out of the version tag).

**Decision:** `validate_run.py` in the eval arm checks Tier 1 pre-run, per-dispatch, and post-run; any Tier 1 violation invalidates the run before (or during) compute is spent. Full write-up in `experiment-sarol-archive-and-eval-framework.md` §"Measurement invariants and validation."

This exchange is a clean example of the collaboration pattern recorded in D14: Human articulated a methodological principle (invariants vs. free variables as a philosophical dividing line); Agent enumerated the specific instances and surfaced additional candidates Human hadn't named. Complementary; both contributions are load-bearing for the paper's methodology argument.

### D18 — Model pinning: alias-only, calendar-compressed; full-hash pinning deferred

**Human raised 2026-04-21:** "we need to version control the model... If Claude releases 4.8, we still use 4.7... paper-trail is deploying sub-agents, and there is a choice in what sub-agents it deploys. I think we want to try to freeze that choice."
**Agent surfaced constraint:** Claude Code's Agent tool accepts only `opus` / `sonnet` / `haiku` alias enum, not full model hashes. Fully reproducible pinning would require bypassing Claude Code (direct Anthropic SDK or open-source agentic framework).
**Human accepted the tradeoff:** "Claude code is just so much better... I don't want to run this experiment in [an open-source framework] yet, but that would be the more principled way to do it."
**Decision:**
- Pin all dispatches to `model: "opus"` alias (already the runbook convention). Pin orchestrator via `claude --model opus --print …`.
- Compress the experiment calendar to ~2 weeks from 2026-04-21 to minimize `opus` alias-drift exposure.
- Record Claude Code version in every archived `summary.json` as proxy for alias-drift detection.
- Disclose as paper limitations: alias-not-hash pinning, inference seed not lockable, invisible Anthropic backend changes to a fixed model ID.

Documented across: `experiment-sarol-runbook.md` §Model selection; `experiment-sarol-archive-and-eval-framework.md` §Model pinning; `paper-writeup-items.md` §Things to be honest about; `docs/plans/NEXT.md` §Invariants.

### D17 — "Seed" clarification: two different kinds

**Human 2026-04-21:** "I'm not quite sure what you mean by seed here. Is this what samples we are selecting?"
**Agent:** yes, I was conflating two different concepts:
- **Sample seed** — which claims get drawn into eval-train-N subsets. Makes the draw reproducible. Decision: fixed (seeded, committed, never redrawn; nested across N levels).
- **Inference seed** — LLM sampling at inference time (Opus 4.7 is non-deterministic). Multiple seeds per claim = multiple runs = CI on verdicts. Decision: single seed during iteration + triple-seed calibration on v1; multi-seed only at locked-candidate + test.

**Human lean aligned with Agent's decision on sample-fixed:** "you can really test whether your changes improve performance on those specific train data sets. You'll clearly overfit, but I think that's okay." Randomizing sampling during iteration deferred as future-work ablation.

### D15 — Paper-writeup-items cleanup: cross-ref faithfulness doc

Agent discovered during 2026-04-21 doc organization pass that `docs/plans/experiment-sarol-faithfulness.md` already formally documents the "Sarol tests 3 of 7 paper-trail arms" framing (phase-by-phase map, what's idealized, what's impaired). Paper-writeup-items.md now cross-references that doc as the source of truth rather than duplicating. Fresh-agent-readable.

### D16 — `docs/plans/NEXT.md` created as the living status doc

**Human request 2026-04-21:** "I want you to take another pass at reading all of our docs, not all of our docs, but just making sure that we have good organization so it's clear what we're working on next and in what context... we are going to run into context issues at some point. I want to make sure that each task has enough information, because the memory leakage one is crucial."
**Decision:** `docs/plans/NEXT.md` is always-current; fresh agents read it first per CLAUDE.md's reading path; each next-step task carries enough context to be picked up without re-reading the whole journal.
