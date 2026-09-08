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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OPT="$REPO_ROOT/experiments/sarol-2024/optimizer"
DATA_TGZ_BUCKET="gs://su-vista-uscentral1/chaudhari_lab/phil/paper-trail-data/sarol-data.tgz"
RUNS="$HOME/.paper-trail/runs/$RUN_ID"

say()  { printf '\n=== %s\n' "$*"; }
fail() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preconditions
say "Preconditions"

command -v python3 >/dev/null || fail "python3 not on PATH"
python3 - <<'PY' || fail "python >= 3.11 required (the code uses X | Y unions and match-era syntax)"
import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
echo "  python3: $(python3 -V)"

command -v claude >/dev/null || fail "the 'claude' CLI is not installed -- the judge is a nested 'claude -p' session per claim"
echo "  claude:  $(claude --version 2>&1 | head -1)"

# Auth is the failure that costs the most: it surfaces only on the first paid dispatch, after
# staging has run. Force it now, cheaply, with a prompt whose answer we do not care about.
if command -v timeout >/dev/null; then AUTH_TIMEOUT=(timeout 120); else AUTH_TIMEOUT=(); fi
if ! printf 'say OK' | "${AUTH_TIMEOUT[@]}" claude -p --max-budget-usd 0.05 >/dev/null 2>&1; then
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
  out=$(python3 "$m.py" --selftest 2>&1 | tail -1)
  case "$out" in *"passed"*) : ;; *) fail "$m selftest did not pass: $out";; esac
  echo "  $m: $out"
done

cd "$REPO_ROOT/experiments/sarol-2024"
python3 scripts/freeze_program_v0.py --verify --tree program-v0 >/dev/null 2>&1 \
  || fail "program-v0 does not verify against its tag -- the tree and the tag disagree, so numbers would be filed under the wrong program"
echo "  program-v0 verifies against its tag"

# ---------------------------------------------------------------- run
say "Run: $RUN_ID (workers=$MAX_WORKERS, iterations=$ITERATIONS)"
mkdir -p "$RUNS"
cd "$OPT"
# errexit off across the run itself: we want the post-run assertions to report the failure in
# terms of what is missing, not a bare non-zero from the pipeline.
set +e
python3 -u dispatcher.py --run \
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

python3 - "$REL" <<'PY' || fail "the final release did not carry a scored metric -- see the reason it printed"
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
PY

echo
echo "OK: run $RUN_ID completed. Results under $RUNS ; releases under $REPO_ROOT/iter/."
