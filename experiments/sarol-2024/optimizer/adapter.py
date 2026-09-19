"""paper-trail's ``TaskAdapter`` — the four protocols `agentic-label-opt`'s ``run_loop`` drives.

paper-trail is consumer #3 of the shared engine (rad-eval #1, crc-extraction-agent #2). The engine
abstracts the *container* — the manifest freeze, the materialize step, the audit ledger, the
frontier bookkeeping — and never the *payload*. This module is the payload: `ProgramStore`,
`Runner`, `Scorer`, `ReleaseBuilder`, plus the agent wrapper that enforces the one guarantee the
engine cannot.

What is genuinely load-bearing here, and why (plan Parts C1/C4, engine @ `6d621ac`):

* **The audit ledger is the engine's, and this consumer does not use it.** ``run_loop`` takes an
  ``audit_ledger`` path (`loop.py:197`) and verifies a hash chain over it; `dispatcher.py` passes
  none, and ``audit_ledger`` and ``policy_config`` appear zero times there. Recorded because four
  optimizer-facing docs used to promise the agent that reaching for held-out gold was "logged to
  the audit ledger, and a denied-call threshold pauses the run" — a guarantee nothing implemented.
  Those docs now say the true thing instead: **VAL/TEST isolation here is by construction**, the
  records living outside the repository tree entirely, which needs no watcher to hold. Wire the
  ledger if a future run wants one; do not describe it as wired until it is.

* **The contract-file re-hash is consumer-side, and it is the whole of "immutable".** The engine's
  ``contract_file=True`` enforces **presence only** (`versioning.py:86-90`, `materialize.py:72-79`):
  nothing in the engine stops the optimizer rewriting a contract file's bytes. So the frozen Sarol
  enum is immutable only because :class:`SarolProgramStore` re-hashes it after every edit pass and
  :class:`ContractGuardedAgent` turns a mismatch into a nonzero exit. That placement is deliberate:
  `run_loop` raises ``LoopStop`` on a nonzero agent exit *before* ``commit_version``, so a mutated
  contract fails the iteration **before any scoring or freeze** — which is exactly the gate the
  plan's Verification table asks for. Anywhere later and a poisoned version is already tagged.

* **The Runner is called three times per iteration, not twice.** `loop.py:334` (TRAIN), `:335`
  (VAL), and `:410` (the post-commit frozen-version probe, on ``val_inputs`` again). Only the
  probe's ``status`` is ever checked (`:413`); ``train_artifacts.status``/``val_artifacts.status``
  are read by nothing, and there is no try/except around the current-version calls. For an agentic
  Runner that means a partial-batch failure either scores as a silently degraded metric or takes
  the loop down. So this Runner never raises: it catches its own failures and reports them as
  ``status="timeout"``/``"program_error"``/``"infra_error"``, and the Scorer refuses to score
  anything that is not ``status="ok"``.

* **The engine never injects ``_split``.** `loop.py:320-321` comments that ``_iter``/``_split``
  "ride inside `task_config`", but only ``_iter`` actually does (`:336-337`). The split arrives at
  the Scorer as its *second positional argument* instead. :class:`SarolScorer` therefore stashes it
  into the returned ``task_config``; without that, :class:`SarolReleaseBuilder` would return a
  train-phase payload for the VAL call and the loop would ``LoopStop`` at `loop.py:373-377`.

* **Call-shape asymmetry is real and unforgiving.** ``runner.run(...)`` and ``scorer.score(...)``
  are called **positionally**; ``build_release(..., frontier=, budget=)`` and
  ``agent.run(iter_n=, materialized_path=)`` are **keyword-only**. Uniform signatures in either
  style break one pair or the other. These are copied from the engine's own `adapter.py` Protocols
  rather than guessed.

* **The materialized tree is not a runnable Claude Code project.** ``materialize`` does
  ``git show`` + ``write_text`` (`materialize.py:81-84`), so `main`'s ``.claude/*`` symlinks would
  land as regular files containing their target string; the orchestrator is deliberately outside
  the fileset; and the whole tree is chmod'd read-only, directories included (`:100-113`). So the
  Runner keeps a real working checkout as cwd and points ``{{spec_root}}`` at the materialized
  tree, per `src/commands/paper-trail.md:439`. Everything reachable through ``{{spec_root}}`` must
  therefore be a manifest entry (plan A4).

* **NaN passes the engine's metric validation.** ``PrimaryMetric`` checks ``isinstance`` only
  (`schemas.py:80-81`). A NaN frontier value makes ``_select_best`` order-dependent and makes
  ``_regressed`` return ``False``, so step-back never fires. The Scorer asserts finiteness.

Gold is never touched here. ``parse_verdict.py`` remains the single gold boundary and is called
only after a batch's adjudications are complete — the Runner never imports it.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import hashlib
import inspect
import json
import math
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Sequence

_HERE = pathlib.Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import dispatch_prompt  # noqa: E402
import engine_pin  # noqa: E402
import evidence_producers  # noqa: E402
# ⚠ Bound under the bare name `isolation` in `sys.modules` whatever we alias it to here, and the
# ENGINE's package is also called `isolation`. `isolation._import_engine()` swaps the engine's in and
# puts ours back; it restores `sys.modules` as well as `sys.path`, which it did not on first write
# (fixed 2026-09-18 after review) — without that, this import would silently start resolving to the
# engine's package after the first dispatch.
import isolation as isolation_mod  # noqa: E402
import profiles as profiles_mod  # noqa: E402
import validate_sarol  # noqa: E402

#: Repo root: experiments/sarol-2024/optimizer/adapter.py -> up 3.
REPO_ROOT = _HERE.parents[2]
MANIFEST_PATH = _HERE.parent / "program-v0" / "manifest.json"

#: Where `agentic-label-opt` is checked out. ⚠ **Re-exported, not redefined (2026-09-18).** This
#: was one of three separate copies of the same path literal; `engine_pin` now owns it, so a
#: re-pin cannot leave one copy behind. Kept as a name because callers import it.
DEFAULT_ENGINE = engine_pin.DEFAULT_ENGINE

#: Bumped 0.1.0 -> 0.2.0 when the `profile` key entered the release payloads (C6.5). A consumer
#: reading a 0.1.0 release cannot tell which rung produced the number, and the engine's frontier is
#: a bare scalar that will happily compare the two.
SCHEMA_VERSION = "0.2.0"

#: The three nested Claude Code sessions one claim costs. Named because the cost preflight has to
#: multiply by it and because `RunArtifacts.sub_invocation_count` is the field that carries it.
#: Every stage that exists. What a given run dispatches is the *profile's* subset
#: (`profiles.Profile.stages`) -- under `retrieval` that is `("adjudicator",)` alone. Kept as the
#: full tuple because it is the vocabulary, not the schedule.
STAGES: tuple[str, ...] = profiles_mod.ALL_STAGES


def engine_path() -> pathlib.Path:
    """Delegates to :mod:`engine_pin`, which is the single definition (2026-09-18)."""
    return engine_pin.engine_path()


def _import_engine():
    """Import the engine's schema types. Kept in a function so this module is importable (and
    self-testable) on a machine without the engine checked out.

    ⚠ **Refuses an engine that does not carry the pin (2026-09-18).** Until now the only version
    check lived in ``scripts/vm/run_hillclimb_vm.sh``, so every other entry point -- this one,
    ``dispatcher``, ``canary``, ``sampling``, ``run_baseline`` -- imported whatever happened to be
    in that directory. ``require_engine`` is memoized, so the ~20 call sites cost one ``git``
    invocation between them. Override with ``SAROL_ALLOW_ENGINE_DIVERGENCE=1``.
    """
    path = engine_pin.require_engine()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    from engine import schemas  # noqa: PLC0415

    return schemas


# =================================================================================================
# ProgramStore — the manifest, the edit scope, and the contract-file re-hash
# =================================================================================================


@dataclass(frozen=True)
class ContractViolation:
    path: str
    expected_sha256: str
    actual_sha256: str | None  # None when the file is missing entirely

    def __str__(self) -> str:
        actual = self.actual_sha256 or "<missing>"
        return f"{self.path}: frozen {self.expected_sha256[:12]}, found {actual[:12] if self.actual_sha256 else actual}"


class SarolProgramStore:
    """Serves the frozen `program-v0` manifest to the engine, and owns the two things the engine
    does not model: the adapter-owned extras strip, and the contract-file re-hash.

    Our manifest carries two fields per entry the engine's ``ManifestEntry`` does not declare —
    ``source`` (which of the two source refs a file was frozen from; the engine models exactly one)
    and ``sha256`` (the frozen content hash the re-hash compares against). Splatting a raw entry
    into ``ManifestEntry`` raises ``TypeError``, which `scripts/materialize_smoke.py` asserts on
    purpose so nobody "simplifies" this strip away.
    """

    def __init__(
        self,
        manifest_path: pathlib.Path = MANIFEST_PATH,
        *,
        repo_root: pathlib.Path = REPO_ROOT,
    ) -> None:
        self.manifest_path = pathlib.Path(manifest_path)
        # Pre-resolved: `policy.py` resolves symlinks when checking a subject (`:42-48`) but
        # compares against the RAW repo_root (`:51-55`). On macOS -- this consumer's only machine --
        # /tmp -> /private/tmp and iCloud-backed paths make an unresolved root deny every read, and
        # the failure is silent and misdiagnosable: the denied threshold trips and the run ends in a
        # LoopPause the engine documents as "a calibration signal, not a failure".
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.raw: dict[str, Any] = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    # -- manifest ---------------------------------------------------------------------------

    @property
    def entries(self) -> list[dict[str, Any]]:
        return self.raw["entries"]

    @property
    def combined_hash(self) -> str:
        return self.raw["combined_hash"]

    @property
    def runtime_pins(self) -> dict[str, Any]:
        return self.raw.get("runtime_pins", {})

    def manifest(self):
        """The engine-facing ``ProgramManifest``. This is the ``ProgramStore`` protocol."""
        schemas = _import_engine()
        # Derived from the dataclass rather than hard-coded, so an additive engine schema change
        # is picked up instead of silently dropped by a stale literal set.
        declared = {f.name for f in dataclasses.fields(schemas.ManifestEntry)}
        stripped = tuple(
            schemas.ManifestEntry(**{k: v for k, v in e.items() if k in declared})
            for e in self.entries
        )
        return schemas.ProgramManifest(entries=stripped, combined_hash=self.combined_hash)

    # -- edit scope -------------------------------------------------------------------------

    def contract_paths(self) -> list[str]:
        """The frozen-and-immutable half: read-only to the optimizer."""
        return [e["path"] for e in self.entries if e.get("contract_file")]

    def editable_paths(self, profile=None) -> list[str]:
        """The optimizer's EDIT scope: non-contract entries, narrowed to the profile (C6.1).

        Two owners, deliberately: `profiles.py` names which paths a rung may touch, and this method
        owns the ``contract_file`` partition. Neither duplicates the other, so widening a profile
        can never accidentally hand over a contract file — the intersection drops it and
        `profiles.validate_against_manifest` refuses it up front.

        The default profile is `agentic`, whose scope is every non-contract entry, so an un-migrated
        caller sees exactly the previous behaviour. Order follows the manifest, not the profile, so
        the scope is stable regardless of how a profile happens to list its paths.
        """
        allowed = set(profiles_mod.get(profile).editable)
        return [
            e["path"]
            for e in self.entries
            if not e.get("contract_file") and e["path"] in allowed
        ]

    # -- the re-hash (layer ii) --------------------------------------------------------------

    @property
    def program_version(self) -> str:
        """The tag this manifest freezes, e.g. ``program-v0``. The tag guard keys off it (S26)."""
        return self.raw["program_version"]

    def _rehash(self, entries, tree_root: pathlib.Path | None) -> list[ContractViolation]:
        """Re-hash `entries` against the tree. One implementation, two scopes (see below)."""
        root = pathlib.Path(tree_root).resolve() if tree_root is not None else self.repo_root
        violations: list[ContractViolation] = []
        for entry in entries:
            target = root / entry["path"]
            if not target.exists():
                violations.append(ContractViolation(entry["path"], entry["sha256"], None))
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != entry["sha256"]:
                violations.append(ContractViolation(entry["path"], entry["sha256"], actual))
        return violations

    def verify_contract_files(self, tree_root: pathlib.Path | None = None) -> list[ContractViolation]:
        """Re-hash every ``contract_file=True`` entry against its frozen ``sha256``.

        This is the *only* thing making those files immutable — the engine's own flag checks that a
        contract file is present in the fileset, never that its bytes are unchanged. Returns the
        violations rather than raising, so the caller decides the failure mode (the agent wrapper
        turns them into a nonzero exit; the dispatcher preflight prints them).
        """
        return self._rehash(
            [e for e in self.entries if e.get("contract_file")], tree_root
        )

    def verify_tag_tree(self, tag: str | None = None) -> list[ContractViolation]:
        """Re-hash every entry as it exists in the COMMITTED tree `tag` names.

        Different question again from its two siblings, and the one that decides what a run actually
        evaluates. `verify_tree_matches_tag` asks about the files on disk; **the engine never reads
        the files on disk.** `engine.materialize` does `git ls-tree`/`git show` against the single
        `version_sha` the tag resolves to, so the bytes the judge sees come from the TAG. A working
        tree that matches the manifest while the tag points at older content is the exact shape of
        "the numbers say v0 and the program was something else" -- and the tree check alone reports
        it as clean.

        This was a real gap, not a hypothetical: the 2026-09-07 re-freeze rewrote the manifest and
        restored the tree but left `program-v0` on the pre-trim enum, and every offline gate stayed
        green. Found by a Codex implementation audit.

        A tag that does not resolve is itself a violation -- reported with `actual_sha256=None`,
        the same shape as a missing file, since the consequence is the same: nothing to materialize.
        """
        ref = tag or self.program_version
        violations: list[ContractViolation] = []
        for entry in self.entries:
            proc = subprocess.run(
                ["git", "-C", str(self.repo_root), "show", f"{ref}^{{commit}}:{entry['path']}"],
                capture_output=True,
            )
            if proc.returncode != 0:
                violations.append(ContractViolation(entry["path"], entry["sha256"], None))
                continue
            actual = hashlib.sha256(proc.stdout).hexdigest()
            if actual != entry["sha256"]:
                violations.append(ContractViolation(entry["path"], entry["sha256"], actual))
        return violations

    def verify_tree_matches_tag(self, tree_root: pathlib.Path | None = None) -> list[ContractViolation]:
        """Re-hash **every** entry, contract or not — "is this tree really `program-v0`?" (S26).

        Different question from `verify_contract_files`, which asks "has anything immutable been
        touched?" and is therefore silent about the four editable files. Those four are exactly the
        ones an optimizer run rewrites, so after any run the tree no longer matches the tag it
        still names, and nothing noticed. A run labelled `program-v0` whose adjudicator is v3's is
        an unreadable data point, and it is unreadable *afterwards*, when the money is spent.

        Returns violations rather than raising, matching its sibling: the dispatcher decides the
        failure mode.
        """
        return self._rehash(self.entries, tree_root)


# =================================================================================================
# Runner — nested dispatch, with the preflight and the bounds the engine does not provide
# =================================================================================================


@dataclass(frozen=True)
class InvocationResult:
    """One nested headless Claude Code session's outcome."""

    exit_code: int
    cost_usd: float
    duration_seconds: float
    timed_out: bool = False
    detail: str = ""
    #: The nested session's own id, read from the `system/init` event of the stream. It is the
    #: filename Claude Code writes its transcript under, which is what makes the judge's full
    #: reasoning trace reachable at all -- see :func:`_parse_stream_meta`.
    session_id: str | None = None
    #: The RESOLVED model id (`claude-haiku-4-5`), not the alias that was requested (`haiku`).
    #: A number is only reportable alongside the instrument that produced it, and the alias is
    #: not the instrument -- it is a pointer that moves when Anthropic ships a new Haiku.
    model: str | None = None
    #: The session's whole `stream-json` output, as captured. ⚠ **Retained rather than parsed and
    #: dropped (1d, 2026-09-18).** The judge's reasoning trace used to be recovered by globbing the
    #: HOST's `~/.claude/projects` for `session_id` — which a contained session does not write to,
    #: because a `--rm` container discards its own. Worse, the lookup is guarded at every step, so
    #: inside a container every `trace_ref` would be `null` while the run still reported `status:
    #: ok`. This is the same bytes, already in hand, and it does not depend on a cache Claude Code
    #: owns and prunes.
    stream: str = ""


#: A seam, so every offline gate below can drive the Runner without spending money. The real
#: implementation is :func:`headless_claude_invoke`.
Invoker = Callable[[Sequence[str], pathlib.Path, float], InvocationResult]


