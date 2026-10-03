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
#: Bumped 2026-10-02 from `592862f` (PT-A, stage 14): the engine's sealed sessions (S1), seal proof and
#: setup fingerprint (S2), contained optimizer (A), program runner (PR), the IPv4-only proxy (A13), and
#: the contract-file copy-back rule plus paper-trail's seal replay on both grants (PT-A D12, D7).
#: Earlier: 2026-09-18 from `82f547d`.
ENGINE_PIN = "764419b22487b5ab00ebd6436eea6e63f1cb0bbe"

#: What the pin buys, in one line, so the next person to bump it knows what they must not drop.
ENGINE_PIN_REASON = (
    "the engine's sealed sessions for both principals: SealedSession (S1), Forbidden entries, the setup "
    "fingerprint and image-by-digest (S2), ContainedOptimizerAgent (A), ProgramRunner (PR), and the "
    "IPv4-only allowlist proxy (A13), and the copy-back refusal of a contract-file edit (PT-A D12)"
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
    work is built on and fails on the first one missing: since PT-A, the sealed session, the strict
    ``Forbidden`` entries, the program runner, the contained optimizer, the setup pins and the image
    form, ``run_loop``'s ``expected_isolation_hash``, and -- carried over from the shell probe this
    replaced -- ``LoopStop``'s ``reason`` and ``EmptyCommitError``.

    Paper-trail's own module was renamed ``sarol_isolation.py`` on 2026-10-01 so the engine's
    ``isolation`` package imports plainly.
    """
    engine = engine or engine_path()
    # Since 2026-10-01 paper-trail's own module is `sarol_isolation.py`, so the engine's `isolation`
    # package no longer collides with a sibling file: putting the engine on the path is enough, and
    # its modules stay bound for the rest of the process (one copy of each engine class).
    if str(engine) not in sys.path:
        sys.path.append(str(engine))  # appended: the engine root has its own adapter.py, which must never shadow ours
    try:
        import inspect  # noqa: PLC0415

        # What PT-A builds on (2026-10-01): the grant's strict entries, the program runner, the
        # contained optimizer, the setup pins and the image form. A later commit that removed or
        # renamed one would otherwise surface mid-run as an AttributeError.
        needs = {
            "isolation.session_scope": ("SessionScope", "Forbidden", "scope_problem", "host_path_leak"),
            "isolation.sealed_session": ("SealedSession", "SessionDescription", "AnthropicApiProfile", "NO_CREDENTIAL", "UNPINNED"),
            "isolation.program_runner": ("ProgramRunner", "ProgramSpec", "CALL_CONTAINER_PATH"),
            "isolation.pass_outputs": ("Call", "PassStopped"),
            "isolation.contained_agent": ("ContainedOptimizerAgent", "DeclaredOutput", "OPTIMIZER_TOOLS"),
            "isolation.setup_fingerprint": ("setup_fingerprint", "combined_value", "committed_pin", "platform_key"),
            "isolation.image_pin": ("image_ref", "image_ref_problem"),
        }
        for module, symbols in needs.items():
            mod = importlib.import_module(module)
            for symbol in symbols:
                if not hasattr(mod, symbol):
                    return f"the engine's {module} has no {symbol}"
        if "expected_isolation_hash" not in inspect.signature(importlib.import_module("engine.loop").run_loop).parameters:
            return "the engine's run_loop takes no expected_isolation_hash, so a release stamp could not be checked"

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
    checks = [
        ("the pinned engine passes the capability probe", real is None),
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
