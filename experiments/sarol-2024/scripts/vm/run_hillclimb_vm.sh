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
PYTHONPATH="$AGENTIC_LABEL_OPT" "$PY" - <<'PYENG' || fail "the engine at AGENTIC_LABEL_OPT lacks the LoopStop-hardening contract -- re-pin to the landed hardening SHA"
import inspect
from engine.loop import LoopStop
from engine.versioning import EmptyCommitError  # noqa: F401  (must exist)
assert "reason" in inspect.signature(LoopStop.__init__).parameters, "LoopStop has no reason kwarg"
raise SystemExit(0)
PYENG
ENG_SHA="$(git -C "$AGENTIC_LABEL_OPT" rev-parse --short HEAD 2>/dev/null || echo '?')"

# Plan A declares 82f547d the compatible engine: the SHA the five-iteration run actually used.
# The feature check above catches an engine that is too OLD, but not one that has DIVERGED -- a
# checkout parked on an unrelated feature branch can carry LoopStop.reason and EmptyCommitError and
# still break the adapter seam. Measured 2026-09-09: a sibling branch crashed dispatcher --selftest
# with `'function' object has no attribute 'batch_id'` while satisfying every feature probe.
#
# So assert ANCESTRY, not equality: 82f547d must be reachable from HEAD. That still permits a
# forward re-pin (the whole point of the contract check above).
#
# Be precise about what this does and does not catch. It detects an engine that PREDATES or FORKED
# BELOW the declared-compatible commit -- the common real failure, e.g. a checkout parked on another
# session's branch. It does NOT catch a branch cut FROM 82f547d that later broke the adapter seam:
# the pin is still an ancestor and this passes cleanly. For that, the feature probe above and the
# dispatcher selftest are the backstop.
# Deliberate override: SAROL_ALLOW_ENGINE_DIVERGENCE=1.
ENGINE_PIN="82f547dac49394005781df62892d41d9b26dfb09"
if [ "${SAROL_ALLOW_ENGINE_DIVERGENCE:-0}" != "1" ]; then
  if ! git -C "$AGENTIC_LABEL_OPT" cat-file -e "$ENGINE_PIN^{commit}" 2>/dev/null; then
    fail "the engine checkout does not contain the declared-compatible commit $ENGINE_PIN at all -- wrong repo, or a shallow clone. Fetch it, or set SAROL_ALLOW_ENGINE_DIVERGENCE=1 to proceed anyway."
  fi
  if ! git -C "$AGENTIC_LABEL_OPT" merge-base --is-ancestor "$ENGINE_PIN" HEAD 2>/dev/null; then
    ENG_BRANCH="$(git -C "$AGENTIC_LABEL_OPT" branch --show-current 2>/dev/null || echo 'detached')"
    fail "engine at $ENG_SHA (branch '$ENG_BRANCH') has DIVERGED from the declared-compatible $ENGINE_PIN, which is not an ancestor of HEAD. This is usually a checkout left on another session's feature branch. Check out a commit containing the pin, or set SAROL_ALLOW_ENGINE_DIVERGENCE=1 if the divergence is intended."
  fi
  echo "  engine:  $AGENTIC_LABEL_OPT @ $ENG_SHA (LoopStop-hardening contract OK; contains pin ${ENGINE_PIN:0:7})"
else
  echo "  engine:  $AGENTIC_LABEL_OPT @ $ENG_SHA (LoopStop-hardening contract OK; ENGINE PIN CHECK OVERRIDDEN)"
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
echo "  gates:   paper-fidelity OK, empty-window OK, orchestrator-consistency OK"

command -v paperclip >/dev/null || fail "paperclip not on PATH -- the Runner asserts the manifest paperclip pin before any dispatch"
echo "  paperclip: $(paperclip --version 2>&1 | head -1)"

command -v claude >/dev/null || fail "the 'claude' CLI is not installed -- the judge is a nested 'claude -p' session per claim"
echo "  claude:  $(claude --version 2>&1 | head -1)"

# Auth is the failure that costs the most: it surfaces only on the first paid dispatch, after
# staging has run. Force it now, cheaply, with a prompt whose answer we do not care about.
if command -v timeout >/dev/null; then AUTH_TIMEOUT=(timeout 120); else AUTH_TIMEOUT=(); fi
# Budget cap only bounds this probe's cost; keep it comfortably above one trivial prompt on the
# default model (a $0.05 cap false-fails an authed CLI — the prompt alone exceeds it).
if ! printf 'say OK' | "${AUTH_TIMEOUT[@]}" claude -p --max-budget-usd 1.00 >/dev/null 2>&1; then
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
for m in adapter dispatcher sampling validate_sarol profiles canary; do
  out=$("$PY" "$m.py" --selftest 2>&1 | tail -1)
  case "$out" in *"passed"*) : ;; *) fail "$m selftest did not pass: $out";; esac
  echo "  $m: $out"
done

cd "$REPO_ROOT/experiments/sarol-2024"
"$PY" scripts/freeze_program_v0.py --verify --tree program-v0 >/dev/null 2>&1 \
  || fail "program-v0 does not verify against its tag -- the tree and the tag disagree, so numbers would be filed under the wrong program"
echo "  program-v0 verifies against its tag"

# ---------------------------------------------------------------- canary staging
# The canary's runtime staging tree is git-ignored, so it is ABSENT on a fresh clone -- and the
# Runner refuses to dispatch a canary whose staged files are gone. Rebuild it deterministically
# (offline, free: corpus source_mode, no LLM) from the seeded pinned claim, idempotently.
say "Canary staging (offline, free)"
cd "$OPT"
PYTHONPATH="$AGENTIC_LABEL_OPT" "$PY" - <<'PYCAN' || fail "could not rebuild/verify the canary staging tree -- see the reason it printed"
import sys
import canary
import stage_claim

PROFILE = "retrieval"
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
  --profile retrieval \
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
