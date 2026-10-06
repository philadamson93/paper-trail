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
  batch, same answer. The engine's ``run_loop`` reuses that pass within the run (plan B, B6: keyed on
  the tree's content, the batch and the runner's own pass identity), so the second call is free.
  paper-trail kept its own copy of this cache until PT-B.

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
import contextlib
import hashlib
import importlib
import inspect
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
import canary as canary_mod  # noqa: E402
import engine_pin  # noqa: E402
import sarol_isolation as isolation_mod  # noqa: E402
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

        ``probe_cached=True`` prices an iteration whose probe is reused by the engine's run_loop
        (B6) -- one VAL call instead of two.
        """
        return self.sessions_per_iteration(train_n, probe_cached=probe_cached) * self.per_session_usd

    def sessions_per_iteration(self, train_n: int, *, probe_cached: bool = False) -> int:
        val_calls = 1 if probe_cached else 2
        scored = (train_n + val_calls * self.val_size) * self.stages_per_claim
        return scored + self.canary_sessions(probe_cached=probe_cached)

    def remaining_iteration_cost(
        self, split: str, *, train_n: int, probe_cached: bool = False
    ) -> float:
        """Cost still owed to FINISH the current iteration, counted from ``split``'s call.

        The engine's sequence is TRAIN -> VAL -> (agent) -> probe-VAL. Pricing from the current
        position is what makes "refuse to start" mean "refuse to start something that would strand
        the iteration half-paid-for".

        **This lives on the cost model, not on the guard, on purpose.** ``BudgetGuard`` previously
        did its own arithmetic and omitted the canary term that ``sessions_per_iteration`` charges
        -- so once a canary was actually wired, the preflight priced three firings per iteration
        and the per-call refusal priced none. A run could clear the guard with enough money for its
        scored claims and none for the canary it dispatches FIRST. That is the `--val-n` defect's
        exact shape: an estimate and an enforcement reading two different models. One arithmetic
        source is what stops them drifting a third time.
        """
        remaining_val_calls = 1 if probe_cached else 2
        val_sessions = self.val_size * self.stages_per_claim
        scored = remaining_val_calls * val_sessions
        runner_calls = remaining_val_calls
        if split == "train":
            scored += train_n * self.stages_per_claim
            runner_calls += 1
        if self.canary_enabled:
            # Conservative when the canary fires once per ITERATION rather than per call: it may
            # already have fired, but over-reserving refuses a run that could not finish, while
            # under-reserving strands one mid-iteration. Only one of those is recoverable.
            firings = runner_calls if self.canary_per_runner_call else 1
            scored += firings * self.stages_per_claim
        return scored * self.per_session_usd

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

    Consulted before each pass and charged after it, through the driver's ``before_pass`` and
    ``after_pass`` hooks (:func:`budget_hooks`): the point where spend actually happens.
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

        Delegates to :meth:`CostModel.remaining_iteration_cost` rather than re-deriving the
        arithmetic here. The guard used to compute its own TRAIN+VAL total and silently omit the
        canary the preflight charged for -- see that method's docstring; the delegation is the fix.
        """
        return self.cost_model.remaining_iteration_cost(
            split, train_n=self.train_n, probe_cached=probe_cached
        )

    def check(self, split: str, *, probe_cached: bool = False) -> str | None:
        need = self.worst_case_to_finish_iteration(split, probe_cached=probe_cached)
        if need > self.remaining_usd:
            return (
                f"budget: finishing this {split} iteration needs ~${need:,.2f}, "
                f"${self.remaining_usd:,.2f} remains of ${self.max_budget_usd:,.2f}"
            )
        return None


# =================================================================================================
# Wiring
# =================================================================================================


PROMPT_PATH = _HERE / "prompt" / "optimizer-instructions.md"
CONTEXT_DIR = _HERE / "context"


# The host optimizer (`OptimizerAgent`: `claude` with its permission-skip flag and the repo as its
# cwd) was removed by PT-A on 2026-10-01. The optimizer is the engine's contained optimizer, built in
# `sarol_optimizer.SarolOptimizer` and wired in `build_components`.


class _FakeStore:
    """Minimal stand-in for `SarolProgramStore` in the C6.9 negative control -- only `repo_root`
    is read before the isolation check fires, so building a real store would be noise."""

    def __init__(self, repo_root):
        self.repo_root = pathlib.Path(repo_root)


def _drift_refusal_text(exc: BaseException) -> str:
    """The text of the tree/tag drift refusal: the driver's ``consumer_refused`` stop, nothing else.
    Any other exception means the guard was passed, so it comes back marked as the wrong one."""
    if type(exc).__name__ == "LoopStop" and getattr(exc, "reason", None) == "consumer_refused":
        return str(exc)
    return f"<wrong exception: {type(exc).__name__}: {getattr(exc, 'reason', None)}: {exc}>"


