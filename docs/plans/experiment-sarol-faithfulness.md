# Faithfulness audit: what the Sarol 2024 experiment actually tests

This document maps the Sarol benchmark experiment (Variants A and C) to paper-trail's real pipeline, phase by phase, calling out exactly what is and isn't exercised. Its purpose is to make paper-write-up claims precise and to preempt reviewer questions about what our reported Sarol numbers mean.

**Write before running the experiment. Reread before writing the paper.**

Companion: `docs/plans/experiment-sarol-benchmark.md` (strategy), `docs/plans/experiment-sarol-runbook.md` (execution).

## TL;DR

- **Variant A tests paper-trail's verdict core** (extractor + adjudicator + verifier) in isolation from upstream stages. It does *not* test paper-trail end-to-end.
- **Variant C tests more of the pipeline** (bib resolution, PDF fetch, GROBID ingest) by feeding full citing PDFs, but introduces alignment noise between paper-trail-extracted claims and Sarol-annotated claims.
- **Upstream stages not covered by Sarol** (claim extraction from manuscript, structural ingest, figure inspection, co-cite cross-check, native rubric) must be validated by the synthetic, opt-in, and errata experiments — not by Sarol.
- **Sarol 2024 is the best external benchmark available for the verdict-core task.** Their data format fundamentally precludes end-to-end testing because they ship pre-extracted claims paired with pre-chunked cited-paper body text.

## Phase-by-phase map

Real paper-trail pipeline (from `.claude/commands/ground-claim.md`) vs. what each Sarol variant exercises:

