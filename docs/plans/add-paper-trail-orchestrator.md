Reference: docs/claude_ops.md

# `/paper-trail` — end-to-end audit of an input PDF (reader / reviewer mode)

## Context

All four existing paper-trail commands (`init-writing-tools`, `fetch-paper`, `ground-claim`, `verify-bib`) assume an *author* workflow: you have a manuscript (`.tex`) + `.bib` + PDF directory, and the tools verify your citations against those sources. There's no workflow for a *reader* or *peer reviewer* who wants to audit someone else's paper end-to-end.

This plan adds a `/paper-trail` orchestrator command that runs the existing suite against a single input PDF and produces a self-contained audit artifact. Motivating use cases: peer review, literature vetting, skeptical reading — you don't own the manuscript, you don't want to touch project-level config, and you want one artifact that tells you (a) which references look fabricated or chimeric and (b) which in-text claims aren't actually supported by their cited sources.

User has explicitly agreed the scope default is `full` (no sample mode — most refs have 1-2 claims so the cost is manageable once the source PDF is already open). User has flagged that bibliography-parser quality is a separate concern to test over time, and that a UX collaborator is handling interactive-prompt polish — so keep UX surfaces simple and swappable.

## Goal

A `/paper-trail` slash command that:
- Prompts the user (via `AskUserQuestion`) for input PDF path, output directory, mode (`full` | `single`), and institutional access.
- Extracts the input paper's reference list via (a) PDF bibliography parsing and (b) external lookup by DOI (PapersFlow / CrossRef / arXiv) for verification and enrichment.
- Writes a synthetic `.bib` to disk so existing `/verify-bib` and `/fetch-paper` logic runs unchanged.
- Invokes `/verify-bib` logic on the refs, parallelized in batches.
- Invokes `/fetch-paper` logic for each ref, parallelized in batches; surfaces paywalled list.
- Invokes `/ground-claim` logic per *source paper* (groups claims by citekey), parallelized in batches, following the existing "read each source PDF once" invariant.
- Writes a single self-contained audit artifact in `<output>/` following the existing `claims_ledger.md` schema, with an input-paper frontmatter block and a "Critical findings" header surfaced above the Summary table.
- Supports `single` mode: ground one claim the user describes in free text — LLM interprets the description semantically against the input PDF.
- Supports `--skip-paywalled`, `--sequential`, `--batch-size N`, `--skip=citekey1,citekey2,...`.

## Approach

### Reuse, don't reimplement
`/paper-trail` is an orchestrator. It invokes `/verify-bib`, `/fetch-paper`, `/ground-claim` semantics via subagents. It does not duplicate their per-entry / per-claim logic. It adds only:
1. Bibliography extraction from the input PDF (new).
2. Citation-marker → claim extraction from the input PDF body text (new).
3. Batching / agent-spawn orchestration (new).
4. Self-contained artifact layout independent of `/init-writing-tools` (new).

### Artifact layout
`<output-dir>/` (default `./paper-trail-<pdf-stem>/`, user-confirmable):
- `ledger.md` — reuses the `claims_ledger.md` schema (YAML frontmatter + Summary table + Details blocks + severity taxonomies). Adds an "Input paper" block in the frontmatter (title, authors, DOI, path) and a "Critical findings" header above the Summary table that surfaces CRITICAL bib entries + CONTRADICTED/UNSUPPORTED claims.
- `refs.bib` — synthetic bib built from parsed + looked-up references.
- `pdfs/` — fetched source PDFs, named `<citekey>.pdf`.
- `parse_report.md` — bibliography parser diagnostics (refs found, DOI hit rate, low-confidence entries, style auto-detected). Keeps parser-quality signal for iteration.

### Phase structure

**Phase 0 — Bibliography extraction.**
- Parse the "References" / "Bibliography" section of the input PDF. Handle the two most common styles in v1: numbered `[N]` and author-year. Flag other styles as low-confidence in `parse_report.md`.
- For each parsed entry: derive a citekey, extract DOI/arXiv ID/title/authors/year/venue where possible.
- Enrichment pass: for each parsed entry, attempt external lookup (PapersFlow MCP → CrossRef → arXiv) to confirm / fill in missing fields. Parallelize in batches.
- Emit `refs.bib` + `parse_report.md`.

**Phase 1 — Verify bib.** Spawn N subagents (batches of 10) each invoking `/verify-bib <citekey>` logic against the synthetic `refs.bib`. Aggregate results into the ledger's Critical-findings header.

**Phase 2 — Fetch PDFs.** Spawn N subagents (batches of 10) each invoking `/fetch-paper <citekey>` logic. Save to `<output-dir>/pdfs/<citekey>.pdf`. After all batches complete, print the paywalled / failed-retrieval list. If `--skip-paywalled` → mark those entries `NEEDS_PDF` and continue. Otherwise stop and let the user either drop PDFs into place manually or re-invoke with the flag.

**Phase 3 — Ground claims.**
- Claim extraction: scan input PDF body text (skip captions / appendices / references section) for inline citation markers — author-year `(Author et al., YYYY)`, numbered `[N]`, superscripts. Every marker-bearing sentence is a candidate claim; map each marker to its `refs.bib` citekey.
- Group claims by cited source paper (one source → one subagent reads that PDF once, handles all its claims).
- Spawn M subagents (batches of 10) each invoking `/ground-claim` per-claim workflow for one source paper's worth of claims.
- `NEEDS_PDF` refs → their claims are marked `PENDING` in the ledger, not grounded.

