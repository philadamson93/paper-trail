"""Which `agentic-label-opt` commit this experiment runs against, and the check that enforces it.

Every number this experiment produces depends on engine code that lives in a *different repository*,
resolved at runtime from a path. Nothing in git records which bytes those were. This module is the
one place that says which commit is required, so the shell runner and the three Python entry points
cannot drift apart about it.

**This is not a new gate — it is the existing one, moved and widened.**
``scripts/vm/run_hillclimb_vm.sh`` has pinned the engine since 2026-09-09, by *ancestry* rather than
equality so a forward re-pin still passes, behind a feature probe and an explicit override. That
check was good and is kept. Two things were wrong with it, both fixed here:

* It named a commit that went **28 commits stale**. Because the test is "is the pin reachable from
  HEAD", a checkout with no :class:`SessionScope`, no ``inherit_env`` and no ``render_dispatch``
  passed it cleanly — and the isolation work would then fail at import, or quietly not run at all.
* It guarded **one of four** ways the engine gets resolved. ``adapter.engine_path()`` (which
  ``dispatcher``, ``canary``, ``sampling`` and ``run_baseline`` all reach through),
  ``isolation.engine_path()`` and ``scripts/materialize_smoke.py`` had no check between them.

**Why ancestry and not equality.** Equality would break on every engine commit, including ones that
change nothing we use, and the override would become habitual — a gate everyone switches off is not
a gate. Ancestry says "at least this", which is the real requirement, and it still catches the
failure that actually happens: a checkout parked on another session's branch. Measured 2026-09-09 —
a sibling branch satisfied every feature probe and still crashed ``dispatcher --selftest`` with
``'function' object has no attribute 'batch_id'``.

**What this does NOT catch, stated because a guard whose limits are unwritten gets over-trusted:**

* **Uncommitted edits in the engine tree.** Ancestry reads committed history; a dirty working tree
  is invisible to it. :func:`engine_description` reports dirtiness so a run log records it, but it
  is not a failure — engine development would be impossible if it were.
* **A branch cut from the pin that later broke the seam.** The pin is still an ancestor, so this
  passes. The capability probe and the dispatcher selftest are the backstop.

Deliberate override: ``SAROL_ALLOW_ENGINE_DIVERGENCE=1``, the same switch the shell runner already
documents.
"""

from __future__ import annotations

import functools
import importlib
import os
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent

__all__ = [
    "ENGINE_PIN",
    "ENGINE_PIN_REASON",
    "OVERRIDE_ENV",
    "DEFAULT_ENGINE",
    "engine_path",
    "pin_problem",
    "capability_problem",
    "CAPABILITIES",
    "require_engine",
    "engine_description",
]

#: The `agentic-label-opt` commit this experiment requires, in full — short SHAs are ambiguous
#: across repos and `cat-file -e` will happily resolve a prefix to the wrong object in a big one.
#:
#: Bumped 2026-10-07 to `993dda1` (B8 + B9, stage 14): a run's start chosen by the engine's rule
#: (`engine.run_start.resolve_start`: newest good, seed or a tag; HEAD must hold it), the sealed optimizer's
#: feedback staged by the engine at `/workspace/ro/feedback` (`ContainedOptimizerAgent(iter_root)`), and
#: `bb018e5`, which puts HEAD back on the last good version after a failed one.
#: Earlier: 2026-10-06 from `5b512d9` (C-core, stage 14): the engine's shared driver (`engine.driver.run_driver`),
#: the setup check at run start (C0, `isolation.setup_gate`) and the engine-version check paper-trail's own
#: checks now call (C2, `engine.engine_version`).
#: Earlier: 2026-10-05 from `764419b` (PT-B, stage 14): the engine's run bookkeeping (B: version lock,
#: run-start reset, notes history, same-run pass reuse, failed versions, signal stop) and the optional-glob
#: staging fix. Then to `1141256` (same day): a run's start recorded as its tag's commit, so a
#: paper-trail run (whose main is ahead of its start tag) can be resumed; found by PT-B's live check.
#: Earlier: 2026-10-02 from `592862f` (PT-A, stage 14): the engine's sealed sessions (S1), seal proof and
#: setup fingerprint (S2), contained optimizer (A), program runner (PR), the IPv4-only proxy (A13), and
#: the contract-file copy-back rule plus paper-trail's seal replay on both grants (PT-A D12, D7).
#: Earlier: 2026-09-18 from `82f547d`.
ENGINE_PIN = "993dda11328236182b48050ecfcedcb69e5f7470"

#: What the pin buys, in one line, so the next person to bump it knows what they must not drop.
ENGINE_PIN_REASON = (
    "the engine's sealed sessions for both principals: SealedSession (S1), Forbidden entries, the setup "
    "fingerprint and image-by-digest (S2), ContainedOptimizerAgent (A), ProgramRunner (PR), and the "
    "IPv4-only allowlist proxy (A13), the copy-back refusal of a contract-file edit (PT-A D12), and the run "
    "bookkeeping: version lock, run-start reset, notes history, failed-version records (B), and the shared driver "
    "with the setup check at run start and the engine-version check (C0, C-core), and the run's start "
    "chosen by the engine's rule plus the optimizer's feedback staged by the engine (B8, B9)"
)

