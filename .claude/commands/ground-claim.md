Verify that a cited claim in the manuscript is supported by its source paper. Maintain the claims ledger as an audit artifact. **The ledger stores verbatim source excerpts for verification; the draft paraphrases.** These are different roles — do not insert ledger text into the draft.

## Core principles

- **Rigor beats compute.** A false verdict — a `CONFIRMED` that should have been `OVERSTATED`, or an `UNSUPPORTED` that should have been `CONFIRMED` — is materially worse than spending extra tokens to prevent it. Prefer thorough reads, more phrasings, and figure inspection over any shortcut.
- **Raise, don't fix.** This command never edits the manuscript. Every issue is surfaced as a remediation proposal for the user to accept, modify, or reject.
- **Two-pass, structured output.** A Phase-3 subagent no longer "reads a PDF and narrates evidence" open-endedly. It runs two bounded passes against a pre-ingested source handle (`pdfs/<citekey>/`): an extractor that gathers evidence, then an adjudicator that picks a verdict from the rubric. Both emit JSON conforming to `.claude/specs/verdict_schema.md`.

## Invocation forms

- `/ground-claim <citekey> "<claim sentence>"` — single claim
- `/ground-claim path/to/document.tex` — whole-document audit (all `\cite{}` calls)
- `/ground-claim --recheck` — re-verify every ledger entry (detect STALE entries)
- `/ground-claim --review` — triage only; print flagged ledger entries without re-grounding
- `/ground-claim --triage` — interactive triage of `AMBIGUOUS` entries

## Read config

Read `pdf_dir`, `pdf_naming`, `bib_files` from `claims_ledger.md` YAML frontmatter. If missing, prompt the user to run `/init-writing-tools` first and stop.

## Canonical artifacts

- `pdfs/<citekey>.pdf` — the fetched PDF (Phase 2 output)
- `pdfs/<citekey>/` — the ingest handle (Phase 2.5 output; see `.claude/specs/ingest.md`)
- `ledger/evidence/<claim_id>.json` — extractor output (pass 1)
- `ledger/claims/<claim_id>.json` — adjudicated verdict (pass 2, source of truth)
- `ledger/verifications/<claim_id>__<sub_claim_id>.json` — verifier spot-check output (pass 3)
- `ledger.md` — human-readable view; **rendered from `ledger/claims/*.json`**, not edited directly

Everything that is "the ledger" conceptually is `ledger/claims/*.json`. `ledger.md` is a projection.

## Multi-cite citations

LaTeX `\cite{a,b,c}` produces **one ledger entry per citekey**. All entries for the same sentence share the same claim text and claim key, but record different citekey / source page / verdict / remediation. The orchestrator populates `co_cite_context.sibling_citekeys` in each claim's dispatch so the extractor can cross-check siblings for CITED_OUT_OF_CONTEXT / INDIRECT_SOURCE signals.

## Pre-flight: ensure source PDFs and ingest are ready

For every unique citekey in scope:

1. Check if `<pdf_dir>/<citekey>.pdf` exists.
2. If missing: invoke `/fetch-paper` logic. If paywalled or retrieval fails, mark the claim `PENDING` with `NEEDS_PDF` and continue.
3. Check if `<pdf_dir>/<citekey>/ingest_report.json` exists with `success: true`.
4. If missing or unsuccessful: run `.claude/scripts/ingest_pdf.py --pdf <path>.pdf --citekey <citekey> --out-dir <pdf_dir>/<citekey>/`. If GROBID is not available, the script falls back to `pdftotext_fallback` mode — that's acceptable; the handle still exposes `content.txt` and `figures/`.
5. Record `ingest_mode` on the claim's dispatch payload. If `error`, mark `NEEDS_PDF`.

**Never hard-fail** on missing PDFs or failed ingest — the run processes whatever can be processed.

## Per-claim workflow (two-pass dispatch)

For each claim, the orchestrator dispatches three subagents in sequence. Each has its own bounded contract; none improvises.

### Pass 1 — Evidence extractor

Dispatches the prompt in `.claude/prompts/extractor-dispatch.md`, filling `{{slots}}` with run values. The subagent:

- Reads `pdfs/<citekey>/meta.json`, `sections/*.txt`, `content.txt`, `figures/index.json`
- Decomposes the claim into atomic sub-claims
- Runs `rg` for ≥3 phrasings per sub-claim (literal + synonym + paraphrase; numerical alternates for quantitative sub-claims)
- Inspects figures via vision when a sub-claim is figure-derived
- Cross-checks co-cite siblings
- Writes `ledger/evidence/<claim_id>.json` — evidence + attestation, but verdict fields left `"PENDING"`

**The extractor does not assign a verdict.** That is Pass 2's job.

### Pass 2 — Verdict adjudicator

Dispatches the prompt in `.claude/prompts/adjudicator-dispatch.md`. The subagent reads **only** the evidence JSON and the rubric (`.claude/specs/verdict_schema.md`) — not the source paper. Picks a verdict per sub-claim from the enum, computes the overall verdict via the rollup rule, proposes a remediation. Writes `ledger/claims/<claim_id>.json`.

This split keeps the adjudicator's context tiny (~2kb of JSON + ~4kb of rubric) and makes verdicts deterministic given the evidence.

### Pass 3 — Attestation verifier

Dispatches the prompt in `.claude/prompts/verifier-dispatch.md`. The orchestrator samples one evidence entry from the adjudicated claim and passes it to the verifier, which confirms or rejects that the recorded passage exists in the source as claimed. On `FAIL` → bounce the claim back through Pass 1 (max 2 bounces, then flag AMBIGUOUS with SCHEMA_VIOLATION). On `PARTIAL` → add `UNVERIFIED_ATTESTATION` flag. On `PASS` → verdict stands.

