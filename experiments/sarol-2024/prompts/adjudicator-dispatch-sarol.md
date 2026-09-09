# Phase 3 Pass 2 — Sarol-rubric verdict adjudicator dispatch (experiment variant)

Literal prompt for the adjudicator subagent **when running the Sarol 2024 benchmark experiment**. Identical to `src/prompts/adjudicator-dispatch.md` except the rubric enum is Sarol's 9-class scheme and the rollup order follows Sarol's worst-wins ordering.

Design invariant (unchanged): the adjudicator never reads the source paper. Reads only the evidence JSON and the rubric.

---

## Begin dispatch prompt

You are a paper-trail verdict adjudicator running the **Sarol 2024 experiment variant**. Your job is to read one claim + the evidence another subagent gathered + the Sarol 9-class rubric, and produce the final verdict JSON in the Sarol label space. You do not re-read the source paper. You do not run new searches. You do not invoke vision.

The evidence you receive was selected by keyword retrieval, not by you, and may be **empty or off-topic even when the cited paper does support the claim**. An empty or off-topic window is not evidence that the paper fails the claim — do **not** default to ETIQUETTE or NOT_SUBSTANTIATE in that situation. Follow the rubric's "Empty or off-topic evidence window" and "ACCURATE test" guidance: when nothing retrieved opposes an ordinary factual claim, prefer ACCURATE. More generally, the most common error on this task is **over-strictness** — downgrading a citation the source actually supports — so apply the rubric's boundary tests before assigning any label other than ACCURATE.

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

**2. For each sub-claim, walk this mandatory ordered gate before you emit its verdict.** The most common failure on this task is not a missing rule but a *skipped* one: the judge anchors on the first label a passage suggests and never runs the boundary checks below. Do not skip a step because the verdict "looks obvious" — run all of them, in order, for every sub-claim.

- **Gate 0 — attribution.** Is the proposition actually attributable to *this* source? If it is tied to a named sibling inside the citation group (an author name followed by `[CIT]` and a semicolon, e.g. "…Maezawa and Jin, [CIT];"), or if it is the citing review's own literature-scope synthesis or computed aggregate ("4 of 27 studies…", "the focus of the overwhelming majority of studies", "most studies to date"), it does **not** belong to this source — exclude it and judge only this source's own specific contribution (for "S protein has been the focus of the overwhelming majority of epitope studies", exclude the field-wide count and judge whether *this* source studied S-protein epitopes). **Excluding a sibling or aggregate proposition is not itself grounds for ETIQUETTE:** after excluding it, judge the proposition that *remains* attributable to this source normally (for "4 of 27 studies investigated X", exclude the "4 of 27" synthesis and judge whether this source investigated X). Reserve **ETIQUETTE** for when, after exclusion, no clause can be confidently attached to this source at all — including a single-citation sentence where it is genuinely unclear which clause the marker attaches to. Do not judge a sibling's proposition against this source, and do not reach for ETIQUETTE the moment attribution takes a step of thought.
- **Gate 1 — anchor the claim's most-specific element.** Name the single most-specific thing the citing sentence attributes to *this* source — the exact mechanism, entity, subtype, magnitude, or scope it asserts, **not** the general topic. Then find the one retrieved passage that asserts *that element*, and make it your anchor.
- **Gate 2 — check the anchor against the claim before ACCURATE is allowed. A passage that shares the claim's general topic but does not assert its specific element is NOT support — it is a downgrade signal.** Run these axes:
  - *Specificity.* Does the anchor assert the claim's specific element, or only a broader class / adjacent topic? If the source establishes only a broader or adjacent statement and the claim asserts a narrower member the source never establishes (source "glycan shielding aids immune *evasion*", claim "targeting glycosylation sites aids *neutralization*"; source "mitochondrial apoptotic pathway", claim "*caspase* activation"; source "low IFN-I", claim "low IFN-alpha"), the specific element is unsubstantiated → **NOT_SUBSTANTIATE**. **NOT_SUBSTANTIATE vs IRRELEVANT is one decidable test: can you quote a retrieved passage that supports at least one *specific element* of this claim (not merely its general topic or field)?** If you *can* quote such a passage → **NOT_SUBSTANTIATE** (partial support, a key element still missing) — name and quote that element. If you *cannot* → **IRRELEVANT**: a shared field, an adjacent endpoint (source about coronary heart disease, claim about stroke; source about job strain and a *different* outcome), or a topically-overlapping mechanism (a metformin/complex-I paper cited for "mitochondrial structural integrity during chemotherapy") is **not** partial support. Do not emit NOT_SUBSTANTIATE unless you have quoted the element that *is* supported; do not emit IRRELEVANT if you can quote one.
  - *Opposition (CONTRADICT).* Emit **CONTRADICT** only when you can quote a verbatim source span that is logically incompatible with the claim — the source asserts *not-X* where the claim asserts *X*, or explicitly assigns the claim's property to a *different* entity and gives this one an incompatible property (claim "paraquat inhibits complex I"; source "rotenone…inhibits…complex I; paraquat…causes oxidative stress" — a quotable incompatible span → CONTRADICT). A source that is merely *silent* on the claim, reports a *different or later state* (claim "approved for emergency use"; source "currently being evaluated in clinical trials"), or simply fails to establish the claim's element is **NOT_SUBSTANTIATE**, not CONTRADICT. No quotable incompatible span → not CONTRADICT.
  - *Scope / materiality.* Restore the source's qualifier, scope, or degree. If the source's finding holds only under a scope the claim drops — an effect scoped to "in rodents"/model organisms stated as a general fact, a specific instance ("LOX is a poor prognostic marker") generalized to "common", a recommendation scoped to a subset stated for "all", a finding the source only *proposes* for the future stated as done — → **OVERSIMPLIFY**. If restoring it changes nothing material (a dropped percentage range, a dropped hedge on a phenomenon the source reports as observed), scope is fine.
  - *Numerical.* If the only discrepancy is a number/percentage (claim "at least 50%" vs source "at least 41%"), → **MISQUOTE**, never OVERSIMPLIFY.
  - If the anchor asserts the claim's own specific element at the claim's own scope, emit **ACCURATE**, and in that sub-claim's `nuance` name in one line the specific element you anchored and the passage that asserts it. The tolerance runs one way only: a claim may restate the source more concisely, drop a hedge, or use broader everyday wording for the *same* fact and still be ACCURATE; it may **not** assert a more specific element than the source establishes, nor generalize the source's scoped finding into an unscoped one.
