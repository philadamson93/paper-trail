#!/usr/bin/env bash
# Standalone runner for the Sarol hill-climb on a VM with no Claude Code session present.
#
# Per docs/claude_ops.md: no agent is there to interpret an ambiguous result, so this script
# asserts its own preconditions and exits non-zero rather than starting a run that cannot finish.
# Copy-paste onto the box and invoke directly. Idempotent: safe to re-run after a failed check.
#
#   ./run_hillclimb_vm.sh [RUN_ID] [MAX_WORKERS] [ITERATIONS]
#
# Defaults: RUN_ID=hillclimb-$(date +%F), MAX_WORKERS=4, ITERATIONS=5.

set -euo pipefail

RUN_ID="${1:-hillclimb-$(date +%F)}"
MAX_WORKERS="${2:-4}"
ITERATIONS="${3:-5}"
# One profile for the whole script. The paperclip-pin preflight, the canary staging and the run
# itself all read this, so they cannot disagree about what is being run -- `retrieval` is the only
# runnable rung today (`profiles.IMPLEMENTED_STAGES`).
PROFILE="${PROFILE:-retrieval}"

# Deterministic interpreter: name the exact executable rather than trusting whatever `python3`
# resolves to on a fresh box (the engine + optimizer are pinned to 3.13). Override with
# PAPER_TRAIL_PYTHON if this box installs it elsewhere.
PY="${PAPER_TRAIL_PYTHON:-$HOME/.local/bin/python3.13}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OPT="$REPO_ROOT/experiments/sarol-2024/optimizer"
DATA_TGZ_BUCKET="gs://su-vista-uscentral1/chaudhari_lab/phil/paper-trail-data/sarol-data.tgz"
RUNS="$HOME/.paper-trail/runs/$RUN_ID"

say()  { printf '\n=== %s\n' "$*"; }
fail() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preconditions
say "Preconditions"

[ -x "$PY" ] || fail "interpreter not found/executable at $PY (set PAPER_TRAIL_PYTHON to the right python3.13)"
# Verify it can actually run the code, not just report a version tuple: a 3.13 that can't import
# the engine (wrong AGENTIC_LABEL_OPT, half-installed deps) fails just as hard as a 3.9.
"$PY" - <<'PYCHK' || fail "python >= 3.11 required at $PY (the code uses X | Y unions and match-era syntax)"
import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PYCHK
echo "  python:  $("$PY" -V) ($PY)"

# The engine seam must resolve to an agentic-label-opt checkout that carries the mid-run
# failure-handling hardening (LoopStop.reason + EmptyCommitError). A run against a pre-hardening
# engine would abort on a bad probe with a bare traceback and lose the partial-run summary -- the
# exact failure this runner exists to prevent. Contract-checked (feature presence), not SHA-pinned,
# so it survives an engine re-pin.
: "${AGENTIC_LABEL_OPT:?STOP: AGENTIC_LABEL_OPT must point at the agentic-label-opt engine checkout (its DEFAULT_ENGINE is a Mac-only path)}"
[ -d "$AGENTIC_LABEL_OPT" ] || fail "AGENTIC_LABEL_OPT=$AGENTIC_LABEL_OPT is not a directory"
# ⚠ **The engine version check moved to `optimizer/engine_pin.py` on 2026-09-18.** It used to live
# only here, which meant this runner was the one entry point that checked -- `adapter`, `dispatcher`,
# `canary`, `sampling`, `run_baseline` and `materialize_smoke` all imported whatever happened to be
# sitting in that directory. The module carries the pin, the ancestry test, the capability probe
# (including the LoopStop.reason / EmptyCommitError checks that used to be the heredoc below) and
# the same SAROL_ALLOW_ENGINE_DIVERGENCE=1 override this script has always documented.
#
# Keeping the SHA in one place is the point: the pin here went 28 commits stale, and because the
# test is ancestry, it kept passing against engines missing everything the isolation work needs.
PIN_MODULE="$REPO_ROOT/experiments/sarol-2024/optimizer/engine_pin.py"
[ -f "$PIN_MODULE" ] || fail "the engine pin module is missing at $PIN_MODULE"
if ENGINE_REPORT="$("$PY" "$PIN_MODULE" 2>&1)"; then
  printf '%s\n' "$ENGINE_REPORT" | sed 's/^/  /'
