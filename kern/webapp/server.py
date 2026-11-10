"""Chalkless live overview – a local, read-only web app.

Usage (from anywhere):  python kern/webapp/server.py [--port 8765] [--no-browser]
                        python kern/webapp/server.py --datei     (no server: writes the overview as a file)
Standard library only. Binds to 127.0.0.1 only. The instance is the folder two levels above this file
(not the current directory). Watches the instance folders and pushes a change event (Server-Sent Events);
the page also polls /api/state with an ETag as a fallback and re-renders only what changed.
There is no input: the teacher talks to the agent in the chat, this page only shows what is saved.

--datei is for hosts where a local server cannot reach the teacher's browser (the agent works in a separate
environment, or Python exists only there): it writes the same page with the current state into the folder
(Übersicht.html / Overview.html plus uebersicht-daten.js) and exits. The teacher opens the page with a double
click; an open page reads the data file every few seconds and shows a new state without a reload. The agent
runs it again after every finished step. Exit code 0.

Start and port collision (before binding, the port is asked who is there):
  - nothing there            → start on the port.
  - the overview of THIS instance answers → print "läuft schon: <url>", open it (unless --no-browser),
                                start nothing, exit code 3.
  - something else (another program or the overview of another Chalkless folder)
                             → say so, take the next free port of the following 20 and start there.
  - no free port             → say so, exit code 4.
Exit codes: 0 stopped normally (Ctrl+C / window closed) · 2 wrong arguments · 3 already running for this
instance (nothing started) · 4 port taken by something else and no free replacement port.
The port is bound exclusively (no SO_REUSEADDR; on Windows SO_EXCLUSIVEADDRUSE), so a second start
can never bind the same port twice.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import mimetypes
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "kern" / "tools"))
from check_instance import aktiv_state, kv_lines, parse_stand, read_meta, unset  # noqa: E402

APP = "chalkless-uebersicht"
INSTANCE_ID = hashlib.sha256(str(ROOT).lower().encode("utf-8")).hexdigest()[:16]
WATCH = ("bereiche", "profil", "gedaechtnis", "review", "eingang", "rahmen", "vorlagen", "kern/VERSION")
SERVE = ("bereiche", "vorlagen", "beispiele", "rahmen", "archiv")  # folders whose files may be opened
EXPORT_EXT = (".pdf", ".docx", ".pptx")
HIDDEN_CHECKS = {"werkzeuge", "pilot-export", "pilot-hinweis"}  # rows the agent handles alone
STATIC_PAGE = {"de": "Übersicht.html", "en": "Overview.html"}  # by the language of the instance
STATIC_DATA = "uebersicht-daten.js"
EXIT_ALREADY_RUNNING = 3
EXIT_NO_PORT = 4


# ------------------------------------------------------------------ reading the brain
def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def damaged(path: Path) -> bool:
    try:
        path.read_bytes().decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True
    except OSError:
        return False


def md_tables(text: str):
    """Yield (header, rows) for every Markdown table; cells stripped, links kept as text."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


def table_with(text: str, *words):
    for header, rows in md_tables(text):
        h = " ".join(header).lower()
        if all(w.lower() in h for w in words):
            return header, rows
    return None, []


def clean(s: str) -> str:
    """Display text: no Markdown links/backticks, no skeleton placeholders `[ ]`, no `(hint)` after them."""
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s or "")
    s = s.replace("`", "").replace("**", "")
    s = re.sub(r"\[\s*\]\s*(\([^)]*\))?", "", s)  # "[ ]  (hint)" and bare "[ ]"
    s = s.strip()
    return "" if s in ("–", "-", "—") else s


def as_dicts(header, rows):
    out = []
    for r in rows:
        if not any(clean(c) for c in r):
            continue
        out.append({header[k].lower(): (r[k] if k < len(r) else "") for k in range(len(header))})
    return out


def kv_front_matter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def html_complete(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 400))
            return b"</html>" in fh.read().lower()
    except OSError:
        return False


