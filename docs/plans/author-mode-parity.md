Reference: docs/claude_ops.md

# Author mode — parity with reader mode

## Context

Reader mode (`/paper-trail <pdf>`) has been extensively tested against `examples/paper-trail-adamson-2025/` (the MRM paper) and is solid. Author mode (`/paper-trail --author`) hasn't been exercised end-to-end since the M1 rewrite, and the README / `paper-trail.md` still describe it as "writes to `claims_ledger.md`" — language that predates the JSON-first ledger format.

Before writing this plan I re-audited author mode. The picture is better than expected: `/ground-claim` already implements the modern architecture (per `.claude/commands/ground-claim.md`):

- ✅ `ledger/evidence/<claim_id>.json` (extractor, Pass 1)
- ✅ `ledger/claims/<claim_id>.json` (adjudicator, Pass 2 — source of truth)
- ✅ `ledger/verifications/<claim_id>__<sub_claim_id>.json` (verifier, Pass 3)
- ✅ Verdict schema enforcement per `.claude/specs/verdict_schema.md`
- ✅ Ambiguity triage

So architecturally, author mode is already at parity. The actual gaps are narrower, focused on the **pre-dispatch validator (Step 3.1.5)** and the **documentation surface**.

## Goal

Author mode runs end-to-end on a real `.tex` manuscript + `.bib` + source-PDF directory, produces `ledger/claims/<id>.json` entries that conform to the reader-mode schema, and the Tier 1 validator runs cleanly over the `.tex` manuscript text — flagging phantom claims / misattached citekeys just as it does in reader mode. Docs reflect this.

Success criteria:

1. `/paper-trail --author <mrm-adamson-2025.tex>` completes without `NO_PAPER_TEXT` flooding the validator.
2. Ledger JSONs conform to the same schema as the checked-in reader-mode run.
3. Claim counts + overall verdict distribution on the MRM `.tex` converge with the reader-mode run (same paper, same claims) within a small tolerance — a strong end-to-end regression signal.
4. README and `paper-trail.md` wording describe author mode accurately (JSON ledger, not flat `claims_ledger.md`).

## Current state — actual gaps

| Area | Reader mode | Author mode | Gap |
|---|---|---|---|
| Ledger format | `ledger/claims/<id>.json` + rendered `ledger.md` | Same (via `/ground-claim`) | **none** |
| 3-pass dispatch | Extractor / adjudicator / verifier | Same | **none** |
| Verdict schema | `.claude/specs/verdict_schema.md` | Same | **none** |
| Manuscript source | `paper.txt` (pdftotext of input PDF) | `.tex` at project root | **validator only knows paper.txt** |
| Validator (3.1.5) | Runs + flags work | `load_paper_text()` fails → every claim `NO_PAPER_TEXT` | **blocks dispatch in author mode** |
| `FRONT_MATTER_ANCHOR` | Applies (author block is ambiguous in pdftotext) | N/A — LaTeX `\author{…}` isn't ambiguous | **should be skipped for .tex** |
| `CITEKEY_MARKER_MISMATCH` | Looks for numeric refnums near anchor | Should look for `\cite{key}` near anchor | **logic is PDF-specific** |
| Docs | Accurate | Says "writes to `claims_ledger.md`", doesn't mention JSONs | **dated copy** |

## Testbed

Author mode and reader mode are for different users — the author of a paper works in `.tex`, a reviewer / reader works from a PDF. Having the same paper in both formats is unusual in practice and shouldn't be promoted as a normal workflow. Here, it's a **regression-test convenience**: the MRM paper (`Adamson et al. 2025`, *Magn Reson Med*) exists as both a checked-in reader-mode audit (`examples/paper-trail-adamson-2025/`) and as LaTeX on the user's machine. That pair is the ideal regression target:

- **Same manuscript, same bibliography, same sources.** Running `/paper-trail --author` on the `.tex` should produce ~87 claims (reader mode produced 87 after the re-grounding in commit `846bd0b`).
- **Convergence check.** For each claim key `(claim_text, citekey)` pair, compare verdicts reader vs. author. A high agreement rate validates that both modes really do implement the same audit.
- **Divergence diagnostic.** Where they disagree, the difference comes from manuscript-source fidelity (PDF parse noise vs. LaTeX text). The author-mode run should be *more* reliable where they disagree, because `.tex` text isn't corrupted by pdftotext.

