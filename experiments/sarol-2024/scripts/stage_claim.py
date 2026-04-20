#!/usr/bin/env python3
"""
Stage one Sarol 2024 citation instance into a paper-trail-compatible working directory.

For Variant A of the Sarol benchmark experiment. Structurally blinded for leakage:

- Benchmark raw data reads from $PAPER_TRAIL_BENCHMARKS_DIR/sarol-2024/
  (default: $HOME/.paper-trail/benchmarks/sarol-2024/). Data lives OUTSIDE the repo tree.
- Gold labels write to $PAPER_TRAIL_GOLD_DIR/sarol-2024/<split>/
  (default: $HOME/.paper-trail/gold/sarol-2024/<split>/). Also outside the repo.
- Staging citekey is an OPAQUE deterministic hash (ref_<6hex>) — does not encode
  split or paper bucket. The orchestrator that runs this script knows the claim_id
  but the citekey in subagent prompts and staging files reveals nothing.

After staging, the caller dispatches the paper-trail extractor + Sarol-variant
adjudicator + verifier against this directory to produce a verdict. Scoring
happens separately, in a different process invocation, via parse_verdict.py.

Usage:
    stage_claim.py \\
        --split train \\
        --claim-id 417 \\
        --cited-paper-id 81 \\
        --source corpus \\
        --out experiments/sarol-2024/staging/smoketest/s1
"""

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _benchmarks_root() -> pathlib.Path:
    override = os.environ.get("PAPER_TRAIL_BENCHMARKS_DIR")
    if override:
        return pathlib.Path(override).expanduser()
    return pathlib.Path.home() / ".paper-trail" / "benchmarks"


def _gold_root() -> pathlib.Path:
    override = os.environ.get("PAPER_TRAIL_GOLD_DIR")
    if override:
        return pathlib.Path(override).expanduser()
    return pathlib.Path.home() / ".paper-trail" / "gold"


BENCH_DIR = _benchmarks_root() / "sarol-2024"
GOLD_ROOT = _gold_root() / "sarol-2024"


def opaque_citekey(split: str, claim_row_id: int, paper_bucket: int) -> str:
    """Deterministic opaque citekey. Hides split + bucket from subagent prompts
    and from any file the orchestrator sees in the staging tree. Collision rate
    at 24 bits is negligible for our corpus size."""
    h = hashlib.sha256(f"{split}|{claim_row_id}|{paper_bucket}".encode()).hexdigest()
    return f"ref_{h[:6]}"


def load_claims(split: str) -> list[dict[str, Any]]:
    path = BENCH_DIR / f"claims-{split}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Benchmark not found at {path}. Set PAPER_TRAIL_BENCHMARKS_DIR or run "
            f"data/benchmarks/sarol-2024/download.sh first."
        )
    return [json.loads(l) for l in path.open()]


def load_corpus() -> dict[int, dict[str, Any]]:
    path = BENCH_DIR / "corpus.jsonl"
    return {r["doc_id"]: r for r in (json.loads(l) for l in path.open())}


def find_references_txt(split: str, paper_bucket: int) -> pathlib.Path | None:
    ref_dir = BENCH_DIR / "annotations" / split.capitalize() / "references"
    if not ref_dir.exists():
        return None
    for candidate in ref_dir.iterdir():
        if candidate.name.startswith(f"{paper_bucket:03d}_") or candidate.name.startswith(f"{paper_bucket:04d}_"):
            return candidate
    return None


