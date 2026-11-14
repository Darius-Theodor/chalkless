"""Self-tests of the rule texts: every section reference resolves, and the folder check reports open marks.

Run:  python kern/tools/tests/test_regelwerk.py -v
Standard library only. Reads the core files of this folder; the check test builds a small instance in a
temporary folder.

A reference is `kern/regeln.md` §4 or `konventionen.md` §5, optionally followed by a quoted title ("Changes")
or by step numbers (step 4, steps 1–4). In a skill a bare §n means kern/regeln.md. The design references
(kern/gestaltung/) use bare §n for their own sections and are only checked for references that name a file.
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import check_instance  # noqa: E402

TARGETS = {"regeln": ROOT / "kern" / "regeln.md", "konventionen": ROOT / "kern" / "konventionen.md"}
NAMED = re.compile(r"(regeln|konventionen)\.md`?,? §(\d+)(?:,? (?:steps?) (\d+)(?:[–-](\d+))?| [\"“]([^\"”]+)[\"”])?")
BARE = re.compile(r"(?<!\.md` )(?<!\.md )§(\d+)(?: steps? (\d+)(?:[–-](\d+))?)?")


def sections(path: Path) -> dict:
    """{number: text of the section} for the headings `## <n>. <title>`."""
    out, number = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (\d+)\. ", line)
        if m:
            number = int(m.group(1))
            out[number] = ""
        if number is not None:
            out[number] += line + "\n"
    return out


def sources():
    files = [ROOT / n for n in ("AGENTS.md", "CLAUDE.md", "START-HIER.md")]
    for folder, pattern in (("kern", "*.md"), ("kern/tools", "*.py"), ("setup", "*.md")):
        files += sorted((ROOT / folder).rglob(pattern))
    return [f for f in files if f.is_file() and "tests" not in f.parts]


class References(unittest.TestCase):
    def check(self, source, line_no, target, number, last_step, title):
        where = f"{source.relative_to(ROOT).as_posix()}:{line_no}"
        secs = sections(TARGETS[target])
        self.assertIn(number, secs, f"{where}: {target}.md has no §{number}")
        if title:
            self.assertIn(title.lower(), secs[number].lower(), f"{where}: §{number} of {target}.md does not contain \"{title}\"")
        if last_step:
            self.assertRegex(secs[number], rf"(?m)^\s*{last_step}\. ", f"{where}: §{number} of {target}.md has no step {last_step}")

    def test_references_resolve(self):
        seen = 0
        for source in sources():
            in_skill = "skills" in source.parts
            for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
                named = list(NAMED.finditer(line))
                for m in named:
                    seen += 1
                    self.check(source, line_no, m.group(1), int(m.group(2)), m.group(4) or m.group(3), m.group(5))
                if in_skill:
                    rest = NAMED.sub("", line)
                    for m in BARE.finditer(rest):
                        seen += 1
                        self.check(source, line_no, "regeln", int(m.group(1)), m.group(3) or m.group(2), None)
        self.assertGreater(seen, 40, "the reference pattern no longer finds the references")


class OpenMarks(unittest.TestCase):
    def instance(self, status, body):
        root = Path(tempfile.mkdtemp())
        (root / "kern").mkdir()
        (root / "kern" / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        (root / "profil").mkdir()
        (root / "profil" / "rahmen.md").write_text("- kern_version: 9.9.9\n- paket: [ ]\n", encoding="utf-8")
        folder = root / "bereiche" / "3b-hsu" / "praesentationen"
        folder.mkdir(parents=True)
        (folder / "2027-03-17_praesentation_magnete.html").write_text(
            f'<html><head><meta name="chalkless.status" content="{status}"></head><body>{body}</body></html>', encoding="utf-8")
        return [msg for level, msg in check_instance.check(root) if level == "INFO" and "marks remain" in msg]

    def test_fine_with_open_marks_is_reported(self):
        self.assertEqual(len(self.instance("geprüft", "<p>[PRÜFEN: Lehrplanbezug]</p>")), 1)

    def test_draft_and_clean_documents_are_not(self):
        self.assertEqual(self.instance("entwurf", "<p>[PRÜFEN: Lehrplanbezug]</p>"), [])
        self.assertEqual(self.instance("geprüft", "<p>Magnete ziehen Eisen an.</p>"), [])


if __name__ == "__main__":
    unittest.main()
