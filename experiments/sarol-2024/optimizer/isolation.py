"""paper-trail's container adapter — where the read boundary becomes a filesystem fact.

Every number this experiment has produced came from an adjudicator session running with ``cwd`` set
to the whole checkout and permissions switched off. In that tree sit the optimizer's own notes on
which claims it got wrong, its hypothesis log, and a file that leads to the gold labels. Across 561
traces nothing was actually read — but "nothing was read" is a measurement, not a guarantee, and it
is the only thing standing behind every result so far.

This module makes it a guarantee by handing the program a mount set instead of an instruction. What
it cannot reach is decided by what was mounted, and a prompt the optimizer is allowed to rewrite
cannot widen that.

**A thin consumer adapter, not a second Docker renderer.** Every docker flag stays the engine's to
emit (``isolation.docker_prefix.build_docker_cmd_prefix``). What lives here is paper-trail's mount
*contents as data*: which host directory backs which container directory, per stage.

Three things this module is deliberately strict about, each because a plausible-looking alternative
is silently weaker:

* **One path map, used by everything that crosses the boundary.** ``--add-dir``, the workdir, and
  any path interpolated into prompt text all resolve through :data:`PATH_MAP`. A path that is right
  in argv and stale in the prompt is a dispatch the adjudicator cannot complete, and it reads as a
  model failure rather than a wiring bug.
* **One prefix per dispatch, keyed on ``(stage, claim, version)``.** Not one per process. The
  program mount changes per program version, staging and trace per claim, and the mount *set* per
  stage — the extractor needs the paper, the adjudicator must never see it. A factory keyed on the
  claim alone hands all three stages one mount set the moment a three-stage profile runs, which is a
  boundary widening that looks like a stale path.
* **No second stage gate.** A stage with no mount set is already refused, at preflight, by
  ``profiles.unrunnable_reason``. :func:`unspecified_stage_problem` points at that check rather than
  duplicating it — building a second gate beside a working one is the failure pattern this whole
  plan is a response to.

**Not here yet, by intent** (each is its own phase and its own gate, and none is needed by the dry
run this module ships with): the sentinel scope predicate and its negative control (1g), the
optimizer's own mount set (1e), and the configuration hash that pins the rendered shape into the
manifest's ``runtime_pins`` (Phase 3).

Sister files: ``dispatcher.py:467`` (``val_isolation_problem``) for the ``-> str | None`` problem
idiom this module's predicates follow; ``adapter.py:700`` (``_stage_command``) for the uncontained
argv these replace.

Run the dry run — the cheapest gate in the plan, no container, no model, no spend::

    python3 experiments/sarol-2024/optimizer/isolation.py --selftest
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent

if str(_HERE) not in sys.path:  # importable as a script and as a module
    sys.path.insert(0, str(_HERE))

import profiles as profiles_mod  # noqa: E402

#: Repo root: experiments/sarol-2024/optimizer/isolation.py -> up 3. Same derivation as adapter.py.
REPO_ROOT = _HERE.parents[2]

#: Where `agentic-label-opt` is checked out. Same default and same override as `adapter.py:102`.
DEFAULT_ENGINE = pathlib.Path.home() / "Documents" / "Misc" / "Projects" / "agentic-label-opt"


def engine_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("AGENTIC_LABEL_OPT", DEFAULT_ENGINE)).expanduser()


def _import_engine():
    """Import the engine's docker prefix builder.

    Kept in a function, like ``adapter._import_engine``, so this module stays importable on a
    machine with no engine checkout. The dry run genuinely needs it — there is no argv to assert on
    without it — so :func:`_selftest` refuses rather than skipping.

    ⚠ **This module and the engine's package are both called ``isolation``.** The plan named this
    file ``optimizer/isolation.py`` and the engine's package was already ``isolation/``, so with
    this directory on ``sys.path`` a plain ``import isolation.docker_prefix`` resolves to *this
    file* and fails with "isolation is not a package". So the engine's root goes on the front of
    the path and this directory comes off it for the duration of the import. Anything else that
    needs both in one process has the same collision to handle — worth renaming one of them, but
    that is a change to a name the plan fixed, not a decision to make here.
    """
    import importlib  # noqa: PLC0415

    path = engine_path()
    saved = list(sys.path)
    try:
        sys.path[:] = [p for p in sys.path if p and pathlib.Path(p).resolve() != _HERE]
        sys.path.insert(0, str(path))
        for name in [k for k in sys.modules if k == "isolation" or k.startswith("isolation.")]:
            del sys.modules[name]
        module = importlib.import_module("isolation.docker_prefix")
        return module.build_docker_cmd_prefix
    finally:
        sys.path[:] = saved


# =================================================================================================
# The canonical container path map (1c)
# =================================================================================================

#: The program version being scored. Read-only, and also the working directory: the snapshot is a
#: real checkout, so it can be the cwd rather than needing a second copy kept in sync (2a).
#:
#: ⚠ **Not ``/workspace/program``, and this corrects the plan.** The plan's rendered shape (1c)
#: mounts the snapshot at ``/workspace/program``, but the engine *reserves* that path — along with
#: ``/workspace/writable``, ``/workspace/mistakes.json`` and ``/workspace/context`` — and rejects
#: any ``extra_ro_mounts`` target that collides with, nests under, or sits above one
#: (``docker_prefix.py:66``, ``:236``). It stays reserved even when nothing is mounted there, which
#: is exactly our case: the engine only mounts ``/workspace/program`` when ``edit_agent_mounts`` is
#: given, and the program has no editing agent. So the path the plan names is simultaneously
#: unmounted and unusable. A sibling avoids it with **zero engine diff**, which is what the plan
#: asked for; the alternative — passing ``edit_agent_mounts`` just to claim the path — would
#: declare an editing agent the program does not have and drag the editable overlays in with it.
CONTAINER_PROGRAM = "/workspace/snapshot"

#: This claim's staging tree, and the only writable place the program gets. One claim, not the run:
#: a shared staging mount lets claim B read claim A's verdict.
CONTAINER_STAGING = "/workspace/staging"

#: The session transcript. Writable and mounted because the container is `--rm`, and a contained
#: adjudicator with no trace is a less useful instrument than an uncontained one (1d).
CONTAINER_TRACE = "/workspace/trace"

#: The source paper. Mounted for the extractor alone. The adjudicator reads the finished evidence
#: envelope and must not see the paper — that is a standing product invariant
#: (`.claude/commands/paper-trail.md:388`), not a convenience of this experiment.
CONTAINER_PAPER = "/workspace/paper"

#: Host path prefixes that must never appear in the command handed to the session. The host sides of
#: the `-v` flags are host paths necessarily — see `inner_command_host_leak` for what is checked.
HOST_PATH_MARKERS = ("/Users/", "/home/", "/private/var/", "/tmp/")

#: Passed by NAME, never as `KEY=VALUE`. paper-trail authenticates with an env var, so the value in
#: host argv would land in the wrapper's `meta.json` too. ⚠ The engine's renderer emits only
#: `-e KEY=VALUE` today (`docker_prefix.py:437`); the by-name form is owed upstream and is a
#: prerequisite of landing Phase 1. The dry run asserts the name is what we ask for, which is the
#: part that is ours.
ENV_ALLOWLIST: tuple[str, ...] = ("CLAUDE_CODE_OAUTH_TOKEN",)

#: The tool surface, as an exact list with a reason per entry, because this layer covers the threats
#: a mount set cannot. `Task` is absent because OQ1 removed the driver session, so the adjudicator is
#: a top-level session with no subagent to spawn — a real narrowing, not a formality. `Bash`,
#: `WebFetch` and `WebSearch` are absent, which is what leaves no per-call decision for a hook to
#: make on this path (the finding behind OQ6).
ALLOWED_TOOLS: tuple[str, ...] = ("Read", "Write")


@dataclasses.dataclass(frozen=True)
class Mount:
    """One bind mount. ``host`` is a real host path; ``container`` comes from the map above."""

    host: pathlib.Path
    container: str
    writable: bool

    def as_engine_pair(self) -> tuple[pathlib.Path, str]:
        """The shape the engine's ``extra_ro_mounts`` / ``writable_mounts`` params take."""
        return (self.host, self.container)


