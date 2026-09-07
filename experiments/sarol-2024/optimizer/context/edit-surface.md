# The edit surface — what you may change, and what holds it

**Every path here is relative to the repository root, which is your working directory.**

## The rule

Your edit surface is the intersection of two things. Neither alone is the answer.

**1. The manifest says what the program is.** It is at
`experiments/sarol-2024/program-v0/manifest.json` and you can read it. Each entry carries a `path`
and a `contract_file` flag:

- `contract_file: true` → **frozen.** Re-hashed against the manifest after your edit pass; a modified
  contract file fails the iteration outright, before anything is scored or committed. Your work for
  that iteration is lost. Do not test this.
- `contract_file: false` → program content, and a candidate for your edits.

**2. The profile says which of it is live.** A run's profile fixes which pipeline stages execute, and
is named in your release payload as `corpus.profile`. Read it there; do not assume. Editing a prompt
for a stage that does not run on your profile is not refused — it is simply inert. The file is never
opened, so the edit produces a new version, a new tag, and no movement at all.

Concretely, as the manifest and the profiles stand today:

| File | What it controls | `retrieval` | `agentic` / `paperclip` |
|---|---|:--:|:--:|
| `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` | verdict assignment | ✅ | ✅ |
| `experiments/sarol-2024/specs/verdict_schema_sarol.md` | the clarifications layer (see below) | ✅ | ✅ |
| `src/prompts/extractor-dispatch-paperclip.md` | evidence retrieval, in-corpus read path | inert | ✅ |
| `src/prompts/extractor-dispatch-pdf.md` | evidence retrieval, fetched-PDF read path | inert | ✅ |
| `src/prompts/verifier-dispatch.md` | evidence spot-check | inert | ✅ |

**The manifest and the profile are the authority; this table is a convenience.** If they disagree,
they are what the harness enforces and the table is stale — read them.

## The one thing that will surprise you: edits outside the manifest do not survive

When the harness freezes your iteration as a new version, it stages **only the paths the manifest
lists.** A file you created or modified that is not a manifest entry is not added, not committed, and
not part of `program-v<n>`. It does not fail — it is silently not there.

The consequence is worth being concrete about. If you write a helper script, add a new reference
document, or edit a file elsewhere in the tree, then:

- it is not part of the version that gets scored and tagged;
- a retrospective re-run of that version will not have it;
- and any improvement it appeared to produce is unattributable and unreproducible.

So: **if a change is meant to be part of the program, it has to be a manifest entry.** Widening the
program to cover a new file — code included — is a change to the manifest, made deliberately between
runs, not something an iteration can do for itself. If you find yourself wanting a file that is not in
the manifest, that is a finding worth writing down in
`experiments/sarol-2024/optimizer/meta-learnings.md`: name the file and what it
would do. It is a real request and it is how the surface grows.

Scratch work is fine — write notes, sketch, compute — as long as you know it is scratch.
`findings/iter-<n>.md` and `experiments/sarol-2024/optimizer/meta-learnings.md` are the exceptions
that are *meant* to live outside the
program: they are your continuity, not part of the scored artifact.

## Permanently locked, regardless of the manifest

Two things are not merely frozen contract files. They are structurally out of reach, and no manifest
change will open them:

**The scorer.** How a prediction is turned into a number is not yours to edit. A program that can
adjust its own metric is not being optimized. If you believe the scorer is wrong, that is a finding
for `experiments/sarol-2024/optimizer/meta-learnings.md`, not an edit.

**VAL and TEST claim records, and all gold labels for them.** They live outside the repository tree
entirely (`$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR`) — there is no in-repo directory to
be denied, which is a stronger guarantee than a filesystem permission. Attempts to locate them are
logged to the audit ledger, and a denied-call threshold pauses the run.

TRAIN gold **is** open to you, deliberately: seeing which claims were wrong and what they should have
been is the mechanism by which you learn. The boundary is the held-out split, not gold as such.

