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
contradiction. MISQUOTE is numerical only — a non-numerical difference is simply not MISQUOTE, and
where it goes is decided by the ordered test below, not here.
INDIRECT vs INDIRECT_NOT_REVIEW turns on whether the reference article is itself a review.

## Choosing one label when several definitions fit — house text

Several definitions above can be true of the same sub-claim at once. NOT_SUBSTANTIATE's "fails to
substantiate all statements" is *also* true whenever the citing sentence contradicts the source,
misquotes a number, overgeneralises a finding, attributes onward, is unclear about what it cites, or
names a subject the paper never studies. It is therefore the **residual** label, not the first one to
reach for.

The worst-wins ladder below does not settle this. It reduces *several sub-claims* to one paper-level
label; it does not choose one sub-claim's label, and on a single-sub-claim citation it is the
identity function. Use this order instead, per sub-claim.

**Two things to fix before you start, because this is where the order goes wrong in practice.**

**First, fix what you are judging.** Verify the proposition the citation marker is attached to, and
only that. A citing sentence's background framing — what the literature generally holds, how many
studies exist, what a field mostly focuses on, how broad a problem is, how many of a review's own
included studies did something — is **not charged to this source**, and its scope words are not this
source's scope. Quote the clause you are judging before you test anything against it.

**Second, this is first-match-wins, and it binds in both directions.** Walk the tests in order from
1. Answer each one explicitly yes or no. **Stop at the first yes and emit that label** — do not keep
going to see whether a later test also passes, and do not skip ahead to a test that looks like the
answer. A later test passing as well is expected and means nothing; that is what "residual" means.

To make the stop auditable, **begin each sub-claim's `nuance` with `gate N:`** — the number of the
test that fired — followed by your one-sentence reason. A verdict whose `nuance` does not name the
gate that produced it was not chosen by this order.

**Third, a gate is answered by its finding, not by your assertion. — house text** Naming a gate and
writing "not applicable" is not answering it. Gates 1 and 6 each require you to write down a specific
thing before "no" is available to you, and the commonest way this order fails is that the write-down
is skipped, the gate is waved through, and then the test it asked for gets performed further down —
inside gate 7's reason — where it no longer selects a label. Two fixed forms, which cost you a phrase
each:

