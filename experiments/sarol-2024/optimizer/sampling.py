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
import inspect
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

#: The engine's first ``iter_n``. ``engine/loop.py`` iterates ``for n in range(resume_from + 1,
#: iterations + 1)``, so on a fresh run the first iteration it hands this module is **1**, not 0.
#:
#: This is a cross-repo contract, not a detail. The first optimization run (2026-09-02) ramped
#: 25 -> 50 -> 50 instead of the requested 10 -> 25 -> 50 because `ramp_for` assumed a 0-based
#: counter, so the cheap 10-claim rung -- the one whose entire purpose is to fail early -- never
#: ran. It is stated once here, and `dispatcher._integration_checks` pins it by driving the REAL
#: ``run_loop`` and recording the values the factory is actually called with. That is deliberate:
#: this module's own selftests previously asserted the convention against itself, which is how a
#: wrong base passed 296 green gates.
ENGINE_FIRST_ITER_N = 1


def rung_index(iter_n: int, *, first_iter_n: int = ENGINE_FIRST_ITER_N) -> int:
    """The engine's ``iter_n`` -> a 0-based ramp rung.

    Deliberately separate from :func:`ramp_for`, which stays a pure 0-based lookup the offline
    gates can exercise directly. One function knows the engine's counting base; everything else
    is expressed in rungs.
    """
    rung = iter_n - first_iter_n
    if rung < 0:
        raise ValueError(
            f"iter_n={iter_n} is below the engine's first iteration ({first_iter_n}); "
            "the ramp has no rung for it"
        )
    return rung


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


