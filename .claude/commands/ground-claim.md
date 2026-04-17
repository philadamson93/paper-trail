Verify that a cited claim in the manuscript is supported by its source paper. Maintain the claims ledger as an audit artifact. **The ledger stores verbatim source excerpts for verification; the draft paraphrases.** These are different roles — do not insert ledger text into the draft.

## Core principle: rigor beats compute

A false verdict — a `CONFIRMED` that should have been `OVERSTATED`, or an `UNSUPPORTED` that should have been `CONFIRMED` — is materially worse than spending extra tokens to prevent it. When grounding a claim, always prefer the more thorough path: read the whole paper, try more phrasings, inspect tables and figure captions, document what you searched. Do **not** pre-optimize for speed by skimming, sampling, or declaring "not found" after a shallow pass. The cost of a missed piece of evidence propagates downstream into the manuscript and the literature; the cost of extra reading stops here.

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

**Minimum reading requirement — no shortcuts.**

Before returning *any* verdict (`CONFIRMED`, `UNSUPPORTED`, `OVERSTATED`, anything), you must have read the **entire** cited paper, not only the section most likely to contain the claim. Partial reads are the single biggest failure mode in automated citation auditing — an agent skims the abstract, doesn't find the claim, and declares `UNSUPPORTED` when the evidence was in Results. Do not do this.

For every non-`FRAMING` claim, complete this section-read checklist and record it alongside the claim's entry in the ledger Details block:

```
Paper length:       <N> pages
Section checklist:
  [ ] Abstract
  [ ] Introduction
  [ ] Methods / Materials
  [ ] Results (prose)
  [ ] Results (all tables — list: Table 1, Table 2, …)
  [ ] Results (all figure captions — list: Fig. 1 caption, Fig. 2 caption, …)
  [ ] Discussion
  [ ] Conclusions / Summary
  [ ] Appendix / Supplementary material      (or: n/a if none in PDF)
```

Check each box only after actually reading that section. If the PDF references a supplement you cannot access and the claim is numerical or highly specific, return `PENDING` with a `NEEDS_SUPPLEMENT` note instead of forcing a verdict without it.

**Tables and figure captions count as reading.** Numerical claims (dataset sizes, N values, batch sizes, accuracy numbers, pixel counts, hyperparameters) live in tables and figure captions far more often than in prose. If you haven't inspected the tables, you haven't read the paper.

**Banned shortcuts — any of these invalidates your verdict:**

- "The paper is about X, not Y." Papers routinely contain incidental claims outside their stated topic.
- "Checked the abstract." The abstract simplifies — it is not the paper.
- "Not in the introduction" used as a stand-in for "not in the paper".
- "I couldn't find it" without a completed search-log attestation (see negative-evidence protocol below).
- Skipping tables because they "look like methods details".
- Skipping figure captions because "the result must also be in the prose".
- Concluding from a single keyword search with one phrasing.

If, partway through grounding, you realize you haven't read a section that could plausibly contain the claim — go back and read it before finalizing. Err on the side of more reading.

**Where to search, by claim type:**

- **DIRECT / factual** (numeric values, specific methods, experimental setup like "batch size 24", "trained for 100 epochs"): methods section first, then results tables. Look for near-verbatim match.
- **Priority-of-invention** ("X et al. introduced / first proposed Y"): abstract + introduction + contributions list. Look for claim-of-novelty language ("we propose", "we introduce").
- **Results** ("achieves 95% accuracy on Z"): abstract + results section + result tables + discussion. Verify exact number, unit, and scope.
- **Methods / architecture** ("uses transformer / diffusion / U-Net"): methods section.
- **FRAMING / BACKGROUND** (general motivation like "X is important", "Y is a challenge"): introduction + motivation paragraphs + related work.

**Search procedure:**

