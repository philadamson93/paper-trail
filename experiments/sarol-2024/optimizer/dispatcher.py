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
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import adapter  # noqa: E402
import profiles as profiles_mod  # noqa: E402
import sampling  # noqa: E402
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
#:
#: CALIBRATED 2026-09-02 against the first metered claim, exactly as the line above anticipated.
#: One real `retrieval` adjudicator session on dev claim 0 (a 123-chunk, 49KB cited paper, model
#: `opus`) cost **$1.0026** and took 98.7s. The previous placeholder was 0.05 -- understating every
#: forecast by ~20x, which is the dangerous direction: it would have cleared a "$32/iteration" run
#: that actually costs ~$647. One sample, so treat this as order-of-magnitude rather than precise,
#: and re-measure when the profile, model or claim mix changes.
DEFAULT_PER_SESSION_USD = 1.00


# =================================================================================================
# Cost model
# =================================================================================================


@dataclass(frozen=True)
class CostModel:
    """Prices an iteration. The arithmetic the Verification table gates a paid run on."""

    per_session_usd: float = DEFAULT_PER_SESSION_USD
    #: Sessions one claim costs. **Derive this from the profile** rather than passing it: under
    #: `retrieval` a claim is one session, not three, and hard-coding 3 overstates a Phase 1
    #: iteration by ~3x (C6.6). `for_profile()` is the way in.
    stages_per_claim: int = len(STAGES)
    val_size: int = VAL_SIZE
    #: Display only -- which rung these numbers describe. A cost table without it is ambiguous
    #: between two experiments that differ by 3x.
    profile_name: str = profiles_mod.DEFAULT_PROFILE
    #: Open Questions §12, resolved 2026-09-02 (Phil): the canary fires once per **Runner call**,
    #: which is what the landed Runner already does -- three firings per iteration, so a break
    #: between TRAIN and VAL is caught inside the iteration it happened in rather than one later.
    #: Priced here rather than left as an untracked extra, which was the condition attached to
    #: either answer. Set False to price the cheaper once-per-iteration reading.
    canary_per_runner_call: bool = True
    #: Whether a canary is configured at all. No canary, no canary sessions.
    canary_enabled: bool = True

    @classmethod
    def for_profile(cls, profile, **kwargs) -> "CostModel":
        """Build a model whose per-claim session count comes from the profile (C6.6)."""
        prof = profiles_mod.get(profile)
        return cls(stages_per_claim=prof.sessions_per_claim, profile_name=prof.name, **kwargs)

    def claim_cost(self) -> float:
        return self.stages_per_claim * self.per_session_usd

    def batch_cost(self, n_claims: int) -> float:
        return n_claims * self.claim_cost()

    def runner_calls(self, *, probe_cached: bool = False) -> int:
        """TRAIN + current-VAL + probe-VAL. A cached probe is served without calling the Runner."""
        return 2 if probe_cached else 3

    def canary_sessions(self, *, probe_cached: bool = False) -> int:
        """Sessions the canary itself costs per iteration.

        One canary claim costs a full ``stages_per_claim`` -- it goes through the same dispatch
        path as a scored claim, which is the point of it.
        """
        if not self.canary_enabled:
            return 0
        calls = self.runner_calls(probe_cached=probe_cached) if self.canary_per_runner_call else 1
        return calls * self.stages_per_claim

    def iteration_cost(self, train_n: int, *, probe_cached: bool = False) -> float:
        """TRAIN + current-VAL + probe-VAL, plus the canary.

        ``probe_cached=True`` prices an iteration whose probe is served from
        :class:`CachingRunner` -- one VAL call instead of two.
        """
        return self.sessions_per_iteration(train_n, probe_cached=probe_cached) * self.per_session_usd

    def sessions_per_iteration(self, train_n: int, *, probe_cached: bool = False) -> int:
        val_calls = 1 if probe_cached else 2
        scored = (train_n + val_calls * self.val_size) * self.stages_per_claim
        return scored + self.canary_sessions(probe_cached=probe_cached)

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
            f"profile {self.profile_name}   per-session ${self.per_session_usd:.4f}   "
            f"{self.stages_per_claim} sessions/claim   VAL={self.val_size}   "
            + (
                f"canary {self.canary_sessions()} sessions/iter "
                f"({'per Runner call' if self.canary_per_runner_call else 'once per iter'})"
                if self.canary_enabled
                else "no canary"
            ),
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


PROMPT_PATH = _HERE / "prompt" / "optimizer-instructions.md"
CONTEXT_DIR = _HERE / "context"