def documents(area_dir: Path):
    docs = []
    for h in sorted(area_dir.rglob("*.html")):
        meta = read_meta(h)
        rel = h.relative_to(ROOT).as_posix()
        exports = [h.with_suffix(e).relative_to(ROOT).as_posix() for e in EXPORT_EXT if h.with_suffix(e).exists()]
        docs.append({
            "pfad": rel,
            "ordner": h.parent.name,
            "titel": clean(meta.get("titel", "")) or h.stem,
            "typ": meta.get("typ") or h.parent.name,
            "datum": meta.get("datum", ""),
            "status": meta.get("status", ""),
            "variante": clean(meta.get("variante", "")),
            "geaendert": clean(meta.get("geaendert", "")),
            "exporte": exports,
            "defekt": not html_complete(h),
            "mtime": int(h.stat().st_mtime),
        })
    for pdf in sorted(area_dir.rglob("*.pdf")):
        if not pdf.with_suffix(".html").exists():  # a PDF whose HTML is missing: still show it, marked
            docs.append({"pfad": pdf.relative_to(ROOT).as_posix(), "ordner": pdf.parent.name, "titel": pdf.stem,
                         "typ": pdf.parent.name, "datum": "", "status": "", "variante": "", "geaendert": "",
                         "exporte": [], "defekt": False, "ohne_html": True, "mtime": int(pdf.stat().st_mtime)})
    for p in sorted(area_dir.rglob("*.prompt.md")):
        rel = p.relative_to(ROOT).as_posix()
        fm = kv_front_matter(read(p))
        imgs = [p.with_name(p.name.replace(".prompt.md", e)).relative_to(ROOT).as_posix()
                for e in (".png", ".jpg", ".jpeg", ".webp") if p.with_name(p.name.replace(".prompt.md", e)).exists()]
        docs.append({"pfad": rel, "ordner": "bilder", "titel": clean(fm.get("titel", "")) or p.name[:-10], "typ": "bild",
                     "datum": fm.get("datum", ""), "status": fm.get("status", ""), "variante": "",
                     "geaendert": "", "exporte": imgs, "defekt": False, "mtime": int(p.stat().st_mtime)})
    docs.sort(key=lambda d: (d["datum"], d["mtime"]), reverse=True)
    return docs


SPUR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:T(\d{2}:\d{2}))?\s*·\s*([^·]+?)\s*(?:·\s*(.*))?$")


def spur_entry(line: str) -> dict:
    """'2026-11-10T19:02 · start · stunde · igel' → {datum, zeit, art, text}; anything else → text only."""
    m = SPUR_RE.match(line.strip())
    if not m:
        return {"datum": "", "zeit": "", "art": "", "text": clean(line)}
    text = clean(re.sub(r"[\[\]]", "", m.group(4) or ""))
    return {"datum": m.group(1), "zeit": m.group(2) or "", "art": m.group(3).strip().lower(), "text": text}


def aktiv_parts(aktiv: str) -> dict:
    """'stunde · igel-zuhause · 2026-11-10T19:02' → {typ, slug, datum, zeit}."""
    if unset(aktiv):
        return {}
    parts = [p.strip() for p in aktiv.split("·")]
    out = {"typ": "", "slug": "", "datum": "", "zeit": ""}
    rest = []
    for p in parts:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", p)
        if m:
            out["datum"], out["zeit"] = m.group(1), m.group(2)
        else:
            rest.append(clean(p))
    if rest:
        out["typ"] = rest[0]
    if len(rest) > 1:
        out["slug"] = " · ".join(rest[1:])
    return out


def area_info(lk_text: str) -> dict:
    h, rows = table_with(lk_text, "bereich")
    out = {}
    for d in as_dicts(h, rows):
        joined = " ".join(d.values())
        m = re.search(r"bereiche/([a-z0-9-]+)", joined) or re.search(r"^\s*`?([a-z0-9-]+)`?\s*$", d.get("bereich (ordner)", ""))
        if m:
            out[m.group(1)] = {k: clean(v) for k, v in d.items()}
    return out


