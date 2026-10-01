# 2026-04-29 — pause Sarol experiment, pivot to three product features

Decision-log entry capturing the 2026-04-29 session in which paper-trail's active work-direction shifted from the Sarol-2024 agentic-optimization experiment to three targeted feature improvements on paper-trail-the-tool, plus the start of community-feedback intake. Conventions: **Human:** / **Agent:** inline attribution per `feedback_decision_doc_attribution.md`.

---

## Pause decision

**Human 2026-04-29:** Wants to pause the Sarol-experiment / agentic-optimization work and instead make targeted feature improvements that have been on his mind, plus begin getting community feedback. The Sarol work is paused, not abandoned — `experimental-plan-of-record.md` (the in-progress consolidated plan-of-record draft from 2026-04-23) is preserved on the renamed `sarol` branch, ready for resumption.

**Agent:** Captured the three features (multi-citation joint verdict, neighbor-sentence claim attribution, GitHub-issues `/issue` slash command) as separate plan docs on `main`, with code branches to follow.

## Branch hygiene decisions

**Human 2026-04-29:** Wanted main to be Sarol-clean — the new feature work should not have any Sarol mentions or context cluttering it. Asked whether the existing Sarol work could be moved to its own branch and the relevant docs deleted from main.

**Agent:** Investigated the actual git state. Surprise finding — main was already nearly Sarol-free: only three plan docs (`add-paper-trail-orchestrator.md`, `author-mode-parity.md`, `blindspot-mitigations.md`), no `docs/journal/`, no `experiments/` subtree. All the Sarol work lived on `experiment-plan`, which was effectively the Sarol branch already. So the "scrub Sarol from main" step was simpler than expected — just rename `experiment-plan` to `sarol`, no `git rm` storm needed.

**Decisions captured:**

- **Branch rename.** `experiment-plan` → `sarol`. The branch's recent ten or so commits are all Sarol work; the name now matches the contents. Pushed to origin; remote `experiment-plan` deleted.
- **Plan docs land on main.** The three feature plan docs (`feature-multi-cite-joint-verdict.md`, `feature-neighbor-claim-attribution.md`, `feature-issue-command.md`) live on main as forward-looking to-do items. Code changes for each feature go on their own branch off main.
- **Two feature branches, not three.** Features 1 (joint verdicts) and 2 (neighbor attribution) share `feature/multi-cite-and-neighbor-claims` because they both touch the extractor and adjudicator and will likely co-evolve. Feature 3 (`/issue`) is on its own branch (`feature/issue-command`, to be cut when that work begins) since it is pure tooling.
- **Cherry-pick three items from sarol to main.** `paper-trail-product-backlog.md`, `.claude/skills/doc-split-check.md`, and the `.gitignore` carveout pattern for project-owned skills are generally useful and not Sarol-specific. Brought to main as commit `2a46e8e`. **Human:** *"yes option (a) all eslse sounds good!"*

## Feature 1 — multi-citation joint verdict

