#!/usr/bin/env python3
"""Gate H -- a fresh run starts from a fresh sheet.

`meta-learnings.md` is injected into every optimizer session and is the only thing that carries
forward between iterations. That is the point *within* a run. Across runs it is contamination: a
"fresh" run opens with the previous run's hypotheses, formed against a program that may no longer
exist. Nothing in this repo ever archived or reset it -- it was reset once by hand (S6 of
`optimizer-instrument-repair.md`) while `profiles.py` reasons as though "reset between runs" were a
guaranteed property. This gate makes the sheet's lifecycle real.

🚩 **This used to call itself a stopgap awaiting a per-run git clone. OQ9 struck the clone (Phil,
2026-09-14) and this IS the fix.** The reasoning, in one line: the defect is *sequential* residue
between runs, a clone buys *concurrent-namespace* isolation paper-trail will never need, and the
reset is the part that does the work. So this gate is not retired — it is the mechanism, and the VM
runner now calls it twice per run: `--archive <run-id>` to move the state out, then bare to assert
the tree is actually clean. A reset with no assertion after it is an inert mechanism.

⚠ **One thing the clone would have given free is still open: the `program-v*` tag namespace.** Tags
are repo-global whether or not there is a clone, so a ledger recut still rewrites shared identity.
The plan's recommendation is to stop treating tags as version identity and key on the manifest's
`combined_hash`, which is committed and is already what the configuration pin covers. Not decided
here.

⚠ **The list is derived from what carries state from one measurement to the next, and is never
appended to when something is noticed.** It used to be derived from *what the optimizer reads*,
and that is precisely why the graders' answers were missed: they are read by the GRADER, not by
the optimizer, so the old question could not see them. Re-derived 2026-09-21 from the better
question. A fifth class appearing later means the derivation is wrong again, not that the list
grew.

⚠ **Two lifetimes, not one longer list.** The sheet, the findings and the releases are *meant* to
carry between iterations inside a run -- that is their purpose -- and must not cross a RUN. The
graders' answers must not cross an ITERATION at all. So `CARRIED` below states a lifetime per
class rather than naming one reset cadence for everything.

    check_run_scope.py                 assert this checkout is ready for a FRESH run
    check_run_scope.py --archive <id>  file the sheet, findings and iter/ away, then reset
    check_run_scope.py --selftest      negative controls, including "what if the archive is skipped"

Override for a deliberate continuation run: `SAROL_ALLOW_INHERITED_LESSONS=1` (same convention as
`SAROL_ALLOW_ENGINE_DIVERGENCE`). It is loud on purpose -- a continuation run's numbers are not
comparable to a fresh one's.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
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
#: The optimizer's per-iteration releases. Run state living in the shared checkout: `iter/<n>/`
#: is written by run N and read by nothing that should outlive it, and the VM runner's own closing
#: line admits the boundary stops here -- *"Results under $RUNS; releases under $REPO_ROOT/iter/."*
ITER = REPO / "iter"
#: ⚠ **Kept at `runs/_archive/<ts>-<run_id>`, not the `runs/<run_id>/_archive/` the plan's Phase 4
#: table names.** The plan contradicts itself -- its own OQ8 paragraph cites this path -- and
#: archives already exist here. Moving them would orphan the only copy of the earlier sheets, which
#: is the precise thing this script exists to prevent.
ARCHIVE_ROOT = Path.home() / ".paper-trail" / "runs" / "_archive"
OVERRIDE = "SAROL_ALLOW_INHERITED_LESSONS"


@dataclasses.dataclass(frozen=True)
class Carried:
    """One class of state that outlives whatever wrote it unless something clears it.

    ``crosses_iteration`` and ``crosses_run`` are the LIFETIME -- what this class is *allowed* to
    survive, which is the property the gates enforce, not a description of what currently happens.
    """

    name: str
    read_by: str
    crosses_iteration: bool
    crosses_run: bool
    archived_to: str


#: ⚠ **Four explicit classes, not a reusable lifecycle framework.** This is a single-purpose gate.
#: The declaration exists so that the next class is added at a boundary someone has to think about
#: -- "what is its lifetime, and where does it get archived?" -- rather than so a general state
#: manager exists. The first three keep exactly the behaviour they had; the fourth is the one the
#: old derivation could not see.
CARRIED: "tuple[Carried, ...]" = (
    Carried(
        name="optimizer/meta-learnings.md",
        read_by="the optimizer -- injected into every one of its sessions",
        crosses_iteration=True,   # that is its purpose: lessons accumulate within a run
        crosses_run=False,
        archived_to="<run archive>/meta-learnings.md",
    ),
    Carried(
        name="optimizer/findings/iter-*.md",
        read_by="the optimizer -- its own per-iteration write-ups, read like the sheet",
        crosses_iteration=True,
        crosses_run=False,
        archived_to="<run archive>/iter-<n>.md",
    ),
    Carried(
        name="iter/<n>/",
        read_by="the VM runner, which reads `iter/<n>/release_val.json` back at the end",
        crosses_iteration=True,   # keyed by iteration number, so run N+1 overwrites run N
        crosses_run=False,
        archived_to="<run archive>/iter-<n>/",
    ),
    Carried(
        name="<staging>/ledger/claims/*.json",
        read_by="the GRADER -- which is why the old derivation, keyed on the optimizer, missed it",
        #: The only class with a per-ITERATION lifetime. An answer that survives into the next pass
        #: is not merely stale: the grader is told to read the file first, so it reads the previous
        #: verdict and is talked out of its own -- and its attempt to save over it is auto-denied
        #: headless, so the previous answer is what gets scored.
        crosses_iteration=False,
        crosses_run=False,
        archived_to="<run archive>/iter-<n>/<split>/answers/",
    ),
)


def _safe(segment: str) -> str:
    """One path segment, never a traversal.

    Both values that reach this come from outside the module -- the engine's materialized
    directory name and the split string -- and a ``..`` in either would put the archive somewhere
    other than the archive.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", segment).strip(".")
    return cleaned or "unnamed"


