"""Sarol's claim pool, gold and staging, as the engine's data-schedule source.

**The draw lives in the engine now** (`agentic-label-opt` `engine.schedule`, plan
`planning/paper-trail/2026-10-08-paper-trail-adopts-data-schedule.md`): TRAIN grows on a size curve and
retires claims answered right twice in a row, VAL grows nested inside Dev, and the best version is
re-graded when VAL grows. This module keeps only what is Sarol-specific -- which `(claim, cited paper)`
units exist, their gold, and staging a set of them into the batch file the Runner reads -- and hands the
first two to the engine as :class:`SarolScheduleSource` (``pool``, ``stage``). The old graduated-N draw
(cumulative / fresh / reproduce, ``draw_history.json``) was deleted with it; the engine's ledger
(``schedule_state.json``) replaces the history.

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
import functools
import json
import os
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

#: The seed the pre-schedule draws used (``random.Random(SEED + iteration)``). Kept because the legacy
#: 50-claim VAL roster (:func:`legacy_val50_roster`) is that draw's iteration 0, and because the engine's
#: schedule takes this as its seed too, so one number names every paper-trail draw.
SEED = 20260902

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


#: The legacy VAL roster's fingerprint: md5 of ``",".join(sorted(claim_ids))``, first 8 hex. The roster is
#: the 50 Dev claims every run before the schedule scored (v8, v13, the gxl card); `baseline_gxl_verify`
#: carries the same value.
LEGACY_VAL50_MD5 = "8e73ac3e"


def legacy_val50_roster() -> list[str]:
    """The 50 Dev claim ids every pre-schedule run scored, sorted.

    Recomputed rather than read from a run folder, so it exists on every machine: it was the old draw's
    iteration 0 in ``fresh`` mode, ``random.Random(SEED).sample(claim_pool("dev"), 50)``. The schedule
    puts these first (``val_first``), so size-50 scores stay comparable with v8, v13 and the gxl card.
    Refuses if the pool has moved and the recomputation no longer matches the fingerprint."""
    import hashlib  # noqa: PLC0415

    ids = sorted(u.claim_id for u in random.Random(SEED).sample(claim_pool("dev"), 50))
    md5 = hashlib.md5(",".join(ids).encode()).hexdigest()[:8]
    if md5 != LEGACY_VAL50_MD5:
        raise ValueError(
            f"the legacy 50-claim VAL roster no longer recomputes (md5 {md5}, expected {LEGACY_VAL50_MD5}): "
            "the Dev pool changed, so the first VAL rung would not be the claims v8, v13 and gxl were scored on"
        )
    return ids


#: The benchmark split behind each engine split. VAL is drawn from Dev; Test stays sealed.
SCHEDULE_SPLITS = {"train": "train", "val": "dev"}


class SarolScheduleSource:
    """The engine's ``ScheduleSource`` (``pool``, ``stage``) for Sarol.

    Ids are ``ClaimUnit.claim_id`` (``"<row>-<bucket>"``): structure, not verdicts. Each split stages
    under its **own** root -- ``roots["train"]`` beside the TRAIN outputs the optimizer may read,
    ``roots["val"]`` beside the VAL outputs it may not (C6.9) -- as ``<root>/staging/<claim_id>`` and
    ``<root>/batches/<label>.json``. ``stage`` checks the batch file holds exactly the claims asked for,
    reading it back through the Runner's own reader (:func:`assert_staged_size`)."""

    def __init__(self, *, roots: "dict[str, pathlib.Path]", source_mode: str = "corpus") -> None:
        if set(roots) != set(SCHEDULE_SPLITS):
            raise ValueError(f"roots must name exactly {sorted(SCHEDULE_SPLITS)}, got {sorted(roots)}")
        self.roots = {k: pathlib.Path(v) for k, v in roots.items()}
        self.source_mode = source_mode
        self._units: dict[str, dict[str, ClaimUnit]] = {}

    def _by_id(self, split: str) -> "dict[str, ClaimUnit]":
        if split not in SCHEDULE_SPLITS:
            raise ValueError(f"split must be one of {sorted(SCHEDULE_SPLITS)}, got {split!r}")
        if split not in self._units:
            self._units[split] = {u.claim_id: u for u in claim_pool(SCHEDULE_SPLITS[split])}
        return self._units[split]

    def pool(self, split: str) -> list[str]:
        return sorted(self._by_id(split))

    def stage(self, ids, split: str, label: str):
        from adapter import _import_engine  # noqa: PLC0415 -- engine is optional at import time

        schemas = _import_engine()
        by_id = self._by_id(split)
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise ValueError(f"{len(missing)} {split} id(s) are not in the {SCHEDULE_SPLITS[split]} pool")
        units = sorted((by_id[i] for i in ids), key=lambda u: (u.claim_row_id, u.paper_bucket))
        root = self.roots[split]
        batch_path = root / "batches" / f"{label}.json"
        stage_batch(units, split=SCHEDULE_SPLITS[split], staging_root=root / "staging",
                    batch_path=batch_path, source_mode=self.source_mode)
        assert_staged_size(batch_path, len(units), label=f"{split} batch {label}")
        return schemas.RunInputs(input_ref=str(batch_path), batch_id=label, split=split)