- **Gate 1's "no" needs a line number.** Write `gate 1: subject=<...>, predicate=<...>, predicate
  reported at L<nn> -> no`. The locator must be a passage you actually hold. If no passage in your
  window reports on the predicate, you cannot write a line number, and the answer is **yes**.
- **Gate 6's "no" needs a failed search.** You may only write `gate 6: no excluded member` after
  trying to name one. If the excluded member appears anywhere in what you finally write — in
  `nuance`, in `paper_value`, in `claim_value` — then gate 6 answered **yes**, and the fact that you
  wrote it under a later heading does not move it there.

1. **IRRELEVANT** — no passage you were given addresses the subject the citation is attached to.

   **The bound test: the clause has a subject and a predicate, and the passages must reach both.**
   Write down the clause's subject (what it is about) and its predicate (the outcome, property or
   relationship it asserts of that subject). Then ask of the predicate specifically: does *any*
   passage report on it at all? A passage that shares the subject and is silent on the predicate does
   not clear this gate. A paper about job strain and *coronary heart disease* is IRRELEVANT to a clause
   about job strain and *stroke*, though both are cardiovascular; a paper about mitochondrial
   *metabolism* in cancer is IRRELEVANT to a clause about mitochondrial *structural integrity* under
   chemotherapy. Matching the broad field, the disease area, or the subject alone is **not** clearing
   this gate — that is the specific mistake this test exists to catch. Shared vocabulary is not
   relevance.
2. **ETIQUETTE** — you cannot tell which part of the citing sentence this source is being cited for.

   **Run this test against the raw `claim_text` you were handed, character for character** — not
   against your own restatement of the sub-claim. Restating the proposition strips the citation
   punctuation, and the punctuation *is* the evidence for this gate.

   **Write the last dozen characters of `claim_text` down before you answer.** `gate 2: ends
   "<...>"`. That is the whole evidence for this gate and you cannot weigh it from memory or from a
   paraphrase.

   **It fires on one thing: a sibling citation you can see the beginning of and not the end of.** The
   visible sentence stops *part-way through a cluster* — a trailing `;` or `,` sitting inside the
   citation, a dangling author-year fragment such as `(Smith et al., [CIT];`, or an `[OTHER_CIT]`
   placeholder. An unknown number of siblings, and the clauses they carry, are invisible to you, so no
   part of the sentence can be attributed to this source rather than to one you cannot read. That is
   ETIQUETTE.

   ⚠ **A sentence that merely stops at the marker is not that. — house text** This corpus renders
   citing sentences clipped at the citation, so a text ending `([CIT]` or `[[CIT]` — marker last, no
   separator after it, no partial sibling showing — is a rendering artifact of the benchmark and tells
   you nothing about the citation style. It is not evidence of a hidden sibling list and it does not
   fire this gate. What fires the gate is a separator or an author fragment showing the list *carries
   on* past the text you were handed.

   **It does not fire on an ordinary visible co-citation.** Two or more sources cited together, cluster
   visibly closed, backing one shared proposition, is not ambiguous — it is normal joint citation.
   Narrow this source's burden per the multi-citation section and carry on down the ladder. "Several
   sources are cited here" is not by itself unclear citation style.

   **Ask the attributability question here, not later.** "Which portion of this sentence is this
   source answerable for?" is gate 2's question. If your answer is "no portion can be separated out",
   that answer *is* ETIQUETTE and you stop here. Finding it further down the ladder and writing it as
   a caveat underneath some other verdict is the same mistake made late.
3. **CONTRADICT** — a passage you were given states the opposite of the citing clause. It must
   oppose, not merely differ: a source that assigns the claimed property to a *different* agent, or
   reports the claimed status at an *earlier* stage, opposes only if the citing clause cannot also be
   true. Silence never contradicts.
4. **MISQUOTE** — a number or percentage in the citing sentence differs from the number in a passage.
   Once you have identified a numeric mismatch, the label is MISQUOTE; do not re-describe a numeric
   mismatch as a scope or emphasis problem and route it to OVERSIMPLIFY. **This gate does not ask
   *why* the figures differ.** Rounding, a different cut of the data, a figure the citing authors
   re-estimated, a disagreement about the right number rather than a copying slip — all of them are
   MISQUOTE. "At least 50%" against a source's "at least 41%" is MISQUOTE, not a support gap.
5. **INDIRECT / INDIRECT_NOT_REVIEW** — the passage that supports the clause carries its own citation
   marker for the fact — `(12)`, `5-8`, `(Ota et al., 2009)` — so this source is relaying the fact
   rather than reporting it. INDIRECT if the cited paper is itself a review, INDIRECT_NOT_REVIEW
   otherwise. **Two bounds.** The marked passage must be the one carrying the clause's own entities,
   not merely one whose phrasing resembles the citing sentence — check the entities before the marker.
   And if another passage reports the same fact as this paper's own result ("here we show", "we
   demonstrate", a Results line), the paper *is* the source and this gate does not fire.

   **A third bound, and it is the one that decides most cases: the marked passage must be the *only*
   passage in your window carrying the clause's entities. — house text** Papers relay prior literature
   with markers throughout their introductions, and a review's every sentence ends in one; finding a
   marker on a sentence that resembles the clause is therefore the ordinary case, not the gate. Count
   first. If any other passage you hold carries the clause's own entities without a marker, this
   source is not merely relaying — go to test 6. Gate 5 is for the claim whose *sole* support in the
   window is a sentence crediting someone else.
6. **OVERSIMPLIFY** — a passage supports the clause, but the citing sentence asserts the finding
   over a **larger set of things** than the passage does. The set is of real-world referents —
   populations, conditions, diseases, analytes, timepoints, list items — not of words.

   **The bound test, and it is the whole gate: name the excluded member.** Write down (a) the scope
   expression quoted from the passage, (b) the scope expression quoted from the citing sentence, and
   (c) **one specific thing the citing sentence's scope covers and the passage's scope excludes.** All
   three, in `paper_value`, `claim_value` and `nuance`. **If you cannot name (c), this gate does not
   fire — go to test 7.** Worked: source lists four symptoms, citing sentence adds "fevers" → (c) is
   *fevers*. Source says "a range of age-related processes", citing sentence says "age-related
   processes" → (c) is *an age-related process outside the range the source lists*. Source reports one
   enzyme in two cancers, citing sentence says "protease activity and patient outcomes" → (c) is
   *a protease other than that enzyme*.

   **Four things that are not this gate, because none of them widens a set.** Do not fire OVERSIMPLIFY
   on any of them.
   - **Confidence.** The citing sentence is more assertive than the passage — the passage says "may",
     "might", "will need to be confirmed", "consistent with", and the citing sentence simply states the
     finding. That is not a widened set. A confident summary of a hedged finding is **ACCURATE**. This
     is the same rule as the banned bar below: a hedged source supports a citing clause.
   - **Wording and specificity.** The citing sentence describes the same referents in different words,
     or with more or less mechanistic detail, or omits adjectives that do not change which referents
     are meant. If (c) would be a thing that does not exist or that the sentence is not talking about,
     you have found a wording delta, not a widening. **ACCURATE.**
   - **Direction.** The citing sentence is *narrower* than the passage — it reports one of the source's
     two mechanisms, or drops an intermediate step, or names a subtype where the source named the
     class. Gate 6 fires only on claim-broader-than-passage. Claim-narrower is not this gate.
   - **A clause the citation is not attached to.** Scope words in the sentence's background framing are
     not this source's scope. See the preamble above.

   *House note on calibration:* on this benchmark OVERSIMPLIFY is a **rare** label — roughly one
   citation in sixteen. A lexical difference between the citing sentence and a passage is the ordinary
   case, not the gate; almost every correctly-ACCURATE citation has one.
7. **NOT_SUBSTANTIATE** — none of the above fires, and a passage that *does* address the clause stops
   short of it. What "stops short" requires is the next section.

   **Read back your reason before you emit this label, because it names the gate that really fired.**
   NOT_SUBSTANTIATE's reason has exactly one admissible shape: *a passage reaches this clause's own
   subject and predicate, and falls short of the strength, population, stage or specificity the clause
   asserts.* If what you have written is one of the four below instead, an earlier gate answered yes
   and you go back and emit its label:
   - it names a particular thing the citing sentence covers and the passage does not → **gate 6,
     OVERSIMPLIFY.** Move your two scope expressions into `paper_value` and `claim_value`.
   - no passage reports on the clause's predicate at all → **gate 1, IRRELEVANT.**
   - a number or percentage differs → **gate 4, MISQUOTE.**
   - the passage states the opposite, or assigns the claimed property to a *different* agent by
     explicit contrast while the clause assigns it to this one → **gate 3, CONTRADICT.**

   And one shape that is genuinely this gate, because it is the one most often mistaken for gate 1: a
   passage that reports the clause's own relationship but at a **different stage, population, setting
   or timepoint** has reached the predicate. That is a shortfall, not irrelevance. NOT_SUBSTANTIATE.
8. **ACCURATE** — none of the above fires. A passage is consistent with the clause, or the passages
   are plainly about the clause's own entities and relationship and the window simply did not return
   the supporting sentence (next section).

   **You may not reach this gate by skipping the ones before it,** and the retrieval-silence branch is
   not available to you if you answered gate 1 "no" by citing a passage that reaches the clause. That
   citation was your finding that a passage *does* address the clause, so the live question is whether
   it stops short — gate 7 — not whether the window was silent. Silence and a passage you have already
   pointed at are not both true.

## What you were given is a subset of the paper — house text

Under the retrieval profile the evidence envelope was built mechanically. Three fields in it say how
much of the paper you actually hold: `attestation.selector` (the search that chose your passages),
`attestation.retrieval_k` (how many you were handed) and `attestation.n_passages_available` (how many
the cited paper has). **Read all three before you decide.** On this benchmark the second is typically
under a tenth of the third — you are looking at a keyword-selected sliver, not at the article.

So: **a clause you cannot find in your passages has not been shown to be absent from the paper.**
Argument from silence over a sliver is not a support gap, and it is the largest single source of
wrong verdicts this program makes.

The test that separates a real shortfall from retrieval silence, and it is checkable against the
passages in front of you:

- **A passage addresses the clause and stops short of it** — it reports the same relationship more
  weakly, for a different population, only as a recommendation rather than a finding, or for a whole
  class where the clause asserts it of one member. That is a real shortfall: **NOT_SUBSTANTIATE**.
  (Not OVERSIMPLIFY. Gate 6 is decided by its own named test and nothing here routes into it.)
- **No passage addresses the clause, but the passages are plainly about the clause's own entities and
  relationship** — the paper studies this and your window did not return the sentence. That is
  retrieval silence: **ACCURATE**. Do not require the citing sentence's wording to appear in the
  window, and do not enumerate the sentence's elements and fail it on the first one you cannot match.
- **No passage addresses the clause and the passages are about something else** — IRRELEVANT, per
  test 1 above.

Three bars you may not apply, because none of them is in the scheme: that the source must use the
citing sentence's exact causal framing; that the source must display a particular method (a
multivariate model, a meta-analysis, a quantitative result) before a claim counts as supported; and
that a hedged source sentence cannot support a citing clause. A hedged source supports a citing
clause, hedged or not — and stating a hedged finding confidently is not a defect under any label.

Two of these have a habit of surviving as a *different label* once you have been told not to score
them as a support gap. Naming a support gap "an overgeneralisation" does not make it one, and the
window is still a sliver whichever label you are reaching for. If your reason for a non-ACCURATE
verdict is that you could not find something, the answer is ACCURATE — not a differently-named miss.

## Rollup (per citation instance = per (claim, cited_paper) pair) — house text

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

## Multi-citation handling (critical — 51% of Sarol data) — house text

The dispatch supplies `multi_cit_context`: `"single"` when the evaluated citation stands alone at this position, `"grouped"` when it is one of a `[1,2,3]`-style cluster. **That field is the trigger.** There is no marker in the claim text to look for.

When `multi_cit_context == "grouped"`, verify only the portion of the claim attributable to *this specific source*. Parts of the citing claim that a sibling citation may cover do not count against the current source. If the evidence supports the source-specific portion, label ACCURATE even if the overall sentence says more than this paper alone substantiates.

⚠ A sentence can carry sibling citations while `multi_cit_context` is `"single"`. An `[OTHER_CIT]` placeholder in the claim text says so. Narrow this source's burden the same way when you see one.

**This section applies only to clusters you can see the end of.** A sentence that breaks off inside an unfinished citation list is gate 2's case, not this one, and gate 2 has already decided it: you cannot narrow a burden against siblings you cannot read. Burden-narrowing is what you do once the cluster is visible and the shared proposition is identifiable.

## 3-way collapse

Moved to the enum contract (`verdict_enum_sarol.md`) — it is what the published metric is
computed over, so it is fixed rather than tunable. Do not restate it here; a second copy is a
second thing to drift.
