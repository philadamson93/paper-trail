# Sarol 2024 9-class verdict rubric — for experiment use only

**Scope:** experiment-only rubric used by the Sarol benchmark adjudicator variant. Not a replacement for paper-trail's native rubric (`src/specs/verdict_schema.md`), which stays the main tool's default. Whether to adopt Sarol's taxonomy globally is a separate post-experiment decision.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

**The label set is not defined here.** The emittable labels and the 3-way collapse are a frozen contract in `verdict_enum_sarol.md` beside this file — that file is authoritative and is not editable. **This file is the mostly-editable half:** how to *choose* between those labels. The boundary tests, the worst-wins rollup order, multi-citation handling and any guidance a later iteration adds are optimizer-editable, and sharpening them is the point of the optimization loop.

⚠ **Two things you may not do here.** You may not add, remove, or rename a label — the enum contract governs that, and the Scorer will charge an out-of-enum label as a miss. And you may not reword the **eight paper-verbatim class definitions** below: they are quoted from Sarol et al. 2024 Table 1, they are the scheme gold was annotated under, and rewording them is how this program acquired the three inverted definitions that five iterations then hill-climbed on. `scripts/check_paper_fidelity.py` enforces this. Everything you add is house text and must be marked as house text.

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
- **CONTRADICT** — "The citation context contradicts a statement made in the reference article. This statement is annotated as the evidence segment."
- **MISQUOTE** — "The numbers or percentages are misquoted."
- **INDIRECT** — "The evidence segment includes a citation to other articles, indicating that the reference article is not the original source of the cited information."
- **INDIRECT_NOT_REVIEW** — the same indirect-attribution pattern as INDIRECT, where the reference article is not a review article. *(house definition — not in Table 1. The class is real in the released gold data: 25 occurrences in `claims-train.jsonl`, 9 in `claims-test.jsonl`, 0 in dev.)*
- **ETIQUETTE** — "This category, unique to our work, indicates that the citation style is ambiguous and it is unclear what is being cited from the reference article."
- **IRRELEVANT** — "There is no information in the reference article relevant to the citation."

