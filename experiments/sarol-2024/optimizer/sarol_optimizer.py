"""paper-trail's optimizer as the engine's contained optimizer (PT-A step 4; PT1, PT3).

Plan: ``planning/paper-trail/2026-09-30-adopt-engine-sessions.md`` (build design D6), consumer half of
the engine's ``planning/agentic-label-opt/2026-09-22-engine-optimizer-container.md`` (A).

The optimizer used to be ``claude --dangerously-skip-permissions`` on the host with the repo as its
working folder: it could have read the validation answer key and chose not to. It is now one sealed
session per iteration, ``isolation.contained_agent.ContainedOptimizerAgent``: it edits a writable copy
of the program, and only changes inside the editable manifest come back, all at once or not at all.

Container layout (the engine's):

=====================================  ==============================================  ==========
Container path                         What paper-trail puts there                     Mode
=====================================  ==============================================  ==========
``/workspace/rw/program``              a copy of this iteration's program (the cwd)    writable
``/workspace/rw/out/findings.md``      this iteration's findings note                  writable
``/workspace/rw/out/meta-learnings.md``  the whole notebook, rewritten                 writable
``/workspace/ro/versions``             earlier program versions, materialized          read-only
``/workspace/ro/in/context``           the reference docs                              read-only
``/workspace/ro/notes``                every earlier note of the lineage (B4)          read-only
``/workspace/ro/in/meta-learnings.md`` the notebook as it stands                       read-only
``/workspace/ro/in/feedback``          every iteration's releases and train mistakes   read-only
=====================================  ==============================================  ==========

⚠ **Feedback is copied, not mounted from the repo (D6).** The engine forbids the repo's ``iter/``
folder wholesale (A6), and the train mistakes and judge traces live in the scorer's and the program
runner's roots, which are forbidden too. Before each iteration this module copies that iteration's
releases, the train mistakes file and the traces it cites into the feedback folder, rewriting each host
path to its container path.

**The two outputs are the engine's to file (B4, adopted in PT-B).** Each session starts with both
empty. A non-empty one is filed into the notes history at ``<notes root>/<run id>/iter-<n>/`` (a failed
session's notes too, under ``iter-<n>-failed``), which every later session reads at
``/workspace/ro/notes``. The notebook is also a running file: a non-empty copy replaces the real
notebook after a clean session; an empty one replaces nothing. paper-trail used to hold and file these
itself (``_file_outputs``, ``findings/iter-<n>.md``), success only.
"""

from __future__ import annotations

import dataclasses
import functools
import json
import os
import subprocess
import pathlib
import shutil
from typing import Any, Sequence

import adapter
import sarol_isolation as iso
import stage_claim

iso.engine_on_path()

from engine.materialize import materialize  # noqa: E402
from engine.schemas import ManifestEntry, ProgramManifest  # noqa: E402
from isolation import contained_agent as ca  # noqa: E402
from isolation import sealed_session as ss  # noqa: E402
from isolation.session_scope import Forbidden  # noqa: E402

_HERE = pathlib.Path(__file__).resolve().parent

TOKEN_ENV_NAME = "CLAUDE_CODE_OAUTH_TOKEN"

#: The optimizer's image: the engine's isolation image plus ``python3`` (Phil 2026-09-22: paper-trail's
#: optimizer image has Python; the engine's has none). Built from ``image/Dockerfile``; the tag carries
#: the Claude Code version it contains, like the grader image.
OPTIMIZER_IMAGE_TAG = "paper-trail-optimizer:" + iso.SHIPPING_IMAGE_TAG.rsplit(":", 1)[1]
DOCKERFILE = _HERE / "image" / "Dockerfile"

PROMPT_PATH = _HERE / "prompt" / "optimizer-instructions.md"
CONTEXT_DIR = _HERE / "context"
NOTEBOOK = _HERE / "meta-learnings.md"
#: What a fresh lineage's notebook starts as; the run-start reset puts it back (B3).
NOTEBOOK_STUB = _HERE / "meta-learnings.stub.md"

IN = ca.INPUTS_PATH
OUT = ca.OUT_PATH


def optimizer_image() -> str:
    """The optimizer image as ``name:version@sha256:…``."""
    from isolation.image_pin import image_ref  # noqa: PLC0415

    return image_ref(OPTIMIZER_IMAGE_TAG)


def build_command() -> list[str]:
    """The one line that builds the optimizer image on this machine."""
    version = OPTIMIZER_IMAGE_TAG.rsplit(":", 1)[1]
    return ["docker", "build", "--build-arg", f"CLAUDE_CODE_VERSION={version}", "-t", OPTIMIZER_IMAGE_TAG,
            "-f", str(DOCKERFILE), str(DOCKERFILE.parent)]


