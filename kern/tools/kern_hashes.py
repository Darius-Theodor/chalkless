"""SHA-256 list of the shipped core, to tell local core changes apart from the published core.

Usage (from the Chalkless folder):
  python kern/tools/kern_hashes.py --write    write kern/core-hashes.sha256 (done when the package is built,
                                              as the last step after every change to the core)
  python kern/tools/kern_hashes.py            compare the folder with that list: changed / missing / added files
  python kern/tools/kern_hashes.py --json     the same as JSON
Core = everything in kern/ (without __pycache__) plus the root files that an update replaces:
AGENTS.md, CLAUDE.md, README.md, START-HIER.md, CHANGELOG.md, .claude/launch.json.
Text files are hashed with LF line endings, so a checkout with CRLF does not count as a change.
kern/PILOT is optional: it is hashed when present, but a missing kern/PILOT is never reported (a release
without it is complete, even with a list written while it was there); a kern/PILOT added later is reported.
The list is never written by the agent in a teacher's instance: a list made from an already changed core
would hide the change. check_instance.py reads the list and reports changed files.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST = Path("kern") / "core-hashes.sha256"
ROOT_FILES = ("AGENTS.md", "CLAUDE.md", "README.md", "START-HIER.md", "CHANGELOG.md", ".claude/launch.json")
OPTIONAL = {"kern/PILOT"}  # may be absent in a complete package (release builds)
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx", ".pptx", ".woff", ".woff2", ".ttf", ".ico", ".zip"}


def core_files(root: Path = ROOT) -> list[str]:
    out = []
    for p in sorted((root / "kern").rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        rel = p.relative_to(root).as_posix()
        if rel != LIST.as_posix():
            out.append(rel)
    out += [f for f in ROOT_FILES if (root / f).is_file()]
    return out


def file_hash(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() not in BINARY:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def read_list(root: Path = ROOT):
    """{path: sha256} from kern/core-hashes.sha256, or None if the list is missing."""
    f = root / LIST
    if not f.exists():
        return None
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        h, _, rel = line.partition("  ")
        out[rel.strip()] = h.strip()
    return out


def compare(root: Path = ROOT):
    """Return None without a list, else {'changed': [...], 'missing': [...], 'added': [...]}."""
    ref = read_list(root)
    if ref is None:
        return None
    now = {rel: file_hash(root / rel) for rel in core_files(root)}
    return {"changed": sorted(r for r in ref if r in now and now[r] != ref[r]),
            "missing": sorted(r for r in ref if r not in now and r not in OPTIONAL),
            "added": sorted(r for r in now if r not in ref and r.startswith("kern/"))}


def write_list(root: Path = ROOT) -> Path:
    version = (root / "kern" / "VERSION").read_text(encoding="utf-8").strip()
    lines = [f"# Chalkless core {version} - SHA-256 per file (text with LF line endings); written by kern/tools/kern_hashes.py --write"]
    lines += [f"{file_hash(root / rel)}  {rel}" for rel in core_files(root)]
    (root / LIST).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root / LIST


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    if "--write" in sys.argv:
        p = write_list()
        print(f"written {p.relative_to(ROOT).as_posix()} ({len(core_files())} files)")
        return 0
    res = compare()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
    elif res is None:
        print(f"no list {LIST.as_posix()} - core changes cannot be detected")
    else:
        for k in ("changed", "missing", "added"):
            for rel in res[k]:
                print(f"{k:8} {rel}")
        if not any(res.values()):
            print("core unchanged")
    return 0 if res is not None and not any(res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
