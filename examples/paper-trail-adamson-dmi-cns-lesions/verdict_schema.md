# Verdict JSON Schema — Phase 3 subagent exit contract

Every Phase 3 subagent (grounding extractor, grounding adjudicator, verifier) emits JSON conforming to this schema. The orchestrator validates on receipt; validation failure triggers one retry, then escalation to the user.

This is the **authoritative exit format**. The `ledger.md` markdown is a rendered view of verdict JSON — not the other way around. If the rendered markdown and the JSON disagree, the JSON wins.

## File layout

Per run:

```
<output-dir>/
  ledger/
    claims/
      C001.json    ← per-claim verdict (source of truth)
      C002.json
      ...
    evidence/
      C001.json    ← extractor output (Pass 1 only; optional persistence)
      C002.json
      ...
  ledger.md        ← rendered from ledger/claims/*.json
```

For backwards compatibility with the current `.inflight/` convention used by the archived orchestrator, the active orchestrator writes directly to `ledger/claims/`. The old `.inflight/` directory is no longer used.

## Verdict envelope

```json
{
  "claim_id": "C042",
  "schema_version": "1.0",
  "run_id": "run_20260418T1234Z",
  "citekey": "hammernik2021",
  "handle": "pdfs/hammernik2021/",
  "ingest_mode": "grobid",
  "source_ref_urls": [
    "file:///absolute/path/to/pdfs/hammernik2021.pdf#page=5"
  ],

  "claim_text": "<verbatim manuscript sentence>",
  "manuscript_section": "2.2.3",
  "claim_type": {
    "type": "PARAPHRASED",
    "confidence": "medium"
  },

  "sub_claims": [
    {
      "sub_claim_id": "C042.a",
      "text": "<the atomic factual assertion this sub-claim encodes>",
      "evidence": [
        {"section": "Results", "line": 47, "snippet": "<verbatim excerpt>"}
      ],
      "figures_checked": [
        {"figure": "fig2_p3.png", "question": "<question asked>", "vision_response": "<verbatim vision response>"}
      ],
      "verdict": "CONFIRMED",
      "paper_value": null,
      "claim_value": null,
      "nuance": "<optional one-sentence note>"
    }
  ],

  "overall_verdict": "CONFIRMED_WITH_MINOR",
  "overall_flag": "MINOR",
  "remediation": {
    "category": "REWORD",
    "suggested_edit": "<concrete edit suggestion>"
  },

  "attestation": {
    "phrasings_tried": [
      "<phrasing 1>",
      "<phrasing 2>",
      "<phrasing 3>"
    ],
    "section_checklist": [
      {"section": "Abstract", "read": true},
      {"section": "Introduction", "read": true},
      {"section": "Methods", "read": true}
    ],
    "closest_adjacent": "<closest-but-not-matching passage, if UNSUPPORTED/CONTRADICTED>",
    "indirect_attribution_check": "<note on whether source credits another primary>",
    "out_of_context_check": "<note on context mismatch vs manuscript usage>"
  },

  "co_cite_context": {
    "sibling_citekeys": ["chen2022", "sandino2020"],
    "sibling_verdicts": [
      {"citekey": "chen2022", "supports_sub_claim_ids": ["C042.a"], "excerpt": "..."}
    ]
  },

  "stage": "grounding",
  "timing": {
    "wall_clock_seconds": 42,
    "tokens_in": null,
    "tokens_out": null
  }
}
```

## Field reference

### Identity

