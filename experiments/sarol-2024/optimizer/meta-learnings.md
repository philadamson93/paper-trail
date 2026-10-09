# Meta-learnings — what iterations have established

Continuity across optimization sessions. Each iteration runs in a fresh session with no memory of
the previous one (deliberately — a retrospective evaluation of version N has to be blind to
everything learned after N), so this file is the only thing that carries forward.

**Read before iterating. Append after.** Move entries between sections as evidence accumulates;
do not delete them. A reverted attempt is as useful as a confirmed one, and more likely to be
retried by accident.

**What belongs here rather than in an iteration's findings note** is defined in one place: the
*"The three record surfaces, and what goes in which"* section of
`experiments/sarol-2024/optimizer/prompt/optimizer-instructions.md`. The short form is that this
file is about *how to optimize this task* and that one is about *these examples* — but do not
carry a second copy of the rule in your head from here.

---

## Status

**Reset-state text was inherited, but the program was NOT fresh.** The paragraph that used to sit here
said this lineage had established nothing and that the sheet is reset only "when a run starts fresh
from program-v0's content". On `hillclimb-2026-10-08b` iteration 1 that was false in its premise:
`frontier.best_tag` / `current_tag` were **`program-v11`** and the working tree was byte-identical to
`/workspace/ro/versions/restored-program-v11`, with `/workspace/ro/notes/` empty. So a mature program
arrived with no notebook and no notes. **Deleted the "fresh lineage" claim rather than leaving it to
mislead the next session.** Entries below start at iteration 1 of `hillclimb-2026-10-08b`.

⚠ **Verify the program's tag against this sheet's contents before trusting either.** One `diff -rq`
against the matching folder in `/workspace/ro/versions/` tells you whether the notebook you are reading
belongs to the program you are editing. ⚠ **Check `ls /workspace/ro/versions/` for the name first.** The
folders are *not* all `restored-program-v<n>`: at iteration 2 the baseline for `frontier.current_tag`
`program-v12` was `iter2-current` (and `iter1-program-v12`), with **no** `restored-program-v12`. Guessing
the path returns nothing and looks like "the program is unmodified".

Record what *this* run establishes. Sections are ordered by how settled a claim is; move entries
between them as evidence accumulates rather than rewriting them in place.

⚠ **One measurement fact you need before your first entry, because it decides what counts as a
result:** the instrument's own scatter is **0.06** — a byte-identical program re-scored 0.48 vs
0.42 on the same 50 claims. A single-iteration delta of 0.02–0.04 is *inside* that scatter. Write
those down as hypotheses seen once, never as settled results.


**2026-10-09 (iter 2) — the v13 restore is confirmed by repeat measurement:** v13 content scored
**0.76 and 0.76** on the same first-50 VAL claims (v13 in `hillclimb-2026-10-08b`, v17 in this run),
against 0.66 for v16. The v14–v16 decline was the rubric, not scatter. v17 on VAL n100: 0.71 (floor
0.69). **Judge later edits against v17's re-grade on the current VAL, never against TRAIN.**

**2026-10-09 (`hillclimb-sched-2026-10-09` iter 1) — this run started on `program-v16`, and at
iteration 1 the rubric and dispatch were restored byte-for-byte to `program-v13`.** So every
Confirmed entry below that describes a rule added by v14–v16 (gate-3 rewrite and refusal write-down,
gate-6 breadth word and (a)-minus-(b) span classifier, banned slot fills, gate-1 axis restorations)
**describes text no longer in the program.** The lessons about *how* to write rules still stand; the
rules themselves are gone. Verify with one `diff -rq` against `/workspace/ro/versions/restored-program-v13`.

## Confirmed

*(Claims this run has tested more than once, in the same direction.)*

