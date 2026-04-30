# Feature plan — multi-citation joint verdict

**Status.** Plan-only. To-do for upcoming feature work on `feature/multi-cite-and-neighbor-claims`. No code yet.

**Provenance.** Scoped 2026-04-29; full design discussion in `docs/journal/2026-04-29-pause-sarol-pivot-to-features.md`.

---

## Implementation surface (post-critic-review 2026-04-29)

Concrete edits-list and pinned design decisions surfaced by a fresh-eyes critic-agent review. Treat as authoritative over the more abstract architectural prose below.

**Files to edit:**

- `.claude/commands/paper-trail.md` Phase 3 (around line 414): add Pass-3 barrier semantics — group per-ref adjudicator outputs by `claim_text` (or a normalized claim-key hash) and dispatch the joint-adjudicator only when all N per-ref Pass-2s for the same sentence have completed. Today Phase 3 groups by citekey for handle amortization; the new group-by-sentence step runs after.
- `.claude/commands/paper-trail.md` Phase 3 Step 3.3 (around line 430): update `ledger.md` markdown rendering to include the joint row inline below the per-ref rows for multi-cite sentences, with the asterisk-pointer convention.
- `.claude/commands/paper-trail.md` Phase 5 (around line 507) and `.claude/scripts/render_html_demo.py`: HTML viewer renders the joint-verdict row plus per-ref asterisk pointers. (Note: Phase 5 renders HTML, not the markdown ledger — the markdown is Phase 3 Step 3.3. Both surfaces need joint-row support.)
- `.claude/commands/paper-trail.md` end-of-run summary (around line 658-668): report joint-verdict counts separately from per-ref counts to avoid double-counting in the run-level totals.
- `.claude/specs/verdict_schema.md` validation rules section (lines 179-193, NOT 196-208 as the earlier draft of this doc said): admit `C*__joint.json` filenames; admit the new top-level `joint_verdict` envelope; bump `schema_version` 1.0 → 1.1.
- `.claude/scripts/render_html_demo.py` claim-loading code (`load_claims()` around line 144): auto-detect both legacy `data/claims/` (reader-mode fixture layout) and modern `ledger/claims/` layouts; treat `*__joint.json` as a separate render type, not a peer claim, so existing per-claim iteration paths don't double-count.
- NEW: `.claude/prompts/joint-adjudicator-dispatch.md` modeled on `adjudicator-dispatch.md`. Reads only the per-ref adjudicator JSONs and the rubric; never reads source PDFs.

**Naming and shape pins:**

- **Joint file naming:** `<C-id>__joint.json` where `<C-id>` is the alphabetically-first per-ref claim_id for the sentence (stable across runs given seeded ordering). Example: sentence with C042 (chen2022) + C043 (sandino2020) → joint file is `C042__joint.json`.
- **Joint envelope shape:** a complete `verdict_envelope` (reuse the existing schema), with the per-claim fields populated as usual PLUS a new top-level `joint_verdict` object containing `participating_citekeys` array, `relation_to_per_ref` enum, joint-level `overall_verdict` and reasoning. The joint envelope is "additive to" the existing schema in the sense that it slots in alongside per-ref envelopes — not a new file format.
- **`participates_in_joint` per-ref pointer:** orchestrator patches each per-ref envelope after Pass 3 completes (write-after-finalize step — call this out in Phase 3.3 narrative). Per-ref envelope schema gains an additive optional `participates_in_joint: <joint_claim_id>` field.

**Pinned design decisions** (promoted from "Open questions" in earlier draft):

- **AMBIGUOUS handling in joint pass:** treat per-ref AMBIGUOUS as evidence-present-but-uncertain. Joint verdict CONFIRMS only if all non-AMBIGUOUS per-ref verdicts contribute to a coherent joint support; otherwise joint verdict is AMBIGUOUS.
- **Single-ref shortcut:** orchestrator skips Pass 3 for single-citation sentences (nothing to combine). Renderer still emits a one-row per-ref view (no synthesized joint row).
- **Unanimous-CONFIRMED shortcut:** orchestrator skips Pass 3 when all N per-ref verdicts agree on `CONFIRMED`. Renderer shows the per-ref rows without a joint row in this case (no rescue needed; trivial case).

**Co-cite plumbing accuracy** (correction from earlier draft of this doc): the orchestrator passes `co_citekeys` as a flat dispatch slot (`paper-trail.md` line 406; `extractor-dispatch.md` line 29 `{{co_citekeys}}`). The **extractor** writes `co_cite_context.sibling_citekeys` into the evidence JSON. So the data is already available where the joint pass needs it.