The user has also mentioned thesis chapters as a second testbed — one of those gives a new manuscript (unaudited, real content) to catch issues the MRM regression doesn't.

Execution order: MRM `.tex` first (known-good reference), thesis chapter second (unknown content, real use).

## Phased implementation

### Phase 1 — Validator supports `.tex`

Scope: `.claude/scripts/validate_claims.py`.

1. Add `--manuscript-path <file>` CLI flag. Overrides the auto-detection.
2. Update `load_paper_text()` to a broader `load_manuscript_text()`:
   - If `--manuscript-path` given, read that file directly.
   - Else, search order:
     1. `run_dir / "paper.txt"` (reader mode)
     2. `run_dir / "input-paper.txt"` (reader-mode alternative)
     3. A single `*.tex` file at `run_dir` (author mode auto-detect; if multiple, require `--manuscript-path`).
   - Return `(text, kind)` where `kind ∈ {"pdftotext", "latex"}`.
3. Skip `FRONT_MATTER_ANCHOR` when `kind == "latex"`. LaTeX front-matter lives inside `\author{…}` / `\thanks{…}` and doesn't produce ambiguous digit sequences; the check is noise-only there.
4. Rewrite `CITEKEY_MARKER_MISMATCH` for LaTeX: when `kind == "latex"`, find `\cite{key1,key2}` / `\citep{…}` / `\citet{…}` occurrences within ±280 chars of the anchor, split on `,`, trim whitespace, compare against the claim's stored `citekey`. Keep the PDF-mode numeric-refnum check behind `kind == "pdftotext"`.
5. The existing `normalize()` already strips `\cite` / `\textit` / etc. so `TEXT_ANCHOR_MISSING` works for `.tex` out of the box. Verify with a small unit test using the MRM `.tex`.
6. Report header in `claim_extraction_report.md` notes the detected manuscript kind and path.

Risk: `.tex` with conditional `\input{…}` / `\include{…}` of sub-files. Deferred to Phase 1b if needed — initial pass reads the single `.tex` file as-is. If TEXT_ANCHOR_MISSING flags many claims whose text lives in an `\input`-ed sub-file, expand `\input{foo}` against `run_dir` relative paths.

### Phase 2 — Orchestrator passes manuscript path in author mode

Scope: `.claude/commands/paper-trail.md` Step 3.1.5.

Currently: `python3 .claude/scripts/validate_claims.py --run-dir <output-dir>`.

Update to: in author mode, pass `--manuscript-path <path/to/document.tex>` explicitly. Use the `.tex` path the orchestrator already has from the author-mode input-paper discovery step.

Author mode `run_dir` for the validator should be the project root (where `ledger/claims/` lives), not the non-existent `output-dir`.

### Phase 3 — Doc refresh

Scope: README, `docs/internals.md`, `docs/output.md`, `.claude/commands/paper-trail.md`.

1. **README "Run it" → Author mode.** Replace "Writes to `claims_ledger.md` at the project root — that's both the audit config (YAML frontmatter: `pdf_dir`, `bib_files`, institutional access) and the rendered ledger." with something accurate:

   > Writes per-claim verdicts to `ledger/claims/<id>.json` at the project root (source of truth), renders `claims_ledger.md` as the human-readable view, and reads its own config from `claims_ledger.md`'s YAML frontmatter (`pdf_dir`, `bib_files`, institutional access).

2. **`paper-trail.md` "Artifact layout (author mode)".** Same fix — the JSON layer is the source of truth; `claims_ledger.md` is both config and rendered view.

3. **`docs/output.md`.** Mention that the same `ledger/claims/<id>.json` + rendered markdown pair applies in both modes; the only difference is where it lands (`<output-dir>/` vs. project root) and what the markdown file is named (`ledger.md` vs `claims_ledger.md`).

4. **Phase-mapping table in `paper-trail.md`** already accurate; double-check "3.5 verifier" and "4 triage" rows and fix anything stale.

Workshop README headline copy per the memory rule before committing.

### Phase 4 — Regression: MRM LaTeX convergence check

Scope: ad-hoc test; no code artifact.

