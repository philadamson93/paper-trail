#!/usr/bin/env python3
"""Gate H -- a fresh run starts from a fresh sheet.

`meta-learnings.md` is injected into every optimizer session and is the only thing that carries
forward between iterations. That is the point *within* a run. Across runs it is contamination: a
"fresh" run opens with the previous run's hypotheses, formed against a program that may no longer
exist. Nothing in this repo ever archived or reset it -- it was reset once by hand (S6 of
`optimizer-instrument-repair.md`) while `profiles.py` reasons as though "reset between runs" were a
guaranteed property. This gate makes the sheet's lifecycle real.

⚠ **This is a stopgap, and the real fix is structural.** rad-eval scopes a run by cloning the repo
per run-id (`src/optimizer_loop/run_artifacts.py::default_loop_clone`), so the working tree, `iter/`,
the `program-v*` tag namespace and the optimizer's own docs all isolate for free. paper-trail already
has the run-id -- results land in `~/.paper-trail/runs/<run-id>/` -- but the boundary stops there and
releases, lessons, findings and tags all live in one shared checkout. Adopting the per-run clone
retires this gate and most of the ledger-recut problem with it. Recorded as a contract owed to the
isolation plan, which is already building per-run checkouts.

    check_run_scope.py                 assert this checkout is ready for a FRESH run
    check_run_scope.py --archive <id>  file the current sheet + findings away, then reset
    check_run_scope.py --selftest      negative controls

Override for a deliberate continuation run: `SAROL_ALLOW_INHERITED_LESSONS=1` (same convention as
`SAROL_ALLOW_ENGINE_DIVERGENCE`). It is loud on purpose -- a continuation run's numbers are not
comparable to a fresh one's.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OPT = REPO / "experiments" / "sarol-2024" / "optimizer"
SHEET = OPT / "meta-learnings.md"
STUB = OPT / "meta-learnings.stub.md"
FINDINGS = OPT / "findings"
ARCHIVE_ROOT = Path.home() / ".paper-trail" / "runs" / "_archive"
OVERRIDE = "SAROL_ALLOW_INHERITED_LESSONS"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    """Repo-relative when it is in the repo; the plain path otherwise (the selftest uses tmp dirs)."""
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def stub_bytes() -> bytes | None:
    """The stub as COMMITTED, not as it sits in the worktree.

    Comparing the sheet to the working-tree stub is not a stable anchor: both are ordinary
    optimizer-side files, so one session that rewrote *both* to the same inherited content would
    pass this gate trivially. The committed blob is the anchor -- it cannot be changed by the same
    edit that dirties the sheet. Falls back to the worktree copy only outside a git checkout (the
    selftest), and says so rather than silently degrading.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "show", f"HEAD:{STUB.relative_to(REPO)}"],
            capture_output=True, check=True,
        )
        return out.stdout
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def inherited() -> list[str]:
    """What this checkout would hand a 'fresh' run that does not belong to it."""
    problems = []
    if not STUB.exists():
        problems.append(f"{_rel(STUB)} is missing -- there is no clean sheet to reset to")
        return problems
    committed = stub_bytes()
    if committed is not None and hashlib.sha256(committed).hexdigest() != _sha(STUB):
        problems.append(
            f"{_rel(STUB)} differs from its COMMITTED bytes. The clean sheet is the anchor this "
            "gate compares against, so an edited stub would let inherited content pass. Commit the "
            "stub change deliberately, or revert it."
        )
    if not SHEET.exists():
        problems.append(f"{_rel(SHEET)} is missing entirely; reset it from the stub")
    elif _sha(SHEET) != _sha(STUB):
        problems.append(
            f"{_rel(SHEET)} carries content from a previous run. It is injected into "
            "every optimizer session, so this run would open with hypotheses it did not earn -- "
            "measured against a program P0 may already have deleted."
        )
    stale = sorted(p.name for p in FINDINGS.glob("iter-*.md")) if FINDINGS.exists() else []
    if stale:
        problems.append(
            f"{_rel(FINDINGS)} still holds a previous run's per-iteration findings: "
            f"{', '.join(stale)}"
        )
    return problems


