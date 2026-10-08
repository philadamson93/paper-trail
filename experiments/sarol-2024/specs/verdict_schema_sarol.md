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
- **INDIRECT_NOT_REVIEW** — the same indirect-attribution pattern as INDIRECT, where the reference article is not a review article. *(house definition — not in Table 1. The class is real in the released gold data: 25 occurrences in `claims-train.jsonl`, 0 in dev.)*
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

**First, this is first-match-wins, and it binds in both directions.** Walk the tests in order from
1. Answer each one explicitly yes or no. **Stop at the first yes and emit that label** — do not keep
going to see whether a later test also passes, and do not skip ahead to a test that looks like the
answer. A later test passing as well is expected and means nothing; that is what "residual" means.

To make the stop auditable, **begin each sub-claim's `nuance` with `gate N:`** — the number of the
test that fired — followed by your one-sentence reason. A verdict whose `nuance` does not name the
gate that produced it was not chosen by this order.

**Second, a gate fires on a finding you can quote, and silence is not a finding. — house text** Your
passages are a keyword-selected sliver of the article (the subset section below has the numbers), so
*my passages do not mention X* is a fact about the window and never about the paper. Gates 1, 3, 6
and 7 each name a label on the strength of a positive finding, so each one has a write-down you must
be able to produce **in order to fire it**. Produce it and the gate fires; fail to produce it and the
gate answers **no** and you walk on. The write-down licenses the label, not the refusal — with one
exception, stated at gate 3, where you write the **refusal** down as well, because that is the gate
this program disposes of in prose most often and never fires.

A gate disposed of in prose — "not applicable", "relevant to the paper", "no scope difference" — has
not been answered in either direction, and prose can never fire one.

**Third, three rules from further down this file decide more claims than any gate does, so apply
them inside every gate rather than after the walk. — house text**

