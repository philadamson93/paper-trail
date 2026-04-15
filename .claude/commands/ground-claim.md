Verify that a cited claim in the manuscript is supported by its source paper. Maintain the claims ledger as an audit artifact. **The ledger stores verbatim source excerpts for verification; the draft paraphrases.** These are different roles — do not insert ledger text into the draft.

## Core principle: raise, don't fix

This command **never edits the manuscript**. It writes only to the claims ledger. Every issue it finds is surfaced as a proposal in the triage report, with:

- The manuscript section / file location where the claim appears
- The claim text as it currently reads
- The source paper citekey + **page number** where the relevant passage appears
- A proposed remediation category plus a concrete suggested edit

The user reviews the triage and decides what to accept. If they accept a proposal, they apply the edit themselves or ask Claude in a follow-up turn to make a specific bounded edit. Unsolicited manuscript edits are out of scope for this command — full stop.

## Invocation forms

- `/ground-claim <citekey> "<claim sentence>"` — single claim
- `/ground-claim path/to/document.tex` — whole-document audit (all `\cite{}` calls)
- `/ground-claim --recheck` — re-verify every ledger entry (detect STALE entries)
- `/ground-claim --review` — triage only; print flagged ledger entries without re-reading PDFs

## Read config

Read `pdf_dir`, `pdf_naming`, `bib_files` from `claims_ledger.md` YAML frontmatter. If missing, prompt the user to run `/init-writing-tools` first and stop.

## Multi-cite citations

LaTeX `\cite{a,b,c}` (comma-separated keys) produces **one ledger entry per citekey**. All entries for the same sentence share the same claim text and claim key, but record different citekey / source page / support level / remediation. If different sub-claims of the sentence rely on different citations, note the covered sub-claim in each entry's source excerpt.

## Pre-flight: ensure source PDFs exist

For every unique citekey in scope:

- Check if `<pdf_dir>/<formatted citekey>.pdf` exists.
- If missing: invoke `/fetch-paper` logic inline. If paywalled or retrieval fails, mark the claim's entry as `PENDING` with a `NEEDS_PDF` flag and continue with other claims. **Never hard-fail** on missing PDFs — the run should process whatever can be processed.

## Per-claim workflow

Process claims grouped by source paper: read each paper once, verify all its claims in a single pass. This is significantly more efficient than the section-by-section order and gives better cross-claim consistency.

For each claim:

### Step 1 — Classify the claim

Assign one of:

- **DIRECT** — attributes a specific finding to the paper ("X et al. showed Y"). Evidence bar: near-verbatim match.
- **PARAPHRASED** — summarizes the paper's argument in our words. Evidence bar: semantic match.
- **SUPPORTING** — our claim, paper cited as evidence for it. Evidence bar: paper's evidence compatible with our framing.
- **BACKGROUND** — definition, priority of invention, general context. Evidence bar: paper contains the concept.
- **CONTRASTING** — "unlike X, we...". Evidence bar: paper actually takes the contrasted position.
- **FRAMING** — citation gestures at a broad topic or motivation without a specific sentence-level claim extracted from the paper. The citation is a pointer to a conversation, not a piece of evidence. Evidence bar: paper addresses the topic. **Contrast with BACKGROUND:** BACKGROUND extracts a specific concept, definition, or priority-of-invention *from* the paper; FRAMING extracts nothing specific — it just marks adjacency. When support is weak, typical remediation is `ACCEPT_AS_FRAMING` or `REMOVE`.

### Step 2 — Locate source evidence

Read the cited PDF. Extract the exact source text that speaks to the claim. Record it verbatim in the ledger with page number.

- Keep excerpts minimal but complete — one to two sentences that unambiguously pin the claim.
- Preserve extraction artifacts (hyphenation, odd whitespace) to maintain the audit trail. Do not clean up the source text.
- For composite claims (multiple sub-claims in one sentence), extract evidence for each sub-claim. Note which sub-claims are not covered.

### Step 3 — Assess support level

Choose one:

- **CONFIRMED** — evidence directly supports the claim.
- **PARTIALLY_SUPPORTED** — supports part of the claim; a sub-element is missing or weaker.
- **OVERSTATED** — true, but our wording is stronger than the paper's (e.g., "substantially outperforms" where paper says "outperforms").
- **UNSUPPORTED** — no evidence found on careful read. Possible hallucination or wrong citation.
- **CONTRADICTED** — evidence actively contradicts the claim. **Critical flag.**
- **MISATTRIBUTED** — claim is true but this is not the source for it.
- **STALE** — the claim text in the manuscript has changed since last verification (claim key mismatch).
- **PENDING** — not yet checked (pre-flight state).

### Step 4 — Propose remediation

If support is not `CONFIRMED`, propose a remediation category AND a concrete suggested edit. Category choices:

- **REWORD** — soften language to match evidence strength.
- **RESCOPE** — narrow the claim so evidence covers it fully.
- **RECITE** — wrong citation; suggest a better source (name specific candidates from the bib or literature).
- **SPLIT** — composite claim; separate the cited sentence from synthesized framing.
- **ADD_EVIDENCE** — add a second citation to cover what the first doesn't.
- **REMOVE** — not supportable and not essential.
- **ACCEPT_AS_FRAMING** — our framing, not the paper's; move citation scope or hedge with "informed by" / "following".

Always include one specific edit, not just a general prescription. Example:

> Remediation: REWORD. Suggested edit: delete "substantially" — source says "Merlin outperforms ... on zero-shot findings classification" without the intensifier.