**Human 2026-04-29 (initial framing):** Wants better reconciliation and aggregation of sentences with multiple citations — should spin up agents per reference (today's behavior), but then have a gate that combines all N and reaches a verdict assessing them in their combination.

**Agent:** Grounded the question by reading the current paper-trail prompts and schema. Today's pipeline dispatches one extractor + adjudicator pair per `(claim, citekey)`; the extractor has limited sibling awareness via `co_cite_context.sibling_verdicts`, but the adjudicator never sees siblings' verdicts and there is no joint-verdict pass.

**Human 2026-04-29:** Raised the load-bearing epistemic question — when a sentence has 3 references, are they meant to be (a) independently sufficient (any one supports the claim, redundant citation), or (b) jointly necessary (together they support the claim, neither alone does)? This distinction matters because today's per-ref pipeline would falsely report all three as UNSUPPORTED in case (b).

**Agent:** Articulated four cases worth distinguishing — independent redundancy / joint support via premise decomposition / mixed (one carries the load) / truly unsupported. The premise-decomposition case is the high-value rescue.

**Decisions:**

- **Per-ref AND joint, both reported.** Don't replace per-ref verdicts with joint verdicts — the per-ref result tells the user which specific reference to drop or replace, which is information the joint verdict alone loses. **Human:** *"sounds good, should do individual + joint and report all."*
- **UI: asterisk pointer.** When a per-ref verdict is "not supported" but the joint verdict says supported, mark the per-ref row with an asterisk-style pointer ("not supported individually but supported jointly"). For the mixed case (3 refs, 2 support jointly, 1 doesn't support at all), the joint row explicitly names which refs participate. **Human:** *"if there's 3 refs, and 2 support jointly but 1 doesn't support at all that needs to be specified too. A bit tricky on the UI front but workable on the backend for the adjudicator imo so can come up with something defensible for UI in the plan but dont need to make it perfect yet."*
- **Render inline with existing per-claim ledger entries**, not in a separate "multi-citation" section. **Human:** *"should live inline with existing claims."*

Full plan: `docs/plans/feature-multi-cite-joint-verdict.md`.

## Feature 2 — neighbor-sentence claim attribution

**Human 2026-04-29 (initial framing):** Wants paper-trail to also do a better job looking at neighboring sentences to infer which sentence ALSO belongs in a claim about a given reference. Common pattern: an author writes a sentence with reference `[m]`, then in the next sentence makes another claim about `[m]` without re-citing. There are no strict rules; purely a judgment call.

**Agent:** Asked architectural-fork question — does this live in the extractor (extractor sees sliding window, emits multiple claims tagged to the same ref) or the adjudicator (adjudicator pulls in neighbor sentences as context for the explicitly-tagged claim)? Also asked window size and bidirectional-vs-forward-only.

**Human 2026-04-29:** Extractor-side; bidirectional. On window: ±1 sentence to start. On the case where the neighbor sentence itself has a different citation `[n]`, the call is to **skip** rather than try to cross-attribute — that scenario is reference-hygiene territory: *"if If sentence S+1 contains a new citation [n] but also seems to extend a claim about [m] that's a lot of inferring and should flag to the writer to better separate claims? That seems to be in the territory of reference hygeine, it should be obvious to the reader what reference is supporting what claim(s) within reason."*

**Decisions:**

- **Extractor-side, bidirectional, ±1 sentence window.**
- **Skip if the neighbor sentence has its own citation.** This is the load-bearing simplification — it cleanly separates "implicit attribution" from "ambiguous attribution"; the latter is the author's problem, not paper-trail's.
- **Schema field `claim_source: explicit | inferred_forward | inferred_backward`.** Adjudicator leans AMBIGUOUS more readily on inferred claims; report renderer visually distinguishes inferred from explicit claims so the user can sanity-check the attribution itself.

Full plan: `docs/plans/feature-neighbor-claim-attribution.md`.

## Feature 3 — `/issue` slash command

**Human 2026-04-29 (initial framing):** Wants a way to leverage GitHub issues for users to type `/issue` and submit either genuine bugs or — more commonly — when paper-trail made a mistake in its assessment of a claim. The verdict-dispute workflow should guide the user through `AskUserQuestion` to gauge which claims they disagree with, why, and what their answer would have been (optional). Saves to a structured local file; user submits when done. Should contain the actual claim plus a pointer to the original paper PDF.

**Agent:** Asked about target repo (same as paper-trail or separate), bug-vs-dispute split (one command branching, or two commands), what to include re: the paper (full PDF vs DOI vs bib entry — privacy and copyright concerns), and where the local draft lives.

**Human 2026-04-29 decisions:**

- **Same repo as paper-trail**, two labels (`bug`, `verdict-dispute`). Reasoning around volume / privacy / audience addressed via labels and an explicit privacy warning at submission, not by separate repos.
- **One command, AskUserQuestion branches at step 1** ("Bug report or verdict dispute?"). **Human:** *"Yes, open with bug report or verdict dispute."*
- **Never attach PDFs.** Cited paper PDF is not in the issue payload — copyright concern. **Human:** *"agree never attach PDF."*
- **Citing sentence only, not the manuscript.** Only the one sentence containing the disputed claim ships, not the surrounding paragraph. **Human:** *"agree only including citing sentence that contains the disputed claim."*
- **DOI-based deduplication is deferred.** Worth doing eventually if dispute volume warrants, but not in v1. **Human:** *"sure though seems like an edge case, I dont think ill have that many users that this will matter for the forseeable future, arent gonna need this for now."*
- **Issue body includes BibTeX stanza for the cited reference** (DOI / URL / title / authors / year), **citing sentence**, **paper-trail's claim + verdict + reasoning** (as a collapsible markdown details block from the run's `ledger/claims/<claim_id>.json` slice), and the **user's disagreement reason** plus optional proposed verdict.
- **Local draft at `.paper-trail/issue-draft.json`**, gitignored, cleared on successful submit.

Full plan: `docs/plans/feature-issue-command.md`.

## Process notes

- **One thing at a time, conceptually.** Per `feedback_one_thing_at_a_time.md` — the "one thing" for this session was the pivot itself (capturing the three features as plan docs and getting branch hygiene right). Code work for any of the three features is the next session's primary task.
- **First journal entry on main.** Main had no `docs/journal/` directory before this session; this entry creates it. Subsequent feature-design discussions and decisions land here, per the per-day-per-topic convention.
- **The leftover `experiments/` subtree in the working tree** (53 files of sarol smoketest predictions / staging artifacts left over from the branch switch — gitignored on sarol but not on main) is flagged for separate disposition. Untracked, no commit risk; choice is whether to add `/experiments/` to main's `.gitignore`, delete the working-tree files, or leave as-is.