| # | paper-trail phase | Variant A | Variant C |
| --- | --- | --- | --- |
| 1 | Read `claims_ledger.md` frontmatter | Stub (pass-through) | Real |
| 2 | Enumerate `\cite{}` in manuscript | Skipped (claim pre-provided) | Real |
| 3 | Claim-type classifier pre-step (`DIRECT` / `PARAPHRASED` / `SUPPORTING` / `BACKGROUND` / `CONTRASTING` / `FRAMING` + confidence) | Hardcoded `PARAPHRASED / medium` | Real |
| 4 | Compute `co_cite_context.sibling_citekeys` for multi-cite sentences | Empty list for smoketest single-cit | Real |
| 5 | Bibliographic resolution (citekey → title / DOI via `refs.bib`) | Stub `refs.bib` with one synthetic entry | Real (resolves against citing paper's actual bib) |
| 6 | `/fetch-paper` PDF retrieval (arXiv / OA / paywall handling) | Skipped (source text pre-staged) | Real (fetches PMC full text for cited refs) |
| 7 | `scripts/ingest_pdf.py` GROBID → `sections/*.txt`, `figures/index.json`, `content.txt` | Skipped (`ingest_mode: pdftotext_fallback` marker, `content.txt` hand-staged from Sarol chunks) | Real |
| 8 | Extractor subagent: `rg` over sections, figure vision, sub-claim decomposition, attestation | Real but degraded (flat `content.txt` only; no `sections/`, no figures) | Real (full handle with figures if PMC paper has them) |
| 9 | Adjudicator subagent: verdict assignment from rubric | Real, but **uses Sarol 9-class variant rubric, not paper-trail native** | Same (uses Sarol variant) |
| 10 | Verifier subagent: spot-check one evidence entry | Real | Real |
| 11 | Rollup rule (CONTRADICTED > UNSUPPORTED > MISATTRIBUTED > INDIRECT_SOURCE > …) | Replaced by Sarol worst-wins order (CONTRADICT > NOT_SUBSTANTIATE > MISQUOTE > OVERSIMPLIFY > INDIRECT > …) | Same |
| 12 | Flag and remediation category | Real (mapped from Sarol verdict) | Same |
| 13 | Write `ledger/claims/<claim_id>.json` | Real | Real |
| 14 | Render `ledger.md` + `demo.html` | Skipped | Skipped |
| 15 | Paywalled-reference handling (mark `PENDING + NEEDS_PDF`) | Skipped | Real |

## What is idealized in paper-trail's favor (Variant A)

These are ways the benchmark is easier than the real tool's normal operating environment:

- **Pre-digested `content.txt`** — no OCR noise, no GROBID misparses, no malformed references.
- **Exactly one cited paper, pre-selected** — no retrieval/selection noise from `/fetch-paper` picking the wrong PDF.
- **No ingest failures** to handle; no `NEEDS_PDF` flags; no fallback cascades.
- **Claim text verbatim from Sarol's annotators** — no extraction error introduced upstream.
- **Sarol-rubric class boundaries are human-annotated** — gold labels were Cohen's-κ-validated, whereas in-the-wild citations may have more label ambiguity that paper-trail's AMBIGUOUS bucket is designed for (but Sarol's rubric drops AMBIGUOUS).

## What is impaired against paper-trail (Variant A)

These are ways the benchmark is harder than the real tool's normal operation:

- **No figures staged** — any evidence that lives in a figure (figure captions, plot values, table contents) is invisible. Sarol's biomedical corpus is text-heavy so this is mostly OK, but known-to-exist figure-derived claims will be undercalled.
- **No section structure** — the extractor's section checklist reduces to a single `content` line. Per-section phrasing search (`rg` against `Methods.txt`, `Results.txt`, etc.) is impossible; the extractor falls back to `content.txt` which is slower and noisier.
- **Rubric collapse** — paper-trail's CONFIRMED_WITH_MINOR, OVERSTATED_MILD, PARTIALLY_SUPPORTED, AMBIGUOUS, UNVERIFIED_ATTESTATION are not in Sarol's 9-class scheme. Forcing an adjudicator trained to emit those to instead pick from Sarol's categories may systematically mis-label borderline cases.
- **No claim-type classifier** — confidence modulation of extractor search effort (low/medium confidence → strictest DIRECT-level evidence bar) is absent.

Net for Variant A: the benchmark is plausibly representative of verdict-core behavior on well-formed inputs but **cannot rule out that claim-extraction / ingest errors dominate end-to-end performance**. That's what the other experiments cover.

## Why Variant C helps but doesn't fully close the gap

Variant C feeds full citing PDFs, so paper-trail does real bib resolution, real PDF fetch, real GROBID ingest, real figure inspection. Phases 1–7, 8 all run faithfully.

But Variant C introduces a **claim-alignment problem**:

- Paper-trail extracts every `\cite{}` in the citing paper, not just the ones Sarol annotated.
- To compute F1 against Sarol's gold, we must match paper-trail's extracted claims to Sarol's annotated `citation_context.text` for the same `marker_span.text`.
- Exact string match will miss cases where paper-trail's claim extractor tokenizes or normalizes differently. Fuzzy match (embedding similarity + character-span overlap) will match most but introduce noise.
- Unmatched annotated claims (paper-trail didn't extract them or mis-located them) are effectively a **recall failure of the claim-extractor phase** — they count as misses even though Variant C's target is the verdict core's performance conditional on a claim being extracted.
- Extra paper-trail-extracted claims not in Sarol gold are simply unscored (free signal for qualitative analysis, no F1 impact).

Report both numbers in the paper:

1. **Coverage:** fraction of Sarol-annotated citations that paper-trail extracted and produced a verdict for.
2. **Conditional F1:** on the covered subset, how well paper-trail's verdict matched Sarol's gold.

A low coverage × high conditional F1 reads as "extractor under-retrieves; verdict core is strong when fed." A high coverage × low F1 reads as "the bottleneck is the verdicts, not extraction."

## What this benchmark *cannot* tell us

Do not claim any of the following based on Sarol numbers alone:

- **paper-trail's cross-domain capability.** Sarol is biomedical only. Needs a different benchmark (MSVEC was ruled out for scope reasons; SemanticCite's cross-domain set has LLM-generated labels, not gold). Opt-in cohort + user-volunteered non-biomed manuscripts are the only credible path, and they're small-sample.
- **paper-trail's rubric quality.** We're testing under Sarol's rubric. Our native rubric (with CONFIRMED_WITH_MINOR, OVERSTATED_MILD, etc.) is evaluated separately on synthetic injection + opt-in cohort experiments.
- **paper-trail's bib-resolution or fetching reliability.** Variant A bypasses entirely; Variant C tests only against PMC-OA sources with reliable PMC IDs. Real-world cases with paywalled refs, malformed bib entries, or non-OA journals are tested by the opt-in cohort.
- **paper-trail's figure-inspection accuracy.** Untested on Sarol. The extractor does vision calls on figures during normal operation; none of that shows up in Variant A, and Variant C only partially (whether a figure happens to be informative for an annotated claim).
- **paper-trail's handling of ingest failures, paywalls, OCR fallbacks.** All untested.

## Is Sarol the best available external benchmark?

Yes, for the verdict-core task. We surveyed alternatives in `docs/plans/paper-tool-validation.md`; restating the outcome:

| Dataset | Why not a better fit |
| --- | --- |
| SciFact / SciFact-Open | General claim verification (claim vs corpus). Claims are synthesized atomic assertions, not real in-paper citations. Out of scope. |
| HealthVer / COVID-Fact / PubHealth / MSVEC | Fact-checking of public or adversarial claims. Not citation integrity. Blast-radius risky for our framing. |
| SciClaimHunt | Similar fact-verification framing. Out of scope. |
| SemanticCite 1,111-citation dataset | Labels are GPT-4.1 generated, not human. Silver-standard at best. |
| Greenberg 2009 / Hagen 2022 / Brown 2024 distortion chains | Case-study scale (N=1 per chain). Already replicated in Sarol et al. 2025 (ASIS&T). |
| PubMed errata | Author-acknowledged corrections; we plan to use but it's recall-only and a noisier signal (most errata are non-citation). |

So Sarol 2024 is uniquely positioned: **human-annotated (5 annotators, Cohen's κ reported), public (MIT license), aligned to the citation-integrity task, and large enough (3,063 instances) for meaningful per-class F1**. Other experiments round out what Sarol can't test.

## Paper-write-up guidance

**Honest framing.** *"We evaluate paper-trail's three-agent verdict core (extractor → adjudicator → verifier) on the Sarol 2024 citation-integrity benchmark under the Sarol 9-class rubric. Upstream pipeline stages (claim extraction, bibliographic resolution, PDF fetching, structural ingest, figure inspection) are bypassed in Variant A and partially tested in Variant C; they are evaluated separately via synthetic injection [§X] and opt-in cohort studies [§Y]."*

**Cross-referenced limitations list.** Include a table mirroring this doc's "What this benchmark cannot tell us" and "What is idealized / impaired" sections. Reviewers ask; better to volunteer.

**Numbers to report.**

- Variant A: 3-way micro/macro F1 against MultiVerS + GPT-4 4-shot baselines (apples-to-apples). 9-way per-class F1 as the first published baseline at that granularity.
- Variant C: coverage + conditional F1. Full-pipeline vs verdict-core deltas. Case studies for prominent wins and losses.
- Do NOT report a single headline "paper-trail F1 on Sarol" number. Report the decomposition.

**Do not imply end-to-end.** paper-trail's end-to-end story is better told via Variants C + synthetic injection + opt-in cohort. Sarol is one piece.

## Open questions

- **Should Variant C normalize paper-trail-extracted claims before matching to Sarol gold?** Exact-span alignment vs fuzzy similarity vs semantic embedding — pick one and justify. Defer to post-pilot analysis.
- **Do we publish a "paper-trail-native rubric on Sarol" as a secondary evaluation?** Would require re-adjudicating using the native rubric and mapping paper-trail labels → Sarol's 3-way for scoring. Possibly useful ablation; decide after Variant A numbers are in.
- **Does the Sarol rubric's exclusion of AMBIGUOUS disadvantage paper-trail?** Paper-trail uses AMBIGUOUS as a triage state; forcing a choice on legitimately-uncertain cases may depress F1. Measure by tracking how often the adjudicator's `nuance` field indicates uncertainty under the Sarol rubric.
