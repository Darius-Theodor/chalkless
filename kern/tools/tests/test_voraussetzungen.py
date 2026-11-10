"""Deterministic self-tests of the 48-hour rule in kern/tools/voraussetzungen.py.

Run:  python kern/tools/tests/test_voraussetzungen.py -v      (or: python kern/tools/voraussetzungen.py --self-test)
Standard library only, no network, no system clock, no pip call, nothing is installed:
metadata comes from local JSON files in a temporary folder, the resolved set from fake pip reports,
the reference time is fixed. The eight required variants are the classes V1-V8 below.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import voraussetzungen as vz  # noqa: E402

NOW = vz.to_utc("2026-11-08T12:00:00Z")


def f(name, version, iso, sha=None, plain=None, yanked=False):
    """One published file as in the PyPI JSON API."""
    d = {"filename": f"{name}-{version}-py3-none-any.whl", "upload_time_iso_8601": iso,
         "digests": {"sha256": sha or f"{name}{version}".ljust(64, "0")[:64]}, "yanked": yanked}
    if plain is not None:
        d["upload_time"] = plain
    return d


def item(name, version, requested=True, requires=(), sha=None):
    """One entry of `pip install --dry-run --report` output."""
    sha = sha or f"{name}{version}".ljust(64, "0")[:64]
    return {"download_info": {"url": f"https://files.example/{name}-{version}-py3-none-any.whl",
                              "archive_info": {"hash": f"sha256={sha}", "hashes": {"sha256": sha}}},
            "requested": requested, "metadata": {"name": name, "version": version, "requires_dist": list(requires)}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="chalkless-vz-test-")
        self.dir = Path(self.tmp.name)
        self.meta = vz.Metadata(metadata_dir=str(self.dir))

    def tearDown(self):
        self.tmp.cleanup()

    def project(self, name, releases):
        (self.dir / f"{vz.norm(name)}.json").write_text(json.dumps({"info": {"name": name}, "releases": releases}), encoding="utf-8")

    def resolver(self, mapping):
        """mapping: frozenset(constraints.items()) -> report; records the calls."""
        self.calls = []

        def resolve(constraints):
            self.calls.append(dict(constraints))
            return {"install": mapping[frozenset(constraints.items())]}
        return resolve


class V1Older(Fixture):
    def test_older_than_48h_is_allowed(self):
        self.project("alpha", {"1.0": [f("alpha", "1.0", "2026-11-01T00:00:00.000000Z", plain="2026-11-01T00:00:00")]})
        r = vz.plan([("alpha", ">=1")], self.resolver({frozenset(): [item("alpha", "1.0")]}), self.meta, NOW,
                    installed=lambda n: None)
        self.assertTrue(r["ok"])
        self.assertEqual([i["name"] for i in r["install"]], ["alpha"])
        self.assertEqual(r["verdicts"][0]["status"], "allowed")


class V2Exactly48h(Fixture):
    def test_exactly_48h_is_allowed_one_microsecond_less_is_not(self):
        self.project("beta", {"2.0": [f("beta", "2.0", "2026-11-06T12:00:00.000000Z")],
                              "2.1": [f("beta", "2.1", "2026-11-06T12:00:00.000001Z")]})
        v = vz.judge({"name": "beta", "version": "2.0", "sha256": f("beta", "2.0", "")["digests"]["sha256"]}, self.meta, NOW)
        self.assertEqual(v["status"], "allowed")
        self.assertEqual((NOW - vz.to_utc("2026-11-06T12:00:00Z")).total_seconds(), vz.MIN_AGE_S)
        v = vz.judge({"name": "beta", "version": "2.1", "sha256": f("beta", "2.1", "")["digests"]["sha256"]}, self.meta, NOW)
        self.assertEqual(v["status"], "too_young")


class V3Younger(Fixture):
    def test_younger_is_blocked_and_older_allowed_version_is_used(self):
        self.project("gamma", {"2.9": [f("gamma", "2.9", "2026-09-01T00:00:00Z")],
                               "3.0": [f("gamma", "3.0", "2026-10-01T00:00:00Z")],
                               "3.1": [f("gamma", "3.1", "2026-11-07T12:00:00Z")]})
        res = self.resolver({frozenset(): [item("gamma", "3.1")],
                             frozenset({("gamma", "3.0")}): [item("gamma", "3.0")]})
        r = vz.plan([("gamma", ">=2.9")], res, self.meta, NOW, installed=lambda n: None)
        self.assertTrue(r["ok"])
        self.assertEqual([(i["name"], i["version"]) for i in r["install"]], [("gamma", "3.0")])
        self.assertEqual(self.calls, [{}, {"gamma": "3.0"}])

    def test_younger_without_older_candidate_installs_nothing(self):
        self.project("gamma", {"3.1": [f("gamma", "3.1", "2026-11-07T12:00:00Z")]})
        r = vz.plan([("gamma", ">=3.1")], self.resolver({frozenset(): [item("gamma", "3.1")]}), self.meta, NOW,
                    installed=lambda n: None)
        self.assertFalse(r["ok"])
        self.assertEqual(r["install"], [])
        self.assertIn("younger than 48 hours", r["limit"])
        self.assertIsNone(r["verdicts"][0].get("suggestion"))


class V4Unknown(Fixture):
    def test_no_metadata_blocks(self):
        r = vz.plan([("delta", "")], self.resolver({frozenset(): [item("delta", "1.0")]}), self.meta, NOW,
                    installed=lambda n: None)
        self.assertFalse(r["ok"])
        self.assertEqual(r["verdicts"][0]["status"], "unknown")
        self.assertIn("no verifiable publication date", r["limit"])

    def test_missing_upload_time_blocks(self):
        d = f("delta", "1.0", "2026-01-01T00:00:00Z")
        del d["upload_time_iso_8601"]
        self.project("delta", {"1.0": [d]})
        v = vz.judge({"name": "delta", "version": "1.0", "sha256": d["digests"]["sha256"]}, self.meta, NOW)
        self.assertEqual(v["status"], "unknown")

    def test_unreachable_index_blocks(self):
        meta = vz.Metadata(base_url="http://127.0.0.1:9/pypi", timeout=2)  # nothing listens on port 9
        v = vz.judge({"name": "delta", "version": "1.0", "sha256": "0" * 64}, meta, NOW)
        self.assertEqual(v["status"], "unknown")


class V5YoungTransitive(Fixture):
    def test_old_package_with_young_dependency_installs_nothing(self):
        self.project("epsilon", {"1.0": [f("epsilon", "1.0", "2026-01-01T00:00:00Z")]})
        self.project("zeta", {"0.5": [f("zeta", "0.5", "2026-11-08T00:00:00Z")]})
        rep = [item("epsilon", "1.0", requires=["zeta>=0.5"]), item("zeta", "0.5", requested=False)]
        r = vz.plan([("epsilon", ">=1")], self.resolver({frozenset(): rep}), self.meta, NOW, installed=lambda n: None)
        self.assertFalse(r["ok"])
        self.assertEqual(r["install"], [])
        st = {v["name"]: v["status"] for v in r["verdicts"]}
        self.assertEqual(st, {"epsilon": "allowed", "zeta": "too_young"})
        self.assertIn("zeta 0.5", r["limit"])

    def test_dependency_suggestion_respects_parent_specifier(self):
        self.project("epsilon", {"1.0": [f("epsilon", "1.0", "2026-01-01T00:00:00Z")]})
        self.project("zeta", {"0.4": [f("zeta", "0.4", "2026-01-01T00:00:00Z")],
                              "0.5": [f("zeta", "0.5", "2026-11-08T00:00:00Z")]})
        rep = [item("epsilon", "1.0", requires=["zeta>=0.5"]), item("zeta", "0.5", requested=False)]
        r = vz.plan([("epsilon", ">=1")], self.resolver({frozenset(): rep}), self.meta, NOW, installed=lambda n: None)
        self.assertFalse(r["ok"])  # 0.4 would violate zeta>=0.5, so no proposal and no install
        self.assertIsNone(r["verdicts"][1].get("suggestion"))


class V6Contradictory(Fixture):
    def test_upload_times_disagree(self):
        d = f("eta", "1.0", "2026-11-07T00:00:00Z", plain="2026-10-01T00:00:00")
        self.project("eta", {"1.0": [d]})
        v = vz.judge({"name": "eta", "version": "1.0", "sha256": d["digests"]["sha256"]}, self.meta, NOW)
        self.assertEqual(v["status"], "contradictory")

    def test_hash_differs_for_same_file(self):
        self.project("eta", {"1.0": [f("eta", "1.0", "2026-01-01T00:00:00Z", sha="b" * 64)]})
        r = vz.plan([("eta", "")], self.resolver({frozenset(): [item("eta", "1.0", sha="a" * 64)]}), self.meta, NOW,
                    installed=lambda n: None)
        self.assertFalse(r["ok"])
        self.assertEqual(r["verdicts"][0]["status"], "contradictory")
        self.assertIn("contradictory", r["limit"])

    def test_upload_in_future_and_yanked(self):
        self.project("eta", {"1.0": [f("eta", "1.0", "2026-12-01T00:00:00Z")],
                             "0.9": [f("eta", "0.9", "2026-01-01T00:00:00Z", yanked=True)]})
        for version in ("1.0", "0.9"):
            v = vz.judge({"name": "eta", "version": version, "sha256": f("eta", version, "")["digests"]["sha256"]}, self.meta, NOW)
            self.assertEqual(v["status"], "contradictory", version)


class V7Timezone(Fixture):
    def test_offsets_are_converted_to_utc(self):
        # 13:30+02:00 = 11:30Z -> 48.5 h old (a naive reading would say 46.5 h)
        # 11:30-01:00 = 12:30Z -> 47.5 h old (a naive reading would say 48.5 h)
        self.project("theta", {"1.0": [f("theta", "1.0", "2026-11-06T13:30:00+02:00")]})
        self.project("iota", {"1.0": [f("iota", "1.0", "2026-11-06T11:30:00-01:00")]})
        now = vz.reference_time("2026-11-08T13:00:00+01:00")  # = 12:00Z
        self.assertEqual(now, NOW)
        a = vz.judge({"name": "theta", "version": "1.0", "sha256": f("theta", "1.0", "")["digests"]["sha256"]}, self.meta, now)
        b = vz.judge({"name": "iota", "version": "1.0", "sha256": f("iota", "1.0", "")["digests"]["sha256"]}, self.meta, now)
        self.assertEqual((a["status"], a["age_h"]), ("allowed", 48.5))
        self.assertEqual((b["status"], b["age_h"]), ("too_young", 47.5))

    def test_naive_reference_time_is_utc(self):
        self.assertEqual(vz.reference_time("2026-11-08T12:00:00"), NOW)


class V8AlreadyInstalled(Fixture):
    def test_satisfied_requirement_needs_no_resolve_and_no_metadata(self):
        def never(_):
            raise AssertionError("resolver must not run when everything is installed")
        r = vz.plan([("kappa", ">=1")], never, self.meta, NOW, installed=lambda n: "1.4")
        self.assertTrue(r["ok"])
        self.assertEqual(r["install"], [])
        self.assertEqual(r["present"][0][2:], ("1.4", True))
        self.assertEqual(self.meta.requests, 0)

    def test_installed_but_too_old_is_resolved_and_checked(self):
        self.project("kappa", {"2.0": [f("kappa", "2.0", "2026-01-01T00:00:00Z")]})
        r = vz.plan([("kappa", ">=2")], self.resolver({frozenset(): [item("kappa", "2.0")]}), self.meta, NOW,
                    installed=lambda n: "1.4")
        self.assertTrue(r["ok"])
        self.assertEqual([i["version"] for i in r["install"]], ["2.0"])


class CommandLine(Fixture):
    def test_cli_dry_run_with_env_overrides_and_log(self):
        self.project("alpha", {"1.0": [f("alpha", "1.0", "2026-11-01T00:00:00Z")]})
        self.project("zeta", {"0.5": [f("zeta", "0.5", "2026-11-08T00:00:00Z")]})
        rep = self.dir / "report.json"
        rep.write_text(json.dumps({"install": [item("alpha", "1.0", requires=["zeta"]), item("zeta", "0.5", requested=False)]}), encoding="utf-8")
        log = self.dir / "werkzeuge.md"
        env = dict(os.environ, CHALKLESS_NOW="2026-11-08T12:00:00Z", CHALKLESS_PYPI_METADATA=str(self.dir))
        p = subprocess.run([sys.executable, "-B", str(TOOLS / "voraussetzungen.py"), "--install", "--dry-run",
                            "--report", str(rep), "--log", str(log), "--json"], capture_output=True, text=True,
                           encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 1, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["reference_time"], "2026-11-08T12:00:00Z")
        self.assertEqual(out["install"], [])
        self.assertIn("zeta 0.5", out["limit"])
        text = log.read_text(encoding="utf-8")
        self.assertIn("zeta 0.5 (dependency)", text)
        self.assertIn("too_young", text)

    def test_check_run_writes_protocol_even_when_nothing_is_installed(self):
        log = self.dir / "werkzeuge.md"
        req = self.dir / "requirements.txt"
        req.write_text("", encoding="utf-8")  # nothing required: a pure check, deterministic
        env = dict(os.environ, CHALKLESS_NOW="2026-11-08T12:00:00Z")
        p = subprocess.run([sys.executable, "-B", str(TOOLS / "voraussetzungen.py"), "--requirements", str(req),
                            "--log", str(log)], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertIn("mode check", p.stdout, p.stderr)
        text = log.read_text(encoding="utf-8")
        self.assertIn("## 2026-11-08T12:00Z · check", text)
        self.assertIn("- python ", text)
        self.assertIn("- pdf browser: ", text)
        self.assertIn("- slide check: ", text)
        self.assertIn("- git: ", text)
        self.assertIn("- nothing installed (check only)", text)
        self.assertNotIn(str(Path.home()), text)  # no local paths in the protocol
        subprocess.run([sys.executable, "-B", str(TOOLS / "voraussetzungen.py"), "--requirements", str(req),
                        "--log", str(log)], capture_output=True, text=True, encoding="utf-8", env=env)
        text = log.read_text(encoding="utf-8")
        self.assertEqual(text.count("· check"), 2)  # appended, not overwritten
        self.assertEqual(text.count("# Werkzeuge"), 1)

    def test_default_protocol_path_for_every_run_but_a_dry_run(self):
        self.assertIsNone(vz.default_log(self.dir, "check"))  # no profil/ folder: no protocol
        (self.dir / "profil").mkdir()
        self.assertEqual(vz.default_log(self.dir, "check"), self.dir / "profil" / "werkzeuge.md")
        self.assertEqual(vz.default_log(self.dir, "install"), self.dir / "profil" / "werkzeuge.md")
        self.assertIsNone(vz.default_log(self.dir, "dry-run"))

    def test_no_sha_and_no_filename_the_youngest_file_decides(self):
        self.project("kappa", {"1.0": [f("kappa", "1.0", "2026-10-01T00:00:00Z"),
                                       {**f("kappa", "1.0", "2026-11-08T00:00:00Z"), "filename": "kappa-1.0.tar.gz"}],
                               "0.9": [f("kappa", "0.9", "2026-09-01T00:00:00Z")]})
        self.assertEqual(vz.judge({"name": "kappa", "version": "1.0"}, self.meta, NOW)["status"], "too_young")
        self.assertEqual(vz.judge({"name": "kappa", "version": "0.9"}, self.meta, NOW)["status"], "allowed")

    def test_install_refuses_without_hashes(self):
        ok, err = vz.install([{"name": "alpha", "version": "1.0", "sha256": None}], python="python-does-not-exist")
        self.assertFalse(ok)
        self.assertIn("sha256", err)


if __name__ == "__main__":
    unittest.main()
