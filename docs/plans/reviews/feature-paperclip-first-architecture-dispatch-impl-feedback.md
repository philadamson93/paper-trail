Reference: docs/claude_ops.md

# Implementation Feedback: Paperclip-first architecture — Phase-3 dispatch wire-in

## Verdict

Revise before commit. The main branch selection and schema 1.1 fields are mostly wired, but the verifier dispatch has unresolved slot/payload mismatches, and the mode-blind adjudicator guardrail from the plan is not present even though `source_mode` now rides inside the evidence JSON the adjudicator reads.

## Plan Coverage

| Item | Status | Evidence: path:line | Notes |
|---|---|---|---|
| Dispatch payload includes `source_mode` and `paperclip_handle` | Done | `src/commands/paper-trail.md:421` | Payload example includes both at `src/commands/paper-trail.md:429` and `src/commands/paper-trail.md:431`. |
| Source-mode derivation from coverage + ingest mode | Done | `src/commands/paper-trail.md:439` | Matches plan: `coverage=paperclip` -> `source_mode=paperclip`, PDF ingest modes -> `pdf` / `pdf_ocr_fallback`, paperclip leaves `handle` and `ingest_mode` null. |
| Extractor prompt selected by `source_mode` | Done | `src/commands/paper-trail.md:439` | Selects `extractor-dispatch-paperclip.md` for paperclip and `extractor-dispatch-pdf.md` for PDF modes. |
| Verifier payload extended with `source_mode` / `paperclip_handle` | Partial | `src/commands/paper-trail.md:486` | New fields are present, but verifier slots `{{sub_claim_id}}`, `{{section}}`, and `{{line}}` are still not in the payload example. |
| Paperclip extractor prompt honors schema 1.1 | Done | `src/prompts/extractor-dispatch-paperclip.md:71` | Emits `source_mode=paperclip`, sets `paperclip_handle`, and leaves `handle` absent/null and `ingest_mode` null at `src/prompts/extractor-dispatch-paperclip.md:73`. |
| Paperclip `map --from` contract | Done | `src/prompts/extractor-dispatch-paperclip.md:45` | Explicitly says `map --from` consumes a search-results id, not a bare handle. |
| Replayable evidence locator hard rule | Done | `src/prompts/extractor-dispatch-paperclip.md:52` | Hard rule requires every persisted evidence item to carry replayable `locator` + verbatim `snippet`. |
| Paperclip extractor leaves verdict to adjudicator | Done | `src/prompts/extractor-dispatch-paperclip.md:13` | Repeated in output contract and Do-not section at `src/prompts/extractor-dispatch-paperclip.md:76` and `src/prompts/extractor-dispatch-paperclip.md:83`. |
| PDF extractor rename and schema 1.1 echo | Done | `src/prompts/extractor-dispatch-pdf.md:1` | Retitled as PDF mode; emits `source_mode`, `handle`, `ingest_mode`, and null/absent `paperclip_handle` at `src/prompts/extractor-dispatch-pdf.md:61`. |
| Verifier paperclip command allowance | Partial | `src/prompts/verifier-dispatch.md:32` | Allows `paperclip cat` / `paperclip grep`, but also permits grep by `"<phrase>"` without a recorded query in the payload. |
| Control-flow dispatch graph updated | Done | `src/specs/control_flow.md:20` | Phase 3.2 cell names both extractor prompts and source-mode selection. |
| Control-flow slot map no drift | Partial | `src/specs/control_flow.md:56` | Documents verifier-derived slots, but `paper-trail.md` only says it fills the JSON payload keys. |
| Ground-claim mode-aware workflow doc | Done | `src/commands/ground-claim.md:48` | Adds mode section and preserves shared Pass 1 / Pass 2 / Pass 3 skeleton. |

## Critical Drift

