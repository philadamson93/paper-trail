#!/usr/bin/env python3
"""Gate A -- paper fidelity of the Sarol class definitions.

Plan A's P0 reset replaced this repository's transcription of the Sarol 2024 annotation scheme with
the paper's verbatim text. Three of our definitions had diverged, all by our own additions, and all
in the judge's read path -- which is the most parsimonious explanation for why the two worst-precision
classes were exactly the two we mis-transcribed. Nothing in the engine guards that text, so this
script is the guard: it asserts the eight paper-defined classes appear verbatim everywhere the judge
can read them, that the ninth is marked as house text, and that none of the three retired divergent
clauses has crept back.

Run:  ~/.local/bin/python3.13 scripts/check_paper_fidelity.py
Exit: 0 all checks pass; 1 any check fails.
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
EXPERIMENT = HERE.parent

# Sarol MJ, Schneider J, Kilicoglu H. Bioinformatics 40(7):btae420, 2024. Sec 2.2 / Table 1.
# https://pmc.ncbi.nlm.nih.gov/articles/PMC11231046/ -- reconciled verbatim 2026-09-09.
PAPER_DEFINITIONS = {
    "ACCURATE":
        "The citation context is consistent with an evidence segment in the reference article.",
    "CONTRADICT":
        "The citation context contradicts a statement made in the reference article.",
    "NOT_SUBSTANTIATE":
        "The citation is relevant to the content of the reference article but the cited reference "
        "fails to substantiate all statements made in the citing paper.",
    "IRRELEVANT":
        "There is no information in the reference article relevant to the citation.",
    "OVERSIMPLIFY":
        "The findings of the reference article are oversimplified or overgeneralized.",
    "MISQUOTE":
        "The numbers or percentages are misquoted.",
    "INDIRECT":
        "The evidence segment includes a citation to other articles, indicating that the reference "
        "article is not the original source of the cited information.",
    "ETIQUETTE":
        "The citation style is ambiguous and it is unclear what is being cited from the reference "
        "article.",
}

# The ninth class is ours and must say so wherever it is defined.
HOUSE_CLASS = "INDIRECT_NOT_REVIEW"
HOUSE_MARKER = "house definition — not in Table 1"

# Every file the judge can read that carries the class definitions. The rubric is the operative
# source; the dispatch prompt inlines the same text because the judge reads both in one session, so
# a divergence between them would silently defeat the reset.
JUDGE_PATH_FILES = (
    EXPERIMENT / "specs" / "verdict_schema_sarol.md",
    EXPERIMENT / "prompts" / "adjudicator-dispatch-sarol.md",
)
# Optimizer-facing reference: same text, plus provenance. Not loaded by the judge.
REFERENCE_FILE = EXPERIMENT / "specs" / "verdict_definitions_sarol.md"

# The three clauses P0 retired. Each was our addition; each must stay gone from the judge's read
# path. The reference file may quote them in its correction table, so it is exempt.
RETIRED_CLAUSES = (
    ("ACCURATE over-strictness", "directly supports the claim as stated"),
    ("ACCURATE over-strictness (dispatch gloss)", "evidence directly supports the sub-claim"),
    ("OVERSIMPLIFY append", "Narrower-in-source than claimed"),
    ("OVERSIMPLIFY append (lowercased)", "narrower-in-source than claimed"),
    ("NOT_SUBSTANTIATE substitution", "Partial support but key element missing"),
    ("NOT_SUBSTANTIATE substitution (dispatch gloss)", "partial support; key element missing"),
)


def _normalize(text: str) -> str:
    """Collapse markdown line-wrapping so a wrapped quote still matches the paper's sentence."""
    return " ".join(text.split())


def main() -> int:
    failures: list[str] = []
    checks = 0

    for path in JUDGE_PATH_FILES + (REFERENCE_FILE,):
        if not path.exists():
            failures.append(f"MISSING FILE: {path}")
            continue
        blob = _normalize(path.read_text(encoding="utf-8"))
        rel = path.relative_to(EXPERIMENT)

        for label, definition in PAPER_DEFINITIONS.items():
            checks += 1
            if _normalize(definition) not in blob:
                failures.append(f"{rel}: {label} is not the paper's verbatim text")

        checks += 1
        if HOUSE_CLASS in blob and _normalize(HOUSE_MARKER) not in blob:
            failures.append(
                f"{rel}: {HOUSE_CLASS} is defined but not marked '{HOUSE_MARKER}'"
            )

    for path in JUDGE_PATH_FILES:
        if not path.exists():
            continue
        blob = _normalize(path.read_text(encoding="utf-8"))
        rel = path.relative_to(EXPERIMENT)
        for name, clause in RETIRED_CLAUSES:
            checks += 1
            if _normalize(clause) in blob:
                failures.append(f"{rel}: retired clause is back -- {name}: {clause!r}")

    # The one post-v0 clause P0 deliberately re-applied. It is the only statistically real gain of
    # the whole run and the edit most likely to be lost, so its presence is asserted, not assumed.
    dispatch = EXPERIMENT / "prompts" / "adjudicator-dispatch-sarol.md"
    checks += 1
    if dispatch.exists() and '"evidence": []' not in dispatch.read_text(encoding="utf-8"):
        failures.append(
            "prompts/adjudicator-dispatch-sarol.md: the re-applied evidence-array clause is missing"
        )

    if failures:
        print(f"Gate A FAILED -- {len(failures)} of {checks} checks:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"Gate A passed -- {checks} checks.")
    print(f"  8 paper-verbatim definitions in {len(JUDGE_PATH_FILES)} judge-path files + reference")
    print(f"  {HOUSE_CLASS} marked as house text")
    print(f"  {len(RETIRED_CLAUSES)} retired divergent clauses absent from the judge's read path")
    print("  the re-applied evidence-array clause is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
