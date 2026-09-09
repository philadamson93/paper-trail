# Blame brief — read one claim, say why it was judged wrong

**This is your brief.** You have been handed three things: a list of claim ids, the path to a
mistake-corpus JSON file, and the name of this run's **profile**. Work those claims and return one
record each.

**You need nothing about the run itself** — not its history, not what the optimizer is planning, not
how your slice was chosen, not the previous iterations' findings. Those would cost you attention and
buy you nothing, and you have not been given them on purpose.

**You will need to open two program files**, named below: the rubric (because deciding whether the
guidance was at fault means reading the guidance) and the label definitions. Read them once, before
you start; do not go looking for anything else.

**Every path here is relative to your working directory, which is the repository root.**

## The task

A citation-integrity pipeline was given a citing sentence and one paper it cites, and emitted one
verdict from a fixed nine-label vocabulary. On your claims it emitted the wrong one. Your job is to
say **why** — the step the judge took that produced the wrong answer.

You are not fixing anything. You are producing evidence about a mechanism.

**The profile you were given decides how the evidence reached the judge**, and it changes which
blames are even possible. Do not assume; use the one you were handed.

| Profile | How the judge got its evidence | What that means for you |
|---|---|---|
| `retrieval` | BM25 keyword search over the cited paper picked the top *k* passages, mechanically, before the judge ran | `retrieval` blame is about a **keyword miss**. There is no extractor to blame |
| `agentic` / `paperclip` | an extractor agent searched and selected the passages | `retrieval` blame is about an **agent's search**, which is a different defect with a different fix |

Under `retrieval` the envelope also carries exactly one sub-claim covering the whole citing
sentence, and the indirect-attribution check is null. Those are properties of the profile, not
defects of the judge — do not blame the judge for them.

## Your input

The corpus file you were given is JSON. Each entry under `claims` is one wrongly-judged claim. The
fields that matter to you:

| Field | What it gives you |
|---|---|
| `claim_id` | the id you were handed |
| `claim_text` | the citing sentence being judged |
| `gold_label` / `pred_label` | the 9-way verdict, correct and predicted |
| `gold_3way` / `pred_3way` | the collapsed verdict — tells you whether the miss crossed a bucket |
| `sub_claims[]` | the proposition the judge actually evaluated, its verdict, and **the evidence mapped to it** |
| `sub_claims[].evidence[].locator` | `pdfs/<citekey>/content.txt#L22` — where in the cited paper that passage came from |
| `evidence_snippets` | every passage the judge was given, as a flat union across sub-claims |
| `adjudicator_reasoning.nuance` | ⚠ **a JSON array of strings**, one per sub-claim that carried nuance — not a single prose string. Often empty |
| `adjudicator_reasoning.remediation.suggested_edit` | the judge's own proposal for fixing the citing sentence. Undocumented until now and often the most revealing field in the record: it shows what the judge *thought the problem was*, which is frequently the mechanism you are looking for |
| `adjudicator_reasoning.overall_flag` | the judge's paper-level flag, when it set one |
| `claim_type` | the judge's read of the claim (`PARAPHRASED`, `DIRECT`, …) |
| `rubric_variant` | which version of the rubric produced this verdict |
| `trace_ref` | path to the judge's full session transcript for this claim, or `null`. See step 5 |

**Every one of these can be absent, empty, or null.** The record is assembled from whatever the
judge wrote, and a judge that wrote nothing leaves an empty field rather than an error. If a field
you wanted is missing, say so in the record and blame `unclear` — do not go looking for it
elsewhere, and do not treat its absence as evidence of anything.

### The two files you should open

The nine labels: `ACCURATE` · `OVERSIMPLIFY` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `MISQUOTE` ·
`INDIRECT` · `INDIRECT_NOT_REVIEW` · `ETIQUETTE` · `IRRELEVANT`.

- **`experiments/sarol-2024/specs/verdict_schema_sarol.md` — the rubric. Read this one first, and
  read it every time.** It is the operative guidance: it is loaded into the judge's context on every
  claim, and it is what a `rubric` blame is a blame *of*. You cannot say the guidance pointed the
  judge wrong without having read the guidance, and a mechanism sentence written without it tends to
  come out as a restatement of the outcome.
- `experiments/sarol-2024/specs/verdict_definitions_sarol.md` — what each label means, from the
  benchmark's annotation scheme. This is what the **gold annotators** were working from, so it is
  the right reference for "is the gold label defensible", i.e. for a `gold` blame. Note that the
  judge does **not** read this file, so it is never itself the cause of a judge's mistake.

## Per claim

1. **Read the claim.** `claim_text`, `gold_label`, `pred_label`, and the sub-claim the judge
   actually evaluated.
2. **Read the evidence the verdict rested on** — `sub_claims[].evidence[]`, not just the union in
   `evidence_snippets`. *Which passage drove the sub-verdict that went wrong* is the question, and
   the union cannot answer it.