- **`claim_id`** — string, required. Format `C<NNN>`. Allocated by orchestrator before dispatch; subagents never mint IDs.
- **`schema_version`** — string, required. Current `"1.0"`.
- **`run_id`** — string, required. Format `run_<YYYYMMDDTHHMMZ>`. Allows joining across JSON files from the same run.
- **`citekey`** — string, required. The bibtex key for the cited source.
- **`handle`** — string, required. Path prefix to the ingested source artifacts (`pdfs/<citekey>/`). Relative to the run's output-dir.
- **`ingest_mode`** — enum: `"grobid"` | `"ocr_fallback"` | `"pdftotext_fallback"` | `"error"`. Emitted by `scripts/ingest_pdf.py`; confidence-modulates subagent behavior and the verifier's threshold.
- **`source_ref_urls`** — array of strings. Canonical click-through refs for a reader. Usually `file://...pdf#page=N` for local PDFs. Empty array if none.

### Claim

- **`claim_text`** — string, required. Verbatim manuscript sentence (the actual cited sentence, not a summary).
- **`manuscript_section`** — string, optional. Section or heading path where the claim lives (e.g., `"2.2.3"`, `"Methods § Reconstruction"`).
- **`claim_type`** — object `{type, confidence}`. `type` ∈ `DIRECT | PARAPHRASED | SUPPORTING | BACKGROUND | CONTRASTING | FRAMING`. `confidence` ∈ `high | medium | low`.

### Sub-claims (composite-claim resolution)

- **`sub_claims`** — array, required (≥1). Each atomic factual assertion within the sentence gets one entry. For simple claims, one sub-claim is fine; for composite claims (e.g., "ResNet50 pretrained on 1.4M images including 670k MRI"), split into multiple.
  - **`sub_claim_id`** — string, required. Format `<claim_id>.<letter>` (e.g., `C042.a`, `C042.b`).
  - **`text`** — string, required. The atomic assertion.
  - **`evidence`** — array of `{section, line, snippet}`. Evidence retrieved from the source. `line` refers to the line in `handle/content.txt` if available, otherwise null.
  - **`figures_checked`** — array of `{figure, question, vision_response}`. Empty if no figures consulted.
  - **`verdict`** — enum, required:
    - `CONFIRMED` — evidence directly supports the sub-claim
    - `OVERSTATED_MILD` — true in paper but the manuscript's wording is moderately stronger
    - `OVERSTATED` — true in paper but the manuscript's wording is substantially stronger
    - `OVERGENERAL` — true in paper's narrow scope; manuscript generalizes beyond
    - `PARTIALLY_SUPPORTED` — part supported; element missing or weaker
    - `CITED_OUT_OF_CONTEXT` — passage exists but used in a materially different context
    - `UNSUPPORTED` — no evidence found on careful read
    - `CONTRADICTED` — evidence actively contradicts the sub-claim
    - `MISATTRIBUTED` — sub-claim is true but this source isn't where it comes from
    - `INDIRECT_SOURCE` — source contains the fact but credits another primary
    - `AMBIGUOUS` — evidence documented but adjudicator can't confidently pick
  - **`paper_value`** — string or number, optional. The quantitative value from the source (e.g., `"1.35 million"`). Use for OVERSTATED verdicts where a number drifted.
  - **`claim_value`** — string or number, optional. The value as stated in the manuscript (e.g., `"1.4 million"`). Same purpose.
  - **`nuance`** — string, optional. One sentence of reviewer-useful context.

### Overall verdict

- **`overall_verdict`** — enum, required. Rolls up `sub_claims[].verdict` per this rule:
  - All CONFIRMED → `CONFIRMED`
  - Any OVERSTATED* or OVERGENERAL but otherwise CONFIRMED → `CONFIRMED_WITH_MINOR`
  - Single-sub-claim entries: `overall_verdict` = the sub-claim's verdict directly (preserves CITED_OUT_OF_CONTEXT, INDIRECT_SOURCE, MISATTRIBUTED, UNSUPPORTED, CONTRADICTED at top level instead of collapsing to PARTIALLY_SUPPORTED). This avoids losing verdict precision for simple claims.
  - Multi-sub-claim entries with mixed PARTIALLY_SUPPORTED / CITED_OUT_OF_CONTEXT → `PARTIALLY_SUPPORTED`
  - Multi-sub-claim entries with any UNSUPPORTED / CONTRADICTED / MISATTRIBUTED / INDIRECT_SOURCE → match the strongest of these
  - Any AMBIGUOUS sub-claim → `AMBIGUOUS`
  - Strength order (strongest to weakest): CONTRADICTED > UNSUPPORTED > MISATTRIBUTED > INDIRECT_SOURCE > CITED_OUT_OF_CONTEXT > PARTIALLY_SUPPORTED > OVERSTATED > OVERSTATED_MILD > OVERGENERAL > CONFIRMED
