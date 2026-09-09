# Sarol 2024 label definitions — the paper's verbatim annotation scheme

> **What this file is, and is not.** It is an **optimizer-facing reference**, not part of the
> program. It is in no `program-v0` manifest entry and **the adjudicator never loads it** — the judge
> reads the enum and the rubric, and nothing else (`adjudicator-dispatch-sarol.md`). Consult it to
> check what the scheme actually says; do not reason about it as guidance the judge followed.
>
> **Frozen contract. Not editable.** The rubric (`verdict_schema_sarol.md`) is the single *operative*
> source of these definitions — it carries the same verbatim text and is what the judge reads. This
> file exists to hold the text together with its provenance, so the scheme can never again be
> silently re-transcribed. If the two ever differ, the rubric is authoritative for the run and the
> divergence is a defect to report.

## Provenance

**Source:** Sarol MJ, Schneider J, Kilicoglu H. "Assessing citation integrity in biomedical
publications: corpus annotation and NLP models." *Bioinformatics* 40(7):btae420, 2024.
Definitions are in **§2.2 / Table 1**. Open access: `https://pmc.ncbi.nlm.nih.gov/articles/PMC11231046/`.
Reconciled verbatim against the paper on **2026-09-09**.

⚠ **This reconciliation was the fix for a real defect.** Before 2026-09-09 this repository's
transcription diverged from the paper in three places, all by *our* additions, and all in the judge's
read path — see "The three corrected divergences" below. Those divergences were present from
`program-v0` onward, so five optimizer iterations hill-climbed on top of them. Do not re-introduce
them, and do not "improve" a definition by appending a test the paper does not make: any such clause
is house text and must be marked as house text where it lives.

**The published benchmark ships annotation data only, not the scheme** (`ScienceNLP-Lab/Citation-Integrity`,
MIT). The paper is the only source for these definitions.

## The nine labels

Eight are the paper's, quoted verbatim. The ninth is ours.

- **ACCURATE** — "The citation context is consistent with an evidence segment in the reference article."

- **OVERSIMPLIFY** — "The findings of the reference article are oversimplified or overgeneralized."

- **NOT_SUBSTANTIATE** — "The citation is relevant to the content of the reference article but the
  cited reference fails to substantiate all statements made in the citing paper."

- **CONTRADICT** — "The citation context contradicts a statement made in the reference article."

- **MISQUOTE** — "The numbers or percentages are misquoted."

- **INDIRECT** — "The evidence segment includes a citation to other articles, indicating that the
  reference article is not the original source of the cited information."

- **INDIRECT_NOT_REVIEW** — the same indirect-attribution pattern as INDIRECT, where the reference
  article is not a review article. *(house definition — not in Table 1.)* The class is nonetheless
  real in the released gold data: 25 occurrences in `claims-train.jsonl`, 9 in `claims-test.jsonl`,
  0 in dev. The data uses a finer vocabulary than Table 1's eight-row presentation, so our enum is
  right to carry it.

- **ETIQUETTE** — "The citation style is ambiguous and it is unclear what is being cited from the
  reference article."

- **IRRELEVANT** — "There is no information in the reference article relevant to the citation."

## The three corrected divergences

Recorded so the correction cannot be quietly undone. In each case the paper's text is now what ships.

| class | what the paper says | what we had said instead |
|---|---|---|
| **NOT_SUBSTANTIATE** | leads with "**is relevant to the content of the reference article**" | dropped the relevance precondition; substituted "partial support but key element missing" |
| **OVERSIMPLIFY** | stops at "oversimplified or overgeneralized" | appended "narrower-in-source than claimed, or qualified-in-source but unqualified in claim" |
| **ACCURATE** | "consistent with an **evidence segment**" | "**directly supports** the claim as stated" — stricter than the source |

Relevance is the paper's actual **NOT_SUBSTANTIATE vs IRRELEVANT boundary**; deleting it removed the
boundary and replaced it with a quotability test the scheme does not contain.

## Two things the definitions are not

**They are not an authority over gold.** Gold is the objective. Every definition here is a
*hypothesis* about what gold means — now a well-sourced one, but still a hypothesis. Where a
definition and gold disagree, the definition is what is under suspicion.

**They are not the whole task.** How to *apply* a definition to the claim in front of you —
boundaries, tie-breaks, decomposition, multi-citation attribution, rollup — is house text and lives
in `verdict_schema_sarol.md`. The emittable set and the 9→3 collapse are in `verdict_enum_sarol.md`.

## Workflow states are not verdicts

`PENDING` / `NEEDS_PDF` / `STALE` / `SCHEMA_VIOLATION` are pipeline machinery, orthogonal to these
definitions, and are not emittable as a verdict. The same is true of `AMBIGUOUS`, which the shipped
tool uses as a workflow flag: it is not part of this vocabulary, and the exit validator rejects it in
a verdict field exactly like any other out-of-enum label.
