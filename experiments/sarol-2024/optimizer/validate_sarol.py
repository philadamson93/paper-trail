"""Exit validation for verdict files produced under the Sarol 9-class rubric variant.

Why this module exists (plan Part C5, Open Questions §9): `program-v0` freezes **both** rubrics.
The native `src/specs/verdict_schema.md` declares `sub_claims[*].verdict` as paper-trail's own 11
labels and its validation rule 5 requires every sub-claim verdict to be a valid member of that
enum. The Sarol adjudicator emits `ACCURATE` / `OVERSIMPLIFY` / ... instead. So **a correct Sarol
run produces output the frozen native validator rejects as `SCHEMA_VIOLATION`** -- which would gate
the adapter smoke shut even when the program is behaving exactly as designed.

The fix is *not* a branch-local relaxation of the shipped orchestrator: `main`'s validator stays
strict against the native enum and is untouched by this experiment, which keeps the deferred
native-adoption change (plan "Landing & cleanup") a clean separate commit rather than something
this experiment half-lands by side effect. The fix is this experiment-only module, which the
Runner *calls* at exit. The validator owns the rule.

Three behaviours worth not re-deriving:

* **Gated on `rubric_variant`.** The adjudicator already stamps `"sarol_2024_9class"` on every
  file it writes (`prompts/adjudicator-dispatch-sarol.md`). Only files carrying that marker are
  judged against `SAROL_9`.

* **A native label is a rejection; an unknown label is a miss.** These look similar and are not.
  A *native* verdict (`CONFIRMED`, `AMBIGUOUS`, ...) inside a file stamped as Sarol means the
  wrong rubric ran -- a pipeline error, so the file is rejected (`RUBRIC_MISMATCH`) rather than
  coerced. A label in *neither* enum is an ordinary bad prediction: per the plan's Part A2
  fixed-vocabulary rule it is charged as a miss and counted in `error_class_counts`, never raised.
  That asymmetry is the whole point -- an optimizer edit that invents a label simply scores worse
  and the loop rejects it on its own, while a mis-wired run fails loudly instead of scoring.

* **The rollup check enforces worst-wins, with the order READ from the rubric.** There is a real
  tension here worth stating. The plan keeps the native schema's rollup-consistency rule in force
  under the variant gate, but the worst-wins ordering lives in `specs/verdict_schema_sarol.md`,
  which is the **optimizer-editable** half of the rubric (the enum contract beside it owns only the
  labels and the 3-way collapse). Hard-coding the order would make a legitimate optimizer edit fail
  every subsequent run; dropping the check -- an earlier version of this module did exactly that,
  accepting any `overall_verdict` present among the sub-claims -- silently permits a file whose
  sub-claims are `CONTRADICT` and `ACCURATE` to roll up to `ACCURATE`, which is the single most
  consequential thing this validator exists to catch.

  So the order is **parsed from the rubric at validation time** and then enforced strictly. The
  optimizer may reorder the ladder; it may not produce a rollup that disagrees with whatever ladder
  it has declared. If the ordering block cannot be parsed the file is rejected
  (`ROLLUP_ORDER_UNPARSEABLE`) rather than silently unchecked -- fail-closed, because an
  unparseable ladder means the rule is unenforceable, not that it does not apply.

* **`AMBIGUOUS` is a counted miss, not a rubric mismatch.** It is a native verdict, so the obvious
  reading would put it with the wrong-rubric rejections. The frozen enum contract says otherwise in
  as many words: `AMBIGUOUS` survives in the shipped tool as a *workflow flag* (Open Questions §7),
  and "the exit validator must reject it appearing in a verdict field exactly like any other
  out-of-enum label". Out-of-enum labels are charged as misses, so that is what happens to it.

Two native structural rules are deliberately **not** ported, because their triggers are written in
native labels rather than in structure: rule 8 (`UNSUPPORTED`/`CONTRADICTED` require a non-empty
`closest_adjacent`) and rule 9 (`paper_value != claim_value` forces an OVERSTATED* verdict). The
plan names exactly four structural rules as surviving the variant gate -- required fields,
non-empty `sub_claims`, rollup consistency, and the `phrasings_tried` floor -- and inventing Sarol
analogues for 8 and 9 would be writing new contract inside a validator. If they are wanted later
they belong in the rubric, where the optimizer can see them.

Usage:
    validate_sarol.py --verdict <path/to/claim.json> [--claim-id C042]
    validate_sarol.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from parse_verdict import SAROL_9  # noqa: E402  -- the owner of the enum contract

#: The marker the Sarol adjudicator stamps on every file it writes.
SAROL_VARIANT = "sarol_2024_9class"

#: paper-trail's native sub-claim enum, plus the two roll-up-only values. Present here purely so a
#: native label can be *recognised* and rejected as a wrong-rubric signal rather than silently
#: charged as a bad prediction. This module never validates against it -- `main` owns that.
#:
#: `AMBIGUOUS` is deliberately NOT in this set even though it is a native verdict: the frozen enum
#: contract requires it to be treated as an ordinary out-of-enum label (see the module docstring).
NATIVE_VERDICTS = frozenset({
    "CONFIRMED",
    "CONFIRMED_WITH_MINOR",
    "OVERSTATED_MILD",
    "OVERSTATED",
    "OVERGENERAL",
    "PARTIALLY_SUPPORTED",
    "CITED_OUT_OF_CONTEXT",
    "UNSUPPORTED",
    "CONTRADICTED",
    "MISATTRIBUTED",
    "INDIRECT_SOURCE",
})

#: The editable rubric, whose fenced strictness ladder this module parses. Beside this file's
#: package, at ../specs/. Overridable per call so the Runner can validate against the *materialized*
#: rubric the program actually ran under, rather than the repo's current copy.
DEFAULT_RUBRIC_PATH = pathlib.Path(__file__).resolve().parents[1] / "specs" / "verdict_schema_sarol.md"

REQUIRED_TOP_LEVEL = (
    "claim_id",
    "schema_version",
    "run_id",
    "citekey",
    "source_mode",
    "claim_text",
    "claim_type",
    "sub_claims",
    "overall_verdict",
    "attestation",
    "stage",
)

REQUIRED_SUB_CLAIM = ("sub_claim_id", "text", "evidence", "verdict")

VALID_SOURCE_MODES = frozenset({"paperclip", "pdf", "pdf_ocr_fallback"})

#: Claim types the native schema puts a >=3 floor on. Everything else floors at 1; the schema is
#: explicit about DIRECT/PARAPHRASED and FRAMING and silent about the rest.
STRICT_PHRASING_TYPES = frozenset({"DIRECT", "PARAPHRASED"})
STRICT_PHRASING_FLOOR = 3
DEFAULT_PHRASING_FLOOR = 1


def parse_rollup_order(rubric_text: str) -> tuple[str, ...] | None:
    """Pull the worst-wins strictness ladder out of the editable rubric.

    The rubric declares it as a fenced block of `SAROL_9` labels separated by ``>``, strongest
    first. Returns the ladder, or None when no fenced block contains a full permutation of the
    enum -- which the caller must treat as a hard failure, not as "no check applies".

    Parsing a file the optimizer owns is the price of letting it reorder the ladder while still
    enforcing that its own rollups obey whatever ladder it declared.
    """
    for block in re.findall(r"```(.*?)```", rubric_text, flags=re.DOTALL):
        tokens = re.findall(r"[A-Z_]{3,}", block)
        ordered: list[str] = []
        for token in tokens:
            if token in SAROL_9 and token not in ordered:
                ordered.append(token)
        if len(ordered) == len(SAROL_9):
            return tuple(ordered)
    return None


def load_rollup_order(rubric_path: pathlib.Path | None = None) -> tuple[str, ...] | None:
    path = pathlib.Path(rubric_path) if rubric_path is not None else DEFAULT_RUBRIC_PATH
    try:
        return parse_rollup_order(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def worst_wins(labels: Iterable[str], order: Sequence[str]) -> str | None:
    """The strongest label present, per ``order`` (index 0 is strongest)."""
    rank = {label: i for i, label in enumerate(order)}
    ranked = [(rank[l], l) for l in labels if l in rank]
    if not ranked:
        return None
    return min(ranked)[1]


@dataclass
class ValidationResult:
    """What the Runner gets back. `ok` gates the iteration; the labels feed the Scorer."""

    ok: bool
    violations: list[str] = field(default_factory=list)
    error_class_counts: dict[str, int] = field(default_factory=dict)
    overall_verdict: str | None = None
    sub_claim_verdicts: list[str] = field(default_factory=list)
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": list(self.violations),
            "error_class_counts": dict(self.error_class_counts),
            "overall_verdict": self.overall_verdict,
            "sub_claim_verdicts": list(self.sub_claim_verdicts),
            "path": self.path,
        }


def _count(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _classify(label: Any, counts: dict[str, int], where: str, violations: list[str]) -> None:
    """Sort one verdict value into: valid / wrong-rubric (reject) / unknown (miss)."""
    if label in SAROL_9:
        return
    if label in NATIVE_VERDICTS:
        # The wrong rubric ran. Loud failure, never coercion -- coercing would manufacture a score
        # out of a mis-wired pipeline, which is exactly the "silently degraded metric" the plan's
        # Verification table exists to catch.
        violations.append(f"RUBRIC_MISMATCH:{where}={label}")
        return
    # Neither enum: an ordinary invalid output. Charged as a miss, counted, never raised.
    _count(counts, "invalid_label")
    _count(counts, f"invalid_label:{label}")


def validate_obj(
    verdict: dict[str, Any],
    *,
    expect_claim_id: str | None = None,
    expect_variant: str = SAROL_VARIANT,
    path: str | None = None,
    rubric_path: pathlib.Path | None = None,
    rollup_order: Sequence[str] | None = None,
) -> ValidationResult:
    """Validate an already-parsed verdict envelope. Never raises on bad *content*.

    ``rubric_path`` should point at the rubric the program actually ran under -- for a real run
    that is the copy inside the materialized tree, not the repo's working copy. ``rollup_order``
    short-circuits the parse when a caller has already loaded the ladder for a whole batch.
    """
    violations: list[str] = []
    counts: dict[str, int] = {}

    variant = verdict.get("rubric_variant")
    if variant != expect_variant:
        # Not this validator's file. Say so rather than guessing -- the native validator on `main`
        # owns anything not stamped for the experiment.
        violations.append(f"RUBRIC_VARIANT_UNKNOWN:{variant!r}")
        return ValidationResult(ok=False, violations=violations, path=path)

    for key in REQUIRED_TOP_LEVEL:
        if key not in verdict or verdict[key] is None:
            violations.append(f"MISSING_FIELD:{key}")

    if expect_claim_id is not None and verdict.get("claim_id") != expect_claim_id:
        violations.append(
            f"CLAIM_ID_MISMATCH:expected={expect_claim_id},got={verdict.get('claim_id')!r}"
        )

    # Envelope rules 10 and 11 are label-independent, so they survive the variant gate unchanged.
    source_mode = verdict.get("source_mode")
    if source_mode not in VALID_SOURCE_MODES:
        violations.append(f"SOURCE_MODE_MISSING:{source_mode!r}")
    paperclip_handle = verdict.get("paperclip_handle")
    if source_mode == "paperclip" and not paperclip_handle:
        violations.append("PAPERCLIP_HANDLE_MISMATCH:paperclip mode without a handle")
    if source_mode != "paperclip" and paperclip_handle:
        violations.append(f"PAPERCLIP_HANDLE_MISMATCH:handle set under source_mode={source_mode!r}")

    sub_claims = verdict.get("sub_claims")
    if not isinstance(sub_claims, list) or not sub_claims:
        violations.append("EMPTY_SUB_CLAIMS")
        sub_claims = []

    sub_verdicts: list[Any] = []
    for i, sub in enumerate(sub_claims):
        if not isinstance(sub, dict):
            violations.append(f"MISSING_FIELD:sub_claims[{i}]")
            continue
        for key in REQUIRED_SUB_CLAIM:
            if key not in sub or sub[key] is None:
                violations.append(f"MISSING_FIELD:sub_claims[{i}].{key}")
        label = sub.get("verdict")
        sub_verdicts.append(label)
        _classify(label, counts, f"sub_claims[{i}].verdict", violations)

    overall = verdict.get("overall_verdict")
    _classify(overall, counts, "overall_verdict", violations)

    # Rule 6, worst-wins, against the ladder the rubric currently declares. See the module
    # docstring: the order is the optimizer's to change, the consistency is not.
    if sub_verdicts:
        order = rollup_order if rollup_order is not None else load_rollup_order(rubric_path)
        if order is None:
            # Fail closed. An unparseable ladder makes the rule unenforceable, which is not the
            # same as the rule not applying -- and silently skipping it is how a CONTRADICT
            # sub-claim ends up rolled up to ACCURATE with nothing complaining.
            violations.append(
                "ROLLUP_ORDER_UNPARSEABLE:no fenced strictness ladder covering all 9 labels in "
                f"{rubric_path or DEFAULT_RUBRIC_PATH}"
            )
        else:
            valid_subs = [v for v in sub_verdicts if v in SAROL_9]
            expected = worst_wins(valid_subs, order)
            # When no sub-claim carries a usable label there is nothing to roll up from; the
            # invalid labels themselves are already recorded above.
            if expected is not None and overall != expected:
                violations.append(
                    f"ROLLUP_INCONSISTENT:{overall!r} is not the worst-wins rollup of "
                    f"{[str(v) for v in sub_verdicts]}; expected {expected!r}"
                )

    # Rule 7, the attestation floor.
    attestation = verdict.get("attestation") or {}
    phrasings = attestation.get("phrasings_tried") if isinstance(attestation, dict) else None
    claim_type = verdict.get("claim_type") or {}
    ctype = claim_type.get("type") if isinstance(claim_type, dict) else None
    floor = STRICT_PHRASING_FLOOR if ctype in STRICT_PHRASING_TYPES else DEFAULT_PHRASING_FLOOR
    n_phrasings = len(phrasings) if isinstance(phrasings, list) else 0
    if n_phrasings < floor:
        violations.append(
            f"PHRASINGS_FLOOR:claim_type={ctype!r} needs >={floor}, got {n_phrasings}"
        )

    return ValidationResult(
        ok=not violations,
        violations=violations,
        error_class_counts=counts,
        overall_verdict=overall if isinstance(overall, str) else None,
        sub_claim_verdicts=[v for v in sub_verdicts if isinstance(v, str)],
        path=path,
    )


def validate_file(
    path: pathlib.Path,
    *,
    expect_claim_id: str | None = None,
    expect_variant: str = SAROL_VARIANT,
    rubric_path: pathlib.Path | None = None,
    rollup_order: Sequence[str] | None = None,
) -> ValidationResult:
    """Read and validate one verdict file. A malformed file is a violation, not a traceback."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(ok=False, violations=[f"UNREADABLE:{exc}"], path=str(path))
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ValidationResult(ok=False, violations=[f"JSON_PARSE_ERROR:{exc}"], path=str(path))
    if not isinstance(obj, dict):
        return ValidationResult(
            ok=False,
            violations=[f"JSON_PARSE_ERROR:top level is {type(obj).__name__}, not object"],
            path=str(path),
        )
    return validate_obj(
        obj,
        expect_claim_id=expect_claim_id,
        expect_variant=expect_variant,
        path=str(path),
        rubric_path=rubric_path,
        rollup_order=rollup_order,
    )