1. Run `/paper-trail --author path/to/mrm-adamson-2025.tex` with the user's institutional access configured.
2. After completion, compare `<project>/ledger/claims/*.json` against `examples/paper-trail-adamson-2025/data/claims/*.json`:
   - Claim count (expected ~87).
   - Per `(claim_text_hash, citekey)` pair: verdict match rate. Target ≥80%; anything lower is a signal that one of the modes is wrong.
   - `PENDING` / `NEEDS_PDF` overlap: should be identical if institutional access is the same across both runs.
3. Write a short `docs/plans/author-mode-parity-mrm-results.md` capturing the comparison.

Do **not** overwrite the checked-in reader-mode example. Author-mode run writes into the LaTeX project root, not into `examples/`.

### Phase 5 — Thesis chapter shakeout

Scope: second testbed.

Run `/paper-trail --author path/to/chapter.tex` on one of the user's thesis chapters (unaudited real content). Look for:

- Validator flags that fire on legit claims (false positives in `.tex` handling).
- `\cite{…}` forms the updated `CITEKEY_MARKER_MISMATCH` logic doesn't recognize (`\citeauthor`, `\citeyear`, natbib variants).
- Phase 2 fetch behavior on a bibliography that wasn't optimized for paper-trail.

Capture findings in a follow-up plan doc or direct bug-fix PRs.

## Out of scope

- **Migration of pre-existing flat `claims_ledger.md` ledgers.** There don't seem to be any in the wild (author mode hasn't been exercised). If we ever find one, write a one-time migration that parses the flat `.md` Details blocks into `ledger/claims/*.json`. Don't build this speculatively.
- **LaTeX `\input`/`\include` expansion.** Phase 1 handles the single-file case. Deferred until the MRM / thesis runs surface it as a real problem.
- **Parallelism within author mode.** Per memory ("serial-first, then parallel once robust"), run serial first; revisit batching only after the MRM convergence check passes.

## Risks

- **LaTeX citation variants.** `\citep` / `\citet` / `\citeauthor` / `\citeyear` / natbib / biblatex — the regex set in the updated `CITEKEY_MARKER_MISMATCH` needs to cover the common ones. Pilot: `\cite`, `\citep`, `\citet`, `\citeauthor`, `\citeyear{…}`; expand from testbed evidence.
- **Multi-cite expansion.** `\cite{a,b,c}` is one call but three citekeys. The claim is one-per-`(sentence, citekey)` tuple (reader-mode semantics carry over via `/ground-claim` bulk mode), so this is already handled upstream — just make sure the validator's proximity check recognizes all three.
- **Verdict convergence threshold.** I've set 80% as the target. If actual convergence is much lower, likely causes: (a) the LaTeX extractor sees a different sentence boundary than the pdftotext one; (b) parser produced a different claim_text. Treat low convergence as a diagnostic, not a failure.
- **`\input`/`\include`.** Explicitly deferred — log and decide.

## Open questions

1. **Manuscript path priority when both `paper.txt` and `*.tex` exist.** Unlikely in practice (author mode doesn't produce `paper.txt`, reader mode doesn't produce `.tex`), but if both exist, prefer the explicit `--manuscript-path` and otherwise default to `paper.txt` for backward-compat with reader mode.
2. **Should `claims_ledger.md` be renamed to `ledger.md` for cross-mode consistency?** Possibly in a future cleanup, but that's a breaking change for any in-flight author-mode projects. Keep the name for now and document that reader mode's `ledger.md` and author mode's `claims_ledger.md` are the same artifact type.
3. **Should Phase 4's convergence comparison be wired into CI?** Useful as a living regression test if author mode stabilizes. Defer until Phase 4 runs cleanly.

## Execution order

1. Phase 1 (validator `.tex` support) — pure code.
2. Phase 2 (orchestrator integration) — doc + one-line wire-up.
3. Phase 4 (MRM LaTeX convergence run) — exercise the fix with a known-good target.
4. If Phase 4 passes cleanly, Phase 3 (doc refresh) — describe author mode correctly now that we've proven it.
5. Phase 5 (thesis chapter shakeout) — find the real-world bugs the MRM regression can't surface.

Ship each phase in its own commit so rollback is easy.
