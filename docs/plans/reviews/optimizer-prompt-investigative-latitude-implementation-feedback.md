Reference: docs/claude_ops.md

# Implementation Feedback: Plan A — Paper-verbatim reset and optimizer investigative latitude

**Reviewer:** fresh Claude Code subagent (no conversation context) · 2026-09-09 · branch diff 591eb02..HEAD
**Note:** Codex was the intended reviewer; it failed with "workspace is out of credits". This
same-model review is a deliberate, user-authorized substitute and is a WEAKER independence check.

## Verdict

**Revise before land.** The substance is right and independently verified: the P0 reset is exact,
both new gates are genuinely falsifiable, every Gate-B factual claim reproduces from the artifacts,
and all six suites hit the claimed numbers. But the change ships **four new false instrument
facts about its own artifact** — the exact defect class Step 6 exists to delete — and one of them is
baked into `verdict_definitions_sarol.md`, which this same change froze as a hashed manifest contract
file. Fix that one *before* the deferred final rehash or it costs a second re-freeze.

## Plan Coverage

| Slice / section | Status | Evidence: path:line | Notes |
|---|---|---|---|
| P0 step 1–2 — rubric reset from the `program-v0` blob, eight bullets only | **Done** | `experiments/sarol-2024/specs/verdict_schema_sarol.md:19-27` | `diff <(git show program-v0:…) …` shows *only* the definitions block plus "— house text" section-title markers. No other post-v0 clause survived. |
| P0 step 2 — eight definitions verbatim | **Done** | `scripts/check_paper_fidelity.py:26-45` | Char-compared the gate's `PAPER_DEFINITIONS` against findings §8a (the only in-repo record of the paper text): **8/8 identical**, whitespace-normalized. Gate then proves all three files carry them. |
| P0 step 3 — `INDIRECT_NOT_REVIEW` marked house | **Done** | `specs/verdict_schema_sarol.md:26`, `prompts/adjudicator-dispatch-sarol.md:36`, `specs/verdict_definitions_sarol.md:51-55` | Marker `(house definition — not in Table 1)` asserted by Gate A in all three. |
| P0 step 4 — re-apply EXACTLY ONE post-v0 clause | **Done** | `prompts/adjudicator-dispatch-sarol.md:94` | v0→591eb02 diff shows the removed accretion was the Gate 0–3 apparatus + over-strictness preamble; only the `"evidence": []` bullet was re-applied. |
| P0 step 5 — no other post-v0 clause retained | **Done** | (diff, above) | Judge-read corpus fell 4,475 → 1,948 words (−56%). |
| P0 manifest — generator before generated | **Done (order swapped, harmless)** | `scripts/freeze_program_v0.py:46-50`; `program-v0/manifest.json:71-79` | Bytes landed at `b20debd` *before* the FILESET edit at `e717397`; the hazard the plan names (a `--write` between) never occurred and the end state is consistent. |
| P0 manifest — recipe unchanged, idempotent | **Done** | `program-v0/manifest.json:16` | `freeze_program_v0.py --verify` → `OK: 9/9 vs source refs; combined_hash 8d8fe097b4ab reproduces`; tree clean after. |
| P0 — entry-count/scope assertions updated deliberately | **Done, tightened not loosened** | `optimizer/adapter.py:1668,1673-1677,1773`; `optimizer/profiles.py:261` | Two *new* positive assertions added (definitions file is a contract file; is NOT in `editable`). Scope tuples `JUDGE_SCOPE`/`ACQUISITION_SCOPE` untouched (`profiles.py:52,55`). |
| P0 — `materialize_smoke.py`, `run_baseline.py` | **Partial** | `scripts/materialize_smoke.py:17` | `run_baseline.py` carries no entry count (nothing owed). `materialize_smoke.py:129` is dynamic, but :17 still says "writes all 8 files". See H3. |
| Step 0 — gold is the objective | **Done (adapted — deviation 2)** | `optimizer/prompt/optimizer-instructions.md:11-37` | Adjudicated below. |
| Step 1 — ground blame in traces | **Done, strongest part of the change** | `optimizer-instructions.md:208-221`; `context/failure-mode-discovery.md:79-95`; `context/subagent-blame-brief.md:98-107,123-138` | The subagent brief makes the trace read **mandatory** with a required `evidence_cue` quote — an enforceable artifact, not just prose. Names `run_manifest.json` as the correct-answer-trace source per the plan's ⚠ caveat. |
| Step 1 — fourth remedy (delete competing guidance) | **Done** | `optimizer-instructions.md:248-253`; `failure-mode-discovery.md:88-95` | |
| Step 2 — three record surfaces, no-edit iteration = terminal stop | **Done** | `optimizer-instructions.md:288-315`; `findings/README.md:6-26,62-67` | Routing table present in both, in lockstep. Terminal-stop text names `EmptyCommitError` and the cost. |
| Step 3 — evidence surface stated honestly | **Done** | `context/edit-surface.md:215-236` | No capability claim it cannot honour; routes to Plan B. |
| Step 4 — trend framing + prediction record | **Done** | `optimizer-instructions.md:279-286,345-364` | `1/sqrt(n)` paragraph replaced by the measured scatter. |
| Step 4 — drop the 311-claim table | **Drifted** | `context/task-and-scoring.md:40,117-125` | Table kept and bracketed with warnings rather than replaced. See H1. |
| Step 5 — bundle freely, separably | **Done** | `optimizer-instructions.md:242-247` | |
| Step 6 — TRAIN-roster correction | **Done, verified** | `context/playbook.md:94-116` | |
| Step 6 — release verify-absence gate | **Done, verified** | `context/release-format.md:272-296,313-318` | |
| Step 6 — delete the false `meta-learnings` release note; preserve iter-1..5 | **Done** | `optimizer/meta-learnings.md:183-196,232-256` | Dated deletion records left in place, per D4. |
| Step 6 — artifact pointers | **Done** | `optimizer-instructions.md:331-341` | All five named. |
| P0 — engine SHA preflight | **Done (ancestry — deviation 3)** | `scripts/vm/run_hillclimb_vm.sh:57-81` | Adjudicated below. |
| Gate A (fidelity), Gate D (empty window) | **Done, both falsifiable** | `scripts/check_paper_fidelity.py`, `scripts/check_empty_window_regression.py` | Break-tested five ways; see Audit Trail. |
| Gate B (factual audit) | **Done — 6/6 claims reproduce** | (see Audit Trail) | Nothing shipped that I could not reproduce. |
| Doc-path gate | **Passes, and is live** | `optimizer/profiles.py:349-361,371-399,429-430` | Nine docs. Break-tested: injecting one bogus backticked `.md` drops profiles to 47/48. |
| Tracking (`docs/plans/README.md`, `NEXT.md`) | **Done at 591eb02** | `docs/plans/README.md:11,36`; `docs/plans/NEXT.md:12` | Already carries the row and pointer. `docs/journal/` correctly holds **14** entries. |

