# Verifier results — Phase 3.5 attestation-verification contract

Contract of record for the Phase 3.5 verifier's output artifact and for how the orchestrator acts on it. The dispatch prompt (`src/prompts/verifier-dispatch.md`) embeds a copy of the output shape because the subagent must receive its instructions verbatim — when editing either file, keep the two in sync (this spec wins on disagreement).

## Artifact

One JSON file per verified claim, at `<output-dir>/ledger/verifications/<claim_id>__<sub_claim_id>.json`:

```json
{
  "claim_id": "C042",
  "sub_claim_id": "C042.a",
  "run_id": "run_20260418T1522Z",
  "stage": "verification",
  "sample_type": "grep_hit" | "figure" | "attestation_log",
  "result": "PASS" | "PARTIAL" | "FAIL",
  "sampled": { "...": "the sampled_evidence input, echoed" },
  "observed": {
    "at_claimed_location": "<what was actually at the line/section>",
    "numerical_match": true,
    "note": "<short human-readable observation>"
  },
  "verdict_impact": "none" | "bounce_to_re_ground" | "flag_unverified_attestation"
}
```

(`observed.numerical_match` is `true | false | null` — `null` when the sub-claim carries no `paper_value` to check.)

## `result` semantics

- **PASS** — the source at the claimed location contains the claimed snippet (exact or near-exact; minor whitespace / hyphenation normalization OK).
- **PARTIAL** — the location exists and is related, but the specific words the extractor quoted aren't verbatim there.
- **FAIL** — the claimed location doesn't contain the snippet at all (wrong line, wrong section, or fabricated).

Figure-derived evidence is out of scope for the text verifier: `sample_type: "figure"` returns PASS with a "skipped" note.

## `verdict_impact` → orchestrator handling

- **`none`** (PASS) — verdict stands; no action.
- **`flag_unverified_attestation`** (PARTIAL) — patch the verdict JSON's `overall_flag` to include `UNVERIFIED_ATTESTATION`. The verdict itself is unchanged.
- **`bounce_to_re_ground`** (FAIL) — re-dispatch the claim through extractor + adjudicator and increment the claim's `attempts`. **Two-bounce ceiling:** after 2 bounces, stop and flag the claim `AMBIGUOUS` with `SCHEMA_VIOLATION` (a repeat FAIL suggests a systematic extractor issue, not a one-off).

The verifier never rewrites verdicts directly — it flags or bounces; the adjudicator owns verdicts.

## Defaults

Verify every adjudicated claim in v1, including `CONFIRMED` (a falsely-confirmed claim is as dangerous as a falsely-denied one). A `--verify-sample-rate=<pct>` downgrade may be added later on cost data; not a v1 default.
