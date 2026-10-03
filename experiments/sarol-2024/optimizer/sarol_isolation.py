"""paper-trail's values for its sealed sessions, and the engine on the import path.

Until PT-A (2026-10-01) this module was ``isolation.py`` and held paper-trail's own container machinery:
the grant builder, the per-batch boundary, the mount parser, the configuration pin, the digest code and
the grader argv. All of that is now the shared engine's (``agentic-label-opt``: S1 sealed sessions, S2
seal proof and setup pins, PR program runner, A contained optimizer), and paper-trail supplies values:

* **the grader's tools** (``ALLOWED_TOOLS``) and **hosts** (``EGRESS_ALLOWED_HOSTS``), used by
  ``sarol_program.session_template`` and ``sarol_optimizer``;
* **the token's name** (``ENV_ALLOWLIST``), passed by name, never by value;
* **the grader image tag** (``SHIPPING_IMAGE_TAG``), resolved to ``name:version@sha256:…`` by the engine.

It was renamed because it shared its name with the engine's ``isolation`` package, which made every
engine import a path-and-module dance that call-time imports inside the engine could not survive
(build design D8). Where each removed check is covered now: ``planning/paper-trail/2026-09-30-adopt-
engine-sessions/deleted-checks-coverage.md``.

    python3 experiments/sarol-2024/optimizer/sarol_isolation.py --selftest
"""

from __future__ import annotations