## Critical Drift

**C1 — A frozen manifest contract file states a falsehood about itself, and the falsehood is now
inside `combined_hash`.** HIGHEST SEVERITY, and time-sensitive.

- code: `experiments/sarol-2024/specs/verdict_definitions_sarol.md:3-4` — "It is an
  **optimizer-facing reference**, not part of the program. It is in no `program-v0` manifest entry
  and **the adjudicator never loads it**"
- reality: `experiments/sarol-2024/program-v0/manifest.json:71-79` — it **is** entry 8 of 9,
  `"contract_file": true`, `"freeze_policy": "committed"`, `sha256 4f54a6d8…`, and its bytes are
  folded into `combined_hash 8d8fe097…`.

The "adjudicator never loads it" half is still true. The manifest half was true at `b20debd` and was
falsified by the author's own `e717397`/`0f43ba9`. Because the file is now hashed, fixing this
sentence changes its `sha256`, the sarol `source_ref`, and the `combined_hash` — i.e. it forces a
re-freeze. The plan already defers one final rehash (driver FILESET, 10th entry). **Fold this fix
into that same rehash; do not land the tag first.**

The same claim is repeated in three more places, all in the optimizer's read path:
- `optimizer/prompt/optimizer-instructions.md:111` — "it is not in the manifest and not in the
  judge's context" (only the second half survives)
