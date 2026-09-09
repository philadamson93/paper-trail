# Sarol 2024 9-class verdict rubric — for experiment use only

**Scope:** experiment-only rubric used by the Sarol benchmark adjudicator variant. Not a replacement for paper-trail's native rubric (`src/specs/verdict_schema.md`), which stays the main tool's default. Whether to adopt Sarol's taxonomy globally is a separate post-experiment decision.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

**The label set is not defined here.** The emittable labels and the 3-way collapse are a frozen contract in `verdict_enum_sarol.md` beside this file — that file is authoritative and is not editable. **This file is the editable half:** how to *choose* between those labels. Everything below — class definitions and boundaries, the worst-wins rollup order, multi-citation handling — is optimizer-editable, and improving it is the point of the optimization loop. What you may not do here is add, remove, or rename a label; the enum contract governs that, and the Scorer will charge an out-of-enum label as a miss.

## Choosing among the 9 classes

The adjudicator picks exactly one per sub-claim. The names below are the contract's; the guidance attached to each is this file's:

- **ACCURATE** — cited paper directly supports the claim as stated.
- **OVERSIMPLIFY** — source findings are oversimplified or overgeneralized in the citing claim. Narrower-in-source than claimed, or qualified-in-source but unqualified in claim.
- **NOT_SUBSTANTIATE** — cited paper fails to substantiate all parts of the claim. Partial support but key element missing.
- **CONTRADICT** — citation context contradicts a statement made in the cited paper. Requires a verbatim source excerpt that opposes the claim. Decidable test: you must be able to quote a source span that is logically *incompatible* with the claim (source asserts *not-X* where the claim asserts *X*, or assigns the claim's property to a *different* entity and gives this one an incompatible property). A source that is merely silent, reports a *different or later state* (claim "approved for emergency use"; source "currently being evaluated in clinical trials"), or just fails to establish the element is **NOT_SUBSTANTIATE**, not CONTRADICT.
- **MISQUOTE** — numbers or percentages misquoted. Narrow, numerical-specific. Not for non-numerical strength drift (use OVERSIMPLIFY).
- **INDIRECT** — cited paper itself cites other articles for the claim; claim's attribution goes through a review or secondary source rather than the primary.
- **INDIRECT_NOT_REVIEW** — same pattern as INDIRECT but cited paper is not a review article.
- **ETIQUETTE** — citation style is ambiguous; unclear from the citing sentence what specifically is being cited to this paper. Predominantly a multi-citation issue.
- **IRRELEVANT** — no information in the cited paper relevant to the claim.

## Applying the labels — boundary tests

These tests decide the boundaries the one-line definitions above leave open. They exist because the
most common error on this task is **over-strictness**: downgrading a citation the source actually
supports. Read them before assigning any label other than ACCURATE.

### The ACCURATE test — substance, not wording

A citation is **ACCURATE** when the source substantively supports the proposition the citing
sentence attributes to it. Apply this three-step test before considering any downgrade:

1. **Name the claim's most-specific element** — the exact mechanism, entity, subtype, magnitude, or
   scope the citing sentence attributes to *this* source (only this source — see the attribution
   procedure under multi-citation below). Not the general topic: the topic is "mitochondria and
   cancer", the element is "targeting glycosylation sites aids neutralization" or "caspase activation".
2. **Look for the passage that asserts that specific element** — not one that merely shares the
   general topic. A passage on the claim's broad subject that does not assert the claim's specific
   element is **not support**; it is a downgrade signal (topical overlap alone → the specificity or
   IRRELEVANT test below, not ACCURATE).
3. If such a passage exists, the verdict is **ACCURATE** — even when the citing sentence is more
   concise, paraphrases, drops a hedge, or uses broader everyday framing — *unless* the dropped
   detail is load-bearing (see the OVERSIMPLIFY test).

Do not require the claim to restate the source's caveats, and do not require the source to prove more
than the claim asserts. Concretely: naming a drug, mechanism, or association that the source
documents is ACCURATE even if the claim omits the source's qualifiers; a hedged claim ("may be",
"could be", "candidate") is supported by a source that reports the phenomenon as observed; and do not
invent a stronger assertion than the sentence actually makes (e.g. do not demand proof of clinical
efficacy when the claim only names a drug, or proof of statistical independence when the claim only
calls something a candidate predictor).

The tolerance runs one way only. A claim may be **broader** than the source (paraphrase, dropped
hedge, everyday framing) and still be ACCURATE. A claim that is **more specific** than the source is
not: if the source establishes a class-level or general finding and the claim asserts a narrower
member of it (source "low type-I interferon", claim "low IFN-alpha"; source "a signalling defect",
claim "a defect in kinase K"), the source does not establish the specific element the claim asserts,
and the verdict is **NOT_SUBSTANTIATE**, not ACCURATE.

