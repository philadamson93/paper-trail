# Blame brief — read one claim, say why it was judged wrong

**This document is your whole brief.** You have been handed a list of claim ids and the path to a
mistake corpus. Work those claims and return one record each. You do not need any context beyond
this file — not the run's history, not what the optimizer is planning, not how your slice was
chosen.

**Every path here is relative to your working directory, which is the repository root.**

## The task

A citation-integrity pipeline was given a citing sentence and one paper it cites, and emitted one
verdict from a fixed nine-label vocabulary. On your claims it emitted the wrong one. Your job is to
say **why** — the step the judge took that produced the wrong answer.

You are not fixing anything. You are producing evidence about a mechanism.

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
| `adjudicator_reasoning.nuance` | the judge's own prose about what it was weighing |
| `claim_type` | the judge's read of the claim (`PARAPHRASED`, `DIRECT`, …) |

The nine labels: `ACCURATE` · `OVERSIMPLIFY` · `NOT_SUBSTANTIATE` · `CONTRADICT` · `MISQUOTE` ·
`INDIRECT` · `INDIRECT_NOT_REVIEW` · `ETIQUETTE` · `IRRELEVANT`. Their definitions are in
`experiments/sarol-2024/specs/verdict_definitions_sarol.md` — read it if a blame call turns on what
a label means.

## Per claim

1. **Read the claim.** `claim_text`, `gold_label`, `pred_label`, and the sub-claim the judge
   actually evaluated.
2. **Read the evidence the verdict rested on** — `sub_claims[].evidence[]`, not just the union in
   `evidence_snippets`. *Which passage drove the sub-verdict that went wrong* is the question, and
   the union cannot answer it.
3. **Read `adjudicator_reasoning.nuance`.** The judge frequently names the thing it got wrong.
4. **Decide the blame.** One of:

   - **rubric** — the guidance the judge followed pointed it at the wrong label, or failed to
     distinguish the two labels in play.
   - **retrieval** — the evidence needed to reach the gold label was not in the window the judge
     saw. On this pipeline the judge is handed a keyword-retrieved subset of the cited paper and is
     **not told that it is a subset**, so it can report a fact as absent from the paper when the
     fact simply was not retrieved. Check whether the `locator` values cluster in one region (a
     keyhole) or scatter across the paper (broad coverage).
   - **decomposition** — the citing sentence carries more than one proposition and the judge judged
     them as one, so a single verdict had to cover both.
   - **attribution** — the sentence cites a cluster of sources and the judge attributed the wrong
     portion of it to this one.
   - **gold** — you believe the benchmark's label is wrong or genuinely ambiguous. Legitimate, and
     rare. Say why in one sentence; it is not a catch-all for a miss you cannot explain.
   - **unclear** — the record does not tell you. Better than a guess.

5. **Open a reasoning trace only if you must.** The run manifest records a `trace_ref` per claim,
   pointing at the judge's own session transcript. It is the full reasoning and it is large. Open
   one when the fields above genuinely cannot tell you why the judge concluded what it did — one or
   two across your whole slice, not one per claim. Opening them by default will exhaust your budget
   before it teaches you anything.

## What to return

One record per claim, and nothing else. Not the evidence text, not the trace, not the corpus.

```
claim_id:      C042
gold / pred:   CONTRADICT -> ACCURATE   (3-way: NOT_ACCURATE -> ACCURATE, crossed)
blame:         rubric
mechanism:     one sentence on WHY the judge landed where it did -- the step it took, not the
               outcome. "Treated a source passage stating the opposite as merely unsupportive,
               because the guidance requires a verbatim opposing excerpt and this one paraphrased."
evidence_cue:  the single locator or short snippet that shows it (<= 15 words)
confidence:    high | medium | low
```

`mechanism` is the load-bearing field. "The judge was wrong about CONTRADICT" restates the label
columns and is worth nothing. Name the step that produced the wrong answer.

## Boundaries

- **Do not edit any file.** You are reading and blaming; someone else makes the edits.
- **Do not look for VAL or TEST claim records or gold labels.** They are outside the repository tree
  entirely. Attempts are logged, and a threshold of denied calls pauses the run.
- **Do not print the corpus back.** Your return value is the records above.
