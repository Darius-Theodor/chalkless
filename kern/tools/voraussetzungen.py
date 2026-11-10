"""Check and set up the tools Chalkless needs - new packages only if they are at least 48 hours old.

Usage (from the Chalkless folder; the agent runs this, never the teacher):
  python kern/tools/voraussetzungen.py                      check only: Python, packages, PDF browser,
                                                            page images, slide check, git (capabilities)
  python kern/tools/voraussetzungen.py --install            install what is missing, but only if every package
                                                            that would be installed (including all transitive
                                                            dependencies) was published at least 48 h ago
  python kern/tools/voraussetzungen.py --install --dry-run  decide everything, install nothing
Options:
  --json               machine-readable result on stdout
  --probe-browser      also start the installed Edge/Chrome once headless through Playwright (channel), to prove
                       that the slide check can render; never downloads a browser
  --log FILE           append the protocol to FILE instead of the default. Every run without --dry-run (check or
                       install) appends one entry to profil/werkzeuge.md when the folder has profil/: reference time,
                       mode, every checked tool with its version, the result per line, the installed versions with
                       their publication age or "nothing installed". --dry-run writes no protocol unless --log is given
  --now ISO            reference time instead of the system clock, e.g. 2026-11-08T12:00:00Z (env CHALKLESS_NOW);
                       a time without offset is read as UTC
  --metadata-dir DIR   read PyPI metadata from local files DIR/<name>.json (project JSON with "releases") or
                       DIR/<name>-<version>.json (version JSON) instead of the network (env CHALKLESS_PYPI_METADATA)
  --pypi-url URL       base of the PyPI JSON API, default https://pypi.org/pypi (env CHALKLESS_PYPI_JSON_URL)
  --report FILE        use an existing `pip install --dry-run --report` JSON as the resolved set instead of running pip
  --requirements FILE  default kern/tools/requirements.txt
  --self-test          run the deterministic self-tests (kern/tools/tests/test_voraussetzungen.py)
--now, --metadata-dir, --pypi-url and their env variables are test hooks: never set them in a teacher's instance.
Without them the reference time is the system clock (a clock set ahead makes young packages look old; the
protocol in profil/werkzeuge.md names the reference time of every run).

The 48-hour rule (new package versions and all their dependencies must be at least 48 hours old):
1. The set to install is resolved first, without installing: `pip install --dry-run --report --only-binary=:all:`.
   Wheels only, so no build step can pull unchecked build dependencies.
2. For EVERY package in that set (direct and transitive) the concrete version is looked up in the PyPI JSON API.
   The file pip would install is matched by its sha256; its `upload_time_iso_8601` (converted to UTC) must be
   at least 172800 s before the reference time. Exactly 48 h counts as old enough.
3. Too young -> not installed; the newest version that is old enough and fits the requirement is proposed and
   the set is resolved again with that pin (at most 3 rounds).
   Unknown (no metadata, network error, no upload time, file not found) or contradictory (hash differs, upload
   times disagree, upload time in the future, wrong name/version in the metadata, yanked) -> nothing is installed.
4. Installation is all or nothing: `pip install --no-deps --require-hashes` from a lock file with exactly the
   checked versions and hashes. Playwright browsers are never downloaded (`playwright install` is not used);
   the slide check uses the installed Edge or Chrome via Playwright's channel.
Exit code: 0 everything needed is there (or was installed), 1 something is missing or blocked, 2 usage error.
Standard library only (uses pip's bundled `packaging` for version rules when available).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
MIN_AGE_S = 172_800  # 48 h
MIN_PYTHON = (3, 10)
DEFAULT_PYPI = "https://pypi.org/pypi"
MAX_ROUNDS = 3

try:  # pip ships packaging; use it for exact version and specifier rules
    from pip._vendor.packaging.requirements import Requirement as _Req
    from pip._vendor.packaging.specifiers import SpecifierSet as _Spec
    from pip._vendor.packaging.version import InvalidVersion, Version as _Ver
except Exception:  # pragma: no cover - fallback without pip
    _Req = _Spec = _Ver = None

    class InvalidVersion(ValueError):
        pass


# ---------------------------------------------------------------- small helpers

def norm(name: str) -> str:
    """PEP 503 normalised project name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def to_utc(value: str) -> dt.datetime:
    """Parse an ISO 8601 time with offset ('Z' or +hh:mm) and return it in UTC. Raises ValueError."""
    s = value.strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        raise ValueError(f"time without offset: {value}")
    return t.astimezone(dt.timezone.utc)