class OptimizerAgent:
    """The optimizer's own headless Claude Code session — the engine's ``agent`` port.

    It edits files in ``repo_root`` and exits; the harness commits and tags. Note this is the one
    port the engine *does* budget (`loop.py:513-521` counts these tokens), which is exactly
    backwards from where paper-trail's spend actually is — hence :class:`BudgetGuard` on the
    Runner side.
    """

    def __init__(
        self,
        *,
        repo_root: pathlib.Path,
        prompt_path: pathlib.Path = PROMPT_PATH,
        context_dir: pathlib.Path = CONTEXT_DIR,
        invoke=None,
        timeout_seconds: float = 3600.0,
        max_budget_usd: float = 20.0,
        model: str = "opus",
    ) -> None:
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.prompt_path = pathlib.Path(prompt_path)
        self.context_dir = pathlib.Path(context_dir)
        self.invoke = invoke or adapter.headless_claude_invoke
        self.timeout_seconds = timeout_seconds
        self.max_budget_usd = max_budget_usd
        self.model = model

    def agent_instructions(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")

    def command(self, iter_n: int, materialized_path) -> list[str]:
        return [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            (
                f"Iteration {iter_n}. The frozen program for this iteration is materialized at "
                f"{materialized_path}. Your reference docs are in {self.context_dir}. "
                "Follow your standing instructions."
            ),
            "--append-system-prompt",
            self.agent_instructions(),
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--setting-sources",
            "project",
            "--strict-mcp-config",
            "--max-budget-usd",
            str(self.max_budget_usd),
        ]

    def run(self, *, iter_n: int, materialized_path=None):  # keyword-only -- loop.py:398
        res = self.invoke(
            self.command(iter_n, materialized_path), self.repo_root, self.timeout_seconds
        )
        return adapter.GuardedOutcome(
            exit_code=124 if res.timed_out else res.exit_code,
            detail=res.detail,
            token_usage={},
            cost_usd=res.cost_usd,
            attempting_step_back=False,
        )


class _FakeStore:
    """Minimal stand-in for `SarolProgramStore` in the C6.9 negative control -- only `repo_root`
    is read before the isolation check fires, so building a real store would be noise."""

    def __init__(self, repo_root):
        self.repo_root = pathlib.Path(repo_root)


def _raises_valueerror(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


def val_isolation_problem(val_root, repo_root) -> str | None:
    """Is the VAL output root readable by the optimizer? (C6.9). Returns a problem, or None.

    The optimizer's session runs with cwd = ``repo_root`` and no ``--add-dir``, so its readable
    scope is that tree. VAL is Tier 2 -- **scalar only** -- and the release builder already strips
    VAL's breakdown down to the scalar plus completeness metadata. But stripping the *release* is
    only half of it: if the VAL run manifest and its per-example outputs sit inside the repo, the
    optimizer can simply open them and read the held-out set's per-claim behaviour directly,
    bypassing the release boundary entirely.

    So the boundary is a filesystem fact, not a payload convention, and this is what asserts it.
    Note the earlier diagnosis in an draft of C6.9 -- that TRAIN and VAL "share one root separated
    only by a subdirectory name" -- was wrong: ``RunInputs.batch_id`` already differs per split, so
    the derived roots differ. The real and still-live requirement is the one checked here.
    """
    if val_root is None:
        return None
    val = pathlib.Path(val_root).resolve()
    repo = pathlib.Path(repo_root).resolve()
    if val == repo or repo in val.parents:
        return (
            f"VAL output root {val} is inside the optimizer's readable tree {repo}; "
            "the held-out set's per-claim outputs would be directly readable, which defeats the "
            "Tier 2 scalar-only boundary the release builder enforces on the payload"
        )
    return None


def build_components(
    *,
    max_budget_usd: float,
    train_n: int,
    per_session_usd: float = DEFAULT_PER_SESSION_USD,
    working_checkout: pathlib.Path = adapter.REPO_ROOT,
    invoke=None,
    paperclip_version_probe=None,
    gold_resolver=None,
    canary=None,
    require_command: bool = True,
    per_call_max_budget_usd: float = 2.0,
    agent_invoke=None,
    program_store: SarolProgramStore | None = None,
    profile=None,
    train_output_root: pathlib.Path | None = None,
    val_output_root: pathlib.Path | None = None,
    val_n: int | None = None,
):
    """Assemble the four protocol objects, the guards, and the guarded optimizer agent.

    The agent is wrapped in :class:`adapter.ContractGuardedAgent` **here**, not at the call site,
    so there is no way to wire this loop up without the contract-file re-hash in place — an
    unguarded agent was previously possible simply by forgetting.
    """
    store = program_store or SarolProgramStore()
    prof = profiles_mod.get(profile)
    # `val_n` is the cost lever, and it has to reach the cost model or the preflight prices a run
    # that is not the one about to happen. VAL is charged TWICE per iteration at a fixed size, so
    # at TRAIN=10 it is ~98% of the bill -- subsampling TRAIN alone barely moves it.
    cost_model = CostModel.for_profile(
        prof, per_session_usd=per_session_usd, val_size=val_n or VAL_SIZE
    )
    # C6.9. Stated, not derived: `train_output_root` is where the per-claim mistake corpus lands
    # and must be readable by the optimizer; `val_output_root` must not be.
    roots = {}
    if train_output_root is not None:
        roots["train"] = pathlib.Path(train_output_root)
    if val_output_root is not None:
        roots["val"] = pathlib.Path(val_output_root)
    leak = val_isolation_problem(val_output_root, store.repo_root)
    if leak:
        raise ValueError(f"VAL isolation (C6.9): {leak}")
    budget = BudgetGuard(max_budget_usd=max_budget_usd, cost_model=cost_model, train_n=train_n)
    runner = CachingRunner(
        adapter.SarolRunner(
            store,
            working_checkout=working_checkout,
            invoke=invoke,
            paperclip_version_probe=paperclip_version_probe,
            canary=canary,
            require_command=require_command,
            per_call_max_budget_usd=per_call_max_budget_usd,
            profile=prof,
            output_roots=roots,
        ),
        store,
        budget=budget,
    )
    agent = adapter.ContractGuardedAgent(
        OptimizerAgent(repo_root=store.repo_root, invoke=agent_invoke),
        store,
        tree_root=store.repo_root,
    )
    return {
        "program_store": store,
        "runner": runner,
        "scorer": adapter.SarolScorer(
            gold_resolver=gold_resolver, mistakes_root=train_output_root
        ),
        "profile": prof,
        "release_builder": adapter.SarolReleaseBuilder(),
        "build_mistake_corpus": adapter.build_mistake_corpus,
        "agent": agent,
        "budget": budget,
        "cost_model": cost_model,
    }


def run_optimization(
    *,
    iterations: int,
    run_id: str,
    train_input_ref: str,
    val_input_ref: str,
    max_budget_usd: float,
    train_n: int,
    materialize_root: pathlib.Path,
    train_output_root: pathlib.Path | None = None,
    val_output_root: pathlib.Path | None = None,
    profile=None,
    per_session_usd: float = DEFAULT_PER_SESSION_USD,
    current_tag: str = "program-v0",
    components: dict | None = None,
    train_schedule: "list[int] | None" = None,
    draw_mode: str = "cumulative",
    val_n: int | None = None,
    sampling_root: pathlib.Path | None = None,
    **component_kwargs,
):
    """Drive the engine's ``run_loop``. This is the entrypoint the plan's Files-to-create names.

    A whole-run affordability check runs before anything is dispatched; the per-iteration refusal
    still lives in :class:`CachingRunner`, because ``run_loop`` exposes no pre-iteration hook.

    **Graduated N.** Pass ``train_schedule`` (e.g. ``[5, 10, 20]``) to grow the TRAIN batch across
    iterations instead of running a fixed cohort every time — the engine takes ``train_inputs`` as
    a factory, so this needs no engine change. ``draw_mode`` selects `sampling`'s cumulative /
    fresh / reproduce semantics. Omit ``train_schedule`` and the old static-batch behaviour is
    unchanged, which is what every existing caller and gate relies on.

    ⚠ **The ramp is not the cost fix on its own.** An iteration is three Runner calls, two of them
    VAL at a fixed size, so at TRAIN=10 roughly 98% of the bill is VAL. ``val_n`` is the knob that
    actually moves the number; ``train_schedule`` is the knob that controls what the optimizer
    learns from. Both are priced, and the preflight below uses the ramp's TOP rung so the check
    describes the most expensive iteration the run can reach, not its cheapest.
    """
    engine_root = adapter.engine_path()
    if str(engine_root) not in sys.path:
        sys.path.insert(0, str(engine_root))
    from engine.loop import run_loop  # noqa: PLC0415
    from engine.schemas import RunInputs  # noqa: PLC0415

    # A real run must SAY where its outputs go. Both roots are load-bearing and neither has a
    # safe default: `train_output_root` is where the per-claim mistake corpus lands (C6.8 -- with
    # no root the optimizer silently drops back to counts-only, the exact defect C6.8 repairs),
    # and `val_output_root` must lie outside the optimizer's readable tree (C6.9), which no
    # derived default can promise. Refused here rather than in `build_components` so selftests can
    # still assemble components freely; this function is the real-run entrypoint.
    if components is None:
        missing = [
            name
            for name, value in (
                ("train_output_root", train_output_root),
                ("val_output_root", val_output_root),
            )
            if value is None
        ]
        if missing:
            raise ValueError(
                f"a real run must specify {', '.join(missing)}: "
                "TRAIN's root carries the per-claim mistake corpus (C6.8) and VAL's must sit "
                "outside the optimizer's readable tree (C6.9); neither can be safely derived"
            )
        # Selectable != runnable. `agentic` and `paperclip` are fully specified and correctly
        # priced, but /sarol-eval-item implements only the adjudicator stage, so they would abort
        # on the first claim -- after the session has been paid for. Refuse at the entrypoint.
        blocked = profiles_mod.unrunnable_reason(profile)
        if blocked:
            raise ValueError(blocked)

    # The ramp's top rung, not its first: the affordability check has to describe the most
    # expensive iteration the run can reach. Checking rung 0 would clear a run that cannot pay for
    # its own last iteration -- and the engine stops nothing.
    peak_train_n = max(train_schedule) if train_schedule else train_n

    parts = components or build_components(
        max_budget_usd=max_budget_usd,
        train_n=peak_train_n,
        per_session_usd=per_session_usd,
        profile=profile,
        train_output_root=train_output_root,
        val_output_root=val_output_root,
        val_n=val_n,
        **component_kwargs,
    )

    ok, message = preflight(
        parts["cost_model"],
        train_n=peak_train_n,
        iterations=iterations,
        max_budget_usd=max_budget_usd,
    )
    if not ok:
        raise BudgetExceeded(message)

    return run_loop(
        iterations=iterations,
        run_id=run_id,
        repo_root=parts["program_store"].repo_root,
        program_store=parts["program_store"],
        runner=parts["runner"],
        scorer=parts["scorer"],
        release_builder=parts["release_builder"],
        agent=parts["agent"],
        # A factory when a ramp was asked for, a fixed batch otherwise. `run_loop` accepts either
        # (`train_inputs: RunInputs | Callable[[int], RunInputs]`), so the graduated cohort needs
        # no engine change -- the same seam crc drives its growing batch through.
        train_inputs=(
            sampling.train_inputs_factory(
                schedule=train_schedule,
                mode=draw_mode,
                split="train",
                run_id=run_id,
                staging_root=pathlib.Path(sampling_root or train_output_root) / "staging",
                batch_root=pathlib.Path(sampling_root or train_output_root) / "batches",
                history_path=pathlib.Path(sampling_root or train_output_root) / "draw_history.json",
            )
            if train_schedule
            else RunInputs(
                input_ref=train_input_ref, batch_id=f"{run_id}-train", split="train"
            )
        ),
        val_inputs=RunInputs(input_ref=val_input_ref, batch_id=f"{run_id}-val", split="val"),
        task_config={
            "rubric_variant": adapter.validate_sarol.SAROL_VARIANT,
            "profile": parts["profile"].name,
        },
        # C6.5: a resume whose profile differs from the recorded one must STOP, not silently
        # continue a curve built from two different systems. The engine's frontier is a bare
        # scalar and cannot notice this on its own.
        hard_fields={
            "profile": parts["profile"].name,
            "retrieval_k": parts["profile"].retrieval_k,
            "rubric_variant": adapter.validate_sarol.SAROL_VARIANT,
        },
        materialize_root=pathlib.Path(materialize_root),
        build_mistake_corpus=parts["build_mistake_corpus"],
        current_tag=current_tag,
    )


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


def _seed_repo(dest: pathlib.Path, store: SarolProgramStore) -> str:
    """Build a throwaway checkout holding exactly the frozen fileset, tagged `program-v0`."""
    def run(*args: str) -> str:
        proc = subprocess.run(
            args, cwd=str(dest), capture_output=True, text=True, check=True,
            env={"PATH": os.environ.get("PATH", ""), "HOME": str(dest),
                 "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return proc.stdout.strip()

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "selftest@example.invalid")
    run("git", "config", "user.name", "selftest")
    for entry in store.entries:
        dst = dest / entry["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(store.repo_root / entry["path"], dst)
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "program-v0")
    run("git", "tag", "program-v0")
    return run("git", "rev-parse", "HEAD")


def _integration_checks(schemas) -> list[tuple[str, bool]]:
    """Drive the engine's REAL ``run_loop`` and prove the contract guard stops it before commit.

    This is the check the isolated `adapter.py --selftest` cannot make. That one constructs a
    :class:`adapter.ContractGuardedAgent` by hand and asserts it returns nonzero — which proves the
    guard works, not that the loop is actually wired to it, and not that a nonzero exit really does
    land before ``commit_version``. Here the engine drives everything: if the wiring in
    :func:`build_components` were removed, or if the engine committed before checking the agent's
    exit code, this fails.
    """
    import tempfile

    from engine.loop import LoopStop, run_loop  # noqa: PLC0415

    checks: list[tuple[str, bool]] = []

    class _Runner:
        def run(self, materialized_path, inputs):
            return schemas.RunArtifacts(
                batch_id=inputs.batch_id, status="ok", artifact_refs=(), cost_usd=0.0
            )

    class _Scorer:
        def score(self, artifacts, split, task_config):
            return schemas.ScoreResult(
                primary_metric=schemas.PrimaryMetric(
                    name="sarol_3way_macro_f1", value=0.4, higher_is_better=True
                ),
                breakdown={"scored": True, "n_total": 1, "n_invalid": 0},
                task_config={**task_config, "_split": split},
            )

    class _MutatingAgent:
        """Stands in for an optimizer session that edits a file it must not touch."""

        def __init__(self, root: pathlib.Path) -> None:
            self.root = root
            self.ran = 0

        def run(self, *, iter_n: int, materialized_path=None):
            self.ran += 1
            target = self.root / "experiments/sarol-2024/specs/verdict_enum_sarol.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\nSNEAKY_NEW_LABEL\n", encoding="utf-8"
            )
            return adapter.GuardedOutcome(exit_code=0, detail=f"mutated on iter {iter_n}")

    with tempfile.TemporaryDirectory() as tmp:
        repo = pathlib.Path(tmp) / "repo"
        repo.mkdir()
        real_store = SarolProgramStore()
        _seed_repo(repo, real_store)

        store = SarolProgramStore(repo_root=repo)
        inner = _MutatingAgent(repo)
        guarded = adapter.ContractGuardedAgent(inner, store, tree_root=repo)

        checks.append(
            ("the seeded checkout starts with contract files matching the freeze",
             not store.verify_contract_files())
        )

        stopped = None
        try:
            run_loop(
                iterations=1,
                run_id="selftest",
                repo_root=repo,
                program_store=store,
                runner=_Runner(),
                scorer=_Scorer(),
                release_builder=adapter.SarolReleaseBuilder(),
                agent=guarded,
                train_inputs=schemas.RunInputs(
                    input_ref="unused", batch_id="t", split="train"),
                val_inputs=schemas.RunInputs(input_ref="unused", batch_id="v", split="val"),
                task_config={},
                materialize_root=pathlib.Path(tmp) / "materialized",
                current_tag="program-v0",
            )
        except LoopStop as exc:
            stopped = str(exc)

        tags = subprocess.run(
            ["git", "tag"], cwd=str(repo), capture_output=True, text=True
        ).stdout.split()

        checks += [
            ("the real run_loop STOPS when the agent mutates a contract file",
             stopped is not None),
            ("...because the guard returned a nonzero exit",
             stopped is not None and "exited 91" in stopped),
            ("...and the agent did run, so this is the guard firing, not a wiring no-op",
             inner.ran == 1),
            # The whole point of the placement: nothing was frozen.
            ("...with NO new version committed or tagged", tags == ["program-v0"]),
            ("the mutation really did land on disk, so the guard caught a real edit",
             bool(store.verify_contract_files())),
        ]

        # And the converse: a well-behaved agent is not blocked by the guard.
        class _CleanAgent:
            def __init__(self, root):
                self.root = root

            def run(self, *, iter_n: int, materialized_path=None):
                editable = self.root / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
                editable.write_text(
                    editable.read_text(encoding="utf-8") + f"\n<!-- iter {iter_n} -->\n",
                    encoding="utf-8",
                )
                return adapter.GuardedOutcome(exit_code=0, detail="clean edit")

        repo2 = pathlib.Path(tmp) / "repo2"
        repo2.mkdir()
        _seed_repo(repo2, real_store)
        store2 = SarolProgramStore(repo_root=repo2)
        guarded2 = adapter.ContractGuardedAgent(_CleanAgent(repo2), store2, tree_root=repo2)
        completed = False
        try:
            run_loop(
                iterations=1,
                run_id="selftest2",
                repo_root=repo2,
                program_store=store2,
                runner=_Runner(),
                scorer=_Scorer(),
                release_builder=adapter.SarolReleaseBuilder(),
                agent=guarded2,
                train_inputs=schemas.RunInputs(
                    input_ref="unused", batch_id="t", split="train"),
                val_inputs=schemas.RunInputs(input_ref="unused", batch_id="v", split="val"),
                task_config={},
                materialize_root=pathlib.Path(tmp) / "materialized2",
                current_tag="program-v0",
            )
            completed = True
        except LoopStop:
            completed = False

        tags2 = subprocess.run(
            ["git", "tag"], cwd=str(repo2), capture_output=True, text=True
        ).stdout.split()
        checks += [
            ("an edit inside the EDIT scope is allowed through", completed),
            ("...and does get committed and tagged as a new version", len(tags2) > 1),
        ]

    # The wiring itself: you cannot build these components with a bare, unguarded agent.
    parts = build_components(max_budget_usd=1000.0, train_n=10, require_command=False)
    checks += [
        ("build_components wraps the optimizer agent in the contract guard",
         isinstance(parts["agent"], adapter.ContractGuardedAgent)),
        ("...around the real OptimizerAgent", isinstance(parts["agent"].inner, OptimizerAgent)),
        ("...which loads the hot-path prompt as its instructions",
         "maximize 3-way macro-F1" in parts["agent"].inner.agent_instructions().lower()
         or "Maximize 3-way macro-F1" in parts["agent"].inner.agent_instructions()),
        ("the optimizer session also carries a hard budget cap",
         "--max-budget-usd" in parts["agent"].inner.command(1, pathlib.Path("/tmp/m"))),
    ]
    return checks


def _selftest() -> int:
    checks: list[tuple[str, bool]] = []
    cm = CostModel(per_session_usd=0.05)

    # -- the arithmetic the Verification table gates on ---------------------------------------
    train_only = cm.batch_cost(50)
    full = cm.iteration_cost(50)
    # The scored-claim arithmetic is stated against a canary-free model so these keep testing the
    # TRAIN/VAL call structure rather than silently absorbing the canary term added for OQ12.
    bare = CostModel(canary_enabled=False)
    checks += [
        ("an iteration prices THREE runner calls, not one",
         bare.iteration_cost(50) == bare.batch_cost(50) + 2 * bare.batch_cost(VAL_SIZE)),
        ("a TRAIN-only estimate understates by exactly 2 x VAL",
         round(bare.iteration_cost(50) - bare.batch_cost(50), 6)
         == round(2 * bare.batch_cost(VAL_SIZE), 6)),
        ("the shortfall does not shrink as TRAIN grows",
         round(cm.iteration_cost(2141) - cm.batch_cost(2141), 6)
         == round(cm.iteration_cost(10) - cm.batch_cost(10), 6)),
        ("VAL=316 x 3 sessions x 2 calls is the 1,896 sessions the plan names",
         2 * VAL_SIZE * len(STAGES) == 1896),
        ("caching the probe removes one VAL call, and the canary firing that went with it",
         round(cm.iteration_cost(50) - cm.iteration_cost(50, probe_cached=True), 6)
         == round(cm.batch_cost(VAL_SIZE) + cm.stages_per_claim * cm.per_session_usd, 6)),
        ("...which for a canary-free run is exactly the VAL call",
         round(bare.iteration_cost(50) - bare.iteration_cost(50, probe_cached=True), 6)
         == round(bare.batch_cost(VAL_SIZE), 6)),
        ("the ladder is sarol's D13 ramp", TRAIN_LADDER[-1] == 2141),
        # Open Questions §12, resolved 2026-09-02 (Phil): once per Runner call, and priced.
        ("the canary is a priced term, not an untracked extra",
         cm.canary_sessions() == 3 * cm.stages_per_claim),
        ("...billed once per Runner call, which is three per iteration",
         cm.runner_calls() == 3 and cm.canary_sessions() > 0),
        ("...two when the probe is served from cache",
         cm.canary_sessions(probe_cached=True) == 2 * cm.stages_per_claim),
        ("...one per iteration under the cheaper reading, had it been chosen",
         CostModel(canary_per_runner_call=False).canary_sessions() == cm.stages_per_claim),
        ("...and zero when no canary is configured", bare.canary_sessions() == 0),
        ("cost and session count stay consistent with each other",
         round(cm.iteration_cost(50), 9)
         == round(cm.sessions_per_iteration(50) * cm.per_session_usd, 9)),
        ("the canary is a rounding error against VAL, so it never drives the N choice",
         cm.iteration_cost(10) - bare.iteration_cost(10) < 0.02 * bare.iteration_cost(10)),
        # C6.6 -- the profile drives sessions/claim. Hard-coding 3 overstates Phase 1 by ~3x, which
        # is the difference between "$32 an iteration" and "$96 an iteration" on a paid decision.
        ("a retrieval iteration is one session per claim",
         CostModel.for_profile("retrieval").stages_per_claim == 1),
        ("...and agentic is three", CostModel.for_profile("agentic").stages_per_claim == 3),
        ("...so Phase 1 costs a third of Phase 2 per claim",
         round(CostModel.for_profile("retrieval").claim_cost() * 3, 9)
         == round(CostModel.for_profile("agentic").claim_cost(), 9)),
        # These three pin the cost-model ARITHMETIC, so they name the price they are computed at
        # rather than inheriting the module default. The plan's headline $32/$16/$96 figures were
        # all derived at $0.05/session; once that placeholder was calibrated to real metered spend
        # (see DEFAULT_PER_SESSION_USD) they would otherwise have failed for the right reason at
        # the wrong layer -- the structure is still correct, only the unit price moved.
        ("retrieval prices at the ~$32/iteration the plan names, at the $0.05 it assumed",
         31 < CostModel.for_profile("retrieval", per_session_usd=0.05).iteration_cost(10) < 34),
        ("...and ~$16 with the probe cached, as C6.6 states",
         15 < CostModel.for_profile("retrieval", per_session_usd=0.05)
         .iteration_cost(10, probe_cached=True) < 18),
        ("agentic still prices at the ~$96 floor, at that same assumed price",
         94 < CostModel.for_profile("agentic", per_session_usd=0.05).iteration_cost(10) < 99),
        # And the measured reality, pinned so a regression back to a toy default is visible: at the
        # calibrated price a Phase 1 iteration is a ~$650 decision, not a ~$32 one.
        ("at the calibrated price, a retrieval iteration is a several-hundred-dollar decision",
         600 < CostModel.for_profile("retrieval").iteration_cost(10) < 700),
        ("the cost table says which rung it is describing",
         "retrieval" in CostModel.for_profile("retrieval").render_table()),
        # -- the graduated cohort (Phil, 2026-09-02), and which knob actually moves the bill -----
        ("a smaller VAL is priced, since VAL is what an iteration mostly buys",
         CostModel.for_profile("retrieval", val_size=25).iteration_cost(10)
         < 0.2 * CostModel.for_profile("retrieval").iteration_cost(10)),
        ("...and the cost table reports the VAL size it priced",
         "VAL=25" in CostModel.for_profile("retrieval", val_size=25).render_table()),
        # The finding that shaped the CLI: ramping TRAIN alone is nearly free of effect, because
        # two of the three Runner calls are VAL at a fixed size. Pinned so nobody re-derives it
        # after paying for it.
        ("ramping TRAIN 10 -> 5 changes an iteration by <2%, so TRAIN is NOT the cost lever",
         abs(CostModel.for_profile("retrieval").iteration_cost(5)
             - CostModel.for_profile("retrieval").iteration_cost(10))
         < 0.02 * CostModel.for_profile("retrieval").iteration_cost(10)),
        ("...while halving VAL changes it by ~half, which is",
         CostModel.for_profile("retrieval", val_size=158).iteration_cost(10)
         < 0.6 * CostModel.for_profile("retrieval").iteration_cost(10)),
    ]

    # -- C6.9: the VAL boundary is a filesystem fact, not a payload convention ------------------
    import tempfile as _tf

    with _tf.TemporaryDirectory() as _repo, _tf.TemporaryDirectory() as _outside:
        repo = pathlib.Path(_repo)
        inside = repo / "runs" / "val"
        checks += [
            ("a VAL root inside the optimizer's readable tree is refused",
             val_isolation_problem(inside, repo) is not None),
            ("...naming the tree it is inside",
             str(repo.resolve()) in (val_isolation_problem(inside, repo) or "")),
            ("the repo root itself is refused as a VAL root",
             val_isolation_problem(repo, repo) is not None),
            ("a VAL root outside it passes",
             val_isolation_problem(pathlib.Path(_outside), repo) is None),
        ("the helper itself treats no-root as no-problem -- it is a path predicate",
         val_isolation_problem(None, repo) is None),
        ("...but a REAL run refuses to start without both roots stated",
         _raises_valueerror(lambda: run_optimization(
             iterations=1, run_id="r", train_input_ref="t", val_input_ref="v",
             max_budget_usd=1.0, train_n=1, materialize_root=repo))),
        # C6.9 asks for a control against the CONCRETE path the runtime writes, not a generic
        # directory. These are the real run-manifest and mistake-corpus locations.
        ("the concrete VAL manifest path the runtime would write is caught",
         val_isolation_problem(repo / "runs-r-val", repo) is not None),
        ("...and so is a TRAIN mistake-corpus root pointed inside the tree",
         val_isolation_problem(repo / "trainout" / "mistakes", repo) is not None),
        # Selectable != runnable: agentic is priced and selectable, but /sarol-eval-item
        # implements only the adjudicator stage.
        ("only retrieval is runnable today",
         profiles_mod.runnable_profiles() == ["retrieval"]),
        ("a real run refuses an unrunnable profile before spending anything",
         _raises_valueerror(lambda: run_optimization(
             iterations=1, run_id="r", train_input_ref="t", val_input_ref="v",
             max_budget_usd=1.0, train_n=1, materialize_root=repo,
             train_output_root=repo / "trainout",
             val_output_root=pathlib.Path(_outside), profile="agentic"))),
            # The negative control the plan asks for: wiring the loop up with a readable VAL root
            # must fail loudly at construction, not quietly produce a leaky run.
            ("build_components refuses to assemble a loop with a readable VAL root",
             _raises_valueerror(lambda: build_components(
                 max_budget_usd=1.0, train_n=1,
                 program_store=_FakeStore(repo),
                 val_output_root=inside))),
        ]

        # The CLI is where this broke: `--profile` was parsed, used to price the run, then dropped
        # before `run_optimization` -- so `--profile retrieval` printed a retrieval cost table and
        # ran `agentic`. Capture what main() actually forwards.
        seen: dict = {}

        def _recorder(**kw):
            seen.update(kw)
            raise BudgetExceeded("stop before doing any work")

        _real = globals()["run_optimization"]
        globals()["run_optimization"] = _recorder
        try:
            main([
                "--run", "--profile", "retrieval",
                "--run-id", "r1", "--train-n", "10", "--max-budget-usd", "1",
                "--train-inputs", "t.json", "--val-inputs", "v.json",
                "--materialize-root", str(repo),
                "--train-output-root", str(repo / "trainout"),
                "--val-output-root", _outside,
            ])
            no_roots = main([
                "--run", "--run-id", "r", "--train-n", "10", "--max-budget-usd", "1",
                "--train-inputs", "t", "--val-inputs", "v",
                "--materialize-root", str(repo),
            ])
        finally:
            globals()["run_optimization"] = _real

        checks += [
            ("the CLI forwards the selected profile to the run, not just to the estimate",
             seen.get("profile") == "retrieval"),
            ("...and forwards both output roots",
             str(seen.get("train_output_root") or "").endswith("trainout")
             and str(seen.get("val_output_root")) == _outside),
            ("--run without the output roots is refused by argument checking", no_roots == 2),
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

        checks += _integration_checks(schemas)
    else:
        checks.append((f"engine not found at {adapter.engine_path()} -- engine checks SKIPPED", True))

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="print the per-landmark cost table")
    ap.add_argument("--run", action="store_true", help="drive the engine's optimization loop")
    ap.add_argument(
        "--profile",
        default=profiles_mod.DEFAULT_PROFILE,
        choices=sorted(profiles_mod.PROFILES),
        help="evidence-acquisition profile (C6.1). 'retrieval' is Phase 1; the default is the "
             "landed three-stage pipeline, so Phase 1 must be asked for explicitly.",
    )
    ap.add_argument("--per-session-usd", type=float, default=DEFAULT_PER_SESSION_USD)
    ap.add_argument("--max-budget-usd", type=float, default=None)
    ap.add_argument("--per-call-max-budget-usd", type=float, default=2.0)
    ap.add_argument("--train-n", type=int, default=None)
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--train-inputs", default=None, help="path to the TRAIN batch JSON")
    ap.add_argument("--val-inputs", default=None, help="path to the VAL batch JSON")
    ap.add_argument("--materialize-root", default=None)
    ap.add_argument(
        "--train-output-root",
        default=None,
        help="where TRAIN run outputs and the per-claim mistake corpus land (C6.8). Must be "
             "readable by the optimizer.",
    )
    ap.add_argument(
        "--val-output-root",
        default=None,
        help="where VAL run outputs land (C6.9). Must lie OUTSIDE the optimizer's readable tree, "
             "or the held-out set's per-claim outputs are directly readable.",
    )
    ap.add_argument(
        "--train-n-schedule",
        default=None,
        help="graduated TRAIN cohort, e.g. '5,10,20': iteration i uses rung i, holding at the top "
             "rung thereafter. Replaces --train-inputs, which stages a fixed batch. Non-decreasing.",
    )
    ap.add_argument(
        "--draw-mode",
        default="cumulative",
        choices=sorted(sampling.DRAW_MODES),
        help="how each rung is drawn. 'cumulative' grows the batch without dropping anything the "
             "optimizer already saw; 'fresh' redraws independently; 'reproduce' repeats the "
             "previous iteration's exact set.",
    )
    ap.add_argument(
        "--val-n",
        type=int,
        default=None,
        help="subsample VAL to this many claims (default: all 316). THIS is the cost lever -- VAL "
             "is charged twice per iteration at a fixed size, so at TRAIN=10 it is ~98%% of the "
             "bill and ramping TRAIN alone barely changes the total.",
    )
    ap.add_argument(
        "--sampling-root",
        default=None,
        help="where drawn batches, their staging trees and draw_history.json land "
             "(default: --train-output-root).",
    )
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.run:
        # A ramp supplies its own TRAIN batches per iteration, so --train-inputs/--train-n are
        # exactly what it replaces. Requiring both would force the caller to hand over a fixed
        # batch that is then ignored -- the kind of dead argument that later reads as a bug.
        schedule = (
            sampling.parse_schedule(args.train_n_schedule) if args.train_n_schedule else None
        )
        required = {
            "--max-budget-usd": args.max_budget_usd,
            "--run-id": args.run_id,
            "--val-inputs": args.val_inputs,
            "--materialize-root": args.materialize_root,
            "--train-output-root": args.train_output_root,
            "--val-output-root": args.val_output_root,
        }
        if schedule is None:
            required["--train-n"] = args.train_n
            required["--train-inputs"] = args.train_inputs
        missing = [flag for flag, value in required.items() if value is None]
        if missing:
            print(f"--run requires: {', '.join(missing)}", file=sys.stderr)
            return 2
        try:
            run = run_optimization(
                iterations=args.iterations,
                run_id=args.run_id,
                train_input_ref=args.train_inputs,
                val_input_ref=args.val_inputs,
                max_budget_usd=args.max_budget_usd,
                train_n=args.train_n,
                materialize_root=pathlib.Path(args.materialize_root),
                # Without these three the CLI printed a `retrieval` cost table and then ran
                # `agentic`: --profile was parsed, used to price the run, and dropped before the
                # run itself. A profile that only reaches the estimate is worse than no profile.
                profile=args.profile,
                train_output_root=pathlib.Path(args.train_output_root),
                val_output_root=pathlib.Path(args.val_output_root),
                per_session_usd=args.per_session_usd,
                per_call_max_budget_usd=args.per_call_max_budget_usd,
                train_schedule=schedule,
                draw_mode=args.draw_mode,
                val_n=args.val_n,
                sampling_root=(
                    pathlib.Path(args.sampling_root) if args.sampling_root else None
                ),
            )
        except BudgetExceeded as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 1
        print(json.dumps({
            "run_id": run.run_id,
            "best_tag": run.best_tag,
            "best_metric_value": run.best_metric_value,
            "stop_reason": run.stop_reason,
            "spent_usd": run.spent_usd,
        }, indent=2))
        return 0

    cost_model = CostModel.for_profile(
        args.profile,
        per_session_usd=args.per_session_usd,
        val_size=args.val_n or VAL_SIZE,
    )
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