- **The clause is what the marker is attached to** — not the sentence around it. Background framing
  (what the literature holds, how many studies exist, what a field focuses on, how broad a problem
  is, how many of a citing review's own included studies did something) is not charged to this
  source, and its scope words are not this source's scope. Quote the clause before any gate.
- **You may not fail a clause element-by-element.** Splitting the clause into assertions and charging
  the source for the ones your window does not match is the single commonest way this program
  produces a wrong label.
- **Three bars are not in the scheme and may not be applied under any gate:** that the source must use
  the citing sentence's causal framing; that it must show a particular method before a claim counts as
  supported; and that a hedged source sentence cannot support a citing clause.

1. **IRRELEVANT** — no passage you were given addresses the subject the citation is attached to.

   **The bound test, and it is one question: does any passage assert something on the clause's
   *predicate axis*? — house text** The axis is the kind of thing the clause asserts of its subject —
   a status, a risk of one named outcome, one named property, one named relationship. Write
   `gate 1: clause asserts <axis> of <subject>; my passages assert <axis> of <subject>`. **Fire this
   gate only when no passage asserts anything on that axis.** Then go on to the two readings of
   "yes" below and pick the right one.

   **Fill the two `<axis>` slots with the same words, or the gate has not been answered. — house
   text** The left slot is read off the **marker-attached clause**, and once written it is fixed: you
   may not widen it to the paper's topic to make the right slot match. The right slot must be quoted
   from a passage. If the honest right slot is broader than the left, or names a different
   relationship — clause says *death rate is unaffected by treatment status until suppression*,
   passages say *life expectancy of people on ART*; clause says *risk of stroke*, passages say *risk
   of coronary heart disease* — then the axes do **not** match, and what you have is topic overlap,
   which is the one thing this test exists to reject.

   ⚠ **"the same axis", "a matching axis", "the clause's axis", "the same relationship" are not
   quotations — they are this gate's conclusion written into the slot that was supposed to produce
   it. — house text** If the right slot does not hold words copied off a passage, the gate has not
   been answered; go back and copy them.

   **An admitted mismatch fires this gate. — house text** Once you have written two slots that do not
   match, you have answered test 1 **yes** and the label is IRRELEVANT; stop here. Writing "the axes
   do not match" and then walking on to gates 7 and 8 is not an answer to this gate, it is a refusal
   to emit the one it produced — and gate 8's naming test will pass on the shared subject every time,
   so walking on always lands on ACCURATE.

   **The left slot holds the whole relationship the clause asserts, qualifiers included — not one
   quantity out of it. — house text** A passage that reports a bare quantity the relationship is
   *about*, without asserting the relationship, has not matched the axis. Writing that bare quantity
   into the right slot is how an admitted mismatch gets talked away: the slots then read as matching
   while the clause's actual relationship is nowhere in your window.

   **Same axis, different value, is not this gate — it may be gate 7.** A passage that reports the
   clause's own relationship of a **population, stage or setting that the clause's own set does not
   contain** is on the axis and falls short of it: a paper reporting a vaccine in clinical trials
   where the clause says approved for emergency use, or linkage failing at an earlier stage of care
   than the clause names. Route it to gate 7, which decides it by its own containment test — and
   **that test, not this sentence, is what makes it NOT_SUBSTANTIATE.** Do not read the setting into
   the predicate; the setting belongs to the subject. — house text

   **Silence is not this gate either.** `predicate reported at L=none` is a fact about your window,
   not a finding about the paper, and on its own it cannot fire this gate. — house text

   **A different axis does fire it, even when the subject matches.** A paper about job strain and
   *coronary heart disease* is IRRELEVANT to a clause about job strain and *stroke*, though both are
   cardiovascular; a paper about mitochondrial *metabolism* in cancer is IRRELEVANT to a clause about
   mitochondrial *structural integrity* under chemotherapy. Matching the broad field, the disease
   area, or the subject alone is **not** clearing this gate — that is the specific mistake this test
   exists to catch. Shared vocabulary is not relevance.
2. **ETIQUETTE** — you cannot tell which part of the citing sentence this source is being cited for.

   **Run this test against the raw `claim_text` you were handed, character for character** — not
   against your own restatement of the sub-claim. Restating the proposition strips the citation
   punctuation, and the punctuation *is* the evidence for this gate.

   **Write the last dozen characters of `claim_text` down before you answer.** `gate 2: ends
   "<...>"`. That is the whole evidence for this gate and you cannot weigh it from memory or from a
   paraphrase.

   **It fires on one thing: a sibling citation you can see the beginning of and not the end of — and
   what shows that is a partial sibling you can point at.** An author-year fragment the clip left
   open (`(Smith et al., [CIT];`, `(Maezawa and Jin, [CIT];`), or a parenthetical the text never
   closes. An unknown number of siblings, and the clauses they carry, are invisible to you, so no
   part of the sentence can be attributed to this source rather than to one you cannot read. That is
   ETIQUETTE. **Quote the fragment, or do not fire.**

   ⚠ **Neither a clip at the marker nor a bare separator after it is a partial sibling. — house
   text** This corpus renders citing sentences clipped at the citation, so a text ending `([CIT]`,
   `[[CIT]`, `[[CIT],` or `[CIT];` — marker closed, at most one punctuation mark after it, no author
   fragment and no unclosed parenthesis — is the benchmark's clip landing where it landed. It tells
   you nothing about the citation style, it is not evidence of a hidden sibling list, and it does not
   fire this gate. An `[OTHER_CIT]` placeholder is not this gate either: a sibling you *can* see is a
   visible one, and it goes to the multi-citation section's burden-narrowing, not here.

   **It does not fire on an ordinary visible co-citation.** Two or more sources cited together, cluster
   visibly closed, backing one shared proposition, is not ambiguous — it is normal joint citation.
   Narrow this source's burden per the multi-citation section and carry on down the ladder. "Several
   sources are cited here" is not by itself unclear citation style.

   **Ask the attributability question here, not later.** "Which portion of this sentence is this
   source answerable for?" is gate 2's question. If your answer is "no portion can be separated out",
   that answer *is* ETIQUETTE and you stop here. Finding it further down the ladder and writing it as
   a caveat underneath some other verdict is the same mistake made late.
3. **CONTRADICT** — a passage you were given states the opposite of the citing clause. **Quote it.**
   The requirement is that you produce the excerpt verbatim, *not* that the excerpt contain a denial:
   a source need never write "X does not happen" for this gate to fire. — house text It must
   oppose, not merely differ, and **silence never contradicts.**

   **The opposition has a direction, and the direction is the test. — house text** Two shapes count,
   and they are the two this gate already named: a source that assigns the claimed property to a
   *different* agent, and one that reports the claimed status at a *different* stage.
   - **A different named agent.** The paper assigns the clause's own predicate to some *other* named
     thing, and no passage you hold assigns that predicate to the clause's agent. Write
     `gate 3: passage assigns <predicate> to <agent A> at L..; clause assigns it to <agent B>; no
     passage assigns <predicate> to <agent B>`. A paper that attributes complex-I inhibition to one
     compound while giving the compound the clause names a different mechanism is opposing the
     clause, not merely saying less than it.
   - **A different named stage or state.** The paper reports the clause's own predicate as *not yet*,
     *no longer*, or *not* holding where the clause reports it as holding. Quote both values.

   **A shortfall is the other direction, and that is what keeps the two apart. — house text** A
   passage on the clause's axis pointing the *same* way but not as far — weaker, narrower, of a
   subset — is gate 7. Opposite direction on the axis is this gate; same direction and short of it is
   gate 7.

   **Two things do not excuse this gate. — house text**
   - **A hedge on the opposing passage.** The banned hedging bar says a hedged source can still
     *support* a clause. It does not say a hedged source cannot *oppose* one: "may not", "we found no
     evidence that", "is unlikely to" assert the opposition and this gate fires on them. What does
     *not* oppose is a passage whose only difference from the clause is how sure it is of the **same**
     content — that is confidence, and it is ACCURATE.
   - **The element-by-element ban, which is about silence and not about opposition. — house text** You
     may not fail a clause because your window is *silent* on one of its conjuncts. But a conjunct a
     passage **actively opposes** is a contradiction, and the other conjuncts being supported does not
     cancel it. Test each conjunct of the marker-attached clause for opposition before you leave here.

   **Write the refusal down, or this gate has not been answered. — house text** This is the gate most
   often disposed of in unquoted prose — "no passage states the opposite" — which the rule above
   forbids. To answer **no**, write `gate 3: tested <conjunct 1>, <conjunct 2> ... against L..;
   nothing opposes`, naming the conjuncts you tested and the passages you tested them against.

   **No strengthening, and no presupposing. — house text** If you had to strengthen the clause to make
   it clash — adding *all*, *only*, *identical*, *always*, or turning a modelling assumption into a
   claim about every subgroup — you are contradicting your restatement, not the clause, and this gate
   answers **no**. A passage reporting that a quantity differs across subgroups does not oppose a
   clause that never denied it.

   **The opposed content must be a span the clause *asserts*, and you must quote that span. — house
   text** A proposition the clause merely carries along — the background a comparative or concessive
   adjunct takes for granted ("**unlike** infection or interferon responses", "**in contrast to**",
   "**whereas**", "**as opposed to**", "**despite**"), an implication, a presupposition of a definite
   noun phrase — is not what this source is cited for, and a passage opposing it is not opposing the
   clause. Write the opposed words out of `claim_text` verbatim; if what you are opposing is a
   proposition you had to *derive* from the clause rather than read off it, this gate answers **no**.
   This is the preamble's background-framing rule applied here: a comparator the clause sets its own
   subject against is framing.
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
   window is a sentence crediting someone else. **Name the unmarked passages you checked and the
   entities each carries, and read each passage's own markers off that passage** — a marker list
   belonging to a neighbouring line is not evidence about this one.
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

   **Gate 6 does not fire while another passage asserts the clause's predicate at the clause's own
   scope. — house text** Before firing, scan your other passages and write
   `gate 6: no other passage asserts <predicate> of <the clause's own set>`. If one does — the clause
   says "the hippocampus" and a passage says "hippocampal negative control of the HPA axis"; the
   clause says "prior coronavirus outbreaks" and a passage asserts the predisposition without naming
   a subtype — then the narrow bound you found belongs to *that other passage's* experiment, the
   paper is not asserting less than the clause, and gate 6 answers **no**. Go to test 7. Note the
   bar: a passage that merely *carries* the clause's entities is gate 5's test and does not clear
   this one — this one needs the predicate asserted of the clause's own set.

   **Answer the scan against the whole of every sentence you quote, including the one you are
   quoting for (c). — house text** The commonest way this scan is answered wrongly is by splitting a
   single passage sentence: taking its second half as the thing that rules (c) out while its first
   half asserts the clause's predicate at the clause's own scope. "Many commonly utilized drugs have
   been shown to inhibit mitochondrial function in vitro, though it is not clear whether the in vivo
   mechanism is through modulating mitochondrial metabolism" is **one** sentence, and its first half
   asserts the predicate of the clause's own class. **If the sentence you are quoting for (c) also
   asserts the clause's predicate at the clause's own scope, the scan has answered yes and this gate
   does not fire** — go to test 7. Quote the sentence whole before you read either half of it.

   **What may count as (c), and this is where the gate goes wrong. — house text** (c) must be a
   referent the passage's **own scope expression rules out**: a fifth item against a list of four, a
   disease outside the class the passage names, a condition its wording bounds out. Write the
   passage's scope expression down first — if the passage states no scope, there is nothing for the
   sentence to exceed. **If the only thing you can say about (c) is that it is not mentioned, not
   found in the evidence, or not covered by your passages, you have named window silence rather than
   an excluded member, and this gate does not fire** — go to test 7.

   **(b) must be a *set* expression, and you must quote the word that makes it one. — house text**
   This gate's own definition is that the citing sentence asserts the finding "over a **larger set of
   things**". A larger set needs more than one member, so (c) has to be a *second* member of (b)
   beside the one or ones the passage reports. Write
   `gate 6: (b) '<quote>' is a set because '<the quoted breadth word>'; (c) <x> is a second member`.
   The breadth word is one of: an **enumeration** ("fatigue, headaches, muscle pains, and fevers"); a
   **plural or mass class noun** standing for more than one referent ("age-related processes",
   "extracellular protease activity in cancer"); or an explicit **generality word** ("a range of",
   "various", "diverse", "most", "common", "commonly", "all", "in general").

   **If (b) picks out a single referent there is no set, and this gate answers no: go to test 7.** A
   bare definite or anaphoric noun phrase — "the capsid lattice", "this mutation", "the hippocampus" —
   names one thing the citing paper's own earlier text has already fixed. Reading it as a universal
   and then offering a referent of some *other* kind as (c) invents the set the gate needs.

   **Then classify the span, because that is what decides the gate. — house text** Lay (a) beside (b)
   and find **the span of (a) that (b) does not print**. (c) is always built out of that span, so write
   it down on its own: `gate 6: (a) minus (b) = '<the span>'`. Three spans fire this gate and one does
   not, and you tell them apart by what kind of word the span is — not by whether the widening feels
   real.

   - **An item the citing sentence itself prints**, which the passage's closed list or ranking leaves
     out. Diagnostic: the item appears verbatim in (b) and in no passage. **Fires.**
   - **A quantity expression governing a head noun that (b) prints verbatim** — "**a range of**
     age-related processes", "**some** of", "**in two** cancers", "**four of the** studies", "**one**
     enzyme", "**the two most frequently reported**" — where (b) prints the head noun with the
     quantity dropped. **Fires.** This is the dropped quantifier over the finding's own referents.
   - **The proper name or abbreviated identifier of the single referent the paper measured**, where
     (b) prints a class noun in its place and the identifier appears nowhere in the citing sentence
     ("LOX" against "extracellular protease activity in cancer"). **Fires.**
   - ⚠ **An attributive adjective standing immediately before a noun phrase that (b) prints
     verbatim** — "prior *virulent zoonotic* coronavirus outbreaks" against a clause printing "prior
     coronavirus outbreaks"; "*respiratory* virus infections" against "virus infections". **Does not
     fire: go to test 7.** The adjective says *which cases the source looked at*, and the head noun's
     referents are the same kind of thing either way, so negating it ("non-virulent", "non-respiratory")
     manufactures a (c) out of the ordinary fact that the paper is narrower than the clause. Every
     paper is. This is the fork the gate most often takes wrongly, and it is the one the scheme's own
     definition excludes: OVERSIMPLIFY is "oversimplified or overgeneralized", not
     *qualified-in-source but unqualified in the clause*.

   One consequence worth naming: a (b) defined by the very property the clause asserts of it —
   "clinical drugs *with ETC-targeting effects*", "patients *who responded*" — admits only referents
   that already have the property, so there is no second member lacking it and this gate answers
   **no**.

   **(a) must be quoted from a span that asserts a finding. — house text** The scope expression you
   write into (a) has to come from a sentence with a finite verb that states a result. A table or
   figure caption, a supplementary-dataset title, a section heading or a methods label — a span ending
   in a colon, or one you could not read aloud as a claim — states the paper's filing, not its finding,
   and has no scope for the clause to exceed. **If (a) is not a finding, this gate answers no: go to
   test 7.**

   **An enumeration or a ranking is a stated scope, not silence. — house text** Where the passage
   closes a list — "four symptoms: A, B, C and D", "in two cancers", "the two most frequently
   reported were A and B" — a member the enumeration leaves out is ruled out *by the enumeration*,
   and it is a valid (c). Quote the enumeration verbatim and name the member it closes out. This is
   the one case where "the passage does not list it" is a finding rather than window silence, and it
   is what the first worked example above is.

   **Four things that are not this gate, because none of them widens a set.** Do not fire OVERSIMPLIFY
   on any of them.
   - **Wording and mechanistic detail.** The citing sentence describes the same referents in different
     words, or with more or less mechanism spelled out, or omits adjectives that do not change which
     referents are meant. If (c) would be a thing that does not exist or that the sentence is not
     talking about, you have found a wording delta, not a widening. **ACCURATE.** The one dropped
     modifier this does *not* cover is a dropped quantity span, which is the second bullet of the
     span classifier above.
   - **Confidence.** The citing sentence is more assertive than the passage — the passage says "may",
     "might", "will need to be confirmed", "consistent with", and the citing sentence simply states the
     finding. That is not a widened set. A confident summary of a hedged finding is **ACCURATE**. This
     is the same rule as the banned bar in the preamble: a hedged source supports a citing clause.
   - **A bound on whom, where or when the source measured. — house text** This is the commonest
     wrong gate-6 fire this program makes, and it is not a widened referent set. A study population,
     a cohort, enrolment criteria, a clinical setting, a geography, an anatomical subregion, a
     timepoint or a disease stage is the source's **own experimental scope**, not the set its finding
     is asserted of: "hospitalized adults with lower respiratory tract infection", "a subset of
     neurons within the dentate gyrus", "at 4 weeks". A citing sentence that states the finding
     without repeating one of those is **not** gate 6.
     **The test, and it decides the gate: ask what (c) is a different *kind* of.** If (c) is a
     different kind of thing the finding is about — a fifth symptom, a protease other than the one
     measured, a disease outside the class named — gate 6 fires. If (c) is the *same* thing in a
     different population, place, tissue or time, gate 6 answers **no**: that shortfall, if it is real
     at all, is gate 7's `population` or `stage/setting` axis, and it is real only if gate 7's
     **containment test** answers *outside*. Firing gate 6 on it instead does not make it a widening;
     it just moves a wrong gate one rung up the ladder.
   - **Direction.** The citing sentence is *narrower* than the passage — it reports one of the source's
     two mechanisms, or drops an intermediate step, or names a subtype where the source named the
     class. Gate 6 fires only on claim-broader-than-passage. Claim-narrower is not this gate.

7. **NOT_SUBSTANTIATE** — none of the above fires, and a passage that *does* address the clause stops
   short of it. What "stops short" requires is the closed axis list and the containment test below.

   **Read back your reason before you emit this label, because it names the gate that really fired.**
   NOT_SUBSTANTIATE's reason has exactly one admissible shape: *a passage asserts something of its
   own about this clause's predicate, and what it asserts falls short of the clause.* Write it as
   `gate 7: passage says '<quote>', clause says '<quote>', shortfall = <axis>`, and the axis must be
   one of exactly four: **strength** (the passage recommends where the clause reports a finding, *or*
   the passage's recommendation is permissive — "reasonable to consider", "may be considered", "could
   be used" — where the clause reports a strong or universal directive — "strongly recommend",
   "recommend in all", "is indicated"), **population**, **stage or setting**, or **class-vs-member**
   (the passage reports it of a whole class where the clause asserts it of one member — interferons
   I and III against IFN-α). — house text

   ⚠ **`population` and `stage/setting` have a containment test, and it is the whole of those two
   axes. — house text** These two are the commonest wrong fire of this gate, because every paper
   states the population, cohort, site, stage or setting it measured, so a `shortfall = population`
   write-down is producible on *any* claim that reports a finding without repeating that qualifier.
   The write-down therefore decides nothing. **One question decides it: is the group, stage or setting
   the passage reports an *instance of* the one the clause asserts?** Write the answer down as
   `gate 7: passage set <x>; clause set <y>; x is inside/outside y`.

   ⚠ **Before either branch, run gate 6's other-passage scan — this gate needs it more than gate 6
   does. — house text** Write `gate 7: no other passage asserts <the clause's predicate> of <the
   clause's own set>`. **Those words, with the clause's own predicate and the clause's own set
   substituted in.** Written as "no other passage asserts a *weaker* version" it inverts the scan
   into something trivially clean and does the opposite work: you are looking for a passage that
   asserts the clause's predicate of the clause's **own** set, not for one that falls short of it.
   ⚠ **That phrasing is banned outright, and so is any other restatement of the scan's own
   conclusion. — house text** "a weaker version", "the same scope", "nothing broader", "no better
   match" are the answer written into the slot that was supposed to produce it. The slot holds the
   clause's predicate and the clause's set, copied out; if it holds anything else the scan has not
   been run.
   The containment test is run against **one** passage you picked, and a paper
   that studied the clause's own group routinely reports it in a passage your pick is not: a vaccine
   paper's trial-stage line sits beside nothing about emergency-use approval, but a knockout paper's
   antibody-blockade arm sits beside its own knockout arm. **If another passage does assert the
   clause's predicate of the clause's own set, these two axes answer no whatever the containment
   direction says — go to test 8.**

   - **Inside** — the clause's set contains the passage's: "hospitalized adults with lower
     respiratory tract infection" inside "adults with COVID-19"; "Brca1-null mouse ES cells" inside
     "cells with impaired BRCA1 activity"; "mice" inside "mammals". The passage asserts the clause's
     own predicate, of a subset of what the clause is about. The clause has merely dropped the
     source's study qualifier, which is a wording delta and not a shortfall: **this axis does not
     fire — go to test 8.** Generalising from the sample you measured to the thing you were measuring
     is what every paper's own discussion does, and this benchmark labels it ACCURATE.
   - **Outside** — the passage's set lies outside the clause's, or the two are disjoint: a vaccine
     "currently being evaluated in clinical trials" against a clause saying "approved for emergency
     use"; "failure to link patients from HIV testing to HIV care" against a clause about "transition
     from the inpatient setting to self-management at home". The passage is not reporting the clause's
     proposition about a subset of it — it is reporting a different stage or setting of affairs.
     **The axis fires: NOT_SUBSTANTIATE.**

   This test binds only `population` and `stage/setting`. `strength` and `class-vs-member` have their
   own tests below and are unaffected — and note that `class-vs-member` is the *opposite* direction
   (passage broader than the clause), so a passage set that is **inside** the clause's is never
   `class-vs-member` either.

   **`strength` against the banned hedging bar, and the one question that separates them. — house
   text** The banned bar is about *confidence in a result*: a passage that says "may", "might",
   "suggests", "consistent with" or "will need to be confirmed" about a finding it reports does
   support a citing clause stated flatly, and that is ACCURATE. `strength` is about the *force of a
   prescription*: both sides are recommendations and the passage's is optional where the clause's is
   mandatory or universal. **Ask what the modal attaches to.** Attached to how sure the source is of
   a result → confidence, and the verdict is ACCURATE. Attached to how strongly, or to how widely,
   something is advised → `strength`, and the verdict is NOT_SUBSTANTIATE.

   **The axis is a closed list, and the check is literal. — house text** The word after
   `shortfall =` must be exactly one of `strength`, `population`, `stage/setting` or
   `class-vs-member`. If the word you would write is anything else — *scope*, *specificity*,
   *numerical specificity*, *detail*, *mechanism*, *attribution*, *field-wide*, *prevalence*,
   *this paper's own work* — gate 7 did not fire: emit **ACCURATE**. Three shortfalls this rule
   exists to stop, each of which is ACCURATE: a count or number the passages simply do not state
   (that is silence, and gate 4 needs a *differing* number); a clause about what a field or the
   literature mostly does, charged to a source that reports its own instance of it; and a clause
   framed as "other studies have shown X" where the passage reports X.

   **If you cannot quote a passage sentence that asserts something about the clause's predicate, this
   gate does not fire — go to test 8.** "The passage does not mention the mechanism / the number / the
   qualifier" is silence over a sliver, not a shortfall; a shortfall needs a passage saying something
   *weaker*, and a passage saying nothing is not saying something weaker. A passage that names a
   measurement without reporting its result is such a silence. Neither is a delta of **mechanistic
   detail or wording** — the same relationship in more or fewer words, with more or less mechanism
   spelled out, is the ordinary case and is ACCURATE. — house text

   If what you have written is one of the three below instead, an earlier gate answered yes and you
   go back and emit its label:
   - it names a particular thing the citing sentence covers and the passage's own scope rules out
     → **gate 6, OVERSIMPLIFY.** Move your two scope expressions into `paper_value` and `claim_value`.
   - your passages assert a **different predicate** of the clause's subject, rather than a weaker
     value of the clause's own predicate → **gate 1, IRRELEVANT.** A matching subject does not save
     it; gate 1 fires on the axis, not the topic. Silence on the predicate alone still does not
     qualify — a mismatch needs a passage that asserts the *other* axis.
   - a number or percentage in the citing sentence differs from a number in a passage → **gate 4,
     MISQUOTE.**

8. **ACCURATE** — none of the above fires. A passage is consistent with the clause, or the passages
   are plainly about the clause's own entities and relationship and the window simply did not return
   the supporting sentence (next section).

   **The silence route has one bound, and it is literal. — house text** If you are reaching ACCURATE
   because no passage actually asserts the clause — the first half of this gate did not apply — then
   write down the clause's **agent** (the thing doing or causing it) and its **subject** (the thing it
   happens to), each with the passage line where it appears **by name**:
   `gate 8: agent <x> at L..; subject <y> at L..`. The same entity under another name, an abbreviation,
   or a close synonym counts as naming it; a broader process or category the entity merely belongs to
   does not. **Name either one and emit ACCURATE. Emit NOT_SUBSTANTIATE only when you can name
   *neither*** — a window that sits on the clause's predicate axis and names **nothing** the clause is
   about is the paper being *relevant and substantiating nothing*, which is NOT_SUBSTANTIATE's own
   definition.
   ⚠ **One of the two missing is not that case; it is an ordinary retrieval hole. — house text** The
   window is a keyword-selected sliver, and the commonest thing a sliver drops is the clause's named
   agent — a variant, a drug, a molecule — while keeping the general passages about what it does. If
   you can name the subject and not the agent, or the agent and not the subject, the window **is**
   partly about the clause's own entities: that is the retrieval silence this gate exists to absorb,
   and the verdict is **ACCURATE**. Counter-worked: a clause about the N501Y mutation increasing ACE2
   binding affinity, against a window that reports ACE2-binding affinity for RBD mutations at several
   lines and never writes "N501Y" — subject named, agent not, so **ACCURATE**, not a shortfall.
   Worked: a clause about bortezomib causing vacuolation in DRG satellite cells, against a window
   where several passages discuss mitochondrial damage and apoptosis and none names bortezomib, DRG
   or satellite cells — the shared axis is why gate 1 did not fire, and the missing agent is why this
   is not ACCURATE.

