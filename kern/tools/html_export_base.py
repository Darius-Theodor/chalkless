"""HTML -> .docx export base for Chalkless templates.

Each template's export.py (written once by skill vorlage-ableiten) imports PageSetup and export_docx
and only sets parameters. The HTML subset understood here is what templates use:

  h1-h6, p, div, section/article/header/footer/main, ul/ol/li, table (thead/tbody/tfoot, tr, th, td,
  colspan, rowspan, colgroup/col), strong/b, em/i, u, sup, sub, span, a, br, img (skipped with a
  placeholder), and page breaks via class="seitenumbruch" or style="break-before: page" /
  "page-break-before: always". Elements with data-export="skip" are left out. <head>, <style>,
  <script> are ignored; meta chalkless.titel becomes the document title.

Usage as a script (defaults: A4 portrait, Arial 11, margins 2 cm):
  python kern/tools/html_export_base.py <file.html> [--landscape] [--font Arial] [--size 11]
Needs python-docx (set up by the agent: python kern/tools/voraussetzungen.py --install, 48-hour rule).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

try:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
except ImportError:  # pragma: no cover - reported to the agent
    sys.stderr.write("python-docx is missing. Set it up with: python kern/tools/voraussetzungen.py --install (48-hour rule)\n")
    raise

VOID = {"br", "meta", "link", "col", "img", "hr", "input", "source", "wbr"}
SKIP = {"head", "style", "script", "template", "noscript"}
BLOCK = {"p", "div", "section", "article", "header", "footer", "main", "aside", "nav", "figure",
         "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "blockquote", "hr", "dl", "dt", "dd"}
CONTAINERS = {"div", "section", "article", "header", "footer", "main", "aside", "nav", "figure", "blockquote", "body", "html", "dl"}


@dataclass
class PageSetup:
    width_cm: float = 21.0
    height_cm: float = 29.7
    margins_cm: tuple = (2.0, 2.0, 2.0, 2.0)  # top, right, bottom, left (CSS order)
    font: str = "Arial"
    size_pt: float = 11
    line_spacing: float = 1.0
    space_after_pt: float = 3
    heading_sizes: dict = field(default_factory=lambda: {1: 14, 2: 12, 3: 11, 4: 11, 5: 11, 6: 11})
    header_fill: str | None = "D9D9D9"  # shading of <th> cells, None = none
    table_borders: bool = True


# ---------------------------------------------------------------- HTML tree
class Node:
    __slots__ = ("tag", "attrs", "children", "text")

    def __init__(self, tag, attrs=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.text = text

    def cls(self):
        return self.attrs.get("class", "").split()

    def style(self):
        return (self.attrs.get("style") or "").replace(" ", "").lower()


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        if tag == "meta":
            a = dict(attrs)
            name = a.get("name", "")
            if name.startswith("chalkless."):
                self.meta[name[10:]] = a.get("content", "")
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(Node("#text", text=data))


def parse_html(text):
    b = TreeBuilder()
    b.feed(text)
    b.close()
    return b.root, b.meta


def find(node, tag):
    if node.tag == tag:
        return node
    for c in node.children:
        r = find(c, tag)
        if r is not None:
            return r
    return None


# ---------------------------------------------------------------- docx helpers
def is_page_break(node):
    s = node.style()
    return "seitenumbruch" in node.cls() or "break-before:page" in s or "page-break-before:always" in s


# Child order required by the OOXML schema (Word reports "unreadable content" otherwise).
TBLPR_ORDER = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize",
               "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
               "tblCaption", "tblDescription"]
TCPR_ORDER = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark"]


def put_ordered(parent, el, order):
    """Insert el into parent at its schema position, replacing an existing element of the same name."""
    name = el.tag.split("}")[1]
    for old in parent.findall(qn(f"w:{name}")):
        parent.remove(old)
    rank = order.index(name)
    for i, child in enumerate(parent):
        cname = child.tag.split("}")[1] if "}" in child.tag else child.tag
        if cname in order and order.index(cname) > rank:
            parent.insert(i, el)
            return
    parent.append(el)


def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    put_ordered(tcPr, shd, TCPR_ORDER)


def set_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    put_ordered(tblPr, borders, TBLPR_ORDER)


def set_fixed_layout(table):
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    put_ordered(tblPr, layout, TBLPR_ORDER)


def css_width_cm(node):
    if "data-breite-cm" in node.attrs:
        try:
            return float(node.attrs["data-breite-cm"].replace(",", "."))
        except ValueError:
            return None
    m = re.search(r"width:([\d.]+)(cm|mm)", node.style())
    if m:
        v = float(m.group(1))
        return v / 10 if m.group(2) == "mm" else v
    return None


class Writer:
    def __init__(self, doc, page: PageSetup, columns: dict | None):
        self.doc = doc
        self.page = page
        self.columns = columns or {}
        self.warnings = []

    # -------- inline content
    def add_inline(self, para, node, fmt=None):
        fmt = dict(fmt or {})
        if node.tag == "#text":
            text = re.sub(r"\s+", " ", node.text)
            current = para.text
            if current == "" or current.endswith(("\n", " ", "\t")):
                text = text.lstrip()
            if not text:
                return
            run = para.add_run(text)
            run.bold = fmt.get("b") or None
            run.italic = fmt.get("i") or None
            run.underline = fmt.get("u") or None
            if fmt.get("sup"):
                run.font.superscript = True
            if fmt.get("sub"):
                run.font.subscript = True
            if fmt.get("size"):
                run.font.size = Pt(fmt["size"])
            return
        tag = node.tag
        if tag in SKIP or node.attrs.get("data-export") == "skip":
            return
        if tag == "br":
            if para.runs and para.runs[-1].text.endswith(" "):
                para.runs[-1].text = para.runs[-1].text.rstrip()
            para.add_run().add_break()
            return
        if tag == "img":
            alt = node.attrs.get("alt") or node.attrs.get("src", "Bild")
            para.add_run(f"[Bild: {alt}]").italic = True
            return
        if tag in ("strong", "b", "th"):
            fmt["b"] = True
        if tag in ("em", "i"):
            fmt["i"] = True
        if tag == "u":
            fmt["u"] = True
        if tag == "sup":
            fmt["sup"] = True
        if tag == "sub":
            fmt["sub"] = True
        s = node.style()
        if "font-weight:bold" in s or "font-weight:700" in s:
            fmt["b"] = True
        if "font-style:italic" in s:
            fmt["i"] = True
        for c in node.children:
            self.add_inline(para, c, fmt)

    def new_para(self, container, style=None):
        p = container.add_paragraph(style=style) if style else container.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(self.page.space_after_pt)
        pf.line_spacing = self.page.line_spacing
        return p

    @staticmethod
    def strip_trailing(para):
        if para.runs and para.runs[-1].text.endswith(" "):
            para.runs[-1].text = para.runs[-1].text.rstrip()

    # -------- blocks
    def blocks(self, container, node, list_level=0):
        """Write children of node as paragraphs/tables into container (Document or cell)."""
        inline_buf = []

        def flush():
            if not inline_buf:
                return
            if all(n.tag == "#text" and not n.text.strip() for n in inline_buf):
                inline_buf.clear()
                return
            p = self.new_para(container)
            for n in inline_buf:
                self.add_inline(p, n)
            self.strip_trailing(p)
            inline_buf.clear()

        for c in node.children:
            if c.tag in SKIP or c.attrs.get("data-export") == "skip":
                continue
            if c.tag == "#text" or c.tag not in BLOCK:
                inline_buf.append(c)
                continue
            flush()
            self.block(container, c, list_level)
        flush()

    def block(self, container, node, list_level=0):
        tag = node.tag
        if is_page_break(node) and hasattr(container, "add_page_break"):
            container.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            p = self.new_para(container)
            size = self.page.heading_sizes.get(int(tag[1]), self.page.size_pt)
            self.add_inline(p, node, {"b": True, "size": size})
            self.strip_trailing(p)
            p.paragraph_format.space_before = Pt(6 if tag in ("h1", "h2") else 3)
            p.paragraph_format.keep_with_next = True
        elif tag in ("p", "dt", "dd"):
            if any(ch.tag in BLOCK for ch in node.children):
                self.blocks(container, node, list_level)
                return
            p = self.new_para(container)
            self.add_inline(p, node, {"b": tag == "dt"})
            self.strip_trailing(p)
        elif tag in ("ul", "ol"):
            n = 0
            for li in node.children:
                if li.tag != "li":
                    continue
                n += 1
                marker = f"{n}." if tag == "ol" else "•"
                p = self.new_para(container)
                p.paragraph_format.left_indent = Cm(0.6 * (list_level + 1))
                p.paragraph_format.first_line_indent = Cm(-0.5)
                p.add_run(marker + "\t")
                inline = Node("span")
                nested = []
                for ch in li.children:
                    (nested if ch.tag in ("ul", "ol") else inline.children).append(ch)
                self.add_inline(p, inline)
                self.strip_trailing(p)
                for sub in nested:
                    self.block(container, sub, list_level + 1)
        elif tag == "table":
            self.table(container, node)
        elif tag == "hr":
            pass
        else:  # containers and li outside lists
            self.blocks(container, node, list_level)

    # -------- tables
    def table(self, container, node):
        rows = []
        cols = []

        def walk(n):
            for c in n.children:
                if c.tag == "tr":
                    rows.append(c)
                elif c.tag in ("thead", "tbody", "tfoot"):
                    walk(c)
                elif c.tag == "colgroup":
                    cols.extend(x for x in c.children if x.tag == "col")
                elif c.tag == "col":
                    cols.append(c)

        walk(node)
        if not rows:
            return
        # grid with colspan/rowspan
        grid = []  # list of rows, each a list of (cell_node, is_origin, span info)
        occupied = {}
        ncols = 0
        for r, tr in enumerate(rows):
            c = 0
            for cell in (x for x in tr.children if x.tag in ("td", "th")):
                while (r, c) in occupied:
                    c += 1
                cs = int(cell.attrs.get("colspan", 1) or 1)
                rs = int(cell.attrs.get("rowspan", 1) or 1)
                for dr in range(rs):
                    for dc in range(cs):
                        occupied[(r + dr, c + dc)] = (cell, r, c, rs, cs)
                c += cs
            ncols = max(ncols, max([k[1] for k in occupied if k[0] == r], default=-1) + 1)
        nrows = len(rows)
        table = container.add_table(rows=nrows, cols=ncols)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        table.autofit = False
        set_fixed_layout(table)
        if self.page.table_borders:
            set_table_borders(table)

        widths = self.columns.get(node.attrs.get("id", ""))
        if not widths and cols:
            ws = [css_width_cm(c) for c in cols]
            if all(ws):
                widths = ws
        if widths and len(widths) != ncols:
            self.warnings.append(f"table '{node.attrs.get('id', '?')}': {len(widths)} widths for {ncols} columns")
            widths = None
        if not widths:
            usable = self.page.width_cm - self.page.margins_cm[1] - self.page.margins_cm[3]
            widths = [usable / ncols] * ncols

        done = set()
        for (r, c), (cell_node, r0, c0, rs, cs) in sorted(occupied.items()):
            if (r0, c0) in done or r >= nrows or c >= ncols:
                continue
            done.add((r0, c0))
            cell = table.cell(r0, c0)
            if rs > 1 or cs > 1:
                cell = cell.merge(table.cell(min(r0 + rs - 1, nrows - 1), min(c0 + cs - 1, ncols - 1)))
            cell.paragraphs[0]._element.getparent().remove(cell.paragraphs[0]._element)
            if cell_node.tag == "th":
                bold = Node("strong")
                bold.children = cell_node.children
                wrapper = Node("div")
                wrapper.children = [bold] if not any(ch.tag in BLOCK for ch in cell_node.children) else cell_node.children
                self.blocks(cell, wrapper)
                if self.page.header_fill:
                    set_cell_shading(cell, self.page.header_fill)
                if cell_node.children and any(ch.tag in BLOCK for ch in cell_node.children):
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.bold = True
            else:
                self.blocks(cell, cell_node)
            if not cell.paragraphs:
                cell.add_paragraph()
        for i, col in enumerate(table.columns):  # tblGrid – Word uses it with fixed layout
            col.width = Cm(widths[i])
        for row in table.rows:
            for tc in row._tr.tc_lst:  # per-cell widths, honouring horizontal spans
                start = tc.grid_offset
                span = tc.grid_span
                tc.width = Cm(sum(widths[start:start + span]))
        # trailing paragraph so consecutive tables do not merge
        if hasattr(container, "add_page_break"):
            self.new_para(container)


def clear_body(doc):
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def apply_page(doc, page: PageSetup):
    for s in doc.sections:
        s.page_width = Cm(page.width_cm)
        s.page_height = Cm(page.height_cm)
        s.orientation = WD_ORIENT.LANDSCAPE if page.width_cm > page.height_cm else WD_ORIENT.PORTRAIT
        s.top_margin, s.right_margin, s.bottom_margin, s.left_margin = (Cm(x) for x in page.margins_cm)
    normal = doc.styles["Normal"]
    normal.font.name = page.font
    normal.font.size = Pt(page.size_pt)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    rpr = normal.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(k), page.font)
    normal.paragraph_format.space_after = Pt(page.space_after_pt)
    normal.paragraph_format.line_spacing = page.line_spacing


def export_docx(html_path, docx_path, page: PageSetup | None = None, columns: dict | None = None,
                base_docx=None):
    """Convert html_path to docx_path. Returns a list of warnings (also printed)."""
    page = page or PageSetup()
    text = Path(html_path).read_text(encoding="utf-8")
    root, meta = parse_html(text)
    body = find(root, "body") or root
    if base_docx:
        doc = Document(str(base_docx))
        clear_body(doc)
    else:
        doc = Document()
    apply_page(doc, page)
    if meta.get("titel"):
        doc.core_properties.title = meta["titel"]
    w = Writer(doc, page, columns)
    w.blocks(doc, body)
    # drop an empty trailing paragraph
    paras = doc.paragraphs
    if paras and not paras[-1].text.strip() and len(paras) > 1:
        paras[-1]._element.getparent().remove(paras[-1]._element)
    if "{{" in text and re.search(r"\{\{[^}]+\}\}", re.sub(r"<head>.*?</head>", "", text, flags=re.S)):
        w.warnings.append("placeholders {{…}} left in the document")
    if "[PRÜFEN" in text or "[PRUEFEN" in text:
        w.warnings.append("document contains [PRÜFEN: …] markers")
    doc.save(str(docx_path))
    for msg in w.warnings:
        print("warning:", msg)
    print("written:", docx_path)
    return w.warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("html", nargs="+")
    ap.add_argument("--landscape", action="store_true")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--size", type=float, default=11)
    a = ap.parse_args(argv)
    page = PageSetup(font=a.font, size_pt=a.size)
    if a.landscape:
        page.width_cm, page.height_cm = page.height_cm, page.width_cm
    for h in a.html:
        p = Path(h)
        export_docx(p, p.with_suffix(".docx"), page=page)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