def checks_view(rows, today: str):
    """Reminders for the page: erledigt is hidden; due (fällig) and later (später/irgendwann) are separate."""
    out = []
    for d in rows:
        anlass = clean(d.get("anlass", ""))
        status = clean(d.get("status", "")).lower()
        if not anlass or anlass.lower() in HIDDEN_CHECKS or status.startswith("erledigt"):
            continue
        datum = clean(d.get("nächster termin", d.get("naechster termin", "")))
        m = re.search(r"\d{4}-\d{2}-\d{2}", status) if status.startswith("verschoben") else None
        if m:
            datum = m.group(0)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", datum or ""):
            datum = ""
        if datum and datum > today:
            wann = "spaeter"
        elif datum or status.startswith("offen"):
            wann = "faellig"
        else:
            wann = "irgendwann"
        out.append({"anlass": anlass, "datum": datum, "wann": wann, "notiz": clean(d.get("notiz", "")),
                    "setup": anlass.lower() == "setup"})
    return out


def preferences(text: str):
    out = []
    for line in text.splitlines():
        m = re.match(r"^- (\d{4}-\d{2}-\d{2}) \(([^)]*)\) \[(bestätigt|vermutet|überholt)\] \(([^)]*)\): (.+)$", line.strip())
        if m:
            out.append({"datum": m.group(1), "zustand": m.group(3), "geltung": clean(m.group(4)), "regel": clean(m.group(5))})
    return out


def language(lk: dict) -> dict:
    sprache = clean(lk.get("sprache", ""))
    anrede = clean(lk.get("anrede", "")).lower()
    s = sprache.lower()
    if not s or s.startswith(("de", "deutsch", "german")):
        code = "de"
    elif s.startswith(("en", "english", "englisch")):
        code = "en"
    else:
        code = "en"  # page texts exist in German and English; other languages fall back to English
    formal = anrede.startswith("sie") or anrede in ("formal", "förmlich")
    return {"sprache": sprache, "code": code, "anrede": anrede, "formell": formal}