#: Set to "1" to run against an engine that does not contain the pin. Same switch the shell uses.
OVERRIDE_ENV = "SAROL_ALLOW_ENGINE_DIVERGENCE"

#: Where `agentic-label-opt` is checked out. A Mac-only default; the VM sets `AGENTIC_LABEL_OPT`.
DEFAULT_ENGINE = pathlib.Path.home() / "Documents" / "Misc" / "Projects" / "agentic-label-opt"


def engine_path() -> pathlib.Path:
    """The engine checkout this process will import from.

    The single definition. ``adapter.engine_path`` and ``isolation.engine_path`` delegate here;
    they used to be three separate copies of this line with three separate copies of the default.
    """
    return pathlib.Path(os.environ.get("AGENTIC_LABEL_OPT", DEFAULT_ENGINE)).expanduser()


def _git(engine: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(engine), *args],
        capture_output=True, text=True, check=False,
    )


#: What paper-trail builds on, as the engine's capability names (``engine.engine_version``, C2):
#: ``module:name`` for an attribute, ``module:function(param)`` for a parameter. A later commit that
#: removed or renamed one would otherwise surface mid-run as an AttributeError.
CAPABILITIES = (
    # PT-A (2026-10-01): the grant's strict entries, the program runner, the contained optimizer, the
    # setup pins and the image form.
    "isolation.session_scope:SessionScope", "isolation.session_scope:Forbidden",
    "isolation.session_scope:scope_problem", "isolation.session_scope:host_path_leak",
    "isolation.sealed_session:SealedSession", "isolation.sealed_session:SessionDescription",
    "isolation.sealed_session:AnthropicApiProfile", "isolation.sealed_session:NO_CREDENTIAL",
    "isolation.sealed_session:UNPINNED",
    "isolation.program_runner:ProgramRunner", "isolation.program_runner:ProgramSpec",
    "isolation.program_runner:CALL_CONTAINER_PATH",
    "isolation.pass_outputs:Call", "isolation.pass_outputs:PassStopped",
    "isolation.contained_agent:ContainedOptimizerAgent", "isolation.contained_agent:DeclaredOutput",
    "isolation.contained_agent:OPTIMIZER_TOOLS",
    "isolation.setup_fingerprint:setup_fingerprint", "isolation.setup_fingerprint:combined_value",
    "isolation.setup_fingerprint:committed_pin", "isolation.setup_fingerprint:platform_key",
    "isolation.image_pin:image_ref", "isolation.image_pin:image_ref_problem",
    # PT-B (2026-10-05): the run bookkeeping, and the optimizer's notes history.
    "engine.versioning:version_lock", "engine.versioning:VersionLockHeld",
    "engine.run_start:prepare_run_start", "engine.run_start:Carried",
    "engine.run_store:FakeRunStore.version_status",
    "isolation.contained_agent:ContainedOptimizerAgent(notes_root)",
    "isolation.contained_agent:ContainedOptimizerAgent(run_id)",
    "engine.loop:run_loop(expected_isolation_hash)",
    # Carried over from the shell probe this replaced: without these a bad probe mid-run aborts with a
    # bare traceback and loses the partial-run summary.
    "engine.loop:LoopStop(reason)", "engine.versioning:EmptyCommitError",
    # C-core (2026-10-05): the shared driver and the setup check at run start.
    "engine.driver:run_driver", "engine.driver:DriverConfig(after_pass)", "engine.driver:record_pre_loop_stop",
    "isolation.setup_gate:check_setup",
    "isolation.contained_agent:ContainedOptimizerAgent.setup_description",
    "isolation.program_runner:ProgramRunner.setup_description",
    # B8 + B9 (2026-10-07): the start point, and the feedback the engine stages for the optimizer.
    "engine.run_start:resolve_start", "engine.run_start:StartPoint", "engine.driver:DriverConfig(start)",
    "isolation.contained_agent:ContainedOptimizerAgent(iter_root)",
    "isolation.contained_agent:ContainedOptimizerAgent(train_feedback_roots)",
    "isolation.contained_agent:ContainedOptimizerAgent(validation_roots)",
    "isolation.contained_agent:ContainedOptimizerAgent(run_summary_path)",
    "isolation.contained_agent:FEEDBACK_PATH", "isolation.feedback:stage_feedback",
)


def _engine_version(engine: pathlib.Path):
    """The engine's own version checks (C2), imported from ``engine``. ``None`` when that engine
    predates them, which also means it predates the pin."""
    if str(engine) not in sys.path:
        sys.path.append(str(engine))  # appended: the engine root has its own adapter.py, which must never shadow ours
    try:
        return importlib.import_module("engine.engine_version")
    except ImportError:
        return None