**Smoke-test fixture layout:** `examples/paper-trail-adamson-2025/data/claims/` (legacy `data/claims/` layout, 87 claims with 83 multi-cite siblings — strong regression base). After implementation, re-running paper-trail against the fixture produces the same per-ref verdicts AND new `*__joint.json` files for multi-cite sentences. Diff per-ref verdicts against baseline (must be identical = no regression); inspect joint files for the four-case rollup behavior.

---

## Codebase pointers

- **Orchestrator (slash-command prompt):** `.claude/commands/paper-trail.md` — Phase 3 dispatches per-claim subagent chains. Note Phase 3 Step 3.3 (around line 430) renders the markdown `ledger.md`, while Phase 5 (around line 507) renders the HTML viewer via `render_html_demo.py` — both surfaces need joint-row support. Pass-3 joint-adjudicator dispatch logic is added to Phase 3 here, after all per-ref Pass-2 adjudicators have completed for the same `claim_text`.
- **Per-claim workflow:** `.claude/commands/ground-claim.md` — current multi-cite handling lives in the "Multi-cite citations" section ("LaTeX `\cite{a,b,c}` produces one ledger entry per citekey"). The orchestrator passes `co_citekeys` as a flat dispatch slot (see `paper-trail.md` line 406 + `extractor-dispatch.md` line 29 `{{co_citekeys}}`); the **extractor** is what writes `co_cite_context.sibling_citekeys` into the evidence JSON. Pass 3 is the new cross-citekey aggregation that runs once per multi-ref `claim_text` after the per-ref Pass-2s complete.
- **New dispatch prompt to author:** `.claude/prompts/joint-adjudicator-dispatch.md` (new file). Model from `.claude/prompts/adjudicator-dispatch.md`. Same blindness discipline — reads only the per-ref adjudicator JSONs and the rubric, never the source PDFs.
- **Schema:** `.claude/specs/verdict_schema.md` — additive 1.0 → 1.1 bump per "Schema changes needed" below.
- **Ledger renderer:** `.claude/scripts/render_html_demo.py` (and any other consumers of `ledger/claims/*.json`) — needs an update to render the new joint rows + asterisk-pointer per-ref annotations.
- **Smoke test:** re-run /paper-trail on `examples/paper-trail-adamson-2025/` (the canonical M1 reference run per memory `project_m1_complete.md`). The MRM paper contains multi-cite sentences; joint verdicts should appear without changing per-ref verdicts on single-cite claims (regression check).

---

## Goal