**2026-10-08 (iter 5) — ⚠ THE MOST EXPENSIVE LESSON OF THIS RUN, and it is about *how you delete*:
a deletion that cuts inside a sentence silently removes the operative half of a bound, and an
aggregate TRAIN threshold cannot see it.** Iteration 4 made thirteen deletions, each justified as a
redundant roster anchor or a duplicated meta-argument. **Three of them straddled a sentence boundary**
and left the judge reading, verbatim: *"…will pass on the shared subject every time,"* (gate 1, lost
"so walking on always lands on ACCURATE" **and** the predicate-is-the-whole-relationship rule, with
**zero** paraphrase left anywhere in the file); *"…that shortfall, if it is"* (gate 6, lost the
routing destination into gate 7); *"…whatever the containment"* (gate 7, lost "direction says — go to
test 8", leaving its Inside/Outside bullets hanging off an unfinished sentence). **Both of iteration
5's new misses sat at two of those three loci and both had been correct for three iterations.** The
prediction that the deletions were free *held on its stated observable* — TRAIN accuracy and macro
both cleared their thresholds — because two unrelated fixes exactly cancelled the two regressions. 44
of 49 both times, 34 of VAL both times, zero net movement. **Two standing procedures follow.**
(i) After any deletion pass, run a scripted scan for paragraph-final lines ending in a comma or a
bare lowercase word, re-check every count phrase ("Five things…", "exactly four axes") against the
items that actually follow, and re-resolve every cross-reference ("see the next section", "per the
rule above") — iteration 4's pass left **three** truncations, **two** stale counts, **two** dead
section pointers and **one dangling cross-file reference** from `adjudicator-dispatch-sarol.md` into a
rubric rule it had deleted. (ii) **Never grade a deletion on an aggregate alone.** Diff the per-claim
label table against the previous iteration and name the claims that moved in each direction; an
aggregate that holds while two claims regress and two improve is the normal case, not a rare one.

**2026-10-08 (iter 5) — the fifth attempt at gate 6 is the first that is a *string comparison*, and
the shape is now general enough to reuse: classify the **span**, not the relationship.** Four
previous bounds on gate 6 failed because each asked the judge to characterise something — is (c)
"inside" (b), is (b) "a set", is this a "genuine widening" — and a characterisation is satisfied by
assertion. The bound that measured 15-for-15 instead says: find **the span of (a) that (b) does not
print**, write it down on its own, and decide by **what kind of word it is**. A quantity expression
governing a head noun the clause prints verbatim → fires. The proper-name identifier of the single
referent the paper measured → fires. An item the clause itself prints → fires. ⚠ **An attributive
adjective before a noun phrase the clause prints verbatim → does not fire.** The undifferentiated
"(c) is the complement of a modifier the paper carries" class is **2–2 and discriminates nothing**;
split by the span's lexical class it is **2–0 / 0–2**. **Generalised procedure: when a rule needs the
judge to compare two expressions, make the rule be about the sub-string that differs, and about its
part of speech. That is a question with a wrong answer.**

**2026-10-08 (iter 5) — the frozen definitions file is a *source of edits*, not only a check, and
nobody had mined it that way.** `verdict_definitions_sarol.md` records three divergences *we* once
introduced and removed. One of them — OVERSIMPLIFY's appended "qualified-in-source but unqualified in
claim" — turned out to be **exactly what gate 6's house machinery had quietly re-implemented**, and
gate 6 is the gate firing 3.9× its dev rate. **Standing check: for any class whose firing rate is far
off its dev prior, read that class's row in the "three corrected divergences" table and ask whether
the house layer has grown the divergence back.** A removed divergence is a hypothesis about gold that
has already been falsified once; finding it reconstituted in the clarifications layer is the cheapest
rubric defect there is to find.

**2026-10-08 (iter 5) — a write-down slot gets filled with the conclusion it was supposed to produce,
and that is a distinct defect from an unbound trigger.** Three of 49 ledgers filled a required slot
with a self-description instead of a quotation: gate 1's `<axis>` slot with *"the same axis"*, gate
7's scan slot with *"no other passage asserts a **weaker** version"*. The second one survived an
iteration-4 edit that told the judge the string was literal and *moved to a different two claims*
rather than disappearing. **So: when you require a quotation, enumerate the self-descriptions that are
banned, by name.** "The slot must be quoted from a passage" is not enough; "'the same axis', 'a
matching axis', 'nothing broader' are the conclusion written into the slot" is. Iteration 5 tests
this remedy at two gates at once.

**2026-10-08 (iter 5) — the judge cannot see a previous version of the rubric, so archaeology in the
prompt is pure cost.** Two iteration-4 additions explained what *used to* stand in their place ("What
used to stand here voided both by requiring…", "the previous test here — whether (c) lies 'inside' (b)
— did not break it"). Those sentences are addressed to the optimizer and they ride in the judge's
context on every claim. **Write the rationale for an edit in `findings.md`, never in the rubric.**

**2026-10-08 — `nuance` is the trace. Read it before you spend anything on transcripts.** Under
`retrieval` on `claude-haiku-5-5` the adjudicator emits one or two sentences of visible text — it reads
its three files and writes the JSON — and records its entire ordered gate walk inside
`sub_claims[].nuance`. That field is already in the mistake corpus as
`adjudicator_reasoning.nuance`, so **the cheapest possible gate-compliance audit is free**, needs no
subagent, and covers every claim. (Opening the trace jsonl is still how you reach a *correct* claim's
nuance, via the `Write` tool-call input; `run_manifest.json` has the verdict but not the nuance.)
Confirmed twice: on the 11 misses and on all 38 correct answers of the same batch.

**2026-10-08 (iter 2) — correction to the above, and it makes the census free rather than cheap: the
`nuance` of a *correct* answer is in `/workspace/ro/feedback/iter/<n>/files/<claim_id>.json`, not only
in the trace.** `files/` carries one **ledger JSON per claim** — every claim, not just the misses —
with `sub_claims[].nuance` and `overall_verdict` in plain form beside the trace jsonls. The full
gate-fired × verdict × correct census over 50 claims is one 15-line script over those files; no
`Write`-tool-input extraction and no subagent. Keep the trace route only for what the judge
*considered and rejected*, which is still where the decisive quote came from on one claim. **⚠ The
canary's ledger file is in `files/` but the canary is not in `run_manifest.json`'s `claims[]`** — glob
`files/*.json` and you get n+1.

**2026-10-08 (iter 2) — the control census is now confirmed, not pending, and it is the step to run
first.** Twice now it has turned a complaint into a rule by answering "what does a *correct* fire of
this gate look like": at iter 1 it bounded gate 6, at iter 2 it produced the containment test from a
6-row table (`population` 0/2 correct, the other three axes 4/4). **Both times the discriminator was
invisible in the mistake corpus**, because the corpus has no correct fires to contrast against. It also
twice stopped an edit: measuring exposure before narrowing showed one rule was load-bearing on exactly
one correct answer (a 1-for-1 coin flip, not an edit).

**2026-10-08 (iter 3) — PROMOTED, and it is this rubric's signature defect: a rule whose trigger is a
write-down the judge can always produce is unbound however closed it looks. Three independent
occurrences now, in three different places.** (i) iter 1: gate 6's named excluded member (c) —
producible on any claim, because every source's study population excludes *something*. (ii) iter 2:
gate 7's `shortfall = population` — producible on any claim, because every paper states the
population it measured. (iii) iter 3: the burden-narrowing trigger `multi_cit_context=grouped` —
producible on **two claims in five**, so iter 2's "quote the trigger" bound bounded the rule in form
only and the claim it was written for (`1360-20`) was still mislabelled. **The remedy has been the
same all three times, and it is a *direction*, not a magnitude:** gate 6 asked what the excluded
member is a different *kind* of; gate 7 asked whether the passage's set lies *inside* or *outside*
the clause's; narrowing asked whether the narrowed-away referent is *printed in the clause* or is
residue you had to supply. **Standing procedure before you write any new rule: state its trigger,
then ask on what fraction of an arbitrary batch the trigger is producible. If the answer is "most",
find the asymmetry instead.**

**2026-10-08 (iter 3) — the corollary that costs the most: a quotable trigger is not an auditable
one.** iter 2 bound narrowing to `burden narrowed: multi_cit_context=grouped`, believing a required
quote was a bound. But the field is interpolated into the judge's *initial prompt*, which no trace
and no manifest records, so the value cannot be checked — and the judge both over- and
under-applied it (narrowed on 11 of the 20 claims it reported as grouped, declined on 9, same
reported value). **Before binding a rule to an input field, check that the field's value is
recoverable from the artifacts you will grade against.** If it is not, bind the rule to something in
the claim text instead.


**2026-10-08 (iter 4) — ⚠ THE MOST EXPENSIVE THING ON THIS SHEET, and it invalidates how three
iterations read their own results: "measure the exposure before you narrow" measures *TRAIN*
exposure, which is precisely the quantity that cannot bound VAL.** Iterations 1-3 each measured a
new rule's exposure at or near zero over the fixed 50-claim TRAIN roster and shipped it. At iter 4,
**eleven of iteration 3's twelve predictions held - and the twelfth was the objective.** TRAIN
0.8571 -> 0.8980 while VAL 0.76 -> 0.6939. A rule whose TRAIN exposure is zero can have large VAL
exposure *by construction*, because the roster is fixed and the rule was written from it. The
exposure measurement is still the right step - it has stopped four bad edits now - but **it licenses
"this does not break the claims I can see", never "this generalises".** Grade an iteration on the
VAL trend, and treat a TRAIN-only confirmation as unresolved.

**2026-10-08 (iter 4) - the cheapest high-yield measurement in this loop, and nobody had run it: compare
your per-class *firing rate* to the published class priors of the pool the held-out split is drawn
from.** `/workspace/ro/in/context/task-and-scoring.md` carries drawable gold per class for **both**
pools (TRAIN n=2076, dev n=311; VAL is drawn from dev). One table lookup plus one division over the
predicted labels in `run_manifest.json` found three badly miscalibrated classes and **about 9 claims per
50 of misallocated label mass** - the same order as the whole TRAIN-VAL spread - none of which was
visible in a 5-record mistake corpus: CONTRADICT fired **0%** against a 7.1% dev rate, ETIQUETTE
**4.1%** against 12.2%, OVERSIMPLIFY **10.2%** against 2.6%. **Two further things this found that
per-claim reading cannot:**
(i) the rubric's own house base-rate note matched the **TRAIN** pool on all five of its figures and
was wrong by **2.5x** on CONTRADICT for the split actually scored;
(ii) **the fixed TRAIN roster systematically mis-ranks exactly the miscalibrated classes** - it drew
CONTRADICT 1 (2% vs dev 7.1%), ETIQUETTE 3 (6% vs 12.2%), OVERSIMPLIFY 3 (6% vs 2.6%) - which is
*why* fourteen versions of mistake-corpus reading never found any of it. **Run this in step 2, before
you look at a single failure.**

**2026-10-08 (iter 4) - a gate with no required write-down fires zero times and is invisible to every
audit you can run.** Gate 3 (CONTRADICT) was the one gate the preamble's write-down list did not
name. Census over 49 ledgers: **0 fires**, 22 claims never mentioned it, 19 disposed of it in the
unquoted prose the rubric's own rule forbids. The rubric had been telling the judge "a gate disposed
of in prose has not been answered in either direction" while giving that gate nothing to write. **So
when a class scores F1 0.000, check whether its gate has a write-down before you theorise about its
boundary** - and note the asymmetry: every write-down in this rubric licensed *firing*, so the
refusal side of every gate was unauditable. A required **refusal** write-down is the obvious
instrument and iter 4 is the first test of one.

**2026-10-08 (iter 4) - the signature defect's fourth occurrence, and the remedy sharpens: replace a
*judgement* with a *quotation*, not merely with a direction.** Iter 3's own fix for gate 6 - "(c)
must lie inside (b), and you must say why" - became the fourth instance of the thing it was written
to cure, because the judge satisfied it on **all four** claims where it appeared, including the one
it got wrong, by simply *declaring* "(b) is unqualified and independent of the predicate". The
notebook's standing remedy ("find the asymmetry, not the magnitude") was followed and still failed,
because "which way does it point" was itself a judgement the judge gets to make. **What the repair
needed was a property of the text the judge must copy out**: (b) must carry a breadth word - an
enumeration, a plural/mass class noun, or a generality word - or there is no set for the clause to
widen. **Updated standing procedure: state the trigger, ask what fraction of a batch can produce it,
then ask whether answering it requires the judge to *characterise* something or merely to *quote*
something. If it is a characterisation, it is not yet bound.**

## Pending

*(Claims seen once. Most single-iteration deltas belong here, not above.)*

**2026-10-09 (`hillclimb-sched-2026-10-09` iter 5) — a house *precondition* on a gate can encode the inverse of how gold uses
the label. Find it by splitting the gold class on the precondition's own variable.** Gate 2 required a quotable sibling
before ETIQUETTE could fire. But **26 of 27 gold-ETIQUETTE claims on a 200-claim fresh-weighted TRAIN carry a lone marker**,
so the precondition closed the class's main route. The tell was in two places nobody had cross-tabulated. The judge's ledgers
wrote the ETIQ finding as a caveat under ACCURATE ("NLRP6 and NLRP12 are not in the window, which is retrieval silence").
And the gate's *existing* fires split by whether the sibling was visible in text: flag-only (lone in text) were 14 ETIQ / 5 ACC
over iters 3–5, visible-sibling were 10 / 8. **Procedure: for any gate with a precondition, tabulate gold for the class
against the precondition's yes/no before you tune the gate's body.** Edit: sibling precondition deleted, item test bound to
distinct named list members. Pending until graded (T1–T8 in that iteration's findings). If ETIQ precision falls below 0.45,
narrow it.

**2026-10-09 (iter 5) — on a retire-weighted TRAIN, measure a new rule's exposure on the *fresh* claims, not the batch.**
Across all 199 claims the gate-2 extension looked 12 gains / 5 losses. On the 93 fresh claims it was 5 / 3. Carried claims are
the program's past errors, so any rule that fixes errors looks better on them by construction. The fresh ratio is the one
that predicts VAL.

**2026-10-09 (`hillclimb-sched-2026-10-09` iter 4) — on a fresh-draw distribution, a gate whose class barely exists in
gold should be cut to a quotable two-quote trigger, not bounded again. Bounding it only re-routes which shape fires.**
Across ~250 distinct TRAIN claims this run, gold OVERSIMPLIFY appeared **once**, while gate 6 fired **0/21** over v16–v19.
Iteration 3's E2 ("a plural is satisfied by two; an unprinted (c) only when exactly one member") **raised** OS fires from
4 to 14 (0 right). The "exactly one member" clause was itself a new producible trigger, and a 20-passage window nearly always
shows one member. That is the signature defect again, created by the fix. Iter 4 replaced the gate with "passage's own
restriction word (*only*/*limited to*…) + a referent the clause prints that it excludes" and deleted about 75 lines. Gate 7's
class-vs-member axis and relayed-passage "outside" fires (0/5) were cut in the same edit, so the mass cannot relocate to NS.
**Procedure: before bounding a gate a fourth time, count gold support for its class across every TRAIN batch of the run.
If the gate's fresh precision is ~0 and support is ~0, narrow it to a literal-quote trigger and route the rest to ACCURATE.**
**Graded at iter 5: held.** OS fires 14 → 0, 4/4 named claims → ACC, NS fires stayed at 3 (no relocation), carried diff 19 FIX / 8 REG, VAL n250 v20 0.651 vs v19 0.644 (inside scatter). Cutting a near-zero-support gate to a literal two-quote trigger and deleting ~75 lines cost nothing measurable.

**2026-10-09 (iter 4) — iteration 3's point fixes held (5/5 targeted claims moved) while its aggregate prediction failed.**
Named-claim predictions are cheap to satisfy. A gate-level count prediction (R5: OS ≤ 2, measured 14) is what caught the
regression. Always pair the two.

**2026-10-09 (`hillclimb-sched-2026-10-09` iter 3) — precision figures measured on the old fixed
roster do not transfer to a fresh draw. Re-measure every firing gate's precision on the *fresh* claims
of each TRAIN batch before trusting it.** v13's gates were tuned over a Jaccard-1.000 roster to
NS precision 0.83, IRRELEVANT 1.00 and OVERSIMPLIFY 0.60. On this run's fresh-draw TRAIN the same text
(v17/v18) fires OVERSIMPLIFY **0/7**, MISQUOTE **0/5**, NS 1/8 and IRRELEVANT 2/4. In iteration 3,
**every non-ETIQUETTE non-ACCURATE verdict was wrong (0/14, 10 on gold ACCURATE)**, and VAL n150 sat
at the floor (0.653 vs 0.647). Each false fire traced to a house rule the judge *obeyed*, not one it
skipped. Gate 4 had "rounding / another cut / the citing authors' figure are all MISQUOTE". Gate 6 read the window's
enumeration as a closed list. Gate 7 charged a methods citation for the citing study's own cells.
**Procedure: in step 2, split TRAIN into carried and fresh claims (`train_schedule.json` of n−1
gives the carried set). Compute per-predicted-label precision on the fresh ones.** That number is
the unbiased one, and one script over `run_manifest.json` plus the corpus produces it. Iteration 3
bounded gates 3, 4 and 6 and added a citing-authors'-own-study rule. **Graded at iter 4:** the gate-4 bound and the
own-study rule held on every named claim (MISQUOTE 1/2 right, up from 0/5). The gate-3 design rule did not fire on
its target. The gate-6 bound made things worse (see the iter-4 entry above).

**2026-10-09 (iter 3) — iteration 2's ETIQUETTE edit is graded: it held on its own boundary and was
invisible on VAL.** ETIQUETTE F1 went 0.25 → 0.61 on TRAIN (7/12 recalled, 7/11 precise), and the three
named claims all flipped. VAL: v18 0.653 vs v17 0.640 on n150, but 0.65 vs 0.71 on n100. Same two
programs, opposite signs on nested batches, so it is scatter. **The ledger-sentence trigger (the judge's own
"attributable portion" carve-out) is confirmed as a usable discriminator.** The remaining ETIQUETTE misses
are single-marker claims, which gate 2(i) shuts by design. Gate 2(ii) also counts window silence as
"not carried" (3 false fires), and its correct fires use the same step.

**2026-10-09 (`hillclimb-sched-2026-10-09` iter 2) — the ETIQUETTE gap was a *competing-guidance*
problem, not a trigger problem. Find the discriminator in the judge's own ledger, not in the
sentence's punctuation.** The thirteen syntactic triggers measured in iter 5 below (all ≤ 50%) were
all searches over citation punctuation. On a fresh 50-claim roster with 6 ETIQUETTE, the
discriminator turned out to be a *step the judge already writes down*: on every gold-ETIQUETTE
grouped claim the `nuance` hands part of the **one** marker-attached clause to siblings ("this source's
attributable portion is…"). It does this on 0 of the 10 gold-ACCURATE grouped claims, which either
found the whole clause carried or narrowed only across clauses. The rubric's multi-citation section
and dispatch step 4 ordered that carve-out and then ordered ACCURATE for the remainder, and gate 2
forbade firing on visible co-citation, so three passages agreed on the wrong answer. Edit: within-clause
carve-out → ETIQUETTE at gate 2; across-clause narrowing kept; the "ACCURATE for the attributable
portion" sentence deleted from both files. **Pending until graded (prediction Q1–Q8 in that
iteration's findings).** **Generalise: when a class under-fires, census the *other-label* ledgers
for the sentence in which the judge argues itself out of it.** That sentence is a better trigger than
any surface feature, because the judge has already computed it. The census over the per-claim output
files in `files/` took one script.

**2026-10-09 (iter 2) — gate 5's third bound ("the marked passage must be the *only* one carrying
the clause's entities") is measured as a two-sided bound; do not loosen it under accuracy.** It
suppressed 4 gold INDIRECT/INR on TRAIN *and* released gate 5 on ≥ 4 gold-ACCURATE claims with the
same ledger sentence ("L.. carries a marker, but L.. carries the same entities unmarked"). Loosening
it would be about 50% precise on TRAIN. On VAL it is negative: INDIRECT is about 2% of dev, INR 0%, ACCURATE about 60%.
Revisit only if the objective changes to macro.

⚠ *Superseded 2026-10-09 (iter 2): a fresh roster held 6 ETIQUETTE and the discriminator was a ledger step, not punctuation — see the entry above.* **2026-10-08 (iter 5) — ETIQUETTE's 3× under-fire is now measured twice and dropped twice; treat it
as a *roster* limit, not an open edit.** Iteration 4 measured two candidate gate-2 triggers at 1-for-2
and 1-for-6. Iteration 5 measured **thirteen** over all 49 scorable citing sentences: the best two are
exactly **1 of 2 (50%)** (comparator + negated predicate; fronted concessive), the appealing
"one marker over a multi-clause sentence" family runs at **0–10%**, and the only 100%-precise rules
fire on the single claim they were fitted to. Current gate 2 is 2 fires / 2 correct. **Since widening
at 50% precision is net-zero by construction, the remaining ETIQUETTE mass (≈4 VAL claims, the largest
single unfixed block) is not reachable from a roster holding 3 ETIQUETTE claims of which 2 are the
signature already covered.** Do not re-derive this a third time; log it and ask for a re-draw.

**2026-10-08 (iter 5) — the first required *refusal* write-down worked, and it worked fast.** Gate 3
had fired **0** times in fourteen versions and was disposed of in unquoted prose on 41 of 49 claims.
Adding `gate 3: tested <conjunct> … against L..; nothing opposes` put the write-down in **42 of 49**
ledgers in one iteration and the gate fired twice, taking CONTRADICT F1 from **0.000 to 0.667**.
**Generalise: a class at F1 0.000 whose gate has no required write-down is not a boundary problem, it
is an unanswered gate — and the refusal side is the half that was missing, because every write-down in
this rubric licensed *firing*.** The cost showed up immediately in the other direction: the gate's one
false fire opposed a **presupposition** of a contrastive adjunct ("*unlike* infection or interferon
responses") rather than anything the clause asserts. **When you un-blind a gate, bound what counts as
the clause's own content in the same iteration.**

**2026-10-08 (iter 3; ⚠ half of this proved too weak — see the iter-4 Confirmed entry on base rates.
Ask for the class's dev *rate*, not merely whether it exists. Iter 4 found CONTRADICT at 22 in dev,
1 in 14, the fourth commonest of nine, being written off as support-1 noise on exactly this
reasoning for three iterations.)** ⚠ TRAIN carries classes that cannot appear on VAL, so some TRAIN misses are
worth exactly zero against the objective. Check before you spend an edit.** `verdict_definitions_sarol.md`
records INDIRECT_NOT_REVIEW as **25 occurrences in `claims-train.jsonl` and 0 in dev** — and VAL is
drawn from the dev pool. Our TRAIN roster carries one (`330-15`), which three iterations have now
chewed on. **A gate-5 widening to reach it can gain at most 1 TRAIN point and exactly 0 VAL points,
while exposing VAL to false positives.** The objective is VAL accuracy. Generalised rule: before
building for a rare class, ask whether it exists in dev at all; the definitions file's own counts are
the cheapest place to check, and TRAIN-only classes are a trap that looks like rare-class work.

**2026-10-08 (iter 3, ⚠ SUPERSEDED AT ITER 4 — kept because the superseding is the lesson).** Iter 3
recorded "three rising points … the overfitting gap is closing" on VAL 0.60 → 0.70 → 0.76 with the
TRAIN−VAL spread narrowing 0.19 → 0.137 → 0.097. **Iteration 4 made it 0.60 → 0.70 → 0.76 → 0.694
with the spread at 0.204** — widest of the run, reversing three iterations of narrowing in one step,
while TRAIN went on rising to 0.8980. So the narrowing spread was **not** evidence that
roster-fitting was under control; it was three steps of a trend that turned. Read a TRAIN−VAL spread
as a lagging indicator, never as reassurance, and do not write "the gap is closing" off three points.

**2026-10-08 (iter 3) — "measure the exposure before you widen" has now also stopped an edit by being
*impossible*, and that is a legitimate reason to drop one.** The designed gate-3 fix for `140-50`
needed to know how many correct answers write an opposing fact into a `remediation` field without
firing the gate. **`remediation` is not a field in the per-claim ledger**, so the count could not be
made at all. Dropped rather than guessed, on a gate the rubric's own base-rate note flags as having
the least room, for a class with TRAIN support 1. **When exposure is unmeasurable, treat it as high,
not as zero** — an absent surface is not an empty one.

**2026-10-08 (iter 3) — the error budget has now ping-ponged between exactly two classes for three
iterations, and that is a property of the ladder worth planning around.** iter 1 fixed OVERSIMPLIFY
precision (0.29 → 0.67) and paid in NOT_SUBSTANTIATE precision (0.75 → 0.56). iter 2 fixed
NOT_SUBSTANTIATE precision (0.56 → 0.83) and paid in OVERSIMPLIFY precision (0.67 → 0.40). Gates 6
and 7 sit next to each other on a first-match-wins ladder and share a boundary, so **mass pushed out
of one lands in the other unless the receiving gate is bounded in the same iteration.** The net is
still up every time (−3, −1 misses), so this is not futile — but **budget an edit for the receiving
gate every time you bound one of the pair**, and read both precisions together rather than one.

**2026-10-08 (iter 3) — two blame subagents on disjoint slices converged on the same bound without
being told the hypothesis, and that is the strongest evidence a cheap fan-out produces.** My own
control census and slice A reached "you may not narrow away a referent the clause names in so many
words" independently — I from an 11-row narrowing table, it from the run-time rubric's own asymmetry
(the existing bound sat only on the *no-trigger* path). **Worth knowing: a blame subagent reading the
frozen `/workspace/ro/versions/iter<n>-current` snapshot rather than the working copy will notice
when you have already edited the file mid-session, and will say so.** Tell them which snapshot to
read, or they spend tokens discovering it.

**2026-10-08 (iter 2) — ⚠ the generalised form of this loop's central error: a wrong gate that you
bound is a wrong gate you have *relocated* unless you also bound where you routed it to.** Iter 1
correctly took study-scope bounds out of gate 6 — OVERSIMPLIFY precision 0.29 → 0.67, the edit worked
— and routed them to gate 7's `population` axis with the proviso "only if gate 7's own write-down can
be produced there." That proviso is vacuous: every paper states the population it measured, so the
write-down is producible on any claim of that shape. **NOT_SUBSTANTIATE precision fell 0.75 → 0.56 by
exactly the mass gate 6 gave up.** The notebook already carried the local lesson ("a gate that can
always produce its own write-down is unbound in practice"); the new part is that *the receiving gate
needs the same audit as the one you fixed*. **Before you route a mode from gate A to gate B, ask
whether B's write-down is producible on an arbitrary claim of that shape — and if it is, write B's
bound in the same iteration.**

**2026-10-08 (iter 2) — the shape that both bounded gates needed was the same one: a *direction*, not a
threshold.** Gate 6's repair asked what the excluded member is a different *kind* of; gate 7's asked
whether the passage's set lies *inside* or *outside* the clause's. Both replaced "can you produce the
write-down" (always yes) with "which way does it point" (a question with a wrong answer). **When a
rule's trigger is unbound, look for an asymmetry in the thing itself before reaching for a magnitude
word** — "substantial", "peripheral" and "materially" are what you write when you have not found the
direction yet.

**2026-10-08 (iter 2) — the loop's first real gain, and what it was made of.** VAL **0.60 → 0.70** and
TRAIN 0.7917 → 0.8367, with `macro_f1_renormalised` **0.5394 → 0.6015** — accuracy up *and* macro up,
so none of it was bought by collapsing toward ACCURATE. The iteration that produced it made **ten**
edits at once across four label boundaries; ten of its twelve predictions held, and the per-class
movement attributed them individually anyway because they targeted different classes. **A ten-edit
iteration was not harder to read than a one-edit iteration** — it was cheaper per point and the
attribution came free from `per_class_f1_9way`. Bundle, but bundle across boundaries.

**2026-10-08 (iter 2) — the two highest-yield edit *shapes* in this rubric, both now seen twice: a
clause that states a rule and then excuses it, and a trigger whose gating field may never arrive.**
(i) *"…which is the one thing this test exists to reject. Say so and carry the mismatch forward."* The
judge takes the second half every time, and the symptom looks like a skipped rule. Grep your own added
prose for a sentence that ends by sending the judge onward from a test it just passed. (ii) The
multi-citation rule says "that field is the trigger. There is no marker in the claim text to look for"
— and when the field is absent or unrendered, the judge **supplies a sibling from the shape of the
sentence** and narrows the burden against it, which deletes gate 6's excluded member. **A rule gated on
an input may not assume the input arrives: say what to do when it is missing, and require the trigger
quoted.**

*(The control-census entry that stood here was **moved up to Confirmed** at iteration 2, where it
now carries both iterations' evidence. Not deleted — promoted.)*

**2026-10-08 — a gate that can always produce its own write-down is unbound in practice however closed
it looks on paper.** Gate 6 demanded a named excluded member (c) and got one on all five of its false
positives, because the source's study population always excludes *something*. The lesson generalises
past this gate: **when you bound a rule, ask whether the required write-down is producible on an
arbitrary claim.** If it is, you have written a ritual, not a test. The repair that worked was to
constrain what (c) may be a different *kind* of — a question with a wrong answer.

**2026-10-08 — look for the contradiction before writing prose; this rubric had four.** Every one was a
later layer aimed at a boundary an earlier layer already decided, and in each case the judge followed
*one* of them, so the symptom looked like a skip: (i) gate 6's "dropped scope quantifier" carve-out vs
gate 1's and gate 7's routing of population/stage/setting to NOT_SUBSTANTIATE; (ii) "the worked examples
outrank this exclusion" vs the wording-delta exclusion it outranked; (iii) gate 2's `[OTHER_CIT]`
trigger vs the multi-citation section's burden-narrowing for a *visible* placeholder; (iv) four separate
copies of "a hedged source supports a citing clause" vs gate 7's `strength` axis. **Proof the judge was
obeying rather than skipping: on the same shape it reached opposite verdicts from opposite clauses** —
`514-19`/`949-76` routed a setting bound to gate 7 and got it right; `330-15`/`737-47` fired gate 6 and
got it wrong. Same rubric, same batch.

**2026-10-08 — zero `retrieval` blames on a 50-claim batch.** The context docs record window-silence-read-as-absence as ~31% of misses
historically; it produced **none** of the 11 misses here. The rubric's existing anti-argument-from-silence
layer appears to have closed it. If anything the pendulum has swung: two misses came from the
silence→ACCURATE escape firing when it should not have. Treat the documented 31% as a historical figure
about an earlier program, not a standing prior.


**2026-10-08 (iter 4) - first net *shrink* of the rubric in this run, and it is deliberately a
measurement.** 531 -> 513 lines: **thirteen deletions (~67 lines) against five additions (~49)**,
after three iterations that added +37, +55, +56. The deletions were not cosmetic - three were
identified contradictions rather than redundancy: the categorical "if you have already named a
candidate (c) **anywhere**, this gate answered yes" sat earliest in gate 6 and **pre-empted four
later paragraphs** that each describe a candidate (c) which does not fire it, the most plausible
single cause of four iterations of OVERSIMPLIFY over-firing; and the house base-rate note licensed
rejecting a fired gate on prior-probability grounds the judge cannot evaluate on one claim. **A
dedicated redundancy / contradiction / roster-anchor audit of the whole prompt by one subagent is
worth its cost** - it found ~150 deletable lines with no decidable test lost, flagged which anchors
*are* the test (do not cut those: gate 7's `strength` phrase lists and `class-vs-member` have no
other definition anywhere), and independently noticed that the 55 lines added in the single
iteration where VAL fell were the four most roster-anchored blocks in the file.

**2026-10-08 (iter 4) - a measured-and-dropped edit worth recording because the *reason* will recur:
the fixed roster can identify VAL mass it cannot be used to design against.** Calibration says
ETIQUETTE is under-fired **3x** (4.1% vs 12.2% dev) - the largest unfixed block, about 4 VAL claims.
Gate 2 is narrowed by house text to **one** syntactic signature ("it fires on one thing"), narrower
than the paper's own definition. But TRAIN holds only 3 ETIQUETTE claims and **2 of them are that
signature**, so every trigger I could construct for the third scored 1-for-2 or 1-for-6 against.
Dropped rather than fitted to one example. **When calibration names a gap and the roster holds <=3
instances of the class, the honest move is to log it and ask for a re-draw, not to invent a
trigger.** Four iterations of a Jaccard-1.000 roster is itself the binding constraint.


**2026-10-09 — ⚠ the VAL trend is the highest-mass signal this lineage has, and it outranks any
TRAIN corpus.** On the same first-50 VAL claims: v11 0.60, v12 0.70, **v13 0.76**, v14 0.694, v15
0.68, v16 **0.66 (floor 0.70)**. Three consecutive declines totalling −0.10 — beyond the 0.06
single-measurement scatter — across 49 edits that each held on TRAIN. On a fresh 25-claim roster v16
was 0.64 against a 0.72 floor, and **its non-ACCURATE verdicts were right 1 time in 5**. Response:
restored v13 wholesale, *with no other edit*, so the next VAL is a repeat measurement of v13.
**Pending until graded:** if v13 re-scores ≥ 0.70, the decline was the rubric and every future edit
should be judged against v13's re-measured VAL, not TRAIN; if ≤ 0.66, v13's 0.76 was scatter.
**Standing procedure either way: in step 2, line up every version's VAL on the same claims before
reading the corpus; when the last three steps all fall, restoring the peak is a measured edit, and
forward-only means nobody else will make it.**

## Resolved baselines (kept for provenance)

*(Numbers this run has pinned, each with the batch and key it was measured against.)*

**2026-10-08 — `program-v11`, run `hillclimb-2026-10-08b`, profile `retrieval`, `claude-haiku-5-5`.**

- TRAIN (`hillclimb-2026-10-08b-train-i1`, 48 scored of 50): `primary_metric` **0.7917**,
  `do_nothing_floor` **0.62** → **+0.17**. `macro_f1_renormalised` 0.5394 at 8 classes present.
  `micro_f1` 0.8125. 38 correct / 11 mistakes.
- VAL (`hillclimb-2026-10-08b-val`, 50): `primary_metric` **0.60**, 6 classes present.
- ⚠ **`release_val.json` carries no `do_nothing_floor`**, so the VAL floor for this run is unknown. Do
  **not** import **0.70** — that is the 2026-09-09 roster's floor, not this one. Leave the VAL gap
  unsigned until the key appears.
- The TRAIN−VAL spread is **0.19** on a program tuned over eleven versions against a fixed TRAIN roster.
  That is the shape of overfitting, and it is the reason to weight VAL over TRAIN when they disagree.
- `micro_f1` − `primary_metric` = **0.021**: almost none of the error is a confusion *inside*
  NOT_ACCURATE. On this program the points are at the bucket boundaries, so the strictness ladder is
  not where the work is.
- Where the error actually is, both derivable only by combining `per_class_f1_9way` with predicted
  counts recovered from `run_manifest.json`: **OVERSIMPLIFY precision 0.29** (7 predicted, 3 gold) and
  **NOT_SUBSTANTIATE recall 0.43** (4 predicted, 7 gold). Those two carried 8 of 11 misses.
  `per_class_f1_9way` alone does not separate precision from recall — recover the predicted counts.

**2026-10-08 — `program-v12`, run `hillclimb-2026-10-08b`, same profile/model/roster.**

- TRAIN (49 scored of 50): `primary_metric` **0.8367**, floor **0.62** → **+0.2167**.
  `macro_f1_renormalised` **0.6015** at 8 classes. `micro_f1` 0.8571. 41 correct / 8 mistakes.
- VAL: `primary_metric` **0.70**, up from 0.60. No `do_nothing_floor` in `release_val.json`. ⚠ Do
  not let the digits fool you: VAL *scoring* 0.70 is not the same object as the 2026-09-09 roster's
  0.70 *floor*.
- TRAIN−VAL spread **0.19 → 0.137**. Still the shape of overfitting to a fixed roster; keep weighting
  VAL when they disagree.
- `micro_f1` − `primary_metric` = **0.0204** (2nd of 5 identical readings — see the v15 entry).
- Error mass after v12: **NOT_SUBSTANTIATE precision 0.56** (9 predicted, 7 gold) — 4 of 8 misses.
  OVERSIMPLIFY precision is repaired (0.67). IRRELEVANT and OVERSIMPLIFY recall both 0.67.
- **The roster is fixed:** `draw_history.json` iterations 1 and 2 are the same 50 ids, pairwise
  Jaccard **1.000**. Verified, not assumed. An absent claim is a real absence.

**2026-10-08 — `program-v13`, run `hillclimb-2026-10-08b`, same profile/model/roster.**

- TRAIN (49 scored of 50): `primary_metric` **0.8571**, floor **0.62** → **+0.2371**.
  `macro_f1_renormalised` **0.6237** at 8 classes. `micro_f1` 0.8776. 42 correct / 7 mistakes.
- VAL: `primary_metric` **0.76** — the run's best, and `frontier.best_tag`. No VAL floor key.
- TRAIN−VAL spread **0.19 → 0.137 → 0.097**.
- `micro_f1` − `primary_metric` = **0.0204** (3rd of 5 identical readings — see the v15 entry).
- Error mass after v13: **OVERSIMPLIFY precision 0.40** (5 predicted, 3 gold) — 3 of 7 misses.
  NOT_SUBSTANTIATE precision repaired to 0.83; IRRELEVANT now 1.00 (precision and recall).
  CONTRADICT and INDIRECT_NOT_REVIEW both 0.000 at support 1 each.
- **The roster is fixed through three iterations** — but *verify* it in `draw_history.json` rather
  than inheriting this line.


**2026-10-08 - `program-v14`, run `hillclimb-2026-10-08b`, same profile/model/roster.**

- TRAIN (49 scored of 50): `primary_metric` **0.8980**, floor **0.62** -> **+0.2780**.
  `macro_f1_renormalised` **0.6651** at 8 classes. `micro_f1` 0.9184. 44 correct / 5 mistakes.
- VAL: `primary_metric` **0.6939** - **down** from 0.76. `n_invalid` **1** on VAL for the first time
  (iterations 1-3 had 0), so the denominator moved: **34/49 against 38/50**, i.e. four fewer correct
  labels. Still **no `do_nothing_floor` in `release_val.json`** - four iterations running; treat its
  absence as this run's norm and leave the VAL gap unsigned.
- TRAIN-VAL spread **0.19 -> 0.137 -> 0.097 -> 0.204.** Widest of the run.
- `micro_f1` - `primary_metric` = **0.0204** (4th of 5 identical readings — see the v15 entry).
- Error mass after v14 - and the point is that it is nearly gone from TRAIN: **5 misses**, of which
  `330-15` (INDIRECT_NOT_REVIEW, **0** dev occurrences) is worth 0 VAL points and `1914-14` was shown
  at iter 2 to be inseparable from `1202-17` under any naming rule. **TRAIN is saturated**; the
  remaining per-claim work there cannot produce another two points, and iter 4 measured what mining it
  produces instead (TRAIN +0.041, VAL -0.066).
- Per-class: OVERSIMPLIFY precision **0.60** (5 predicted, 3 gold), NOT_SUBSTANTIATE precision
  **1.00**, ACCURATE precision 0.91 / recall 0.97, ETIQUETTE recall **0.67**, IRRELEVANT and MISQUOTE
  1.00, **CONTRADICT and INDIRECT_NOT_REVIEW both 0.000**.
- **The roster is fixed through four iterations** - `draw_history.json`, pairwise Jaccard **1.000** on
  all six pairs. Verified, not inherited. An absent claim is a real absence.
- **Canary healthy**: top-level `canary` in `run_manifest.json`, claim `1969-64`, `status: "ok"`, not
  among the 50 scored claims. These numbers carry a round-trip guarantee and are comparable to
  iterations 1-3.

**2026-10-08 - `program-v15`, run `hillclimb-2026-10-08b`, same profile/model/roster.**

- TRAIN (49 scored of 50): `primary_metric` **0.8980**, floor **0.62** -> **+0.2780**. Flat against
  v14 to four decimal places, at **44 correct / 5 mistakes** - the same count, a different five.
  `macro_f1_renormalised` **0.7253** at 8 classes (up from 0.6651). `micro_f1` 0.9184.
  `macro_f1_9way` 0.6447. `macro_f1_3way` **0.8532**, *down* from 0.8801.
- VAL: `primary_metric` **0.68** (0.60 -> 0.70 -> 0.76 -> 0.6939 -> **0.68**). `n_invalid` back to
  **0**, so the denominator returned to 50: **34/50 against v14's 34/49 - the same 34 correct
  labels.** ⚠ Read `n_invalid` beside the VAL metric on this run; the denominator has moved twice.
- Still **no `do_nothing_floor` in `release_val.json`** - five iterations running. The VAL gap is
  unsignable here; do not import another roster's figure.
- ⚠ **`frontier.best_tag` is `program-v13` at 0.76.** The last three versions scored 0.694, 0.68,
  and are built on top of it. **0.76, not 0.68, is the number to beat**, and the loop is forward-only
  so v13 is not recoverable.
- TRAIN-VAL spread **0.19 -> 0.137 -> 0.097 -> 0.204 -> 0.218**, widest of the run for the second
  iteration running.
- `micro_f1` - `primary_metric` = **0.0204** for the **fifth** iteration running. Settled: the error
  is at the 3-way bucket boundaries, the strictness ladder is not where the work is. Stop deriving it.
- Per-class: OVERSIMPLIFY precision **0.60** (5 predicted, 3 gold) - *unmoved for two iterations*;
  CONTRADICT **0.50 / 1.00** (F1 0.000 -> 0.667); **IRRELEVANT recall 1.00 -> 0.67**;
  NOT_SUBSTANTIATE 1.00 / 0.83; ETIQUETTE 1.00 / 0.67; ACCURATE 0.94 / 0.97; MISQUOTE 1.00;
  INDIRECT_NOT_REVIEW 0.000.
- Firing rate vs the **dev** priors VAL is drawn from: OVERSIMPLIFY **3.9× over** (10.2% vs 2.6%),
  ETIQUETTE **0.33×**, IRRELEVANT 0.60× (down from 0.91×), CONTRADICT 0.57× (up from 0).
- **The roster is fixed through five iterations** - `draw_history.json`, pairwise Jaccard **1.000** on
  all ten pairs. Verified, not inherited.
- **Canary healthy**: top-level `canary` in `run_manifest.json`, claim `1969-64`, `status: "ok"`.
  These numbers carry a round-trip guarantee and are comparable to iterations 1-4.
- Gate-prefix compliance **49 of 49**. Five iterations in, no execution-skip story is available for
  this program: every ledger carries an ordered walk.

## Reverted

*(Attempts this run made and backed out. As useful as a confirmed one, and likelier to be retried
by accident — say what you tried and what the measurement did.)*

## Notes on the instrument itself

*(Things you learned about the harness rather than about the task. If you believe an inherited
harness fact is wrong, verify it and record the verification here.)*

**2026-10-08 — verified: the release files and the run manifest are all on disk, before the session
starts.** The inherited warning that "no release files are written" is not true of this run.
`/workspace/ro/feedback/iter/1/` held `release_train.json`, `release_val.json` and a `files/` directory
with the mistake corpus, `run_manifest.json` and 51 per-claim trace jsonls (10 MB). One `find` confirms
it. `run_summary.json` was **absent** at iteration 1 — expected with no prior VAL to summarise — and
**present at iteration 2**, carrying each iteration's `base_metric` and `sarol_accuracy_9class`. It is
the right place to read the VAL trend, and it exists from the second iteration onward.

**2026-10-08 — `run_manifest.json` is the only source of predicted labels for *correct* claims, and it
is what makes a precision number possible.** The mistake corpus lists errors only, so without the
manifest you can see recall and not precision. Each manifest entry carries
`validation.overall_verdict` and `validation.sub_claim_verdicts` for all 50 claims, plus the per-claim
`trace_ref`, cost and status, plus the top-level `canary`.

**2026-10-08 (iter 2) — thinking blocks are redacted in the per-claim traces** (empty `thinking` with a
signature). A blame subagent reported `execution` was *unassignable* across its whole slice for want of
a quotable abandonment point. Assistant text and tool-call inputs survive, so deliberation the judge
wrote out loud is still readable. **Budget trace-reading for what the judge said and wrote, never for
its chain of thought.**

**2026-10-08 — invalid outputs are dropped from the accuracy denominator, not charged as misses.**
Measured: 38/48 = 0.7917 with `n_total` 50 and `n_invalid` 2. The context docs say an invalid label is
"charged as a miss against whatever the gold class was"; this release excluded it instead. But
`support_9way` still counts the invalid claim's gold, so **`support_9way` and `n_scored` have different
denominators** — do not combine them into a precision figure without allowing for the gap.

## Iteration log

*(One line per iteration: what you changed, what the measurement did, what you concluded.)*

- **iter 1 (2026-10-08, `hillclimb-2026-10-08b`)** — First measurement of `program-v11`: TRAIN 0.7917
  vs floor 0.62, VAL 0.60. No predecessor notes to check. Error mass was two numbers — OVERSIMPLIFY
  precision 0.29 and NOT_SUBSTANTIATE recall 0.43, together 8 of 11 misses. Ten edits to the rubric and
  the dispatch, all aimed at four different label boundaries so they attribute separately: bounded gate
  6 so a *study-scope* bound (population / cohort / setting / site / timepoint) can no longer be its
  excluded member and routed those to gate 7; deleted *"the worked examples outrank this exclusion"*;
  added "no other passage asserts the predicate at the clause's own scope" as a gate-6 precondition;
  extended gate 7's `strength` to permissive-vs-universal recommendations without touching the four
  axis words; bounded the silence→ACCURATE escape to requiring the clause's agent and subject each
  **named** in a passage, with NOT_SUBSTANTIATE as the fallback; narrowed gate 2 to a quotable partial
  sibling; made gate 1's axis write-down literal on both sides; and deleted a fourth duplicate copy of
  the hedging ban. Prediction and the risk I accepted are in the iteration's findings. **Not yet
  measured.**
- **iter 2 (2026-10-08, `hillclimb-2026-10-08b`)** — Measured v12: **TRAIN 0.7917 → 0.8367, VAL 0.60 →
  0.70, macro-renorm 0.5394 → 0.6015.** Ten of iter 1's twelve predictions held; 5 claims fixed, 2 new,
  net −3 misses. **The gain was real and the regression was predictable**: iter 1's gate-6 bound worked
  and handed its mass to gate 7, whose `population` axis then fired 0-for-2 while its other three axes
  went 4-for-4. Six edits: the **containment test** bounding gate 7's `population`/`stage/setting` to
  passage-sets *outside* the clause's; gate 6's exclusion re-pointed at it; **deleted** gate 1's
  *"carry the mismatch forward"* clause so an admitted axis mismatch fires IRRELEVANT, with gate 7's
  contradicting back-route bullet repaired to match; gate 8's silence branch loosened from "fail
  either" to **"fail both"** (one of agent/subject missing is a retrieval hole, not a support gap); and
  burden-narrowing hard-bounded to a **quotable** trigger in both rubric and dispatch, because an
  inferred sibling deletes gate 6's excluded member. Exposure measured at zero before each narrowing.
  One designed edit **dropped** on evidence: no naming rule can separate `1202-17` (gold ACCURATE) from
  `1914-14` (gold NOT_SUBSTANTIATE), which are the same shape under that test. Rubric 421 → 476 lines
  (+55) — a cost, flagged, with the deletion that would pay for it named for next time. **Not yet
  measured.**
- **iter 3 (2026-10-08, `hillclimb-2026-10-08b`)** — Measured v13: **TRAIN 0.8367 → 0.8571, VAL 0.70 →
  0.76, macro-renorm 0.6015 → 0.6237.** Ten of iter 2's twelve predictions held; the two that failed
  (Q5, Q8) were the *same* edit, E15's burden-narrowing bound, and had one mechanism: the trigger it
  required (`multi_cit_context=grouped`) is producible on **two claims in five**, so the rule was
  bound in form only — the third occurrence of this rubric's signature defect, now promoted to
  Confirmed. 3 fixed, 2 new, net −1 miss. Five edits, two of them deletions: **deleted** the false
  *"There is no marker in the claim text to look for"* and the unbounded *"Parts of the citing claim
  that a sibling citation may cover do not count against the current source"* — the competing
  permission the judge was actually taking; added the **named-referent bound** (you may not narrow
  away a referent the clause prints, with a per-item-marker exception), a **(c)-must-lie-inside-(b)**
  test for gate 6, a **whole-sentence** rule for gate 6's other-passage scan, and **ported gate 6's
  other-passage scan onto gate 7's containment test** (which had none, and it is the gate that needs
  it more, since containment is read off one chosen passage). Two designed edits **dropped on
  evidence**: the `1914-14` axis-list loosening (load-bearing on 3 correct answers, wrong on 1 —
  3-for-1 against) and the `140-50` gate-3 fix (exposure unmeasurable, `remediation` is not a ledger
  field). **Withdrew** two iterations' claim that `330-15`'s gold is indefensible — gold keys on a
  relayed appositive the judge never tested — and declined to fix it anyway, because
  INDIRECT_NOT_REVIEW has 0 occurrences in dev and VAL is drawn from dev. Rubric 476 → 532 (+56), a
  cost flagged with the deletion that would pay for it named. **Not yet measured.**
- **iter 4 (2026-10-08, `hillclimb-2026-10-08b`)** - Measured v14: **TRAIN 0.8571 -> 0.8980,
  macro-renorm 0.6237 -> 0.6651 - and VAL 0.76 -> 0.6939.** Eleven of iteration 3's twelve
  predictions held; the twelfth was the objective. That asymmetry *is* the iteration: TRAIN is
  saturated at 5 misses, two of them established as worth 0 VAL points, so per-claim mining of the
  corpus now buys TRAIN and costs VAL. Pivoted to a **calibration** diagnosis from the published
  dev-pool class priors, which no earlier iteration had read: CONTRADICT fires 0% against a **7.1%**
  dev rate (the rubric's own house base-rate note matched the *TRAIN* pool and was 2.5x wrong on
  exactly that class), ETIQUETTE 4.1% vs 12.2%, OVERSIMPLIFY 10.2% vs 2.6% - about 9 claims per 50
  misallocated. **Eighteen edits, thirteen of them deletions, rubric 531 -> 513 (-18, the run's first
  net shrink).** Rewrote **gate 3**: removed the "opposes only if the citing clause cannot also be
  true" excuse that voided the gate's own two named shapes and is stricter than the paper's
  definition, replaced it with a *different-named-agent / different-named-stage* direction test,
  ruled that a hedge does not excuse opposition and that the element-by-element ban is about
  **silence not opposition**, and gave it the rubric's first required **refusal** write-down (it was
  disposed of in unquoted prose on 41 of 49 claims and had fired zero times). Replaced **gate 6's**
  useless "(c) is inside (b)" judgement - satisfied on all 4 claims where it appeared, discriminating
  nothing - with a **quotable breadth word in (b)**, 4-for-4 on measured TRAIN exposure. Made gate
  7's containment scan string literal (the judge was writing it *inverted* on 2 of 7, one a miss).
  **Deleted** the subset section's 25-line restatement of gates 1/7/8 (iter 3's own named,
  conditional deletion - its condition was met), the house base-rate note, the categorical "named a
  candidate (c) anywhere -> gate answered yes" that pre-empted four later gate-6 bounds, and ten
  smaller duplicates. **Two designed edits dropped on measured evidence:** the gate-2 widening for
  ETIQUETTE (every constructible trigger 1-for-2 or 1-for-6 against) and the gate-5 fix for `330-15`
  (0 dev occurrences). **Not yet measured.**
- **iter 5 (2026-10-08, `hillclimb-2026-10-08b`)** - Measured v15: **TRAIN 0.8980 -> 0.8980 (44/49
  both times), macro-renorm 0.6651 -> 0.7253, VAL 0.6939 -> 0.68 - and the same 34 correct VAL labels
  as v14.** Eight of iteration 4's twelve predictions held, three did not, one held on its threshold
  while the thing it asserted was false, two were could-not-tell by prior construction. **The
  iteration's finding is that one: iteration 4's thirteen deletions were not free. Three of them cut
  *inside sentences*** - gate 1 lost "so walking on always lands on ACCURATE" plus the
  predicate-is-the-whole-relationship rule, gate 6 lost its routing destination into gate 7, gate 7
  lost "go to test 8" - **and both new misses sat at two of those loci**, each having been correct for
  three iterations (`737-47` IRRELEVANT->ACCURATE, `1572-12` ACCURATE->OVERSIMPLIFY). Two unrelated
  fixes (`140-50`, `1094-46`) cancelled them exactly, which is why the aggregate threshold held.
  **Thirteen edits: four restorations of the truncated text; the (a)-minus-(b) span classifier for
  gate 6** (classify the differing span by part of speech - quantity expression / proper-name
  identifier / printed item fire; an **attributive adjective** does not - 15-for-15 on measured
  exposure, and corroborated by the definitions file's record that *qualified-in-source but unqualified
  in claim* is a divergence **we** once added to OVERSIMPLIFY and removed); a requirement that gate
  6's (a) be quoted from a span with a finite verb rather than a table caption; **literal bans on
  self-certifying slot fills** at gates 1 and 7 ("the same axis", "a weaker version"); a gate-3
  **no-presupposing** bound (its one false fire opposed the background of an "unlike…" adjunct); a
  repointed dead cross-reference at gate 7; and three trims, including the two archaeology sentences
  that told the judge what *used to* stand in the rubric. **Two edits dropped on measured evidence:**
  the gate-2 ETIQUETTE widening (thirteen triggers measured, best 1-of-2) and the gate-5 fix for
  `330-15` (0 dev occurrences). Rubric 513 -> 570 (+57), the run's largest addition, flagged as a cost
  with the next iteration's deletion candidates named in the findings. **Not yet measured.**
- **iter 1 (2026-10-09, `hillclimb-sched-2026-10-09`)** — Measured v16: VAL **0.66 vs floor 0.70
  (−0.04)**, TRAIN 0.64 vs floor 0.72 on a new 25-claim roster (16/9). All of iteration 5's
  claim-level predictions could-not-tell (roster replaced); its VAL prediction did not hold. Read the
  9 misses directly (no fan-out): 3 ETIQUETTE misses on three different surface shapes, 4 false
  non-ACCURATE fires at four different gates, 2 rare-class misses. **One edit: rubric + dispatch
  restored to `program-v13`** (570 → 476 lines), as a deliberate pure re-measurement of the lineage's
  best VAL version. **Measured: VAL 0.76 on n50 (same as v13) — confirmed; 0.71 on n100.**
- **iter 2 (2026-10-09, `hillclimb-sched-2026-10-09`)** — Measured v17 (= v13): VAL n100 **0.71 vs
  floor 0.69 (+0.02)**, TRAIN 0.60 vs floor 0.66 on 50 claims (30/20). Iteration 1's P1–P7 all held.
  Two subagents × 10 claims: 18 rubric, 1 gold, 0 execution. Dominant mode: within-clause burden
  narrowing turns ETIQUETTE into ACCURATE (5/20). **One-boundary edit** (gate 2 rewritten as a two-question
  bound test; the "ACCURATE for the attributable portion" sentence deleted from the rubric's
  multi-citation section and from dispatch step 4). Rubric 476 → 473. Gate-5 loosening measured at
  about 50% and dropped. **Not yet measured.**
- **iter 3 (2026-10-09, `hillclimb-sched-2026-10-09`)** — Measured v18: VAL n150 **0.653 vs floor
  0.647 (+0.007)**, v17 re-graded 0.640 on the same claims. TRAIN 0.626 vs floor 0.68 (62/99, 1
  crashed call). Iteration 2's Q1–Q3, Q5–Q7 held, Q4 did not, Q8 could not tell, and Q9 held except for NS. Three
  subagents took 24 claims; 13 re-read from ledgers. 22 rubric, 0 execution. Dominant mode: non-ETIQ
  gates 0/14. **Four edits on four boundaries, rubric only, 473 → 508:** gate 4 bounded to the same
  quantity with three quotable "no"s (deleting "rounding … all MISQUOTE"); gate 6 "a plural is
  satisfied by two" (deleting three contradicting examples); a preamble rule that the citing authors'
  own study is not the source's content; gate 3 fires on a misdescribed *design* attribute of the
  cited study. Gate-2 silence, single-marker ETIQUETTE, the NS "not clear whether" route and gate 5
  were all recorded and not edited. **Not yet measured.**
- **iter 4 (2026-10-09, `hillclimb-sched-2026-10-09`)** — Measured v19: VAL n250 **0.644 vs floor 0.612 (+0.032)**;
  n150 v19 0.667 vs v18 0.653 (scatter). TRAIN 0.564 vs floor 0.60 (84/149), macro-renorm 0.259. Iteration 3's R2–R4, R7, R9
  held and R1 held in part. R5, R6, R8, R11 did not hold, and R10 could not tell. Dominant mode: **gate 6 fired 14 times, 0 right**. Three
  subagents took 22 claims (18 rubric, 4 execution, 1 gold). **Two edits on two classes, 508 → 437 lines:** gate 6 cut
  to a two-quote restriction-word trigger, with ~75 lines of excluded-member machinery deleted, and gate 7's class-vs-member
  axis deleted, with a "Contains → no fire" branch and a relayed-passage bar on "outside". NS name-either route and
  lone-marker ETIQUETTE recorded, not edited. **Not yet measured.**
- **iter 5 (2026-10-09, `hillclimb-sched-2026-10-09`)** — Measured v20: VAL n311 **0.653 vs floor 0.595 (+0.058)**; n250 v20
  0.651 vs v19 0.644 (scatter). TRAIN 0.578 vs floor 0.575 (115/199), macro-renorm 0.239. 25 VAL crashes (infra). Iteration 4's S1–S5
  and S7 held, S6 and S9 did not, and S8 could not tell. 83% of verdicts are ACCURATE, and 63 of 84 misses are gold non-ACC → ACC. Four subagents
  × ~21 claims covered all 84 misses (68 rubric, 5 execution with quotes). **Two edits, 437 → 447 lines:** gate 2's sibling
  precondition deleted, so lone-marker partial carry of a named list → ETIQUETTE, with four competing passages repaired. And a
  gate-4 rounding "no". NS residual (16), gate-5 bound (9) and IRR axis widening (5) recorded, not edited. **Not yet measured.**
