"""Read an example file and report its text and format facts (for skills eingang and vorlage-ableiten).

Usage:
  python kern/tools/convert_example.py <file> [--facts] [--out text.md]

Supported: .docx (paragraphs + tables as Markdown; facts: page, margins, fonts, table column widths),
.pdf (text via `pdftotext -layout` if available, else pypdf; facts: page sizes, orientation, fonts),
.pptx (slide texts), .txt/.md (as is). Images: reports size only – look at them directly.
Standard library for docx/pptx; pypdf only needed for PDFs without pdftotext.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = "{%s}" % W_NS
TWIP_CM = 2.54 / 1440


# ------------------------------------------------------------------ docx
def _para_text(p):
    parts = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append(" ")
        elif node.tag == W + "br":
            parts.append("<br>")
    return "".join(parts).strip()


def _is_bold(p):
    runs = [r for r in p.findall(".//w:r", NS) if _para_text(r)]
    return bool(runs) and all(r.find("w:rPr/w:b", NS) is not None for r in runs)


def _style(p):
    ps = p.find("w:pPr/w:pStyle", NS)
    return ps.get(W + "val", "") if ps is not None else ""


def docx_text(path):
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    out = []
    for el in root.find("w:body", NS):
        if el.tag == W + "p":
            t = _para_text(el)
            if not t:
                continue
            st = _style(el).lower()
            if st.startswith(("heading", "berschrift", "title")):
                lvl = re.sub(r"\D", "", st) or "1"
                out.append("#" * min(int(lvl) + 1, 4) + " " + t)
            elif _is_bold(el) and len(t) < 120:
                out.append("**" + t + "**")
            else:
                out.append(t)
            out.append("")
        elif el.tag == W + "tbl":
            grid = [["<br>".join(x for x in (_para_text(p) for p in tc.findall("w:p", NS)) if x).replace("|", "\\|")
                     for tc in tr.findall("w:tc", NS)] for tr in el.findall("w:tr", NS)]
            if not grid:
                continue
            width = max(len(r) for r in grid)
            grid = [r + [""] * (width - len(r)) for r in grid]
            out.append("| " + " | ".join(grid[0]) + " |")
            out.append("|" + "---|" * width)
            out.extend("| " + " | ".join(r) + " |" for r in grid[1:])
            out.append("")
    return "\n".join(out)


def docx_facts(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    facts = []
    for i, sect in enumerate(root.iter(W + "sectPr")):
        pg = sect.find("w:pgSz", NS)
        mar = sect.find("w:pgMar", NS)
        if pg is not None:
            w, h = int(pg.get(W + "w")), int(pg.get(W + "h"))
            facts.append(f"section {i + 1}: page {w * TWIP_CM:.2f} x {h * TWIP_CM:.2f} cm "
                         f"({'landscape' if w > h else 'portrait'})")
        if mar is not None:
            m = {k: int(mar.get(W + k, 0)) * TWIP_CM for k in ("top", "right", "bottom", "left")}
            facts.append("  margins cm (top, right, bottom, left): "
                         + ", ".join(f"{m[k]:.2f}" for k in ("top", "right", "bottom", "left")))
    fonts, sizes = {}, {}
    for r in root.iter(W + "rPr"):
        f = r.find("w:rFonts", NS)
        if f is not None and f.get(W + "ascii"):
            fonts[f.get(W + "ascii")] = fonts.get(f.get(W + "ascii"), 0) + 1
        s = r.find("w:sz", NS)
        if s is not None:
            pt = int(s.get(W + "val")) / 2
            sizes[pt] = sizes.get(pt, 0) + 1
    if "word/styles.xml" in z.namelist():
        st = ET.fromstring(z.read("word/styles.xml"))
        d = st.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        if d is not None:
            f = d.find("w:rFonts", NS)
            s = d.find("w:sz", NS)
            facts.append(f"default font: {f.get(W + 'ascii') if f is not None else '?'}, "
                         f"{int(s.get(W + 'val')) / 2 if s is not None else '?'} pt")
        for sty in st.findall("w:style", NS):
            if sty.get(W + "styleId") == "Normal":
                f = sty.find("w:rPr/w:rFonts", NS)
                s = sty.find("w:rPr/w:sz", NS)
                facts.append(f"style Normal: {f.get(W + 'ascii') if f is not None else '(default)'}, "
                             f"{int(s.get(W + 'val')) / 2 if s is not None else '(default)'} pt")
    facts.append("fonts used (runs): " + ", ".join(f"{k} ×{v}" for k, v in sorted(fonts.items(), key=lambda x: -x[1])))
    facts.append("sizes used (pt): " + ", ".join(f"{k:g} ×{v}" for k, v in sorted(sizes.items(), key=lambda x: -x[1])))
    for i, tbl in enumerate(root.iter(W + "tbl")):
        cols = [int(g.get(W + "w", 0)) * TWIP_CM for g in tbl.findall("w:tblGrid/w:gridCol", NS)]
        rows = len(tbl.findall("w:tr", NS))
        tr0 = tbl.find("w:tr", NS)
        first = [_para_text(tc) for tc in tr0.findall("w:tc", NS)][:12] if tr0 is not None else []
        facts.append(f"table {i + 1}: {rows} rows, column widths cm {[round(c, 2) for c in cols]}")
        facts.append(f"  first row: {first}")
    return facts


# ------------------------------------------------------------------ pdf
def pdf_text(path):
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"], capture_output=True)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", errors="replace")
    import pypdf
    return "\n\n".join((p.extract_text() or "") for p in pypdf.PdfReader(str(path)).pages)


def pdf_facts(path):
    try:
        import pypdf
    except ImportError:
        return ["pypdf missing: python kern/tools/voraussetzungen.py --install (48-hour rule; needed for PDF facts)"]
    r = pypdf.PdfReader(str(path))
    facts = []
    fonts = set()
    for i, p in enumerate(r.pages):
        w, h = float(p.mediabox.width), float(p.mediabox.height)
        if p.get("/Rotate") in (90, 270):
            w, h = h, w
        facts.append(f"page {i + 1}: {w / 72 * 2.54:.1f} x {h / 72 * 2.54:.1f} cm ({'landscape' if w > h else 'portrait'})")
        res = p.get("/Resources") or {}
        for v in (res.get("/Font") or {}).values():
            name = str(v.get_object().get("/BaseFont", ""))
            fonts.add(re.sub(r"^/?[A-Z]{6}\+", "", name).lstrip("/"))
    meta = r.metadata or {}
    facts.append("fonts: " + ", ".join(sorted(fonts)))
    facts.append(f"creator: {meta.get('/Creator')} · producer: {meta.get('/Producer')}")
    facts.append("margins/column widths: not stored in PDFs – estimate from the layout and confirm with the teacher")
    return facts


# ------------------------------------------------------------------ pptx
def pptx_text(path):
    z = zipfile.ZipFile(path)
    slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                    key=lambda n: int(re.findall(r"\d+", n)[-1]))
    out = []
    for n in slides:
        root = ET.fromstring(z.read(n))
        texts = [t.text for t in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t") if t.text]
        out.append(f"## {Path(n).stem}\n" + "\n".join(texts) + "\n")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file")
    ap.add_argument("--facts", action="store_true", help="also print format facts")
    ap.add_argument("--out", help="write the text to this file")
    a = ap.parse_args(argv)
    p = Path(a.file)
    ext = p.suffix.lower()
    facts = []
    if ext == ".docx":
        text = docx_text(p)
        facts = docx_facts(p)
    elif ext == ".pdf":
        text = pdf_text(p)
        facts = pdf_facts(p)
    elif ext == ".pptx":
        text = pptx_text(p)
    elif ext in (".txt", ".md", ".html", ".htm", ".csv"):
        text = p.read_text(encoding="utf-8", errors="replace")
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        text = f"image file ({p.stat().st_size // 1024} KB) – look at it directly"
    else:
        text = f"unsupported type {ext}; ask the teacher for docx, pdf or a screenshot"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8", newline="\n")
        print("written:", a.out)
    else:
        print(text)
    if a.facts or ext in (".docx", ".pdf"):
        print("\n--- format facts ---")
        print("\n".join(facts))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