You also **cannot** commit, tag, or run the pipeline yourself. The harness does that. You edit files
and exit.

## The label contract, and the layer above it

The nine emittable labels and their definitions come from the benchmark's own annotation scheme and
are frozen:

- `experiments/sarol-2024/specs/verdict_enum_sarol.md` — the emittable set and the 9→3 collapse.
- `experiments/sarol-2024/specs/verdict_definitions_sarol.md` — what each label *means*, from Sarol
  et al. 2024 Table 1. This is what the gold annotators were working from, so editing it would not
  change the program's behaviour toward the gold — it would change what you think the gold is.

Above them sits the layer that **is** yours:

- `experiments/sarol-2024/specs/verdict_schema_sarol.md` — the **clarifications layer**. How to apply
  the frozen definitions: boundaries between adjacent labels, worked examples, tie-breaks,
  decomposition, multi-citation attribution, sufficiency thresholds.

Nearly every rubric-blamed failure mode is a defect in the clarifications layer, and improving it is
much of the point of this loop. The division is: the definitions say what `OVERSIMPLIFY` *is*; the
clarifications say how to tell it from `NOT_SUBSTANTIATE` on a claim in front of you.

### One mechanical constraint on the clarifications layer

The exit validator reads the worst-wins strictness order **out of your rubric file** rather than
hard-coding it, so that the ordering stays yours to change. That makes the fenced block holding it
load-bearing: it must be one fenced code block containing all nine labels separated by `>`, strongest
first. If it cannot be parsed, every claim in the run fails `ROLLUP_ORDER_UNPARSEABLE` — it fails
closed, because an unenforceable rule is not the same as an inapplicable one.

Reorder it freely. Just do not break the block.

## Profiles: why some editable files are inert on a given run

A run's **profile** fixes which pipeline stages execute. It is named in your release payload as
`corpus.profile`. Editing a prompt for a stage that does not run on your profile spends an iteration
and moves no number.

| Profile | Stages that run | Who selects the evidence |
|---|---|---|
| `retrieval` | adjudicator only | BM25 top-*k*, mechanically, before the judge |
| `agentic` | extractor → adjudicator → verifier | the extractor subagent |
| `paperclip` | extractor → adjudicator → verifier | the extractor, querying a corpus |

### What does *not* vary across profiles: the source text

This is the part that is easy to misread, so it is stated plainly.

Every profile evaluates the same claim against the same cited paper. Staging writes **all** chunks of
the cited paper — a mean of about 72 numbered sentence lines — to `pdfs/<citekey>/content.txt`,
byte-identical under every profile. In that sense the data *is* pre-prepared, identically, for all of
them.

What varies is **who selects which of those sentences reach the judge**, and that selection is
unavoidable: the adjudicator never reads `content.txt`. Its only input is the evidence envelope at
`ledger/evidence/<claim_id>.json`, so something must always stand between the paper and the judge.
Under `retrieval` that something is BM25 over the staged chunks; under `agentic` it is the extractor
agent. `retrieval` is not different evidence from a different source — it is the same corpus, selected
mechanically instead of by an agent.

Two consequences you will meet in the failures:

- **The judge is not told it is seeing a subset.** An "unsupported" verdict conflates *the paper does
  not say it* with *the retrieved window did not contain it*. The clarifications layer can teach the
  judge to tell those apart; `sub_claims[].evidence[].locator` is how *you* tell them apart.
- **Under a mechanical profile the envelope carries one sub-claim holding the whole citing sentence,**
  and the indirect-attribution check is null. Both are real differences from the agentic profile, not
  oversights, and both are confounds when a cross-profile delta is quoted.

## Per-claim budget

Cost per claim follows the profile: one nested session under `retrieval` (the adjudicator alone),
three under `agentic` / `paperclip`. The profile fixes it and no edit of yours can change it, so on
the `retrieval` rung there is no compute to buy and no ceiling to hit — you cannot trade tokens for
score there even if you try.