def pin_problem(engine: pathlib.Path | None = None) -> str | None:
    """Is the engine checkout missing the pinned commit? Returns a problem, or None.

    The check itself is the engine's (``engine.engine_version.version_problem``, C2: a full-SHA pin
    that must be an ancestor of the engine's HEAD); this module keeps the pin, the reason and the
    override. Follows this codebase's ``-> str | None`` problem idiom: the caller decides.
    """
    engine = engine or engine_path()
    if not engine.is_dir():
        return (
            f"the engine checkout {engine} is not a directory; set AGENTIC_LABEL_OPT to an "
            "agentic-label-opt checkout (the built-in default is a Mac-only path)"
        )
    ev = _engine_version(engine)
    problem = (
        f"the engine at {engine} has no engine.engine_version, so it predates the required commit "
        f"{ENGINE_PIN[:7]}" if ev is None else ev.version_problem(ENGINE_PIN, engine_root=engine)
    )
    if problem is None:
        return None
    return f"{problem}. Check out a commit containing the pin, or set {OVERRIDE_ENV}=1 if the divergence is intended. The pin buys {ENGINE_PIN_REASON}."


def capability_problem(engine: pathlib.Path | None = None) -> str | None:
    """Can the engine actually produce what paper-trail builds on? Returns a problem, or None.

    Ancestry says the pin is *reachable*; it does not say a later commit kept what we need, and it says
    nothing at all about an uncommitted edit. The engine's ``capability_problem`` imports each name in
    :data:`CAPABILITIES` and reports the first one missing; ``import_origin_problem`` refuses an
    ``engine`` or ``isolation`` package imported from anywhere but this checkout.
    """
    engine = engine or engine_path()
    ev = _engine_version(engine)
    if ev is None:
        return f"the engine at {engine} has no engine.engine_version (it predates the shared driver, C-core)"
    return ev.import_origin_problem(engine) or ev.capability_problem(CAPABILITIES)


@functools.lru_cache(maxsize=None)
def _engine_problem(engine_str: str, probe_capabilities: bool) -> str | None:
    engine = pathlib.Path(engine_str)
    problem = pin_problem(engine)
    if problem is not None:
        return problem
    return capability_problem(engine) if probe_capabilities else None


def require_engine(
    engine: pathlib.Path | None = None, *, probe_capabilities: bool = False
) -> pathlib.Path:
    """Resolve the engine and refuse if it does not carry the pin. Returns the path.

    Memoized per (path, probe) so the ~20 ``_import_engine`` call sites cost one ``git`` invocation
    between them, not twenty. Honours ``SAROL_ALLOW_ENGINE_DIVERGENCE=1``.

    Raises:
        RuntimeError: the checkout does not contain the pin, and the override is not set.
    """
    engine = engine or engine_path()
    if os.environ.get(OVERRIDE_ENV) == "1":
        return engine
    problem = _engine_problem(str(engine), probe_capabilities)
    if problem is not None:
        raise RuntimeError(f"refusing to run against this engine checkout: {problem}")
    return engine


def engine_description(engine: pathlib.Path | None = None) -> str:
    """``<path> @ <sha>`` for a run log, with ``(DIRTY)`` when the tree has uncommitted edits.

    Dirtiness is reported rather than refused: ancestry cannot see it, and failing on it would make
    engine development impossible. Recording it is what lets a surprising number be explained later.
    """
    engine = engine or engine_path()
    if not engine.is_dir():
        return f"{engine} (missing)"
    sha = _git(engine, "rev-parse", "--short", "HEAD").stdout.strip() or "?"
    dirty = bool(_git(engine, "status", "--porcelain").stdout.strip())
    return f"{engine} @ {sha}{' (DIRTY -- uncommitted engine edits are in this run)' if dirty else ''}"


def _selftest() -> int:
    """The capability probe, positively and against a deliberately broken engine module."""
    engine = engine_path()
    real = capability_problem(engine)
    scope_mod = importlib.import_module("isolation.session_scope")
    saved = scope_mod.Forbidden
    try:
        del scope_mod.Forbidden
        broken = capability_problem(engine)
    finally:
        scope_mod.Forbidden = saved
    agent_cls = importlib.import_module("isolation.contained_agent").ContainedOptimizerAgent
    saved_init = agent_cls.__init__
    try:
        agent_cls.__init__ = lambda self, *, run_id=None: None  # an engine from before B4: no notes_root
        no_notes = capability_problem(engine)
    finally:
        agent_cls.__init__ = saved_init
    checks = [
        ("the pinned engine passes the capability probe", real is None),
        ("...and an optimizer agent without notes_root is reported (negative control)", no_notes is not None and "notes_root" in no_notes),
        ("...and a missing symbol is reported by name (negative control)", broken is not None and "Forbidden" in broken),
        ("...and putting it back passes again", capability_problem(engine) is None),
    ]
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover - a hand check, and what the shell runner calls
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--print-pin" in sys.argv:
        print(ENGINE_PIN)
        raise SystemExit(0)
    print(f"engine:  {engine_description()}")
    print(f"pin:     {ENGINE_PIN[:7]} -- {ENGINE_PIN_REASON}")
    for label, found in (("pin", pin_problem()), ("capability", capability_problem())):
        print(f"{label + ':':9}{found or 'OK'}")
    raise SystemExit(1 if (pin_problem() or capability_problem()) else 0)