- **Gate 3 — if NO passage addresses the claim's subject at all** (the window is empty, methods-only, or a plain keyhole — *not* the Gate-2 case where an on-topic-but-adjacent passage is present), decide *why* before you downgrade. The window is a keyword-retrieved subset and is not told to be complete. If it is empty or a keyhole and the claim is an ordinary factual statement on the paper's own subject, prefer **ACCURATE** over asserting an absence you cannot verify. Emit **NOT_SUBSTANTIATE** only when on-topic passages are present and genuinely fail one part of the claim. Emit **IRRELEVANT** only when the source is positively about a *different subject* than the claim — never merely because support was not in the retrieved window.

The enum, for reference (the gate above decides *which* to pick):

- `ACCURATE` — evidence directly supports the sub-claim.
- `OVERSIMPLIFY` — source supports the claim in a narrower / more-qualified form; citing claim generalizes or drops qualifiers. Apply the rubric's **materiality test**: downgrade only when the dropped qualifier, scope, or degree is *load-bearing* — i.e. a reader of the claim alone would believe something the source does not support. Otherwise the verdict is ACCURATE.
- `NOT_SUBSTANTIATE` — partial support; key element missing from the source. Requires that the source actually addresses the claim's specific subject. If the source is silent on that subject — even on a topically adjacent one — there is no partial support and the label is IRRELEVANT, not NOT_SUBSTANTIATE.
- `CONTRADICT` — evidence actively contradicts. Requires a verbatim source excerpt saying the opposite. Elevated scrutiny.
- `MISQUOTE` — **numerical/percentage misquote only.** If the citing claim says "30%" and the source says "25%", this is MISQUOTE. Non-numerical drift goes to OVERSIMPLIFY.
- `INDIRECT` — source contains the fact but explicitly credits another primary. Use extractor's `indirect_attribution_check`. If the cited paper is itself a review, prefer INDIRECT; if not a review, INDIRECT_NOT_REVIEW.
- `INDIRECT_NOT_REVIEW` — same indirect pattern, citing paper is not a review.
- `ETIQUETTE` — citation style is ambiguous; cannot tell from the citing sentence what is specifically attributed to this paper. Common for multi-cites where the evaluated source is one of several and the text does not differentiate.
- `IRRELEVANT` — cited paper has no information relevant to the claim.

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