*House routing notes (ours, not the paper's, carried over from `program-v0`):* CONTRADICT requires a
verbatim source excerpt that opposes the claim — a source that is merely *silent* is not a
contradiction. MISQUOTE is numerical only. INDIRECT vs INDIRECT_NOT_REVIEW turns on whether the
reference article is itself a review.

## How to apply them — house text

Everything in this section is ours, not the paper's. It exists because the eight definitions above
overlap: on a real citing sentence two or three of them can all be made to fit, and without a test
that decides between them the widest one wins by default. The tests below are what decides.

### Step 1 — name the proposition under test

Before choosing any label, write one sentence: **what is this source being cited to establish?**
That is the *proposition under test*, and it is the only thing you grade. It is the assertion
carried by the clause the citation marker sits in or immediately follows — not the whole sentence,
and not the sentence's framing.

The following parts of a citing sentence are **not** part of the proposition under test. A source
that does not carry them is not thereby failing to substantiate anything, and you may not use any
of them as the reason for a non-ACCURATE label:

- **Supersets introduced by an exemplar.** "a variety of diseases, **including** multiple
  cardiovascular outcomes", "a range of X, such as Y". Grade the named exemplar, not the superset.
- **Field-level or bibliometric framing.** "the focus of the overwhelming majority of studies",
  "the most widely studied", "one of the deepest and broadest studied", "it is well established
  that". A single cited paper is offered here as an *instance* of the state of the field, never as
  a survey of it. No primary study can substantiate a statement about how much of a literature
  exists, and it is not being asked to.
- **Comparative asides.** "similar to prior coronavirus outbreaks", "unlike X", "as in Y", where
  the compared-to thing is not the cited paper's subject.
- **The citing paper's own bookkeeping.** "in 4 of 27 studies", "one of the trials we identified",
  "we assume that". These describe the citing paper's own review or model, not the cited paper's
  findings.
- **Material a sibling citation covers** — see the citation-group section below.

### Step 2 — the ACCURATE floor

ACCURATE asks whether the citation context is *consistent with an evidence segment*. It does not
ask whether the source proves every word of the sentence, and it does not ask whether you could
write a better sentence. **If a retrieved passage carries the proposition under test, the answer is
ACCURATE** — even when:

- the citing sentence drops a qualifier the source carried ("partial", "virulent", "in vitro");
- the source hedges on mechanism, or says the mechanism is not yet understood, while still stating
  the relationship the citation asserts;
- the citing sentence compresses an intermediate step in a causal chain the source spells out;
- the citing sentence is firmer than the source ("shows" where the source says "suggests").

**Do not reach for a non-ACCURATE label because you can propose an edit.** The test is not "would a
careful editor reword this"; it is "does a retrieved passage carry this proposition".

Two limits on the floor, so it does not swallow real defects:

- **Granularity.** The passage must carry the claim's *named* entity, population or outcome, not a
  parent category containing it. A heading about type-I interferons is not a passage about
  interferon-alpha; a finding in rodents is not a finding in mammals generally.
- **The source's own negative conclusion.** If the source's stated conclusion on that very
  proposition is that the effect was *not* established, is uncertain, or is under investigation,
  then a citing sentence asserting it is not consistent with the evidence segment. Hedged support
  is still support; a stated non-result is not.

### Step 3 — the pairwise tests

Each of these decides one pair of labels that would otherwise both fit, and each requires you to be
able to **quote** something. If you cannot quote what the test asks for, that label is not available
to you.

**IRRELEVANT vs NOT_SUBSTANTIATE.** Relevance is measured against the proposition under test, not
against the paper's research field. Try to quote a retrieved passage that is *about that
proposition* — the same relationship between the same kind of entities.

- You can quote one, and it falls short of the claim (weaker, a different setting, a missing
  component, mis-framed) → **NOT_SUBSTANTIATE**.
- You cannot quote one, and the passages instead establish affirmatively that this paper is about
  some *other* proposition — a different outcome, population, intervention or kind of analysis than
  the claim names → **IRRELEVANT**. The diagnostic is substitution, not silence: you are pointing at
  what the paper is about, not at what you failed to find. Sharing a disease area, a molecule, a
  field or a method with the claim is **not** being about the proposition. A paper whose passages
  report job strain and coronary heart disease, cited for a claim about stroke, is IRRELEVANT rather
  than NOT_SUBSTANTIATE.

**OVERSIMPLIFY vs NOT_SUBSTANTIATE.** These split on *breadth* versus *shortfall*.

- The source establishes the proposition for a narrower population, agent, class or outcome set
  than the citing sentence states it for, and the citing sentence presents the narrow finding as
  the general one → **OVERSIMPLIFY**. This is the label for "the claim is broader than the source's
  finding", including a listed item the passages do not support when the rest of the list is
  supported.
- The source is about the right scope but does not get the claim there at all → **NOT_SUBSTANTIATE**.

Loss of a hedge, a qualifier or a modal is **not** OVERSIMPLIFY on its own — that is Step 2. To
choose OVERSIMPLIFY you must be able to quote the passage that states the *narrower* scope the
citing sentence widened.

**CONTRADICT vs NOT_SUBSTANTIATE.** CONTRADICT still requires a verbatim excerpt that opposes the
claim; silence is not contradiction. But an excerpt that assigns the claimed property to a
*different* agent, population or cause than the claim assigns it to **is** opposing, not silent —
if the source says the effect comes from rotenone and the claim credits paraquat, that is a
contradiction of the citing sentence, not a gap in it.

### Step 4 — what you were given is a subset

The evidence file holds passages selected by keyword search over the cited paper. It is not the
paper. **Never write that the paper "does not discuss" or "never mentions" something** — you have
no way to know that. Every test above is phrased against what the retrieved passages carry, and
that is the only thing you can speak to.

One consequence worth naming: if the retrieved passages are mostly methods, materials, assay
conditions, statistics or acknowledgements — the boilerplate a keyword search returns when it has
missed the substance — then the search missed, and a non-ACCURATE label resting on that window's
silence is not warranted.

## Rollup (per citation instance = per (claim, cited_paper) pair) — house text

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

## Citation groups (critical — 51% of Sarol data) — house text

The evaluated citation is often one member of a cluster. **Decide that from the claim text itself**
— `multi_cit_context` is frequently absent, and a `<|multi_cit|>` marker is not present in this
corpus, so neither can be your trigger. Read the citation marker in the citing sentence as grouped
when any of these holds:

- an `[OTHER_CIT]` token appears anywhere in the sentence;
- the citation marker is immediately followed or preceded by `;` or `,` inside a parenthetical —
  `(Krishnamachary et al., [CIT];` — which is a sibling citation the staging truncated away;
- the sentence enumerates several items and the marker attaches to one of them.

When the citation is grouped, verify **only the portion of the claim attributable to this specific
source**. Parts of the sentence a sibling citation may cover do not count against the current
source. If the evidence carries the source-specific portion, label ACCURATE even if the overall
sentence says more than this paper alone substantiates.

When the grouping is truncated or ambiguous enough that you cannot tell which part of the sentence
this source was cited for, that is exactly what ETIQUETTE is for — the citation style is ambiguous
and it is unclear what is being cited from this reference. Choose ETIQUETTE rather than charging
the whole sentence to this source and failing it.

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