### OVERSIMPLIFY vs ACCURATE — the materiality test

**OVERSIMPLIFY applies only when the gap between what the source supports and what the claim asserts
is *material*** — i.e. when restoring the source's qualifier, scope, or degree would change whether
the source supports the claim. Decision test: *would a reader of the claim alone believe something
the source does not support?*

- If **no** — the omitted detail (a percentage, a hedge, a broader framing) does not reverse or
  materially weaken the asserted proposition — the verdict is **ACCURATE**. Examples: source
  "restores activity to 10–50%", claim "restores activity" → ACCURATE, the degree is not load-bearing
  to the asserted fact; source "protective association, consistently observed (with dose-response
  caveats)", claim cites the protective association → ACCURATE.
- If **yes** — the source's finding holds only under a condition, scope, or degree the claim drops —
  the verdict is **OVERSIMPLIFY**. Example: source shows an effect only in rodents, claim states it
  as a general fact about mammals without qualification → OVERSIMPLIFY, the species restriction is
  load-bearing.

### NOT_SUBSTANTIATE vs IRRELEVANT — is there partial support at all?

**NOT_SUBSTANTIATE requires that the source actually addresses the claim's specific subject and gives
*partial* support** — some parts confirmed, a key element missing. It is not the default label for a
citation you cannot confirm.

Decidable test: can you **quote** a passage in *this* source that supports at least one *specific
element* of the claim's proposition — not merely its general topic or field? If **you can quote one**,
the verdict is **NOT_SUBSTANTIATE** (partial support, a key element still missing); name and quote the
element that is supported. If **no such passage exists — even when the source is on a topically
adjacent subject** (claim about stroke, source about coronary heart disease; claim about a
chemotherapy-induced change, source about a drug's metabolic mechanism; claim about job strain and one
outcome, source about job strain and a *different* outcome) — there is no partial support, and the
verdict is **IRRELEVANT**, not NOT_SUBSTANTIATE. Topical adjacency is not partial support. The test is
symmetric: do not emit NOT_SUBSTANTIATE without quoting the supported element, and do not emit
IRRELEVANT if you can quote one.

**IRRELEVANT is a last-resort label, and a thin retrieved window is not grounds for it.** Choose it
only when the retrieved passages positively show the source is about a *different subject* than the
claim — a paper on drug X's metabolism cited for a claim about disease Y. Do **not** choose IRRELEVANT
merely because the window is empty, methods-only, or a keyhole that did not happen to contain the
supporting passage: that is retrieval silence, not evidence of a different subject (see "Empty or
off-topic evidence window" below). When you are unsure between IRRELEVANT and either ACCURATE on a
thin window or NOT_SUBSTANTIATE on a partially-supported claim, do not choose IRRELEVANT.

### Empty or off-topic evidence window

The evidence you are given was selected by keyword retrieval, not by you, and it can be empty or miss
the relevant passage even when the paper contains it. An empty or off-topic window is **not** evidence
that the paper contradicts or fails the claim.

- If the window is empty or contains no passage on the claim's subject: you have no basis to assert a
  not-accurate verdict. If the citing sentence states an ordinary factual claim and nothing retrieved
  opposes it, prefer **ACCURATE** over manufacturing NOT_SUBSTANTIATE, OVERSIMPLIFY, or ETIQUETTE.
- If the window contains on-topic passages that genuinely fail to support the claim: the not-accurate
  labels apply as usual.

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

**Attribution procedure — do this before assigning any verdict on a multi-citation sentence.** First split the sentence into propositions and decide which belong to *this* source. Signals that a proposition belongs to a **sibling** citation and must be excluded from this source's verdict:

- it is tied to a specific other citation marker or author name inside the citation group (e.g. "…as shown by Maezawa and Jin, [CIT];" — the named authors and the trailing semicolon mark a sibling's proposition);
- it concerns a subject that none of the passages retrievable from this source address, while a sibling plausibly covers it;
- it reports an aggregate or literature-scope synthesis the citing review itself made ("4 of 27 studies…", "the focus of the overwhelming majority of studies", "most studies to date"), which is the citing author's synthesis, not a claim this single source makes — exclude the field-wide count and judge only this source's own specific contribution.

Do **not** count such a proposition against this source. Judge this source only on the propositions attributable to it; if those are supported, the verdict is **ACCURATE**.

When a citation is grouped so ambiguously that no proposition can be confidently attributed to a single source — **including a single-citation sentence where it is unclear which clause the marker attaches to** — the verdict is **ETIQUETTE**. Despite the "predominantly a multi-citation issue" note above, ETIQUETTE is not restricted to multi-citation clusters.

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
