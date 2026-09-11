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

import pathlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXPERIMENT = REPO / "experiments" / "sarol-2024"

#: Changelog phrasing. Each is a way of telling the reader the file changed, which no agent needs.
FORBIDDEN: tuple[tuple[str, str], ...] = (
    ("retrospective-wording", r"\bused to (be|say|carry|have|read|claim|promise|require|mean)\b"),
    ("retrospective-wording", r"\b(an|the) earlier (revisions?|drafts?|versions?)\b"),
    ("retrospective-wording", r"\bthis (file|document|section) (used to|once)\b"),
    ("superseded-instruction", r"~~[^~]{10,}~~"),
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

#: Sourced from `main`, so an experiment branch must not edit them. Registered, not ignored: the
#: gate asserts each entry is a REAL, still-present violation, so a stale entry fails rather than
#: drifting. Empty is the correct state today -- and the register's logic is still exercised by
#: selftest's injected-stale-entry control, so it cannot rot while unused. A mechanism tested only
#: when non-empty is green-by-absence, which is the defect this whole gate family exists for.
#:
#: ⚠ `src/specs/verdict_schema.md` is deliberately OUT OF SCOPE rather than deferred: it is a
#: shipped schema contract whose version history is part of its function (a consumer needs to know
#: what changed between 1.0 and 1.1), it is not injected into any agent as instructions, and it is
#: sourced from `main`. Listing it here was wrong on both counts -- the entry claimed a violation
#: this gate's rules do not flag, so it read as coverage while asserting nothing.
KNOWN_DEFERRED: tuple[tuple[str, str], ...] = ()


def _normalize(text: str) -> str:
    """Collapse markdown line-wrapping so a wrapped phrase still matches.

    Reuses `check_paper_fidelity.py`'s idiom rather than re-deriving it. Without this the gate is
    defeated by an authored line break: "four documents used to\nsay it was" did NOT match
    `used to say`, because the pattern's literal space is not a newline. That miss was real and
    shipped -- an audit found it in `edit-surface.md`. A gate that a line wrap can silence is not
    a gate, so normalization happens before matching, always.
    """
    return " ".join(text.split())


def violations_in(text: str) -> list[tuple[str, str]]:
    flat = _normalize(text)
    out = []
    for kind, pat in FORBIDDEN:
        for m in re.finditer(pat, flat, re.IGNORECASE):
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
    # The deferred register is an ASSERTION, not a note. It was dead data on first ship -- declared
    # and never consumed -- which is the "suppression list dressed as a register" shape this gate
    # exists to avoid, committed by this gate. Each entry must still be a real, still-present
    # violation: if the prose was fixed, the entry is stale and must be deleted, and if the file
    # vanished the deferral is meaningless. Either way the gate fails rather than drifting.
    for rel, reason in KNOWN_DEFERRED:
        checks += 1
        path = REPO / rel
        if not path.exists():
            failures.append(f"KNOWN_DEFERRED names {rel}, which does not exist -- delete the entry")
            continue
        if not violations_in(path.read_text()):
            failures.append(
                f"KNOWN_DEFERRED carries {rel} ({reason}) but it is now clean. "
                "The prose was fixed; delete the allowlist entry rather than carrying it."
            )

    if failures:
        print(f"Gate G FAILED -- {len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"Gate G passed -- {checks} agent-read files carry no development history.")
    n = len(KNOWN_DEFERRED)
    print(f"  {n} deferred" + (", each verified still-violating" if n else " (register empty; its logic is covered by --selftest)"))
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

    # A line break must not silence the gate. This is the miss that shipped: `used to say` is in the
    # pattern list, but "four documents used to\nsay it was" did not match, because the pattern's
    # literal space is not a newline. An audit found it in a swept file the gate had passed.
    wrapped = "because four documents used to\nsay it was frozen"
    fired = bool(violations_in(wrapped))
    ok &= fired
    print(f"  {'PASS' if fired else 'FAIL'}  a phrase broken across an authored LINE WRAP is still "
          "caught (the miss that shipped)")

    # The register's own control: a stale entry must FAIL, proving the mechanism works even though
    # KNOWN_DEFERRED is empty in the shipped state.
    import tempfile
    real_reg, real_repo = KNOWN_DEFERRED, REPO
    with tempfile.TemporaryDirectory() as td:
        clean_file = pathlib.Path(td) / "clean.md"
        clean_file.write_text("# a file with no development history\n")
        globals()["KNOWN_DEFERRED"] = ((clean_file.name, "injected stale entry"),)
        globals()["REPO"] = pathlib.Path(td)
        globals()["_SILENCE"] = True
        stale_caught = main() == 1
    globals()["KNOWN_DEFERRED"], globals()["REPO"] = real_reg, real_repo
    globals()["_SILENCE"] = False
    ok &= stale_caught
    print(f"  {'PASS' if stale_caught else 'FAIL'}  a STALE deferred entry fails the gate "
          "(the register is an assertion, not a note)")

    print(f"\n{'8/8 passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv else main())
