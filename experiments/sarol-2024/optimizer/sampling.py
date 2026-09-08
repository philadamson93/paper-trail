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

**What the pool is, exactly.** A claim is drawable only if `stage_claim.stage()` can stage it.
That is **2,076 of 2,141 TRAIN rows and 311 of 316 dev rows**. It read 1,699 / 255 until
2026-09-07, when the evidence-annotation requirement was found to be deleting two whole classes --
`IRRELEVANT` and `ETIQUETTE` are *defined* by the absence of evidence, so requiring an annotation
excluded 100% of them and nothing else. `recovered_gold` joins their labels back from the
annotation files. The 65 TRAIN and 5 dev rows still outside the pool are ones `stage()` cannot
stage at all, which is a different thing from a class being dropped.

Gold therefore comes from **two** sources, not one. `parse_verdict.gold_paper_label` derives a label
from the evidence annotations by taking the strictest observed one -- that covers the seven classes
that have evidence. `recovered_gold` supplies the other two from the annotation files directly. The
older reading, that "the labelled population *is* its evidence annotations" (from
`paper-tool-validation.md:203`, which counts gold over "1,873 evidence annotations" for dev+test),
is the reading that produced the bug: it is true of the seven, and false of exactly the two classes
whose definition is that no evidence exists. Verified 2026-09-02: no claim in either split spans
more than one evidence bucket, so `(claim_row_id, paper_bucket)` is an unambiguous draw unit.

**Leakage posture.** This module runs consumer-side, in the dispatcher's process, and is never
mounted into the optimizer's readable tree. It reads `claims-<split>.jsonl` to learn *which rows
exist and which bucket each cites* -- structure, not verdicts. It never reads a label and never
writes one; gold resolution stays where `parse_verdict.py` puts it.
"""
from __future__ import annotations

import argparse
import inspect
import functools
import json
import re
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


#: Splits, as the benchmark's annotation tree names them.
_ANN_SPLIT = {"train": "Train", "dev": "Dev", "test": "Test"}


def _norm(text) -> str:
    """Whitespace/punctuation-insensitive form, for joining a claim to its annotation file."""
    if isinstance(text, list):
        text = " ".join(map(str, text))
    return re.sub(r"\W+", " ", str(text or "")).lower().strip()


@functools.lru_cache(maxsize=8)
def recovered_gold(split: str) -> "dict[tuple[int, int], str]":
    """Gold for the claims the evidence-annotation rule silently deleted.

    **The bug this repairs.** A unit was drawable only if its cited bucket carried an *evidence
    annotation*. But `IRRELEVANT` means "no information in the cited paper is relevant" and
    `ETIQUETTE` means "unclear what is being cited to this paper" -- both are *defined by the
    absence of evidence*, so neither has evidence segments to point at. The rule therefore deleted
    exactly the two classes whose defining property is having nothing to point at, and nothing
    else: the excluded population is **442/2141 TRAIN (300 ETIQUETTE + 142 IRRELEVANT)** and
    **61/316 dev (37 + 24)**, an exact match, while every other class is 100% evidence-covered.

    That is why no run ever predicted `IRRELEVANT` and why a third of 3-way macro sat pinned at
    zero: the program was never shown one. It was a property of our filter, not of the benchmark.

    **How gold is recovered.** The label lives in the benchmark's per-citation annotation files
    (`annotations/<Split>/citations/<cited>/<citing>_<n>.json`), which `claims-*.jsonl` does not
    carry for these rows. The join is on normalised claim text against the annotation's
    `citation_context`, restricted to the cited paper's own directory.

    **Validated, not assumed.** Run against the 255 dev rows whose gold is already known from
    their evidence annotations, the join agrees **235/235 and disagrees 0 times** -- its only
    failure mode is *no match* (~8%), never a wrong label. Unmatched rows stay excluded, which
    keeps the pool conservative: a claim is added only when its label is unambiguous. That control
    is a standing gate, not a one-off check.
    """
    import stage_claim  # noqa: PLC0415

    by_bucket = _annotations_by_bucket(split)
    out: dict[tuple[int, int], str] = {}
    for row in stage_claim.load_claims(split):
        evidence = row.get("evidence") or {}
        if any(evidence.values()):
            continue  # already drawable; gold comes from its own evidence annotations
        for bucket in sorted({int(d) // 1000 for d in (row.get("cited_doc_ids") or [])}):
            label = join_label(row.get("claim"), bucket, by_bucket)
            if label is not None:
                out[(int(row["id"]), bucket)] = label
    return out


def join_label(claim, bucket: int, by_bucket: "dict[int, list[dict]]") -> "str | None":
    """The annotation label for `claim` under `bucket`, or None when it is not unambiguous.

    Split out so the precision control in the gates drives *this* function rather than a
    reimplementation of it -- a control that exercises a copy proves nothing about what ships.
    """
    text = _norm(claim)
    if not text:
        return None
    hits = {
        obj["label"]
        for obj in by_bucket.get(bucket, ())
        if text in _norm(obj.get("citation_context") or obj.get("citing_paragraph"))
    }
    return hits.pop() if len(hits) == 1 else None


def _annotations_by_bucket(split: str) -> "dict[int, list[dict]]":
    """Per-citation annotation records, keyed by the cited paper's bucket number."""
    import stage_claim  # noqa: PLC0415

    ann_dir = stage_claim.BENCH_DIR / "annotations" / _ANN_SPLIT[split] / "citations"
    by_bucket: dict[int, list[dict]] = {}
    if ann_dir.is_dir():
        for path in ann_dir.rglob("*.json"):
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(obj, dict) or not obj.get("label"):
                continue
            head = path.parent.name.split("_", 1)[0]
            if head.isdigit():
                by_bucket.setdefault(int(head), []).append(obj)
    return by_bucket


