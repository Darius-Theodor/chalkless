"""Deterministic view tests of the live overview (kern/webapp).

Run:  python kern/tools/tests/test_webapp.py [--out <folder>] [--port-start 8800] [--no-browser-tests]
Standard library + Playwright (installed Edge, else Chrome; no browser download). No pytest needed.
The test builds temporary instance copies itself (kern/ of this folder + kern/instanz-vorlage + synthetic
areas with long and empty contents, an interrupted and a running step, a damaged file), starts the server
on free ports >= --port-start with --no-browser, and checks: /, /api/state, named states, ETag, file
views, port collision (same instance → exit 3; foreign program / other instance → replacement port),
connection lost → shown → restart → reconnected, no full re-render (focus and preview survive), widths
400/600/1280 without horizontal scrolling, language de (du/Sie) and en. Writes results.json and PNGs to
--out. Also the overview as a file (server.py --datei): written, not rewritten when nothing changed, named by
language, no machine path inside, opened from file:// with a working preview and a state that follows the data file.
Every server it starts is stopped at the end. Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RESULTS = []
PROCS = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("PASS " if ok else "FAIL ") + name + (f" – {detail}" if detail and not ok else ""), flush=True)
    return ok


# ------------------------------------------------------------------ synthetic instance
def w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def doc_html(titel, typ, bereich, datum, status="entwurf", complete=True, body=""):
    head = (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{titel}</title>'
            f'<meta name="chalkless.titel" content="{titel}"><meta name="chalkless.typ" content="{typ}">'
            f'<meta name="chalkless.bereich" content="{bereich}"><meta name="chalkless.datum" content="{datum}">'
            f'<meta name="chalkless.status" content="{status}"><meta name="chalkless.vorlage" content="standard">'
            f'<meta name="chalkless.vorlage_version" content="0">'
            '<style>body{background:#ddd}.page{width:210mm;min-height:297mm;margin:10mm auto;padding:20mm;background:#fff}'
            'table{width:100%;border-collapse:collapse}td{border:1px solid #000;padding:4px}</style></head>')
    content = body or ("<h1>" + titel + "</h1>" + "<p>" + "Ein sehr langer Absatz zur Planung. " * 40 + "</p>"
                       "<table><tr><td>Phase</td><td>Inhalt</td><td>Sozialform</td><td>Medien</td><td>Zeit</td></tr>"
                       "<tr><td>Einstieg</td><td>" + "Bildimpuls und Gespräch " * 8 + "</td><td>Plenum</td><td>Tafel</td><td>10</td></tr></table>")
    html = head + '<body><div class="page">' + content + "</div></body>"
    return html + ("</html>\n" if complete else "\n<p>abgeschnitt")


def build_instance(base: Path, *, sprache="Deutsch", anrede="du", fresh=False) -> Path:
    inst = base
    shutil.copytree(REPO / "kern", inst / "kern", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    tpl = inst / "kern" / "instanz-vorlage"
    for d in ("profil", "gedaechtnis", "review"):
        shutil.copytree(tpl / d, inst / d)
    (inst / "eingang").mkdir()
    w(inst / "eingang" / "README.md", "drop folder\n")
    if fresh:
        (inst / "profil" / "rahmen.md").unlink()
        return inst
    today = dt.date.today()
    rahmen = (tpl / "profil" / "rahmen.md").read_text(encoding="utf-8")
    for k, v in (("land", "Testland"), ("region", "Testregion"), ("schulform", "Testschule"), ("status", "ausgebildet"),
                 ("paket", "rahmen/xx-test-schule"), ("kern_version", (inst / "kern" / "VERSION").read_text().strip()),
                 ("pilot", "aus")):
        rahmen = rahmen.replace(f"- {k}: [ ]", f"- {k}: {v}", 1)
    w(inst / "profil" / "rahmen.md", rahmen)
    w(inst / "profil" / "lehrkraft.md", f"""# Lehrkraft

- anrede: {anrede}
- sprache: {sprache}

## Klassen und Fächer (Schuljahr 2026/27)
| Bereich (Ordner) | Klasse | Fach | Stunden/Woche | Tage/Stunden | Lehrwerk / Material |
|---|---|---|---|---|---|
| bereiche/k1-fach-a | K1 | Fach A mit einem ausgesprochen langen Fachnamen zum Umbrechen | 4 | Mo 1, Mi 2 | [ ] |
| bereiche/k2-fach-b | K2 | Fach B | 2 | [ ] | [ ] |
| bereiche/k3-fach-c | K3 | Fach C | 2 | [ ] | [ ] |
| bereiche/k4-fach-d | K4 | Fach D | 1 | [ ] | [ ] |

