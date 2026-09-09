# Sarol 2024 9-class verdict rubric — for experiment use only

**Scope:** experiment-only rubric used by the Sarol benchmark adjudicator variant. Not a replacement for paper-trail's native rubric (`src/specs/verdict_schema.md`), which stays the main tool's default. Whether to adopt Sarol's taxonomy globally is a separate post-experiment decision.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

**The label set is not defined here.** The emittable labels and the 3-way collapse are a frozen contract in `verdict_enum_sarol.md` beside this file — that file is authoritative and is not editable. **This file is the editable half:** how to *choose* between those labels. Everything below — class definitions and boundaries, the worst-wins rollup order, multi-citation handling — is optimizer-editable, and improving it is the point of the optimization loop. What you may not do here is add, remove, or rename a label; the enum contract governs that, and the Scorer will charge an out-of-enum label as a miss.

## Choosing among the 9 classes

The adjudicator picks exactly one per sub-claim.

**The eight class definitions below are the paper's own words, quoted verbatim from Sarol et al. 2024
§2.2 / Table 1.** They are the annotation scheme the gold labels were produced under. Do not
paraphrase, narrow, or extend them: where a definition and a gold label appear to disagree, the
definition is what is under suspicion, never gold. The same text with full provenance is in
`verdict_definitions_sarol.md` beside this file.

**Everything else in this file is house text** — ours, not the paper's: the rollup order, the
multi-citation procedure, and any boundary guidance a later iteration adds. If you add a clause,
mark it as house text so a future reader can always tell the scheme from our reading of it.

- **ACCURATE** — "The citation context is consistent with an evidence segment in the reference article."
- **OVERSIMPLIFY** — "The findings of the reference article are oversimplified or overgeneralized."
- **NOT_SUBSTANTIATE** — "The citation is relevant to the content of the reference article but the cited reference fails to substantiate all statements made in the citing paper."
- **CONTRADICT** — "The citation context contradicts a statement made in the reference article."
- **MISQUOTE** — "The numbers or percentages are misquoted."
- **INDIRECT** — "The evidence segment includes a citation to other articles, indicating that the reference article is not the original source of the cited information."
- **INDIRECT_NOT_REVIEW** — the same indirect-attribution pattern as INDIRECT, where the reference article is not a review article. *(house definition — not in Table 1. The class is real in the released gold data: 25 occurrences in `claims-train.jsonl`, 9 in `claims-test.jsonl`, 0 in dev.)*
- **ETIQUETTE** — "The citation style is ambiguous and it is unclear what is being cited from the reference article."
- **IRRELEVANT** — "There is no information in the reference article relevant to the citation."

## Rollup (per citation instance = per (claim, cited_paper) pair) — house text

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

## Multi-citation handling (critical — 51% of Sarol data) — house text

When the citing sentence contains `<|multi_cit|>` — i.e., the evaluated citation is part of a `[1,2,3]`-style cluster — the adjudicator must verify only the portion of the claim attributable to *this specific source*. Parts of the citing claim that a sibling citation may cover do not count against the current source. If the evidence supports the source-specific portion, label ACCURATE even if the overall sentence says more than this paper alone substantiates.

When a citation is grouped ambiguously such that no sub-claim can clearly be attributed to a single source, prefer ETIQUETTE.

## 3-way collapse

Moved to the enum contract (`verdict_enum_sarol.md`) — it is what the published metric is
computed over, so it is fixed rather than tunable. Do not restate it here; a second copy is a
second thing to drift.

## What this rubric does *not* have (vs paper-trail native) — house text

Intentionally dropped for this experiment — the adapter does not emit:

- CONFIRMED_WITH_MINOR / OVERSTATED_MILD / OVERGENERAL — no analog in Sarol taxonomy
- PARTIALLY_SUPPORTED — Sarol rolls partial into NOT_SUBSTANTIATE
- MISATTRIBUTED — Sarol's MISQUOTE is narrower (numerical only); generic misattribution collapses into NOT_SUBSTANTIATE or INDIRECT
- CITED_OUT_OF_CONTEXT — closest in Sarol is ETIQUETTE; experiment-level label, use ETIQUETTE
- AMBIGUOUS — not in Sarol; if the adjudicator truly cannot pick, prefer ETIQUETTE with a nuance note

Workflow-state flags (PENDING, NEEDS_PDF, STALE) are orthogonal to the rubric and remain paper-trail native.
