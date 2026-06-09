#!/usr/bin/env python3
"""
Render a paper-trail audit run as a standalone PDF.js-based HTML viewer.

Layout:
  - Left: continuous-scroll PDF.js viewer of the input paper (text layer on so
    citation markers are clickable and text is selectable).
  - Right: sidebar listing every claim with verdict pill, citekey/refnum, and
    a one-line preview. Clicking a row jumps the PDF to that claim's page and
    highlights the associated citation markers; an info button opens a popup
    with the full claim details + evidence + remediation.
  - Clicking a citation marker inside the PDF scrolls the sidebar to the
    matching claim(s) and highlights them.

The emitted `demo.html` expects `input-paper.pdf` as a sibling file. Open in
Firefox directly, or serve via `python3 -m http.server` for Chrome (Chrome
blocks cross-file `file://` fetches by default).

Usage:
    python3 render_html_demo.py --run-dir paper-trail-adamson2025-v2/
    python3 render_html_demo.py --run-dir examples/paper-trail-adamson-2025/ \
        --claims-dir data/claims --pdf input-paper.pdf
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from html import escape
from pathlib import Path


PDFJS_VERSION = "3.11.174"
PDFJS_BASE = f"https://cdn.jsdelivr.net/npm/pdfjs-dist@{PDFJS_VERSION}/build"


VERDICT_COLOR = {
    "CONFIRMED": "#16a34a",
    "CONFIRMED_WITH_MINOR": "#65a30d",
    "OVERSTATED_MILD": "#eab308",
    "OVERSTATED": "#f97316",
    "OVERGENERAL": "#f97316",
    "PARTIALLY_SUPPORTED": "#fb923c",
    "CITED_OUT_OF_CONTEXT": "#fb923c",
    "INDIRECT_SOURCE": "#a855f7",
    "MISATTRIBUTED": "#dc2626",
    "UNSUPPORTED": "#dc2626",
    "CONTRADICTED": "#991b1b",
    "AMBIGUOUS": "#9ca3af",
    "PENDING": "#cbd5e1",
}

VERDICT_LABEL = {
    "CONFIRMED": "Confirmed",
    "CONFIRMED_WITH_MINOR": "Confirmed (minor)",
    "OVERSTATED_MILD": "Overstated (mild)",
    "OVERSTATED": "Overstated",
    "OVERGENERAL": "Overgeneral",
    "PARTIALLY_SUPPORTED": "Partial support",
    "CITED_OUT_OF_CONTEXT": "Out of context",
    "INDIRECT_SOURCE": "Indirect source",
    "MISATTRIBUTED": "Misattributed",
    "UNSUPPORTED": "Unsupported",
    "CONTRADICTED": "Contradicted",
    "AMBIGUOUS": "Ambiguous",
    "PENDING": "Pending — PDF unavailable",
}

# Rough severity ordering (worst → best) for sorting / "critical first" display.
VERDICT_SEVERITY = {
    "CONTRADICTED": 0,
    "UNSUPPORTED": 1,
    "MISATTRIBUTED": 2,
    "INDIRECT_SOURCE": 3,
    "CITED_OUT_OF_CONTEXT": 4,
    "PARTIALLY_SUPPORTED": 5,
    "OVERGENERAL": 6,
    "OVERSTATED": 7,
    "OVERSTATED_MILD": 8,
    "AMBIGUOUS": 9,
    "CONFIRMED_WITH_MINOR": 10,
    "CONFIRMED": 11,
    "PENDING": 12,
}


def parse_refs_bib(bib_path: Path) -> dict[str, dict]:
    refs: dict[str, dict] = {}
    if not bib_path.exists():
        return refs
    text = bib_path.read_text()
    for entry in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.DOTALL):
        etype = entry.group(1)
        key = entry.group(2).strip()
        body = entry.group(3)
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", body, re.DOTALL):
            fields[fm.group(1).lower()] = re.sub(r"\s+", " ", fm.group(2).strip())
        refnum = None
        if "refnum" in fields:
            try:
                refnum = int(fields["refnum"])
            except ValueError:
                pass
        refs[key] = {
            "citekey": key,
            "type": etype,
            "refnum": refnum,
            "authors": fields.get("author", ""),
            "title": fields.get("title", ""),
            "venue": fields.get("journal", "") or fields.get("booktitle", ""),
            "year": fields.get("year", ""),
            "doi": fields.get("doi", ""),
            "arxiv": fields.get("arxiv", ""),
        }
    return refs


def first_author_short(authors: str) -> str:
    if not authors:
        return ""
    parts = [a.strip() for a in authors.split(" and ")]
    first = parts[0]
    last = first.split(",")[0].strip() if "," in first else first.split()[-1]
    if len(parts) == 1:
        return last
    if len(parts) == 2:
        second = parts[1]
        sec_last = second.split(",")[0].strip() if "," in second else second.split()[-1]
        return f"{last} & {sec_last}"
    return f"{last} et al."


def reference_link(ref: dict) -> str:
    if ref.get("doi"):
        return f"https://doi.org/{ref['doi']}"
    if ref.get("arxiv"):
        return f"https://arxiv.org/abs/{ref['arxiv']}"
    return ""


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
                print(f"skip {fp.name}: {e}")
        if claims:
            break
    return claims


def first_sentence(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    m = re.search(r"([.!?])\s+[A-Z(]", s)
    if m:
        s = s[: m.start() + 1]
    if len(s) > max_chars:
        cut = s[: max_chars - 1].rstrip()
        sp = cut.rfind(" ")
        if sp > max_chars * 0.6:
            cut = cut[:sp]
        s = cut + "…"
    return s


def build_diagnosis(claim: dict) -> dict:
    """Return {brief, detail} strings explaining what's wrong with the claim.

    Draws on the worst-verdict sub-claim's `nuance` plus the verdict-appropriate
    attestation check (`closest_adjacent`, `indirect_attribution_check`,
    `out_of_context_check`) and any paper/claim value drift. `brief` is suitable
    for a one-line sidebar hint; `detail` is the 2-3 sentence popup summary.
    """
    overall = claim.get("overall_verdict") or "PENDING"
    sub_claims = claim.get("sub_claims") or []
    attestation = claim.get("attestation") or {}

    if overall == "CONFIRMED":
        return {"brief": "", "detail": ""}

    if overall == "PENDING":
        flag = claim.get("overall_flag") or ""
        reason = flag if flag and flag != "—" else "paywall or fetch failure"
        return {
            "brief": "Source PDF unavailable",
            "detail": (
                f"Not yet adjudicated — {reason}. "
                "Drop the source PDF into pdfs/<citekey>.pdf and re-run "
                "`/paper-trail <pdf> --recheck` to ground it."
            ),
        }

    # Pick the most-severe problem sub-claim.
    problem = None
    worst_sev = 99
    for sc in sub_claims:
        sv = sc.get("verdict") or "PENDING"
        if sv == "CONFIRMED":
            continue
        sev = VERDICT_SEVERITY.get(sv, 99)
        if sev < worst_sev:
            worst_sev = sev
            problem = sc
    if problem is None and sub_claims:
        problem = sub_claims[0]

    nuance = (problem.get("nuance") if problem else "") or ""
    paper_val = problem.get("paper_value") if problem else None
    claim_val = problem.get("claim_value") if problem else None

    # Brief: prefer drift values for OVERSTATED/OVERGENERAL, else first sentence of nuance.
    brief = ""
    has_drift = paper_val is not None and claim_val is not None and str(paper_val) != str(claim_val)
    if has_drift and overall in ("OVERSTATED", "OVERSTATED_MILD", "OVERGENERAL", "CONFIRMED_WITH_MINOR"):
        brief = f"Paper: {str(paper_val)[:70]} · Claim: {str(claim_val)[:70]}"
    else:
        brief = first_sentence(nuance, 160)
    if not brief:
        brief = VERDICT_LABEL.get(overall, overall)

    # Detail: full nuance + relevant attestation context.
    detail_parts: list[str] = []
    if nuance:
        detail_parts.append(nuance)
    if overall in ("CONTRADICTED", "UNSUPPORTED"):
        ca = (attestation.get("closest_adjacent") or "").strip()
        if ca:
            detail_parts.append(f"Closest passage found: {ca}")
    elif overall in ("MISATTRIBUTED", "INDIRECT_SOURCE"):
        ia = (attestation.get("indirect_attribution_check") or "").strip()
        if ia:
            detail_parts.append(ia)
    elif overall == "CITED_OUT_OF_CONTEXT":
        oc = (attestation.get("out_of_context_check") or "").strip()
        if oc:
            detail_parts.append(oc)
    detail = " ".join(p for p in detail_parts if p).strip()
    if not detail:
        detail = brief

    return {"brief": brief, "detail": detail}


def build_claim_summary(claim: dict) -> dict:
    """One-shot summary for the sidebar: verdict, pill color, preview, diagnosis."""
    overall = claim.get("overall_verdict") or "PENDING"
    flag = claim.get("overall_flag") or ""
    text = (claim.get("claim_text") or "").strip()
    preview = text[:160] + ("…" if len(text) > 160 else "")
    search_prefix = re.sub(r"\s+", " ", text[:80]).strip()
    diag = build_diagnosis(claim)
    return {
        "claim_id": claim.get("claim_id", ""),
        "citekey": claim.get("citekey", ""),
        "verdict": overall,
        "verdict_label": VERDICT_LABEL.get(overall, overall),
        "verdict_color": VERDICT_COLOR.get(overall, "#9ca3af"),
        "flag": flag,
        "preview": preview,
        "search_prefix": search_prefix,
        "section": claim.get("manuscript_section", ""),
        "severity": VERDICT_SEVERITY.get(overall, 99),
        "diagnosis_brief": diag["brief"],
        "diagnosis_detail": diag["detail"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--claims-dir", default="",
                    help="path (relative to run-dir) of verdict JSONs. Auto-detects ledger/claims then data/claims if blank.")
    ap.add_argument("--bib", default="refs.bib", help="bib filename relative to run-dir")
    ap.add_argument("--pdf", default="input-paper.pdf",
                    help="PDF filename relative to run-dir; inlined by default so demo.html works from file:// everywhere")
    ap.add_argument("--external-pdf", action="store_true",
                    help="Don't inline the PDF. demo.html will fetch it as a sibling file (requires Firefox for file://, or an HTTP server).")
    ap.add_argument("--output", default="demo.html", help="output filename relative to run-dir")
    args = ap.parse_args()

    run = args.run_dir.resolve()

    # refs: prefer refs.verified.bib if it exists.
    verified = run / "refs.verified.bib"
    bib_path = verified if verified.exists() else run / args.bib
    refs = parse_refs_bib(bib_path)

    claims = load_claims(run, args.claims_dir)

    # index: refnum -> [claim_id], citekey -> refnum
    refnum_to_claims: dict[int, list[str]] = {}
    citekey_to_refnum: dict[str, int] = {}
    for ref in refs.values():
        rn = ref.get("refnum")
        if isinstance(rn, int):
            citekey_to_refnum[ref["citekey"]] = rn
    for c in claims:
        ck = c.get("citekey")
        rn = citekey_to_refnum.get(ck)
        if rn is not None:
            refnum_to_claims.setdefault(rn, []).append(c["claim_id"])

    summaries = [build_claim_summary(c) for c in claims]
    summaries.sort(key=lambda s: (s["severity"], s["claim_id"]))

    # verdict counts
    counts: dict[str, int] = {}
    for c in claims:
        v = c.get("overall_verdict") or "PENDING"
        counts[v] = counts.get(v, 0) + 1

    # header metadata from ledger.md frontmatter (best effort)
    paper_title = ""
    paper_doi = ""
    led = run / "ledger.md"
    if led.exists():
        led_text = led.read_text()
        m = re.search(r'title:\s*"?([^"\n]+?)"?\s*$', led_text, re.MULTILINE)
        if m:
            paper_title = m.group(1).strip()
        m = re.search(r'doi:\s*([^\s]+)', led_text)
        if m:
            paper_doi = m.group(1).strip()

    # PDF source — inline as base64 by default so demo.html works in every browser from file://.
    pdf_path = run / args.pdf
    pdf_data_url = ""
    pdf_url = args.pdf
    if pdf_path.exists() and not args.external_pdf:
        with pdf_path.open("rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        pdf_data_url = f"data:application/pdf;base64,{b64}"
        pdf_url = ""  # JS will prefer pdfDataUrl when set
    elif not pdf_path.exists():
        print(f"warning: {pdf_path} not found — demo.html will try to fetch '{args.pdf}' at runtime")

    data = {
        "refs": refs,
        "refnumToClaimIds": {str(k): v for k, v in refnum_to_claims.items()},
        "citekeyToRefnum": citekey_to_refnum,
        "claimsById": {c["claim_id"]: c for c in claims},
        "summaries": summaries,
        "verdictCounts": counts,
        "verdictColors": VERDICT_COLOR,
        "verdictLabels": VERDICT_LABEL,
        "pdfUrl": pdf_url,
        "pdfDataUrl": pdf_data_url,
        "pdfjsBase": PDFJS_BASE,
    }

    doi_link = ""
    if paper_doi:
        doi_link = f'<a href="https://doi.org/{escape(paper_doi)}" target="_blank">DOI: {escape(paper_doi)}</a>'

    # Escape </ so that any literal "</script>" inside claim text can't break out of the <script> tag.
    data_json = json.dumps(data, default=str).replace("</", "<\\/")

    html = HTML_TEMPLATE.format(
        title=escape(paper_title or "paper-trail audit"),
        doi_link=doi_link,
        pdfjs_base=PDFJS_BASE,
        data_json=data_json,
    )

    out = run / args.output
    out.write_text(html)
    print(f"wrote {out}")
    print(f"claims: {len(claims)} · refs with claims: {len(refnum_to_claims)}")
    print(f"verdict counts: {counts}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — paper-trail</title>
<style>
  :root {{
    --bg: #fafaf9;
    --panel: #ffffff;
    --border: #e2e8f0;
    --border-strong: #cbd5e1;
    --text: #1c1917;
    --text-muted: #64748b;
    --accent: #1e293b;
    --hover: #f1f5f9;
    --sidebar-width: 420px;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    display: flex;
    flex-direction: column;
  }}
  header {{
    background: var(--accent);
    color: #f8fafc;
    padding: 0.75rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
  }}
  header h1 {{ margin: 0; font-size: 1.05rem; font-weight: 600; flex: 1;
               overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  header .doi a {{ color: #93c5fd; font-size: 0.8rem; text-decoration: none; }}
  header .doi a:hover {{ text-decoration: underline; }}
  header .counts {{ font-size: 0.8rem; opacity: 0.85; white-space: nowrap; }}

  main.viewer {{
    flex: 1;
    display: flex;
    min-height: 0;
  }}

  /* PDF panel */
  .pdf-panel {{
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background: #404040;
  }}
  .pdf-toolbar {{
    background: #1f2937;
    color: #f8fafc;
    padding: 0.35rem 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    border-bottom: 1px solid #111827;
  }}
  .pdf-toolbar button {{
    background: #374151;
    color: #f8fafc;
    border: 1px solid #4b5563;
    border-radius: 4px;
    padding: 0.2rem 0.55rem;
    font-size: 0.8rem;
    cursor: pointer;
  }}
  .pdf-toolbar button:hover {{ background: #4b5563; }}
  .pdf-toolbar input[type=number] {{
    width: 3.5rem;
    background: #111827;
    color: #f8fafc;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 0.15rem 0.4rem;
    font-size: 0.8rem;
  }}
  .pdf-toolbar .sep {{ width: 1px; height: 1.2rem; background: #4b5563; }}
  .pdf-toolbar .status {{ color: #9ca3af; font-size: 0.75rem; margin-left: auto; }}

  #pdf-pages {{
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }}
  .page-wrap {{
    position: relative;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    background: white;
  }}
  .page-wrap canvas {{ display: block; }}
  .page-wrap .textLayer {{
    position: absolute; inset: 0; overflow: hidden; opacity: 1;
    line-height: 1; pointer-events: auto;
  }}
  .page-wrap .textLayer > span {{
    color: transparent;
    position: absolute;
    white-space: pre;
    cursor: text;
    transform-origin: 0% 0%;
  }}
  .page-wrap .textLayer .cite-marker {{
    color: transparent;
    cursor: pointer;
    background: transparent;
    border-radius: 2px;
    transition: background 0.15s;
  }}
  .page-wrap .textLayer .cite-marker::after {{
    content: "";
    position: absolute;
    inset: -1px -1px -2px -1px;
    border-bottom: 2px solid var(--cite-color, #94a3b8);
    pointer-events: none;
  }}
  .page-wrap .textLayer .cite-marker:hover::after {{
    border-bottom-width: 3px;
    background: rgba(245, 158, 11, 0.12);
  }}
  .page-wrap .textLayer .cite-marker.active::after {{
    border-bottom: 2px solid #f59e0b;
    background: rgba(245, 158, 11, 0.22);
  }}
  .page-wrap .textLayer .sentence-highlight {{
    background: rgba(252, 211, 77, 0.35);
    border-radius: 2px;
    box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.4);
  }}

  /* Sidebar */
  aside.sidebar {{
    width: var(--sidebar-width);
    flex-shrink: 0;
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }}
  .sidebar-header {{
    padding: 0.6rem 0.85rem;
    border-bottom: 1px solid var(--border);
    background: #f8fafc;
  }}
  .sidebar-header h2 {{
    margin: 0 0 0.4rem 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text);
  }}
  .sidebar-search {{
    width: 100%;
    padding: 0.4rem 0.55rem;
    border: 1px solid var(--border-strong);
    border-radius: 4px;
    font-size: 0.8rem;
    background: white;
  }}
  .verdict-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.45rem;
  }}
  .legend-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.45rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: white;
    font-size: 0.7rem;
    cursor: pointer;
    user-select: none;
  }}
  .legend-chip.off {{ opacity: 0.4; }}
  .legend-chip .swatch {{
    width: 9px; height: 9px; border-radius: 2px;
  }}

  #claim-list {{
    flex: 1;
    overflow-y: auto;
    padding: 0.25rem 0;
  }}
  .claim-row {{
    padding: 0.55rem 0.85rem;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    transition: background 0.1s;
    position: relative;
  }}
  .claim-row:hover {{ background: var(--hover); }}
  .claim-row.active {{ background: #fef3c7; border-left: 3px solid #f59e0b; padding-left: calc(0.85rem - 3px); }}
  .claim-row.hidden {{ display: none; }}
  .claim-row-top {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }}
  .verdict-pill {{
    display: inline-block;
    padding: 0.1rem 0.45rem;
    border-radius: 10px;
    color: white;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }}
  .verdict-pill.big {{ font-size: 0.75rem; padding: 0.22rem 0.6rem; }}
  .flag-pill {{
    display: inline-block;
    padding: 0.1rem 0.4rem;
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
  }}
  .claim-meta {{
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  .claim-refnum {{
    display: inline-block;
    font-weight: 600;
    color: #334155;
    background: #e2e8f0;
    padding: 0 0.3rem;
    border-radius: 3px;
  }}
  .details-btn {{
    margin-left: auto;
    background: transparent;
    border: 1px solid var(--border-strong);
    color: var(--text-muted);
    border-radius: 4px;
    width: 22px;
    height: 22px;
    font-size: 0.7rem;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }}
  .details-btn:hover {{ background: white; color: var(--accent); border-color: var(--accent); }}
  .claim-preview {{
    font-size: 0.78rem;
    color: #334155;
    line-height: 1.35;
  }}
  .claim-diagnosis {{
    font-size: 0.74rem;
    color: #475569;
    line-height: 1.35;
    padding: 0.3rem 0.5rem;
    background: #fff7ed;
    border-left: 3px solid var(--diag-color, #f59e0b);
    border-radius: 0 3px 3px 0;
    margin-top: 0.15rem;
  }}
  .claim-diagnosis::before {{
    content: "▸ ";
    color: var(--diag-color, #f59e0b);
    font-weight: 700;
  }}
  .claim-section {{
    font-size: 0.68rem;
    color: var(--text-muted);
    font-style: italic;
  }}
  .mismatch-badge {{
    font-size: 0.7rem;
    color: #92400e;
    background: #fef3c7;
    border: 1px solid #fcd34d;
    padding: 0.2rem 0.45rem;
    border-radius: 3px;
    margin-top: 0.15rem;
  }}

  .diagnosis-box {{
    border-left: 4px solid var(--diag-color, #f59e0b);
    background: #fff7ed;
    padding: 0.7rem 0.9rem;
    border-radius: 0 4px 4px 0;
    margin-top: 0.3rem;
  }}
  .diagnosis-box .diagnosis-brief {{
    font-size: 0.88rem;
    font-weight: 600;
    color: #334155;
    line-height: 1.4;
  }}
  .diagnosis-box .diagnosis-detail {{
    font-size: 0.82rem;
    color: #475569;
    line-height: 1.5;
    margin-top: 0.4rem;
  }}

  /* Popup */
  .popup-backdrop {{
    position: fixed; inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }}
  .popup-backdrop.open {{ display: flex; }}
  #popup {{
    background: white;
    border-radius: 8px;
    max-width: 640px;
    width: calc(100% - 2rem);
    max-height: 85vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
  }}
  .popup-head {{
    padding: 0.9rem 1.1rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}
  .popup-head .spacer {{ flex: 1; }}
  .popup-close {{
    background: transparent;
    border: none;
    font-size: 1.3rem;
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0.2rem 0.45rem;
    border-radius: 4px;
  }}
  .popup-close:hover {{ background: var(--hover); color: var(--text); }}
  .popup-body {{
    overflow-y: auto;
    padding: 0.75rem 1.1rem 1.1rem 1.1rem;
  }}
  .popup-section {{ margin-top: 1rem; }}
  .popup-section:first-child {{ margin-top: 0; }}
  .popup-section h3 {{
    font-size: 0.7rem; font-weight: 600; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin: 0 0 0.4rem 0;
  }}
  .ref-meta {{ font-size: 0.85rem; }}
  .ref-title {{ font-weight: 600; }}
  .ref-authors {{ color: var(--text-muted); font-size: 0.78rem; }}
  .ref-venue {{ color: var(--text-muted); font-style: italic; font-size: 0.78rem; }}
  .ref-link a {{ font-size: 0.75rem; color: #0369a1; }}
  .claim-text-box {{
    font-size: 0.85rem; font-style: italic;
    background: #f8fafc;
    border-left: 3px solid #94a3b8;
    padding: 0.55rem 0.75rem;
    margin: 0.3rem 0 0 0;
  }}
  .subclaim {{
    margin: 0.5rem 0;
    padding: 0.5rem 0.7rem;
    background: #fafafa;
    border-radius: 4px;
    border: 1px solid var(--border);
  }}
  .subclaim-head {{
    display: flex; gap: 0.4rem; align-items: center; margin-bottom: 0.25rem;
    flex-wrap: wrap;
  }}
  .subclaim-id {{ font-size: 0.7rem; color: var(--text-muted); font-family: monospace; }}
  .subclaim-text {{ font-size: 0.82rem; color: #334155; }}
  .drift {{ margin: 0.35rem 0; font-size: 0.75rem; color: var(--text-muted); }}
  .drift code {{ background: #fef9c3; padding: 1px 4px; border-radius: 3px; }}
  .ev {{
    font-size: 0.75rem; color: #475569;
    margin: 0.3rem 0; padding-left: 0.6rem;
    border-left: 2px solid var(--border-strong);
  }}
  .ev-loc {{ font-family: monospace; color: var(--text-muted); font-size: 0.7rem; }}
  .ev-snip {{ display: block; margin-top: 0.15rem; font-style: italic; }}
  .remediation {{
    margin-top: 0.75rem; padding: 0.55rem 0.75rem;
    background: #fef3c7;
    border-left: 3px solid #f59e0b;
    border-radius: 0 4px 4px 0;
  }}
  .rem-cat {{ font-size: 0.7rem; font-weight: 700; color: #92400e; text-transform: uppercase; }}
  .rem-edit {{ font-size: 0.8rem; color: #422006; margin-top: 0.25rem; }}

  .empty-state {{
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
  }}
  .loading-state {{
    padding: 2rem 1rem;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
  }}

  @media (max-width: 900px) {{
    main.viewer {{ flex-direction: column; }}
    aside.sidebar {{ width: 100%; max-height: 45vh; border-left: none; border-top: 1px solid var(--border); }}
  }}

  /* Help popup */
  .help-btn {{
    background: #f8fafc;
    color: var(--accent);
    border: 1px solid #f8fafc;
    border-radius: 999px;
    padding: 0.22rem 0.7rem;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    line-height: 1;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }}
  .help-btn:hover {{ background: #e2e8f0; }}
  .help-btn .help-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: var(--accent);
    color: #f8fafc;
    font-size: 0.7rem;
    font-weight: 700;
  }}

  #help-popup {{
    background: white;
    border-radius: 8px;
    max-width: 560px;
    width: calc(100% - 2rem);
    max-height: 85vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
  }}
  .help-head {{
    padding: 0.85rem 1.05rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .help-head h2 {{ margin: 0; font-size: 1rem; font-weight: 600; flex: 1; }}
  .help-body {{
    overflow-y: auto;
    padding: 0.85rem 1.05rem 1.05rem 1.05rem;
    font-size: 0.85rem;
    color: #334155;
  }}
  .help-body h3 {{
    font-size: 0.7rem; font-weight: 600; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em;
    margin: 0.9rem 0 0.35rem 0;
  }}
  .help-body h3:first-child {{ margin-top: 0; }}
  .help-body ul {{ margin: 0.25rem 0; padding-left: 1.15rem; }}
  .help-body li {{ margin: 0.3rem 0; line-height: 1.45; }}
  .help-body code {{
    background: #f1f5f9; padding: 1px 4px; border-radius: 3px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.8em;
  }}
  .help-body .kbd {{
    display: inline-block; padding: 0 0.3rem;
    border: 1px solid var(--border-strong); border-bottom-width: 2px;
    border-radius: 3px; background: #f8fafc;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.78rem;
  }}
  .verdict-guide {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.4rem 0.6rem;
    align-items: start;
  }}
  .verdict-guide .vg-desc {{
    font-size: 0.8rem;
    color: #475569;
    line-height: 1.4;
  }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="doi">{doi_link}</div>
  <div class="counts" id="counts"></div>
  <button class="help-btn" id="help-btn" title="How to use this viewer" aria-label="help"><span class="help-icon">?</span>Help</button>
</header>

<main class="viewer">
  <div class="pdf-panel">
    <div class="pdf-toolbar">
      <button id="zoom-out" title="Zoom out">−</button>
      <button id="zoom-in" title="Zoom in">+</button>
      <span class="sep"></span>
      <button id="page-prev" title="Previous page">↑</button>
      Page <input type="number" id="page-input" min="1" value="1"> / <span id="page-total">?</span>
      <button id="page-next" title="Next page">↓</button>
      <span class="status" id="pdf-status">loading PDF…</span>
    </div>
    <div id="pdf-pages">
      <div class="loading-state">Loading PDF…<br><small>If nothing appears, the browser may be blocking local file fetches.<br>Try Firefox, or run <code>python3 -m http.server</code> in this directory.</small></div>
    </div>
  </div>

  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>Claim ledger · <span id="visible-count"></span></h2>
      <input type="text" class="sidebar-search" id="search" placeholder="filter by text, citekey, or claim id">
      <div class="verdict-legend" id="legend"></div>
    </div>
    <div id="claim-list"><div class="loading-state">Loading claims…</div></div>
  </aside>
</main>

<div class="popup-backdrop" id="popup-backdrop">
  <div id="popup" role="dialog" aria-modal="true"></div>
</div>

<div class="popup-backdrop" id="help-backdrop">
  <div id="help-popup" role="dialog" aria-modal="true" aria-labelledby="help-title">
    <div class="help-head">
      <h2 id="help-title">How to use this viewer</h2>
      <button class="popup-close" id="help-close" aria-label="close">×</button>
    </div>
    <div class="help-body" id="help-body"></div>
  </div>
</div>

<script src="{pdfjs_base}/pdf.min.js"></script>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc = "{pdfjs_base}/pdf.worker.min.js";

const DATA = {data_json};
window.__DATA__ = DATA; // for debugging

const summaries = DATA.summaries;
const refnumToClaimIds = DATA.refnumToClaimIds;
const citekeyToRefnum = DATA.citekeyToRefnum;
const refs = DATA.refs;
const claimsById = DATA.claimsById;
const COLORS = DATA.verdictColors;
const LABELS = DATA.verdictLabels;

// Per-page indexes used for citation-marker detection and claim-sentence highlight.
// citeMarkersByPage: pageNum -> [marker entries]
// claimPageIndex:    claimId -> page+charStart info
// pageTextByNum:     pageNum -> lowercased concatenated text
// pageSpanIndexByNum pageNum -> span char-range entries
const citeMarkersByPage = new Map();
const claimPageIndex = new Map();
const pageTextByNum = new Map();
const pageSpanIndexByNum = new Map();

let activeClaimId = null;
const hiddenVerdicts = new Set(); // verdicts the user toggled off

// First "Abstract" heading location across the rendered PDF. Numeric superscripts
// that appear before it are author-affiliation markers, not real citations — we
// use this to suppress false positives on the title/author block.
let firstAbstractPage = null;
let firstAbstractCharStart = -1;

// ------- Header counts --------
(function renderCounts() {{
  const counts = DATA.verdictCounts;
  const total = summaries.length;
  const parts = [];
  for (const [v, n] of Object.entries(counts)) {{
    if (!n) continue;
    parts.push(`<span title="${{LABELS[v]||v}}">${{n}} ${{shortLabel(v)}}</span>`);
  }}
  document.getElementById('counts').innerHTML = `${{total}} claims · ` + parts.join(" · ");
}})();

function shortLabel(v) {{
  return (LABELS[v]||v).replace(/\s*\(.+\)$/, "").toLowerCase();
}}

// ------- Legend (filterable) --------
(function renderLegend() {{
  const legend = document.getElementById('legend');
  const counts = DATA.verdictCounts;
  const ordered = Object.keys(counts).sort((a, b) => (summaries.find(s=>s.verdict===a)?.severity ?? 99) - (summaries.find(s=>s.verdict===b)?.severity ?? 99));
  for (const v of ordered) {{
    const chip = document.createElement('span');
    chip.className = 'legend-chip';
    chip.dataset.verdict = v;
    chip.innerHTML = `<span class="swatch" style="background:${{COLORS[v]||'#9ca3af'}}"></span>${{LABELS[v]||v}} · ${{counts[v]}}`;
    chip.addEventListener('click', () => {{
      if (hiddenVerdicts.has(v)) {{
        hiddenVerdicts.delete(v);
        chip.classList.remove('off');
      }} else {{
        hiddenVerdicts.add(v);
        chip.classList.add('off');
      }}
      applyFilters();
    }});
    legend.appendChild(chip);
  }}
}})();

// ------- Sidebar claim list --------
function renderSidebar() {{
  const list = document.getElementById('claim-list');
  list.innerHTML = "";
  if (!summaries.length) {{
    list.innerHTML = '<div class="empty-state">No claims in this run.</div>';
    return;
  }}
  for (const s of summaries) {{
    const row = document.createElement('div');
    row.className = 'claim-row';
    row.dataset.claimId = s.claim_id;
    row.dataset.verdict = s.verdict;
    const refnum = citekeyToRefnum[s.citekey];
    const refnumHtml = refnum != null ? `<span class="claim-refnum">[${{refnum}}]</span>` : "";
    const flagHtml = s.flag && s.flag !== '—' ? `<span class="flag-pill">${{escapeHtml(s.flag)}}</span>` : "";
    const sectionHtml = s.section ? `<div class="claim-section">${{escapeHtml(s.section)}}</div>` : "";
    const diagHtml = s.diagnosis_brief
      ? `<div class="claim-diagnosis" style="--diag-color:${{s.verdict_color}}">${{escapeHtml(s.diagnosis_brief)}}</div>`
      : "";
    row.innerHTML = `
      <div class="claim-row-top">
        <span class="verdict-pill" style="background:${{s.verdict_color}}">${{escapeHtml(s.verdict_label)}}</span>
        ${{flagHtml}}
        <span class="claim-meta">${{escapeHtml(s.claim_id)}} · ${{refnumHtml}} <code>${{escapeHtml(s.citekey)}}</code></span>
        <button class="details-btn" title="details" aria-label="details">ⓘ</button>
      </div>
      <div class="claim-preview">${{escapeHtml(s.preview)}}</div>
      ${{diagHtml}}
      ${{sectionHtml}}
    `;
    row.addEventListener('click', (e) => {{
      if (e.target.closest('.details-btn')) return;
      focusClaim(s.claim_id, {{ scrollPdf: true }});
    }});
    row.querySelector('.details-btn').addEventListener('click', (e) => {{
      e.stopPropagation();
      showPopup(s.claim_id);
    }});
    list.appendChild(row);
  }}
  updateVisibleCount();
}}

function applyFilters() {{
  const q = document.getElementById('search').value.trim().toLowerCase();
  const rows = document.querySelectorAll('.claim-row');
  for (const row of rows) {{
    const s = summaries.find(x => x.claim_id === row.dataset.claimId);
    if (!s) continue;
    let hide = false;
    if (hiddenVerdicts.has(s.verdict)) hide = true;
    if (q && !(`${{s.claim_id}} ${{s.citekey}} ${{s.preview}} ${{s.section}}`.toLowerCase().includes(q))) hide = true;
    row.classList.toggle('hidden', hide);
  }}
  updateVisibleCount();
}}

function updateVisibleCount() {{
  const visible = document.querySelectorAll('.claim-row:not(.hidden)').length;
  document.getElementById('visible-count').textContent = `${{visible}} of ${{summaries.length}}`;
}}

document.getElementById('search').addEventListener('input', applyFilters);

// ------- Popup --------
const backdrop = document.getElementById('popup-backdrop');
const popup = document.getElementById('popup');

function showPopup(claimId) {{
  const claim = claimsById[claimId];
  if (!claim) return;
  const refnum = citekeyToRefnum[claim.citekey];
  const ref = refs[claim.citekey] || null;
  const summary = summaries.find(s => s.claim_id === claimId);
  popup.innerHTML = renderPopupContent(claim, ref, refnum, summary);
  popup.querySelector('.popup-close').addEventListener('click', hidePopup);
  backdrop.classList.add('open');
}}
function hidePopup() {{ backdrop.classList.remove('open'); }}
backdrop.addEventListener('click', (e) => {{ if (e.target === backdrop) hidePopup(); }});
document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') {{ hidePopup(); hideHelp(); }} }});

function renderPopupContent(claim, ref, refnum, summary) {{
  const v = claim.overall_verdict || 'PENDING';
  const color = COLORS[v] || '#9ca3af';
  const label = LABELS[v] || v;
  const flag = claim.overall_flag || '';
  const diagBrief = summary && summary.diagnosis_brief || '';
  const diagDetail = summary && summary.diagnosis_detail || '';

  let refHtml = '';
  if (ref) {{
    const link = ref.doi ? `https://doi.org/${{ref.doi}}` : (ref.arxiv ? `https://arxiv.org/abs/${{ref.arxiv}}` : '');
    refHtml = `
      <div class="popup-section">
        <h3>Cited source${{refnum != null ? ' [' + refnum + ']' : ''}}</h3>
        <div class="ref-meta">
          <div class="ref-title">${{escapeHtml(ref.title || '')}}</div>
          <div class="ref-authors">${{escapeHtml(ref.authors || '')}}</div>
          <div class="ref-venue">${{escapeHtml(ref.venue || '')}} (${{escapeHtml(ref.year || '')}})</div>
          ${{link ? `<div class="ref-link"><a href="${{link}}" target="_blank">${{escapeHtml(link)}}</a></div>` : ''}}
        </div>
      </div>
    `;
  }}

  let subHtml = '';
  for (const sc of (claim.sub_claims || [])) {{
    const sv = sc.verdict || 'PENDING';
    const scColor = COLORS[sv] || '#9ca3af';
    const scLabel = LABELS[sv] || sv;
    let driftHtml = '';
    if (sc.paper_value != null || sc.claim_value != null) {{
      driftHtml = `<div class="drift"><strong>Paper:</strong> <code>${{escapeHtml(String(sc.paper_value ?? '—'))}}</code> · <strong>Claim:</strong> <code>${{escapeHtml(String(sc.claim_value ?? '—'))}}</code></div>`;
    }}
    let evHtml = '';
    for (const ev of (sc.evidence || [])) {{
      evHtml += `<div class="ev"><span class="ev-loc">${{escapeHtml(String(ev.section || '?'))}} L${{escapeHtml(String(ev.line ?? '?'))}}</span><span class="ev-snip">"${{escapeHtml(String(ev.snippet || ''))}}"</span></div>`;
    }}
    if (!(sc.evidence || []).length && sc.nuance) {{
      evHtml = `<div class="ev"><em>${{escapeHtml(sc.nuance)}}</em></div>`;
    }}
    subHtml += `
      <div class="subclaim">
        <div class="subclaim-head">
          <span class="verdict-pill" style="background:${{scColor}}">${{escapeHtml(scLabel)}}</span>
          <span class="subclaim-id">${{escapeHtml(sc.sub_claim_id || '')}}</span>
        </div>
        <div class="subclaim-text">${{escapeHtml(sc.text || '')}}</div>
        ${{driftHtml}}
        ${{evHtml}}
      </div>
    `;
  }}

  const rem = claim.remediation;
  let remHtml = '';
  if (rem && rem.category) {{
    remHtml = `
      <div class="remediation">
        <div class="rem-cat">${{escapeHtml(rem.category)}}</div>
        <div class="rem-edit">${{escapeHtml(rem.suggested_edit || '')}}</div>
      </div>
    `;
  }}

  return `
    <div class="popup-head">
      <span class="verdict-pill big" style="background:${{color}}">${{escapeHtml(label)}}</span>
      ${{flag && flag !== '—' ? `<span class="flag-pill">${{escapeHtml(flag)}}</span>` : ''}}
      <span class="claim-meta">${{escapeHtml(claim.claim_id)}} · <code>${{escapeHtml(claim.citekey)}}</code>${{claim.manuscript_section ? ' · ' + escapeHtml(claim.manuscript_section) : ''}}</span>
      <span class="spacer"></span>
      <button class="popup-close" aria-label="close">×</button>
    </div>
    <div class="popup-body">
      ${{refHtml}}
      <div class="popup-section">
        <h3>Manuscript claim</h3>
        <div class="claim-text-box">"${{escapeHtml(claim.claim_text || '')}}"</div>
      </div>
      ${{diagBrief ? `
      <div class="popup-section">
        <h3>What's wrong</h3>
        <div class="diagnosis-box" style="--diag-color:${{color}}">
          <div class="diagnosis-brief">${{escapeHtml(diagBrief)}}</div>
          ${{diagDetail && diagDetail !== diagBrief ? `<div class="diagnosis-detail">${{escapeHtml(diagDetail)}}</div>` : ''}}
        </div>
      </div>` : ''}}
      <div class="popup-section">
        <h3>Sub-claims · evidence</h3>
        ${{subHtml || '<div class="empty-state">No sub-claim evidence recorded (likely PENDING — source PDF unavailable).</div>'}}
      </div>
      ${{remHtml ? `<div class="popup-section"><h3>Suggested remediation</h3>${{remHtml}}</div>` : ''}}
    </div>
  `;
}}

// ------- Focus a claim (scroll PDF + highlight) --------
function focusClaim(claimId, opts = {{}}) {{
  const {{ scrollPdf = false, highlightSentence = true }} = opts;
  if (activeClaimId && activeClaimId !== claimId) {{
    document.querySelectorAll('.claim-row.active').forEach(r => r.classList.remove('active'));
    document.querySelectorAll('.cite-marker.active').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.sentence-highlight').forEach(el => el.classList.remove('sentence-highlight'));
  }}
  activeClaimId = claimId;
  const row = document.querySelector(`.claim-row[data-claim-id="${{claimId}}"]`);
  if (row) {{
    row.classList.add('active');
    row.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
  }}
  const claim = claimsById[claimId];
  if (!claim) return;
  const entry = claimPageIndex.get(claimId);

  if (scrollPdf && entry) {{
    scrollToPage(entry.page);
  }}

  if (highlightSentence) {{
    highlightSentenceForClaim(claimId);
    // also underline this refnum's markers within the claim's page
    const refnum = citekeyToRefnum[claim.citekey];
    if (refnum != null && entry) {{
      const pageWrap = document.querySelector(`.page-wrap[data-page="${{entry.page}}"]`);
      if (pageWrap) {{
        pageWrap.querySelectorAll(`.cite-marker[data-refnum="${{refnum}}"]`).forEach(el => el.classList.add('active'));
      }}
    }}
  }}
}}

function scrollToPage(pageNum) {{
  const el = document.querySelector(`.page-wrap[data-page="${{pageNum}}"]`);
  if (el) {{
    el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    document.getElementById('page-input').value = pageNum;
  }}
}}

// ------- PDF.js rendering --------
let pdfDoc = null;
let baseScale = 1.3;

async function loadPdf() {{
  const status = document.getElementById('pdf-status');
  // Prefer an inlined base64 PDF (works file:// everywhere); fall back to sibling-file fetch.
  try {{
    let task;
    if (DATA.pdfDataUrl) {{
      const bytes = dataUrlToBytes(DATA.pdfDataUrl);
      task = pdfjsLib.getDocument({{ data: bytes }});
    }} else {{
      task = pdfjsLib.getDocument(DATA.pdfUrl);
    }}
    pdfDoc = await task.promise;
  }} catch (e) {{
    status.textContent = "couldn't load PDF";
    const pagesEl = document.getElementById('pdf-pages');
    const srcNote = DATA.pdfDataUrl
      ? '(inlined PDF failed to decode — file may be corrupt)'
      : `expects <code>${{escapeHtml(DATA.pdfUrl)}}</code> next to this HTML. Use Firefox, or serve via <code>python3 -m http.server</code>.`;
    pagesEl.innerHTML = `<div class="empty-state"><strong>PDF failed to load.</strong><br><br>${{srcNote}}<br><br><small>${{escapeHtml(String(e && e.message || e))}}</small></div>`;
    return;
  }}
  document.getElementById('page-total').textContent = pdfDoc.numPages;
  document.getElementById('page-input').max = pdfDoc.numPages;
  status.textContent = `${{pdfDoc.numPages}} pages`;

  const pagesEl = document.getElementById('pdf-pages');
  pagesEl.innerHTML = "";

  for (let n = 1; n <= pdfDoc.numPages; n++) {{
    const wrap = document.createElement('div');
    wrap.className = 'page-wrap';
    wrap.dataset.page = n;
    pagesEl.appendChild(wrap);
    await renderPage(n, wrap);
  }}

  // now that pages are rendered, build claim → page index via text search
  indexClaimsToPages();
}}

async function renderPage(pageNum, wrap) {{
  const page = await pdfDoc.getPage(pageNum);
  const viewport = page.getViewport({{ scale: baseScale }});
  const canvas = document.createElement('canvas');
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  wrap.style.width = `${{canvas.width}}px`;
  wrap.style.height = `${{canvas.height}}px`;
  wrap.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  await page.render({{ canvasContext: ctx, viewport }}).promise;

  const textContent = await page.getTextContent();

  // text layer container
  const textLayer = document.createElement('div');
  textLayer.className = 'textLayer';
  textLayer.style.width = `${{canvas.width}}px`;
  textLayer.style.height = `${{canvas.height}}px`;
  textLayer.style.setProperty('--scale-factor', String(viewport.scale));
  wrap.appendChild(textLayer);

  await pdfjsLib.renderTextLayer({{
    textContentSource: textContent,
    container: textLayer,
    viewport,
    textDivs: [],
  }}).promise;

  // Build char-offset index for the page: concat every span's text with a single
  // space separator, tracking each span's [charStart, charEnd] in the concat.
  const allSpans = Array.from(textLayer.querySelectorAll('span'));
  const spanIndex = [];
  let concat = "";
  for (const span of allSpans) {{
    const t = span.textContent || "";
    const start = concat.length;
    concat += t;
    const end = concat.length;
    concat += " ";
    spanIndex.push({{ span, charStart: start, charEnd: end }});
  }}
  const pageLower = concat.toLowerCase();
  pageTextByNum.set(pageNum, pageLower);
  pageSpanIndexByNum.set(pageNum, spanIndex);

  // Locate the first "Abstract" heading we see; its position bounds the author block.
  if (firstAbstractPage === null) {{
    const m = pageLower.match(/\babstract\b/);
    if (m && m.index != null) {{
      firstAbstractPage = pageNum;
      firstAbstractCharStart = m.index;
    }}
  }}

  // Collect body-text stats for superscript detection. Use bounding-rect heights:
  // citation superscripts render at ~60-75% of body-text height.
  const heights = [];
  for (const {{ span }} of spanIndex) {{
    const r = span.getBoundingClientRect();
    if (r.height > 0 && (span.textContent || "").trim().length >= 3) heights.push(r.height);
  }}
  heights.sort((a, b) => a - b);
  const bodyHeight = heights.length ? heights[Math.floor(heights.length * 0.6)] : 0;
  const pageRect = textLayer.getBoundingClientRect();
  const marginTop = pageRect.top + pageRect.height * 0.06;
  const marginBottom = pageRect.top + pageRect.height * 0.94;

  // Detect citation markers with heuristics:
  //   1. text is purely a number (or numeric list/range)
  //   2. ALL numbers resolve to known refnums
  //   3. span is in the body area (not in top/bottom 6% margins — excludes page numbers)
  //   4. span's rendered height is clearly smaller than body text (superscript) OR
  //      it's a comma-separated list of numbers (common typesetting — these stay body-height)
  const markers = [];
  for (let ei = 0; ei < spanIndex.length; ei++) {{
    const entry = spanIndex[ei];
    const {{ span, charStart }} = entry;
    const txt = (span.textContent || "").trim();
    if (!txt || txt.length > 20) continue;
    const m = txt.match(/^[\-–,\s]*(\d{{1,3}}(?:\s*[\-–,]\s*\d{{1,3}})*)[\-–,\s]*$/);
    if (!m) continue;
    const nums = parseNumSequence(m[1]);
    if (!nums.length) continue;
    const valid = nums.filter(n => refnumToClaimIds[String(n)] && refnumToClaimIds[String(n)].length);
    if (!valid.length) continue;

    // Author-affiliation filter: numeric superscripts ahead of the "Abstract"
    // heading on the page that contains it are affiliation markers, not citations.
    if (firstAbstractPage === pageNum && charStart < firstAbstractCharStart) continue;

    const r = span.getBoundingClientRect();
    // Margin exclusion — page numbers in headers / footers are outside body area.
    if (r.top < marginTop || r.bottom > marginBottom) continue;

    // Size check: true superscripts are smaller than body text. Allow multi-number
    // lists (which typeset at body height) only if they contain more than one number.
    const isMultiList = nums.length > 1;
    const isSuperscript = bodyHeight > 0 && r.height > 0 && r.height < bodyHeight * 0.88;
    if (!isSuperscript && !isMultiList) continue;

    // Chemistry-isotope filter: a numeric superscript sitting directly against
    // an alphabetic character (e.g. 2H, 13C, 18F, 99mTc) is an isotope label,
    // not a citation. Telltale signal: the *next* span starts with a letter
    // and has near-zero horizontal gap on the same line. Citation superscripts
    // are always followed by word-space or punctuation.
    if (isSuperscript && !isMultiList) {{
      let adjacentLetter = false;
      for (let nj = ei + 1; nj < spanIndex.length && nj <= ei + 3; nj++) {{
        const nextSpan = spanIndex[nj].span;
        const nextTxt = (nextSpan.textContent || "");
        if (!nextTxt.trim()) continue; // skip empty / whitespace-only spans
        if (!/^[A-Za-z]/.test(nextTxt.trim())) break; // punctuation / digit → not isotope
        const nextRect = nextSpan.getBoundingClientRect();
        const gap = nextRect.left - r.right;
        const sameLine = Math.abs(r.top - nextRect.top) < bodyHeight * 1.5;
        const gapThreshold = Math.max(3, bodyHeight * 0.2);
        if (sameLine && gap < gapThreshold) adjacentLetter = true;
        break;
      }}
      if (adjacentLetter) continue;
    }}

    span.classList.add('cite-marker');
    span.dataset.refnum = String(valid[0]);
    span.dataset.allRefnums = valid.join(",");
    span.dataset.pageNum = String(pageNum);
    span.dataset.charStart = String(charStart);
    const claimIds = [];
    for (const n of valid) claimIds.push(...(refnumToClaimIds[String(n)] || []));
    span.dataset.claimIds = claimIds.join(",");
    const worst = worstVerdictForClaims(claimIds);
    span.style.setProperty('--cite-color', COLORS[worst] || '#94a3b8');
    span.addEventListener('click', (ev) => {{
      ev.stopPropagation();
      onCiteMarkerClick(pageNum, charStart, valid, claimIds);
    }});
    markers.push({{ refnum: valid[0], el: span, charStart, claimIds }});
  }}
  citeMarkersByPage.set(pageNum, markers);
}}

function parseNumSequence(s) {{
  const out = [];
  for (const part of s.split(",")) {{
    const p = part.trim();
    if (!p) continue;
    const range = p.split(/[\-–]/);
    if (range.length === 2) {{
      const a = parseInt(range[0], 10), b = parseInt(range[1], 10);
      if (!isNaN(a) && !isNaN(b) && a >= 1 && b >= 1 && b - a >= 0 && b - a < 20) {{
        for (let i = a; i <= b; i++) out.push(i);
      }}
    }} else {{
      const n = parseInt(p, 10);
      if (!isNaN(n) && n >= 1 && n <= 500) out.push(n);
    }}
  }}
  return out;
}}

function worstVerdictForClaims(claimIds) {{
  let worst = null;
  let worstSev = 99;
  for (const cid of claimIds) {{
    const c = claimsById[cid];
    if (!c) continue;
    const v = c.overall_verdict || 'PENDING';
    const sev = (summaries.find(s => s.claim_id === cid) || {{}}).severity ?? 99;
    if (sev < worstSev) {{ worstSev = sev; worst = v; }}
  }}
  return worst || 'PENDING';
}}

function onCiteMarkerClick(pageNum, charStart, refnums, claimIds) {{
  if (!claimIds.length) return;
  // Pick the claim whose manuscript sentence appears closest *before* this
  // marker on this page — that's the sentence that cites this reference here.
  // Fall back to any claim on this page, then any claim at all.
  let best = null;
  let bestDist = Infinity;
  for (const cid of claimIds) {{
    const entry = claimPageIndex.get(cid);
    if (!entry || entry.page !== pageNum) continue;
    const dist = charStart - entry.charStart;
    // prefer claim whose text starts before the marker (dist >= 0), with small positive distance
    const score = dist >= 0 ? dist : Math.abs(dist) + 10000;
    if (score < bestDist) {{ bestDist = score; best = cid; }}
  }}
  if (!best) {{
    // any claim on this page for this refnum, else first claim
    for (const cid of claimIds) {{
      const entry = claimPageIndex.get(cid);
      if (entry && entry.page === pageNum) {{ best = cid; break; }}
    }}
  }}
  if (!best) best = claimIds[0];
  focusClaim(best, {{ scrollPdf: false, highlightSentence: true }});
}}

function highlightSentenceForClaim(claimId) {{
  // Clear prior sentence highlight wherever it lives.
  document.querySelectorAll('.sentence-highlight').forEach(el => el.classList.remove('sentence-highlight'));
  const entry = claimPageIndex.get(claimId);
  if (!entry) return;
  const claim = claimsById[claimId];
  if (!claim) return;
  const spanIndex = pageSpanIndexByNum.get(entry.page);
  const pageText = pageTextByNum.get(entry.page);
  if (!spanIndex || !pageText) return;

  // Locate the sentence in the page text. Start from the claim's indexed start,
  // then extend to the next sentence boundary after including the cited markers.
  const claimText = (claim.claim_text || "").trim();
  // Use the raw (case-insensitive) lowercased prefix to find the start; then
  // extend forward until we pass the claim's full length OR hit a sentence end.
  const prefix = (entry.searchPrefix || "").toLowerCase();
  let start = -1;
  if (prefix.length >= 15) {{
    start = pageText.indexOf(prefix, Math.max(0, entry.charStart - 40));
    if (start < 0) start = pageText.indexOf(prefix);
  }}
  if (start < 0) return;
  // End = start + claim length, extended to the next '.' '!' '?' boundary (to
  // include the trailing citation marker) but not beyond another 200 chars.
  const targetLen = Math.min(claimText.length + 80, 400);
  let end = Math.min(pageText.length, start + targetLen);
  // extend to the nearest sentence-ending punctuation within a small window
  for (let i = start + claimText.length; i < Math.min(pageText.length, start + claimText.length + 120); i++) {{
    const ch = pageText[i];
    if (ch === '.' || ch === '!' || ch === '?') {{ end = i + 1; break; }}
  }}
  // Mark every span whose char range overlaps [start, end).
  for (const {{ span, charStart, charEnd }} of spanIndex) {{
    if (charEnd <= start) continue;
    if (charStart >= end) break;
    span.classList.add('sentence-highlight');
  }}
}}

// ------- Index claims → page --------
// Primary: text-search the claim's manuscript prefix in the PDF text.
// Fallback 1: sliding 4- and 3-word windows from the claim_text (handles
//   paraphrased or lightly-edited stored claim_text).
// Fallback 2: jump to the first citation marker we detected for this claim's
//   refnum — guarantees a landing point near where the ref is actually cited.
function indexClaimsToPages() {{
  for (const s of summaries) {{
    let found = findByPrefix(s.search_prefix);
    if (found) {{ found.matchMethod = "prefix"; }}
    if (!found) {{
      found = findByWordWindows(s.search_prefix || "", s.preview || "");
      if (found) found.matchMethod = "words";
    }}
    if (!found) {{
      found = findByRefnumMarker(s.citekey);
      if (found) found.matchMethod = "marker-only";
    }}
    if (found) claimPageIndex.set(s.claim_id, found);
  }}
  // After indexing, annotate sidebar rows that landed via the marker-only fallback —
  // those are likely upstream extractor bugs (the stored claim_text doesn't appear
  // verbatim or nearly-so in the paper body).
  for (const s of summaries) {{
    const entry = claimPageIndex.get(s.claim_id);
    const row = document.querySelector(`.claim-row[data-claim-id="${{s.claim_id}}"]`);
    if (!row) continue;
    if (!entry) {{
      row.dataset.matchMethod = "none";
      addMismatchBadge(row, "claim text not found in manuscript");
    }} else if (entry.matchMethod === "marker-only") {{
      row.dataset.matchMethod = "marker-only";
      addMismatchBadge(row, "claim text not located; landing on first citation marker");
    }}
  }}
}}

function addMismatchBadge(row, text) {{
  if (row.querySelector('.mismatch-badge')) return;
  const badge = document.createElement('div');
  badge.className = 'mismatch-badge';
  badge.textContent = `⚠ ${{text}}`;
  row.appendChild(badge);
}}

function findByPrefix(searchPrefix) {{
  if (!searchPrefix) return null;
  const prefix = searchPrefix.toLowerCase();
  for (const q of [prefix, prefix.slice(0, 60), prefix.slice(0, 40)]) {{
    if (q.length < 15) break;
    for (const [pnum, text] of pageTextByNum) {{
      const pos = text.indexOf(q);
      if (pos >= 0) return {{ page: pnum, charStart: pos, searchPrefix: q }};
    }}
  }}
  return null;
}}

function findByWordWindows(...sources) {{
  // Build a pool of meaningful word tokens from each source string; try sliding
  // 4-word windows (then 3-word) against each page, accept first match that also
  // contains at least one distinctive noun-like word (≥5 letters).
  const seen = new Set();
  const words = [];
  for (const src of sources) {{
    const toks = (src || "").toLowerCase().replace(/[^\w\s-]/g, " ").split(/\s+/).filter(Boolean);
    for (const t of toks) {{
      if (t.length < 3) continue;
      if (STOPWORDS.has(t)) continue;
      if (seen.has(t)) continue;
      seen.add(t);
      words.push(t);
    }}
  }}
  for (const size of [5, 4, 3]) {{
    for (let i = 0; i + size <= words.length; i++) {{
      const window = words.slice(i, i + size);
      // require at least one "content" word (≥5 chars) in this window
      if (!window.some(w => w.length >= 5)) continue;
      const q = window.join(" ");
      for (const [pnum, text] of pageTextByNum) {{
        // allow any whitespace between window words in the page text
        const re = new RegExp(window.map(escapeRegex).join("\\s+"), "i");
        const m = text.match(re);
        if (m && m.index != null) return {{ page: pnum, charStart: m.index, searchPrefix: m[0] }};
      }}
    }}
  }}
  return null;
}}

function findByRefnumMarker(citekey) {{
  const rn = citekeyToRefnum[citekey];
  if (rn == null) return null;
  const pages = [...citeMarkersByPage.keys()].sort((a, b) => a - b);
  for (const p of pages) {{
    const markers = citeMarkersByPage.get(p) || [];
    for (const m of markers) {{
      const matches = String(m.el.dataset.allRefnums || "").split(",").map(Number).includes(rn);
      if (matches) return {{ page: p, charStart: m.charStart, searchPrefix: "" }};
    }}
  }}
  return null;
}}

function escapeRegex(s) {{
  return s.replace(/[.*+?^${{}}()|[\]\\]/g, '\\$&');
}}

const STOPWORDS = new Set([
  "the","and","for","with","this","that","from","have","has","are","was","were",
  "not","but","any","all","can","use","used","using","one","two","three","also",
  "such","these","those","into","over","here","where","when","what","which",
  "into","been","which","their","there","than","then","its","it's","its'",
  "our","your","his","her","him","she","he","they","them","you","our","we",
  "et","al","etc","e.g.","i.e.","eg","ie","vs","versus","per",
  "been","being","seem","seems","seemed","appears","appear","appeared"
]);

// ------- Toolbar controls --------
document.getElementById('zoom-in').addEventListener('click', () => setZoom(baseScale * 1.15));
document.getElementById('zoom-out').addEventListener('click', () => setZoom(baseScale / 1.15));
document.getElementById('page-prev').addEventListener('click', () => {{
  const cur = currentPage();
  if (cur > 1) scrollToPage(cur - 1);
}});
document.getElementById('page-next').addEventListener('click', () => {{
  const cur = currentPage();
  if (pdfDoc && cur < pdfDoc.numPages) scrollToPage(cur + 1);
}});
document.getElementById('page-input').addEventListener('change', (e) => {{
  const n = parseInt(e.target.value, 10);
  if (!isNaN(n) && n >= 1 && pdfDoc && n <= pdfDoc.numPages) scrollToPage(n);
}});

function currentPage() {{
  const scroller = document.getElementById('pdf-pages');
  const wraps = scroller.querySelectorAll('.page-wrap');
  const top = scroller.getBoundingClientRect().top;
  for (const w of wraps) {{
    const r = w.getBoundingClientRect();
    if (r.bottom > top + 20) return parseInt(w.dataset.page, 10);
  }}
  return 1;
}}

async function setZoom(newScale) {{
  baseScale = Math.max(0.5, Math.min(3.0, newScale));
  if (!pdfDoc) return;
  const pagesEl = document.getElementById('pdf-pages');
  pagesEl.innerHTML = "";
  citeMarkersByPage.clear();
  pageTextByNum.clear();
  pageSpanIndexByNum.clear();
  claimPageIndex.clear();
  firstAbstractPage = null;
  firstAbstractCharStart = -1;
  for (let n = 1; n <= pdfDoc.numPages; n++) {{
    const wrap = document.createElement('div');
    wrap.className = 'page-wrap';
    wrap.dataset.page = n;
    pagesEl.appendChild(wrap);
    await renderPage(n, wrap);
  }}
  indexClaimsToPages();
}}

// ------- Helpers --------
function escapeHtml(s) {{
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}}[c]
  ));
}}

function dataUrlToBytes(dataUrl) {{
  const comma = dataUrl.indexOf(',');
  const b64 = dataUrl.slice(comma + 1);
  const binStr = atob(b64);
  const bytes = new Uint8Array(binStr.length);
  for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
  return bytes;
}}

// ------- Help popup --------
const VERDICT_DESC = {{
  CONFIRMED: "Source fully supports the claim.",
  CONFIRMED_WITH_MINOR: "Supported, with minor deviations (rounding, rewording).",
  OVERSTATED_MILD: "Claim is slightly stronger than the source supports.",
  OVERSTATED: "Claim is clearly stronger than the source supports.",
  OVERGENERAL: "Claim is broader than the specific source finding.",
  PARTIALLY_SUPPORTED: "Some sub-claims supported, others not.",
  CITED_OUT_OF_CONTEXT: "Source says it, but in a different sense or scope.",
  INDIRECT_SOURCE: "Cited work is itself citing the real source.",
  MISATTRIBUTED: "Attributed to the wrong paper.",
  UNSUPPORTED: "No evidence for the claim in the cited source.",
  CONTRADICTED: "Source actively contradicts the claim.",
  AMBIGUOUS: "Evidence unclear or conflicting.",
  PENDING: "Source PDF unavailable — not yet adjudicated.",
}};

const helpBackdrop = document.getElementById('help-backdrop');
const helpBody = document.getElementById('help-body');

function renderHelpBody() {{
  const counts = DATA.verdictCounts || {{}};
  const present = Object.keys(counts)
    .filter(v => counts[v])
    .sort((a, b) => ((summaries.find(s => s.verdict === a) || {{}}).severity ?? 99)
                  - ((summaries.find(s => s.verdict === b) || {{}}).severity ?? 99));
  const verdictRows = present.map(v => `
    <span class="verdict-pill" style="background:${{COLORS[v]||'#9ca3af'}}">${{escapeHtml(LABELS[v]||v)}}</span>
    <span class="vg-desc">${{escapeHtml(VERDICT_DESC[v] || '')}}</span>
  `).join("");
  helpBody.innerHTML = `
    <h3>Navigating the audit</h3>
    <ul>
      <li><strong>Click a claim row</strong> in the sidebar — the PDF jumps to that sentence and highlights it in yellow.</li>
      <li><strong>Click a numbered citation</strong> in the PDF (the colored underlines) — the sidebar scrolls to the matching claim.</li>
      <li><strong>Click the <span class="kbd">ⓘ</span> button</strong> on a row — opens full details: sub-claims, source evidence, and suggested edits.</li>
      <li><strong>Filter by verdict</strong> — click the colored chips at the top of the sidebar to hide a category; click again to re-show.</li>
      <li><strong>Search</strong> — the input above the list filters by claim text, citekey, or claim id.</li>
      <li><strong>Close popups</strong> with <span class="kbd">Esc</span> or by clicking the dimmed backdrop.</li>
    </ul>
    <h3>Verdicts in this audit</h3>
    <div class="verdict-guide">${{verdictRows || '<span class="vg-desc">(no claims recorded)</span>'}}</div>
    <h3>Color coding in the PDF</h3>
    <ul>
      <li>Each citation number is <strong>underlined in the color of its worst verdict</strong> on that reference — a red underline means at least one unsupported or contradicted claim.</li>
      <li>The sentence that made the active claim is highlighted in <span style="background:rgba(252,211,77,0.55);padding:0 3px;border-radius:2px">yellow</span>.</li>
    </ul>
  `;
}}

function showHelp() {{
  renderHelpBody();
  helpBackdrop.classList.add('open');
}}
function hideHelp() {{ helpBackdrop.classList.remove('open'); }}

document.getElementById('help-btn').addEventListener('click', showHelp);
document.getElementById('help-close').addEventListener('click', hideHelp);
helpBackdrop.addEventListener('click', (e) => {{ if (e.target === helpBackdrop) hideHelp(); }});

// Auto-show on first visit; subsequent visits stay out of the way until the user opens it.
// If localStorage is blocked (e.g. Chrome on file://), fall back to always showing — better
// to re-show every load than to silently swallow the popup.
(function autoShowHelp() {{
  const KEY = 'paper-trail-help-seen-v2';
  let seen = false;
  try {{ seen = !!localStorage.getItem(KEY); }} catch (_) {{ seen = false; }}
  if (!seen) {{
    setTimeout(showHelp, 350);
    try {{ localStorage.setItem(KEY, '1'); }} catch (_) {{ /* ignore */ }}
  }}
}})();

// ------- Boot --------
renderSidebar();
loadPdf();

// scroll listener updates page input
document.getElementById('pdf-pages').addEventListener('scroll', () => {{
  document.getElementById('page-input').value = currentPage();
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