@dataclasses.dataclass(frozen=True)
class StageMounts:
    """The mount set for one ``(stage, claim, version)``, plus what the session is told about it."""

    stage: str
    ro: tuple[Mount, ...]
    rw: tuple[Mount, ...]
    workdir: str
    add_dirs: tuple[str, ...]

    def container_paths(self) -> tuple[str, ...]:
        return tuple(m.container for m in self.ro + self.rw)


def version_snapshot_dir(
    runs_root: pathlib.Path, run_id: str, version: str
) -> pathlib.Path:
    """The read-only snapshot of one program version — the cwd the session runs in (2a).

    Version-addressed rather than a single ``current`` directory: with one shared directory, round
    5's adjudicator runs in round 1's folder on top of round 1's verdict, which is the contamination
    the per-version path removes.
    """
    return runs_root / run_id / f"program-{version}"


def stage_mount_set(
    *,
    stage: str,
    profile,
    claim,
    snapshot_dir: pathlib.Path,
    trace_dir: pathlib.Path,
    paper_dir: pathlib.Path | None = None,
) -> StageMounts:
    """Derive one stage's mount set. Raises :class:`ValueError` for a stage with no specified set.

    The per-stage split is the whole reason this is keyed on the stage: under a three-stage profile
    the extractor produces evidence *from the source*, so it needs the paper mounted, while the
    adjudicator reads the finished envelope and must not get it. Under ``retrieval`` the evidence is
    produced by ordinary Python beforehand, which is the only reason one mount set has sufficed.
    """
    profile = profiles_mod.get(profile) if isinstance(profile, str) else profile

    program = Mount(snapshot_dir, CONTAINER_PROGRAM, writable=False)
    staging = Mount(claim.staging_dir, CONTAINER_STAGING, writable=True)
    trace = Mount(trace_dir, CONTAINER_TRACE, writable=True)

    if stage == "adjudicator":
        # No paper, deliberately and permanently.
        return StageMounts(
            stage=stage,
            ro=(program,),
            rw=(staging, trace),
            workdir=CONTAINER_PROGRAM,
            add_dirs=(CONTAINER_STAGING,),
        )

    if stage == "extractor":
        if profile.evidence_producer != "extractor":
            raise ValueError(
                f"profile {profile.name!r} produces evidence with {profile.evidence_producer!r}, "
                "so it dispatches no extractor stage; a mount set here would describe a dispatch "
                "that never happens"
            )
        if paper_dir is None:
            raise ValueError(
                "the extractor stage reads the source paper, so it needs paper_dir; refusing "
                "rather than mounting nothing and letting the session fail as a model error"
            )
        return StageMounts(
            stage=stage,
            ro=(program, Mount(paper_dir, CONTAINER_PAPER, writable=False)),
            rw=(staging, trace),
            workdir=CONTAINER_PROGRAM,
            add_dirs=(CONTAINER_STAGING, CONTAINER_PAPER),
        )

    if stage == "verifier":
        # Spot-checks the adjudicator's verdict against the staged evidence. Same reason as the
        # adjudicator for not getting the paper.
        return StageMounts(
            stage=stage,
            ro=(program,),
            rw=(staging, trace),
            workdir=CONTAINER_PROGRAM,
            add_dirs=(CONTAINER_STAGING,),
        )

    raise ValueError(f"no mount set is specified for stage {stage!r}")