elif [ "${SAROL_ALLOW_ENGINE_DIVERGENCE:-0}" = "1" ]; then
  printf '%s\n' "$ENGINE_REPORT" | sed 's/^/  /'
  echo "  engine:  ^^ ENGINE PIN CHECK OVERRIDDEN -- proceeding against a non-conforming engine"
else
  printf '%s\n' "$ENGINE_REPORT" >&2
  fail "the engine checkout does not satisfy the pin (diagnosis above). Check out a commit containing it, or set SAROL_ALLOW_ENGINE_DIVERGENCE=1 if the divergence is intended."
fi

# Program-integrity gates. These run BEFORE any money is spent, and they fail closed.
#
# The optimizer edits `verdict_schema_sarol.md` every iteration and the eight class definitions live
# in that same file. Nothing in the engine, the manifest, or the selftests can tell a reworded
# definition from a sharpened boundary test -- `validate_against_manifest` and the freeze both pass
# either way. These two scripts are the ONLY barrier between the loop and the paper-verbatim reset it
# was given, so a run that skips them can silently undo it and score the result as progress.
"$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_paper_fidelity.py" \
  || fail "GATE A FAILED: the Sarol class definitions no longer match the paper verbatim, or a retired divergent clause is back. Fix the definitions before spending money on a sweep -- see experiments/sarol-2024/specs/verdict_definitions_sarol.md for the reconciled text."
"$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_empty_window_regression.py" \
  || fail "GATE D FAILED: the empty-window contract regressed. An empty BM25 window must still emit \"evidence\": [] or the exit validator rejects the whole file and the claim scores as a miss regardless of verdict."
# Gate F guards the layer Gates A and D do not: the DRIVER's read path. The optimizer may now edit
# the driver itself, and the prompt files it dispatches carry `## Orchestrator notes` addressed to
# that same session -- so a note telling it to validate or retry silently overrides the driver's
# contract, which is how the 2026-09-10 defect happened and survived five review passes.
"$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_orchestrator_consistency.py" \
  || fail "GATE F FAILED: orchestrator-facing prose contradicts a driver hard prohibition, or a deferred contradiction just became live because its stage was implemented. The dispatching session reads both files -- fix the prose before spending money on a sweep."
# Gate G keeps our development history out of the files an agent re-reads every run. A note about
# what a prompt used to say is context the agent pays for and cannot use -- and a superseded
# instruction restated verbatim stays actionable to a model skimming for what to do.
"$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_prompt_hygiene.py" \
  || fail "GATE G FAILED: an agent-read prompt carries development history (what it used to say, or a dated edit). State the rule as it stands -- the history belongs in git and docs/."
# Phase 4, the run-start reset. `meta-learnings.md` is injected into every optimizer session, the
# per-iteration findings are read the same way, and `iter/<n>/` is keyed by iteration number rather
# than by run -- so run N+1 writes over run N's releases. A run that inherits any of the three opens
# with hypotheses it did not earn, measured against a program that may no longer exist.
#
# ⚠ **This archives first and then asserts, rather than refusing and waiting for a human.** Nobody
# is watching a VM run, so a gate whose only outcome is "stop and ask someone to run the archive
# command" costs the whole run. Archiving is a MOVE, never a delete: everything lands under
# ~/.paper-trail/runs/_archive/<timestamp>-<run id>/ and the assertion below then proves the tree is
# actually clean. The reset is idempotent, so a resumed run either finds the archive it made or
# makes one.
#
# The continuation escape hatch still wins: with SAROL_ALLOW_INHERITED_LESSONS=1 nothing is moved
# and the gate passes carrying the state, loudly.
if [ "${SAROL_ALLOW_INHERITED_LESSONS:-}" = "1" ]; then
  say "  reset:   SKIPPED -- SAROL_ALLOW_INHERITED_LESSONS=1, this is a CONTINUATION run"
