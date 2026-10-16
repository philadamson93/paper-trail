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
* **The objective is a run setting** (`OBJECTIVES`, 2026-10-15): accuracy over the nine labels by
  default, or 2-way macro-F1 (ACCURATE vs NOT). Either is quoted against its own do-nothing floor.
  The rest of this point describes the default.
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


#: The objectives a run can climb (plan 2026-10-15-paper-trail-2way-objective-fork). A run setting,
#: chosen once per run (`dispatcher.py --objective`, `OBJECTIVE=` in the launcher) and recorded in the
#: run's identity, so a resume can never splice two objectives into one curve.
#:
#: * ``accuracy_9class`` -- the default, and the objective since 2026-09-07: a claim counts only if the
#:   predicted label equals the gold label. Floor: the always-ACCURATE accuracy.
#: * ``macro_f1_2way`` -- both sides collapsed to ACCURATE vs NOT (every other label, ETIQUETTE /
#:   IRRELEVANT / INDIRECT_NOT_REVIEW included, is NOT); the score is macro-F1 over those two classes.
#:   Added because accuracy rewards defaulting to ACCURATE (always-ACCURATE = 0.60 on Dev) and the
#:   9-class lineage plateaued at ~0.72; an always-ACCURATE program scores ~0.37 here. The judge keeps
#:   its nine labels; only the scoring collapses.
DEFAULT_OBJECTIVE = "accuracy_9class"
OBJECTIVES: tuple[str, ...] = ("accuracy_9class", "macro_f1_2way")

#: The frontier metric's name per objective -- the name the release carries and the run-summary key
#: each version's VAL score is stored under. `adapter.PRIMARY_METRIC_NAME` is the default's.
METRIC_NAMES: dict[str, str] = {
    "accuracy_9class": "sarol_accuracy_9class",
    "macro_f1_2way": "sarol_macro_f1_2way",
}

#: The one paragraph the optimizer's standing instructions carry about the run's objective, filled
#: in per run (`sarol_optimizer.SarolOptimizer.agent_instructions`). The instructions themselves stay
#: neutral: "maximize the metric your release names, against its floor".
OBJECTIVE_DESCRIPTIONS: dict[str, str] = {
    "accuracy_9class": (
        "**This run's objective: maximize accuracy over the nine classes** -- the fraction of claims whose "
        "predicted label equals the gold label exactly, reported as `primary_metric` under the name "
        "`sarol_accuracy_9class`. A `CONTRADICT` answered for an `OVERSIMPLIFY` is a miss, though both "
        "collapse to NOT_ACCURATE. `do_nothing_floor` is the accuracy of a program that answers "
        "`ACCURATE` every time on the same batch (about 0.6 on Dev). Accuracy rewards defaulting to "
        "`ACCURATE`, so read `macro_f1_renormalised` beside it: accuracy up and macro down means the gain "
        "came from answering `ACCURATE` more often."
    ),
    "macro_f1_2way": (
        "**This run's objective: 2-way macro-F1, ACCURATE versus NOT** -- both your label and gold are "
        "collapsed to `ACCURATE` or NOT (every other label, `ETIQUETTE`, `IRRELEVANT` and "
        "`INDIRECT_NOT_REVIEW` included), and the score is the mean of the two classes' F1, reported as "
        "`primary_metric` under the name `sarol_macro_f1_2way`. A `CONTRADICT` answered "
        "`NOT_SUBSTANTIATE` is right; an `ACCURATE` answered `OVERSIMPLIFY` is wrong. A label outside "
        "the nine is a miss. `do_nothing_floor` is the 2-way macro-F1 of a program that answers "
        "`ACCURATE` every time on the same batch (about 0.37 on Dev), so defaulting to `ACCURATE` is "
        "punished here, not rewarded. You still emit the nine labels; right and wrong on TRAIN, the "
        "mistakes file and retirement all follow the 2-way collapse. Every route to a NOT label is a "
        "trade: each real problem it catches raises the score, each `ACCURATE` claim it flags lowers it. "
        "Work out the break-even from your own TRAIN `confusion_matrix_2way`: recompute the score with one "
        "more problem caught and with one more false flag, and the ratio of the two changes is how often "
        "a route must be right to pay. While missed problems outnumber false flags it is below one half, "
        "so do not tighten a route that is right more often than its break-even. Write your predictions "
        "in this objective's currency: per edit, how many TRAIN claims you expect to cross the "
        "ACCURATE/NOT line the right way and the wrong way, graded next iteration from the per-claim "
        "right/wrong."
    ),
}

#: The 2-way classes, in report order.
TWO_WAY: tuple[str, str] = ("ACCURATE", "NOT")


