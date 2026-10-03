"""Score a frozen program (default: the version the manifest freezes) on a VAL subsample.

This is deliberately NOT the optimizer loop. It answers one question: what does the frozen
starting-point program actually score against Sarol, where no real number existed before. No
program edits, no frontier, no iterations — materialize the freeze, dispatch the judge, score.

**Sizing.** `--n` draws from the split's stageable pool via `optimizer/sampling.py`, so the draw is
seeded, recorded, and reproducible. The full dev pool is 255 (not 316: a row with no evidence
annotation on its cited bucket has no gold label to score against — see `sampling.py`'s docstring).
At the measured ~$1.00/session a full-pool baseline is ~$255 and ~7 hours, so `--n` exists to buy a
real number sooner.

⚠ **A small `--n` is not comparable to the published baselines.** `IRRELEVANT` is ~1.8% of gold, so
a 25-claim draw is expected to contain zero of them; macro-F1 over three classes then divides by
three while one class is structurally absent, which drags it down for a reason that has nothing to
do with the program. Read `micro_f1` and `per_class_f1` at small `n`, and only quote 3-way macro-F1
against MultiVerS 0.52 / GPT-4 0.45 from a full-pool run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
_OPT = _HERE.parent / "optimizer"
for _p in (str(_OPT), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import adapter  # noqa: E402
import profiles as profiles_mod  # noqa: E402
import sampling  # noqa: E402

ENGINE_FIELDS = {"path", "freeze_policy", "contract_file", "optional"}


def _clear(dest: pathlib.Path) -> None:
    """`materialize()` chmods the tree read-only, the dest root included."""
    if not dest.exists():
        return
    os.chmod(dest, 0o755)
    for root, dirs, files in os.walk(dest):
        for name in dirs + files:
            os.chmod(pathlib.Path(root) / name, 0o755)
    shutil.rmtree(dest)


def resolve_program_tag(requested: str | None, store) -> str:
    """The tag to score: the one asked for, else the version the manifest freezes."""
    return requested or store.program_version


def _selftest() -> int:
    import subprocess as sp  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    class _Store:
        program_version = "program-v11"

    checks = [
        ("with no --program-tag the baseline scores the version the manifest freezes",
         resolve_program_tag(None, _Store()) == "program-v11"),
        ("...and an explicit tag wins", resolve_program_tag("program-v10", _Store()) == "program-v10"),
        ("...and the real manifest names a version", bool(adapter.SarolProgramStore().program_version)),
    ]
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": td, "GIT_CONFIG_NOSYSTEM": "1"}
        for cmd in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.invalid"],
                    ["config", "user.name", "t"], ["commit", "-q", "--allow-empty", "-m", "v"],
                    ["tag", "-a", "program-vT", "-m", "annotated"]):
            sp.run(["git", "-C", td, *cmd], check=True, capture_output=True, env=env)
        commit = sp.run(["git", "-C", td, "rev-parse", "HEAD"], capture_output=True, text=True, env=env).stdout.strip()
        checks.append(("an annotated tag resolves to its COMMIT, not the tag object",
                       _tag_sha(repo, "program-vT") == commit))
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", default="dev", choices=("train", "dev"))
    ap.add_argument("--n", type=int, required=True, help="claims to draw (see the size caveat)")
    ap.add_argument("--profile", default="retrieval", choices=sorted(profiles_mod.PROFILES))
    ap.add_argument("--out-root", required=True, help="where staging, batch and outputs land")
    ap.add_argument("--run-id", default="baseline")
    ap.add_argument(
        "--program-tag",
        default=None,
        help="which frozen program to score. Default: the version the manifest freezes (program-v11 since "
             "PT-A); pass an earlier tag (e.g. program-v10) to re-score a historical program.",
    )
    ap.add_argument(
        "--image",
        default=None,
        help=(
            "the grader image by digest (name:version@sha256:...). Default: the locally built "
            "paper-trail-isolation image. There is no uncontained mode: this script produces the "
            "baseline every later iteration is compared against, through the same engine runner."
        ),
    )
    ap.add_argument("--max-workers", type=int, default=1, help="claims run at once (wall-clock only)")
    ap.add_argument("--per-call-max-budget-usd", type=float, default=2.0)
    ap.add_argument("--per-call-timeout-seconds", type=float, default=900.0)
    args = ap.parse_args(argv)

    out_root = pathlib.Path(args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    profile = profiles_mod.get(args.profile)
    blocked = profiles_mod.unrunnable_reason(args.profile)
    if blocked:
        print(f"REFUSED  {blocked}", file=sys.stderr)
        return 2

    # -- draw + stage ----------------------------------------------------------------------------
    pool = sampling.claim_pool(args.split)
    print(f"pool({args.split}) = {len(pool)} stageable claims")
    units = sampling.resolve_batch(
        0,
        n=args.n,
        mode="fresh",
        split=args.split,
        history_path=out_root / "draw_history.json",
        pool=pool,
    )
    batch = sampling.stage_batch(
        units,
        split=args.split,
        staging_root=out_root / "staging",
        batch_path=out_root / f"{args.run_id}-batch.json",
    )
    print(f"drew and staged {len(units)} claims -> {batch}")

    # -- materialize the freeze ------------------------------------------------------------------
    # Puts the engine on sys.path (and fails with the adapter's own message if it is absent).
    adapter._import_engine()
    from engine.materialize import materialize  # noqa: PLC0415
    from engine.schemas import ManifestEntry, ProgramManifest, RunInputs  # noqa: PLC0415

    store = adapter.SarolProgramStore()
    stripped = [
        ManifestEntry(**{k: v for k, v in e.items() if k in ENGINE_FIELDS})
        for e in store.raw["entries"]
    ]
    manifest = ProgramManifest(entries=tuple(stripped), combined_hash=store.raw["combined_hash"])
    args.program_tag = resolve_program_tag(args.program_tag, store)
    sha = _tag_sha(store.repo_root, args.program_tag)
    # One folder per tag under the materialize root: the engine runner keys a pass on the
    # materialized folder's name and refuses an output root inside the materialize root.
    materialize_root = out_root / "materialized"
    dest = materialize_root / args.program_tag
    _clear(dest)
    materialize(manifest, sha, repo_root=store.repo_root, dest=dest)
    written = sorted(p for p in dest.rglob("*") if p.is_file())
    print(f"materialized {len(written)} files from {args.program_tag} @ {sha[:12]}")

    # -- run -------------------------------------------------------------------------------------
    # Through the engine's runner (PT-A), as a run's graders are: one sealed session per claim, the
    # materialized program read-only, each claim's own folder writable, under the program's committed
    # setup pin. Scored as VAL regardless of the split it was drawn from: a held-out measurement of
    # the freeze, so nothing here writes a TRAIN mistake corpus.
    import sarol_program  # noqa: PLC0415 -- needs the engine on the path

    pins = sarol_program.committed_pins(store.repo_root)
    if not pins.get("program"):
        print("REFUSED  no program setup pin is committed for this platform "
              f"({sarol_program.platform_key()}); run sarol_program.py --print-pins and commit it",
              file=sys.stderr)
        return 2
    program = sarol_program.SarolProgram(
        profile=profile, model=adapter.DEFAULT_JUDGE_MODEL,
        per_call_timeout_seconds=int(args.per_call_timeout_seconds),
        per_call_max_budget_usd=args.per_call_max_budget_usd, max_concurrent=args.max_workers,
    )
    engine_runner = sarol_program.program_runner(
        program, output_root=out_root / "program-out", materialize_root=materialize_root,
        image=args.image or sarol_program.grader_image(), transcript_dir=out_root / "program-out" / "transcripts",
        expected_fingerprint=pins["program"], forbidden=sarol_program.forbidden_list(repo_root=store.repo_root),
    )
    inputs = RunInputs(input_ref=str(batch), batch_id=f"{args.run_id}", split="val")

    started = time.time()
    with engine_runner as pr:
        arts = pr.as_runner(run_id=args.run_id).run(dest, inputs)
    elapsed = time.time() - started

    print(f"\nstatus={arts.status}  sessions={arts.sub_invocation_count}  "
          f"cost=${arts.cost_usd:.2f}  elapsed={elapsed / 60:.1f}min")
    if arts.error:
        print(f"error: {arts.error.code} | {arts.error.message_redacted[:400]}")

    # -- score -----------------------------------------------------------------------------------
    scored_arts = arts
    score = adapter.SarolScorer().score(scored_arts, "val", {"_split": "val", "_iter": 0})
    manifest_path = arts.artifact_refs[0].path if arts.artifact_refs else None

    print("\n=== BASELINE ===")
    print(f"primary ({score.primary_metric.name}): {score.primary_metric.value:.4f}")
    for key in ("micro_f1", "macro_f1_9way", "n_scored", "n_total", "n_invalid",
                "n_unresolved", "scored"):
        if key in score.breakdown:
            print(f"  {key}: {score.breakdown[key]}")
    print(f"  per_class_f1: {score.breakdown.get('per_class_f1')}")
    print(f"  confusion   : {score.breakdown.get('confusion_matrix')}")

    summary = {
        "run_id": args.run_id,
        "split": args.split,
        "n_requested": args.n,
        "profile": profile.name,
        "retrieval_k": profile.retrieval_k,
        "program_tag": args.program_tag,
        "program_sha": sha,
        "status": arts.status,
        "sessions": arts.sub_invocation_count,
        "cost_usd": arts.cost_usd,
        "elapsed_seconds": round(elapsed, 1),
        "run_manifest": manifest_path,
        "primary_metric": score.primary_metric.value,
        "breakdown": score.breakdown,
    }
    (out_root / f"{args.run_id}-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {out_root / f'{args.run_id}-summary.json'}")
    return 0


def _tag_sha(repo_root: pathlib.Path, tag: str = "program-v0") -> str:
    """Resolve a program tag to its COMMIT, matching `materialize_smoke.py`'s convention.

    `program-v0` is an annotated tag, so a bare `rev-parse` returns the tag OBJECT sha — a
    different id for the same program, which would make one run look like two systems.
    """
    import subprocess

    return subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", f"{tag}^{{commit}}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
