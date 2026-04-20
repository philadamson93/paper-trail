#!/usr/bin/env bash
# Downloads the Sarol et al. 2024 citation-integrity benchmark from its public GitHub repo.
# Idempotent — re-running skips files that already exist with a non-zero size.
# Source: https://github.com/ScienceNLP-Lab/Citation-Integrity (MIT license)

set -euo pipefail
BASE_URL="https://raw.githubusercontent.com/ScienceNLP-Lab/Citation-Integrity/main/Data"
cd "$(dirname "$0")"

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

echo "Done. Files in $(pwd):"
ls -la | grep -v '^total\|^d.*\.\.\?$'
