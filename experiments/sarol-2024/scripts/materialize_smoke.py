#!/usr/bin/env python3
"""Materialization smoke: prove the composed program-v0 tree actually feeds the engine.

The manifest self-check (`freeze_program_v0.py --verify`) proves the recorded hashes match the
source refs. That is necessary but NOT sufficient, because it never touches the engine: it
verifies *provenance*, not *materializability*. This script closes that gap, and covers the
verification row the plan calls "Materialization smoke".

Two things are asserted, both of which the plan predicted and neither of which the engine will
tell you about until it breaks:

1. **The manifest's adapter-owned extras must be stripped.** `ManifestEntry` declares only
   path / freeze_policy / content_hash / archive_ref / contract_file / optional. Our manifest
   entries additionally carry `source` and `sha256` (we need two source refs; the engine models
   one). Splatting a raw entry raises TypeError -- asserted here so nobody "simplifies" the
   adapter's strip step away later.
2. **materialize() writes all 8 files from the single tag SHA**, and every file's bytes hash to
   what the manifest recorded -- i.e. the composed tree is faithful.

Usage:  materialize_smoke.py [--tree program-v0] [--engine <path to agentic-label-opt>]
Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = Path(__file__).resolve().parents[1] / "program-v0" / "manifest.json"
DEFAULT_ENGINE = Path.home() / "Documents" / "Misc" / "Projects" / "agentic-label-opt"

# The only fields engine.schemas.ManifestEntry declares that our manifest also carries.
ENGINE_FIELDS = {"path", "freeze_policy", "contract_file", "optional"}


def rev_parse(ref: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot resolve {ref!r}: {out.stderr.strip()}")
    return out.stdout.strip()


def force_rmtree(path: Path) -> None:
    """materialize() chmods the tree read-only, directories included."""
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            try:
                os.chmod(Path(root) / name, stat.S_IRWXU)
            except OSError:
                pass
    os.chmod(path, stat.S_IRWXU)
    shutil.rmtree(path, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", default="program-v0")
    ap.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    args = ap.parse_args()

    if not (args.engine / "engine" / "materialize.py").exists():
        print(f"SKIP: engine not found at {args.engine}")
        return 1
    sys.path.insert(0, str(args.engine))
    from engine.materialize import materialize
    from engine.schemas import ManifestEntry, ProgramManifest

    raw = json.loads(MANIFEST.read_text())
    entries = raw["entries"]
    failures: list[str] = []

    # --- 1. the extras really are rejected by the engine's dataclass ------------------------
    try:
        ManifestEntry(**entries[0])
    except TypeError as e:
        print(f"OK  splatting a raw entry raises TypeError as designed\n      ({e})")
    else:
        failures.append(
            "ManifestEntry accepted a raw manifest entry -- the engine's schema gained the "
            "adapter-owned extras, so the adapter's strip step needs revisiting"
        )

    # --- 2. strip to the declared fields, exactly as the adapter must -----------------------
    stripped = [ManifestEntry(**{k: v for k, v in e.items() if k in ENGINE_FIELDS}) for e in entries]
    manifest = ProgramManifest(entries=tuple(stripped), combined_hash=raw["combined_hash"])
    print(f"OK  built ProgramManifest from {len(stripped)} stripped entries")

    # --- 3. materialize from the single composed SHA ---------------------------------------
    sha = rev_parse(args.tree)
    dest = Path(tempfile.mkdtemp(prefix="program-v0-smoke-"))
    try:
        materialize(manifest, sha, repo_root=REPO, dest=dest)
        written = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
        print(f"OK  materialize({args.tree} @ {sha[:12]}) wrote {len(written)} files")

        expected = {e["path"] for e in entries}
        missing = expected - set(written)
        extra = set(written) - expected
        if missing:
            failures.append(f"materialize did not write: {sorted(missing)}")
        if extra:
            failures.append(f"materialize wrote unexpected paths: {sorted(extra)}")

        # --- 4. the materialized bytes hash to what the manifest froze ----------------------
        for e in entries:
            f = dest / e["path"]
            if not f.exists():
                continue
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
            if actual != e["sha256"]:
                failures.append(
                    f"materialized content differs from the freeze: {e['path']}\n"
                    f"       manifest {e['sha256']}\n       actual   {actual}"
                )
        if not failures:
            print(f"OK  all {len(entries)} materialized files hash to their frozen sha256")
    finally:
        force_rmtree(dest)

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASS: program-v0 materializes from one version_sha and is byte-faithful to the freeze")
    return 0


if __name__ == "__main__":
    sys.exit(main())
