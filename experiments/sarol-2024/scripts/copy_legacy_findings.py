#!/usr/bin/env python3
"""Copy the optimizer's old per-iteration findings into the engine's notes history, once (PT-B).

Before PT-B paper-trail filed each iteration's findings itself, as
``experiments/sarol-2024/optimizer/findings/iter-<n>.md`` (untracked, so only a machine that ran the
optimizer has them). The engine now files notes at ``<notes root>/<run id>/iter-<n>/findings.md`` and
mounts that folder read-only in every optimizer session. This copies the old files in under the run id
``legacy``, so the optimizer can still read them. It never overwrites, copies (never moves), and exits 0
with nothing to do.

    python3 copy_legacy_findings.py              copy, from this checkout into ~/.paper-trail
    python3 copy_legacy_findings.py --selftest   check it on a scratch folder
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
FINDINGS_DIR = HERE.parent / "optimizer" / "findings"
NOTES_ROOT = pathlib.Path.home() / ".paper-trail" / "optimizer-notes"
LEGACY_RUN_ID = "legacy"
_NAME = re.compile(r"^iter-(\d+)\.md$")


def copy_legacy(findings_dir: pathlib.Path, notes_root: pathlib.Path) -> tuple[list[str], list[str]]:
    """Copy every ``iter-<n>.md`` to ``<notes_root>/legacy/iter-<n>/findings.md``.

    Returns ``(copied, refused)``: a destination that already exists is refused, never overwritten.
    """
    copied, refused = [], []
    if not findings_dir.is_dir():
        return copied, refused
    for src in sorted(findings_dir.iterdir(), key=lambda p: p.name):
        match = _NAME.match(src.name)
        if not match or not src.is_file():
            continue
        dest = notes_root / LEGACY_RUN_ID / f"iter-{int(match.group(1))}" / "findings.md"
        if dest.exists():
            refused.append(str(dest))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied.append(f"{src.name} -> {dest}")
    return copied, refused


def _selftest() -> int:
    checks = []
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        findings, notes = root / "findings", root / "notes"
        checks.append(("nothing to copy is not an error", copy_legacy(findings, notes) == ([], [])))
        findings.mkdir()
        (findings / "iter-1.md").write_text("one\n", encoding="utf-8")
        (findings / "iter-12.md").write_text("twelve\n", encoding="utf-8")
        (findings / "README.md").write_text("not a note\n", encoding="utf-8")
        copied, refused = copy_legacy(findings, notes)
        checks += [
            ("each iter-<n>.md lands at legacy/iter-<n>/findings.md",
             (notes / "legacy" / "iter-1" / "findings.md").read_text() == "one\n"
             and (notes / "legacy" / "iter-12" / "findings.md").read_text() == "twelve\n"),
            ("...and only those (a README is not a note)", len(copied) == 2 and not refused),
            ("the originals are copied, not moved", (findings / "iter-1.md").exists()),
        ]
        (findings / "iter-1.md").write_text("changed\n", encoding="utf-8")
        copied2, refused2 = copy_legacy(findings, notes)
        checks.append(("a second run overwrites nothing and says what it refused",
                       not copied2 and len(refused2) == 2
                       and (notes / "legacy" / "iter-1" / "findings.md").read_text() == "one\n"))
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--findings-dir", type=pathlib.Path, default=FINDINGS_DIR)
    ap.add_argument("--notes-root", type=pathlib.Path, default=NOTES_ROOT)
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    copied, refused = copy_legacy(args.findings_dir, args.notes_root)
    for line in copied:
        print(f"copied   {line}")
    for line in refused:
        print(f"refused  {line} (already there; left as it was)")
    print(f"legacy findings: {len(copied)} copied, {len(refused)} already present, from {args.findings_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