def build_source_text(
    split: str,
    paper_bucket: int,
    cited_doc_ids: list[int],
    corpus: dict[int, dict[str, Any]],
    source_mode: str,
) -> tuple[str, str, str]:
    if source_mode == "corpus":
        chunks_for_paper = sorted([d for d in cited_doc_ids if d // 1000 == paper_bucket])
        lines: list[str] = []
        for d in chunks_for_paper:
            row = corpus.get(d)
            if row is None:
                continue
            for sent in row.get("abstract", []):
                lines.append(sent.strip())
        body = "\n".join(lines)
        title = ""
        desc = f"corpus-chunks (N={len(chunks_for_paper)})"
    elif source_mode == "full":
        path = find_references_txt(split, paper_bucket)
        if path is None:
            raise FileNotFoundError(
                f"No references/ file found for paper bucket {paper_bucket} in split {split}"
            )
        body = path.read_text()
        first_line = body.strip().splitlines()[0] if body else ""
        title = first_line[:200]
        desc = "references-fulltext"
    else:
        raise ValueError(f"unknown source_mode: {source_mode}")
    return body, title, desc


def normalize_claim_text(claim: str) -> str:
    out = claim
    out = re.sub(r"<\|multi_cit\|>", "[CIT]", out)
    out = re.sub(r"<\|cit\|>", "[CIT]", out)
    out = re.sub(r"<\|other_cit\|>", "[OTHER_CIT]", out)
    return out


def stage(
    split: str,
    claim_row_id: int,
    cited_paper_bucket: int,
    source_mode: str,
    out_dir: pathlib.Path,
) -> dict[str, Any]:
    claims = load_claims(split)
    row = next((r for r in claims if r["id"] == claim_row_id), None)
    if row is None:
        raise KeyError(f"claim id {claim_row_id} not found in claims-{split}.jsonl")

    evidence = row.get("evidence", {})
    evidence_for_bucket = {
        doc_id: anns
        for doc_id, anns in evidence.items()
        if int(doc_id) // 1000 == cited_paper_bucket
    }
    if not evidence_for_bucket:
        raise ValueError(
            f"claim {claim_row_id} has no evidence annotations on paper bucket {cited_paper_bucket}"
        )

    corpus = load_corpus() if source_mode == "corpus" else {}

    body_text, title, source_desc = build_source_text(
        split=split,
        paper_bucket=cited_paper_bucket,
        cited_doc_ids=row["cited_doc_ids"],
        corpus=corpus,
        source_mode=source_mode,
    )

    citekey = opaque_citekey(split, claim_row_id, cited_paper_bucket)
    claim_text = normalize_claim_text(row["claim"])
    is_multi_cit = "<|multi_cit|>" in row["claim"]
    multi_cit_context = "grouped" if is_multi_cit else "single"

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir / "pdfs"
    handle = pdf_dir / citekey
    handle.mkdir(parents=True, exist_ok=True)

    lines = body_text.splitlines()
    content_lines = [f"L{i+1} [p?]: {line}" for i, line in enumerate(lines) if line.strip()]
    (handle / "content.txt").write_text("\n".join(content_lines) + "\n")

    (handle / "meta.json").write_text(
        json.dumps(
            {
                "citekey": citekey,
                "title": title or "Cited paper (staged)",
                "authors": [],
                "abstract": "",
                "doi": None,
            },
            indent=2,
        )
    )

    (handle / "ingest_report.json").write_text(
        json.dumps(
            {
                "success": True,
                "mode": "pdftotext_fallback",
                "notes": "staged from external benchmark; no real PDF ingest performed",
            },
            indent=2,
        )
    )

    (out_dir / "refs.bib").write_text(
        f'@article{{{citekey},\n'
        f'  title = {{{title or "Cited paper"}}},\n'
        f'  author = {{Unknown}},\n'
        f'  year = {{2020}},\n'
        f'  note = {{Staged reference}},\n'
        f'}}\n'
    )

    (out_dir / "claims_ledger.md").write_text(
        "---\n"
        f"pdf_dir: pdfs\n"
        f"bib_files:\n"
        f"  - refs.bib\n"
        f"pdf_naming: citekey\n"
        "---\n\n"
        "# Claims ledger\n\n"
        "_Populated by the experiment adjudicator._\n"
    )

    # Agent-visible staging info: opaque citekey + source mode + multi-cit flag only.
    # No split, no claim_row_id, no paper bucket — everything that could be used to
    # back out the gold label lives outside the repo.
    staging_info = {
        "citekey": citekey,
        "source_mode": source_mode,
        "multi_cit_context": multi_cit_context,
        "source_description": source_desc,
    }
    (out_dir / "staging_info.json").write_text(json.dumps(staging_info, indent=2))

    # Agent-invisible: gold labels + full provenance, written OUTSIDE the repo tree.
    # parse_verdict.py reads this at scoring time only, by ref.
    gold_dir = GOLD_ROOT / split
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_file = gold_dir / f"{citekey}.json"
    gold_payload = {
        "citekey": citekey,
        "split": split,
        "claim_row_id": claim_row_id,
        "cited_paper_bucket": cited_paper_bucket,
        "source_mode": source_mode,
        "multi_cit_context": multi_cit_context,
        "claim_text_original": row["claim"],
        "claim_text_normalized": claim_text,
        "gold_evidence": evidence_for_bucket,
        "staging_dir": str(out_dir),
    }
    gold_file.write_text(json.dumps(gold_payload, indent=2))

    return {
        "staging_info": staging_info,
        "citekey": citekey,
        "staging_dir": str(out_dir),
        # Note: gold_file path is deliberately NOT returned here — the orchestrator
        # has no business knowing it. parse_verdict.py reconstructs it from citekey.
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", choices=["train", "dev", "test"], required=True)
    ap.add_argument("--claim-id", type=int, required=True, help="row id in claims-<split>.jsonl")
    ap.add_argument(
        "--cited-paper-id",
        type=int,
        required=True,
        help="paper bucket (doc_id // 1000) of the cited paper to evaluate against",
    )
    ap.add_argument(
        "--source",
        choices=["corpus", "full"],
        default="corpus",
        help='"corpus" = pre-chunked Sarol corpus.jsonl (apples-to-apples); "full" = PMC .txt from references/',
    )
    ap.add_argument("--out", required=True, type=pathlib.Path)
    args = ap.parse_args()

    result = stage(
        split=args.split,
        claim_row_id=args.claim_id,
        cited_paper_bucket=args.cited_paper_id,
        source_mode=args.source,
        out_dir=args.out,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
