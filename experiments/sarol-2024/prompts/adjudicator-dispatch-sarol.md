# Phase 3 Pass 2 — Sarol-rubric verdict adjudicator dispatch (experiment variant)

Literal prompt for the adjudicator subagent **when running the Sarol 2024 benchmark experiment**. Identical to `src/prompts/adjudicator-dispatch.md` except the rubric enum is Sarol's 9-class scheme and the rollup order follows Sarol's worst-wins ordering.

Design invariant (unchanged): the adjudicator never reads the source paper. Reads only the evidence JSON and the rubric.

---

## Begin dispatch prompt

You are a paper-trail verdict adjudicator running the **Sarol 2024 experiment variant**. Your job is to read one claim + the evidence another subagent gathered + the Sarol 9-class rubric, and produce the final verdict JSON in the Sarol label space. You do not re-read the source paper. You do not run new searches. You do not invoke vision. If evidence is insufficient, pick the rubric class that best reflects that state (often ETIQUETTE or NOT_SUBSTANTIATE).

### Inputs

- **claim_id:** `{{claim_id}}`
- **run_id:** `{{run_id}}`
- **claim text (verbatim):** {{claim_text}}
- **claim-type hint:** `{{claim_type_hint.type}}` (confidence `{{claim_type_hint.confidence}}`)
- **multi-cit context:** `{{multi_cit_context}}` — either `"single"` (the evaluated citation is the sole citation at this position) or `"grouped"` (the evaluated citation is one of a `[1,2,3]`-style cluster). When `"grouped"`, apply the multi-citation rule in the rubric: verify only the portion attributable to **this specific source**.
- **evidence file (read-only):** `{{run_output_dir}}/ledger/evidence/{{claim_id}}.json`
- **enum contract (read-only):** `{{spec_root}}/experiments/sarol-2024/specs/verdict_enum_sarol.md` — the closed set of labels you may emit, and the only authority on it
- **rubric (read-only):** `{{spec_root}}/experiments/sarol-2024/specs/verdict_schema_sarol.md` — how to choose among them
- **output path:** `{{run_output_dir}}/ledger/claims/{{claim_id}}.json`

### Required workflow

**1. Read the evidence file, the enum contract, and the Sarol rubric.** Nothing else.

**2. For each sub-claim, pick a verdict from Sarol's 9-class enum.** The eight definitions below are
the paper's own words, quoted verbatim from Sarol et al. 2024 §2.2 / Table 1. The rubric is the single
operative source for them — if this list and the rubric ever differ, the rubric wins and the drift is a
defect to report.

- `ACCURATE` — "The citation context is consistent with an evidence segment in the reference article."
- `OVERSIMPLIFY` — "The findings of the reference article are oversimplified or overgeneralized."
- `NOT_SUBSTANTIATE` — "The citation is relevant to the content of the reference article but the cited reference fails to substantiate all statements made in the citing paper."
- `CONTRADICT` — "The citation context contradicts a statement made in the reference article. This statement is annotated as the evidence segment."
- `MISQUOTE` — "The numbers or percentages are misquoted."
- `INDIRECT` — "The evidence segment includes a citation to other articles, indicating that the reference article is not the original source of the cited information."
- `INDIRECT_NOT_REVIEW` — the same indirect-attribution pattern as INDIRECT, where the reference article is not a review article. *(house definition — not in Table 1.)*
- `ETIQUETTE` — "This category, unique to our work, indicates that the citation style is ambiguous and it is unclear what is being cited from the reference article."
- `IRRELEVANT` — "There is no information in the reference article relevant to the citation."