- The adjudicator guardrail required by the plan is missing. The plan says `source_mode` is carried as inert evidence metadata and "the one guardrail is a single line in the adjudicator prompt stating that `source_mode` must not influence the verdict" (`docs/plans/feature-paperclip-first-architecture.md:176`). The adjudicator still reads the whole evidence JSON (`src/prompts/adjudicator-dispatch.md:19`, `src/prompts/adjudicator-dispatch.md:25`) but has no instruction to ignore `source_mode`; meanwhile the schema says `source_mode` must not bias the verdict (`src/specs/verdict_schema.md:116`, `src/specs/verdict_schema.md:203`). This is a real mode-blindness gap because `source_mode` is now present in extractor output (`src/prompts/extractor-dispatch-paperclip.md:73`, `src/prompts/extractor-dispatch-pdf.md:61`).

## Missing Pieces

- `extractor-dispatch-paperclip.md` still contains a stale "Wiring status" note claiming the prompt is dormant and "referenced by no phase" (`src/prompts/extractor-dispatch-paperclip.md:5`). The wire-in now explicitly references and selects it (`src/commands/paper-trail.md:439`, `src/specs/control_flow.md:20`). This is not runtime-breaking, but it is contradictory operational guidance in a literal dispatch prompt file.

## Contract Violations

- The verifier's paperclip replay language is looser than the deterministic-locator contract. The plan requires re-running the same paperclip attestation, not a fresh search (`docs/plans/feature-paperclip-first-architecture.md:137`), and the schema defines `locator` as the deterministic replay pointer (`src/specs/verdict_schema.md:131`). The prompt says to re-run the exact locator, but then permits `paperclip grep -i "<phrase>" {{paperclip_handle}}content.lines` (`src/prompts/verifier-dispatch.md:34`) without any recorded grep phrase in the payload. That can become a fresh search unless constrained to text from `sampled_evidence.locator` / `sampled_evidence.snippet`.

## Slot / Payload Mismatches

- `verifier-dispatch.md` reads `{{sub_claim_id}}`, `{{section}}`, and `{{line}}` (`src/prompts/verifier-dispatch.md:28`, `src/prompts/verifier-dispatch.md:33`, `src/prompts/verifier-dispatch.md:50`), but the Phase 3.5 payload example only supplies `claim_id`, `run_id`, `sampled_evidence`, `source_mode`, `handle`, `paperclip_handle`, and `run_output_dir` (`src/commands/paper-trail.md:486`). `control_flow.md` calls these derived fields (`src/specs/control_flow.md:58`), but `paper-trail.md` says the orchestrator fills the verifier prompt "with these slots" from the payload (`src/commands/paper-trail.md:498`). Either add the derived keys to the payload contract or state in `paper-trail.md` that the orchestrator derives/fills them from `sampled_evidence`.

- The paperclip slot map is compressed rather than enumerated. `extractor-dispatch-paperclip.md` reads the same shared slots as the PDF prompt plus `{{paperclip_handle}}` (`src/prompts/extractor-dispatch-paperclip.md:17` through `src/prompts/extractor-dispatch-paperclip.md:33`), while `control_flow.md` lists only combined/prose rows for most paperclip slots (`src/specs/control_flow.md:47`, `src/specs/control_flow.md:69`). It is probably accurate, but weaker than the "slot-map rows" requirement because a direct row-by-row audit misses paperclip `{{claim_id}}`, `{{run_id}}`, `{{citekey}}`, `{{claim_text}}`, `{{manuscript_section}}`, `{{claim_type_hint.*}}`, `{{co_citekeys}}`, `{{run_output_dir}}`, and `{{spec_root}}`.

## Defensible Deviations

- `pdf_ocr_fallback` is selected as a source mode while preserving `ingest_mode: ocr_fallback` (`src/commands/paper-trail.md:439`). This matches the plan's naming pin and schema split.
- PDF-mode evidence locators are optional in the PDF extractor (`src/prompts/extractor-dispatch-pdf.md:61`). That matches schema 1.1, where evidence-item `locator` is optional/additive (`src/specs/verdict_schema.md:131`), while the stronger replayable-locator hard rule is only required for persisted paperclip evidence in this increment.
- The old `src/prompts/extractor-dispatch.md` file is gone from `src/prompts/`, and the remaining source references to the old name are either the stale paperclip note or historical plan text. No live `src/commands` / `src/specs/control_flow.md` reference still dispatches the old filename.

