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

**First, fix what you are judging** — the marker-attached clause, per the first rule under "Fourth"
below. Quote it before you test anything against it.

**Second, this is first-match-wins, and it binds in both directions.** Walk the tests in order from
1. Answer each one explicitly yes or no. **Stop at the first yes and emit that label** — do not keep
going to see whether a later test also passes, and do not skip ahead to a test that looks like the
answer. A later test passing as well is expected and means nothing; that is what "residual" means.

*House note on base rates, from this benchmark's own class distribution — house text:* roughly
**three citations in five are ACCURATE**. ETIQUETTE is about one in eight, NOT_SUBSTANTIATE one in
eleven, IRRELEVANT one in eighteen, and CONTRADICT, OVERSIMPLIFY, MISQUOTE and the two INDIRECT
classes are each under one in thirty. A gate that fires more often than its label occurs is
miscalibrated however good its individual reasons looked, and gates 3, 5 and 6 are the ones with the
least room.

To make the stop auditable, **begin each sub-claim's `nuance` with `gate N:`** — the number of the
test that fired — followed by your one-sentence reason. A verdict whose `nuance` does not name the
gate that produced it was not chosen by this order.

**Third, a gate fires on a finding you can quote, and silence is not a finding. — house text** Your
passages are a keyword-selected sliver of the article (the subset section below has the numbers), so
*my passages do not mention X* is a fact about the window and never about the paper. Gates 1, 2, 6 and 7
each name a label on the strength of a positive finding, so each one has a write-down you must be able
to produce **in order to fire it**. Produce it and the gate fires; fail to produce it and the gate
answers **no** and you walk on. The write-down licenses the label, not the refusal.

- **Gate 1** needs a predicate axis written down and no passage found on it — see test 1.
- **Gate 2** needs a list the clause prints, one member carried at a quoted line and another named
  nowhere in the window — see test 2. That one absence is a finding, because the member's name was
  in the search.
- **Gate 6** needs a passage's own restriction word and a referent the clause prints that it excludes — see test 6.
- **Gate 7** needs a quoted passage sentence that asserts something weaker — see test 7.

A gate disposed of in prose — "not applicable", "relevant to the paper", "no scope difference" — has
not been answered in either direction, and prose can never fire one.

**Fourth, four rules decide more claims than any gate does, so apply them inside every gate rather
than after the walk. — house text**