def _selftest() -> int:
    import tempfile

    checks: list[tuple[str, bool]] = []

    # The real-staging assertions below call `stage_claim.stage`, which WRITES a gold vector under
    # its gold root. Where that root is not writable the two staging checks fail for a reason that
    # has nothing to do with sampling -- an undeclared write precondition, found when an audit ran
    # in a read-only sandbox and measured 48/50 instead of 50/50.
    # ⚠ Setting PAPER_TRAIL_GOLD_DIR here is TOO LATE: `stage_claim.GOLD_ROOT` is evaluated at
    # import time (stage_claim.py:55) and this module imports stage_claim at :62. So override the
    # resolved constant, which is explicit and does not depend on import order.
    stage_claim.GOLD_ROOT = pathlib.Path(tempfile.mkdtemp(prefix="sampling-gold-")) / "sarol-2024"
    stage_claim.GOLD_ROOT.mkdir(parents=True, exist_ok=True)

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

    # -- the engine's schedule source (plan 2026-10-08) ------------------------------------------
    # The draw itself is the engine's and is tested there; what crosses the seam is tested here: the
    # pools the engine is handed, the batch files it gets back, and where each split is staged.
    from adapter import _import_engine  # noqa: PLC0415

    _import_engine()
    from engine.schedule import ScheduleError, check_example_ids, val_order  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        _roots = {"train": pathlib.Path(tmp) / "train-side", "val": pathlib.Path(tmp) / "val-side"}
        _src = SarolScheduleSource(roots=_roots)
        _tp, _vp = _src.pool("train"), _src.pool("val")
        try:
            check_example_ids(_tp + _vp)
            _ids_safe = True
        except ScheduleError:
            _ids_safe = False
        _pick = _vp[:3]
        _inputs = _src.stage(_pick, "val", "probe-val-n3")
        _staged = json.loads(pathlib.Path(_inputs.input_ref).read_text(encoding="utf-8"))["claims"]
        checks += [
            ("the schedule source's TRAIN pool is the stageable TRAIN units, sorted and unique",
             _tp == sorted(set(_tp)) and len(_tp) == len(claim_pool("train"))),
            ("...its VAL pool is Dev's (311 usable), never Test's",
             _vp == sorted(u.claim_id for u in claim_pool("dev"))),
            ("...the two pools share no claim, which the engine also refuses",
             not set(_tp) & set(_vp)),
            ("...and every id is one the engine accepts (a safe path segment)", _ids_safe),
            ("stage() hands back RunInputs with the split and the engine's label, as the engine checks",
             _inputs.split == "val" and _inputs.batch_id == "probe-val-n3"),
            ("...over exactly the claims asked for, read back from the batch file",
             sorted(c["claim_id"] for c in _staged) == sorted(_pick)),
            ("...staged under the VAL root, never beside TRAIN (C6.9)",
             all(pathlib.Path(c["staging_dir"]).is_relative_to(_roots["val"]) for c in _staged)
             and not _roots["train"].exists()),
            ("stage() refuses an id that is not in the pool rather than staging a stranger",
             _raises(lambda: _src.stage(["999999-1"], "val", "x"), ValueError)),
            ("a source with no VAL root is refused at construction",
             _raises(lambda: SarolScheduleSource(roots={"train": pathlib.Path(tmp)}), ValueError)),
        ]

    # -- the legacy 50-claim VAL roster is the first rung ----------------------------------------
    _legacy = legacy_val50_roster()
    # The recomputation against the file the old code wrote at the time (09-22), where this machine has
    # it: independent of this module's own arithmetic. Absent (a VM), the md5 gate inside the helper stands.
    _hist = pathlib.Path.home() / ".paper-trail" / "runs" / "hillclimb-2026-09-22c" / "val" / "val_draw.json"
    _hist_ok = (sorted(json.loads(_hist.read_text(encoding="utf-8"))["0"]) == _legacy) if _hist.exists() else None
    _order = val_order(_src.pool("val"), seed=SEED, val_first=_legacy)
    _sizes = (50, 100, 150, 250, 311)
    checks += [
        ("the legacy roster recomputes to the 50 claims v8, v13 and gxl were scored on (md5 8e73ac3e)",
         len(_legacy) == 50 and len(set(_legacy)) == 50),
        ("...every one of them a Dev pool claim", set(_legacy) <= set(_src.pool("val"))),
        ("...and equal to the roster file the old draw wrote on 2026-09-22"
         + (" (file absent here: checked by md5 only)" if _hist_ok is None else ""),
         _hist_ok is not False),
        ("with it as val_first, the engine's VAL at size 50 IS the legacy roster",
         sorted(_order[:50]) == _legacy),
        ("...and each larger VAL contains the one before (nested, never a fresh sample)",
         all(set(_order[:a]) <= set(_order[:b]) for a, b in zip(_sizes, _sizes[1:]))),
        ("...reaching the whole Dev pool at 311", sorted(_order[:311]) == _src.pool("val")),
    ]

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
    ]

    # -- S24: the default reproduces the population, and the alternative demonstrably does not ----
    # Run against the REAL dev pool and the REAL draw path (the engine's `val_order`, which is how the
    # schedule orders VAL), not a re-implementation of the sample.
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
    # The engine's VAL order with no val_first: the random part of every VAL beyond the legacy 50.
    _by_cid = {u.claim_id: u for u in _dev_pool}
    _unstrat = [_by_cid[c] for c in val_order(sorted(_by_cid), seed=SEED)[:_n_val]]
    _strat = stratified_draw(_dev_pool, _dev_gold, _n_val, seed=SEED)

    # +/- 0.08 is ~2 standard errors of a p=0.6 share at n=140 (se = 0.041), so this is "within
    # sampling error" stated as a number rather than as a hope.
    _tol = 0.08
    checks += [
        ("the dev pool really is ~59.5% ACCURATE -- the do-nothing floor the objective quotes",
         abs(_population_share - 0.595) < 0.01),
        ("the schedule's VAL order (unstratified) reproduces the population's ACCURATE share",
         abs(_accurate_share(_unstrat) - _population_share) < _tol),
        ("...while the stratified draw does NOT -- which is why it is no longer the default",
         abs(_accurate_share(_strat) - _population_share) >= _tol),
    ]

    checks.append(("a unit's claim_id carries both row and bucket, so two buckets of one claim "
                   "never collide", ClaimUnit(7, 31).claim_id == "7-31"))

    # Every remaining importer of this module still loads now that the old draw is gone (plan
    # 2026-10-08). In a fresh interpreter, so a name deleted here can't hide behind one this process
    # already imported.
    import subprocess  # noqa: PLC0415

    _importers = ("canary", "run_baseline", "baseline_gxl_verify", "parse_verdict", "dispatcher")
    _probe = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path[:0] = sys.argv[1:3]; "
         + "; ".join(f"import {m}" for m in _importers), str(_HERE), str(_SCRIPTS)],
        capture_output=True, text=True,
    )
    checks.append((f"every remaining importer of sampling.py still loads ({', '.join(_importers)})",
                   _probe.returncode == 0))

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