- `optimizer/README.md:86` — "`specs/verdict_definitions_sarol.md` is in **no** manifest entry"
- `optimizer/README.md:92` — "Not program (no manifest entry, nothing hashes it, the judge never
  sees it)" — directly contradicted by the same README's own table at :30, which this change edited
  to list the file under **Program, frozen**.

Plan, Step 6: *"Before relying on any claim in it about where a file is, what the harness wrote, or
how batches are drawn, verify it."* Shipping four fresh instances of that defect in the change that
installs the rule is the single thing most likely to teach the next optimizer session that the rule
is decorative.

**C2 — `optimizer/README.md:97-99` still says the reconciliation is owed.** "⚠ **One thing is still
owed on it:** the text is this repository's transcription of Sarol Table 1, not a verified verbatim
read … A one-time reconciliation against the paper is owed before anyone treats it as
frozen-from-source." This change performed that reconciliation and froze the file. Delete or invert.

**C3 — `optimizer/meta-learnings.md` contradicts itself within 30 lines, and it is injected reading
every iteration.**
- `:21-23` — "This file was reset on 2026-09-07 and is **deliberately empty of history**. That is not
  a bug and nothing is missing: **the next iteration to run is iteration 1**."
- `:53-176` — the same commit added five iterations of `Confirmed` / `Pending` / `Resolved
  baselines` / `Iteration log` entries.
- `:31` — "quoted against a **0.595** do-nothing floor", while `optimizer-instructions.md:72` in the
  same commit says "⚠ **Do not carry forward 0.595.**"

