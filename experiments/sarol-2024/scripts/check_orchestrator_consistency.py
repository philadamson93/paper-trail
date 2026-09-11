#!/usr/bin/env python3
"""Gate F -- nothing an orchestrating session reads may tell it to break the driver's contract.

Gate A guards the *judge's* read path. Nothing guarded the *driver's*, and on 2026-09-10 that gap
produced a live contradiction: `adjudicator-dispatch-sarol.md`'s `## Orchestrator notes` told the
dispatching session to "Validate the exit JSON" while `.claude/commands/sarol-eval-item.md` step 4
forbids exactly that. Both files are read by the same session on every claim. It survived five
review passes because every one of them was pointed at the judge -- the same "audited the direction
that had a test, never the direction that had only prose" shape the isolation findings name as the
root cause of this whole episode.

So this gate mirrors Gate A one layer over: it takes the driver's hard prohibitions as the contract
and asserts that no orchestrator-facing prose contradicts them.

"Orchestrator-facing" = the text OUTSIDE the `## Begin dispatch prompt` / `## End dispatch prompt`
markers. The driver passes on only what is between them, so everything outside is addressed to the
driver itself -- which is exactly why it must obey the driver's rules.

Deferred violations are ALLOWLISTED, not ignored (see KNOWN_DEFERRED): each is inert only because
its stage is unimplemented, so the gate also asserts those stages are still unimplemented. The day
Plan B widens `IMPLEMENTED_STAGES`, this gate fails and the allowlist must be paid down first.

    check_orchestrator_consistency.py            run the gate
    check_orchestrator_consistency.py --selftest run the gate's own negative controls
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXPERIMENT = REPO / "experiments" / "sarol-2024"
DRIVER = REPO / ".claude" / "commands" / "sarol-eval-item.md"

BEGIN_MARKER = "## Begin dispatch prompt"
END_MARKER = "## End dispatch prompt"

#: The driver's hard prohibitions. `phrase` must appear in the driver -- deleting a prohibition is
#: itself a contract change and fails this gate. `forbids` are the instruction shapes that
#: contradict it if they appear in orchestrator-facing prose.
PROHIBITIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "never validate the subagent's content",
        "Do not validate its content",
        (r"\bvalidate\b[^.\n]{0,40}\b(exit|output)\s+JSON",
         r"\bschema[- ]validates?\b[^.\n]{0,30}\bbefore\b",
         r"\bvalidate\b[^.\n]{0,30}\bagainst the schema\b"),
    ),
    (
        "never retry a stage",
        "Never retry a stage",
        (r"\bretry\b", r"\bre-?dispatch\b", r"\bbounce(s|_to_)?\b"),
    ),
    (
        "never author or repair the verdict",
        "Never write the stage's output file yourself",
        (r"\bupdate the verdict JSON\b", r"\bflag-?patch\b", r"\bkeep malformed output\b"),
    ),
    (
        "never read gold",
        "Never read, and never look for, gold labels",
        (r"\bread\b[^.\n]{0,20}\bgold\b",),
    ),
    (
        "never ask a question",
        "Never ask a question",
        (r"\bask the user\b",),
    ),
)

#: Prompt files the driver can dispatch. These are the non-contract prompt entries of the
#: program manifest -- the surface whose orchestrator notes the driver actually reads.
DISPATCH_PATH_FILES: tuple[Path, ...] = (
    EXPERIMENT / "prompts" / "adjudicator-dispatch-sarol.md",
    REPO / "src" / "prompts" / "extractor-dispatch-pdf.md",
    REPO / "src" / "prompts" / "extractor-dispatch-paperclip.md",
    REPO / "src" / "prompts" / "verifier-dispatch.md",
)

#: (file stem, prohibition, why it is inert today, the stage that would arm it).
#: NOT a suppression list: `--selftest`'s third control asserts every armed-by stage is still
#: absent from `profiles.IMPLEMENTED_STAGES`. Implementing that stage fails this gate by design.
#: (file stem, prohibition, EXACT offending text, arming stage). The offending text is pinned
#: per-occurrence on purpose: keying only on (file, prohibition) would suppress a DIFFERENT forbidden
#: sentence later added to the same file under the same prohibition -- a register that grows silently
#: is the suppression list it was meant not to be.
KNOWN_DEFERRED: tuple[tuple[str, str, str, str], ...] = (
    ("extractor-dispatch-pdf", "never validate the subagent's content",
     "Validate the extractor's exit JSON", "extractor"),
    ("extractor-dispatch-pdf", "never retry a stage", "retry", "extractor"),
    ("extractor-dispatch-paperclip", "never validate the subagent's content",
     "Validate the extractor's exit JSON", "extractor"),
    ("extractor-dispatch-paperclip", "never retry a stage", "retry", "extractor"),
    ("verifier-dispatch", "never retry a stage", "bounce", "verifier"),
    ("verifier-dispatch", "never author or repair the verdict", "flag-patch", "verifier"),
)


def orchestrator_region(text: str) -> str:
    """Everything outside the dispatch-prompt markers -- i.e. addressed to the driver."""
    if BEGIN_MARKER in text and END_MARKER in text:
        head, rest = text.split(BEGIN_MARKER, 1)
        _body, tail = rest.split(END_MARKER, 1)
        return head + "\n" + tail
    return text


def violations_in(path: Path) -> list[tuple[str, str]]:
    """(prohibition, matched text) for every forbidden instruction in this file's driver-facing prose."""
    region = orchestrator_region(path.read_text())
    found = []
    for name, _phrase, patterns in PROHIBITIONS:
        for pat in patterns:
            m = re.search(pat, region, re.IGNORECASE)
            if m:
                found.append((name, m.group(0)))
                break
    return found


