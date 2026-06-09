#!/usr/bin/env python3
"""
Phase 2.5 ingest: turn a fetched PDF into paper-trail's canonical per-paper filesystem.

Spec: `.claude/specs/ingest.md`
Output layout: pdfs/<citekey>/{meta.json, content.txt, sections/*.txt, figures/*.png, figures/index.json, ingest_report.json}

Usage:
    python3 ingest_pdf.py --pdf pdfs/hammernik2021.pdf --citekey hammernik2021 --out-dir pdfs/hammernik2021/

Requires GROBID running at http://localhost:8070. Start with:
    docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # pymupdf
import requests
from lxml import etree

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def check_grobid(url: str) -> bool:
    try:
        r = requests.get(f"{url}/api/isalive", timeout=3)
        return r.status_code == 200 and r.text.strip() == "true"
    except requests.RequestException:
        return False


def grobid_process(pdf_path: Path, url: str) -> str | None:
    with open(pdf_path, "rb") as f:
        files = {"input": (pdf_path.name, f, "application/pdf")}
        params = {"consolidateHeader": "1", "consolidateCitations": "0"}
        try:
            r = requests.post(
                f"{url}/api/processFulltextDocument",
                files=files,
                data=params,
                timeout=180,
            )
        except requests.RequestException as e:
            print(f"[ingest] grobid request failed: {e}", file=sys.stderr)
            return None
    if r.status_code != 200:
        print(f"[ingest] grobid returned {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return None
    return r.text


def parse_tei(tei_xml: str) -> dict:
    root = etree.fromstring(tei_xml.encode())

    def text_of(elem) -> str:
        if elem is None:
            return ""
        return " ".join(elem.itertext()).strip()

    def xp(path, el=None):
        return (el if el is not None else root).xpath(path, namespaces=TEI_NS)

    def first(path, el=None):
        nodes = xp(path, el)
        return nodes[0] if nodes else None

    title = text_of(first(".//tei:teiHeader//tei:titleStmt/tei:title"))

    authors = []
    for pers in xp(".//tei:teiHeader//tei:sourceDesc//tei:analytic//tei:author/tei:persName"):
        forename = text_of(first("./tei:forename", pers))
        surname = text_of(first("./tei:surname", pers))
        full = " ".join(x for x in (forename, surname) if x)
        if full:
            authors.append(full)

    doi = None
    doi_elems = xp(".//tei:teiHeader//tei:sourceDesc//tei:idno[@type='DOI']")
    if doi_elems:
        doi = text_of(doi_elems[0]) or None

    abstract = ""
    ab_elems = xp(".//tei:teiHeader//tei:profileDesc/tei:abstract")
    if ab_elems:
        abstract = text_of(ab_elems[0])

    pub_date = None
    date_elems = xp(".//tei:teiHeader//tei:sourceDesc//tei:monogr//tei:imprint/tei:date/@when")
    if date_elems:
        pub_date = str(date_elems[0])

    # Body sections: each <div> in <body> is a section; use <head> as name.
    sections = []
    body_divs = xp(".//tei:text/tei:body/tei:div")
    for div in body_divs:
        head_elems = xp("./tei:head", div)
        head = text_of(head_elems[0]) if head_elems else "Unnamed"
        # concatenate paragraphs
        paras = [text_of(p) for p in xp("./tei:p", div)]
        body_text = "\n".join(p for p in paras if p)
        if body_text:
            sections.append({"name": head, "text": body_text})

    # Figures: TEI has <figure>, with <head>/<figDesc> captions and @xml:id
    figures_meta = []
    for fig in xp(".//tei:figure"):
        fig_id = fig.get("{http://www.w3.org/XML/1998/namespace}id") or ""
        head_elems = xp("./tei:head", fig)
        label_elems = xp("./tei:label", fig)
        desc_elems = xp("./tei:figDesc", fig)
        label = text_of(label_elems[0]) if label_elems else (text_of(head_elems[0]) if head_elems else fig_id)
        caption = text_of(desc_elems[0]) if desc_elems else (text_of(head_elems[0]) if head_elems else "")
        # try to parse "Figure N" from label
        fignum = None
        m = re.match(r"(?:Fig(?:ure)?\.?\s*)(\d+)", label, flags=re.I)
        if m:
            fignum = int(m.group(1))
        figures_meta.append({"tei_id": fig_id, "label": label, "caption": caption, "figure_number": fignum})

    return {
        "title": title,
        "authors": authors,
        "doi": doi,
        "abstract": abstract,
        "pub_date": pub_date,
        "sections": sections,
        "figures_meta": figures_meta,
    }


def extract_page_texts(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()


def guess_page_for_line(line: str, page_texts: list[str]) -> int:
    # Simple substring search: return 1-indexed page of first match, else 0.
    snippet = line.strip()[:80]
    if not snippet:
        return 0
    for i, pt in enumerate(page_texts, 1):
        if snippet in pt:
            return i
    # fallback: match first 40 chars
    snippet40 = snippet[:40]
    for i, pt in enumerate(page_texts, 1):
        if snippet40 in pt:
            return i
    return 0


def extract_figure_images(pdf_path: Path, out_dir: Path, figures_meta: list[dict]) -> list[dict]:
    """
    pymupdf extracts each embedded XObject image. We group by page and emit one image per figure,
    preferring the largest-bbox image on the page matching each figure's number.

    For papers where GROBID's figure metadata doesn't pin a page number, we still emit all
    large raster images per page under a generic fig_<page>_<idx>.png naming scheme.
    """
    out = out_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    index = []
    try:
        for page_num, page in enumerate(doc, 1):
            page_images = page.get_images(full=True)
            for img_idx, img_info in enumerate(page_images):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                except Exception:
                    continue
                # skip tiny icons / decorative vectors
                if pix.width < 200 or pix.height < 200:
                    pix = None
                    continue
                # Normalize to RGB: handles CMYK, indexed (palette), and DeviceN.
                # fitz.Pixmap.save(png) requires gray or rgb without alpha.
                if pix.colorspace is None or pix.colorspace.name not in ("DeviceGray", "DeviceRGB"):
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.alpha:
                    pix = fitz.Pixmap(pix, 0)
                fname = f"fig_p{page_num}_i{img_idx}.png"
                fpath = out / fname
                pix.save(fpath)
                index.append({
                    "filename": fname,
                    "page": page_num,
                    "width": pix.width,
                    "height": pix.height,
                    "tei_match": None,
                    "caption": "",
                })
                pix = None
    finally:
        doc.close()

    # Try to match GROBID figure metadata to extracted images by page:
    # for each figure caption, if we have exactly one image on that page, associate them.
    # Best-effort; leaves unassociated entries with empty caption.
    if figures_meta:
        # crude per-page grouping
        by_page: dict[int, list[int]] = {}
        for i, entry in enumerate(index):
            by_page.setdefault(entry["page"], []).append(i)
        # figures_meta doesn't reliably give pages; just dump captions in order and match
        # where we can. Better matching can come in a follow-up.
        for fm_idx, fm in enumerate(figures_meta):
            label = fm.get("label", "")
            caption = fm.get("caption", "")
            # naive pairing: first unassigned figure gets this caption
            for idx in index:
                if not idx["caption"]:
                    idx["tei_match"] = fm.get("tei_id") or label
                    idx["caption"] = caption
                    if fm.get("figure_number"):
                        # rename to encode the figure number if we have one
                        new_name = f"fig{fm['figure_number']}_p{idx['page']}.png"
                        old_path = out / idx["filename"]
                        new_path = out / new_name
                        if old_path.exists() and not new_path.exists():
                            old_path.rename(new_path)
                            idx["filename"] = new_name
                    break

    return index


def write_outputs(out_dir: Path, citekey: str, pdf_path: Path, parsed: dict, page_texts: list[str], figures_index: list[dict], ingest_mode: str, errors: list[str]):
    out_dir.mkdir(parents=True, exist_ok=True)

    # meta.json
    meta = {
        "citekey": citekey,
        "title": parsed.get("title"),
        "authors": parsed.get("authors", []),
        "doi": parsed.get("doi"),
        "abstract": parsed.get("abstract", ""),
        "pub_date": parsed.get("pub_date"),
        "page_count": len(page_texts),
        "source_pdf": str(pdf_path.resolve()),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    # sections/
    sec_dir = out_dir / "sections"
    sec_dir.mkdir(exist_ok=True)
    # filesystem-safe: replace runs of unsafe chars with single space, trim, dedupe
    unsafe = re.compile(r"[^\w\-§.]+")
    used = set()
    for i, sec in enumerate(parsed.get("sections", [])):
        name = unsafe.sub(" ", sec["name"]).strip()
        name = re.sub(r"\s+", " ", name)
        name = name[:120] or f"Unnamed_{i+1}"
        # dedupe collisions
        base = name
        counter = 2
        while name in used:
            name = f"{base}_{counter}"; counter += 1
        used.add(name)
        (sec_dir / f"{name}.txt").write_text(sec["text"])

    # content.txt with L<n> [p<page>] prefixes. Compose from sections first,
    # falling back to pymupdf page-text if no sections were extracted.
    content_lines = []
    line_no = 1
    if parsed.get("sections"):
        for sec in parsed["sections"]:
            for raw in sec["text"].splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                page = guess_page_for_line(raw, page_texts)
                content_lines.append(f"L{line_no} [p{page}]: {raw}")
                line_no += 1
    else:
        for page_idx, pt in enumerate(page_texts, 1):
            for raw in pt.splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                content_lines.append(f"L{line_no} [p{page_idx}]: {raw}")
                line_no += 1
    (out_dir / "content.txt").write_text("\n".join(content_lines))

    # figures/index.json
    (out_dir / "figures" / "index.json").write_text(json.dumps(figures_index, indent=2, ensure_ascii=False))

    # ingest_report.json
    report = {
        "tool": "grobid+pymupdf" if ingest_mode == "grobid" else ingest_mode,
        "ingest_mode": ingest_mode,
        "success": ingest_mode in ("grobid", "ocr_fallback", "pdftotext_fallback"),
        "sections_extracted": len(parsed.get("sections", [])),
        "figure_count": len(figures_index),
        "page_count": len(page_texts),
        "errors": errors,
    }
    (out_dir / "ingest_report.json").write_text(json.dumps(report, indent=2))
    return report


def pdftotext_fallback(pdf_path: Path) -> dict:
    page_texts = extract_page_texts(pdf_path)
    return {
        "title": None,
        "authors": [],
        "doi": None,
        "abstract": "",
        "pub_date": None,
        "sections": [],  # no section structure without GROBID
        "figures_meta": [],
    }, page_texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--citekey", required=True)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--grobid-url", default="http://localhost:8070")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if not args.pdf.exists():
        print(f"[ingest] pdf not found: {args.pdf}", file=sys.stderr)
        sys.exit(2)

    # resumability
    report_path = args.out_dir / "ingest_report.json"
    if report_path.exists() and not args.force:
        existing = json.loads(report_path.read_text())
        if existing.get("success"):
            print(f"[ingest] already ingested; skip (use --force to redo)")
            sys.exit(0)

    errors = []
    ingest_mode = "error"
    parsed = {}
    page_texts = []

    if check_grobid(args.grobid_url):
        tei = grobid_process(args.pdf, args.grobid_url)
        if tei:
            try:
                parsed = parse_tei(tei)
                page_texts = extract_page_texts(args.pdf)
                ingest_mode = "grobid"
            except Exception as e:
                errors.append(f"tei_parse: {e}")
        else:
            errors.append("grobid_returned_none")
    else:
        errors.append("grobid_not_available")
        print(
            "[ingest] GROBID not available at "
            f"{args.grobid_url}. Start it:\n"
            "    docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2",
            file=sys.stderr,
        )

    if ingest_mode == "error":
        # fallback to pymupdf-only: flat text, no sections
        try:
            parsed, page_texts = pdftotext_fallback(args.pdf)
            ingest_mode = "pdftotext_fallback"
        except Exception as e:
            errors.append(f"pdftotext_fallback: {e}")

    figures_index = []
    if page_texts:
        try:
            figures_index = extract_figure_images(args.pdf, args.out_dir, parsed.get("figures_meta", []))
        except Exception as e:
            errors.append(f"figures: {e}")

    report = write_outputs(
        args.out_dir, args.citekey, args.pdf, parsed, page_texts, figures_index, ingest_mode, errors
    )
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["success"] else 3)


if __name__ == "__main__":
    main()