### `single` mode
- Phase 0 runs normally (needed to build `refs.bib`).
- Ask the user: "Describe the claim you want to ground" — free text.
- LLM reads the input PDF and semantically matches the description to sentence(s) + citation marker(s).
- Confirm matches with the user via `AskUserQuestion` before proceeding.
- Phases 1-3 run scoped to just the confirmed reference(s) — usually 1-2 refs total.

### Resumability
Re-running `/paper-trail` against the same `<output-dir>`:
- `refs.bib` present → skip Phase 0 extraction (ask before re-running).
- For each ref, PDF already in `pdfs/` → skip its fetch.
- Ledger entries with non-`PENDING` support level → skip re-grounding (unless `--recheck`, reusing existing `/ground-claim` semantics).
- `PENDING` + `NEEDS_PDF` entries → retry fetch + ground.

### Agent / batching topology
Three parallel batches (default batch size 10; override via `--batch-size N` or `--sequential`):
- Phase 1: one subagent per reference for bib verification.
- Phase 2: one subagent per reference for PDF fetch.
- Phase 3: one subagent per unique cited source paper for grounding.

`--skip=citekey1,...` excludes specific refs from Phases 2 and 3 (their entries become `NEEDS_PDF` / `PENDING` but are not retried). `--skip-paywalled` auto-applies this to anything Phase 2 couldn't fetch.

### Failure modes handled explicitly
- Input PDF has no extractable bibliography (image-only scan, non-standard format): emit structured error with guidance, don't crash.
- Input paper has no DOI: Phase 0 falls back to PDF-parse-only; per-ref enrichment still works individually.
- External lookup service unavailable: per-ref entry stays UNVERIFIED; flagged in ledger.
- Very large papers (>200 refs): Phase 0 prints ref count and asks for confirmation before spawning Phase 1/2/3 batches.

## Files to Create

- `.claude/commands/paper-trail.md` — the orchestrator command prompt (directive-style, ~200 lines in the `ground-claim.md` mold: invocation-forms, config, per-phase specification, resumability, triage-report format, "Do not" section).

## Files to Modify

- `README.md` — add a row to the commands table for `/paper-trail`; add 1-2 sentences framing reader/reviewer use case vs. existing author workflow.

## Files NOT to Touch Yet

- `templates/claims_ledger.md` — schema is reused verbatim; per-paper additions (input-paper frontmatter, critical-findings header) live in the command prompt, not the template. Only modify if we decide to share these with other commands later.
- `examples/` — defer a `paper-trail-example.md` until after we've run it against a real paper and can include a real (not placeholder) artifact. User has explicitly flagged parser-quality testing as a follow-up.
- `.claude/commands/init-writing-tools.md` — `/paper-trail` deliberately does not depend on init; don't cross-couple.

## Open Questions

- **PapersFlow vs CrossRef preference during Phase 0 enrichment**: the existing commands already prefer PapersFlow when available. `/paper-trail` should follow the same priority — worth confirming this is still desired in the orchestrator context.
- **Large-paper threshold**: 200 refs is a guess. Could be higher or lower. Tunable.

## Verification

No unit-test suite (per `docs/claude_ops.md`). Verification is end-to-end, against this test input:

**Test PDF:** `/Users/pmayankees/Documents/Stanford/RSL/Spielman_Lab/Papers/DMI/Deuterium_Metabolic_Imaging__DMI__for_3D_Mapping_of_Glucose_Metabolism_in_Humans_with_Central_Nervous_System_Lesions_at_3T.pdf.pdf` — one of the user's own published papers (MRM 2023, Adamson et al.), so ground-truth reference metadata is knowable and parser output can be checked against the real bibliography.

1. **Smoke run** — `/paper-trail` against the DMI paper. Expect:
   - `<output-dir>/refs.bib` with one entry per reference; DOI present where source has one.
   - `<output-dir>/parse_report.md` with an accuracy/coverage summary we can eyeball vs. a manual count.
   - `<output-dir>/ledger.md` with:
     - Input-paper frontmatter block populated.
     - "Critical findings" header present (even if empty).
     - Summary table with rows for every (claim, citekey) pair.
     - At least one `CONFIRMED` entry and at least one `NEEDS_PDF` or `PENDING` entry (if any refs were paywalled).
2. **Resumability check** — re-run on the same output-dir; confirm Phases 0–2 skip completed items and only `PENDING` entries are re-processed.
3. **Single mode** — `/paper-trail <same-pdf>` in single mode with a plausible claim description; confirm it locates the right sentence, matches the right citekey, and grounds only that source.
4. **Parser-quality review** — read `parse_report.md` and a sample of `refs.bib` entries; if accuracy < some-threshold, file a follow-up plan to strengthen Phase 0's PDF parser. Per user guidance, parser perfection is NOT a v1 blocker.

Pre-commit implementation-review agent (per `docs/claude_ops.md`) runs after implementation to check plan fidelity and that the `README.md` row was added.
