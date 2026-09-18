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
    "require_engine",
    "engine_description",
]

#: The `agentic-label-opt` commit this experiment requires, in full — short SHAs are ambiguous
#: across repos and `cat-file -e` will happily resolve a prefix to the wrong object in a big one.
#:
#: Bumped 2026-09-18 from `82f547d` (the mid-run failure-handling hardening, 2026-09-09).
ENGINE_PIN = "592862fe9e041a5597fac6cb8b3fe8f6549ed063"

#: What the pin buys, in one line, so the next person to bump it knows what they must not drop.
ENGINE_PIN_REASON = (
    "the contained-nested-session capability: SessionScope and build_contained_session_prefix "
    "(isolation/session_scope.py), inherit_env for passing a credential by name, and "
    "HostAllowlistNetworkStack.render_dispatch for one container per dispatch on a standing network"
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


def pin_problem(engine: pathlib.Path | None = None) -> str | None:
    """Is the engine checkout missing the pinned commit? Returns a problem, or None.

    Follows this codebase's ``-> str | None`` problem idiom (``dispatcher.val_isolation_problem``,
    ``isolation.unspecified_stage_problem``): the caller decides whether a problem is fatal.
    """
    engine = engine or engine_path()

    if not engine.is_dir():
        return (
            f"the engine checkout {engine} is not a directory; set AGENTIC_LABEL_OPT to an "
            "agentic-label-opt checkout (the built-in default is a Mac-only path)"
        )
    if _git(engine, "rev-parse", "--git-dir").returncode != 0:
        return f"the engine checkout {engine} is not a git repository, so its version is unknowable"
    if _git(engine, "cat-file", "-e", f"{ENGINE_PIN}^{{commit}}").returncode != 0:
        return (
            f"the engine checkout {engine} does not contain the required commit "
            f"{ENGINE_PIN[:7]} at all -- wrong repository, or a shallow clone. Fetch it, or set "
            f"{OVERRIDE_ENV}=1 to proceed anyway. The pin buys {ENGINE_PIN_REASON}."
        )
    if _git(engine, "merge-base", "--is-ancestor", ENGINE_PIN, "HEAD").returncode != 0:
        head = _git(engine, "rev-parse", "--short", "HEAD").stdout.strip() or "?"
        branch = _git(engine, "branch", "--show-current").stdout.strip() or "detached"
        return (
            f"the engine at {engine} is on {head} (branch '{branch}'), which does NOT contain the "
            f"required commit {ENGINE_PIN[:7]} -- so it predates or has forked below it. This is "
            f"usually a checkout left on another session's branch. Check out a commit containing "
            f"the pin, or set {OVERRIDE_ENV}=1 if the divergence is intended. The pin buys "
            f"{ENGINE_PIN_REASON}."
        )
    return None


def capability_problem(engine: pathlib.Path | None = None) -> str | None:
    """Can the engine actually produce a contained session? Returns a problem, or None.

    Ancestry says the pin is *reachable*; it does not say a later commit did not remove the thing
    we need, and it says nothing at all about an uncommitted edit. This imports the symbols the
    work is built on and fails on the first one missing: the contained-session vocabulary
    (``SessionScope``, ``build_contained_session_prefix``, ``scope_problem``), ``inherit_env``,
    ``render_dispatch``, and -- carried over from the shell probe this replaced -- ``LoopStop``'s
    ``reason`` and ``EmptyCommitError``.

    ⚠ **This module sits beside ``optimizer/isolation.py``, and the engine's package is also called
    ``isolation``.** With this directory on ``sys.path`` a plain ``import isolation.session_scope``
    resolves to the sibling *file* and dies with "isolation is not a package". Same dance as
    ``isolation._import_engine``: engine root to the front, this directory off, purge any
    half-bound ``isolation*`` modules, and restore the path afterwards.
    """
    engine = engine or engine_path()
    saved_path = list(sys.path)
    saved_modules = {k: v for k, v in sys.modules.items()
                     if k == "isolation" or k.startswith("isolation.")}
    try:
        sys.path[:] = [p for p in sys.path if p and pathlib.Path(p).resolve() != _HERE]
        sys.path.insert(0, str(engine))
        for name in list(saved_modules):
            del sys.modules[name]

        import inspect  # noqa: PLC0415

        scope = importlib.import_module("isolation.session_scope")
        for symbol in ("SessionScope", "build_contained_session_prefix", "scope_problem"):
            if not hasattr(scope, symbol):
                return f"the engine's isolation.session_scope has no {symbol}"

        docker_prefix = importlib.import_module("isolation.docker_prefix")
        params = inspect.signature(docker_prefix.build_docker_cmd_prefix).parameters
        if "inherit_env" not in params:
            return (
                "the engine's build_docker_cmd_prefix takes no inherit_env, so a credential could "
                "only be passed by value into the container command and its log"
            )

        allowlist = importlib.import_module("isolation.network_allowlist")
        if not hasattr(allowlist.HostAllowlistNetworkStack, "render_dispatch"):
            return (
                "the engine's HostAllowlistNetworkStack has no render_dispatch, so one network "
                "serves only one container and a per-claim dispatch loop cannot use it"
            )

        # ⚠ Carried over from the probe this replaced in `run_hillclimb_vm.sh`, NOT dropped. It
        # guards a different failure: without these, a bad probe mid-run aborts with a bare
        # traceback and loses the partial-run summary -- the exact thing that runner exists to
        # prevent. Folding the two probes together is the only reason it was safe to delete the
        # shell copy.
        loop = importlib.import_module("engine.loop")
        if "reason" not in inspect.signature(loop.LoopStop.__init__).parameters:
            return (
                "the engine's LoopStop takes no reason, so a mid-run failure would abort with a "
                "bare traceback and lose the partial-run summary"
            )
        versioning = importlib.import_module("engine.versioning")
        if not hasattr(versioning, "EmptyCommitError"):
            return "the engine's engine.versioning has no EmptyCommitError"
        return None
    except ImportError as exc:
        return f"the engine at {engine} could not be imported for the capability probe: {exc}"
    finally:
        sys.path[:] = saved_path
        for name in [k for k in sys.modules if k == "isolation" or k.startswith("isolation.")]:
            del sys.modules[name]
        sys.modules.update(saved_modules)


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


if __name__ == "__main__":  # pragma: no cover - a hand check, and what the shell runner calls
    if "--print-pin" in sys.argv:
        print(ENGINE_PIN)
        raise SystemExit(0)
    print(f"engine:  {engine_description()}")
    print(f"pin:     {ENGINE_PIN[:7]} -- {ENGINE_PIN_REASON}")
    for label, found in (("pin", pin_problem()), ("capability", capability_problem())):
        print(f"{label + ':':9}{found or 'OK'}")
    raise SystemExit(1 if (pin_problem() or capability_problem()) else 0)
