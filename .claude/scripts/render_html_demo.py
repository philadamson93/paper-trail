#!/usr/bin/env python3
"""
Render a paper-trail audit run as an interactive HTML demo.

Output: a single self-contained HTML file. The user opens it in a browser; the
paper text renders with citation markers; hovering over any marker pops up:
  - reference details (authors, title, venue, DOI/arXiv link)
  - the manuscript claim sentence(s) tagged to that reference
  - per-claim verdict + flag + remediation
  - evidence excerpts and attestation

Color-coded by overall_verdict.

Usage:
    python3 render_html_demo.py --run-dir paper-trail-adamson2025-v2/
"""

from __future__ import annotations

import argparse
import json
import re
from html import escape
from pathlib import Path


VERDICT_COLOR = {
    "CONFIRMED": "#16a34a",  # green
    "CONFIRMED_WITH_MINOR": "#65a30d",  # yellow-green
    "OVERSTATED_MILD": "#eab308",  # amber
    "OVERSTATED": "#f97316",  # orange
    "OVERGENERAL": "#f97316",
    "PARTIALLY_SUPPORTED": "#fb923c",  # light orange
    "CITED_OUT_OF_CONTEXT": "#fb923c",
    "INDIRECT_SOURCE": "#a855f7",  # purple
    "MISATTRIBUTED": "#dc2626",  # red
    "UNSUPPORTED": "#dc2626",
    "CONTRADICTED": "#991b1b",  # dark red
    "AMBIGUOUS": "#9ca3af",  # gray
    "PENDING": "#cbd5e1",  # light gray
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


def parse_refs_bib(bib_path: Path) -> dict[str, dict]:
    """Parse refs.bib into a dict keyed by citekey."""
    refs = {}
    text = bib_path.read_text()
    for entry in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.DOTALL):
        etype = entry.group(1)
        key = entry.group(2).strip()
        body = entry.group(3)
        fields = {}
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
    """Return 'Lastname et al.' or 'Lastname & Other' style abbreviation."""
    if not authors:
        return ""
    parts = [a.strip() for a in authors.split(" and ")]
    first = parts[0]
    # extract surname (assume "Last, First" or "First Last")
    if "," in first:
        last = first.split(",")[0].strip()
    else:
        toks = first.split()
        last = toks[-1] if toks else first
    if len(parts) == 1:
        return last
    if len(parts) == 2:
        # "First & Second"
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


def load_claims(run_dir: Path) -> list[dict]:
    claims = []
    for fp in sorted((run_dir / "ledger" / "claims").glob("*.json")):
        try:
            claims.append(json.loads(fp.read_text()))
        except Exception as e:
            print(f"skip {fp.name}: {e}")
    return claims


