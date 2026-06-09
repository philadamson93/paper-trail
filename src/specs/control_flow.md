# Control flow — orchestrator → dispatch → subagent → validation map

Single source of truth for the agent graph behind `/paper-trail`: which orchestrator phase dispatches which prompt or script, which subagent emits which artifact, and which validation gates each artifact. A fresh agent picking up a feature plan traces pathways here instead of re-reading every prompt.

**No-drift constraint.** This file is the cross-cut, not the source. Validation cells link to `src/specs/verdict_schema.md` § "Validation rules (orchestrator-enforced)" by anchor — the bulleted rules, verdict enums, sub-claim shapes, and verifier `result` enums are never reproduced here. Any cell needing more than a sentence points at its source spec instead of expanding.

**Anchor convention.** Rows anchor to stable section headings in `src/commands/paper-trail.md`, not line numbers (line numbers shift on every prompt edit). To re-pin a heading to a current line: `grep -n "<heading text>" src/commands/paper-trail.md`.

## Pathway: orchestrator stages → dispatch / script / exit-validation

| Phase | Orchestrator anchor in `src/commands/paper-trail.md` | Call shape | Artifact (schema) | Exit validation |
|---|---|---|---|---|
| Preflight — dependency check | "Preflight — Dependency check" heading | In-orchestrator probes (read-only; no dispatch) | decisions recorded in `parse_report.md` | (none — blocking prompt on missing `pdftotext`) |
| Phase 0 — Bibliography extraction | "Phase 0 — Bibliography extraction" heading, Steps 0.0–0.5 | In-orchestrator parsing + CrossRef count cross-check | `refs.bib`, `parse_report.md` | Step 0.5 user confirmation gate (count reconciliation via `AskUserQuestion`) |
| Phase 1 — Verify bib | "Phase 1 — Verify bib" heading | One subagent per reference running `/verify-bib` per-entry logic (`src/commands/verify-bib.md`) | severity-classified findings; `refs.verified.bib` | Severity taxonomy per `/verify-bib`; CRITICAL entries never silently corrected |
| Phase 2 — Fetch PDFs | "Phase 2 — Fetch PDFs" heading | One subagent per citekey running `/fetch-paper` logic (`src/commands/fetch-paper.md`) | `pdfs/<citekey>.pdf` | Substitution candidates gated by `--fetch-substitute` policy; failures → `NEEDS_PDF` |
| Phase 2.5 — Ingest | "Phase 2.5 — Ingest" heading | `src/scripts/ingest_pdf.py --pdf <path>.pdf --citekey <citekey> --out-dir <output-dir>/pdfs/<citekey>/` (process-local, no subagent) | per-PDF handle (`src/specs/ingest.md`) | `ingest_report.json` `success` flag; `ingest_mode: error` → claims stubbed `PENDING`/`NEEDS_PDF` |
| Phase 3.1 — Claim extraction | "Step 3.1 — Claim extraction" heading + "Disambiguation heuristics" subsection | In-orchestrator prompt instructions (no subagent dispatch) | candidate-claim list `{claim_text, citekey, manuscript_section}` | (none — orchestrator-internal; Step 3.1.5 gates next) |
| Phase 3.1.5 — Pre-dispatch claim validator | "Step 3.1.5 — Validate extracted claims against the manuscript" heading | `src/scripts/validate_claims.py --run-dir <output-dir>` (reader) **or** `--run-dir <manuscript-dir> --manuscript-path <…>` (author) | `claim_extraction_report.md` | Script flags `TEXT_ANCHOR_MISSING` / `FRONT_MATTER_ANCHOR` / `CITEKEY_MARKER_MISMATCH`; non-zero exit pauses for user decision before Phase 3.2 |
| Phase 3.2 Pass 1 — Extractor | "Step 3.2 — Two-pass dispatch (extractor → adjudicator)" heading → "Dispatch inputs" payload, per-claim slot-fill and send | `src/prompts/extractor-dispatch.md` | `ledger/evidence/<claim_id>.json` | per `src/specs/verdict_schema.md` § Validation rules (orchestrator-enforced inline on each return; retry once, then `SCHEMA_VIOLATION`) |
| Phase 3.2 Pass 2 — Adjudicator | Same "Step 3.2" section, post-extractor slot-fill | `src/prompts/adjudicator-dispatch.md` | `ledger/claims/<claim_id>.json` | per `src/specs/verdict_schema.md` § Validation rules, incl. the rollup-consistency invariant (`overall_verdict` vs `sub_claims[*].verdict`) |
| Phase 3.3 — Ledger render | "Step 3.3 — Ledger rendering" heading | Derived-view re-render from `ledger/claims/*.json` | `ledger.md` | (idempotent re-render; not a validation gate) |
| Phase 3.5 — Verifier | "Phase 3.5 — Attestation verification (gating)" heading; "Sampling" + "Dispatch payload" subsections | `src/prompts/verifier-dispatch.md` | `ledger/verifications/<claim_id>__<sub_claim_id>.json` | `result` enum per verifier prompt (`PASS`/`PARTIAL`/`FAIL`) + `verdict_impact` handling; two-bounce ceiling then `AMBIGUOUS` + `SCHEMA_VIOLATION` |
| Phase 4 — Ambiguity triage | "Phase 4 — Ambiguity triage" heading | In-orchestrator `/ground-claim --triage` workflow inline | dated `history[]` notes on claim JSONs | user-adjudicated; no schema gate |
| Phase 5 — HTML render | "Phase 5 — Render HTML viewer" heading | `src/scripts/render_html_demo.py --run-dir <output-dir>` | `<output-dir>/demo.html` | Non-fatal warning on failure; canonical ledger artifacts unaffected |

