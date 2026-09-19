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
idiom these predicates follow; ``adapter.SarolRunner._inner_command`` for the caller that builds
every dispatch through them; ``engine_pin.py`` for which engine commit is required and what it buys.

Run the dry run — the cheapest gate in the plan, no container, no model, no spend::

    python3 experiments/sarol-2024/optimizer/isolation.py --selftest
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import functools
import hashlib
import importlib
import inspect
import json
import os
import pathlib
import re
import subprocess
import sys
import types
from typing import Any, Sequence

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
    with engine_importable():
        scope_mod = importlib.import_module("isolation.session_scope")
        allowlist_mod = importlib.import_module("isolation.network_allowlist")
        docker_mod = importlib.import_module("isolation.docker_prefix")
        # The seal control's generic half (1g). Imported HERE rather than in `seal_control.py`
        # because the name-collision dance is the thing not to have two copies of.
        control_mod = importlib.import_module("isolation.negative_control")
        return types.SimpleNamespace(
            SessionScope=scope_mod.SessionScope,
            scope_problem=scope_mod.scope_problem,
            scope_render_params=scope_mod.scope_render_params,
            host_path_leak=scope_mod.host_path_leak,
            build_contained_session_prefix=scope_mod.build_contained_session_prefix,
            HostAllowlistNetworkStack=allowlist_mod.HostAllowlistNetworkStack,
            default_workdir=docker_mod._DEFAULT_WORKDIR,
            reserved_mount_points=docker_mod._RESERVED_CONTAINER_MOUNT_POINTS,
            build_contained_scenario=control_mod.build_contained_scenario,
            run_contained_probe=control_mod.run_contained_probe,
            mount_set_problem=control_mod.mount_set_problem,
            probe_path_for=control_mod.probe_path_for,
            docker_available=control_mod.docker_available,
            default_image_tag=control_mod.IMAGE_TAG,
        )


@contextlib.contextmanager
def engine_importable():
    """Hold the engine's ``isolation`` package importable for the duration of a block.

    ⚠ **Several engine entry points defer their own relative imports to CALL time**, and that makes
    this a context manager rather than a one-shot. ``negative_control.build_contained_scenario``
    runs ``from .session_scope import ...`` *inside* the function; by then :func:`_import_engine`
    has already put ``sys.modules["isolation"]`` back to THIS module, so the engine's own package
    name resolves to a plain module and it dies with "isolation is not a package". Any call into a
    function like that has to happen in here.

    ⚠ The shipping dispatch path does **not** need this — ``build_contained_session_prefix`` and
    ``HostAllowlistNetworkStack.render_dispatch`` import at module level, so they work once bound.
    The two that defer are ``negative_control`` (the seal control) and the ``vertex-only`` / ``open``
    branches of ``docker_prefix``, which this consumer does not take. Checked 2026-09-18; re-check
    if a dispatch ever starts failing with that message.
    """
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
        yield path
    finally:
        # The engine classes stay alive through the namespace the caller keeps, so dropping its
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
#:
#: ⚠ **This is also where ``{{spec_root}}`` points, and a second mount for it was deleted on
#: 2026-09-18.** The grant used to carry a separate ``/workspace/spec`` alongside a
#: version-addressed snapshot, on the reasoning that the materialized tree is chmod'd read-only and
#: so cannot be a working checkout. Two things make that wrong. The plan's own step 2a concludes the
#: cwd should simply *be* the materialized snapshot — it already holds the program at the same
#: relative paths, is already read-only, and already has no ``.git`` and no ``CLAUDE.md``, so
#: version-addressing comes free and there is one fewer copy to keep in sync. And the "must be a
#: working checkout" reason died with the slash command: a contained session is handed its prompt on
#: argv (``dispatch_prompt``) and states its own permissions, so it never reads ``.claude/`` from the
#: cwd and needs no settings file there. ⇒ **one tree, mounted once, read-only, and it is the cwd.**
#: The deleted alternative also required a second directory that nothing in this repo creates.
CONTAINER_PROGRAM = "/workspace/program"

#: The staging **root** — every claim's staged evidence, and the only writable place the program gets
#: besides its trace.
#:
#: ⚠ **The root, not one claim, and this reversed on 2026-09-16.** A grant scopes a worker's whole
#: life and the number of claims per worker is a parameter; today's one-session-per-claim shape is the
#: N=1 case, not the design. A worker that will be asked about claims A through K is granted the
#: directory holding all of them and each request names an item inside it, which is the shape the
#: transport already assumes — inputs by reference, never inline.
CONTAINER_STAGING = "/workspace/staging"

#: Every container path this module will ever mount. One place, so a reader can see the whole surface.
CONTAINER_PATHS: tuple[str, ...] = (
    CONTAINER_PROGRAM,
    CONTAINER_STAGING,
)

#: ⚠ **There is deliberately no trace mount, and one was deleted on 2026-09-18.** A ``--rm``
#: container discards its own ``~/.claude/projects``, so containerizing would silently end
#: adjudicator traceability — and silently is literal: ``trace_ref`` starts ``None`` and every
#: failure path resets it to ``None``, so every trace would be ``null`` while the run still reported
#: ``status: ok``. The fix is not a mount. Plan item 1d: the adapter **already holds the streamed
#: session JSON** (it is the captured stdout that ``_parse_stream_meta`` reads), so it is persisted
#: host-side beside the verdict. That is strictly better than what the uncontained path did, which
#: was to glob the host's ``~/.claude/projects`` — a cache Claude Code owns and prunes, i.e. evidence
#: for a published result living somewhere that may garbage-collect it.

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

#: What the shipping boundary IS, as a name a reviewer approves rather than an instance name a run
#: mints. The allowlist stack's Docker network carries a per-run id, so the rendered `--network`
#: value is useless to a pin; this is the stable statement of the same thing.
HOST_ALLOWLIST_POLICY = "host-allowlist"