def program_manifest(store: "adapter.SarolProgramStore") -> ProgramManifest:
    """The manifest the contained optimizer is given: the WHOLE program, contract files included.

    The engine's copy-back checks every file of the staged program against this manifest, so it has to
    cover every materialized file (an editable-only manifest refused every copy-back: found by the
    selftest below). The contract files stay frozen because the engine refuses a change to any entry
    marked ``contract_file``, even under a folder glob that also matches it (engine, PT-A). Which files
    a profile actually uses is guidance in the optimizer's docs, not a gate, as before.
    """
    return store.manifest()


#: Where a program file lived in versions before program-v11 (PT-L moved the driver out of `.claude/`).
LEGACY_PROGRAM_PATHS: tuple[str, ...] = (".claude/commands/sarol-eval-item.md",)


def earlier_version_view(store: "adapter.SarolProgramStore"):
    """The manifest the optimizer uses to show it EARLIER program versions (``/workspace/ro/versions``).

    Before each session the engine materializes every ``program-v*`` tag it has no tree for, and by
    default it does so with today's manifest. Tags before program-v11 keep the driver at its old path,
    so today's manifest matches nothing there and the session never starts (found by PT-A's live
    optimizer check, 2026-10-02). This view marks every entry optional and adds the old paths, so each
    version shows the files it actually had. It is read-only: copy-back still checks the strict
    manifest (:func:`program_manifest`), and the loop materializes the current version with that too.
    """
    base = store.manifest()
    entries = tuple(
        dataclasses.replace(e, optional=True, contract_file=False) if e.freeze_policy == "committed" else e
        for e in base.entries
    ) + tuple(ManifestEntry(path=p, freeze_policy="committed", optional=True) for p in LEGACY_PROGRAM_PATHS)
    view = ProgramManifest(entries=entries, combined_hash=base.combined_hash)
    return lambda _sha: view


def forbidden_list(
    *, repo_root: pathlib.Path, program_output_root: pathlib.Path, scorer_roots: Sequence[pathlib.Path] = ()
) -> tuple[Forbidden, ...]:
    """What the optimizer must be unable to reach (A6), wholesale, each with a representative.

    Different from the graders' list on purpose: the optimizer's own notes and context are its
    inputs, and the graders must not see them; the scorer, the run outputs and ``iter/`` are the
    optimizer's to be kept from. The test split sits in the benchmark folder, covered wholesale (PT4,
    its own sealed folder, is deferred).
    """
    repo_root = pathlib.Path(repo_root)
    git_dir = repo_root / ".git"
    entries = [
        Forbidden(stage_claim.GOLD_ROOT.parent, representatives=("sarol-2024/train", "sarol-2024/dev")),
        Forbidden(stage_claim.BENCH_DIR.parent, representatives=(
            "sarol-2024/claims-dev.jsonl", "sarol-2024/claims-test.jsonl", "sarol-2024/corpus.jsonl")),
        Forbidden(pathlib.Path(program_output_root), representatives=("archive", "live")),
        Forbidden(repo_root / "iter", representatives=("1/release_val.json",)),
        Forbidden(repo_root / "experiments" / "sarol-2024" / "scripts", representatives=("score_sarol3.py",)),
        Forbidden(repo_root / "experiments" / "sarol-2024" / "program-v0" / "manifest.json", representatives=("",)),
        Forbidden(git_dir, representatives=("",) if git_dir.is_file() else ("HEAD",)),
        Forbidden(pathlib.Path.home() / ".claude", representatives=(".credentials.json",)),
        Forbidden(pathlib.Path.home() / ".paper-trail" / "credentials.env", representatives=("",)),
        *(Forbidden(pathlib.Path(r), representatives=("mistakes",)) for r in scorer_roots),
    ]
    return tuple(entries)


# =================================================================================================
# Feedback (D6)
# =================================================================================================


def _copy_into(src: str | None, dest_dir: pathlib.Path, container_dir: str) -> str | None:
    """Copy one host file into ``dest_dir`` and return its container path, or ``None``."""
    if not src:
        return None
    path = pathlib.Path(src)
    if not path.is_file():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if dest.exists() and dest.read_bytes() != path.read_bytes():
        dest = dest_dir / f"{path.parent.name}-{path.name}"
    shutil.copyfile(path, dest)
    return f"{container_dir}/{dest.name}"


def _without_host_paths(obj, *, roots: Sequence[str] = ()):
    """``obj`` with every string that is an absolute host path replaced by ``None`` (the optimizer's
    container has none of them; a host path in what it reads is a wiring bug, S1's ``host_path_leak``)."""
    home = str(pathlib.Path.home())
    if isinstance(obj, dict):
        return {k: _without_host_paths(v, roots=roots) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_without_host_paths(v, roots=roots) for v in obj]
    if isinstance(obj, str) and obj.startswith("/") and not obj.startswith("/workspace/") and (
        obj.startswith(home) or obj.startswith(("/var/", "/private/", "/tmp/", "/Users/", "/home/")) or any(obj.startswith(r) for r in roots)
    ):
        return None
    return obj


