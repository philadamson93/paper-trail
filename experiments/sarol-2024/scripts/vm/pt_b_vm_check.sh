#!/usr/bin/env bash
# PT-B's check on the VM that holds the hill-climb checkout: run once after pulling PT-B.
#
# Copies the optimizer's old per-iteration findings into the engine's notes history (run id `legacy`),
# confirms the engine checkout carries PT-B's pin, and runs every self-test the preflight runs plus the
# two PT-B rewrote. Spends nothing; no session is started. Last line: PT-B VM CHECK: PASS, or the
# first failure.
#
#   AGENTIC_LABEL_OPT=<engine checkout> bash experiments/sarol-2024/scripts/vm/pt_b_vm_check.sh
#
# The Linux setup pins owed since PT-A are not part of this check.

set -euo pipefail

PY="${PAPER_TRAIL_PYTHON:-$HOME/.local/bin/python3.13}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
EXP="$REPO_ROOT/experiments/sarol-2024"

fail() { printf '\nPT-B VM CHECK: FAIL -- %s\n' "$*" >&2; exit 1; }

[ -x "$PY" ] || fail "interpreter not found at $PY (set PAPER_TRAIL_PYTHON)"
: "${AGENTIC_LABEL_OPT:?PT-B VM CHECK: FAIL -- set AGENTIC_LABEL_OPT to the agentic-label-opt checkout}"
export AGENTIC_LABEL_OPT

echo "== engine pin"
"$PY" "$EXP/optimizer/engine_pin.py" || fail "the engine checkout does not carry PT-B's pin; pull agentic-label-opt main"

echo "== old findings into the notes history"
"$PY" "$EXP/scripts/copy_legacy_findings.py" || fail "copying the old findings failed"

echo "== self-tests"
for f in optimizer/adapter optimizer/dispatcher optimizer/sampling optimizer/validate_sarol optimizer/profiles \
         optimizer/canary optimizer/evidence_producers optimizer/engine_pin optimizer/sarol_isolation \
         optimizer/sarol_optimizer optimizer/sarol_program scripts/copy_legacy_findings scripts/check_prompt_hygiene \
         scripts/freeze_program_v0; do
  rc=0; full="$(cd "$EXP/$(dirname "$f")" && "$PY" "$(basename "$f").py" --selftest 2>&1)" || rc=$?
  out="$(printf '%s\n' "$full" | tail -1)"
  [ "$rc" = 0 ] || fail "$f exited $rc: $out"
  counts="${out%% passed*}"; counts="${counts##* }"; n="${counts%%/*}"; m_="${counts##*/}"
  case "$out" in *" passed"*) : ;; *) fail "$f: $out";; esac
  # "N/N passed" with N a positive number: "44/48", "0/0" and "ok (all checks passed)" all refused.
  [[ "$counts" == */* && "$n" =~ ^[1-9][0-9]*$ && "$n" = "$m_" ]] || fail "$f: $out"
  echo "  $f: $out"
done

echo
echo "PT-B VM CHECK: PASS"
