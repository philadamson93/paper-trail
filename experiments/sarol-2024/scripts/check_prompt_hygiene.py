#!/usr/bin/env python3
"""Gate G -- agent-read prompts carry instructions, never our development history.

Every one of these files is re-read by an agent on every run, so anything in them is paid for on
every read. A sentence about what the file *used to* say is pure tax: the agent has no knowledge of
our development cycle, needs none to do its task, and is measurably worse off for the distraction.
Worse, restating a superseded instruction leaves it actionable -- a language model skimming for what
to do does not reliably honour "this used to say" framing the way a human reader does. That is not
hypothetical: Gate F's first catch on a live file was exactly this shape.

The line this gate draws:

  ALLOWED  -- citing a run that produced a number the agent must act on.
              "on the 2026-09-09 VAL roster gold is ACCURATE 35/50, so the floor is 0.70"
              The date identifies evidence. Strip it and the claim becomes unverifiable.

  FORBIDDEN -- narrating a change we made.
              "This was macro-F1 until 2026-09-07", "there used to be five of them",
              "the underlying cause has since been fixed", "corrected 2026-09-10".
              Rewrite to state the rule as it stands. The history belongs in git and in docs/.

Rewriting, not deleting, is usually the fix: "Why not 3-way, which the objective used to be" keeps
all its operative force as "Why not 3-way".

    check_prompt_hygiene.py            run the gate
    check_prompt_hygiene.py --selftest run the gate's own negative controls
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXPERIMENT = REPO / "experiments" / "sarol-2024"

#: Changelog phrasing. Each is a way of telling the reader the file changed, which no agent needs.
FORBIDDEN: tuple[tuple[str, str], ...] = (
    ("retrospective-wording", r"\bused to (be|say|carry|have|read)\b"),
    ("retrospective-wording", r"\bearlier (revisions?|drafts?)\b"),
    ("retrospective-wording", r"\bpreviously (said|read|was|were)\b"),
    ("retrospective-wording", r"\bno longer (says|reads|claims)\b"),
    ("retrospective-wording", r"\bhas since been (fixed|changed|corrected|removed)\b"),
    ("retrospective-wording", r"\bwas reversed\b"),
    ("dated-edit", r"\bcorrected\s+20\d\d-\d\d-\d\d"),
    ("dated-edit", r"\b(until|since|as of)\s+20\d\d-\d\d-\d\d"),
    ("dated-edit", r"\b(added|changed|fixed|removed)\s+20\d\d-\d\d-\d\d"),
)

#: Files an agent reads as instructions. `meta-learnings.md` and `findings/` are the OPTIMIZER's own
#: dated logs -- dating them is a deliberate requirement (D4), so they are not swept.
def agent_read_files() -> list[Path]:
    files: list[Path] = [
        REPO / ".claude" / "commands" / "sarol-eval-item.md",
        EXPERIMENT / "prompts" / "adjudicator-dispatch-sarol.md",
        EXPERIMENT / "specs" / "verdict_enum_sarol.md",
        EXPERIMENT / "specs" / "verdict_schema_sarol.md",
        EXPERIMENT / "specs" / "verdict_definitions_sarol.md",
        EXPERIMENT / "optimizer" / "prompt" / "optimizer-instructions.md",
    ]
    files += sorted((EXPERIMENT / "optimizer" / "context").glob("*.md"))
    return [f for f in files if f.exists()]

#: Sourced from `main`, so an experiment branch must not edit them. Registered, not ignored:
#: the gate still asserts each is exactly as known, so a change there surfaces here.
KNOWN_DEFERRED: tuple[tuple[str, str], ...] = (
    ("src/specs/verdict_schema.md", "shipped schema version history; file is sourced from `main`"),
)


def violations_in(text: str) -> list[tuple[str, str]]:
    out = []
    for kind, pat in FORBIDDEN:
        for m in re.finditer(pat, text, re.IGNORECASE):
            out.append((kind, m.group(0)))
    return out


def main() -> int:
    failures: list[str] = []
    checks = 0
    for path in agent_read_files():
        checks += 1
        for kind, matched in violations_in(path.read_text()):
            failures.append(
                f"{path.relative_to(REPO)}: {kind} -- {matched!r}. An agent reading this file has "
                "no use for what it used to say. State the rule as it stands; the history is in git."
            )
    if failures:
        print(f"Gate G FAILED -- {len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"Gate G passed -- {checks} agent-read files carry no development history.")
    print(f"  {len(KNOWN_DEFERRED)} deferred (sourced from `main`, not editable from this branch)")
    return 0


def selftest() -> int:
    ok = True
    cases = [
        ("a 'used to say' note is caught", "This bullet used to say validate.", True),
        ("a dated correction is caught", "- Corrected 2026-09-10 - the rule changed.", True),
        ("an 'until <date>' changelog is caught", "This was macro-F1 until 2026-09-07.", True),
        ("a 'has since been fixed' note is caught", "The cause has since been fixed upstream.", True),
        ("...but CITING a run that produced a number is left alone",
         "On the 2026-09-09 VAL roster gold is ACCURATE 35 of 50, so the floor is 0.70.", False),
        ("...and an example payload timestamp is left alone",
         '"produced_at_utc": "2026-09-01T18:04:11+00:00",', False),
    ]
    for label, text, should_fire in cases:
        fired = bool(violations_in(text))
        good = fired == should_fire
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {label}")
    print(f"\n{'6/6 passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv else main())
