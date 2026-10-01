Run **one** frozen-program stage against **one** staged Sarol 2024 citation instance, non-interactively, and exit.

This is an **experiment instrument**, not a user-facing command. It is dispatched by
`experiments/sarol-2024/optimizer/adapter.py` (`SarolRunner._stage_command`) once per stage per
claim, as a nested headless session:

```
claude --dangerously-skip-permissions -p \
  "/sarol-eval-item --stage <stage> --claim <claim_id> --staging <dir> --spec-root <dir>" ...
```

Every number the optimizer ever sees is produced through this path. Treat deviation from the
letter of this file as a measurement error, not a style choice.

## Arguments

Parse them from `$ARGUMENTS`. All four are required; all are `--flag value` pairs; order is not
significant. There are no defaults and no positional forms.

Path values arrive **double-quoted** (`--staging "/abs/path"`). Strip the surrounding quotes before
use, and treat everything between them as one value — a path may legitimately contain spaces, and
splitting on whitespace would silently truncate it.

| Flag | Value |
|---|---|
| `--stage` | `extractor` \| `adjudicator` \| `verifier` — which frozen prompt to dispatch |
| `--claim` | the `claim_id`, e.g. `C042`. Opaque; it encodes nothing about split or gold |
| `--staging` | the staged working directory for this claim — the adjudicator prompt's `{{run_output_dir}}` |
| `--spec-root` | root of the **materialized** frozen program tree — the prompts' `{{spec_root}}` |

If a flag is missing, repeated, or carries an empty value, **abort** (see *Aborting*). Do not infer
a value, do not fall back to a default, and never ask the user anything — there is no user attached
to this session.

## Hard prohibitions

These exist because this session is the instrument. Violating any of them corrupts the measurement
rather than merely failing it.

- **Never ask a question.** No `AskUserQuestion`, no clarifying prose, no waiting. This session is
  spawned by a Python subprocess with no attached terminal.
- **Never read the source paper yourself** — not `pdfs/<citekey>/content.txt`, not `meta.json`,
  not `sections/`. Only the dispatched subagent reads what its own prompt entitles it to read.
- **Never read, and never look for, gold labels.** Gold lives outside the repo tree entirely
  (`$PAPER_TRAIL_GOLD_DIR`, default `~/.paper-trail/gold/`). Do not `ls` it, do not resolve it, do
  not mention it. `parse_verdict.py` is the only code allowed to touch it, at scoring time, in a
  different process.
- **Never write the stage's output file yourself.** Only the dispatched subagent writes it. An
  orchestrator-authored verdict is a fabricated data point.
- **Never repair, reformat, re-score, or "improve" the subagent's output.** If it is wrong, it is
  wrong — that is the signal the optimizer is being paid to see. `validate_sarol.py` owns the
  content rule and the Runner calls it after this session exits.
- **Never retry a stage.** One dispatch per invocation. A retry loop silently changes the sampling
  distribution and inflates cost against a per-call budget cap.
- **Never edit anything under `--spec-root`.** That tree is the frozen program, materialized
  read-only. Edits there would rewrite the program mid-measurement.
- **Do not read `CLAUDE.md`, `docs/`, `NEXT.md`, or any plan doc.** They describe the experiment
  and would leak framing into the run. Read only the files this file names.

## Stage: `adjudicator` — the Phase 1 path

The only stage implemented today. See *Stages not implemented* below for why.

### 1. Resolve and check inputs

Do this with a **single** `Bash` call that prints what you need. Resolve `--staging` and
`--spec-root` to absolute paths (relative values resolve against the session cwd, which is a real
checkout, not the materialized tree).

Abort if any of these is not true:

- `<staging>` exists and is a directory
- `<spec-root>` exists and is a directory
- `<staging>/staging_info.json` exists and parses as JSON
- `<staging>/ledger/evidence/<claim_id>.json` exists and parses as JSON
- `<spec-root>/experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md` exists
- `<spec-root>/experiments/sarol-2024/specs/verdict_enum_sarol.md` exists
- `<spec-root>/experiments/sarol-2024/specs/verdict_schema_sarol.md` exists

A missing evidence file gets its own message. Under the Phase 1 `retrieval` profile the envelope is
written before you are dispatched, by the mechanical BM25 producer
(`optimizer/evidence_producers.py`, plan C6.2) that `SarolRunner.run` calls for any profile whose
`evidence_producer` is not the extractor. So if it is absent, the producer failed or was never
invoked — the fault is upstream of this command. Abort with `EVIDENCE_MISSING` and say so, rather
than letting the next reader hunt for a bug here.

### 2. Collect the slot values

From `<staging>/ledger/evidence/<claim_id>.json`:

| Slot | Source field |
|---|---|
| `{{run_id}}` | `run_id` |
| `{{claim_text}}` | `claim_text` |
| `{{claim_type_hint.type}}` | `claim_type.type` |
| `{{claim_type_hint.confidence}}` | `claim_type.confidence` |

From `<staging>/staging_info.json`:

| Slot | Source field |
|---|---|
| `{{multi_cit_context}}` | `multi_cit_context` — `"single"` or `"grouped"` |

Directly from the arguments:

| Slot | Value |
|---|---|
| `{{claim_id}}` | `--claim` |
| `{{run_output_dir}}` | absolute `--staging` |
| `{{spec_root}}` | absolute `--spec-root` |

Two integrity checks, because a mismatch here means the batch and the staging tree have drifted
apart and every downstream number would be silently mis-joined:

- the evidence file's `claim_id` **must** equal `--claim` → else abort `CLAIM_ID_MISMATCH`
- the evidence file's `claim_text` **must** equal `staging_info.claim_text_normalized` → else abort
  `CLAIM_TEXT_MISMATCH`

If a slot's source field is absent or null, abort `SLOT_UNRESOLVED:<slot>`. Do not substitute a
placeholder, an empty string, or a guess: a silently-empty slot produces a plausible-looking
verdict formed on missing input, which is the worst available outcome.

### 3. Dispatch the frozen prompt to a subagent

Read `<spec-root>/experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md`. Take **only** the
text strictly between the `## Begin dispatch prompt` and `## End dispatch prompt` markers. The
preamble above the first marker and the `## Orchestrator notes` below the second are addressed to
you, not to the subagent; passing either one on changes the judge's context.

Substitute every `{{slot}}` with its value from step 2 — literal textual replacement, nothing else.
Do not reword, summarise, reorder, append to, or "clarify" the prompt body. It is a frozen manifest
entry (`combined_hash` covers it) and its exact bytes are the program under measurement.

Dispatch the filled text as the **entire** prompt of exactly one general-purpose subagent. Give it
no extra instructions, no context about the experiment, no mention of the optimizer, the rubric
variant's purpose, scoring, or that it is being evaluated.

The subagent writes `<staging>/ledger/claims/<claim_id>.json` itself, per its own output contract.

### 4. Verify and report

After the subagent returns, check with one `Bash` call that
`<staging>/ledger/claims/<claim_id>.json` exists and parses as JSON. That is the whole check.

**Do not validate its content.** Not the enum, not the rollup, not the required fields, and above
all do not fix any of them. `validate_sarol.py` is called by the Runner immediately after this
session exits and owns every one of those rules; a second opinion here can only disagree with the
validator of record.

Final message, one line, nothing else:

```
OK <absolute path to the verdict JSON> stage=adjudicator claim=<claim_id>
```

Then stop. Do not summarise, do not offer next steps, do not comment on the verdict.

## Stages not implemented: `extractor`, `verifier`

Recognised, deliberately not built. Abort with `STAGE_NOT_IMPLEMENTED` and this reason:

> Phase 1 (`retrieval` profile) runs the adjudicator alone — the evidence envelope is produced
> mechanically, so no extractor session runs. The `extractor` and `verifier` stages belong to the
> Phase 2 `agentic` profile (plan Part C6.1) and are not built.

You should not see this from a real run. `SarolRunner.run` dispatches `self.profile.stages`, which
is `("adjudicator",)` under `retrieval`, and `dispatcher.run_optimization` refuses any profile whose
stages are not in `profiles.IMPLEMENTED_STAGES` before spending anything. Reaching this abort means
one of those guards was bypassed — a Runner constructed with an `agentic` profile directly, say.

**Fix the caller, not this command.** Adding the two stages here would quietly run Phase 2 while the
manifest, the cost model and the release payload all still say Phase 1. When the extractor and
verifier paths are genuinely implemented here, widen `profiles.IMPLEMENTED_STAGES` in the same
change — that tuple is what makes `agentic` runnable.

## Aborting

On any abort: write a forensic sidecar, say one line, stop.

The sidecar is the only durable channel this session has. `headless_claude_invoke` keeps stdout
solely to parse cost from it and keeps stderr only when the process itself exits non-zero — which a
slash command cannot cause. So an abort that leaves no file behind is invisible to whoever reads
the run afterwards.

Write `<staging>/ledger/errors/<claim_id>__<stage>.json` (create parents; overwrite):

```json
{
  "claim_id": "<claim_id>",
  "stage": "<stage>",
  "code": "<ABORT_CODE>",
  "detail": "<one sentence, no gold, no paper text, no claim text>",
  "staging_dir": "<absolute>",
  "spec_root": "<absolute>"
}
```

If `--staging` itself is unusable, skip the sidecar — there is nowhere safe to write — and report
on stdout alone.

Then emit exactly one line and stop:

```
ABORT <ABORT_CODE> claim=<claim_id> stage=<stage> -- <one sentence>
```

Codes: `ARGS_INVALID`, `STAGING_MISSING`, `SPEC_ROOT_MISSING`, `STAGING_INFO_MISSING`,
`EVIDENCE_MISSING`, `PROMPT_MISSING`, `CLAIM_ID_MISMATCH`, `CLAIM_TEXT_MISMATCH`,
`SLOT_UNRESOLVED:<slot>`, `STAGE_NOT_IMPLEMENTED`, `VERDICT_NOT_WRITTEN`.

**Never write the verdict file on an abort.** A missing `ledger/claims/<claim_id>.json` is exactly
how the Runner learns this claim failed: `validate_file()` returns `UNREADABLE`, `validation.ok` is
false, and the claim is recorded `program_error`. An abort placeholder at that path would instead
be validated as a real verdict and scored as a real prediction.

## Why the exit code is not the failure channel

Worth stating once, because the Runner's `if res.exit_code != 0` reads as though it were.

A slash command cannot set the exit code of the `claude` process that hosts it. That code is
non-zero only for process-level failure — the wall-clock timeout (124), a `--max-budget-usd` stop,
a crash. Stage-level failure is carried entirely by the **absence of the verdict file**, which the
Runner's exit validation converts into `program_error`. The two channels are complementary and
neither substitutes for the other, which is why the rule above is *never* to write a placeholder.
