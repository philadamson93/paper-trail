# Feature plan — paperclip-first architecture

**Status.** Plan-only. To-do for upcoming feature work on `feature/paperclip-primary-workflow`. No code yet.

**Provenance.** Scoped 2026-05-01 after the upstream paperclip team announced full-text arXiv coverage and an abstract-only PubMed corpus. Coverage probe re-measured the same day on the canonical `examples/paper-trail-adamson-2025/` fixture; results in `experiments/paperclip-coverage-2026-05-01/` (gitignored). Decision-log entry to be written in `docs/journal/2026-05-01-paperclip-coverage-revisit.md`.

**Supersedes.** The 2026-04-18 reversal recorded in user memory `project_paperclip_primary.md` and the in-repo plan `docs/plans/add-paper-trail-orchestrator.md`'s implicit PDF-centric default. The previously-archived `~/.claude/plans/shiny-juggling-fountain--v1-paperclip-primary-ARCHIVED.md` (out-of-repo) anticipated this design; the changes here adapt it to the post-2026-05-01 paperclip corpus and to the `verdict_schema.md` / dispatch-template structure paper-trail has shipped since then.

---

## Headline rationale

The April 2026 reversal hinged on one number: ~15% greppable full-text coverage on the canonical fixture, of which ~5–6% was real (the rest were arxiv abstract-only entries that looked like hits in the SQL but couldn't be grepped for evidence). The March/April spike report concluded a mixed-path architecture (paperclip-when-hit, PDF-otherwise) doubled implementation surface for too small a coverage lift.

The May 1 2026 re-probe — same fixture, same probe shape, post-arxiv-fulltext — measures **27/56 (48%) greppable full-text** on a worst-case fixture (medical imaging plus pre-2010 image-quality classics, both arxiv-unfriendly slices). That number is roughly **4× the April baseline**, and a more arxiv-friendly fixture (recent CS / ML refs) is expected to clear 70%+.

**Human:** "i think we aim paperclip first. even with PDF fallback it requires manual download of PDFs that are paywalled which is a limitation anyways. We dont need a perfect tool, we need a helpful one."

**Agent:** That framing settles the question of whether mixed-path is acceptable. The PDF-centric path already requires manual intervention for paywalled references (the existing paywall-fallback flow). Paperclip-first does not introduce a new failure mode — it shrinks the slice of references that hit the existing one. With ~50% of references newly addressable server-side at the worst-case fixture, the implementation cost of the second path is paid back by half the references becoming fetch-free, parse-free, and grep-fast.

---

## Implementation surface

Concrete edits-list and pinned design decisions. Treat as authoritative over the more abstract architectural prose below.

**Files to edit:**

- `.claude/commands/paper-trail.md` — Phases 1, 2, 2.5, 3, 3.5. Specifically:
  - Phase 1 (`/verify-bib` invocation, around line 200ish — re-locate at implementation time): add a paperclip-lookup pre-step before the CrossRef → arXiv → Semantic Scholar chain. Marks each reference's `coverage` field as `paperclip` / `external` / `unresolved`.
  - Phase 2 (`/fetch-paper` invocation, around line 230ish): make coverage-aware. Skip PDF download for `coverage: paperclip` references; existing path for `external`; flag `unresolved` for user triage as today.
  - Phase 2.5 (GROBID ingest): unchanged in shape, but only runs over the PDFs that actually got fetched (i.e., the `external` slice).
  - Phase 3 (per-claim two-pass dispatch, around line 315 onward): branch on the reference's `source_mode` field. Paperclip-mode subagents use the new dispatch prompt and operate on `/papers/<doc_id>/` handles via `paperclip` CLI primitives. PDF-mode subagents continue to use the existing dispatch flow over `pdfs/<citekey>/` GROBID-parsed handles.
  - Phase 3.5 (verifier): unchanged in shape; verifier picks an attestation line and re-checks it. For paperclip-mode entries, this is a `paperclip grep` re-run; for PDF-mode entries, the existing local re-grep.
  - End-of-run summary: add per-source-mode counts so `paperclip` / `external` / `unresolved` slices are reportable separately.
- `.claude/commands/ground-claim.md` — per-claim workflow doc. Add a Mode section near the top distinguishing paperclip-mode vs PDF-mode workflows, sharing the same Pass 1 / Pass 2 / Pass 3 (verifier) skeleton and the same exit JSON schema. Existing multi-cite handling (`co_cite_context.sibling_citekeys`) carries over unchanged — the sibling list is computed at extraction time from `\cite{a,b,c}` and is mode-agnostic.
- `.claude/commands/verify-bib.md` — Phase 1 helper. Adds the paperclip-lookup pre-step. Falls back to the existing CrossRef → arXiv → Semantic Scholar chain on miss. The paperclip `abstracts` source (description: "Title + abstract corpus, broader coverage, no full text") is useful here as an identity-resolution helper for paywalled references that have a PubMed entry — it is **not** useful for grounding.
- `.claude/commands/fetch-paper.md` — Phase 2 helper. Becomes coverage-aware (skip in-corpus references). Existing PDF-download path unchanged for the `external` slice.
- `.claude/specs/verdict_schema.md` — additive 1.1 → 1.2 bump. New top-level `source_mode` enum field on the verdict envelope: `paperclip` | `pdf` | `pdf_ocr_fallback`. New `paperclip_handle` field on the per-reference metadata (the `/papers/<doc_id>/` directory name). New `attestation` shape variants for paperclip-mode (server-side grep hits with `L<n>` line citations) versus PDF-mode (existing local-page citations).
- `.claude/prompts/extractor-dispatch.md` — split into two variants: `extractor-dispatch-paperclip.md` (new) and `extractor-dispatch-pdf.md` (rename of current). Orchestrator picks based on `source_mode`. Both produce the same evidence-JSON shape, differing only in the read primitives (`paperclip grep / cat / scan` vs `rg / pdftotext`).
- `.claude/prompts/adjudicator-dispatch.md` — unchanged in shape (adjudicator is blind to the read mode). Confirm by re-reading: the adjudicator should not need to know whether evidence came from paperclip or PDF.
- `.claude/prompts/verifier-dispatch.md` — minor: verifier picks one attestation line and re-checks it; if `source_mode: paperclip`, re-runs `paperclip grep` instead of local `rg`.
- `.claude/skills/paperclip/SKILL.md` — refresh from upstream via `paperclip install --dir .`. Currently stale (still describes corpus as "PMC + bioRxiv + medRxiv" with no arXiv or PubMed-abstract surface, and references commands the 0.3.0 CLI no longer exposes the same way). The refresh is a prerequisite for any paperclip-mode dispatch prompt to work — subagents read this skill, not memory.
- `.claude/scripts/render_html_demo.py` — add a `source_mode` badge per claim row so the user can see at a glance which references were grounded via paperclip vs PDF. Color-key for visual scan.
- `.claude/scripts/validate_claims.py` — add a `SOURCE_MODE_MISSING` validation if a verdict envelope lacks the new `source_mode` field after the 1.2 schema bump. Existing `CITEKEY_MARKER_MISMATCH` validation is unaffected.
- `templates/claims_ledger.md` — add a `source_mode` column to the per-claim table render and document the three-value enum near the top.
- **Dispatch payload JSON in `paper-trail.md` (around line 396, the per-claim dispatch block):** add `source_mode` and `paperclip_handle` fields to the orchestrator's per-claim dispatch payload. Without these, the new paperclip-mode extractor cannot know which mode to run in or which `/papers/<doc_id>/` to read from. This is in addition to the dispatch-prompt files listed above — the JSON payload and the `{{slot}}` placeholders are separate surfaces and both need updating.
- **Slot placeholders in dispatch prompts:** new `{{source_mode}}` and `{{paperclip_handle}}` slots in `extractor-dispatch-paperclip.md` (read by the paperclip-mode extractor); the PDF-mode variant only needs `{{source_mode}}` (already has `{{handle}}` which is the local PDF path).

**New files to create:**

- `.claude/prompts/extractor-dispatch-paperclip.md` — paperclip-mode extractor dispatch. Uses `paperclip grep` / `paperclip cat /papers/<doc_id>/sections/<name>.lines` / `paperclip ask-image /papers/<doc_id>/figures/<file>` as the read primitives. Same evidence-JSON exit schema as the PDF variant.

**Naming and shape pins:**

- **`source_mode` enum:** `paperclip` | `pdf` | `pdf_ocr_fallback`. The `pdf_ocr_fallback` value is reserved for image-only PDFs where GROBID failed; today these flow through Phase 2.5 as `ingest_mode: ocr_fallback`. Renaming to `pdf_ocr_fallback` here aligns the Phase 2.5 mode and the Phase 3 source_mode under one vocabulary.
- **`coverage` field on the verified-bib metadata:** `paperclip` | `external` | `unresolved`. This is what Phase 1 emits and Phase 2 / Phase 3 consume.
- **`paperclip_handle` field:** the `/papers/<doc_id>/` directory name as paperclip surfaces it (e.g., `PMC10131505` for a PMC ID, `2407.11321` for an arXiv ID, `bio_<uuid>` for bioRxiv). The orchestrator stores this on the verified-bib metadata so subagents can read it without re-querying.
- **`--paperclip=<mode>` flag:** values `prefer` (the shipped default — paperclip in-corpus, PDF for `external`, user-triage for `unresolved`), `only` (abort on `external`; useful for pure-biomed audits), `never` (force the existing PDF path; useful while migrating or for fixtures that paperclip handles poorly), `off` (paperclip unavailable / unauthed; equivalent to `never` with a startup warning).

**Pinned design decisions** (from the May 1 discussion):

- **Paperclip-first is the shipped default.** No shadow-run phase, no opt-in flag for users who want it. `--paperclip=prefer` is the default; users who want the old behavior pass `--paperclip=never`.
- **Mixed-path is the reality, not a temporary state.** The architecture commits to two subagent dispatch prompts (paperclip and PDF) with one shared exit schema. The `external` slice is not a deprecation target — paywalled MRM / IEEE TMI references will not deposit to arxiv, and the existing PDF path remains the right way to handle them.
- **Abstracts source is a Phase-1 helper, not a Phase-3 source.** The new `abstracts` corpus paperclip 0.3.0 ships is explicitly described as "no full text." It can help bib verification and identity resolution (catching wrong-paper citations where the abstract makes clear the paper is about a different topic) but cannot ground a claim. Phase 3 never reads from `abstracts`.
- **Authentication failure is non-fatal.** If `paperclip config` shows the user is not signed in, the run proceeds in `--paperclip=off` mode with a one-line warning. The product remains useful without paperclip (parity with today's PDF-centric path).
- **No back-compat for the schema bump.** Per memory `feedback_rework_for_quality.md` ("refactors are welcome if they improve the product"), the 1.1 → 1.2 schema bump is hard. Old verdict files without `source_mode` will fail validation; users re-run paper-trail to regenerate. No migration shim.

**Coordination with the other in-flight feature branch:** `feature/multi-cite-and-neighbor-claims` (Features 1 + 2 from the 2026-04-29 pivot — joint multi-citation verdicts and ±1-sentence neighbor inference) also touches `paper-trail.md` Phase 3 and the dispatch prompts. If both branches are in flight at the same time, sequence them: land Features 1 + 2 first (they share a smaller schema delta — additive 1.0 → 1.1) so the paperclip-first branch rebases onto a stable per-ref + joint dispatch shape, then bumps the schema again to 1.2. Both branches add fields to the same `paper-trail.md` line 396 dispatch payload; the rebase will need a careful three-way merge.

**Smoke-test fixture layout:** `examples/paper-trail-adamson-2025/` (canonical M1 reference run per memory `project_m1_complete.md`). Re-running paper-trail on this fixture in `--paperclip=prefer` mode should produce ~27/56 references via paperclip-mode and ~29/56 via PDF-mode (or paywall-flagged), with the same per-claim verdicts as today's PDF-centric run on the references that were already grounded in M1. Diff per-claim verdicts against the M1 baseline (`examples/paper-trail-adamson-2025/data/claims/`); the verdicts must agree for any reference where M1 had a non-PENDING verdict, with mode-of-grounding being the only orthogonal change.

---

## Codebase pointers for fresh agents

When picking up this plan and starting implementation, the relevant files to read first:

- **Orchestrator (slash-command prompt):** `.claude/commands/paper-trail.md` — phases 0-5, 698 lines. The bulk of the changes land here. Phase 1 verify-bib, Phase 2 fetch-paper, Phase 2.5 ingest, Phase 3 per-claim dispatch, Phase 3.5 verifier all need updates per the implementation surface above.
- **Per-claim workflow:** `.claude/commands/ground-claim.md` — per-claim two-pass workflow, 172 lines. Adds a Mode section. Existing multi-cite handling (`co_cite_context.sibling_citekeys`) carries over unchanged.
- **Verdict schema:** `.claude/specs/verdict_schema.md` — source-of-truth contract. The 1.1 → 1.2 bump is the single largest schema change in the plan; read this whole file before implementing schema changes.
- **Subagent dispatch prompts:** `.claude/prompts/extractor-dispatch.md`, `.claude/prompts/adjudicator-dispatch.md`, `.claude/prompts/verifier-dispatch.md` — the literal prompts subagents receive. The extractor split into paperclip-mode and PDF-mode is the most prompt-heavy change.
- **Paperclip skill:** `.claude/skills/paperclip/SKILL.md` — currently stale; refresh first via `paperclip install --dir .`. The refresh affects what primitives the new paperclip-mode extractor can call.
- **Existing reader-mode fixture:** `examples/paper-trail-adamson-2025/data/claims/` — 87 baseline claim JSONs, the M1 regression base. Use as the smoke-test target.
- **Existing author-mode fixture:** `examples/DFD_authormode/ledger/claims/` — modern-layout author-mode example. Use to confirm author-mode parity (the plan applies equally to author and reader modes).
- **The current PDF-centric plan it supersedes:** `~/.claude/plans/shiny-juggling-fountain.md` (out-of-repo, in user home directory). Has the architectural prose for the PDF-centric M1 design that paperclip-first now sits beside as the second mode. The archived v1-paperclip-primary plan in the same directory has the original architectural sketch for paperclip-first.

---

## Phase-by-phase changes

### Phase 0 — input PDF parse (unchanged)

Extract bibliography from the user's input PDF. `pdftotext` → heuristic ref parsing → CrossRef cross-check → emit `refs.bib` + `parse_report.md`. Paperclip is corpus-side; it does not help parse the user's manuscript.

### Phase 1 — `/verify-bib` (paperclip-aware)

For each reference, in order:

1. Try paperclip exact-DOI lookup (PMC + bioRxiv + medRxiv). If hit, mark `coverage: paperclip`, store `paperclip_handle` (the `/papers/<doc_id>/` directory name), record metadata diffs against what we extracted from the input PDF the same way we record CrossRef diffs today.
2. If miss, try paperclip title-search against arXiv (the search command, not lookup-title — search is more permissive and handles arxiv preprints that share titles with their journal versions). Filter results by normalized-title overlap (≥0.6) and ±2-year publication-date sanity. If hit, mark `coverage: paperclip`.
3. If miss, try paperclip `abstracts` source for identity resolution help (catching wrong-paper citations or refining metadata). If hit, mark `coverage: external` (paperclip can't ground but can help verify) and pass through to the next step.
4. Fall back to today's CrossRef → arXiv-API → Semantic Scholar chain. Mark `coverage: external` or `coverage: unresolved`.

Emit `refs.verified.bib` with the new fields. Emit a Phase-1 summary line: `verified: 56/56 (paperclip:27, external:24, unresolved:5)`.

### Phase 2 — `/fetch-paper` (coverage-aware)

For each reference, branch on `coverage`:

- `paperclip` → skip download. The paper never hits disk. Pass through to Phase 3 with the `paperclip_handle`.
- `external` → existing download path (paper-search MCP → PapersFlow → CrossRef OA → arXiv API). Save to `pdfs/<citekey>.pdf`. On paywall, flag for user triage as today.
- `unresolved` → skip; flag for user triage at end of run.

This is where the "performance may degrade" warning surfaces. If a reference falls to `external` + paywall, the user gets the existing manual-download dance. **Per the May 1 discussion, this is not a regression — the existing PDF-centric path has the same dance for paywalled references. Paperclip-first does not introduce new manual steps; it shrinks the slice that has them.**

### Phase 2.5 — Ingest (PDF-only)

Only runs over PDFs that actually got fetched (the `external` slice). GROBID + figure extraction unchanged. Cache ingest artifacts; skip on re-run.

If GROBID fails (image-based PDF, odd layout), fall back to `pdftotext` + tesseract OCR and mark the entry `ingest_mode: ocr_fallback`. Phase 3 reads this mode and propagates it to the verdict envelope's `source_mode` as `pdf_ocr_fallback` (lower confidence weighting in the adjudicator's prompt).

### Phase 3 — `/ground-claim` (mode-aware)

The orchestrator dispatches Pass 1 (extractor) and Pass 2 (adjudicator) per `(claim, citekey)` pair as today. The new branch is in extractor selection:

- `source_mode: paperclip` → dispatch with `extractor-dispatch-paperclip.md`. Subagent operates on `/papers/<paperclip_handle>/` via `paperclip` CLI primitives: read meta.json, list sections, run `paperclip grep` with ≥3 phrasings, optionally `paperclip ask-image` on figures, optionally `paperclip map` over sibling handles for multi-cite reasoning.
- `source_mode: pdf` or `pdf_ocr_fallback` → dispatch with `extractor-dispatch-pdf.md` (current extractor-dispatch.md, renamed). Existing local-rg / pdfplumber-figure-crops workflow. Unchanged in shape.

Both extractors produce the same evidence-JSON shape (per `verdict_schema.md` 1.2). The Pass-2 adjudicator is mode-blind: it reads the evidence JSON plus the rubric and emits a verdict, never knowing whether evidence came from paperclip or PDF.

Multi-cite handling (`co_cite_context.sibling_citekeys`) carries over unchanged. The extractor populates it from the orchestrator's flat `co_citekeys` slot; mode does not affect this.

### Phase 3.5 — verifier (mode-aware)

Verifier picks one attestation line and re-checks it. If `source_mode: paperclip`, re-runs the same `paperclip grep` against the same handle. If `source_mode: pdf*`, re-runs the existing local re-check. The verifier's exit shape is mode-agnostic.

### Phase 4 — triage (unchanged)

Interactive AMBIGUOUS triage. Mode-blind.

### Phase 5 — render (mode-aware HTML)

Add `source_mode` badge per claim row in the HTML renderer. Color-key: paperclip = green, pdf = blue, pdf_ocr_fallback = yellow (lower confidence visual signal).

---

## Schema changes

`.claude/specs/verdict_schema.md` 1.1 → 1.2 bump:

**New top-level fields on the verdict envelope:**

- `source_mode`: enum `paperclip` | `pdf` | `pdf_ocr_fallback`. Required.
- `paperclip_handle`: string, present iff `source_mode == "paperclip"`. The `/papers/<doc_id>/` directory name.

**New attestation shape variant for paperclip-mode:**

Existing `attestation.hits[]` shape is reused. Per-hit fields adapt:

- `pattern`: the grep pattern that matched (unchanged).
- `paperclip_snippet`: replaces `pdf_excerpt`. The matched text from `paperclip grep`.
- `location`: `/papers/<doc_id>/sections/<name>.lines#L<n>` for paperclip-mode, `pdfs/<citekey>.pdf#page=<n>` for PDF-mode.
- `figures_checked[]`: each item has `figure_id`, `figure_path` (`/papers/<doc_id>/figures/<file>` or `pdfs/<citekey>/figures/<file>`), `ask_image_summary`.

**Validation rule additions** (`.claude/scripts/validate_claims.py`):

- `SOURCE_MODE_MISSING` — verdict envelope lacks `source_mode`.
- `PAPERCLIP_HANDLE_MISMATCH` — `source_mode == "paperclip"` but no `paperclip_handle`, or vice versa.

---

## Open questions

1. **Repo concept (paperclip 0.3.0):** the new `paperclip init <topic>` / `paperclip checkout <topic>` workflow scopes subsequent paperclip queries to a "repo" of papers. Should one paper-trail run = one paperclip repo (auto-init at Phase 1, all Phase-3 queries scoped to it)? Pros: cleaner provenance, paperclip can amortize work across the run. Cons: extra setup the user might not want; unclear interaction with `paperclip --no-repo` escape. Discover empirically — try both shapes in the smoke test.
2. **Sibling co-citation handling — `paperclip map` or per-citekey loop?** Today the orchestrator dispatches one extractor-adjudicator chain per `(claim, citekey)` pair, with multi-cite siblings flowing through `co_cite_context.sibling_citekeys`. Paperclip's `map` primitive could fan out a single "does this paper support <claim>?" query across N sibling handles in one call. Open: is `map` reliable enough to replace the per-citekey loop, or should it be an optional accelerator inside the per-citekey extractor for multi-cite sentences? Default to per-citekey loop in v1 (parity with PDF mode); revisit `map` after smoke test.
3. **Verifier — re-grep or LLM-based check?** Today's verifier picks an attestation line and re-checks the source. Paperclip's `paperclip grep` re-run is deterministic (same query → same hits) so the verifier becomes near-trivial. Should it stay deterministic, or should we keep an LLM-based judgment layer for nuance (e.g., does the snippet *actually* support the claim, vs just match keywords)? Default to deterministic re-grep in v1; LLM-based layer is a separate `verifier-dispatch.md` change orthogonal to this plan.
4. **Authentication startup probe:** Phase 0 should call `paperclip config` and check the `Auth: ✓` line. If unauthed, the run goes straight to `--paperclip=off`. Open: should the warning be one line at the start of the run, or should the user be prompted to run `paperclip login` interactively? Default to one-line warning + auto-fall-back-to-PDF; user can re-run after login. Per memory `feedback_author_mode_always_ask_path.md` we don't silently probe; same principle here — the warning surfaces the state.
5. **`abstracts` source in Phase 1 — opt-in or default?** Identity resolution via `abstracts` could surface wrong-paper citations the CrossRef chain misses. Default to default-on; cost is one extra paperclip query per Phase-1 reference (sub-second).

---

## Out of scope

- **Parallel optimization (lift M1 serial to M2 parallel).** Per memory `feedback_serial_then_parallel.md`, harden the serial path first. Parallelism is a separate plan after this lands.
- **Replacing the PDF-centric path entirely.** The `external` slice (paywalled MRM / IEEE TMI references) is permanent. PDF mode is not a deprecation target.
- **Citation hygiene checks beyond what the existing rubric does.** This plan is a read-path change, not a rubric change.
- **`paperclip map` as the dominant fan-out primitive.** Investigated as Open Question 2 but not committed in v1.
- **Author-mode-only or reader-mode-only behavior differences.** The plan applies symmetrically to both modes. Author-mode-specific changes belong in `docs/plans/author-mode-parity.md` if they emerge.
- **Optimizing the paperclip skill prompt itself.** Refreshing from upstream is in scope; rewriting upstream's skill prose is not.

---

## Smoke-test plan

1. Run `paperclip install --dir .` to refresh `.claude/skills/paperclip/SKILL.md`.
2. Implement Phase 1 paperclip-aware verify-bib first. Run on `examples/paper-trail-adamson-2025/refs.verified.bib`. Expected output: `verified: 56/56 (paperclip:~27, external:~29, unresolved:0)` matching the May 1 probe results.
3. Implement Phase 2 coverage-aware fetch-paper. Run on the same fixture with `--paperclip=prefer`. Expected: ~27 references skip download; ~29 hit the existing PDF-fetch path.
4. Implement Phase 3 mode-aware dispatch. Run on a single claim from the fixture (e.g., `C001`) in paperclip mode and confirm the evidence JSON validates against schema 1.2.
5. Run end-to-end on the full Adamson fixture. Diff per-claim verdicts against the M1 baseline at `examples/paper-trail-adamson-2025/data/claims/`. The verdicts must agree for any reference where M1 produced a non-PENDING verdict, with the only orthogonal change being `source_mode`. Any disagreement is a bug to investigate before merge.
6. Run end-to-end on `examples/DFD_authormode/` to confirm author-mode parity.

Success criteria:

- Phase 1 hit rate matches the May 1 probe within ±2 references.
- No regression on per-claim verdicts vs M1 baseline.
- Average per-claim wall-clock time on paperclip-mode references is materially lower than PDF-mode (no fetch, no GROBID parse).
- Paywalled-reference handling is at parity with today (same paywall-flag behavior on the `external` slice).