def _parse_cost(stdout: str) -> float:
    """Pull real metered spend out of the CLI's own JSON output.

    Deliberately NOT `parse_verdict.estimate_cost_usd`: its ``PRICING`` table covers four model ids
    and contributes nothing for anything unlisted, it falls back to an 0.85 input/output split
    because real ledger rows carry null token counts, and the ledger it reads is produced by a
    hand-transcription step no committed prompt performs. Estimation stays for *forecasting*
    (the dispatcher's preflight); accounting uses the number the CLI actually reports.
    """
    total = 0.0
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = obj.get("total_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total = float(value)
    return total


#: The JUDGE's model, NOT the optimizer's -- and the only model choice that moves the bill. The
#: judge runs one nested session per claim, ~113 an iteration, against the optimizer's one; at
#: Opus prices that was ~$95 an iteration and ~$0.84 a claim, measured.
#:
#: Haiku is ~5x cheaper, which at a fixed budget buys ~5x the VAL -- and VAL SIZE, not judge
#: quality, is what the 2026-09-02 run actually ran out of: its effects were ~1 claim ~ 0.03
#: macro-F1 against n=50, which is noise. Buying resolution is worth more here than buying a
#: better judge. Phil's call 2026-09-03, explicitly revisitable, hence `--model` rather than a
#: hard-coded string.
#:
#: ⚠ Changing it invalidates `program-v0`'s baseline (0.4949 was measured on Opus) and any canary
#: pinned under the previous model. `canary.load` refuses that mismatch rather than trusting the
#: caller to remember -- the same guard it already applies to `profile`, for the same reason: a
#: guard silently comparing against a different instrument is worse than no guard.
#:
#: Named here rather than defaulted in two signatures so `dispatcher` and `canary` agree on what
#: "no --model was given" means without either restating it.
DEFAULT_JUDGE_MODEL = "haiku"

#: The predicted label recorded for a claim whose verdict could not be parsed at all. Deliberately
#: NOT a member of the Sarol 9-class enum, so it can never accidentally match gold and is counted
#: by `score_sarol3` exactly as any other wrong answer. A mangled verdict is a wrong answer -- it
#: is not an absent one, and treating it as absent is what let 7 bad claims void 93 good ones.
INVALID_OUTPUT_LABEL = "INVALID_OUTPUT"

#: The frontier metric's name. One definition, shared by the scorer's output, the release payload
#: and the gate that checks the optimizer's prompt names the objective the adapter reports -- so
#: a rename cannot leave the prompt describing a metric nothing computes.
#:
#: Renamed 2026-09-07 from `sarol_macro_f1_6class`, which was wrong twice over by the end: the
#: objective had stopped being six-class (the "6" was an artifact of the pool-filter bug) and then
#: stopped being macro-F1 at all. It is overall accuracy over the nine emittable labels.
PRIMARY_METRIC_NAME = "sarol_accuracy_9class"


def _parse_stream_meta(stdout: str) -> "tuple[str | None, str | None]":
    """``(session_id, resolved_model)`` from the CLI's own stream-json output.

    Both ride on the `system`/`init` event. The session id is the only thing that makes the
    judge's reasoning trace reachable: `--output-format stream-json --verbose` streams the whole
    trace through this pipe, :func:`headless_claude_invoke` reads the cost out of it and drops
    the rest, and Claude Code separately persists the same session to
    ``~/.claude/projects/<slug>/<session_id>.jsonl``. Without the id those transcripts are an
    undifferentiated pool -- 691 of them survived the 2026-09-02 run with nothing linking any of
    them to a claim.

    The model is read here rather than taken from ``self.model`` because the request carries an
    ALIAS and the response carries the resolution. Recording `haiku` would make a run
    unreproducible the day a new Haiku ships; recording `claude-haiku-4-5` would not.
    """
    session_id = model = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if session_id is None and isinstance(obj.get("session_id"), str):
            session_id = obj["session_id"]
        if model is None and obj.get("type") == "system" and isinstance(obj.get("model"), str):
            model = obj["model"]
        if session_id and model:
            break
    return session_id, model


#: ⚠ **``find_transcript`` was deleted on 2026-09-18, and it should stay deleted.** It globbed the
#: HOST's ``~/.claude/projects/`` for a nested session's transcript. A contained session writes that
#: directory inside its own ``--rm`` container, so the glob finds nothing — and since the lookup was
#: guarded at every step, the result was not an error but a null ``trace_ref`` under a run that
#: still reported ``status: ok``. The replacement is not a mount: ``InvocationResult.stream`` is the
#: same bytes, already captured, and persisting them host-side also stops citing evidence for a
#: published result out of a cache Claude Code owns and prunes.


def headless_claude_invoke(
    cmd: Sequence[str], cwd: pathlib.Path, timeout_seconds: float
) -> InvocationResult:
    """Run one nested headless session under a hard timeout.

    ``loop.py`` has no timeout anywhere, so the bound has to live here: an agentic Runner that
    hangs would otherwise stall the whole optimization loop with no stop.

    **Why a process group rather than plain ``subprocess.run(timeout=...)``.** Hardening, not a
    fix for an observed defect — the distinction matters, so read this before "simplifying" it
    back. ``subprocess.run`` kills only the *direct* child on timeout and then drains its pipes;
    ``claude`` spawns grandchildren (``bg-pty-host``, ``bg-spare``, tool subprocesses) that
    inherit those pipes, so killing the root alone can leave the drain waiting on a descendant.
    Running in its own session (``start_new_session=True``) and killing the whole **group** closes
    that gap, and the post-kill drain is itself bounded, because a guard that can hang is not a
    guard. Net effect: the call returns within ``timeout_seconds + 30`` whatever the child spawned.

    ⚠ **A long wall-clock gap here is not automatically a hang.** On 2026-09-02 a claim showed a
    101-minute gap between its evidence envelope and the next claim's, with no verdict written.
    That was **the laptop sleeping** (Phil), not a stuck session: macOS's monotonic clock does not
    advance across sleep, so the timeout correctly did not fire — almost no time had passed from
    the process's point of view. The claims either side ran in 82s and 4min. Before treating a gap
    like that as a timeout bug, check whether the machine was awake, and run long batches under
    ``caffeinate -i`` so it stays that way.
    """
    started = time.monotonic()
    proc = subprocess.Popen(
        list(cmd),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        # Its own process group, so one signal reaches the session AND everything it spawned.
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        try:
            # Bounded: the group is dead, so the pipes are closed and this returns at once. The
            # timeout is belt-and-braces against a pathological descendant that escaped the group.
            proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        return InvocationResult(
            exit_code=124,
            cost_usd=0.0,
            duration_seconds=time.monotonic() - started,
            timed_out=True,
            detail=f"timed out after {timeout_seconds}s (process group killed)",
        )
    session_id, model = _parse_stream_meta(stdout or "")
    return InvocationResult(
        exit_code=proc.returncode,
        cost_usd=_parse_cost(stdout or ""),
        duration_seconds=time.monotonic() - started,
        detail=(stderr or "").strip()[:500],
        session_id=session_id,
        model=model,
        stream=stdout or "",
    )


def _kill_process_group(proc: "subprocess.Popen") -> None:
    """SIGKILL the child's whole process group, falling back to the child alone."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        # Already reaped, or the platform would not give us the group. Killing the direct child is
        # strictly better than nothing, even though it is what left grandchildren behind before.
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def installed_paperclip_version(
    runner: Callable[[Sequence[str]], subprocess.CompletedProcess] | None = None,
) -> str | None:
    """``paperclip --version``, or None when the CLI is absent."""
    run = runner or (lambda c: subprocess.run(list(c), capture_output=True, text=True, timeout=30))
    try:
        proc = run(["paperclip", "--version"])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def _normalize_version(text: str | None) -> str | None:
    """``"paperclip, version 0.5.11"`` -> ``"0.5.11"``, so a cosmetic banner change is not a
    spurious mismatch while a real version drift still is."""
    if not text:
        return None
    match = re.search(r"(\d+\.\d+(?:\.\d+)*)", text)
    return match.group(1) if match else text.strip()


@dataclass
class ClaimRecord:
    claim_id: str
    citekey: str
    staging_dir: pathlib.Path
    source_mode: str = "pdf"

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "ClaimRecord":
        return cls(
            claim_id=obj["claim_id"],
            citekey=obj["citekey"],
            # Resolved against the repo, so a pin written repo-relative (`canary.py`'s
            # `portable_staging_dir`, which keeps the committed pin free of an absolute home
            # path) survives a move between checkouts. Joining an absolute path with a root
            # yields the absolute path unchanged, so batches that still carry one are untouched.
            #
            # ⚠ **And `.resolve()`d here, once, rather than at each use.** The container grant
            # holds resolved host paths, so a claim carrying the unresolved spelling of the same
            # directory silently disables the host-path leak check: on macOS a batch written with
            # `/var/folders/...` never matches a grant holding `/private/var/folders/...`, and the
            # guard returns "no leak" for a prompt full of host paths. Found by mutation, 2026-09-18.
            staging_dir=(REPO_ROOT / obj["staging_dir"]).resolve(),
            source_mode=obj.get("source_mode", "pdf"),
        )


def materialize_program(
    store: "SarolProgramStore", dest: pathlib.Path, *, tag: str = "program-v0"
) -> pathlib.Path:
    """Write the frozen program into ``dest`` and return it, ready to be a container's program mount.

    ⚠ **A Runner can no longer be pointed at the repo root, and that is the containment change.**
    The grant puts ``program_dir`` in as a read-only mount and the engine refuses a mount that
    contains a denied path -- and the repo root contains three of them (``optimizer/findings``,
    ``meta-learnings.md``, ``optimizer/context``). So every caller that used to hand the Runner a
    checkout now hands it a materialized tree instead. `canary.pin` was the last one, and it was
    refused outright until this existed (found by review, 2026-09-18).

    ⚠ **Two older copies of this sequence remain**, in ``scripts/run_baseline.py:110-126`` and
    ``scripts/materialize_smoke.py:93-120``. They work and they are verified; they should adopt
    this helper next time either is touched, rather than in a slice that cannot run the baseline
    it would be changing.

    ``tag`` is resolved to its COMMIT: ``program-v0`` is an annotated tag, so a bare rev-parse
    returns the tag object's sha -- a different id for the same program, which would make one run
    look like two systems.
    """
    _import_engine()  # puts the engine on sys.path, with its own message if it is absent
    from engine.materialize import materialize  # noqa: PLC0415
    from engine.schemas import ManifestEntry, ProgramManifest  # noqa: PLC0415

    fields = set(inspect.signature(ManifestEntry).parameters)
    manifest = ProgramManifest(
        entries=tuple(
            ManifestEntry(**{k: v for k, v in entry.items() if k in fields})
            for entry in store.raw["entries"]
        ),
        combined_hash=store.raw["combined_hash"],
    )
    sha = subprocess.run(
        ["git", "-C", str(store.repo_root), "rev-parse", f"{tag}^{{commit}}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    dest = pathlib.Path(dest)
    materialize(manifest, sha, repo_root=store.repo_root, dest=dest)
    return dest


def staging_root(claim: ClaimRecord) -> pathlib.Path:
    """The host directory granted to the container for this claim — its staging dir's parent.

    The **root**, not the claim's own directory: a grant scopes a worker's whole life, and one
    session per claim is the N=1 case of that rather than the design (Phil, 2026-09-16). Every
    claim staged under one root therefore shares one grant, and each dispatch names its own item
    inside it.
    """
    return claim.staging_dir.resolve().parent


def container_staging(claim: ClaimRecord, scope) -> str:
    """Where this claim's staged tree appears **inside** the container, read off the grant.

    ⚠ **Derived from the mount set, not computed beside it** — the idiom ``isolation.add_dirs``
    already uses. The mount set is what makes a path real inside the container, so deriving this
    from anything else lets the two disagree silently, and a prompt naming a directory that does
    not exist is a dispatch the adjudicator cannot complete: it reads as a model failure rather
    than as the wiring bug it is.

    Raises:
        ValueError: the grant mounts nothing as staging, or mounts a tree this claim is not
            staged under — i.e. it is some other claim's grant.
    """
    mounted = next(
        (
            pathlib.Path(host)
            for host, container in scope.writable
            if container == isolation_mod.CONTAINER_STAGING
        ),
        None,
    )
    if mounted is None:
        raise ValueError(
            f"UNDISPATCHABLE:this grant mounts nothing at {isolation_mod.CONTAINER_STAGING}, so "
            f"claim {claim.claim_id} has nowhere to read its evidence or write its verdict"
        )
    try:
        rel = claim.staging_dir.resolve().relative_to(mounted)
    except ValueError:
        raise ValueError(
            f"UNDISPATCHABLE:claim {claim.claim_id} is staged at {claim.staging_dir}, outside the "
            f"{mounted} this grant mounts at {isolation_mod.CONTAINER_STAGING} — this is another "
            "claim's grant, and the prompt would name a path that does not exist in the container"
        ) from None
    # Exactly one level down, and that is the grant's shape rather than a formatting rule: the
    # staging root holds the claims and each request names an item inside it (Phil, 2026-09-16).
    # A grant one level higher still renders a consistent path, so nothing downstream would
    # notice -- while handing the container everything beside the staging root, which on the real
    # layout is the optimizer's own scores.
    if len(rel.parts) != 1:
        raise ValueError(
            f"UNDISPATCHABLE:this grant mounts {mounted}, which is not claim "
            f"{claim.claim_id}'s own staging root but {len(rel.parts)} levels above it. That "
            "grants the container everything else under it too"
        )
    return "/".join((isolation_mod.CONTAINER_STAGING, *rel.parts))


@dataclass
class CanarySpec:
    """A pinned claim with a known verdict, processed before any scored claim (`sarol`'s D46).

    This guards the most expensive failure mode available here: a silently broken scorer or
    pipeline. A metric bug of that shape does not announce itself, and it invalidates every
    iteration after the break rather than just the current one -- so the canary's job is to turn
    an invisible, retroactive failure into a loud, immediate one.

    A canary miss returns ``infra_error`` before the first scored claim is dispatched: a run whose
    instrument moved is not a run that produced a worse number, and must not be scored as one.
    """

    claim: ClaimRecord
    expected_verdict: str

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "CanarySpec":
        return cls(
            claim=ClaimRecord.from_dict(obj["claim"]),
            expected_verdict=obj["expected_verdict"],
        )


def load_batch(input_ref: str | pathlib.Path) -> list[ClaimRecord]:
    """Read a dispatcher-owned batch file. Never inline claim content — a path, per ``RunInputs``."""
    obj = json.loads(pathlib.Path(input_ref).read_text(encoding="utf-8"))
    return [ClaimRecord.from_dict(c) for c in obj["claims"]]


def batch_totals(records: "Iterable[dict[str, Any]]") -> "tuple[int, float]":
    """``(sub_invocation_count, cost_usd)`` summed from the records themselves.

    This replaces a ``counter`` dict that the dispatch loop mutated in place with non-atomic
    ``+=``. Under concurrent dispatch that was the one genuinely shared mutable object in the
    Runner, and the fix is to delete the shared state rather than lock it: every stage record
    already carries its own ``cost_usd``, and one stage entry is written per ``invoke`` call, so
    both totals are recoverable from what the batch returns. A lock would have preserved a
    variable that never needed to exist.

    Exact, not approximate -- the old counter incremented once per ``invoke`` and added that
    call's ``cost_usd``, which is one-to-one with the stage entries written beside them, including
    on the timeout and non-zero-exit paths that return early.
    """
    subs = 0
    cost = 0.0
    for record in records:
        for stage in (record.get("stages") or {}).values():
            subs += 1
            cost += float(stage.get("cost_usd") or 0.0)
    return subs, cost


#: Every file that constructs a Runner. Checked by source inspection in `_selftest` (V2c).
_RUNNER_SITE_FILES = (
    _HERE / "adapter.py",
    _HERE / "dispatcher.py",
    _HERE / "canary.py",
    _HERE.parent / "scripts" / "run_baseline.py",
)

#: How many places construct a Runner. ⚠ **If this number moves, read the new site before changing
#: it.** The container boundary is only as good as the set of sites that take one, and a count is
#: the only thing that notices a new site quietly copying `fake_container()` from its neighbour.
#: The census, which the plan put at 22 before this change: **22** selftests in this file, its
#: `_RealInvokerRunner` subclass (the one the plan warned matches no text search), **1** selftest
#: in `canary.py`, and **3** that can run outside a test -- `dispatcher.build_components`,
#: `canary.pin` and `scripts/run_baseline.py`. Plus **4** to watch the constructor's refusal
#: actually fire: two passing an explicit `None`, one a tag-named image, one the accepted
#: shipping shape.
#: ⚠ Four selftest sites arrived with the contained dispatch (1f-b): a Runner whose session
#: streams nothing, which controls the trace no longer being read off the host; the two-version
#: Runner that proves the prefix is rendered per dispatch (V2d); the empty-batch refusal; and
#: `canary.py`'s real Runner, which is the only gate that builds a grant on the canary's own path.
#: ⚠ Three more arrived with Phase 2's version-addressed command discovery: the Runner handed an
#: incomplete freeze, the one whose working checkout is empty while the version is complete, and the
#: two-version render that proves the BYTES followed the mount (V3d builds one per version in a
#: loop, which the AST census counts once).
#: ⚠ Two more arrived with Phase 3's configuration pin: the Runner on an unpinned boundary, which
#: must be refused, and the one on the pinned boundary beside it, which must not — a refusal gate
#: with no passing case beside it cannot tell "correctly refused" from "always refuses".
_EXPECTED_RUNNER_SITES = 36


#: Where the frozen slash-command file lives, and the ONLY place it counts.
#:
#: 🚩 **This used to be a three-location search (`.claude/commands/`, `src/commands/`,
#: `experiments/sarol-2024/commands/`) and Codex was right to call that a hole (2026-09-19).** The
#: broad search made sense when the check asked "does some checkout have this file somewhere?". It
#: does not survive version-addressing: the question is now "does THIS frozen version carry it?",
#: and the manifest answers that at exactly one path (entry #10). A materialized tree missing
#: `.claude/commands/` but carrying a stale copy under `src/commands/` would have passed a
#: completeness check on a tree that is not in fact complete — and `materialize` only ever writes
#: manifest paths, so the other two arms could not match anything legitimate anyway.
COMMAND_REL_TEMPLATE = ".claude/commands/{name}.md"


#: The claim every dispatch gate stages, and the corpus line that answers it.
_GATE_CLAIM_TEXT = "deep learning reconstruction accelerates MRI fourfold"


def _materialized_program(root: pathlib.Path, name: str = "mat") -> pathlib.Path:
    """A materialized program tree holding the one frozen file a dispatch reads: the prompt.

    Copied from the repo rather than faked, so a gate asserting on the rendered prompt asserts on
    the real slots. A tree without it is not a program the Runner can dispatch, which is why these
    gates cannot keep passing a bare temp directory as the materialized path.
    """
    dest = root / name / dispatch_prompt.TEMPLATE_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / dispatch_prompt.TEMPLATE_REL, dest)
    return root / name


def _staged_batch(
    root: pathlib.Path,
    *,
    claim_ids: Sequence[str] = ("C1",),
    split: str = "train",
    citekey: str = "k1",
    name: str | None = None,
) -> "tuple[pathlib.Path, pathlib.Path]":
    """One batch staged on disk, in the layout a contained run actually has.

    ⚠ **The shape is load-bearing, not tidiness.** The grant denies the optimizer's output root and
    grants the staging root *inside* it, so the flat layout these gates used to use — staging as a
    sibling of the materialized program — is refused by the engine for granting a mount that sits
    above a denied path. Production would be refused for the same reason, which is the point of
    making the fixture match it::

        <root>/mat/                            the materialized program: read-only, and the cwd
        <root>/run/<split>/                    the optimizer's output root: DENIED
        <root>/run/<split>/staging/            the staging root: the one writable grant
        <root>/run/<split>/staging/<claim_id>/ one claim

    Each claim gets both a corpus to retrieve over (so the mechanical producer under ``retrieval``
    does real work) and a finished envelope (so a gate that only renders a command needs no
    producer run). Returns ``(output_root, batch_path)``.
    """
    out_root = root / "run" / split
    staging_dir_root = out_root / "staging"
    for claim_id in claim_ids:
        staging = staging_dir_root / claim_id
        (staging / "ledger" / "evidence").mkdir(parents=True, exist_ok=True)
        (staging / "pdfs" / citekey).mkdir(parents=True, exist_ok=True)
        (staging / "staging_info.json").write_text(
            json.dumps(
                {
                    "citekey": citekey,
                    "claim_text_normalized": _GATE_CLAIM_TEXT,
                    "source_mode": "corpus",
                    "multi_cit_context": "single",
                    "source_description": "corpus-chunks (N=3)",
                }
            ),
            encoding="utf-8",
        )
        (staging / "pdfs" / citekey / "content.txt").write_text(
            "L1 [p?]: a fourfold acceleration was achieved for MRI reconstruction\n"
            "L2 [p?]: unrelated sentence about cardiology cohorts\n"
            "L3 [p?]: deep learning methods were applied throughout\n",
            encoding="utf-8",
        )
        (staging / "ledger" / "evidence" / f"{claim_id}.json").write_text(
            json.dumps(
                {
                    "claim_id": claim_id,
                    "run_id": "run_test",
                    "citekey": citekey,
                    "claim_text": _GATE_CLAIM_TEXT,
                    "claim_type": dict(evidence_producers.STAGED_CLAIM_TYPE),
                }
            ),
            encoding="utf-8",
        )
    batch = root / (name or f"batch-{split}.json")
    batch.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": claim_id,
                        "citekey": citekey,
                        "staging_dir": str(staging_dir_root / claim_id),
                    }
                    for claim_id in claim_ids
                ]
            }
        ),
        encoding="utf-8",
    )
    return out_root, batch


#: Markdown delimiters that wrap a path in the adjudicator's prompt. ⚠ **Stripped before the
#: host-path leak check, and that is not cosmetic.** The engine tokenizes on shell-ish separators
#: (whitespace, ``:``, ``=``, quotes, brackets) — so a path written as `` `/host/path` ``, which is
#: how every path in the prompt template is written, begins with a backtick, is not seen as a path
#: at all, and the guard returns "no leak" for a prompt made entirely of host paths. Found by
#: mutation on 2026-09-18; worth pushing upstream, since any consumer handing a worker markdown
#: has the same hole.
_MARKDOWN_DELIMITERS = str.maketrans({c: " " for c in "`*<>{}|"})


def _unmarked(text: str) -> str:
    """``text`` with markdown delimiters blanked, so a path inside them is still a path."""
    return text.translate(_MARKDOWN_DELIMITERS)


def _claim_dispatched(cmd) -> str:
    """Which claim a rendered dispatch names, read off its container staging path.

    ⚠ Returns ``"?"`` rather than raising when the marker is absent. The gates' spy invokers call
    this, and a spy that raises turns a check that should go RED into a crashed suite -- which
    would let a mutation that breaks the module pass for a mutation the gates caught.
    """
    marker = isolation_mod.CONTAINER_STAGING + "/"
    tail = cmd[-1] if cmd else ""
    return tail.split(marker)[1].split("/")[0] if marker in tail else "?"


def _manifest_of(res) -> "dict[str, Any]":
    """The run manifest a Runner returned, or ``{}`` when it refused before writing one.

    Indexing ``artifact_refs[0]`` straight turns a REFUSED run into a traceback, and a crashed
    suite is not a red check: a mutation that breaks the module must not be able to pass for a
    guard that caught it. So the gates read through this and assert on the contents.
    """
    if not getattr(res, "artifact_refs", ()):
        return {}
    return json.loads(pathlib.Path(res.artifact_refs[0].path).read_text(encoding="utf-8"))


def _raises_valueerror(fn) -> bool:
    """Did ``fn`` refuse with a ``ValueError``? Used for the constructor's refusal controls."""
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


def _refusal_mentions(fn, needle: str) -> bool:
    """Did ``fn``'s refusal actually name ``needle``? A refusal nobody can act on is half a gate."""
    try:
        fn()
    except ValueError as exc:
        return needle in str(exc)
    except Exception:
        return False
    return False


def _runner_construction_sites() -> "list[dict[str, Any]]":
    """Every Runner construction in the repo, found by parsing the source (V2c).

    ⚠ **Parsed, not text-searched, and the first version of this was text-searched and wrong in two
    ways at once.** It matched its own docstring — which mentions the constructor by name — and the
    paren-matching then ran away through the prose that followed, so it reported 3 sites in a file
    holding 20 and called that a pass. A check that miscounts in the safe direction is worse than
    no check: it certifies a boundary over sites it never saw. Parsing has neither failure mode,
    because a name inside a string is not a call.

    A registry populated at import time would also have been wrong here: the property is about code
    that *exists*, so a new site that forgets the boundary must show up even if no test runs it.

    Subclass constructions count. ``_RealInvokerRunner`` does not override the constructor, so it
    reaches the same refusal while matching no search for the parent's name. A subclass *definition*
    is not a call, so it is naturally excluded rather than needing a special case.

    ⚠ **What this does NOT catch, stated because a guard whose limits are unwritten gets
    over-trusted:** it matches the callee by *name*, so a construction through a local alias
    (``Runner = SarolRunner; Runner(store)``) is invisible to it. That is not the failure this
    guards — the failure is a new site that simply forgets the boundary, which does match by name —
    and the constructor's own refusal still fires either way at run time. The census exists to make
    a forgotten site fail *offline*, not to be the only thing standing between here and a leak.
    """
    import ast  # noqa: PLC0415

    wanted = {"SarolRunner", "_RealInvokerRunner"}
    sites: "list[dict[str, Any]]" = []
    for path in _RUNNER_SITE_FILES:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        selftest_line = next(
            (
                node.lineno
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_selftest"
            ),
            None,
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name not in wanted:
                continue
            stated = [kw for kw in node.keywords if kw.arg == "container"]
            sites.append(
                {
                    "file": path.name,
                    "line": node.lineno,
                    "states_container": bool(stated),
                    "uses_fake": any(
                        "fake_container" in ast.unparse(kw.value) for kw in stated
                    ),
                    # An explicit `container=None` is the ONE legitimate way to say "this site is
                    # here to watch the refusal fire". It still counts as stating a container --
                    # the plan's requirement is that every site is *visible* about it -- but no
                    # site that can run outside a selftest may use it.
                    "states_none": any(
                        isinstance(kw.value, ast.Constant) and kw.value.value is None
                        for kw in stated
                    ),
                    "in_selftest": selftest_line is not None
                    and node.lineno > selftest_line,
                }
            )
    return sites


class SarolRunner:
    """Dispatches the frozen program over a batch of claims and reports what happened.

    Never raises. Every failure becomes a ``RunArtifacts.status`` the Scorer can refuse, because the
    engine checks that status on exactly one of its three calls and wraps none of them.
    """

    def __init__(
        self,
        program_store: SarolProgramStore,
        *,
        working_checkout: pathlib.Path = REPO_ROOT,
        output_root: pathlib.Path | None = None,
        invoke: Invoker | None = None,
        per_call_timeout_seconds: float = 900.0,
        per_call_max_budget_usd: float = 2.0,
        paperclip_version_probe: Callable[[], str | None] | None = None,
        model: str = DEFAULT_JUDGE_MODEL,
        canary: "CanarySpec | None" = None,
        command_name: str = "sarol-eval-item",
        require_command: bool = True,
        profile=None,
        output_roots: "dict[str, pathlib.Path] | None" = None,
        max_workers: int = 1,
        container: "isolation_mod.ContainerConfig | None" = None,
    ) -> None:
        # ⚠ **The 1f refusal locus, and it is here rather than in `build_components` for a
        # measured reason.** There are THREE ways to reach a Runner: through `build_components`,
        # by direct construction (`canary.py`, `scripts/run_baseline.py`), and by handing
        # `run_optimization` a pre-built `components=` dict that skips `build_components` entirely
        # (`dispatcher.py:604`, `:748`). Only the constructor sits under all three — a gate in
        # `build_components` would miss the baseline recut AND the `components=` path while the
        # suite reported green.
        #
        # `container` is declared with a `None` default only so this message can replace a bare
        # TypeError. It is not optional: there is no value of it meaning "no container", and
        # nothing that produces or guards a reportable number gets an opt-out, because a baseline
        # measured uncontained against iterations measured contained is not a weaker guarantee but
        # an invalid comparison.
        container_refusal = isolation_mod.container_problem(container)
        if container_refusal is not None:
            raise ValueError(f"refusing to build a Runner: {container_refusal}")
        self.container = container

        self.program_store = program_store
        # A real checkout, not the materialized tree: that tree is chmod'd read-only, its `.claude/`
        # symlinks materialize as regular files containing their target string, and the orchestrator
        # is deliberately not in the fileset. `{{spec_root}}` is what points at the frozen bytes.
        self.working_checkout = pathlib.Path(working_checkout).resolve()
        self.output_root = pathlib.Path(output_root).resolve() if output_root else None
        self.invoke: Invoker = invoke or headless_claude_invoke
        self.per_call_timeout_seconds = per_call_timeout_seconds
        # A HARD per-call spend cap at the actual spender. The dispatcher's preflight only
        # forecasts and refuses at batch boundaries; nothing there stops one runaway session.
        # The engine stops neither -- its only budget check is on the optimizer agent's tokens.
        self.per_call_max_budget_usd = per_call_max_budget_usd
        self.paperclip_version_probe = paperclip_version_probe or installed_paperclip_version
        self.model = model
        self.canary = canary
        self.command_name = command_name
        self.require_command = require_command
        # Which stages this run dispatches, and therefore what it costs and what it measures.
        # Defaults to the landed three-stage pipeline, so adding profiles changed no behaviour.
        self.profile = profiles_mod.get(profile)
        # C6.9: per-split output roots, stated rather than derived. The VAL root must lie outside
        # the optimizer's readable mounts, and "outside" is not something a derived default can
        # promise -- `dispatcher.val_isolation_problem` is what checks it.
        self.output_roots = {k: pathlib.Path(v) for k, v in (output_roots or {}).items()}
        # How many claims are dispatched at once. Claims are independent -- each is its own nested
        # session writing to its own `claim_id`-keyed paths -- so this changes only wall-clock, not
        # what any session sees. Every prompt, subagent and materialized tree stays byte-identical,
        # which is why raising it does NOT move the instrument or invalidate an earlier baseline.
        #
        # Defaults to 1 (exactly the old serial dispatch) because the useful ceiling is EMPIRICAL,
        # not architectural: each `claude -p` spawns a subagent, so N workers is ~2N concurrent API
        # consumers plus N node processes. Ramp it on a real run and watch for rate-limit errors
        # rather than inheriting an unverified default here.
        self.max_workers = max(1, int(max_workers))

    # -- preflight ---------------------------------------------------------------------------

    def paperclip_pin_error(self) -> str | None:
        """The pin is enforced, not merely recorded.

        The extractor prompt loads the paperclip command reference at run time via ``paperclip
        skill``, and that reference lives outside the frozen fileset — so without this check two
        runs of one program version could diverge with no manifest diff. Returns an error string on
        mismatch, else None.
        """
        pinned = self.program_store.runtime_pins.get("paperclip_cli")
        if not pinned:
            return None
        installed = self.paperclip_version_probe()
        if installed is None:
            return f"paperclip CLI not found; program-v0 pins {pinned!r}"
        want, got = _normalize_version(pinned), _normalize_version(installed)
        if want != got:
            return f"paperclip version mismatch: pinned {want!r}, installed {got!r}"
        return None

    def isolation_configuration(self, scope) -> dict:
        """What boundary this run puts the program behind, as the dict the pin hashes.

        Rendered on the engine's **deny-all** policy rather than the shipping allowlist, on purpose:
        standing up a Squid sidecar to find out what we are about to run would make a preflight gate
        cost a container. Nothing network-shaped is read from that render — the policy comes from
        the stated :attr:`isolation.ContainerConfig.policy` — and the two renders are asserted to
        agree mount for mount by ``isolation.py``'s own selftest.

        The inner argv is rendered with an **empty prompt**. The prompt is not part of the
        configuration, and rendering a real one at preflight would need the evidence envelope, which
        the producer has not written yet.
        """
        return isolation_mod.configuration(
            container=self.container,
            scope=scope,
            prefix=isolation_mod.dispatch_prefix(
                scope=scope,
                image=self.container.image,
                network_policy=isolation_mod.DENY_ALL_EGRESS,
            ),
            inner_command=isolation_mod.inner_command(
                scope=scope,
                prompt="",
                model=self.model,
                max_budget_usd=self.per_call_max_budget_usd,
            ),
            program_entries=[e["path"] for e in self.program_store.entries],
        )

    def isolation_pin_error(self, scope) -> str | None:
        """Does the boundary about to run match the pin committed in the manifest? Error, or None.

        ⚠ **Refuses before anything is spent**, beside the paperclip pin, and for the same reason:
        a run that produces ten paid verdicts under a configuration nobody approved cannot be
        un-run, and its numbers cannot honestly be published either.
        """
        try:
            computed = isolation_mod.configuration_hash(self.isolation_configuration(scope))
        except (ValueError, OSError) as exc:
            return f"cannot compute the isolation configuration: {str(exc)[:200]}"
        policy = self.container.policy
        return isolation_mod.configuration_pin_problem(
            computed,
            committed=isolation_mod.committed_configuration_pin(policy),
            policy=policy,
        )

    # -- dispatch ----------------------------------------------------------------------------

    def _inner_command(
        self,
        stage: str,
        claim: ClaimRecord,
        *,
        scope,
        materialized_path: pathlib.Path,
        run_id: str,
    ) -> list[str]:
        """The adjudicator's own argv, in container paths only.

        ⚠ **This replaced a slash command, and that is OQ1 rather than a refactor.** The old form
        told a *driver* session to run ``/sarol-eval-item``, which then spawned the adjudicator as
        a subagent -- so the container boundary and the session boundary were two different things
        and the inner one was inherited rather than stated. Now the prompt is rendered here
        (``dispatch_prompt``) and arrives on argv: one container, one session, one boundary.

        Every path in it is a container path. The template is read from the **host** copy of the
        materialized tree while ``spec_root`` names where that same tree is mounted inside the
        container -- the one place the two spellings legitimately differ, which is why
        ``dispatch_prompt.render`` takes them separately.

        Raises:
            ValueError: the stage has no prompt to render, the evidence the prompt points at is
                missing or disagrees with staging (``dispatch_prompt`` raises, with its own
                ``CODE:detail`` prefixes), or the assembled command still carries the permission
                bypass or a host path the container cannot resolve.
        """
        if stage not in profiles_mod.IMPLEMENTED_STAGES:
            raise ValueError(
                f"STAGE_UNIMPLEMENTED:{stage} -- only {', '.join(profiles_mod.IMPLEMENTED_STAGES)} "
                "has a prompt to render, so there is nothing to dispatch for this stage. "
                "`profiles.unrunnable_reason` refuses such a profile at preflight before any "
                "spend; reaching here means that check was bypassed"
            )
        prompt = dispatch_prompt.render(
            staging_dir=claim.staging_dir,
            claim_id=claim.claim_id,
            run_id=run_id,
            run_output_dir=container_staging(claim, scope),
            spec_root=isolation_mod.CONTAINER_PROGRAM,
            template_root=materialized_path,
        )
        # The audit copy, beside the evidence and the verdict. Not an input to anything -- the
        # prompt travels on argv -- but a surprising verdict is only readable against the exact
        # text that produced it.
        dispatch_prompt.write_rendered(claim.staging_dir, claim.claim_id, prompt)
        cmd = isolation_mod.inner_command(
            scope=scope,
            prompt=prompt,
            model=self.model,
            max_budget_usd=self.per_call_max_budget_usd,
        )
        # Both predicates are the existing ones, called on the argv this Runner actually built --
        # the surface an implementer who fixes only the shared wrapper would leave untouched.
        # ⚠ The leak scan takes the prompt and the inner argv, NEVER the docker line: the host side
        # of every bind mount is a host path necessarily, so scanning the whole command is vacuous.
        for problem in (
            isolation_mod.bypass_flag_problem(cmd),
            isolation_mod.told_host_path_problem([_unmarked(prompt), *cmd], scope),
        ):
            if problem is not None:
                raise ValueError(f"UNDISPATCHABLE:{problem}")
        return cmd

    def _dispatch_command(
        self,
        stage: str,
        claim: ClaimRecord,
        *,
        scope,
        materialized_path: pathlib.Path,
        run_id: str,
        render_prefix,
    ) -> list[str]:
        """The whole command line: this dispatch's container prefix, then the adjudicator's argv.

        The prefix is rendered **per dispatch** rather than fixed at construction, because the
        program mount moves per iteration and the staging mount per staging root. One prefix reused
        across either axis silently points a v1 dispatch at v0's bytes, and both produce plausible
        verdicts.

        This is also the seam a gate overrides to stand a cheap process in for ``claude`` without
        stubbing the invoker, so the real process machinery still runs.
        """
        return list(render_prefix(scope)) + self._inner_command(
            stage, claim, scope=scope, materialized_path=materialized_path, run_id=run_id
        )

    def command_path(self, root: pathlib.Path | None = None) -> pathlib.Path | None:
        """Where the nested slash command lives for one program version, if it is there at all.

        ``root`` is **the version being scored** — the materialized tree ``run()`` was handed.
        Omitting it falls back to the working checkout, which is right for a bare structural
        question ("does this repo ship the file at all?") and wrong for anything a run depends on.

        ⚠ **Resolving this against a single fixed directory stopped being valid when the program
        became version-addressed (2a).** The command file is manifest entry #10 and the optimizer
        may edit it, so its bytes differ per version. A check against the working checkout answers
        for whichever version the optimizer wrote last, not for the one about to be scored — and it
        answers *positively* even when the tree being dispatched is missing the file entirely,
        because the repo itself ships one. Both directions are wrong, and both are silent.
        """
        base = pathlib.Path(root) if root is not None else self.working_checkout
        candidate = base / COMMAND_REL_TEMPLATE.format(name=self.command_name)
        return candidate if candidate.exists() else None

    def missing_command_error(self, root: pathlib.Path | None = None) -> str | None:
        """Fail loudly when the committed `/sarol-eval-item` file is missing.

        ⚠ **It is no longer what gets dispatched, and the name now overstates what this checks.**
        Since OQ1 the adjudicator is invoked directly with a prompt rendered by ``dispatch_prompt``
        (from ``prompts/adjudicator-dispatch-sarol.md``), so nothing runs a slash command. The file
        is still a frozen manifest entry and still the human-readable statement of the eval arm, so
        its absence still means the checkout is incomplete -- but the check that actually guards a
        dispatch is ``_inner_command``, which refuses rather than sending one.
        """
        if not self.require_command:
            return None
        base = pathlib.Path(root) if root is not None else self.working_checkout
        if self.command_path(base) is None:
            return (
                f"nested command /{self.command_name} not found at "
                f"{COMMAND_REL_TEMPLATE.format(name=self.command_name)} in {base}"
            )
        return None

    def run(self, materialized_path, inputs):  # positional -- loop.py:334/:335/:410
        """The ``Runner`` protocol. ``(materialized_path, inputs) -> RunArtifacts``."""
        schemas = _import_engine()
        materialized_path = pathlib.Path(materialized_path)

        def artifacts(status: str, *, code: str = "", message: str = "", refs=(), n=0, cost=0.0):
            return schemas.RunArtifacts(
                batch_id=inputs.batch_id,
                status=status,
                artifact_refs=tuple(refs),
                error=schemas.ErrorInfo(code=code, message_redacted=message) if code else None,
                sub_invocation_count=n,
                cost_usd=cost,
            )

        # Negative control: a mismatched pin fails BEFORE any claim is dispatched, so a scored batch
        # can never be produced under the wrong CLI.
        pin_error = self.paperclip_pin_error()
        if pin_error is not None:
            return artifacts("infra_error", code="PAPERCLIP_PIN_MISMATCH", message=pin_error)

        # The command this Runner dispatches has to exist before we spend anything looking for it,
        # and "the command" means the one belonging to THIS version — the materialized tree that is
        # about to be the container's cwd, not the working checkout the optimizer keeps editing.
        command_error = self.missing_command_error(materialized_path)
        if command_error is not None:
            return artifacts("infra_error", code="NESTED_COMMAND_MISSING", message=command_error)

        try:
            claims = load_batch(inputs.input_ref)
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            return artifacts("infra_error", code="BATCH_UNREADABLE", message=str(exc)[:300])

        # Every per-claim artifact -- evidence envelope, verdict JSON, judge trace -- is keyed on
        # `claim_id`, so two claims sharing one id write the SAME paths. Serially that was merely
        # wasteful and deterministic (the second overwrote the first); under concurrent dispatch
        # the two writes race, and the verdict that survives is whichever thread finished last.
        # Concurrency is what turns a harmless duplicate into a corrupt one, so the refusal lands
        # in the same change.
        #
        # No drawn batch can trip this: the pool is a dict keyed on `claim_id`, `cumulative` builds
        # its batch with a set union and `fresh` uses `rng.sample` (without replacement). The
        # exposed path is `--train-inputs` / `--val-inputs`, a hand-written batch JSON that
        # bypasses the sampler entirely -- i.e. exactly where a typo comes from. Refuse loudly
        # rather than race quietly.
        _dupes = sorted({c.claim_id for c in claims if [x.claim_id for x in claims].count(c.claim_id) > 1})
        if _dupes:
            return artifacts(
                "infra_error",
                code="DUPLICATE_CLAIM_IDS",
                message=(
                    f"batch repeats claim_id(s) {', '.join(_dupes[:5])}"
                    f"{' ...' if len(_dupes) > 5 else ''}; every per-claim artifact is keyed on "
                    "claim_id, so duplicates would race on the same verdict and trace paths"
                ),
            )

        # An empty batch has nothing to grant a container for, and nothing to score either: the
        # Scorer's coverage rule would divide by zero and a manifest naming no claims cannot reach
        # the frontier as a number. Refuse it where the batch is read, rather than letting it
        # surface as a StopIteration when the boundary looks for a grant to stand up on.
        if not claims:
            return artifacts(
                "infra_error",
                code="EMPTY_BATCH",
                message=f"{inputs.input_ref} names no claims, so there is nothing to dispatch",
            )

        # Namespace every Runner call under the materialized version it actually ran (Bug 3).
        # The engine calls this Runner THREE times per iteration -- TRAIN and current-VAL against
        # `iter<n>-current`, then the post-commit probe against `iter<n>-<tag>` -- and
        # `materialized_path.name` is the one value already distinct across all three. Without it
        # every VAL call wrote the same `run_manifest.json`, so only the last survived: the first
        # optimization run's three-point VAL curve does not exist on disk, and per-call cost
        # accounting was impossible after the fact. Downstream reads the manifest through the
        # returned `ArtifactRef`, never a derived path, so nothing depends on the old flat layout.
        call_ns = pathlib.Path(materialized_path).name
        explicit = self.output_roots.get(inputs.split)
        if explicit is not None:
            out_dir = pathlib.Path(explicit) / call_ns
        else:
            out_root = self.output_root or (materialized_path.parent / f"runs-{inputs.batch_id}")
            out_dir = pathlib.Path(out_root) / inputs.split / call_ns
        out_dir.mkdir(parents=True, exist_ok=True)

        # Validate against the rubric the program ACTUALLY RAN UNDER -- the materialized copy, not
        # the repo's working tree, which the optimizer may already have edited past this version.
        rubric_path = materialized_path / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
        rollup_order = validate_sarol.load_rollup_order(rubric_path)

        # Where the optimizer's own numbers land, and therefore what the program must not read.
        # Every root this Runner could write to, not only this split's: the VAL root in particular
        # has to stay denied on a TRAIN run, which is what `dispatcher.val_isolation_problem`
        # exists to check.
        denied_roots = [pathlib.Path(p) for p in self.output_roots.values()]
        if self.output_root is not None:
            denied_roots.append(pathlib.Path(self.output_root))
        if explicit is None:
            denied_roots.append(pathlib.Path(out_root))

        # The grant, built BEFORE anything is dispatched. A grant the engine refuses is an
        # infrastructure failure of this run, not a bad verdict, and finding that out after the
        # first claim has been paid for is the expensive way to learn it.
        #
        # One grant per staging ROOT rather than per claim: a grant scopes a worker's whole life,
        # and the canary is staged under the repo while the batch is staged under the run's output
        # root, so a batch legitimately spans two roots. Built here, read-only inside the workers,
        # so nothing mutates shared state under the pool.
        try:
            grants = {
                root: isolation_mod.program_scope(
                    profile=self.profile.name,
                    program_dir=materialized_path,
                    staging_root=root,
                    output_roots=denied_roots,
                )
                for root in sorted(
                    {
                        staging_root(c)
                        for c in ([self.canary.claim] if self.canary is not None else []) + claims
                    }
                )
            }
        except ValueError as exc:
            return artifacts(
                "infra_error", code="PROGRAM_GRANT_REFUSED", message=str(exc)[:300]
            )

        # The configuration this run is about to use, held to the one committed in the manifest --
        # before any claim is dispatched. Checked on EVERY grant, not just the first: two staging
        # roots render two mount sets, and pinning one of them while the other goes unchecked is the
        # partial coverage this gate exists to remove.
        for _root, _scope in sorted(grants.items()):
            pin_problem = self.isolation_pin_error(_scope)
            if pin_problem is not None:
                return artifacts(
                    "infra_error", code="ISOLATION_PIN_MISMATCH", message=pin_problem[:300]
                )

        def process(claim: ClaimRecord) -> dict[str, Any]:
            record: dict[str, Any] = {
                "claim_id": claim.claim_id,
                "citekey": claim.citekey,
                "staging_dir": str(claim.staging_dir),
                "stages": {},
                "status": "ok",
            }
            # Mechanical profiles have no extractor stage, so nothing would otherwise write the
            # evidence envelope the adjudicator reads (C6.0/C6.2). Produce it here, before the
            # judge is dispatched. Never raises -- a producer failure is this claim's failure, not
            # the batch's exception.
            producer = evidence_producers.for_profile(self.profile)
            if producer is not None:
                try:
                    producer(
                        claim.staging_dir,
                        claim.claim_id,
                        run_id=inputs.batch_id,
                        profile=self.profile,
                    )
                except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                    record["status"] = "program_error"
                    record["detail"] = f"evidence producer failed: {str(exc)[:200]}"
                    return record

            for stage in self.profile.stages:
                try:
                    cmd = self._dispatch_command(
                        stage,
                        claim,
                        scope=grants[staging_root(claim)],
                        materialized_path=materialized_path,
                        run_id=inputs.batch_id,
                        render_prefix=render_prefix,
                    )
                except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                    # The dispatch was never sent, so nothing was spent and no verdict exists.
                    # `program_error` rather than `invalid_output` for the same reason the evidence
                    # producer's failure above takes it: the program did not run and emit something
                    # the contract rejects, the pipeline failed to put it in front of the model.
                    record["status"] = "program_error"
                    record["detail"] = f"dispatch not built: {str(exc)[:300]}"
                    return record
                res = self.invoke(cmd, self.working_checkout, self.per_call_timeout_seconds)
                # Keep the adjudicator's own reasoning trace (1d). ⚠ **These are the bytes already
                # in hand, not a copy out of `~/.claude/projects/`** -- a `--rm` container discards
                # its own copy of that directory, and the old lookup was guarded at every step, so
                # containerizing would have made every `trace_ref` null while the run still
                # reported `status: ok`. Persisting the captured stream is also strictly better
                # than what the uncontained path did, which was to cite evidence for a published
                # result out of a cache Claude Code owns and prunes. Write failures stay non-fatal
                # -- a missing trace is worth less than a claim, and must never cost one.
                trace_ref = None
                if res.stream:
                    dest = out_dir / isolation_mod.TRACE_DEST_SHAPE.format(
                        claim_id=claim.claim_id, stage=stage
                    )
                    try:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(res.stream, encoding="utf-8")
                        trace_ref = str(dest)
                    except OSError:
                        trace_ref = None
                record["stages"][stage] = {
                    "exit_code": res.exit_code,
                    "cost_usd": res.cost_usd,
                    "duration_seconds": res.duration_seconds,
                    "timed_out": res.timed_out,
                    # The instrument, and the record of what it thought. `model` is the resolved
                    # id; `trace_ref` is an OPTIONAL read -- nothing pushes the trace into the
                    # optimizer's context, it just becomes openable when the agent wants to know
                    # why the judge said what it said.
                    "model": res.model,
                    "session_id": res.session_id,
                    "trace_ref": trace_ref,
                }
                if res.timed_out:
                    record["status"] = "timeout"
                    return record
                if res.exit_code != 0:
                    record["status"] = "program_error"
                    record["detail"] = res.detail
                    return record

            # Exit validation (Part C5). The Runner calls the validator; the validator owns the rule.
            verdict_path = claim.staging_dir / "ledger" / "claims" / f"{claim.claim_id}.json"
            validation = validate_sarol.validate_file(
                verdict_path,
                expect_claim_id=claim.claim_id,
                rubric_path=rubric_path,
                rollup_order=rollup_order,
                # How the evidence was ACTUALLY acquired. The profile knows; the judge only
                # echoes, and a dropped echo used to fail the claim (2026-09-07).
                harness_selector=self.profile.selector,
            )
            record["validation"] = validation.as_dict()
            if not validation.ok:
                # `invalid_output`, NOT `program_error`. The distinction is the whole point: the
                # program ran and emitted something the contract rejects, which is a RESULT -- the
                # rubric's own words are "scored as a miss and counted in error_class_counts, never
                # a crash". `program_error` means the RUNNER broke, and `run()` escalates it to a
                # run-level status the Scorer refuses to score at all.
                #
                # Conflating them cost a whole batch on 2026-09-07: 93 of 100 claims were fine and
                # every number came back 0.0. And because the Scorer also demands 100% coverage,
                # merely *skipping* the invalid ones zeroes it too -- so at any non-zero judge
                # failure rate (~2% irreducible: malformed JSON, a missing field) the instrument
                # could never produce a number. P(>=1 failure in 50) is ~64% at 2%.
                record["status"] = "invalid_output"
            return record

        # The container boundary, stood up ONCE for the whole batch and torn down on every exit
        # path including the early returns below. Once, not per claim, because the shipping
        # boundary owns a Docker network and a Squid sidecar: at 561 dispatches a sidecar each is
        # not a boundary anyone keeps, which is exactly how this code ended up running on the
        # unrestricted policy as a stand-in before. What IS per dispatch is the rendered prefix --
        # `render_prefix(scope)` below, called with that dispatch's own grant.
        #
        # There is no branch here that skips it. `container` is refused at construction when it is
        # absent, and the selftests inject a fake *renderer* rather than switching the boundary
        # off, so nothing that produces or guards a number can be measured on a different
        # instrument than the baseline it is compared against.
        with self.container.open_boundary(grants[next(iter(grants))]) as render_prefix:
            # The round-trip canary, BEFORE any scored claim (D46). A run whose instrument moved is
            # not a run that scored worse -- it is not a run at all.
            canary_record = None
            if self.canary is not None:
                canary_record = process(self.canary.claim)
                observed = (canary_record.get("validation") or {}).get("overall_verdict")
                if canary_record["status"] != "ok" or observed != self.canary.expected_verdict:
                    return artifacts(
                        "infra_error",
                        code="CANARY_FAILED",
                        message=(
                            f"canary {self.canary.claim.claim_id} expected "
                            f"{self.canary.expected_verdict!r}, observed {observed!r} "
                            f"(status={canary_record['status']}) -- the scorer or pipeline moved; "
                            "numbers from this run are not comparable to earlier ones"
                        ),
                        n=batch_totals([canary_record])[0],
                        cost=batch_totals([canary_record])[1],
                    )

            manifest_path = out_dir / "run_manifest.json"

            # Once per batch, before the first manifest write. The shipping boundary answers this
            # by starting one short container; the selftests' stand-in answers from a literal. A
            # failure here is recorded, never silently dropped: a manifest that cannot name its
            # instrument is worth less than one that says why it cannot.
            try:
                container_described = self.container.describe()
            except Exception as exc:  # noqa: BLE001 -- an unnameable instrument must not cost a run
                container_described = {
                    "error": f"could not describe the container: {str(exc)[:200]}"
                }

            def write_manifest(records: "list[dict[str, Any]]", *, complete: bool) -> None:
                """Write the run manifest. Called after EVERY claim, not only at the end.

                The Runner wrote per-claim verdicts incrementally but its manifest only after the whole
                batch, so a killed run left finished claims on disk with nothing pointing at them. The
                v0 baseline survived its interruption at 37/50 only because a manifest was rebuilt by
                hand over the claims that happened to finish -- ad-hoc recovery standing in for a
                missing feature, on the single most expensive artifact of the run.

                A partial manifest is safe to leave lying around: `requested_count` still names the
                full batch, so `SarolScorer`'s coverage check reports `scored: False` with a coverage
                reason rather than letting a half-finished batch reach the frontier as a real number.
                `complete` says the same thing directly, for whoever is reading the file by hand.
                """
                # Roll the validator's own invalid-label counts up to the batch. The Scorer merges
                # these rather than re-deriving them, because `parse_verdict` only ever sees the
                # OVERALL label: an invalid SUB-CLAIM verdict under a valid overall verdict would
                # otherwise score clean and disappear from error_class_counts entirely.
                _subs, _cost = batch_totals(
                    ([canary_record] if canary_record is not None else []) + list(records)
                )
                validator_counts: dict[str, int] = {}
                for rec in records:
                    for key, n in (
                        (rec.get("validation") or {}).get("error_class_counts") or {}
                    ).items():
                        validator_counts[key] = validator_counts.get(key, 0) + n
                payload = json.dumps(
                        {
                            "batch_id": inputs.batch_id,
                            "split": inputs.split,
                            # C6.5: macro-F1 under two profiles measures two different systems, and
                            # the engine's frontier is a bare scalar that cannot tell them apart.
                            # Stamping the profile here is the consumer-side half of keeping them
                            # distinguishable.
                            "profile": self.profile.name,
                            # Run identity, same rule as `retrieval_k`: a macro-F1 without the
                            # instrument that produced it is not a result. Resolved id, taken from
                            # what the sessions reported rather than from the requested alias, and
                            # None only if no stage ever reported one.
                            "model": next(
                                (
                                    st.get("model")
                                    for rec in records
                                    for st in (rec.get("stages") or {}).values()
                                    if st.get("model")
                                ),
                                None,
                            ),
                            "profile_stages": list(self.profile.stages),
                            "retrieval_k": self.profile.retrieval_k,
                            # The instrument the program ran ON, by the same rule as `model` and
                            # `retrieval_k`: containerizing SWAPS the instrument, so a number is
                            # only comparable to an earlier one if the image and the Claude Code
                            # inside it are recorded beside it. Probed from the boundary itself
                            # rather than stated, and computed once per batch -- a selftest's
                            # stand-in says so in the record instead of leaving it blank.
                            "container": container_described,
                            # The Scorer's coverage assertion compares against what was actually ASKED
                            # of the Runner, not against however many records came back.
                            "requested_count": len(claims),
                            # False until the last claim lands. A reader finding this file after a
                            # kill knows immediately whether it describes a finished batch.
                            "complete": complete,
                            "claims": records,
                            "validator_error_class_counts": validator_counts,
                            "canary": canary_record,
                            # Derived from the records rather than read off a mutable counter.
                            # The canary is included because the counter it replaces was incremented
                            # by the canary's own dispatch too -- dropping it here would have silently
                            # under-reported every run's cost by one claim.
                            "sub_invocation_count": _subs,
                            "cost_usd": _cost,
                        },
                        indent=2,
                )
                # Atomic: serialize to a sibling temp file, then rename over the target. A plain
                # `write_text` truncates first, so a kill mid-write leaves a TORN manifest -- and this
                # file is rewritten after every claim precisely so a killed run stays salvageable.
                # Unreadable JSON at the moment of the kill would defeat the whole point of writing it
                # early. `os.replace` is atomic within a directory on POSIX, so a reader sees either
                # the previous complete manifest or the new one, never a half of either.
                #
                # Cost noted and accepted: this reserializes the whole manifest per claim, which is
                # O(n^2) in batch size. At the real rungs (10-200 claims) that is microseconds against
                # a claim that costs a full LLM session -- ~$1 and ~100s measured. Salvageability is
                # worth more than the arithmetic; revisit only if a rung ever approaches the full 2,141.
                tmp_path = manifest_path.with_name(manifest_path.name + ".tmp")
                tmp_path.write_text(payload, encoding="utf-8")
                os.replace(tmp_path, manifest_path)

            # Dispatch. Claims are independent units of work -- each one is its own nested session,
            # writing its verdict under its OWN `claim.staging_dir` and its trace under its own
            # `<claim_id>-<stage>.jsonl` -- so running several at once changes wall-clock and nothing
            # else. Every session, prompt, subagent and materialized tree is byte-identical to what
            # serial dispatch produced, which is the whole reason this is safe: it does not move the
            # instrument, so baselines measured serially stay comparable.
            #
            # THREADS, not processes: `process` spends ~all of its time blocked in `communicate()`
            # waiting on a `claude` subprocess, so the GIL is released throughout and processes would
            # buy nothing while breaking the closure.
            #
            # Results are collected BY SUBMISSION INDEX, not by arrival and not by `claim_id`:
            #   - by index, so the manifest stays in input order and byte-deterministic regardless of
            #     which claim finishes first (`SarolScorer` keys on `record["claim_id"]` and does not
            #     require order, but a manifest that reshuffles between runs is a diffing hazard);
            #   - by index rather than `claim_id`, so a duplicated id in a batch cannot silently
            #     collapse two records into one.
            #
            # Salvageability is delivered by writing the manifest INSIDE the worker (see
            # `process_and_record`), not by how finished futures are collected here -- which is why
            # this loop is free to consume them in completion order for prompt failure detection.
            indexed: dict[int, dict[str, Any]] = {}
            # Guards BOTH the shared `indexed` dict and the manifest write. Held only for a JSON
            # dump, never across a dispatch, so it does not serialize the actual work.
            ledger_lock = threading.Lock()

            def process_and_record(index: int, claim: ClaimRecord) -> dict[str, Any]:
                """Dispatch one claim, then fold it into the running manifest before releasing the
                worker.

                The manifest write lives HERE, in the worker, rather than in the main thread
                collecting finished futures -- and that placement is load-bearing, not incidental.
                Collecting on the main thread lets a worker pick up its next claim the instant the
                previous one returns, i.e. BEFORE the manifest naming the finished one has been
                written. At `max_workers=1` that silently weakens the incremental-manifest guarantee
                the salvage path depends on, which is precisely what the two `seen_partials` gates
                below caught when this was written the other way round. Writing inside the worker
                restores the exact serial ordering at N=1 (dispatch, write, dispatch, write) and at
                N>1 still lands each claim in the manifest as it finishes.
                """
                record = process(claim)
                with ledger_lock:
                    indexed[index] = record
                    write_manifest([indexed[i] for i in sorted(indexed)], complete=False)
                return record

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = [
                    pool.submit(process_and_record, i, claim) for i, claim in enumerate(claims)
                ]
                try:
                    # `as_completed`, NOT submission order: this has to notice the first failure in
                    # TIME, because every claim still queued behind it is real money. Iterating
                    # `futures` in order would sit on a slow claim 0 while later failures went unseen.
                    for future in concurrent.futures.as_completed(futures):
                        # Re-raises whatever a worker raised, rather than burying it in a future.
                        future.result()
                except BaseException:
                    # Fail fast, as the serial loop did. Cancelling is a no-op for a claim already
                    # running -- a dispatched nested session cannot be unsent -- but it stops every
                    # QUEUED claim from starting. Without this the executor's own shutdown drains the
                    # whole batch first, so an exception on claim 3 of 300 would still pay for the
                    # remaining 297. The old `for claim in claims:` loop stopped at claim 3, and
                    # matching that is the point: propagation alone was not the contract, not
                    # spending the rest of the batch was.
                    for pending in futures:
                        pending.cancel()
                    raise

        results: list[dict[str, Any]] = [indexed[i] for i in sorted(indexed)]
        write_manifest(results, complete=True)

        timed_out = any(r["status"] == "timeout" for r in results)
        errored = any(r["status"] == "program_error" for r in results)
        sub_invocations, total_cost = batch_totals(
            ([canary_record] if canary_record is not None else []) + results
        )
        ref = schemas.ArtifactRef(
            path=str(manifest_path),
            sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        )

        status = "timeout" if timed_out else ("program_error" if errored else "ok")
        return artifacts(status, refs=(ref,), n=sub_invocations, cost=total_cost)


# =================================================================================================
# Scorer
# =================================================================================================


class SarolScorer:
    """Turns a run's artifacts into the frontier scalar, with the two guards the engine lacks.

    ``gold_resolver`` is the seam over ``parse_verdict.parse`` — the single piece of code allowed to
    touch gold. Injecting it keeps this class testable without a gold tree present, and keeps the
    sealed-split boundary exactly where ``parse_verdict.py`` puts it.
    """

    def __init__(
        self,
        *,
        gold_resolver: Callable[[pathlib.Path], dict[str, Any]] | None = None,
        mistakes_root: pathlib.Path | None = None,
    ) -> None:
        self._gold_resolver = gold_resolver
        # Where the per-claim TRAIN mistake corpus is written (C6.8). None disables it, which is
        # what every VAL call does implicitly -- see `_write_mistakes`.
        self.mistakes_root = pathlib.Path(mistakes_root) if mistakes_root else None

    def _resolve_gold_only(self, staging_dir: pathlib.Path) -> str | None:
        """Gold for a claim whose VERDICT is unreadable. Returns the label, or None.

        Gold is keyed off `staging_info.json`'s citekey and never touches the verdict, so a claim
        the judge mangled is still a claim we know the right answer to -- and therefore still
        scoreable, as a miss. Goes through `_gold_resolver` first so the injection seam that keeps
        this class testable without a gold tree is preserved.
        """
        if self._gold_resolver is not None:
            try:
                return self._gold_resolver(staging_dir)["gold_label"]
            except (OSError, KeyError, RuntimeError, TypeError):
                return None
        import parse_verdict  # noqa: PLC0415 -- imported late; it reads gold

        try:
            info = json.loads((staging_dir / "staging_info.json").read_text(encoding="utf-8"))
            gold = json.loads(parse_verdict.find_gold_file(info["citekey"]).read_text())
            return parse_verdict.gold_paper_label(gold["gold_evidence"])
        except (OSError, KeyError, RuntimeError, json.JSONDecodeError):
            return None

    def _resolve(self, staging_dir: pathlib.Path) -> dict[str, Any]:
        if self._gold_resolver is not None:
            return self._gold_resolver(staging_dir)
        import parse_verdict  # noqa: PLC0415 -- imported late; it reads gold

        return parse_verdict.parse(staging_dir)

    def _write_mistakes(self, split, batch_id, joined) -> str | None:
        """Persist the per-claim TRAIN mistake corpus (C6.8). Returns its path, or None.

        **This is a repair, not an addition.** The landed corpus was `counts` plus a pointer at the
        *run manifest*, so the optimizer could see that it scored 0.29 and which error classes
        fired, but never which claims failed, what it answered, or what gold said. On a Tier-1-open
        split that is close to scalar-only optimization -- the optimizer was being asked to fix
        mistakes it could not read.

        **TRAIN only, and that is a boundary, not a default.** This file contains gold labels. TRAIN
        gold is fully open to the optimizer (that is the mechanism by which it learns, not a leak);
        VAL gold is not, so nothing is written on a VAL call however the Scorer is configured.

        **A claim is correct here only if its 9-class label matches** -- not its 3-way bucket. The
        3-way comparison this used to make is the same collapse that makes `micro_f1` a weaker
        number than it looks: it treats the five NOT_ACCURATE classes as interchangeable, which is
        exactly the discrimination the rubric exists to make. `pred_3way` and `gold_3way` are still
        written on every row, so a reader can see the collapse; they just no longer decide it.

        Two things deliberately withheld even on TRAIN. ``parse_verdict.parse`` also returns
        ``split``, ``claim_row_id`` and ``cited_paper_bucket`` -- raw benchmark provenance that the
        opaque-citekey staging design exists to keep out of the run. The optimizer needs the gold
        *label* to learn; it has no use for the row it came from. And correct claims are summarised
        by count rather than listed: the file is the mistake corpus, and if positive examples turn
        out to be wanted that should be a deliberate change, not a silent one.
        """
        if split != "train" or self.mistakes_root is None:
            return None
        rows = []
        n_correct = 0
        for record, resolved in joined:
            # S25: 9-WAY, not 3-way. This compared `pred_3way` to `gold_3way` until 2026-09-07,
            # which silently forgave every within-bucket confusion -- CONTRADICT answered for
            # OVERSIMPLIFY collapses to NOT_ACCURATE on both sides and was banked as CORRECT. Five
            # of the nine labels live inside NOT_ACCURATE, so the whole of the rubric's hardest
            # discrimination was invisible in the corpus AND added to the `n_correct` the agent is
            # told to read first. Under an accuracy objective those are plainly errors, and the
            # optimizer cannot fix what it is never shown.
            if resolved.get("pred_label") == resolved.get("gold_label"):
                n_correct += 1
                continue
            rows.append({
                "claim_id": record.get("claim_id"),
                "citekey": resolved.get("citekey"),
                **self._verdict_detail(record),
                "pred_label": resolved.get("pred_label"),
                "gold_label": resolved.get("gold_label"),
                "pred_3way": resolved.get("pred_3way"),
                "gold_3way": resolved.get("gold_3way"),
                # S13. The trace path, ON THE ROW. It was reachable only from the run manifest,
                # which a blame subagent is never handed -- so the brief's "open the trace if the
                # fields cannot explain the verdict" step sent it hunting through the tree, which
                # the same brief forbids. Copying the one string across turns an impossible
                # instruction into a one-line file read. None when the trace could not be copied.
                "trace_ref": ((record.get("stages") or {}).get("adjudicator") or {}).get(
                    "trace_ref"
                ),
            })
        out = self.mistakes_root / "mistakes" / f"{batch_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "split": split,
                    "n_scored": len(joined),
                    "n_correct": n_correct,
                    "n_mistakes": len(rows),
                    "claims": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return str(out)

    @staticmethod
    def _verdict_detail(record) -> dict[str, Any]:
        """Claim text, the evidence the judge saw, and why it said what it said.

        Read from the adjudicated ledger file rather than re-derived, so what the optimizer reads
        is exactly what the judge wrote. A missing or malformed file degrades to empty fields --
        the mistake is still worth recording without its reasoning.

        **`sub_claims` carries the judge's working, not just its conclusion.** The flat
        `evidence_snippets` list below is the UNION of every sub-claim's evidence, and
        `adjudicator_reasoning.sub_claim_verdicts` is a bare list of labels with no text attached
        -- so a reader could see that a claim was judged wrong and which snippets were in play,
        but not WHICH evidence drove the sub-verdict that went wrong. That is the question an
        optimizer has to answer to fix a rubric: not "was this claim wrong" but "what did the
        judge read, and what did it conclude from it". The `retrieval` rung makes this sharper --
        the judge sees a BM25 top-k subset and is not told so, so a sub-claim marked unsupported
        may simply have had its evidence retrieved away. Only the per-sub-claim mapping
        distinguishes a rubric defect from a retrieval defect.

        `locator` (`pdfs/<citekey>/content.txt#L22`, relative to the claim's staging dir) rides
        along with each snippet so scattered-versus-clustered evidence is visible without opening
        the source. `claim_type` and `rubric_variant` are the judge's own read of the claim and
        the rubric version that produced the verdict -- both plausible upstream causes of a wrong
        label, and both previously invisible.

        The flat fields are KEPT rather than replaced: `context/release-format.md` describes them,
        and this is a widening, not a migration. TRAIN-only either way (the caller returns early
        for any other split), so no gold-label surface changes -- the cited papers are public
        biomedical literature and Tier 1 is fully open by design.
        """
        blank = {
            "claim_text": None,
            "claim_type": None,
            "rubric_variant": None,
            "evidence_snippets": [],
            "adjudicator_reasoning": {},
            "sub_claims": [],
        }
        claim_id = record.get("claim_id")
        try:
            verdict = json.loads(
                (pathlib.Path(record["staging_dir"]) / "ledger" / "claims" / f"{claim_id}.json")
                .read_text(encoding="utf-8")
            )
        except (OSError, KeyError, json.JSONDecodeError):
            return blank
        subs = verdict.get("sub_claims") or []
        return {
            "claim_text": verdict.get("claim_text"),
            "evidence_snippets": [
                ev.get("snippet")
                for sub in subs
                for ev in (sub.get("evidence") or [])
                if ev.get("snippet")
            ],
            "adjudicator_reasoning": {
                "sub_claim_verdicts": [s.get("verdict") for s in subs],
                "nuance": [s.get("nuance") for s in subs if s.get("nuance")],
                "overall_flag": verdict.get("overall_flag"),
                "remediation": verdict.get("remediation"),
            },
            "claim_type": verdict.get("claim_type"),
            "rubric_variant": verdict.get("rubric_variant"),
            "sub_claims": [
                {
                    "sub_claim_id": sub.get("sub_claim_id"),
                    "text": sub.get("text"),
                    "verdict": sub.get("verdict"),
                    "nuance": sub.get("nuance"),
                    "evidence": [
                        {
                            "snippet": ev.get("snippet"),
                            "locator": ev.get("locator"),
                            "section": ev.get("section"),
                            "line": ev.get("line"),
                        }
                        for ev in (sub.get("evidence") or [])
                    ],
                }
                for sub in subs
            ],
        }

    def score(self, artifacts, split, task_config):  # positional -- loop.py:336/:337
        """The ``Scorer`` protocol. ``(artifacts, split, task_config) -> ScoreResult``."""
        schemas = _import_engine()
        import score_sarol3  # noqa: PLC0415

        # `_split` is stashed here because the engine never injects it (loop.py:320-321 says it
        # does; loop.py:336-337 shows only `_iter` is). Without this the ReleaseBuilder returns a
        # train-phase payload for the VAL call and the loop stops at loop.py:373-377.
        config = {**task_config, "_split": split}

        def result(metric_value: float, breakdown: dict[str, Any]):
            metric = schemas.PrimaryMetric(
                name=PRIMARY_METRIC_NAME, value=metric_value, higher_is_better=True
            )
            return schemas.ScoreResult(
                primary_metric=metric, breakdown=breakdown, task_config=config
            )

        if artifacts.status != "ok" or not artifacts.artifact_refs:
            # A failed batch is not a zero -- it is not a result. Reporting 0.0 would let a
            # degraded run masquerade as a bad-but-real score and pollute the frontier.
            return result(
                0.0,
                {
                    "scored": False,
                    "reason": f"run status={artifacts.status!r}",
                    "n_total": 0,
                    "n_invalid": 0,
                },
            )

        run_manifest = json.loads(
            pathlib.Path(artifacts.artifact_refs[0].path).read_text(encoding="utf-8")
        )
        requested = int(run_manifest.get("requested_count", 0))

        pairs: list[tuple[str, str]] = []
        unresolved = 0
        joined: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for record in run_manifest["claims"]:
            # `invalid_output` is SCORED, not skipped. The program emitted something the contract
            # rejects, which is a result about the program -- and skipping it is not neutral here,
            # because the coverage rule below demands n_total == requested, so a skip zeroes the
            # whole batch exactly as the old `program_error` escalation did. Only a genuine
            # infrastructure status (timeout, program_error) is still dropped.
            if record.get("status") not in ("ok", "invalid_output"):
                continue
            try:
                resolved = self._resolve(pathlib.Path(record["staging_dir"]))
            except (OSError, KeyError, RuntimeError, json.JSONDecodeError):
                # Unparseable verdict. Gold does NOT depend on the verdict -- it resolves from
                # `staging_info.json`'s citekey -- so this claim is still scoreable, as a miss
                # against a sentinel that is not in the 9-class enum and so can never match.
                gold_only = self._resolve_gold_only(pathlib.Path(record["staging_dir"]))
                if gold_only is None:
                    unresolved += 1
                    continue
                pairs.append((INVALID_OUTPUT_LABEL, gold_only))
                continue
            pairs.append((resolved["pred_label"], resolved["gold_label"]))
            # Kept, not discarded. Discarding it is what left the optimizer with counts only.
            joined.append((record, resolved))

        scored = score_sarol3.score(pairs)

        # Merge the validator's per-file invalid-label counts on top of the scorer's own. The
        # scorer only ever sees the OVERALL predicted label (that is what `parse_verdict` returns),
        # so an invalid label on a SUB-CLAIM under a valid overall verdict is invisible to it. The
        # prediction is still scored on the overall label -- that part is a real answer -- but the
        # defective sub-claim has to reach `error_class_counts`, or an optimizer edit that corrupts
        # sub-claim vocabulary looks clean right up until someone reads the ledger by hand.
        merged_counts = dict(scored.get("error_class_counts") or {})
        for key, n in (run_manifest.get("validator_error_class_counts") or {}).items():
            merged_counts[key] = merged_counts.get(key, 0) + n

        # Coverage: guard partial or missing output, not just degenerate values. A partially-scored
        # batch presented as complete is not a result.
        complete = scored["n_total"] == requested and unresolved == 0
        breakdown = {
            **scored,
            "error_class_counts": merged_counts,
            "scored": complete,
            "requested_count": requested,
            "n_unresolved": unresolved,
            "split": split,
            # C6.5 -- recovered from the run manifest rather than passed in, so it always
            # describes the run that actually happened.
            "profile": run_manifest.get("profile"),
            "retrieval_k": run_manifest.get("retrieval_k"),
            "model": run_manifest.get("model"),
        }
        if not complete:
            breakdown["reason"] = (
                f"coverage: scored {scored['n_total']} of {requested} requested"
                f"{f', {unresolved} unresolved' if unresolved else ''}"
            )
            return result(0.0, breakdown)

        mistakes_ref = self._write_mistakes(split, run_manifest.get("batch_id", "batch"), joined)
        if mistakes_ref:
            breakdown["mistakes_ref"] = mistakes_ref

        value = scored["primary_metric"]
        # NaN passes PrimaryMetric's isinstance-only validation (schemas.py:80-81), and a NaN on the
        # frontier makes _select_best order-dependent and _regressed always False -- so step-back
        # would silently never fire. Catch it here, where it is still legible.
        if not math.isfinite(value):
            breakdown["scored"] = False
            breakdown["reason"] = f"non-finite primary_metric: {value!r}"
            return result(0.0, breakdown)

        return result(value, breakdown)


# =================================================================================================
# ReleaseBuilder + mistake corpus
# =================================================================================================


#: What a VAL release is allowed to carry. TRAIN is Tier 1 (fully open); VAL is Tier 2 and the
#: framework's rule for it is *scalar only* (`sarol`'s D24). Per-class F1 and the confusion matrix
#: are aggregates, but they are aggregates **of the held-out set** — they describe where the
#: program fails on VAL, which is precisely the signal an optimizer would overfit to and precisely
#: what makes train-vs-val divergence usable as a stopping rule. So the scalar crosses the boundary
#: and the error structure does not. What remains is completeness metadata: enough to tell a real
#: score from a partial batch, carrying no information about *which* claims were missed.
#:
#: `n_invalid` is included deliberately, and it is the one judgement call in this list. It is a
#: bare count of unparseable predictions, not a distribution over classes -- it says "this many
#: outputs were malformed", never which gold classes they fell against. The plan's Verification
#: table asks for it alongside the coverage assertion, and withholding it would mean a VAL run
#: could be half-garbage while still reporting `scored: true`.
#: `profile` is on this list and is not a judgement call: it says nothing about *which* held-out
#: claims were missed or how, only which system produced the number. Withholding it would leave a
#: VAL scalar that cannot be told apart from a scalar produced by a different experiment (C6.5).
#: What survives the Tier 2 reduction. The rule is *run condition and completeness, never per-class
#: structure* -- so `profile` and `retrieval_k` belong and `per_class_f1` / `confusion_matrix` /
#: `error_class_counts` / `support_9way` / `mistakes_ref` never can.
#:
#: `retrieval_k` was missing, which broke the plan's own C6.3: "A macro-F1 without the *k* is not a
#: result" (`papertrail-optimizer-requirements.md:247`), and every reported Phase 1 number must
#: carry its profile and, under `retrieval`, its k (`:423`). The VAL scalar IS a reported Phase 1
#: number -- it is the frontier -- so it was being reported without its evidence condition. `k` is
#: a scalar property of how the run was configured, identical for every claim, so it discloses
#: nothing about the held-out set: this widens the identity metadata, not the leakage surface.
_VAL_BREAKDOWN_ALLOWED = (
    "scored", "reason", "n_total", "n_invalid", "requested_count", "split", "profile",
    "retrieval_k", "model",
    # The objective renormalises over the objective classes PRESENT in the batch, so the
    # denominator is part of the number and VAL is uninterpretable without it.
    #
    # The COUNT is allowed; the presence LIST is not. `objective_classes_present` is a thresholded
    # `support_9way` (support > 0), and `support_9way` is on the deny-list two lines down for
    # exactly the reason that matters here -- it is VAL's gold structure. The count says "this
    # number was renormalised over 5 classes, so do not compare it to a 6-class one"; the list
    # would additionally say WHICH class VAL happens to lack, which is gold distribution and buys
    # the optimizer nothing it should have. `objective_class_set` is the fixed configured set,
    # identical every run and independent of the draw, so it leaks nothing at all.
    "n_objective_classes_present", "objective_class_set",
)


class SarolReleaseBuilder:
    """Builds the per-iteration release. Aggregates only, and for VAL, not even all of those."""

    def __init__(self, *, policy: str) -> None:
        """Stamps every payload with the configuration pin committed for ``policy``.

        🚩 **This used to default to the literal `'sarol-2024'`, which is how the last run wrote the
        same inert string onto all ten payloads.** A release that names its isolation configuration
        with a constant names nothing. The value now comes from the manifest's committed
        `runtime_pins`, for the boundary kind the run actually used.

        ⚠ **It is NOT what the pin gate compares against, and that separation is the whole point.**
        The gate (`SarolRunner.isolation_pin_error`) compares the **computed** configuration against
        this same committed value, so by the time anything is stamped the two are known to agree.
        Comparing the stamp to the computed hash instead would compare a value to itself -- the
        tautology the plan calls out, which is the original inertness moved one layer up.
        """
        pin = isolation_mod.committed_configuration_pin(policy)
        if not pin:
            raise ValueError(
                f"refusing to build releases with no committed isolation pin for {policy!r}: "
                f"nothing at runtime_pins.{isolation_mod.PIN_KEY}.{policy} in "
                f"HEAD:{isolation_mod.MANIFEST_REL}. Run `python3 optimizer/isolation.py "
                "--print-pin` and commit the block"
            )
        self.policy = policy
        self.optimizer_isolation_hash = pin

    def _reduce_for_val(self, score):
        """Strip a VAL ``ScoreResult`` down to the scalar plus completeness metadata."""
        schemas = _import_engine()
        reduced = {k: score.breakdown[k] for k in _VAL_BREAKDOWN_ALLOWED if k in score.breakdown}
        return schemas.ScoreResult(
            primary_metric=score.primary_metric,
            breakdown=reduced,
            task_config=score.task_config,
        )

    def build_release(self, score, corpus, *, frontier=None, budget=None):
        """The ``ReleaseBuilder`` protocol. First two positional, ``frontier``/``budget`` keyword —
        `run_loop` always passes the latter two as keywords, so a strict two-arg signature raises
        ``TypeError``."""
        schemas = _import_engine()
        split = score.task_config.get("_split", "train")
        iter_n = score.task_config.get("_iter", 0)
        now = datetime.now(timezone.utc).isoformat()

        if split == "val":
            return schemas.ReleasePayloadVal(
                schema_version=SCHEMA_VERSION,
                phase="val",
                metrics=self._reduce_for_val(score),
                iter=iter_n,
                produced_at_utc=now,
                optimizer_isolation_hash=self.optimizer_isolation_hash,
            )
        return schemas.ReleasePayloadTrain(
            schema_version=SCHEMA_VERSION,
            phase="train",
            corpus={
                "ref": corpus.ref,
                "counts": corpus.counts,
                "profile": score.breakdown.get("profile"),
                "retrieval_k": score.breakdown.get("retrieval_k"),
                "metrics": {
                    "primary_metric": score.primary_metric.value,
                    "primary_metric_name": score.primary_metric.name,
                    "breakdown": score.breakdown,
                },
                "frontier": frontier or {},
                "budget": budget or {},
            },
            iter=iter_n,
            produced_at_utc=now,
            optimizer_isolation_hash=self.optimizer_isolation_hash,
        )


def build_mistake_corpus(artifacts, score):
    """Per-claim adjudicator reasoning + evidence + bounce history, as an adapter-owned blob.

    TRAIN-side mistakes are fully open to the optimizer (Tier 1, `sarol`'s D24). The corpus stays
    opaque to the engine — ``ref`` + ``counts`` only — because the reason for sealing here is
    leakage of gold labels, not privacy: the cited papers are public biomedical literature.
    """
    schemas = _import_engine()
    counts = dict(score.breakdown.get("error_class_counts") or {})
    # C6.8: point at the per-claim corpus the Scorer wrote, NOT at the batch run manifest. The
    # manifest carries dispatch bookkeeping -- exit codes, costs, timings -- and no gold and no
    # reasoning, so an optimizer following that ref learned nothing about why it was wrong.
    # `MistakeCorpus` exposes only `ref` and `counts`, so the richer content rides behind `ref`
    # and no engine schema changes.
    ref = score.breakdown.get("mistakes_ref")
    if not ref:
        # VAL, or a Scorer with no mistakes_root. Falling back to the manifest keeps `ref`
        # non-empty for the engine; it is deliberately the poorer artifact.
        ref = artifacts.artifact_refs[0].path if artifacts.artifact_refs else ""
    return schemas.MistakeCorpus(ref=ref, counts=counts)


# =================================================================================================
# Agent wrapper — where the contract re-hash actually bites
# =================================================================================================


@dataclass
class GuardedOutcome:
    exit_code: int
    detail: str
    token_usage: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    attempting_step_back: bool = False


class ContractGuardedAgent:
    """Wraps the real optimizer agent and re-hashes the contract files after its edit pass.

    Placement is the point. ``run_loop`` raises ``LoopStop`` on a nonzero agent exit *before*
    ``commit_version`` (`loop.py:405-407`), so returning nonzero here fails the iteration before
    anything is scored or frozen. A check anywhere later would be inspecting a version that had
    already been tagged.
    """

    def __init__(
        self,
        inner,
        program_store: SarolProgramStore,
        *,
        tree_root: pathlib.Path | None = None,
    ) -> None:
        self.inner = inner
        self.program_store = program_store
        self.tree_root = tree_root

    def run(self, *, iter_n: int, materialized_path=None):  # keyword-only -- loop.py:398
        outcome = self.inner.run(iter_n=iter_n, materialized_path=materialized_path)
        violations = self.program_store.verify_contract_files(self.tree_root)
        if violations:
            detail = "; ".join(str(v) for v in violations)
            return GuardedOutcome(
                exit_code=91,
                detail=(
                    f"iter {iter_n}: contract file(s) modified -- the frozen enum is not editable. "
                    f"{detail}"
                ),
                token_usage=dict(getattr(outcome, "token_usage", {}) or {}),
                cost_usd=float(getattr(outcome, "cost_usd", 0.0) or 0.0),
                attempting_step_back=False,
            )
        return outcome


# =================================================================================================
# Offline gates
# =================================================================================================


class _StubAgent:
    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code = exit_code

    def run(self, *, iter_n: int, materialized_path=None):
        return GuardedOutcome(exit_code=self.exit_code, detail=f"stub iter {iter_n}")


def _selftest() -> int:
    import tempfile

    store = SarolProgramStore()
    checks: list[tuple[str, bool]] = []

    # ⚠ **A guard clause, because the alternative is a CRASHED suite and a crashed suite reports
    # nothing.** Dozens of gates below run a full `run()` and then index `artifact_refs[0]`. Once
    # the configuration pin became a preflight refusal, any divergence between the stand-in boundary
    # and its committed pin turns every one of those into an IndexError -- the suite dies before it
    # prints a single line, so the one fact you needed ("the pin is stale") is the one thing you
    # cannot see. Found by mutation: changing what the hash covers produced exactly that.
    #
    # Refusing here converts it into a named failure with the fix in it.
    _pin_problem = isolation_mod.configuration_pin_problem(
        isolation_mod.configuration_hash(
            isolation_mod._configurations_by_policy()[isolation_mod.STAND_IN_POLICY]
        ),
        committed=isolation_mod.committed_configuration_pin(isolation_mod.STAND_IN_POLICY),
        policy=isolation_mod.STAND_IN_POLICY,
    )
    if _pin_problem is not None:
        print(
            "  FAIL  the selftests' own boundary no longer matches its committed pin, so every "
            "gate that runs a batch would refuse before dispatching and this suite would crash "
            "rather than report"
        )
        print(f"  detail: {_pin_problem}")
        print(
            "  fix:    read `python3 optimizer/isolation.py --print-config`, and if the change is "
            "intended, commit the block from `--print-pin`"
        )
        return 1

    # -- the per-call timeout must bound a REAL process tree, not just its root -------------------
    # `sh -c 'sleep 60 & sleep 60'` is the shape that matters: a backgrounded grandchild inherits
    # stdout and outlives its parent, so killing only the root can leave the drain waiting on it.
    # This pins the bound the Runner actually relies on -- a hung tree returns in seconds, not in
    # however long the longest descendant happens to live.
    _t0 = time.monotonic()
    _res = headless_claude_invoke(["sh", "-c", "sleep 60 & sleep 60"], pathlib.Path.cwd(), 1.0)
    _elapsed = time.monotonic() - _t0
    checks += [
        ("a hung nested session times out", _res.timed_out and _res.exit_code == 124),
        ("...and the timeout is REAL wall-clock, not a value the pipe drain can outlive",
         _elapsed < 20.0),
        ("...and a grandchild holding stdout cannot keep the call alive",
         _elapsed < 20.0 and _res.timed_out),
    ]

    # -- manifest / edit scope --------------------------------------------------------------
    contracts = store.contract_paths()
    editable = store.editable_paths()
    checks += [
        ("manifest has 10 entries", len(store.entries) == 10),
        ("four of them are contract files", len(contracts) == 4),
        ("the enum contract is one of them",
         "experiments/sarol-2024/specs/verdict_enum_sarol.md" in contracts),
        # Plan A P0: the paper-verbatim definitions are frozen, so the reconciled scheme
        # cannot be reworded without cutting a version. The rubric stays editable.
        ("the paper-verbatim definitions are a contract file",
         "experiments/sarol-2024/specs/verdict_definitions_sarol.md" in contracts),
        ("...and are therefore NOT optimizer-editable",
         "experiments/sarol-2024/specs/verdict_definitions_sarol.md" not in editable),
        ("the rubric GUIDANCE is editable, per OQ8",
         "experiments/sarol-2024/specs/verdict_schema_sarol.md" in editable),
        ("edit scope and contract scope partition the globset",
         len(contracts) + len(editable) == len(store.entries)),
        ("no contract path leaks into the edit scope",
         not (set(contracts) & set(editable))),
        # C6.1 -- the profile narrows the EDIT scope. The invariant with teeth: you may not
        # optimize a stage you do not run.
        ("the default edit scope is unchanged by profiles landing",
         editable == store.editable_paths("agentic")),
        ("retrieval narrows the scope to the judge, its rubric, and the driver",
         set(store.editable_paths("retrieval")) == {
             "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md",
             "experiments/sarol-2024/specs/verdict_schema_sarol.md",
             ".claude/commands/sarol-eval-item.md"}),
        ("...so Phase 1 cannot edit the extractor it never runs",
         "src/prompts/extractor-dispatch-pdf.md" not in store.editable_paths("retrieval")),
        ("no profile's scope reaches a contract file",
         all(not (set(store.editable_paths(name)) & set(contracts))
             for name in profiles_mod.PROFILES)),
        ("edit scope keeps manifest order regardless of how a profile lists paths",
         store.editable_paths("retrieval")
         == [e["path"] for e in store.entries
             if e["path"] in set(store.editable_paths("retrieval"))]),
        ("the profiles themselves validate against this manifest",
         profiles_mod.validate_against_manifest(store.entries) == []),
    ]

    # -- contract re-hash: the gate that makes "immutable" true ------------------------------
    clean = store.verify_contract_files()
    checks.append(("the working tree's contract files match the freeze", not clean))

    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp)
        for entry in store.entries:
            dst = tree / entry["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((store.repo_root / entry["path"]).read_bytes())
        checks.append(("a faithful copy re-hashes clean", not store.verify_contract_files(tree)))

        mutated = tree / "experiments/sarol-2024/specs/verdict_enum_sarol.md"
        mutated.write_text(mutated.read_text(encoding="utf-8") + "\nIRRELEVANT_2\n", encoding="utf-8")
        violations = store.verify_contract_files(tree)
        checks += [
            ("a mutated contract file is caught", len(violations) == 1),
            ("...and named", violations and "verdict_enum_sarol.md" in violations[0].path),
        ]

        guarded = ContractGuardedAgent(_StubAgent(), store, tree_root=tree)
        outcome = guarded.run(iter_n=1)
        checks += [
            ("the guarded agent fails the iteration on a mutated contract", outcome.exit_code != 0),
            ("...before any scoring or freeze (nonzero exit stops loop.py:405 pre-commit)",
             outcome.exit_code == 91),
        ]

        mutated.write_text(
            (store.repo_root / "experiments/sarol-2024/specs/verdict_enum_sarol.md").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        checks.append(
            ("restoring the bytes clears the violation", ContractGuardedAgent(
                _StubAgent(), store, tree_root=tree).run(iter_n=2).exit_code == 0)
        )

    # -- paperclip pin negative control ------------------------------------------------------
    # Probe the manifest's OWN pin for the match cases so a future pin bump (e.g. 0.5.11 -> 0.7.48)
    # doesn't turn these into spurious failures; the mismatch case uses a version the pin can never be.
    _pin = store.runtime_pins["paperclip_cli"]
    pinned_ok = SarolRunner(store, paperclip_version_probe=lambda: _pin, container=isolation_mod.fake_container())
    pinned_bad = SarolRunner(store, paperclip_version_probe=lambda: "paperclip, version 0.0.0", container=isolation_mod.fake_container())
    pinned_absent = SarolRunner(store, paperclip_version_probe=lambda: None, container=isolation_mod.fake_container())
    checks += [
        ("the pinned paperclip version passes preflight", pinned_ok.paperclip_pin_error() is None),
        ("a wrong version is caught", pinned_bad.paperclip_pin_error() is not None),
        ("a missing CLI is caught", pinned_absent.paperclip_pin_error() is not None),
        ("a cosmetic banner change is not a spurious mismatch",
         SarolRunner(store, paperclip_version_probe=lambda: _normalize_version(_pin), container=isolation_mod.fake_container()).paperclip_pin_error() is None),
    ]

    # -- version normalisation ---------------------------------------------------------------
    checks += [
        ("version parse", _normalize_version("paperclip, version 0.5.11") == "0.5.11"),
        ("cost parse reads the CLI's own total",
         _parse_cost('{"type":"result","total_cost_usd":0.42}') == 0.42),
        ("cost parse survives non-JSON noise", _parse_cost("hello\nworld") == 0.0),
    ]

    # -- engine-facing shapes ----------------------------------------------------------------
    engine_ok = (engine_path() / "engine" / "schemas.py").exists()
    if engine_ok:
        schemas = _import_engine()
        manifest = store.manifest()
        checks += [
            ("manifest builds against the engine's ManifestEntry", len(manifest.entries) == 10),
            ("combined_hash is carried through",
             manifest.combined_hash == store.combined_hash),
        ]
        try:
            schemas.ManifestEntry(**store.entries[0])
        except TypeError:
            checks.append(("raw entries still need the adapter's strip step", True))
        else:
            checks.append(("raw entries still need the adapter's strip step", False))

        # Scorer guards, driven without gold or an engine run.
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = pathlib.Path(tmp) / "run_manifest.json"
            manifest_path.write_text(json.dumps({
                "batch_id": "b1", "split": "train", "requested_count": 2,
                "profile": "retrieval", "retrieval_k": 20,
                "claims": [
                    {"claim_id": "C1", "citekey": "k1", "staging_dir": tmp, "status": "ok"},
                    # C2 becomes the mistake row below. It carries the per-stage record the real
                    # Runner writes, so the trace_ref join (S13) is exercised against the actual
                    # manifest shape rather than asserted against an invented one.
                    {"claim_id": "C2", "citekey": "k2", "staging_dir": tmp, "status": "ok",
                     "stages": {"adjudicator": {"exit_code": 0,
                                                "trace_ref": "/runs/traces/C2-adjudicator.jsonl"}}},
                ],
                # An invalid SUB-CLAIM label under a valid overall verdict. parse_verdict only
                # ever reports the overall label, so without the merge this vanishes.
                "validator_error_class_counts": {
                    "invalid_label": 1, "invalid_label:PROBABLY_FINE": 1,
                },
            }), encoding="utf-8")
            ref = schemas.ArtifactRef(
                path=str(manifest_path),
                sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            )
            ok_artifacts = schemas.RunArtifacts(
                batch_id="b1", status="ok", artifact_refs=(ref,), sub_invocation_count=6
            )
            gold = iter([
                {"pred_label": "ACCURATE", "gold_label": "ACCURATE"},
                {"pred_label": "OVERSIMPLIFY", "gold_label": "OVERSIMPLIFY"},
            ])
            scorer = SarolScorer(gold_resolver=lambda _p: next(gold))
            score = scorer.score(ok_artifacts, "val", {"_iter": 1})
            checks += [
                ("the Scorer stashes _split, which the engine never injects",
                 score.task_config.get("_split") == "val"),
                ("a complete batch scores", score.breakdown["scored"] is True),
                ("the metric is finite", math.isfinite(score.primary_metric.value)),
                ("the release names the metric the adapter and the prompt share",
                 score.primary_metric.name == PRIMARY_METRIC_NAME),
                # The scorer sees only the OVERALL label, so a bad sub-claim verdict reaches
                # error_class_counts only because the validator's counts are merged in.
                ("an invalid sub-claim label survives into error_class_counts",
                 score.breakdown["error_class_counts"].get("invalid_label") == 1),
                ("...named", score.breakdown["error_class_counts"].get(
                    "invalid_label:PROBABLY_FINE") == 1),
                ("...even though both scored predictions were valid",
                 score.breakdown["n_invalid"] == 0),
            ]

            # Coverage: one claim short of what was requested.
            short = iter([{"pred_label": "ACCURATE", "gold_label": "ACCURATE"}])
            partial_manifest = pathlib.Path(tmp) / "partial.json"
            partial_manifest.write_text(json.dumps({
                "batch_id": "b1", "split": "train", "requested_count": 2,
                "claims": [{"claim_id": "C1", "citekey": "k1", "staging_dir": tmp, "status": "ok"}],
            }), encoding="utf-8")
            partial_ref = schemas.ArtifactRef(
                path=str(partial_manifest),
                sha256=hashlib.sha256(partial_manifest.read_bytes()).hexdigest(),
            )
            partial = SarolScorer(gold_resolver=lambda _p: next(short)).score(
                schemas.RunArtifacts(batch_id="b1", status="ok", artifact_refs=(partial_ref,)),
                "train",
                {"_iter": 1},
            )
            checks += [
                ("a partial batch does not score as complete", partial.breakdown["scored"] is False),
                ("...and says why", "coverage" in partial.breakdown.get("reason", "")),
            ]

            # -- C6.8: the per-claim mistake corpus ----------------------------------------
            # The landed corpus was counts + a pointer at the run manifest, so the optimizer knew
            # its score and nothing about which claims failed. These pin the repair.
            mroot = pathlib.Path(tmp) / "trainout"
            (pathlib.Path(tmp) / "ledger" / "claims").mkdir(parents=True, exist_ok=True)
            (pathlib.Path(tmp) / "ledger" / "claims" / "C2.json").write_text(json.dumps({
                "claim_id": "C2",
                "claim_text": "the citing sentence",
                "claim_type": {"type": "PARAPHRASED", "confidence": "medium"},
                "rubric_variant": "verdict_schema_sarol@v3",
                # TWO sub-claims with DISJOINT evidence. One would not distinguish a real
                # per-sub-claim mapping from the flat union that shipped before.
                "sub_claims": [
                    {"sub_claim_id": "C2.a", "text": "the first half",
                     "verdict": "ACCURATE",
                     "nuance": "the passage states it directly",
                     "evidence": [{"snippet": "a fourfold acceleration",
                                   "locator": "pdfs/k2/content.txt#L22",
                                   "section": "content", "line": 22}]},
                    {"sub_claim_id": "C2.b", "text": "the second half",
                     "verdict": "NOT_SUBSTANTIATE",
                     "evidence": [{"snippet": "no comparable effect was observed",
                                   "locator": "pdfs/k2/content.txt#L91",
                                   "section": "content", "line": 91}]},
                ],
                "overall_flag": None,
                "remediation": {"category": "REWORD", "suggested_edit": "narrow the scope"},
            }), encoding="utf-8")

            def scored_with(split, root):
                g = iter([
                    {"pred_label": "ACCURATE", "gold_label": "ACCURATE",
                     "pred_3way": "ACCURATE", "gold_3way": "ACCURATE", "citekey": "k1",
                     "split": "train", "claim_row_id": 417, "cited_paper_bucket": 81},
                    {"pred_label": "ACCURATE", "gold_label": "CONTRADICT",
                     "pred_3way": "ACCURATE", "gold_3way": "NOT_ACCURATE", "citekey": "k2",
                     "split": "train", "claim_row_id": 418, "cited_paper_bucket": 82},
                ])
                return SarolScorer(gold_resolver=lambda _p: next(g),
                                   mistakes_root=root).score(ok_artifacts, split, {"_iter": 1})

            train_score = scored_with("train", mroot)
            corpus_file = json.loads(
                pathlib.Path(train_score.breakdown["mistakes_ref"]).read_text(encoding="utf-8")
            )
            row = corpus_file["claims"][0]
            val_score = scored_with("val", mroot)
            built = build_mistake_corpus(ok_artifacts, train_score)
            _subs = row.get("sub_claims") or []
            _failing_sub = _subs[1] if len(_subs) > 1 else {}

            checks += [
                ("a TRAIN score writes a per-claim mistake corpus",
                 pathlib.Path(train_score.breakdown["mistakes_ref"]).exists()),
                ("...at mistakes/<batch_id>.json",
                 train_score.breakdown["mistakes_ref"].endswith("mistakes/b1.json")),
                ("...shaped as the C6.8 wrapper: counts plus the per-claim list",
                 set(corpus_file) == {"batch_id", "split", "n_scored",
                                      "n_correct", "n_mistakes", "claims"}),
                ("...listing only the claims that were wrong, with the denominator beside them",
                 corpus_file["n_mistakes"] == 1 and corpus_file["n_correct"] == 1
                 and corpus_file["n_scored"] == 2),
                ("...and `claims` carrying C6.8's nine fields plus the three that carry the "
                 "judge's working rather than only its conclusion",
                 set(corpus_file["claims"][0]) == {
                     "claim_id", "citekey", "claim_text", "evidence_snippets",
                     "pred_label", "gold_label", "pred_3way", "gold_3way",
                     "adjudicator_reasoning", "claim_type", "rubric_variant",
                     "sub_claims", "trace_ref"}),
                ("...naming which claim failed", row["claim_id"] == "C2"),
                # S13. The brief tells a blame subagent to open the judge's trace when the
                # structured fields cannot explain the verdict. That instruction was unfollowable:
                # the path lived in the run manifest, which the subagent is never handed, and the
                # same brief forbids the tree-searching that finding it would take.
                ("...and the judge's reasoning trace, so the brief's 'open the trace' step is "
                 "actually followable from the corpus alone",
                 row["trace_ref"] == "/runs/traces/C2-adjudicator.jsonl"),
                ("...what it answered and what gold said",
                 row["pred_label"] == "ACCURATE" and row["gold_label"] == "CONTRADICT"),
                ("...at the granularity the frontier is scored on",
                 row["pred_3way"] == "ACCURATE" and row["gold_3way"] == "NOT_ACCURATE"),
                ("...the evidence the judge actually saw, flattened across sub-claims as before",
                 row["evidence_snippets"] == ["a fourfold acceleration",
                                              "no comparable effect was observed"]),

                # The flat list above is the UNION and cannot answer "which evidence drove the
                # sub-verdict that went wrong" -- the question that separates a rubric defect
                # from a retrieval one. These pin the per-sub-claim mapping.
                # Read defensively. A gate that raises KeyError when its property is absent
                # reports a crashed suite instead of a named failure, and the crash masks every
                # later check in the block -- so the negative control that proves the gate works
                # cannot say WHICH property went missing. Verified 2026-09-03: with the mapping
                # reverted these five report five clean failures rather than one traceback.
                ("each sub-claim carries its own text and verdict, so a rollup error can be "
                 "traced to the sub-claim that caused it",
                 [(c.get("sub_claim_id"), c.get("verdict")) for c in _subs]
                 == [("C2.a", "ACCURATE"), ("C2.b", "NOT_SUBSTANTIATE")]),
                ("...with the evidence MAPPED to it rather than pooled -- the failing sub-claim "
                 "shows only what the judge cited for it",
                 [ev.get("snippet") for ev in _failing_sub.get("evidence", [])]
                 == ["no comparable effect was observed"]),
                ("...and located, so scattered-versus-clustered evidence is visible without "
                 "opening the source",
                 next(iter(_failing_sub.get("evidence", [])), {}).get("locator")
                 == "pdfs/k2/content.txt#L91"),
                ("the judge's own read of the claim rides along, being a plausible upstream "
                 "cause of a wrong label",
                 row.get("claim_type") == {"type": "PARAPHRASED", "confidence": "medium"}),
                ("...as does the rubric version that produced the verdict",
                 row.get("rubric_variant") == "verdict_schema_sarol@v3"),
                ("...and why it said what it said",
                 "the passage states it directly" in row["adjudicator_reasoning"]["nuance"]),
                # Blinding hygiene: TRAIN gold is open, raw benchmark provenance is not.
                ("raw benchmark provenance is withheld even on the open split",
                 not ({"claim_row_id", "cited_paper_bucket", "split"} & set(row))),
                # The boundary that matters more than any of the above.
                ("a VAL score writes NO mistake corpus, whatever the Scorer is configured with",
                 "mistakes_ref" not in val_score.breakdown),
                ("...and VAL's reduced breakdown could not carry one anyway",
                 "mistakes_ref" not in _VAL_BREAKDOWN_ALLOWED),
                ("the corpus ref points at the per-claim file, not the run manifest",
                 built.ref == train_score.breakdown["mistakes_ref"]),
                ("...while still carrying the counts the engine reads",
                 built.counts == train_score.breakdown["error_class_counts"]),
            ]

            # -- S25: the corpus filter is 9-WAY ------------------------------------------------
            # The fixture above never exercises the case that matters, because both its claims
            # differ (or agree) at 3-way resolution too. The interesting claim is the one whose
            # LABELS differ while its BUCKETS agree: CONTRADICT answered for OVERSIMPLIFY. Five of
            # the nine labels collapse into NOT_ACCURATE, so this is the whole of the rubric's
            # hardest discrimination, and the old `pred_3way == gold_3way` filter banked every
            # instance of it as CORRECT -- hiding it from the corpus and inflating `n_correct`.
            def _within_bucket(root):
                g = iter([
                    {"pred_label": "CONTRADICT", "gold_label": "OVERSIMPLIFY",
                     "pred_3way": "NOT_ACCURATE", "gold_3way": "NOT_ACCURATE", "citekey": "k1",
                     "split": "train", "claim_row_id": 419, "cited_paper_bucket": 83},
                    {"pred_label": "ACCURATE", "gold_label": "ACCURATE",
                     "pred_3way": "ACCURATE", "gold_3way": "ACCURATE", "citekey": "k2",
                     "split": "train", "claim_row_id": 420, "cited_paper_bucket": 84},
                ])
                return SarolScorer(gold_resolver=lambda _p: next(g),
                                   mistakes_root=root).score(ok_artifacts, "train", {"_iter": 1})

            _wb_score = _within_bucket(pathlib.Path(tmp) / "wbout")
            _wb = json.loads(
                pathlib.Path(_wb_score.breakdown["mistakes_ref"]).read_text(encoding="utf-8")
            )
            _wb_rows = _wb["claims"]
            # Read defensively, for the reason the C6.8 block above records: under a revert this
            # list is EMPTY, and a gate that indexes it raises instead of failing by name -- the
            # crash then masks the negative control that is the point of the block. Verified by
            # reverting the filter: these four report four clean failures, not one traceback.
            _wb_row = _wb_rows[0] if _wb_rows else {}

            checks += [
                ("a within-bucket confusion is a MISTAKE: labels differ, so the claim is wrong "
                 "however its 3-way buckets collapse",
                 _wb["n_mistakes"] == 1 and len(_wb_rows) == 1),
                ("...and it is NOT added to the n_correct the agent is told to read first",
                 _wb["n_correct"] == 1 and _wb["n_scored"] == 2),
                ("...and the row names the confusion the optimizer has to fix",
                 _wb_row.get("pred_label") == "CONTRADICT"
                 and _wb_row.get("gold_label") == "OVERSIMPLIFY"),

                # NEGATIVE CONTROL, and the reason this block exists. The recorded row is one the
                # OLD filter would have dropped: its buckets are equal. Re-deriving the old
                # predicate here rather than describing it means this gate cannot go green on a
                # silent revert to `pred_3way == gold_3way`.
                ("negative control: the OLD 3-way filter would have called this same row correct "
                 "and written no mistake at all",
                 bool(_wb_rows)
                 and _wb_row.get("pred_3way") == _wb_row.get("gold_3way")
                 and not [r for r in _wb_rows if r.get("pred_3way") != r.get("gold_3way")]),
            ]

            failed = scorer.score(
                schemas.RunArtifacts(batch_id="b1", status="timeout", artifact_refs=()),
                "train",
                {"_iter": 1},
            )
            checks.append(
                ("a timed-out run is not scored as a zero-but-real result",
                 failed.breakdown["scored"] is False)
            )

            # ReleaseBuilder discrimination -- the loop LoopStops if these come back crossed.
            rb = SarolReleaseBuilder(policy=isolation_mod.STAND_IN_POLICY)
            corpus = schemas.MistakeCorpus(ref="", counts={})
            val_payload = rb.build_release(score, corpus, frontier={}, budget={})
            # Same scored batch, relabelled as the TRAIN call -- so the only difference between
            # the two payloads below is the tier, not the underlying numbers.
            train_score = schemas.ScoreResult(
                primary_metric=score.primary_metric,
                breakdown=dict(score.breakdown),
                task_config={**score.task_config, "_split": "train"},
            )
            train_payload = rb.build_release(train_score, corpus, frontier={}, budget={})
            train_breakdown = train_payload.corpus["metrics"]["breakdown"]
            val_breakdown = val_payload.metrics.breakdown
            checks += [
                ("a val split builds a ReleasePayloadVal",
                 isinstance(val_payload, schemas.ReleasePayloadVal)),
                ("a train split builds a ReleasePayloadTrain",
                 isinstance(train_payload, schemas.ReleasePayloadTrain)),
                # Tier 2: the scalar crosses the boundary, the held-out error structure does not.
                ("the VAL release still carries the frontier scalar",
                 val_payload.metrics.primary_metric.value == score.primary_metric.value),
                ("the VAL release does NOT leak per-class F1",
                 "per_class_f1" not in val_breakdown),
                ("...nor the confusion matrix", "confusion_matrix" not in val_breakdown),
                ("...nor the error-class counts", "error_class_counts" not in val_breakdown),
                ("...but keeps enough to tell a real score from a partial batch",
                 "scored" in val_breakdown),
                # A bare count of malformed outputs, not a distribution over classes -- without it
                # a VAL run could be half-garbage and still report scored: true.
                ("...including n_invalid, per the coverage verification row",
                 "n_invalid" in val_breakdown),
                # Same numbers in, different tier out -- the boundary is the ReleaseBuilder's,
                # not an artefact of the two payloads having been scored differently.
                ("the SAME batch through the TRAIN tier keeps per-class F1",
                 "per_class_f1" in train_breakdown),
                ("...and the confusion matrix -- Tier 1 is fully open",
                 "confusion_matrix" in train_breakdown),
                # -- C6.5: a profile is part of a run's identity ---------------------------
                # The engine's frontier is a bare scalar: `_select_best` and `_regressed` compare
                # numbers with no idea where they came from. Two profiles measure two different
                # systems, so both tiers have to say which one produced the number.
                ("the TRAIN release records which profile produced it",
                 train_payload.corpus["profile"] == "retrieval"),
                ("...with the retrieval budget alongside it",
                 train_payload.corpus["retrieval_k"] == 20),
                ("the VAL release records it too, or its scalar is unattributable",
                 val_breakdown.get("profile") == "retrieval"),
                ("...and that is identity, not held-out error structure",
                 "profile" in _VAL_BREAKDOWN_ALLOWED),
                ("the schema version was bumped when the profile key landed",
                 SCHEMA_VERSION == "0.2.0" and train_payload.schema_version == "0.2.0"),
            ]

        # Runner: the pin negative control fires before any claim is dispatched.
        dispatched: list[str] = []

        def spy(cmd, cwd, timeout):
            dispatched.append(" ".join(cmd))
            return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

        bad_runner = SarolRunner(
            store, invoke=spy, paperclip_version_probe=lambda: "paperclip, version 0.0.1", container=isolation_mod.fake_container()
        )
        art = bad_runner.run(
            pathlib.Path("/nonexistent"),
            schemas.RunInputs(input_ref="/nonexistent/batch.json", batch_id="b", split="train"),
        )
        checks += [
            ("a mismatched pin returns infra_error", art.status == "infra_error"),
            ("...before any claim is dispatched", not dispatched),
            ("...naming the pin", art.error is not None and "PAPERCLIP" in art.error.code),
        ]

        # The nested command must exist before a run spends anything looking for it. Tested
        # against a checkout that genuinely lacks it -- the repo itself now ships the command, so
        # pointing this at REPO_ROOT would assert nothing.
        ok_pin = lambda: store.runtime_pins["paperclip_cli"]  # noqa: E731
        with tempfile.TemporaryDirectory() as empty_checkout:
            missing_cmd = SarolRunner(
                store,
                working_checkout=pathlib.Path(empty_checkout),
                invoke=spy,
                paperclip_version_probe=ok_pin,
            container=isolation_mod.fake_container(), )
            art_cmd = missing_cmd.run(
                pathlib.Path("/nonexistent"),
                schemas.RunInputs(input_ref="/nonexistent/batch.json", batch_id="b", split="train"),
            )
            checks += [
                ("a missing nested command fails the run up front",
                 art_cmd.status == "infra_error"
                 and art_cmd.error is not None
                 and art_cmd.error.code == "NESTED_COMMAND_MISSING"),
                ("...naming what it looked for",
                 art_cmd.error is not None and "sarol-eval-item" in art_cmd.error.message_redacted),
                ("...without dispatching anything", not dispatched),
            ]

        # And the converse, now that it is built: the repo ships /sarol-eval-item where a nested
        # session can actually resolve it. ⚠ `command_path()` used to accept src/commands/ and
        # experiments/sarol-2024/commands/ as well, so a copy in either would satisfy this
        # preflight and still fail at dispatch; since 2026-09-19 it looks only at the one location
        # the manifest freezes (`COMMAND_REL_TEMPLATE`). This still pins the location, and the
        # negative control for the narrowing is in the V3b block below.
        shipped = SarolRunner(store, paperclip_version_probe=ok_pin, container=isolation_mod.fake_container()).command_path()
        checks += [
            ("the repo ships /sarol-eval-item", shipped is not None),
            ("...in .claude/commands/, the only place a nested session resolves it",
             shipped is not None
             and shipped.parent == REPO_ROOT / ".claude" / "commands"),
        ]

        # ---- V3b / V3d: what gets scored is the version that was handed in --------------------
        # ⚠ **Every check above passes whether command discovery is version-addressed or fixed**,
        # which is why these exist. The missing-command gate hands the Runner an empty working
        # checkout *and* a nonexistent materialized path, so it goes red under both implementations
        # and separates neither. Found by mutation, not by reading: reverting `command_path` to the
        # working checkout left the suite fully green.
        with tempfile.TemporaryDirectory() as _v3_tmp:
            _v3_tmp = pathlib.Path(_v3_tmp)
            _v3_out, _v3_batch = _staged_batch(_v3_tmp)
            _v3_inputs = schemas.RunInputs(
                input_ref=str(_v3_batch), batch_id="v3", split="train"
            )
            _v3_sent: list[str] = []

            def _v3_spy(cmd, cwd, timeout):
                _v3_sent.append(" ".join(cmd))
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            # (a) The version being scored is missing the command file; the working checkout
            # (REPO_ROOT, the default) ships it. A fixed-checkout implementation answers for the
            # repo, finds the file, and dispatches an incomplete freeze.
            _v3_thin = _materialized_program(_v3_tmp, "iter9-thin")
            _v3_thin_art = SarolRunner(
                store,
                invoke=_v3_spy,
                paperclip_version_probe=ok_pin,
                container=isolation_mod.fake_container(),
            ).run(_v3_thin, _v3_inputs)

            # (b) The converse. The version has the file, the working checkout does not. A fixed
            # implementation refuses a freeze that is in fact complete.
            _v3_full = _materialized_program(_v3_tmp, "iter9-full")
            _v3_entry = next(
                e for e in store.entries if e["path"] == ".claude/commands/sarol-eval-item.md"
            )
            _v3_frozen = subprocess.run(
                [
                    "git", "-C", str(REPO_ROOT), "show",
                    f"{store.raw['source_refs'][_v3_entry['source']]['commit']}:{_v3_entry['path']}",
                ],
                capture_output=True,
            )
            _v3_cmd_file = _v3_full / _v3_entry["path"]
            _v3_cmd_file.parent.mkdir(parents=True, exist_ok=True)
            _v3_cmd_file.write_bytes(_v3_frozen.stdout)
            with tempfile.TemporaryDirectory() as _v3_empty:
                _v3_r = SarolRunner(
                    store,
                    working_checkout=pathlib.Path(_v3_empty),
                    invoke=_v3_spy,
                    paperclip_version_probe=ok_pin,
                    container=isolation_mod.fake_container(),
                )
                _v3_version_ok = _v3_r.missing_command_error(_v3_full) is None
                _v3_checkout_bad = _v3_r.missing_command_error() is not None
                # V3b's "command_path() resolves inside it". Asserted on the RESOLVED path, not
                # just on the absence of a problem: a future caller that drops the root argument
                # would still satisfy the problem check via the working-checkout fallback.
                _v3_resolved = _v3_r.command_path(_v3_full)
                # The negative control for narrowing discovery to the manifest's one location: a
                # tree carrying the file only where `materialize` would never put it is NOT a
                # complete version, and used to pass.
                _v3_wrong_place = _materialized_program(_v3_tmp, "iter9-wrong-place")
                _v3_stale = _v3_wrong_place / "src" / "commands" / "sarol-eval-item.md"
                _v3_stale.parent.mkdir(parents=True, exist_ok=True)
                _v3_stale.write_bytes(_v3_frozen.stdout)
                _v3_wrong_place_bad = _v3_r.missing_command_error(_v3_wrong_place) is not None

            # (c) The bytes in the cwd are the bytes the manifest froze for this entry. An exact
            # fileset is satisfied by a correct-LOOKING file, so the structural checks alone
            # cannot see a substitution.
            _v3_sha = hashlib.sha256(_v3_cmd_file.read_bytes()).hexdigest()
            _v3_sha_bad = hashlib.sha256(_v3_cmd_file.read_bytes() + b"x").hexdigest()

            # (d) Nothing ambient in the cwd or above it, up to the tree the container mounts.
            # This is the channel that actually fired on 2026-09-09.
            _v3_ambient = [
                str(q)
                for q in (_v3_full, *_v3_full.parents)
                if (q / ".git").exists() or (q / "CLAUDE.md").exists()
                if _v3_tmp == q or _v3_tmp in q.parents or q == _v3_full
            ]

            # (e) V3d, the behavioural half: two versions whose templates differ, rendered in ONE
            # process. Mount-level checks say the paths differ; this says the BYTES followed.
            _v3_claim = load_batch(_v3_batch)[0]
            _v3_marks: dict[str, str] = {}
            _v3_cwds: dict[str, list[str]] = {}
            _v3_trees: dict[str, pathlib.Path] = {}
            for _v3_name, _v3_mark in (("iter9-v0", "V3DMARKERALPHA"), ("iter9-v1", "V3DMARKERBETA")):
                _v3_tree = _materialized_program(_v3_tmp, _v3_name)
                _v3_trees[_v3_mark] = _v3_tree
                _v3_tpl = _v3_tree / dispatch_prompt.TEMPLATE_REL
                # ⚠ Inside the fence, not appended. `prompt_body` sends only the region between the
                # markers and drops the commentary after it, so a marker on the tail proves nothing
                # about what the adjudicator was given -- it is dropped exactly as designed.
                _v3_tpl.write_text(
                    _v3_tpl.read_text(encoding="utf-8").replace(
                        dispatch_prompt.MARKER_END, f"\n{_v3_mark}\n" + dispatch_prompt.MARKER_END
                    ),
                    encoding="utf-8",
                )
                _v3_scope = isolation_mod.program_scope(
                    profile="retrieval",
                    program_dir=_v3_tree,
                    staging_root=staging_root(_v3_claim),
                    output_roots=[_v3_out],
                )
                _v3_runner = SarolRunner(
                    store,
                    require_command=False,
                    profile="retrieval",
                    container=isolation_mod.fake_container(),
                )
                try:
                    _v3_marks[_v3_mark] = _v3_runner._inner_command(
                        "adjudicator",
                        _v3_claim,
                        scope=_v3_scope,
                        materialized_path=_v3_tree,
                        run_id="v3d",
                    )[-1]
                    # V3d's second clause: "the cwd the program saw resolves under that version's
                    # snapshot". The prompt bytes alone do not prove it -- a render could read the
                    # right template and still mount the wrong tree, and the program would then be
                    # reading one version while being told about another. Taken off the REAL
                    # engine render, not a stub prefix.
                    _v3_prefix = isolation_mod.dispatch_prefix(
                        scope=_v3_scope,
                        image=isolation_mod.FAKE_IMAGE,
                        network_policy=isolation_mod.DENY_ALL_EGRESS,
                    )
                    _v3_cwds[_v3_mark] = [
                        host
                        for host, container, _mode in isolation_mod.rendered_mounts(_v3_prefix)
                        if container == _v3_scope.workdir
                    ]
                except Exception:  # noqa: BLE001 -- a refusal must read as a red check
                    _v3_marks[_v3_mark] = ""
                    _v3_cwds[_v3_mark] = []

            checks += [
                ("a freeze missing the command file is refused even though the repo ships one",
                 _v3_thin_art.status == "infra_error"
                 and _v3_thin_art.error is not None
                 and _v3_thin_art.error.code == "NESTED_COMMAND_MISSING"),
                ("...without dispatching the incomplete version", not _v3_sent),
                ("...and the refusal names the version it searched, not the working checkout",
                 _v3_thin_art.error is not None
                 and "iter9-thin" in _v3_thin_art.error.message_redacted),
                ("a complete version passes even when the working checkout lacks the file",
                 _v3_version_ok),
                ("...and that pair is not vacuous: the same Runner still faults its own checkout",
                 _v3_checkout_bad),
                ("the command file in the cwd hashes to what the manifest froze for it",
                 _v3_frozen.returncode == 0 and _v3_sha == _v3_entry["sha256"]),
                ("...and the hash is not vacuous: one extra byte breaks it",
                 _v3_sha_bad != _v3_entry["sha256"]),
                ("no .git and no CLAUDE.md in the cwd or any ancestor inside the mounted tree",
                 _v3_ambient == []),
                ("two program versions dispatched in one process each carry their own bytes",
                 "V3DMARKERALPHA" in _v3_marks.get("V3DMARKERALPHA", "")
                 and "V3DMARKERBETA" in _v3_marks.get("V3DMARKERBETA", "")),
                ("...and neither carries the other's, which a shared cwd would make impossible",
                 "V3DMARKERBETA" not in _v3_marks.get("V3DMARKERALPHA", "")
                 and "V3DMARKERALPHA" not in _v3_marks.get("V3DMARKERBETA", "")),
                ("...and the cwd each dispatch gets resolves under its OWN version's snapshot",
                 all(
                     _v3_cwds.get(m) == [str(_v3_trees[m])]
                     for m in ("V3DMARKERALPHA", "V3DMARKERBETA")
                 )),
                ("the command file is found at the manifest's path inside the version's tree",
                 _v3_resolved is not None
                 and _v3_resolved.parent == _v3_full / ".claude" / "commands"),
                ("...and a copy anywhere else does not make an incomplete version look complete",
                 _v3_wrong_place_bad),
            ]

        # ---- V4: the configuration pin refuses before anything is spent ----------------------
        with tempfile.TemporaryDirectory() as _v4_tmp:
            _v4_tmp = pathlib.Path(_v4_tmp)
            _v4_out, _v4_batch = _staged_batch(_v4_tmp)
            _v4_mat = _materialized_program(_v4_tmp, "iter4-v0")
            _v4_claim = load_batch(_v4_batch)[0]
            _v4_inputs = schemas.RunInputs(
                input_ref=str(_v4_batch), batch_id="v4", split="train"
            )
            _v4_sent: list[str] = []

            def _v4_spy(cmd, cwd, timeout):
                _v4_sent.append(" ".join(cmd))
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            # A boundary that is valid in every other way but is NOT the one pinned: same stand-in
            # policy, different image. The computed hash therefore diverges from the committed pin.
            _v4_wrong = SarolRunner(
                store,
                invoke=_v4_spy,
                paperclip_version_probe=ok_pin,
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(
                    image=isolation_mod.FAKE_IMAGE.replace("0" * 64, "1" * 64)
                ),
            )
            _v4_art = _v4_wrong.run(_v4_mat, _v4_inputs)

            # ...and the same Runner on the pinned boundary must NOT be refused, or the gate above
            # would pass for any Runner at all.
            _v4_right = SarolRunner(
                store,
                invoke=_v4_spy,
                paperclip_version_probe=ok_pin,
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(),
            )
            _v4_scope = isolation_mod.program_scope(
                profile="retrieval",
                program_dir=_v4_mat,
                staging_root=staging_root(_v4_claim),
                output_roots=[_v4_out],
            )
            _v4_right_ok = _v4_right.isolation_pin_error(_v4_scope) is None

            # The re-pin tool and the gate must compute the SAME configuration. If they drift, the
            # value an operator pastes into the manifest is one no run will ever reproduce, and the
            # gate becomes permanently red for a reason nobody can find.
            _v4_tool = isolation_mod.configuration_hash(
                isolation_mod._configurations_by_policy()[isolation_mod.STAND_IN_POLICY]
            )
            _v4_runner_side = isolation_mod.configuration_hash(
                _v4_right.isolation_configuration(_v4_scope)
            )

            _v4_builder = SarolReleaseBuilder(policy=isolation_mod.STAND_IN_POLICY)
            _v4_no_pin = _raises_valueerror(
                lambda: SarolReleaseBuilder(policy="no-such-boundary")
            )

            checks += [
                ("a boundary that is not the pinned one is refused",
                 _v4_art.status == "infra_error"
                 and _v4_art.error is not None
                 and _v4_art.error.code == "ISOLATION_PIN_MISMATCH"),
                ("...before a single claim is dispatched, since a paid run cannot be un-run",
                 not _v4_sent),
                ("...and the refusal names both hashes, so an operator can tell stale pin from "
                 "moved configuration",
                 _v4_art.error is not None
                 and "Expected" in _v4_art.error.message_redacted
                 and "computed" in _v4_art.error.message_redacted),
                ("...while the pinned boundary is NOT refused, so the gate is not simply always on",
                 _v4_right_ok),
                ("the re-pin tool computes the same configuration the gate does",
                 _v4_tool == _v4_runner_side),
                ("the release stamp is the committed pin, not the old literal",
                 _v4_builder.optimizer_isolation_hash != "sarol-2024"
                 and _v4_builder.optimizer_isolation_hash
                 == isolation_mod.committed_configuration_pin(isolation_mod.STAND_IN_POLICY)),
                ("...and a builder for a boundary with no committed pin refuses to be built at all",
                 _v4_no_pin),
            ]

        # The hard per-call spend cap has to be in the command vector, not just in a docstring --
        # and the whole rendered dispatch is checked here, because containerizing is exactly the
        # kind of change that can drop a flag while every other gate still passes.
        with tempfile.TemporaryDirectory() as _cmd_tmp:
            _cmd_tmp = pathlib.Path(_cmd_tmp)
            _cmd_mat = _materialized_program(_cmd_tmp)
            _cmd_out, _cmd_batch = _staged_batch(_cmd_tmp)
            _cmd_claim = load_batch(_cmd_batch)[0]
            _cmd_scope = isolation_mod.program_scope(
                profile="retrieval",
                program_dir=_cmd_mat,
                staging_root=staging_root(_cmd_claim),
                output_roots=[_cmd_out],
            )
            _cmd_runner = SarolRunner(
                store,
                per_call_max_budget_usd=1.25,
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(),
            )
            # ⚠ A refusal here has to read as a RED CHECK, not a traceback. A crashed suite
            # reports nothing, and a mutation that crashes the module would otherwise pass for a
            # mutation these gates caught.
            try:
                cmd_vector = _cmd_runner._inner_command(
                    "adjudicator",
                    _cmd_claim,
                    scope=_cmd_scope,
                    materialized_path=_cmd_mat,
                    run_id="b",
                )
                _cmd_full = _cmd_runner._dispatch_command(
                    "adjudicator",
                    _cmd_claim,
                    scope=_cmd_scope,
                    materialized_path=_cmd_mat,
                    run_id="b",
                    render_prefix=lambda sc: ["docker", "run", "--rm", "img"],
                )
            except Exception:  # noqa: BLE001 -- the assertions below are the report
                cmd_vector, _cmd_full = [""], [""]
            checks += [
                ("the nested command carries a hard --max-budget-usd",
                 "--max-budget-usd" in cmd_vector),
                ("...with the configured value",
                 "--max-budget-usd" in cmd_vector
                 and cmd_vector[cmd_vector.index("--max-budget-usd") + 1] == "1.25"),
                ("...alongside the timeout, which alone would not bound spend",
                 "--max-budget-usd" in cmd_vector and "--print" in cmd_vector),
                # OQ1: the prompt arrives on argv, so there is no driver session and no slash
                # command. A dispatch that reverted to one would pass every gate above.
                ("the adjudicator is invoked directly, not through a slash command",
                 not any(a.startswith("/sarol-eval-item") for a in cmd_vector)),
                ("...with the rendered prompt as the last argument",
                 _GATE_CLAIM_TEXT in cmd_vector[-1]),
                ("...and no unfilled slot left in it",
                 "{{" not in cmd_vector[-1]),
                ("the permission bypass is gone from the argv we build",
                 "--dangerously-skip-permissions" not in cmd_vector),
                # ...and the leak check can actually see a path written the way the prompt
                # writes them. The second clause is the control: hand the engine the raw markdown
                # and it reports nothing, which is why the delimiters are blanked first.
                ("a host path wrapped in markdown is still read as a host path",
                 isolation_mod.told_host_path_problem(
                     [_unmarked(f"evidence at `{_cmd_claim.staging_dir}/x.json`")], _cmd_scope
                 ) is not None
                 and isolation_mod.told_host_path_problem(
                     [f"evidence at `{_cmd_claim.staging_dir}/x.json`"], _cmd_scope
                 ) is None),
                # 1c: every path the session is told is a container path. A host path here is a
                # dispatch the adjudicator cannot complete, and it reads like a model failure.
                ("every path the session is told is a container path",
                 isolation_mod.told_host_path_problem([*cmd_vector], _cmd_scope) is None),
                ("...including the staging path in the prompt, which names /workspace",
                 container_staging(_cmd_claim, _cmd_scope) in cmd_vector[-1]
                 and str(_cmd_claim.staging_dir) not in cmd_vector[-1]),
                ("the dispatch is the container prefix followed by that argv",
                 _cmd_full[:4] == ["docker", "run", "--rm", "img"]
                 and _cmd_full[4:] == cmd_vector),
                # The exact bytes the adjudicator was given, kept beside its evidence.
                ("the prompt handed over is recorded for audit",
                 (_cmd_claim.staging_dir / "ledger" / "prompts" / "C1.md").is_file()),
                # A grant for a different staging root would render a container path that
                # resolves to nothing, and the session would fail looking for its own evidence.
                ("a claim dispatched under another root's grant is refused rather than sent",
                 _raises_valueerror(lambda: _cmd_runner._inner_command(
                     "adjudicator",
                     _cmd_claim,
                     scope=isolation_mod.program_scope(
                         profile="retrieval",
                         program_dir=_cmd_mat,
                         staging_root=_cmd_tmp / "elsewhere",
                         output_roots=[_cmd_out],
                     ),
                     materialized_path=_cmd_mat,
                     run_id="b",
                 ))),
                # ...and a stage with no prompt of its own is refused too, rather than being
                # handed the adjudicator's.
                ("a stage with no implementation is refused, not given the adjudicator's prompt",
                 _refusal_mentions(
                     lambda: _cmd_runner._inner_command(
                         "extractor",
                         _cmd_claim,
                         scope=_cmd_scope,
                         materialized_path=_cmd_mat,
                         run_id="b",
                     ),
                     "STAGE_UNIMPLEMENTED",
                 )),
            ]

        # Runner: a timeout surfaces as status="timeout", never as an exception.
        with tempfile.TemporaryDirectory() as tmp:
            # A staged claim and a materialized program, in the layout a contained run has: the
            # program mounted read-only as the cwd, the staging root the one writable grant, and
            # the optimizer's output roots denied. The flat layout this gate used to build --
            # everything directly under `tmp` -- is refused by the engine now, because granting a
            # mount that sits above a denied path is exactly what the grant is for.
            mat = _materialized_program(pathlib.Path(tmp))
            _, batch = _staged_batch(pathlib.Path(tmp))

            def timeout_invoke(cmd, cwd, t):
                return InvocationResult(
                    exit_code=124, cost_usd=0.0, duration_seconds=t, timed_out=True
                )

            r = SarolRunner(
                store,
                invoke=timeout_invoke,
                output_root=pathlib.Path(tmp) / "out",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
            container=isolation_mod.fake_container(), )
            res = r.run(
                mat,
                schemas.RunInputs(input_ref=str(batch), batch_id="b", split="train"),
            )
            checks += [
                ("a hung session surfaces as status=timeout, not an exception",
                 res.status == "timeout"),
                ("the engine checks this status on only 1 of its 3 calls, so we report it",
                 res.sub_invocation_count == 1),
            ]

            # Bug 3: the three Runner calls of one iteration must not overwrite each other's
            # manifest. Same split, same batch, different materialized version -- which is exactly
            # the current-VAL / probe-VAL pair the frontier curve is built from.
            ns_root = pathlib.Path(tmp) / "ns-out"
            ns_runner = SarolRunner(
                store,
                invoke=timeout_invoke,
                output_roots={"val": ns_root},
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
            container=isolation_mod.fake_container(), )
            mat_current = _materialized_program(pathlib.Path(tmp), "iter1-current")
            mat_probe = _materialized_program(pathlib.Path(tmp), "iter1-program-v1")
            val_inputs = schemas.RunInputs(
                input_ref=str(batch), batch_id="b", split="val"
            )
            res_cur = ns_runner.run(mat_current, val_inputs)
            res_probe = ns_runner.run(mat_probe, val_inputs)
            cur_path = pathlib.Path(res_cur.artifact_refs[0].path)
            probe_path = pathlib.Path(res_probe.artifact_refs[0].path)
            checks += [
                ("two Runner calls on one VAL batch write to DIFFERENT manifests, so a "
                 "per-iteration curve survives on disk (Bug 3)", cur_path != probe_path),
                ("...namespaced by the materialized version each call actually ran",
                 cur_path.parent.name == "iter1-current"
                 and probe_path.parent.name == "iter1-program-v1"),
                ("...both still under the declared VAL output root, so C6.9 isolation holds",
                 ns_root in cur_path.parents and ns_root in probe_path.parents),
                ("...and both files really exist rather than one having clobbered the other",
                 cur_path.exists() and probe_path.exists()),
            ]

            # Salvageability: a manifest exists after EVERY claim, so a killed run leaves
            # something pointing at the claims that finished. Asserted by spying on the
            # filesystem mid-batch rather than by reading the final file, which would prove
            # nothing about when it appeared.
            _, multi_batch = _staged_batch(
                pathlib.Path(tmp), claim_ids=("C0", "C1", "C2"), name="multi.json"
            )
            inc_root = pathlib.Path(tmp) / "inc-out"
            # (claims recorded so far, complete flag) sampled from inside the batch -- what matters
            # is that a manifest is READABLE mid-batch and honestly marked partial.
            seen_partials: list[tuple[int, Any]] = []

            torn: list[str] = []

            def spy_invoke(cmd, cwd, t):
                mp = inc_root / "m" / "run_manifest.json"
                if mp.exists():
                    # Parsed, not just stat'd. A manifest rewritten in place is readable-but-torn
                    # exactly when someone looks mid-write, and a salvage path that finds invalid
                    # JSON is no salvage path at all.
                    try:
                        obj = json.loads(mp.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as exc:
                        torn.append(str(exc))
                        return InvocationResult(
                            exit_code=0, cost_usd=0.0, duration_seconds=0.1
                        )
                    seen_partials.append((len(obj["claims"]), obj.get("complete")))
                return InvocationResult(
                    exit_code=0, cost_usd=0.0, duration_seconds=0.1
                )

            inc_runner = SarolRunner(
                store,
                invoke=spy_invoke,
                output_roots={"train": inc_root},
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
            container=isolation_mod.fake_container(), )
            mat_m = _materialized_program(pathlib.Path(tmp), "m")
            inc_res = inc_runner.run(
                mat_m,
                schemas.RunInputs(input_ref=str(multi_batch), batch_id="inc", split="train"),
            )
            final_manifest = _manifest_of(inc_res)
            checks += [
                ("a manifest exists BEFORE the batch finishes, so a killed run is salvagable "
                 "without rebuilding one by hand", bool(seen_partials)),
                ("...covering the claims finished so far, and growing",
                 sorted({n for n, _ in seen_partials}) == [1, 2]),
                ("...and honestly marked incomplete while it is partial",
                 all(flag is False for _, flag in seen_partials)),
                ("the finished manifest says so", final_manifest.get("complete") is True),
                ("...and still names the full batch, so a partial one cannot pass the Scorer's "
                 "coverage check as a real number",
                 final_manifest["requested_count"] == 3),
                ("every mid-batch read of the manifest parsed as valid JSON -- the write is "
                 "atomic (temp + rename), not a truncate-in-place", not torn),
                ("...and no .tmp scratch file is left behind for a salvage reader to trip over",
                 not list((inc_root / "m").glob("*.tmp"))),
            ]

            # --------------------------------------------------------------------------------
            # The two checks above CANNOT go red single-threaded, and a gate that cannot fail is
            # not a gate. `spy_invoke` reads the manifest BETWEEN invocations, never during a
            # write, so a truncate-in-place implementation finishes writing before control
            # returns and is never observed torn; and a plain `write_text` leaves no `.tmp`
            # files at all, so the scratch-file check passes trivially on the broken version.
            # Negative-controlled 2026-09-03: reverting the atomic write to a bare
            # `manifest_path.write_text(payload)` left every gate in the suite green.
            #
            # Durability is only testable by INTERRUPTING a write. Fail every write from the
            # second onward, halfway through the payload, then read the manifest back:
            # temp-plus-rename leaves the last complete manifest untouched, while
            # truncate-in-place leaves invalid JSON exactly where the salvage path looks for a
            # run. This is the check that motivated writing the manifest early in the first
            # place -- the v0 baseline was recovered from a killed run's partial manifest.
            crash_root = pathlib.Path(tmp) / "crash"
            _real_write_text = pathlib.Path.write_text
            _manifest_writes: list[str] = []

            def _half_write(self, data, *a, **kw):
                if self.name.startswith("run_manifest.json"):
                    _manifest_writes.append(self.name)
                    if len(_manifest_writes) >= 2:
                        _real_write_text(self, data[: len(data) // 2], *a, **kw)
                        raise OSError("simulated kill mid-manifest-write")
                return _real_write_text(self, data, *a, **kw)

            crash_runner = SarolRunner(
                store,
                invoke=lambda cmd, cwd, t: InvocationResult(
                    exit_code=0, cost_usd=0.0, duration_seconds=0.1
                ),
                output_roots={"train": crash_root},
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
            container=isolation_mod.fake_container(), )
            mat_c = _materialized_program(pathlib.Path(tmp), "c")
            pathlib.Path.write_text = _half_write
            try:
                crash_runner.run(
                    mat_c,
                    schemas.RunInputs(
                        input_ref=str(multi_batch), batch_id="crash", split="train"
                    ),
                )
            except Exception:  # noqa: BLE001 -- the file on disk is what is asserted
                pass
            finally:
                pathlib.Path.write_text = _real_write_text

            _crash_manifest = crash_root / "c" / "run_manifest.json"
            try:
                _salvaged = json.loads(_crash_manifest.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                _salvaged = None

            checks += [
                ("a manifest write KILLED HALFWAY leaves the previous manifest parseable -- the "
                 "salvage path's whole premise, and untestable without interrupting a write",
                 _salvaged is not None),
                ("...still carrying the claims that had already finished, so the salvage "
                 "recovers a run rather than an empty file",
                 isinstance(_salvaged, dict) and len(_salvaged.get("claims", [])) >= 1),
            ]

            # --------------------------------------------------------------------------------
            # The adjudicator's own reasoning trace, and the instrument that produced it.
            #
            # ⚠ **Where the trace comes from changed with containment (1d).** It used to be copied
            # out of the HOST's `~/.claude/projects/`, keyed on the session id. A contained session
            # writes that directory inside a `--rm` container, which discards it — and because the
            # old lookup was guarded at every step, every `trace_ref` would have come back null
            # while the run still reported `status: ok`. The bytes are already in hand: the same
            # `--output-format stream-json --verbose` output the cost is parsed from. So the home
            # directory below is now the NEGATIVE CONTROL rather than the source — it exists, it is
            # empty, and the trace still has to appear.
            _fake_home = pathlib.Path(tmp) / "fakehome"
            _sid = "11111111-2222-3333-4444-555555555555"
            (_fake_home / ".claude" / "projects" / "some-slug").mkdir(parents=True, exist_ok=True)
            _stream_body = (
                '{"type":"system","subtype":"init","session_id":"%s",'
                '"model":"claude-haiku-4-5"}\n'
                '{"type":"assistant","text":"the adjudicator thinking out loud"}\n'
                '{"type":"result","total_cost_usd":0.0}\n' % _sid
            )

            def _trace_invoke(cmd, cwd, t):
                return InvocationResult(
                    exit_code=0, cost_usd=0.0, duration_seconds=0.1,
                    session_id=_sid, model="claude-haiku-4-5", stream=_stream_body,
                )

            _trace_out = pathlib.Path(tmp) / "traceout"
            _trace_runner = SarolRunner(
                store,
                invoke=_trace_invoke,
                output_roots={"train": _trace_out},
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
            container=isolation_mod.fake_container(), )
            _mat_t = _materialized_program(pathlib.Path(tmp), "t")
            # Patched so the Runner's OWN resolution path is exercised, rather than testing a
            # root parameter the production call never passes. With the cache empty, a Runner that
            # still reached for it records no trace at all.
            _real_home = pathlib.Path.home
            pathlib.Path.home = staticmethod(lambda: _fake_home)
            try:
                _tres = _trace_runner.run(
                    _mat_t,
                    schemas.RunInputs(
                        input_ref=str(multi_batch), batch_id="tr", split="train"
                    ),
                )
            finally:
                pathlib.Path.home = _real_home

            # The converse: a session that streamed nothing gets no trace path invented for it.
            _quiet_out = pathlib.Path(tmp) / "quietout"
            _quiet_res = SarolRunner(
                store,
                invoke=lambda cmd, cwd, t: InvocationResult(
                    exit_code=0, cost_usd=0.0, duration_seconds=0.1, session_id=_sid
                ),
                output_roots={"train": _quiet_out},
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(),
            ).run(
                _materialized_program(pathlib.Path(tmp), "q"),
                schemas.RunInputs(input_ref=str(multi_batch), batch_id="q", split="train"),
            )
            _qman = _manifest_of(_quiet_res)
            _qstage = next(iter(((_qman.get("claims") or [{}])[0].get("stages") or {}).values()), {})

            _tman = _manifest_of(_tres)
            _tclaim = (_tman.get("claims") or [{}])[0]
            _tstage = next(iter((_tclaim.get("stages") or {}).values()), {})
            _tref = _tstage.get("trace_ref")
            # A real subprocess emitting a real stream-json line: no LLM, no spend, but the
            # production invoker's own parsing path.
            _live_meta = headless_claude_invoke(
                [
                    "sh", "-c",
                    "printf '%s\\n' "
                    "'{\"type\":\"system\",\"subtype\":\"init\","
                    "\"session_id\":\"S9\",\"model\":\"claude-haiku-4-5\"}'",
                ],
                pathlib.Path.cwd(),
                20.0,
            )
            _sid_p, _model_p = _parse_stream_meta(
                '{"type":"system","subtype":"init","session_id":"abc","model":"claude-haiku-4-5"}\n'
                'not json at all\n'
                '{"type":"result","total_cost_usd":0.4}\n'
            )

            checks += [
                ("the stream's session_id and RESOLVED model are parsed out of the output that "
                 "was previously read for cost and discarded",
                 (_sid_p, _model_p) == ("abc", "claude-haiku-4-5")),
                # ...and the same assertion against the REAL invoker. Testing `_parse_stream_meta`
                # alone proves the parser, not that anything calls it -- the exact shape of the
                # `loop_ops` gap, where a gate drove the engine directly and nothing checked that
                # the production entrypoint passed the argument. Negative-controlled: blanking the
                # call site leaves the parser gate above green.
                ("...and `headless_claude_invoke` actually calls it, so the fields reach a real "
                 "InvocationResult rather than only a unit-tested helper",
                 (_live_meta.session_id, _live_meta.model) == ("S9", "claude-haiku-4-5")),
                ("each claim records the session that judged it, so a trace is reachable at all",
                 _tstage.get("session_id") == _sid),
                ("...and the RESOLVED model id rather than the alias that was requested -- an "
                 "alias moves when a new release ships, so it cannot identify an instrument",
                 _tstage.get("model") == "claude-haiku-4-5"),
                ("the trace lands in the run root, taken from the stream the run already "
                 "captured rather than from ~/.claude/projects, which a --rm container discards "
                 "and Claude Code prunes",
                 bool(_tref) and pathlib.Path(_tref).exists()
                 and str(_trace_out) in str(_tref)),
                ("...byte-identical to what the session streamed back",
                 bool(_tref)
                 and pathlib.Path(_tref).read_text(encoding="utf-8") == _stream_body),
                # The control for the line above: the host cache was present and EMPTY for that
                # run, so a Runner still globbing it would have recorded no trace at all.
                ("...with the host transcript cache empty throughout, which is what a contained "
                 "session leaves behind",
                 not list((_fake_home / ".claude" / "projects").glob("*/*.jsonl"))),
                ("a session that streamed nothing records no trace, rather than a path to an "
                 "empty file standing in for evidence",
                 _qstage.get("trace_ref") is None),
                ("the run manifest carries the model as run identity, the same rule as "
                 "retrieval_k: a macro-F1 without its instrument is not a result",
                 _tman.get("model") == "claude-haiku-4-5"),
                ("the judge defaults to the cheap model, since the judge is ~113 sessions an "
                 "iteration and the optimizer is one",
                 SarolRunner(store, require_command=False, container=isolation_mod.fake_container()).model == DEFAULT_JUDGE_MODEL
                 and DEFAULT_JUDGE_MODEL == "haiku"),
            ]

            # The round-trip canary: a moved instrument stops the run before any scored claim.
            _staged_batch(pathlib.Path(tmp), claim_ids=("CANARY",), name="canary.json")
            canary_claim = ClaimRecord(
                claim_id="CANARY",
                citekey="k1",
                staging_dir=pathlib.Path(tmp) / "run" / "train" / "staging" / "CANARY",
            )
            dispatched_claims: list[str] = []

            def canary_invoke(cmd, cwd, t):
                # ⚠ Read off the container path, not a `--claim` flag: since OQ1 the claim is
                # named by the rendered prompt and the staging path inside it, not by argv.
                dispatched_claims.append(_claim_dispatched(cmd))
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            # No verdict file exists, so validation fails -> the canary cannot match -> stop.
            canary_runner = SarolRunner(
                store,
                invoke=canary_invoke,
                output_root=pathlib.Path(tmp) / "out2",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                canary=CanarySpec(claim=canary_claim, expected_verdict="ACCURATE"),
            container=isolation_mod.fake_container(), )
            canary_res = canary_runner.run(
                mat,
                schemas.RunInputs(input_ref=str(batch), batch_id="b", split="train"),
            )
            checks += [
                ("a failed canary stops the run", canary_res.status == "infra_error"),
                ("...named as a canary failure",
                 canary_res.error is not None and canary_res.error.code == "CANARY_FAILED"),
                ("...before any scored claim is dispatched",
                 all(c == "CANARY" for c in dispatched_claims)),
                ("...and it is not scored as a bad result, which is the whole point",
                 canary_res.status != "ok"),
            ]

            # C6.1 -- the profile decides what gets dispatched. This is the check that would have
            # caught the landed `for stage in STAGES` loop running Phase 2 under a Phase 1 label.
            # ⚠ **The stage is no longer readable off argv** (OQ1: no `--stage` flag, because there
            # is no slash command), so what is counted here is dispatches per claim against the
            # profile's own stage list -- and, for agentic, that there are none at all.
            dispatches: list[str] = []

            def stage_spy(cmd, cwd, t_):
                dispatches.append(cmd[-1])
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            def run_under(profile_name):
                dispatches.clear()
                runner = SarolRunner(
                    store,
                    invoke=stage_spy,
                    output_root=pathlib.Path(tmp) / f"out-{profile_name}",
                    paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                    require_command=False,
                    profile=profile_name,
                container=isolation_mod.fake_container(), )
                res_ = runner.run(
                    mat,
                    schemas.RunInputs(input_ref=str(batch), batch_id="b", split="train"),
                )
                return list(dispatches), res_

            retr_prompts, retr_res = run_under("retrieval")
            agentic_prompts, agentic_res = run_under("agentic")
            retr_manifest = _manifest_of(retr_res)
            checks += [
                ("under retrieval the Runner dispatches the adjudicator alone",
                 len(retr_prompts) == len(profiles_mod.RETRIEVAL.stages)
                 and profiles_mod.RETRIEVAL.stages == ("adjudicator",)),
                ("...one session per claim, not three",
                 len(retr_prompts) == 1),
                ("...and what it dispatches is the adjudicator's own prompt, pointed at the "
                 "rubric inside the container",
                 bool(retr_prompts)
                 and f"{isolation_mod.CONTAINER_PROGRAM}/experiments/sarol-2024/specs/"
                 "verdict_schema_sarol.md" in retr_prompts[0]),
                # agentic used to dispatch three sessions here. It cannot any more, and the reason
                # is the grant rather than the stage list: its extractor reads the source paper and
                # the grant mounts none, so it is refused before anything is dispatched. Running it
                # would have had the extractor fail looking for a paper, which reads as a model
                # error rather than a missing mount.
                ("agentic is refused outright, because the grant carries no paper for its "
                 "extractor to read",
                 agentic_res.status == "infra_error"
                 and agentic_res.error is not None
                 and agentic_res.error.code == "PROGRAM_GRANT_REFUSED"),
                ("...naming the mount it would need, not just failing",
                 agentic_res.error is not None
                 and "paper" in agentic_res.error.message_redacted),
                ("...without dispatching a single session", not agentic_prompts),
                # C6.5: the frontier is a bare scalar, so the profile has to be recoverable from
                # the artifacts or two different experiments become indistinguishable after the
                # fact.
                ("the run manifest records which profile produced it",
                 retr_manifest["profile"] == "retrieval"),
                ("...with the retrieval budget, without which the number is unreportable",
                 retr_manifest["retrieval_k"] == 20),
                ("...and the stages it actually ran",
                 retr_manifest["profile_stages"] == ["adjudicator"]),
                # Containerizing swaps the instrument, so the image and the Claude Code inside it
                # belong beside `model` -- a macro-F1 is only comparable to an earlier one if both
                # were measured on the same thing.
                ("the run manifest records the container the program ran in",
                 isinstance(retr_manifest.get("container"), dict)
                 and "image" in retr_manifest["container"]),
                ("...and a run under the selftest stand-in says so, so its manifest cannot be "
                 "mistaken for one produced under a real boundary",
                 "stand_in" in retr_manifest["container"]),
            ]

            # A batch naming no claims has nothing to grant a container for and nothing to score.
            _empty_batch = pathlib.Path(tmp) / "empty.json"
            _empty_batch.write_text(json.dumps({"claims": []}), encoding="utf-8")
            _empty_dispatched: list[str] = []
            _empty_runner = SarolRunner(
                store,
                invoke=lambda cmd, cwd, t: _empty_dispatched.append("x") or InvocationResult(
                    exit_code=0, cost_usd=0.0, duration_seconds=0.1
                ),
                output_root=pathlib.Path(tmp) / "empty-out",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(),
            )
            try:
                _empty_res = _empty_runner.run(
                    mat,
                    schemas.RunInputs(
                        input_ref=str(_empty_batch), batch_id="mt", split="train"
                    ),
                )
            except BaseException:  # noqa: BLE001 -- "never raises" is the contract under test
                _empty_res = None
            checks += [
                ("an empty batch is refused up front rather than scored as a perfect run",
                 _empty_res is not None
                 and _empty_res.status == "infra_error"
                 and _empty_res.error is not None
                 and _empty_res.error.code == "EMPTY_BATCH"),
                ("...and nothing is dispatched for it", not _empty_dispatched),
            ]

            # ------------------------------------------------------------------------------
            # V2d: two claims x two program versions, in one process. A prefix built once and
            # reused across either axis is the failure mode -- it points a v1 dispatch at v0's
            # bytes, or claim B at claim A's staging, and both produce a plausible verdict. So
            # the assertion is on the PAIRING: every dispatch's program mount is its own
            # version and its own claim, not merely that four dispatches happened.
            # ------------------------------------------------------------------------------
            _, v_batch = _staged_batch(
                pathlib.Path(tmp), claim_ids=("V1", "V2"), name="versions.json"
            )
            v_cmds: list[list[str]] = []

            def _version_spy(cmd, cwd, t_):
                v_cmds.append(list(cmd))
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            v_mats = [
                _materialized_program(pathlib.Path(tmp), "iter2-v0"),
                _materialized_program(pathlib.Path(tmp), "iter2-v1"),
            ]
            # The renderer records the grant it was handed, once per call -- which is what makes
            # "rendered per dispatch" assertable at all. Reading only the final argv cannot tell a
            # prefix rendered four times from one rendered once and reused, because two claims
            # under one staging root legitimately produce the SAME mount set.
            v_renders: list = []
            v_runner = SarolRunner(
                store,
                invoke=_version_spy,
                output_root=pathlib.Path(tmp) / "versions-out",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                container=isolation_mod.fake_container(calls=v_renders),
            )
            for _v_mat in v_mats:
                v_runner.run(
                    _v_mat,
                    schemas.RunInputs(
                        input_ref=str(v_batch), batch_id="vv", split="train"
                    ),
                )

            def _program_mount(argv):
                return next(
                    (host for host, container, _mode in isolation_mod.rendered_mounts(argv)
                     if container == isolation_mod.CONTAINER_PROGRAM),
                    None,
                )

            def _claim_told(argv):
                return _claim_dispatched(argv)

            _v_pairs = sorted((_program_mount(c), _claim_told(c)) for c in v_cmds)
            checks += [
                ("two claims across two program versions dispatch four containers (V2d)",
                 len(v_cmds) == 4),
                ("...each mounting the version it was asked to score, and each told its own "
                 "claim",
                 _v_pairs == sorted(
                     (str(m), cid) for m in v_mats for cid in ("V1", "V2")
                 )),
                # ⚠ The mount set is deliberately shared by claims under one staging root, so
                # identical argv is NOT evidence of a reused prefix. Counting the render calls is.
                ("...with the prefix rendered once per dispatch rather than once per grant and "
                 "reused, which identical argv could not distinguish",
                 len(v_renders) == 4),
                ("...each render handed the grant for the version being scored",
                 sorted(str(s.program) for s in v_renders)
                 == sorted(str(m) for m in v_mats for _ in range(2))),
                ("...and all four mount the staging root read-write, the one place the "
                 "program may write",
                 all(
                     any(
                         container == isolation_mod.CONTAINER_STAGING and mode == "rw"
                         for _h, container, mode in isolation_mod.rendered_mounts(c)
                     )
                     for c in v_cmds
                 )),
            ]

            # ==========================================================================
            # Concurrent dispatch. Claims are independent, so the ONLY thing `max_workers`
            # may change is wall-clock -- not which sessions run, not what they are told,
            # and not a single number in the manifest.
            # ==========================================================================
            _, conc_batch = _staged_batch(
                pathlib.Path(tmp),
                claim_ids=tuple(f"P{7 - i}" for i in range(8)),
                name="conc.json",
            )

            # Tracks how many dispatches are in flight at once, and dispatches claims with
            # DESCENDING durations so the last-submitted claim finishes first. That ordering
            # is what makes the determinism gate below meaningful: under a completion-ordered
            # implementation the manifest would come back reversed.
            inflight = {"now": 0, "peak": 0}
            inflight_lock = threading.Lock()

            def concurrent_invoke(cmd, cwd, t_):
                # The claim is named by the container staging path in the rendered prompt now,
                # not by a `--claim` flag (OQ1).
                claim_id = _claim_dispatched(cmd)
                # A dispatch this spy cannot attribute gets no sleep rather than a crash, so a
                # mutation shows up as a red check below instead of a traceback.
                _rank = int(claim_id[1:]) if claim_id[1:].isdigit() else 0
                with inflight_lock:
                    inflight["now"] += 1
                    inflight["peak"] = max(inflight["peak"], inflight["now"])
                # The FIRST-submitted claim (P7) is the slowest and the last (P0) the
                # fastest, so completion order is the reverse of submission order.
                time.sleep(0.05 * (1 + _rank))
                with inflight_lock:
                    inflight["now"] -= 1
                return InvocationResult(exit_code=0, cost_usd=0.25, duration_seconds=0.1)

            def run_conc(workers, out_name):
                inflight["now"] = 0
                inflight["peak"] = 0
                runner_ = SarolRunner(
                    store,
                    invoke=concurrent_invoke,
                    output_root=pathlib.Path(tmp) / out_name,
                    paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                    require_command=False,
                    profile="retrieval",
                    max_workers=workers,
                container=isolation_mod.fake_container(), )
                t0 = time.monotonic()
                res_ = runner_.run(
                    mat,
                    schemas.RunInputs(
                        input_ref=str(conc_batch), batch_id="cc", split="train"
                    ),
                )
                elapsed = time.monotonic() - t0
                man = _manifest_of(res_)
                return man, res_, elapsed, inflight["peak"]

            par_man, par_res, par_elapsed, par_peak = run_conc(4, "conc-par")
            ser_man, ser_res, ser_elapsed, ser_peak = run_conc(1, "conc-ser")

            checks += [
                # The point of the change. Without a pool `peak` can never exceed 1.
                ("max_workers>1 really dispatches claims concurrently", par_peak > 1),
                ("...bounded BY max_workers, so the pool size is the actual throttle and a "
                 "batch cannot open 300 sessions at once", par_peak <= 4),
                ("...while the default stays strictly serial, so nothing changes for a caller "
                 "that did not ask for concurrency", ser_peak == 1),
                # A MARGIN, not `par < ser`. The batch sleeps 1.80s serially and ~0.55s over
                # four workers, so a real speed-up clears 0.75x easily -- whereas bare
                # `par < ser` is a coin flip once both paths are serial, and went green under
                # the forced-serial negative control. A gate that passes on a coin flip is not
                # a gate.
                ("...and it is actually faster in wall-clock, which is the only reason to do "
                 "any of this", par_elapsed < ser_elapsed * 0.75),

                # Identity: concurrency must not perturb the instrument or the numbers.
                ("every claim comes back exactly once under concurrency, none lost to a race",
                 [c["claim_id"] for c in par_man["claims"]] == [f"P{7 - i}" for i in range(8)]),
                # The ids are deliberately submitted P7..P0, so alphabetical order is the
                # REVERSE of submission order. That makes this gate fail if records are ever
                # collected keyed on `claim_id` instead of submission index, not only if they
                # are collected in arrival order.
                ("...in INPUT order even though they finished in reverse, so the manifest is "
                 "byte-deterministic and diffable across runs",
                 [c["claim_id"] for c in par_man["claims"]]
                 == [c["claim_id"] for c in ser_man["claims"]]),
                ("...and the concurrent manifest is otherwise identical to the serial one, "
                 "which is what lets a serially-measured baseline stay comparable",
                 {k: v for k, v in par_man.items() if k != "claims"}
                 == {k: v for k, v in ser_man.items() if k != "claims"}),

                # The deleted counter. A non-atomic `+=` across threads loses increments; the
                # totals are now DERIVED from the records, so they are exact by construction.
                ("the cost total survives concurrency exactly -- 8 claims x 1 adjudicator x "
                 "$0.25, no increment lost to a racy +=",
                 abs(par_res.cost_usd - 2.0) < 1e-9),
                ("...and the sub-invocation count likewise",
                 par_res.sub_invocation_count == 8),
                ("...with the manifest agreeing with the returned artifacts, since both now "
                 "read the same derivation rather than a shared mutable counter",
                 abs(par_man["cost_usd"] - par_res.cost_usd) < 1e-9
                 and par_man["sub_invocation_count"] == par_res.sub_invocation_count),
                ("...and serial dispatch reports the identical totals",
                 abs(ser_res.cost_usd - par_res.cost_usd) < 1e-9
                 and ser_res.sub_invocation_count == par_res.sub_invocation_count),

                # batch_totals is the whole derivation, so pin its contract directly.
                ("batch_totals sums per-stage costs rather than trusting a counter",
                 batch_totals([{"stages": {"a": {"cost_usd": 1.5}, "b": {"cost_usd": 0.25}}}])
                 == (2, 1.75)),
                ("...and counts a claim that failed before dispatching any stage as zero, not "
                 "as one free session", batch_totals([{"stages": {}}]) == (0, 0.0)),
            ]

            # A duplicated claim_id in one batch must not collapse two records into one. This
            # is why results are collected by SUBMISSION INDEX and not keyed on claim_id.
            # Both entries point at one real staged claim: the refusal fires on the repeated id
            # before any grant is built, so what matters is that the batch is otherwise valid.
            _dup_staging = pathlib.Path(tmp) / "run" / "train" / "staging" / "C1"
            dup_batch = pathlib.Path(tmp) / "dup.json"
            dup_batch.write_text(json.dumps({"claims": [
                {"claim_id": "D1", "citekey": "k1", "staging_dir": str(_dup_staging)},
                {"claim_id": "D1", "citekey": "k1", "staging_dir": str(_dup_staging)},
            ]}), encoding="utf-8")
            dup_dispatched: list[str] = []
            dup_runner = SarolRunner(
                store,
                invoke=lambda cmd, cwd, t_: (
                    dup_dispatched.append(cmd[3]),
                    InvocationResult(exit_code=0, cost_usd=0.1, duration_seconds=0.1),
                )[1],
                output_root=pathlib.Path(tmp) / "conc-dup",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                max_workers=4,
            container=isolation_mod.fake_container(), )
            dup_res = dup_runner.run(
                pathlib.Path(tmp),
                schemas.RunInputs(input_ref=str(dup_batch), batch_id="dd", split="train"),
            )
            checks += [
                # Every per-claim artifact is claim_id-keyed, so duplicates would race on the same
                # verdict and trace paths once dispatch is concurrent. No DRAWN batch can contain
                # one (set union / sample-without-replacement); a hand-written --train-inputs file
                # can, which is exactly where a typo lives.
                ("a batch repeating a claim_id is REFUSED, not raced -- two claims writing one "
                 "verdict path would otherwise keep whichever thread finished last",
                 dup_res.status == "infra_error"
                 and dup_res.error is not None
                 and dup_res.error.code == "DUPLICATE_CLAIM_IDS"),
                ("...before a single claim is dispatched, so the refusal costs nothing",
                 dup_dispatched == []),
            ]

            # ------------------------------------------------------------------------------
            # Concurrency through the REAL invoker. Every gate above injects a Python callable
            # for `invoke`, so `headless_claude_invoke` itself -- Popen, `start_new_session`,
            # the pipe drain, stream-json parsing -- has never run on more than one thread at a
            # time. `sh` stands in for `claude` so this costs nothing and touches no API, but
            # the process machinery is the production path, not a stub.
            # ------------------------------------------------------------------------------
            _, real_batch = _staged_batch(
                pathlib.Path(tmp),
                claim_ids=tuple(f"R{i}" for i in range(8)),
                name="real.json",
            )
            real_inflight = {"now": 0, "peak": 0}
            real_lock = threading.Lock()

            class _RealInvokerRunner(SarolRunner):
                """Real `headless_claude_invoke`, with `sh` in place of the whole dispatch.

                ⚠ The override is the WHOLE command, prefix included: standing `sh` in for the
                inner argv alone would leave the container prefix in front of it, and this gate is
                about the process machinery -- Popen, the process group, the pipe drain -- not
                about Docker, which it must not need.
                """

                def _dispatch_command(
                    self, stage, claim, *, scope, materialized_path, run_id, render_prefix
                ):
                    # Emits the same stream-json init + result lines the production parser reads
                    # cost, session_id and the resolved model out of.
                    return ["sh", "-c", (
                        "sleep 0.2; "
                        "printf '%s\\n' "
                        "'{\"type\":\"system\",\"subtype\":\"init\","
                        f"\"session_id\":\"S-{claim.claim_id}\","
                        "\"model\":\"claude-haiku-4-5\"}'; "
                        "printf '%s\\n' '{\"type\":\"result\",\"total_cost_usd\":0.125}'"
                    )]

            def counting_real_invoke(cmd, cwd, timeout):
                """The PRODUCTION invoker, wrapped only to count overlap.

                Passed as the `invoke` argument rather than overridden as a method: `__init__`
                assigns `self.invoke` as an instance attribute, which shadows any class-level
                method of the same name -- so a subclass override here is silently never called.
                """
                with real_lock:
                    real_inflight["now"] += 1
                    real_inflight["peak"] = max(real_inflight["peak"], real_inflight["now"])
                try:
                    return headless_claude_invoke(cmd, cwd, timeout)
                finally:
                    with real_lock:
                        real_inflight["now"] -= 1

            real_runner = _RealInvokerRunner(
                store,
                invoke=counting_real_invoke,
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                max_workers=4,
                output_root=pathlib.Path(tmp) / "conc-real",
                # ⚠ The 23rd site. A subclass that does not override `__init__`, so it reaches the
                # same refusal while matching no text search for `SarolRunner(`.
                container=isolation_mod.fake_container(),
            )
            _t0 = time.monotonic()
            real_res = real_runner.run(
                mat,
                schemas.RunInputs(input_ref=str(real_batch), batch_id="rr", split="train"),
            )
            real_elapsed = time.monotonic() - _t0
            real_man = _manifest_of(real_res)
            real_stages = [
                st
                for rec in (real_man.get("claims") or [])
                for st in (rec.get("stages") or {}).values()
            ]
            checks += [
                ("the REAL invoker survives concurrent use -- 8 nested process trees spawned "
                 "from 4 threads, each in its own process group",
                 real_inflight["peak"] > 1 and len(real_man.get("claims") or []) == 8),
                ("...with every claim's cost parsed out of its OWN process's stdout, not "
                 "cross-wired between concurrent pipes",
                 len(real_stages) == 8
                 and all(abs(st["cost_usd"] - 0.125) < 1e-9 for st in real_stages)),
                ("...and every session id likewise, which is what makes a trace attributable "
                 "to the claim it judged",
                 sorted(st["session_id"] for st in real_stages)
                 == sorted(f"S-R{i}" for i in range(8))),
                ("...summing to the exact batch total, through the real parse path",
                 abs(real_res.cost_usd - 1.0) < 1e-9 and real_res.sub_invocation_count == 8),
                ("...and genuinely in parallel: 8 x 0.2s of real subprocess serialises to 1.6s, "
                 "so four workers must come in well under that",
                 real_elapsed < 1.2),
            ]

            # An unexpected exception in one worker must stop the batch, not merely surface
            # after it. The serial loop failed fast for free; a thread pool does the opposite
            # by default -- `ThreadPoolExecutor.__exit__` calls `shutdown(wait=True)`, which
            # DRAINS every already-submitted claim before the exception is allowed out. On a
            # 300-claim paid batch that is 297 claims of spend after the failure.
            _, fail_batch = _staged_batch(
                pathlib.Path(tmp),
                claim_ids=tuple(f"X{i}" for i in range(12)),
                name="fail.json",
            )
            dispatched_ids: list[str] = []
            dispatch_lock = threading.Lock()

            def exploding_invoke(cmd, cwd, t_):
                cid = _claim_dispatched(cmd)
                with dispatch_lock:
                    dispatched_ids.append(cid)
                if cid == "X1":
                    raise RuntimeError("simulated unexpected worker failure")
                time.sleep(0.05)
                return InvocationResult(exit_code=0, cost_usd=0.1, duration_seconds=0.1)

            fail_runner = SarolRunner(
                store,
                invoke=exploding_invoke,
                output_root=pathlib.Path(tmp) / "conc-fail",
                paperclip_version_probe=lambda: store.runtime_pins["paperclip_cli"],
                require_command=False,
                profile="retrieval",
                max_workers=2,
            container=isolation_mod.fake_container(), )
            raised = None
            try:
                fail_runner.run(
                    mat,
                    schemas.RunInputs(
                        input_ref=str(fail_batch), batch_id="ff", split="train"
                    ),
                )
            except RuntimeError as exc:
                raised = exc
            fail_man_path = (
                pathlib.Path(tmp) / "conc-fail" / "train" / mat.name / "run_manifest.json"
            )
            fail_man = (
                json.loads(fail_man_path.read_text(encoding="utf-8"))
                if fail_man_path.exists() else {}
            )
            checks += [
                ("an unexpected worker exception still escapes run(), as it did serially",
                 isinstance(raised, RuntimeError)),
                ("...and the claims queued behind it are NEVER dispatched, so a failure at "
                 "claim 2 of 12 does not pay for the other 10",
                 0 < len(dispatched_ids) <= 4),
                ("...while claims that finished before the failure survive in the manifest, so "
                 "the run is still salvageable",
                 bool(fail_man.get("claims"))),
            ]
    else:
        checks.append((f"engine not found at {engine_path()} -- engine-facing checks SKIPPED", True))

    # -- the container boundary, and the census of who takes one (1f / V2c) ----------------------
    _sites = _runner_construction_sites()
    _production = [x for x in _sites if not x["in_selftest"]]
    _store_for_refusal = SarolProgramStore(repo_root=REPO_ROOT)
    checks += [
        ("every place that constructs a Runner states a container",
         bool(_sites) and all(x["states_container"] for x in _sites)),
        (f"...and there are exactly {_EXPECTED_RUNNER_SITES} of them, so a new site has to be read",
         len(_sites) == _EXPECTED_RUNNER_SITES),
        ("...of which exactly three can run outside a selftest",
         len(_production) == 3),
        ("...and they are build_components, the canary and the baseline recut",
         {x["file"] for x in _production}
         == {"dispatcher.py", "canary.py", "run_baseline.py"}),
        ("no site that can run outside a selftest uses the selftest stand-in",
         not [x for x in _production if x["uses_fake"]]),
        ("...nor opts out with an explicit None, which only a refusal control may do",
         not [x for x in _production if x["states_none"]]),
        ("...and the only sites that do opt out are the refusal controls, which are selftests",
         all(x["in_selftest"] for x in _sites if x["states_none"])),
        ("...and both command-line entry points build the real one-host boundary",
         "shipping_container" in (_HERE / "dispatcher.py").read_text(encoding="utf-8")
         and "shipping_container"
         in (_HERE.parent / "scripts" / "run_baseline.py").read_text(encoding="utf-8")),
        # Negative controls: the refusal has to be watched failing, or it proves nothing.
        ("a Runner built with no container is refused, before anything is dispatched",
         _raises_valueerror(lambda: SarolRunner(_store_for_refusal, container=None))),
        ("...and the refusal says what to pass instead",
         _refusal_mentions(
             lambda: SarolRunner(_store_for_refusal, container=None), "shipping_container"
         )),
        ("...and an image named by tag rather than digest is refused too",
         _raises_valueerror(
             lambda: SarolRunner(
                 _store_for_refusal,
                 container=isolation_mod.shipping_container(
                     image="ghcr.io/example/paper-trail:latest"
                 ),
             )
         )),
        ("...while a digest-pinned shipping container is accepted",
         SarolRunner(
             _store_for_refusal,
             container=isolation_mod.shipping_container(image=isolation_mod.FAKE_IMAGE),
         ).container is not None),
        # 1d: the judge's trace no longer depends on a cache Claude Code prunes.
        ("the invocation result carries the session stream, so a contained trace is recoverable",
         "stream" in {f.name for f in dataclasses.fields(InvocationResult)}),
        # ⚠ Scoped to the function's OWN source. Grepping the whole file for the keyword was a
        # check that could never fail, because this very line contains the string it looked for --
        # the same self-reference that made the first census report 3 sites out of 20 (2026-09-18).
        ("...and the real invoker fills it from what it captured rather than dropping it",
         "stream=" in inspect.getsource(headless_claude_invoke)),
    ]

    failed_n = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        failed_n += 0 if ok else 1
    print(f"\n{len(checks) - failed_n}/{len(checks)} passed")
    return 1 if failed_n else 0


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run the offline adapter gates")
    ap.add_argument("--edit-scope", action="store_true", help="print the optimizer's EDIT globset")
    ap.add_argument(
        "--verify-contracts", action="store_true", help="re-hash the contract files and report"
    )
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if args.edit_scope:
        store = SarolProgramStore()
        print(json.dumps(
            {"editable": store.editable_paths(), "contract_read_only": store.contract_paths()},
            indent=2,
        ))
        return 0
    if args.verify_contracts:
        violations = SarolProgramStore().verify_contract_files()
        if violations:
            for v in violations:
                print(f"MUTATED  {v}")
            return 1
        print("OK  all contract files match the freeze")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