## Suggested Code Edits

- Add the adjudicator guardrail line to `src/prompts/adjudicator-dispatch.md`: `source_mode` / `paperclip_handle` / `locator` provenance must not affect verdict selection; apply the same rubric regardless of read path.
- In `src/commands/paper-trail.md` Phase 3.5 payload, include explicit `sub_claim_id`, `section`, and `line`, or document that they are derived from `sampled_evidence` and filled as slots before dispatch.
- Tighten verifier paperclip replay to prefer `paperclip cat <locator-file>` + line extraction from `sampled_evidence.locator`; only allow grep against the recorded snippet/locator when the locator cannot be line-read, not arbitrary new phrasing.
- Remove or update the stale "Wiring status" block in `src/prompts/extractor-dispatch-paperclip.md`.
- Expand `control_flow.md` paperclip slot rows so the paperclip prompt can be audited mechanically, not by prose inheritance from the PDF variant.

## Questions For The Author

- Should paperclip closest-adjacent attestations also be represented as structured evidence-like objects with `locator`, or is the current string field in `attestation.closest_adjacent` intentionally sufficient for verifier replay?
- Does the real orchestrator slot-filler support derived verifier slots from `sampled_evidence`, or does it only substitute keys present in the Phase 3.5 payload object?

## Audit Trail

- Read `docs/claude_ops.md`.
- Read relevant plan sections: Implementation surface, Phase 3, Phase 3.5, dispatch-payload derivation, map/verifier open-question resolutions.
- Read committed schema contract in `src/specs/verdict_schema.md`.
- Ran `git diff` for the scoped modified files.
- Read `src/prompts/extractor-dispatch-paperclip.md` in full.
- Enumerated prompt slots with `grep -o '{{[^}]*}}'` because `rg` is not installed in this sandbox.
- Checked for dangling live references to `extractor-dispatch.md`; only the stale paperclip note and historical plan text remain.

## Resolution (Claude, 2026-06-27)

All findings agreed with and applied:
- **Critical (adjudicator guardrail missing):** added the OQ7 guardrail to `adjudicator-dispatch.md` step 1 — `source_mode` / `paperclip_handle` / `locator` are provenance and must not influence the verdict; identical rubric regardless of read path.
- **Missing (stale "Wiring status" note):** replaced the dormant-prompt blockquote in `extractor-dispatch-paperclip.md` with an accurate "Wiring" note (selected when `source_mode==paperclip`; points at paper-trail.md § 3.2 + control_flow.md).
- **Contract (loose verifier replay):** tightened the paperclip branch — line-read the recorded locator; `paperclip grep` allowed only with a fixed string taken verbatim from `sampled_evidence.snippet`, never a new phrasing.
- **Slot/payload (verifier derived slots):** documented in `paper-trail.md` Phase-3.5 that `{{sub_claim_id}}` / `{{section}}` / `{{line}}` are derived from `sampled_evidence` (not separate payload keys; for paperclip, from the evidence `locator`).
- **Slot/payload (compressed paperclip slot-map):** enumerated every shared paperclip slot explicitly in `control_flow.md` so a `grep -ho '{{[^}]*}}'` audit reconciles row-for-row (chose explicit enumeration over 10 duplicate table rows to keep the spec terse).

Author Questions:
- **closest_adjacent structure:** keep `attestation.closest_adjacent` a string (schema 1.0/1.1) with the replayable locator embedded in the text — sufficient for the rare no-evidence verifier-replay case in v1; no schema change.
- **Derived verifier slots:** yes — the orchestrator extracts `sub_claim_id`/`section`/`line` from `sampled_evidence` before substitution (now documented).
