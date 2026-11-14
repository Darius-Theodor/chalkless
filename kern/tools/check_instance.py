"""Health and compatibility check of a Chalkless instance against the core.

Usage (from the Chalkless folder):  python kern/tools/check_instance.py [--json]
Standard library only. Prints one line per finding: OK / INFO / WARN / FAIL. Every WARN says in one sentence
what the next session should do.
Exit codes: 0 = no FAIL (there may be WARN/INFO lines), 1 = at least one FAIL, 2 = wrong arguments.
Run it after unpacking a package, at the end of setup, after a core update (kern/VERSION changed) and
when something seems broken. The agent fixes what it reports inside the instance. It does not change the
core to make a warning go away: a core change needs the teacher's explicit consent (kern/regeln.md §10).
What it checks:
  - core version (kern/VERSION) against the instance (profil/rahmen.md kern_version);
  - core files against kern/core-hashes.sha256 (written when the package is built, see kern_hashes.py):
    a changed file with an `aktiv` row in gedaechtnis/kernaenderungen.md is a logged local change (INFO), without
    such a row WARN (a row `zurückgenommen` or `überschrieben durch Update` no longer covers it), a missing file
    WARN (never kern/PILOT: it is optional, a release has none);
  - compatibility: profile fields that the current skeletons (kern/instanz-vorlage/) have and the instance
    lacks (WARN), fields the skeletons no longer know (INFO: old or renamed field), old [vermutet] lines,
    a pilot setting without a pilot build;
  - half states left by an interrupted step: STAND `aktiv` set (with or without a saved file), a trace
    `start` without `fertig`, a document HTML without its PDF or with an older PDF, a PDF without its HTML,
    documents cut off while saving, brain files that are not UTF-8;
  - the tool protocol profil/werkzeuge.md (INFO only: its last run, or that none was written yet);
  - areas, templates, document metadata (also: status geprüft or verwendet while [PRÜFEN: …] marks remain, INFO),
    memory and incoming files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_META = ("titel", "typ", "bereich", "datum", "status", "vorlage", "vorlage_version")
STATUS = {"entwurf", "geprüft", "verwendet"}
PREF_RE = re.compile(r"^- \d{4}-\d{2}-\d{2} \([^)]+\) \[(bestätigt|vermutet|überholt)\] \([^)]+\): .+")
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9-]+_[a-z0-9-]+\.html$")
TEMPLATE_FILES = ("herkunft.md", "vorlage.html", "stil.css", "pruefung.md")
STALE_HOURS = 3


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if (a.get("name") or "").startswith("chalkless."):
                self.meta[a["name"][10:]] = a.get("content", "")


def read_meta(path: Path) -> dict:
    p = MetaParser()
    try:
        p.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # broken HTML still yields what was parsed
        pass
    return p.meta


def kv_lines(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*([a-z_]+):\s*(.*?)(?:\s{2,}\(.*\))?\s*$", line)  # "  (hint)" is a skeleton hint
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2)
    return out


def unset(v) -> bool:
    return v is None or v.strip() in ("", "[ ]", "–", "-") or v.strip().startswith("{{")  # "{{...}}" = template value not filled in


def parse_stand(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text.split("## Spur")[0]
    data = kv_lines(head)
    data["spur"] = [l[2:].strip() for l in text.split("## Spur")[1].splitlines() if l.startswith("- ")] if "## Spur" in text else []
    return data


def aktiv_state(aktiv: str, now=None):
    """Return (state, detail) for the activity trace value of STAND."""
    if unset(aktiv):
        return "ruhig", ""
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", aktiv)
    if not m:
        return "wird erstellt", aktiv
    started = dt.datetime.fromisoformat(m.group(1))
    now = now or dt.datetime.now()
    if (now - started).total_seconds() > STALE_HOURS * 3600:
        return "unterbrochen", aktiv
    return "wird erstellt", aktiv


def _active_row(row: str, rel: str) -> bool:
    """A row of gedaechtnis/kernaenderungen.md for this file whose state is `aktiv` (not taken back, not overwritten)."""
    if f"`{rel}`" not in row and f"| {rel} |" not in row:
        return False
    return any(c.strip().strip("`").lower() == "aktiv" for c in row.strip().strip("|").split("|"))


def core_check(root: Path, add):
    """Shipped core vs. folder; local core changes must be logged (kern/regeln.md §10)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import kern_hashes
    except Exception:
        add("WARN", "kern/tools/kern_hashes.py missing – core changes cannot be detected")
        return
    res = kern_hashes.compare(root)
    if res is None:
        add("INFO", "no core hash list (kern/core-hashes.sha256) – local core changes cannot be detected")
        return
    log = root / "gedaechtnis" / "kernaenderungen.md"
    rows = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
    for rel in res["changed"] + res["added"]:
        what = "changed" if rel in res["changed"] else "added"
        if any(_active_row(row, rel) for row in rows):
            add("INFO", f"core file {rel} {what} locally, logged in gedaechtnis/kernaenderungen.md – a core update may overwrite it")
        else:
            add("WARN", f"core file {rel} {what} without an `aktiv` row in gedaechtnis/kernaenderungen.md – not from this package; "
                        "tell the teacher once, do not restore or keep editing it without their consent")
    # a host that protects folders starting with a dot leaves .claude/ out: that is no damaged package
    host = [rel for rel in res["missing"] if rel.startswith(".claude/") and not (root / ".claude").exists()]
    for rel in res["missing"]:
        if rel in host:
            add("INFO", f"core file {rel} not written – this host allows no .claude folder; only the side panel needs it, "
                        "the overview is the file (kern/regeln.md §11)")
        else:
            add("WARN", f"core file {rel} missing – the package is incomplete; unpack it again (instance files stay)")
    if not (res["changed"] or res["added"] or set(res["missing"]) - set(host)):
        add("OK", "core unchanged against kern/core-hashes.sha256")


