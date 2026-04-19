# Trust model

Every judgment step (reading, evidence extraction, verdict, remediation) is performed by an LLM — so the *process* around the LLM, not any single step, is what's designed for reliability. LLMs still make mistakes; the structure below is meant to reduce a few failure modes, not eliminate them.

- **Two-pass dispatch.** An extractor reads the ingested source and records evidence; a separate adjudicator reads only the evidence JSON + the rubric (no paper) and picks a verdict. Keeps each subagent's context narrow and decouples reading from classification.
- **Attestation.** Before any `UNSUPPORTED` or `CONTRADICTED` verdict, the extractor must record a section-by-section read checklist, ≥3 distinct phrasings searched, and the closest adjacent passage. No abstract-only shortcuts.
- **Independent verifier.** After adjudication, a third subagent sees only the claim + one sampled evidence entry + the rubric and confirms the excerpt exists in the source as recorded. `FAIL` bounces the claim back through extractor + adjudicator; `PARTIAL` adds an `UNVERIFIED_ATTESTATION` flag.
- **Structured exit JSON.** Every subagent's output is validated against a schema; malformed output retries once then escalates.
- **Configurable fetch substitution.** When a DOI is paywalled but a related preprint exists, `--fetch-substitute=<never|ask|always>` governs whether to accept the substitute; every substitution is logged in `parse_report.md` and in each downstream claim's attestation.

None of this makes a verdict authoritative — see [Cautions](../README.md#cautions) in the main README. Every flagged entry is a triage lead, not a conclusion.