# =================================================================================================
# Predicates — the `-> str | None` problem idiom, after `dispatcher.val_isolation_problem`
# =================================================================================================


def unspecified_stage_problem(profile) -> str | None:
    """Would this profile dispatch a stage with no implementation? Delegates, by design.

    ``profiles.unrunnable_reason`` already refuses this at preflight, before any spend, and
    ``DEFAULT_PROFILE`` is itself an unrunnable three-stage profile so the check fires in practice
    today. The requirement the container work carries is therefore **negative**: do not bypass or
    relocate that check. This wrapper exists so a caller reaching for a stage gate finds the
    existing one instead of writing a second.
    """
    return profiles_mod.unrunnable_reason(profile)


def inner_command_host_leak(inner_command: list[str]) -> str | None:
    """Does the command handed to the session name a host path? Returns a problem, or None.

    ⚠ Scoped to the *inner* command — the ``claude ...`` argv and the rendered prompt — and not to
    the whole docker argv, because the host side of every ``-v`` flag is a host path necessarily.
    Checking the whole argv would make this either vacuous (if it allowed them) or unsatisfiable (if
    it did not), and either way it would stop being the check it is named for: that nothing the
    *session* is told to open is a path that does not exist inside its container.
    """
    for arg in inner_command:
        for marker in HOST_PATH_MARKERS:
            if marker in arg:
                return (
                    f"the command handed to the session contains the host path marker {marker!r} "
                    f"in {arg!r}; that path does not resolve inside the container, so the dispatch "
                    "fails as what looks like a model error"
                )
    return None


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


