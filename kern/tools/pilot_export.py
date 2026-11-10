"""Pilot feedback export: one local file for the people developing Chalkless (pilot builds only).

Usage (from the Chalkless folder):
  python kern/tools/pilot_export.py [--host "<app/host>"] [--datum YYYY-MM-DD] [--schwaerzen] [--dry-run]
  python kern/tools/pilot_export.py --selbsttest
Writes review/pilot-export_<datum>.md and prints its path. It contains only: the core version, the host
as the agent names it, the period, counts (days with entries, documents per type, protocol entries per
kind and skill, framework blocks per status, open change requests), the technical protocol sentences and
the teacher's own sentences about the tool (review/pilot-feedback.md, verbatim). It never contains document
contents or titles, names, the school, pupils or parents, and it sends nothing anywhere (no network code).
Before writing, every line of the draft is checked against a block list: privacy markers
(SCHOOL_PRIVATE_MARKER, LEARNER_PRIVATE_MARKER, any *_PRIVATE_MARKER), e-mail addresses, phone-like or long
digit sequences, and the titles of the instance's own documents. Any hit stops the export: nothing is
written, the hits are listed by line and category. --schwaerzen replaces each line with a hit by
"[entfernt: <category>]" and writes the file (the agent decides that after looking at the hits).
Exit codes: 0 written (or --dry-run shown), 2 wrong arguments, 3 stopped by the block list (nothing
written), 5 not a pilot build (kern/PILOT missing) or no pilot files. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_instance import kv_lines, read_meta  # noqa: E402

PROTO_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · ([^·]+?) · ([^·]+?) · ([a-z-]+): (.*)$")
FEED_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · ")
MARKER_RE = re.compile(r"[A-Z]+_PRIVATE_MARKER")
MAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
VERSION_RE = re.compile(r"\b\d+\.\d+\.\d+(?:-[a-z0-9]+)?\b")
DIGITS_RE = re.compile(r"(?<!\w)\+?\d[\d /().-]{6,}\d(?!\w)")
EXIT_BLOCKED, EXIT_NOT_PILOT = 3, 5


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def titles(root: Path):
    out = set()
    for h in (root / "bereiche").rglob("*.html") if (root / "bereiche").exists() else []:
        t = (read_meta(h).get("titel") or "").strip()
        if len(t) >= 5:
            out.add(t.lower())
    return out


def blocklist_hits(lines, doc_titles):
    """[(line number, category)] for every draft line that must not leave the folder."""
    hits = []
    for n, line in enumerate(lines, 1):
        cats = []
        if MARKER_RE.search(line):
            cats.append("Datenschutz-Marker")
        if MAIL_RE.search(line):
            cats.append("E-Mail-Adresse")
        if DIGITS_RE.search(VERSION_RE.sub("", DATE_RE.sub("", line))):
            cats.append("Telefon- oder Zahlenfolge")
        low = line.lower()
        if any(t in low for t in doc_titles):
            cats.append("Dokumenttitel")
        if cats:
            hits.append((n, ", ".join(cats)))
    return hits


def compile_export(root: Path, host: str, datum: str):
    proto = [m.groups() for m in (PROTO_RE.match(l.strip()) for l in read(root / "review" / "pilot-protokoll.md").splitlines()) if m]
    feed = [l.strip() for l in read(root / "review" / "pilot-feedback.md").splitlines() if FEED_RE.match(l.strip())]
    days = sorted({p[0] for p in proto} | {FEED_RE.match(f).group(1) for f in feed})
    docs = Counter()
    for h in (root / "bereiche").rglob("*.html") if (root / "bereiche").exists() else []:
        docs[(read_meta(h).get("typ") or h.parent.name).strip() or "?"] += 1
    rahmen = kv_lines(read(root / "profil" / "rahmen.md"))
    pid = (rahmen.get("paket") or "").replace("rahmen/", "").strip("/ ")
    blocks = Counter()
    if pid:
        head = re.split(r"(?m)^## ", read(root / "rahmen" / pid / "paket.md"), maxsplit=1)[0]
        for st in re.findall(r"\|\s*(geprüft|gefunden, ungeprüft|fehlt)\s*\|", head):
            blocks[st] += 1
    offen = sum(1 for l in read(root / "review" / "offen.md").splitlines()
                if l.startswith("|") and not re.match(r"^\|\s*(Datum|-)", l) and "erledigt" not in l)
    kinds = Counter(p[3] for p in proto)
    skills = Counter(p[1].strip() for p in proto)
    L = [f"# Pilot-Rückmeldung {datum}", "",
         "> Für die Entwicklung von Chalkless. Enthält nur Zahlen und Sätze über das Werkzeug – keine Inhalte der Planung, "
         "keine Namen, keine Schule, keine Lernenden. Nichts wurde gesendet; die Lehrkraft gibt die Datei weiter, wenn sie mag.", "",
         "## Rahmen",
         f"- Kern-Version: {read(root / 'kern' / 'VERSION').strip() or '?'}",
         f"- Host/App: {host or 'unbekannt'}",
         f"- Zeitraum: {days[0] if days else '–'} bis {days[-1] if days else '–'}",
         f"- Tage mit Einträgen: {len(days)}",
         f"- Pilot-Protokoll: {rahmen.get('pilot', '–')}", "",
         "## Zahlen",
         "- Dokumente je Typ: " + (", ".join(f"{k} {v}" for k, v in sorted(docs.items())) or "keine"),
         "- Protokolleinträge je Art: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) or "keine"),
         "- Protokolleinträge je Skill: " + (", ".join(f"{k} {v}" for k, v in sorted(skills.items())) or "keine"),
         "- Rahmen-Bausteine je Status: " + (", ".join(f"{k} {v}" for k, v in sorted(blocks.items())) or "keine"),
         f"- Offene Änderungswünsche: {offen}", "",
         "## Technische Beobachtungen (Pilot-Protokoll)"]
    L += [f"- {d} · {s.strip()} · {t.strip()} · {k}: {x}" for d, s, t, k, x in proto] or ["- keine"]
    L += ["", "## Sätze der Lehrkraft zum Werkzeug (wörtlich)"]
    L += feed or ["- keine"]
    return L


def run(root: Path, host="", datum=None, schwaerzen=False, dry_run=False, out=sys.stdout) -> int:
    if not (root / "kern" / "PILOT").exists():
        print("Keine Pilotfassung (kern/PILOT fehlt) – es gibt nichts zu exportieren.", file=out)
        return EXIT_NOT_PILOT
    if not any((root / "review" / f).exists() for f in ("pilot-protokoll.md", "pilot-feedback.md")):
        print("Keine Pilot-Dateien in review/ – es gibt nichts zu exportieren.", file=out)
        return EXIT_NOT_PILOT
    datum = datum or dt.date.today().isoformat()
    lines = compile_export(root, host, datum)
    hits = blocklist_hits(lines, titles(root))
    if hits and not schwaerzen:
        print(f"GESTOPPT: {len(hits)} Zeile(n) dürfen den Ordner nicht verlassen; nichts geschrieben.", file=out)
        for n, cat in hits:
            print(f"  Zeile {n}: {cat}", file=out)
        print("Prüfe die Zeilen in review/pilot-*.md; danach erneut, oder mit --schwaerzen exportieren (Zeilen werden ersetzt).", file=out)
        return EXIT_BLOCKED
    for n, cat in hits:
        lines[n - 1] = f"- [entfernt: {cat}]"
    assert not blocklist_hits(lines, titles(root))
    text = "\n".join(lines) + "\n"
    if dry_run:
        print(text, file=out)
        return 0
    target = root / "review" / f"pilot-export_{datum}.md"
    i = 2
    while target.exists():
        target = root / "review" / f"pilot-export_{datum}-{i}.md"
        i += 1
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"geschrieben: {target.relative_to(root).as_posix()}" + (f" ({len(hits)} Zeile(n) geschwärzt)" if hits else ""), file=out)
    return 0


def selbsttest() -> int:
    """Negative example with privacy markers is stopped; positive example is written without them."""
    import io
    tmp = Path(tempfile.mkdtemp(prefix="chalkless-pilottest-"))
    ok = True

    def expect(name, cond):
        nonlocal ok
        ok = ok and cond
        print(("PASS " if cond else "FAIL ") + name)

    try:
        r = tmp / "i"
        (r / "kern").mkdir(parents=True)
        (r / "kern" / "VERSION").write_text("0.4.0-dev\n", encoding="utf-8")
        (r / "review").mkdir()
        (r / "profil").mkdir()
        (r / "profil" / "rahmen.md").write_text("- pilot: an\n- paket: [ ]\n", encoding="utf-8")
        a = r / "bereiche" / "k1-fach" / "stunden"
        a.mkdir(parents=True)
        (a / "2026-11-02_stunde_x.html").write_text('<meta name="chalkless.titel" content="Geheimes Stundenthema">'
                                                     '<meta name="chalkless.typ" content="stunde"></html>', encoding="utf-8")
        buf = io.StringIO()
        expect("without kern/PILOT: exit 5, nothing written", run(r, out=buf) == EXIT_NOT_PILOT and not list((r / "review").glob("pilot-export*")))
        (r / "kern" / "PILOT").write_text("pilot\n", encoding="utf-8")
        (r / "review" / "pilot-protokoll.md").write_text(
            "# Pilot-Protokoll\n- 2026-11-02 · dokument · stunde · fehler: pdf_export.py brach mit Timeout ab\n"
            "- 2026-11-03 · material · – · wartezeit: 7 Minuten\n", encoding="utf-8")
        feed = r / "review" / "pilot-feedback.md"
        feed.write_text("# Pilot-Feedback\n- 2026-11-03 · dokument · [kritik] · \"das Tool nervt mit der Rückfrage\" → noted\n", encoding="utf-8")
        buf = io.StringIO()
        rc = run(r, host="Testhost", datum="2026-11-04", out=buf)
        out = r / "review" / "pilot-export_2026-11-04.md"
        expect("positive example: written, exit 0", rc == 0 and out.exists())
        text = out.read_text(encoding="utf-8") if out.exists() else ""
        expect("export holds version, counts and the sentence about the tool",
               "0.4.0-dev" in text and "fehler 1" in text and "das Tool nervt" in text and "stunde 1" in text)
        expect("export holds no document title", "Geheimes Stundenthema" not in text)
        out.unlink()
        with feed.open("a", encoding="utf-8") as fh:
            fh.write("- 2026-11-04 · dokument · [hinweis] · \"in der Klasse von SCHOOL_PRIVATE_MARKER fehlt LEARNER_PRIVATE_MARKER\" → noted\n"
                     "- 2026-11-04 · dokument · [hinweis] · \"schreib an lehrer@example.org oder 0171 2345678\" → noted\n"
                     "- 2026-11-04 · dokument · [kritik] · \"Geheimes Stundenthema war zu lang\" → noted\n")
        buf = io.StringIO()
        rc = run(r, datum="2026-11-04", out=buf)
        msg = buf.getvalue()
        expect("negative example with SCHOOL_/LEARNER_PRIVATE_MARKER: stopped, exit 3, nothing written",
               rc == EXIT_BLOCKED and not list((r / "review").glob("pilot-export*")) and "Datenschutz-Marker" in msg)
        expect("e-mail, phone number and document title are named", all(c in msg for c in ("E-Mail-Adresse", "Telefon- oder Zahlenfolge", "Dokumenttitel")))
        expect("the stop message does not repeat the private text", "SCHOOL_PRIVATE_MARKER" not in msg and "lehrer@" not in msg)
        buf = io.StringIO()
        rc = run(r, datum="2026-11-04", schwaerzen=True, out=buf)
        text = out.read_text(encoding="utf-8") if out.exists() else ""
        expect("--schwaerzen: written without the private lines", rc == 0 and "PRIVATE_MARKER" not in text and "lehrer@" not in text
               and "2345678" not in text and "Geheimes" not in text and "[entfernt:" in text and "das Tool nervt" in text)
        print("\n".join("  | " + l for l in buf.getvalue().splitlines()))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("Selbsttest " + ("bestanden" if ok else "FEHLGESCHLAGEN"))
    return 0 if ok else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="pilot_export.py", description=__doc__.split("\n\n")[0],
                                 epilog=__doc__.split("\n", 2)[2], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="", help="host/app as the agent knows it, e.g. 'Claude Desktop (Windows)'")
    ap.add_argument("--datum", default=None, help="date in the file name (default: today)")
    ap.add_argument("--schwaerzen", action="store_true", help="replace lines with block-list hits and write the file")
    ap.add_argument("--dry-run", action="store_true", help="show the export, write nothing")
    ap.add_argument("--selbsttest", action="store_true", help="run the self-test in a temporary folder")
    a = ap.parse_args(argv)
    if a.selbsttest:
        return selbsttest()
    if a.datum and not re.match(r"^\d{4}-\d{2}-\d{2}$", a.datum):
        ap.error("--datum needs YYYY-MM-DD")
    return run(ROOT, a.host, a.datum, a.schwaerzen, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
