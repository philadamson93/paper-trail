#!/usr/bin/env python3
"""
Stage one Sarol 2024 citation instance into a paper-trail-compatible working directory.

For Variant A of the Sarol benchmark experiment. Given a claim record from
claims-{train,dev,test}.jsonl and a target cited doc_id, this builds:

    <staging>/
      claims_ledger.md          — YAML frontmatter + empty claims section
      refs.bib                  — one fake bib entry for the cited paper
      pdfs/<citekey>/content.txt          — cited paper body text
      pdfs/<citekey>/meta.json            — minimal metadata
      pdfs/<citekey>/ingest_report.json   — marks pdftotext_fallback

After staging, the caller invokes the paper-trail extractor + Sarol-variant
adjudicator + verifier against this directory to produce a verdict.

Usage:
    stage_claim.py \\
        --split train \\
        --claim-id 0 \\
        --cited-paper-id 10 \\
        --source corpus \\
        --out experiments/sarol-2024/staging/train/0_10

The claim-id is the row ID in claims-<split>.jsonl. The cited-paper-id is the
paper's leading bucket (doc_id // 1000) — one claim record typically has
evidence annotations on one cited paper (occasionally multiple).
"""

import argparse
import json
import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "benchmarks" / "sarol-2024"
GOLD_DIR = REPO_ROOT / "experiments" / "sarol-2024" / "gold"


def load_claims(split: str) -> list[dict[str, Any]]:
    path = DATA_DIR / f"claims-{split}.jsonl"
    return [json.loads(l) for l in path.open()]


def load_corpus() -> dict[int, dict[str, Any]]:
    path = DATA_DIR / "corpus.jsonl"
    return {r["doc_id"]: r for r in (json.loads(l) for l in path.open())}


def find_references_txt(split: str, paper_bucket: int) -> pathlib.Path | None:
    """Find annotations/<Split>/references/NNN_PMC<ID>.txt by bucket number."""
    ref_dir = DATA_DIR / "annotations" / split.capitalize() / "references"
    if not ref_dir.exists():
        return None
    # Filenames are zero-padded NNN_PMC<ID>.txt; bucket number is NNN with leading zeros.
    # Bucket 10 -> could be 010_PMC... or 10_PMC... — try a few.
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
    """Return (body_text, title, source_description)."""
    if source_mode == "corpus":
        # Concatenate chunks from corpus.jsonl in doc_id order.
        chunks_for_paper = sorted(
            [d for d in cited_doc_ids if d // 1000 == paper_bucket]
        )
        lines: list[str] = []
        for d in chunks_for_paper:
            row = corpus.get(d)
            if row is None:
                continue
            for sent in row.get("abstract", []):
                lines.append(sent.strip())
        body = "\n".join(lines)
        title = ""  # corpus entries have blank titles
        desc = f"corpus.jsonl chunks, paper bucket {paper_bucket}, {len(chunks_for_paper)} chunks"
    elif source_mode == "full":
        path = find_references_txt(split, paper_bucket)
        if path is None:
            raise FileNotFoundError(
                f"No references/ file found for paper bucket {paper_bucket} in split {split}"
            )
        body = path.read_text()
        first_line = body.strip().splitlines()[0] if body else ""
        title = first_line[:200]
        desc = f"annotations/{split.capitalize()}/references/{path.name}"
    else:
        raise ValueError(f"unknown source_mode: {source_mode}")
    return body, title, desc


def normalize_claim_text(claim: str) -> str:
    """Replace Sarol's citation markers with a single placeholder so paper-trail's
    extractor treats them uniformly. The evaluated citation becomes [CIT]; other
    citations become [OTHER_CIT]."""
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

    # Validate the cited paper bucket actually has evidence for this claim.
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

    citekey = f"sarol_{split}_{cited_paper_bucket:03d}"
    claim_text = normalize_claim_text(row["claim"])
    is_multi_cit = "<|multi_cit|>" in row["claim"]
    multi_cit_context = "grouped" if is_multi_cit else "single"

    # Stage paths
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = out_dir / "pdfs"
    handle = pdf_dir / citekey
    handle.mkdir(parents=True, exist_ok=True)

    # Write content.txt with `L<n> [p<page>]: ...` line prefixes as the extractor expects.
    lines = body_text.splitlines()
    content_lines = [f"L{i+1} [p?]: {line}" for i, line in enumerate(lines) if line.strip()]
    (handle / "content.txt").write_text("\n".join(content_lines) + "\n")

    # Minimal meta.json
    (handle / "meta.json").write_text(
        json.dumps(
            {
                "citekey": citekey,
                "title": title or f"Sarol cited paper bucket {cited_paper_bucket}",
                "authors": [],
                "abstract": "",
                "doi": None,
                "sarol_paper_bucket": cited_paper_bucket,
                "sarol_source_mode": source_mode,
                "sarol_source_description": source_desc,
            },
            indent=2,
        )
    )

    # ingest_report.json — marks pdftotext_fallback so the extractor reads content.txt directly.
    (handle / "ingest_report.json").write_text(
        json.dumps(
            {
                "success": True,
                "mode": "pdftotext_fallback",
                "notes": "staged from Sarol 2024 benchmark; no real PDF ingest performed",
            },
            indent=2,
        )
    )

    # refs.bib — one entry for the citekey
    (out_dir / "refs.bib").write_text(
        f'@article{{{citekey},\n'
        f'  title = {{{title or "Sarol cited paper"}}},\n'
        f'  author = {{Unknown}},\n'
        f'  year = {{2020}},\n'
        f'  note = {{Staged from Sarol 2024 benchmark}},\n'
        f'}}\n'
    )

    # claims_ledger.md — minimum frontmatter for ground-claim to find pdf_dir and bib_files.
    (out_dir / "claims_ledger.md").write_text(
        "---\n"
        f"pdf_dir: pdfs\n"
        f"bib_files:\n"
        f"  - refs.bib\n"
        f"pdf_naming: citekey\n"
        "---\n\n"
        "# Claims ledger (Sarol experiment staging)\n\n"
        "_Populated by the experiment adjudicator._\n"
    )

    # === Leakage-safe split of manifest info ===
    # agent-visible: only what the dispatch prompts need (claim text normalized,
    # citekey, source_mode, multi_cit_context). NO gold labels, NO claim_row_id,
    # NO split, NO raw claim text (which could be grep'd against the benchmark).
    staging_info = {
        "citekey": citekey,
        "source_mode": source_mode,
        "multi_cit_context": multi_cit_context,
        "source_description": source_desc,
    }
    (out_dir / "staging_info.json").write_text(json.dumps(staging_info, indent=2))

    # agent-invisible: gold labels + full provenance, written to a sibling dir
    # outside the staging tree. parse_verdict.py loads this at scoring time.
    gold_file = GOLD_DIR / split / f"claim_{claim_row_id}_{cited_paper_bucket:03d}.json"
    gold_file.parent.mkdir(parents=True, exist_ok=True)
    gold_payload = {
        "split": split,
        "claim_row_id": claim_row_id,
        "cited_paper_bucket": cited_paper_bucket,
        "citekey": citekey,
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
        "gold_file": str(gold_file),
        "staging_dir": str(out_dir),
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

    manifest = stage(
        split=args.split,
        claim_row_id=args.claim_id,
        cited_paper_bucket=args.cited_paper_id,
        source_mode=args.source,
        out_dir=args.out,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
