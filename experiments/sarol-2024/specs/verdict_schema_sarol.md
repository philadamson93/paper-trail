# Sarol 2024 9-class verdict rubric — for experiment use only

**Scope:** experiment-only rubric used by the Sarol benchmark adjudicator variant. Not a replacement for paper-trail's native rubric (`src/specs/verdict_schema.md`), which stays the main tool's default. Whether to adopt Sarol's taxonomy globally is a separate post-experiment decision.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

**The label set is not defined here.** The emittable labels and the 3-way collapse are a frozen contract in `verdict_enum_sarol.md` beside this file — that file is authoritative and is not editable. **This file is the editable half:** how to *choose* between those labels. Everything below — class definitions and boundaries, the worst-wins rollup order, multi-citation handling — is optimizer-editable, and improving it is the point of the optimization loop. What you may not do here is add, remove, or rename a label; the enum contract governs that, and the Scorer will charge an out-of-enum label as a miss.

## Choosing among the 9 classes

The adjudicator picks exactly one per sub-claim. The names below are the contract's; the guidance attached to each is this file's:

- **ACCURATE** — cited paper directly supports the claim as stated.
- **OVERSIMPLIFY** — source findings are oversimplified or overgeneralized in the citing claim. Narrower-in-source than claimed, or qualified-in-source but unqualified in claim.
- **NOT_SUBSTANTIATE** — cited paper fails to substantiate all parts of the claim. Partial support but key element missing.
- **CONTRADICT** — citation context contradicts a statement made in the cited paper. Requires a verbatim source excerpt that opposes the claim.
- **MISQUOTE** — numbers or percentages misquoted. Narrow, numerical-specific. Not for non-numerical strength drift (use OVERSIMPLIFY).
- **INDIRECT** — cited paper itself cites other articles for the claim; claim's attribution goes through a review or secondary source rather than the primary.
- **INDIRECT_NOT_REVIEW** — same pattern as INDIRECT but cited paper is not a review article.
- **ETIQUETTE** — citation style is ambiguous; unclear from the citing sentence what specifically is being cited to this paper. Predominantly a multi-citation issue.
- **IRRELEVANT** — no information in the cited paper relevant to the claim.

## How much of the claim must be substantiated

**The evidence you are given is a keyword-retrieved subset of the cited paper, not a complete reading of it.** An element you cannot find in it may simply not have been retrieved. Treat a missing element as genuinely absent from the source only when it is core subject matter of the paper: lockdowns unmentioned across the retrieved chunks of a COVID-interventions paper is a retrieval gap; schizophrenia unmentioned in a stress-and-neurogenesis paper is real absence.

`ACCURATE` therefore does not require every element to be independently located. Ask what the citing sentence asserts *on the strength of this source* — its central proposition — and whether the evidence supports that.

- Central proposition supported, and one peripheral element (a further item in an enumeration, a secondary conjunct, an example) neither found nor contradicted → **ACCURATE**.
- Central proposition unsupported, or a claimed element positively conflicting with the evidence → `NOT_SUBSTANTIATE` (or `CONTRADICT` where the source states the opposite).

The "key element missing" in NOT_SUBSTANTIATE means the claim's substance is only half-made — not that the enumeration ran one item longer than the retrieved passages did.

## Rollup (per citation instance = per (claim, cited_paper) pair)

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

## Multi-citation handling (critical — 51% of Sarol data)

When the evaluated citation is one of a `[1,2,3]`-style cluster (`multi_cit_context == "grouped"`), judge only the portion of the claim attributable to *this specific source*.

**Fix that portion first — from the citing sentence alone, before you look at the evidence.** There are two cases and only two:

1. **The sentence assigns.** Its syntax ties a particular clause to this citation's position: separate markers on separate clauses ("… in vitro ([OTHER_CIT]) and … in vivo ([CIT])"), or a named attribution ("Laflamme et al. showed X ([CIT])"). That clause is the attributable portion.
2. **The sentence does not assign.** The cluster sits at the end and covers the whole statement. Then **the entire claim is attributable to this source** — every item of an enumeration, every conjunct of a compound claim. Do not carve elements out on the theory that a sibling citation might cover them. A shared citation asserts joint support, not a division of labour. That fixes what is *in scope*; how much of it must be verified is the sufficiency threshold above.

Fixing the portion is the **only** thing the grouped context changes. Once it is fixed, judge it by exactly the standard a single citation gets — the same sufficiency threshold, no stricter and no softer. Grouping narrows *what* is judged. It never changes *how* it is judged, and it is never in itself a reason to prefer ACCURATE.

Reach for ETIQUETTE only when case 1 seems to apply but the assignment is genuinely undecidable — not merely because the sentence is long or cites several sources. An end-of-sentence cluster is case 2, not ambiguity.

## 3-way collapse

Moved to the enum contract (`verdict_enum_sarol.md`) — it is what the published metric is
computed over, so it is fixed rather than tunable. Do not restate it here; a second copy is a
second thing to drift.

## What this rubric does *not* have (vs paper-trail native)

Intentionally dropped for this experiment — the adapter does not emit:

- CONFIRMED_WITH_MINOR / OVERSTATED_MILD / OVERGENERAL — no analog in Sarol taxonomy
- PARTIALLY_SUPPORTED — Sarol rolls partial into NOT_SUBSTANTIATE
- MISATTRIBUTED — Sarol's MISQUOTE is narrower (numerical only); generic misattribution collapses into NOT_SUBSTANTIATE or INDIRECT
- CITED_OUT_OF_CONTEXT — closest in Sarol is ETIQUETTE; experiment-level label, use ETIQUETTE
- AMBIGUOUS — not in Sarol; if the adjudicator truly cannot pick, prefer ETIQUETTE with a nuance note

Workflow-state flags (PENDING, NEEDS_PDF, STALE) are orthogonal to the rubric and remain paper-trail native.