1. Start with keyword / phrase search for the most specific terms in the claim. Exact noun phrases ("deep feature distance", "diffusion posterior sampling") and numbers are strongest signals.
2. If keyword search misses, expand to semantic matches (synonyms, paraphrases).
3. Always check the abstract — the cleanest summary often lives there.
4. For numeric claims, verify the exact number, unit, *and scope* (e.g., "95% accuracy" might be top-1 vs. top-5, in-distribution vs. OOD — specify which).

**Negative-evidence protocol — required before marking `UNSUPPORTED` or `CONTRADICTED`:**

These are the two highest-consequence verdicts. `UNSUPPORTED` accuses the manuscript of a possibly-hallucinated citation; `CONTRADICTED` claims the cited paper actively disagrees. Neither is appropriate after a shallow pass. Before returning either, record a complete attestation log in the Details block:

```
Attestation log:
  Paper length:       <N> pages
  Section checklist:  abstract ✓, intro ✓, methods ✓,
                      results ✓ (prose + <K> tables + <M> figure captions),
                      discussion ✓, conclusions ✓,
                      appendix / supplement ✓ / not accessible / n/a
  Phrasings searched: "<literal claim>",
                      "<synonym / term-substitution variant>",
                      "<semantic paraphrase>",
                      … (minimum 3 distinct phrasings)
  Specific checks:    e.g., Table 2 rows for dataset sizes,
                      Fig. 4 caption for accuracy numbers,
                      Eq. 3 surrounding prose for the derivation,
                      …
  Closest adjacent passage: "<verbatim quote>" (p. <N>)
                            — reason it is not the claim:
                            <one sentence>
```

Minimum phrasings:

- **Three or more distinct phrasings** before `UNSUPPORTED`. Must include: (1) the claim's literal words; (2) at least one synonym or term-substitution variant; (3) at least one semantic paraphrase.
- For **numerical claims**, also search alternate formats (`10,000` / `10k` / `ten thousand` / scientific notation / nearby unit conversions).
- For **methodological claims**, include the method name *and* common abbreviations *and* alternative terminology (e.g., "Deep Image Prior" + "DIP"; "Generative Adversarial Network" + "GAN").
- For **priority-of-invention claims**, check novelty phrasings: "we propose", "we introduce", "we are the first", "to our knowledge, the first", "novel".

Invalid attestations (any of these invalidates an `UNSUPPORTED` verdict — return `PENDING` with a `NEEDS_RECHECK` flag instead):

- Any section left unchecked.
- Fewer than 3 phrasings tried.
- No "closest adjacent passage" recorded (there is almost always *something* nearby worth quoting, even in a true negative).
- Tables and figure captions not explicitly inspected for numerical / specific claims.

`CONTRADICTED` additionally requires a direct verbatim quote of the contradicting passage — the attestation log above is necessary but not sufficient.

**Check for indirect attribution — required for every non-`FRAMING` claim:**

When you *do* find supporting text in the cited paper, also check whether *that paper* attributes the fact to another source (citation marker in the supporting sentence or adjacent paragraph). If yes, this is a signal for `INDIRECT_SOURCE` — see Step 3. Extract the primary-source reference from the cited paper's own bibliography so Step 4's `CITE_PRIMARY` remediation has something concrete to propose.

**Check for out-of-context citation — required for every claim:**

Record the paragraph's topic / section heading alongside the extracted quote (e.g., "Section 3.2 Results — baseline comparison"). If the passage is being used in our manuscript in a context materially different from where it appears in the cited paper — e.g., a stated limitation quoted as a contribution; a related-work summary quoted as the paper's own finding; a passing remark quoted as a central result — flag for `CITED_OUT_OF_CONTEXT` in Step 3.

**Extraction rules:**

- Keep excerpts minimal but complete — one to two sentences that unambiguously pin the claim.
- Preserve extraction artifacts (hyphenation, odd whitespace) to maintain the audit trail. Do not clean up the source text.
- For composite claims (multiple sub-claims in one sentence), extract evidence for each sub-claim. Note which sub-claims are not covered.

