# Plan docs — index

One row per plan in `docs/plans/`. **Status** is the plan's own state; **Reviewed** tracks whether
*Phil* has read the current content — not whether a reviewer agent passed over it.

`Reviewed` values: `Yes` (Phil read the current content, recorded via `/read-plan` or an approved
in-sync `/explain-plan` HTML) · `No` (never) · `Stale` (was `Yes`, edited substantively since).
Only `/read-plan` or `/explain-plan` promotes a row to `Yes`.

`docs/plans/NEXT.md` is the live state doc, not a plan — it is deliberately not listed below.

| Plan | Status | Reviewed | Description |
|---|---|---|---|
| [`add-paper-trail-orchestrator.md`](add-paper-trail-orchestrator.md) | — | No | `/paper-trail` — end-to-end audit of an input PDF (reader / reviewer mode) |
| [`advisor-pitch.md`](advisor-pitch.md) | — | No | Optimization of agentic programs requires instrumentable agentic ecosystems |
| [`agentic-pipeline-optimization-framework.md`](agentic-pipeline-optimization-framework.md) | Authoritative (2026-04-21) | No | Agentic pipeline optimization framework |
| [`author-mode-parity.md`](author-mode-parity.md) | — | No | Author mode — parity with reader mode |
| [`blindspot-mitigations.md`](blindspot-mitigations.md) | Drafted; round 1 impl next | No | v1 blindspot mitigations — rigor gaps in `/paper-trail` and `/ground-claim` |
| [`canary-runbook-vertex.md`](canary-runbook-vertex.md) | Drafted 2026-04-22, not executed | No | Canary runbook — Q9c memory-blind + D44 Agent-tool, on Vertex AI |
| [`experiment-april-20-findings.md`](experiment-april-20-findings.md) | — | No | Experiment April 20 findings: Sarol 2024 N=5 smoketest |
| [`experiment-sarol-archive-and-eval-framework.md`](experiment-sarol-archive-and-eval-framework.md) | Scaffolded, revised 2026-04-21 | No | Archive and evaluation framework for the paper-trail × Sarol experiment |
| [`experiment-sarol-benchmark.md`](experiment-sarol-benchmark.md) | — | No | Experiment: paper-trail on the Sarol 2024 citation-integrity benchmark |
| [`experiment-sarol-eval-arm-isolation.md`](experiment-sarol-eval-arm-isolation.md) | — | No | Eval-arm invocation isolation (Rule 3) |
| [`experiment-sarol-faithfulness.md`](experiment-sarol-faithfulness.md) | — | No | Faithfulness audit: what the Sarol 2024 experiment actually tests |
| [`experiment-sarol-hardening-implementation.md`](experiment-sarol-hardening-implementation.md) | — | No | Implementation: leakage hardening for the Sarol experiment |
| [`experiment-sarol-leakage-hardening.md`](experiment-sarol-leakage-hardening.md) | — | No | Plan: leakage hardening for the Sarol experiment |
| [`experiment-sarol-methods-research.md`](experiment-sarol-methods-research.md) | — | No | Research: systematic use of Sarol's gold-standard labels for paper-trail |
| [`experiment-sarol-optimization-escalation.md`](experiment-sarol-optimization-escalation.md) | — | No | If manual iteration stalls: optimization escalation plan |
| [`experiment-sarol-optimization-loop-hygiene.md`](experiment-sarol-optimization-loop-hygiene.md) | — | No | Operational hygiene for the Sarol experiment optimization loop |
| [`experiment-sarol-runbook.md`](experiment-sarol-runbook.md) | — | No | Runbook: Sarol 2024 benchmark — Variant A smoketest (N=5) |
| [`experiment-sarol-smoketest-handoff.md`](experiment-sarol-smoketest-handoff.md) | — | No | Handoff: run the Sarol 2024 smoketest (N=5) |
| [`experimental-plan-of-record.md`](experimental-plan-of-record.md) | First-pass outline | No | Experimental plan of record |
| [`paper-tool-validation.md`](paper-tool-validation.md) | — | No | paper-trail validation paper — experiment plan |
| [`paper-trail-product-backlog.md`](paper-trail-product-backlog.md) | — | No | paper-trail product backlog |
| [`paper-writeup-items.md`](paper-writeup-items.md) | — | No | Items to touch on in the paper / blog writeup |
| [`papertrail-optimizer-requirements.md`](papertrail-optimizer-requirements.md) | Draft · impl in flight | Stale | papertrail-optimizer-requirements — pin `program-v0`, author the paper-trail optimizer-prompt, and spec the paper-trail consumer that further validates the `agentic-label-opt` seam |
| [`tier-0-resolution-2026-04-22.md`](tier-0-resolution-2026-04-22.md) | — | No | Tier 0 resolution milestone (2026-04-22 / 2026-04-23) |
