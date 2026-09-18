"""paper-trail's side of the container: which host directory holds what, and which hosts it may reach.

Every number this experiment has produced came from an adjudicator session running with ``cwd`` set
to the whole checkout and permissions switched off. In that tree sit the optimizer's own notes on
which claims it got wrong, its hypothesis log, and a file that leads to the gold labels. Across 561
traces nothing was actually read — but "nothing was read" is a measurement, not a guarantee, and it
is the only thing standing behind every result so far.

**Rewritten 2026-09-18 onto the engine's grant.** The boundary machinery landed in
``agentic-label-opt`` at ``592862f``, so four things this module used to own now come from there:
``SessionScope`` (the grant), ``scope_problem`` (its validator), ``host_path_leak`` (the check that
nothing the session is *told* names a host path) and ``HostAllowlistNetworkStack.render_dispatch``
(one container per dispatch on a network stood up once). Deleted here rather than wrapped: ``Mount``,
``StageMounts``, ``stage_mount_set()``, ``inner_command_host_leak()`` and the hand-rolled prefix
factory. What is left is the part that is genuinely paper-trail's — the mount *contents*, the secret
list, the host list, the version-addressed cwd, and two consumer predicates.

**One grant for the program, with no stage dimension** (Phil, 2026-09-17): *"we've decided several
times now that the entire program is one entity in terms of data visibility. While there are 'stages'
nominally, nothing experimentally warrants or benefits from splitting in this way. In fact the
optimizer may freely choose to edit the topology of a program making such divides a nuisance and
unnecessary."* So :func:`program_scope` takes a profile, never a stage, and the uniqueness rule is
**per grant** — two program versions must never render the same command, while two claims under one
version deliberately do, because a grant scopes a worker's whole life and N claims per worker is a
parameter.

⚠ **The adjudicator-and-paper split is gone, and that was the point of the ruling.** The old module
withheld the paper from the adjudicator's mount set. The paper is not a secret — it is the source
document, freely readable; gold is the secret. The reason a judge should not read the whole paper is
that its evidence *is* the retrieved subset, and that subset is the experimental condition being
measured. That is measurement integrity, and it is held by the release pinning ``profile`` and
``retrieval_k``, not by withholding a mount. ⇒ nothing here derives an extractor grant, and
:func:`evidence_source_problem` refuses a profile that would need one rather than quietly handing it
a container with no paper in it.

Three things this module is still deliberately strict about:

* **One path map, used by everything that crosses the boundary.** ``--add-dir``, the workdir, and any
  path interpolated into prompt text resolve through the container constants below. A path that is
  right in argv and stale in the prompt is a dispatch the adjudicator cannot complete, and it reads
  as a model failure rather than a wiring bug. The engine's ``host_path_leak`` is what checks it, and
  because it takes the grant it can tell a leaked path from a legitimately granted one.
* **``denied`` is populated, always.** It renders no Docker flag — a path that is not mounted is
  already unreachable — and exists to be *probed*: the negative control plants a sentinel at each
  entry and every probe must fail to read. The engine refuses a grant with an empty ``denied``
  outright, because "the boundary held" over zero observations is not a finding.
* **No second stage gate.** ``profiles.unrunnable_reason`` already refuses a profile whose stages have
  no command implementation, at preflight, before any spend. :func:`unspecified_stage_problem` points
  at that check rather than duplicating it.

**Not here yet, by intent**: the optimizer's own grant (1e) and the configuration hash that pins the
rendered shape into the manifest's ``runtime_pins`` (Phase 3).

Sister files: ``dispatcher.py:467`` (``val_isolation_problem``) for the ``-> str | None`` problem
idiom these predicates follow; ``adapter.py:711`` (``_stage_command``) for the uncontained argv these
replace; ``engine_pin.py`` for which engine commit is required and what it buys.

Run the dry run — the cheapest gate in the plan, no container, no model, no spend::

    python3 experiments/sarol-2024/optimizer/isolation.py --selftest
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import importlib
import inspect
import os
import pathlib
import sys
import types
from typing import Sequence

_HERE = pathlib.Path(__file__).resolve().parent

if str(_HERE) not in sys.path:  # importable as a script and as a module
    sys.path.insert(0, str(_HERE))

import engine_pin  # noqa: E402
import profiles as profiles_mod  # noqa: E402

#: Repo root: experiments/sarol-2024/optimizer/isolation.py -> up 3. Same derivation as adapter.py.
REPO_ROOT = _HERE.parents[2]

#: Where `agentic-label-opt` is checked out. ⚠ **Re-exported from `engine_pin`, not redefined
#: (2026-09-18)** -- this used to be a third copy of the same literal.
DEFAULT_ENGINE = engine_pin.DEFAULT_ENGINE

#: `scripts/stage_claim.py` owns where the benchmark and gold trees live, including their env-var
#: overrides. Imported rather than re-derived: two copies of `_gold_root()` is exactly the drift
#: `engine_pin` was created to end, and a `denied` entry pointing at the wrong directory is a
#: sentinel planted where nothing will look for it.
_SCRIPTS = REPO_ROOT / "experiments" / "sarol-2024" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import stage_claim  # noqa: E402


def engine_path() -> pathlib.Path:
    """Delegates to :mod:`engine_pin`, the single definition."""
    return engine_pin.engine_path()


@functools.lru_cache(maxsize=1)
def _import_engine() -> types.SimpleNamespace:
    """The engine symbols this module composes. Memoized -- the path dance is paid once.

    Kept in a function, like ``adapter._import_engine``, so this module stays importable on a
    machine with no engine checkout. Nothing real can be built without it: since 2026-09-18 the
    grant type itself is the engine's, so the dry run refuses rather than skipping.

    ⚠ **This module and the engine's package are both called ``isolation``.** With this directory on
    ``sys.path`` a plain ``import isolation.session_scope`` resolves to *this file* and fails with
    "isolation is not a package". So the engine's root goes on the front of the path and this
    directory comes off it for the duration of the import. Same dance as
    ``engine_pin.capability_problem``; worth renaming one of them, but that is a change to a name the
    plan fixed, not a decision to make here.
    """
    # ⚠ Capability-probed, not just pin-checked: this module needs SessionScope, inherit_env and
    # render_dispatch specifically, and ancestry alone would not notice a later commit that removed
    # one.
    path = engine_pin.require_engine(probe_capabilities=True)
    saved_path = list(sys.path)
    # ⚠ **The modules are saved too, and leaving this out was a real bug (found by review,
    # 2026-09-18).** Purging `isolation*` from `sys.modules` is what stops a half-bound sibling from
    # shadowing the engine's package -- but without putting the old entries back, this function
    # leaves `sys.modules["isolation"]` pointing at the ENGINE for the rest of the process. The next
    # `import isolation` anywhere then gets the wrong module, and this file is imported by bare name
    # (`import profiles as profiles_mod` is how every sibling here is imported), so the upcoming
    # adapter wiring would have hit exactly that. Same save/restore shape as
    # `engine_pin.capability_problem`, which had it right; this copied only half the dance.
    saved_modules = {
        k: v for k, v in sys.modules.items()
        if k == "isolation" or k.startswith("isolation.")
    }
    try:
        sys.path[:] = [p for p in sys.path if p and pathlib.Path(p).resolve() != _HERE]
        sys.path.insert(0, str(path))
        for name in list(saved_modules):
            del sys.modules[name]
        scope_mod = importlib.import_module("isolation.session_scope")
        allowlist_mod = importlib.import_module("isolation.network_allowlist")
        docker_mod = importlib.import_module("isolation.docker_prefix")
        return types.SimpleNamespace(
            SessionScope=scope_mod.SessionScope,
            scope_problem=scope_mod.scope_problem,
            scope_render_params=scope_mod.scope_render_params,
            host_path_leak=scope_mod.host_path_leak,
            build_contained_session_prefix=scope_mod.build_contained_session_prefix,
            HostAllowlistNetworkStack=allowlist_mod.HostAllowlistNetworkStack,
            default_workdir=docker_mod._DEFAULT_WORKDIR,
            reserved_mount_points=docker_mod._RESERVED_CONTAINER_MOUNT_POINTS,
        )
    finally:
        # The engine classes stay alive through the namespace returned above, so dropping its
        # modules from the table costs nothing and leaves the name free for its real owner.
        sys.path[:] = saved_path
        for name in [k for k in sys.modules if k == "isolation" or k.startswith("isolation.")]:
            del sys.modules[name]
        sys.modules.update(saved_modules)


# =================================================================================================
# The canonical container path map (1c)
# =================================================================================================

#: The program version being scored: read-only, and also the working directory, since the snapshot is
#: a real checkout and can be the cwd rather than needing a second copy kept in sync (2a).
#:
#: ⚠ **This is the engine's own reserved path, and using it is now correct.** The previous version of
#: this module mounted the snapshot at ``/workspace/snapshot`` to dodge a collision: the engine
#: reserves ``/workspace/program`` and rejects any ``extra_ro_mounts`` target that touches it. The
#: grant removes the problem instead of working around it — ``SessionScope.program`` is a first-class
#: field that renders to ``program_mount``, which is *how* the engine mounts something there. So the
#: sibling path is gone and the default workdir needs no override. A check below asserts this
#: constant still equals the engine's ``_DEFAULT_WORKDIR``, so a change upstream shows up here as a
#: failed dry run rather than a container starting in an empty directory.
CONTAINER_PROGRAM = "/workspace/program"

#: The materialized spec root — the frozen bytes of this program version, which is what
#: ``{{spec_root}}`` points at. Read-only. Separate from the cwd because the materialized tree is
#: chmod'd read-only and its ``.claude/`` symlinks materialize as plain files, so it cannot itself be
#: a working checkout (``adapter.py:654``).
CONTAINER_SPEC = "/workspace/spec"

#: The staging **root** — every claim's staged evidence, and the only writable place the program gets
#: besides its trace.
#:
#: ⚠ **The root, not one claim, and this reversed on 2026-09-16.** A grant scopes a worker's whole
#: life and the number of claims per worker is a parameter; today's one-session-per-claim shape is the
#: N=1 case, not the design. A worker that will be asked about claims A through K is granted the
#: directory holding all of them and each request names an item inside it, which is the shape the
#: transport already assumes — inputs by reference, never inline.
CONTAINER_STAGING = "/workspace/staging"

#: The session transcripts. Writable and mounted because the container is `--rm`, and a contained
#: adjudicator with no trace is a less useful instrument than an uncontained one (1d).
CONTAINER_TRACE = "/workspace/trace"

#: Every container path this module will ever mount. One place, so a reader can see the whole surface.
CONTAINER_PATHS: tuple[str, ...] = (
    CONTAINER_PROGRAM,
    CONTAINER_SPEC,
    CONTAINER_STAGING,
    CONTAINER_TRACE,
)

#: Passed by NAME, never as `KEY=VALUE`. paper-trail authenticates with an env var, so the value in
#: host argv would land in the wrapper's `meta.json` too. ⚠ **This works now** — the engine's
#: `inherit_env` renders `--env NAME` and lets Docker read the value from the host at run time
#: (`docker_prefix.py:603`). Until 2026-09-18 it was owed upstream and nothing was passed at all,
#: which is why the dry run used to assert only that no value leaked.
ENV_ALLOWLIST: tuple[str, ...] = ("CLAUDE_CODE_OAUTH_TOKEN",)

#: The tool surface, as an exact list with a reason per entry, because this layer covers the threats
#: a mount set cannot. `Task` is absent because OQ1 removed the driver session, so the adjudicator is
#: a top-level session with no subagent to spawn — a real narrowing, not a formality. `Bash`,
#: `WebFetch` and `WebSearch` are absent, which is what leaves no per-call decision for a hook to
#: make on this path (the finding behind OQ6).
ALLOWED_TOOLS: tuple[str, ...] = ("Read", "Write")


# =================================================================================================
# Egress (1f)
# =================================================================================================

#: The hosts the program may reach, named explicitly — the 2026-07-20 ruling was that paper-trail's
#: allowlist *"must name Anthropic's API explicitly, not leave it implicit"*.
#:
#: Under `retrieval`, the only runnable profile, the evidence is produced mechanically beforehand, so
#: the adjudicator needs no literature APIs and this is a single host. One permitted destination is
#: about as provable as an egress boundary gets.
#:
#: ⚠ **One host is what the design calls for; whether it is *sufficient* is a live-run question.**
#: `claude -p` also talks to telemetry and error-reporting hosts on some builds. Squid denies those
#: and the session still completes, but the first armed run is what confirms it — the honest state is
#: "designed for one host, not yet observed for one host". Same posture as the engine's own
#: `VERTEX_ALLOWED_HOSTS` docstring takes about the region it never exercised.
EGRESS_ALLOWED_HOSTS: tuple[str, ...] = ("api.anthropic.com",)

#: What the engine calls the unrestricted policy. Named here so a reader of this module does not have
#: to know that `"open"` means "no egress restriction at all" — and so the dry run can assert the
#: shipping path is *not* on it.
UNRESTRICTED_EGRESS = "open"

#: The engine's real deny-all. What the negative control runs on, since the probe must not be able to
#: reach anything at all.
DENY_ALL_EGRESS = "none"


# =================================================================================================
# What must be unreachable (1b)
# =================================================================================================

#: Host paths the program must never read, independent of any particular run. Each is unreachable by
#: **absence** from the grant and proved unreachable by the negative control's sentinel probe.
#:
#: `~/.paper-trail/gold` and `~/.paper-trail/benchmarks` come from `stage_claim`, which owns their
#: env-var overrides — a hardcoded copy here would plant sentinels in a directory nobody reads.
#: The denied paths that are genuinely **secret**, as opposed to merely out of scope.
#:
#: ⚠ **The distinction is not decorative, and a dry-run check found it missing (2026-09-18).** For
#: an output root, granting one subdirectory of a denied tree is the design — the staging root
#: *is* ``<output_root>/staging``, so the container sees the staged evidence and not the scores
#: beside it. For these two there is no such case: no part of the gold labels or the benchmark
#: tree has any business inside the container, descendants included. So they carry the stricter
#: rule, and the dry run asserts each rule where it belongs instead of applying one to both.
SECRET_ROOTS: tuple[pathlib.Path, ...] = (
    stage_claim.GOLD_ROOT.parent,
    stage_claim.BENCH_DIR.parent,
)

FIXED_DENIED_PATHS: tuple[pathlib.Path, ...] = SECRET_ROOTS + (
    _HERE / "findings",
    _HERE / "meta-learnings.md",
    _HERE / "context",
)


def denied_paths(*, output_roots: Sequence[pathlib.Path]) -> tuple[pathlib.Path, ...]:
    """Everything the program must be unable to read, for one run.

    ``output_roots`` are the optimizer's own per-iteration trees — the plan's ``iter/``. They are a
    parameter rather than a constant because they are stated per run, not derived
    (``SarolRunner.output_roots``, C6.9), and because the VAL root in particular *must* lie outside
    the program's readable mounts, which is what ``dispatcher.val_isolation_problem`` checks.

    ⚠ **Required, with no default.** An omitted output root would silently drop the one denied entry
    that holds this run's own scores, and the grant would still validate because the five fixed
    entries keep the list non-empty. A caller must say where the optimizer writes.

    ⚠ Denying an output root while granting its ``staging/`` subdirectory is deliberate and valid: the
    engine refuses a grant whose mount is an *ancestor* of a denied path, and ``<root>/staging`` is a
    descendant. The container sees the staged evidence and not the scores beside it.
    """
    return FIXED_DENIED_PATHS + tuple(pathlib.Path(r) for r in output_roots)


# =================================================================================================
# The grant (1b) — one per program version, no stage dimension
# =================================================================================================


def version_snapshot_dir(
    runs_root: pathlib.Path, run_id: str, version: str
) -> pathlib.Path:
    """The read-only snapshot of one program version — the cwd the session runs in (2a).

    Version-addressed rather than a single ``current`` directory: with one shared directory, round
    5's adjudicator runs in round 1's folder on top of round 1's verdict, which is the contamination
    the per-version path removes.
    """
    return runs_root / run_id / f"program-{version}"


def evidence_source_problem(profile) -> str | None:
    """Would this profile's program read the source paper? Returns a problem, or None.

    The grant has no paper in it, deliberately (see the module docstring). Under ``retrieval`` the
    evidence is produced by ordinary Python beforehand, so no session ever opens a PDF and there is
    nothing to grant. Under ``agentic`` the program extracts evidence *from the source*, so it would
    need a mount this grant does not carry.

    ⚠ **Not a duplicate of the stage gate, and the difference is load-bearing.**
    ``profiles.unrunnable_reason`` refuses ``agentic`` today because its extractor has no *command
    implementation*. That gate opens the day someone writes the command — for a reason that has
    nothing to do with mounts — and the grant would then silently contain no paper, so the extractor
    would fail looking for one and read as a model error. This refusal is keyed on what produces the
    evidence, which is the condition that actually decides whether a paper mount is owed. The two
    disagree on ``paperclip``, which is how you can tell they are different checks.
    """
    profile = profiles_mod.get(profile)
    if profile.evidence_producer == "extractor":
        return (
            f"profile {profile.name!r} produces its evidence from the source paper "
            f"(evidence_producer={profile.evidence_producer!r}), but this grant mounts no paper: "
            "one grant covers the whole program and the paper was left out of it (Phil, "
            "2026-09-17 -- the program is one entity for data visibility, and the evidence "
            "condition is held by the release pinning profile and retrieval_k, not by a mount). "
            "Add a paper root to the grant before running this profile; do not run it with the "
            "grant as it stands, because the session would fail looking for a paper that is not "
            "there and it would read as a model error"
        )
    return None


def program_scope(
    *,
    profile,
    snapshot_dir: pathlib.Path,
    spec_root: pathlib.Path,
    staging_root: pathlib.Path,
    trace_root: pathlib.Path,
    output_roots: Sequence[pathlib.Path],
):
    """The program's grant: one :class:`SessionScope` for one program version.

    ⚠ **No ``stage`` parameter, and that absence is the design.** Phil struck the per-stage split on
    2026-09-17; the engine's grant has no stage dimension to put one in either way. The dispatch
    *command* still carries a stage (``adapter._stage_command``); the *grant* does not.

    Raises:
        ValueError: the profile would need a paper mount this grant does not carry
            (:func:`evidence_source_problem`), or the engine refuses the grant
            (``session_scope.scope_problem`` — an empty ``denied``, a denied path reachable through a
            granted mount, a reserved-path collision, a duplicate target, a bad workdir).
    """
    problem = evidence_source_problem(profile)
    if problem is not None:
        raise ValueError(problem)

    engine = _import_engine()
    scope = engine.SessionScope(
        program=pathlib.Path(snapshot_dir),
        readable=((pathlib.Path(spec_root), CONTAINER_SPEC),),
        writable=(
            (pathlib.Path(staging_root), CONTAINER_STAGING),
            (pathlib.Path(trace_root), CONTAINER_TRACE),
        ),
        workdir=CONTAINER_PROGRAM,
        denied=denied_paths(output_roots=output_roots),
    )
    # Validated here rather than at render time: a grant that is only checked when it is rendered is
    # a grant a caller can hold and pass around in an invalid state.
    refusal = engine.scope_problem(scope)
    if refusal is not None:
        raise ValueError(f"refusing this program grant: {refusal}")
    return scope


def add_dirs(scope) -> tuple[str, ...]:
    """The ``--add-dir`` list: every granted container path except the one that is already the cwd.

    Derived from the grant rather than listed beside it, so the two cannot disagree. ``--add-dir`` is
    what tells the session it may read outside its working directory; the mount set is what makes that
    true. A path in one and not the other is the failure this derivation removes.
    """
    granted = [container for _host, container in (*scope.readable, *scope.writable)]
    return tuple(c for c in granted if c != scope.workdir)


# =================================================================================================
# Predicates — the `-> str | None` problem idiom, after `dispatcher.val_isolation_problem`
# =================================================================================================


def unspecified_stage_problem(profile) -> str | None:
    """Would this profile dispatch a stage with no implementation? Delegates, by design.

    ``profiles.unrunnable_reason`` already refuses this at preflight, before any spend, and
    ``DEFAULT_PROFILE`` is itself an unrunnable three-stage profile so the check fires in practice
    today. The requirement the container work carries is therefore **negative**: do not bypass or
    relocate that check. This wrapper exists so a caller reaching for a stage gate finds the existing
    one instead of writing a second.
    """
    return profiles_mod.unrunnable_reason(profile)


def bypass_flag_problem(inner_command: list[str]) -> str | None:
    """Is the permission bypass still on this path? Returns a problem, or None.

    The flag is passed in two places and only one of them is ours: ``_stage_command`` builds it into
    the program's own argv (``adapter.py:714``), which is a local edit with no upstream dependency.
    The other is the shared wrapper on the *optimizer's* path. An implementer who changes only the
    wrapper leaves the program on bypass while the diff looks like the fix, so this asserts on the
    argv the Runner actually builds.
    """
    if "--dangerously-skip-permissions" in inner_command:
        return (
            "the shipping argv still carries --dangerously-skip-permissions; inside a mount "
            "boundary that is strictly worse than deny-by-default and it is ours to remove"
        )
    return None


def told_host_path_problem(told, scope) -> str | None:
    """Does what the session is told name a host path from its own grant? Delegates to the engine.

    ``isolation.session_scope.host_path_leak`` replaced this module's ``inner_command_host_leak`` on
    2026-09-18. The engine's version is strictly better in two ways worth knowing: it takes the
    **grant**, so it can tell a leaked path from a legitimately granted one, and it compares by path
    component rather than by substring — the old marker list (``/Users/``, ``/home/``, ...) both
    cried wolf on sibling paths and missed equivalent spellings.

    ⚠ Never hand this the whole ``docker run`` line. The host side of every bind mount is a host path
    necessarily, so a scan over the full command is either vacuous or unsatisfiable. The surface that
    matters is what the session reads: its prompt and its own argv.
    """
    return _import_engine().host_path_leak(told, scope)


# =================================================================================================
# The dispatch (1c) — one container per dispatch
# =================================================================================================


def inner_command(
    *,
    scope,
    prompt: str,
    model: str,
    max_budget_usd: float,
) -> list[str]:
    """The ``claude`` invocation, in container paths only.

    Since OQ1 this is the adjudicator's own invocation rather than a slash command a driver session
    runs: the prompt arrives fully rendered on argv, so there is no second session, no ``Task``, and
    the container boundary and the session boundary are the same boundary.
    """
    cmd = [
        "claude",
        "--print",
        # Deny-by-default in place of bypass-everything. `none` is claude's "anything that would
        # prompt is denied automatically".
        "--permission-prompts",
        "none",
        "--permission-mode",
        "default",
        "--allowedTools",
        ",".join(ALLOWED_TOOLS),
    ]
    for add_dir in add_dirs(scope):
        cmd += ["--add-dir", add_dir]
    cmd += [
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--max-budget-usd",
        str(max_budget_usd),
        prompt,
    ]
    return cmd


def allowlist_stack(
    *,
    scope,
    image: str,
    hosts: Sequence[str] = EGRESS_ALLOWED_HOSTS,
    run_id: str | None = None,
    container_user: str | None = None,
):
    """The egress boundary, stood up once per run. Construction is pure — nothing starts here.

    The Docker network and the Squid sidecar are created in ``__enter__`` and torn down in
    ``close()``; use it as a context manager around the dispatch loop and render each dispatch with
    :func:`allowlist_dispatch_prefix`.

    ⚠ **One stack, many dispatches — this is what made an allowlist affordable.** The stack fixes its
    own ``cmd_prefix`` in ``__init__`` from a single mount set, so before ``render_dispatch`` existed
    the only way to give a second dispatch a different mount set was a second stack, and a second
    stack means a second Squid sidecar. At 561 dispatches that is not a boundary anyone keeps, which
    is exactly why this code ran on the unrestricted ``"open"`` policy as a recorded stand-in until
    2026-09-18.

    ⚠ **No ``adc_path`` parameter anywhere on this path, and that is the point.** On the plain-policy
    path the argument defaults to a *real* credential file, so omitting it is what grants a Google
    credential; here there is nothing to omit.

    **Lifecycle, stated because the wiring's first question is where this goes** (asked by review,
    2026-09-18; answered from the engine's own design rather than left open):

    * **One stack per RUN** — not per grant, not per claim. It serves every program version the run
      scores: pass the run's first grant here, then render each later grant through
      :func:`allowlist_dispatch_prefix`. A stack per program version would work but wastes a sidecar
      per version and, in a test fixture, silently makes two grants look distinct when only their
      network name differed.
    * **So it belongs at the batch level, above ``SarolRunner.process``**, which is per-claim. The
      ``with`` block has to outlive every dispatch in the batch, because ``close()`` destroys the
      network those commands name.
    * **Safe to share across workers.** Rendering is pure and touches no Docker resource, so
      ``max_workers > 1`` may render concurrently onto one entered stack. What is *not* safe is
      entering or closing it from a worker.
    """
    engine = _import_engine()
    refusal = engine.scope_problem(scope)
    if refusal is not None:
        raise ValueError(f"refusing to stand up an egress boundary for this grant: {refusal}")
    kwargs = dict(
        allowed_hosts=tuple(hosts),
        image_tag=image,
        edit_agent_mounts=None,
        inherit_env=ENV_ALLOWLIST,
        **engine.scope_render_params(scope),
    )
    if run_id is not None:
        kwargs["run_id"] = run_id
    if container_user is not None:
        kwargs["container_user"] = container_user
    return engine.HostAllowlistNetworkStack(**kwargs)


def allowlist_dispatch_prefix(*, scope, stack, render=None) -> list[str]:
    """One dispatch's docker prefix, on the standing allowlist network. The shipping path.

    ``render`` is injectable so the dry run can record what the stack was asked for while still
    calling the real renderer (OQ7: an injected recorder, not an opt-out flag — there is no
    production-reachable branch here that disables the boundary).
    """
    engine = _import_engine()
    refusal = engine.scope_problem(scope)
    if refusal is not None:
        raise ValueError(f"refusing to render this grant: {refusal}")
    dispatch = render or stack.render_dispatch
    return dispatch(
        edit_agent_mounts=None,
        inherit_env=ENV_ALLOWLIST,
        **engine.scope_render_params(scope),
    )


def dispatch_prefix(
    *,
    scope,
    image: str,
    network_policy: str,
    container_user: str | None = None,
    render=None,
) -> list[str]:
    """One dispatch's docker prefix on a plain network policy, straight through the engine's grant.

    Kept beside :func:`allowlist_dispatch_prefix` for the two cases an allowlist cannot serve: the
    negative control, which runs on a real deny-all (``"none"``) so the probe can reach nothing at
    all, and the recorded ``"open"`` stand-in this path ran on before the allowlist became
    affordable.

    ``network_policy`` is required. Nothing here defaults to unrestricted — ``"open"`` is plain bridge
    networking that the engine itself files under ``_UNRESTRICTED_NETWORK_POLICIES`` and describes as
    sealing nothing on the network axis, so a caller has to choose it out loud.

    ⚠ ``adc_path=None`` is passed **explicitly**. The engine's default is a real credential path, so
    *omitting* this argument is what grants the credential, not what withholds it. It is also honoured
    only on ``"open"``; under ``"vertex-only"`` an explicit ``None`` is silently coerced back to the
    default.
    """
    engine = _import_engine()
    build = render or engine.build_contained_session_prefix
    return build(
        scope=scope,
        network_policy=network_policy,
        image_tag=image,
        adc_path=None,
        edit_agent_mounts=None,
        inherit_env=ENV_ALLOWLIST,
        container_user=container_user,
    )


# =================================================================================================
# Step 0a — the free dry run. No container started, no model called, nothing spent.
# =================================================================================================

#: A digest-pinned image, so the dry run asserts the shape production must use.
_DRY_IMAGE = "ghcr.io/example/paper-trail@sha256:" + "0" * 64


def _dry_paths(version: str) -> dict:
    """Fabricated, self-consistent host paths for one program version. Nothing is created on disk."""
    runs_root = REPO_ROOT / "runs"
    train_root = runs_root / "run_dry" / "train"
    val_root = runs_root / "run_dry" / "val"
    return {
        "snapshot_dir": version_snapshot_dir(runs_root, "run_dry", version),
        "spec_root": runs_root / "run_dry" / "materialized" / version,
        "staging_root": train_root / "staging",
        "trace_root": runs_root / "run_dry" / "traces",
        "output_roots": (train_root, val_root),
    }


def _dry_run_matrix(*, dispatch_render=None, plain_render=None):
    """Build every grant and render every dispatch. Returns rows, grants and refusals.

    The dimensions are what the ruling left: a **grant** per program version, and a **dispatch** per
    claim inside it. No stage anywhere.
    """
    versions = ["v0", "v1"]
    claims = ["C001", "C002"]

    rows: list[dict] = []
    grants: list[dict] = []
    refusals: list[dict] = []

    for profile in (profiles_mod.RETRIEVAL, profiles_mod.AGENTIC, profiles_mod.PAPERCLIP):
        stage_refusal = unspecified_stage_problem(profile.name)
        evidence_refusal = evidence_source_problem(profile.name)
        if stage_refusal or evidence_refusal:
            refusals.append(
                {
                    "profile": profile.name,
                    "stage_refusal": stage_refusal,
                    "evidence_refusal": evidence_refusal,
                }
            )
            continue
        scopes = [
            (version, program_scope(profile=profile.name, **_dry_paths(version)))
            for version in versions
        ]
        # ⚠ **One stack for every grant, and the first draft got this wrong.** It stood up a stack
        # per version, which gave each version a different Docker network name -- so the per-grant
        # uniqueness check below passed on the network name and would have passed even if the
        # program mount never moved. Found by review, 2026-09-18. One standing network rendering
        # many grants is also the lifecycle the engine was built for ("stand the boundary up once,
        # render many dispatches onto it"), so the honest fixture and the real shape are the same
        # thing.
        stack = allowlist_stack(scope=scopes[0][1], image=_DRY_IMAGE, run_id="dry")
        for version, scope in scopes:
            prefix = allowlist_dispatch_prefix(
                scope=scope, stack=stack, render=dispatch_render and dispatch_render(stack)
            )
            plain = dispatch_prefix(
                scope=scope,
                image=_DRY_IMAGE,
                network_policy=DENY_ALL_EGRESS,
                render=plain_render,
            )
            grants.append(
                {
                    "profile": profile.name,
                    "version": version,
                    "scope": scope,
                    "stack": stack,
                    "prefix": prefix,
                    "plain": plain,
                }
            )
            for claim in claims:
                prompt = (
                    f"Adjudicate {claim} using the evidence envelope at "
                    f"{CONTAINER_STAGING}/{claim}/ledger/evidence.json "
                    f"and the rubric under {CONTAINER_PROGRAM}."
                )
                inner = inner_command(
                    scope=scope, prompt=prompt, model="haiku", max_budget_usd=0.5
                )
                rows.append(
                    {
                        "profile": profile.name,
                        "version": version,
                        "claim": claim,
                        "scope": scope,
                        "prompt": prompt,
                        "prefix": prefix,
                        "inner": inner,
                        "full": list(prefix) + inner,
                    }
                )
    return rows, grants, refusals


def rendered_mounts(argv) -> tuple[tuple[str, str, str], ...]:
    """Every bind mount in a rendered docker argv, as ``(host, container, mode)`` triples.

    ⚠ **Parses the argv rather than reading the grant back, and that distinction is the whole
    point.** V2a-seal is a statement about what the container actually receives, so a check that
    inspects ``scope.readable`` proves only that we asked correctly — it cannot see a renderer that
    dropped a mount or added one. Added after review found every mount assertion here was
    grant-side (2026-09-18).

    Split from the right so a host path containing a colon still parses: Docker's own spec is
    ``host:container[:mode]`` and only the last two fields are fixed-width.
    """
    args = [str(a) for a in argv]
    mounts: list[tuple[str, str, str]] = []
    for index, arg in enumerate(args):
        if arg != "-v" or index + 1 >= len(args):
            continue
        parts = args[index + 1].split(":")
        if len(parts) >= 3:
            mounts.append((":".join(parts[:-2]), parts[-2], parts[-1]))
        elif len(parts) == 2:
            mounts.append((parts[0], parts[1], "rw"))
    return tuple(mounts)


def _expected_mounts(scope) -> tuple[tuple[str, str, str], ...]:
    """The triples a grant should render to. Compared against :func:`rendered_mounts`, sorted."""
    return tuple(
        sorted(
            [(str(scope.program), CONTAINER_PROGRAM, "ro")]
            + [(str(h), c, "ro") for h, c in scope.readable]
            + [(str(h), c, "rw") for h, c in scope.writable]
        )
    )


def _path_at_or_above(one, other) -> bool:
    """Is ``one`` the same path as ``other``, or an ancestor of it?

    The engine's own rule for a granted mount against a denied path: an ancestor hands the denied
    path over inside a tree the session was granted. Not symmetric -- see :data:`SECRET_ROOTS` for
    why a granted *descendant* of a denied tree is legitimate and is in fact how the staging root
    works.
    """
    a = pathlib.PurePosixPath(os.path.normpath(str(one)))
    b = pathlib.PurePosixPath(os.path.normpath(str(other)))
    return a == b or a in b.parents


def _paths_overlap(one, other) -> bool:
    """Do two host paths overlap — equal, or either one inside the other?

    Both directions matter. A mount that is an *ancestor* of a denied path hands the denied path
    over inside a granted tree; a mount that sits *inside* one is a slice of the secret itself.
    Normalized lexically, like the engine's own comparison, so ``/srv/gold/..`` cannot slip through
    as a string that matches nothing.
    """
    a = pathlib.PurePosixPath(os.path.normpath(str(one)))
    b = pathlib.PurePosixPath(os.path.normpath(str(other)))
    return a == b or a in b.parents or b in a.parents


def _recording_dispatch(calls: list[dict]):
    """Record what a stack was asked to render, then let the real renderer render it.

    Deliberately not a fake: a stand-in renderer can agree with us about the keywords and still hide
    a grant the engine would refuse. Recording around the real call asserts both.
    """

    def factory(stack):
        def render(**kw):
            calls.append(kw)
            return stack.render_dispatch(**kw)

        return render

    return factory


def _recording_plain(calls: list[dict]):
    def render(**kw):
        calls.append(kw)
        return _import_engine().build_contained_session_prefix(**kw)

    return render


def _replaced(scope, **fields):
    """One field of a grant changed, for the negative controls. The grant is frozen on purpose."""
    return dataclasses.replace(scope, **fields)


def _raises(fn, *, want: str | None = None) -> bool:
    """Did ``fn`` refuse with a ``ValueError``, optionally one whose message contains ``want``?"""
    try:
        fn()
    except ValueError as exc:
        return want is None or want in str(exc)
    except Exception:
        return False
    return False


def _selftest() -> int:
    engine = _import_engine()  # refuses here if the engine is missing or misses a capability
    dispatch_calls: list[dict] = []
    plain_calls: list[dict] = []
    rows, grants, refusals = _dry_run_matrix(
        dispatch_render=_recording_dispatch(dispatch_calls),
        plain_render=_recording_plain(plain_calls),
    )

    a_scope = grants[0]["scope"]
    a_stack = grants[0]["stack"]
    dry = _dry_paths("v0")

    checks: list[tuple[str, bool]] = [
        # -- the matrix itself ---------------------------------------------------------------------
        (
            "every profile is either granted or refused, none silently skipped",
            len({g["profile"] for g in grants}) + len({r["profile"] for r in refusals}) == 3
            and all(r["stage_refusal"] or r["evidence_refusal"] for r in refusals),
        ),
        (
            "the rendered matrix is 2 grants (one per program version) and 4 dispatches",
            len(grants) == 2 and len(rows) == 4,
        ),
        (
            "...and the two profiles that cannot run are refused by name",
            {r["profile"] for r in refusals} == {"agentic", "paperclip"},
        ),
        # -- the struck design is gone, not merely unused -------------------------------------------
        (
            "no stage-keyed mount vocabulary survives in this module",
            not any(
                hasattr(sys.modules[__name__], name)
                for name in ("Mount", "StageMounts", "stage_mount_set", "inner_command_host_leak")
            ),
        ),
        # ⚠ The four names above are a tripwire for the old code and nothing more -- a renamed
        # stage-keyed helper would walk straight past them (review, 2026-09-18). This is the
        # structural version: whatever anything here is called, nothing in this module may take a
        # stage.
        (
            "...and no function in this module takes a stage, whatever it might be called",
            not [
                name
                for name, obj in vars(sys.modules[__name__]).items()
                if inspect.isfunction(obj)
                and obj.__module__ == __name__
                and "stage" in inspect.signature(obj).parameters
            ],
        ),
        (
            "the grant takes a profile and never a stage, and carries no paper",
            "stage" not in inspect.signature(program_scope).parameters
            and not any(
                "paper" in p for p in inspect.signature(program_scope).parameters
            ),
        ),
        (
            "the container path map has no paper entry left in it",
            not any("paper" in p for p in CONTAINER_PATHS),
        ),
        # -- per-GRANT uniqueness, which replaced per-(stage, claim, version) -----------------------
        # ⚠ The rule inverted on 2026-09-16. A grant scopes a worker's whole life, so reuse across
        # claims *within* one grant is the design; what must never collide is the command of two
        # different grants. At N=1 the correct and the incorrect rule are indistinguishable, which is
        # exactly how a wrong gate here would pass unnoticed and mis-attribute results once N moves.
        (
            "two different grants never render the same command",
            len({tuple(g["prefix"]) for g in grants}) == len(grants),
        ),
        # ⚠ **And the network name cannot be what makes them distinct.** Review pointed out that the
        # first fixture stood up a stack per version, so two commands differed by Docker network
        # even when the mount set was identical -- the check would have certified uniqueness that
        # the grant did not provide. Every grant now renders onto ONE standing network, so the only
        # thing left to distinguish two commands is what they mount, which is the property the rule
        # is about.
        (
            "...and every grant renders onto the SAME network, so only the mounts can distinguish",
            len({g["stack"].internal_network_name for g in grants}) == 1,
        ),
        (
            "...while two claims under one grant share it, which is the design under N>1",
            len({tuple(r["prefix"]) for r in rows}) == 2 and len(rows) == 4,
        ),
        (
            "...because the program mount moves with the version and nothing else does",
            len({g["scope"].program for g in grants}) == 2
            and len({g["scope"].writable for g in grants}) == 1,
        ),
        (
            "...so a v0 dispatch never points at v1's bytes",
            all(g["version"] in str(g["scope"].program) for g in grants),
        ),
        (
            "the inner command varies per claim, since the claim is named inside the mounted root",
            len({tuple(r["inner"]) for r in rows}) == len({r["claim"] for r in rows}),
        ),
        # ⚠ Found by this check failing on the first run of the rewrite, and the check was what was
        # wrong. The version is carried by WHAT IS MOUNTED at /workspace/program, never by anything
        # the session is told -- so two versions of one claim are byte-identical commands over
        # different bytes. That is the property that makes a version swap invisible to the program,
        # which is the whole point of a version-addressed cwd; asserting 4 distinct commands for 4
        # dispatches would have demanded the opposite.
        (
            "...and is identical across program versions, because the version lives in the mount",
            all(
                len(
                    {
                        tuple(r["inner"])
                        for r in rows
                        if r["claim"] == claim
                    }
                )
                == 1
                for claim in {r["claim"] for r in rows}
            ),
        ),
        # -- denied: the load-bearing field --------------------------------------------------------
        (
            "every grant denies something, so the negative control has something to probe",
            all(g["scope"].denied for g in grants),
        ),
        (
            "...and what it denies includes gold, the benchmark tree and the optimizer's own outputs",
            all(
                stage_claim.GOLD_ROOT.parent in g["scope"].denied
                and stage_claim.BENCH_DIR.parent in g["scope"].denied
                and dry["output_roots"][1] in g["scope"].denied
                for g in grants
            ),
        ),
        (
            "...and the engine accepts every grant as rendered",
            all(engine.scope_problem(g["scope"]) is None for g in grants),
        ),
        (
            "an empty denied list is refused -- a grant with no proof",
            engine.scope_problem(_replaced(a_scope, denied=())) is not None,
        ),
        (
            "...and so is a grant whose readable mount is an ancestor of a denied path",
            engine.scope_problem(
                _replaced(a_scope, readable=((stage_claim.GOLD_ROOT.parent.parent, CONTAINER_SPEC),))
            )
            is not None,
        ),
        (
            "...which is why granting the repo root is refused outright",
            _raises(
                lambda: program_scope(profile="retrieval", **{**dry, "spec_root": REPO_ROOT}),
                want="is reachable through",
            ),
        ),
        # -- nothing the session is told names a host path -----------------------------------------
        (
            "nothing any session is told names a host path from its own grant",
            all(
                told_host_path_problem(r["inner"], r["scope"]) is None for r in rows
            )
            and all(told_host_path_problem(r["prompt"], r["scope"]) is None for r in rows),
        ),
        (
            "...and the check is not vacuous: a granted host path in the prompt is caught",
            told_host_path_problem(
                f"read {dry['staging_root']}/C001/evidence.json", a_scope
            )
            is not None,
        ),
        (
            "...nor is a denied host path missed",
            told_host_path_problem(f"read {stage_claim.GOLD_ROOT}/test", a_scope) is not None,
        ),
        (
            "...while the container-side path is not flagged",
            told_host_path_problem(f"read {CONTAINER_STAGING}/C001/evidence.json", a_scope)
            is None,
        ),
        # -- the container path map ----------------------------------------------------------------
        (
            "every mount's container side comes from the path map",
            all(
                {c for _h, c in (*g["scope"].readable, *g["scope"].writable)}
                <= set(CONTAINER_PATHS)
                for g in grants
            ),
        ),
        (
            "the workdir is the program snapshot, and it is the engine's own default",
            all(g["scope"].workdir == CONTAINER_PROGRAM for g in grants)
            and CONTAINER_PROGRAM == engine.default_workdir,
        ),
        (
            "every --add-dir is a granted container path, and the cwd is not among them",
            all(
                set(add_dirs(g["scope"])) <= set(CONTAINER_PATHS)
                and CONTAINER_PROGRAM not in add_dirs(g["scope"])
                and set(add_dirs(g["scope"]))
                == {c for _h, c in (*g["scope"].readable, *g["scope"].writable)}
                for g in grants
            ),
        ),
        # -- the tool surface ----------------------------------------------------------------------
        (
            "Task is absent from every allowlist, since OQ1 removed the subagent",
            "Task" not in ALLOWED_TOOLS and all("Task" not in r["inner"] for r in rows),
        ),
        (
            "Bash, WebFetch and WebSearch are absent too",
            not ({"Bash", "WebFetch", "WebSearch"} & set(ALLOWED_TOOLS)),
        ),
        (
            "no shipping argv carries --dangerously-skip-permissions",
            all(bypass_flag_problem(r["inner"]) is None for r in rows),
        ),
        (
            "...and that check is not vacuous either",
            bypass_flag_problem(["claude", "--dangerously-skip-permissions"]) is not None,
        ),
        (
            "deny-by-default is what replaced it",
            all(
                "--permission-prompts" in r["inner"]
                and r["inner"][r["inner"].index("--permission-prompts") + 1] == "none"
                for r in rows
            ),
        ),
        # -- evidence from the source has no mount here, and says so -------------------------------
        (
            "a profile that would read the source paper is refused, naming what the grant owes",
            _raises(
                lambda: program_scope(profile="agentic", **dry), want="mounts no paper"
            ),
        ),
        (
            "...while the mechanical profile is not refused by it",
            evidence_source_problem("retrieval") is None,
        ),
        (
            "...and this is a different check from the stage gate, which the two disagreeing shows",
            evidence_source_problem("paperclip") is None
            and unspecified_stage_problem("paperclip") is not None,
        ),
        (
            "the unspecified-stage refusal is still profiles.unrunnable_reason, not a second gate",
            unspecified_stage_problem("agentic") == profiles_mod.unrunnable_reason("agentic"),
        ),
        (
            "the default profile is still refused at preflight, and names its missing stages",
            (lambda r: r is not None and "extractor" in r and "verifier" in r)(
                unspecified_stage_problem(profiles_mod.DEFAULT_PROFILE)
            ),
        ),
        # -- egress --------------------------------------------------------------------------------
        (
            "the shipping dispatch renders onto a host allowlist, not the unrestricted policy",
            bool(dispatch_calls)
            and all(g["stack"].allowed_hosts == EGRESS_ALLOWED_HOSTS for g in grants)
            and all(
                UNRESTRICTED_EGRESS not in [str(a) for a in g["prefix"]] for g in grants
            ),
        ),
        (
            "...and the allowlist names Anthropic's API explicitly, with no wildcard in it",
            EGRESS_ALLOWED_HOSTS == ("api.anthropic.com",)
            and not any("*" in h for h in EGRESS_ALLOWED_HOSTS),
        ),
        (
            "...and the rendered argv joins the stack's own internal network, not a bridge",
            all(
                f"--network={g['stack'].internal_network_name}" in [str(a) for a in g["prefix"]]
                or g["stack"].internal_network_name in [str(a) for a in g["prefix"]]
                for g in grants
            ),
        ),
        (
            "an allowlist with no hosts is refused -- an empty ACL denies everything",
            _raises(lambda: allowlist_stack(scope=a_scope, image=_DRY_IMAGE, hosts=())),
        ),
        (
            "the plain-policy path still makes the caller state a policy; nothing defaults to open",
            inspect.signature(dispatch_prefix).parameters["network_policy"].default
            is inspect.Parameter.empty,
        ),
        (
            "...and the plain path the negative control uses is the engine's real deny-all",
            DENY_ALL_EGRESS == "none"
            and bool(plain_calls)
            and all(c["network_policy"] == DENY_ALL_EGRESS for c in plain_calls),
        ),
        # -- what we asked the engine for ----------------------------------------------------------
        (
            "the allowlist path takes no adc_path at all, so there is no credential to withhold",
            "adc_path" not in inspect.signature(allowlist_stack).parameters
            and "adc_path" not in inspect.signature(allowlist_dispatch_prefix).parameters
            and all("adc_path" not in c for c in dispatch_calls),
        ),
        (
            "...and the plain path passes adc_path=None explicitly, since omitting it grants one",
            all("adc_path" in c and c["adc_path"] is None for c in plain_calls),
        ),
        (
            "every render declares no editing agent on the program's path",
            all(c.get("edit_agent_mounts") is None for c in dispatch_calls + plain_calls),
        ),
        (
            "the image is pinned by digest, not by tag",
            "@sha256:" in _DRY_IMAGE
            and all("@sha256:" in str(c["image_tag"]) for c in plain_calls),
        ),
        (
            "the token is requested by name on every render",
            all(
                tuple(c["inherit_env"]) == ENV_ALLOWLIST
                for c in dispatch_calls + plain_calls
            ),
        ),
        (
            "...and it reaches the rendered argv as a bare --env NAME",
            all(
                "CLAUDE_CODE_OAUTH_TOKEN" in [str(a) for a in g["prefix"]] for g in grants
            ),
        ),
        (
            "...with no value beside it, on any rendered command",
            all(
                "CLAUDE_CODE_OAUTH_TOKEN=" not in str(a)
                for r in rows
                for a in r["full"]
            )
            and all(
                "CLAUDE_CODE_OAUTH_TOKEN=" not in str(a) for g in grants for a in g["plain"]
            ),
        ),
        (
            "...and no environment value of any kind is passed through as KEY=VALUE by us",
            all(not c.get("env") for c in dispatch_calls + plain_calls),
        ),
        # -- against the real engine renderer ------------------------------------------------------
        (
            "the engine's argv starts a container and nothing else ran to find out",
            all(g["prefix"][:2] == ["docker", "run"] for g in grants),
        ),
        (
            "the rendered argv mounts exactly the four granted paths, in the right modes, no extras",
            all(
                tuple(sorted(rendered_mounts(g["prefix"]))) == _expected_mounts(g["scope"])
                for g in grants
            ),
        ),
        (
            "...and the plain-policy render agrees with it mount for mount",
            all(
                tuple(sorted(rendered_mounts(g["plain"]))) == _expected_mounts(g["scope"])
                for g in grants
            ),
        ),
        (
            "...and that comparison is not vacuous: an extra mount in the argv is caught",
            tuple(sorted(rendered_mounts(list(grants[0]["prefix"]) + ["-v", "/etc:/workspace/x:ro"])))
            != _expected_mounts(grants[0]["scope"]),
        ),
        (
            "the program is read-only and only staging and trace are writable",
            all(
                {c for _h, c, mode in rendered_mounts(g["prefix"]) if mode == "rw"}
                == {CONTAINER_STAGING, CONTAINER_TRACE}
                and (str(g["scope"].program), CONTAINER_PROGRAM, "ro")
                in rendered_mounts(g["prefix"])
                for g in grants
            ),
        ),
        (
            "no rendered mount lands on a path the engine reserves for its own use",
            all(
                c not in engine.reserved_mount_points
                for g in grants
                for _h, c in (*g["scope"].readable, *g["scope"].writable)
            ),
        ),
        # ⚠ This used to search the rendered argv for the `sarol-2024` child paths, which is
        # weaker than its own label: a mount of the PARENT `~/.paper-trail/gold` contains neither
        # string and would have passed (review, 2026-09-18). Now every rendered mount is compared
        # against every denied root, in both directions -- a mount that is an ancestor of a denied
        # path hands it over inside a granted tree, and one that sits inside a denied path is a
        # slice of the secret itself.
        (
            "no rendered mount is, or is an ancestor of, anything the grant denies",
            not [
                (host, denied)
                for g in grants
                for host, _c, _m in rendered_mounts(g["prefix"]) + rendered_mounts(g["plain"])
                for denied in g["scope"].denied
                if _path_at_or_above(host, denied)
            ],
        ),
        (
            "...and no part of gold or the benchmark tree is mounted at all, descendants included",
            not [
                (host, secret)
                for g in grants
                for host, _c, _m in rendered_mounts(g["prefix"]) + rendered_mounts(g["plain"])
                for secret in SECRET_ROOTS
                if _paths_overlap(host, secret)
            ],
        ),
        # ⚠ The two rules above differ on purpose, and asserting one of them for both is what the
        # first draft of this check did -- it failed, correctly, on the staging mount. `denied`
        # holds each output root while the staging root granted to the container IS
        # `<output_root>/staging`, so a granted DESCENDANT of a denied tree is the design there.
        # For a secret root it is not. Asserted rather than left in prose:
        (
            "...and the two rules really do differ, which the staging mount is the live case of",
            all(
                any(
                    _paths_overlap(host, denied) and not _path_at_or_above(host, denied)
                    for host, container, _m in rendered_mounts(g["prefix"])
                    if container == CONTAINER_STAGING
                    for denied in g["scope"].denied
                )
                for g in grants
            ),
        ),
        (
            "...and that check is not vacuous: a mount of the gold root's parent is caught",
            _paths_overlap(stage_claim.GOLD_ROOT.parent.parent, stage_claim.GOLD_ROOT)
            and _paths_overlap(stage_claim.GOLD_ROOT / "test" / "labels.csv", stage_claim.GOLD_ROOT)
            and not _paths_overlap(
                stage_claim.GOLD_ROOT.parent / "gold2", stage_claim.GOLD_ROOT
            ),
        ),
    ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="Step 0a: build every grant, render every dispatch, assert on the argv. No container.",
    )
    ap.add_argument(
        "--print-matrix",
        action="store_true",
        help="Print the rendered command for every dispatch, for reading by eye.",
    )
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.print_matrix:
        rows, grants, refusals = _dry_run_matrix()
        for r in rows:
            print(f"\n=== {r['profile']} / {r['version']} / {r['claim']} ===")
            print(" ".join(str(a) for a in r["full"]))
        for g in grants:
            print(f"\n=== grant {g['profile']} / {g['version']} denies ===")
            for path in g["scope"].denied:
                print(f"    {path}")
        for r in refusals:
            print(f"\n=== {r['profile']} === REFUSED")
            for label in ("stage_refusal", "evidence_refusal"):
                if r[label]:
                    print(f"    {label}: {r[label]}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