import contextlib
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
# This folder and the experiment's scripts folder, which the old module also put on the path and
# several modules import from by bare name (`stage_claim`, `check_run_scope`, `parse_verdict`).
for _p in (_HERE, _HERE.parent / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import engine_pin  # noqa: E402

#: The repository root, for callers that resolve paths against it.
REPO_ROOT = _HERE.parents[2]

#: The token, passed by NAME only (``docker run --env NAME``): its value never enters argv or a log.
ENV_ALLOWLIST: tuple[str, ...] = ("CLAUDE_CODE_OAUTH_TOKEN",)

#: The grader's tool surface, an exact list. ``Task`` is absent because the adjudicator is a top-level
#: session with no subagent to spawn (OQ1); ``Bash``, ``WebFetch`` and ``WebSearch`` are absent, which
#: leaves no per-call decision for a hook to make on this path (OQ6). Under the engine's deny-by-default
#: posture anything else that would prompt is refused.
ALLOWED_TOOLS: tuple[str, ...] = ("Read", "Write")

#: The hosts a sealed session may reach. Named explicitly (the 2026-07-20 ruling: paper-trail's
#: allowlist "must name Anthropic's API explicitly, not leave it implicit"). Under ``retrieval`` the
#: evidence is produced mechanically beforehand, so one host is the whole list.
EGRESS_ALLOWED_HOSTS: tuple[str, ...] = ("api.anthropic.com",)

#: The grader image, built from the engine's isolation Dockerfile. The tag names the Claude Code version
#: inside it; the engine resolves it to ``name:version@sha256:…`` and checks the claim.
SHIPPING_IMAGE_TAG = "paper-trail-isolation:2.1.277"

#: A digest-form stand-in for selftests that never start a container.
FAKE_IMAGE = SHIPPING_IMAGE_TAG + "@sha256:" + "0" * 64


def engine_path() -> pathlib.Path:
    """Delegates to :mod:`engine_pin`, the single definition."""
    return engine_pin.engine_path()


def engine_on_path() -> pathlib.Path:
    """Put the pinned engine checkout on ``sys.path`` (once) and return it. Refuses an engine that
    does not contain the pin or lacks a capability paper-trail builds on (``engine_pin``)."""
    path = engine_pin.require_engine(probe_capabilities=True)
    if str(path) not in sys.path:
        # APPENDED, never put in front: the engine checkout's root holds its own `adapter.py`, which
        # in front of this folder would shadow paper-trail's `adapter` for every later bare import.
        sys.path.append(str(path))
    # ...which means an engine installed elsewhere on the path would win silently, at an unpinned
    # version. Refuse that rather than run on it.
    import engine as _engine  # noqa: PLC0415
    import isolation as _isolation  # noqa: PLC0415

    for mod in (_engine, _isolation):
        where = pathlib.Path(getattr(mod, "__file__", None) or next(iter(getattr(mod, "__path__", [""])))).resolve()
        if pathlib.Path(path).resolve() not in where.parents:
            raise RuntimeError(
                f"`{mod.__name__}` imports from {where}, not from the pinned engine checkout {path}; "
                "another copy of agentic-label-opt is installed on this Python path. Remove it, or run "
                "with that copy's directory off the path"
            )
    return path


@contextlib.contextmanager
def engine_importable():
    """Kept for callers written against the old guard: now just :func:`engine_on_path`."""
    yield engine_on_path()


def _selftest() -> int:
    import os  # noqa: PLC0415

    engine_on_path()
    from isolation import sealed_session as ss  # noqa: PLC0415
    from isolation.contained_argv import build_contained_argv  # noqa: PLC0415
    from isolation.image_pin import image_ref_problem  # noqa: PLC0415
    from isolation.setup_fingerprint import setup_fingerprint  # noqa: PLC0415

    import adapter  # noqa: PLC0415, F401 -- fully loaded before sarol_program, which reads it at import
    import sarol_program  # noqa: PLC0415

    os.environ.setdefault(ENV_ALLOWLIST[0], "selftest-token")
    d = sarol_program.session_template(model="haiku", image=FAKE_IMAGE, transcript_dir=None,
                                       expected_fingerprint=ss.UNPINNED)
    argv = build_contained_argv(posture=d.posture, scope=d.scope, prompt="p", model=d.model, tools=d.tools,
                                allowed_tools=d.allowed_tools, max_budget_usd=2.0, extra_host_paths=())
    fp = setup_fingerprint(d)
    checks = [
        ("the grader's tools are exactly Read and Write", ALLOWED_TOOLS == ("Read", "Write")),
        ("...so Task, Bash, WebFetch and WebSearch are absent", not {"Task", "Bash", "WebFetch", "WebSearch"} & set(ALLOWED_TOOLS)),
        ("one allowed host, Anthropic's API, named explicitly with no wildcard",
         EGRESS_ALLOWED_HOSTS == ("api.anthropic.com",) and not any("*" in h for h in EGRESS_ALLOWED_HOSTS)),
        ("the token is the only name passed through", ENV_ALLOWLIST == ("CLAUDE_CODE_OAUTH_TOKEN",)),
        ("the grader image tag names the Claude Code version inside it", SHIPPING_IMAGE_TAG.rsplit(":", 1)[1].count(".") == 2),
        ("the selftest stand-in is in the engine's image form", image_ref_problem(FAKE_IMAGE) is None),
        ("the grader session is deny-by-default", d.posture == "deny-by-default"),
        ("...with no permission skip on the argv the engine builds for it", "--dangerously-skip-permissions" not in argv),
        ("...no session written to disk", "--no-session-persistence" in argv),
        ("...the prompt-caching flag kept off (it relocates rather than removes)",
         "--exclude-dynamic-system-prompt-sections" not in argv),
        ("...a hard budget cap on every session", "--max-budget-usd" in argv),
        # The engine adds the proxy variables and HOME as values of its own; the token it passes with
        # `--env NAME` (refusing a description that carries its value, `sealed_session.py:257`).
        ("...and the token reaches the container by name, with no value in the description",
         "CLAUDE_CODE_OAUTH_TOKEN" in fp["env_names"] and not any(k == "CLAUDE_CODE_OAUTH_TOKEN" for k, _v in d.env)),
        ("...on the Anthropic profile with exactly the one host", fp["profile"] == {"kind": "anthropic", "hosts": ["api.anthropic.com"]}),
    ]
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("usage: sarol_isolation.py --selftest")
