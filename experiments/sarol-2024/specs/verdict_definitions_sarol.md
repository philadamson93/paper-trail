# Sarol 2024 label definitions — what each verdict means

**Frozen contract. Not editable.**

What the nine labels mean, as the benchmark's annotators understood them. The emittable set and the
9→3 collapse are in `verdict_enum_sarol.md`; how to *apply* these definitions to a claim in front of
you — boundaries, worked examples, tie-breaks, decomposition, multi-citation attribution — is in
`verdict_schema_sarol.md`.

**Source:** Sarol, Schneider, Kilicoglu 2024, *"Assessing Citation Integrity in Biomedical
Publications"* (Bioinformatics btae420), Table 1 (annotation scheme).

## The nine labels

- **ACCURATE** — the cited paper directly supports the claim as stated.

- **OVERSIMPLIFY** — the source's findings are oversimplified or overgeneralized in the citing claim.
  The source is narrower than the claim asserts, or the source qualifies what the claim states
  unqualified.

- **NOT_SUBSTANTIATE** — the cited paper fails to substantiate all parts of the claim: there is
  partial support, but a key element is missing.

- **CONTRADICT** — the citation context contradicts a statement made in the cited paper.

- **MISQUOTE** — numbers or percentages are misquoted. Narrow and numerical; non-numerical drift in
  strength is `OVERSIMPLIFY`.

- **INDIRECT** — the cited paper itself cites other articles for the claim. The claim's attribution
  runs through a review or secondary source rather than the primary one. Applies when the cited paper
  is a review article.

- **INDIRECT_NOT_REVIEW** — the same indirect-attribution pattern, where the cited paper is not a
  review article.

- **ETIQUETTE** — the citation style is ambiguous: it is unclear from the citing sentence what
  specifically is being attributed to this paper. Predominantly a multi-citation issue.

- **IRRELEVANT** — there is no information in the cited paper relevant to the claim.

## Workflow states are not verdicts

`PENDING` / `NEEDS_PDF` / `STALE` / `SCHEMA_VIOLATION` are pipeline machinery, orthogonal to these
definitions, and are not emittable as a verdict. The same is true of `AMBIGUOUS`, which the shipped
tool uses as a workflow flag: it is not part of this vocabulary, and the exit validator rejects it in
a verdict field exactly like any other out-of-enum label.