## Termine
| Datum | Bereich | Art | Thema | Dokument |
|---|---|---|---|---|
| {(today + dt.timedelta(days=5)).isoformat()} | k1-fach-a | Besuch | Thema X | [ ] |
| {(today + dt.timedelta(days=60)).isoformat()} | k2-fach-b | Prüfung | Thema Y | [ ] |
| 2020-01-01 | k2-fach-b | Besuch | vorbei | [ ] |
""")
    w(inst / "profil" / "checks.md", f"""# Checks

| Anlass | zuletzt geprüft | nächster Termin | Status | Notiz |
|---|---|---|---|---|
| setup | {today} | – | erledigt | fertig |
| werkzeuge | {today} | – | erledigt | ok |
| Übergang Halbjahr | – | {(today - dt.timedelta(days=1)).isoformat()} | offen | fällig |
| Übergang Schuljahr | – | {(today + dt.timedelta(days=200)).isoformat()} | offen | später |
| Alter Hinweis | {today} | – | erledigt | ERLEDIGT_SOLL_FEHLEN |
""")
    w(inst / "gedaechtnis" / "vorlieben.md", (tpl / "gedaechtnis" / "vorlieben.md").read_text(encoding="utf-8") + """
## Dokumente
- 2026-11-01 (Chat) [bestätigt] (alle): Feinziele immer nummerieren.
- 2026-11-02 (Chat) [überholt] (stunde): Sicherung immer als Quiz.
""")
    w(inst / "review" / "offen.md", (tpl / "review" / "offen.md").read_text(encoding="utf-8") + "| 2026-11-01 | x | kürzer | offen |\n")
    w(inst / "rahmen" / "xx-test-schule" / "paket.md", """# Paket xx-test-schule

| Baustein | Quelle | Status |
|---|---|---|
| Lehrplan Fach A | Q | geprüft |
| Kalender 2026/27 | Q | gefunden, ungeprüft |
| Recht | – | fehlt |
""")
    stand_tpl = (tpl / "bereich" / "STAND.md").read_text(encoding="utf-8")
    now = dt.datetime.now()
    a = inst / "bereiche" / "k1-fach-a"
    w(a / "STAND.md", f"""# Stand: k1-fach-a
- schuljahr: 2026/27
- sequenz: [Eine sehr lange Sequenz über ein Thema mit vielen Wörtern, die im schmalen Panel umbrechen müssen](sequenzen/x.html) – Teil 2 von 8
- naechstes: Stunde 3 – {"lange Beschreibung " * 12}
- letztes: [Stunde 2](stunden/{today}_stunde_lang.html) · entwurf
- offen: –
- aktiv: –

## Spur
- {today}T08:00 · start · stunde · lang
- {today}T08:20 · fertig · [stunden/{today}_stunde_lang.html]
""")
    w(a / "stunden" / f"{today}_stunde_lang.html",
      doc_html("Stunde mit einem außergewöhnlich langen Titel, der in 400 Pixeln umbrechen muss, ohne zu überlaufen", "stunde", "k1-fach-a", today.isoformat()))
    (a / "stunden" / f"{today}_stunde_lang.pdf").write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    w(a / "stunden" / "2026-10-01_stunde_kaputt.html", doc_html("Abgebrochene Stunde", "stunde", "k1-fach-a", "2026-10-01", complete=False))
    w(a / "bilder" / "01_baum.prompt.md", "---\ntitel: Baum\ntyp: bild\nbereich: k1-fach-a\ndatum: 2026-11-01\nstatus: entwurf\n---\nSTYLE: " + "flat illustration, " * 30 + "\n")
    w(inst / "bereiche" / "k2-fach-b" / "STAND.md", stand_tpl.replace("<bereich>", "k2-fach-b"))
    old = (now - dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    w(inst / "bereiche" / "k3-fach-c" / "STAND.md", f"""# Stand: k3-fach-c
- schuljahr: 2026/27
- sequenz: –
- naechstes: –
- letztes: –
- offen: –
- aktiv: material · wortkarten · {old}

