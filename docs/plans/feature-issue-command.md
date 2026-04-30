# Feature plan — `/issue` slash command

**Status.** Plan-only. To-do for a separate feature branch (`feature/issue-command`, cut later when work begins). No code yet.

**Provenance.** Scoped 2026-04-29; full design discussion in `docs/journal/2026-04-29-pause-sarol-pivot-to-features.md`.

---

## Implementation surface (post-critic-review 2026-04-29)

Concrete edits-list and pinned design decisions surfaced by a fresh-eyes critic-agent review. Treat as authoritative over the more abstract prose below — several pointers in the earlier draft were factually wrong.

**Files to create:**

- NEW: `.claude/commands/issue.md` — the slash-command prompt. **Use `paper-trail.md` as the AskUserQuestion-pattern template, NOT `ground-claim.md`.** paper-trail.md has 11 AskUserQuestion invocations covering the canonical patterns (option-list presentation, post-action pause, run-discovery prompts) that `/issue` needs to mirror. ground-claim.md has only 1 AskUserQuestion reference and is not the right template for AskUserQuestion-driven flows.
- OPTIONAL: `.github/ISSUE_TEMPLATE/verdict-dispute.md` — does not exist today; `/issue` can self-generate the body content without it. Add only if it improves the GitHub-side issue-list ergonomics.

**Slash-command file conventions to honor:**

- **NO YAML frontmatter.** All commands in `.claude/commands/` start with a one-paragraph description, then `## Invocation forms` (or similar). Do not invent a frontmatter convention.
- **The prompt INSTRUCTS the agent to use AskUserQuestion** — the prompt is documentation of orchestrator behavior, not a literal interactive wizard. The flows described in this plan should be written as instructions like "Call `AskUserQuestion` with options A / B" rather than as live prompts.

**Run-discovery convention (corrected from earlier draft):**

- **Reader mode:** glob `paper-trail-*/` in cwd; if zero matches, AskUserQuestion for path; if multiple, AskUserQuestion to pick.
- **Author mode:** detect `claims_ledger.md` in cwd. **Author mode never produces a `paper-trail-*/` dir** (per `paper-trail.md` line 574: "Never write a `./paper-trail-*/` output-dir in author mode"). The per-claim verdicts live at `<project-root>/ledger/claims/<claim_id>.json`, not under any run subdirectory. The earlier draft's "verdict files live alongside in the project root" understated this.

**BibTeX source (filled in — was missing in earlier draft):**

- **Reader mode:** extract by citekey from `<run-dir>/refs.verified.bib` (Phase-1 post-CrossRef-enriched bib; canonical for the run). Fall back to `<run-dir>/refs.bib` (raw) if `refs.verified.bib` is absent.
- **Author mode:** extract by citekey from the project's `bib_files` (declared in `claims_ledger.md` YAML frontmatter as `bib_files`).

**JSON fields to extract for the issue body's `<details>` block** (earlier draft said "adjudicator reasoning" — this is not a single field; the actual fields are):

- `claim_text`
- `claim_type.type`
- `sub_claims[*].text`, `sub_claims[*].verdict`, `sub_claims[*].nuance`
- `attestation.closest_adjacent`
- `attestation.indirect_attribution_check`, `attestation.out_of_context_check` (when populated)
- `overall_verdict`
- `remediation.suggested_edit`

Do not dump the whole verdict JSON (often 100+ lines); pin to this list.

**Submission mechanics (corrected):**

