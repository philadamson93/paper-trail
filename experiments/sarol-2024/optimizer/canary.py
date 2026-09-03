"""The round-trip canary: pin one claim's verdict, and refuse to run without it.

`sarol`'s D46 and OQ12 both treat the canary as load-bearing — a pinned claim, processed before
any scored claim, whose changed verdict stops the run. The reasoning is that a silently-broken
scorer or pipeline is the most expensive failure available here: it does not announce itself, and
it invalidates every iteration *after* the break, not just the current one.

**It never fired.** The 2026-09-02 run priced the canary at three firings per iteration and
carried `"canary": null` in every manifest, because `CanarySpec` had a `None` default and nothing
ever constructed one. So no number that run produced carries the round-trip guarantee the design
says it must — and nothing said so. That is the shape this module closes: a guard that can be
absent without announcing itself is not a guard.

Two halves, deliberately separate:

* **The pin** (`--pin`) is a *measurement*, not an assertion. It stages a claim, dispatches it
  through the real `SarolRunner` — the same path that will later guard the run, not a
  reimplementation of it — and records the verdict that actually came back. A hand-written
  expected verdict would be pinning a belief.
* **The refusal** lives in `dispatcher.run_optimization`: a real run whose cost model prices a
  canary must have one wired, or it stops before spending anything.

⚠ **Known limitation, unresolved — the adjudicator is an LLM and is not deterministic.** A pin is
one observation of a stochastic process, and a canary miss is a hard stop. If the judge flips this
claim at rate *p*, a run of *k* iterations takes roughly `1 - (1-p)^(3k)` spurious stops, since
the canary fires once per Runner call and there are three per iteration. At p=0.05 over 3
iterations that is ~37%. The honest fix is a stability check at pin time (record the verdict only
if it repeats across *m* dispatches) and/or a tolerance band, which is the same
noise-floor question Finding 6 raises for the frontier itself. Neither is decided, so this module
pins a single observation and says so loudly rather than implying a guarantee it cannot make.
See `--pin --repeat N`, which is the cheap half of that and is available now.

Usage:
    canary.py --pin --profile retrieval        # measure and write the pin (COSTS ~1 session)
    canary.py --pin --profile retrieval --repeat 3   # ...and require it to be stable first
    canary.py --show                           # print the current pin
    canary.py --selftest                       # offline gates
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_SCRIPTS = _HERE.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import adapter  # noqa: E402
import profiles as profiles_mod  # noqa: E402
import sampling  # noqa: E402

#: Where the pin lives. One file per profile, because a canary pinned under `retrieval` says
#: nothing about `agentic`: different stages run, so a changed verdict would mean something else
#: entirely. C6.5's reasoning about the frontier scalar applies here for the same reason.
CANARY_DIR = _HERE / "canary"

#: A dedicated seed, unrelated to `sampling.SEED`, so the canary claim is not a function of any
#: run's draw and does not move when a ramp or VAL size changes.
CANARY_SEED = 20260903


def pin_path(profile: str) -> pathlib.Path:
    return CANARY_DIR / f"canary-{profile}.json"


def canary_staging_dir(profile: str) -> pathlib.Path:
    """Staged separately from any batch's staging root.

    The pinned claim is drawn from TRAIN and is therefore also drawable into a TRAIN batch. Its
    own staging dir keeps the two dispatches from overwriting each other's verdict ledger — the
    canary must be judged on its own record, not on whatever a scored pass last wrote there.
    """
    return CANARY_DIR / "staging" / profile


def choose_claim(split: str = "train") -> "sampling.ClaimUnit":
    """The pinned claim: a seeded draw of one from `split`, stable across runs.

    Drawn rather than hard-coded so it is reproducible from the pool alone, and drawn from TRAIN
    because TRAIN is Tier 1 — a canary on a held-out claim would put a VAL record in the
    optimizer's blast radius for no benefit.
    """
    import random

    pool = sampling.claim_pool(split)
    if not pool:
        raise ValueError(f"no drawable units in split {split!r}")
    return random.Random(CANARY_SEED).choice(pool)


def load(profile: str) -> "adapter.CanarySpec | None":
    """The pinned `CanarySpec` for `profile`, or None if nothing has been pinned yet.

    Returning None rather than raising is deliberate for *absence*: whether a missing pin is fatal
    is the caller's policy, and `dispatcher.run_optimization` is where that policy lives. A pin
    that EXISTS but disagrees with itself is a different matter and raises here -- the filename is
    not the authority, the payload is. A `canary-retrieval.json` whose body says
    `"profile": "agentic"` would otherwise wire and price as retrieval while pinning a verdict
    produced under a three-stage pipeline: a guard silently comparing against the wrong instrument,
    which is worse than no guard at all.
    """
    path = pin_path(profile)
    if not path.exists():
        return None
    obj = json.loads(path.read_text(encoding="utf-8"))

    recorded_profile = obj.get("profile")
    if recorded_profile is not None and recorded_profile != profile:
        raise ValueError(
            f"canary pin at {path} was measured under profile {recorded_profile!r} but is being "
            f"loaded for {profile!r}. A canary compares this run against a verdict produced by a "
            "DIFFERENT pipeline; re-pin under the profile you intend to run."
        )
    recorded_split = obj.get("split")
    if recorded_split is not None and recorded_split != "train":
        raise ValueError(
            f"canary pin at {path} was drawn from split {recorded_split!r}. The canary claim is "
            "read and re-dispatched every Runner call, so a held-out claim would put a VAL/TEST "
            "record inside the optimizer's blast radius for no benefit. Re-pin from train."
        )
    return adapter.CanarySpec(
        claim=adapter.ClaimRecord.from_dict(obj["claim"]),
        expected_verdict=obj["expected_verdict"],
    )


def describe(profile: str) -> dict[str, Any] | None:
    path = pin_path(profile)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# =================================================================================================
# Pinning -- a measurement, and it costs real money
# =================================================================================================


def pin(
    *,
    profile: str,
    repeat: int = 1,
    split: str = "train",
    source_mode: str = "corpus",
    runner=None,
    program_store=None,
    claim: "adapter.ClaimRecord | None" = None,
) -> dict[str, Any]:
    """Dispatch the chosen claim `repeat` times through the REAL Runner and record the verdict.

    Refuses to write a pin when the observations disagree. That is the point of `--repeat`: a
    canary pinned to a verdict the judge only produces sometimes converts ordinary LLM
    nondeterminism into a hard stop, which is worse than no canary because it looks like a real
    instrument failure.
    """
    import datetime

    if repeat < 1:
        raise ValueError(f"--repeat must be >= 1, got {repeat}")
    if split != "train":
        # The module docstring said TRAIN-only and argparse accepted anything -- help text is not
        # a guard, which is the whole lesson of this post-mortem. Enforced here, at the one place
        # that can actually stage a held-out claim into the optimizer's reach.
        raise ValueError(
            f"the canary must be pinned from the train split, got {split!r}: it is Tier 1, so its "
            "gold is already open to the optimizer. Pinning a dev/test claim would stage a "
            "held-out record where the optimizer can read it."
        )

    prof = profiles_mod.get(profile)
    store = program_store or adapter.SarolProgramStore()
    # `claim` is an injection seam for the offline gates: staging a real one needs the benchmark
    # on disk, and what has to be provable without spending money is that this function reads its
    # expected verdict back from a REAL dispatch rather than asserting one.
    if claim is None:
        unit = choose_claim(split)
        staging = canary_staging_dir(prof.name) / unit.claim_id
        import stage_claim  # noqa: PLC0415

        info = stage_claim.stage(
            split=split,
            claim_row_id=unit.claim_row_id,
            cited_paper_bucket=unit.paper_bucket,
            source_mode=source_mode,
            out_dir=staging,
        )
        claim = adapter.ClaimRecord(
            claim_id=unit.claim_id,
            citekey=info["citekey"],
            staging_dir=staging,
            source_mode=source_mode,
        )
    else:
        staging = claim.staging_dir

    # The batch file the Runner reads. Written rather than passed inline: `RunInputs` carries a
    # path, never claim content, and pinning through the real dispatch path is the whole point.
    batch_path = CANARY_DIR / f"pin-batch-{prof.name}.json"
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    batch_path.write_text(
        json.dumps({"claims": [{
            "claim_id": claim.claim_id, "citekey": claim.citekey,
            "staging_dir": str(staging), "source_mode": source_mode,
        }]}, indent=2),
        encoding="utf-8",
    )

    run = runner or adapter.SarolRunner(store, profile=prof.name)
    schemas = adapter._import_engine()
    materialized = store.repo_root

    observed: list[str | None] = []
    for attempt in range(repeat):
        artifacts = run.run(
            materialized,
            schemas.RunInputs(
                input_ref=str(batch_path),
                batch_id=f"canary-pin-{prof.name}-{attempt}",
                split="train",
            ),
        )
        if artifacts.status != "ok" or not artifacts.artifact_refs:
            raise RuntimeError(
                f"canary pin attempt {attempt + 1}/{repeat} did not complete "
                f"(status={artifacts.status!r}); nothing pinned"
            )
        manifest = json.loads(
            pathlib.Path(artifacts.artifact_refs[0].path).read_text(encoding="utf-8")
        )
        record = manifest["claims"][0]
        observed.append((record.get("validation") or {}).get("overall_verdict"))

    if len(set(observed)) != 1 or observed[0] is None:
        raise RuntimeError(
            f"the judge did not produce a stable verdict for {claim.claim_id} across {repeat} "
            f"dispatches: {observed}. Pinning an unstable claim turns LLM nondeterminism into a "
            "hard stop -- pick another claim or raise --repeat, but do not pin this one."
        )

    payload = {
        "profile": prof.name,
        "expected_verdict": observed[0],
        "observations": observed,
        "pinned_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "program_combined_hash": store.combined_hash,
        "split": split,
        "claim": {
            "claim_id": claim.claim_id,
            "citekey": claim.citekey,
            "staging_dir": str(staging),
            "source_mode": source_mode,
        },
        "note": (
            "Measured, not asserted: this is the verdict the real Runner produced under the "
            "program at program_combined_hash. It is one observation of a nondeterministic "
            "judge -- see this module's docstring."
        ),
    }
    path = pin_path(prof.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


# =================================================================================================
# Offline gates
# =================================================================================================


def _selftest() -> int:
    import tempfile

    checks: list[tuple[str, bool]] = []

    checks += [
        ("a profile with no pin loads as None, so the CALLER owns the policy",
         load("no-such-profile") is None),
        ("the pin path is per-profile, since a canary under one profile says nothing about "
         "another", pin_path("retrieval") != pin_path("agentic")),
        ("canary staging is separate from batch staging, so a scored pass cannot overwrite the "
         "canary's own verdict record",
         "canary" in str(canary_staging_dir("retrieval"))),
    ]

    # Round-trip a written pin without dispatching anything.
    with tempfile.TemporaryDirectory() as tmp:
        global CANARY_DIR
        original = CANARY_DIR
        try:
            CANARY_DIR = pathlib.Path(tmp)
            pin_path("fake").parent.mkdir(parents=True, exist_ok=True)
            pin_path("fake").write_text(json.dumps({
                "profile": "fake", "expected_verdict": "ACCURATE",
                "claim": {"claim_id": "7-31", "citekey": "ref_abc123",
                          "staging_dir": tmp, "source_mode": "corpus"},
            }), encoding="utf-8")
            spec = load("fake")
            checks += [
                ("a written pin loads back as a CanarySpec the Runner accepts",
                 isinstance(spec, adapter.CanarySpec)),
                ("...carrying the measured verdict", spec.expected_verdict == "ACCURATE"),
                ("...and the pinned claim", spec.claim.claim_id == "7-31"),
            ]
        finally:
            CANARY_DIR = original

    # The pin path itself, driven end to end against a FAKE runner. The prior gates only round-
    # tripped a hand-written pin through `load()`, so they would have stayed green if `pin()` had
    # stopped dispatching entirely and just written a verdict someone typed -- which is precisely
    # the "asserts a belief, not a measurement" failure this module exists to avoid.
    with tempfile.TemporaryDirectory() as tmp:
        original = CANARY_DIR
        try:
            CANARY_DIR = pathlib.Path(tmp)
            staging = pathlib.Path(tmp) / "stage"
            staging.mkdir()
            fake_claim = adapter.ClaimRecord(
                claim_id="9-9", citekey="ref_fake01", staging_dir=staging,
                source_mode="corpus",
            )

            class _Artifacts:
                def __init__(self, path):
                    self.status = "ok"
                    self.artifact_refs = (type("R", (), {"path": str(path)})(),)

            class _FakeRunner:
                """Writes a manifest carrying a verdict, exactly as SarolRunner does."""
                def __init__(self, verdicts):
                    self.verdicts = list(verdicts)
                    self.calls = 0

                def run(self, materialized, inputs):
                    mpath = pathlib.Path(tmp) / f"m{self.calls}.json"
                    mpath.write_text(json.dumps({"claims": [{
                        "claim_id": "9-9", "status": "ok",
                        "validation": {"overall_verdict": self.verdicts[self.calls]},
                    }]}), encoding="utf-8")
                    self.calls += 1
                    return _Artifacts(mpath)

            stable = _FakeRunner(["OVERSIMPLIFY", "OVERSIMPLIFY"])
            payload = pin(profile="retrieval", repeat=2, runner=stable, claim=fake_claim,
                          program_store=adapter.SarolProgramStore())
            checks += [
                ("pin() records the verdict the RUNNER returned, not one supplied by hand",
                 payload["expected_verdict"] == "OVERSIMPLIFY"),
                ("...having actually dispatched once per --repeat", stable.calls == 2),
                ("...and the written pin loads back as that same spec",
                 load("retrieval").expected_verdict == "OVERSIMPLIFY"),
                ("...stamped with the program hash it was measured against, so a pin cannot "
                 "silently outlive its program", "program_combined_hash" in payload),
            ]

            # An unstable judge must not be pinned at all -- that is the difference between a
            # guard and a coin flip fired three times an iteration.
            pin_path("retrieval").unlink()
            flaky = _FakeRunner(["ACCURATE", "OVERSIMPLIFY"])
            try:
                pin(profile="retrieval", repeat=2, runner=flaky, claim=fake_claim,
                    program_store=adapter.SarolProgramStore())
                unstable_refused = False
            except RuntimeError:
                unstable_refused = True
            checks += [
                ("a judge that disagrees with itself across --repeat is REFUSED, so LLM "
                 "nondeterminism cannot become a hard stop", unstable_refused),
                ("...and no pin file is left behind by the refusal",
                 not pin_path("retrieval").exists()),
            ]
        finally:
            CANARY_DIR = original

    # A pin that disagrees with itself is refused on LOAD -- the filename is not the authority.
    with tempfile.TemporaryDirectory() as tmp:
        original = CANARY_DIR
        try:
            CANARY_DIR = pathlib.Path(tmp)
            body = {"expected_verdict": "ACCURATE",
                    "claim": {"claim_id": "1-1", "citekey": "k", "staging_dir": tmp,
                              "source_mode": "corpus"}}
            pin_path("retrieval").parent.mkdir(parents=True, exist_ok=True)
            pin_path("retrieval").write_text(
                json.dumps({**body, "profile": "agentic", "split": "train"}), encoding="utf-8")
            checks.append((
                "a pin measured under another PROFILE is refused, not silently wired -- a canary "
                "compared against the wrong pipeline is worse than none",
                _raises(lambda: load("retrieval"), ValueError)))
            pin_path("retrieval").write_text(
                json.dumps({**body, "profile": "retrieval", "split": "dev"}), encoding="utf-8")
            checks.append((
                "a pin drawn from a HELD-OUT split is refused, since the canary claim is "
                "re-dispatched every Runner call inside the optimizer's reach",
                _raises(lambda: load("retrieval"), ValueError)))
        finally:
            CANARY_DIR = original

    checks.append((
        "pinning from a non-train split is refused at the source too, so the CLI's choices= is "
        "not the only thing standing between a held-out claim and the optimizer",
        _raises(lambda: pin(profile="retrieval", split="dev"), ValueError)))

    # --repeat is refused below 1, so "pin without measuring" is not reachable.
    try:
        pin(profile="retrieval", repeat=0)
        checks.append(("--repeat 0 is refused rather than pinning nothing", False))
    except ValueError:
        checks.append(("--repeat 0 is refused rather than pinning nothing", True))
    except Exception:
        checks.append(("--repeat 0 is refused rather than pinning nothing", False))

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


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--show", action="store_true", help="print the current pin for --profile")
    ap.add_argument("--pin", action="store_true",
                    help="MEASURE and write the pin. Dispatches real sessions and costs money.")
    ap.add_argument("--repeat", type=int, default=1,
                    help="dispatch this many times and refuse to pin unless every verdict agrees")
    ap.add_argument("--profile", default=profiles_mod.DEFAULT_PROFILE,
                    choices=sorted(profiles_mod.PROFILES))
    ap.add_argument("--split", default="train", choices=("train",),
                    help="split to draw the pinned claim from. TRAIN only, and enforced: TRAIN "
                         "gold is Tier 1 and already open to the optimizer, so a canary there "
                         "reveals nothing a held-out one would not.")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.show:
        current = describe(args.profile)
        print(json.dumps(current, indent=2) if current else
              f"no canary pinned for profile {args.profile!r}")
        return 0 if current else 1
    if args.pin:
        payload = pin(profile=args.profile, repeat=args.repeat, split=args.split)
        print(json.dumps(payload, indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
