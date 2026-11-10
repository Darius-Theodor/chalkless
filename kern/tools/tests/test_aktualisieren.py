"""Self-tests of kern/tools/aktualisieren.py: setup from a git source, updates, ZIP instances, the verlauf/ route.

Run:  python kern/tools/tests/test_aktualisieren.py -v
Standard library and git only, no network: the "published source" is a small synthetic Chalkless repository
in a temporary folder, cloned like the agent clones the real one.
"""
from __future__ import annotations

import contextlib
import functools
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import aktualisieren as ak  # noqa: E402
import verlauf  # noqa: E402

GIT = shutil.which("git")
ID = ["-c", "user.name=Test", "-c", "user.email=test@localhost", "-c", "init.defaultBranch=main"]


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *ID, *args], cwd=str(cwd), check=True, capture_output=True, text=True).stdout.strip()


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def quiet(fn, *a):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn(*a)
    return code, out.getvalue()


@unittest.skipUnless(GIT, "git is not installed")
class Aktualisieren(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="chalkless-akt-"))
        self.pub = self.tmp / "oeffentlich"
        self.pub.mkdir()
        git(self.pub, "init", "-q")
        self.release("0.5.0", {"kern/regeln.md": "rules v1\n", "kern/alt.md": "old core file\n",
                               "setup/EINRICHTUNG.md": "setup v1\n"})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def release(self, version: str, files: dict[str, str | None], branch: str = "main") -> None:
        """One published version: a synthetic core with the real tools, hash list written like a build."""
        base = {"kern/VERSION": version + "\n", "AGENTS.md": "agents\n", "README.md": "readme\n",
                ".gitignore": "setup/\n__pycache__/\n", "profil/README.md": "instance folder\n"}
        for rel, text in {**base, **files}.items():
            if text is None:
                (self.pub / rel).unlink(missing_ok=True)
            else:
                write(self.pub / rel, text)
        for name in ("verlauf.py", "kern_hashes.py", "aktualisieren.py"):
            write(self.pub / "kern" / "tools" / name, (TOOLS / name).read_text(encoding="utf-8"))
        subprocess.run([sys.executable, "-B", "kern/tools/kern_hashes.py", "--write"], cwd=self.pub, check=True,
                       capture_output=True)
        git(self.pub, "add", "-A")
        git(self.pub, "add", "-f", "--", "setup")  # ignored in an instance, published like the ZIP ships it
        git(self.pub, "commit", "-q", "-m", f"Chalkless {version}")

    def clone(self, name: str = "quelle") -> Path:
        dest = self.tmp / "temp" / name
        dest.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(self.pub), str(dest)], check=True, capture_output=True)
        return dest

    def install(self, folder: Path, **einrichten_opts) -> str:
        orig = ak.verlauf.einrichten
        if einrichten_opts:
            ak.verlauf.einrichten = functools.partial(orig, **einrichten_opts)
        try:
            code, out = quiet(ak.installieren, self.clone(), folder)
        finally:
            ak.verlauf.einrichten = orig
        self.assertEqual(code, 0, out)
        return out

    def repo(self, root: Path) -> ak.Repo:
        return ak.Repo(GIT, root)

    def finish_setup(self, root: Path) -> None:
        """What the agent does after installing: the instance, setup/ removed, one commit."""
        write(root / "profil" / "rahmen.md", "- kern_version: 0.5.0\n")
        write(root / "bereiche" / "2a-mathe" / "STAND.md", "stand\n")
        shutil.rmtree(root / "setup")
        r = self.repo(root)
        r("add", "profil", "bereiche")
        r("commit", "-q", "-m", "setup: instance for 2a-mathe")

    # -----------------------------------------------------------------------------------------------
    def test_install_into_empty_folder(self):
        folder = self.tmp / "Chalkless"
        out = self.install(folder)
        self.assertIn("history: git (.git/)", out)
        self.assertTrue((folder / "kern" / "regeln.md").is_file())
        self.assertTrue((folder / "setup" / "EINRICHTUNG.md").is_file(), "setup aid is placed for the agent")
        r = self.repo(folder)
        self.assertEqual(r("status", "--porcelain"), "")
        self.assertEqual(r("ls-files", "--", "setup"), "", "setup/ is not part of the history")
        self.assertEqual(r("config", "--get", "remote.chalkless.pushurl"), ak.NO_PUSH)
        self.assertIn(git(self.pub, "rev-parse", "HEAD"), r("log", "--format=%H"))
        code, out = quiet(ak.pruefen, folder)
        self.assertIn("current", out)

    def test_install_next_to_own_files_goes_into_subfolder(self):
        folder = self.tmp / "Dokumente"
        write(folder / "meine-notizen.txt", "x")
        out = self.install(folder)
        self.assertIn(str(folder / "Chalkless"), out)
        self.assertEqual((folder / "meine-notizen.txt").read_text(), "x")

    def test_install_refuses_existing_instance(self):
        folder = self.tmp / "Chalkless"
        write(folder / "profil" / "rahmen.md", "x")
        with self.assertRaises(ak.Stop) as cm:
            ak.installieren(self.clone(), folder)
        self.assertIn("update", cm.exception.msg)

    def test_update_replaces_core_keeps_instance(self):
        folder = self.tmp / "Chalkless"
        self.install(folder)
        self.finish_setup(folder)
        # a consented local core change, committed as the rules ask
        write(folder / "kern" / "regeln.md", "rules v1, changed locally\n")
        self.repo(folder)("commit", "-q", "-am", "core-change: regeln")
        self.release("0.6.0", {"kern/regeln.md": "rules v2\n", "kern/alt.md": None, "kern/neu.md": "new\n",
                               "setup/EINRICHTUNG.md": "setup v2\n"})
        code, out = quiet(ak.pruefen, folder)
        self.assertIn("update available: 0.5.0 -> 0.6.0", out)
        code, out = quiet(ak.einspielen, folder)
        self.assertEqual(code, 0, out)
        self.assertIn("core: update to 0.6.0", out)
        self.assertIn("overwritten: kern/regeln.md", out)
        self.assertIn("core against its hash list: unchanged", out)
        self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v2\n")
        self.assertTrue((folder / "kern" / "neu.md").is_file())
        self.assertFalse((folder / "kern" / "alt.md").exists(), "a core file the new version dropped is gone")
        self.assertFalse((folder / "setup").exists(), "setup/ never comes back")
        self.assertEqual((folder / "profil" / "rahmen.md").read_text(), "- kern_version: 0.5.0\n")
        self.assertTrue((folder / "bereiche" / "2a-mathe" / "STAND.md").is_file())
        r = self.repo(folder)
        self.assertEqual(r("status", "--porcelain"), "")
        self.assertEqual(len(r("log", "-1", "--format=%P").split()), 2, "one merge commit")
        code, out = quiet(ak.einspielen, folder)
        self.assertIn("current", out)
        # undo of the whole update
        r("revert", "--no-edit", "-m", "1", "HEAD")
        self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v1, changed locally\n")

    def test_update_refuses_unsaved_changes(self):
        folder = self.tmp / "Chalkless"
        self.install(folder)
        self.finish_setup(folder)
        write(folder / "profil" / "rahmen.md", "edited, not saved\n")
        self.release("0.6.0", {"kern/regeln.md": "rules v2\n"})
        code, out = quiet(ak.main, ["--root", str(folder), "--einspielen"])
        self.assertEqual(code, 2, out)
        self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v1\n")

    def test_verlauf_route_without_dot_git(self):
        """Hosts that refuse a .git folder (and the pointer file): history in verlauf/, updates still work."""
        folder = self.tmp / "Chalkless"
        out = self.install(folder, dot_folder=False, pointer=False)
        self.assertIn("verlauf/", out)
        self.assertFalse((folder / ".git").exists())
        self.finish_setup(folder)
        self.release("0.6.0", {"kern/regeln.md": "rules v2\n"})
        code, out = quiet(ak.einspielen, folder)
        self.assertEqual(code, 0, out)
        self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v2\n")
        self.assertEqual(self.repo(folder)("status", "--porcelain"), "")

    def test_zip_instance_can_be_connected(self):
        """A folder set up from a ZIP package (own history, no shared commits) gets connected and updated."""
        folder = self.tmp / "Chalkless"
        folder.mkdir()
        data = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=self.pub, check=True,
                              capture_output=True).stdout
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            for m in t.getmembers():
                if m.isfile():
                    write(folder / m.name, t.extractfile(m).read().decode("utf-8"))
        shutil.rmtree(folder / "setup")
        verlauf.einrichten(GIT, folder)
        r = self.repo(folder)
        r("add", "-A")
        r("commit", "-q", "-m", "setup: initial instance")
        write(folder / "profil" / "rahmen.md", "- kern_version: 0.5.0\n")
        r("add", "profil")
        r("commit", "-q", "-m", "setup: instance")
        code, out = quiet(ak.main, ["--root", str(folder), "--einspielen"])
        self.assertEqual(code, 1)
        self.assertIn("--anbinden", out)
        self.release("0.6.0", {"kern/regeln.md": "rules v2\n", "kern/alt.md": None})
        code, out = quiet(ak.anbinden, folder, str(self.pub), "main")
        self.assertEqual(code, 0, out)
        code, out = quiet(ak.einspielen, folder)
        self.assertEqual(code, 0, out)
        self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v2\n")
        self.assertFalse((folder / "kern" / "alt.md").exists())
        self.assertEqual((folder / "profil" / "rahmen.md").read_text(), "- kern_version: 0.5.0\n")
        self.assertEqual(r("status", "--porcelain"), "")

    def test_weekly_check(self):
        """--woechentlich: once per calendar week, remembered only while current, an update is reported."""
        folder = self.tmp / "Chalkless"
        orig = ak.this_week
        ak.this_week = lambda: "2026-W46"
        try:
            self.install(folder)
            self.finish_setup(folder)
            r = self.repo(folder)
            self.assertEqual(r("config", "--get", ak.WEEK_KEY), "2026-W46", "setup counts as checked")
            code, out = quiet(ak.woechentlich, folder)
            self.assertIn("checked already this week", out)
            # a new release in the same week stays unseen until next week
            self.release("0.6.0", {"kern/regeln.md": "rules v2\n"})
            code, out = quiet(ak.woechentlich, folder)
            self.assertIn("checked already", out)
            ak.this_week = lambda: "2026-W47"
            code, out = quiet(ak.woechentlich, folder)
            self.assertEqual(code, 0, out)
            self.assertIn("update available: 0.5.0 -> 0.6.0", out)
            self.assertEqual(r("config", "--get", ak.WEEK_KEY), "2026-W46", "not remembered while an update waits")
            self.assertEqual((folder / "kern" / "regeln.md").read_text(), "rules v1\n", "the check changes nothing")
            code, out = quiet(ak.einspielen, folder)
            self.assertEqual(code, 0, out)
            self.assertEqual(r("config", "--get", ak.WEEK_KEY), "2026-W47")
            code, out = quiet(ak.woechentlich, folder)
            self.assertIn("checked already", out)
            # unreachable: exit 4, the week stays open
            ak.this_week = lambda: "2026-W48"
            r("remote", "set-url", "chalkless", str(self.tmp / "gibt-es-nicht"))
            code, out = quiet(ak.main, ["--root", str(folder), "--woechentlich"])
            self.assertEqual(code, 4, out)
            self.assertEqual(r("config", "--get", ak.WEEK_KEY), "2026-W47")
            self.assertEqual(r("status", "--porcelain"), "", "the check never leaves a changed file")
        finally:
            ak.this_week = orig

    def test_weekly_check_skips_without_source(self):
        folder = self.tmp / "ohne"
        folder.mkdir()
        code, out = quiet(ak.main, ["--root", str(folder), "--woechentlich"])
        self.assertEqual(code, 0, out)
        self.assertIn("skipped", out)

    def test_unreachable_source(self):
        folder = self.tmp / "Chalkless"
        self.install(folder)
        self.finish_setup(folder)
        self.repo(folder)("remote", "set-url", "chalkless", str(self.tmp / "gibt-es-nicht"))
        code, out = quiet(ak.main, ["--root", str(folder), "--pruefen"])
        self.assertEqual(code, 4, out)


if __name__ == "__main__":
    unittest.main()
