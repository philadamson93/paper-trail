# Feature plan — neighbor-sentence claim attribution

**Status.** Plan-only. To-do for upcoming feature work on `feature/multi-cite-and-neighbor-claims`. No code yet.

**Provenance.** Scoped 2026-04-29; full design discussion in `docs/journal/2026-04-29-pause-sarol-pivot-to-features.md`.

---

## Codebase pointers

- **Where claim extraction actually lives:** `.claude/commands/paper-trail.md` Phase 3.1 ("Claim extraction", line 315+). **Important reframe:** the orchestrator IS the agent driven by this slash-command prompt — there is no separate Python "orchestrator's Phase-3.1 claim-extraction step." To extend extraction to neighbor sentences, the change is in the Phase-3.1 prompt instructions, telling the agent to do the bidirectional ±1-sentence walk and emit additional claims tagged to the same citekey with `claim_source: inferred_*`.
- **Per-claim workflow:** `.claude/commands/ground-claim.md` — claims flow through here once extracted. The new `claim_source` value is set at dispatch time from `paper-trail.md` Phase 3.1 and travels through to the per-claim ledger entry.
- **Schema:** `.claude/specs/verdict_schema.md` — additive 1.0 → 1.1 bump per "Schema changes needed" below. (If Feature 1 also bumps to 1.1, both features share one schema_version bump.)
- **Adjudicator behavior:** `.claude/prompts/adjudicator-dispatch.md` — add one paragraph to the rubric about leaning AMBIGUOUS for thin-evidence inferred claims (where `claim_source != "explicit"`).
- **Ledger renderer:** `.claude/scripts/render_html_demo.py` — needs to visually distinguish inferred claims from explicit ones in the per-claim ledger entries.
- **Smoke test:** re-run /paper-trail on `examples/paper-trail-adamson-2025/` and check whether new `inferred_forward` / `inferred_backward` claims appear (there are forward/backward sentence patterns in the MRM paper that should match). Verify all existing `explicit` claims still appear with the same verdicts as baseline (regression check).

---

## Goal

When an author writes a sentence with reference `[m]` and the next or previous sentence makes an additional claim about `[m]` without re-citing it, paper-trail should detect the implicit attribution and treat the neighbor sentence as an additional claim about `[m]`. There is no strict syntactic rule for this — it is a judgment call about reading flow and whether the neighbor sentence is genuinely making an attributable claim about the cited reference.

## Current behavior

The orchestrator's Phase-3.1 claim-extraction step (the orchestrator-side pass that runs before `extractor-dispatch.md`) extracts one claim per cited sentence. Sentences without explicit citations are not analyzed against any reference. A sentence sequence like:

> Smith et al. report a 23% reduction in inference latency for their attention-pruning approach [smith2024]. The same method scales linearly with model size, holding the latency benefit constant up to 70B parameters.

produces one claim against `smith2024` (the first sentence). The second sentence — clearly making a further claim about Smith's method — is not extracted as a claim against `smith2024`.

## Proposed change

Extend the orchestrator's Phase-3.1 claim-extraction step to look ±1 sentence around each cited sentence, bidirectionally, and judgment-call which neighbor sentences also make claims about the same reference. Emit those as additional claims tagged to the same `citekey`.

**Window.** ±1 sentence (the immediately preceding sentence and the immediately following sentence). Larger windows can come later if the v1 behavior shows clear under-recall, but the principle that this is a judgment call rather than a syntactic rule means a tight window is the right starting point — we trade some recall for low false-positive rate.

**Skip rule (load-bearing).** If the neighbor sentence contains its own citation `[n]`, do NOT attempt to attribute the neighbor sentence to `[m]`. The reasoning is reference-hygiene: when the author has explicitly cited `[n]` in the neighbor sentence, attempting to cross-attribute the same sentence to `[m]` is over-inferring on the agent's part. If the author meant the neighbor sentence to also be about `[m]`, they should re-cite — and if they did not, the cleanest signal back to the author is "your reference attribution is ambiguous; consider clarifying" rather than the agent silently inferring.

This skip rule means each sentence gets attributed to at most one reference via inference, and explicit citations always win over inferred attributions.

**Direction.** Bidirectional — both forward (sentence `S+1`) and backward (sentence `S-1`). Backward attribution catches the pattern where the author sets up a claim and then names the source: "Inference latency drops by 23% with attention pruning. Smith et al. report this for transformer architectures up to 70B parameters [smith2024]." The forward direction is more common, but the cost of supporting both is small and the recall gain is real.

## Schema changes needed