def copy_feedback_files(files: Sequence[tuple[str, pathlib.Path]], *, feedback_root: pathlib.Path) -> list[str]:
    """Copy run-level files the optimizer reads (the run summary, the TRAIN draw history) into the
    feedback folder, host paths stripped. Missing files are skipped: early in a run they do not exist."""
    copied = []
    for name, host in files:
        host = pathlib.Path(host)
        if not host.is_file():
            continue
        try:
            body = _without_host_paths(json.loads(host.read_text(encoding="utf-8")))
            (pathlib.Path(feedback_root) / name).write_text(json.dumps(body, indent=2), encoding="utf-8")
        except ValueError:
            continue
        copied.append(name)
    return copied


def prepare_feedback(iter_n: int, *, repo_root: pathlib.Path, feedback_root: pathlib.Path) -> dict:
    """Copy iteration ``iter_n``'s releases into ``feedback_root/iter/<n>/`` with host paths rewritten.

    The train release's corpus points at the train mistakes file; that file's rows point at the
    judge's traces. Both are copied beside it and every reference is rewritten to the container path
    under ``/workspace/ro/in/feedback``. The VAL release carries the scalar only (``_VAL_BREAKDOWN_
    ALLOWED``) and is copied as it is. Returns what was copied, for the run's record.
    """
    src = pathlib.Path(repo_root) / "iter" / str(iter_n)
    dest = pathlib.Path(feedback_root) / "iter" / str(iter_n)
    dest.mkdir(parents=True, exist_ok=True)
    c_iter = f"{IN}/feedback/iter/{iter_n}"
    copied: dict[str, Any] = {"iter": iter_n, "releases": [], "mistakes": None, "traces": 0}
    val = src / "release_val.json"
    if val.is_file():
        shutil.copyfile(val, dest / "release_val.json")
        copied["releases"].append("release_val.json")
    train = src / "release_train.json"
    if train.is_file():
        payload = json.loads(train.read_text(encoding="utf-8"))
        corpus = payload.get("corpus") or {}
        mistakes_host = corpus.get("ref")
        if mistakes_host and pathlib.Path(mistakes_host).suffix == ".json" and "mistakes" in pathlib.Path(mistakes_host).parts:
            body = json.loads(pathlib.Path(mistakes_host).read_text(encoding="utf-8"))
            for row in body.get("claims", []):
                row["trace_ref"] = _copy_into(row.get("trace_ref"), dest / "traces", f"{c_iter}/traces")
                copied["traces"] += 1 if row["trace_ref"] else 0
            manifest_host = body.get("run_manifest_ref")
            body["run_manifest_ref"] = None
            if manifest_host and pathlib.Path(manifest_host).is_file():
                # Correct-answer traces (TRAIN only, the open tier): the pass's whole manifest, every
                # claim's trace copied beside it, call folders dropped (they are host paths).
                run_manifest = json.loads(pathlib.Path(manifest_host).read_text(encoding="utf-8"))
                for rec in run_manifest.get("claims", []):
                    rec["staging_dir"] = None
                    for st in (rec.get("stages") or {}).values():
                        st["trace_ref"] = _copy_into(st.get("trace_ref"), dest / "traces", f"{c_iter}/traces")
                        copied["traces"] += 1 if st["trace_ref"] else 0
                (dest / "run_manifest.json").write_text(json.dumps(_without_host_paths(run_manifest), indent=2), encoding="utf-8")
                body["run_manifest_ref"] = f"{c_iter}/run_manifest.json"
                copied["run_manifest"] = body["run_manifest_ref"]
            (dest / "mistakes").mkdir(parents=True, exist_ok=True)
            name = pathlib.Path(mistakes_host).name
            (dest / "mistakes" / name).write_text(json.dumps(body, indent=2), encoding="utf-8")
            container_ref = f"{c_iter}/mistakes/{name}"
            corpus["ref"] = container_ref
            breakdown = ((corpus.get("metrics") or {}).get("breakdown")) or {}
            if "mistakes_ref" in breakdown:
                breakdown["mistakes_ref"] = container_ref
            copied["mistakes"] = container_ref
        elif mistakes_host:
            # Not a mistakes file (a failed or unscored batch points at the run manifest): the path is
            # meaningless inside the container, so it is dropped rather than handed over.
            corpus["ref"] = None
        (dest / "release_train.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        copied["releases"].append("release_train.json")
    return copied


# =================================================================================================
# The prompt
# =================================================================================================


def sandbox_note(iter_n: int, run_id: str | None = None) -> str:
    """Where everything is in the sealed container, and what is not there at all (PT3)."""
    return (
        f"## Where things are (iteration {iter_n}" + (f", run `{run_id}`" if run_id else "") + ")\n\n"
        "You are in a sealed container. Only these exist for you:\n\n"
        f"- `{ca.PROGRAM_PATH}`: a copy of the program as of this iteration, and your working folder. "
        "Edit program files here, at the same repo-relative paths your docs name "
        "(for example `experiments/sarol-2024/specs/verdict_definitions_sarol.md`). Only files in the "
        "program's editable manifest come back; any other change, or a new file outside it, stops the run.\n"
        f"- `{IN}/context/`: your reference docs.\n"
        f"- Your notebook: `{OUT}/meta-learnings.md`, which starts EMPTY. First copy the notebook as it "
        f"stands into it (`cp {IN}/meta-learnings.md {OUT}/meta-learnings.md`), then read and edit it there. "
        "Whatever that file holds when you exit becomes the notebook; left empty, the notebook is unchanged.\n"
        f"- `{ca.NOTES_PATH}/`: every earlier note of this lineage, one folder per run and iteration "
        "(`<run id>/iter-<n>/findings.md`, `meta-learnings.md`; `iter-<n>-failed` for a session that failed; "
        "`legacy/` for notes from before this layout). Write this iteration's findings to "
        f"`{OUT}/findings.md`.\n"
        f"- `{IN}/feedback/iter/<n>/`: each iteration's releases (`release_train.json`, `release_val.json`), "
        "the train mistakes file the train release points at, and the judge traces its rows cite.\n"
        f"- `{ca.VERSIONS_PATH}/`: earlier program versions, materialized. Read an earlier version's file "
        "there; there is no git history in here.\n\n"
        "Not mounted at all: the gold labels, the benchmark (the test split included), the scorer, the run "
        "outputs, the repository's history and the account's credentials. Looking for them finds nothing; "
        "a path outside the folders above does not exist here.\n"
    )


def prompt_builder(iter_n: int, paths, run_id: str | None = None) -> str:
    return (
        f"Iteration {iter_n}" + (f" of run `{run_id}`" if run_id else "") + f". The program to improve is the "
        f"copy in `{paths.program}`. Follow your standing instructions.\n\n" + sandbox_note(iter_n, run_id)
    )


# =================================================================================================
# The agent
# =================================================================================================


class SarolOptimizer:
    """The loop's agent: one contained optimizer session per iteration.

    A fresh ``ContainedOptimizerAgent`` is built each iteration because its declared outputs and the
    feedback it reads are per-iteration; construction is cheap and refuses a bad grant before any spend.
    """

    def __init__(
        self,
        *,
        store: "adapter.SarolProgramStore",
        materialize_root: pathlib.Path,
        program_output_root: pathlib.Path,
        run_root: pathlib.Path,
        image: str,
        expected_fingerprint: str,
        model: str = "opus",
        max_budget_usd: float = 20.0,
        timeout_seconds: float = 3600.0,
        profile=None,
        scorer_roots: Sequence[pathlib.Path] = (),
        transcript_dir: pathlib.Path | None = None,
        feedback_files: Sequence[tuple[str, pathlib.Path]] = (),
        notebook: pathlib.Path = NOTEBOOK,
        context_dir: pathlib.Path = CONTEXT_DIR,
        #: The notes history (B4) and the run it is keyed by. Both or neither.
        notes_root: pathlib.Path | None = None,
        run_id: str | None = None,
        _agent_factory=None,
    ) -> None:
        self.feedback_files = tuple((n, pathlib.Path(p)) for n, p in feedback_files)
        self.notebook = pathlib.Path(notebook)
        self.notes_root = pathlib.Path(notes_root) if notes_root is not None else None
        self.run_id = run_id
        self.context_dir = pathlib.Path(context_dir)
        self.store = store
        self.repo_root = pathlib.Path(store.repo_root)
        self.materialize_root = pathlib.Path(materialize_root)
        self.run_root = pathlib.Path(run_root)
        self.feedback_root = self.run_root / "optimizer-feedback"
        self.program_output_root = pathlib.Path(program_output_root)
        self.image = image
        self.expected_fingerprint = expected_fingerprint
        self.model = model
        self.max_budget_usd = max_budget_usd
        self.timeout_seconds = timeout_seconds
        self.profile = profile
        self.forbidden = forbidden_list(
            repo_root=self.repo_root, program_output_root=self.program_output_root, scorer_roots=scorer_roots
        )
        self.transcript_dir = transcript_dir
        self._agent_factory = _agent_factory or ca.ContainedOptimizerAgent
        self.feedback_records: list[dict] = []
        if not self.notebook.exists():
            self.notebook.write_text("", encoding="utf-8")
        self.feedback_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def agent_instructions() -> str:
        """The optimizer's standing instructions: the head of every prompt it is given."""
        return PROMPT_PATH.read_text(encoding="utf-8")

    def agent(self, iter_n: int):
        return self._agent_factory(
            model=self.model,
            system_prompt=self.agent_instructions(),
            prompt_builder=functools.partial(prompt_builder, run_id=self.run_id),
            manifest=program_manifest(self.store),
            manifest_for_version=earlier_version_view(self.store),
            repo_root=self.repo_root,
            materialize_root=self.materialize_root,
            forbidden=self.forbidden,
            profile=ss.AnthropicApiProfile(token_env_name=TOKEN_ENV_NAME, allowed_hosts=iso.EGRESS_ALLOWED_HOSTS),
            credential=ss.NO_CREDENTIAL,
            image=self.image,
            expected_fingerprint=self.expected_fingerprint,
            transcript_dir=self.transcript_dir,
            # findings.md is per iteration (filed in the notes history only); the notebook is a running
            # file, replaced by a non-empty copy. Its current copy stays readable below: the history
            # holds per-iteration copies only, and a fresh lineage starts from the stub, never filed.
            declared_outputs=(
                ca.DeclaredOutput("findings.md"),
                ca.DeclaredOutput("meta-learnings.md", self.notebook),
            ),
            readable_inputs=(
                ("context", self.context_dir),
                ("meta-learnings.md", self.notebook),
                ("feedback", self.feedback_root),
            ),
            notes_root=self.notes_root,
            run_id=self.run_id,
            max_budget_usd=self.max_budget_usd,
            timeout_seconds=self.timeout_seconds,
            host_env=self._host_env(),
        )

    def setup_description(self):
        """The optimizer session's description, for the setup check at run start and the pin: the
        engine's own builder (``ContainedOptimizerAgent.setup_description``, C0), over placeholder
        folders the fingerprint never reads. Replaces the hand-built ``pin_description``."""
        return self.agent(0).setup_description()

    @staticmethod
    def _host_env() -> dict:
        value = os.environ.get(TOKEN_ENV_NAME)
        return {TOKEN_ENV_NAME: value} if value else {}

    def run(self, *, iter_n: int, materialized_path=None):  # keyword-only, the loop's agent seam
        record = prepare_feedback(iter_n, repo_root=self.repo_root, feedback_root=self.feedback_root)
        record["run_files"] = copy_feedback_files(self.feedback_files, feedback_root=self.feedback_root)
        self.feedback_records.append(record)
        return self.agent(iter_n).run(iter_n=iter_n, materialized_path=materialized_path)


# =================================================================================================
# Selftest
# =================================================================================================


def _selftest() -> int:
    import tempfile  # noqa: PLC0415

    from isolation.session_scope import host_path_leak  # noqa: PLC0415

    os.environ.setdefault(TOKEN_ENV_NAME, "selftest-token")
    checks: list[tuple[str, bool]] = []
    fake_image = OPTIMIZER_IMAGE_TAG + "@sha256:" + "0" * 64
    with tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as td:
        root = pathlib.Path(td)
        repo = root / "repo"
        run_root = root / "run"
        traces = run_root / "program-out" / "archive" / "pass-1" / "transcripts"
        traces.mkdir(parents=True)
        trace = traces / "events.jsonl"
        trace.write_text('{"type": "result"}\n', encoding="utf-8")
        mistakes = run_root / "scorer" / "mistakes" / "run-train-i1.json"
        mistakes.parent.mkdir(parents=True)
        trace_ok = traces / "events-ok.jsonl"
        trace_ok.write_text('{"type": "result", "ok": true}\n', encoding="utf-8")
        pass_manifest = run_root / "program-out" / "archive" / "pass-1" / "run_manifest.json"
        pass_manifest.write_text(json.dumps({"claims": [
            {"claim_id": "C1", "staging_dir": str(run_root / "program-out" / "archive" / "pass-1" / "calls" / "C1"),
             "stages": {"adjudicator": {"trace_ref": str(trace)}}},
            {"claim_id": "C3", "staging_dir": str(run_root / "program-out" / "archive" / "pass-1" / "calls" / "C3"),
             "stages": {"adjudicator": {"trace_ref": str(trace_ok)}}}]}), encoding="utf-8")
        mistakes.write_text(json.dumps({"claims": [{"claim_id": "C1", "trace_ref": str(trace)},
                                                   {"claim_id": "C2", "trace_ref": None}],
                                        "run_manifest_ref": str(pass_manifest)}), encoding="utf-8")
        it = repo / "iter" / "1"
        it.mkdir(parents=True)
        (it / "release_train.json").write_text(json.dumps({
            "phase": "train", "corpus": {"ref": str(mistakes), "metrics": {"breakdown": {"mistakes_ref": str(mistakes)}}}}))
        (it / "release_val.json").write_text(json.dumps({"phase": "val", "metrics": {"primary_metric": 0.4}}))
        feedback = run_root / "optimizer-feedback"
        copied = prepare_feedback(1, repo_root=repo, feedback_root=feedback)
        written = "".join(p.read_text(encoding="utf-8") for p in feedback.rglob("*") if p.is_file())
        train = json.loads((feedback / "iter" / "1" / "release_train.json").read_text())
        rows = json.loads((feedback / "iter" / "1" / "mistakes" / "run-train-i1.json").read_text())["claims"]
        checks += [
            ("both releases are copied into the feedback folder", sorted(copied["releases"]) == ["release_train.json", "release_val.json"]),
            ("the train release points at its mistakes file by container path",
             train["corpus"]["ref"] == f"{IN}/feedback/iter/1/mistakes/run-train-i1.json"
             and train["corpus"]["metrics"]["breakdown"]["mistakes_ref"] == train["corpus"]["ref"]),
            ("...and each cited judge trace is copied beside it and re-pointed",
             rows[0]["trace_ref"] == f"{IN}/feedback/iter/1/traces/events.jsonl"
             and (feedback / "iter" / "1" / "traces" / "events.jsonl").is_file() and rows[1]["trace_ref"] is None),
            ("no host path is left in anything the optimizer reads", str(root) not in written),
            ("the TRAIN pass's manifest is copied for correct-answer traces, call folders dropped",
             copied.get("run_manifest") == f"{IN}/feedback/iter/1/run_manifest.json"
             and all(c["staging_dir"] is None for c in json.loads((feedback / "iter" / "1" / "run_manifest.json").read_text())["claims"])),
            ("...with a correct claim's trace copied and re-pointed too",
             json.loads((feedback / "iter" / "1" / "run_manifest.json").read_text())["claims"][1]["stages"]["adjudicator"]["trace_ref"]
             == f"{IN}/feedback/iter/1/traces/events-ok.jsonl"),
        ]
        # Two traces with one file name in two call folders (the engine names every transcript
        # events.jsonl): both kept, re-pointed to two different container paths.
        twin_a, twin_b = run_root / "t" / "a" / "events.jsonl", run_root / "t" / "b" / "events.jsonl"
        for twin, body_ in ((twin_a, "A\n"), (twin_b, "B\n")):
            twin.parent.mkdir(parents=True)
            twin.write_text(body_, encoding="utf-8")
        it3 = repo / "iter" / "3"
        it3.mkdir()
        m3 = run_root / "scorer" / "mistakes" / "run-train-i3.json"
        m3.write_text(json.dumps({"claims": [{"claim_id": "X1", "trace_ref": str(twin_a)},
                                             {"claim_id": "X2", "trace_ref": str(twin_b)}]}), encoding="utf-8")
        (it3 / "release_train.json").write_text(json.dumps({"corpus": {"ref": str(m3)}}))
        prepare_feedback(3, repo_root=repo, feedback_root=feedback)
        rows3 = json.loads((feedback / "iter" / "3" / "mistakes" / "run-train-i3.json").read_text())["claims"]
        ref_a, ref_b = rows3[0]["trace_ref"], rows3[1]["trace_ref"]
        host_a = feedback / "iter" / "3" / "traces" / pathlib.Path(ref_a).name
        host_b = feedback / "iter" / "3" / "traces" / pathlib.Path(ref_b).name
        checks.append(("two traces sharing a file name are both kept, at two different container paths",
                       ref_a != ref_b and host_a.read_text() == "A\n" and host_b.read_text() == "B\n"))
        broken = run_root / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        checks.append(("a malformed run-level file is skipped, not copied",
                       copy_feedback_files([("broken.json", broken)], feedback_root=feedback) == []
                       and not (feedback / "broken.json").exists()))
        checks.append(("host paths are stripped and container paths kept, including a stated extra root",
                       _without_host_paths({"a": "/workspace/ro/in/x", "b": "/Users/someone/x", "c": "/private/var/x",
                                            "d": "/srv/run/x", "e": "plain text"}, roots=("/srv/run",))
                       == {"a": "/workspace/ro/in/x", "b": None, "c": None, "d": None, "e": "plain text"}))
        summary = run_root / "run_summary.json"
        summary.write_text(json.dumps({"iterations": [{"val": 0.4, "manifest": str(pass_manifest)}]}), encoding="utf-8")
        files = copy_feedback_files([("run_summary.json", summary), ("draw_history.json", run_root / "absent.json")],
                                    feedback_root=feedback)
        body = json.loads((feedback / "run_summary.json").read_text())
        checks.append(("run-level files are copied with host paths stripped, and a missing one is skipped",
                       files == ["run_summary.json"] and body["iterations"][0] == {"val": 0.4, "manifest": None}))
        # A failed batch's release points at the run manifest, not a mistakes file: dropped, not handed over.
        it2 = repo / "iter" / "2"
        it2.mkdir()
        (it2 / "release_train.json").write_text(json.dumps({"corpus": {"ref": str(run_root / "program-out" / "x" / "run_manifest.json")}}))
        prepare_feedback(2, repo_root=repo, feedback_root=feedback)
        checks.append(("a release pointing anywhere but a mistakes file has the path dropped",
                       json.loads((feedback / "iter" / "2" / "release_train.json").read_text())["corpus"]["ref"] is None))

        # -- the agent, built for real (no session), with the engine filing its notes (B4) ----------
        notebook = root / "notes" / "meta-learnings.md"
        notebook.parent.mkdir()
        notebook.write_text("earlier lessons\n", encoding="utf-8")
        context = root / "notes" / "context"
        context.mkdir()
        (context / "playbook.md").write_text("docs\n")
        notes_root = root / "state" / "optimizer-notes"
        mat_root = root / "mat"
        mat_root.mkdir()
        store = adapter.SarolProgramStore()
        built: list = []

        class _FakeAgent:
            def __init__(self, **kw):
                self.real = ca.ContainedOptimizerAgent(**kw)  # its construction refusals still run
                self.kw = kw
                built.append(self)

            def run(self, *, iter_n, materialized_path=None):
                return type("O", (), {"exit_code": 0, "detail": "", "token_usage": {}, "cost_usd": 0.0})()

        def _optimizer(**overrides):
            kw = dict(
                store=store, materialize_root=mat_root, program_output_root=run_root / "program-out", run_root=run_root,
                image=fake_image, expected_fingerprint=ss.UNPINNED, scorer_roots=(run_root / "scorer",),
                notebook=notebook, context_dir=context, notes_root=notes_root, run_id="selftest-run",
                _agent_factory=_FakeAgent,
            )
            kw.update(overrides)
            return SarolOptimizer(**kw)

        opt = _optimizer()
        outcome = opt.run(iter_n=1, materialized_path=mat_root / "iter1-current")
        kw = built[-1].kw
        outs = {o.name: o.destination for o in kw["declared_outputs"]}
        inputs = dict(kw["readable_inputs"])
        checks += [
            ("a real ContainedOptimizerAgent accepts paper-trail's grant with a notes root (no construction refusal)",
             len(built) == 1 and outcome.exit_code == 0),
            ("the engine files the notes: notes root and run id are passed through",
             kw["notes_root"] == notes_root and kw["run_id"] == "selftest-run"),
            ("findings.md is a per-iteration note (no destination); the notebook is a running file onto the real one",
             outs == {"findings.md": None, "meta-learnings.md": notebook}),
            ("the old findings folder is no longer an input; the notebook, context and feedback still are",
             set(inputs) == {"context", "meta-learnings.md", "feedback"} and inputs["meta-learnings.md"] == notebook),
            ("paper-trail no longer files outputs itself (the holding folder is gone)",
             not (run_root / "optimizer-outputs").exists() and not hasattr(opt, "_file_outputs")),
        ]
        # Negative control: a notes root inside the checkout (here, under iter/) is refused at construction.
        try:
            _optimizer(notes_root=store.repo_root / "iter" / "notes").agent(1)
            inside_refused = False
        except ValueError as exc:
            inside_refused = "overlaps the checkout" in str(exc)
        checks.append(("a notes root inside the checkout is refused (negative control)", inside_refused))
        agent = built[-1].real
        prompt = agent.prompt(2)
        scope = agent.scope(root / "stage" / "program", root / "stage" / "out")
        d = agent.description(scope, materialized_path=mat_root / "iter2-current")
        checks += [
            ("the optimizer's prompt carries its standing instructions and the sandbox map",
             PROMPT_PATH.read_text(encoding="utf-8")[:200] in prompt and "Where things are (iteration 2, run `selftest-run`)" in prompt),
            ("...and it names the run id, which the notes history is keyed by", "Iteration 2 of run `selftest-run`" in prompt),
            ("...and no host path the engine can see", host_path_leak([prompt], scope, extra_paths=d.extra_host_paths) is None),
            ("the optimizer's manifest covers the whole program, contract files marked as such",
             {e.path for e in program_manifest(store).entries} >= set(store.contract_paths())
             and all(e.contract_file for e in program_manifest(store).entries if e.path in set(store.contract_paths()))),
            ("the session is the optimizer kind with skip posture and the optimizer's tools",
             d.kind == "optimizer" and d.posture == "skip" and d.tools == ca.OPTIMIZER_TOOLS),
        ]
    # The engine's copy-back over a REAL materialized program: an unchanged copy, an allowed edit, a
    # contract edit. This is the check that found an editable-only manifest refusing every copy-back.
    from isolation import copy_back as cb  # noqa: PLC0415

    with tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as td2:
        store = adapter.SarolProgramStore()
        mat = adapter.materialize_program(store, pathlib.Path(td2) / "mat" / "iter1-current")
        work = pathlib.Path(td2) / "work"
        cb.stage_program(mat, work)
        manifest = program_manifest(store)
        try:
            unchanged_ok = cb.program_changes(work, mat, manifest).changed == ()
        except cb.CopyBackRefused:
            unchanged_ok = False
        editable = next(p for p in store.editable_paths("retrieval") if p not in store.contract_paths())
        (work / editable).write_text((work / editable).read_text() + "\nan optimizer edit\n")
        try:
            allowed_ok = cb.program_changes(work, mat, manifest).changed == (editable,)
        except cb.CopyBackRefused:
            allowed_ok = False
        contract = store.contract_paths()[0]
        (work / contract).write_text((work / contract).read_text() + "\nan edit to a frozen contract\n")
        try:
            cb.program_changes(work, mat, manifest)
            contract_refused = False
        except cb.CopyBackRefused as exc:
            contract_refused = "contract" in str(exc)
    checks += [
        ("copy-back over the real materialized program accepts an unchanged copy", unchanged_ok),
        ("...accepts an edit to an editable program file", allowed_ok),
        ("...and refuses an edit to a frozen contract file", contract_refused),
    ]
    fl = forbidden_list(repo_root=adapter.REPO_ROOT, program_output_root=pathlib.Path("/x/out"),
                        scorer_roots=(pathlib.Path("/x/scorer"),))
    paths = {str(f.path) for f in fl}
    checks += [
        ("the optimizer's forbidden list covers gold, benchmark, run outputs, iter/, scorer, manifest, .git, token",
         {str(stage_claim.GOLD_ROOT.parent), str(stage_claim.BENCH_DIR.parent), "/x/out", "/x/scorer",
          str(adapter.REPO_ROOT / "iter"), str(adapter.REPO_ROOT / ".git"), str(pathlib.Path.home() / ".claude")} <= paths),
        ("...and never its own inputs (context, notebook)",
         not {str(CONTEXT_DIR), str(NOTEBOOK)} & paths),
        ("every entry names a representative", all(f.representatives for f in fl)),
    ]
    # Earlier versions materialize through the view; the strict manifest fails on a pre-v11 tag
    # (the negative control: without the view the optimizer never starts).
    store = adapter.SarolProgramStore()
    tags = subprocess.run(["git", "-C", str(store.repo_root), "tag", "--list", "program-v*", "--merged", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.split()
    if not tags:
        checks.append(("(no program tags in this checkout: the earlier-version view is not exercised)", True))
    else:
        view = earlier_version_view(store)("unused")
        bad, legacy_seen = [], False
        with tempfile.TemporaryDirectory(dir=pathlib.Path.home() / ".cache") as vd:
            for tag in tags:
                sha = subprocess.run(["git", "-C", str(store.repo_root), "rev-list", "-n", "1", tag],
                                     capture_output=True, text=True, check=True).stdout.strip()
                dest = pathlib.Path(vd) / tag
                try:
                    materialize(view, sha, repo_root=store.repo_root, dest=dest)
                except Exception as exc:  # noqa: BLE001
                    bad.append(f"{tag}: {exc}")
                    continue
                files = [q for q in dest.rglob("*") if q.is_file()]
                if not files:
                    bad.append(f"{tag}: no files")
                legacy_seen |= (dest / LEGACY_PROGRAM_PATHS[0]).is_file()
            for q in pathlib.Path(vd).rglob("*"):
                q.chmod(0o700 if q.is_dir() else 0o600)
            pathlib.Path(vd).chmod(0o700)
            strict_failed = False
            if "program-v10" in tags:
                sha10 = subprocess.run(["git", "-C", str(store.repo_root), "rev-list", "-n", "1", "program-v10"],
                                       capture_output=True, text=True, check=True).stdout.strip()
                try:
                    materialize(store.manifest(), sha10, repo_root=store.repo_root, dest=pathlib.Path(vd) / "strict-v10")
                except RuntimeError:
                    strict_failed = True
                for q in pathlib.Path(vd).rglob("*"):
                    q.chmod(0o700 if q.is_dir() else 0o600)
        checks.append((f"every program tag ({len(tags)}) materializes through the earlier-version view: {bad[:2]}", not bad))
        checks.append(("...and a pre-v11 version shows the driver at its old path", legacy_seen or "program-v10" not in tags))
        checks.append(("...while the strict manifest fails on program-v10 (the negative control)",
                       strict_failed or "program-v10" not in tags))
        checks.append(("...and the view keeps no contract file and marks every committed entry optional",
                       all(e.optional and not e.contract_file for e in view.entries if e.freeze_policy == "committed")))
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    if "--build" in sys.argv:
        sys.exit(subprocess.call(build_command()))
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("usage: sarol_optimizer.py --build | --selftest")