else
  "$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_run_scope.py" --archive "$RUN_ID" \
    || fail "RESET FAILED: could not archive the previous run's lessons, findings or releases. Nothing has been dispatched."
fi
# ...and now assert it worked. A reset with no assertion after it is an inert mechanism -- this is
# the half that fails if the archive silently moved nothing.
"$PY" "$REPO_ROOT/experiments/sarol-2024/scripts/check_run_scope.py" \
  || fail "GATE H FAILED AFTER THE RESET: this checkout still holds a previous run's lessons, findings or releases. The archive step above did not clear them -- do not treat this run's numbers as a fresh run's."
echo "  gates:   paper-fidelity OK, empty-window OK, orchestrator-consistency OK, prompt-hygiene OK, run-scope OK"

command -v paperclip >/dev/null || fail "paperclip not on PATH -- the Runner asserts the manifest paperclip pin before any dispatch"
echo "  paperclip: $(paperclip --version 2>&1 | head -1)"
# ...and now actually COMPARE it to the pin, which is what the Runner asserts. Checking only that
# the binary exists is a check that looks like it covers the pin and does not: on 2026-09-19 a box
# with 0.5.11 against a 0.7.48 pin sailed through this preflight, reached the first dispatch, and
# got `infra_error`/PAPERCLIP_PIN_MISMATCH there. The loop then handed the optimizer a payload
# saying nothing was scored, the optimizer correctly changed nothing, and the run stopped -- about
# $2 and a session to learn what this line answers for free. The error code never surfaced in the
# log either, so diagnosing it meant reading the source.
#
# Reuses the adapter's OWN probe and normalizer rather than re-implementing the comparison, so the
# preflight and the runtime gate cannot drift into disagreeing about what matches.
PIN_REPORT="$(cd "$OPT" && PYTHONPATH="$AGENTIC_LABEL_OPT" PROFILE="$PROFILE" "$PY" -c '
import json, os, pathlib, sys, adapter, profiles
if not profiles.get(os.environ["PROFILE"]).requires_paperclip_cli:
    print("not asserted -- this profile does not invoke the CLI")
    sys.exit(0)
pinned = json.loads(pathlib.Path("../program-v0/manifest.json").read_text())["runtime_pins"].get("paperclip_cli")
if not pinned:
    print("no pin recorded")
    sys.exit(0)
want, got = adapter._normalize_version(pinned), adapter._normalize_version(adapter.installed_paperclip_version())
if want != got:
    print(f"pinned {want!r}, installed {got!r}")
    sys.exit(1)
print("matches the manifest")
' 2>&1)" || fail "GATE: paperclip does not match the manifest pin -- $PIN_REPORT. The Runner refuses at the first dispatch with PAPERCLIP_PIN_MISMATCH, so this stops here rather than after a paid optimizer session. Install the pinned version, or re-pin deliberately (that changes combined_hash and the program identity)."
echo "  paperclip pin: $PIN_REPORT"

# Load the container credential from a file, so a run does not need a secret typed on its command
# line (where it lands in shell history and in `ps`). The file lives under ~/.paper-trail/ -- beside
# the gold and the runs, deliberately OUTSIDE any checkout, so no gitignore rule stands between it
# and a commit. Override with PAPER_TRAIL_CREDENTIALS.
#
# Format is one `NAME=value` per line. Only names in `isolation.ENV_ALLOWLIST` are read, and the
# file is never sourced -- sourcing would execute whatever is in it, and this is a secrets file, not
# a script. An already-set variable in the environment wins, so a one-off override still works.
#
# Mint the token with `claude setup-token` (subscription-backed OAuth, one year; NOT an API key --
# `ANTHROPIC_API_KEY` would outrank it and bill per token, which is why it is not in the allowlist).
CRED_FILE="${PAPER_TRAIL_CREDENTIALS:-$HOME/.paper-trail/credentials.env}"
if [ -f "$CRED_FILE" ]; then
  # Fail closed on a loose mode: a long-lived credential readable by group or other is a finding,
  # and silently loading it anyway would be this script asserting a safety property it does not have.
  CRED_PERM="$(stat -f '%OLp' "$CRED_FILE" 2>/dev/null || stat -c '%a' "$CRED_FILE" 2>/dev/null || echo unknown)"
  case "$CRED_PERM" in
    600|400) : ;;
    *) fail "$CRED_FILE is mode $CRED_PERM -- a long-lived token must not be readable by group or other. Fix it:  chmod 600 $CRED_FILE" ;;
  esac
  for CRED_NAME in $(cd "$OPT" && PYTHONPATH="$AGENTIC_LABEL_OPT" "$PY" -c 'import isolation; print(" ".join(isolation.ENV_ALLOWLIST))'); do
    CRED_LINE="$(grep -m1 "^${CRED_NAME}=" "$CRED_FILE" 2>/dev/null || true)"
    if [ -n "$CRED_LINE" ] && [ -z "$(eval "printf '%s' \"\${${CRED_NAME}:-}\"")" ]; then
      export "$CRED_NAME=${CRED_LINE#*=}"
    fi
  done
  # Names only, never values.
  echo "  credentials: loaded $CRED_FILE (mode $CRED_PERM)"
