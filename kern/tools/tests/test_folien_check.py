"""Self-tests of kern/tools/folien_check.py.

Run:  python kern/tools/tests/test_folien_check.py -v      (or: python kern/tools/folien_check.py --self-test)
Nothing is installed or downloaded. The structural tests use the standard library only. The rendering tests need
Playwright and an installed Edge or Chrome; without them they are skipped with the reason. Test decks are written
into a temporary folder whose name has a space and an umlaut (the deck must work from any folder, offline).
The broken mini deck has an overflow, a visible teacher note and an external picture; the clean one has none.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TOOL = TOOLS / "folien_check.py"
FRAME = TOOLS.parent / "gestaltung" / "deck-rahmen.html"
sys.path.insert(0, str(TOOLS))
import folien_check as fc  # noqa: E402

MINI = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Mini-Deck</title>
<style>
body { margin: 0; font: 40px/1.3 Arial, sans-serif; }
.beat { display: none; width: 100vw; height: 100vh; padding: 60px; box-sizing: border-box; position: relative; overflow: visible; }
.beat[data-active] { display: block; }
.future { visibility: hidden; opacity: 0; }
.notes { display: none; }
@@CSS@@
</style></head><body><main>
<section class="beat" id="b1" data-title="Eins"><h2>Erste Folie</h2><p data-build="1">Ein Satz erscheint mit dem ersten Klick.</p>
<aside class="notes" hidden>Notiz eins: Diese Notiz der Lehrkraft darf auf keiner Folie sichtbar sein.</aside></section>
<section class="beat" id="b2" data-title="Zwei"><h2>Zweite Folie</h2><p>Ein ruhiger Satz.</p>@@EXTRA@@
<aside class="notes" @@NOTESATTR@@>Notiz zwei: Die erwarteten Antworten der Klasse stehen nur in dieser Notiz.</aside></section>
</main>
<script>
(function () {
  var beats = Array.prototype.slice.call(document.querySelectorAll('main section.beat'));
  var max = beats.map(function (b) { var m = 0; b.querySelectorAll('[data-build]').forEach(function (e) { m = Math.max(m, +e.getAttribute('data-build')); }); return m; });
  var step = beats.map(function () { return 0; }), cur = -1;
  function render(i) { beats.forEach(function (b, j) { b.toggleAttribute('data-active', j === i); });
    beats[i].querySelectorAll('[data-build]').forEach(function (e) { e.classList.toggle('future', +e.getAttribute('data-build') > step[i]); }); }
  function go(i, s) { i = Math.max(0, Math.min(beats.length - 1, i)); step[i] = s === 'end' ? max[i] : Math.max(0, Math.min(max[i], +s || 0)); cur = i; render(i);
    try { sessionStorage.setItem('mini', JSON.stringify([cur, step[cur]])); } catch (e) {} history.replaceState(null, '', location.pathname + '#b' + (i + 1)); }
  function next() { if (step[cur] < max[cur]) go(cur, step[cur] + 1); else if (cur + 1 < beats.length) go(cur + 1, 0); }
  window.addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') next(); });
  window.deck = { get count() { return beats.length; }, get index() { return cur; }, get step() { return step[cur]; },
    stepsOf: function (i) { return max[i]; }, go: go, next: next };
  var q = new URLSearchParams(location.search).get('step'), m = /^#b(\\d+)$/.exec(location.hash), i0 = m ? +m[1] - 1 : 0, saved = null;
  try { saved = JSON.parse(sessionStorage.getItem('mini')); } catch (e) {}
  if (q !== null) go(i0, q); else if (saved && saved[0] === i0) go(i0, saved[1]); else go(i0, 0);
})();
</script></body></html>
"""

BROKEN_EXTRA = ('<p style="position:absolute; left:1700px; top:900px; width:800px">Dieser Satz ragt weit über den Rand hinaus.</p>'
                '<img src="https://example.invalid/bild.png" alt="" width="200" height="100">')


def mini(broken: bool) -> str:
    return (MINI.replace("@@CSS@@", ".beat .notes { display: block !important; }" if broken else "")
                .replace("@@EXTRA@@", BROKEN_EXTRA if broken else "")
                .replace("@@NOTESATTR@@", "" if broken else "hidden"))


def run(*args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, env=e, timeout=180)
    return p.returncode, p.stdout.decode("ascii", "replace"), p.stderr.decode("utf-8", "replace")