#: The selftest stand-in's policy, named so a configuration hash computed under a selftest can never
#: collide with one computed under the real boundary.
STAND_IN_POLICY = "selftest-stand-in"


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
    program_dir: pathlib.Path,
    staging_root: pathlib.Path,
    output_roots: Sequence[pathlib.Path],
):
    """The program's grant: one :class:`SessionScope` for one program version.

    ``program_dir`` is the **materialized** tree for the version being scored — never the working
    checkout, which the optimizer may already have edited past this version, and which holds the
    files this grant exists to keep out.

    ⚠ **No ``stage`` parameter, and that absence is the design.** Phil struck the per-stage split on
    2026-09-17; the engine's grant has no stage dimension to put one in either way. The dispatch
    *dispatch* still carries a stage (``adapter.SarolRunner._inner_command`` takes one, and
    refuses any stage with no prompt of its own); the *grant* does not.

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
        # The materialized tree, mounted once: the program's bytes, the cwd, and what
        # ``{{spec_root}}`` resolves to inside the container. Version-addressed because the
        # materialized path already is (``adapter`` namespaces it per call, ``iter<n>-<tag>``), so
        # a v0 dispatch cannot land in v1's directory.
        program=pathlib.Path(program_dir),
        readable=(),
        writable=((pathlib.Path(staging_root), CONTAINER_STAGING),),
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

    The flag is passed in two places and only one of them is ours: this module's
    :func:`inner_command` builds the program's own argv, which is a local edit with no upstream
    dependency. The other is the shared wrapper on the *optimizer's* path. An implementer who
    changes only the wrapper leaves the program on bypass while the diff looks like the fix, so
    this asserts on the argv the Runner actually builds -- ``SarolRunner._inner_command`` calls it
    on every dispatch and refuses rather than sending one.
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
        # No session written to disk, so nothing this dispatch does can be resumed into the next
        # one. ⚠ Largely redundant with `--rm`, and kept anyway because the two cover different
        # failures: `--rm` discards the container, this stops the write happening at all. It is
        # honoured only with `--print`, which is two entries above.
        "--no-session-persistence",
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
    # ⚠ Inside the engine-import context because the ``"open"`` and ``"vertex-only"`` branches of
    # `build_docker_cmd_prefix` defer their own relative imports to call time. Outside it, those two
    # policies fail with "isolation is not a package" -- a confusing error for a correct call. The
    # allowlist path this consumer ships on does not go through here; see `engine_importable`.
    with engine_importable():
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
# What a Runner is configured with (1f)
# =================================================================================================


@dataclasses.dataclass(frozen=True)
class ContainerConfig:
    """Everything a Runner needs to put each of its dispatches in a container, stated once per run.

    ⚠ **No value of this means "no container".** ``open_boundary`` is always a boundary; the
    selftests inject a *fake renderer* rather than switching the boundary off (OQ7), so no
    production-reachable branch can disable it. There is deliberately no ``contained: bool``, no
    ``None`` fallback and no environment override — an opt-out for anything that produces or guards
    a reportable number would make the baseline and the iterations measured on different
    instruments, which is not a weaker guarantee but an invalid comparison.

    ``open_boundary`` takes the run's grant and returns a context manager yielding a callable that
    renders one dispatch's prefix. It is a context manager because the shipping boundary owns a
    Docker network and a Squid sidecar that must be torn down on every exit path, and it is opened
    **once per batch** rather than per claim — see :func:`allowlist_stack` for why.
    """

    image: str
    hosts: tuple[str, ...]
    #: What KIND of network boundary this is, named rather than inferred. The configuration pin
    #: (Phase 3) needs it, and the alternative -- reading `--network` off a rendered prefix -- pins
    #: the wrong thing: the allowlist stack's network name carries a per-run id, so it would move
    #: the hash every run, while the plain policies render a literal. A name here is stable and is
    #: the thing a reviewer actually approves.
    policy: str
    open_boundary: Any
    #: What instrument this boundary actually is, as a dict, for the run manifest. A zero-argument
    #: callable rather than a value because the shipping answer costs a container start and the
    #: selftests must not pay it — the same injection shape as ``open_boundary``.
    #:
    #: ⚠ **No default, deliberately.** Giving it ``None`` would make the field syntactically
    #: optional while the contract says it is required, and the two factories below both supply
    #: one — so the only thing a default could do is let a future construction site omit it and
    #: reach the runtime refusal instead of a TypeError here.
    describe: Any


def container_problem(config) -> str | None:
    """Why this Runner cannot dispatch into a container, or ``None``. The 1f refusal, as a predicate.

    Called from ``SarolRunner.__init__`` — the one place all three routes to a Runner pass through
    (``build_components``, direct construction, and a pre-built ``components=`` dict that skips
    ``build_components`` entirely). A gate in ``build_components`` would miss the baseline recut
    *and* the ``components=`` path while the suite reported green.
    """
    if config is None:
        return (
            "no container configuration was given, so this Runner would dispatch the program "
            "with the run of whatever directory it was pointed at. Pass "
            "isolation.shipping_container(image=...) for anything that produces or guards a "
            "number, or isolation.fake_container() in a selftest"
        )
    for field in ("image", "hosts", "open_boundary", "describe"):
        if not hasattr(config, field):
            return f"the container configuration has no {field!r}; expected an isolation.ContainerConfig"
    if "@sha256:" not in str(config.image):
        return (
            f"the container image {config.image!r} is named by tag, not by digest. A tag is not a "
            "version: an image rebuilt from the same Dockerfile on a newer base layer keeps the "
            "tag and changes the bytes, so a run pinned by tag cannot say what it ran on"
        )
    if not config.hosts:
        return (
            "the egress allowlist is empty, which denies every destination including the API the "
            "adjudicator needs to think; use a real deny-all policy if that is the intent"
        )
    if not callable(config.open_boundary):
        return "the container configuration's open_boundary is not callable"
    if not callable(config.describe):
        return (
            "the container configuration cannot describe itself, so a run under it would report "
            "numbers without naming the instrument that produced them"
        )
    return None


#: The image this program dispatches into, built from the shared Dockerfile with the CLI version
#: this host runs. ⚠ **A build argument, not a change to the shared default** — moving
#: `CLAUDE_CODE_VERSION` in `isolation/Dockerfile` would move the image for rad-eval, crc and MedVAL
#: too, and none of them asked for it. Rebuild with::
#:
#:     docker build --build-arg CLAUDE_CODE_VERSION=$(claude --version | cut -d' ' -f1) \
#:       -t paper-trail-isolation:<version> -f <engine>/isolation/Dockerfile <engine>/isolation
SHIPPING_IMAGE_TAG = "paper-trail-isolation:2.1.277"


def image_digest_ref(tag: str = SHIPPING_IMAGE_TAG) -> str | None:
    """``<repo>@sha256:...`` for a locally built image, or ``None`` if it is not built.

    ⚠ **A locally built image has a digest and Docker will run it by one** — verified 2026-09-18,
    and worth stating because the obvious reading is that digests require a registry push. That
    reading would have made :func:`container_problem`'s digest rule unsatisfiable without standing
    up a registry, which is a piece of infrastructure this program does not otherwise need.
    """
    try:
        done = subprocess.run(
            ["docker", "inspect", "--format", "{{.Id}}", tag],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    digest = (done.stdout or "").strip()
    if done.returncode != 0 or not digest.startswith("sha256:"):
        return None
    return f"{tag.split(':')[0]}@{digest}"


def host_cli_version() -> str | None:
    """The Claude Code version on THIS machine, or None if it cannot be read.

    ⚠ **Recorded, never gated on.** It used to be half of a host-vs-image equality check, which
    Phil struck on 2026-09-19 because a background CLI update on the Mac turned it red without
    anything about the experiment changing (see :func:`mislabelled_image_problem`). The host runs
    the optimizer session and produces no reported number, so its version belongs in the run
    manifest as provenance and nowhere else. Anything that makes a *pass/fail* decision from this
    value is reintroducing the bug.
    """
    return _version_from(["claude", "--version"])


def image_cli_version(image: str) -> str | None:
    """The Claude Code version installed INSIDE ``image``, or None. Starts one short container."""
    return _version_from(
        ["docker", "run", "--rm", "--entrypoint", "sh", image, "-c", "claude --version"]
    )


def _version_from(command: Sequence[str]) -> str | None:
    """First whitespace-delimited token of ``command``'s output, or None if it did not run."""
    try:
        done = subprocess.run(list(command), capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    first = (done.stdout or "").strip().split()
    return first[0] if first else None


#: A tag that names the Claude Code it contains, e.g. ``paper-trail-isolation:2.1.277``.
_TAGGED_VERSION = re.compile(r":(\d+\.\d+\.\d+)$")


def tag_claimed_version(image: str) -> str | None:
    """The Claude Code version an image's own tag claims, or ``None`` if it claims none."""
    found = _TAGGED_VERSION.search(image)
    return found.group(1) if found else None


def mislabelled_image_problem(image: str) -> str | None:
    """Does ``image`` contain the Claude Code its own tag claims? Returns a problem, or ``None``.

    🚩 **This compared the image against THIS HOST until 2026-09-19, and the host was the wrong
    object to compare it to.** Phil's ruling, on being shown the check going red overnight: *"our
    code shouldn't break because of a mac autoupdate"*. He was right, and the reason is not only
    ergonomic. Since containment, every scored dispatch runs **inside the image**; the host's CLI
    runs the optimizer session, which produces no number anyone reports. So host-vs-image equality
    (a) could not fail for a reason that affects a result, and (b) failed routinely for a reason
    that affects nothing — a background Claude Code update. Worse, the obvious way to clear it was
    to rebuild the image to match the new host, which **moves the instrument mid-experiment**: the
    exact harm the check was written to prevent.

    What must not move is the image, so the image is what this now checks, against a reference that
    is already committed and cannot drift on its own — **its own tag**. ``SHIPPING_IMAGE_TAG`` names
    a version; this asserts the image really contains it. That is portable (a VM gets the same
    answer), stable (no host in it), and catches the failure that actually matters: a rebuild that
    quietly changed the CLI while keeping the label.

    ⚠ **Exact image identity is Phase 3's job, and this is not a substitute for it.** A version
    string is coarser than a digest — two builds of 2.1.277 are different images with the same
    label. The plan's V4 requires the configuration pin to move when the image **digest** moves at
    an unchanged tag, which is the precise form. This is the cheap guard that runs today; it must
    not be cited as pinning the image.

    The host's version is still *recorded* — ``shipping_container.describe`` writes both into the
    run manifest — because provenance is worth keeping even where a gate on it is not.
    """
    claimed = tag_claimed_version(image)
    if claimed is None:
        return (
            f"{image!r} does not name a Claude Code version in its tag, so there is nothing to hold "
            "it to. The shipping image is tagged with the version it contains on purpose: a label "
            "like 'latest' makes no claim, and an instrument that makes no claim about itself "
            "cannot be checked"
        )
    inside = image_cli_version(image)
    if inside is None:
        return f"cannot read the Claude Code version inside {image!r}; is the image built?"
    if inside != claimed:
        return (
            f"{image!r} is mislabelled: its tag claims Claude Code {claimed} and it actually runs "
            f"{inside}. One of the two is wrong, and either way a run under it would record an "
            "instrument it is not using. Rebuild with --build-arg CLAUDE_CODE_VERSION="
            f"{claimed}, or retag the image to :{inside}"
        )
    return None


def shipping_container(
    *, image: str, hosts: Sequence[str] = EGRESS_ALLOWED_HOSTS
) -> ContainerConfig:
    """The real boundary: a one-host egress allowlist, and a fresh container per dispatch.

    What every site that produces or guards a number takes — ``build_components``,
    ``scripts/run_baseline.py`` and the canary.
    """

    def open_boundary(scope):
        @contextlib.contextmanager
        def entered():
            stack = allowlist_stack(scope=scope, image=image, hosts=hosts)
            with stack:
                yield lambda dispatch_scope: allowlist_dispatch_prefix(
                    scope=dispatch_scope, stack=stack
                )

        return entered()

    def describe() -> dict:
        # Probed, not stated. A version someone typed beside the image is a claim; this is the
        # instrument answering for itself. Costs one short container per run, not per claim.
        return {
            "image": image,
            "cli_version": image_cli_version(image),
            "host_cli_version": host_cli_version(),
            "egress_hosts": list(hosts),
        }

    return ContainerConfig(
        image=image,
        hosts=tuple(hosts),
        policy=HOST_ALLOWLIST_POLICY,
        open_boundary=open_boundary,
        describe=describe,
    )


#: A digest-shaped stand-in, so a selftest asserts the shape production must use.
FAKE_IMAGE = "ghcr.io/example/paper-trail@sha256:" + "0" * 64


def fake_container(
    *, calls: list | None = None, image: str = FAKE_IMAGE
) -> ContainerConfig:
    """A recording stand-in for the 19 selftest construction sites. **Selftests only.**

    ⚠ **This is a fake *renderer*, not an opt-out**, and the difference is the whole of OQ7. It
    still emits docker-shaped argv, so a selftest asserting on a command asserts on the same shape
    production builds; what it does not do is start anything. A boolean that skipped the prefix
    would let a selftest pass while proving nothing about the argv, and would put a
    boundary-disabling branch in reachable code.

    Nothing stops a *production* site importing this, which is why the count of construction sites
    is asserted (V2c) rather than trusted: a new site taking the fake changes that count.
    """
    recorded = calls if calls is not None else []

    def open_boundary(scope):
        @contextlib.contextmanager
        def entered():
            def render(dispatch_scope) -> list[str]:
                recorded.append(dispatch_scope)
                argv = ["docker", "run", "--rm", "--network", "fake-internal"]
                if dispatch_scope.program is not None:
                    argv += ["-v", f"{dispatch_scope.program}:{CONTAINER_PROGRAM}:ro"]
                for host, container in dispatch_scope.readable:
                    argv += ["-v", f"{host}:{container}:ro"]
                for host, container in dispatch_scope.writable:
                    argv += ["-v", f"{host}:{container}:rw"]
                for name in ENV_ALLOWLIST:
                    argv += ["--env", name]
                argv += ["-w", dispatch_scope.workdir, image]
                return argv

            yield render

        return entered()

    return ContainerConfig(
        image=image,
        hosts=EGRESS_ALLOWED_HOSTS,
        policy=STAND_IN_POLICY,
        open_boundary=open_boundary,
        # Marked as a stand-in rather than left empty, so a manifest written under a selftest can
        # never be mistaken for one written under a real boundary.
        describe=lambda: {
            "image": image,
            "cli_version": None,
            "host_cli_version": None,
            "egress_hosts": list(EGRESS_ALLOWED_HOSTS),
            "stand_in": "fake_container: no container was started and no version was probed",
        },
    )


# =================================================================================================
# The configuration pin (Phase 3) — what the program was run under, hashed and held to a committed
# reference
# =================================================================================================

#: Where the per-claim adjudicator trace lands, relative to that claim's output directory. ONE
#: definition: ``adapter`` writes to it and the configuration hash covers it, so the two cannot
#: drift into disagreeing about where a published result's evidence lives.
TRACE_DEST_SHAPE = "traces/{claim_id}-{stage}.jsonl"

#: The committed manifest, repo-relative. Read through ``git show HEAD:<this>``, never off disk.
MANIFEST_REL = "experiments/sarol-2024/program-v0/manifest.json"

#: The key under ``runtime_pins`` holding the expected configuration hash.
PIN_KEY = "isolation_config"

#: Bumped whenever the *shape* below changes, so an old pin cannot silently satisfy a new schema.
#: Without it, deleting a component from the payload would produce a different hash and read as
#: "someone changed the configuration" rather than "the schema moved".
CONFIG_SCHEMA_VERSION = 1


def mount_shape(prefix: Sequence[str], scope) -> tuple[tuple[str, str, str], ...]:
    """Every rendered mount as ``(role, target, mode)`` — the host source replaced by its role.

    ⚠ **The plan asked for ``(source, target, mode)`` and that cannot be pinned.** Verified by
    printing a real render (2026-09-19): the program source is the per-iteration materialized tree
    (`.../tmpXXXX/iter3-v0`) and the staging source is the run's output root, so a hash over raw
    sources moves **every iteration and every run** and no committed value could ever match it. The
    plan's actual requirement — *"the mount set as rendered, so the pin is computed from the same
    bytes V2a-seal probes rather than from the intent that produced them"* — is preserved: this
    reads the rendered argv, not the grant. Only the one component that cannot be a constant is
    replaced, by the thing the plan separately demands be present anyway (*"with each mount's
    role"*).

    Everything the pin is meant to catch survives: a changed target, a changed mode, a mount added
    or removed, or a source that has moved to a different role. What is lost is only "this exact
    temp directory", which was never reviewable.
    """
    roles = {str(pathlib.Path(scope.program).resolve()): "program"}
    for host, _container in scope.writable:
        roles[str(pathlib.Path(host).resolve())] = "staging"
    for host, _container in scope.readable:
        roles.setdefault(str(pathlib.Path(host).resolve()), "readable")
    shaped = []
    for source, target, mode in rendered_mounts(prefix):
        # ⚠ Resolve both sides. On macOS a grant holding `/private/var/...` and an argv holding
        # `/var/...` are the same directory spelled two ways, and an unresolved comparison would
        # label a known mount "unknown" — the failure in [[resolved-vs-unresolved...]], again.
        shaped.append(
            (roles.get(str(pathlib.Path(source).resolve()), "UNKNOWN"), target, mode)
        )
    return tuple(sorted(shaped))


def _flag_value(argv: Sequence[str], flag: str) -> str | None:
    """The value after ``flag``, or ``None`` if the flag is absent or has nothing after it."""
    argv = list(argv)
    if flag not in argv:
        return None
    i = argv.index(flag)
    return argv[i + 1] if i + 1 < len(argv) else None


def _flag_values(argv: Sequence[str], flag: str) -> tuple[str, ...]:
    """Every value following each occurrence of ``flag``, sorted."""
    argv = list(argv)
    return tuple(sorted(argv[i + 1] for i, a in enumerate(argv) if a == flag and i + 1 < len(argv)))


def configuration(*, container, scope, prefix, inner_command, program_entries) -> dict:
    """Everything about the boundary this run puts the program behind, as a plain dict.

    Read from the **rendered** argv wherever the plan says "as rendered", and from the stated
    configuration only where a render carries a per-run instance name instead of a reviewable value
    (the network, see :data:`HOST_ALLOWLIST_POLICY`).

    ⚠ **`prefix` may be rendered on the deny-all policy rather than the shipping allowlist**, and
    that is sound for exactly one reason, which is asserted rather than assumed: the two renders
    agree mount for mount (selftest *"...and the plain-policy render agrees with it mount for
    mount"*). Nothing network-shaped is taken from `prefix`. This is what lets the pin be computed
    at preflight without standing up a Squid sidecar to find out what we are about to run.

    ⚠ **The env allowlist contributes NAMES only.** A rotated OAuth token must not read as a
    configuration change, or the gate gets switched off the first time a credential is refreshed.
    """
    described = container.describe() or {}
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "image": {
            "ref": container.image,
            "cli_version": described.get("cli_version"),
            "user": _flag_value(prefix, "--user"),
            "workdir": _flag_value(prefix, "-w"),
            # Rendered, stable, and behaviour-affecting: a container that runs out of memory
            # produces a failed dispatch, not a verdict. Beyond the plan's table, and recorded here
            # rather than silently: they cost nothing to cover and a change to either is exactly the
            # kind of thing that moves results without moving any file.
            "cpus": _flag_value(prefix, "--cpus"),
            "memory": _flag_value(prefix, "--memory"),
        },
        "boundary": {
            "mounts": [list(m) for m in mount_shape(prefix, scope)],
            "network_policy": container.policy,
            "egress_hosts": sorted(container.hosts),
        },
        "session": {
            "add_dirs": sorted(_flag_values(inner_command, "--add-dir")),
            "env_allowlist": sorted(_flag_values(prefix, "--env")),
            "permission_mode": _flag_value(inner_command, "--permission-mode"),
            "permission_prompts": _flag_value(inner_command, "--permission-prompts"),
            "allowed_tools": sorted(
                (_flag_value(inner_command, "--allowedTools") or "").split(",")
            ),
            # Every option name on the inner argv, values excluded. This is what makes the pin
            # notice a flag ARRIVING as well as one leaving -- including
            # `--exclude-dynamic-system-prompt-sections`, which is deliberately absent and whose
            # return would otherwise move nothing.
            "option_names": sorted({a for a in inner_command if str(a).startswith("--")}),
        },
        "program": {
            # Paths, not contents. Contents are `combined_hash`'s job and the optimizer edits them
            # every iteration by design; the isolation pin must not move when the program is
            # improved, only when the BOX around it changes. A file joining or leaving the program
            # is a configuration change and does move it.
            "fileset": sorted(program_entries),
            "trace_destination": TRACE_DEST_SHAPE,
        },
    }