def cmd_archive(run_id: str) -> int:
    dest = ARCHIVE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{run_id}"
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    if SHEET.exists() and STUB.exists() and _sha(SHEET) != _sha(STUB):
        shutil.copy2(SHEET, dest / "meta-learnings.md")
        moved.append("meta-learnings.md")
    if FINDINGS.exists():
        for p in sorted(FINDINGS.glob("iter-*.md")):
            shutil.move(str(p), dest / p.name)
            moved.append(f"findings/{p.name}")
    if STUB.exists():
        shutil.copyfile(STUB, SHEET)
    if not moved:
        dest.rmdir()
        print("nothing to archive; the sheet is already clean.")
        return 0
    print(f"archived {len(moved)} file(s) to {dest}")
    for m in moved:
        print(f"  {m}")
    print(f"reset {_rel(SHEET)} from the stub")
    print("⚠ the sheet is git-tracked, so this leaves a working-tree change -- commit it with the run.")
    return 0


def main() -> int:
    problems = inherited()
    if problems and os.environ.get(OVERRIDE) == "1":
        print(f"Gate H OVERRIDDEN via {OVERRIDE}=1 -- this is a CONTINUATION run.")
        for p in problems:
            print(f"  carrying: {p}")
        print("  ⚠ its numbers are not comparable to a fresh run's. Say so in the writeup.")
        return 0
    if problems:
        print(f"Gate H FAILED -- {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\n  Fix: experiments/sarol-2024/scripts/check_run_scope.py --archive <run-id>\n"
            f"  Or, for a deliberate continuation run: {OVERRIDE}=1",
            file=sys.stderr,
        )
        return 1
    print("Gate H passed -- the optimizer's sheet is clean; this run starts from scratch.")
    print(f"  checkout inspected: {REPO}")
    print("  ⚠ scoped to THIS checkout only -- it resolves from its own location, so a pass here "
          "says nothing about a sibling worktree.")
    return 0


def selftest() -> int:
    ok = True
    real_sheet, real_stub = SHEET, STUB
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        stub = tmp / "stub.md"
        stub.write_text("# clean\n")
        sheet = tmp / "sheet.md"

        globals()["STUB"] = stub
        globals()["FINDINGS"] = tmp / "findings"

        sheet.write_text("# clean\n")
        globals()["SHEET"] = sheet
        r = inherited()
        print(f"  {'PASS' if not r else 'FAIL'}  a sheet identical to the stub is accepted")
        ok &= not r

        sheet.write_text("# clean\n\n## Confirmed\n- iteration 3 established X\n")
        r = inherited()
        print(f"  {'PASS' if r else 'FAIL'}  a sheet carrying prior-run lessons is refused")
        ok &= bool(r)

        sheet.write_text("# clean\n")
        (tmp / "findings").mkdir()
        (tmp / "findings" / "iter-4.md").write_text("x")
        r = inherited()
        print(f"  {'PASS' if r else 'FAIL'}  leftover per-iteration findings are refused even with a clean sheet")
        ok &= bool(r)

        (tmp / "findings" / "iter-4.md").unlink()
        (tmp / "findings" / "README.md").write_text("standing doc")
        r = inherited()
        print(f"  {'PASS' if not r else 'FAIL'}  ...but findings/README.md is standing doc, not run state")
        ok &= not r

    globals()["SHEET"], globals()["STUB"] = real_sheet, real_stub
    print(f"\n{'4/4 passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--archive" in sys.argv:
        i = sys.argv.index("--archive")
        raise SystemExit(cmd_archive(sys.argv[i + 1] if len(sys.argv) > i + 1 else "unnamed"))
    raise SystemExit(main())