def render_claim_block(claim: dict, ref: dict, source_pdf_url: str = "") -> str:
    """Render the in-popup claim detail block."""
    overall = claim.get("overall_verdict", "PENDING")
    flag = claim.get("overall_flag") or "—"
    color = VERDICT_COLOR.get(overall, "#9ca3af")
    label = VERDICT_LABEL.get(overall, overall)
    rem = claim.get("remediation") or {}

    sub_claims_html = []
    for sc in claim.get("sub_claims", []):
        sv = sc.get("verdict", "PENDING")
        sv_color = VERDICT_COLOR.get(sv, "#9ca3af")
        sv_label = VERDICT_LABEL.get(sv, sv)
        evidence_html = ""
        for ev in (sc.get("evidence") or [])[:3]:
            sec = escape(str(ev.get("section", "?")))
            line = ev.get("line", "?")
            snip = escape(str(ev.get("snippet", ""))[:280])
            evidence_html += f'<div class="ev"><span class="ev-loc">{sec} L{line}</span> <span class="ev-snip">"{snip}"</span></div>'
        if not evidence_html and sc.get("nuance"):
            evidence_html = f'<div class="ev"><em>{escape(sc["nuance"][:300])}</em></div>'
        nuance_html = ""
        if sc.get("paper_value") or sc.get("claim_value"):
            nuance_html = f'<div class="drift"><strong>Paper:</strong> <code>{escape(str(sc.get("paper_value","—")))[:120]}</code> · <strong>Claim:</strong> <code>{escape(str(sc.get("claim_value","—")))[:120]}</code></div>'
        sub_claims_html.append(f"""
        <div class="subclaim">
          <div class="subclaim-head">
            <span class="verdict-pill" style="background:{sv_color}">{escape(sv_label)}</span>
            <span class="subclaim-id">{escape(sc.get('sub_claim_id',''))}</span>
          </div>
          <div class="subclaim-text">{escape(sc.get('text','')[:300])}</div>
          {nuance_html}
          {evidence_html}
        </div>
        """)

    rem_html = ""
    if rem and rem.get("category"):
        rem_html = f"""
        <div class="remediation">
          <div class="rem-cat">{escape(rem.get('category',''))}</div>
          <div class="rem-edit">{escape(rem.get('suggested_edit','')[:500])}</div>
        </div>
        """

    pdf_link = ""
    if source_pdf_url:
        pdf_link = f' · <a href="{source_pdf_url}" target="_blank">open PDF</a>'

    return f"""
    <div class="popup-content">
      <div class="popup-header">
        <div class="overall">
          <span class="verdict-pill big" style="background:{color}">{escape(label)}</span>
          {f'<span class="flag-pill">{escape(flag)}</span>' if flag != "—" else ""}
        </div>
        <div class="claim-id">{escape(claim.get('claim_id',''))} → <code>{escape(claim.get('citekey',''))}</code>{pdf_link}</div>
      </div>
      <div class="claim-text">"{escape(claim.get('claim_text','')[:500])}"</div>
      <div class="subclaims">{''.join(sub_claims_html)}</div>
      {rem_html}
    </div>
    """


def render_reference_block(ref: dict) -> str:
    link = reference_link(ref)
    link_html = f'<a href="{link}" target="_blank">{escape(link)}</a>' if link else ""
    return f"""
    <div class="ref-block">
      <div class="ref-num">[{ref.get('refnum') or '?'}]</div>
      <div class="ref-meta">
        <div class="ref-authors">{escape(ref.get('authors','')[:300])}</div>
        <div class="ref-title">{escape(ref.get('title',''))}</div>
        <div class="ref-venue">{escape(ref.get('venue',''))} ({escape(ref.get('year',''))})</div>
        <div class="ref-link">{link_html}</div>
      </div>
    </div>
    """