def _stops(fn, reason: str) -> bool:
    """Does ``fn`` stop the run (the engine's ``LoopStop``) with ``reason``? A refusal through the
    shared driver is a recorded stop, not an exception of paper-trail's own (C-core)."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 -- the stop's type and reason are what is asserted
        return type(exc).__name__ == "LoopStop" and getattr(exc, "reason", None) == reason
    return False


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


# =================================================================================================
# Run state the engine resets and keeps (PT-B: the engine's B3/B4/B5 replace check_run_scope.py)
# =================================================================================================

#: Where a run's lasting state lives: the optimizer's notes history, the run store (failed-version
#: records, program snapshots) and the archive of what a run start moved aside. One setting so the
#: live check and the self-tests can point it at a scratch folder and never touch the real notebook.
STATE_ROOT = pathlib.Path.home() / ".paper-trail"


def state_paths(state_root: pathlib.Path) -> dict:
    """The three folders under a state root. The archive stays ``runs/_archive`` (isolation OQ9: moving
    it would orphan the notebooks earlier runs archived there)."""
    root = pathlib.Path(state_root)
    return {"notes": root / "optimizer-notes", "run_store": root / "run-store", "archive": root / "runs" / "_archive"}


def run_carried(*, repo_root: pathlib.Path, notebook: "pathlib.Path | None", notes_root: pathlib.Path) -> list:
    """paper-trail's state and how long each piece lives (was ``check_run_scope.CARRIED``).

    ``iter/`` is the run's own: archived at every start. The notebook and the notes history are the
    lineage's: kept when a run continues from a later version, archived only on a fresh start from
    program-v0's content, the notebook put back as its stub (next-run H2). The fourth piece the old
    list named, the graders' ledger, is the engine program runner's since PT-A.
    """
    from engine.run_start import Carried  # noqa: PLC0415
    import sarol_optimizer  # noqa: PLC0415 -- needs the engine on the path

    carried = [Carried(pathlib.Path(repo_root) / "iter", "run"), Carried(pathlib.Path(notes_root), "lineage")]
    if notebook is not None:
        carried.append(Carried(pathlib.Path(notebook), "lineage", stub=sarol_optimizer.NOTEBOOK_STUB))
    return carried


def reset_carried(parts: dict, notes_root: pathlib.Path) -> list:
    """What ``run_optimization`` hands the run-start reset: :func:`run_carried` over the components'
    own repo and optimizer, so a selftest checks the same lookup a run does."""
    return run_carried(
        repo_root=parts["program_store"].repo_root,
        notebook=getattr(parts.get("optimizer"), "notebook", None),
        notes_root=notes_root,
    )


def build_components(
    *,
    max_budget_usd: float,
    train_n: int,
    per_session_usd: float = DEFAULT_PER_SESSION_USD,
    gold_resolver=None,
    canary=None,
    require_command: bool = True,
    per_call_max_budget_usd: float = 2.0,
    program_store: SarolProgramStore | None = None,
    profile=None,
    train_output_root: pathlib.Path | None = None,
    val_output_root: pathlib.Path | None = None,
    val_n: int | None = None,
    #: The JUDGE's model, not the optimizer's.
    model: str | None = None,
    #: How many claims run at once: the engine runner's ``max_concurrent``. Claims are independent
    #: sessions, so this changes wall-clock only, not what any session sees.
    max_workers: int = 1,
    run_id: str | None = None,
    #: The loop's materialized trees. The engine runner refuses an output root inside it, and the
    #: optimizer reads earlier versions from it.
    materialize_root: pathlib.Path | None = None,
    #: Where the engine runner keeps every pass (``live/``, ``archive/``). Default: beside the TRAIN
    #: and VAL roots, as ``<run>/program-out``.
    program_output_root: pathlib.Path | None = None,
    #: Images by digest (``name:version@sha256:…``). Default: the locally built ones.
    grader_image: str | None = None,
    optimizer_image: str | None = None,
    optimizer_model: str = "opus",
    optimizer_max_budget_usd: float = 20.0,
    optimizer_timeout_seconds: float = 3600.0,
    #: ``{"program": …, "optimizer": …}``: the setup pins each session is held to. Default: the pins
    #: committed in the manifest for this platform; ``ss.UNPINNED`` only when said explicitly.
    expected_fingerprints: "dict | None" = None,
    #: Run-level files the optimizer reads, copied into its feedback folder each iteration with host
    #: paths stripped (D6): the run summary and the TRAIN draw history.
    optimizer_feedback_files: "tuple | list" = (),
    #: The run's lasting state (:func:`state_paths`). Default: ``~/.paper-trail``.
    state_root: pathlib.Path | None = None,
    _program_runner_private: "dict | None" = None,
    _agent_factory=None,
):
    """Assemble the program, the engine runner around it, the contained optimizer, and the guards.

    Since PT-A (2026-10-01) the graders run through the engine's ``ProgramRunner`` and the optimizer
    is the engine's ``ContainedOptimizerAgent`` (``sarol_program``, ``sarol_optimizer``). The runner is
    returned **not entered**: ``run_optimization`` enters it around ``run_loop``, which is what closes
    its network on every exit path.

    The agent is wrapped in :class:`adapter.ContractGuardedAgent` **here**, not at the call site,
    so there is no way to wire this loop up without the contract-file re-hash in place.
    """
    import sarol_optimizer  # noqa: PLC0415 -- both need the engine on the path
    import sarol_program  # noqa: PLC0415
    from isolation import sealed_session as ss  # noqa: PLC0415
    from isolation.session_scope import Forbidden  # noqa: PLC0415

    store = program_store or SarolProgramStore()
    prof = profiles_mod.get(profile)
    cost_model = CostModel.for_profile(
        prof,
        per_session_usd=per_session_usd,
        val_size=val_n or VAL_SIZE,
        canary_enabled=canary is not None,
    )
    # VAL isolation (C6.9) is checked by the driver on every run (`run_refusals`), not at build time.
    if materialize_root is None:
        raise ValueError("build_components needs materialize_root: the engine runner and the optimizer both read it")
    scorer_roots = tuple(pathlib.Path(r) for r in (train_output_root, val_output_root) if r is not None)
    if program_output_root is None:
        if not scorer_roots:
            raise ValueError("say where the program's passes go: program_output_root, or a TRAIN/VAL root beside it")
        program_output_root = scorer_roots[0].parent / "program-out"
    program_output_root = pathlib.Path(program_output_root)
    pins = expected_fingerprints or sarol_program.committed_pins()
    missing = [k for k in ("program", "optimizer") if not pins.get(k)]
    if missing:
        raise ValueError(
            f"no setup fingerprint is pinned for {', '.join(missing)} on this platform "
            f"({sarol_program.platform_key()}): run `sarol_program.py --print-pins` and commit the block "
            f"under runtime_pins.{sarol_program.PIN_KEY} in the manifest, or pass ss.UNPINNED explicitly"
        )
    budget = BudgetGuard(max_budget_usd=max_budget_usd, cost_model=cost_model, train_n=train_n)
    program = sarol_program.SarolProgram(
        profile=prof,
        model=model or adapter.DEFAULT_JUDGE_MODEL,
        canary=canary,
        per_call_max_budget_usd=per_call_max_budget_usd,
        max_concurrent=max_workers,
        require_command=require_command,
    )
    grader_forbidden = sarol_program.forbidden_list(
        repo_root=store.repo_root,
        extra=tuple(Forbidden(r, representatives=("mistakes",)) for r in scorer_roots),
    )
    program_runner = sarol_program.program_runner(
        program,
        output_root=program_output_root,
        materialize_root=pathlib.Path(materialize_root),
        image=grader_image or sarol_program.grader_image(),
        transcript_dir=program_output_root / "transcripts",
        expected_fingerprint=pins["program"],
        forbidden=grader_forbidden,
        **(_program_runner_private or {}),
    )
    optimizer = sarol_optimizer.SarolOptimizer(
        store=store,
        materialize_root=pathlib.Path(materialize_root),
        program_output_root=program_output_root,
        run_root=program_output_root.parent,
        image=optimizer_image or sarol_optimizer.optimizer_image(),
        expected_fingerprint=pins["optimizer"],
        model=optimizer_model,
        max_budget_usd=optimizer_max_budget_usd,
        timeout_seconds=optimizer_timeout_seconds,
        profile=prof,
        scorer_roots=scorer_roots,
        transcript_dir=program_output_root.parent / "optimizer-transcripts",
        feedback_files=tuple(optimizer_feedback_files),
        notes_root=state_paths(state_root or STATE_ROOT)["notes"],
        # A real run always names itself (run_optimization). Without one (the pin printer, selftests)
        # a placeholder: the run id names a folder inside the notes history, not a mount, so the
        # session's description and its setup pin are the same either way (checked in the selftest).
        run_id=run_id or "unnamed-run",
        **({"_agent_factory": _agent_factory} if _agent_factory is not None else {}),
    )
    setup_value = sarol_program.setup_value(program_runner, optimizer, materialize_root=pathlib.Path(materialize_root))
    agent = adapter.ContractGuardedAgent(optimizer, store, tree_root=store.repo_root)
    return {
        "program_store": store,
        "program": program,
        "program_runner": program_runner,
        "optimizer": optimizer,
        "setup_value": setup_value,
        "scorer": adapter.SarolScorer(gold_resolver=gold_resolver, mistakes_root=train_output_root),
        "profile": prof,
        "release_builder": adapter.SarolReleaseBuilder(setup_value=setup_value),
        "build_mistake_corpus": adapter.build_mistake_corpus,
        "agent": agent,
        "budget": budget,
        "cost_model": cost_model,
        "state_root": pathlib.Path(state_root or STATE_ROOT),
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
    #: The version the run starts from. Default: the one the manifest freezes (program-v11 since PT-A).
    current_tag: str | None = None,
    components: dict | None = None,
    train_schedule: "list[int] | None" = None,
    draw_mode: str = "cumulative",
    val_n: int | None = None,
    sampling_root: pathlib.Path | None = None,
    require_canary: bool = True,
    run_summary_path: pathlib.Path | None = None,
    resume: bool = False,
    #: The run's lasting state (:func:`state_paths`). Default ``~/.paper-trail``; the live check uses a
    #: scratch folder. Components handed in by a selftest bring their own (``parts["state_root"]``) or
    #: none, and with none there is no run store and nothing carried across the reset.
    state_root: pathlib.Path | None = None,
    **component_kwargs,
):
    """Run the optimization through the engine's shared driver (``engine.driver.run_driver``, C-core).

    The driver owns the order (consumer refusals, signals, lock, run-start reset, resume, engine-version
    check, sealed-setup check, runner, loop) and records every refusal as a stop in the run summary.
    This function builds paper-trail's components and draws, hands them over, and supplies paper-trail's
    hooks: its refusals (:func:`run_refusals`) and the per-pass budget (:func:`budget_hooks`).

    Two refusals stay ahead of the build, because the build needs what they check: a profile that can't
    run, and the canary a run must pin. They are stops recorded the same way, with the driver's helper.

    **Graduated N.** Pass ``train_schedule`` (e.g. ``[5, 10, 20]``) to grow the TRAIN batch across
    iterations instead of running a fixed cohort every time; ``draw_mode`` selects `sampling`'s
    cumulative / fresh / reproduce semantics. Omit it and the batch is fixed.

    ⚠ **The ramp is not the cost fix on its own.** An iteration is three Runner calls, two of them
    VAL at a fixed size, so at TRAIN=10 roughly 98% of the bill is VAL. ``val_n`` is the knob that
    actually moves the number; ``train_schedule`` controls what the optimizer learns from. Both are
    priced, and the budget check uses the ramp's TOP rung, the most expensive iteration the run can reach.
    """
    # The engine is checked (pin, import origin, what paper-trail builds on) before its code is trusted
    # to run anything, including the driver that records stops: an engine too old to have the driver
    # can't record one. A refusal here still becomes a recorded `engine_version` stop when the engine
    # can import the driver's stop writer (implementation review, 2026-10-06).
    try:
        isolation_mod.engine_on_path()
    except RuntimeError as exc:
        _engine_refused(exc, run_summary_path=run_summary_path, val_output_root=val_output_root, run_id=run_id)
    from engine.driver import DriverConfig, record_pre_loop_stop, run_driver  # noqa: PLC0415
    from engine.loop import LoopStop  # noqa: PLC0415
    from engine.loop_ops import LocalLoopOps  # noqa: PLC0415
    from engine.run_store import FakeRunStore  # noqa: PLC0415
    from engine.schemas import RunInputs  # noqa: PLC0415
    import sarol_optimizer  # noqa: PLC0415

    if current_tag is None:
        current_tag = adapter.SarolProgramStore().program_version
    effective_run_summary = run_summary_path
    if effective_run_summary is None and val_output_root is not None:
        effective_run_summary = pathlib.Path(val_output_root).parent / "run_summary.json"
    model = component_kwargs.get("model") or adapter.DEFAULT_JUDGE_MODEL

    def refuse_before_build(message: str, step: str):
        stop = LoopStop(message, reason="consumer_refused")
        record_pre_loop_stop(effective_run_summary, run_id=run_id, stop=stop, step=step)
        raise stop

    # A real run must SAY where its outputs go. `train_output_root` is where the per-claim mistake
    # corpus lands (C6.8) and `val_output_root` must lie outside the optimizer's readable tree (C6.9);
    # neither has a safe default. An argument error, like a missing flag: there is no run yet.
    if components is None:
        missing = [n for n, v in (("train_output_root", train_output_root), ("val_output_root", val_output_root)) if v is None]
        if missing:
            raise ValueError(
                f"a real run must specify {', '.join(missing)}: "
                "TRAIN's root carries the per-claim mistake corpus (C6.8) and VAL's must sit "
                "outside the optimizer's readable tree (C6.9); neither can be safely derived"
            )

    # Selectable != runnable: `agentic` and `paperclip` would abort on the first claim, after the
    # session is paid for. Refused before the build, which would refuse it less clearly.
    blocked = profiles_mod.unrunnable_reason(profile if components is None else components["profile"].name)
    if blocked:
        refuse_before_build(blocked, "before_run")

    # FAIL CLOSED on a missing canary (Finding 4): the 2026-09-02 run carried `"canary": null` in every
    # manifest and nothing noticed. Turning it off has to be SAID (`require_canary=False` / `--no-canary`),
    # and the cost model then prices the cheaper reality. Before the build, because the canary is an
    # input to it.
    if components is None and require_canary and component_kwargs.get("canary") is None:
        pinned = canary_mod.load(profiles_mod.get(profile).name, model=model)
        if pinned is None:
            refuse_before_build(
                f"no round-trip canary is pinned for profile "
                f"{profiles_mod.get(profile).name!r}. Every number from a run without one "
                "lacks the instrument check the design requires, and the first optimization "
                "run produced exactly that silently. Pin one with "
                f"`python3 canary.py --pin --profile {profiles_mod.get(profile).name} "
                "--repeat 3` (costs real sessions), or say `--no-canary` to run without it "
                "-- which also reprices the run, so the estimate stays honest.",
                "before_run",
            )
        component_kwargs["canary"] = pinned

    # S26: the tree must BE the version it says it is. Checked before the build for a real run (the
    # build needs the real images, and a mislabelled tree should say so first); the driver checks it
    # again on every run, injected components included.
    if components is None:
        drift = start_version_problem(adapter.SarolProgramStore(), current_tag)
        if drift:
            refuse_before_build(drift, "before_run")

    peak_train_n = max(train_schedule) if train_schedule else train_n
    if components is None and "optimizer_feedback_files" not in component_kwargs:
        feedback_files = []
        if effective_run_summary is not None:
            feedback_files.append(("run_summary.json", pathlib.Path(effective_run_summary)))
        if sampling_root or train_output_root:
            feedback_files.append(("draw_history.json", pathlib.Path(sampling_root or train_output_root) / "draw_history.json"))
        component_kwargs["optimizer_feedback_files"] = feedback_files

    parts = components or build_components(
        max_budget_usd=max_budget_usd,
        train_n=peak_train_n,
        per_session_usd=per_session_usd,
        profile=profile,
        train_output_root=train_output_root,
        val_output_root=val_output_root,
        val_n=val_n,
        run_id=run_id,
        materialize_root=pathlib.Path(materialize_root),
        state_root=state_root,
        **component_kwargs,
    )

    store = parts["program_store"]
    repo_root = store.repo_root
    state = parts.get("state_root")
    paths = state_paths(state) if state is not None else None
    # The run store records a failed version across runs, so a later run never starts from one (B5).
    run_store = FakeRunStore(paths["run_store"]) if paths is not None else None
    program_runner = parts.get("program_runner")
    if "setup_owners" in parts or "unsealed" in parts:
        # Components handed in by a selftest say which sessions they seal, out loud.
        owners, unsealed = dict(parts.get("setup_owners") or {}), tuple(parts.get("unsealed") or ())
    else:
        owners, unsealed = {"optimizer": parts["optimizer"], "program": program_runner}, ()

    config = DriverConfig(
        run_id=run_id,
        repo_root=repo_root,
        iterations=iterations,
        program_store=store,
        scorer=parts["scorer"],
        release_builder=parts["release_builder"],
        agent=parts["agent"],
        # The engine runner, entered and bound to the run id by the driver (one network for the whole
        # run, closed on every exit path); a selftest's own runner otherwise.
        runner=program_runner if program_runner is not None else parts["runner"],
        # A factory when a ramp was asked for, a fixed batch otherwise.
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
            else _static_train_inputs(RunInputs, train_input_ref, run_id=run_id, train_n=train_n)
        ),
        # A sampled VAL when one was asked for, the caller's fixed batch otherwise, drawn once and held
        # for the run.
        val_inputs=(
            sampling.val_inputs_for(
                n=val_n,
                split="dev",
                run_id=run_id,
                staging_root=pathlib.Path(sampling_root or val_output_root) / "val-staging",
                batch_root=pathlib.Path(sampling_root or val_output_root) / "val-batches",
                history_path=pathlib.Path(sampling_root or val_output_root) / "val_draw.json",
            )
            if val_n
            else RunInputs(input_ref=val_input_ref, batch_id=f"{run_id}-val", split="val")
        ),
        materialize_root=pathlib.Path(materialize_root),
        start_tag=current_tag,
        manifest_for_version=sarol_optimizer.earlier_version_view(store),
        # B3: fresh or continuing is decided by the start version's content. With no state root (a
        # selftest's components) nothing is carried, so the reset only checks and archives nothing.
        carried=reset_carried(parts, paths["notes"]) if paths is not None else (),
        archive_root=paths["archive"] if paths is not None else pathlib.Path(materialize_root).parent / "run-archive",
        run_summary_path=effective_run_summary,
        resume=resume,
        run_store=run_store,
        engine_pin=engine_pin.ENGINE_PIN,
        engine_root=engine_pin.engine_path(),
        engine_capabilities=engine_pin.CAPABILITIES,
        allow_engine_divergence=os.environ.get(engine_pin.OVERRIDE_ENV) == "1",
        pin_command="python3 experiments/sarol-2024/optimizer/sarol_program.py --print-pins",
        setup_owners=owners,
        unsealed=unsealed,
        before_run=run_refusals(
            parts, current_tag=current_tag, val_output_root=val_output_root,
            peak_train_n=peak_train_n, iterations=iterations, max_budget_usd=max_budget_usd,
        ),
        **budget_hooks(parts.get("budget")),
        loop_options=dict(
            task_config={
                "rubric_variant": adapter.validate_sarol.SAROL_VARIANT,
                "profile": parts["profile"].name,
            },
            # C6.5: a resume whose profile differs from the recorded one must STOP, not silently
            # continue a curve built from two different systems.
            hard_fields={
                "profile": parts["profile"].name,
                "retrieval_k": parts["profile"].retrieval_k,
                "rubric_variant": adapter.validate_sarol.SAROL_VARIANT,
            },
            # Provenance-only drift (warns, never STOPs).
            soft_fields={"model": model},
            # The ledger key each frozen version's VAL scalar is stored under and `--resume` reads back.
            metric_field="sarol_accuracy_9class",
            build_mistake_corpus=parts["build_mistake_corpus"],
            # ⚠ THIS ARGUMENT IS THE FEEDBACK LOOP. `run_loop` writes `iter/<n>/release_train.json` and
            # `release_val.json` (the only channel by which the held-out VAL scalar reaches the
            # optimizer) only when it has loop_ops. The 2026-09-02 run omitted it and optimized blind.
            loop_ops=LocalLoopOps(repo_root),
        ),
    )
    # #3 consumer half: a stop carries the partial run; attach the BudgetGuard so `main` can report the
    # graders' real spend beside the optimizer's. The stop still re-raises.
    try:
        run = run_driver(config)
    except LoopStop as exc:
        exc.budget = parts.get("budget")
        raise
    return run, parts.get("budget")


def start_version_problem(store, current_tag: str) -> str | None:
    """S26: is the tree the version the run starts from and files its numbers under? A problem, or
    ``None``. Called before the build for a real run and by the driver on every run."""
    # S26: the tree must BE the version it says it is. For the manifest's own frozen version the
    # tree and the tag are re-hashed against the frozen hashes; a version the engine minted is a
    # commit, so the tree must equal that commit's program (PT-B).
    if current_tag != store.program_version:
        differ = store.tree_differs_from(current_tag)
        if differ:
            return (
                f"the working tree does not match {current_tag!r}, the version this run starts from "
                f"and files its numbers under:\n  " + "\n  ".join(differ)
                + f"\n\nCheck out {current_tag}'s program files, or pass the `current_tag` the tree "
                "actually holds. Running as-is produces numbers that cannot be attributed to a version."
            )
        return None
    # TWO checks: the working tree is what a human reads; the TAG is what the engine materializes
    # from. A tree that matches while the tag points at older bytes runs the OLD program under the
    # new name (the 2026-09-07 re-freeze).
    drift = store.verify_tree_matches_tag()
    if drift:
        return (
            f"the working tree does not match {current_tag!r}, which is the tag every "
            f"number from this run would be filed under:\n  " + "\n  ".join(str(v) for v in drift)
            + f"\n\nRestore the {len(drift)} file(s) to the frozen {store.program_version} content "
            "before starting a baseline run, or pass a `current_tag` that names what the tree "
            "actually holds. Running as-is produces numbers that cannot be attributed to a program version."
        )
    tag_drift = store.verify_tag_tree(current_tag)
    if tag_drift:
        return (
            f"the git tag {current_tag!r} does not carry the frozen {store.program_version} content, "
            "and the tag is what the engine actually materializes from -- so this run would evaluate "
            "the tagged bytes while reporting under the manifest's identity:\n  "
            + "\n  ".join(str(v) for v in tag_drift)
            + f"\n\nRe-cut the tag onto a commit whose tree matches the manifest "
            f"(`git tag -f -a {current_tag} <commit>`), then confirm with "
            f"`freeze_program_v0.py --verify --tree {current_tag}`."
        )
    return None


def _engine_refused(exc: RuntimeError, *, run_summary_path, val_output_root, run_id: str):
    """Raise the engine check's refusal as an ``engine_version`` stop recorded in the run summary, when
    the engine on the path has the driver's stop writer; otherwise re-raise it as it is. The engine path
    is already on ``sys.path`` (``engine_pin`` appends it before checking)."""
    try:
        from engine.driver import record_pre_loop_stop  # noqa: PLC0415
        from engine.loop import LoopStop  # noqa: PLC0415
    except ImportError:
        raise exc from None
    summary = run_summary_path or (pathlib.Path(val_output_root).parent / "run_summary.json" if val_output_root else None)
    stop = LoopStop(str(exc), reason="engine_version")
    record_pre_loop_stop(summary, run_id=run_id, stop=stop, step="engine_version")
    raise stop from exc


def run_refusals(parts: dict, *, current_tag: str, val_output_root, peak_train_n: int, iterations: int,
                 max_budget_usd: float) -> tuple:
    """paper-trail's refusals the driver runs first, before the lock, on every run: built components
    and a selftest's injected ones alike (isolation OQ10: no switch skips them). Each returns a message
    or ``None``; the driver turns a message into a stop recorded in the run summary."""
    store = parts["program_store"]

    def profile_runnable(config) -> str | None:
        return profiles_mod.unrunnable_reason(parts["profile"].name)

    def val_isolation(config) -> str | None:
        leak = val_isolation_problem(val_output_root, store.repo_root)
        return f"VAL isolation (C6.9): {leak}" if leak else None

    def tree_is_the_start_version(config) -> str | None:
        return start_version_problem(store, current_tag)

    def affordable(config) -> str | None:
        # The ramp's top rung: the check describes the most expensive iteration the run can reach.
        ok, message = preflight(parts["cost_model"], train_n=peak_train_n, iterations=iterations,
                                max_budget_usd=max_budget_usd)
        return None if ok else f"budget: {message}"

    return (profile_runnable, val_isolation, tree_is_the_start_version, affordable)


def budget_hooks(budget: "BudgetGuard | None") -> dict:
    """The per-pass budget as driver hooks (was ``BudgetedRunner``, PT-B): refuse a pass the run can't
    finish the iteration after, and record what each pass cost. A pass the engine reuses is not run,
    so it is neither checked nor charged. The engine's hook wrapper keeps the runner's ``run_id`` and
    ``cache_identity``."""
    if budget is None:
        return {}
    from engine.loop import LoopStop  # noqa: PLC0415

    def within_budget(inputs) -> None:
        # The engine reuses a pass before this is ever called, so this cannot know whether the
        # iteration's next validation pass will be reused: it prices the worst case. Near the cap a
        # run may stop one iteration early; it never starts what it cannot finish.
        reason = budget.check(inputs.split)
        if reason is not None:
            raise LoopStop(reason, reason="budget_exhausted")
        return None

    def charge(inputs, artifacts) -> None:
        budget.record(artifacts.cost_usd or 0.0)

    return {"before_pass": (within_budget,), "after_pass": (charge,)}


def _static_train_inputs(RunInputs, train_input_ref, *, run_id: str, train_n: int | None):
    """A fixed TRAIN batch, checked against the size the run was PRICED at.

    The ramped path stages its own batch and verifies it (`sampling.assert_staged_size`). This
    path takes the caller's file as-is -- and `preflight`/`BudgetGuard` still price `train_n`. So
    a `--train-inputs` file holding 200 claims under `--train-n 10` reproduces the `--val-n`
    defect exactly: a quote and a guard describing one batch while a different one executes.
    Reading the file back through the Runner's own reader is the cheap half of never doing that
    again; it costs one file read against an iteration that costs hundreds of LLM sessions.
    """
    if train_n is not None:
        sampling.assert_staged_size(
            pathlib.Path(train_input_ref), train_n,
            label=f"static TRAIN batch for run {run_id} (--train-inputs vs --train-n)",
        )
    return RunInputs(input_ref=train_input_ref, batch_id=f"{run_id}-train", split="train")


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
        if entry.get("pattern"):
            continue  # a folder pattern (PT14) is not a file
        dst = dest / entry["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(store.repo_root / entry["path"], dst)
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "program-v0")
    run("git", "tag", "program-v0")
    return run("git", "rev-parse", "HEAD")


_TEST_ROOTS: list = []
_FAKE_GRADER_IMAGE = "paper-trail-isolation:2.1.277@sha256:" + "0" * 64
_FAKE_OPTIMIZER_IMAGE = "paper-trail-optimizer:2.1.277@sha256:" + "0" * 64


def _test_components(**kw):
    """``build_components`` over fresh temp roots, with stated fake images and no pins. Nothing it
    builds is entered or run here."""
    import atexit  # noqa: PLC0415
    import tempfile  # noqa: PLC0415

    from isolation import sealed_session as ss  # noqa: PLC0415

    root = pathlib.Path(tempfile.mkdtemp(prefix="sarol-dispatch-", dir=pathlib.Path.home() / ".cache"))
    if not _TEST_ROOTS:
        atexit.register(lambda: [shutil.rmtree(r, ignore_errors=True) for r in _TEST_ROOTS])
    _TEST_ROOTS.append(root)
    base = dict(
        train_output_root=root / "train", val_output_root=root / "val", materialize_root=root / "mat",
        grader_image=_FAKE_GRADER_IMAGE, optimizer_image=_FAKE_OPTIMIZER_IMAGE, profile="retrieval",
        expected_fingerprints={"program": ss.UNPINNED, "optimizer": ss.UNPINNED},
        state_root=root / "state",
    )
    base.update(kw)
    return build_components(**base)


def _integration_checks(schemas) -> list[tuple[str, bool]]:
    _VAL_ALLOWED_KEYS = set(adapter._VAL_BREAKDOWN_ALLOWED)
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
    from engine.loop_ops import LocalLoopOps  # noqa: PLC0415

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
                    name=adapter.PRIMARY_METRIC_NAME, value=0.4, higher_is_better=True
                ),
                breakdown={"scored": True, "n_total": 1, "n_invalid": 0,
                           "retrieval_k": 20, "profile": "retrieval",
                           "per_class_f1": {"ACCURATE": 0.9}},
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
                release_builder=adapter.SarolReleaseBuilder(setup_value="setup-v1:selftest"),
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

        # Record the iteration numbers the engine ACTUALLY hands the train_inputs factory. This is
        # the cross-repo contract Bug 2 got wrong: `sampling.ramp_for` assumed a 0-based counter,
        # `engine/loop.py` counts from 1, and the requested 10 -> 25 -> 50 ramp ran 25 -> 50 -> 50
        # with the cheap rung never firing. `sampling.py`'s own gates could not catch it -- they
        # asserted that module's convention against itself. Only the real engine can settle it.
        seen_iter_ns: list[int] = []

        def _recording_train_inputs(iter_n: int):
            seen_iter_ns.append(iter_n)
            return schemas.RunInputs(
                input_ref="unused", batch_id=f"t{iter_n}", split="train"
            )

        completed = False
        try:
            run_loop(
                iterations=1,
                run_id="selftest2",
                repo_root=repo2,
                program_store=store2,
                runner=_Runner(),
                scorer=_Scorer(),
                release_builder=adapter.SarolReleaseBuilder(setup_value="setup-v1:selftest"),
                agent=guarded2,
                train_inputs=_recording_train_inputs,
                val_inputs=schemas.RunInputs(input_ref="unused", batch_id="v", split="val"),
                task_config={},
                materialize_root=pathlib.Path(tmp) / "materialized2",
                current_tag="program-v0",
                # Exactly what `run_optimization` passes. Without it the engine skips the release
                # writes entirely, which is the whole of Finding 3.
                loop_ops=LocalLoopOps(repo2),
            )
            completed = True
        except LoopStop:
            completed = False

        tags2 = subprocess.run(
            ["git", "tag"], cwd=str(repo2), capture_output=True, text=True
        ).stdout.split()

        train_release = repo2 / "iter" / "1" / "release_train.json"
        val_release = repo2 / "iter" / "1" / "release_val.json"
        val_payload = (
            json.loads(val_release.read_text(encoding="utf-8")) if val_release.exists() else {}
        )
        val_metric = ((val_payload.get("metrics") or {}).get("primary_metric") or {})

        checks += [
            ("an edit inside the EDIT scope is allowed through", completed),
            ("...and does get committed and tagged as a new version", len(tags2) > 1),

            # Bug 2 -- the engine's counting base, read from the engine rather than assumed.
            ("the engine's FIRST iteration number is what sampling.ENGINE_FIRST_ITER_N claims",
             seen_iter_ns[:1] == [sampling.ENGINE_FIRST_ITER_N]),
            ("...so the ramp's first rung is the one that actually runs",
             bool(seen_iter_ns)
             and sampling.ramp_for(
                 sampling.rung_index(seen_iter_ns[0]), [10, 25, 50]) == 10),
            ("...and the factory is called exactly once per iteration",
             len(seen_iter_ns) == 1),

            # Finding 3 -- the release payload crossing the seam, asserted by PRESENCE on disk.
            # A guard that can be absent without announcing itself is not a guard: the first run
            # produced no release file at all and every offline gate stayed green.
            ("the loop writes the TRAIN release where the optimizer is told to read it",
             train_release.exists()),
            ("...and the VAL release too, which is the ONLY channel carrying the held-out "
             "scalar back to the optimizer (Finding 3)", val_release.exists()),
            ("...carrying a real scalar, not an empty envelope",
             isinstance(val_metric.get("value"), (int, float))),
            ("...under the optimizer's own tree, so its session can actually open it",
             val_release.exists() and repo2 in val_release.parents),
            # Tier 2 is about per-class STRUCTURE, and VAL legitimately carries a `breakdown` of
            # completeness metadata -- so this searches the whole serialized payload for the
            # fields that would actually leak, rather than checking for a key at one nesting
            # level and calling that the boundary.
            # C6.3: "A macro-F1 without the *k* is not a result" (plan:247). The VAL scalar IS a
            # reported Phase 1 number, so it has to carry its evidence condition -- while still
            # carrying no per-class structure. Both halves, asserted against the same payload.
            ("the VAL release carries its evidence condition (profile AND retrieval_k), so the "
             "frontier number is reportable under C6.3",
             (val_payload.get("metrics", {}).get("breakdown", {}) or {}).get("retrieval_k") == 20
             and (val_payload.get("metrics", {}).get("breakdown", {}) or {}).get("profile")
             == "retrieval"),
            ("...and the JUDGE it was measured with, which is run identity exactly as the "
             "profile and k are -- a macro-F1 says nothing without the instrument",
             "model" in _VAL_ALLOWED_KEYS),
            ("...and the objective's own denominator, since it renormalises over the classes "
             "present in the batch -- two numbers with different denominators are not comparable",
             {"n_objective_classes_present", "objective_class_set"} <= _VAL_ALLOWED_KEYS),
            ("...but NOT which classes were present: that is a thresholded `support_9way`, i.e. "
             "VAL's gold structure, and the count alone is what makes the number readable",
             "objective_classes_present" not in _VAL_ALLOWED_KEYS),
            ("...while the scorer's per-class structure, offered on the same breakdown, is "
             "stripped -- so the widening is identity metadata, not leakage",
             "per_class_f1" not in json.dumps(val_payload)),
            ("...and the VAL release stays Tier 2: the scalar plus completeness metadata, with "
             "no per-class structure anywhere in it",
             not any(leak in json.dumps(val_payload) for leak in (
                 "per_class_f1", "confusion_matrix", "error_class_counts",
                 "support_9way", "mistakes_ref"))),
        ]

        # -----------------------------------------------------------------------------------
        # Finding 3, asserted at the PRODUCTION call site.
        #
        # The release check above drives `run_loop` directly and passes its OWN `loop_ops`,
        # under a comment reading "exactly what run_optimization passes". That comment is an
        # assumption, not a check. It proves the ENGINE writes a release when handed loop_ops
        # -- which was never in doubt -- and proves nothing about whether the entrypoint that
        # actually shipped hands it over. Negative-controlled 2026-09-03: delete `loop_ops=`
        # from `run_optimization`, reintroducing the exact defect that cost the 2026-09-02 run
        # its VAL signal, and all 91 gates stayed green.
        #
        # That is the postmortem's own diagnosis -- "a test that asserts an assumption instead
        # of a contract" -- reappearing in the fix for the bug it diagnosed. So drive the real
        # entrypoint end-to-end and look for the files on disk.
        #
        # `build_mistake_corpus` is left None deliberately: the engine substitutes its own
        # default, which keeps this gate about the loop_ops seam rather than about corpus
        # construction (covered separately by the adapter's own gates).
        repo3 = pathlib.Path(tmp) / "repo3"
        repo3.mkdir()
        _seed_repo(repo3, real_store)
        store3 = SarolProgramStore(repo_root=repo3)

        _batch3 = pathlib.Path(tmp) / "train3.json"
        _batch3.write_text(
            json.dumps({"claims": [{"claim_id": "C0", "citekey": "k0", "staging_dir": tmp}]}),
            encoding="utf-8",
        )

        _parts3 = {
            "program_store": store3,
            "runner": _Runner(),
            "scorer": _Scorer(),
            "profile": profiles_mod.get("retrieval"),
            "release_builder": adapter.SarolReleaseBuilder(setup_value="setup-v1:selftest"),
            "build_mistake_corpus": None,
            "agent": adapter.ContractGuardedAgent(_CleanAgent(repo3), store3, tree_root=repo3),
            "budget": None,
            "cost_model": CostModel.for_profile("retrieval", val_size=1),
            "unsealed": ("optimizer", "program"),
        }
        entrypoint_error = None
        try:
            run_optimization(
                iterations=1,
                run_id="selftest3",
                train_input_ref=str(_batch3),
                val_input_ref=str(_batch3),
                max_budget_usd=1e9,
                train_n=1,
                materialize_root=pathlib.Path(tmp) / "materialized3",
                current_tag="program-v0",
                components=_parts3,
            )
        except Exception as exc:  # noqa: BLE001 -- the files on disk are what is asserted
            entrypoint_error = exc

        entry_train_release = repo3 / "iter" / "1" / "release_train.json"
        entry_val_release = repo3 / "iter" / "1" / "release_val.json"
        entry_val_payload = (
            json.loads(entry_val_release.read_text(encoding="utf-8"))
            if entry_val_release.exists()
            else {}
        )

        checks += [
            ("run_optimization ITSELF writes the release payload -- the entrypoint that ships, "
             "not just the engine it calls (Finding 3, at the seam that actually broke)",
             entry_train_release.exists() and entry_val_release.exists()),
            ("...and the VAL release it writes carries the held-out scalar, which is the whole "
             "channel the 2026-09-02 run was missing",
             isinstance(
                 ((entry_val_payload.get("metrics") or {}).get("primary_metric") or {}).get(
                     "value"
                 ),
                 (int, float),
             )),
            ("...and the entrypoint completed without raising, so the two checks above are "
             "evidence of a written file and not of an early abort",
             entrypoint_error is None),
        ]

    # The wiring itself: you cannot build these components with a bare, unguarded agent.
    parts = _test_components(max_budget_usd=1000.0, train_n=10, require_command=False)

    # PT-B: what the run-start reset is handed comes from the optimizer build_components really builds.
    import sarol_optimizer  # noqa: PLC0415
    import sarol_program  # noqa: PLC0415

    carried = {pathlib.Path(c.path): c for c in reset_carried(parts, state_paths(parts["state_root"])["notes"])}
    named = _test_components(max_budget_usd=1000.0, train_n=10, require_command=False, run_id="pt-b-real-run")
    mat = pathlib.Path(parts["state_root"]).parent / "mat"
    saved_notes = parts["optimizer"].notes_root
    parts["optimizer"].notes_root = None
    try:
        no_notes_value = sarol_program.setup_value(parts["program_runner"], parts["optimizer"], materialize_root=mat)
    finally:
        parts["optimizer"].notes_root = saved_notes
    checks += [
        ("the built optimizer hands the reset the REAL notebook, as lineage state with its stub",
         sarol_optimizer.NOTEBOOK in carried and carried[sarol_optimizer.NOTEBOOK].lifetime == "lineage"
         and pathlib.Path(carried[sarol_optimizer.NOTEBOOK].stub) == sarol_optimizer.NOTEBOOK_STUB),
        ("...and the notes root the reset carries is the one the optimizer mounts",
         parts["optimizer"].notes_root == state_paths(parts["state_root"])["notes"]
         and carried[parts["optimizer"].notes_root].lifetime == "lineage"),
        ("D4: the setup value does not depend on the run id or the state root (so --print-pins matches a run)",
         parts["setup_value"] == named["setup_value"]),
        ("...negative control: without the notes mount the setup value changes, so that comparison can fail",
         no_notes_value != parts["setup_value"]),
        ("the one-time legacy copy writes into the notes root a real run mounts",
         importlib.import_module("copy_legacy_findings").NOTES_ROOT == state_paths(STATE_ROOT)["notes"]),
    ]

    # argv -> run_optimization, with the real parser. `run_optimization` is stubbed so nothing
    # is dispatched, materialized or spent: the assertion is purely that the flag survives the
    # hop from `args` into the run's kwargs.
    _cli_max_workers = None

    def _capture_run_optimization(**kwargs):
        nonlocal_holder["mw"] = kwargs.get("max_workers")
        nonlocal_holder["state_root"] = kwargs.get("state_root")
        nonlocal_holder["opt_budget"] = kwargs.get("optimizer_max_budget_usd")
        raise _StopCapture()

    class _StopCapture(Exception):
        pass

    nonlocal_holder: dict[str, Any] = {}
    _real_run_optimization = globals()["run_optimization"]
    globals()["run_optimization"] = _capture_run_optimization
    try:
        main([
            "--run", "--image", isolation_mod.FAKE_IMAGE, "--max-workers", "6",
            "--max-budget-usd", "1", "--run-id", "gate", "--train-n", "1",
            "--materialize-root", "/tmp/pt-gate-mat",
            "--train-output-root", "/tmp/pt-gate-train",
            "--val-output-root", "/tmp/pt-gate-val",
            "--train-inputs", "/tmp/pt-gate-train.json",
            "--val-inputs", "/tmp/pt-gate-val.json",
            "--state-root", "/tmp/pt-gate-state", "--optimizer-max-budget-usd", "1.5",
        ])
    except _StopCapture:
        pass
    except Exception:  # noqa: BLE001 -- a refusal before dispatch is still a failed capture
        pass
    finally:
        globals()["run_optimization"] = _real_run_optimization
    _cli_max_workers = nonlocal_holder.get("mw")
    checks.append(("--state-root and --optimizer-max-budget-usd reach the run (a live check's notes stay in "
                   "its scratch folder; its optimizer session keeps to its cap)",
                   nonlocal_holder.get("state_root") == pathlib.Path("/tmp/pt-gate-state")
                   and nonlocal_holder.get("opt_budget") == 1.5))

    # Finding 4: the canary must be priced from what is WIRED, and a real run must refuse to start
    # without one. The first optimization run priced three firings per iteration and executed
    # zero; these are the two checks that make that state unreachable rather than merely unlikely.
    import tempfile as _tempfile  # noqa: PLC0415

    canary_refusal = None
    other_refusal = None
    # ISOLATE THE PRECONDITION. This gate asserts "a run refuses when NO canary is pinned", and it
    # used to establish that condition by hoping none existed. It held only until someone actually
    # pinned one: on 2026-09-07 the first real `--pin` turned this gate red, because the gate was
    # reading whatever happened to be on the machine. A gate whose truth depends on an artifact
    # outside the test is not testing what its name says. So hide any real pin for the duration
    # and put it back afterwards -- the same save/restore the model-mismatch block below already
    # does 40 lines down; this one simply never adopted it.
    _gate_pin = canary_mod.pin_path("retrieval")
    _gate_saved = _gate_pin.read_text(encoding="utf-8") if _gate_pin.exists() else None
    if _gate_saved is not None:
        _gate_pin.unlink()
    try:
        with _tempfile.TemporaryDirectory() as _tmp:
            _val_root = pathlib.Path(_tmp) / "val-out"   # outside the repo, so C6.9 passes
            _common = dict(
                iterations=1, run_id="gate", train_input_ref="unused", val_input_ref="unused",
                train_n=1, materialize_root=pathlib.Path(_tmp) / "mat",
                train_output_root=pathlib.Path(_tmp) / "train-out", val_output_root=_val_root,
                profile="retrieval",
            )
            try:
                run_optimization(max_budget_usd=1000.0, **_common)
            except Exception as exc:  # noqa: BLE001 -- the message is what is being asserted
                canary_refusal = exc
            # With the canary explicitly waived the run gets PAST that gate and fails later, on
            # budget. Same call, one flag different -- so this proves the gate is the canary gate
            # and not some earlier refusal standing in for it.
            try:
                run_optimization(max_budget_usd=0.0, require_canary=False, **_common)
            except Exception as exc:  # noqa: BLE001
                other_refusal = exc
    finally:
        if _gate_saved is not None:
            _gate_pin.parent.mkdir(parents=True, exist_ok=True)
            _gate_pin.write_text(_gate_saved, encoding="utf-8")

    # The other half of Bug 1: the RAMPED path stages and verifies its batch, but a fixed
    # --train-inputs file was handed to the engine unchecked while preflight priced --train-n.
    with _tempfile.TemporaryDirectory() as _tmp2:
        _batch = pathlib.Path(_tmp2) / "train.json"
        _batch.write_text(json.dumps({"claims": [
            {"claim_id": f"C{i}", "citekey": f"k{i}", "staging_dir": _tmp2} for i in range(3)
        ]}), encoding="utf-8")
        _mismatch = _raises_valueerror(
            lambda: _static_train_inputs(
                adapter._import_engine().RunInputs, str(_batch), run_id="g", train_n=1))
        _match = _static_train_inputs(
            adapter._import_engine().RunInputs, str(_batch), run_id="g", train_n=3)

    # End-to-end on the plumbing that matters: a pin measured under `haiku`, a run requesting
    # `opus`, and the refusal must name both. If `run_optimization` stopped forwarding its model
    # to `canary.load`, this run would sail past the mismatch.
    _cpath = canary_mod.pin_path("retrieval")
    _cpath.parent.mkdir(parents=True, exist_ok=True)
    _csaved = _cpath.read_text(encoding="utf-8") if _cpath.exists() else None
    _model_reaches_canary = False
    try:
        _cpath.write_text(json.dumps({
            "profile": "retrieval", "split": "train", "model_requested": "haiku",
            "expected_verdict": "ACCURATE",
            "claim": {"claim_id": "M1", "citekey": "k", "staging_dir": str(_cpath.parent)},
        }), encoding="utf-8")
        with _tempfile.TemporaryDirectory() as _mt:
            try:
                run_optimization(
                    iterations=1, run_id="model-gate", train_input_ref="unused",
                    val_input_ref="unused", max_budget_usd=1e9, train_n=1,
                    materialize_root=pathlib.Path(_mt) / "mat",
                    train_output_root=pathlib.Path(_mt) / "tr",
                    val_output_root=pathlib.Path(_mt) / "va",
                    profile="retrieval", model="opus",
                )
            except Exception as exc:  # noqa: BLE001 -- a crash here is a FAILED gate, not a
                # crashed suite. If the model stops reaching `canary.load`, the run gets past the
                # mismatch and raises something else entirely; catching only ValueError would
                # turn that into a traceback that masks every check after it.
                _model_reaches_canary = "haiku" in str(exc) and "opus" in str(exc)
    finally:
        if _csaved is None:
            _cpath.unlink(missing_ok=True)
        else:
            _cpath.write_text(_csaved, encoding="utf-8")

    no_canary_model = CostModel.for_profile("retrieval", canary_enabled=False)
    checks += [
        ("a real run REFUSES to start with no canary pinned (Finding 4), as a recorded stop",
         type(canary_refusal).__name__ == "LoopStop" and getattr(canary_refusal, "reason", None) == "consumer_refused"),
        ("...saying so in the message, and naming how to pin one",
         canary_refusal is not None and "canary" in str(canary_refusal)
         and "--pin" in str(canary_refusal)),
        ("...and --no-canary gets PAST that gate, so the refusal really is about the canary",
         other_refusal is not None and "canary" not in str(other_refusal)),
        ("a fixed --train-inputs batch whose size disagrees with the priced --train-n is "
         "REFUSED -- the other half of Bug 1, where the ramp is not in play", _mismatch),
        ("...and a matching one passes through, so the check is on size and not on the path",
         _match.input_ref.endswith("train.json") and _match.split == "train"),


        # --model must reach the RUN, not just the estimate. The identical defect shipped once
        # already for --profile: it was parsed, priced the run, and dropped before the run began,
        # so the CLI printed a `retrieval` table and executed `agentic`. A flag that reaches only
        # the quote is worse than no flag, because the quote then lies with authority.
        ("--model reaches the constructed grader program, not merely the cost table",
         _test_components(
             max_budget_usd=1e9, train_n=1, require_command=False, model="sonnet")["program"].model == "sonnet"),
        ("...and with no --model the judge takes the one documented default, so 'unspecified' "
         "means exactly one thing across dispatcher, canary and adapter",
         _test_components(
             max_budget_usd=1e9, train_n=1, require_command=False)["program"].model == adapter.DEFAULT_JUDGE_MODEL),
        ("...and that model reaches the CANARY check too, so a run cannot be judged by one model "
         "against a pin measured with another",
         _model_reaches_canary),

        # The same flag-plumbing hazard, on the value that decides WHERE a run's answers are
        # archived. The per-call `batch_id` this module builds is deliberately different for TRAIN
        # (`{run_id}-train-i{n}`) and VAL (`{run_id}-val`), so the Runner cannot recover the run's
        # identity from it -- a Runner that silently fell back to the batch id would scatter one
        # run's answers across sibling archive roots and still look completely healthy. That is
        # exactly what shipped until the Codex audit caught it on 2026-09-21, so the wiring is
        # asserted rather than assumed.
        # `--resume` was unreachable from the CLI until 2026-09-22: the S26 guard compares the tree
        # against the manifest's frozen version, and after ANY run the tree carries a later one, so
        # every resume died on the guard whose own error text says to "pass a `current_tag`" -- a
        # flag that did not exist. Both halves are gated: the flag parses, and it actually reaches
        # `run_optimization`, because a flag that parses and is dropped looks identical from outside.
        ("--current-tag parses and defaults to the version the manifest freezes, so a plain run starts there",
         _parser().parse_args(["--run"]).current_tag is None
         and "current_tag = adapter.SarolProgramStore().program_version" in inspect.getsource(run_optimization)),
        ("...and names a later version when given one, which is what makes --resume reachable",
         _parser().parse_args(["--run", "--current-tag", "program-v7"]).current_tag == "program-v7"),
        ("...and `main` passes it through rather than dropping it on the floor",
         "current_tag=args.current_tag," in inspect.getsource(main)),

        # Under the engine runner the run id is part of every pass key and of every archive path,
        # and it reaches the runner in exactly one place: `as_runner(run_id=...)`.
        ("...and `run_optimization` threads it to build_components as well",
         "run_id=run_id," in inspect.getsource(run_optimization)),

        # --max-workers is the same flag-plumbing hazard a third time, so it is gated at BOTH
        # seams: the kwarg into the Runner, and argv into the run. Concurrency that silently
        # stayed at 1 would look exactly like "the pool did not help" and would be debugged as
        # a rate limit rather than as a dropped flag.
        ("a run with no committed pin for a session kind is refused before anything is built",
         _raises_valueerror(lambda: _test_components(max_budget_usd=1.0, train_n=1, require_command=False,
                                                     expected_fingerprints={"program": None, "optimizer": "x"}))),
        ("the engine runner's output root defaults to <run>/program-out, beside the TRAIN and VAL roots",
         (lambda p: p["program_runner"].root.root.name == "program-out"
          and p["program_runner"].root.root.parent == p["optimizer"].run_root
          and p["optimizer"].program_output_root == p["program_runner"].root.root)(
             _test_components(max_budget_usd=1.0, train_n=1, require_command=False))),
        ("--max-workers reaches the engine runner as max_concurrent",
         _test_components(
             max_budget_usd=1e9, train_n=1, require_command=False, max_workers=6)["program_runner"].spec.max_concurrent == 6),
        ("...and the default is serial, so concurrency is opt-in and every existing baseline "
         "was measured under the same dispatch the default still gives",
         _test_components(
             max_budget_usd=1e9, train_n=1, require_command=False)["program_runner"].spec.max_concurrent == 1),
        ("...and the CLI flag reaches the RUN, not merely the parser -- the defect that shipped "
         "for --profile and was nearly repeated for --model",
         _cli_max_workers == 6),
        ("a run with no canary wired prices ZERO canary sessions, so 'priced but absent' cannot "
         "happen again", no_canary_model.canary_sessions() == 0),
        ("...while a wired one is priced at three firings per iteration, per OQ12",
         CostModel.for_profile("retrieval").canary_sessions() == 3),
    ]

    # The check above asserts the COST MODEL's arithmetic, which is not the thing that refuses to
    # spend. `BudgetGuard` did its own sums and omitted the canary entirely, so those two gates
    # stayed green while enforcement under-reserved -- a decorative gate of exactly the kind that
    # let three silent failures through the first run. These assert the GUARD, behaviourally.
    _with = CostModel.for_profile("retrieval", val_size=5, canary_enabled=True)
    _without = CostModel.for_profile("retrieval", val_size=5, canary_enabled=False)
    guard_with = BudgetGuard(max_budget_usd=1e9, cost_model=_with, train_n=4)
    guard_without = BudgetGuard(max_budget_usd=1e9, cost_model=_without, train_n=4)
    need_with = guard_with.worst_case_to_finish_iteration("train")
    need_without = guard_without.worst_case_to_finish_iteration("train")
    canary_term = _with.canary_sessions() * _with.per_session_usd
    # A budget that covers the scored claims but NOT the canary must be refused -- the canary is
    # dispatched FIRST, so this is the case that would strand a run before its first scored claim.
    tight = BudgetGuard(max_budget_usd=need_without, cost_model=_with, train_n=4)
    checks += [
        ("the BUDGET GUARD reserves more when a canary is wired -- not just the cost model",
         need_with > need_without),
        ("...by exactly the canary term, so estimate and enforcement cannot drift again",
         abs((need_with - need_without) - canary_term) < 1e-9),
        ("a budget covering the scored claims but not the canary is REFUSED, since the canary "
         "is dispatched before the first scored claim",
         tight.check("train") is not None),
        ("...and the same budget is accepted once no canary is wired, so this is the canary term "
         "and not an off-by-one somewhere else",
         guard_without.__class__(max_budget_usd=need_without, cost_model=_without,
                                 train_n=4).check("train") is None),

        ("build_components wraps the optimizer agent in the contract guard",
         isinstance(parts["agent"], adapter.ContractGuardedAgent)),
        ("...around the contained optimizer (the engine's, sealed), never a host session",
         type(parts["agent"].inner).__name__ == "SarolOptimizer"
         and "--dangerously-skip-permissions" not in inspect.getsource(sys.modules[__name__])
         .split("def _selftest", 1)[0].split("def _integration_checks", 1)[0]),
        # Keyed on the metric NAME the adapter actually emits, not on a phrase from the prose.
        # The previous version matched "maximize 3-way macro-F1", which broke the moment the
        # objective moved -- and would have gone on passing if the prompt kept the old wording
        # while the scorer changed underneath it. The name is the seam both sides share.
        ("...which loads the hot-path prompt as its instructions, naming the objective the "
         "adapter actually reports",
         adapter.PRIMARY_METRIC_NAME in parts["agent"].inner.agent_instructions()),
        # The engine renders the description's `max_budget_usd` as `--max-budget-usd` on the session
        # argv (its contained_argv); what paper-trail owns is that the cap is set and is the one stated.
        ("the optimizer session also carries a hard budget cap",
         parts["agent"].inner.setup_description().max_budget_usd
         == parts["agent"].inner.max_budget_usd > 0),
    ]
    return checks


def _lifecycle_checks(schemas) -> list[tuple[str, bool]]:
    """PT-B: the engine's run bookkeeping as paper-trail wires it, driven through ``run_optimization``
    and the engine's real ``run_loop`` (fake runner, scorer and agent; no sessions, no spend).

    Every run uses a scratch state root, so the real notebook, notes history and archive are never
    touched. The optimizer's notes filing needs a real session and is the live check's to prove.
    """
    import tempfile  # noqa: PLC0415
    import types  # noqa: PLC0415

    import engine.run_start as run_start_mod  # noqa: PLC0415
    from engine.loop import LoopStop  # noqa: PLC0415
    from engine.versioning import version_lock  # noqa: PLC0415
    import sarol_optimizer  # noqa: PLC0415

    checks: list[tuple[str, bool]] = []
    real_store = SarolProgramStore()
    stub = sarol_optimizer.NOTEBOOK_STUB.read_text(encoding="utf-8")

    class _Runner:
        """Counts validation passes; can fail the k-th one; can change its pass identity after each
        training pass (as an edited grader prompt would)."""

        def __init__(self, run_id, *, fail_val_call=None, identity_moves=False):
            self.run_id = run_id
            self.val_calls = 0
            self.fail_val_call = fail_val_call
            self.identity_moves = identity_moves
            self.prompt = 0

        def run(self, materialized_path, inputs):
            if inputs.split == "val":
                self.val_calls += 1
                if self.val_calls == self.fail_val_call:
                    return schemas.RunArtifacts(
                        batch_id=inputs.batch_id, status="program_error", artifact_refs=(), cost_usd=0.0,
                        error=schemas.ErrorInfo(code="PROGRAM_CRASHED", message_redacted="MARKER-a validation claim"),
                    )
            elif self.identity_moves:
                self.prompt += 1
            return schemas.RunArtifacts(batch_id=inputs.batch_id, status="ok", artifact_refs=(), cost_usd=0.0)

        def cache_identity(self, materialized_path, inputs):
            return f"prompt-{self.prompt}"

    class _NoForwarding:
        """What the old wrapper exposed to the engine: run(), and nothing else."""

        def __init__(self, inner):
            self.inner = inner

        def run(self, materialized_path, inputs):
            return self.inner.run(materialized_path, inputs)

    class _Scorer:
        def score(self, artifacts, split, task_config):
            return schemas.ScoreResult(
                primary_metric=schemas.PrimaryMetric(name=adapter.PRIMARY_METRIC_NAME, value=0.4, higher_is_better=True),
                breakdown={"scored": True, "n_total": 1, "n_invalid": 0, "retrieval_k": 20, "profile": "retrieval",
                           "per_class_f1": {"ACCURATE": 0.9}},
                task_config={**task_config, "_split": split},
            )

    class _CleanAgent:
        def __init__(self, root):
            self.root = root

        def run(self, *, iter_n: int, materialized_path=None):
            editable = self.root / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
            editable.write_text(editable.read_text(encoding="utf-8") + f"\n<!-- iter {iter_n} -->\n", encoding="utf-8")
            return adapter.GuardedOutcome(exit_code=0, detail="clean edit")

    with tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as td:
        tmp = pathlib.Path(td)
        state = tmp / "state"
        batch = tmp / "batch.json"
        batch.write_text(json.dumps({"claims": [{"claim_id": "C0", "citekey": "k0", "staging_dir": td}]}),
                         encoding="utf-8")

        def _repo(name):
            repo = tmp / name
            repo.mkdir()
            _seed_repo(repo, real_store)
            notebook = tmp / f"{name}-meta-learnings.md"
            return repo, notebook

        def _run(repo, notebook, runner, *, run_id, current_tag="program-v0", iterations=1, resume=False, budget=None):
            store = SarolProgramStore(repo_root=repo)
            parts = {
                "program_store": store, "runner": runner, "scorer": _Scorer(),
                "profile": profiles_mod.get("retrieval"),
                "release_builder": adapter.SarolReleaseBuilder(setup_value="setup-v1:selftest"),
                "build_mistake_corpus": None,
                "agent": adapter.ContractGuardedAgent(_CleanAgent(repo), store, tree_root=repo),
                "budget": budget, "cost_model": CostModel.for_profile("retrieval", val_size=1),
                "optimizer": types.SimpleNamespace(notebook=notebook), "state_root": state,
                # The selftest's stand-ins are not sealed sessions; said out loud, as the driver requires.
                "unsealed": ("optimizer", "program"),
            }
            return run_optimization(
                iterations=iterations, run_id=run_id, train_input_ref=str(batch), val_input_ref=str(batch),
                max_budget_usd=1e9, train_n=1, materialize_root=tmp / f"mat-{run_id}", current_tag=current_tag,
                components=parts, run_summary_path=tmp / f"summary-{run_id}.json", resume=resume,
            )

        def _archived(run_id):
            return sorted((state / "runs" / "_archive").glob(f"*-{run_id}"))

        # -- B3: a fresh start archives the lineage; a continuation keeps it -------------------------
        repo_a, nb_a = _repo("a")
        nb_a.write_text("a lesson from an earlier lineage\n", encoding="utf-8")
        (repo_a / "iter" / "9").mkdir(parents=True)
        (repo_a / "iter" / "9" / "old.json").write_text("{}", encoding="utf-8")
        fresh_runner = _Runner("fresh-1")
        _run(repo_a, nb_a, fresh_runner, run_id="fresh-1", iterations=2)
        fresh_archive = _archived("fresh-1")
        moved = "".join(p.read_text(encoding="utf-8") for d in fresh_archive for p in d.rglob("*") if p.is_file())
        checks += [
            ("B3: a run from program-v0's content is FRESH: the notebook is archived and its stub put back",
             nb_a.read_text(encoding="utf-8") == stub and "a lesson from an earlier lineage" in moved),
            ("...and the previous run's iter/ is archived too", not (repo_a / "iter" / "9").exists() and "{}" in moved),
            ("B6: the probe and the next iteration's score of one version cost one validation pass (3, not 4)",
             fresh_runner.val_calls == 3),
        ]
        nb_a.write_text("a lesson this lineage earned\n", encoding="utf-8")
        _run(repo_a, nb_a, _Runner("cont-1"), run_id="cont-1", current_tag="program-v2")
        checks.append(("B3: a run from a later version CONTINUES the lineage and keeps the notebook (next-run H2)",
                       nb_a.read_text(encoding="utf-8") == "a lesson this lineage earned\n"))
        notes = state / "optimizer-notes"
        (notes / "earlier-run" / "iter-1").mkdir(parents=True, exist_ok=True)
        (notes / "earlier-run" / "iter-1" / "findings.md").write_text("an earlier note\n", encoding="utf-8")
        _run(repo_a, nb_a, _Runner("cont-n"), run_id="cont-n", current_tag="program-v3")
        kept = (notes / "earlier-run" / "iter-1" / "findings.md").exists()
        repo_n, nb_n = _repo("n")
        _run(repo_n, nb_n, _Runner("fresh-n"), run_id="fresh-n")
        moved_n = "".join(p.read_text(encoding="utf-8") for d in _archived("fresh-n") for p in d.rglob("*") if p.is_file())
        checks += [
            ("B3: a continuation keeps the notes history", kept),
            ("...and a fresh start archives it (moved, not deleted)",
             not (notes / "earlier-run").exists() and "an earlier note" in moved_n),
        ]

        # -- B6 through the wrapper: the runner's identity and run id must reach the engine -----------
        repo_b, nb_b = _repo("b")
        moving = _Runner("ident-1", identity_moves=True)
        _roomy = lambda: BudgetGuard(max_budget_usd=1e9, cost_model=CostModel.for_profile("retrieval", val_size=1), train_n=1)  # noqa: E731
        _run(repo_b, nb_b, moving, run_id="ident-1", iterations=2, budget=_roomy())
        repo_c, nb_c = _repo("c")
        moving_bare = _Runner("ident-2", identity_moves=True)
        _run(repo_c, nb_c, _NoForwarding(moving_bare), run_id="ident-2", iterations=2)
        checks += [
            ("B6: through the driver's budget hooks, a changed grader identity means a fresh validation pass (4 passes)",
             moving.val_calls == 4),
            ("...negative control: a wrapper that does not forward it reuses the stale pass (3 passes)",
             moving_bare.val_calls == 3),
        ]
        repo_d, nb_d = _repo("d")
        try:
            _run(repo_d, nb_d, _Runner("someone-elses-run"), run_id="mine", budget=_roomy())
            mismatch = None
        except LoopStop as exc:
            mismatch = exc.reason
        checks.append(("B5: through the driver's budget hooks, a runner bound to another run id stops the run",
                       mismatch == "run_id_mismatch"))

        # -- B6: a version whose validation pass crashes is a failed version, told to the optimizer ---
        repo_e, nb_e = _repo("e")
        failing = _Runner("fail-1", fail_val_call=2)
        _run(repo_e, nb_e, failing, run_id="fail-1", iterations=2)
        release2 = (repo_e / "iter" / "2" / "release_train.json")
        release_text = release2.read_text(encoding="utf-8") if release2.exists() else ""
        feedback = tmp / "feedback-e"
        sarol_optimizer.prepare_feedback(2, repo_root=repo_e, feedback_root=feedback)
        copied = feedback / "iter" / "2" / "release_train.json"
        copied_text = copied.read_text(encoding="utf-8") if copied.exists() else ""
        status_file = state / "run-store" / "version_status.json"
        checks += [
            ("B6: the next TRAIN release carries frontier.previous_attempt for the failed version",
             '"previous_attempt": {' in release_text and '"validation_pass"' in release_text),
            ("...and so does the copy in the optimizer's feedback folder, the only place it can read it",
             '"previous_attempt": {' in copied_text),
            ("...with no error message in either (the seal)",
             "MARKER" not in release_text and "MARKER" not in copied_text),
            ("...and the run store records the version as failed, so no later run starts from it",
             status_file.exists() and '"failed"' in status_file.read_text(encoding="utf-8")),
            ("...and the iteration after it scores the held base without a new pass (3 passes, not 4)",
             failing.val_calls == 3),
        ]
        def _after(run_id):
            try:
                _run(repo_e, nb_e, _Runner(run_id), run_id=run_id, current_tag="program-v1")
                return None
            except LoopStop as exc:
                return exc.reason

        # No bypass (C-core, isolation OQ10): the tree still holds the later version, so the drift check
        # refuses first, for injected components too (it used to be skipped for them).
        drift_first = _after("after-fail-drift")
        subprocess.run(["git", "-C", str(repo_e), "checkout", "program-v1", "--", "experiments"], check=True,
                       capture_output=True)
        after_fail = _after("after-fail")
        checks += [
            (f"no bypass: a tree that is not the start version is refused even with injected components [got {drift_first}]",
             drift_first == "consumer_refused"),
            (f"B5: with the tree on program-v1, a run starting from that failed version is refused at run start "
             f"(the run store reaches the reset) [got {after_fail}]", after_fail == "start_from_failed_version"),
        ]

        # -- B5: a second driver stops at the lock, before the reset touches anything ----------------
        repo_f, nb_f = _repo("f")
        nb_f.write_text("must survive\n", encoding="utf-8")
        with version_lock(repo_f, "first-driver"):
            try:
                _run(repo_f, nb_f, _Runner("second-driver"), run_id="second-driver")
                second = None
            except LoopStop as exc:
                second = f"{exc.reason}: {exc}"
        checks.append(("B5: a second driver on the same repo stops at once (version_lock_held, as the "
                       "engine reports it), and nothing is archived",
                       second is not None and second.startswith("version_lock_held") and "first-driver" in second
                       and nb_f.read_text(encoding="utf-8") == "must survive\n" and not _archived("second-driver")))

        # -- the run id and the runner reach the driver, which binds one to the other (C-core) ---------
        # Captured at the driver's door rather than read from the source: the driver's own tests prove it
        # binds the runner it is handed to the run id it is handed (`as_runner(run_id=...)`).
        driver_mod = importlib.import_module("engine.driver")
        handed = {}
        real_run_driver = driver_mod.run_driver

        def _capture(config):
            handed["config"] = config
            raise LoopStop("captured", reason="captured")

        driver_mod.run_driver = _capture
        try:
            repo_h, nb_h = _repo("h")
            runner_h = _Runner("bind-1")
            try:
                _run(repo_h, nb_h, runner_h, run_id="bind-1")
            except LoopStop:
                pass
        finally:
            driver_mod.run_driver = real_run_driver
        cfg = handed.get("config")
        checks.append(("the run id and the runner reach the driver, which binds one to the other, so one run's "
                       "passes archive under one run",
                       cfg is not None and cfg.run_id == "bind-1" and cfg.runner is runner_h))

        # -- a stale engine is a recorded stop, not a traceback (implementation review, 2026-10-06) ------
        stale_val = tmp / "stale-engine" / "val"
        stale_summary = stale_val.parent / "run_summary.json"
        stale_summary.parent.mkdir(parents=True)
        stale_rows = [{"iter": 1, "tag": "program-v12"}, {"iter": 2, "tag": "program-v13"}]
        stale_summary.write_text(json.dumps({"config": {}, "run_id": "eng-stale", "iters": stale_rows}), encoding="utf-8")
        real_on_path = isolation_mod.engine_on_path

        def _stale_engine():
            raise RuntimeError("refusing to run against this engine checkout: the engine does not contain the "
                               "pinned commit (selftest stand-in)")

        isolation_mod.engine_on_path = _stale_engine
        try:
            import contextlib as _cl  # noqa: PLC0415
            import io as _io  # noqa: PLC0415

            with _cl.redirect_stdout(_io.StringIO()), _cl.redirect_stderr(_io.StringIO()):
                stale_rc = main([
                    "--run", "--image", isolation_mod.FAKE_IMAGE, "--run-id", "eng-stale", "--train-n", "1",
                    "--max-budget-usd", "1", "--train-inputs", str(batch), "--val-inputs", str(batch),
                    "--materialize-root", str(tmp / "stale-engine" / "mat"),
                    "--train-output-root", str(tmp / "stale-engine" / "train"), "--val-output-root", str(stale_val),
                ])
        finally:
            isolation_mod.engine_on_path = real_on_path
        stale_after = json.loads(stale_summary.read_text(encoding="utf-8"))
        checks.append(("a stale engine stops the CLI with exit 3 and a recorded engine_version stop, keeping the "
                       "summary's rows (no traceback)",
                       stale_rc == 3 and stale_after.get("iters") == stale_rows
                       and (stale_after.get("stop") or {}).get("reason") == "engine_version"))

        # -- a resume continues its own run: no reset ------------------------------------------------
        repo_g, nb_g = _repo("g")
        calls = []
        # The driver calls the reset (C-core), so the stand-in goes where the driver looks it up.
        real_prepare = driver_mod.prepare_run_start
        driver_mod.prepare_run_start = lambda **kw: calls.append(kw)
        try:
            try:
                _run(repo_g, nb_g, _Runner("res-1"), run_id="res-1", resume=True)
                resume_stop = "completed"
            except LoopStop as exc:  # a resume with no history stops; the reset is what is checked here
                resume_stop = exc.reason
            with version_lock(repo_g, "someone-else"):
                try:
                    _run(repo_g, nb_g, _Runner("res-locked"), run_id="res-locked", resume=True)
                    resume_locked = None
                except LoopStop as exc:
                    resume_locked = exc.reason
            _run(repo_g, nb_g, _Runner("res-2"), run_id="res-2")
        finally:
            driver_mod.prepare_run_start = real_prepare
        checks += [
            (f"a resume skips the run-start reset; a plain run calls it (the resume ended: {resume_stop})",
             [c["run_id"] for c in calls] == ["res-2"]),
            ("...and a resume still takes the lock (D2)", resume_locked == "version_lock_held"),
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
        ("a real run refuses an unrunnable profile before spending anything, as a recorded stop",
         _stops(lambda: run_optimization(
             iterations=1, run_id="r", train_input_ref="t", val_input_ref="v",
             max_budget_usd=1.0, train_n=1, materialize_root=repo,
             train_output_root=repo / "trainout",
             val_output_root=pathlib.Path(_outside), profile="agentic"), "consumer_refused")),
        ]
        # The negative control the plan asks for: a run wired with a readable VAL root must refuse,
        # not quietly produce a leaky run. Since C-core the refusal is one of the driver's before_run
        # hooks, which run on every run, injected components included (isolation OQ10).
        _hook_parts = {"program_store": _FakeStore(repo), "profile": profiles_mod.get("retrieval"),
                       "cost_model": CostModel.for_profile("retrieval")}

        def _val_hook(root):
            hooks = {h.__name__: h for h in run_refusals(_hook_parts, current_tag="program-v0", val_output_root=root,
                                                          peak_train_n=1, iterations=1, max_budget_usd=1e9)}
            return hooks["val_isolation"](None)

        checks += [
            ("the driver's VAL-isolation refusal names a readable VAL root",
             "VAL isolation (C6.9)" in (_val_hook(inside) or "")),
            ("...and passes one outside the tree (negative control)", _val_hook(pathlib.Path(_outside)) is None),
        ]

        # The CLI is where this broke: `--profile` was parsed, used to price the run, then dropped
        # before `run_optimization` -- so `--profile retrieval` printed a retrieval cost table and
        # ran `agentic`. Capture what main() actually forwards.
        seen: dict = {}

        class _StopRecorder(Exception):
            pass

        def _recorder(**kw):
            seen.update(kw)
            raise _StopRecorder("stop before doing any work")

        _real = globals()["run_optimization"]
        globals()["run_optimization"] = _recorder
        try:
            try:
                main([
                    "--run", "--image", isolation_mod.FAKE_IMAGE, "--profile", "retrieval",
                    "--run-id", "r1", "--train-n", "10", "--max-budget-usd", "1",
                    "--train-inputs", "t.json", "--val-inputs", "v.json",
                    "--materialize-root", str(repo),
                    "--train-output-root", str(repo / "trainout"),
                    "--val-output-root", _outside,
                ])
            except _StopRecorder:
                pass
            no_roots = main([
                "--run", "--image", isolation_mod.FAKE_IMAGE, "--run-id", "r", "--train-n", "10", "--max-budget-usd", "1",
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
                if entry.get("pattern"):
                    continue  # a folder pattern (PT14) is not a file
                dst = tree / entry["path"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes((store.repo_root / entry["path"]).read_bytes())

            batch = pathlib.Path(tmp) / "batch.json"
            batch.write_text(json.dumps({"claims": []}), encoding="utf-8")
            inputs = schemas.RunInputs(input_ref=str(batch), batch_id="b1", split="val")

            calls: list[str] = []

            class _Inner:
                run_id = "run-a"

                def run(self, materialized_path, inp):
                    calls.append(inp.split)
                    return schemas.RunArtifacts(
                        batch_id=inp.batch_id, status="ok", artifact_refs=(),
                        sub_invocation_count=3, cost_usd=1.25,
                    )

                def cache_identity(self, materialized_path, inp):
                    return f"calls+setup+prompt:{inp.batch_id}"

            # The budget is two driver hooks since C-core (`budget_hooks`): refuse before a pass, charge
            # after it. The engine's hook wrapper keeps the runner's run id and pass identity; its tests
            # and the lifecycle checks above (through the driver) cover that.
            budget = BudgetGuard(max_budget_usd=1_000_000.0, cost_model=cm, train_n=10)
            hooks = budget_hooks(budget)
            inner = _Inner()
            for _ in range(2):
                hooks["before_pass"][0](inputs)
                hooks["after_pass"][0](inputs, inner.run(tree, inputs))
            checks += [
                ("a roomy budget lets each pass through, and real metered spend is recorded, not the estimate",
                 len(calls) == 2 and budget.spent_usd == 2.5),
                ("no budget, no hooks", budget_hooks(None) == {}),
            ]

            broke = budget_hooks(BudgetGuard(max_budget_usd=0.01, cost_model=cm, train_n=50))
            refused = None
            try:
                broke["before_pass"][0](schemas.RunInputs(input_ref=str(batch), batch_id="b2", split="train"))
            except Exception as exc:  # noqa: BLE001 -- the stop's reason is what is asserted
                refused = exc
            checks += [
                ("an unaffordable pass stops the run before it is dispatched, as budget_exhausted",
                 type(refused).__name__ == "LoopStop" and getattr(refused, "reason", None) == "budget_exhausted"),
                ("...naming the budget", "budget:" in str(refused)),
            ]

        # -- S26: the tag guard ---------------------------------------------------------------
        # Two halves, because either alone gives false assurance: that the re-hash SEES a drifted
        # editable file (`verify_contract_files` does not -- that is the whole reason the second
        # method exists), and that `run_optimization` actually CALLS it before dispatching.
        with tempfile.TemporaryDirectory() as tag_tmp:
            tag_repo = pathlib.Path(tag_tmp) / "repo"
            tag_repo.mkdir()
            # Seeded from the manifest's own `source_refs`, NOT from the live tree. `_seed_repo`
            # copies whatever is on disk today and tags it `program-v0` -- which is the very
            # mislabelling this guard exists to catch, and the live tree does currently differ on
            # the two files an optimizer run rewrites. A gate for "does the tree match the tag"
            # cannot be seeded from a tree that does not.
            _real = SarolProgramStore()
            for _entry in _real.entries:
                _dst = tag_repo / _entry["path"]
                _dst.parent.mkdir(parents=True, exist_ok=True)
                _blob = subprocess.run(
                    ["git", "show",
                     f"{_real.raw['source_refs'][_entry['source']]['commit']}:{_entry['path']}"],
                    cwd=str(_real.repo_root), capture_output=True, check=True,
                ).stdout
                _dst.write_bytes(_blob)

            # The tag the manifest freezes (program-v11 since PT-A): the guard checks that version.
            _TAG = SarolProgramStore().program_version
            # Make it a real repo and TAG it, because the tag is the half that matters most: the
            # engine materializes from `git show <tag>:<path>`, never off disk.
            def _g(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(tag_repo), *args], capture_output=True, text=True, check=True,
                    env={"PATH": os.environ.get("PATH", ""), "HOME": str(tag_repo),
                         "GIT_CONFIG_NOSYSTEM": "1"},
                ).stdout.strip()

            _g("init", "-q", "-b", "main")
            _g("config", "user.email", "selftest@example.invalid")
            _g("config", "user.name", "selftest")
            _g("add", "-A")
            _g("commit", "-q", "-m", _TAG)
            _g("tag", "-a", _TAG, "-m", _TAG)
            _good_commit = _g("rev-parse", "HEAD")

            tag_store = SarolProgramStore(repo_root=tag_repo)

            pristine = not tag_store.verify_tree_matches_tag()
            tag_pristine = not tag_store.verify_tag_tree(_TAG)

            # Edit an EDITABLE, non-contract file -- exactly what an optimizer iteration does, and
            # exactly what the contract re-hash is blind to by design.
            editable = tag_repo / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
            editable.write_text(
                editable.read_text(encoding="utf-8") + "\n<!-- an iteration's edit -->\n",
                encoding="utf-8",
            )
            drifted = tag_store.verify_tree_matches_tag()
            contract_blind = tag_store.verify_contract_files()

            checks += [
                ("a pristine checkout matches the tag it names", pristine),
                ("...and an edit to an EDITABLE file makes it stop matching",
                 len(drifted) == 1
                 and drifted[0].path == "experiments/sarol-2024/specs/verdict_schema_sarol.md"),
                # The negative control, and the reason the tag guard is not just a second call to
                # `verify_contract_files`: the contract re-hash is silent on exactly the files an
                # optimizer run rewrites, so it can never answer "is this tree still v0?".
                ("negative control: the CONTRACT re-hash is blind to that same edit, which is why "
                 "a separate whole-tree check had to exist",
                 contract_blind == []),
                ("the TAG carries the frozen content too -- it is what the engine materializes "
                 "from, and the tree check cannot speak for it",
                 tag_pristine),
            ]


            # The wiring. Point `run_optimization` at the drifted checkout and check it refuses
            # before it prices or dispatches anything.
            _real_store_cls = adapter.SarolProgramStore
            adapter.SarolProgramStore = lambda *a, **k: SarolProgramStore(repo_root=tag_repo)
            try:
                run_optimization(
                    iterations=1, run_id="tagguard",
                    train_input_ref="unused", val_input_ref="unused",
                    max_budget_usd=1.0, train_n=1,
                    materialize_root=pathlib.Path(tag_tmp) / "mat",
                    train_output_root=pathlib.Path(tag_tmp) / "trainout",
                    val_output_root=pathlib.Path(tag_tmp) / "valout",
                    profile="retrieval", require_canary=False,
                )
                refusal = ""
            except Exception as exc:  # noqa: BLE001 -- only the drift refusal's own stop counts
                refusal = _drift_refusal_text(exc)
            finally:
                adapter.SarolProgramStore = _real_store_cls

            checks += [
                ("run_optimization REFUSES a tree that does not match the tag it would file its "
                 "numbers under",
                 f"does not match '{_TAG}'" in refusal),
                ("...naming the file that drifted, so the fix is obvious",
                 "verdict_schema_sarol.md" in refusal),
            ]
            # The scenario a Codex audit actually found on 2026-09-07, reproduced: a CLEAN working
            # tree matching the manifest, and a tag left behind on older bytes. The tree check
            # reports no problem; the run would materialize the old program and file the numbers
            # under the new identity. Only `verify_tag_tree` sees it.
            editable.write_text(  # restore the tree so ONLY the tag is wrong
                editable.read_text(encoding="utf-8").replace(
                    "\n<!-- an iteration's edit -->\n", ""),
                encoding="utf-8",
            )
            _g("add", "-A")
            _g("commit", "-q", "--allow-empty", "-m", "later work")
            # Move the tag onto a commit whose enum predates the freeze.
            _stale = tag_repo / "experiments/sarol-2024/specs/verdict_enum_sarol.md"
            _kept = _stale.read_text(encoding="utf-8")
            _stale.write_text(_kept + "\nAN OLDER ENUM\n", encoding="utf-8")
            _g("add", "-A")
            _g("commit", "-q", "-m", "stale enum")
            _stale_commit = _g("rev-parse", "HEAD")
            _g("tag", "-f", "-a", _TAG, _stale_commit, "-m", "stale")
            _stale.write_text(_kept, encoding="utf-8")  # tree clean again, tag now wrong

            _tree_says = tag_store.verify_tree_matches_tag()
            _tag_says = tag_store.verify_tag_tree(_TAG)

            checks += [
                ("a stale TAG over a clean tree is caught -- the case the first version of this "
                 "guard missed entirely",
                 len(_tag_says) == 1
                 and _tag_says[0].path
                 == "experiments/sarol-2024/specs/verdict_enum_sarol.md"),
                ("negative control: the TREE check calls that same repo clean, which is why "
                 "checking the tree alone was not enough",
                 _tree_says == []),
                ("a tag that does not resolve at all is a violation, not a silent pass",
                 len(tag_store.verify_tag_tree("program-v999"))
                 == sum(1 for e in tag_store.entries if not e.get("pattern"))),
            ]

            _g("tag", "-f", "-a", _TAG, _good_commit, "-m", _TAG)

            # ...and the same wiring for the TAG half. Restore the tree first so the tree check
            # passes and execution actually REACHES the tag check -- otherwise this gate would go
            # green off the tree refusal and prove nothing about the tag.
            editable.write_text(
                editable.read_text(encoding="utf-8").replace(
                    "\n<!-- an iteration's edit -->\n", ""),
                encoding="utf-8",
            )
            _g("tag", "-f", "-a", _TAG, _stale_commit, "-m", "stale")
            adapter.SarolProgramStore = lambda *a, **k: SarolProgramStore(repo_root=tag_repo)
            try:
                run_optimization(
                    iterations=1, run_id="tagguard2",
                    train_input_ref="unused", val_input_ref="unused",
                    max_budget_usd=1.0, train_n=1,
                    materialize_root=pathlib.Path(tag_tmp) / "mat2",
                    train_output_root=pathlib.Path(tag_tmp) / "trainout2",
                    val_output_root=pathlib.Path(tag_tmp) / "valout2",
                    profile="retrieval", require_canary=False,
                )
                tag_refusal = ""
            except Exception as exc:  # noqa: BLE001 -- only the drift refusal's own stop counts
                tag_refusal = _drift_refusal_text(exc)
            finally:
                adapter.SarolProgramStore = _real_store_cls
                _g("tag", "-f", "-a", _TAG, _good_commit, "-m", _TAG)

            checks += [
                ("run_optimization ALSO refuses when the tree is clean but the TAG is stale -- "
                 "the engine materializes from the tag, so this is the one that decides what runs",
                 "does not carry the frozen" in tag_refusal),
                ("...naming the tag, and pointing at the re-cut that fixes it",
                 _TAG in tag_refusal and "git tag -f" in tag_refusal),
            ]

            # PT-B: a start tag other than the manifest's own is checked too, against its commit.
            editable.write_text(editable.read_text(encoding="utf-8") + "\n<!-- a later version -->\n",
                                encoding="utf-8")
            _g("commit", "-q", "-am", "a later version")
            _g("tag", "-a", "program-v12", "-m", "program-v12")
            later_clean = tag_store.tree_differs_from("program-v12") == []

            def _start_from(tag):
                adapter.SarolProgramStore = lambda *a, **k: SarolProgramStore(repo_root=tag_repo)
                try:
                    run_optimization(
                        iterations=1, run_id="laterguard", train_input_ref="unused", val_input_ref="unused",
                        max_budget_usd=1.0, train_n=1, materialize_root=pathlib.Path(tag_tmp) / "mat3",
                        train_output_root=pathlib.Path(tag_tmp) / "trainout3",
                        val_output_root=pathlib.Path(tag_tmp) / "valout3",
                        profile="retrieval", require_canary=False, current_tag=tag,
                        state_root=pathlib.Path(tag_tmp) / "state",
                    )
                    return ""
                except Exception as exc:  # noqa: BLE001 -- only the drift refusal's own stop counts
                    return _drift_refusal_text(exc)
                finally:
                    adapter.SarolProgramStore = _real_store_cls

            editable.write_text(editable.read_text(encoding="utf-8") + "\n<!-- uncommitted -->\n", encoding="utf-8")
            edited_refusal = _start_from("program-v12")
            _g("checkout", "--", str(editable.relative_to(tag_repo)))
            new_prompt = tag_repo / "experiments/sarol-2024/prompts/new-helper.md"
            new_prompt.parent.mkdir(parents=True, exist_ok=True)
            new_prompt.write_text("an untracked new file under a folder pattern\n", encoding="utf-8")
            new_listed = "experiments/sarol-2024/prompts/new-helper.md" in tag_store.tree_differs_from("program-v12")
            new_prompt.unlink()
            missing_refusal = _start_from("program-v99")
            past_guard = _start_from("program-v12")
            deleted = tag_repo / "experiments/sarol-2024/specs/verdict_enum_sarol.md"
            deleted_text = deleted.read_bytes()
            deleted.unlink()
            deleted_listed = "experiments/sarol-2024/specs/verdict_enum_sarol.md" in tag_store.tree_differs_from("program-v12")
            deleted.write_bytes(deleted_text)
            checks += [
                ("run_optimization lets a clean tree past the guard for a LATER start tag (it fails later, not there)",
                 "does not match 'program-v12'" not in past_guard and "does not resolve" not in past_guard),
                ("...and a deleted program file counts as a difference", deleted_listed),
                ("a later start tag whose commit the tree matches passes its check", later_clean),
                ("run_optimization REFUSES a tree edited since a LATER start tag (was skipped before PT-B)",
                 "does not match 'program-v12'" in edited_refusal and "verdict_schema_sarol.md" in edited_refusal),
                ("...and a new untracked file under a folder pattern counts as a difference", new_listed),
                ("...and a start tag that does not exist is refused, not skipped",
                 "program-v99 does not resolve" in missing_refusal),
            ]

        checks += _integration_checks(schemas)
        checks += _lifecycle_checks(schemas)
    else:
        checks.append((f"engine not found at {adapter.engine_path()} -- engine checks SKIPPED", True))

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def _run_summary_json(run, budget, *, stopped: bool) -> dict:
    """The dispatcher's stdout run summary. Reports Runner/judge spend (the ``BudgetGuard``)
    SEPARATELY from the optimizer-agent spend the engine tracks on ``LoopRun.spent_usd`` — labeling
    agent-only cost as the total is the defect the plan flags. ``run`` may be None for a stop that
    fired before any iteration completed (e.g. a resume-precondition mismatch)."""
    return {
        "run_id": getattr(run, "run_id", None),
        "best_tag": getattr(run, "best_tag", None),
        "best_metric_value": getattr(run, "best_metric_value", None),
        "stop_reason": getattr(run, "stop_reason", None) or ("stopped" if stopped else None),
        "iterations_completed": len(run.results) if run is not None else 0,
        # Real Runner/judge dollars (what the run actually paid the LLM judge).
        "runner_spent_usd": getattr(budget, "spent_usd", None),
        # Optimizer-agent dollars only (the Claude Code editing sessions) — NOT the total.
        "agent_spent_usd": getattr(run, "spent_usd", None),
    }


def _parser() -> "argparse.ArgumentParser":
    """The CLI, built separately from `main` so the selftests can gate flags by PARSING them.

    A flag asserted by grepping this file's source passes just as happily when `main` never reads
    it -- which is exactly how `--resume` stayed unreachable: the option existed, the guard it had
    to satisfy did not take it, and nothing compared the two.
    """
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
    ap.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help=(
            "claims dispatched concurrently (default 1 = serial). Claims are independent, so "
            "this changes wall-clock only -- every session, prompt and materialized tree is "
            "byte-identical, and a serially-measured baseline stays comparable. The useful "
            "ceiling is empirical: each claim spawns a nested session which itself spawns a "
            "subagent, so N here is ~2N concurrent API consumers. Ramp it and watch for "
            "rate-limit errors."
        ),
    )
    ap.add_argument(
        "--model",
        default=None,
        help=(
            "the JUDGE's model (alias or full id). Defaults to the Runner's own default. This "
            "is where ~all the spend is -- one nested session per claim, ~113 an iteration -- so "
            "it is the knob that moves the bill. Changing it invalidates program-v0's baseline "
            "and any canary pinned under the previous model; the canary refuses that mismatch."
        ),
    )
    ap.add_argument(
        "--image",
        default=None,
        help=(
            "the grader image, BY DIGEST in the engine's form (name:version@sha256:...). Default: "
            "the locally built paper-trail-isolation image (sarol_isolation.SHIPPING_IMAGE_TAG). A bare "
            "tag is refused by the engine: an image rebuilt on a newer base layer keeps its tag and "
            "changes its bytes, so a tag cannot say what the run ran on."
        ),
    )
    ap.add_argument(
        "--optimizer-image",
        default=None,
        help=(
            "the optimizer image, by digest (name:version@sha256:...). Default: the locally built "
            "paper-trail-optimizer image (optimizer/image/Dockerfile: the engine image plus python3)."
        ),
    )
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
    ap.add_argument(
        "--no-canary",
        action="store_true",
        help="run WITHOUT the round-trip canary. A run has one by default and refuses to start "
             "without a pin, because the first optimization run priced three firings per "
             "iteration and executed none, silently. This flag makes that choice explicit and "
             "reprices the run to match.",
    )
    ap.add_argument(
        "--run-summary",
        default=None,
        help="path to the durable resume ledger (rewritten every iteration). Defaults to "
             "run_summary.json in the VAL output root's parent dir. Must be the SAME path on the "
             "original run and its --resume continuation.",
    )
    ap.add_argument(
        "--current-tag",
        default=None,
        help="the program version the working tree already holds. Defaults to the version the "
             "manifest freezes (program-v11 since PT-A), which is right for a baseline run. ⚠ **Required to RESUME**: after any run the tree carries "
             "the last version the optimizer committed, and the S26 tree-vs-tag guard compares "
             "against the manifest's frozen version -- so without this, `--resume` is refused by "
             "the very guard whose error message tells you to pass it, and the feature is "
             "unreachable from the command line (found 2026-09-22 trying to resume a run that had "
             "stopped on a usage limit).",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="continue an interrupted run from its last cleanly-committed program-v<k>: "
             "reconstruct the frontier from the --run-summary ledger + the program-v0..vk tag "
             "chain and resume at iteration k+1. STOPs if the profile / rubric differ from the "
             "recorded run (a curve must not mix two systems).",
    )
    ap.add_argument(
        "--state-root",
        default=None,
        help="where the run's lasting state lives: the optimizer's notes history, the run store and "
             "the run-start archive (default ~/.paper-trail). A check run on a throwaway clone passes a "
             "scratch folder so its notes never reach the real lineage.",
    )
    ap.add_argument(
        "--optimizer-max-budget-usd",
        type=float,
        default=None,
        help="cap on each optimizer session's spend (default: build_components' own, $20)",
    )
    return ap


def main(argv: "list[str] | None" = None) -> int:
    args = _parser().parse_args(argv)

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
            "--materialize-root": args.materialize_root,
            "--train-output-root": args.train_output_root,
            "--val-output-root": args.val_output_root,
        }
        if schedule is None:
            required["--train-n"] = args.train_n
            required["--train-inputs"] = args.train_inputs
        # --val-n draws and stages its own VAL batch, so a supplied one would be ignored.
        if not args.val_n:
            required["--val-inputs"] = args.val_inputs
        missing = [flag for flag, value in required.items() if value is None]
        if missing:
            print(f"--run requires: {', '.join(missing)}", file=sys.stderr)
            return 2
        # LoopStop lives in the shared engine. Only make it importable here: run_optimization checks the
        # engine and turns a refusal into a recorded `engine_version` stop, caught below like any other.
        _eng = engine_pin.engine_path()
        if str(_eng) not in sys.path:
            sys.path.append(str(_eng))  # appended, never in front: see sarol_isolation.engine_on_path
        try:
            from engine.driver import exit_code  # noqa: PLC0415
            from engine.loop import LoopStop  # noqa: PLC0415
        except ImportError as exc:
            print(f"STOP (engine_version): the engine at {_eng} cannot run the shared driver: {exc}. "
                  f"{engine_pin.pin_problem(_eng) or ''}", file=sys.stderr)
            return 3
        try:
            run, budget = run_optimization(
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
                require_canary=not args.no_canary,
                # Same lesson as --profile and --model: a flag that reaches the estimate and not
                # the run is worse than no flag. Gated in `_selftest`.
                max_workers=args.max_workers,
                # Same lesson as --profile directly above: a flag that reaches the estimate and
                # not the run is worse than no flag. `model` rides `**component_kwargs` into
                # `build_components`, which hands it to the Runner.
                run_summary_path=(pathlib.Path(args.run_summary) if args.run_summary else None),
                resume=args.resume,
                current_tag=args.current_tag,
                state_root=pathlib.Path(args.state_root) if args.state_root else None,
                **({"optimizer_max_budget_usd": args.optimizer_max_budget_usd}
                   if args.optimizer_max_budget_usd is not None else {}),
                # Ride `**component_kwargs` into `build_components`. None means the locally built
                # image, resolved to its digest there; there is no uncontained mode either way.
                grader_image=args.image,
                optimizer_image=args.optimizer_image,
                **({"model": args.model} if args.model else {}),
            )
        except LoopStop as exc:
            # Every refusal and every hard stop (a stale setup pin, the budget, a bad probe, a resume
            # config mismatch, a security trip-wire) is a stop, recorded in the run summary by the
            # driver. Print the partial-run summary the engine attached, if the loop started, and exit
            # non-zero. NOT swallowed.
            run = exc.run
            budget = getattr(exc, "budget", None)
            print(f"STOP ({exc.reason or 'loop_stop'}): {exc}", file=sys.stderr)
            print(json.dumps(_run_summary_json(run, budget, stopped=True), indent=2))
            return exit_code(exc)
        print(json.dumps(_run_summary_json(run, budget, stopped=False), indent=2))
        return exit_code(run)

    # The preflight table prices what a run would ACTUALLY do: a canary term only if one is
    # pinned and not waived. A quote that assumes a guard the run will not execute is the same
    # class of error as the `--val-n` priced-but-not-sampled bug -- an estimate describing a
    # different run than the one about to happen.
    cost_model = CostModel.for_profile(
        args.profile,
        per_session_usd=args.per_session_usd,
        val_size=args.val_n or VAL_SIZE,
        canary_enabled=(
            not args.no_canary
            and canary_mod.load(profiles_mod.get(args.profile).name) is not None
        ),
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
