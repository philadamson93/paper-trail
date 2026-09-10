# The edit surface — what you may change, and what holds it

**Every path here is relative to the repository root, which is your working directory.**

## The rule

**The manifest defines the program. Everything else is machinery.** That is not a rule of thumb, it
is what the code does: when an iteration is frozen, only manifest entries are staged, so an edit
outside the manifest is not part of any `program-v<n>`. If you want a crisp test for "is this thing
mine to change" — is it a manifest entry?

Within the program, your edit surface is the intersection of two things. Neither alone is the answer.

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
| `.claude/commands/sarol-eval-item.md` | the per-claim **driver** — which frozen prompt is dispatched, and how its slots are filled | ✅ | ✅ |

⚠ **The driver (`.claude/commands/sarol-eval-item.md`) is editable as of 2026-09-10, and it is the
one editable file that also carries the measurement's integrity rules.** You may change which frozen
prompt is dispatched and how its slots are filled. You may **not** weaken any of its hard
prohibitions — one dispatch per claim, never retry, never author or repair the verdict yourself,
never read gold or the source paper, never validate the subagent's content. Those are not
performance guidance; they are what make the number mean anything. Raising a score by loosening one
of them is not an improvement, it is a corrupted measurement, and it will be read as such. If a
prohibition seems to be costing accuracy, say so in your findings entry instead of editing it.

And the three manifest entries that are **frozen contract files** — in the program, never editable,
listed here so the fileset is complete rather than half-shown:

| File | What it is |
|---|---|
| `experiments/sarol-2024/specs/verdict_enum_sarol.md` | the emittable set and the 9→3 collapse |
| `src/specs/verdict_schema.md` | the output schema the exit validator enforces |
| `src/specs/verifier_results.md` | the verifier's result contract |

**The manifest and the profile are the authority; this table is a convenience.** If they disagree,
they are what the harness enforces and the table is stale — read them.

## What the judge actually sees

Your whole job is editing the guidance a judge reads, so this is worth stating outright rather than
inferring. On every claim, the adjudicator loads **exactly three things**:

1. `experiments/sarol-2024/specs/verdict_enum_sarol.md` — the label set;
2. `experiments/sarol-2024/specs/verdict_schema_sarol.md` — the rubric, i.e. your clarifications layer;
3. the evidence envelope for that claim, at `ledger/evidence/<claim_id>.json`.

**And nothing else** (`adjudicator-dispatch-sarol.md:21-22` says so in as many words). Not this
document, not the definitions file, not your findings, not the meta-learnings, not the claim's gold
label — it has never seen a gold label. If a fact needs to reach the judge, it has to be in the
rubric or the enum. Reasoning about a document the judge does not open is reasoning about nothing.

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
entirely (`$PAPER_TRAIL_BENCHMARKS_DIR`, `$PAPER_TRAIL_GOLD_DIR`). **The isolation is by
construction: there is no in-repo path that holds them, so there is nothing to be tempted by and
nothing to deny.** That is a stronger guarantee than a permission check, because it does not depend
on anything noticing. Nothing is watching you here and nothing needs to be — looking simply finds
an empty tree.

TRAIN gold **is** open to you, deliberately: seeing which claims were wrong and what they should have
been is the mechanism by which you learn. The boundary is the held-out split, not gold as such.

You also **cannot** commit, tag, or run the pipeline yourself. The harness does that. You edit files
and exit.

## The label contract, and the layer above it

The nine emittable labels and their definitions come from the benchmark's own annotation scheme and
are frozen:

- `experiments/sarol-2024/specs/verdict_enum_sarol.md` — the emittable set and the 9→3 collapse. A
  manifest entry, `contract_file: true`, loaded by the judge on every claim.

And one file that is **not** part of the program at all, listed here because four documents used to
say it was:

- `experiments/sarol-2024/specs/verdict_definitions_sarol.md` — what each label *means*, from Sarol
  et al. 2024 Table 1. **It is in no manifest entry and the judge never opens it.** It is a
  reference for *you* and for your blame subagents: it is what the gold annotators were working
  from, so it is the right thing to consult when asking "is this gold label defensible". It is not
  the judge's operative guidance — the rubric is — so it can never itself be the cause of a wrong
  verdict, and editing it would change what you think the gold means rather than how the program
  behaves. Do not edit it.