class Help(unittest.TestCase):
    def test_help_in_cp1252_console(self):
        rc, outp, err = run("--help", env={"PYTHONIOENCODING": "cp1252"})
        self.assertEqual(rc, 0, err)
        self.assertIn("Exit codes", outp)
        self.assertIn("Not checked by this tool", outp)
        self.assertTrue(all(ord(c) < 128 for c in outp))

    def test_missing_file_is_load_error(self):
        rc, outp, _ = run(Path(tempfile.gettempdir()) / "gibt-es-nicht-folien.html")
        self.assertEqual(rc, 2)
        self.assertIn("NOT RENDERED", outp)


class Structure(unittest.TestCase):
    def test_broken_structure(self):
        s = fc.structural(mini(True).replace("<title>Mini-Deck</title>", "<title>{{titel}}</title>")
                          + '<div class="pic-missing">Bild folgt: ein Magnet</div><p>bild_03.png</p>')
        self.assertEqual(s["beats"], 2)
        self.assertEqual(s["notes"], 2)
        self.assertEqual(s["notes_without_hidden"], 1)
        self.assertTrue(any("example.invalid" in x for x in s["external_refs"]))
        self.assertIn("Bild folgt: ein Magnet", s["missing_pictures"])
        self.assertTrue(any("bild_03.png" in x for x in s["template_leftovers"]))
        self.assertTrue(any("{{titel}}" in x for x in s["template_leftovers"]))

    def test_clean_structure(self):
        s = fc.structural(mini(False))
        self.assertEqual(s["notes_without_hidden"], 0)
        self.assertEqual(s["external_refs"], [])
        self.assertEqual(s["template_leftovers"], [])


class Render(unittest.TestCase):
    """Needs Playwright and Edge/Chrome; skipped otherwise."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="folien check ü "))
        (cls.tmp / "sauber.html").write_text(mini(False), encoding="utf-8")
        (cls.tmp / "defekt.html").write_text(mini(True), encoding="utf-8")
        shutil.copy(FRAME, cls.tmp / "rahmen.html")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def check(self, name, *extra):
        outdir = self.tmp / ("out-" + name.replace(".html", "") + ("-".join(extra).replace("-", "") or ""))
        rc, outp, err = run(self.tmp / name, "--out", outdir, *extra)
        rep = outdir / "folien_check.json"
        if rc == 2 and rep.exists():
            data = json.loads(rep.read_text(encoding="utf-8"))
            if "renderer" in " ".join(data.get("nicht_geprueft", [])) or "Playwright" in data.get("load_error", "") or "Edge" in data.get("load_error", ""):
                self.skipTest("no renderer: " + data.get("load_error", ""))
        self.assertTrue(rep.exists(), outp + err)
        return rc, json.loads(rep.read_text(encoding="utf-8")), outdir

    def test_clean_mini_deck(self):
        rc, rep, outdir = self.check("sauber.html")
        self.assertEqual(rc, 0, rep["problems"])
        self.assertEqual(rep["beats"], 2)
        self.assertEqual(rep["steps_per_beat"], [1, 0])
        self.assertEqual(rep["summary"]["states"], 3)
        self.assertEqual(rep["summary"]["overflow"], 0)
        self.assertEqual(rep["summary"]["notes_visible"], 0)
        self.assertEqual(rep["network"], [])
        self.assertTrue((outdir / "b01-s00.png").exists() and (outdir / "b01-s01.png").exists() and (outdir / "b02-s00.png").exists())
        self.assertIn("nicht_geprueft", rep)
        self.assertTrue(rep["reload"]["ok"], rep["reload"])

    def test_broken_mini_deck(self):
        rc, rep, _ = self.check("defekt.html")
        self.assertEqual(rc, 1)
        self.assertGreater(rep["summary"]["overflow"], 0)
        self.assertGreater(rep["summary"]["notes_visible"], 0)
        self.assertTrue(any("example.invalid" in u for u in rep["network"]), rep["network"])
        kinds = " ".join(rep["problems"])
        for word in ("overflow", "notes visible", "network"):
            self.assertIn(word, kinds)

    def test_font_reference_is_only_a_hint(self):
        rc, rep, _ = self.check("sauber.html", "--min-font", "50")
        self.assertEqual(rc, 0)
        self.assertGreater(rep["summary"]["below_min_font"], 0)
        self.assertTrue(any("reference size" in h for h in rep["hints"]))

    def test_frame_is_clean_and_prints(self):
        rc, rep, outdir = self.check("rahmen.html", "--pdf")
        self.assertEqual(rc, 0, rep["problems"])
        self.assertEqual(rep["summary"]["notes_visible"], 0)
        self.assertTrue(rep["reload"]["ok"], rep["reload"])
        self.assertTrue(rep["keys"]["ok"])
        self.assertEqual(rep["pdf"]["pages"], rep["beats"])
        self.assertEqual(len(rep["summary"]["missing_pictures"]), 1)


if __name__ == "__main__":
    unittest.main()
