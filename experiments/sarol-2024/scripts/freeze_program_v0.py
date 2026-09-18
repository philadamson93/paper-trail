#!/usr/bin/env python3
"""Freeze (or verify) the program-v0 manifest.

program-v0 spans two source refs -- five files from `main`, three from `sarol` -- which the
engine's single-`version_sha` materialization cannot express. Per Open Questions 6(a) of
docs/plans/papertrail-optimizer-requirements.md the two are composed into one tagged tree for
the engine, and this manifest survives as the *provenance* record: it is what proves the
composed tree is faithful to the refs the bytes actually came from.

Written 2026-09-01 when OQ8's rubric split invalidated the hand-written 7-entry manifest.
Hand-editing a file whose whole job is to carry hashes is how hashes go stale, so:

    freeze_program_v0.py --write     rewrite manifest.json from the source refs
    freeze_program_v0.py --verify    re-check every entry (exit 1 on any mismatch)
    freeze_program_v0.py --verify --tree <ref>
                                     also check every entry against a composed tree,
                                     which is the OQ6 tag's real gate
    freeze_program_v0.py --retag [<ref>]
                                     verify <ref> (default HEAD) and, only if it is a
                                     faithful composition, move the `program-v0` tag to it

⚠ **The tag is what the engine materializes from, not your working tree.** `materialize()` is
handed `rev_parse("program-v0")`, so the tag decides which program a run actually executes. Before
`--retag` existed, refreshing the manifest was one command and moving the tag was an undocumented
manual step -- so the manifest stayed current while the tag drifted. It did exactly that between
2026-09-07 and 2026-09-18, across the paper-verbatim reset, and two gates caught it
(`--verify --tree program-v0` here, which `run_hillclimb_vm.sh` blocks on, and
`materialize_smoke.py`). `--retag` exists so the fix lives next to the check.

⚠ **`--retag` does not push.** A tag that moved locally changes nothing on the VM, which fetches
it; the command prints the push line and leaves it to you, because overwriting a published tag
should be a decision rather than a side-effect.

The `sha256`/`source`/`source_refs` fields are adapter-owned extras. `ManifestEntry` does not
declare them (engine/schemas.py), so the adapter strips them before handing anything to the
engine -- splatting a raw entry into ManifestEntry raises TypeError.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "program-v0" / "manifest.json"
REPO = Path(__file__).resolve().parents[3]

# (path, source, contract_file). Order here is the logical reading order; combined_hash is
# always computed over ascending path order, per the recipe recorded in the manifest.
FILESET: list[tuple[str, str, bool]] = [
    ("src/prompts/extractor-dispatch-paperclip.md", "main", False),
    ("src/prompts/extractor-dispatch-pdf.md", "main", False),
    ("experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md", "sarol", False),
    ("src/prompts/verifier-dispatch.md", "main", False),
    ("src/specs/verdict_schema.md", "main", True),
    ("experiments/sarol-2024/specs/verdict_enum_sarol.md", "sarol", True),
    ("experiments/sarol-2024/specs/verdict_schema_sarol.md", "sarol", False),
    # Added by Plan A P0. The paper-verbatim definitions plus their provenance. Frozen
    # (contract_file=True): the rubric is the single OPERATIVE copy of the eight definitions,
    # and an editable second copy would be either inert or a silently drifting authority.
    # It is in the manifest so the reconciled text cannot be changed without cutting a version.
    ("experiments/sarol-2024/specs/verdict_definitions_sarol.md", "sarol", True),
    ("src/specs/verifier_results.md", "main", True),
    # Added 2026-09-10 (Phil's ruling, Plan A Step 7 residue). The per-claim driver. It was the
    # one component in the judge path that no version covered: it could change without the
    # program version changing, so two runs both labelled program-v0 could have had different
    # drivers with nothing detecting it -- and it is the layer that produced two observed
    # failures (an invented 4-class scheme, and hallucinated claim text).
    # contract_file=False -- EDITABLE, per Phil's standing directive that the optimizer may
    # repair this layer. ACCEPTED RISK, recorded rather than reasoned away: this file also
    # carries the measurement's integrity rules (one dispatch / no retry / never author the
    # verdict / never re-score), so an editable driver is a reward-hacking surface. The
    # invariant tests that would bound it migrated to the isolation plan and are NOT YET
    # IMPLEMENTED -- they must land before the next armed run.
    (".claude/commands/sarol-eval-item.md", "sarol", False),
]

COMBINED_HASH_RECIPE = (
    "sha256 over the concatenation, in ascending path order, of '<path>\\0<sha256>\\n' for "
    "every entry. Each entry sha256 is over the raw bytes of "
    "`git show <source_refs[entry.source].commit>:<entry.path>`."
)


def git_show(ref: str, path: str) -> bytes:
    """Raw bytes of one path at one ref. Bytes, not text -- the hash is over bytes."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"],
        capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"git show {ref}:{path} failed: {out.stderr.decode().strip()}")
    return out.stdout


