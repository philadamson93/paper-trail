"""Score Sarol-variant predictions: 9-class labels -> Sarol's 3-way buckets -> metrics.

The optimized program under OQ1 emits **Sarol's own 9-class enum directly**
(`experiments/sarol-2024/specs/verdict_schema_sarol.md`), so there is no lossy bridge between
paper-trail's vocabulary and the benchmark's: every gold label is reachable and 3-way macro-F1 is
directly comparable to the published baselines (MultiVerS 0.52 macro, GPT-4 4-shot 0.45 macro).

The enum and the 9->3 collapse are **not redefined here** -- they are imported from
`parse_verdict.py`, which owns them. This module adds only the metrics layer, which did not exist
anywhere. It touches **no gold**: callers pass in already-resolved gold buckets, so the sealed-split
boundary (Part C3) stays where `parse_verdict.py` puts it.

Two design points worth not re-deriving (see the plan's Part A2):

* **The output vocabulary is a fixed contract, the rubric's guidance is not.** The optimizer may
  edit every part of the rubric that makes it good -- definitions, boundaries, worked examples,
  tie-breaks, the worst-wins ordering -- but not the set of emittable labels, because the benchmark
  defines it and this scorer consumes it. A label outside `SAROL_9` is an ordinary invalid output:
  scored as a miss and counted in `error_class_counts`. It never crashes the run and is never
  silently re-bucketed, so a bad edit simply scores worse and the loop rejects it on its own.
* **The objective is accuracy over the nine labels, and it is quoted against a floor.** A claim
  counts only if the predicted label equals the gold label; `micro_f1` is the same quantity
  computed AFTER the 3-way collapse, so it forgives every confusion inside NOT_ACCURATE and is a
  diagnostic, not the objective. Accuracy is dominated by the ACCURATE base rate -- an
  always-ACCURATE program scores 0.595 on the repaired dev pool -- so `do_nothing_floor` is
  computed from each batch's own gold and reported beside it. Compare against the floor, never
  against zero. `macro_f1_renormalised` is kept as the diagnostic that catches the one degenerate
  strategy accuracy admits: collapsing toward ACCURATE raises accuracy and craters macro.
  `--selftest` pins all of this, in both directions.

  *(History, so it is not re-litigated: the objective was 3-way macro-F1, then macro-F1
  renormalised over the classes present. The renormalising denominator moved between batches,
  which manufactured a -0.15 TRAIN "decline" across three iterations for a program that never
  changed. Accuracy has no denominator to wobble. Changed 2026-09-07.)*
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Iterable, Literal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_verdict import SAROL_9, to_3way  # noqa: E402  -- the owners of enum + collapse

Bucket = Literal["ACCURATE", "NOT_ACCURATE", "IRRELEVANT"]

#: The three scored buckets, in report order.
BUCKETS: tuple[Bucket, ...] = ("ACCURATE", "NOT_ACCURATE", "IRRELEVANT")

#: The nine emittable labels in the enum contract's own listing order. A stable order matters
#: because the 9-way breakdown is reported per class; `--selftest` pins it as a permutation of
#: `SAROL_9` so a drift in either place is caught.
SAROL_9_ORDER: tuple[str, ...] = (
    "ACCURATE",
    "OVERSIMPLIFY",
    "NOT_SUBSTANTIATE",
    "CONTRADICT",
    "MISQUOTE",
    "INDIRECT",
    "INDIRECT_NOT_REVIEW",
    "ETIQUETTE",
    "IRRELEVANT",
)

#: What `to_3way` returns for a label outside SAROL_9.
UNKNOWN = "UNKNOWN"


#: The classes the objective is computed over: all nine, renormalised over those present.
#:
#: This was briefly a six-class set, on the finding that dev held no gold for `IRRELEVANT` and only
#: three `ETIQUETTE`. **That finding was an artifact of our own pool filter, not the benchmark.**
#: A claim was drawable only if its cited bucket carried an *evidence annotation*, and `IRRELEVANT`
#: ("nothing in the cited paper is relevant") and `ETIQUETTE` ("unclear what is being cited") are
#: defined by the absence of evidence -- so the filter deleted exactly those two classes and
#: nothing else: 442/2141 TRAIN and 61/316 dev excluded, 100% of them ETIQUETTE or IRRELEVANT,
#: while every other class was 100% evidence-covered. See `sampling.recovered_gold`.
#:
#: With that repaired the drawable pools carry ACCURATE 1308, ETIQUETTE 264, NOT_SUBSTANTIATE 189,
#: IRRELEVANT 118, CONTRADICT 58, OVERSIMPLIFY 56, INDIRECT 35, INDIRECT_NOT_REVIEW 25, MISQUOTE 23
#: (TRAIN) and ACCURATE 185, ETIQUETTE 38, NOT_SUBSTANTIATE 25, CONTRADICT 22, IRRELEVANT 21,
#: OVERSIMPLIFY 8, MISQUOTE 6, INDIRECT 6 (dev). Every class dev holds has support >= 6; only
#: `INDIRECT_NOT_REVIEW` is genuinely absent there, and renormalisation drops it automatically.
#:
#: Why the macro diagnostic renormalises rather than dividing by nine: a fixed denominator caps a
#: *perfect* program at classes_present/9 -- 8/9 on full dev -- which is a property of the sample,
#: not the program. The cost is that the denominator varies between batches, so
#: `n_objective_classes_present` is reported beside it and MUST be read with it. That wobble is
#: precisely why this is no longer the frontier: it made a constant program look like it was
#: declining. VAL is drawn once and held per run.
#:
#: Why not 3-way: it collapses five classes into NOT_ACCURATE, so confusions among 26% of dev cost
#: nothing, and its IRRELEVANT bucket rested on the same handful of claims the filter was deleting.
#: Still reported as `macro_f1_3way` for the published baselines (MultiVerS 0.52, GPT-4 0.45).
#:
#: ⚠ **This set no longer defines the objective** -- since 2026-09-07 the objective is plain
#: accuracy over the nine labels, which needs no class set. It defines the renormalised macro
#: kept as a DIAGNOSTIC (`macro_f1_renormalised`), and it is what `sampling.stratified_draw`
#: spreads a draw across when a per-class question is being asked. The renormalisation rationale
#: above still applies to that diagnostic; it no longer applies to the frontier.
OBJECTIVE_CLASSES = SAROL_9_ORDER

#: The objective renormalises over the objective classes PRESENT in the batch, rather than dividing
#: by a fixed 6. Dividing by a constant would make a batch that happens to draw no MISQUOTE cap at
#: 5/6 through no fault of the program -- the exact ceiling artifact that made raw macro-9
#: unusable. The cost of renormalising is that the denominator varies between batches, so
#: `objective_classes_present` is reported beside every number and MUST be read with it. VAL is
#: drawn once and held for a run, so its denominator is stable across the frontier being compared.


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall)


def _nine_way(pairs: list[tuple[str, str]]) -> tuple[dict[str, float], dict[str, int]]:
    """Per-class F1 and gold support over the full 9-class enum.

    Reported alongside the 3-way frontier, never optimized against -- see the module docstring and
    the plan's Open Questions 5. A prediction outside `SAROL_9` is a false negative for its gold
    class and contributes to no class's false positives, matching the 3-way treatment.

    **Read `support` before reading the F1s.** Macro-F1 here always divides by 9, so a batch whose
    gold covers only 3 of the classes caps at 3/9 = 0.333 no matter how perfect the predictions.
    That is a property of the sample, not of the program, and it is exactly why 9-way is a
    breakdown rather than the frontier at VAL=316.
    """
    tp = {c: 0 for c in SAROL_9_ORDER}
    fp = {c: 0 for c in SAROL_9_ORDER}
    fn = {c: 0 for c in SAROL_9_ORDER}
    for predicted_label, gold_label in pairs:
        if gold_label not in tp:
            raise ValueError(f"gold label {gold_label!r} is not in the Sarol 9-class enum")
        if predicted_label == gold_label:
            tp[gold_label] += 1
        else:
            fn[gold_label] += 1
            if predicted_label in fp:
                fp[predicted_label] += 1
    per_class = {c: _f1(tp[c], fp[c], fn[c]) for c in SAROL_9_ORDER}
    support = {c: tp[c] + fn[c] for c in SAROL_9_ORDER}
    return per_class, support


def score(pairs: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Score ``(predicted_9class_label, gold_9class_label)`` pairs.

    Both sides are collapsed with `parse_verdict.to_3way`. A predicted label outside `SAROL_9`
    collapses to ``UNKNOWN`` and is charged as a false negative against its gold class -- a miss,
    not an error, so an optimizer edit that invents a label just scores worse.
    """
    pairs = list(pairs)  # consumed twice: once for the 3-way collapse, once for the 9-way breakdown
    confusion = {g: {p: 0 for p in BUCKETS} for g in BUCKETS}
    invalid_by_gold = {g: 0 for g in BUCKETS}
    error_class_counts: dict[str, int] = {}
    total = 0

    for predicted_label, gold_label in pairs:
        gold = to_3way(gold_label)
        if gold not in confusion:
            raise ValueError(f"gold label {gold_label!r} does not collapse to a scored bucket")
        total += 1
        if predicted_label not in SAROL_9:
            invalid_by_gold[gold] += 1
            error_class_counts["invalid_label"] = error_class_counts.get("invalid_label", 0) + 1
            error_class_counts[f"invalid_label:{predicted_label}"] = (
                error_class_counts.get(f"invalid_label:{predicted_label}", 0) + 1
            )
            continue
        confusion[gold][to_3way(predicted_label)] += 1

    per_class: dict[str, float] = {}
    for c in BUCKETS:
        tp = confusion[c][c]
        fp = sum(confusion[g][c] for g in BUCKETS if g != c)
        fn = sum(confusion[c][p] for p in BUCKETS if p != c) + invalid_by_gold[c]
        per_class[c] = _f1(tp, fp, fn)

    scored = sum(confusion[g][p] for g in BUCKETS for p in BUCKETS)
    correct = sum(confusion[c][c] for c in BUCKETS)

    per_class_9, support_9 = _nine_way(pairs)

    # THE OBJECTIVE: 9-class accuracy. A claim counts only if the predicted label equals the gold
    # label -- not if their 3-way buckets happen to agree. Five of the nine collapse into
    # NOT_ACCURATE, so a 3-way accuracy would treat the rubric's hardest discrimination as free.
    # An invalid label can never equal a gold label, so this shares `scored`'s denominator.
    correct_9 = sum(1 for predicted, gold in pairs if predicted == gold)

    # The do-nothing floor, computed FROM THIS BATCH so it is never quoted from a stale fixture.
    # A program that always answers ACCURATE and does no work scores exactly this. Denominator is
    # `n_total`, because that program emits no invalid labels and so scores every claim.
    n_gold_accurate = support_9.get("ACCURATE", 0)
    do_nothing_floor = n_gold_accurate / total if total else 0.0

    objective_present = [c for c in OBJECTIVE_CLASSES if support_9.get(c, 0) > 0]
    objective_macro = (
        sum(per_class_9[c] for c in objective_present) / len(objective_present)
        if objective_present
        else 0.0
    )

    return {
        # The frontier scalar: overall 9-class accuracy on this batch.
        "primary_metric": correct_9 / scored if scored else 0.0,
        # Quoted BESIDE it, always. Accuracy is dominated by the ACCURATE base rate, so the
        # comparison that means anything is against this number, never against zero.
        "do_nothing_floor": do_nothing_floor,
        "n_correct_9way": correct_9,
        # The diagnostic, not the objective (it WAS `primary_metric` until 2026-09-07): macro-F1
        # at 9-way resolution, renormalised over the classes present. Read it to see whether an
        # accuracy gain came from getting the rare classes right or from collapsing toward
        # ACCURATE -- a collapse raises accuracy and craters this.
        "macro_f1_renormalised": objective_macro,
        "objective_class_set": list(OBJECTIVE_CLASSES),
        "objective_classes_present": objective_present,
        "n_objective_classes_present": len(objective_present),
        # The published-comparability axis, reported not optimised: MultiVerS 0.52, GPT-4 0.45.
        "macro_f1_3way": sum(per_class.values()) / len(BUCKETS),
        # 3-WAY accuracy -- the same quantity as `primary_metric` but computed after the collapse,
        # so it forgives every within-bucket confusion. Reported as a diagnostic: the gap between
        # this and `primary_metric` IS the mass of the confusions inside NOT_ACCURATE.
        "micro_f1": correct / scored if scored else 0.0,
        "per_class_f1": per_class,
        "confusion_matrix": {g: dict(confusion[g]) for g in BUCKETS},
        # Reported only, never optimized against (plan Open Questions 5). Always read
        # `support_9way` alongside these: macro_f1_9way divides by 9 regardless of how many
        # classes the batch's gold actually covers.
        "macro_f1_9way": sum(per_class_9.values()) / len(SAROL_9_ORDER),
        "per_class_f1_9way": per_class_9,
        "support_9way": support_9,
        "n_classes_present_9way": sum(1 for c in SAROL_9_ORDER if support_9[c] > 0),
        "error_class_counts": error_class_counts,
        "n_total": total,
        "n_scored": scored,
        "n_invalid": total - scored,
    }