# =================================================================================================
# The prefix factory (1c) — one per dispatch, keyed on (stage, claim, version)
# =================================================================================================


def inner_command(
    *,
    mounts: StageMounts,
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
    for add_dir in mounts.add_dirs:
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


#: The egress shape this path is meant to end up on: a host allowlist naming exactly what the
#: program legitimately needs. Under `retrieval` -- the only runnable profile -- the evidence is
#: produced mechanically beforehand, so the adjudicator needs no literature APIs and the list is a
#: single host. One permitted destination is about as provable as an egress boundary gets.
#:
#: Not yet reachable: see the note in `dispatch_prefix` for the one engine addition it waits on.
TARGET_EGRESS = "host-allowlist"

#: What the engine calls the unrestricted policy. Named here so a reader of this module does not
#: have to know that `"open"` means "no egress restriction at all".
UNRESTRICTED_EGRESS = "open"


def dispatch_prefix(
    *,
    stage: str,
    profile,
    claim,
    snapshot_dir: pathlib.Path,
    trace_dir: pathlib.Path,
    image: str,
    network_policy: str,
    paper_dir: pathlib.Path | None = None,
    container_user: str | None = None,
    build=None,
) -> list[str]:
    """One dispatch's docker prefix, composed from the engine's renderer.

    ``build`` is injectable so the selftests can assert on real argv without the engine present and
    without a production-reachable branch that disables the boundary (OQ7: an injected fake, not an
    opt-out flag).
    """
    mounts = stage_mount_set(
        stage=stage,
        profile=profile,
        claim=claim,
        snapshot_dir=snapshot_dir,
        trace_dir=trace_dir,
        paper_dir=paper_dir,
    )
    builder = build or _import_engine()
    return builder(
        # ⚠ **The target is a host allowlist, not this.** `"open"` is plain bridge networking; the
        # engine files it under `_UNRESTRICTED_NETWORK_POLICIES` and says it "seals nothing on the
        # network axis" (`docker_prefix.py:49-54`). It was built for crc, whose justification --
        # "its dataset is private, so the data-leakage risk ... doesn't apply" -- does not transfer
        # to a program whose entire purpose is that it must not reach the gold labels. It also makes
        # the plan's own egress gate unsatisfiable: "an outbound request to a non-allowlisted host
        # must fail" cannot pass when there is no non-allowlisted host.
        #
        # The replacement is `HostAllowlistNetworkStack(allowed_hosts=[<the API host>])` -- already
        # built, already run for real by rad-eval, and it takes no `adc_path` at all, so the
        # credential-free shape comes free rather than needing the `None` trap below.
        #
        # ⚠ Blocked on one engine addition, NOT on a decision (Phil, 2026-09-16): the stack fixes its
        # command in `__init__` from a single mount set while creating the network and sidecar in
        # `__enter__`, so one stack serves one container -- a sidecar per dispatch at 561 dispatches.
        # Rendering further dispatches onto a standing network is item 7 of
        # `agentic-label-opt/docs/plans/2026-09-16-contained-nested-sessions.md`. Switch here when it
        # lands; until then this is a recorded stand-in, not a choice.
        network_policy=network_policy,
        image_tag=image,
        # ⚠ Explicit None. The default is a real credential path (`gcp_credentials.py:35`), so
        # *omitting* this argument is what grants the credential, not what withholds it.
        adc_path=None,
        extra_ro_mounts=tuple(m.as_engine_pair() for m in mounts.ro),
        writable_mounts=tuple(m.as_engine_pair() for m in mounts.rw),
        workdir=mounts.workdir,
        container_user=container_user,
        # No editing agent on this path at all — the program does not edit itself; the optimizer
        # does, in its own container (1e).
        edit_agent_mounts=None,
    )


# =================================================================================================
# Step 0a — the free dry run. No container started, no model called, nothing spent.
# =================================================================================================


def _fake_builder(calls: list[dict]):
    """A stand-in renderer that records what it was asked for and emits a docker-shaped argv.

    Used for the checks that must hold with or without an engine checkout. The engine-backed run
    below asserts the same properties against the real renderer.
    """

    def build(**kw):
        calls.append(kw)
        argv = ["docker", "run", "--rm"]
        for host, container in kw.get("extra_ro_mounts") or ():
            argv += ["-v", f"{host}:{container}:ro"]
        for host, container in kw.get("writable_mounts") or ():
            argv += ["-v", f"{host}:{container}:rw"]
        argv += ["--network", str(kw["network_policy"])]
        for name in ENV_ALLOWLIST:
            argv += ["--env", name]
        if kw.get("container_user"):
            argv += ["-u", str(kw["container_user"])]
        argv += ["-w", str(kw["workdir"]), str(kw["image_tag"])]
        return argv

    return build


def _dry_run_matrix(build):
    """Render every ``(profile, stage, claim, version)`` dispatch. Returns rows and refusals."""
    claims = [
        _claim("C001", "smith2020", REPO_ROOT / "staging" / "C001"),
        _claim("C002", "jones2021", REPO_ROOT / "staging" / "C002"),
    ]
    versions = ["v0", "v1"]
    runs_root = REPO_ROOT / "runs"

    rows: list[dict] = []
    refusals: list[dict] = []

    for profile in (profiles_mod.RETRIEVAL, profiles_mod.AGENTIC, profiles_mod.PAPERCLIP):
        refusal = unspecified_stage_problem(profile.name)
        for stage in profile.stages:
            specified = stage in profiles_mod.IMPLEMENTED_STAGES
            if not specified:
                refusals.append(
                    {"profile": profile.name, "stage": stage, "refusal": refusal}
                )
                continue
            for claim in claims:
                for version in versions:
                    snapshot = version_snapshot_dir(runs_root, "run_dry", version)
                    trace = runs_root / "run_dry" / "traces" / claim.claim_id
                    mounts = stage_mount_set(
                        stage=stage,
                        profile=profile,
                        claim=claim,
                        snapshot_dir=snapshot,
                        trace_dir=trace,
                        paper_dir=None,
                    )
                    prefix = dispatch_prefix(
                        stage=stage,
                        profile=profile,
                        claim=claim,
                        snapshot_dir=snapshot,
                        trace_dir=trace,
                        image="ghcr.io/example/paper-trail@sha256:" + "0" * 64,
                        network_policy=UNRESTRICTED_EGRESS,
                        build=build,
                    )
                    prompt = (
                        f"Adjudicate {claim.claim_id} using the evidence envelope at "
                        f"{CONTAINER_STAGING}/ledger/evidence/{claim.claim_id}.json "
                        f"and the rubric under {CONTAINER_PROGRAM}."
                    )
                    inner = inner_command(
                        mounts=mounts,
                        prompt=prompt,
                        model="haiku",
                        max_budget_usd=0.5,
                    )
                    rows.append(
                        {
                            "profile": profile.name,
                            "stage": stage,
                            "claim": claim.claim_id,
                            "version": version,
                            "mounts": mounts,
                            "prefix": prefix,
                            "inner": inner,
                            "full": prefix + inner,
                        }
                    )
    return rows, refusals


def _claim(claim_id: str, citekey: str, staging_dir: pathlib.Path):
    """A minimal stand-in for ``adapter.ClaimRecord`` — importing adapter here would be circular."""

    @dataclasses.dataclass(frozen=True)
    class _C:
        claim_id: str
        citekey: str
        staging_dir: pathlib.Path
        source_mode: str = "sarol_corpus"

    return _C(claim_id, citekey, staging_dir)


def _selftest() -> int:
    calls: list[dict] = []
    rows, refusals = _dry_run_matrix(_fake_builder(calls))

    prefixes = [tuple(r["prefix"]) for r in rows]
    inners = [tuple(r["inner"]) for r in rows]

    adjudicator_rows = [r for r in rows if r["stage"] == "adjudicator"]

    # Engine-backed rendering: the same properties against the real renderer, which is what
    # production will call. Refuses rather than skipping — there is no argv to assert on without it.
    engine_ok, engine_note = True, ""
    try:
        real_build = _import_engine()
    except Exception as exc:  # pragma: no cover - depends on the machine
        engine_ok, engine_note = False, f"{type(exc).__name__}: {exc}"
        engine_rows = []
    else:
        engine_rows, _ = _dry_run_matrix(real_build)

    checks: list[tuple[str, bool]] = [
        # -- the matrix itself ---------------------------------------------------------------------
        (
            "every profile-and-stage pair is either rendered or refused, none silently skipped",
            len(rows) + len(refusals) > 0
            and all(r["refusal"] for r in refusals)
            and sum(len(profiles_mod.get(p).stages) for p in ("retrieval", "agentic", "paperclip"))
            == len({(r["profile"], r["stage"]) for r in rows})
            + len({(r["profile"], r["stage"]) for r in refusals}),
        ),
        (
            "the rendered matrix is 3 profiles x 2 claims x 2 versions on the one implemented stage",
            len(rows) == 12,
        ),
        (
            "...and the unimplemented stages are the four the three-stage profiles ask for",
            len(refusals) == 4
            and {r["stage"] for r in refusals} == {"extractor", "verifier"},
        ),
        # -- no host path reaches the session (the V2d defect class) -------------------------------
        (
            "no command handed to a session names a host path",
            all(inner_command_host_leak(r["inner"]) is None for r in rows),
        ),
        (
            "...and the check is not vacuous: a host path in the prompt is caught",
            inner_command_host_leak(["claude", "-p", "read /Users/someone/gold.json"]) is not None,
        ),
        (
            "...while a container path is not flagged",
            inner_command_host_leak(["claude", "-p", f"read {CONTAINER_STAGING}/x.json"]) is None,
        ),
        (
            "every mount's container side comes from the path map",
            all(
                set(r["mounts"].container_paths())
                <= {CONTAINER_PROGRAM, CONTAINER_STAGING, CONTAINER_TRACE, CONTAINER_PAPER}
                for r in rows
            ),
        ),
        (
            "every --add-dir is a container path",
            all(
                all(d.startswith("/workspace/") for d in r["mounts"].add_dirs) for r in rows
            ),
        ),
        # -- one prefix per dispatch (V2d) ---------------------------------------------------------
        # The axes that must not collide are the claim and the program version (V2d). The profile
        # is deliberately NOT one of them: the adjudicator's mount set does not depend on which
        # profile dispatched it, so two profiles running the same stage on the same claim and
        # version rendering the same prefix is correct, and asserted as such just below.
        (
            "no two dispatches of one stage share a prefix across claim and version",
            len({(r["stage"], r["claim"], r["version"]): None for r in rows})
            == len({(r["stage"], r["claim"], r["version"], tuple(r["prefix"])) for r in rows}),
        ),
        (
            "...and the same holds for the inner command",
            len({(r["stage"], r["claim"], r["version"]): None for r in rows})
            == len({(r["stage"], r["claim"], r["version"], tuple(r["inner"])) for r in rows}),
        ),
        (
            "...so the four distinct claim-and-version dispatches render four distinct prefixes",
            len({tuple(r["prefix"]) for r in rows}) == 4,
        ),
        (
            "two profiles dispatching the same stage, claim and version agree, which is intended",
            len({tuple(r["prefix"]) for r in rows}) < len(prefixes)
            and len({tuple(r["inner"]) for r in rows}) < len(inners),
        ),
        (
            "...because the program mount moves with the version",
            len({tuple(m.host for m in r["mounts"].ro) for r in rows}) == 2,
        ),
        (
            "...and the staging mount moves with the claim",
            len({r["mounts"].rw[0].host for r in rows}) == 2,
        ),
        (
            "...so a v0 dispatch never points at v1's bytes",
            all(
                r["version"] in str(r["mounts"].ro[0].host)
                for r in rows
            ),
        ),
        # -- the tool surface ----------------------------------------------------------------------
        (
            "Task is absent from every allowlist, since OQ1 removed the subagent",
            "Task" not in ALLOWED_TOOLS
            and all("Task" not in r["inner"] for r in rows),
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
        # -- the adjudicator never gets the paper --------------------------------------------------
        (
            "the adjudicator's mount set contains no paper mount",
            all(
                CONTAINER_PAPER not in r["mounts"].container_paths()
                for r in adjudicator_rows
            ),
        ),
        (
            "...and it gets exactly one read-only mount, the program snapshot",
            all(
                len(r["mounts"].ro) == 1 and r["mounts"].ro[0].container == CONTAINER_PROGRAM
                for r in adjudicator_rows
            ),
        ),
        (
            "the extractor does get the paper, so the split is real and not an accident",
            stage_mount_set(
                stage="extractor",
                profile=profiles_mod.AGENTIC,
                claim=_claim("C003", "k2022", REPO_ROOT / "staging" / "C003"),
                snapshot_dir=REPO_ROOT / "runs" / "r" / "program-v0",
                trace_dir=REPO_ROOT / "runs" / "r" / "traces" / "C003",
                paper_dir=REPO_ROOT / "pdfs" / "k2022",
            ).container_paths()
            == (CONTAINER_PROGRAM, CONTAINER_PAPER, CONTAINER_STAGING, CONTAINER_TRACE),
        ),
        (
            "an extractor with no paper directory is refused, not mounted empty",
            _raises(
                lambda: stage_mount_set(
                    stage="extractor",
                    profile=profiles_mod.AGENTIC,
                    claim=_claim("C004", "k2022", REPO_ROOT / "s" / "C004"),
                    snapshot_dir=REPO_ROOT / "runs" / "r" / "program-v0",
                    trace_dir=REPO_ROOT / "runs" / "r" / "t",
                    paper_dir=None,
                )
            ),
        ),
        (
            "an extractor under a mechanical profile is refused, since that dispatch never happens",
            _raises(
                lambda: stage_mount_set(
                    stage="extractor",
                    profile=profiles_mod.RETRIEVAL,
                    claim=_claim("C005", "k2022", REPO_ROOT / "s" / "C005"),
                    snapshot_dir=REPO_ROOT / "runs" / "r" / "program-v0",
                    trace_dir=REPO_ROOT / "runs" / "r" / "t",
                    paper_dir=REPO_ROOT / "pdfs" / "k2022",
                )
            ),
        ),
        ("an unknown stage has no mount set", _raises(
            lambda: stage_mount_set(
                stage="summariser",
                profile=profiles_mod.RETRIEVAL,
                claim=_claim("C006", "k2022", REPO_ROOT / "s" / "C006"),
                snapshot_dir=REPO_ROOT / "runs" / "r" / "program-v0",
                trace_dir=REPO_ROOT / "runs" / "r" / "t",
            )
        )),
        # -- the stage refusal is the existing one, not a new one ----------------------------------
        (
            "the unspecified-stage refusal is profiles.unrunnable_reason, not a second gate",
            unspecified_stage_problem("agentic") == profiles_mod.unrunnable_reason("agentic"),
        ),
        (
            "the default profile is still refused at preflight, and names its missing stages",
            (lambda r: r is not None and "extractor" in r and "verifier" in r)(
                unspecified_stage_problem(profiles_mod.DEFAULT_PROFILE)
            ),
        ),
        (
            "...while the one runnable profile is not refused",
            unspecified_stage_problem("retrieval") is None,
        ),
        # -- what we asked the engine for ----------------------------------------------------------
        # ⚠ This used to assert `network_policy == "open"` as though that were a property worth
        # having. It is the opposite: the engine files `"open"` under its unrestricted set. A gate
        # certifying the wrong answer is worse than no gate, so what is asserted now is that the
        # caller had to choose, and that the stand-in is visible rather than silent.
        (
            "the caller must state an egress policy; nothing defaults to unrestricted",
            "network_policy" in inspect.signature(dispatch_prefix).parameters
            and inspect.signature(dispatch_prefix).parameters["network_policy"].default
            is inspect.Parameter.empty,
        ),
        (
            "...and the target egress shape is recorded as a host allowlist, not this stand-in",
            TARGET_EGRESS == "host-allowlist" and UNRESTRICTED_EGRESS == "open",
        ),
        (
            "the dry run is honest about running on the unrestricted stand-in today",
            bool(calls) and all(c["network_policy"] == UNRESTRICTED_EGRESS for c in calls),
        ),
        (
            "every render passes adc_path=None explicitly, since omitting it grants a credential",
            all("adc_path" in c and c["adc_path"] is None for c in calls),
        ),
        (
            "every render declares no editing agent on the program's path",
            all(c.get("edit_agent_mounts") is None for c in calls),
        ),
        (
            "the image is pinned by digest, not by tag",
            all("@sha256:" in str(c["image_tag"]) for c in calls),
        ),
        (
            "the workdir is the read-only program snapshot",
            all(c["workdir"] == CONTAINER_PROGRAM for c in calls),
        ),
        (
            "the token is named, never valued",
            ENV_ALLOWLIST == ("CLAUDE_CODE_OAUTH_TOKEN",),
        ),
        # ⚠ The rendered command carries no credential at all today, and that is deliberate rather
        # than finished: the engine emits only `-e KEY=VALUE` (`docker_prefix.py:437`), which would
        # put the token in host argv and in the wrapper's meta.json. So nothing is passed until the
        # by-name form lands upstream — a stated prerequisite of Phase 1, not of this dry run. What
        # is assertable now is that no value leaks, so that is what is asserted.
        (
            "no rendered argv carries a token value, on this path or the engine's",
            all(
                "CLAUDE_CODE_OAUTH_TOKEN=" not in str(a)
                for r in rows + engine_rows
                for a in r["full"]
            ),
        ),
        (
            "...and no environment value of any kind is passed through as KEY=VALUE",
            all(c.get("env") in (None, {}) for c in calls),
        ),
        # -- against the real engine renderer ------------------------------------------------------
        (
            f"the engine's own renderer is reachable and rendered the matrix{engine_note and ' -- ' + engine_note}",
            engine_ok and len(engine_rows) == len(rows),
        ),
        (
            "the engine's argv starts a container and nothing else ran to find out",
            engine_ok and all(r["prefix"][:2] == ["docker", "run"] for r in engine_rows),
        ),
        (
            "the engine's argv mounts the program read-only",
            engine_ok
            and all(
                any(f":{CONTAINER_PROGRAM}:ro" in a for a in r["prefix"])
                for r in engine_rows
            ),
        ),
        (
            "the engine's argv mounts this claim's staging writable",
            engine_ok
            and all(
                any(f":{CONTAINER_STAGING}:rw" in a for a in r["prefix"])
                for r in engine_rows
            ),
        ),
        (
            "the engine renders a distinct prefix per claim and per program version",
            engine_ok
            and len({tuple(r["prefix"]) for r in engine_rows}) == 4
            and len(
                {
                    (r["stage"], r["claim"], r["version"], tuple(r["prefix"]))
                    for r in engine_rows
                }
            )
            == len({(r["stage"], r["claim"], r["version"]) for r in engine_rows}),
        ),
        (
            "no engine-rendered mount lands on a path the engine reserves for itself",
            engine_ok
            and all(
                c not in ("/workspace/program", "/workspace/writable", "/workspace/context")
                for r in engine_rows
                for c in r["mounts"].container_paths()
            ),
        ),
        (
            "nothing in the engine's argv mounts the gold or benchmark trees",
            engine_ok
            and not any(
                "gold" in a or "benchmark" in a
                for r in engine_rows
                for a in r["prefix"]
            ),
        ),
    ]

    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


def _raises(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="Step 0a: render every dispatch and assert on the argv. No container, no model.",
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
        try:
            build = _import_engine()
        except Exception as exc:
            print(f"# engine unavailable ({type(exc).__name__}), showing the stand-in shape: {exc}")
            build = _fake_builder([])
        rows, refusals = _dry_run_matrix(build)
        for r in rows:
            print(f"\n=== {r['profile']} / {r['stage']} / {r['claim']} / {r['version']} ===")
            print(" ".join(str(a) for a in r["full"]))
        for r in refusals:
            print(f"\n=== {r['profile']} / {r['stage']} === REFUSED: {r['refusal']}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