- `gh issue create` has **NO `--dry-run` flag**. The earlier draft's smoke-test step was impossible. Replacement convention: render the assembled issue body to `.paper-trail/issue-preview-<claim_id>.md` and report the path. User `cat`s and visually verifies before sending. After verification, user re-invokes `/issue --submit` (or similar) to actually submit.
- Live submission: `gh issue create --repo philadamson93/paper-trail --label <bug|verdict-dispute> --title "<title>" --body-file <preview-path>`.
- **Issue title format** (corrected from earlier draft to drop em-dash per project style — see thesis style rules and the project's no-em-dash convention): `[verdict-dispute] <claim_id> against <citekey>: <one-line user reason>` (colon, not em-dash).

**Maintainer setup (one-time):**

- Create the GitHub labels: `gh label create bug --color FF0000 --description "Bug report"` and `gh label create verdict-dispute --color FFA500 --description "User disagreement with paper-trail's verdict"`.
- The `.github/` directory does not exist in the repo today; if `/issue` references issue templates, the directory needs to be created.

**`.paper-trail/issue-draft.json` schema** (pin field names so cross-implementation consistency):

```json
{
  "run_id": "<string>",
  "mode": "reader" | "author",
  "entries": [
    {
      "claim_id": "<string>",
      "citekey": "<string>",
      "kind": "bug" | "verdict-dispute",
      "user_reason": "<string>",
      "proposed_verdict": "<verdict-enum-or-null>",
      "assembled_body_path": "<path to rendered preview .md>",
      "submitted": false,
      "issue_url": null
    }
  ]
}
```

**Smoke-test fixture (corrected):**

- Reader-mode smoke: `examples/paper-trail-adamson-2025/data/claims/` (NOT `ledger/claims/` — the earlier draft was wrong about this path).
- Author-mode smoke: `examples/DFD_authormode/ledger/claims/` (this fixture uses the modern `ledger/claims/` layout).
- Verify the assembled issue body contains BibTeX + citing sentence + verdict JSON slice + user reasoning. Verify the preview file lands at the expected path; verify the local-draft `.paper-trail/issue-draft.json` accumulates entries correctly across multiple `/issue` invocations.

**.gitignore note:** the existing `/paper-trail-*/` pattern in the project's `.gitignore` is anchored and does NOT match `.paper-trail/` (leading dot, no trailing wildcard). The `/issue` implementation needs to add `.paper-trail/` to the project's `.gitignore` (or instruct the user to) so the local draft does not leak into commits.

---

## Codebase pointers

- **New slash command file:** `.claude/commands/issue.md`. Slash commands in this project live as markdown prompt files in `.claude/commands/`. Six existing commands. **Use `paper-trail.md` (the orchestrator) as the sister-template for AskUserQuestion patterns** — it has 11 AskUserQuestion invocations covering the canonical flows. (`ground-claim.md` is the closest match in size and surface area but has only one AskUserQuestion reference, so it is not the right model for this command's flows.)
- **Where runs live (for run discovery):**
  - **Reader mode:** output dirs at `<cwd>/paper-trail-<pdf-stem>/` (default location per `.claude/commands/paper-trail.md` Phase 0). Find recent runs by globbing `paper-trail-*/` in cwd or walking a user-specified path.
  - **Author mode:** the project's `claims_ledger.md` declares the run state in its YAML frontmatter (`pdf_dir`, `bib_files`). The per-claim verdict files live alongside in the project root.
- **Verdict structured truth:** `<run-dir>/ledger/claims/<claim_id>.json` — schema at `.claude/specs/verdict_schema.md`. Pull the relevant slice (claim_text, verdict, adjudicator reasoning) into the issue body's collapsible details block.
- **Local draft path:** `.paper-trail/issue-draft.json` in the audited project's working dir. Note: the existing `/paper-trail-*/` `.gitignore` pattern is anchored and does NOT match `.paper-trail/` (leading dot, no trailing wildcard match). The `/issue` implementation needs to add `.paper-trail/` to the project's `.gitignore` (or instruct the user to) so the draft does not leak into commits.
- **Submission tool:** `gh issue create --repo philadamson93/paper-trail --label <bug|verdict-dispute>`. Requires `gh` CLI authenticated.
- **Smoke test:** run /paper-trail against `examples/paper-trail-adamson-2025/` to produce a known set of verdicts, then invoke `/issue` and walk through the verdict-dispute flow on any one claim. Verify the assembled issue body contains BibTeX + citing sentence + verdict JSON slice + user reasoning. Use `gh issue create --dry-run` (or equivalent local-render check) before live submission during development.

---

## Goal

Give paper-trail users a structured, low-friction path to file GitHub issues against the paper-trail repo for two distinct cases:

1. **Bug reports** — paper-trail crashed, produced malformed output, or otherwise misbehaved.
2. **Verdict disputes** — paper-trail completed a run but the user disagrees with one or more verdicts. This is the higher-volume case and the one this command exists to capture cleanly, since today users would have to copy-paste the relevant context manually into a GitHub issue.

The verdict-dispute path is also a training-signal capture mechanism — examples of where paper-trail's judgment diverges from the user's are the most valuable feedback the project can collect.

## Two flows, one command

`/issue` opens an `AskUserQuestion` step asking "Bug report or verdict dispute?". The two flows then diverge:

### Bug-report flow

Standard issue-template prompts: what were you doing, what did you expect, what happened, OS / paper-trail version, attached log if available. Submitted as a GitHub issue with label `bug`. Out of scope for this plan to over-design — follow standard GitHub issue-template patterns.

### Verdict-dispute flow

This is the substantive flow. After the user picks "verdict dispute", `/issue` walks the user through a structured intake:

1. **Locate the run.** Either the user is invoking `/issue` immediately after a `/paper-trail` run (in which case the most-recent run is the default), or they pass a run identifier as an argument, or the command lists recent runs and asks. The run gives access to `ledger/claims/*.json`, the structured truth.
2. **Pick the disputed claims.** `AskUserQuestion` with a multi-select listing each claim from the run, showing claim text + verdict + reference. User picks one or more.
3. **Per-disputed-claim, ask why.** For each picked claim: free-text "Why do you disagree with this verdict?" Optional follow-up: "What verdict would you have given?" (multi-select from the verdict enum, plus "I don't know").
4. **Confirm and submit.** Show the user the assembled issue text(s) and ask whether to submit. Each disputed claim becomes its own issue (separate issues are cleaner for tracking, deduplication, and discussion than one mega-issue with N disputes).

`AskUserQuestion` is the right tool for the per-claim walk because it natively renders a multiple-choice picker; the user can move through their report quickly without typing identifiers.

## Issue payload structure

Each verdict-dispute issue submission contains:

**Always-included structured block:**

- **Cited reference, full BibTeX stanza.** Includes DOI, URL, title, authors, year — everything the maintainer needs to fetch the same source the user audited. One block, copy-pasteable.
- **Citing sentence.** The verbatim manuscript sentence that contains (or, if Feature 2 is live, was attributed to) the disputed claim's reference. One sentence — not the surrounding paragraph, not the section.
- **Paper-trail's extracted claim text and verdict.** A collapsible markdown `<details>` block containing the relevant slice of the run's `ledger/claims/<claim_id>.json` — claim_text, verdict, the adjudicator's reasoning. The structured JSON is more accurate and more reproducible than re-summarizing in prose.
- **User's disagreement reason.** Free-text from step 3 of the intake flow.

**Optional (offered during intake):**

- User's proposed correct verdict.
- Additional context (free text).
- Manuscript citation (if the user wants their work credited or linked).

**Never included:**

- The cited paper's PDF — copyright concern; posting copyrighted PDFs to a public GitHub issue is a TOS / legal risk and is not something paper-trail should automate.
- The full user manuscript — privacy concern; only the one citing sentence ships.
- Local file paths from the user's machine — useless for the maintainer and a small information leak.

## Submission mechanics

- **Target repo.** `philadamson93/paper-trail` (the same repo as paper-trail itself). Two labels distinguish flows: `bug` and `verdict-dispute`. Same-repo with labels was chosen over a separate user-feedback repo because (a) volume is hypothetical and addressable later via `gh repo transfer-issues` if needed, (b) one place for users to look beats two, (c) verdict-disputes are good public artifacts that make the tool's edge cases visible to the community.
- **Privacy warning before submission.** The intake's confirm-and-submit step explicitly tells the user: "This will post the citing sentence and your dispute reasoning publicly to the paper-trail GitHub repo. Continue?" The user can cancel and the local draft persists.
- **Submission via `gh issue create`.** The command depends on `gh` being authenticated. If `gh` is not set up, the command should detect that and surface a clear next-step message rather than crashing.

## Local draft mechanics

While the user is walking through a multi-claim review, the in-progress draft persists at `.paper-trail/issue-draft.json` in the audited project's working directory. Properties:

- **Gitignored.** The `/paper-trail-*/` pattern in the project's `.gitignore` already covers most paper-trail run artifacts; the draft path needs an explicit entry (`.paper-trail/issue-draft.json` or the broader `.paper-trail/`) so the draft does not accidentally leak into commits.
- **Structured JSON.** Each entry captures the claim_id, the user's selection, the user's reasoning, the proposed verdict, and the assembled markdown that will become the issue body. Structured so a session crash mid-review doesn't lose state.
- **Cleared on successful submit.** After all picked claims have been submitted as issues, the draft file is removed. If submission fails partway through, the unsubmitted entries persist for retry.

## Privacy considerations

The verdict-dispute flow publishes the citing sentence and the cited reference's bibliographic data to a public GitHub issue. Considerations the user should be aware of:

- **Manuscript privacy.** Users auditing unpublished or in-progress manuscripts may not want even one sentence quoted publicly. The confirm-before-submit warning addresses this; users can also cancel after seeing the assembled issue text.
- **Cited-paper exposure.** Posting "user audited Smith 2024" reveals the user's research interests. For most users this is fine (their bibliography is public anyway); for some it may not be. Same warning covers it.
- **Aggregation risk over time.** If a single user files many disputes, the corpus reveals their reading patterns. Worth a `paper-trail-bot` follow-up notification recommending users consolidate or use anonymized GitHub accounts if this becomes a real concern. Out of scope for v1.

## Open questions for implementation

1. **`gh` auth gating.** Detect missing `gh` setup and surface clear setup instructions vs silently failing. Worth defining the error UX before implementing.
2. **Run-discovery UX.** When the user invokes `/issue` without a run argument, the command needs to find the relevant run. Per the Codebase pointers section above, runs live at `<cwd>/paper-trail-<pdf-stem>/` in reader mode and alongside `claims_ledger.md` in author mode — there is no central registry. v1 behavior: glob `paper-trail-*/` in cwd; if zero matches, prompt for a path; if multiple, AskUserQuestion to pick. Author mode: detect `claims_ledger.md` in cwd and use that.
3. **Multi-claim batching vs one-at-a-time.** Each picked claim becomes a separate issue (per the plan above). Worth confirming this with first real users — some may prefer one consolidated issue. Easy to A/B at the confirm step if needed.
4. **Issue title format.** Probably `[verdict-dispute] <claim_id> against <citekey> — <one-line user reason>`. Pin the format in implementation; consistent titles make the issue list scannable.
5. **Bug-report flow specifics.** Largely follows standard GitHub issue templates, but worth checking whether paper-trail has a `.github/ISSUE_TEMPLATE/` directory to inform the prompt structure.

## Out of scope for v1

- **DOI-based deduplication** (machinery for "all disputes about Smith 2024" search). Hypothetical until dispute volume warrants it. Adding DOI in a parseable form to the issue body is cheap and leaves the door open.
- **Attaching PDFs to issues.** Copyright concern; never automate this.
- **Separate user-feedback repo.** Same repo with labels is the v1 design.
- **Public dispute-corpus aggregation / dashboard.** GitHub's issue search is sufficient until the corpus is large enough to warrant tooling.
- **Anonymized submission.** Users who want anonymity can use a throwaway GitHub account; paper-trail does not need to mediate.