def main() -> int:
    failures: list[str] = []
    checks = 0

    driver_text = DRIVER.read_text()
    for name, phrase, _ in PROHIBITIONS:
        checks += 1
        if phrase not in driver_text:
            failures.append(
                f"the driver no longer states the prohibition {name!r} (looked for {phrase!r}). "
                "A prohibition is the contract this gate enforces; removing one is a contract change."
            )

    deferred = {(stem, proh, text.lower()) for stem, proh, text, _ in KNOWN_DEFERRED}
    seen_deferred: set[tuple[str, str]] = set()

    for path in DISPATCH_PATH_FILES:
        checks += 1
        if not path.exists():
            failures.append(f"{path.relative_to(REPO)} is missing from the dispatch path")
            continue
        for proh, matched in violations_in(path):
            key = (path.stem, proh, matched.lower())
            if key in deferred:
                seen_deferred.add(key)
                continue
            failures.append(
                f"{path.relative_to(REPO)}: orchestrator-facing prose says {matched!r}, which "
                f"contradicts the driver's rule {proh!r}. The dispatching session reads both."
            )

    # A deferral that no longer matches is a stale entry -- pay it down rather than carrying it.
    checks += 1
    for key in sorted(deferred - seen_deferred):
        failures.append(
            f"KNOWN_DEFERRED carries {key} but no such violation was found. "
            "The text was fixed; delete the allowlist entry."
        )

    sys.path.insert(0, str(EXPERIMENT / "optimizer"))
    import profiles  # noqa: E402

    for stem, proh, _why, arming_stage in KNOWN_DEFERRED:
        checks += 1
        if arming_stage in profiles.IMPLEMENTED_STAGES:
            failures.append(
                f"stage {arming_stage!r} is now implemented, which ARMS the deferred contradiction "
                f"({stem}, {proh}). Fix the prose before shipping that stage."
            )

    if failures:
        print(f"Gate F FAILED -- {len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"Gate F passed -- {checks} checks.")
    print(f"  {len(PROHIBITIONS)} driver prohibitions present and un-contradicted")
    print(f"  {len(DISPATCH_PATH_FILES)} dispatch-path files swept for driver-facing contradictions")
    print(f"  {len(KNOWN_DEFERRED)} deferred, each still inert (its stage unimplemented)")
    return 0


def selftest() -> int:
    """Negative controls. A gate that cannot fail is not a gate."""
    ok = True

    live = "## Orchestrator notes\n\n- Validate the exit JSON against the schema.\n"
    hit = [p for p, _ in _violations_in_text(live)]
    print(f"  {'PASS' if 'never validate' in ' '.join(hit) else 'FAIL'}  "
          "a 'Validate the exit JSON' note is caught (the 2026-09-10 defect)")
    ok &= "never validate" in " ".join(hit)

    retry = "## Orchestrator notes\n\n- Schema violations -> one retry with a pointed message.\n"
    hit = [p for p, _ in _violations_in_text(retry)]
    print(f"  {'PASS' if 'never retry a stage' in hit else 'FAIL'}  a 'one retry' note is caught")
    ok &= "never retry a stage" in hit

    inside = (f"{BEGIN_MARKER}\nValidate the exit JSON against the schema.\n{END_MARKER}\n")
    hit = _violations_in_text(inside)
    print(f"  {'PASS' if not hit else 'FAIL'}  "
          "...but the SAME text between the dispatch markers is NOT flagged -- it goes to the "
          "judge, not the driver, so the gate must not fire on it")
    ok &= not hit

    clean = "## Orchestrator notes\n\n- Sampling: pick one evidence entry at random.\n"
    hit = _violations_in_text(clean)
    print(f"  {'PASS' if not hit else 'FAIL'}  benign orchestrator prose is left alone")
    ok &= not hit

    # The four above exercise the regex helper. These three exercise main() -- the gate's real
    # decision path -- because the advertised allowlist and prohibition claims were previously
    # asserted only in a comment. A control that tests the helper does not test the gate.
    import copy
    real_stages = None
    try:
        sys.path.insert(0, str(EXPERIMENT / "optimizer"))
        import profiles as _pf
        real_stages = _pf.IMPLEMENTED_STAGES
        _pf.IMPLEMENTED_STAGES = tuple(list(real_stages) + ["extractor"])
        armed = main() == 1
    finally:
        if real_stages is not None:
            _pf.IMPLEMENTED_STAGES = real_stages
    print(f"  {'PASS' if armed else 'FAIL'}  implementing a deferred stage ARMS its contradictions "
          "and fails the gate (the allowlist is tripwired, not a suppression list)")
    ok &= armed

    real_def = KNOWN_DEFERRED
    globals()["KNOWN_DEFERRED"] = real_def + (
        ("verifier-dispatch", "never retry a stage", "a sentence that is not present", "verifier"),)
    stale = main() == 1
    globals()["KNOWN_DEFERRED"] = real_def
    print(f"  {'PASS' if stale else 'FAIL'}  a deferral whose exact text is absent fails "
          "(occurrence-level, so swapping in a different violation cannot hide behind it)")
    ok &= stale

    real_proh = PROHIBITIONS
    globals()["PROHIBITIONS"] = tuple(
        (n, "a phrase the driver does not contain", pats) if i == 0 else (n, ph, pats)
        for i, (n, ph, pats) in enumerate(real_proh))
    deleted = main() == 1
    globals()["PROHIBITIONS"] = real_proh
    print(f"  {'PASS' if deleted else 'FAIL'}  deleting a hard prohibition from the driver fails "
          "(the contract cannot be quietly narrowed)")
    ok &= deleted

    print(f"\n{'7/7 passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


def _violations_in_text(text: str) -> list[tuple[str, str]]:
    region = orchestrator_region(text)
    found = []
    for name, _phrase, patterns in PROHIBITIONS:
        for pat in patterns:
            m = re.search(pat, region, re.IGNORECASE)
            if m:
                found.append((name, m.group(0)))
                break
    return found


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv else main())