def claim_pool(split: str) -> list[ClaimUnit]:
    """Every stageable `(claim, cited bucket)` in `split`, in a stable order.

    Stable order matters: the draw is seeded, so an unstable pool order would make the same seed
    produce different batches and quietly break `reproduce`.
    """
    units: list[ClaimUnit] = []
    seen: set[tuple[int, int]] = set()
    for row in stage_claim.load_claims(split):
        buckets = sorted({int(doc_id) // 1000 for doc_id in (row.get("evidence") or {})})
        for bucket in buckets:
            seen.add((int(row["id"]), bucket))
            units.append(ClaimUnit(claim_row_id=int(row["id"]), paper_bucket=bucket))
    # ...plus the ETIQUETTE / IRRELEVANT claims the evidence-annotation rule used to delete. Their
    # cited paper is `cited_doc_ids // 1000`, which agrees with the evidence-derived bucket on
    # 255/255 rows where both exist -- so BM25 has exactly the same document to search that it
    # does for any other claim. See `recovered_gold`.
    for (row_id, bucket) in recovered_gold(split):
        if (row_id, bucket) not in seen:
            units.append(ClaimUnit(claim_row_id=row_id, paper_bucket=bucket))
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
    # The evidence-less classes carry their label in the annotation files instead; `recovered_gold`
    # joins them back. Merged second and without overwriting, so a unit that has real evidence
    # always keeps the label derived from it.
    for key, label in recovered_gold(split).items():
        out.setdefault(key, label)
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

    **This draw is NOT free under the current objective, and is off by default.** It was free while
    the frontier was macro-F1, which weights every class equally however common it is: equalising
    support cut the variance without shifting the estimand. The frontier is now **accuracy**, which
    is weighted by the population's own class balance -- so re-balancing the draw changes what the
    number means rather than how precisely it is measured. A stratified VAL reports accuracy over a
    population that does not exist, and it is not comparable to the 0.595 do-nothing floor, which is
    the ACCURATE share of the *unstratified* dev pool.

    So: use this for a per-class question, where equal support is the point and rare-class F1 at
    n=50 otherwise swings on a single claim. Do not use it to produce the frontier number. Same
    caveat as before for `micro_f1` and the published 3-way baseline -- quote those unstratified
    too.

    Water-filling, scarcest class first: each class takes an equal share of what is left, capped by
    what it actually has, and the surplus flows to classes with capacity. On the real dev pool at
    n=140 that resolves to "every rare-class claim dev has, plus ACCURATE for the remainder", which
    is the most support the split can give.

    Units whose gold is OUTSIDE `classes` are **excluded from the draw**, not merely unscored. Such
    a claim cannot add recall to any scored class while a prediction on it can only cost precision,
    so including it would inject noise nothing can attribute.

    ⚠ **As of 2026-09-07 this excludes nothing**, and both reasons it used to matter are gone:
    `OBJECTIVE_CLASSES` is now all nine labels, so no gold class is outside it; and the pool repair
    put ETIQUETTE and IRRELEVANT back, so the 3 stray ETIQUETTE claims this used to drop (out of the
    then-255 dev rows) are 38 ordinary members of a 311-row pool. The clause is kept because
    `classes` is a parameter and a caller may still narrow it.
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
    stratify: bool = False,
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
    # OFF by default since the objective became accuracy (2026-09-07). Accuracy is a population
    # quantity: it asks what fraction of the split's claims the program gets right, so the draw has
    # to look like the split. A stratified VAL over-samples the rare classes and the resulting
    # number is not the population accuracy of anything -- it is accuracy on a population that does
    # not exist. `stratified_draw`'s own docstring said as much while the default still stratified.
    #
    # Kept as an opt-in because it is still the right draw for a per-class question (rare-class F1
    # at n=50 swings on a single claim, and dev holds only 6 MISQUOTE and 6 INDIRECT). Ask for it
    # when you want per-class resolution; do not ask for it when you want the frontier number.
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

    _seam_tmp = tempfile.mkdtemp(prefix="sampling-seam-")

    def _stageable(unit, split: str) -> bool:
        """Really run `stage_claim.stage`, rather than restate its precondition here.

        A gate that re-implements the rule it is checking passes when the two drift apart, which
        is the whole failure this exists to catch. ~30ms a unit, so the dev pool sweeps in ~9s.
        """
        try:
            stage_claim.stage(
                split=split,
                claim_row_id=unit.claim_row_id,
                cited_paper_bucket=unit.paper_bucket,
                source_mode="corpus",
                out_dir=pathlib.Path(_seam_tmp) / "sweep",
            )
            return True
        except Exception:
            return False

    _gold_dev = gold_labels("dev")
    _by_kind: dict[bool, Any] = {}
    for _u in claim_pool("dev"):
        _recovered = _gold_dev.get((_u.claim_row_id, _u.paper_bucket)) in {
            "ETIQUETTE", "IRRELEVANT"
        }
        _by_kind.setdefault(_recovered, _u)
    _staged_evidence_backed = (
        False in _by_kind and _stageable(_by_kind[False], "dev")
    )
    _staged_recovered = True in _by_kind and _stageable(_by_kind[True], "dev")

    # Cross-consumer gold agreement. Pure data -- no staging, no dispatch -- so it sweeps the
    # whole pool in well under a second.
    import parse_verdict as _pv  # noqa: PLC0415

    _gold_map = gold_labels("dev")
    _rows_by_id = {int(r["id"]): r for r in stage_claim.load_claims("dev")}
    _gold_disagreements: list[str] = []
    _gold_checked_recovered = 0
    for _u in claim_pool("dev"):
        _row = _rows_by_id.get(_u.claim_row_id)
        if _row is None:
            continue
        _ev = {
            d: a for d, a in (_row.get("evidence") or {}).items()
            if int(d) // 1000 == _u.paper_bucket
        }
        if not _ev:
            _gold_checked_recovered += 1
        _grader = _pv.canonical_gold_label(
            split="dev",
            claim_row_id=_u.claim_row_id,
            cited_paper_bucket=_u.paper_bucket,
            evidence_for_bucket=_ev,
        )
        _drawn = _gold_map.get((_u.claim_row_id, _u.paper_bucket))
        if _drawn is not None and _drawn != _grader:
            _gold_disagreements.append(
                f"{_u.claim_row_id}-{_u.paper_bucket}: draw={_drawn} grader={_grader}"
            )

    # The negative control for the relaxation: a bucket the claim neither has evidence for nor
    # cites has no source text to stage, and must still be refused.
    _stage_refuses_uncited = _raises(
        lambda: stage_claim.stage(
            split="dev", claim_row_id=89, cited_paper_bucket=999999,
            source_mode="corpus", out_dir=pathlib.Path(_seam_tmp) / "uncited",
        ),
        ValueError,
    )

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
    # ETIQUETTE and IRRELEVANT are IN the objective now (the six-class set was a pool-filter
    # artifact). `NOT_A_LABEL` stands in for anything outside the scored vocabulary.
    _AVAIL = {"ACCURATE": 200, "NOT_SUBSTANTIATE": 50, "CONTRADICT": 50,
              "OVERSIMPLIFY": 8, "MISQUOTE": 1, "NOT_A_LABEL": 9}
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
        ("...excluding gold outside the scored vocabulary, which cannot add recall to any scored "
         "class and can only cost precision",
         "NOT_A_LABEL" not in _dist),
        ("...deterministically for a fixed seed, so a resumed run rebuilds the same VAL",
         [u.claim_id for u in _drawn] == [u.claim_id for u in _again]),
        ("a request larger than the objective classes can fill comes back short, so the caller "
         "can refuse rather than silently measure something else",
         len(stratified_draw(_su, _sg, 5000, seed=1)) == 200 + 50 + 50 + 8 + 1),
        # The repair itself: the two classes the evidence-annotation rule used to delete are now
        # drawable, and the objective spans all nine.
        ("the pool carries ETIQUETTE and IRRELEVANT, which the evidence-annotation rule deleted "
         "(442 TRAIN / 61 dev rows, 100% those two classes)",
         {"ETIQUETTE", "IRRELEVANT"} <= set(gold_labels("dev").values())),
        ("...and the recovered dev gold is ~56 claims, not the 3 the old filter left",
         50 <= len(recovered_gold("dev")) <= 62),
        # gold_labels() merging the recovery is NOT enough: the units must also reach the POOL, or
        # the draw silently reverts to the old 255 while gold looks complete. Negative-controlled
        # 2026-09-07 -- dropping them from `claim_pool` failed nothing until this gate existed.
        ("the recovered claims reach the POOL, not just the gold map -- dev is 311 units, not "
         "the 255 the evidence-annotation rule left",
         305 <= len(claim_pool("dev")) <= 316),
        ("...and the pool actually contains the two recovered classes",
         {"ETIQUETTE", "IRRELEVANT"} <= {
             gold_labels("dev").get((u.claim_row_id, u.paper_bucket))
             for u in claim_pool("dev")
         }),
        # ...and the seam the previous three gates stop one step short of. Being in the pool is
        # worth nothing if `stage_claim.stage` then refuses the unit: the pool was repaired for
        # the recovered classes and the stager's evidence-annotation gate was not, so a draw
        # containing one aborted the run at staging time with every gate above green. The first
        # live `--val-n` draw hit it on its first try (claim 89 / bucket 24, ETIQUETTE).
        #
        # This asserts what CROSSES the seam rather than what either side believes about itself,
        # which is the 2026-09-03 post-mortem's own lesson about guards that pass locally.
        ("every unit the pool yields can actually be STAGED -- the pool's promise is "
         "'stageable', and nothing checked it against the stager",
         all(_stageable(u, "dev") for u in claim_pool("dev"))),
        ("...proven by really staging one of each kind through `stage_claim.stage`, not by "
         "re-implementing its precondition here",
         _staged_evidence_backed and _staged_recovered),
        ("...while a bucket the claim neither has evidence for nor cites is STILL refused, so "
         "the relaxation admitted the recovered classes and not everything",
         _stage_refuses_uncited),
        # The OTHER half of the same seam, and the one that cost a batch of real numbers. Being
        # drawable and stageable is worth nothing if the GRADER then reads a different answer key:
        # `parse_verdict` derives gold from supporting passages and falls back to ACCURATE when
        # there are none, which is exactly backwards for the two classes defined by having none.
        # S24 readmitted them here without updating that. Asserts agreement over the WHOLE pool,
        # not a sample, because the disagreement is confined to ~18% of it.
        ("every pool unit's gold agrees between the draw (`gold_labels`) and the grader "
         "(`parse_verdict.canonical_gold_label`) -- one answer key, not two",
         _gold_disagreements == []),
        ("...and the check actually reaches the recovered classes, so it could have failed",
         _gold_checked_recovered >= 40),
    ]

    # -- PRECISION CONTROL for the recovery join ------------------------------------------------
    # `recovered_gold` invents gold labels for claims the benchmark file does not label, by
    # matching claim text to a per-citation annotation. That is a heuristic, and a heuristic that
    # mislabels gold poisons every number downstream -- so it is controlled, not trusted.
    #
    # The control runs the SAME `join_label` the recovery uses against the dev rows whose gold is
    # already known from their own evidence annotations, and requires it to never disagree. It is
    # allowed to return None (no match) -- incompleteness costs coverage, a wrong label costs
    # correctness, and only one of those is acceptable. Measured 2026-09-07: 235 agree, 0 disagree.
    from parse_verdict import gold_paper_label  # noqa: PLC0415

    _by_bucket = _annotations_by_bucket("dev")
    _agree = _disagree = 0
    for _row in stage_claim.load_claims("dev"):
        _ev = {k: v for k, v in (_row.get("evidence") or {}).items() if v}
        if not _ev:
            continue
        _known = gold_paper_label(_ev)
        _got = join_label(_row.get("claim"), int(next(iter(_ev))) // 1000, _by_bucket)
        if _got is None:
            continue
        if _got == _known:
            _agree += 1
        else:
            _disagree += 1

    checks += [
        ("the recovery join NEVER disagrees with gold that is already known -- a wrong label "
         "would poison every number downstream, so precision is the property that matters",
         _disagree == 0),
        ("...and it matches often enough to be worth having (>200 of the 255 known-gold rows)",
         _agree > 200),
        # The default is the decision, and it INVERTED on 2026-09-07 when the objective became
        # accuracy. Accuracy is a population quantity, so the draw has to look like the population;
        # a stratified VAL measures accuracy on a population that does not exist and is not
        # comparable to the 0.595 do-nothing floor. Stratifying stays available for per-class work.
        ("VAL does NOT stratify by default -- accuracy is a population quantity",
         inspect.signature(val_inputs_for).parameters["stratify"].default is False),
    ]

    # -- S24: the default reproduces the population, and the alternative demonstrably does not ----
    # Run against the REAL dev pool and the REAL draw path (`resolve_batch(pool=None)`, which is
    # exactly what `val_inputs_for(stratify=False)` calls), not a re-implementation of the sample.
    # The stratified draw is the negative control: if both draws tracked the population, the
    # default would be cosmetic and this gate would be worth nothing.
    _dev_gold = gold_labels("dev")
    _dev_pool = claim_pool("dev")
    _n_val = 140

    def _accurate_share(units) -> float:
        got = [_dev_gold.get((u.claim_row_id, u.paper_bucket)) for u in units]
        got = [g for g in got if g is not None]
        return sum(1 for g in got if g == "ACCURATE") / len(got) if got else 0.0

    _population_share = _accurate_share(_dev_pool)
    with tempfile.TemporaryDirectory() as tmp:
        _unstrat = resolve_batch(
            0, n=_n_val, mode="fresh", split="dev",
            history_path=pathlib.Path(tmp) / "draws.json", pool=None,
        )
    _strat = stratified_draw(_dev_pool, _dev_gold, _n_val, seed=SEED)

    # +/- 0.08 is ~2 standard errors of a p=0.6 share at n=140 (se = 0.041), so this is "within
    # sampling error" stated as a number rather than as a hope.
    _tol = 0.08
    checks += [
        ("the dev pool really is ~59.5% ACCURATE -- the do-nothing floor the objective quotes",
         abs(_population_share - 0.595) < 0.01),
        ("the DEFAULT (unstratified) VAL draw reproduces the population's ACCURATE share",
         abs(_accurate_share(_unstrat) - _population_share) < _tol),
        ("...while the stratified draw does NOT -- which is why it is no longer the default",
         abs(_accurate_share(_strat) - _population_share) >= _tol),
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
