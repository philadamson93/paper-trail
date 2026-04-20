#!/usr/bin/env bash
# Downloads the Sarol et al. 2024 citation-integrity benchmark from its public GitHub repo.
# Fetches INTO $PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/ (default: $HOME/.paper-trail/benchmarks/sarol-2024/).
#
# Rationale: benchmark raw data is deliberately stored OUTSIDE the repo tree so that
# experiment orchestrator agents whose working directory is the repo do not encounter
# gold labels via filesystem exploration. See docs/plans/experiment-sarol-leakage-hardening.md.
#
# Source: https://github.com/ScienceNLP-Lab/Citation-Integrity (MIT license)

set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/ScienceNLP-Lab/Citation-Integrity/main/Data"
BENCH_ROOT="${PAPER_TRAIL_BENCHMARKS_DIR:-$HOME/.paper-trail/benchmarks}"
DEST="$BENCH_ROOT/sarol-2024"

mkdir -p "$DEST"
cd "$DEST"

fetch() {
  local rel="$1"
  local out="$2"
  if [[ -s "$out" ]]; then
    echo "[skip] $out (already present)"
    return
  fi
  echo "[get ] $out"
  curl -fsSL -o "$out" "$BASE_URL/$rel"
}

fetch "multivers-format/claims-train.jsonl" "claims-train.jsonl"
fetch "multivers-format/claims-dev.jsonl"   "claims-dev.jsonl"
fetch "multivers-format/claims-test.jsonl"  "claims-test.jsonl"
fetch "multivers-format/corpus.jsonl"       "corpus.jsonl"
fetch "annotations.zip"                     "annotations.zip"

if [[ -s annotations.zip && ! -d annotations ]]; then
  echo "[unzip] annotations.zip"
  unzip -q annotations.zip
  rm -rf __MACOSX
fi

echo
echo "Done. Files in $DEST:"
ls -la "$DEST" | grep -v '^total\|^d.*\.\.\?$'
echo
echo "Stage/parse scripts will find this automatically via the default path."
echo "Override with:  export PAPER_TRAIL_BENCHMARKS_DIR=<your/path>"