def rev_parse(ref: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", ref], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot resolve ref {ref!r}: {out.stderr.strip()}")
    return out.stdout.strip()


def combined_hash(entries: list[dict]) -> str:
    h = hashlib.sha256()
    for e in sorted(entries, key=lambda e: e["path"]):
        h.update(e["path"].encode() + b"\0" + e["sha256"].encode() + b"\n")
    return h.hexdigest()


def build_entries(refs: dict[str, str]) -> list[dict]:
    entries = []
    for path, source, contract in FILESET:
        blob = git_show(refs[source], path)
        entries.append(
            {
                "path": path,
                "source": source,
                "freeze_policy": "committed",
                "contract_file": contract,
                "optional": False,
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
    return entries


def cmd_write(args) -> int:
    old = json.loads(MANIFEST.read_text())
    refs = {"main": rev_parse(args.main_ref), "sarol": rev_parse(args.sarol_ref)}
    entries = build_entries(refs)

    manifest = dict(old)
    manifest["frozen_at_utc"] = args.date
    manifest["source_refs"] = {
        "main": {
            "commit": refs["main"],
            "note": "mainline extractors + verifier + native schema/verifier contracts",
        },
        "sarol": {
            "commit": refs["sarol"],
            "note": (
                "Sarol-variant adjudicator + the enum contract and rubric guidance it was "
                "split into (OQ8 resolved 2026-09-01)"
            ),
        },
    }
    manifest["entries"] = entries
    manifest["combined_hash"] = combined_hash(entries)
    manifest["combined_hash_recipe"] = COMBINED_HASH_RECIPE

    # Key order matters only for readability; keep the original document shape.
    ordered = {}
    for k in old:
        ordered[k] = manifest[k]
    for k in manifest:
        if k not in ordered:
            ordered[k] = manifest[k]

    MANIFEST.write_text(json.dumps(ordered, indent=2) + "\n")
    n_contract = sum(1 for e in entries if e["contract_file"])
    try:
        shown = MANIFEST.relative_to(REPO)
    except ValueError:
        shown = MANIFEST  # --selftest round-trips against a copy outside the repo
    print(f"wrote {shown}")
    print(f"  entries        {len(entries)} ({n_contract} contract_file)")
    print(f"  main   @ {refs['main'][:12]}")
    print(f"  sarol  @ {refs['sarol'][:12]}")
    print(f"  combined_hash  {manifest['combined_hash']}")
    return 0


def cmd_verify(args) -> int:
    m = json.loads(MANIFEST.read_text())
    refs = {k: v["commit"] for k, v in m["source_refs"].items()}
    bad = 0

    for e in m["entries"]:
        actual = hashlib.sha256(git_show(refs[e["source"]], e["path"])).hexdigest()
        if actual != e["sha256"]:
            bad += 1
            print(f"  MISMATCH (source ref) {e['path']}")
            print(f"    manifest {e['sha256']}\n    actual   {actual}")

    recomputed = combined_hash(m["entries"])
    if recomputed != m["combined_hash"]:
        bad += 1
        print(f"  MISMATCH combined_hash\n    manifest {m['combined_hash']}\n    actual   {recomputed}")

    # The composed tree is what the engine actually materializes, so a manifest that verifies
    # against its source refs but not against the tag would still break at materialize time.
    if args.tree:
        tree = rev_parse(args.tree)
        for e in m["entries"]:
            actual = hashlib.sha256(git_show(tree, e["path"])).hexdigest()
            if actual != e["sha256"]:
                bad += 1
                print(f"  MISMATCH (composed tree {args.tree}) {e['path']}")

    n = len(m["entries"])
    if bad:
        print(f"FAIL: {bad} mismatch(es) across {n} entries")
        return 1
    scope = f"{n}/{n} vs source refs" + (f" and vs {args.tree}" if args.tree else "")
    print(f"OK: {scope}; combined_hash {m['combined_hash'][:12]} reproduces")
    return 0


#: The tag the engine materializes the program from.
PROGRAM_TAG = "program-v0"


def cmd_retag(args) -> int:
    """Move :data:`PROGRAM_TAG` to a ref, but only if that ref is a faithful composition.

    The ordering is the whole point: **verify, then move.** A `--retag` that tagged first and
    checked afterwards would let one mistyped ref publish a program nobody meant to run, and the
    gates downstream would then be arguing with a tag that is already wrong. Refusing costs a
    second; a bad tag costs a run.
    """
    target = args.retag if isinstance(args.retag, str) and args.retag else "HEAD"
    sha = rev_parse(f"{target}^{{commit}}")
    m = json.loads(MANIFEST.read_text())

    # A tag names a commit, so uncommitted edits are NOT in it. Tagging HEAD with a dirty program
    # tree produces a tag that disagrees with the files in front of you -- the same class of
    # confusion this command exists to end, arriving from the other direction.
    paths = [e["path"] for e in m["entries"]]
    dirty = subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain", "--", *paths],
        capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        print("REFUSING to move the tag: these program files have uncommitted changes, which a")
        print("tag cannot capture. Commit them first, then re-run.")
        for line in dirty.splitlines():
            print(f"    {line}")
        return 1

    print(f"Verifying {target} ({sha[:12]}) before moving {PROGRAM_TAG} ...")
    if cmd_verify(argparse.Namespace(tree=target)) != 0:
        print(f"REFUSING to move {PROGRAM_TAG}: {target} is not a faithful composition (above).")
        return 1

    was = rev_parse(f"{PROGRAM_TAG}^{{commit}}") if _tag_exists() else None
    if was == sha:
        print(f"{PROGRAM_TAG} already points at {sha[:12]}; nothing to do.")
        return 0

    message = (
        f"Move {PROGRAM_TAG} to {sha[:12]}, verified {len(m['entries'])}/{len(m['entries'])} "
        f"against the manifest's source refs and against the tree itself "
        f"(combined_hash {m['combined_hash'][:12]})"
    )
    out = subprocess.run(
        ["git", "-C", str(REPO), "tag", "-f", "-a", PROGRAM_TAG, sha, "-m", message],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(f"FAIL: could not move the tag: {out.stderr.strip()}")
        return 1

    print(f"moved {PROGRAM_TAG}: {was[:12] if was else '(new)'} -> {sha[:12]}")
    print(f"  undo:  git tag -f -a {PROGRAM_TAG} {was[:12]} -m '<why>'" if was else "")
    print(f"  ⚠ NOT on the remote yet -- the VM fetches this tag, so until you run:")
    print(f"      git push --force origin {PROGRAM_TAG}")
    print(f"    a VM run still materializes the old program.")
    return 0


def _tag_exists() -> bool:
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", f"refs/tags/{PROGRAM_TAG}"],
        capture_output=True,
    ).returncode == 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=False)
    p.add_argument("--write", action="store_true", help="rewrite manifest.json")
    p.add_argument("--verify", action="store_true", help="verify manifest.json")
    p.add_argument("--selftest", action="store_true",
                   help="round-trip a COPY and assert runtime_pins survives a re-freeze")
    p.add_argument("--tree", help="also verify every entry against this composed tree/tag")
    p.add_argument("--retag", nargs="?", const="HEAD", default=None, metavar="REF",
                   help=f"verify REF (default HEAD) and, only if faithful, move the "
                        f"program-v0 tag to it. Does not push.")
    p.add_argument("--main-ref", default="main")
    p.add_argument("--sarol-ref", default="HEAD")
    p.add_argument("--date", default="2026-09-01")
    args = p.parse_args()

    if args.write:
        return cmd_write(args)
    if getattr(args, "selftest", False):
        return cmd_selftest(args)
    if args.verify:
        return cmd_verify(args)
    if args.retag is not None:
        return cmd_retag(args)
    p.print_help()
    return 2


def cmd_selftest(args) -> int:
    """Assert the properties two gates now DEPEND on, rather than assuming them.

    `runtime_pins` is where a dependency outside the frozen fileset gets recorded -- the paperclip
    CLI today, and (proposed) the BM25 evidence producer, whose bytes decide every passage the judge
    reads while `combined_hash` stays identical. Two gates would then read pins out of this file.
    Neither gate writes it, and nothing asserted it survives a re-freeze: `cmd_write` preserves it
    only because it does `dict(old)`. A later tidy-up that rebuilt the manifest from a literal would
    silently empty the container, and every gate keyed on it would report green-by-absence.

    So this is a real round-trip against a COPY, not an inspection of the source for `dict(old)` --
    that structural form would itself break on a rename and is green-by-absence-prone in the same way.
    """
    import shutil
    import tempfile

    global MANIFEST
    real = MANIFEST
    checks: list[tuple[str, bool]] = []
    try:
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "manifest.json"
            shutil.copyfile(real, copy)
            before = json.loads(copy.read_text())
            MANIFEST = copy
            rc = cmd_write(args)
            after = json.loads(copy.read_text())

        checks.append(("the re-freeze itself succeeds against a copy", rc == 0))
        checks.append((
            "`runtime_pins` is byte-identical after a re-freeze -- the container two gates read "
            "out of this file is not emptied by rewriting it",
            after.get("runtime_pins") == before.get("runtime_pins") and bool(after.get("runtime_pins")),
        ))
        checks.append((
            "...and it is NON-EMPTY, so the assertion above cannot pass by both sides being absent",
            bool(after.get("runtime_pins")),
        ))
        checks.append((
            "`output_vocabulary` and `deliberately_excluded` survive too (same mechanism)",
            after.get("output_vocabulary") == before.get("output_vocabulary")
            and after.get("deliberately_excluded") == before.get("deliberately_excluded"),
        ))
        checks.append((
            "the re-freeze DID rewrite what it owns, so the test is not passing on a no-op",
            after.get("combined_hash_recipe") == COMBINED_HASH_RECIPE and "entries" in after,
        ))
    finally:
        MANIFEST = real

    ok = True
    for label, passed in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
    n = len(checks)
    print(f"\n{f'{n}/{n} passed' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
