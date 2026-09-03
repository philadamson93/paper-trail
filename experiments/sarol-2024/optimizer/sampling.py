"""Growing-batch sampling for the Sarol consumer: draw a batch per iteration, stage it, price it.

This is paper-trail's analog of crc-extraction-agent's `agent/optimizer/split.py` §6 (see
`resolve_train_batch` there). Same three draw modes, same per-iteration draw-history bookkeeping,
same seeded determinism, and the same engine seam: `agentic-label-opt`'s
``run_loop(train_inputs=Callable[[int], RunInputs])`` accepts a *factory*, so TRAIN can grow across
iterations without the consumer re-entering the loop.

**Why this exists, and why it is not only about TRAIN.** Phil's ask was a graduated `N` over the
TRAIN cohort rather than a full epoch. That is implemented here -- but on its own it would barely
move paper-trail's bill, and saying so is the point of this docstring. An iteration is *three*
Runner calls (TRAIN + current-VAL + post-commit probe-VAL), so VAL is charged **twice per
iteration at a fixed size** while TRAIN is charged once at size `N`. At the measured
$1.00/session (see ``dispatcher.DEFAULT_PER_SESSION_USD``), a `retrieval` iteration at TRAIN=10
costs ~$647, of which ~$636 is VAL. Ramping TRAIN 10 -> 5 saves $5 of $647.

So this module makes **both** cohorts drawable. `val_n` is the real cost lever; `train_n` is the
one that controls what the optimizer learns from. Two different knobs for two different jobs, and
conflating them is how a "cheap" ramp turns out to cost the same as the full run.

**What the pool is, exactly.** A claim is drawable only if `stage_claim.stage()` can stage it,
which requires at least one evidence annotation on the cited paper bucket. That is 1,699 of 2,141
TRAIN rows and 255 of 316 dev rows. This is not a filter this module invents: the benchmark's
labelled population *is* its evidence annotations -- `paper-tool-validation.md:203` states the gold
distribution over "1,873 evidence annotations" (dev+test), and `parse_verdict.gold_paper_label`
derives a label by taking the strictest observed annotation. A row with no annotation on its cited
bucket has no gold label to score against, so it is outside the population of record rather than a
class being silently dropped. Verified 2026-09-02: no claim in either split spans more than one
evidence bucket, so `(claim_row_id, paper_bucket)` is an unambiguous draw unit.

**Leakage posture.** This module runs consumer-side, in the dispatcher's process, and is never
mounted into the optimizer's readable tree. It reads `claims-<split>.jsonl` to learn *which rows
exist and which bucket each cites* -- structure, not verdicts. It never reads a label and never
writes one; gold resolution stays where `parse_verdict.py` puts it.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from dataclasses import dataclass
from typing import Any, Callable

_HERE = pathlib.Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import stage_claim  # noqa: E402

#: Base seed. The effective seed is ``SEED + iteration`` so each iteration draws reproducibly but
#: differently -- the same convention crc uses, and the reason a re-run of iteration 3 redraws
#: iteration 3's batch rather than iteration 0's.
SEED = 20260902

DRAW_MODES = ("cumulative", "fresh", "reproduce")


@dataclass(frozen=True)
class ClaimUnit:
    """One drawable unit: a claim row plus the cited paper bucket it is judged against."""

    claim_row_id: int
    paper_bucket: int

    @property
    def claim_id(self) -> str:
        """The id carried through staging, the ledger and the run manifest."""
        return f"{self.claim_row_id}-{self.paper_bucket}"


def claim_pool(split: str) -> list[ClaimUnit]:
    """Every stageable `(claim, cited bucket)` in `split`, in a stable order.

    Stable order matters: the draw is seeded, so an unstable pool order would make the same seed
    produce different batches and quietly break `reproduce`.
    """
    units: list[ClaimUnit] = []
    for row in stage_claim.load_claims(split):
        buckets = sorted({int(doc_id) // 1000 for doc_id in (row.get("evidence") or {})})
        # No annotation on any bucket -> no gold label to score against. See module docstring.
        for bucket in buckets:
            units.append(ClaimUnit(claim_row_id=int(row["id"]), paper_bucket=bucket))
    units.sort(key=lambda u: (u.claim_row_id, u.paper_bucket))
    return units


def ramp_for(iteration: int, schedule: "list[int]") -> int:
    """The graduated `N` for this iteration: schedule[i], clamped at the last rung.

    A ramp shorter than the run does not fall off the end -- it holds at its top rung, so
    `--iterations 10` against a 3-rung ramp runs seven iterations at full size rather than
    crashing or silently resetting to the first rung.
    """
    if not schedule:
        raise ValueError("ramp schedule is empty")
    if iteration < 0:
        raise ValueError(f"iteration must be >= 0, got {iteration}")
    return schedule[min(iteration, len(schedule) - 1)]


def parse_schedule(text: str) -> list[int]:
    """`"5,10,20"` -> `[5, 10, 20]`, rejecting a ramp that shrinks."""
    rungs = [int(part.strip()) for part in text.split(",") if part.strip()]
    if not rungs:
        raise ValueError(f"empty ramp schedule: {text!r}")
    if any(n <= 0 for n in rungs):
        raise ValueError(f"ramp rungs must be positive: {rungs}")
    if any(b < a for a, b in zip(rungs, rungs[1:])):
        # A ramp that shrinks is nearly always a typo, and under `cumulative` it is also
        # incoherent: the batch can never get smaller than what has already been drawn.
        raise ValueError(f"ramp schedule must be non-decreasing: {rungs}")
    return rungs


# -------------------------------------------------------------------------------------------------
# Draw history -- the bookkeeping `cumulative` and `reproduce` read back
# -------------------------------------------------------------------------------------------------


def load_draw_history(path: pathlib.Path) -> dict[int, list[str]]:
    """iteration -> the claim_ids drawn that iteration. Empty dict if there is no history yet."""
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): list(v) for k, v in raw.items()}


def record_draw(iteration: int, claim_ids: "list[str]", path: pathlib.Path) -> None:
    history = load_draw_history(path)
    history[iteration] = sorted(claim_ids)
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({str(k): v for k, v in sorted(history.items())}, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_batch(
    iteration: int,
    *,
    n: int,
    mode: str,
    split: str,
    history_path: pathlib.Path,
    seed: int | None = None,
    pool: "list[ClaimUnit] | None" = None,
) -> list[ClaimUnit]:
    """Resolve this iteration's batch and record the draw. Mirrors crc's `resolve_train_batch`.

    - ``cumulative`` -- the union of every prior draw plus enough fresh units to reach `n`. Never
      drops a unit the optimizer has already seen, which is what makes a growing batch a *growing*
      one rather than a sequence of unrelated samples.
    - ``fresh`` -- an independent draw of size `n`, unconstrained by history.
    - ``reproduce`` -- re-run the immediately preceding iteration's exact set. `n` must match it,
      so a ramp that moved cannot silently reproduce a different-sized batch.
    """
    if mode not in DRAW_MODES:
        raise ValueError(f"mode must be one of {DRAW_MODES}, got {mode!r}")
    units = list(pool) if pool is not None else claim_pool(split)
    by_id = {u.claim_id: u for u in units}
    history = load_draw_history(history_path)
    rng = random.Random(SEED + iteration if seed is None else seed)

    if mode == "reproduce":
        prior = history.get(iteration - 1)
        if not prior:
            raise ValueError(
                f"mode='reproduce' needs a recorded draw for iteration {iteration - 1}, found none"
            )
        if n != len(prior):
            raise ValueError(
                f"mode='reproduce' needs n == len(prior draw) ({len(prior)}), got n={n}"
            )
        drawn = [by_id[cid] for cid in prior if cid in by_id]
        if len(drawn) != len(prior):
            raise ValueError("prior draw references claim_ids absent from the pool")
    elif mode == "cumulative":
        already: set[str] = set()
        for prior_iter, prior_batch in history.items():
            if prior_iter < iteration:
                already.update(prior_batch)
        if n > len(units):
            raise ValueError(f"n={n} exceeds the {split} pool size {len(units)}")
        remaining = [u for u in units if u.claim_id not in already]
        rng.shuffle(remaining)
        needed = max(0, n - len(already))
        keep = sorted(already | {u.claim_id for u in remaining[:needed]})
        drawn = [by_id[cid] for cid in keep if cid in by_id]
    else:  # fresh
        if n > len(units):
            raise ValueError(f"n={n} exceeds the {split} pool size {len(units)}")
        drawn = sorted(rng.sample(units, n), key=lambda u: (u.claim_row_id, u.paper_bucket))

    record_draw(iteration, [u.claim_id for u in drawn], history_path)
    return drawn


# -------------------------------------------------------------------------------------------------
# Staging -- turn drawn units into the batch file the Runner reads
# -------------------------------------------------------------------------------------------------


def _memoize_corpus() -> None:
    """`stage_claim.load_corpus` re-reads an 8,515-row, 5MB JSONL on every call.

    Staging a 200-claim batch would read it 200 times. Memoized here rather than in
    `stage_claim.py` because that script is also a one-shot CLI, where a module-level cache is
    dead weight.
    """
    if getattr(stage_claim.load_corpus, "_memoized", False):
        return
    original = stage_claim.load_corpus
    cache: dict[int, dict[str, Any]] = {}

    def cached() -> dict[int, dict[str, Any]]:
        if not cache:
            cache.update(original())
        return cache

    cached._memoized = True  # type: ignore[attr-defined]
    stage_claim.load_corpus = cached  # type: ignore[assignment]


def stage_batch(
    units: "list[ClaimUnit]",
    *,
    split: str,
    staging_root: pathlib.Path,
    batch_path: pathlib.Path,
    source_mode: str = "corpus",
) -> pathlib.Path:
    """Stage every unit and write the `{"claims": [...]}` batch file `load_batch` expects.

    Staging is idempotent per claim, so a resumed run re-stages cheaply rather than re-deciding
    what to draw.
    """
    _memoize_corpus()
    staging_root = pathlib.Path(staging_root)
    claims: list[dict[str, Any]] = []
    for unit in units:
        out_dir = staging_root / unit.claim_id
        info = stage_claim.stage(
            split=split,
            claim_row_id=unit.claim_row_id,
            cited_paper_bucket=unit.paper_bucket,
            source_mode=source_mode,
            out_dir=out_dir,
        )
        claims.append(
            {
                "claim_id": unit.claim_id,
                "citekey": info["citekey"],
                "staging_dir": str(out_dir),
                # `staging_info.json` says how the text was BUILT (corpus|full); the schema's
                # `source_mode` is a different vocabulary entirely. The envelope's value is the
                # producer's job, not ours -- see OQ13.
                "source_mode": source_mode,
            }
        )
    batch_path = pathlib.Path(batch_path)
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(json.dumps({"claims": claims}, indent=2), encoding="utf-8")
    return batch_path


def val_inputs_for(
    *,
    n: int,
    split: str,
    run_id: str,
    staging_root: pathlib.Path,
    batch_root: pathlib.Path,
    history_path: pathlib.Path,
    source_mode: str = "corpus",
) -> Any:
    """A **fixed** VAL subsample, drawn once and reused by every iteration of the run.

    Fixed is the whole point, and it is not a convenience. The engine's frontier is a bare scalar:
    it compares iteration *i*'s VAL score against the best so far and steps back when the score
    drops. Redrawing VAL each iteration would make that comparison span two different claim sets,
    so ordinary sampling noise would read as a regression and trigger step-backs that have nothing
    to do with the program. One draw per run, held constant.

    The draw is seeded and iteration-independent (`SEED + 0`), so a resumed run reconstructs the
    same set without needing to persist it — and `history_path` still records the exact claim_ids,
    which is the audit trail for "which 50 claims is this number over?".

    ⚠ Two VAL sizes are two different measurements. A score over a 50-claim VAL is not comparable
    to one over the full pool, and neither is comparable to a published baseline computed over the
    whole dev set. `--val-n` buys a real number sooner; it does not buy a comparable one.
    """
    from adapter import _import_engine  # noqa: PLC0415

    schemas = _import_engine()
    units = resolve_batch(0, n=n, mode="fresh", split=split, history_path=history_path)
    batch_path = pathlib.Path(batch_root) / f"{run_id}-val.json"
    stage_batch(
        units,
        split=split,
        staging_root=staging_root,
        batch_path=batch_path,
        source_mode=source_mode,
    )
    return schemas.RunInputs(
        input_ref=str(batch_path), batch_id=f"{run_id}-val", split="val"
    )


def train_inputs_factory(
    *,
    schedule: "list[int]",
    mode: str,
    split: str,
    run_id: str,
    staging_root: pathlib.Path,
    batch_root: pathlib.Path,
    history_path: pathlib.Path,
    source_mode: str = "corpus",
) -> Callable[[int], Any]:
    """The engine's `train_inputs` hook: iteration -> `RunInputs` over that iteration's batch.

    Imported lazily so this module stays importable (and selftestable) without the engine present.
    """

    def factory(iteration: int):
        from adapter import _import_engine  # noqa: PLC0415 -- engine is optional at import time

        schemas = _import_engine()
        n = ramp_for(iteration, schedule)
        units = resolve_batch(
            iteration, n=n, mode=mode, split=split, history_path=history_path
        )
        batch_path = pathlib.Path(batch_root) / f"{run_id}-train-i{iteration}.json"
        stage_batch(
            units,
            split=split,
            staging_root=staging_root,
            batch_path=batch_path,
            source_mode=source_mode,
        )
        return schemas.RunInputs(
            input_ref=str(batch_path),
            batch_id=f"{run_id}-train-i{iteration}",
            split="train",
        )

    return factory


# =================================================================================================
# Offline gates
# =================================================================================================


def _selftest() -> int:
    import tempfile

    checks: list[tuple[str, bool]] = []

    # -- the ramp ---------------------------------------------------------------------------------
    checks += [
        ("a ramp returns its rung for each iteration", ramp_for(0, [5, 10, 20]) == 5),
        ("...and the next rung next", ramp_for(1, [5, 10, 20]) == 10),
        ("...and HOLDS at the top rather than falling off the end",
         ramp_for(9, [5, 10, 20]) == 20),
        ("a single-rung ramp is a constant N", ramp_for(7, [25]) == 25),
        ("'5,10,20' parses to its rungs", parse_schedule("5, 10,20") == [5, 10, 20]),
        ("a shrinking ramp is refused, since cumulative cannot honour it",
         _raises(lambda: parse_schedule("20,10"), ValueError)),
        ("a zero rung is refused", _raises(lambda: parse_schedule("0,5"), ValueError)),
        ("an empty schedule is refused", _raises(lambda: ramp_for(0, []), ValueError)),
    ]

    # -- draws, against a synthetic pool so the gates need no benchmark ---------------------------
    pool = [ClaimUnit(claim_row_id=i, paper_bucket=1) for i in range(50)]
    with tempfile.TemporaryDirectory() as tmp:
        hist = pathlib.Path(tmp) / "draws.json"

        i0 = resolve_batch(0, n=5, mode="fresh", split="dev", history_path=hist, pool=pool)
        checks.append(("a fresh draw returns exactly n units", len(i0) == 5))
        checks.append(("...and records the draw", set(load_draw_history(hist)) == {0}))

        again = resolve_batch(0, n=5, mode="fresh", split="dev", history_path=hist, pool=pool)
        checks.append(("the same iteration redraws identically -- the seed is iteration-keyed",
                       [u.claim_id for u in again] == [u.claim_id for u in i0]))

        i1 = resolve_batch(1, n=5, mode="fresh", split="dev", history_path=hist, pool=pool)
        checks.append(("a different iteration draws a different sample",
                       [u.claim_id for u in i1] != [u.claim_id for u in i0]))

    with tempfile.TemporaryDirectory() as tmp:
        hist = pathlib.Path(tmp) / "draws.json"
        c0 = resolve_batch(0, n=5, mode="cumulative", split="dev", history_path=hist, pool=pool)
        c1 = resolve_batch(1, n=12, mode="cumulative", split="dev", history_path=hist, pool=pool)
        checks += [
            ("a cumulative batch grows to the new n", len(c1) == 12),
            ("...and KEEPS every unit the optimizer already saw",
             set(u.claim_id for u in c0) <= set(u.claim_id for u in c1)),
            ("...with no duplicates", len({u.claim_id for u in c1}) == len(c1)),
        ]
        c2 = resolve_batch(2, n=12, mode="cumulative", split="dev", history_path=hist, pool=pool)
        checks.append(("a cumulative batch at an unchanged n draws nothing new",
                       {u.claim_id for u in c2} == {u.claim_id for u in c1}))

        r3 = resolve_batch(3, n=12, mode="reproduce", split="dev", history_path=hist, pool=pool)
        checks.append(("reproduce re-runs the previous iteration's exact set",
                       {u.claim_id for u in r3} == {u.claim_id for u in c2}))
        checks.append(("...and refuses a mismatched n rather than silently resizing",
                       _raises(lambda: resolve_batch(4, n=7, mode="reproduce", split="dev",
                                                     history_path=hist, pool=pool), ValueError)))

    with tempfile.TemporaryDirectory() as tmp:
        hist = pathlib.Path(tmp) / "draws.json"
        checks.append(("a draw larger than the pool is refused, not silently truncated",
                       _raises(lambda: resolve_batch(0, n=999, mode="fresh", split="dev",
                                                     history_path=hist, pool=pool), ValueError)))
        checks.append(("an unknown mode is refused",
                       _raises(lambda: resolve_batch(0, n=1, mode="random", split="dev",
                                                     history_path=hist, pool=pool), ValueError)))

    # -- VAL must be ONE draw held constant, or the frontier compares two different sets ----------
    with tempfile.TemporaryDirectory() as tmp:
        hist = pathlib.Path(tmp) / "val_draw.json"
        v_a = resolve_batch(0, n=10, mode="fresh", split="dev", history_path=hist, pool=pool)
        v_b = resolve_batch(0, n=10, mode="fresh", split="dev", history_path=hist, pool=pool)
        checks.append((
            "a VAL draw is reproducible across calls, so every iteration scores the same claims "
            "and a step-back means the program moved, not the sample",
            [u.claim_id for u in v_a] == [u.claim_id for u in v_b],
        ))
        v_c = resolve_batch(0, n=20, mode="fresh", split="dev", history_path=hist, pool=pool)
        checks.append((
            "...but a different VAL size is a different measurement, not a superset",
            [u.claim_id for u in v_c] != [u.claim_id for u in v_a],
        ))

    # -- the draw unit ----------------------------------------------------------------------------
    checks.append(("a unit's claim_id carries both row and bucket, so two buckets of one claim "
                   "never collide", ClaimUnit(7, 31).claim_id == "7-31"))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def _raises(fn, exc) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pool", choices=("train", "dev", "test"),
                    help="print the drawable pool size for a split")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.pool:
        units = claim_pool(args.pool)
        rows = len({u.claim_row_id for u in units})
        print(f"{args.pool}: {len(units)} drawable units over {rows} claim rows")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