### Step 5 — Update the ledger

Append or update the entry in `claims_ledger.md`. Each entry has:

- **Claim ID** — sequential (`C001`, `C002`, ...).
- **Manuscript section** — e.g., `2.2.3`.
- **Citekey**.
- **Claim text** — the current sentence from the manuscript.
- **Claim key** — sha1 of the normalized claim text if a hashing tool is available; otherwise store the normalized text itself as the key. Used for stale detection via hash or string comparison on re-run. **Normalization rules** — apply in this order, identically on first verification and re-run, or stale detection will produce false positives:
  1. Lowercase.
  2. Strip LaTeX commands and their arguments: `\cite{...}`, `\citep{...}`, `\citet{...}`, `\ref{...}`, `\label{...}`, `\emph{...}`, `\textbf{...}`, non-breaking tildes `~`.
  3. Collapse runs of whitespace (including newlines) to a single space. Applied *after* command stripping so any whitespace artifacts introduced by stripping are absorbed.
  4. Retain all other punctuation as-is (no stripping of commas, em-dashes, parentheses, etc.).
- **Claim type** — one of the six above.
- **Source excerpt** — verbatim from the PDF with page number.
- **Support level**.
- **Remediation** — category + concrete edit, or `—` if CONFIRMED.
- **Last verified** — today's ISO date.

Maintain both the `## Summary` table (one row per claim) and the `## Details` section (one block per claim). Summary table schema:

```
| ID | Section | Cite | Type | Support | Source page | Flag | Last verified |
```

Keep this schema aligned with the triage report format below so users don't have to reconcile two views.

**Valid `Flag` column values** (use exactly one; keeps the column sortable):

| Flag | When |
|------|------|
| `—` | No flag. Use for CONFIRMED entries. |
| `REVIEW` | Non-critical support-level issue (OVERSTATED, PARTIALLY_SUPPORTED, MISATTRIBUTED). |
| `CRITICAL` | CONTRADICTED or UNSUPPORTED entry. Surface at top of triage. |
| `RECHECK` | STALE — claim text changed since last verification. Re-verify on next run. |
| `NEEDS_PDF` | PDF unavailable. Entry stays PENDING until the PDF is retrieved. |

## Re-run semantics

Every run against an existing ledger must preserve history and handle stale detection deterministically. These rules govern how old entries interact with new evidence.

### Stale detection

When running in `--recheck` mode, or at the start of any run:

- For each existing ledger entry, re-compute the claim key from the current manuscript text (look up the sentence by section + citekey, or best-match if the section has moved).
- If the current key differs from the stored key, set status to `STALE` and add the `RECHECK` flag.
- In non-recheck mode, `STALE` entries are re-verified during this run.

### Updating an existing entry

Entries are identified by the `(claim_key, citekey)` tuple, not by claim key alone. This matters for multi-cite sentences where two or three entries share a claim key but differ in citekey — lookup must match on both.

When a `(claim_key, citekey)` tuple matches an existing entry:

- **Support level unchanged** — update `Last verified` in place; leave the rest.
- **Support level changed** — append a dated history note to the Details block (e.g., `_2026-04-15: was OVERSTATED → now CONFIRMED after reword_`). Never silently overwrite the previous verdict.
- **Source excerpt or page changed** — update and note in the history.

### Claim ID numbering

Claim IDs (`C001`, `C002`, ...) are **global and sequential across runs**. Never restart numbering. The next ID is the highest existing `C###` in the ledger plus one. If you import entries from another ledger, renumber to avoid collisions.

## End-of-run triage report

Print a structured summary. Surface `CONTRADICTED` and `UNSUPPORTED` at the top — these are the entries most needing user attention. Every flagged entry must include the source paper page number so the user can look up the relevant passage directly.

```
Grounding summary: N claims processed.
  CONFIRMED:           X
  PARTIALLY_SUPPORTED: Y
  OVERSTATED:          Z
  UNSUPPORTED:         A   ← review
  CONTRADICTED:        B   ← critical
  MISATTRIBUTED:       C
  STALE:               D
  PENDING (needs PDF): E

Requiring attention:
- C014 (sec 2.2.3, blankemeier2024merlin p. 9) — OVERSTATED.
  Claim (manuscript): "Merlin substantially outperforms ..."
  Source (p. 9):       "Merlin outperforms ..." (no intensifier)
  Remediation: REWORD. Suggested edit: delete "substantially".
  → Your call — this command will not apply the edit.
- ...
```

For every flagged entry, the user should be able to (a) go directly to the cited page in the source PDF to check the context, and (b) see a concrete suggested edit they can accept, modify, or reject.

## Do not

- **Never edit the manuscript (`.tex`) file.** This command writes only to `claims_ledger.md`. Every manuscript-facing proposal is surfaced in the triage report for user acceptance.
- Never suggest inserting a verbatim source excerpt into the manuscript. The draft paraphrases; the ledger preserves.
- Never mark a claim `CONFIRMED` when you couldn't read the PDF. Use `PENDING` + `NEEDS_PDF`.
- Never hallucinate evidence. If no supporting text is found, mark `UNSUPPORTED` and let the user decide.
- Never treat `PARAPHRASED` and `SUPPORTING` as interchangeable — the verification bar differs, and so does the remediation if support is weak.
- Never flag an issue without citing the source paper page number where the relevant passage appears (or explicitly noting "not found anywhere in the paper" for UNSUPPORTED claims).