- **`overall_flag`** — enum: `null | MINOR | REVIEW | AMBIGUOUS | UNVERIFIED_ATTESTATION | CRITICAL | RECHECK | NEEDS_PDF | NEEDS_OCR | NEEDS_SUPPLEMENT`.
- **`remediation`** — object `{category, suggested_edit}`. `category` ∈ `REWORD | RESCOPE | RECITE | CITE_PRIMARY | SPLIT | ADD_EVIDENCE | REMOVE | ACCEPT_AS_FRAMING | —`. `suggested_edit` is a concrete edit the user can apply.

### Attestation

Proves the subagent did the work.

- **`phrasings_tried`** — array of strings, required. ≥3 for DIRECT/PARAPHRASED claims; ≥1 acceptable for FRAMING.
- **`section_checklist`** — array of `{section, read}`. Sections in the ingested paper and whether the subagent read them. Enables verifier to spot-check.
- **`closest_adjacent`** — string, optional. For UNSUPPORTED / CONTRADICTED / MISATTRIBUTED: the closest passage found that doesn't match. Surfaces near-misses for reviewer review.
- **`indirect_attribution_check`** — string, optional. Subagent's note on whether the source credits another primary for this fact.
- **`out_of_context_check`** — string, optional. Subagent's note on whether the source passage is used in a different context than the manuscript's usage.

### Co-cite context

- **`co_cite_context`** — object, optional (present only when the manuscript sentence cites multiple refs).
  - **`sibling_citekeys`** — array of citekeys cited on the same manuscript sentence (excluding this claim's own citekey).
  - **`sibling_verdicts`** — array of `{citekey, supports_sub_claim_ids, excerpt}`. Per-sibling: which sub-claims of ours the sibling paper supports. Enables CITED_OUT_OF_CONTEXT / INDIRECT_SOURCE detection.

### Bookkeeping

- **`stage`** — enum: `"grounding" | "adjudication" | "verification"`. Which pass produced this file.
- **`timing`** — object, optional. `{wall_clock_seconds, tokens_in, tokens_out}`. `tokens_*` may be null if the agent runtime doesn't expose them.

## Validation rules (orchestrator-enforced)

On subagent exit, orchestrator checks:

1. JSON parses.
2. All required fields present.
3. `claim_id` matches the one assigned at dispatch.
4. `sub_claims` is non-empty.
5. Every `sub_claims[i].verdict` is a valid enum.
6. `overall_verdict` is consistent with `sub_claims[*].verdict` per the rollup rule.
7. `phrasings_tried` count meets the floor for the claim_type (≥3 for DIRECT/PARAPHRASED).
8. If any sub-claim is UNSUPPORTED / CONTRADICTED, `closest_adjacent` is non-empty.
9. If any sub-claim has `paper_value` ≠ `claim_value`, the sub-claim verdict is one of {OVERSTATED_MILD, OVERSTATED, OVERGENERAL} (not CONFIRMED).

Validation failure → one retry with a pointed failure message appended to the dispatch. Second failure → escalate to user as a `SCHEMA_VIOLATION` flag and keep the malformed output for inspection.

## Non-goals

- Not a manuscript-edit plan. Remediations are suggestions; the user applies them.
- Not a ranking across verdicts — `overall_verdict` is a roll-up, not a quality score.
- Not for tracking ledger history (use git for that).