## What you were given is a subset of the paper — house text

Under the retrieval profile the evidence envelope was built mechanically. Three fields in it say how
much of the paper you actually hold: `attestation.selector` (the search that chose your passages),
`attestation.retrieval_k` (how many you were handed) and `attestation.n_passages_available` (how many
the cited paper has). **Read all three before you decide.** On this benchmark the second is typically
under a tenth of the third — you are looking at a keyword-selected sliver, not at the article.

So: **a clause you cannot find in your passages has not been shown to be absent from the paper.**
Argument from silence over a sliver is not a support gap, and it is the largest single source of
wrong verdicts this program makes.

## Rollup (per citation instance = per (claim, cited_paper) pair) — house text

When the citing claim is decomposed into multiple sub-claims, reduce to one paper-level label by **worst-wins** strictness order:

```
CONTRADICT  >  NOT_SUBSTANTIATE  >  MISQUOTE  >  OVERSIMPLIFY
            >  INDIRECT  >  INDIRECT_NOT_REVIEW
            >  IRRELEVANT  >  ETIQUETTE  >  ACCURATE
```

Exception: a single-sub-claim citation gets that sub-claim's label directly (preserves verdict precision for simple citations).

⚠ **That exception is about the *value*, not about the field. — house text** `overall_verdict` is a required top-level field on every output: write it, carrying that value. A file whose `overall_verdict` is missing or null is rejected (`MISSING_FIELD:overall_verdict`) and the claim scores as a miss whatever the sub-claim said — this has already cost this program a claim.