def render_paper_with_markers(paper_text: str, refnum_to_claims: dict[int, list]) -> str:
    """Walk the paper text, escape it, and replace numeric citation markers with hover spans."""
    # simple approach: split into paragraphs, render markers inline
    # citation markers in this paper format: superscript-like numbers attached to words, e.g., "research.1–4"
    # we'll detect patterns like (?<=[\w.\)\]])(\d{1,3}(?:[,–\-]\d{1,3})*)
    paragraphs = re.split(r"\n{2,}", paper_text)
    out = []
    for p in paragraphs:
        # escape first
        p_esc = escape(p)
        # then replace markers
        def replace_marker(m):
            full = m.group(0)
            nums = []
            # tokenize: comma- or dash-separated numbers; dash means range
            for piece in re.split(r",", full):
                if re.search(r"[\-–]", piece):
                    parts = re.split(r"[\-–]", piece)
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        a, b = int(parts[0]), int(parts[1])
                        if 1 <= a <= 200 and 1 <= b <= 200 and b - a < 20:
                            nums.extend(range(a, b + 1))
                else:
                    if piece.isdigit():
                        n = int(piece)
                        if 1 <= n <= 200:
                            nums.append(n)
            # filter to those that have entries
            valid = [n for n in nums if n in refnum_to_claims and refnum_to_claims[n]]
            if not valid:
                return full
            spans = []
            for n in valid:
                claim_ids = ",".join(c["claim_id"] for c in refnum_to_claims[n])
                # color = highest-severity overall_verdict among claims
                colors = [VERDICT_COLOR.get(c.get("overall_verdict","PENDING"), "#cbd5e1") for c in refnum_to_claims[n]]
                color = colors[0]
                spans.append(f'<span class="cite" data-refnum="{n}" data-claim-ids="{escape(claim_ids)}" style="border-bottom:2px solid {color}">{n}</span>')
            return ",".join(spans)

        p_with_marks = re.sub(r"(?<=[\w\.\)\]])(\d{1,3}(?:[,\-–]\d{1,3})?(?:,\d{1,3})*)", replace_marker, p_esc)
        out.append(f"<p>{p_with_marks}</p>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--paper-txt", default="paper.txt", help="path relative to run-dir")
    ap.add_argument("--bib", default="refs.bib", help="bib filename relative to run-dir")
    ap.add_argument("--output", default="demo.html", help="output filename relative to run-dir")
    args = ap.parse_args()

    run = args.run_dir.resolve()
    paper_text = (run / args.paper_txt).read_text()
    refs = parse_refs_bib(run / args.bib)
    claims = load_claims(run)

    # build refnum -> [claims] index
    refnum_to_claims: dict[int, list] = {}
    for c in claims:
        ref = refs.get(c["citekey"])
        if ref and ref.get("refnum") is not None:
            refnum_to_claims.setdefault(ref["refnum"], []).append(c)

    # data blob for JS
    data = {
        "refs": {str(rn): refs[c["citekey"]] for rn, lst in refnum_to_claims.items() for c in lst if (refs.get(c["citekey"]) and refs[c["citekey"]].get("refnum") == rn)},
        "refsByCitekey": refs,
        "claimsById": {c["claim_id"]: c for c in claims},
        "refnumToClaimIds": {str(rn): [c["claim_id"] for c in lst] for rn, lst in refnum_to_claims.items()},
    }

    paper_html = render_paper_with_markers(paper_text, refnum_to_claims)

    # render references list
    ref_list_html = "\n".join(
        render_reference_block(refs[ck])
        for rn, lst in sorted(refnum_to_claims.items())
        for ck in [lst[0]["citekey"]]
        if refs.get(ck)
    )

    # verdict legend
    legend_html = "\n".join(
        f'<span class="legend-item"><span class="legend-color" style="background:{c}"></span>{label}</span>'
        for v, label in [
            ("CONFIRMED", "Confirmed"),
            ("CONFIRMED_WITH_MINOR", "Confirmed (minor)"),
            ("OVERSTATED", "Overstated"),
            ("INDIRECT_SOURCE", "Indirect source"),
            ("MISATTRIBUTED", "Misattributed"),
            ("CITED_OUT_OF_CONTEXT", "Out of context"),
            ("PENDING", "Pending — no PDF"),
        ]
        for c in [VERDICT_COLOR[v]]
    )

    # summary stats
    counts = {}
    for c in claims:
        v = c.get("overall_verdict", "PENDING")
        counts[v] = counts.get(v, 0) + 1
    summary_html = " · ".join(f"<strong>{v}:</strong> {n}" for v, n in sorted(counts.items()))

    paper_title = ""
    paper_doi = ""
    # try to read frontmatter from ledger.md if present
    led = run / "ledger.md"
    if led.exists():
        led_text = led.read_text()
        m = re.search(r'title:\s*"([^"]+)"', led_text)
        if m: paper_title = m.group(1)
        m = re.search(r'doi:\s*([^\s]+)', led_text)
        if m: paper_doi = m.group(1).strip()

    html = HTML_TEMPLATE.format(
        title=escape(paper_title or "paper-trail demo"),
        doi=escape(paper_doi),
        summary=summary_html,
        legend=legend_html,
        paper_html=paper_html,
        ref_list_html=ref_list_html,
        data_json=json.dumps(data, default=str),
    )

    out = run / args.output
    out.write_text(html)
    print(f"wrote {out}")
    print(f"claims: {len(claims)} · refs with claims: {len(refnum_to_claims)}")
    print(f"verdict counts: {counts}")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} — paper-trail demo</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
         margin: 0; padding: 0; background: #fafaf9; color: #1c1917; line-height: 1.6; }}
  header {{ background: #1e293b; color: white; padding: 1.5rem 2rem; }}
  header h1 {{ margin: 0 0 0.25rem 0; font-size: 1.4rem; font-weight: 600; }}
  header .doi {{ font-size: 0.85rem; opacity: 0.7; }}
  .summary {{ background: #f1f5f9; padding: 0.75rem 2rem; font-size: 0.85rem; border-bottom: 1px solid #e2e8f0; }}
  .legend {{ background: #f8fafc; padding: 0.75rem 2rem; font-size: 0.8rem; border-bottom: 1px solid #e2e8f0;
            display: flex; flex-wrap: wrap; gap: 1rem; }}
  .legend-item {{ display: flex; align-items: center; gap: 0.4rem; }}
  .legend-color {{ display: inline-block; width: 12px; height: 12px; border-radius: 2px; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 2rem; }}
  .paper p {{ margin: 0 0 1rem 0; font-size: 0.95rem; }}
  .cite {{ cursor: pointer; padding: 0 2px; font-weight: 600; transition: background 0.15s; }}
  .cite:hover {{ background: #fef3c7; }}
  .references {{ margin-top: 3rem; padding-top: 2rem; border-top: 2px solid #e2e8f0; }}
  .references h2 {{ font-size: 1.1rem; }}
  .ref-block {{ display: flex; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; }}
  .ref-num {{ font-weight: 600; min-width: 2rem; }}
  .ref-meta {{ flex: 1; }}
  .ref-authors {{ color: #475569; }}
  .ref-title {{ font-weight: 500; margin: 0.1rem 0; }}
  .ref-venue {{ color: #64748b; font-style: italic; font-size: 0.8rem; }}
  .ref-link a {{ font-size: 0.75rem; color: #0369a1; }}

  /* Popup */
  #popup {{ position: fixed; display: none; max-width: 540px; max-height: 78vh; overflow-y: auto;
           background: white; border: 1px solid #94a3b8; border-radius: 8px;
           box-shadow: 0 10px 30px rgba(0,0,0,0.15); padding: 0; z-index: 100; }}
  .popup-section {{ padding: 1rem 1.25rem; border-bottom: 1px solid #f1f5f9; }}
  .popup-section:last-child {{ border-bottom: none; }}
  .popup-section h3 {{ font-size: 0.7rem; font-weight: 600; color: #64748b; text-transform: uppercase;
                       margin: 0 0 0.5rem 0; letter-spacing: 0.05em; }}
  .popup-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }}
  .verdict-pill {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; color: white;
                   font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }}
  .verdict-pill.big {{ font-size: 0.8rem; padding: 0.3rem 0.75rem; }}
  .flag-pill {{ display: inline-block; padding: 0.15rem 0.5rem; background: #fef2f2; color: #991b1b;
                border: 1px solid #fecaca; border-radius: 4px; font-size: 0.7rem; font-weight: 600;
                margin-left: 0.5rem; }}
  .claim-id {{ font-size: 0.75rem; color: #64748b; }}
  .claim-id code {{ background: #f1f5f9; padding: 1px 4px; border-radius: 3px; }}
  .claim-text {{ font-size: 0.85rem; font-style: italic; color: #1c1917; padding: 0.5rem;
                 background: #f8fafc; border-left: 3px solid #94a3b8; margin: 0.5rem 0; }}
  .subclaim {{ margin: 0.75rem 0; padding: 0.5rem 0.75rem; background: #fafafa; border-radius: 4px; }}
  .subclaim-head {{ display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.25rem; }}
  .subclaim-id {{ font-size: 0.7rem; color: #64748b; font-family: monospace; }}
  .subclaim-text {{ font-size: 0.8rem; color: #334155; }}
  .drift {{ margin: 0.4rem 0; font-size: 0.75rem; color: #64748b; }}
  .drift code {{ background: #fef9c3; padding: 1px 4px; border-radius: 3px; }}
  .ev {{ font-size: 0.75rem; color: #475569; margin: 0.25rem 0; padding-left: 0.5rem;
        border-left: 2px solid #cbd5e1; }}
  .ev-loc {{ font-family: monospace; color: #64748b; font-size: 0.7rem; }}
  .ev-snip {{ display: block; margin-top: 0.15rem; }}
  .remediation {{ margin-top: 0.75rem; padding: 0.5rem 0.75rem; background: #fef3c7;
                  border-left: 3px solid #f59e0b; border-radius: 0 4px 4px 0; }}
  .rem-cat {{ font-size: 0.7rem; font-weight: 700; color: #92400e; text-transform: uppercase; }}
  .rem-edit {{ font-size: 0.8rem; color: #422006; margin-top: 0.25rem; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="doi">DOI: {doi}</div>
</header>
<div class="summary">{summary}</div>
<div class="legend">{legend}</div>

<main>
  <div class="paper">
    {paper_html}
  </div>

  <section class="references">
    <h2>References</h2>
    {ref_list_html}
  </section>
</main>

<div id="popup"></div>

<script>
const DATA = {data_json};

const popup = document.getElementById('popup');

function buildPopup(refnum) {{
  const claimIds = DATA.refnumToClaimIds[String(refnum)] || [];
  const ref = DATA.refs[String(refnum)];
  if (!ref) return '<div class="popup-section"><em>No data for ref ' + refnum + '</em></div>';

  let refHtml = '<div class="popup-section">' +
    '<h3>Reference [' + refnum + ']</h3>' +
    '<div class="ref-meta">' +
      '<div class="ref-authors">' + escapeHtml(ref.authors || '') + '</div>' +
      '<div class="ref-title"><strong>' + escapeHtml(ref.title || '') + '</strong></div>' +
      '<div class="ref-venue">' + escapeHtml(ref.venue || '') + ' (' + escapeHtml(ref.year || '') + ')</div>';
  const link = ref.doi ? 'https://doi.org/' + ref.doi : (ref.arxiv ? 'https://arxiv.org/abs/' + ref.arxiv : '');
  if (link) refHtml += '<div class="ref-link"><a href="' + link + '" target="_blank">' + link + '</a></div>';
  refHtml += '</div></div>';

  let claimsHtml = '';
  for (const cid of claimIds) {{
    const claim = DATA.claimsById[cid];
    if (!claim) continue;
    claimsHtml += '<div class="popup-section">' + renderClaim(claim) + '</div>';
  }}
  return refHtml + claimsHtml;
}}

const COLORS = {{
  CONFIRMED: '#16a34a', CONFIRMED_WITH_MINOR: '#65a30d',
  OVERSTATED_MILD: '#eab308', OVERSTATED: '#f97316', OVERGENERAL: '#f97316',
  PARTIALLY_SUPPORTED: '#fb923c', CITED_OUT_OF_CONTEXT: '#fb923c',
  INDIRECT_SOURCE: '#a855f7',
  MISATTRIBUTED: '#dc2626', UNSUPPORTED: '#dc2626', CONTRADICTED: '#991b1b',
  AMBIGUOUS: '#9ca3af', PENDING: '#cbd5e1',
}};
const LABELS = {{
  CONFIRMED: 'Confirmed', CONFIRMED_WITH_MINOR: 'Confirmed (minor)',
  OVERSTATED_MILD: 'Overstated (mild)', OVERSTATED: 'Overstated', OVERGENERAL: 'Overgeneral',
  PARTIALLY_SUPPORTED: 'Partial support', CITED_OUT_OF_CONTEXT: 'Out of context',
  INDIRECT_SOURCE: 'Indirect source',
  MISATTRIBUTED: 'Misattributed', UNSUPPORTED: 'Unsupported', CONTRADICTED: 'Contradicted',
  AMBIGUOUS: 'Ambiguous', PENDING: 'Pending — PDF unavailable',
}};

function renderClaim(claim) {{
  const v = claim.overall_verdict || 'PENDING';
  const color = COLORS[v] || '#9ca3af';
  const label = LABELS[v] || v;
  const flag = claim.overall_flag || '';

  let h = '<div class="popup-header">' +
    '<div><span class="verdict-pill big" style="background:' + color + '">' + escapeHtml(label) + '</span>';
  if (flag && flag !== '—') h += '<span class="flag-pill">' + escapeHtml(flag) + '</span>';
  h += '</div><div class="claim-id">' + escapeHtml(claim.claim_id) + ' → <code>' + escapeHtml(claim.citekey) + '</code></div></div>';
  h += '<div class="claim-text">"' + escapeHtml((claim.claim_text || '').slice(0, 500)) + '"</div>';

  for (const sc of (claim.sub_claims || [])) {{
    const sv = sc.verdict || 'PENDING';
    const sc_color = COLORS[sv] || '#9ca3af';
    const sc_label = LABELS[sv] || sv;
    h += '<div class="subclaim">' +
      '<div class="subclaim-head">' +
      '<span class="verdict-pill" style="background:' + sc_color + '">' + escapeHtml(sc_label) + '</span>' +
      '<span class="subclaim-id">' + escapeHtml(sc.sub_claim_id || '') + '</span></div>' +
      '<div class="subclaim-text">' + escapeHtml((sc.text || '').slice(0, 300)) + '</div>';
    if (sc.paper_value || sc.claim_value) {{
      h += '<div class="drift"><strong>Paper:</strong> <code>' + escapeHtml(String(sc.paper_value || '—').slice(0, 120)) +
           '</code> · <strong>Claim:</strong> <code>' + escapeHtml(String(sc.claim_value || '—').slice(0, 120)) + '</code></div>';
    }}
    for (const ev of (sc.evidence || []).slice(0, 3)) {{
      h += '<div class="ev"><span class="ev-loc">' + escapeHtml(String(ev.section || '?')) + ' L' + escapeHtml(String(ev.line || '?')) +
           '</span><span class="ev-snip">"' + escapeHtml(String(ev.snippet || '').slice(0, 280)) + '"</span></div>';
    }}
    if ((sc.evidence || []).length === 0 && sc.nuance) {{
      h += '<div class="ev"><em>' + escapeHtml(sc.nuance.slice(0, 300)) + '</em></div>';
    }}
    h += '</div>';
  }}

  const rem = claim.remediation;
  if (rem && rem.category) {{
    h += '<div class="remediation">' +
      '<div class="rem-cat">' + escapeHtml(rem.category) + '</div>' +
      '<div class="rem-edit">' + escapeHtml((rem.suggested_edit || '').slice(0, 500)) + '</div></div>';
  }}
  return h;
}}

function escapeHtml(s) {{
  return String(s).replace(/[&<>"']/g, c => (
    {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}}[c]
  ));
}}

function showPopup(target, refnum) {{
  popup.innerHTML = buildPopup(refnum);
  popup.style.display = 'block';
  const rect = target.getBoundingClientRect();
  let top = rect.bottom + window.scrollY + 8;
  let left = rect.left + window.scrollX;
  if (left + 540 > window.innerWidth) left = window.innerWidth - 560;
  if (left < 10) left = 10;
  popup.style.top = (top - window.scrollY) + 'px';
  popup.style.left = left + 'px';
}}

function hidePopup() {{ popup.style.display = 'none'; }}

let popupTimer;
document.querySelectorAll('.cite').forEach(span => {{
  span.addEventListener('mouseenter', e => {{
    clearTimeout(popupTimer);
    showPopup(e.target, e.target.dataset.refnum);
  }});
  span.addEventListener('mouseleave', e => {{
    popupTimer = setTimeout(hidePopup, 300);
  }});
  span.addEventListener('click', e => {{
    showPopup(e.target, e.target.dataset.refnum);
  }});
}});
popup.addEventListener('mouseenter', () => clearTimeout(popupTimer));
popup.addEventListener('mouseleave', () => {{ popupTimer = setTimeout(hidePopup, 300); }});
document.addEventListener('click', e => {{
  if (!e.target.closest('.cite') && !e.target.closest('#popup')) hidePopup();
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