fi

# The CONTAINER's credential, which is a different thing from the host `claude` being logged in.
# Every scored dispatch runs `claude` inside the container, and the container is handed exactly the
# variables in `isolation.ENV_ALLOWLIST` BY NAME (`docker run --env VAR`, no value) -- so an unset
# name silently passes nothing and the contained CLI starts unauthenticated. It then exits
# immediately at zero cost, which reads as a canary miss, which returns `infra_error`, which scores
# nothing. On 2026-09-19 that consumed two runs before anyone looked: the preflight above says
# "claude auth: OK" about the HOST and had nothing to say about the container.
#
# Read from the allowlist rather than hardcoding the name, so adding a credential to the boundary
# cannot leave this check behind asserting the old set.
CRED_REPORT="$(cd "$OPT" && PYTHONPATH="$AGENTIC_LABEL_OPT" "$PY" -c '
import os, sys, isolation
missing = [v for v in isolation.ENV_ALLOWLIST if not os.environ.get(v)]
if missing:
    print(", ".join(missing))
    sys.exit(1)
print("all set: " + ", ".join(isolation.ENV_ALLOWLIST))
' 2>&1)" || fail "GATE: the container credential is not set on this host -- $CRED_REPORT. The contained CLI would start unauthenticated and every dispatch would fail at zero cost. Mint one with 'claude setup-token' and pass it on the same line as this script."
echo "  container cred: $CRED_REPORT"

command -v claude >/dev/null || fail "the 'claude' CLI is not installed -- the judge is a nested 'claude -p' session per claim"
echo "  claude:  $(claude --version 2>&1 | head -1)"

# Auth is the failure that costs the most: it surfaces only on the first paid dispatch, after
# staging has run. Force it now, cheaply, with a prompt whose answer we do not care about.
# macOS ships bash 3.2, where expanding an EMPTY array under `set -u` is an "unbound variable"
# error, not an empty expansion. Keeping the command inside the array keeps it non-empty on every
# box, so a host without GNU `timeout` no longer dies here and gets misreported as unauthenticated.
if command -v timeout >/dev/null; then AUTH_PROBE=(timeout 120 claude); else AUTH_PROBE=(claude); fi
# Budget cap only bounds this probe's cost; keep it comfortably above one trivial prompt on the
# default model (a $0.05 cap false-fails an authed CLI — the prompt alone exceeds it).
if ! printf 'say OK' | "${AUTH_PROBE[@]}" -p --max-budget-usd 1.00 >/dev/null 2>&1; then
  fail "the 'claude' CLI is installed but not authenticated (or has no budget). Run 'claude' once interactively on this box first."
fi
echo "  claude auth: OK"

[ -d "$OPT" ] || fail "optimizer not found at $OPT -- is this script inside a paper-trail checkout?"