## Multi-citation handling (critical — 51% of Sarol data) — house text

The dispatch supplies `multi_cit_context`: `"single"` when the evaluated citation stands alone at this position, `"grouped"` when it is one of a `[1,2,3]`-style cluster. **That field is one of the two triggers; a literal `[OTHER_CIT]` in the claim text is the other.**

When `multi_cit_context == "grouped"`, verify only the portion of the claim attributable to *this specific source*. If the evidence supports the source-specific portion, label ACCURATE even if the overall sentence says more than this paper alone substantiates.

⚠ A sentence can carry sibling citations while `multi_cit_context` is `"single"`. An `[OTHER_CIT]` placeholder in the claim text says so. Narrow this source's burden the same way when you see one.

⚠ **Those two are the only triggers, and you must quote the one you used. — house text** Before you narrow anything, write `burden narrowed: multi_cit_context=grouped` or `burden narrowed: [OTHER_CIT] visible`. If you can write neither — `multi_cit_context` is `"single"`, is absent from your inputs, or you are unsure what it was, and the claim text contains no literal `[OTHER_CIT]` — then **there is no sibling and you may not narrow.** The whole marker-attached clause is this source's burden, every item in it.

A sibling you have *inferred* from the shape of the sentence is not a sibling. "A sibling citation may cover the remainder", "the rest is presumably cited elsewhere", "this source's portion is the first three items" — written against a lone closed `[CIT]` or `[[CIT]]` — is you supplying the co-citation, and it is wrong in the one place it costs most: **it deletes gate 6's excluded member.** A clause that asserts a four-item list where the passage closes a three-item one is gate 6's own first worked example; handing the fourth item to an imagined sibling turns OVERSIMPLIFY into ACCURATE on exactly the claims this gate exists for. If (c) is an item of a list the clause asserts and you cannot quote a trigger, **gate 6 fires.**