def _selftest() -> int:
    gold_dist = {"ACCURATE": 1463, "NOT_ACCURATE": 376, "IRRELEVANT": 34}
    # gold 9-class labels that collapse into each bucket
    rep = {"ACCURATE": "ACCURATE", "NOT_ACCURATE": "OVERSIMPLIFY", "IRRELEVANT": "ETIQUETTE"}
    do_nothing = [("ACCURATE", rep[b]) for b, n in gold_dist.items() for _ in range(n)]
    r = score(do_nothing)

    perfect = score([(rep[b], rep[b]) for b in BUCKETS])

    # The measured 9-way gold distribution of the drawable dev pool (255 of 316; a claim whose
    # cited bucket carries no evidence annotation has no gold label and is refused at staging).
    # The REPAIRED drawable dev pool (311 of 316). Before `sampling.recovered_gold`, the
    # evidence-annotation rule deleted 61 rows that were 100% ETIQUETTE (37) and IRRELEVANT (24),
    # which is what made those classes look unmeasurable and forced a six-class objective.
    _DEV_GOLD = {"ACCURATE": 185, "ETIQUETTE": 38, "NOT_SUBSTANTIATE": 25, "CONTRADICT": 22,
                 "IRRELEVANT": 21, "OVERSIMPLIFY": 8, "MISQUOTE": 6, "INDIRECT": 6}
    _dev_nothing = score(
        [("ACCURATE", g) for g, n in _DEV_GOLD.items() for _ in range(n)]
    )
    _two_class_perfect = score([("ACCURATE", "ACCURATE"), ("CONTRADICT", "CONTRADICT")])
    invalid = score([("NOT_A_LABEL", "ACCURATE"), ("ACCURATE", "ACCURATE")])
    # One within-bucket confusion and one hit. 3-way accuracy sees 2/2; 9-way sees 1/2. This is
    # the fixture the objective choice turns on, so it is asserted in both directions below.
    within = score([("CONTRADICT", "OVERSIMPLIFY"), ("ACCURATE", "ACCURATE")])
    # the two labels the mainline-plus-collapse path could not tell apart
    split = score([("INDIRECT", "INDIRECT"), ("INDIRECT_NOT_REVIEW", "INDIRECT_NOT_REVIEW")])

    checks = [
        # -- the objective is ACCURACY (2026-09-07). These four replace the four that asserted
        # the opposite; each is written so that switching the objective back turns it RED.
        ("a do-nothing program scores exactly the do-nothing floor -- that is what makes the "
         "floor the number to compare against",
         round(r["primary_metric"], 6) == round(r["do_nothing_floor"], 6)),
        ("...and the floor is REPORTED, not left for the reader to remember",
         "do_nothing_floor" in r and round(r["do_nothing_floor"], 3) == 0.781),
        ("primary_metric is accuracy over the NINE labels, so it can never exceed the 3-way "
         "accuracy that forgives within-bucket confusions",
         r["primary_metric"] <= r["micro_f1"] and within["primary_metric"] < within["micro_f1"]),
        ("...which is the whole point: a CONTRADICT answered for an OVERSIMPLIFY is WRONG, "
         "though both collapse to NOT_ACCURATE and 3-way accuracy calls it right",
         within["primary_metric"] == 0.5 and within["micro_f1"] == 1.0),
        ("the renormalised macro survives as a DIAGNOSTIC, so a gain bought by collapsing "
         "toward ACCURATE is visible rather than invisible",
         round(r["macro_f1_renormalised"], 3) == 0.292),
        ("do-nothing 3-way macro is near-worthless", round(r["macro_f1_3way"], 3) == 0.292),
        ("perfect predictions score 1.0", perfect["primary_metric"] == 1.0),
        ("invalid label is a miss, not a crash", invalid["n_invalid"] == 1),
        ("invalid label is counted", invalid["error_class_counts"].get("invalid_label") == 1),
        # Both are predicted correctly and land in different buckets -- the exact pair the
        # mainline-plus-collapse path could not separate. Asserted per-class, not on macro:
        # ACCURATE is absent from this 2-pair sample so its F1 is 0 and macro would be 0.667.
        ("INDIRECT and INDIRECT_NOT_REVIEW are both reachable",
         split["per_class_f1"]["NOT_ACCURATE"] == 1.0 and split["per_class_f1"]["IRRELEVANT"] == 1.0),
        ("they land in DIFFERENT buckets", to_3way("INDIRECT") != to_3way("INDIRECT_NOT_REVIEW")),
        ("enum is the benchmark's 9", len(SAROL_9) == 9),
        # --- 9-way breakdown: reported, never optimized against (Open Questions 5) -------------
        ("the 9-way report order is a permutation of the enum", set(SAROL_9_ORDER) == SAROL_9),
        ("perfect 9-way predictions on the represented classes score 1.0 each",
         all(split["per_class_f1_9way"][c] == 1.0 for c in ("INDIRECT", "INDIRECT_NOT_REVIEW"))),
        ("9-way punishes the do-nothing program harder than 3-way",
         r["macro_f1_9way"] < r["macro_f1_3way"]),
        ("...roughly a tenth, not a third", round(r["macro_f1_9way"], 3) == 0.097),
        # The sample-size hazard, made concrete: macro-9 always divides by 9, so a batch whose
        # gold covers 3 classes caps at 3/9 even with flawless predictions. This is why 9-way is
        # a breakdown and not the frontier at VAL=316.
        ("macro-9 caps at classes_present/9 -- a property of the sample, not the program",
         round(perfect["macro_f1_9way"], 4) == round(3 / 9, 4)),
        ("...and perfect 3-way on the same batch is a clean 1.0",
         perfect["macro_f1_3way"] == 1.0),
        ("support is reported so the cap is visible rather than mysterious",
         perfect["n_classes_present_9way"] == 3
         and sum(perfect["support_9way"].values()) == 3),
        # ------------------------------------------------------------------------------------
        # The objective choice, pinned against the REAL drawable dev distribution (255 claims).
        # These are the numbers the decision was made on; if the class set or the renormalisation
        # changes, they move and this says so.
        ("on real dev, a do-nothing program scores 0.595 -- THE number to quote beside every "
         "accuracy this experiment reports",
         round(_dev_nothing["primary_metric"], 3) == 0.595),
        ("...and the scorer reports that floor itself, from the batch's own gold",
         round(_dev_nothing["do_nothing_floor"], 3) == 0.595),
        ("...the real cost of the choice, on the record: accuracy is mostly the ACCURATE base "
         "rate, so rubric work on the rare classes will barely move it",
         _dev_nothing["primary_metric"] > 0.5),
        ("...which is exactly what the macro diagnostic is kept for -- it scores the same "
         "do-nothing program at ~0.09",
         round(_dev_nothing["macro_f1_renormalised"], 2) == 0.09),
        ("...and ~0.25 on 3-way", round(_dev_nothing["macro_f1_3way"], 2) == 0.25),
        ("dev supports 8 of 9 classes once the pool filter is repaired -- only "
         "INDIRECT_NOT_REVIEW is genuinely absent there",
         _dev_nothing["n_objective_classes_present"] == 8),
        ("the objective spans all nine classes, renormalised over those present -- the earlier "
         "six-class set was an artifact of the pool filter, not of the benchmark",
         set(OBJECTIVE_CLASSES) == set(SAROL_9_ORDER)
         and {"ETIQUETTE", "IRRELEVANT"} <= set(OBJECTIVE_CLASSES)),
        ("a batch missing an objective class is NOT capped for it -- renormalising over present "
         "classes is what makes the macro DIAGNOSTIC usable at 9-way resolution",
         _two_class_perfect["macro_f1_renormalised"] == 1.0
         and _two_class_perfect["n_objective_classes_present"] == 2),
        ("...and the classes it renormalised over are reported, so two numbers with different "
         "denominators cannot be silently compared",
         _two_class_perfect["objective_classes_present"] == ["ACCURATE", "CONTRADICT"]),
        ("the do-nothing batch's gold support sums to the corpus size",
         sum(r["support_9way"].values()) == 1873),
    ]
    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run the metric regression guards")
    ap.add_argument("--pairs", type=str, default=None,
                    help='JSON file of [[predicted_label, gold_label], ...] to score')
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.pairs:
        with open(args.pairs, encoding="utf-8") as fh:
            print(json.dumps(score([(a, b) for a, b in json.load(fh)]), indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