**Where validation actually lives.** `validate_claims.py` is a **pre-dispatch manuscript validator** (checks that extracted claim text appears in the manuscript and that nearby citation markers match the assigned citekey) — it is *not* an exit-schema validator on subagent output. Exit-schema validation is in `src/specs/verdict_schema.md` § "Validation rules (orchestrator-enforced)" and is enforced inline by the orchestrator on each subagent return; no separate Python validator runs there.

## Pathway: dispatch slot map

Slots actually present in each dispatch prompt (re-enumerate with `grep -o '{{[a-z_]*}}' src/prompts/*.md | sort -u` after any prompt edit — a `plan-check` requirement). Source fields refer to the "Dispatch inputs" payload JSON in `src/commands/paper-trail.md` (Step 3.2) and the Phase 3.5 "Dispatch payload" JSON.

| Dispatch prompt | Slot | Source on orchestrator dispatch payload | Notes |
|---|---|---|---|
| `extractor-dispatch.md` | `{{claim_id}}` | payload `claim_id` | orchestrator-allocated before dispatch (`C001`, …) |
| `extractor-dispatch.md` | `{{run_id}}` | payload `run_id` | |
| `extractor-dispatch.md` | `{{citekey}}` | payload `citekey` | |
| `extractor-dispatch.md` | `{{claim_text}}` | payload `claim_text` | |
| `extractor-dispatch.md` | `{{manuscript_section}}` | payload `manuscript_section` | |
| `extractor-dispatch.md` | `{{co_citekeys}}` | payload `co_citekeys` (flat array) | extractor populates `evidence.co_cite_context.sibling_citekeys` |
| `extractor-dispatch.md` | `{{handle}}` | payload `handle` | local PDF-handle dir; becomes `paperclip_handle` for paperclip mode after `feature-paperclip-first-architecture.md` lands |
| `extractor-dispatch.md` | `{{ingest_mode}}` | payload `ingest_mode` | `grobid` / `pdftotext_fallback` / `ocr_fallback` — drives trust-adjusted confidence |
| `extractor-dispatch.md` | `{{run_output_dir}}` | payload `run_output_dir` | absolute |
| `extractor-dispatch.md` | `{{spec_root}}` | payload `spec_root` | paper-trail repo root (absolute); prompts reference specs as `{{spec_root}}/src/specs/<file>` so paths resolve regardless of subagent cwd |
| `adjudicator-dispatch.md` | `{{claim_id}}` | payload `claim_id` | |
| `adjudicator-dispatch.md` | `{{run_id}}` | payload `run_id` | |
| `adjudicator-dispatch.md` | `{{claim_text}}` | payload `claim_text` | |
| `adjudicator-dispatch.md` | `{{run_output_dir}}` | payload `run_output_dir` | adjudicator reads `ledger/evidence/<claim_id>.json` from here; no paper handle by design |
| `adjudicator-dispatch.md` | `{{spec_root}}` | payload `spec_root` | rubric path: `{{spec_root}}/src/specs/verdict_schema.md` |
| `verifier-dispatch.md` | `{{claim_id}}` | Phase 3.5 payload `claim_id` | |
| `verifier-dispatch.md` | `{{run_id}}` | Phase 3.5 payload `run_id` | |
| `verifier-dispatch.md` | `{{sub_claim_id}}` | derived: the sub-claim owning the sampled evidence entry | not a top-level payload field |
| `verifier-dispatch.md` | `{{sampled_evidence}}` | Phase 3.5 payload `sampled_evidence` (one entry) | sampling rules in "Phase 3.5 — Attestation verification" § Sampling |
| `verifier-dispatch.md` | `{{section}}` | derived: `sampled_evidence` section field | |
| `verifier-dispatch.md` | `{{line}}` | derived: `sampled_evidence` line/locator field | |
| `verifier-dispatch.md` | `{{handle}}` | Phase 3.5 payload `handle` | |
| `verifier-dispatch.md` | `{{run_output_dir}}` | Phase 3.5 payload `run_output_dir` | |

(The literal `{{slot}}` token also appears in `extractor-dispatch.md` prose as a generic placeholder example, not a fillable slot.)

## Pathway: skill auto-load triggers

| Skill (location) | Trigger condition | Used by |
|---|---|---|
| `src/skills/doc-split-check.md` | doc edit ≥ ~400 lines | manual + commit-review |
| `src/skills/plan-check.md` | new or substantially-edited plan doc in `docs/plans/` | manual + commit-review |
| `src/skills/paperclip/SKILL.md` (directory-shaped) | orchestrator/author invokes the paperclip read-path or pre-pulls preprint metadata | `feature-paperclip-first-architecture.md` workflow |

## Maintenance

- Any feature plan that touches the dispatch graph (new phase, new slot, new validator, changed artifact path) must update this file in the same change — this is a `plan-check` check item.
- Exit-validation semantics live in `src/specs/verdict_schema.md`; verifier `result`/`verdict_impact` semantics live in `src/prompts/verifier-dispatch.md` and the Phase 3.5 section of the orchestrator. Update there, not here.
