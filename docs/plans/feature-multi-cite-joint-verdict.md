# Feature plan — multi-citation joint verdict

**Status.** Plan-only. To-do for upcoming feature work on `feature/multi-cite-and-neighbor-claims`. No code yet.

**Provenance.** Scoped 2026-04-29; full design discussion in `docs/journal/2026-04-29-pause-sarol-pivot-to-features.md`.

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

Schema versioning: bump `schema_version` from `"1.0"` to `"1.1"`. The orchestrator's validation rules (lines 196-208) should not break on existing 1.0 ledger files — joint-verdict fields are additive optional.

## Open questions for implementation

1. **What "joint" means when the per-ref verdicts are ambiguous.** If the per-ref verdicts are CONFIRMED + AMBIGUOUS + UNSUPPORTED, does the joint pass treat AMBIGUOUS as evidence-present-but-uncertain (lean toward CONFIRMED jointly) or as evidence-absent (lean UNSUPPORTED)? Probably document both outcomes and let the joint adjudicator pick — but worth pinning before implementation.
2. **Cost.** Pass 3 adds one more subagent dispatch per multi-ref claim. Worth sampling on a representative manuscript to estimate the budget delta.
3. **Where the joint adjudicator sees the manuscript context.** Pass 2 currently sees only the focal claim_text; the joint pass might need adjacent-sentence context for some cases (e.g., when the premise decomposition is across two sentences, which is also where Feature 2 — neighbor claim attribution — comes in). Coordinate with Feature 2 during implementation.
4. **Single-sub-claim shortcut.** When all per-ref verdicts already agree (e.g., all CONFIRMED, or all UNSUPPORTED with similar reasoning), the joint pass is mostly redundant — the joint verdict will track the per-ref consensus. Consider an orchestrator-side cheap-check that skips Pass 3 when all per-ref verdicts agree on `CONFIRMED` (the unanimous-CONFIRMED case adds nothing). Don't skip on unanimous-UNSUPPORTED since that's exactly the case where premise-decomposition rescue might fire.

## Out of scope for v1

- Joint verdicts across non-co-cited refs (e.g., one citation in sentence S, another in sentence S+5). v1 limits joint to same-sentence co-citations.
- Joint verdicts spanning multiple sub-claims (e.g., "premise-1 supported by [a]; premise-2 supported by [b]; therefore claim CONFIRMED jointly"). The Pass-3 adjudicator can note this in its reasoning, but the schema doesn't formally model per-sub-claim joint attribution.
- Per-ref-vs-joint UI A/B testing. Land the inline asterisk-pointer rendering, iterate based on real-use feedback.