FIXTURE_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _selftest() -> int:
    """The plan's three Verification-table fixtures, plus guards on the asymmetry they encode."""
    valid = validate_file(FIXTURE_DIR / "valid_all_sarol.json")
    mixed = validate_file(FIXTURE_DIR / "mixed_native_sarol.json")
    unknown = validate_file(FIXTURE_DIR / "out_of_enum_label.json")
    sub_only = validate_file(FIXTURE_DIR / "invalid_subclaim_only.json")
    bad_rollup = validate_file(FIXTURE_DIR / "bad_rollup.json")
    order = load_rollup_order()

    checks = [
        # Fixture 1 -- the gate the adapter smoke actually depends on.
        ("a correct all-Sarol file validates", valid.ok),
        ("...and returns its labels for scoring", valid.overall_verdict == "OVERSIMPLIFY"),
        ("...with nothing charged as invalid", valid.error_class_counts == {}),
        # Fixture 2 -- wrong rubric ran, so reject rather than coerce.
        ("a mixed native/Sarol file is rejected", not mixed.ok),
        ("...specifically as a rubric mismatch",
         any(v.startswith("RUBRIC_MISMATCH") for v in mixed.violations)),
        ("...naming the native label that gave it away",
         any("CONFIRMED" in v for v in mixed.violations)),
        ("...and is NOT charged as an invalid prediction",
         "invalid_label" not in mixed.error_class_counts),
        # Fixture 3 -- an ordinary bad prediction, scored not raised.
        ("an out-of-enum label does not raise", isinstance(unknown, ValidationResult)),
        ("...is counted in error_class_counts",
         unknown.error_class_counts.get("invalid_label") == 2),
        ("...under its own name too",
         unknown.error_class_counts.get("invalid_label:AMBIGUOUS") == 2),
        ("...and does not trip a rubric mismatch",
         not any(v.startswith("RUBRIC_MISMATCH") for v in unknown.violations)),
        # AMBIGUOUS is a native verdict, so this is the case that is easy to get wrong: the frozen
        # enum contract requires it be charged as an ordinary out-of-enum miss, not rejected as a
        # wrong-rubric signal.
        ("AMBIGUOUS is a counted miss, per the enum contract -- not a rubric mismatch",
         "AMBIGUOUS" not in NATIVE_VERDICTS),
        # Fixture 4 -- an invalid SUB-CLAIM under a valid overall verdict. The case that scored
        # clean before, because the scorer re-derived counts from the overall label alone.
        ("an invalid sub-claim is counted even when overall_verdict is valid",
         sub_only.error_class_counts.get("invalid_label") == 1),
        ("...named", sub_only.error_class_counts.get("invalid_label:PROBABLY_FINE") == 1),
        ("...and the valid overall verdict is still returned for scoring",
         sub_only.overall_verdict == "ACCURATE"),
        # Fixture 5 -- worst-wins is enforced, not merely "overall appears somewhere".
        ("CONTRADICT + ACCURATE must NOT roll up to ACCURATE", not bad_rollup.ok),
        ("...specifically as a rollup inconsistency",
         any(v.startswith("ROLLUP_INCONSISTENT") for v in bad_rollup.violations)),
        ("...naming the label worst-wins actually requires",
         any("CONTRADICT" in v for v in bad_rollup.violations)),
        # The ladder is read from the rubric, so the optimizer may reorder it...
        ("the strictness ladder parses out of the editable rubric", order is not None),
        ("...as a full permutation of the enum", order is not None and set(order) == SAROL_9),
        ("...strongest first", order is not None and order[0] == "CONTRADICT"),
        ("...weakest last", order is not None and order[-1] == "ACCURATE"),
        ("a reordered ladder changes what validates -- the order is the optimizer's to set",
         validate_obj(_fixture("bad_rollup.json"),
                      rollup_order=("ACCURATE",) + tuple(l for l in SAROL_9 if l != "ACCURATE")).ok),
        # ...but an unparseable ladder fails closed rather than skipping the rule.
        ("an unparseable ladder is a violation, not a silent skip",
         not validate_obj(_fixture("bad_rollup.json"),
                          rubric_path=pathlib.Path("/nonexistent/rubric.md")).ok),
        ("...named as such",
         any(v.startswith("ROLLUP_ORDER_UNPARSEABLE") for v in validate_obj(
             _fixture("bad_rollup.json"),
             rubric_path=pathlib.Path("/nonexistent/rubric.md")).violations)),
        ("rollup rejects a label absent from sub-claims",
         not validate_obj({**_fixture("valid_all_sarol.json"), "overall_verdict": "MISQUOTE"}).ok),
        # The variant gate itself.
        ("a non-Sarol file is declined, not judged",
         not validate_obj({**_fixture("valid_all_sarol.json"), "rubric_variant": "native"}).ok),
        ("the two enums are disjoint, so the asymmetry is decidable",
         not (SAROL_9 & NATIVE_VERDICTS)),
    ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    if failed:
        for label, res in (("valid", valid), ("mixed", mixed), ("unknown", unknown)):
            print(f"\n[{label}] {json.dumps(res.as_dict(), indent=2)}", file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verdict", type=pathlib.Path, help="verdict JSON to validate")
    ap.add_argument("--claim-id", default=None, help="claim_id assigned at dispatch (rule 3)")
    ap.add_argument("--selftest", action="store_true", help="run the three Part C5 fixtures")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if args.verdict:
        result = validate_file(args.verdict, expect_claim_id=args.claim_id)
        print(json.dumps(result.as_dict(), indent=2))
        return 0 if result.ok else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
