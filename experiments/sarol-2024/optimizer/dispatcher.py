"""Drives `agentic-label-opt`'s ``run_loop`` for paper-trail, and owns the money.

The engine does not bound cost. ``RunArtifacts.cost_usd`` and ``sub_invocation_count`` are read by
nothing in ``engine/``; the only budget stop is ``token_budget_exhausted`` (`loop.py:513-521`), and
that counts the **optimizer agent's** tokens — not the Runner's, which is where essentially all of
paper-trail's spend lives. crc settled this consumer-side (Phil, 2026-08-27) and **no engine change
is being requested**; this module is paper-trail adopting the same pattern.

Three things here are not obvious and are the reason this is a module rather than a script:

* **An iteration costs THREE Runner calls, not two.** `loop.py:334` (TRAIN), `:335` (VAL), and
  `:410` (the post-commit frozen-version probe, on ``val_inputs`` again). A preflight that counts
  TRAIN only understates every landmark by a fixed ``2 x VAL``. At VAL=316 claims x 3 nested
  sessions that is **1,896 sessions per iteration** unaccounted for. :class:`CostModel` counts all
  three.

* **Two of those three calls are redundant across iteration boundaries.** Unless an iteration
  step-back-reverts, the probe at `:410` runs the newly-committed version against VAL, and then
  iteration *n+1* runs the *same* program against the *same* VAL batch at `:335`. Same bytes, same
  batch, same answer. :class:`CachingRunner` content-addresses on the materialized program's own
  bytes plus the batch id, so the second call is free. This is crc's pattern.

* **The refusal has to live in the Runner.** ``run_loop`` exposes no pre-iteration hook — ``on_iter``
  fires *after* an iteration completes, which is too late to decline to spend. The Runner is where
  the money is actually spent, so that is where :class:`BudgetGuard` is consulted: before dispatching
  a batch it prices the worst case for *finishing the current iteration* from this point, and
  returns ``infra_error`` rather than starting something it cannot afford to complete. A
  whole-run preflight runs once up front as well, but the per-call check is the enforcement.

Cost accounting uses **real metered spend** — the ``total_cost_usd`` the CLI reports, summed by
``adapter.SarolRunner``. ``parse_verdict.estimate_cost_usd`` is retained for *forecasting* only
(:class:`CostModel`); it is the wrong source of truth for accounting, because its ``PRICING`` table
covers four model ids and contributes nothing for anything unlisted, it falls back to a 0.85
input/output split since real ledger rows carry null token counts, and the ledger it reads is
written by a hand-transcription step no committed prompt performs.

Usage:
    dispatcher.py --preflight                 # the per-landmark cost table
    dispatcher.py --preflight --per-session-usd 0.05
    dispatcher.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import adapter  # noqa: E402
from adapter import STAGES, SarolProgramStore  # noqa: E402

#: `sarol`'s graduated-N TRAIN ramp (D13). Nested, so the same version is comparable across levels.
TRAIN_LADDER: tuple[int, ...] = (10, 25, 50, 100, 200, 2141)

#: The fixed VAL split (dev), and the sealed TEST split. TEST is here for the preflight's sake
#: only -- it is unsealed exactly once, via the --confirm-unseal tripwire, and never in this loop.
VAL_SIZE = 316
TEST_SIZE = 606

#: Rough per-nested-session spend. A forecasting input, deliberately explicit rather than buried:
#: the real number replaces it after the first metered claim, and the preflight is only as honest
#: as this value.
DEFAULT_PER_SESSION_USD = 0.05


# =================================================================================================
# Cost model
# =================================================================================================


@dataclass(frozen=True)
class CostModel:
    """Prices an iteration. The arithmetic the Verification table gates a paid run on."""

    per_session_usd: float = DEFAULT_PER_SESSION_USD
    stages_per_claim: int = len(STAGES)
    val_size: int = VAL_SIZE

    def claim_cost(self) -> float:
        return self.stages_per_claim * self.per_session_usd

    def batch_cost(self, n_claims: int) -> float:
        return n_claims * self.claim_cost()

    def iteration_cost(self, train_n: int, *, probe_cached: bool = False) -> float:
        """TRAIN + current-VAL + probe-VAL.

        ``probe_cached=True`` prices an iteration whose probe is served from
        :class:`CachingRunner` -- one VAL call instead of two.
        """
        val_calls = 1 if probe_cached else 2
        return self.batch_cost(train_n) + val_calls * self.batch_cost(self.val_size)

    def sessions_per_iteration(self, train_n: int, *, probe_cached: bool = False) -> int:
        val_calls = 1 if probe_cached else 2
        return (train_n + val_calls * self.val_size) * self.stages_per_claim

    def table(self, ladder: tuple[int, ...] = TRAIN_LADDER) -> list[dict[str, Any]]:
        rows = []
        for n in ladder:
            rows.append(
                {
                    "train_n": n,
                    "sessions_uncached": self.sessions_per_iteration(n),
                    "sessions_cached": self.sessions_per_iteration(n, probe_cached=True),
                    "usd_uncached": round(self.iteration_cost(n), 2),
                    "usd_cached": round(self.iteration_cost(n, probe_cached=True), 2),
                    "train_only_usd": round(self.batch_cost(n), 2),
                }
            )
        return rows

    def render_table(self, ladder: tuple[int, ...] = TRAIN_LADDER) -> str:
        header = (
            f"{'TRAIN N':>8}  {'sessions':>10}  {'$/iter':>10}  "
            f"{'$/iter cached':>14}  {'TRAIN-only $':>13}  {'understated by':>15}"
        )
        lines = [
            f"per-session ${self.per_session_usd:.4f}   "
            f"{self.stages_per_claim} sessions/claim   VAL={self.val_size}",
            "",
            header,
            "-" * len(header),
        ]
        for row in self.table(ladder):
            gap = row["usd_uncached"] - row["train_only_usd"]
            lines.append(
                f"{row['train_n']:>8}  {row['sessions_uncached']:>10,}  "
                f"${row['usd_uncached']:>9,.2f}  ${row['usd_cached']:>13,.2f}  "
                f"${row['train_only_usd']:>12,.2f}  ${gap:>14,.2f}"
            )
        lines += [
            "",
            "The last column is what a TRAIN-only preflight misses: a fixed 2 x VAL every",
            "iteration (loop.py:335 and :410). It does not shrink as TRAIN grows.",
        ]
        return "\n".join(lines)


# =================================================================================================
# Budget guard
# =================================================================================================


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class BudgetGuard:
    """Refuses to start what it cannot afford to finish.

    The engine has no pre-iteration hook (``on_iter`` fires after the fact), so this is consulted
    from inside the Runner wrapper -- the point where spend actually happens.
    """

    max_budget_usd: float
    cost_model: CostModel = field(default_factory=CostModel)
    train_n: int = TRAIN_LADDER[0]
    spent_usd: float = 0.0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_budget_usd - self.spent_usd)

    def record(self, usd: float) -> None:
        self.spent_usd += max(0.0, float(usd or 0.0))

    def worst_case_to_finish_iteration(self, split: str, *, probe_cached: bool = False) -> float:
        """Cost of this call plus whatever else the current iteration still owes.

        The engine's per-iteration sequence is TRAIN -> VAL -> (agent) -> probe-VAL. Pricing from
        the current position is what makes "refuse to start" mean "refuse to start something that
        would strand the iteration half-paid-for".
        """
        val = self.cost_model.batch_cost(self.cost_model.val_size)
        train = self.cost_model.batch_cost(self.train_n)
        if split == "train":
            remaining_val_calls = 1 if probe_cached else 2
            return train + remaining_val_calls * val
        # A VAL call: either the current-version score (probe still owed) or the probe itself.
        return val if probe_cached else 2 * val

    def check(self, split: str, *, probe_cached: bool = False) -> str | None:
        need = self.worst_case_to_finish_iteration(split, probe_cached=probe_cached)
        if need > self.remaining_usd:
            return (
                f"budget: finishing this {split} iteration needs ~${need:,.2f}, "
                f"${self.remaining_usd:,.2f} remains of ${self.max_budget_usd:,.2f}"
            )
        return None


# =================================================================================================
# Caching + budgeted Runner wrapper
# =================================================================================================


def program_digest(materialized_path: pathlib.Path, rel_paths: list[str]) -> str:
    """Order-stable hash over the materialized program's own bytes.

    Content-addressed on purpose: the probe and the next iteration's VAL call are the same work
    exactly when the program bytes and the batch are the same, which is a property of content,
    not of the tag or the iteration number (a step-back revert breaks any name-based assumption).
    """
    h = hashlib.sha256()
    for rel in sorted(rel_paths):
        target = pathlib.Path(materialized_path) / rel
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(target.read_bytes() if target.exists() else b"<missing>")
        h.update(b"\0")
    return h.hexdigest()


class CachingRunner:
    """Wraps a Runner with the budget refusal and the probe cache.

    Never raises: like the Runner it wraps, every refusal is a ``RunArtifacts`` status the Scorer
    can decline, because the engine wraps none of its three Runner calls in a try/except.
    """

    def __init__(
        self,
        inner,
        program_store: SarolProgramStore,
        *,
        budget: BudgetGuard | None = None,
        enable_cache: bool = True,
    ) -> None:
        self.inner = inner
        self.program_store = program_store
        self.budget = budget
        self.enable_cache = enable_cache
        self._cache: dict[tuple[str, str, str], Any] = {}
        self.hits = 0
        self.misses = 0
        self.refusals = 0

    def _key(self, materialized_path, inputs) -> tuple[str, str, str]:
        digest = program_digest(materialized_path, [e["path"] for e in self.program_store.entries])
        return (digest, str(inputs.input_ref), inputs.split)

    def run(self, materialized_path, inputs):  # positional -- matches the engine's call sites
        schemas = adapter._import_engine()
        key = self._key(materialized_path, inputs) if self.enable_cache else None

        if key is not None and key in self._cache:
            self.hits += 1
            return self._cache[key]

        if self.budget is not None:
            # If the probe for this exact program+batch is already cached, the iteration owes one
            # fewer VAL call -- so price the refusal against the cheaper, truthful sequence.
            probe_cached = key is not None and key in self._cache
            reason = self.budget.check(inputs.split, probe_cached=probe_cached)
            if reason is not None:
                self.refusals += 1
                return schemas.RunArtifacts(
                    batch_id=inputs.batch_id,
                    status="infra_error",
                    artifact_refs=(),
                    error=schemas.ErrorInfo(code="BUDGET_EXCEEDED", message_redacted=reason),
                    sub_invocation_count=0,
                    cost_usd=0.0,
                )

        self.misses += 1
        artifacts = self.inner.run(materialized_path, inputs)

        if self.budget is not None:
            self.budget.record(artifacts.cost_usd or 0.0)
        if key is not None and artifacts.status == "ok":
            # Only a clean run is reusable. Caching a timeout would make one flaky batch permanent.
            self._cache[key] = artifacts
        return artifacts

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "refusals": self.refusals}


# =================================================================================================
# Wiring
# =================================================================================================


def build_components(
    *,
    max_budget_usd: float,
    train_n: int,
    per_session_usd: float = DEFAULT_PER_SESSION_USD,
    working_checkout: pathlib.Path = adapter.REPO_ROOT,
    invoke=None,
    paperclip_version_probe=None,
    gold_resolver=None,
):
    """Assemble the four protocol objects plus the guards, without running anything."""
    store = SarolProgramStore()
    cost_model = CostModel(per_session_usd=per_session_usd)
    budget = BudgetGuard(max_budget_usd=max_budget_usd, cost_model=cost_model, train_n=train_n)
    runner = CachingRunner(
        adapter.SarolRunner(
            store,
            working_checkout=working_checkout,
            invoke=invoke,
            paperclip_version_probe=paperclip_version_probe,
        ),
        store,
        budget=budget,
    )
    return {
        "program_store": store,
        "runner": runner,
        "scorer": adapter.SarolScorer(gold_resolver=gold_resolver),
        "release_builder": adapter.SarolReleaseBuilder(),
        "build_mistake_corpus": adapter.build_mistake_corpus,
        "budget": budget,
        "cost_model": cost_model,
    }


def preflight(cost_model: CostModel, *, train_n: int, iterations: int, max_budget_usd: float):
    """Whole-run affordability check. Returns (ok, message)."""
    per_iter = cost_model.iteration_cost(train_n)
    per_iter_cached = cost_model.iteration_cost(train_n, probe_cached=True)
    # Iteration 1 cannot hit the probe cache; every later one can.
    worst = per_iter + max(0, iterations - 1) * per_iter_cached
    ok = worst <= max_budget_usd
    msg = (
        f"{iterations} iteration(s) at TRAIN={train_n}: "
        f"~${worst:,.2f} worst case (${per_iter:,.2f} first, ${per_iter_cached:,.2f} thereafter) "
        f"against a ${max_budget_usd:,.2f} budget"
    )
    return ok, msg


# =================================================================================================
# Offline gates
# =================================================================================================


def _selftest() -> int:
    checks: list[tuple[str, bool]] = []
    cm = CostModel(per_session_usd=0.05)

    # -- the arithmetic the Verification table gates on ---------------------------------------
    train_only = cm.batch_cost(50)
    full = cm.iteration_cost(50)
    checks += [
        ("an iteration prices THREE runner calls, not one",
         full == train_only + 2 * cm.batch_cost(VAL_SIZE)),
        ("a TRAIN-only estimate understates by exactly 2 x VAL",
         round(full - train_only, 6) == round(2 * cm.batch_cost(VAL_SIZE), 6)),
        ("the shortfall does not shrink as TRAIN grows",
         round(cm.iteration_cost(2141) - cm.batch_cost(2141), 6)
         == round(cm.iteration_cost(10) - cm.batch_cost(10), 6)),
        ("VAL=316 x 3 sessions x 2 calls is the 1,896 sessions the plan names",
         2 * VAL_SIZE * len(STAGES) == 1896),
        ("caching the probe removes exactly one VAL call",
         round(cm.iteration_cost(50) - cm.iteration_cost(50, probe_cached=True), 6)
         == round(cm.batch_cost(VAL_SIZE), 6)),
        ("the ladder is sarol's D13 ramp", TRAIN_LADDER[-1] == 2141),
    ]

    # -- budget refusal ------------------------------------------------------------------------
    tight = BudgetGuard(max_budget_usd=1.0, cost_model=cm, train_n=50)
    roomy = BudgetGuard(max_budget_usd=1_000_000.0, cost_model=cm, train_n=50)
    checks += [
        ("a too-small budget refuses a TRAIN call", tight.check("train") is not None),
        ("...and says what it needed", "budget:" in (tight.check("train") or "")),
        ("an ample budget does not refuse", roomy.check("train") is None),
    ]
    roomy.record(999_999.0)
    checks.append(("spend is subtracted from the remaining budget", roomy.check("train") is not None))

    # -- whole-run preflight -------------------------------------------------------------------
    ok_small, _ = preflight(cm, train_n=10, iterations=1, max_budget_usd=1_000_000)
    ok_big, msg = preflight(cm, train_n=2141, iterations=10, max_budget_usd=100)
    checks += [
        ("an affordable run passes preflight", ok_small),
        ("an unaffordable run is refused before it starts", not ok_big),
        ("...and the message prices first-vs-subsequent iterations", "thereafter" in msg),
    ]

    # -- engine-facing behaviour ----------------------------------------------------------------
    if (adapter.engine_path() / "engine" / "schemas.py").exists():
        import tempfile

        schemas = adapter._import_engine()
        store = SarolProgramStore()

        with tempfile.TemporaryDirectory() as tmp:
            tree = pathlib.Path(tmp) / "materialized"
            for entry in store.entries:
                dst = tree / entry["path"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes((store.repo_root / entry["path"]).read_bytes())

            batch = pathlib.Path(tmp) / "batch.json"
            batch.write_text(json.dumps({"claims": []}), encoding="utf-8")
            inputs = schemas.RunInputs(input_ref=str(batch), batch_id="b1", split="val")

            calls: list[str] = []

            class _Inner:
                def run(self, materialized_path, inp):
                    calls.append(inp.split)
                    return schemas.RunArtifacts(
                        batch_id=inp.batch_id, status="ok", artifact_refs=(),
                        sub_invocation_count=3, cost_usd=1.25,
                    )

            budget = BudgetGuard(max_budget_usd=1_000_000.0, cost_model=cm, train_n=10)
            caching = CachingRunner(_Inner(), store, budget=budget)

            first = caching.run(tree, inputs)
            second = caching.run(tree, inputs)
            checks += [
                ("the first VAL call actually runs", first.status == "ok" and len(calls) == 1),
                ("the identical probe/VAL pair is served from cache", len(calls) == 1),
                ("...and returns the same artifacts", second is first),
                ("cache stats are honest", caching.stats()["hits"] == 1),
                ("real metered spend is recorded, not the estimate", budget.spent_usd == 1.25),
            ]

            # A changed program byte must miss the cache -- this is the whole point of
            # content-addressing rather than keying on a tag or iteration number.
            editable = tree / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
            editable.write_text(
                editable.read_text(encoding="utf-8") + "\n<!-- optimizer edit -->\n",
                encoding="utf-8",
            )
            caching.run(tree, inputs)
            checks.append(("an edited program misses the cache", len(calls) == 2))

            # A failed run must not be cached.
            class _Failing:
                def run(self, materialized_path, inp):
                    return schemas.RunArtifacts(
                        batch_id=inp.batch_id, status="timeout", artifact_refs=(), cost_usd=0.0
                    )

            flaky = CachingRunner(_Failing(), store, budget=None)
            flaky.run(tree, inputs)
            flaky.run(tree, inputs)
            checks.append(("a timeout is never cached", flaky.misses == 2))

            # Budget refusal returns infra_error rather than raising or spending.
            broke_calls: list[str] = []

            class _Spy:
                def run(self, materialized_path, inp):
                    broke_calls.append(inp.split)
                    return schemas.RunArtifacts(
                        batch_id=inp.batch_id, status="ok", artifact_refs=(), cost_usd=0.0
                    )

            broke = CachingRunner(
                _Spy(), store,
                budget=BudgetGuard(max_budget_usd=0.01, cost_model=cm, train_n=50),
            )
            refused = broke.run(tree, schemas.RunInputs(
                input_ref=str(batch), batch_id="b2", split="train"))
            checks += [
                ("an unaffordable iteration returns infra_error", refused.status == "infra_error"),
                ("...naming the budget", refused.error is not None
                 and refused.error.code == "BUDGET_EXCEEDED"),
                ("...without dispatching anything", not broke_calls),
            ]

            digest_a = program_digest(tree, [e["path"] for e in store.entries])
            digest_b = program_digest(tree, [e["path"] for e in store.entries])
            checks.append(("the program digest is stable", digest_a == digest_b))
    else:
        checks.append((f"engine not found at {adapter.engine_path()} -- engine checks SKIPPED", True))

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="print the per-landmark cost table")
    ap.add_argument("--per-session-usd", type=float, default=DEFAULT_PER_SESSION_USD)
    ap.add_argument("--max-budget-usd", type=float, default=None)
    ap.add_argument("--train-n", type=int, default=None)
    ap.add_argument("--iterations", type=int, default=1)
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    cost_model = CostModel(per_session_usd=args.per_session_usd)
    if args.preflight:
        print(cost_model.render_table())
        if args.max_budget_usd is not None and args.train_n is not None:
            ok, msg = preflight(
                cost_model,
                train_n=args.train_n,
                iterations=args.iterations,
                max_budget_usd=args.max_budget_usd,
            )
            print(f"\n{'OK  ' if ok else 'REFUSE  '}{msg}")
            return 0 if ok else 1
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