def configuration_hash(config: dict) -> str:
    """A stable sha256 over :func:`configuration`'s dict. Key order cannot move it."""
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def committed_configuration_pin(
    policy: str, *, repo_root: pathlib.Path = REPO_ROOT, manifest_rel: str = MANIFEST_REL
) -> str | None:
    """The expected hash **for this boundary kind**, from committed bytes — ``git show HEAD:<manifest>``.

    ⚠ **Keyed by policy, and that is not a convenience.** The selftests render a real grant through
    a stand-in boundary (OQ7: an injected fake renderer, never a switch that turns the boundary
    off), so their configuration legitimately hashes to something other than the shipping one. The
    alternatives were both bad: give the Runner a way to skip the gate — an opt-out on the one check
    that says a scored run used an approved boundary — or leave the suite permanently red. Keying by
    policy instead means **both configurations are committed and reviewable**, the selftests
    exercise the real gate rather than a bypass of it, and a boundary whose kind has no pin at all
    is refused rather than defaulted.

    ⚠ **Never the worktree copy, and this is a defect Plan A actually shipped.** Its Gate H compared
    a sheet against a stub that was editable in the same tree, so one session rewriting both sides
    passed the gate. A pin the same edit can move is not a pin. ``canary.py`` states the rule: *a
    guard whose reference value is not under version control is not a guard.*

    Returns ``None`` when the manifest is not committed, has no such key, or git cannot be run —
    every one of which :func:`configuration_pin_problem` treats as a refusal, never as a pass.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{manifest_rel}"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    try:
        pins = (json.loads(done.stdout) or {}).get("runtime_pins") or {}
    except json.JSONDecodeError:
        return None
    entry = (pins.get(PIN_KEY) or {}).get(policy)
    if isinstance(entry, dict):
        entry = entry.get("hash")
    return entry if isinstance(entry, str) and entry else None


def configuration_pin_problem(
    config_hash: str, *, committed: str | None, policy: str = ""
) -> str | None:
    """Does the configuration about to run match the committed pin? A problem, or ``None``.

    ⚠ **It compares the computed hash against the MANIFEST, never against what the release builder
    would stamp.** The builder takes its pin from the same committed value at all five construction
    sites, so "what the builder would stamp" versus "what we computed" compares a value to itself
    and cannot fail — the plan names this tautology explicitly, and it is the same inertness that
    left `optimizer_isolation_hash` as the literal `'sarol-2024'` on all ten payloads of the last
    run.
    """
    if not committed:
        return (
            f"no configuration pin committed at runtime_pins.{PIN_KEY}.{policy} in "
            f"HEAD:{MANIFEST_REL}. "
            f"The configuration about to run hashes to {config_hash}. Commit that value as the pin "
            "once it has been reviewed -- `python3 optimizer/isolation.py --print-pin` prints the "
            "block to paste. Refusing rather than defaulting: a run with no pin is precisely the "
            "state this gate exists to end"
        )
    if committed != config_hash:
        return (
            f"the isolation configuration does not match the committed pin. Expected {committed}, "
            f"computed {config_hash}. Either the boundary changed and the pin is stale, or the pin "
            "is right and something moved underneath this run -- inspect with `python3 "
            "optimizer/isolation.py --print-config` before re-pinning, because re-pinning a "
            "configuration nobody looked at turns this gate off"
        )
    return None

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
        # Shaped like a real materialized path, which `adapter` namespaces per call.
        "program_dir": runs_root / "run_dry" / "materialized" / f"iter0-{version}",
        "staging_root": train_root / "staging",
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


def _fake_render(scope) -> list[str]:
    """One dispatch rendered through the selftest stand-in, for comparing against the real one."""
    with fake_container().open_boundary(scope) as render:
        return render(scope)


def _fake_render_calls(scope) -> list:
    """What the stand-in recorded, so the recording itself is asserted rather than assumed."""
    seen: list = []
    with fake_container(calls=seen).open_boundary(scope) as render:
        render(scope)
    return seen


def _renders(fn) -> bool:
    """Did ``fn`` return a rendered docker argv rather than raising?

    ⚠ Reported rather than allowed to propagate. The failure this guards against is an exception
    (the engine's call-time relative imports resolving to the wrong ``isolation``), and an
    exception escaping the check list crashes the whole dry run — which prints nothing at all and
    so cannot be told apart from the gate passing.
    """
    try:
        argv = fn()
    except Exception:  # noqa: BLE001
        return False
    return isinstance(argv, list) and bool(argv) and "docker" in argv[0]


def _raises(fn, *, want: str | None = None) -> bool:
    """Did ``fn`` refuse with a ``ValueError``, optionally one whose message contains ``want``?"""
    try:
        fn()
    except ValueError as exc:
        return want is None or want in str(exc)
    except Exception:
        return False
    return False


def _committed_bytes_checks(repo: pathlib.Path) -> list:
    """The pin comes from ``git show HEAD:``, so editing the worktree copy cannot move it.

    ⚠ **This is not a hypothetical.** Plan A's Gate H compared a sheet against a stub that was
    editable in the same tree, so a single session rewriting both sides passed the gate it was
    supposed to fail. A reference the same edit can move is not a reference. Run against a real
    throwaway git repo rather than a mock, because the property under test *is* git's.
    """
    import subprocess as sp

    manifest = repo / MANIFEST_REL
    manifest.parent.mkdir(parents=True, exist_ok=True)

    def write(value):
        manifest.write_text(
            json.dumps({"runtime_pins": {PIN_KEY: {"host-allowlist": {"hash": value}}}}),
            encoding="utf-8",
        )

    def git(*args):
        return sp.run(["git", "-C", str(repo), *args], capture_output=True, text=True)

    write("COMMITTED")
    ok = git("init", "-q").returncode == 0
    git("config", "user.email", "gate@example.invalid")
    git("config", "user.name", "gate")
    git("add", "-A")
    ok = ok and git("commit", "-q", "-m", "pin").returncode == 0
    from_head = committed_configuration_pin("host-allowlist", repo_root=repo)

    # Now the attack the gate must survive: edit the worktree copy and ask again.
    write("WORKTREE-EDIT")
    after_edit = committed_configuration_pin("host-allowlist", repo_root=repo)
    unknown_policy = committed_configuration_pin("no-such-policy", repo_root=repo)
    return [
        ("the pin is read from committed bytes", ok and from_head == "COMMITTED"),
        (
            "...and an edit to the worktree copy does NOT move it, which is the defect Plan A's "
            "Gate H shipped",
            after_edit == "COMMITTED",
        ),
        (
            "...and a boundary kind with no pin committed reads as absent, so it is refused rather "
            "than falling back to another kind's",
            unknown_policy is None,
        ),
    ]


def _pin_checks() -> list:
    """V4: one case per component the pin covers, each moving an input rather than the dict."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="pin-checks-") as tmp:
        tmp = pathlib.Path(tmp)
        program = tmp / "program"
        program.mkdir()
        staging = tmp / "run" / "train" / "staging"
        staging.mkdir(parents=True)
        scope = program_scope(
            profile="retrieval",
            program_dir=program,
            staging_root=staging,
            output_roots=[tmp / "run" / "train"],
        )
        base_container = fake_container()
        base_prefix = dispatch_prefix(
            scope=scope, image=base_container.image, network_policy=DENY_ALL_EGRESS
        )
        base_inner = inner_command(scope=scope, prompt="", model="m", max_budget_usd=1.0)
        entries = ["a.md", "b.md"]

        def h(*, container=None, prefix=None, inner=None, program_entries=None) -> str:
            return configuration_hash(
                configuration(
                    container=container or base_container,
                    scope=scope,
                    prefix=prefix or base_prefix,
                    inner_command=inner or base_inner,
                    program_entries=program_entries or entries,
                )
            )

        def swapped(argv, old, new):
            return [new if a == old else a for a in argv]

        base = h()
        mounts = rendered_mounts(base_prefix)
        program_mount = f"{mounts[0][0]}:{mounts[0][1]}:{mounts[0][2]}"
        staging_mount = f"{mounts[1][0]}:{mounts[1][1]}:{mounts[1][2]}"

        moved = {
            "a different image digest at the same tag": h(
                container=fake_container(image=FAKE_IMAGE.replace("0" * 64, "1" * 64))
            ),
            "a changed mount target": h(
                prefix=swapped(base_prefix, program_mount,
                               f"{mounts[0][0]}:/workspace/elsewhere:{mounts[0][2]}")
            ),
            "a changed mount mode": h(
                prefix=swapped(base_prefix, program_mount, f"{mounts[0][0]}:{mounts[0][1]}:rw")
            ),
            "a changed mount role": h(
                prefix=swapped(base_prefix, staging_mount,
                               f"{tmp}/elsewhere:{mounts[1][1]}:{mounts[1][2]}")
            ),
            "a different network policy": h(container=shipping_container(image=FAKE_IMAGE)),
            "a different egress allowlist": h(
                container=shipping_container(image=FAKE_IMAGE, hosts=("example.invalid",))
            ),
            "a different container user": h(prefix=swapped(base_prefix, "1000:1000", "4242:4242")),
            "a different workdir": h(
                prefix=swapped(base_prefix, CONTAINER_PROGRAM, "/workspace/other")
            ),
            "a different memory limit": h(prefix=swapped(base_prefix, "4g", "16g")),
            "a changed allowedTools set": h(
                inner=swapped(base_inner, ",".join(ALLOWED_TOOLS), "Read,Write,Bash")
            ),
            "a changed permission mode": h(inner=swapped(base_inner, "default", "acceptEdits")),
            "a flag arriving on the inner argv": h(
                inner=list(base_inner) + ["--exclude-dynamic-system-prompt-sections"]
            ),
            "a changed program fileset": h(program_entries=["a.md", "b.md", "c.md"]),
        }
        # Names only: the env allowlist is rendered as `--env NAME`, so no value is ever in scope to
        # move the hash. Proved by hashing a prefix whose token NAME is unchanged -- if any value
        # leaked in, the two renders below would differ.
        same_names = h(prefix=list(base_prefix))

        unmoved = [label for label, got in moved.items() if got == base]
        return [
            (
                "every component the pin covers moves the hash when it changes, one case each: "
                + f"{len(moved)} checked",
                not unmoved,
            ),
            (
                "...naming any that did not move, because a silent component is the whole failure",
                not unmoved,
            ),
            (
                "...and all of them are distinct hashes, so two different configurations cannot "
                "share a pin",
                len(set(moved.values())) == len(moved),
            ),
            (
                "the env allowlist contributes NAMES only, so rotating the token is not a "
                "configuration change",
                same_names == base
                and all("CLAUDE_CODE_OAUTH_TOKEN=" not in str(a) for a in base_prefix),
            ),
            (
                "a mount whose source belongs to no granted role is marked UNKNOWN rather than "
                "quietly dropped",
                any(
                    m[0] == "UNKNOWN"
                    for m in mount_shape(
                        list(base_prefix) + ["-v", "/tmp/sneaked:/workspace/extra:ro"], scope
                    )
                ),
            ),
            (
                "the literal 'sarol-2024' no longer satisfies the pin",
                configuration_pin_problem(base, committed="sarol-2024") is not None,
            ),
            (
                "...nor does an absent pin, which refuses rather than defaulting",
                configuration_pin_problem(base, committed=None) is not None,
            ),
            (
                "...while the matching pin passes",
                configuration_pin_problem(base, committed=base) is None,
            ),
            *_committed_bytes_checks(tmp / "pinrepo"),
        ]


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
                _replaced(
                    a_scope,
                    writable=((stage_claim.GOLD_ROOT.parent.parent, CONTAINER_STAGING),),
                )
            )
            is not None,
        ),
        (
            "...which is why granting the repo root as the program tree is refused outright",
            _raises(
                lambda: program_scope(profile="retrieval", **{**dry, "program_dir": REPO_ROOT}),
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
        (
            "no dispatch writes a resumable session to disk",
            all(
                "--no-session-persistence" in r["inner"] and "--print" in r["inner"]
                for r in rows
            ),
        ),
        (
            "...and the flag is honoured, since it only applies with --print, which precedes it",
            # ⚠ Both membership tests come FIRST and the `and` short-circuits. Written the obvious
            # way -- two bare `.index()` calls -- dropping the flag raises ValueError and crashes
            # the suite instead of turning this check red, and a crashed suite reports nothing.
            # Caught by mutation, which is the only thing that finds this shape.
            all(
                "--print" in r["inner"]
                and "--no-session-persistence" in r["inner"]
                and r["inner"].index("--print") < r["inner"].index("--no-session-persistence")
                for r in rows
            ),
        ),
        (
            "--exclude-dynamic-system-prompt-sections stays OFF, because it relocates rather than "
            "removes and would read as a closed channel that is open",
            all("--exclude-dynamic-system-prompt-sections" not in r["inner"] for r in rows),
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
        # -- the Runner's configuration, and the 1f refusal ----------------------------------------
        (
            "a Runner given no container configuration is refused, naming what to pass",
            (lambda r: r is not None and "shipping_container" in r)(container_problem(None)),
        ),
        (
            "...and an image named by tag rather than digest is refused",
            (lambda r: r is not None and "not by digest" in r)(
                container_problem(shipping_container(image="ghcr.io/example/paper-trail:latest"))
            ),
        ),
        (
            "...and an empty egress allowlist is refused",
            container_problem(shipping_container(image=FAKE_IMAGE, hosts=())) is not None,
        ),
        (
            "...while both the shipping and the selftest configurations are accepted",
            container_problem(shipping_container(image=FAKE_IMAGE)) is None
            and container_problem(fake_container()) is None,
        ),
        (
            "the unrestricted and deny-all policies render at all, which they did not while the "
            "engine's call-time imports ran outside the engine context",
            _renders(
                lambda: dispatch_prefix(
                    scope=grants[0]["scope"], image=_DRY_IMAGE,
                    network_policy=UNRESTRICTED_EGRESS
                )
            ),
        ),
        (
            "a boundary that cannot say what instrument it is gets refused, because a number "
            "without its instrument is not reportable",
            (lambda r: r is not None and "instrument" in r)(
                container_problem(
                    dataclasses.replace(shipping_container(image=FAKE_IMAGE), describe=None)
                )
            ),
        ),
        (
            "...and the selftest stand-in says so in what it reports, so a manifest written "
            "under it cannot be mistaken for one written under a real boundary",
            "stand_in" in fake_container().describe(),
        ),
        (
            "...while the shipping description names the image, the CLI inside it and the host's, "
            "which is what makes the parity check possible at all",
            set(shipping_container(image=FAKE_IMAGE).describe())
            >= {"image", "cli_version", "host_cli_version", "egress_hosts"},
        ),
        (
            "the configuration carries no way to switch the boundary off",
            not [
                f.name
                for f in dataclasses.fields(ContainerConfig)
                if f.name
                in ("contained", "enabled", "skip", "bypass", "opt_out", "uncontained", "dry_run")
            ]
            and all(
                f.type is not bool for f in dataclasses.fields(ContainerConfig)
            ),
        ),
        (
            "the shipping configuration names the one-host allowlist, not the unrestricted policy",
            shipping_container(image=FAKE_IMAGE).hosts == EGRESS_ALLOWED_HOSTS,
        ),
        (
            "the selftest stand-in renders the SAME mount set as the real renderer",
            (
                lambda fake: tuple(sorted(rendered_mounts(fake)))
                == _expected_mounts(a_scope)
            )(_fake_render(a_scope)),
        ),
        (
            "...and is docker-shaped and digest-pinned, so a selftest asserts production's shape",
            _fake_render(a_scope)[:2] == ["docker", "run"]
            and any("@sha256:" in a for a in _fake_render(a_scope)),
        ),
        (
            "...and records the grant it was asked to render, so a selftest can assert on it",
            (lambda seen: len(seen) == 1 and seen[0] is a_scope)(_fake_render_calls(a_scope)),
        ),
        # -- against the real engine renderer ------------------------------------------------------
        (
            "the engine's argv starts a container and nothing else ran to find out",
            all(g["prefix"][:2] == ["docker", "run"] for g in grants),
        ),
        (
            "the rendered argv mounts exactly the two granted paths, in the right modes, no extras",
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
                == {CONTAINER_STAGING}
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
        # -- V4: the configuration pin ------------------------------------------------------
        #
        # ⚠ Every case below changes an INPUT and asserts the hash moved -- never the config dict
        # directly. Mutating the dict would only prove `configuration_hash` is a hash, which is not
        # in doubt; what is in doubt is whether `configuration` actually READS each component. The
        # first draft of this plan hashed only host-side properties, so a container swapped
        # underneath it left the hash unmoved and the pin certified a configuration it never saw.
        *_pin_checks(),
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


_PIN_WHY = {
    HOST_ALLOWLIST_POLICY: (
        "The boundary every scored dispatch runs behind. Covers the image by digest and the CLI "
        "inside it, the rendered mount set by role/target/mode, the network policy and egress "
        "allowlist, the session's add-dirs, permission mode, tool surface and full option-name set, "
        "the env allowlist by NAME (so a rotated token is not a configuration change), and the "
        "program's fileset and trace destination. Re-pin with `python3 optimizer/isolation.py "
        "--print-pin` ONLY after reading `--print-config` -- re-pinning a configuration nobody "
        "looked at turns this gate off."
    ),
    STAND_IN_POLICY: (
        "The same schema under the selftests' stand-in renderer (OQ7: an injected fake, never a "
        "switch that disables the boundary). Committed so the suite exercises the real gate instead "
        "of a bypass of it, and so a change to what the gates run under is itself reviewed."
    ),
}


def _configurations_by_policy() -> dict:
    """One configuration per boundary kind, built on a throwaway grant.

    The grant's paths are temporary and deliberately so: :func:`mount_shape` reduces every source to
    its role, so the hash does not depend on where this happened to run. That is the property that
    makes a committed pin possible at all.
    """
    import tempfile

    out: dict = {}
    with tempfile.TemporaryDirectory(prefix="isolation-pin-") as tmp:
        tmp = pathlib.Path(tmp)
        program = tmp / "program"
        program.mkdir()
        staging = tmp / "run" / "train" / "staging"
        staging.mkdir(parents=True)
        scope = program_scope(
            profile="retrieval",
            program_dir=program,
            staging_root=staging,
            output_roots=[tmp / "run" / "train"],
        )
        manifest = json.loads((REPO_ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
        entries = [e["path"] for e in manifest["entries"]]
        shipping_ref = image_digest_ref() or SHIPPING_IMAGE_TAG
        for container in (
            shipping_container(image=shipping_ref),
            fake_container(),
        ):
            out[container.policy] = configuration(
                container=container,
                scope=scope,
                prefix=dispatch_prefix(
                    scope=scope, image=container.image, network_policy=DENY_ALL_EGRESS
                ),
                inner_command=inner_command(
                    scope=scope, prompt="", model="", max_budget_usd=0.0
                ),
                program_entries=entries,
            )
    return out


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
    ap.add_argument(
        "--print-config",
        action="store_true",
        help="Print the configuration the pin hashes, for BOTH boundary kinds, as JSON.",
    )
    ap.add_argument(
        "--print-pin",
        action="store_true",
        help="Print the runtime_pins block to paste into the manifest. The documented re-pin path.",
    )
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.print_config or args.print_pin:
        configs = _configurations_by_policy()
        if args.print_config:
            print(json.dumps(configs, indent=2, sort_keys=True))
            return 0
        block = {
            PIN_KEY: {
                policy: {
                    "hash": configuration_hash(cfg),
                    "why": _PIN_WHY[policy],
                }
                for policy, cfg in sorted(configs.items())
            }
        }
        print("# Paste under `runtime_pins` in " + MANIFEST_REL + ", then COMMIT it --")
        print("# the gate reads `git show HEAD:<manifest>`, so an uncommitted edit changes nothing.")
        print(json.dumps(block, indent=2, sort_keys=True))
        return 0
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
