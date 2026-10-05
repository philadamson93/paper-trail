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
import sarol_isolation as isolation_mod  # noqa: E402
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
        sys.path.append(str(path))
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
            if entry.get("pattern"):
                continue  # a folder pattern (PT14) has no bytes of its own to compare
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

    def tree_differs_from(self, tag: str) -> list[str]:
        """The program files on disk that differ from the COMMITTED tree ``tag`` names: edited,
        deleted, or new and untracked under a folder pattern. Empty when they match.

        S26 for a start tag other than the manifest's own (PT-B). Versions the engine mints have no
        frozen hashes to re-hash, but each is a commit, so the question becomes "is the tree that
        commit's program?". A tag that does not resolve is reported as the one difference.
        """
        root = str(self.repo_root)
        ref = f"{tag}^{{commit}}"
        if subprocess.run(["git", "-C", root, "rev-parse", "--verify", "--quiet", ref], capture_output=True).returncode:
            return [f"<{tag} does not resolve to a commit>"]
        specs = [e["path"] for e in self.entries]
        changed = subprocess.run(["git", "-C", root, "diff", "--name-only", ref, "--", *specs],
                                 capture_output=True, text=True, check=True).stdout.split()
        new = subprocess.run(["git", "-C", root, "ls-files", "--others", "--exclude-standard", "--", *specs],
                             capture_output=True, text=True, check=True).stdout.split()
        return sorted(set(changed) | set(new))

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
        return self._rehash([e for e in self.entries if not e.get("pattern")], tree_root)


# =================================================================================================
# Runner — nested dispatch, with the preflight and the bounds the engine does not provide
# =================================================================================================


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

#: The prediction recorded for a call that crashed or timed out (plan PR). Not in the 9-class enum, so
#: it can never match gold; distinct from INVALID_OUTPUT so a reader can tell "the judge answered
#: badly" from "the call never answered".
FAILED_CALL_LABEL = "FAILED_CALL"

#: The frontier metric's name. One definition, shared by the scorer's output, the release payload
#: and the gate that checks the optimizer's prompt names the objective the adapter reports -- so
#: a rename cannot leave the prompt describing a metric nothing computes.
#:
#: Renamed 2026-09-07 from `sarol_macro_f1_6class`, which was wrong twice over by the end: the
#: objective had stopped being six-class (the "6" was an artifact of the pool-filter bug) and then
#: stopped being macro-F1 at all. It is overall accuracy over the nine emittable labels.
PRIMARY_METRIC_NAME = "sarol_accuracy_9class"