def gold_labels(split: str) -> "dict[tuple[int, int], str]":
    """`(claim_row_id, paper_bucket) -> 9-class gold label`, for every unit in `split`'s pool.

    Read from the benchmark rather than from a staged run, so a draw can be stratified *before*
    anything is dispatched -- stratifying after staging would mean paying for the claims you then
    throw away.
    """
    import stage_claim  # noqa: PLC0415
    from parse_verdict import gold_paper_label  # noqa: PLC0415

    out: dict[tuple[int, int], str] = {}
    for row in stage_claim.load_claims(split):
        evidence = row.get("evidence") or {}
        row_id = int(row["id"])
        for bucket in sorted({int(doc_id) // 1000 for doc_id in evidence}):
            mine = {k: v for k, v in evidence.items() if v and int(k) // 1000 == bucket}
            if mine:
                out[(row_id, bucket)] = gold_paper_label(mine)
    return out


def stratified_draw(
    units: "list[ClaimUnit]",
    gold: "dict[tuple[int, int], str]",
    n: int,
    *,
    seed: int,
    classes: "tuple[str, ...] | None" = None,
) -> "list[ClaimUnit]":
    """Draw `n` units spread as evenly as the pool allows across the objective's classes.

    **Why stratifying is free here, and would not be under a different objective.** The frontier is
    macro-F1, which already weights every class equally regardless of how common it is. Equalising
    support therefore does not shift the estimand at all -- it only cuts its variance. Under a
    micro/accuracy objective the same draw WOULD distort the number, which is part of why micro is
    not the objective. (It does break comparability of the reported `micro_f1` and of the published
    3-way baseline, so quote those from an unstratified batch.)

    Water-filling, scarcest class first: each class takes an equal share of what is left, capped by
    what it actually has, and the surplus flows to classes with capacity. On the real dev pool at
    n=140 that resolves to "every rare-class claim dev has, plus ACCURATE for the remainder", which
    is the most support the split can give.

    Units whose gold is OUTSIDE `classes` are **excluded from the draw**, not merely unscored. Such
    a claim cannot add recall to any scored class -- its gold class is not in the objective -- while
    a prediction on it can only cost precision, so including it injects noise the metric has no way
    to attribute. On dev that drops 3 ETIQUETTE claims out of 255.
    """
    import random  # noqa: PLC0415

    from score_sarol3 import OBJECTIVE_CLASSES  # noqa: PLC0415

    classes = classes or OBJECTIVE_CLASSES
    by_class: dict[str, list] = {c: [] for c in classes}
    for u in units:
        label = gold.get((u.claim_row_id, u.paper_bucket))
        if label in by_class:
            by_class[label].append(u)

    rng = random.Random(seed)
    for c in classes:
        rng.shuffle(by_class[c])

    available = [c for c in classes if by_class[c]]
    # Scarcest first: a class with 6 claims must claim its share before an abundant one soaks up
    # the budget. Sorting the other way would hand ACCURATE n/k and starve the tail.
    available.sort(key=lambda c: len(by_class[c]))

    taken: list = []
    remaining = n
    for i, c in enumerate(available):
        share = remaining // (len(available) - i)
        take = min(len(by_class[c]), share)
        taken.extend(by_class[c][:take])
        by_class[c] = by_class[c][take:]
        remaining -= take
    # Surplus (every class exhausted below its share) flows to whoever still has capacity.
    for c in sorted(available, key=lambda c: -len(by_class[c])):
        if remaining <= 0:
            break
        take = min(len(by_class[c]), remaining)
        taken.extend(by_class[c][:take])
        remaining -= take

    taken.sort(key=lambda u: (u.claim_row_id, u.paper_bucket))
    return taken


def ramp_for(rung: int, schedule: "list[int]") -> int:
    """The graduated `N` for a 0-based ramp **rung**: schedule[rung], clamped at the last one.

    Takes a rung, not the engine's ``iter_n`` -- convert with :func:`rung_index` first. Keeping
    this function 0-based and base-agnostic is what lets the gates below test the ramp itself
    without also encoding an assumption about who calls it.

    A ramp shorter than the run does not fall off the end -- it holds at its top rung, so
    `--iterations 10` against a 3-rung ramp runs seven iterations at full size rather than
    crashing or silently resetting to the first rung.
    """
    if not schedule:
        raise ValueError("ramp schedule is empty")
    if rung < 0:
        raise ValueError(f"rung must be >= 0, got {rung}")
    return schedule[min(rung, len(schedule) - 1)]


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


def assert_staged_size(batch_path: pathlib.Path, expected_n: int, *, label: str) -> None:
    """Assert the batch that will actually be EXECUTED holds `expected_n` claims.

    This is the gate Bug 1 was missing. `--val-n` reached :class:`dispatcher.CostModel` but not
    the sampler, so the preflight quoted $63 for a $647 run -- and because ``BudgetGuard`` reads
    the same cost model, enforcement was wrong by the same 10x, in the same direction. 296
    offline gates missed it because every one of them asserted on ``CostModel``, a *pricing*
    input, and none on the staged batch the Runner is handed.

    So this reads the file back through ``adapter.load_batch`` -- the Runner's own reader -- rather
    than trusting the list that was just written. Asserting the artifact is the whole point: when
    a flag both prices work and selects work, a check that only reads the price proves nothing.
    """
    from adapter import load_batch  # noqa: PLC0415 -- adapter imports the engine lazily

    actual = len(load_batch(batch_path))
    if actual != expected_n:
        raise ValueError(
            f"{label}: staged {actual} claims but {expected_n} were requested ({batch_path}). "
            "The batch that gets priced and the batch that gets executed must be the same batch."
        )


def val_inputs_for(
    *,
    n: int,
    split: str,
    run_id: str,
    staging_root: pathlib.Path,
    batch_root: pathlib.Path,
    history_path: pathlib.Path,
    source_mode: str = "corpus",
    stratify: bool = True,
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
    # Spread the draw across the objective's classes. Free for a macro objective (see
    # `stratified_draw`), and rare-class support -- not batch size -- is this metric's binding
    # constraint: dev holds only 6 MISQUOTE and 6 INDIRECT, so an unstratified n=50 expects ~1 of
    # each and their F1 swings on a single claim. A stratified n=60 takes every one.
    #
    # Narrowed as a POOL rather than drawn directly, so `resolve_batch` still owns the draw, the
    # seeding and the `draw_history.json` audit trail. Two mechanisms writing that history would
    # be one too many.
    pool = None
    if stratify:
        pool = stratified_draw(claim_pool(split), gold_labels(split), n, seed=SEED)
        if len(pool) < n:
            raise ValueError(
                f"stratified VAL draw could only fill {len(pool)} of {n} requested claims from "
                f"split {split!r}: the objective's classes do not hold that many. Lower --val-n, "
                "or pass stratify=False to draw from the raw pool."
            )
    units = resolve_batch(
        0, n=n, mode="fresh", split=split, history_path=history_path, pool=pool
    )
    batch_path = pathlib.Path(batch_root) / f"{run_id}-val.json"
    stage_batch(
        units,
        split=split,
        staging_root=staging_root,
        batch_path=batch_path,
        source_mode=source_mode,
    )
    assert_staged_size(batch_path, n, label=f"VAL batch for run {run_id}")
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
    first_iter_n: int = ENGINE_FIRST_ITER_N,
) -> Callable[[int], Any]:
    """The engine's `train_inputs` hook: ``iter_n`` -> `RunInputs` over that iteration's batch.

    The engine calls this with **its** iteration counter, which starts at
    :data:`ENGINE_FIRST_ITER_N` (1), not at 0. `first_iter_n` states that base explicitly rather
    than letting the ramp infer it -- inferring it is what skipped the cheapest rung on the first
    real run. Draw bookkeeping (the seed and `draw_history.json` keys) stays keyed on the engine's
    own ``iter_n`` so a history file reads the same way the run log does; only the *ramp rung* is
    rebased.

    Imported lazily so this module stays importable (and selftestable) without the engine present.
    """

    def factory(iter_n: int):
        from adapter import _import_engine  # noqa: PLC0415 -- engine is optional at import time

        schemas = _import_engine()
        rung = rung_index(iter_n, first_iter_n=first_iter_n)
        n = ramp_for(rung, schedule)
        units = resolve_batch(
            iter_n, n=n, mode=mode, split=split, history_path=history_path
        )
        batch_path = pathlib.Path(batch_root) / f"{run_id}-train-i{iter_n}.json"
        stage_batch(
            units,
            split=split,
            staging_root=staging_root,
            batch_path=batch_path,
            source_mode=source_mode,
        )
        assert_staged_size(
            batch_path, n, label=f"TRAIN batch for iter {iter_n} (ramp rung {rung})"
        )
        return schemas.RunInputs(
            input_ref=str(batch_path),
            batch_id=f"{run_id}-train-i{iter_n}",
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

    # -- the engine's counting base (Bug 2) -------------------------------------------------------
    # These test the CONVERSION only. That the base really is 1 is pinned in
    # `dispatcher._integration_checks`, against the real `run_loop` -- asserting it here too would
    # repeat the original mistake of testing this module's assumption against itself.
    checks += [
        ("the engine's first iteration maps to the FIRST rung, not the second -- the whole of "
         "Bug 2", ramp_for(rung_index(ENGINE_FIRST_ITER_N), [10, 25, 50]) == 10),
        ("...and the second engine iteration to the second rung",
         ramp_for(rung_index(ENGINE_FIRST_ITER_N + 1), [10, 25, 50]) == 25),
        ("...and the third to the third, so a 3-rung ramp over 3 iterations runs all three",
         ramp_for(rung_index(ENGINE_FIRST_ITER_N + 2), [10, 25, 50]) == 50),
        ("a 0-based caller under the engine's base is refused rather than silently clamped -- "
         "the failure Bug 2 wanted",
         _raises(lambda: rung_index(0, first_iter_n=1), ValueError)),
        ("the base is a parameter, so a caller that counts from 0 says so",
         rung_index(0, first_iter_n=0) == 0),
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
    # -- stratified draw: rare-class support is what the macro objective actually needs ----------
    # Synthetic pool, so these test the ALGORITHM rather than today's benchmark contents (the real
    # dev distribution is pinned in score_sarol3's gates). Five classes with spread availability,
    # because a 3-class fixture cannot distinguish scarcest-first from abundant-first -- the
    # surplus pass repairs the difference at small k, and an earlier version of these gates was
    # green under BOTH orderings for exactly that reason.
    _AVAIL = {"ACCURATE": 200, "NOT_SUBSTANTIATE": 50, "CONTRADICT": 50,
              "OVERSIMPLIFY": 8, "MISQUOTE": 1, "ETIQUETTE": 9}  # ETIQUETTE: outside the objective
    _su, _sg, _next = [], {}, 0
    for _lbl, _cnt in _AVAIL.items():
        for _ in range(_cnt):
            _u = ClaimUnit(claim_row_id=_next, paper_bucket=0)
            _su.append(_u); _sg[(_next, 0)] = _lbl; _next += 1

    def _dist_of(drawn):
        d = {}
        for u in drawn:
            lbl = _sg[(u.claim_row_id, 0)]
            d[lbl] = d.get(lbl, 0) + 1
        return d

    _drawn = stratified_draw(_su, _sg, 157, seed=1)
    _dist = _dist_of(_drawn)
    _again = stratified_draw(_su, _sg, 157, seed=1)

    checks += [
        ("a stratified draw returns exactly the requested size", len(_drawn) == 157),
        ("...taking EVERY unit of the scarcest objective classes rather than their proportional "
         "share -- rare-class support, not batch size, is what a macro objective is short of",
         _dist.get("MISQUOTE") == 1 and _dist.get("OVERSIMPLIFY") == 8),
        ("...and capping the abundant class near an equal share rather than letting it soak up "
         "the budget (abundant-first would give it ~86 of 157 here)",
         _dist.get("ACCURATE", 0) <= 55),
        ("...spreading the remainder evenly across the classes that still have units",
         _dist.get("NOT_SUBSTANTIATE") == _dist.get("CONTRADICT") >= 45),
        ("...excluding classes outside the objective, which cannot add recall to any scored "
         "class and can only cost precision",
         "ETIQUETTE" not in _dist),
        ("...deterministically for a fixed seed, so a resumed run rebuilds the same VAL",
         [u.claim_id for u in _drawn] == [u.claim_id for u in _again]),
        ("a request larger than the objective classes can fill comes back short, so the caller "
         "can refuse rather than silently measure something else",
         len(stratified_draw(_su, _sg, 5000, seed=1)) == 200 + 50 + 50 + 8 + 1),
        # The default is the decision: an unstratified VAL at these sizes expects ~1 MISQUOTE.
        ("VAL stratifies BY DEFAULT, not on request",
         inspect.signature(val_inputs_for).parameters["stratify"].default is True),
    ]

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
