# Sarol 2024 9-class verdict rubric — for experiment use only

**Scope:** experiment-only rubric used by the Sarol benchmark adjudicator variant. Not a replacement for paper-trail's native rubric (`.claude/specs/verdict_schema.md`), which stays the main tool's default. Whether to adopt Sarol's taxonomy globally is a separate post-experiment decision.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

## Verdict enum (9 classes)

Per-sub-claim, the adjudicator picks exactly one:

- **ACCURATE** — cited paper directly supports the claim as stated.
- **OVERSIMPLIFY** — source findings are oversimplified or overgeneralized in the citing claim. Narrower-in-source than claimed, or qualified-in-source but unqualified in claim.
- **NOT_SUBSTANTIATE** — cited paper fails to substantiate all parts of the claim. Partial support but key element missing.
- **CONTRADICT** — citation context contradicts a statement made in the cited paper. Requires a verbatim source excerpt that opposes the claim.
- **MISQUOTE** — numbers or percentages misquoted. Narrow, numerical-specific. Not for non-numerical strength drift (use OVERSIMPLIFY).
- **INDIRECT** — cited paper itself cites other articles for the claim; claim's attribution goes through a review or secondary source rather than the primary.
- **INDIRECT_NOT_REVIEW** — same pattern as INDIRECT but cited paper is not a review article.
- **ETIQUETTE** — citation style is ambiguous; unclear from the citing sentence what specifically is being cited to this paper. Predominantly a multi-citation issue.
- **IRRELEVANT** — no information in the cited paper relevant to the claim.

## Rollup (per citation instance = per (claim, cited_paper) pair)

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

## Multi-citation handling (critical — 51% of Sarol data)

When the citing sentence contains `<|multi_cit|>` — i.e., the evaluated citation is part of a `[1,2,3]`-style cluster — the adjudicator must verify only the portion of the claim attributable to *this specific source*. Parts of the citing claim that a sibling citation may cover do not count against the current source. If the evidence supports the source-specific portion, label ACCURATE even if the overall sentence says more than this paper alone substantiates.

When a citation is grouped ambiguously such that no sub-claim can clearly be attributed to a single source, prefer ETIQUETTE.

## 3-way collapse (for Sarol's published metric)

- **ACCURATE** → ACCURATE
- **OVERSIMPLIFY / NOT_SUBSTANTIATE / CONTRADICT / MISQUOTE / INDIRECT** → NOT_ACCURATE
- **ETIQUETTE / INDIRECT_NOT_REVIEW / IRRELEVANT** → IRRELEVANT

The adapter computes both 9-way and 3-way scores from the same predictions.

## What this rubric does *not* have (vs paper-trail native)

Intentionally dropped for this experiment — the adapter does not emit:

- CONFIRMED_WITH_MINOR / OVERSTATED_MILD / OVERGENERAL — no analog in Sarol taxonomy
- PARTIALLY_SUPPORTED — Sarol rolls partial into NOT_SUBSTANTIATE
- MISATTRIBUTED — Sarol's MISQUOTE is narrower (numerical only); generic misattribution collapses into NOT_SUBSTANTIATE or INDIRECT
- CITED_OUT_OF_CONTEXT — closest in Sarol is ETIQUETTE; experiment-level label, use ETIQUETTE
- AMBIGUOUS — not in Sarol; if the adjudicator truly cannot pick, prefer ETIQUETTE with a nuance note

Workflow-state flags (PENDING, NEEDS_PDF, STALE) are orthogonal to the rubric and remain paper-trail native.