def check_objective(objective: str) -> str:
    """Return ``objective`` if it is one of :data:`OBJECTIVES`; raise ``ValueError`` otherwise."""
    if objective not in OBJECTIVES:
        raise ValueError(f"unknown objective {objective!r}; choose one of {', '.join(OBJECTIVES)}")
    return objective


def to_2way(label: str) -> str:
    """ACCURATE stays ACCURATE; every other Sarol label is NOT. Not defined for a non-Sarol label --
    callers treat an invalid prediction as a miss for its gold side before collapsing."""
    if label not in SAROL_9:
        raise ValueError(f"label {label!r} is not in the Sarol 9-class enum")
    return "ACCURATE" if label == "ACCURATE" else "NOT"


def is_correct(predicted_label: str, gold_label: str, objective: str = DEFAULT_OBJECTIVE) -> bool:
    """One claim's right/wrong under ``objective`` -- the single definition the score, the data
    schedule's retirement and the mistakes file all use. A prediction outside the nine is never right."""
    check_objective(objective)
    if objective == "accuracy_9class":
        return predicted_label == gold_label
    return predicted_label in SAROL_9 and to_2way(predicted_label) == to_2way(gold_label)


def _two_way(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Macro-F1 over {ACCURATE, NOT}, its always-ACCURATE floor, and the 2x2 table.

    An invalid predicted label is a false negative for its gold side and a false positive for
    neither, matching the 3-way and 9-way treatment. The macro always divides by two: a batch with
    no gold NOT caps NOT's F1 at 0, which is a property of the sample (VAL is drawn to hold both).
    """
    confusion = {g: {p: 0 for p in TWO_WAY} for g in TWO_WAY}
    invalid = {g: 0 for g in TWO_WAY}
    for predicted_label, gold_label in pairs:
        gold = to_2way(gold_label)
        if predicted_label not in SAROL_9:
            invalid[gold] += 1
        else:
            confusion[gold][to_2way(predicted_label)] += 1
    per_class = {}
    for c in TWO_WAY:
        other = "NOT" if c == "ACCURATE" else "ACCURATE"
        per_class[c] = _f1(confusion[c][c], confusion[other][c], confusion[c][other] + invalid[c])
    n_acc = sum(confusion["ACCURATE"].values()) + invalid["ACCURATE"]
    n_not = sum(confusion["NOT"].values()) + invalid["NOT"]
    # Always-ACCURATE: tp = n_acc, fp = n_not, fn = 0 for ACCURATE; NOT has tp = 0, so F1 0.
    floor = (_f1(n_acc, n_not, 0) + 0.0) / 2
    return {
        "macro_f1_2way": sum(per_class.values()) / 2,
        "do_nothing_floor_2way": floor,
        "per_class_f1_2way": per_class,
        "confusion_matrix_2way": {g: dict(confusion[g]) for g in TWO_WAY},
        "n_correct_2way": confusion["ACCURATE"]["ACCURATE"] + confusion["NOT"]["NOT"],
        "support_2way": {"ACCURATE": n_acc, "NOT": n_not},
    }


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


def score(pairs: Iterable[tuple[str, str]], objective: str = DEFAULT_OBJECTIVE) -> dict[str, Any]:
    """Score ``(predicted_9class_label, gold_9class_label)`` pairs.

    ``objective`` picks what ``primary_metric`` and ``do_nothing_floor`` are (:data:`OBJECTIVES`).
    Under the default the returned dict is exactly what it was before objectives existed; under
    ``macro_f1_2way`` every diagnostic is still there, the two headline keys carry the 2-way numbers,
    and ``objective``, ``accuracy_9class`` and the 2-way breakdown are added.

    Both sides are collapsed with `parse_verdict.to_3way`. A predicted label outside `SAROL_9`
    collapses to ``UNKNOWN`` and is charged as a false negative against its gold class -- a miss,
    not an error, so an optimizer edit that invents a label just scores worse.
    """
    check_objective(objective)
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

    result = {
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
    if objective == "accuracy_9class":
        return result
    two = _two_way(pairs)
    return {
        **result,
        "objective": objective,
        # The headline pair, now 2-way. The 9-class accuracy and its floor stay readable beside them.
        "primary_metric": two["macro_f1_2way"],
        "do_nothing_floor": two["do_nothing_floor_2way"],
        "accuracy_9class": result["primary_metric"],
        "accuracy_9class_floor": result["do_nothing_floor"],
        "per_class_f1_2way": two["per_class_f1_2way"],
        "confusion_matrix_2way": two["confusion_matrix_2way"],
        "support_2way": two["support_2way"],
        "n_correct_2way": two["n_correct_2way"],
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

    # -- the 2-way objective (2026-10-15). Expected numbers worked out by hand, not by the code:
    # Dev has 185 ACCURATE of 311, so always-ACCURATE scores F1(ACC) = 2*185/(185+311) = 0.746 and
    # F1(NOT) = 0, macro 0.373.
    _dev_nothing_2 = score([("ACCURATE", g) for g, n in _DEV_GOLD.items() for _ in range(n)],
                           objective="macro_f1_2way")
    # gold ACC x2, NOT x2. pred: ACC (hit), INVALID (miss, ACC side), NOT_SUBSTANTIATE for a CONTRADICT
    # (hit: both NOT), ACCURATE for an ETIQUETTE (miss). ACC: tp1 fp1 fn1 -> 0.5; NOT: tp1 fp0 fn1 -> 0.667.
    _mixed = [("ACCURATE", "ACCURATE"), ("NOT_A_LABEL", "ACCURATE"),
              ("NOT_SUBSTANTIATE", "CONTRADICT"), ("ACCURATE", "ETIQUETTE")]
    _mixed_2 = score(_mixed, objective="macro_f1_2way")
    _mixed_9 = score(_mixed)

    checks = [
        # -- the objective setting (2026-10-15) ---------------------------------------------------
        ("the default objective adds no key and changes no value: the 9-class dict is what it was",
         score(_mixed, objective="accuracy_9class") == _mixed_9 and "objective" not in _mixed_9),
        ("an unknown objective is refused, not silently scored as the default",
         _raises(lambda: score(_mixed, objective="macro_f1_3way"))),
        ("2-way: always-ACCURATE on real Dev scores the floor, 185/496 = 0.373",
         round(_dev_nothing_2["primary_metric"], 3) == 0.373
         and round(_dev_nothing_2["do_nothing_floor"], 6) == round(185 / 496, 6)),
        ("2-way: the hand-worked mixed batch scores (0.5 + 2/3) / 2",
         round(_mixed_2["primary_metric"], 6) == round((0.5 + 2 / 3) / 2, 6)
         and _mixed_2["n_correct_2way"] == 2),
        ("2-way: an invalid label is a miss for its gold side, never a hit and never a crash",
         _mixed_2["n_invalid"] == 1 and _mixed_2["support_2way"] == {"ACCURATE": 2, "NOT": 2}
         and _mixed_2["per_class_f1_2way"]["ACCURATE"] == 0.5),
        ("2-way keeps every 9-class diagnostic, and the 9-class accuracy and floor beside it",
         set(_mixed_9) <= set(_mixed_2) and _mixed_2["accuracy_9class"] == _mixed_9["primary_metric"]
         and _mixed_2["accuracy_9class_floor"] == _mixed_9["do_nothing_floor"]
         and _mixed_2["objective"] == "macro_f1_2way"),
        ("per-claim right/wrong: a CONTRADICT answered NOT_SUBSTANTIATE is right under 2-way, wrong "
         "under 9-class",
         is_correct("NOT_SUBSTANTIATE", "CONTRADICT", "macro_f1_2way")
         and not is_correct("NOT_SUBSTANTIATE", "CONTRADICT", "accuracy_9class")),
        ("...ETIQUETTE / IRRELEVANT / INDIRECT_NOT_REVIEW are NOT, so ACCURATE for them is wrong and any "
         "other label is right",
         all(not is_correct("ACCURATE", g, "macro_f1_2way") and is_correct("MISQUOTE", g, "macro_f1_2way")
             for g in ("ETIQUETTE", "IRRELEVANT", "INDIRECT_NOT_REVIEW"))),
        ("...and an invalid label is never right under either objective",
         not any(is_correct(bad, "ACCURATE", o) for bad in ("INVALID_OUTPUT", "FAILED_CALL") for o in OBJECTIVES)),
        ("...and the right/wrong count agrees with the score's own count",
         sum(is_correct(p, g, "macro_f1_2way") for p, g in _mixed) == _mixed_2["n_correct_2way"]
         and sum(is_correct(p, g) for p, g in _mixed) == _mixed_9["n_correct_9way"]),
        ("every objective has a metric name and a description naming that metric",
         all(METRIC_NAMES[o] in OBJECTIVE_DESCRIPTIONS[o] for o in OBJECTIVES)
         and METRIC_NAMES[DEFAULT_OBJECTIVE] == "sarol_accuracy_9class"),

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


def _raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run the metric regression guards")
    ap.add_argument("--pairs", type=str, default=None,
                    help='JSON file of [[predicted_label, gold_label], ...] to score')
    ap.add_argument("--objective", choices=OBJECTIVES, default=DEFAULT_OBJECTIVE,
                    help="what primary_metric and do_nothing_floor are (default: %(default)s)")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.pairs:
        with open(args.pairs, encoding="utf-8") as fh:
            print(json.dumps(score([(a, b) for a, b in json.load(fh)], objective=args.objective), indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
