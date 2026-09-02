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
    ("src/specs/verifier_results.md", "main", True),
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
    print(f"wrote {MANIFEST.relative_to(REPO)}")
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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=False)
    p.add_argument("--write", action="store_true", help="rewrite manifest.json")
    p.add_argument("--verify", action="store_true", help="verify manifest.json")
    p.add_argument("--tree", help="also verify every entry against this composed tree/tag")
    p.add_argument("--main-ref", default="main")
    p.add_argument("--sarol-ref", default="HEAD")
    p.add_argument("--date", default="2026-09-01")
    args = p.parse_args()

    if args.write:
        return cmd_write(args)
    if args.verify:
        return cmd_verify(args)
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
