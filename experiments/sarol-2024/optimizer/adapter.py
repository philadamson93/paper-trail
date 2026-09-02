"""paper-trail's ``TaskAdapter`` — the four protocols `agentic-label-opt`'s ``run_loop`` drives.

paper-trail is consumer #3 of the shared engine (rad-eval #1, crc-extraction-agent #2). The engine
abstracts the *container* — the manifest freeze, the materialize step, the audit ledger, the
frontier bookkeeping — and never the *payload*. This module is the payload: `ProgramStore`,
`Runner`, `Scorer`, `ReleaseBuilder`, plus the agent wrapper that enforces the one guarantee the
engine cannot.

What is genuinely load-bearing here, and why (plan Parts C1/C4, engine @ `6d621ac`):

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

import dataclasses
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
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

import evidence_producers  # noqa: E402
import profiles as profiles_mod  # noqa: E402
import validate_sarol  # noqa: E402

#: Repo root: experiments/sarol-2024/optimizer/adapter.py -> up 3.
REPO_ROOT = _HERE.parents[2]
MANIFEST_PATH = _HERE.parent / "program-v0" / "manifest.json"

#: Where `agentic-label-opt` is checked out. Same default as `scripts/materialize_smoke.py`.
DEFAULT_ENGINE = pathlib.Path.home() / "Documents" / "Misc" / "Projects" / "agentic-label-opt"

SCHEMA_VERSION = "0.1.0"

#: The three nested Claude Code sessions one claim costs. Named because the cost preflight has to
#: multiply by it and because `RunArtifacts.sub_invocation_count` is the field that carries it.
#: Every stage that exists. What a given run dispatches is the *profile's* subset
#: (`profiles.Profile.stages`) -- under `retrieval` that is `("adjudicator",)` alone. Kept as the
#: full tuple because it is the vocabulary, not the schedule.
STAGES: tuple[str, ...] = profiles_mod.ALL_STAGES


def engine_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("AGENTIC_LABEL_OPT", DEFAULT_ENGINE)).expanduser()


def _import_engine():
    """Import the engine's schema types. Kept in a function so this module is importable (and
    self-testable) on a machine without the engine checked out."""
    path = engine_path()
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

    def verify_contract_files(self, tree_root: pathlib.Path | None = None) -> list[ContractViolation]:
        """Re-hash every ``contract_file=True`` entry against its frozen ``sha256``.

        This is the *only* thing making those files immutable — the engine's own flag checks that a
        contract file is present in the fileset, never that its bytes are unchanged. Returns the
        violations rather than raising, so the caller decides the failure mode (the agent wrapper
        turns them into a nonzero exit; the dispatcher preflight prints them).
        """
        root = pathlib.Path(tree_root).resolve() if tree_root is not None else self.repo_root
        violations: list[ContractViolation] = []
        for entry in self.entries:
            if not entry.get("contract_file"):
                continue
            target = root / entry["path"]
            if not target.exists():
                violations.append(ContractViolation(entry["path"], entry["sha256"], None))
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != entry["sha256"]:
                violations.append(ContractViolation(entry["path"], entry["sha256"], actual))
        return violations


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


def headless_claude_invoke(
    cmd: Sequence[str], cwd: pathlib.Path, timeout_seconds: float
) -> InvocationResult:
    """Run one nested headless session under a hard timeout.

    ``loop.py`` has no timeout anywhere, so the bound has to live here: an agentic Runner that
    hangs would otherwise stall the whole optimization loop with no stop.
    """
    started = time.monotonic()
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return InvocationResult(
            exit_code=124,
            cost_usd=0.0,
            duration_seconds=time.monotonic() - started,
            timed_out=True,
            detail=f"timed out after {timeout_seconds}s",
        )
    return InvocationResult(
        exit_code=proc.returncode,
        cost_usd=_parse_cost(proc.stdout),
        duration_seconds=time.monotonic() - started,
        detail=(proc.stderr or "").strip()[:500],
    )


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
            staging_dir=pathlib.Path(obj["staging_dir"]),
            source_mode=obj.get("source_mode", "pdf"),
        )


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
        model: str = "opus",
        canary: "CanarySpec | None" = None,
        command_name: str = "sarol-eval-item",
        require_command: bool = True,
        profile=None,
    ) -> None:
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

    # -- dispatch ----------------------------------------------------------------------------

    def _stage_command(
        self, stage: str, claim: ClaimRecord, materialized_path: pathlib.Path
    ) -> list[str]:
        prompt = (
            f"/{self.command_name} --stage {stage} --claim {claim.claim_id} "
            f"--staging {claim.staging_dir} --spec-root {materialized_path}"
        )
        return [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            # "project", not "" -- "" silently disables the whole hook stack. Note this reads
            # .claude/settings.json from the *cwd*, which is why cwd is a real checkout.
            "--setting-sources",
            "project",
            "--strict-mcp-config",
            # The hard stop. Without it the only bound on a single nested session is the
            # wall-clock timeout, which a cheap-but-endless session satisfies while still
            # spending. The engine will not stop it either.
            "--max-budget-usd",
            str(self.per_call_max_budget_usd),
        ]

    def command_path(self) -> pathlib.Path | None:
        """Where the nested slash command is expected to live, if it exists at all."""
        for rel in (
            f".claude/commands/{self.command_name}.md",
            f"src/commands/{self.command_name}.md",
            f"experiments/sarol-2024/commands/{self.command_name}.md",
        ):
            candidate = self.working_checkout / rel
            if candidate.exists():
                return candidate
        return None

    def missing_command_error(self) -> str | None:
        """Fail loudly when the command the Runner dispatches does not exist.

        Without this the first real run burns a session per stage and fails somewhere inside
        Claude Code with an unrelated-looking message. `/sarol-eval-item` is named as a Task 5
        eval-arm deliverable and is not built yet, so this preflight is the honest boundary
        between "the adapter is wired" and "the pipeline can actually run".
        """
        if not self.require_command:
            return None
        if self.command_path() is None:
            return (
                f"nested command /{self.command_name} not found under .claude/commands/, "
                f"src/commands/ or experiments/sarol-2024/commands/ in {self.working_checkout}"
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

        # The command this Runner dispatches has to exist before we spend anything looking for it.
        command_error = self.missing_command_error()
        if command_error is not None:
            return artifacts("infra_error", code="NESTED_COMMAND_MISSING", message=command_error)

        try:
            claims = load_batch(inputs.input_ref)
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            return artifacts("infra_error", code="BATCH_UNREADABLE", message=str(exc)[:300])

        out_root = self.output_root or (materialized_path.parent / f"runs-{inputs.batch_id}")
        out_dir = pathlib.Path(out_root) / inputs.split
        out_dir.mkdir(parents=True, exist_ok=True)

        # Validate against the rubric the program ACTUALLY RAN UNDER -- the materialized copy, not
        # the repo's working tree, which the optimizer may already have edited past this version.
        rubric_path = materialized_path / "experiments/sarol-2024/specs/verdict_schema_sarol.md"
        rollup_order = validate_sarol.load_rollup_order(rubric_path)

        # Per-call, closed over by `process` below -- deliberately NOT instance state: the
        # engine calls this Runner three times per iteration and a counter on `self` would
        # carry across those calls.
        counter = {"cost": 0.0, "subs": 0}

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
                cmd = self._stage_command(stage, claim, materialized_path)
                res = self.invoke(cmd, self.working_checkout, self.per_call_timeout_seconds)
                counter["subs"] += 1
                counter["cost"] += res.cost_usd
                record["stages"][stage] = {
                    "exit_code": res.exit_code,
                    "cost_usd": res.cost_usd,
                    "duration_seconds": res.duration_seconds,
                    "timed_out": res.timed_out,
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
            )
            record["validation"] = validation.as_dict()
            if not validation.ok:
                record["status"] = "program_error"
            return record

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
                    n=counter["subs"],
                    cost=counter["cost"],
                )

        results: list[dict[str, Any]] = [process(c) for c in claims]
        timed_out = any(r["status"] == "timeout" for r in results)
        errored = any(r["status"] == "program_error" for r in results)
        total_cost = counter["cost"]
        sub_invocations = counter["subs"]

        # Roll the validator's own invalid-label counts up to the batch. The Scorer merges these
        # rather than re-deriving them, because `parse_verdict` only ever sees the OVERALL label:
        # an invalid SUB-CLAIM verdict under a valid overall verdict would otherwise score clean
        # and disappear from error_class_counts entirely.
        validator_counts: dict[str, int] = {}
        for record in results:
            for key, n in ((record.get("validation") or {}).get("error_class_counts") or {}).items():
                validator_counts[key] = validator_counts.get(key, 0) + n

        manifest_path = out_dir / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "batch_id": inputs.batch_id,
                    "split": inputs.split,
                    # C6.5: macro-F1 under two profiles measures two different systems, and the
                    # engine's frontier is a bare scalar that cannot tell them apart. Stamping the
                    # profile here is the consumer-side half of keeping them distinguishable.
                    "profile": self.profile.name,
                    "profile_stages": list(self.profile.stages),
                    "retrieval_k": self.profile.retrieval_k,
                    # The Scorer's coverage assertion compares against what was actually ASKED of
                    # the Runner, not against however many records came back.
                    "requested_count": len(claims),
                    "claims": results,
                    "validator_error_class_counts": validator_counts,
                    "canary": canary_record,
                    "sub_invocation_count": sub_invocations,
                    "cost_usd": total_cost,
                },
                indent=2,
            ),
            encoding="utf-8",
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
    ) -> None:
        self._gold_resolver = gold_resolver

    def _resolve(self, staging_dir: pathlib.Path) -> dict[str, Any]:
        if self._gold_resolver is not None:
            return self._gold_resolver(staging_dir)
        import parse_verdict  # noqa: PLC0415 -- imported late; it reads gold

        return parse_verdict.parse(staging_dir)

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
                name="sarol_3way_macro_f1", value=metric_value, higher_is_better=True
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
        for record in run_manifest["claims"]:
            if record.get("status") != "ok":
                continue
            try:
                resolved = self._resolve(pathlib.Path(record["staging_dir"]))
            except (OSError, KeyError, RuntimeError):
                unresolved += 1
                continue
            pairs.append((resolved["pred_label"], resolved["gold_label"]))

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
        }
        if not complete:
            breakdown["reason"] = (
                f"coverage: scored {scored['n_total']} of {requested} requested"
                f"{f', {unresolved} unresolved' if unresolved else ''}"
            )
            return result(0.0, breakdown)

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
_VAL_BREAKDOWN_ALLOWED = (
    "scored", "reason", "n_total", "n_invalid", "requested_count", "split",
)


class SarolReleaseBuilder:
    """Builds the per-iteration release. Aggregates only, and for VAL, not even all of those."""

    def __init__(self, *, optimizer_isolation_hash: str = "sarol-2024") -> None:
        self.optimizer_isolation_hash = optimizer_isolation_hash

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

    # -- manifest / edit scope --------------------------------------------------------------
    contracts = store.contract_paths()
    editable = store.editable_paths()
    checks += [
        ("manifest has 8 entries", len(store.entries) == 8),
        ("three of them are contract files", len(contracts) == 3),
        ("the enum contract is one of them",
         "experiments/sarol-2024/specs/verdict_enum_sarol.md" in contracts),
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
        ("retrieval narrows the scope to the judge and its rubric",
         set(store.editable_paths("retrieval")) == {
             "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md",
             "experiments/sarol-2024/specs/verdict_schema_sarol.md"}),
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
    pinned_ok = SarolRunner(store, paperclip_version_probe=lambda: "paperclip, version 0.5.11")
    pinned_bad = SarolRunner(store, paperclip_version_probe=lambda: "paperclip, version 0.5.10")
    pinned_absent = SarolRunner(store, paperclip_version_probe=lambda: None)
    checks += [
        ("the pinned paperclip version passes preflight", pinned_ok.paperclip_pin_error() is None),
        ("a wrong version is caught", pinned_bad.paperclip_pin_error() is not None),
        ("a missing CLI is caught", pinned_absent.paperclip_pin_error() is not None),
        ("a cosmetic banner change is not a spurious mismatch",
         SarolRunner(store, paperclip_version_probe=lambda: "0.5.11").paperclip_pin_error() is None),
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
            ("manifest builds against the engine's ManifestEntry", len(manifest.entries) == 8),
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
                "claims": [
                    {"claim_id": "C1", "citekey": "k1", "staging_dir": tmp, "status": "ok"},
                    {"claim_id": "C2", "citekey": "k2", "staging_dir": tmp, "status": "ok"},
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
                ("the frontier scalar is 3-way macro-F1",
                 score.primary_metric.name == "sarol_3way_macro_f1"),
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
            rb = SarolReleaseBuilder()
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
            ]

        # Runner: the pin negative control fires before any claim is dispatched.
        dispatched: list[str] = []

        def spy(cmd, cwd, timeout):
            dispatched.append(" ".join(cmd))
            return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

        bad_runner = SarolRunner(
            store, invoke=spy, paperclip_version_probe=lambda: "paperclip, version 0.0.1"
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
        ok_pin = lambda: "paperclip, version 0.5.11"  # noqa: E731
        with tempfile.TemporaryDirectory() as empty_checkout:
            missing_cmd = SarolRunner(
                store,
                working_checkout=pathlib.Path(empty_checkout),
                invoke=spy,
                paperclip_version_probe=ok_pin,
            )
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
        # session can actually resolve it. `command_path()` also accepts src/commands/ and
        # experiments/sarol-2024/commands/, but Claude Code only discovers .claude/commands/ from
        # the session cwd -- so a copy in either of the other two would satisfy this preflight and
        # still fail at dispatch. Pin the location that works.
        shipped = SarolRunner(store, paperclip_version_probe=ok_pin).command_path()
        checks += [
            ("the repo ships /sarol-eval-item", shipped is not None),
            ("...in .claude/commands/, the only place a nested session resolves it",
             shipped is not None
             and shipped.parent == REPO_ROOT / ".claude" / "commands"),
        ]

        # The hard per-call spend cap has to be in the command vector, not just in a docstring.
        cmd_vector = SarolRunner(
            store, per_call_max_budget_usd=1.25, require_command=False
        )._stage_command(
            "adjudicator",
            ClaimRecord(claim_id="C1", citekey="k", staging_dir=pathlib.Path("/tmp/s")),
            pathlib.Path("/tmp/mat"),
        )
        checks += [
            ("the nested command carries a hard --max-budget-usd",
             "--max-budget-usd" in cmd_vector),
            ("...with the configured value",
             cmd_vector[cmd_vector.index("--max-budget-usd") + 1] == "1.25"),
            ("...alongside the timeout, which alone would not bound spend",
             "--max-budget-usd" in cmd_vector and "-p" in cmd_vector),
        ]

        # Runner: a timeout surfaces as status="timeout", never as an exception.
        with tempfile.TemporaryDirectory() as tmp:
            batch = pathlib.Path(tmp) / "batch.json"
            staging = pathlib.Path(tmp) / "staging"
            staging.mkdir()
            # A minimally staged claim, in `stage_claim.py`'s own shape, so the mechanical
            # evidence producer has something real to retrieve over under the retrieval profile.
            (staging / "staging_info.json").write_text(json.dumps({
                "citekey": "k1",
                "claim_text_normalized": "deep learning reconstruction accelerates MRI fourfold",
                "source_mode": "corpus",
                "multi_cit_context": "single",
                "source_description": "corpus-chunks (N=3)",
            }), encoding="utf-8")
            handle = staging / "pdfs" / "k1"
            handle.mkdir(parents=True)
            (handle / "content.txt").write_text(
                "L1 [p?]: a fourfold acceleration was achieved for MRI reconstruction\n"
                "L2 [p?]: unrelated sentence about cardiology cohorts\n"
                "L3 [p?]: deep learning methods were applied throughout\n",
                encoding="utf-8",
            )
            batch.write_text(json.dumps({"claims": [
                {"claim_id": "C1", "citekey": "k1", "staging_dir": str(staging)}
            ]}), encoding="utf-8")

            def timeout_invoke(cmd, cwd, t):
                return InvocationResult(
                    exit_code=124, cost_usd=0.0, duration_seconds=t, timed_out=True
                )

            r = SarolRunner(
                store,
                invoke=timeout_invoke,
                output_root=pathlib.Path(tmp) / "out",
                paperclip_version_probe=lambda: "paperclip, version 0.5.11",
                require_command=False,
            )
            res = r.run(
                pathlib.Path(tmp),
                schemas.RunInputs(input_ref=str(batch), batch_id="b", split="train"),
            )
            checks += [
                ("a hung session surfaces as status=timeout, not an exception",
                 res.status == "timeout"),
                ("the engine checks this status on only 1 of its 3 calls, so we report it",
                 res.sub_invocation_count == 1),
            ]

            # The round-trip canary: a moved instrument stops the run before any scored claim.
            canary_claim = ClaimRecord(
                claim_id="CANARY", citekey="canary", staging_dir=staging
            )
            dispatched_claims: list[str] = []

            def canary_invoke(cmd, cwd, t):
                joined = " ".join(cmd)
                for token in joined.split():
                    if token.startswith("--claim"):
                        pass
                dispatched_claims.append(
                    joined.split("--claim ")[1].split()[0] if "--claim " in joined else "?"
                )
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            # No verdict file exists, so validation fails -> the canary cannot match -> stop.
            canary_runner = SarolRunner(
                store,
                invoke=canary_invoke,
                output_root=pathlib.Path(tmp) / "out2",
                paperclip_version_probe=lambda: "paperclip, version 0.5.11",
                require_command=False,
                canary=CanarySpec(claim=canary_claim, expected_verdict="ACCURATE"),
            )
            canary_res = canary_runner.run(
                pathlib.Path(tmp),
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
            stages_seen: list[str] = []

            def stage_spy(cmd, cwd, t_):
                joined = " ".join(cmd)
                stages_seen.append(joined.split("--stage ")[1].split()[0])
                return InvocationResult(exit_code=0, cost_usd=0.0, duration_seconds=0.1)

            def run_under(profile_name):
                stages_seen.clear()
                runner = SarolRunner(
                    store,
                    invoke=stage_spy,
                    output_root=pathlib.Path(tmp) / f"out-{profile_name}",
                    paperclip_version_probe=lambda: "paperclip, version 0.5.11",
                    require_command=False,
                    profile=profile_name,
                )
                res_ = runner.run(
                    pathlib.Path(tmp),
                    schemas.RunInputs(input_ref=str(batch), batch_id="b", split="train"),
                )
                return list(stages_seen), res_

            retr_stages, retr_res = run_under("retrieval")
            agentic_stages, _ = run_under("agentic")
            retr_manifest = json.loads(
                pathlib.Path(retr_res.artifact_refs[0].path).read_text(encoding="utf-8")
            )
            checks += [
                ("under retrieval the Runner dispatches the adjudicator alone",
                 set(retr_stages) == {"adjudicator"}),
                ("...one session per claim, not three",
                 len(retr_stages) == 1 and len(agentic_stages) == 3),
                ("...and agentic still runs all three, in order",
                 agentic_stages == list(profiles_mod.ALL_STAGES)),
                # C6.5: the frontier is a bare scalar, so the profile has to be recoverable from
                # the artifacts or two different experiments become indistinguishable after the
                # fact.
                ("the run manifest records which profile produced it",
                 retr_manifest["profile"] == "retrieval"),
                ("...with the retrieval budget, without which the number is unreportable",
                 retr_manifest["retrieval_k"] == 20),
                ("...and the stages it actually ran",
                 retr_manifest["profile_stages"] == ["adjudicator"]),
            ]
    else:
        checks.append((f"engine not found at {engine_path()} -- engine-facing checks SKIPPED", True))

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
