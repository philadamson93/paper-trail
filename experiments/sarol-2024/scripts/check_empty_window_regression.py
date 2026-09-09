#!/usr/bin/env python3
"""Gate D -- the empty-window regression, run offline before anything paid.

The paper-verbatim reset (Plan A, P0) rebuilt `adjudicator-dispatch-sarol.md` from its `program-v0`
blob and re-applied exactly ONE post-v0 clause by hand: the `### Output contract` rule requiring every
sub-claim to carry an `evidence` array even when retrieval returned nothing. That clause recovered 5
`MISSING_FIELD` failures and is the only statistically real gain of the whole five-iteration run --
and because it is re-applied by hand rather than inherited, it is the single edit most likely to be
silently lost. This gate proves it survived, without spending a cent on a live sweep.

It asserts the asymmetry the clause depends on:

  - a sub-claim with `"evidence": []`      -> ACCEPTED  (empty window is legal)
  - the same sub-claim with the field GONE -> REJECTED  with `MISSING_FIELD:sub_claims[0].evidence`

The second half is the negative control. Without it this gate would pass on a validator that accepts
everything, which is exactly the failure it exists to rule out.

Run:  ~/.local/bin/python3.13 scripts/check_empty_window_regression.py
Exit: 0 both halves hold; 1 otherwise.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
FIXTURE = EXPERIMENT / "optimizer" / "fixtures" / "empty_window_sarol.json"
DISPATCH = EXPERIMENT / "prompts" / "adjudicator-dispatch-sarol.md"

sys.path.insert(0, str(EXPERIMENT / "optimizer"))
import validate_sarol  # noqa: E402


def main() -> int:
    failures: list[str] = []

    if not FIXTURE.exists():
        print(f"Gate D FAILED -- fixture missing: {FIXTURE}", file=sys.stderr)
        return 1
    envelope = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # --- half 1: an empty window is legal -------------------------------------------------
    sub = envelope["sub_claims"][0]
    if sub.get("evidence") != []:
        failures.append("fixture drift: the fixture's sub-claim no longer carries an EMPTY evidence list")

    ok = validate_sarol.validate_obj(envelope, expect_claim_id=envelope["claim_id"])
    if not ok.ok:
        failures.append(
            f"an empty evidence array was REJECTED, but it must be accepted: {list(ok.violations)}"
        )

    # --- half 2: the negative control -- a missing field must still be caught ---------------
    stripped = copy.deepcopy(envelope)
    del stripped["sub_claims"][0]["evidence"]
    bad = validate_sarol.validate_obj(stripped, expect_claim_id=stripped["claim_id"])
    if bad.ok:
        failures.append(
            "NEGATIVE CONTROL FAILED: an omitted `evidence` field was accepted, so this gate proves "
            "nothing -- the validator is not enforcing the field at all"
        )
    else:
        expected = "MISSING_FIELD:sub_claims[0].evidence"
        if not any(expected in v for v in bad.violations):
            failures.append(
                f"omitting `evidence` was rejected, but not with {expected!r}: {list(bad.violations)}"
            )

    # --- half 3: the clause is still in the prompt that produces the field ------------------
    if DISPATCH.exists():
        text = DISPATCH.read_text(encoding="utf-8")
        if '"evidence": []' not in text:
            failures.append(
                "the dispatch prompt no longer tells the judge to emit `\"evidence\": []` on an empty "
                "window -- the validator would accept it, but nothing would produce it"
            )
    else:
        failures.append(f"missing dispatch prompt: {DISPATCH}")

    if failures:
        print(f"Gate D FAILED -- {len(failures)} problem(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("Gate D passed.")
    print('  empty window  `"evidence": []`   -> ACCEPTED')
    print("  negative ctl  field omitted      -> REJECTED with MISSING_FIELD:sub_claims[0].evidence")
    print("  the re-applied dispatch clause that produces the field is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
