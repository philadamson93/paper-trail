Reference: docs/claude_ops.md

# Plan A — Paper-verbatim reset, canonical baseline recut, and optimizer investigative latitude

**Status: In progress** (2026-09-09; revised after Phil's HTML review round, then after the Codex review) · **Reviewed: Yes**
**Approved** 2026-09-09 at plan-sha256 `2f099e956d23…`, zero open questions (`docs/plans/README.md`
already recorded the approval; this header lagged it). **P0's definitions half, the
definitions-only manifest rehash, and Steps 0–6 are IMPLEMENTED** on branch
`feat/optimizer-prompt-latitude`. Step 7, the ledger recut, the canary re-pin and Gate E remain.
**Split from a single plan on Codex's recommendation** (feedback: `docs/plans/reviews/optimizer-prompt-investigative-latitude-feedback.md`, verdict *Blocked* on scope entanglement). This is **Plan A**; evidence-acquisition programmability moved to **Plan B**, `docs/plans/phase2-evidence-acquisition-programmability.md`.
**Findings this plan is built on:** `docs/session/2026-09-09-optimizer-loop-and-isolation-findings.md`
(git-ignored; read it first — §8 carries the Table 1 reconciliation that reshaped this plan).
**Sibling plan, queued next:** the isolation protocol (findings §4g).

## Goal

Two things, and the first is new since the last revision.

**1. Reset the rubric's class definitions to the paper's verbatim text, then re-cut the baseline.**
The owed reconciliation against Sarol Table 1 is now done (findings §8). Three of our class
definitions diverge from the paper, all by *our* additions, and all in the judge's read path:
- **NOT_SUBSTANTIATE** — we deleted the paper's leading precondition "the citation **is relevant to
  the content** of the reference article" and substituted "partial support but key element missing."
  Relevance *is* the paper's NS-vs-IRRELEVANT boundary. So v4/v5's entire "can you quote a passage
  supporting a specific element" apparatus is our invention, not the scheme. NS: 115 predictions,
  precision **0.17**.
- **OVERSIMPLIFY** — the paper stops at "oversimplified or overgeneralized." We appended
  "Narrower-in-source than claimed, or qualified-in-source but unqualified in claim." 45 predictions,
  **2 hits** (precision 0.04).
- **ACCURATE** — the paper says "consistent with an **evidence segment**"; we say "**directly
  supports** the claim as stated." Stricter than the source, and over-strictness is the loop's own
  documented modal error. ACCURATE→NS is the largest confusion cell, 36 of 226.

⚠ **These clauses were already present in `program-v0`** (verified via
`git show program-v0:experiments/sarol-2024/specs/verdict_schema_sarol.md`). They are not optimizer
accretion — the loop inherited them, so **"reset to v0" is not the fix.** All five iterations
hill-climbed on top of an inverted definition, which is the most parsimonious explanation for why the
two worst-precision classes are exactly the two we mis-transcribed.

**2. Make the optimizer able to investigate rather than only rewrite.** It never opened a judge
trace, so it diagnosed "the judge ignored my rule" where the traces show 92% compliance — and its
only remedy for that is more prose, which cannot help when the prose was already obeyed. It also
inherited three false claims about its own harness and had nowhere to file defects it correctly found
but could not fix by editing a prompt.

**The absolute target is gold** (Phil, 2026-09-09). Gold is broadly correct and the experiment is
about fitting to it. Class definitions are a *fitted hypothesis*, never an authority — we may log a
suspected-wrong label, but gold is not the suspect.

**Explicitly not in this plan:**
- **No one-edit-per-iteration rule.** The judging sweep (~$20) dominates the optimizer session (~$5),
  so forcing one edit per sweep multiplies the expensive thing to buy attribution of the cheap thing.
- **No hard noise-band veto.** A trend across iterations is signal even when each step is not.
- No objective change and no eval-set resize — the held-out metric sits below its own
  always-ACCURATE floor of 0.70 while the best program scored 0.62. That is the largest problem in the
  system and it is the next plan, because switching to macro-F1 at n=50 makes measurement *worse*
  (bootstrap SD 0.082 vs accuracy's 0.070).
- No judge-model swap. Trace evidence puts haiku at ~30–38% of current error; it ranks after the
  instrument work.

## Approach

A paper-verbatim reset, then seven prose changes. Two are factual corrections, five are capability
grants. Where a habit is better learned than mandated it ships as guidance and the loop derives the
rule into `meta-learnings.md`.

### Step 0 — Gold is the absolute target; definitions are a hypothesis
New opening section of `prompt/optimizer-instructions.md`:
> **Gold is the objective. Always target the gold labels.** The nine label *names* and the 9→3
> collapse come from the benchmark and are frozen. **Every class definition in the rubric is ours** —
> a hypothesis about what gold means, not an authority. Where a definition and gold disagree, the
> definition is wrong. You have full per-claim gold for the TRAIN batch: **derive the boundaries from
> how gold actually uses them** rather than reasoning from the words you inherited. If you believe a
> specific gold label is indefensible, log it as a journal entry — one label, with the evidence quote
> and your reasoning — and move on. Do not build rules around the belief that gold is wrong.

### Step P0 (pre-step) — Paper-verbatim reset and a re-cut canonical baseline

**Primary source, cited here so this step survives the findings doc's retirement:** Sarol MJ,
Schneider J, Kilicoglu H. "Assessing citation integrity in biomedical publications: corpus annotation
and NLP models." *Bioinformatics* 40(7):btae420, 2024. Definitions in **§2.2 / Table 1**. Open access:
`https://pmc.ncbi.nlm.nih.gov/articles/PMC11231046/`. Accessed 2026-09-09. The eight verbatim
definitions are reproduced in findings §8a and must be copied into this plan's implementation commit.

**Reset algorithm — exact, not "drop the accretion":**
1. Start from the **`program-v0` blobs** of both operative files
   (`git show program-v0:experiments/sarol-2024/specs/verdict_schema_sarol.md` and
   `…:prompts/adjudicator-dispatch-sarol.md`).
2. Replace **only** the eight class-definition bullets with the paper's verbatim text.
3. `INDIRECT_NOT_REVIEW` keeps a house definition, explicitly marked `(house definition — not in
   Table 1)`. It is real in the released gold data (25 occurrences in
   `~/.paper-trail/benchmarks/sarol-2024/claims-train.jsonl`, 9 in `claims-test.jsonl`).
4. **Re-apply exactly one post-v0 clause:** the `### Output contract` evidence-array rule
   (`prompts/adjudicator-dispatch-sarol.md:99` and `:107`), which the validator independently
   requires at `optimizer/validate_sarol.py:127`. It recovered 5 `MISSING_FIELD` failures and is the
   only statistically real gain of the whole run.
5. **No other post-v0 clause is retained.** Anything else that looks worth keeping must be re-derived
   by the optimizer under measurement, not carried over on intuition.

**Baseline ledger — re-cut `program-v0`, archive `v1`–`v5`** (Phil's ruling 2026-09-09; keeps the
engine's contiguous `program-v0..vN` convention, which `engine/versioning.py` and `engine/resume.py`
both assume — a `program-p0` prefix is not supported without engine changes):
- Archive the existing `program-v1`…`program-v5` tags (move to `archive/2026-09-09/program-vN` or
  delete) **and** retire their run ledger, so the next run's first commit mints `program-v1` again.
- Replace the `program-v0` tag with the reset baseline.
- ⚠ The old run summaries and materialized snapshots under `~/.paper-trail/runs/` reference the
  retired tags. State them as historical, not resumable; do not attempt `--resume` across the recut.

**Manifest / hash mechanics — `combined_hash` is over COMMITTED source refs, not working-tree bytes**
(`program-v0/manifest.json:15-16` carries the recipe; the generator is
`experiments/sarol-2024/scripts/freeze_program_v0.py`). Correct order, and it is not optional:
1. Edit the generator's **`FILESET`** (`freeze_program_v0.py:38`) to add the two new entries — the
   driver and the definitions file. **Generator before generated**, or a later `--write` silently
   drops them (`freeze_program_v0.py:83`, `:100`).
2. Commit the intended baseline bytes.
3. Advance `source_refs` to those commits, then regenerate every entry `sha256` and the
   `combined_hash` via the generator; verify write-then-verify idempotence.
4. Cut the `program-v0` tag on that commit and confirm `program-v0 verifies against its tag`.
5. **Re-pin the canary and make its provenance non-stale.** `canary-retrieval.json:2,:12` records a
   `program_combined_hash`, but `canary.py:115,:152,:295` keys on profile + requested model + split +
   `expected_verdict` only — the hash is provenance and is *not* validated. So "re-verify" is
   insufficient: re-pin under the new baseline (prefer `--repeat 3`) and **assert the recorded
   `program_combined_hash` equals the new manifest `combined_hash`.**
6. Update the selftests that assert manifest entry **counts and scopes** — `adapter.py:1668`, `:1682`,
   `:1767`, `profiles.py:261`, `:275` — plus `run_baseline.py:166` and `scripts/materialize_smoke.py`,
   and the VM runner's engine-feature preflight (`scripts/vm/run_hillclimb_vm.sh:42`).

**Engine contract:** `ManifestEntry(path, freeze_policy, content_hash, archive_ref, contract_file,
optional)` and `ProgramManifest(entries, combined_hash)` (`engine/schemas.py:92`, `:112`). Adding
committed entries is schema-compatible and the engine treats `combined_hash` as **opaque** — it does
not verify it, so our generator is the only guard. The adapter-owned `source`/`sha256` extras must
continue to be stripped (`adapter.py:188`). Engine pin: the run used
`agentic-label-opt @ 82f547dac49394005781df62892d41d9b26dfb09`, but `adapter.py:101`/`:117` resolve an
env-selected path and the VM runner checks feature presence rather than the SHA — this plan **declares
82f547d as the compatible engine** and adds a preflight assertion of that SHA.

### Step 1 — Ground blame in traces
Every mistake record carries `trace_ref`; the optimizer opened **zero** in five iterations. Trace
forensics measured 92% ordered-gate compliance with the forced-nuance artifact at 31/31, so four
iterations went to hardening rules already being followed — 1,716 added words for a VAL move inside
the scatter.

Add to `prompt/optimizer-instructions.md` where blame is assigned:
> **Before you attribute a failure to the judge not following the program, open the trace.** Every
> record in the mistake corpus carries `trace_ref` — the judge's full session. Read it. Two failures
> look identical in the label and need opposite fixes: the judge *ignored* a rule, or the judge
> *followed* it and the rule was wrong. If you cannot point to where in the trace the procedure was
> abandoned, it was not skipped — and restating the rule more forcefully cannot help, because it was
> already obeyed. Sample the traces of correct answers too: if the gates are being walked on the
> claims you get right, "skipped" is not your explanation for the ones you get wrong.

Mirror it in `context/failure-mode-discovery.md` and `context/subagent-blame-brief.md`, where the
`execution` blame category is defined — **the blame subagents are what actually read individual
failures, so the instruction lands there or nowhere** (Phil's point: instructions are owed to the
subagents the program agent spawns, not just the judge). Add a fourth remedy to the three additive
ones:
> **Fourth remedy — delete the competing guidance.** A rule that looks "skipped" is often a rule
> contradicted by earlier layers aimed at the same boundary. Before adding prose, read every other
> passage in both files touching that label boundary and ask whether they can all be true at once.
> Removing two of them is a valid edit, and a testable one.

### Step 2 — Journal entries instead of new report files (D1 resolved)
The loop diagnosed defects it could not act on and logged them as "deferred", spending its edit on the
second-best target. Rather than three new report files, the optimizer appends **dated entries to the
existing committed `docs/journal/`** — the convention paper-trail already uses (five entries) and
rad-eval mirrors (dated entries plus an `experiment-journal.md` index). `.gitignore` states the intent:
"The plan docs and `docs/journal/` are what get committed."

⚠ **A no-program-edit iteration is a TERMINAL STOP, not a silent continue** (Phil's ruling
2026-09-09; the engine can only do this today). `versioning.commit_new_version` stages only manifest
entries and raises `EmptyCommitError` when none changed; `loop.py:411` converts that to a terminal
`LoopStop`. `docs/journal/` is outside the manifest and the optimizer cannot commit. So:

> **Not every defect is a prompt defect.** When this iteration's highest-mass failure mode is not
> fixable by editing the program, **write your findings entry, state plainly that no program edit is
> warranted and why, and stop.** The run halts for human triage — that is a legitimate, reportable
> outcome, not a failure. Do not invent a cosmetic edit to keep the loop alive.

**Three record surfaces, mutually exclusive scopes** (Codex flagged that a third surface without a
routing rule duplicates the two that exist; `findings/README.md` is the authority to update in
lockstep):
| surface | scope | who writes | committed |
|---|---|---|---|
| `optimizer/findings/iter-N.md` | run-local per-iteration detail: metrics, blames, modes, edits, predictions | optimizer, every iteration | no (untracked today) |
| `optimizer/meta-learnings.md` | **verified reusable** optimization heuristics only — dated (D4) | optimizer, when a lesson generalizes | yes |
| `docs/journal/` | curated cross-run decisions and postmortems | **human or the landing process promotes**, not the optimizer per-defect | yes |

The optimizer therefore does **not** auto-create a journal entry per suspected defect — that would
duplicate `findings/` and bypass curation. Promotion into `docs/journal/` happens at landing.
Closest sister file for a promoted entry: `docs/journal/2026-09-03-first-optimization-attempt-postmortem.md`.

Dropped from the previous revision: `gold-disputes.md`, `scoring-quarantine.md`, `infra-defects.md`. Also corrected: `docs/journal/` holds **14** entries, not the five an earlier draft claimed.
Quarantine in particular did not earn a file — the harness already excludes `invalid_label` from the
denominator (iteration 5 scored 37/49, not 37/50).

### Step 3 — Name the evidence surface honestly (retrieval latitude moves to Plan B)
**Phil's ruling stands** — evidence acquisition is the optimizer's problem, and "the original paper-trail
literally had an agent just read the whole paper." The architecture already reflects that, and my
earlier draft of this step was **false about where the lever is**:
- `profiles.py:107-116` — the `retrieval` profile is `editable=JUDGE_SCOPE` with
  `evidence_producer="bm25"`, `selector="bm25-top20"`, `retrieval_k=20`. **BM25's fixity is a
  deliberate Phase-1 condition**, not an oversight: it isolates judgment from acquisition so Phase 1
  measures the adjudicator alone.
- `profiles.py:121-133` — the `agentic` profile is `editable=JUDGE_SCOPE + ACQUISITION_SCOPE` with
  `evidence_producer="extractor"`, `source_mode="pdf"`. **An extractor agent reading the staged paper
  is already the design**, and `ACQUISITION_SCOPE` (`profiles.py:55` — the extractor-pdf,
  extractor-paperclip and verifier prompts) is **already manifest-owned and already optimizer-editable.**
- ⚠ **But it cannot run today.** `profiles.py:59-61`: the driver "implements the Phase 1 adjudicator
  path and aborts `extractor` / `verifier` with `STAGE_NOT_IMPLEMENTED`, so a profile requiring them
  cannot complete a run however well-formed it is."

So the real blocker is driver stage coverage, **not** a missing retrieval-config schema. Codex proposed
introducing a versioned retrieval-condition schema (`query_strategy`, `k`, `ranker`, `bm25_k1`,
`bm25_b`); this plan **declines that fix** — it would engineer around a deliberate Phase-1 constraint
and duplicate a capability Phase 2 already grants by prompt.

**In Plan A**, Step 3 is prose only and makes no capability claim it cannot honour:
> **A thin evidence window is not automatically a ceiling.** Under the `retrieval` profile the window
> is a fixed experimental condition (BM25 top-20, one query) and is *not* yours to change — so ask
> whether the program can decide correctly *given* an incomplete window. That is program work and it
> is yours: the largest single error mode (~31% of misses, both directions) is window-silence read as
> paper-absence. When the window itself is the binding constraint, say so in your findings and name it
> as a Phase-2 question rather than working around it in the rubric.

**Everything else about retrieval — making Phase 2 runnable, the comparability rule, and the
programmable acquisition surface — is Plan B.**

### Step 4 — Trends, not single steps; and record the prediction
Trend framing, replacing the `1/sqrt(n)` paragraph and the 311-claim calibration table in
`context/task-and-scoring.md` (which describes an eval set six times larger than the one used):
> **The noise floor is measured, not derived.** Re-scoring an *unchanged* program has moved VAL by
> 0.06: a byte-identical program scored 0.48 and 0.42 on the same 50 claims, changing 16 of 50 labels.
> A single iteration's move is usually smaller than the instrument's own scatter. This does **not**
> make the metric useless — a trend across several iterations is real signal even when no single step
> is (v0→v5 is significant at p=0.021 while every individual step is not). Read direction off the
> trend across three or more iterations, and off per-class movement where support allows.
> **What a single sub-band step does not license is a reversal of direction:** if VAL fell by less
> than the scatter you have no information about that edit, not evidence against it. This loosens as
> TRAIN and VAL grow — check the current `n_total` rather than assuming.

Prediction record — a structured record, not a grading vocabulary:
> End each iteration with a **prediction record**: per edit, the class or boundary you expect to move,
> the direction, and the observable you will read next time (`per_class_f1_9way` entry, VAL trend, a
> specific claim_id's label). Next iteration resolve each as **held / did not hold / could not tell** —
> three outcomes. "Could not tell" is the honest answer when the class had too little support (check
> `support_9way`) or the move was inside the scatter. A prediction you can only half-grade was not
> specific enough; say so and write a sharper one.

### Step 5 — Bundle freely, but separably (guidance, not a gate)
> Make as many edits as the evidence supports. If two edits target *different* label boundaries,
> per-class movement attributes them for free — prefer that shape. If a bundle regresses, spend the
> next iteration isolating rather than adding. A repeat measurement of an unchanged program is also a
> legitimate iteration; it is the only thing that separates a real move from scatter.

### Step 6 — Verify inherited instrument facts (two factual corrections + a standing duty)
- `context/playbook.md:96-98` asserts "each iteration sees a different TRAIN batch". **False** —
  rosters are byte-identical across all five (Jaccard 1.000, `train/draw_history.json`). Fix the text;
  the real hazard is overfitting a fixed 50, not incomparability.
- `context/release-format.md`'s "When the release is not there at all" fallback institutionalises a
  bug fixed months ago. Keep the recipe, gate it: **verify absence first** — releases are at
  `iter/<n>/release_{train,val}.json` under the repo root, written before your session starts.
- `meta-learnings.md:183` ("no release files are written — this is now the norm") and the derived
  "Instrument:" notes: delete. ⚠ **Preserve the iter-1..5 rubric lessons** — that file is currently
  modified-uncommitted in the working tree.

> **`meta-learnings.md` was written by your predecessors and nothing checks it.** Before relying on
> any claim in it about where a file is, what the harness wrote, or how batches are drawn, verify it —
> one `ls` is cheaper than an iteration. If an inherited claim is false, **delete it and say you
> deleted it.** Lessons about the rubric and the judge belong in `meta-learnings.md`; observations
> about *this run's* harness belong in a dated `docs/journal/` entry and are never promoted.
> **Date every entry you add** (D4).

Plus the artifact pointers it never had: `trace_ref` per record;
`iter/<n>/release_{train,val}.json`; `run_summary.json` (every version's VAL scalar); per-iteration
`run_manifest.json` (per-claim cost, duration, status, and the verdict for all 50 — not just misses);
`train/draw_history.json`.

### Step 7 — Widen the editable surface SAFELY: split the driver, single definitions source
Phil's directive was to make the driver editable. Codex flagged that making the *whole* command
editable also makes measurement and isolation contracts editable — argument parsing, the gold and
source-paper prohibitions, one-dispatch/no-retry, stage topology, output ownership, abort semantics
(`.claude/commands/sarol-eval-item.md:15,:35,:48,:53,:123,:158`). An optimizer could raise its score
or cut cost by weakening those while staying inside its declared edit scope. That is a reward-hacking
surface, so the directive ships in its safe form:
- **Frozen shell (`contract_file=True`):** argument parsing and validation, the hard prohibitions
  (never read gold, never read the source paper yourself, never ask a question, never author the
  verdict), one dispatch with no retry, output ownership, and the abort codes.
- **Narrowly editable component (`contract_file=False`):** the dispatch/program content — which frozen
  prompt is handed to the nested session and how slots are filled.
- **Invariant tests run after every optimizer edit**, asserting: exactly one dispatch per claim, no
  retry, no gold or source-paper read, the orchestrator never writes the verdict, and stage/profile
  consistency. A profile's stage count and the budget/release claims are lies if these can drift.
- ⚠ **Coordination:** the queued isolation plan also rewrites this driver (harness-side prompt
  rendering, fail-closed on no-task). These branches are **not** independent. Isolation lands
  **first**; Plan A rebases onto it. Conflict owner: whoever lands isolation.

**`verdict_definitions_sarol.md` — one source of truth, not a second rubric.** The judge reads only
the enum and the rubric; the definitions file is explicitly not loaded. Making it *editable* while it
also duplicates the eight paper definitions creates either an inert file or a silently drifting second
authority. Resolution: the **rubric** is the single operative source of the definitions; the
definitions file keeps the **verbatim paper text plus provenance** as an optimizer-facing reference,
stays `contract_file=True` (frozen), and the rubric references it rather than re-deriving it. It does
*not* become optimizer-editable — which supersedes the earlier draft of this step.

## Files to Modify

**P0 — reset + baseline recut (do the generator before the generated):**
- `experiments/sarol-2024/scripts/freeze_program_v0.py` — `FILESET` (:38) gains the driver's editable
  component and the definitions file; write-then-verify idempotence (:83, :100).
- `experiments/sarol-2024/specs/verdict_schema_sarol.md` — the eight paper-verbatim definitions
  (replace lines 13–21 only); single operative source.
- `experiments/sarol-2024/specs/verdict_definitions_sarol.md` — verbatim paper text + provenance;
  stays frozen (`contract_file=True`).
- `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` — reset to the `program-v0` blob,
  re-applying only the `### Output contract` evidence-array clause (:99, :107).
- `experiments/sarol-2024/program-v0/manifest.json` — regenerated: `program_version`, `source_refs`
  (:2), per-entry `sha256`, `combined_hash` (:15–16), two new entries.
- `experiments/sarol-2024/optimizer/canary/canary-retrieval.json` — re-pin under the new baseline;
  recorded `program_combined_hash` (:2, :12) must equal the new manifest hash.
- Selftests asserting manifest counts/scopes: `optimizer/adapter.py` (:1668, :1682, :1767),
  `optimizer/profiles.py` (:261, :275).
- `experiments/sarol-2024/scripts/run_baseline.py` (:166), `scripts/materialize_smoke.py`,
  `scripts/vm/run_hillclimb_vm.sh` (:42 engine preflight — add the `82f547d` SHA assertion).
- `.claude/commands/sarol-eval-item.md` — split into frozen shell + narrow editable component (Step 7).

**Optimizer prose (Steps 0–6):**
- `optimizer/prompt/optimizer-instructions.md` — Steps 0, 1, 2, 3, 4, 5, 6 + artifact pointers.
- `optimizer/context/failure-mode-discovery.md`, `optimizer/context/subagent-blame-brief.md` — Step 1.
- `optimizer/context/playbook.md` — Step 6 TRAIN-roster correction.
- `optimizer/context/release-format.md` — Step 6 verify-absence gate.
- `optimizer/context/task-and-scoring.md` — Step 4 trend framing; drop the 311-claim table.
- `optimizer/context/edit-surface.md` — Step 3 (evidence surface stated honestly) and Step 7.
- `optimizer/meta-learnings.md` — Step 6 deletions; dated entries; reduced to reusable heuristics.
- `optimizer/findings/README.md` — the three-surface routing rule (Step 2), in lockstep.
- `optimizer/README.md` — record-keeping model and the widened/narrowed surfaces.
- ⚠ **Constraint on all doc edits:** `profiles.py` has a gate asserting every backticked `.md` path in
  the optimizer-facing docs resolves from repo root. Do not add unresolvable code-formatted paths.

**Tracking:** `docs/plans/README.md` (feature row), `docs/plans/NEXT.md` (pointer),
`docs/journal/2026-09-09-table-1-reconciliation.md` (NEW — promotes findings §8 into the committed
record; sister file `docs/journal/2026-09-03-first-optimization-attempt-postmortem.md`).

## Decisions (resolved — do not relitigate)
- **D1** — journal semantics: three mutually exclusive record surfaces (Step 2 table). The optimizer
  does not auto-write `docs/journal/`; promotion happens at landing.
- **D2** — evidence acquisition: Phil's ruling stands, but the lever is Phase 2's `ACQUISITION_SCOPE`,
  not a retrieval-config schema. **Moved to Plan B** (Step 3).
- **D3** — no mechanical instrument-fact preflight. Over-engineering.
- **D4** — date `meta-learnings.md` entries. Yes.
- **D6** — baseline ledger: re-cut `program-v0`, archive `v1`–`v5` (P0).
- **No-edit iteration** — a deliberate terminal stop for human triage; no engine change (Step 2).
- **Driver** — editable in its split form only; the contract-bearing shell stays frozen (Step 7).
- **Definitions file** — stays frozen; the rubric is the single operative source (Step 7).
- **D5 — ETIQUETTE gets no special or upfront testing** (Phil, 2026-09-09): "this is part of the
  experiment, we don't need any upfront or special testing of this." It is one class among nine; the
  optimizer meets it under measurement like any other. No targeted iteration is scheduled and no
  ETIQUETTE-specific verification is added. (Context, not an action: it is the paper's second most
  common label at 13.61% while our loop scores 0/51, and the released data encodes it as *absence* of
  an evidence segment — 8 labels in `claims-train.jsonl` against the paper's 417.)
- **Pre-existing offline-gate failure — accepted and named, not a prerequisite** (Claude's call,
  2026-09-09; Phil may override). `profiles.py --selftest` is **47/48**: the
  `_unresolvable_doc_paths` gate (`profiles.py:349`) trips on template placeholders (`iter-<n>.md`)
  and on README-relative paths, neither of which is a real defect. Gate C therefore measures against
  the **recorded** baseline below, not an imagined all-green one. Fix it in passing if cheap, since
  Plan A edits those docs anyway. (Codex also reported `sampling.py` at 48/50 — **wrong**; it is
  50/50 under both interpreters, its run was sandbox-restricted.)

## Open Questions

**None.** D1–D6, D5 and the offline-gate question are all resolved above; the comparability question
Codex raised was dropped by Phil (2026-09-09, "nope don't care about this at all") and is recorded in
Plan B. Nothing gates implementation.

## Verification

Prose plus a definitions reset, so verification is (i) fidelity to the paper, (ii) the recut is
mechanically sound, (iii) the next iteration behaves. Runs on this VM with
`~/.local/bin/python3.13` (default `python3` is 3.10 and this code needs ≥3.11).

**Step A — reconciliation fidelity.**
- *Expected:* all eight paper-defined classes match §2.2/Table 1 verbatim; `INDIRECT_NOT_REVIEW`
  marked `(house definition — not in Table 1)`; **no clause present that is not either paper text,
  marked house text, or the re-applied evidence-array rule.**
- *Stop:* any silent addition survives — that is the exact defect this reset removes.

**Step B — factual audit of every harness claim written into the docs.**
- *Expected:* both release files present; `draw_history.json` confirms identical rosters; `trace_ref`
  present per mistake record; the 0.48/0.42 replicate reproduces.
- *Stop:* any claim fails to reproduce; do not ship that sentence.
- ⚠ **Trace-sampling caveat:** `trace_ref` may legitimately be null, and the mistake corpus lists only
  errors — correct-answer traces come from the per-iteration `run_manifest.json`, not the corpus
  (`context/release-format.md:93,:154,:170`). Step 1's prose must name that artifact and a fallback.

**Step C — the recut is mechanically clean.**
- *Expected:* generator updated *before* the manifest; baseline bytes committed; `source_refs`
  advanced; `combined_hash` regenerated and write-then-verify idempotent; `program-v0` re-cut and
  verifying against its tag; `v1`–`v5` archived and the next run's first commit minting `program-v1`;
  canary re-pinned with `--repeat 3` **and** its recorded `program_combined_hash` equal to the manifest
  hash; the two new manifest entries materialize and are editable only under their intended profile.
- *Expected suite baseline (measured 2026-09-09, not assumed):* adapter 150/150, dispatcher 114/114,
  sampling **50/50**, validate_sarol 33/33, profiles **47/48** (one pre-existing doc-path failure),
  canary 24/24. Updating manifest entry counts will break the count/scope assertions listed in Files
  to Modify — change them deliberately and say so.
- *Stop:* the canary flips verdict, the recorded hash still mismatches, or any suite regresses **below
  that measured baseline**.

**Step D — offline regression before anything paid.**
- *Expected:* a one-claim **empty-window fixture** proves the `"evidence": []` rule survived the reset
  (validator `validate_sarol.py:127` accepts; a stripped variant fails). This is the only edit P0
  re-applies by hand, so it is the one most likely to be lost.
- *Stop:* the empty-window claim produces a `MISSING_FIELD`-class rejection.

**Step E — one live iteration as a behavioural probe (~$25), on the recut baseline.**
- *Expected:* the session (a) opens at least one `trace_ref`; (b) writes a prediction record with a
  named observable per edit; (c) either edits the program **or** states that no edit is warranted and
  halts (the terminal-stop path); (d) shows its check for any harness claim it repeats.
- *Stop:* it still reports "no release files were written" (Step 6 failed), or claims an execution skip
  with no trace quote (Step 1 failed).
- *Decision gate:* (a)–(c) present ⇒ proceed to the fresh run under the new measurement design once
  that plan lands. Any absent ⇒ one wording revision, re-probe once, then escalate.

**Not verified by this plan:** whether any of this raises held-out accuracy. It cannot be, at the
instrument's ±0.155 MDE, and the objective sits below its own 0.70 floor. Plan A buys a *correct
baseline* plus better reasoning; the measurement redesign makes outcome claims possible.

## Landing & cleanup

⚠ **`ff-only` to `main` is impossible from this base** and an earlier draft asserted it. Measured
2026-09-09: `main` is **not** an ancestor of `9309434`; the branch carries **162** commits `main` does
not, and `main` carries **40** the branch does not.

- **Integration target:** `sarol-optimizer-concurrent` is the live experiment line and stays the
  integration branch. Plan A lands **onto `sarol-optimizer-concurrent`**, not `main`.
- **Branch:** `feat/optimizer-prompt-latitude`, cut from the `sarol-optimizer-concurrent` tip
  (`9309434`), merged back with `--no-ff`.
- **Reconciling with `main` is out of scope for Plan A** and needs its own decision — 162 vs 40
  divergent commits is not a landing step, it is a project call. State it as owed; do not improvise.
- ⚠ **Dirty tree first:** the tip holds uncommitted work — `meta-learnings.md` modified plus five
  untracked `findings/iter-*.md` and three untracked plan/review docs. Commit or stash them
  **deliberately before cutting the branch**, and do not fold run artifacts into the baseline commit.
  Never `git reset --hard` — unstaged edits have no blob to restore.
- **Order:** the **isolation plan lands first** (it rewrites the same driver); Plan A rebases onto it.
  Plan B follows Plan A.
- **Landing gate:** Step A fidelity clean; Step B audit clean; Step C mechanically clean incl. canary
  hash equality; Step D empty-window regression green; Step E behaviours present; this Codex review's
  findings applied; `/read-plan` sign-off. D5 explicitly deferred, not blocking.
- **Cleanup on land:** prune branch and worktree; `Status: Completed`; `docs/plans/README.md` row;
  `docs/plans/NEXT.md` pointer; promote findings §8 into
  `docs/journal/2026-09-09-table-1-reconciliation.md`. Archive the `v1`–`v5` tags and mark the old run
  ledger historical. Retire the `docs/session/` findings doc only once Plan A, Plan B, and the
  isolation plan have all landed — it seeds all three.