#: Judge transcripts: the engine runner writes each call's session events to its pass folder and
#: records the path in the call's receipt; the manifest's ``trace_ref`` points there (PT-A). The host
#: ``~/.claude/projects`` lookup (``find_transcript``, deleted 2026-09-18) must not come back: a
#: contained session writes that folder inside its own ``--rm`` container.


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
    store: "SarolProgramStore", dest: pathlib.Path, *, tag: str | None = None
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
        ["git", "-C", str(store.repo_root), "rev-parse", f"{tag or store.program_version}^{{commit}}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    dest = pathlib.Path(dest)
    materialize(manifest, sha, repo_root=store.repo_root, dest=dest)
    return dest


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
COMMAND_REL_TEMPLATE = "src/commands/{name}.md"


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


# The Markdown-delimiter blanking that used to live here (`_unmarked`, found by mutation 2026-09-18)
# moved into the engine's `host_path_leak` (S1, umbrella A9/PT15), so a path written as `/host/path`
# inside backticks is read as a path there, for every consumer.


def _raises_valueerror(fn) -> bool:
    """Did ``fn`` refuse with a ``ValueError``? Used for the constructor's refusal controls."""
    try:
        fn()
    except ValueError:
        return True
    except Exception:
        return False
    return False


# The grader Runner (`SarolRunner`) was removed by PT-A on 2026-10-01. The graders run through the
# engine's `ProgramRunner`; paper-trail's half of it (calls, staging, prompt, canary, manifest) is
# `sarol_program.py`.


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
            # THE answer key, the same resolver `parse_verdict.parse` uses. `gold_paper_label` alone
            # turns an empty-evidence ETIQUETTE or IRRELEVANT claim into ACCURATE, so a claim whose
            # verdict was unreadable used to be filed under the wrong class in the per-class
            # breakdown (PT-L's implementation review, 2026-09-30; fixed in PT-A).
            return parse_verdict.canonical_gold_label(
                split=gold["split"],
                claim_row_id=gold["claim_row_id"],
                cited_paper_bucket=gold["cited_paper_bucket"],
                evidence_for_bucket=gold["gold_evidence"],
            )
        except (OSError, KeyError, RuntimeError, json.JSONDecodeError):
            return None

    def _resolve(self, staging_dir: pathlib.Path) -> dict[str, Any]:
        if self._gold_resolver is not None:
            return self._gold_resolver(staging_dir)
        import parse_verdict  # noqa: PLC0415 -- imported late; it reads gold

        return parse_verdict.parse(staging_dir)

    def _write_mistakes(self, split, batch_id, joined, run_manifest_ref: str | None = None) -> str | None:
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
                    # The pass's run manifest, for the correct-answer traces this corpus does not
                    # list. The optimizer's feedback copy brings it in with paths rewritten (D6).
                    "run_manifest_ref": run_manifest_ref,
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
            #
            # ⚠ **Carry the error CODE, not just the status** (2026-09-19). This used to report
            # `run status='infra_error'` and nothing else, while this path distinguishes at least
            # eight codes (PAPERCLIP_PIN_MISMATCH, NESTED_COMMAND_MISSING, BATCH_UNREADABLE,
            # DUPLICATE_CLAIM_IDS, the canary miss, the budget refusal, ...). A run that dies here
            # writes no run manifest and no traces, so the release payload is the ONLY thing the
            # optimizer -- or a person -- gets to see. Twice in one afternoon a run stopped and
            # diagnosing it meant reading the source to enumerate what could have returned that
            # status. The optimizer session reached the same conclusion unprompted and wrote it
            # into the sheet: "a failed run is currently undiagnosable from the optimizer's side."
            #
            # `status` stays first in the string so anything already matching on it keeps working.
            err = getattr(artifacts, "error", None)
            reason = f"run status={artifacts.status!r}"
            if err is not None and getattr(err, "code", None):
                reason += f" code={err.code!r}"
                if getattr(err, "message", None):
                    reason += f" message={str(err.message)[:300]!r}"
            elif artifacts.status == "ok":
                # Status says fine but nothing came back: distinct from a failure, and previously
                # indistinguishable from one because both printed the status alone.
                reason += " (no artifact_refs -- the batch produced no run manifest)"
            return result(
                0.0,
                {
                    "scored": False,
                    "reason": reason,
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
        failed_calls = {"count": 0, "by_reason": {"crash": 0, "timeout": 0}}
        for record in run_manifest["claims"]:
            # A call that crashed or timed out is a MISS, clearly marked (Phil 2026-09-25; plan PR):
            # scored against gold under a sentinel that is not in the 9-class enum, and counted in
            # `failed_calls` so the optimizer is told those calls failed, not that it answered wrong.
            # Before PT-A a single failed call made the whole batch unscoreable.
            if record.get("status") == "failed":
                gold_only = self._resolve_gold_only(pathlib.Path(record["staging_dir"]))
                # A gold label equal to the sentinel would score a failed call as correct; such a
                # resolver is broken, so the claim is unresolved (the batch is then unscored).
                if gold_only is None or gold_only == FAILED_CALL_LABEL:
                    unresolved += 1
                    continue
                pairs.append((FAILED_CALL_LABEL, gold_only))
                failed_calls["count"] += 1
                why = record.get("failed")
                if why in failed_calls["by_reason"]:
                    failed_calls["by_reason"][why] += 1
                continue
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
            "failed_calls": failed_calls,
        }
        if not complete:
            breakdown["reason"] = (
                f"coverage: scored {scored['n_total']} of {requested} requested"
                f"{f', {unresolved} unresolved' if unresolved else ''}"
            )
            return result(0.0, breakdown)

        mistakes_ref = self._write_mistakes(split, run_manifest.get("batch_id", "batch"), joined,
                                            run_manifest_ref=str(artifacts.artifact_refs[0].path))
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
    # How many calls crashed or timed out (plan PR). A bare count by reason, like `n_invalid`: it
    # says the instrument failed on that many calls, never which held-out claims they were.
    "failed_calls",
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

    def __init__(self, *, setup_value: str) -> None:
        """Stamps every payload with the run's setup value (S2's ``combined_value``).

        Since PT-A (2026-10-01) this is what the run's two session kinds compute from their
        descriptions, not a pin read from the manifest: each sealed session is held to its committed
        pin when it starts (the real gate), and the loop is given this same value to check the stamp
        (``run_loop(expected_isolation_hash=...)``), which catches a builder stamping a placeholder.
        """
        if not isinstance(setup_value, str) or not setup_value.startswith("setup-v"):
            raise ValueError(f"refusing to build releases with no computed setup value (got {setup_value!r})")
        self.optimizer_isolation_hash = setup_value

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

    # -- manifest / edit scope --------------------------------------------------------------
    contracts = store.contract_paths()
    editable = store.editable_paths()
    checks += [
        ("manifest has 12 entries: 10 files and the two folder patterns (PT14)",
         len(store.entries) == 12 and sum(1 for e in store.entries if e.get("pattern")) == 2),
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
        ("retrieval narrows the scope to the judge, its rubric, the driver, and the two folder patterns",
         set(store.editable_paths("retrieval")) >= {
             "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md",
             "experiments/sarol-2024/specs/verdict_schema_sarol.md",
             "src/commands/sarol-eval-item.md"}
         and set(store.editable_paths("retrieval")) <= {
             "experiments/sarol-2024/prompts/adjudicator-dispatch-sarol.md",
             "experiments/sarol-2024/specs/verdict_schema_sarol.md",
             "src/commands/sarol-eval-item.md",
             "experiments/sarol-2024/prompts/*.md", "experiments/sarol-2024/specs/*.md"}),
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
            if entry.get("pattern"):
                continue  # a folder pattern (PT14) is not a file
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

    # -- profiles: which ones depend on the paperclip CLI -----------------------------------------
    # The paperclip pin gate went with the old Runner (PT-A, 2026-10-01): every profile that runs the
    # CLI has stages beyond the adjudicator, which the engine-runner path refuses (`sarol_program`),
    # and paperclip itself is deferred (umbrella PT12). This declaration is what that gate keyed on,
    # and what it will key on again when paperclip is revisited.
    checks += [
        # The VM preflight compares the installed paperclip CLI to the pin through these two.
        ("paperclip version banners normalise to the bare version, so a cosmetic change is no mismatch",
         _normalize_version("paperclip, version 0.7.48") == "0.7.48" and _normalize_version(None) is None
         and installed_paperclip_version(lambda c: subprocess.CompletedProcess(c, 1, "", "")) is None),
        ("a profile that runs no CLI declares it has no CLI dependency, and paperclip declares one",
         profiles_mod.get("retrieval").requires_paperclip_cli is False
         and profiles_mod.get("paperclip").requires_paperclip_cli is True),
    ]

    # -- engine-facing shapes ----------------------------------------------------------------
    engine_ok = (engine_path() / "engine" / "schemas.py").exists()
    if engine_ok:
        schemas = _import_engine()
        manifest = store.manifest()
        checks += [
            ("manifest builds against the engine's ManifestEntry", len(manifest.entries) == 12),
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
                ("...shaped as the C6.8 wrapper: counts, the per-claim list, and the pass's run manifest",
                 set(corpus_file) == {"batch_id", "split", "n_scored",
                                      "n_correct", "n_mistakes", "claims", "run_manifest_ref"}),
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
            rb = SarolReleaseBuilder(setup_value="setup-v1:selftest")
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