# ---------------------------------------------------------------- data
say "Benchmark data"
if [ ! -d "$HOME/.paper-trail/gold/sarol-2024" ] || [ ! -d "$HOME/.paper-trail/benchmarks/sarol-2024" ]; then
  echo "  not present locally; fetching from the bucket"
  command -v gcloud >/dev/null || fail "gcloud not on PATH and the data is absent -- cannot fetch $DATA_TGZ_BUCKET"
  mkdir -p "$HOME/.paper-trail"
  # Straight from the bucket, NOT through the NFS mount: per-file latency there makes a
  # 3,800-file untar pathological, and a mount write can silently fail to persist.
  gcloud storage cp "$DATA_TGZ_BUCKET" "$HOME/.paper-trail/sarol-data.tgz" \
    || fail "could not fetch the benchmark tarball"
  tar xzf "$HOME/.paper-trail/sarol-data.tgz" -C "$HOME/.paper-trail"
  rm -f "$HOME/.paper-trail/sarol-data.tgz"
fi
GOLD_N=$(find "$HOME/.paper-trail/gold/sarol-2024" -type f | wc -l | tr -d ' ')
BENCH_N=$(find "$HOME/.paper-trail/benchmarks/sarol-2024" -type f | wc -l | tr -d ' ')
[ "$GOLD_N"  -ge 400  ] || fail "gold looks short: $GOLD_N files (expected ~412)"
[ "$BENCH_N" -ge 3000 ] || fail "benchmarks look short: $BENCH_N files (expected ~3272)"
echo "  gold=$GOLD_N benchmarks=$BENCH_N"

# ---------------------------------------------------------------- instrument
say "Instrument checks (offline, free)"
cd "$OPT"
# evidence_producers was omitted here while contributing 26 checks to the reported total, so the
# preflight under-reported the suite it claims to gate -- and it is the runnable retrieval path.
for m in adapter dispatcher sampling validate_sarol profiles canary evidence_producers; do
  out=$("$PY" "$m.py" --selftest 2>&1 | tail -1)
  case "$out" in *"passed"*) : ;; *) fail "$m selftest did not pass: $out";; esac
  echo "  $m: $out"
done

cd "$REPO_ROOT/experiments/sarol-2024"
"$PY" scripts/freeze_program_v0.py --verify --tree program-v0 >/dev/null 2>&1 \
  || fail "program-v0 does not verify against its tag -- the tree and the tag disagree, so numbers would be filed under the wrong program"
echo "  program-v0 verifies against its tag"

# ---------------------------------------------------------------- container image
# Every scored dispatch runs in a container and there is no uncontained mode, so the dispatcher
# refuses without `--image` given BY DIGEST. This runner predated that refusal and never passed one,
# which made it unable to start a run at all once the isolation work landed -- it got all the way to
# the dispatch and stopped there, after the free gates but before spending anything.
#
# The digest is resolved from the tag the code itself ships (`isolation.SHIPPING_IMAGE_TAG`) rather
# than written out here, so the runner cannot drift from the image the pin is keyed on. A locally
# built image has a digest and Docker will run it by one -- no registry is needed.
say "Container image"
cd "$OPT"
IMAGE_REF="$(PYTHONPATH="$AGENTIC_LABEL_OPT" "$PY" -c 'import isolation, sys; r = isolation.image_digest_ref(); sys.exit(1) if not r else print(r)' 2>/dev/null)" \
  || fail "the isolation image is not built on this box. Build it, then re-run:  docker build -t \$(PYTHONPATH=\"\$AGENTIC_LABEL_OPT\" \"\$PY\" -c 'import isolation; print(isolation.SHIPPING_IMAGE_TAG)') -f \"\$AGENTIC_LABEL_OPT/isolation/Dockerfile\" \"\$AGENTIC_LABEL_OPT/isolation\""
case "$IMAGE_REF" in *@sha256:*) : ;; *) fail "resolved image ref is not a digest: $IMAGE_REF";; esac
echo "  image:   $IMAGE_REF"

# ---------------------------------------------------------------- canary staging
# The canary's runtime staging tree is git-ignored, so it is ABSENT on a fresh clone -- and the
# Runner refuses to dispatch a canary whose staged files are gone. Rebuild it deterministically
# (offline, free: corpus source_mode, no LLM) from the seeded pinned claim, idempotently.
say "Canary staging (offline, free)"
cd "$OPT"
PYTHONPATH="$AGENTIC_LABEL_OPT" PROFILE="$PROFILE" "$PY" - <<'PYCAN' || fail "could not rebuild/verify the canary staging tree -- see the reason it printed"
import os
import sys
import canary
import stage_claim

