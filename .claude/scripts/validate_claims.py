#!/usr/bin/env python3
"""
Validate extracted claims against the manuscript text before Phase 3 dispatch.

Runs three cheap, non-LLM checks per claim:

  1. Text anchor — does the stored `claim_text` actually appear in `paper.txt`?
     We accept any sequential 5-word window from the claim that matches the
     paper (after whitespace/punctuation normalization). No match on any
     window → the claim is almost certainly paraphrased or fabricated.

  2. Front-matter anchor — does the text-anchor fall above the Abstract /
     Introduction heading? That means the "claim" was pulled from the title
     / author / affiliation block, where superscript affiliation digits look
     identical to numbered citation markers. No real citation lives there.

  3. Citekey / refnum consistency — for numbered-citation papers, we look at
     citation markers (digit tokens) near the text-anchor position. If the
     claim's stored `citekey` resolves to a `refnum` and that refnum is NOT
     one of the nearby markers, the claim is attached to the wrong reference.

Emits `claim_extraction_report.md` in the run directory. Exit 0 if all
claims pass; exit 1 if any FLAG (gate-friendly).

Usage:
    python3 validate_claims.py --run-dir paper-trail-adamson2025-v2/
    python3 validate_claims.py --run-dir examples/paper-trail-adamson-2025/ \
        --claims-dir data/claims --allow-flagged
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "with", "this", "that",
    "from", "have", "has", "had", "are", "was", "were", "be", "been",
    "being", "is", "am", "not", "any", "all", "can", "use", "used", "using",
    "one", "two", "three", "also", "such", "these", "those", "into", "over",
    "here", "where", "when", "what", "which", "their", "there", "than",
    "then", "its", "our", "your", "his", "her", "him", "she", "he", "they",
    "them", "you", "we", "it", "of", "in", "on", "at", "to", "by", "as",
    "et", "al", "etc", "eg", "ie", "vs", "versus", "per", "via",
}


@dataclass
class ClaimResult:
    claim_id: str
    citekey: str
    refnum: int | None
    status: str  # "PASS" | "FLAG"
    flags: list[str] = field(default_factory=list)
    match_position: int | None = None
    match_window: str = ""
    nearby_refnums: list[int] = field(default_factory=list)
    claim_text_preview: str = ""


# ---------- Text normalization ----------

def normalize(text: str) -> str:
    """Lowercase, drop LaTeX commands, split letter↔digit boundaries, collapse whitespace."""
    s = text.lower()
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", s)              # \cite, \textit, etc.
    s = re.sub(r"[\{\}\\]", " ", s)                    # stray LaTeX braces
    s = re.sub(r"[^a-z0-9\-\s]", " ", s)
    # Split letter↔digit transitions so inline citation markers like "MSSIM11"
    # or "DFDs28-33" tokenize as two tokens, matching whatever the paper's PDF
    # extractor produced on the other side.
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def content_tokens(text: str) -> list[str]:
    toks = normalize(text).split()
    return [t for t in toks if len(t) >= 3 and t not in STOPWORDS]


# ---------- Paper loading ----------

def load_paper_text(run_dir: Path) -> str:
    """Pull manuscript text. Prefer paper.txt, then ledger content.txt, else ''."""
    for candidate in [run_dir / "paper.txt", run_dir / "input-paper.txt"]:
        if candidate.exists():
            return candidate.read_text(errors="replace")
    return ""


# ---------- Body-start detection ----------

# Heading patterns that mark the transition from title/author/affiliation
# block to real body text. Ordered by confidence; first hit wins.
BODY_START_PATTERNS = [
    re.compile(r"^\s*Abstract\s*$", re.MULTILINE),
    re.compile(r"^\s*ABSTRACT\s*$", re.MULTILINE),
    re.compile(r"^\s*A\s*B\s*S\s*T\s*R\s*A\s*C\s*T\s*$", re.MULTILINE),
    re.compile(r"^\s*Abstract\s*[:.\-—–]", re.MULTILINE),
    re.compile(r"^\s*Summary\s*$", re.MULTILINE),
    # Fallback for arXiv preprints that skip Abstract in pdftotext output.
    re.compile(r"^\s*(?:[IVX]+\.|\d+\.?)\s*Introduction\s*$", re.MULTILINE),
    re.compile(r"^\s*Introduction\s*$", re.MULTILINE),
]

# Cap the search to the first 10 KB; anything farther isn't front-matter.
BODY_START_SEARCH_LIMIT = 10_000


def find_body_start_offset(paper: str) -> int:
    """Return the raw offset where the paper body begins.

    We return the *start* of the first heading line that looks like
    "Abstract" / "ABSTRACT" / "Summary" / "1. Introduction", so anchors that
    land on or after that offset are considered body text. If no heading is
    recognizable, return 0 (no trimming — fail open so the rest of validation
    still runs).
    """
    window = paper[:BODY_START_SEARCH_LIMIT]
    earliest: int | None = None
    for pat in BODY_START_PATTERNS:
        m = pat.search(window)
        if m is None:
            continue
        if earliest is None or m.start() < earliest:
            earliest = m.start()
    return earliest if earliest is not None else 0


# ---------- Refs ----------

def parse_refs_bib(bib_path: Path) -> dict[str, dict]:
    refs: dict[str, dict] = {}
    if not bib_path.exists():
        return refs
    text = bib_path.read_text()
    for entry in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.DOTALL):
        key = entry.group(2).strip()
        body = entry.group(3)
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", body, re.DOTALL):
            fields[fm.group(1).lower()] = fm.group(2).strip()
        refnum = None
        if "refnum" in fields:
            try:
                refnum = int(fields["refnum"])
            except ValueError:
                pass
        refs[key] = {"citekey": key, "refnum": refnum}
    return refs


# ---------- Claim loading ----------

def load_claims(run_dir: Path, claims_subdir: str) -> list[dict]:
    claims: list[dict] = []
    search = [
        run_dir / claims_subdir,
        run_dir / "ledger" / "claims",
        run_dir / "data" / "claims",
    ]
    seen = set()
    for d in search:
        if d in seen or not d.exists():
            continue
        seen.add(d)
        for fp in sorted(d.glob("*.json")):
            try:
                claims.append(json.loads(fp.read_text()))
            except Exception as e:
                print(f"skip {fp.name}: {e}", file=sys.stderr)
        if claims:
            break
    return claims


# ---------- Check 1: text anchor ----------

def find_text_anchor(
    claim_text: str, paper_norm: str, paper_raw: str, paper_norm_to_raw: list[int]
) -> tuple[int | None, str]:
    """Return (position_in_paper_raw, matched_window_text) or (None, '').

    Strategy: take the first ~15 content tokens of the claim; try 5-/4-/3-token
    windows and match them against the normalized paper text, allowing up to 3
    intervening words between each pair (so stopwords in the paper don't break
    the match for a content-only claim window). Return the first hit's raw-offset.
    """
    claim_toks = content_tokens(claim_text)
    if len(claim_toks) < 3:
        return None, ""
    head = claim_toks[:15]
    for size in (5, 4, 3):
        if size > len(head):
            continue
        for i in range(len(head) - size + 1):
            window = head[i : i + size]
            # Allow up to 3 arbitrary words (stopwords, inline markers, etc.)
            # between each pair of content tokens.
            gap = r"(?:\s+\S+){0,3}\s+"
            parts = [r"\b" + re.escape(t) + r"\b" for t in window]
            pattern = re.compile(gap.join(parts))
            m = pattern.search(paper_norm)
            if not m:
                continue
            raw_start = (
                paper_norm_to_raw[m.start()]
                if m.start() < len(paper_norm_to_raw)
                else 0
            )
            return raw_start, " ".join(window)
    return None, ""


def build_normalized_index(paper: str) -> tuple[str, list[int]]:
    """Return (paper_norm, paper_norm_to_raw_offset_map).

    paper_norm_to_raw[i] = raw paper offset for the i-th char of paper_norm.
    """
    out_chars: list[str] = []
    map_to_raw: list[int] = []
    prev_space = True
    i = 0
    while i < len(paper):
        c = paper[i]
        cl = c.lower()
        if cl.isalnum() or cl == "-":
            out_chars.append(cl)
            map_to_raw.append(i)
            prev_space = False
        elif cl.isspace() or not cl.isalnum():
            if not prev_space:
                out_chars.append(" ")
                map_to_raw.append(i)
                prev_space = True
        i += 1
    return "".join(out_chars), map_to_raw


# ---------- Check 2: citekey / refnum consistency ----------

# Citation markers attach directly after punctuation/letters (e.g. "research.51",
# "methods,5", "MSSIM11"), so the *lookbehind* must NOT reject a preceding dot —
# only a preceding digit (to avoid splitting a longer number). But we still want
# to reject matches inside decimals ("1.2", "0.6") and version strings, hence the
# extra (?<!\d\.) and (?!\.\d) guards.
RANGE_RE = re.compile(r"(?<!\d\.)(?<!\d)(\d{1,3})\s*[\-–]\s*(\d{1,3})(?!\d)(?!\.\d)")
REFNUM_MARKER_RE = re.compile(r"(?<!\d\.)(?<!\d)(\d{1,3})(?!\d)(?!\.\d)")


def nearby_refnums(paper_raw: str, pos: int, valid_refnums: set[int], window: int = 280) -> list[int]:
    """Find citation markers near `pos` that correspond to known refnums.

    Handles ranges ("27-30", "28–33") by expanding to every integer in the range,
    and falls back to isolated digit tokens. Skips tokens that look like years.
    """
    lo = max(0, pos - window)
    hi = min(len(paper_raw), pos + window + 240)
    region = paper_raw[lo:hi]

    numbers_in_order: list[int] = []

    # Pass 1: expand ranges. Replace each range with a space so the single-number
    # regex doesn't double-count the endpoints.
    def emit_range(m: re.Match) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b and (b - a) <= 20:
            for n in range(a, b + 1):
                if n in valid_refnums and not (1900 <= n <= 2100):
                    numbers_in_order.append(n)
        return " " * len(m.group(0))
    region_after_ranges = RANGE_RE.sub(emit_range, region)

    # Pass 2: isolated numbers.
    for m in REFNUM_MARKER_RE.finditer(region_after_ranges):
        n = int(m.group(1))
        if n in valid_refnums and not (1900 <= n <= 2100):
            numbers_in_order.append(n)

    # Pass 3: hyphen-glued citation markers, e.g. "VGG-1646" where the body text
    # is "VGG-16" (model name) + superscript "46" (citation). pdftotext strips
    # the superscript, leaving glued digits that Pass 2's (?<!\d) rejects.
    # Scope tight: only letter(s)-hyphen-digits(3-5) patterns where the leading
    # digits form a plausible model version and the trailing 1-3 digits are a
    # valid refnum.
    for m in re.finditer(r'(?<![a-zA-Z0-9])[a-zA-Z]+(?:-[a-zA-Z]+)*-(\d{3,5})(?!\d)', region_after_ranges):
        digits = m.group(1)
        for k in (3, 2, 1):
            if len(digits) <= k:
                continue
            head = digits[:-k]
            tail = digits[-k:]
            # head must be a small model-version number (1-3 digits, <200)
            if not (1 <= len(head) <= 3 and int(head) < 200):
                continue
            n = int(tail)
            if n in valid_refnums and not (1900 <= n <= 2100):
                numbers_in_order.append(n)
                break

    # Dedupe preserving order.
    seen = set()
    out = []
    for n in numbers_in_order:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


# ---------- Main validator ----------

def validate(
    claims: list[dict],
    paper_raw: str,
    paper_norm: str,
    paper_norm_to_raw: list[int],
    citekey_to_refnum: dict[str, int],
    body_start_offset: int,
) -> list[ClaimResult]:
    valid_refnums = set(citekey_to_refnum.values())
    results: list[ClaimResult] = []

    for c in claims:
        cid = c.get("claim_id", "")
        ck = c.get("citekey", "")
        rn = citekey_to_refnum.get(ck)
        claim_text = c.get("claim_text") or ""
        overall = c.get("overall_verdict") or ""

        res = ClaimResult(
            claim_id=cid,
            citekey=ck,
            refnum=rn,
            status="PASS",
            claim_text_preview=claim_text[:140].replace("\n", " "),
        )

        # Skip PENDING claims — the source PDF wasn't fetched, so no adjudication
        # happened yet; validating the manuscript-side anchor still matters but
        # we relax the citekey check since PENDING claims weren't dispatched.
        is_pending = overall == "PENDING"

        if not paper_raw:
            res.flags.append("NO_PAPER_TEXT — cannot validate (paper.txt missing)")
            res.status = "FLAG"
            results.append(res)
            continue

        # Check 1: text anchor
        pos, window = find_text_anchor(claim_text, paper_norm, paper_raw, paper_norm_to_raw)
        res.match_position = pos
        res.match_window = window
        if pos is None:
            res.flags.append(
                "TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)"
            )
            res.status = "FLAG"

        # Check 2: front-matter anchor. If we detected a body-start heading
        # and this claim's anchor lives above it, the extractor pulled from
        # the title/author/affiliation block where superscript affiliation
        # digits look exactly like numbered citation markers.
        if pos is not None and body_start_offset > 0 and pos < body_start_offset:
            res.flags.append(
                f"FRONT_MATTER_ANCHOR — claim text anchors at offset {pos}, above the detected body-start "
                f"(Abstract / Introduction) at offset {body_start_offset}; author-affiliation superscripts "
                f"are being read as citation markers"
            )
            res.status = "FLAG"

        # Check 3: citekey/refnum consistency (only runnable if we have both a
        # position AND the bib carries refnum fields)
        if pos is not None and rn is not None and valid_refnums and not is_pending:
            nearby = nearby_refnums(paper_raw, pos, valid_refnums)
            res.nearby_refnums = nearby
            if nearby and rn not in nearby:
                res.flags.append(
                    f"CITEKEY_MARKER_MISMATCH — claim cites {ck} (ref {rn}), but nearby markers are {nearby}"
                )
                res.status = "FLAG"

        results.append(res)

    return results


# ---------- Reporting ----------

def render_report(
    run_dir: Path, results: list[ClaimResult], counts: dict, body_start_offset: int
) -> str:
    flagged = [r for r in results if r.status == "FLAG"]
    passed = [r for r in results if r.status == "PASS"]
    flag_breakdown: dict[str, int] = {}
    for r in flagged:
        for f in r.flags:
            key = f.split(" ", 1)[0]
            flag_breakdown[key] = flag_breakdown.get(key, 0) + 1

    lines: list[str] = []
    lines.append(f"# Claim extraction validation — `{run_dir.name}`\n")
    lines.append(f"**{len(results)} claims total · {len(passed)} PASS · {len(flagged)} FLAG**\n")
    if body_start_offset > 0:
        lines.append(
            f"Body-start heading detected at offset {body_start_offset} "
            f"(everything above is title/author/affiliation block and is excluded from claim extraction).\n"
        )
    else:
        lines.append(
            "No body-start heading (Abstract / Introduction) detected — "
            "FRONT_MATTER_ANCHOR check disabled for this run.\n"
        )
    if flag_breakdown:
        lines.append("## Flag breakdown\n")
        for k, v in sorted(flag_breakdown.items(), key=lambda kv: -kv[1]):
            lines.append(f"- `{k}`: **{v}**")
        lines.append("")

    if flagged:
        lines.append("## Flagged claims\n")
        for r in flagged:
            header = f"### {r.claim_id} · `{r.citekey}`"
            if r.refnum is not None:
                header += f" (ref {r.refnum})"
            lines.append(header)
            lines.append("")
            lines.append(f"> {r.claim_text_preview}{'…' if len(r.claim_text_preview) >= 140 else ''}")
            lines.append("")
            for f in r.flags:
                lines.append(f"- **{f}**")
            if r.match_position is not None:
                lines.append(f"- Matched window `{r.match_window}` at offset {r.match_position}")
            if r.nearby_refnums:
                lines.append(f"- Nearby markers: {r.nearby_refnums}")
            lines.append("")

    lines.append("## Passed claims (for reference)\n")
    lines.append("<details><summary>Click to expand</summary>\n")
    for r in passed:
        ref_str = f" (ref {r.refnum})" if r.refnum is not None else ""
        lines.append(f"- {r.claim_id} · `{r.citekey}`{ref_str}")
    lines.append("\n</details>")

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--claims-dir", default="", help="override; default auto-detects ledger/claims or data/claims")
    ap.add_argument("--bib", default="refs.bib")
    ap.add_argument("--output", default="claim_extraction_report.md")
    ap.add_argument("--allow-flagged", action="store_true", help="exit 0 even if claims are flagged")
    args = ap.parse_args()

    run = args.run_dir.resolve()
    paper_raw = load_paper_text(run)
    paper_norm, paper_norm_to_raw = build_normalized_index(paper_raw) if paper_raw else ("", [])
    body_start_offset = find_body_start_offset(paper_raw) if paper_raw else 0

    verified = run / "refs.verified.bib"
    bib_path = verified if verified.exists() else run / args.bib
    refs = parse_refs_bib(bib_path)
    citekey_to_refnum = {
        r["citekey"]: r["refnum"] for r in refs.values() if r.get("refnum") is not None
    }

    claims = load_claims(run, args.claims_dir)
    if not claims:
        print("no claims found — nothing to validate", file=sys.stderr)
        return 1

    results = validate(
        claims, paper_raw, paper_norm, paper_norm_to_raw, citekey_to_refnum, body_start_offset
    )
    counts = {
        "total": len(results),
        "pass": sum(1 for r in results if r.status == "PASS"),
        "flag": sum(1 for r in results if r.status == "FLAG"),
    }

    report = render_report(run, results, counts, body_start_offset)
    (run / args.output).write_text(report)

    # Console summary
    print(f"validated {counts['total']} claims — {counts['pass']} PASS, {counts['flag']} FLAG")
    if counts["flag"]:
        flag_types: dict[str, int] = {}
        for r in results:
            for f in r.flags:
                k = f.split(" ", 1)[0]
                flag_types[k] = flag_types.get(k, 0) + 1
        for k, v in sorted(flag_types.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")
        print(f"report: {run / args.output}")
        if not args.allow_flagged:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
