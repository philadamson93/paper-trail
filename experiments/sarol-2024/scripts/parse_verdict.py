#!/usr/bin/env python3
"""
Read a paper-trail adjudicated claim JSON produced under the Sarol 9-class
rubric variant, look up gold (from outside the repo) by opaque citekey, and
emit one prediction record.

Design invariants for leakage prevention:
- Gold lives at $PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/<citekey>.json
  (default: $HOME/.paper-trail/gold/sarol-2024/…) — OUTSIDE the repo tree.
- This script is the ONLY code that touches gold. Call it only AFTER all
  adjudications for a run are complete. Do not invoke it inside the run loop.

Usage:
    parse_verdict.py --staging <dir> --out <predictions.jsonl>
"""

import argparse
import json
import os
import pathlib
import sys
from typing import Any

SAROL_9 = {
    "ACCURATE",
    "OVERSIMPLIFY",
    "NOT_SUBSTANTIATE",
    "CONTRADICT",
    "MISQUOTE",
    "INDIRECT",
    "INDIRECT_NOT_REVIEW",
    "ETIQUETTE",
    "IRRELEVANT",
}

NOT_ACCURATE_3WAY = {"OVERSIMPLIFY", "NOT_SUBSTANTIATE", "CONTRADICT", "MISQUOTE", "INDIRECT"}
IRRELEVANT_3WAY = {"ETIQUETTE", "INDIRECT_NOT_REVIEW", "IRRELEVANT"}

PRICING = {
    "claude-opus-4-7": {"in": 5.0, "out": 25.0},
    "claude-opus-4-6": {"in": 5.0, "out": 25.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
}
DEFAULT_INPUT_FRACTION = 0.85


def _gold_root() -> pathlib.Path:
    override = os.environ.get("PAPER_TRAIL_GOLD_DIR")
    if override:
        return pathlib.Path(override).expanduser()
    return pathlib.Path.home() / ".paper-trail" / "gold"


def find_gold_file(citekey: str) -> pathlib.Path:
    root = _gold_root() / "sarol-2024"
    matches = list(root.glob(f"*/{citekey}.json"))
    if not matches:
        raise FileNotFoundError(
            f"No gold file for citekey {citekey} under {root}. "
            f"Re-run stage_claim.py to regenerate, or set PAPER_TRAIL_GOLD_DIR if you moved the gold tree."
        )
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous gold for {citekey}: multiple matches {matches}")
    return matches[0]


def to_3way(label: str) -> str:
    if label == "ACCURATE":
        return "ACCURATE"
    if label in NOT_ACCURATE_3WAY:
        return "NOT_ACCURATE"
    if label in IRRELEVANT_3WAY:
        return "IRRELEVANT"
    return "UNKNOWN"


def gold_paper_label(evidence_for_bucket: dict[str, list[dict[str, Any]]]) -> str:
    strictness = [
        "CONTRADICT",
        "NOT_SUBSTANTIATE",
        "MISQUOTE",
        "OVERSIMPLIFY",
        "INDIRECT",
        "INDIRECT_NOT_REVIEW",
        "IRRELEVANT",
        "ETIQUETTE",
        "ACCURATE",
    ]
    observed = set()
    for _doc_id, ann_list in evidence_for_bucket.items():
        for ann in ann_list:
            observed.add(ann["label"])
    for label in strictness:
        if label in observed:
            return label
    return "ACCURATE"


def load_usage(staging_dir: pathlib.Path, claim_id: str) -> list[dict[str, Any]]:
    path = staging_dir / "ledger" / "usage" / f"{claim_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.open() if l.strip()]


def estimate_cost_usd(usage_records: list[dict[str, Any]]) -> dict[str, Any]:
    total_in = 0
    total_out = 0
    total_cost = 0.0
    per_stage: dict[str, dict[str, Any]] = {}
    for rec in usage_records:
        model = rec.get("model", "claude-opus-4-7")
        price = PRICING.get(model)
        total = rec.get("total_tokens") or 0
        tok_in = rec.get("tokens_in")
        tok_out = rec.get("tokens_out")
        if tok_in is None or tok_out is None:
            tok_in = int(total * DEFAULT_INPUT_FRACTION)
            tok_out = total - tok_in
            inferred = True
        else:
            inferred = False
        cost = None
        if price is not None:
            cost = (tok_in / 1_000_000) * price["in"] + (tok_out / 1_000_000) * price["out"]
            total_cost += cost
        total_in += tok_in
        total_out += tok_out
        stage = rec.get("stage", "unknown")
        per_stage[stage] = {
            "model": model,
            "total_tokens": total,
            "tokens_in": tok_in,
            "tokens_out": tok_out,
            "tokens_inferred_split": inferred,
            "tool_uses": rec.get("tool_uses"),
            "wall_clock_seconds": rec.get("wall_clock_seconds"),
            "cost_usd": round(cost, 6) if cost is not None else None,
        }
    return {
        "tokens_in_total": total_in,
        "tokens_out_total": total_out,
        "cost_usd_total": round(total_cost, 6),
        "per_stage": per_stage,
    }


def parse(staging_dir: pathlib.Path) -> dict[str, Any]:
    staging_info = json.loads((staging_dir / "staging_info.json").read_text())
    citekey = staging_info["citekey"]

    gold_file = find_gold_file(citekey)
    gold = json.loads(gold_file.read_text())

    claims_dir = staging_dir / "ledger" / "claims"
    claim_files = sorted(claims_dir.glob("*.json"))
    if not claim_files:
        raise FileNotFoundError(f"no adjudicated claim JSON under {claims_dir}")
    if len(claim_files) > 1:
        print(
            f"[warn] {len(claim_files)} claim files in {claims_dir}; taking first",
            file=sys.stderr,
        )
    verdict = json.loads(claim_files[0].read_text())

    if verdict.get("rubric_variant") != "sarol_2024_9class":
        print(
            f"[warn] verdict {claim_files[0]} not marked rubric_variant=sarol_2024_9class "
            f"(got {verdict.get('rubric_variant')!r}); treating output as if it were",
            file=sys.stderr,
        )

    pred = verdict.get("overall_verdict")
    if pred not in SAROL_9:
        print(f"[warn] adjudicated label {pred!r} not in Sarol 9-class enum", file=sys.stderr)

    gold_label = gold_paper_label(gold["gold_evidence"])

    claim_id = verdict.get("claim_id", "C???")
    usage_records = load_usage(staging_dir, claim_id)
    usage_summary = estimate_cost_usd(usage_records) if usage_records else None

    return {
        "split": gold["split"],
        "claim_row_id": gold["claim_row_id"],
        "cited_paper_bucket": gold["cited_paper_bucket"],
        "citekey": citekey,
        "source_mode": gold["source_mode"],
        "multi_cit_context": gold["multi_cit_context"],
        "pred_label": pred,
        "pred_3way": to_3way(pred) if pred in SAROL_9 else "UNKNOWN",
        "gold_label": gold_label,
        "gold_3way": to_3way(gold_label),
        "sub_claim_verdicts": [s.get("verdict") for s in verdict.get("sub_claims", [])],
        "claim_text": gold["claim_text_original"],
        "overall_flag": verdict.get("overall_flag"),
        "remediation_category": (verdict.get("remediation") or {}).get("category"),
        "timing_seconds": (verdict.get("timing") or {}).get("wall_clock_seconds"),
        "usage": usage_summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--staging", required=True, type=pathlib.Path)
    ap.add_argument(
        "--out",
        required=True,
        type=pathlib.Path,
        help="predictions.jsonl — appended to, not overwritten",
    )
    args = ap.parse_args()

    record = parse(args.staging)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