def reference_time(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return to_utc(value)
    except ValueError:
        t = dt.datetime.fromisoformat(value.strip())  # no offset given: read as UTC (documented)
        return t.replace(tzinfo=dt.timezone.utc)


def ver(v: str):
    if _Ver is not None:
        return _Ver(v)
    parts = re.findall(r"\d+", v.split("+")[0])
    if not parts:
        raise InvalidVersion(v)
    return tuple(int(p) for p in parts)


def is_prerelease(v: str) -> bool:
    if _Ver is not None:
        try:
            return _Ver(v).is_prerelease
        except InvalidVersion:
            return True
    return bool(re.search(r"(a|b|rc|dev)\d*", v))


def satisfies(version: str, specs: list[str]) -> bool:
    """True if version fits every specifier string (e.g. '>=4', '>=1.1,<2')."""
    specs = [s for s in specs if s and s.strip()]
    if not specs:
        return True
    if _Spec is not None:
        try:
            return all(_Spec(s).contains(version, prereleases=True) for s in specs)
        except Exception:
            return False
    ops = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "==": lambda a, b: a == b,
           ">": lambda a, b: a > b, "<": lambda a, b: a < b, "!=": lambda a, b: a != b}
    try:
        v = ver(version)
        for s in specs:
            for part in s.split(","):
                m = re.match(r"\s*(>=|<=|==|!=|>|<)\s*([\w.]+)", part)
                if m and not ops[m.group(1)](v, ver(m.group(2))):
                    return False
        return True
    except InvalidVersion:
        return False


def parse_requirement(line: str):
    """'pypdf>=4   # comment' -> ('pypdf', '>=4', marker_ok). Returns None for empty lines."""
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    if _Req is not None:
        r = _Req(line)
        ok = True
        if r.marker is not None:
            try:
                ok = r.marker.evaluate()
            except Exception:
                ok = True
        return r.name, str(r.specifier), ok
    m = re.match(r"([A-Za-z0-9_.\-]+)\s*(.*)", line)
    return m.group(1), m.group(2).split(";")[0].strip(), True