⚠ **The second bound, and it is the one the field trigger cannot supply: you may not narrow away a
referent the clause names in so many words. — house text** Quoting the field licenses narrowing on
almost any claim and by itself decides nothing — the same defect gates 6 and 7 each had. **One
question bounds it: is
the thing you are handing to the sibling *printed in the marker-attached clause*, or is it unnamed
residue of a breadth word?**

- **Printed in the clause** — an item of a list the clause spells out, a named entity, a named
  condition. "fatigue, headaches, muscle pains, and fevers" against a lone closed `[[CIT]]`: *fevers*
  is on the page, so it is this source's burden and may not be handed to a sibling. Narrowing here
  deletes gate 6's own first worked example and turns OVERSIMPLIFY into ACCURATE. **Not narrowable.**
- **Unnamed residue of a breadth word** — the clause says "deregulated in diverse cancers" and the
  passage names breast, colon and liver. The cancers beyond those three are nowhere named in the
  clause; you had to supply one in order to object. A sibling may carry that breadth.
  **Narrowable.**

The one exception: an item that carries **its own** visible citation marker is attached to that
marker and not to yours — four vaccines each followed by its own `[[OTHER_CIT]]` or `[[CIT]]` is four
attributions, not one burden. That is the "the clause is what the marker is attached to" rule rather
than narrowing, and it is why a per-item marker list is not caught by the bound above.

**This section applies only to clusters you can see the end of.** A sentence that breaks off inside an unfinished citation list is gate 2's case, not this one, and gate 2 has already decided it: you cannot narrow a burden against siblings you cannot read. Burden-narrowing is what you do once the cluster is visible and the shared proposition is identifiable.

## 3-way collapse

Moved to the enum contract (`verdict_enum_sarol.md`) — it is what the published metric is
computed over, so it is fixed rather than tunable. Do not restate it here; a second copy is a
second thing to drift.
