"""Export Chalkless HTML documents to PDF (the standard hand-in format).

The HTML file is the document; the PDF is printed from it by a Chromium-based browser in headless
mode (Microsoft Edge, Google Chrome or Chromium), so page size, margins, fonts and table widths come
from the template's stil.css (@page rules). No Python package is needed.

Usage:
  python kern/tools/pdf_export.py <file.html> [<file.html> ...]   -> <file>.pdf next to each HTML
  python kern/tools/pdf_export.py --check                          -> which browser would be used
  python kern/tools/pdf_export.py --png <file.pdf> --out <dir>     -> one PNG per page in <dir> (needs pypdfium2 + pillow),
                                                                      for the visual comparison in vorlage-ableiten;
                                                                      put <dir> outside the instance (temp folder)

Browser search order: environment variable CHALKLESS_BROWSER, then the usual install paths of Edge,
Chrome and Chromium on Windows, macOS and Linux. If none is found the script says so and exits 2;
the fallback is: open the HTML in any browser -> Drucken -> "Als PDF speichern".
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    # Windows
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
ON_PATH = ["msedge", "microsoft-edge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]


def find_browser():
    env = os.environ.get("CHALKLESS_BROWSER")
    if env and Path(env).exists():
        return env
    for c in CANDIDATES:
        p = Path(os.path.expandvars(c))
        if "%" not in str(p) and p.exists():
            return str(p)
    for name in ON_PATH:
        p = shutil.which(name)
        if p:
            return p
    return None


def page_info(pdf: Path):
    """Return (pages, 'w x h cm') if pypdf is installed, else None."""
    try:
        import pypdf
    except ImportError:
        return None
    r = pypdf.PdfReader(str(pdf))
    box = r.pages[0].mediabox
    w, h = float(box.width) / 72 * 2.54, float(box.height) / 72 * 2.54
    return len(r.pages), f"{w:.1f} x {h:.1f} cm"


def export_pdf(html: Path, browser: str, out: Path | None = None) -> Path:
    html = html.resolve()
    out = (out or html.with_suffix(".pdf")).resolve()
    with tempfile.TemporaryDirectory(prefix="chalkless-pdf-") as profile:
        cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={profile}", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
               "--virtual-time-budget=5000", f"--print-to-pdf={out}", html.as_uri()]
        if out.exists():
            out.unlink()
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"browser did not write {out.name}")
    return out


def render_png(pdf: Path, out_dir: Path, scale: float = 1.5):
    """Render every page of a PDF to PNG (for looking at it). Returns the list of files."""
    import pypdfium2 as pdfium  # optional dependency
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    doc = pdfium.PdfDocument(str(pdf))
    for i in range(len(doc)):
        img = doc[i].render(scale=scale).to_pil()
        f = out_dir / f"{pdf.stem}-s{i + 1}.png"
        img.save(f)
        files.append(f)
    return files


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    args = list(sys.argv[1:] if argv is None else argv)
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--png" in args:
        rest = [a for a in args if a != "--png"]
        out = Path(tempfile.gettempdir()) / "chalkless-pages"
        if "--out" in rest:
            i = rest.index("--out")
            out = Path(rest[i + 1])
            rest = rest[:i] + rest[i + 2:]
        try:
            for a in rest:
                for f in render_png(Path(a), out):
                    print(f"page image: {f}")
        except ImportError as e:
            print(f"page images not available: Python package {e.name!r} is missing – set it up with: python kern/tools/voraussetzungen.py --install (48-hour rule). Compare by facts instead.")
            return 2
        return 0
    browser = find_browser()
    if "--check" in args:
        print(f"browser: {browser}" if browser else "no browser found (set CHALKLESS_BROWSER to Edge/Chrome/Chromium)")
        return 0 if browser else 2
    if not args:
        print(__doc__)
        return 1
    if not browser:
        print("PDF export not available: no Edge, Chrome or Chromium found. "
              "Fallback: open the HTML in a browser -> Drucken -> 'Als PDF speichern'.")
        return 2
    rc = 0
    for a in args:
        src = Path(a)
        if not src.exists() or src.suffix.lower() not in (".html", ".htm"):
            print(f"skip {a}: not an existing .html file")
            rc = 1
            continue
        try:
            out = export_pdf(src, browser)
        except Exception as e:  # report and continue with the next file
            print(f"FAILED {a}: {e}")
            rc = 1
            continue
        info = page_info(out)
        print(f"written: {out.name}" + (f" ({info[0]} pages, {info[1]})" if info else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main())