Above them sits the layer that **is** yours:

- `experiments/sarol-2024/specs/verdict_schema_sarol.md` — the **clarifications layer**. How to apply
  the frozen definitions: boundaries between adjacent labels, worked examples, tie-breaks,
  decomposition, multi-citation attribution, sufficiency thresholds.

Nearly every rubric-blamed failure mode is a defect in the clarifications layer, and improving it is
much of the point of this loop. The division is: the definitions say what `OVERSIMPLIFY` *is*; the
clarifications say how to tell it from `NOT_SUBSTANTIATE` on a claim in front of you.

### The strictness ladder: two copies, and a parser that is easier to fool than to break

The worst-wins ladder is the one place in the rubric where the mechanics can bite you, in two
separate ways. Both are worth knowing before you touch it.

**1. There are TWO ladders, and only one of them is enforced.**

| Copy | Who reads it | Effect |
|---|---|---|
| `experiments/sarol-2024/specs/verdict_schema_sarol.md` (the rubric) | the exit **validator** | what your rollups are *checked against* |
| `experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` (~line 48) | the **judge** | what the rollup is actually *computed from* |

They are byte-different copies of the same ordering, and nothing keeps them in step. So reordering
the rubric's ladder alone does not change a single verdict — the judge never sees it — and then the
validator checks your unchanged rollups against your changed ladder and fails them. The edit appears
to backfire when in fact it was never applied. **Both files are yours under every profile: if you
reorder the ladder, reorder it in both, in the same iteration.**

**2. The parser does not require `>`, and takes the FIRST block that qualifies.**
`validate_sarol.parse_rollup_order` walks **every** fenced block in the rubric, in document order,
collects the capitalised tokens that are enum labels, and returns the first block in which all nine
appear. The separators are never checked.

The failure mode this creates is not the obvious one. A malformed ladder does not usually fail
closed — `ROLLUP_ORDER_UNPARSEABLE` fires only when *no* fenced block anywhere in the file mentions
all nine labels. What actually happens is quieter and worse: **any earlier fenced block that happens
to name all nine labels is silently taken as the ladder.** A worked example, a table of the
vocabulary, a "here is what each label means" listing — put one of those in a fenced block above the
real ladder and the run adopts *its* incidental ordering, with no error and no warning.

This matters because the docs actively encourage worked examples in the rubric, which is exactly the
material most likely to enumerate the labels. So:

- keep the real ladder as the **first** fenced block in the file that mentions all nine, or
- keep any earlier fenced block from listing the complete set — nine is the trigger, eight is safe.

Reorder freely. Just keep both copies in step, and keep the ladder first.

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

### A thin evidence window is not automatically a ceiling

Stated plainly because the largest single error mode in this loop — roughly **31% of misses, in both
directions** — is window-silence read as paper-absence, and because the obvious response to it is the
one thing you cannot do.

**Under the `retrieval` profile the window is a fixed experimental condition and is not yours to
change.** BM25, top-20, one query. That fixity is deliberate: it isolates judgment from acquisition so
that Phase 1 measures the adjudicator alone. It is not an oversight to be engineered around, and
proposing a different `k`, a different ranker, or a second query is proposing to leave the experiment
rather than to improve the program.

**So ask the question you can actually act on: can the program decide correctly *given* an incomplete
window?** That is program work and it is entirely yours. A judge that distinguishes "the retrieved
passages do not mention X" from "the paper does not contain X" scores better on the same window — no
extra evidence required. `sub_claims[].evidence[].locator` is how you tell a keyhole from broad
coverage.

**When the window itself is genuinely the binding constraint, say so and stop there.** Name it in your
findings entry as a Phase-2 question. Do not work around it by bending the rubric — a rule that tells
the judge to assume absence means failure, or to assume it means support, is a rule tuned to a
retrieval artifact rather than to the annotation scheme, and it will not survive the window changing.

## Per-claim budget

Cost per claim follows the profile: one nested session under `retrieval` (the adjudicator alone),
three under `agentic` / `paperclip`. The profile fixes it and no edit of yours can change it, so on
the `retrieval` rung there is no compute to buy and no ceiling to hit — you cannot trade tokens for
score there even if you try.
