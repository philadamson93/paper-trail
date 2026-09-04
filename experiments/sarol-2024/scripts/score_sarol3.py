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
* **3-way micro-F1 is reported but MUST NOT be the objective.** For single-label multiclass it
  equals accuracy, and with ACCURATE at 78.1% of gold an always-ACCURATE program scores 0.781 --
  beating both published baselines while doing nothing. `--selftest` pins this so nobody adopts it
  by accident.
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


#: The classes the objective is computed over: the ones the held-out split can actually measure.
#:
#: Not a preference. Over the drawable dev pool (255 claims) the 9-way gold distribution is
#: ACCURATE 185, NOT_SUBSTANTIATE 25, CONTRADICT 22, OVERSIMPLIFY 8, MISQUOTE 6, INDIRECT 6,
#: ETIQUETTE 3, INDIRECT_NOT_REVIEW 0, IRRELEVANT 0. Two classes have NO gold instance anywhere in
#: dev, so raw macro-9 caps a *perfect* program at 7/9 = 0.778; and ETIQUETTE's support of 3 means
#: one claim flipping moves a macro-7 by ~0.06, which is noise to hill-climb on. The six below are
#: every class with dev support >= 6.
#:
#: Why not 3-way (the previous objective): its IRRELEVANT bucket has support **3** in the entire
#: dev pool, so a third of the number rested on three claims -- which is why no run ever predicted
#: it and ~1/3 of the metric sat pinned at zero. It also collapses five classes into NOT_ACCURATE,
#: making every confusion among 26% of dev cost exactly nothing. 3-way is still reported, because
#: the published baselines (MultiVerS 0.52, GPT-4 4-shot 0.45) are on that axis.
#:
#: Why not micro: micro == accuracy for single-label multiclass, and a program that always answers
#: ACCURATE and does no work scores **0.725** on dev. The measured program scores 0.784, so the
#: entire competence of the pipeline is ~6 points on top of a free 72.5-point floor -- and the
#: cheapest way to climb inside that band is to say ACCURATE more, which walks toward the
#: degenerate program. Reported, never optimized.
OBJECTIVE_CLASSES = (
    "ACCURATE",
    "NOT_SUBSTANTIATE",
    "CONTRADICT",
    "OVERSIMPLIFY",
    "MISQUOTE",
    "INDIRECT",
)

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

    objective_present = [c for c in OBJECTIVE_CLASSES if support_9.get(c, 0) > 0]
    objective_macro = (
        sum(per_class_9[c] for c in objective_present) / len(objective_present)
        if objective_present
        else 0.0
    )

    return {
        # The frontier scalar: 9-way-resolution macro-F1 over the classes the held-out split can
        # measure, renormalised over those present in this batch. See OBJECTIVE_CLASSES.
        "primary_metric": objective_macro,
        "objective_class_set": list(OBJECTIVE_CLASSES),
        "objective_classes_present": objective_present,
        "n_objective_classes_present": len(objective_present),
        # The published-comparability axis, reported not optimised: MultiVerS 0.52, GPT-4 0.45.
        "macro_f1_3way": sum(per_class.values()) / len(BUCKETS),
        # Reported only. See the module docstring: micro == accuracy here and is gameable.
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
    _DEV_GOLD = {"ACCURATE": 185, "NOT_SUBSTANTIATE": 25, "CONTRADICT": 22, "OVERSIMPLIFY": 8,
                 "MISQUOTE": 6, "INDIRECT": 6, "ETIQUETTE": 3}
    _dev_nothing = score(
        [("ACCURATE", g) for g, n in _DEV_GOLD.items() for _ in range(n)]
    )
    _two_class_perfect = score([("ACCURATE", "ACCURATE"), ("CONTRADICT", "CONTRADICT")])
    invalid = score([("NOT_A_LABEL", "ACCURATE"), ("ACCURATE", "ACCURATE")])
    # the two labels the mainline-plus-collapse path could not tell apart
    split = score([("INDIRECT", "INDIRECT"), ("INDIRECT_NOT_REVIEW", "INDIRECT_NOT_REVIEW")])

    checks = [
        ("do-nothing micro_f1 is degenerate (== majority share)", round(r["micro_f1"], 3) == 0.781),
        ("do-nothing 3-way macro is near-worthless", round(r["macro_f1_3way"], 3) == 0.292),
        # 0.438 not 0.140 because THIS fixture carries only two objective classes (ACCURATE and
        # OVERSIMPLIFY), so renormalising divides by 2. The real dev distribution is asserted
        # separately below -- that is the number the objective choice actually rests on.
        ("do-nothing objective is well under micro on this fixture too",
         round(r["primary_metric"], 3) == 0.439),
        ("primary_metric < micro_f1 (micro would have been gameable)",
         r["primary_metric"] < r["micro_f1"]),
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
        ("on real dev, a do-nothing program scores ~0.14 on the objective -- so the metric has "
         "room to hill-climb in", round(_dev_nothing["primary_metric"], 2) == 0.14),
        ("...while scoring 0.726 on MICRO, which is why micro is not the objective: the whole "
         "pipeline is worth ~6 points on top of that free floor",
         0.72 < _dev_nothing["micro_f1"] < 0.73),
        ("...and 0.28 on 3-way, whose IRRELEVANT third rests on 3 dev claims",
         round(_dev_nothing["macro_f1_3way"], 2) == 0.28),
        ("the objective covers the six classes dev can measure, and excludes the three it "
         "cannot -- two have zero dev gold, one has support 3",
         set(OBJECTIVE_CLASSES) == {"ACCURATE", "NOT_SUBSTANTIATE", "CONTRADICT",
                                     "OVERSIMPLIFY", "MISQUOTE", "INDIRECT"}
         and not ({"ETIQUETTE", "INDIRECT_NOT_REVIEW", "IRRELEVANT"} & set(OBJECTIVE_CLASSES))),
        ("a batch missing an objective class is NOT capped for it -- renormalising over present "
         "classes is what makes 9-way resolution usable at all",
         _two_class_perfect["primary_metric"] == 1.0
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