PROFILE = os.environ.get("PROFILE", "retrieval")
spec = canary.load(PROFILE)
if spec is None:
    print(f"  no pinned canary for {PROFILE!r} -- expected canary/canary-{PROFILE}.json in the checkout")
    raise SystemExit(1)

unit = canary.choose_claim("train")  # seeded draw -> the pinned claim, deterministically
if unit.claim_id != spec.claim.claim_id:
    print(f"  seeded claim {unit.claim_id!r} != pinned {spec.claim.claim_id!r} -- pool/pin drift")
    raise SystemExit(1)

staging = canary.canary_staging_dir(PROFILE) / unit.claim_id
# Rebuild when the staged tree is absent or lacks its manifest (a fresh clone, or a half-write).
# Presence-checked, not counted: the exact file set is stage_claim's business, not this guard's.
if not (staging / "staging_info.json").is_file():
    info = stage_claim.stage(
        split="train",
        claim_row_id=unit.claim_row_id,
        cited_paper_bucket=unit.paper_bucket,
        source_mode=spec.claim.source_mode,
        out_dir=staging,
    )
    if info["citekey"] != spec.claim.citekey:
        print(f"  staged citekey {info['citekey']!r} != pinned {spec.claim.citekey!r}")
        raise SystemExit(1)

n = sum(1 for p in staging.rglob("*") if p.is_file())
if not (staging / "staging_info.json").is_file() or n == 0:
    print(f"  canary staging incomplete at {staging} ({n} files, no staging_info.json)")
    raise SystemExit(1)
print(f"  canary {unit.claim_id} ({spec.claim.citekey}) staged: {n} files under {staging.name}/")
PYCAN

# ---------------------------------------------------------------- run
say "Run: $RUN_ID (workers=$MAX_WORKERS, iterations=$ITERATIONS)"
mkdir -p "$RUNS"
cd "$OPT"
# errexit off across the run itself: we want the post-run assertions to report the failure in
# terms of what is missing, not a bare non-zero from the pipeline.
set +e
"$PY" -u dispatcher.py --run \
  --image "$IMAGE_REF" \
  --profile "$PROFILE" \
  --iterations "$ITERATIONS" \
  --train-n-schedule 50,50,50,50,50 \
  --draw-mode cumulative \
  --val-n 50 \
  --max-workers "$MAX_WORKERS" \
  --run-id "$RUN_ID" \
  --max-budget-usd 1000 \
  --materialize-root "$RUNS/materialized" \
  --train-output-root "$RUNS/train" \
  --val-output-root  "$RUNS/val" \
  2>&1 | tee "$RUNS/run.log" || true
RC=${PIPESTATUS[0]}
set -e

# ---------------------------------------------------------------- assertions
say "Post-run assertions"
[ "$RC" -eq 0 ] || fail "dispatcher exited $RC -- see $RUNS/run.log"

REL="$REPO_ROOT/iter/$ITERATIONS/release_val.json"
[ -s "$REL" ] || fail "no release payload at $REL -- the loop did not reach iteration $ITERATIONS"

"$PY" - "$REL" <<'PYREL' || fail "the final release did not carry a scored metric -- see the reason it printed"
import json, sys, pathlib
d = json.loads(pathlib.Path(sys.argv[1]).read_text())
m = d.get("metrics") or {}
pm = m.get("primary_metric"); pm = pm.get("value") if isinstance(pm, dict) else pm
b = m.get("breakdown") or {}
print(f"  final VAL metric={pm} scored={b.get('scored')} n={b.get('n_total')}/{b.get('requested_count')}")
if not b.get("scored"):
    print(f"  NOT SCORED: {b.get('reason')}"); raise SystemExit(1)
if pm is None or not (0.0 <= float(pm) <= 1.0):
    print(f"  metric out of range: {pm!r}"); raise SystemExit(1)
PYREL

echo
echo "OK: run $RUN_ID completed. Results under $RUNS ; releases under $REPO_ROOT/iter/."
