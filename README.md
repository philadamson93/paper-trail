<p align="center">
  <img src="assets/logo.jpg" alt="paper-trail" width="180">
</p>

<h1 align="center">paper-trail</h1>

<p align="center">
  <code>paper-trail</code> is a Claude Code–native workflow.
</p>

<p align="center">
  The bracket-number citation is a pre-digital convention: a reader sees <code>[7]</code> and takes the link from claim to source on faith. It doesn't have to work that way anymore. This is what an online journal should look like:
</p>

<p align="center">
  <a href="https://philadamson93.github.io/paper-trail/Adamson-MRM-DFDs-2025.html">
    <img src="https://img.shields.io/badge/Open%20demo-MR%20reconstruction%20(Adamson%202025)-2ea44f?style=for-the-badge" alt="Open demo — MR reconstruction (Adamson 2025)">
  </a>
  &nbsp;
  <a href="https://philadamson93.github.io/paper-trail/Adamson-MRM-DMI-2024.html">
    <img src="https://img.shields.io/badge/Open%20demo-Deuterium%20MRI%20(Adamson%202024)-2ea44f?style=for-the-badge" alt="Open demo — Deuterium MRI (Adamson 2024)">
  </a>
</p>

---

## Why paper-trail

Scientific papers routinely cite 50–100 references, and verifying every one by hand rarely happens — LLM-assisted writing makes plausibly-phrased misattributions easier to produce and harder to spot.

`paper-trail` serves three audiences:

- **Authors** — proofread your own citations before submission; establish the rigor of your grounding work in the record.
- **Reviewers** — skip the manual slog of opening every cited paper; triage from a ledger of flagged entries.
- **Readers and the public** — follow a transparent trail from each claim to its source and decide what to trust.

## Getting Started

Clone this repo and launch Claude Code in it:

```bash
git clone https://github.com/philadamson93/paper-trail.git ~/src/paper-trail
cd ~/src/paper-trail
```

1. **One-time install** — run `/paper-trail-init` to bootstrap system prerequisites (GROBID, poppler, optional MCPs). Details: [docs/prerequisites.md](docs/prerequisites.md).
2. **Audit a paper** — run `/paper-trail` and answer a few setup questions.

For author mode against your own manuscript, vendor-copy `.claude/` and `templates/` into your writing project and invoke `/paper-trail --author` there:

```bash
cp -r ~/src/paper-trail/.claude .
cp -r ~/src/paper-trail/templates .
```

## How it works

```mermaid
flowchart TD
    A["Cited claim<br/>('following Smith 2022…')"] --> B["Fetch source PDF"]
    B --> C["Ingest<br/>(GROBID → sections + figures)"]
    C --> D["Extractor: gather evidence"]
    D --> E["Adjudicator: pick verdict<br/>from rubric"]
    E --> F["Verifier: spot-check<br/>a sampled excerpt"]
    F --> G["Verdict JSON + ledger.md<br/>+ demo.html"]
    classDef default font-size:14px;
```

Say a paper includes *"following the method in Smith et al. 2022, we pretrained for 100 epochs on 1.2M images"* — one citation, two factual sub-claims. `/paper-trail`:

1. **Resolves** `Smith et al. 2022` from the paper's bibliography.
2. **Fetches** the Smith 2022 PDF (arXiv / open-access, or prompts you for institutional access if paywalled).
3. **Ingests** the PDF into structured sections + figures (GROBID, with `pdftotext` / OCR fallbacks).
4. **Extracts evidence** for each sub-claim — the "100 epochs" procedure and the "1.2M images" dataset — with verbatim quotes and page numbers.
5. **Adjudicates** each sub-claim from a fixed rubric: `CONFIRMED`, `OVERSTATED` (Smith says 95 epochs), `UNSUPPORTED` (no epoch count in the paper), `MISATTRIBUTED` (Smith credits another paper for that procedure), `AMBIGUOUS` (close call that awaits human triage), and so on.
6. **Spot-checks** a sampled piece of evidence with a third independent subagent to catch fabricated quotes.
7. **Records** everything — verdict, sub-claim breakdown, evidence quotes, page numbers, suggested fix — in a per-claim JSON. A `ledger.md` and a self-contained `demo.html` viewer are rendered from those JSONs.

Repeat for every citation. At 50+ references per paper, this is why it usually doesn't get done by hand in review.

## Run it

One entry point, two workflows.

### Reader mode — audit someone else's paper

```bash
/paper-trail                                  # fully interactive
/paper-trail <path-to-pdf>                    # audit that PDF
/paper-trail <path-to-pdf> --skip-paywalled   # don't block on paywalled refs
/paper-trail <path-to-pdf> --scope=single     # ground one claim you describe
/paper-trail <path-to-pdf> --triage           # resolve AMBIGUOUS entries
```

Writes a self-contained audit artifact to `./paper-trail-<pdf-stem>/`.

### Author mode — audit your own in-progress manuscript

```bash
/paper-trail --author                         # against current writing project
/paper-trail --author path/to/document.tex    # against a specific .tex
```

Writes to `claims_ledger.md` at the project root — that's both the audit config (YAML frontmatter: `pdf_dir`, `bib_files`, institutional access) and the rendered ledger. On first run, prompts you to bootstrap it via `/init-writing-tools` (one-time, detects your `.bib` and PDF layout).

> **On paywalled sources.** `paper-trail` can only auto-fetch open-access PDFs. Paywalled references are stubbed and marked `PENDING`; drop the PDF in by hand (institutional access, ILL, authors' websites) and re-run to ground them. Nothing bypasses paywalls.

## Cautions

- **LLMs can make mistakes.** Despite attestation and the verifier, the agent can misread tables, misclassify a claim, or get a verdict wrong. Every flagged entry (`UNSUPPORTED`, `CONTRADICTED`, `AMBIGUOUS`, `UNVERIFIED_ATTESTATION`, `CITED_OUT_OF_CONTEXT`, `INDIRECT_SOURCE`, `MISATTRIBUTED`) should be **manually verified** against the cited source before you act on it. Treat the ledger as a triage queue, not a verdict.
- **Editing assistance, not scholarly judgment.** A finding on someone else's published paper is a hypothesis surfaced by an LLM that read the cited source; it is not a ground-truth accounting of prior published work. Use findings as leads to investigate, not as conclusions to publish.

## Learn more

- **[Outputs & verdicts](docs/output.md)** — what files land on disk, full verdict rubric, remediation categories.
- **[Trust model](docs/trust-model.md)** — two-pass dispatch, attestation, verifier, substitution policy.
- **[Internals](docs/internals.md)** — orchestrator phases, component commands, schemas, scripts.
- **[Prerequisites](docs/prerequisites.md)** — what Claude installs for you.

## License

[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) — see [LICENSE](LICENSE).

Free for personal work, academic research, non-profit projects, and internal research at any organization. Commercial use (selling the software, offering it as paid SaaS, incorporating it into a paid product) is not permitted under this license. Open an issue if you'd like a commercial license.

PolyForm NC is a *source-available* license, not OSI-approved "open source". All non-commercial-resale uses are permitted.