def run_archive_dir(run_id: str, *, create: bool = True) -> Path:
    """The ONE archive folder for ``run_id``, reused by every call within that run.

    ⚠ **Reused, not re-timestamped on each call.** ``cmd_archive`` runs once at run start and the
    per-iteration answer sweep runs three times per iteration after it. Minting a fresh
    ``<ts>-<run_id>`` each time would scatter one run's record across a dozen sibling folders,
    which is the opposite of what the layout is for. The timestamp is chosen once, by whichever
    call lands first.

    This is also the single builder of the path. The answers compose *onto* what this returns
    rather than assembling ``_archive/<ts>-<run>`` a second time somewhere else -- two builders of
    one path is how the two drift.
    """
    existing = sorted(p for p in ARCHIVE_ROOT.glob(f"*-{run_id}") if p.is_dir())
    if existing:
        return existing[-1]
    dest = ARCHIVE_ROOT / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{run_id}"
    if create:
        dest.mkdir(parents=True, exist_ok=True)
    return dest


#: The engine names its materialized trees ``iter<n>-current`` (loop.py:370) and ``iter<n>-<tag>``
#: (loop.py:469). Both levels of the answer archive are derived from that name plus the split.
_ITER_DIR = re.compile(r"^iter(\d+)-(.+)$")


def answer_segments(iter_name: str, split: str) -> "tuple[str, str]":
    """Where one Runner call's answers are filed: ``(iter-<n>, <split>)``.

    The engine makes THREE Runner calls per iteration and none of them may collide::

        train, `iter1-current`  ->  ("iter-1", "train")
        val,   `iter1-current`  ->  ("iter-1", "val")
        val,   `iter1-v5`       ->  ("iter-1", "val-v5")   <- the post-commit probe

    ⚠ **The second level is load-bearing.** Without it the post-commit probe overwrites
    validation's answers *inside the archive* -- the same defect this file exists to fix, one
    directory up. Both levels come from the two values the adapter already uses to place run
    manifests and traces, so nothing new has to be threaded through to get here.

    A name the engine did not produce (a canary pin, a smoke, a hand-driven dispatch) keeps its own
    name as the first level, so two of those cannot collide either.
    """
    m = _ITER_DIR.match(iter_name)
    if not m:
        return _safe(iter_name), _safe(split)
    n, suffix = m.group(1), m.group(2)
    if suffix == "current":
        return f"iter-{n}", _safe(split)
    return f"iter-{n}", f"{_safe(split)}-{_safe(suffix)}"