**Self-check before moving to Step 3 — answer each question silently; if any is "no" or "unsure", return to Step 2 before proceeding:**

1. Did I read every section of the paper — abstract, intro, methods, results prose *and* all tables *and* all figure captions, discussion, conclusions, and any appendix / supplement present in the PDF?
2. For any section I did not read, is it clearly impossible for the claim to appear there? If not, I have not read enough.
3. If I am about to return `UNSUPPORTED` or `CONTRADICTED`, have I completed the full attestation log with at least 3 distinct phrasings and a closest-adjacent quote?
4. If I am about to return `CONFIRMED`, have I also verified that no *later* section of the paper qualifies, narrows, or walks back the claim I found? (Results and discussion commonly qualify what the abstract states.)
5. For numerical or highly specific claims, did I inspect tables and figure captions directly — not only prose?
6. Did I check whether the cited paper itself attributes this fact to another source (signal for `INDIRECT_SOURCE`)?
7. Did I check whether the passage is used in a materially different context in the cited paper vs. our manuscript (signal for `CITED_OUT_OF_CONTEXT`)?
8. Would a careful reviewer, given my search log and extracted quote, agree that the verdict is justified? If the attestation could be accused of shortcutting, strengthen it.

Rigor beats compute. If in doubt, read more.

### Step 3 — Assess support level

Choose one:

- **CONFIRMED** — evidence directly supports the claim.
- **PARTIALLY_SUPPORTED** — supports part of the claim; a sub-element is missing or weaker.
- **OVERSTATED** — true, but our wording is stronger than the paper's (e.g., "substantially outperforms" where paper says "outperforms"). About *strength*.
- **OVERGENERAL** — true within the paper's narrow scope, but our claim generalizes beyond that scope (e.g., paper shows a result on chest CT; we claim "medical imaging"). About *scope*, distinct from `OVERSTATED`'s strength dimension.
- **CITED_OUT_OF_CONTEXT** — the passage supporting the claim exists in the cited paper, but it was written in a context materially different from how we're using it (e.g., citing a paper's stated limitation as if it were a contribution; citing a related-work summary as the paper's own finding; citing a passing remark as a central result). More subtle than `MISATTRIBUTED`.
- **UNSUPPORTED** — no evidence found on careful read. Possible hallucination or wrong citation. Requires a search log in the Details block per Step 2.
- **CONTRADICTED** — evidence actively contradicts the claim. **Critical flag.**
- **MISATTRIBUTED** — claim is true, but this is not the source for it at all.
- **INDIRECT_SOURCE** — cited paper *does* contain the fact, but it cites another source for that same fact. Technically true; not the primary source. Reference-hygiene issue, not factual error. Typical remediation is `CITE_PRIMARY` — extract the primary source from the cited paper's own bibliography and suggest citing it directly (or in addition).
- **STALE** — the claim text in the manuscript has changed since last verification (claim key mismatch).
- **PENDING** — not yet checked (pre-flight state).

### Step 4 — Propose remediation

If support is not `CONFIRMED`, propose a remediation category AND a concrete suggested edit. Category choices:

- **REWORD** — soften language to match evidence strength.
- **RESCOPE** — narrow the claim so evidence covers it fully.
- **RECITE** — wrong citation entirely; suggest a different source (name specific candidates from the bib or literature).
- **CITE_PRIMARY** — cited paper is not the primary source for the fact; replace (or supplement) with the primary source that the cited paper itself credits. Name the specific primary source — pull it from the cited paper's own bibliography. Do not return a vague "find a better source".
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
| `REVIEW` | Non-critical support-level issue (OVERSTATED, OVERGENERAL, PARTIALLY_SUPPORTED, CITED_OUT_OF_CONTEXT, MISATTRIBUTED, INDIRECT_SOURCE). |
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
