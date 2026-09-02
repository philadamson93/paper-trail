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

    return {
        # Every class is reachable under this variant, so the frontier scalar is the full 3-way
        # macro-F1 -- the axis the published baselines report.
        "primary_metric": sum(per_class.values()) / len(BUCKETS),
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
    invalid = score([("NOT_A_LABEL", "ACCURATE"), ("ACCURATE", "ACCURATE")])
    # the two labels the mainline-plus-collapse path could not tell apart
    split = score([("INDIRECT", "INDIRECT"), ("INDIRECT_NOT_REVIEW", "INDIRECT_NOT_REVIEW")])

    checks = [
        ("do-nothing micro_f1 is degenerate (== majority share)", round(r["micro_f1"], 3) == 0.781),
        ("do-nothing primary_metric is near-worthless", round(r["primary_metric"], 3) == 0.292),
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
         r["macro_f1_9way"] < r["primary_metric"]),
        ("...roughly a tenth, not a third", round(r["macro_f1_9way"], 3) == 0.097),
        # The sample-size hazard, made concrete: macro-9 always divides by 9, so a batch whose
        # gold covers 3 classes caps at 3/9 even with flawless predictions. This is why 9-way is
        # a breakdown and not the frontier at VAL=316.
        ("macro-9 caps at classes_present/9 -- a property of the sample, not the program",
         round(perfect["macro_f1_9way"], 4) == round(3 / 9, 4)),
        ("...and perfect 3-way on the same batch is a clean 1.0", perfect["primary_metric"] == 1.0),
        ("support is reported so the cap is visible rather than mysterious",
         perfect["n_classes_present_9way"] == 3
         and sum(perfect["support_9way"].values()) == 3),
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