A new field on the claim-level schema in `.claude/specs/verdict_schema.md`:

```
claim_source: "explicit" | "inferred_forward" | "inferred_backward"
```

- `explicit` — the claim sentence contains the citation (today's only behavior).
- `inferred_forward` — the claim is from sentence `S+1`, attributed to a reference cited in sentence `S`.
- `inferred_backward` — the claim is from sentence `S-1`, attributed to a reference cited in sentence `S`.

The adjudicator reads this field and may lean more readily toward `AMBIGUOUS` when the evidence for an inferred claim is sparse, since the attribution itself is a judgment call. A `CONFIRMED` verdict on an inferred claim should require correspondingly stronger evidence.

The report renderer uses `claim_source` to visually distinguish inferred claims from explicit ones — the user should see at a glance which claims are paper-trail's inference versus the author's explicit attribution, so they can sanity-check the attribution itself before considering the verdict.

## Behavioral details

**Paragraph and section boundaries.** Inference does not cross paragraphs or section boundaries. A reference cited in the last sentence of paragraph P does not get attributed to the first sentence of paragraph P+1, even though they are immediately adjacent in linear reading order. The paragraph break is a strong topical signal.

**Adjacent citations to the same reference.** If sentences `S` and `S+2` both explicitly cite `[m]`, the inference window for `S` covers `S+1` and `S-1`; the inference window for `S+2` covers `S+1` and `S+3`. Sentence `S+1` could be attributed to `[m]` from either direction (forward from `S` or backward from `S+2`). Emit one inferred claim, not two, attributed to whichever direction the extractor judges stronger; document the choice in the claim's reasoning.

**Adjudicator handling.** No prompt change required for the adjudicator; the existing rubric applies. The adjudicator sees `claim_source` in the schema and adjusts disposition (lean AMBIGUOUS rather than UNSUPPORTED when evidence is thin AND `claim_source != "explicit"`). Add one paragraph to `adjudicator-dispatch.md` calling this out explicitly.

## UI surface

Inferred claims render inline in the per-claim ledger with a visual marker:

```
[smith2024] claim (explicit, sentence 14): "Smith et al. report a 23% reduction in inference latency..."
  verdict: CONFIRMED
[smith2024] claim (inferred from sentence 14, sentence 15): "The same method scales linearly with model size..."
  verdict: CONFIRMED
```

The "inferred from sentence X" parenthetical is the load-bearing UI element. A reader scanning the report can immediately distinguish what they wrote-and-cited from what paper-trail inferred.

## Open questions for implementation

1. **Sentence boundary detection robustness.** The orchestrator's Phase-3.1 claim-extraction step needs reliable sentence segmentation. Common edge cases: abbreviations ("e.g.", "et al."), citations mid-sentence interpreted as boundary, equation-bearing sentences, list items. Worth checking what segmenter the current pre-step uses and whether ±1 sentence is well-defined for edge inputs.
2. **What counts as a "claim" in a neighbor sentence.** Sentences that are framing-only ("This is interesting because...") or transition-only ("Building on this...") should not be extracted as claims even if they appear in the inference window. The judgment call is fundamentally about whether the neighbor sentence asserts a fact attributable to the source.
3. **Cost.** Each cited sentence today triggers one extractor + adjudicator chain (N chains if the sentence has N citations). Adding inferred-neighbor extraction adds up to 2 more chains per cited sentence (one per qualifying neighbor direction). Estimate the budget delta on a representative manuscript before shipping — the canonical run at `examples/paper-trail-adamson-2025/` is a good reference.
4. **Coordinate with Feature 1 (joint verdicts).** The premise-decomposition case in Feature 1 sometimes spans two sentences ("Premise A holds [refs]. Premise B follows from..."). Whether neighbor-attribution + joint-verdict interact cleanly is worth verifying during implementation — both features are on `feature/multi-cite-and-neighbor-claims` so they will land in coordinated diffs.

## Out of scope for v1

- **Window > ±1 sentence.** Defer until v1 ships and we can see whether under-recall is a real problem.
- **Cross-paragraph inference.** Paragraph break is a hard boundary in v1.
- **Multi-citation neighbor sentences.** If the neighbor sentence has its own citation, skip — see "Skip rule" above. Cross-attribution across explicit citations is reference-hygiene territory and we should not try to fix it silently.
- **Confidence scoring on the inference itself.** The adjudicator's rubric (lean AMBIGUOUS on thin evidence + non-explicit source) handles this implicitly. Adding an explicit confidence score is a v2 consideration.