When a manuscript sentence cites multiple references — `"X [a, b, c]"` — paper-trail should produce both per-reference verdicts (today's behavior) AND a joint verdict that assesses whether the citation block, taken together, supports the claim. The joint pass catches a real and common false-positive failure mode of per-reference-only assessment: a claim that no single reference supports alone but that the references jointly support via premise decomposition.

## Current behavior

One extractor + adjudicator pair runs per `(claim, citekey)` pair. For sentence `"X [a, b, c]"`, this dispatches three independent extractor → adjudicator chains and produces three verdict files.

The extractor has limited sibling awareness: `co_cite_context.sibling_verdicts` records which of the focal claim's sub-claims a sibling paper also supports (see `.claude/specs/verdict_schema.md` lines 168-172 and `.claude/prompts/extractor-dispatch.md` step 8). The adjudicator does NOT see sibling adjudicators' verdicts and operates only on the focal extractor's evidence file plus the rubric. There is no joint-verdict pass.

## Proposed change

Add a Pass 3 — joint adjudicator — that takes the N per-reference adjudicator JSONs for one `claim_text` and emits one additional verdict file capturing the joint assessment.

**Architecture.**

- Pass 1 (extractor) and Pass 2 (per-ref adjudicator) unchanged. Today's per-ref verdicts continue to be produced.
- Pass 3 (joint adjudicator) dispatches once per multi-ref claim sentence (skipped for single-ref sentences; nothing to combine).
- Pass-3 input: the array of per-ref adjudicator JSONs for the same `claim_text`, plus the rubric. No raw PDF access (same blindness discipline as Pass 2).
- Pass-3 output: a new joint-verdict JSON written to `<output-dir>/ledger/claims/<claim_id>__joint.json` (or similar — exact path during implementation).

## Verdict cases worth distinguishing

The interesting epistemic question is how the per-ref verdicts and the joint verdict relate. Four cases are worth naming explicitly so the joint adjudicator's prompt can target each:

| Case | Per-ref verdicts | Joint verdict | Diagnostic message for the user |
|---|---|---|---|
| Independent redundancy | all CONFIRMED | CONFIRMED, "any one suffices" | Citation hygiene: the redundant references could be dropped |
| Joint support / premise decomposition | each UNSUPPORTED *alone* | CONFIRMED *jointly* | Keep the citation block; it is well-formed |
| Mixed: one carries the load | a CONFIRMED, b/c UNSUPPORTED | CONFIRMED via a; b/c are decorative | Drop b/c, or move them to a different claim they actually support |
| Truly unsupported | all UNSUPPORTED, no joint coverage | UNSUPPORTED | Per-ref result was right; the claim needs different sources or rewording |

The premise-decomposition case is the high-value rescue. Without a joint pass, the report flags three UNSUPPORTED verdicts on a citation block that is in fact fine, and the user has every right to push back.

## UI surface

Joint verdicts render inline with existing per-claim ledger entries — not in a separate "multi-citation" section. The existing per-ref rows are the user's anchor.

**Sketch (refine during implementation):**

For a sentence with three citations, the report renders one ledger entry per reference (today's behavior) plus one joint row beneath them, visually grouped:

```
[a] verdict: UNSUPPORTED *
[b] verdict: UNSUPPORTED *
[c] verdict: UNSUPPORTED *
[a, b, c] joint verdict: CONFIRMED — premises decomposed across refs
* part of joint claim — see [a, b, c] joint row
```

For the mixed case (some refs support jointly, one doesn't support at all):

```
[a] verdict: CONFIRMED
[b] verdict: UNSUPPORTED **
[c] verdict: UNSUPPORTED
[a, b] joint verdict: CONFIRMED — [b] complements [a] for the second sub-claim
** part of joint claim — supports jointly with [a]; consider dropping [c] or moving it
```

The asterisk pointer is the load-bearing UI element: it tells a reader scanning the per-ref rows not to over-react to the per-ref UNSUPPORTED if the joint row rescues it. The exact glyph and layout can iterate during implementation.

## Schema changes needed

The verdict schema in `.claude/specs/verdict_schema.md` needs:

- A new `joint_verdict` envelope (separate from `overall_verdict` which is the per-claim sub-claim rollup, not a multi-ref rollup).
- A `joint_verdict.participating_citekeys` array naming which refs the joint applies to (so the mixed case "joint verdict applies to [a, b] but not [c]" renders correctly).
- A `joint_verdict.relation_to_per_ref` enum: `redundant_independent | joint_premise_decomposition | mixed_one_carries | truly_unsupported_jointly` — mirrors the four-case table; lets the report-renderer pick the right diagnostic copy.
- A pointer field on each per-ref verdict: `participates_in_joint: <claim_id>__joint` — so the report-renderer can wire the asterisk pointer.

Schema versioning: bump `schema_version` from `"1.0"` to `"1.1"`. The orchestrator's validation rules (lines 179-193) should not break on existing 1.0 ledger files — joint-verdict fields are additive optional.

## Open questions for implementation

1. **What "joint" means when the per-ref verdicts are ambiguous.** If the per-ref verdicts are CONFIRMED + AMBIGUOUS + UNSUPPORTED, does the joint pass treat AMBIGUOUS as evidence-present-but-uncertain (lean toward CONFIRMED jointly) or as evidence-absent (lean UNSUPPORTED)? Probably document both outcomes and let the joint adjudicator pick — but worth pinning before implementation.
2. **Cost.** Pass 3 adds one more subagent dispatch per multi-ref claim. Worth sampling on a representative manuscript to estimate the budget delta.
3. **Where the joint adjudicator sees the manuscript context.** Pass 2 currently sees only the focal claim_text; the joint pass might need adjacent-sentence context for some cases (e.g., when the premise decomposition is across two sentences, which is also where Feature 2 — neighbor claim attribution — comes in). Coordinate with Feature 2 during implementation.
4. **Single-sub-claim shortcut.** When all per-ref verdicts already agree (e.g., all CONFIRMED, or all UNSUPPORTED with similar reasoning), the joint pass is mostly redundant — the joint verdict will track the per-ref consensus. Consider an orchestrator-side cheap-check that skips Pass 3 when all per-ref verdicts agree on `CONFIRMED` (the unanimous-CONFIRMED case adds nothing). Don't skip on unanimous-UNSUPPORTED since that's exactly the case where premise-decomposition rescue might fire.

## Out of scope for v1

- Joint verdicts across non-co-cited refs (e.g., one citation in sentence S, another in sentence S+5). v1 limits joint to same-sentence co-citations.
- Joint verdicts spanning multiple sub-claims (e.g., "premise-1 supported by [a]; premise-2 supported by [b]; therefore claim CONFIRMED jointly"). The Pass-3 adjudicator can note this in its reasoning, but the schema doesn't formally model per-sub-claim joint attribution.
- Per-ref-vs-joint UI A/B testing. Land the inline asterisk-pointer rendering, iterate based on real-use feedback.