3. **Read `adjudicator_reasoning.nuance`.** The judge frequently names the thing it got wrong.
4. **Decide the blame.** One of:

   - **rubric** — the guidance is **wrong or silent**: it pointed the judge at the wrong label, or
     it does not distinguish the two labels in play at all. The test: reading the rubric, could a
     careful reader have reached the gold label? If not, it is this.
   - **execution** — the guidance is **right and the judge did not follow it**. The rubric covers
     this case, correctly, and the verdict contradicts it anyway. The test is the same one, answered
     the other way: a careful reader *could* have reached the gold label from the rubric as written.
     Kept separate from `rubric` because the two imply opposite fixes — `rubric` says write a rule,
     `execution` says the rule exists and needs to be made harder to skip (moved earlier, stated as
     a check, given a worked example). Collapsing them is how an iteration adds a rule that was
     already there.

     ⚠ **This is the one blame you may not assign from the fields alone. Open the trace first**
     (step 5 below) **and quote the point where the procedure was abandoned.** If you cannot find
     that point in the trace, the rule was *not* skipped — and the blame is `rubric`, or the rule
     was followed and is wrong. This is a hard requirement because the alternative has already been
     measured: five iterations blamed execution without opening a single trace, and when the traces
     were finally read they showed **92% ordered-gate compliance**. Four iterations of "state the
     rule more forcefully" went into rules that were already being obeyed. Restating an obeyed rule
     cannot help. An `execution` record without a trace quote in its `evidence_cue` will be read as
     `unclear`.
   - **retrieval** — the evidence needed to reach the gold label was not in the window the judge
     saw. On this pipeline the judge is handed a keyword-retrieved subset of the cited paper and is
     **not told that it is a subset**, so it can report a fact as absent from the paper when the
     fact simply was not retrieved. Check whether the `locator` values cluster in one region (a
     keyhole) or scatter across the paper (broad coverage).
   - **decomposition** — the citing sentence carries more than one proposition and the judge judged
     them as one, so a single verdict had to cover both.
   - **attribution** — the sentence cites a cluster of sources and the judge attributed the wrong
     portion of it to this one.
   - **gold** — you believe the benchmark's label is wrong or genuinely ambiguous. Legitimate. Say
     why in one sentence, against the definitions file. It is not a catch-all for a miss you cannot
     explain — that is `unclear` — but do not talk yourself out of it either: this category used to
     be described as "rare", and that word alone was enough to break a tie the evidence did not.
   - **unclear** — the record does not tell you. Better than a guess.

5. **Open a reasoning trace when the blame turns on what the judge did.** Each corpus row carries
   `trace_ref`: a path to the judge's own session transcript for that claim, openable directly. It
   is the full reasoning and it is large, so this is not a read-everything instruction — it is a
   read-the-deciding-ones instruction:

   - **Mandatory** before you record an `execution` blame. Quote the point where the procedure was
     abandoned, in `evidence_cue`. No quote, no `execution`.
   - **Worth it** whenever the fields above cannot tell you why the judge concluded what it did, and
     whenever `rubric` and `execution` both look plausible — that is precisely the pair the trace
     separates and the fields cannot.
   - **Not needed** when the record is already unambiguous (a clean `retrieval` keyhole, an obvious
     `decomposition`).

   Budget it: a few across your slice, concentrated on the blames that turn on judge behaviour, not
   one per claim. When `trace_ref` is `null` the transcript was not captured — say so and fall back
   to `rubric` or `unclear`; a missing trace is never itself evidence of a skip.

## What to return

One record per claim, and nothing else. Not the evidence text, not the trace, not the corpus.

```
claim_id:      <the id from the corpus>
gold / pred:   <GOLD> -> <PRED>   (3-way: <gold_3way> -> <pred_3way>, crossed | same bucket)
blame:         rubric | execution | retrieval | decomposition | attribution | gold | unclear
mechanism:     one sentence on WHY the judge landed where it did -- the step it took, not the
               outcome
evidence_cue:  the single locator or short snippet that shows it (<= 15 words)
confidence:    high | medium | low
```

A filled-in one. The failure it describes is real — it is the retrieval-silence case observed in
the n=50 run of 2026-09-02, where the judge was handed 20 chunks of a paper about COVID
non-pharmaceutical interventions, found two of the five it named, and wrote that lockdowns were
something "this paper never discusses". The **id and the locator values below are placeholders**:
that run's per-claim corpus is not on disk, so they are shown in the right shape rather than quoted.

```
claim_id:      <id>
gold / pred:   ACCURATE -> NOT_SUBSTANTIATE   (3-way: ACCURATE -> NOT_ACCURATE, crossed)
blame:         retrieval
mechanism:     Judged the claim unsupported because the passage supporting it was never in the
               judge's window -- the locators cluster in one region of the paper, so BM25
               returned a keyhole and the judge read the silence as absence.
evidence_cue:  "this paper never discusses" -- of a paper about exactly that
confidence:    medium
```

`mechanism` is the load-bearing field. **Name the step that produced the wrong answer, not the
outcome.** "The judge was wrong about CONTRADICT" restates the label columns and is worth nothing.
"Treated a source passage stating the opposite as merely unsupportive, because the guidance requires
a verbatim opposing excerpt and this one paraphrased" names a step, and a fix follows from it.

## Boundaries

- **Do not edit any file.** You are reading and blaming; someone else makes the edits.
- **Do not look for VAL or TEST claim records or gold labels.** They are outside the repository
  tree entirely, so there is nothing in it to find — the isolation is structural, not enforced by
  anything watching you. Every gold label you are allowed to see is already on your corpus rows.
- **Do not print the corpus back.** Your return value is the records above.
