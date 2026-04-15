Check a document against submission guidelines. Build a requirement-indexed compliance table keyed to source URLs. Re-run on demand to re-verify before the deadline.

## Invocation forms

- `/check-style <guide-url> <path/to/main.tex>` — guide from a URL (journal author info, thesis template page, conference style sheet)
- `/check-style <guide-pdf> <path/to/main.tex>` — guide from a local PDF
- `/check-style --recheck` — re-verify `compliance_table.md` against the current document
- Multiple guide URLs can be provided, space-separated, when requirements span several pages.

## Step 1 — Extract requirements from the guide

Read the submission guide(s). Enumerate every concrete, checkable requirement. Typical categories:

- **Formatting**: margins, font family/size, line spacing, pagination style, title page layout.
- **Structure**: required sections (abstract, TOC, references, appendices), required ordering, max/min page counts.
- **Attribution**: author role designation for co-authored chapters, copyright permissions for previously published material.
- **Compilation**: PDF format (PDF/A, embedded fonts, resolution), figure format requirements.
- **File handling**: naming conventions, max filename length, supplementary material limits, permitted characters.

For each requirement:

- State the rule concisely (e.g., "1.5\" binding margin, 1\" other margins").
- Capture the source URL + section anchor / page so future re-checks can link back.

Skip anything the guide is silent on. Do not invent requirements.

## Step 2 — Build or update `compliance_table.md`

Write/update `compliance_table.md` at the project root. Format:

```markdown
# Submission Compliance — <venue name>

**Guide source(s):**
- <URL or PDF path 1>
- <URL or PDF path 2>

**Document:** <path/to/main.tex>
**Last checked:** <ISO date>
**Deadline:** <if known>

## Requirements

| # | Requirement | Source | Status | Notes |
|---|-------------|--------|--------|-------|
| 1 | Margins: 1.5" binding, 1" others | <url#sec> | COMPLIANT | `geometry` package configured |
| 2 | Author role designation for co-authored chapters | <url#sec> | NOT-COMPLIANT | Missing from introduction |
| ... |  |  |  |  |

## Must-fix

- <requirement N>: <specific action>
- ...
```

Status codes:

- **COMPLIANT** — verified from source text (e.g., geometry package) or compiled output.
- **VERIFY** — needs visual check at compile time (widows, orphans, margins, page breaks).
- **NOT-COMPLIANT** — concrete gap identified; requires fix before submission.
- **PENDING** — not yet checked.
- **N/A** — requirement doesn't apply to this document.

## Step 3 — Compile and visual scan

If a compile command is inferable (`latexmk`, `pdflatex main.tex`, `Makefile`, `build.sh`), run it. Then inspect the output PDF:

- Plausible page count against any stated limit?
- Margins visually correct on a sampled page?
- Widows and orphans present on spot-checked pages?
- Overfull `hbox` warnings in the log?
- All required prelim sections present in the expected order (title, abstract, TOC, lists if required)?
- Arabic-vs-Roman pagination transition correct?

Update VERIFY entries to COMPLIANT or NOT-COMPLIANT based on the scan. Note which specific pages were checked in the `Notes` column.

## Step 4 — Report gaps

Print a short triage:

```
Compliance summary — <venue>:
  COMPLIANT:     X
  VERIFY:        Y (needs visual check)
  NOT-COMPLIANT: Z (must fix before submission)
  PENDING:       K

Must-fix before submission:
- <requirement>: <concrete action>
- ...
```

## Re-check mode

On `--recheck`:

- Preserve existing table entries and their source references.
- Re-verify `VERIFY` and `NOT-COMPLIANT` entries against the current state of the document.
- Leave `COMPLIANT` entries alone unless the document has changed materially (e.g., `main.tex` modified more recently than the table's `Last checked` date).
- Update `Last checked` to today's date when done.

## Do not

- Never mark a requirement `COMPLIANT` without a concrete source — either a quote from the guide or evidence from the compiled output.
- Never invent a requirement the guide doesn't state.
- Never auto-fix a `NOT-COMPLIANT` item. Flag it and let the user decide on the remediation.
- Never treat a silent guide as permissive; silence means the requirement is not stated, not that it's not needed.
