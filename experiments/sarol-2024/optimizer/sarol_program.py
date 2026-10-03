"""paper-trail's program on the engine's program runner (PT-A steps 2-3).

Plan: ``planning/paper-trail/2026-09-30-adopt-engine-sessions.md`` (build design D1-D5), consumer half of
the engine's ``planning/agentic-label-opt/2026-09-23-engine-program-runner.md`` (PR).

The graders used to run through paper-trail's own container code: a per-staging-root grant, a boundary
opened per batch, an archive-and-clear of the answer slots, a stale-answer check, an incremental manifest.
All of that is now the engine's ``ProgramRunner``: one sealed session per claim, the program mounted
read-only at ``/workspace/program``, and only that claim's own folder writable at ``/workspace/call``.
What stays here is what is genuinely paper-trail's:

- **which calls** a batch makes (one per claim) and **what each call is given** (its staged evidence,
  copied into the call folder, the mechanical evidence envelope, and the rendered adjudicator prompt);
- **the canary**, a one-claim pass run before every pass (D4);
- **the manifest**, in the record shape ``SarolScorer`` already reads (D5);
- **the forbidden list**, as the engine's ``Forbidden`` entries;
- **the session template**: deny-by-default, ``Read`` and ``Write`` only, the Anthropic profile with the
  subscription token passed by name, and the grader image by digest.

⚠ **The prompt is rendered while staging, not in the prompt builder (D3).** The engine hands the prompt
builder container paths only, but ``dispatch_prompt.render`` reads the evidence envelope and the
template from the host. ``stage()`` has the host call folder and the materialized program, so it renders
there, writes the audit copy into the call folder (``ledger/prompts/<claim>.md``, as before), and the
prompt builder returns what it rendered.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import adapter
import dispatch_prompt
import evidence_producers
import profiles as profiles_mod
import sarol_isolation as iso
import stage_claim
import validate_sarol

iso.engine_on_path()

from engine.schemas import RunInputs  # noqa: E402
from isolation import sealed_session as ss  # noqa: E402
from isolation.pass_outputs import Call, PassStopped  # noqa: E402
from isolation.program_runner import CALL_CONTAINER_PATH, ProgramRunner, ProgramSpec  # noqa: E402
from isolation.session_scope import DEFAULT_WORKDIR, Forbidden, SessionScope  # noqa: E402

#: The token's NAME. Its value is read at call time and passed by name; it never enters a description.
TOKEN_ENV_NAME = "CLAUDE_CODE_OAUTH_TOKEN"

#: Part of the pass key: bump it when the way a call's prompt is built changes, so an archived pass
#: built the old way is never returned for the new one.
PROMPT_TAG = "sarol-adjudicator-v1"

#: The one stage paper-trail's runnable profiles dispatch. The engine runs one session per stage and
#: the stages must write different files.
STAGES: tuple[str, ...] = ("adjudicator",)

#: What a call produces, relative to its folder: the verdict file.
OUTPUT_PATTERNS: tuple[str, ...] = ("ledger/claims/*.json",)

#: Where the materialized program is mounted, read-only, and what ``{{spec_root}}`` names.
SPEC_ROOT = DEFAULT_WORKDIR

#: The rubric the program ran under, inside a materialized tree.
RUBRIC_REL = "experiments/sarol-2024/specs/verdict_schema_sarol.md"

#: Folders a call folder never copies from a claim's staging tree: a previous pass's answers live
#: under ``ledger/``, and copying them in is the Sep 21 contamination this layout exists to prevent.
_NEVER_STAGED = ("ledger",)


def verdict_rel(claim_id: str) -> str:
    return f"ledger/claims/{claim_id}.json"


# =================================================================================================
# The forbidden list
# =================================================================================================


def forbidden_list(
    *, repo_root: pathlib.Path = adapter.REPO_ROOT, extra: Sequence[Forbidden] = ()
) -> tuple[Forbidden, ...]:
    """What no grader may reach, as the engine's strict ``Forbidden`` entries (S2).

    Gold and the benchmark are the secret roots: no grant inside them at all. The test split lives in
    the benchmark folder (``claims-test.jsonl``), so it is covered wholesale; moving it to its own
    sealed folder (PT4) is deferred (Phil 2026-09-30). The optimizer's notes (findings,
    ``meta-learnings.md``, context) are the other principal's; ``.git`` holds every version; the
    account's ``.claude`` holds the subscription token. The engine adds the run's output root itself
    (``Forbidden(root, allowed_inside=("live",))``), so it is not repeated here; ``extra`` carries the
    scorer's and the optimizer's own roots, which the driver knows.
    """
    here = pathlib.Path(__file__).resolve().parent
    gold_parent = stage_claim.GOLD_ROOT.parent
    bench_parent = stage_claim.BENCH_DIR.parent
    git_dir = pathlib.Path(repo_root) / ".git"
    entries = [
        Forbidden(gold_parent, representatives=("sarol-2024/train", "sarol-2024/dev")),
        Forbidden(
            bench_parent,
            representatives=(
                "sarol-2024/corpus.jsonl",
                "sarol-2024/claims-train.jsonl",
                "sarol-2024/claims-dev.jsonl",
                "sarol-2024/claims-test.jsonl",
            ),
        ),
        Forbidden(here / "findings", representatives=("iter-1.md",)),
        Forbidden(here / "context", representatives=("playbook.md",)),
        # A file entry names itself with "" as its representative (S2/A: every entry carries one).
        Forbidden(here / "meta-learnings.md", representatives=("",)),
        Forbidden(git_dir, representatives=("",) if git_dir.is_file() else ("HEAD",)),
        Forbidden(pathlib.Path.home() / ".claude", representatives=(".credentials.json",)),
        # The subscription token's file: never mounted, named so the seal replay proves it unreachable.
        Forbidden(pathlib.Path.home() / ".paper-trail" / "credentials.env", representatives=("",)),
        *extra,
    ]
    return tuple(entries)


# =================================================================================================
# The session template
# =================================================================================================


def grader_image() -> str:
    """The grader image as ``name:version@sha256:…`` (S2's one form), from the tag this code ships."""
    from isolation.image_pin import image_ref  # noqa: PLC0415

    return image_ref(iso.SHIPPING_IMAGE_TAG)


def session_template(
    *,
    model: str,
    image: str,
    transcript_dir: pathlib.Path | None,
    expected_fingerprint: str,
) -> ss.SessionDescription:
    """The description every grader session is built from. The runner fills in the grant, limits and
    kind per call; the placeholder grant here is never rendered."""
    return ss.SessionDescription(
        scope=SessionScope(program=adapter.REPO_ROOT, denied=(pathlib.Path("/nonexistent-placeholder"),)),
        posture="deny-by-default",
        tools=iso.ALLOWED_TOOLS,
        allowed_tools=iso.ALLOWED_TOOLS,
        model=model,
        image=image,
        profile=ss.AnthropicApiProfile(token_env_name=TOKEN_ENV_NAME, allowed_hosts=iso.EGRESS_ALLOWED_HOSTS),
        credential=ss.NO_CREDENTIAL,
        transcript_dir=transcript_dir,
        kind="program",
        expected_fingerprint=expected_fingerprint,
    )


# =================================================================================================
# The program
# =================================================================================================


@dataclass
class SarolProgram:
    """paper-trail's half of a ``ProgramSpec``: calls, staging, prompt, stamp, canary, manifest.

    One instance serves one runner. It remembers the materialized program the current pass runs on
    (``before_pass`` records it) and the prompts ``stage()`` rendered, keyed by pass and call.
    """

    profile: Any
    model: str
    canary: "adapter.CanarySpec | None" = None
    #: The grader image (``name:version@sha256:…``), recorded in the manifest as the instrument the
    #: claims ran on. ``program_runner`` sets it.
    image: str | None = None
    #: Refuse a version whose tree lacks the frozen command file (manifest entry #10). It is no longer
    #: what gets dispatched, but its absence means the freeze is incomplete.
    require_command: bool = True
    command_name: str = "sarol-eval-item"
    per_call_timeout_seconds: int = 900
    per_call_max_budget_usd: float = 2.0
    max_concurrent: int = 1
    _program: pathlib.Path | None = field(default=None, init=False, repr=False)
    _prompts: dict = field(default_factory=dict, init=False, repr=False)
    _mu: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    #: What the last canary saw, for the manifest. ``None`` when no canary ran this pass.
    canary_record: "dict | None" = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.profile = profiles_mod.get(self.profile)
        unrunnable = profiles_mod.unrunnable_reason(self.profile) if hasattr(profiles_mod, "unrunnable_reason") else None
        if unrunnable:
            raise ValueError(f"refusing profile {self.profile.name!r}: {unrunnable}")
        if tuple(self.profile.stages) != STAGES:
            raise ValueError(
                f"profile {self.profile.name!r} dispatches {list(self.profile.stages)}; the program "
                f"runner path supports {list(STAGES)} only (the other stages have no prompt to render)"
            )

    # -- the spec -----------------------------------------------------------------------------

    def spec(self, *, forbidden: Sequence[Forbidden]) -> ProgramSpec:
        return ProgramSpec(
            calls_for=self.calls_for,
            stage=self.stage,
            prompt=self.prompt,
            stages=STAGES,
            output_patterns=OUTPUT_PATTERNS,
            prompt_tag=PROMPT_TAG,
            max_concurrent=max(1, int(self.max_concurrent)),
            timeout_seconds=int(self.per_call_timeout_seconds),
            max_budget_usd=float(self.per_call_max_budget_usd),
            token_env_name=TOKEN_ENV_NAME,
            read_stamp=self.read_stamp,
            before_pass=self.before_pass,
            summarize=self.summarize,
            forbidden=tuple(forbidden),
        )

    # -- calls --------------------------------------------------------------------------------

    def calls_for(self, inputs: RunInputs) -> list[Call]:
        """One call per claim, its id the claim id. Duplicates and an empty batch are refused by the
        engine (``check_calls``), which is where paper-trail's ``DUPLICATE_CLAIM_IDS`` moved."""
        return [
            Call(
                c.claim_id,
                {"claim_id": c.claim_id, "citekey": c.citekey, "staging_dir": str(c.staging_dir)},
            )
            for c in adapter.load_batch(inputs.input_ref)
        ]

    def stage(self, call: Call, folder: pathlib.Path, pass_id: str) -> None:
        """Copy the claim's staged evidence in, write the evidence envelope, render the prompt.

        Raises ``PassStopped("stage_failed: …")`` on any failure: the pass stops with a reason and is
        never scored, which matches the old behaviour (one claim's producer failure made the batch a
        ``program_error`` the scorer refused) without a bare traceback.
        """
        claim_id = call.call_id
        try:
            if self._program is None:
                raise RuntimeError("no materialized program recorded for this pass (before_pass did not run)")
            source = pathlib.Path(call.payload["staging_dir"])
            if not source.is_dir():
                raise FileNotFoundError(f"the claim's staging folder {source} does not exist")
            shutil.copytree(
                source, folder, dirs_exist_ok=True,
                ignore=lambda d, names: [n for n in names if pathlib.Path(d) == source and n in _NEVER_STAGED],
            )
            producer = evidence_producers.for_profile(self.profile)
            if producer is not None:
                producer(folder, claim_id, run_id=pass_id, profile=self.profile)
            prompt = dispatch_prompt.render(
                staging_dir=folder,
                claim_id=claim_id,
                run_id=pass_id,
                run_output_dir=CALL_CONTAINER_PATH,
                spec_root=SPEC_ROOT,
                template_root=self._program,
            )
            dispatch_prompt.write_rendered(folder, claim_id, prompt)
        except PassStopped:
            raise
        except Exception as exc:  # noqa: BLE001 -- any staging failure stops the pass with a reason
            raise PassStopped(f"stage_failed: claim {claim_id}: {str(exc)[:300]}") from exc
        with self._mu:
            self._prompts[(pass_id, claim_id)] = prompt

    def prompt(self, call: Call, stage: str, paths, pass_id: str) -> str:
        if paths.call != CALL_CONTAINER_PATH or paths.program != SPEC_ROOT:
            raise PassStopped(
                f"stage_failed: the grant mounts the call at {paths.call!r} and the program at "
                f"{paths.program!r}; the rendered prompt names {CALL_CONTAINER_PATH} and {SPEC_ROOT}"
            )
        with self._mu:
            text = self._prompts.get((pass_id, call.call_id))
        if text is None:
            raise PassStopped(f"stage_failed: no prompt was rendered for {call.call_id} in {pass_id}")
        return text

    @staticmethod
    def read_stamp(call: Call, folder: pathlib.Path) -> str | None:
        """The pass id the adjudicator wrote into its verdict's ``run_id``."""
        path = pathlib.Path(folder) / verdict_rel(call.call_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("run_id")
        except (OSError, ValueError, AttributeError):
            return None
        return value if isinstance(value, str) else None

    # -- before the pass: record the program, run the canary ----------------------------------

    def before_pass(self, bound, inputs: RunInputs, program: pathlib.Path) -> str | None:
        """Record the program this pass runs on, then run the canary (D4). Returns a stop message
        (``canary_failed: …``) or ``None``. The canary is its own one-claim pass with hooks off, so it
        does not recurse and writes no manifest; its verdict is read from its archived call folder."""
        self._program = pathlib.Path(program)
        self.canary_record = None
        if self.require_command and not (pathlib.Path(program) / adapter.COMMAND_REL_TEMPLATE.format(name=self.command_name)).exists():
            return (
                f"nested_command_missing: /{self.command_name} is not at "
                f"{adapter.COMMAND_REL_TEMPLATE.format(name=self.command_name)} in the version being scored "
                f"({pathlib.Path(program).name}); the freeze is incomplete"
            )
        if self.canary is None:
            return None
        claim = self.canary.claim
        # The batch file only has to be readable by this process (``calls_for``); it goes in the system
        # temp folder, never beside the materialized trees the optimizer may read.
        fd, name = tempfile.mkstemp(prefix=f"sarol-canary-{inputs.batch_id}-", suffix=".json")
        os.close(fd)
        batch = pathlib.Path(name)
        batch.write_text(
            json.dumps({"claims": [{"claim_id": claim.claim_id, "citekey": claim.citekey,
                                    "staging_dir": str(claim.staging_dir)}]}),
            encoding="utf-8",
        )
        canary_inputs = RunInputs(input_ref=str(batch), batch_id=f"{inputs.batch_id}-canary", split=inputs.split)
        completed = bound.run_pass(program, canary_inputs, hooks=False)
        receipt = next((r for r in completed.receipts if r["call_id"] == claim.claim_id), None)
        record = self._record(receipt, program) if receipt is not None else None
        self.canary_record = record
        observed = ((record or {}).get("validation") or {}).get("overall_verdict")
        status = (record or {}).get("status")
        if status != "ok" or observed != self.canary.expected_verdict:
            return (
                f"canary_failed: canary {claim.claim_id} expected {self.canary.expected_verdict!r}, observed "
                f"{observed!r} (status={status}) -- the scorer or pipeline moved; numbers from this run are "
                "not comparable to earlier ones"
            )
        return None

    # -- the manifest -------------------------------------------------------------------------

    def _record(self, receipt: Mapping[str, Any], program: pathlib.Path | None) -> dict:
        """One claim's manifest record, in the shape ``SarolScorer`` reads (D5)."""
        folder = pathlib.Path(receipt["call_folder"])
        claim_id = receipt["call_id"]
        stages = {
            s.get("stage", STAGES[0]): {
                "exit_code": s.get("exit_code"),
                "cost_usd": s.get("cost_usd"),
                "duration_seconds": s.get("duration_seconds"),
                "timed_out": receipt.get("failed") == "timeout",
                "model": s.get("model"),
                "trace_ref": s.get("transcript"),
            }
            for s in receipt.get("stages", [])
        }
        record: dict[str, Any] = {
            "claim_id": claim_id,
            "staging_dir": str(folder),
            "stages": stages,
            "status": "ok",
        }
        try:
            record["citekey"] = json.loads((folder / "staging_info.json").read_text(encoding="utf-8")).get("citekey")
        except (OSError, ValueError, AttributeError):
            record["citekey"] = None
        if receipt.get("failed"):
            # A crashed or timed-out call is a miss, clearly marked (Phil 2026-09-25): the scorer
            # scores it against gold and counts it in `failed_calls`, never as a wrong answer.
            record["status"] = "failed"
            record["failed"] = receipt["failed"]
            record["detail"] = receipt.get("failure_reason")
            return record
        rubric = (pathlib.Path(program) / RUBRIC_REL) if program is not None else None
        validation = validate_sarol.validate_file(
            folder / verdict_rel(claim_id),
            expect_claim_id=claim_id,
            rubric_path=rubric,
            rollup_order=validate_sarol.load_rollup_order(rubric) if rubric is not None else None,
            harness_selector=self.profile.selector,
        )
        record["validation"] = validation.as_dict()
        record["answer_run_id"] = receipt["pass_id"]
        if not validation.ok:
            record["status"] = "invalid_output"
        return record

    def summarize(self, archive: pathlib.Path, receipts: Sequence[Mapping[str, Any]]) -> pathlib.Path:
        records = [self._record(r, self._program) for r in receipts]
        validator_counts: dict[str, int] = {}
        for rec in records:
            for key, n in ((rec.get("validation") or {}).get("error_class_counts") or {}).items():
                validator_counts[key] = validator_counts.get(key, 0) + n
        everything = records + ([self.canary_record] if self.canary_record is not None else [])
        cost = sum(float(st.get("cost_usd") or 0.0) for r in everything for st in (r.get("stages") or {}).values())
        sessions = sum(len(r.get("stages") or {}) for r in everything)
        failed = [r for r in records if r["status"] == "failed"]
        pass_record = json.loads((pathlib.Path(archive) / "pass.json").read_text(encoding="utf-8"))
        manifest = pathlib.Path(archive) / "run_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "batch_id": (pass_record.get("key") or {}).get("batch_id"),
                    "split": (pass_record.get("key") or {}).get("split"),
                    "pass_id": pass_record.get("pass_id"),
                    "profile": self.profile.name,
                    "model": next(
                        (st.get("model") for r in records for st in (r.get("stages") or {}).values() if st.get("model")),
                        None,
                    ),
                    "profile_stages": list(self.profile.stages),
                    "retrieval_k": self.profile.retrieval_k,
                    "requested_count": len(records),
                    "complete": True,
                    "claims": records,
                    "validator_error_class_counts": validator_counts,
                    "failed_calls": {
                        "count": len(failed),
                        "by_reason": {k: sum(1 for r in failed if r.get("failed") == k) for k in ("crash", "timeout")},
                    },
                    "canary": self.canary_record,
                    # The instrument the claims ran on: the grader image by digest (the Claude Code
                    # version is in its tag). The pass key also carries the setup fingerprint.
                    "container": {"image": self.image},
                    "sub_invocation_count": sessions,
                    "cost_usd": cost,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest


# =================================================================================================
# Setup pins (S2): one per session kind and platform, committed in the manifest
# =================================================================================================

#: Where the manifest keeps the pins: ``runtime_pins.isolation_config.<kind>.<platform>``.
MANIFEST_REL = "experiments/sarol-2024/program-v0/manifest.json"


def platform_key() -> str:
    from isolation.setup_fingerprint import platform_key as _pk  # noqa: PLC0415

    return _pk()


PIN_KEY = "isolation_config"


def committed_pins(repo_root: pathlib.Path = adapter.REPO_ROOT) -> dict:
    """``{"program": hash|None, "optimizer": hash|None}`` from ``git show HEAD:<manifest>``, never the
    working tree's copy (a pin the same edit can move is not a pin)."""
    from isolation.setup_fingerprint import committed_pin  # noqa: PLC0415

    return {kind: committed_pin(pathlib.Path(repo_root), MANIFEST_REL, kind=kind) for kind in ("program", "optimizer")}


def program_pin_description(runner: ProgramRunner) -> ss.SessionDescription:
    """A grader session's description as the runner builds one for a call (its ``_call_scope`` and
    ``_description``), over placeholder host folders, which the fingerprint never reads. The selftest
    holds its fingerprint to the one the runner's own sessions are given."""
    from dataclasses import replace  # noqa: PLC0415

    spec, template = runner.spec, runner.template
    folder = runner.root.root / "live" / "pin" / "calls" / "pin"
    scope = SessionScope(
        program=pathlib.Path("/pin/program"),
        readable=tuple((pathlib.Path(h), f"/workspace/ro/{name}") for h, name in spec.readable),
        writable=((folder, CALL_CONTAINER_PATH),),
        denied=(*spec.forbidden, Forbidden(runner.root.root, representatives=("live/pin/receipts",), allowed_inside=("live",))),
    )
    return replace(
        template, scope=scope, transcript_dir=None if template.transcript_dir is None else folder,
        timeout_seconds=spec.timeout_seconds, max_budget_usd=spec.max_budget_usd, kind="program", editable_patterns=(),
    )


def fingerprints(runner: ProgramRunner, optimizer, *, materialize_root: pathlib.Path) -> dict:
    """``{"program": fingerprint, "optimizer": fingerprint}`` for this run's two session kinds."""
    from isolation.setup_fingerprint import setup_fingerprint  # noqa: PLC0415

    return {
        "program": setup_fingerprint(program_pin_description(runner)),
        "optimizer": setup_fingerprint(optimizer.pin_description(materialize_root=materialize_root)),
    }


def setup_value(runner: ProgramRunner, optimizer, *, materialize_root: pathlib.Path) -> str:
    """The result field's value (``setup-v1:<sha256>``): what this run's sessions compute. The release
    builder stamps it and the loop is given it to check the stamp; the PIN each session is held to on
    entry is the real gate (S2)."""
    from isolation.setup_fingerprint import combined_value  # noqa: PLC0415

    return combined_value(fingerprints(runner, optimizer, materialize_root=materialize_root))


# =================================================================================================
# The runner the driver enters
# =================================================================================================


def program_runner(
    program: SarolProgram,
    *,
    output_root: pathlib.Path,
    materialize_root: pathlib.Path,
    image: str,
    transcript_dir: pathlib.Path | None,
    expected_fingerprint: str,
    forbidden: Sequence[Forbidden],
    **private,
) -> ProgramRunner:
    """The engine's runner for paper-trail's graders. Enter it around ``run_loop`` and pass
    ``runner.as_runner(run_id=...)`` to the loop. ``private`` is the tests' fakes only."""
    program.image = image
    return ProgramRunner(
        spec=program.spec(forbidden=forbidden),
        template=session_template(
            model=program.model, image=image, transcript_dir=transcript_dir,
            expected_fingerprint=expected_fingerprint,
        ),
        output_root=pathlib.Path(output_root),
        materialize_root=pathlib.Path(materialize_root),
        **private,
    )


def _print_pins() -> int:
    """Print the ``runtime_pins.isolation_config`` block for this platform, from the real images and
    the production wiring (``dispatcher.build_components``), to commit in the manifest."""
    import tempfile as _tempfile  # noqa: PLC0415

    import dispatcher  # noqa: PLC0415
    from isolation.setup_fingerprint import fingerprint_hash  # noqa: PLC0415

    with _tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as td:
        root = pathlib.Path(td)
        parts = dispatcher.build_components(
            max_budget_usd=1.0, train_n=1, train_output_root=root / "train", val_output_root=root / "val",
            materialize_root=root / "mat", expected_fingerprints={"program": ss.UNPINNED, "optimizer": ss.UNPINNED},
            # The production profile. The optimizer's pin covers its editable patterns, which the
            # profile narrows, so a pin is for one profile; `retrieval` is the only runnable one.
            profile="retrieval",
        )
        fps = fingerprints(parts["program_runner"], parts["optimizer"], materialize_root=root / "mat")
    key = platform_key()
    block = {PIN_KEY: {kind: {key: fingerprint_hash(fp)} for kind, fp in sorted(fps.items())}}
    print(json.dumps(block, indent=2))
    return 0


# =================================================================================================
# Selftest: real passes through the engine's runner, with the engine tests' fake sessions
# =================================================================================================


class _FakeResult:
    def __init__(self, exit_code=0, cost_usd=0.1, stderr=""):
        self.exit_code, self.cost_usd, self.stderr = exit_code, cost_usd, stderr
        self.raw_events, self.model, self.session_id = [], "claude-haiku-fake", "s"
        self.duration_seconds, self.log_dir, self.container_name, self.run_id = 0.01, None, None, None


class _FakeWorld:
    """Fake Docker, network and sessions, after the engine's ``tests/test_program_runner.py``. A
    session writes a verdict into its call folder the way the adjudicator does, unless the claim's
    behaviour says otherwise."""

    def __init__(self, verdict_label="OVERSIMPLIFY"):
        self.prompts: dict[str, str] = {}
        self.descriptions: list = []
        self.pre_existing: list[str] = []
        self.behaviour: dict[str, str] = {}
        self.verdict_label = verdict_label

    def kill(self, names, run_ids):
        return None

    def listed(self, names):
        return []

    def stack(self, description):
        world = self

        class _Stack:
            run_id = "p1-net1"
            sidecar_name = "alo-allowlist-squid-p1-net1"

            def __enter__(self):
                return self

            def close(self):
                return None

            def proxy_problem(self, hosts, *, client_leg=False):
                return None

            def squid_log_window(self, start, end):
                return []

        return _Stack()

    def session(self, description, network_stack):
        world = self
        world.descriptions.append(description)

        class _Session:
            run_id = "p1-fake"
            timings = {"sweep_seconds": 0.0, "probe_seconds": 0.0}
            probe_container_name = "alo-sealed-p1-fake-probe"
            _n = 0

            def next_container_name(self, call_name):
                return f"alo-sealed-p1-fake-{call_name}-{self._n + 1}"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def run(self, prompt, *, call_name, host_env):
                self._n += 1
                folder = pathlib.Path(description.scope.writable[0][0])
                claim_id = folder.name
                pass_id = folder.parents[1].name
                world.prompts[claim_id] = prompt
                verdict = folder / verdict_rel(claim_id)
                if verdict.exists():
                    world.pre_existing.append(claim_id)
                behaviour = world.behaviour.get(claim_id, "answer")
                if behaviour == "crash":
                    return _FakeResult(exit_code=1, stderr="Traceback: boom")
                if behaviour == "timeout":
                    return _FakeResult(exit_code=124, stderr="")  # the engine wrapper's timeout code
                body = json.loads((validate_sarol.FIXTURE_DIR / "valid_all_sarol.json").read_text(encoding="utf-8"))
                body["claim_id"] = claim_id
                body["run_id"] = pass_id
                if behaviour == "garbage":
                    verdict.parent.mkdir(parents=True, exist_ok=True)
                    verdict.write_text("{not json", encoding="utf-8")
                    return _FakeResult()
                body["overall_verdict"] = world.verdict_label
                verdict.parent.mkdir(parents=True, exist_ok=True)
                verdict.write_text(json.dumps(body), encoding="utf-8")
                result = _FakeResult()
                if description.transcript_dir is not None:
                    # The engine's wrapper writes the session's events here; the receipt records it.
                    log = pathlib.Path(description.transcript_dir)
                    log.mkdir(parents=True, exist_ok=True)
                    (log / "events.jsonl").write_text('{"type": "result"}\n', encoding="utf-8")
                    result.log_dir = str(log)
                return result

        return _Session()


def _selftest() -> int:
    import tempfile as _tempfile  # noqa: PLC0415

    os.environ.setdefault(TOKEN_ENV_NAME, "selftest-token")
    fake_image = "paper-trail-isolation:2.1.277@sha256:" + "0" * 64
    checks: list[tuple[str, bool]] = []

    with _tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as td:
        root = pathlib.Path(td)
        mat_root = root / "mat"
        program = adapter._materialized_program(mat_root, name="iter1-current")
        rubric = program / RUBRIC_REL
        rubric.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(adapter.REPO_ROOT / RUBRIC_REL, rubric)
        command = program / adapter.COMMAND_REL_TEMPLATE.format(name="sarol-eval-item")
        command.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(adapter.REPO_ROOT / "src" / "commands" / "sarol-eval-item.md", command)
        _out, batch = adapter._staged_batch(root / "staged", claim_ids=("C1", "C2", "C3"), split="train")
        claims = adapter.load_batch(batch)
        # A previous pass's answer left in the source staging tree: it must not be copied in.
        stale = pathlib.Path(claims[0].staging_dir) / verdict_rel("C1")
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text(json.dumps({"claim_id": "C1", "run_id": "an-old-pass"}), encoding="utf-8")

        runners: list = []

        def run_one(world, prog, inputs, out_name):
            runner = program_runner(
                prog, output_root=root / out_name, materialize_root=mat_root, image=fake_image,
                transcript_dir=root / out_name / "transcripts", expected_fingerprint=ss.UNPINNED, forbidden=forbidden_list(),
                _session_factory=world.session, _stack_factory=world.stack, _docker=world,
            )
            runners.append(runner)
            with runner as pr:
                return pr.as_runner(run_id="selftest-run").run(program, inputs)

        inputs = RunInputs(input_ref=str(batch), batch_id="selftest-train", split="train")

        # -- a clean pass ----------------------------------------------------------------------
        world = _FakeWorld()
        prog = SarolProgram(profile="retrieval", model="haiku")
        art = run_one(world, prog, inputs, "out-clean")
        manifest = json.loads(pathlib.Path(art.artifact_refs[0].path).read_text(encoding="utf-8"))
        records = {r["claim_id"]: r for r in manifest["claims"]}
        checks += [
            ("a clean pass returns ok with the manifest first", art.status == "ok"
             and pathlib.Path(art.artifact_refs[0].path).name == "run_manifest.json"),
            ("...one record per claim, each validated", sorted(records) == ["C1", "C2", "C3"]
             and all(r["status"] == "ok" and (r.get("validation") or {}).get("ok") for r in records.values())),
            ("...each record points at its archived call folder",
             all("/archive/" in r["staging_dir"] and r["staging_dir"].endswith("/calls/" + c) for c, r in records.items())),
            ("...and the answer belongs to this pass", len({r["answer_run_id"] for r in records.values()}) == 1
             and manifest["pass_id"] in {r["answer_run_id"] for r in records.values()}),
            ("a previous pass's answer is never copied into a call folder", world.pre_existing == []),
            ("every prompt names the call and program by container path",
             all(CALL_CONTAINER_PATH in p and SPEC_ROOT in p for p in world.prompts.values())),
            ("...and no host path", all(str(root) not in p and str(pathlib.Path.home()) not in p for p in world.prompts.values())),
            ("the audit copy of the prompt is in the archived call folder",
             all((pathlib.Path(r["staging_dir"]) / "ledger" / "prompts" / f"{c}.md").read_text(encoding="utf-8") == world.prompts[c]
                 for c, r in records.items())),
            ("each record's trace is the session transcript the engine recorded, readable after the pass",
             all((r["stages"]["adjudicator"].get("trace_ref") or "").endswith("events.jsonl")
                 and pathlib.Path(r["stages"]["adjudicator"]["trace_ref"]).is_file() for r in records.values())),
            ("the manifest carries the run identity the scorer reads",
             manifest["profile"] == "retrieval" and manifest["retrieval_k"] == 20 and manifest["requested_count"] == 3
             and manifest["model"] == "claude-haiku-fake" and manifest["failed_calls"]["count"] == 0),
        ]
        from isolation.setup_fingerprint import fingerprint_hash, setup_fingerprint  # noqa: PLC0415

        given = {fingerprint_hash(setup_fingerprint(d)) for d in world.descriptions}
        checks.append(("the program pin is computed from the same setup the runner hands its sessions",
                       len(given) == 1 and given == {fingerprint_hash(setup_fingerprint(program_pin_description(runners[-1])))}))
        gold = {"pred_label": "OVERSIMPLIFY", "gold_label": "OVERSIMPLIFY"}
        scored = adapter.SarolScorer(gold_resolver=lambda _p: gold).score(art, "train", {})
        checks.append(("the scorer scores a clean pass in full", scored.breakdown.get("scored") is True
                       and scored.breakdown.get("n_total") == 3))

        # -- one call crashes, one writes garbage ----------------------------------------------
        world = _FakeWorld()
        world.behaviour = {"C2": "crash", "C3": "garbage"}
        art = run_one(world, SarolProgram(profile="retrieval", model="haiku"), inputs, "out-failed")
        manifest = json.loads(pathlib.Path(art.artifact_refs[0].path).read_text(encoding="utf-8"))
        records = {r["claim_id"]: r for r in manifest["claims"]}
        checks += [
            ("a crashed call is recorded as failed, with its reason", records["C2"]["status"] == "failed"
             and records["C2"]["failed"] == "crash" and "boom" in (records["C2"].get("detail") or "")),
            ("...the pass still completes and says calls failed", art.status == "ok"
             and getattr(art.error, "code", None) == "calls_failed"),
            ("a garbage verdict is invalid_output, not failed", records["C3"]["status"] == "invalid_output"),
        ]
        scored = adapter.SarolScorer(gold_resolver=lambda _p: gold).score(art, "train", {})
        b = scored.breakdown
        checks += [
            ("the scorer scores the crashed call as a miss instead of refusing the batch",
             b.get("scored") is True and b.get("n_total") == 3),
            ("...and counts it in failed_calls by reason", b.get("failed_calls") == {"count": 1, "by_reason": {"crash": 1, "timeout": 0}}),
            ("...which the VAL reduction lets through", "failed_calls" in adapter._VAL_BREAKDOWN_ALLOWED),
        ]

        # -- a timeout beside a crash: accounting invariants ----------------------------------
        world = _FakeWorld()
        world.behaviour = {"C2": "timeout", "C3": "crash"}
        art = run_one(world, SarolProgram(profile="retrieval", model="haiku"), inputs, "out-timeout")
        manifest = json.loads(pathlib.Path(art.artifact_refs[0].path).read_text(encoding="utf-8"))
        records = {r["claim_id"]: r for r in manifest["claims"]}
        failed_records = [r for r in manifest["claims"] if r["status"] == "failed"]
        scored = adapter.SarolScorer(gold_resolver=lambda _p: gold).score(art, "train", {})
        checks += [
            ("a timed-out call is failed for timeout, its stage marked timed out",
             records["C2"]["failed"] == "timeout" and records["C2"]["stages"]["adjudicator"]["timed_out"] is True),
            ("failed_calls counts exactly the failed records, by reason",
             manifest["failed_calls"] == {"count": len(failed_records), "by_reason": {"crash": 1, "timeout": 1}}),
            ("...and the scorer counts every requested claim, failed ones included",
             scored.breakdown.get("n_total") == manifest["requested_count"] == 3
             and scored.breakdown.get("failed_calls") == manifest["failed_calls"]),
        ]
        unresolved = adapter.SarolScorer(
            gold_resolver=lambda p: (_ for _ in ()).throw(OSError("no gold")) if pathlib.Path(p).name == "C3" else gold
        ).score(art, "train", {})
        sentinel = adapter.SarolScorer(
            gold_resolver=lambda p: {"pred_label": "OVERSIMPLIFY", "gold_label": adapter.FAILED_CALL_LABEL}
            if pathlib.Path(p).name in ("C2", "C3") else gold
        ).score(art, "train", {})
        checks += [
            ("a failed call whose gold cannot be resolved leaves the batch unscored, not quietly counted",
             unresolved.breakdown.get("scored") is False and unresolved.breakdown.get("n_unresolved") == 1),
            ("a failed call is never counted correct, even if a broken resolver returns the sentinel as gold",
             sentinel.breakdown.get("scored") is False and sentinel.breakdown.get("n_unresolved") == 2),
        ]

        # -- the prompt cache is per pass: a claim reused across passes gets its own prompt ----
        prog = SarolProgram(profile="retrieval", model="haiku")
        prog._program = program
        from isolation.program_runner import CallPaths  # noqa: PLC0415

        call = Call("C1", {"claim_id": "C1", "citekey": "k1", "staging_dir": str(claims[0].staging_dir)})
        paths = CallPaths(program=SPEC_ROOT, call=CALL_CONTAINER_PATH, ro={})
        for pid in ("pass-aaa", "pass-bbb"):
            folder = root / "cache" / pid / "C1"
            folder.mkdir(parents=True)
            prog.stage(call, folder, pid)
        pa = prog.prompt(call, "adjudicator", paths, "pass-aaa")
        pb = prog.prompt(call, "adjudicator", paths, "pass-bbb")
        checks.append(("the rendered prompt is per pass: a claim reused across passes carries each pass's own id",
                       "pass-aaa" in pa and "pass-bbb" not in pa and "pass-bbb" in pb and "pass-aaa" not in pb))

        # -- the canary ------------------------------------------------------------------------
        canary_claim = adapter.load_batch(adapter._staged_batch(root / "canary", claim_ids=("K1",), split="train")[1])[0]
        world = _FakeWorld()
        good = SarolProgram(profile="retrieval", model="haiku",
                            canary=adapter.CanarySpec(claim=canary_claim, expected_verdict="OVERSIMPLIFY"))
        art = run_one(world, good, inputs, "out-canary-ok")
        manifest = json.loads(pathlib.Path(art.artifact_refs[0].path).read_text(encoding="utf-8"))
        checks += [
            ("a matching canary runs first and the pass proceeds", art.status == "ok" and "K1" in world.prompts
             and (manifest.get("canary") or {}).get("claim_id") == "K1"),
            ("...and the canary is not scored as a claim", sorted(r["claim_id"] for r in manifest["claims"]) == ["C1", "C2", "C3"]),
            ("...while its session counts toward the pass's sessions and cost",
             manifest["requested_count"] == 3 and manifest["sub_invocation_count"] == 4
             and abs(manifest["cost_usd"] - 0.4) < 1e-9),
        ]
        world = _FakeWorld()
        bad = SarolProgram(profile="retrieval", model="haiku",
                           canary=adapter.CanarySpec(claim=canary_claim, expected_verdict="ACCURATE"))
        try:
            run_one(world, bad, inputs, "out-canary-bad")
            stopped = None
        except PassStopped as exc:
            stopped = exc
        checks.append(("a canary miss stops the pass before any scored claim",
                       stopped is not None and getattr(stopped, "reason", "") == "canary_failed"
                       and set(world.prompts) == {"K1"}))

        # -- staging failures stop the pass with a reason --------------------------------------
        missing = root / "missing-batch.json"
        missing.write_text(json.dumps({"claims": [{"claim_id": "M1", "citekey": "k", "staging_dir": str(root / "nope")}]}))
        try:
            run_one(_FakeWorld(), SarolProgram(profile="retrieval", model="haiku"),
                    RunInputs(input_ref=str(missing), batch_id="selftest-missing", split="train"), "out-missing")
            stopped = None
        except PassStopped as exc:
            stopped = exc
        checks.append(("a claim whose staging folder is missing stops the pass as stage_failed",
                       stopped is not None and getattr(stopped, "reason", "") == "stage_failed"))

        bare_root = root / "mat-bare"
        bare = adapter._materialized_program(bare_root, name="iter1-current")
        world = _FakeWorld()
        try:
            runner = program_runner(
                SarolProgram(profile="retrieval", model="haiku"), output_root=root / "out-bare", materialize_root=bare_root,
                image=fake_image, transcript_dir=None, expected_fingerprint=ss.UNPINNED, forbidden=forbidden_list(),
                _session_factory=world.session, _stack_factory=world.stack, _docker=world,
            )
            with runner as pr:
                pr.as_runner(run_id="selftest-run").run(bare, inputs)
            stopped = None
        except PassStopped as exc:
            stopped = exc
        checks.append(("a version whose tree lacks the frozen command file stops the pass, naming it",
                       stopped is not None and getattr(stopped, "reason", "") == "nested_command_missing"
                       and "sarol-eval-item" in str(stopped) and world.prompts == {}))

        dup = root / "dup-batch.json"
        dup.write_text(json.dumps({"claims": [{"claim_id": "C1", "citekey": "k", "staging_dir": str(claims[0].staging_dir)}] * 2}))
        try:
            run_one(_FakeWorld(), SarolProgram(profile="retrieval", model="haiku"),
                    RunInputs(input_ref=str(dup), batch_id="selftest-dup", split="train"), "out-dup")
            refused = False
        except ValueError:
            refused = True
        checks.append(("a batch that repeats a claim id is refused before any call (engine check_calls)", refused))

    try:
        SarolProgram(profile="agentic", model="haiku")
        multi_refused = False
    except ValueError:
        multi_refused = True
    checks.append(("a profile with stages beyond the adjudicator is refused, not given its prompt", multi_refused))
    checks.append(("every forbidden entry names a representative (\"\" for a file), as the engine requires",
                   all(f.representatives for f in forbidden_list())))
    checks.append(("the forbidden list covers gold, the benchmark (test split included) and the token",
                   {str(f.path) for f in forbidden_list()} >= {
                       str(stage_claim.GOLD_ROOT.parent), str(stage_claim.BENCH_DIR.parent),
                       str(pathlib.Path.home() / ".claude")}
                   and any("claims-test.jsonl" in r for f in forbidden_list() for r in f.representatives)))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys as _sys  # noqa: PLC0415

    if "--selftest" in _sys.argv:
        _sys.exit(_selftest())
    if "--print-pins" in _sys.argv:
        _sys.exit(_print_pins())
    print("usage: sarol_program.py --selftest | --print-pins")