def state():
    now = dt.datetime.now()
    today = now.date().isoformat()
    s = {"app": APP, "instanz": {"id": INSTANCE_ID, "pfad": str(ROOT)},
         "heute": today, "kern_version": read(ROOT / "kern" / "VERSION").strip(), "defekt": []}
    rahmen_md = ROOT / "profil" / "rahmen.md"
    r = kv_lines(read(rahmen_md)) if rahmen_md.exists() else {}
    s["eingerichtet"] = rahmen_md.exists() and not unset(r.get("land"))
    s["profil_da"] = rahmen_md.exists()
    paket = (r.get("paket") or "").replace("rahmen/", "").strip("/ ")
    pk = {"id": "", "bausteine": []}
    if paket and not unset(paket):
        pk["id"] = clean(paket)
        h, rows = table_with(read(ROOT / "rahmen" / paket / "paket.md"), "baustein", "status")
        for d in as_dicts(h, rows):
            pk["bausteine"].append({"baustein": clean(d.get("baustein", "")), "status": clean(d.get("status", ""))})
    s["rahmen"] = {k: clean(r.get(k, "")) for k in
                   ("land", "region", "schulform", "status", "status_begriff", "ausbildung_ende")}
    s["paket"] = pk

    lk_text = read(ROOT / "profil" / "lehrkraft.md")
    s["sprache"] = language(kv_lines(lk_text))
    areas_meta = area_info(lk_text)
    h, rows = table_with(lk_text, "datum", "art")
    s["termine"] = [t for t in ({k: clean(v) for k, v in d.items()} for d in as_dicts(h, rows))
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", t.get("datum", "")) and t["datum"] >= today]

    areas = []
    broot = ROOT / "bereiche"
    for a in sorted(p for p in broot.iterdir() if p.is_dir()) if broot.exists() else []:
        st_path = a / "STAND.md"
        problem = ""
        stand = {}
        if not st_path.exists():
            problem = "stand_fehlt"
        elif damaged(st_path):
            problem = "stand_defekt"
            s["defekt"].append(st_path.relative_to(ROOT).as_posix())
        else:
            stand = parse_stand(st_path)
        act, _ = aktiv_state(stand.get("aktiv"), now)
        docs = documents(a)
        for d in docs:
            if d.get("defekt"):
                s["defekt"].append(d["pfad"])
        if act == "ruhig":
            act = "fertig" if docs else "leer"
        if problem == "stand_defekt":
            act = "defekt"
        fields = {k: clean(v) for k, v in stand.items() if k not in ("spur", "aktiv")}
        areas.append({"id": a.name, "info": areas_meta.get(a.name, {}),
                      "stand": {k: v for k, v in fields.items() if v},
                      "spur": [spur_entry(l) for l in stand.get("spur", [])[-6:]],
                      "aktivitaet": act, "aktiv": aktiv_parts(stand.get("aktiv", "")),
                      "problem": problem, "dokumente": docs})
    s["bereiche"] = areas

    h, rows = table_with(read(ROOT / "profil" / "checks.md"), "status")
    s["checks"] = checks_view(as_dicts(h, rows), today)
    h, rows = table_with(read(ROOT / "review" / "offen.md"), "status")
    s["offen"] = sum(1 for d in as_dicts(h, rows) if not clean(d.get("status", "")).lower().startswith("erledigt"))
    inc = ROOT / "eingang"
    s["eingang"] = sorted(p.name for p in inc.iterdir() if p.name != "README.md") if inc.exists() else []
    vroot = ROOT / "vorlagen"
    s["vorlagen"] = []
    for t in sorted(p for p in vroot.iterdir() if p.is_dir()) if vroot.exists() else []:
        m = re.search(r"version:\s*(\d+)", read(t / "herkunft.md"))
        s["vorlagen"].append({"typ": t.name, "version": m.group(1) if m else ""})
    vl = ROOT / "gedaechtnis" / "vorlieben.md"
    if damaged(vl):
        s["defekt"].append("gedaechtnis/vorlieben.md")
    s["vorlieben"] = preferences(read(vl))
    for f in ("profil/rahmen.md", "profil/lehrkraft.md", "profil/checks.md"):
        if damaged(ROOT / f):
            s["defekt"].append(f)
    return s


def write_static() -> str:
    """Overview without a server: the page with the state built in, and the state again as a small script the
    open page polls. Files are only rewritten when their content changes. Returns the name of the page."""
    s = state()
    s["instanz"] = {"id": INSTANCE_ID}  # no path of this machine in a file that lies in the folder
    data = json.dumps(s, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    name = STATIC_PAGE.get(s["sprache"]["code"], STATIC_PAGE["en"])
    page = (HERE / "app.html").read_text(encoding="utf-8")
    head = (f'<script>window.CHALKLESS_STATIC = {{"daten": "{STATIC_DATA}"}}; '
            f'window.CHALKLESS_STATE = {data};</script>' + "\n<script>")
    page = page.replace("<script>", head, 1)
    for fname, text in ((STATIC_DATA, f"window.chalklessStand && window.chalklessStand({data});" + "\n"), (name, page)):
        target = ROOT / fname
        if not target.exists() or read(target) != text:
            target.write_bytes(text.encode("utf-8"))
    for other in STATIC_PAGE.values():  # the language changed: the page of the other language is stale
        if other != name and (ROOT / other).exists():
            (ROOT / other).unlink()
    return name


def fingerprint():
    parts = []
    for w in WATCH:
        p = ROOT / w
        if p.is_file():
            parts.append((w, p.stat().st_mtime_ns, p.stat().st_size))
        elif p.is_dir():
            for f in p.rglob("*"):
                try:
                    stt = f.stat()
                except OSError:
                    continue
                parts.append((f.as_posix(), stt.st_mtime_ns, stt.st_size))
    return hash(tuple(sorted(parts)))


class Watcher(threading.Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.version = 0
        self.cond = threading.Condition()
        self.fp = fingerprint()

    def run(self):
        while True:
            time.sleep(1.0)
            fp = fingerprint()
            if fp != self.fp:
                self.fp = fp
                with self.cond:
                    self.version += 1
                    self.cond.notify_all()


WATCHER = Watcher()

# Screen reading view of a document: the print layout (A4 width) is reflowed to the frame width, so a
# document stays readable in a 400 px side panel. Print and PDF are not affected (screen only).
READ_CSS = """<style id="chalkless-lesefassung">@media screen{html,body{width:auto!important;min-width:0!important;
max-width:100%!important;margin:0!important;padding:0!important;background:#fff!important;}
body>*{box-sizing:border-box!important;width:auto!important;min-width:0!important;max-width:100%!important;
margin-left:0!important;margin-right:0!important;padding:12px!important;box-shadow:none!important;}
*{max-width:100%!important;overflow-wrap:anywhere;}table{width:100%!important;table-layout:auto!important;}
img,svg{height:auto!important;}pre{white-space:pre-wrap!important;}}</style>
<meta name="viewport" content="width=device-width, initial-scale=1">"""


def text_page(title: str, text: str) -> bytes:
    body = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<meta name='color-scheme' content='light dark'><title>{html.escape(title)}</title>"
            "<style>body{margin:0;padding:12px;font:15px/1.5 system-ui,sans-serif}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;margin:0}</style></head>"
            f"<body><pre>{html.escape(text)}</pre></body></html>")
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "chalkless"

    def log_message(self, *args):  # keep the console quiet
        pass

    def send(self, code, body: bytes, ctype: str, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        return self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            return self.send(200, (HERE / "app.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        if path == "/api/hallo":  # who is on this port (used by a second start)
            body = json.dumps({"app": APP, "instanz": {"id": INSTANCE_ID, "pfad": str(ROOT)}}, ensure_ascii=False)
            return self.send(200, body.encode("utf-8"), "application/json; charset=utf-8")
        if path == "/api/state":
            body = json.dumps(state(), ensure_ascii=False, sort_keys=True).encode("utf-8")
            etag = '"' + hashlib.sha256(body).hexdigest()[:20] + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return
            return self.send(200, body, "application/json; charset=utf-8", {"ETag": etag})
        if path == "/api/events":
            return self.events()
        if path.startswith("/datei/"):
            return self.file(urllib.parse.unquote(path[len("/datei/"):]), "lesen" in query.get("ansicht", []))
        self.send(404, b"not found", "text/plain")

    def file(self, rel, lesen=False):
        target = (ROOT / rel).resolve()
        try:
            inside = target.relative_to(ROOT)
        except ValueError:
            return self.send(403, b"forbidden", "text/plain")
        if not inside.parts or inside.parts[0] not in SERVE or not target.is_file():
            return self.send(404, b"not found", "text/plain")
        name = urllib.parse.quote(target.name)
        if target.suffix == ".md":  # prompt files and notes: readable text page, never a raw download
            return self.send(200, text_page(target.name, read(target)), "text/html; charset=utf-8")
        data = target.read_bytes()
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in (".html", ".htm") and lesen:
            txt = data.decode("utf-8", errors="replace")
            m = re.search(r"<head[^>]*>", txt, re.I)
            txt = (txt[:m.end()] + READ_CSS + txt[m.end():]) if m else READ_CSS + txt
            return self.send(200, txt.encode("utf-8"), "text/html; charset=utf-8")
        if ctype.startswith("text/") or target.suffix == ".css":
            ctype += "; charset=utf-8"
        extra = {}
        if target.suffix == ".pdf":
            extra["Content-Disposition"] = f"inline; filename*=UTF-8''{name}"
        elif target.suffix in EXPORT_EXT:  # Word/PowerPoint cannot be shown in a browser
            extra["Content-Disposition"] = f"attachment; filename*=UTF-8''{name}"
        self.send(200, data, ctype, extra)

    def events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        seen = WATCHER.version
        try:
            self.wfile.write(b"retry: 2000\nevent: hallo\ndata: 0\n\n")
            self.wfile.flush()
            while True:
                with WATCHER.cond:
                    WATCHER.cond.wait(timeout=15)
                    v = WATCHER.version
                if v != seen:
                    seen = v
                    self.wfile.write(f"event: geaendert\ndata: {v}\n\n".encode())
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return


class ExclusiveServer(ThreadingHTTPServer):
    """Never shares a port: no SO_REUSEADDR, and on Windows SO_EXCLUSIVEADDRUSE."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def who_is_there(port: int, timeout: float = 1.5):
    """None = nothing answers; 'self' = this instance's overview; else a short description of the occupant."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            pass
    except OSError:
        return None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hallo", timeout=timeout) as resp:
            info = json.loads(resp.read().decode("utf-8"))
        if info.get("app") == APP:
            if (info.get("instanz") or {}).get("id") == INSTANCE_ID:
                return "self"
            return f"die Chalkless-Übersicht eines anderen Ordners ({(info.get('instanz') or {}).get('pfad', '?')})"
    except Exception:
        pass
    return "ein anderes Programm"


def bind(port: int):
    try:
        return ExclusiveServer(("127.0.0.1", port), Handler)
    except OSError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chalkless live overview (read-only). Exit codes: 0 stopped normally, "
                                             "2 wrong arguments, 3 already running for this folder, "
                                             "4 port taken by something else and no free replacement port.")
    ap.add_argument("--port", type=int, default=8765, help="port on 127.0.0.1 (default 8765)")
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    ap.add_argument("--datei", action="store_true",
                    help="no server: write the overview as a file into the folder (opened by double click) and exit")
    a = ap.parse_args(argv)
    if a.datei:
        print(f"Übersicht geschrieben: {write_static()} (im Ordner; Doppelklick öffnet sie)", flush=True)
        return 0
    port = a.port
    occupant = who_is_there(port)
    httpd = None
    if occupant is None:
        httpd = bind(port)
        if httpd is None:  # taken between the question and the bind
            occupant = who_is_there(port) or "ein anderes Programm"
    if occupant == "self":
        url = f"http://localhost:{port}"
        print(f"Die Chalkless-Übersicht dieses Ordners läuft schon: {url} – es wurde nichts neu gestartet.", flush=True)
        if not a.no_browser:
            webbrowser.open(url)
        return EXIT_ALREADY_RUNNING
    if httpd is None:
        for alt in range(port + 1, port + 21):
            if who_is_there(alt, timeout=0.3) == "self":
                url = f"http://localhost:{alt}"
                print(f"Port {port} ist belegt durch {occupant}. Die Übersicht dieses Ordners läuft schon: {url}", flush=True)
                if not a.no_browser:
                    webbrowser.open(url)
                return EXIT_ALREADY_RUNNING
            httpd = bind(alt)
            if httpd is not None:
                print(f"Port {port} ist belegt durch {occupant}. Die Übersicht nimmt stattdessen Port {alt}.", flush=True)
                port = alt
                break
        else:
            print(f"Port {port} ist belegt durch {occupant}, und die Ports {port + 1}–{port + 20} sind auch belegt. "
                  f"Die Übersicht startet nicht. Abhilfe: das andere Programm beenden oder --port <frei> angeben.", flush=True)
            return EXIT_NO_PORT
    WATCHER.start()
    url = f"http://localhost:{port}"
    print(f"Chalkless-Übersicht läuft: {url}  (Fenster offen lassen; schließen beendet sie)", flush=True)
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
