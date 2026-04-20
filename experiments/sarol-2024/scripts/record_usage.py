#!/usr/bin/env python3
"""
Record one subagent's usage report into the staging dir's ledger/usage sidecar.

Called by the orchestrator (or the runbook agent) immediately after an Agent tool
call returns, using the numbers from the `<usage>` block in the Agent's output.

Usage:
    record_usage.py --staging <staging_dir> --claim-id C001 --stage extractor \\
        --model claude-opus-4-7 --total-tokens 38929 --tool-uses 15 --duration-ms 73917

Writes JSONL to <staging_dir>/ledger/usage/<claim_id>.jsonl (append). Each line
is one subagent call's usage. `parse_verdict.py` aggregates.
"""

import argparse
import json
import pathlib
import sys
import time
from typing import Any


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--staging", required=True, type=pathlib.Path)
    ap.add_argument("--claim-id", required=True)
    ap.add_argument(
        "--stage",
        required=True,
        choices=["extractor", "adjudicator", "verifier"],
    )
    ap.add_argument("--model", default="claude-opus-4-7")
    ap.add_argument("--total-tokens", type=int, required=True)
    ap.add_argument("--tokens-in", type=int, default=None)
    ap.add_argument("--tokens-out", type=int, default=None)
    ap.add_argument("--tool-uses", type=int, default=None)
    ap.add_argument("--duration-ms", type=int, default=None)
    args = ap.parse_args()

    record: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claim_id": args.claim_id,
        "stage": args.stage,
        "model": args.model,
        "total_tokens": args.total_tokens,
        "tokens_in": args.tokens_in,
        "tokens_out": args.tokens_out,
        "tool_uses": args.tool_uses,
        "duration_ms": args.duration_ms,
        "wall_clock_seconds": (args.duration_ms / 1000.0) if args.duration_ms else None,
    }

    usage_dir = args.staging / "ledger" / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    path = usage_dir / f"{args.claim_id}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