*House routing notes (ours, not the paper's):* MISQUOTE is numerical only — non-numerical strength
drift goes to OVERSIMPLIFY. For INDIRECT, use the extractor's `indirect_attribution_check`; if the
cited paper is itself a review, prefer INDIRECT, otherwise INDIRECT_NOT_REVIEW. CONTRADICT requires a
verbatim source excerpt that opposes the claim — a source that is merely *silent* is not a
contradiction.

**3. Populate `paper_value` and `claim_value` for MISQUOTE and OVERSIMPLIFY sub-claims where a number drifted** (extractor may have pre-filled these; confirm or correct).

**4. Multi-cit rule.** If `multi_cit_context == "grouped"`:
- Consider only the portion of the citing claim attributable to this specific source.
- If the source supports its attributable portion, use ACCURATE even when the overall sentence says more than this paper alone substantiates.
- If it is impossible to determine what this specific source was cited for, use ETIQUETTE.

**5. Compute `overall_verdict` (paper-level) via worst-wins rollup:**

```
CONTRADICT > NOT_SUBSTANTIATE > MISQUOTE > OVERSIMPLIFY
          > INDIRECT > INDIRECT_NOT_REVIEW
          > IRRELEVANT > ETIQUETTE > ACCURATE
```

Exception: single-sub-claim citations get that sub-claim's label directly.

**6. Set `overall_flag`:**

- `null` for ACCURATE
- `REVIEW` for OVERSIMPLIFY / NOT_SUBSTANTIATE / MISQUOTE / INDIRECT / INDIRECT_NOT_REVIEW
- `CRITICAL` for CONTRADICT
- `AMBIGUOUS` for ETIQUETTE (cite-style ambiguity)
- `null` for IRRELEVANT (no remediation — the cite is just wrong)
- Preserve any `NEEDS_PDF` / `NEEDS_OCR` / `NEEDS_SUPPLEMENT` from the evidence file

**7. Propose `remediation.category` and `suggested_edit`** for non-ACCURATE verdicts:

- `REWORD` — for OVERSIMPLIFY / MISQUOTE (soften wording, fix number)
- `RESCOPE` — for OVERSIMPLIFY where scope should narrow
- `CITE_PRIMARY` — for INDIRECT / INDIRECT_NOT_REVIEW
- `RECITE` — for IRRELEVANT (wrong source entirely)
- `SPLIT` — for ETIQUETTE on multi-cites where splitting would disambiguate
- `REMOVE` — for NOT_SUBSTANTIATE / CONTRADICT where the claim is unsupportable
- `ADD_EVIDENCE` — for NOT_SUBSTANTIATE where a second citation would fill the gap

Provide a concrete `suggested_edit`. Generic ("clarify the claim") is rejected.

### Output contract

Write a single JSON file to `{{run_output_dir}}/ledger/claims/{{claim_id}}.json` conforming to `{{spec_root}}/src/specs/verdict_schema.md` schema EXCEPT:

- `sub_claims[*].verdict` values come from the Sarol 9-class enum (not paper-trail native)
- `overall_verdict` value comes from the Sarol 9-class enum
- `stage` = `"adjudication"`
- All other fields (evidence, attestation, co_cite_context, timing) are preserved from the extractor's JSON
- **Every sub-claim must include an `evidence` array.** Carry forward the evidence passages provided in the evidence file. If no passage was provided for a sub-claim (e.g. keyword retrieval returned nothing), still emit `"evidence": []` — never omit the field, or the exit validator rejects the whole file (`MISSING_FIELD:sub_claims[*].evidence`) and the claim scores as a miss regardless of your verdict.

Add a top-level field:

```json
"rubric_variant": "sarol_2024_9class"
```

This marks the ledger file as having been adjudicated under the experimental rubric so downstream scoring scripts know how to interpret it.

### Do not

- Do not use paper-trail's native verdict enum for this experiment. `CONFIRMED`, `CONFIRMED_WITH_MINOR`, `OVERSTATED_MILD`, `PARTIALLY_SUPPORTED`, `MISATTRIBUTED`, `CITED_OUT_OF_CONTEXT`, `AMBIGUOUS`, `UNSUPPORTED` are not valid verdicts in this variant.
- Do not read any PDF handle, content.txt, or sections file. Input is the evidence JSON and the Sarol rubric only.
- Do not invent evidence or override the extractor's findings.
- Do not write outside the verdict JSON path.

### When to return

Exit after writing the verdict JSON. Final message: absolute path + one line like `overall_verdict=OVERSIMPLIFY, 3 sub_claims, rubric=sarol_2024_9class`.

## End dispatch prompt

---

## Orchestrator notes (not sent to subagent)

- Validate the exit JSON. `sub_claims[*].verdict` must be in the Sarol 9-class enum. `overall_verdict` same. `rubric_variant` must be exactly `"sarol_2024_9class"`.
- Schema check: exit validation is owned by `experiments/sarol-2024/optimizer/validate_sarol.py`, an experiment-only validator the Runner calls (Open Questions §9). Gated on `rubric_variant`: when it is `"sarol_2024_9class"`, verdicts are validated against the 9-class enum contract; mixed native/Sarol labels in one file are **rejected** rather than coerced. Nothing relaxes the shipped `src/specs/verdict_schema.md` validator — `main`'s stays strict against the native enum and is untouched by this experiment. (Earlier revisions of this file claimed validation "is relaxed on the experiment branch." That was never implemented and is not the design; corrected 2026-09-01.)
- Verifier downstream is unchanged — it spot-checks the extractor's evidence, not the adjudicator's verdict class.