def archive_and_clear_answers(
    staging_dirs: "list[Path] | tuple[Path, ...]",
    *,
    run_id: str,
    iter_name: str,
    split: str,
) -> "dict[str, list[str]]":
    """Move every live grader answer out of the way before a pass dispatches. The per-iteration
    entry point -- the fourth class in :data:`CARRIED`, and the only one with this lifetime.

    Archive, never delete (Phil, 2026-09-21). The answers land under
    ``_archive/<ts>-<run-id>/iter-<n>/<split>/answers/`` and the live ``ledger/claims/`` slots come
    back empty. That emptiness is the whole fix: a grader whose answer file does not exist CREATES
    one, which the narrow ``Write`` grant already allows, while a grader facing a populated slot
    has to OVERWRITE, which is auto-denied in a headless session -- so the previous pass's answer
    stays on disk and gets scored instead of this one's.

    Returns ``{"archived": [...], "remaining": [...]}``. ``remaining`` is non-empty only when a
    move silently failed, and the caller refuses the batch on it: an archive that moved nothing
    looks exactly like a clean tree from the outside, which is the inert-mechanism failure this
    file already guards against once.
    """
    iter_seg, split_seg = answer_segments(iter_name, split)
    dest = run_archive_dir(run_id) / iter_seg / split_seg / "answers"
    archived: "list[str]" = []
    remaining: "list[str]" = []
    for staging in sorted({Path(s).resolve() for s in staging_dirs}):
        slot = staging / "ledger" / "claims"
        if not slot.is_dir():
            continue
        for answer in sorted(slot.glob("*.json")):
            dest.mkdir(parents=True, exist_ok=True)
            target = dest / answer.name
            if target.exists():
                # Two staging roots can hold the same `<claim_id>.json` -- the canary is staged
                # under the repo while the batch is staged under the run's output root, and the
                # canary claim is drawn from train like the rest. Disambiguate on the staging path
                # rather than archiving one on top of the other.
                tag = hashlib.sha256(str(staging).encode("utf-8")).hexdigest()[:8]
                target = dest / f"{answer.stem}--{tag}.json"
            shutil.move(str(answer), target)
            archived.append(str(target))
        remaining.extend(str(q) for q in sorted(slot.glob("*.json")))
    return {"archived": archived, "remaining": remaining}


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
    releases = sorted(p.name for p in ITER.glob("*") if p.is_dir()) if ITER.exists() else []
    if releases:
        problems.append(
            f"{_rel(ITER)} still holds a previous run's per-iteration releases: "
            f"{', '.join(releases)}. They are keyed by iteration number, not by run, so run N+1's "
            f"iteration 1 overwrites run N's -- and `iter/<n>/release_val.json` is what the runner "
            "reads back at the end, so the two runs' results become indistinguishable on disk."
        )
    return problems