- **The clause is what the marker is attached to** — not the sentence around it. Background framing
  (what the literature holds, how many studies exist, what a field focuses on, how broad a problem
  is, how many of a citing review's own included studies did something) is not charged to this
  source, and its scope words are not this source's scope. Quote the clause before any gate.
- **You may not fail a clause element-by-element.** Splitting the clause into assertions and charging
  the source for the ones your window does not match is the single commonest way this program
  produces a wrong label. The one exception is gate 2's list test: a printed list member that no
  passage names is decided there, as ETIQUETTE, before any silence rule applies.
- **Three bars are not in the scheme and may not be applied under any gate:** that the source must use
  the citing sentence's causal framing; that it must show a particular method before a claim counts as
  supported; and that a hedged source sentence cannot support a citing clause.
- **The citing authors' own study is not this source's content.** When the clause reports what the
  citing authors themselves did — first person, "we used", "we drew", "our cohort", "here we" —
  the source is cited for the method, dataset, tool or definition they borrowed. That is the whole
  burden: does a passage show the source is, or describes, that method or dataset? The citing
  study's own counts, subjects, cell types and settings are not charged to the source at any gate.
  They are not a differing number at gate 4 and not a `population` shortfall at gate 7.

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

   **An admitted mismatch fires this gate. — house text** Once you have written two slots that do not
   match, you have answered test 1 **yes** and the label is IRRELEVANT; stop here. Writing "the axes
   do not match" and then walking on to gates 7 and 8 is not an answer to this gate, it is a refusal
   to emit the one it produced — and gate 8's naming test will pass on the shared subject every time,
   so walking on always lands on ACCURATE. The clause's predicate is **the whole relationship it
   asserts, qualifiers included**: *death rate is unaffected by treatment status until suppression* is
   not the axis *life expectancy*, and a passage reporting the bare quantity does not assert the
   clause's relationship about it.

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

   **The bound test — house text, and it is one question: does the marker-attached clause name
   parallel items that your passages carry only some of?** It applies to every marker — a lone
   `[CIT]` or `[[CIT]]` as much as one in a cluster. The commonest ETIQUETTE on this benchmark is a
   single marker closing a list of several named things, of which the cited paper is about one.

   **Items** are the members of a list the clause prints — two or more coordinated noun phrases
   that each name a *different* thing: genes or proteins (`NLRP3, NLRP6, and NLRP12`, `BRCA2 and
   DSS1`), drugs or vaccines, diseases or outcomes (`anxiety, depression and mortality`), species,
   loci, assays, or two figures for two different products. Two words for one thing are one item
   (`overweight and obesity`, `EMT/MET`), and a modifier, a mechanism or a detail of how is not an
   item. If the clause prints no such list, gate 2 answers **no**.

   An item is **carried** when some passage names it — by name, abbreviation or close synonym — and
   asserts the clause's predicate of it or reports on it. It is **not carried** when no passage in
   your window names it at all. A list member is a printed name the keyword search was looking for,
   so its total absence from the window is a finding about which part the paper covers, not the
   retrieval silence gate 8 absorbs. Write
   `gate 2: items <...>; carried <items at L..>; not carried <items>`.
   - **Every item carried** → gate 2 answers **no**; walk on.
   - **Some items carried and some not named anywhere** → **ETIQUETTE; stop here.** The marker
     closes a list and the paper is about only part of it — that is exactly "unclear what is being
     cited from the reference article". Do **not** call the uncarried items retrieval silence or hand
     them to siblings and emit ACCURATE for the remainder; that carve-out is this gate's own finding
     written under the wrong label.
   - **No item carried** → gate 2 answers no; walk on and let gates 7 and 8 decide.

   **Ask the attributability question here, not later.** If you find yourself writing "this source's
   attributable portion is …" or "the rest belongs to the siblings" about one clause anywhere in your
   reasoning, gate 2 answered yes. Finding it further down the ladder and writing it as a caveat
   underneath some other verdict is the same mistake made late.
3. **CONTRADICT** — a passage you were given states the opposite of the citing clause. **Quote it.**
   The requirement is that you produce the excerpt verbatim, *not* that the excerpt contain a denial:
   a source need never write "X does not happen" for this gate to fire. — house text It must
   oppose, not merely differ: a source that assigns the claimed property to a *different* agent, or
   reports the claimed status at an *earlier* stage, opposes only if the citing clause cannot also be
   true. Silence never contradicts.

   **One case where a different value always opposes: the cited study's own design. — house text**
   Sometimes the clause describes how the cited study itself was run: the subjects it used (species,
   strain, age, sex), its sample, dose, duration or site. If a passage states that same attribute of
   the source's own study with a value that excludes the clause's, the passage contradicts the
   clause. "Eight to nine-week-old mice" against "the 6–11-month-old mice" is an example, because the
   paper's account of its own design is the fact. Quote both values. This covers design attributes
   only. A clause about the study's *results* is tested as above. A clause about the citing authors'
   own study is not this source's content (see the preamble).

   **Write the clash down with the clause quoted verbatim, not restated. — house text**
   `gate 3: passage '<quote>'; clause '<verbatim quote of the marker-attached clause>'; both cannot
   be true because <reason>`. If you had to strengthen the clause to make it clash — adding *all*,
   *only*, *identical*, *always*, or turning a modelling assumption into a claim about every
   subgroup — you are contradicting your restatement, not the clause, and this gate answers **no**.
   A passage reporting that a quantity differs across subgroups does not oppose a clause that never
   denied it.
4. **MISQUOTE** — a number or percentage the citing sentence attributes to this source differs from
   the source's number for **the same quantity**. Once you have such a mismatch, the label is
   MISQUOTE; do not re-describe it as a scope or emphasis problem and route it to OVERSIMPLIFY.
   "At least 50%" against a source's "at least 41%" for the same measure is MISQUOTE, not a support gap.

   **The write-down is the test. — house text** `gate 4: clause '<number> <the words it measures>';
   passage '<number> <the words it measures>' at L..`. The two "words it measures" must name the same
   outcome, endpoint, subgroup and unit. Four things answer **no**:
   - **A passage prints the clause's figure.** If any passage gives the clause's number for the
     clause's quantity, the source states it. A different figure elsewhere in the window belongs to
     another endpoint, subgroup or timepoint, and that is not a misquote of this one.
   - **The number belongs to the citing study.** A count of what the citing authors did themselves,
     such as "we drew data from eight cohorts" or "we enrolled 40 mice", is not a figure quoted from
     this source. That holds even where the source's own count differs.
   - **Approximation.** When either figure is marked approximate (`∼`, about, approximately, around,
     nearly, roughly), a difference of one unit in the last printed digit is that approximation, not
     a misquote: "∼11%" against "∼10%".
   - **Rounding.** Round the passage's figure to the precision the clause prints (whole units, or
     tens when the clause's figure is marked approximate and ends in 0). If that gives the clause's
     figure, it is a rounding, not a misquote: "53%" or "∼50%" against "52.5%".
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
6. **OVERSIMPLIFY** — a passage itself restricts the finding, in its own words, and the citing
   clause asserts the finding of something that restriction rules out.

   **The bound test, and it is the whole gate: two quotes. — house text** Write
   `gate 6: passage '<restriction>' at L..; clause names '<referent>'`. The left quote must contain
   one of the passage's own restriction words governing the finding the clause cites — *only*,
   *exclusively*, *limited to*, *restricted to*, *specific to* — and the right quote must be a
   referent the **citing clause prints by name** that this restriction excludes. Both quotes, or the
   gate answers **no** and you go to test 7. Put the two quotes in `paper_value` and `claim_value`.

   **A clause broader than your passages is not this gate. — house text** A plural or generality
   word ("diverse cancers", "various bNAbs", "stem cell therapies"), a list item your passages do not
   carry, a dropped study population, cohort, setting or timepoint, a confident summary of a hedged
   finding, or the same finding in other words: none of these is a restriction the passage states,
   and none of them fires gate 6. When a passage asserts the clause's predicate of any member of the
   clause's set, the clause is summarising that finding, and this benchmark labels it ACCURATE.
   It is not a gate 7 shortfall either — gate 7's containment test calls a passage set inside the
   clause's set ACCURATE.

7. **NOT_SUBSTANTIATE** — none of the above fires, and a passage that *does* address the clause stops
   short of it. What "stops short" requires is the next section.

   **Read back your reason before you emit this label, because it names the gate that really fired.**
   NOT_SUBSTANTIATE's reason has exactly one admissible shape: *a passage asserts something of its
   own about this clause's predicate, and what it asserts falls short of the clause.* Write it as
   `gate 7: passage says '<quote>', clause says '<quote>', shortfall = <axis>`, and the axis must be
   one of exactly three: **strength** (the passage recommends where the clause reports a finding, *or*
   the passage's recommendation is permissive — "reasonable to consider", "may be considered", "could
   be used" — where the clause reports a strong or universal directive — "strongly recommend",
   "recommend in all", "is indicated"), **population**, or **stage or setting**. — house text

   ⚠ **`population` and `stage/setting` have a containment test, and it is the whole of those two
   axes. — house text** These two are the commonest wrong fire of this gate, because every paper
   states the population, cohort, site, stage or setting it measured, so a `shortfall = population`
   write-down is producible on *any* claim that reports a finding without repeating that qualifier.
   The write-down therefore decides nothing. **One question decides it: is the group, stage or setting
   the passage reports an *instance of* the one the clause asserts?** Write the answer down as
   `gate 7: passage set <x>; clause set <y>; x is inside/outside/contains y`.

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
     **The axis fires: NOT_SUBSTANTIATE** — but only on a passage that reports the source's own
     finding. A passage carrying its own citation marker (`(12)`, `5-8`, `(Ota et al., 2009)`) is the
     source relaying someone else, not stating what it measured, and cannot fire this axis.
   - **Contains** — the passage's set contains the clause's: "COVID-19 patients" against a clause
     about "severe COVID-19"; "interferons I and III" against "IFN-α". A finding reported of the
     whole set is reported of the member the clause names. **This axis does not fire — go to test 8.**

   This test binds only `population` and `stage/setting`. `strength` has its own test below.

   **`strength` against the banned hedging bar, and the one question that separates them. — house
   text** The banned bar is about *confidence in a result*: a passage that says "may", "might",
   "suggests", "consistent with" or "will need to be confirmed" about a finding it reports does
   support a citing clause stated flatly, and that is ACCURATE. `strength` is about the *force of a
   prescription*: both sides are recommendations and the passage's is optional where the clause's is
   mandatory or universal. **Ask what the modal attaches to.** Attached to how sure the source is of
   a result → confidence, and the verdict is ACCURATE. Attached to how strongly, or to how widely,
   something is advised → `strength`, and the verdict is NOT_SUBSTANTIATE.

   **The axis is a closed list, and the check is literal. — house text** The word after
   `shortfall =` must be exactly one of `strength`, `population` or `stage/setting`. If the word you would write is anything else — *scope*, *specificity*,
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
   - it quotes a passage's own restriction word (*only*, *limited to* …) excluding a referent the
     clause prints by name → **gate 6, OVERSIMPLIFY.** Move the two quotes into `paper_value` and
     `claim_value`.
   - your passages assert a **different predicate** of the clause's subject, rather than a weaker
     value of the clause's own predicate → **gate 1, IRRELEVANT.** A matching subject does not save
     it; gate 1 fires on the axis, not the topic. Silence on the predicate alone still does not
     qualify — a mismatch needs a passage that asserts the *other* axis.
   - a number or percentage in the citing sentence differs from the passage's number for the same
     quantity, and gate 4's write-down holds → **gate 4, MISQUOTE.**

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
   (When the clause lists several agents or subjects and the window names some of them and not the
   others, gate 2 has already answered ETIQUETTE; this paragraph does not reach it.)
   Worked: a clause about bortezomib causing vacuolation in DRG satellite cells, against a window
   where several passages discuss mitochondrial damage and apoptosis and none names bortezomib, DRG
   or satellite cells — the shared axis is why gate 1 did not fire, and the missing agent is why this
   is not ACCURATE.

   **You may not reach this gate by skipping the ones before it** — each of 1 to 7 has to be answered.
   But reaching it because none of them produced its write-down is not skipping: on this benchmark it
   is the commonest correct outcome.

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
  weakly, for a population or setting outside the clause's, or only as a recommendation rather than
  a finding. That is a real shortfall: **NOT_SUBSTANTIATE**.
  (Not OVERSIMPLIFY. Gate 6 is decided by its own named test and nothing here routes into it.)
- **No passage addresses the clause, but the passages are plainly about the clause's own entities and
  relationship** — the paper studies this and your window did not return the sentence. That is
  retrieval silence: **ACCURATE**. Do not require the citing sentence's wording to appear in the
  window, and do not enumerate the sentence's elements and fail it on the first one you cannot match.
  **"Plainly about the clause's own entities" is the literal test in gate 8** — the clause's agent
  **or** its subject named in some passage — and not a judgement about topic overlap. If neither can
  be named, you are on the next bullet but one.
- **No passage addresses the clause, some passage is on its predicate axis, and no passage anywhere in
  your window names the clause's agent *or* its subject** — relevant paper, nothing substantiated:
  **NOT_SUBSTANTIATE**, per gate 8's bound. Both missing, not one: one of the two missing is a
  retrieval hole and stays ACCURATE. — house text
- **No passage addresses the clause and the passages are about something else** — IRRELEVANT, per
  test 1 above.

The three banned bars stated in the preamble apply here too, and two of them have a habit of
surviving as a *different label* once you have been told not to score them as a support gap. Naming a support gap "an overgeneralisation" does not make it one, and the
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

⚠ **That exception is about the *value*, not about the field. — house text** `overall_verdict` is a required top-level field on every output: write it, carrying that value. A file whose `overall_verdict` is missing or null is rejected (`MISSING_FIELD:overall_verdict`) and the claim scores as a miss whatever the sub-claim said — this has already cost this program a claim.

## Multi-citation handling (critical — 51% of Sarol data) — house text

The dispatch supplies `multi_cit_context`: `"single"` when the evaluated citation stands alone at this position, `"grouped"` when it is one of a `[1,2,3]`-style cluster. **That field is the trigger.**

When `multi_cit_context == "grouped"`, the sentence's *other* clauses — the ones a sibling marker closes, or the framing around the marker-attached clause — do not count against the current source. **Nothing is narrowed inside the marker-attached clause. — house text** If your passages carry only some of that clause's items, gate 2 has already answered ETIQUETTE; if they carry all of them, the whole clause goes on down the ladder. "ACCURATE for this source's portion" of a single shared clause is not a verdict this rubric produces.

⚠ A sentence can carry sibling citations while `multi_cit_context` is `"single"`. An `[OTHER_CIT]` placeholder in the claim text says so. Narrow this source's burden the same way when you see one.

⚠ **Those two are the only triggers, and you must quote the one you used. — house text** Before you narrow anything, write `burden narrowed: multi_cit_context=grouped` or `burden narrowed: [OTHER_CIT] visible`. If you can write neither — `multi_cit_context` is `"single"`, is absent from your inputs, or you are unsure what it was, and the claim text contains no literal `[OTHER_CIT]` — then **there is no sibling and you may not narrow.** The whole marker-attached clause is this source's burden, every item in it.

A sibling you have *inferred* from the shape of the sentence is not a sibling. "A sibling citation may cover the remainder", "the rest is presumably cited elsewhere", "this source's portion is the first three items" — written against a lone closed `[CIT]` or `[[CIT]]` — is you supplying the co-citation. Without a quotable trigger the whole marker-attached clause goes down the ladder as this source's burden.

**This section narrows across clauses, never inside one. — house text** A clause whose list items your passages carry only in part is gate 2's case (ETIQUETTE) whether or not it is shared with co-cited sources, not a burden to narrow here.

## 3-way collapse

Moved to the enum contract (`verdict_enum_sarol.md`) — it is what the published metric is
computed over, so it is fixed rather than tunable. Do not restate it here; a second copy is a
second thing to drift.