SKELETON = Path("kern") / "instanz-vorlage"
NO_PDF_TYPES = {"praesentation", "bild"}  # slides need no PDF (kern/regeln.md §11)
PDF_GRACE_S = 120


def _tables(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i in range(len(lines) - 1):
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            yield [c.strip() for c in lines[i].strip().strip("|").split("|")], i


def compat_check(root: Path, add):
    """Profile fields of the current skeletons vs. the instance (older instance, renamed or removed fields)."""
    for rel in ("profil/rahmen.md", "profil/lehrkraft.md"):
        inst, tpl = root / rel, root / SKELETON / rel
        if not inst.exists() or not tpl.exists():
            continue
        have = kv_lines(inst.read_text(encoding="utf-8", errors="replace"))
        want = kv_lines(tpl.read_text(encoding="utf-8", errors="replace"))
        for k in want:
            if k not in have:
                add("WARN", f"{rel}: field '{k}' missing (instance older than the core) – next session: add the line "
                            f"'- {k}: [ ]' from {(SKELETON / rel).as_posix()} without changing other lines; ask for it only when it is needed")
        for k in have:
            if k not in want:
                add("INFO", f"{rel}: field '{k}' is not in the current skeleton – an old or renamed field; keep its value, "
                            f"move it to the matching new field if there is one, never delete it unasked")
    tpl = root / SKELETON / "profil" / "checks.md"
    inst = root / "profil" / "checks.md"
    if tpl.exists() and inst.exists():
        th = next((h for h, _ in _tables(tpl)), None)
        ih = next((h for h, _ in _tables(inst)), None)
        if th and ih and [c.lower() for c in th] != [c.lower() for c in ih]:
            add("WARN", f"profil/checks.md: columns {ih} differ from the skeleton {th} – next session: rebuild the table "
                        "with the skeleton columns and keep every row")
    stpl = root / SKELETON / "bereich" / "STAND.md"
    want = list(kv_lines(stpl.read_text(encoding="utf-8", errors="replace"))) if stpl.exists() else []
    for st in sorted((root / "bereiche").glob("*/STAND.md")) if (root / "bereiche").exists() else []:
        try:
            have = kv_lines(st.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        miss = [k for k in want if k not in have]
        if miss:
            add("WARN", f"{st.relative_to(root).as_posix()}: keys {', '.join(miss)} missing – next session: add them with '–' "
                        "(the activity trace needs 'aktiv')")
    vl = root / "gedaechtnis" / "vorlieben.md"
    if vl.exists():
        n = len(re.findall(r"\[vermutet\]", vl.read_text(encoding="utf-8", errors="replace")))
        if n:
            add("INFO", f"gedaechtnis/vorlieben.md: {n} old [vermutet] line(s) – they never act; ask once at the next fitting document (kern/regeln.md §5)")
    rahmen = root / "profil" / "rahmen.md"
    if rahmen.exists():
        pilot = (kv_lines(rahmen.read_text(encoding="utf-8", errors="replace")).get("pilot") or "").strip().lower()
        if pilot == "an" and not (root / "kern" / "PILOT").exists():
            add("WARN", "profil/rahmen.md: pilot: an, but this is not a pilot build (kern/PILOT missing) – nothing is recorded; "
                        "next session: set pilot: aus without mentioning it")


def _aktiv_parts(aktiv):
    parts = [p.strip() for p in (aktiv or "").split("·")]
    words = [p for p in parts if p and p not in ("–", "-") and not re.match(r"^\d{4}-\d{2}-\d{2}T", p)]
    return (words[0] if words else ""), (words[1] if len(words) > 1 else "")


def half_states(root: Path, add, now=None):
    """Leftovers of an interrupted step (kern/konventionen.md §4, kern/regeln.md §11), one next step each."""
    broot = root / "bereiche"
    if not broot.exists():
        return
    for area in sorted(p for p in broot.iterdir() if p.is_dir()):
        st = area / "STAND.md"
        active_slug = ""
        if st.exists():
            try:
                stand = parse_stand(st)
            except Exception:
                stand = {}
            aktiv = stand.get("aktiv")
            state, detail = aktiv_state(aktiv, now)
            typ, slug = _aktiv_parts(aktiv)
            active_slug = slug
            saved = [h for h in area.rglob("*.html") if slug and slug in h.stem]
            rel = f"bereiche/{area.name}"
            if state == "unterbrochen":
                if saved:
                    add("WARN", f"{rel}: work interrupted ({detail}); a file was saved ({saved[0].name}) – next session: say so once, "
                                "check it against its template, then finish it (PDF, STAND, commit) or drop it as they wish, and set aktiv: –")
                else:
                    add("WARN", f"{rel}: work interrupted ({detail}) before any file was saved – next session: say so once, "
                                "ask whether to start it again or drop it, then set aktiv: –")
            elif state == "wird erstellt":
                add("INFO", f"{rel}: work in progress ({detail}) – if no session is working on it now, treat it as interrupted")
            if state == "ruhig":
                started = {}
                for line in stand.get("spur", []):
                    m = re.match(r"^(\S+)\s*·\s*(start|fertig)\s*·\s*(.*)$", line)
                    if not m:
                        continue
                    if m.group(2) == "start":
                        started[m.group(3).split("·")[-1].strip()] = m.group(1)
                    else:
                        for key in list(started):
                            if key and key in m.group(3):
                                del started[key]
                for key, when in started.items():
                    add("WARN", f"{rel}: trace has 'start {key}' ({when}) without 'fertig' – next session: check whether that "
                                "document is complete (file, PDF, STAND), then add the fertig line or note that it was dropped")
        for h in sorted(area.rglob("*.html")):
            meta = read_meta(h)
            rel = h.relative_to(root).as_posix()
            if (meta.get("typ") or "") in NO_PDF_TYPES or "praesentationen" in h.parts:
                continue
            if active_slug and active_slug in h.stem:
                continue
            if "eigene-endfassung" in (meta.get("export") or ""):
                continue
            if b"</html>" not in h.read_bytes()[-400:].lower():
                continue  # cut off while saving: reported below as incomplete
            pdf = h.with_suffix(".pdf")
            if not pdf.exists():
                add("WARN", f"{rel}: no PDF next to the HTML – next session: export it (python kern/tools/pdf_export.py) "
                            "and look at it before showing it; do not report it as finished before")
            elif pdf.stat().st_mtime + PDF_GRACE_S < h.stat().st_mtime:
                add("WARN", f"{rel}: the PDF is older than the HTML – next session: export it again so both say the same")
        for pdf in sorted(area.rglob("*.pdf")):
            if not pdf.with_suffix(".html").exists():
                add("WARN", f"{pdf.relative_to(root).as_posix()}: PDF without its HTML – next session: restore the HTML from git "
                            "(git log -- <file>) or ask whether the PDF is their own final version")


def check(root: Path = ROOT):
    res = []

    def add(level, msg):
        res.append((level, msg))

    version = (root / "kern" / "VERSION").read_text(encoding="utf-8", errors="replace").strip() if (root / "kern" / "VERSION").exists() else None
    if not version:
        add("FAIL", "kern/VERSION missing – the core is incomplete")
    core_check(root, add)
    rahmen = root / "profil" / "rahmen.md"
    if not rahmen.exists():
        add("INFO", "not set up yet (profil/rahmen.md missing) – offer skill einrichten")
        return res
    r = kv_lines(rahmen.read_text(encoding="utf-8", errors="replace"))
    if unset(r.get("kern_version")):
        add("WARN", "profil/rahmen.md: kern_version not set")
    elif version and r["kern_version"] != version:
        add("WARN", f"core version changed: instance {r['kern_version']} → core {version}; review the results below, then set kern_version")
    elif version:
        add("OK", f"core {version} = instance kern_version")
    paket = r.get("paket", "")
    if unset(paket):
        add("WARN", "profil/rahmen.md: paket not set (setup stage R unfinished)")
    else:
        pid = paket.replace("rahmen/", "").strip("/ ")
        if not (root / "rahmen" / pid / "paket.md").exists():
            add("FAIL", f"framework package rahmen/{pid}/paket.md missing – run skill recherche")
        else:
            txt = (root / "rahmen" / pid / "paket.md").read_text(encoding="utf-8", errors="replace")
            txt = re.split(r"(?m)^## ", txt, maxsplit=1)[0]  # block table only, not the report table below it
            n_open = len(re.findall(r"\|\s*(gefunden, ungeprüft|fehlt)\s*\|", txt))
            n_ok = len(re.findall(r"\|\s*geprüft\s*\|", txt))
            add("OK" if n_open == 0 else "INFO", f"package {pid}: {n_ok} blocks geprüft, {n_open} open")
    for f in ("lehrkraft.md", "pflichten.md", "stil.md", "checks.md"):
        if not (root / "profil" / f).exists():
            add("WARN", f"profil/{f} missing – copy from kern/instanz-vorlage/profil/")
    wz = root / "profil" / "werkzeuge.md"
    if wz.exists():
        runs = re.findall(r"(?m)^## (\S+) · (\S+)", wz.read_text(encoding="utf-8", errors="replace"))
        add("INFO", f"profil/werkzeuge.md: last tool run {runs[-1][0]} ({runs[-1][1]})" if runs
            else "profil/werkzeuge.md has no run entry – run python kern/tools/voraussetzungen.py once")
    else:
        add("INFO", "no tool protocol yet (profil/werkzeuge.md) – run python kern/tools/voraussetzungen.py once, it writes the protocol")
    compat_check(root, add)

    # areas
    listed = set()
    lk = root / "profil" / "lehrkraft.md"
    if lk.exists():
        listed = set(re.findall(r"bereiche/([a-z0-9-]+)", lk.read_text(encoding="utf-8", errors="replace")))
    present = {p.name for p in (root / "bereiche").iterdir() if p.is_dir()} if (root / "bereiche").exists() else set()
    for a in sorted(listed - present):
        add("WARN", f"area {a} listed in profil/lehrkraft.md but folder missing")
    for a in sorted(present - listed):
        add("WARN", f"area folder bereiche/{a} not listed in profil/lehrkraft.md")
    for a in sorted(present):
        st = root / "bereiche" / a / "STAND.md"
        if not st.exists():
            add("WARN", f"bereiche/{a}/STAND.md missing")
            continue

    # templates
    versions = {}
    vroot = root / "vorlagen"
    if vroot.exists():
        for t in sorted(p for p in vroot.iterdir() if p.is_dir()):
            if t.name == "bild":
                continue
            missing = [f for f in TEMPLATE_FILES if not (t / f).exists()]
            if missing:
                add("WARN", f"template {t.name}: missing {', '.join(missing)}")
            if (t / "herkunft.md").exists():
                m = re.search(r"version:\s*(\d+)", (t / "herkunft.md").read_text(encoding="utf-8", errors="replace"))
                versions[t.name] = m.group(1) if m else None
                if not m:
                    add("WARN", f"template {t.name}: no 'version:' in herkunft.md")

    # documents
    docs = 0
    for h in sorted((root / "bereiche").rglob("*.html")) if (root / "bereiche").exists() else []:
        docs += 1
        rel = h.relative_to(root).as_posix()
        meta = read_meta(h)
        miss = [k for k in REQUIRED_META if unset(meta.get(k))]
        if miss:
            add("WARN", f"{rel}: meta missing {', '.join(miss)}")
        if meta.get("status") and meta["status"] not in STATUS:
            add("WARN", f"{rel}: unknown status '{meta['status']}'")
        if not NAME_RE.match(h.name):
            add("INFO", f"{rel}: file name does not follow YYYY-MM-DD_<typ>_<slug>.html")
        if meta.get("status") in ("geprüft", "verwendet") and "[PRÜFEN:" in h.read_text(encoding="utf-8", errors="replace"):
            add("INFO", f"{rel}: status {meta['status']}, but [PRÜFEN: …] marks remain – the status says they find it fine, "
                        "not that these points were verified; name them when the document comes up next, never change the status yourself")
        v = meta.get("vorlage")
        if v and v in versions and versions[v] and meta.get("vorlage_version") not in (None, versions[v]):
            add("INFO", f"{rel}: built with template {v} v{meta.get('vorlage_version')}, current v{versions[v]}")
        elif v and v not in versions and not unset(v) and v != "standard":
            add("WARN", f"{rel}: template '{v}' not found in vorlagen/")
    add("OK", f"{docs} documents checked")
    half_states(root, add)

    # damaged files: brain files that are not valid UTF-8, documents cut off while writing
    for d in ("profil", "gedaechtnis", "review", "bereiche", "vorlagen", "rahmen"):
        for f in sorted((root / d).rglob("*.md")) if (root / d).exists() else []:
            try:
                f.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                add("WARN", f"{f.relative_to(root).as_posix()}: not readable as UTF-8 (damaged) – restore it from git (git log -- <file>) or rewrite the damaged part")
    for h in sorted((root / "bereiche").rglob("*.html")) if (root / "bereiche").exists() else []:
        tail = h.read_bytes()[-200:].decode("utf-8", errors="replace").lower()
        if "</html>" not in tail:
            add("WARN", f"{h.relative_to(root).as_posix()}: document incomplete (no closing </html>) – probably cut off while saving; restore it from git or finish it")

    # memory
    vl = root / "gedaechtnis" / "vorlieben.md"
    if vl.exists():
        bad = [l for l in vl.read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("- ") and not PREF_RE.match(l)]
        for l in bad[:5]:
            add("WARN", f"vorlieben.md line not in format: {l[:80]}")
    for f in ("gedaechtnis/feedback-log.md", "gedaechtnis/kernaenderungen.md", "review/offen.md"):
        if not (root / f).exists():
            add("WARN", f"{f} missing – copy from kern/instanz-vorlage/")

    # incoming
    inc = [p.name for p in (root / "eingang").iterdir() if p.name != "README.md"] if (root / "eingang").exists() else []
    if inc:
        add("INFO", f"{len(inc)} file(s) in eingang/: {', '.join(inc[:5])}")
    return res


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="check_instance.py", description=__doc__.split("\n\n")[0],
                                 epilog=__doc__.split("\n", 2)[2], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the findings as JSON")
    a = ap.parse_args(argv)
    res = check()
    if a.json:
        print(json.dumps([{"level": l, "msg": m} for l, m in res], ensure_ascii=False, indent=1))
    else:
        for level, msg in res:
            print(f"{level:4} {msg}")
    sys.exit(1 if any(l == "FAIL" for l, _ in res) else 0)


if __name__ == "__main__":
    main()