## Spur
- {old} · start · material · wortkarten
""")
    (inst / "bereiche" / "k5-fach-e").mkdir(parents=True)
    (inst / "bereiche" / "k5-fach-e" / "STAND.md").write_bytes(b"# Stand: k5\n- schuljahr: 2026/27\n- offen: \xff\xfe kaputt\n")
    cur = now.strftime("%Y-%m-%dT%H:%M")
    w(inst / "bereiche" / "k4-fach-d" / "STAND.md", stand_tpl.replace("<bereich>", "k4-fach-d").replace("- aktiv: –", f"- aktiv: stunde · einstieg · {cur}"))
    return inst


# ------------------------------------------------------------------ server handling
def free_port(start: int) -> int:
    for p in range(start, start + 400):
        s = socket.socket()
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(("127.0.0.1", p))
            s.close()
            # also nothing listening on another interface variant
            return p
        except OSError:
            s.close()
    raise RuntimeError("no free port")


def start_server(inst: Path, port: int, wait=True):
    p = subprocess.Popen([sys.executable, "-B", "-u", str(inst / "kern" / "webapp" / "server.py"), "--port", str(port), "--no-browser"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    PROCS.append(p)
    if wait:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hallo", timeout=0.5).read()
                return p
            except Exception:
                if p.poll() is not None:
                    return p
                time.sleep(0.1)
    return p


def stop(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=5)


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def run_until_exit(cmd, timeout=15):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip(), round(time.time() - t, 2)


# ------------------------------------------------------------------ tests
def http_tests(inst, port, other_inst, args):
    base = f"http://127.0.0.1:{port}"
    code, _, body = get(base + "/")
    check("GET / answers with the page", code == 200 and b"<title>Chalkless</title>" in body, code)
    code, hdr, body = get(base + "/api/state")
    st = json.loads(body.decode("utf-8"))
    check("GET /api/state names app and instance", st.get("app") == "chalkless-uebersicht" and st["instanz"]["pfad"] == str(inst), st.get("instanz"))
    acts = {a["id"]: a["aktivitaet"] for a in st["bereiche"]}
    check("states: fertig / neu(leer) / unterbrochen / wird erstellt / Datei beschädigt",
          acts == {"k1-fach-a": "fertig", "k2-fach-b": "leer", "k3-fach-c": "unterbrochen", "k4-fach-d": "wird erstellt",
                  "k5-fach-e": "defekt"}, acts)
    check("damaged files are named (cut-off document, non-UTF-8 STAND)",
          any("kaputt" in d for d in st["defekt"]) and any("k5-fach-e/STAND.md" in d for d in st["defekt"]), st["defekt"])
    wann = {c["anlass"]: c["wann"] for c in st["checks"]}
    check("reminders: erledigt hidden, fällig and später separate",
          wann == {"Übergang Halbjahr": "faellig", "Übergang Schuljahr": "spaeter"}, wann)
    check("past dates are not shown", all(t["datum"] >= st["heute"] for t in st["termine"]), st["termine"])
    raw = json.dumps({k: st[k] for k in ("bereiche", "checks", "termine", "rahmen")}, ensure_ascii=False)
    check("no raw placeholder [ ] in shown values", "[ ]" not in raw)
    check("preferences listed", [p["zustand"] for p in st["vorlieben"]] == ["bestätigt", "überholt"], st["vorlieben"])
    etag = hdr.get("ETag")
    code2, _, _ = get(base + "/api/state", {"If-None-Match": etag})
    check("unchanged state answers 304 (ETag)", etag and code2 == 304, code2)
    pdf = next(e for a in st["bereiche"] for d in a["dokumente"] for e in d["exporte"] if e.endswith(".pdf"))
    code, hdr, _ = get(base + "/datei/" + urllib.request.quote(pdf))
    check("PDF is shown inline, not forced as download", code == 200 and hdr.get("Content-Disposition", "").startswith("inline"), hdr.get("Content-Disposition"))
    code, hdr, body = get(base + "/datei/bereiche/k1-fach-a/bilder/01_baum.prompt.md")
    check(".prompt.md is a readable text page", code == 200 and hdr.get("Content-Type", "").startswith("text/html") and b"<pre>" in body, hdr.get("Content-Type"))
    h = next(d["pfad"] for a in st["bereiche"] for d in a["dokumente"] if d["pfad"].endswith("lang.html"))
    code, _, body = get(base + "/datei/" + urllib.request.quote(h) + "?ansicht=lesen")
    check("reading view injects the reflow style", b"chalkless-lesefassung" in body)
    code, _, _ = get(base + "/datei/profil/lehrkraft.md")
    check("profile files are not served", code == 404, code)
    code, _, _ = get(base + "/datei/..%2F..%2Fwindows%2Fwin.ini")
    check("path traversal refused", code in (403, 404), code)

    # port collision: same instance
    rc, out, secs = run_until_exit([sys.executable, "-B", str(inst / "kern/webapp/server.py"), "--port", str(port), "--no-browser"])
    check("second start, same instance: says 'läuft schon', exit 3, starts nothing", rc == 3 and "läuft schon" in out, f"rc={rc} {out}")
    RESULTS[-1]["output"] = out
    # foreign program on a port
    fport = free_port(port + 30)
    blocker = socket.socket()
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        blocker.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    blocker.bind(("127.0.0.1", fport))
    blocker.listen(5)
    p = start_server(inst, fport, wait=False)
    line = ""
    t = time.time()
    while time.time() - t < 15 and "läuft:" not in line:
        line += p.stdout.readline()
    alt = None
    for tok in line.replace("/", " ").replace(":", " ").split():
        if tok.isdigit() and int(tok) > fport and int(tok) <= fport + 20:
            alt = int(tok)
    ok = "belegt durch ein anderes Programm" in line and alt is not None
    if ok:
        code, _, body = get(f"http://127.0.0.1:{alt}/api/hallo")
        ok = code == 200 and json.loads(body)["instanz"]["pfad"] == str(inst)
    check("port taken by another program: says so, takes a replacement port", ok, line.strip())
    RESULTS[-1]["output"] = line.strip()
    stop(p)
    blocker.close()
    # another Chalkless folder on the port
    oport = free_port(port + 60)
    po = start_server(other_inst, oport)
    p = start_server(inst, oport, wait=False)
    line = ""
    t = time.time()
    while time.time() - t < 15 and "läuft:" not in line:
        line += p.stdout.readline()
    check("port taken by the overview of another folder: named, replacement port", "anderen Ordners" in line and "stattdessen Port" in line, line.strip())
    RESULTS[-1]["output"] = line.strip()
    stop(p)
    stop(po)
    # exclusive bind: a raw second bind on the running port fails
    s = socket.socket()
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        bound = True
    except OSError:
        bound = False
    finally:
        s.close()
    check("port is bound exclusively (a SO_REUSEADDR bind fails)", not bound)


def browser_tests(inst, port, out: Path, en_inst, sie_inst, fresh_inst, args):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        check("playwright available", False, "not installed – browser checks skipped")
        return None
    base = f"http://127.0.0.1:{port}"
    srv = {"p": None}
    with sync_playwright() as pw:
        browser = None
        for ch in ("msedge", "chrome"):
            try:
                browser = pw.chromium.launch(channel=ch, headless=True)
                RESULTS.append({"name": "browser channel", "ok": True, "detail": ch})
                break
            except Exception as e:  # noqa: BLE001
                last = e
        if browser is None:
            check("browser channel msedge/chrome", False, last)
            return None
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
        today = dt.date.today().isoformat()
        doc = f"bereiche/k1-fach-a/stunden/{today}_stunde_lang.html"
        views = {"ueberblick": "#heute", "bereich": "#b:k1-fach-a", "vorschau": f"#b:k1-fach-a/{doc}",
                 "unterbrochen": "#b:k3-fach-c", "leer": "#b:k2-fach-b", "gemerkt": "#gemerkt", "sagen": "#sagen"}
        for width in (400, 600, 1280):
            page.set_viewport_size({"width": width, "height": 900})
            for name, h in views.items():
                page.goto(base + "/" + h)
                page.wait_for_selector("body[data-conn='ok']", timeout=10000)
                page.wait_for_timeout(300)
                if name == "vorschau":
                    page.wait_for_function("(() => { const f = document.querySelector('#preview iframe'); const d = f && f.contentDocument;"
                                           " return d && d.readyState === 'complete' && d.body && d.body.innerText.length > 0; })()", timeout=10000)
                sw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
                check(f"{width}px {name}: no horizontal scrolling", sw[0] <= sw[1], sw)
                txt = page.inner_text("body")
                bad = [m for m in ("[ ]", "naechstes", "aktiv:", today + "T", "ERLEDIGT_SOLL_FEHLEN", "undefined", "Warteschlange") if m in txt]
                check(f"{width}px {name}: no raw keys, placeholders or ISO times", not bad, bad)
                page.screenshot(path=str(out / f"{width}_{name}.png"), full_page=True)
                if name == "vorschau":
                    iw = page.evaluate("(() => { const f = document.querySelector('#preview iframe'); const d = f.contentDocument; return [d.documentElement.scrollWidth, f.clientWidth]; })()")
                    if width < 860:
                        check(f"{width}px preview: document reflowed to the frame width (reading view)", iw[0] <= iw[1] + 1, iw)
            nav_ok = page.evaluate("(() => { const n = document.getElementById('nav'); return n.scrollHeight <= 60; })()")
            check(f"{width}px navigation stays one row", nav_ok)
        # a11y basics
        page.goto(base + "/#b:k1-fach-a")
        page.wait_for_selector("body[data-conn='ok']")
        check("aria-current marks the open tab", page.evaluate("document.querySelector('nav a[aria-current=page]')?.textContent || ''").startswith("K1"))
        check("aria-live status region and color-scheme present",
              page.evaluate("!!document.querySelector('[aria-live]') && !!document.querySelector('meta[name=color-scheme]')"))
        small = page.evaluate("""[...document.querySelectorAll('nav a, a.doc, a.ex, button')].filter(e => e.offsetParent)
              .map(e => e.getBoundingClientRect()).filter(r => r.height < 24 || r.width < 24).length""")
        check("targets at least 24 px", small == 0, small)
        anim = page.evaluate("getComputedStyle(document.querySelector('.pill') || document.body).animationName")
        check("no animation with reduced motion", anim in ("none", ""), anim)
        check("German, du", page.evaluate("document.documentElement.lang") == "de" and "Was du sagen kannst" in page.inner_text("nav"))

        # no full re-render: preview and focus survive a poll and an unrelated change
        page.goto(base + "/" + views["vorschau"])
        page.wait_for_selector("body[data-conn='ok']")
        page.evaluate("document.querySelector('#preview iframe').dataset.marke = 'x'")
        page.focus("nav a[aria-current=page]")
        page.wait_for_timeout(16500)  # one fallback poll
        st = inst / "bereiche" / "k2-fach-b" / "STAND.md"
        st.write_text(st.read_text(encoding="utf-8").replace("- offen: –", "- offen: neu eingetragen"), encoding="utf-8")
        page.wait_for_timeout(3000)  # change event → reload of the state
        kept = page.evaluate("[document.querySelector('#preview iframe')?.dataset.marke, document.activeElement?.getAttribute('aria-current')]")
        check("no full re-render: preview frame and focus survive poll and change", kept == ["x", "page"], kept)
        page.goto(base + "/#heute")
        page.wait_for_selector("body[data-conn='ok']")
        check("change shows up without reload", "neu eingetragen" in page.inner_text("main"))
        live1 = page.inner_text("#live")
        page.wait_for_timeout(2000)
        check("live label does not tick", page.inner_text("#live") == live1 and ":" not in live1.split("–")[0], live1)

        # server gone → named → back
        for p in list(PROCS):
            if p.args and str(port) in p.args and p.poll() is None:
                stop(p)
        page.wait_for_selector("body[data-conn='weg']", timeout=20000)
        gone_txt = page.inner_text("#live")
        page.screenshot(path=str(out / "1280_verbindung-weg.png"))
        check("server stopped: page says 'Verbindung weg'", "Verbindung weg" in gone_txt, gone_txt)
        srv["p"] = start_server(inst, port)
        try:
            page.wait_for_selector("body[data-conn='ok']", timeout=25000)
            check("server back: page reconnects by itself", "wieder verbunden" in page.inner_text("#live"), page.inner_text("#live"))
        except Exception as e:  # noqa: BLE001
            check("server back: page reconnects by itself", False, e)

        # languages and empty state on further instances
        for label, inst2, expect in (("en", en_inst, ("en", "Overview", "What you can say")),
                                     ("Sie", sie_inst, ("de", "Überblick", "Was Sie sagen können")),
                                     ("frisch", fresh_inst, ("de", "Willkommen bei Chalkless", "Richte meinen Arbeitsbereich ein"))):
            p2port = free_port(port + 90)
            p2 = start_server(inst2, p2port)
            for width in (400, 1280):
                page.set_viewport_size({"width": width, "height": 900})
                page.goto(f"http://127.0.0.1:{p2port}/#{'sagen' if label != 'frisch' else 'heute'}")
                page.wait_for_selector("body[data-conn='ok']")
                page.wait_for_timeout(300)
                body = page.inner_text("body")
                sw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
                ok = page.evaluate("document.documentElement.lang") == expect[0] and expect[1] in body and expect[2] in body and sw[0] <= sw[1]
                if label == "frisch":
                    ok = ok and page.evaluate("document.getElementById('nav').children.length") == 0
                check(f"{width}px language/state {label}", ok, body[:200])
                page.screenshot(path=str(out / f"{width}_{label}.png"), full_page=True)
            stop(p2)
        check("no script errors in the page", not errors, errors[:5])
        browser.close()
    return srv["p"]


def file_tests(inst: Path, en_inst: Path, out: Path, args):
    """The overview written into the folder (no server)."""
    cmd = lambda i: [sys.executable, "-B", str(i / "kern/webapp/server.py"), "--datei"]
    rc, text, _ = run_until_exit(cmd(inst))
    page, data = inst / "Übersicht.html", inst / "uebersicht-daten.js"
    check("file: --datei exits 0 and names the page", rc == 0 and "Übersicht.html" in text, text.strip())
    check("file: page and data file written", page.is_file() and data.is_file())
    src = page.read_text(encoding="utf-8") if page.is_file() else ""
    check("file: state built into the page", "window.CHALKLESS_STATE = {" in src and "window.CHALKLESS_STATIC" in src)
    check("file: no path of this machine in the page", str(inst) not in src and json.dumps(str(inst)).strip('"') not in src)
    before = (page.stat().st_mtime_ns, data.stat().st_mtime_ns) if page.is_file() and data.is_file() else None
    time.sleep(0.05)
    run_until_exit(cmd(inst))
    check("file: second run with no change rewrites nothing",
          before == (page.stat().st_mtime_ns, data.stat().st_mtime_ns))
    run_until_exit(cmd(en_inst))
    check("file: English instance gets Overview.html", (en_inst / "Overview.html").is_file() and not (en_inst / "Übersicht.html").exists())
    if args.no_browser_tests:
        return
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as pw:
        browser = None
        for channel in ("msedge", "chrome"):
            try:
                browser = pw.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            check("file: a browser to open the page", False, "neither Edge nor Chrome")
            return
        pg = browser.new_context(viewport={"width": 1000, "height": 800}).new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(page.as_uri())
        pg.wait_for_timeout(500)
        check("file: opened from file://, areas in the navigation", pg.locator("#nav a").count() >= 3)
        check("file: label says it updates by itself", "von selbst" in pg.inner_text("#live"), pg.inner_text("#live"))
        pg.locator("#nav a").nth(1).click()
        pg.wait_for_timeout(300)
        docs = pg.locator("a.doc[data-k^='doc-']")
        if check("file: documents listed in the area", docs.count() >= 1):
            docs.first.click()
            pg.wait_for_timeout(600)
            frame_src = pg.get_attribute("iframe", "src") or ""
            check("file: preview uses a relative path", frame_src.startswith("bereiche/"), frame_src)
        pg.screenshot(path=str(out / "datei-vorschau.png"))
        old = data.read_text(encoding="utf-8")
        data.write_text(old.replace('"eingang": [', '"eingang": ["nachgezogen.pdf", ', 1), encoding="utf-8")
        pg.goto(page.as_uri() + "#heute")
        pg.wait_for_timeout(5500)
        check("file: an open page follows the data file without reload", "nachgezogen.pdf" in pg.inner_text("body"))
        data.write_text(old, encoding="utf-8")
        check("file: no script errors", not errors, "; ".join(errors))
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="folder for results.json and screenshots")
    ap.add_argument("--port-start", type=int, default=8800)
    ap.add_argument("--no-browser-tests", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="chalkless-webtest-out-"))
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="chalkless-webtest-"))
    t0 = time.time()
    try:
        inst = build_instance(tmp / "instanz")
        other = build_instance(tmp / "andere")
        en = build_instance(tmp / "en", sprache="English", anrede="you")
        sie = build_instance(tmp / "sie", anrede="Sie")
        fresh = build_instance(tmp / "frisch", fresh=True)
        port = free_port(max(8800, args.port_start))
        start_server(inst, port)
        http_tests(inst, port, other, args)
        if not args.no_browser_tests:
            browser_tests(inst, port, out, en, sie, fresh, args)
        file_tests(inst, en, out, args)
    finally:
        for p in PROCS:
            stop(p)
        shutil.rmtree(tmp, ignore_errors=True)
    n_fail = sum(1 for r in RESULTS if not r["ok"])
    summary = {"when": dt.datetime.now().isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1),
               "passed": len(RESULTS) - n_fail, "failed": n_fail, "results": RESULTS,
               "servers_left_running": sum(1 for p in PROCS if p.poll() is None)}
    (out / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{summary['passed']} passed, {n_fail} failed – {out / 'results.json'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