def read_requirements(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        r = parse_requirement(line)
        if r and r[2]:
            out.append((r[0], r[1]))
    return out


def installed_version(name: str):
    from importlib import metadata
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


# ---------------------------------------------------------------- metadata source

class Metadata:
    """PyPI JSON metadata, from local files (tests, offline) or the JSON API."""

    def __init__(self, metadata_dir: str | None = None, base_url: str | None = None, timeout: float = 20):
        self.dir = Path(metadata_dir) if metadata_dir else None
        self.base = (base_url or DEFAULT_PYPI).rstrip("/")
        self.timeout = timeout
        self._cache: dict[str, object] = {}
        self.requests = 0

    def _load(self, key: str, local_name: str, url: str):
        if key in self._cache:
            return self._cache[key]
        res = (None, "not looked up")
        if self.dir is not None:
            f = self.dir / local_name
            if f.exists():
                try:
                    res = (json.loads(f.read_text(encoding="utf-8")), None)
                except ValueError as e:
                    res = (None, f"unreadable metadata file {f.name}: {e}")
            else:
                res = (None, f"no metadata file {local_name}")
        else:
            self.requests += 1
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "chalkless-voraussetzungen"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    res = (json.loads(r.read().decode("utf-8")), None)
            except urllib.error.HTTPError as e:
                res = (None, f"PyPI answered {e.code} for {url}")
            except Exception as e:  # network down, timeout, bad JSON
                res = (None, f"PyPI not reachable ({type(e).__name__})")
        self._cache[key] = res
        return res

    def project(self, name: str):
        n = norm(name)
        return self._load(n, f"{n}.json", f"{self.base}/{urllib.parse.quote(n)}/json")

    def files(self, name: str, version: str):
        """Return (files, problem) for one concrete version."""
        data, err = self.project(name)
        if data is not None:
            info_name = (data.get("info") or {}).get("name")
            if info_name and norm(info_name) != norm(name):
                return None, f"metadata names {info_name!r}, expected {name!r} (contradictory)"
            rel = data.get("releases")
            if isinstance(rel, dict) and version in rel:
                return rel[version], None
        n = norm(name)
        vdata, verr = self._load(f"{n}=={version}", f"{n}-{version}.json",
                                 f"{self.base}/{urllib.parse.quote(n)}/{urllib.parse.quote(version)}/json")
        if vdata is None:
            return None, verr if data is None else f"version {version} not in the metadata of {name}"
        info = vdata.get("info") or {}
        if info.get("version") and info["version"] != version:
            return None, f"metadata is for {name} {info['version']}, expected {version} (contradictory)"
        if info.get("name") and norm(info["name"]) != n:
            return None, f"metadata names {info['name']!r}, expected {name!r} (contradictory)"
        return vdata.get("urls") or [], None


# ---------------------------------------------------------------- the age check

def upload_time(f: dict):
    """Return (utc_time, problem_kind, text). problem_kind is None, 'unknown' or 'contradictory'."""
    iso = f.get("upload_time_iso_8601")
    if not iso:
        return None, "unknown", f"{f.get('filename', '?')}: no upload_time_iso_8601"
    try:
        t = to_utc(iso)
    except ValueError:
        return None, "unknown", f"{f.get('filename', '?')}: unreadable upload time {iso!r}"
    plain = f.get("upload_time")  # PyPI's second field: naive UTC; both must agree
    if plain:
        try:
            p = dt.datetime.fromisoformat(plain.replace("Z", "")).replace(tzinfo=dt.timezone.utc)
            if abs((p - t).total_seconds()) > 1:
                return None, "contradictory", f"{f.get('filename', '?')}: upload_time {plain} and upload_time_iso_8601 {iso} disagree"
        except ValueError:
            return None, "contradictory", f"{f.get('filename', '?')}: unreadable upload_time {plain!r}"
    return t, None, ""


def judge(item: dict, meta: Metadata, now: dt.datetime) -> dict:
    """Decide for one concrete package version: allowed / too_young / unknown / contradictory."""
    name, version = item["name"], item["version"]
    out = {"name": name, "version": version, "requested": item.get("requested", False)}
    files, problem = meta.files(name, version)
    if files is None:
        kind = "contradictory" if "contradictory" in (problem or "") else "unknown"
        return {**out, "status": kind, "reason": problem}
    if not files:
        return {**out, "status": "unknown", "reason": f"no files published for {name} {version}"}
    sha, fname = item.get("sha256"), item.get("filename")
    if sha:
        chosen = [f for f in files if (f.get("digests") or {}).get("sha256") == sha]
        if not chosen:
            same = [f for f in files if fname and f.get("filename") == fname]
            why = (f"{fname}: sha256 differs from the published file" if same
                   else f"the file pip would install ({fname or sha[:12]}) is not among the published files")
            return {**out, "status": "contradictory", "reason": why}
    elif fname:
        chosen = [f for f in files if f.get("filename") == fname]
        if not chosen:
            return {**out, "status": "unknown", "reason": f"{fname} not found in the metadata"}
    else:
        chosen = list(files)  # no file known: the youngest file of the version decides (conservative)
    if any(f.get("yanked") for f in chosen):
        return {**out, "status": "contradictory", "reason": f"{name} {version} is yanked on PyPI"}
    times = []
    for f in chosen:
        t, kind, text = upload_time(f)
        if kind:
            return {**out, "status": kind, "reason": text}
        times.append(t)
    t = max(times)
    age = (now - t).total_seconds()
    out.update(uploaded=t.strftime("%Y-%m-%dT%H:%M:%SZ"), age_h=round(age / 3600, 1))
    if age < 0:
        return {**out, "status": "contradictory", "reason": f"upload time {out['uploaded']} lies after the reference time"}
    if age >= MIN_AGE_S:
        return {**out, "status": "allowed", "reason": ""}
    return {**out, "status": "too_young", "reason": f"published {out['age_h']} h ago, needs 48 h"}


def suggest(name: str, specs: list[str], blocked_version: str, meta: Metadata, now: dt.datetime):
    """Newest version below the blocked one that fits specs, is not a pre-release and is >= 48 h old."""
    data, _ = meta.project(name)
    rel = (data or {}).get("releases")
    if not isinstance(rel, dict):
        return None
    best = None
    for v, files in rel.items():
        try:
            if ver(v) >= ver(blocked_version) or is_prerelease(v) or not files:
                continue
        except InvalidVersion:
            continue
        if not satisfies(v, specs) or any(f.get("yanked") for f in files):
            continue
        times = [upload_time(f) for f in files]
        if any(k for _, k, _ in times):
            continue
        if (now - max(t for t, _, _ in times)).total_seconds() < MIN_AGE_S:
            continue
        if best is None or ver(v) > ver(best):
            best = v
    return best


# ---------------------------------------------------------------- resolving and planning

def items_from_report(report: dict) -> list[dict]:
    out = []
    for it in report.get("install") or []:
        md = it.get("metadata") or {}
        di = it.get("download_info") or {}
        url = di.get("url") or ""
        ai = di.get("archive_info") or {}
        sha = (ai.get("hashes") or {}).get("sha256")
        if not sha and str(ai.get("hash", "")).startswith("sha256="):
            sha = ai["hash"].split("=", 1)[1]
        out.append({"name": md.get("name", "?"), "version": md.get("version", "?"), "sha256": sha,
                    "filename": urllib.parse.unquote(url.rsplit("/", 1)[-1].split("#")[0]) if url else None,
                    "requested": bool(it.get("requested")), "requires_dist": md.get("requires_dist") or []})
    return out


def specs_by_name(items: list[dict], requirements: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Which version specifiers apply to each package: requirements.txt plus the parents in the resolved set."""
    out: dict[str, list[str]] = {}
    for n, s in requirements:
        out.setdefault(norm(n), []).append(s)
    for it in items:
        for line in it["requires_dist"]:
            r = parse_requirement(line)
            if r is None:
                continue
            if "extra ==" in line or "extra==" in line:
                continue
            out.setdefault(norm(r[0]), []).append(r[1])
    return out


def pip_resolver(requirements_file: Path, python: str = sys.executable):
    def resolve(constraints: dict[str, str]) -> dict:
        with tempfile.TemporaryDirectory(prefix="chalkless-pip-") as tmp:
            rep = Path(tmp) / "report.json"
            cmd = [python, "-m", "pip", "install", "--dry-run", "--quiet", "--disable-pip-version-check",
                   "--only-binary=:all:", "--report", str(rep), "-r", str(requirements_file)]
            if constraints:
                c = Path(tmp) / "constraints.txt"
                c.write_text("".join(f"{n}=={v}\n" for n, v in constraints.items()), encoding="utf-8")
                cmd += ["-c", str(c)]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if p.returncode != 0 or not rep.exists():
                tail = (p.stderr or p.stdout or "").strip().splitlines()[-1:] or ["no output"]
                raise RuntimeError(f"pip could not resolve the packages: {tail[0][:200]}")
            return json.loads(rep.read_text(encoding="utf-8"))
    return resolve


def missing_requirements(requirements, installed=installed_version):
    """[(name, spec, installed_version_or_None, ok)] for every requirement."""
    rows = []
    for n, s in requirements:
        v = installed(n)
        rows.append((n, s, v, v is not None and satisfies(v, [s])))
    return rows


def plan(requirements, resolver, meta: Metadata, now: dt.datetime, installed=installed_version, from_report=False):
    """Decide what may be installed. Never installs. Returns a dict with 'ok', 'install', 'verdicts', 'present'."""
    present = missing_requirements(requirements, installed) if not from_report else []
    if present and all(r[3] for r in present):
        return {"ok": True, "install": [], "verdicts": [], "present": present, "rounds": 0,
                "limit": ""}
    constraints: dict[str, str] = {}
    verdicts: list[dict] = []
    for rnd in range(1, MAX_ROUNDS + 1):
        try:
            report = resolver(dict(constraints))
        except Exception as e:
            return {"ok": False, "install": [], "verdicts": verdicts, "present": present, "rounds": rnd,
                    "limit": f"Nothing was installed: {e}."}
        items = items_from_report(report)
        if not items:
            return {"ok": True, "install": [], "verdicts": [], "present": present, "rounds": rnd, "limit": ""}
        verdicts = [judge(i, meta, now) for i in items]
        blocked = [v for v in verdicts if v["status"] != "allowed"]
        if not blocked:
            return {"ok": True, "install": items, "verdicts": verdicts, "present": present, "rounds": rnd, "limit": ""}
        specs = specs_by_name(items, requirements)
        new = {}
        for v in blocked:
            if v["status"] == "too_young":
                s = suggest(v["name"], specs.get(norm(v["name"]), []), v["version"], meta, now)
                v["suggestion"] = s
                if s and constraints.get(v["name"]) != s:
                    new[v["name"]] = s
        retry = len(new) == len(blocked)  # only when every blocked package has a new, older candidate
        if not retry or rnd == MAX_ROUNDS:
            break
        constraints.update(new)
    first = blocked[0]
    kinds = {"too_young": "is younger than 48 hours", "unknown": "has no verifiable publication date",
             "contradictory": "has contradictory publication data"}
    hint = f" (an older version that is old enough: {first['suggestion']})" if first.get("suggestion") else ""
    limit = (f"Nothing was installed, because {first['name']} {first['version']} {kinds[first['status']]}{hint}"
             + (f" and {len(blocked) - 1} more package(s) are blocked" if len(blocked) > 1 else "") + ".")
    return {"ok": False, "install": [], "verdicts": verdicts, "present": present, "rounds": rnd, "limit": limit,
            "blocked": blocked}


def install(items: list[dict], python: str = sys.executable) -> tuple[bool, str]:
    """Install exactly the checked versions and files, nothing else."""
    if any(not i.get("sha256") for i in items):
        return False, "Nothing was installed: pip did not report a sha256 for every file."
    with tempfile.TemporaryDirectory(prefix="chalkless-lock-") as tmp:
        lock = Path(tmp) / "lock.txt"
        lock.write_text("".join(f"{i['name']}=={i['version']} --hash=sha256:{i['sha256']}\n" for i in items), encoding="utf-8")
        cmd = [python, "-m", "pip", "install", "--no-deps", "--require-hashes", "--only-binary=:all:",
               "--disable-pip-version-check", "--quiet", "-r", str(lock)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()[-1:] or ["no output"]
        return False, f"pip install failed: {tail[0][:200]}"
    return True, ""


# ---------------------------------------------------------------- capabilities (T4: what is really there)

def capabilities(probe_browser: bool = False) -> dict:
    sys.path.insert(0, str(TOOLS))
    caps: dict[str, object] = {}
    caps["python"] = {"version": ".".join(map(str, sys.version_info[:3])), "ok": sys.version_info[:2] >= MIN_PYTHON,
                      "path": sys.executable}
    try:
        from pdf_export import CANDIDATES, find_browser
        browser = find_browser()
        found = [os.path.expandvars(c) for c in CANDIDATES if "%" not in os.path.expandvars(c) and Path(os.path.expandvars(c)).exists()]
    except Exception:
        browser, found = None, []
    caps["pdf_browser"] = browser
    channels = []
    for p in ([browser] if browser else []) + found:
        low = p.lower()
        ch = "msedge" if "edge" in low else "chrome" if "chrome" in low and "chromium" not in low else None
        if ch and ch not in channels:
            channels.append(ch)

    def importable(mod):
        try:
            __import__(mod)
            return True
        except Exception:
            return False

    caps["page_images"] = importable("pypdfium2") and importable("PIL")
    caps["pdf_facts"] = importable("pypdf")
    caps["word_export"] = importable("docx")
    pw = importable("playwright")
    slide = {"playwright": pw, "channels": channels, "ok": pw and bool(channels), "probe": None}
    if probe_browser and slide["ok"]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(channel=channels[0], headless=True)
                pg = b.new_page()
                pg.set_content("<p>ok</p>")
                slide["probe"] = f"{channels[0]} {b.version}"
                b.close()
        except Exception as e:
            slide["probe"] = f"failed: {type(e).__name__}: {str(e).splitlines()[0][:120]}"
            slide["ok"] = False
    caps["slide_check"] = slide
    caps["git"] = shutil.which("git")
    return caps


def routes(caps: dict) -> list[str]:
    """The documented way for each check, chosen from what is available (kern/regeln.md §10)."""
    r = []
    r.append("pdf: headless browser export" if caps["pdf_browser"] else
             "pdf: no Edge/Chrome/Chromium - the teacher prints the HTML to PDF in any browser")
    r.append("pages: page images via pypdfium2 + pillow" if caps["page_images"] else
             "pages: no page images - check page facts with pypdf (if present) and re-read the HTML; say that the pages were not seen")
    sc = caps["slide_check"]
    r.append(f"slides: python kern/tools/folien_check.py <deck> --out <temp folder> (Playwright via channel {sc['channels'][0]})" if sc["ok"] else
             "slides: no rendering - folien_check.py runs its structural check only (notes hidden, no external requests, steps per phase); say that the display was not seen")
    r.append("history: git - python kern/tools/verlauf.py --einrichten says where it lives in this folder" if caps["git"]
             else "history: no git - no undo; say so once")
    return r


# ---------------------------------------------------------------- output

def default_log(root: Path, mode: str) -> Path | None:
    """Where the protocol goes without --log: profil/werkzeuge.md of an instance for every real run
    (check or install); a dry run, or a folder without profil/, writes none."""
    if mode == "dry-run" or not (root / "profil").is_dir():
        return None
    return root / "profil" / "werkzeuge.md"


def write_log(path: Path, now: dt.datetime, mode: str, result: dict, caps: dict | None):
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if new:
        lines += ["# Werkzeuge", "",
                  "> Protokoll der Werkzeug-Prüfung und -Einrichtung (schreibt der Agent bei jedem Lauf). Neue Pakete werden "
                  "nur installiert, wenn die Version und alle Abhängigkeiten mindestens 48 Stunden veröffentlicht sind.", ""]
    lines.append(f"## {now.strftime('%Y-%m-%dT%H:%MZ')} · {mode}")
    if caps:  # names and versions only, never local paths (they can hold the user name)
        py = caps["python"]
        lines.append(f"- python {py['version']}: {'ok' if py['ok'] else 'older than 3.10'}")
        lines.append(f"- pdf browser: {Path(caps['pdf_browser']).name if caps.get('pdf_browser') else 'none'}")
        lines.append(f"- page images (pypdfium2 + pillow): {'present' if caps.get('page_images') else 'missing'}")
        sc = caps.get("slide_check") or {}
        probe = f" · probe {sc['probe']}" if sc.get("probe") else ""
        lines.append(f"- slide check: {'ok' if sc.get('ok') else 'no rendering'}"
                     f" (playwright {'present' if sc.get('playwright') else 'missing'}, "
                     f"channels {', '.join(sc.get('channels') or []) or 'none'}){probe}")
        lines.append(f"- git: {'present' if caps.get('git') else 'missing'}")
    for n, s, v, ok in result.get("present", []):
        lines.append(f"- {n}{s}: {'present ' + v if ok else ('missing' if v is None else 'too old ' + v)}")
    for v in result.get("verdicts", []):
        extra = f" · uploaded {v['uploaded']} · {v['age_h']} h" if v.get("uploaded") else ""
        sug = f" · proposal {v['suggestion']}" if v.get("suggestion") else ""
        lines.append(f"- {v['name']} {v['version']}{' (dependency)' if not v.get('requested') else ''}{extra} · "
                     f"{v['status']}{(': ' + v['reason']) if v.get('reason') else ''}{sug}")
    if result.get("installed"):
        lines.append(f"- installed: {', '.join(i['name'] + ' ' + i['version'] for i in result['install'])}")
    elif mode == "dry-run":
        lines.append("- nothing installed (dry run)")
    elif mode == "check":
        lines.append("- nothing installed (check only)")
    else:
        lines.append("- nothing installed" + (" (everything needed was present)" if result.get("ok") else ""))
    if result.get("limit"):
        lines.append(f"- limit: {result['limit']}")
    if caps:
        lines += [f"- route {x}" for x in routes(caps)]
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--probe-browser", action="store_true")
    ap.add_argument("--log")
    ap.add_argument("--now", default=os.environ.get("CHALKLESS_NOW"))
    ap.add_argument("--metadata-dir", default=os.environ.get("CHALKLESS_PYPI_METADATA"))
    ap.add_argument("--pypi-url", default=os.environ.get("CHALKLESS_PYPI_JSON_URL"))
    ap.add_argument("--report")
    ap.add_argument("--requirements", default=str(TOOLS / "requirements.txt"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if a.self_test:
        return subprocess.call([sys.executable, "-B", str(TOOLS / "tests" / "test_voraussetzungen.py"), "-v"])
    try:
        now = reference_time(a.now)
    except ValueError:
        print(f"unreadable --now {a.now!r}", file=sys.stderr)
        return 2
    reqs = read_requirements(Path(a.requirements))
    meta = Metadata(a.metadata_dir, a.pypi_url)
    caps = capabilities(a.probe_browser)

    result: dict = {"ok": True, "install": [], "verdicts": [], "present": missing_requirements(reqs), "limit": ""}
    mode = "check"
    if a.install or a.report:
        mode = "dry-run" if (a.dry_run or not a.install) else "install"
        if a.report:
            rep = json.loads(Path(a.report).read_text(encoding="utf-8"))
            resolver = lambda constraints: rep  # noqa: E731 - fixed set given from outside
        else:
            resolver = pip_resolver(Path(a.requirements))
        result = plan(reqs, resolver, meta, now, from_report=bool(a.report))
        if mode == "install" and result["ok"] and result["install"]:
            ok, err = install(result["install"])
            result["installed"] = ok
            if not ok:
                result["ok"], result["limit"] = False, f"Nothing usable was installed: {err}."
            caps = capabilities(a.probe_browser)
            result["present"] = missing_requirements(reqs)
    if not caps["python"]["ok"]:
        result["ok"] = False
        result["limit"] = (result.get("limit") or "") + f" Python {caps['python']['version']} is older than 3.10."

    log = a.log or default_log(ROOT, mode)
    if log:
        write_log(Path(log), now, mode, result, caps)

    if a.json:
        print(json.dumps({"reference_time": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": mode, "capabilities": caps,
                          "routes": routes(caps), **{k: v for k, v in result.items() if k != "install"},
                          "install": [{"name": i["name"], "version": i["version"]} for i in result.get("install", [])]},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(f"reference time {now.strftime('%Y-%m-%dT%H:%M:%SZ')} · mode {mode}")
        print(f"{'OK  ' if caps['python']['ok'] else 'FAIL'} python {caps['python']['version']}")
        for n, s, v, ok in result.get("present", []):
            print(f"{'OK  ' if ok else 'MISS'} {n}{s}: {v or 'not installed'}")
        for v in result.get("verdicts", []):
            tag = "OK  " if v["status"] == "allowed" else "BLOCK"
            extra = f" uploaded {v['uploaded']} ({v['age_h']} h)" if v.get("uploaded") else ""
            print(f"{tag} {v['name']} {v['version']}{' (dependency)' if not v.get('requested') else ''}:{extra} "
                  f"{v['status']}{(' - ' + v['reason']) if v.get('reason') else ''}"
                  f"{(' - proposal ' + v['suggestion']) if v.get('suggestion') else ''}")
        if result.get("install"):
            print(("INSTALLED " if result.get("installed") else "WOULD INSTALL ")
                  + ", ".join(f"{i['name']}=={i['version']}" for i in result["install"]))
        for x in routes(caps):
            print(f"ROUTE {x}")
        if caps["slide_check"].get("probe"):
            print(f"PROBE slide browser: {caps['slide_check']['probe']}")
        if result.get("limit"):
            print(f"LIMIT {result['limit'].strip()}")
    missing = [r for r in result.get("present", []) if not r[3]]
    return 0 if result["ok"] and caps["python"]["ok"] and not (missing and mode != "dry-run" and not a.report) else 1


if __name__ == "__main__":
    sys.exit(main())