def cmd_archive(run_id: str) -> int:
    # The same builder the per-iteration answer sweep uses, so one run's start-up sweep and its
    # per-pass answer archives land in the SAME folder rather than two conventions side by side.
    dest = run_archive_dir(run_id)
    moved = []
    if SHEET.exists() and STUB.exists() and _sha(SHEET) != _sha(STUB):
        shutil.copy2(SHEET, dest / "meta-learnings.md")
        moved.append("meta-learnings.md")
    if FINDINGS.exists():
        for p in sorted(FINDINGS.glob("iter-*.md")):
            shutil.move(str(p), dest / p.name)
            moved.append(f"findings/{p.name}")
    if ITER.exists():
        for d in sorted(q for q in ITER.glob("*") if q.is_dir()):
            shutil.move(str(d), dest / f"iter-{d.name}")
            moved.append(f"iter/{d.name}")
    if STUB.exists():
        shutil.copyfile(STUB, SHEET)
    if not moved:
        # Only if it is genuinely empty. Once the answer sweep writes into this same folder,
        # a bare `rmdir()` here would raise on a resumed run instead of reporting a clean sheet.
        if not any(dest.iterdir()):
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
    real_iter, real_archive, real_findings = ITER, ARCHIVE_ROOT, FINDINGS
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        stub = tmp / "stub.md"
        stub.write_text("# clean\n")
        sheet = tmp / "sheet.md"

        globals()["STUB"] = stub
        globals()["FINDINGS"] = tmp / "findings"
        # ⚠ `ITER` and `ARCHIVE_ROOT` must be redirected too. Without this the `iter/` branch below
        # points at the real checkout, which has no `iter/`, so every assertion about it passes
        # because there is nothing there -- green by absence, on the one branch being added.
        globals()["ITER"] = tmp / "iter"
        globals()["ARCHIVE_ROOT"] = tmp / "_archive"

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

        # -- `iter/`, the third thing the reset owns (Phase 4) --------------------------------
        (tmp / "iter" / "1").mkdir(parents=True)
        (tmp / "iter" / "1" / "release_val.json").write_text("{}")
        r = inherited()
        print(f"  {'PASS' if r else 'FAIL'}  a previous run's iter/<n> releases are refused, since "
              f"run N+1 writes the same iteration numbers over them")
        ok &= bool(r)

        # -- the archive actually clears all three, and a second run id sees a clean tree -----
        sheet.write_text("# clean\n\n## Confirmed\n- run A learned X\n")
        (tmp / "findings" / "iter-4.md").write_text("run A finding")
        rc = cmd_archive("run-A")
        after_first = inherited()
        print(f"  {'PASS' if rc == 0 and not after_first else 'FAIL'}  archiving under one run id "
              f"leaves the tree clean for the next")
        ok &= rc == 0 and not after_first

        archived = sorted(q.name for d in (tmp / "_archive").glob("*") for q in d.glob("*"))
        print(f"  {'PASS' if set(archived) >= {'meta-learnings.md', 'iter-4.md', 'iter-1'} else 'FAIL'}"
              f"  ...and all three kinds are IN the archive, not deleted: {archived}")
        ok &= set(archived) >= {"meta-learnings.md", "iter-4.md", "iter-1"}

        # A second consecutive run id, with nothing new: still clean, and idempotent.
        rc2 = cmd_archive("run-B")
        after_second = inherited()
        print(f"  {'PASS' if rc2 == 0 and not after_second else 'FAIL'}  ...and a second consecutive "
              f"run id finds it clean, so the reset is idempotent")
        ok &= rc2 == 0 and not after_second

        # The negative control the plan names: SKIP the archive and the assertion must FAIL.
        # A reset with no control for "what if it did not run" is the inert-mechanism pattern.
        sheet.write_text("# clean\n\n## Confirmed\n- run B learned Y\n")
        (tmp / "iter" / "2").mkdir(parents=True)
        skipped = inherited()
        print(f"  {'PASS' if len(skipped) >= 2 else 'FAIL'}  skipping the archive is caught, naming "
              f"every item that was not reset ({len(skipped)} of them)")
        ok &= len(skipped) >= 2

        # =====================================================================================
        # The fourth carried class: the graders' answers, whose lifetime is ONE ITERATION.
        # =====================================================================================
        def _answer(staging: Path, claim_id: str, run_id: str) -> Path:
            slot = staging / "ledger" / "claims"
            slot.mkdir(parents=True, exist_ok=True)
            f = slot / f"{claim_id}.json"
            f.write_text(f'{{"claim_id": "{claim_id}", "run_id": "{run_id}"}}', encoding="utf-8")
            return f

        # -- the two lifetimes, asserted in BOTH directions -----------------------------------
        # A mechanism that cleared everything always would pass a one-sided test, so each class is
        # checked for what it must SURVIVE as well as what must clear it.
        sheet.write_text("# clean\n\n## Confirmed\n- run C learned Z\n")
        (tmp / "findings" / "iter-7.md").write_text("run C finding")
        s1 = tmp / "staging" / "C1"
        a1 = _answer(s1, "C1", "prev-pass")

        archive_and_clear_answers([s1], run_id="run-C", iter_name="iter1-current", split="train")
        survived_iteration = (
            sheet.read_text() != stub.read_text() and (tmp / "findings" / "iter-7.md").exists()
        )
        print(f"  {'PASS' if survived_iteration else 'FAIL'}  the per-RUN classes (the sheet, the "
              f"findings) survive an ITERATION boundary -- carrying them is their purpose")
        ok &= survived_iteration

        cleared_by_iteration = not a1.exists()
        print(f"  {'PASS' if cleared_by_iteration else 'FAIL'}  ...while the per-ITERATION class "
              f"(a grader's answer) does not survive one")
        ok &= cleared_by_iteration

        rc3 = cmd_archive("run-C")
        crossed_run = inherited()
        print(f"  {'PASS' if rc3 == 0 and not crossed_run else 'FAIL'}  ...and the per-RUN classes "
              f"do not survive a RUN boundary either, so neither class crosses a run")
        ok &= rc3 == 0 and not crossed_run

        # -- the declaration is not decorative -------------------------------------------------
        # `CARRIED` states a lifetime per class. If nothing checks the table against what the code
        # does, it is a comment that can drift silently -- which is how the answers were missed.
        answers_class = [c for c in CARRIED if "ledger/claims" in c.name]
        declared = (
            len(CARRIED) == 4
            and len(answers_class) == 1
            and answers_class[0].crosses_iteration is False
            and all(c.crosses_run is False for c in CARRIED)
            and [c.crosses_iteration for c in CARRIED] == [True, True, True, False]
        )
        print(f"  {'PASS' if declared else 'FAIL'}  the declared lifetimes match the behaviour "
              f"above: three per-run classes, one per-iteration, none crossing a run")
        ok &= declared

        # -- the archive HAS it, and the clear left nothing ------------------------------------
        # Two different bugs: an archive that silently moved nothing, and a clear that deleted
        # without archiving. Checking one hides the other.
        archived_answers = sorted((tmp / "_archive").rglob("answers/*.json"))
        kept = (
            len(archived_answers) == 1
            and "prev-pass" in archived_answers[0].read_text()
            and archived_answers[0].parent.parent.name == "train"
            and archived_answers[0].parent.parent.parent.name == "iter-1"
        )
        print(f"  {'PASS' if kept else 'FAIL'}  the cleared answer is IN the archive under "
              f"iter-1/train/answers/, with its old run id intact -- moved, never deleted")
        ok &= kept

        # -- the three gradings of one iteration must not collide ------------------------------
        # Without the `<split>` level the post-commit probe overwrites validation's answers INSIDE
        # the archive, reintroducing this exact defect one directory up.
        for call_ns, split_name, claim in (
            ("iter2-current", "train", "T1"),
            ("iter2-current", "val", "V1"),
            ("iter2-v5", "val", "V1"),
        ):
            st = tmp / "staging" / f"{split_name}-{call_ns}"
            _answer(st, claim, f"pass-{split_name}-{call_ns}")
            archive_and_clear_answers(
                [st], run_id="run-C", iter_name=call_ns, split=split_name
            )
        iter2 = run_archive_dir("run-C", create=False) / "iter-2"
        splits = sorted(q.name for q in iter2.glob("*") if q.is_dir())
        three = splits == ["train", "val", "val-v5"] and all(
            len(list((iter2 / q / "answers").glob("*.json"))) == 1 for q in splits
        )
        print(f"  {'PASS' if three else 'FAIL'}  one iteration's THREE gradings land in three "
              f"distinct folders, so the probe cannot overwrite validation: {splits}")
        ok &= three

        # -- negative control: skip the sweep and the slot is still populated -------------------
        # A clear with no control for "what if it did not run" proves nothing about the clear.
        s_skip = tmp / "staging" / "SKIPPED"
        a_skip = _answer(s_skip, "S1", "prev-pass")
        not_swept = a_skip.exists()
        print(f"  {'PASS' if not_swept else 'FAIL'}  ...and a staging dir that was NOT swept still "
              f"holds its old answer, so the checks above are not passing by absence")
        ok &= not_swept

        # -- one folder per run, not one per call ------------------------------------------------
        same_folder = run_archive_dir("run-C", create=False) == run_archive_dir("run-C", create=False)
        run_folders = [q for q in (tmp / "_archive").glob("*-run-C") if q.is_dir()]
        print(f"  {'PASS' if same_folder and len(run_folders) == 1 else 'FAIL'}  every call within "
              f"one run archives into the SAME folder, not a fresh timestamp each time "
              f"({len(run_folders)} folder(s) for run-C)")
        ok &= same_folder and len(run_folders) == 1

        # -- the path derivation, directly --------------------------------------------------------
        segs = (
            answer_segments("iter1-current", "train") == ("iter-1", "train")
            and answer_segments("iter1-current", "val") == ("iter-1", "val")
            and answer_segments("iter1-v5", "val") == ("iter-1", "val-v5")
            and answer_segments("iter12-v7", "val") == ("iter-12", "val-v7")
        )
        print(f"  {'PASS' if segs else 'FAIL'}  the engine's own directory names "
              f"(iter<n>-current, iter<n>-<tag>) map to the three archive destinations")
        ok &= segs

        # The property is "the result stays inside the archive", not "the string looks tidy" --
        # `_.._etc` contains dots and is perfectly safe. Checked by joining, which is what the
        # code actually does with these two values.
        probe_root = (tmp / "_probe").resolve()
        traversal = answer_segments("../../etc", "../x")
        landed = (probe_root / traversal[0] / traversal[1]).resolve()
        raw = (probe_root / "../../etc" / "../x").resolve()
        safe = landed.is_relative_to(probe_root) and not raw.is_relative_to(probe_root)
        print(f"  {'PASS' if safe else 'FAIL'}  ...and a traversal in either value stays inside "
              f"the archive, where the raw strings would have escaped it: {traversal}")
        ok &= safe

    globals()["SHEET"], globals()["STUB"] = real_sheet, real_stub
    globals()["ITER"], globals()["ARCHIVE_ROOT"] = real_iter, real_archive
    globals()["FINDINGS"] = real_findings
    print(f"\n{'19/19 passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--archive" in sys.argv:
        i = sys.argv.index("--archive")
        raise SystemExit(cmd_archive(sys.argv[i + 1] if len(sys.argv) > i + 1 else "unnamed"))
    raise SystemExit(main())