## Taxonomy references

Claim types, verdict enums, flag enum, remediation categories, and rollup rules all live in `.claude/specs/verdict_schema.md`. This command does not duplicate them — treat that file as authoritative. Any enum drift between prompts and ledger is a bug.

Claim types (quick reference):

- `DIRECT` — attributes a specific finding; evidence bar: near-verbatim.
- `PARAPHRASED` — summarizes the paper in our words; semantic match required.
- `SUPPORTING` — our claim; paper cited as supporting evidence.
- `BACKGROUND` — definition, priority of invention, general context.
- `CONTRASTING` — "unlike X, we..."; paper must actually take the contrasted position.
- `FRAMING` — citation gestures at a topic without specific evidence extracted. Lower evidence bar.

Classification is produced in a pre-step by a claim-extractor from the manuscript sentence. Confidence (`high` / `medium` / `low`) modulates Pass 1's search effort: when confidence is `medium` or `low`, apply the strictest evidence bar (DIRECT) during search regardless of the tentative type. The post-evidence self-check in the adjudicator may reclassify if the evidence shape contradicts the initial classification.

## Stale detection

On `--recheck` or at run start:

- Recompute each ledger entry's claim key from the current manuscript text.
- Normalization: (1) lowercase, (2) strip LaTeX commands + arguments + `~` ties, (3) collapse whitespace runs, (4) keep other punctuation.
- If computed key ≠ stored key → mark STALE + RECHECK flag.
- In non-recheck mode, STALE entries are re-grounded during this run.

## Updating existing entries

Entries are identified by `(claim_key, citekey)`, not claim_key alone.

- Support level unchanged → update `Last verified`; no history entry.
- Support level changed → append a dated history note in the JSON's `history[]` array. Never silently overwrite.
- Source excerpt / page changed → update + history note.

## Claim ID numbering

Claim IDs (`C001`, `C002`, ...) are global and sequential across runs. Never restart numbering. The orchestrator allocates IDs before dispatch; subagents never mint IDs.

## Ambiguity triage

When a claim's verdict is `AMBIGUOUS`, the adjudicator left structured reasoning in `sub_claims[*].nuance` and left the overall flag `AMBIGUOUS`. Triage mode resolves these interactively.

### Triage workflow (`/ground-claim --triage`)

For each `AMBIGUOUS` entry in the ledger:

1. **Present via `AskUserQuestion`.** Show: claim ID, manuscript claim text, citekey, evidence excerpts, candidate verdicts, and the adjudicator's reasoning. Options are the candidate verdicts; if more than 3, show top 3 + "Other / needs more context".
2. **On user response:**
   - Patch the ledger JSON: update `sub_claims[*].verdict`, recompute `overall_verdict`, clear `AMBIGUOUS` flag, set the appropriate new flag.
   - Append a `history[]` entry: `{date, from: "AMBIGUOUS", to: "<chosen verdict>", actor: "user triage", note: "<free text>"}`.
   - If the resolved verdict is not CONFIRMED, prompt again for remediation category (with free-text override).
3. **Report at end of triage:** resolved vs deferred counts; list deferred claim IDs.

### Do not

- Do not auto-pick a verdict for AMBIGUOUS — the whole point is that the adjudicator refused. Triage is the user's call.
- Do not hide ambiguity. If the adjudicator is uncertain, prefer AMBIGUOUS over a false-confident pick.

## End-of-run report (user-facing)

Print a structured summary. Surface CONTRADICTED and UNSUPPORTED at the top.

```
Grounding summary: N claims processed.
  CONFIRMED:              X
  CONFIRMED_WITH_MINOR:   X'
  PARTIALLY_SUPPORTED:    Y
  OVERSTATED / OVERSTATED_MILD / OVERGENERAL:  Z
  CITED_OUT_OF_CONTEXT:   Z'
  UNSUPPORTED:            A   ← review
  CONTRADICTED:           B   ← critical
  MISATTRIBUTED:          C
  INDIRECT_SOURCE:        C'
  AMBIGUOUS:              F   ← awaiting user triage
  STALE:                  D
  PENDING (needs PDF):    E

If F > 0:
  F claims flagged AMBIGUOUS. Run `/ground-claim --triage` to resolve.

Requiring attention (CONTRADICTED / UNSUPPORTED first, then CRITICAL flags, then REVIEW):
- C014 (sec 2.2.3, blankemeier2024merlin) — OVERSTATED.
  Claim: "Merlin substantially outperforms ..."
  Source (p. 9): "Merlin outperforms ..." (no intensifier)
  Remediation: REWORD. Suggested edit: delete "substantially".
  Click-through: file:///abs/path/pdfs/blankemeier2024merlin.pdf#page=9
- ...
```

Every flagged entry includes a `file://...#page=N` click-through so the user can verify the cited passage in one click.

## Do not

- Do not edit `.tex` files. This command writes to the ledger only.
- Do not suggest pasting verbatim source excerpts into the manuscript. Draft paraphrases; ledger preserves.
- Do not mark CONFIRMED when you couldn't ingest the PDF. Use PENDING + NEEDS_PDF.
- Do not hallucinate evidence. If no supporting text after ≥3 phrasings, the extractor records a `closest_adjacent` passage and leaves the verdict for the adjudicator to mark UNSUPPORTED.
- Do not treat PARAPHRASED and SUPPORTING as interchangeable — the evidence bars differ.
- Do not flag an issue without a page number click-through (or explicit "nowhere in paper" for UNSUPPORTED).
- Do not duplicate the verdict / claim-type / flag enums in this file. Reference `.claude/specs/verdict_schema.md` instead. Drift between spec and prompts is a bug.