Separately, and worth the author's judgement rather than a mechanical fix: the `## Confirmed` section
now presents as *established, reusable heuristics* a set of conclusions drawn from (a) edits P0 has
just deleted from the program, and (b) single-iteration VAL deltas of 0.02–0.04 — all of them inside
the 0.06 same-program scatter this very change ships at `optimizer-instructions.md:347-351`. The
file's own header defines `Confirmed` as "moved the number in a predicted direction **and been seen
again**"; most of these were seen once. The plan asked for the iter-1..5 lessons to be *preserved*
(Step 6 ⚠), so deleting them would be wrong — but a dated caveat at the head of `## Confirmed`
("measured pre-reset, on a program that no longer exists, at step sizes inside the instrument's
scatter") is owed. Otherwise the change hands the next session exactly the false confidence it
diagnoses.

**H1 — `context/task-and-scoring.md` still states the wrong floor where an agent will read it
first.**
- `:40` — "**Compare it against 0.595, never against zero.**" — unchanged.
- `:119` — table row: `**primary_metric** (accuracy, 9-class) | **0.595** | **The objective. This is
  the floor to beat.**` — unchanged.
- corrections land at `:108-110` and `:129-140`, 70–100 lines later.

Plan Step 4: *"replacing the `1/sqrt(n)` paragraph **and the 311-claim calibration table** in
`context/task-and-scoring.md` (which describes an eval set six times larger than the one used)."*
The table was bracketed, not replaced. The `1/sqrt(n)` half was correctly handled (it lived in
`optimizer-instructions.md`, not here). At minimum `:40` must be rewritten to point at
`do_nothing_floor`, and the `:119` cell must stop calling 0.595 "the floor to beat". Note
`profiles.py:476` asserts the literal string `"0.595"` is present in `optimizer-instructions.md` —
the gate protects the string, so the warning-form at `:72` satisfies it; no gate change needed.

**H2 — Two of the nine standing docs point at a section heading that no longer exists.** The change
renamed *"The two records, and what goes in which"* → *"The three record surfaces, and what goes in
which"* (`optimizer-instructions.md:288`) and updated `findings/README.md:8-9`, but not:
- `optimizer/meta-learnings.md:11-13`
- `optimizer/context/playbook.md:124`

Both send the agent to a heading it will not find. The doc-path gate only resolves backticked `.md`
paths, not section titles, so nothing caught it.

**H3 — `profiles.py` docstring half-updated; stale hash and a live "8".**
`optimizer/profiles.py:16-19`: "`program-v0` stays **9** entries at ``combined_hash``
``**0a02710cbd88**`` … the engine's materializer still sees all **8** and ``commit_new_version()``
still stages all **8**." The count was bumped, the hash was not (`8d8fe097…` now) and the two "all 8"
clauses were not. `scripts/materialize_smoke.py:17` — "materialize() writes **all 8 files** from the
single tag SHA" — is the same miss, in a file the plan named in *Files to Modify*.

**H4 — The rubric contradicts itself on whether the eight definitions are editable.**
- `specs/verdict_schema_sarol.md:7` (inherited from v0, untouched): "**This file is the editable
  half** … Everything below — **class definitions and boundaries**, the worst-wins rollup order,
  multi-citation handling — **is optimizer-editable**."
- `specs/verdict_schema_sarol.md:13-16` (new): "**The eight class definitions below are the paper's
  own words** … **Do not paraphrase, narrow, or extend them.**"

Both are in the judge's *and* the optimizer's read path, six lines apart. This is the precise shape
the change's own new "fourth remedy" tells the agent to hunt for
(`optimizer-instructions.md:248-252`: "read every other passage in both files touching that label
boundary and ask whether they can all be true at once"). One-line fix at `:7`.

## Missing Pieces

Nothing in scope is missing beyond the doc corrections above. `materialize_smoke.py` was named in
*Files to Modify* and received no edit (H3) — its only owed change is the `:17` docstring, since
`:129` already reads `len(entries)`. `run_baseline.py:166` turned out to owe nothing; say so in the
readback so the next reviewer does not re-derive it.

## Contract Violations

- **C1** is the material one: a `contract_file=True` manifest entry whose self-description is false,
  with the falsehood hashed into the frozen `combined_hash`.
- **H4**: the rubric grants an editability the adapter selftest and `JUDGE_SCOPE` do not actually
  restrict — `verdict_schema_sarol.md` *is* in `JUDGE_SCOPE` (`profiles.py:52`), so an optimizer that
  believes `:7` and reworded a definition would pass `validate_against_manifest`, pass the freeze,
  and only trip `check_paper_fidelity.py` — which nothing runs (see T2). Prose is currently the only
  barrier between the optimizer and the reset it just paid for.

## Test Gaps

**T1 — Gate A is a denylist where the plan's Step A asks for an allowlist.** Verification Step A:
*"no clause present that is not either paper text, marked house text, or the re-applied
evidence-array rule."* `check_paper_fidelity.py` asserts (a) eight verbatim strings present, (b) the
house marker present, (c) six named retired substrings absent (`:60-68`), (d) the evidence-array
clause present. It cannot see a *new* clause. That is defensible going forward — P0 explicitly
licenses the optimizer to re-derive house text under measurement — but the docstring at `:8-10`
reads as though it enforces the allowlist. State the limit so a future reader does not over-trust it.
Second-order: the `HOUSE_MARKER` check (`:97-101`) is file-global, not adjacent to the class, and the
marker string carries a literal em-dash — a hyphen variant would fail confusingly.

**T2 — Neither gate is wired into anything.** `grep` finds `check_paper_fidelity` /
`check_empty_window_regression` referenced only in their own docstrings and one prose line
(`optimizer/README.md:43`). No suite, no `--selftest`, no preflight calls them. The natural home is
`scripts/vm/run_hillclimb_vm.sh`, which already fails closed on engine divergence at `:57-81` and
runs before any money is spent. Without that, the reset can be silently undone by the next optimizer
iteration and nothing notices until a human remembers to run a script. Combined with H4, this is the
one place where the change's guarantees are weaker than they read.

**T3 — Fixture incoherence.** `optimizer/fixtures/empty_window_sarol.json` mixes two unrelated
claims: `claim_text` / `sub_claims[0].text` are about prophylactic anticoagulation, while
`citekey: "hammernik2021"`, `attestation.phrasings_tried` ("fourfold acceleration diagnostic
quality", "acquisition time reduction all anatomies") and `remediation.suggested_edit` ("Narrow
'across all anatomies' to 'in knee and brain imaging'") are MRI-reconstruction residue from another
fixture. It also carries a `remediation` block under an `ACCURATE` verdict. The validator does not
care and the gate passes, but this is now a committed reference artifact that a future reader will
reason from.

**T4 — new directory not planned.** `optimizer/fixtures/` is a new dir; `claude_ops.md` (*Code
Quality Standards → File & Directory Placement*) asks that new dirs be named in the plan's *Files to
Modify* with a one-line rationale. The placement itself is fine.

## Defensible Deviations

**(1) Resetting the dispatch prompt's inline nine-class gloss as well — CORRECT, and the plan would
have failed without it.** Confirmed against the blobs: the v0→591eb02 diff shows the dispatch's own
bullet list carried all three divergences independently — `ACCURATE`: "evidence directly supports the
sub-claim"; `NOT_SUBSTANTIATE`: "partial support; key element missing from the source";
`OVERSIMPLIFY`: "source supports the claim in a narrower / more-qualified form … drops qualifiers".
Resetting only the rubric would have left the judge reading the corrected scheme and the inverted
gloss in one session, which is the opposite of the plan's goal. The plan's "eight class-definition
bullets" phrasing simply did not anticipate two copies.

*Does duplication create new drift risk?* Yes, and the mitigation is adequate for the definitions
themselves but not complete:
- **Adequate:** Gate A asserts the same eight verbatim strings in *both* judge-path files
  (`check_paper_fidelity.py:54-57`), so a one-sided reword fails. `adjudicator-dispatch-sarol.md:29-31`
  adds an explicit tie-break ("if this list and the rubric ever differ, the rubric wins and the drift
  is a defect to report").
- **Not covered:** the *surrounding* house text. Gate A does not compare the two files' routing
  notes, so the dispatch's house block (`:39-41`) and the rubric's house sections can diverge freely.
- **Not covered at all until T2 is fixed:** a guard nothing runs is not a guard.

One judgement call worth confirming: v0's `CONTRADICT` bullet carried "Requires a verbatim source
excerpt that opposes the claim" in *both* files, and it is now gone from both — while v0's MISQUOTE
and INDIRECT glosses were deliberately preserved as *House routing notes*
(`adjudicator-dispatch-sarol.md:39-41`). Dropping CONTRADICT's excerpt requirement follows the letter
of the plan ("replace only the eight bullets"), but the inconsistent treatment of three v0 house
clauses looks unintentional. Confirm it was a choice.

**(2) Rewriting Step 0's "Every class definition in the rubric is ours" — CORRECT, nothing lost.**
The plan's literal sentence would have been false one commit after P0, and would have installed
exactly the false-instrument-fact the same plan's Step 6 exists to delete. The shipped
paper-layer/house-layer split (`optimizer-instructions.md:15-25`) preserves the plan's actual claim
verbatim in substance — it explicitly says the paper definitions "are still only a hypothesis:
annotators applied the scheme, and how they applied it is what gold records" (`:20-22`) — and keeps
"Where a definition and gold disagree, the definition is what is wrong" (`:14-15`). The added
"do not 'improve' a paper definition by appending a test the paper does not make" (`:31-32`) is
strictly more actionable than the original.

"log it as a journal entry" → "log it in this iteration's findings entry" (`:34-36`) is not merely
permitted by D1, it is **required** by it: D1 rules that the optimizer never writes `docs/journal/`.
The plan's Step 0 draft predated its own decision. Correct.

Caveat: the deviation is right, but the file around it was not reconciled — see **H4**. Step 0 tells
the optimizer the eight definitions "are not yours to reword" while the rubric it will open says the
opposite at `verdict_schema_sarol.md:7`.

**(3) Ancestry instead of SHA equality in the runner preflight — SATISFIES THE PLAN'S INTENT; the
comment oversells it.** The plan says the runner "checks feature presence rather than the SHA" and
"adds a preflight assertion of that SHA". Equality would fail the instant anyone commits to the
engine, which defeats the runner's own documented reason for avoiding a pin. Ancestry is the right
shape, and it is verified working:

| checkout | HEAD | pin present | pin is ancestor | preflight |
|---|---|---|---|---|
| `~/engine-82f547d` | `82f547d` (detached) | yes | yes | PASSES |
| `~/code/agentic-label-opt` | `de07032` (`feat/isolation-docker-substrate`) | yes | **no** | **FAILS** |

Two corrections owed:
- The comment at `run_hillclimb_vm.sh:63-65` claims this makes "divergence loud". It does not, in
  general: a branch cut *from* 82f547d that later broke the adapter seam still has the pin as an
  ancestor and passes cleanly. What the check actually detects is "engine predates, or forked below,
  the declared-compatible commit". Say that.
- The readback states the sibling checkout "does **not** contain `82f547d`". It does — the object is
  in the shared object DB (`git cat-file -e` succeeds, so the script's *first* guard passes). What
  fails is `merge-base --is-ancestor`. The code is right; the readback's description is not.

Also note the pin lives only in the shell runner, so anything invoked directly (`--selftest`,
`run_baseline.py`) is unguarded. That matches what the plan asked for; flagging so it is a known
boundary rather than an assumption.

## Suggested Code Edits

Ordered by cost of deferring.

1. `specs/verdict_definitions_sarol.md:3-4` — replace "It is in no `program-v0` manifest entry and
   **the adjudicator never loads it**" with something like "It **is** a frozen `program-v0` manifest
   entry (`contract_file=True`), so the reconciled text cannot change without cutting a version — but
   **the adjudicator never loads it**; the judge reads the enum and the rubric, and nothing else."
   **Do this before the deferred final rehash**, so one re-freeze covers both this and the driver's
   10th FILESET entry.
2. `optimizer/prompt/optimizer-instructions.md:111` — drop "it is not in the manifest and".
3. `optimizer/README.md:86` and `:92` — same correction; `:97-99` — delete the "still owed" block
   (C2).
4. `optimizer/meta-learnings.md:21-23` — replace the "deliberately empty of history" status with the
   actual state (five iterations ran on 2026-09-09 against the pre-reset program; the ledger recut
   will mint `program-v1` again). `:31` — drop or qualify the 0.595 figure.
5. `optimizer/meta-learnings.md:53` — add a dated caveat heading `## Confirmed` per C3.
6. `context/task-and-scoring.md:40` and `:119` — point at `do_nothing_floor`; stop calling 0.595
   "the floor to beat".
7. `optimizer/meta-learnings.md:11-13` and `context/playbook.md:124` — update the section title to
   *"The three record surfaces, and what goes in which"*.
8. `optimizer/profiles.py:17-19` — `0a02710cbd88` → `8d8fe097b4ab`; "all 8" → "all 9" (×2).
   `scripts/materialize_smoke.py:17` — "all 8 files" → "all 9 files".
9. `specs/verdict_schema_sarol.md:7` — narrow "Everything below … class definitions and boundaries …
   is optimizer-editable" to exclude the eight paper definitions.
10. `scripts/vm/run_hillclimb_vm.sh` — add `check_paper_fidelity.py` and
    `check_empty_window_regression.py` to the preflight block (fail-closed, alongside the engine
    check at `:57-81`). This is the highest-leverage single edit in the list: it converts two
    correct-but-inert scripts into an actual barrier.
11. `scripts/vm/run_hillclimb_vm.sh:63-65` — soften the "divergence loud" claim per deviation (3).
12. `scripts/check_paper_fidelity.py:8-10` — state that the retired-clause list is a denylist and
    cannot detect new clauses.
13. `optimizer/fixtures/empty_window_sarol.json` — make the fixture internally coherent (T3).

## Questions For The Author

1. Was dropping v0's `CONTRADICT` "requires a verbatim source excerpt that opposes the claim" from
   *both* files intentional, given that MISQUOTE's and INDIRECT's v0 glosses were deliberately
   preserved as house routing notes?
2. Findings §8a is the only in-repo record of the paper's Table 1 text, and every downstream
   artifact — the two judge files, the frozen definitions file, and `check_paper_fidelity.py`'s
   `PAPER_DEFINITIONS` — was derived from it. I verified all four agree character-for-character with
   §8a, but §8a itself is a single unverified transcription of a PDF, and this repo has already
   shipped one wrong transcription of the same table. Was §8a independently double-read against
   `https://pmc.ncbi.nlm.nih.gov/articles/PMC11231046/`? The plan says the definitions "must be
   copied into this plan's implementation commit"; they were not (the plan's Goal quotes only three
   fragments, and §8a is git-ignored). Consider quoting all eight into the plan doc or the journal
   entry so the source of record survives the findings doc's retirement.
3. `docs/plans/README.md:11` says the plan was "approved 2026-09-09 at plan-sha `2f099e956d23`" while
   the plan header still reads `Status: Draft … Reviewed: No`. Pre-existing at 591eb02, not caused by
   this change, but it should be reconciled before `/land`.
4. Net word counts: the *judge-read* program shrank 4,475 → 1,948 (−56%), which is the plan's
   diagnosis correctly applied. The *optimizer-facing* corpus grew 15,838 → 21,159 (+34%), with
   `optimizer-instructions.md` alone at +52% (3,077 → 4,674). Almost all of it is corrective or
   makes a behaviour checkable (the mandatory trace quote, the verify-absence `ls`, the prediction
   record's named observable), so it is not the "1,716 words that bought nothing" mistake repeated —
   the plan's own point is that prose fails when the rule was already obeyed, and none of these
   rules existed before. But nothing measures whether the *optimizer* obeys its instructions either,
   and Gate E — the one probe that would test it — is deferred. Is there an intent to keep the
   corpus from growing again next round, or does `optimizer-instructions.md` need the same
   subtractive pass P0 just gave the rubric?

## Audit Trail

**Files inspected in full:** the plan; `docs/session/plan-a-implementation-readback.md`;
`scripts/check_paper_fidelity.py`; `scripts/check_empty_window_regression.py`;
`optimizer/fixtures/empty_window_sarol.json`; `specs/verdict_schema_sarol.md`;
`specs/verdict_definitions_sarol.md`; `prompts/adjudicator-dispatch-sarol.md`;
`program-v0/manifest.json`; the full branch diff `591eb02..HEAD` (21 files); the `program-v0` blobs of
both operative files; `optimizer/profiles.py:1-30,40-70,190-215,255-270,300-400,470-480`;
`optimizer/adapter.py:1660-1690,1765-1780`; `scripts/freeze_program_v0.py:38-52`;
`scripts/vm/run_hillclimb_vm.sh:40-85`; `engine/loop.py:370-395` (in `~/engine-82f547d`);
`optimizer/dispatcher.py:855-870,1090-1105`; `~/.paper-trail/runs/hillclimb-vm-2026-09-0{8,9}/`.

**Environment:** `~/.local/bin/python3.13`, `AGENTIC_LABEL_OPT=/home/philadamson/engine-82f547d`
(`rev-parse HEAD` = `82f547dac49394005781df62892d41d9b26dfb09`, the declared pin). Working tree
verified clean before and after every temporary edit; no git state was mutated.

**Suites — actual output (all match the readback):**

```
optimizer/adapter.py         152/152 passed
optimizer/dispatcher.py      114/114 passed
optimizer/sampling.py         50/50  passed
optimizer/validate_sarol.py   33/33  passed
optimizer/profiles.py         48/48  passed
optimizer/canary.py           24/24  passed
scripts/freeze_program_v0.py --verify
  -> OK: 9/9 vs source refs; combined_hash 8d8fe097b4ab reproduces   (tree clean after)
scripts/check_paper_fidelity.py         -> Gate A passed -- 40 checks.
scripts/check_empty_window_regression.py-> Gate D passed.
bash -n scripts/vm/run_hillclimb_vm.sh  -> OK
```

**Gate break-tests (each edit reverted from a `/tmp` copy; `git status --short` empty after):**

| # | Temporary edit | Result |
|---|---|---|
| 1 | Reword `ACCURATE` in the rubric to the v0 wording | Gate A FAILED, 2 findings: "ACCURATE is not the paper's verbatim text" + "retired clause is back — ACCURATE over-strictness" |
| 2 | Append "Narrower-in-source than claimed." to a dispatch bullet | Gate A FAILED: "retired clause is back — OVERSIMPLIFY append" |
| 3 | Delete the `"evidence": []` clause from the dispatch | Gate A FAILED ("re-applied evidence-array clause is missing") **and** Gate D FAILED (half 3) |
| 4 | Give the fixture a non-empty `evidence` list | Gate D FAILED: "fixture drift: … no longer carries an EMPTY evidence list" |
| 5 | Drop `"evidence"` from `validate_sarol.REQUIRED_SUB_CLAIM` | Gate D FAILED: "NEGATIVE CONTROL FAILED: an omitted `evidence` field was accepted, so this gate proves nothing" |
| 6 | Append a backticked non-existent `.md` path to `playbook.md` | `profiles.py --selftest` 47/48, FAIL on "every path the optimizer's docs cite resolves from the agent's cwd" |

Every half of every gate is falsifiable. This is above the bar; the gates are real.

**Gate B — independent reproduction of each shipped claim:**

| Claim | Shipped at | Reproduced |
|---|---|---|
| TRAIN rosters identical across all 5 iterations | `context/playbook.md:97-100` | ✅ `train/draw_history.json`: 5 iters × n=50, all sets equal, all 10 pairwise Jaccard = **1.0000** |
| Two `iter1-current` snapshots byte-identical, 8 files | `optimizer-instructions.md:348-351` | ✅ content hash of `runs/hillclimb-vm-2026-09-08/materialized/iter1-current` = `bc148ab8…` = `…-09-09/materialized/iter1-current`; 8 files each |
| Same VAL roster | same | ✅ `val/val_draw.json["0"]` identical, n=50, in both runs |
| VAL 0.48 vs 0.42 | same | ✅ via `sampling.gold_labels("dev")`, key `(row,bucket)`: 09-08 = **24/50 = 0.48**, 09-09 = **21/50 = 0.42** |
| 16 of 50 labels changed | same | ✅ exactly **16** |
| VAL gold ACCURATE 35/50 ⇒ floor 0.70 | `optimizer-instructions.md:70-73`, `task-and-scoring.md:129-133` | ✅ gold dist on the roster: ACCURATE 35, ETIQUETTE 6, CONTRADICT 4, NOT_SUBSTANTIATE 3, INDIRECT 1, IRRELEVANT 1 ⇒ **0.70** |
| "best program scored 0.62 — below its own floor" | `task-and-scoring.md:134-137` | ✅ `val/iter5-program-v5` = **31/50 = 0.62** on the same roster (and `program-v1` = 28/50 = 0.56, matching `run_summary.json`) |
| `trace_ref` present per mistake record | `optimizer-instructions.md:209-210`, `subagent-blame-brief.md:123-138` | ✅ **94/94** mistake records across i1–i5 carry `trace_ref`; **0** null |
| Releases written to `iter/<n>/release_{train,val}.json` | `release-format.md:278-283`, `meta-learnings.md:186-189` | ✅ `engine/loop.py:391-392` gated on `loop_ops`; `dispatcher.py:867` passes `LocalLoopOps(repo_root)`; **all 10 files present** under `~/paper-trail/iter/{1..5}/` |
| `docs/journal/` holds 14 entries | plan Step 2 | ✅ 14 |

**Zero shipped claims failed to reproduce.** Gate B is clean.

**Paper-fidelity chain, verified end to end:** parsed the eight definitions out of findings §8a and
compared them character-by-character (whitespace-normalized, bold markers stripped) against
`check_paper_fidelity.py:PAPER_DEFINITIONS` → **0 mismatches, 8/8**. Gate A then proves those exact
strings appear in `verdict_schema_sarol.md`, `adjudicator-dispatch-sarol.md`, and
`verdict_definitions_sarol.md`. The residual risk is §8a itself (see Question 2).

**Reset exactness:** `diff <(git show program-v0:…verdict_schema_sarol.md) …` returns only the
definitions block plus three "— house text" section-title suffixes. `diff` on the dispatch prompt
returns only the definitions block, the house routing note, and the one re-applied evidence-array
bullet. The `v0 → 591eb02` diff confirms what was discarded: the Gate 0–3 apparatus, the
over-strictness preamble, and the four amended enum glosses. **No post-v0 clause other than the
evidence-array rule survived.**

**Word-count measurements** (`git diff … | grep '^+' | wc -w`, and `wc -w` on both revisions):
judge-read program 4,475 → 1,948 words; optimizer corpus (the nine gate-covered docs) 15,838 →
21,159; `optimizer-instructions.md` 3,077 → 4,674; `meta-learnings.md` 628 → 2,782.

**Engine preflight predicates** tested directly against both checkouts (read-only `git` queries; the
sibling checkout was not touched) — table under Defensible Deviations (3).
