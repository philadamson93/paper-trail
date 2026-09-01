"""Collapse paper-trail's native `overall_verdict` to Sarol's 3-way scheme, and score it.

Sibling of `parse_verdict.py`, which owns the *Sarol-variant* 9-class collapse and is the only
code in this repo that reads gold. This module deliberately touches **no gold**: callers pass in
already-resolved gold buckets, so the sealed-split boundary (Part C3) stays where it is.

Design decisions this implements live in `docs/plans/papertrail-optimizer-requirements.md` Part A2:

* The collapse is **not injective** against Sarol's labels. paper-trail's single `INDIRECT_SOURCE`
  verdict covers both Sarol's `INDIRECT` (-> NOT_ACCURATE) and `INDIRECT_NOT_REVIEW`
  (-> IRRELEVANT), so 17 of the IRRELEVANT bucket's 34 dev+test instances can never be predicted
  correctly, and a further 16 (`ETIQUETTE`) are ambiguous between `AMBIGUOUS` and
  `CITED_OUT_OF_CONTEXT`. Max achievable IRRELEVANT recall is ~50% before the model does anything.
* Therefore the frontier scalar is `macro_f1_reachable` -- macro-F1 over {ACCURATE, NOT_ACCURATE}
  only. IRRELEVANT is reported, never optimized.
* 3-way micro-F1 is reported but MUST NOT be used as the objective: for single-label multiclass it
  equals accuracy, and with ACCURATE at 78.1% of gold an always-CONFIRMED program scores 0.781 --
  beating both published baselines while doing nothing. `--selftest` asserts this stays true, so
  nobody re-adopts it by accident.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable, Literal

Bucket = Literal["ACCURATE", "NOT_ACCURATE", "IRRELEVANT"]

#: The three scored buckets, in report order.
BUCKETS: tuple[Bucket, ...] = ("ACCURATE", "NOT_ACCURATE", "IRRELEVANT")

#: The classes the collapse can actually reach; `macro_f1_reachable` averages over these.
REACHABLE: tuple[Bucket, ...] = ("ACCURATE", "NOT_ACCURATE")

#: Sentinel for an abstention -- excluded from the adjusted denominator, scored as a miss otherwise.
EXCLUDED = "EXCLUDED"

#: paper-trail's native 12-value `overall_verdict` (11 sub-claim verdicts + the rollup-only
#: CONFIRMED_WITH_MINOR) -> Sarol 3-way. See Part A2 for the per-value rationale.
NATIVE_TO_SAROL3: dict[str, str] = {
    "CONFIRMED": "ACCURATE",
    "CONFIRMED_WITH_MINOR": "ACCURATE",
    "OVERSTATED_MILD": "NOT_ACCURATE",
    "OVERSTATED": "NOT_ACCURATE",
    "OVERGENERAL": "NOT_ACCURATE",
    "PARTIALLY_SUPPORTED": "NOT_ACCURATE",
    "UNSUPPORTED": "NOT_ACCURATE",
    "CONTRADICTED": "NOT_ACCURATE",
    "MISATTRIBUTED": "NOT_ACCURATE",
    "INDIRECT_SOURCE": "NOT_ACCURATE",
    "CITED_OUT_OF_CONTEXT": "IRRELEVANT",
    "AMBIGUOUS": EXCLUDED,
}

#: Documented in every release payload so a reader never mistakes the IRRELEVANT figure for a
#: model result. Counts are dev+test evidence annotations from `docs/plans/paper-tool-validation.md`.
IRRELEVANT_REACHABILITY_CEILING: dict[str, Any] = {
    "bucket_n": 34,
    "unreachable_n": 17,
    "unreachable_reason": (
        "Sarol's INDIRECT_NOT_REVIEW (n=17) collapses to IRRELEVANT, but maps to paper-trail's "
        "INDIRECT_SOURCE, which this table sends to NOT_ACCURATE. No program the optimizer can "
        "write predicts these correctly."
    ),
    "ambiguous_n": 16,
    "ambiguous_reason": (
        "Sarol's ETIQUETTE (n=16) is reachable only if the adjudicator emits CITED_OUT_OF_CONTEXT "
        "rather than AMBIGUOUS; this table routes those two verdicts differently."
    ),
    "max_recall": 0.5,
}


class UnknownVerdict(ValueError):
    """Raised for a verdict outside the native enum -- never silently bucketed."""


def collapse(verdict: str) -> str:
    """Map one native `overall_verdict` to a Sarol bucket or ``EXCLUDED``.

    Fails loudly rather than defaulting: a verdict this table does not know about means the rubric
    grew a value and the collapse was not updated, which would otherwise show up as a silent
    metric shift mid-run.
    """
    try:
        return NATIVE_TO_SAROL3[verdict]
    except KeyError:
        raise UnknownVerdict(
            f"{verdict!r} is not in paper-trail's native overall_verdict enum; "
            f"update NATIVE_TO_SAROL3 and re-run the OQ2 reachability check"
        ) from None


def _f1(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall)


def score(
    pairs: Iterable[tuple[str, str]],
    *,
    abstentions: Literal["adjust", "miss"] = "adjust",
) -> dict[str, Any]:
    """Score ``(native_verdict, gold_bucket)`` pairs.

    ``abstentions="adjust"`` drops AMBIGUOUS predictions from the denominator (the default, and
    what `primary_metric` uses); ``"miss"`` keeps them and counts each as a false negative for its
    gold class, which is the variant comparable to Sarol's own abstention-free setup.
    """
    confusion = {g: {p: 0 for p in BUCKETS} for g in BUCKETS}
    abstained = 0
    total = 0

    for verdict, gold in pairs:
        if gold not in confusion:
            raise ValueError(f"gold bucket {gold!r} is not one of {BUCKETS}")
        total += 1
        predicted = collapse(verdict)
        if predicted == EXCLUDED:
            abstained += 1
            if abstentions == "adjust":
                continue
            # scored as a miss: a false negative for the gold class, credited to no prediction
            confusion[gold]["__abstained__"] = confusion[gold].get("__abstained__", 0) + 1
            continue
        confusion[gold][predicted] += 1

    per_class: dict[str, float] = {}
    for c in BUCKETS:
        tp = confusion[c][c]
        fp = sum(confusion[g][c] for g in BUCKETS if g != c)
        fn = sum(confusion[c][p] for p in BUCKETS if p != c) + confusion[c].get("__abstained__", 0)
        per_class[c] = _f1(tp, fp, fn)

    scored = sum(confusion[g][p] for g in BUCKETS for p in BUCKETS)
    correct = sum(confusion[c][c] for c in BUCKETS)
    # single-label multiclass: micro-F1 == accuracy. Reported only -- see the module docstring.
    micro = correct / scored if scored else 0.0

    return {
        "primary_metric": sum(per_class[c] for c in REACHABLE) / len(REACHABLE),
        "macro_f1_3way": sum(per_class.values()) / len(BUCKETS),
        "micro_f1": micro,
        "per_class_f1": per_class,
        "confusion_matrix": {g: {p: confusion[g][p] for p in BUCKETS} for g in BUCKETS},
        "abstention_rate": abstained / total if total else 0.0,
        "n_total": total,
        "n_scored": scored,
        "irrelevant_reachability_ceiling": IRRELEVANT_REACHABILITY_CEILING,
    }


def _selftest() -> int:
    """Regression-guard the two facts that drove the metric choice."""
    gold_dist = {"ACCURATE": 1463, "NOT_ACCURATE": 376, "IRRELEVANT": 34}
    always_confirmed = [("CONFIRMED", g) for g, n in gold_dist.items() for _ in range(n)]
    r = score(always_confirmed)

    checks = [
        ("do-nothing micro_f1 is degenerate (== majority share)", round(r["micro_f1"], 3) == 0.781),
        ("do-nothing macro_f1_3way is near-worthless", round(r["macro_f1_3way"], 3) == 0.292),
        ("do-nothing primary_metric discriminates", round(r["primary_metric"], 3) == 0.439),
        ("primary_metric < micro_f1 (i.e. micro would have been gameable)",
         r["primary_metric"] < r["micro_f1"]),
        ("collapse rejects unknown verdicts", _raises(lambda: collapse("NOT_A_VERDICT"))),
        ("AMBIGUOUS abstains", collapse("AMBIGUOUS") == EXCLUDED),
        ("every native verdict maps", len(NATIVE_TO_SAROL3) == 12),
    ]
    perfect = [(v, b) for v, b in
               [("CONFIRMED", "ACCURATE"), ("UNSUPPORTED", "NOT_ACCURATE"),
                ("CITED_OUT_OF_CONTEXT", "IRRELEVANT")]]
    checks.append(("perfect predictions score 1.0", score(perfect)["primary_metric"] == 1.0))

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def _raises(fn) -> bool:
    try:
        fn()
    except UnknownVerdict:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run the metric regression guards")
    ap.add_argument("--pairs", type=str, default=None,
                    help='JSON file of [[native_verdict, gold_bucket], ...] to score')
    ap.add_argument("--abstentions", choices=("adjust", "miss"), default="adjust")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if args.pairs:
        with open(args.pairs, encoding="utf-8") as fh:
            pairs = [(a, b) for a, b in json.load(fh)]
        print(json.dumps(score(pairs, abstentions=args.abstentions), indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
